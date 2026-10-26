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
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

import firestore
import records as shared
import returns
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


# What a claim's record holds, in the order it is written (a field outside this list is refused by the writer). **The platform's own long message is
# not kept** -- it can be a page of HTML; what it says about being paid is the amount, taken by `the_amount_paid`.
CLAIM_FIELDS = ("platform", "report", "claimKey", "orderId", "status", "raisedOn", "issue", "recovered", "recoveredWas", "fileDay", "digest")
KIND = shared.RecordKind(firestore.CLAIMS, CLAIM_FIELDS, "claim", days=("raisedOn", "fileDay"))


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
    shared.require_columns(rows, THE_COLUMNS, "a claims file")
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


# ---------------------------------------------------------------- FLIPKART (v0.1.21 job 3)
# **THE SHAPE IS FROM HIS REAL FILE** (`flipkart_claim_report_till_2026-05-27.xlsx`): sheets `Help` (skipped), `Seller Claims` and
# `Auto-Approved Claims` (his own Help sheet calls them "Seller Raised Claims" and "Auto Approved Claims", so either spelling is found).
# The seller sheet has an Approved Amount and no Pay/Recovery column; the auto sheet has both, and the real file only shows `PAY`.
FLIPKART_SELLER_COLUMNS = ("Claim ID", "Order Id", "Order Item ID", "Updated at", "Claim Status", "Approved Amount")
FLIPKART_AUTO_COLUMNS = ("Claim ID", "Order Id", "Order Item ID", "Claim Processing Date", "Claim Status", "Approved Amount", "Pay/Recovery")


def flipkart_sheet_names(names) -> Tuple[Optional[str], Optional[str]]:
    """`(seller claims sheet, auto-approved claims sheet)` out of a workbook's sheet names, either one absent; neither is refused in words.

    A sheet is told by its name containing `claim` and then `seller` or `auto`: `Help` and every other sheet are never read.
    """
    seller = auto = None
    for name in names:
        words = re.sub(r"[^a-z]+", " ", name.lower())
        if "claim" not in words:
            continue
        if "auto" in words and auto is None:
            auto = name
        elif "seller" in words and seller is None:
            seller = name
    if seller is None and auto is None:
        raise table.CannotRead(
            "This does not look like Flipkart's claims file. It has no 'Seller Claims' or 'Auto-Approved Claims' sheet. It has: "
            + ", ".join(repr(n) for n in names) + ". Nothing was read."
        )
    return seller, auto


def read_flipkart_claims(seller: Optional[Table], auto: Optional[Table], file_day: str) -> WhatClaimsSaid:
    """One Flipkart claims workbook's claims, one per order, from its two claim sheets (either may be missing; a header with no rows is fine).

    **PAY IS PLUS AND RECOVER IS MINUS (auto sheet only)**; a seller-sheet claim has no Pay/Recovery column, and its Approved Amount is
    money paid. **Only an `Approved` claim carries rupees** (a Not Approved or In Processing claim's amount is never counted). **ORDER ITEM `NA`
    IS STOCK FLIPKART HOLDS, with no order to put the claim on: it is kept aside and said, never dropped silently.** A claim id named twice
    is one claim, the newer line standing. **ONE ORDER WITH SEVERAL CLAIMS:** the newest claim's id and status stand, and the rupees are the
    net of every approved claim (paid minus recovered). Whether an order has one ledger row to put it on is the ledger's question, not this one's.
    """
    if seller is not None:
        shared.require_columns(seller, FLIPKART_SELLER_COLUMNS, "Flipkart's seller claims sheet")
    if auto is not None:
        shared.require_columns(auto, FLIPKART_AUTO_COLUMNS, "Flipkart's auto-approved claims sheet")
    # claim id -> (newest-first key, order, status, signed rupees or None)
    found: Dict[str, Tuple[Tuple[str, int], str, str, Optional[Decimal]]] = {}
    not_read: List[str] = []
    count = 0
    for label, rows, when_column in (("seller claims", seller, "Updated at"), ("auto-approved claims", auto, "Claim Processing Date")):
        if rows is None:
            continue
        for row in rows:
            count += 1
            order, item, claim = row["Order Id"].strip(), row["Order Item ID"].strip(), row["Claim ID"].strip()
            where = f"line {row.line} of the {label} sheet"
            if not claim or not order:
                not_read.append(f"{where}: no order or claim id, so the claim belongs to nothing")
                continue
            if order.upper() == "NA" or item.upper() == "NA":
                not_read.append(
                    f"{where}: claim {claim} names order item 'NA' -- stock Flipkart holds, with no order, so it belongs to no order and is kept aside"
                )
                continue
            status = row["Claim Status"].strip()
            money: Optional[Decimal] = None
            if status.lower() == "approved":
                try:
                    amount = shared.a_figure(row["Approved Amount"])
                except ValueError as wrong:
                    not_read.append(f"{where}: claim {claim}'s Approved Amount: {wrong}")
                    continue
                if amount is not None:
                    if rows is auto:
                        way = row["Pay/Recovery"].strip().upper()
                        if way == "PAY":
                            money = amount
                        elif way.startswith("RECOVER"):
                            money = -amount
                        else:
                            not_read.append(
                                f"{where}: claim {claim}'s Pay/Recovery says {row['Pay/Recovery'].strip()!r}, which is neither Pay nor Recover, so its rupees are not guessed"
                            )
                            continue
                    else:
                        money = amount
            key = (row[when_column].strip(), row.line)
            held = found.get(claim)
            if held is None or key >= held[0]:
                found[claim] = (key, order, status, money)
    by_order: Dict[str, List[Tuple[str, Tuple[str, int], str, Optional[Decimal]]]] = {}
    for claim, (key, order, status, money) in found.items():
        by_order.setdefault(order, []).append((claim, key, status, money))
    out = []
    for order, mine in sorted(by_order.items()):
        newest = max(mine, key=lambda one: (one[1][0], one[0]))
        paid = [one[3] for one in mine if one[3] is not None]
        out.append(Sale(
            platform="flipkart", order_id=order, sku="", claim_id=newest[0], claim_status=newest[2] or None,
            claim_recovered=str(sum(paid, Decimal(0))) if paid else None, claims_on=file_day,
        ))
    return WhatClaimsSaid(tuple(out), tuple(not_read), count)


def read_claim_records(report_id: str, platform: str, rows: Table, file_day: str, context=None):
    """`(records, rows refused)`: every claim a file names, as a record each, by record name `<platform>__<claim id>` (D459).

    **THE CLAIM'S OWN ID NAMES IT**, so the same claim in many files (30-day downloads) is one record, and the latest file's status wins in the
    writer. It carries the sub-order it is about and is never tied to an order row. **`Approved, will be settled` has no `recovered` until a
    later file gives it.** The file's columns are checked by `read_claims`, which is asked first.
    """
    read_claims(platform, rows, file_day)  # refuses a file without the columns, in words
    records: Dict[str, Dict[str, object]] = {}
    not_read = []
    for row in rows:
        order, claim = row["Suborder Number"].strip(), row["Ticket ID"].strip()
        if not order or not shared.a_safe_name(claim):
            not_read.append(f"line {row.line}: no order, or a claim id that cannot name a record, so the claim belongs to nothing")
            continue
        record: Dict[str, object] = {
            "platform": platform, "report": report_id, "claimKey": claim, "orderId": order, "fileDay": file_day,
        }
        status = row["Ticket Status"].strip()
        if status:
            record["status"] = status
        raised = returns.a_day(row["Created Date"])
        if raised:
            record["raisedOn"] = raised
        issue = row["Issue"].strip() if "Issue" in rows.columns else ""
        if issue:
            record["issue"] = issue
        paid = the_amount_paid(row["Last Update"], status)
        if paid:
            record["recovered"] = paid
        record["digest"] = shared.the_digest(record)
        records[f"{platform}__{claim}"] = record
    return records, tuple(not_read)


AMAZON_SAFET_COLUMNS = ("Order ID", "SAFE-T Claim ID", "Claim Date", "SAFE-T claim state", "Claim Filing Reason", "Total Reimbursement amount")


def read_safet_records(report_id: str, platform: str, rows: Table, file_day: str, context=None):
    """`(records, rows refused)`: every claim Amazon's SAFE-T report names, as a record each, by record name `<platform>__<SAFE-T claim id>` (N018, his ruling D726; D459).

    **THE COLUMNS ARE FROM HIS REAL FILE** (Manage SAFE-T claims > Download the SAFE-T Report, type "SAFE-T Claims", seen 26 Oct 2026: 20 columns, one claim in 60 days).
    **THE CLAIM'S OWN ID NAMES IT**, so the same claim in many overlapping files is one record and the latest file's state wins in the writer, exactly as for Meesho. It carries the
    order it is about and is never tied to an order row. **THE RUPEES ARE AMAZON'S OWN `Total Reimbursement amount`, TAKEN ONLY FOR A `Granted` CLAIM**: a claim under
    investigation or denied has none, and a figure that cannot be read is refused by name rather than guessed.
    """
    shared.require_columns(rows, AMAZON_SAFET_COLUMNS, "Amazon's SAFE-T claims report")
    made: Dict[str, Dict[str, object]] = {}
    not_read = []
    for row in rows:
        order, claim = row["Order ID"].strip(), row["SAFE-T Claim ID"].strip()
        if not order or not shared.a_safe_name(claim):
            not_read.append(f"line {row.line}: no order, or a claim id that cannot name a record, so the claim belongs to nothing")
            continue
        record: Dict[str, object] = {"platform": platform, "report": report_id, "claimKey": claim, "orderId": order, "fileDay": file_day}
        status = row["SAFE-T claim state"].strip()
        if status:
            record["status"] = status
        raised = returns.a_day(row["Claim Date"])
        if raised:
            record["raisedOn"] = raised
        issue = row["Claim Filing Reason"].strip()
        if issue:
            record["issue"] = issue
        if status.lower() == "granted":
            try:
                paid = shared.a_figure(row["Total Reimbursement amount"])
            except ValueError as wrong:
                not_read.append(f"line {row.line}: claim {claim}'s Total Reimbursement amount: {wrong}")
                continue
            if paid is not None and paid > 0:
                record["recovered"] = str(paid)
        record["digest"] = shared.the_digest(record)
        made[f"{platform}__{claim}"] = record
    return made, tuple(not_read)


def merge(record: Dict[str, object], held) -> Dict[str, object]:
    """The record with the rupees already held for this claim kept (`held` is the record in the database, or nothing)."""
    held = held or {}
    return keeping_what_was_paid(record, str(held.get("recovered") or ""), str(held.get("recoveredWas") or ""))


def keeping_what_was_paid(record: Dict[str, object], recovered_before: str, was_before: str = "") -> Dict[str, object]:
    """The record with the rupees already recorded for this claim kept. **A PAID CLAIM NEVER LOSES ITS RUPEES (his ruling, 20 Oct).**

    A later file that says nothing about the amount, or words it so that none can be taken, leaves the recorded amount standing; a different
    amount replaces it and the one it replaced is noted in `recoveredWas`. The fingerprint is worked out again, so the same file read twice
    still writes nothing.
    """
    if not recovered_before:
        return record
    kept = dict(record)
    if not kept.get("recovered"):
        kept["recovered"] = recovered_before
    if str(kept["recovered"]) != str(recovered_before):
        kept["recoveredWas"] = recovered_before
    elif was_before:
        # The same amount again: the note of what it replaced stands, or the next run would drop it.
        kept["recoveredWas"] = was_before
    kept["digest"] = shared.the_digest(kept)
    return kept


def a_table_to_ask_with(platform: str = "meesho") -> Table:
    """A one-line claims table built out of the reader's own column names, for driving the reader without a file (Flipkart's: its seller sheet)."""
    from table import where_each_column_is  # noqa: PLC0415 - kept beside its one use

    names = FLIPKART_SELLER_COLUMNS if platform == "flipkart" else THE_COLUMNS
    where, ambiguous = where_each_column_is(names)
    said = {"Suborder Number": "asking-whether-a-file-says-which-day-it-is", "Ticket ID": "1", "Ticket Status": "Open",
            "Order Id": "asking-whether-a-file-says-which-day-it-is", "Claim ID": "1", "Order Item ID": "1", "Claim Status": "Open"}
    cells = tuple(said.get(name, "") for name in names)
    return Table(columns=tuple(names), rows=(Row(line=2, cells=cells, _where=where, _ambiguous=ambiguous),))
