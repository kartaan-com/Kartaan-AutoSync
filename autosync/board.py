"""The day board: what was expected against what actually arrived.

Shape 3 of the contract (D100), and the second and third of the three layers.

**ONE ROW PER REPORT PER DATA DATE -- not per run.** A run is a thing that
happened; a data date is a thing that is owed. The reference mixed them and its
manifest could not answer "is the 12th there?" without knowing which run to ask.

**THE TWO RULES THAT MAKE THIS LAYER WORTH HAVING AT ALL:**

1. **A JOB REPORTING SUCCESS IS NOT EVIDENCE THAT A USABLE FILE EXISTS.** Those
   are two different questions and this is the only layer that asks the second.
   The reference recorded a report as Verified when a mangled filename still
   happened to contain the date -- campaign 1's file had never uploaded. Silent
   data loss, reported as healthy.
2. **NEVER INVENT A REASON.** A report that has not run yet, or that skipped
   itself on purpose, shows a bare row. A made-up reason sends whoever reads it
   looking in the wrong place, which is worse than saying nothing.

**AND THE THING THE REFERENCE COULD NOT DO AT ALL: say that nothing ran.**
Four days in twenty-six, its whole sync began and never reported finishing --
and later, two days running, it did not start at all. Nothing noticed, because
every alarm it had was attached to a report failing, and no report failed: no
report was ever asked. **`nothing_ran` is rule 2, it is the loudest thing on this
board, and it is the single most valuable line in this package.**
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set

from landing import Arrived, undated
from reports import ONLY_WHEN_ASKED, WHEN_THEY_PUBLISH_IT, Report, blocked_by
from schedule import data_date_for, days_late, should_ask_a_person

# What a row can say about one report on one day.
ARRIVED = "arrived"
MISSING = "missing"
BLOCKED = "blocked"
EMPTY = "arrived empty"
NEEDS_A_PERSON = "needs somebody"


@dataclass(frozen=True)
class Row:
    """One report, one data date, and the truth about it.

    `why_not` is `None` when nothing is recorded -- **never a sentence made up to
    fill the column.**
    """

    data_date: date
    report_id: str
    expected: bool
    state: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    why_not: Optional[str] = None
    days_late: int = 0
    ask_a_person: bool = False

    @property
    def is_a_problem(self) -> bool:
        return self.expected and self.state in (MISSING, BLOCKED, EMPTY)


def rows_for(
    reports: Sequence[Report],
    arrivals: Callable[[str], Sequence[Arrived]],
    today: date,
    reason_for: Optional[Callable[[str], Optional[str]]] = None,
    failed_ids: Iterable[str] = (),
    look_back_days: int = 14,
) -> List[Row]:
    """The board, oldest day first.

    `arrivals(report_id)` hands back what is REALLY in that report's folder --
    names and sizes, read from the folder itself. Nothing here asks a job what it
    thinks it did.

    `reason_for(report_id)` hands back the recorded reason or None. **None means
    none, and the row says nothing.**
    """
    reason_for = reason_for or (lambda _r: None)
    failed = set(failed_ids or ())
    out: List[Row] = []

    for a_report in reports:
        if a_report.every == ONLY_WHEN_ASKED:
            continue
        # What is really there, by the date in each file's own name.
        by_date: Dict[date, Arrived] = {}
        for got in arrivals(a_report.id) or ():
            when = got.data_date
            if when is None:
                # Counted separately by `files_nothing_can_find`. It is neither
                # arrived nor missing, and pretending otherwise is what hid seven
                # real files for six weeks.
                continue
            # A later file for the same day wins only if the earlier one was empty.
            standing = by_date.get(when)
            if standing is None or (standing.is_empty and not got.is_empty):
                by_date[when] = got

        newest_owed = data_date_for(a_report, today)
        day = today - timedelta(days=look_back_days)
        while day <= newest_owed:
            got = by_date.get(day)
            if got is None and a_report.every == WHEN_THEY_PUBLISH_IT:
                # **NOTHING IS OWED ON A DAY THE PLATFORM DID NOT PUBLISH ONE
                # (cycle 46, R2#7).** Amazon schedules settlement reports on its
                # own cycle and there is no way to ask for one, so every day
                # between them read as missing, the days-late clock ticked up,
                # and **the alarm could never be cleared -- because nothing was
                # ever going to arrive for that day.** An alarm nobody can clear
                # is an alarm everybody mutes, and the one that matters goes
                # unread with it.
                #
                # A day one DID arrive on is still a row, so what came is still
                # on the board.
                day += timedelta(days=1)
                continue
            late = days_late(day, today)
            stopped_by = blocked_by(a_report.id, failed)

            if got is not None and not got.is_empty:
                state = ARRIVED
                why = None
            elif got is not None:
                # **PRESENT AND EMPTY IS NOT ARRIVED.** Presence alone recorded a
                # truncated file as Verified in the reference.
                state = EMPTY
                why = reason_for(a_report.id)
            elif a_report.needs_a_person:
                # Not a nightly failure. It is a report that cannot run by itself,
                # and saying so is what stops it drowning the board.
                state = NEEDS_A_PERSON
                why = reason_for(a_report.id)
            elif stopped_by:
                # Rule 10: one cause, one problem.
                state = BLOCKED
                why = f"Waiting on {stopped_by}."
            else:
                state = MISSING
                why = reason_for(a_report.id)

            out.append(
                Row(
                    data_date=day,
                    report_id=a_report.id,
                    expected=True,
                    state=state,
                    file_name=got.name if got else None,
                    file_size=got.size if got else None,
                    why_not=why,
                    days_late=late,
                    ask_a_person=should_ask_a_person(day, today) and state != ARRIVED,
                )
            )
            day += timedelta(days=1)

    out.sort(key=lambda r: (r.data_date, r.report_id))
    return out


def files_nothing_can_find(
    reports: Sequence[Report],
    arrivals: Callable[[str], Sequence[Arrived]],
) -> Dict[str, Sequence[str]]:
    """Files sitting in folders with no data date in their names.

    **THE THIRD STATE, and the reference had no word for it.** Seven Meesho
    payment files sat in Drive for six weeks; the manifest looked for a date in
    the name, found none, and called every one of them missing while the data was
    right there. Neither side said anything.
    """
    out: Dict[str, Sequence[str]] = {}
    for a_report in reports:
        names = [g.name for g in (arrivals(a_report.id) or ())]
        stray = undated(names)
        if stray:
            out[a_report.id] = stray
    return out


# ------------------------------------------------------------ nothing ran


@dataclass(frozen=True)
class NothingRan:
    """The alarm that the reference could not raise.

    It is its own type rather than a row on the board, because it is not about a
    report. Every alarm the reference had hung off a report failing -- and when
    nothing runs, no report fails, because no report is ever asked.
    """

    last_run_on: Optional[date]
    days_quiet: int
    message: str


def nothing_ran(
    run_days: Iterable[date],
    today: date,
    quiet_days_allowed: int = 1,
) -> Optional[NothingRan]:
    """Has the fetcher gone quiet? Rule 2.

    `run_days` is the days a run genuinely started -- read from the run log, not
    from a schedule, because a schedule says what should have happened.

    **NEVER HAVING RUN AT ALL IS ALSO AN ANSWER**, and it is the state a new
    seller is in on the day they connect. It says so in different words rather
    than reporting a day count from a date that does not exist.
    """
    days = sorted({d for d in (run_days or ()) if d is not None})
    if not days:
        return NothingRan(
            last_run_on=None,
            days_quiet=0,
            message=(
                "Nothing has ever run. If a platform is connected, nothing is "
                "fetching from it yet."
            ),
        )
    last = days[-1]
    quiet = (today - last).days
    if quiet <= quiet_days_allowed:
        return None
    return NothingRan(
        last_run_on=last,
        days_quiet=quiet,
        message=(
            f"Nothing has run for {quiet} days -- the last run was {last}. "
            "No report has failed, because no report has been asked for. "
            "Nothing is being fetched from any platform."
        ),
    )


def what_to_say(
    rows: Sequence[Row],
    quiet: Optional[NothingRan],
    stray: Optional[Dict[str, Sequence[str]]] = None,
) -> List[str]:
    """Everything worth telling somebody, worst first.

    **THE QUIET ALARM COMES FIRST, ALWAYS.** A board full of missing days is the
    SYMPTOM when nothing is running; leading with the symptom sends a person to
    fix twenty reports when the answer is that the fetcher is not running at all.
    """
    said: List[str] = []
    if quiet is not None:
        said.append(quiet.message)
    for report_id, names in (stray or {}).items():
        said.append(
            f"{report_id}: {len(names)} file(s) in the folder have no date in the name, "
            "so nothing can match them to a day. The data is there and unreachable."
        )
    overdue = [r for r in rows if r.is_a_problem and r.ask_a_person]
    for row in sorted(overdue, key=lambda r: (-r.days_late, r.report_id)):
        # **THE RECORDED REASON OR NOTHING.** No sentence is invented to fill it.
        because = f" -- {row.why_not}" if row.why_not else ""
        said.append(
            f"{row.report_id} for {row.data_date} is {row.days_late} days late{because}"
        )
    return said
