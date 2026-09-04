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

**WHAT CAN BE READ TODAY IS ORDERS, AND NOTHING ELSE. Named, never derived.**

`orders.py` is the only file that knows what a platform calls things, and it
knows it for orders files. Returns, payments and claims have no mapping
anywhere, so their files are **not listed, not read and not marked** -- because
an id in the record for a file nothing has actually read is a file the reader
written next month would never see.

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

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import landing
import orders
import sheet
import table
import whats_new
from ledger import Reading
from reports import report as the_report

# **WHAT AN ORDERS REPORT IS ENTITLED TO WRITE (D150 rule 1).** It knows nothing
# about settlements, returns or charges, and naming the columns here is what
# makes that impossible to forget rather than merely remembered.
#
# **`id` IS NOT AMONG THEM ON PURPOSE.** A sale's name is what a row IS, not
# something a report states about it, and `ledger.plan` writes it itself when it
# first sees a sale.
WHAT_ORDERS_KNOWS = ("platform", "orderId", "on", "sku", "qty", "gmv")


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


WHAT_CAN_BE_READ: Tuple[HowToRead, ...] = (
    HowToRead("me_orders", WHAT_ORDERS_KNOWS),
    HowToRead(
        "fk_orders",
        WHAT_ORDERS_KNOWS,
        which_sheet=orders.WHERE_FLIPKART_ORDERS_ARE,
        header_row=orders.FLIPKART_HEADER_ROW,
    ),
    HowToRead("az_orders", WHAT_ORDERS_KNOWS),
)


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
    # Why a folder could not be listed, by name. This one is our own defect: with
    # a folder unknown, what is new cannot be worked out at all.
    could_not_list: Tuple[str, ...] = ()
    # Why nothing was let go of when something otherwise would have been.
    refused_to_forget: str = ""
    # Why nothing was read at all, when that was the answer. Empty when reading
    # did happen.
    nowhere_to_put_it: str = ""

    @property
    def is_a_defect(self) -> bool:
        """**A FOLDER THAT COULD NOT BE LISTED IS OURS (D108).** What is new
        cannot be decided without it, so the night's reading is not to be
        trusted. A single file that would not read is the platform's, and is
        named, counted and left green."""
        return bool(self.could_not_list)

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
                f"{self.empty_files} arrived empty, {self.already_read} already read, "
                f"{len(self.let_go_of)} id(s) let go of."
            )
        if self.refused_to_forget:
            said += f"  Nothing was let go of: {self.refused_to_forget}"
        for why in self.could_not_list:
            said += f"  A folder could not be listed: {why}"
        for why in self.could_not_read:
            said += f"  {why}"
        return said


def what_this_can_read(can_be_read: Sequence[HowToRead] = WHAT_CAN_BE_READ) -> Tuple[str, ...]:
    """The report ids this job can turn into sales.

    Asked here rather than worked out by whoever wants it, for the same reason
    `reports.on_the_api_door` exists beside its twin: each caller filtering the
    list itself is a second copy of one fact.
    """
    return tuple(one.report_id for one in can_be_read)


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
        return table.read(body, header_row=how.header_row)
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
    was = orders.read_orders(rows, which.platform)
    return (
        Reading(
            report=how.report_id,
            on=when.isoformat(),
            knows=how.knows,
            sales=was.sales,
            which=one.which,
        ),
        len(was.not_read),
    )


def read_what_is_new(
    already_read: Sequence[str],
    what_is_in_the_folder: Optional[Callable[[str], Sequence[whats_new.InTheFolder]]] = None,
    bring_it_back: Optional[Callable[[str], bytes]] = None,
    record_the_sales: Optional[Callable[[Sequence[Reading]], None]] = None,
    can_be_read: Sequence[HowToRead] = WHAT_CAN_BE_READ,
) -> WhatTheNightRead:
    """Read every file in the seller's folders that has not been read before.

    **THE ONLY TWO THINGS THAT DECIDE WHAT IS NEW ARE THE FOLDER AND THE LIST OF
    WHAT HAS BEEN READ.** Nothing about tonight's fetching reaches this -- not a
    run, not a log, not a report's state -- and that is structural rather than
    remembered: there is no argument here through which it could arrive. His
    rule, and the word is his: *"solely based on what is new."*

    **NOT HANDED A FOLDER, OR NOWHERE TO PUT A SALE, IS NOT A FAILURE.** It is
    where this stands until the seller's sales ledger exists, and it is said in
    words rather than as a night of noughts.
    """
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
    how_many_sales = 0
    rows_refused = 0

    # **OLDEST FIRST, AND EVERY FOLDER'S FILES TOGETHER.** Handed over in the
    # order Drive answered a listing in, the last file to be recorded is the last
    # one Drive happened to name -- and the last one recorded is the one whose
    # figures stand. See `_oldest_first`.
    for how, one in _oldest_first(listed, can_be_read, remembered):
        try:
            body = bring_it_back(one.which)
            reading, refused_rows = a_reading(how, one, body)
            # **THE ONE PLACE A SALE LANDS.** Everything above this line can be
            # done again tomorrow at no cost; everything below depends on this
            # having happened.
            record_the_sales([reading])
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
        could_not_list=tuple(could_not_list),
        refused_to_forget=refused_to_forget,
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
    _, one = pair
    when = landing.data_date_in(one.name)
    return (when is None, when.isoformat() if when is not None else "", one.which)


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

    **WHAT THIS DOES NOT FIX, and it is written here rather than left to be
    discovered: a file arriving on a LATER NIGHT than one it is older than.**
    Tonight's files can be sorted because tonight holds them all; last night's
    figures are in the sheet, and **no row in that sheet says which day's file
    wrote it** -- the ledger has 45 columns and not one of them is a date marker.
    So the late fourth still overwrites the fifth across two nights. D157's second
    half asked for four such columns and they were never built (D180). The check
    named for that case asserts today's wrong answer on purpose, so it goes red
    the day the columns land.
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
