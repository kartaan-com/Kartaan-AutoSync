"""Checks for the day board and the quiet alarm.

**THE MOST IMPORTANT CHECK IN THIS PACKAGE IS IN THIS FILE**, and it is the one
the reference could not have passed: `nothing_ran`. Two of the last three days
produced nothing at all, and not one thing anywhere said so -- because every alarm
it had hung off a report failing, and when nothing runs, no report fails.

Run: python autosync/board_checks.py
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import board as tool  # noqa: E402
from landing import Arrived  # noqa: E402
from reports import BROWSER, DAILY, ONLY_WHEN_ASKED, WHEN_THEY_PUBLISH_IT, Report  # noqa: E402

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
    red -- so the measurement reads "noticed" while saying nothing about whether
    any check here is any good. Worked out in here, a call that throws answers
    with nothing, that one check goes red by itself, and the rest still run.

    Nothing is never a pass: every check reads its answer for truth, so nothing
    always fails. That is what makes this safe to put round every one of them.
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


DAY = lambda s: date.fromisoformat(s)  # noqa: E731
TODAY = DAY("2026-08-27")

ORDERS = Report("me_orders", "meesho", "Meesho orders", BROWSER, DAILY, "csv")
ADS = Report("fk_ads_daily", "flipkart", "Flipkart ads by day", BROWSER, DAILY, "csv")
ADS_FSN = Report("fk_ads_fsn", "flipkart", "Flipkart ads by product", BROWSER, DAILY, "csv",
                 depends_on=("fk_ads_daily",))
KEYWORDS = Report("fk_keywords", "flipkart", "Flipkart keywords", BROWSER, DAILY, "csv", needs_a_person=True)
ASKED = Report("fk_extra", "flipkart", "Only when asked", BROWSER, ONLY_WHEN_ASKED, "csv")


def folder(**by_report):
    return lambda report_id: by_report.get(report_id, [])


# ------------------------------------------------------- arrived, or missing

got = folder(me_orders=[Arrived("meesho_me_orders_2026-08-26.csv", 4021)])
rows = tool.rows_for([ORDERS], got, TODAY, look_back_days=2)
by_day = {r.data_date: r for r in rows}
check("a day whose file is really there says arrived", answered(lambda: by_day[DAY("2026-08-26")].state == tool.ARRIVED))
check("and carries the file's name and size", answered(lambda: by_day[DAY("2026-08-26")].file_name.endswith(".csv") and by_day[DAY("2026-08-26")].file_size == 4021))
check("a day with no file says missing", answered(lambda: by_day[DAY("2026-08-25")].state == tool.MISSING))
check("one row per report per data date, not per run", answered(lambda: len(rows) == 2))
check("oldest day first", answered(lambda: rows[0].data_date < rows[-1].data_date))
check("a report that only runs when asked is not on the board at all", answered(lambda: tool.rows_for([ASKED], folder(), TODAY) == []))

# **ARRIVAL IS ASKED OF THE FILE, NEVER OF A JOB'S OPINION.** There is nowhere in
# this call to pass what a job believed -- which is the property, not an accident.
check(
    "the board takes what is in the folder, and has nowhere to be told what a job thought",
    answered(lambda: "arrivals" in tool.rows_for.__code__.co_varnames and "succeeded" not in tool.rows_for.__code__.co_varnames),
)

# **PRESENT AND EMPTY IS NOT ARRIVED.** The reference recorded a truncated file as
# Verified because a name existed.
empty = folder(me_orders=[Arrived("meesho_me_orders_2026-08-26.csv", 0)])
check(
    "a file of nothing does not count as arrived",
    answered(lambda: {r.data_date: r for r in tool.rows_for([ORDERS], empty, TODAY, look_back_days=1)}[DAY("2026-08-26")].state == tool.EMPTY),
)
# A real file landing later beats an empty one for the same day.
both = folder(me_orders=[Arrived("a_2026-08-26.csv", 0), Arrived("b_2026-08-26.csv", 900)])
check(
    "and a real file for the same day beats the empty one",
    answered(lambda: {r.data_date: r for r in tool.rows_for([ORDERS], both, TODAY, look_back_days=1)}[DAY("2026-08-26")].state == tool.ARRIVED),
)

# --------------------------------------------------- a reason is never invented

no_reason = tool.rows_for([ORDERS], folder(), TODAY, look_back_days=1)
check("a missing day with nothing recorded says nothing about why", answered(lambda: no_reason[0].why_not is None))
with_reason = tool.rows_for(
    [ORDERS], folder(), TODAY, look_back_days=1,
    reason_for=lambda r: "Download Orders Data button not found" if r == "me_orders" else None,
)
check("and a missing day with a recorded reason carries it", answered(lambda: with_reason[0].why_not == "Download Orders Data button not found"))

# ------------------------------------------------- one cause is one problem

blocked_rows = tool.rows_for([ADS_FSN], folder(), TODAY, look_back_days=1, failed_ids=["fk_ads_daily"])
check("a report waiting on another says it is blocked", answered(lambda: blocked_rows[0].state == tool.BLOCKED))
check("and names what it is waiting on", answered(lambda: "fk_ads_daily" in blocked_rows[0].why_not))
check(
    "the one that actually failed reports itself, not a blockage",
    answered(lambda: tool.rows_for([ADS], folder(), TODAY, look_back_days=1, failed_ids=["fk_ads_daily"])[0].state == tool.MISSING),
)

# ------------------------------------ a report that needs somebody is not a failure

person = tool.rows_for([KEYWORDS], folder(), TODAY, look_back_days=1)
check("a report that cannot run unattended says so rather than reading as a failure", answered(lambda: person[0].state == tool.NEEDS_A_PERSON))
check("and is not counted as a problem to chase", answered(lambda: person[0].is_a_problem is False))

# ------------------------------------------- files nothing can ever match to a day

strays = folder(me_payments=[
    Arrived("meesho_payments.xlsx", 16000),
    Arrived("meesho_payments (1).xlsx", 20000),
    Arrived("meesho_me_payments_2026-08-24.zip", 15000),
])
PAY = Report("me_payments", "meesho", "Meesho payments", BROWSER, DAILY, "zip")
found = tool.files_nothing_can_find([PAY], strays)
check("files with no date in the name are named as their own problem", answered(lambda: len(found["me_payments"]) == 2))
check("and the properly named one is not among them", answered(lambda: "meesho_me_payments_2026-08-24.zip" not in found["me_payments"]))
check("a folder with nothing wrong reports nothing", answered(lambda: tool.files_nothing_can_find([ORDERS], got) == {}))

# ------------------------------------------------ NOTHING RAN -- rule 2

# **THE REAL CASE.** The last run was 2026-08-25; today is the 27th.
quiet = tool.nothing_ran([DAY("2026-08-24"), DAY("2026-08-25")], TODAY)
check("two days with nothing running is an alarm in its own right", answered(lambda: quiet is not None))
check("and it says how long", answered(lambda: quiet.days_quiet == 2))
check("and when the last run was", answered(lambda: quiet.last_run_on == DAY("2026-08-25")))
# **THE SENTENCE MATTERS: it has to say WHY nothing failed.** A person looking at a
# board of missing days and no failures concludes the board is broken.
check(
    "and it says that nothing failed because nothing was asked for",
    answered(lambda: "no report has been asked for" in quiet.message),
)
check("a run yesterday is not an alarm", answered(lambda: tool.nothing_ran([DAY("2026-08-26")], TODAY) is None))
check("a run today is certainly not", answered(lambda: tool.nothing_ran([TODAY], TODAY) is None))
check("how quiet is too quiet can be set", answered(lambda: tool.nothing_ran([DAY("2026-08-25")], TODAY, quiet_days_allowed=5) is None))
# Never having run is a different sentence, not a day count from a date that does
# not exist.
never = tool.nothing_ran([], TODAY)
check("never having run at all is its own answer", answered(lambda: never is not None and never.last_run_on is None))
check("and does not report a number of days", answered(lambda: never.days_quiet == 0))
check("and says so in words", answered(lambda: "ever run" in never.message))

# ------------------------------------------------------ what to tell somebody

rows = tool.rows_for([ORDERS], folder(), TODAY, look_back_days=10)
said = tool.what_to_say(rows, quiet, found)
# **THE QUIET ALARM COMES FIRST.** A board full of missing days is the SYMPTOM of
# nothing running; leading with the symptom sends a person to fix twenty reports.
check("the quiet alarm is said first, above everything", answered(lambda: said[0] == quiet.message))
check("the unreachable files are said too", answered(lambda: any("no date in the name" in s for s in said)))
check("and the overdue days after that", answered(lambda: any("days late" in s for s in said)))
check(
    "an overdue day with no recorded reason does not have one invented for it",
    answered(lambda: all(not s.endswith("-- None") for s in said)),
)
# Nothing wrong at all says nothing at all.
good = folder(me_orders=[Arrived(f"meesho_me_orders_2026-08-{d}.csv", 900) for d in range(17, 27)])
check(
    "a day when everything arrived and something ran says nothing",
    answered(lambda: tool.what_to_say(tool.rows_for([ORDERS], good, TODAY, look_back_days=9), None, {}) == []),
)


# ------------------------------------------------- the ends nothing else reached

# Both records are frozen: a board anything can edit underneath the reader is not
# a board.
def refuses_edit(thing, field, value):
    try:
        setattr(thing, field, value)
    except AttributeError:
        return True
    return False


check("a board row cannot be edited after it is made", answered(lambda: refuses_edit(rows[0], "state", tool.ARRIVED)))
check("and neither can the quiet alarm", answered(lambda: refuses_edit(quiet, "days_quiet", 99)))
check("a row that says nothing about asking a person is taken as not asking", answered(lambda: tool.Row(TODAY, "x", True, tool.MISSING).ask_a_person is False))

# **A ROW CARRIES HOW LATE IT IS.** Without it every overdue row reads as one day
# old and the worst-first ordering has nothing to sort on.
old_rows = tool.rows_for([ORDERS], folder(), TODAY, look_back_days=6)
check("a row says how many days late its day is", answered(lambda: old_rows[0].days_late == 6))
check("and the newest owed day is one", answered(lambda: old_rows[-1].days_late == 1))

# **AN OLD DAY THAT ARRIVED IS NOT SOMETHING TO CHASE.** Without the second half
# of that test, every report would ask for a person about days it already has.
all_there = folder(me_orders=[Arrived(f"meesho_me_orders_2026-08-{d}.csv", 900) for d in range(20, 27)])
arrived_old = tool.rows_for([ORDERS], all_there, TODAY, look_back_days=6)
check("a day that arrived never asks for a person, however old it is", answered(lambda: not any(r.ask_a_person for r in arrived_old)))
check("and every one of those days really did arrive", answered(lambda: all(r.state == tool.ARRIVED for r in arrived_old)))

# **TWO REPORTS ARE INTERLEAVED BY DAY, not listed one report at a time.**
two = tool.rows_for([ORDERS, ADS], folder(), TODAY, look_back_days=1)
check("two reports on the board are ordered by day, then by report", answered(lambda: [r.report_id for r in two] == ["fk_ads_daily", "me_orders"]))

# **THE FIRST FILE FOR A DAY WINS UNLESS IT WAS EMPTY.** Two real files for one
# day is a repeat, not a reason to swap; only an empty one gives way.
twice = folder(me_orders=[Arrived("first_2026-08-26.csv", 900), Arrived("second_2026-08-26.csv", 800)])
kept = {r.data_date: r for r in tool.rows_for([ORDERS], twice, TODAY, look_back_days=1)}[DAY("2026-08-26")]
check("a second real file for the same day does not replace the first", answered(lambda: kept.file_name == "first_2026-08-26.csv"))
two_empty = folder(me_orders=[Arrived("first_2026-08-26.csv", 0), Arrived("second_2026-08-26.csv", 0)])
still_empty = {r.data_date: r for r in tool.rows_for([ORDERS], two_empty, TODAY, look_back_days=1)}[DAY("2026-08-26")]
check("and two empty ones are still empty", answered(lambda: still_empty.state == tool.EMPTY))

# **THE QUIET MESSAGE NAMES THE DAY IT LAST RAN**, because that is the fact
# somebody acts on -- "it has been quiet a while" is not something anyone can use.
check("the quiet alarm names the last day anything ran", answered(lambda: "2026-08-25" in quiet.message))
check("and how many days it has been", answered(lambda: "2 days" in quiet.message))

# **ONLY PROBLEMS THAT ARE ALSO OVERDUE ARE SAID.** Both halves matter: a missing
# day from this morning is not worth waking anybody, and an old day that ARRIVED
# is not a problem at all.
fresh = tool.rows_for([ORDERS], folder(), TODAY, look_back_days=1)
check("a day missing since this morning is not said", answered(lambda: tool.what_to_say(fresh, None, {}) == []))
check(
    "and an old day that arrived is not said either",
    answered(lambda: tool.what_to_say(arrived_old, None, {}) == []),
)
check(
    "while an old day that is genuinely missing is",
    answered(lambda: len(tool.what_to_say(old_rows, None, {})) > 0),
)


# **AND NOTHING ABOVE ENDED BY THROWING RATHER THAN BY ANSWERING.** Answering
# with nothing keeps the run alive; this is what stops a check phrased as "this
# word is NOT in what it said" going green because there was nothing to look in.
# ------------------- nothing is owed on a day nothing was published (R2#7)

PUBLISHED = tool.Report("az_settlements", "amazon", "Settlements", "api",
                        WHEN_THEY_PUBLISH_IT, "csv")
# **AMAZON PUBLISHES SETTLEMENTS ON ITS OWN CYCLE -- roughly a fortnight.**
# Every day between them used to read as missing, the clock ticked up, and the
# alarm could never be cleared, because nothing was ever going to arrive for
# that day. **An alarm nobody can clear is an alarm everybody mutes.**
quiet_rows = answered(lambda: tool.rows_for([PUBLISHED], lambda _r: [], TODAY))
check("a fortnight with nothing published puts nothing on the board",
      quiet_rows == [])
# **AND SO NOTHING IS LATE, which is what the alarm was built from.**
check("and nothing about it is late", all(not row.ask_a_person for row in quiet_rows))
# **BUT WHAT DID ARRIVE IS STILL ON IT.** Left off entirely, a stream that
# stopped for good would look exactly like one nobody has published lately.
landed = Arrived("amazon_az_settlements_2026-08-25.csv", 900)
came_rows = answered(lambda: tool.rows_for([PUBLISHED], lambda _r: [landed], TODAY))
check("and the day one did arrive is still a row", len(came_rows) == 1)
check("and it reads as arrived", came_rows[0].state == tool.ARRIVED)
# And a report that really is daily still reports its missing days, so this is
# about the one kind rather than about the board giving up.
EVERY_DAY = tool.Report("az_orders", "amazon", "Orders", "api", DAILY, "csv")
check("while a daily report still says which days did not arrive",
      len(answered(lambda: tool.rows_for([EVERY_DAY], lambda _r: [], TODAY))) > 1)

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)


EXPECTED = 55
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
