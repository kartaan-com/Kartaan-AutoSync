"""Reading an old-style `.xls` spreadsheet, with nothing installed.

**HIS FLIPKART LISTING FILE IS ONE.** `flipkart_fk_listings_2026-10-02.xls` opens with the bytes `D0 CF 11 E0`, which is the
old binary Excel format and not the zip-of-XML an `.xlsx` is, so `sheet.py` cannot open it. Nothing in this package is
installed from outside, so this reads the format itself, from Microsoft's published description of it (`[MS-CFB]` for the
container, `[MS-XLS]` for the records).

**IT HANDS BACK THE SAME `table.Table` AS `sheet.read`**, through the same `sheet.table_from_rows`, so nothing above this can
tell which kind of file it was given.

**WHAT IT READS, AND WHAT IT REFUSES.** Text, numbers, booleans and formula results, in the Excel 97-2003 layout (BIFF8).
An older layout (Excel 5, BIFF5), an encrypted book or a book with no workbook stream is refused in words, never read as
empty. A number comes back as the shortest text that reads back as the same number, a whole number without a `.0`; dates are
not converted (a listing file has none that matter), so a date cell comes back as its serial number. A cell Excel marks as an error, or a number that
is not finite, comes back blank. A cell outside the 65,536-row by 256-column grid the format has is a damaged file and is refused.

**NOTHING HERE TOUCHES THE NETWORK OR A CLOCK.**
"""

import struct
from typing import Dict, List, Optional, Sequence, Tuple

import sheet as sheet_file
from table import Table

NotASpreadsheet = sheet_file.NotASpreadsheet

OLE_MAGIC = bytes.fromhex("d0cf11e0a1b11ae1")
END_OF_CHAIN = 0xFFFFFFFE
FREE = 0xFFFFFFFF

# Record numbers, from [MS-XLS].
BOF, EOF_, BOUNDSHEET, SST, CONTINUE = 0x0809, 0x000A, 0x0085, 0x00FC, 0x003C
LABELSST, LABEL, NUMBER, RK, MULRK = 0x00FD, 0x0204, 0x0203, 0x027E, 0x00BD
FORMULA, STRING, BOOLERR, FILEPASS = 0x0006, 0x0207, 0x0205, 0x002F
# Records Excel may put between a formula and the text it came to.
SHRFMLA, ARRAY, TABLE = 0x04BC, 0x0221, 0x0236
# The grid this format has: 65,536 rows and 256 columns. A cell outside it is a damaged file, and is refused before anything is held for it.
LAST_ROW, LAST_COLUMN = 65_535, 255
BIFF8 = 0x0600

def _refuse(why: str):
    raise NotASpreadsheet(why)


# ------------------------------------------------------------------ the container ([MS-CFB])


def _the_workbook_stream(raw: bytes) -> bytes:
    """The bytes of the `Workbook` stream inside an old Excel file's container."""
    if len(raw) < 512 or raw[:8] != OLE_MAGIC:
        _refuse("This is not an old-style Excel file (it does not start the way one does).")
    shift = struct.unpack_from("<H", raw, 0x1E)[0]
    mini_shift = struct.unpack_from("<H", raw, 0x20)[0]
    if shift not in (9, 12) or mini_shift != 6:
        _refuse("This Excel file's container is laid out in a way this cannot read.")
    size = 1 << shift
    mini_size = 1 << mini_shift
    n_fat, first_dir = struct.unpack_from("<I", raw, 0x2C)[0], struct.unpack_from("<I", raw, 0x30)[0]
    cutoff, first_mini = struct.unpack_from("<II", raw, 0x38)
    first_difat, n_difat = struct.unpack_from("<II", raw, 0x44)
    if n_difat > len(raw) // size:
        _refuse("This Excel file's container is damaged (it claims more index sectors than the file has). Download it again.")

    def sector(number: int) -> bytes:
        start = (number + 1) * size
        piece = raw[start: start + size]
        if len(piece) < size:
            _refuse("This Excel file is cut short, so it cannot be read.")
        return piece

    difat = list(struct.unpack_from("<109I", raw, 0x4C))
    at, left, visited = first_difat, n_difat, set()
    while left > 0 and at not in (END_OF_CHAIN, FREE):
        if at in visited:
            _refuse("This Excel file's container loops back on itself, so it cannot be read. Download it again.")
        visited.add(at)
        block = sector(at)
        entries = struct.unpack("<%dI" % (size // 4), block)
        difat.extend(entries[:-1])
        at = entries[-1]
        left -= 1
    fat: List[int] = []
    for number in difat[:n_fat]:
        if number in (FREE, END_OF_CHAIN):
            continue
        fat.extend(struct.unpack("<%dI" % (size // 4), sector(number)))

    def chain(start: int, table: Sequence[int]) -> List[int]:
        out, seen = [], set()
        while start not in (END_OF_CHAIN, FREE) and start < len(table):
            if start in seen:
                _refuse("This Excel file's container loops back on itself, so it cannot be read. Download it again.")
            seen.add(start)
            out.append(start)
            start = table[start]
        return out

    def big_stream(start: int) -> bytes:
        return b"".join(sector(n) for n in chain(start, fat))

    directory = big_stream(first_dir)
    entries = []
    for at in range(0, len(directory) - 127, 128):
        entry = directory[at: at + 128]
        length = struct.unpack_from("<H", entry, 0x40)[0]
        name = entry[: max(length - 2, 0)].decode("utf-16-le", "replace")
        kind = entry[0x42]
        first = struct.unpack_from("<I", entry, 0x74)[0]
        length_of_stream = struct.unpack_from("<Q", entry, 0x78)[0] & 0xFFFFFFFF
        entries.append((name, kind, first, length_of_stream))
    root = next((e for e in entries if e[1] == 5), None)
    wanted = next((e for e in entries if e[1] == 2 and e[0] in ("Workbook", "Book")), None)
    if wanted is None:
        _refuse("This Excel file has no workbook inside it.")
    _, _, first, length = wanted
    if length >= cutoff:
        return big_stream(first)[:length]
    # A small stream lives in the mini stream, which is itself a stream held by the root entry.
    if root is None:
        _refuse("This Excel file has no root, so its small parts cannot be found.")
    mini_stream = big_stream(root[2])
    mini_fat: List[int] = []
    for number in chain(first_mini, fat):
        mini_fat.extend(struct.unpack("<%dI" % (size // 4), sector(number)))
    pieces = [mini_stream[n * mini_size: (n + 1) * mini_size] for n in chain(first, mini_fat)]
    return b"".join(pieces)[:length]


# ------------------------------------------------------------------ the records ([MS-XLS])


def _records(book: bytes):
    at = 0
    while at + 4 <= len(book):
        number, length = struct.unpack_from("<HH", book, at)
        yield number, book[at + 4: at + 4 + length]
        at += 4 + length


def _number_text(value: float) -> str:
    if value != value or value in (float("inf"), float("-inf")):
        return ""
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return repr(value)


def _rk(raw: int) -> float:
    if raw & 2:
        value = float(struct.unpack("<i", struct.pack("<I", raw & 0xFFFFFFFC))[0] >> 2)
    else:
        value = struct.unpack("<d", struct.pack("<Q", (raw & 0xFFFFFFFC) << 32))[0]
    return value / 100 if raw & 1 else value


class _Pieces:
    """The shared-string table's bytes in the pieces Excel split them into.

    **A STRING CAN RUN ACROSS A `CONTINUE` RECORD**, and when it does the new piece opens with one byte saying whether the
    rest of it is two bytes a character or one. That byte is not part of the text, so reading the pieces as one run of bytes
    would put it in the middle of a word.
    """

    def __init__(self, pieces: Sequence[bytes]):
        self.pieces = list(pieces)
        self.at = 0
        self.inside = 0

    def _left(self) -> int:
        return len(self.pieces[self.at]) - self.inside

    def _next_piece(self):
        self.at += 1
        self.inside = 0
        if self.at >= len(self.pieces):
            _refuse("The shared text in this Excel file is cut short, so it cannot be read.")

    def take(self, n: int) -> bytes:
        out = b""
        while n > 0:
            if self._left() == 0:
                self._next_piece()
            part = self.pieces[self.at][self.inside: self.inside + n]
            self.inside += len(part)
            n -= len(part)
            out += part
        return out

    def characters(self, count: int, wide: bool) -> str:
        text = ""
        while count > 0:
            if self._left() == 0:
                self._next_piece()
                wide = bool(self.pieces[self.at][0] & 1)
                self.inside = 1
            width = 2 if wide else 1
            fit = min(count, self._left() // width)
            if fit == 0:
                _refuse("The shared text in this Excel file is cut short, so it cannot be read.")
            chunk = self.take(fit * width)
            text += chunk.decode("utf-16-le" if wide else "latin-1")
            count -= fit
        return text


def _shared_strings(pieces: Sequence[bytes]) -> List[str]:
    if not pieces:
        return []
    reader = _Pieces(pieces)
    reader.take(4)
    (unique,) = struct.unpack("<I", reader.take(4))
    out: List[str] = []
    for _ in range(unique):
        try:
            count, flags = struct.unpack("<HB", reader.take(3))
        except NotASpreadsheet:
            break
        runs = struct.unpack("<H", reader.take(2))[0] if flags & 8 else 0
        extra = struct.unpack("<I", reader.take(4))[0] if flags & 4 else 0
        out.append(reader.characters(count, bool(flags & 1)))
        reader.take(4 * runs + extra)
    return out


def _unicode_string(data: bytes, at: int) -> str:
    count, flags = struct.unpack_from("<HB", data, at)
    at += 3
    if flags & 8:
        at += 2
    if flags & 4:
        at += 4
    if flags & 1:
        return data[at: at + 2 * count].decode("utf-16-le", "replace")
    return data[at: at + count].decode("latin-1")


def _sheets_in(book: bytes):
    """Each sheet's name and where its records start, and the shared strings, in the order the book holds them."""
    names: List[Tuple[str, int]] = []
    strings_pieces: List[bytes] = []
    in_strings = False
    started = False
    for number, data in _records(book):
        if number == BOF and not started:
            started = True
            version = struct.unpack_from("<H", data, 0)[0]
            if version != BIFF8:
                _refuse("This is an older Excel file (before Excel 97), which this cannot read. Save it as .xlsx and send it again.")
            continue
        if number == FILEPASS:
            _refuse("This Excel file is password-protected, so it cannot be read.")
        if number == BOUNDSHEET:
            offset = struct.unpack_from("<I", data, 0)[0]
            kind = data[5]
            if kind == 0:  # a worksheet, not a chart or a macro sheet
                names.append((_unicode_string_short(data, 6), offset))
            in_strings = False
        elif number == SST:
            in_strings = True
            strings_pieces = [data]
        elif number == CONTINUE and in_strings:
            strings_pieces.append(data)
        elif number == EOF_:
            break
        else:
            in_strings = False
    return names, _shared_strings(strings_pieces)


def _unicode_string_short(data: bytes, at: int) -> str:
    """A sheet's name: one byte of length, one of flags, then the characters."""
    count, flags = data[at], data[at + 1]
    at += 2
    if flags & 1:
        return data[at: at + 2 * count].decode("utf-16-le", "replace")
    return data[at: at + count].decode("latin-1")


def _rows_of(book: bytes, start: int, strings: Sequence[str]) -> List[List[str]]:
    cells: Dict[Tuple[int, int], str] = {}

    def put(row: int, col: int, text: str) -> None:
        if row > LAST_ROW or col > LAST_COLUMN:
            _refuse("This Excel file has a cell outside the grid Excel allows, so it is damaged. Download it again.")
        cells[(row, col)] = text

    waiting_string: Optional[Tuple[int, int]] = None
    first = True
    for number, data in _records(book[start:]):
        if first:
            first = False
            if number != BOF:
                _refuse("A sheet in this Excel file does not start where the book says it does.")
            continue
        if number == EOF_:
            break
        if number == STRING and waiting_string is not None:
            put(*waiting_string, _unicode_string(data, 0))
            waiting_string = None
            continue
        if number not in (SHRFMLA, ARRAY, TABLE):
            waiting_string = None
        if number == LABELSST:
            row, col, _, index = struct.unpack_from("<HHHI", data, 0)
            if index >= len(strings):
                _refuse("A cell in this Excel file names text that is not in it, so the file cannot be trusted.")
            put(row, col, strings[index])
        elif number == LABEL:
            row, col = struct.unpack_from("<HH", data, 0)
            put(row, col, _unicode_string(data, 6))
        elif number == NUMBER:
            row, col = struct.unpack_from("<HH", data, 0)
            put(row, col, _number_text(struct.unpack_from("<d", data, 6)[0]))
        elif number == RK:
            row, col, _, raw = struct.unpack_from("<HHHI", data, 0)
            put(row, col, _number_text(_rk(raw)))
        elif number == MULRK:
            row, col_first = struct.unpack_from("<HH", data, 0)
            (col_last,) = struct.unpack_from("<H", data, len(data) - 2)
            for n, col in enumerate(range(col_first, col_last + 1)):
                (raw,) = struct.unpack_from("<I", data, 4 + 6 * n + 2)
                put(row, col, _number_text(_rk(raw)))
        elif number == BOOLERR:
            row, col = struct.unpack_from("<HH", data, 0)
            if data[7] == 0:
                put(row, col, "TRUE" if data[6] else "FALSE")
        elif number == FORMULA:
            row, col = struct.unpack_from("<HH", data, 0)
            if data[12:14] == b"\xff\xff":
                if data[6] == 0:
                    waiting_string = (row, col)
                elif data[6] == 1:
                    put(row, col, "TRUE" if data[8] else "FALSE")
            else:
                put(row, col, _number_text(struct.unpack_from("<d", data, 6)[0]))
    if not cells:
        return []
    # **EACH ROW IS AS WIDE AS ITS OWN LAST CELL, NOT AS WIDE AS THE SHEET.** The format allows 65,536 rows and 256 columns, and a grid of all of it
    # for one stray cell is sixteen million places. `table_from_rows` fills a short row out, as it does for an .xlsx.
    rows = max(r for r, _ in cells) + 1
    out = [[] for _ in range(rows)]
    for (row, col), text in sorted(cells.items()):
        out[row].extend([""] * (col + 1 - len(out[row])))
        out[row][col] = text
    return out


# ------------------------------------------------------------------ what callers use


def _damaged_is_refused(work):
    """Run a reading of the file, and turn the ways a damaged one fails into the one refusal a person can act on."""

    def wrapped(*args, **kwargs):
        try:
            return work(*args, **kwargs)
        except (struct.error, IndexError, UnicodeError):
            _refuse("This Excel file is damaged and cannot be read. Download it again.")

    wrapped.__doc__ = work.__doc__
    return wrapped


@_damaged_is_refused
def sheets_in(content: bytes) -> Tuple[str, ...]:
    """The names of the worksheets in the file, in the order the book holds them."""
    names, _ = _sheets_in(_the_workbook_stream(content))
    return tuple(name for name, _ in names)


@_damaged_is_refused
def rows_in(content: bytes, sheet_name: Optional[str] = None) -> List[List[str]]:
    """Every row of one sheet as text, columns placed by their own position. `sheet_name` left out is the first sheet."""
    book = _the_workbook_stream(content)
    names, strings = _sheets_in(book)
    if not names:
        _refuse("This Excel file has no worksheet in it.")
    if sheet_name is None:
        return _rows_of(book, names[0][1], strings)
    where = [offset for name, offset in names if name == sheet_name]
    if len(where) != 1:
        _refuse(f"This Excel file has no sheet called {sheet_name!r}. It has: " + ", ".join(repr(n) for n, _ in names) + ".")
    return _rows_of(book, where[0], strings)


def read(
    content: bytes,
    *,
    sheet: Optional[str] = None,
    header_row: int = 1,
    expect: Optional[Sequence[str]] = None,
) -> Table:
    """Read one sheet of an old-style `.xls` into the same rows `sheet.read` gives. `sheet` is the sheet's NAME."""
    return sheet_file.table_from_rows(rows_in(content, sheet), header_row, expect)
