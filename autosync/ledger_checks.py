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
import ledger_sheet  # noqa: E402
import orders  # noqa: E402
import reading  # noqa: E402
import sales  # noqa: E402
import sheet  # noqa: E402
import table  # noqa: E402

ran = 0
failures = []
not_run = []
THREW = []

HIS_FILES = Path(os.environ.get("RAW_DATA") or r"H:\My Drive\Rumee Raw Data")

# **WHAT AN ORDERS REPORT SAYS TODAY, STATUS INCLUDED (job 37).** Used only by the checks that drive the status word.
ORDERS_KNOWS_WITH_STATUS = ("platform", "orderId", "on", "sku", "qty", "gmv", "status")

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
# ------------------------------------------- job 37: A CANCELLED ORDER ALREADY IN THE LEDGER IS CORRECTED, AND NOTHING ELSE ON IT CHANGES

HE_SAW_A_SALE = sales.the_row_for(a_sale("O1", qty=0, notes="the seller wrote this", cogs=40))
corrected = answered(lambda: tool.plan(
    as_sheet([HE_SAW_A_SALE]),
    [a_reading("meesho orders", "2026-09-08", [a_sale("O1", qty=0, status="CANCELLED")],
               knows=ORDERS_KNOWS_WITH_STATUS)]))
check("a row that looked like a sale reads CANCELLED once the file is read with the status word",
      corrected is not None and len(corrected.update) == 1
      and corrected.update[0][1][AT["status"]] == "CANCELLED")
check("and the seller's own notes and the cost already on that row are exactly as they were",
      corrected is not None and corrected.update[0][1][AT["notes"]] == "the seller wrote this"
      and corrected.update[0][1][AT["cogs"]] == "40")
again = answered(lambda: tool.plan(
    as_sheet([corrected.update[0][1]]),
    [a_reading("meesho orders", "2026-09-08", [a_sale("O1", qty=0, status="CANCELLED")],
               knows=ORDERS_KNOWS_WITH_STATUS)])) if corrected is not None else None
check("and a second reading of the same file changes nothing, so the re-read is safe to run twice",
      again is not None and again.update == () and again.append == ())
check("an orders report that does NOT know the status column cannot touch it (rule 1 still holds)",
      answered(lambda: tool.plan(as_sheet([HE_SAW_A_SALE]),
                                 [a_reading("meesho orders", "2026-09-08", [a_sale("O1", qty=0, status="CANCELLED")])])).update == ())

check("a reading claiming a column the ledger does not have is refused",
      refused_by(lambda: a_reading("orders", "2026-08-01", [], knows=("nonsense",))))

# ------------------------- A MARKER DECLARED AND NOT CARRIED (D157)

# **A REPORT MAY SAY IT WRITES `ordersOn` AND THEN WRITE NOTHING INTO IT, and
# that is the exact shape of the fault D157 already cost two days to.** The
# columns landed in the ERP, every refusal built on their NAMES lifted itself
# the same day, and no code anywhere put a date in one. A declaration nothing
# fills is worth less than no declaration at all: it reads, to everything
# downstream and to any reviewer, as the marker being handled.
#
# **REFUSED WHERE THE READING IS BUILT, so the file is never marked as read** --
# `read_what_is_new` catches this, names the file and leaves it for tomorrow,
# which is what happens to every file it cannot read.
_MARKED = ("platform", "orderId", "qty", "ordersOn")
check("A READING THAT SAYS IT WRITES A DATE MARKER AND CARRIES NO DATE IS REFUSED",
      refused_by(lambda: a_reading("orders", "2026-08-01",
                                   [a_sale("SO-1", qty=1)], knows=_MARKED)))
check("and the refusal names the marker and the sale, so it can be gone and looked at",
      (lambda e: e is not None and "ordersOn" in str(e) and "SO-1" in str(e))(
          _catch(lambda: a_reading("orders", "2026-08-01",
                                   [a_sale("SO-1", qty=1)], knows=_MARKED))))
check("and one carrying the date is accepted",
      a_reading("orders", "2026-08-01",
                [a_sale("SO-1", qty=1, orders_on="2026-08-01")],
                knows=_MARKED) is not None)
# **ONE SALE WITHOUT IT IS ENOUGH.** A file of sixty rows where one carries no
# marker is a row in the sheet nothing can later tell was written by an older
# file, and it is invisible among the fifty-nine that are right.
check("one sale of many missing the marker still refuses the whole reading",
      refused_by(lambda: a_reading("orders", "2026-08-01", [
          a_sale("SO-1", qty=1, orders_on="2026-08-01"),
          a_sale("SO-2", qty=1),
      ], knows=_MARKED)))
# **AND A READING THAT NAMES NO MARKER IS NOT REFUSED HERE.** Whether a report
# is entitled to write to the sheet at all with no marker is a different
# question, asked once a night by `ledger_sheet.why_it_must_not_write_yet` over
# the whole list of readable reports -- not row by row here, where every
# narrower check of `plan` would trip on it.
check("a reading that names no date marker at all is still built",
      a_reading("orders", "2026-08-01", [a_sale("SO-1", qty=1)]) is not None)
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
check("THE RUN NEVER MOVES THE VERSION: `rev` is the ERP's alone (D472), and the run is guarded by its four date markers",
      after_pay is not None and after_pay.update[0][1][AT["rev"]] == "" and "rev" not in {c for _, those in after_pay.cells for c, _ in those})

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


# **A NEWER FILE SAYING THE SAME FIGURE IS STILL THAT DAY'S WORD (AP11, from the proving run).** So a second file of that same newer day that
# disagrees is a TIE, reported and left for him -- never a newer file quietly winning over a word already given that day.
def _a_file(which, gmv, on):
    return tool.Reading(report="meesho orders", on=on, knows=ORDERS_KNOWS, which=which, sales=(a_sale("O1", gmv=gmv),))


def _a_tie_after_the_same_word():
    memory = tool.WhatTheNightHasDecided()
    rows = HEADER + [list(r) for r in tool.plan([], [_a_file("file-one", 100, "2026-08-29")], memory).append]
    tool.plan(rows, [_a_file("file-two", 100, "2026-08-30")], memory)
    return tool.plan(rows, [_a_file("file-three", 200, "2026-08-30")], memory)


check("A NEWER FILE THAT SAYS THE SAME FIGURE STILL DECIDES ITS DAY: a second file of that day saying otherwise is a tie, not a quiet win",
      (lambda x: x is not None and x.update == () and len(x.disagreements) == 1 and x.disagreements[0].kept_from == "file-two"
       and x.disagreements[0].also_from == "file-three")(answered(_a_tie_after_the_same_word)))

# ---- D157'S FOUR DATE COLUMNS: NAMED, SO THAT THEIR ABSENCE IS A FACT

check("the four date-marker columns D157 asked for are named in one place",
      tool.WHICH_FILE_LAST_WROTE
      == ("ordersOn", "returnsOn", "paymentsOn", "claimsOn"))
# **ALL FOUR NOW EXIST, AND THAT IS THE ANSWER THIS PAIR OF CHECKS USED TO
# CARRY IN THE OPPOSITE DIRECTION.** Until 2026-09-06 the first of them said
# "NONE OF THE FOUR EXISTS YET" -- today's answer written down as a check, which
# is right and is also why it had to be rewritten the day the answer changed
# rather than deleted for going red. The ERP landed its half, `sales.COLUMNS` is
# pinned to the ERP's committed list, and this went empty with nothing here
# touched to make it.
check("ALL FOUR NOW EXIST, so nothing is missing and nothing is refused",
      tool.what_the_sheet_cannot_yet_say() == ())
check("and it is asking the real column list, not agreeing with itself",
      all(one in sales.COLUMNS for one in tool.WHICH_FILE_LAST_WROTE))
# **THREE OF FOUR IS STILL NOT GOOD ENOUGH, AND THE MISSING ONE IS STILL NAMED.**
# The guard has to keep working: a sale written with one marker missing is a row
# nothing can later tell was written by an older file. Driven by taking each of
# the four away in turn rather than by waiting for one to be absent.
check("take any ONE of the four away and it is missed, by name",
      all(tool.what_the_sheet_cannot_yet_say(
          tuple(c for c in sales.COLUMNS if c != one)) == (one,)
          for one in tool.WHICH_FILE_LAST_WROTE))
check("and take all four away and all four are named, in the ERP's order",
      tool.what_the_sheet_cannot_yet_say(
          tuple(c for c in sales.COLUMNS if c not in tool.WHICH_FILE_LAST_WROTE))
      == tool.WHICH_FILE_LAST_WROTE)

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
# ------------------- AN OLDER FILE DOES NOT UNDO A NEWER ONE, ACROSS RUNS (D157)

# **THE WHOLE OF D157'S SECOND HALF, and until 2026-09-08 there was no memory in
# the sheet to enforce it with.** His own case: the 4th's file fails, the 5th's
# lands and corrects a quantity from one to nine, and the 4th turns up a night
# later still saying one. `plan` is handed one file at a time, so the sort that
# fixes this within a run has nothing to sort -- the sheet's own marker is the
# only thing that can tell the run which day's file wrote what is there.
_MARKED = ("platform", "orderId", "qty", "ordersOn")


def _a_sheet_written_by(day, how_many="9"):
    """A sheet holding one sale, last written by a file of that day."""
    row = {one: "" for one in sales.COLUMNS}
    row["id"] = "meesho::O1::A"
    row["qty"] = how_many
    row["ordersOn"] = day
    return as_sheet([[row[one] for one in sales.COLUMNS]])


def _the_older_file_says(day, how_many="1"):
    return tool.Reading(
        report="me_orders", on=day, knows=_MARKED, which="the-late-file",
        sales=(a_sale("O1", qty=how_many, orders_on=day),))


_late = answered(lambda: tool.plan(_a_sheet_written_by("2026-09-05"),
                                   [_the_older_file_says("2026-09-04")]))
check("A FILE OLDER THAN THE ROW DOES NOT OVERWRITE IT -- D157, HIS OWN CASE",
      _late is not None and _late.update == () and _late.append == ())
check("AND IT IS SAID OUT LOUD, never quietly dropped",
      _late is not None and len(_late.left_alone) == 1)
check("and what it says names the sale, both days and the file",
      _late is not None and len(_late.left_alone) == 1
      and "meesho::O1::A" in str(_late.left_alone[0])
      and "2026-09-04" in str(_late.left_alone[0])
      and "2026-09-05" in str(_late.left_alone[0])
      and "the-late-file" in str(_late.left_alone[0]))
check("and the night's one line counts it, rather than reporting a quiet nought",
      _late is not None and "1 left alone as older than the row" in _late.says())
# **A NEWER FILE STILL WINS, or this is a wall rather than a rule.**
_newer = answered(lambda: tool.plan(_a_sheet_written_by("2026-09-04", "1"),
                                    [_the_older_file_says("2026-09-05", "9")]))
check("and a file NEWER than the row still writes, so this is a rule not a wall",
      _newer is not None and len(_newer.update) == 1 and _newer.left_alone == ())
# **AND THE OLDER FILE STILL ADDS WHAT ONLY IT HAS.** D157 in his own words: the
# 4th is read; where the 5th has written something newer the 4th leaves it;
# **where nothing is there the 4th fills it in.**
_only_the_old_one_has_it = tool.Reading(
    report="me_orders", on="2026-09-04", knows=_MARKED, which="the-late-file",
    sales=(a_sale("O1", qty="1", orders_on="2026-09-04"),
           a_sale("O2", qty="7", orders_on="2026-09-04")))
_both = answered(lambda: tool.plan(_a_sheet_written_by("2026-09-05"),
                                   [_only_the_old_one_has_it]))
check("AND THE OLDER FILE STILL ADDS THE SALE ONLY IT HAS -- it is not thrown away",
      _both is not None and len(_both.append) == 1 and _both.update == ()
      and len(_both.left_alone) == 1)
# **AN EQUAL DATE IS NOT OLD, AND THAT IS DELIBERATE RATHER THAN AN OVERSIGHT.**
# Two files of ONE day disagreeing is D150 rule 3, and rule 3 is decided over the
# RUN'S OWN MEMORY of which FILE said what -- the sheet records only the day, so
# answering a tie from the DATE alone would be inventing an AGE the sheet cannot
# state. **Found by breaking it: turning `<` into `<=` here left every check in
# this file green while three in `reading_checks.py` and six in
# `nightly_checks.py` went red.** A rule this file owns must be checked in this
# file, or a proving pass reports it as caught by something that only noticed the
# knock-on.
#
# **AND UNTIL A32 THE SENTENCE ABOVE WAS ONLY HALF SAID, AND THE MISSING HALF WAS
# MONEY.** "A tie is rule 3's" was true, and rule 3 never got the tie: it is
# decided over `WhatTheNightHasDecided`, **which starts empty every night**. So
# this same pair -- a sheet holding qty 9 written by a file of the 5th, a
# DIFFERENT file also of the 5th arriving on a later night -- met no tie at all
# and simply overwrote. Driven by an independent reviewer: `left_alone` 0,
# `disagreements` 0, quantity 9 became quantity 1, and nothing anywhere said so.
# **This check ASSERTED that overwrite** (`len(update) == 1`), which is how it
# stayed green through the fault. It now asserts what D150 rule 3 actually says:
# keep what is there, change nothing, and SAY SO. `ledger._what_the_sheet_
# remembers` is what supplies the missing side.
_same_day = answered(lambda: tool.plan(_a_sheet_written_by("2026-09-04", "1"),
                                       [_the_older_file_says("2026-09-04", "9")]))
check("A FILE OF THE SAME DAY IS NOT 'OLDER' -- a tie is rule 3's, not this rule's",
      _same_day is not None and _same_day.left_alone == ())
_QTY = sales.COLUMNS.index("qty")
check("AND ACROSS TWO NIGHTS THAT TIE IS KEPT AND REPORTED, not silently overwritten",
      _same_day is not None and len(_same_day.disagreements) == 1
      and all(row[_QTY] == "1" for _, row in _same_day.update))
check("and what it says names the sale, the column, both figures and both sides",
      _same_day is not None and len(_same_day.disagreements) == 1
      and "meesho::O1::A" in str(_same_day.disagreements[0])
      and "'1'" in str(_same_day.disagreements[0])
      and "'9'" in str(_same_day.disagreements[0])
      and tool.THE_SHEET_REMEMBERS in str(_same_day.disagreements[0])
      and "the-late-file" in str(_same_day.disagreements[0]))
# **AND A SALE THE SHEET HAS NEVER SEEN IS STILL APPENDED ON A TIE.** Rule 3 keeps
# what is THERE; where nothing is there it keeps nothing, and the file's own sale
# is the only statement about it.
_tie_but_new = answered(lambda: tool.plan(
    _a_sheet_written_by("2026-09-04", "1"),
    [tool.Reading(report="me_orders", on="2026-09-04", knows=_MARKED,
                  which="the-late-file",
                  sales=(a_sale("O2", qty="7", orders_on="2026-09-04"),))]))
check("a sale only the tying file has is still added, so a tie is not a wall",
      _tie_but_new is not None and len(_tie_but_new.append) == 1
      and _tie_but_new.disagreements == ())
# **AND A NIGHT'S OWN SECOND FILE STILL MEETS RULE 3 THE WAY IT ALWAYS DID, AND
# THE RUN'S OWN MEMORY IS ASKED FIRST.** The sheet remembers only the DAY; the run
# remembers the FILE, which is what a person needs to go and look at. So where
# both could answer, the run's answer is the one said out loud.
_night = tool.WhatTheNightHasDecided()
_first = answered(lambda: tool.plan(as_sheet([]),
                                    [_the_older_file_says("2026-09-04", "9")], _night))
_second = answered(lambda: tool.plan(
    as_sheet([list(_first.append[0])]),
    [tool.Reading(report="me_orders", on="2026-09-04", knows=_MARKED,
                  which="a-different-file",
                  sales=(a_sale("O1", qty="3", orders_on="2026-09-04"),))],
    _night))
check("two files of one night still tie on the run's own memory, naming both files",
      _second is not None and _second.update == ()
      and len(_second.disagreements) == 1
      and "the-late-file" in str(_second.disagreements[0])
      and "a-different-file" in str(_second.disagreements[0])
      and tool.THE_SHEET_REMEMBERS not in str(_second.disagreements[0]))

# **A ROW WITH NO MARKER IS NOT OLD.** Every row written before 2026-09-08 has a
# blank one, and refusing to touch those would freeze the whole ledger.
_blank = answered(lambda: tool.plan(_a_sheet_written_by(""),
                                    [_the_older_file_says("2026-09-04")]))
check("a row whose marker is blank is not treated as newer -- nothing is frozen",
      _blank is not None and len(_blank.update) == 1 and _blank.left_alone == ())
# **AND A MARKER SOMEBODY HAS TYPED OVER IS TREATED AS NEWER.** A sheet is a
# thing a person can open and edit. Compared as text, "yesterday" sorts after
# every real date and "1/9/26" sorts before every one -- so half the wrong
# answers are the silent overwrite this rule exists to stop.
for _typed in ("yesterday", "1/9/26", "05-09-2026"):
    _bad = answered(lambda d=_typed: tool.plan(_a_sheet_written_by(d),
                                               [_the_older_file_says("2026-09-04")]))
    check(f"a marker somebody typed over ({_typed!r}) is left alone, not written past",
          _bad is not None and _bad.update == () and len(_bad.left_alone) == 1)
# **AND A REPORT IS COMPARED AGAINST ITS OWN KIND OF MARKER AND NO OTHER (D157).**
# A payments file says nothing about when a delivery date was last stated, so an
# orders file dated later must not hold it back -- that is rule 1 from the other
# side.
_payments = tool.Reading(
    report="me_payments", on="2026-09-04", knows=("settlement",),
    sales=(a_sale("O1", settlement="12.5"),))
_pay = answered(lambda: tool.plan(_a_sheet_written_by("2026-09-05"), [_payments]))
check("A REPORT IS HELD TO ITS OWN MARKER ONLY -- a payments file is not stopped "
      "by an orders file dated later",
      _pay is not None and len(_pay.update) == 1 and _pay.left_alone == ())

# ------------------------------- A87 (AU2): "NOT UNDERSTOOD YET" IS CLEARED ONCE THE WORD IS KNOWN, AND NO OTHER WORD IS WIPED BY A BLANK

_WITH_WORD = ORDERS_KNOWS_WITH_STATUS + ("whatHappened",)
_stale = sales.the_row_for(a_sale("O9", what_happened=orders.NOT_UNDERSTOOD_YET))
_cleared = answered(lambda: tool.plan(
    as_sheet([_stale]), [a_reading("amazon orders", "2026-10-20", [a_sale("O9")], knows=_WITH_WORD)]))
check("AN OLD 'NOT UNDERSTOOD YET' IS CLEARED BY A READING WHERE THE WORD IS NOW KNOWN (an order still on its way is blank)",
      _cleared is not None and len(_cleared.update) == 1 and _cleared.update[0][1][AT["whatHappened"]] == "")
_delivered = sales.the_row_for(a_sale("O9", what_happened=orders.DELIVERED))
_kept = answered(lambda: tool.plan(
    as_sheet([_delivered]), [a_reading("amazon orders", "2026-10-20", [a_sale("O9")], knows=_WITH_WORD)]))
check("but a blank still never wipes a real outcome such as Delivered",
      _kept is not None and _kept.update == ())
_no_qty = answered(lambda: tool.plan(as_sheet([sales.the_row_for(a_sale("O8", qty=1, gmv="100"))]),
                                     [a_reading("meesho orders", "2026-10-20", [a_sale("O8")])]))
check("a blank price beside a quantity that says nothing (not a nought) leaves the old price standing (R20 proving)",
      _no_qty is not None and all(one[1][AT["gmv"]] == "100" for one in _no_qty.update))
_two = answered(lambda: tool.plan(as_sheet([sales.the_row_for(a_sale("O5", on="2026-09-11", qty=1, gmv="100"))]),
                                  [a_reading("meesho orders", "2026-10-20", [a_sale("O5", on="2026-09-10", qty=2, gmv="150")])]))
check("the cells of a changed row are named in the SHEET'S column order (R20 proving)",
      _two is not None and len(_two.cells) == 1
      and [c for c, _ in _two.cells[0][1]] == [c for c in sales.COLUMNS if c in {c for c, _ in _two.cells[0][1]}]
      and len(_two.cells[0][1]) >= 2)
for _source, _knows, _day in (("payments", ("settlement", "paymentsOn", "whatHappened"), {"payments_on": "2026-10-20"}),
                              ("returns", ("platform", "orderId", "sku", "whatHappened", "returnsOn"), {"returns_on": "2026-10-20"})):
    _left = answered(lambda k=_knows, s=_source, d=_day: tool.plan(
        as_sheet([_stale]), [a_reading("flipkart " + s, "2026-10-20", [a_sale("O9", **d)], knows=k)]))
    check(f"a {_source} file, which carries no status word, leaves 'NOT UNDERSTOOD YET' standing (R20 review)",
          _left is not None and all(one[1][AT["whatHappened"]] == orders.NOT_UNDERSTOOD_YET for one in _left.update))

_first = sales.the_row_for(a_sale("O7", on="2026-09-11", status="DELIVERED"))
_relisted = answered(lambda: tool.plan(
    as_sheet([_first]), [a_reading("meesho orders", "2026-09-23", [a_sale("O7", on="2026-09-23", status="READY_TO_SHIP")],
                                   knows=ORDERS_KNOWS_WITH_STATUS)]))
check("A MEESHO SUB-ORDER LISTED AGAIN UNDER A LATER DATE KEEPS ITS FIRST DATE, and the status still moves on (D447)",
      _relisted is not None and len(_relisted.update) == 1 and _relisted.update[0][1][AT["on"]] == "2026-09-11"
      and _relisted.update[0][1][AT["status"]] == "READY_TO_SHIP")
_earlier = answered(lambda: tool.plan(
    as_sheet([sales.the_row_for(a_sale("O7", on="2026-09-23"))]),
    [a_reading("meesho orders", "2026-09-24", [a_sale("O7", on="2026-09-11")], knows=ORDERS_KNOWS)]))
check("but an EARLIER date still replaces a later one",
      _earlier is not None and _earlier.update[0][1][AT["on"]] == "2026-09-11")

_came = sales.the_row_for(a_sale("O6", what_happened=orders.CAME_BACK))
for _word, _source in ((orders.DELIVERED, "payments"), (orders.NOT_UNDERSTOOD_YET, "orders")):
    _back = answered(lambda w=_word: tool.plan(
        as_sheet([_came]), [a_reading("meesho " + _source, "2026-10-01", [a_sale("O6", what_happened=w)],
                                      knows=("platform", "orderId", "sku", "whatHappened"))]))
    check(f"A RETURNED ORDER STAYS RETURNED: a {_source} file saying {_word!r} does not take 'Came back' back, whichever file is newer",
          _back is not None and _back.update == ())
_delivered_then = answered(lambda: tool.plan(
    as_sheet([sales.the_row_for(a_sale("O6", what_happened=orders.DELIVERED))]),
    [a_reading("meesho returns", "2026-10-01", [a_sale("O6", what_happened=orders.CAME_BACK)],
               knows=("platform", "orderId", "sku", "whatHappened"))]))
check("but 'Came back' still replaces 'Delivered'",
      _delivered_then is not None and _delivered_then.update[0][1][AT["whatHappened"]] == "Came back")
_odd = answered(lambda: tool.plan(
    as_sheet([sales.the_row_for(a_sale("O7", on="11/09/2026"))]),
    [a_reading("meesho orders", "2026-09-23", [a_sale("O7", on="2026-09-23")], knows=ORDERS_KNOWS)]))
check("the first-date rule compares only real days: a cell that is not one is replaced, not compared as text",
      _odd is not None and _odd.update[0][1][AT["on"]] == "2026-09-23")

# ------------------------------- P15 piece 4 (D462): THE RUN WRITES ONLY THE CELLS IT CHANGED, AND NEVER THE ERP'S
_settled = sales.the_row_for(a_sale("O5", qty=1, gmv=100, took="stock-lot-7"))
_payment = tool.Reading(report="me_payments", on="2026-10-01", knows=("settlement", "charge_commission", "paymentsOn"),
                          sales=(a_sale("O5", settlement="80", charges={"commission": "20"}, payments_on="2026-10-01"),), only_existing=True)
_cells = answered(lambda: tool.plan(as_sheet([_settled]), [_payment]))
_named = {c for _, those in (_cells.cells if _cells else ()) for c, _ in those}
check("A PAYMENTS FILE THAT STATES A SETTLEMENT NAMES EXACTLY ITS SETTLEMENT, ITS CHARGE AND ITS DATE MARKER -- nothing else",
      _named == {"settlement", "charge_commission", "paymentsOn"})
check("and the row it will look like keeps the ERP's cell", _cells is not None and _cells.update[0][1][AT["took"]] == "stock-lot-7")
check("A READING THAT NAMES A COLUMN THE ERP OWNS IS REFUSED, not written",
      refused_by(lambda: tool.plan(as_sheet([_settled]), [a_reading("meesho orders", "2026-10-01", [a_sale("O5", cogs=5)],
                                                                        knows=("platform", "orderId", "sku", "cogs"))])))
check("the columns the ERP owns are the sheet's 'comes back from Kartaan' set and the version (D472)",
      set(sales.ERP_OWNED_COLUMNS) == {c for c, (origin, _) in ledger_sheet.WHERE_A_COLUMN_COMES_BACK_FROM.items() if origin == ledger_sheet.FROM_KARTAAN} | {"rev"})
check("a reading naming the version is refused too",
      refused_by(lambda: tool.plan(as_sheet([_settled]), [a_reading("meesho orders", "2026-10-01", [a_sale("O5")],
                                                                        knows=("platform", "orderId", "sku", "rev"))])))

_priced = sales.the_row_for(a_sale("O8", qty=0, gmv=338.83))
_unpriced = answered(lambda: tool.plan(
    as_sheet([_priced]), [a_reading("amazon orders", "2026-10-20", [a_sale("O8", qty=0)], knows=ORDERS_KNOWS)]))
check("A PRICE BESIDE A QUANTITY OF NOUGHT IS TAKEN BACK BY A READING THAT SAYS QUANTITY NOUGHT AND NO PRICE",
      _unpriced is not None and len(_unpriced.update) == 1 and _unpriced.update[0][1][AT["gmv"]] == "")
_priced_sale = sales.the_row_for(a_sale("O8", qty=1, gmv=338.83))
_not_wiped = answered(lambda: tool.plan(
    as_sheet([_priced_sale]), [a_reading("amazon orders", "2026-10-20", [a_sale("O8", qty=1)], knows=ORDERS_KNOWS)]))
check("but a sale with a quantity above nought never loses its price to a blank",
      _not_wiped is not None and _not_wiped.update == ())

# **AN ORDER DELIVERED AND RETURNED ON THE SAME DAY KEEPS "DELIVERED" WHICHEVER FILE IS READ FIRST (A89, AU3 item 4).** Amazon's returns file says
# nothing about what became of an order until the platform has finished the return; its blank must not count as that day's word and shut out the
# orders file of the same day. **THE PROOF IS THE MIDDLE CHECK** (returns file between the two orders files); the other two guard the orders that already
# worked. Real files: 405-8281274-2953914 (delivered 16 Oct, return requested 16 Oct) read blank in the sheet after run #25.
_RETURNS_KNOW = reading.WHAT_RETURNS_KNOW
_ORDERS_KNOW = reading.WHAT_ORDERS_KNOWS


def _amazon_night(files):
    values, memory = HEADER, tool.WhatTheNightHasDecided()
    for one in files:
        made = tool.plan(values, [one], memory)
        values = [list(r) for r in values]
        values += [list(r) for r in made.append]
        for at, row in made.update:
            values[at - 1] = list(row)
    return dict(zip(sales.COLUMNS, values[-1]))


def _amazon(order_id="A1", **rest):
    return sales.Sale(platform="amazon", order_id=order_id, sku="S", **rest)


_picked_up = tool.Reading("az_orders", "2026-10-12", _ORDERS_KNOW, (_amazon(on="2026-10-10", qty=1, gmv=349, status="Shipped - Picked Up",
                          orders_on="2026-10-12"),), "o12")
_delivered = tool.Reading("az_orders", "2026-10-16", _ORDERS_KNOW, (_amazon(on="2026-10-10", qty=1, gmv=349, status="Shipped - Delivered to Buyer",
                          what_happened="Delivered", orders_on="2026-10-16"),), "o16")
_requested = tool.Reading("az_returns", "2026-10-16", _RETURNS_KNOW, (_amazon(returns_on="2026-10-16"),), "r16")
for _name, _files in (("orders file first", [_picked_up, _delivered, _requested]),
                      ("returns file between the two orders files", [_picked_up, _requested, _delivered]),
                      ("returns file first", [_requested, _picked_up, _delivered])):
    _row = answered(lambda f=_files: _amazon_night(f))
    check(f"a delivered order whose return was only requested the same day reads Delivered -- {_name}",
          _row is not None and _row["whatHappened"] == "Delivered" and _row["returnsOn"] == "2026-10-16")

# ---------------------------------- PR1 (A10): A FLIPKART ORDER'S MONEY IS THE SUM OF ITS DISTINCT PAYOUTS, NEVER THE LAST PAYOUT ALONE
# The real case (Rumee's ledger, 30 Oct 2026): a sale paid 196.85 in one payout, then a customer return taken back in a later payout (refund and reverse
# shipping, -403.35). The row ended at -403.35; it is -206.50.
import payments  # noqa: E402
from decimal import Decimal  # noqa: E402


def _payout(payout, on, figure):
    return tool.Reading("fk_payments", on, payments.WHAT_PAYMENTS_KNOW,
                        (sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement=figure, notes="fkpay:" + payout, payments_on=on),),
                        "file-" + payout, only_existing=True)


def _night(files, start=None):
    values, memory = (start or HEADER), tool.WhatTheNightHasDecided()
    said = []
    for one in files:
        made = tool.plan(values, [one], memory)
        values = [list(r) for r in values] + [list(r) for r in made.append]
        for at, row in made.update:
            values[at - 1] = list(row)
        said += [str(r) for r in made.restated] + [str(d) for d in made.disagreements] + [str(k) for k in made.kept] + ["QUIET:" + str(k) for k in made.kept_quietly]
    return dict(zip(sales.COLUMNS, values[-1])), said


_sale_paid, _return_paid = _payout("UTR-0001", "2026-10-20", "196.85"), _payout("UTR-0002", "2026-10-29", "-403.35")
_row, _said = _night([_sale_paid, _return_paid])
check("A10: a sale paid in one payout and taken back in a later one is the SUM of the two (196.85 + -403.35 = -206.50)",
      Decimal(_row["settlement"]) == Decimal("-206.50") and _row["notes"] == "fkpay:UTR-0001 fkpay:UTR-0002")
check("A10: and the change is said (was -> now), not made quietly", any("196.85" in line and "-206.5" in line for line in _said))
_row, _ = _night([_sale_paid, _return_paid, _return_paid, _sale_paid])
check("A10: the same payouts read again (overlapping files) change nothing", Decimal(_row["settlement"]) == Decimal("-206.50"))
_row, _ = _night([_return_paid, _sale_paid])
check("A10: a payout that arrives AFTER a newer one is still added, not held back as older than the row",
      Decimal(_row["settlement"]) == Decimal("-206.50"))
_wrong = sales.the_row_for(sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="-403.35", payments_on="2026-10-29"))
_row, _ = _night([_sale_paid, _return_paid], start=HEADER + [list(_wrong)])
check("A10 REPAIR: a row written before this change at -403.35 is re-worked from the payouts in order and comes out at -206.50",
      Decimal(_row["settlement"]) == Decimal("-206.50"))
_row, _ = _night([_sale_paid, _sale_paid], start=HEADER + [list(sales.the_row_for(sales.Sale(platform="flipkart", order_id="OD1", sku="S",
                                                                                                  settlement="196.85", payments_on="2026-10-20")))])
check("A10 REPAIR: a row that was right (one payout, no key) is not doubled by being read again", Decimal(_row["settlement"]) == Decimal("196.85"))
_mixed = tool.Reading("fk_payments", "2026-10-29", payments.WHAT_PAYMENTS_KNOW,
                      (sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="5", notes="fkpay:UTR-0001 fkpay:UTR-0003", payments_on="2026-10-29"),),
                      "file-mixed", only_existing=True)
_row, _said = _night([_sale_paid, _mixed])
check("A10: a file with one payout the row has and one it has not is SAID and the figure is left", Decimal(_row["settlement"]) == Decimal("196.85") and any("settlement" in line for line in _said))

# The earlier payout's file is gone from the folder: the row (written before payouts were keyed) holds -403.35, and the only payout file read says -403.35.
_row, _said = _night([_return_paid], start=HEADER + [list(_wrong)])
check("A10: an old figure that the only payout file left agrees with stays, and the order is NAMED as kept (never silent)",
      Decimal(_row["settlement"]) == Decimal("-403.35") and any("kept the old figure -403.35 for payout UTR-0002" in line for line in _said))
_row, _said = _night([_sale_paid, _return_paid])
check("A10: and an order whose payouts all arrived in order names nothing as kept", not any("kept the old figure" in line for line in _said))

# ---------------------------------- PR1c: the fresh review's findings 1, 3, 4, 5, 8 (each starts from the mixed shape the reviewer said was never tried)
def _unkeyed(on, figure, file="file-unkeyed"):
    return tool.Reading("fk_payments", on, payments.WHAT_PAYMENTS_KNOW,
                        (sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement=figure, payments_on=on),), file, only_existing=True)


_row, _said = _night([_sale_paid, _return_paid, _unkeyed("2026-10-30", "10")])
check("PR1c 1: a line with no payout key over a row summed from keyed payouts changes no money, and is SAID",
      Decimal(_row["settlement"]) == Decimal("-206.50") and any("settlement" in line and "'10'" in line for line in _said))
_row, _said = _night([_sale_paid, _unkeyed("2026-10-30", "196.85")])
check("PR1c 1: an unkeyed line that agrees with the keyed row changes nothing and says nothing",
      Decimal(_row["settlement"]) == Decimal("196.85") and not _said)
_row, _ = _night([_sale_paid, _unkeyed("2026-10-30", "10"), _return_paid])
check("PR1c 1: and the real payout read after the unkeyed line is still added (the sum was never destroyed)",
      Decimal(_row["settlement"]) == Decimal("-206.50"))
_typed = list(sales.the_row_for(sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="196.85", payments_on="2026-10-20", notes="pay:later")))
_row, _ = _night([_sale_paid], start=HEADER + [_typed])
check("PR1c 3: a word the seller typed (`pay:later`) is not a payout key -- 196.85 read with payout UTR-0001 (196.85) stays 196.85, not 393.70",
      Decimal(_row["settlement"]) == Decimal("196.85") and "pay:later" in _row["notes"] and "fkpay:UTR-0001" in _row["notes"])
_row, _said = _night([_sale_paid, _payout("UTR-0001", "2026-10-30", "150", )])
check("PR1c 4: the same payout read again with a different figure is SAID, and the figure is kept",
      Decimal(_row["settlement"]) == Decimal("196.85") and any("'150'" in line for line in _said))
_row, _ = _night([_return_paid, _sale_paid])
check("PR1c 8: the day of the last payment never goes backwards when an older payout is added", _row["paymentsOn"] == "2026-10-29")
_legacy_sale = list(sales.the_row_for(sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="196.85", payments_on="2026-10-20")))
_row, _said = _night([_sale_paid], start=HEADER + [_legacy_sale])
check("PR1c 5: a legacy single-payout row re-read on the repair night is COUNTED, not named",
      Decimal(_row["settlement"]) == Decimal("196.85") and not any("kept the old figure" in line and not line.startswith("QUIET") for line in _said)
      and sum(line.startswith("QUIET:") for line in _said) == 1)
_made = tool.plan(HEADER + [_legacy_sale], [_sale_paid, _return_paid], tool.WhatTheNightHasDecided())
check("PR1c 5: but a legacy row that ends the night (one call, both payouts) with a later payout is NAMED, not counted",
      len(_made.kept) == 1 and not _made.kept_quietly and "kept the old figure 196.85" in str(_made.kept[0]))

# **TWO PAYOUTS FOR ONE ORDER IN ONE FILE (PR1c finding 6; the real files have 325 such lines in 14 files).** The reader now gives each payout its own line.
def _two_in_one_file(on="2026-10-29"):
    return tool.Reading("fk_payments", on, payments.WHAT_PAYMENTS_KNOW,
                        (sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="196.85", notes="fkpay:UTR-0001", payments_on=on),
                         sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="-403.35", notes="fkpay:UTR-0002", payments_on=on)),
                        "file-two", only_existing=True)


_row, _ = _night([_two_in_one_file()])
check("PR1c 6: two payouts for one order in one file, on a new row, add up (196.85 + -403.35 = -206.50) with both keys",
      Decimal(_row["settlement"]) == Decimal("-206.50") and _row["notes"] == "fkpay:UTR-0001 fkpay:UTR-0002")
_row, _ = _night([_sale_paid, _two_in_one_file()])
check("PR1c 6: and a row that already has the first payout gets the second added, not a disagreement and not lost",
      Decimal(_row["settlement"]) == Decimal("-206.50"))
_row, _ = _night([_two_in_one_file(), _two_in_one_file(), _sale_paid, _return_paid])
check("PR1c 6: and reading the same file again, or each payout's own file, changes nothing", Decimal(_row["settlement"]) == Decimal("-206.50"))
_row, _ = _night([_two_in_one_file()], start=HEADER + [list(_wrong)])
check("PR1c 6: a legacy row written wrong at -403.35 is re-worked to -206.50 by the file holding both payouts", Decimal(_row["settlement"]) == Decimal("-206.50"))

# **PR1c REVIEW: a keyed and an unkeyed line for one order in one file are ONE order's money; a note shaped like an id is not a payout key.**
def _keyed_and_loose(on="2026-10-29"):
    return tool.Reading("fk_payments", on, payments.WHAT_PAYMENTS_KNOW,
                        (sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="200", notes="fkpay:UTR-0001", payments_on=on),
                         sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="-50", payments_on=on)),
                        "file-loose", only_existing=True)


_row, _said = _night([_keyed_and_loose()])
check("PR1c review 1: a keyed line (200) and an unkeyed line (-50) for one order in one file: the keyed payout is the row's money and the unkeyed one is SAID, not set first and lost",
      Decimal(_row["settlement"]) == Decimal("200") and any("'-50'" in line for line in _said))
_rebate_file = tool.Reading("fk_payments", "2026-10-30", payments.WHAT_PAYMENTS_KNOW,
                            (sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="5", notes="fkpay:UTR-0009", payments_on="2026-10-30"),),
                            "file-rebate", only_existing=True)
_row, _ = _night([_sale_paid, _return_paid, _rebate_file])
check("PR1c review: a rebate paid in its own payout is added to a row that already has two payouts (-206.50 + 5 = -201.50)", Decimal(_row["settlement"]) == Decimal("-201.50"))
_new_first = tool.Reading("fk_payments", "2026-10-30", payments.WHAT_PAYMENTS_KNOW,
                          (sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="-30", notes="fkpay:AAA-00000", payments_on="2026-10-30"),
                           sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="205", notes="fkpay:UTR-0001", payments_on="2026-10-30")),
                          "file-new-first", only_existing=True)
_row, _said = _night([_sale_paid, _new_first])
check("PR1c review: a restated payout is said even when a NEW payout in the same file sorts before it",
      any("'205'" in line or "205" in line for line in _said if "settlement" in line))
_typed2 = list(sales.the_row_for(sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="196.85", payments_on="2026-10-20", notes="pay:15Nov2026")))
_row, _ = _night([_sale_paid], start=HEADER + [_typed2])
check("PR1c review 3: a seller note shaped like an id (`pay:15Nov2026`) is no payout key either",
      Decimal(_row["settlement"]) == Decimal("196.85") and "pay:15Nov2026" in _row["notes"])

# **PR1c PROVING: survivors the prover found in the new payout rules.**
_zero_row = list(sales.the_row_for(sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="0", payments_on="2026-10-20")))
_zero_file = tool.Reading("fk_payments", "2026-10-29", payments.WHAT_PAYMENTS_KNOW,
                          (sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="0", notes="fkpay:UTR-0001", payments_on="2026-10-29"),),
                          "file-zero", only_existing=True)
_made = tool.plan(HEADER + [_zero_row], [_zero_file], tool.WhatTheNightHasDecided())
check("PR1c proving: a kept figure of nought is NAMED (a sale of nothing is return-type), not counted away",
      len(_made.kept) == 1 and not _made.kept_quietly)
_made = tool.plan(HEADER + [_legacy_sale], [_sale_paid], tool.WhatTheNightHasDecided())
check("PR1c proving: and a positive kept figure with no later payout is counted, not named", not _made.kept and len(_made.kept_quietly) == 1)
_made = tool.plan(HEADER + [_legacy_sale], [_sale_paid], tool.WhatTheNightHasDecided())
check("PR1c proving: a payout added to a row has its key SENT as a changed cell (notes), not only in the whole row",
      any(("notes", "fkpay:UTR-0001") in cells for _, cells in tool.plan(HEADER, [_sale_paid], tool.WhatTheNightHasDecided()).cells)
      or any("notes" in dict(cells) for _, cells in _made.cells))
_with_fee = list(sales.the_row_for(sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="196.85", payments_on="2026-10-20",
                                              notes="fkpay:UTR-0001 fee:SET1:1")))
_row, _said = _night([_payout("UTR-0001", "2026-10-30", "150")], start=HEADER + [_with_fee])
check("PR1c proving: a row that also holds an added fee is not compared with a payout's figure (the row's figure includes the fee)",
      not any("'150'" in line for line in _said))
_two_keys = list(sales.the_row_for(sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="-206.5", payments_on="2026-10-29",
                                              notes="fkpay:UTR-0001 fkpay:UTR-0002")))
_row, _said = _night([_payout("UTR-0002", "2026-10-30", "-100")], start=HEADER + [_two_keys])
check("PR1c proving: a restated payout on a row holding TWO payouts cannot be compared and changes nothing (the stated limit)",
      Decimal(_row["settlement"]) == Decimal("-206.50") and not _said)
_made = tool.plan(HEADER, [_sale_paid, _unkeyed("2026-10-30", "10")], tool.WhatTheNightHasDecided())
check("PR1c proving: an unkeyed line over a keyed row says WHO said it: the sheet's own memory against the file",
      len(_made.disagreements) == 1 and _made.disagreements[0].kept_from == tool.THE_SHEET_REMEMBERS and _made.disagreements[0].also_from == "file-unkeyed")
check("PR1c proving: is_payout_key accepts a key this program writes, and refuses a bare prefix, a short id, an id with no digit and another prefix",
      payments.is_payout_key("fkpay:UTR-00000001") and not payments.is_payout_key("fkpay:") and not payments.is_payout_key("fkpay:short1")
      and not payments.is_payout_key("fkpay:ABCDEFGHIJ") and not payments.is_payout_key("pay:UTR-00000001"))
_groups = payments._PayoutGroups()
_groups.put(("OD1", "S"), Decimal(1), {}, "fkpay:AAAAAAA1")
_groups.put(("OD1", "S"), Decimal(2), {}, "fkpay:BBBBBBB2")
_groups.put_on_what_states(("OD9", "S"), Decimal(5), {})
_groups.put_on_what_states(("OD1", "S"), Decimal(5), {})
check("PR1c proving: a rebate with no payout of its own rides on the FIRST payout that states its order, and on nothing when none does",
      [(s_.order_id, s_.settlement) for s_ in _groups.sales("flipkart", "2026-10-29")] == [("OD1", "6"), ("OD1", "2")])

_kf = tool.KeptFigure(name="n", figure="1", payout="p", from_report="fk_payments", on="2026-10-29", from_file="f.xlsx")
check("PR1c proving: a kept figure is said with its report, day and file, and without a file it still closes properly",
      str(_kf) == "'n': kept the old figure 1 for payout p (fk_payments of 2026-10-29, file f.xlsx)"
      and str(tool.KeptFigure(name="n", figure="1", payout="p", from_report="fk_payments", on="2026-10-29")) == "'n': kept the old figure 1 for payout p (fk_payments of 2026-10-29)")
_unreadable_row = list(sales.the_row_for(sales.Sale(platform="flipkart", order_id="OD1", sku="S", settlement="n/a", payments_on="2026-10-20", notes="fkpay:UTR-0001")))
_row, _said = _night([_payout("UTR-0001", "2026-10-30", "150")], start=HEADER + [_unreadable_row])
check("PR1c proving: a restated payout is NOT compared with a figure on the row that cannot be read (nothing said, nothing guessed)", not any("'150'" in line for line in _said))
_made = tool.plan(HEADER, [_sale_paid, _mixed], tool.WhatTheNightHasDecided())
check("PR1c proving: a file with one payout the row has and one it has not says which file said what (the sheet's memory against this file)",
      len(_made.disagreements) == 1 and _made.disagreements[0].kept_from == tool.THE_SHEET_REMEMBERS and _made.disagreements[0].also_from == "file-mixed")

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

WITH_HIS_FILES = 115 + 2 + 2 + 3 + 1 + 7 + 2 + 8 + 4 + 2 + 2 + 8 + 3
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
