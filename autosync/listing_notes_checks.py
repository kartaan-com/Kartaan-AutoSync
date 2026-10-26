"""Checks for what a platform's side file says about a listing, put beside that listing's record (v0.1.21 lane 2, AP9).

**EVERY ROW IN HERE IS MADE UP, AND SO IS THE HEADER.** Amazon's page names the Suppressed Listings Report's eight columns and does not show a
file; none has been fetched yet (plan sample A5). The words below are the page's own column names, in the page's order.

Run: python autosync/listing_notes_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import firestore  # noqa: E402
import firestore_door  # noqa: E402
import listing_notes as tool  # noqa: E402
import listings  # noqa: E402
import reading  # noqa: E402
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


def why(work):
    try:
        work()
    except table.CannotRead as wrong:
        return str(wrong)
    except Exception as wrong:  # noqa: BLE001
        return "THREW " + repr(wrong)
    return ""


HEAD = ["Status", "Reason", "SKU", "ASIN", "Product name", "Condition", "Status Change Date", "Issue Description"]


def a_row(sku, asin, reason="Missing image", issue="Add a main image"):
    return ["Suppressed", reason, sku, asin, "A made-up bangle", "New", "2026-10-01", issue]


def a_file(rows, head=HEAD, bom=True):
    text = "\r\n".join("\t".join(r) for r in [head] + rows) + "\r\n"
    return (b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8")


GOOD = a_file([a_row("BANGLE-5 FIVE", "B0AAAAAAA1"), a_row("RING-1", "B0AAAAAAA2", "Price too high", "Lower the price")])

# ---------------------------------------------------------------- the reader

said = answered(lambda: tool.read_suppressed(GOOD, "az.txt"))
check("each listing the file names becomes a note under amazon::ASIN::seller-sku, a SKU with a space in it kept",
      said is not None and set(said.notes) == {"amazon::B0AAAAAAA1::BANGLE-5 FIVE", "amazon::B0AAAAAAA2::RING-1"} and said.rows_in_file == 2)
check("a note says suppressed, Amazon's reason and Amazon's words on what to fix, and nothing else",
      said is not None and said.notes["amazon::B0AAAAAAA2::RING-1"] == {"suppressed": True, "suppressedReason": "Price too high", "fixHint": "Lower the price"})
check("the byte-order mark Amazon puts first is not left in the first column's name", table.read(GOOD).columns[0] == "Status" and said is not None and not said.not_read)
other_language = a_file([a_row("X-1", "B0AAAAAAA3")], head=["Statut", "Raison", "Référence", "Code", "Nom", "État", "Date", "Description du problème"])
check("a header in another language is read by position",
      "amazon::B0AAAAAAA3::X-1" in (answered(lambda: tool.read_suppressed(other_language)) or tool.WhatNotesSaid({}, (), 0)).notes)
swapped = a_file([a_row("X-1", "B0AAAAAAA3")], head=["Status", "Reason", "ASIN", "SKU", "Product name", "Condition", "Status Change Date", "Issue Description"])
check("an English header with SKU and ASIN the other way round is refused, so one is never read as the other",
      "puts its SKU column at 4" in why(lambda: tool.read_suppressed(swapped)) and "Nothing was read" in why(lambda: tool.read_suppressed(swapped)))
check("a file with fewer columns than Amazon's page names is refused in words",
      "has 3 columns" in why(lambda: tool.read_suppressed(a_file([["a", "b", "c"]], head=["a", "b", "c"]))))
none_hidden = answered(lambda: tool.read_suppressed(a_file([])))
check("a file with its headings and no row is nothing suppressed, not a refusal", none_hidden is not None and none_hidden.notes == {} and none_hidden.rows_in_file == 0)
check("a file with nothing in it at all is refused", "empty" in why(lambda: tool.read_suppressed(b"")))
bad = answered(lambda: tool.read_suppressed(a_file([a_row("", "B0AAAAAAA4"), a_row("A/B", "B0AAAAAAA5"), a_row("OK-1", "not an asin!"), a_row("OK-2", "B0AAAAAAA6")])))
check("rows that could not name a listing are said by line and the rest are read",
      bad is not None and len(bad.not_read) == 3 and bad.not_read[0].startswith("line 2") and set(bad.notes) == {"amazon::B0AAAAAAA6::OK-2"})
twice = answered(lambda: tool.read_suppressed(a_file([a_row("T-1", "B0AAAAAAA7"), a_row("T-1", "B0AAAAAAA7", "Other", "Other")])))
check("a listing named twice keeps the first and says so", twice is not None and len(twice.notes) == 1 and "line 3 already names" not in twice.not_read[0] and "line 3" in twice.not_read[0] and "line 2 already names" in twice.not_read[0])
torn = answered(lambda: tool.read_suppressed(a_file([a_row("T-1", "B0AAAAAAA7"), ["only", "three", "cells"]])))
check("a row of the wrong width is said as a row not read and counted in the file, so a torn file does not read as read in full",
      torn is not None and len(torn.notes) == 1 and len(torn.not_read) == 1 and torn.not_read[0].startswith("line 3") and torn.rows_in_file == 2)
check("the reader is found by report id, and an id it does not know is refused",
      tool.read_notes_file("az_suppressed", GOOD).notes == said.notes and "Nothing here knows" in why(lambda: tool.read_notes_file("fk_orders", GOOD)))
key_in_listings = f"amazon::{'B0AAAAAAA1'}::BANGLE-5 FIVE"
check("the name a note is filed under is the one the listing file files its listing under (D326)",
      listings.the_review_id({"platform": "amazon", "platformId": "B0AAAAAAA1::BANGLE-5 FIVE"}) == key_in_listings)

# ---------------------------------------------------------------- the write

write = answered(lambda: firestore.a_listing_note_write("p", "amazon::B0AAAAAAA2::RING-1", {"suppressed": True, "suppressedReason": "r", "fixHint": "f", "suppressedOn": "2026-10-02"}))
check("a note is written with a mask naming only its own fields, so the listing beside it is never erased",
      write is not None and write["updateMask"]["fieldPaths"] == ["fixHint", "suppressed", "suppressedOn", "suppressedReason"]
      and write["update"]["fields"]["suppressed"] == {"booleanValue": True} and "listing" not in write["update"]["fields"])
def refused(work):
    try:
        work()
    except firestore.Refused as wrong:
        return str(wrong)
    return ""


check("a field outside the notes' list is refused", "not" in refused(lambda: firestore.a_listing_note_write("p", "x", {"stock": 3})))
check("a note that holds nothing is refused", "nothing" in refused(lambda: firestore.a_listing_note_write("p", "x", {})))
check("a fee goes as money and a text in the fee's place is refused",
      firestore.a_listing_note_write("p", "x", {"referralFee": 12.5, "feeAsOf": "2026-10-02"})["update"]["fields"]["referralFee"] == {"doubleValue": 12.5}
      and refused(lambda: firestore.a_listing_note_write("p", "x", {"referralFee": "12"})))
the_listing = {
    "platform": "amazon", "platformId": "B0AAAAAAA2::RING-1", "sku": "RING-1", "productName": "n", "stock": 1, "mrp": 1, "sellingPrice": 1,
    "settlement": None, "buyerLink": "", "state": "live", "stateReason": "", "platformVariation": "", "catalogId": "", "listingId": "",
}
whole = firestore.a_listing_write("p", the_listing, "az_listings", "2026-10-02")
check("a listing's own write now carries a mask of its own four fields, so a note beside it survives the listing being written again",
      whole.get("updateMask", {}).get("fieldPaths") == ["changedOn", "id", "listing", "report"])

# ---------------------------------------------------------------- the sink: only listings that are held, only what differs


class Reply:
    def __init__(self, status=200, body=None):
        self.status, self._body, self.text = status, body if body is not None else {}, str(body or "")

    ok = property(lambda self: 200 <= self.status < 300)

    def json(self):
        return self._body

    def records(self):
        return self._body if isinstance(self._body, list) else None


class Transport:
    """`held` is {record id: fields as Firestore holds them}."""

    def __init__(self, held=None, fail_on=None, not_a_list=False):
        self.posts, self.held, self.fail_on, self.not_a_list = [], held or {}, fail_on, not_a_list

    def post(self, url, params=None, headers=None, json=None, data=None):
        self.posts.append({"url": url, "json": json})
        if url.endswith(":batchGet"):
            if self.not_a_list:
                return Reply(200, {"oops": 1})
            return Reply(200, [
                {"found": {"name": n, "fields": self.held[n.rsplit("/", 1)[-1]]}} if n.rsplit("/", 1)[-1] in self.held else {"missing": n}
                for n in json["documents"]
            ])
        if url.endswith(":runQuery"):
            # One field filter, compared as Firestore compares plain values: a record without the field never matches.
            asked = json["structuredQuery"]["where"]["fieldFilter"]
            field, op = asked["field"]["fieldPath"], asked["op"]
            want = firestore.plain({"v": asked["value"]})["v"]
            compare = {"EQUAL": lambda a: a == want, "GREATER_THAN_OR_EQUAL": lambda a: not isinstance(a, bool) and a >= want}[op]
            return Reply(200, [
                {"document": {"name": f"projects/p/databases/(default)/documents/listings_seen/{name}", "fields": fields}}
                for name, fields in self.held.items()
                if field in fields and compare(firestore.plain({"v": fields[field]})["v"])
            ])
        return Reply(self.fail_on or 200, {})

    def commits(self):
        return [w for p in self.posts if p["url"].endswith(":commit") for w in p["json"]["writes"]]


RING, BANGLE = "amazon::B0AAAAAAA2::RING-1", "amazon::B0AAAAAAA1::BANGLE-5 FIVE"
LISTED = firestore.a_listing_write("p", the_listing, "az_listings", "2026-10-02")["update"]["fields"]
notes = said.notes if said else {}
t = Transport(held={RING: LISTED})
put = answered(lambda: firestore_door.a_listing_notes_sink(t, "p")("az_suppressed", "2026-10-03", notes))
check("only a listing whose record is already held gets its note: one is written, the one with no record is not made up",
      put == (1, 1) and [w["update"]["name"].rsplit("/", 1)[-1] for w in t.commits()] == [RING])
check("the note carries the day of the file it came from, as suppressedOn",
      t.commits() and t.commits()[0]["update"]["fields"]["suppressedOn"] == {"stringValue": "2026-10-03"})
now_held = {RING: {**LISTED, **t.commits()[0]["update"]["fields"]}} if t.commits() else {}
again = Transport(held=now_held)
check("the same file again writes nothing", answered(lambda: firestore_door.a_listing_notes_sink(again, "p")("az_suppressed", "2026-10-03", notes)) == (0, 1) and again.commits() == [])
changed = Transport(held=now_held)
check("a new reason is written again",
      answered(lambda: firestore_door.a_listing_notes_sink(changed, "p")("az_suppressed", "2026-10-04", {RING: {**notes[RING], "suppressedReason": "New"}})) == (1, 0))
late = Transport(held=now_held)
check("a file of an earlier day never puts older words over newer ones",
      answered(lambda: firestore_door.a_listing_notes_sink(late, "p")("az_suppressed", "2026-10-01", {RING: {**notes[RING], "suppressedReason": "Old"}})) == (0, 0))
try:
    firestore_door.a_listing_notes_sink(Transport(held={RING: LISTED}, fail_on=403), "p")("az_suppressed", "2026-10-03", notes)
    check("a database that says no raises, so the file is not marked read", False)
except firestore_door.TheirDatabaseSaidNo:
    check("a database that says no raises, so the file is not marked read", True)
try:
    firestore_door.a_listing_notes_sink(Transport(not_a_list=True), "p")("az_suppressed", "2026-10-03", notes)
    check("an answer that is not a list is not read as nothing held", False)
except firestore_door.TheirDatabaseSaidNo:
    check("an answer that is not a list is not read as nothing held", True)

# ---------------------------------------------------------------- the night


class Night:
    def __init__(self, files, bodies, record=True, error=None):
        self.files, self.bodies, self.written, self.error, self.complete = files, bodies, [], error, []
        self.record = self.write if record else None

    def write(self, report_id, day, found, complete=False):
        if self.error:
            raise self.error
        self.written.append((report_id, day, found))
        self.complete.append(complete)
        return len(found), 1

    def go(self, already=()):
        return answered(lambda: reading.read_what_is_new(
            already_read=already,
            what_is_in_the_folder=lambda r: list(self.files.get(r, ())),
            bring_it_back=lambda w: self.bodies[w],
            record_the_sales=lambda readings: None,
            record_notes=self.record,
        ))


FILES = {"az_suppressed": [whats_new.InTheFolder(which="s1", name="amazon_az_suppressed_2026-10-02.txt", size=100)]}
night = Night(FILES, {"s1": GOOD})
was = night.go()
check("a night reads the suppressed file and hands its notes over with the file's day",
      was is not None and was.read_tonight and [(r, d, set(n)) for r, d, n in night.written] == [("az_suppressed", "2026-10-02", set(notes))])
check("it is written down as read and the notes are counted", was is not None and was.files_read == ("s1",) and was.notes_written == 2 and was.notes_skipped == 1 and "1 listing(s) named in a side file had no record" in was.says())
check("the standing record says what the file held and what was read",
      was is not None and [(r.report_id, r.rows_in_file, r.rows_read, r.into) for r in was.reads] == [("az_suppressed", 2, 2, "notes on listings")])
check("and the night's summary says how many listings were noted", was is not None and "2 listing(s) were marked" in was.says())
check("a file already read is not read again", (answered(lambda: Night(FILES, {"s1": GOOD}).go(already=("s1",))) or was).read_tonight == ())
nowhere = Night(FILES, {"s1": GOOD}, record=False).go()
check("with nowhere to write them the file is not opened and not marked read, and the night says so",
      nowhere is not None and nowhere.read_tonight == () and not nowhere.files_read and nowhere.notes_waiting == 1 and "left unread" in nowhere.says())
broken = Night(FILES, {"s1": GOOD}, error=RuntimeError("would not take it")).go()
check("a database that fails leaves the file unread and says why", broken is not None and broken.read_tonight == () and "would not take it" in broken.could_not_read[0])
refusing = Night(FILES, {"s1": GOOD}, error=firestore_door.TheirDatabaseSaidNo("403")).go()
check("a database that says no is OUR defect", refusing is not None and refusing.is_a_defect and refusing.read_tonight == ())
partly = Night(FILES, {"s1": a_file([a_row("", "B0AAAAAAA4"), a_row("OK-2", "B0AAAAAAA6")])}).go()
check("a file with one bad row is read and the bad row is said by line",
      partly is not None and partly.read_tonight == ("s1",) and partly.rows_refused == 1 and "1 row(s) not read" in partly.could_not_read[0])
hopeless = Night(FILES, {"s1": a_file([a_row("", "B0AAAAAAA4")])}).go()
check("a file in which no row could be read is NOT marked read", hopeless is not None and hopeless.read_tonight == () and "no row of" in hopeless.could_not_read[0])
nameless = Night({"az_suppressed": [whats_new.InTheFolder(which="s2", name="suppressed.txt", size=100)]}, {"s2": GOOD}).go()
check("a file with no day in its name is refused like every other reader's", nameless is not None and nameless.read_tonight == () and "no day in its name" in nameless.could_not_read[0])
check("az_suppressed is read now and no longer says it is not",
      reading.why_a_report_has_no_decision() == "" and "az_suppressed" not in reading.WHAT_IS_FETCHED_AND_NOT_READ_YET
      and [o.report_id for o in reading.WHAT_NOTES_CAN_BE_READ] == ["az_suppressed", "az_fee_preview", "me_pricing"])


# ---------------------------------------------------------------- the fee side (job 2): lane 1's real `listings.WhatFeesSaid`, joined at AP10


FEES = listings.WhatFeesSaid({RING: 12.5, BANGLE: 0}, ("line 4 (X): the fee reads 'free', which is not an amount of money. A fee nobody can read is not set",), 3)
fee_notes = answered(lambda: tool.notes_from_fees(FEES))
check("each fee becomes a referralFee note on its listing, the 0.00 Amazon gave kept as a figure",
      fee_notes is not None and fee_notes.notes == {RING: {"referralFee": 12.5}, BANGLE: {"referralFee": 0}})
check("the rows the fee reader would not take and the rows in the file go through, so the night says them",
      fee_notes is not None and fee_notes.not_read == FEES.not_read and fee_notes.rows_in_file == 3)
fee_t = Transport(held={RING: LISTED, BANGLE: LISTED})
fee_put = answered(lambda: firestore_door.a_listing_notes_sink(fee_t, "p")("az_fee_preview", "2026-10-05", fee_notes.notes))
check("the sink writes referralFee with feeAsOf, masked to those two fields, on each held record",
      fee_put == (2, 0) and all(sorted(w["updateMask"]["fieldPaths"]) == ["feeAsOf", "referralFee"] for w in fee_t.commits())
      and fee_t.commits()[0]["update"]["fields"]["feeAsOf"] == {"stringValue": "2026-10-05"})
fee_held = {n: {**LISTED, **w["update"]["fields"]} for w, n in zip(fee_t.commits(), (BANGLE, RING))}
check("the same fees a day later write nothing, and an older file's fee never lands over a newer one",
      answered(lambda: firestore_door.a_listing_notes_sink(Transport(held=fee_held), "p")("az_fee_preview", "2026-10-06", fee_notes.notes)) == (0, 0)
      and answered(lambda: firestore_door.a_listing_notes_sink(Transport(held=fee_held), "p")("az_fee_preview", "2026-10-01", {RING: {"referralFee": 99.0}})) == (0, 0))
check("a fee that changed is written again",
      answered(lambda: firestore_door.a_listing_notes_sink(Transport(held=fee_held), "p")("az_fee_preview", "2026-10-06", {RING: {"referralFee": 13.0}})) == (1, 0))

# **THE JOIN (AP10): a real tab-separated fee file, as Amazon makes it, through lane 1's reader and lane 2's notes, on a night.**
FEE_FILE = ("seller-sku\tasin\titem-name\tprice\testimated-referral-fee-per-item\r\n"
            "RING-1\tB0AAAAAAA2\tA ring\t399.00\t59.85\r\n"
            "BANGLE-5 FIVE\tB0AAAAAAA1\tA bangle\t250.00\t0.00\r\n"
            "NOFEE-1\tB0AAAAAAA3\tNo fee\t100.00\t--\r\n").encode("utf-8")
fee_read = answered(lambda: tool.read_notes_file("az_fee_preview", FEE_FILE, "the fee file"))
check("a real fee file is read by its own reader into referralFee notes, 0.00 kept and '--' read as no fee, never as a row not read (AP10 review)",
      fee_read is not None and fee_read.notes == {RING: {"referralFee": 59.85}, BANGLE: {"referralFee": 0}}
      and fee_read.not_read == () and fee_read.rows_in_file == 3)
fee_night = Night({"az_fee_preview": [whats_new.InTheFolder(which="f1", name="amazon_az_fee_preview_2026-10-05.txt", size=100)]}, {"f1": FEE_FILE})
fee_was = fee_night.go()
check("a night reads the fee file and hands its referralFee notes over with the file's day",
      fee_was is not None and fee_was.read_tonight == ("f1",)
      and [(r, d, n) for r, d, n in fee_night.written] == [("az_fee_preview", "2026-10-05", {RING: {"referralFee": 59.85}, BANGLE: {"referralFee": 0}})])
check("and a fee file with a '--' row is not said to be unread: read in full, nothing said as not read (AP10 review)",
      fee_was is not None and not fee_was.could_not_read
      and [(r.report_id, r.rows_in_file, r.rows_read) for r in fee_was.reads] == [("az_fee_preview", 3, 3)])
ALL_NO_FEE = ("seller-sku\tasin\titem-name\tprice\testimated-referral-fee-per-item\r\nNOFEE-1\tB0AAAAAAA3\tNo fee\t100.00\t--\r\n").encode("utf-8")
none_night = Night({"az_fee_preview": [whats_new.InTheFolder(which="f2", name="amazon_az_fee_preview_2026-10-05.txt", size=100)]}, {"f2": ALL_NO_FEE}).go()
check("a fee file in which Amazon gave no estimate for any row is read, not refused and asked again every night",
      none_night is not None and none_night.read_tonight == ("f2",) and not none_night.could_not_read)
# **SIDE FILES AFTER LISTING FILES (AP10 review):** a note lands only on a record already held, so a same-day fee or suppressed file taken before the
# listings file would find no record, be marked read for good, and write nothing until the next file.
LISTING_FIRST = reading._oldest_first(
    {"az_fee_preview": [whats_new.InTheFolder(which="a1", name="amazon_az_fee_preview_2026-10-05.txt", size=1)],
     "az_suppressed": [whats_new.InTheFolder(which="a2", name="amazon_az_suppressed_2026-10-05.txt", size=1)],
     "az_listings": [whats_new.InTheFolder(which="z9", name="amazon_az_listings_2026-10-05.txt", size=1)]},
    reading.WHAT_LISTINGS_CAN_BE_READ + reading.WHAT_NOTES_CAN_BE_READ, ())
check("a same-day listings file is taken before the side files about its listings, whatever Drive's ids say",
      [one.which for _, one in LISTING_FIRST][0] == "z9" and len(LISTING_FIRST) == 3)

# ---------------------------------------------------------------- taken back (D633, AP11): a later COMPLETE file no longer naming the listing

# RING suppressed on 3 Oct, BANGLE suppressed on 3 Oct; RING and BANGLE both carry a fee from 5 Oct.
SUPPRESSED_HELD = {
    RING: {**LISTED, "suppressed": {"booleanValue": True}, "suppressedReason": {"stringValue": "Missing image"},
           "fixHint": {"stringValue": "Add one"}, "suppressedOn": {"stringValue": "2026-10-03"}},
    BANGLE: {**LISTED, "suppressed": {"booleanValue": True}, "suppressedReason": {"stringValue": "Price"},
             "fixHint": {"stringValue": "Fix it"}, "suppressedOn": {"stringValue": "2026-10-03"}},
}
gone = Transport(held=SUPPRESSED_HELD)
gone_put = answered(lambda: firestore_door.a_listing_notes_sink(gone, "p")(
    "az_suppressed", "2026-10-06", {BANGLE: dict(firestore.plain({k: SUPPRESSED_HELD[BANGLE][k] for k in ("suppressed", "suppressedReason", "fixHint")}))},
    complete=True))
cleared = [w for w in gone.commits() if w["update"]["name"].endswith(RING)]
check("A SUPPRESSION A LATER COMPLETE FILE NO LONGER NAMES IS TAKEN BACK: not suppressed, Amazon's reason and hint taken away, with the file's day",
      gone_put == (1, 0) and len(gone.commits()) == 1 and len(cleared) == 1
      and cleared[0]["update"]["fields"] == {"suppressed": {"booleanValue": False}, "suppressedOn": {"stringValue": "2026-10-06"}}
      and sorted(cleared[0]["updateMask"]["fieldPaths"]) == ["fixHint", "suppressed", "suppressedOn", "suppressedReason"])
part = Transport(held=SUPPRESSED_HELD)
check("a partial suppressed file (a row it could not read) takes nothing back -- the row it lost may be that listing",
      answered(lambda: firestore_door.a_listing_notes_sink(part, "p")("az_suppressed", "2026-10-06", {}, complete=False)) == (0, 0)
      and part.commits() == [])
older = Transport(held=SUPPRESSED_HELD)
check("an older complete file takes back nothing a newer file said",
      answered(lambda: firestore_door.a_listing_notes_sink(older, "p")("az_suppressed", "2026-10-01", {}, complete=True)) == (0, 0)
      and older.commits() == [])
already = Transport(held={RING: {**LISTED, "suppressed": {"booleanValue": False}, "suppressedOn": {"stringValue": "2026-10-06"}}})
check("a listing already taken back is not written again every night",
      answered(lambda: firestore_door.a_listing_notes_sink(already, "p")("az_suppressed", "2026-10-07", {}, complete=True)) == (0, 0)
      and already.commits() == [])
FEES_HELD = {RING: {**LISTED, "referralFee": {"doubleValue": 59.85}, "feeAsOf": {"stringValue": "2026-10-05"}},
             BANGLE: {**LISTED, "referralFee": {"integerValue": "0"}, "feeAsOf": {"stringValue": "2026-10-05"}}}
fee_gone = Transport(held=FEES_HELD)
fee_gone_put = answered(lambda: firestore_door.a_listing_notes_sink(fee_gone, "p")("az_fee_preview", "2026-10-07", {BANGLE: {"referralFee": 0}}, complete=True))
check("A FEE A LATER COMPLETE FILE NO LONGER GIVES IS TAKEN AWAY, never written as nought (0.00 is a figure Amazon gives), with the file's day",
      fee_gone_put == (1, 0) and [w["update"]["name"].rsplit("/", 1)[-1] for w in fee_gone.commits()] == [RING]
      and fee_gone.commits()[0]["update"]["fields"] == {"feeAsOf": {"stringValue": "2026-10-07"}}
      and sorted(fee_gone.commits()[0]["updateMask"]["fieldPaths"]) == ["feeAsOf", "referralFee"])
fee_part = Transport(held=FEES_HELD)
check("a partial fee file takes no fee away",
      answered(lambda: firestore_door.a_listing_notes_sink(fee_part, "p")("az_fee_preview", "2026-10-07", {BANGLE: {"referralFee": 0}})) == (0, 0)
      and fee_part.commits() == [])
CLEAN = Night(FILES, {"s1": GOOD})
CLEAN.go()
TORN = Night(FILES, {"s1": a_file([a_row("", "B0AAAAAAA4"), a_row("OK-2", "B0AAAAAAA6")])})
TORN.go()
check("the night says a file is complete only when every row of it was read",
      CLEAN.complete == [True] and TORN.complete == [False])

# ---------------------------------------------------------------- Meesho pricing (N017, his D726; plan piece 43)
# **THE FILE IS THE EXTENSION'S OWN (`extension/tables.js` `meesho-pricing`), so its header is the one the walker writes. NO PRICING FILE HAS EVER LANDED IN HIS DRIVE**
# (the fetch failed every night): the rows below are made up to that header. The text inside a price cell is therefore not known -- only the FIRST piece of a cell is
# read as the price, and a cell whose first piece is not an amount is a row not read, never a guess.
RUPEE_SIGN = chr(0x20B9)
PHEAD = '"Product","Catalog ID","SKU ID","Tab counts","Current Stock","Growth in 30 days","Current Customer Price","Recommended Customer Price","Insights"'


def a_price_row(product, catalog, sku, current, recommended, label="Losing Views"):
    return f'"{product}","{catalog}","{sku}","All Products (6)","5","3%","{current}","{recommended}","{label}"'


def a_price_file(*rows, head=PHEAD):
    return ("\n".join([head, *rows]) + "\n").encode("utf-8")


def a_shop_listing(product_id, variation, sku, catalog, title):
    return {"platform": "meesho", "platformId": f"{product_id}::{variation}", "sku": sku, "catalogId": catalog, "productName": title}


SHOP = {one["platform"] + "::" + one["platformId"]: one for one in (
    a_shop_listing("1001", "1", "DJ-1", "555", "Gold Jhumka"), a_shop_listing("1001", "2", "DJ-1", "555", "Gold Jhumka"),
    a_shop_listing("2002", "1", "R-9", "777", "Silver Ring"),
    a_shop_listing("3003", "1", "S 5", "888", "Twin Title"), a_shop_listing("4004", "1", "T-1", "999", "Twin Title"),
)}
L_DJ1, L_DJ2, L_RING = "meesho::1001::1", "meesho::1001::2", "meesho::2002::1"
priced = answered(lambda: tool.read_pricing(a_price_file(
    a_price_row("Gold Jhumka", "555", "DJ-1", RUPEE_SIGN + "1,199", RUPEE_SIGN + "999", "Losing Views"),
    a_price_row("Silver Ring", "", "", RUPEE_SIGN + "250.50", "", "Best Priced"),
), "the pricing file", SHOP))
check("PRICING: a row matched by its SKU puts the three figures on EVERY listing with that SKU (two variations here), commas read as thousands",
      priced is not None and priced.notes[L_DJ1] == priced.notes[L_DJ2]
      == {"currentPrice": 1199, "recommendedPrice": 999, "priceLabel": "Losing Views"} and priced.rows_in_file == 2)
check("a row with no SKU and no catalogue id is matched by its title when the title belongs to one catalogue; a blank recommended price is null, said as such, never nought",
      priced is not None and priced.notes[L_RING] == {"currentPrice": 250.5, "recommendedPrice": None, "priceLabel": "Best Priced"} and not priced.not_read)
by_catalog = answered(lambda: tool.read_pricing(a_price_file(a_price_row("Whatever the page called it", "777", "NOT-A-SKU", RUPEE_SIGN + "300", RUPEE_SIGN + "280")), "f", SHOP))
check("a SKU nobody has falls back to the catalogue id, and the row is matched",
      by_catalog is not None and set(by_catalog.notes) == {L_RING} and not by_catalog.not_read)
parts = answered(lambda: tool.read_pricing(a_price_file(a_price_row("Gold Jhumka", "555", "DJ-1", RUPEE_SIGN + "199 | Margin: " + RUPEE_SIGN + "100", RUPEE_SIGN + "179 | Margin: x")), "f", SHOP))
check("only the first piece of a price cell is the price, the rest is not read as anything",
      parts is not None and parts.notes[L_DJ1]["currentPrice"] == 199 and parts.notes[L_DJ1]["recommendedPrice"] == 179)
bad_rows = answered(lambda: tool.read_pricing(a_price_file(
    a_price_row("Twin Title", "", "", RUPEE_SIGN + "100", RUPEE_SIGN + "90"),
    a_price_row("Nobody Sells This", "", "", RUPEE_SIGN + "100", RUPEE_SIGN + "90"),
    a_price_row("Gold Jhumka", "555", "DJ-1", "", RUPEE_SIGN + "90"),
    a_price_row("Gold Jhumka", "555", "DJ-1", "price on request", RUPEE_SIGN + "90"),
    a_price_row("Gold Jhumka", "555", "DJ-1", RUPEE_SIGN + "100", "soon"),
    a_price_row("Gold Jhumka", "777", "DJ-1", RUPEE_SIGN + "100", RUPEE_SIGN + "90"),
    a_price_row("Silver Ring", "777", "R-9", RUPEE_SIGN + "260", RUPEE_SIGN + "240"),
), "f", SHOP))
check("EVERY ROW THAT CANNOT BE PUT ON A LISTING IS SAID BY LINE AND NEVER DROPPED SILENTLY: a title shared by two catalogues, a title nobody has, no current price, a price that is not an amount, a recommended price that is not one, a SKU and catalogue that disagree",
      bad_rows is not None and len(bad_rows.not_read) == 6 and all(x.startswith(f"line {n} ") for n, x in zip(range(2, 8), bad_rows.not_read))
      and set(bad_rows.notes) == {L_RING} and bad_rows.rows_in_file == 7)
check("and each of them says why: two catalogues, no listing, no current price, not an amount",
      bad_rows is not None and "2 catalogues" in bad_rows.not_read[0] and "no listing" in bad_rows.not_read[1] and "current price" in bad_rows.not_read[2]
      and "not an amount" in bad_rows.not_read[3] and "recommended" in bad_rows.not_read[4] and "disagree" in bad_rows.not_read[5])
twice_priced = answered(lambda: tool.read_pricing(a_price_file(
    a_price_row("Silver Ring", "777", "R-9", RUPEE_SIGN + "260", RUPEE_SIGN + "240"), a_price_row("Silver Ring", "777", "R-9", RUPEE_SIGN + "999", RUPEE_SIGN + "1")), "f", SHOP))
check("a listing named by two rows keeps the first and says the second was not used",
      twice_priced is not None and twice_priced.notes[L_RING]["currentPrice"] == 260 and len(twice_priced.not_read) == 1 and "already" in twice_priced.not_read[0])
torn_price = answered(lambda: tool.read_pricing(
    ("\n".join([PHEAD, a_price_row("Silver Ring", "777", "R-9", RUPEE_SIGN + "260", RUPEE_SIGN + "240"), '"Gold Jhumka","555"']) + "\n").encode("utf-8"), "f", SHOP))
check("PRICING: A TORN ROW (the wrong width) IS A ROW NOT READ AND COUNTED IN THE FILE, so a torn file does not read as read in full",
      torn_price is not None and len(torn_price.notes) == 1 and len(torn_price.not_read) == 1 and torn_price.not_read[0].startswith("line 3") and torn_price.rows_in_file == 2)
check("a pricing file missing a column is refused in words naming the columns it has",
      "Nothing was read" in why(lambda: tool.read_pricing(a_price_file(a_price_row("a", "1", "b", "1", "1"), head='"Product","Catalog ID","SKU ID"'), "f", SHOP)))
SHOP2 = {one["platform"] + "::" + one["platformId"]: one for one in (
    a_shop_listing("5001", "1", "X", "A", "Ring A"), a_shop_listing("5002", "1", "X", "B", "Ring B"),
    a_shop_listing("6001", "1", "RING", "C", "Ring C"), a_shop_listing("6002", "1", "NECK", "C", "Necklace C"),
    a_shop_listing("7001", "1", "S1", "D", "Sized D"), a_shop_listing("7001", "2", "S1", "D", "Sized D"),
)}
two_cat = answered(lambda: tool.read_pricing(a_price_file(
    a_price_row("Ring B", "B", "X", RUPEE_SIGN + "500", RUPEE_SIGN + "450"),
    a_price_row("Ring A or B", "", "X", RUPEE_SIGN + "100", RUPEE_SIGN + "90"),
), "f", SHOP2))
check("N017 REVIEW: A SKU SHARED BY TWO CATALOGUES GETS ONLY THE CATALOGUE THE ROW NAMES, and a row that names none is not matched (which is meant cannot be said)",
      two_cat is not None and two_cat.notes == {"meesho::5002::1": {"currentPrice": 500, "recommendedPrice": 450, "priceLabel": "Losing Views"}}
      and len(two_cat.not_read) == 1 and "2 catalogues" in two_cat.not_read[0])
cat_fallback = answered(lambda: tool.read_pricing(a_price_file(
    a_price_row("x", "C", "UNKNOWN-SKU", RUPEE_SIGN + "100", RUPEE_SIGN + "90"),
    a_price_row("x", "D", "UNKNOWN-2", RUPEE_SIGN + "70", RUPEE_SIGN + "60"),
), "f", SHOP2))
check("N017 REVIEW: THE CATALOGUE-ID FALLBACK NEVER SPREADS ONE PRICE OVER SEVERAL PRODUCTS: a catalogue of two SKUs is not matched, a catalogue of one SKU in two sizes is",
      cat_fallback is not None and set(cat_fallback.notes) == {"meesho::7001::1", "meesho::7001::2"}
      and len(cat_fallback.not_read) == 1 and "more than one product" in cat_fallback.not_read[0])
loose = answered(lambda: tool.read_pricing(a_price_file(
    a_price_row("Ring C", "C", "RING", "12%", RUPEE_SIGN + "90"), a_price_row("Necklace C", "C", "NECK", "Rs 100", RUPEE_SIGN + "90"),
), "f", SHOP2))
check("N017 REVIEW: A PRICE CELL THAT IS NOT PLAINLY AN AMOUNT (a percentage, words) IS A ROW NOT READ, not a price",
      loose is not None and not loose.notes and len(loose.not_read) == 2 and all("not an amount" in x for x in loose.not_read))
huge = answered(lambda: tool.read_pricing(a_price_file(
    a_price_row("Ring C", "C", "RING", "1e3000000", RUPEE_SIGN + "90"), a_price_row("Necklace C", "C", "NECK", RUPEE_SIGN + "99999999999", RUPEE_SIGN + "90"),
    a_price_row("Sized D", "D", "S1", RUPEE_SIGN + "1,250.5", RUPEE_SIGN + "90", "x" * 5000),
), "f", SHOP2))
check("N017 SECURITY: AN EXPONENT OR A PRICE PAST TEN MILLION IS A ROW NOT READ (never a hang or a write the database refuses), and a label is cut to 200 characters",
      huge is not None and len(huge.not_read) == 2 and huge.notes["meesho::7001::1"]["currentPrice"] == 1250.5
      and len(huge.notes["meesho::7001::1"]["priceLabel"]) == 200)
check("without the shop's listings (no catalog file yet) it is refused rather than every row being flagged unmatched for good",
      "listings" in why(lambda: tool.read_pricing(a_price_file(a_price_row("a", "1", "b", "1", "1")), "f", None)))
check("a pricing file with its headings and no row is refused, as an empty listing file is",
      "not one" in why(lambda: tool.read_pricing(a_price_file(), "f", SHOP)))
check("the reader is found by report id, and gets the shop's listings", tool.read_notes_file("me_pricing", a_price_file(
    a_price_row("Silver Ring", "777", "R-9", RUPEE_SIGN + "260", RUPEE_SIGN + "240")), "f", SHOP).notes[L_RING]["currentPrice"] == 260)

price_write = answered(lambda: firestore.a_listing_note_write("p", L_RING, {
    "currentPrice": 260, "recommendedPrice": None, "priceLabel": "Best Priced", "priceAsOf": "2026-10-26"}))
check("PRICING: the write is masked to the pricing fields only, a missing recommendation goes as null, and the listing beside it is never touched",
      price_write is not None and price_write["updateMask"]["fieldPaths"] == ["currentPrice", "priceAsOf", "priceLabel", "recommendedPrice"]
      and price_write["update"]["fields"]["recommendedPrice"] == {"nullValue": None} and "listing" not in price_write["update"]["fields"]
      and price_write["update"]["fields"]["currentPrice"] == {"integerValue": "260"})
check("a price that is text, or a price day that is not a day, is refused",
      refused(lambda: firestore.a_listing_note_write("p", L_RING, {"currentPrice": "260"}))
      and refused(lambda: firestore.a_listing_note_write("p", L_RING, {"priceAsOf": "yesterday"})))
price_t = Transport(held={L_RING: LISTED, L_DJ1: LISTED})
price_put = answered(lambda: firestore_door.a_listing_notes_sink(price_t, "p")("me_pricing", "2026-10-26", {L_RING: priced.notes[L_RING], L_DJ1: priced.notes[L_DJ1], L_DJ2: priced.notes[L_DJ2]}))
check("the sink writes the pricing on each held record with priceAsOf; the variation with no record yet is skipped, not made up",
      price_put == (2, 1) and all("priceAsOf" in w["updateMask"]["fieldPaths"] for w in price_t.commits())
      and price_t.commits()[0]["update"]["fields"]["priceAsOf"] == {"stringValue": "2026-10-26"})
price_held = {n: {**LISTED, **w["update"]["fields"]} for w, n in zip(price_t.commits(), (L_DJ1, L_RING))}
check("the same file again writes nothing, an older file's price never lands over a newer one, and a changed price is written again",
      answered(lambda: firestore_door.a_listing_notes_sink(Transport(held=price_held), "p")("me_pricing", "2026-10-27", {L_RING: priced.notes[L_RING]})) == (0, 0)
      and answered(lambda: firestore_door.a_listing_notes_sink(Transport(held=price_held), "p")("me_pricing", "2026-10-20", {L_RING: {**priced.notes[L_RING], "currentPrice": 1}})) == (0, 0)
      and answered(lambda: firestore_door.a_listing_notes_sink(Transport(held=price_held), "p")("me_pricing", "2026-10-27", {L_RING: {**priced.notes[L_RING], "currentPrice": 240}})) == (1, 0))
price_gone = Transport(held=price_held)
price_gone_put = answered(lambda: firestore_door.a_listing_notes_sink(price_gone, "p")("me_pricing", "2026-10-28", {L_DJ1: priced.notes[L_DJ1]}, complete=True))
check("A PRICE A LATER COMPLETE FILE NO LONGER NAMES IS TAKEN OFF THE LISTING (all three figures), with the file's day, and never written as nought",
      price_gone_put == (1, 0) and [w["update"]["name"].rsplit("/", 1)[-1] for w in price_gone.commits()] == [L_RING]
      and price_gone.commits()[0]["update"]["fields"] == {"priceAsOf": {"stringValue": "2026-10-28"}}
      and sorted(price_gone.commits()[0]["updateMask"]["fieldPaths"]) == ["currentPrice", "priceAsOf", "priceLabel", "recommendedPrice"])
price_part = Transport(held=price_held)
check("a partial pricing file takes no price away",
      answered(lambda: firestore_door.a_listing_notes_sink(price_part, "p")("me_pricing", "2026-10-28", {L_DJ1: priced.notes[L_DJ1]})) == (0, 0) and price_part.commits() == [])


def _the_shop_file(how, one, body):
    return type("Said", (), {"records": SHOP})(), "2026-10-20"


PRICING_FILES = {"me_pricing": [whats_new.InTheFolder(which="p1", name="meesho_me_pricing_2026-10-26.csv", size=100)],
                 "me_catalog": [whats_new.InTheFolder(which="c1", name="meesho_me_catalog_2026-10-20.xlsx", size=100)]}
PRICING_BODY = a_price_file(a_price_row("Silver Ring", "777", "R-9", RUPEE_SIGN + "260", RUPEE_SIGN + "240", "Best Priced"))
_real_listings_reading = reading.a_listings_reading
reading.a_listings_reading = _the_shop_file
try:
    price_night = Night(PRICING_FILES, {"p1": PRICING_BODY, "c1": b"the catalogue file, made up"})
    price_was = price_night.go(already=("c1",))
finally:
    reading.a_listings_reading = _real_listings_reading
check("PRICING: a night matches the file against the newest me_catalog file's listings and hands the notes over with the file's day",
      price_was is not None and price_was.read_tonight == ("p1",)
      and [(r, d, n) for r, d, n in price_night.written] == [("me_pricing", "2026-10-26", {L_RING: {"currentPrice": 260, "recommendedPrice": 240, "priceLabel": "Best Priced"}})]
      and [(r.report_id, r.rows_in_file, r.rows_read) for r in price_was.reads] == [("me_pricing", 1, 1)])
price_none = Night({"me_pricing": PRICING_FILES["me_pricing"]}, {"p1": PRICING_BODY}).go()
check("with no catalog file in the folder the pricing file is NOT marked read, and the night says why",
      price_none is not None and price_none.read_tonight == () and any("catalog" in x for x in price_none.could_not_read))
check("me_pricing is read now and no longer says it is not",
      "me_pricing" not in reading.WHAT_IS_FETCHED_AND_NOT_READ_YET and "me_pricing" in {o.report_id for o in reading.WHAT_NOTES_CAN_BE_READ}
      and reading.why_a_report_has_no_decision() == "")

check("nothing above ended by throwing rather than by answering -- " + str(THREW), not THREW)
EXPECTED = 49 + 7 + 25
check(f"checks went missing -- {ran + 1} ran, {EXPECTED} expected", ran + 1 == EXPECTED)

if failures:
    print(f"\n{len(failures)} FAILED ({ran} checks)")
    sys.exit(1)
print(f"\nall {ran} checks passed")
