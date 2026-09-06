"""Checks for making, finding and writing the seller's sales ledger.

**NOTHING HERE TOUCHES GOOGLE.** Both transports are handed in, so every rule
below is checked with no account, no Drive, no spreadsheet and no internet -- and
both stand-ins RECORD every call, so what is checked is the request that would
really have gone out, not a description of it.

**THE ONE THIS FILE EXISTS FOR: A LEDGER IS NEVER MADE TWICE.** Every other
failure here costs a night. Making a second, empty ledger beside the one holding
a seller's whole history costs the history, and it does it in silence -- the run
succeeds, the sheet looks right, and nobody finds out until they open the wrong
one. Three separate refusals below exist for that one fault, and each is checked
by driving the thing it refuses.

Run: python autosync/ledger_sheet_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import drive_door  # noqa: E402
import ledger  # noqa: E402
import ledger_sheet as tool  # noqa: E402
import sales  # noqa: E402

ran = 0
failures = []
THREW = []


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


def answered(work):
    try:
        return work()
    except Exception as wrong:  # noqa: BLE001
        THREW.append(repr(wrong))
        return None


def refused(work):
    """Did this refuse? Answers the refusal, or None if it did not refuse."""
    try:
        work()
        return None
    except Exception as wrong:  # noqa: BLE001
        return wrong


class ADriveReply:
    """What Drive's transport hands back, in the five shapes `_every_file` reads."""

    def __init__(self, body, status=200):
        self.status = status
        self._body = body

    @property
    def ok(self):
        return 200 <= self.status < 300

    @property
    def text(self):
        return str(self._body)

    def json(self):
        return self._body


class PretendDrive:
    """A stand-in Drive that remembers exactly what it was asked.

    `live` is what a search for `trashed = false` finds; `binned` is what a search
    for `trashed = true` finds. **They are answered separately on purpose**: the
    whole point of asking twice is that the two answers are different.
    """

    def __init__(self, live=(), binned=(), incomplete=False, status=200):
        self.live = [dict(one) for one in live]
        self.binned = [dict(one) for one in binned]
        self.incomplete = incomplete
        self.status = status
        self.asked = []

    def get(self, url, params=None, headers=None):
        self.asked.append({"url": url, "params": dict(params or {})})
        looking = (params or {}).get("q", "")
        files = self.binned if "trashed = true" in looking else self.live
        body = {"files": [dict(one) for one in files]}
        if self.incomplete:
            body["incompleteSearch"] = True
        return ADriveReply(body, status=self.status)


class PretendSheets:
    """A stand-in Google Sheets that remembers exactly what it was asked.

    It answers the three questions `LedgerDoor` asks -- what tabs are in it, what
    is in the tab, and here is something to write -- and nothing else.
    """

    def __init__(self, tabs=("orders",), rows=None, missing=False, makes="new-sheet-id"):
        self.tabs = list(tabs)
        self.rows = [list(r) for r in (rows or [])]
        self.missing = missing
        self.makes = makes
        self.calls = []

    def __call__(self, method, path, query=None, body=None):
        self.calls.append({"method": method, "path": path,
                           "query": dict(query or {}), "body": body})
        if method == "POST" and path == "/v4/spreadsheets":
            return {"spreadsheetId": self.makes} if self.makes else {}
        if self.missing:
            raise drive_door.DriveSaidNo("GET: Google refused (404) about the sales ledger.")
        if method == "GET" and "/values/" not in path:
            return {"sheets": [{"properties": {"title": t}} for t in self.tabs]}
        if method == "GET":
            return {"values": [list(r) for r in self.rows]}
        if method == "POST" and ":append" in path:
            self.rows += [list(r) for r in (body or {}).get("values", [])]
            return {}
        if method == "POST" and "values:batchUpdate" in path:
            return {}
        return {}

    def wrote(self):
        return [c for c in self.calls if c["method"] == "POST"]

    def made_a_spreadsheet(self):
        return [c for c in self.calls if c["path"] == "/v4/spreadsheets"]


THE_HEADER = [list(sales.the_header())]


# ------------------------------------------------------------- finding it

nothing_there = PretendDrive()
check("a seller who has never had a ledger is answered with nothing, not a refusal",
      answered(lambda: tool.find_the_ledger(nothing_there)) is None)
check("and the rubbish bin is asked before that answer is given",
      any("trashed = true" in a["params"].get("q", "") for a in nothing_there.asked))
check("the live search asks for a spreadsheet by name and by kind",
      f"name = '{tool.THE_SHEET_IS_CALLED}'" in nothing_there.asked[0]["params"]["q"]
      and tool.SPREADSHEET in nothing_there.asked[0]["params"]["q"])

one_there = PretendDrive(live=[{"id": "sheet-1", "name": tool.THE_SHEET_IS_CALLED}])
check("a ledger this app already made is found and its address answered",
      answered(lambda: tool.find_the_ledger(one_there)) == "sheet-1")
check("and once it is found the rubbish bin is never asked",
      not any("trashed = true" in a["params"].get("q", "") for a in one_there.asked))

two_there = PretendDrive(live=[{"id": "sheet-1", "name": tool.THE_SHEET_IS_CALLED},
                               {"id": "sheet-2", "name": tool.THE_SHEET_IS_CALLED}])
check("two ledgers of one name is refused, never chosen between",
      isinstance(refused(lambda: tool.find_the_ledger(two_there)), tool.CannotMakeTheLedger))
check("and the refusal says nothing was written to either",
      "nothing has been written to either" in str(refused(lambda: tool.find_the_ledger(two_there))))

# **THE ONE THAT MATTERS MOST.** A deleted ledger and a ledger that never existed
# look identical to a search that only asks `trashed = false` -- and answering the
# second as though it were the first makes a new empty sheet on top of the
# seller's whole history, with nothing saying so (D184).
in_the_bin = PretendDrive(binned=[{"id": "sheet-9", "name": tool.THE_SHEET_IS_CALLED}])
check("A LEDGER IN THE SELLER'S RUBBISH BIN IS NOT 'NO LEDGER' -- it stops the run",
      isinstance(refused(lambda: tool.find_the_ledger(in_the_bin)), tool.TheLedgerIsGone))
check("and what it says begins by telling them to restore it",
      "RESTORE IT FIRST" in str(refused(lambda: tool.find_the_ledger(in_the_bin))))
check("and says plainly that no new sheet is made in its place",
      "NOT MADE IN ITS PLACE" in str(refused(lambda: tool.find_the_ledger(in_the_bin))))

# **THE LISTING IS THE ONE WITH THE GUARDS ON IT.** A short listing reads as "no
# ledger", and "no ledger" is what makes a new one -- so an incomplete search must
# refuse here exactly as it does everywhere else (D161).
half_a_listing = PretendDrive(incomplete=True)
check("an incomplete search refuses rather than reading as 'there is no ledger'",
      isinstance(refused(lambda: tool.find_the_ledger(half_a_listing)), drive_door.DriveSaidNo))
check("a Drive that refuses the listing is not read as 'there is no ledger' either",
      isinstance(refused(lambda: tool.find_the_ledger(PretendDrive(status=500))),
                 drive_door.DriveSaidNo))
check("and the listing asks Drive for the page marker by name, so a second page cannot be missed",
      "nextPageToken" in nothing_there.asked[0]["params"]["fields"])


# --------------------------------------------------------------- making it

BODY = tool.the_creating_call()
check("the spreadsheet is made with the one name this file looks for",
      BODY["properties"]["title"] == tool.THE_SHEET_IS_CALLED)
check("the tab is named in the same call that makes the spreadsheet",
      BODY["sheets"][0]["properties"]["title"] == sales.THE_TAB)
# **PINNED TO THE DOOR'S OWN REFUSAL, not to the word "orders".** The door turns
# away any spreadsheet without that tab; a sheet made with a tab the door rejects
# would be created successfully and be unwritable for ever.
import ledger_door  # noqa: E402

check("and the tab it makes is one the door will actually accept",
      ledger_door.why_that_sheet_will_not_do(
          {"sheets": [{"properties": {"title": BODY["sheets"][0]["properties"]["title"]}}]}
      ) is None)

GRID = BODY["sheets"][0]["properties"]["gridProperties"]
check("THE GRID IS MADE AS WIDE AS THE LEDGER, worked out and never typed",
      GRID["columnCount"] == len(sales.COLUMNS))
# **AND THIS IS NOT DECORATION.** A new Google spreadsheet is 26 columns wide.
# Without the line above, the sheet would be made successfully, would look
# perfectly right, and would refuse the first sale ever written into it.
check("and the ledger really is wider than a new spreadsheet's 26 columns",
      len(sales.COLUMNS) > 26)
check("the column names stay on screen when the seller scrolls",
      GRID["frozenRowCount"] == 1)

made = PretendSheets()
check("making the ledger answers which spreadsheet it made",
      answered(lambda: tool.make_the_ledger(made)) == "new-sheet-id")
check("and it is one POST to the spreadsheets address",
      len(made.made_a_spreadsheet()) == 1)

said_nothing = PretendSheets(makes="")
check("Google saying nothing about which spreadsheet it made is refused, not carried on from",
      isinstance(refused(lambda: tool.make_the_ledger(said_nothing)), tool.CannotMakeTheLedger))
check("and the refusal says no file was written down as read",
      "written down as read" in str(refused(lambda: tool.make_the_ledger(PretendSheets(makes="")))))


# --------------------------------------------------------------- the header

from ledger_door import LedgerDoor  # noqa: E402

blank = PretendSheets(rows=[])
door_on_blank = LedgerDoor(blank, "sheet-1")
check("a sheet with nothing in it has the column names put on row 1",
      "put on row 1" in str(answered(lambda: tool.make_sure_the_header_is_there(door_on_blank))))
check("and what was written is exactly the ledger's columns, in order",
      blank.rows and blank.rows[0] == list(sales.the_header()))

right = PretendSheets(rows=list(THE_HEADER))
door_on_right = LedgerDoor(right, "sheet-1")
check("a sheet whose header is already right is left alone",
      "already right" in str(answered(lambda: tool.make_sure_the_header_is_there(door_on_right))))
check("and not one cell is written to it",
      not right.wrote())

# **THE ONE THAT MATTERS.** A ledger written before a column existed has a header
# that was right the day it was made. Rewriting it silently renames every column
# of every row already in it.
short = PretendSheets(rows=[list(sales.the_header())[:-3], ["a"] * 42])
door_on_short = LedgerDoor(short, "sheet-1")
check("a sheet whose header is not this ledger's columns is REFUSED, never rewritten",
      isinstance(refused(lambda: tool.make_sure_the_header_is_there(door_on_short)),
                 tool.CannotMakeTheLedger))
check("and nothing at all is written to it",
      not short.wrote())
check("and the refusal names how many columns it found and how many there should be",
      f"{len(sales.COLUMNS)}" in str(refused(lambda: tool.make_sure_the_header_is_there(
          LedgerDoor(PretendSheets(rows=[list(sales.the_header())[:-3]]), "s")))))

renamed = PretendSheets(rows=[["id", "platform", "WRONG"] + list(sales.the_header())[3:]])
check("one renamed column is enough to refuse -- it is not a near-enough header",
      isinstance(refused(lambda: tool.make_sure_the_header_is_there(LedgerDoor(renamed, "s"))),
                 tool.CannotMakeTheLedger))
check("and it names WHICH column first disagrees, so somebody can mend it",
      "column 3" in str(refused(lambda: tool.make_sure_the_header_is_there(
          LedgerDoor(PretendSheets(rows=[["id", "platform", "WRONG"]
                                         + list(sales.the_header())[3:]]), "s")))))


# ----------------------------------------------------------- asking Google

class ASheetsReply:
    def __init__(self, body=None, status=200, text=""):
        self.status = status
        self._body = body if body is not None else {}
        self._text = text

    @property
    def ok(self):
        return 200 <= self.status < 300

    @property
    def text(self):
        return self._text

    def json(self):
        return self._body


class PretendConnection:
    """The seller's own `Google`, as far as this file needs it."""

    def __init__(self, status=200, text=""):
        self.status = status
        self.text_ = text
        self.calls = []

    def get(self, url, params=None, headers=None):
        self.calls.append(("GET", url, dict(params or {}), None))
        return ASheetsReply({"sheets": []}, self.status, self.text_)

    def post(self, url, params=None, headers=None, json=None, data=None):
        self.calls.append(("POST", url, dict(params or {}), json))
        return ASheetsReply({"spreadsheetId": "made-it"}, self.status, self.text_)


line = PretendConnection()
asking = tool.a_way_to_ask(line)
answered(lambda: asking("GET", "/v4/spreadsheets/abc", query={"fields": "x"}))
check("a question goes to Google's own Sheets address and nowhere else",
      line.calls[0][1] == "https://sheets.googleapis.com/v4/spreadsheets/abc")
check("and what was asked for is carried as it was given",
      line.calls[0][2] == {"fields": "x"})

answered(lambda: asking("POST", "/v4/spreadsheets", body={"a": 1}))
check("a write carries its body", line.calls[1][3] == {"a": 1})

check("a way of talking to Google that this file has not read the documentation for is refused",
      isinstance(refused(lambda: asking("DELETE", "/v4/spreadsheets/abc")),
                 tool.CannotMakeTheLedger))

# **A REFUSAL IS A REFUSAL, NOT AN EMPTY ANSWER.** Read as an empty answer, a 403
# on the ledger would look exactly like a ledger with nothing in it -- and every
# sale the seller has ever made would be appended again as new.
sour = tool.a_way_to_ask(PretendConnection(status=403, text="no"))
check("Google refusing is raised, never handed back as an empty ledger",
      isinstance(refused(lambda: sour("GET", "/v4/spreadsheets/abc")), drive_door.DriveSaidNo))
check("and the refusal says the status rather than what was sent",
      "403" in str(refused(lambda: sour("GET", "/v4/spreadsheets/abc"))))


# ------------------------------------------------------- putting it together

# 1. A REMEMBERED ADDRESS IS USED AND NEVER SECOND-GUESSED.
known = PretendSheets(rows=list(THE_HEADER))
drive_for_known = PretendDrive()
door, which = answered(lambda: tool.the_ledger(
    drive_for_known, remembered="sheet-7", ask=known)) or (None, None)
check("a ledger whose address is remembered is used", which == "sheet-7")
check("and Drive is never searched for it at all", not drive_for_known.asked)
check("and no second spreadsheet is made", not known.made_a_spreadsheet())

# 2. A REMEMBERED ADDRESS THAT NO LONGER ANSWERS STOPS THE RUN.
gone = PretendSheets(missing=True)
check("a remembered ledger that has gone stops the run and says so",
      isinstance(refused(lambda: tool.the_ledger(PretendDrive(), remembered="sheet-7", ask=gone)),
                 tool.TheLedgerIsGone))
check("AND IT NEVER MAKES ANOTHER ONE -- not one spreadsheet was created",
      not gone.made_a_spreadsheet())
check("and it does not fall back to searching Drive by name either",
      not PretendDrive().asked)

wrong_sheet = PretendSheets(tabs=("Sheet1",), rows=[])
check("a remembered address pointing at some other spreadsheet stops the run too",
      isinstance(refused(lambda: tool.the_ledger(PretendDrive(), remembered="sheet-7",
                                                 ask=wrong_sheet)), tool.TheLedgerIsGone))
check("and that one makes no spreadsheet either", not wrong_sheet.made_a_spreadsheet())

# 3. NOTHING REMEMBERED, SOMETHING THERE: ADOPT IT.
adopting = PretendSheets(rows=list(THE_HEADER))
_, adopted = answered(lambda: tool.the_ledger(
    PretendDrive(live=[{"id": "sheet-3", "name": tool.THE_SHEET_IS_CALLED}]), ask=adopting)) \
    or (None, None)
check("a first night that finds the seller's existing ledger adopts it", adopted == "sheet-3")
check("and does not make a second one beside it", not adopting.made_a_spreadsheet())

# 4. NOTHING REMEMBERED, NOTHING THERE: MAKE IT, AND FINISH IT.
fresh = PretendSheets(rows=[])
_, brand_new = answered(lambda: tool.the_ledger(PretendDrive(), ask=fresh)) or (None, None)
check("a seller with no ledger at all gets one made", brand_new == "new-sheet-id")
check("and its column names are written before anything else happens",
      fresh.rows and fresh.rows[0] == list(sales.the_header()))

# 5. A SHEET MADE BY A RUN THAT DIED BEFORE WRITING ROW 1 IS MENDED, NOT REMADE.
half_made = PretendSheets(rows=[])
_, mended = answered(lambda: tool.the_ledger(
    PretendDrive(live=[{"id": "sheet-4", "name": tool.THE_SHEET_IS_CALLED}]), ask=half_made)) \
    or (None, None)
check("a ledger made but never given its column names is adopted and finished",
      mended == "sheet-4" and half_made.rows[0] == list(sales.the_header()))
check("and no second one is made to replace it", not half_made.made_a_spreadsheet())

# **WHAT HAPPENED IS SAID OUT LOUD.** A run that quietly made a seller's ledger is
# a run nobody can ask about afterwards.
spoken = []
answered(lambda: tool.the_ledger(PretendDrive(), say=spoken.append, ask=PretendSheets(rows=[])))
check("making a seller's ledger is said in the run's own words",
      any("has been made" in one for one in spoken))


# ----------------------------------------------------------- writing into it

A_SALE = sales.Sale(platform="meesho", order_id="M-1", sku="RING-1", qty=1, gmv=499)
A_READING = ledger.Reading(report="ms_orders", on="2026-09-01",
                           knows=("platform", "orderId", "on", "sku", "qty", "gmv"),
                           sales=(A_SALE,), which="file-1")

sheet = PretendSheets(rows=list(THE_HEADER))
record = tool.recording_into(LedgerDoor(sheet, "sheet-1"))
answered(lambda: record([A_READING]))
check("A SALE THAT IS READ ACTUALLY REACHES THE SELLER'S SHEET",
      any(A_SALE.id in str(r) for r in sheet.rows))

# **THE SHEET IS READ AGAIN FOR EVERY FILE**, or the second file's changes land on
# the first file's row numbers.
before = len([c for c in sheet.calls if c["method"] == "GET" and "/values/" in c["path"]])
answered(lambda: record([A_READING]))
after = len([c for c in sheet.calls if c["method"] == "GET" and "/values/" in c["path"]])
check("the sheet is read again for the next file, not remembered from the last one",
      after > before)
check("and reading the same file twice adds no second row",
      len([r for r in sheet.rows if A_SALE.id in str(r)]) == 1)

# **IT REFUSES OUT LOUD.** Swallowed, the file would be written down as read and
# its sales would have reached nothing -- and it would never be read again (D157).
angry = PretendSheets(rows=list(THE_HEADER), missing=True)
check("a sheet that will not answer stops the file, rather than passing quietly",
      refused(lambda: tool.recording_into(LedgerDoor(angry, "s"))([A_READING])) is not None)

heard = []
tool.recording_into(LedgerDoor(PretendSheets(rows=list(THE_HEADER)), "s"), say=heard.append)(
    [A_READING])
check("what was written is said in the run's own words", any("added" in one for one in heard))


# ---- D150 RULE 3, THROUGH THE ONE-FILE-AT-A-TIME HANDOVER THIS FILE OWNS
#
# **THE LOOP BELOW THAT REPORTS A DISAGREEMENT WAS DEAD CODE.** `plan` decides
# rule 3 in a memory that used to be its own, and this calls `plan` once per file
# -- so the memory was empty every time, two files of ONE report and ONE data date
# never met, and the seller's figure was settled silently by whichever Drive id
# sorted higher. His own re-fetch-by-hand case (D110): a day fetched again lands
# as a second file of the same name.
#
# Driven here the way the job runs -- one file, then the other, into a sheet that
# keeps what it was given.
SAME_DAY_ONE = ledger.Reading(report="ms_orders", on="2026-09-01",
                              knows=("platform", "orderId", "on", "sku", "qty", "gmv"),
                              sales=(sales.Sale(platform="meesho", order_id="M-9",
                                                sku="RING-9", qty=9, gmv=499),),
                              which="fetched-first")
SAME_DAY_TWO = ledger.Reading(report="ms_orders", on="2026-09-01",
                              knows=("platform", "orderId", "on", "sku", "qty", "gmv"),
                              sales=(sales.Sale(platform="meesho", order_id="M-9",
                                                sku="RING-9", qty=1, gmv=499),),
                              which="fetched-again")
THE_TIED_SALE = SAME_DAY_ONE.sales[0].id


class KeepsWhatItIsGiven(PretendSheets):
    """`PretendSheets`, plus a row that really changes when it is written to.

    **THE ONE ABOVE ANSWERS A ROW UPDATE WITH `{}` AND CHANGES NOTHING**, which is
    enough for every question about what was CALLED and useless for a question
    about what the seller ends up looking at. Rule 3 is a question about the
    second sort: what stands in the cell after two files have both spoken about
    it. So this one really overwrites the row the plan names -- and a plan built
    against a stale reading names the wrong one, which is the fault it would hide.
    """

    def __call__(self, method, path, query=None, body=None):
        said = super().__call__(method, path, query, body)
        if method == "POST" and "values:batchUpdate" in path:
            for one in (body or {}).get("data", ()):
                # `orders!A7:AS7` -- the row number is the plan's own.
                at = int(one["range"].split("!A")[1].split(":")[0])
                self.rows[at - 1] = list(one["values"][0])
        return said


def a_night_of(two_files):
    """Two files handed over ONE AT A TIME, exactly as the reading hands them."""
    keeping = KeepsWhatItIsGiven(rows=list(THE_HEADER))
    told = []
    into = tool.recording_into(LedgerDoor(keeping, "sheet-1"), say=told.append)
    for one in two_files:
        into([one])
    at_id, at_qty = sales.COLUMNS.index("id"), sales.COLUMNS.index("qty")
    qty = next((r[at_qty] for r in keeping.rows[1:]
                if len(r) > at_qty and r[at_id] == THE_TIED_SALE), None)
    return qty, [line for line in told if "DISAGREEMENT" in line]


qty_one, told_one = a_night_of([SAME_DAY_ONE, SAME_DAY_TWO])
check("TWO FILES OF ONE REPORT AND ONE DATE: WHAT IS IN THE SHEET IS KEPT",
      qty_one == "9")
check("AND THE DISAGREEMENT IS REPORTED, not resolved", len(told_one) == 1)
check("and the report names both files, so somebody can go and look",
      told_one and "fetched-first" in told_one[0] and "fetched-again" in told_one[0])
check("and it names the sale and the column that disagree",
      told_one and THE_TIED_SALE in told_one[0] and "qty" in told_one[0])

qty_two, told_two = a_night_of([SAME_DAY_TWO, SAME_DAY_ONE])
check("handed over the other way round it keeps the OTHER figure",
      qty_two == "1")
check("AND REPORTS IT EITHER WAY -- which is the whole of rule 3",
      len(told_two) == 1)

# **TWO FILES OF DIFFERENT DAYS ARE NOT A TIE.** The newer one wins outright and
# nothing is reported, or every ordinary correction would read as a quarrel.
NEXT_DAY = ledger.Reading(report="ms_orders", on="2026-09-02",
                          knows=("platform", "orderId", "on", "sku", "qty", "gmv"),
                          sales=(sales.Sale(platform="meesho", order_id="M-9",
                                            sku="RING-9", qty=1, gmv=499),),
                          which="the-next-day")
qty_later, told_later = a_night_of([SAME_DAY_ONE, NEXT_DAY])
check("a NEWER file still wins outright, and that is not a disagreement",
      qty_later == "1" and told_later == [])


# ------------------------------------------- D184: what a rebuild cannot put back

check("EVERY column of the ledger has been measured against a rebuild",
      set(tool.WHERE_A_COLUMN_COMES_BACK_FROM) == set(sales.COLUMNS))


def _with_an_unmeasured_column():
    """Add a column to the ledger and ask again what a rebuild loses.

    **A COLUMN NOBODY MEASURED MUST NOT READ AS SAFE.** Left out of the list, it
    would simply not appear in what the seller is told they lose -- which is the
    warning-written-from-imagination D184 forbids. Put back and taken away again,
    so the ledger is exactly as it was afterwards.
    """
    was = sales.COLUMNS
    sales.COLUMNS = was + ("somethingNobodyMeasured",)
    try:
        return tool.what_a_rebuild_cannot_put_back()
    finally:
        sales.COLUMNS = was


check("and a column added tomorrow and never measured refuses rather than reading as safe",
      isinstance(refused(_with_an_unmeasured_column), tool.CannotMakeTheLedger))
check("and the refusal names the column nobody measured",
      "somethingNobodyMeasured" in str(refused(_with_an_unmeasured_column)))
check("and the ledger is left exactly as it was afterwards",
      set(tool.WHERE_A_COLUMN_COMES_BACK_FROM) == set(sales.COLUMNS))

LOST = [column for column, _ in tool.what_a_rebuild_cannot_put_back()]
check("what a rebuild cannot put back is measured, and it is three columns",
      LOST == ["notes", "adSpend", "rev"])
check("every one of the twelve platform charges comes back from the payments report",
      all(tool.WHERE_A_COLUMN_COMES_BACK_FROM[c][0] == tool.FROM_THE_FILES
          for c in sales.CHARGE_COLUMNS))
check("what the seller typed in Kartaan comes back from Kartaan, not from the files",
      all(tool.WHERE_A_COLUMN_COMES_BACK_FROM[c][0] == tool.FROM_KARTAAN
          for c in ("cogs", "earringCondition", "itemLoss", "took")))
check("and profit is named as a snapshot -- today's answer, not the day's (D151)",
      "today" in tool.WHERE_A_COLUMN_COMES_BACK_FROM["netPnl"][1])

WORDS = tool.what_to_tell_them_about_a_deleted_ledger(in_the_bin=True)
check("what a seller is told begins with restoring it, because that loses nothing",
      WORDS.index("RESTORE IT FIRST") < WORDS.index("write the whole history again"))
check("and says the rebuild is theirs to choose, never done on its own",
      "never done on its own" in WORDS)
check("and says the offer stays open for ever", "stays open for ever" in WORDS)
check("and the list of what is lost is the measured one, not a warning somebody imagined",
      all(one in WORDS for one in LOST))
check("and it names the spreadsheet they are looking for", tool.THE_SHEET_IS_CALLED in WORDS)


# ------------------------------------------- the whole writing half, driven
#
# **THIS IS THE PART `start.py` CALLS, AND IT IS HERE SO IT CAN BE DRIVEN.** That
# file needs a real Google account, so anything written in it is a rule nobody
# ever watches fail -- which is precisely how the sales ledger came to be finished
# at both ends and called by nothing.

import between_runs  # noqa: E402


class ADriveFile:
    """The record in the seller's Drive, as bytes that survive being written."""

    def __init__(self, holding=None):
        self.holding = holding
        self.saved = []

    def read(self):
        return self.holding

    def save(self, raw):
        self.saved.append(raw)
        self.holding = raw


# ---- 0. IT REFUSES TO WRITE AT ALL IF D157'S FOUR DATE COLUMNS ARE NOT THERE
#
# **THE REGISTER SAID WRITING WAS NOT SAFE TO LAND UNTIL THOSE COLUMNS EXIST, AND
# `start.py` WIRED THE WRITING IN ANYWAY.** Both could not be true. This is the
# code meeting the record.
#
# **AND ON 2026-09-06 THE COLUMNS LANDED AND THE REFUSAL LIFTED BY ITSELF**, as
# `work.json` said it would -- `sales.COLUMNS` is pinned to the ERP's committed
# list, the ERP added the four, and `what_the_sheet_cannot_yet_say()` went empty
# with nothing here changed to make it.
#
# **SO THESE CHECKS ARE NOW DRIVEN RATHER THAN WAITED FOR.** The four are taken
# away for the length of this block and put straight back. That is the whole
# point of keeping them: **the refusal is not finished business, it is a guard,
# and a guard nobody has watched fire is a guard that could have stopped working
# the day the thing it guards against became possible again.** If the ERP ever
# drops one of the four, this is what stands between that and a sale written into
# a column that is not there.
_the_columns_are_really_there = ledger.what_the_sheet_cannot_yet_say
ledger.what_the_sheet_cannot_yet_say = lambda *a, **k: ledger.WHICH_FILE_LAST_WROTE

no_columns_yet = ADriveFile(holding=None)
never_asked = PretendDrive()
never_made = PretendSheets(rows=[])
refuses, said_why = answered(lambda: tool.the_writing_half(
    never_asked, no_columns_yet.read, no_columns_yet.save, ask=never_made)) or ("threw", "")
check("WHILE THE FOUR DATE COLUMNS DO NOT EXIST THERE IS NOWHERE TO PUT A SALE",
      refuses is None and said_why != "")
check("and the refusal NAMES ALL FOUR of the columns that are missing",
      all(one in said_why for one in ledger.WHICH_FILE_LAST_WROTE))
check("and it says no file has been marked as read",
      "NO FILE HAS BEEN MARKED AS READ" in said_why)
check("and it says the refusal is Kartaan's, not Google's",
      "not Google" in said_why)
check("and it says nothing is lost while it stands",
      "NOTHING IS LOST WHILE THIS STANDS" in said_why)
check("and it says it ends by itself the day those columns land",
      "IT ENDS BY ITSELF" in said_why)
# **NOT ONE CALL TO GOOGLE.** Asked after the ledger was found or made, this would
# leave the seller a spreadsheet Kartaan made and then refused to fill.
check("AND GOOGLE IS NOT TOUCHED AT ALL -- no search, no sheet made",
      not never_asked.asked and not never_made.made_a_spreadsheet())
check("and the record in their Drive is not written to either",
      not no_columns_yet.saved)

# **AND THE SAME REFUSAL IS WHAT `read_what_is_new` ALREADY ANSWERS SAFELY.**
import reading  # noqa: E402

refused_night = answered(lambda: reading.read_what_is_new(
    already_read=("a-file-read-before",),
    what_is_in_the_folder=lambda report_id: (),
    bring_it_back=lambda which: b"", record_the_sales=refuses))
check("WITH THE WRITING REFUSED, NO FILE IS OPENED AND NONE IS MARKED READ",
      refused_night is not None and bool(refused_night.nowhere_to_put_it)
      and refused_night.read_tonight == ())
check("and nothing already written down as read is forgotten either",
      refused_night is not None and refused_night.files_read == ("a-file-read-before",))

# **THE FOUR GO STRAIGHT BACK, and everything below runs against the ledger as it
# really is now.** Until 2026-09-06 the opposite was needed: the refusal was the
# real state and had to be stood down for the rest of this file to run at all.
ledger.what_the_sheet_cannot_yet_say = _the_columns_are_really_there


# ---- AND WITH THOSE COLUMNS THERE, IT WRITES. Driven, not assumed.
#
# **THIS IS NO LONGER A PRETENCE.** It asks the real function, against the real
# column list, with nothing patched -- and it is the check that says the refusal
# has genuinely lifted rather than being switched off for the convenience of the
# file. A refusal nobody has watched lift is a refusal that could be permanent by
# accident; this one has now been watched, both ways, in the same run.
check("with the four columns in the ledger, nothing refuses any more",
      ledger.what_the_sheet_cannot_yet_say() == ()
      and tool.why_it_must_not_write_yet() == "")

# 1. FIRST NIGHT: no record, no ledger. One is made and its address written down.
first_night = ADriveFile(holding=None)
sheets_1 = PretendSheets(rows=[])
plug, why_not = answered(lambda: tool.the_writing_half(
    PretendDrive(), first_night.read, first_night.save, ask=sheets_1)) or (None, "threw")
check("a first night ends with somewhere for a sale to go", callable(plug))
check("and nothing went wrong to report", why_not == "")
check("THE LEDGER'S ADDRESS IS WRITTEN DOWN, and that is the hole this closes",
      answered(lambda: between_runs.read(first_night.holding).ledger_sheet) == "new-sheet-id")
# **BEFORE THE RUN, NOT AFTER.** A night that died in between would otherwise
# leave a ledger nothing remembers, and the next night would make a second one.
check("and it is written down before a single sale is read", len(first_night.saved) == 1)

# 2. SECOND NIGHT: the address is remembered, so Drive is not searched at all.
drive_2 = PretendDrive()
sheets_2 = PretendSheets(rows=list(THE_HEADER))
second_night = ADriveFile(first_night.holding)
plug_2, why_not_2 = answered(lambda: tool.the_writing_half(
    drive_2, second_night.read, second_night.save, ask=sheets_2)) or (None, "threw")
check("the night after, the ledger is the one already written down", callable(plug_2))
check("and Drive is not searched for it again", not drive_2.asked)
check("and no second ledger is made", not sheets_2.made_a_spreadsheet())

# 3. THE ADDRESS IS NOT WRITTEN DOWN AGAIN WHEN IT HAS NOT CHANGED.
kept = ADriveFile(first_night.holding)
answered(lambda: tool.the_writing_half(
    PretendDrive(), kept.read, kept.save, ask=PretendSheets(rows=list(THE_HEADER))))
check("an address that has not changed is not written down a second time", not kept.saved)

# 4. THE LEDGER IS GONE: NO PLACE FOR A SALE, AND THE FETCHING STILL HAPPENS.
gone_night = ADriveFile(first_night.holding)
plug_3, why_not_3 = answered(lambda: tool.the_writing_half(
    PretendDrive(), gone_night.read, gone_night.save,
    ask=PretendSheets(missing=True))) or ("threw", "")
check("a ledger that has gone leaves nowhere for a sale to go", plug_3 is None)
check("and it says why, in the seller's own words, rather than throwing at the job",
      "RESTORE IT FIRST" in why_not_3)
check("and it never makes a new ledger in its place",
      "NOT MADE IN ITS PLACE" in why_not_3)
check("and it does not touch the record either",
      not gone_night.saved)

# **NOWHERE TO PUT A SALE MEANS NO FILE IS MARKED READ.** That is
# `read_what_is_new`'s own rule, and this only has to hand it the `None` that
# turns it on -- a file marked read whose sales reached nothing is lost for ever.
what_happened = answered(lambda: reading.read_what_is_new(
    already_read=(), what_is_in_the_folder=lambda report_id: (),
    bring_it_back=lambda which: b"", record_the_sales=plug_3))
check("WITH NOWHERE TO PUT A SALE, NO FILE IS OPENED AND NONE IS MARKED READ",
      what_happened is not None and what_happened.files_read == ()
      and bool(what_happened.nowhere_to_put_it))

# 5. A DAMAGED RECORD IS NOT READ PAST.
broken = ADriveFile(holding=b"{not a record")
plug_4, why_not_4 = answered(lambda: tool.the_writing_half(
    PretendDrive(), broken.read, broken.save, ask=PretendSheets(rows=[]))) or ("threw", "")
check("a damaged record leaves nowhere for a sale to go rather than starting again",
      plug_4 is None and why_not_4 != "")
check("and no ledger is made on the strength of a record nobody could read",
      not broken.saved)

# **PUT BACK, AND CHECKED THAT IT REALLY IS BACK.** A stand-in left in place would
# make every run of this file after today's silently answer a question nobody
# asked.
# **NOTHING TO PUT BACK ANY MORE.** The four columns are real, so this file no
# longer runs with the refusal switched off -- it takes them away for one block
# near the top and restores them there. Left as a line rather than deleted so
# that anybody looking for the old stand-down finds out where it went.
assert ledger.what_the_sheet_cannot_yet_say is _the_columns_are_really_there
# **AND THE LAST WORD OF THIS FILE IS THAT THE GUARD IS STILL LOADED.** It used
# to say "the refusal is back where it was, and still refuses" -- true until
# 2026-09-06 and false from the moment the ERP landed the four. What is worth
# asserting now is that the real function is what is in place at the end, so no
# check below the top block ever ran against a stood-down refusal.
check("the real column list is what the rest of this file ran against, not a stand-in",
      ledger.what_the_sheet_cannot_yet_say is _the_columns_are_really_there
      and ledger.what_the_sheet_cannot_yet_say() == ())
# **AND EACH OF THE FOUR ON ITS OWN STILL STOPS IT.** Three of four is not good
# enough: a sale written with one marker missing is a row nothing can later tell
# was written by an older file.
def _without(one):
    """What the ledger would refuse if that single column went missing."""
    ledger.what_the_sheet_cannot_yet_say = lambda *a, **k: (one,)
    try:
        return tool.why_it_must_not_write_yet()
    finally:
        ledger.what_the_sheet_cannot_yet_say = _the_columns_are_really_there


check("and taking any ONE of the four away still stops the writing, by name",
      all(_without(one) != "" and one in _without(one)
          for one in ledger.WHICH_FILE_LAST_WROTE))

print()
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 107
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
