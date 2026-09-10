"""Checks for the clock.

**THE ONE THAT MATTERS MOST: a run that died must not stop every later one for
ever.** A record saying "still going" is exactly what a killed run leaves behind,
and reading it as a run in progress is how a system stops by itself with nothing
saying so. The reference had four runs vanish mid-flight in twenty-six days.

Run: python autosync/clock_checks.py
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import clock as tool  # noqa: E402

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


# **THE MOMENT EVERY RULE BELOW IS ASKED AT IS THE ONE TICK OF THE DAY**, four
# in the afternoon in his time -- hand-typed, not read off the clock it checks.
# It used to be half past ten in the morning, which stopped being a moment any
# tick arrives at on 2026-09-10.
AT = datetime(2026, 8, 28, 16, 0)

# ---------------------------------------------- whose day it is

# **HIS DAY, NOT THE MACHINE'S.** A run on a clock somewhere else fetches
# "yesterday" while it is still today for him, and the platform has nothing to
# give. The reference's quota meter reset seven hours early for exactly this.
check("the clock is India's, said out loud rather than assumed",
      answered(lambda: (tool.HOURS_AHEAD_OF_UTC, tool.MINUTES_AHEAD_OF_UTC)) == (5, 30))
check("the machine's clock is told as his, and this is the ONE place that happens",
      answered(lambda: tool.his_clock(datetime(2026, 8, 28, 0, 0))) == datetime(2026, 8, 28, 5, 30))

# **THE DAY IT FETCHES IS YESTERDAY IN HIS DAY, NOT IN GREENWICH.**
check("a run in the morning fetches yesterday",
      answered(lambda: tool.the_day_to_fetch(datetime(2026, 8, 28, 10, 30))) == date(2026, 8, 27))
# **THE MOMENT HANDED IN IS ALREADY HIS, so the turn happens at HIS midnight.**
check("a run just after his midnight fetches the day that just ended",
      answered(lambda: tool.the_day_to_fetch(datetime(2026, 8, 28, 0, 10))) == date(2026, 8, 27))
check("and ten minutes before it, the day before that",
      answered(lambda: tool.the_day_to_fetch(datetime(2026, 8, 27, 23, 50))) == date(2026, 8, 26))
# **AND IT DOES NOT CONVERT AGAIN.** Converted twice, a moment is five and a half
# hours wrong, and for those hours every night the wrong day would be asked for
# -- which is the quietest way there is to lose a day.
check("the day is not shifted a second time",
      answered(lambda: tool.the_day_to_fetch(datetime(2026, 8, 28, 21, 0))) == date(2026, 8, 27))

# ---------------------------------------------- whether to run at all

check("with nothing before it, a run may start",
      answered(lambda: tool.why_not_now(None, AT)) is None)
check("and with a record that has never run",
      answered(lambda: tool.why_not_now(tool.LastRun(), AT)) is None)
# **A RECORD THAT SAYS IT FINISHED AND NEVER SAYS IT STARTED IS NOT A RUN.** It
# is a half-written record, and reading it as a finished run would hold the next
# one back for a day on the strength of something that never happened.
check("a record that finished without ever starting is not treated as a run",
      answered(lambda: tool.why_not_now(tool.LastRun(finished=AT - timedelta(minutes=5)), AT))
      is None)

# **TWO AT ONCE IS EVERY FILE FETCHED TWICE**, into two differently-named copies
# -- the fault that put three wrongly-dated files in the reference's Drive.
going = tool.LastRun(started=AT - timedelta(minutes=20))
check("a run already going stops another starting",
      "not finished" in (answered(lambda: tool.why_not_now(going, AT)) or ""))
check("and it says why that matters",
      "twice" in (answered(lambda: tool.why_not_now(going, AT)) or ""))

# **BUT A RUN THAT DIED MUST NOT STOP EVERY LATER ONE FOR EVER.**
died = tool.LastRun(started=AT - timedelta(hours=5))
check("a run that never finished is given up on after long enough",
      answered(lambda: tool.why_not_now(died, AT)) is None)
check("and that is said out loud, not quietly assumed",
      answered(lambda: tool.gave_up_on(died, AT)) is True)
check("while one that is merely slow is not given up on",
      answered(lambda: tool.gave_up_on(going, AT)) is False)
check("and a run that finished properly is not given up on either",
      answered(lambda: tool.gave_up_on(
          tool.LastRun(started=AT - timedelta(hours=9), finished=AT - timedelta(hours=8)), AT))
      is False)
check("nor is nothing at all", answered(lambda: tool.gave_up_on(None, AT)) is False)

# **ONCE A DAY, AND NOT TWICE.**
just_done = tool.LastRun(started=AT - timedelta(hours=2), finished=AT - timedelta(hours=1))
check("a run an hour after the last one is too soon",
      "due tomorrow" in (answered(lambda: tool.why_not_now(just_done, AT)) or ""))
check("and it says the last one was today",
      "which is today" in (answered(lambda: tool.why_not_now(just_done, AT)) or ""))
yesterday = tool.LastRun(started=AT - timedelta(hours=25), finished=AT - timedelta(hours=25))
check("a day later it may run again", answered(lambda: tool.why_not_now(yesterday, AT)) is None)
# **AND THE REASON NAMES WHEN THE LAST ONE FINISHED**, or a person told to wait
# has nothing to check it against.
check("being told to wait says when the last run finished",
      (AT - timedelta(hours=1)).isoformat() in (answered(lambda: tool.why_not_now(just_done, AT)) or ""))
# **A RUN GIVEN UP ON STARTS THE NEXT ONE AT ONCE**, rather than waiting a day
# from a finish that never happened.
check("a run given up on does not also have to wait a day",
      answered(lambda: tool.why_not_now(died, AT)) is None)
# **THE FAULT THIS RULE WAS REWRITTEN FOR (cycle 46, R2#1), and it is the one
# case that tells the two rules apart.** Measured as twenty-four hours since the
# last FINISH, a run that finished at 02:25 pushes tomorrow's floor to 02:25 --
# so a tick at 02:23 the next day is refused, and under D120 there is no second
# tick to catch it. **A whole day is never fetched, and nothing says so.**
# Asked of the day instead, the answer cannot drift.
last_night = tool.LastRun(
    started=datetime(2026, 8, 27, 2, 23), finished=datetime(2026, 8, 27, 2, 25))
a_tick_two_minutes_early = datetime(2026, 8, 28, 2, 23)
check("a run that finished at 02:25 does not refuse tomorrow's tick at 02:23",
      answered(lambda: tool.why_not_now(last_night, a_tick_two_minutes_early, 2)) is None)
# **AND IT IS STILL ONCE A DAY.** The drift is gone; the rule it was serving is not.
same_day_again = tool.LastRun(
    started=datetime(2026, 8, 28, 2, 23), finished=datetime(2026, 8, 28, 2, 25))
check("but a second tick the same day is still refused",
      answered(lambda: tool.why_not_now(
          same_day_again, datetime(2026, 8, 28, 23, 0), 2)) is not None)

# A run is given up on well within a day, so a run that died in the night is
# replaced rather than blocking every later one.
check("a run is given up on in hours, not days",
      answered(lambda: tool.GONE_AFTER < timedelta(hours=24)) is True)

check("a record of the last run cannot be edited after it is read",
      answered(lambda: setattr(going, "finished", AT)) is None and bool(THREW))
THREW.clear()

# ------------------------------- what a seller wrote, as an hour (D114)

# **ONE PLACE, because it is asked in two: the environment, and the seller's own
# database.** Written out twice, one of them would tidy a bad setting into the
# default and the other would refuse it -- and only one of those is right.
check("a whole hour written as text is that hour", answered(lambda: tool.the_hour_they_mean("23")) == 23)
check("and one written as a number is too", answered(lambda: tool.the_hour_they_mean(23)) == 23)
check("and midnight is an hour, not nothing", answered(lambda: tool.the_hour_they_mean("0")) == 0)
check("and stray spaces around it do not matter",
      answered(lambda: tool.the_hour_they_mean("  7 ")) == 7)
# **NEVER CHOSEN IS NOT A BROKEN SETTING.** Both mean the default.
check("nothing set at all means the default", answered(lambda: tool.the_hour_they_mean("")) == tool.NOT_BEFORE_HOUR)
check("and nothing at all means the default too",
      answered(lambda: tool.the_hour_they_mean(None)) == tool.NOT_BEFORE_HOUR)
check("and only spaces means the default", answered(lambda: tool.the_hour_they_mean("   ")) == tool.NOT_BEFORE_HOUR)
# **ANYTHING ELSE COMES BACK AS THEY WROTE IT**, so it can be refused in their own
# words. Tidied into the default here, a seller who typed "elevenish" would be
# fetched at the default hour and never told their setting was ignored.
check("something that is not an hour comes back exactly as it was written",
      answered(lambda: tool.the_hour_they_mean("elevenish")) == "elevenish")
check("and the clock then refuses it",
      tool.why_the_hour_is_no_good(tool.the_hour_they_mean("elevenish")) is not None)
# **AND THE REFUSAL NAMES WHAT WAS SET.** Since D114 this value comes off the
# seller's own business record, not out of a file somebody can go and look at.
check("and the refusal says what it was set to",
      "elevenish" in (tool.why_the_hour_is_no_good(tool.the_hour_they_mean("elevenish")) or ""))
check("and an hour out of range says what it was set to too",
      "25" in (tool.why_the_hour_is_no_good(25) or ""))
check("and says what the range actually is",
      "between 0 and 23" in (tool.why_the_hour_is_no_good(25) or ""))
# An hour out of range is still a number, and must not be quietly kept.
check("an hour nobody has is handed on and refused",
      tool.why_the_hour_is_no_good(answered(lambda: tool.the_hour_they_mean("25"))) is not None)

# ------------------------------------------- the hour the seller chose
#
# **A FLOOR, NOT AN APPOINTMENT.** "Not before eight" and "at eight exactly" are
# different rules, and only the first survives the way GitHub behaves: its own
# documentation says a scheduled run can be delayed. An appointment missed by an
# hour is a day lost, and D108 says no day is ever lost.

MORNING = datetime(2026, 8, 28, 8, 23)

check("a tick at the hour the seller chose is not too early",
      answered(lambda: tool.why_not_now(tool.LastRun(), MORNING, 8)) is None)
check("and one after it is not either",
      answered(lambda: tool.why_not_now(tool.LastRun(), MORNING, 2)) is None)
too_early = answered(lambda: tool.why_not_now(tool.LastRun(), MORNING, 9))
check("a tick before it is refused", too_early is not None)
# **REFUSED IN WORDS, not silently.** A tick that does nothing and says nothing
# cannot be told from a tick that failed, and there are twenty-three of them now.
check("and it says what time it is", "08:23" in (too_early or ""))
check("and what time fetching is set for", "09:00" in (too_early or ""))
# **AND IT NAMES THE ONE TICK, because the sentence without it was the fault.**
# "It is 02:23 and fetching is set for 11:00 or later" reads exactly like a tick
# that will succeed later today. Naming the single fetch is what lets a reader
# tell a wait from a dead end.
check("and it says there is one fetch a day", "one fetch a day" in (too_early or ""))
check("and says when that one fetch is", "16:00" in (too_early or ""))

# **EVEN A FIRST RUN WAITS FOR THE HOUR.** Otherwise a seller who chose the
# afternoon has their very first run on whatever hour a hand-started tick
# happened to land on.
check("a seller who has never run still waits for their hour",
      answered(lambda: tool.why_not_now(None, MORNING, 9)) is not None)

# **A RUN GOING RIGHT NOW STILL STOPS A SECOND ONE, whatever hour it is.**
going = tool.LastRun(started=MORNING - timedelta(minutes=5))
check("a run already going is refused even at the chosen hour",
      "not finished" in (answered(lambda: tool.why_not_now(going, MORNING, 8)) or ""))
# And the once-a-day rule is what stops a second run later the same day.
done_today = tool.LastRun(started=MORNING - timedelta(hours=2), finished=MORNING - timedelta(hours=1))
check("and one that ran an hour ago is refused for the rest of the day",
      "due tomorrow" in (answered(lambda: tool.why_not_now(done_today, MORNING, 8)) or ""))

# **AN HOUR NOBODY CAN CHOOSE STOPS THE RUN AND SAYS SO.** Falling back to the
# default would fetch at an hour the seller did not choose and never say why.
for wrong in (24, -1, "8", None, 8.5, True):
    check(f"{wrong!r} is not an hour a seller can choose",
          tool.why_the_hour_is_no_good(wrong) is not None)
for right in (0, 2, 16):
    check(f"{right} is", tool.why_the_hour_is_no_good(right) is None)
check("and a setting that is wrong stops the run rather than being ignored",
      answered(lambda: tool.why_not_now(tool.LastRun(), MORNING, 25)) is not None)
check("midnight is a real choice, not a missing one",
      answered(lambda: tool.why_not_now(tool.LastRun(), datetime(2026, 8, 28, 0, 23), 0)) is None)

# ------------------------------------ the one tick, and the seven hours above it
#
# **HIS DECISION, 2026-09-10: FOUR IN THE AFTERNOON.** There is one tick a day and
# the chosen hour is a FLOOR, so the tick's hour is the ceiling on what a seller
# can usefully choose. It used to be 02:23, which left three usable hours out of
# twenty-four; it is 16:00, which leaves seventeen.
#
# **BOTH NUMBERS ARE HAND-TYPED HERE.** Read off `clock` they would agree with
# themselves whatever either of them said.
check("the one tick of the day is at four in the afternoon, his time",
      tool.THE_ONE_TICK_HOUR == 16)
check("and the default for a seller who has not chosen IS that tick -- higher "
      "would fetch nothing and lower would name an hour the tick cannot honour",
      tool.NOT_BEFORE_HOUR == 16)

# **THE SEVEN HOURS THAT STILL CANNOT WORK ARE REFUSED WHERE THEY ARE READ.**
# Left alone they are refused every night by `_too_early` instead, which reads
# like a tick that will succeed later today -- and that sentence is the fault
# this whole repair exists for. A setting that can NEVER work is a wrong setting,
# not a wait.
for above in (17, 18, 19, 20, 21, 22, 23):
    check(f"{above} is a real hour of a real day and still not one a seller can "
          f"be fetched at, so it is refused",
          tool.why_the_hour_is_no_good(above) is not None)
_seven = tool.why_the_hour_is_no_good(20) or ""
# **AND IT SAYS ALL THREE THINGS A SELLER NEEDS**, rather than only that it is
# wrong: what they set, when the one fetch is, and what to set instead.
check("and the refusal says what they set", "20:00" in _seven)
check("and when the one fetch of the day actually is", "16:00" in _seven)
check("and that nothing would be fetched on ANY day, which is what tells it "
      "apart from a wait", "on any day" in _seven)
# **AND IT IS REFUSED AT THE TICK ITSELF, not merely by the range guard.** A
# seller who chose 20:00 is not early at 16:00 -- they are unreachable -- and the
# whole point is that the sentence they get says so.
_at_the_tick = answered(lambda: tool.why_not_now(None, AT, 20)) or ""
check("a seller who chose an hour above the tick is refused ON the tick",
      _at_the_tick != "")
check("and told it is the setting that is wrong, not the moment",
      "on any day" in _at_the_tick)
# **AND THE TICK'S OWN HOUR IS REACHABLE**, which is what makes the ceiling a
# ceiling rather than one off it. Asserted positively, so a change that moved the
# tick without moving this could not pass by making a phrase absent.
check("and the tick's own hour is a choice that works",
      answered(lambda: tool.why_not_now(None, AT, 16)) is None)
check("and so is every hour below it, taking the middle of the day as the case "
      "that used to fail",
      all(answered(lambda: tool.why_not_now(None, AT, hour)) is None
          for hour in range(0, 17)))

# **THE FLOOR IS A FLOOR WHATEVER HAPPENED BEFORE IT.**
long_ago = tool.LastRun(started=MORNING - timedelta(days=2), finished=MORNING - timedelta(days=2))
check("a run that is due again is still not started before the chosen hour",
      answered(lambda: tool.why_not_now(long_ago, MORNING, 9)) is not None)
check("and it is started at it", answered(lambda: tool.why_not_now(long_ago, MORNING, 8)) is None)
# A run abandoned in the night must not let its replacement start at an hour the
# seller did not choose.
abandoned = tool.LastRun(started=MORNING - timedelta(hours=6))
check("a run given up on does not let the next one start early",
      answered(lambda: tool.why_not_now(abandoned, MORNING, 9)) is not None)
check("and the next one starts at the chosen hour",
      answered(lambda: tool.why_not_now(abandoned, MORNING, 8)) is None)

# **AND NOTHING ABOVE ENDED BY THROWING RATHER THAN BY ANSWERING.**
#
# **IT SAT SEVENTY-ONE LINES FROM THE END, with fifteen checks after it (cycle
# 46, R2#13)** -- so a deliberate breakage anywhere in those fifteen ended the
# run with nothing said about it, and the measurement read "noticed" while
# saying nothing about whether any check here is any good. It is the LAST thing
# before the tally now, which is the only place it covers everything.
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 80
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
