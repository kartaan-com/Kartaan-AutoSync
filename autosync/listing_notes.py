"""What a platform's side file says ABOUT a listing, read into the fields put beside that listing's record (v0.1.21 lane 2, AP9).

**A NOTE IS NOT A LISTING.** A listing file says what is for sale; these files say something about a listing that file already named:
Amazon's Suppressed Listings Report says which listings are hidden from buyers and why. The note goes on the listing's own record
(`firestore.a_listing_note_write`) under its own field names, with a mask, so the listing file and the note file never erase each other.

**THE SUPPRESSED LISTINGS REPORT (`GET_MERCHANTS_LISTINGS_FYP_REPORT`), from Amazon's own page**
(developer-docs.amazon/sp-api/docs/report-type-values-inventory, "Suppressed Listings Report", read 23 Oct 2026, Rule 1): a tab-delimited
flat file with eight attributes, in this order -- Status, Reason, SKU, ASIN, Product name, Condition, Status Change Date, Issue Description --
that **"includes a UTF-8 Byte Order Mark (BOM) as the first 3 bytes"**, and whose **headers may come back in a different locale than the one
asked for** (the page: reports are not cached by locale). **THE PAGE GIVES NO SAMPLE AND NO LIST OF THE WORDS IN `Status`**, and no real file
of his has been fetched yet (plan sample A5), so: **columns are taken BY POSITION, never by name**, and only the two that decide the record's
name (SKU, ASIN) are cross-checked -- if the header carries either of those words in English anywhere but its place, the file is refused.
`Status` is not read: every row of this report is a suppressed listing, and nothing documented says another status can be in it.
"""

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import listings
import records as shared
import table

# The place of each column in the file, counting from nought, as Amazon's page orders them.
THE_PLACE_OF = {"reason": 1, "sku": 2, "asin": 3, "issue": 7}
HOW_MANY_COLUMNS = 8
# The longest a name can be and the same for the record's id: a slash or a longer one cannot be a record's name. listings.py's own, so the two readers agree.
_LONGEST_ID = listings._LONGEST_ID


@dataclass(frozen=True)
class WhatNotesSaid:
    """One side file's notes (the listing's record id -> the fields to put beside it) and every row it would not take."""

    notes: Dict[str, Dict]
    not_read: Tuple[str, ...]
    rows_in_file: int


def read_suppressed(content: bytes, report_name: str = "this file") -> WhatNotesSaid:
    """Amazon's Suppressed Listings Report as notes: `suppressed`, `suppressedReason` and `fixHint` for each listing it names.

    The record id is the listing's own (`amazon::ASIN::seller-sku`, D326). `suppressedReason` is the `Reason` column and `fixHint` is
    `Issue Description`: the words Amazon gives for what to put right, kept as Amazon wrote them.

    **A FILE WITH ITS HEADINGS AND NO ROW IS NOT REFUSED** (the opposite of a listing file): a seller with nothing hidden may well get
    exactly that, and refusing it would leave the file unread and the board red for good news. A file with nothing in it at all is refused.
    """
    rows = table.read(content, header_row=1)
    heads = rows.columns
    if len(heads) < HOW_MANY_COLUMNS:
        raise table.CannotRead(
            f"The Amazon suppressed listings file {report_name} has {len(heads)} columns and Amazon's page names {HOW_MANY_COLUMNS}. "
            "Nothing was read. Download the report again; if it still says this, Amazon has changed its file and Kartaan needs to be told."
        )
    for word, place in (("sku", THE_PLACE_OF["sku"]), ("asin", THE_PLACE_OF["asin"])):
        at = [i for i, name in enumerate(heads) if name.strip().lower() == word]
        if at and at != [place]:
            raise table.CannotRead(
                f"{report_name} puts its {word.upper()} column at {' and '.join(str(i + 1) for i in at)}, and Amazon's page puts it at {place + 1}. "
                "Nothing was read, because reading by position would put one column's words on another. Kartaan needs to be told."
            )
    notes: Dict[str, Dict] = {}
    not_read = []
    seen_at: Dict[str, int] = {}
    for row in rows:
        cells = row.cells
        sku, asin = cells[THE_PLACE_OF["sku"]].strip(), cells[THE_PLACE_OF["asin"]].strip()
        if not sku or not re.match(r"^[A-Za-z0-9]+$", asin) or "/" in sku or len(sku.encode("utf-8")) > _LONGEST_ID:
            not_read.append(
                f"line {row.line} ({sku or 'no SKU'}): this row has no ASIN and seller SKU that could name a listing, so the suppression "
                "could not be put on one"
            )
            continue
        name = f"amazon::{asin}::{sku}"
        if name in seen_at:
            not_read.append(f"line {row.line} ({sku}): line {seen_at[name]} already names the same listing. Only the first was kept")
            continue
        seen_at[name] = row.line
        notes[name] = {
            "suppressed": True,
            "suppressedReason": cells[THE_PLACE_OF["reason"]].strip(),
            "fixHint": cells[THE_PLACE_OF["issue"]].strip(),
        }
    # **A ROW OF THE WRONG WIDTH IS A ROW NOT READ** (table.read keeps it in `refused`): left out, a file with a torn row would read as read in full.
    not_read += [f"line {one.line}: {one.why}" for one in rows.refused]
    return WhatNotesSaid(notes=notes, not_read=tuple(not_read), rows_in_file=len(rows) + len(rows.refused))


def notes_from_fees(fees_said) -> WhatNotesSaid:
    """Amazon's referral fee per listing (what lane 1's `listings.read_fee_preview` answers) as notes: `referralFee` on each listing's record.

    **WRITTEN AGAINST THE SHAPE LANE 1 DOCUMENTS (DONE_AP8), AS LANE 2'S HALF (AP9):** `fees_said.fees` is `{amazon::ASIN::seller-sku: the fee per item}`, `.not_read`
    the rows it would not take and `.rows_in_file` the rows in the file. `read_fees` below joins the two (AP10). **A fee of 0.00 is kept: it is a figure Amazon gave.** `feeAsOf`, the file's day, is added by the sink, as `suppressedOn` is.
    """
    return WhatNotesSaid(
        notes={name: {"referralFee": fee} for name, fee in fees_said.fees.items()},
        not_read=tuple(fees_said.not_read),
        rows_in_file=fees_said.rows_in_file,
    )


def read_fees(content: bytes, report_name: str = "this file") -> WhatNotesSaid:
    """Amazon's Referral Fee Preview file's bytes, read by lane 1's `listings.read_fee_preview`, as `referralFee` notes (the two lanes joined at AP10)."""
    return notes_from_fees(listings.read_fee_preview(table.read(content, header_row=1), report_name))


# **MEESHO'S PRICING TABLE (N017, his D726; plan piece 43): current customer price, recommended customer price and Meesho's own label, on each Meesho listing.**
#
# **THE FILE IS THE EXTENSION'S OWN** -- `extension/tables.js` reads Meesho's pricing page page by page and writes `Product`, `Catalog ID`, `SKU ID`, `Tab counts`,
# `Current Stock`, `Growth in 30 days`, `Current Customer Price`, `Recommended Customer Price`, `Insights`. **NO PRICING FILE HAS EVER LANDED IN HIS DRIVE** (the fetch
# failed every night from 5 Oct to 25 Oct), so what a cell holds beyond its first piece is not known. Therefore: **only the FIRST piece of a price cell (before a ` | `) is
# read, as an amount, and a cell whose first piece is not an amount makes its row a row not read -- never a guess.** The label is the `Insights` cell as the page wrote it.
# `Tab counts` (the page's chips, the same on every row) and the stock and growth cells are not read.
#
# **HOW A ROW FINDS ITS LISTINGS: by `SKU ID` against the listing's SKU (the catalogue file's `STYLE ID`); a row whose SKU no listing has falls back to its `Catalog ID`
# against the listing's catalogue id; a row with neither is matched by its title when the title belongs to exactly one catalogue (the way product performance is matched, D459).**
# A row whose SKU and catalogue id point at different catalogues is not matched: which is meant cannot be said. One row's figures go on EVERY listing it finds (the page
# prices a product; its sizes are listings of it). Meesho's `Catalog ID` was BLANK on every row of the product performance file, so the SKU and the title carry the match.
PRICING_COLUMNS = ("Product", "Catalog ID", "SKU ID", "Current Customer Price", "Recommended Customer Price", "Insights")


def _first_piece_amount(said: str, what: str) -> Optional[object]:
    """The amount in the first piece of a price cell, or None for a blank cell. Raises ValueError saying what it read when that is not an amount."""
    first = (said or "").split("|")[0].strip()
    if not first:
        return None
    try:
        value = shared.a_figure(first)
    except ValueError:
        raise ValueError(f"the {what} reads {first!r}, which is not an amount") from None
    if value is None:
        raise ValueError(f"the {what} reads {first!r}, which is not an amount")
    return int(value) if value == value.to_integral_value() else float(round(value, 2))


def read_pricing(content: bytes, report_name: str = "this file", shop_listings: Optional[Dict[str, Dict]] = None) -> WhatNotesSaid:
    """Meesho's pricing file as notes: `currentPrice`, `recommendedPrice` (null when Meesho gave none) and `priceLabel` on each listing it finds.

    `shop_listings` is the seller's own Meesho listings as `listings.py` reads them (`meesho::<product>::<variation>` -> the listing). **None is refused, not read as
    "nothing sells": a file matched against nothing would flag every row unmatched for good.** A listing named by two rows keeps the first row's figures and says so.
    """
    if shop_listings is None:
        raise table.CannotRead(
            f"The Meesho pricing file {report_name} cannot be matched to the seller's listings yet: the catalogue file holding the listings has not been read. "
            "Nothing was read; this file is left to be read again."
        )
    rows = table.read(content, header_row=1)
    shared.require_columns(rows, PRICING_COLUMNS, "a Meesho pricing file")
    if not len(rows) and not rows.refused:
        raise table.CannotRead(
            f"The Meesho pricing file {report_name} has its column headings and not one product under them. Nothing was read; "
            "an empty file is not the same as a shop with nothing to price."
        )
    by_sku: Dict[str, List[str]] = {}
    by_catalog: Dict[str, List[str]] = {}
    by_title: Dict[str, List[str]] = {}
    for name, one in sorted(shop_listings.items()):
        for index, key in ((by_sku, one.get("sku")), (by_catalog, one.get("catalogId")), (by_title, str(one.get("productName") or "").strip().lower())):
            if key:
                index.setdefault(str(key).strip(), []).append(name)
    notes: Dict[str, Dict] = {}
    not_read: List[str] = []
    seen_at: Dict[str, int] = {}
    for row in rows:
        title, catalog, sku = row["Product"].strip(), row["Catalog ID"].strip(), row["SKU ID"].strip()
        who = f"line {row.line} ({sku or catalog or title or 'no name'})"
        try:
            current = _first_piece_amount(row["Current Customer Price"], "current price") if row["Current Customer Price"].strip() else None
            recommended = _first_piece_amount(row["Recommended Customer Price"], "recommended price") if row["Recommended Customer Price"].strip() else None
        except ValueError as wrong:
            not_read.append(f"{who}: {wrong}, so no price was put on a listing")
            continue
        if current is None:
            not_read.append(f"{who}: this row has no current price, so there is no price to put on a listing")
            continue
        found = None
        for layer, index, key in (("SKU", by_sku, sku), ("catalogue id", by_catalog, catalog)):
            if key and key in index:
                found = (layer, index[key])
                break
        if found and found[0] == "SKU" and catalog and all(
            str(shop_listings[n].get("catalogId") or "").strip() not in ("", catalog) for n in found[1]
        ):
            not_read.append(f"{who}: its SKU and its catalogue id disagree -- the listings with that SKU are in another catalogue -- so which listing is meant cannot be said")
            continue
        if found is None and title and not sku and not catalog:
            names = by_title.get(title.lower(), [])
            catalogs = {str(shop_listings[n].get("catalogId") or "") for n in names}
            if len(catalogs) > 1:
                not_read.append(f"{who}: the title belongs to {len(catalogs)} catalogues, so which one is meant cannot be said")
                continue
            if names:
                found = ("title", names)
        if found is None:
            not_read.append(f"{who}: no listing of the seller's has this SKU, catalogue id or title, so the price could not be put on one")
            continue
        label = row["Insights"].strip()
        for name in found[1]:
            if name in seen_at:
                not_read.append(f"{who}: line {seen_at[name]} already put a price on {name}. Only the first was kept")
                continue
            seen_at[name] = row.line
            notes[name] = {"currentPrice": current, "recommendedPrice": recommended, "priceLabel": label}
    # **A ROW OF THE WRONG WIDTH IS A ROW NOT READ** (table.read keeps it in `refused`): left out, a torn file would read as read in full.
    not_read += [f"line {one.line}: {one.why}" for one in rows.refused]
    return WhatNotesSaid(notes=notes, not_read=tuple(not_read), rows_in_file=len(rows) + len(rows.refused))


# Which report's file is read by which reader.
READERS: Dict[str, Callable[..., WhatNotesSaid]] = {"az_suppressed": read_suppressed, "az_fee_preview": read_fees, "me_pricing": read_pricing}
# The readers that match a file against the seller's own listings, and so are handed them.
NEEDS_THE_SHOP_LISTINGS = frozenset({"me_pricing"})


def read_notes_file(report_id: str, content: bytes, report_name: str = "this file", shop_listings: Optional[Dict[str, Dict]] = None) -> WhatNotesSaid:
    """A fetched side file's bytes, as the notes it holds. `shop_listings` goes only to a reader that matches against them."""
    reader = READERS.get(report_id)
    if reader is None:
        raise table.CannotRead(f"Nothing here knows how to read {report_id!r} into notes on listings.")
    if report_id in NEEDS_THE_SHOP_LISTINGS:
        return reader(content, report_name, shop_listings)
    return reader(content, report_name)
