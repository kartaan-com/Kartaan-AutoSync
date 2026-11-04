"""One run: work out what is owed, fetch it, land it, say what happened.

Phase 3. This is the piece that ties the spine to a door.

**IT HOLDS NOTHING AND DECIDES NOTHING ON ITS OWN.** What is owed comes from
`schedule.py`, what arrived comes from the folder, what a file is called comes
from `landing.py`, what Amazon's answers mean comes from `amazon.py`. This file
only puts them in order. That is deliberate: every rule this package has is
checkable without a run happening, and a runner that started making its own
decisions would take them back out of reach.

**THREE THINGS IT MUST DO THAT THE REFERENCE COULD NOT:**

**1. Survive being interrupted, and carry on from where it stopped.** Rule 3. The
   whole run happens inside `Run(...)`, so whatever ends it -- finishing, throwing,
   a login prompt, the machine going to sleep -- flushes the evidence on the way
   out. And what was already asked for is written down BEFORE the fetch, so the
   next run continues rather than starting again.

**2. Never ask twice for the same report.** `createReport` is one call a minute,
   and asking again for one Amazon already accepted leaves two reports being
   built. What is in flight is carried between runs and handed to the door, which
   then waits rather than asks.

**3. Say that it ran.** Not that it succeeded -- that it RAN. `nothing_ran` is
   answered from that record, and it is the loudest alarm there is.

**AND ONE REPORT FAILING NEVER STOPS THE REST.** The reference's queue died at the
first login prompt and abandoned everything behind it; on 25 August that was every
Flipkart report of the day. Each report here is its own attempt, and its failure is
recorded against it and nothing else.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple

import runlog
from board import Row, nothing_ran, rows_for, files_nothing_can_find
from alarms import Alarm, alarms_for, what_changed, Changes
from reports import API, ONLY_WHEN_ASKED, Report
from schedule import (
    Owed, days_beyond_reach, spread_the_catch_up, what_could_not_be_fetched_said, what_is_owed,
)

# What one report's attempt came to. The door's own words, kept as they are so
# nothing is translated twice.
LANDED = "landed"
NOTHING_TO_FETCH = "nothing-to-fetch"
STILL_WAITING = "still-waiting"
FAILED = "failed"

# AS4: how many nights an ask of a snapshot report is kept for collecting; older, the picture is stale or stuck, and it is asked afresh.
SNAPSHOT_ASK_KEPT_DAYS = 3


@dataclass
class InFlight:
    """What has been asked for and not yet collected.

    **THE ONE THING THAT MUST SURVIVE A RUN ENDING BADLY.** Lost, the next run
    asks again for a report Amazon is already building -- which spends a rationed
    call and leaves two reports where there should be one.

    Keyed by report AND day, because two days of one report can be in flight at
    once and they are not interchangeable.
    """

    asked: Dict[Tuple[str, str], str] = field(default_factory=dict)
    # J288: called the moment an ask is remembered, so the record can be saved NOW and not only when the run ends. It must never raise.
    kept: Optional[Callable[[], None]] = None

    def key(self, report_id: str, data_date: date) -> Tuple[str, str]:
        return (report_id, data_date.isoformat())

    def what_was_asked(self, report_id: str, data_date: date) -> Optional[str]:
        return self.asked.get(self.key(report_id, data_date))

    def remember(self, report_id: str, data_date: date, their_id: str) -> None:
        self.asked[self.key(report_id, data_date)] = their_id
        if self.kept is not None:
            self.kept()

    def forget(self, report_id: str, data_date: date) -> None:
        self.asked.pop(self.key(report_id, data_date), None)

    def newest_day_asked(self, report_id: str) -> Optional[date]:
        """The day the newest ask of a SNAPSHOT report was made under. **A snapshot's day is always today**, so an ask made last night
        sat under a day nobody looks up again and was asked for afresh every night, never collected (`az_suppressed`, 28 Oct to 3 Nov)."""
        days = sorted(day for (one, day) in self.asked if one == report_id)
        return date.fromisoformat(days[-1]) if days else None

    def forget_every_day(self, report_id: str) -> None:
        for key in [k for k in self.asked if k[0] == report_id]:
            del self.asked[key]


@dataclass(frozen=True)
class WhatHappened:
    """What a whole run came to."""

    run: str
    on: date
    landed: Tuple[str, ...] = ()
    waiting: Tuple[str, ...] = ()
    nothing_to_fetch: Tuple[str, ...] = ()
    failed: Tuple[str, ...] = ()
    tried: int = 0
    # **WHY THE EVIDENCE COULD NOT BE GOT OUT OF THE BUILDING, if it could not.**
    # `runlog.Run` has recorded this since it was written and NOTHING HAS EVER
    # READ IT -- so a run whose log never reached the seller's Drive or their
    # database finished green and silent, which is the exact failure this whole
    # package exists against. Carried out of the run here so `one_tick` can call
    # it what it is: our own defect (D108).
    could_not_flush: Optional[str] = None
    # **WHY EACH REPORT THAT FAILED, FAILED -- IN ITS OWN WORDS.**
    #
    # `runlog` has kept a reason against each report since it was written, and
    # **nothing carried it out of the run** (cycle 46, R2#6). The day board has a
    # column for exactly this and it was blank on every row, on every night --
    # so a seller looking at a report five days late was told it was five days
    # late and nothing else.
    #
    # **The same shape as `could_not_flush` above**, which was recorded and never
    # read for the same reason: a run ends, and what it knew ends with it unless
    # something takes it out.
    reasons: Mapping[str, str] = field(default_factory=dict)
    # **WHICH DAYS LANDED, not only which reports (AS7b)**: the manifest marks a line `by="api"` only for a file this run really brought.
    landed_days: Tuple[Tuple[str, date], ...] = ()

    def summary(self) -> str:
        """One sentence. **It says how many were TRIED**, not only how many worked
        -- a run that tried nothing and a run where everything worked both report
        no failures, and they are entirely different days."""
        said = (
            f"{self.tried} tried: {len(self.landed)} landed, {len(self.waiting)} still coming, "
            f"{len(self.nothing_to_fetch)} had nothing, {len(self.failed)} failed."
        )
        if self.could_not_flush:
            said += f"  The run log could not be got out of the building: {self.could_not_flush}"
        return said


def do_a_run(
    name: str,
    reports: Sequence[Report],
    fetch: Callable[..., "object"],
    arrivals: Callable[[str], Sequence],
    in_flight: InFlight,
    sink: Callable[[Sequence[runlog.Line]], None],
    now: Callable[[], datetime],
    today: date,
    look_back_days: Optional[int] = None,
    asked_for: Optional[Sequence["Owed"]] = None,
    refused: Sequence[str] = (),
) -> WhatHappened:
    """Fetch everything that is owed, and say what happened.

    **`asked_for` IS A PERSON NAMING THE DAYS THEMSELVES**, instead of the run
    working out what is owed. Everything after that point is identical -- the
    same fetching, the same landing, the same log, the same marker. The reference
    had a separate program for this, and that is where its three wrongly-dated
    duplicate files came from.

    `fetch(report_id, data_date, asked_already=...)` is the door -- Amazon's, or
    later a browser's. It answers something with `.state`, `.say`, and optionally
    `.their_id` for a report that has been asked for and is still being built.

    **THE WHOLE THING IS INSIDE A `Run`, so the evidence gets out however it
    ends.** That is the 25 August fault, closed at the level it happened.
    """
    landed: List[str] = []
    landed_days: List[Tuple[str, date]] = []
    waiting: List[str] = []
    nothing: List[str] = []
    failed: List[str] = []
    tried = 0

    # **ONLY THE API DOOR'S SNAPSHOTS:** the browser door's `asked_already` means "collect from the page", which a day-old note must not trigger.
    api_snapshots = {r.id for r in reports if r.door == API and r.snapshot}

    def asked_for_it(report_id: str, data_date: date) -> Optional[str]:
        if report_id in api_snapshots:
            # AS4: an ask older than SNAPSHOT_ASK_KEPT_DAYS is not collected (a stale picture, or one stuck in Amazon's queue): asked afresh.
            day = in_flight.newest_day_asked(report_id)
            if day is None or (today - day).days > SNAPSHOT_ASK_KEPT_DAYS:
                return None
            return in_flight.what_was_asked(report_id, day)
        return in_flight.what_was_asked(report_id, data_date)

    def let_go(one) -> None:
        if one.report_id in api_snapshots:
            in_flight.forget_every_day(one.report_id)
        else:
            in_flight.forget(one.report_id, one.data_date)

    with runlog.Run(name, sink, now) as run:
        named_by_hand = asked_for is not None
        owed = (list(asked_for) if named_by_hand
                else what_is_owed(reports, arrivals, today, look_back_days=look_back_days))
        # **A LONG CATCH-UP IS SPREAD, AND WHAT CANNOT BE FETCHED AT ALL IS SAID.**
        # Both only for a run that worked out what is owed itself -- a person who
        # named the days gets exactly the days they named.
        held_over = 0
        if not named_by_hand:
            owed, held_over = spread_the_catch_up(
                owed, today,
                already_asked=lambda one: asked_for_it(one.report_id, one.data_date) is not None,
            )
            for said_lost in what_could_not_be_fetched_said(
                days_beyond_reach(reports, arrivals, today, look_back_days=look_back_days)
            ):
                run.log.failed(runlog.SYSTEM, said_lost, now())
        # **WHAT WAS REFUSED IS SAID BEFORE ANYTHING IS TRIED**, so a person who
        # asked for six reports and got five sees why -- rather than reading a
        # clean-looking run and wondering where the sixth went.
        for why in refused:
            run.log.failed(runlog.SYSTEM, why, now())
        if named_by_hand:
            run.log.working(
                runlog.SYSTEM,
                f"{len(owed)} report-day(s) asked for by hand."
                if owed else "Nothing was asked for that could be fetched.",
                now(),
            )
        else:
            run.log.working(
                runlog.SYSTEM,
                f"{len(owed)} report-days owed." if owed else "Nothing is owed.",
                now(),
            )
            if held_over:
                run.log.working(
                    runlog.SYSTEM,
                    f"{held_over} older day(s) are still owed and wait for the next run: "
                    "Amazon allows one request a minute, so a long catch-up is spread out.",
                    now(),
                )

        for one in owed:
            tried += 1
            # **EACH REPORT IS ITS OWN ATTEMPT.** One failing must never stop the
            # rest -- the reference's queue died at the first login prompt and
            # abandoned every report behind it.
            handed = asked_for_it(one.report_id, one.data_date)
            try:
                got = fetch(
                    one.report_id,
                    one.data_date,
                    asked_already=handed,
                )
            except Exception as wrong:  # noqa: BLE001 - recorded against its own report, never swallowed
                failed.append(one.report_id)
                run.log.failed(one.report_id, f"{one.data_date}: {wrong}", now())
                continue

            state = getattr(got, "state", FAILED)
            said = getattr(got, "say", "") or ""
            their_id = getattr(got, "their_id", None)

            if state == LANDED:
                landed.append(one.report_id)
                landed_days.append((one.report_id, one.data_date))
                # AS4: a snapshot collected from an ask of an earlier night is asked for afresh NOW, or with one run a day it lands every second night.
                # Only when an old ask was really handed to the door: a stale one asked afresh tonight has already spent tonight's ask.
                asked_on = in_flight.newest_day_asked(one.report_id) if one.report_id in api_snapshots and handed is not None else None
                # **FORGOTTEN ONLY ONCE IT HAS LANDED.** Forgotten earlier, a run
                # that fell over between asking and collecting would ask again.
                let_go(one)
                run.log.done(one.report_id, f"{one.data_date}: {said}", now())
                if asked_on is not None and asked_on != one.data_date:
                    try:
                        again = fetch(one.report_id, one.data_date, asked_already=None)
                    except Exception as wrong:  # noqa: BLE001 - tonight's picture landed; the fresh ask is tried again tomorrow
                        run.log.warning(one.report_id, f"{one.data_date}: landed; asking for the next picture failed: {wrong}", now())
                    else:
                        if getattr(again, "state", None) == STILL_WAITING and getattr(again, "their_id", None):
                            in_flight.remember(one.report_id, one.data_date, str(again.their_id))
                            run.log.working(one.report_id, f"{one.data_date}: landed; the next picture is asked for", now())
                        else:
                            run.log.warning(one.report_id, f"{one.data_date}: landed; asking for the next picture came to "
                                            f"{getattr(again, 'state', FAILED)}: {getattr(again, 'say', '') or ''}", now())
            elif state == STILL_WAITING:
                waiting.append(one.report_id)
                if their_id:
                    # **WRITTEN DOWN NOW, not at the end.** A run that stops here
                    # must still leave the next one able to collect it.
                    if one.report_id not in api_snapshots:
                        in_flight.remember(one.report_id, one.data_date, str(their_id))
                    # AS4: the same ask still building keeps the day it was made, so its age counts and a stuck one is asked afresh.
                    elif asked_for_it(one.report_id, one.data_date) != str(their_id):
                        in_flight.forget_every_day(one.report_id)
                        in_flight.remember(one.report_id, one.data_date, str(their_id))
                run.log.working(one.report_id, f"{one.data_date}: {said}", now())
            elif state == NOTHING_TO_FETCH:
                nothing.append(one.report_id)
                let_go(one)
                # **NOT A FAILURE AND NOT A SUCCESS.** Recorded as a warning so it
                # is visible without putting a reason against the report -- a
                # `done` here would clear a real failure standing from before.
                run.log.warning(one.report_id, f"{one.data_date}: {said}", now())
            else:
                failed.append(one.report_id)
                let_go(one)
                run.log.failed(one.report_id, f"{one.data_date}: {said}", now())

        # **TAKEN OUT OF THE RUN BEFORE IT ENDS.** The log clears a reason the
        # moment that report succeeds, so this is every reason still standing --
        # which is exactly what the board's "why" column is for.
        said_why = {report: run.log.reason_for(report) or "" for report in run.log.failed_reports()}

    return WhatHappened(
        run=name,
        on=today,
        landed=tuple(landed),
        waiting=tuple(waiting),
        nothing_to_fetch=tuple(nothing),
        failed=tuple(failed),
        tried=tried,
        # **READ AFTER THE BLOCK, because the flush happens on the way out of it.**
        could_not_flush=run.could_not_flush,
        # **CARRIED OUT OF THE RUN, or the board's "why" column stays blank.**
        # Read inside the block, because this is the run's own record of it.
        reasons=said_why,
        landed_days=tuple(landed_days),
    )


# ------------------------------------------------------------ looking at it


def look(
    reports: Sequence[Report],
    arrivals: Callable[[str], Sequence],
    run_days: Sequence[date],
    today: date,
    reason_for: Optional[Callable[[str], Optional[str]]] = None,
    failed_ids: Sequence[str] = (),
    look_back_days: Optional[int] = None,
) -> Tuple[List[Row], List[Alarm]]:
    """The board and the alarms, worked out from the record.

    **NOTHING HERE NEEDS A RUN TO BE HAPPENING**, and that is the whole point. A
    run finishing can ask this; so can a watcher on a clock, and so can somebody
    opening the app. **That is what lets "nothing ran" ever fire at all** -- the
    reference could not raise it because every alarm it had lived inside a run,
    and the case it was needed for is the case where no run happens.
    """
    rows = rows_for(reports, arrivals, today, reason_for=reason_for,
                    failed_ids=failed_ids, look_back_days=look_back_days)
    quiet = nothing_ran(run_days, today)
    stray = files_nothing_can_find(reports, arrivals)
    return rows, alarms_for(rows, quiet, stray)


def tell_somebody(
    alarms: Sequence[Alarm],
    standing: Sequence[str],
    send: Callable[[Sequence[str]], None],
) -> Changes:
    """Send out what has changed, and answer what the standing list should become.

    **THE STANDING LIST IS ANSWERED, NEVER WRITTEN HERE.** Whoever called owns it,
    and the write happens where the failure of that write can be seen. A function
    that both sends and saves has a window where it has told somebody and then
    forgotten it did -- which is how the same alarm goes out every night.

    **AND `send` IS ONLY CALLED WHEN THERE IS SOMETHING TO SAY.** A channel that
    gets a message every night whether or not anything moved is a channel people
    mute, and a muted channel is worse than no channel.
    """
    changed = what_changed(standing, alarms)
    if not changed.anything_to_send:
        return changed
    from alarms import to_send  # noqa: PLC0415 - kept beside its one use

    send(to_send(changed))
    return changed
