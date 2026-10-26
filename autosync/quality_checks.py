"""Checks for reading Flipkart's Quality Insights file into a record per listing (A87, plan part F1).

The fixture rows are copied from his real file `flipkart_fk_quality_insights_2026-10-19.csv` (18 listings), including the cells that are not plain:
`NA | Not Enough Orders`, a returns share with no note, a rupee amount in K and in L.

Run: python autosync/quality_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import quality  # noqa: E402
import records  # noqa: E402
import table  # noqa: E402

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
_over, over_said = answered(lambda: quality.read_quality("fk_quality_insights", "flipkart", file_of(
    row("A", "S1", "1K", "4.0", "150%"), row("B", "S2", "1K", "4.0", "100%")), "2026-10-19")) or ({}, ())
check("THE PLATFORM'S OWN RETURN % IS STORED EXACTLY AS GIVEN, even past 100: never capped, never refused (D561, A90)",
      over_said == () and _over.get("flipkart__S1", {}).get("returnsPct") == 150.0 and _over.get("flipkart__S2", {}).get("returnsPct") == 100.0)
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
      records.the_digest(today_record, leave_out=quality.NOT_IN_THE_DIGEST) == records.the_digest(merged, leave_out=quality.NOT_IN_THE_DIGEST)
      == records.the_digest(dict(today_record, fileDay="2026-10-26"), leave_out=quality.NOT_IN_THE_DIGEST))


# ---------------------------------------------------------------- what the record keeps of the one held

check("MERGE GIVES A NEW LISTING A HISTORY OF ONE READING, and a held listing's history its place",
      quality.merge(today_record, None)["history"] == [{"day": "2026-10-19", "stars": 4.2, "returnsPct": 17.6}]
      and [p["day"] for p in quality.merge(today_record, {"history": list(older)})["history"]] == ["2026-10-12", "2026-10-19"])

# ---------------------------------------------------------------- R20 proving: what each record holds, exactly
_qm, _qr = answered(lambda: quality.read_quality("fk_quality", "flipkart", table.read(("\n".join([
    HEAD,
    f'"Ring","SKU1","{RUPEE}1.2346K","4.2","9.1% | up 2%","Yes","Low","Quality"',
    '"","SKU2","","","9.1% |","Maybe","",""',
    f'"Big","SKU3","{RUPEE}1K","4","150%","No","",""',
]) + "\n").encode("utf-8")), "2026-10-19")) or ({}, ())
_qwant = {"platform": "flipkart", "report": "fk_quality", "sku": "SKU1", "fileDay": "2026-10-19", "product": "Ring", "yearlySales": 1235,
          "stars": 4.2, "returnsPct": 9.1, "returnsNote": "up 2%", "faBadge": True, "suppressionRisk": "Low", "issue": "Quality"}
check("A LISTING'S RECORD HOLDS EXACTLY WHAT THE ROW SAYS: rupees rounded to the nearest one after the K, the note after the bar, "
      "the badge as yes or no (R20 proving)",
      _qm.get("flipkart__SKU1") == dict(_qwant, digest=records.the_digest(_qwant, leave_out=quality.NOT_IN_THE_DIGEST)))
check("a row that says nothing in a cell writes nothing for it: no product, sales, stars, note, unknown badge word, risk or issue (R20 proving)",
      set(_qm.get("flipkart__SKU2", {})) == {"platform", "report", "sku", "fileDay", "returnsPct", "digest"})
check("a returns share above a hundred per cent is stored as the platform gave it, never refused (D561, A90; was R20 proving)",
      _qm.get("flipkart__SKU3", {}).get("returnsPct") == 150.0 and len(_qr) == 0)
_shuffled = tuple({"day": f"2026-09-{n:02d}", "stars": 4.0} for n in (7, 1, 13, 4, 10, 2, 12, 3, 9, 5, 11, 6, 8))
check("THE HISTORY KEEPS THE LAST TWELVE BY DAY, oldest dropped, whatever order they were held in (R20 proving)",
      [p["day"] for p in quality.with_history(dict(today_record, fileDay="2026-10-01"), _shuffled)["history"]]
      == [f"2026-09-{n:02d}" for n in range(3, 14)] + ["2026-10-01"])
for _gone in ("FA badge", "Issue Details"):
    check(f"a file without the {_gone} column is refused in words (R20 proving)",
          "Nothing was read" in str(caught(lambda g=_gone: quality.read_quality("fk_quality", "flipkart", table.read(
              (HEAD.replace(f'"{g}"', '"X"') + "\n").encode("utf-8")), "2026-10-19"))))

# ---------------------------------------------------------------- N025: MEESHO'S PRODUCT QUALITY PAGE, one file a day
# **THE FILE IS WHAT THE WALK WRITES FROM HIS PAGE (seen 26 Oct 2026; every figure here is made up):** `Kind` is store / feedback / tab / product; the products carry their tab, name, Style ID, band, own percentage and reasons.
MQ_HEAD = '"Kind","Tab","Name","Style ID","Band","Percent","Count","Detail"'


def mq_file(*lines):
    return table.read(("\n".join([MQ_HEAD, *lines]) + "\n").encode("utf-8"))


_MQ = (
    '"store","","Quality score","","Good","15.0","307","46 of 307 ratings were 1 or 2 stars"',
    '"feedback","","Color is not good","","","","2",""',
    '"feedback","","Design is not good","","","","1",""',
    '"tab","Blocking Soon","","","","","0",""', '"tab","Action Pending","","","","","2",""', '"tab","Fixed","","","","","1",""',
    '"product","Action Pending","Traditional Jhumka ...","DJ-5 Test Five","Yellow","19.7","9","Color is not good (5 ratings) | Size is not proper (4 ratings)"',
    '"product","Action Pending","Ethnic Drops ...","DJ-6 Test Six","Green","12","5","Size is not proper (5 ratings)"',
    '"product","Fixed","Gold Hoops ...","DJ-7 Test Seven","Green","3.5","0",""',
)
_mq, _mq_bad = answered(lambda: quality.read_meesho_quality("me_quality", "meesho", mq_file(*_MQ), "2026-10-26")) or ({}, ())
_mq_store = _mq.get("meesho__store", {})
_mq_want = {"platform": "meesho", "report": "me_quality", "kind": "store", "percent": 15.0, "band": "Good", "lowRatings": 46, "totalRatings": 307,
            "blockingSoon": 0, "actionPending": 2, "fixed": 1,
            "topFeedback": [{"reason": "Color is not good", "products": 2}, {"reason": "Design is not good", "products": 1}], "fileDay": "2026-10-26"}
check("THE STORE IS ONE RECORD, meesho__store: its score as a percentage, band, low and total ratings, the three tab counts and the top feedback reasons with their product counts, and the fingerprint of all of it",
      _mq_store == dict(_mq_want, digest=records.the_digest(_mq_want)) and _mq_bad == ())
_mq_p = _mq.get("meesho__DJ-5 Test Five", {})
_mq_pwant = {"platform": "meesho", "report": "me_quality", "kind": "product", "styleId": "DJ-5 Test Five", "product": "Traditional Jhumka ...", "tab": "Action Pending", "band": "Yellow",
             "percent": 19.7, "reasons": [{"reason": "Color is not good", "ratings": 5}, {"reason": "Size is not proper", "ratings": 4}], "fileDay": "2026-10-26"}
check("EVERY PRODUCT IS A RECORD OF ITS OWN named by its Style ID, with its tab, band, own percentage and its reasons as reason and number of ratings",
      {k: v for k, v in _mq_p.items() if k not in ("digest", "history")} == _mq_pwant and set(_mq) == {"meesho__store", "meesho__DJ-5 Test Five", "meesho__DJ-6 Test Six", "meesho__DJ-7 Test Seven"})
check("a product with no reasons has an empty list, and a tab with none of its products is only a count on the store",
      _mq["meesho__DJ-7 Test Seven"]["reasons"] == [] and _mq_store["blockingSoon"] == 0)
check("every field of every record is one the quality record kind accepts", all(set(r) <= set(quality.QUALITY_FIELDS) for r in _mq.values()))
_mq_dup, _mq_dup_said = answered(lambda: quality.read_meesho_quality("me_quality", "meesho", mq_file(*_MQ, '"product","Fixed","Gold Hoops ...","DJ-7 Test Seven","Green","3.5","0",""'), "2026-10-26")) or ({}, ())
check("a product named twice (it is on two tabs) is one record, the later line standing, and it is said", len(_mq_dup_said) == 1 and _mq_dup["meesho__DJ-7 Test Seven"]["tab"] == "Fixed")
_mq_nostore = answered(lambda: quality.read_meesho_quality("me_quality", "meesho", mq_file(*_MQ[1:]), "2026-10-26")) or ({}, ())
check("a file with no store line is refused by name, the products still read", len(_mq_nostore[1]) == 1 and "store" in _mq_nostore[1][0] and "meesho__DJ-5 Test Five" in _mq_nostore[0])
_mq_badpct = answered(lambda: quality.read_meesho_quality("me_quality", "meesho", mq_file(_MQ[0], '"product","Fixed","X","DJ-9 Test Nine","Green","lots","0",""', '"product","Fixed","Y","DJ-8 / Bad","Green","3","0",""'), "2026-10-26")) or ({}, ())
check("a product with an unreadable percentage, or a Style ID that cannot name a record, is refused by name and the rest read", len(_mq_badpct[1]) == 2)
check("a file without the quality columns is refused in words naming what it has", "Nothing was read" in str(caught(lambda: quality.read_meesho_quality("me_quality", "meesho", table.read(b"A,B\n1,2\n"), "2026-10-26"))))
_held_mq = {"history": [{"day": "2026-10-25", "percent": 20.0}]}
check("a product's percentage goes into its short history the way a listing's stars do, one point a day",
      [p.get("percent") for p in quality.merge(_mq_p, _held_mq)["history"]] == [20.0, 19.7])

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 14 + 6 + 1 + 9
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")
print(f"\n{len(failures)} FAILED: {failures}" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
