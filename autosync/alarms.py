"""What gets told to somebody, and what does not. Phase 3.

**THE PROBLEM THIS FILE EXISTS FOR, and the reference could not solve it: when
nothing runs, nothing is there to raise the alarm.** Every alarm it had lived
inside a run and hung off a report failing -- so on the two days nothing started
at all, no report failed, because no report was ever asked for, and nothing
anywhere said a word. Two days of no data, silent.

**So the alarms are worked out from the RECORD, not from inside a run.** Every
function here takes the day board and the run history and answers what is wrong.
Nothing here needs a run to be happening. That is what lets the same answers be
had by a run finishing, by a watcher on a clock, or by somebody opening the app --
and it is the whole reason `nothing_ran` can ever fire.

**AN ALARM IS KEYED TO ITS CONDITION, NEVER TO EACH OCCURRENCE.** The reference
wrote a fresh record every day for anything that stayed true, so a report broken
for three weeks produced twenty-one identical messages and the real ones drowned.
Raising the same condition twice here is raising it once.

**AND AN ALARM LEAVES ON ITS OWN WHEN THE THING BEHIND IT IS FIXED.** There is
nothing here to dismiss one with, deliberately: a dismissed alarm is a problem
somebody decided to stop seeing, and this whole package exists because problems
were not being seen.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from board import NothingRan, Row

# How loudly. Three, and the order matters -- see `worst_first`.
STOP = "stop"          # nothing is being fetched at all
ACT = "act"            # something needs a person
KNOW = "know"          # worth knowing, nothing to do

LOUDNESS = {STOP: 0, ACT: 1, KNOW: 2}


@dataclass(frozen=True)
class Alarm:
    """One thing that is wrong.

    `key` is the CONDITION, not the occurrence. Two alarms with one key are one
    alarm, however many days it has been true.

    `what_it_means` is separate from `headline` on purpose: the headline is what
    fits on a phone, and the meaning is what somebody reads when they open it.
    The reference sent one line and left everybody guessing what to do.
    """

    key: str
    loudness: str
    headline: str
    what_it_means: str
    # **THE DEFAULT SAYS IT, AND NOTHING REPEATS IT.** Every alarm raised here was
    # passing `needs_action=True` explicitly as well -- three copies of one fact,
    # and the tool that breaks this code proved they could all be deleted without
    # anything noticing, because they only ever restated the default. A new kind
    # of alarm is loud until somebody deliberately decides otherwise, which is the
    # safe direction for it to slide.
    needs_action: bool = True

    def __str__(self) -> str:  # pragma: no cover - read by people
        return self.headline


# The one alarm that is not about any report.
NOTHING_RAN = "autosync::nothing-ran"


def alarms_for(
    rows: Sequence[Row],
    quiet: Optional[NothingRan],
    stray: Optional[Dict[str, Sequence[str]]] = None,
) -> List[Alarm]:
    """Everything worth telling somebody, loudest first.

    **THE QUIET ALARM IS ALWAYS FIRST AND IS ITS OWN LOUDNESS.** A board full of
    missing days is the SYMPTOM of nothing running. Sent as twenty "report X is
    late" messages, it sends a person to fix twenty reports when the answer is
    that the fetcher is not running at all -- which is exactly what a month of the
    reference's summaries did.
    """
    out: List[Alarm] = []

    if quiet is not None:
        out.append(
            Alarm(
                key=NOTHING_RAN,
                loudness=STOP,
                headline=(
                    "Nothing is being fetched."
                    if quiet.last_run_on is None
                    else f"Nothing has been fetched for {quiet.days_quiet} days."
                ),
                what_it_means=quiet.message,
            )
        )

    for report_id, names in sorted((stray or {}).items()):
        out.append(
            Alarm(
                key=f"autosync::unreachable::{report_id}",
                loudness=ACT,
                headline=f"{report_id}: {len(names)} file(s) nothing can match to a day.",
                what_it_means=(
                    f"These files are in the folder and no reader can find them, because their "
                    f"names carry no date: {', '.join(sorted(names)[:5])}"
                    + ("..." if len(names) > 5 else "")
                    + ". The data is there and unreachable. Renaming them with the day they "
                    "cover is what makes them count."
                ),
            )
        )

    # **ONE ALARM PER REPORT, NOT PER DAY.** A report broken for three weeks is one
    # problem. Twenty-one messages about it is how the real ones get lost.
    worst: Dict[str, Row] = {}
    for row in rows:
        if not row.is_a_problem or not row.ask_a_person:
            continue
        standing = worst.get(row.report_id)
        if standing is None or row.days_late > standing.days_late:
            worst[row.report_id] = row

    for report_id, row in sorted(worst.items()):
        how_many = len([r for r in rows if r.report_id == report_id and r.is_a_problem and r.ask_a_person])
        # **THE RECORDED REASON OR NOTHING.** Never a sentence invented to fill it.
        because = f" {row.why_not}" if row.why_not else ""
        days = "day" if how_many == 1 else "days"
        out.append(
            Alarm(
                key=f"autosync::late::{report_id}",
                loudness=ACT,
                headline=f"{report_id} is {row.days_late} days behind.",
                what_it_means=(
                    f"{how_many} {days} of {report_id} have not arrived, the oldest being "
                    f"{row.data_date}.{because}"
                ),
            )
        )

    return worst_first(out)


def worst_first(alarms: Sequence[Alarm]) -> List[Alarm]:
    """Loudest first, and within a loudness, in a settled order.

    Sorted by key within a loudness rather than left in whatever order they were
    built. **The same facts must produce the same list every time**, or "has this
    changed since I last looked" cannot be asked -- which is the question the
    whole of `what_changed` rests on.
    """
    return sorted(alarms, key=lambda a: (LOUDNESS.get(a.loudness, 99), a.key))


@dataclass(frozen=True)
class Changes:
    """What is new, what has gone, and what is simply still true."""

    raised: Tuple[Alarm, ...]
    cleared: Tuple[str, ...]
    still: Tuple[Alarm, ...]

    @property
    def anything_to_send(self) -> bool:
        """**ONLY A CHANGE IS WORTH SENDING.** Something still true is on the board
        for anybody who looks; sending it again every night is how a channel gets
        muted, and a muted channel is worse than none."""
        return bool(self.raised or self.cleared)


def what_changed(standing: Iterable[str], now: Sequence[Alarm]) -> Changes:
    """What is different since last time.

    `standing` is the keys that were already raised. **Keys, not alarms** -- what
    is kept between runs is the smallest thing that answers the question, so a
    stored alarm cannot go stale against a changed message.

    **AN ALARM CLEARS BECAUSE THE CONDITION WENT, and for no other reason.**
    Nothing here takes a dismissal. A problem somebody decided to stop seeing is
    exactly what this package exists to prevent.
    """
    was: Set[str] = set(standing or ())
    ordered = worst_first(now)
    is_now = {a.key: a for a in ordered}
    raised = tuple(a for a in ordered if a.key not in was)
    still = tuple(a for a in ordered if a.key in was)
    # Sorted so the answer is the same every time it is asked.
    cleared = tuple(sorted(was - set(is_now)))
    return Changes(raised=raised, cleared=cleared, still=still)


def to_send(changes: Changes) -> List[str]:
    """The lines to send out, or nothing at all.

    **NOTHING IS SENT WHEN NOTHING CHANGED**, and that is a decision rather than a
    saving. The reference posted a summary after every run whether or not anything
    had moved; twenty-six days of "these are missing" trained everybody to ignore
    it, and the day something new broke it looked exactly like the day before.
    """
    if not changes.anything_to_send:
        return []
    lines: List[str] = []
    for alarm in changes.raised:
        lines.append(f"{alarm.headline} {alarm.what_it_means}")
    for key in changes.cleared:
        # **A FIX IS WORTH SAYING TOO.** Only ever hearing about breakage teaches
        # people that the channel is bad news, and then nobody reads it.
        lines.append(f"Fixed: {key} is no longer a problem.")
    return lines
