"""Checks for the one-record-per-platform-per-month summary of ads (A87, D463).

Run: python autosync/ads_month_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ads  # noqa: E402
import fake_firestore  # noqa: E402
import firestore  # noqa: E402
import firestore_door  # noqa: E402
import reading  # noqa: E402
import table  # noqa: E402
import whats_new  # noqa: E402

ran = 0
failures = []
THREW = []


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


# ---------------------------------------------------------------- the month, built from its days

DAY_10 = {"platform": "flipkart", "day": "2026-10-10", "campaigns": {"C1": {"spend": 5.0, "views": 100}}}
DAY_11 = {"platform": "flipkart", "day": "2026-10-11", "campaigns": {"C1": {"spend": 7.5, "views": 90}, "C2": {"spend": 1.0}}}
SEARCH_10 = {"platform": "flipkart", "day": "2026-10-10", "kind": "search", "rows": [{"campaignId": "C1", "query": "jhumka", "spend": 2.0}]}
SEARCH_11 = {"platform": "flipkart", "day": "2026-10-11", "kind": "search", "rows": [{"campaignId": "C1", "query": "jhumka", "spend": 3.0}]}
OVERALL_C1 = {"platform": "flipkart", "day": "2026-10-11", "kind": "overall", "campaignId": "C1", "rows": [{"campaignId": "C1", "skuId": "A"}]}
OVERALL_C2 = {"platform": "flipkart", "day": "2026-10-11", "kind": "overall", "campaignId": "C2", "rows": [{"campaignId": "C2", "skuId": "B"}]}
MEESHO_LIFE = {"platform": "meesho", "day": "2026-10-14", "kind": "lifetime", "rows": [{"campaignId": "M1", "spend": 5649.58}]}
DETAILS = [SEARCH_10, SEARCH_11, OVERALL_C1, OVERALL_C2, MEESHO_LIFE]

month = answered(lambda: ads.build_month("flipkart", "2026-10", {"2026-10-10": DAY_10, "2026-10-11": DAY_11}, DETAILS, "2026-10-20"))
check("THE MONTH KEEPS EVERY DAY AS A DAY, the campaigns as each day's record holds them",
      month is not None and month["days"] == {"10": DAY_10["campaigns"], "11": DAY_11["campaigns"]}
      and (month["platform"], month["month"], month["updatedOn"]) == ("flipkart", "2026-10", "2026-10-20"))
check("NOTHING IS SUMMED OVER THE MONTH: each day's search rows stay under that day, so a 7-day period can still be answered",
      month["search"] == {"10": SEARCH_10["rows"], "11": SEARCH_11["rows"]})
check("a day's `overall` rows of every campaign are together under the day, each carrying its campaign",
      sorted(row["campaignId"] for row in month["overall"]["11"]) == ["C1", "C2"])
check("another platform's records are left out of this platform's month", month["lifetime"] == {})
meesho = answered(lambda: ads.build_month("meesho", "2026-10", {}, DETAILS, "2026-10-20"))
check("and Meesho's campaigns-so-far are its own month's `lifetime`, per read day", meesho is not None and meesho["lifetime"] == {"14": MEESHO_LIFE["rows"]})
check("a record outside the month is not put in it",
      ads.build_month("flipkart", "2026-09", {}, [SEARCH_10], "2026-10-20")["search"] == {})
too_big = caught(lambda: ads.build_month(
    "flipkart", "2026-10", {}, [dict(SEARCH_10, rows=[{"campaignId": "C", "query": "x" * 1000, "n": n} for n in range(2000)])], "2026-10-20"))
check("A MONTH TOO BIG FOR ONE RECORD IS REFUSED IN WORDS, never shortened",
      too_big is not None and "would make a summary" in str(too_big))
check("the record's fields are ones the writer allows",
      set(month) <= set(ads.MONTH_FIELDS) and firestore.a_record_write("p", ads.MONTH, "flipkart__2026-10", month) is not None)
check("a field outside the list is refused by the writer", caught(lambda: firestore.a_record_write("p", ads.MONTH, "x", dict(month, secret=1))) is not None)


# ---------------------------------------------------------------- the sink, against a stand-in database


def database(days, details, months=()):
    return fake_firestore.FakeFirestore({
        firestore.ADS_DAYS: {f"{d['platform']}__{d['day']}": d for d in days},
        firestore.ADS_DETAIL: {f"{d['platform']}__{d['day']}__{d['kind']}__{n}": d for n, d in enumerate(details)},
        firestore.ADS_MONTH: {name: {"platform": name.split("__")[0]} for name in months},
    })


SEPT = {"platform": "flipkart", "day": "2026-09-30", "campaigns": {"C1": {"spend": 1.0}}}

backfill = database([DAY_10, DAY_11, SEPT], DETAILS)
wrote = answered(lambda: firestore_door.an_ads_month_sink(backfill, "p", "2026-10-20")(()))
got = backfill.written()
check("THE FIRST RUN BACKFILLS EVERY MONTH THAT ALREADY HAS DAY RECORDS, though tonight touched none",
      wrote == 2 and set(got) == {"flipkart__2026-10", "flipkart__2026-09"})
check("and each month holds what its days hold, read back from the database",
      got["flipkart__2026-10"]["days"]["11"] == DAY_11["campaigns"] and got["flipkart__2026-10"]["search"]["10"] == SEARCH_10["rows"]
      and got["flipkart__2026-09"]["days"] == {"30": SEPT["campaigns"]})
check("each month is two bounded queries, never the whole of the collection",
      len([p for p in backfill.posts if p["url"].endswith(":runQuery") and "where" in p["json"]["structuredQuery"]]) == 4)

later = database([DAY_10, DAY_11, SEPT], DETAILS, months=("flipkart__2026-10", "flipkart__2026-09"))
wrote_later = answered(lambda: firestore_door.an_ads_month_sink(later, "p", "2026-10-21")((("flipkart", "2026-10"),)))
check("ONCE A MONTH RECORD EXISTS ONLY THE MONTHS TONIGHT TOUCHED ARE REBUILT, and an untouched month is not rewritten",
      wrote_later == 1 and set(later.written()) == {"flipkart__2026-10"})
quiet = database([DAY_10], DETAILS, months=("flipkart__2026-10",))
check("a night that touched no month writes nothing",
      answered(lambda: firestore_door.an_ads_month_sink(quiet, "p", "2026-10-21")(())) == 0 and quiet.written() == {})
huge = database(
    [DAY_10, SEPT], [dict(SEARCH_10, rows=[{"campaignId": "C", "query": "x" * 1000, "n": n} for n in range(2000)]), SEARCH_11],
    months=("flipkart__2026-10", "flipkart__2026-09"))
huge_said = caught(lambda: firestore_door.an_ads_month_sink(huge, "p", "2026-10-21")((("flipkart", "2026-10"), ("flipkart", "2026-09"))))
check("A MONTH TOO BIG IS SAID AFTER THE OTHERS ARE WRITTEN, not swallowed and not taking them down",
      huge_said is not None and "would make a summary" in str(huge_said) and set(huge.written()) == {"flipkart__2026-09"})
check("the size is counted the way Firestore counts it, more than the plain text (a figure is 8 bytes, a name is its bytes + 1)",
      ads.firestore_size({"abc": [1, 2, "xy"]}) == 32 + 4 + 8 + 8 + 3)

# A backfill cut off part way is finished by the next night, though some month records now exist.
cut_off = database([DAY_10, SEPT], DETAILS, months=("flipkart__2026-10",))
check("A BACKFILL CUT OFF PART WAY IS FINISHED THE NEXT NIGHT: a month with days but no record is built although others exist",
      answered(lambda: firestore_door.an_ads_month_sink(cut_off, "p", "2026-10-21")(())) == 1 and set(cut_off.written()) == {"flipkart__2026-09"})
TRIMMED = dict(SEARCH_10, rowsInFile=900, rowsKept=700)
month_trim = answered(lambda: ads.build_month("flipkart", "2026-10", {"2026-10-10": DAY_10}, [TRIMMED, SEARCH_11], "2026-10-20"))
check("A DAY THAT WAS HELD TO SIZE SAYS SO IN THE MONTH, so the month never looks more complete than its days",
      month_trim is not None and month_trim["trimmed"] == {"10": [{"kind": "search", "rowsInFile": 900, "rowsKept": 700}]}
      and "trimmed" not in month)
read_once = database([DAY_10], DETAILS + [MEESHO_LIFE], months=())
answered(lambda: firestore_door.an_ads_month_sink(read_once, "p", "2026-10-21")((("flipkart", "2026-10"), ("meesho", "2026-10"))))
check("a month is read once however many platforms touched it",
      len([p for p in read_once.posts if p["url"].endswith(":runQuery") and "where" in p["json"]["structuredQuery"]]) == 2)

# ---------------------------------------------------------------- the night hands it the months, and says when it fails

night_months = []
_files = {"fk_ads_daily": [whats_new.InTheFolder(which="d1", name="flipkart_fk_ads_daily_2026-10-11.csv", size=900)]}
BODY = ("Start Time, 2026-10-11\nEnd Time, 2026-10-11\n"
        "Campaign ID,Campaign Name,Ad Spend,Views,Clicks,Total Converted Units,Total Revenue (Rs.),Date\n"
        "C1,One,5,100,10,1,100,2026-10-11\n").encode("utf-8")
night = answered(lambda: reading.read_what_is_new(
    already_read=(), what_is_in_the_folder=lambda r: list(_files.get(r, ())), bring_it_back=lambda w: BODY,
    record_the_sales=lambda readings: None, record_ads=lambda *a: len(a[-1])))
check("A NIGHT THAT READS AN ADS FILE SAYS WHICH PLATFORM AND MONTH IT TOUCHED",
      night is not None and night.ads_months == (("flipkart", "2026-10"),))

# ---------------------------------------------------------------- R20 proving
def _a_day(platform, day, **more):
    return dict({"platform": platform, "day": day, "campaigns": {"C1": {"spend": 1.0}}}, **more)


edges = database([_a_day("flipkart", d) for d in ("2026-09-30", "2026-10-01", "2026-10-31", "2026-11-01")] + [_a_day("meesho", "2026-10-15")],
                 [], months=("flipkart__2026-09", "flipkart__2026-11", "meesho__2026-10"))
answered(lambda: firestore_door.an_ads_month_sink(edges, "p", "2026-11-02")((("flipkart", "2026-10"),)))
check("A MONTH HOLDS ITS FIRST AND ITS 31ST DAY and nothing of the month either side, nor another platform's day (R20 proving)",
      set(edges.written().get("flipkart__2026-10", {}).get("days", {})) == {"01", "31"})
check("and it is written into the month-of-ads collection itself (R20 proving)",
      edges.written_where() == {"flipkart__2026-10": firestore.ADS_MONTH})
odd_days = fake_firestore.FakeFirestore({firestore.ADS_DAYS: {"a": {"day": "2026-08-05", "campaigns": {"C": {"spend": 1}}},
                                                              "b": {"platform": "flipkart", "campaigns": {"C": {"spend": 1}}}}})
check("a day record with no platform, or no day, starts no month: no month is even asked for (R20 proving)",
      answered(lambda: firestore_door.an_ads_month_sink(odd_days, "p", "2026-10-21")(())) == 0 and odd_days.written() == {}
      and not [p for p in odd_days.posts if p["url"].endswith(":runQuery") and "where" in p["json"]["structuredQuery"]])
only_detail = database([], [SEARCH_10, dict(MEESHO_LIFE, day="2026-09-14")], months=("flipkart__2026-10",))
answered(lambda: firestore_door.an_ads_month_sink(only_detail, "p", "2026-10-21")(
    (("flipkart", "2026-10"), ("meesho", "2026-10"), ("flipkart", "2026-09"), ("amazon", "2026-10"))))
check("a month with ad detail but no day records is built; a wanted month where only ANOTHER platform has anything, or nothing at all, is not (R20 proving)",
      set(only_detail.written()) == {"flipkart__2026-10"})
two_wants = database([_a_day("flipkart", "2026-09-10"), _a_day("flipkart", "2026-10-10"), _a_day("meesho", "2026-09-10"), _a_day("meesho", "2026-10-10")],
                     [], months=("flipkart__2026-09", "flipkart__2026-10", "meesho__2026-09", "meesho__2026-10"))
answered(lambda: firestore_door.an_ads_month_sink(two_wants, "p", "2026-10-21")((("flipkart", "2026-10"), ("meesho", "2026-09"))))
check("each platform's month is built only where THAT platform wanted it (R20 proving)",
      set(two_wants.written()) == {"flipkart__2026-10", "meesho__2026-09"})
huge_first = database(
    [SEPT, DAY_10], [dict(SEARCH_10, day="2026-09-30", rows=[{"campaignId": "C", "query": "x" * 1000, "n": n} for n in range(2000)])],
    months=("flipkart__2026-10", "flipkart__2026-09"))
said_first = caught(lambda: firestore_door.an_ads_month_sink(huge_first, "p", "2026-10-21")((("flipkart", "2026-09"), ("flipkart", "2026-10"))))
check("a month too big that comes FIRST does not stop a later month being written (R20 proving)",
      said_first is not None and "would make a summary" in str(said_first) and set(huge_first.written()) == {"flipkart__2026-10"})
refusing = fake_firestore.FakeFirestore({firestore.ADS_DAYS: {"flipkart__2026-09-30": SEPT, "flipkart__2026-10-10": DAY_10},
                                         firestore.ADS_MONTH: {"flipkart__2026-09": {"platform": "flipkart"}, "flipkart__2026-10": {"platform": "flipkart"}}},
                                        refuse={"flipkart__2026-09"})
said_no = caught(lambda: firestore_door.an_ads_month_sink(refusing, "p", "2026-10-21")((("flipkart", "2026-09"), ("flipkart", "2026-10"))))
check("A MONTH THE DATABASE REFUSES IS SAID BY NAME, and the next month is still written (R20 proving)",
      isinstance(said_no, firestore_door.TheirDatabaseSaidNo) and "flipkart 2026-09" in str(said_no)
      and [p for p in refusing.posts if p["url"].endswith(":commit")][-1]["json"]["writes"][0]["update"]["name"].endswith("flipkart__2026-10"))
check("an answer to a query that is not a list stops the sink as the database's refusal (R20 proving)",
      isinstance(caught(lambda: firestore_door.an_ads_month_sink(fake_firestore.FakeFirestore(odd_query=True), "p", "2026-10-21")(())),
                 firestore_door.TheirDatabaseSaidNo))
check("the month with a day held to size goes through the real writer, its note of what was trimmed allowed (R20 proving)",
      month_trim is not None and firestore.a_record_write("p", ads.MONTH, "flipkart__2026-10", month_trim) is not None)
ORDERS_10 = {"platform": "flipkart", "day": "2026-10-10", "kind": "orders", "rows": [{"campaignId": "C1", "orderId": "OD1"}]}
check("ad orders are a kind of their own in the month (R20 proving)",
      ads.build_month("flipkart", "2026-10", {}, [ORDERS_10], "2026-10-20")["orders"] == {"10": ORDERS_10["rows"]})
shaped = ads.build_month("flipkart", "2026-10", {
    "2026-10-10": DAY_10, "2026-10-12": _a_day("meesho", "2026-10-12"), "2026-10-13": dict(_a_day("flipkart", "2026-10-13"), campaigns={}),
    "2026-10-14": dict(_a_day("flipkart", "2026-10-14"), campaigns=["C1"])}, [
    dict(OVERALL_C2, rows=[{"campaignId": "C2"}]), dict(OVERALL_C1, rows=[{"campaignId": "C1"}]), dict(SEARCH_10, kind="weird"),
    dict(SEARCH_10, rowsInFile=5, rowsKept=5), dict(SEARCH_11, rowsInFile=5), dict(SEARCH_11, rowsKept=5, day="2026-10-11"),
    dict(OVERALL_C1, day="2026-10-12", rowsInFile=9, rowsKept=3)], "2026-10-20")
check("a month keeps only this platform's days that hold a map of campaigns (R20 proving)", set(shaped["days"]) == {"10"})
check("a day's detail rows are in campaign order whatever order they came in, and an unknown kind is left out (R20 proving)",
      [r["campaignId"] for r in shaped["overall"]["11"]] == ["C1", "C2"] and "weird" not in shaped)
check("only a day held SHORT is noted as trimmed, with its campaign when it has one; a day missing either count is not (R20 proving)",
      shaped.get("trimmed") == {"12": [{"kind": "overall", "rowsInFile": 9, "rowsKept": 3, "campaignId": "C1"}]})
_pad0 = ads.firestore_size(ads.build_month("flipkart", "2026-10", {}, [dict(SEARCH_10, rows=[{"q": ""}])], "2026-10-20"))
_at_most = ads.MOST_MONTH_BYTES - _pad0
check("A MONTH OF EXACTLY THE LIMIT IS WRITTEN, ONE BYTE MORE IS REFUSED (R20 proving)",
      caught(lambda: ads.build_month("flipkart", "2026-10", {}, [dict(SEARCH_10, rows=[{"q": "x" * _at_most}])], "2026-10-20")) is None
      and caught(lambda: ads.build_month("flipkart", "2026-10", {}, [dict(SEARCH_10, rows=[{"q": "x" * (_at_most + 1)}])], "2026-10-20")) is not None
      and ads.MOST_MONTH_BYTES == 1000 * 1000)
check("the size counts names and text in BYTES, a yes/no or nothing as 1 (R20 proving)",
      ads.firestore_size({"\u00e9": "\u00e9\u00e9"}) == 32 + 3 + 5 and ads.firestore_size(True) == 1 and ads.firestore_size(None) == 1)

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 21 + 15
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")
print(f"\n{len(failures)} FAILED: {failures}" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
