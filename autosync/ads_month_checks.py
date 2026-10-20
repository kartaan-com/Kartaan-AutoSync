"""Checks for the one-record-per-platform-per-month summary of ads (A87, D463).

Run: python autosync/ads_month_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ads  # noqa: E402
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
      set(month) <= set(ads.MONTH_FIELDS) and firestore.a_ads_month_write("p", "flipkart__2026-10", month) is not None)
check("a field outside the list is refused by the writer", caught(lambda: firestore.a_ads_month_write("p", "x", dict(month, secret=1))) is not None)


# ---------------------------------------------------------------- the sink, against a stand-in database


class Reply:
    def __init__(self, status=200, body=None):
        self.status, self._body, self.text = status, body if body is not None else {}, str(body or "")

    ok = property(lambda self: 200 <= self.status < 300)

    def json(self):
        return self._body

    def records(self):
        return self._body if isinstance(self._body, list) else None


class Database:
    """Answers runQuery by collection (and a `day` range when one is asked), and keeps what was committed."""

    def __init__(self, days, details, months=()):
        self.collections = {
            firestore.ADS_DAYS: {f"{d['platform']}__{d['day']}": d for d in days},
            firestore.ADS_DETAIL: {f"{d['platform']}__{d['day']}__{d['kind']}__{n}": d for n, d in enumerate(details)},
            firestore.ADS_MONTH: {name: {"platform": name.split("__")[0]} for name in months},
        }
        self.posts = []

    def post(self, url, params=None, headers=None, json=None, data=None):
        self.posts.append({"url": url, "json": json})
        if url.endswith(":runQuery"):
            query = json["structuredQuery"]
            docs = self.collections[query["from"][0]["collectionId"]]
            low = high = None
            if "where" in query:
                for one in query["where"]["compositeFilter"]["filters"]:
                    f = one["fieldFilter"]
                    if f["op"] == "GREATER_THAN_OR_EQUAL":
                        low = f["value"]["stringValue"]
                    else:
                        high = f["value"]["stringValue"]
            out = []
            for name, record in sorted(docs.items()):
                if low is not None and not (low <= str(record.get("day", "")) <= high):
                    continue
                out.append({"document": {"name": f"projects/p/databases/(default)/documents/x/{name}",
                                         "fields": firestore.a_deep(record)["mapValue"]["fields"]}})
            return Reply(200, out)
        return Reply(200, {})

    def written(self):
        out = {}
        for post in self.posts:
            if post["url"].endswith(":commit"):
                for write in post["json"]["writes"]:
                    out[write["update"]["name"].rsplit("/", 1)[-1]] = firestore.plain_deep({"mapValue": {"fields": write["update"]["fields"]}})
        return out


SEPT = {"platform": "flipkart", "day": "2026-09-30", "campaigns": {"C1": {"spend": 1.0}}}

backfill = Database([DAY_10, DAY_11, SEPT], DETAILS)
wrote = answered(lambda: firestore_door.an_ads_month_sink(backfill, "p", "2026-10-20")(()))
got = backfill.written()
check("THE FIRST RUN BACKFILLS EVERY MONTH THAT ALREADY HAS DAY RECORDS, though tonight touched none",
      wrote == 2 and set(got) == {"flipkart__2026-10", "flipkart__2026-09"})
check("and each month holds what its days hold, read back from the database",
      got["flipkart__2026-10"]["days"]["11"] == DAY_11["campaigns"] and got["flipkart__2026-10"]["search"]["10"] == SEARCH_10["rows"]
      and got["flipkart__2026-09"]["days"] == {"30": SEPT["campaigns"]})
check("each month is two bounded queries, never the whole of the collection",
      len([p for p in backfill.posts if p["url"].endswith(":runQuery") and "where" in p["json"]["structuredQuery"]]) == 4)

later = Database([DAY_10, DAY_11, SEPT], DETAILS, months=("flipkart__2026-10", "flipkart__2026-09"))
wrote_later = answered(lambda: firestore_door.an_ads_month_sink(later, "p", "2026-10-21")((("flipkart", "2026-10"),)))
check("ONCE A MONTH RECORD EXISTS ONLY THE MONTHS TONIGHT TOUCHED ARE REBUILT, and an untouched month is not rewritten",
      wrote_later == 1 and set(later.written()) == {"flipkart__2026-10"})
quiet = Database([DAY_10], DETAILS, months=("flipkart__2026-10",))
check("a night that touched no month writes nothing",
      answered(lambda: firestore_door.an_ads_month_sink(quiet, "p", "2026-10-21")(())) == 0 and quiet.written() == {})
huge = Database(
    [DAY_10, SEPT], [dict(SEARCH_10, rows=[{"campaignId": "C", "query": "x" * 1000, "n": n} for n in range(2000)]), SEARCH_11],
    months=("flipkart__2026-10", "flipkart__2026-09"))
huge_said = caught(lambda: firestore_door.an_ads_month_sink(huge, "p", "2026-10-21")((("flipkart", "2026-10"), ("flipkart", "2026-09"))))
check("A MONTH TOO BIG IS SAID AFTER THE OTHERS ARE WRITTEN, not swallowed and not taking them down",
      huge_said is not None and "would make a summary" in str(huge_said) and set(huge.written()) == {"flipkart__2026-09"})
check("the size is counted the way Firestore counts it, more than the plain text (a figure is 8 bytes, a name is its bytes + 1)",
      ads.firestore_size({"abc": [1, 2, "xy"]}) == 32 + 4 + 8 + 8 + 3)

# A backfill cut off part way is finished by the next night, though some month records now exist.
cut_off = Database([DAY_10, SEPT], DETAILS, months=("flipkart__2026-10",))
check("A BACKFILL CUT OFF PART WAY IS FINISHED THE NEXT NIGHT: a month with days but no record is built although others exist",
      answered(lambda: firestore_door.an_ads_month_sink(cut_off, "p", "2026-10-21")(())) == 1 and set(cut_off.written()) == {"flipkart__2026-09"})
TRIMMED = dict(SEARCH_10, rowsInFile=900, rowsKept=700)
month_trim = answered(lambda: ads.build_month("flipkart", "2026-10", {"2026-10-10": DAY_10}, [TRIMMED, SEARCH_11], "2026-10-20"))
check("A DAY THAT WAS HELD TO SIZE SAYS SO IN THE MONTH, so the month never looks more complete than its days",
      month_trim is not None and month_trim["trimmed"] == {"10": [{"kind": "search", "rowsInFile": 900, "rowsKept": 700}]}
      and "trimmed" not in month)
read_once = Database([DAY_10], DETAILS + [MEESHO_LIFE], months=())
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

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 21
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")
print(f"\n{len(failures)} FAILED: {failures}" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
