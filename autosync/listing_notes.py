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
from typing import Callable, Dict, Tuple

import table

# The place of each column in the file, counting from nought, as Amazon's page orders them.
THE_PLACE_OF = {"reason": 1, "sku": 2, "asin": 3, "issue": 7}
HOW_MANY_COLUMNS = 8
# The longest a name can be and the same for the record's id: a slash or a longer one cannot be a record's name (as listings.py).
_LONGEST_ID = 1000


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
    the rows it would not take and `.rows_in_file` the rows in the file. `read_fee_preview` itself is on lane 1 only, so the lane merge joins them (the reader line is in
    DONE_AP9). **A fee of 0.00 is kept: it is a figure Amazon gave.** `feeAsOf`, the file's day, is added by the sink, as `suppressedOn` is.
    """
    return WhatNotesSaid(
        notes={name: {"referralFee": fee} for name, fee in fees_said.fees.items()},
        not_read=tuple(fees_said.not_read),
        rows_in_file=fees_said.rows_in_file,
    )


# Which report's file is read by which reader.
READERS: Dict[str, Callable[..., WhatNotesSaid]] = {"az_suppressed": read_suppressed}


def read_notes_file(report_id: str, content: bytes, report_name: str = "this file") -> WhatNotesSaid:
    """A fetched side file's bytes, as the notes it holds."""
    reader = READERS.get(report_id)
    if reader is None:
        raise table.CannotRead(f"Nothing here knows how to read {report_id!r} into notes on listings.")
    return reader(content, report_name)
