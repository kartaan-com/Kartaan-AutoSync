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
_fk_row = [COLS, list(sales.the_row_for(sales.Sale(platform="flipkart", order_id="OD9", sku="RING", on="2026-09-20", qty=1, gmv="100")))]
_fk_claim = sales.Sale(platform="flipkart", order_id="OD9", sku="", claim_id="F1", claim_status="Open", claims_on="2026-10-14")
check("a SKU-less claim is placed on an order's one row for MEESHO only, whose sub-order is one line; another platform's is said (R20 proving)",
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

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 29 + 2 + 9 + 2
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")
print(f"\n{len(failures)} FAILED: {failures}" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
