"""Reading Meesho's whole-shop dashboard figures into one record per day (A87, D473; plan part G step 4, `me_views`).

**THE FILE IS FROM HIS REAL RUNS** (`meesho_me_views.csv`, `Date,Views,Orders`, one shop-wide row per day; A86's lane lands it as
`meesho_me_views_<yyyy-mm-dd>.csv`). It holds a figure for the WHOLE SHOP, so it belongs to no listing: a record per day, `platform_shop_days/<platform>__<day>`.
Meesho's page does not say what window a day's figure covers, so nothing is derived from it -- two days are two records and are never added or subtracted.

**A BLANK IS NOTHING, NEVER NOUGHT; a day or a figure this cannot read refuses that row by name** and the rest are read. A column the file lacks stops it in
words naming the columns it has.

Nothing here opens a file, a clock or a connection.
"""

from typing import Dict, Tuple

import firestore
import records as shared
import returns
import table

THE_COLUMNS = ("Date", "Views", "Orders")
SHOP_FIELDS = ("platform", "report", "day", "views", "orders", "healthRating", "orderDefectRate", "lateDispatchRate", "cancelRate", "validTrackingRate", "fileDay", "digest")
KIND = shared.RecordKind(firestore.SHOP_DAYS, SHOP_FIELDS, "shop day", required_days=("day", "fileDay"))


def read_shop_days(report_id: str, platform: str, rows: table.Table, file_day: str) -> Tuple[Dict[str, Dict[str, object]], Tuple[str, ...]]:
    """`(records, not_read)`: one record per day, named `<platform>__<day>`; a day named twice in a file is its later line."""
    shared.require_columns(rows, THE_COLUMNS, "a shop figures file")
    records: Dict[str, Dict[str, object]] = {}
    not_read = []
    for row in rows:
        day = returns.a_day(row["Date"])
        if day is None:
            not_read.append(f"line {row.line}: {row['Date']!r} is not a day this can read")
            continue
        try:
            views, orders = shared.a_figure(row["Views"], whole=True), shared.a_figure(row["Orders"], whole=True)
        except ValueError as wrong:
            not_read.append(f"line {row.line}: {wrong}")
            continue
        record: Dict[str, object] = {"platform": platform, "report": report_id, "day": day, "fileDay": file_day}
        if views is not None:
            record["views"] = int(views)
        if orders is not None:
            record["orders"] = int(orders)
        record["digest"] = shared.the_digest(record)
        if f"{platform}__{day}" in records:
            not_read.append(f"line {row.line}: {day} is named twice in this file, so the later line stands")
        records[f"{platform}__{day}"] = record
    return records, tuple(not_read)


# ---------------------------------------------------------------- AMAZON'S ACCOUNT HEALTH (N018)
# **THE FIGURES ARE FROM HIS OWN ACCOUNT HEALTH PAGE (seen 26 Oct 2026: rating 204; order defect 0%, late dispatch 1.8% against a 2% target, pre-fulfilment cancel 0%, valid tracking 100%)**, written by the walk as the day's
# own one-row file (his D473: a running list is never read again). It is the same kind of fact as Meesho's views -- a figure for the WHOLE SHOP on a day -- so it lands as the same record, `platform_shop_days/amazon__<day>`.
# **A BLANK IS NOTHING, NEVER NOUGHT:** a late dispatch rate of 0 is a good day, a blank is a page that did not draw. A rate below nought or over a hundred percent, or a rating that is not a whole number, is refused by name.
HEALTH_COLUMNS = ("Date", "Account Health Rating", "Order Defect Rate", "Late Dispatch Rate", "Pre-fulfilment Cancel Rate", "Valid Tracking Rate")
_HEALTH_RATES = (("Order Defect Rate", "orderDefectRate"), ("Late Dispatch Rate", "lateDispatchRate"),
                 ("Pre-fulfilment Cancel Rate", "cancelRate"), ("Valid Tracking Rate", "validTrackingRate"))


def read_health_days(report_id: str, platform: str, rows: table.Table, file_day: str) -> Tuple[Dict[str, Dict[str, object]], Tuple[str, ...]]:
    """`(records, not_read)`: one record per day, named `<platform>__<day>`; a day named twice in a file is its later line."""
    shared.require_columns(rows, HEALTH_COLUMNS, "an account health file")
    records: Dict[str, Dict[str, object]] = {}
    not_read = []
    for row in rows:
        day = returns.a_day(row["Date"])
        if day is None:
            not_read.append(f"line {row.line}: {row['Date']!r} is not a day this can read")
            continue
        try:
            rating = shared.a_figure(row["Account Health Rating"], whole=True)
            rates = [(field, shared.a_figure(row[name], most=100)) for name, field in _HEALTH_RATES]
        except ValueError as wrong:
            not_read.append(f"line {row.line}: {wrong}")
            continue
        record: Dict[str, object] = {"platform": platform, "report": report_id, "day": day, "fileDay": file_day}
        if rating is not None:
            record["healthRating"] = int(rating)
        for field, value in rates:
            if value is not None:
                record[field] = float(value)
        record["digest"] = shared.the_digest(record)
        if f"{platform}__{day}" in records:
            not_read.append(f"line {row.line}: {day} is named twice in this file, so the later line stands")
        records[f"{platform}__{day}"] = record
    return records, tuple(not_read)
