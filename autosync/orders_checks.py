"""Checks for which of a platform's columns is the SKU, the quantity, the money.

**THE COLUMN NAMES ARE NOT TYPED OUT IN THIS FILE. They are read off HIS REAL
FILES and compared** -- so a name that has drifted from what Meesho, Flipkart or
Amazon actually writes goes red against the platform's own file rather than
against somebody's memory of it.

**AND THE ROWS THAT MUST NOT READ ARE BUILT BY HAND**, because his real files are
clean: nothing in them has a broken date or a missing order number, so a check
that only ever reads them would say nothing at all about what happens when one
does.

Run: python autosync/orders_checks.py
     RAW_DATA=/nowhere python autosync/orders_checks.py   (to see it say so)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import landing  # noqa: E402
import orders as tool  # noqa: E402
import sheet  # noqa: E402
import table  # noqa: E402

ran = 0
failures = []
not_run = []
THREW = []

HIS_FILES = Path(os.environ.get("RAW_DATA") or r"H:\My Drive\Rumee Raw Data")


def answered(work):
    try:
        return work()
    except Exception as wrong:  # noqa: BLE001
        THREW.append(repr(wrong))
        return None


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


def refused_by(work):
    """True when that raises `CannotRead`, and nothing else."""
    try:
        work()
    except table.CannotRead:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


def _catch(work):
    try:
        work()
    except Exception as e:  # noqa: BLE001
        return e
    return None


TAB = "\t"
LF = "\n"


def a_file(columns, *rows):
    """A tab-separated file with those columns and those rows."""
    out = [TAB.join(columns)]
    for r in rows:
        out.append(TAB.join(r))
    return table.read(LF.join(out) + LF)


# ------------------------------------------------------------- a day, never guessed

check("a plain day is read", tool.the_day_in("2026-08-30") == "2026-08-30")
check("a day with a time after it is read", tool.the_day_in("2026-08-19 11:24:07") == "2026-08-19")
check("and one written the way Amazon writes it",
      tool.the_day_in("2026-09-01T16:22:51+00:00") == "2026-09-01")
check("A DAY-FIRST DATE IS REFUSED, NOT GUESSED AT",
      tool.the_day_in("26.08.2026") is None)
check("and so is the one that would have been silently wrong -- 1 September read as 9 January",
      tool.the_day_in("01.09.2026") is None)
check("an American one is refused too", tool.the_day_in("08/26/2026") is None)
check("a day that cannot exist is refused rather than rounded",
      tool.the_day_in("2026-02-31") is None)
check("and one whose month cannot exist", tool.the_day_in("2026-13-01") is None)
check("nothing at all is refused", tool.the_day_in("") is None and tool.the_day_in(None) is None)
check("a real leap day is fine", tool.the_day_in("2028-02-29") == "2028-02-29")

# ------------------------------------------------------------------ a figure

check("a figure comes back as the platform wrote it", tool.a_figure("349.0") == "349.0")
check("and is not turned into a number and back", tool.a_figure("349.00") == "349.00")
check("a negative one is a figure", tool.a_figure("-423.296") == "-423.296")
check("A NOUGHT IS A FIGURE", tool.a_figure("0") == "0")
check("and so is a fractional nought", tool.a_figure("0.0") == "0.0")
check("A BLANK IS NOTHING, NOT NOUGHT", tool.a_figure("") is None)
check("and words are not a figure", tool.a_figure("about 200") is None)

# ------------------------------------------------- unwrapping Flipkart's SKU

check("Flipkart's wrapper comes off",
      tool._unwrap_flipkart_sku('"""SKU:DJ 14 Bahubali"""') == "DJ 14 Bahubali")
check("and the SKU itself is not otherwise touched -- spacing kept",
      tool._unwrap_flipkart_sku('"""SKU:DJ-5 Bahu (2)"""') == "DJ-5 Bahu (2)")
check("its case is not changed either",
      tool._unwrap_flipkart_sku('"""SKU:DJ-11 BAHUBALI"""') == "DJ-11 BAHUBALI")
check("a SKU with no wrapper is left alone", tool._unwrap_flipkart_sku("PLAIN-1") == "PLAIN-1")
check("and nothing stays nothing", tool._unwrap_flipkart_sku("") == "")

# ------------------------------------------------------- what each one is called

check("three platforms are known", set(tool.EVERY_MAPPING) == {"meesho", "flipkart", "amazon"})
check("a platform nobody knows is refused, naming the ones known",
      refused_by(lambda: tool.mapping_for("myntra")))
check("and the refusal lists them",
      (lambda e: e is not None and "meesho" in str(e) and "amazon" in str(e))(
          _catch(lambda: tool.mapping_for("myntra"))))
check("FLIPKART'S ORDERS FILE IS KNOWN TO HAVE NO MONEY COLUMN",
      tool.FROM_FLIPKART.gmv is None)
check("and the other two are known to have one",
      tool.FROM_MEESHO.gmv is not None and tool.FROM_AMAZON.gmv is not None)
check("the money is never one of the columns a file cannot do without",
      all(m.gmv not in m.needs for m in tool.EVERY_MAPPING.values()))
check("Meesho's own spelling of Commision is kept exactly as Meesho writes it",
      "Commision" in tool.FROM_MEESHO.gmv)
check("only Flipkart's SKU is unwrapped",
      tool.FROM_FLIPKART.unwrap_sku
      and not tool.FROM_MEESHO.unwrap_sku and not tool.FROM_AMAZON.unwrap_sku)

# ------------------------------------------------------- a moved column stops it

GOOD = ("Sub Order No", "SKU", "Quantity", "Order Date", "Reason for Credit Entry",
        "Supplier Discounted Price (Incl GST and Commision)")
rows = a_file(GOOD, ("S1", "AAA", "2", "2026-08-30", "SHIPPED", "174.0"))
r = answered(lambda: tool.read_orders(rows, "meesho"))
check("a good file reads", r is not None and len(r.sales) == 1)

# ------------------------------------ WHICH DAY'S FILE THE SALE CAME OUT OF (D157)

# **ONE ROW OF EACH PLATFORM'S OWN FILE, in that platform's own column names.**
# Written out here rather than taken off the mapping, because a fixture built
# from the thing under check agrees with it about anything.
_EVERY_PLATFORM_FILE = (
    (a_file(GOOD, ("S1", "AAA", "2", "2026-08-30", "SHIPPED", "174.0")), "meesho"),
    (a_file(("order_id", "sku", "quantity", "order_date", "order_item_status"),
            ("OD1", "AAA", "1", "2026-08-30", "SHIPPED")), "flipkart"),
    (a_file(("amazon-order-id", "sku", "quantity", "purchase-date", "order-status",
             "item-price"),
            ("AZ1", "AAA", "1", "2026-08-30T10:00:00+00:00", "Shipped", "199.0")),
     "amazon"),
)

# **THE FIRST OF THE FOUR DATE MARKERS EVER TO BE FILLED BY ANYTHING.** They
# landed in the ERP's column list on 2026-09-06 and every refusal built on their
# NAMES lifted itself the same day; nothing anywhere assigned one, so every row
# written still could not say which day's file produced it.
_dated = answered(lambda: tool.read_orders(rows, "meesho", data_date="2026-08-31"))
check("A SALE CARRIES THE DAY OF THE FILE IT CAME OUT OF",
      _dated is not None and _dated.sales[0].orders_on == "2026-08-31")
# **THE FILE'S DAY, NOT THE ROW'S OWN.** The row says the sale happened on the
# 30th and the file is the 31st's statement about it. Read off the row instead,
# the marker would say a statement is older or newer than it is -- which is the
# one thing it exists to answer.
check("and it is the FILE'S day, not the day the sale itself happened",
      _dated is not None and _dated.sales[0].on == "2026-08-30"
      and _dated.sales[0].orders_on == "2026-08-31")
check("and the other three markers are left blank rather than guessed",
      _dated is not None and _dated.sales[0].returns_on is None
      and _dated.sales[0].payments_on is None and _dated.sales[0].claims_on is None)
# **NOT GIVEN A DAY, IT IS BLANK AND NOT TODAY.** A marker filled from the clock
# says a file is newer than it is, which is the direction that loses money.
check("not given a day, the marker is blank rather than filled from the clock",
      r is not None and r.sales[0].orders_on is None)
# **AND A DAY THAT IS NOT A DAY STOPS THE WHOLE FILE.** The marker is COMPARED --
# it is what decides whether an older file may put its figure back over a newer
# one -- so something that is not a date decides that wrongly, and silently.
check("A FILE'S DAY THAT IS NOT A DAY STOPS THE FILE, it is not written verbatim",
      refused_by(lambda: tool.read_orders(rows, "meesho", data_date="last Tuesday")))
check("and a day-first one is refused too, not read backwards",
      refused_by(lambda: tool.read_orders(rows, "meesho", data_date="31.08.2026")))
check("and the refusal says why a wrong marker matters",
      (lambda e: e is not None and "older file" in str(e))(
          _catch(lambda: tool.read_orders(rows, "meesho", data_date="last Tuesday"))))
# **EVERY PLATFORM, not just the one the fixture above happens to use.**
check("every platform's reader carries it, not only Meesho",
      all((lambda got: got is not None and bool(got.sales) and all(
              one.orders_on == "2026-08-31" for one in got.sales))(
          answered(lambda t=t, p=p: tool.read_orders(t, p, data_date="2026-08-31")))
          for t, p in _EVERY_PLATFORM_FILE))

MOVED = ("Sub Order No", "SKU", "Qty", "Order Date", "Reason for Credit Entry")
check("A COLUMN THAT HAS MOVED STOPS THE WHOLE FILE",
      refused_by(lambda: tool.read_orders(
          a_file(MOVED, ("S1", "AAA", "2", "2026-08-30", "SHIPPED")), "meesho")))
check("and says which one, once, rather than once per row",
      (lambda e: e is not None and "'Quantity'" in str(e))(
          _catch(lambda: tool.read_orders(
              a_file(MOVED, ("S1", "AAA", "2", "2026-08-30", "SHIPPED")), "meesho"))))
check("and names the columns it DID find, so the new name can be seen",
      (lambda e: e is not None and "'Qty'" in str(e))(
          _catch(lambda: tool.read_orders(
              a_file(MOVED, ("S1", "AAA", "2", "2026-08-30", "SHIPPED")), "meesho"))))
check("A MISSING MONEY COLUMN DOES NOT STOP THE FILE",
      (lambda x: x is not None and len(x.sales) == 1 and x.sales[0].gmv is None)(
          answered(lambda: tool.read_orders(
              a_file(GOOD[:5], ("S1", "AAA", "2", "2026-08-30", "SHIPPED")), "meesho"))))

# ------------------------------------------- one bad row must not lose the file

MIXED = a_file(
    GOOD,
    ("S1", "AAA", "2", "2026-08-30", "SHIPPED", "174.0"),
    ("S2", "BBB", "1", "26.08.2026", "SHIPPED", "200.0"),      # day-first
    ("S3", "CCC", "many", "2026-08-30", "SHIPPED", "300.0"),   # quantity in words
    ("", "DDD", "1", "2026-08-30", "SHIPPED", "400.0"),        # no order number
    ("S5", "EEE", "3", "2026-08-30", "SHIPPED", "500.0"),
)
r = answered(lambda: tool.read_orders(MIXED, "meesho"))
check("three bad rows do not lose the other two", r is not None and len(r.sales) == 2)
check("and all three are kept by name", r is not None and len(r.not_read) == 3)
check("the day-first row is named by its line", r is not None and r.not_read[0].line == 3)
check("and its reason says the day was refused rather than guessed",
      r is not None and "guessed" in r.not_read[0].why)
check("the words-for-a-quantity row says so", r is not None and "not a number" in r.not_read[1].why)
check("the row with no order number says why that matters",
      r is not None and "no order number" in r.not_read[2].why)
check("the good rows either side of them are both read",
      r is not None and {s.order_id for s in r.sales} == {"S1", "S5"})
check("what was read is said in one line, bad rows included",
      r is not None and "2 sales read" in r.says() and "3 rows could not be read" in r.says())
check("and a clean read still says nought could not be read, rather than staying quiet",
      "0 rows could not be read" in tool.read_orders(rows, "meesho").says())

# ------------------------------------------------- the platform's own word

r = answered(lambda: tool.read_orders(a_file(
    GOOD,
    ("S1", "A", "1", "2026-08-30", "SHIPPED", "1"),
    ("S2", "B", "1", "2026-08-30", "CANCELLED", "1"),
    ("S3", "C", "1", "2026-08-30", "CANCELLED", "1"),
), "meesho"))
check("CANCELLED ROWS ARE READ, NOT DROPPED -- a dropped row corrects nothing tomorrow",
      r is not None and len(r.sales) == 3)
check("and the platform's own word is counted so it is never silent",
      r is not None and dict(r.their_words) == {"SHIPPED": 1, "CANCELLED": 2})
check("it is said out loud in what the read reports",
      r is not None and "CANCELLED x2" in r.says())
check("BUT IT IS NOT WRITTEN TO A COLUMN -- notes is the seller's own typing",
      r is not None and all(s.notes is None for s in r.sales))
check("and no sale is given a state -- a sale read from a file has not been applied",
      r is not None and all(s.state is None for s in r.sales))

# --------------------------------------------- the same file twice changes nothing

import sales as sales_tool  # noqa: E402

TWICE = a_file(GOOD,
               ("S1", "AAA", "2", "2026-08-30", "SHIPPED", "174.0"),
               ("S1", "AAA", "2", "2026-08-30", "SHIPPED", "174.0"))
r = answered(lambda: tool.read_orders(TWICE, "meesho"))
check("a sale stated twice in one file is two sales read", r is not None and len(r.sales) == 2)
check("BUT ONE ROW IN THE SHEET", r is not None and len(sales_tool.by_name(r.sales)) == 1)
check("and reading the same file again gives the same names",
      sales_tool.by_name(tool.read_orders(TWICE, "meesho").sales).keys()
      == sales_tool.by_name(tool.read_orders(TWICE, "meesho").sales).keys())

# ------------------------------------------------- and now HIS REAL FILES

REAL = [
    ("meesho", HIS_FILES / "meesho" / "orders" / "meesho_orders_2026-08-30.csv",
     None, 12, True),
    ("flipkart", HIS_FILES / "flipkart" / "orders" / "flipkart_orders_2026-08-20.xlsx",
     "Orders", 63, False),
    ("amazon", HIS_FILES / "amazon" / "amazon_az_orders_2026-09-02.csv",
     None, 46, True),
]

for platform, path, which, how_many, has_money in REAL:
    if not path.is_file():
        not_run.append(f"{platform} -- {path} is not on this machine")
        print(f"NOT RUN  his real {platform} orders: {path} is not here")
        continue
    raw = path.read_bytes()
    rows = answered(lambda r=raw, w=which: sheet.read(r, sheet=w) if w else table.read(r))
    # **THE DAY OFF THE REAL FILE'S OWN NAME, through the one function the run
    # uses.** A day typed into this check would be a second way of reading a
    # date off a name, and two ways of reading one thing is two answers waiting
    # to disagree.
    its_day = landing.data_date_in(path.name)
    got = answered(lambda t=rows, p=platform, d=its_day:
                   tool.read_orders(t, p, data_date=d.isoformat() if d else None))
    check(f"his real {platform} orders: every column this needs is there",
          got is not None)
    check(f"his real {platform} orders: {how_many} sales", got is not None and len(got.sales) == how_many)
    check(f"his real {platform} orders: NOT ONE ROW was unreadable",
          got is not None and got.not_read == ())
    check(f"his real {platform} orders: every sale can be named",
          got is not None and all(s.id.count("::") == 2 for s in got.sales))
    check(f"his real {platform} orders: every day is a real day",
          got is not None and all(tool.the_day_in(s.on) == s.on for s in got.sales))
    check(f"HIS REAL {platform.upper()} ORDERS: every sale says which day's file it came out of",
          its_day is not None and got is not None and bool(got.sales)
          and all(one.orders_on == its_day.isoformat() for one in got.sales))
    check(f"his real {platform} orders: the money is "
          + ("there" if has_money else "ABSENT, because the file has none"),
          got is not None and (
              any(s.gmv for s in got.sales) if has_money
              else all(s.gmv is None for s in got.sales)))

fk = HIS_FILES / "flipkart" / "orders" / "flipkart_orders_2026-08-20.xlsx"
if fk.is_file():
    got = answered(lambda: tool.read_orders(
        sheet.read(fk.read_bytes(), sheet="Orders"), "flipkart"))
    check("his real Flipkart SKUs come out unwrapped",
          got is not None and all('"' not in s.sku and not s.sku.upper().startswith("SKU:")
                                  for s in got.sales))
    check("and one of them is exactly what is on his listing",
          got is not None and any(s.sku == "DJ 14 Bahubali" for s in got.sales))
    check("HIS REAL FLIPKART ORDERS CARRY CANCELLATIONS, and they are counted not dropped",
          got is not None and dict(got.their_words).get("CANCELLED", 0) > 0)

if not_run:
    print()
    print(f"      {len(not_run)} group(s) NOT RUN -- his real files are not on this machine:")
    for one in not_run:
        print(f"        {one}")
    print("      They are not passes.")

print()
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

WITH_HIS_FILES = 85
WITHOUT = WITH_HIS_FILES - 7 * len(REAL) - 3
EXPECTED = WITH_HIS_FILES if not not_run else WITHOUT
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print(f"all {ran} checks passed"
      + (f" ({len(not_run)} group(s) not run -- his real files are elsewhere)" if not_run else ""))
