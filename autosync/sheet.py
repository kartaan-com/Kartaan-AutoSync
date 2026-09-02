"""Reading a spreadsheet, with nothing installed. The other half of the floor.

**MOST OF HIS FILES ARE NOT TEXT, and that was in nobody's plan until 2026-09-02.**
Counted in his own Drive: **all 67 Flipkart order files are `.xlsx`**, and so is
every payments file -- 99 Meesho and 87 Flipkart. Only Meesho orders and Amazon
can be read as text. So without this file, Flipkart cannot be read at all.

**NOTHING IS INSTALLED TO DO IT.** This package takes nothing from outside the
standard library, and it does not need to: an `.xlsx` is a zip holding XML, so
`zipfile` and `xml.etree` are enough. That is not a clever trick, it is the file
format.

**IT HANDS BACK A `table.Table`, exactly what a text file hands back.** One shape,
so everything above this cannot tell whether a report arrived as a spreadsheet or
as text -- and the rules about refused rows, missing columns and never handing
back a number are written once, in `table.py`, rather than twice.

---

**SIX THINGS HIS REAL SPREADSHEETS DO THAT THE OBVIOUS CODE GETS WRONG.** Every
one measured on his own files, 2026-09-02.

1. **THE FIRST SHEET IS NOT THE DATA.** In his Flipkart orders file the sheets are
   `Help` then `Orders`. In his Flipkart payments file there are **SIXTEEN**, and
   the first is `Report Help`. **A reader that takes the first sheet reads a help
   page and reports that the seller had no orders** -- which is a lie the day
   board would show as a quiet, believable zero.

2. **THE PART FILENAMES DO NOT MATCH THE SHEET ORDER.** His payments file's FIRST
   sheet lives in `xl/worksheets/sheet17.xml`, and its `Orders` sheet lives in
   `sheet19.xml`. Sorting the parts by name, or trusting `sheet1.xml`, picks a
   sheet at random. **The only correct route is workbook.xml -> the sheet's
   relationship id -> the relationships file -> the part.** Anything shorter is
   a guess that happens to work on some files.

3. **`<dimension>` LIES.** Both of his files declare `ref="A1"` or `"A1:AM1"` --
   one row -- while holding 64 and 84. It is a hint a writer may leave stale, not
   a fact. **The rows are counted by reading them.**

4. **A ROW WITH NOTHING IN A COLUMN SIMPLY HAS NO CELL FOR IT.** Cells carry their
   own reference (`r="C2"`), and empty ones are left out entirely. **Read in
   order, every value after a gap shifts one column left** -- so a settlement
   figure lands in the tax column with nothing saying so. **Every cell is placed
   by its OWN reference, never by its position in the row.**

5. **TEXT ARRIVES TWO COMPLETELY DIFFERENT WAYS IN ONE FILE.** His Flipkart orders
   file writes its header row as shared strings (`t="s"`, the value being a
   NUMBER that indexes another part) and every data row as inline strings
   (`t="inlineStr"`). A reader that handles one and not the other gets a header of
   numbers, or 2,331 empty cells.

6. **A DATE IS A NUMBER.** Excel keeps `19 August 2026` as `46253`. Whether that
   number is a date is not in the cell -- it is in the cell's STYLE, which points
   into `styles.xml`. **Read without that, every date in the file becomes a
   five-digit number**; and his payments file really does carry a date format
   (`dd/mm/yyyy`). Date cells come back as `YYYY-MM-DD` text, and that conversion
   is about the FILE FORMAT, not about the money -- the money rules stay in one
   place (D119).

---

**AND ONE THING IT DOES NOT DO.** Header names are handed over with their edges
tidied but nothing else: his payments file has a column literally called
`" Payment Date"` with a leading space, and another whose name contains a real
newline. Tidying the edges is the difference between a name that can be looked up
and one that cannot. **Renaming them further is not this file's business** -- a
column called something odd is the platform's word, and whoever maps it says so
out loud in its own file.

**NOTHING HERE TOUCHES THE NETWORK OR A CLOCK**, so every rule in it is checked
with no account, no Drive and no internet.
"""

import re
import zipfile
from datetime import date, timedelta
from io import BytesIO
from typing import Dict, List, Optional, Sequence, Tuple
from xml.etree import ElementTree

from table import CannotRead, Row, Table, where_each_column_is

# The one namespace a spreadsheet's own parts live in, and the one the
# relationship ids live in. Written once so nothing can invent a near-miss.
MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RELS_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
RELS = "{http://schemas.openxmlformats.org/package/2006/relationships}"

WORKBOOK = "xl/workbook.xml"
WORKBOOK_RELS = "xl/_rels/workbook.xml.rels"
SHARED_STRINGS = "xl/sharedStrings.xml"
STYLES = "xl/styles.xml"

# **THE DAY EXCEL COUNTS FROM, and it is not the day Excel says it counts from.**
# It counts from 1 January 1900 being day 1, but it also believes 1900 was a leap
# year, which it was not. Counting from 30 December 1899 absorbs that error and
# is right for every date from 1 March 1900 onwards. Everything of his is 2026.
EXCEL_COUNTS_FROM = date(1899, 12, 30)

# **BELOW THIS, THE LEAP-YEAR ERROR IS NOT ABSORBED and the answer would be a day
# out.** A serial that low is not a date anybody meant -- it is 1900 -- so it is
# refused rather than quietly answered wrong.
LEAP_YEAR_LIE_ENDS = 61

# The date formats Excel has built in and does not write down anywhere. Read off
# the spreadsheet file format's own list of built-in number formats.
BUILT_IN_DATE_FORMATS = frozenset(
    list(range(14, 23)) + list(range(45, 48)) + [27, 30, 36, 50, 57]
)

# What makes a written-out format a date one. **The quote-stripping matters:** a
# money format like `"d"#,##0` holds a `d` inside quotes that means the letter,
# not a day.
IN_QUOTES = re.compile(r'"[^"]*"|\[[^\]]*\]')
LOOKS_LIKE_A_DATE = re.compile(r"[ymdhs]")

A_CELL_REFERENCE = re.compile(r"^([A-Z]+)")


class NotASpreadsheet(CannotRead):
    """This is not a spreadsheet, or not one that can be read.

    **THE SAME KIND AS A TEXT FILE'S REFUSAL**, so whatever is reading a report
    catches one thing rather than two -- and a spreadsheet that will not open is
    reported exactly like a text file that will not.
    """


def column_number(reference: str) -> int:
    """`A2` -> 0, `B2` -> 1, `AM7` -> 38. Which column a cell says it is in.

    **THIS IS WHAT STOPS A GAP SHIFTING A WHOLE ROW.** A row with nothing in
    column C has no cell for C at all, so reading cells in order puts D's value
    under C, E's under D, and every figure after the gap in the wrong column.
    """
    found = A_CELL_REFERENCE.match((reference or "").strip().upper())
    if not found:
        raise NotASpreadsheet(
            f"A cell in this spreadsheet says it is at {reference!r}, which is not "
            "a place in a spreadsheet, so nothing in its row can be trusted."
        )
    at = 0
    for letter in found.group(1):
        at = at * 26 + (ord(letter) - 64)
    return at - 1


def _all_the_text(node) -> str:
    """Every bit of text under a node, joined.

    **A CELL'S TEXT CAN BE IN SEVERAL PIECES.** One word in bold makes a value
    into runs -- `<r><t>Ready</t></r><r><t> to ship</t></r>` -- and reading only
    the first `<t>` gives `Ready`, which is a different answer that looks fine.
    """
    return "".join(t.text or "" for t in node.iter(f"{MAIN}t"))


def _shared_strings(book: zipfile.ZipFile) -> List[str]:
    """The strings a spreadsheet keeps in one place and points at by number.

    Missing entirely is not a fault: a file whose every value is written inline
    has no such part, and his Flipkart orders file nearly is one.
    """
    if SHARED_STRINGS not in book.namelist():
        return []
    root = _parse(book, SHARED_STRINGS)
    return [_all_the_text(si) for si in root.findall(f"{MAIN}si")]


def _which_styles_are_dates(book: zipfile.ZipFile) -> frozenset:
    """Which of a file's styles mean "this number is a date".

    A cell says `s="261"`, which is a place in `cellXfs`, which names a number
    format, which is either one of Excel's built-in ones or written out in the
    same file. **All three steps are needed**: stopping at any one of them reads
    a real date as a five-digit number.
    """
    if STYLES not in book.namelist():
        return frozenset()
    root = _parse(book, STYLES)

    written_out = set()
    for fmt in root.iter(f"{MAIN}numFmt"):
        code = fmt.get("formatCode") or ""
        naked = IN_QUOTES.sub("", code)
        if LOOKS_LIKE_A_DATE.search(naked.lower()):
            try:
                written_out.add(int(fmt.get("numFmtId")))
            except (TypeError, ValueError):
                continue

    dates = set()
    styles = root.find(f"{MAIN}cellXfs")
    if styles is None:
        return frozenset()
    for at, xf in enumerate(styles.findall(f"{MAIN}xf")):
        try:
            which = int(xf.get("numFmtId") or 0)
        except ValueError:
            continue
        if which in BUILT_IN_DATE_FORMATS or which in written_out:
            dates.add(at)
    return frozenset(dates)


def _a_date(serial: str) -> str:
    """A spreadsheet's number for a day, as `YYYY-MM-DD`.

    Anything that is not a number it could be is handed back untouched rather
    than lost: a cell wearing a date format but holding text is somebody's typing,
    and the row it is in still has thirty other columns worth reading.
    """
    try:
        number = float(serial)
    except (TypeError, ValueError):
        return serial
    whole = int(number)
    if whole < LEAP_YEAR_LIE_ENDS:
        return serial
    return (EXCEL_COUNTS_FROM + timedelta(days=whole)).isoformat()


def _parse(book: zipfile.ZipFile, part: str):
    try:
        return ElementTree.fromstring(book.read(part))
    except KeyError:
        raise NotASpreadsheet(
            f"This spreadsheet has no {part!r} inside it, so it cannot be read."
        ) from None
    except ElementTree.ParseError as wrong:
        raise NotASpreadsheet(
            f"The {part!r} inside this spreadsheet is damaged: {wrong}"
        ) from None


def _open(content) -> zipfile.ZipFile:
    if isinstance(content, zipfile.ZipFile):
        return content
    if isinstance(content, str):
        raise NotASpreadsheet(
            "A spreadsheet is bytes, not text. Handed text, it would be decoded "
            "before it was unzipped and every byte in it changed."
        )
    if not isinstance(content, (bytes, bytearray)):
        raise NotASpreadsheet(
            f"A spreadsheet is bytes, and this is {type(content).__name__}."
        )
    try:
        return zipfile.ZipFile(BytesIO(bytes(content)))
    except zipfile.BadZipFile:
        raise NotASpreadsheet(
            "This is not a spreadsheet. **The commonest reason by far is that the "
            "platform sent a sign-in page instead of a report**, which arrives as "
            "a file of the right name and the wrong thing entirely."
        ) from None


def sheets_in(content) -> Tuple[str, ...]:
    """What the sheets are called, in the order the spreadsheet lists them.

    **THE ORDER IS THE WORKBOOK'S, not the order of the parts inside the zip.**
    His payments file's first sheet is in `sheet17.xml`; sorting the parts by
    name would call `sheet10.xml` the second sheet and be wrong on every file
    with more than nine.
    """
    book = _open(content)
    root = _parse(book, WORKBOOK)
    return tuple(
        (s.get("name") or "").strip()
        for s in root.iter(f"{MAIN}sheet")
    )


def _where_that_sheet_lives(book: zipfile.ZipFile, wanted: Optional[str]) -> str:
    """The part holding that sheet, found the only way that is not a guess."""
    root = _parse(book, WORKBOOK)
    sheets = [
        ((s.get("name") or "").strip(), s.get(RELS_ID))
        for s in root.iter(f"{MAIN}sheet")
    ]
    if not sheets:
        raise NotASpreadsheet("This spreadsheet lists no sheets at all.")

    if wanted is None:
        name, rel = sheets[0]
    else:
        matching = [(n, r) for n, r in sheets if n == wanted]
        if not matching:
            raise NotASpreadsheet(
                f"This spreadsheet has no sheet called {wanted!r}. It has: "
                + ", ".join(repr(n) for n, _ in sheets)
                + "."
            )
        name, rel = matching[0]

    if not rel:
        raise NotASpreadsheet(
            f"The sheet {name!r} does not say which part of the file it is in."
        )

    rels = _parse(book, WORKBOOK_RELS)
    for one in rels.iter(f"{RELS}Relationship"):
        if one.get("Id") != rel:
            continue
        target = (one.get("Target") or "").lstrip("/")
        if target.startswith("xl/"):
            return target
        return "xl/" + target
    raise NotASpreadsheet(
        f"The sheet {name!r} points at {rel!r}, which this spreadsheet does not have."
    )


def _rows_of(part_xml, strings: Sequence[str], date_styles: frozenset) -> List[List[str]]:
    """Every row, every cell placed by its own reference.

    Rows are placed by their own number too, for the same reason cells are: a
    spreadsheet may leave an empty row out, and counting them as they come would
    silently move every later row up one.
    """
    by_number: Dict[int, Dict[int, str]] = {}
    widest = 0
    for row in part_xml.iter(f"{MAIN}row"):
        try:
            number = int(row.get("r") or 0)
        except ValueError:
            number = 0
        if number <= 0:
            number = (max(by_number) + 1) if by_number else 1
        cells: Dict[int, str] = {}
        for cell in row.findall(f"{MAIN}c"):
            reference = cell.get("r")
            at = column_number(reference) if reference else (max(cells) + 1 if cells else 0)
            cells[at] = _what_a_cell_says(cell, strings, date_styles)
            widest = max(widest, at + 1)
        by_number[number] = cells

    out: List[List[str]] = []
    for number in sorted(by_number):
        cells = by_number[number]
        out.append([cells.get(at, "") for at in range(widest)])
    return out


def _what_a_cell_says(cell, strings: Sequence[str], date_styles: frozenset) -> str:
    """One cell, as the text a person would see in it.

    **EVERYTHING COMES BACK AS TEXT**, exactly as `table.py` does, so a nought is
    the text `0` and never `None`, and no figure is turned into a number by
    anything that does not know what that column means (D119).
    """
    kind = cell.get("t")

    if kind == "inlineStr":
        holder = cell.find(f"{MAIN}is")
        return _all_the_text(holder) if holder is not None else ""

    value = cell.find(f"{MAIN}v")
    said = (value.text or "") if value is not None else ""

    if kind == "s":
        try:
            return strings[int(said)]
        except (ValueError, IndexError):
            # **NAMED RATHER THAN BLANKED.** A pointer into the shared strings
            # that leads nowhere means the file is damaged, and a blank cell
            # would read as "this order had no SKU".
            raise NotASpreadsheet(
                f"A cell at {cell.get('r')!r} points at word number {said!r}, "
                f"which this spreadsheet does not have."
            )
    if kind == "b":
        return "true" if said == "1" else "false"
    if kind == "e":
        # A spreadsheet's own error, kept as the platform wrote it. Turned into a
        # blank it would read as a missing value rather than a broken one.
        return said
    if kind in ("str", "inlineStr", None) and value is None:
        return ""
    if kind is None:
        style = cell.get("s")
        try:
            if style is not None and int(style) in date_styles:
                return _a_date(said)
        except ValueError:
            pass
    return said


def read(
    content,
    *,
    sheet: Optional[str] = None,
    header_row: int = 1,
    expect: Optional[Sequence[str]] = None,
) -> Table:
    """Read one sheet of a spreadsheet into the same rows a text file gives.

    `sheet` is the sheet's NAME. **Left out, the first sheet is used and that is
    usually wrong** -- his Flipkart files put `Help` and `Report Help` first --
    so callers name it, and `sheets_in()` says what there is to name.

    `header_row` is which row the column names are on. **It is not always the
    first**: his Flipkart payments file puts category bands across row 1
    (`Payment Details`, `Marketplace Fees`) and the real column names on row 2.
    A reader that assumed row 1 would look up `Order ID` and be told there is no
    such column, on a file that has one.

    Rows above the header are not data and are not refusals -- they are somebody's
    title block, and reporting them as bad rows would put refusals on every clean
    file of that shape.
    """
    book = _open(content)
    part = _where_that_sheet_lives(book, sheet)
    strings = _shared_strings(book)
    date_styles = _which_styles_are_dates(book)
    rows = _rows_of(_parse(book, part), strings, date_styles)

    if header_row < 1:
        raise NotASpreadsheet("The header row is a row number, counting from one.")
    if len(rows) < header_row:
        raise NotASpreadsheet(
            f"This sheet has {len(rows)} rows, so there is no row {header_row} "
            "to take the column names from."
        )

    names = [n.strip() for n in rows[header_row - 1]]
    # **TRAILING EMPTY COLUMNS ARE DROPPED, and only trailing ones.** A sheet is
    # as wide as its widest row, so a header of thirty names beside a data row of
    # thirty-four cells leaves four nameless columns on the end. A gap in the
    # MIDDLE is left alone -- his payments file really has one, and dropping it
    # would move every column after it.
    while names and not names[-1]:
        names.pop()
    if not names:
        raise NotASpreadsheet(
            f"Row {header_row} of this sheet names no columns at all."
        )

    where, ambiguous = where_each_column_is(names)
    columns = tuple(names)

    if expect:
        doubled = [n for n in expect if n in ambiguous]
        if doubled:
            raise NotASpreadsheet(
                "This sheet has more than one column called "
                + ", ".join(repr(n) for n in doubled)
                + ", and the reading needs that column. Which one is meant cannot "
                "be decided, so nothing is read."
            )
        missing = [n for n in expect if n not in where]
        if missing:
            raise NotASpreadsheet(
                "This sheet does not have the column"
                + ("s " if len(missing) > 1 else " ")
                + ", ".join(repr(n) for n in missing)
                + ". It has: "
                + ", ".join(repr(n) for n in columns if n)
                + ". Nothing was read, because a column that has moved would put "
                "a blank where a figure should be."
            )

    kept: List[Row] = []
    width = len(columns)
    for at, cells in enumerate(rows[header_row:], start=header_row + 1):
        trimmed = list(cells[:width])
        if not any(c.strip() for c in trimmed):
            continue
        # **A SHORT ROW IS FILLED OUT, NOT REFUSED, and only here.** In a text
        # file a row of the wrong width means the separators went wrong and
        # nothing in it can be trusted. In a spreadsheet it means the last
        # columns were empty, which the format states by leaving them out. The
        # two look the same and are not, so they are treated differently on
        # purpose.
        trimmed += [""] * (width - len(trimmed))
        kept.append(
            Row(line=at, cells=tuple(trimmed), _where=where, _ambiguous=ambiguous)
        )

    return Table(
        columns=columns,
        rows=tuple(kept),
        refused=(),
        separator="\t",
        ambiguous=ambiguous,
    )
