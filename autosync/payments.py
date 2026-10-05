"""A platform's payment file, turned into what each order was paid and what it was charged (job 36).

**THE WHOLE JOB, IN HIS WORDS: "reconciliation means matching the order data with payment data."** An orders file says what was
sold; a payments file, weeks later, says what the platform actually paid and took for it. This reads the second kind and says it
about the same orders -- on the order id -- so the one ledger row that explains one order carries its money too.

**IT WAS WRITTEN AGAINST HIS REAL FILES (2026-10-05), read for their shape only:** Amazon's unified transaction report (a
definitions block, then the header on its own line, one line per transaction), Flipkart's settlement workbook (the `Orders`
sheet, group names on row 1, column names on row 2, a sub-header row under them) and Meesho's payments workbook (the
`Order Payments` sheet, the same two header rows, one line per sub-order). None of those files is in this repository and no
figure from them is written here.

**ONE SIGN, FOR EVERY PLATFORM: A CHARGE IS POSITIVE WHEN MONEY WAS TAKEN FROM HIM.** All three platforms write what they take
as a negative figure, so every charge below is the platform's figure with its sign turned over. A fee that was given back
(a refunded fee) comes out negative, which is the truth. `settlement` is NOT turned over: it is what was actually paid to him
for the order, as the platform states it, so it can be negative where the platform took money back.

**A BLANK IS NEVER A NOUGHT.** A charge no line of the file mentions is left out of the sale entirely, so the ledger's cell is
not written, so what is already there stays. A real nought the platform wrote is written as a nought.

**THE FILE'S OWN LINES FOR ONE ORDER ARE ADDED TOGETHER.** Amazon writes an order, its shipping fee and a refund as separate
lines; the ledger has one row, so they are summed here -- in decimals, never in floating point, because adding rupees in
floating point is how a figure ends in 0.30000000000000004.

**WHAT IS NOT PUT ON AN ORDER IS SAID, NOT DROPPED.** A payout, a service fee with no order, a line the platform has not released
yet: each is counted by kind in `set_aside` and the run says it. Which row a line belongs to when the ledger does not have the
order is decided in `ledger.plan`, which knows the ledger -- this file does not.

**NOTHING HERE TOUCHES THE NETWORK, THE DISK OR A CLOCK.**
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from orders import NotRead, _unwrap_flipkart_sku, a_figure, the_day_in
from sales import CHARGE_COLUMNS, CHARGE_IDS, Sale
from table import CannotRead, Row, Table

AMAZON = "amazon"
FLIPKART = "flipkart"
MEESHO = "meesho"

# Where the money is inside each platform's file. Flipkart's and Meesho's are not the first sheet, and a reader that took the
# first would report a file with no payments in it.
WHERE_FLIPKART_PAYMENTS_ARE = "Orders"
FLIPKART_HEADER_ROW = 2
WHERE_MEESHO_PAYMENTS_ARE = "Order Payments"
MEESHO_HEADER_ROW = 2

# What Amazon's header line starts with. **Found, not counted down to**: the block of definitions above it is the platform's
# to lengthen, and a header assumed on line 14 is a header missed the day it is on line 15.
AMAZON_HEADER_STARTS = "date/time"

# **WHAT EACH PLATFORM'S FILE KNOWS, IN THE LEDGER'S OWN WORDS.** The columns a payments file may write, and no others (D150
# rule 1). `paymentsOn` is the file's own data day: it is what lets an older payments file be told from a newer one.
WHAT_PAYMENTS_KNOW = ("settlement",) + CHARGE_COLUMNS + ("paymentsOn",)


@dataclass(frozen=True)
class WhatWasPaid:
    """What a payments file came to: the sales it states money for, and what was not put on any."""

    platform: str
    sales: Tuple[Sale, ...]
    not_read: Tuple[NotRead, ...] = ()
    # Lines the file carries that are not about an order -- or not about money paid yet. Said, one sentence per kind.
    set_aside: Tuple[str, ...] = ()

    def says(self) -> str:
        return (
            f"{self.platform}: money stated for {len(self.sales)} order lines, "
            f"{len(self.not_read)} rows could not be read, {len(self.set_aside)} kinds of line set aside"
        )


# ---------------------------------------------------------------- figures


def a_decimal(said: str) -> Optional[Decimal]:
    """A figure as an exact decimal, or nothing when the cell has none. **A blank is nothing, not nought.**"""
    text = a_figure((said or "").replace(",", ""))
    if text is None:
        return None
    try:
        made = Decimal(text)
    except InvalidOperation:
        return None
    # **A FIGURE OF ANY SANE SIZE, AND NO OTHER.** `1E999999` is a figure to `float` and a million characters once written out,
    # which no cell takes -- and `1E999999999` overflows the adding. Past fifteen digits either way it is not money.
    if not made.is_finite() or abs(made.adjusted()) > 15:
        return None
    return made


def as_text(figure: Decimal) -> str:
    """A decimal written the way the sheet takes it: no exponent, no trailing noughts, and no negative nought."""
    if figure == 0:
        return "0"
    return format(figure.normalize(), "f")


def add_up(one: Optional[str], other: Optional[str]) -> Optional[str]:
    """Two figures written as text, added; nothing when neither has one. **One missing is the other, not nought.**"""
    a = a_decimal(one) if one not in (None, "") else None
    b = a_decimal(other) if other not in (None, "") else None
    if a is None and b is None:
        return None
    return as_text((a or Decimal(0)) + (b or Decimal(0)))


def two_sales_of_one_row(first: Sale, second: Sale) -> Sale:
    """Two statements about ONE ledger row in one file, added together.

    Used when a line with no SKU (Amazon's shipping fee for an order) is found to belong to the one row its order has, and
    that row already has lines of its own in the same file.
    """
    from dataclasses import replace  # noqa: PLC0415 - kept beside its one use

    charges: Dict[str, str] = {}
    for one in CHARGE_IDS:
        both = add_up((first.charges or {}).get(one), (second.charges or {}).get(one))
        if both is not None:
            charges[one] = both
    return replace(
        first,
        settlement=add_up(first.settlement, second.settlement),
        charges=charges,
    )


# ---------------------------------------------------------------- finding columns


def _where(columns: Sequence[str], name: str, *, starts: bool = False, after: Optional[int] = None) -> int:
    """The one place a column is, or a refusal saying what was found.

    **`after` IS FOR A NAME A FILE USES TWICE** (Meesho's two `Fixed Fee`s), taking the one past an anchor column. A name that
    is still not exactly one place is refused rather than picked from: which one is meant would be a coin toss in the money.
    """
    found = [
        at for at, one in enumerate(columns)
        if (one.startswith(name) if starts else one == name) and (after is None or at > after)
    ]
    if len(found) != 1:
        raise CannotRead(
            f"This payments file has {len(found)} columns called {name!r}"
            + (f" after the column {columns[after]!r}" if after is not None else "")
            + ", and the reading needs exactly one. Nothing was read, because a column that has moved "
            "would put a blank where a figure should be. It has: "
            + ", ".join(repr(c) for c in columns if c)
            + "."
        )
    return found[0]


def _the_refused(rows: Table) -> List[NotRead]:
    """The lines the table could not read (the wrong width), kept by name. **A line with money on it must not vanish unsaid.**"""
    return [NotRead(line=one.line, why=str(one)) for one in rows.refused]


def _cell(row: Row, at: int) -> str:
    return row.cells[at] if at < len(row.cells) else ""


# ---------------------------------------------------------------- one order line, collected


class _Lines:
    """What a file says about each (order, SKU), added up as the rows go by."""

    def __init__(self):
        self._settlement: Dict[Tuple[str, str], Optional[Decimal]] = {}
        self._charges: Dict[Tuple[str, str], Dict[str, Decimal]] = {}

    def states(self, key: Tuple[str, str]) -> bool:
        """Does this file already state money for that order and SKU?"""
        return key in self._settlement

    def put(self, key: Tuple[str, str], settlement: Optional[Decimal], charges: Dict[str, Decimal]) -> None:
        if settlement is None and not charges:
            return  # a line with nothing in it states nothing
        if settlement is not None:
            self._settlement[key] = (self._settlement.get(key) or Decimal(0)) + settlement
        else:
            self._settlement.setdefault(key, None)
        held = self._charges.setdefault(key, {})
        for one, figure in charges.items():
            held[one] = held.get(one, Decimal(0)) + figure

    def _the_skuless_placed(self) -> None:
        """A line with no SKU (Amazon's shipping fee for an order) belongs to its order's one SKU, when the SAME FILE names exactly one.

        **PLACED HERE, WHERE THE FILE'S OWN LINES FOR THE ORDER ARE ALL IN HAND, and not later by guessing from the ledger.** Placed
        from the ledger -- "the order's only row" -- it put a whole order's shipping on one item whenever the other item's orders
        file had not arrived yet. With several SKUs in the file it cannot be said which item the fee is for, so it stays
        without one and `ledger.plan` says it.
        """
        for key in [k for k in self._settlement if k[1] == ""]:
            names = sorted({k[1] for k in self._settlement if k[0] == key[0] and k[1] != ""})
            if len(names) != 1:
                continue
            target = (key[0], names[0])
            settlement = self._settlement.pop(key)
            charges = self._charges.pop(key)
            self.put(target, settlement, charges)

    def sales(self, platform: str, data_date: str) -> Tuple[Sale, ...]:
        self._the_skuless_placed()
        out: List[Sale] = []
        for key in sorted(self._settlement):
            settlement = self._settlement[key]
            out.append(Sale(
                platform=platform,
                order_id=key[0],
                sku=key[1],
                settlement=None if settlement is None else as_text(settlement),
                charges={one: as_text(figure) for one, figure in sorted(self._charges[key].items())},
                payments_on=data_date,
            ))
        return tuple(out)


def _taken(row: Row, places: Dict[str, Sequence[int]]) -> Dict[str, Decimal]:
    """The charges one row states, positive where money was taken. **The platform's sign, turned over.**"""
    out: Dict[str, Decimal] = {}
    for charge, spots in places.items():
        for at in spots:
            figure = a_decimal(_cell(row, at))
            if figure is not None:
                out[charge] = out.get(charge, Decimal(0)) - figure
    return out


# ---------------------------------------------------------------- Flipkart

# **WHICH OF FLIPKART'S COLUMNS IS WHICH CHARGE.** The platform's own names, exactly as the file spells them (one has two
# spaces in it). `Marketplace Fee`, `Taxes` and the `Bank Settlement Value` are sums of other columns and are never added in
# again: each would count a charge twice.
FLIPKART_CHARGES: Tuple[Tuple[str, str], ...] = (
    ("commission", "Commission (Rs.)"),
    ("fixedFee", "Fixed Fee  (Rs.)"),
    ("collectionFee", "Collection Fee (Rs.)"),
    ("shipping", "Shipping Fee (Rs.)"),
    ("returnShipping", "Reverse Shipping Fee (Rs.)"),
    ("otherServices", "Pick And Pack Fee (Rs.)"),
    ("otherServices", "No Cost Emi Fee Reimbursement(Rs.)"),
    ("otherServices", "Installation Fee (Rs.)"),
    ("otherServices", "Tech Visit Fee (Rs.)"),
    ("otherServices", "Uninstallation & Packaging Fee (Rs.)"),
    ("otherServices", "Customer Add-ons Amount Recovery (Rs.)"),
    ("otherServices", "Franchise Fee (Rs.)"),
    ("otherServices", "Shopsy Marketing Fee (Rs.)"),
    ("otherServices", "Protection Fund (Rs.)"),
    ("otherServicesTax", "GST on MP Fees (Rs.)"),
    ("tcs", "TCS (Rs.)"),
    ("tds", "TDS (Rs.)"),
    ("penalty", "Product Cancellation Fee (Rs.)"),
)
FLIPKART_ORDER_ID = "Order ID"
FLIPKART_SKU = "Seller SKU"
# The settlement's heading carries its own formula after a line break, which the platform may reword; the start is the name.
FLIPKART_SETTLEMENT_STARTS = "Bank Settlement Value"


def _places(columns: Sequence[str], spec: Sequence[Tuple[str, str]], **how) -> Dict[str, List[int]]:
    out: Dict[str, List[int]] = {}
    for charge, name in spec:
        out.setdefault(charge, []).append(_where(columns, name, **how))
    return out


def _flipkart_rebates(lines: "_Lines", found) -> List[str]:
    """Flipkart's `MP Fee Rebate` sheet added to its orders: a fee given back is money paid and a charge negated. Returns what to say."""
    if isinstance(found, str):
        # **REFUSES THE FILE, like a moved column does**: said and carried on, the file would be marked read and the rebates lost.
        raise CannotRead(f"the {FLIPKART_REBATE_SHEET!r} sheet could not be read ({found}). Nothing in this file was read, so it is read again once mended.")
    columns = found.columns
    order_at = _where(columns, FLIPKART_ORDER_ID)
    sku_at = _where(columns, "SKU")
    paid_at = _where(columns, "Settlement Value (Rs.)")
    said = []
    for row in found:
        order_id = _cell(row, order_at).strip()
        paid = a_decimal(_cell(row, paid_at))
        if paid is None:
            continue
        if order_id == "":
            said.append("rebate line(s) with no order id")
            continue
        key = (order_id, _unwrap_flipkart_sku(_cell(row, sku_at)))
        if not lines.states(key):
            # **A REBATE ADDS TO WHAT THIS FILE STATES FOR THE ORDER, AND ONLY THEN.** The rebate sheet is often for orders paid in an
            # earlier workbook; as a line of its own it would REPLACE that order's settlement and other charges (the newest statement
            # wins), turning a real figure into the rebate. So it is said, and the order's money is left as it is.
            said.append("rebate line(s) for an order this file does not otherwise state, left out so they cannot replace its money")
            continue
        lines.put(key, paid, {"otherServices": -paid})
    return [f"{said.count(one)} {one}" for one in sorted(set(said))]


def read_flipkart(rows: Table, data_date: str, extras: Optional[Dict[str, object]] = None) -> WhatWasPaid:
    columns = rows.columns
    order_at = _where(columns, FLIPKART_ORDER_ID)
    sku_at = _where(columns, FLIPKART_SKU)
    paid_at = _where(columns, FLIPKART_SETTLEMENT_STARTS, starts=True)
    places = _places(columns, FLIPKART_CHARGES)

    lines = _Lines()
    not_read = _the_refused(rows)
    nameless_money = 0
    for row in rows:
        order_id = _cell(row, order_at).strip()
        paid = a_decimal(_cell(row, paid_at))
        charges = _taken(row, places)
        if order_id == "":
            # The sub-header row under the column names has no order and no figure, and is not a refusal. A line that has
            # money and no order is said.
            if paid is not None or charges:
                nameless_money += 1
            continue
        lines.put((order_id, _unwrap_flipkart_sku(_cell(row, sku_at))), paid, charges)

    aside: List[str] = []
    if nameless_money:
        aside.append(f"{nameless_money} lines with money in them and no order id")
    for name, found in (extras or {}).items():
        if name == FLIPKART_REBATE_SHEET:
            aside += _flipkart_rebates(lines, found)
        else:
            said = _lines_stating_money(name, found, lambda one: one.strip().lower().startswith("settlement value"))
            if said:
                aside.append(said)
    return WhatWasPaid(FLIPKART, lines.sales(FLIPKART, data_date), tuple(not_read), tuple(aside))


# ---------------------------------------------------------------- Meesho

# **MEESHO'S DEDUCTIONS BLOCK.** Meesho uses some names twice -- once among the revenue columns and once among the deductions --
# so these are read only AFTER the commission column, which opens the deductions. Whether the revenue block's copies of the first
# `Fixed Fee` and of `Warehousing fee (inc Gst)` are money charged or only the working behind it is not something his sample shows
# (every one of them is nought in it), so they are NOT read: a blank is honest, a guess in the money is not. **The two `Return
# premium` columns are the exception and ARE read (MEESHO_RETURN_PREMIUM)**: they have no copy in the deductions block, so nothing
# is counted twice, and Control asked for them.
MEESHO_ANCHOR = "Meesho Commission (Incl. GST)"
MEESHO_AFTER_THE_ANCHOR: Tuple[Tuple[str, str], ...] = (
    ("commission", MEESHO_ANCHOR),
    ("otherServices", "Meesho gold platform fee (Incl. GST)"),
    ("otherServices", "Meesho mall platform fee (Incl. GST)"),
    ("fixedFee", "Fixed Fee (Incl. GST)"),
    ("warehousing", "Warehousing fee (Incl. GST)"),
    ("returnShipping", "Return Shipping Charge (Incl. GST)"),
    ("shipping", "Shipping Charge (Incl. GST)"),
    ("otherServices", "Net Other Support Service Charges (Excl. GST)"),
    ("otherServicesTax", "GST on Net Other Support Service Charges"),
    ("tcs", "TCS"),
    ("tds", "TDS"),
)
MEESHO_ORDER_ID = "Sub Order No"
MEESHO_SKU = "Supplier SKU"
MEESHO_SETTLEMENT = "Final Settlement Amount"
# **MEESHO'S RETURN PREMIUM (job 15 c):** two columns in the revenue block, each named exactly once in the file. Both are in Meesho's own
# settlement formula (read off the sample's formula row), so each is money that belongs on the order, and it is read like every other
# charge: the platform's sign, turned over. **His sample has nought in both, so the sign is the platform's usual, not one seen.**
MEESHO_RETURN_PREMIUM: Tuple[Tuple[str, str], ...] = (
    ("returnPremium", "Return premium (incl GST)"),
    ("returnPremium", "Return premium (incl GST) of Return"),
)

# **THE OTHER SHEETS OF A PAYMENTS WORKBOOK (job 15 c).** Each has group names on row 1 and column names on row 2, like the orders sheet.
EXTRA_HEADER_ROW = 2
# Flipkart's `MP Fee Rebate` names an order and an item: a marketplace fee given back for it. It is added to that order's settlement and,
# as a fee returned, to its other charges as a negative.
FLIPKART_REBATE_SHEET = "MP Fee Rebate"
# Every other Flipkart sheet carrying money names no order (a claim, a fine, a storage fee, an ad top-up, a tax recovery). Said by kind,
# counted by the lines that state a figure under the sheet's `Settlement Value` column. **COUNTS ONLY, never the amounts**: this goes
# in a log, and what he was fined is in the file.
FLIPKART_SHEETS_WITH_NO_ORDER = (
    "Non_Order_SPF", "Storage_Recall", "Value Added Services", "Support Services Services", "Fines", "Google Ads Services",
    "Review Accelerator Services", "Insight Subscription Services", "Ads", "TCS_Recovery", "TDS",
)
# Meesho's three money sheets that are not about one order, and the column whose figure makes a line a line.
MEESHO_SHEETS_WITH_NO_ORDER = {
    "Ads Cost": "Total Ads Cost",
    "Referral Payments": "Net Referral Amount",
    "Compensation and Recovery": "Amount (inc GST) INR",
}


def other_sheets_of(platform: str) -> Tuple[str, ...]:
    """The sheets besides the orders sheet that this reads, by name. None for Amazon, whose file is one report."""
    key = (platform or "").strip().lower()
    if key == FLIPKART:
        return (FLIPKART_REBATE_SHEET,) + FLIPKART_SHEETS_WITH_NO_ORDER
    if key == MEESHO:
        return tuple(MEESHO_SHEETS_WITH_NO_ORDER)
    return ()


def _lines_stating_money(name: str, found, amount_test: Callable[[str], bool]) -> Optional[str]:
    """One sentence about a sheet that belongs to no sale, or nothing when it holds no line with a figure.

    `found` is the sheet read as a table, or the words saying why it could not be read -- which is said too, since a sheet whose
    columns moved may be holding money.
    """
    if isinstance(found, str):
        return f"the {name!r} sheet could not be read ({found}), so any money in it is not counted"
    amounts = [at for at, one in enumerate(found.columns) if amount_test(one)]
    if len(amounts) != 1:
        return (
            f"the {name!r} sheet has {len(amounts)} columns that could state its money, so its lines could not be counted"
        )
    count = sum(1 for row in found if a_decimal(_cell(row, amounts[0])) is not None)
    if not count:
        return None
    return f"{count} line(s) in the {name!r} sheet, which belong to no sale"


def read_meesho(rows: Table, data_date: str, extras: Optional[Dict[str, object]] = None) -> WhatWasPaid:
    columns = rows.columns
    order_at = _where(columns, MEESHO_ORDER_ID)
    sku_at = _where(columns, MEESHO_SKU)
    paid_at = _where(columns, MEESHO_SETTLEMENT)
    anchor = _where(columns, MEESHO_ANCHOR)
    places: Dict[str, List[int]] = {}
    for charge, name in MEESHO_AFTER_THE_ANCHOR:
        at = anchor if name == MEESHO_ANCHOR else _where(columns, name, after=anchor)
        places.setdefault(charge, []).append(at)
    for charge, name in MEESHO_RETURN_PREMIUM:
        places.setdefault(charge, []).append(_where(columns, name))

    lines = _Lines()
    nameless_money = 0
    for row in rows:
        order_id = _cell(row, order_at).strip()
        paid = a_decimal(_cell(row, paid_at))
        charges = _taken(row, places)
        if order_id == "":
            if paid is not None or charges:
                nameless_money += 1
            continue
        lines.put((order_id, _cell(row, sku_at).strip()), paid, charges)

    aside: List[str] = []
    if nameless_money:
        aside.append(f"{nameless_money} lines with money in them and no order id")
    for name, found in (extras or {}).items():
        wanted = MEESHO_SHEETS_WITH_NO_ORDER[name]
        said = _lines_stating_money(name, found, lambda one, wanted=wanted: one.strip() == wanted)
        if said:
            aside.append(said)
    return WhatWasPaid(MEESHO, lines.sales(MEESHO, data_date), tuple(_the_refused(rows)), tuple(aside))


# ---------------------------------------------------------------- Amazon

# **AMAZON'S OWN DEFINITIONS, from the block at the top of its file:** `selling fees` are the variable closing fees and referral
# fees; `other transaction fees` are shipping chargebacks, shipping holdbacks and sales tax collection fees; `other` is non-order
# transaction amounts. So selling fees are the commission, and the shipping chargebacks are shipping. `fba fees` are fulfilment
# fees and go to other services, as `other` does. The three TCS columns are one tax and are added.
AMAZON_CHARGES: Tuple[Tuple[str, str], ...] = (
    ("commission", "selling fees"),
    ("shipping", "other transaction fees"),
    ("otherServices", "fba fees"),
    ("otherServices", "other"),
    ("tcs", "TCS-CGST"),
    ("tcs", "TCS-SGST"),
    ("tcs", "TCS-IGST"),
    ("tds", "TDS (Section 194-O)"),
)
AMAZON_ORDER_ID = "order id"
AMAZON_SKU = "Sku"
AMAZON_KIND = "type"
AMAZON_TOTAL = "total"
AMAZON_STATUS = "Transaction Status"
AMAZON_RELEASED = "released"


def read_amazon(rows: Table, data_date: str, extras: Optional[Dict[str, object]] = None) -> WhatWasPaid:
    columns = rows.columns
    order_at = _where(columns, AMAZON_ORDER_ID)
    sku_at = _where(columns, AMAZON_SKU)
    kind_at = _where(columns, AMAZON_KIND)
    total_at = _where(columns, AMAZON_TOTAL)
    status_at = _where(columns, AMAZON_STATUS)
    places = _places(columns, AMAZON_CHARGES)

    lines = _Lines()
    no_order: Dict[str, int] = {}
    not_yet: Dict[str, int] = {}
    for row in rows:
        kind = _cell(row, kind_at).strip() or "unnamed"
        order_id = _cell(row, order_at).strip()
        if order_id == "":
            no_order[kind] = no_order.get(kind, 0) + 1
            continue
        status = _cell(row, status_at).strip()
        if status.lower() != AMAZON_RELEASED:
            # **MONEY AMAZON HAS NOT RELEASED IS NOT MONEY HE HAS BEEN PAID.** A later file says it again once it is released,
            # and the newest statement wins.
            word = status or "no status"
            not_yet[word] = not_yet.get(word, 0) + 1
            continue
        lines.put((order_id, _cell(row, sku_at).strip()), a_decimal(_cell(row, total_at)), _taken(row, places))

    aside: List[str] = []
    for kind, count in sorted(no_order.items()):
        aside.append(f"{count} {kind!r} lines with no order id, which belong to no sale")
    for word, count in sorted(not_yet.items()):
        aside.append(f"{count} lines the platform marks {word!r} rather than released, left for a later file")
    return WhatWasPaid(AMAZON, lines.sales(AMAZON, data_date), tuple(_the_refused(rows)), tuple(aside))


# ---------------------------------------------------------------- the one door

READERS: Dict[str, Callable[..., WhatWasPaid]] = {
    AMAZON: read_amazon,
    FLIPKART: read_flipkart,
    MEESHO: read_meesho,
}


def read_payments(rows: Table, platform: str, data_date: str, extras: Optional[Dict[str, object]] = None) -> WhatWasPaid:
    """A payments file's rows, turned into what was paid on each order.

    **THE FILE'S DAY IS REFUSED IF IT IS NOT A DAY**, exactly as `orders.read_orders` refuses it: it goes into `paymentsOn`,
    which decides whether an older file may put its figure over a newer one.
    """
    if the_day_in(data_date) != data_date:
        raise CannotRead(
            f"{data_date!r} is not a day this can read, so nothing in this file was read. The marker saying which day's "
            "file wrote a row decides whether an older file may put its figure back over a newer one."
        )
    reader = READERS.get((platform or "").strip().lower())
    if reader is None:
        raise CannotRead(
            f"Nothing here knows how to read {platform!r}'s payments. It knows: " + ", ".join(sorted(READERS)) + "."
        )
    return reader(rows, data_date, extras)


# ---------------------------------------------------------------- a file to ask a question with

A_DAY_TO_ASK_WITH = "0001-01-02"


def the_columns_a_file_of(platform: str) -> Tuple[str, ...]:
    """Every column a payments file of that platform must have, in an order the reader can read. Asked of the reader's own lists."""
    key = (platform or "").strip().lower()
    if key == FLIPKART:
        return (FLIPKART_ORDER_ID, FLIPKART_SKU, FLIPKART_SETTLEMENT_STARTS + " (Rs.)") + tuple(
            name for _, name in FLIPKART_CHARGES
        )
    if key == MEESHO:
        return (MEESHO_ORDER_ID, MEESHO_SKU, MEESHO_SETTLEMENT) + tuple(
            name for _, name in MEESHO_RETURN_PREMIUM
        ) + tuple(name for _, name in MEESHO_AFTER_THE_ANCHOR)
    if key == AMAZON:
        return (AMAZON_ORDER_ID, AMAZON_SKU, AMAZON_KIND, AMAZON_TOTAL, AMAZON_STATUS) + tuple(
            name for _, name in AMAZON_CHARGES
        )
    raise CannotRead(f"Nothing here knows {platform!r}'s payments.")


def a_table_to_ask_with(platform: str) -> Table:
    """A one-line payments table built out of the reader's own column names, for driving the reader without a file.

    **NOTHING HERE SPELLS A COLUMN.** The names come from the lists the reader itself reads by, so a platform whose file changes
    shape changes this with it. It is the same idea as the one-row orders file `reading.would_a_file_say_which_day_it_is` makes.
    """
    from table import where_each_column_is  # noqa: PLC0415 - kept beside its one use

    names = the_columns_a_file_of(platform)
    where, ambiguous = where_each_column_is(names)
    said = {
        FLIPKART_ORDER_ID: "asking-whether-a-file-says-which-day-it-is",
        MEESHO_ORDER_ID: "asking-whether-a-file-says-which-day-it-is",
        AMAZON_ORDER_ID: "asking-whether-a-file-says-which-day-it-is",
        AMAZON_STATUS: "Released",
        AMAZON_KIND: "Order",
    }
    cells = tuple(
        said.get(name, "") if name in said
        else ("1" if name in (MEESHO_SETTLEMENT, AMAZON_TOTAL) or name.startswith(FLIPKART_SETTLEMENT_STARTS) else "")
        for name in names
    )
    return Table(columns=tuple(names), rows=(Row(line=2, cells=cells, _where=where, _ambiguous=ambiguous),))
