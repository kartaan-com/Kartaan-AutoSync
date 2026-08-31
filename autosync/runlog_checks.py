"""Checks for the run log.

**THE THREE CENTRAL CHECKS HERE REPRODUCE THE THREE REAL FAULTS**, each one
proved by making the new code do the thing the old code could not:

  1. A run that ends on a login prompt still writes its evidence. In the
     reference this path skipped the only flush there was, and 25 August's seven
     real uploads left no trace in any of the three layers.
  2. A flush that fails leaves the lines to go again. In the reference the marker
     was the clock, and a restart discarded a whole run's evidence.
  3. A reason belongs to its report and is cleared only by that report's success.
     In the reference it lived in a list wiped at the start of every run,
     including an unrelated one-report recheck.

Run: python autosync/runlog_checks.py
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import runlog as tool  # noqa: E402

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


def refuses(fn):
    try:
        fn()
    except (ValueError, KeyError, TypeError):
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


AT = datetime(2026, 8, 25, 16, 44, 26)
tick = [0]


def now():
    tick[0] += 1
    return AT + timedelta(seconds=tick[0])


class Sink:
    """A place lines go. Records what it was given; can be made to fail."""

    def __init__(self, refuse=False):
        self.batches = []
        self.refuse = refuse

    def __call__(self, lines):
        if self.refuse:
            raise RuntimeError("Drive is not answering")
        self.batches.append(tuple(lines))

    @property
    def lines(self):
        return tuple(line for batch in self.batches for line in batch)


# ------------------------------------------------------------ writing a line

log = tool.RunLog("run-1")
one = log.say("me_orders", tool.WORKING, "Started.", AT)
check("a line carries all five fields", answered(lambda: (one.at, one.run, one.report, one.level, one.message) == (AT, "run-1", "me_orders", tool.WORKING, "Started.")))
check("both doors would write the same shape", answered(lambda: len(one.as_row()) == 5))
check("the time is written to the second", answered(lambda: one.as_row()[0] == "2026-08-25T16:44:26"))
check("a level nobody knows is refused", answered(lambda: refuses(lambda: log.say("x", "shouting", "m", AT))))
check("a line with no message in it is refused", answered(lambda: refuses(lambda: log.say("x", tool.WORKING, "   ", AT))))
check("a run with no name is refused", answered(lambda: refuses(lambda: tool.RunLog(""))))
check("a line about nothing in particular belongs to the system", answered(lambda: log.say("", tool.WORKING, "m", AT).report == tool.SYSTEM))

# ------------------------------------------------- the reason belongs to its report

log = tool.RunLog("run-2")
log.failed("me_orders", "Download Orders Data button not found", AT)
check("a failure records its reason against its own report", answered(lambda: log.reason_for("me_orders") == "Download Orders Data button not found"))
check("a report that has not failed has no reason", answered(lambda: log.reason_for("fk_views") is None))

# **THE REAL FAULT: an unrelated report failing and succeeding must not touch it.**
log.failed("fk_views", "Custom Dates button not found", AT)
log.done("fk_views", "Uploaded.", AT)
check(
    "another report succeeding does not wipe this one's reason",
    answered(lambda: log.reason_for("me_orders") == "Download Orders Data button not found"),
)
check("and that other report's own reason is cleared by its own success", answered(lambda: log.reason_for("fk_views") is None))
# Only its OWN success clears it.
log.done("me_orders", "Uploaded.", AT)
check("its own success clears it", answered(lambda: log.reason_for("me_orders") is None))
check("and the list of failing reports is empty again", answered(lambda: log.failed_reports() == ()))

# A system line is not a report and must not create a reason for one.
log2 = tool.RunLog("run-2b")
log2.failed(tool.SYSTEM, "the whole run stopped", AT)
check("a system failure does not invent a reason for a report", answered(lambda: log2.failed_reports() == ()))

# ------------------------------------------------------------------ flushing

sink = Sink()
log = tool.RunLog("run-3")
log.working("me_orders", "one", AT)
log.working("me_orders", "two", AT)
check("a flush sends everything not yet sent", answered(lambda: log.flush(sink) == 2))
check("and the sink really got them", answered(lambda: len(sink.lines) == 2))
check("nothing left waiting afterwards", answered(lambda: log.waiting_to_flush() == ()))
check("flushing again with nothing to send sends nothing", answered(lambda: log.flush(sink) == 0))
check("and does not call the sink at all", answered(lambda: len(sink.batches) == 1))

# **THE MARKER MOVES ONLY IF THE SINK RETURNED.** The reference read its marker
# from the clock, so a mid-day restart discarded the start of a run for ever.
log = tool.RunLog("run-4")
log.working("me_orders", "one", AT)
log.working("me_orders", "two", AT)
refused = Sink(refuse=True)
threw = False
try:
    log.flush(refused)
except RuntimeError:
    threw = True
check("a flush that cannot get out says so rather than swallowing it", answered(lambda: threw is True))
check("and the lines are still waiting to go", answered(lambda: len(log.waiting_to_flush()) == 2))
working_now = Sink()
check("so the next flush carries them", answered(lambda: log.flush(working_now) == 2))
check("and nothing was lost", answered(lambda: len(working_now.lines) == 2))

# ------------------------------------------- A RUN THAT ENDS ANY WAY STILL FLUSHES

# **THE 25 AUGUST FAULT, REPRODUCED.** Seven Meesho files really uploaded, the run
# stopped on a login prompt, and the reference wrote nothing anywhere.
sink = Sink()
tick[0] = 0
with tool.Run("run-ordinary", sink, now) as run:
    run.log.done("me_orders", "Uploaded meesho_orders.", now())
check("an ordinary run flushes on the way out", answered(lambda: len(sink.lines) >= 2))
check("and says it finished", answered(lambda: any(line.level == tool.DONE and "finished" in line.message for line in sink.lines)))

# The interrupted one. This is the case the reference lost.
sink = Sink()
tick[0] = 0
stopped = False
try:
    with tool.Run("run-login", sink, now) as run:
        run.log.done("me_orders", "Uploaded meesho_orders.", now())
        run.log.done("me_returns", "Uploaded meesho_returns.", now())
        raise RuntimeError("Login required - open seller.flipkart.com")
except RuntimeError:
    stopped = True

check("a run stopped by a login prompt still leaves the block", answered(lambda: stopped is True))
# **THE WHOLE POINT.** The reference wrote nothing here.
check("and its evidence still got out", answered(lambda: len(sink.lines) > 0))
check(
    "including the work that really succeeded before it stopped",
    answered(lambda: any("Uploaded meesho_orders" in line.message for line in sink.lines)
    and any("Uploaded meesho_returns" in line.message for line in sink.lines)),
)
check(
    "and what stopped it, in the evidence rather than only in whatever caught it",
    answered(lambda: any(line.level == tool.FAILED and "Login required" in line.message for line in sink.lines)),
)
check(
    "the run is never reported as having finished",
    answered(lambda: not any(line.level == tool.DONE and "finished" in line.message for line in sink.lines)),
)

# **THERE IS NO WAY OUT THAT SKIPS THE FLUSH**, and that is what makes this
# structural rather than remembered. A `return` from inside the block is a third
# way out -- neither finishing nor throwing -- and it is the shape the reference's
# login path actually had: it returned early, and the flush was after it.
sink = Sink()
tick[0] = 0


def gives_up_early(the_sink):
    with tool.Run("run-returns-early", the_sink, now) as run:
        run.log.done("me_orders", "Uploaded before giving up.", now())
        return "gave up"
    # unreachable; here only to show there is nothing after the block to rely on


what_it_gave_back = gives_up_early(sink)
check("a run left by returning early still flushes", answered(lambda: len(sink.lines) > 0))
check("and the work it did got out with it", answered(lambda: any("Uploaded before giving up" in l.message for l in sink.lines)))
check("and the caller still gets its answer", answered(lambda: what_it_gave_back == "gave up"))

# A flush that fails on the way out must not replace the reason the run ended.
sink = Sink(refuse=True)
tick[0] = 0
right_reason = None
try:
    with tool.Run("run-both-broken", sink, now) as run:
        raise RuntimeError("Login required")
except RuntimeError as e:
    right_reason = str(e)
check("when the run failed AND the flush failed, the run's own reason is the one raised", answered(lambda: right_reason == "Login required"))

sink = Sink(refuse=True)
tick[0] = 0
clean = True
try:
    with tool.Run("run-clean-bad-flush", sink, now) as run:
        run.log.done("me_orders", "Uploaded.", now())
except Exception:  # noqa: BLE001
    clean = False
check("a failed flush does not turn a clean run into a failed one", answered(lambda: clean is True))
check("but it is recorded where the caller can see it", answered(lambda: run.could_not_flush is not None))
check("and the lines are still there to go again", answered(lambda: len(run.log.waiting_to_flush()) > 0))

# ------------------------------------------------------------ nothing is hidden

log = tool.RunLog("run-5")
log.working("a", "m", AT)
lines = log.lines
check("the lines can be read", answered(lambda: len(lines) == 1))
# Handed out as a tuple, so a caller cannot append to it and change the log
# underneath. The reference handed out its own array and a viewer trimmed it.
check("and what is handed out cannot be edited to change the log", answered(lambda: isinstance(lines, tuple)))
check("and the same is true of what is waiting to go", answered(lambda: isinstance(log.waiting_to_flush(), tuple)))


# ------------------------------------------------- the ends nothing else reached

# A log line is frozen: what a reader is holding must not change underneath it.
was_refused = False
try:
    one.message = "something else"
except AttributeError:
    was_refused = True
check("a log line cannot be edited after it is written", answered(lambda: was_refused is True))

# `warning` is a real level and a real way in. Unused in the cases above, which is
# how a level quietly stops working.
warn_log = tool.RunLog("run-warn")
check("a warning is written at the warning level", answered(lambda: warn_log.warning("me_orders", "took longer than usual", AT).level == tool.WARNING))
# **AND A WARNING IS NOT A FAILURE.** It must not put a reason against the report,
# or every slow run would read afterwards as a broken one.
check("and a warning does not record a failure reason", answered(lambda: warn_log.reason_for("me_orders") is None))

# **BOTH HALVES OF "a success clears its own report's reason".** A DONE line about
# the system, or about nothing in particular, must not clear a real report's
# reason -- the reference wiped reasons from an unrelated place and that is the
# fault this guard exists for.
guard = tool.RunLog("run-guard")
guard.failed("me_orders", "button not found", AT)
guard.done(tool.SYSTEM, "Run finished.", AT)
check("a system success does not clear a report's reason", answered(lambda: guard.reason_for("me_orders") == "button not found"))
guard.done("", "finished", AT)
check("nor does a success about nothing in particular", answered(lambda: guard.reason_for("me_orders") == "button not found"))
guard.done("me_orders", "Uploaded.", AT)
check("only its own success does", answered(lambda: guard.reason_for("me_orders") is None))

# **THE WHOLE TABLE, because one case cannot tell three conditions apart.** Only a
# DONE line, about that report by name, clears it. Every other combination leaves
# it standing -- and the reference's fault was precisely that something else could
# clear it.
def after(level, report_id):
    log = tool.RunLog("table")
    log.failed("me_orders", "boom", AT)
    log.say(report_id, level, "m", AT)
    return log.reason_for("me_orders")


check("a working line about that report does not clear its reason", answered(lambda: after(tool.WORKING, "me_orders") == "boom"))
check("a warning about that report does not clear its reason", answered(lambda: after(tool.WARNING, "me_orders") == "boom"))
check("a done line about that report clears it", answered(lambda: after(tool.DONE, "me_orders") is None))
check("a done line about the system does not", answered(lambda: after(tool.DONE, tool.SYSTEM) == "boom"))
check("a done line about nothing in particular does not", answered(lambda: after(tool.DONE, "") == "boom"))
check("a done line about a DIFFERENT report does not", answered(lambda: after(tool.DONE, "fk_views") == "boom"))

# A run says it started, in the evidence -- so a run that began and vanished can be
# told apart from one that never began.
sink = Sink()
tick[0] = 0
with tool.Run("beginning-line", sink, now):
    pass
check("a run writes that it started", answered(lambda: any("started" in line.message for line in sink.lines)))
check("and names itself in that line", answered(lambda: any("beginning-line" in line.message for line in sink.lines)))

# A clean run has nothing to say about a failed flush.
sink = Sink()
tick[0] = 0
with tool.Run("run-clean", sink, now) as clean_run:
    clean_run.log.done("me_orders", "Uploaded.", now())
check("a run whose flush worked reports no flush trouble", answered(lambda: clean_run.could_not_flush is None))


# **AND NOTHING ABOVE ENDED BY THROWING RATHER THAN BY ANSWERING.** Answering
# with nothing keeps the run alive; this is what stops a check phrased as "this
# word is NOT in what it said" going green because there was nothing to look in.
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)


EXPECTED = 56
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
