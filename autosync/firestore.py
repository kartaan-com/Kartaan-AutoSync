"""What the nightly job writes into the seller's own database (D114).

**THE GAP THIS CLOSES.** Kartaan's page and the seller's nightly job had no
shared writable place. The job wrote to the seller's Drive, the page wrote to the
seller's Firestore, and neither could reach the other -- so the run log, the day
board and the seller's own chosen fetch hour all had somewhere to be written and
nowhere to be read. **His decision, 2026-08-29:** *"go with the datastore
scope."*

**NO NEW KEY ANYWHERE, and that is the whole reason it was chosen.** The seller
owns their own Firebase project (D1, D3), so their own Google account already has
the right to write to it. The job asks for `datastore` alongside the `drive.file`
it already asks for, and uses the refresh token it already holds. There is no
service-account key, no eighth credential, nothing new to leak.

**READ FROM GOOGLE'S OWN DOCUMENTATION FIRST (Golden Rule 1), and one thing it
says has to be said out loud rather than left in a link:**

> *"Cloud Firestore assumes requests act on behalf of your application instead of
> an individual user"* -- an OAuth 2.0 access token carrying the `datastore`
> scope is authorised by **IAM, not by Security Rules.**

**SO `firestore.rules` DOES NOT STAND BETWEEN THIS JOB AND THE SELLER'S DATA.**
The seller owns the project, so IAM lets their own token do anything in it. The
only thing keeping this job to the three record types D114 named is the code in
this file -- `where_a_document_lives` refuses any other collection by name. That
is ours, not Google's, and pretending otherwise would be exactly the "a lock that
holds by association" fault this project has already paid for. It is checked, and
it is the first check in the file beside this one.

**THREE TRAPS THAT WOULD EACH HAVE BEEN SILENT:**

1. **A moment written as a timestamp reads five and a half hours wrong.** Every
   time in this package is already the seller's own clock (`clock.his_clock`,
   applied once at the very edge). Written as Firestore's `timestampValue` it
   would be taken for UTC, and the page -- which turns a Firestore timestamp back
   into a UTC string -- would show two in the morning as half past eight the
   evening before. **Every moment goes in as TEXT, exactly the text the Drive
   copy carries.**
2. **`True` is an `int` in Python.** Asked "is this a whole number?" first, every
   `expected` and `askAPerson` on the day board would go in as 1 and 0, and the
   page's `askAPerson === true` would never be true again. **Asked about
   booleans first, always.**
3. **Firestore wants a whole number as a STRING** (`integerValue`), and a
   fraction as a number (`doubleValue`). The two are not interchangeable, and
   sending a JSON number where it wants an int64 is refused with a message about
   the value rather than about the shape.

**UPDATE 2026-10-05 (job 25, route (e)): THE `datastore` SCOPE IS NO LONGER USED.**
The paragraphs above describe the decision of 2026-08-29 as it was made. The
run now writes as the seller through their own Firebase sign-in, so Firestore
applies the seller's Security Rules and the lock below is the second lock, not
the only one. See `transport.FirebaseSeller`.

**NOTHING HERE OPENS A CONNECTION.** The door is `firestore_door.py`, and the
transport is handed to it -- the same split as Drive's and Amazon's, for the same
reason: every rule in this file is checked with no account, no token and no
internet.

**Sources:** [Use the Cloud Firestore REST API](https://firebase.google.com/docs/firestore/use-rest-api) |
[projects.databases.documents.commit](https://cloud.google.com/firestore/docs/reference/rest/v1/projects.databases.documents/commit) |
[Value](https://cloud.google.com/firestore/docs/reference/rest/v1/Value) |
[Usage and limits](https://firebase.google.com/docs/firestore/quotas)
"""

import json
import re
from datetime import date, datetime
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

# Where Firestore is, and which database. Written once so nothing can invent a
# near-miss of either.
API = "https://firestore.googleapis.com/v1"

# **THE EIGHT FIELDS OF A LISTING'S DAY** (the ERP's record, commit 94de631), in `views.FIELDS`'s order.
VIEW_FIELDS = ("views", "clicks", "sales", "revenue", "adViews", "adClicks", "adSpend", "adSales")

# **THE ONE FIRESTORE A FIREBASE PROJECT STARTS WITH.** Firebase creates it under
# this exact name, brackets and all, and every seller's is this one. A project
# with a second, named database is not something Kartaan makes or asks for.
DATABASE = "(default)"

# **THE THREE RECORD TYPES D114 NAMED, AND NOTHING ELSE.** Spelt exactly as
# `src/shared/definitions/sync.js` spells them, which is the file the page reads
# them by -- and a check reads those names back out of that file, so the two
# cannot drift apart in silence.
LOG = "sync_log"
BOARD = "sync_board"
RUNS = "sync_runs"

# **THE WHOLE OF THE NARROWNESS, IN ONE TUPLE.** The scope this job holds can
# write anywhere in the seller's project; this is what stops it. A fourth name
# added here is a decision, made in a diff somebody read.
# **AND FOURTH, FROM JOB 86 PART A: HOW EACH LISTING IS DOING.** The ERP's rules (commit 94de631) let the run write it as the
# owner and nobody else; it is written only by `a_views_write`, with a mask, so one report never undoes another's figures.
LISTING_VIEWS = "listing_views"
# **AND FIFTH, FROM JOB 41: THE LISTINGS THE PLATFORMS' LISTING FILES NAME.** One record per listing, named exactly as the ERP names a listing
# waiting to be let in (`platform::platformId`), holding the listing as the ERP's own reader reads it. **The run writes ONLY this and never
# `needs_review` or `products`**: the seller lets a listing in, and which listings are new is for the ERP to say, against what it already holds.
# Written only by `a_listing_write`. The ERP's rules must let the run write it as the owner -- see the job 41 report for the exact rule.
LISTINGS_SEEN = "listings_seen"
# **AND SIXTH, FROM JOB 19: WHAT LANDED AGAINST WHAT WAS READ, FOR THE ERP's DATA TAB.** The ERP cannot read the run's record from Drive
# (`drive.file` reaches only files its own Google app made), so the run copies the cross-check here and the ERP reads it here. One row per
# report per day, named `<reportId>::<day>` like the board, written whole by the owner; only the last `CHECK_KEPT_DAYS` days are kept.
CHECK = "sync_check"
CHECK_KEPT_DAYS = 60
# **AND SEVENTH, EIGHTH AND NINTH, FROM A78: WHAT THE RETURN AND AD REPORTS SAY.** One record per returned line (`platform_returns`), one per
# platform per day of ad figures (`platform_ads_days`), one per platform per day per kind of ad breakdown (`platform_ads_detail`). Their shapes
# are in `docs/A78-RETURNS-ADS-SHAPES.md`; written only by `a_return_write`, `a_ads_days_write` and `a_ads_detail_write`. The ERP's rules must
# let the run write them as the owner, as for `listing_views`.
RETURNS = "platform_returns"
ADS_DAYS = "platform_ads_days"
ADS_DETAIL = "platform_ads_detail"
# **AND TENTH, FROM PLAN JOB 78: WHERE THE SALES LEDGER IS AND WHEN THE RUN LAST WROTE IT.** ONE record, `sync_ledger/ledger`
# -- a collection of one, addressed the way `businesses/business` is, because the ERP reads it by a fixed name and a run has
# no id of its own to name it by. Written whole, as the owner, only by `a_ledger_record`, and only on a run that really wrote
# sales rows. The ERP's rules must let the run write it as the owner (job 76 reads it).
SYNC_LEDGER = "sync_ledger"
THE_LEDGER_RECORD = "ledger"
# **AND ELEVENTH, FROM ERP JOB 77 / PIECE 34 / D316: WHERE THE RETURNS SHEET IS.** ONE record, `returns_sheet/sheet`, written whole as the owner
# the same way (`a_returns_sheet_record`), and ONLY when the run has just made the sheet or when the record is missing or names another sheet.
# It is never rewritten on a later run, so `createdAt` stays the day the sheet was made. The ERP's rules must let the run write it as the owner.
RETURNS_SHEET = "returns_sheet"
THE_RETURNS_RECORD = "sheet"
# **AND TWELFTH, FROM A87 / D459: WHAT A CLAIM SAYS.** One record per claim (`platform_claims`), named `<platform>__<claim id>` and carrying the id of the
# sub-order it is about, on the same pattern as `platform_returns`. A claim never creates an order row (many are about orders from before the sheet
# began); the ERP reads these. Written only by `a_record_write`. The ERP's rules must let the run write them as the owner.
CLAIMS = "platform_claims"
# **AND THIRTEENTH, FROM A87 / D459: HOW EACH MEESHO PRODUCT DID IN A WEEK.** One record per product per week (`platform_performance`), written only by
# `a_record_write`; the product's catalog id is carried when its title says one, and a title that matches none is kept and flagged. The ERP's
# rules must let the run write them as the owner.
PERFORMANCE = "platform_performance"
# **AND FOURTEENTH, FROM A87 / D463: ONE SUMMARY RECORD PER PLATFORM PER MONTH OF ADS** (`platform_ads_month/<platform>__<yyyy-mm>`), rebuilt whole from that
# month's `platform_ads_days` and `platform_ads_detail` records so the ERP's Ads tab reads a few records instead of hundreds. Written only by
# `a_record_write`. The ERP's rules must let the run write it as the owner; the ERP never writes it.
ADS_MONTH = "platform_ads_month"
# **AND FIFTEENTH, FROM A87 / PLAN PART F: WHAT THE PLATFORM SAYS OF EACH LISTING'S QUALITY** (`platform_quality/<platform>__<SKU>`): the star level, the returns
# share, the badge and the suppression risk as they stand, with a short history of the last readings. Written only by `a_record_write`; the ERP's rules
# must let the run write it as the owner.
QUALITY = "platform_quality"
# **AND SIXTEENTH, FROM A87 / D473: A WHOLE-SHOP FIGURE FOR A DAY** (`platform_shop_days/<platform>__<day>`: Meesho's dashboard views and orders), one record per day,
# written only by `a_record_write`. It belongs to no listing. The ERP's rules must let the run write it as the owner.
SHOP_DAYS = "platform_shop_days"
WHAT_IT_MAY_WRITE = (
    LOG, BOARD, RUNS, LISTING_VIEWS, LISTINGS_SEEN, CHECK, RETURNS, ADS_DAYS, ADS_DETAIL, SYNC_LEDGER, RETURNS_SHEET, CLAIMS, PERFORMANCE, ADS_MONTH,
    QUALITY, SHOP_DAYS,
)

# Where the seller's own business record lives, and the one field this job reads
# out of it. **READ, NEVER WRITTEN (D114):** the hour is the seller's setting,
# written from the This business tab, and a job that could write it would be a
# second author of one fact.
BUSINESSES = "businesses"
THE_BUSINESS = "business"
THE_HOUR_FIELD = "fetchHour"

# **GOOGLE'S OWN CEILING ON ONE CALL, and the only one its limits page states for
# a commit.** It gives no maximum number of writes, so nothing here invents one:
# the writes are packed until the call itself would be too big, and a number with
# no documentation behind it is what this project keeps being caught by.
A_REQUEST_IS_AT_MOST = 10 * 1024 * 1024

# How much of that is left alone. The measured size is the writes; the envelope,
# the headers and anything Google counts that we cannot see are not.
LEAVE_SPARE = 2 * 1024 * 1024

# How much of one call the writes may actually fill. Worked out from the two
# above rather than written a third time.
ROOM = A_REQUEST_IS_AT_MOST - LEAVE_SPARE


class Refused(RuntimeError):
    """This job will not do that.

    **ITS OWN KIND, so a refusal from here is never mistaken for Firestore having
    said no.** One is a defect in this code; the other is a seller's permission
    or connection, and they need entirely different things doing about them.
    """


# --------------------------------------------------------------- where things go


def where_a_document_lives(project: str, collection: str, doc_id: str) -> str:
    """The full name of one document, or a refusal.

    **THIS IS THE LOCK.** The `datastore` scope bypasses `firestore.rules`
    entirely (Google's own documented behaviour, quoted at the top of this file),
    so this function is the only thing that keeps the nightly job to the three
    record types D114 named. Every write and every read of the job's own records
    is built here; there is no second way to name a document.
    """
    if not project:
        raise Refused("There is no project to write to, so nothing has been sent.")
    if collection not in WHAT_IT_MAY_WRITE:
        raise Refused(
            f"The nightly job may only write {', '.join(WHAT_IT_MAY_WRITE)}, and "
            f"{collection!r} is not one of them. Nothing has been sent."
        )
    return _name(project, collection, doc_id)


def where_the_business_is(project: str) -> str:
    """The name of the seller's own business record.

    **SEPARATE FROM `where_a_document_lives` ON PURPOSE.** That one refuses
    everything outside the three the job writes, and this is a READ of a record
    the job must never write -- so it is a different function with a different
    name, rather than a hole punched in the one that refuses.
    """
    if not project:
        raise Refused("There is no project to read from, so nothing has been asked.")
    return _name(project, BUSINESSES, THE_BUSINESS)


def _name(project: str, collection: str, doc_id: str) -> str:
    """The name Firestore uses for a document. Its shape, not ours.

    **A DOCUMENT ID WITH A SLASH IN IT WOULD NAME A DIFFERENT DOCUMENT
    ENTIRELY** -- a collection deeper, in a place nothing here checks -- and the
    reply would look perfectly ordinary. Every id this job builds is made from
    values it controls, and this refuses the day one is not.
    """
    if not doc_id:
        raise Refused("A record cannot be written without a name to write it at.")
    if "/" in doc_id:
        raise Refused(f"{doc_id!r} cannot be the name of a record: it carries a slash.")
    if doc_id in (".", ".."):
        raise Refused(f"A record cannot be called {doc_id!r}.")
    if doc_id.startswith("__") and doc_id.endswith("__"):
        # Firestore keeps that shape for itself and refuses the write.
        raise Refused(f"{doc_id!r} is a name Firestore keeps for its own.")
    if len(doc_id.encode("utf-8")) > 1500:
        raise Refused("That record's name is longer than the 1500 bytes Firestore will take.")
    return f"projects/{project}/databases/{DATABASE}/documents/{collection}/{doc_id}"


# ------------------------------------------------------------- what a value is


def a_value(held) -> Dict:
    """One value, in the shape Firestore's REST API takes.

    **BOOLEANS ARE ASKED ABOUT BEFORE WHOLE NUMBERS**, because in Python a `True`
    IS a whole number -- and every `expected` and `askAPerson` on the day board
    would go in as 1 and 0, which the page's `=== true` would never read as true
    again.
    """
    if held is None:
        return {"nullValue": None}
    if isinstance(held, bool):
        return {"booleanValue": held}
    if isinstance(held, int):
        # **A WHOLE NUMBER GOES AS TEXT.** Firestore's own encoding: `integerValue`
        # is an int64 written as a string, and a JSON number there is refused.
        return {"integerValue": str(held)}
    if isinstance(held, float):
        return {"doubleValue": held}
    if isinstance(held, (datetime, date)):
        # **NEVER REACHED BY ANYTHING THIS JOB WRITES, AND REFUSED RATHER THAN
        # CONVERTED.** A moment converted quietly here is a moment nobody chose
        # the timezone of -- the five-and-a-half-hour fault, in the one place it
        # would never be looked for. Whoever writes a time writes the text.
        raise Refused(
            "A moment has to be written as the text the rest of the package uses, so that "
            "nothing has to guess which clock it belongs to."
        )
    if isinstance(held, str):
        return {"stringValue": held}
    raise Refused(f"There is no way to write a {type(held).__name__} into a record.")


def fields_of(record: Dict) -> Dict:
    """A plain record, as Firestore's `fields`."""
    if not isinstance(record, dict):
        raise Refused("A record has to be a set of named values.")
    out: Dict[str, Dict] = {}
    for name, held in record.items():
        if not name:
            raise Refused("A record cannot have a field with no name.")
        if name.startswith("__") and name.endswith("__"):
            raise Refused(f"{name!r} is a field name Firestore keeps for its own.")
        out[name] = a_value(held)
    return out


def plain(fields: Optional[Dict]) -> Dict:
    """Firestore's `fields`, back as a plain record.

    Only ever used on what this job READS -- the business record -- and it reads
    one field out of it. Anything it does not recognise comes back as it stands
    rather than as a guess.
    """
    out: Dict = {}
    for name, held in (fields or {}).items():
        if not isinstance(held, dict):
            continue
        if "nullValue" in held:
            out[name] = None
        elif "booleanValue" in held:
            out[name] = bool(held["booleanValue"])
        elif "integerValue" in held:
            out[name] = int(held["integerValue"])
        elif "doubleValue" in held:
            out[name] = float(held["doubleValue"])
        elif "stringValue" in held:
            out[name] = str(held["stringValue"])
        else:
            out[name] = held
    return out


# ------------------------------------------------------------- the three shapes


def fingerprint(words: str) -> str:
    """A short, steady fingerprint of some words.

    **THE SAME ONE `src/shared/definitions/sync.js` USES, AND THAT IS THE WHOLE
    POINT** -- a line's name is worked out from the line itself, so the same line
    written twice (which is what a retried flush does) lands at the same name and
    the second write changes nothing (D93).

    **IT COUNTS UTF-16 UNITS, NOT PYTHON CHARACTERS.** JavaScript's
    `charCodeAt` gives one number per UTF-16 unit, so anything outside the basic
    range -- an emoji in a platform's error text -- is two numbers there and one
    here. Encoded first, the two languages agree on every string rather than on
    most of them.

    **IT PROVES NOTHING AND IS NEVER ASKED TO.** It only tells two lines apart.
    """
    held = 0
    text = str(words or "")
    raw = text.encode("utf-16-le")
    for at in range(0, len(raw), 2):
        unit = raw[at] | (raw[at + 1] << 8)
        held = (held * 31 + unit) & 0xFFFFFFFF
    return _base36(held)


def _base36(number: int) -> str:
    """A number the way JavaScript's `toString(36)` writes it. Lower case."""
    if number == 0:
        return "0"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while number:
        number, left = divmod(number, 36)
        out = digits[left] + out
    return out


def as_text(moment) -> str:
    """A moment, or a day, as the text every other layer of this package uses.

    **ONE PLACE, so nothing can convert one of them differently.** Each of the
    three record shapes below writes at least one, and three copies of this line
    is three chances for one of them to grow a timezone the others do not have --
    which is the five-and-a-half-hour fault, on a value nobody would think to
    check.

    **SECONDS, NOT MILLISECONDS**, matching `runlog.Line.as_row` exactly, so the
    copy in the seller's Drive and the record in their database say the same
    thing about the same line.

    Nothing at all is empty text, and that is an answer: a run that has not
    finished says nothing about finishing.

    **A DAY NEEDS NO BRANCH OF ITS OWN AND HAS NOT GOT ONE.** Written out plainly,
    a day is already `2026-08-29`; a moment is `2026-08-29 02:15:30`, **with a
    space where the page wants a T**. So the moment is the one that has to be
    asked for by name, and a second branch for the day would be a line no check
    could ever make go red.
    """
    if isinstance(moment, datetime):
        return moment.isoformat(timespec="seconds")
    return str(moment or "")


def a_log_line(line) -> Tuple[str, Dict]:
    """One line of a run log, named and shaped as the page reads it.

    Five fields, the same five the Drive copy carries, and **the moment as text**.
    """
    moment = as_text(line.at)
    run = str(line.run or "")
    report = str(line.report or "system")
    level = str(line.level or "")
    message = str(line.message or "")
    if not run or not moment or not level or not message:
        # **REFUSED RATHER THAN WRITTEN HALF-EMPTY.** The page refuses a line with
        # no level rather than calling it `working`, and a job that wrote one
        # would be writing a failure that reads as progress.
        raise Refused("That log line is missing something the screen needs, so it has not been written.")
    # **ITS PLACE IN THE RUN IS PART OF ITS NAME (cycle 46, R2#18).** Without it,
    # two genuinely different lines that match in all five fields -- same report,
    # same level, same second, same words -- land at one name and the second
    # silently replaces the first. The place is stable across a retried flush, so
    # the same line still writes once (D93).
    place = int(getattr(line, "place", 0) or 0)
    # Named the same words the page names them -- see the check that holds
    # the two together, which compares each side's own template part by part.
    at = moment
    named = f"{run}::{at}::{place:04d}::{report}::{level}::{fingerprint(message)}"
    return named, {"at": moment, "run": run, "report": report, "level": level, "message": message}


def a_board_row(row) -> Tuple[str, Dict]:
    """One report on one day, named and shaped as the page reads it.

    **ONE REPORT, ONE DAY, ONE NAME** -- so tonight's answer about a day replaces
    last night's rather than sitting beside it. A board with two answers for one
    day is a board nobody can read.

    **NOTHING RECORDED BECOMES AN EMPTY WORD, NEVER A MADE-UP ONE.** `why_not` is
    `None` in Python when nothing is recorded; the page shows text and says
    nothing when there is none. An invented sentence sends whoever reads it
    looking in the wrong place, which is worse than silence.
    """
    day = as_text(row.data_date)
    report = str(row.report_id or "")
    state = str(row.state or "")
    if not day or not report or not state:
        raise Refused("That board row is missing something the screen needs, so it has not been written.")
    return f"{report}::{day}", {
        "dataDate": day,
        "reportId": report,
        # **BOTH OF THESE STAY A YES OR A NO.** `a_value` writes a whole number as
        # a whole number, so anything truthy-but-not-a-boolean arriving here would
        # go in as 1 -- and the page's `=== true` would never read it as true.
        "expected": bool(row.expected),
        "state": state,
        # **NOTHING RECORDED BECOMES EMPTY, NEVER AN INVENTED SENTENCE.** These
        # three are `None` in Python when there is nothing to say, and the page
        # shows text and shows nothing when there is none.
        "fileName": str(row.file_name or ""),
        "fileSize": int(row.file_size or 0),
        "whyNot": str(row.why_not or ""),
        "daysLate": int(row.days_late),
        "askAPerson": bool(row.ask_a_person),
    }


# **THE FOUR WORDS THE ERP'S DATA TAB READS, UNDERSCORED.** `manifest.py` says them with spaces (it is a sentence to a person); the ERP's
# page reads them as words. Spelt here once, keyed by the manifest's own constants so a verdict added there is refused here, not guessed.
CHECK_STATES = {
    "landed and read": "landed_and_read",
    "landed, not read": "landed_not_read",
    "read, never seen landing": "read_never_seen_landing",
    "missing": "missing",
}


def a_check_row(crossing) -> Tuple[str, Dict]:
    """One report on one day, as the two records read together: `{dataDate, reportId, state, landedBy}` and nothing else.

    **NO ROW COUNTS (his ruling: the old Data tab has none).** `landedBy` is `'the run'`, `'the extension'` or empty when nothing landed.
    A verdict this does not know is refused rather than passed on, so the page never gets a word it cannot read.
    """
    day = as_text(crossing.data_date)
    report = str(crossing.report_id or "")
    state = CHECK_STATES.get(str(crossing.verdict or ""))
    if not day or not report or state is None:
        raise Refused("That cross-check row is missing something the screen needs, or says something it cannot read, so it has not been written.")
    landed_by = str(crossing.landed_by or "")
    if landed_by not in ("", "the run", "the extension"):
        raise Refused(f"{landed_by!r} is not someone who lands files, so that cross-check row has not been written.")
    return f"{report}::{day}", {"dataDate": day, "reportId": report, "state": state, "landedBy": landed_by}


def a_run(name: str, started_at, finished_at=None, why: str = "") -> Tuple[str, Dict]:
    """One run: when it started, and when it finished if it did.

    **A RUN THAT NEVER FINISHED IS NOT A RUN THAT FAILED, and blank is how the
    page tells them apart.** Four days in twenty-six the reference's whole sync
    began and never reported finishing, and nothing anywhere could say so. So
    `finishedAt` is left empty rather than filled in with the moment this was
    written -- which would make every abandoned run read as a clean one.
    """
    named = str(name or "")
    started = as_text(started_at)
    if not named or not started:
        raise Refused("A run is written down by name and by when it started, and one was missing.")
    return named, {"startedAt": started, "finishedAt": as_text(finished_at), "why": str(why or "")}


def a_ledger_record(sheet_id: str, wrote_at, rows: int) -> Tuple[str, Dict]:
    """Where the sales ledger is, when this run last wrote it, and how many rows it wrote.

    **A RECORD WITH NO SHEET OR NO MOMENT, OR A COUNT THAT IS NOT A WHOLE NUMBER, IS REFUSED RATHER THAN WRITTEN.** The ERP
    reads these three to say where the seller's sales are and how fresh they are; a blank id or a count of `True` would
    read as an answer. `wrote_at` is written as the text every other record uses (`as_text`), on the run's own clock.
    """
    sheet = str(sheet_id or "").strip()
    moment = as_text(wrote_at)
    if not sheet or not moment:
        raise Refused("The ledger record is written by the sheet's id and the moment it was written, and one was missing.")
    if isinstance(rows, bool) or not isinstance(rows, int) or rows < 0:
        raise Refused(f"{rows!r} is not a number of rows written.")
    return THE_LEDGER_RECORD, {"sheetId": sheet, "lastWroteAt": moment, "rows": rows}


def a_returns_sheet_record(sheet_id: str, created_at) -> Tuple[str, Dict]:
    """Where the returns sheet is and when it was made: `{sheetId, createdAt}`, and nothing else.

    **A RECORD WITH NO SHEET OR NO MOMENT IS REFUSED RATHER THAN WRITTEN**, for the same reason the ledger's is: the ERP reads
    the id as an answer. `created_at` is the text every other record uses (`as_text`), on the run's own clock.
    """
    sheet = str(sheet_id or "").strip()
    moment = as_text(created_at)
    if not sheet or not moment:
        raise Refused("The returns sheet record is written by the sheet's id and the moment it was made, and one was missing.")
    return THE_RETURNS_RECORD, {"sheetId": sheet, "createdAt": moment}


# ------------------------------------------------------------------- the writes


def one_write(project: str, collection: str, doc_id: str, record: Dict) -> Dict:
    """One write, in the shape a commit takes.

    **NO `updateMask`, DELIBERATELY.** Without one, Firestore replaces the whole
    document with what is sent -- which is exactly right here, because every
    record this job writes is written whole. With one, a field dropped from a
    record would quietly stay behind for ever on every day that already has a
    row.

    **AND NO PRECONDITION.** Every name is worked out from the record's own
    content or from the day it is about, so writing the same thing twice writes
    the same thing -- which is what makes a retried flush safe. A precondition
    would turn that harmless repeat into a failed call.
    """
    return {
        "update": {
            "name": where_a_document_lives(project, collection, doc_id),
            "fields": fields_of(record),
        }
    }


def one_delete(project: str, collection: str, doc_id: str) -> Dict:
    """One delete, in the shape a commit takes: the document's full name, built by the same lock as a write.

    **ONLY EVER USED FOR A NAME THAT A QUERY JUST ANSWERED WITH**, so it never deletes a record nobody saw there.
    """
    return {"delete": where_a_document_lives(project, collection, doc_id)}


A_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _a_number(held) -> Dict:
    """A figure for a listing's day: a whole number as one, money as a double. Bools are not figures."""
    if isinstance(held, bool) or not isinstance(held, (int, float)):
        raise Refused(f"{held!r} is not a figure a listing's day can hold.")
    return a_value(held)


def a_views_write(project: str, doc_id: str, platform: str, listing_id: str, days: Dict, drop: Sequence[str], updated_on: str) -> Dict:
    """One listing's record, written WITH A MASK so only what is said changes (job 86 part A).

    **THE MASK IS THE WHOLE POINT, and it is the opposite of `one_write`.** The traffic file says a day's views and the ads file
    says the same day's ad spend; written whole, whichever came second would erase the other. Each figure is its own field path
    (days.`2026-10-04`.views), so a figure in the file replaces that figure and nothing else. **Days named in `drop` are in the
    mask and not in the record, which Firestore documents as deleting them** ("Fields referenced in the mask, but not present in
    the input document, are deleted") -- that is how a record is held to its newest sixty days.

    A day is quoted in backticks because `2026-10-04` is not a simple field name (docs: Document.fields).
    """
    for day in list(days) + list(drop):
        if not A_DAY.match(str(day)):
            raise Refused(f"{day!r} is not a day written year-month-day, so no record was written for it.")
    paths = ["platform", "listingId", "updatedOn"]
    in_days: Dict[str, Dict] = {}
    for day, figures in sorted(days.items()):
        said = {name: _a_number(held) for name, held in figures.items() if name in VIEW_FIELDS}
        if len(said) != len(figures):
            raise Refused(f"{sorted(set(figures) - set(VIEW_FIELDS))} are not fields of a listing's day.")
        if said:
            in_days[day] = {"mapValue": {"fields": said}}
            paths += [f"days.`{day}`.{name}" for name in sorted(said)]
    paths += [f"days.`{day}`" for day in sorted(set(drop) - set(days))]
    fields: Dict[str, Dict] = {
        "platform": a_value(str(platform)), "listingId": a_value(str(listing_id)), "updatedOn": a_value(str(updated_on)),
    }
    if in_days:
        fields["days"] = {"mapValue": {"fields": in_days}}
    return {
        "update": {"name": where_a_document_lives(project, LISTING_VIEWS, doc_id), "fields": fields},
        "updateMask": {"fieldPaths": paths},
    }


# **THE FIELDS OF A LISTING, AND NO OTHERS** (the ERP reader's listing, less the line it sat on). A field outside this list is refused rather
# than written, so a column a platform adds can never reach a seller's database by way of a reader that was not told about it.
LISTING_FIELDS = (
    "platform", "platformId", "sku", "productName", "stock", "mrp", "sellingPrice", "settlement", "buyerLink", "state",
    "stateReason", "platformVariation", "catalogId", "listingId",
)
# The figures among them: a whole number goes as one, money as a double, a figure a platform did not give as null.
LISTING_FIGURES = ("stock", "mrp", "sellingPrice", "settlement")


def a_listing_write(project: str, listing: Dict, report_id: str, changed_on: str) -> Dict:
    """One listing's record, written whole: `{id, listing, report, changedOn}`.

    **THE SHAPE IS THE ERP'S OWN QUEUE RECORD (`reviewRecord`: `{id, listing}`) WITH TWO FIELDS OF THE RUN'S ADDED**, so letting a listing in
    copies `listing` straight across. `changedOn` is the day of the file in which this listing last differed from what was held.
    **THE LISTING IS ONE FIELD, WRITTEN WHOLE**, so a field dropped from a listing must go; the mask below keeps the fields a note put beside it (`a_listing_note_write`).
    """
    if not A_DAY.match(str(changed_on)):
        raise Refused(f"{changed_on!r} is not a day written year-month-day, so no record was written for it.")
    if set(listing) != set(LISTING_FIELDS):
        raise Refused(f"A listing must have exactly the fields {LISTING_FIELDS}; this one has {sorted(listing)}.")
    held: Dict[str, Dict] = {}
    for name in LISTING_FIELDS:
        value = listing[name]
        if name in LISTING_FIGURES:
            held[name] = a_value(None) if value is None else _a_number(value)
        else:
            if not isinstance(value, str):
                raise Refused(f"{name} of a listing must be text, and {value!r} is not.")
            held[name] = a_value(value)
    doc_id = f"{listing['platform']}::{listing['platformId']}"
    return {
        "update": {
            "name": where_a_document_lives(project, LISTINGS_SEEN, doc_id),
            "fields": {
                "id": a_value(doc_id),
                "listing": {"mapValue": {"fields": held}},
                "report": a_value(str(report_id)),
                "changedOn": a_value(str(changed_on)),
            },
        },
        # **A MASK OF ITS OWN FOUR FIELDS (v0.1.21 lane 2):** the record now has fields this write does not own (`a_listing_note_write`), and a write with no
        # mask replaces the whole record, which would erase them every time the listing changed. A field dropped from `listing` still goes: `listing` is one field.
        "updateMask": {"fieldPaths": ["changedOn", "id", "listing", "report"]},
    }


# **WHAT A PLATFORM'S SIDE FILE SAYS ABOUT A LISTING, AND NO MORE** (v0.1.21 lane 2): the fields `a_listing_note_write` may put beside a listing's `listing`.
# `suppressedOn` and `feeAsOf` are the day of the file the words came from, so a file uploaded late cannot undo a newer one.
NOTE_TEXT = ("suppressedReason", "fixHint", "suppressedOn", "feeAsOf")
NOTE_FIELDS = ("suppressed", "referralFee") + NOTE_TEXT
# The day-field that goes with each side report (`firestore_door.a_listing_notes_sink`).
NOTE_DAY_FIELD = {"az_suppressed": "suppressedOn", "az_fee_preview": "feeAsOf"}


def a_listing_note_write(project: str, doc_id: str, notes: Dict) -> Dict:
    """What a side file says about one listing, written WITH A MASK naming only those fields, so the listing beside it is never touched.

    Refuses a field outside `NOTE_FIELDS`, a `suppressed` that is not true or false, a fee that is not a figure, and a note with nothing in it.
    The record must already exist: the caller (`a_listing_notes_sink`) asks first, because a mask-write to a record that is not there makes one
    with a note and no listing, which the ERP's queue would have to guess at.
    """
    if not notes:
        raise Refused("A note with nothing in it was not written.")
    strange = sorted(set(notes) - set(NOTE_FIELDS))
    if strange:
        raise Refused(f"{strange} are not a field a listing's note can hold.")
    fields: Dict[str, Dict] = {}
    for name, held in notes.items():
        if name == "suppressed":
            if not isinstance(held, bool):
                raise Refused(f"suppressed must be true or false, and {held!r} is not.")
            fields[name] = a_value(held)
        elif name == "referralFee":
            fields[name] = _a_number(held)
        else:
            if not isinstance(held, str):
                raise Refused(f"{name} of a listing's note must be text, and {held!r} is not.")
            if name in ("suppressedOn", "feeAsOf") and not A_DAY.match(held):
                raise Refused(f"{held!r} is not a day written year-month-day, so no note was written.")
            fields[name] = a_value(held)
    return {
        "update": {"name": where_a_document_lives(project, LISTINGS_SEEN, doc_id), "fields": fields},
        "updateMask": {"fieldPaths": sorted(fields)},
    }


def listing_day_held(document: Optional[Dict]) -> str:
    """The day (`changedOn`) a record says its listing last differed, or '' when it says none."""
    return plain((document or {}).get("fields") or {}).get("changedOn") or ""


def listing_held(document: Optional[Dict]) -> Optional[Dict]:
    """The listing a record already holds, read from what Firestore answered for it. None when there is no record."""
    inside = (((document or {}).get("fields") or {}).get("listing") or {}).get("mapValue") or {}
    if not inside.get("fields"):
        return None
    return plain(inside["fields"])


def days_held(document: Optional[Dict]) -> Tuple[str, ...]:
    """The days a record already holds, read from what Firestore answered for it. None when there is no record."""
    fields = (document or {}).get("fields") or {}
    inside = ((fields.get("days") or {}).get("mapValue") or {}).get("fields") or {}
    return tuple(sorted(inside))


# ------------------------------------------------- returns and ads (A78)


def a_deep(held) -> Dict:
    """A value that may be a map or a list, in Firestore's shape. Text, whole numbers and money go as `a_value` sends them."""
    if isinstance(held, dict):
        return {"mapValue": {"fields": {str(k): a_deep(v) for k, v in held.items()}}}
    if isinstance(held, (list, tuple)):
        return {"arrayValue": {"values": [a_deep(v) for v in held]}}
    return a_value(held)


def a_return_write(project: str, record: Dict, named_by: Optional[str] = None) -> Dict:
    """One returned line, written whole (nothing else writes this record).

    **THE FIELDS ARE `returns.RETURN_FIELDS` AND NO OTHERS**: a column a platform adds can never reach a seller's database by way of a reader
    that was not told about it. Absent fields are absent from the record, never blank.

    `named_by` is the key the record is stored under when that is not its own `returnKey`: an Amazon return that first arrived with no
    RMA ID and now has one stays ONE record (A81), carrying the RMA ID in `returnKey`.
    """
    import returns  # noqa: PLC0415 - kept beside its one use

    stray = sorted(set(record) - set(returns.RETURN_FIELDS))
    if stray:
        raise Refused(f"{stray} are not fields of a returned line.")
    for day in ("startedOn", "closedOn", "fileDay"):
        if day in record and not A_DAY.match(str(record[day])):
            raise Refused(f"{record[day]!r} is not a day written year-month-day, so no return was written for it.")
    doc_id = f"{record['platform']}__{named_by or record['returnKey']}"
    return {"update": {"name": where_a_document_lives(project, RETURNS, doc_id), "fields": {k: a_deep(v) for k, v in record.items()}}}


def plain_deep(held) -> object:
    """One Firestore value (any shape, maps and lists included) back as plain data. Only ever used on records this job wrote itself."""
    if "mapValue" in held:
        return {name: plain_deep(one) for name, one in ((held["mapValue"].get("fields")) or {}).items()}
    if "arrayValue" in held:
        return [plain_deep(one) for one in ((held["arrayValue"].get("values")) or [])]
    return next(iter(plain({"x": held}).values()))


def a_record_write(project: str, kind, doc_id: str, record: Dict) -> Dict:
    """One record of any kind in `records.RecordKind`, written whole (nothing else writes it).

    **THE KIND SAYS WHICH FIELDS IT MAY HOLD AND WHICH OF THEM ARE DAYS AND MONTHS**; a field outside the list, a day that is not one and a missing day that
    must be there are refused, so nothing a platform adds can reach a seller's database by way of a reader that was not told about it.
    """
    stray = sorted(set(record) - set(kind.fields))
    if stray:
        raise Refused(f"{stray} are not fields of a {kind.what}.")
    for day in kind.required_days + kind.days:
        if (day in record or day in kind.required_days) and not A_DAY.match(str(record.get(day, ""))):
            raise Refused(f"{record.get(day)!r} is not a day written year-month-day, so no {kind.what} was written for it.")
    for month in kind.months:
        if not re.fullmatch(r"\d{4}-\d{2}", str(record.get(month, ""))):
            raise Refused(f"{record.get(month)!r} is not a month written year-month, so no {kind.what} was written for it.")
    return {"update": {"name": where_a_document_lives(project, kind.collection, doc_id), "fields": {k: a_deep(v) for k, v in record.items()}}}


def a_ads_days_write(project: str, platform: str, day: str, campaigns: Dict, digest: str, file_day: str, updated_on: str) -> Dict:
    """One platform's ad figures for one day, written WITH A MASK so only the campaigns change (what the charge file says is another's)."""
    for one in (day, file_day, updated_on):
        if not A_DAY.match(str(one)):
            raise Refused(f"{one!r} is not a day written year-month-day, so no ad figures were written.")
    fields = {
        "platform": a_value(str(platform)), "day": a_value(str(day)), "updatedOn": a_value(str(updated_on)),
        "campaigns": a_deep(campaigns), "campaignsDigest": a_value(str(digest)), "campaignsFileDay": a_value(str(file_day)),
    }
    return {
        "update": {"name": where_a_document_lives(project, ADS_DAYS, f"{platform}__{day}"), "fields": fields},
        "updateMask": {"fieldPaths": sorted(fields)},
    }


def a_ads_detail_write(project: str, doc_id: str, platform: str, content: Dict, file_day: str, updated_on: str) -> Dict:
    """One breakdown of a day's ads, written whole."""
    for one in (content.get("day"), file_day, updated_on):
        if not A_DAY.match(str(one)):
            raise Refused(f"{one!r} is not a day written year-month-day, so no ad breakdown was written.")
    fields = {k: a_deep(v) for k, v in content.items()}
    fields.update({"platform": a_value(str(platform)), "fileDay": a_value(str(file_day)), "updatedOn": a_value(str(updated_on))})
    return {"update": {"name": where_a_document_lives(project, ADS_DETAIL, doc_id), "fields": fields}}


def how_big(writes: Sequence[Dict]) -> int:
    """How large this call would be, in bytes, measured rather than guessed."""
    return len(json.dumps({"writes": list(writes)}, separators=(",", ":")).encode("utf-8"))


def in_calls(writes: Sequence[Dict], room: int = ROOM) -> Iterator[List[Dict]]:
    """The writes, split into calls small enough for Firestore to take.

    **PACKED BY MEASURED SIZE, NOT BY A COUNT.** Google's limits page states a
    maximum request size and no maximum number of writes, so a count here would
    be a number nobody could point at a document for -- and this project has been
    caught by exactly that before.

    **ONE WRITE TOO BIG ON ITS OWN IS ITS OWN CALL, and it fails at Firestore
    saying so.** Silently dropping it would lose a log line, which is the one
    thing this whole package exists to stop.
    """
    batch: List[Dict] = []
    for write in writes or ():
        if batch and how_big(batch + [write]) > room:
            yield batch
            batch = []
        batch.append(write)
    if batch:
        yield batch


# ---------------------------------------------------------- what it reads back


def the_hour_they_chose(document: Optional[Dict]) -> Optional[str]:
    """The hour the seller chose, exactly as they wrote it, or None.

    **THREE ANSWERS, AND THEY ARE NOT THE SAME THING:**

      - `None` -- there is no business record, or it says nothing about an hour.
        The job uses its own default and says so.
      - `""` -- the field is there and empty. Same as never having chosen; the
        page writes an empty string for a business that has not chosen one.
      - anything else -- handed on **exactly as written**, whether or not it is
        an hour. `clock.why_not_now` refuses a setting that is not an hour, in
        words, rather than quietly falling back to the default. A setting that
        silently does nothing is worse than one that says it is wrong.
    """
    if not isinstance(document, dict):
        return None
    said = plain(document.get("fields")).get(THE_HOUR_FIELD)
    if said is None:
        return None
    return str(said)
