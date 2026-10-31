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
        self.sales = tuple(sales.Sale(platform="flipkart", order_id=o, sku="S", settlement=fig, notes="pay:" + pay) for o, pay, fig in lines)


same = [("a.xlsx", Pretend(("OD1", "UTR-0001", "196.85"))), ("b.xlsx", Pretend(("OD1", "UTR-0001", "196.85")))]
check("the same payout and line with the same figure in two files is normal and is not listed", answered(lambda: dry.the_payouts_that_disagree(same)) == [])
different = [("a.xlsx", Pretend(("OD1", "UTR-0001", "196.85"))), ("b.xlsx", Pretend(("OD1", "UTR-0001", "100.00")))]
said = answered(lambda: dry.the_payouts_that_disagree(different)) or []
check("one payout carrying different figures for one order in two files is listed, with both figures and both files",
      len(said) == 1 and "196.85 in a.xlsx" in said[0] and "100.00 in b.xlsx" in said[0] and "UTR-0001" in said[0])
other_orders = [("a.xlsx", Pretend(("OD1", "UTR-0001", "1"))), ("b.xlsx", Pretend(("OD2", "UTR-0001", "2"), ("OD1", "UTR-0002", "3")))]
check("different orders in one payout, or one order in different payouts, are not a contradiction", answered(lambda: dry.the_payouts_that_disagree(other_orders)) == [])

merged = [("a.xlsx", Pretend(("OD1", "UTR-0001 pay:UTR-0002", "50"))), ("b.xlsx", Pretend(("OD1", "UTR-0001", "196.85")))]
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

with tempfile.TemporaryDirectory() as folder:
    (Path(folder) / "fk_payments").mkdir()
    one = Path(folder) / "fk_payments" / "flipkart_fk_payments_2026-10-29.xlsx"
    one.write_bytes(b"this is no spreadsheet")
    lines = []
    code = answered(lambda: dry.main(["dry_run.py", folder], lines.append))
    check("run over a folder it lists the refusal, answers 1, and says nothing was written", code == 1 and any("REFUSED" in x for x in lines) and "Nothing was written." in lines[-1])
    check("and the file it read is exactly as it was", one.read_bytes() == b"this is no spreadsheet" and sorted(p.name for p in Path(folder).rglob("*") if p.is_file()) == [one.name])
    check("with no folder it prints the usage and answers 2", answered(lambda: dry.main(["dry_run.py"], lines.append)) == 2)

EXPECTED = 11
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
