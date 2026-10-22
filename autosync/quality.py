"""Reading Flipkart's Quality Insights file into one record per listing (A87, plan part F, piece F1).

**THE COLUMNS AND THE SHAPES OF THEIR CELLS ARE FROM HIS REAL FILE** (`flipkart_fk_quality_insights_2026-10-19.csv`, 18 listings, read from his Drive):

| Column | What a cell holds | Read as |
|---|---|---|
| `Product`, `SKU ID` | the title and the seller's own SKU | `product`, `sku` (the record is named by the SKU) |
| `Yearly Sales` | `₹6.32L`, `₹79.67K`, `₹3.68K` (rupees with a K, L or Cr suffix) | `yearlySales` in rupees |
| `1Y Ratings Trend` | the star level, `4.2` (or `NA`) | `stars`, **a level, never summed** |
| `5M Returns Trend` | `17.6%`, `25%`, `9.1% | Not Enough Orders`, `NA | Not Enough Orders` | `returnsPct` and, when the cell says so, `returnsNote` |
| `FA badge` | `Yes` / `No` | `faBadge` |
| `Suppression Risk` | `No Risk`, `At Risk`, `Suppressed` | `suppressionRisk`, as the platform wrote it |
| `Issue Details` | `Quality`, `Misshipment`, `Not enough feedback` | `issue`, as the platform wrote it |

**A BLANK OR `NA` IS NOTHING, NEVER NOUGHT.** A cell this cannot read (an unknown rupee suffix, a star level that is not a number) refuses that row by name and the
rest are read; a column the file lacks stops the file in words naming the columns it has.

Nothing here opens a file, a clock or a connection.
"""

from decimal import Decimal
from typing import Dict, Optional, Tuple

import firestore
import records as shared
import table

THE_COLUMNS = ("Product", "SKU ID", "Yearly Sales", "1Y Ratings Trend", "5M Returns Trend", "FA badge", "Suppression Risk", "Issue Details")
# What a record holds, in the order it is written (a field outside this list is refused by the writer).
QUALITY_FIELDS = (
    "platform", "report", "sku", "product", "yearlySales", "stars", "returnsPct", "returnsNote", "faBadge", "suppressionRisk", "issue",
    "history", "fileDay", "digest",
)
KIND = shared.RecordKind(firestore.QUALITY, QUALITY_FIELDS, "listing quality record", required_days=("fileDay",))
HISTORY_KEPT = 12
# The history grows with every change, so it is not part of what the listing "says".
NOT_IN_THE_DIGEST = ("history",)
_SUFFIX = {"K": Decimal(1000), "L": Decimal(100000), "CR": Decimal(10000000)}


def rupees(said: str) -> Optional[int]:
    """`₹6.32L` -> 632000. Nothing for a blank or `NA`; a suffix this does not know is refused (`ValueError`), never guessed."""
    text = (said or "").strip()
    factor = Decimal(1)
    for suffix in ("CR", "K", "L"):
        if text.upper().endswith(suffix):
            factor, text = _SUFFIX[suffix], text[: -len(suffix)]
            break
    try:
        value = shared.a_figure(text, most=10 ** 13 / float(factor))
    except ValueError:
        raise ValueError(f"{said!r} is not an amount of rupees") from None
    return None if value is None else int((value * factor).to_integral_value())


def merge(record: Dict[str, object], held) -> Dict[str, object]:
    """The record with its history made from the held record's (`held` is the record in the database, or nothing)."""
    return with_history(record, tuple((held or {}).get("history") or ()))


def with_history(record: Dict[str, object], held: Tuple[Dict, ...]) -> Dict[str, object]:
    """The record with its short history: the held readings, then this day's, newest last, the last `HISTORY_KEPT` of them (one reading a day).

    **IT IS THE LAST TWELVE CHANGES, not twelve days:** a listing's record is only rewritten when what the platform says about it changed, so a point is added
    when the figures move. A change in the rupees or the note alone adds a point with the same stars and returns share.
    """
    point = {k: record[k] for k in ("stars", "returnsPct") if k in record}
    points = [one for one in held if isinstance(one, dict) and one.get("day") != record["fileDay"]]
    points.append({"day": record["fileDay"], **point})
    out = dict(record)
    out["history"] = sorted(points, key=lambda one: str(one.get("day")))[-HISTORY_KEPT:]
    return out


def read_quality(report_id: str, platform: str, rows: table.Table, file_day: str):
    """`(records, not_read)`: one record per listing, named `<platform>__<SKU ID>`."""
    shared.require_columns(rows, THE_COLUMNS, "a quality insights file")
    records: Dict[str, Dict[str, object]] = {}
    not_read = []
    for row in rows:
        sku = row["SKU ID"].strip()
        if not shared.a_safe_name(sku):
            not_read.append(f"line {row.line}: {sku[:60]!r} cannot be the name of a listing record (empty, a slash, a dot name or too long)")
            continue
        record: Dict[str, object] = {"platform": platform, "report": report_id, "sku": sku, "fileDay": file_day}
        if row["Product"].strip():
            record["product"] = row["Product"].strip()
        try:
            sales = rupees(row["Yearly Sales"])
            stars = shared.a_figure(row["1Y Ratings Trend"], most=5)
            returns_cell = [part.strip() for part in row["5M Returns Trend"].split("|")]
            returns_pct = shared.a_figure(returns_cell[0], most=10**6)
        except ValueError as wrong:
            not_read.append(f"line {row.line} ({sku}): {wrong}")
            continue
        if sales is not None:
            record["yearlySales"] = sales
        if stars is not None:
            record["stars"] = float(stars)
        if returns_pct is not None:
            record["returnsPct"] = float(returns_pct)
        if len(returns_cell) > 1 and returns_cell[1]:
            record["returnsNote"] = returns_cell[1]
        badge = row["FA badge"].strip().lower()
        if badge in ("yes", "no"):
            record["faBadge"] = badge == "yes"
        for field, column in (("suppressionRisk", "Suppression Risk"), ("issue", "Issue Details")):
            if row[column].strip():
                record[field] = row[column].strip()
        record["digest"] = shared.the_digest(record, leave_out=NOT_IN_THE_DIGEST)
        if f"{platform}__{sku}" in records:
            not_read.append(f"line {row.line}: {sku!r} is named twice in this file, so the later line stands")
        records[f"{platform}__{sku}"] = record
    return records, tuple(not_read)
