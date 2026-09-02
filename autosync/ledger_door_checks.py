"""Checks for writing the seller's sales ledger.

**NOTHING HERE TOUCHES GOOGLE.** The transport is handed in, so every rule is
checked with no account, no sheet and no internet -- and the stand-in RECORDS
every call, so what is checked is the request that would really have gone out.

**THE CALLS ARE PINNED TO THE ERP'S OWN, not typed out from memory.** Kartaan
already talks to this API in `src/shared/data/sheet-store.js`; a second, different
way of talking to Google is the duplication D119 exists to prevent. Those checks
read that file through the door and REFUSE rather than skip when it is not there.

Run: python autosync/ledger_door_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ledger  # noqa: E402
import ledger_door as tool  # noqa: E402
import sales  # noqa: E402
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
    try:
        work()
    except ledger.LedgerRefused:
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


class Pretend:
    """A stand-in Google that remembers exactly what it was asked."""

    def __init__(self, tabs=("orders",), rows=None, blow_up=None):
        self.tabs = list(tabs)
        self.rows = [list(r) for r in (rows or [])]
        self.calls = []
        self.blow_up = blow_up

    def __call__(self, method, path, query=None, body=None):
        self.calls.append({"method": method, "path": path,
                           "query": dict(query or {}), "body": body})
        if self.blow_up:
            raise RuntimeError(self.blow_up)
        if method == "GET" and "/values/" not in path:
            return {"sheets": [{"properties": {"title": t}} for t in self.tabs]}
        if method == "GET":
            return {"values": [list(r) for r in self.rows]}
        if path.endswith(":append"):
            self.rows += [list(v) for v in body["values"]]
            return {}
        if path.endswith("values:batchUpdate"):
            for one in body["data"]:
                where = one["range"].split("!")[1].split(":")[0]
                n = int("".join(c for c in where if c.isdigit()))
                while len(self.rows) < n:
                    self.rows.append([])
                self.rows[n - 1] = list(one["values"][0])
            return {}
        return {}


HEADER = [list(sales.COLUMNS)]
AT = {c: n for n, c in enumerate(sales.COLUMNS)}
KNOWS = ("platform", "orderId", "on", "sku", "qty", "gmv")


def a_sale(order_id, **rest):
    return sales.Sale(platform="meesho", order_id=order_id, sku="A", **rest)


def a_reading(on, sale_list):
    return ledger.Reading(report="orders", on=on, knows=KNOWS, sales=tuple(sale_list))


# ------------------------------------------------------- what it will not accept

check("a door with no way of asking Google is refused",
      refused_by(lambda: tool.LedgerDoor(ask=None, sheet_id="S1")))
check("a door with no sheet id is refused",
      refused_by(lambda: tool.LedgerDoor(ask=Pretend(), sheet_id="")))
check("and the refusal says Kartaan creates the sheet, so a pasted id will not do",
      (lambda e: e is not None and "pasted id" in str(e))(
          _catch(lambda: tool.LedgerDoor(ask=Pretend(), sheet_id=" "))))

# ------------------------------------------------- is this really our sheet

check("a spreadsheet with no orders tab is refused",
      refused_by(lambda: tool.LedgerDoor(Pretend(tabs=("Sheet1",)), "S1").everything()))
check("and the refusal names the tabs it DOES have",
      (lambda e: e is not None and "Sheet1" in str(e))(
          _catch(lambda: tool.LedgerDoor(Pretend(tabs=("Sheet1",)), "S1").everything())))
check("a spreadsheet Google says nothing about is refused",
      tool.why_that_sheet_will_not_do(None) is not None)
check("one with the orders tab is fine",
      tool.why_that_sheet_will_not_do({"sheets": [{"properties": {"title": "orders"}}]}) is None)

# **IT IS ACTUALLY CALLED.** The ERP's own version of this existed, was checked,
# and was called by nothing until an independent reviewer found it.
g = Pretend()
door = tool.LedgerDoor(g, "S1")
answered(lambda: door.everything())
check("THE SHEET IS CHECKED BEFORE A SINGLE CELL IS READ",
      len(g.calls) >= 2 and "/values/" not in g.calls[0]["path"])
check("and only the tab names are asked for, not every cell in the spreadsheet",
      g.calls[0]["query"].get("fields") == "sheets.properties.title")
before = len(g.calls)
answered(lambda: door.everything())
check("it is asked ONCE, not on every call",
      len([c for c in g.calls if "/values/" not in c["path"]]) == 1)

g2 = Pretend(tabs=("Sheet1",))
d2 = tool.LedgerDoor(g2, "S1")
check("a sheet that will not do is refused when it is WRITTEN to as well as read",
      refused_by(lambda: d2.carry_out(ledger.Plan(append=(tuple("x" * len(sales.COLUMNS)),)))))

# --------------------------------------------------------------- the calls

g = Pretend(rows=HEADER)
door = tool.LedgerDoor(g, "S1")
plan = ledger.plan(door.everything(), [a_reading("2026-08-01", [a_sale("O1", gmv=100)])])
did = answered(lambda: door.carry_out(plan))
check("a new sale is added", did == {"added": 1, "changed": 0})
add = [c for c in g.calls if c["path"].endswith(":append")][-1]
check("adding uses append, as the ERP does", add["method"] == "POST")
check("with RAW, so Google does not reinterpret a figure",
      add["query"].get("valueInputOption") == "RAW")
check("and INSERT_ROWS, so it never writes over what is there",
      add["query"].get("insertDataOption") == "INSERT_ROWS")
check("the range in the path is the whole tab, worked out from the columns",
      "orders%21A%3AAB" in add["path"])
check("the row sent has one cell per column",
      len(add["body"]["values"][0]) == len(sales.COLUMNS))

plan2 = ledger.plan(door.everything(), [a_reading("2026-08-05", [a_sale("O1", gmv=150)])])
did = answered(lambda: door.carry_out(plan2))
check("a sale that has changed is updated, not added again",
      did == {"added": 0, "changed": 1})
up = [c for c in g.calls if c["path"].endswith("values:batchUpdate")][-1]
check("changing uses batchUpdate, as the ERP does", up["method"] == "POST")
check("with RAW there too", up["body"].get("valueInputOption") == "RAW")
check("the range names the row that sale is really on",
      up["body"]["data"][0]["range"] == "orders!A2:AB2")
check("and the sheet now holds the new figure",
      g.rows[1][AT["gmv"]] == "150")
check("the ledger still holds one row for that sale, not two", len(g.rows) == 2)

# **ONE CALL FOR MANY ROWS.**
g = Pretend(rows=HEADER)
door = tool.LedgerDoor(g, "S1")
many = ledger.plan(door.everything(),
                   [a_reading("2026-08-01", [a_sale(f"O{n}") for n in range(20)])])
door.carry_out(many)
door.carry_out(ledger.plan(door.everything(),
                           [a_reading("2026-08-09", [a_sale(f"O{n}", gmv=1) for n in range(20)])]))
check("twenty rows are added in ONE call",
      len([c for c in g.calls if c["path"].endswith(":append")]) == 1)
check("and twenty rows are changed in ONE call",
      len([c for c in g.calls if c["path"].endswith("values:batchUpdate")]) == 1)
check("that one call carries all twenty ranges",
      len([c for c in g.calls if c["path"].endswith("values:batchUpdate")][0]["body"]["data"]) == 20)

# ---------------------------------------------------------- a quiet night

g = Pretend(rows=HEADER)
door = tool.LedgerDoor(g, "S1")
door.everything()
writes_before = len([c for c in g.calls if c["method"] == "POST"])
did = answered(lambda: door.carry_out(ledger.Plan()))
check("a night with nothing to write makes NO write call at all",
      len([c for c in g.calls if c["method"] == "POST"]) == writes_before)
check("and says so plainly", did == {"added": 0, "changed": 0})

# ------------------------------------------------------------ what it refuses

check("writing a sale over row 1 is refused -- that row is the column names",
      refused_by(lambda: tool.LedgerDoor(Pretend(rows=HEADER), "S1").carry_out(
          ledger.Plan(update=((1, tuple("" for _ in sales.COLUMNS)),)))))
check("and the refusal says what would happen",
      (lambda e: e is not None and "column names" in str(e))(
          _catch(lambda: tool.LedgerDoor(Pretend(rows=HEADER), "S1").carry_out(
              ledger.Plan(update=((1, tuple("" for _ in sales.COLUMNS)),))))))
check("a row with the wrong number of cells is refused, not written wonky",
      refused_by(lambda: tool.LedgerDoor(Pretend(rows=HEADER), "S1").carry_out(
          ledger.Plan(append=(("a", "b"),)))))
check("something that is not a plan at all is refused",
      refused_by(lambda: tool.LedgerDoor(Pretend(rows=HEADER), "S1").carry_out("go on then")))
check("nothing in this door can remove a row", not hasattr(tool.LedgerDoor, "remove"))

# **THE ORDER OF THE TWO WRITES.** Changing first keeps every row number in the
# plan true at the moment it is used.
g = Pretend(rows=HEADER + [["meesho::O1::A"] + ["" for _ in sales.COLUMNS[1:]]])
door = tool.LedgerDoor(g, "S1")
door.carry_out(ledger.Plan(
    append=(tuple("x" for _ in sales.COLUMNS),),
    update=((2, tuple("y" for _ in sales.COLUMNS)),),
))
kinds = [("update" if c["path"].endswith("values:batchUpdate") else "append")
         for c in g.calls if c["method"] == "POST"]
check("CHANGES GO FIRST AND ADDITIONS LAST", kinds == ["update", "append"])

# ----------------------------------------------- a failure is not swallowed

g = Pretend(blow_up="Google said no")
check("Google refusing is not swallowed into a quiet success",
      (lambda e: e is not None and "Google said no" in str(e))(
          _catch(lambda: tool.LedgerDoor(g, "S1").everything())))

# ---------------------------------------------- the header, on an empty sheet

g = Pretend(rows=[])
door = tool.LedgerDoor(g, "S1")
check("an empty sheet reads as nothing, not as a fault", door.everything() == [])
door.write_the_header()
check("the header written is exactly the ledger's columns",
      g.rows and tuple(g.rows[0]) == sales.COLUMNS)

# **THE HEADER'S OWN CALL WAS UNCHECKED, and the proving pass found it.** Both
# `write_the_header` and `carry_out` send the same two options, so a fault put
# into the FIRST of them -- the header's -- went unnoticed by every check here.
head = [c for c in g.calls if c["path"].endswith(":append")][-1]
check("the header is sent RAW too, so Google does not reinterpret a column name",
      head["query"].get("valueInputOption") == "RAW")
check("and with INSERT_ROWS, so writing it can never overwrite a sale",
      head["query"].get("insertDataOption") == "INSERT_ROWS")
check("it goes to the ledger's own tab, not somewhere else",
      "orders%21A%3AAB" in head["path"])

# --------------------------------------- pinned to the ERP's own calls

THEIRS = readFromKartaan("src", "shared", "data", "sheet-store.js")
for what, needle in (
    ("the whole ledger is read with one values GET",
     "/values/${encodeURIComponent(WHOLE_TAB)}`"),
    ("rows are added with append", ":append`"),
    ("rows are changed with values:batchUpdate", "/values:batchUpdate`"),
    ("figures are sent RAW", "valueInputOption: 'RAW'"),
    ("adding never writes over what is there", "insertDataOption: 'INSERT_ROWS'"),
    ("the sheet is checked by asking only for tab titles",
     "fields: 'sheets.properties.title'"),
):
    check(f"THE ERP DOES IT THIS WAY TOO: {what}", needle in THEIRS)

check("and this door uses the same tab name the ERP does",
      f"export const THE_TAB = '{sales.THE_TAB}'" in THEIRS)
check("nothing here invents a second address for Google",
      tool.API == "https://sheets.googleapis.com")

print()
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 49
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print(f"all {ran} checks passed")
