"""What is owed, when it is late, and when to stop trying and ask a person.

**THIS FILE EXISTS BECAUSE OF ONE FAULT, and it is the worst one found in the
working reference.** Its retry system counted a deadline in ATTEMPTS, not in days:
`daysPending` went up only when an attempt actually happened on a new calendar
day. When the machine did not run -- Chrome shut, an earlier failure killing the
queue, a run that vanished -- no attempt happened, nothing was counted, **and the
clock stopped.**

Traced through its own live log:

    fk_orders / 2026-08-05    handed off 08-06, nine silent days, escalated 08-17
                              -- TWELVE calendar days to reach a "three-day" limit
    fk_orders / 2026-08-09    handed off 08-10, fourteen silent days, still
                              reporting "day 2" on 08-24 -- FIFTEEN days stuck,
                              never escalated at all
    fk_payments / 2026-08-05  still "day 2" on 08-24 -- NINETEEN days

**The safety net's timer only ticked while the thing it protected was already
working.** The one case it exists for -- the machine not running -- is the exact
case where it never fires, so nobody is ever told.

**RULE 13: a deadline is counted in CALENDAR days from the day the data was owed,
never in attempts.** An owed date nobody has even tried for three days is a LOUDER
alarm than one tried and failed three times, not a quieter one.

Everything here is pure: dates in, answers out, no clock of its own and no
database. The day is always passed in, so a check can ask about a particular
morning rather than the morning it happens to run on.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, List, Optional, Sequence, Set, Tuple

from landing import days_that_arrived
from reports import (
    DAILY, EVERY_THREE_DAYS, ONLY_WHEN_ASKED, WHEN_THEY_PUBLISH_IT, Report,
)

# How many calendar days an owed date may go unfetched before a person is asked.
# Three, the same as the reference intended -- the difference is that here it is
# three real days rather than three days on which something happened to run.
GIVE_UP_AFTER_DAYS = 3

# How wide the "every three days" window is.
THREE_DAY_SPAN = 3


def data_date_for(a_report: Report, run_date: date) -> date:
    """Which day's data a run on `run_date` is fetching.

    **THE RUN DATE AND THE DATA DATE ARE NOT THE SAME THING**, and confusing them
    is how the reference retried the wrong day for ever. A failure on the run of
    the 9th means the 8th's data is owed -- not the 9th's.
    """
    return run_date - timedelta(days=1) if a_report.owes_previous_day else run_date


def is_due(a_report: Report, data_date: date, already_have: Iterable[date]) -> bool:
    """Should this report be fetched for this data date?

    **ASKED OF WHAT HAS ARRIVED, never of what a job believes it did.** That is
    rule 7 one level up: the reference built its queue from a `lastRun` map the
    jobs wrote about themselves, so a job that reported success without producing
    a file was never asked for again.
    """
    if a_report.every == ONLY_WHEN_ASKED:
        return False
    have: Set[date] = set(already_have)
    if data_date in have:
        return False
    if a_report.every == DAILY:
        return True
    if a_report.every == EVERY_THREE_DAYS:
        window = {data_date - timedelta(days=n) for n in range(THREE_DAY_SPAN)}
        return not (have & window)
    if a_report.every == WHEN_THEY_PUBLISH_IT:
        # **LOOKED FOR EVERY NIGHT, AND OWED ON NO PARTICULAR DAY.** The run asks
        # the platform whether it has published a new one. A night it has not is
        # a quiet night, not a late day -- and `what_is_owed` below asks for one
        # day only, so this is one look a night rather than fourteen.
        return True
    return False


def days_late(owed_for: date, today: date) -> int:
    """How many CALENDAR days this data has been owed. Never attempts.

    **THIS ONE FUNCTION IS THE FIX FOR THE WORST FAULT IN THE REFERENCE.** It
    takes no attempt count, no run history and no state at all -- because there is
    nothing it could be given that would let it stop ticking while nobody was
    looking. That is the property, and it is why the signature is this short.

    Nought on the day it is owed. A date in the future answers nought rather than
    a negative, which would read as "not late" from the wrong direction.
    """
    return max(0, (today - owed_for).days)


def should_ask_a_person(owed_for: date, today: date, limit: int = GIVE_UP_AFTER_DAYS) -> bool:
    """Has this been owed long enough to stop trying and tell somebody?

    **IT DOES NOT MATTER WHETHER ANYTHING WAS EVER TRIED.** A date owed four days
    ago that nothing has even attempted is exactly the case the reference could
    not see, and it is the case that most needs saying out loud.
    """
    return days_late(owed_for, today) > limit


@dataclass(frozen=True)
class Owed:
    """One report owing one day, and how late it is.

    `ask_a_person` is on the record rather than worked out again by whoever draws
    it -- two places deciding when something has run out of time is two answers to
    one question, and the reference had exactly that between its popup and its
    notification.
    """

    report_id: str
    data_date: date
    days_late: int
    ask_a_person: bool
    # Filled in when this report is waiting on another one. Rule 10.
    blocked_by: Optional[str] = None

    def __str__(self) -> str:  # pragma: no cover - read by people, not by checks
        late = "owed today" if self.days_late == 0 else f"{self.days_late} days late"
        if self.blocked_by:
            return f"{self.report_id} for {self.data_date} -- {late}, blocked by {self.blocked_by}"
        return f"{self.report_id} for {self.data_date} -- {late}"


def what_is_owed(
    reports: Sequence[Report],
    arrivals,
    today: date,
    look_back_days: int = 30,
    blocked=None,
) -> List[Owed]:
    """Every report-and-day still owed, oldest first.

    `arrivals(report_id)` answers **what is really in that report's folder** --
    the same records the day board reads, so there is one contract and not two.
    It was a list of dates here and a list of files there, both called `arrivals`;
    a caller handing one to the other believed nothing had ever arrived and
    re-fetched every day for ever. `days_that_arrived` is the one translator.

    **OLDEST FIRST, because that is the order they have to be dealt with**, and
    because the oldest is the one closest to being gone for good.

    **A REPORT THAT CANNOT BE RE-FETCHED IS NOT LISTED AS OWED FOR A PAST DAY.**
    Meesho payments and every snapshot report can only ever be captured on the
    day; listing them as owed would put a permanent, un-actionable row on the
    board for every day they were ever missed, which is how a board stops being
    read at all. They are owed for TODAY's capture and nothing earlier.
    """
    blocked = blocked or {}
    out: List[Owed] = []
    for a_report in reports:
        if a_report.every == ONLY_WHEN_ASKED:
            continue
        have = set(days_that_arrived(arrivals(a_report.id)))
        # How far back this report can honestly be chased.
        first = today - timedelta(days=look_back_days)
        if a_report.cannot_backfill is not None:
            # Only the most recent owed day is real for these.
            first = data_date_for(a_report, today)
        if a_report.every == WHEN_THEY_PUBLISH_IT:
            # **ONE LOOK A NIGHT, not one per day of the window.** There is
            # nothing to chase: the platform publishes when it publishes, and
            # fourteen looks a night would be thirteen calls spent learning the
            # same thing.
            first = data_date_for(a_report, today)
        day = first
        while day <= data_date_for(a_report, today):
            if is_due(a_report, day, have):
                out.append(
                    Owed(
                        report_id=a_report.id,
                        data_date=day,
                        days_late=days_late(day, today),
                        ask_a_person=should_ask_a_person(day, today),
                        blocked_by=blocked.get(a_report.id),
                    )
                )
            day += timedelta(days=1)
    out.sort(key=lambda o: (o.data_date, o.report_id))
    return out


def asked_for_by_hand(
    reports: Sequence[Report],
    which: Sequence[str],
    first_day: date,
    last_day: date,
    today: date,
) -> Tuple[List[Owed], List[str]]:
    """The days a person has deliberately asked for, and what had to be refused.

    **HIS ASK, 2026-08-28, and the reason it exists:** the catching-up already
    chases a missed day on its own, but it can chase one for days and still not
    get it. When that happens he has to be able to name the day himself and have
    it fetched now, instead of waiting for a system that is already not working.

    **IT IS THE ORDINARY PATH WITH A DIFFERENT DAY, NOT A SECOND PROGRAM.** The
    reference had a separate backfill, and that is exactly where its three
    wrongly-dated duplicate files in Drive came from: two ways of naming a file
    is two ways of naming it wrongly. Everything after this -- fetching, landing,
    logging, the marker -- is the same code the nightly run uses.

    **WHAT IT REFUSES, and it says why rather than quietly dropping it:**

      - a report that can only ever be captured on the day. Meesho's payments
        export ignores the range it is given and always hands back the current
        settlement batch, so asking for last Tuesday produces today's file
        wearing last Tuesday's name. **That is worse than nothing**, and it is
        the fault that put three wrong files in the reference's Drive;
      - a day in the future, or a range that ends before it starts;
      - a report nobody has heard of.

    **IT DOES NOT ASK WHETHER THE FILE IS ALREADY THERE.** Somebody naming a day
    by hand has a reason -- usually that what arrived was wrong -- and second-
    guessing that is how a person ends up unable to fix their own data.
    """
    if last_day < first_day:
        return [], [f"{first_day} to {last_day} ends before it starts."]

    known = {r.id: r for r in reports}
    out: List[Owed] = []
    refused: List[str] = []

    for report_id in which:
        a_report = known.get(report_id)
        if a_report is None:
            refused.append(f"{report_id} is not a report Kartaan knows about.")
            continue
        if a_report.cannot_backfill is not None:
            # **SAID IN THE REPORT'S OWN WORDS.** The reason is written where the
            # report is declared, so a person reading the refusal is told why
            # this particular one cannot be had -- not a general apology.
            refused.append(f"{report_id}: {a_report.cannot_backfill}")
            continue
        day = first_day
        while day <= last_day:
            if day > data_date_for(a_report, today):
                refused.append(
                    f"{report_id}: {day} has not happened yet as far as this report goes."
                )
            else:
                out.append(
                    Owed(
                        report_id=report_id,
                        data_date=day,
                        days_late=days_late(day, today),
                        ask_a_person=False,
                    )
                )
            day += timedelta(days=1)

    out.sort(key=lambda o: (o.data_date, o.report_id))
    return out, refused


def worst_first(owed: Sequence[Owed]) -> List[Owed]:
    """The same list, most overdue first -- for a person deciding what to do.

    Two orderings of one list, on purpose and named differently: a machine works
    oldest-first because that is the order data must be filled in, and a person
    reads worst-first because that is the order things must be decided. The
    reference had one list serving both and it read wrong to whoever was not
    expecting it.
    """
    return sorted(owed, key=lambda o: (-o.days_late, o.report_id))
