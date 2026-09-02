"""Turning a platform's file into rows, honestly. The floor the reader stands on.

**EVERY MONEY RULE IN THE READER SITS ON TOP OF THIS FILE**, so a fault here is a
fault in every figure. It does one job: take the bytes a platform handed over and
say what rows are in them, or say why a row could not be read. It knows nothing
about sales, settlements, SKUs or money.

**IT WAS WRITTEN AGAINST HIS REAL FILES, not against a description of them** --
his 46 real Amazon orders, 7 real Amazon returns, 15 real settlement lines and a
real Meesho orders file, on 2026-09-02. Every rule below is a fault those files
actually have. Nothing here is defensive programming against something imagined.

---

**FOUR THINGS REAL FILES DO THAT THE OBVIOUS CODE GETS WRONG:**

1. **AMAZON ENDS EVERY LINE WITH CARRIAGE-RETURN CARRIAGE-RETURN NEWLINE.**
   Measured: 47 of them in a 46-order file. `str.splitlines()` treats the lone
   carriage return as a line break too, so it hands back **94 lines, 47 of them
   empty** -- a row count of 93 orders where there are 46. Splitting on the
   ordinary two-character ending instead leaves **a stray carriage return welded
   to the last column of every row**, so `is-prime` reads as `false` plus an
   invisible character and never equals `false`. That is how a column silently
   stops matching while the screen looks like it works.

2. **A FILE'S NAME DOES NOT SAY WHAT IS INSIDE IT.** All three Amazon files are
   named `.csv` and all three are TAB-separated. `landing.py` names a landed file
   from the extension in `reports.py`, so the name is ours, not the platform's.
   **What separates the columns is read out of the file itself, every time.**

3. **QUOTING IS NOT THE SAME ON BOTH.** Meesho's comma file quotes every field,
   because a product name has commas in it. Amazon's tab files contain **not one
   quote character** -- measured across all three. Reading a tab file as though
   quoted means a stray `"` in a product title starts a quoted field and swallows
   every tab after it, joining columns together silently. **So a tab file is read
   with quoting OFF, and a comma file with it on.**

4. **A ROW THAT DOES NOT FIT IS NAMED, NOT DROPPED AND NOT FATAL.** The reference
   read its files with `on_bad_lines='skip'`, which is the worst of both: the row
   is gone and nothing says so. **One bad row must never lose the file, and it
   must never go quiet either.**

---

**WHAT THIS FILE REFUSES TO DO, each for its own reason:**

- **It never hands back a number.** Everything is text, exactly as the platform
  wrote it. Turning `"0"` into `0` is a decision about a FIELD, and a field
  belongs to whatever knows what that field means (D119: the money rules are
  written once, and they are not written here).
- **It never guesses at a missing column.** Asked for a name that is not in the
  header it refuses, naming what it did find. A reader that answers "nothing" for
  a column that has moved would put a blank in the money.
- **It never accepts two columns with the same name.** Which one a lookup means
  would be a coin toss, and `find` answering a count rather than a guess is
  already how this package refuses ambiguity (D108).

**NOTHING HERE TOUCHES THE NETWORK, THE DISK OR A CLOCK.** It takes bytes or text
and answers. That is what lets every rule in it be checked with no account, no
Drive and no internet -- the same seam every door in this package is built on.
"""

import csv
import io
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

# **THE TWO THINGS A PLATFORM USES TO SEPARATE COLUMNS.** Written once so nothing
# can invent a near-miss of either. Semicolon is deliberately not here: no file of
# his uses one, and a separator nobody has seen is a guess.
TAB = "\t"
COMMA = ","

# **THE LINE ENDINGS, LONGEST FIRST, AND THE ORDER IS THE WHOLE POINT.** Replace
# the two-character ending first and Amazon's three-character one becomes a
# two-character one that then survives as a stray carriage return. Longest first,
# every time.
LINE_ENDINGS = ("\r\r\n", "\r\n", "\r")


class CannotRead(ValueError):
    """This file cannot be read at all, and here is which part of it.

    **ITS OWN KIND**, so "the platform sent something unreadable" is never
    mistaken for a fault in the reading. One is their problem, one is ours, and
    they need different things doing about them (D108).
    """


@dataclass(frozen=True)
class Refused:
    """One row that could not be read, kept by name rather than dropped.

    **`line` IS THE LINE NUMBER IN THE FILE, counting the header as line 1** --
    the number a person sees when they open it. A refusal that says "row 12"
    when the file's own numbering says 13 sends whoever is helping to the wrong
    place, which is the same fault as reporting the wrong error entirely.
    """

    line: int
    why: str
    said: Tuple[str, ...]

    def __str__(self) -> str:
        return f"line {self.line}: {self.why}"


@dataclass(frozen=True)
class Row:
    """One row, by column name.

    **IT CARRIES ITS OWN LINE NUMBER**, because everything downstream that
    refuses a value has to be able to say WHICH row it refused, and a row that
    cannot name itself makes that impossible.
    """

    line: int
    cells: Tuple[str, ...]
    _where: Dict[str, int]

    def __getitem__(self, column: str) -> str:
        """What this row says in that column.

        Refuses a column the file does not have, rather than answering blank.
        **A blank for a column that has MOVED is money quietly going missing**;
        a refusal is a Flipkart rename found the day it happens (D108).
        """
        try:
            at = self._where[column]
        except KeyError:
            raise CannotRead(
                f"There is no column called {column!r} in this file. "
                "It has: " + ", ".join(repr(n) for n in sorted(self._where)) + "."
            ) from None
        return self.cells[at] if at < len(self.cells) else ""

    def get(self, column: str, missing: str = "") -> str:
        """What this row says, or `missing` when the file has no such column.

        **FOR COLUMNS A PLATFORM GENUINELY MAY OR MAY NOT SEND**, and for nothing
        else. Reaching for this to make a refusal go away is how a moved column
        turns into a blank -- so every use of it is a decision somebody makes on
        purpose, in a diff that gets read.
        """
        at = self._where.get(column)
        if at is None:
            return missing
        return self.cells[at] if at < len(self.cells) else ""

    def has(self, column: str) -> bool:
        return column in self._where


@dataclass(frozen=True)
class Table:
    """What was in the file: its columns, its rows, and what would not read."""

    columns: Tuple[str, ...]
    rows: Tuple[Row, ...]
    refused: Tuple[Refused, ...] = ()
    separator: str = TAB

    def __len__(self) -> int:
        return len(self.rows)

    def __iter__(self) -> Iterator[Row]:
        return iter(self.rows)

    @property
    def separator_name(self) -> str:
        """What a person would call it, for saying out loud."""
        return "tab" if self.separator == TAB else "comma"

    def says(self) -> str:
        """One line saying what was read, for the run log.

        **THE REFUSED COUNT IS SAID EVEN WHEN IT IS NOUGHT.** A sentence that
        mentions refusals only when there are some makes a clean read and a read
        nobody checked look identical.
        """
        return (
            f"{len(self.rows)} rows read, {len(self.refused)} refused, "
            f"{len(self.columns)} columns, {self.separator_name}-separated"
        )


def as_text(content) -> str:
    """The file's bytes as text, with the mark some tools put at the front removed.

    **THE BYTE-ORDER MARK IS REAL AND IT IS IN HIS FILES**: `az_catalog_2026-06-30.csv`
    starts with one. Left in place it becomes part of the FIRST COLUMN'S NAME, so
    looking that column up by name fails while every other column works -- which
    reads as "Amazon renamed one column" and is not.

    Anything that cannot be decoded is replaced rather than fatal: a single bad
    character in a product name must not lose the file (D108).
    """
    if isinstance(content, str):
        return content.lstrip("﻿")
    if isinstance(content, (bytes, bytearray)):
        return bytes(content).decode("utf-8-sig", errors="replace")
    raise CannotRead(
        f"A file is bytes or text, and this is {type(content).__name__}."
    )


def one_line_endings(text: str) -> str:
    """Every line ending made the same, longest first.

    **THIS IS WHERE AMAZON'S THREE-CHARACTER LINE ENDING IS DEALT WITH**, once,
    at the front door -- rather than in every reader that ever opens a file.

    A carriage return sitting INSIDE a value becomes a newline here. That is a
    real change to the data and it is said out loud rather than hidden: no
    platform file of his has one, and a value that genuinely contained a line
    break is already indistinguishable from a row ending in a file this shape.
    """
    for ending in LINE_ENDINGS:
        text = text.replace(ending, "\n")
    return text


def what_separates(header_line: str) -> str:
    """Tab or comma, decided by the file, never by its name.

    **ASKED OF THE HEADER LINE ONLY, and that is deliberate.** Asked of the whole
    file, one product name holding a dozen commas can outvote the tabs that
    actually separate the columns. The header is the one line that is nothing but
    separators and column names.

    **A TIE GOES TO TAB**, because a file with neither is a one-column file and
    reading it as tab-separated hands back that one column intact. Read as
    comma-separated with quoting on, the same file would be reshaped by any quote
    character in it.
    """
    if header_line.count(COMMA) > header_line.count(TAB):
        return COMMA
    return TAB


def where_each_column_is(names: Sequence[str]) -> Dict[str, int]:
    """Column name to its place, refusing a header that cannot answer plainly.

    **TWO COLUMNS WITH ONE NAME IS REFUSED, NOT RESOLVED.** Which one a lookup
    means would be a coin toss, and a coin toss in the money is worse than a
    stop. This package already refuses ambiguity rather than picking: `find`
    answers a count so a wrong button cannot be pressed by accident (D108).

    **A HEADER WITH NO NAMES AT ALL IS REFUSED TOO.** An empty header reads every
    later row as having the wrong width, so a whole file would come back as
    nothing but refusals -- true, but useless, and it hides the real cause.
    """
    tidy = [n.strip() for n in names]
    real = [n for n in tidy if n]
    if not real:
        raise CannotRead("The first line of this file names no columns at all.")
    seen: Dict[str, int] = {}
    twice = []
    for at, name in enumerate(tidy):
        if not name:
            continue
        if name in seen:
            twice.append(name)
            continue
        seen[name] = at
    if twice:
        raise CannotRead(
            "This file has more than one column called "
            + ", ".join(repr(n) for n in sorted(set(twice)))
            + ". Which one is meant cannot be decided, so nothing is read."
        )
    return seen


def _split_into_rows(text: str, separator: str) -> List[List[str]]:
    """The rows, as lists of cells. Quoting on for comma, off for tab.

    **WHY QUOTING IS OFF FOR A TAB FILE, measured rather than assumed:** his three
    real Amazon files contain **not one quote character between them**. With
    quoting on, a single `"` appearing one day in a product title would start a
    quoted field and swallow every tab after it, joining columns together with
    nothing saying so. With it off, that quote stays an ordinary character.

    **AND WHY IT IS ON FOR A COMMA FILE:** Meesho's real orders file quotes every
    field, because its product names are full of commas. Read with quoting off,
    one product name would become a dozen columns.
    """
    handle = io.StringIO(text)
    if separator == TAB:
        reader = csv.reader(handle, delimiter=TAB, quoting=csv.QUOTE_NONE)
    else:
        reader = csv.reader(handle, delimiter=COMMA)
    try:
        return [list(r) for r in reader]
    except csv.Error as wrong:
        raise CannotRead(f"This file could not be split into rows: {wrong}") from None


def read(content, *, expect: Optional[Sequence[str]] = None) -> Table:
    """Read a platform's file into rows.

    `expect` names columns the caller cannot do its job without. **They are
    checked ONCE, here, against the header -- not per row.** Checked per row, a
    file whose columns have moved produces one identical complaint for every row
    in it, which buries the one fact that matters: the column moved.

    **A ROW OF THE WRONG WIDTH IS REFUSED BY NAME AND THE REST ARE READ.** That
    is the whole of "one bad cell must never lose the file": the row is kept, in
    `refused`, with its line number and what it said, so it can be reported and
    looked at -- and the other forty-five rows still become sales.

    **A COMPLETELY BLANK LINE IS NOT A REFUSAL.** Files end with a newline; a
    trailing empty line is not a fault and reporting it as one would put a
    refusal on every clean file this package ever reads.
    """
    text = one_line_endings(as_text(content))
    if not text.strip():
        raise CannotRead("This file is empty.")

    header_line = text.split("\n", 1)[0]
    separator = what_separates(header_line)

    rows = _split_into_rows(text, separator)
    if not rows:
        raise CannotRead("This file is empty.")

    names = [n.strip() for n in rows[0]]
    where = where_each_column_is(names)
    columns = tuple(names)

    if expect:
        missing = [n for n in expect if n not in where]
        if missing:
            raise CannotRead(
                "This file does not have the column"
                + ("s " if len(missing) > 1 else " ")
                + ", ".join(repr(n) for n in missing)
                + ". It has: "
                + ", ".join(repr(n) for n in columns if n)
                + ". Nothing was read, because a column that has moved would put "
                "a blank where a figure should be."
            )

    kept: List[Row] = []
    refused: List[Refused] = []
    width = len(columns)
    for at, cells in enumerate(rows[1:], start=2):
        if not any(c.strip() for c in cells):
            continue
        if len(cells) != width:
            refused.append(
                Refused(
                    line=at,
                    why=(
                        f"this row has {len(cells)} values where the columns say "
                        f"{width}, so which value belongs to which column cannot "
                        "be decided"
                    ),
                    said=tuple(cells),
                )
            )
            continue
        kept.append(Row(line=at, cells=tuple(cells), _where=where))

    return Table(
        columns=columns,
        rows=tuple(kept),
        refused=tuple(refused),
        separator=separator,
    )
