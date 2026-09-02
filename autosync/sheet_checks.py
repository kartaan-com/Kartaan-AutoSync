"""Checks for reading a spreadsheet with nothing installed.

**EVERY FAULT CHECKED HERE IS ONE HIS REAL SPREADSHEETS ACTUALLY HAVE**, measured
2026-09-02 on his Flipkart orders file, his Flipkart payments file and his Meesho
payments file. Nothing here guards against something imagined.

**THE SPREADSHEETS THE CHECKS BUILD ARE BUILT BY HAND, out of zip and XML**, and
that is the point: a spreadsheet made by the same code that reads it would agree
with itself about anything. These are written the way the platforms write them --
including the parts they get wrong.

Run: python autosync/sheet_checks.py
"""

import os
import sys
import zipfile
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sheet as tool  # noqa: E402
import table  # noqa: E402

ran = 0
failures = []
not_run = []
THREW = []

HIS_FILES = Path(os.environ.get("RAW_DATA") or r"H:\My Drive\Rumee Raw Data")


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


def refused_by(work):
    """True when that raises `CannotRead`, and nothing else.

    **THE KIND IS CHECKED, not just that it threw**, or a typo in the code would
    make this green.
    """
    try:
        work()
    except table.CannotRead:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


def _catch(work):
    try:
        work()
    except Exception as e:  # noqa: BLE001
        return e
    return None


# --------------------------------------------------------- building one by hand

NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" ' \
     'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'


def a_spreadsheet(sheets, shared=(), styles_xml=None, break_rels=False):
    """A real `.xlsx`: a zip of XML parts, written the way a platform writes one.

    `sheets` is a list of (name, rows), where a row is a list of cells and a cell
    is `(reference, xml)` -- so a check can leave a cell OUT, which is exactly
    what a spreadsheet does with an empty one.
    """
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        book = [f"<workbook {NS}><sheets>"]
        rels = ['<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for at, (name, rows) in enumerate(sheets, start=1):
            rid = f"rId{100 + at}"
            book.append(f'<sheet name="{name}" sheetId="{at}" r:id="{rid}"/>')
            # **THE PART NAME DELIBERATELY DOES NOT MATCH THE SHEET ORDER**, the
            # way his real payments file's does not. A reader that sorts the
            # parts, or reaches for `sheet1.xml`, gets the wrong sheet here.
            part = f"worksheets/sheet{90 - at}.xml"
            if not break_rels:
                rels.append(
                    f'<Relationship Id="{rid}" Target="{part}" '
                    'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                    'relationships/worksheet"/>'
                )
            body = []
            for at, cells in enumerate(rows, start=1):
                # **THE ROW'S NUMBER COMES FROM ITS OWN CELLS, not from its
                # position in this list.** Numbered by position, a check could
                # never write rows out of order -- the helper would quietly put
                # them back, and the check that needs them shuffled would pass
                # whatever the reader did. Found by putting that fault back.
                number = at
                for ref, _ in cells:
                    digits = "".join(c for c in ref if c.isdigit())
                    if digits:
                        number = int(digits)
                        break
                inside = "".join(x for _, x in cells)
                body.append(f'<row r="{number}">{inside}</row>')
            # **A LYING `<dimension>`, exactly like his real files carry.**
            z.writestr(
                "xl/" + part,
                f'<worksheet {NS}><dimension ref="A1"/><sheetData>'
                + "".join(body)
                + "</sheetData></worksheet>",
            )
        book.append("</sheets></workbook>")
        rels.append("</Relationships>")
        z.writestr("xl/workbook.xml", "".join(book))
        z.writestr("xl/_rels/workbook.xml.rels", "".join(rels))
        if shared:
            z.writestr(
                "xl/sharedStrings.xml",
                f"<sst {NS}>" + "".join(f"<si><t>{w}</t></si>" for w in shared) + "</sst>",
            )
        if styles_xml:
            z.writestr("xl/styles.xml", styles_xml)
    return out.getvalue()


def text(ref, said):
    return (ref, f'<c r="{ref}" t="inlineStr"><is><t>{said}</t></is></c>')


def shared(ref, number):
    return (ref, f'<c r="{ref}" t="s"><v>{number}</v></c>')


def number(ref, said, style=None):
    s = f' s="{style}"' if style is not None else ""
    return (ref, f'<c r="{ref}"{s}><v>{said}</v></c>')


# ------------------------------------------------------------ the real faults

# 1. THE FIRST SHEET IS NOT THE DATA
TWO_SHEETS = a_spreadsheet([
    ("Help", [[text("A1", "How to use this report")]]),
    ("Orders", [[text("A1", "order_id"), text("B1", "sku")],
                [text("A2", "OD1"), text("B2", "AAA")]]),
])
check("the sheets are named in the workbook's own order",
      tool.sheets_in(TWO_SHEETS) == ("Help", "Orders"))
t = answered(lambda: tool.read(TWO_SHEETS, sheet="Orders"))
check("a sheet asked for by name is the one that is read",
      t is not None and t.columns == ("order_id", "sku") and len(t.rows) == 1)
check("and it is found even though its part is not named for its position",
      t is not None and t.rows[0]["order_id"] == "OD1")
check("asking for a sheet that is not there is refused",
      refused_by(lambda: tool.read(TWO_SHEETS, sheet="Nope")))
check("and the refusal names the sheets there ARE",
      (lambda e: e is not None and "Help" in str(e) and "Orders" in str(e))(
          _catch(lambda: tool.read(TWO_SHEETS, sheet="Nope"))))
t = answered(lambda: tool.read(TWO_SHEETS))
check("not naming a sheet reads the FIRST one -- which on his files is the help page",
      t is not None and t.columns == ("How to use this report",))

# 2. A SHEET THAT POINTS AT A PART THE FILE DOES NOT HAVE
check("a sheet whose part is missing is refused, not read as empty",
      refused_by(lambda: tool.read(
          a_spreadsheet([("Orders", [[text("A1", "x")]])], break_rels=True),
          sheet="Orders")))

# 3. `<dimension>` LIES -- the rows are counted by reading them
MANY = a_spreadsheet([("Orders", [[text("A1", "sku")]] + [[text(f"A{n}", f"S{n}")] for n in range(2, 12)])])
t = answered(lambda: tool.read(MANY, sheet="Orders"))
check("a lying <dimension> does not shorten the file", t is not None and len(t.rows) == 10)

# 4. A MISSING CELL MUST NOT SHIFT THE ROW
GAPPY = a_spreadsheet([("Orders", [
    [text("A1", "sku"), text("B1", "qty"), text("C1", "gmv")],
    [text("A2", "AAA"), text("B2", "2"), text("C2", "100")],
    # **NO CELL FOR B AT ALL** -- what a spreadsheet does with an empty one.
    [text("A3", "BBB"), text("C3", "300")],
])])
t = answered(lambda: tool.read(GAPPY, sheet="Orders"))
check("a row with a missing cell still reads", t is not None and len(t.rows) == 2)
check("THE VALUE AFTER THE GAP STAYS IN ITS OWN COLUMN",
      t is not None and t.rows[1]["gmv"] == "300")
check("and the empty one reads as empty, not as the next value",
      t is not None and t.rows[1]["qty"] == "")
check("the row before it is untouched", t is not None and t.rows[0]["qty"] == "2")

# A row left out entirely must not move the ones after it either.
SKIPPED = BytesIO()
GAPPY_ROWS = a_spreadsheet([("Orders", [
    [text("A1", "sku")], [text("A2", "first")], [text("A5", "later")],
])])
t = answered(lambda: tool.read(GAPPY_ROWS, sheet="Orders"))
check("a skipped row number does not reorder what is left",
      t is not None and [r["sku"] for r in t.rows] == ["first", "later"])

# **AND ROWS WRITTEN OUT OF ORDER ARE PUT BACK IN ORDER.** The check above could
# not catch this: its rows were already in order, so reading them as they came
# gave the same answer. Found by putting the fault back and watching nothing go
# red. A spreadsheet may write its rows in any order and states which is which
# with `r=`; read as they come, a settlement lands against the wrong day.
_shuffled = a_spreadsheet([("Orders", [
    [text("A1", "sku")], [text("A4", "fourth")],
    [text("A2", "second")], [text("A3", "third")],
])])
t = answered(lambda: tool.read(_shuffled, sheet="Orders"))
check("rows written out of order come back in their own order",
      t is not None and [r["sku"] for r in t.rows] == ["second", "third", "fourth"])
check("and each row still knows which line it really is",
      t is not None and [r.line for r in t.rows] == [2, 3, 4])

# 5. TEXT ARRIVES TWO WAYS IN ONE FILE
BOTH_WAYS = a_spreadsheet(
    [("Orders", [[shared("A1", 0), shared("B1", 1)],
                 [text("A2", "OD9"), text("B2", "ZZZ")]])],
    shared=("order_id", "sku"),
)
t = answered(lambda: tool.read(BOTH_WAYS, sheet="Orders"))
check("a header written as shared words comes back as words, not numbers",
      t is not None and t.columns == ("order_id", "sku"))
check("and inline rows underneath it read normally",
      t is not None and t.rows[0]["sku"] == "ZZZ")
check("a shared word that points nowhere is refused rather than blanked",
      refused_by(lambda: tool.read(
          a_spreadsheet([("Orders", [[shared("A1", 0)], [shared("A2", 99)]])],
                        shared=("sku",)), sheet="Orders")))

# 6. A DATE IS A NUMBER, and only the style says so
STYLES = (
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<numFmts><numFmt numFmtId="164" formatCode="dd/mm/yyyy"/>'
    '<numFmt numFmtId="165" formatCode="&quot;d&quot;#,##0.00"/></numFmts>'
    '<cellXfs>'
    '<xf numFmtId="0"/>'      # style 0 -- plain number
    '<xf numFmtId="164"/>'    # style 1 -- a written-out date
    '<xf numFmtId="14"/>'     # style 2 -- a built-in date
    '<xf numFmtId="165"/>'    # style 3 -- MONEY whose format has a "d" IN QUOTES
    '</cellXfs></styleSheet>'
)
DATES = a_spreadsheet([("Orders", [
    [text("A1", "plain"), text("B1", "written"), text("C1", "builtin"), text("D1", "money")],
    [number("A2", "46253", 0), number("B2", "46253", 1),
     number("C2", "46253", 2), number("D2", "46253", 3)],
])], styles_xml=STYLES)
t = answered(lambda: tool.read(DATES, sheet="Orders"))
check("a number with no date format stays the number it was",
      t is not None and t.rows[0]["plain"] == "46253")
check("a number wearing a written-out date format becomes a date",
      t is not None and t.rows[0]["written"] == "2026-08-19")
check("and one wearing a built-in date format does too",
      t is not None and t.rows[0]["builtin"] == "2026-08-19")
check("A MONEY FORMAT WITH A 'd' IN QUOTES IS NOT A DATE",
      t is not None and t.rows[0]["money"] == "46253")
check("a cell wearing a date format but holding text is not lost",
      (lambda r: r is not None and r.rows[0]["written"] == "not a date")(
          answered(lambda: tool.read(a_spreadsheet([("Orders", [
              [text("A1", "written")],
              [("A2", '<c r="A2" s="1" t="inlineStr"><is><t>not a date</t></is></c>')],
          ])], styles_xml=STYLES), sheet="Orders"))))
check("a number too small for the leap-year lie is left alone rather than answered wrong",
      tool._a_date("40") == "40")
check("and the day Excel counts from is the one that absorbs that lie",
      tool.EXCEL_COUNTS_FROM.isoformat() == "1899-12-30")

# ------------------------------------------------- the header is not always row 1

BANDED = a_spreadsheet([("Orders", [
    [text("A1", "Payment Details"), text("B1", "")],
    [text("A2", " Payment Date"), text("B2", "Order ID")],
    [text("A3", "2026-08-28"), text("B3", "OD7")],
])])
t = answered(lambda: tool.read(BANDED, sheet="Orders", header_row=2))
check("the column names can be taken from a row that is not the first",
      t is not None and t.columns == ("Payment Date", "Order ID"))
check("a name with a space on the front can still be looked up",
      t is not None and t.rows[0]["Payment Date"] == "2026-08-28")
check("the band row above is not read as data", t is not None and len(t.rows) == 1)
check("asking for a header row the sheet does not reach is refused",
      refused_by(lambda: tool.read(BANDED, sheet="Orders", header_row=9)))
check("a header row of nought is refused",
      refused_by(lambda: tool.read(BANDED, sheet="Orders", header_row=0)))
check("a header row naming nothing at all is refused",
      refused_by(lambda: tool.read(a_spreadsheet([("Orders", [
          [text("A1", "")], [text("A2", "x")]])]), sheet="Orders")))

# --------------------------------------------------------- what it refuses

check("text handed in where bytes belong is refused",
      refused_by(lambda: tool.read("not bytes")))
check("something that is neither is refused too", refused_by(lambda: tool.read(7)))
check("a file that is not a zip at all is refused -- usually a sign-in page",
      refused_by(lambda: tool.read(b"<html>Please sign in</html>")))
check("and that refusal says so, so nobody hunts for a broken reader",
      (lambda e: e is not None and "sign-in" in str(e))(
          _catch(lambda: tool.read(b"<html>Please sign in</html>"))))
# **A ZIP THAT IS NOT A SPREADSHEET, and a spreadsheet that is damaged.**
# Written first as a one-liner ending in `if False else True` -- green by
# construction, and the SECOND such check written today. Both are real now.


def _a_zip_of_something_else():
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("hello.txt", "this is not a spreadsheet")
    return out.getvalue()


def _a_damaged_workbook():
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("xl/workbook.xml", "<workbook><sheets><sheet ")
    return out.getvalue()


check("a zip that is not a spreadsheet is refused",
      refused_by(lambda: tool.read(_a_zip_of_something_else())))
check("and so is one whose workbook part is damaged",
      refused_by(lambda: tool.read(_a_damaged_workbook())))
check("naming the sheets of a damaged one is refused too, rather than answering none",
      refused_by(lambda: tool.sheets_in(_a_damaged_workbook())))

# --------------------------------------------- it hands back the same shape

t = answered(lambda: tool.read(TWO_SHEETS, sheet="Orders"))
check("what comes back is the same kind of thing a text file gives",
      isinstance(t, table.Table))
check("so what it read can be said in one line", t is not None and "1 rows read" in t.says())
check("a nought comes back as text, never as a number",
      (lambda r: r is not None and r.rows[0]["qty"] == "0")(
          answered(lambda: tool.read(a_spreadsheet([("Orders", [
              [text("A1", "qty")], [number("A2", "0")]])]), sheet="Orders"))))
check("a column that is not there is refused, not answered blank",
      t is not None and refused_by(lambda: t.rows[0]["nope"]))

# A cell that says it is somewhere impossible.
check("a cell with a nonsense reference is refused rather than guessed at",
      refused_by(lambda: tool.read(a_spreadsheet([("Orders", [
          [text("A1", "sku")], [("?", '<c r="?" t="inlineStr"><is><t>x</t></is></c>')]])]),
          sheet="Orders")))
check("a cell reference turns into the right column number",
      tool.column_number("A2") == 0 and tool.column_number("B1") == 1
      and tool.column_number("AM7") == 38)

# Bold-in-the-middle: one value written as several pieces.
check("a value written in pieces comes back whole",
      (lambda r: r is not None and r.rows[0]["sku"] == "Ready to ship")(
          answered(lambda: tool.read(a_spreadsheet([("Orders", [
              [text("A1", "sku")],
              [("A2", '<c r="A2" t="inlineStr"><is><r><t>Ready</t></r>'
                      '<r><t xml:space="preserve"> to ship</t></r></is></c>')],
          ])]), sheet="Orders"))))

# ------------------------------------------- and now against HIS REAL FILES

REAL = [
    ("flipkart orders",
     HIS_FILES / "flipkart" / "orders" / "flipkart_orders_2026-08-20.xlsx",
     "Orders", 1, 39, 63, "order_item_id", ("Help", "Orders")),
    ("flipkart payments",
     HIS_FILES / "flipkart" / "payments" / "flipkart_payments_2026-08-28.xlsx",
     "Orders", 2, 74, 77, "Order ID", None),
    ("meesho payments",
     HIS_FILES / "meesho" / "payments" / "meesho_payments_2026-08-31.xlsx",
     "Order Payments", 2, 43, 83, None, None),
]

for what, path, which, header, columns, rows, a_column, names in REAL:
    if not path.is_file():
        not_run.append(f"{what} -- {path} is not on this machine")
        print(f"NOT RUN  his real {what}: {path} is not here")
        continue
    raw = path.read_bytes()
    real = answered(lambda r=raw, w=which, h=header: tool.read(r, sheet=w, header_row=h))
    check(f"his real {what}: it reads at all", real is not None)
    check(f"his real {what}: {columns} columns", real is not None and len(real.columns) == columns)
    check(f"his real {what}: {rows} rows", real is not None and len(real.rows) == rows)
    check(f"his real {what}: the first sheet is NOT the one with the data",
          (lambda s: s is not None and s[0] != which)(answered(lambda r=raw: tool.sheets_in(r))))
    if names:
        check(f"his real {what}: its sheets are named {names}",
              answered(lambda r=raw: tool.sheets_in(r)) == names)
    if a_column:
        check(f"his real {what}: {a_column!r} can be looked up on every row",
              real is not None and all(r[a_column] is not None for r in real.rows))

# The one his real file has that no made-up file would have thought of.
mp = HIS_FILES / "meesho" / "payments" / "meesho_payments_2026-08-31.xlsx"
if mp.is_file():
    real = answered(lambda: tool.read(mp.read_bytes(), sheet="Order Payments", header_row=2))
    check("HIS REAL MEESHO PAYMENTS FILE HAS TWO COLUMNS WITH ONE NAME",
          real is not None and "Fixed Fee (Incl. GST)" in real.ambiguous)
    check("and it still reads, rather than one name losing 42 good columns",
          real is not None and len(real.columns) == 43 and len(real.rows) == 83)
    check("asking for that one name is refused, and says where both are",
          real is not None and refused_by(lambda: real.rows[0]["Fixed Fee (Incl. GST)"]))
    check("and the file says out loud that a column cannot be read",
          real is not None and "cannot be read" in real.says())
    # A real date, converted from a real serial, in a real file.
    fp = HIS_FILES / "flipkart" / "payments" / "flipkart_payments_2026-08-28.xlsx"
    if fp.is_file():
        pay = answered(lambda: tool.read(fp.read_bytes(), sheet="Orders", header_row=2))
        dates = [r["Payment Date"] for r in pay.rows if r["Payment Date"].strip()] if pay else []
        check("his real payment dates come back as dates, not five-digit numbers",
              len(dates) > 50 and all(len(d) == 10 and d[4] == "-" for d in dates))
else:
    not_run.append("the duplicate-column and real-date checks")

if not_run:
    print()
    print(f"      {len(not_run)} group(s) NOT RUN -- his real files are not on this machine:")
    for one in not_run:
        print(f"        {one}")
    print("      They are not passes. Run this where the Drive folder is.")

print()
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

WITH_HIS_FILES = 66
WITHOUT = 46
EXPECTED = WITH_HIS_FILES if not not_run else WITHOUT
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print(f"all {ran} checks passed"
      + (f" ({len(not_run)} group(s) not run -- his real files are elsewhere)" if not_run else ""))
