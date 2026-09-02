"""Checks for turning a platform's file into rows.

**EVERY FAULT CHECKED HERE IS ONE HIS REAL FILES ACTUALLY HAVE**, measured on
2026-09-02 against 46 real Amazon orders, 7 real Amazon returns, 15 real
settlement lines and a real Meesho orders file. Nothing here guards against
something imagined.

**THE REAL FILES ARE READ WHEN THEY ARE THERE, AND SAID TO BE MISSING WHEN THEY
ARE NOT.** They live in his Drive, which no checkout has, so these checks cannot
depend on them -- but a check that quietly stops checking is worse than no check,
because it is still counted (the same rule the doors into the other repositories
are built on). So the ones needing real files SAY they were not run, and the
count at the end knows the difference.

Run: python autosync/table_checks.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import table as tool  # noqa: E402

ran = 0
failures = []
not_run = []
THREW = []

# Where his real files are. **Not a secret and not a credential** -- a folder
# path. Nothing here opens anything else in it.
#
# **IT CAN BE POINTED SOMEWHERE ELSE, and that is not a convenience.** It is the
# only way to prove the not-run path actually works: point it at nothing and the
# real-file checks must SAY they did not run and the count must follow. A
# skipping path nobody has watched skip is a path nobody knows works.
#     RAW_DATA=/nowhere python autosync/table_checks.py
HIS_FILES = Path(os.environ.get("RAW_DATA") or r"H:\My Drive\Rumee Raw Data")


def answered(work):
    """What this answers, or nothing at all when it threw.

    A run that stops is not a check going red: one deliberate breakage would end
    the whole run and nothing would go red, so the measurement would read
    "noticed" while saying nothing about whether any check here is any good.
    """
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
    """True when that raises `CannotRead`, and nothing else.

    **THE KIND IS CHECKED, not just that it threw.** A check written as "it
    raised something" passes when the code has a typo in it, which is the loudest
    possible way to be green for the wrong reason.
    """
    try:
        work()
    except tool.CannotRead:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


TAB = "\t"
CR = "\r"
LF = "\n"


def _catch(work):
    try:
        work()
    except Exception as e:  # noqa: BLE001
        return e
    return None


# ------------------------------------------------------- the four real faults

# 1. AMAZON'S CARRIAGE-RETURN CARRIAGE-RETURN NEWLINE
AMAZON_SHAPED = (
    f"a{TAB}b{TAB}is-prime{CR}{CR}{LF}"
    f"1{TAB}2{TAB}false{CR}{CR}{LF}"
    f"3{TAB}4{TAB}true{CR}{CR}{LF}"
)

t = answered(lambda: tool.read(AMAZON_SHAPED))
check("Amazon's three-character line ending gives the right number of rows",
      t is not None and len(t.rows) == 2)
check("and the plain way of counting lines would have got it wrong",
      len(AMAZON_SHAPED.splitlines()) != 3)
check("the last column's name has no carriage return stuck to it",
      t is not None and t.columns[-1] == "is-prime")
check("and its value has none either, so a comparison actually fires",
      t is not None and t.rows[0]["is-prime"] == "false")
check("no empty row is invented by the extra carriage return",
      t is not None and all(any(c for c in r.cells) for r in t.rows))

# The order of the replacing is the whole point -- shortest first leaves a stray.
check("the line endings are replaced longest first",
      tool.LINE_ENDINGS[0] == "\r\r\n" and tool.LINE_ENDINGS.index("\r\n") == 1)
check("and doing it shortest first would have left a stray carriage return",
      f"a{CR}{CR}{LF}".replace("\r\n", "\n").replace("\r\r\n", "\n") != "a\n")

# 2. THE NAME OF A FILE DOES NOT SAY WHAT IS INSIDE IT
t = answered(lambda: tool.read(f"a{TAB}b{LF}1{TAB}2{LF}"))
check("a tab-separated file is read as tab-separated",
      t is not None and t.separator == tool.TAB and t.columns == ("a", "b"))
t = answered(lambda: tool.read(f"a,b{LF}1,2{LF}"))
check("a comma-separated one is read as comma-separated",
      t is not None and t.separator == tool.COMMA and t.columns == ("a", "b"))

# **THE HEADER DECIDES, NOT THE WHOLE FILE.** One product name full of commas
# must not outvote the tabs that actually separate the columns.
COMMA_HEAVY = (
    f"sku{TAB}name{LF}"
    f"A1{TAB}Pearl, Silver, Oxidised, Choker, Set{LF}"
    f"A2{TAB}Bangle, Gold, Two, Piece{LF}"
)
t = answered(lambda: tool.read(COMMA_HEAVY))
check("a product name full of commas does not outvote the real separator",
      t is not None and t.separator == tool.TAB and len(t.columns) == 2)
check("and that name comes back whole",
      t is not None and t.rows[0]["name"] == "Pearl, Silver, Oxidised, Choker, Set")
check("a file with neither separator is read as one column, not reshaped",
      (lambda r: r is not None and len(r.columns) == 1)(answered(lambda: tool.read("only\nrow\n"))))

# 3. QUOTING IS NOT THE SAME ON BOTH
# **THE QUOTE HAS TO START THE FIELD, and that is the whole point of this
# sample.** Written as `9" Bangle` -- quote in the middle -- reading the file as
# quoted makes no difference at all, because a quote that is not the first
# character never opens a quoted field. So the check passed whether the rule was
# there or not. Found by putting the fault back and watching nothing go red.
QUOTE_IN_A_TAB_FILE = (
    f'sku{TAB}name{TAB}qty{LF}'
    f'A1{TAB}"Pearl" Choker{TAB}3{LF}'
    f'A2{TAB}plain{TAB}5{LF}'
)
t = answered(lambda: tool.read(QUOTE_IN_A_TAB_FILE))
check("a quote starting a field in a tab file does not swallow the columns after it",
      t is not None and len(t.rows) == 2 and t.rows[0]["qty"] == "3")
check("and it does not swallow the NEXT ROW either",
      t is not None and len(t.rows) == 2 and t.rows[1]["sku"] == "A2")
check("the value keeps its quotes exactly as the platform wrote them",
      t is not None and t.rows[0]["name"] == '"Pearl" Choker')

MEESHO_SHAPED = 'sku,name,qty\n"A1","Pearl, Silver Choker","2"\n'
t = answered(lambda: tool.read(MEESHO_SHAPED))
check("a quoted comma file keeps a comma inside a value",
      t is not None and t.rows[0]["name"] == "Pearl, Silver Choker")
check("and does not turn one value into several columns",
      t is not None and len(t.columns) == 3 and len(t.rows) == 1)

# 4. A ROW THAT DOES NOT FIT IS NAMED, NOT DROPPED AND NOT FATAL
SHORT_ROW = f"a{TAB}b{TAB}c{LF}1{TAB}2{TAB}3{LF}4{TAB}5{LF}6{TAB}7{TAB}8{LF}"
t = answered(lambda: tool.read(SHORT_ROW))
check("a row of the wrong width does not lose the file", t is not None and len(t.rows) == 2)
check("the bad row is kept rather than dropped", t is not None and len(t.refused) == 1)
check("and it is named by the line number a person would see",
      t is not None and t.refused[0].line == 3)
check("what it said is kept too, so somebody can look at it",
      t is not None and t.refused[0].said == ("4", "5"))
check("the reason says both counts, not just that it was wrong",
      t is not None and "2 values" in t.refused[0].why and "3" in t.refused[0].why)
check("a row with too MANY values is refused the same way",
      (lambda r: r is not None and len(r.refused) == 1 and len(r.rows) == 1)(
          answered(lambda: tool.read(f"a{TAB}b{LF}1{TAB}2{LF}3{TAB}4{TAB}5{LF}"))))

# A blank line is not a refusal -- every file ends with one.
t = answered(lambda: tool.read(f"a{TAB}b{LF}1{TAB}2{LF}{LF}{LF}"))
check("a trailing blank line is not reported as a bad row",
      t is not None and len(t.rows) == 1 and t.refused == ())

# ------------------------------------------------- what it refuses to guess at

t = answered(lambda: tool.read(f"a{TAB}b{LF}1{TAB}2{LF}"))
check("asking for a column the file does not have is refused, not answered blank",
      t is not None and refused_by(lambda: t.rows[0]["nope"]))

# **THE DUPLICATE-NAME RULE MOVED, and his real data is why.** It used to refuse
# the whole FILE. His real Meesho payments file has two columns called
# `Fixed Fee (Incl. GST)`, at columns 18 and 26, beside 41 good ones -- so
# refusing the file made that whole stream permanently unreadable over one name.
# Nothing guesses, which was always the point; the refusal simply happens where
# it bites, when somebody asks for that name.
TWICE = f"sku{TAB}qty{TAB}sku{LF}1{TAB}2{TAB}3{LF}"
t = answered(lambda: tool.read(TWICE))
check("a name used twice does not lose the file", t is not None and len(t.rows) == 1)
check("the other columns still read", t is not None and t.rows[0]["qty"] == "2")
check("asking for the doubled name is refused, never picked between",
      t is not None and refused_by(lambda: t.rows[0]["sku"]))
check("and the refusal says where BOTH of them are",
      (lambda e: e is not None and "1" in str(e) and "3" in str(e) and "2 columns" in str(e))(
          _catch(lambda: t.rows[0]["sku"])))
check("what was doubled is kept, so it can be reported",
      t is not None and t.ambiguous == {"sku": (0, 2)})
check("and it is said out loud rather than staying quiet",
      t is not None and "cannot be read" in t.says())
check("has() says no to a doubled column, rather than promising a value",
      t is not None and not t.rows[0].has("sku") and t.rows[0].has("qty"))
check("a doubled column that the reading NEEDS stops the file",
      refused_by(lambda: tool.read(TWICE, expect=["sku"])))
check("but a doubled column nobody needs does not",
      (lambda r: r is not None and len(r.rows) == 1)(
          answered(lambda: tool.read(TWICE, expect=["qty"]))))
check("a header naming no columns at all is refused",
      refused_by(lambda: tool.read(f"{TAB}{TAB}{LF}1{TAB}2{TAB}3{LF}")))
check("an empty file is refused", refused_by(lambda: tool.read("")))
check("and so is one that is only whitespace", refused_by(lambda: tool.read("   \n\n")))
check("something that is neither bytes nor text is refused",
      refused_by(lambda: tool.read(12345)))

# The columns a caller cannot work without are checked ONCE, against the header.
check("a missing needed column stops the whole file rather than every row",
      refused_by(lambda: tool.read(f"a{TAB}b{LF}1{TAB}2{LF}", expect=["a", "settlement"])))
t = answered(lambda: tool.read(f"a{TAB}b{LF}1{TAB}2{LF}", expect=["a", "b"]))
check("and when they are all there it reads normally", t is not None and len(t.rows) == 1)


err = _catch(lambda: tool.read(f"a{TAB}b{LF}1{TAB}2{LF}", expect=["settlement"]))
check("the refusal names the column that is missing AND what was found instead",
      err is not None and "settlement" in str(err) and "'a'" in str(err))

err = _catch(lambda: tool.read(f"a{TAB}b{LF}1{TAB}2{LF}").rows[0]["nope"])
check("a missing column's refusal lists the columns that are there",
      err is not None and "'a'" in str(err) and "'b'" in str(err))

# The mark some tools put at the front of a file.
t = answered(lambda: tool.read("\ufeff" + f"sku{TAB}qty{LF}A1{TAB}2{LF}"))
check("a byte-order mark does not become part of the first column's name",
      t is not None and t.columns[0] == "sku")
check("so the first column can still be looked up by name",
      t is not None and t.rows[0]["sku"] == "A1")
t = answered(lambda: tool.read(("\ufeff" + f"sku{TAB}qty{LF}A1{TAB}2{LF}").encode("utf-8")))
check("and the same is true when it arrives as bytes",
      t is not None and t.columns[0] == "sku")
check("a byte that cannot be decoded does not lose the file",
      (lambda r: r is not None and len(r.rows) == 1)(
          answered(lambda: tool.read(f"sku{TAB}qty{LF}A1{TAB}2{LF}".encode() + b"\xff\n"))))

# ------------------------------------------------------- it hands back TEXT

t = answered(lambda: tool.read(f"qty{TAB}gmv{LF}0{TAB}0.0{LF}"))
check("a nought comes back as the text the platform wrote, not as a number",
      t is not None and t.rows[0]["qty"] == "0" and isinstance(t.rows[0]["qty"], str))
check("and an empty cell comes back empty rather than as nothing at all",
      (lambda r: r is not None and r.rows[0]["gmv"] == "")(
          answered(lambda: tool.read(f"qty{TAB}gmv{LF}1{TAB}{LF}"))))

# `get` exists for columns a platform may or may not send, and says so.
t = answered(lambda: tool.read(f"a{TAB}b{LF}1{TAB}2{LF}"))
check("get() answers for a column that is not there", t is not None and t.rows[0].get("nope") == "")
check("get() answers what was asked for when it is there", t is not None and t.rows[0].get("a") == "1")
check("has() says whether a column is there at all",
      t is not None and t.rows[0].has("a") and not t.rows[0].has("nope"))

# What it says out loud.
t = answered(lambda: tool.read(SHORT_ROW))
check("what it read is said in one line, refusals included",
      t is not None and "2 rows read" in t.says() and "1 refused" in t.says())
t = answered(lambda: tool.read(f"a{TAB}b{LF}1{TAB}2{LF}"))
check("and a clean read still says how many were refused, rather than staying quiet",
      t is not None and "0 refused" in t.says())
check("it says which separator it found", t is not None and "tab-separated" in t.says())

# ------------------------------------------- and now against HIS REAL FILES

REAL = {
    "amazon orders": (
        HIS_FILES / "amazon" / "amazon_az_orders_2026-09-02.csv",
        34, 46, tool.TAB, "is-prime", "amazon-order-id",
    ),
    "amazon returns": (
        HIS_FILES / "amazon" / "amazon_az_returns_2026-09-02.csv",
        34, 7, tool.TAB, "Order Item ID", "Order ID",
    ),
    "amazon settlements": (
        HIS_FILES / "amazon" / "amazon_az_settlements_2026-09-01.csv",
        24, 15, tool.TAB, "promotion-id", "settlement-id",
    ),
    "meesho orders": (
        HIS_FILES / "meesho" / "orders" / "meesho_orders_2026-08-30.csv",
        13, 12, tool.COMMA, "Packet Id", "Sub Order No",
    ),
}

for what, (path, columns, rows, separator, last, first) in REAL.items():
    if not path.is_file():
        not_run.append(f"{what} -- {path} is not on this machine")
        print(f"NOT RUN  his real {what}: {path} is not here")
        continue
    real = answered(lambda p=path: tool.read(p.read_bytes()))
    check(f"his real {what}: it reads at all", real is not None)
    check(f"his real {what}: {columns} columns", real is not None and len(real.columns) == columns)
    check(f"his real {what}: {rows} rows", real is not None and len(real.rows) == rows)
    check(f"his real {what}: nothing was refused", real is not None and real.refused == ())
    check(f"his real {what}: read as {'tab' if separator == tool.TAB else 'comma'}-separated",
          real is not None and real.separator == separator)
    check(f"his real {what}: the last column is {last!r} with nothing stuck to it",
          real is not None and real.columns[-1] == last)
    check(f"his real {what}: every row can be looked up by name",
          real is not None and all(r[first] is not None for r in real.rows))

if not_run:
    print()
    print(f"      {len(not_run)} check group(s) NOT RUN -- his real files are not on this machine:")
    for one in not_run:
        print(f"        {one}")
    print("      They are not passes. Run this where the Drive folder is.")

print()
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

# **THE COUNT KNOWS THE DIFFERENCE between here and a machine without his Drive.**
# A single expected number would go red on one of them and be edited until it went
# green on both, which is how a count stops meaning anything.
WITH_HIS_FILES = 83
WITHOUT = WITH_HIS_FILES - 7 * len(REAL)
EXPECTED = WITHOUT if len(not_run) == len(REAL) else WITH_HIS_FILES
if not_run and len(not_run) != len(REAL):
    EXPECTED = WITH_HIS_FILES - 7 * len(not_run)
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print(f"all {ran} checks passed"
      + (f" ({len(not_run)} group(s) not run -- his real files are elsewhere)" if not_run else ""))
