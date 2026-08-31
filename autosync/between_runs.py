"""What one run has to hand to the next, and where it is kept.

**FOUR THINGS SURVIVE A RUN, and every one of them is a fault if it does not:**

| | |
|---|---|
| **What Amazon is already building** | Lost, the next run asks again for a report Amazon has in hand. Asking is rationed at ONE CALL A MINUTE, and a second request leaves two reports being built and two files with two names -- the exact shape of the three wrongly-dated duplicates in the reference's Drive. |
| **When the last run started and finished** | This is what `clock.py` is handed. Lost, either two runs go at once, or a run that died is believed to still be going and nothing ever starts again. |
| **Which days a run happened on** | `board.nothing_ran` is worked out from this and nothing else. Lost, the loudest alarm there is -- *nothing is fetching at all* -- can never fire, which is precisely the state the reference sat in for nine days. |
| **Which alarms have already gone out** | Lost, every standing alarm is sent again every night. A channel that says the same thing every night is a channel people mute, and a muted channel is worse than none. |

**IT LIVES IN THE SELLER'S OWN DRIVE, beside the log, and that is D100 rather
than a new idea.** His instruction, verbatim: *"I would not want to store that on
my storage, let it be in seller's drive."* It also means the job needs no
credential it does not already have -- the alternative was reaching into the
seller's database from a scheduled job, which is a second secret, a second thing
to go wrong, and a second thing that could leak.

**THE RULE THIS FILE EXISTS FOR: A RECORD THAT IS MISSING AND A RECORD THAT
CANNOT BE READ ARE NOT THE SAME THING.** Missing is an ordinary first day and
starts empty. Unreadable, treated as empty, silently throws away what Amazon is
building and what has already been said -- so it refuses, and the run does not
start. That is the whole difference between a first night and a corrupted one,
and reading them alike is how a system quietly begins again every night for ever.

**NOTHING HERE OPENS A CONNECTION.** Bytes in, a record out; a record in, bytes
out. Where those bytes come from and go is the caller's, so all of this is
checkable with no Drive and no account.
"""

import json
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from typing import Dict, List, Optional, Sequence, Tuple

# What the file in the seller's Drive is called. One name, so nothing has to
# search for it and nothing can write a second one beside it.
FILE_NAME = "autosync-state.json"

# How many days of run history are kept.
#
# **LONG ENOUGH TO ANSWER THE QUESTION, AND NO LONGER.** `nothing_ran` only ever
# looks at the most recent day, so the rest is for a person reading back. A list
# that is never trimmed is a file that grows for ever and eventually stops being
# writable -- and it would fail on the one night it mattered.
KEEP_RUN_DAYS = 60

# The one version of this record there has ever been. Written so that the day it
# changes, an older job reading a newer file says so instead of quietly reading
# the fields it recognises and dropping the rest.
SHAPE = 1


def _a_day(text) -> Optional[date]:
    """A day as it was written down, or None if it was not a day.

    Used only where a value being absent is genuinely ordinary. Anywhere that a
    bad value means the record is damaged, `_read` refuses instead.
    """
    try:
        return date.fromisoformat(str(text))
    except (TypeError, ValueError):
        return None


def _a_moment(text, called: str) -> Optional[datetime]:
    """A written-down moment, or nothing at all when there was none.

    **NOTHING WRITTEN DOWN AND SOMETHING UNREADABLE ARE NOT THE SAME THING
    (cycle 46, R2#2), and this is the field where that costs the most.** Anything
    unreadable used to come back as `None` -- and `None` is what the clock reads
    as *"no run has ever started"*, which is exactly the state in which a run is
    allowed to begin.

    **So a record saying a run IS GOING, damaged in this one field, let a second
    run start.** Two at once fetch every file twice, into two differently-named
    copies -- the fault that put three wrongly-dated files into the reference's
    Drive.

    Every other field in this file already refuses. These two were the exception,
    and they are the two the clock actually turns on.
    """
    if text is None or text == "":
        return None
    try:
        return datetime.fromisoformat(str(text))
    except (TypeError, ValueError):
        raise Damaged(
            f"{called} is written down as {text!r}, which is not a moment. Nothing has been "
            "started, because a run may already be going."
        ) from None


class Damaged(RuntimeError):
    """The record is there and cannot be read.

    **ITS OWN KIND, because the answer to it is not the answer to a missing
    one.** Missing means start; damaged means stop and let somebody look. One
    exception for both would have the job decide they are the same thing, which
    is the fault this file is written against.
    """


@dataclass(frozen=True)
class Between:
    """Everything one run leaves for the next.

    Frozen. A record anything can edit in place is a record two parts of a run
    can disagree about -- the reference's job objects were mutable and a backfill
    changed one under the job reading it.
    """

    # (report id, the day it is about) -> what Amazon calls the report it is making.
    in_flight: Dict[Tuple[str, str], str] = field(default_factory=dict)
    last_started: Optional[datetime] = None
    last_finished: Optional[datetime] = None
    run_days: Tuple[date, ...] = ()
    standing: Tuple[str, ...] = ()

    def started(self, at: datetime) -> "Between":
        """The record as it stands the moment a run begins.

        **WRITTEN DOWN BEFORE THE FETCHING, not after.** A run that is killed
        halfway must leave behind a record saying it started, or the next one
        cannot tell "nothing has run" from "one is going" -- and `clock.py`'s
        whole giving-up rule reads that difference.

        The day is added here too, for the same reason: `nothing_ran` asks
        whether a run HAPPENED, never whether it succeeded.
        """
        days = tuple(sorted(set(self.run_days) | {at.date()}))[-KEEP_RUN_DAYS:]
        return replace(self, last_started=at, last_finished=None, run_days=days)

    def finished(self, at: datetime) -> "Between":
        return replace(self, last_finished=at)


def empty() -> Between:
    """A first night. Nothing has run, nothing is in flight, nothing has been said."""
    return Between()


def _read(raw: bytes) -> Between:
    """The record as it was written down, or a refusal.

    **EVERY FIELD IS ASKED FOR PLAINLY.** A record of the wrong shape stops the
    run and names itself, rather than each careful `getattr` quietly turning a
    damaged file into an empty one -- which is `landing.days_that_arrived`'s
    lesson, paid for once already: written defensively, it answered "no day has
    ever arrived" and every day was fetched again for ever.
    """
    try:
        said = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as wrong:
        raise Damaged(
            f"The record of what the last run left behind could not be read: {wrong}. "
            "Nothing has been started -- reading it as empty would ask Amazon again for "
            "reports it is already building."
        ) from wrong
    if not isinstance(said, dict):
        raise Damaged(
            "The record of what the last run left behind is not a record at all. "
            "Nothing has been started."
        )
    shape = said.get("shape")
    if shape != SHAPE:
        # **A NEWER FILE IS NOT READ HALFWAY.** Reading the fields this job knows
        # and dropping the rest is how the part it dropped goes missing silently.
        raise Damaged(
            f"The record of what the last run left behind is shape {shape!r} and this job "
            f"reads shape {SHAPE}. Nothing has been started."
        )

    in_flight: Dict[Tuple[str, str], str] = {}
    for one in said.get("in_flight") or ():
        if not isinstance(one, dict):
            raise Damaged("A line saying what Amazon is building is not a record. Nothing has been started.")
        report_id, day, theirs = one.get("report"), one.get("day"), one.get("theirs")
        if not report_id or not theirs or _a_day(day) is None:
            # **REFUSED, NOT SKIPPED.** Skipping one is how a report Amazon is
            # already building gets asked for a second time, which is the single
            # thing this record exists to prevent.
            raise Damaged(
                f"A line saying what Amazon is building is incomplete ({one!r}). "
                "Nothing has been started."
            )
        in_flight[(str(report_id), str(day))] = str(theirs)

    days: List[date] = []
    for one in said.get("run_days") or ():
        when = _a_day(one)
        if when is None:
            raise Damaged(f"{one!r} is written down as a day a run happened and is not a day.")
        days.append(when)

    return Between(
        in_flight=in_flight,
        last_started=_a_moment(said.get("last_started"), "When the last run started"),
        last_finished=_a_moment(said.get("last_finished"), "When the last run finished"),
        run_days=tuple(sorted(set(days)))[-KEEP_RUN_DAYS:],
        standing=tuple(str(s) for s in said.get("standing") or ()),
    )


def read(raw: Optional[bytes]) -> Between:
    """What the last run left, or an empty record when there has never been one.

    **THE ONE DISTINCTION THIS FILE IS FOR.** `None` is "there is no such file" --
    an ordinary first night. Bytes that will not read are damage, and damage
    refuses.
    """
    if raw is None:
        return empty()
    if raw == b"":
        # An empty file is not a first night: something wrote it. Reading it as a
        # fresh start would throw away whatever it was meant to hold.
        raise Damaged(
            "The record of what the last run left behind is an empty file. Nothing has been "
            "started -- an empty file is not the same as no file."
        )
    return _read(raw)


def write(state: Between) -> bytes:
    """The record as it goes back to Drive.

    Sorted, so two runs that left the same thing behind produce the same bytes --
    which is what makes a difference between two of them mean something.
    """
    return json.dumps(
        {
            "shape": SHAPE,
            "in_flight": [
                {"report": report_id, "day": day, "theirs": theirs}
                for (report_id, day), theirs in sorted(state.in_flight.items())
            ],
            "last_started": state.last_started.isoformat() if state.last_started else None,
            "last_finished": state.last_finished.isoformat() if state.last_finished else None,
            "run_days": [d.isoformat() for d in sorted(state.run_days)],
            "standing": sorted(state.standing),
        },
        # **READABLE BY A PERSON, because it sits in the seller's own Drive.**
        # The one time anybody opens this file is the night something has gone
        # wrong, and one long line is a file nobody can read on a phone.
        indent=1,
    ).encode("utf-8")


def why_it_cannot_be_saved(state: Between) -> Optional[str]:
    """Why this record must not be written, in words, or None.

    **A RUN THAT FINISHED BEFORE IT STARTED IS A BROKEN CLOCK**, and written down
    it would make `clock.py` refuse every later run for a day on the strength of
    something that never happened. Caught on the way out, where it is still one
    run's problem.
    """
    if state.last_finished and not state.last_started:
        return "A run cannot be recorded as finished without ever having started."
    if state.last_started and state.last_finished and state.last_finished < state.last_started:
        return (
            f"A run cannot finish ({state.last_finished.isoformat()}) before it started "
            f"({state.last_started.isoformat()})."
        )
    return None


def as_the_clock_reads_it(state: Between):
    """The last run, in the shape `clock.why_not_now` takes.

    **ONE TRANSLATION, HERE.** Two places turning this record into the clock's
    record is two answers to "is a run going?", and `landing.days_that_arrived`
    is on the register for exactly that -- one contract with two meanings, and
    whichever caller got the other one believed nothing had ever happened.
    """
    from clock import LastRun  # noqa: PLC0415 - kept beside its one use

    return LastRun(started=state.last_started, finished=state.last_finished)


def carried_in_flight(state: Between):
    """What Amazon is building, in the shape the runner takes."""
    from runner import InFlight  # noqa: PLC0415 - kept beside its one use

    return InFlight(asked=dict(state.in_flight))


def with_in_flight(state: Between, in_flight) -> Between:
    """The record updated with whatever the run left in flight."""
    return replace(state, in_flight=dict(in_flight.asked))


def with_standing(state: Between, standing: Sequence[str]) -> Between:
    """The record updated with the alarms that have now been sent."""
    return replace(state, standing=tuple(standing))
