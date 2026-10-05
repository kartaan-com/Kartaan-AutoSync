"""Reading what is new in the seller's folder, and remembering that it was read.

**THIS IS THE FILE THAT WAS MISSING, and it is the same shape of hole D171 keeps
naming: four finished, checked, proved files with nothing calling them.**
`whats_new.py` decides what is new, `table.py` and `sheet.py` turn bytes into
rows, `orders.py` turns rows into sales, `ledger.py` decides what to write --
and until this file, `nightly.py` called none of them. So `with_files_read` was
never called by anything, the record's list of what has been read stayed empty
for ever, and **what is new in the folder was worked out from nothing every
night.**

---

**A FILE IS MARKED AS READ ONLY WHEN ITS SALES HAVE ACTUALLY LANDED SOMEWHERE,
and that is the one rule this file is written around.**

`whats_new.now_read` already says *"only what actually read"*, meaning a file
that was fetched back and parsed. This is that rule taken one step further, and
the step matters more than the rule: **a file read into nowhere has had no
effect, so marking it read would lose it for ever.** The list exists to stop a
file being read twice; a file whose sales reached nothing has not been read once.

So there is exactly one place a sale can land -- `record_the_sales` -- and a file
is added to the list on the line after that call returns, per file, never in a
batch at the end. A run that dies halfway keeps what it had already recorded and
loses nothing it had not.

**AND WHEN THERE IS NOWHERE TO PUT A SALE, NOTHING IS READ AND NOTHING IS
MARKED.** That is still today's real state, and the reason has changed rather
than gone: `ledger_sheet.py` now makes the seller's sheet, remembers it and
writes into it -- and it **REFUSES to start** while D157's four date-marker
columns do not exist, because without them a file that turns up late puts its old
figure back over a newer one, in the money, silently. Rather than go quiet about
it, this **still lists the folders and says how many files are sitting there
unread**, every night, in the run's own summary. A number that grows every night
is a thing somebody notices; a sentence in a file is not.

---

**WHAT CAN BE READ TODAY IS ORDERS AND PAYMENTS, AND NOTHING ELSE. Named, never derived.**

`orders.py` knows what a platform calls things in an orders file, and `payments.py` (job 36) in a payments file: a payments
file is matched to the orders the ledger already has, on the order id, and never makes a row. Returns and claims have no
mapping anywhere, so their files are **not listed, not read and not marked** -- because an id in the record for a file
nothing has actually read is a file the reader written next month would never see.

The list below is written out by name rather than worked out from a report id,
because *"every id ending in `_orders`"* is a check against a spelling, and a
spelling is not a fact (D170). A check pins every id here against `reports.py`,
so a typo cannot ship.

---

**LETTING GO OF AN ID IS D161, AND ITS GUARD IS WIDENED HERE BECAUSE THERE IS
MORE THAN ONE FOLDER.**

His rule: an id is let go of only when its file has gone from the folder --
never after so many days, because a landed file is never removed, so a day-count
would let go of ids for files still sitting there and each would be read again
and put its old figures back over newer ones.

`whats_new.still_worth_remembering` enforces that against ONE listing, and
refuses to let go of anything when that listing comes back empty. **Here there
are three folders**, and a folder that failed makes its files look tidied away
while the other two carry the union past that guard. So:

  - **a folder that could not be listed at all: nothing is let go of, anywhere.**
  - **a folder that came back with no files in it while something is remembered:
    the same.**

Both say why, in words, in the night's summary.

---

**NOTHING HERE OPENS A CONNECTION.** The folder listing, the bytes of a file and
the place a sale lands are all handed in, exactly as every door in this package
has its transport handed in -- so every rule above is checked with no Drive, no
Google account and no internet.
"""

import csv
import io
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import landing
import manifest
import orders
import payments
import sheet
import table
import views
import whats_new
from firestore_door import TheirDatabaseSaidNo
from ledger import LedgerRefused, Reading, which_markers
from reports import report as the_report
from sales import FROM_FIELD

# **WHAT AN ORDERS REPORT IS ENTITLED TO WRITE (D150 rule 1).** It knows nothing
# about settlements, returns or charges, and naming the columns here is what
# makes that impossible to forget rather than merely remembered.
#
# **`id` IS NOT AMONG THEM ON PURPOSE.** A sale's name is what a row IS, not
# something a report states about it, and `ledger.plan` writes it itself when it
# first sees a sale.
# **AND `ordersOn` IS AMONG THEM, WHICH IS D157 FINALLY REACHING A ROW.** The
# four date markers landed in the ERP's column list on 2026-09-06 and every
# refusal built around them lifted itself the same day -- and nothing anywhere
# put a date in one, so every row written still could not say which day's file
# produced it. **A column a report may not write is a column that stays blank
# however the sale was built** (rule 1, enforced in `ledger._what_a_sale_says`),
# so naming it here is what lets the value through.
#
# **AND ONLY THIS ONE OF THE FOUR.** Returns, payments and claims have no reader,
# so a date in one of their columns would be a date nobody measured.
WHAT_ORDERS_KNOWS = ("platform", "orderId", "on", "sku", "qty", "gmv", "status", "whatHappened", "ordersOn")

# **WHICH RULES THE LIST OF READ FILES WAS MADE UNDER (job 37).** A file already read before the orders
# reader began to write the platform's status word would never be opened again, so the five cancelled orders
# already in his ledger would go on looking like sales for ever. Change this name whenever the orders reader
# learns to write a column it did not, and every file is read once more -- which is safe, because reading a
# file again writes the same figures and an older file never undoes a newer one (D150 rule 2).
READING_RULES = "orders-with-the-platforms-status-word-and-what-happened"



@dataclass(frozen=True)
class HowToRead:
    """One report this job can turn into sales, and how its file opens.

    `which_sheet` and `header_row` are the two things a spreadsheet needs and a
    text file mostly does not. **Flipkart's orders are not the first sheet** --
    the first is `Help`, and a reader that took it would report that the seller
    had no orders, which is a lie the day board would show as a believable zero.
    """

    report_id: str
    knows: Tuple[str, ...]
    which_sheet: Optional[str] = None
    header_row: int = 1
    # **WHAT KIND OF FILE (job 36).** Orders make the rows of the ledger; payments only add money to rows it already has, and
    # are matched to them on the order id. Everything below that differs between the two asks this one field.
    kind: str = "orders"
    # **FOR A TEXT FILE WHOSE HEADER IS NOT ON A FIXED LINE** (Amazon's unified transaction report has a block of definitions
    # above it, which the platform may lengthen): the words its header line starts with. Found, never counted down to.
    header_starts: Optional[str] = None


# **WHAT A PAYMENTS REPORT IS ENTITLED TO WRITE (D150 rule 1, job 36):** the settlement, the charges, and the day of the file that
# said them. Never an order's own columns: a payment cannot change what was sold, only say what was paid for it.
WHAT_PAYMENTS_KNOW = payments.WHAT_PAYMENTS_KNOW

WHAT_CAN_BE_READ: Tuple[HowToRead, ...] = (
    HowToRead("me_orders", WHAT_ORDERS_KNOWS),
    HowToRead(
        "fk_orders",
        WHAT_ORDERS_KNOWS,
        which_sheet=orders.WHERE_FLIPKART_ORDERS_ARE,
        header_row=orders.FLIPKART_HEADER_ROW,
    ),
    HowToRead("az_orders", WHAT_ORDERS_KNOWS),
    HowToRead(
        "fk_payments",
        WHAT_PAYMENTS_KNOW,
        which_sheet=payments.WHERE_FLIPKART_PAYMENTS_ARE,
        header_row=payments.FLIPKART_HEADER_ROW,
        kind="payments",
    ),
    HowToRead(
        "me_payments",
        WHAT_PAYMENTS_KNOW,
        which_sheet=payments.WHERE_MEESHO_PAYMENTS_ARE,
        header_row=payments.MEESHO_HEADER_ROW,
        kind="payments",
    ),
    HowToRead(
        "az_settlements",
        WHAT_PAYMENTS_KNOW,
        header_starts=payments.AMAZON_HEADER_STARTS,
        kind="payments",
    ),
)


# **HOW EACH LISTING IS DOING (job 86 part A).** These three make no sale and touch no ledger column, so they are kept apart from the
# list above (which the ledger's own guards walk) and joined to it only where a night reads a folder. Each is read into a record per
# listing in the seller's own database (`firestore_door.a_views_sink`), not into the sheet.
WHAT_VIEWS_CAN_BE_READ: Tuple[HowToRead, ...] = tuple(
    HowToRead(report_id, (), header_row=views.way_for(report_id).header_row, kind="views")
    for report_id in ("fk_views", "fk_ads_fsn", "me_ads_catalog")
)

# **EVERY REPORT THE RUN FETCHES IS READ, OR SAYS IN WORDS WHY IT IS NOT YET (job 35).**
#
# **THE FAULT THIS CLOSES (Finding 51):** `reports.REPORTS` declares twenty-six reports and
# `WHAT_CAN_BE_READ` holds three, and nothing tied the two lists -- so twenty-three reports landed in
# his Drive every day and nothing ever read them, and nobody could say which of them was meant to be.
# His own question: *"how does the pipeline know what files AutoSync is placing and what folders it
# is using?"*
#
# **THE RULE, MECHANISED (his 19:42 ruling): a check fails if any report in `REPORTS` has neither a
# reader above nor an entry below.** A new stream (42, 43, 44) cannot be added without one. An entry
# below is the plan's decision for that report, taken ONE BY ONE, and the piece that builds its
# reader; when the reader is built the entry moves up and the check refuses it in both places.
WHAT_IS_FETCHED_AND_NOT_READ_YET: Dict[str, str] = {
    "fk_keywords": (
        "switched off by his ruling (piece 49), so it is not fetched at all and has no folder"
    ),
    "az_returns": "decided: into the returned columns and the returns screen's lookup -- pieces 78 and 77",
    "fk_returns": "decided: into the returned columns and the returns screen's lookup -- pieces 78 and 77",
    "me_returns": "decided: into the returned columns and the returns screen's lookup -- pieces 78 and 77",
    "fk_claims": "decided: into the claims columns of the ledger and the ERP's Claims section -- piece 78",
    "me_claims": "decided: into the claims columns of the ledger and the ERP's Claims section -- piece 78",
    "fk_listings": "decided: into Needs Review, for him to let in -- piece 41",
    "me_catalog": "decided: into Needs Review, for him to let in -- piece 41",
    "me_views": (
        "a whole-shop figure with no listing in it, so it has no per-listing record; Meesho's views per product "
        "are piece 44 (Product Performance), which will write them into the same listing record"
    ),
}
for _ads in (
    "fk_ads_daily", "fk_ads_placements", "fk_ads_overall", "fk_ads_search", "fk_ads_orders",
    "fk_ads_kw", "me_ads", "me_ads_summary",
):
    WHAT_IS_FETCHED_AND_NOT_READ_YET[_ads] = (
        "decided: an ads record per day, shown beside sales, and the ad spend becomes a charge on the ledger. "
        "Its reader is the next piece built; the place its record will go (a listing's ad figures) exists since job 86 part A"
    )
del _ads


def why_a_report_has_no_decision() -> str:
    """Words naming every report with neither a reader nor a written reason, or '' when all are decided.

    **ALSO REFUSES THE TWO LISTS HOLDING THE SAME REPORT, AND A REPORT THAT DOES NOT EXIST**: a reader built
    and its old reason left standing is a report that says it is not read while it is.
    """
    from reports import REPORTS  # noqa: PLC0415 - kept beside its one use

    read = {one.report_id for one in WHAT_CAN_BE_READ + WHAT_VIEWS_CAN_BE_READ}
    said = set(WHAT_IS_FETCHED_AND_NOT_READ_YET)
    known = {one.id for one in REPORTS}
    wrong = []
    undecided = sorted(known - read - said)
    if undecided:
        wrong.append("reports with no reader and no written reason: " + ", ".join(undecided))
    both = sorted(read & said)
    if both:
        wrong.append("reports both read and said to be not read: " + ", ".join(both))
    stray = sorted((read | said) - known)
    if stray:
        wrong.append("entries for reports that do not exist: " + ", ".join(stray))
    return "; ".join(wrong)


@dataclass(frozen=True)
class WhatTheNightRead:
    """What the reading half of one night came to.

    **`files_read` IS THE WHOLE LIST TO KEEP**, not tonight's additions -- what
    was remembered, capped to the folder, plus what actually read tonight. It is
    what goes straight into `between_runs.with_files_read`, so there is no second
    place where the two halves of that sum could be put together differently.
    """

    files_read: Tuple[str, ...] = ()
    read_tonight: Tuple[str, ...] = ()
    new_files: int = 0
    empty_files: int = 0
    already_read: int = 0
    sales: int = 0
    rows_refused: int = 0
    let_go_of: Tuple[str, ...] = ()
    # Why a file could not be read, by name. **Never a count on its own.**
    could_not_read: Tuple[str, ...] = ()
    # Why the LEDGER refused a file, by name. **Kept apart from the one above,
    # and that separation is the whole of `is_a_defect` below.** A file that will
    # not parse is the platform's doing; a file the ledger refuses is OURS.
    the_ledger_refused: Tuple[str, ...] = ()
    # Why a folder could not be listed, by name. This one is our own defect: with
    # a folder unknown, what is new cannot be worked out at all.
    could_not_list: Tuple[str, ...] = ()
    # Why nothing was let go of when something otherwise would have been.
    refused_to_forget: str = ""
    # Why nothing was read at all, when that was the answer. Empty when reading
    # did happen.
    nowhere_to_put_it: str = ""
    # **WHAT EACH FILE READ TONIGHT CAME TO, FOR THE STANDING RECORD (job 38):** which report and day, what the
    # file held and what was read from it -- two numbers, never one.
    reads: Tuple["manifest.Read", ...] = ()
    # **HOW EACH LISTING IS DOING (job 86 part A):** figures written into listing records tonight, and files left unread because
    # there was nowhere to write them.
    listing_figures: int = 0
    views_waiting: int = 0
    # Why the seller's own database refused a listing record. **OURS, like the ledger refusing**: the usual cause is the ERP's rules
    # (commit 94de631) not yet published to that seller, and a night that says green while every night refuses is the fault kept
    # apart above.
    the_database_refused: Tuple[str, ...] = ()

    @property
    def is_a_defect(self) -> bool:
        """**A FOLDER THAT COULD NOT BE LISTED IS OURS (D108).** What is new
        cannot be decided without it, so the night's reading is not to be
        trusted. A single file that would not read is the platform's, and is
        named, counted and left green.

        **AND SO IS A FILE THE LEDGER REFUSED, which is a distinction this used
        not to make.** A malformed spreadsheet is the platform's; the ledger
        saying "this reading declares a date marker and carries no date" is a
        fault in OUR OWN code. Counted with the platform's, a night where every
        single file was refused by our own rule would report GREEN while the
        seller's files piled up unread for ever -- **found by an independent
        reviewer, and it is Golden Rule 29 exactly.**"""
        return bool(self.could_not_list or self.the_ledger_refused or self.the_database_refused)

    def says(self) -> str:
        """One line for the night's summary. **EVERY COUNT, EVEN THE NOUGHTS.**

        **THIS IS THE WHOLE ANSWER TO "a night that read nothing must not look
        like a night that read everything".** Two nightly runs have already
        "succeeded" in eleven and forty-seven seconds while doing nothing,
        because no platform is connected -- correct behaviour, and indis-
        tinguishable in a summary from a night that worked. So every number is
        said out loud whatever it is, and the one case where nothing was read at
        all says so in its own words rather than by printing noughts.
        """
        if self.nowhere_to_put_it:
            said = f"Read nothing: {self.nowhere_to_put_it}"
            if self.new_files:
                said += (
                    f"  {self.new_files} file(s) are sitting in the folder unread "
                    "and will still be there when there is."
                )
        else:
            said = (
                f"Read {len(self.read_tonight)} of {self.new_files} new file(s): "
                f"{self.sales} sales, {self.rows_refused} rows refused, "
                f"{len(self.could_not_read)} file(s) could not be read, "
                f"{len(self.the_ledger_refused)} refused by our own ledger, "
                f"{self.empty_files} arrived empty, {self.already_read} already read, "
                f"{len(self.let_go_of)} id(s) let go of."
            )
        if self.listing_figures or self.views_waiting:
            said += f"  {self.listing_figures} listing figure(s) read into the listing records."
        if self.views_waiting:
            said += (
                f"  {self.views_waiting} listing traffic/ads file(s) were left unread because the seller's database "
                "could not be reached for them; they will be read when it can."
            )
        if self.refused_to_forget:
            said += f"  Nothing was let go of: {self.refused_to_forget}"
        for why in self.could_not_list:
            said += f"  A folder could not be listed: {why}"
        for why in self.could_not_read:
            said += f"  {why}"
        # **SAID SEPARATELY, AND SAID AS OURS.** A reader seeing these among the
        # platform's would go and look at the platform.
        for why in self.the_ledger_refused:
            said += f"  KARTAAN'S OWN LEDGER REFUSED A FILE: {why}"
        for why in self.the_database_refused:
            said += f"  THE SELLER'S DATABASE REFUSED A LISTING RECORD (publish the ERP's rules to this project, then run again): {why}"
        return said


def what_this_can_read(can_be_read: Sequence[HowToRead] = WHAT_CAN_BE_READ) -> Tuple[str, ...]:
    """The report ids this job can turn into sales.

    Asked here rather than worked out by whoever wants it, for the same reason
    `reports.on_the_api_door` exists beside its twin: each caller filtering the
    list itself is a second copy of one fact.
    """
    return tuple(one.report_id for one in can_be_read)


def _where_the_header_is(how: HowToRead, body: bytes, called: str) -> int:
    """The line a text file's column names are on: the one named, or the first line that starts with the words given.

    **A FILE WHOSE HEADER IS NOT FOUND IS REFUSED**, not read from line 1: a block of definitions read as a header would name
    no column the reader needs, and the file would be reported as one with no payments in it.
    """
    if not how.header_starts:
        return how.header_row
    text = table.one_line_endings(table.as_text(body))
    wanted = how.header_starts.strip().lower()
    # **COUNTED IN PARSED ROWS, AS `table.read` COUNTS THEM**, so a definition with a line break inside its quotes cannot make the
    # two disagree about which row is the header.
    for number, cells in enumerate(csv.reader(io.StringIO(text)), start=1):
        # **THE FIRST CELL IS THE WORDS, WHOLE.** A definition above the header can START with the same words
        # (`Date/Time: Posted date/time of the transaction`), and matching the start of the line takes that for the header.
        if cells and cells[0].strip().lower() == wanted:
            return number
    raise table.CannotRead(
        f"{called} has no line starting with {how.header_starts!r}, so there is no line to take the column names from."
    )


def _rows_in(how: HowToRead, body: bytes, called: str):
    """The file's rows, whatever kind of file it turns out to be.

    **WHAT IT REALLY IS IS READ OUT OF THE BYTES, NEVER OFF THE NAME.** This
    package names a landed file itself, from the extension in `reports.py`, so
    the name is ours and says nothing about what the platform actually sent --
    and `landing.py` already has the one function that looks inside.

    **A PORTAL'S SIGN-IN PAGE IS NOT A REPORT, and is refused as one by name.**
    Read as text it would parse into rows of HTML and be reported as a file with
    no columns Kartaan knows -- which is true, and says nothing about the real
    problem, which is that nobody is signed in.
    """
    really = landing.what_it_really_is(body)
    if really == "xlsx":
        return sheet.read(body, sheet=how.which_sheet, header_row=how.header_row)
    if really == "csv":
        return table.read(body, header_row=_where_the_header_is(how, body, called))
    raise table.CannotRead(
        f"{called} is {really}, which is not something this can read. It reads a "
        "spreadsheet or a text file, and a page or a wrapper is not either."
    )


def a_reading(how: HowToRead, one: whats_new.InTheFolder, body: bytes) -> Tuple[Reading, int]:
    """One file turned into a statement about sales, and how many rows it refused.

    **THE DAY COMES OUT OF THE FILE'S OWN NAME, and it is the file's DATA DATE
    rather than when it was fetched (D150 rule 2).** A file with no day in its
    name is refused rather than dated today: which of two statements is newer is
    what decides every figure, and a wrong answer there is money dated months
    out.

    **`which` IS DRIVE'S OWN ID, and it is not decoration.** Two files of one
    report and one data date are two separate statements -- a day fetched again
    lands under the same name (D110) -- and told apart only by report and date
    they look like one statement, so rule 3 has nothing to see.

    **CARRYING IT WAS ONLY HALF, AND THIS NOTE USED TO STOP HERE AS THOUGH IT
    WERE THE WHOLE.** With the id carried, the two files were still handed to
    `ledger.plan` in separate calls -- one file at a time is what makes the
    marking above safe -- and `plan` kept what it had decided inside the call, so
    it began every file knowing nothing. The tie was still invisible; what the id
    bought was that the SAME file won every time instead of a different one.
    **The other half is `ledger_sheet.recording_into`, which makes one
    `WhatTheNightHasDecided` for the night and hands it to every file.** Both are
    needed and neither is enough.
    """
    when = landing.data_date_in(one.name)
    if when is None:
        raise table.CannotRead(
            f"{one.name or one.which} has no day in its name, so there is no way to "
            "say whether what it holds is newer or older than what is already "
            "written. Nothing in it was read."
        )
    which = the_report(how.report_id)
    rows = _rows_in(how, body, one.name or one.which)
    # **THE FILE'S OWN DAY GOES ONTO EVERY SALE IT PRODUCES (D157).** It is
    # already worked out above, out of the file's name, and refused if it is not
    # there -- so there is no path through here that fills a marker with a
    # guess. Handed down rather than re-read, because two ways of reading a date
    # off a name is two answers waiting to disagree.
    return _a_reading_of_the_rows(how, one, rows, which.platform, when.isoformat())


def _a_reading_of_the_rows(how: HowToRead, one: whats_new.InTheFolder, rows, platform: str, day: str) -> Tuple[Reading, int]:
    """The rows of one file, turned into a reading by whichever reader its kind needs. **The one place the two kinds part.**"""
    if how.kind == "payments":
        paid = payments.read_payments(rows, platform, day)
        return (
            Reading(
                report=how.report_id, on=day, knows=how.knows, sales=paid.sales, which=one.which,
                only_existing=True, set_aside=paid.set_aside,
            ),
            len(paid.not_read),
        )
    was = orders.read_orders(rows, platform, data_date=day)
    return (
        Reading(
            report=how.report_id,
            on=day,
            knows=how.knows,
            sales=was.sales,
            which=one.which,
        ),
        len(was.not_read),
    )


def a_views_reading(how: HowToRead, one: whats_new.InTheFolder, body: bytes) -> views.WhatViewsSaid:
    """One traffic or ads file turned into figures per listing per day.

    **THE DAY OF A FILE WITH NO DATE INSIDE IT (Flipkart's ads by product) IS THE ONE ON ITS FIRST LINE, else the one in its
    name.** A rolling file names its days row by row, so the name only has to carry a day at all -- the same refusal every
    reader here makes, because which of two files is newer decides a figure.
    """
    when = landing.data_date_in(one.name)
    if when is None:
        raise table.CannotRead(
            f"{one.name or one.which} has no day in its name, so there is no way to say whether what it holds is newer or older "
            "than what is already written. Nothing in it was read."
        )
    rows = _rows_in(how, body, one.name or one.which)
    day = None
    if views.way_for(how.report_id).day is None:
        day = views.day_in_ads_header(body) or when.isoformat()
    said = views.read_views(how.report_id, rows, day)
    if not said.records and said.not_read:
        # **NOTHING READ FROM A FILE THAT HAD ROWS IS A FILE NOT READ, not a file read for good**: marked, it would never be opened again.
        raise table.CannotRead(f"no row of {one.name or one.which} could be read; the first was {said.not_read[0]}")
    return said


# A day no real file could ever be about, used only to drive the question below.
# **It is a real day** -- everything on the way through refuses one that is not --
# and it is nothing any fixture in this package also carries.
A_DAY_TO_ASK_WITH = "0001-01-02"


def would_a_file_say_which_day_it_is(how: HowToRead) -> bool:
    """Would a real file of this report really produce sales that say its own day?

    **THIS IS THE READER HALF OF D157'S GUARD, AND UNTIL A32 NOTHING ASKED IT.**
    `ledger_sheet.why_it_must_not_write_yet` said in its own words that it
    "ANSWERS THE TWO HALVES AT ONCE" and that "a report whose rows carry no
    marker cannot be told apart from a newer one, so it fails this". Both were
    false. `ledger.would_an_older_file_be_stopped` builds its own `Reading` with
    the markers ALREADY FILLED and hands it to `plan`: it drives the WRITING half
    honestly and never touches a reader. An independent reviewer proved it twice
    over -- taking `orders_on=data_date` out of `orders.read_orders`, and turning
    `a_reading`'s `data_date=when.isoformat()` into a fixed constant claiming
    every file is the same day -- and the guard said "safe to write" through
    both. **That is the third generation of one fault: a guard that reads as
    covering something it does not touch.**

    **SO THIS DRIVES THE READER, END TO END, ON A REAL FILE.** A one-row file is
    built out of the column names that platform's OWN mapping says it needs --
    nothing here spells a column, so a platform whose file changes shape changes
    this with it -- given a name with a day in it, and put through `a_reading`,
    which is the exact path a night takes. What comes out the other side is
    looked at: **every sale it produced must carry that day in a marker this
    report is entitled to write.**

    Both mutations above turn this False. The first leaves the marker empty, and
    `Reading` refuses the whole reading; the second fills it with a day that is
    not the file's, and the comparison below fails.

    **AND IT IS CHEAP AND COLD.** No Drive, no account, no network, no file on
    disk: a few hundred bytes made here and thrown away, asked once a night
    before anything reaches Google.
    """
    markers = which_markers(how.knows)
    if not markers:
        # A report that writes no marker cannot say which day's file wrote a
        # row, which is the whole of what D157 asked for.
        return False
    if how.kind == "payments":
        # **A PAYMENTS FILE IS DRIVEN THE SAME WAY, WITH A ONE-LINE TABLE BUILT OUT OF THE READER'S OWN COLUMN LISTS.** It goes
        # through the same `_a_reading_of_the_rows` a night uses, so the day it is handed is the day that comes back.
        try:
            which = the_report(how.report_id)
            reading = _a_reading_of_the_rows(
                how,
                whats_new.InTheFolder(which="asking", name="", size=1),
                payments.a_table_to_ask_with(which.platform),
                which.platform,
                A_DAY_TO_ASK_WITH,
            )[0]
        except Exception:  # noqa: BLE001 - any refusal is an answer of "no"
            return False
        return bool(reading.sales) and all(
            any(
                str(getattr(sale, FROM_FIELD[marker], "") or "").strip() == A_DAY_TO_ASK_WITH
                for marker in markers
            )
            for sale in reading.sales
        )
    try:
        which = the_report(how.report_id)
        way = orders.mapping_for(which.platform)
    except Exception:  # noqa: BLE001 - any refusal is an answer of "no"
        return False
    columns = list(dict.fromkeys(way.needs))
    said = {
        way.order_id: "asking-whether-a-file-says-which-day-it-is",
        way.sku: "asking",
        way.qty: "1",
        way.on: A_DAY_TO_ASK_WITH,
    }
    body = '\n'.join(
        [",".join(columns), ",".join(said[one] for one in columns), ""]
    ).encode("utf-8")
    one = whats_new.InTheFolder(
        which="asking",
        # **THE DAY IS IN THE NAME, because that is where the run reads it from.**
        name=f"{which.platform}_{how.report_id}_{A_DAY_TO_ASK_WITH}.csv",
        size=len(body),
    )
    try:
        reading, _ = a_reading(how, one, body)
    except Exception:  # noqa: BLE001 - any refusal is an answer of "no"
        return False
    if not reading.sales:
        return False
    return all(
        any(
            str(getattr(sale, FROM_FIELD[marker], "") or "").strip() == A_DAY_TO_ASK_WITH
            for marker in markers
        )
        for sale in reading.sales
    )


def read_what_is_new(
    already_read: Sequence[str],
    what_is_in_the_folder: Optional[Callable[[str], Sequence[whats_new.InTheFolder]]] = None,
    bring_it_back: Optional[Callable[[str], bytes]] = None,
    record_the_sales: Optional[Callable[[Sequence[Reading]], None]] = None,
    can_be_read: Optional[Sequence[HowToRead]] = None,
    record_views: Optional[Callable[[str, Dict], int]] = None,
) -> WhatTheNightRead:
    """Read every file in the seller's folders that has not been read before.

    `can_be_read` left out is every report this can read: the ledger's and how each listing is doing.
    `record_views(platform, records)` is where a listing's figures go and answers how many records it wrote; left out, the
    traffic and ads files are not opened and not marked, and the night says how many are waiting.

    **THE ONLY TWO THINGS THAT DECIDE WHAT IS NEW ARE THE FOLDER AND THE LIST OF
    WHAT HAS BEEN READ.** Nothing about tonight's fetching reaches this -- not a
    run, not a log, not a report's state -- and that is structural rather than
    remembered: there is no argument here through which it could arrive. His
    rule, and the word is his: *"solely based on what is new."*

    **NOT HANDED A FOLDER, OR NOWHERE TO PUT A SALE, IS NOT A FAILURE.** It is
    where this stands until the seller's sales ledger exists, and it is said in
    words rather than as a night of noughts.
    """
    if can_be_read is None:
        can_be_read = WHAT_CAN_BE_READ + WHAT_VIEWS_CAN_BE_READ
    remembered = tuple(sorted({
        str(one).strip() for one in (already_read or ()) if str(one).strip()
    }))

    if what_is_in_the_folder is None:
        return WhatTheNightRead(
            files_read=remembered,
            nowhere_to_put_it="this run was given no folder to look in.",
        )

    # **EVERY FOLDER IS LISTED FIRST, before a single file is opened.** Whether
    # an id may be let go of depends on ALL of them, and a run that read some
    # files and then found a folder it could not list must not let go of
    # anything on the strength of the folders it did manage.
    listed: Dict[str, List[whats_new.InTheFolder]] = {}
    could_not_list: List[str] = []
    for how in can_be_read:
        try:
            listed[how.report_id] = list(what_is_in_the_folder(how.report_id) or ())
        except Exception as wrong:  # noqa: BLE001 - reported, never swallowed
            could_not_list.append(f"{how.report_id}: {wrong}")

    new_files = 0
    empty_files = 0
    already = 0
    for how in can_be_read:
        if how.report_id not in listed:
            continue
        what = whats_new.what_is_new(listed[how.report_id], remembered)
        new_files += len(what.new)
        empty_files += len(what.empty)
        already += len(what.already)

    if record_the_sales is None or bring_it_back is None:
        # **NOTHING IS READ AND NOTHING IS FORGOTTEN.** A sale has nowhere to go,
        # so a file opened tonight would have to be opened again anyway -- and an
        # id let go of tonight is an id nothing would put back.
        return WhatTheNightRead(
            files_read=remembered,
            new_files=new_files,
            empty_files=empty_files,
            already_read=already,
            could_not_list=tuple(could_not_list),
            nowhere_to_put_it=(
                "there is nowhere yet to put a sale, so no file was opened and none "
                "was written down as read."
            ),
        )

    read_tonight: List[whats_new.InTheFolder] = []
    could_not_read: List[str] = []
    the_ledger_refused: List[str] = []
    the_database_refused: List[str] = []
    how_many_sales = 0
    rows_refused = 0
    reads: List["manifest.Read"] = []
    listing_figures = 0
    views_waiting = 0

    # **OLDEST FIRST, AND EVERY FOLDER'S FILES TOGETHER.** Handed over in the
    # order Drive answered a listing in, the last file to be recorded is the last
    # one Drive happened to name -- and the last one recorded is the one whose
    # figures stand. See `_oldest_first`.
    for how, one in _oldest_first(listed, can_be_read, remembered):
        if how.kind == "views":
            if record_views is None:
                views_waiting += 1
                continue
            try:
                said = a_views_reading(how, one, bring_it_back(one.which))
                record_views(said.platform, said.records)
            except TheirDatabaseSaidNo as wrong:
                the_database_refused.append(f"{one.name or one.which}: {wrong}")
                continue
            except Exception as wrong:  # noqa: BLE001 - named, never swallowed
                could_not_read.append(f"{one.name or one.which}: {wrong}")
                continue
            read_tonight.append(one)
            listing_figures += said.figures
            rows_refused += len(said.not_read)
            if said.not_read:
                could_not_read.append(
                    f"{one.name or one.which}: {len(said.not_read)} row(s) not read, the first being {said.not_read[0]}"
                )
            the_day = landing.data_date_in(one.name)
            if the_day is not None:
                reads.append(manifest.Read(
                    data_date=the_day, report_id=how.report_id, file_name=one.name or one.which,
                    into="listing records", rows_in_file=said.rows_in_file,
                    rows_read=said.rows_in_file - len(said.not_read),
                ))
            continue
        try:
            body = bring_it_back(one.which)
            reading, refused_rows = a_reading(how, one, body)
            # **THE ONE PLACE A SALE LANDS.** Everything above this line can be
            # done again tomorrow at no cost; everything below depends on this
            # having happened.
            record_the_sales([reading])
        except LedgerRefused as wrong:
            # **OUR OWN FAULT, KEPT APART FROM THE PLATFORM'S.** See
            # `is_a_defect`: a night where our own rule refused every file must
            # not report green.
            the_ledger_refused.append(f"{one.name or one.which}: {wrong}")
            continue
        except Exception as wrong:  # noqa: BLE001 - named, never swallowed
            could_not_read.append(f"{one.name or one.which}: {wrong}")
            continue
        # **MARKED ONLY NOW, AND ONE FILE AT A TIME.** Marked before the
        # recording, a run that died between the two would lose the file for
        # ever; marked in a batch at the end, a run that died halfway would lose
        # every file it had already written.
        read_tonight.append(one)
        how_many_sales += len(reading.sales)
        rows_refused += refused_rows
        the_day = landing.data_date_in(one.name)
        if the_day is not None:
            reads.append(manifest.Read(
                data_date=the_day, report_id=how.report_id, file_name=one.name or one.which,
                into="the sales ledger", rows_in_file=len(reading.sales) + refused_rows,
                rows_read=len(reading.sales),
            ))

    keep, let_go_of, refused_to_forget = _what_is_still_worth_remembering(
        remembered, listed, can_be_read, could_not_list,
    )

    return WhatTheNightRead(
        files_read=whats_new.now_read(keep, read_tonight),
        read_tonight=tuple(sorted(one.which for one in read_tonight)),
        new_files=new_files,
        empty_files=empty_files,
        already_read=already,
        sales=how_many_sales,
        rows_refused=rows_refused,
        let_go_of=let_go_of,
        could_not_read=tuple(could_not_read),
        the_ledger_refused=tuple(the_ledger_refused),
        the_database_refused=tuple(the_database_refused),
        could_not_list=tuple(could_not_list),
        refused_to_forget=refused_to_forget,
        reads=tuple(reads),
        listing_figures=listing_figures,
        views_waiting=views_waiting,
    )


def _which_day_it_is_about(pair: Tuple[HowToRead, whats_new.InTheFolder]):
    """The day one file is about, as something that can be sorted.

    **THE DAY COMES OUT OF THE NAME, exactly as `a_reading` takes it**, and out of
    the same one function -- two ways of reading a date off a file name is two
    answers waiting to disagree.

    **A FILE WITH NO DAY IN ITS NAME GOES LAST.** `a_reading` refuses it and the
    night names it, so where it sits changes nothing about what is written -- but
    left where the listing dropped it, it would sit between two files that CAN be
    dated, and a reader would have to work out that it does not matter. Drive's
    own id breaks a tie, so two files of one report and one day are handed over in
    the same order every time rather than in whatever order a listing came back.
    """
    how, one = pair
    when = landing.data_date_in(one.name)
    # **PAYMENTS AFTER ORDERS, WHATEVER DAY EACH IS ABOUT (job 36).** A payments file adds money to rows the orders files make, and
    # is written down as read when it has been applied. Taken in plain day order a catch-up night applies a settlement before the
    # orders it settles, every line finds no row, and the file is read for good with its money on nothing. The two kinds write
    # different columns under different markers, so putting every payments file after every orders file changes no figure.
    return (how.kind == "payments", when is None, when.isoformat() if when is not None else "", one.which)


def _oldest_first(
    listed: Dict[str, List[whats_new.InTheFolder]],
    can_be_read: Sequence[HowToRead],
    remembered: Sequence[str],
) -> List[Tuple[HowToRead, whats_new.InTheFolder]]:
    """Tonight's new files, all three folders' together, OLDEST FIRST.

    **THE ORDER DRIVE HAPPENED TO LIST A FOLDER IN DECIDED THE SELLER'S FIGURES,
    and this is where that stops.** `ledger.plan` sorts its readings oldest-first
    for exactly this reason and says so in its own words -- *"an order of fetching
    must never decide what a figure is"* -- but a sale lands one file at a time,
    which is what makes the marking above safe, so **`plan` is handed a list of
    one every time and its sort has nothing to sort.** The ordering therefore has
    to be settled here, before the handover, and not by the writing half seeing
    each file on its own.

    **HIS OWN CASE, and it is not hypothetical:** the fourth day's file fails, the
    fifth's lands and corrects a sale from one to nine, and the fourth arrives
    later still saying one. With both new in the one run, listed fourth-then-fifth
    the sheet ended at nine and listed fifth-then-fourth it ended at one -- the
    same night, the same files, the correction destroyed by a listing order
    nobody chose.

    **EVERY FOLDER'S FILES ARE SORTED AS ONE LIST, not each folder's on its own.**
    Three folders read one after another would put every Amazon file after every
    Meesho file whatever day each is about; a run catching up on a week would then
    apply a whole platform's week out of order against another's.

    **WHAT IT DOES NOT DECIDE, AND MUST NOT: two files of ONE report and ONE
    day.** Sorting cannot help there -- neither is older -- and D150 rule 3 says
    keep what is there and REPORT it, never a silent pick. That is settled in
    `ledger.plan`, over the memory `ledger_sheet.recording_into` makes for the
    night. All the sort does here is break the tie on Drive's id so the two files
    are handed over in the same order every time.

    **WHAT THIS DOES NOT FIX, AND WHAT NOW DOES: a file arriving on a LATER NIGHT
    than one it is older than.** Tonight's files can be sorted because tonight
    holds them all; last night's figures are already in the sheet, and this sort
    never sees them. **The ledger is 50 columns wide and four of them say which
    day's file last wrote each figure**, and reading one of those four back is
    what settles the case this sort cannot. **That is not this function's job and never was** -- it is
    `ledger.older_than_the_row`, which reads the row's own date marker back
    before anything is applied and leaves an older file's claim alone, saying so.
    Until 2026-09-08 nothing filled those markers, so the late fourth really did
    overwrite the fifth across two nights (D157's second half, left open as
    D180); the checks named for that case asserted the wrong answer on purpose
    and went red the day it was closed.
    """
    tonight: List[Tuple[HowToRead, whats_new.InTheFolder]] = []
    for how in can_be_read:
        if how.report_id not in listed:
            continue
        for one in whats_new.what_is_new(listed[how.report_id], remembered).new:
            tonight.append((how, one))
    return sorted(tonight, key=_which_day_it_is_about)


def _what_is_still_worth_remembering(
    remembered: Sequence[str],
    listed: Dict[str, List[whats_new.InTheFolder]],
    can_be_read: Sequence[HowToRead],
    could_not_list: Sequence[str],
) -> Tuple[Tuple[str, ...], Tuple[str, ...], str]:
    """Which ids stay in the record. **HIS CAP, over more than one folder.**

    **D161 WIDENED, and the widening is the whole of this function.**
    `whats_new.still_worth_remembering` refuses to let go of anything when its
    one listing comes back empty, because an empty listing is what a failed one
    looks like. With three folders that guard is not enough on its own: one
    folder failing while the other two answer leaves a union that looks perfectly
    healthy, and every id belonging to the failed folder reads as a file somebody
    tidied away. Each would then be read again and put its old figures back over
    the newer ones that had already corrected them -- silently, which is exactly
    the fault D161 was written against.

    So a single folder that could not be listed, or that came back with nothing
    in it while something is remembered, stops ALL forgetting. **Costing a night
    of remembering too much is nothing; forgetting too much is a re-read.**
    """
    held = tuple(sorted(set(remembered)))
    if could_not_list and held:
        return held, (), (
            f"{len(could_not_list)} of the {len(can_be_read)} folders could not be "
            "listed, and a folder nobody can see looks exactly like a folder "
            "somebody emptied."
        )

    empty_ones = [name for name, files in listed.items() if not files]
    if empty_ones and held:
        return held, (), (
            ", ".join(sorted(empty_ones))
            + " came back with no files in it at all, which is what a listing looks "
            "like when it failed."
        )

    everything: List[whats_new.InTheFolder] = []
    for files in listed.values():
        everything += files
    still = whats_new.still_worth_remembering(everything, held)
    return still.keep, still.forgotten, still.refused_to_forget
