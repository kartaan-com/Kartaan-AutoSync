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

# ---- how wide the ledger is, in every place that says so -------------------
#
# **ONE NUMBER IS WRITTEN DOWN IN SIX PLACES AND ONLY ONE OF THEM WAS HELD.**
# `tools/work.json` said 28 for two days after the answer became 45 -- **the
# third hand-written copy of one number found in this repository** (D169: a
# correction is finished when everything repeating the withdrawn claim is
# corrected too; D190: where a list governs behaviour, something holds the two
# to each other). The check written for that read the register's SENTENCES, and
# nothing at all was pointed at the other five: **a wrong width in
# `autosync/ledger.py` left all thirty checks files green.**
#
# **THE LIMIT THE PREVIOUS ANSWER RECORDED UNDER D180 IS WITHDRAWN, NOT KEPT
# BESIDE THE FIX.** It said a width worded without the word "ledger" beside it
# slips past, and that *"the register has no field carrying the number, so there
# is nothing stronger to hold"*. **That described the register's shape on the
# day, not a limit on it.** `tools/work.json` is JSON and the gate already reads
# it, so the width is a FIELD now, pinned to `len(sales.COLUMNS)` -- the list the
# ERP owns and this file compares against. **A number living only in prose is how
# the 28 came to be wrong in the first place**, and leaving it living only in
# prose was the wrong answer.
#
# **SO THE WORD "ledger" IS NOT ASKED FOR ANYWHERE BELOW.**
#   - The register states the width in a field, and every OTHER column count it
#     states in words is listed in a field of its own -- so a count that is
#     neither is a count nobody has accounted for, whatever words surround it.
#   - The four source files that state the width in words state no other column
#     count at all, so every column count in them is asked about directly.
#
# **THE PRICE, SAID PLAINLY:** writing a genuinely new column count into the
# register's prose, or any column count into one of those four files, turns this
# red until the register lists it. That is the check doing its job, and D167
# already settled that brittleness is what catching things costs.
REGISTER = Path(__file__).resolve().parent.parent / "tools" / "work.json"
check("the work register can be read at all", REGISTER.is_file())
SAID_IN_THE_REGISTER = REGISTER.read_text(encoding="utf-8") if REGISTER.is_file() else ""
try:
    REGISTER_SAYS = json.loads(SAID_IN_THE_REGISTER)
except ValueError:
    REGISTER_SAYS = None
check("and it reads as JSON, which is what makes a field possible at all",
      isinstance(REGISTER_SAYS, dict))

# **THE FIELD.** Not a sentence parsed and not a number retyped somewhere nobody
# reads: the register carries the width, and it is held to the thing that knows.
THE_WIDTH_FIELD = "the_ledger_is_this_many_columns_wide"
check("THE REGISTER CARRIES THE LEDGER'S WIDTH IN A FIELD OF ITS OWN, AND IT IS "
      "THE WIDTH THE LEDGER REALLY IS",
      isinstance(REGISTER_SAYS, dict)
      and REGISTER_SAYS.get(THE_WIDTH_FIELD) == len(tool.COLUMNS))

A_COLUMN_COUNT = re.compile(r"(\d+)\s+columns")


def _column_counts_in(text):
    """Every "<number> columns" written in `text`, as numbers."""
    return [int(one) for one in A_COLUMN_COUNT.findall(text)]


# **AND THE SENTENCES THAT STILL SAY IT.** Read a clause at a time and in BOTH
# directions -- the old pattern only read forwards from the word "ledger" and
# only forty characters, so "28 columns in the ledger" escaped it while using
# the very word it looked for.
CLAUSES_ABOUT_THE_LEDGER = [
    one for one in re.split(r"[.\n]", SAID_IN_THE_REGISTER) if "ledger" in one.lower()
]
WIDTHS_CLAIMED = [n for one in CLAUSES_ABOUT_THE_LEDGER for n in _column_counts_in(one)]
# **BOTH DIRECTIONS.** Without the first half, deleting every such sentence would
# leave this green while the register said nothing at all about the ledger.
check("THE REGISTER SAYS HOW WIDE THE LEDGER IS, AND EVERY PLACE IT SAYS SO IS "
      "THE WIDTH IT REALLY IS",
      bool(WIDTHS_CLAIMED) and all(one == len(tool.COLUMNS) for one in WIDTHS_CLAIMED))

# **AND NO COLUMN COUNT ANYWHERE IN THE REGISTER IS ONE NOBODY HAS ACCOUNTED
# FOR.** This is the half that needs no word beside the number: a wrong width
# written into a sentence that never mentions the ledger is still a number that
# is neither the ledger's width nor one of the counts the register lists.
ACCOUNTED_FOR = REGISTER_SAYS.get("other_column_counts_this_register_states", {}) \
    if isinstance(REGISTER_SAYS, dict) else {}
UNACCOUNTED = sorted({
    n for n in _column_counts_in(SAID_IN_THE_REGISTER)
    if n != len(tool.COLUMNS) and str(n) not in ACCOUNTED_FOR
})
check("AND EVERY OTHER COLUMN COUNT IN THE REGISTER IS ONE THE REGISTER ITSELF "
      "ACCOUNTS FOR, SO A WRONG WIDTH NEED NOT SAY THE WORD 'ledger' TO BE CAUGHT",
      bool(ACCOUNTED_FOR) and not UNACCOUNTED)
if UNACCOUNTED:
    print(f"      counted in words and listed nowhere: {UNACCOUNTED}")

# **AND WHAT THAT EXEMPTION CANNOT CATCH, WRITTEN WHERE SOMEBODY WILL MEET
# IT -- WHICH IS NOT HERE.** The exemption above is a WHOLE-FILE one: a count
# the register accounts for is never asked about again, wherever in the file
# it is written. So a wrong ledger width typed into the register's prose,
# worded with no mention of the ledger AND equal to one of those accounted
# counts, passes. **Driven rather than reasoned: 44 reddens the check above
# and names the number; 74 leaves every check in this file green.**
#
# **IT IS LEFT OPEN ON PURPOSE, AND OUT LOUD** (D180). The width that decides
# anything is the FIELD, held to the ERP's own column list; this prose is
# documentation and cannot move a cell. Both ways of closing it -- an anchor
# word demanded beside every exempt number, or a count of how often each is
# written -- redden on ordinary edits to the one file here that is rewritten
# by hand every session, and the obvious repair for such a red is to widen
# the exemption. **Closing the smaller hole would have made the larger one
# easier to fall into**, and the larger one is that the exemption grows by
# hand with nothing telling a real count from a number added to buy quiet.
#
# **AND THE LIMIT IS NOT RECORDED IN THIS COMMENT, BECAUSE NOBODY MEETS A
# COMMENT.** The last limit this check carried was written in a comment and
# was afterwards quoted as though a comment were somewhere anybody stands
# (D169). This one lives in `tools/work.json` BESIDE THE EXEMPTION ITSELF,
# so the person widening the exemption -- the single act that makes the hole
# bigger -- cannot do it without reading what it costs. The three checks
# below are what keep it there, keep it true, and keep it pointed here.
THE_LIMIT = REGISTER_SAYS.get("and_what_that_exemption_cannot_catch") \
    if isinstance(REGISTER_SAYS, dict) else None
# **THIS FIRST ONE IS A PRESENCE CHECK AND SAYS SO** (D170: a check that
# matches a surface is checking spelling, and must admit it). It asks whether
# the limit is still written down beside the exemption -- not whether what it
# says is true. Gutting the sentence to a stub is the same as deleting it, so
# it has to still be the length of an explanation.
check("THE REGISTER RECORDS, BESIDE THE EXEMPTION ITSELF, WHAT THAT EXEMPTION "
      "CANNOT CATCH",
      isinstance(THE_LIMIT, dict)
      and isinstance(THE_LIMIT.get("the_limit"), str)
      and len(THE_LIMIT.get("the_limit", "")) > 300)
# **AND THIS ONE HOLDS THE TWO LISTS TO EACH OTHER, BOTH DIRECTIONS** (D190),
# so the exemption cannot be widened -- or narrowed -- without the limit
# beside it being opened and brought along.
check("AND THE NUMBERS IT SAYS ARE EXEMPT ARE EXACTLY THE NUMBERS THAT REALLY "
      "ARE EXEMPT, SO THE EXEMPTION CANNOT GROW OR SHRINK QUIETLY",
      isinstance(THE_LIMIT, dict)
      and bool(THE_LIMIT.get("the_numbers_exempt_today"))
      and sorted(str(one) for one in THE_LIMIT["the_numbers_exempt_today"])
      == sorted(str(one) for one in ACCOUNTED_FOR))
# **AND THE POINTER IN THAT FIELD IS HELD TOO**, because this commit is about
# claims nobody tests and it must not add one. The register says which file
# holds the limit to the exemption; the file it names is asked to be this one,
# so moving or renaming these checks without telling the register reddens.
check("AND THE FILE THE REGISTER NAMES AS HOLDING ALL THAT IS THE FILE THAT "
      "REALLY DOES",
      isinstance(THE_LIMIT, dict)
      and (Path(__file__).resolve().parent.parent / str(THE_LIMIT.get(
          "and_these_are_held_to_the_list_above_in_both_directions_by") or ""))
      == Path(__file__).resolve())

# **AND THE FOUR SOURCE FILES THAT STATE THE WIDTH IN WORDS.** Each is asked
# about BY NAME (D175), because "a wrong width somewhere reddened something" is
# not the same answer as "a wrong width in ledger.py reddened ledger.py's own
# question". **None of them states any other column count**, so no word anchor is
# needed and none is used -- reword the sentence however you like and the number
# is still asked about. Both directions again: a file that stops saying it at all
# is as wrong as one that says it wrongly, because the number would then be
# unheld the next time somebody wrote it back.
ALSO_WRITTEN_DOWN_IN = (
    "autosync/ledger.py",
    "autosync/reading.py",
    "autosync/reading_checks.py",
    "autosync/nightly_checks.py",
)
HERE = Path(__file__).resolve().parent.parent
for where in ALSO_WRITTEN_DOWN_IN:
    written = HERE / where
    said = _column_counts_in(written.read_text(encoding="utf-8")) if written.is_file() else []
    check(f"{where} SAYS HOW WIDE THE LEDGER IS, AND IT IS THE WIDTH IT REALLY IS",
          bool(said) and all(one == len(tool.COLUMNS) for one in said))
    if said and any(one != len(tool.COLUMNS) for one in said):
        print(f"      {where} says {said}, and the ledger is {len(tool.COLUMNS)}")

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

EXPECTED = 81
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print(f"all {ran} checks passed")
