"""Checks for tools/dry_run.py -- by CALLING it with made-up files (PR1).

The tool reads and lists; it must never write. Two of the questions use the real readers (a body that is no spreadsheet, a name with no day);
the payout question hands it readings built here, because a real payments file is the seller's own data.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dry_run as dry  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "autosync"))
import sales  # noqa: E402

ran = 0
failures = []


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


def answered(work):
    try:
        return work()
    except Exception:  # noqa: BLE001 - a throw turns one check red by name
        return None


class Pretend:
    """A reading with only what the payout question looks at."""

    def __init__(self, *lines):
        self.sales = tuple(sales.Sale(platform="flipkart", order_id=o, sku="S", settlement=fig, notes="fkpay:" + pay) for o, pay, fig in lines)


same = [("a.xlsx", Pretend(("OD1", "UTR-0001", "196.85"))), ("b.xlsx", Pretend(("OD1", "UTR-0001", "196.85")))]
check("the same payout and line with the same figure in two files is normal and is not listed", answered(lambda: dry.the_payouts_that_disagree(same)) == [])
different = [("a.xlsx", Pretend(("OD1", "UTR-0001", "196.85"))), ("b.xlsx", Pretend(("OD1", "UTR-0001", "100.00")))]
said = answered(lambda: dry.the_payouts_that_disagree(different)) or []
check("one payout carrying different figures for one order in two files is listed, with both figures and both files",
      len(said) == 1 and "196.85 in a.xlsx" in said[0] and "100.00 in b.xlsx" in said[0] and "UTR-0001" in said[0])
other_orders = [("a.xlsx", Pretend(("OD1", "UTR-0001", "1"))), ("b.xlsx", Pretend(("OD2", "UTR-0001", "2"), ("OD1", "UTR-0002", "3")))]
check("different orders in one payout, or one order in different payouts, are not a contradiction", answered(lambda: dry.the_payouts_that_disagree(other_orders)) == [])

merged = [("a.xlsx", Pretend(("OD1", "UTR-0001 fkpay:UTR-0002", "50"))), ("b.xlsx", Pretend(("OD1", "UTR-0001", "196.85")))]
check("PR1c 9: a line holding two payout keys (one combined figure) is not read as each key's own figure",
      answered(lambda: dry.the_payouts_that_disagree(merged)) == [])
said = answered(lambda: dry.the_orders_with_several_payouts_in_one_file(merged)) or []
check("PR1c 6: and it is listed as an order paid in several payouts in ONE file, with the file named",
      len(said) == 1 and "a.xlsx" in said[0] and "UTR-0001, UTR-0002" in said[0])

ok, refused, clash = answered(lambda: dry.the_dry_run({"fk_payments": [("flipkart_fk_payments_2026-10-29.xlsx", b"this is no spreadsheet")]})) or ([], [], [])
check("a body that is no spreadsheet is REFUSED and named with the reader's own words, not skipped", ok == [] and len(refused) == 1 and "fk_payments/flipkart_fk_payments_2026-10-29.xlsx" in refused[0])
ok, refused, clash = answered(lambda: dry.the_dry_run({"fk_payments": [("no day here.xlsx", b"x")]})) or ([], [], [])
check("a file with no day in its name is refused, saying so", len(refused) == 1 and "no day in its name" in refused[0])
ok, refused, clash = answered(lambda: dry.the_dry_run({"made_up_report": [("x.xlsx", b"x")], "az_settlements": [("a", b"x"), ("b", b"y")]})) or ([], [], [])
check("a folder no reader is named for, and the settlements report, are listed as not read -- never silently skipped",
      len(refused) == 2 and any("no reader" in r for r in refused) and any("2 file(s) unchecked" in r for r in refused))

# **A REAL READABLE FLIPKART PAYMENTS FILE (PR1c proving):** two payouts for one order in one file, and the same payout with another figure in a second file.
import io  # noqa: E402
import zipfile  # noqa: E402
from xml.sax.saxutils import escape  # noqa: E402

import payments  # noqa: E402

NS = ('xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')


def _letters(n):
    out = ""
    n += 1
    while n:
        n, rest = divmod(n - 1, 26)
        out = chr(65 + rest) + out
    return out


def _a_spreadsheet(sheets):
    """A real `.xlsx` made by hand, a zip of XML parts, as payments_checks.py makes one: GitHub's runner has no openpyxl."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        book = [f"<workbook {NS}><sheets>"]
        rels = ['<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for at, (name, rows) in enumerate(sheets, start=1):
            book.append(f'<sheet name="{name}" sheetId="{at}" r:id="rId{at}"/>')
            rels.append(f'<Relationship Id="rId{at}" Target="worksheets/sheet{at}.xml" '
                        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/>')
            body = "".join(
                f'<row r="{number}">' + "".join(
                    f'<c r="{_letters(n)}{number}" t="inlineStr"><is><t>{escape(said)}</t></is></c>'
                    for n, said in enumerate(cells) if said != "") + "</row>"
                for number, cells in enumerate(rows, start=1))
            z.writestr(f"xl/worksheets/sheet{at}.xml", f"<worksheet {NS}><sheetData>{body}</sheetData></worksheet>")
        z.writestr("xl/workbook.xml", "".join(book) + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels", "".join(rels) + "</Relationships>")
    return out.getvalue()


def _a_payments_file(*lines):
    cols = list(payments.the_columns_a_file_of("flipkart")) + ["NEFT ID"]
    rows = [["Payment Details"] + [""] * (len(cols) - 1), cols, ["", "", "", "sub-heading"] + [""] * (len(cols) - 4)]
    for order, figure, payout in lines:
        row = [""] * len(cols)
        row[cols.index("Order ID")], row[cols.index("Seller SKU")] = order, "S"
        row[cols.index("Bank Settlement Value (Rs.)")], row[cols.index("NEFT ID")] = figure, payout
        rows.append(row)
    return _a_spreadsheet([("Report Help", []), ("Orders", rows)])


_one = _a_payments_file(("OD1", "196.85", "UTR-00000001"), ("OD1", "-403.35", "UTR-00000002"))
_two = _a_payments_file(("OD1", "100.00", "UTR-00000001"))
ok, refused, clash = answered(lambda: dry.the_dry_run({"fk_payments": [("flipkart_fk_payments_2026-10-29.xlsx", _one), ("flipkart_fk_payments_2026-10-30.xlsx", _two)]})) or ([], [], [])
check("PR1c proving: real payments files are read, counted by their lines, and not refused",
      refused == [] and ok == ["fk_payments/flipkart_fk_payments_2026-10-29.xlsx: 2 line(s) read", "fk_payments/flipkart_fk_payments_2026-10-30.xlsx: 1 line(s) read"])
check("PR1c proving: and from them it lists the payout that disagrees with itself AND the order paid in two payouts in one file",
      any("UTR-00000001" in x and "196.85 in flipkart_fk_payments_2026-10-29.xlsx" in x and "100 in flipkart_fk_payments_2026-10-30.xlsx" in x for x in clash)
      and any("2 payouts in ONE file flipkart_fk_payments_2026-10-29.xlsx" in x for x in clash))
with tempfile.TemporaryDirectory() as folder2:
    (Path(folder2) / "fk_payments").mkdir()
    (Path(folder2) / "fk_payments" / "flipkart_fk_payments_2026-10-29.xlsx").write_bytes(_one)
    (Path(folder2) / "fk_payments" / "flipkart_fk_payments_2026-10-30.xlsx").write_bytes(_two)
    said = []
    code = answered(lambda: dry.main(["dry_run.py", folder2], said.append))
    check("PR1c proving: run over a folder it prints each problem under PAYOUT PROBLEM, answers 1, and counts them",
          code == 1 and sum(x.startswith("PAYOUT PROBLEM  ") for x in said) == len(clash) and any(x.startswith("READ     ") for x in said)
          and "2 file(s) read, 0 refused or not read, 2 payout problem(s)" in said[-1])

with tempfile.TemporaryDirectory() as folder:
    (Path(folder) / "fk_payments").mkdir()
    one = Path(folder) / "fk_payments" / "flipkart_fk_payments_2026-10-29.xlsx"
    one.write_bytes(b"this is no spreadsheet")
    lines = []
    code = answered(lambda: dry.main(["dry_run.py", folder], lines.append))
    check("run over a folder it lists the refusal, answers 1, and says nothing was written", code == 1 and any("REFUSED" in x for x in lines) and "Nothing was written." in lines[-1])
    check("and the file it read is exactly as it was", one.read_bytes() == b"this is no spreadsheet" and sorted(p.name for p in Path(folder).rglob("*") if p.is_file()) == [one.name])
    _usage = []
    check("with no folder it prints the usage and answers 2", answered(lambda: dry.main(["dry_run.py"], _usage.append)) == 2)
    check("PR1c proving: and the usage line says what to give it", len(_usage) == 1 and "Usage: python tools/dry_run.py" in _usage[0] and "sub-folder per report" in _usage[0])

EXPECTED = 15
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
