"""Reading how each listing is doing -- views, clicks and ad figures -- into one record per listing (plan job 86 part A).

**THE SHAPE IS THE ERP'S, FIXED BY ITS COMMIT 94de631:** one record per `<platform>__<listingId>`, and inside it
`days{yyyy-mm-dd: views, clicks, sales, revenue, adViews, adClicks, adSpend, adSales}`. Different reports fill different
fields of one day (the traffic file fills the first four, an ads file the last four), so a reader here says only the fields
its file states, and the writer (`firestore_door.a_views_sink`) changes only those -- a day's ad figures never undo its views.

**THREE REPORTS, and the columns of each come from the working reference's code that read his real files
(`process.py` in the old dashboard), not from a guess:**

| Report | Listing id | Day | Fields |
|---|---|---|---|
| `fk_views` (rolling, every day inside) | `SKU Id` | `Impression Date` on each row | views `Product Views`, clicks `Product Clicks`, sales `Sales` (units), revenue `Revenue` |
| `fk_ads_fsn` (one day, two title lines) | `Sku Id` | `Start Time` on the first line | adViews `Views`, adClicks `Clicks`, adSpend `Ad Spend`, adSales `Direct Units Sold` + `Indirect Units Sold` |
| `me_ads_catalog` (every day inside) | `Catalog ID` | `Date` on each row | adViews `Views`, adClicks `Clicks`, adSpend `Spend`, adSales `Orders` |

**`adSales` IS UNITS, not money**, matching `sales` beside it (units) and `revenue` (money). It is a reading of the shape
and is put to Control as a question.

**A BLANK IS NOTHING, NEVER NOUGHT.** A cell a platform left empty leaves the field out of that day; the page says "not
fetched yet", not 0. **A NAME THE FILE DOES NOT HAVE STOPS THE FILE** (`table.CannotRead`, naming the columns it does have),
and **a name it has TWICE does too** -- never the first of two. **A ROW WITH A DAY OR A FIGURE THAT IS NOT ONE IS REFUSED BY
NAME** and the rest are read. Two rows for one listing and one day in a file are added together, as the reference did.

Nothing here opens a file, a clock or a connection.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable, Dict, List, Optional, Tuple

import orders
import table

# Whole numbers by nature; the others are money.
COUNTS = frozenset({"views", "clicks", "sales", "adViews", "adClicks", "adSales"})

# How many days a record keeps (the brief's 60), newest first. Kept by the writer, named here so one number serves both.
DAYS_KEPT = 60


@dataclass(frozen=True)
class WhatViewsSaid:
    """One file's figures, by listing and day, and every row it would not take."""

    report: str
    platform: str
    # listing id -> day -> field -> figure
    records: Dict[str, Dict[str, Dict[str, object]]]
    not_read: Tuple[str, ...] = ()
    rows_in_file: int = 0

    @property
    def figures(self) -> int:
        return sum(len(day) for days in self.records.values() for day in days.values())


@dataclass(frozen=True)
class Way:
    """Where one report keeps each thing: column tests, one per thing, each answering whether a column name is the one."""

    platform: str
    listing: Callable[[str], bool]
    day: Optional[Callable[[str], bool]]
    # field -> tests whose cells are added together
    fields: Dict[str, Tuple[Callable[[str], bool], ...]]
    header_row: int


def _is(*names: str) -> Callable[[str], bool]:
    wanted = {n.strip().lower() for n in names}
    return lambda said: said.strip().lower() in wanted


def _has(*words: str) -> Callable[[str], bool]:
    return lambda said: any(w in said.strip().lower() for w in words)


WAYS: Dict[str, Way] = {
    "fk_views": Way(
        "flipkart", _is("SKU Id"), _is("Impression Date"),
        {
            "views": (_is("Product Views"),),
            "clicks": (_is("Product Clicks"),),
            "sales": (_is("Sales"),),
            "revenue": (_is("Revenue"),),
        },
        header_row=1,
    ),
    "fk_ads_fsn": Way(
        "flipkart", _is("Sku Id"), None,
        {
            "adViews": (_is("Views"),),
            "adClicks": (_is("Clicks"),),
            "adSpend": (_is("Ad Spend"),),
            "adSales": (_is("Direct Units Sold"), _is("Indirect Units Sold")),
        },
        # Two title lines, then the names (the reference skipped two lines).
        header_row=3,
    ),
    "me_ads_catalog": Way(
        "meesho", _has("catalog id", "catalog_id"), _is("Date"),
        {
            "adViews": (_has("views"),),
            "adClicks": (_has("clicks"),),
            "adSpend": (_has("spend"),),
            "adSales": (_has("orders", "order_count"),),
        },
        header_row=1,
    ),
}


def way_for(report_id: str) -> Way:
    found = WAYS.get(report_id)
    if found is None:
        raise table.CannotRead(f"Nothing here knows how to read {report_id!r} into how a listing is doing.")
    return found


def day_in_ads_header(body: bytes) -> Optional[str]:
    """The day an ads FSN file is about: its first line, `Start Time, 2026-06-18 00:00:00`. Nothing when it is not that."""
    first = table.one_line_endings(table.as_text(body)).split("\n", 1)[0]
    parts = first.split(",", 1)
    if len(parts) != 2 or parts[0].strip().lower() != "start time":
        return None
    return orders.the_day_in(parts[1].strip().strip('"'))


def _the_one_column(columns: Tuple[str, ...], test: Callable[[str], bool], what: str) -> str:
    found = [c for c in columns if test(c)]
    if len(found) == 1:
        return found[0]
    if not found:
        raise table.CannotRead(
            f"There is no column for {what} in this file. It has: " + ", ".join(repr(c) for c in columns) + "."
        )
    raise table.CannotRead(
        f"{len(found)} columns could be {what} ({', '.join(repr(c) for c in found)}), so which is meant cannot be decided."
    )


def _a_number(said: str, field: str) -> Optional[Decimal]:
    """A figure, or None for a blank. A word that is not a figure, or a count with a fraction, raises ValueError."""
    if not said.strip():
        return None
    figure = orders.a_figure(said.replace(",", ""))
    if figure is None:
        raise ValueError(f"{said!r} is not a figure")
    try:
        value = Decimal(figure)
    except InvalidOperation as wrong:
        raise ValueError(f"{said!r} is not a figure") from wrong
    if not value.is_finite():
        raise ValueError(f"{said!r} is not a figure a listing can have")
    # A count is never below nought; money can be (a refund or an adjustment is a real negative).
    if field in COUNTS and (value < 0 or value != value.to_integral_value()):
        raise ValueError(f"{said!r} is not a whole number")
    return value


def _clean(value: Decimal, field: str):
    if field in COUNTS:
        return int(value)
    return float(round(value, 2))


def read_views(report_id: str, rows: table.Table, day: Optional[str] = None) -> WhatViewsSaid:
    """One file's rows turned into figures per listing per day.

    `day` is the day a file with no date column is about (the ads FSN file), read by the caller from the file's own first line.
    """
    way = way_for(report_id)
    columns = tuple(rows.columns)
    listing_column = _the_one_column(columns, way.listing, "the listing")
    day_column = _the_one_column(columns, way.day, "the day") if way.day else None
    if day_column is None and day is None:
        raise table.CannotRead(f"{report_id} says no day inside it and none was given, so no figure can be dated.")
    field_columns = {
        field: [_the_one_column(columns, test, field) for test in tests] for field, tests in way.fields.items()
    }

    records: Dict[str, Dict[str, Dict[str, Decimal]]] = {}
    not_read: List[str] = []
    for row in rows:
        listing = row[listing_column].strip()
        if way.platform == "flipkart":
            listing = orders._unwrap_flipkart_sku(listing)
        if not listing:
            not_read.append(f"line {row.line}: no listing named, so the figures on it belong to nothing")
            continue
        if "/" in listing or listing in (".", "..") or (listing.startswith("__") and listing.endswith("__")):
            not_read.append(
                f"line {row.line}: {listing!r} cannot be the name of a record (a slash or a reserved name), so its figures were not kept"
            )
            continue
        when = orders.the_day_in(row[day_column]) if day_column else day
        if when is None:
            not_read.append(f"line {row.line}: {row[day_column]!r} is not a day written year-month-day")
            continue
        said: Dict[str, Decimal] = {}
        try:
            for field, names in field_columns.items():
                parts = [_a_number(row[name], field) for name in names]
                stated = [p for p in parts if p is not None]
                if stated:
                    said[field] = sum(stated, Decimal(0))
        except ValueError as wrong:
            not_read.append(f"line {row.line}: {wrong}")
            continue
        if not said:
            continue
        mine = records.setdefault(listing, {}).setdefault(when, {})
        for field, value in said.items():
            mine[field] = mine.get(field, Decimal(0)) + value

    clean = {
        listing: {when: {f: _clean(v, f) for f, v in fields.items()} for when, fields in days.items()}
        for listing, days in records.items()
    }
    return WhatViewsSaid(
        report=report_id, platform=way.platform, records=clean, not_read=tuple(not_read) + tuple(str(r) for r in rows.refused),
        rows_in_file=len(rows.rows) + len(rows.refused),
    )
