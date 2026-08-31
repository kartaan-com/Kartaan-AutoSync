"""What time it is for a run, and whether one should happen at all.

**THE CLOCK IS THE PIECE THAT WAS MISSING FOR NINE DAYS.** Everything else about
auto-sync can be right and still fetch nothing, because nothing set it off. The
reference's alarm existed only from the moment it was installed, and when it went,
nothing ever asked again.

**NOTHING HERE READS A CLOCK.** The time is handed in, like everything else in
this package, which is what lets every rule below be checked on any day at all
rather than only on the day the checks happen to run.

**AND IT IS NOT THE SAME AS THE ONE IN THE EXTENSION.** That one wakes the
seller's own Chrome, because Meesho can only be driven there. This one is for the
half that runs with nobody present (D36) -- and both being wrong in the same way
at the same time is precisely what left him with nothing for nine days, so they
are told apart here rather than assumed to be one thing.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional, Sequence

# **INDIA, because that is when his day ends.** A run on a clock somewhere else
# fetches "yesterday" while it is still today for him, and the platform has
# nothing to give. The reference's quota meter reset seven hours early for
# exactly this reason -- one clock assumed and never named.
HOURS_AHEAD_OF_UTC = 5
MINUTES_AHEAD_OF_UTC = 30

# **ONE RUN PER DAY OF HIS CLOCK -- A DAY, NOT TWENTY-FOUR HOURS (D120).**
#
# It was twenty-four hours since the last run FINISHED, and that is a different
# rule with a fault in it: a run that finishes at 02:25 pushes tomorrow's floor
# to 02:25, so a tick at 02:23 is refused and the hour walks forward every night.
# **The day it walks past the last tick of the day, a whole day is never fetched
# at all** -- and there is nothing in the log to say so, because a refusal is an
# ordinary answer.
#
# Hourly ticks hid it: the next tick an hour later ran, and the only cost was
# fetching at a drifting hour. **D120 wakes the job ONCE a day, so the same drift
# now loses the day.** Asked as "has one already run today", nothing can drift:
# the answer is about the calendar, not about how long ago something happened.

# How long a run may go without finishing before it is treated as gone. A run
# that died leaves its record saying it is still going, and nothing would ever
# start another one.
GONE_AFTER = timedelta(hours=4)

# The hour of HIS day a run is not started before, when the seller has not said.
#
# **TWO IN THE MORNING, because that is after his day has ended and the platforms
# have yesterday to give.** It is the hour the schedule already effectively used;
# it is written down here now because a seller can change it, and a default that
# lives in a cron line is a default nobody can see or reason about.
NOT_BEFORE_HOUR = 2

# The earliest and latest hour a seller may choose. Both ends of a real day.
FIRST_HOUR = 0
LAST_HOUR = 23


def his_clock(machine_moment: datetime) -> datetime:
    """The machine's clock, told as his.

    **THIS IS THE ONE PLACE THE OFFSET IS EVER APPLIED, and it is called once, at
    the very edge, the moment the machine is asked what time it is.** Everything
    after that point -- every moment in this package, every line of the run log,
    every record of when a run started -- is ALREADY his time and must never be
    converted again.

    **His words, and the reason this changed:** *"I live and speak and work in
    IST, so everything should be according to that only."* It used to convert
    part-way down, which meant some moments were his and some were the machine's
    and only the reader could tell which. Converting in one place makes a second
    conversion impossible rather than merely unlikely -- and a moment converted
    twice is five and a half hours wrong, in the direction nothing notices.
    """
    return machine_moment + timedelta(hours=HOURS_AHEAD_OF_UTC, minutes=MINUTES_AHEAD_OF_UTC)


def the_day_to_fetch(moment: datetime) -> date:
    """Which day a run starting now is about.

    **YESTERDAY, IN HIS OWN DAY.** A platform has nothing to give for a day that
    has not ended, and a run that asked for one would record an empty answer as
    the day's data.

    The moment handed in is already his (see `his_clock`), so there is nothing to
    convert here -- and adding the offset again would ask for the wrong day for
    five and a half hours out of every twenty-four.
    """
    return moment.date() - timedelta(days=1)


@dataclass(frozen=True)
class LastRun:
    """What is known about the run before this one."""

    started: Optional[datetime] = None
    finished: Optional[datetime] = None

    @property
    def still_going(self) -> bool:
        return self.started is not None and self.finished is None


def why_the_hour_is_no_good(hour) -> Optional[str]:
    """Why this is not an hour of the day, in words, or None.

    **AN HOUR NOBODY CAN CHOOSE IS A SETTING THAT SILENTLY DOES NOTHING.** Read
    as a default when it is out of range, a seller who typed 25 would be fetched
    at two in the morning and never told why.

    **AND IT SAYS WHAT WAS ACTUALLY SET.** Since D114 this value comes off the
    seller's own business record rather than out of a file somebody could go and
    look at, so a refusal that does not name the value is a refusal nobody can
    act on -- and this sentence ends up in a log read the morning after.
    """
    if isinstance(hour, bool) or not isinstance(hour, int):
        return f"The hour to fetch at has to be a whole number of hours, and it is set to {hour!r}."
    if hour < FIRST_HOUR or hour > LAST_HOUR:
        return (
            f"The hour to fetch at has to be between {FIRST_HOUR} and {LAST_HOUR}, "
            f"and it is set to {hour}."
        )
    return None


def the_hour_they_mean(said):
    """What a seller wrote, as an hour -- or exactly what they wrote.

    **ONE PLACE, because it is asked in two: the environment and the seller's own
    database.** Written out twice, one of them would one day tidy a bad setting
    into the default and the other would refuse it, and only one of those is
    right.

    **NOT SET AT ALL MEANS THE DEFAULT** -- a seller who has never chosen is not a
    seller whose setting is broken.

    **AND ANYTHING THAT IS NOT A WHOLE HOUR COMES BACK AS THEY WROTE IT**, so
    `why_the_hour_is_no_good` can refuse it in their own words. Tidied into the
    default here, a seller who typed "elevenish" would be fetched at two in the
    morning and never told their setting was ignored.
    """
    text = str(said if said is not None else "").strip()
    if text == "":
        return NOT_BEFORE_HOUR
    try:
        return int(text)
    except ValueError:
        return text


def why_not_now(last: LastRun, moment: datetime, not_before_hour: int = NOT_BEFORE_HOUR) -> Optional[str]:
    """Why a run should not start now, in words, or None.

    **THE SELLER PICKS THE HOUR, IN HIS OWN TIME, AND IT IS A FLOOR RATHER THAN AN
    APPOINTMENT.** "Not before eight" and "at eight exactly" are different rules,
    and only the first survives the way GitHub actually behaves: its own
    documentation says a scheduled run "can be delayed during periods of high
    loads". An appointment missed by an hour is a day lost, and D108 says no day
    is ever lost. So the run happens at the first tick at or after the hour the
    seller chose, and the twenty-four-hour rule below is what stops it happening
    again the same day.

    **TWO RUNS AT ONCE IS EVERY FILE FETCHED TWICE**, into two differently-named
    copies -- the fault that put three wrongly-dated files into the reference's
    Drive.

    **BUT A RUN THAT DIED MUST NOT STOP EVERY LATER ONE FOR EVER.** A record
    saying "still going" is exactly what a run that was killed leaves behind, and
    reading it as a run in progress is how a system stops by itself and nothing
    says so. So after long enough it is treated as gone, and it says which of the
    two it decided.
    """
    too_early = _too_early(moment, not_before_hour)
    if last is None or last.started is None:
        # **EVEN A FIRST RUN WAITS FOR THE HOUR.** Otherwise a seller who chose
        # the evening would have their very first run at two in the morning, on
        # a day the platforms may not have finished writing.
        return too_early
    if last.still_going:
        if moment - last.started < GONE_AFTER:
            return (
                f"A run started at {last.started.isoformat()} and has not finished. "
                "Two at once would fetch every file twice."
            )
        # **GIVEN UP ON.** It falls through to the same floor at the bottom --
        # the hour still applies, because a run abandoned in the night must not
        # let its replacement start at an hour the seller did not choose. An
        # early return was written here and taken out again: it answered exactly
        # what the bottom of this function already answers, and a second way of
        # saying one thing is a place for the two to disagree.
    if last.finished is not None and last.finished.date() == moment.date():
        # **ASKED OF THE DAY, NEVER OF HOW LONG AGO.** Twenty-four hours from the
        # last finish walks the floor forward every night by however long the run
        # took, and the night it walks past the tick, the day is lost.
        return (
            f"The last run finished at {last.finished.isoformat()}, "
            "which is today. The next one is due tomorrow."
        )
    return too_early


def _too_early(moment: datetime, not_before_hour: int) -> Optional[str]:
    """Is it earlier in his day than the seller asked for?

    **REFUSED IN WORDS, not silently.** A tick that does nothing and says nothing
    is indistinguishable from a tick that failed, and there are twenty-three of
    them every day.
    """
    wrong = why_the_hour_is_no_good(not_before_hour)
    if wrong:
        # **A SETTING THAT MAKES NO SENSE STOPS THE RUN AND SAYS SO.** Falling
        # back to the default would fetch at an hour the seller did not choose
        # and never tell them their setting was ignored.
        return wrong
    if moment.hour >= not_before_hour:
        return None
    return (
        f"It is {moment.hour:02d}:{moment.minute:02d} and fetching is set for "
        f"{not_before_hour:02d}:00 or later."
    )


def gave_up_on(last: LastRun, moment: datetime) -> bool:
    """Did a run that never finished have to be given up on?

    **SAID OUT LOUD, because it is not the same as an ordinary start.** A run
    abandoned because the machine was shut, or Chrome was closed, is a thing
    somebody should know happened -- the reference had four of them in
    twenty-six days and not one of them was written down anywhere.
    """
    return bool(last and last.still_going and moment - last.started >= GONE_AFTER)
