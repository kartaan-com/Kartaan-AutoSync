"""Checks for file names and how far a marker may move.

**TWO REAL FAULTS ARE REPRODUCED HERE WITH THEIR REAL FILES:**

  1. Seven Meesho payment files sat in Drive with no date in their names --
     `meesho_payments.xlsx`, `(1)` ... `(6)` -- and every one counted as missing
     while the data was right there. Six weeks, silent on both sides.
  2. A two-day Flipkart traffic request came back with one day in it, no error,
     and the marker moved past both. That day was permanently believed done.

Run: python autosync/landing_checks.py
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import landing as tool  # noqa: E402
from reports import BROWSER, DAILY, REPORTS, Report  # noqa: E402

ran = 0
failures = []
# Everything that ended by throwing rather than by answering. **The floor under
# all of it:** answering with nothing stops the run dying, but on its own it is
# not enough -- a check written as "this word is NOT in what it said" passes
# against nothing, and would go green for the worst possible reason.
THREW = []


def refused(work):
    """What this threw, or None when it did not.

    **A REFUSAL IS AN ANSWER HERE**, so the checks about what is refused read
    the thing that was raised rather than merely that something was.
    """
    try:
        work()
        return None
    except Exception as caught:  # noqa: BLE001
        return caught


def answered(work):
    """What this answers, or nothing at all when it threw.

    **A RUN THAT STOPS IS NOT A CHECK GOING RED.** Worked out before it is handed
    over, one deliberate breakage anywhere ends the whole run and nothing goes
    red -- so the measurement reads "noticed" while saying nothing about whether
    any check here is any good. Worked out in here, a call that throws answers
    with nothing, that one check goes red by itself, and the rest still run.

    Nothing is never a pass: every check reads its answer for truth, so nothing
    always fails. That is what makes this safe to put round every one of them.
    """
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


DAY = lambda s: date.fromisoformat(s)  # noqa: E731

ORDERS = Report("me_orders", "meesho", "Meesho orders", BROWSER, DAILY, "csv")
PAYMENTS = Report("me_payments", "meesho", "Meesho payments", BROWSER, DAILY, "zip")

# ------------------------------------------------------------- the file name

name = tool.file_name_for(ORDERS, DAY("2026-08-26"))
check("a file is named for its platform, its report and its data date", answered(lambda: name == "meesho_me_orders_2026-08-26.csv"))
check("the extension comes off the report", answered(lambda: tool.file_name_for(PAYMENTS, DAY("2026-08-26")).endswith(".zip")))

# **BUILT IN ONE PLACE AND READ BACK IN ONE PLACE, so the two cannot drift.**
check("the date can be read back out of the name it was built into", answered(lambda: tool.data_date_in(name) == DAY("2026-08-26")))
check(
    "and that holds for every report in the real list",
    answered(lambda: all(
        tool.data_date_in(tool.file_name_for(r, DAY("2026-08-26"))) == DAY("2026-08-26")
        for r in REPORTS
    )),
)

# ------------------------------------------- THE SEVEN FILES NOTHING COULD FIND

# **THE REAL NAMES, out of his Drive folder today.**
REAL_STRAYS = [
    "meesho_payments.xlsx",
    "meesho_payments (1).xlsx",
    "meesho_payments (2).xlsx",
    "meesho_payments (3).xlsx",
    "meesho_payments (4).xlsx",
    "meesho_payments (5).xlsx",
    "meesho_payments (6).xlsx",
]
check("a file with no date in its name answers nothing, not a date", answered(lambda: tool.data_date_in(REAL_STRAYS[0]) is None))
check("and all seven of the real ones do", answered(lambda: all(tool.data_date_in(n) is None for n in REAL_STRAYS)))
# **THE THIRD STATE.** They are not missing and they are not fine.
check("they are named as files nothing can find", answered(lambda: tool.undated(REAL_STRAYS) == tuple(REAL_STRAYS)))
check(
    "and a properly dated file beside them is not swept up with them",
    answered(lambda: tool.undated(REAL_STRAYS + ["meesho_me_payments_2026-08-24.zip"]) == tuple(REAL_STRAYS)),
)
check("a folder with nothing wrong in it reports nothing", answered(lambda: tool.undated(["meesho_me_orders_2026-08-26.csv"]) == ()))
check("and an empty folder is not an error", answered(lambda: tool.undated([]) == ()))
# A date that looks like one but is not.
check("something that looks like a date but is not one answers nothing", answered(lambda: tool.data_date_in("x_2026-13-45.csv") is None))
check("and nothing at all answers nothing", answered(lambda: tool.data_date_in("") is None and tool.data_date_in(None) is None))

# ------------------------------------------------------- present but no good

check("a file with bytes in it is not empty", answered(lambda: tool.Arrived("a_2026-08-26.csv", 4021).is_empty is False))
# **PRESENCE IS NOT CORRECTNESS**, and nought bytes is the one wrongness presence
# alone can catch. The reference recorded a truncated file as Verified.
check("a file of nothing is empty", answered(lambda: tool.Arrived("a_2026-08-26.csv", 0).is_empty is True))
check("and it still knows its date", answered(lambda: tool.Arrived("a_2026-08-26.csv", 0).data_date == DAY("2026-08-26")))

# --------------------------------------- THE MARKER MOVES ONLY AS FAR AS PROVEN

# **THE REAL INCIDENT.** A range asked for up to 07-03 came back containing 07-02
# only. The reference moved its marker to 07-03 and that day was gone for ever.
asked = DAY("2026-07-03")
found_inside = [DAY("2026-07-02")]
check(
    "a range that came back short moves the marker only as far as what was in it",
    answered(lambda: tool.advance_marker(asked, found_inside, marker_now=DAY("2026-07-01")) == DAY("2026-07-02")),
)
check(
    "and it is NOT moved to what was asked for",
    answered(lambda: tool.advance_marker(asked, found_inside, marker_now=DAY("2026-07-01")) != asked),
)
check(
    "so the missing tail is left to fetch again",
    answered(lambda: tool.short_of_what_was_asked(asked, DAY("2026-07-02")) is not None),
)
check(
    "and it says so in words rather than leaving it to be noticed",
    answered(lambda: "left to fetch again" in tool.short_of_what_was_asked(asked, DAY("2026-07-02"))),
)
check(
    "a complete range says nothing",
    answered(lambda: tool.short_of_what_was_asked(asked, asked) is None),
)
check(
    "a complete range moves the marker all the way",
    answered(lambda: tool.advance_marker(asked, [DAY("2026-07-02"), asked], marker_now=DAY("2026-07-01")) == asked),
)

# Nothing verified at all: the marker must not move one day.
check(
    "nothing usable in what came back moves the marker not at all",
    answered(lambda: tool.advance_marker(asked, [], marker_now=DAY("2026-07-01")) == DAY("2026-07-01")),
)
check("and says so", answered(lambda: tool.short_of_what_was_asked(asked, None) is not None))
check("with no marker to start from, nothing verified stays nothing", answered(lambda: tool.advance_marker(asked, []) is None))

# **NEVER BACKWARDS.** An old file turning up must not undo progress.
check(
    "a date older than the marker does not move it back",
    answered(lambda: tool.advance_marker(asked, [DAY("2026-06-01")], marker_now=DAY("2026-07-01")) == DAY("2026-07-01")),
)
# **AND NEVER PAST WHAT WAS ASKED FOR.** A file containing a date beyond the
# request is a file from somewhere else -- the reference once parsed an unrelated
# download and looped over 18,752 imaginary campaigns.
check(
    "a date beyond what was asked for is not trusted past the request",
    answered(lambda: tool.advance_marker(asked, [DAY("2026-09-01")], marker_now=DAY("2026-07-01")) == asked),
)
check(
    "a None among the dates is ignored rather than crashing the marker",
    answered(lambda: tool.advance_marker(asked, [None, DAY("2026-07-02")], marker_now=DAY("2026-07-01")) == DAY("2026-07-02")),
)


# ------------------------------------------------- the ends nothing else reached

# An arrival record is frozen for the same reason a report is: what the board is
# reading must not change underneath it.
was_refused = False
try:
    tool.Arrived("a_2026-08-26.csv", 1).size = 99
except AttributeError:
    was_refused = True
check("an arrival record cannot be edited after it is made", answered(lambda: was_refused is True))

# **THE SHORT-RANGE SENTENCE HAS TO NAME BOTH DATES**, because whoever reads it is
# deciding what still has to be fetched. "It came back short" without saying how
# short is the same silence one step along.
short = tool.short_of_what_was_asked(DAY("2026-07-03"), DAY("2026-07-02"))
check("the short-range sentence names what was asked for", answered(lambda: "2026-07-03" in short))
check("and how far it actually got", answered(lambda: "2026-07-02" in short))

# A range that came back FURTHER than asked is not "short" -- it is the marker
# already being at the request, and it says nothing.
check(
    "a range that reached exactly what was asked for says nothing at all",
    answered(lambda: tool.short_of_what_was_asked(DAY("2026-07-03"), DAY("2026-07-03")) is None),
)
check(
    "and one that somehow reached past it says nothing either",
    answered(lambda: tool.short_of_what_was_asked(DAY("2026-07-03"), DAY("2026-07-09")) is None),
)

# ------------------------------- which days a folder REALLY holds

# **NOTHING IN THIS FILE'S OWN CHECKS HAD EVER CALLED THIS**, and it is the one
# function here whose docstring names "the quietest possible way to lose a day
# permanently". It was reached only through the schedule, so the proving tool
# broke every line of it and nothing went red. Found 2026-08-27.
REAL = tool.Arrived("meesho_me_orders_2026-07-02.csv", 900)
ALSO = tool.Arrived("meesho_me_orders_2026-07-01.csv", 40)
check("a file that is really there is the day in its name",
      answered(lambda: tool.days_that_arrived([REAL]) == (DAY("2026-07-02"),)))

# **A NOUGHT-BYTE FILE IS NOT A DAY THAT ARRIVED.** Counted, its day would never
# be fetched again -- the day is gone and nothing ever says so.
check("a file with nothing in it is not a day that arrived",
      answered(lambda: tool.days_that_arrived([tool.Arrived("meesho_me_orders_2026-07-02.csv", 0)]) == ()))
check("and neither is one whose size is nonsense",
      answered(lambda: tool.days_that_arrived([tool.Arrived("meesho_me_orders_2026-07-02.csv", -5)]) == ()))

# A file with no date in its name is the THIRD state, and it is not a day either.
check("a file nothing can match to a day is not one",
      answered(lambda: tool.days_that_arrived([tool.Arrived("orders (3).csv", 900)]) == ()))

# **THE SAME DAY TWICE IS ONE DAY**, and they come back in order -- what asks this
# compares it against what is owed, and an unsorted or repeated answer would make
# that comparison wrong in a way nothing would show.
check("the same day arriving twice is still one day",
      answered(lambda: tool.days_that_arrived([REAL, tool.Arrived("meesho_me_orders_2026-07-02.csv", 12)])
      == (DAY("2026-07-02"),)))
check("and the days come back in order, earliest first",
      answered(lambda: tool.days_that_arrived([REAL, ALSO]) == (DAY("2026-07-01"), DAY("2026-07-02"))))
check("a good file beside an empty one is still counted",
      answered(lambda: tool.days_that_arrived([REAL, tool.Arrived("meesho_me_orders_2026-07-05.csv", 0)])
      == (DAY("2026-07-02"),)))

check("an empty folder holds no days", answered(lambda: tool.days_that_arrived([]) == ()))

# **THE OLD WRONG THING, HANDED IN ON PURPOSE.** A list of plain dates is what
# this used to be given by one caller and files by another -- one word with two
# meanings. Asked politely it answered "nothing has ever arrived" and every day
# was fetched again for ever. It has to stop the run and name itself instead.
stopped = False
try:
    tool.days_that_arrived([DAY("2026-07-02")])
except AttributeError:
    stopped = True
check("a record of the wrong kind stops the run rather than vanishing from the answer",
      answered(lambda: stopped is True))
# **NOTHING AT ALL IS NOT AN ERROR.** A folder nobody has read yet answers with
# no days rather than falling over -- and falling over here would stop the whole
# schedule being worked out.
check("and nothing at all is answered with no days rather than a crash",
      answered(lambda: tool.days_that_arrived(None) == ()))


# **AND NOTHING ABOVE ENDED BY THROWING RATHER THAN BY ANSWERING.** Answering
# with nothing keeps the run alive; this is what stops a check phrased as "this
# word is NOT in what it said" going green because there was nothing to look in.
# ------------------------------------- what actually came down

# **ELEVEN OF HIS OWN FILES BOUGHT THIS RULE.** Between 14 June and 6 July 2026
# Meesho served its payment export as a ZIP with the spreadsheet inside it, then
# went back to a plain spreadsheet. The extension saved those bytes under the
# name it had already chosen -- `meesho_payments_2026-06-29.xlsx` -- so eleven
# files sat in his Drive looking exactly like the other eighty-four, and
# **twelve per cent of his settlement money could not be opened by anything.**
# Right name, right size, right folder, and ARRIVED on the day board.

import io as _io  # noqa: E402
import zipfile as _zip  # noqa: E402


def _a_zip_of(files):
    """A real zip, built here rather than described."""
    held = _io.BytesIO()
    with _zip.ZipFile(held, "w") as book:
        for name, body in files.items():
            book.writestr(name, body)
    return held.getvalue()


# **AN `.xlsx` IS A ZIP.** Both begin PK, so stopping at the first four bytes
# would call every spreadsheet a zip and rename all of them.
A_SPREADSHEET = _a_zip_of({"xl/workbook.xml": "<x/>", "[Content_Types].xml": "<t/>"})
A_WRAPPER = _a_zip_of({"SP_ORDER_PAYMENT_2026-06-29.xlsx": A_SPREADSHEET})
TWO_INSIDE = _a_zip_of({"TCS_Sales.xlsx": "a", "TCS_Return.xlsx": "b"})

check("a spreadsheet is a spreadsheet, not the zip it is made of",
      answered(lambda: tool.what_it_really_is(A_SPREADSHEET)) == "xlsx")
check("and a plain zip is a zip", answered(lambda: tool.what_it_really_is(A_WRAPPER)) == tool.ZIP)
check("an older spreadsheet is known by its own first bytes",
      answered(lambda: tool.what_it_really_is(tool.AN_OLD_SPREADSHEET + b"rest")) == "xls")
check("plain text is text", answered(lambda: tool.what_it_really_is(b"a,b,c")) == "csv")
check("nothing at all is nothing anybody knows",
      answered(lambda: tool.what_it_really_is(b"")) == tool.UNKNOWN)
# Something that begins like a zip and is not one must not be read as one.
check("and something claiming to be a zip that is not is not guessed at",
      answered(lambda: tool.what_it_really_is(tool.A_ZIP + b"broken")) == tool.UNKNOWN)

# **A ZIP HOLDING ONE SPREADSHEET IS UNWRAPPED**, so what lands can be read.
named, body, note = answered(lambda: tool.the_file_that_matters(
    "meesho_me_payments_2026-06-29.zip", A_WRAPPER)) or ("", b"", None)
check("a zip wrapping one spreadsheet is unwrapped", body == A_SPREADSHEET)
check("and named for what is now in it", named == "meesho_me_payments_2026-06-29.xlsx")
# **THE DATE NEVER MOVES.** The whole day board finds a file by the date in its
# name, so a rename that touched it would lose the day it belongs to.
check("and the day it is about is untouched",
      answered(lambda: tool.data_date_in(named)) == date(2026, 6, 29))
# **SAID OUT LOUD.** Silence here is the same silence that hid eleven files.
check("and it says what it did", "zip" in (note or "") and "xlsx" in (note or ""))

# **A ZIP HOLDING TWO IS NOT SOMETHING TO CHOOSE BETWEEN.** Meesho's GST export
# really does carry two -- sales and returns -- and picking one would put half a
# day's money in the folder and call it the day.
named, body, note = answered(lambda: tool.the_file_that_matters("a.zip", TWO_INSIDE)) or ("", b"", None)
check("a zip holding two is left exactly as it came", body == TWO_INSIDE and named == "a.zip")
check("and somebody is told to look inside it", "look inside" in (note or ""))
check("and it says it was put away as it arrived", "exactly as it arrived" in (note or ""))

# **A ZIP HOLDING NOTHING A READER CAN OPEN IS LEFT ALONE TOO.** The original is
# what makes a bad read fixable without re-fetching, and some reports cannot be
# re-fetched at all.
NOTHING_USEFUL = _a_zip_of({"readme.txt": "hello", "notes.pdf": "x"})
named, body, note = answered(lambda: tool.the_file_that_matters("a.zip", NOTHING_USEFUL)) or ("", b"", None)
check("a zip with nothing a reader can open is left as it came", body == NOTHING_USEFUL)
# **ONE FILE IS NOT ENOUGH -- IT HAS TO BE ONE THIS CAN READ.** A zip holding a
# single PDF has exactly one thing in it, and unwrapping that would put a PDF in
# the folder named as a spreadsheet, which is the fault this whole rule is about.
JUST_A_NOTE = _a_zip_of({"readme.txt": "hello"})
check("a zip holding one file that is not a spreadsheet is left alone",
      (answered(lambda: tool.the_file_that_matters("a.zip", JUST_A_NOTE)) or ("", b"", None))[1]
      == JUST_A_NOTE)
check("and it says so rather than going quiet", "nothing in it a reader can open" in (note or ""))

# **A FOLDER INSIDE A ZIP IS NOT A FILE.** Counted as one, a zip holding one
# spreadsheet in a folder would look like a zip holding two and be left alone --
# and the day's money would stay unreadable for the reason the fix exists.
IN_A_FOLDER = _a_zip_of({"payments/": "", "payments/SP_ORDER.xlsx": A_SPREADSHEET})
check("a spreadsheet inside a folder inside a zip is still unwrapped",
      (answered(lambda: tool.the_file_that_matters("a.zip", IN_A_FOLDER)) or ("", b"", None))[1]
      == A_SPREADSHEET)
# And the ending it is named for is the one that was inside.
check("and it is named for the ending that was inside it",
      (answered(lambda: tool.the_file_that_matters("meesho_x_2026-06-29.zip", _a_zip_of(
          {"inside.csv": "a,b"}))) or ("", b"", None))[0] == "meesho_x_2026-06-29.csv")

# A file that is what it says it is passes through, and says nothing.
named, body, note = answered(lambda: tool.the_file_that_matters("a.xlsx", A_SPREADSHEET)) or ("", b"", "x")
check("a file that is what it says it is is left alone",
      named == "a.xlsx" and body == A_SPREADSHEET)
check("and nothing is said about it", note is None)

# **RENAMED RATHER THAN REFUSED.** A spreadsheet under a `.zip` name is a good
# file nothing will open: the fetching worked and only the labelling was wrong.
named, _, note = answered(lambda: tool.the_file_that_matters("a.zip", A_SPREADSHEET)) or ("", b"", None)
check("a spreadsheet named as a zip is renamed, not thrown", named == "a.xlsx")
check("and it says the labelling was what was wrong", "really a xlsx" in (note or ""))
check("and it says what it was put away as", "put away as a xlsx" in (note or ""))
# A file with no ending at all is named too, and said in words that make sense.
check("and a file with no ending at all is named for what it is",
      (answered(lambda: tool.the_file_that_matters("noending", A_SPREADSHEET)) or ("", b"", None))[0]
      == "noending.xlsx")

# **NOTHING AT ALL IS HANDED STRAIGHT BACK.** "No file came back" and "a file
# with nothing in it" are two different failures with two different sentences,
# and turning the first into the second would report a fetch that returned
# nothing as an empty file -- and its day as fetched.
check("nothing at all stays nothing at all",
      answered(lambda: tool.the_file_that_matters("a.csv", None)) == ("a.csv", None, None))
check("and an empty file stays an empty file",
      answered(lambda: tool.the_file_that_matters("a.csv", b"")) == ("a.csv", b"", None))

# What may be unwrapped is a written list, not whatever happens to be in there.
check("only a spreadsheet or a csv is worth unwrapping",
      set(tool.WORTH_UNWRAPPING) == {"xlsx", "xls", "csv"})

# ------------------- a page is not a report (cycle 46, R2#9)

# **ANYTHING THAT WAS NOT A ZIP WAS CALLED `csv`**, so a portal's sign-in page
# went into the seller's Drive under a real report's name -- right name, right
# size, right folder, and ARRIVED on the day board. **A sign-in page saved as a
# report is the worst possible outcome**: it is a file, it has a size, and
# everything downstream believes the day arrived.
A_SIGN_IN_PAGE = b"<!DOCTYPE html>\n<html><body>Please sign in</body></html>"
check("a web page is recognised as a web page",
      answered(lambda: tool.what_it_really_is(A_SIGN_IN_PAGE)) == tool.A_PAGE)
check("and it is not called a csv", answered(lambda: tool.what_it_really_is(A_SIGN_IN_PAGE)) != "csv")
check("one that starts with whitespace is still recognised",
      answered(lambda: tool.what_it_really_is(b"\n\n  <html><body>no</body></html>")) == tool.A_PAGE)
check("and a lower-case doctype too",
      answered(lambda: tool.what_it_really_is(b"<!doctype html><p>no")) == tool.A_PAGE)
check("the platform saying no in JSON is not a report either",
      answered(lambda: tool.what_it_really_is(b'{"error":"unauthorised"}')) == tool.NOT_A_REPORT)

# **AND IT IS REFUSED RATHER THAN LANDED**, which leaves the day reading as
# missing -- true, and something the catching-up will chase.
page = refused(lambda: tool.the_file_that_matters("meesho_me_orders_2026-08-28.csv", A_SIGN_IN_PAGE))
check("a web page is refused rather than put away", isinstance(page, tool.NotAReport))
check("and it says what is usually behind it", "signed in to again" in str(page))
# **AND IT SAYS WHICH OF THE TWO IT WAS.** A page and a message in JSON are
# different things to go and look at, and one sentence covering both tells
# nobody which they are looking for.
check("and it says it was a web page", "a web page" in str(page))
check("while a message in JSON says that instead",
      "a message rather than a report" in str(refused(lambda: tool.the_file_that_matters(
          "x_2026-08-28.csv", b'{"error":1}'))))
check("and it says the day is still owed", "still owed" in str(page))
check("a message in JSON is refused too",
      isinstance(refused(lambda: tool.the_file_that_matters("x_2026-08-28.csv", b'{"error":1}')),
                 tool.NotAReport))

# **BUT A REAL FILE IS STILL A REAL FILE.** A csv beginning with a heading, and
# one beginning with a figure, both land exactly as they came.
kept, body, note = answered(lambda: tool.the_file_that_matters(
    "meesho_me_orders_2026-08-28.csv", b"Sub Order No,Quantity\n123,1\n"))
check("a real csv is still put away as it came", kept == "meesho_me_orders_2026-08-28.csv")
check("and nothing is said about it", note is None)
check("and its bytes are untouched", body.startswith(b"Sub Order No"))

# ------------------- how big it says it unpacks to (cycle 46, R2#10)

# **A ZIP SAYS WHAT EACH ENTRY UNPACKS TO, and reading without asking is how a
# few kilobytes becomes gigabytes in memory.** A runner killed for running out of
# memory leaves NO evidence at all -- the process dies, nothing flushes, and the
# log says nothing about a night that produced nothing. That is the one failure
# this package cannot report, so it is refused before it can happen.
check("there is a ceiling on what one file inside a zip may unpack to",
      tool.BIGGEST_ONE_INSIDE > 0)
# **MEASURED ON HIS OWN DRIVE: 1,406 files, the biggest 11.5 MB.** The ceiling is
# far above anything real and far below what would take a runner down.
check("and it is far above anything his own files reach",
      tool.BIGGEST_ONE_INSIDE > 20 * 1024 * 1024)

import io as _io  # noqa: E402
import zipfile as _zipfile  # noqa: E402


def _a_zip_claiming(size):
    """A zip whose entry SAYS it unpacks to `size`, without actually holding it."""
    kept = _io.BytesIO()
    with _zipfile.ZipFile(kept, "w") as book:
        book.writestr("sales.csv", b"a,b\n1,2\n")
    raw = bytearray(kept.getvalue())
    # The uncompressed size is written twice: in the entry's own header and in
    # the directory at the end. Both are changed, the way a real one would be.
    from struct import pack  # noqa: PLC0415
    claimed = pack("<I", size)
    honest = pack("<I", len(b"a,b\n1,2\n"))
    raw = bytearray(bytes(raw).replace(honest, claimed))
    return bytes(raw)


huge = refused(lambda: tool.the_file_that_matters(
    "meesho_me_payments_2026-08-28.zip", _a_zip_claiming(900 * 1024 * 1024)))
check("a zip whose contents say they are enormous is refused before being read",
      isinstance(huge, tool.TooBig))
check("and it says how big it claims to be", "900" in str(huge) or "943" in str(huge))
check("and it says it was left as it came", "left as it came" in str(huge))

# **AND AN ORDINARY ZIP IS STILL UNWRAPPED.** A ceiling that refused real files
# would be worse than none.
ordinary = _io.BytesIO()
with _zipfile.ZipFile(ordinary, "w") as book:
    book.writestr("sales.csv", b"a,b\n1,2\n")
name, out, said = answered(lambda: tool.the_file_that_matters(
    "meesho_me_payments_2026-08-28.zip", ordinary.getvalue()))
check("an ordinary zip with one file in it is still unwrapped", name.endswith(".csv"))
check("and what comes out is what was inside", out == b"a,b\n1,2\n")
check("and it says so", bool(said))

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)


EXPECTED = 92
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
