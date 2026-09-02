"""Which of a platform's own columns is the SKU, the quantity, the money.

**THIS IS THE ONLY FILE THAT KNOWS WHAT MEESHO, FLIPKART AND AMAZON CALL THINGS.**
Above it, a sale is a sale (`sales.py`). Below it, a file is rows (`table.py`,
`sheet.py`). One word for one thing, said once, so a seller comparing two
platforms is comparing like with like -- and so a renamed column is one entry
changed here and nothing else.

**EVERY COLUMN NAME BELOW WAS READ OFF HIS OWN FILES on 2026-09-02**, not off a
description of them: 46 real Amazon orders, a real Meesho orders file, a real
Flipkart orders file of 39 columns and 63 rows.

---

**THE THING TO KNOW BEFORE ANYTHING ELSE: FLIPKART'S ORDERS FILE HAS NO MONEY IN
IT.** Thirty-nine columns and **not one of them is an amount** -- no price, no
GMV, no settlement. Counted, not assumed. So a Flipkart sale is read with its
money left BLANK, which `sales.py` writes as blank, which means exactly what it
should: *nobody has worked this out yet.* The figure arrives later, from the
payments file, as a second statement about the same sale.

**That is why blank and nought had to be different things** before this file
could be written at all. The reference blanked a real nought; here a real nought
is a nought and a blank is an open question, and Flipkart's orders are the reason
it matters.

---

**WHAT EACH PLATFORM CALLS THINGS, side by side:**

|                | Meesho                | Flipkart          | Amazon             |
|----------------|-----------------------|-------------------|--------------------|
| the file       | `.csv`, comma         | `.xlsx`, "Orders" | tab-separated      |
| the order      | `Sub Order No`        | `order_id`        | `amazon-order-id`  |
| the SKU        | `SKU`                 | `sku`             | `sku`              |
| how many       | `Quantity`            | `quantity`        | `quantity`         |
| the money      | `Supplier Discounted Price (Incl GST and Commision)` | **none** | `item-price` |
| the day        | `Order Date`          | `order_date`      | `purchase-date`    |
| their word     | `Reason for Credit Entry` | `order_item_status` | `order-status` |

**Meesho's own spelling of "Commision" is kept exactly as Meesho writes it.**
Correcting it here would look right and match nothing.

---

**THREE RULES ABOUT GETTING IT WRONG:**

1. **A MOVED COLUMN STOPS THE WHOLE FILE, once, by name.** Checked against the
   header before a single row is read -- not per row, or a Flipkart rename
   produces one identical complaint sixty-three times and buries the one fact
   that matters.
2. **A ROW THAT CANNOT BE READ IS REFUSED BY NAME, AND THE REST ARE READ.** A
   quantity that is not a number, a date nobody can parse, an order with no
   number: that row is kept aside with its line number and what it said, and the
   other sixty-two still become sales. **One bad cell must never lose the file.**
3. **A DATE IS NEVER GUESSED AT.** All three of these files write their day
   leading with the year, so a day is read from the front and REFUSED if it is
   not there. Amazon's SETTLEMENT file writes `26.08.2026` -- day first, with
   dots -- and read the other way round `01.09.2026` becomes 9 January instead of
   1 September. **Nothing here will ever be asked to guess between them**, and a
   shape it does not recognise stops that row rather than dating it wrong.

---

**AND ONE THING WITH NOWHERE TO GO, SAID OUT LOUD RATHER THAN INVENTED AROUND.**

Every one of these files carries the platform's own word for what happened --
`SHIPPED`, `CANCELLED`, `READY_TO_SHIP`, `Pending`. Counted on his real August
Meesho files: 209 shipped, 42 **cancelled**, 37 ready to ship, 5 on hold, 4
delivered.

**Kartaan's ledger has no column for it.** That is deliberate on the ERP's side
-- `sheet-store.js` says so in as many words: *"The reference asked this of a
platform status -- Delivered, RTO, Cancelled -- and Kartaan does not store one."*

So there are three ways to go and **all three are his to choose**, not mine:

- put the platform's word in `notes` -- **REJECTED here without asking**, because
  `notes` is the seller's own typing and D136 forbids the run touching what the
  seller decided. It would quietly overwrite them.
- drop cancelled rows -- **REJECTED here without asking**, because a file is a
  report of how things stand: a sale that arrives today and is cancelled tomorrow
  must be CORRECTED tomorrow, and a dropped row corrects nothing. The sale would
  stand for ever.
- add a column for it, which changes the contract the ERP and this file are
  pinned to, on both sides.

**Until he says: every row is read faithfully, cancelled ones included, and the
platform's own word is carried on the sale but NOT WRITTEN TO A COLUMN.**
`their_word` exists on the record, goes nowhere near the sheet, and is counted in
what a read says out loud -- so 42 cancelled orders are visible as a number
rather than silently becoming 42 ordinary sales.
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

from sales import Sale
from table import CannotRead, Table

MEESHO = "meesho"
FLIPKART = "flipkart"
AMAZON = "amazon"

# A day, at the front of whatever else the platform wrote after it. All three
# orders files lead with the year; nothing else is accepted, and nothing is
# guessed at.
A_DAY_AT_THE_FRONT = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")


@dataclass(frozen=True)
class NotRead:
    """One row that could not be turned into a sale, kept by name."""

    line: int
    why: str

    def __str__(self) -> str:
        return f"line {self.line}: {self.why}"


@dataclass(frozen=True)
class WhatWasRead:
    """What a file turned into: the sales, and what would not read.

    **`by_name` IS WHAT GOES TO THE SHEET, not `sales`.** Two rows of one file
    naming one sale collapse to one row, exactly as the second reading of the
    whole file collapses onto the first (D126).
    """

    platform: str
    sales: Tuple[Sale, ...]
    not_read: Tuple[NotRead, ...] = ()
    their_words: Tuple[Tuple[str, int], ...] = ()

    def says(self) -> str:
        """One line for the run log.

        **THE COUNTS ARE SAID EVEN WHEN THEY ARE NOUGHT.** A sentence that
        mentions bad rows only when there are some makes a clean read and a read
        nobody checked look identical.
        """
        said = (
            f"{self.platform}: {len(self.sales)} sales read, "
            f"{len(self.not_read)} rows could not be read"
        )
        if self.their_words:
            said += "; the platform said " + ", ".join(
                f"{word} x{count}" for word, count in self.their_words
            )
        return said


def the_day_in(said: str) -> Optional[str]:
    """The day at the front of what a platform wrote, or nothing at all.

    **NOTHING IS GUESSED AT.** `26.08.2026` and `08/26/2026` both come back as
    nothing, and the row that held them is refused by name -- rather than being
    dated eight months wrong and looking perfectly fine on a screen.
    """
    found = A_DAY_AT_THE_FRONT.match((said or "").strip())
    if not found:
        return None
    try:
        return date(int(found.group(1)), int(found.group(2)), int(found.group(3))).isoformat()
    except ValueError:
        # A real shape holding an impossible day -- 2026-02-31. Refused, not
        # rounded to the end of the month by something being helpful.
        return None


def a_figure(said: str) -> Optional[str]:
    """A figure as the platform wrote it, or nothing when it is not one.

    **HANDED ON AS TEXT, exactly as it arrived.** Turning `349.0` into a Python
    number and back again is a rounding nobody asked for; the sheet takes text
    and the ERP turns it back when it reads it.

    **A BLANK IS NOTHING, NOT NOUGHT.** Amazon leaves `shipping-price` empty on
    every one of his real rows -- read as 0 that would state a fact nobody has.
    """
    text = (said or "").strip()
    if text == "":
        return None
    try:
        float(text)
    except ValueError:
        return None
    return text


def _unwrap_flipkart_sku(said: str) -> str:
    """`\"\"\"SKU:DJ 14 Bahubali\"\"\"` -> `DJ 14 Bahubali`.

    **EVERY ONE OF HIS 63 REAL FLIPKART ROWS IS WRAPPED LIKE THIS** -- counted,
    not assumed. The wrapper is the file format's, not the seller's: the SKU on
    his listing is `DJ 14 Bahubali`, and left wrapped it matches no product he
    has.

    **THIS IS UNWRAPPING, NOT TIDYING, and the difference is a rule.** The
    register already carries the fault: *"A tidy-up map sat inside an identity
    lookup. Order SKUs were rewritten before matching Product Master, so 17 of 39
    mapped SKUs could never match."* So nothing here changes case, spacing inside
    the name, or any character of the SKU itself. It removes what the file put
    round it and stops.
    """
    text = (said or "").strip().strip('"').strip()
    if text.upper().startswith("SKU:"):
        text = text[4:].strip()
    return text


@dataclass(frozen=True)
class Mapping:
    """What one platform calls the things a sale is made of."""

    platform: str
    order_id: str
    sku: str
    qty: str
    on: str
    their_word: str
    gmv: Optional[str] = None
    unwrap_sku: bool = False

    @property
    def needs(self) -> Tuple[str, ...]:
        """The columns without which nothing can be read.

        **THE MONEY IS NOT AMONG THEM, and that is Flipkart's doing.** A file
        with no amount in it is still a file full of real sales.
        """
        return (self.order_id, self.sku, self.qty, self.on)


# **MEESHO.** `Sub Order No` is the line, not the order -- one basket of three
# things is three rows with three sub-order numbers, which is exactly the grain
# a sale is written at. Its own spelling of "Commision" is kept.
FROM_MEESHO = Mapping(
    platform=MEESHO,
    order_id="Sub Order No",
    sku="SKU",
    qty="Quantity",
    on="Order Date",
    their_word="Reason for Credit Entry",
    gmv="Supplier Discounted Price (Incl GST and Commision)",
)

# **FLIPKART. NO MONEY COLUMN EXISTS** -- 39 columns, none an amount.
FROM_FLIPKART = Mapping(
    platform=FLIPKART,
    order_id="order_id",
    sku="sku",
    qty="quantity",
    on="order_date",
    their_word="order_item_status",
    gmv=None,
    unwrap_sku=True,
)

# **AMAZON.** `item-price` is what the reference used and what his real rows
# carry; `item-tax` is beside it and is NOT added in -- a charge is a charge, and
# where it goes is `charges.py`'s business, not this file's.
FROM_AMAZON = Mapping(
    platform=AMAZON,
    order_id="amazon-order-id",
    sku="sku",
    qty="quantity",
    on="purchase-date",
    their_word="order-status",
    gmv="item-price",
)

EVERY_MAPPING = {m.platform: m for m in (FROM_MEESHO, FROM_FLIPKART, FROM_AMAZON)}

# Where a platform's orders live inside its file. **Flipkart's is not the first
# sheet** -- the first is `Help` -- and a reader taking the first sheet reports
# that the seller had no orders.
WHERE_FLIPKART_ORDERS_ARE = "Orders"
FLIPKART_HEADER_ROW = 1


def mapping_for(platform: str) -> Mapping:
    """What that platform calls things, or a refusal naming the ones known."""
    found = EVERY_MAPPING.get((platform or "").strip().lower())
    if found is None:
        raise CannotRead(
            f"Nothing here knows how to read {platform!r}'s orders. It knows: "
            + ", ".join(sorted(EVERY_MAPPING))
            + "."
        )
    return found


def read_orders(rows: Table, platform: str) -> WhatWasRead:
    """Turn a platform's orders file into sales.

    **THE COLUMNS ARE CHECKED ONCE, AGAINST THE HEADER**, before a row is read.
    A column that has moved stops the file with one sentence naming it -- rather
    than sixty-three identical complaints, which bury the one fact that matters.
    """
    how = mapping_for(platform)

    missing = [c for c in how.needs if c not in rows.columns]
    if missing:
        raise CannotRead(
            f"This does not look like a {how.platform} orders file. It has no "
            + ", ".join(repr(c) for c in missing)
            + ". It has: "
            + ", ".join(repr(c) for c in rows.columns if c)
            + ". Nothing was read, because a column that has moved would put a "
            "blank where a figure should be."
        )
    money_is_here = bool(how.gmv) and how.gmv in rows.columns

    sales: List[Sale] = []
    not_read: List[NotRead] = []
    words: Dict[str, int] = {}

    for row in rows:
        try:
            order_id = row[how.order_id].strip()
            sku = row[how.sku].strip()
            if how.unwrap_sku:
                sku = _unwrap_flipkart_sku(sku)
            said_when = row[how.on]
            said_many = row[how.qty].strip()
            their_word = row.get(how.their_word, "").strip()
        except CannotRead as wrong:
            not_read.append(NotRead(line=row.line, why=str(wrong)))
            continue

        if order_id == "":
            not_read.append(NotRead(
                line=row.line,
                why="this row has no order number, and a sale with no order "
                    "number cannot be told apart from any other that has none",
            ))
            continue

        when = the_day_in(said_when)
        if when is None:
            not_read.append(NotRead(
                line=row.line,
                why=f"the day reads {said_when!r}, which is not a shape this "
                    "knows. It is refused rather than guessed at, because a day "
                    "guessed the wrong way round is money dated months out",
            ))
            continue

        how_many = a_figure(said_many)
        if how_many is None:
            not_read.append(NotRead(
                line=row.line,
                why=f"the quantity reads {said_many!r}, which is not a number",
            ))
            continue

        # **THE MONEY IS ALLOWED TO BE MISSING; THE REST IS NOT.** Flipkart never
        # sends it, and Amazon leaves it blank on rows it has not priced.
        money = a_figure(row[how.gmv]) if money_is_here else None

        if their_word:
            words[their_word] = words.get(their_word, 0) + 1

        try:
            sales.append(Sale(
                platform=how.platform,
                order_id=order_id,
                sku=sku,
                on=when,
                qty=how_many,
                gmv=money,
            ))
        except Exception as wrong:  # noqa: BLE001
            # A sale this file states but Kartaan will not accept. Named, kept
            # aside, and the rest of the file still read.
            not_read.append(NotRead(line=row.line, why=str(wrong)))

    return WhatWasRead(
        platform=how.platform,
        sales=tuple(sales),
        not_read=tuple(not_read),
        their_words=tuple(sorted(words.items())),
    )
