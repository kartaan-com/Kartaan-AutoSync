"""Reading a platform's returns file into one record per returned line (plan jobs 35, 77, 78).

**THE PLATFORM'S OWN WORDS ARE KEPT.** `returnType`, `reason`, `subReason` and `status` are stored exactly as the platform wrote
them (his Valmo rule: a grouping is done when the ERP SHOWS them, never by rewriting what is stored). Nothing here translates a reason.

**THE COLUMNS ARE FROM HIS REAL FILES (2026-10-11/09, `D:\\Kartaan-Samples\\autosync-returns-ads-2026-10-12`):**

| Field | Flipkart `fk_returns` | Meesho `me_returns` | Amazon `az_returns` (tab-separated) |
|---|---|---|---|
| key | Return ID | Suborder Number | Amazon RMA ID |
| orderId | Order ID | Suborder Number (the ledger's `Sub Order No`) | Order ID |
| sku | SKU | SKU | Merchant SKU |
| trackingId | Tracking ID | AWB Number | Tracking ID |
| qty | Quantity | Qty | Return quantity |
| returnType | Return Type | Type of Return | Return type |
| reason | Return Reason | Return Reason | Return Reason |
| subReason | Return Sub-reason | Detailed Return Reason | -- |
| status | Completion Status | -- | Return request status |
| startedOn | Return Requested Date | Return Created Date | Return request date |
| closedOn | Completed Date | Delivered Date | Return delivery date |

**A BLANK IS NOTHING, NEVER NOUGHT OR AN EMPTY WORD:** a cell the platform left empty leaves the field out. **A COLUMN THE FILE LACKS
STOPS THE FILE** in words naming the columns it has (a moved column read as blank is a return quietly losing its reason), and **a
name it has twice stops it too**. **A ROW WITH NO KEY, NO ORDER, OR A DATE THAT IS NOT ONE IS REFUSED BY NAME** and the rest are read.

Nothing here opens a file, a clock or a connection.
"""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

import orders
import records as shared
import sales
import table

# What a record's fields are, in the order they are written. A field outside this list is refused by the writer.
RETURN_FIELDS = (
    "platform", "report", "returnKey", "orderId", "sku", "saleKey", "trackingId", "qty", "returnType", "reason",
    "subReason", "status", "startedOn", "closedOn", "fileDay", "digest",
)

_MONTHS = {
    name: number for number, name in enumerate(
        ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"),
        start=1,
    )
}
_MONTHS.update({name[:3]: number for name, number in list(_MONTHS.items())})
_MONTHS["sept"] = 9

# Flipkart writes `11 October, 2026`; Amazon `09-Oct-2026`; Meesho `2026-10-11`. Any of them may be followed by a time.
_WORDS_DAY = re.compile(r"^(\d{1,2})[ -]([A-Za-z]+),?[ -](\d{4})\b")


def a_day(said: str) -> Optional[str]:
    """`yyyy-mm-dd` from any of the three ways these files write a day, or nothing. **Nothing is guessed:** `26.08.2026` is nothing."""
    text = (said or "").strip()
    found = orders.the_day_in(text)
    if found:
        return found
    words = _WORDS_DAY.match(text)
    if not words:
        return None
    month = _MONTHS.get(words.group(2).lower())
    if month is None:
        return None
    try:
        return date(int(words.group(3)), month, int(words.group(1))).isoformat()
    except ValueError:
        return None


@dataclass(frozen=True)
class Way:
    """Which column says each thing in one report's file. A test per field; `needed` fields stop the file when absent."""

    platform: str
    columns: Dict[str, str]
    needed: Tuple[str, ...]
    header_row: int = 1
    header_starts: Optional[str] = None
    # The key is the ORDER's number, not the return's own (Meesho's Suborder Number): the same key twice with different words is two
    # returns of one sub-order (A87, AU2), not one return named twice.
    key_is_the_order: bool = False


WAYS: Dict[str, Way] = {
    "fk_returns": Way(
        "flipkart",
        {
            "returnKey": "return id", "orderId": "order id", "sku": "sku", "trackingId": "tracking id", "qty": "quantity",
            "returnType": "return type", "reason": "return reason", "subReason": "return sub-reason",
            "status": "completion status", "startedOn": "return requested date", "closedOn": "completed date",
        },
        needed=("returnKey", "orderId", "reason", "closedOn"),
    ),
    "me_returns": Way(
        "meesho",
        {
            "returnKey": "suborder number", "orderId": "suborder number", "sku": "sku", "trackingId": "awb number",
            "qty": "qty", "returnType": "type of return", "reason": "return reason", "subReason": "detailed return reason",
            "startedOn": "return created date", "closedOn": "delivered date",
        },
        needed=("returnKey", "orderId", "reason", "closedOn"),
        # **THE COLUMN NAMES ARE ON LINE 8 TODAY, AFTER A TITLE BLOCK THE PLATFORM MAY LENGTHEN:** found by its first word.
        header_row=8, header_starts="S No", key_is_the_order=True,
    ),
    "az_returns": Way(
        "amazon",
        {
            "returnKey": "amazon rma id", "orderId": "order id", "sku": "merchant sku", "trackingId": "tracking id", "qty": "return quantity",
            "returnType": "return type", "reason": "return reason", "status": "return request status",
            "startedOn": "return request date", "closedOn": "return delivery date",
        },
        needed=("returnKey", "orderId", "reason"),
    ),
}


# **A RETURN WITHOUT AN AMAZON RMA ID IS STILL A RETURN (A81).** Amazon leaves the RMA ID blank on some rows (its `Merchant RMA ID` is
# blank on them too); on run #19's files one real return (24 Sep) and one rejected return (11 Oct) were dropped for it. Such a row is
# named by what is certain about it instead: its order, its SKU and the day the return was requested. The same file read again
# gives the same name (so nothing new is written), and a row that later gets an RMA ID is folded onto this record by the writer
# (`firestore_door.a_returns_sink`), not made a second return.
NO_RMA = "NORMA"


def a_return_without_an_rma(order: str, sku: str, requested_on: str) -> str:
    """The record name of an Amazon return that has no RMA ID. **Characters a record name should not hold become `_`.**"""
    return "-".join(re.sub(r"[^A-Za-z0-9._-]", "_", part) for part in (NO_RMA, order, sku, requested_on))


def way_for(report_id: str) -> Way:
    found = WAYS.get(report_id)
    if found is None:
        raise table.CannotRead(f"Nothing here knows how to read {report_id!r} into returns.")
    return found


@dataclass(frozen=True)
class WhatReturnsSaid:
    """One file's returns, by record name, and every row it would not take."""

    report: str
    platform: str
    records: Dict[str, Dict[str, object]]
    not_read: Tuple[str, ...] = ()
    rows_in_file: int = 0


def _the_column(columns: Tuple[str, ...], wanted: str, field: str, needed: bool) -> Optional[str]:
    found = [c for c in columns if c.strip().lower() == wanted]
    if len(found) == 1:
        return found[0]
    if not found:
        if needed:
            raise table.CannotRead(
                f"There is no column called {wanted!r} (for {field}) in this file. It has: "
                + ", ".join(repr(c) for c in columns) + "."
            )
        return None
    raise table.CannotRead(
        f"{len(found)} columns are called {wanted!r} (for {field}), so which is meant cannot be decided."
    )


def _a_count(said: str) -> Optional[int]:
    text = (said or "").strip()
    if not text:
        return None
    try:
        value = Decimal(text.replace(",", ""))
    except InvalidOperation:
        raise ValueError(f"{said!r} is not a quantity") from None
    if not value.is_finite() or value < 0 or value != value.to_integral_value():
        raise ValueError(f"{said!r} is not a whole quantity")
    return int(value)


def read_returns(report_id: str, rows: table.Table, file_day: str) -> WhatReturnsSaid:
    """One file's rows turned into returned lines. `file_day` is the day in the file's name, kept as `fileDay`."""
    way = way_for(report_id)
    columns = tuple(rows.columns)
    where = {
        field: _the_column(columns, wanted, field, field in way.needed) for field, wanted in way.columns.items()
    }
    records: Dict[str, Dict[str, object]] = {}
    not_read: List[str] = []
    count = 0
    for row in rows:
        count += 1

        def said(field: str) -> str:
            column = where.get(field)
            return row[column].strip() if column else ""

        order = said("orderId")
        sku = said("sku")
        if way.platform == "flipkart":
            sku = orders._unwrap_flipkart_sku(sku)
        key = said("returnKey")
        if way.platform == "amazon" and order and not key and sku and a_day(said("startedOn")):
            key = a_return_without_an_rma(order, sku, a_day(said("startedOn")))
        if not order or not key:
            not_read.append(f"line {row.line}: no order or return named, so the return belongs to nothing")
            continue
        if "/" in key or key in (".", "..") or (key.startswith("__") and key.endswith("__")):
            not_read.append(f"line {row.line}: {key!r} cannot be the name of a record (a slash or a reserved name)")
            continue
        record: Dict[str, object] = {
            "platform": way.platform, "report": report_id, "returnKey": key, "orderId": order,
            "saleKey": sales.name_for(way.platform, order, sku), "fileDay": file_day,
        }
        if sku:
            record["sku"] = sku
        try:
            for field in ("trackingId", "returnType", "reason", "subReason", "status"):
                if said(field):
                    record[field] = said(field)
            qty = _a_count(said("qty"))
            if qty is not None:
                record["qty"] = qty
            for field in ("startedOn", "closedOn"):
                if said(field):
                    day = a_day(said(field))
                    if day is None:
                        raise ValueError(f"{said(field)!r} is not a day this can read ({field})")
                    record[field] = day
        except ValueError as wrong:
            not_read.append(f"line {row.line}: {wrong}")
            continue
        record["digest"] = shared.the_digest(record)
        name = f"{way.platform}__{key}"
        if (way.key_is_the_order and name in records and records[name]["digest"] != record["digest"]
                and records[name].get("startedOn") != record.get("startedOn")):
            # **A SUB-ORDER RETURNED TWICE KEEPS BOTH RETURNS (A87, AU2: 334340762231555264_1, returned 8 Oct and again 11 Oct).** The
            # earlier return keeps the plain name every earlier night wrote it under; a later one is named by the day it was requested.
            earlier, later = sorted((records[name], record), key=lambda r: (str(r.get("startedOn", "")), r["digest"]))
            records[name] = earlier
            name = f"{name}~{later.get('startedOn') or later['digest'][:8]}"
            if name in records:
                if records[name]["digest"] != later["digest"]:
                    not_read.append(f"line {row.line}: {key!r} is returned a third time on the same day with different words, so only the first was kept")
                continue
            record = later
            records[name] = record
            continue
        if name in records:
            # **THE SAME RETURN TWICE WITH THE SAME WORDS IS ONE RETURN; WITH DIFFERENT WORDS IT IS SAID, never silently the first.**
            if records[name]["digest"] != record["digest"]:
                not_read.append(f"line {row.line}: {key!r} is named twice in this file with different words, so only the first was kept")
            continue
        records[name] = record
    return WhatReturnsSaid(report_id, way.platform, records, tuple(not_read), count)
