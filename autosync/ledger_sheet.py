"""The seller's sales ledger: making it, finding it again, and writing into it.

**THIS IS THE MIDDLE THAT WAS MISSING, and it had been missing in silence.** For
two days every report said *"the sheet door is built"*, and that was true and
misleading: `ledger_door.py`, the ERP's `sheetLedger` and its `google-ask.js`
were all finished, checked and called by nobody, **nothing anywhere created the
spreadsheet, and nothing anywhere supplied its id.** So `ledger.plan` could work
out a hundred and twenty-one real sales and there was nowhere to put one. This
file is the join, and it is deliberately the smallest thing that closes it.

---

**THREE HOLES, AND THIS CLOSES ALL THREE:**

| | |
|---|---|
| Nothing MADE it | `make_the_ledger` -- one Sheets call that names the tab and sizes the grid |
| Nothing REMEMBERED it | the id goes in the record in the seller's own Drive, beside everything else a run hands the next (D100) |
| Nothing USED the door | `recording_into` is the `record_the_sales` that `reading.read_what_is_new` has always taken and has never been given |

---

**IT IS THE SELLER'S OWN GOOGLE PERMISSION, AND THE SAME ONE THAT WRITES.**

`drive.file` reaches *"only the specific Google Drive files you use with this
app"* (D137). That makes one thing load-bearing rather than incidental: **whoever
creates the sheet must be the identity that later writes to it.** So the sheet is
made with the very `Google` connection the nightly run already holds -- the
seller's own refresh token, the seller's own Drive -- and not by Kartaan's
account and not by a second connection built here. **There is no way for the
creating identity and the writing identity to differ, because there is only one
object and it is handed in.**

**AND THAT IS WHY LOOKING BY NAME IS SAFE.** Under `drive.file`, a Drive listing
returns only files this app created, so a spreadsheet the SELLER made by hand can
never be found by the search below and can never be adopted. A duplicate name in
their Drive is therefore possible and is a fact to tell them, not a fault to fix
here.

---

**WHAT IS OPEN, AND WHERE IT WOULD BITE.** Whether the ERP page, the server and
this nightly job are ONE Google application is not decided by anybody: the page
has no Google sign-in for sheets at all (`initTokenClient` appears only inside a
comment). **Nothing in this file depends on that answer** -- the run creates the
sheet, remembers the sheet and writes the sheet, all with one identity. If the
answer comes back "two applications", what breaks is not where the id is kept: it
is that the page cannot open the sheet AT ALL, because `drive.file` is granted
per application. **Where the id lives is the smaller half of that problem, and
moving it is one function.**

---

**A NIGHT THAT CANNOT WRITE STOPS AND SAYS SO.** Two runs in this repository have
already "succeeded" in eleven seconds while doing nothing. Everything here
refuses in words rather than returning something empty, and **a sheet that was
once remembered and is now gone is the loudest refusal of the lot: it NEVER makes
a second one** (D184).

**NOTHING HERE OPENS A CONNECTION.** The transport is handed in, exactly as it is
for Drive, Amazon and Firestore, so every line below is checked with no account,
no sheet and no internet.
"""

from typing import Callable, Dict, Optional, Sequence, Tuple

import ledger
import sales
# **THE LISTING IS BORROWED, NEVER REWRITTEN.** `_every_file` is the one pager in
# this repository: it reads every page, asks Drive for `nextPageToken` by name,
# and refuses an incomplete search instead of believing it. Writing a second
# listing here would be a second set of those guards to keep right, and the fault
# it would hide is the worst one available -- a short listing reads as "there is
# no ledger", and "there is no ledger" is what makes a new one.
from drive_door import DriveSaidNo, _every_file
from ledger_door import API as SHEETS
from ledger_door import LedgerDoor

# What the spreadsheet is called in the seller's own Drive.
#
# **ONE NAME, WRITTEN ONCE.** It is what the search below looks for and what the
# creating call sets, so the two cannot drift apart into a job that makes a new
# sheet every night because it looks for a name it does not use.
THE_SHEET_IS_CALLED = "Kartaan sales ledger"

# What Google calls a spreadsheet. Read off Drive's own documentation rather than
# typed from memory: a near-miss here matches nothing, and matching nothing reads
# exactly like "there is no ledger yet" -- which is what makes a second one.
SPREADSHEET = "application/vnd.google-apps.spreadsheet"

# **HOW WIDE THE GRID IS MADE, AND IT IS NOT DECORATION.** A new Google
# spreadsheet is twenty-six columns wide and this ledger has more than that. Every
# write in `ledger_door` addresses `orders!A:AW`, and a range wider than the grid
# is refused by Sheets with *"exceeds grid limits"* -- so a sheet created without
# this line would be made successfully, would look perfectly right, and would
# refuse the first sale ever written into it.
#
# **WORKED OUT, NEVER TYPED.** The day a column is added, the grid grows with it.
HOW_MANY_COLUMNS = len(sales.COLUMNS)

# The header stays on screen when the seller scrolls. The whole reason this sheet
# exists is that a person can read one row and understand an order (D152), and a
# row of forty-five figures with the column names scrolled off the top is not
# readable by anybody.
THE_HEADER_STAYS_PUT = 1


class TheLedgerIsGone(RuntimeError):
    """The sheet this seller's ledger lives in was remembered and is not there.

    **ITS OWN KIND, and the reason is D184.** Every other failure here is
    something to run again or something to fix. This one is a decision that
    belongs to the seller: restore it from their own Drive rubbish bin, or ask for
    the history to be written again. **A run must never answer this by making a
    second sheet** -- a ledger that silently reappears with a different history in
    it is worse than no ledger, because nobody can tell which one they are
    reading.
    """


class CannotMakeTheLedger(RuntimeError):
    """The ledger could not be made or could not be trusted, and it says why.

    **ITS OWN KIND**, so "Google refused" is never mistaken for "the seller
    deleted it". One is a night to run again; the other is a conversation.
    """


# --------------------------------------------------------------- finding it


def _looking_for(name: str, trashed: bool) -> str:
    """The Drive search for one spreadsheet of one name.

    **`trashed` IS ASKED BOTH WAYS ON PURPOSE.** A search that only ever says
    `trashed = false` cannot tell a ledger that was never made from a ledger
    sitting in the seller's rubbish bin -- and answering the second as though it
    were the first is exactly the silent second sheet D184 forbids.
    """
    return (
        f"name = '{name}' and mimeType = '{SPREADSHEET}' "
        f"and trashed = {'true' if trashed else 'false'}"
    )


def find_the_ledger(transport, name: str = THE_SHEET_IS_CALLED) -> Optional[str]:
    """The id of the ledger this app made, or None if it has never made one.

    **THROUGH THE SAME PAGER EVERY OTHER LISTING USES**, deliberately: that one
    reads every page, asks for `nextPageToken` by name, and refuses an incomplete
    search rather than believing it (D161). A second listing written here would be
    a second set of those guards to keep right, and the fault it would hide is the
    worst one available -- a short listing reads as "no ledger", and "no ledger"
    is what makes a new one.

    **TWO OF THE SAME NAME IS NOT SOMETHING TO CHOOSE BETWEEN.** Picking one would
    write tonight's sales into a different history from last night's, silently.
    Same shape, same refusal, as `drive_door.folder_for` (D119, one shape not two).
    """
    found = _every_file(
        transport,
        _looking_for(name, trashed=False),
        "id,name",
        f"looking for the {name} spreadsheet",
    )
    if len(found) > 1:
        raise CannotMakeTheLedger(
            f"There are {len(found)} spreadsheets called {name} that Kartaan made "
            "in the seller's Drive. Which one holds their sales cannot be known, "
            "so nothing has been written to either."
        )
    if found:
        return found[0]["id"]

    # **NOT THERE IS NOT THE SAME AS NEVER THERE.** Before anything is made, the
    # rubbish bin is asked -- because a deleted ledger and a ledger that never
    # existed look identical from the search above, and making a new one on top of
    # a deleted one loses the seller's whole history without a word.
    binned = _every_file(
        transport,
        _looking_for(name, trashed=True),
        "id,name",
        f"looking in the rubbish bin for the {name} spreadsheet",
    )
    if binned:
        raise TheLedgerIsGone(what_to_tell_them_about_a_deleted_ledger(in_the_bin=True))
    return None


# --------------------------------------------------------------- making it


def the_creating_call() -> Dict:
    """The body that makes the seller's ledger. **Built, never typed.**

    **THE TAB IS NAMED IN THE SAME CALL THAT MAKES THE SPREADSHEET.** A new one's
    tab is called `Sheet1`, and this ledger requires a tab called `orders` -- the
    door refuses any spreadsheet without one. Naming it here costs nothing, and it
    removes for ever the state where Kartaan has made a sheet it cannot itself
    write to.

    **READ OFF GOOGLE'S OWN REFERENCE, not a sample:** the body of
    `spreadsheets.create` is a Spreadsheet, a Spreadsheet carries `sheets`, a
    Sheet carries `properties`, and `SheetProperties.title` is *"The name of the
    sheet"* with `gridProperties` holding `columnCount` and `frozenRowCount`.
    """
    return {
        "properties": {"title": THE_SHEET_IS_CALLED},
        "sheets": [
            {
                "properties": {
                    "title": sales.THE_TAB,
                    "gridProperties": {
                        "columnCount": HOW_MANY_COLUMNS,
                        "frozenRowCount": THE_HEADER_STAYS_PUT,
                    },
                }
            }
        ],
    }


def make_the_ledger(ask: Callable) -> str:
    """Make the seller's sales ledger, and say which one it is.

    **IN THE SELLER'S OWN DRIVE, WITH THE SELLER'S OWN PERMISSION.** A spreadsheet
    made through the Sheets API lands in the Drive of whoever the token belongs
    to, which is the seller. It is deliberately NOT moved into Kartaan's own
    folder: that folder holds the machine's files -- raw platform reports, the
    log, the record between runs -- and this is a document a person opens. Moving
    it would also be a second call that can half-succeed, for no gain.

    **THE HEADER IS A SECOND CALL, AND THAT IS SAID RATHER THAN HIDDEN.** Seeding
    cells inside the creating call is allowed by the resource and is shown nowhere
    in Google's own guide, and Golden Rule 1 forbids guessing at the shape of a
    call. So the header goes through `ledger_door.write_the_header`, which is the
    reviewed call the ERP already makes. **The gap between the two calls is real
    and is covered**: a run that dies between them leaves a sheet with no header,
    the next run finds it by name, and `make_sure_the_header_is_there` puts the
    header on. That repair has to exist anyway, so it costs nothing here.
    """
    said = ask("POST", "/v4/spreadsheets", body=the_creating_call())
    which = (said or {}).get("spreadsheetId") if isinstance(said, dict) else None
    if not str(which or "").strip():
        raise CannotMakeTheLedger(
            "Google was asked to make the seller's sales ledger and did not say "
            "which spreadsheet it made, so there is nowhere to write and nothing "
            "has been written down as read."
        )
    return str(which).strip()


def make_sure_the_header_is_there(door: LedgerDoor) -> str:
    """Row 1 says what every column means, or this refuses. Never both.

    **THREE STATES, AND EACH HAS ITS OWN ANSWER.** Written as one `if` they
    collapse into "write the header if it looks wrong", and that overwrites the
    seller's first sale with a row of column names.

    | What row 1 is | What happens |
    |---|---|
    | nothing at all | the header is written -- this is a sheet that was made and not finished |
    | exactly the columns | nothing |
    | anything else | **REFUSED**, in words, and not one cell is touched |

    **THE THIRD IS THE ONE THAT MATTERS.** A ledger written before a column
    existed has a header that was right the day it was made and is short today,
    and rewriting it silently renames every column of every row already in it.
    What happens to a sheet written before a column existed is undecided (carried
    from D150, D151 and D152), and this refuses rather than deciding it here.
    """
    rows = door.everything()
    header = [str(c) for c in (rows[0] if rows else [])]
    want = [str(c) for c in sales.the_header()]
    if not any(cell.strip() for cell in header):
        door.write_the_header()
        return "the column names were put on row 1 of a sheet that had none"
    if header == want:
        return "the column names were already right"
    raise CannotMakeTheLedger(
        "That spreadsheet's first row is not this ledger's column names "
        f"({len(header)} columns where there should be {len(want)}; the first "
        f"one that differs is column {_first_difference(header, want)}). Nothing "
        "has been written to it. Rewriting row 1 would rename every column of "
        "every sale already in the sheet, so this stops instead."
    )


def _first_difference(header: Sequence[str], want: Sequence[str]) -> int:
    """Which column first disagrees, counting from 1. **Named, not hinted at.**"""
    for at, (was, should) in enumerate(zip(header, want), start=1):
        if was != should:
            return at
    return min(len(header), len(want)) + 1


# ------------------------------------------------- the one way to ask Google


def a_way_to_ask(transport, api: str = SHEETS) -> Callable:
    """Turn the seller's `Google` connection into what `LedgerDoor` asks with.

    **ONE CONNECTION, ONE REFRESH TOKEN, THREE GOOGLE SERVICES.** Drive, the
    seller's database and now Sheets are the same seller's same permission; a
    second way of holding that token would be a second place it could leak
    (Golden Rule 8). Nothing here reads the token, prints it, or puts it in an
    address -- the transport keeps it and this only calls the transport.

    **A REFUSAL SAYS THE STATUS, NEVER WHAT WAS SENT.** These sentences end up in
    a log that is written into the seller's own Drive.
    """

    def ask(
        method: str,
        path: str,
        query: Optional[Dict] = None,
        body: Optional[Dict] = None,
    ):
        where = f"{api}{path}"
        if method == "GET":
            reply = transport.get(where, params=query)
        elif method == "POST":
            reply = transport.post(where, params=query, json=body)
        else:
            # **REFUSED RATHER THAN GUESSED AT.** The two the ledger uses are the
            # two that exist here; anything else is a call nobody has read
            # Google's documentation for.
            raise CannotMakeTheLedger(
                f"The sales ledger was asked to talk to Google with {method}, and "
                "the only ways it talks are GET and POST."
            )
        if reply is None:
            raise DriveSaidNo(
                f"{method} {path}: Google said nothing at all about the sales ledger."
            )
        if not getattr(reply, "ok", False):
            raise DriveSaidNo(
                f"{method} {path}: Google refused "
                f"({getattr(reply, 'status', '')}) about the sales ledger. "
                f"{getattr(reply, 'text', '') or ''}"[:400]
            )
        return reply.json()

    return ask


# ------------------------------------------------------- putting it together


def the_ledger(
    transport,
    remembered: Optional[str] = None,
    say: Optional[Callable[[str], None]] = None,
    ask: Optional[Callable] = None,
) -> Tuple[LedgerDoor, str]:
    """The seller's ledger, made if it has never existed, and its id.

    **THE ORDER IS THE WHOLE DESIGN, and each step is there for a failure that has
    a name:**

    1. **A REMEMBERED ID IS USED AND NEVER SECOND-GUESSED.** If it no longer
       answers, that is `TheLedgerIsGone` and the run stops. It does NOT then look
       by name and it does NOT make a new one -- a seller who renamed their sheet
       would otherwise get a second, empty one beside it, and a seller who deleted
       theirs would get their whole history quietly replaced by tonight's.
    2. **NOTHING REMEMBERED, SO LOOK BY NAME.** This is a first night, or a record
       that was lost. Adopting what is already there is what stops a forgotten id
       from costing the seller their history.
    3. **NOTHING FOUND, SO MAKE IT** -- and the rubbish bin has already been asked
       by then, so "nothing found" really does mean never made.

    **AND THE HEADER IS CHECKED WHICHEVER WAY IT ARRIVED.** A sheet adopted at
    step 2 may have been made by a run that died before writing row 1.
    """
    speak = say if callable(say) else (lambda line: None)
    asking = ask if callable(ask) else a_way_to_ask(transport)

    which = str(remembered or "").strip()
    if which:
        door = LedgerDoor(asking, which)
        try:
            door.make_sure_it_is_ours()
        except (ledger.LedgerRefused, DriveSaidNo) as wrong:
            # **BOTH KINDS MEAN THE SAME THING HERE, and that is worth saying.**
            # "Google would not answer about that spreadsheet" and "that
            # spreadsheet is not this ledger" are different sentences and the same
            # situation: the sheet this seller's history is in cannot be reached
            # tonight. Neither is ever answered by making another one.
            raise TheLedgerIsGone(
                what_to_tell_them_about_a_deleted_ledger(in_the_bin=False)
                + f"\n(Google was asked about it and the answer was: {wrong})"
            ) from wrong
        speak("The seller's sales ledger is the sheet this job already knew about.")
    else:
        found = find_the_ledger(transport)
        if found:
            which = found
            speak("The seller's sales ledger was found in their Drive by name and adopted.")
        else:
            which = make_the_ledger(asking)
            speak("The seller's sales ledger did not exist and has been made in their own Drive.")
        door = LedgerDoor(asking, which)

    speak(f"The sales ledger: {make_sure_the_header_is_there(door)}.")
    return door, which


def recording_into(
    door: LedgerDoor,
    say: Optional[Callable[[str], None]] = None,
) -> Callable[[Sequence[ledger.Reading]], None]:
    """What `reading.read_what_is_new` has always taken and has never been given.

    **THE SHEET IS READ AGAIN FOR EVERY FILE, and that is not waste.** A plan's row
    numbers describe the sheet as it was READ; the moment rows are appended they
    are stale. Holding one reading across a night of files is how the second
    file's changes land on the first file's row numbers -- which is the one thing
    `ledger_door.carry_out` is written to make impossible, undone from outside.

    **AND IT REFUSES OUT LOUD.** Anything that throws here reaches
    `read_what_is_new`, which records the file as one it could not read and --
    this is the point -- **does not write it down as read.** The file is opened
    again tomorrow. A run that swallowed this would mark files read whose sales
    reached nothing, and they would never be read again (D157).

    **AND ONE THING THROWS ON PURPOSE RATHER THAN BY ACCIDENT (A32):** a row held
    back because its date-marker cell is not a date. That is the one kind of
    "left alone" a person can fix, and it is only fixable if the file is still
    waiting to be read when they fix it. See the refusal at the end of
    `record_the_sales`.

    **WHAT THE NIGHT HAS DECIDED IS MADE ONCE HERE AND HANDED TO EVERY FILE, and
    that is what lets D150's rule 3 fire at all.** The sheet is re-read per file
    and `plan` is called per file, so `plan`'s own memory of which file claimed
    which column started empty every time: two files of ONE report and ONE data
    date -- his own re-fetch-by-hand case (D110) -- never met, the tie was
    invisible, and **the seller's figure was settled silently by which Drive id
    sorted higher.** The loop below that reports a disagreement could not fire,
    ever. **The one-file-at-a-time handover is untouched** -- it is what makes
    marking a file read safe -- and the memory is what crosses it.
    """
    speak = say if callable(say) else (lambda line: None)
    # **ONE PER NIGHT, NOT ONE PER FILE.** Made here rather than inside the
    # function below, which is called once per file and would make a fresh empty
    # one each time -- which is exactly the fault this closes.
    so_far = ledger.WhatTheNightHasDecided()

    def record_the_sales(readings: Sequence[ledger.Reading]) -> None:
        rows = door.everything()
        what = ledger.plan(rows, list(readings or ()), so_far)
        did = door.carry_out(what)
        speak(f"Sales ledger: {did['added']} added, {did['changed']} changed.")
        # **REPORTED, NEVER SWALLOWED.** A disagreement is two equally current
        # files claiming one column, and D150 says keep what is already there and
        # SAY SO. A row the sheet holds twice is reported the same way and left
        # alone, because writing to either of them is writing to the wrong one.
        for one in what.disagreements:
            speak(f"SALES LEDGER DISAGREEMENT  {one}")
        # **AND AN OLDER FILE THAT WAS NOT ALLOWED TO UNDO A NEWER ONE IS SAID
        # TOO.** That is rule 2 working rather than a fault -- and a by-hand
        # backfill (D110) is a deliberately old file somebody fetched on
        # purpose, so a night that ignored one in silence would look exactly
        # like a night that applied it.
        for one in what.left_alone:
            speak(f"SALES LEDGER OLDER THAN THE ROW  {one}")
        for one in what.unreadable:
            speak(f"SALES LEDGER UNREADABLE ROW  {one}")
        # **AND A FILE HELD BACK BY A CELL SOMEBODY TYPED OVER IS REFUSED, WHICH
        # IS THE ONLY WAY IT EVER GETS READ AGAIN (A32).**
        #
        # `ledger.older_than_the_row` treats a marker nobody can read as NEWER --
        # the safe direction -- and its own words called that "the recoverable
        # half of the mistake, because a file left alone is never written down as
        # read". **That sentence was false.** This function returned normally,
        # `reading.read_what_is_new` reached `read_tonight.append(one)` like any
        # other file, and the file WAS marked read. So somebody could put the
        # cell back and the file that was waiting on it would never be opened
        # again -- the sale sitting in it lost for good, silently.
        #
        # **THROWING IS THE ONE PATH THAT LEAVES A FILE UNREAD**, and it is the
        # path this function's own header already describes: what throws here is
        # named, the file stays in the folder, and it is opened again tomorrow.
        # What was already written stays written; reading the file again writes
        # the same figures and changes nothing.
        #
        # **AND RULE 2 WORKING IS NOT THIS.** A genuinely older file is old for
        # ever, and marking it read is correct -- refusing it would re-read it
        # every night until the end of time and say the same thing each night.
        if what.somebody_has_to_put_a_cell_back:
            raise ledger.LedgerRefused(
                "a date-marker cell in the seller's sales ledger holds something "
                "that is not a date, so this file was not applied to those rows "
                "and has NOT been written down as read. Put the cell back to a "
                "date and it is read again the next night. The rows are named "
                "above, each on its own SALES LEDGER OLDER THAN THE ROW line."
            )

    return record_the_sales


def which_reports_an_older_file_could_still_undo() -> Tuple[str, ...]:
    """Which readable reports a file older than the row could still overwrite.

    **THE WHOLE OF D157, ASKED AS A BEHAVIOUR RATHER THAN AS A SPELLING.** For
    every report this run can turn into sales, both halves of that behaviour are
    DRIVEN -- neither is read off a list of column names, which is what both
    earlier versions of this guard did, and both lifted themselves while the harm
    they were written for was untouched.

    **IT REALLY DOES ASK THE TWO HALVES, AND UNTIL A32 IT ONLY CLAIMED TO.** This
    docstring used to say "IT ANSWERS THE TWO HALVES AT ONCE" and that "a report
    whose rows carry no marker cannot be told apart from a newer one, so it fails
    this". **Both were false.** The one question asked was
    `ledger.would_an_older_file_be_stopped`, which builds its own `Reading` with
    the markers ALREADY FILLED -- so it drove the WRITING half honestly and never
    went near a reader. An independent reviewer proved it by taking
    `orders_on=data_date` out of `orders.py`, and again by turning
    `reading.a_reading`'s `data_date=when.isoformat()` into a fixed constant
    claiming every file is the same day: **the guard said "safe to write" through
    both.** That is the third generation of one fault -- a guard that reads as
    covering something it does not touch -- and this is the repair.

    | The half | Who drives it | What breaks it |
    |---|---|---|
    | A file really PUTS its own day in a marker | `reading.would_a_file_say_which_day_it_is` | no reader fills one, or fills it with the wrong day |
    | An older file is really STOPPED by it | `ledger.would_an_older_file_be_stopped` | `plan` stops reading the marker back |

    **EMPTY MEANS BOTH ARE TRUE, for every report a run can read.**
    """
    import reading  # noqa: PLC0415 - kept beside its one use

    return tuple(
        how.report_id for how in reading.WHAT_CAN_BE_READ
        if not (reading.would_a_file_say_which_day_it_is(how)
                and ledger.would_an_older_file_be_stopped(how.knows))
    )


def why_it_must_not_write_yet() -> str:
    """Why writing to the seller's sheet is refused tonight, or "" when it is not.

    **WHAT GOES WRONG, in one sentence:** the fourth day's file arrives late, on a
    night after the fifth's correction is already in the sheet, and nothing in the
    sheet says which day's file wrote it -- so the fourth's old figure goes over
    the fifth's and the seller is never told. **That is the money, and it is
    silent.**

    ---

    **THIS GUARD HAS NOW ASKED THREE DIFFERENT QUESTIONS, AND THE FIRST TWO BOTH
    LIFTED THEMSELVES WHILE THE HARM ABOVE WAS UNTOUCHED. THAT HISTORY IS THE
    REASON THE THIRD ONE IS SHAPED THE WAY IT IS.**

    | Asked | What it really tested | It lifted while |
    |---|---|---|
    | Are the four columns NAMED? | a name in a list | nothing filled one |
    | Would a row CARRY a marker? | a name in `knows` | nothing read one back |
    | Would an OLDER FILE be stopped? | the WRITING half only | no reader filled one |
    | **Both halves, each driven** | **the behaviour, end to end** | -- |

    **THE THIRD ONE IS IN THAT LIST BECAUSE IT WAS THE SAME FAULT AGAIN.** It
    drove `ledger.plan` honestly and never touched a reader, and its own words
    said it "ANSWERS THE TWO HALVES AT ONCE". An independent reviewer took the
    marker assignment out of `orders.py`, and separately made `reading.a_reading`
    claim every file was one fixed day, and it said "safe to write" through both.

    **THE FIRST LIFTED ON 2026-09-06**, the day the ERP put the four names in its
    column list, while a `grep` for the four fields across `autosync/` outside
    `sales.py` returned nothing. **The second was written to repair the first and
    reproduced its exact shape one level up** -- an independent reviewer proved it
    the same day by taking the assignment out of `orders.py` and watching all 114
    checks stay green.

    **A GUARD THAT LIFTS ON THE APPEARANCE OF THE THING IT WANTS IS WORSE THAN NO
    GUARD**, because it also tells everybody the thing is now handled.

    **SO THE QUESTION IS NOW THE BEHAVIOUR ITSELF, BOTH HALVES OF IT, DRIVEN:** a
    one-row file is put through the real reader and must come out carrying its own
    day in a marker; and `ledger` is handed a sheet holding a sale written by a
    newer file and a reading from an older one, and what came out is looked at.
    Nothing anywhere in either reads a column name.

    **THE COLUMNS ARE STILL ASKED ABOUT FIRST, and the order matters.** A column
    the ERP had dropped would fail the behaviour too -- and would be reported as
    "no reader fills a marker", pointing at the wrong repository. Asked first, the
    refusal names the missing column.

    **AND IT IS NOT A WALL.** Each half takes itself away the day its answer
    changes, and nobody has to remember to come back and delete anything.

    **WHAT IS NOT REFUSED IS THE FETCHING.** The seller's platform files still
    land in their own Drive tonight. What stops is writing and, above all,
    marking: `read_what_is_new` opens no file and writes none down as read, so
    every file waits and nothing is lost (D157, D184).
    """
    missing = ledger.what_the_sheet_cannot_yet_say()
    if missing:
        return (
            "NOTHING HAS BEEN WRITTEN TO THE SELLER'S SALES LEDGER TONIGHT, AND NO "
            "FILE HAS BEEN MARKED AS READ. This is Kartaan refusing, not Google.\n"
            "1. WHY. The sheet has no column saying which day's file last wrote each "
            "figure. Without that, a file that arrives late -- say the 4th, turning "
            "up after the 5th has already corrected a quantity -- puts its older "
            "figure back over the newer one, in the money, with nothing anywhere "
            "saying so.\n"
            "2. WHAT IS MISSING, by name: " + ", ".join(missing) + ". Each one holds "
            "the data date of the newest file of that kind that touched the row. "
            "They are D157's, and they are the ERP's to add to its column list.\n"
            "3. NOTHING IS LOST WHILE THIS STANDS. The seller's platform reports "
            "still land in their own Drive every night, and every one of them is "
            "still waiting to be read. Not one file is written down as read, so not "
            "one is skipped later.\n"
            "4. IT ENDS BY ITSELF. The day those four columns are in the ledger's "
            "columns and an older file is really stopped, this stops refusing and "
            "the night writes. Nobody has to remember to come back."
        )
    could_undo = which_reports_an_older_file_could_still_undo()
    if not could_undo:
        return ""
    return (
        "NOTHING HAS BEEN WRITTEN TO THE SELLER'S SALES LEDGER TONIGHT, AND NO "
        "FILE HAS BEEN MARKED AS READ. This is Kartaan refusing, not Google.\n"
        "1. WHY. A file OLDER than the one that last wrote a row would still be "
        "applied over it. So the 4th's file, turning up on a night after the 5th "
        "has already corrected a quantity, puts its older figure back over the "
        "newer one -- in the money, with nothing anywhere saying so.\n"
        "2. WHICH REPORTS, by name: " + ", ".join(could_undo) + ". The four "
        "columns are in the ledger; either these reports put no date in one, or "
        "nothing reads one back before writing. **A column that exists and is "
        "never used is not the safeguard, it is the appearance of one** -- and "
        "this refusal itself lifted on exactly that twice, on 2026-09-06 and "
        "again on 2026-09-08.\n"
        "3. WHAT HAS TO BE TRUE: a row carries one of "
        + ", ".join(ledger.WHICH_FILE_LAST_WROTE)
        + " -- the data date of the newest file of that kind that touched it -- "
        "AND a reading older than what that says is left alone and reported. "
        "Both, or neither is worth anything.\n"
        "4. NOTHING IS LOST WHILE THIS STANDS. The seller's platform reports "
        "still land in their own Drive every night, and every one of them is "
        "still waiting to be read. Not one file is written down as read, so not "
        "one is skipped later.\n"
        "5. IT ENDS BY ITSELF, and it is asked by DRIVING the thing rather than "
        "by reading a list of names -- so it cannot lift on the appearance of a "
        "fix a third time. Nobody has to remember to come back."
    )


def the_writing_half(
    transport,
    read_state: Callable[[], Optional[bytes]],
    save_state: Callable[[bytes], None],
    say: Optional[Callable[[str], None]] = None,
    ask: Optional[Callable] = None,
) -> Tuple[Optional[Callable], str]:
    """The one place a sale lands, and why there is none when there is none.

    **THIS IS THE RULE, AND IT LIVES HERE SO THAT IT CAN BE CHECKED.** `start.py`
    says of itself that it decides nothing, and the reason is that it is the one
    file nothing can drive: it needs a real Google account. A rule written there
    is a rule nobody ever watches fail, which is this project's own named fault
    (D171) -- the same one that left the ledger finished at both ends and called
    by nobody. So all of it is here and `start.py` calls it in one line.

    **THE ADDRESS IS WRITTEN DOWN BEFORE THE RUN, NOT AFTER.** Left until the end,
    a night that died in between would leave a ledger nothing remembers -- and the
    next night would look by name, or, where the seller had renamed it, make a
    second one. Saving first also means the tick reads the address, carries it and
    writes it back with everything else, rather than two things authoring one file.

    **AND IT REFUSES OUTRIGHT WHILE D157'S FOUR DATE COLUMNS DO NOT EXIST.** That
    is `why_it_must_not_write_yet`, asked before anything reaches Google, so no
    sheet is made that would then be refused. The register already said writing
    was not safe to land until those columns exist; this is the code agreeing with
    it rather than the sentence being softened.

    **AND WHEN THE LEDGER CANNOT BE REACHED, THE FETCHING STILL HAPPENS (D184).**
    Kartaan does not stop because a seller's sheet is gone: their platform files
    still land in their own Drive tonight. What stops is the READING -- no file is
    opened and, above all, **no file is written down as read**, which is what
    `read_what_is_new` already does when it is handed nowhere to put a sale. A file
    marked read whose sales reached nothing would never be read again (D157).
    """
    import between_runs  # noqa: PLC0415 - kept beside its one use

    speak = say if callable(say) else (lambda line: None)

    # **BEFORE GOOGLE IS TOUCHED AT ALL.** Asked after the ledger was found or
    # made, a refusal would have created a spreadsheet it then refused to write
    # to -- and a seller would be looking at an empty sheet Kartaan made and
    # would not fill. Asked here, the night makes nothing and changes nothing.
    not_yet = why_it_must_not_write_yet()
    if not_yet:
        return None, not_yet

    try:
        so_far = between_runs.read(read_state())
        door, which = the_ledger(transport, remembered=so_far.ledger_sheet, say=speak, ask=ask)
        if which != so_far.ledger_sheet:
            save_state(between_runs.write(between_runs.with_the_ledger(so_far, which)))
        return recording_into(door, speak), ""
    except Exception as wrong:  # noqa: BLE001 - handed back in words, never swallowed
        return None, str(wrong)


# ---------------------------------------------------- D184: what a rebuild loses


# **WHERE EACH COLUMN WOULD COME FROM IF THE LEDGER HAD TO BE WRITTEN AGAIN.**
#
# D184 says the seller is told what they lose, and that the list is MEASURED and
# not written from imagination. This is the measurement. Three answers, and only
# the third is a loss:
#
#   FILES   -- it comes out of a platform report, so it returns if that report is
#              still in the seller's Drive, and does not if they tidied it away
#   KARTAAN -- it is a copy of something Kartaan's own records hold, and D151
#              makes that copy one-way, so the record is the authority and it
#              returns
#   GONE    -- nothing anywhere can put it back
FROM_THE_FILES = "files"
FROM_KARTAAN = "kartaan"
CANNOT_COME_BACK = "gone"

WHERE_A_COLUMN_COMES_BACK_FROM: Dict[str, Tuple[str, str]] = {
    "id": (FROM_THE_FILES, "built from the platform, the order number and the SKU"),
    "platform": (FROM_THE_FILES, "the orders report says which platform"),
    "orderId": (FROM_THE_FILES, "the orders report"),
    "on": (FROM_THE_FILES, "the orders report"),
    "sku": (FROM_THE_FILES, "the orders report"),
    "qty": (FROM_THE_FILES, "the orders report"),
    "gmv": (FROM_THE_FILES, "the orders report"),
    "status": (FROM_THE_FILES, "the platform's own status word, from orders and payments"),
    "isShopsy": (FROM_THE_FILES, "the orders report"),
    "settlement": (FROM_THE_FILES, "the payments report"),
    "taxPct": (FROM_THE_FILES, "the payments report"),
    "returned": (FROM_THE_FILES, "the returns report"),
    "returnReason": (FROM_THE_FILES, "the returns report"),
    "claimId": (FROM_THE_FILES, "the claims report"),
    "claimStatus": (FROM_THE_FILES, "the claims report"),
    "claimRecovered": (FROM_THE_FILES, "the claims report"),
    "state": (FROM_KARTAAN, "whether the stock could be taken off the shelf"),
    "heldFor": (FROM_KARTAAN, "why it could not"),
    "took": (FROM_KARTAAN, "which stock came off the shelf"),
    "taking": (FROM_KARTAAN, "what it is still waiting on"),
    "cogs": (FROM_KARTAAN, "worked out from the stock that came off the shelf"),
    "packagingCost": (FROM_KARTAAN, "the seller's own packaging setting"),
    "earringCondition": (FROM_KARTAAN, "the quality check somebody did"),
    "boxCondition": (FROM_KARTAAN, "the quality check somebody did"),
    "chainCondition": (FROM_KARTAAN, "the quality check somebody did"),
    "itemLoss": (FROM_KARTAAN, "worked out from the quality check"),
    "packingLoss": (FROM_KARTAAN, "worked out from the quality check"),
    "chainLoss": (FROM_KARTAAN, "worked out from the quality check"),
    # **THESE TWO COME BACK WITH TODAY'S ANSWER, NOT THE DAY'S.** They are
    # snapshots (D151): written as they stood when the row was written, and worked
    # out again from records that have moved on since. That is a difference a
    # seller should be told about, and it is not a loss.
    "netPnl": (FROM_KARTAAN, "worked out again, as it stands today rather than as it stood then"),
    "returnPnl": (FROM_KARTAAN, "worked out again, today's answer for the same reason"),
    # **D157'S FOUR DATE MARKERS.** Each says which day's file last touched the
    # row. **They come back from the files**: a rebuild reads those same files in
    # the same order and sets the same markers as it goes, so nothing about them
    # is lost with the sheet. Said here rather than left out -- a column nobody
    # measured would simply not appear in what the seller is told they lose,
    # which is the warning-written-from-imagination D184 forbids, and the refusal
    # above names any column that reaches this file without an answer.
    "ordersOn": (FROM_THE_FILES, "set again as the orders report is read"),
    "returnsOn": (FROM_THE_FILES, "set again as the returns report is read"),
    "paymentsOn": (FROM_THE_FILES, "set again as the payments report is read"),
    "claimsOn": (FROM_THE_FILES, "set again as the claims report is read"),
    # ---- and the three that genuinely cannot come back
    "notes": (
        CANNOT_COME_BACK,
        "anything written into the row in words. No report and no record holds it",
    ),
    "adSpend": (
        CANNOT_COME_BACK,
        "what an advert cost this order. No report and no record anywhere carries "
        "it -- the column exists and nothing has ever filled it",
    ),
    "rev": (
        CANNOT_COME_BACK,
        "how many times THIS sheet's row had been written. It is about the sheet's "
        "own history, so a new sheet starts again from nothing",
    ),
}

for _one in sales.CHARGE_COLUMNS:
    WHERE_A_COLUMN_COMES_BACK_FROM[_one] = (
        FROM_THE_FILES,
        "the payments report, which is where every platform charge arrives",
    )
del _one


def what_a_rebuild_cannot_put_back() -> Tuple[Tuple[str, str], ...]:
    """The columns that are lost for good, measured rather than imagined (D184).

    **THIS IS THE LIST A SELLER IS SHOWN**, and it is short on purpose: D151 makes
    the ledger DERIVED with a one-way mirror, so nearly everything in it is a copy
    of something that still exists somewhere else. What is left is what was only
    ever in the sheet.
    """
    missed = [c for c in sales.COLUMNS if c not in WHERE_A_COLUMN_COMES_BACK_FROM]
    if missed:
        # **A COLUMN NOBODY MEASURED IS NOT SILENTLY SAFE.** Added and not listed
        # here, it would simply not appear in what the seller is told they lose --
        # which is the exact warning-written-from-imagination D184 forbids.
        raise CannotMakeTheLedger(
            "These ledger columns have never been measured against a rebuild, so "
            "what a seller loses cannot honestly be said: " + ", ".join(missed)
        )
    return tuple(
        (column, why)
        for column, (where, why) in WHERE_A_COLUMN_COMES_BACK_FROM.items()
        if where == CANNOT_COME_BACK
    )


def what_to_tell_them_about_a_deleted_ledger(in_the_bin: bool) -> str:
    """D184's five steps, in his order, in words a seller reads.

    **RESTORE FIRST.** It is the cheapest answer and it loses nothing at all. Only
    when that has failed is a rebuild worth talking about, and the rebuild is
    theirs to choose -- never automatic, and the offer never closes.
    """
    where = (
        "It is sitting in the rubbish bin of the seller's own Google Drive."
        if in_the_bin
        else "It has been deleted, renamed, or the permission to reach it has gone."
    )
    lost = what_a_rebuild_cannot_put_back()
    return (
        "THE SALES LEDGER IS GONE, so nothing has been written tonight and no file "
        f"has been marked as read. {where}\n"
        "1. RESTORE IT FIRST. Open Google Drive, go to Bin, right-click the "
        f'"{THE_SHEET_IS_CALLED}" spreadsheet and choose Restore. That loses '
        "nothing at all.\n"
        "2. If it cannot be restored, Kartaan can write the whole history again "
        "from the platform reports still in the seller's Drive. That is the "
        "seller's choice and is never done on its own.\n"
        "3. If they choose not to, everything else carries on working. The offer "
        "stays open for ever and they can change their mind next month.\n"
        "4. WHAT WRITING IT AGAIN CANNOT PUT BACK, measured rather than guessed "
        "at: " + "; ".join(f"{column} -- {why}" for column, why in lost) + ".\n"
        "5. A NEW SHEET IS NOT MADE IN ITS PLACE. A ledger that quietly reappears "
        "with a different history in it is worse than none, because nobody can "
        "tell which one they are reading."
    )
