"""Checks for reading an old-style `.xls` with nothing installed (plan job 41).

**EVERY FILE IN HERE IS BUILT HERE, from Microsoft's published description of the format**, by a small writer at the top of this file --
no value of his is in the repository. The reader was also compared, cell by cell, against an independent reader (`xlrd`) on his real
Flipkart listing file on 2026-10-05: 7,119 cells, none different. That comparison needs his file, so it is not a check.

Run: python autosync/xls_checks.py
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sheet  # noqa: E402
import table  # noqa: E402
import xls  # noqa: E402

ran = 0
failures = []
THREW = []


def answered(work):
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


def why_it_is_refused(work):
    try:
        work()
    except table.CannotRead as wrong:
        return str(wrong)
    return ""


def refused(work, kind=Exception):
    try:
        work()
    except kind:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


# ---------------------------------------------------------------- a writer for the format


def record(number, data=b""):
    return struct.pack("<HH", number, len(data)) + data


def unicode_string(text, wide=False):
    body = text.encode("utf-16-le" if wide else "latin-1")
    return struct.pack("<HB", len(text), 1 if wide else 0) + body


def sst_records(strings, room):
    """The shared-string table as an SST record and as many CONTINUEs as `room` forces, splitting inside a string's characters the way Excel does."""
    pieces = [bytearray(struct.pack("<II", len(strings), len(strings)))]
    for text in strings:
        wide = any(ord(c) > 255 for c in text)
        header = struct.pack("<HB", len(text), 1 if wide else 0)
        width = 2 if wide else 1
        if len(pieces[-1]) + len(header) + width > room:
            pieces.append(bytearray())
        pieces[-1] += header
        left = text
        while True:
            fit = (room - len(pieces[-1])) // width
            put, left = left[:fit], left[fit:]
            pieces[-1] += put.encode("utf-16-le" if wide else "latin-1")
            if not left:
                break
            pieces.append(bytearray(b"\x01" if wide else b"\x00"))
    out = record(0x00FC, bytes(pieces[0]))
    for more in pieces[1:]:
        out += record(0x003C, bytes(more))
    return out


def rk_of(whole):
    return struct.pack("<I", (whole << 2) | 2)


def a_workbook(sheets, room=8000):
    """`sheets` is {name: rows}; a cell is text, a whole number, a float, `("rk", n)`, `("f", text)`, `("formula", number)` or `("bool", b)`."""
    strings = []

    def at(text):
        if text not in strings:
            strings.append(text)
        return strings.index(text)

    bodies = []
    for rows in sheets.values():
        out = record(0x0809, struct.pack("<HHHHII", 0x0600, 0x0010, 0x1DBB, 0x07CC, 0, 6))
        for r, cells in enumerate(rows):
            for c, held in enumerate(cells):
                if held == "" or held is None:
                    continue
                if isinstance(held, str):
                    out += record(0x00FD, struct.pack("<HHHI", r, c, 0, at(held)))
                elif isinstance(held, tuple) and held[0] == "rk":
                    out += record(0x027E, struct.pack("<HHH", r, c, 0) + rk_of(held[1]))
                elif isinstance(held, tuple) and held[0] == "rk100":
                    out += record(0x027E, struct.pack("<HHH", r, c, 0) + struct.pack("<I", (held[1] << 2) | 3))
                elif isinstance(held, tuple) and held[0] == "mulrk":
                    out += record(0x00BD, struct.pack("<HH", r, c) + b"".join(struct.pack("<H", 0) + rk_of(n) for n in held[1])
                                  + struct.pack("<H", c + len(held[1]) - 1))
                elif isinstance(held, tuple) and held[0] == "error":
                    out += record(0x0205, struct.pack("<HHHBB", r, c, 0, 7, 1))
                elif isinstance(held, tuple) and held[0] == "f" and len(held) == 3:
                    out += record(0x0006, struct.pack("<HHH", r, c, 0) + bytes([0, 0, 0, 0, 0, 0, 0xFF, 0xFF]) + bytes(6))
                    out += record(0x04BC, bytes(10))
                    out += record(0x0207, unicode_string(held[1]))
                elif isinstance(held, tuple) and held[0] == "f":
                    out += record(0x0006, struct.pack("<HHH", r, c, 0) + bytes([0, 0, 0, 0, 0, 0, 0xFF, 0xFF]) + b"\x00" * 6)
                    out += record(0x0207, unicode_string(held[1], any(ord(x) > 255 for x in held[1])))
                elif isinstance(held, tuple) and held[0] == "formula":
                    out += record(0x0006, struct.pack("<HHHd", r, c, 0, held[1]) + b"\x00" * 6)
                elif isinstance(held, tuple) and held[0] == "bool":
                    out += record(0x0205, struct.pack("<HHHBB", r, c, 0, 1 if held[1] else 0, 0))
                else:
                    out += record(0x0203, struct.pack("<HHHd", r, c, 0, float(held)))
        out += record(0x000A)
        bodies.append(out)
    names = list(sheets)
    sst = sst_records(strings, room)
    head = record(0x0809, struct.pack("<HHHHII", 0x0600, 0x0005, 0x1DBB, 0x07CC, 0, 6))
    boundsheets_size = sum(4 + 6 + 2 + len(n) for n in names)
    first = len(head) + boundsheets_size + len(sst) + len(record(0x000A))
    out = head
    at_offset = first
    for name, body in zip(names, bodies):
        out += record(0x0085, struct.pack("<IBB", at_offset, 0, 0) + bytes([len(name), 0]) + name.encode("latin-1"))
        at_offset += len(body)
    out += sst + record(0x000A)
    return out + b"".join(bodies)


def a_directory_entry(text, kind, start, size, child=0xFFFFFFFF):
    return (
        text.encode("utf-16-le").ljust(64, bytes(1)) + struct.pack("<HBB", len(text) * 2 + 2, kind, 1)
        + struct.pack("<III", 0xFFFFFFFF, 0xFFFFFFFF, child) + bytes(16) + bytes(4) + bytes(16)
        + struct.pack("<IQ", start, size)
    )


def an_old_spreadsheet(workbook, mini=False):
    """The workbook's bytes inside the container Excel 97 put them in. `mini` keeps a small stream in the mini stream, as the format says to."""
    end, free, fat_sector_mark = 0xFFFFFFFE, 0xFFFFFFFF, 0xFFFFFFFD
    if mini:
        assert len(workbook) < 4096
        small = [workbook[n: n + 64].ljust(64, bytes(1)) for n in range(0, len(workbook), 64)]
        mini_fat = list(range(1, len(small))) + [end]
        mini_fat_sector = struct.pack("<128I", *(mini_fat + [free] * (128 - len(mini_fat))))
        container = b"".join(small)
        container_sectors = [container[n: n + 512].ljust(512, bytes(1)) for n in range(0, len(container), 512)]
        # sector 0 is the FAT, 1 the directory, 2 the mini FAT, 3 onwards the mini stream
        fat = [fat_sector_mark, end, end] + list(range(4, 3 + len(container_sectors))) + [end]
        sectors = [None, None, mini_fat_sector] + container_sectors
        entries = a_directory_entry("Root Entry", 5, 3, len(container), child=1) + a_directory_entry("Workbook", 2, 0, len(workbook))
        first_mini, n_mini = 2, 1
        first_directory = 1
    else:
        padded = workbook.ljust(max(4096, len(workbook)), bytes(1))
        big = [padded[n: n + 512].ljust(512, bytes(1)) for n in range(0, len(padded), 512)]
        wanted = 1
        while wanted * 128 < wanted + 1 + len(big):
            wanted += 1
        # sectors 0..wanted-1 are the FAT, then the directory, then the workbook
        first_directory = wanted
        fat = [fat_sector_mark] * wanted + [end] + list(range(first_directory + 2, first_directory + 1 + len(big))) + [end]
        sectors = [None] * wanted + [None] + big
        entries = (a_directory_entry("Root Entry", 5, end, 0, child=1)
                   + a_directory_entry("Workbook", 2, first_directory + 1, len(padded)))
        first_mini, n_mini = end, 0
    fat_sectors = len(sectors) and (wanted if not mini else 1)
    padded_fat = fat + [free] * (128 * fat_sectors - len(fat))
    for n in range(fat_sectors):
        sectors[n] = struct.pack("<128I", *padded_fat[n * 128:(n + 1) * 128])
    sectors[first_directory if not mini else 1] = entries.ljust(512, bytes(1))
    header = (
        bytes.fromhex("d0cf11e0a1b11ae1") + bytes(16) + struct.pack("<HHHHH", 0x3E, 3, 0xFFFE, 9, 6) + bytes(6)
        + struct.pack("<IIIIIIIII", 0, fat_sectors, first_directory, 0, 4096, first_mini, n_mini, end, 0)
        + struct.pack("<109I", *(list(range(fat_sectors)) + [free] * (109 - fat_sectors)))
    )
    assert len(header) == 512
    return header + b"".join(sectors)


# ---------------------------------------------------------------- the checks


def the_checks():
    global ran

    ROWS = [
        ["Sku", "Stock", "Price", "Note"],
        ["A-1", 100, 399.5, "plain"],
        ["B (2)", ("rk", 7), ("formula", 12.25), ("f", "from a formula")],
        ["C–3", ("bool", True), "", "very " * 6 + "long"],
    ]
    BOOK = a_workbook({"Data": ROWS, "Other": [["x"], ["y"]]})

    old = an_old_spreadsheet(BOOK)
    check("the sheets are named in the order the book holds them", answered(lambda: xls.sheets_in(old)) == ("Data", "Other"))
    got = answered(lambda: xls.rows_in(old, "Data"))
    check("text, whole numbers, decimals, packed numbers and formula results all read",
          got == [["Sku", "Stock", "Price", "Note"], ["A-1", "100", "399.5", "plain"], ["B (2)", "7", "12.25", "from a formula"],
                  ["C–3", "TRUE", "", "very very very very very very long"]])

    small = an_old_spreadsheet(a_workbook({"Data": [["Sku"], ["A-1"]]}), mini=True)
    check("a small book, which lives in the container's mini stream, reads", answered(lambda: xls.rows_in(small, "Data")) == [["Sku"], ["A-1"]])

    room = a_workbook({"Data": [["Sku", "Name"], ["A-1", "Pearl – Jhumka " * 3], ["A-2", "Ünï " * 20], ["A-3", "ascii " * 30]]}, room=40)
    split = answered(lambda: xls.rows_in(an_old_spreadsheet(room), "Data"))
    check("shared text split across continuation records comes out whole, in one byte and in two bytes a character",
          split == [["Sku", "Name"], ["A-1", "Pearl – Jhumka " * 3], ["A-2", "Ünï " * 20], ["A-3", "ascii " * 30]])

    as_a_table = answered(lambda: xls.read(an_old_spreadsheet(BOOK), sheet="Data", header_row=1))
    check("read hands back the same table an .xlsx gives, columns by name",
          as_a_table is not None and isinstance(as_a_table, table.Table) and as_a_table.columns == ("Sku", "Stock", "Price", "Note")
          and [row["Sku"] for row in as_a_table] == ["A-1", "B (2)", "C–3"])
    check("and the rule for a column the reader needs is the one `sheet.read` has",
          refused(lambda: xls.read(an_old_spreadsheet(BOOK), sheet="Data", expect=("Colour",)), table.CannotRead))
    try:
        xls.rows_in(an_old_spreadsheet(BOOK), "Nope")
        check("a sheet that is not there is refused, naming the ones that are", False)
    except table.CannotRead as wrong:
        check("a sheet that is not there is refused, naming the ones that are", "'Data'" in str(wrong) and "'Other'" in str(wrong))

    check("bytes that are not an old spreadsheet are refused in words, not read as empty",
          refused(lambda: xls.sheets_in(b"just some text, not a spreadsheet at all" * 20), table.CannotRead))
    check("a file cut short is refused", refused(lambda: xls.rows_in(an_old_spreadsheet(BOOK)[:700], "Data"), table.CannotRead))
    check("an Excel 5 book (before Excel 97) is refused with what to do",
          refused(lambda: xls.sheets_in(an_old_spreadsheet(BOOK.replace(struct.pack("<H", 0x0600), struct.pack("<H", 0x0500), 1))),
                  table.CannotRead))
    check("a password-protected book is refused",
          refused(lambda: xls.sheets_in(an_old_spreadsheet(BOOK[:4 + 16] + record(0x002F, b"\x00\x00") + BOOK[4 + 16:])), table.CannotRead))
    check("and the refusal is the same kind a spreadsheet's is, so one catch serves both",
          issubclass(xls.NotASpreadsheet, table.CannotRead) and xls.NotASpreadsheet is sheet.NotASpreadsheet)

    # **A SHEET SPLIT FROM `sheet.read` MUST NOT HAVE CHANGED IT.** The header and column rules live in `table_from_rows`; an .xlsx still gets them.
    check("`sheet.table_from_rows` is what both readers end in",
          sheet.table_from_rows([["a", "b"], ["1", "2"]]).columns == ("a", "b") and len(sheet.table_from_rows([["a"], ["1"], ["2"]])) == 2)

    kinds = answered(lambda: xls.rows_in(an_old_spreadsheet(a_workbook({"D": [
        [("rk100", 12345), ("error",), ("bool", False), ("f", "kept", "between"), ("mulrk", [5, 6, 7])]]})), "D"))
    check("a packed number with the hundredths flag, a run of packed numbers, an error cell, a false, and a formula's text with another record "
          "between the formula and its text all read as they should",
          kinds == [["123.45", "", "FALSE", "kept", "5", "6", "7"]])
    many = [[f"row {n}", "x" * 40] for n in range(3000)]
    big = an_old_spreadsheet(a_workbook({"D": many}))
    check("a book of more than 64 KB, which needs a second FAT sector, reads in full",
          len(big) > 100_000 and answered(lambda: xls.rows_in(big, "D")) == many)
    check("a cell past the 256th column is refused, not held",
          "outside the grid" in str(answered(lambda: why_it_is_refused(lambda: xls.rows_in(
              an_old_spreadsheet(a_workbook({"D": [[""] * 256 + ["x"]]})), "D"))) or ""))
    looping = bytearray(an_old_spreadsheet(BOOK))
    looping[0x44:0x4C] = struct.pack("<II", 5, 1_000_000)
    check("a container claiming a million index sectors is refused at once, not looped over",
          "damaged" in str(answered(lambda: why_it_is_refused(lambda: xls.rows_in(bytes(looping), "Data"))) or ""))
    # **A DAMAGED FILE IS REFUSED IN WORDS, NEVER A STACK TRACE.** Every one of 300 single-byte corruptions, spread along the book, either still reads
    # or is refused with the one kind of refusal a person can act on.
    import random
    chance = random.Random(2026)
    clean = an_old_spreadsheet(BOOK)
    odd = []
    for _ in range(300):
        broken = bytearray(clean)
        broken[chance.randrange(512, len(clean))] = chance.randrange(256)
        try:
            xls.read(bytes(broken), sheet="Data")
        except table.CannotRead:
            pass
        except Exception as wrong:  # noqa: BLE001
            odd.append(repr(wrong))
    check("300 corruptions of one byte each are read or refused, never anything else -- " + str(odd[:2]), not odd)
    far = a_workbook({"Data": [["Sku"]] + [[]] * 65_534 + [[""] * 255 + ["far away"]]})
    reached = answered(lambda: xls.rows_in(an_old_spreadsheet(far), "Data"))
    check("a cell on the last row and column the format has reads, without a grid of sixteen million places being held",
          reached is not None and len(reached) == 65_536 and reached[-1][255] == "far away" and sum(len(r) for r in reached) < 1_000)
    check("nothing above ended by throwing rather than by answering -- " + str(THREW), not THREW)
    EXPECTED = 21
    check(f"checks went missing -- {ran + 1} ran, {EXPECTED} expected", ran + 1 == EXPECTED)


if __name__ == "__main__":
    the_checks()
    if failures:
        print(f"\n{len(failures)} FAILED ({ran} checks)")
        sys.exit(1)
    print(f"\nall {ran} checks passed")
