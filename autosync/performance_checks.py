"""Checks for reading Meesho's product-performance file into a record per product per week (A87, D459).

The fixture carries the header and the shapes of cell his real file has (`meesho_me_product_performance_2026-10-19.csv`, 144 rows): joined
`97677 | 89.1%` figures, a rupee amount, an empty Catalog ID and a blank Rating.

Run: python autosync/performance_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import performance  # noqa: E402
import reading  # noqa: E402
import table  # noqa: E402
import whats_new  # noqa: E402

ran = 0
failures = []
THREW = []
RUPEE = chr(0x20B9)


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


def answered(work):
    try:
        return work()
    except Exception as wrong:  # noqa: BLE001
        THREW.append(repr(wrong))
        return None


def caught(work):
    try:
        work()
    except Exception as wrong:  # noqa: BLE001
        return wrong
    return None


HEAD = '"Range","Last updated","Product","Catalog ID","Rating","Views","Clicks","Orders","Conversions","Sales","Returns","Insights","Recommendations"'
WEEK = "13th Oct '26 - 19th Oct '26"


def row(product, rating="", views="100 | 5.0%", clicks="10", orders="1", conversions="10.0% | 2.0%", sales=None, returns="0.0%", week=WEEK):
    sales = sales or (RUPEE + "1,250.50")
    return f'"{week}","Last updated 19th Oct | 10:55","{product}","","{rating}","{views}","{clicks}","{orders}","{conversions}","{sales}","{returns}","",""'


def file_of(*rows):
    return table.read(("\n".join([HEAD, *rows]) + "\n").encode("utf-8"))


TITLES = {
    "gold jhumka": frozenset({"111"}),
    "shared title": frozenset({"222", "333"}),
}

# ---------------------------------------------------------------- the week and the figures

check("THE WEEK IS READ FROM THE RANGE, and a range this cannot read is nothing, never a guessed week",
      performance.a_week(WEEK) == ("2026-10-13", "2026-10-19") and performance.a_week("last 7 days") is None
      and performance.a_week("32nd Oct '26 - 33rd Oct '26") is None)
made, not_read = answered(lambda: performance.read_performance("me_product_performance", "meesho", file_of(
    row("Gold Jhumka", rating="4.1", views="97677 | 89.1%", clicks="7416", orders="53", conversions="54.3% | 42.6%",
        sales=RUPEE + "12,916.00", returns="11.1%"),
    row("Shared Title"), row("Unknown Product")), "2026-10-19", TITLES)) or ({}, ())
mine = next((r for r in made.values() if r["product"] == "Gold Jhumka"), {})
check("A PRODUCT'S WEEK KEEPS THE FIGURES AS THE PAGE WRITES THEM: views and conversion are the first figure, the second is kept under its own name",
      mine.get("views") == 97677 and mine.get("viewsOther") == 89.1 and mine.get("conversion") == 54.3 and mine.get("conversionOther") == 42.6
      and mine.get("clicks") == 7416 and mine.get("orders") == 53 and mine.get("sales") == 12916 and mine.get("returnsPct") == 11.1
      and mine.get("rating") == 4.1 and mine.get("weekFrom") == "2026-10-13" and mine.get("weekTo") == "2026-10-19")
check("a blank rating is nothing, not nought", "rating" not in next(r for r in made.values() if r["product"] == "Shared Title"))

# ---------------------------------------------------------------- matched to a catalog by title

check("A TITLE THAT BELONGS TO ONE CATALOG GIVES ITS CATALOG ID",
      mine.get("matched") is True and mine.get("catalogId") == "111")
shared = next(r for r in made.values() if r["product"] == "Shared Title")
unknown = next(r for r in made.values() if r["product"] == "Unknown Product")
check("a title shared by several catalogs is kept, says so, and is not given one of them",
      shared["matched"] is False and "catalogId" not in shared and "2 catalogs" in shared["note"])
check("A TITLE NOBODY HAS IS KEPT AND FLAGGED 'not matched to a catalog' -- never dropped",
      unknown["matched"] is False and unknown["note"] == "not matched to a catalog" and "catalogId" not in unknown and len(made) == 3)
check("the seller's own titles are made from the listings read from me_catalog",
      performance.titles_of({"a": {"productName": " Gold Jhumka ", "catalogId": "111"}, "b": {"productName": "gold jhumka", "catalogId": "111"}})
      == {"gold jhumka": frozenset({"111"})})

# ---------------------------------------------------------------- names, repeats, refusals

twice, _ = answered(lambda: performance.read_performance("me_product_performance", "meesho", file_of(
    row("Gold Jhumka", orders="1"), row("Gold Jhumka", orders="2")), "2026-10-19", TITLES)) or ({}, ())
check("TWO ROWS WITH ONE TITLE IN A WEEK ARE TWO RECORDS (three titles repeat in his real file), none lost",
      len(twice) == 2 and sorted(r["orders"] for r in twice.values()) == [1, 2])
other_week, _ = answered(lambda: performance.read_performance("me_product_performance", "meesho", file_of(
    row("Gold Jhumka", week="6th Oct '26 - 12th Oct '26")), "2026-10-19", TITLES)) or ({}, ())
check("another week of the same product is another record, so two overlapping weeks are never summed",
      len(other_week) == 1 and not (set(other_week) & set(made)))
_, bad = answered(lambda: performance.read_performance("me_product_performance", "meesho", file_of(
    row("Gold Jhumka", views="lots | 5%"), row("", orders="1"), row("Fine Product")), "2026-10-19", TITLES)) or ({}, ())
check("a figure that is not one, or a row with no product, is refused by name and the rest are read",
      len(bad) == 2)
no_columns = caught(lambda: performance.read_performance("me_product_performance", "meesho", table.read(b"A,B\n1,2\n"), "2026-10-19", TITLES))
check("a file without the columns is refused in words naming what it has",
      no_columns is not None and "Product" in str(no_columns) and "Nothing was read" in str(no_columns))
check("and the fields are only the product week's own", all(set(r) <= set(performance.PERFORMANCE_FIELDS) for r in made.values()))

# ---------------------------------------------------------------- the record, the sink and the night


_night_records = []
_files = {
    "me_product_performance": [whats_new.InTheFolder(which="pp1", name="meesho_me_product_performance_2026-10-19.csv", size=900)],
    "me_catalog": [whats_new.InTheFolder(which="cat1", name="meesho_me_catalog_2026-10-14.xlsx", size=900)],
}
_asked_for = []


class _Listings:
    records = {"x": {"productName": "Gold Jhumka", "catalogId": "111"}}


def _the_catalog_file(how, one, body):
    _asked_for.append(one.which)
    return _Listings(), "2026-10-14"


_real_listings_reading = reading.a_listings_reading
reading.a_listings_reading = _the_catalog_file
_files["me_catalog"].append(whats_new.InTheFolder(which="cat0", name="meesho_me_catalog_2026-10-01.xlsx", size=900))
try:
    night = answered(lambda: reading.read_what_is_new(
        already_read=("cat0", "cat1"),
        what_is_in_the_folder=lambda r: list(_files.get(r, ())),
        bring_it_back=lambda w: ("\n".join([HEAD, row("Gold Jhumka"), row("Unknown Product")]) + "\n").encode("utf-8"),
        record_the_sales=lambda readings: None,
        record_records={"me_product_performance": lambda report_id, day, records: _night_records.append((report_id, day, records)) or len(records)},
    ))
finally:
    reading.a_listings_reading = _real_listings_reading
_night_made = _night_records[0][2] if _night_records else {}
check("THE NIGHT MATCHES BY THE NEWEST CATALOG FILE'S TITLES, writes every product week, keeps a product it cannot match, and the file is read",
      night is not None and night.read_tonight == ("pp1",) and night.wrote("me_product_performance") == 2 and _asked_for == ["cat1"]
      and {r["product"]: r["matched"] for r in _night_made.values()} == {"Gold Jhumka": True, "Unknown Product": False})


def _a_catalog_that_will_not_read(how, one, body):
    raise table.CannotRead("the download was cut short")


reading.a_listings_reading = _a_catalog_that_will_not_read
_wrote_anyway = []
try:
    broken = answered(lambda: reading.read_what_is_new(
        already_read=("cat0", "cat1"), what_is_in_the_folder=lambda r: list(_files.get(r, ())),
        bring_it_back=lambda w: ("\n".join([HEAD, row("Gold Jhumka")]) + "\n").encode("utf-8"),
        record_the_sales=lambda readings: None,
        record_records={"me_product_performance": lambda report_id, day, records: _wrote_anyway.append(1) or len(records)},
    ))
finally:
    reading.a_listings_reading = _real_listings_reading
check("A CATALOG FILE THAT WILL NOT READ LEAVES THE PERFORMANCE FILE UNREAD and says why -- matched against nothing, every product would be flagged for good",
      broken is not None and broken.read_tonight == () and _wrote_anyway == [] and any("could not be read" in x for x in broken.could_not_read))
# ---------------------------------------------------------------- R20 proving: what each record holds, exactly
import hashlib  # noqa: E402
import records  # noqa: E402

_pm, _pr = answered(lambda: performance.read_performance("me_product_performance", "meesho", file_of(
    row("Gold Jhumka", rating="4.3", views="100 | -5.5%", conversions="10.126% | 2.0%", returns="120%"),
    row("Gold Jhumka"),
    row("Shared Title"),
    row("Bad Range", week="13th Oct '26 - 19th Oct '26 - 20th Oct '26"),
    row("Bad Month", week="13th Foo '26 - 19th Oct '26"),
    row("Three Figures", views="1 | 2 | 3"),
), "2026-10-20", TITLES)) or ({}, ())
_base = "meesho__2026-10-19__" + hashlib.sha1("Gold Jhumka".encode("utf-8")).hexdigest()[:12]
_pwant = {"platform": "meesho", "report": "me_product_performance", "product": "Gold Jhumka", "weekFrom": "2026-10-13", "weekTo": "2026-10-19",
          "fileDay": "2026-10-20", "views": 100, "viewsOther": -5.5, "conversion": 10.13, "conversionOther": 2, "clicks": 10, "orders": 1,
          "sales": 1250.5, "returnsPct": 120, "rating": 4.3, "catalogId": "111", "matched": True}
check("A PRODUCT WEEK HOLDS EXACTLY ITS OWN FIGURES: whole ones whole, others to two places, a second figure that may be below nought, "
      "returns above a hundred per cent as said, named by the week's LAST day and twelve characters of the title (R20 proving)",
      _pm.get(_base) == dict(_pwant, digest=records.the_digest(_pwant))
      and all(type(_pm.get(_base, {}).get(k)) is int for k in ("views", "conversionOther", "clicks", "orders", "returnsPct")))
check("the same title twice in a week: the first keeps the plain name, the second is -2 (R20 proving)",
      set(_pm) >= {_base, _base + "-2"} and _pm[_base]["rating"] == 4.3)
check("a week of three dates, a month word that is not one, and three joined figures are each refused by line, not guessed (R20 proving)",
      len(_pr) == 3 and len(_pm) == 3)
check("a title two catalogs share is not matched, and says how many (R20 proving)",
      performance.titles_of({"a": {"productName": "Shared", "catalogId": "1"}, "b": {"productName": " shared ", "catalogId": "2"}})
      == {"shared": frozenset({"1", "2"})})
check("a figure that changes changes the fingerprint, so a changed week is written again (R20 proving)",
      (lambda a, b: a and b and next(iter(a[0].values()))["digest"] != next(iter(b[0].values()))["digest"])(
          answered(lambda: performance.read_performance("p", "meesho", file_of(row("Gold Jhumka", orders="1")), "2026-10-20", TITLES)),
          answered(lambda: performance.read_performance("p", "meesho", file_of(row("Gold Jhumka", orders="2")), "2026-10-20", TITLES))))
_no_rating = answered(lambda: performance.read_performance("p", "meesho", table.read(
    (HEAD.replace('"Rating",', "") + "\n" + f'"{WEEK}","x","Gold Jhumka","","100 | 5.0%","10","1","10.0% | 2.0%","9","0.0%","",""' + "\n").encode("utf-8")),
    "2026-10-20", TITLES))
check("a file without the optional Rating column is still read, with no rating (R20 proving)",
      _no_rating is not None and len(_no_rating[0]) == 1 and "rating" not in next(iter(_no_rating[0].values())))
for _gone in ("Returns", "Conversions"):
    check(f"a file without the {_gone} column is refused in words (R20 proving)",
          "Nothing was read" in str(caught(lambda g=_gone: performance.read_performance("p", "meesho", table.read(
              (HEAD.replace(f'"{g}",', "") + "\n").encode("utf-8")), "2026-10-20", TITLES))))

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 15 + 8
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")
print(f"\n{len(failures)} FAILED: {failures}" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
