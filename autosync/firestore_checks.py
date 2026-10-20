"""Checks for what the nightly job writes into the seller's own database (D114).

**THE ONE THAT MATTERS MOST: the three collection names are read back out of the
page's own file.** `src/shared/definitions/sync.js` is what the screens read
these records by, and the two are joined by nothing but a comment. Read back
here, a rename on either side goes red instead of quietly reading nothing.

**AND THE SECOND: the collection this job may not write is refused by name.** The
`datastore` scope is authorised by IAM, not by `firestore.rules` -- Google's own
documented behaviour -- so this refusal is the only lock there is.

Run: python autosync/firestore_checks.py
"""

import re
import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import board  # noqa: E402
import firestore as tool  # noqa: E402
import runlog  # noqa: E402
from the_other_half import readFromKartaan  # noqa: E402

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


def _refused(work):
    """True when the work was refused by this job's own `Refused`, and by nothing else."""
    try:
        work()
    except tool.Refused:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


def _why(work, *args):
    """The words a refusal came with, so a check can ask what it SAID.

    **A refusal that says the wrong thing is a refusal nobody can act on**, and
    "it threw" alone cannot tell the two apart.
    """
    try:
        work(*args)
    except Exception as wrong:  # noqa: BLE001
        return str(wrong)
    return ""


PROJECT = "seller-project-1"
AT = datetime(2026, 8, 29, 2, 15, 30)

# ------------------------------------- the names, against the page's own file

# **READ OUT OF THE FILE THE SCREENS USE.** Written twice in two languages, and
# the only thing that stops them drifting is this.
# **THE OTHER HALF IS IN THE OTHER REPOSITORY NOW.** See `the_other_half.py`
# for why this refuses rather than skips when it cannot find it.
THE_PAGES_OWN = readFromKartaan("src", "shared", "definitions", "sync.js")

check("the page's own definitions file was found at all", len(THE_PAGES_OWN) > 500)
for named, value in (("SYNC_LOG", tool.LOG), ("SYNC_BOARD", tool.BOARD), ("SYNC_RUNS", tool.RUNS)):
    check(f"{named} is spelt the same on both sides",
          f"export const {named} = '{value}';" in THE_PAGES_OWN)

# **THE ID OF A LOG LINE IS BUILT THE SAME WAY IN BOTH LANGUAGES.** The page never
# writes one, so a difference would not break a screen -- it would break the one
# thing the shape is for: a retried flush landing at the same name twice.
# **THIS USED TO ASSERT THE PAGE CONTAINED ONE PARTICULAR STRING, AND PASSED
# WHILE THE TWO SIDES DISAGREED.** An independent reviewer found it: the page
# built a FIVE-part name and this file a SIX-part one -- the extra part being a
# line's place in the run, without which two different lines matching in all five
# fields land at one name and the second silently replaces the first. The check
# was named for exactly that fault and could not fail for it.
#
# **BOTH SIDES ARE READ AND COMPARED NOW, in pieces, neither typed out here.**
# A part renamed, added, removed or reordered on either side goes red, because
# what is compared is what each side actually builds.
_OURS = re.search(r'named = f"([^"]+)"', Path(__file__).with_name("firestore.py").read_text(encoding="utf-8"))
_THEIRS = re.search(r"id: `([^`]+)`,", THE_PAGES_OWN)
check("both sides say how a log line is named",
      _OURS is not None and _THEIRS is not None)


def _parts(said: str):
    """The names between the `::`s, whatever each language wraps them in."""
    out = []
    for one in said.split("::"):
        one = one.strip().strip("{}$")
        one = one.replace("line.", "").replace("fingerprint(", "").rstrip(")")
        one = one.split(":")[0]
        out.append(one.strip())
    return out


check("a log line's name is built the same way on both sides",
      _parts(_OURS.group(1)) == _parts(_THEIRS.group(1)))
if _parts(_OURS.group(1)) != _parts(_THEIRS.group(1)):
    print(f"      this file builds {_parts(_OURS.group(1))}; "
          f"the page builds {_parts(_THEIRS.group(1))}. "
          "One of them is writing lines the other cannot find, or two lines at one name.")
check("and a board row's name is too", "`${report}::${day}`" in THE_PAGES_OWN)
# The fingerprint itself, pinned to the page's own arithmetic.
check("the fingerprint is the same arithmetic on both sides",
      "held = (held * 31 + text.charCodeAt(at)) >>> 0" in THE_PAGES_OWN)
check("and it is written in the same base", "held.toString(36)" in THE_PAGES_OWN)

# ------------------------------------- what it may write, and what it may not

check("there are exactly fourteen things it may write", len(tool.WHAT_IT_MAY_WRITE) == 14)
check("and they are the three D114 named, how each listing is doing (job 86 part A), the listings a listing file names (job 41), the cross-check (job 19), the returns and ads (A78), where the sales ledger and the returns sheet are (plan jobs 78, 77), the claims, how each Meesho product did in its week (A87, D459) and a month of ads in one record (D463)",
      set(tool.WHAT_IT_MAY_WRITE) == {tool.LOG, tool.BOARD, tool.RUNS, tool.LISTING_VIEWS, tool.LISTINGS_SEEN, tool.CHECK,
                                      tool.RETURNS, tool.ADS_DAYS, tool.ADS_DETAIL, tool.SYNC_LEDGER, tool.RETURNS_SHEET, tool.CLAIMS, tool.PERFORMANCE, tool.ADS_MONTH})

check("the run log can be written",
      answered(lambda: tool.where_a_document_lives(PROJECT, tool.LOG, "r1"))
      == f"projects/{PROJECT}/databases/(default)/documents/sync_log/r1")
check("and so can the day board",
      answered(lambda: tool.where_a_document_lives(PROJECT, tool.BOARD, "x")) is not None)
check("and so can the runs",
      answered(lambda: tool.where_a_document_lives(PROJECT, tool.RUNS, "x")) is not None)

# **THE LOCK.** The scope this job holds could write any of these; this is what
# stops it, and nothing else does.
for forbidden in ("orders", "products", "stock_lots", "businesses", "purchases", "directory"):
    check(f"a seller's own {forbidden} cannot be written by this job",
          answered(lambda f=forbidden: tool.where_a_document_lives(PROJECT, f, "x")) is None and bool(THREW))
    THREW.clear()
check("and the refusal names what it will write instead",
      "sync_log" in (_why(tool.where_a_document_lives, PROJECT, "orders", "x") or ""))
# **AND IT NAMES THE ONE THAT WAS ASKED FOR**, or whoever reads it has a list of
# three right answers and no idea which wrong one was tried.
check("and it names the one that was asked for",
      "orders" in (_why(tool.where_a_document_lives, PROJECT, "orders", "x") or ""))

# ------------------------------------- names that would reach somewhere else

check("a project nobody named is refused",
      answered(lambda: tool.where_a_document_lives("", tool.LOG, "x")) is None and bool(THREW))
THREW.clear()
check("a record with no name is refused",
      answered(lambda: tool.where_a_document_lives(PROJECT, tool.LOG, "")) is None and bool(THREW))
THREW.clear()
# **A SLASH WOULD NAME A DOCUMENT A COLLECTION DEEPER**, somewhere nothing here
# checks, and the reply would look perfectly ordinary.
check("a name carrying a slash is refused",
      answered(lambda: tool.where_a_document_lives(PROJECT, tool.LOG, "a/b")) is None and bool(THREW))
THREW.clear()
check("and so is a name that is only dots",
      answered(lambda: tool.where_a_document_lives(PROJECT, tool.LOG, "..")) is None and bool(THREW))
THREW.clear()
check("and so is a name Firestore keeps for itself",
      answered(lambda: tool.where_a_document_lives(PROJECT, tool.LOG, "__id__")) is None and bool(THREW))
THREW.clear()
# **BOTH ENDS, NOT EITHER.** Firestore keeps `__something__`; a name that merely
# begins with two underscores is perfectly allowed, and refusing it would throw
# away a log line for a reason that is not true.
check("but a name that only begins with two underscores is allowed",
      answered(lambda: tool.where_a_document_lives(PROJECT, tool.LOG, "__id")) is not None)
check("and one that only ends with them is too",
      answered(lambda: tool.where_a_document_lives(PROJECT, tool.LOG, "id__")) is not None)
check("and so is one longer than Firestore will take",
      answered(lambda: tool.where_a_document_lives(PROJECT, tool.LOG, "a" * 1501)) is None and bool(THREW))
THREW.clear()
check("but one right on the limit is taken",
      answered(lambda: tool.where_a_document_lives(PROJECT, tool.LOG, "a" * 1500)) is not None)

# The business record is read, and it is a different function on purpose.
check("the business record has a name of its own",
      answered(lambda: tool.where_the_business_is(PROJECT))
      == f"projects/{PROJECT}/databases/(default)/documents/businesses/business")
check("and the writing function will not build it",
      answered(lambda: tool.where_a_document_lives(PROJECT, "businesses", "business")) is None and bool(THREW))
THREW.clear()

check("it is the one database a Firebase project starts with", tool.DATABASE == "(default)")
check("and Firestore is where Google says it is", tool.API == "https://firestore.googleapis.com/v1")

# ------------------------------------- what a value is

# **BOOLEANS BEFORE WHOLE NUMBERS.** In Python a True IS an int, and asked the
# other way round every `expected` on the board goes in as 1 -- which the page's
# `=== true` would never read as true again.
check("true is written as a boolean, not as one", answered(lambda: tool.a_value(True)) == {"booleanValue": True})
check("false is written as a boolean, not as nought", answered(lambda: tool.a_value(False)) == {"booleanValue": False})
check("a whole number is written as text, the way Firestore takes it",
      answered(lambda: tool.a_value(7)) == {"integerValue": "7"})
check("and a nought is written, not left out", answered(lambda: tool.a_value(0)) == {"integerValue": "0"})
check("a fraction is written as a number", answered(lambda: tool.a_value(1.5)) == {"doubleValue": 1.5})
check("words are written as words", answered(lambda: tool.a_value("hello")) == {"stringValue": "hello"})
check("and empty words are still words", answered(lambda: tool.a_value("")) == {"stringValue": ""})
check("nothing is written as nothing", answered(lambda: tool.a_value(None)) == {"nullValue": None})

# **A MOMENT IS REFUSED RATHER THAN CONVERTED.** Converted here it would be taken
# for Greenwich, and two in the morning his time would read as half past eight the
# evening before -- the five-and-a-half-hour fault, where nobody would look.
check("a moment cannot be written as a value at all",
      answered(lambda: tool.a_value(AT)) is None and bool(THREW))
THREW.clear()
check("and the refusal says to write the text instead",
      "text" in (_why(tool.a_value, AT) or ""))
check("and so is a day", answered(lambda: tool.a_value(date(2026, 8, 29))) is None and bool(THREW))
THREW.clear()
check("something with no shape at all is refused",
      answered(lambda: tool.a_value({"a": 1})) is None and bool(THREW))
THREW.clear()

check("a record becomes named values",
      answered(lambda: tool.fields_of({"a": "x", "b": 2}))
      == {"a": {"stringValue": "x"}, "b": {"integerValue": "2"}})
check("a field with no name is refused",
      answered(lambda: tool.fields_of({"": "x"})) is None and bool(THREW))
THREW.clear()
check("a field name Firestore keeps is refused",
      answered(lambda: tool.fields_of({"__name__": "x"})) is None and bool(THREW))
THREW.clear()
check("but a field that only begins with two underscores is allowed",
      answered(lambda: tool.fields_of({"__name": "x"})) == {"__name": {"stringValue": "x"}})
check("and something that is not a record at all is refused",
      answered(lambda: tool.fields_of(["a"])) is None and bool(THREW))
THREW.clear()

check("named values come back as a plain record",
      answered(lambda: tool.plain({"a": {"stringValue": "x"}, "b": {"integerValue": "2"},
                                   "c": {"booleanValue": True}, "d": {"nullValue": None},
                                   "e": {"doubleValue": 1.5}}))
      == {"a": "x", "b": 2, "c": True, "d": None, "e": 1.5})
check("and nothing at all comes back as an empty record", answered(lambda: tool.plain(None)) == {})

# ------------------------------------- a moment, as text

# **ONE PLACE, so nothing can convert a moment differently in three record
# shapes.** Seconds, matching `runlog.Line.as_row` exactly, so the copy in the
# seller's Drive and the record in their database say the same thing.
check("a moment is text, to the second", answered(lambda: tool.as_text(AT)) == "2026-08-29T02:15:30")
check("and not to the millisecond", "." not in (answered(lambda: tool.as_text(AT)) or "."))
check("a day is text too", answered(lambda: tool.as_text(date(2026, 8, 29))) == "2026-08-29")
# **AND A MOMENT WRITTEN OUT PLAINLY HAS A SPACE WHERE THE PAGE WANTS A T**, which
# is why the moment is asked for by name and the day is not.
check("and a moment written out plainly would have been the wrong shape",
      str(AT) != tool.as_text(AT))
# **A MOMENT THAT IS ALREADY TEXT IS LEFT ALONE.** Reached for and converted, a
# line whose time came from somewhere else would be rewritten into a shape nobody
# asked for -- or thrown away.
check("something already written as text is left exactly as it is",
      answered(lambda: tool.as_text("2026-08-29T02:15:30")) == "2026-08-29T02:15:30")
# Nothing at all is an answer: a run that has not finished says nothing about it.
check("and nothing at all is empty text, which is an answer",
      answered(lambda: tool.as_text(None)) == "")

# ------------------------------------- the fingerprint, against known answers

# **PINNED TO WHAT THE PAGE'S OWN ARITHMETIC GIVES.** The same numbers are checked
# on the JavaScript side, in `src/shared/definitions/sync.test.js`, so the two
# languages are held to one table rather than to each other's word.
FINGERPRINTS = {
    "": "0",
    "a": "2p",
    "hello": "1n1e4y",
    "Amazon would not give the report up": "11aqrx9",
}
for words, expected in FINGERPRINTS.items():
    check(f"the fingerprint of {words[:20]!r} is what the page would give",
          answered(lambda w=words: tool.fingerprint(w)) == expected)
check("two different messages get two different fingerprints",
      tool.fingerprint("one") != tool.fingerprint("two"))
# **UTF-16 UNITS, NOT PYTHON CHARACTERS.** An emoji is two units in JavaScript and
# one character here, so counting characters would disagree on exactly the strings
# a platform's error text is likeliest to contain.
check("something outside the basic range is counted the way JavaScript counts it",
      answered(lambda: tool.fingerprint("\U0001F600")) == "11zz7")

# ------------------------------------- a log line

LINE = runlog.Line(at=AT, run="20260829T021500", report="az_orders", level="done", message="ok")
named, record = answered(lambda: tool.a_log_line(LINE)) or ("", {})
check("a log line whose moment is already text keeps that text",
      (answered(lambda: tool.a_log_line(
          runlog.Line(at="2026-08-29T02:15:30", run="r", report="x", level="done", message="m")))
       or ("", {}))[1].get("at") == "2026-08-29T02:15:30")
check("a log line is named for its run, its moment, its place, its report and its level",
      named == "20260829T021500::2026-08-29T02:15:30::0000::az_orders::done::"
      + tool.fingerprint("ok"))

# **TWO GENUINELY DIFFERENT LINES IN ONE SECOND DO NOT COLLAPSE (cycle 46,
# R2#18).** Same run, same report, same level, same second, same words -- and
# they were landing at ONE name, so the second silently replaced the first. A log
# quietly losing a line is the thing this package exists against.
same_second = [
    runlog.Line(at=AT, run="r", report="az_orders", level="failed", message="Would not.", place=n)
    for n in (1, 2)
]
check("two different lines in the same second get two different names",
      answered(lambda: tool.a_log_line(same_second[0])[0])
      != answered(lambda: tool.a_log_line(same_second[1])[0]))
# **AND THE SAME LINE TWICE STILL LANDS AT ONE NAME**, which is what makes a
# retried flush safe (D93). Its place is stable across a retry: the same lines,
# in the same order, are flushed again.
check("and the very same line twice still lands at one name",
      answered(lambda: tool.a_log_line(same_second[0])[0])
      == answered(lambda: tool.a_log_line(
          runlog.Line(at=AT, run="r", report="az_orders", level="failed",
                      message="Would not.", place=1))[0]))
# **AND THE PLACE IS NOT A FIELD ON THE RECORD.** The name IS the id; a second
# copy of it inside the record is the two-records-of-one-fact fault in miniature.
check("and the place is not written into the record as well",
      "place" not in answered(lambda: tool.a_log_line(same_second[0])[1]))
check("and the moment in it is text, not a timestamp", record.get("at") == "2026-08-29T02:15:30")
check("and it carries the five things the page reads",
      set(record) == {"at", "run", "report", "level", "message"})
# **NO `id` FIELD.** The document's own name IS the id, and a second copy of it
# inside the record is the "two records of one fact" fault in miniature.
check("and it does not carry its own name a second time", "id" not in record)
# The same line twice lands at the same name, which is what makes a retried flush safe.
check("the same line written twice lands at the same name",
      answered(lambda: tool.a_log_line(LINE))[0] == named)
check("a line about nothing in particular is still about the system",
      (answered(lambda: tool.a_log_line(
          runlog.Line(at=AT, run="r", report="system", level="working", message="m"))) or ("", {}))[1]
      .get("report") == "system")
check("a line with no level is refused rather than called working",
      answered(lambda: tool.a_log_line(
          runlog.Line(at=AT, run="r", report="x", level="", message="m"))) is None and bool(THREW))
THREW.clear()
check("a line with no message is refused",
      answered(lambda: tool.a_log_line(
          runlog.Line(at=AT, run="r", report="x", level="done", message=""))) is None and bool(THREW))
THREW.clear()
check("a line belonging to no run is refused",
      answered(lambda: tool.a_log_line(
          runlog.Line(at=AT, run="", report="x", level="done", message="m"))) is None and bool(THREW))
THREW.clear()

# ------------------------------------- a board row

ROW = board.Row(data_date=date(2026, 8, 28), report_id="az_orders", expected=True,
                state=board.MISSING, file_name=None, file_size=None,
                why_not=None, days_late=3, ask_a_person=True)
named, record = answered(lambda: tool.a_board_row(ROW)) or ("", {})
check("a board row is named for its report and its day", named == "az_orders::2026-08-28")
check("and the day in it is text", record.get("dataDate") == "2026-08-28")
check("nothing recorded becomes an empty word, never an invented sentence", record.get("whyNot") == "")
check("and a file nobody has is an empty name", record.get("fileName") == "")
check("and no size is nought", record.get("fileSize") == 0)
check("whether somebody is needed stays a yes or no", record.get("askAPerson") is True)
check("and so does whether it was expected", record.get("expected") is True)
check("a row nobody expected says so", (answered(lambda: tool.a_board_row(
    board.Row(data_date=date(2026, 8, 28), report_id="x", expected=False, state=board.ARRIVED)))
    or ("", {}))[1].get("expected") is False)
check("and it carries the nine things the page reads",
      set(record) == {"dataDate", "reportId", "expected", "state", "fileName",
                      "fileSize", "whyNot", "daysLate", "askAPerson"})
check("a row about no day is refused",
      answered(lambda: tool.a_board_row(
          board.Row(data_date=None, report_id="x", expected=True, state=board.ARRIVED)))
      is None and bool(THREW))
THREW.clear()
check("and a row with nothing to say about the day is refused",
      answered(lambda: tool.a_board_row(
          board.Row(data_date=date(2026, 8, 28), report_id="x", expected=True, state="")))
      is None and bool(THREW))
THREW.clear()

# ------------------------------------- a run

named, record = answered(lambda: tool.a_run("20260829T021500", AT)) or ("", {})
check("a run is named by its own name", named == "20260829T021500")
check("and it says when it started", record.get("startedAt") == "2026-08-29T02:15:30")
check("and it carries the three things the page reads",
      set(record) == {"startedAt", "finishedAt", "why"})
check("and a reason recorded against it is carried",
      (answered(lambda: tool.a_run("r", AT, why="stopped part way")) or ("", {}))[1]
      .get("why") == "stopped part way")
check("and no reason is an empty one, never an invented one",
      record.get("why") == "")
# **BLANK IS HOW A RUN THAT NEVER FINISHED IS TOLD FROM ONE THAT FAILED.** Filled
# in with the moment it was written, every abandoned run would read as a clean one.
check("a run that has not finished says nothing about finishing", record.get("finishedAt") == "")
check("a finished one says when",
      (answered(lambda: tool.a_run("r", AT, finished_at=datetime(2026, 8, 29, 2, 20, 0))) or ("", {}))[1]
      .get("finishedAt") == "2026-08-29T02:20:00")
check("a run with no name is refused",
      answered(lambda: tool.a_run("", AT)) is None and bool(THREW))
THREW.clear()
check("and one that does not say when it started is refused",
      answered(lambda: tool.a_run("r", None)) is None and bool(THREW))
THREW.clear()

# ------------------------------------- the writes themselves

WRITE = answered(lambda: tool.one_write(PROJECT, tool.LOG, "r1", {"a": "x"}))
check("a write names the document and carries its fields",
      WRITE == {"update": {"name": f"projects/{PROJECT}/databases/(default)/documents/sync_log/r1",
                           "fields": {"a": {"stringValue": "x"}}}})
# **NO `updateMask`.** Without one Firestore replaces the whole document, which is
# right here -- with one, a field dropped from a record would stay behind for ever.
check("and it does not name which fields to leave alone", "updateMask" not in WRITE)
# **NO PRECONDITION.** Every name is worked out from the record itself, so writing
# the same thing twice writes the same thing -- which is what makes a retry safe.
check("and it does not refuse to write over what is there", "currentDocument" not in WRITE)

check("Google's own ceiling on one call is what its limits page says",
      tool.A_REQUEST_IS_AT_MOST == 10 * 1024 * 1024)
check("and some of it is left spare", 0 < tool.LEAVE_SPARE < tool.A_REQUEST_IS_AT_MOST)

MANY = [tool.one_write(PROJECT, tool.LOG, f"r{n}", {"a": "x"}) for n in range(50)]
check("writes small enough go in one call", len(list(tool.in_calls(MANY))) == 1)
check("and every one of them goes", sum(len(b) for b in tool.in_calls(MANY)) == 50)
# **PACKED BY MEASURED SIZE.** Google's limits page states a size and no count, so
# a count here would be a number with no document behind it.
SPLIT = list(tool.in_calls(MANY, room=tool.how_big(MANY[:5])))
check("writes too big for one call are split across several", len(SPLIT) > 1)
check("and splitting them loses none", sum(len(b) for b in SPLIT) == 50)
check("and no call is empty", all(b for b in SPLIT))
check("nothing to write is no calls at all", list(tool.in_calls([])) == [])
# **ONE WRITE TOO BIG ON ITS OWN IS STILL SENT**, and fails at Firestore saying so.
# Dropped here it would lose a log line without anything going red.
check("one write bigger than a whole call is still sent, on its own",
      [len(b) for b in tool.in_calls(MANY[:2], room=1)] == [1, 1])
check("how big a call is, is measured rather than guessed", tool.how_big(MANY) > tool.how_big(MANY[:5]))

# ------------------------------------- the hour it reads back

check("the hour the seller chose is read out of the record",
      answered(lambda: tool.the_hour_they_chose({"fields": {"fetchHour": {"stringValue": "23"}}})) == "23")
# **THREE ANSWERS, NOT TWO.** No record and no choice are the same thing to the
# job; a setting that is not an hour is NOT, and the clock refuses it in words.
check("a business that has not chosen answers nothing",
      answered(lambda: tool.the_hour_they_chose({"fields": {}})) is None)
check("no record at all answers nothing",
      answered(lambda: tool.the_hour_they_chose(None)) is None)
check("an empty choice answers an empty choice, not nothing",
      answered(lambda: tool.the_hour_they_chose({"fields": {"fetchHour": {"stringValue": ""}}})) == "")
# **HANDED ON EXACTLY AS WRITTEN.** A setting that silently does nothing is worse
# than one that says it is wrong, so nothing here tidies it into the default.
check("something that is not an hour is handed on as it stands",
      answered(lambda: tool.the_hour_they_chose({"fields": {"fetchHour": {"stringValue": "elevenish"}}}))
      == "elevenish")
check("and an hour stored as a number is still an hour",
      answered(lambda: tool.the_hour_they_chose({"fields": {"fetchHour": {"integerValue": "23"}}})) == "23")
check("the field it reads is the one the page writes", tool.THE_HOUR_FIELD == "fetchHour")
check("and it is read off the business record the rules name",
      (tool.BUSINESSES, tool.THE_BUSINESS) == ("businesses", "business"))


# ------------------------------------- plan job 78: the one record that says where the sales ledger is

named_ledger, held_ledger = tool.a_ledger_record("sheet-9", datetime(2026, 10, 12, 4, 30, 0), 7)
check("the ledger record is one fixed name in a collection called sync_ledger",
      tool.SYNC_LEDGER == "sync_ledger"
      and tool.where_a_document_lives(PROJECT, tool.SYNC_LEDGER, named_ledger)
      == f"projects/{PROJECT}/databases/(default)/documents/sync_ledger/ledger")
check("and it holds exactly the sheet, the moment as text on the run's own clock, and the rows",
      held_ledger == {"sheetId": "sheet-9", "lastWroteAt": "2026-10-12T04:30:00", "rows": 7})
check("written whole: as Firestore fields with no mask, so nothing left over can linger",
      "updateMask" not in tool.one_write(PROJECT, tool.SYNC_LEDGER, named_ledger, held_ledger)
      and tool.one_write(PROJECT, tool.SYNC_LEDGER, named_ledger, held_ledger)["update"]["fields"]["rows"] == {"integerValue": "7"})
check("a record with no sheet is refused", _refused(lambda: tool.a_ledger_record("", datetime(2026, 10, 12), 1)))
check("and so is one with no moment", _refused(lambda: tool.a_ledger_record("s", None, 1)))
check("and a count that is not a whole number of rows (a bool, a fraction, a negative)",
      all(_refused(lambda bad=bad: tool.a_ledger_record("s", datetime(2026, 10, 12), bad)) for bad in (True, 1.5, -1, "3")))
check("and the job still may not write a collection it was not given",
      _refused(lambda: tool.where_a_document_lives(PROJECT, "businesses", "business")))

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

# ------------------------------------- the cross-check for the ERP's Data tab (job 19)
# **THE CONTRACT IS E77's, PINNED HERE BECAUSE THE ERP'S `sync.js` DOES NOT NAME THE COLLECTION ON ITS MAIN BRANCH YET** (it is on `e77-data-tab`).
# The day it lands there, a spelling check against that file belongs beside the three above.
check("the collection is spelt sync_check and is kept sixty days", tool.CHECK == "sync_check" and tool.CHECK_KEPT_DAYS == 60)
check("and it can be written", answered(lambda: tool.where_a_document_lives(PROJECT, tool.CHECK, "x")) is not None)
import manifest as _manifest  # noqa: E402
SEEN = _manifest.Crossing(report_id="az_orders", data_date=date(2026, 8, 28), verdict=_manifest.LANDED_AND_READ,
                          landed_by="the run", rows_in_file=40, rows_read=38)
NAMED, SAID = answered(lambda: tool.a_check_row(SEEN)) or (None, None)
check("a row is named for its report and its day, like the board", NAMED == "az_orders::2026-08-28")
check("and says exactly the four fields the page reads, and no row counts",
      SAID == {"dataDate": "2026-08-28", "reportId": "az_orders", "state": "landed_and_read", "landedBy": "the run"})
for spaced, underscored in (("landed and read", "landed_and_read"), ("landed, not read", "landed_not_read"),
                            ("read, never seen landing", "read_never_seen_landing"), ("missing", "missing")):
    got = answered(lambda v=spaced: tool.a_check_row(_manifest.Crossing("r", date(2026, 8, 28), v)))
    check(f"the manifest's '{spaced}' is written as {underscored}", got is not None and got[1]["state"] == underscored)
check("and every verdict the manifest can give is one the map knows",
      {_manifest.LANDED_AND_READ, _manifest.LANDED_NOT_READ, _manifest.READ_NEVER_SEEN_LANDING, _manifest.NOT_THERE}
      == set(tool.CHECK_STATES))
check("nobody landing it is written as empty, not as a made-up word",
      answered(lambda: tool.a_check_row(_manifest.Crossing("r", date(2026, 8, 28), "missing")))[1]["landedBy"] == "")
check("and the extension is written as 'the extension'",
      answered(lambda: tool.a_check_row(_manifest.Crossing("r", date(2026, 8, 28), "landed, not read", landed_by="the extension")))[1]["landedBy"]
      == "the extension")
check("a verdict nobody knows is refused rather than passed on",
      answered(lambda: tool.a_check_row(_manifest.Crossing("r", date(2026, 8, 28), "fine"))) is None and bool(THREW))
THREW.clear()
check("and so is someone who is not the run or the extension",
      answered(lambda: tool.a_check_row(_manifest.Crossing("r", date(2026, 8, 28), "missing", landed_by="a friend"))) is None and bool(THREW))
THREW.clear()
check("a delete is built by the same lock, and refuses what a write would",
      answered(lambda: tool.one_delete(PROJECT, tool.CHECK, "a::2026-01-01")) == {
          "delete": f"projects/{PROJECT}/databases/(default)/documents/sync_check/a::2026-01-01"}
      and answered(lambda: tool.one_delete(PROJECT, "orders", "x")) is None and bool(THREW))
THREW.clear()

EXPECTED = 142
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
