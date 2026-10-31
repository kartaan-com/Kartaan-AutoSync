"""A read-only DRY RUN of the readers over a folder of old files: what would be refused, and whether any payout contradicts itself.

    python tools/dry_run.py <folder>

**NOTHING IS WRITTEN ANYWHERE, AND NOTHING IS SENT.** Files are opened to read, no connection is made, no state is kept. Run it on the
old months BEFORE they are moved into the seller's folders, so a layout the readers refuse is found while it costs nothing.

`<folder>` holds one sub-folder per report, named by the report's id (`fk_orders`, `fk_payments`, ...) -- the layout the seller's own
Kartaan folder has. Every file in a sub-folder is read by that report's reader exactly as a night would read it; a refusal is listed with
the file's name and the reader's own words. **THE SETTLEMENTS REPORT (`az_settlements`) NEEDS THE SELLER'S OTHER FILES TO BE READ, so it is
listed as not read here, never skipped silently.**

**AND ONE QUESTION ONLY THIS CAN ANSWER (PR1, A10, a release condition):** Flipkart's payments file is one payout (its NEFT id) and a row's
money is the sum of its distinct payouts, on the promise that the same payout in two files carries the same lines for an order. For every
`fk_payments` file in the folder this lists each payout that appears with DIFFERENT figures for the same order and SKU in different files.
"""

import sys
from pathlib import Path
from typing import Callable, Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "autosync"))

import reading  # noqa: E402
import whats_new  # noqa: E402
from payments import PAYOUT_KEY  # noqa: E402

NOT_READ_HERE = ("az_settlements",)


def the_payouts_that_disagree(read: Sequence[Tuple[str, "reading.Reading"]]) -> List[str]:
    """Each payout that carries different money for one order and SKU in different files, one line each.

    **THE SAME PAYOUT AND THE SAME LINE WITH THE SAME FIGURE IN TWO FILES IS NORMAL** (overlapping downloads) and is not listed.
    """
    seen: Dict[Tuple[str, str], Dict[str, set]] = {}
    for file_name, one in read:
        for sale in one.sales:
            for key in (k for k in (sale.notes or "").split() if k.startswith(PAYOUT_KEY)):
                figures = seen.setdefault((key[len(PAYOUT_KEY):], sale.id), {})
                figures.setdefault(str(sale.settlement), set()).add(file_name)
    return [
        f"payout {payout}, {line!r}: " + "; ".join(f"{figure} in {', '.join(sorted(files))}" for figure, files in sorted(figures.items()))
        for (payout, line), figures in sorted(seen.items()) if len(figures) > 1
    ]


def the_dry_run(
    files: Dict[str, Sequence[Tuple[str, bytes]]],
    can_be_read: Sequence["reading.HowToRead"] = reading.WHAT_CAN_BE_READ,
) -> Tuple[List[str], List[str], List[str]]:
    """`(read, refused, payouts that disagree)` -- each a list of plain lines. `files` is `{report id: [(file name, bytes), ...]}`."""
    how_by_id = {how.report_id: how for how in can_be_read}
    read_ok: List[str] = []
    refused: List[str] = []
    payments_read: List[Tuple[str, "reading.Reading"]] = []
    for report_id in sorted(files):
        how = how_by_id.get(report_id)
        if how is None:
            refused.append(f"{report_id}: a folder no reader is named for -- nothing in it was read")
            continue
        if report_id in NOT_READ_HERE:
            refused.append(f"{report_id}: not read by the dry run (it needs the seller's other files); {len(files[report_id])} file(s) unchecked")
            continue
        for name, body in files[report_id]:
            try:
                made = reading.a_reading(how, whats_new.InTheFolder(which=f"{report_id}/{name}", name=name, size=len(body)), body)
            except Exception as wrong:  # noqa: BLE001 - every refusal is listed, whatever kind it is
                refused.append(f"{report_id}/{name}: {wrong}")
                continue
            one, rows_refused = made
            read_ok.append(f"{report_id}/{name}: {len(one.sales)} line(s) read" + (f", {rows_refused} row(s) refused" if rows_refused else ""))
            if report_id == "fk_payments":
                payments_read.append((name, one))
    return read_ok, refused, the_payouts_that_disagree(payments_read)


def main(argv: Sequence[str], out: Callable[[str], None] = print) -> int:
    if len(argv) != 2 or not Path(argv[1]).is_dir():
        out("Usage: python tools/dry_run.py <folder with one sub-folder per report>")
        return 2
    files = {
        sub.name: [(f.name, f.read_bytes()) for f in sorted(sub.iterdir()) if f.is_file()]
        for sub in sorted(Path(argv[1]).iterdir()) if sub.is_dir()
    }
    read_ok, refused, contradicting = the_dry_run(files)
    for line in read_ok:
        out("READ     " + line)
    for line in refused:
        out("REFUSED  " + line)
    for line in contradicting:
        out("PAYOUT CONTRADICTS ITSELF  " + line)
    out(f"\n{len(read_ok)} file(s) read, {len(refused)} refused or not read, {len(contradicting)} payout line(s) with different figures in different files. Nothing was written.")
    return 1 if refused or contradicting else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
