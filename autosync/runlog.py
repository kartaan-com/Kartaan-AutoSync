"""The run log. Shape 2 of the contract (D100), and the first of the three layers.

**BOTH DOORS WRITE THE SAME FIVE THINGS**, so one screen reads both without
knowing which door a line came from: `at`, `run`, `report`, `level`, `message`.

Three faults from the working reference are fixed here, and two of them are fixed
STRUCTURALLY -- made impossible rather than remembered:

**1. A RUN THAT ENDS ANY OTHER WAY THAN FINISHING WROTE NOTHING AT ALL.**
    Found live on 2026-08-27. Its `handlePanelLoginRequired` set the run to
    stopped and never called `finishSync()` -- and `finishSync()` was the only
    place the log was flushed, the day board written, and the summary sent. On
    25 August seven files really uploaded, the run stopped on a login prompt, and
    **every layer that exists to record it stayed silent.** The three log layers
    read as if nothing had happened since the 24th.
    **Fixed by making the run a context manager: leaving the block flushes,
    whether the body finished, raised, or gave up.** There is no path out that
    skips it, so there is no path that can forget.

**2. THE FLUSH READ FROM "WHEN THIS RUN STARTED".**
    A restart mid-day moved that marker and discarded the whole start of a run --
    on 3 August the entire Flipkart head of the queue failed and left no trace.
    **Fixed: the marker only ever advances over lines a sink actually accepted.**
    A sink that throws leaves the marker where it was, so the next flush carries
    them again. Losing evidence is never the cheaper failure.

**3. A FAILURE REASON WAS WIPED BY AN UNRELATED RUN.**
    The reason lived in a list cleared at the start of EVERY run, including a
    one-report recheck for something else entirely, so the real reason vanished
    before anybody read it. **Fixed: a reason is kept against its own report id
    and cleared only by that same report's next success.**

**AND A REASON IS NEVER INVENTED.** A report that has not run yet, or skipped
itself on purpose, has no reason and says nothing. A made-up one sends whoever
reads it looking in the wrong place -- which is worse than silence, because it
looks like an answer.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional, Sequence

# What a line can be. Four, from the contract.
WORKING = "working"
WARNING = "warning"
FAILED = "failed"
DONE = "done"
LEVELS = (WORKING, WARNING, FAILED, DONE)

# The report id used for anything that is not about one report.
SYSTEM = "system"


@dataclass(frozen=True)
class Line:
    """One line of the run log. Five fields, the same from either door."""

    at: datetime
    run: str
    report: str
    level: str
    message: str
    # **WHICH LINE OF THE RUN THIS IS, counted from one (cycle 46, R2#18).**
    #
    # A line is written at a name worked out from the line itself, so a retried
    # flush writes it once rather than twice (D93). **But two genuinely different
    # lines identical in all five fields -- same report, same level, same second,
    # same words -- collapsed into one, and a log quietly losing a line is the
    # thing this package exists against.**
    #
    # Its place in the run tells them apart, and it is STABLE across a retry: the
    # same lines, in the same order, are flushed again. A finer clock would not
    # be -- two lines can share a millisecond, and nothing here reaches for a
    # clock anyway.
    #
    # **NOT ON `as_row`**, because the Drive copy is a file read by a person and
    # the order of the lines is already the order of the lines.
    place: int = 0

    def as_row(self) -> Sequence[str]:
        """The line as plain text, for the copy that goes to the seller's Drive.

        **SECONDS, NOT MILLISECONDS, AND NO TIMEZONE GUESSING.** The caller hands
        in the moment it wants recorded; this does not reach for a clock, so a
        check can ask about a particular second.
        """
        return (self.at.isoformat(timespec="seconds"), self.run, self.report, self.level, self.message)


class RunLog:
    """Every line of one run, and what has been got safely out of the building.

    **IT KEEPS TWO THINGS, and they are different questions:** the lines, and how
    far a sink has actually accepted them. The reference kept only the first and
    inferred the second from the clock, which is what lost a whole run's evidence.
    """

    def __init__(self, run: str):
        if not run:
            raise ValueError("A run has to have a name, so its lines can be told apart.")
        self.run = run
        self._lines: List[Line] = []
        # How many lines a sink has accepted. Advances only on success.
        self._flushed = 0
        # report id -> the reason it last failed. Cleared only by its own success.
        self._reasons: Dict[str, str] = {}

    # ------------------------------------------------------------ writing

    def say(self, report: str, level: str, message: str, at: datetime) -> Line:
        """Write one line.

        The moment is passed in rather than read from a clock here, for the same
        reason every date in this package is: a check has to be able to ask about
        a particular second, and a bound nothing can shorten is a bound nothing
        can prove.
        """
        if level not in LEVELS:
            raise ValueError(f"{level!r} is not a level. It is one of {', '.join(LEVELS)}.")
        if not str(message).strip():
            raise ValueError("A log line with no message in it says nothing.")
        line = Line(at=at, run=self.run, report=report or SYSTEM, level=level,
                    message=message, place=len(self._lines) + 1)
        self._lines.append(line)
        # **THE REASON IS KEPT AGAINST ITS OWN REPORT, and cleared only by that
        # report's own success.** Never by an unrelated run starting.
        if level == FAILED and report and report != SYSTEM:
            self._reasons[report] = message
        elif level == DONE and report and report != SYSTEM:
            self._reasons.pop(report, None)
        return line

    def working(self, report: str, message: str, at: datetime) -> Line:
        return self.say(report, WORKING, message, at)

    def warning(self, report: str, message: str, at: datetime) -> Line:
        return self.say(report, WARNING, message, at)

    def failed(self, report: str, message: str, at: datetime) -> Line:
        return self.say(report, FAILED, message, at)

    def done(self, report: str, message: str, at: datetime) -> Line:
        return self.say(report, DONE, message, at)

    # ------------------------------------------------------------ reading

    @property
    def lines(self) -> Sequence[Line]:
        """Everything written this run. A copy, so nothing outside can edit it."""
        return tuple(self._lines)

    def waiting_to_flush(self) -> Sequence[Line]:
        """The lines no sink has accepted yet."""
        return tuple(self._lines[self._flushed:])

    def reason_for(self, report: str) -> Optional[str]:
        """Why this report last failed, or None if it has not.

        **None IS AN ANSWER AND IT MEANS NOTHING IS RECORDED.** Whoever shows this
        says nothing rather than inventing something -- a report that has not run
        yet and a report that failed for an unknown reason must not read alike.
        """
        return self._reasons.get(report)

    def failed_reports(self) -> Sequence[str]:
        """Every report with a reason standing against it, in the order they failed."""
        return tuple(self._reasons.keys())

    # ------------------------------------------------------------ flushing

    def flush(self, sink: Callable[[Sequence[Line]], None]) -> int:
        """Hand everything not yet accepted to `sink`, and say how many went.

        **THE MARKER MOVES ONLY IF THE SINK RETURNED.** If it throws -- the network
        is down, Drive refuses, the token expired -- the marker stays where it was
        and those lines go again on the next flush. Duplicated evidence is a
        nuisance; lost evidence is a day of not knowing what happened.

        Nothing to send is not an error, and does not call the sink at all.
        """
        pending = self.waiting_to_flush()
        if not pending:
            return 0
        sink(pending)
        self._flushed += len(pending)
        return len(pending)


class Run:
    """One run of the fetcher, from start to whatever ends it.

    **LEAVING THIS BLOCK FLUSHES, whatever ended it.** Finished, threw, gave up
    on a login prompt, was interrupted -- all of them go through `__exit__`, and
    `__exit__` flushes. That is the whole point: the reference's flush lived on
    one path out of several, and the paths that skipped it were exactly the ones
    where the evidence mattered most.

    An exception is never swallowed. It is recorded and re-raised, because a run
    that failed and reported success is the fault this whole package is built
    against.
    """

    def __init__(self, name: str, sink: Callable[[Sequence[Line]], None], now: Callable[[], datetime]):
        self.log = RunLog(name)
        self._sink = sink
        self._now = now
        # Set when the flush on the way out could not get the lines away.
        self.could_not_flush: Optional[str] = None

    def __enter__(self) -> "Run":
        self.log.working(SYSTEM, f"Run {self.log.run} started.", self._now())
        return self

    def __exit__(self, kind, value, traceback) -> bool:
        if value is not None:
            # **SAID IN THE LOG BEFORE THE FLUSH, so the thing that ended the run
            # is inside the evidence rather than only in whatever caught it.**
            self.log.failed(SYSTEM, f"Run {self.log.run} stopped: {value}", self._now())
        else:
            self.log.done(SYSTEM, f"Run {self.log.run} finished.", self._now())
        try:
            self.log.flush(self._sink)
        except Exception as flushing:  # noqa: BLE001 - reported, never swallowed
            # **NOTHING IS RE-RAISED FROM HERE.** A failed flush must not replace
            # the real reason the run ended, and must not turn a clean run into a
            # failed one. It is recorded on the run, where the caller can see it,
            # and the unflushed lines are still in the log to go again.
            self.could_not_flush = str(flushing)
        # False: never swallow whatever ended the run.
        return False
