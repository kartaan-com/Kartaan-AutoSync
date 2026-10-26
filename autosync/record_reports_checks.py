"""Checks for the ONE table, ONE reader branch and ONE sink that serve every report written as records (A87; his standing order D458 / D482).

What is true for all of them is checked here, once, over the whole table: the table is consistent, a sink writes only what is new or changed and never over a newer
file's, and the night reads each report's file, leaves it unread where there is nowhere to write it, and leaves it unread when the database says no. What is true of ONE
report (its columns, its parsing, what its merge keeps) is checked in that report's own checks file.

Run: python autosync/record_reports_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fake_firestore  # noqa: E402
import firestore  # noqa: E402
import firestore_door  # noqa: E402
import reading  # noqa: E402
import record_reports  # noqa: E402
import records  # noqa: E402
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


# One small real-shaped file for each report in the table: (file name, body).
CLAIM_HEAD = ('"S No","Product Name","SKU","Variation","Qty","Meesho PID","Order Number","Suborder Number","Ticket ID","Ticket Status","Created Date",'
              '"Issue","Last Update","Reopen Validity","CPP Flag"')
SAMPLES = {
    "me_claims": ("meesho_me_claims_2026-10-14.csv",
                  CLAIM_HEAD + '\n"1","","","","","","11","11_1","T1","Open","2026-09-22T19:59:37","wrong return","escalated","null",""\n'),
    "me_product_performance": (
        "meesho_me_product_performance_2026-10-19.csv",
        '"Range","Last updated","Product","Catalog ID","Rating","Views","Clicks","Orders","Conversions","Sales","Returns","Insights","Recommendations"\n'
        '"13th Oct \'26 - 19th Oct \'26","x","Gold Jhumka","","4.1","100 | 5.0%","10","1","10.0% | 2.0%","₹1,250.50","0.0%","",""\n'),
    "fk_quality_insights": (
        "flipkart_fk_quality_insights_2026-10-19.csv",
        '"Product","SKU ID","Yearly Sales","1Y Ratings Trend","5M Returns Trend","FA badge","Suppression Risk","Issue Details"\n'
        '"Rumee Jhumki","DJ-5 Bahubali","₹6.32L","4.2","17.6%","Yes","No Risk","Quality"\n'),
    "me_views": ("meesho_me_views_2026-10-20.csv", "Date,Views,Orders\n2026-10-14,52750,23\n"),
    # Amazon's Account Health day file (N018): the five labels the walk reads, the figures seen on his page on 26 Oct 2026.
    "az_health": (
        "amazon_az_health_2026-10-26.csv",
        "Date,Account Health Rating,Order Defect Rate,Late Dispatch Rate,Pre-fulfilment Cancel Rate,Valid Tracking Rate\n2026-10-26,204,0,1.8,0,100\n"),
    # Amazon's SAFE-T claims report (N018): the real header, one made-up row.
    "az_claims": (
        "amazon_az_claims_2026-10-26.csv",
        '"Order Date","Order ID","ASIN","Item name","Fulfillment Channel","Return Tracking ID","Return Status","Return Delivery Date","SAFE-T Claim ID","Claim Date",'
        '"Claim Filing Reason","Quantity In Claim","Currency","Claim amount","SAFE-T claim state","Appeal by/ Respond by date","Reimbursement amount (Product value)",'
        '"Reimbursement amount (Others)","Total Reimbursement amount","Date of reimbursement"\n'
        '"2026-09-23","403-1","B0X","Item","Easy Ship","515","Delivered to seller","2026-10-03","10000-20000-0000001","2026-10-05","I received damaged/ used item",'
        '"1","INR","246.79","Granted","2026-10-13","55.50","0.0","55.50","2026-10-06"\n'),
}
TABLE = record_reports.RECORD_REPORTS

# ---------------------------------------------------------------- the table is consistent

check("THE TABLE HAS A SAMPLE FILE FOR EVERY REPORT IT NAMES, so no report in it goes unchecked here",
      set(SAMPLES) == set(TABLE))
check("each report's records go in a collection the run may write, and every kind lists the fields every record has",
      all(one.kind.collection in firestore.WHAT_IT_MAY_WRITE and {"platform", "fileDay", "digest"} <= set(one.kind.fields) for one in TABLE.values()))
check("and no two KINDS of record write one collection (Meesho's and Amazon's claims are one kind, in one collection, by design, D459)",
      len({one.kind.collection for one in TABLE.values()}) == len({id(one.kind) for one in TABLE.values()}))
check("every report is read, by the ledger branch (claims) or by the one records branch, and none is also said to be waiting",
      all(rid in reading.what_this_can_read() or rid in {h.report_id for h in reading.WHAT_RECORDS_CAN_BE_READ} for rid in TABLE)
      and not set(TABLE) & set(reading.WHAT_IS_FETCHED_AND_NOT_READ_YET) and reading.why_a_report_has_no_decision() == "")
sinks = firestore_door.the_record_sinks(fake_firestore.FakeFirestore(), "p")
check("there is exactly one sink for each report in the table, built from the table", set(sinks) == set(TABLE))

# ---------------------------------------------------------------- the one sink

KIND = records.RecordKind(firestore.CLAIMS, ("platform", "claimKey", "status", "fileDay", "digest"), "claim")


def a_record(status, day="2026-10-14"):
    one = {"platform": "meesho", "claimKey": "T1", "status": status, "fileDay": day}
    one["digest"] = records.the_digest(one)
    return {"meesho__T1": one}


def held_as(status, day):
    return fake_firestore.FakeFirestore({firestore.CLAIMS: {"meesho__T1": a_record(status, day)["meesho__T1"]}})


fresh = fake_firestore.FakeFirestore()
check("RECORDS ARE ASKED ABOUT FIRST, THEN WRITTEN, in one call each, and the sink says how many",
      answered(lambda: firestore_door.a_records_sink(fresh, "p", KIND)("r", "2026-10-14", a_record("Open"))) == 1 and fresh.asked() == ["batchGet", "commit"])
same = held_as("Open", "2026-10-14")
check("a second run on the same file writes nothing",
      answered(lambda: firestore_door.a_records_sink(same, "p", KIND)("r", "2026-10-14", a_record("Open"))) == 0 and same.commits() == 0)
check("a later file's change replaces an earlier file's",
      answered(lambda: firestore_door.a_records_sink(held_as("Open", "2026-10-11"), "p", KIND)("r", "2026-10-14", a_record("Approved"))) == 1)
check("and an older file never puts a newer file's figures back",
      answered(lambda: firestore_door.a_records_sink(held_as("Approved", "2026-10-20"), "p", KIND)("r", "2026-10-14", a_record("Open"))) == 0)
merged = []
answered(lambda: firestore_door.a_records_sink(held_as("Open", "2026-10-11"), "p", KIND, lambda record, held: merged.append(held) or record)(
    "r", "2026-10-14", a_record("Approved")))
check("a kind's merge is handed the record already held, or nothing when there is none",
      len(merged) == 1 and merged[0]["status"] == "Open"
      and (answered(lambda: firestore_door.a_records_sink(fake_firestore.FakeFirestore(), "p", KIND, lambda record, held: merged.append(held) or record)(
          "r", "2026-10-14", a_record("Open"))), merged[-1])[1] is None)
check("a field the kind does not list is refused by the writer, naming it",
      "secret" in str(caught(lambda: firestore.a_record_write("p", KIND, "meesho__T1", dict(a_record("Open")["meesho__T1"], secret=1)))))
check("so is a record whose required day is not a day, and a month that is not one",
      caught(lambda: firestore.a_record_write("p", records.RecordKind(firestore.CLAIMS, ("fileDay",), "x", required_days=("fileDay",)), "a", {"fileDay": "soon"})) is not None
      and caught(lambda: firestore.a_record_write("p", records.RecordKind(firestore.CLAIMS, ("month",), "x", months=("month",)), "a", {"month": "2026"})) is not None)
check("a database that says no stops the sink with that said in words",
      "403" in str(caught(lambda: firestore_door.a_records_sink(fake_firestore.FakeFirestore(fail_on=403), "p", KIND)("r", "2026-10-14", a_record("Open")))))

# ---------------------------------------------------------------- the real kinds through the real sinks (merge runs BEFORE the fingerprint test)


def made_from_sample(report_id):
    name, body = SAMPLES[report_id]
    import table
    return TABLE[report_id].read(report_id, {"fk_quality_insights": "flipkart", "az_claims": "amazon", "az_health": "amazon"}.get(report_id, "meesho"), table.read(body.encode("utf-8")), name[-14:-4], None)[0]


def paid_claim_held():
    one = dict(made_from_sample("me_claims")["meesho__T1"], status="Approved", recovered="177.84", recoveredWas="100.00", fileDay="2026-10-11")
    return one


_reworded = {k: dict(v, status="Approved") for k, v in made_from_sample("me_claims").items()}  # says nothing of the amount
_for_claims = fake_firestore.FakeFirestore({firestore.CLAIMS: {"meesho__T1": dict(paid_claim_held(), digest="old")}})
answered(lambda: firestore_door.the_record_sinks(_for_claims, "p")["me_claims"]("me_claims", "2026-10-14", _reworded))
_after = _for_claims.written().get("meesho__T1", {})
check("A PAID CLAIM'S RUPEES AND THE NOTE OF WHAT THEY REPLACED SURVIVE A REWORDED LATER FILE, through the real kind, merge and sink",
      _after.get("recovered") == "177.84" and _after.get("recoveredWas") == "100.00" and _after.get("status") == "Approved")
_settled = fake_firestore.FakeFirestore({firestore.CLAIMS: {"meesho__T1": dict(_after)}})
check("and the same file read again writes nothing, because the merge ran before the fingerprints were compared",
      answered(lambda: firestore_door.the_record_sinks(_settled, "p")["me_claims"]("me_claims", "2026-10-14", _reworded)) == 0)
_for_quality = fake_firestore.FakeFirestore()
answered(lambda: firestore_door.the_record_sinks(_for_quality, "p")["fk_quality_insights"]("fk_quality_insights", "2026-10-19", made_from_sample("fk_quality_insights")))
check("A LISTING'S QUALITY IS WRITTEN WITH ITS HISTORY, through the real kind, merge and sink",
      _for_quality.written()["flipkart__DJ-5 Bahubali"]["history"] == [{"day": "2026-10-19", "stars": 4.2, "returnsPct": 17.6}])

# ---------------------------------------------------------------- the one night branch, for every report


def a_night(report_id, sinks_given):
    name, body = SAMPLES[report_id]
    return answered(lambda: reading.read_what_is_new(
        already_read=(), what_is_in_the_folder=lambda r: [whats_new.InTheFolder(which="f1", name=name, size=900)] if r == report_id else [],
        bring_it_back=lambda w: body.encode("utf-8"), record_the_sales=lambda readings: None, record_records=sinks_given))


for report_id in TABLE:
    handed = []
    night = a_night(report_id, {report_id: lambda rid, day, made, handed=handed: handed.append((rid, day, sorted(made))) or len(made)})
    check(f"{report_id}: THE NIGHT READS ITS FILE, hands its records to its sink under the file's day, counts them, and the file is read",
          night is not None and night.read_tonight == ("f1",) and night.wrote(report_id) == 1 and len(handed) == 1 and handed[0][1] == SAMPLES[report_id][0][-14:-4])
    nowhere = a_night(report_id, None)
    check(f"{report_id}: with nowhere to write its records the file is left unread, not lost",
          nowhere is not None and nowhere.read_tonight == () and nowhere.waiting(report_id) == 1 and "left unread" in nowhere.says())

    def _says_no(rid, day, made):
        raise firestore_door.TheirDatabaseSaidNo("no")

    refused = a_night(report_id, {report_id: _says_no})
    check(f"{report_id}: a database that says no leaves the file unread and says so as the database's refusal",
          refused is not None and refused.read_tonight == () and len(refused.the_database_refused) == 1)

# ---------------------------------------------------------------- R20 proving: the shared helpers every record reader uses
import table  # noqa: E402

check("a fingerprint is sixteen characters (R20 proving)", len(records.the_digest({"a": 1})) == 16)
check("a figure that is not finite is refused, NaN and Infinity alike (R20 proving)",
      all(caught(lambda s=s: records.a_figure(s)) is not None for s in ("Infinity", "NaN", "-Infinity")))
check("a figure exactly at its most is taken, one past it refused (R20 proving)",
      records.a_figure("5", most=5) == 5 and caught(lambda: records.a_figure("5.01", most=5)) is not None)
check("a whole count with a fraction is refused (R20 proving)", caught(lambda: records.a_figure("12.5", whole=True)) is not None)
check("a name is measured in BYTES: a thousand bytes is allowed, a thousand and one is not, however few the characters (R20 proving)",
      records.a_safe_name("a" * 1000) and not records.a_safe_name("a" * 1001) and not records.a_safe_name("\u00e9" * 501))
_said_no = caught(lambda: records.require_columns(table.read(b"A,,B\n1,2,3\n"), ("Z",), "a test file"))
check("a refusal names the columns the file has, leaving out blank ones (R20 proving)",
      _said_no is not None and "It has: 'A', 'B'." in str(_said_no))
check("the shop days are kept as said, with nothing of another reader's history merged into them, and summed up in their own words (R20 proving)",
      record_reports.RECORD_REPORTS["me_views"].merge is None and record_reports.RECORD_REPORTS["me_views"].label == "shop day(s)")

# ---------------------------------------------------------------- R20 proving: the record writer's own locks
import ads  # noqa: E402
import claims  # noqa: E402
import performance  # noqa: E402

_claim = {"platform": "meesho", "report": "me_claims", "claimKey": "T1", "orderId": "1_1", "fileDay": "2026-10-14", "digest": "d"}
check("the writer refuses an optional day that is not a day (R20 proving)",
      caught(lambda: firestore.a_record_write("p", claims.KIND, "meesho__T1", dict(_claim, raisedOn="soon"))) is not None
      and caught(lambda: firestore.a_record_write("p", claims.KIND, "meesho__T1", _claim)) is None)
check("the writer refuses a record missing a day it must carry (R20 proving)",
      caught(lambda: firestore.a_record_write("p", performance.KIND, "x", {"platform": "meesho", "weekFrom": "2026-10-13", "fileDay": "2026-10-20"})) is not None)
check("the writer refuses a month with anything after the month (R20 proving)",
      caught(lambda: firestore.a_record_write("p", ads.MONTH, "x", {"platform": "f", "month": "2026-10-xx", "updatedOn": "2026-10-20"})) is not None)
check("EVERY RECORD IS WRITTEN INTO ITS OWN KIND'S COLLECTION (R20 proving)",
      all(firestore.a_record_write("p", one.kind, "n", {}).get("update", {}).get("name", "").endswith(f"/documents/{one.kind.collection}/n")
          for one in record_reports.RECORD_REPORTS.values() if not one.kind.required_days)
      and firestore.a_record_write("p", claims.KIND, "n", _claim)["update"]["name"].endswith(f"/documents/{firestore.CLAIMS}/n"))

# ---------------------------------------------------------------- R20 proving: the records branch of the night


def _views_night(bodies, sinks=None, more=None):
    files = [whats_new.InTheFolder(which=w, name=f"meesho_me_views_2026-10-{20 + n}.csv", size=9) for n, w in enumerate(sorted(bodies))]
    listed = dict({"me_views": files}, **(more or {}))
    fetched = []
    said = answered(lambda: reading.read_what_is_new(
        already_read=(), what_is_in_the_folder=lambda r: list(listed.get(r, ())),
        bring_it_back=lambda w: fetched.append(w) or bodies.get(w, b""), record_the_sales=lambda readings: None,
        record_records={"me_views": lambda rid, day, made: len(made)} if sinks is None else sinks))
    return said, fetched


_all_bad, _ = _views_night({"v1": b"Date,Views,Orders\nsoon,1,1\n"})
check("A RECORDS FILE WHOSE EVERY ROW IS REFUSED IS NOT READ, so it is opened again (R20 proving)",
      _all_bad is not None and _all_bad.read_tonight == ())
_part, _fetched = _views_night({"v1": b"Date,Views,Orders\nsoon,1,1\n2026-10-14,5,1\n"},
                               more={"me_catalog": [whats_new.InTheFolder(which="cat", name="meesho_me_catalog_2026-10-20.xlsx", size=9)]})
check("a file with SOME rows refused is read, the refused counted and said by line (R20 proving)",
      _part is not None and _part.read_tonight == ("v1",) and _part.rows_refused == 1 and any("1 row(s) not read" in x for x in _part.could_not_read))
_vread = [r for r in (_part.reads if _part else ()) if r.report_id == "me_views"]
check("and its record of what was opened says two rows held, one read, so it shows as landed-not-read (R20 proving)",
      len(_vread) == 1 and (_vread[0].rows_in_file, _vread[0].rows_read) == (2, 1))
check("a report that does not match catalog titles never downloads the catalog (R20 proving)", _fetched == ["v1"])
_two, _ = _views_night({"v1": b"Date,Views,Orders\n2026-10-14,5,1\n", "v2": b"Date,Views,Orders\n2026-10-15,5,1\n"})
check("two files of one records report in one night: what they wrote is added up, and said in the report's own words (R20 proving)",
      _two is not None and _two.wrote("me_views") == 2
      and "  2 shop day(s) were new or changed in the shop figures files and were recorded." in _two.says())
_two_wait, _ = _views_night({"v1": b"Date,Views,Orders\n2026-10-14,5,1\n", "v2": b"Date,Views,Orders\n2026-10-15,5,1\n"}, sinks={})
check("and with nowhere to write, both files are counted as waiting, in the report's words (R20 proving)",
      _two_wait is not None and _two_wait.waiting("me_views") == 2
      and "  2 shop figures file(s) were left unread because the seller's database could not be reached" in _two_wait.says())
_cats = []
_real_listings = reading.a_listings_reading
try:
    reading.a_listings_reading = lambda how, one, body: _cats.append(one.which) or (type("R", (), {"records": {}})(), "x")
    answered(lambda: reading.write_the_records(
        next(h for h in reading.WHAT_RECORDS_CAN_BE_READ if h.report_id == "me_product_performance"),
        whats_new.InTheFolder(which="pp", name="meesho_me_product_performance_2026-10-19.csv", size=9), SAMPLES["me_product_performance"][1].encode("utf-8"),
        "2026-10-19", lambda rid, day, made: len(made),
        {"me_catalog": [whats_new.InTheFolder(which="undated", name="meesho_me_catalog.xlsx", size=9),
                        whats_new.InTheFolder(which="cat-a", name="meesho_me_catalog_2026-10-18.xlsx", size=9),
                        whats_new.InTheFolder(which="cat-b", name="meesho_me_catalog_2026-10-18.xlsx", size=9)]},
        lambda w: b""))
finally:
    reading.a_listings_reading = _real_listings
check("the titles come from the newest DATED catalog file, Drive's id breaking a tie of one day (R20 proving)", _cats == ["cat-b"])
check("the reading rules carry this release's change, so files read under the old rules are read once more (R20 proving)",
      reading.READING_RULES.endswith("-returns-in-the-ledger-a87"))
_orders_key = reading._which_day_it_is_about((next(h for h in reading.WHAT_CAN_BE_READ if h.report_id == "me_orders"),
                                              whats_new.InTheFolder(which="o", name="meesho_me_orders_2026-10-20.csv", size=9)))
_claims_key = reading._which_day_it_is_about((next(h for h in reading.WHAT_CAN_BE_READ if h.report_id == "me_claims"),
                                              whats_new.InTheFolder(which="c", name="meesho_me_claims_2026-10-01.csv", size=9)))
check("a claims file is read after every orders file, whatever day each is about (R20 proving)", _claims_key > _orders_key)

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 17 + 3 * len(TABLE) + 7 + 4 + 9
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")
print(f"\n{len(failures)} FAILED: {failures}" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
