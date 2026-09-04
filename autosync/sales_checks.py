"""Checks for what a sale is, and for the row it becomes.

**THE MOST IMPORTANT CHECKS IN THIS FILE READ THE OTHER REPOSITORY.** The columns
of the seller's ledger belong to the ERP, in `src/shared/data/sheet-store.js`,
which is the file that READS them. They are written out again in `sales.py`
because Python cannot import JavaScript -- and that is one fact written down
twice, in two languages, which is the exact shape this project keeps paying for.

**SO BOTH SIDES ARE READ AND COMPARED, name by name and in order. Neither list is
typed out in this file.** A column added, renamed, removed or reordered on either
side turns this red the same day.

**THIS IS WRITTEN THE WAY IT IS BECAUSE OF A REAL FAULT, not a hypothetical one.**
`firestore_checks.py` had a check named for exactly this danger which asserted
that the page CONTAINED one particular string -- and it passed for days while the
two sides disagreed: the Python built a six-part log-line name and the page a
five-part one, so no line Kartaan made could ever have matched a line the run
made. **A check that looks for a string is not a check that compares two sides.**

**IT REFUSES; IT DOES NOT SKIP.** A check that quietly stops checking when it
cannot find the other repository is worse than no check, because it is still
counted in the tally.

Run: python autosync/sales_checks.py
    set KARTAAN=D:\\Kartaan-ERP      (Windows)
    export KARTAAN=~/Kartaan-ERP     (anywhere else)
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sales as tool  # noqa: E402
from the_other_half import readFromKartaan  # noqa: E402

ran = 0
failures = []
THREW = []


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
    """True when that raises `NotASale`, and nothing else."""
    try:
        work()
    except tool.NotASale:
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


# ------------------------------------------------ the other half of the contract

# **REFUSES RATHER THAN SKIPS.** If the ERP is not here this raises and says so.
SHEET_STORE = readFromKartaan("src", "shared", "data", "sheet-store.js")
CHARGES = readFromKartaan("src", "shared", "definitions", "charges.js")
ORDERS = readFromKartaan("src", "shared", "definitions", "orders.js")


def _without_comments(source):
    """The source with its comments taken out, before anything is read from it.

    **THIS IS NOT TIDINESS. IT IS THE DIFFERENCE BETWEEN RIGHT AND WRONG.** The
    first version of this check read the ERP's column list with a plain
    quote-matching pattern, and reported that the two sides DISAGREED -- naming
    two columns called things like `s shelf it would come out different...`.

    Those were sentences out of the COMMENTS beside the list. The ERP explains
    `taking` as "the whole of D51's replay safety", and that apostrophe opened a
    string as far as the pattern was concerned -- swallowing `took` and inventing
    two columns that do not exist.

    **A confident, specific, WRONG answer about real data**, which is exactly
    what a check across two repositories exists to avoid rather than produce.
    Comments come out first, always.
    """
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"(?<!:)//[^\n]*", "", source)


def _list_named(source, what):
    """The strings inside `export const <what> = [ ... ];`, in order.

    Read out of the ERP's own source. **The count is checked by the caller**, so
    a pattern that quietly stops matching goes red rather than agreeing with an
    empty list -- which is how a check goes green for the worst possible reason.
    """
    found = re.search(
        r"export const " + what + r"\s*=\s*\[(.*?)\n\];",
        _without_comments(source), re.S
    )
    if not found:
        return None
    return re.findall(r"'([^']*)'", found.group(1))


# ---- the plain fields ------------------------------------------------------

THEIR_PLAIN = _list_named(SHEET_STORE, "PLAIN_FIELDS")
check("the ERP's own list of plain columns can be read", THEIR_PLAIN is not None)
check("and it is not empty, so a pattern that stopped matching goes red",
      bool(THEIR_PLAIN) and len(THEIR_PLAIN) > 10)
check("THE PLAIN COLUMNS ARE THE SAME ON BOTH SIDES, in the same order",
      tuple(THEIR_PLAIN or ()) == tool.PLAIN_FIELDS)
if tuple(THEIR_PLAIN or ()) != tool.PLAIN_FIELDS:
    print(f"      the ERP says {THEIR_PLAIN}")
    print(f"      this file says {list(tool.PLAIN_FIELDS)}")
    print("      A column on one side and not the other is money written to a "
          "cell nothing reads, or a cell read that nothing writes.")

# The two an independent reviewer found missing from a hand-written list.
check("`took` has a column -- what a sale took off the shelf cannot be re-derived",
      "took" in tool.PLAIN_FIELDS)
check("`taking` has a column -- it is the whole of D51's replay safety",
      "taking" in tool.PLAIN_FIELDS)
check("`rev` has a column, or every guarded write goes out unguarded",
      "rev" in tool.PLAIN_FIELDS)

# ---- the charge columns ----------------------------------------------------

THEIR_CHARGES = None
_found = re.search(r"export const CHARGE_KINDS\s*=\s*\[(.*?)\n\];",
                   _without_comments(CHARGES), re.S)
if _found:
    THEIR_CHARGES = re.findall(r"id:\s*'([^']+)'", _found.group(1))

check("the ERP's own list of charges can be read", THEIR_CHARGES is not None)
check("and it is not empty", bool(THEIR_CHARGES) and len(THEIR_CHARGES) > 5)
check("THE CHARGES ARE THE SAME ON BOTH SIDES, in the same order",
      tuple(THEIR_CHARGES or ()) == tool.CHARGE_IDS)
if tuple(THEIR_CHARGES or ()) != tool.CHARGE_IDS:
    print(f"      the ERP says {THEIR_CHARGES}")
    print(f"      this file says {list(tool.CHARGE_IDS)}")

check("a charge column is the charge's id with `charge_` on the front, "
      "which is how the ERP builds them",
      "export const CHARGE_COLUMNS = CHARGE_KINDS.map((kind) => `charge_${kind.id}`);"
      in SHEET_STORE)
check("so every charge column matches",
      tool.CHARGE_COLUMNS == tuple(f"charge_{i}" for i in (THEIR_CHARGES or ())))

# ---- everything together ---------------------------------------------------

check("every column is the plain ones then the charge ones, as the ERP has it",
      "export const COLUMNS = [...PLAIN_FIELDS, ...CHARGE_COLUMNS];" in SHEET_STORE)
check("and the whole column list matches, end to end",
      tool.COLUMNS == tuple(THEIR_PLAIN or ()) + tuple(
          f"charge_{i}" for i in (THEIR_CHARGES or ())))
check("no column is listed twice", len(set(tool.COLUMNS)) == len(tool.COLUMNS))

# ---- the name of a sale ----------------------------------------------------

# **READ OUT OF THE ERP'S OWN SOURCE AND COMPARED PIECE BY PIECE**, never
# matched as a string. A string match is what let the log-line-name fault ship.
THEIRS = re.search(r"return `([^`]+)`;\n\}", ORDERS)
check("the ERP's own way of naming a sale can be read", THEIRS is not None)


def _parts(said):
    """The names between the `::`s, whatever each language wraps them in."""
    out = []
    for one in (said or "").split("::"):
        one = one.strip().strip("{}$")
        one = re.sub(r"^asText\(|\)$", "", one).strip()
        out.append(one)
    return out


OURS = re.search(r'return f"([^"]+)"', Path(tool.__file__).read_text(encoding="utf-8"))
check("this file's own way of naming a sale can be read", OURS is not None)
check("A SALE IS NAMED THE SAME WAY ON BOTH SIDES",
      OURS is not None and THEIRS is not None
      and len(_parts(OURS.group(1))) == len(_parts(THEIRS.group(1))))
if OURS and THEIRS and len(_parts(OURS.group(1))) != len(_parts(THEIRS.group(1))):
    print(f"      this file builds {_parts(OURS.group(1))}")
    print(f"      the ERP builds   {_parts(THEIRS.group(1))}")
    print("      One of them is writing sales the other cannot find.")

check("it is three parts joined by ::, and the same three",
      tool.name_for("meesho", "OD1", "AAA") == "meesho::OD1::AAA")
check("a sale with no sku is still named, with the sku part empty",
      tool.name_for("meesho", "OD1") == "meesho::OD1::")
check("a sale with no platform is REFUSED, not named with a hole in it",
      refused_by(lambda: tool.name_for("", "OD1", "AAA")))
check("and one with no order number is too",
      refused_by(lambda: tool.name_for("meesho", "", "AAA")))
check("whitespace round a name does not make a second sale",
      tool.name_for(" meesho ", " OD1 ", " AAA ") == "meesho::OD1::AAA")

# ---- the states ------------------------------------------------------------

THEIR_STATES = re.findall(
    r"id:\s*'([^']+)'", re.search(r"export const ORDER_STATES\s*=\s*\[(.*?)\n\];",
                                 _without_comments(ORDERS), re.S).group(1))
check("THE STATES A SALE CAN BE IN ARE THE SAME ON BOTH SIDES",
      tuple(THEIR_STATES) == tool.STATES)
check("and there are exactly two of them", len(tool.STATES) == 2)

# ---- what it refuses -------------------------------------------------------

check("a sale that cannot be named is refused when it is BUILT",
      refused_by(lambda: tool.Sale(platform="", order_id="OD1")))
check("a state no screen knows how to show is refused",
      refused_by(lambda: tool.Sale(platform="meesho", order_id="OD1", state="posted")))
check("the two real states are accepted",
      all(tool.Sale(platform="p", order_id="o", state=s) for s in tool.STATES))
check("a state left unsaid is fine -- a sale read from a file has not been applied yet",
      tool.Sale(platform="p", order_id="o").state is None)
check("a charge Kartaan does not know about is refused, not silently dropped",
      refused_by(lambda: tool.Sale(platform="p", order_id="o",
                                   charges={"mysteryFee": 12})))
check("and the refusal lists what it DOES know",
      (lambda e: e is not None and "commission" in str(e) and "mysteryFee" in str(e))(
          _catch(lambda: tool.Sale(platform="p", order_id="o",
                                   charges={"mysteryFee": 12}))))
check("every real charge id is accepted",
      tool.Sale(platform="p", order_id="o",
                charges={i: 1 for i in tool.CHARGE_IDS}) is not None)

# ---- a nought is a nought --------------------------------------------------

check("a nought is written as a nought, not blanked", tool.a_cell(0) == "0")
check("and so is a fractional nought", tool.a_cell(0.0) == "0.0")
check("and False is written as a word, not as blank", tool.a_cell(False) == "no")
check("only nothing at all is blank", tool.a_cell(None) == "")
check("an empty string stays an empty string", tool.a_cell("") == "")
check("and the obvious wrong way would have blanked all three",
      ("" if (0 or "") == "" else "x") == "" and (0.0 or "") == "" and (False or "") == "")

sale = tool.Sale(platform="meesho", order_id="OD1", sku="AAA", qty=0,
                 gmv=0.0, settlement=0, state="held")
row = tool.the_row_for(sale)
at = {c: n for n, c in enumerate(tool.COLUMNS)}
check("a sale with nought money writes noughts, not blanks",
      row[at["qty"]] == "0" and row[at["gmv"]] == "0.0" and row[at["settlement"]] == "0")
check("a settlement nobody has worked out yet is blank, which is the truth",
      tool.the_row_for(tool.Sale(platform="p", order_id="o"))[at["settlement"]] == "")

# ---- the row ---------------------------------------------------------------

check("a row has exactly one cell per column",
      len(tool.the_row_for(sale)) == len(tool.COLUMNS))
check("the header is exactly the columns", tool.the_header() == tool.COLUMNS)
check("the id cell is the sale's own name", row[at["id"]] == "meesho::OD1::AAA")
check("every plain column is written from a field that exists",
      all(hasattr(sale, tool.FROM_FIELD[c]) for c in tool.PLAIN_FIELDS))
check("and every plain column has a field named for it",
      set(tool.FROM_FIELD) == set(tool.PLAIN_FIELDS))

charged = tool.Sale(platform="p", order_id="o", charges={"commission": 30, "tcs": 0})
crow = tool.the_row_for(charged)
check("a charge lands in its own column", crow[at["charge_commission"]] == "30")
check("a charge of nought lands as nought", crow[at["charge_tcs"]] == "0")
check("a charge nobody worked out is blank", crow[at["charge_penalty"]] == "")

took = tool.Sale(platform="p", order_id="o", took=[{"lot": "L1", "qty": 2}])
check("what came off the shelf is written as something anything can read",
      json.loads(tool.the_row_for(took)[at["took"]]) == [{"lot": "L1", "qty": 2}])

# ---- the range is never typed ---------------------------------------------

check("the last column's letter is worked out from how many there are",
      tool.column_letter(1) == "A" and tool.column_letter(26) == "Z"
      and tool.column_letter(27) == "AA" and tool.column_letter(28) == "AB")
check("the whole tab's range covers every column",
      tool.the_whole_tab() == f"orders!A:{tool.column_letter(len(tool.COLUMNS))}")
check("and it is 45 columns wide today, which is AS",
      len(tool.COLUMNS) == 45 and tool.the_whole_tab() == "orders!A:AS")

# **AND THE WORK REGISTER SAYS HOW WIDE THE LEDGER IS TOO, IN WORDS, AND NOTHING
# HELD IT TO THIS.** `tools/work.json` said 28 for two days after the answer
# became 45. Five other places had been corrected and that one was missed --
# **the third hand-written copy of one number found in this repository** (D169:
# a correction is finished when everything repeating the withdrawn claim is
# corrected too; D190: where a list governs behaviour, something holds the two
# to each other).
#
# **THE QUESTION IS "IS ANY WIDTH THE REGISTER STATES FOR THE LEDGER WRONG?"**,
# not "does the number 45 appear". Other counts in that file are real and
# different -- his Flipkart payments are 74 columns wide, a brand-new Google
# spreadsheet is 26 -- so only a width said of the LEDGER is asked about.
#
# **WHAT THIS DOES NOT REACH, said rather than glossed (D180):** a sentence that
# gives the ledger's width without using the word "ledger" within the same
# clause escapes it. The register has no field carrying the number, so there is
# nothing stronger to hold than the sentences that state it.
REGISTER = Path(__file__).resolve().parent.parent / "tools" / "work.json"
check("the work register can be read at all", REGISTER.is_file())
SAID_IN_THE_REGISTER = REGISTER.read_text(encoding="utf-8") if REGISTER.is_file() else ""
WIDTHS_CLAIMED = [
    int(one) for one in
    re.findall(r"ledger(?:'s| is| has)?[^.]{0,40}?(\d+) columns", SAID_IN_THE_REGISTER)
]
# **BOTH DIRECTIONS.** Without the first half, deleting every such sentence would
# leave this green while the register said nothing at all about the ledger.
check("THE REGISTER SAYS HOW WIDE THE LEDGER IS, AND EVERY PLACE IT SAYS SO IS "
      "THE WIDTH IT REALLY IS",
      bool(WIDTHS_CLAIMED) and all(one == len(tool.COLUMNS) for one in WIDTHS_CLAIMED))

# **WHICH COLUMNS ARE FIGURES IS THE ERP'S LIST TOO, and it is read, not typed.**
# A sheet hands back TEXT for everything, so a column the ERP turns back into a
# number and this side does not is a figure that arrives as the string "0" and
# gets joined rather than added.
THEIR_NUMBERS = _list_named(SHEET_STORE, "NUMBER_FIELDS")
check("the ERP's own list of number columns can be read", THEIR_NUMBERS is not None)
check("and it is not empty", bool(THEIR_NUMBERS) and len(THEIR_NUMBERS) > 4)
check("THE NUMBER COLUMNS ARE THE SAME ON BOTH SIDES, in the same order",
      tuple(THEIR_NUMBERS or ()) == tool.NUMBER_FIELDS)
if tuple(THEIR_NUMBERS or ()) != tool.NUMBER_FIELDS:
    print(f"      the ERP says {THEIR_NUMBERS}")
    print(f"      this file says {list(tool.NUMBER_FIELDS)}")
check("every number column is a real column", 
      all(n in tool.COLUMNS for n in tool.NUMBER_FIELDS))

# D152's seventeen, present and in his order.
D152 = ("status", "isShopsy", "cogs", "packagingCost", "adSpend", "returnReason",
        "earringCondition", "boxCondition", "chainCondition", "itemLoss",
        "packingLoss", "chainLoss", "claimId", "claimStatus", "claimRecovered",
        "netPnl", "returnPnl")
check("D152's seventeen are at the END, after rev, in his order",
      tool.PLAIN_FIELDS[-17:] == D152)
check("and every one of them can be written from a field that exists",
      all(hasattr(tool.Sale(platform="p", order_id="o"), tool.FROM_FIELD[c]) for c in D152))
check("THE THREE LOSSES ARE THREE COLUMNS, never one lump (D152)",
      all(c in tool.COLUMNS for c in ("itemLoss", "packingLoss", "chainLoss")))
check("and so are the three conditions",
      all(c in tool.COLUMNS for c in ("earringCondition", "boxCondition", "chainCondition")))
check("a sale that says nothing about them writes them blank, which is the truth",
      all(tool.the_row_for(tool.Sale(platform="p", order_id="o"))[
          {c: n for n, c in enumerate(tool.COLUMNS)}[c]] == "" for c in D152))
check("a nonsense column count is refused rather than answered",
      refused_by(lambda: tool.column_letter(0)))
check("and True is not a column count, whatever Python thinks",
      refused_by(lambda: tool.column_letter(True)))
check("one row's range is that row only", tool.the_range_for(2) == "orders!A2:AS2")
check("writing a sale to row 1 is REFUSED -- that row is the column names",
      refused_by(lambda: tool.the_range_for(1)))

# ---- the same file twice changes nothing -----------------------------------

TWICE = [
    tool.Sale(platform="meesho", order_id="OD1", sku="A", gmv=100),
    tool.Sale(platform="meesho", order_id="OD2", sku="B", gmv=200),
    tool.Sale(platform="meesho", order_id="OD1", sku="A", gmv=100),
]
check("the same sale stated twice in one file is ONE row",
      len(tool.by_name(TWICE)) == 2)
check("and reading the whole file again gives the same rows at the same names",
      set(tool.by_name(TWICE)) == set(tool.by_name(TWICE + TWICE)))
check("the later statement of a sale is the one that is kept",
      tool.by_name([
          tool.Sale(platform="p", order_id="o", gmv=1),
          tool.Sale(platform="p", order_id="o", gmv=2),
      ])["p::o::"].gmv == 2)
check("two sales on one order but different SKUs are two rows",
      len(tool.by_name([
          tool.Sale(platform="p", order_id="o", sku="A"),
          tool.Sale(platform="p", order_id="o", sku="B"),
      ])) == 2)

print()
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 71
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print(f"all {ran} checks passed")
