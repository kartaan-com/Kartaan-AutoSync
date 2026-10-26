"""Checks for reading a claims file into the ledger's claim columns (A87; Meesho first).

The columns are from his real files (`meesho_me_claims_2026-10-14.csv`, 154 rows); the fixtures below carry the same header and the message
shapes that file really has.

Run: python autosync/claims_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claims  # noqa: E402
import ledger  # noqa: E402
import reading  # noqa: E402
import record_reports  # noqa: E402
import records  # noqa: E402
import sales  # noqa: E402
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


HEAD = ('"S No","Product Name","SKU","Variation","Qty","Meesho PID","Order Number","Suborder Number","Ticket ID","Ticket Status",'
        '"Created Date","Issue","Last Update","Reopen Validity","CPP Flag"')


def line(sub, ticket, status, created, message=""):
    return (f'"1","","","","","","{sub.split("_")[0]}","{sub}","{ticket}","{status}","{created}",'
            f'"Item/s are missing in my return","{message}","null",""')


def file_of(*lines):
    return table.read(("\n".join([HEAD, *lines]) + "\n").encode("utf-8"))


PAID = "Your claim payment of Rs 177.84 for this order was done on 28 Sep 2026 with a transaction id: AXISCN1481062641"

# ---------------------------------------------------------------- what one file says

one = answered(lambda: claims.read_claims("meesho", file_of(
    line("11_1", "T1", "Approved", "2026-09-22T19:59:37", PAID),
    line("12_1", "T2", "Rejected", "2026-09-23T10:00:00", "Dear Seller, we regret to inform you"),
    line("13_1", "T3", "Open", "2026-09-24T10:00:00", "We have escalated your claim")), "2026-10-14"))
by = {s.order_id: s for s in (one.sales if one else ())}
check("A CLAIM IS KEPT BY ITS CLAIM ID, STATUS AND THE DAY OF THE FILE, on its sub-order",
      one is not None and by["11_1"].claim_id == "T1" and by["11_1"].claim_status == "Approved" and by["11_1"].claims_on == "2026-10-14"
      and by["13_1"].claim_status == "Open")
check("the rupees recovered are taken only from the platform's own words for paying, and a rejection or an open claim recovers nothing",
      by["11_1"].claim_recovered == "177.84" and by["12_1"].claim_recovered is None and by["13_1"].claim_recovered is None)
check("and the file has no SKU, so none is made up", all(s.sku == "" for s in by.values()))
check("a message that only looks like a payment is not one",
      claims.the_amount_paid("We will make a claim payment of Rs 5 soon", "Approved") == ""
      and claims.the_amount_paid(PAID, "Rejected") == "")

# ---------------------------------------------------------------- the same claim in many files (A86: 30-day downloads)

twice = answered(lambda: claims.read_claims("meesho", file_of(
    line("11_1", "T1", "Open", "2026-09-22T19:59:37", "escalated"),
    line("11_1", "T1", "Approved", "2026-09-22T19:59:37", PAID)), "2026-10-14"))
check("THE SAME CLAIM NAMED TWICE IN ONE FILE IS ONE CLAIM, the later line standing",
      twice is not None and len(twice.sales) == 1 and twice.sales[0].claim_status == "Approved")
two_claims = answered(lambda: claims.read_claims("meesho", file_of(
    line("14_1", "T7", "Rejected", "2026-08-22T19:55:58", ""),
    line("14_1", "T9", "Open", "2026-08-24T13:12:12", "escalated")), "2026-10-14"))
check("an order with two claims is the one raised last", two_claims is not None and len(two_claims.sales) == 1
      and two_claims.sales[0].claim_id == "T9")
refused = answered(lambda: claims.read_claims("meesho", file_of(
    line("15_1", "", "Open", "2026-09-24T10:00:00"), line("", "T5", "Open", "2026-09-24T10:00:00"),
    line("16_1", "T6", "Open", "2026-09-24T10:00:00")), "2026-10-14"))
check("a row with no claim id or no order is refused by name and the rest are read",
      refused is not None and len(refused.sales) == 1 and len(refused.not_read) == 2)
no_columns = caught(lambda: claims.read_claims("meesho", table.read(b"A,B\n1,2\n"), "2026-10-14"))
check("a file without the columns is refused in words, naming what it has",
      no_columns is not None and "Ticket ID" in str(no_columns) and "Nothing was read" in str(no_columns))

# ---------------------------------------------------------------- into the ledger: the LATEST FILE'S STATUS WINS

COLS = list(sales.COLUMNS)


def sheet_with_row(order, sku="RING"):
    row = sales.the_row_for(sales.Sale(platform="meesho", order_id=order, sku=sku, on="2026-09-20", qty=1, gmv="100"))
    return [COLS, list(row)]


def a_claims_reading(day, *those):
    return ledger.Reading(report="me_claims", on=day, knows=reading.WHAT_CLAIMS_KNOW, sales=tuple(those), which=day, only_existing=True)


earlier = claims.read_claims("meesho", file_of(line("11_1", "T1", "Open", "2026-09-22T19:59:37", "escalated")), "2026-10-11").sales
later = claims.read_claims("meesho", file_of(line("11_1", "T1", "Approved", "2026-09-22T19:59:37", PAID)), "2026-10-14").sales
first = answered(lambda: ledger.plan(sheet_with_row("11_1"), [a_claims_reading("2026-10-11", *earlier)]))
check("A CLAIM LANDS ON THE ONE ROW OF ITS SUB-ORDER although the claim names no SKU",
      first is not None and len(first.update) == 1 and first.unmatched == ())
after_first = [COLS, list(first.update[0][1])] if first and first.update else sheet_with_row("11_1")
row1 = dict(zip(COLS, after_first[1]))
check("with its id and status and the day of the file", row1["claimId"] == "T1" and row1["claimStatus"] == "Open" and row1["claimsOn"] == "2026-10-11")
second = answered(lambda: ledger.plan(after_first, [a_claims_reading("2026-10-14", *later)]))
row2 = dict(zip(COLS, second.update[0][1])) if second and second.update else {}
check("THE LATER FILE'S STATUS WINS, and the rupees recovered arrive with it",
      row2.get("claimStatus") == "Approved" and row2.get("claimRecovered") == "177.84" and row2.get("claimId") == "T1")
older_again = (answered(lambda: ledger.plan([COLS, list(second.update[0][1])], [a_claims_reading("2026-10-11", *earlier)]))
               if second and second.update else None)
check("and an OLDER file read after it does not put the claim back to Open",
      older_again is not None and older_again.update == ())
check("a claim for an order the sheet does not hold is said, never put on another row",
      (lambda p: p is not None and p.update == () and p.append == () and len(p.unmatched) == 1)(
          answered(lambda: ledger.plan(sheet_with_row("99_1"), [a_claims_reading("2026-10-14", *later)]))))
two_rows = [COLS, list(sheet_with_row("11_1", "A")[1]), list(sheet_with_row("11_1", "B")[1])]
check("and a claim cannot choose between two rows of one order",
      (lambda p: p is not None and p.update == () and len(p.unmatched) == 1)(
          answered(lambda: ledger.plan(two_rows, [a_claims_reading("2026-10-14", *later)]))))

# a different claim takes its own rupees: the old claim's money is not left beside the new claim's id
t1_on_11 = claims.read_claims("meesho", file_of(line("11_1", "T1", "Approved", "2026-09-22T19:59:37", PAID)), "2026-10-11").sales
t1_paid = answered(lambda: ledger.plan(sheet_with_row("11_1"), [a_claims_reading("2026-10-11", *t1_on_11)]))
sheet_paid = [COLS, list(t1_paid.update[0][1])] if t1_paid and t1_paid.update else sheet_with_row("11_1")
t2_open = claims.read_claims("meesho", file_of(
    line("11_1", "T1", "Approved", "2026-09-22T19:59:37", PAID),
    line("11_1", "T2", "Open", "2026-10-12T10:00:00", "escalated")), "2026-10-14").sales
t2 = answered(lambda: ledger.plan(sheet_paid, [a_claims_reading("2026-10-14", *t2_open)]))
row_t2 = dict(zip(COLS, t2.update[0][1])) if t2 and t2.update else {}
check("A NEW CLAIM ON THE ORDER TAKES THE OLD CLAIM'S RUPEES AWAY with its id (a paid claim's money is not shown beside another claim)",
      row_t2.get("claimId") == "T2" and row_t2.get("claimStatus") == "Open" and row_t2.get("claimRecovered") == "")
payment_no_sku = ledger.Reading(report="me_payments", on="2026-10-14", knows=("settlement", "paymentsOn"), only_existing=True, which="p",
                                sales=(sales.Sale(platform="meesho", order_id="11_1", sku="", settlement="5", payments_on="2026-10-14"),))
check("and a payment line with no SKU is still not placed by guessing: the SKU-less placement is for claims only",
      (lambda p: p is not None and p.update == () and len(p.unmatched) == 1)(answered(lambda: ledger.plan(sheet_with_row("11_1"), [payment_no_sku]))))
_fk_row = [COLS, list(sales.the_row_for(sales.Sale(platform="other", order_id="OD9", sku="RING", on="2026-09-20", qty=1, gmv="100")))]
_fk_claim = sales.Sale(platform="other", order_id="OD9", sku="", claim_id="F1", claim_status="Open", claims_on="2026-10-14")
check("a SKU-less claim is placed on an order's one row for MEESHO and FLIPKART only; a platform with no such rule is said (R20 proving, widened for Flipkart in v0.1.21 job 3)",
      (lambda p: p is not None and p.update == () and len(p.unmatched) == 1)(
          answered(lambda: ledger.plan(_fk_row, [a_claims_reading("2026-10-14", _fk_claim)]))))
_same_again = sales.Sale(platform="meesho", order_id="11_1", sku="", claim_id="T1", claim_status="Approved", claims_on="2026-10-15")
_kept = answered(lambda: ledger.plan(sheet_paid, [a_claims_reading("2026-10-15", _same_again)]))
check("the SAME claim seen again with no rupees keeps the rupees already recovered (R20 proving)",
      _kept is not None and len(_kept.update) == 1 and all(dict(zip(COLS, one[1])).get("claimRecovered") == "177.84" for one in _kept.update)
      and dict(zip(COLS, sheet_paid[1])).get("claimRecovered") == "177.84")

# ---------------------------------------------------------------- every claim is a record of its own (D459)

_ROWS = (
    line("11_1", "T1", "Approved", "2026-09-22T19:59:37", PAID),
    line("12_1", "T2", "Approved", "2026-09-23T10:00:00", "Approved, will be settled on 20 Oct"),
    line("12_1", "T3", "Open", "2026-09-25T10:00:00", "escalated"),
)
_made, _refused = answered(lambda: claims.read_claim_records("me_claims", "meesho", file_of(*_ROWS), "2026-10-14")) or ({}, ())
check("EVERY CLAIM IS A RECORD OF ITS OWN named by its claim id and carrying its sub-order, even two on one order, and none is tied to an order row",
      set(_made) == {"meesho__T1", "meesho__T2", "meesho__T3"} and _made["meesho__T2"]["orderId"] == "12_1"
      and _made["meesho__T3"]["orderId"] == "12_1" and _made["meesho__T1"]["raisedOn"] == "2026-09-22" and _refused == ())
check("'Approved, will be settled' has no rupees until a later file gives them; a paid one has",
      "recovered" not in _made["meesho__T2"] and _made["meesho__T1"]["recovered"] == "177.84")
check("the platform's own long message is not kept, and the fields are only the claim's own",
      all(set(r) <= set(claims.CLAIM_FIELDS) for r in _made.values()))
_, _skipped = answered(lambda: claims.read_claim_records("me_claims", "meesho", file_of(
    line("15_1", "", "Open", "2026-09-24T10:00:00"), line("", "T5", "Open", "2026-09-24T10:00:00"), line("16_1", "a/b", "Open", "2026-09-24T10:00:00")),
    "2026-10-14")) or ({}, ())
check("a claim with no order, no id or an id that cannot name a record is refused by name", len(_skipped) == 3)

# ---------------------------------------------------------------- A PAID CLAIM NEVER LOSES ITS RUPEES

_held_paid = {"recovered": "177.84"}
_reworded = {k: v for k, v in _made["meesho__T1"].items() if k != "recovered"}
_kept = claims.merge(_reworded, _held_paid)
check("A PAID CLAIM NEVER LOSES ITS RUPEES: a later file that says nothing of the amount leaves the recorded amount standing, and the fingerprint is worked out again",
      _kept["recovered"] == "177.84" and "recoveredWas" not in _kept and _kept["digest"] == records.the_digest(_kept)
      and _kept["digest"] == _made["meesho__T1"]["digest"])
_changed = claims.merge(dict(_made["meesho__T1"], recovered="150.00"), _held_paid)
check("and a different amount replaces it, the one it replaced noted",
      _changed["recovered"] == "150.00" and _changed["recoveredWas"] == "177.84")
_again = claims.merge(dict(_made["meesho__T1"]), {"recovered": "177.84", "recoveredWas": "100.00"})
check("and the note of what a replaced amount was survives the next runs, not only the one that replaced it",
      _again["recoveredWas"] == "100.00" and _again["recovered"] == "177.84")
check("a claim not held yet, or held with no rupees, is left exactly as read",
      claims.merge(_made["meesho__T2"], None) == _made["meesho__T2"] and claims.merge(_made["meesho__T2"], {"status": "Open"}) == _made["meesho__T2"])

# ---------------------------------------------------------------- R20 proving: what each record holds, exactly

def _raw(sub, ticket, status, created, issue, message):
    return f'"1","","","","","","{sub.split("_")[0]}","{sub}","{ticket}","{status}","{created}","{issue}","{message}","null",""'


_G = (
    _raw("21_1", "T21", " approved ", "2026-09-22T19:59:37", "  Item missing  ", "Your claim payment of Rs 1,234.50 for this order was done on 1 Oct 2026"),
    _raw("22_1", "T22", "Rejected", "2026-09-22T10:00:00", "x", "Your claim payment of Rs 50 for this order was done on 1 Oct 2026"),
    _raw("23_1", "T23", "", "2026-09-22T10:00:00", "", "escalated"),
    _raw("24_1", "T24", "Approved", "2026-09-22T10:00:00", "", "Note: Your claim payment of Rs 5 for this order was done on 1 Oct 2026"),
    _raw("25_1", "T25", "Approved", "2026-09-22T10:00:00", "", "  Your claim payment of Rs 7 for this order was done on 1 Oct 2026"),
    _raw("26_1", "T26", "Approved", "2026-09-22T10:00:00", "", "claim payment of Rs 8 for this order was done on 1 Oct 2026"),
    _raw("27_1", "T27", "Approved", "2026-09-22T10:00:00", "", "Your claim payment of Rs 9 for this order was reversed"),
)
_gm, _gr = answered(lambda: claims.read_claim_records("me_claims", "meesho", file_of(*_G), "2026-10-14")) or ({}, ())
_want = {"platform": "meesho", "report": "me_claims", "claimKey": "T21", "orderId": "21_1", "fileDay": "2026-10-14", "status": "approved",
         "raisedOn": "2026-09-22", "issue": "Item missing", "recovered": "1234.50"}
check("A CLAIM RECORD HOLDS EXACTLY ITS OWN FIELDS: the claim id, the trimmed status and issue, the rupees with the thousands comma taken out, "
      "whatever the case of Approved, and the fingerprint of all of it (R20 proving)",
      _gm.get("meesho__T21") == dict(_want, digest=records.the_digest(_want)))
check("a rejected claim whose words look like a payment recovers nothing (R20 proving)", "recovered" not in _gm.get("meesho__T22", {"recovered": 1}))
check("a claim with no status writes no status (R20 proving)", "status" not in _gm.get("meesho__T23", {"status": 1}))
check("the payment words count only at the START of the message, leading spaces allowed, starting 'Your', ending 'was done on' (R20 proving)",
      [_gm.get(f"meesho__T{n}", {}).get("recovered") for n in (24, 25, 26, 27)] == [None, "7", None, None])
_gs = answered(lambda: claims.read_claims("meesho", file_of(*_G), "2026-10-14"))
_by_claim = {s.claim_id: s for s in (_gs.sales if _gs else ())}
check("as a note for the ledger, a blank status and no rupees are nothing, not blank text, and every row is counted (R20 proving)",
      _by_claim.get("T23") is not None and _by_claim["T23"].claim_status is None and _by_claim["T23"].claim_recovered is None
      and _gs.rows_in_file == 7)
check("and the ledger note of a paid claim whose status is written ' approved ' still carries its rupees (R20 proving)",
      _by_claim.get("T21") is not None and _by_claim["T21"].claim_recovered == "1234.50")
_tie = answered(lambda: claims.read_claims("meesho", file_of(
    line("31_1", "T32", "Open", "2026-09-22T10:00:00"), line("31_1", "T31", "Approved", "2026-09-22T10:00:00")), "2026-10-14"))
check("two claims of one order raised at the same moment: the larger claim id is the order's note, whatever the row order (R20 proving)",
      _tie is not None and [s.claim_id for s in _tie.sales] == ["T32"])
_no_cols = caught(lambda: claims.read_claim_records("me_claims", "meesho", table.read(b"A,B\n1,2\n"), "2026-10-14"))
check("records are not made from a file without the claims columns: it is refused in words (R20 proving)",
      _no_cols is not None and "Nothing was read" in str(_no_cols))
_later_no_amount = {k: v for k, v in _made["meesho__T1"].items() if k not in ("recovered", "digest")}
_later_no_amount["digest"] = records.the_digest(_later_no_amount)
check("A LATER FILE WITHOUT THE AMOUNT, merged with the paid record held, comes out with the HELD fingerprint, so nothing is rewritten (R20 proving)",
      claims.merge(_later_no_amount, _made["meesho__T1"])["digest"] == _made["meesho__T1"]["digest"])

# ---------------------------------------------------------------- the night writes the claims AND notes them on the ledger

_handed, _ledger = [], []
_night = answered(lambda: reading.read_what_is_new(
    already_read=(), what_is_in_the_folder=lambda r: [whats_new.InTheFolder(which="c1", name="meesho_me_claims_2026-10-14.csv", size=900)] if r == "me_claims" else [],
    bring_it_back=lambda w: ("\n".join([HEAD, *_ROWS]) + "\n").encode("utf-8"),
    record_the_sales=lambda readings: _ledger.extend(readings),
    record_records={"me_claims": lambda report_id, day, made: _handed.append(sorted(made)) or len(made)}))
check("THE NIGHT WRITES EVERY CLAIM TO ITS RECORD AND HANDS THE LEDGER ITS NOTE (one per order), and the file is read",
      _night is not None and _night.read_tonight == ("c1",) and _night.wrote("me_claims") == 3 and _handed == [["meesho__T1", "meesho__T2", "meesho__T3"]]
      and len(_ledger) == 1 and sorted(s.order_id for s in _ledger[0].sales) == ["11_1", "12_1"])

_ledger_only = []
_odd_night = answered(lambda: reading.read_what_is_new(
    already_read=(), what_is_in_the_folder=lambda r: [whats_new.InTheFolder(which="c2", name="meesho_me_claims_2026-10-14.csv", size=900)] if r == "me_claims" else [],
    bring_it_back=lambda w: ("\n".join([HEAD, line("17_1", "..", "Open", "2026-09-24T10:00:00")]) + "\n").encode("utf-8"),
    record_the_sales=lambda readings: _ledger_only.extend(readings),
    record_records={"me_claims": lambda report_id, day, made: len(made)}))
check("A CLAIM WHOSE ID CANNOT NAME A RECORD DOES NOT STOP ITS NOTE ON THE LEDGER: the file is read, nothing is recorded, the refusal is counted",
      _odd_night is not None and _odd_night.read_tonight == ("c2",) and _odd_night.wrote("me_claims") == 0 and len(_ledger_only) == 1
      and _odd_night.rows_refused == 1)

# ---------------------------------------------------------------- the report is tied in

HOW = next(h for h in reading.WHAT_CAN_BE_READ if h.report_id == "me_claims")
check("the Meesho claims report is read into the ledger and says only what a claim may say",
      "me_claims" in reading.what_this_can_read() and "me_claims" not in reading.WHAT_IS_FETCHED_AND_NOT_READ_YET
      and HOW.knows == ("claimId", "claimStatus", "claimRecovered", "claimsOn"))
check("and a file of it would really say its own day (the guard that refuses to write otherwise)",
      reading.would_a_file_say_which_day_it_is(HOW))

# ---------------------------------------------------------------- R20 proving: the claims in the night
_real_read_claims = claims.read_claims
try:
    claims.read_claims = lambda platform, rows, day: claims.WhatClaimsSaid(tuple(
        sales.Sale(platform=platform, order_id="1_1", sku="", claim_id="T", claims_on="2000-01-01") for _ in (1,)))
    _forgets = reading.would_a_file_say_which_day_it_is(HOW)

    def _throws(platform, rows, day):
        raise ValueError("this reader cannot read its own table")

    claims.read_claims = _throws
    _throwing = answered(lambda: reading.would_a_file_say_which_day_it_is(HOW))
finally:
    claims.read_claims = _real_read_claims
check("a claims reader that writes another day than the file's is caught by the day guard, and one that throws is an answer of no, not a crash (R20 proving)",
      _forgets is False and _throwing is False)
_seen_ledger = []
_claims_night = answered(lambda: reading.read_what_is_new(
    already_read=(),
    what_is_in_the_folder=lambda r: {"me_claims": [whats_new.InTheFolder(which="c9", name="meesho_me_claims_2026-10-14.csv", size=900)],
                                     "me_orders": [whats_new.InTheFolder(which="o9", name="meesho_me_orders_2026-10-20.csv", size=900)]}.get(r, []),
    bring_it_back=lambda w: ("\n".join([HEAD, *_ROWS, line("", "T9", "Open", "2026-09-24T10:00:00")]) + "\n").encode("utf-8") if w == "c9" else b"x",
    record_the_sales=lambda readings: _seen_ledger.extend(readings),
    record_records={"me_claims": lambda report_id, day, made: len(made)}))
_claims_reading = [r for r in _seen_ledger if r.report == "me_claims"]
check("A CLAIMS FILE ONLY NOTES CLAIMS ON ROWS THAT EXIST, never makes a row, and a row with no order is counted ONCE although both its readers refuse it (R20 review)",
      len(_claims_reading) == 1 and _claims_reading[0].only_existing is True and _claims_night is not None and _claims_night.rows_refused == 1)

# ---------------------------------------------------------------- FLIPKART'S CLAIMS FILE (v0.1.21 job 3)
# **THE SHAPE IS FROM HIS REAL FILE** (`flipkart_claim_report_till_2026-05-27.xlsx`, Dec 2025 - May 2026, read only, no row copied here): sheets `Help`,
# `Seller Claims` (its own Help sheet calls it "Seller Raised Claims") and `Auto-Approved Claims` ("Auto Approved Claims" in the Help). Every id,
# date and rupee figure below is made up. The seller sheet has NO Pay/Recovery column; the auto sheet has one, and the real file only shows `PAY`.

import io  # noqa: E402
import zipfile  # noqa: E402
from xml.sax.saxutils import escape  # noqa: E402

import sheet  # noqa: E402

_NS = ('xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')


def an_xlsx(sheets):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        names = list(sheets)
        z.writestr("xl/workbook.xml", f'<workbook {_NS}><sheets>' + "".join(
            f'<sheet name="{n}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(names, start=1)) + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(
                       f'<Relationship Id="rId{i}" Target="worksheets/sheet{i}.xml" '
                       'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/>'
                       for i, _ in enumerate(names, start=1)) + "</Relationships>")
        for i, name in enumerate(names, start=1):
            body = []
            for number, cells in enumerate(sheets[name], start=1):
                inside = "".join(f'<c r="{chr(65 + n)}{number}" t="inlineStr"><is><t>{escape(str(c))}</t></is></c>'
                                 for n, c in enumerate(cells) if c != "")
                body.append(f'<row r="{number}">{inside}</row>')
            z.writestr(f"xl/worksheets/sheet{i}.xml", f'<worksheet {_NS}><sheetData>' + "".join(body) + "</sheetData></worksheet>")
    return out.getvalue()


FK_HELP = [["Dear Seller,"], ["Use of this report"], ["Seller Raised Claims"], ["Auto Approved Claims"]]
FK_SELLER_HEAD = ["S.No.", "Claim ID", "Incident Id", "Order Id", "Order Item ID", "Created At", "Updated at", "Claim Status", "Approved Amount",
                  "Not Approved Reason"]
FK_AUTO_HEAD = ["S.No.", "Auto-Claim Reason", "Claim ID", "Order Id", "Order Item ID", "Claim Processing Date", "Claim Status", "Approved Amount",
                "Pay/Recovery"]


def fk_seller(claim, order, item, status, amount="", updated="2026-05-02 10:00:00.0", created="2026-04-20 09:00:00.0"):
    return ["1", claim, "IN" + claim, order, item, created, updated, status, amount,
            "Rejected by Claims and Risk Assessment Team" if status == "Not Approved" else ""]


def fk_auto(claim, order, item, amount, way, day="2026-05-03 11:00:00.0", status="Approved"):
    return ["1", "Shipment Lost", claim, order, item, day, status, amount, way]


def fk_book(seller=(), auto=(), seller_name="Seller Claims", auto_name="Auto-Approved Claims"):
    return an_xlsx({"Help": FK_HELP, seller_name: [FK_SELLER_HEAD, *seller], auto_name: [FK_AUTO_HEAD, *auto]})


def fk_read(body, day="2026-05-27"):
    names = claims.flipkart_sheet_names(sheet.sheets_in(body))
    seller = sheet.read(body, sheet=names[0]) if names[0] else None
    auto = sheet.read(body, sheet=names[1]) if names[1] else None
    return claims.read_flipkart_claims(seller, auto, day)


_book = fk_book(
    seller=[fk_seller("C1", "OD111", "111", "Approved", "111.15"), fk_seller("C2", "OD222", "222", "Not Approved"),
            fk_seller("C3", "OD333", "333", "In Processing")],
    auto=[fk_auto("A1", "OD444", "444", "65.01", "PAY"), fk_auto("A2", "OD555", "555", "20.5", "RECOVER")])
_fk = answered(lambda: fk_read(_book))
_by = {s.order_id: s for s in (_fk.sales if _fk else ())}
check("FLIPKART: both claim sheets are read and the Help sheet is skipped (no sale is made of its text)",
      _fk is not None and set(_by) == {"OD111", "OD222", "OD333", "OD444", "OD555"} and all(s.platform == "flipkart" and s.sku == "" for s in _by.values()))
check("an Approved claim on the seller sheet recovers its Approved Amount; Not Approved and In Processing recover nothing",
      _fk is not None and _by["OD111"].claim_recovered == "111.15" and _by["OD111"].claim_status == "Approved"
      and _by["OD222"].claim_recovered is None and _by["OD222"].claim_status == "Not Approved"
      and _by["OD333"].claim_recovered is None and _by["OD333"].claim_status == "In Processing")
check("PAY IS PLUS AND RECOVER IS MINUS on the auto-approved sheet (a recovery is money taken back, never added)",
      _fk is not None and _by["OD444"].claim_recovered == "65.01" and _by["OD555"].claim_recovered == "-20.5")
check("every claim carries its claim id and the day of the file",
      _fk is not None and _by["OD111"].claim_id == "C1" and _by["OD444"].claim_id == "A1" and all(s.claims_on == "2026-05-27" for s in _by.values()))
_alias = answered(lambda: fk_read(fk_book(seller=[fk_seller("C1", "OD111", "111", "Approved", "9")], auto=[],
                                          seller_name="Seller Raised Claims", auto_name="Auto Approved Claims")))
check("the sheet names the file's own Help gives (Seller Raised Claims, Auto Approved Claims) are read too",
      _alias is not None and [s.order_id for s in _alias.sales] == ["OD111"])
_unknown_way = answered(lambda: fk_read(fk_book(auto=[fk_auto("A9", "OD9", "9", "5", "REFUND")])))
check("A PAY/RECOVERY WORD THAT IS NEITHER IS REFUSED BY NAME and no rupees are guessed",
      _unknown_way is not None and _unknown_way.sales == () and len(_unknown_way.not_read) == 1 and "REFUND" in _unknown_way.not_read[0])
_na = answered(lambda: fk_read(fk_book(
    seller=[fk_seller("C1", "OD111", "111", "Approved", "10"), fk_seller("C7", "NA", "NA", "Approved", "99")],
    auto=[fk_auto("A7", "OD777", "NA", "40", "PAY")])))
check("AN ORDER ITEM OF 'NA' (stock held at Flipkart, no order) IS KEPT ASIDE AND SAID, never put on an order and never dropped silently",
      _na is not None and [s.order_id for s in _na.sales] == ["OD111"] and len(_na.not_read) == 2
      and all("NA" in w and "Flipkart" in w for w in _na.not_read))
_two = answered(lambda: fk_read(fk_book(
    seller=[fk_seller("C1", "OD111", "111", "Approved", "100", updated="2026-05-01 10:00:00.0"),
            fk_seller("C2", "OD111", "111", "Approved", "30", updated="2026-05-09 10:00:00.0")],
    auto=[fk_auto("A1", "OD111", "111", "5", "RECOVER", day="2026-05-05 10:00:00.0")])))
check("ONE ORDER WITH SEVERAL CLAIMS: the newest claim's id and status stand, and the rupees are the net of what was paid minus what was recovered",
      _two is not None and len(_two.sales) == 1 and _two.sales[0].claim_id == "C2" and _two.sales[0].claim_status == "Approved"
      and _two.sales[0].claim_recovered == "125")
_dup = answered(lambda: fk_read(fk_book(seller=[fk_seller("C1", "OD111", "111", "Open", "", updated="2026-05-01 10:00:00.0"),
                                                fk_seller("C1", "OD111", "111", "Approved", "50", updated="2026-05-02 10:00:00.0")])))
check("a claim id named twice in one file is one claim, the later line standing, and its rupees are counted once",
      _dup is not None and len(_dup.sales) == 1 and _dup.sales[0].claim_recovered == "50")
_empty = answered(lambda: fk_read(fk_book()))
check("a file with the headers and no claims (every kept daily file is like this) is read as no claims, not refused",
      _empty is not None and _empty.sales == () and _empty.not_read == () and _empty.rows_in_file == 0)
_wrong_col = caught(lambda: fk_read(an_xlsx({"Help": FK_HELP, "Seller Claims": [["Claim ID", "Order Id"], ["C1", "OD1"]], "Auto-Approved Claims": [FK_AUTO_HEAD]})))
check("a seller sheet missing a column the reader needs is refused in words naming the columns it has",
      _wrong_col is not None and "Order Item ID" in str(_wrong_col) and "Claim ID" in str(_wrong_col))
_no_sheet = caught(lambda: claims.flipkart_sheet_names(("Help", "Orders")))
check("a workbook with neither claim sheet is refused in words, not read as having no claims",
      _no_sheet is not None and "Claims" in str(_no_sheet))

# ---- where a Flipkart claim lands in the ledger

_fk_one = [COLS, list(sales.the_row_for(sales.Sale(platform="flipkart", order_id="OD111", sku="RING", on="2026-04-20", qty=1, gmv="100")))]
_fk_pair = [COLS, _fk_one[1], list(sales.the_row_for(sales.Sale(platform="flipkart", order_id="OD111", sku="CHAIN", on="2026-04-20", qty=1, gmv="80")))]


def fk_claims_reading(day, *those):
    return ledger.Reading(report="fk_claims", on=day, knows=reading.WHAT_CLAIMS_KNOW, sales=tuple(those), which=day, only_existing=True)


_on_one = answered(lambda: ledger.plan(_fk_one, [fk_claims_reading("2026-05-27", _two.sales[0])])) if _two else None
_row_one = dict(zip(COLS, _on_one.update[0][1])) if _on_one and _on_one.update else {}
check("A FLIPKART CLAIM GOES ON THE ORDER'S ROW WHEN THE LEDGER HAS EXACTLY ONE ROW FOR THAT ORDER",
      _on_one is not None and len(_on_one.update) == 1 and _row_one.get("claimId") == "C2" and _row_one.get("claimRecovered") == "125"
      and _row_one.get("claimsOn") == "2026-05-27" and _on_one.unmatched == ())
_on_two = answered(lambda: ledger.plan(_fk_pair, [fk_claims_reading("2026-05-27", _two.sales[0])])) if _two else None
check("WITH TWO ROWS FOR THE ORDER (two items) THE CLAIM IS UNMATCHED, SAID IN WORDS, AND NOTHING IS WRITTEN (which item it is for cannot be said)",
      _on_two is not None and _on_two.update == () and len(_on_two.unmatched) == 1 and "2 row" in _on_two.unmatched[0].why)
_on_none = answered(lambda: ledger.plan([COLS], [fk_claims_reading("2026-05-27", _two.sales[0])])) if _two else None
check("and a claim for an order the ledger does not have is unmatched too, never a new row",
      _on_none is not None and _on_none.update == () and len(_on_none.unmatched) == 1)

# ---- the night reads it

_fk_how = next((h for h in reading.WHAT_CAN_BE_READ if h.report_id == "fk_claims"), None)
check("fk_claims is a report this reads, as a claims report, and no longer sits in the not-read-yet list",
      _fk_how is not None and _fk_how.kind == "claims" and "fk_claims" not in reading.WHAT_IS_FETCHED_AND_NOT_READ_YET
      and reading.why_a_report_has_no_decision() == "")
_fk_seen = []
_fk_night = answered(lambda: reading.read_what_is_new(
    already_read=(),
    what_is_in_the_folder=lambda r: {"fk_claims": [whats_new.InTheFolder(which="f9", name="flipkart_fk_claims_2026-05-27.xlsx", size=900)]}.get(r, []),
    bring_it_back=lambda w: _book if w == "f9" else b"x",
    record_the_sales=lambda readings: _fk_seen.extend(readings),
    record_records={"me_claims": lambda report_id, day, made: len(made)}))
_fk_reading = [r for r in _fk_seen if r.report == "fk_claims"]
check("A NIGHT READS A FLIPKART CLAIMS WORKBOOK: one reading, only on rows that exist, five claims, nothing refused, the file written down as read",
      _fk_night is not None and len(_fk_reading) == 1 and _fk_reading[0].only_existing is True and len(_fk_reading[0].sales) == 5
      and _fk_reading[0].on == "2026-05-27" and _fk_night.rows_refused == 0 and _fk_night.files_read == ("f9",))

# ---------------------------------------------------------------- AMAZON'S SAFE-T CLAIMS (N018, his ruling D726; own record per claim, D459)
# **THE HEADER IS THE REAL ONE** (Seller Central > Orders > Manage claims > Manage SAFE-T claims > Download the SAFE-T Report, type "SAFE-T Claims", seen 26 Oct 2026: 20 columns,
# comma-separated, every cell quoted); the rows are made up.
AZ_SAFET_HEAD = ('"Order Date","Order ID","ASIN","Item name","Fulfillment Channel","Return Tracking ID","Return Status","Return Delivery Date","SAFE-T Claim ID","Claim Date",'
                 '"Claim Filing Reason","Quantity In Claim","Currency","Claim amount","SAFE-T claim state","Appeal by/ Respond by date","Reimbursement amount (Product value)",'
                 '"Reimbursement amount (Others)","Total Reimbursement amount","Date of reimbursement"')


def az_safet(*rows):
    return table.read(("\n".join([AZ_SAFET_HEAD, *rows]) + "\n").encode("utf-8"))


def az_claim(order, claim, claim_date, reason, state, total, paid_on=""):
    return (f'"2026-09-23","{order}","B0X","Item","Easy Ship","515","Delivered to seller","2026-10-03","{claim}","{claim_date}","{reason}","1","INR","246.79",'
            f'"{state}","2026-10-13","{total}","0.0","{total}","{paid_on}"')


_az_made, _az_refused = answered(lambda: claims.read_safet_records("az_claims", "amazon", az_safet(
    az_claim("403-1", "44055-43555-0397437", "2026-10-05", "I received damaged/ used item", "Granted", "61.69", "2026-10-06"),
    az_claim("403-2", "44055-43555-0397438", "2026-10-07", "Item not received", "Under Investigation", "0.0"),
    az_claim("403-3", "44055-43555-0397439", "2026-10-08", "Item not received", "Denied", "0.0")), "2026-10-26")) or ({}, ())
check("EVERY SAFE-T CLAIM IS A RECORD OF ITS OWN named by Amazon's claim id and carrying its order, and none is tied to an order row",
      set(_az_made) == {"amazon__44055-43555-0397437", "amazon__44055-43555-0397438", "amazon__44055-43555-0397439"} and _az_refused == ()
      and _az_made["amazon__44055-43555-0397438"]["orderId"] == "403-2" and _az_made["amazon__44055-43555-0397437"]["raisedOn"] == "2026-10-05")
_azg = _az_made.get("amazon__44055-43555-0397437", {})
_azw = {"platform": "amazon", "report": "az_claims", "claimKey": "44055-43555-0397437", "orderId": "403-1", "fileDay": "2026-10-26", "status": "Granted",
        "raisedOn": "2026-10-05", "issue": "I received damaged/ used item", "recovered": "61.69"}
check("A GRANTED CLAIM HOLDS EXACTLY ITS OWN FIELDS: the state as Amazon says it, Amazon's own filing reason, the total reimbursement as the rupees recovered, and the fingerprint of all of it",
      _azg == dict(_azw, digest=records.the_digest(_azw)))
check("a claim still under investigation or denied recovers nothing: no rupees are written for it",
      all("recovered" not in _az_made.get(f"amazon__44055-43555-039743{n}", {"recovered": 1}) for n in (8, 9)))
check("and every field is one of the claim record's own fields, so the writer accepts it",
      all(set(r) <= set(claims.CLAIM_FIELDS) for r in _az_made.values()))
_az_bad = caught(lambda: claims.read_safet_records("az_claims", "amazon", table.read(b"A,B\n1,2\n"), "2026-10-26"))
check("a file without the SAFE-T columns is refused in words naming them, nothing read",
      _az_bad is not None and "Nothing was read" in str(_az_bad) and "SAFE-T Claim ID" in str(_az_bad))
_, _az_skipped = answered(lambda: claims.read_safet_records("az_claims", "amazon", az_safet(
    az_claim("", "44055-1", "2026-10-05", "x", "Granted", "1"), az_claim("403-9", "", "2026-10-05", "x", "Granted", "1"),
    az_claim("403-9", "a/b", "2026-10-05", "x", "Granted", "1")), "2026-10-26")) or ({}, ())
check("a claim with no order, no id or an id that cannot name a record is refused by name", len(_az_skipped) == 3)
_az_again, _ = answered(lambda: claims.read_safet_records("az_claims", "amazon", az_safet(
    az_claim("403-1", "44055-43555-0397437", "2026-10-05", "I received damaged/ used item", "Granted", "")), "2026-10-27")) or ({}, ())
_az_keep = claims.merge(_az_again.get("amazon__44055-43555-0397437", {}), _az_made.get("amazon__44055-43555-0397437"))
check("A PAID CLAIM NEVER LOSES ITS RUPEES: a later file that gives no amount keeps the amount already recorded",
      _az_keep.get("recovered") == "61.69")
check("Amazon's SAFE-T claims are a report that is written as records, like Meesho's claims",
      "az_claims" in record_reports.RECORD_REPORTS and record_reports.RECORD_REPORTS["az_claims"].kind is claims.KIND)

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 29 + 2 + 9 + 2 + 17 + 8
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")
print(f"\n{len(failures)} FAILED: {failures}" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
