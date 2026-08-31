"""Where a file lands, what it is called, and how far a marker may move.

Shape 4 of the contract (D100).

**THE FILE LANDS IN THE SELLER'S OWN DRIVE, UNTOUCHED, BEFORE ANYTHING READS IT.**
Keeping the original is what makes a bad read fixable without re-fetching -- and
some reports cannot be re-fetched at all, so a lost original is lost for good.
Nothing of the seller's is ever kept on Jaiswal's storage, at any point.

**THE NAME CARRIES THE DATA DATE, and that is not cosmetic.** The day board finds
a file by looking for its data date in the name. In the reference, seven Meesho
payment files were written with no date in the name at all --
`meesho_payments.xlsx`, `(1)`, `(2)` ... `(6)` -- so **all seven counted as
missing while the data sat in the folder**, invisible from both ends. A name is
built here, in one place, and `data_date_in` reads it back, so the two can never
drift apart.

**AND A MARKER ADVANCES ONLY AS FAR AS WHAT VERIFIABLY ARRIVED.** A two-day
Flipkart traffic request once came back with one day in it -- no error, no warning
-- and the code moved its marker past both. That missing day was permanently
believed done. **Never advance to what was asked for; advance to what was found
inside what came back.**
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Optional, Sequence, Tuple

from reports import Report

# `<platform>_<report-without-its-platform-prefix>_<data date>.<extension>`
# The date is always ISO and always present. Read back by DATE_IN_NAME below.
DATE_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")


def file_name_for(a_report: Report, data_date: date) -> str:
    """What one day's file of this report is called.

    **ONE PLACE BUILDS IT AND ONE PLACE READS IT BACK.** Two spellings of a naming
    convention is two records of one fact, and the day board's entire idea of
    whether something arrived rests on these agreeing.
    """
    return f"{a_report.platform}_{a_report.id}_{data_date.isoformat()}.{a_report.extension}"


def data_date_in(file_name: str) -> Optional[date]:
    """The data date inside a file name, or None if it has none.

    **None IS A REAL ANSWER AND IT IS A PROBLEM, not a nought.** A file with no
    date in its name is a file nothing downstream can ever find. It is reported as
    itself -- see `undated` below -- rather than silently counted as missing,
    which is what happened to seven real files for six weeks.
    """
    found = DATE_IN_NAME.search(file_name or "")
    if not found:
        return None
    try:
        return date.fromisoformat(found.group(1))
    except ValueError:
        return None


def undated(file_names: Iterable[str]) -> Tuple[str, ...]:
    """Files sitting in a folder that nothing will ever match to a day.

    They are not missing and they are not fine. They are the third thing, and it
    needs saying out loud: the data is there and no reader can reach it.
    """
    return tuple(n for n in (file_names or ()) if data_date_in(n) is None)


@dataclass(frozen=True)
class Arrived:
    """A file that is really in the seller's folder.

    `size` is here because **presence is not correctness, and a nought-byte file
    is the one kind of wrongness presence alone can catch.** The reference's
    manifest checked only that a name existed, and recorded a truncated catalogue
    file as Verified.
    """

    name: str
    size: int

    @property
    def data_date(self) -> Optional[date]:
        return data_date_in(self.name)

    @property
    def is_empty(self) -> bool:
        return self.size <= 0


def days_that_arrived(records: Iterable["Arrived"]) -> Tuple[date, ...]:
    """Which days a folder actually holds, read from the files themselves.

    **ONE PLACE TURNS FILES INTO DAYS, and everything that asks "what is still
    owed" asks this.** It was two: the day board read the records and the schedule
    read a list of dates, both under an argument called `arrivals`. One contract
    with two meanings, so whichever caller got the other one silently believed
    NOTHING had ever arrived -- and re-fetched every day, for ever.

    **AN EMPTY FILE IS NOT A DAY THAT ARRIVED.** A nought-byte file that counted
    would stop its day ever being fetched again, which is the quietest possible
    way to lose a day permanently. The board already refused to call one arrived;
    now the schedule refuses too, from the same line.

    A file with no date in its name is not a day either -- it is the third state,
    and `undated` is what names it.

    **AND IT IS NOT WRITTEN DEFENSIVELY, deliberately.** It used to ask each
    record for its date politely -- `getattr(one, "data_date", None)` -- which
    meant a record of the WRONG KIND simply vanished from the answer. Hand it the
    old wrong thing, a plain list of dates, and it would say **no day has ever
    arrived** and every day would be fetched again for ever: the exact failure
    this function was written to end, made silent by the very line meant to be
    careful. Asked plainly, a wrong record stops the run and names itself.
    """
    out = set()
    for one in records or ():
        when = one.data_date
        if when is None or one.is_empty:
            continue
        out.add(when)
    return tuple(sorted(out))


def advance_marker(
    asked_for_up_to: date,
    verified_dates: Iterable[date],
    marker_now: Optional[date] = None,
) -> Optional[date]:
    """How far the marker may move, given what was actually found in the file.

    **THE RULE THIS PACKAGE IS MOST BUILT AROUND.** Never to `asked_for_up_to`;
    only to the latest date genuinely present in what came back, and never
    backwards.

    Nothing verified means the marker does not move at all -- which leaves the
    whole range to be tried again, and that is the correct outcome. The
    alternative, which the reference did, is to believe a day was captured
    because it was requested.
    """
    verified = [d for d in (verified_dates or ()) if d is not None]
    if not verified:
        return marker_now
    furthest = max(verified)
    # **NEVER PAST WHAT WAS ASKED FOR EITHER.** A file containing a date beyond
    # the request is a file from somewhere else -- the reference once parsed an
    # unrelated download as a campaign list and looped over 18,752 imaginary
    # campaigns. A surprise in this direction is a reason to distrust, not to leap.
    if furthest > asked_for_up_to:
        furthest = asked_for_up_to
    if marker_now is not None and furthest <= marker_now:
        return marker_now
    return furthest


def short_of_what_was_asked(asked_for_up_to: date, moved_to: Optional[date]) -> Optional[str]:
    """A sentence saying the range came back short, or None if it did not.

    **SAID OUT LOUD RATHER THAN LEFT FOR THE NEXT RUN TO NOTICE.** The whole
    reason the marker rule exists is that a short range looked exactly like a
    complete one; a rule that silently leaves a tail to retry, and never mentions
    it, has only moved the silence one step along.
    """
    if moved_to is None:
        return f"Nothing usable came back for anything up to {asked_for_up_to}, so nothing has been marked done."
    if moved_to < asked_for_up_to:
        return (
            f"The range up to {asked_for_up_to} came back only as far as {moved_to}. "
            "The rest has been left to fetch again rather than marked done."
        )
    return None


# ------------------------------------------- what actually came down

# **A FILE IS NAMED FOR WHAT IT IS, NEVER FOR WHAT WAS EXPECTED, and that rule
# was bought with eleven of his own files.** Between 14 June and 6 July 2026
# Meesho served its payment export as a ZIP with the spreadsheet inside it, then
# went back to a plain spreadsheet. The extension saved whatever bytes came down
# under the name it had already chosen -- `meesho_payments_2026-06-29.xlsx` --
# so eleven files sat in his Drive looking exactly like the other eighty-four,
# and **twelve per cent of his settlement money could not be opened by anything.**
# Nothing anywhere said so: they were the right size, the right name, the right
# folder, and on the day board they had ARRIVED.

# What a file begins with, and what that makes it. Read from the formats
# themselves rather than from a name anybody chose.
A_ZIP = b"PK\x03\x04"
# **WHAT A PORTAL SENDS INSTEAD OF A REPORT (cycle 46, R2#9).** A sign-in page, a
# "something went wrong" page, an error in JSON. Every one of them is text, and
# text was being called `csv` -- so it landed under a real report's name, with a
# real size, and the day board said the day had arrived.
#
# **THAT IS THE WORST FAILURE ON THE LIST**, and this project has already written
# it down twice about other paths: a sign-in page saved as a report is a file, it
# has a size, and everything downstream believes it.
A_WEB_PAGE = (b"<!doctype", b"<!DOCTYPE", b"<html", b"<HTML", b"<?xml")
SOMETHING_IN_JSON = (b"{", b"[")
AN_OLD_SPREADSHEET = b"\xd0\xcf\x11\xe0"

# What tells a spreadsheet from a plain zip that happens to hold one. An `.xlsx`
# IS a zip -- so "it starts with PK" settles nothing, and a check that stopped
# there would call every spreadsheet a zip.
INSIDE_A_SPREADSHEET = "xl/"

# What a wrapped file may be for it to be worth unwrapping.
WORTH_UNWRAPPING = ("xlsx", "xls", "csv")

ZIP = "zip"
UNKNOWN = "unknown"
# **THE PLATFORM SENT A PAGE, not a report.** Its own kind, because what somebody
# does about it is different: a page nearly always means the sign-in has run out.
A_PAGE = "a-web-page"
# And something in JSON is nearly always the platform saying no in its own words.
NOT_A_REPORT = "not-a-report"

# **THE BIGGEST ONE FILE INSIDE A ZIP THAT IS WORTH READING.**
#
# **MEASURED ON HIS OWN DRIVE: 1,406 files, and the biggest is 11.5 MB** -- a
# Meesho inventory export. Everything else is under six. Two hundred is far
# above anything real and far below what would take a runner down, which is
# what a ceiling is for: it is not a guess at how big a report gets, it is the
# line past which something is wrong.
BIGGEST_ONE_INSIDE = 200 * 1024 * 1024

class NotAReport(RuntimeError):
    """The platform sent something that is not a report at all.

    **A SIGN-IN PAGE SAVED AS A REPORT IS THE WORST POSSIBLE OUTCOME**: it is a
    file, it has a size, and everything downstream believes the day arrived. So
    it is refused here rather than landed, which leaves the day reading as
    missing -- true, and chaseable.

    **ITS OWN KIND**, because what somebody does about it is different from a
    broken download: a page nearly always means the sign-in has run out.
    """


class TooBig(RuntimeError):
    """What is inside says it unpacks to more than anything real.

    **ITS OWN KIND, because the answer to it is not the answer to a bad zip.**
    A zip that will not open is a broken download and is fetched again; this is
    a file that opens perfectly and should not be read, and the original is
    kept so somebody can look at it.
    """


def what_it_really_is(body: bytes) -> str:
    """What these bytes actually are, whatever anybody called them.

    Answers an extension -- `xlsx`, `xls`, `zip`, `csv` -- or `unknown`.

    **AN `.xlsx` IS A ZIP.** Both begin `PK`, so the only way to tell them apart
    is to look inside: a spreadsheet carries an `xl/` folder and a plain zip does
    not. Stopping at the first four bytes would call every spreadsheet a zip and
    rename all of them.
    """
    raw = bytes(body or b"")
    if raw.startswith(AN_OLD_SPREADSHEET):
        return "xls"
    if not raw.startswith(A_ZIP):
        if not raw:
            return UNKNOWN
        # **A PAGE IS NOT A REPORT (cycle 46, R2#9).** Anything that was not a zip
        # used to be called `csv`, so a portal's sign-in page or its "something
        # went wrong" page landed under a real report's name and the board said
        # the day had arrived.
        looking = raw.lstrip()[:64]
        if looking.startswith(A_WEB_PAGE):
            return A_PAGE
        if looking.startswith(SOMETHING_IN_JSON):
            return NOT_A_REPORT
        # Everything else this fetches is text of one kind or another. Which kind
        # is the name's business; the point of this function is the zip.
        return "csv"
    import io  # noqa: PLC0415 - only ever needed on this one path
    import zipfile  # noqa: PLC0415 - in Python itself; nothing is installed (D111)

    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as book:
            names = book.namelist()
    except zipfile.BadZipFile:
        return UNKNOWN
    if any(one.startswith(INSIDE_A_SPREADSHEET) for one in names):
        return "xlsx"
    return ZIP


def _inside_a_wrapper(raw: bytes) -> Optional[Tuple[str, bytes]]:
    """The one spreadsheet inside a plain zip, or None.

    **EXACTLY ONE, OR NOTHING.** A zip holding two is not something to choose
    between: picking one would put half a day's money in the folder and call it
    the day. Meesho's GST export really does carry two -- sales and returns --
    and the honest answer for that is to leave it alone and say so.

    **THE BYTES ARE READ OUT OF THE ZIP. NOTHING IS RENAMED.** His own words:
    *"if you try to convert the extension from a ZIP to an Excel file, I don't
    think it is going to work. It has to be properly extracted."* Correct, and it
    is why this reads the entry rather than relabelling the wrapper.

    **THE REFERENCE ALREADY SOLVED THIS AND THE TWO AGREE** --
    `process.py:_unwrap_zipped_xlsx` in the Rumee Dashboard does the same: refuse
    if it is already a real workbook, otherwise read the single inner entry out.
    Two differences, both deliberate:

      - it asks for `[Content_Types].xml`, which **every** OOXML file has, so a
        `.docx` would pass it. This asks for `xl/`, which only a workbook has.
      - it needs the zip to hold exactly one entry. This ignores folder entries
        and anything a reader could not open, so a workbook zipped inside a
        folder still comes out.
    """
    import io  # noqa: PLC0415
    import zipfile  # noqa: PLC0415

    with zipfile.ZipFile(io.BytesIO(raw)) as book:
        worth = [
            one for one in book.infolist()
            if not one.filename.endswith("/")
            and one.filename.rsplit(".", 1)[-1].lower() in WORTH_UNWRAPPING
        ]
        if len(worth) != 1:
            return None
        only = worth[0]
        # **HOW BIG IT SAYS IT IS, ASKED BEFORE IT IS READ (cycle 46, R2#10).**
        #
        # A zip says what each entry unpacks to, and reading without asking is how
        # a few kilobytes becomes gigabytes in memory. **A runner killed for
        # running out of memory leaves NO evidence at all** -- the process dies,
        # nothing flushes, and the log says nothing about a night that produced
        # nothing. That is the one failure this whole package cannot report.
        #
        # **Refused out loud instead**, which is a sentence somebody can act on.
        if only.file_size > BIGGEST_ONE_INSIDE:
            raise TooBig(
                f"{only.filename} unpacks to {only.file_size} bytes, which is more than "
                f"{BIGGEST_ONE_INSIDE}. It has been left as it came rather than read."
            )
        return only.filename.rsplit(".", 1)[-1].lower(), book.read(only)


def the_file_that_matters(file_name: str, body: bytes) -> Tuple[str, bytes, Optional[str]]:
    """The file to put away, named for what it is. Answers `(name, body, note)`.

    **THE NAME IS CORRECTED, NEVER THE DATE.** Only the extension moves; the data
    date the whole day board is built on is left exactly as it was.

    **A ZIP HOLDING ONE SPREADSHEET IS UNWRAPPED**, so what lands is something a
    reader can open. **A zip holding anything else is left as it came and SAID**
    -- there is nothing safe to choose, and the original is what makes a bad read
    fixable without re-fetching.

    `note` is a sentence for the run log when something was not as expected, or
    None when it was. **Silence here would be the same silence that hid eleven of
    his files for two months.**
    """
    # **NOTHING AT ALL IS HANDED STRAIGHT BACK, UNTOUCHED.** "No file came back"
    # and "a file with nothing in it" are two different failures with two
    # different sentences, and turning the first into the second here would
    # collapse them -- so a fetch that returned nothing would be reported as an
    # empty file, and the day it belongs to would read as fetched.
    if body is None or body == b"":
        return str(file_name or ""), body, None
    raw = bytes(body)
    named = str(file_name or "")
    has = named.rsplit(".", 1)[-1].lower() if "." in named else ""
    really = what_it_really_is(raw)

    if really == ZIP:
        inside = _inside_a_wrapper(raw)
        if inside is None:
            return named, raw, (
                f"{named} came down as a zip with nothing in it a reader can open, so it has "
                "been put away exactly as it arrived. Somebody has to look inside it."
            )
        was, unwrapped = inside
        return _renamed(named, was), unwrapped, (
            f"{named} came down as a zip with one {was} inside it. The {was} has been put "
            "away and the wrapper thrown, so it can be read."
        )

    if really in (A_PAGE, NOT_A_REPORT):
        # **NOT LANDED AT ALL (cycle 46, R2#9).** Anything that was not a zip used
        # to be called `csv`, so a portal's sign-in page went into the seller's
        # Drive under a real report's name -- right name, right size, right
        # folder, and ARRIVED on the day board. **Refused instead**, which leaves
        # the day reading as missing: true, and something the catching-up will
        # chase.
        raise NotAReport(
            f"{named} came down as "
            + ("a web page" if really == A_PAGE else "a message rather than a report")
            + ". That is usually the platform asking to be signed in to again. "
            "Nothing has been put away, so the day is still owed."
        )

    if really == UNKNOWN or really == has:
        return named, raw, None

    # **RENAMED RATHER THAN REFUSED.** A spreadsheet under a `.zip` name is a
    # perfectly good file that nothing will open; the fetching worked and only
    # the labelling was wrong, so the labelling is what changes.
    return _renamed(named, really), raw, (
        f"{named} is really a {really} rather than a {has or 'file with no ending'}, "
        f"so it has been put away as a {really}."
    )


def _renamed(file_name: str, ending: str) -> str:
    """The same name with a different ending. **The date never moves.**"""
    stem = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
    return f"{stem}.{ending}"
