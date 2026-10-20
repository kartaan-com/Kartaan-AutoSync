"""Reading a platform's claims file into one claim per order, for the ledger's claim columns (plan job 78; Meesho first, A87).

**THE COLUMNS ARE FROM HIS REAL FILES** (`meesho_me_claims_2026-10-11.csv` and `..-10-14.csv`, 154 rows): `Ticket ID` is the claim's own id,
`Suborder Number` is the order line, `Ticket Status` is Open / Approved / Rejected, `Created Date` is when the claim was raised and
`Last Update` is the platform's own message. **The file has no SKU** (every one of 154 rows is blank), so a claim is put on the order's one
row and on no other.

**THE SAME CLAIM IS IN MANY FILES (A86: Flipkart's SPF claims download as 30 days ending on the day), AND THE LATEST FILE'S STATUS WINS.** A claim
is known by its Claim ID (Meesho's `Ticket ID`): named twice in one file it is one claim, and across files the ledger's newest-file rule
(`ledger.plan`, rule 2) puts the later status over the earlier. Where one order has two claims, the one raised last is the order's.

**AN AMOUNT IS TAKEN ONLY FROM THE PLATFORM'S OWN WORDS FOR PAYING, NEVER GUESSED:** `Your claim payment of Rs 177.84 for this order was done on ...`
on an Approved claim. Any other message leaves the recovered amount blank (a rejection says no money came).

Nothing here opens a file, a clock or a connection.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Tuple
from dataclasses import dataclass

import table
from sales import Sale
from table import Row, Table

THE_COLUMNS = ("Suborder Number", "Ticket ID", "Ticket Status", "Created Date", "Last Update")
_PAID = re.compile(r"^\s*Your claim payment of Rs\s*([0-9][0-9,]*(?:\.[0-9]+)?) for this order was done on\b")


@dataclass(frozen=True)
class WhatClaimsSaid:
    """The claims one file named, one per order, and every row it would not take."""

    sales: Tuple[Sale, ...]
    not_read: Tuple[str, ...] = ()
    rows_in_file: int = 0


def the_amount_paid(message: str, status: str) -> str:
    """The rupees the platform says it paid on an Approved claim, as text, or nothing."""
    if (status or "").strip().lower() != "approved":
        return ""
    found = _PAID.match(message or "")
    if not found:
        return ""
    try:
        return str(Decimal(found.group(1).replace(",", "")))
    except InvalidOperation:
        return ""


def read_claims(platform: str, rows: Table, file_day: str) -> WhatClaimsSaid:
    """One file's claims. A file lacking a column it cannot be read without is refused in words naming the columns it has."""
    missing = [c for c in THE_COLUMNS if c not in rows.columns]
    if missing:
        raise table.CannotRead(
            "This does not look like a claims file. It has no " + ", ".join(repr(c) for c in missing)
            + ". It has: " + ", ".join(repr(c) for c in rows.columns if c) + ". Nothing was read."
        )
    claims: Dict[str, Tuple[str, str, Row]] = {}
    not_read: List[str] = []
    count = 0
    for row in rows:
        count += 1
        order, claim = row["Suborder Number"].strip(), row["Ticket ID"].strip()
        if not order or not claim:
            not_read.append(f"line {row.line}: no order or claim id, so the claim belongs to nothing")
            continue
        # A claim named twice in one file is one claim: the later line stands.
        claims[claim] = (order, row["Created Date"].strip(), row)
    by_order: Dict[str, Tuple[str, str, Row]] = {}
    for claim, (order, raised, row) in sorted(claims.items()):
        held = by_order.get(order)
        if held is None or (raised, claim) > (held[1], held[0]):
            by_order[order] = (claim, raised, row)
    out = tuple(
        Sale(
            platform=platform, order_id=order, sku="", claim_id=claim, claim_status=row["Ticket Status"].strip() or None,
            claim_recovered=the_amount_paid(row["Last Update"], row["Ticket Status"]) or None, claims_on=file_day,
        )
        for order, (claim, _, row) in sorted(by_order.items())
    )
    return WhatClaimsSaid(out, tuple(not_read), count)


def a_table_to_ask_with() -> Table:
    """A one-line claims table built out of the reader's own column names, for driving the reader without a file."""
    from table import where_each_column_is  # noqa: PLC0415 - kept beside its one use

    names = THE_COLUMNS
    where, ambiguous = where_each_column_is(names)
    said = {"Suborder Number": "asking-whether-a-file-says-which-day-it-is", "Ticket ID": "1", "Ticket Status": "Open"}
    cells = tuple(said.get(name, "") for name in names)
    return Table(columns=tuple(names), rows=(Row(line=2, cells=cells, _where=where, _ambiguous=ambiguous),))
