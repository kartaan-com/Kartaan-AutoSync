"""Reading Meesho's product-performance file into one record per product per week (A87, D459; plan piece 44).

**THE COLUMNS ARE FROM HIS ONE REAL FILE** (`meesho_me_product_performance_2026-10-19.csv`, 144 rows, one week `13th Oct '26 - 19th Oct '26`):
`Product` (the listing's long title), `Catalog ID` (BLANK on every row of that file), `Rating` (a star level, blank when the product has none),
`Views` and `Conversions` (each two figures joined by ` | `), `Clicks`, `Orders`, `Sales` (a rupee sign then `12,916.00`) and `Returns` (a percentage).

**WHAT IS AND IS NOT CLAIMED.** The first figure of `Views` is the views and the first of `Conversions` is the conversion rate. The platform's page does
not say what the SECOND figure means (it looks like a change against another period), so it is kept as the platform wrote it under its own name
(`viewsOther`, `conversionOther`) and never read as anything. Nothing is summed: a week's figures are the week's, and two overlapping weeks are two records.

**MATCHED TO A CATALOG BY TITLE (D459).** Meesho's file carries no catalog id, so the product's title is looked up among the titles of the seller's own
Meesho listings (`me_catalog`). A title that belongs to exactly one catalog gives that `catalogId`; a title that belongs to several catalogs is
kept with the number said; a title nobody has is kept and flagged `not matched to a catalog`. **Nothing is dropped for not matching.**

Nothing here opens a file, a clock or a connection.
"""

import hashlib
import re
from datetime import date
from decimal import Decimal
from typing import Dict, FrozenSet, Optional, Tuple

import firestore
import records as shared
import returns
import table

THE_COLUMNS = ("Range", "Product", "Views", "Clicks", "Orders", "Conversions", "Sales", "Returns")
# What a record holds, in the order it is written (a field outside this list is refused by the writer).
PERFORMANCE_FIELDS = (
    "platform", "report", "product", "weekFrom", "weekTo", "catalogId", "matched", "note", "rating", "views", "viewsOther", "clicks", "orders",
    "conversion", "conversionOther", "sales", "returnsPct", "fileDay", "digest",
)
KIND = shared.RecordKind(firestore.PERFORMANCE, PERFORMANCE_FIELDS, "product week", required_days=("weekFrom", "weekTo", "fileDay"))
NOT_MATCHED = "not matched to a catalog"

_DAY = re.compile(r"(\d{1,2})(?:st|nd|rd|th)\s+([A-Za-z]{3,9})\s+'(\d{2})")


def a_week(said: str) -> Optional[Tuple[str, str]]:
    """`(from, to)` as `yyyy-mm-dd` out of `13th Oct '26 - 19th Oct '26`, or nothing. **Nothing is guessed.**"""
    found = _DAY.findall(said or "")
    if len(found) != 2:
        return None
    days = []
    for number, month, year in found:
        at = returns._MONTHS.get(month.lower())
        if at is None:
            return None
        try:
            days.append(date(2000 + int(year), at, int(number)).isoformat())
        except ValueError:
            return None
    return days[0], days[1]


def _two_figures(said: str) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    parts = [p.strip() for p in (said or "").split("|")]
    if len(parts) > 2:
        raise ValueError(f"{said!r} has more than two figures")
    first = shared.a_figure(parts[0])
    return first, shared.a_figure(parts[1], negative=True) if len(parts) == 2 else None


def _plain(value: Decimal):
    return int(value) if value == value.to_integral_value() else float(round(value, 2))


def titles_of(listings: Dict[str, Dict[str, object]]) -> Dict[str, FrozenSet[str]]:
    """The seller's own Meesho listings as `lower-cased title -> the catalog ids that title belongs to`."""
    out: Dict[str, set] = {}
    for one in listings.values():
        title = str(one.get("productName") or "").strip().lower()
        if title:
            out.setdefault(title, set()).add(str(one.get("catalogId") or ""))
    return {title: frozenset(ids) for title, ids in out.items()}


def read_performance(report_id: str, platform: str, rows: table.Table, file_day: str, titles: Dict[str, FrozenSet[str]]):
    """`(records, not_read)`: one record per product row, named `<platform>__<week end>__<fingerprint of the title>`."""
    shared.require_columns(rows, THE_COLUMNS, "a product performance file")
    records: Dict[str, Dict[str, object]] = {}
    not_read = []
    seen: Dict[str, int] = {}
    for row in rows:
        product = row["Product"].strip()
        week = a_week(row["Range"])
        if not product or week is None:
            not_read.append(f"line {row.line}: no product, or a week that is not one this can read ({row['Range']!r})")
            continue
        record: Dict[str, object] = {
            "platform": platform, "report": report_id, "product": product, "weekFrom": week[0], "weekTo": week[1], "fileDay": file_day,
        }
        try:
            views, views_other = _two_figures(row["Views"])
            conversion, conversion_other = _two_figures(row["Conversions"])
            figures = {
                "views": views, "viewsOther": views_other, "conversion": conversion, "conversionOther": conversion_other,
                "clicks": shared.a_figure(row["Clicks"]), "orders": shared.a_figure(row["Orders"]), "sales": shared.a_figure(row["Sales"]),
                "returnsPct": shared.a_figure(row["Returns"]),
                "rating": shared.a_figure(row["Rating"]) if "Rating" in rows.columns else None,
            }
        except ValueError as wrong:
            not_read.append(f"line {row.line}: {wrong}")
            continue
        for field, value in figures.items():
            if value is not None:
                record[field] = _plain(value)
        ids = titles.get(product.lower(), frozenset())
        if len(ids) == 1:
            record["catalogId"], record["matched"] = next(iter(ids)), True
        else:
            record["matched"] = False
            record["note"] = NOT_MATCHED if not ids else f"the title belongs to {len(ids)} catalogs, so which one is meant cannot be said"
        record["digest"] = shared.the_digest(record)
        base = f"{platform}__{week[1]}__{hashlib.sha1(product.encode('utf-8')).hexdigest()[:12]}"
        # Two rows with one title in a week (three in his file) are two records, never one lost.
        seen[base] = seen.get(base, 0) + 1
        records[base if seen[base] == 1 else f"{base}-{seen[base]}"] = record
    return records, tuple(not_read)
