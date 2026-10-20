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
from datetime import date, timedelta
from typing import Iterable, Optional, Sequence, Tuple

from reports import Report

# `<platform>_<report-without-its-platform-prefix>_<data date>.<extension>`
# The date is always ISO and always present. Read back by DATE_IN_NAME below.
DATE_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")

# **THE ONE OTHER SHAPE OF A DAY'S NAME: A RANGE ASKED FOR IN ONE REQUEST (P16, D424).**
# `<platform>_<report>_<from>_to_<to>.<ext>`, e.g. `flipkart_fk_orders_2026-09-29_to_2026-10-03.xlsx`.
# **ITS DAY IS ITS `to` DAY** -- Flipkart names the row by its end date, and the ledger's "newest
# file wins" must see a range fetched today as new as its last day, not as old as its first.
A_RANGE_IN_NAME = re.compile(r"_(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})\.[A-Za-z0-9]+$")

# **MOST DAYS ONE RANGE FILE MAY NAME.** One press takes at most 31 days (`extension/screen.js`
# `AS_MANY_DAYS_AS_ONE_PRESS_TAKES`, counting both ends), so a name claiming more was not written by
# this product, and reading it would spread one file over a stretch of days it cannot be holding.
MOST_DAYS_IN_A_RANGE_FILE = 31


def file_name_for(a_report: Report, data_date: date) -> str:
    """What one day's file of this report is called.

    **ONE PLACE BUILDS IT AND ONE PLACE READS IT BACK.** Two spellings of a naming
    convention is two records of one fact, and the day board's entire idea of
    whether something arrived rests on these agreeing.

    """
    return f"{a_report.platform}_{a_report.id}_{data_date.isoformat()}.{a_report.extension}"


def file_name_for_range(a_report: Report, first_day: date, last_day: date) -> str:
    """What the file of one request for several days is called.

    **ONLY WHEN THE FIRST DAY IS BEFORE THE LAST.** A range of one day is a day file, named
    exactly as `file_name_for` names it, so the daily files stay as the reader knows them.
    **NOTHING IN A RUN CALLS THIS -- THE EXTENSION NAMES A RANGE FILE (`walk.js` `theFileName`)**; this is the Python half of that one
    shape, kept so `tools/export_recipes_checks.py` can hold the two builders equal, report by report, and so a reader here can be
    checked against a name built by the rule rather than typed out. **A range the wrong way round, or longer than one press takes, is refused**, because the
    name is what every later reader trusts about which days the file holds.
    """
    if first_day == last_day:
        return file_name_for(a_report, last_day)
    if first_day > last_day:
        raise ValueError(f"a range cannot start ({first_day}) after it ends ({last_day})")
    if (last_day - first_day).days + 1 > MOST_DAYS_IN_A_RANGE_FILE:
        raise ValueError(f"a range of {(last_day - first_day).days + 1} days is more than one file may name")
    return f"{a_report.platform}_{a_report.id}_{first_day.isoformat()}_to_{last_day.isoformat()}.{a_report.extension}"


def range_in_name(file_name: str) -> Optional[Tuple[date, date]]:
    """The first and last day a range file's name gives, or None when it names no real range.

    **A NAME THAT LOOKS LIKE A RANGE AND IS NOT ONE IS NOT A RANGE** -- two days the wrong way
    round, the same day twice, a day that does not exist, or more days than one file may name.
    """
    found = A_RANGE_IN_NAME.search(file_name or "")
    if not found:
        return None
    try:
        first_day, last_day = date.fromisoformat(found.group(1)), date.fromisoformat(found.group(2))
    except ValueError:
        return None
    if not first_day < last_day or (last_day - first_day).days + 1 > MOST_DAYS_IN_A_RANGE_FILE:
        return None
    return first_day, last_day


def days_in_name(file_name: str) -> Tuple[date, ...]:
    """Every day a file's NAME says it holds: its one day, or each day of a range, or none.

    **THE OTHER HALF OF `file_name_for_range`.** Asked of a range name it answers every day from
    the first to the last; asked of a day name, that one day; asked of a name with no day, or a
    range name that is not a real range, nothing.
    """
    the_range = range_in_name(file_name)
    if the_range is None:
        one = data_date_in(file_name)
        return (one,) if one is not None else ()
    first_day, last_day = the_range
    return tuple(first_day + timedelta(days=n) for n in range((last_day - first_day).days + 1))


def data_date_in(file_name: str) -> Optional[date]:
    """The data date inside a file name, or None if it has none.

    **A RANGE FILE'S DATE IS ITS LAST DAY.** Taking the first date in the name would give a
    range file the age of its first day, and the ledger would leave its rows alone as older than
    day files it overlaps. **A name that looks like a range and is not one answers None** rather
    than its first date, so it is reported as undated and not read as the wrong day.

    **None IS A REAL ANSWER AND IT IS A PROBLEM, not a nought.** A file with no
    date in its name is a file nothing downstream can ever find. It is reported as
    itself -- see `undated` below -- rather than silently counted as missing,
    which is what happened to seven real files for six weeks.
    """
    if A_RANGE_IN_NAME.search(file_name or ""):
        the_range = range_in_name(file_name)
        return the_range[1] if the_range else None
    found = DATE_IN_NAME.search(file_name or "")
    if not found:
        return None
    try:
        return date.fromisoformat(found.group(1))
    except ValueError:
        return None


# ------------------------------------------------ how long a report file is kept (job 40)
#
# **THE RULE, READ FROM THE OFFICIAL SOURCES ON 2026-10-05 (Golden Rule 1), NOT FROM "FIVE TO
# SEVEN YEARS":**
#
#   CGST Act 2017, section 36 "Period of retention of accounts" -- *"Every registered person
#   required to keep and maintain books of account or other records in accordance with the
#   provisions of sub-section (1) of section 35 shall retain them until the expiry of
#   seventy-two months from the due date of furnishing of annual return for the year pertaining
#   to such accounts and records"*, with a proviso that a person in an appeal, revision, other
#   proceedings or an investigation keeps what pertains to it for one year after final disposal
#   *"or for the period specified above, whichever is later"*.
#   https://cbic-gst.gov.in/pdf/CGST-Act-Updated-30092020.pdf (CBIC's own site, page 67 of the
#   copy updated to 30 September 2020).
#
#   CGST Rules 2017, rule 80(1) as substituted by notification 30/2021-Central Tax -- the annual
#   return (FORM GSTR-9) *"on or before the thirty-first day of December following the end of
#   such financial year"*. https://gstcouncil.gov.in/sites/default/files/2024-05/notfctn-30-central-tax-english-2021.pdf
#
# So a file for a day in a financial year (April to March) is kept until 72 months after the
# 31 December that follows that year's end. **THIS IS THE REASON, AND IT IS WHAT ANSWERS AMAZON'S
# 18-MONTH LIMIT:** Amazon's own policy allows longer retention where *"longer retention is
# legally required"* (Finding 44), and this section is the law that requires it.
GST_KEEP_MONTHS = 72

# **THE DUE DATE IS EXTENDED BY NOTIFICATION FROM TIME TO TIME**, which moves the end of the period
# LATER -- and a file removed a few months early is a legal record gone, where one kept a year too
# long costs nothing. So nothing is removed until this much after the date the rule gives. Said
# here so that the one place that decides is one place: Control may shorten it, never silently.
WAIT_FOR_EXTENDED_DUE_DATES = timedelta(days=366)

# **THE CASE THE RUN CANNOT SEE: a seller in an appeal or an investigation must keep more.** The run
# cannot know, so it says in the log what it removed and why, and it moves to the bin, not away.


def gst_keep_until(data_day: date) -> date:
    """The last day a report file for this data day must be kept, by section 36 and rule 80(1)."""
    year_the_return_covers_ends = data_day.year + 1 if data_day.month >= 4 else data_day.year
    return date(year_the_return_covers_ends + GST_KEEP_MONTHS // 12, 12, 31)


# **ONLY A FILE NAMED THE WAY THE RUN AND THE EXTENSION NAME A DAY'S REPORT MAY EVER BE REMOVED**:
# `<platform>_<report>_<day>.<ext>`, or with a campaign after the day for the per-campaign ads
# files. A loose date anywhere in a name -- `backup_2017-08-01_final.xlsx`, or a copy the seller
# made, `..._2017-08-01 (1).csv` -- is somebody else's file and is kept.
A_DAYS_REPORT_FILE = re.compile(
    r"(?:amazon|flipkart|meesho)_[a-z0-9_]+?_(\d{4}-\d{2}-\d{2})(?:_to_\d{4}-\d{2}-\d{2}|_[A-Za-z0-9-]+)?\.[a-z]+"
)


def why_a_report_file_may_go(file_name: str, today: date) -> Optional[str]:
    """Words saying why this file is past what the law asks to be kept, or None to keep it.

    **A FILE WITH NO DAY IN ITS NAME IS KEPT, AND SO IS ANY FILE NOT NAMED AS A DAY'S REPORT** -- nothing
    here can say which days it holds.
    """
    shape = A_DAYS_REPORT_FILE.fullmatch(file_name or "")
    # **A RANGE FILE IS KEPT BY ITS LAST DAY** -- the day `data_date_in` gives it -- and a name
    # that only looks like a range is not ours to remove.
    day = data_date_in(file_name) if shape else None
    if day is None:
        return None
    until = gst_keep_until(day)
    if today <= until + WAIT_FOR_EXTENDED_DUE_DATES:
        return None
    return (
        f"{file_name} is for {day.isoformat()}; the GST law (CGST Act 2017 section 36, 72 months after the "
        f"annual return's due date) asks for it to be kept until {until.isoformat()}, and that has passed"
    )


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

    def covers(self, day: date) -> bool:
        """Does this file hold that day's data?

        **THE ONE QUESTION THE DAY BOARD, THE MANIFEST AND THE SCHEDULE ALL ASK,
        ASKED IN ONE PLACE.** It used to be spelt `one.data_date == day` in three
        of them, which was true of every report there was -- and the moment one
        report stopped having its day in its name, all three would have quietly
        answered "no" about a file holding every day it was asked about.

        **EVERY REPORT'S DAY IS IN ITS NAME** (every day of it, when the name is a
        range), so the name is the one source.
        """
        return day in days_in_name(self.name)


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
        if one.is_empty:
            continue
        # **A RANGE FILE ANSWERS WITH EVERY DAY IT NAMES, here and nowhere else.** Answering with
        # its last day alone would make every other day inside it look like a hole, and each
        # would be fetched again -- on Flipkart's orders and payments that spends the twenty a day.
        out.update(days_in_name(one.name))
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
