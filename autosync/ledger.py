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

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from sales import COLUMNS, Sale, a_cell, the_row_for
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


@dataclass(frozen=True)
class Plan:
    """What the door should do, and what nobody could decide."""

    append: Tuple[Tuple[str, ...], ...] = ()
    update: Tuple[Tuple[int, Tuple[str, ...]], ...] = ()
    disagreements: Tuple[Disagreement, ...] = ()
    unreadable: Tuple[Unreadable, ...] = ()
    touched: Tuple[str, ...] = ()

    def says(self) -> str:
        """One line for the run log. **Every count, even the noughts.**"""
        return (
            f"{len(self.append)} sales added, {len(self.update)} updated, "
            f"{len(self.disagreements)} disagreements reported, "
            f"{len(self.unreadable)} rows in the sheet unreadable"
        )

    @property
    def changes_anything(self) -> bool:
        return bool(self.append or self.update)


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
    )
