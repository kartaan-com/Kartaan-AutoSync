"""Reading Meesho's whole-shop dashboard figures into one record per day (A87, D473; plan part G step 4, `me_views`).

**THE FILE IS FROM HIS REAL RUNS** (`meesho_me_views.csv`, `Date,Views,Orders`, one shop-wide row per day; A86's lane lands it as
`meesho_me_views_<yyyy-mm-dd>.csv`). It holds a figure for the WHOLE SHOP, so it belongs to no listing: a record per day, `platform_shop_days/<platform>__<day>`.
Meesho's page does not say what window a day's figure covers, so nothing is derived from it -- two days are two records and are never added or subtracted.

**A BLANK IS NOTHING, NEVER NOUGHT; a day or a figure this cannot read refuses that row by name** and the rest are read. A column the file lacks stops it in
words naming the columns it has.

Nothing here opens a file, a clock or a connection.
"""

import hashlib
import json
from decimal import Decimal, InvalidOperation
from typing import Dict, Tuple

import returns
import table

THE_COLUMNS = ("Date", "Views", "Orders")
SHOP_FIELDS = ("platform", "report", "day", "views", "orders", "fileDay", "digest")


def _a_count(said: str):
    text = (said or "").replace(",", "").strip()
    if not text:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"{said!r} is not a count") from None
    if not value.is_finite() or value < 0 or value != value.to_integral_value():
        raise ValueError(f"{said!r} is not a whole count")
    return int(value)


def the_digest(record: Dict[str, object]) -> str:
    said = {k: v for k, v in sorted(record.items()) if k not in ("fileDay", "digest")}
    return hashlib.sha1(json.dumps(said, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]


def read_shop_days(report_id: str, platform: str, rows: table.Table, file_day: str) -> Tuple[Dict[str, Dict[str, object]], Tuple[str, ...]]:
    """`(records, not_read)`: one record per day, named `<platform>__<day>`; a day named twice in a file is its later line."""
    missing = [c for c in THE_COLUMNS if c not in rows.columns]
    if missing:
        raise table.CannotRead(
            "This does not look like a shop figures file. It has no " + ", ".join(repr(c) for c in missing)
            + ". It has: " + ", ".join(repr(c) for c in rows.columns if c) + ". Nothing was read."
        )
    records: Dict[str, Dict[str, object]] = {}
    not_read = []
    for row in rows:
        day = returns.a_day(row["Date"])
        if day is None:
            not_read.append(f"line {row.line}: {row['Date']!r} is not a day this can read")
            continue
        try:
            views, orders = _a_count(row["Views"]), _a_count(row["Orders"])
        except ValueError as wrong:
            not_read.append(f"line {row.line}: {wrong}")
            continue
        record: Dict[str, object] = {"platform": platform, "report": report_id, "day": day, "fileDay": file_day}
        if views is not None:
            record["views"] = views
        if orders is not None:
            record["orders"] = orders
        record["digest"] = the_digest(record)
        if f"{platform}__{day}" in records:
            not_read.append(f"line {row.line}: {day} is named twice in this file, so the later line stands")
        records[f"{platform}__{day}"] = record
    return records, tuple(not_read)
