"""Is the real file actually sitting in Drive? One standing answer, per report,
per day.

**WHY THIS IS NOT THE RUN LOG AND NOT THE DAY BOARD.** A job can log "success"
and leave nothing usable behind -- wrong data captured, an upload that silently
failed, a sign-in page saved under a report's name. The run log says what a night
believed it did. This says whether the file is there. The reference (section 25
of `D:\\rumee-auto-sync\\DOCS.md`) is explicit that a downstream reader **should
not have to list twenty-two folders itself, and should not trust the run log** --
and merging the two destroys exactly that property, so they stay apart.

**AND IT IS THE EVIDENCE RULE 35 NEEDS.** A version is promoted from one user to
a few only when the work it exists to do actually happened. Without a standing
record of files really landing, *"no errors for three days"* cannot be told apart
from *"nothing ran for three days"*, which is the difference that rule turns on.

---

**THE ONE LESSON, AND IT IS THE WHOLE FILE: THE CHECK IS CONTENT-BASED, NEVER
TIMING-BASED.**

The reference's first version asked *"was anything uploaded in the last few
minutes."* Because the check re-ran after every recheck, and each recheck reset
what "the last few minutes" meant, **a recheck routinely wiped out the correct
`Verified` status of about twenty unrelated reports and replaced it with a false
`Missing`.** Measured: the same data date logged *"21 verified, 2 missing"* and
then *"0 verified, 23 missing"* six minutes later, and **130 of 285 spot-checked
rows were false negatives.**

The fix was not a wider window. It was to ask a different question: **does a file
carrying that data date exist?** That removes the whole class of bug rather than
narrowing it. **Nothing in this file reasons about when anything happened.**
`checked_on` is recorded so a person can see how old an answer is, and no verdict
anywhere is allowed to read it -- there is a check that pins exactly that.

---

**THE JOIN KEY IS THE DATA DATE, NOT THE RUN DATE.** The day the data covers, not
the day the row was written. `schedule.data_date_for` is the one place that turns
one into the other, here as everywhere else: *"a failure on day X's run always
means day X-1's data is what's owed."*

**ONE LINE PER (DATA DATE, REPORT). A later write REPLACES that line in place.**
It never appends a second one. That is what makes re-running safe, and it is why
`merge` refuses a batch that names the same day and report twice.

---

**THERE ARE THREE ANSWERS, NOT TWO, AND THE THIRD IS WHAT MAKES TWO WRITERS
SAFE.**

| | |
|---|---|
| `verified` | checked, and a file carrying that data date is really there |
| `missing`  | **checked**, and no such file is there |
| no line at all | **nobody has checked.** Not the same thing as missing |

The reference had only the first two, because it had one writer. **Kartaan has
two, and they are not in the same place, do not run at the same time, and either
can be the only one that ran on a given night** -- the Amazon reports run in
GitHub Actions with no browser, the other twenty-one run in the seller's own
Chrome. A half that has not run yet contributes no lines, and no line reads as
"nobody has checked" rather than as "the file is not there". **That is the timing
bug arriving by a different door, and this is the door being shut.**

**ONE MANIFEST, TWO WRITERS, AND THE ROWS CANNOT COLLIDE.** Every report carries
exactly one `door` in `reports.py`, so the set of lines the nightly job may write
and the set the extension may write are disjoint **by construction rather than by
agreement** -- `only_mine` refuses a writer that strays outside its own, and a
check drives that refusal. One manifest rather than two because the whole purpose
is that a downstream reader asks in ONE place; two files means a reader that
forgets the second gets a partial answer with nothing saying so, which is the
silence this file exists against.

**AND A WRITE ONLY EVER CARRIES ITS OWN LINES.** There is no recompute-everything
path in here. `merge` replaces the lines it is given and leaves every other line
exactly as it was, byte for byte. So a night when the extension never opened
cannot mark a single Amazon line `missing`, and a night when GitHub Actions was
down cannot mark a single Meesho line `missing`.

---

**IT IS JSON, IN THE SELLER'S OWN DRIVE, BESIDE THE RUN'S OWN MEMORY.**

The reference's manifest was a CSV, and that went wrong in a way nobody would
have predicted: the live file was found with flipped date formats, Windows line
endings and trailing blank rows. Root-caused with byte-level evidence -- **a
spreadsheet application opening and re-saving it**, not a code bug. Its answer was
a native Google Sheet, which stores typed cells and so cannot be re-saved as text.

**Kartaan writes a JSON file instead, and here is what stops the same thing.** No
spreadsheet application opens a `.json` file, so there is no open-and-re-save step
to trigger: Drive previews it as text and offers nothing that would rewrite a date
cell. It needs no Sheets call, no new permission and no second kind of document.
**And this repository already keeps exactly this kind of record exactly this
way** -- `autosync-state.json` sits in the same folder and is read and written
through the same door.

**What it does NOT rely on is nobody editing it by hand.** If somebody does and
breaks it, `read` refuses in words. It is never read as empty -- read as empty,
every verified day in the seller's history would silently become "nobody has
checked", which is the same silence in a new coat.

---

**TWO LIMITS, STATED HERE BECAUSE THE REFERENCE STATES ITS OWN AND BOTH ARE
REAL:**

  1. **PRESENCE IS NOT CORRECTNESS.** A file that is present but corrupt reads as
     `verified`. The reference names a real case -- a truncated catalogue file.
     What is caught here is the one kind of wrongness presence alone can catch: a
     nought-byte file is never `verified`, because a day written off as arrived on
     an empty file is a day that is never fetched again.
  2. **A DAY THAT CANNOT BE FETCHED AGAIN CANNOT BE PROVED AFTERWARDS.** A report
     carrying `cannot_backfill` is a picture of how things stood on the day it was
     taken. If its file was never captured that day, the day is `missing` and will
     stay `missing` for ever, correctly. **An accepted limitation, not a bug** --
     and the reference's own version of it, a rolling "current state" file, cannot
     arise here at all: `landing.file_name_for` puts the data date in every name
     this product writes, so Kartaan has no rolling file to read the inside of.

**NOTHING HERE OPENS A CONNECTION.** Files in, lines out; lines in, bytes out.
Where those bytes come from and go to is the caller's, which is what lets every
rule below be driven with no Google account, no token and no internet.
"""

import json
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from landing import Arrived
from reports import API, BROWSER, ONLY_WHEN_ASKED, WHEN_THEY_PUBLISH_IT, Report
from schedule import data_date_for

# What the file in the seller's Drive is called. One name, beside
# `autosync-state.json`, so nothing has to search for it and nothing can write a
# second one next to it.
FILE_NAME = "autosync-manifest.json"

# Which version of this record this code reads. Written down so that the day the
# shape changes, an older reader says so rather than quietly reading the fields it
# recognises and dropping the rest -- the same rule, and the same reason, as
# `between_runs.SHAPE`.
SHAPE = 1

# The two things a line can say. **There is a third answer and it is the absence
# of a line** -- see the table at the top of this file. It has no spelling here
# on purpose: a word for it would be a word somebody could write into a line.
VERIFIED = "verified"
MISSING = "missing"
WHAT_A_LINE_CAN_SAY = (VERIFIED, MISSING)

# How far back a run re-asks the question. **A `missing` line is not final**: a
# file that lands late flips its own day to `verified` the next time that half
# runs, because the answer is asked of the folder again rather than remembered.
# Fourteen is the day board's window, so the two say the same thing about the
# same fortnight.
LOOK_BACK_DAYS = 14

# **WHICH HALF OWNS A LINE, AND IT IS THE REPORT'S OWN `door` THAT DECIDES.**
# Written down rather than worked out at each call site, because the day a report
# moves from `browser` to `api` -- which D100 says is one word -- a second copy of
# this rule is the copy nobody remembers to change.
WHO_WRITES = {
    API: "the nightly job in GitHub Actions",
    BROWSER: "the extension in the seller's own Chrome",
}

# **REPORTS THAT CANNOT BE VERIFIED BY THE DATE IN THEIR FILE NAME, NAMED ONE BY
# ONE WITH THE REASON. Empty today, and the emptiness is measured rather than
# assumed** -- there is a check below that reads `reports.py` and refuses any
# report that is neither verifiable this way nor named here.
#
# **THIS IS WHERE THE REFERENCE'S OTHER TWO KINDS OF SLOT WOULD GO, AND WHY THEY
# ARE NOT BUILT.** The reference had three: `single` (one dated file), `multi`
# (one file per live campaign that day, labelled `_1`, `_2` after sorting by the
# real filename) and `append` (a rolling file with no date in its name, verified
# by reading the file's own content for a row matching the data date).
#
# **Kartaan has only the first, and that is a fact about this product rather than
# a simplification of the reference.** `landing.file_name_for` builds exactly one
# name per report per day, with the data date in it, and `drive_door.put_file`
# replaces a file of that name rather than putting a second beside it. So there is
# no per-campaign file to number and no rolling file to read the inside of. **The
# day either becomes true -- a report that lands several files for one day, or one
# with no date in its name -- it is named here with its reason, and the check goes
# red until it is.** Writing the two branches now would be two branches nothing
# exercises, which read exactly like two branches that work.
NOT_VERIFIED_BY_A_DATE_IN_THE_NAME: Dict[str, str] = {}


class Damaged(RuntimeError):
    """The manifest is there and cannot be read.

    **ITS OWN KIND, because "not there" and "there and broken" are not the same
    thing.** Not there is an ordinary first night and starts empty. Broken, read
    as empty, silently turns every verified day in the seller's history into
    "nobody has checked" -- and the next reader downstream would then be told
    nothing had ever landed. So it refuses.
    """


@dataclass(frozen=True)
class Line:
    """One report, one data date, and whether the file is really there.

    **`checked_on` IS RECORDED AND IS NEVER READ BY A VERDICT.** It is here so a
    person can see how old an answer is, exactly as the reference's Run Date
    column is. It is also the field that, once read by anything that decides
    something, brings back the 130-out-of-285 bug -- so nothing in this file looks
    at it, and a check pins that two lines differing only in `checked_on` say the
    same thing.
    """

    data_date: date
    report_id: str
    state: str
    file_name: Optional[str] = None
    file_size: int = 0
    checked_on: Optional[date] = None

    @property
    def key(self) -> Tuple[date, str]:
        """What makes this line the same line. **The data date and the report.**"""
        return (self.data_date, self.report_id)

    @property
    def is_there(self) -> bool:
        return self.state == VERIFIED


def why_a_line_is_refused(line) -> Optional[str]:
    """What is wrong with one line, in words, or None.

    **ASKED OF EVERY LINE BEFORE ANY OF THEM IS WRITTEN.** A manifest is the one
    place downstream is meant to be able to trust, and a line with no report, no
    day or a word nobody recognises is a line that reads as an answer.
    """
    if not isinstance(line, Line):
        return "That is not a manifest line."
    if not isinstance(line.data_date, date):
        return f"{line.report_id!r}: the data date is not a day."
    if not line.report_id:
        return "A manifest line has to say which report it is about."
    if line.state not in WHAT_A_LINE_CAN_SAY:
        return (
            f"{line.report_id} for {line.data_date}: {line.state!r} is not something a line "
            f"can say. It is {VERIFIED!r} or {MISSING!r}, and nothing at all when nobody "
            "has checked."
        )
    if line.state == VERIFIED and not line.file_name:
        return (
            f"{line.report_id} for {line.data_date}: says the file is there and does not say "
            "which file. A verdict with nothing behind it is the thing this record exists "
            "to replace."
        )
    if line.state == VERIFIED and int(line.file_size or 0) <= 0:
        return (
            f"{line.report_id} for {line.data_date}: says the file is there and that it has "
            "nothing in it. A nought-byte file counted as arrived would stop its day ever "
            "being fetched again."
        )
    return None


# --------------------------------------------------------- asking the folder


def what_it_says(a_report: Report, day: date, arrived: Sequence[Arrived],
                 checked_on: Optional[date] = None) -> Line:
    """Is a file carrying this data date really in this report's folder?

    **THE QUESTION IS ABOUT THE DATA DATE AND NOTHING ELSE.** Not when the file
    landed, not whether tonight's run touched it, not what any job believed. Hand
    it the same folder twice, a month apart, and it answers the same thing --
    which is the entire difference between this and the version that produced 130
    false negatives out of 285.

    **AN EMPTY FILE IS NOT A FILE THAT ARRIVED**, and a bigger one wins over an
    empty one for the same day, exactly as the day board decides it.
    """
    best: Optional[Arrived] = None
    for one in arrived or ():
        if one.data_date != day:
            continue
        if one.is_empty:
            # **A NOUGHT-BYTE FILE IS NOT A FILE THAT ARRIVED.** It is skipped
            # outright rather than kept as a fallback: a day written off as
            # arrived on an empty file is a day nothing ever fetches again, which
            # is the quietest possible way to lose one for good.
            continue
        if best is None or one.size > best.size:
            best = one
    if best is None:
        return Line(
            data_date=day,
            report_id=a_report.id,
            state=MISSING,
            checked_on=checked_on,
        )
    return Line(
        data_date=day,
        report_id=a_report.id,
        state=VERIFIED,
        file_name=best.name,
        file_size=best.size,
        checked_on=checked_on,
    )


def is_a_day_owed(a_report: Report, day: date, arrived: Sequence[Arrived]) -> bool:
    """Is this report expected to have a file for this day at all?

    **NOTHING IS OWED ON A DAY THE PLATFORM DID NOT PUBLISH ONE.** Amazon
    schedules settlement reports on its own cycle -- roughly a fortnight -- and
    there is no way to ask for one. A `missing` line for every day between them
    would be a `missing` line nobody could ever clear, **and an alarm nobody can
    clear is an alarm everybody mutes.** A day one DID arrive on is still a line,
    so what came is still on the record.

    **THE DAY BOARD DECIDES THIS THE SAME WAY, AND A CHECK HOLDS THE TWO
    TOGETHER** rather than trusting that they were written to agree.
    """
    if a_report.every == ONLY_WHEN_ASKED:
        return False
    if a_report.every == WHEN_THEY_PUBLISH_IT:
        return any(one.data_date == day and not one.is_empty for one in arrived or ())
    return True


def lines_for(
    reports: Sequence[Report],
    arrivals: Callable[[str], Sequence[Arrived]],
    today: date,
    checked_on: Optional[date] = None,
    look_back_days: int = LOOK_BACK_DAYS,
) -> List[Line]:
    """Every line this writer has an answer for, oldest day first.

    `arrivals(report_id)` hands back what is REALLY in that report's folder.
    **There is nowhere in this call to pass what a job thought it did**, and that
    is the property rather than an oversight.

    **IT ANSWERS ONLY FOR THE REPORTS IT IS HANDED.** The caller hands in its own
    half -- `reports.on_the_api_door()` for the nightly job -- so a half that did
    not run produces no lines at all, and `merge` leaves the other half's lines
    untouched.
    """
    out: List[Line] = []
    for a_report in reports or ():
        got = list(arrivals(a_report.id) or ())
        newest = data_date_for(a_report, today)
        day = today - timedelta(days=look_back_days)
        while day <= newest:
            if is_a_day_owed(a_report, day, got):
                out.append(what_it_says(a_report, day, got, checked_on=checked_on))
            day += timedelta(days=1)
    out.sort(key=lambda one: (one.data_date, one.report_id))
    return out


# ------------------------------------------------------- who may write what


def mine(door: str, reports: Sequence[Report]) -> Tuple[str, ...]:
    """The report ids one half of the product is allowed to write lines for."""
    return tuple(r.id for r in reports or () if r.door == door)


def only_mine(lines: Sequence[Line], allowed: Sequence[str]) -> Optional[str]:
    """A refusal in words if this writer strayed outside its own half, or None.

    **THIS IS WHAT MAKES ONE MANIFEST WITH TWO WRITERS SAFE RATHER THAN MERELY
    INTENDED.** The two halves' lines are disjoint because every report has one
    door -- and this is the line of code that says so out loud, so the day
    somebody hands the nightly job the whole report list, it refuses instead of
    quietly overwriting twenty-one lines the extension owns with `missing`.
    """
    may = set(allowed or ())
    strayed = sorted({one.report_id for one in lines or () if one.report_id not in may})
    if not strayed:
        return None
    return (
        "This half of the product does not fetch " + ", ".join(strayed) + ", so it has no "
        "answer about them and nothing has been written. Writing a line about a report "
        "somebody else fetches would overwrite their answer with this one's ignorance."
    )


# ----------------------------------------------------------------- merging


def merge(standing: Sequence[Line], fresh: Sequence[Line]) -> Tuple[Line, ...]:
    """The record with this writer's answers put in place, and nothing else moved.

    **ONE LINE PER (DATA DATE, REPORT), REPLACED IN PLACE, NEVER APPENDED.** That
    is what makes a re-run safe: the same answer written twice is the same record.

    **AND EVERY LINE NOT IN `fresh` COMES THROUGH UNTOUCHED.** There is no
    recompute path in here and there must never be one. A recheck that covers one
    report leaves the other twenty-three exactly as they were -- which is the
    single property the reference's timing-based version did not have, and the
    reason 130 of 285 spot-checked rows were false negatives.
    """
    coming: Dict[Tuple[date, str], Line] = {}
    for one in fresh or ():
        wrong = why_a_line_is_refused(one)
        if wrong:
            raise Damaged(wrong)
        if one.key in coming:
            # **NEVER TWO ANSWERS FOR ONE DAY.** Which of them was meant cannot be
            # known, and picking one is picking at random.
            raise Damaged(
                f"{one.report_id} for {one.data_date} was answered twice in one write. "
                "One line per day per report is what makes this record readable."
            )
        coming[one.key] = one

    kept: Dict[Tuple[date, str], Line] = {}
    for one in standing or ():
        wrong = why_a_line_is_refused(one)
        if wrong:
            raise Damaged(wrong)
        kept[one.key] = one
    kept.update(coming)
    return tuple(sorted(kept.values(), key=lambda one: (one.data_date, one.report_id)))


# ------------------------------------------------------ reading it back out


def is_it_there(lines: Sequence[Line], report_id: str, day: date) -> Optional[str]:
    """What the record says about one report on one day -- **or None for nobody
    has checked.**

    **THE QUESTION EVERY DOWNSTREAM READER ASKS, ANSWERED IN ONE PLACE.** So
    nothing has to list a folder itself, and nothing has to trust the run log.

    **None IS A REAL ANSWER AND IT IS NOT `missing`.** A half that has never run
    has no lines, and reading that as "the file is not there" would be this
    record telling a lie about a folder nobody has looked in. It is also exactly
    what a seller sees before they have ever installed the extension.
    """
    for one in lines or ():
        if one.report_id == report_id and one.data_date == day:
            return one.state
    return None


def how_it_stands(lines: Sequence[Line], day: date) -> Dict[str, int]:
    """How many reports are verified, missing and unchecked for one day.

    Counted from the lines themselves. **What is NOT here is a total** -- a total
    would need to know how many reports there are, and a record that thinks it
    knows that is a record that reads a half that never ran as a pile of failures.
    """
    said = {VERIFIED: 0, MISSING: 0}
    for one in lines or ():
        if one.data_date == day and one.state in said:
            said[one.state] += 1
    return said


# ------------------------------------------------------------ the bytes


def write(lines: Sequence[Line]) -> bytes:
    """The record as bytes to put in the seller's Drive.

    **SORTED AND SPELT THE SAME WAY EVERY TIME**, so two runs that found the same
    thing write the same bytes, and a person reading it back sees a stable order
    rather than the order a folder listing happened to come in.
    """
    for one in lines or ():
        wrong = why_a_line_is_refused(one)
        if wrong:
            raise Damaged(wrong)
    ordered = sorted(lines or (), key=lambda one: (one.data_date, one.report_id))
    return json.dumps(
        {
            "shape": SHAPE,
            "lines": [
                {
                    "dataDate": one.data_date.isoformat(),
                    "reportId": one.report_id,
                    "state": one.state,
                    "fileName": one.file_name or "",
                    "fileSize": int(one.file_size or 0),
                    "checkedOn": one.checked_on.isoformat() if one.checked_on else "",
                }
                for one in ordered
            ],
        },
        indent=1,
        sort_keys=False,
    ).encode("utf-8") + b"\n"


def read(body: Optional[bytes]) -> Tuple[Line, ...]:
    """The record as lines, or nothing at all when there is no record yet.

    **NOTHING THERE AND SOMETHING BROKEN ARE NOT THE SAME THING.** Nothing there
    is an ordinary first night and answers an empty record. Broken refuses --
    because read as empty it would tell every downstream reader that nothing has
    ever landed, which is the loudest possible wrong answer.
    """
    if body is None or body == b"":
        return ()
    try:
        said = json.loads(bytes(body).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as wrong:
        raise Damaged(
            f"{FILE_NAME} is there and cannot be read: {wrong}. It has not been treated as "
            "empty, because that would say nothing has ever landed."
        ) from None
    if not isinstance(said, dict):
        raise Damaged(f"{FILE_NAME} is there and is not a record of this kind.")
    shape = said.get("shape")
    if shape != SHAPE:
        raise Damaged(
            f"{FILE_NAME} is written in shape {shape!r} and this reads shape {SHAPE}. "
            "Nothing has been read, rather than the fields this happens to recognise."
        )
    rows = said.get("lines")
    if not isinstance(rows, list):
        raise Damaged(f"{FILE_NAME} has no lines in it at all, which is not an empty record.")

    out: List[Line] = []
    for row in rows:
        if not isinstance(row, dict):
            raise Damaged(f"{FILE_NAME} holds something that is not a line.")
        try:
            day = date.fromisoformat(str(row.get("dataDate")))
        except (TypeError, ValueError):
            raise Damaged(
                f"{FILE_NAME}: {row.get('dataDate')!r} is not a day, so the record cannot be "
                "read. It has not been treated as empty."
            ) from None
        checked = str(row.get("checkedOn") or "")
        try:
            when = date.fromisoformat(checked) if checked else None
        except ValueError:
            raise Damaged(
                f"{FILE_NAME}: {checked!r} is not a day, so the record cannot be read."
            ) from None
        line = Line(
            data_date=day,
            report_id=str(row.get("reportId") or ""),
            state=str(row.get("state") or ""),
            file_name=str(row.get("fileName") or "") or None,
            file_size=int(row.get("fileSize") or 0),
            checked_on=when,
        )
        wrong = why_a_line_is_refused(line)
        if wrong:
            raise Damaged(f"{FILE_NAME}: {wrong}")
        out.append(line)
    return tuple(sorted(out, key=lambda one: (one.data_date, one.report_id)))
