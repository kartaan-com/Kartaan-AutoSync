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

import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional, Tuple

import table

THE_COLUMNS = ("Product", "SKU ID", "Yearly Sales", "1Y Ratings Trend", "5M Returns Trend", "FA badge", "Suppression Risk", "Issue Details")
# What a record holds, in the order it is written (a field outside this list is refused by the writer).
QUALITY_FIELDS = (
    "platform", "report", "sku", "product", "yearlySales", "stars", "returnsPct", "returnsNote", "faBadge", "suppressionRisk", "issue",
    "history", "fileDay", "digest",
)
HISTORY_KEPT = 12
_SUFFIX = {"K": Decimal(1000), "L": Decimal(100000), "CR": Decimal(10000000)}


def rupees(said: str) -> Optional[int]:
    """`₹6.32L` -> 632000. Nothing for a blank or `NA`; a suffix this does not know is refused (`ValueError`), never guessed."""
    text = (said or "").replace("₹", "").replace(",", "").strip()
    if not text or text.upper() == "NA":
        return None
    factor = Decimal(1)
    for suffix in ("CR", "K", "L"):
        if text.upper().endswith(suffix):
            factor, text = _SUFFIX[suffix], text[: -len(suffix)].strip()
            break
    try:
        value = Decimal(text) * factor
        if not value.is_finite() or abs(value) > Decimal(10) ** 13:
            raise ValueError(f"{said!r} is not an amount of rupees this can hold")
        return int(value.to_integral_value())
    except (InvalidOperation, ArithmeticError):
        raise ValueError(f"{said!r} is not an amount of rupees") from None


def _a_number(said: str, most: float) -> Optional[float]:
    """A figure from `0` to `most`, or nothing for a blank or `NA`; anything else is refused (`ValueError`)."""
    text = (said or "").replace("%", "").strip()
    if not text or text.upper() == "NA":
        return None
    try:
        value = Decimal(text)
        if not value.is_finite() or value < 0 or value > Decimal(str(most)):
            raise ValueError(f"{said!r} is not a figure from 0 to {most:g}")
        return float(value)
    except (InvalidOperation, ArithmeticError):
        raise ValueError(f"{said!r} is not a figure") from None


def the_digest(record: Dict[str, object]) -> str:
    """A fingerprint of what a listing's quality SAYS (never of the day it was read, nor of its history), so the same file read twice writes nothing."""
    said = {k: v for k, v in sorted(record.items()) if k not in ("fileDay", "digest", "history")}
    return hashlib.sha1(json.dumps(said, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]


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
    missing = [c for c in THE_COLUMNS if c not in rows.columns]
    if missing:
        raise table.CannotRead(
            "This does not look like a quality insights file. It has no " + ", ".join(repr(c) for c in missing)
            + ". It has: " + ", ".join(repr(c) for c in rows.columns if c) + ". Nothing was read."
        )
    records: Dict[str, Dict[str, object]] = {}
    not_read = []
    for row in rows:
        sku = row["SKU ID"].strip()
        if not sku or "/" in sku or sku in (".", "..") or len(sku.encode("utf-8")) > 1000:
            not_read.append(f"line {row.line}: {sku[:60]!r} cannot be the name of a listing record (empty, a slash, a dot name or too long)")
            continue
        record: Dict[str, object] = {"platform": platform, "report": report_id, "sku": sku, "fileDay": file_day}
        if row["Product"].strip():
            record["product"] = row["Product"].strip()
        try:
            sales = rupees(row["Yearly Sales"])
            stars = _a_number(row["1Y Ratings Trend"], 5)
            returns_cell = [part.strip() for part in row["5M Returns Trend"].split("|")]
            returns_pct = _a_number(returns_cell[0], 100)
        except ValueError as wrong:
            not_read.append(f"line {row.line} ({sku}): {wrong}")
            continue
        if sales is not None:
            record["yearlySales"] = sales
        if stars is not None:
            record["stars"] = stars
        if returns_pct is not None:
            record["returnsPct"] = returns_pct
        if len(returns_cell) > 1 and returns_cell[1]:
            record["returnsNote"] = returns_cell[1]
        badge = row["FA badge"].strip().lower()
        if badge in ("yes", "no"):
            record["faBadge"] = badge == "yes"
        for field, column in (("suppressionRisk", "Suppression Risk"), ("issue", "Issue Details")):
            if row[column].strip():
                record[field] = row[column].strip()
        record["digest"] = the_digest(record)
        if f"{platform}__{sku}" in records:
            not_read.append(f"line {row.line}: {sku!r} is named twice in this file, so the later line stands")
        records[f"{platform}__{sku}"] = record
    return records, tuple(not_read)
