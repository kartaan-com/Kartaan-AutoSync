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
from datetime import date, datetime
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

# Where Firestore is, and which database. Written once so nothing can invent a
# near-miss of either.
API = "https://firestore.googleapis.com/v1"

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
WHAT_IT_MAY_WRITE = (LOG, BOARD, RUNS)

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
