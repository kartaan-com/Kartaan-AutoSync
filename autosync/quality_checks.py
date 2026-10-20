"""Checks for reading Flipkart's Quality Insights file into a record per listing (A87, plan part F1).

The fixture rows are copied from his real file `flipkart_fk_quality_insights_2026-10-19.csv` (18 listings), including the cells that are not plain:
`NA | Not Enough Orders`, a returns share with no note, a rupee amount in K and in L.

Run: python autosync/quality_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import firestore  # noqa: E402
import firestore_door  # noqa: E402
import quality  # noqa: E402
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


HEAD = '"Product","SKU ID","Yearly Sales","1Y Ratings Trend","5M Returns Trend","FA badge","Suppression Risk","Issue Details"'


def row(product, sku, sales, stars, returns, badge="Yes", risk="No Risk", issue="Quality"):
    return f'"{product}","{sku}","{RUPEE}{sales}","{stars}","{returns}","{badge}","{risk}","{issue}"'


def file_of(*rows):
    return table.read(("\n".join([HEAD, *rows]) + "\n").encode("utf-8"))


ROWS = (
    row("Rumee Antique Gold Tone Bahubali Jhumki", "DJ-5 Bahubali", "6.32L", "4.2", "17.6%"),
    row("Rumee Lakshmi Earrings for Women", "OG DJ6", "79.67K", "3.5", "24.1%", risk="Suppressed", issue="Not enough feedback"),
    row("Rumee South Indian Earrings", "OG DJ5", "41.34K", "4.4", "9.1% | Not Enough Orders", issue="Not enough feedback"),
    row("Rumee Silver Earrings", "NJ2-1", "34.91K", "4.4", "NA | Not Enough Orders", issue="Not enough feedback"),
)

made, not_read = answered(lambda: quality.read_quality("fk_quality_insights", "flipkart", file_of(*ROWS), "2026-10-19")) or ({}, ())
first = made.get("flipkart__DJ-5 Bahubali", {})
check("A LISTING'S QUALITY IS A RECORD NAMED BY ITS SKU, with the star level and returns share as levels",
      set(made) == {"flipkart__DJ-5 Bahubali", "flipkart__OG DJ6", "flipkart__OG DJ5", "flipkart__NJ2-1"} and not_read == ()
      and first.get("stars") == 4.2 and first.get("returnsPct") == 17.6 and first.get("faBadge") is True)
check("RUPEES ARE READ WITH THEIR K AND L: 6.32L is 632000 and 79.67K is 79670",
      first.get("yearlySales") == 632000 and made["flipkart__OG DJ6"]["yearlySales"] == 79670)
check("the platform's own words for suppression risk and the issue are kept as written",
      made["flipkart__OG DJ6"]["suppressionRisk"] == "Suppressed" and made["flipkart__OG DJ6"]["issue"] == "Not enough feedback")
check("a returns share with a note keeps both; NA is nothing, not nought",
      made["flipkart__OG DJ5"]["returnsPct"] == 9.1 and made["flipkart__OG DJ5"]["returnsNote"] == "Not Enough Orders"
      and "returnsPct" not in made["flipkart__NJ2-1"] and made["flipkart__NJ2-1"]["returnsNote"] == "Not Enough Orders")
check("amounts with a suffix this does not know are refused, not guessed", caught(lambda: quality.rupees(RUPEE + "5M")) is not None
      and quality.rupees(RUPEE + "1.5Cr") == 15000000 and quality.rupees("NA") is None and quality.rupees("") is None)
_, bad = answered(lambda: quality.read_quality("fk_quality_insights", "flipkart", file_of(
    row("A", "S1", "5M", "4.0", "1%"), row("B", "", "1K", "4.0", "1%"), row("C", "S3", "1K", "great", "1%"), row("D", "S4", "1K", "4.0", "1%")),
    "2026-10-19")) or ({}, ())
check("a row with an amount, a SKU or a star level this cannot read is refused by name and the rest are read", len(bad) == 3)
_dups, dup_said = answered(lambda: quality.read_quality("fk_quality_insights", "flipkart", file_of(
    row("A", "X", "1K", "4.0", "1%"), row("B", "X", "2K", "4.1", "2%")), "2026-10-19")) or ({}, ())
check("A SKU NAMED TWICE IN ONE FILE IS SAID, the later line standing, never dropped in silence",
      len(_dups) == 1 and _dups["flipkart__X"]["yearlySales"] == 2000 and len(dup_said) == 1 and "named twice" in dup_said[0])
_, odd = answered(lambda: quality.read_quality("fk_quality_insights", "flipkart", file_of(
    row("A", "S1", "Infinity", "4.0", "1%"), row("B", "S2", "1e400K", "4.0", "1%"), row("C", "S3", "1K", "42", "1%"),
    row("D", "S4", "1K", "4.0", "-3%"), row("E", "S5", "1K", "4.0", "1%"), row("F", "S" * 2000, "1K", "4.0", "1%")), "2026-10-19")) or ({}, ())
check("a cell that is not a sane amount, star level or percentage, or a SKU too long to name a record, refuses its row and not the file", len(odd) == 5)
no_columns = caught(lambda: quality.read_quality("fk_quality_insights", "flipkart", table.read(b"A,B\n1,2\n"), "2026-10-19"))
check("a file without the columns is refused in words naming what it has",
      no_columns is not None and "SKU ID" in str(no_columns) and "Nothing was read" in str(no_columns))

# ---------------------------------------------------------------- the history

today_record = made["flipkart__DJ-5 Bahubali"]
older = ({"day": "2026-10-12", "stars": 4.1, "returnsPct": 18.0},)
merged = quality.with_history(today_record, older)
check("THE HISTORY IS THE HELD READINGS WITH TODAY'S PUT ON THE END, one reading a day",
      merged["history"] == [{"day": "2026-10-12", "stars": 4.1, "returnsPct": 18.0}, {"day": "2026-10-19", "stars": 4.2, "returnsPct": 17.6}]
      and [p["day"] for p in quality.with_history(today_record, older + ({"day": "2026-10-19", "stars": 1.0},))["history"]] == ["2026-10-12", "2026-10-19"])
long_ago = tuple({"day": f"2026-09-{n:02d}", "stars": 4.0} for n in range(1, 21))
check("and only the last twelve days are kept", len(quality.with_history(today_record, long_ago)["history"]) == quality.HISTORY_KEPT)
check("the fingerprint ignores the day and the history, so the same file read twice writes nothing",
      quality.the_digest(today_record) == quality.the_digest(merged) == quality.the_digest(dict(today_record, fileDay="2026-10-26")))


# ---------------------------------------------------------------- the sink


class Reply:
    def __init__(self, status=200, body=None):
        self.status, self._body, self.text = status, body if body is not None else {}, str(body or "")

    ok = property(lambda self: 200 <= self.status < 300)

    def json(self):
        return self._body

    def records(self):
        return self._body if isinstance(self._body, list) else None


class Database:
    def __init__(self, held=None):
        self.held, self.posts = held or {}, []

    def post(self, url, params=None, headers=None, json=None, data=None):
        self.posts.append({"url": url, "json": json})
        if url.endswith(":batchGet"):
            found = []
            for name in json["documents"]:
                got = self.held.get(name.rsplit("/", 1)[-1])
                found.append({"found": {"name": name, "fields": firestore.a_deep(got)["mapValue"]["fields"]}} if got else {"missing": name})
            return Reply(200, found)
        return Reply(200, {})

    def written(self):
        out = {}
        for post in self.posts:
            if post["url"].endswith(":commit"):
                for write in post["json"]["writes"]:
                    out[write["update"]["name"].rsplit("/", 1)[-1]] = firestore.plain_deep({"mapValue": {"fields": write["update"]["fields"]}})
        return out


db = Database()
wrote = answered(lambda: firestore_door.a_quality_sink(db, "p")("fk_quality_insights", "2026-10-19", made))
check("THE QUALITY RECORDS ARE ASKED ABOUT FIRST, THEN WRITTEN, each with its history of one reading",
      wrote == 4 and [p["url"].rsplit(":", 1)[-1] for p in db.posts] == ["batchGet", "commit"]
      and db.written()["flipkart__DJ-5 Bahubali"]["history"] == [{"day": "2026-10-19", "stars": 4.2, "returnsPct": 17.6}])
held_same = Database({k: dict(v, history=[{"day": "2026-10-19", "stars": 4.2}]) for k, v in made.items()})
check("a second run on the same file writes nothing",
      answered(lambda: firestore_door.a_quality_sink(held_same, "p")("fk_quality_insights", "2026-10-19", made)) == 0)
held_older = Database({"flipkart__DJ-5 Bahubali": dict(first, stars=4.0, digest="stale", fileDay="2026-10-12", history=list(older))})
check("a changed figure is written with the earlier reading kept in the history",
      answered(lambda: firestore_door.a_quality_sink(held_older, "p")("fk_quality_insights", "2026-10-19", {"flipkart__DJ-5 Bahubali": first})) == 1
      and [p["day"] for p in held_older.written()["flipkart__DJ-5 Bahubali"]["history"]] == ["2026-10-12", "2026-10-19"])
held_newer = Database({"flipkart__DJ-5 Bahubali": dict(first, stars=3.0, digest="other", fileDay="2026-10-25", history=[])})
check("and an older file never puts a newer file's figures back",
      answered(lambda: firestore_door.a_quality_sink(held_newer, "p")("fk_quality_insights", "2026-10-19", {"flipkart__DJ-5 Bahubali": first})) == 0)
check("a field the record may not hold is refused by the writer", caught(lambda: firestore.a_quality_write("p", "x", dict(first, secret=1))) is not None)

# ---------------------------------------------------------------- the night

_files = {"fk_quality_insights": [whats_new.InTheFolder(which="q1", name="flipkart_fk_quality_insights_2026-10-19.csv", size=900)]}
BODY = ("\n".join([HEAD, *ROWS]) + "\n").encode("utf-8")
_written = []
night = answered(lambda: reading.read_what_is_new(
    already_read=(), what_is_in_the_folder=lambda r: list(_files.get(r, ())), bring_it_back=lambda w: BODY,
    record_the_sales=lambda readings: None,
    record_quality=lambda report_id, day, records: _written.append((day, sorted(records))) or len(records)))
check("THE NIGHT WRITES EVERY LISTING'S QUALITY and the file is read",
      night is not None and night.read_tonight == ("q1",) and night.quality_written == 4 and _written[0][0] == "2026-10-19")
nowhere = answered(lambda: reading.read_what_is_new(
    already_read=(), what_is_in_the_folder=lambda r: list(_files.get(r, ())), bring_it_back=lambda w: BODY, record_the_sales=lambda readings: None))
check("and with nowhere to write them the file is left unread, not lost",
      nowhere is not None and nowhere.read_tonight == () and nowhere.quality_waiting == 1)
check("the report is read and no longer said to be waiting",
      [o.report_id for o in reading.WHAT_QUALITY_CAN_BE_READ] == ["fk_quality_insights"]
      and "fk_quality_insights" not in reading.WHAT_IS_FETCHED_AND_NOT_READ_YET and reading.why_a_report_has_no_decision() == "")

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 21
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")
print(f"\n{len(failures)} FAILED: {failures}" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
