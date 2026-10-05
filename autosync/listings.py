"""Reading a platform's listing file into listings, the way the ERP's "Bring in a listing file" button reads it (plan jobs 41 and 46).

**THE SHAPES ARE THE ERP'S, AND THEY ARE WRITTEN TWICE ON PURPOSE.** The ERP keeps them in JavaScript
(`src/shared/definitions/listing-files.js`) and the run is Python, so a second copy is unavoidable. **`listings_checks.py` reads the
ERP's committed copy back and refuses to pass if the two disagree on a column name, the sheet-finding columns or the help-text
marker** -- the same pinning `firestore_checks.py` does for `sync.js` -- and runs the ERP's own reader over his real files to compare
listing for listing. Amazon's entry exists here only until the ERP has its own; see `AMAZON`.

**WHAT COMES OUT IS WHAT THE ERP'S READER MAKES, one dictionary per listing** (`platform`, `platformId`, `sku`, `productName`, `stock`,
`mrp`, `sellingPrice`, `settlement`, `buyerLink`, `state`, `stateReason`, `platformVariation`, `catalogId`, `listingId`), **without the
`line` it carries**: a line number is where the row sat in one day's file, and tomorrow's file puts the same listing somewhere else, so
a record that kept it would look changed every day.

**NOTHING IS WRITTEN INTO THE CATALOGUE, NOTHING IS GUESSED.** A row that cannot be read is said, with its line and the reason, and
the rest are read (the ERP's rule). A column the shape needs that the file does not have refuses the whole file in words, because a
blank stock and a stock that was never found look the same afterwards, and one of them oversells.

**WHAT IS NOT HERE, said rather than left to be found:** his own "leave this listing alone" rules (D92) live in the ERP's database, not
here, so the run records every listing the file names and the ERP applies those rules when it shows them. And a listing that stops
appearing in a file is not noticed: nothing compares one file with the last.
"""

import math
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import sheet
import table
import xls

# What Flipkart writes in `Listing Status` for a listing that is selling (ERP: FLIPKART_SELLING).
FLIPKART_SELLING = "ACTIVE"
# How Flipkart marks a Shopsy listing: its own sub-category starts with this (ERP: SHOPSY_PREFIX). Never read out of the SKU.
SHOPSY_PREFIX = "shopsy_"
# Columns a listing can be read WITHOUT (ERP: CAN_BE_MISSING).
CAN_BE_MISSING = ("mrp", "sellingPrice", "settlement", "stateReason")

# The most a figure can be before it is a float rather than a whole number: JavaScript's last exactly-held whole number.
_LARGEST_WHOLE = 2 ** 53
_A_NUMBER = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")
_A_SPACE = re.compile(r"\s")
# A record's name is at most 1,500 bytes (Firestore's limit), and cannot hold a slash; an id past either is a row to look at, not a file refused.
_LONGEST_ID = 1000


@dataclass(frozen=True)
class Shape:
    """One platform's listing file: how it is found among a workbook's sheets, and what each of its columns is called."""

    id: str
    heading: str
    # Columns that identify the data sheet among the book's other sheets (ERP: findSheetBy). Empty for a plain text file.
    find_by: Tuple[str, ...]
    # (column, what it says on the help row) or None for a file with no help row.
    help_text: Optional[Tuple[str, str]]
    columns: Dict[str, str]


FLIPKART = Shape(
    id="flipkart",
    heading="Flipkart listings",
    find_by=("Seller SKU Id", "Flipkart Serial Number", "Sub-category"),
    help_text=("Seller SKU Id", "Your Identifier for a product"),
    columns={
        "sku": "Seller SKU Id",
        "productName": "Product Title",
        "key": "Flipkart Serial Number",
        "listingId": "Listing ID",
        "stock": "System Stock count",
        "mrp": "MRP",
        "sellingPrice": "Your Selling Price",
        "settlement": "Bank Settlement",
        "state": "Listing Status",
        "stateReason": "Inactive Reason",
        "channel": "Sub-category",
    },
)

MEESHO = Shape(
    id="meesho",
    heading="Meesho listings",
    find_by=("STYLE ID", "PRODUCT ID", "VARIATION ID"),
    help_text=("SERIAL NO", "Row identifier"),
    columns={
        "sku": "STYLE ID",
        "productName": "PRODUCT NAME",
        "key": "PRODUCT ID",
        "keyAlso": "VARIATION ID",
        "catalogId": "CATALOG ID",
        "platformVariation": "VARIATION",
        "stock": "SYSTEM STOCK COUNT",
    },
)

# **AMAZON'S, FROM HIS REAL FILE -- `Active Listings Report`, read 2026-10-05, 88 listings.** Tab-separated text with 48 columns and no help
# row. In it `listing-id`, `seller-sku` and `asin1` are each filled and distinct on all 88 rows; `asin2`, `asin3` and `add-delete` are empty,
# `fulfillment-channel` is `DEFAULT` on all of them. **THE KEY IS THE ASIN** (`asin1`): it is what Amazon's orders carry and what the buyer's
# page is built from (`amazon.in/dp/<ASIN>`); Amazon's own `listing-id` is carried beside it, as Flipkart's is. A report that lists one ASIN twice
# (two offers of it) says so on the second row instead of dropping it silently. The report lists active listings only, so a row being in it
# is what says the listing is live -- as for Meesho. **`maximum-retail-price` and `price` are the MRP and the selling price; Amazon's file has
# no settlement figure.** Not in the ERP's `LISTING_FILES` yet -- that entry is the ERP's to add; this one is the run's until then.
AMAZON = Shape(
    id="amazon",
    heading="Amazon listings",
    find_by=(),
    help_text=None,
    columns={
        "sku": "seller-sku",
        "productName": "item-name",
        "key": "asin1",
        "listingId": "listing-id",
        "stock": "quantity",
        "mrp": "maximum-retail-price",
        "sellingPrice": "price",
    },
)

SHAPES: Dict[str, Shape] = {one.id: one for one in (FLIPKART, MEESHO, AMAZON)}

# Which report's file is which platform's listings.
THE_SHAPE_OF = {"fk_listings": FLIPKART, "me_catalog": MEESHO}


@dataclass(frozen=True)
class WhatListingsSaid:
    """One listing file's listings, and every row it would not take."""

    # reviewId (`platform::platformId`) -> the listing
    records: Dict[str, Dict]
    not_read: Tuple[str, ...]
    rows_in_file: int


def _figure(said: str) -> Tuple[Optional[object], str]:
    """(the number, '') for a figure, (None, '') for a blank, (None, what it said) for something that is not one."""
    said = said.strip()
    if not said:
        return None, ""
    if not _A_NUMBER.match(said):
        return None, said
    number = float(said)
    if not math.isfinite(number):
        return None, said
    if number == int(number) and abs(number) < _LARGEST_WHOLE:
        return int(number), ""
    return number, ""


def _meesho_link(product_id: str) -> str:
    """Meesho's own product page, from the product id written in base 36 (ERP: meeshoLink)."""
    if not product_id.isascii() or not product_id.isdigit():
        return ""
    left = int(product_id)
    if left <= 0 or left >= _LARGEST_WHOLE:
        return ""
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while left > 0:
        out = digits[left % 36] + out
        left //= 36
    return f"https://www.meesho.com/product/p/{out}"


def _buyer_link(shape: Shape, key: str, platform: str) -> str:
    """Where a buyer would see the listing, or '' when the id could not be put in a web address safely (ERP: buyerLinkFrom)."""
    if shape.id == "meesho":
        return _meesho_link(key)
    if not re.match(r"^[A-Za-z0-9]+$", key):
        return ""
    if shape.id == "amazon":
        return f"https://www.amazon.in/dp/{key}"
    shop = "www.shopsy.in" if platform == "shopsy" else "www.flipkart.com"
    return f"https://{shop}/product/p/itme?pid={key}"


def _platform_of(shape: Shape, row: table.Row) -> Optional[str]:
    """Which storefront one row belongs to. None when the file gives no reliable signal (ERP: platformOfRow)."""
    if shape.id != "flipkart":
        return shape.id
    channel = row[shape.columns["channel"]].strip().lower()
    if channel.startswith(SHOPSY_PREFIX):
        return "shopsy"
    if channel:
        return "flipkart"
    return None if "shopsy" in row[shape.columns["sku"]].strip().lower() else "flipkart"


def _state_of(shape: Shape, row: table.Row) -> Optional[str]:
    """`live`, `not_live`, or None when the platform has the column and left this row's blank (ERP: stateOfRow)."""
    column = shape.columns.get("state")
    if not column:
        return "live"
    said = row[column].strip().upper()
    if not said:
        return None
    return "live" if said == FLIPKART_SELLING else "not_live"


def _the_key(shape: Shape, row: table.Row) -> str:
    """The platform's own key for a listing, two parts joined with `::` on Meesho. '' when a part is missing or has a space in it."""
    parts = [row[shape.columns[one]].strip() for one in ("key", "keyAlso") if one in shape.columns]
    if any(not part or _A_SPACE.search(part) or "/" in part or len(part.encode("utf-8")) > _LONGEST_ID for part in parts):
        return ""
    return "::".join(parts)


def the_review_id(listing: Dict) -> str:
    """The stable name of a listing: its platform and the platform's own id, never the seller's SKU (ERP: reviewId)."""
    return f"{listing['platform']}::{listing['platformId']}"


def _required(shape: Shape) -> List[str]:
    named = [name for role, name in shape.columns.items() if role not in CAN_BE_MISSING]
    if shape.help_text:
        named.append(shape.help_text[0])
    return list(dict.fromkeys(named))


def _the_sheet(content: bytes, shape: Shape, report_name: str) -> table.Table:
    """The one sheet of the workbook that has this platform's columns, or a refusal saying what to do."""
    kind = "xls" if content[:4] == bytes.fromhex("d0cf11e0") else "xlsx"
    reader = xls if kind == "xls" else sheet
    found = []
    for name in reader.sheets_in(content):
        try:
            one = reader.read(content, sheet=name, header_row=1)
        except table.CannotRead as wrong:
            if "damaged" in str(wrong):
                raise
            continue
        if all(column in one.columns for column in shape.find_by):
            found.append(one)
    if not found:
        raise table.CannotRead(
            f"{report_name} does not look like a {shape.heading} file: no sheet in it has the columns {', '.join(shape.find_by)}. "
            "Nothing was read. Download the listing file again; if it still says this, the platform has changed its file and "
            "Kartaan needs to be told."
        )
    if len(found) > 1:
        raise table.CannotRead(
            f"{len(found)} sheets in {report_name} look like {shape.heading}, so there is no way to tell which one to read. Nothing "
            "was read. Download the listing file again with only one of them in it."
        )
    return found[0]


def read_listings(shape: Shape, rows: table.Table, report_name: str = "this file") -> WhatListingsSaid:
    """One platform's listing rows turned into listings, the ERP reader's way.

    Refuses the whole file, in words, when it has no listings under its headings or lacks a column a listing cannot be read without.
    """
    needed = _required(shape)
    missing = [name for name in needed if name not in rows.columns]
    if missing:
        raise table.CannotRead(
            f"The {shape.heading} file {report_name} is missing {'a column' if len(missing) == 1 else 'columns'} Kartaan needs: "
            f"{', '.join(missing)}. Nothing was read, because a column that has moved would put a blank where a stock should be. "
            "Download the listing file again; if it still says this, the platform has changed its file and Kartaan needs to be told."
        )
    repeated = [name for name in shape.columns.values() if name in rows.ambiguous]
    if repeated:
        raise table.CannotRead(
            f"{report_name} has more than one column called {', '.join(repr(n) for n in repeated)}, so which is meant cannot be "
            "decided. Nothing was read. Download the listing file again; if it still says this, the platform has changed its file "
            "and Kartaan needs to be told."
        )
    if not len(rows):
        raise table.CannotRead(
            f"The {shape.heading} file {report_name} has its column headings and not one listing under them. Nothing was read; "
            "an empty file is not the same as a catalogue with nothing in it."
        )

    records: Dict[str, Dict] = {}
    not_read: List[str] = []
    if shape.help_text and all(row[shape.help_text[0]].strip() == shape.help_text[1] for row in rows):
        raise table.CannotRead(
            f"The {shape.heading} file {report_name} has its column headings and only the platform's explanation row under them. Nothing was "
            "read; an empty file is not the same as a catalogue with nothing in it."
        )
    seen_at: Dict[str, int] = {}
    rows_seen = 0
    for row in rows:
        try:
            if shape.help_text and row[shape.help_text[0]].strip() == shape.help_text[1]:
                continue
            rows_seen += 1
            sku = row[shape.columns["sku"]].strip()
            key = _the_key(shape, row)
            if not key:
                not_read.append(
                    f"line {row.line} ({sku or 'no SKU'}): this row does not carry "
                    f"{'both ' if 'keyAlso' in shape.columns else 'a '}"
                    f"{' and a '.join(shape.columns[one] for one in ('key', 'keyAlso') if one in shape.columns)} that could be an id -- "
                    "it is blank, a sentence, or has a slash in it, so nothing could ever be matched back to it. Check that row in the file you "
                    "downloaded; every other row was read"
                )
                continue
            platform = _platform_of(shape, row)
            if platform is None:
                not_read.append(
                    f"line {row.line} ({sku}): the SKU mentions Shopsy but the row has no category, so there is no way to confirm "
                    "whether this is a Shopsy listing. Guessing would file it under the wrong storefront"
                )
                continue
            state = _state_of(shape, row)
            if state is None:
                not_read.append(
                    f"line {row.line} ({sku}): {shape.columns['state']} is blank on this row, so the platform has not said whether it "
                    "is selling. Reading a blank as not live would take a real listing off sale"
                )
                continue
            figures: Dict[str, object] = {}
            bad: Optional[Tuple[str, str]] = None
            for role in ("stock", "mrp", "sellingPrice", "settlement"):
                column = shape.columns.get(role)
                if column is None or column not in rows.columns:
                    figures[role] = None
                    continue
                number, unreadable = _figure(row[column])
                if unreadable:
                    bad = (column, unreadable)
                    break
                figures[role] = number
            if bad:
                not_read.append(
                    f"line {row.line} ({sku}): {bad[0]} on this row reads {bad[1]!r}, which is not a number. A stock or a price "
                    "nobody can read is worse than one nobody has given"
                )
                continue
            listing = {
                "platform": platform,
                "platformId": key,
                "sku": sku,
                "productName": row[shape.columns["productName"]].strip(),
                "stock": figures["stock"],
                "mrp": figures["mrp"],
                "sellingPrice": figures["sellingPrice"],
                "settlement": figures["settlement"],
                "buyerLink": _buyer_link(shape, row[shape.columns["key"]].strip(), platform),
                "state": state,
                "stateReason": row.get(shape.columns["stateReason"]).strip() if "stateReason" in shape.columns else "",
                "platformVariation": row.get(shape.columns["platformVariation"]).strip() if "platformVariation" in shape.columns else "",
                "catalogId": row.get(shape.columns["catalogId"]).strip() if "catalogId" in shape.columns else "",
                "listingId": row.get(shape.columns["listingId"]).strip() if "listingId" in shape.columns else "",
            }
            name = the_review_id(listing)
            if name in seen_at:
                not_read.append(f"line {row.line} ({sku}): line {seen_at[name]} already uses the same id. Only the first was kept")
                continue
            seen_at[name] = row.line
            records[name] = listing
        except table.CannotRead as wrong:
            not_read.append(f"line {row.line}: this row could not be read: {wrong}")
    return WhatListingsSaid(records=records, not_read=tuple(not_read), rows_in_file=rows_seen)


def read_listing_file(report_id: str, content: bytes, report_name: str = "this file") -> WhatListingsSaid:
    """A fetched listing file's bytes, as the listings it names. The sheet is found by its columns, never by its name or its place."""
    shape = THE_SHAPE_OF.get(report_id)
    if shape is None:
        raise table.CannotRead(f"Nothing here knows how to read {report_id!r} into listings.")
    return read_listings(shape, _the_sheet(content, shape, report_name), report_name)
