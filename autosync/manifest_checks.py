"""Checks for the download manifest.

**THE CHECK THIS FILE EXISTS FOR IS THE ONE THAT WOULD HAVE CAUGHT THE
REFERENCE'S WORST MANIFEST BUG:** a recheck must not turn another report's
`verified` into `missing`. That fault put 130 false negatives into 285
spot-checked rows, and it is driven here in both directions -- the content-based
version does not do it, and the timing-based version it replaced is put back in
and watched doing it.

Run: python autosync/manifest_checks.py
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import board  # noqa: E402
import drive  # noqa: E402
import manifest as tool  # noqa: E402
from landing import Arrived, file_name_for  # noqa: E402
from reports import (  # noqa: E402
    API,
    BROWSER,
    DAILY,
    ONLY_WHEN_ASKED,
    REPORTS,
    WHEN_THEY_PUBLISH_IT,
    Report,
    on_the_api_door,
    on_the_browser_door,
)

ran = 0
failures = []
# Everything that ended by throwing rather than by answering. **The floor under
# all of it:** answering with nothing stops the run dying, but on its own it is
# not enough -- a check written as "this word is NOT in what it said" passes
# against nothing, and would go green for the worst possible reason.
THREW = []


def answered(work):
    """What this answers, or nothing at all when it threw.

    **A RUN THAT STOPS IS NOT A CHECK GOING RED.** Worked out before it is handed
    over, one deliberate breakage anywhere ends the whole run and nothing goes
    red. Worked out in here, a call that throws answers with nothing, that one
    check goes red by itself, and the rest still run.
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


def _refused(work):
    """Did this refuse in words? **Asked of the kind, never of the wording.**"""
    try:
        work()
    except tool.Damaged:
        return True
    return False


DAY = lambda s: date.fromisoformat(s)  # noqa: E731
TODAY = DAY("2026-09-10")
YESTERDAY = DAY("2026-09-09")


# ------------------------------------------------- what is actually declared

EVERY = list(REPORTS)
API_HALF = list(on_the_api_door())
BROWSER_HALF = list(on_the_browser_door())
print(
    f"--- {len(EVERY)} reports declared in reports.py: "
    f"{len(API_HALF)} on the API door, {len(BROWSER_HALF)} on the browser door"
)

check(
    "every declared report belongs to exactly one of the two halves",
    len(API_HALF) + len(BROWSER_HALF) == len(EVERY),
)
# **THE TWO WRITERS' LINES CANNOT COLLIDE, AND THIS IS WHY.** Not because the two
# were written to agree -- because a report carries one door and nothing else.
check(
    "and no report is owned by both halves",
    not (set(r.id for r in API_HALF) & set(r.id for r in BROWSER_HALF)),
)
check(
    "and every door has a named half that writes its lines",
    all(r.door in tool.WHO_WRITES for r in EVERY),
)

# **WHAT KEEPS `NOT_VERIFIED_BY_A_DATE_IN_THE_NAME` HONEST -- AND WHAT USED TO
# STAND HERE COULD NOT.**
#
# The check here asked `data_date_in(file_name_for(r, YESTERDAY)) == YESTERDAY` of
# every declared report. `file_name_for` puts the ISO date into every name it
# builds, unconditionally, so that expression is True for every possible `Report`,
# for ever. Two adversarial reports standing for the reference's `multi` and
# `append` kinds both sailed through it. **An expectation derived from the thing
# it checks is not an expectation** -- rule 2 of the five in part 5 of
# `WHAT-IS-NOT-DONE.md` -- and it was derived from `file_name_for`, which is the
# very function whose behaviour is in question.
#
# **SO THE PROPERTY IS ASSERTED WHERE IT IS ACTUALLY HELD, IN THE TWO PLACES THAT
# HOLD IT, AND BOTH CAN GO RED.** One file per report per day is true because
# `file_name_for` has nowhere to be told about a second file, and because the door
# replaces a file of that name rather than putting one beside it.

# **NOWHERE TO NAME A SECOND FILE FOR THE SAME DAY.** Structural, in the shape of
# the clock check further down: the day somebody adds a campaign, a part or a
# counter to the name -- which is the day the reference's `multi` kind arrives
# here -- this goes red before any behaviour has to be wrong.
def _what_a_name_is_built_from():
    code = file_name_for.__code__
    return tuple(code.co_varnames[:code.co_argcount])


check(
    "a file's name is built from a report and a day and nothing else -- there is nowhere "
    "to name a second file for the same report and day",
    answered(lambda: _what_a_name_is_built_from() == ("a_report", "data_date")),
)

# **AND THE DOOR REPLACES RATHER THAN PUTS BESIDE.** `drive.what_to_do_about` is
# the one place that decides it, and it is asked here rather than trusted: a name
# already there is replaced, and more than one already there is refused outright
# instead of being tidied up on a guess.
THERE = [{"id": "a", "name": file_name_for(REPORTS[0], YESTERDAY)}]
check(
    "a name already in the folder is replaced, never put beside",
    answered(lambda: drive.what_to_do_about(file_name_for(REPORTS[0], YESTERDAY), THERE)
             == "replace"),
)
check(
    "and two of one name in the folder is refused rather than tidied up on a guess",
    answered(lambda: drive.what_to_do_about(
        file_name_for(REPORTS[0], YESTERDAY), THERE + [dict(THERE[0], id="b")])
        == "somebody has to look"),
)

# **AND THE HOLE IS STATED OUT LOUD RATHER THAN GUARDED BY A CHECK THAT CANNOT
# FIRE.** A day is read as arrived on the strength of ONE file. So a report that
# ever lands several files for one day would read `verified` with most of it
# absent -- driven here against a real declared report, `me_ads_summary`, which is
# the one the reference splits per campaign and which Kartaan builds as a single
# CSV. **This is what `NOT_VERIFIED_BY_A_DATE_IN_THE_NAME` is for**, and it is why
# the two checks above are the ones that have to hold.
SPLIT = next(r for r in EVERY if r.id == "me_ads_summary")
HALF_A_DAY = [Arrived(f"meesho_me_ads_summary_{YESTERDAY.isoformat()}_1.csv", 4021)]
check(
    "a day split across several files reads as arrived on the strength of one of them -- "
    "which is why a report that lands more than one has to be named as a hole",
    answered(lambda: tool.what_it_says(SPLIT, YESTERDAY, HALF_A_DAY).state == tool.VERIFIED),
)
check(
    "and any hole that is named is a report that really exists and gives a reason "
    "somebody can read",
    all(
        which in {r.id for r in EVERY} and len(str(why).strip()) > 20
        for which, why in tool.NOT_VERIFIED_BY_A_DATE_IN_THE_NAME.items()
    ),
)


# ---------------------------------------------------------- a folder to ask

def a_real_file(a_report, day, size=4021):
    return Arrived(file_name_for(a_report, day), size)


def folder(**by_report):
    return lambda report_id: by_report.get(report_id, [])


ORDERS = Report("az_orders", "amazon", "Amazon orders", API, DAILY, "csv")
RETURNS = Report("az_returns", "amazon", "Amazon returns", API, DAILY, "csv")

got = folder(az_orders=[a_real_file(ORDERS, YESTERDAY)])
one = answered(lambda: tool.what_it_says(ORDERS, YESTERDAY, got("az_orders"), checked_on=TODAY))
check("a day whose file is really there says verified", answered(lambda: one.state == tool.VERIFIED))
check("and it names the file it found and its size", answered(lambda: one.file_name.endswith(".csv") and one.file_size == 4021))
missing = answered(lambda: tool.what_it_says(ORDERS, DAY("2026-09-08"), got("az_orders"), checked_on=TODAY))
check("a day with no file for it says missing", answered(lambda: missing.state == tool.MISSING))
check("and names no file, because it found none", answered(lambda: missing.file_name is None))

empty = answered(lambda: tool.what_it_says(
    ORDERS, YESTERDAY, [Arrived(file_name_for(ORDERS, YESTERDAY), 0)], checked_on=TODAY))
check("a nought-byte file is not a day that arrived", answered(lambda: empty.state == tool.MISSING))

# **PRESENCE IS NOT CORRECTNESS, AND IT IS SAID RATHER THAN HIDDEN.** A file that
# is present and wrong reads as verified -- the reference names a truncated
# catalogue file as the real case.
corrupt = answered(lambda: tool.what_it_says(
    ORDERS, YESTERDAY, [Arrived(file_name_for(ORDERS, YESTERDAY), 12)], checked_on=TODAY))
check("a present-but-tiny file still reads as verified -- presence is not correctness",
      answered(lambda: corrupt.state == tool.VERIFIED))


# ------------------------------------------- the answer does not read a clock

# **THE WHOLE LESSON, DRIVEN.** Hand the same folder the same question with two
# completely different "when was this checked" values and the verdict must be
# identical. `checked_on` is recorded and is read by nothing.
early = answered(lambda: tool.what_it_says(ORDERS, YESTERDAY, got("az_orders"), checked_on=DAY("2026-09-10")))
late = answered(lambda: tool.what_it_says(ORDERS, YESTERDAY, got("az_orders"), checked_on=DAY("2027-04-01")))
check(
    "the same folder answers the same thing whenever it is asked",
    answered(lambda: (early.state, early.file_name, early.file_size)
             == (late.state, late.file_name, late.file_size)),
)
check("and the two differ only in when they were checked",
      answered(lambda: early.checked_on != late.checked_on))
# **AND THERE IS NOWHERE TO PASS A CLOCK.** Structural as well as behavioural,
# because a future edit could add one and the behaviour above would still pass on
# the day it was added.
check(
    "and the question has nowhere to be told what time it is",
    answered(lambda: "now" not in tool.what_it_says.__code__.co_varnames
             and "uploaded_at" not in tool.what_it_says.__code__.co_varnames),
)


# ------------------------------------------------------------- one line, in place

first = answered(lambda: tool.lines_for([ORDERS], got, TODAY, checked_on=TODAY, look_back_days=2))
check("one line per report per data date", answered(lambda: len(first) == 2))
check("oldest day first", answered(lambda: first[0].data_date < first[-1].data_date))
again = answered(lambda: tool.merge(first, first))
check("writing the same answer twice writes one record, not two", answered(lambda: len(again) == len(first)))
check("and the record is unchanged by it", answered(lambda: tuple(again) == tuple(first)))
check(
    "two answers for one day in one write are refused rather than one being picked",
    answered(lambda: _refused(lambda: tool.merge((), [first[0], first[0]]))),
)


# --------------------------------------------------------------------------
# THE ONE THAT MATTERS: A RECHECK MUST NOT TURN ANOTHER REPORT'S VERIFIED INTO
# MISSING.
#
# The reference's first version asked "was anything uploaded in the last few
# minutes". Each recheck reset what that meant, so a recheck wiped the correct
# `Verified` of about twenty unrelated reports and wrote a false `Missing` over
# it. Measured: "21 verified, 2 missing" then "0 verified, 23 missing" six
# minutes later; 130 of 285 spot-checked rows were false negatives.
# --------------------------------------------------------------------------

# A whole night, both halves, every declared report with a real file for
# yesterday. This is the state the reference was in when its recheck ruined it.
EVERYTHING = {r.id: [a_real_file(r, YESTERDAY)] for r in EVERY}
WHOLE_FOLDER = folder(**EVERYTHING)


def a_full_night(checked_on):
    """Both halves, each writing only its own lines, into one manifest."""
    record = ()
    for half in (API_HALF, BROWSER_HALF):
        fresh = tool.lines_for(half, WHOLE_FOLDER, TODAY, checked_on=checked_on, look_back_days=1)
        record = tool.merge(record, fresh)
    return record


BEFORE = answered(lambda: a_full_night(TODAY))
check(
    "a full night verifies every declared report for yesterday",
    answered(lambda: tool.how_it_stands(BEFORE, YESTERDAY)[tool.VERIFIED] == len(EVERY)),
)
check(
    "and nothing about that day is missing",
    answered(lambda: tool.how_it_stands(BEFORE, YESTERDAY)[tool.MISSING] == 0),
)


def what_went_backwards(before, after):
    """Reports that said `verified` and now say `missing`. **The bug, named.**"""
    was = {one.key: one.state for one in before or ()}
    return sorted(
        one.report_id for one in after or ()
        if was.get(one.key) == tool.VERIFIED and one.state == tool.MISSING
    )


# The recheck: one report only, hours later, exactly as a slow Flipkart report
# comes back and is looked at again.
RECHECK = [r for r in API_HALF if r.id == "az_orders"] or API_HALF[:1]
AFTER = answered(lambda: tool.merge(
    BEFORE,
    tool.lines_for(RECHECK, WHOLE_FOLDER, TODAY, checked_on=TODAY, look_back_days=1),
))

check(
    "a recheck of one report turns no other report's verified into missing",
    answered(lambda: what_went_backwards(BEFORE, AFTER) == []),
)
# **AND SAID POSITIVELY AS WELL**, because "nothing went backwards" would also
# pass against a record that had come back empty.
check(
    "and every report is still verified for that day, by name and by count",
    answered(lambda: tool.how_it_stands(AFTER, YESTERDAY)[tool.VERIFIED] == len(EVERY)),
)
check(
    "and the untouched half's lines come through byte for byte",
    answered(lambda: [one for one in AFTER if one.report_id in {r.id for r in BROWSER_HALF}]
             == [one for one in BEFORE if one.report_id in {r.id for r in BROWSER_HALF}]),
)
check(
    "and a named other report still says which file it found",
    answered(lambda: tool.is_it_there(AFTER, "me_orders", YESTERDAY) == tool.VERIFIED),
)


# --------------------- the version that measured time, put back in and watched

def the_way_it_used_to_be(reports, uploaded_at, now, within=timedelta(minutes=5), checked_on=None):
    """**THE REFERENCE'S BROKEN CHECK, WRITTEN OUT SO IT CAN BE WATCHED FAILING.**

    "Was anything uploaded in the last few minutes." Nothing about a data date.
    This is not called by the product anywhere -- it lives in this file, and its
    only job is to make the check above go red so that check is known to work.
    """
    out = []
    for a_report in reports:
        when = uploaded_at.get(a_report.id)
        recent = when is not None and (now - when) <= within
        out.append(tool.Line(
            data_date=YESTERDAY,
            report_id=a_report.id,
            state=tool.VERIFIED if recent else tool.MISSING,
            file_name=file_name_for(a_report, YESTERDAY) if recent else None,
            file_size=4021 if recent else 0,
            checked_on=checked_on,
        ))
    return out


T0 = datetime(2026, 9, 10, 2, 30, 0)
UPLOADED = {r.id: T0 for r in EVERY}
OLD_BEFORE = answered(lambda: tool.merge((), the_way_it_used_to_be(EVERY, UPLOADED, T0, checked_on=TODAY)))
check(
    "the version that measured time also starts with everything verified",
    answered(lambda: tool.how_it_stands(OLD_BEFORE, YESTERDAY)[tool.VERIFIED] == len(EVERY)),
)

# Six minutes later, one report is fetched again and the whole check re-runs --
# which is exactly what a recheck mini-sync did.
SIX_MINUTES_ON = T0 + timedelta(minutes=6)
UPLOADED_AGAIN = dict(UPLOADED)
UPLOADED_AGAIN[RECHECK[0].id] = SIX_MINUTES_ON
OLD_AFTER = answered(lambda: tool.merge(
    OLD_BEFORE,
    the_way_it_used_to_be(EVERY, UPLOADED_AGAIN, SIX_MINUTES_ON, checked_on=TODAY),
))

WENT_BACKWARDS = answered(lambda: what_went_backwards(OLD_BEFORE, OLD_AFTER))
check(
    "and the same check, put to it, finds it wiping every other report -- red, as it must be",
    answered(lambda: len(WENT_BACKWARDS) == len(EVERY) - 1),
)
# **SAID POSITIVELY TOO.** A count going up is not on its own evidence that the
# wrong thing happened -- this names a day whose file is genuinely sitting in the
# folder and shows the old way calling it missing anyway.
check(
    "and it calls a day missing whose file is really in the folder",
    answered(lambda: tool.is_it_there(OLD_AFTER, "me_orders", YESTERDAY) == tool.MISSING
             and tool.what_it_says(
                 next(r for r in EVERY if r.id == "me_orders"), YESTERDAY,
                 WHOLE_FOLDER("me_orders")).state == tool.VERIFIED),
)
check(
    "which is the one thing the content-based version does not do to the same folder",
    answered(lambda: tool.is_it_there(AFTER, "me_orders", YESTERDAY) == tool.VERIFIED),
)


# ------------------------------------------- a half that did not run at all

ONLY_THE_NIGHTLY = answered(lambda: tool.merge(
    (), tool.lines_for(API_HALF, WHOLE_FOLDER, TODAY, checked_on=TODAY, look_back_days=1)))
check(
    "a night when only the nightly job ran writes lines for its own reports",
    answered(lambda: tool.is_it_there(ONLY_THE_NIGHTLY, "az_orders", YESTERDAY) == tool.VERIFIED),
)
# **AND THIS IS THE TIMING BUG ARRIVING BY THE OTHER DOOR, SHUT.** The extension
# never opened, so there is no line about its reports -- and no line is NOT
# `missing`. Read as missing, a seller who has not installed the extension yet
# would be told twenty-one files had failed to arrive.
check(
    "and says nothing at all about the half that did not run -- not that its files are missing",
    answered(lambda: tool.is_it_there(ONLY_THE_NIGHTLY, "me_orders", YESTERDAY) is None),
)
check(
    "so the count of missing for that day is nought, not twenty-one",
    answered(lambda: tool.how_it_stands(ONLY_THE_NIGHTLY, YESTERDAY)[tool.MISSING] == 0),
)
# And then the other half runs, hours later, and its lines simply appear.
BOTH = answered(lambda: tool.merge(
    ONLY_THE_NIGHTLY,
    tool.lines_for(BROWSER_HALF, WHOLE_FOLDER, TODAY, checked_on=TODAY, look_back_days=1)))
check(
    "and when the other half does run, its lines land beside them and change nothing else",
    answered(lambda: what_went_backwards(ONLY_THE_NIGHTLY, BOTH) == []
             and tool.how_it_stands(BOTH, YESTERDAY)[tool.VERIFIED] == len(EVERY)),
)


# ------------------- the third limit: two halves saving at the same moment
#
# **THE LIMIT WRITTEN AT THE TOP OF `manifest.py` IS DRIVEN HERE RATHER THAN
# ASSERTED.** It was written down once, elsewhere, that a lost write could only
# ever leave a line ABSENT and never `missing`. It is false, and it was the
# sentence that made one file with two writers read as safe.
#
# `only_mine` governs which lines a half may WRITE. It says nothing about which
# lines a half CARRIES FORWARD -- so the half whose save lands last also puts back
# its own copy of the other half's lines as they stood when it read them.

# The standing record: the extension checked on the 8th, `me_orders` was late, and
# it wrote `missing`. The file has since landed.
LATE_DAY = DAY("2026-09-08")
STOOD = answered(lambda: tool.merge((), [tool.Line(
    data_date=LATE_DAY, report_id="me_orders", state=tool.MISSING, checked_on=LATE_DAY)]))

# Both halves read that same record. The extension's own next run flips its own
# line to `verified`, because it asks the folder again rather than remembering.
THEIR_FOLDER = folder(me_orders=[a_real_file(
    next(r for r in EVERY if r.id == "me_orders"), LATE_DAY)])
THEIR_FLIP = answered(lambda: tool.merge(STOOD, tool.lines_for(
    [r for r in BROWSER_HALF if r.id == "me_orders"], THEIR_FOLDER, TODAY,
    checked_on=TODAY, look_back_days=(TODAY - LATE_DAY).days)))
check("the half that owns a late day flips its own line to verified when the file lands",
      answered(lambda: tool.is_it_there(THEIR_FLIP, "me_orders", LATE_DAY) == tool.VERIFIED))

# And the nightly job, which read the record BEFORE that flip, saves a moment
# later. Its save lands last, so what is in Drive is what it merged -- which
# carries the other half's line forward as IT read it.
OURS_LANDS_LAST = answered(lambda: tool.merge(STOOD, tool.lines_for(
    API_HALF, WHOLE_FOLDER, TODAY, checked_on=TODAY, look_back_days=1)))
check(
    "and a save that lands last puts back a stale missing over a file that is really there "
    "-- the third limit, driven, not asserted",
    answered(lambda: tool.is_it_there(OURS_LANDS_LAST, "me_orders", LATE_DAY) == tool.MISSING
             and tool.what_it_says(
                 next(r for r in EVERY if r.id == "me_orders"), LATE_DAY,
                 THEIR_FOLDER("me_orders")).state == tool.VERIFIED),
)
# **AND THE BOUND IS DRIVEN TOO**, because a limit stated without its bound reads
# worse than it is. No verdict is ever remembered, so the losing half asks the
# folder again on its next run and writes the same flip straight back.
HEALED = answered(lambda: tool.merge(OURS_LANDS_LAST, tool.lines_for(
    [r for r in BROWSER_HALF if r.id == "me_orders"], THEIR_FOLDER, TODAY,
    checked_on=TODAY, look_back_days=(TODAY - LATE_DAY).days)))
check("and the next run of the losing half puts it right again, in one night",
      answered(lambda: tool.is_it_there(HEALED, "me_orders", LATE_DAY) == tool.VERIFIED))
# **AND IT IS NOT ONE HALF MARKING THE OTHER'S LINES**, which is the thing
# `only_mine` really does stop. The stale line came from the record, not from the
# nightly job having an opinion about a report it does not fetch.
check(
    "and neither half can ever write a line of its own about the other's reports",
    answered(lambda: tool.only_mine(
        tool.lines_for([r for r in BROWSER_HALF if r.id == "me_orders"], THEIR_FOLDER, TODAY,
                       look_back_days=1),
        tool.mine(API, EVERY)) is not None),
)


# -------------------------------------------- a writer may not stray outside

MINE = answered(lambda: tool.mine(API, EVERY))
check("the nightly job owns exactly the reports on the API door",
      answered(lambda: sorted(MINE) == sorted(r.id for r in API_HALF)))
check("and it may write its own lines",
      answered(lambda: tool.only_mine(
          tool.lines_for(API_HALF, WHOLE_FOLDER, TODAY, look_back_days=1), MINE) is None))
STRAYED = answered(lambda: tool.only_mine(
    tool.lines_for(BROWSER_HALF, WHOLE_FOLDER, TODAY, look_back_days=1), MINE))
check("and is refused the moment it writes a line about a report it does not fetch",
      answered(lambda: STRAYED is not None))
check("and the refusal names the report rather than saying something went wrong",
      answered(lambda: "me_orders" in STRAYED))


# -------------------------------------------- a day nobody was owed anything

PUBLISHED = Report("az_settlements", "amazon", "Settlements", API, WHEN_THEY_PUBLISH_IT, "csv")
quiet = answered(lambda: tool.lines_for([PUBLISHED], folder(), TODAY, look_back_days=5))
check("a fortnight with nothing published writes no lines at all", answered(lambda: quiet == []))
came = answered(lambda: tool.lines_for(
    [PUBLISHED], folder(az_settlements=[a_real_file(PUBLISHED, YESTERDAY)]), TODAY, look_back_days=5))
check("but the day one did arrive is a line, and it says verified",
      answered(lambda: len(came) == 1 and came[0].state == tool.VERIFIED))
ASKED = Report("fk_extra", "flipkart", "Only when asked", BROWSER, ONLY_WHEN_ASKED, "csv")
check("a report that only runs when asked is not in the manifest at all",
      answered(lambda: tool.lines_for([ASKED], folder(), TODAY) == []))

# **AND THE DAY BOARD DECIDES THIS THE SAME WAY.** Two places deciding what is
# owed is two answers to one question; this holds them to each other rather than
# trusting that they were written to agree.
board_rows = answered(lambda: board.rows_for([PUBLISHED], folder(), TODAY, look_back_days=5))
check("and the day board says the same about a day nothing was published on",
      answered(lambda: (board_rows == []) == (quiet == [])))
board_daily = answered(lambda: board.rows_for([ORDERS], got, TODAY, look_back_days=2))
mani_daily = answered(lambda: tool.lines_for([ORDERS], got, TODAY, look_back_days=2))
check("and the two cover the same days for an ordinary daily report",
      answered(lambda: [r.data_date for r in board_daily] == [one.data_date for one in mani_daily]))


# ---------------------------------------------------------------- the bytes

ROUND_TRIP = answered(lambda: tool.read(tool.write(BEFORE)))
check("what is written comes back the same", answered(lambda: tuple(ROUND_TRIP) == tuple(BEFORE)))
check("and it is written the same way twice", answered(lambda: tool.write(BEFORE) == tool.write(list(reversed(list(BEFORE))))))
check("no record at all is an empty record, which is an ordinary first night",
      answered(lambda: tool.read(None) == () and tool.read(b"") == ()))
# **AND SOMETHING BROKEN IS NOT AN EMPTY RECORD.** Read as empty, it would tell
# every downstream reader that nothing has ever landed.
check("a record that is there and cannot be read refuses rather than reading as empty",
      answered(lambda: _refused(lambda: tool.read(b"{ this is not json"))))
check("a record written in another shape refuses rather than reading the fields it recognises",
      answered(lambda: _refused(lambda: tool.read(b'{"shape": 99, "lines": []}'))))
check("a line whose day is not a day refuses",
      answered(lambda: _refused(lambda: tool.read(
          b'{"shape": 1, "lines": [{"dataDate": "the 9th", "reportId": "az_orders", "state": "missing"}]}'))))
check("a line that says verified and names no file refuses",
      answered(lambda: _refused(lambda: tool.read(
          b'{"shape": 1, "lines": [{"dataDate": "2026-09-09", "reportId": "az_orders", '
          b'"state": "verified", "fileName": "", "fileSize": 10}]}'))))
# **A SIZE THAT IS NOT A NUMBER REFUSES AS `Damaged`, WHICH IS THE ONE KIND THIS
# FUNCTION DOCUMENTS.** Left to `int` it raised `ValueError` straight past the
# contract, and a reader catching `Damaged` -- which is what `one_tick` does for
# the run's own memory -- would not have caught it. `_refused` asks the kind, so
# anything else coming out of here is red as well.
check("a line whose size is not a number refuses, and refuses as the one kind this file names",
      answered(lambda: _refused(lambda: tool.read(
          b'{"shape": 1, "lines": [{"dataDate": "2026-09-09", "reportId": "az_orders", '
          b'"state": "missing", "fileName": "", "fileSize": "lots"}]}'))))
# **TWO LINES FOR ONE DAY IN THE FILE ON DISK REFUSE, in the same words `merge`
# uses about a batch.** Accepted, they gave one file two answers: `is_it_there`
# took the first and said `verified`, `merge` kept the last and wrote back
# `missing`, and one of the two lines went with nothing said.
check("two lines for one day and one report in the stored file refuse rather than one being picked",
      answered(lambda: _refused(lambda: tool.read(
          b'{"shape": 1, "lines": [{"dataDate": "2026-09-09", "reportId": "az_orders", '
          b'"state": "verified", "fileName": "amazon_az_orders_2026-09-09.csv", "fileSize": 12}, '
          b'{"dataDate": "2026-09-09", "reportId": "az_orders", "state": "missing"}]}'))))
check("a line saying something nobody recognises refuses",
      answered(lambda: _refused(lambda: tool.read(
          b'{"shape": 1, "lines": [{"dataDate": "2026-09-09", "reportId": "az_orders", "state": "probably"}]}'))))
# **A REAL ONE READS.** Every check above is a refusal, and a refusal that fired
# on everything would pass all of them.
check("and a well-formed record really does read back",
      answered(lambda: len(tool.read(
          b'{"shape": 1, "lines": [{"dataDate": "2026-09-09", "reportId": "az_orders", '
          b'"state": "verified", "fileName": "amazon_az_orders_2026-09-09.csv", "fileSize": 12}]}')) == 1))


# ------------------------------------------------- what downstream asks it

check("a reader asks one report and one day and gets one word",
      answered(lambda: tool.is_it_there(BEFORE, "fk_orders", YESTERDAY) == tool.VERIFIED))
check("a day nobody has checked answers nothing, and nothing is not missing",
      answered(lambda: tool.is_it_there(BEFORE, "fk_orders", DAY("2020-01-01")) is None))
check("a report nobody has heard of answers nothing rather than missing",
      answered(lambda: tool.is_it_there(BEFORE, "not_a_report", YESTERDAY) is None))

# **A LATE FILE FLIPS ITS OWN DAY BACK.** A `missing` line is not final: the
# answer is asked of the folder again rather than remembered, so the day a slow
# report finally lands, the next run of that half says so without anything having
# to go and delete a line.
LATE_BEFORE = answered(lambda: tool.merge((), tool.lines_for([ORDERS], folder(), TODAY, look_back_days=1)))
LATE_AFTER = answered(lambda: tool.merge(
    LATE_BEFORE, tool.lines_for([ORDERS], got, TODAY, look_back_days=1)))
check("a day that was missing and has since arrived flips to verified in place",
      answered(lambda: tool.is_it_there(LATE_BEFORE, "az_orders", YESTERDAY) == tool.MISSING
               and tool.is_it_there(LATE_AFTER, "az_orders", YESTERDAY) == tool.VERIFIED))
check("and there is still only one line about that day",
      answered(lambda: len([one for one in LATE_AFTER if one.key == (YESTERDAY, "az_orders")]) == 1))


# **AND NOTHING ABOVE ENDED BY THROWING RATHER THAN BY ANSWERING.** Answering
# with nothing keeps the run alive; this is what stops a check phrased as "this
# is NOT there" going green because there was nothing to look in.
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)


EXPECTED = 66
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
