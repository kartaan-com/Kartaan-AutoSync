"""What a sale IS, and the row it becomes in the seller's own sheet.

**SALES DO NOT GO IN THE DATABASE. They go in a GOOGLE SHEET (D126)**, and that
is the one thing about this file easiest to get backwards. The rule behind it:
**a Sheet is for what the pipeline writes and Kartaan only reads; the database is
for what Kartaan's own clicks change.** A sale is written by the run and read by
the screens, so it is a Sheet.

His own numbers decided it. One document per sale means a rolling year is thirty
thousand documents, so **one screen opening reads thirty thousand** -- most of a
day's free allowance in a single load, at his current 83 orders a day. A sheet
comes back in ONE call whatever it holds, a settlement landing three weeks later
rewrites ONE row, and Google's ceiling of ten million cells is **9.4 years** at
this width.

---

**THE COLUMNS ARE NOT INVENTED HERE. THEY BELONG TO THE ERP**, in
`src/shared/data/sheet-store.js`, which is what READS them. They are written out
below because this repository cannot import JavaScript -- **and `sales_checks.py`
reads that file through the door and compares, name by name and in order.** Add a
column there and this goes red the same day.

**That is not belt and braces, it is the whole reason this file can be trusted.**
This project has already shipped one fact written down twice with nothing joining
it: a log line's name was built with SIX parts in Python and FIVE on the page, so
no line Kartaan made could ever have matched a line the run made -- and the check
named for exactly that fault passed anyway, because it looked for a string rather
than comparing the two sides. **This one compares the two sides.**

---

**FOUR RULES THE ERP'S OWN FILE PAID FOR LIVE, and this must not undo any of them:**

1. **A REAL NOUGHT IS WRITTEN AS A NOUGHT.** `value or ''` blanks 0, 0.0 and
   False -- and **a blank cell in a ledger reads as "never worked out"**, which
   is a different thing entirely from "worked out, and it was nothing". Confirmed
   live on Amazon settlement rows: unsettled orders wrote 0.0 and showed blank.
2. **THE RANGE IS DERIVED FROM THE COLUMNS, NEVER TYPED.** The reference wrote
   `A:AJ` by hand beside a list of 35 names; the day a column is added those two
   disagree and **the last column is silently never read again.**
3. **EVERY DOCUMENT IS NAMED FOR WHAT IT IS (D93, D126).** A sale is written AT
   `platform::orderId::sku`, worked out from the sale itself, never generated.
   That is what makes the same file arriving twice change nothing.
4. **`took` AND `taking` CANNOT BE RE-DERIVED AND MUST HAVE THEIR COLUMNS.**
   `took` is which batches a sale consumed at what those batches really cost --
   worked out again from today's shelf it comes out different, because the shelf
   has moved. `taking` is the whole of D51's replay safety. **An independent
   reviewer found both missing from a column list that had been hand-written**,
   which is why the list here is pinned rather than trusted.

---

**NOTHING HERE WRITES ANYTHING ANYWHERE.** It says what a sale is and what row it
becomes. Putting that row in a sheet is a door, and it is not built yet.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# Which collection lives in the sheet. Sales, and nothing else.
IN_THE_SHEET = "orders"

# What the tab inside the spreadsheet is called.
THE_TAB = "orders"

# **THE TWO STATES A SALE CAN BE IN.** `held` is Kartaan unable to take it off
# the shelf yet; `applied` is done. **A third one invented here would be a state
# no screen knows how to show**, so the check pins these against the ERP too.
HELD = "held"
APPLIED = "applied"
STATES = (HELD, APPLIED)

# **THE PLAIN FIELDS, IN THE ORDER THEY ARE WRITTEN.** Named one by one rather
# than taken off a record: built from whatever happens to be on the first record,
# a column would appear the day one sale carried a stray field, and every row
# written before it would be one cell short -- with the header, which is what
# says what a column MEANS, changed underneath them.
PLAIN_FIELDS = (
    "id",
    "platform",
    "orderId",
    "on",
    "sku",
    "qty",
    "gmv",
    "state",
    "heldFor",
    "settlement",
    "taxPct",
    "returned",
    "notes",
    "took",
    "taking",
    "rev",
)

# **ONE COLUMN PER CHARGE A PLATFORM CAN MAKE**, in the ERP's own order.
# A platform's own column names do NOT appear here: Meesho says "Meesho
# Commission (Incl. GST)" and Flipkart says something else, and **a seller
# comparing two platforms needs one word for one thing.** Turning a platform's
# name into one of these belongs with whatever reads that platform's file.
CHARGE_IDS = (
    "commission",
    "fixedFee",
    "collectionFee",
    "shipping",
    "returnShipping",
    "returnPremium",
    "warehousing",
    "otherServices",
    "otherServicesTax",
    "tcs",
    "tds",
    "penalty",
)

CHARGE_COLUMNS = tuple(f"charge_{one}" for one in CHARGE_IDS)

# Every column, in order. **The header row is exactly this.**
COLUMNS = PLAIN_FIELDS + CHARGE_COLUMNS

# The fields that are figures. **A sheet hands back TEXT for everything**, so
# whatever reads a row back has to know which ones to turn into numbers -- and
# `0` read back as the text "0" is what every sum in the product would join
# rather than add.
NUMBER_FIELDS = ("qty", "gmv", "settlement", "taxPct", "returned")


class NotASale(ValueError):
    """This cannot be written as a sale, and here is why.

    **ITS OWN KIND**, so a sale that cannot be built is never mistaken for a file
    that cannot be read. One is the platform's problem and one is ours.
    """


def name_for(platform: str, order_id: str, sku: str = "") -> str:
    """What a sale is called: `platform::orderId::sku`.

    **THIS IS THE SAME NAME THE ERP BUILDS, and a check compares the two sides
    rather than trusting this sentence.** If they ever differ, the run writes
    rows under names the screens cannot find -- and the tab is silently empty
    with nothing anywhere saying why. That has happened in this project once
    already, with a log line's name.

    **IT IS WHAT MAKES THE SAME FILE ARRIVING TWICE CHANGE NOTHING (D126).** The
    name comes out of the sale itself, so the second reading of a file lands on
    the same row as the first and replaces it, rather than adding a second.

    **A sale with no platform or no order number is REFUSED, not named.** A name
    with a hole in it collides with every other sale that has the same hole, so
    they would overwrite each other one by one, quietly.
    """
    where = _as_text(platform)
    which = _as_text(order_id)
    if where == "" or which == "":
        raise NotASale(
            "A sale has to say which platform it was on and what its order "
            "number is."
        )
    return f"{where}::{which}::{_as_text(sku)}"


def _as_text(value) -> str:
    """What a value says, as text, without a nought becoming nothing."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value)


def a_cell(value) -> str:
    """One cell, from one field.

    **A REAL NOUGHT IS WRITTEN AS A NOUGHT.** This is the reference's own live
    fault and it is one character wide: `value or ''` blanks 0, 0.0 and False,
    and a blank cell in a ledger reads as "never worked out". **Only nothing at
    all is blank.**

    A list or a record is written as its own text rather than as Python's idea of
    it -- `took` is a list of what came off the shelf, and `[{'lot': 'L1'}]` read
    back by anything that is not Python is not a list at all.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple, dict)):
        import json

        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    return str(value)


@dataclass(frozen=True)
class Sale:
    """One sale, as one row of the seller's ledger.

    **EVERY FIELD IS OPTIONAL EXCEPT THE THREE THAT NAME IT.** A platform's
    orders file says what was sold; its settlement file, weeks later, says what
    was paid. **The same sale is written twice from two files**, and the second
    writing must not have to invent the parts it does not know -- so anything not
    said is `None`, which is written as a blank, which is the truthful answer:
    nobody has worked it out yet.

    `charges` is by the ERP's own charge id, never by a platform's column name.
    """

    platform: str
    order_id: str
    sku: str = ""
    on: Optional[str] = None
    qty: Optional[object] = None
    gmv: Optional[object] = None
    state: Optional[str] = None
    held_for: Optional[str] = None
    settlement: Optional[object] = None
    tax_pct: Optional[object] = None
    returned: Optional[object] = None
    notes: Optional[str] = None
    took: Optional[object] = None
    taking: Optional[object] = None
    rev: Optional[object] = None
    charges: Dict[str, object] = field(default_factory=dict)

    def __post_init__(self):
        # **REFUSED WHEN IT IS BUILT, not when it is written.** A sale that
        # cannot be named is one that would quietly overwrite another, and the
        # further from the file that is noticed, the harder it is to say which
        # row of which file caused it.
        name_for(self.platform, self.order_id, self.sku)
        if self.state is not None and self.state not in STATES:
            raise NotASale(
                f"A sale is {' or '.join(STATES)}, and this one says "
                f"{self.state!r}. A state no screen knows how to show would put "
                "the sale on no list at all."
            )
        unknown = [k for k in (self.charges or {}) if k not in CHARGE_IDS]
        if unknown:
            raise NotASale(
                "This sale carries "
                + ", ".join(repr(k) for k in sorted(unknown))
                + ", which is not a charge Kartaan knows about. It knows: "
                + ", ".join(CHARGE_IDS)
                + ". A charge with no column is money that vanishes on the way "
                "to the sheet."
            )

    @property
    def id(self) -> str:
        return name_for(self.platform, self.order_id, self.sku)


# Which field of a `Sale` each plain column is written from. **Written down
# rather than worked out from the name**, because `orderId` and `heldFor` and
# `taxPct` are not what they are called in Python, and a rule with three
# exceptions is not a rule.
FROM_FIELD = {
    "id": "id",
    "platform": "platform",
    "orderId": "order_id",
    "on": "on",
    "sku": "sku",
    "qty": "qty",
    "gmv": "gmv",
    "state": "state",
    "heldFor": "held_for",
    "settlement": "settlement",
    "taxPct": "tax_pct",
    "returned": "returned",
    "notes": "notes",
    "took": "took",
    "taking": "taking",
    "rev": "rev",
}


def the_row_for(sale: "Sale") -> Tuple[str, ...]:
    """A sale, as a row of cells in column order.

    **BUILT BY WALKING `COLUMNS`, never by listing the fields again.** A row
    built from the record's own fields is a row whose order is whatever Python
    happened to do that day, and the header says what a column means.
    """
    charges = sale.charges or {}
    out: List[str] = []
    for column in COLUMNS:
        if column.startswith("charge_"):
            out.append(a_cell(charges.get(column[len("charge_"):])))
        else:
            out.append(a_cell(getattr(sale, FROM_FIELD[column])))
    return tuple(out)


def the_header() -> Tuple[str, ...]:
    """The first row of the sheet. Exactly the columns, in order."""
    return COLUMNS


def column_letter(how_many: int) -> str:
    """The last column's letter, worked out from how many there are.

    **A RANGE IS NEVER TYPED.** The reference wrote `A:AJ` beside a list of 35
    names; add a column and the read silently stops one short, with nothing
    saying so -- the last column simply reads empty on every row, for ever.
    """
    if not isinstance(how_many, int) or isinstance(how_many, bool) or how_many < 1:
        raise NotASale("A column number has to be a whole number of at least one.")
    left = how_many
    letters = ""
    while left > 0:
        step = (left - 1) % 26
        letters = chr(65 + step) + letters
        left = (left - 1) // 26
    return letters


def the_whole_tab() -> str:
    """The whole ledger, as a range. Worked out, never written down."""
    return f"{THE_TAB}!A:{column_letter(len(COLUMNS))}"


def the_range_for(row: int) -> str:
    """One row of the ledger, as a range. Row 1 is the header."""
    if not isinstance(row, int) or isinstance(row, bool) or row < 2:
        raise NotASale(
            "Row 1 is the header, so a sale is on row 2 or later. Writing a sale "
            "to row 1 would replace the column names with a sale."
        )
    return f"{THE_TAB}!A{row}:{column_letter(len(COLUMNS))}{row}"


def by_name(sales: Sequence["Sale"]) -> Dict[str, "Sale"]:
    """Sales by the name each is written at, **last one winning.**

    **THIS IS WHAT MAKES THE SAME FILE TWICE CHANGE NOTHING.** A file is a report
    of how things stand, never a list to add to -- so two rows of one file naming
    one sale collapse to one row in the sheet, exactly as the second reading of
    the whole file collapses onto the first.

    **LAST ONE WINS, and that is a decision rather than an accident:** a platform
    writing the same sale twice in one file is stating it twice, and the later
    statement is the one it meant.
    """
    out: Dict[str, "Sale"] = {}
    for one in sales or ():
        out[one.id] = one
    return out
