"""Checks for the four report types that run #19 read wrongly (A81, v0.1.16).

**EVERY ROW IN HERE IS MADE UP.** The shapes are the ones his real files carry (Amazon's `purchase-date` written with `+00:00`, its
`Shipped - Delivered to Buyer` phrase, an Amazon returns row with a blank `Amazon RMA ID`); no order number, address or figure of his
is written here, because this repository is public.

Run: python autosync/a81_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import firestore_door  # noqa: E402
import ledger  # noqa: E402
import orders  # noqa: E402
import reading  # noqa: E402
import returns  # noqa: E402
import sales  # noqa: E402
import table  # noqa: E402
import whats_new  # noqa: E402

ran = 0
failures = []
THREW = []


def answered(work):
    try:
        return work()
    except Exception as wrong:  # noqa: BLE001
        THREW.append(repr(wrong))
        return None


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


# ------------------------------------------------ 1. Amazon's day is the India day

check("21:17 UTC is already the next day in India",
      orders.the_day_in_india("2026-10-12T21:17:27+00:00") == "2026-10-13")
check("18:29:59 UTC is still the same India day", orders.the_day_in_india("2026-10-12T18:29:59+00:00") == "2026-10-12")
check("18:30:00 UTC is the next India day", orders.the_day_in_india("2026-10-12T18:30:00+00:00") == "2026-10-13")
check("a time already written in India's offset keeps its day", orders.the_day_in_india("2026-10-12T23:30:00+05:30") == "2026-10-12")
check("an offset the other way round is moved correctly", orders.the_day_in_india("2026-10-12T23:00:00-05:00") == "2026-10-13")
check("a `Z` is UTC", orders.the_day_in_india("2026-10-12T20:00:00Z") == "2026-10-13")
check("A TIME WITH NO OFFSET IS NOTHING, never guessed", orders.the_day_in_india("2026-10-12T20:00:00") is None)
check("and so is a bare day, which cannot be moved", orders.the_day_in_india("2026-10-12") is None)
check("and an impossible one", orders.the_day_in_india("2026-02-31T10:00:00+00:00") is None)

AZ_HEAD = "amazon-order-id\tsku\tquantity\tpurchase-date\torder-status\titem-price"


def az_orders(*rows):
    return table.read(("\n".join([AZ_HEAD, *rows]) + "\n").encode("utf-8"))


was = answered(lambda: orders.read_orders(az_orders(
    "A-1\tSKU-1\t1\t2026-10-12T21:17:27+00:00\tShipped - Picked Up\t349.0",
    "A-2\tSKU-1\t1\t2026-10-13T20:54:09+00:00\tPending\t199.0",
    "A-3\tSKU-1\t1\t2026-10-11T09:00:00+00:00\tShipped - Delivered to Buyer\t199.0",
), "amazon", data_date="2026-10-14"))
check("an Amazon file is read with each sale on its India day",
      was is not None and [s.on for s in was.sales] == ["2026-10-13", "2026-10-14", "2026-10-11"])
bare = answered(lambda: orders.read_orders(az_orders("A-4\tSKU-1\t1\t2026-10-12\tPending\t1"), "amazon"))
check("an Amazon row whose time has no offset is refused by name, not dated",
      bare is not None and bare.sales == () and len(bare.not_read) == 1 and "2026-10-12" in bare.not_read[0].why)
meesho = answered(lambda: orders.read_orders(table.read(
    b"Sub Order No,SKU,Quantity,Order Date,Reason for Credit Entry,Supplier Discounted Price (Incl GST and Commision)\n"
    b"S1,A,1,2026-10-12 21:17:27,SHIPPED,10\n"), "meesho"))
check("and Meesho's and Flipkart's days are untouched by it", meesho is not None and meesho.sales[0].on == "2026-10-12")

# ------------------------------------------------ 2. Amazon's status words

check("`Shipped - Delivered to Buyer` is Delivered", orders.what_happened("Shipped - Delivered to Buyer") == "Delivered")
check("`Shipped - Picked Up` is still on its way, so blank", orders.what_happened("Shipped - Picked Up") is None)
check("Amazon's own documented list: the three not yet known are still-open",
      all(orders.what_happened(w) is None for w in ("PartiallyShipped", "InvoiceUnconfirmed", "PendingAvailability")))
check("the documented ones already known keep their answers",
      orders.what_happened("Canceled") == "Cancelled" and orders.what_happened("Cancelled") == "Cancelled"
      and orders.what_happened("Pending") is None and orders.what_happened("Unshipped") is None and orders.what_happened("Shipped") is None)
check("`Unfulfillable` is documented but its meaning is not, so it stays not understood",
      orders.what_happened("Unfulfillable") == orders.NOT_UNDERSTOOD_YET)
check("A PHRASE NOBODY HAS LISTED STAYS 'not understood yet'",
      orders.what_happened("Shipped - Lost in Transit") == orders.NOT_UNDERSTOOD_YET)
check("and the phrase is matched whatever its case or spacing at the ends", orders.what_happened("  SHIPPED - DELIVERED TO BUYER ") == "Delivered")
check("A BLANK STAYS NOTHING", orders.what_happened("") is None)
check("the sale carries it", was is not None and [s.what_happened for s in was.sales] == [None, None, "Delivered"])


# ------------------------------------------------ the night names a word nobody has translated

class Folder:
    def __init__(self, files, bodies, recorded_with=None):
        self.files, self.bodies, self.recorded_with = files, bodies, recorded_with
        self.recorded = []

    def record(self, readings):
        self.recorded.extend(readings)
        return self.recorded_with

    def go(self, already=()):
        return reading.read_what_is_new(
            already_read=already,
            what_is_in_the_folder=lambda report: list(self.files.get(report, ())),
            bring_it_back=lambda which: self.bodies[which],
            record_the_sales=self.record,
            can_be_read=reading.WHAT_CAN_BE_READ,
        )


def a_file(which, name):
    return whats_new.InTheFolder(which=which, name=name, size=100)


AZ_BODY = ("\r\r\n".join([
    AZ_HEAD,
    "A-1\tSKU-1\t1\t2026-10-12T21:17:27+00:00\tShipped - Lost in Transit\t349.0",
    "A-2\tSKU-1\t1\t2026-10-12T21:17:27+00:00\tShipped - Lost in Transit\t349.0",
    "A-3\tSKU-2\t1\t2026-10-12T21:17:27+00:00\tShipped - Delivered to Buyer\t199.0",
]) + "\r\r\n").encode("utf-8")
night = answered(lambda: Folder({"az_orders": [a_file("az-1", "amazon_az_orders_2026-10-14.csv")]}, {"az-1": AZ_BODY}).go())
check("A STATUS WORD NOBODY HAS TRANSLATED IS NAMED IN THE NIGHT'S REPORT, with how many rows carried it",
      night is not None and night.words_not_understood == (("Shipped - Lost in Transit", 2),)
      and "'Shipped - Lost in Transit' x2" in night.says())
check("and a word that is understood is not named", night is not None and "Delivered to Buyer" not in night.says())

# ------------------------------------------------ 3. Amazon returns with no RMA ID

AZ_RET_HEAD = ("Amazon RMA ID\tOrder ID\tReturn request date\tReturn request status\tTracking ID\tMerchant SKU\tReturn quantity\t"
               "Return Reason\tReturn type\tReturn delivery date")


def az_returns(*rows):
    return table.read(("\n".join([AZ_RET_HEAD, *rows]) + "\n").encode("utf-8"))


with_rma = "RMA1\t407-1\t11-Oct-2026\tApproved\tTRK-A\tSKU 1\t1\tAMZ\tC-Returns\t"
no_rma = "\t408-2\t11-Oct-2026\tApproved\tTRK-B\tSKU 2\t1\tUND-UNKNOWN\tC-Returns\t"
file_one = answered(lambda: returns.read_returns("az_returns", az_returns(with_rma, no_rma), "2026-10-11"))
check("A ROW WITH NO RMA ID IS KEPT, not dropped",
      file_one is not None and len(file_one.records) == 2 and file_one.not_read == ())
the_name = "amazon__" + returns.a_return_without_an_rma("408-2", "SKU 2", "2026-10-11")
check("under a name made of its order, SKU and request day",
      file_one is not None and the_name in file_one.records and the_name == "amazon__NORMA-408-2-SKU_2-2026-10-11")
check("and the RMA-keyed row is named as before", file_one is not None and "amazon__RMA1" in file_one.records)
file_again = answered(lambda: returns.read_returns("az_returns", az_returns(with_rma, no_rma), "2026-10-12"))
check("READING THE SAME FILE AGAIN GIVES THE SAME NAMES AND THE SAME FINGERPRINTS (so nothing new is written)",
      file_one is not None and file_again is not None and file_one.records.keys() == file_again.records.keys()
      and all(file_one.records[k]["digest"] == file_again.records[k]["digest"] for k in file_one.records))
no_day = answered(lambda: returns.read_returns("az_returns", az_returns("\t408-2\t\tApproved\tTRK-B\tSKU 2\t1\tR\tC\t"), "2026-10-11"))
check("with no request day there is nothing certain to name it by, so the row is refused by name",
      no_day is not None and no_day.records == {} and len(no_day.not_read) == 1)
flipkart_blank = answered(lambda: returns.read_returns("fk_returns", table.read(
    b'"Order ID","Return ID","Tracking ID","SKU","Quantity","Return Requested Date","Completed Date","Completion Status","Return Type",'
    b'"Return Reason","Return Sub-reason"\n"OD1","","T","S","1","11 October, 2026","","x","y","z","w"\n'), "2026-10-11"))
check("and ONLY Amazon gets a fallback: a Flipkart row with no return ID is still refused",
      flipkart_blank is not None and flipkart_blank.records == {} and len(flipkart_blank.not_read) == 1)


# ------------------------------------------------ and a return that later gets its RMA ID stays ONE record

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
        self.held, self.committed = held or {}, []

    def post(self, url, params=None, headers=None, json=None, data=None):
        if url.endswith(":batchGet"):
            found = []
            for name in json["documents"]:
                got = self.held.get(name.rsplit("/", 1)[-1])
                found.append({"found": {"name": name, "fields": {
                    "digest": {"stringValue": got[0]}, "fileDay": {"stringValue": got[1]}}}} if got else {"missing": name})
            return Reply(200, found)
        self.committed.extend(json["writes"])
        return Reply(200, {})


def names_written(database):
    return sorted(w["update"]["name"].rsplit("/", 1)[-1] for w in database.committed)


blank_first = answered(lambda: returns.read_returns("az_returns", az_returns(no_rma), "2026-10-11"))
fallback_name = "amazon__" + returns.a_return_without_an_rma("408-2", "SKU 2", "2026-10-11")
now_has_one = answered(lambda: returns.read_returns(
    "az_returns", az_returns("RMA9\t408-2\t11-Oct-2026\tApproved\tTRK-B\tSKU 2\t1\tUND-UNKNOWN\tC-Returns\t"), "2026-10-14"))
empty = Database()
answered(lambda: firestore_door.a_returns_sink(empty, "p", "2026-10-14")("az_returns", "2026-10-11", blank_first.records))
check("a blank-RMA return is written under its fallback name", names_written(empty) == [fallback_name])
held = Database(held={fallback_name: (blank_first.records[fallback_name]["digest"], "2026-10-11")})
wrote = answered(lambda: firestore_door.a_returns_sink(held, "p", "2026-10-14")("az_returns", "2026-10-14", now_has_one.records))
check("A RETURN THAT HAS SINCE GOT AN RMA ID IS WRITTEN OVER ITS EARLIER RECORD, not as a second return",
      wrote == 1 and names_written(held) == [fallback_name])
check("and the RMA ID is kept in the record", any(
    w["update"]["fields"]["returnKey"] == {"stringValue": "RMA9"} for w in held.committed))
fresh = Database()
answered(lambda: firestore_door.a_returns_sink(fresh, "p", "2026-10-14")("az_returns", "2026-10-14", now_has_one.records))
check("with no earlier record, an RMA-keyed return is written under its own RMA name", names_written(fresh) == ["amazon__RMA9"])
same = Database(held={fallback_name: (now_has_one.records["amazon__RMA9"]["digest"], "2026-10-14")})
check("and reading that same file again writes nothing",
      answered(lambda: firestore_door.a_returns_sink(same, "p", "2026-10-15")("az_returns", "2026-10-14", now_has_one.records)) == 0)

two_rmas = answered(lambda: returns.read_returns("az_returns", az_returns(
    "RMA7	408-2	11-Oct-2026	Approved	TRK-B	SKU 2	1	R	C	", "RMA8	408-2	11-Oct-2026	Approved	TRK-C	SKU 2	1	R	C	"), "2026-10-14"))
two_held = Database(held={fallback_name: ("x", "2026-10-11")})
answered(lambda: firestore_door.a_returns_sink(two_held, "p", "2026-10-14")("az_returns", "2026-10-14", two_rmas.records))
check("TWO RETURNS OF ONE ORDER, SKU AND DAY WITH TWO RMA IDS ARE NOT FOLDED ONTO ONE RECORD: each keeps its own",
      names_written(two_held) == ["amazon__RMA7", "amazon__RMA8"])

# ------------------------------------------------ 4. a payment with no order yet waits

class APaymentsReading:
    sales = ()


def run_payments(how_many_wait, report_id="fk_payments", day="2026-10-14"):
    folder = Folder({report_id: [a_file("p-1", f"x_{report_id}_{day}.xlsx")]}, {"p-1": b"x"}, recorded_with=how_many_wait)
    original, original_settlements = reading.a_reading, reading.a_settlements_reading
    reading.a_reading = lambda how, one, body: (APaymentsReading(), 0)
    reading.a_settlements_reading = lambda how, one, body, listed, bring: (APaymentsReading(), 0)
    try:
        return folder.go(), folder
    finally:
        reading.a_reading, reading.a_settlements_reading = original, original_settlements


all_matched, _ = run_payments(0)
check("a payments file whose every line found its order is read and marked, as before",
      all_matched is not None and all_matched.read_tonight == ("p-1",) and all_matched.payments_waiting == 0)
waiting, _ = run_payments(142)
check("A PAYMENTS FILE WITH LINES WAITING FOR THEIR ORDER IS NOT MARKED READ", waiting is not None and waiting.read_tonight == ())
check("so it is opened again the next run: it is not in the remembered list", waiting is not None and "p-1" not in waiting.files_read)
check("and no standing record says 'read N of N' for it", waiting is not None and waiting.reads == ())
check("THE RUN'S REPORT SAYS HOW MANY LINES ARE WAITING AND WHICH FILE",
      waiting is not None and waiting.payments_waiting == 142 and "142 payment line(s) are WAITING" in waiting.says()
      and "x_fk_payments_2026-10-14.xlsx" in waiting.says())
check("and it is not counted as the platform's fault or ours", waiting is not None and not waiting.is_a_defect)
second, _ = run_payments(0)
check("the run after, when the orders have arrived, reads and marks it", second is not None and second.read_tonight == ("p-1",))
meesho_waiting, _ = run_payments(12, report_id="me_payments")
check("Meesho payments wait the same way", meesho_waiting is not None and meesho_waiting.read_tonight == () and meesho_waiting.payments_waiting == 12)
settlement, _ = run_payments(3, report_id="az_settlements")
check("Amazon's settlements are not held back (the brief names Flipkart and Meesho)",
      settlement is not None and settlement.read_tonight == ("p-1",) and settlement.payments_waiting == 0)
none_given, _ = run_payments(None)
check("a recorder that answers nothing (a test stand-in) holds nothing back", none_given is not None and none_given.read_tonight == ("p-1",))

# ------------------------------------------------ the re-read puts right a wrong day / word that the same day's file left in the sheet

HEADER = list(sales.COLUMNS)
KNOWS = ("platform", "orderId", "on", "sku", "qty", "gmv", "status", "whatHappened", "ordersOn")


def an_amazon_sale(on, word, happened, orders_on="2026-10-14"):
    return sales.Sale(platform="amazon", order_id="A-1", sku="S", on=on, qty="1", gmv="349.0", status=word,
                      what_happened=happened, orders_on=orders_on)


def a_reading_of(sale, day="2026-10-14", which="f1", corrects=False):
    return ledger.Reading(report="az_orders", on=day, knows=KNOWS, sales=(sale,), which=which, corrects=corrects)


wrongly_written = ledger.plan([HEADER], [a_reading_of(an_amazon_sale("2026-10-12", "Shipped - Delivered to Buyer", "not understood yet"))])
sheet_rows = [HEADER] + [list(r) for r in wrongly_written.append]
the_better = an_amazon_sale("2026-10-13", "Shipped - Delivered to Buyer", "Delivered")
plain = ledger.plan(sheet_rows, [a_reading_of(the_better)])
check("WITHOUT THE CORRECTION, THE SAME DAY'S FILE READ BETTER IS A TIE AND THE WRONG DAY STAYS (why the correcting night is needed)",
      len(plain.update) == 0 and len(plain.disagreements) >= 1)
fixed = ledger.plan(sheet_rows, [a_reading_of(the_better, corrects=True)])
check("ON THE CORRECTING NIGHT THE ROW IS UPDATED, not duplicated, and no disagreement is left",
      len(fixed.update) == 1 and len(fixed.append) == 0 and fixed.disagreements == ()
      and fixed.update[0][1][HEADER.index("on")] == "2026-10-13"
      and fixed.update[0][1][HEADER.index("whatHappened")] == "Delivered")
mended = [HEADER, list(fixed.update[0][1])]
again = ledger.plan(mended, [a_reading_of(the_better, corrects=True)])
check("and the correcting night run twice changes nothing the second time", again.update == () and again.append == ())
newer = ledger.plan(sheet_rows, [a_reading_of(the_better, day="2026-10-10", which="f0", corrects=True)])
check("A CORRECTION NEVER UNDOES A NEWER FILE: an older file's reading is still left alone",
      newer.update == () and len(newer.left_alone) == 1)
two_files = ledger.plan(sheet_rows, [a_reading_of(the_better, which="f1", corrects=True),
                                      a_reading_of(an_amazon_sale("2026-10-11", "Shipped", None), which="f2", corrects=True)],
                        ledger.WhatTheNightHasDecided())
check("and two files of one day that disagree on the correcting night are still reported, not settled by which came last",
      len(two_files.disagreements) >= 1)


class Recorder(Folder):
    pass


corrected = Recorder({"az_orders": [a_file("az-1", "amazon_az_orders_2026-10-14.csv")]}, {"az-1": AZ_BODY})
reading.read_what_is_new(already_read=(), what_is_in_the_folder=lambda r: list(corrected.files.get(r, ())),
                         bring_it_back=lambda w: corrected.bodies[w], record_the_sales=corrected.record,
                         can_be_read=reading.WHAT_CAN_BE_READ, correcting=True)
ordinary = Recorder({"az_orders": [a_file("az-1", "amazon_az_orders_2026-10-14.csv")]}, {"az-1": AZ_BODY})
ordinary.go()
check("A NIGHT THAT IS CORRECTING MARKS EVERY ORDERS READING AS A CORRECTION, and an ordinary night marks none",
      corrected.recorded and all(r.corrects for r in corrected.recorded) and ordinary.recorded
      and not any(r.corrects for r in ordinary.recorded))

# ------------------------------------------------ and the files read wrongly are read again

check("THE READING RULES HAVE A NEW NAME, so the one-time re-read of every file fires on the first run of v0.1.16",
      reading.READING_RULES != "orders-with-the-platforms-status-word-and-what-happened")

print()
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 53
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
