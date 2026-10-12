"""The seller's returns sheet: made ONCE, found again every run after, and its place written down once (ERP job 77 / piece 34 / D316).

**WHAT IT IS.** A Google Sheet called `Kartaan returns sheet` in his `Kartaan` folder, beside `Kartaan sales ledger`. It has exactly
two tabs and nothing else: `Receipts` (what the person at the packing table scans when a parcel comes back) and `Log`. The ERP
writes into it; **this file only makes it, finds it, and tells the ERP where it is** with one record, `returns_sheet/sheet`
= `{sheetId, createdAt}`.

**THE COLUMN NAMES ARE THE ERP'S, COPIED AND NOT INVENTED.** They are `RECEIPT_COLUMNS`, `KARTAAN_ID_COLUMN` and `LOG_COLUMNS` in the
ERP's `src/shared/definitions/return-scan.js`. He raises courier and platform claims off the Receipts tab, so a column that moves is
a claim that cannot be found. `returns_sheet_checks.py` compares these to that file whenever it is on this machine.

---

**A SECOND SHEET IS THE ONE FAULT THIS FILE EXISTS TO PREVENT**, because returns would then be written to one sheet by the ERP and
read from another by him, in silence. So the order is fixed, and each step is there for a failure that has a name:

1. **THE REMEMBERED ID FIRST.** The record `returns_sheet/sheet` is the memory (it is what the ERP reads too, so there is no second place
   to keep an id). If Google still answers for that id, that is the sheet. Nothing else is looked at, nothing is made, nothing is written.
2. **THEN BY NAME.** The id may have been lost (record deleted, a run that died between making the sheet and writing the record). The
   Drive search is for the NAME, anywhere this app can see (under `drive.file` that is only files this app made, so a sheet he made by hand
   can never be adopted). Preferring the copy inside `Kartaan`, then the oldest, then the lowest id -- **the same choice every run**, said in words.
3. **THEN THE RUBBISH BIN.** A sheet that is in his bin, or that was remembered and is nowhere, is **not** answered by making a new one:
   it is said, and left for him (the same refusal the sales ledger gives, D184).
4. **ONLY THEN MADE** -- with both tabs in the one creating call, so there is never a stray `Sheet1`, and never a moment in which Kartaan
   has made a sheet it cannot write to.

**IT NEVER TOUCHES WHAT HE HAS.** A header row that has been changed is said and left exactly as it is; a tab that is missing is said
and not added. Only a header row that is EMPTY is filled in -- that is a sheet made by a run that died before it finished.

**AND NOTHING HERE CAN STOP THE RUN.** `make_sure_it_exists` catches everything and says it; returns of a customer's parcel are not
worth failing a night of fetching for.

**NOTHING HERE OPENS A CONNECTION.** Google and the database are handed in, so every line is checked with no account and no internet.
"""

from typing import Callable, Dict, List, Optional
from urllib.parse import quote

from drive_door import DriveSaidNo, _every_file, as_a_quoted_value, move_the_file
from ledger_sheet import SPREADSHEET, a_way_to_ask

THE_SHEET_IS_CALLED = "Kartaan returns sheet"
THE_RECEIPTS_TAB = "Receipts"
THE_LOG_TAB = "Log"

# **COPIED EXACTLY FROM THE ERP'S `return-scan.js` (RECEIPT_COLUMNS, KARTAAN_ID_COLUMN, LOG_COLUMNS).** A to J are his; `Kartaan id` is
# the one column Kartaan adds, at the end (K). `returns_sheet_checks.py` holds these against that file.
RECEIPT_COLUMNS = (
    "Scan Date/Time", "Platform", "Courier Partner", "Order ID", "AWB", "Return Type",
    "Earring Intact", "Box Intact", "Packet QR", "Chain Intact",
)
KARTAAN_ID_COLUMN = "Kartaan id"
LOG_COLUMNS = ("Timestamp", "Event", "Details")

# **THE TWO TABS AND THEIR ROW 1, IN ORDER, AND THE ONLY PLACE THEY ARE LISTED.** Creating, checking and filling all walk this, so they cannot drift.
THE_TABS = (
    (THE_RECEIPTS_TAB, RECEIPT_COLUMNS + (KARTAAN_ID_COLUMN,)),
    (THE_LOG_TAB, LOG_COLUMNS),
)


class CannotUseTheReturnsSheet(RuntimeError):
    """The returns sheet could not be found, made or trusted, and it says why. Always said, never raised past `make_sure_it_exists`."""


def the_creating_call() -> Dict:
    """The body that makes the sheet: both tabs named, sized to their headers and with row 1 kept on screen. **Built from `THE_TABS`, never typed.**"""
    return {
        "properties": {"title": THE_SHEET_IS_CALLED},
        "sheets": [
            {"properties": {"title": tab, "gridProperties": {"columnCount": len(header), "frozenRowCount": 1}}}
            for tab, header in THE_TABS
        ],
    }


def _row_one(tab: str) -> str:
    return quote(f"{tab}!1:1", safe="")


def the_tabs_it_has(ask: Callable, which: str) -> List[str]:
    """The tab names of that spreadsheet. **Also the question 'does Google still answer for this id'.**"""
    said = ask("GET", f"/v4/spreadsheets/{which}", query={"fields": "spreadsheetId,sheets.properties.title"})
    if not isinstance(said, dict) or not str(said.get("spreadsheetId") or "").strip():
        raise CannotUseTheReturnsSheet("Google did not say which spreadsheet that is.")
    return [str(((one or {}).get("properties") or {}).get("title") or "") for one in said.get("sheets") or []]


def _by_name(transport, name: str, trashed: bool) -> List[Dict]:
    """Every spreadsheet of this name the app can see, through the repository's one pager (which reads every page and refuses an incomplete search)."""
    looking = (
        f"name = '{as_a_quoted_value(name)}' and mimeType = '{SPREADSHEET}' "
        f"and trashed = {'true' if trashed else 'false'}"
    )
    return _every_file(transport, looking, "id,name,parents,createdTime", f"looking for the {name} spreadsheet")


def which_one_of_several(found: List[Dict], inside: str) -> Dict:
    """**THE SAME ANSWER EVERY RUN.** The one inside `Kartaan`, else the oldest, else the lowest id."""
    return sorted(
        found,
        key=lambda one: (inside not in (one.get("parents") or []), str(one.get("createdTime") or ""), str(one.get("id") or "")),
    )[0]


def _first_difference(row: List[str], header) -> int:
    """Which column first disagrees, counting from 1."""
    for at, (was, should) in enumerate(zip(row, header), start=1):
        if was != should:
            return at
    return min(len(row), len(header)) + 1


def _the_headers(ask: Callable, which: str, tabs: List[str], say: Callable[[str], None]) -> None:
    """Row 1 of each tab: empty is filled, exact is left, anything else is SAID and left alone. **Not one existing cell is ever written over.**"""
    to_fill = []
    for tab, header in THE_TABS:
        if tab not in tabs:
            say(f"RETURNS SHEET TAB MISSING  the {THE_SHEET_IS_CALLED} has no tab called {tab}. Nothing was added; it is left as it is.")
            continue
        said = ask("GET", f"/v4/spreadsheets/{which}/values/{_row_one(tab)}")
        values = (said or {}).get("values") if isinstance(said, dict) else None
        row = [str(c) for c in (values[0] if values else [])]
        if not any(c.strip() for c in row):
            to_fill.append((tab, header))
        elif row != list(header):
            say(
                f"RETURNS SHEET HEADER CHANGED  row 1 of the {tab} tab is not the column names Kartaan made (it has {len(row)} columns "
                f"where there were {len(header)}; the first that differs is column {_first_difference(row, header)}). It has been left exactly as it is; nothing was written to it."
            )
    if to_fill:
        end = lambda n: chr(ord("A") + n - 1)  # noqa: E731 - the widest header is eleven, so A..K
        ask(
            "POST",
            f"/v4/spreadsheets/{which}/values:batchUpdate",
            body={
                "valueInputOption": "RAW",
                "data": [{"range": f"{tab}!A1:{end(len(header))}1", "majorDimension": "ROWS", "values": [list(header)]} for tab, header in to_fill],
            },
        )
        say("RETURNS SHEET  the column names were put on row 1 of: " + ", ".join(tab for tab, _ in to_fill) + ".")


def make_sure_it_exists(
    transport,
    inside: str,
    now: Callable,
    held: Callable[[], Optional[str]],
    write_record: Callable[..., None],
    say: Optional[Callable[[str], None]] = None,
    ask: Optional[Callable] = None,
) -> str:
    """The returns sheet's id (made if it never existed), or "" when it could not be had. **NEVER RAISES -- a fault is said and the run goes on.**

    `held()` is the sheet id the database record holds (None if there is no record); `write_record(sheet_id, created_at)` writes the record
    whole. Both are handed in so they can be checked with a stand-in database.
    """
    speak = say if callable(say) else (lambda line: None)
    try:
        return _make_sure(transport, inside, now, held, write_record, speak, ask if callable(ask) else a_way_to_ask(transport))
    except Exception as wrong:  # noqa: BLE001 - said in words, never raised: the fetching must go on
        speak(f"RETURNS SHEET NOT READY  {type(wrong).__name__}: {wrong}"[:600])
        return ""


def _make_sure(transport, inside, now, held, write_record, speak, asking) -> str:
    # **THE RECORD IS THE MEMORY.** A database that will not answer is NOT 'no record': that reading would write a fresh `createdAt` over a true one.
    knows = True
    remembered = ""
    try:
        remembered = str(held() or "").strip()
    except Exception as wrong:  # noqa: BLE001
        knows = False
        speak(f"RETURNS SHEET  the record of where it is could not be read ({type(wrong).__name__}: {wrong}), so it is looked for by name and the record is not touched."[:600])

    which, tabs, made = "", [], False
    if remembered:
        try:
            tabs = the_tabs_it_has(asking, remembered)
            which = remembered
        except (DriveSaidNo, CannotUseTheReturnsSheet) as wrong:
            speak(f"RETURNS SHEET  the sheet the record points at did not answer ({wrong}), so it is looked for by name."[:600])

    if not which:
        found = _by_name(transport, THE_SHEET_IS_CALLED, trashed=False)
        if found:
            chosen = which_one_of_several(found, inside)
            which = str(chosen["id"])
            if len(found) > 1:
                speak(
                    f"RETURNS SHEET  there are {len(found)} spreadsheets called {THE_SHEET_IS_CALLED} that Kartaan made. "
                    f"{which} is used (the one inside the Kartaan folder, else the oldest, else the lowest id) and none was made or touched."
                )
            else:
                speak("RETURNS SHEET  found in his Drive by name.")
            if inside and inside not in (chosen.get("parents") or []):
                try:
                    move_the_file(transport, which, inside)
                    speak("RETURNS SHEET  it was put inside the Kartaan folder.")
                except DriveSaidNo as wrong:
                    speak(f"RETURNS SHEET  it could not be put inside the Kartaan folder yet: {wrong}"[:400])
            tabs = the_tabs_it_has(asking, which)
        elif remembered or _by_name(transport, THE_SHEET_IS_CALLED, trashed=True):
            # **NEVER A SECOND ONE (the ledger's D184, same reason).** Made over a deleted sheet, returns he already scanned would be 'lost' in silence.
            raise CannotUseTheReturnsSheet(
                f"The {THE_SHEET_IS_CALLED} was made before and cannot be found now"
                + (" (it is in the rubbish bin of his Drive: restore it)." if not remembered else " (it may have been deleted or moved out of reach).")
                + " A new one has NOT been made in its place. Restore it, or tell Kartaan to make a new one."
            )
        elif not knows:
            # **A RECORD THAT COULD NOT BE READ IS NOT A FIRST RUN.** Only a cleanly read 'no record' (with nothing by name, nothing in the bin) makes one.
            raise CannotUseTheReturnsSheet(
                "The record of where the returns sheet is could not be read, and no sheet by that name was found, so none was made "
                "(it might already exist). It is tried again next run."
            )
        else:
            made = True

    if made:
        said = asking("POST", "/v4/spreadsheets", body=the_creating_call())
        which = str((said or {}).get("spreadsheetId") or "").strip() if isinstance(said, dict) else ""
        if not which:
            raise CannotUseTheReturnsSheet("Google was asked to make the returns sheet and did not say which spreadsheet it made.")
        speak("RETURNS SHEET  did not exist and has been made in his Drive with the tabs Receipts and Log.")
        # **THE RECORD GOES DOWN BEFORE ANYTHING ELSE CAN FAIL.** The id is the one thing a run that dies after this must not lose.
        _the_record(write_record, which, now, speak)
        if inside:
            try:
                move_the_file(transport, which, inside)
                speak("RETURNS SHEET  it was put inside the Kartaan folder.")
            except DriveSaidNo as wrong:
                speak(f"RETURNS SHEET  it could not be put inside the Kartaan folder yet: {wrong}"[:400])
        tabs = [tab for tab, _ in THE_TABS]
    elif knows and remembered != which:
        # Found by name, and the record was missing or named another sheet: say where it is now. A record already right is NOT rewritten (keeps `createdAt`).
        _the_record(write_record, which, now, speak)

    try:
        _the_headers(asking, which, tabs, speak)
    except Exception as wrong:  # noqa: BLE001 - the sheet exists and is recorded; the header is the next run's to finish
        speak(f"RETURNS SHEET HEADER NOT CHECKED  {type(wrong).__name__}: {wrong}"[:600])
    return which


def _the_record(write_record: Callable[..., None], which: str, now: Callable, speak: Callable[[str], None]) -> None:
    try:
        write_record(which, now())
        speak("RETURNS SHEET  its place was written down for the ERP.")
    except Exception as wrong:  # noqa: BLE001 - the sheet is there; the pointer to it is tried again next run
        speak(f"RETURNS SHEET RECORD NOT WRITTEN  the sheet exists but where it is could not be saved ({type(wrong).__name__}: {wrong})"[:600])
