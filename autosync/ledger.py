"""What to write into the seller's sales ledger, and what to leave alone.

**THIS IS WHERE D150 AND D152 LIVE.** It decides; `ledger_door.py` does. Nothing
here touches the network, so every rule below is checked with no Google, no
sheet and no internet.

**THE LEDGER EXISTS SO ONE ROW EXPLAINS ONE ORDER.** His words (D152): *"If
somebody only wants to understand about the orders they can use the Google
Sheet. They don't need to refer to the entire ERP."* Everything below is
answered against that.

---

**A ROW IS ONE LINE OF AN ORDER, NOT ONE ORDER (D152).** A sale is named
`platform::orderId::sku`, so an order of three SKUs is three rows. The reference
kept one row per ORDER, which smeared a return of one item across everything else
in that order. **Here the loss lands on the exact item that came back.**

---

**THE TWO RULES THAT DECIDE EVERY WRITE (D150):**

1. **EACH REPORT WRITES ONLY THE COLUMNS IT KNOWS ABOUT.** Orders knows the
   status; returns knows the return; payments knows the money. **They never
   write each other's columns.** The cost of getting this wrong is not
   hypothetical: a payments file landing three weeks after the sale would wipe a
   delivery date it knows nothing about, and nothing would say so.

2. **WHERE TWO REPORTS CLAIM THE SAME COLUMN, THE NEWEST FILE WINS -- and
   "newest" is the file's own DATA DATE**, the one `landing.py` puts in its name,
   **not when it was downloaded.** A payments file dated 28 August speaking about
   a 1 August order is a newer statement about that order, whenever it arrived.

3. **TWO FILES OF THE SAME DATE DISAGREEING: KEEP WHAT IS THERE AND REPORT IT.**
   Never a silent pick. A silent choice between two equally-current claims is a
   figure nobody can trace; a reported one is a question somebody can answer.

---

**RULE 3 NEEDS A MEMORY THAT OUTLIVES ONE CALL, AND FOR A WHILE IT DID NOT HAVE
ONE. That is the fault this file was repaired for.**

The rule is decided in `decided_on`: which file last claimed each column of each
sale, and on what day. Written as state inside `plan`, it started empty on every
call -- and **the job calls `plan` once per file**, because a sale lands one file
at a time and that is what makes marking a file read safe. So `before` was always
`None`, the tie could never be seen, and the two files that make a tie were never
in one call to be compared. **The seller's figure was decided silently by which
Drive id happened to sort higher, and no disagreement was ever reported.**
Measured through the real chain, not reasoned about.

**So the memory is now the RUN'S, not the call's.** `plan` takes
`WhatTheNightHasDecided` and writes into it; whoever runs the night makes ONE and
hands the same one to every file. **The handover did not change** -- one file at
a time, still -- and the rule now sees both halves of a tie because what the
first file decided is still there when the second arrives.

---

**THE LIMIT OF RULE 2, STATED RATHER THAN GLOSSED -- and it needs four columns
that do not exist.**

Recency is enforced **within one run**, exactly: the readings are sorted by data
date and applied oldest first, and what the run has already decided is carried
from file to file, so the newest genuinely wins whatever order the files were
fetched in.

**Across runs it cannot be.** The ledger's 49 columns hold no record of WHICH
FILE last wrote each value, so a run tomorrow cannot tell whether what is in a
cell came from a file older or newer than the one it is holding. Today that is
almost always harmless -- a new file is newer than what came before it, by
construction. **It is NOT harmless for a by-hand backfill (D110)**, where a
deliberately old file is fetched after newer ones have already written.

**Nothing here pretends otherwise.** A backfill's readings are applied like any
other, and the one thing that would fix it is D157's four date-marker columns --
`WHICH_FILE_LAST_WROTE` below. Until they exist, **writing to the seller's sheet
is refused rather than done badly**: see `what_the_sheet_cannot_yet_say`.

---

**NOTHING IS EVER REMOVED FROM THE LEDGER**, matching the ERP's own rule: a sale
that did not happen is a sale in a state that says so, and a row taken out of a
sheet moves every row under it, so every remembered row number becomes wrong.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

# **THE ONE READER OF 'IS THIS A DAY' IN THIS PACKAGE.** A second way of
# deciding it here would be a second answer waiting to disagree, and what it
# decides is whether an older file may put its figure over a newer one.
from orders import the_day_in
from sales import COLUMNS, FROM_FIELD, Sale, a_cell, name_for, the_row_for
from table import CannotRead

# The first row of the sheet is the column names, so a sale is on row 2 or later.
THE_HEADER_IS_ROW = 1

# **D157'S FOUR DATE-MARKER COLUMNS, NAMED HERE SO THAT THEIR ABSENCE CAN BE
# CHECKED RATHER THAN REMEMBERED.**
#
# Each one holds the data date of the newest file OF THAT KIND that has touched
# the row. With them, a run tomorrow can tell whether the file in its hand is
# older than what is already in the cell, and rule 2 holds across nights as well
# as within one. Without them it cannot, and a late file dated the 4th quietly
# puts its figure over a correction the 5th made -- **in the money, with nothing
# anywhere saying so.**
#
# **THE NAMES ARE THE ERP'S TO SET, AND THESE ARE THE NAMES THIS LOOKS FOR.**
# `sales.COLUMNS` is pinned to the ERP's committed column list, so the day the
# ERP adds these four, this side follows and the refusal below goes away by
# itself. If the ERP lands them under different names, this keeps refusing and
# says exactly what it was looking for -- which is the loud answer, and the one
# to want.
# **IN THE ERP'S OWN ORDER, WHICH IS THE ORDER THE COLUMNS ARE IN.** Nothing
# here reads them by position -- the refusal below asks only whether each name
# is PRESENT -- so this tuple could be in any order and still be correct.
# **IT IS IN THIS ONE BECAUSE IT IS PRINTED TO A PERSON.** `ledger_sheet` joins
# it straight into the nightly alarm that tells somebody which columns to add,
# and that sentence is copied. It said `paymentsOn` before `returnsOn` until
# 2026-09-06, and that order had already been copied out of this repository into
# an instruction once (A26R5 found it still being printed). A sheet is read by
# column POSITION: swapped, every returns date lands in the payments column.
# Read off `Kartaan-ERP` `fc82dc7:src/shared/data/sheet-store.js:219-222`.
WHICH_FILE_LAST_WROTE = ("ordersOn", "returnsOn", "paymentsOn", "claimsOn")


def what_the_sheet_cannot_yet_say(columns: Sequence[str] = COLUMNS) -> Tuple[str, ...]:
    """Which of D157's four date markers the ledger still has no column for.

    **EMPTY MEANS THE SHEET CAN BE WRITTEN TO SAFELY**, and that is the whole
    reason this is a function and not a sentence in a report: a sentence has to
    be remembered, and this is asked every night by the thing it stops.
    """
    return tuple(one for one in WHICH_FILE_LAST_WROTE if one not in tuple(columns))


class WhatTheNightHasDecided:
    """Which file last claimed each column of each sale, for THIS run.

    **IT BELONGS TO THE RUN, NOT TO ONE CALL, AND THAT IS THE WHOLE POINT.**
    Kept inside `plan`, it began empty every time -- and the job calls `plan` once
    per file, because a sale lands one file at a time and that is what makes
    marking a file read safe. Two files of one report and one date therefore never
    met, rule 3 never fired, and which figure the seller ended up with was decided
    by which Drive id happened to sort higher. **Nothing said a word about it.**

    So the caller makes ONE of these for the night and hands the same one to every
    file. The handover is unchanged; the memory is what crosses it.
    """

    def __init__(self):
        self._by: Dict[Tuple[str, str], Tuple[str, str]] = {}

    def what_decided(self, name: str, column: str) -> Optional[Tuple[str, str]]:
        """The day and the file that last claimed this column, or None."""
        return self._by.get((name, column))

    def now_decided(self, name: str, column: str, on: str, statement: str) -> None:
        self._by[(name, column)] = (on, statement)

    def __len__(self) -> int:
        return len(self._by)


class LedgerRefused(CannotRead):
    """The ledger will not be written to, and here is why.

    **THE SAME KIND AS A FILE THAT CANNOT BE READ**, so whatever is running the
    night catches one thing rather than two.
    """


@dataclass(frozen=True)
class Unreadable:
    """A row already in the sheet that cannot be understood.

    **`name` IS CARRIED RATHER THAN PARSED BACK OUT OF `why`.** The first version
    of this dug the sale's name out of the sentence with `why.split()[1]` and got
    the word "sale" -- so the rule that stops a doubled name being written to
    silently did nothing. Reading a fact back out of a message meant for a person
    is the shape this project keeps paying for.
    """

    row: int
    why: str
    name: str = ""


@dataclass(frozen=True)
class Disagreement:
    """Two equally-current statements about one column, neither picked.

    **KEPT AND REPORTED, NEVER RESOLVED (D150).** What is in the sheet stays.

    **AND BOTH FILES ARE NAMED, because the whole worth of reporting a tie is
    that somebody can go and answer it.** The two sides of a tie are the same
    report of the same day -- that is what makes it a tie -- so saying only
    `me_orders of 2026-09-05` says it twice and points at neither. `kept_from`
    and `also_from` are Drive's own ids, which is what a person opens.
    """

    name: str
    column: str
    kept: str
    also_said: str
    from_report: str
    on: str
    # Which file wrote what is standing, and which file disagrees with it. Left
    # empty by a caller that does not know, and then simply not said.
    kept_from: str = ""
    also_from: str = ""

    def __str__(self) -> str:
        said = (
            f"{self.name}: {self.column} says {self.kept!r} and {self.from_report} "
            f"of {self.on} says {self.also_said!r}. Both are as current as each "
            "other, so nothing was changed."
        )
        if self.kept_from and self.also_from:
            said += (
                f" The two files are {self.kept_from} (which is the one standing) "
                f"and {self.also_from}."
            )
        return said


@dataclass(frozen=True)
class Reading:
    """What one file said, and what it is entitled to say it about.

    `knows` is the ledger columns this report may write -- **rule 1, made
    impossible to forget rather than remembered.** A report cannot touch a column
    it does not name here, however much a sale carries.

    `on` is the FILE'S OWN DATA DATE, not when it was fetched.
    """

    report: str
    on: str
    knows: Tuple[str, ...]
    sales: Tuple[Sale, ...]
    # **WHICH FILE THIS CAME FROM, and it is not decoration.**
    #
    # Two files of the SAME report and the SAME data date are two separate
    # statements -- a day fetched again lands as a new file under the same name
    # (D110), and `whats_new` correctly calls it new. Told apart only by report
    # and date they looked like ONE statement, so the second silently overwrote
    # the first and D150's rule 3 never fired. Which of them won depended on the
    # order they happened to be handed over in: the exact thing rule 2 exists to
    # stop. Found by reviewing this file against D150.
    #
    # `whats_new.InTheFolder.which` is what goes here. Left empty, the report's
    # name stands in and two files of one report and one date are indistinguishable
    # again -- so the caller that has it should pass it.
    #
    # **AND CARRYING IT IS ONLY HALF THE RULE.** It tells two files apart; it does
    # not put them in front of each other. The job hands one file per call to
    # `plan`, so the other half is `so_far` -- the run's own memory of what has
    # been decided, which is what makes a tie visible at all.
    which: str = ""

    @property
    def one_statement(self) -> str:
        """What counts as ONE statement for rule 3: this file, not this report."""
        return self.which or self.report

    def __post_init__(self):
        if not self.report.strip():
            raise LedgerRefused("A reading has to say which report it came from.")
        if not self.on.strip():
            raise LedgerRefused(
                f"The reading from {self.report} does not say what day its file is "
                "for. Without that, which of two statements is newer cannot be "
                "decided, and the newest is supposed to win."
            )
        unknown = [c for c in self.knows if c not in COLUMNS]
        if unknown:
            raise LedgerRefused(
                f"{self.report} says it knows about "
                + ", ".join(repr(c) for c in sorted(unknown))
                + ", which is not a column of the ledger. It has: "
                + ", ".join(COLUMNS)
                + "."
            )
        if not self.knows:
            raise LedgerRefused(
                f"{self.report} names no columns it can write, so reading it would "
                "change nothing. That is a mistake, not a quiet no-op."
            )
        # **A DATE MARKER DECLARED AND NOT CARRIED IS REFUSED (D157).**
        #
        # **THIS IS THE FAULT THE FOUR COLUMNS THEMSELVES ALREADY WALKED INTO
        # ONCE.** They landed in the ERP's column list on 2026-09-06; every
        # refusal built on their NAMES lifted itself the same day; and nothing
        # anywhere put a date in one. So a declaration that nothing fills reads,
        # downstream and to any reviewer, exactly like the marker being handled
        # -- and every row written still could not say which day's file produced
        # it. **Naming a marker is now a promise this refuses to let be empty.**
        #
        # **ONE SALE IS ENOUGH TO REFUSE THE WHOLE READING.** A file of sixty
        # rows where one carries no marker leaves one row in the sheet that
        # nothing can later tell was written by an older file, sitting invisibly
        # among the fifty-nine that are right.
        #
        # **REFUSED HERE, WHERE THE READING IS BUILT, SO THE FILE IS NEVER
        # MARKED AS READ.** `read_what_is_new` catches this like any other file
        # it cannot read: it names the file, leaves it in the folder and opens it
        # again tomorrow. Nothing is lost.
        for marker in WHICH_FILE_LAST_WROTE:
            if marker not in self.knows:
                continue
            field = FROM_FIELD[marker]
            for one in self.sales or ():
                if a_cell(getattr(one, field, None)).strip() == "":
                    raise LedgerRefused(
                        f"{self.report} says it writes {marker!r}, and the sale "
                        f"{one.id} carries nothing in it. A row that cannot say "
                        "which day's file produced it is a row a file arriving "
                        "late puts its older figure over, in the money, with "
                        "nothing anywhere saying so -- which is the whole reason "
                        f"{marker!r} exists. Nothing in this file was read."
                    )


@dataclass(frozen=True)
class OlderThanTheRow:
    """A file older than the one that last wrote this sale. Left alone, and said.

    **THIS IS WHAT D157'S FOUR COLUMNS WERE ASKED FOR, and until they were filled
    it could not exist.** Rule 2 says the newest file wins. Within one run that
    was enforced by sorting; across two nights the sheet held no record of WHICH
    day's file had written a cell, so a file for the 4th arriving after the 5th's
    correction was already in the sheet put its older figure straight back over
    it -- **in the money, with nothing anywhere saying so.**

    **IT IS REPORTED, NOT SWALLOWED.** A by-hand backfill (D110) is a deliberately
    old file fetched on purpose, and a night that quietly ignored it would look
    exactly like a night that applied it.
    """

    name: str
    report: str
    on: str
    marker: str
    the_row_says: str
    from_file: str = ""
    # **WHICH OF THE TWO REASONS IT WAS, and they are not the same event (A32).**
    #
    # One is rule 2 working: the row really was written by a newer file, nothing
    # is wrong, and there is nothing for anybody to do. The other is that the
    # cell holding the marker is not a date at all -- somebody typed over it --
    # so it was treated as newer because that is the safe direction, and **the
    # only way out is a person putting the cell back.**
    #
    # Said with one sentence between them in the run log, those two read as the
    # same line, and the one that needs a person looks like the one that does
    # not. Golden Rule 29.
    the_row_cannot_be_read: bool = False

    def __str__(self) -> str:
        if self.the_row_cannot_be_read:
            said = (
                f"{self.name}: the {self.marker} cell of this row holds "
                f"{self.the_row_says!r}, which is not a date. It decides whether an "
                "older file may put its figure back over a newer one, so it has "
                "been treated as newer and nothing was written. SOMEBODY HAS TO "
                "PUT THAT CELL BACK TO A DATE -- until they do, this row cannot "
                f"be written to. {self.report} is for {self.on}, and this file has "
                "NOT been written down as read, so it is opened again the night "
                "after the cell is corrected."
            )
        else:
            said = (
                f"{self.name}: {self.report} is for {self.on}, and this row was last "
                f"written by a {self.marker} file of {self.the_row_says}. The older "
                "file has not been applied, because the newer statement is the one "
                "that stands. Nothing is wrong and there is nothing to do."
            )
        if self.from_file:
            said += f" The older file is {self.from_file}."
        return said


@dataclass(frozen=True)
class Plan:
    """What the door should do, and what nobody could decide."""

    append: Tuple[Tuple[str, ...], ...] = ()
    update: Tuple[Tuple[int, Tuple[str, ...]], ...] = ()
    disagreements: Tuple[Disagreement, ...] = ()
    unreadable: Tuple[Unreadable, ...] = ()
    touched: Tuple[str, ...] = ()
    # **WHAT AN OLDER FILE WAS NOT ALLOWED TO UNDO.** Never a count on its own.
    left_alone: Tuple[OlderThanTheRow, ...] = ()

    def says(self) -> str:
        """One line for the run log. **Every count, even the noughts.**"""
        return (
            f"{len(self.append)} sales added, {len(self.update)} updated, "
            f"{len(self.disagreements)} disagreements reported, "
            f"{len(self.left_alone)} left alone as older than the row, "
            f"{len(self.unreadable)} rows in the sheet unreadable"
        )

    @property
    def changes_anything(self) -> bool:
        return bool(self.append or self.update)

    @property
    def somebody_has_to_put_a_cell_back(self) -> bool:
        """Was anything left alone because a marker cell is not a date? (A32)

        **THIS IS THE HALF OF `left_alone` THAT IS RECOVERABLE**, and it is only
        recoverable if the file is NOT written down as read -- otherwise the cell
        gets corrected and the file that was waiting on it is never opened again.
        `ledger_sheet.recording_into` reads this and refuses the file, which is
        the one path that leaves it unread.
        """
        return any(one.the_row_cannot_be_read for one in self.left_alone)


def what_the_sheet_holds(values: Sequence[Sequence[str]]):
    """The sheet's own rows, by the name each sale is written at.

    **THE HEADER IS CHECKED, AND A SHEET WHOSE COLUMNS HAVE MOVED IS REFUSED.**
    A sheet is a thing a person can open and drag a column about in -- the ERP
    already paid for this: *"A sheet whose columns somebody had dragged about
    read perfectly and wrote back scrambled."*

    **A ROW NOBODY CAN READ IS NAMED AND EVERY OTHER ROW IS STILL USED.** One
    hand-typed cell must not lose the ledger.
    """
    rows = [list(r) for r in (values or [])]
    if not rows:
        # An empty sheet is not a fault -- it is a first night. The door writes
        # the header before anything else.
        return {}, {}, ()

    header = [str(c).strip() for c in rows[0]]
    if tuple(header) != COLUMNS:
        missing = [c for c in COLUMNS if c not in header]
        extra = [c for c in header if c not in COLUMNS]
        raise LedgerRefused(
            "This sheet's columns are not the ledger's columns, so nothing has "
            "been written to it. "
            + (f"Missing: {', '.join(repr(c) for c in missing)}. " if missing else "")
            + (f"Not ours: {', '.join(repr(c) for c in extra)}. " if extra else "")
            + ("The order has changed. " if not missing and not extra else "")
            + "Put the first row back to exactly the ledger's columns, in order."
        )

    at = {name: n for n, name in enumerate(header)}
    held: Dict[str, Dict[str, str]] = {}
    row_of: Dict[str, int] = {}
    unreadable: List[Unreadable] = []

    for n, cells in enumerate(rows[1:], start=2):
        if not any(str(c).strip() for c in cells):
            continue
        said = {
            name: (str(cells[i]) if i < len(cells) else "")
            for name, i in at.items()
        }
        name = said.get("id", "").strip()
        if not name:
            unreadable.append(Unreadable(
                row=n,
                why="this row has no id, so there is no way to tell which sale it "
                    "is or to write to it again",
            ))
            continue
        if name in row_of:
            unreadable.append(Unreadable(
                row=n,
                name=name,
                why=f"the sale {name} is already on row {row_of[name]}. Two rows "
                    "for one sale cannot both be right, so neither is written to",
            ))
            continue
        held[name] = said
        row_of[name] = n

    # **A NAME ON TWO ROWS POISONS BOTH.** The first was kept above while the
    # second was reported; that would write to one of two rows a person can see,
    # which is the coin toss this project refuses. Neither is written to.
    doubled = {u.name for u in unreadable if u.name}
    for name in doubled:
        held.pop(name, None)
        row_of.pop(name, None)

    return held, row_of, tuple(unreadable)


def _what_a_sale_says(sale: Sale, knows: Sequence[str]) -> Dict[str, str]:
    """The cells one sale is entitled to write, and no others.

    **RULE 1 ENFORCED HERE, ONCE.** Every column outside `knows` is left out
    entirely -- not blanked, not copied. A column this report knows nothing about
    cannot be touched by it however the sale was built.
    """
    row = the_row_for(sale)
    by_column = dict(zip(COLUMNS, row))
    return {c: by_column[c] for c in knows if c in by_column}


def which_markers(knows: Sequence[str]) -> Tuple[str, ...]:
    """The date markers this report writes. **Its own kind of file, and no other.**

    An orders report speaks for `ordersOn` and says nothing about when a
    settlement was last stated -- so it is compared against its own marker only.
    Compared against all four, a payments file would be held back by an orders
    file dated later, which is rule 1 broken from the other side.
    """
    return tuple(one for one in WHICH_FILE_LAST_WROTE if one in tuple(knows or ()))


def older_than_the_row(
    row: Dict[str, str], reading: "Reading",
) -> Optional[Tuple[str, str, bool]]:
    """Is this file older than the one that last wrote this row? Which marker, when, and why.

    **THE THIRD THING IT ANSWERS IS WHICH OF THE TWO REASONS IT WAS (A32)**, and
    they need different things done: one is rule 2 working and asks nothing of
    anybody; the other is a cell somebody has typed over, and the only way out of
    it is a person putting that cell back.

    **THIS IS RULE 2 ACROSS TWO NIGHTS, and it is the whole reason D157 asked for
    the four columns.** Within one run the readings are sorted and the newest
    genuinely wins. Across runs the sheet was the only memory, and it held no
    record of WHICH day's file had written a cell -- so the fourth's file,
    arriving on a night after the fifth's correction was already written, put its
    old figure straight back over it and nobody was told.

    **STRICTLY OLDER. An equal date is NOT handled here**, deliberately: two files
    of one day disagreeing is D150's rule 3, it is decided over the run's own
    memory of which FILE said what, and the sheet records only the day. Answering
    a tie from a date alone would be inventing a distinction the sheet cannot
    make.

    **AND A ROW THAT SAYS NOTHING IS NOT OLD.** A blank marker is a row written
    before anything filled one; there is nothing to compare against, so the file
    is applied exactly as it always was.
    """
    for marker in which_markers(reading.knows):
        stood = str(row.get(marker, "") or "").strip()
        if not stood:
            continue
        if the_day_in(stood) != stood:
            # **A MARKER NOBODY CAN READ IS TREATED AS NEWER, NOT AS NOTHING.**
            # A sheet is a thing a person can open and type in, and this cell is
            # what decides whether an older file may overwrite a newer figure.
            # Compared as text, `"yesterday"` sorts after every real date and
            # `"1/9/26"` sorts before every one -- so half the wrong answers are
            # the silent overwrite this whole rule exists to stop.
            #
            # **LEFT ALONE AND REPORTED IS THE RECOVERABLE HALF OF THE MISTAKE --
            # AND UNTIL A32 IT WAS NOT ACTUALLY RECOVERABLE.** This line used to
            # end "because a file left alone is never written down as read",
            # which was simply false: `record_the_sales` returned normally and
            # `reading.read_what_is_new` marked the file read like any other, so
            # somebody could correct the cell and the file waiting on it would
            # never be opened again. **The `True` below is what makes the
            # sentence true**: it reaches `Plan.somebody_has_to_put_a_cell_back`,
            # `ledger_sheet.recording_into` refuses the file on it, and an
            # unread file is opened again the night after the cell is put back.
            return marker, stood, True
        if reading.on < stood:
            # Rule 2, working. Nothing is wrong and nobody has to do anything.
            return marker, stood, False
    return None


# Two days a run could never really be about, one plainly after the other. Used
# only to drive the question below.
AN_OLDER_DAY = "0001-01-01"
A_NEWER_DAY = "0001-01-02"


def would_an_older_file_be_stopped(knows: Sequence[str]) -> bool:
    """Would a file older than the row it is about actually be refused?

    **THIS IS THE QUESTION THE GUARD HAS TO ASK, AND TWO EARLIER VERSIONS OF IT
    ASKED SOMETHING WEAKER.**

    | Asked | What it really tested | Lifted while |
    |---|---|---|
    | are the four columns NAMED? | a name in a list | nothing filled one |
    | would a row CARRY a marker? | a name in `knows` | nothing read one back |
    | **would an older file be STOPPED?** | **the behaviour** | -- |

    The second of those was written to repair the first and reproduced its exact
    shape one level up: planting a marker on a made-up sale and asking whether it
    came back out reduces, for any working rule 1, to asking whether the name is
    in `knows`. **An independent reviewer proved it by taking the assignment out
    of `orders.py` and watching all 114 checks stay green.**

    **SO THIS DRIVES THE WHOLE THING.** It builds a sheet holding one sale
    already written by a NEWER file, hands `plan` a reading from an OLDER one
    claiming a different figure, and looks at what came out. Nothing is asserted
    about names anywhere in it. **If `plan` ever stops reading the marker back,
    this returns False and the night refuses -- which is what a guard is for.**

    **AND IT IS CHEAP AND COLD.** No sheet, no Drive, no account, no file: it is
    two dictionaries and one call, asked once a night before anything reaches
    Google.
    """
    markers = which_markers(knows)
    if not markers:
        return False
    # **EVERY MARKER THIS REPORT WRITES, NOT THE FIRST ONE (A32).** Asked of
    # `markers[0]` alone, a report that reads one marker back and ignores its
    # other three answered yes -- and the three it ignores are three ways an
    # older file still walks over a newer figure. It costs one call each.
    return all(_an_older_file_is_stopped_for(one, markers) for one in markers)


def _an_older_file_is_stopped_for(marker: str, markers: Tuple[str, ...]) -> bool:
    """The driving above, for one of the markers a report writes."""
    a_name = name_for("kartaan", "asking-whether-an-older-file-is-stopped")
    # The sheet as it would stand after a newer file had already written it.
    row = {one: "" for one in COLUMNS}
    row["id"] = a_name
    row["qty"] = "9"
    row[marker] = A_NEWER_DAY
    sheet = [list(COLUMNS), [row[one] for one in COLUMNS]]
    # The older file, saying something different about the same sale.
    older = Reading(
        report="asking",
        on=AN_OLDER_DAY,
        knows=tuple(dict.fromkeys(("qty", marker) + tuple(markers))),
        sales=(Sale(
            platform="kartaan",
            order_id="asking-whether-an-older-file-is-stopped",
            qty="1",
            **{FROM_FIELD[one]: AN_OLDER_DAY for one in markers},
        ),),
        which="the-older-file",
    )
    try:
        what = plan(sheet, [older])
    except LedgerRefused:
        # **A REFUSAL IS NOT AN ANSWER OF "YES".** Something is wrong with the
        # ledger itself, and the night must not write on the strength of it.
        return False
    if what.append or what.update:
        return False
    # **AND IT HAS TO SAY SO.** Stopped in silence, a by-hand backfill (D110)
    # looks exactly like a backfill that worked.
    return len(what.left_alone) == 1


# What the sheet itself is called when IT is the thing that remembers who wrote a
# figure. **It has to be a name no real file can have**, because rule 3 turns on
# the two sides being different files.
THE_SHEET_REMEMBERS = "a file read on an earlier night"


def _what_the_sheet_remembers(
    row: Optional[Dict[str, str]], reading: "Reading",
) -> Optional[Tuple[str, str]]:
    """Which day's file the sheet says last wrote this row, if it says.

    **THIS IS RULE 3 ACROSS TWO NIGHTS, AND IT DID NOT EXIST UNTIL A32.** Rule 3
    -- two equally current files claiming one column, keep what is there and SAY
    SO -- was decided entirely out of `WhatTheNightHasDecided`, the run's own
    memory. **A new night starts with that memory empty.** So a file of the 5th
    arriving on a night after another file of the 5th had already written the row
    met no tie at all: it simply overwrote, quantity 9 became quantity 1, and
    nothing was reported. Driven, exactly that: `left_alone` 0, `disagreements` 0.

    `older_than_the_row` is deliberately no help here -- it answers STRICTLY
    older, because the sheet records only the DAY and a tie is not an age. This
    answers the other half: the sheet's own marker IS a record of which day's
    file last wrote the row, and any file it did not write is a different file.

    **A FILE IS NEVER READ TWICE**, so a marker equal to the reading's own day is
    always some other file's -- which is what makes this a tie rather than a
    report meeting its own writing.
    """
    for marker in which_markers(reading.knows):
        stood = str((row or {}).get(marker, "") or "").strip()
        if stood and the_day_in(stood) == stood:
            return stood, THE_SHEET_REMEMBERS
    return None


def plan(
    values: Sequence[Sequence[str]],
    readings: Sequence[Reading],
    so_far: Optional[WhatTheNightHasDecided] = None,
) -> Plan:
    """What to add, what to change, and what nobody could decide.

    **THE READINGS ARE APPLIED OLDEST FIRST**, so the newest file's word is the
    one left standing (D150). Sorting here rather than asking the caller to is
    the point: an order of fetching must never decide what a figure is.

    **`so_far` IS THE RUN'S MEMORY, AND WITHOUT IT RULE 3 CANNOT FIRE.** The job
    hands one file at a time, so a call that starts with an empty memory has
    nothing to compare a second file's claim against -- the tie is invisible and
    the second file silently wins. Left out, this makes its own and the behaviour
    is the old one, which is right for a caller that really does hold every
    reading at once and wrong for the one that does not. **`ledger_sheet` makes
    one per night.**
    """
    held, row_of, unreadable = what_the_sheet_holds(values)

    # **SORTED BY THE FILE, NOT BY THE REPORT.** Keyed on the report, two files
    # of one report and one date tie -- and a stable sort then keeps whatever
    # order they were handed over in, so the order of FETCHING decided which
    # figure stood. That is precisely what rule 2 exists to stop. Found by the
    # check named for it, after the first half of this fix was already in.
    in_order = sorted(readings or (), key=lambda r: (r.on, r.one_statement))

    # What this run has decided so far, and which day's file decided it -- so a
    # same-day clash can be told from an ordinary overwrite by a newer file.
    # **HANDED IN, so that it survives the one-file-at-a-time handover.**
    now: Dict[str, Dict[str, str]] = {n: dict(v) for n, v in held.items()}
    decided_on = so_far if so_far is not None else WhatTheNightHasDecided()
    fresh: List[str] = []
    disagreements: List[Disagreement] = []
    left_alone: List[OlderThanTheRow] = []
    changed: Dict[str, bool] = {}

    # **A NAME THE SHEET HOLDS TWICE IS UNTOUCHABLE, both ways.**
    # It was taken out of `now` above so neither row is written to -- but that
    # alone made it look like a sale the sheet had never seen, so it was APPENDED
    # and the seller ended up with three rows for one sale. Found by the check
    # named for exactly that. It is reported, in `unreadable`, and left alone.
    poisoned = {u.name for u in unreadable if u.name}

    for reading in in_order:
        for sale in reading.sales:
            name = sale.id
            if name in poisoned:
                continue
            says = _what_a_sale_says(sale, reading.knows)

            # **RULE 2 ACROSS TWO NIGHTS, and this line is what D157'S FOUR
            # COLUMNS WERE ASKED FOR.** Asked of `now` rather than of the sheet
            # as it was read, so it holds within one call as well: a file for
            # the 4th handed over after the 5th is refused by what the 5th just
            # wrote, whatever order they came in. The sort above stops being the
            # only thing standing between a seller and a destroyed correction.
            if name in now:
                too_old = older_than_the_row(now[name], reading)
                if too_old is not None:
                    marker, stood, unreadable_cell = too_old
                    left_alone.append(OlderThanTheRow(
                        name=name, report=reading.report, on=reading.on,
                        marker=marker, the_row_says=stood,
                        from_file=reading.one_statement,
                        the_row_cannot_be_read=unreadable_cell,
                    ))
                    continue

            if name not in now:
                # **A NEW SALE STARTS AS EVERY COLUMN BLANK**, then takes what
                # this report knows. A blank means "nobody has worked this out
                # yet", which for a Flipkart sale's money is the truth.
                now[name] = {c: "" for c in COLUMNS}
                now[name]["id"] = name
                fresh.append(name)
                changed[name] = True

            for column, value in says.items():
                if column == "id":
                    continue
                was = now[name].get(column, "")

                # **SAYING NOTHING IS NOT SAYING "NOTHING". A blank never
                # overwrites something already there.**
                #
                # Rule 1 keeps a report out of columns it knows nothing about.
                # This is the same fault one level down: a payments file DOES
                # know about the settlement, but the row it holds for THIS sale
                # may carry no figure -- and writing that blank would wipe a real
                # settlement written last week, which is exactly the wiping rule
                # 1 exists to stop.
                #
                # A blank means "nobody has worked this out yet" everywhere else
                # in this package, and a platform file that omits a value is not
                # stating that the value is nothing.
                #
                # **Found by a check, not by reasoning: the check named for rule
                # 1 went red because the fix was not here.**
                if str(value) == "" and str(was) != "":
                    continue
                before = decided_on.what_decided(name, column)
                if before is None and str(was) != "":
                    # **AND WHEN THIS RUN REMEMBERS NOTHING, THE SHEET STILL
                    # MIGHT (A32).** Every night after the first starts with an
                    # empty memory, so without this rule 3 could only ever fire
                    # between two files of one night -- and the same tie across
                    # two nights was a silent overwrite in the money.
                    #
                    # **ONLY WHERE THE SHEET ACTUALLY HOLDS SOMETHING.** A blank
                    # cell is nobody's statement -- "nobody has worked this out
                    # yet" is what a blank means everywhere in this package -- so
                    # there is no tie to keep, and filling it in is the whole
                    # point of reading the file. Left out, a tie froze every
                    # blank column of the row as well.
                    before = _what_the_sheet_remembers(held.get(name), reading)
                if (before is not None and before[0] == reading.on
                        and before[1] != reading.one_statement):
                    if str(was) != str(value):
                        # **RULE 3. Nothing is overwritten on a tie.**
                        disagreements.append(Disagreement(
                            name=name, column=column, kept=str(was),
                            also_said=str(value), from_report=reading.report,
                            on=reading.on,
                            # **WHO SAID WHAT, out of the run's own memory.**
                            # `before` is the file that put the standing figure
                            # there; without it the report names one report twice
                            # and points at neither file.
                            kept_from=before[1], also_from=reading.one_statement,
                        ))
                    continue
                if str(was) != str(value):
                    now[name][column] = value
                    changed[name] = True
                decided_on.now_decided(name, column, reading.on, reading.one_statement)

    append: List[Tuple[str, ...]] = []
    update: List[Tuple[int, Tuple[str, ...]]] = []
    touched: List[str] = []

    for name in fresh:
        append.append(tuple(now[name].get(c, "") for c in COLUMNS))
        touched.append(name)

    for name, row in sorted(row_of.items(), key=lambda kv: kv[1]):
        if not changed.get(name):
            continue
        # **THE VERSION MOVES ON EVERY CHANGE**, or the ERP's guarded writes
        # compare one number for ever and refuse nothing.
        was = now[name].get("rev", "")
        try:
            now[name]["rev"] = a_cell(int(float(was or 0)) + 1)
        except (TypeError, ValueError):
            now[name]["rev"] = a_cell(1)
        update.append((row, tuple(now[name].get(c, "") for c in COLUMNS)))
        touched.append(name)

    return Plan(
        append=tuple(append),
        update=tuple(update),
        disagreements=tuple(disagreements),
        unreadable=unreadable,
        touched=tuple(touched),
        left_alone=tuple(left_alone),
    )
