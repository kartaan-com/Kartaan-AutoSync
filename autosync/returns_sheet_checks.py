"""Checks for the seller's returns sheet: made ONCE, found every run after, its place written down once (ERP job 77 / piece 34 / D316).

**NOTHING HERE TOUCHES GOOGLE.** Drive, Sheets and the seller's database are stand-ins that RECORD every call, so what is checked is the
request that would really have gone out. The database stand-in is driven through the REAL `firestore_door` sink and reader, so the path
`returns_sheet/sheet` and the two fields are the ones that would really be sent.

**THE ONE THIS FILE EXISTS FOR: A SECOND RUN MAKES NOTHING.** A run that makes a sheet every night leaves him a Drive full of empty sheets.

**AND THE `PROOF:` CHECKS ARE THE HABIT OF THIS REPOSITORY.** Each takes the real source, breaks ONE rule in the text, re-runs the scenario that
guards it, and wants that scenario to go red -- a guard that nothing can turn red is a comment.

Run: python autosync/returns_sheet_checks.py
"""

import os
import re
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import firestore  # noqa: E402
import firestore_door  # noqa: E402
import returns_sheet as real  # noqa: E402
from drive_door import FILES  # noqa: E402
from ledger_door import API as SHEETS  # noqa: E402

ran = 0
failures = []


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


class Reply:
    def __init__(self, body, ok=True, status=200):
        self._body, self.ok, self.status, self.text = body, ok, status, ""

    def json(self):
        return self._body


NO = Reply({}, ok=False, status=404)
KARTAAN = "FOLDER-KARTAAN"
PROJECT = "kartaan-test"


class World:
    """A seller's Drive + Sheets. Every call is recorded; `fail` makes any call whose 'METHOD url' contains the text answer 500."""

    def __init__(self):
        self.files, self.sheets, self.calls, self.fail, self.made = {}, {}, [], [], 0

    def add(self, fid, name="Kartaan returns sheet", parents=("root",), trashed=False, created="2026-01-01T00:00:00Z", rows=None, tabs=None):
        self.files[fid] = {"id": fid, "name": name, "mimeType": "application/vnd.google-apps.spreadsheet", "parents": list(parents),
                           "trashed": trashed, "createdTime": created}
        if not trashed:
            self.sheets[fid] = {t: (rows or {}).get(t) for t in (tabs or ("Receipts", "Log"))}

    def _go(self, method, url, params=None, body=None):
        self.calls.append((method, url, params, body))
        if any(f in f"{method} {url}" for f in self.fail):
            return Reply({}, ok=False, status=500)
        p = params or {}
        if url == FILES and method == "GET":
            q = p["q"]
            name = re.search(r"name = '(.*?)' and", q).group(1)
            bin_ = "trashed = true" in q
            hit = [{k: f[k] for k in ("id", "name", "parents", "createdTime")} for f in self.files.values()
                   if f["name"] == name and f["trashed"] == bin_]
            return Reply({"files": hit})
        if url.startswith(FILES + "/"):
            fid = url.split("/")[-1]
            if method == "GET":
                return Reply({"parents": self.files[fid]["parents"]})
            gone = [x for x in p.get("removeParents", "").split(",") if x]
            self.files[fid]["parents"] = [x for x in self.files[fid]["parents"] if x not in gone] + [p["addParents"]]
            return Reply({"id": fid})
        if url == SHEETS + "/v4/spreadsheets" and method == "POST":
            self.made += 1
            fid = f"SHEET-{self.made}"
            self.add(fid, name=body["properties"]["title"], tabs=[s["properties"]["title"] for s in body["sheets"]])
            return Reply({"spreadsheetId": fid})
        m = re.match(re.escape(SHEETS) + r"/v4/spreadsheets/([^/]+)(.*)", url)
        if m:
            fid, rest = m.groups()
            if fid not in self.sheets:
                return NO
            if rest == "" and method == "GET":
                return Reply({"spreadsheetId": fid, "sheets": [{"properties": {"title": t}} for t in self.sheets[fid]]})
            if rest.startswith("/values/") and rest.endswith(":batchUpdate") is False and method == "GET":
                tab = unquote(rest[len("/values/"):]).split("!")[0]
                row = self.sheets[fid].get(tab)
                return Reply({"values": [row]} if row else {})
            if rest == "/values:batchUpdate" and method == "POST":
                for one in body["data"]:
                    self.sheets[fid][one["range"].split("!")[0]] = list(one["values"][0])
                return Reply({})
        return NO

    # the transport shape Drive and Sheets are asked through
    def get(self, url, params=None):
        return self._go("GET", url, params)

    def post(self, url, params=None, json=None):
        return self._go("POST", url, params, json)

    def patch(self, url, params=None, json=None):
        return self._go("PATCH", url, params, json)


class Db:
    """The seller's database, as the real firestore_door talks to it."""

    def __init__(self):
        self.docs, self.writes, self.fail = {}, 0, False

    def get(self, url, params=None):
        name = url[len(firestore.API) + 1:]
        return Reply({"name": name, "fields": self.docs[name]}) if name in self.docs else NO

    def post(self, url, params=None, json=None):
        if self.fail:
            return Reply({}, ok=False, status=403)
        for w in json["writes"]:
            self.docs[w["update"]["name"]] = w["update"]["fields"]
            self.writes += 1
        return Reply({})


def the_record(db):
    for name, fields in db.docs.items():
        if name.endswith("/returns_sheet/sheet"):
            return firestore.plain(fields)
    return None


class Clock:
    def __init__(self):
        self.t = datetime(2026, 10, 12, 9, 0, 0)

    def __call__(self):
        self.t += timedelta(hours=1)
        return self.t


def run(m, world, db, clock, held=None):
    said = []
    got = m.make_sure_it_exists(
        world, KARTAAN, clock,
        held or firestore_door.a_returns_sheet_held(db, PROJECT),
        firestore_door.a_returns_sheet_sink(db, PROJECT),
        said.append,
    )
    return got, said


def has(said, text):
    return any(text in line for line in said)


HEADER_A = list(real.RECEIPT_COLUMNS) + ["Kartaan id"]
HEADER_B = ["Timestamp", "Event", "Details"]


# ------------------------------------------------------------------ the scenarios, each one a rule. Each takes a module so a PROOF can hand it a broken copy.


def first_run(m):
    w, db, c = World(), Db(), Clock()
    got, said = run(m, w, db, c)
    rec = the_record(db)
    return {
        "made one sheet": w.made == 1 and got == "SHEET-1",
        "exactly the two tabs, in order": list(w.sheets["SHEET-1"]) == ["Receipts", "Log"],
        "Receipts row 1 is A-K exactly": w.sheets["SHEET-1"]["Receipts"] == HEADER_A and len(HEADER_A) == 11,
        "Log row 1 is the three columns": w.sheets["SHEET-1"]["Log"] == HEADER_B,
        "it sits in the Kartaan folder": w.files["SHEET-1"]["parents"] == [KARTAAN],
        "one record, exactly sheetId and createdAt": rec is not None and set(rec) == {"sheetId", "createdAt"} and db.writes == 1,
        "the record names the sheet and the creation time in his clock": rec is not None and rec["sheetId"] == "SHEET-1" and rec["createdAt"] == "2026-10-12T10:00:00",
        "the record is at returns_sheet/sheet": any(n.endswith("/documents/returns_sheet/sheet") for n in db.docs),
        "creating call carries both tabs and no Sheet1": [s["properties"]["title"] for s in w.calls[[i for i, x in enumerate(w.calls) if x[0] == "POST" and x[1].endswith("/v4/spreadsheets")][0]][3]["sheets"]] == ["Receipts", "Log"],
    }, (w, db, c)


def second_run(m):
    _, (w, db, c) = first_run(m)
    before_calls, before_writes, before_made = len(w.calls), db.writes, w.made
    rec_before = dict(the_record(db))
    rows_before = {t: list(r) for t, r in w.sheets["SHEET-1"].items()}
    got, said = run(m, w, db, c)
    after = w.calls[before_calls:]
    return {
        "second run makes no sheet": w.made == before_made and got == "SHEET-1" and not any(x[0] == "POST" and x[1].endswith("/v4/spreadsheets") for x in after),
        "second run writes no record": db.writes == before_writes,
        "createdAt is not rewritten": the_record(db) == rec_before,
        "second run writes nothing at all to Drive or Sheets": all(x[0] == "GET" for x in after),
        "the sheet's rows are untouched": w.sheets["SHEET-1"] == rows_before,
    }


def id_gone_found_by_name(m):
    w, db, c = World(), Db(), Clock()
    w.add("REAL", parents=(KARTAAN,), rows={"Receipts": HEADER_A, "Log": HEADER_B})
    db.docs[firestore.where_a_document_lives(PROJECT, "returns_sheet", "sheet")] = firestore.fields_of({"sheetId": "DEAD", "createdAt": "2026-09-01T00:00:00"})
    got, said = run(m, w, db, c)
    return {
        "found by name when the remembered id is gone": got == "REAL" and w.made == 0,
        "the record now names the sheet found": the_record(db)["sheetId"] == "REAL",
        "it said so": has(said, "did not answer") and has(said, "by name"),
    }


def remembered_but_renamed(m):
    w, db, c = World(), Db(), Clock()
    w.add("KEPT", name="Something he renamed it to", parents=(KARTAAN,), rows={"Receipts": HEADER_A, "Log": HEADER_B})
    db.docs[firestore.where_a_document_lives(PROJECT, "returns_sheet", "sheet")] = firestore.fields_of({"sheetId": "KEPT", "createdAt": "2026-09-01T00:00:00"})
    got, said = run(m, w, db, c)
    return {"a remembered id that still answers is used, renamed or not, and nothing is made": got == "KEPT" and w.made == 0 and db.writes == 0}


def two_of_the_name(m):
    out = {}
    picks = []
    for order in ("old-first", "new-first"):
        w, db, c = World(), Db(), Clock()
        w.add("TOP", parents=("root",), created="2026-01-01T00:00:00Z", rows={"Receipts": HEADER_A, "Log": HEADER_B})
        w.add("INSIDE", parents=(KARTAAN,), created="2026-05-01T00:00:00Z", rows={"Receipts": HEADER_A, "Log": HEADER_B})
        if order == "new-first":
            w.files = dict(reversed(list(w.files.items())))
        got, said = run(m, w, db, c)
        picks.append(got)
        out[f"two of the name ({order}): none made"] = w.made == 0
        out[f"two of the name ({order}): said in words"] = has(said, "2 spreadsheets")
    out["two of the name: the same one both ways (the one inside Kartaan)"] = picks == ["INSIDE", "INSIDE"]
    return out


def edited_header(m):
    _, (w, db, c) = first_run(m)
    w.sheets["SHEET-1"]["Receipts"][3] = "Order number"
    w.sheets["SHEET-1"]["Log"] = list(HEADER_B)
    edited = list(w.sheets["SHEET-1"]["Receipts"])
    n = len(w.calls)
    got, said = run(m, w, db, c)
    return {
        "an edited header is left exactly as it is": w.sheets["SHEET-1"]["Receipts"] == edited and got == "SHEET-1",
        "an edited header is said": has(said, "HEADER CHANGED") and has(said, "Receipts"),
        "nothing was written to Sheets": all(x[0] == "GET" for x in w.calls[n:]),
        "no second sheet": w.made == 1,
    }


def empty_header_filled(m):
    w, db, c = World(), Db(), Clock()
    w.add("HALF", parents=(KARTAAN,))
    got, said = run(m, w, db, c)
    return {"a sheet made by a run that died is finished, not remade": w.made == 0 and w.sheets["HALF"]["Receipts"] == HEADER_A and w.sheets["HALF"]["Log"] == HEADER_B}


def a_failure_is_not_fatal(m):
    out = {}
    w, db, c = World(), Db(), Clock()
    w.fail = ["POST " + SHEETS + "/v4/spreadsheets"]
    try:
        got, said = run(m, w, db, c)
        out["Google refusing the create: said, returns, does not raise"] = got == "" and has(said, "NOT READY")
    except Exception:  # noqa: BLE001
        out["Google refusing the create: said, returns, does not raise"] = False
    w, db, c = World(), Db(), Clock()
    db.fail = True
    try:
        got, said = run(m, w, db, c)
        out["the database refusing the record: sheet still made, said"] = got == "SHEET-1" and has(said, "RECORD NOT WRITTEN") and w.sheets["SHEET-1"]["Receipts"] == HEADER_A
    except Exception:  # noqa: BLE001
        out["the database refusing the record: sheet still made, said"] = False
    w, db, c = World(), Db(), Clock()

    def boom():
        raise RuntimeError("database down")

    try:
        got, said = run(m, w, db, c, held=boom)
        out["an unreadable record and nothing found by name: REFUSED, said, no sheet made, nothing written"] = (
            w.made == 0 and got == "" and has(said, "could not be read") and has(said, "NOT READY") and db.writes == 0)
    except Exception:  # noqa: BLE001
        out["an unreadable record and nothing found by name: REFUSED, said, no sheet made, nothing written"] = False
    w, db, c = World(), Db(), Clock()
    w.add("FOUND", parents=(KARTAAN,), rows={"Receipts": HEADER_A, "Log": HEADER_B})
    try:
        got, said = run(m, w, db, c, held=boom)
        out["an unreadable record with the sheet found by name: nothing written to the database"] = got == "FOUND" and db.writes == 0
    except Exception:  # noqa: BLE001
        out["an unreadable record with the sheet found by name: nothing written to the database"] = False
    return out


def never_over_a_deleted_one(m):
    out = {}
    w, db, c = World(), Db(), Clock()
    w.add("BINNED", trashed=True)
    got, said = run(m, w, db, c)
    out["a sheet in his rubbish bin: none made, said"] = w.made == 0 and got == "" and has(said, "rubbish bin")
    w, db, c = World(), Db(), Clock()
    db.docs[firestore.where_a_document_lives(PROJECT, "returns_sheet", "sheet")] = firestore.fields_of({"sheetId": "LOST", "createdAt": "2026-09-01T00:00:00"})
    got, said = run(m, w, db, c)
    out["a remembered sheet that is nowhere: none made, said"] = w.made == 0 and got == "" and has(said, "NOT been made")
    return out


SCENARIOS = {
    "first run": lambda m: first_run(m)[0],
    "second run": second_run,
    "id gone": id_gone_found_by_name,
    "renamed": remembered_but_renamed,
    "two of the name": two_of_the_name,
    "edited header": edited_header,
    "empty header": empty_header_filled,
    "failure": a_failure_is_not_fatal,
    "never over a deleted one": never_over_a_deleted_one,
}

for scenario_name, scenario in SCENARIOS.items():
    for what, ok in scenario(real).items():
        check(f"{scenario_name}: {what}", ok)

# ------------------------------------------------------- the headers against the ERP's own file, when it is on this machine


def the_erp_file():
    named = [os.environ.get("KARTAAN_ERP_RETURN_SCAN", "")]
    if os.environ.get("KARTAAN"):
        named.append(str(Path(os.environ["KARTAAN"]) / "src/shared/definitions/return-scan.js"))
    named.append(r"D:\Kartaan-ERP\.claude\worktrees\interesting-mclean-1c64ce\src\shared\definitions\return-scan.js")
    named.append(r"D:\Kartaan-ERP\src\shared\definitions\return-scan.js")
    return next((p for p in named if p and Path(p).is_file()), None)


def strings_of(source, constant):
    found = re.search(r"export const " + constant + r"\s*=\s*(\[.*?\]|'.*?');", source, re.S)
    return re.findall(r"'([^']*)'", found.group(1)) if found else None


erp = the_erp_file()
if erp is not None and strings_of(Path(erp).read_text(encoding="utf-8"), "LOG_COLUMNS") is None:
    print(f"SKIP  {erp} does not carry the receipt/log column lists (an ERP checkout from before E87); set KARTAAN_ERP_RETURN_SCAN")
    erp = None
if erp is None:
    print("SKIP  the headers were NOT compared with the ERP's return-scan.js: that file is not on this machine (set KARTAAN or KARTAAN_ERP_RETURN_SCAN)")
    check("headers vs the ERP file: Receipts SKIPPED (said above)", True)
    check("headers vs the ERP file: Log SKIPPED (said above)", True)
else:
    js = Path(erp).read_text(encoding="utf-8")
    check("headers vs the ERP file: Receipts is RECEIPT_COLUMNS then Kartaan id",
          list(dict(real.THE_TABS)["Receipts"]) == strings_of(js, "RECEIPT_COLUMNS") + strings_of(js, "KARTAAN_ID_COLUMN"))
    check("headers vs the ERP file: Log is LOG_COLUMNS", list(dict(real.THE_TABS)["Log"]) == strings_of(js, "LOG_COLUMNS"))
    print(f"      (compared with {erp})")

check("the tab names are exactly Receipts and Log", [t for t, _ in real.THE_TABS] == ["Receipts", "Log"] and real.THE_SHEET_IS_CALLED == "Kartaan returns sheet")
check("the database lock allows returns_sheet/sheet and the record is replaced whole",
      firestore.RETURNS_SHEET in firestore.WHAT_IT_MAY_WRITE
      and "updateMask" not in firestore.one_write(PROJECT, "returns_sheet", "sheet", {"sheetId": "x", "createdAt": "y"})["update"]
      and firestore.a_returns_sheet_record("x", datetime(2026, 1, 2, 3, 4, 5)) == ("sheet", {"sheetId": "x", "createdAt": "2026-01-02T03:04:05"}))
refused = []
for bad in (("", datetime(2026, 1, 1)), ("x", None)):
    try:
        firestore.a_returns_sheet_record(*bad)
    except firestore.Refused:
        refused.append(True)
check("a record with no sheet or no moment is refused", refused == [True, True])

# -------------------------------------------------------------------------------- PROOF: break one rule in the source, the named check must go red


def mutant(old, new):
    """The real module's source with ONE rule broken in the text, loaded as its own module."""
    source = (HERE / "returns_sheet.py").read_text(encoding="utf-8")
    assert old in source, f"the text this proof breaks is no longer in returns_sheet.py: {old!r}"
    module = types.ModuleType("returns_sheet_broken")
    module.__file__ = str(HERE / "returns_sheet.py")
    exec(compile(source.replace(old, new, 1), "returns_sheet_broken", "exec"), module.__dict__)  # noqa: S102
    return module


def goes_red(old, new, scenario, which):
    broken = SCENARIOS[scenario](mutant(old, new))
    return real_ok(scenario, which) and not broken[which]


def real_ok(scenario, which):
    return SCENARIOS[scenario](real)[which]


check("PROOF: a run that rewrites the record every time (createdAt moves) is caught",
      goes_red("elif knows and remembered != which:", "elif knows:", "second run", "second run writes no record"))
check("PROOF: a run that ignores the remembered id and makes a sheet instead is caught",
      goes_red("    if remembered:\n        try:\n            tabs", "    if False:\n        try:\n            tabs", "renamed",
               "a remembered id that still answers is used, renamed or not, and nothing is made"))
check("PROOF: a run that never looks by name (so makes a second sheet) is caught",
      goes_red("        if found:\n            chosen", "        if False:\n            chosen", "id gone", "found by name when the remembered id is gone"))
check("PROOF: a choice between two sheets that depends on listing order is caught",
      goes_red("key=lambda one: (inside not in (one.get(\"parents\") or []), str(one.get(\"createdTime\") or \"\"), str(one.get(\"id\") or \"\")),",
               "key=lambda one: 0,", "two of the name", "two of the name: the same one both ways (the one inside Kartaan)"))
check("PROOF: a run that makes a sheet when the record could not be read and nothing is found by name is caught",
      goes_red("        elif not knows:", "        elif False:", "failure",
               "an unreadable record and nothing found by name: REFUSED, said, no sheet made, nothing written"))
check("PROOF: a run that makes a new sheet over one in the rubbish bin is caught",
      goes_red("elif remembered or _by_name(transport, THE_SHEET_IS_CALLED, trashed=True):", "elif False:", "never over a deleted one",
               "a sheet in his rubbish bin: none made, said"))
check("PROOF: a run that makes a new sheet when the remembered one is nowhere is caught",
      goes_red("elif remembered or _by_name(transport, THE_SHEET_IS_CALLED, trashed=True):", "elif _by_name(transport, THE_SHEET_IS_CALLED, trashed=True):",
               "never over a deleted one", "a remembered sheet that is nowhere: none made, said"))
check("PROOF: a header that is overwritten whatever it says is caught",
      goes_red("if not any(c.strip() for c in row):", "if True:", "edited header", "an edited header is left exactly as it is"))
check("PROOF: a changed header that is not said is caught",
      goes_red('say(\n                f"RETURNS SHEET HEADER CHANGED', 'print(\n                f"RETURNS SHEET HEADER CHANGED', "edited header", "an edited header is said"))
check("PROOF: a stray Sheet1 beside the two tabs is caught",
      goes_red("for tab, header in THE_TABS\n        ],", 'for tab, header in THE_TABS\n        ] + [{"properties": {"title": "Sheet1"}}],', "first run", "exactly the two tabs, in order"))
check("PROOF: a failure that is allowed to stop the run is caught",
      goes_red("    except Exception as wrong:  # noqa: BLE001 - said in words, never raised: the fetching must go on", "    except ZeroDivisionError as wrong:",
               "failure", "Google refusing the create: said, returns, does not raise"))
check("PROOF: a record failure that stops the run is caught",
      goes_red("    except Exception as wrong:  # noqa: BLE001 - the sheet is there; the pointer to it is tried again next run", "    except ZeroDivisionError as wrong:",
               "failure", "the database refusing the record: sheet still made, said"))
check("PROOF: an unreadable record taken for 'no record' is caught",
      goes_red("        knows = False\n", "        knows = True\n", "failure",
               "an unreadable record with the sheet found by name: nothing written to the database"))
check("PROOF: a sheet that is not put in the Kartaan folder is caught",
      goes_red("        if inside:\n            try:\n                move_the_file(transport, which, inside)\n                speak(\"RETURNS SHEET  it was put inside the Kartaan folder.\")",
               "        if False:\n            try:\n                move_the_file(transport, which, inside)\n                speak(\"RETURNS SHEET  it was put inside the Kartaan folder.\")",
               "first run", "it sits in the Kartaan folder"))
check("PROOF: an empty header that is not filled in is caught",
      goes_red("            to_fill.append((tab, header))", "            pass", "empty header",
               "a sheet made by a run that died is finished, not remade"))

EXPECTED = 54
if ran != EXPECTED:
    print(f"FAIL  checks went missing or were added -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
