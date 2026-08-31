"""Checks for what gets told to somebody.

**THE CENTRAL ONE: an alarm is keyed to its CONDITION, not to each occurrence.**
The reference wrote a fresh record every day for anything that stayed true, so a
report broken for three weeks produced twenty-one identical messages and the real
ones drowned. Every case below is written to make that impossible.

**AND THE LOUDEST IS ALWAYS "nothing is being fetched".** A board full of missing
days is the SYMPTOM of nothing running; sent as twenty separate "report X is late"
messages it sends a person to fix twenty reports when the fetcher is not running
at all -- which is what a month of the reference's summaries did.

Run: python autosync/alarms_checks.py
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import alarms as tool  # noqa: E402
from board import BLOCKED, EMPTY, MISSING, ARRIVED, NothingRan, Row  # noqa: E402

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


def _cannot_edit(thing, field, value):
    """A frozen record refuses with FrozenInstanceError, which is an
    AttributeError -- named, so a refusal is told apart from the code falling
    over some other way."""
    try:
        setattr(thing, field, value)
    except AttributeError:
        return True
    return False


def late(report_id, day, days_late, why=None, state=MISSING):
    return Row(
        data_date=DAY(day), report_id=report_id, expected=True, state=state,
        why_not=why, days_late=days_late, ask_a_person=True,
    )


QUIET = NothingRan(last_run_on=DAY("2026-08-25"), days_quiet=2,
                   message="Nothing has run for 2 days -- the last run was 2026-08-25. "
                           "No report has failed, because no report has been asked for.")

# ------------------------------------------------------- the loudest first

both = tool.alarms_for([late("me_orders", "2026-08-20", 7)], QUIET)
check("nothing running is an alarm", answered(lambda: any(a.key == tool.NOTHING_RAN for a in both)))
# **IT COMES FIRST, ABOVE EVERY LATE REPORT.**
check("and it is first, above the late reports", answered(lambda: both[0].key == tool.NOTHING_RAN))
check("and it is its own loudness, above 'somebody needs to act'", answered(lambda: both[0].loudness == tool.STOP))
check("while a late report is the ordinary loud", answered(lambda: both[1].loudness == tool.ACT))
check("its headline says how long", answered(lambda: "2 days" in both[0].headline))
# **THE MEANING SAYS WHY NOTHING FAILED**, or a person concludes the board is broken.
check("and the meaning says nothing failed because nothing was asked for",
      answered(lambda: "no report has been asked for" in both[0].what_it_means))

# Never having run at all reads differently -- there is no day count to give.
never = tool.alarms_for([], NothingRan(None, 0, "Nothing has ever run."))
check("never having run says so without a number of days", answered(lambda: never[0].headline == "Nothing is being fetched."))
check("and does not claim a count of days", answered(lambda: "0 days" not in never[0].headline))

check("a quiet day with nothing wrong raises nothing at all", answered(lambda: tool.alarms_for([], None) == []))

# ------------------------------------- ONE ALARM PER REPORT, NOT PER DAY

# **THE FAULT THIS EXISTS FOR.** Twenty-one days broken is one problem.
many_days = [late("fk_views", f"2026-08-{d:02d}", 27 - d) for d in range(1, 22)]
one = tool.alarms_for(many_days, None)
check("twenty-one broken days of one report is ONE alarm", answered(lambda: len(one) == 1))
check("and it names the report", answered(lambda: "fk_views" in one[0].headline))
# **THE WORST DAY IS THE ONE REPORTED**, because that is what says how bad it is.
check("reported with the oldest day, not the newest", answered(lambda: "26 days" in one[0].headline))
check("and it says how many days are missing altogether", answered(lambda: "21 days" in one[0].what_it_means))
check("and which the oldest is", answered(lambda: "2026-08-01" in one[0].what_it_means))

# Two reports are two alarms.
two = tool.alarms_for([late("fk_views", "2026-08-01", 26), late("me_orders", "2026-08-20", 7)], None)
check("two broken reports are two alarms", answered(lambda: len(two) == 2))
check("keyed apart from each other", answered(lambda: two[0].key != two[1].key))
check("and each keyed on the report, not the day",
      answered(lambda: {a.key for a in two} == {"autosync::late::fk_views", "autosync::late::me_orders"}))

# ------------------------------------------- a reason is never invented

with_reason = tool.alarms_for([late("me_orders", "2026-08-20", 7, why="Download Orders Data button not found")], None)
check("a recorded reason is carried into the alarm", answered(lambda: "button not found" in with_reason[0].what_it_means))
without = tool.alarms_for([late("me_orders", "2026-08-20", 7)], None)
check("and one with no reason recorded says nothing about why", answered(lambda: "None" not in without[0].what_it_means))
check("and does not trail off after the date", answered(lambda: without[0].what_it_means.endswith("2026-08-20.")))

# ---------------------------------- only real problems, only overdue ones

check("a day that arrived raises nothing",
      answered(lambda: tool.alarms_for([Row(DAY("2026-08-01"), "me_orders", True, ARRIVED, days_late=26)], None) == []))
fresh = Row(DAY("2026-08-26"), "me_orders", True, MISSING, days_late=1, ask_a_person=False)
check("and a day missing since this morning raises nothing", answered(lambda: tool.alarms_for([fresh], None) == []))
check("a blocked report still raises, because somebody has to unblock it",
      answered(lambda: len(tool.alarms_for([late("fk_ads_fsn", "2026-08-20", 7, state=BLOCKED)], None)) == 1))
check("and so does one that arrived empty",
      answered(lambda: len(tool.alarms_for([late("me_orders", "2026-08-20", 7, state=EMPTY)], None)) == 1))

# --------------------------------------- files nothing can match to a day

stray = tool.alarms_for([], None, {"me_payments": ["meesho_payments.xlsx", "meesho_payments (1).xlsx"]})
check("files with no date in the name raise their own alarm", answered(lambda: len(stray) == 1))
check("keyed to the report they are stuck in", answered(lambda: stray[0].key == "autosync::unreachable::me_payments"))
check("saying how many", answered(lambda: "2 file" in stray[0].headline))
check("and naming them, so they can be found", answered(lambda: "meesho_payments.xlsx" in stray[0].what_it_means))
check("and saying what to do about it", answered(lambda: "Renaming them" in stray[0].what_it_means))
# Seven of them really existed; a long list must not become the whole message.
seven = tool.alarms_for([], None, {"me_payments": [f"meesho_payments ({n}).xlsx" for n in range(7)]})
check("a long list is cut short rather than filling the message", answered(lambda: "..." in seven[0].what_it_means))

# ------------------------------------------------- the same list every time

facts = [late("me_orders", "2026-08-20", 7), late("fk_views", "2026-08-01", 26)]
check("the same facts give the same list, every time",
      answered(lambda: [a.key for a in tool.alarms_for(facts, QUIET)] == [a.key for a in tool.alarms_for(facts, QUIET)]))
# **AND ORDER DOES NOT DEPEND ON THE ORDER THE ROWS CAME IN**, or "has this
# changed since I looked" cannot be asked at all.
check("and the order does not depend on the order the rows arrived in",
      answered(lambda: [a.key for a in tool.alarms_for(facts, QUIET)] == [a.key for a in tool.alarms_for(list(reversed(facts)), QUIET)]))

# -------------------------------------------------- what changed since last

now = tool.alarms_for([late("me_orders", "2026-08-20", 7)], None)
first = tool.what_changed([], now)
check("everything is new the first time", answered(lambda: len(first.raised) == 1 and first.still == ()))
check("and there is something to send", answered(lambda: first.anything_to_send is True))

again = tool.what_changed(["autosync::late::me_orders"], now)
check("the same problem next time is not raised again", answered(lambda: again.raised == ()))
check("it is still standing", answered(lambda: len(again.still) == 1))
# **NOTHING IS SENT WHEN NOTHING MOVED.** Twenty-six nights of the same list is
# how everybody learns to ignore the channel.
check("and there is nothing to send", answered(lambda: again.anything_to_send is False))
check("so nothing goes out", answered(lambda: tool.to_send(again) == []))

# **AN ALARM CLEARS BECAUSE THE CONDITION WENT.**
fixed = tool.what_changed(["autosync::late::me_orders"], [])
check("a problem that has gone is cleared", answered(lambda: fixed.cleared == ("autosync::late::me_orders",)))
check("and that is worth sending", answered(lambda: fixed.anything_to_send is True))
# **A FIX IS SAID OUT LOUD.** Only ever hearing bad news teaches people the
# channel is bad news, and then nobody reads it.
check("and the message says it is fixed", answered(lambda: any(line.startswith("Fixed:") for line in tool.to_send(fixed))))

# There is nothing here to dismiss one with, and that is deliberate.
check("nothing here can dismiss an alarm without the problem going",
      answered(lambda: not any("dismiss" in name for name in dir(tool))))

mixed = tool.what_changed(["autosync::late::gone"], tool.alarms_for([late("me_orders", "2026-08-20", 7)], None))
check("one going and another arriving are both reported", answered(lambda: len(mixed.raised) == 1 and len(mixed.cleared) == 1))
lines = tool.to_send(mixed)
check("and both are in what goes out", answered(lambda: len(lines) == 2))
check("with the new one first", answered(lambda: "me_orders" in lines[0]))

# The cleared list is settled, so the same facts give the same answer.
twice = tool.what_changed(["b", "a"], [])
check("cleared keys come out in a settled order", answered(lambda: twice.cleared == ("a", "b")))

# ------------------------------------------------------------ the record

alarm = now[0]
check("an alarm cannot be edited after it is made", answered(lambda: _cannot_edit(alarm, "headline", "x")))
check("it carries a headline short enough for a phone", answered(lambda: len(alarm.headline) < 80))
check("and a meaning that says more than the headline", answered(lambda: len(alarm.what_it_means) > len(alarm.headline)))


# ------------------------------------------- the ends nothing else reached

# **EVERY ALARM HERE NEEDS SOMEBODY TO DO SOMETHING**, and says so. A "know about
# it" alarm exists as a loudness for later; nothing raises one yet, and if that
# ever changes it must be a deliberate choice rather than a default sliding.
check("the quiet alarm needs somebody to act", answered(lambda: both[0].needs_action is True))
check("and so does a late report", answered(lambda: both[1].needs_action is True))
check("and so does a folder of unreachable files", answered(lambda: stray[0].needs_action is True))
check("and every alarm raised at all does", answered(lambda: all(a.needs_action for a in tool.alarms_for(many_days, QUIET, {"me_payments": ["x.xlsx"]}))))
# The default is to need action, so a new kind of alarm is loud until somebody
# decides otherwise -- the safe direction.
check("an alarm made without saying needs somebody by default",
      answered(lambda: tool.Alarm("k", tool.KNOW, "h", "m").needs_action is True))

# The unreachable-files message says what is actually wrong with them.
check("the unreachable message says no reader can find them", answered(lambda: "no reader can find them" in stray[0].what_it_means))
check("and that it is because the names carry no date", answered(lambda: "names carry no date" in stray[0].what_it_means))

# **HOW MANY DAYS ARE COUNTED -- and all three arms of that count matter.**
mixed_rows = [
    late("fk_views", "2026-08-01", 26),
    late("fk_views", "2026-08-02", 25),
    late("me_orders", "2026-08-03", 24),                                    # a different report
    Row(DAY("2026-08-04"), "fk_views", True, ARRIVED, days_late=23),        # not a problem
    Row(DAY("2026-08-05"), "fk_views", True, MISSING, days_late=22, ask_a_person=False),  # not overdue
]
counted = [a for a in tool.alarms_for(mixed_rows, None) if a.key == "autosync::late::fk_views"][0]
check("the count is only this report's days", answered(lambda: "2 days" in counted.what_it_means))
check("a day of another report is not counted into it", answered(lambda: "3 days" not in counted.what_it_means))
check("nor a day that arrived", answered(lambda: "4 days" not in counted.what_it_means))
check("and the other report gets its own alarm", answered(lambda: any(a.key == "autosync::late::me_orders" for a in tool.alarms_for(mixed_rows, None))))
# One day reads as a day, not as days.
single = tool.alarms_for([late("me_orders", "2026-08-20", 7)], None)[0]
check("one missing day says day, not days", answered(lambda: "1 day of" in single.what_it_means))

# What changed is frozen too.
check("what changed cannot be edited after it is worked out",
      answered(lambda: _cannot_edit(tool.what_changed([], []), "cleared", ("x",))))


# **AND NOTHING ABOVE ENDED BY THROWING RATHER THAN BY ANSWERING.** Answering
# with nothing keeps the run alive; this is what stops a check phrased as "this
# word is NOT in what it said" going green because there was nothing to look in.
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)


EXPECTED = 63
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
