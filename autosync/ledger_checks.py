"""Checks for what goes into the seller's sales ledger.

**EVERY RULE HERE IS ONE HE SET, and the decision it comes from is named** --
D150 (each report writes only what it knows; the newest file wins; a tie is
reported, never picked) and D152 (one row per order LINE, the row is updated
never split).

**AND IT IS RUN AGAINST HIS REAL FILES**: 121 real sales into an empty sheet,
then the same three files again, which must change nothing.

Run: python autosync/ledger_checks.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ledger as tool  # noqa: E402
import orders  # noqa: E402
import sales  # noqa: E402
import sheet  # noqa: E402
import table  # noqa: E402

ran = 0
failures = []
not_run = []
THREW = []

HIS_FILES = Path(os.environ.get("RAW_DATA") or r"H:\My Drive\Rumee Raw Data")

# What an ORDERS report is entitled to say. It knows nothing about settlements,
# returns or charges, and rule 1 makes that impossible to forget.
ORDERS_KNOWS = ("platform", "orderId", "on", "sku", "qty", "gmv")


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
    """True when that raises `LedgerRefused`, and nothing else."""
    try:
        work()
    except tool.LedgerRefused:
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


HEADER = [list(sales.COLUMNS)]
AT = {c: n for n, c in enumerate(sales.COLUMNS)}


def a_sale(order_id, sku="A", **rest):
    return sales.Sale(platform="meesho", order_id=order_id, sku=sku, **rest)


def a_reading(report, on, sale_list, knows=ORDERS_KNOWS):
    return tool.Reading(report=report, on=on, knows=knows, sales=tuple(sale_list))


def as_sheet(plan_rows):
    return HEADER + [list(r) for r in plan_rows]


# ------------------------------------------------------- what a reading must say

check("a reading with no report name is refused",
      refused_by(lambda: a_reading("", "2026-08-01", [])))
check("A READING WITH NO FILE DATE IS REFUSED -- the newest is supposed to win",
      refused_by(lambda: a_reading("orders", "", [])))
check("and the refusal says why the date matters",
      (lambda e: e is not None and "newer" in str(e))(
          _catch(lambda: a_reading("orders", "", []))))
check("a reading claiming a column the ledger does not have is refused",
      refused_by(lambda: a_reading("orders", "2026-08-01", [], knows=("nonsense",))))
check("and the refusal lists the columns there are",
      (lambda e: e is not None and "settlement" in str(e))(
          _catch(lambda: a_reading("orders", "2026-08-01", [], knows=("nonsense",)))))
check("a reading that can write nothing at all is refused, not quietly ignored",
      refused_by(lambda: a_reading("orders", "2026-08-01", [], knows=())))

# --------------------------------------------------------- an empty sheet

p = answered(lambda: tool.plan([], [a_reading("orders", "2026-08-01", [a_sale("O1")])]))
check("a sale going into an empty sheet is added", p is not None and len(p.append) == 1)
check("and nothing is updated", p is not None and p.update == ())
check("the row has one cell per column", p is not None and len(p.append[0]) == len(sales.COLUMNS))
check("its id is the sale's own name",
      p is not None and p.append[0][AT["id"]] == "meesho::O1::A")
check("a column the report knows nothing about is BLANK, not invented",
      p is not None and p.append[0][AT["settlement"]] == "")
check("what it did is said in one line, every count including the noughts",
      p is not None and "1 sales added" in p.says() and "0 updated" in p.says()
      and "0 disagreements" in p.says())

# ------------------------------------------------- the same file, twice

first = tool.plan([], [a_reading("orders", "2026-08-01", [a_sale("O1", gmv=100)])])
now = as_sheet(first.append)
again = answered(lambda: tool.plan(now, [a_reading("orders", "2026-08-01", [a_sale("O1", gmv=100)])]))
check("THE SAME FILE AGAIN CHANGES NOTHING", again is not None and not again.changes_anything)
check("it adds nothing", again is not None and again.append == ())
check("and updates nothing", again is not None and again.update == ())

# ------------------------------------------------------ RULE 1 (D150)

# A payments-shaped report that knows only the money must not touch the date.
WITH_A_DATE = tool.plan([], [a_reading("orders", "2026-08-01",
                                       [a_sale("O1", on="2026-08-01", gmv=100)])])
after_pay = answered(lambda: tool.plan(
    as_sheet(WITH_A_DATE.append),
    [tool.Reading(report="payments", on="2026-08-28", knows=("settlement",),
                  sales=(a_sale("O1", on="", gmv=None, settlement=250),))]))
check("RULE 1: a payments file writes the money it knows",
      after_pay is not None and len(after_pay.update) == 1)
check("RULE 1: and the settlement it stated is there",
      after_pay is not None and after_pay.update[0][1][AT["settlement"]] == "250")

# **SAYING NOTHING IS NOT SAYING "NOTHING", and this check found the fault.**
# A payments file that knows about the settlement but carries no figure for THIS
# sale must not blank the one written last week.
SAYS_NOTHING = answered(lambda: tool.plan(
    as_sheet(after_pay.update[0][1:] and
             [after_pay.update[0][1]] or []),
    [tool.Reading(report="payments", on="2026-09-01", knows=("settlement",),
                  sales=(a_sale("O1", settlement=None),))]))
check("RULE 1: A BLANK NEVER OVERWRITES A FIGURE THAT IS ALREADY THERE",
      SAYS_NOTHING is not None and SAYS_NOTHING.update == ())
# **THE CHECK THAT ACTUALLY PROVES RULE 1, and the proving pass is why it
# exists.** Dropping rule 1 altogether was SURVIVING every check above, because
# those sales carried no value for the columns they were not entitled to -- so
# writing every column wrote blanks, and the blank-guard beside it swallowed
# them. A report has to carry a REAL figure for a column it has no business in.
GREEDY = answered(lambda: tool.plan(
    as_sheet(WITH_A_DATE.append),
    [tool.Reading(report="payments", on="2026-08-28", knows=("settlement",),
                  sales=(a_sale("O1", settlement=250, qty=999, on="1999-01-01"),))]))
check("RULE 1: A REPORT'S REAL FIGURE FOR A COLUMN IT DOES NOT KNOW IS NOT WRITTEN",
      GREEDY is not None and GREEDY.update[0][1][AT["qty"]] != "999")
check("RULE 1: and its date does not land either",
      GREEDY is not None and GREEDY.update[0][1][AT["on"]] == "2026-08-01")
check("RULE 1: while the one column it DOES know is written",
      GREEDY is not None and GREEDY.update[0][1][AT["settlement"]] == "250")

check("RULE 1: AND DOES NOT WIPE THE DATE IT KNOWS NOTHING ABOUT",
      after_pay is not None and after_pay.update[0][1][AT["on"]] == "2026-08-01")
check("RULE 1: nor the money the orders file had put there",
      after_pay is not None and after_pay.update[0][1][AT["gmv"]] == "100")
check("the version moves on a change, or every guarded write goes out unguarded",
      after_pay is not None and after_pay.update[0][1][AT["rev"]] == "1")

# ------------------------------------------------------ RULE 2 (D150)

OLD = a_reading("orders", "2026-08-01", [a_sale("O1", gmv=100)])
NEW = a_reading("payments", "2026-08-28", [a_sale("O1", gmv=999)])
p = answered(lambda: tool.plan([], [NEW, OLD]))
check("RULE 2: THE NEWEST FILE WINS, whatever order the files were handed over in",
      p is not None and p.append[0][AT["gmv"]] == "999")
p = answered(lambda: tool.plan([], [OLD, NEW]))
check("RULE 2: and the same answer the other way round -- fetching order decides nothing",
      p is not None and p.append[0][AT["gmv"]] == "999")
check("RULE 2: newness is the FILE'S DATE, not the order it arrived in",
      p is not None and len(p.append) == 1)

# ------------------------------------------------------ RULE 3 (D150)

SAME_DAY_A = a_reading("orders", "2026-08-28", [a_sale("O1", gmv=100)])
SAME_DAY_B = a_reading("payments", "2026-08-28", [a_sale("O1", gmv=200)])
p = answered(lambda: tool.plan([], [SAME_DAY_A, SAME_DAY_B]))
check("RULE 3: two files of the SAME DATE disagreeing keeps what is there",
      p is not None and p.append[0][AT["gmv"]] == "100")
check("RULE 3: and the disagreement is REPORTED, never silently picked",
      p is not None and len(p.disagreements) == 1)
# **GUARDED ON THERE BEING ONE.** Reached straight, a fault that stops rule 3
# firing makes these THROW rather than go red, and the file dies half way through
# with no count and nothing said about anything below. Found by putting that
# fault back.
_said = p.disagreements[0] if p is not None and p.disagreements else None
check("RULE 3: the report names the sale, the column and both figures",
      _said is not None and _said.name == "meesho::O1::A"
      and _said.column == "gmv" and _said.kept == "100" and _said.also_said == "200")
check("RULE 3: and says who said the other thing, and when",
      _said is not None and "payments" in str(_said) and "2026-08-28" in str(_said))
check("RULE 3: two files of the same date AGREEING is not a disagreement",
      (lambda x: x is not None and x.disagreements == ())(
          answered(lambda: tool.plan([], [
              a_reading("orders", "2026-08-28", [a_sale("O1", gmv=100)]),
              a_reading("payments", "2026-08-28", [a_sale("O1", gmv=100)])]))))
# **A STATEMENT IS A FILE, NOT A REPORT -- found by reviewing this against D150.**
# Told apart only by report and date, two files of the SAME report and SAME date
# looked like one statement: the second silently overwrote the first, rule 3
# never fired, and which won depended on the order they were handed over in.
TWO_FILES = [
    tool.Reading(report="meesho orders", on="2026-08-30", knows=ORDERS_KNOWS,
                 which="file-one", sales=(a_sale("O1", gmv=100),)),
    tool.Reading(report="meesho orders", on="2026-08-30", knows=ORDERS_KNOWS,
                 which="file-two", sales=(a_sale("O1", gmv=200),)),
]
p = answered(lambda: tool.plan([], TWO_FILES))
check("RULE 3: TWO FILES OF ONE REPORT AND ONE DATE ARE TWO STATEMENTS",
      p is not None and len(p.disagreements) == 1)
check("RULE 3: and neither silently overwrites the other",
      p is not None and p.append[0][AT["gmv"]] == "100")
check("RULE 3: the order they were handed over in decides nothing",
      p is not None and tool.plan([], list(reversed(TWO_FILES))).append[0][AT["gmv"]]
      == p.append[0][AT["gmv"]])
check("but TWO ROWS OF ONE FILE are still one statement, and the later row wins",
      (lambda x: x is not None and x.disagreements == () and x.append[0][AT["gmv"]] == "200")(
          answered(lambda: tool.plan([], [tool.Reading(
              report="meesho orders", on="2026-08-30", knows=ORDERS_KNOWS, which="file-one",
              sales=(a_sale("O1", gmv=100), a_sale("O1", gmv=200)))]))))
check("a reading that does not say which file it came from falls back to the report",
      tool.Reading(report="r", on="2026-08-01", knows=("gmv",), sales=()).one_statement == "r")

check("RULE 3: one report saying it twice in one file is not a disagreement",
      (lambda x: x is not None and x.disagreements == ())(
          answered(lambda: tool.plan([], [
              a_reading("orders", "2026-08-28",
                        [a_sale("O1", gmv=100), a_sale("O1", gmv=200)])]))))

# ---- RULE 3 ACROSS THE ONE-FILE-AT-A-TIME HANDOVER, WHICH IS HOW THE JOB RUNS

# **EVERY CHECK ABOVE HANDS `plan` BOTH FILES AT ONCE, AND THE JOB NEVER DOES.**
# A sale lands one file at a time -- that is what makes marking a file read safe
# -- so `plan` is called once per file and the memory it decides rule 3 in used to
# start empty every time. The tie was invisible, nothing was reported, and which
# figure the seller ended up with was settled by which Drive id sorted higher.
# **So the rule is driven here the way the job drives it: two calls, and the
# sheet in between holding what the first one wrote.**
def two_calls(first, second, carrying):
    """Two files, one at a time, into a sheet that keeps what it is given."""
    one = tool.plan([], [first], carrying)
    rows = HEADER + [list(r) for r in one.append]
    return one, tool.plan(rows, [second], carrying)


A_FILE = tool.Reading(report="meesho orders", on="2026-08-30", knows=ORDERS_KNOWS,
                      which="file-one", sales=(a_sale("O1", gmv=100),))
ANOTHER = tool.Reading(report="meesho orders", on="2026-08-30", knows=ORDERS_KNOWS,
                       which="file-two", sales=(a_sale("O1", gmv=200),))

night = tool.WhatTheNightHasDecided()
first, second = two_calls(A_FILE, ANOTHER, night)
check("RULE 3 FIRES ONE FILE AT A TIME: the tie is REPORTED, not resolved",
      second is not None and len(second.disagreements) == 1)
check("RULE 3 one file at a time: and what is already in the sheet is KEPT",
      second is not None and second.update == () and second.append == ())
# **GUARDED ON THERE BEING ONE AT ALL.** Reached straight, a fault that stops the
# tie firing makes these THROW rather than go red -- and a check file that dies
# half way through has no count and says nothing about the checks below it.
_tie = second.disagreements[0] if second is not None and second.disagreements else None
check("RULE 3 one file at a time: the report names BOTH files, not one report twice",
      _tie is not None and "file-one" in str(_tie) and "file-two" in str(_tie))
check("RULE 3 one file at a time: and says which of the two is the one standing",
      _tie is not None and _tie.kept_from == "file-one" and _tie.also_from == "file-two")

# **AND THE OTHER WAY ROUND KEEPS THE OTHER FIGURE AND STILL REPORTS.** The point
# of rule 3 is not which figure survives -- it is that nobody chose it silently.
other_way = tool.WhatTheNightHasDecided()
_, back = two_calls(ANOTHER, A_FILE, other_way)
check("RULE 3 one file at a time: the other order reports it too",
      back is not None and len(back.disagreements) == 1
      and back.disagreements[0].kept == "200" and back.disagreements[0].also_said == "100")

# **WITHOUT THE RUN'S MEMORY IT CANNOT FIRE, AND THAT IS SHOWN RATHER THAN
# ASSERTED.** This is the fault as it stood: a fresh memory for each file.
forgets_between_files = tool.plan(
    HEADER + [list(r) for r in tool.plan([], [A_FILE]).append], [ANOTHER])
check("with a fresh memory per file the tie is invisible and the second file wins",
      forgets_between_files.disagreements == ()
      and forgets_between_files.update[0][1][AT["gmv"]] == "200")

check("a night's memory starts empty and remembers what the night decided",
      len(tool.WhatTheNightHasDecided()) == 0 and len(night) > 0)
check("and a DIFFERENT DAY is not a tie -- the newer file still wins outright",
      (lambda x: x is not None and x.disagreements == ()
       and x.update[0][1][AT["gmv"]] == "200")(
          answered(lambda: two_calls(
              A_FILE,
              tool.Reading(report="meesho orders", on="2026-08-31", knows=ORDERS_KNOWS,
                           which="file-two", sales=(a_sale("O1", gmv=200),)),
              tool.WhatTheNightHasDecided())[1])))

# ---- D157'S FOUR DATE COLUMNS: NAMED, SO THAT THEIR ABSENCE IS A FACT

check("the four date-marker columns D157 asked for are named in one place",
      tool.WHICH_FILE_LAST_WROTE
      == ("ordersOn", "paymentsOn", "returnsOn", "claimsOn"))
check("NONE OF THE FOUR EXISTS YET, and this says so rather than a report saying it",
      tool.what_the_sheet_cannot_yet_say() == tool.WHICH_FILE_LAST_WROTE)
check("and the day they are in the ledger's columns, nothing is missing",
      tool.what_the_sheet_cannot_yet_say(
          tuple(sales.COLUMNS) + tool.WHICH_FILE_LAST_WROTE) == ())
check("three of the four is not good enough, and the fourth is named",
      tool.what_the_sheet_cannot_yet_say(
          tuple(sales.COLUMNS) + tool.WHICH_FILE_LAST_WROTE[:3]) == ("claimsOn",))

# ------------------------------------------------- what the sheet already holds

check("a sheet whose columns have been dragged about is REFUSED",
      refused_by(lambda: tool.plan([["id", "platform", "sku"]], [])))
check("and the refusal says what is missing",
      (lambda e: e is not None and "Missing" in str(e))(
          _catch(lambda: tool.plan([["id", "platform", "sku"]], []))))
check("a column that is not ours is named too",
      (lambda e: e is not None and "Not ours" in str(e))(
          _catch(lambda: tool.plan([list(sales.COLUMNS) + ["mine"]], []))))
check("columns in the wrong ORDER are refused, not silently reordered",
      refused_by(lambda: tool.plan([list(reversed(sales.COLUMNS))], [])))
check("an empty sheet is not a fault -- it is a first night",
      (lambda x: x is not None)(answered(lambda: tool.plan([], []))))

ROW = ["" for _ in sales.COLUMNS]
NO_ID = HEADER + [list(ROW)[:] for _ in range(1)]
NO_ID[1][AT["platform"]] = "meesho"
p = answered(lambda: tool.plan(NO_ID, []))
check("a row in the sheet with no id is named, not used",
      p is not None and len(p.unreadable) == 1 and p.unreadable[0].row == 2)
check("and every other row is still used",
      (lambda x: x is not None and len(x.unreadable) == 1)(
          answered(lambda: tool.plan(NO_ID + [["meesho::O1::A"] + ROW[1:]], []))))

# **THE SALE CARRIES A REAL FIGURE, and the proving pass is why.** With a blank
# sale, "written to one of two rows" and "not written to at all" look identical,
# so the check could not fail for the fault it is named for.
TWICE = HEADER + [["meesho::O1::A"] + ROW[1:], ["meesho::O1::A"] + ROW[1:]]
p = answered(lambda: tool.plan(TWICE, [a_reading("orders", "2026-08-01",
                                                 [a_sale("O1", gmv=500)])]))
check("A SALE ON TWO ROWS IS REPORTED and NEITHER is written to",
      p is not None and len(p.unreadable) == 1 and p.update == ())
check("and it is not added again either, which would make it three",
      p is not None and p.append == ())

# -------------------------------------------------- one row per order LINE (D152)

p = answered(lambda: tool.plan([], [a_reading("orders", "2026-08-01", [
    a_sale("O1", sku="A"), a_sale("O1", sku="B"), a_sale("O1", sku="C")])]))
check("D152: one order of three SKUs is THREE rows, not one",
      p is not None and len(p.append) == 3)
check("and each carries its own SKU",
      p is not None and sorted(r[AT["sku"]] for r in p.append) == ["A", "B", "C"])

# ---------------------------------------------------- an update, not a split

p = answered(lambda: tool.plan(
    as_sheet(tool.plan([], [a_reading("orders", "2026-08-01", [a_sale("O1", gmv=100)])]).append),
    [a_reading("orders", "2026-08-05", [a_sale("O1", gmv=150)])]))
check("D152: more happening to a sale UPDATES its row",
      p is not None and len(p.update) == 1 and p.append == ())
check("the row it updates is the one that sale is really on",
      p is not None and p.update[0][0] == 2)
check("and the new figure is there", p is not None and p.update[0][1][AT["gmv"]] == "150")

# ------------------------------------------------- and now HIS REAL FILES

REAL = [
    ("meesho", HIS_FILES / "meesho" / "orders" / "meesho_orders_2026-08-30.csv",
     None, "2026-08-30", 12),
    ("flipkart", HIS_FILES / "flipkart" / "orders" / "flipkart_orders_2026-08-20.xlsx",
     "Orders", "2026-08-20", 63),
    ("amazon", HIS_FILES / "amazon" / "amazon_az_orders_2026-09-02.csv",
     None, "2026-09-02", 46),
]

missing = [p for _, p, _, _, _ in REAL if not p.is_file()]
if missing:
    not_run.append("his real order files are not on this machine")
    print("NOT RUN  his real order files are not here")
else:
    readings = []
    for platform, path, which, on, _ in REAL:
        raw = path.read_bytes()
        rows = sheet.read(raw, sheet=which) if which else table.read(raw)
        readings.append(a_reading(f"{platform} orders", on,
                                  orders.read_orders(rows, platform).sales))
    first = answered(lambda: tool.plan([], readings))
    check("HIS REAL FILES: 121 sales go into an empty ledger",
          first is not None and len(first.append) == 121)
    check("his real files: nothing is updated on a first night",
          first is not None and first.update == ())
    check("his real files: no disagreements between the three orders reports",
          first is not None and first.disagreements == ())
    check("his real files: every row has one cell per column",
          first is not None and all(len(r) == len(sales.COLUMNS) for r in first.append))
    check("his real files: every row carries the sale's own name",
          first is not None and all(r[AT["id"]].count("::") == 2 for r in first.append))
    check("HIS REAL FLIPKART ROWS HAVE THEIR MONEY BLANK, because that file has none",
          first is not None and all(
              r[AT["gmv"]] == "" for r in first.append if r[AT["platform"]] == "flipkart"))
    check("and his real Amazon rows do have money",
          first is not None and any(
              r[AT["gmv"]] for r in first.append if r[AT["platform"]] == "amazon"))
    again = answered(lambda: tool.plan(as_sheet(first.append), readings))
    check("HIS REAL FILES AGAIN CHANGE NOTHING",
          again is not None and not again.changes_anything)
    check("and nothing in the ledger reads as unreadable",
          again is not None and again.unreadable == ())

if not_run:
    print()
    print("      1 group NOT RUN -- his real files are not on this machine. Not a pass.")

print()
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

WITH_HIS_FILES = 74
EXPECTED = WITH_HIS_FILES - (9 if not_run else 0)
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print(f"all {ran} checks passed"
      + (" (1 group not run -- his real files are elsewhere)" if not_run else ""))
