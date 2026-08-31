"""Checks for one run.

**THE THREE THAT MATTER, and the reference failed all three:**

  1. **A run that is interrupted still leaves its evidence, and the next one
     carries on.** On 25 August its run stopped on a login prompt, seven files had
     really uploaded, and all three log layers stayed silent.
  2. **A report already asked for is never asked for again.** `createReport` is one
     call a minute; asking twice leaves two reports being built and spends a
     rationed call for nothing.
  3. **One report failing never stops the rest.** Its queue died at the first login
     prompt and abandoned everything behind it -- on 25 August, every Flipkart
     report of the day.

Run: python autosync/runner_checks.py
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import runner as tool  # noqa: E402
import runlog  # noqa: E402
from landing import Arrived  # noqa: E402
from reports import BROWSER, DAILY, ONLY_WHEN_ASKED, Report  # noqa: E402

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
TODAY = DAY("2026-08-27")
AT = datetime(2026, 8, 27, 16, 0, 0)

ORDERS = Report("me_orders", "meesho", "Meesho orders", BROWSER, DAILY, "csv")
RETURNS = Report("me_returns", "meesho", "Meesho returns", BROWSER, DAILY, "csv")


class Tick:
    def __init__(self):
        self.n = 0

    def __call__(self):
        self.n += 1
        return AT + timedelta(seconds=self.n)


class Answered:
    """What a door answers. Deliberately the shape the Amazon door really gives."""

    def __init__(self, state, say="", their_id=None):
        self.state = state
        self.say = say
        self.their_id = their_id


def a_door(by_report=None, throw_for=None, default=tool.LANDED):
    """A door that answers what it is told to, and records what it was asked."""
    asked = []

    def fetch(report_id, data_date, asked_already=None):
        asked.append({"report": report_id, "day": data_date, "asked_already": asked_already})
        if throw_for and report_id in throw_for:
            raise RuntimeError(f"the door fell over on {report_id}")
        answer = (by_report or {}).get(report_id)
        if answer is None:
            return Answered(default, say="landed something")
        return answer

    fetch.asked = asked
    return fetch


def nothing_arrived(_report_id):
    return []


def collect():
    got = []

    def sink(lines):
        got.extend(lines)

    sink.lines = got
    return sink


# ------------------------------------------------------------ an ordinary run

sink = collect()
flight = tool.InFlight()
door = a_door()
what = tool.do_a_run("run-1", [ORDERS], door, nothing_arrived, flight, sink, Tick(), TODAY, look_back_days=2)
check("a run tries everything that is owed", answered(lambda: what.tried == 2))
check("and says what landed", answered(lambda: len(what.landed) == 2))
check("and how many it tried, not only how many worked", answered(lambda: "2 tried" in what.summary()))
check("and the evidence got out", answered(lambda: len(sink.lines) > 0))
check("including that the run finished", answered(lambda: any("finished" in l.message for l in sink.lines)))
check("a report only owed once is only asked for once per day",
      answered(lambda: len({(a["report"], a["day"]) for a in door.asked}) == 2))

# Nothing owed is a real state and is said, rather than the run looking empty.
sink = collect()
have = lambda _r: [Arrived(f"meesho_me_orders_2026-08-{d}.csv", 900) for d in range(20, 27)]
what = tool.do_a_run("run-none", [ORDERS], a_door(), have, tool.InFlight(), sink, Tick(), TODAY, look_back_days=2)
check("a run with nothing owed tries nothing", answered(lambda: what.tried == 0))
check("and says so out loud", answered(lambda: any("Nothing is owed" in l.message for l in sink.lines)))
check("and still records that it ran", answered(lambda: any("started" in l.message for l in sink.lines)))

# A report that only runs when asked is never picked up by itself.
ASKED_ONLY = Report("fk_extra", "flipkart", "Only when asked", BROWSER, ONLY_WHEN_ASKED, "csv")
what = tool.do_a_run("run-2", [ASKED_ONLY], a_door(), nothing_arrived, tool.InFlight(), collect(), Tick(), TODAY)
check("a report that only runs when asked is left alone", answered(lambda: what.tried == 0))

# --------------------------------- ONE REPORT FAILING NEVER STOPS THE REST

sink = collect()
door = a_door(by_report={"me_orders": Answered(tool.FAILED, say="button not found")})
what = tool.do_a_run("run-3", [ORDERS, RETURNS], door, nothing_arrived, tool.InFlight(), sink, Tick(), TODAY, look_back_days=1)
check("one report failing does not stop the other", answered(lambda: len(what.landed) == 1))
check("and the failure is recorded against its own report", answered(lambda: len(what.failed) == 1))
check("both were tried", answered(lambda: what.tried == 2))

# **EVEN WHEN THE DOOR ITSELF FALLS OVER.** The reference's queue died here.
sink = collect()
door = a_door(throw_for={"me_orders"})
what = tool.do_a_run("run-4", [ORDERS, RETURNS], door, nothing_arrived, tool.InFlight(), sink, Tick(), TODAY, look_back_days=1)
check("a door that throws on one report does not stop the run", answered(lambda: len(what.landed) == 1))
check("the one that threw is recorded as failed", answered(lambda: what.failed == ("me_orders",)))
check("and what it threw is in the log, not swallowed",
      answered(lambda: any("fell over on me_orders" in l.message for l in sink.lines)))
check("and it is recorded against that report, not the system",
      answered(lambda: any(l.report == "me_orders" and l.level == runlog.FAILED for l in sink.lines)))

# ------------------------- A REPORT ALREADY ASKED FOR IS NEVER ASKED AGAIN

sink = collect()
flight = tool.InFlight()
door = a_door(by_report={"me_orders": Answered(tool.STILL_WAITING, say="still building", their_id="report-1")})
tool.do_a_run("run-5", [ORDERS], door, nothing_arrived, flight, sink, Tick(), TODAY, look_back_days=1)
check("a report still being built is remembered", answered(lambda: flight.what_was_asked("me_orders", DAY("2026-08-26")) == "report-1"))
check("and the first run was told nothing was already asked", answered(lambda: door.asked[0]["asked_already"] is None))

# The next run must hand that id back to the door.
door2 = a_door(by_report={"me_orders": Answered(tool.LANDED, say="landed at last")})
tool.do_a_run("run-6", [ORDERS], door2, nothing_arrived, flight, collect(), Tick(), TODAY, look_back_days=1)
check("the NEXT run hands the door what was already asked for", answered(lambda: door2.asked[0]["asked_already"] == "report-1"))
# **FORGOTTEN ONLY ONCE IT HAS LANDED**, so a run that fell over between asking
# and collecting does not ask again.
check("and it is forgotten once it has landed", answered(lambda: flight.what_was_asked("me_orders", DAY("2026-08-26")) is None))

# Two days of one report can be in flight at once, and they are not the same thing.
flight = tool.InFlight()
flight.remember("me_orders", DAY("2026-08-25"), "report-a")
flight.remember("me_orders", DAY("2026-08-26"), "report-b")
check("two days of one report are remembered apart",
      answered(lambda: flight.what_was_asked("me_orders", DAY("2026-08-25")) == "report-a"
      and flight.what_was_asked("me_orders", DAY("2026-08-26")) == "report-b"))
flight.forget("me_orders", DAY("2026-08-25"))
check("and forgetting one leaves the other", answered(lambda: flight.what_was_asked("me_orders", DAY("2026-08-26")) == "report-b"))
check("forgetting one that is not there is not an error", answered(lambda: flight.forget("me_orders", DAY("2026-01-01")) is None))

# A door that says it is waiting but names nothing leaves nothing to collect by --
# so the next run must ask, rather than wait for something it cannot name.
flight = tool.InFlight()
door = a_door(by_report={"me_orders": Answered(tool.STILL_WAITING, say="waiting", their_id=None)})
tool.do_a_run("run-7", [ORDERS], door, nothing_arrived, flight, collect(), Tick(), TODAY, look_back_days=1)
check("a wait with no id to collect by remembers nothing", answered(lambda: flight.what_was_asked("me_orders", DAY("2026-08-26")) is None))

# ------------------------------------- nothing-to-fetch is not a failure

sink = collect()
door = a_door(by_report={"me_orders": Answered(tool.NOTHING_TO_FETCH, say="Amazon had no data for that day")})
what = tool.do_a_run("run-8", [ORDERS], door, nothing_arrived, tool.InFlight(), sink, Tick(), TODAY, look_back_days=1)
check("a day with nothing to fetch is not a failure", answered(lambda: what.failed == ()))
check("it is counted as its own thing", answered(lambda: len(what.nothing_to_fetch) == 1))
# **RECORDED AS A WARNING, NOT AS DONE.** A `done` line clears any real failure
# standing against that report -- so a quiet day would wipe a genuine reason.
check("and recorded as a warning, so it does not clear a real failure",
      answered(lambda: any(l.report == "me_orders" and l.level == runlog.WARNING for l in sink.lines)))
standing = runlog.RunLog("x")
standing.failed("me_orders", "a real problem", AT)
standing.warning("me_orders", "nothing to fetch today", AT)
check("proving it: a warning really does leave a standing reason alone",
      answered(lambda: standing.reason_for("me_orders") == "a real problem"))

# ------------------------- A RUN THAT IS INTERRUPTED STILL LEAVES EVIDENCE

# **THE 25 AUGUST FAULT, at the level it actually happened.**
sink = collect()
flight = tool.InFlight()


def door_that_dies(report_id, data_date, asked_already=None):
    if report_id == "me_returns":
        raise KeyboardInterrupt("the machine went to sleep")
    return Answered(tool.LANDED, say="landed before the interruption")


stopped = False
try:
    tool.do_a_run("run-9", [ORDERS, RETURNS], door_that_dies, nothing_arrived, flight, sink, Tick(), TODAY, look_back_days=1)
except KeyboardInterrupt:
    stopped = True

check("a run stopped by something outside it really stops", answered(lambda: stopped is True))
# **AND ITS EVIDENCE STILL GOT OUT.** This is what the reference lost.
check("and its evidence still got out", answered(lambda: len(sink.lines) > 0))
check("including the work that really succeeded first",
      answered(lambda: any("landed before the interruption" in l.message for l in sink.lines)))
check("and what stopped it", answered(lambda: any("went to sleep" in l.message for l in sink.lines)))
check("and it is never recorded as having finished",
      answered(lambda: not any(l.level == runlog.DONE and "finished" in l.message for l in sink.lines)))

# ------------------------------------------ the board and the alarms, on the record

# **NOTHING HERE NEEDS A RUN TO BE HAPPENING**, which is the whole reason
# "nothing ran" can fire at all.
rows, raised = tool.look([ORDERS], nothing_arrived, run_days=[DAY("2026-08-25")], today=TODAY, look_back_days=3)
check("the board can be had without a run happening", answered(lambda: len(rows) > 0))
check("and the alarms with it", answered(lambda: len(raised) > 0))
check("and nothing running is the loudest of them", answered(lambda: raised[0].loudness == "stop"))

# A healthy day says nothing at all.
rows, raised = tool.look(
    [ORDERS],
    lambda _r: [Arrived(f"meesho_me_orders_2026-08-{d}.csv", 900) for d in range(20, 27)],
    run_days=[TODAY], today=TODAY, look_back_days=3,
)
check("a day when everything arrived and something ran raises nothing", answered(lambda: raised == []))

# ------------------------------------------------- only a change is sent

sent = []
raised = tool.look([ORDERS], nothing_arrived, run_days=[DAY("2026-08-25")], today=TODAY, look_back_days=3)[1]
changed = tool.tell_somebody(raised, [], lambda lines: sent.append(lines))
check("the first time, something is sent", answered(lambda: len(sent) == 1))
# **THE STANDING LIST IS BUILT THE WAY THE RUN BUILDS IT** -- raised and still,
# by key. Written any other way, this would be checking a shape nothing uses.
after = [a.key for a in changed.raised + changed.still]
check("and what is standing afterwards is every alarm still true",
      answered(lambda: len(after) == len(raised)))

sent.clear()
changed = tool.tell_somebody(raised, after, lambda lines: sent.append(lines))
check("the second time, with nothing changed, NOTHING is sent", answered(lambda: sent == []))
check("and the standing list is unchanged",
      answered(lambda: [a.key for a in changed.raised + changed.still] == after))

# Once it is fixed, that is sent too.
sent.clear()
changed = tool.tell_somebody([], after, lambda lines: sent.append(lines))
check("when it is fixed, that is sent", answered(lambda: len(sent) == 1))
check("saying it is fixed", answered(lambda: any("Fixed:" in line for line in sent[0])))
check("and nothing is standing afterwards",
      answered(lambda: [a.key for a in changed.raised + changed.still] == []))


# ------------------------------------------- the ends nothing else reached

def _cannot_edit(thing, field, value):
    try:
        setattr(thing, field, value)
    except AttributeError:
        return True
    return False


check("what a run came to cannot be edited afterwards",
      answered(lambda: _cannot_edit(tool.WhatHappened("r", TODAY), "tried", 99)))

# **THE SUMMARY NAMES ALL FOUR OUTCOMES.** Three of them are not failures, and a
# summary that only counted failures would make a day of "nothing to fetch" read
# identically to a day everything worked.
sink = collect()
door = a_door(by_report={
    "me_orders": Answered(tool.NOTHING_TO_FETCH, say="no data that day"),
    "me_returns": Answered(tool.FAILED, say="button not found"),
})
what = tool.do_a_run("run-summary", [ORDERS, RETURNS], door, nothing_arrived, tool.InFlight(), sink, Tick(), TODAY, look_back_days=1)
line = what.summary()
check("the summary says how many landed", answered(lambda: "0 landed" in line))
check("and how many are still coming", answered(lambda: "0 still coming" in line))
check("and how many had nothing to fetch", answered(lambda: "1 had nothing" in line))
check("and how many failed", answered(lambda: "1 failed" in line))

# **THE WAITING LIST IS REAL AND IS CARRIED BACK.** Without it a run where every
# report was still being built looks identical to one that did nothing.
sink = collect()
door = a_door(by_report={"me_orders": Answered(tool.STILL_WAITING, say="still building", their_id="r-9")})
what = tool.do_a_run("run-wait", [ORDERS], door, nothing_arrived, tool.InFlight(), sink, Tick(), TODAY, look_back_days=1)
check("a report still being built is counted as waiting", answered(lambda: what.waiting == ("me_orders",)))
check("and is not counted as landed or failed", answered(lambda: what.landed == () and what.failed == ()))
check("and it is said in the log, against its own report",
      answered(lambda: any(l.report == "me_orders" and l.level == runlog.WORKING and "still building" in l.message for l in sink.lines)))

# **AN IN-FLIGHT REPORT IS FORGOTTEN WHEN THERE IS NOTHING TO COLLECT.** Left
# remembered, every later run would wait for a report that will never arrive.
flight = tool.InFlight()
flight.remember("me_orders", DAY("2026-08-26"), "r-old")
tool.do_a_run("run-none-left", [ORDERS],
              a_door(by_report={"me_orders": Answered(tool.NOTHING_TO_FETCH, say="no data")}),
              nothing_arrived, flight, collect(), Tick(), TODAY, look_back_days=1)
check("a day with nothing to fetch stops being waited for", answered(lambda: flight.what_was_asked("me_orders", DAY("2026-08-26")) is None))

flight = tool.InFlight()
flight.remember("me_orders", DAY("2026-08-26"), "r-old")
tool.do_a_run("run-failed", [ORDERS],
              a_door(by_report={"me_orders": Answered(tool.FAILED, say="fatal")}),
              nothing_arrived, flight, collect(), Tick(), TODAY, look_back_days=1)
check("and so does one that failed outright", answered(lambda: flight.what_was_asked("me_orders", DAY("2026-08-26")) is None))

# A failure is recorded against its own report, so the reason stands against it.
sink = collect()
tool.do_a_run("run-said", [ORDERS],
              a_door(by_report={"me_orders": Answered(tool.FAILED, say="Custom Dates button not found")}),
              nothing_arrived, tool.InFlight(), sink, Tick(), TODAY, look_back_days=1)
check("a failure is recorded against its own report with its own words",
      answered(lambda: any(l.report == "me_orders" and l.level == runlog.FAILED and "Custom Dates" in l.message for l in sink.lines)))
check("and the day it was about is in the line", answered(lambda: any("2026-08-26" in l.message for l in sink.lines)))


# ------------------------- a person naming the days themselves (his ask)

# **THE SAME RUN, TOLD WHICH DAYS INSTEAD OF WORKING THEM OUT.** The reference had
# a separate program for this and that is where its three wrongly-dated duplicate
# files came from: two ways of naming a file is two ways of naming it wrongly.
from schedule import Owed, asked_for_by_hand  # noqa: E402

sink = collect()
door = a_door()
by_hand, refused = asked_for_by_hand([ORDERS], [ORDERS.id],
                                     TODAY - timedelta(days=4), TODAY - timedelta(days=2), TODAY)
what = tool.do_a_run("by-hand", [ORDERS], door, nothing_arrived, tool.InFlight(), sink,
                     Tick(), TODAY, asked_for=by_hand, refused=refused)
check("a run told which days fetches exactly those",
      answered(lambda: what.tried == len(by_hand) and what.tried == 3))
check("and it is the days that were named, not yesterday",
      answered(lambda: [a["day"] for a in door.asked]
               == [TODAY - timedelta(days=4), TODAY - timedelta(days=3), TODAY - timedelta(days=2)]))
# **AND IT SAYS IT WAS ASKED FOR RATHER THAN OWED**, so a person reading the log
# a month later can tell a deliberate re-fetch from a nightly one.
check("the log says the days were asked for by hand",
      answered(lambda: any("asked for by hand" in l.message for l in sink.lines)))
check("and does not call them owed",
      answered(lambda: not any("report-days owed" in l.message for l in sink.lines)))

# **NOTHING OWED IS LOOKED AT AT ALL.** Working out what is owed as well would
# fetch yesterday too, which is not what was asked for.
check("nothing else is fetched alongside them",
      answered(lambda: len(door.asked) == 3))

# **WHAT WAS REFUSED IS IN THE LOG BEFORE ANYTHING IS TRIED**, so somebody who
# asked for six reports and got five sees why -- rather than reading a clean run
# and wondering where the sixth went.
sink2 = collect()
what2 = tool.do_a_run("by-hand-refused", [ORDERS], a_door(), nothing_arrived, tool.InFlight(),
                      sink2, Tick(), TODAY, asked_for=[],
                      refused=["me_payments: it can only ever be caught on the day."])
check("what could not be asked for is said in the log",
      answered(lambda: any("only ever be caught on the day" in l.message for l in sink2.lines)))
check("and it is recorded as a failure, not as a passing remark",
      answered(lambda: any("only ever be caught on the day" in l.message and l.level == runlog.FAILED
                           for l in sink2.lines)))
check("and a run that could fetch nothing still says so",
      answered(lambda: any("Nothing was asked for" in l.message for l in sink2.lines)))
check("and still leaves its evidence behind", answered(lambda: len(sink2.lines) > 1))

# **AN EMPTY LIST IS NOT THE SAME AS NOT ASKING.** Handed nothing to do, the run
# does nothing -- it must not fall back to working out what is owed, or a person
# whose whole request was refused would get a surprise nightly run instead.
check("a run told to fetch nothing fetches nothing", answered(lambda: what2.tried == 0))


# **AND NOTHING ABOVE ENDED BY THROWING RATHER THAN BY ANSWERING.** Answering
# with nothing keeps the run alive; this is what stops a check phrased as "this
# word is NOT in what it said" going green because there was nothing to look in.
# ------------------------- the evidence not leaving the building (D114)

# **`runlog.Run` HAS RECORDED THIS SINCE IT WAS WRITTEN AND NOTHING EVER READ
# IT.** A run whose log reached neither the seller's Drive nor their database
# finished green and silent -- which is the exact failure this package exists
# against. Carried out of the run so `one_tick` can call it our own defect.


def _refuses(lines):
    raise RuntimeError("Drive would not take the log")


lost = answered(lambda: tool.do_a_run(
    name="r1", reports=[ORDERS], fetch=lambda *a, **k: Answered("landed", "Landed."),
    arrivals=lambda report_id: [], in_flight=tool.InFlight(), sink=_refuses,
    now=Tick(), today=TODAY))
check("a run whose log could not be got out says so", bool(lost and lost.could_not_flush))
check("and says what stopped it", "Drive would not take the log" in (lost.could_not_flush or ""))
check("and its summary says it too", "out of the building" in lost.summary())
kept = answered(lambda: tool.do_a_run(
    name="r2", reports=[ORDERS], fetch=lambda *a, **k: Answered("landed", "Landed."),
    arrivals=lambda report_id: [], in_flight=tool.InFlight(), sink=lambda lines: None,
    now=Tick(), today=TODAY))
check("and a run whose log got out says nothing about it", kept.could_not_flush is None)
check("and its summary says nothing about it either", "out of the building" not in kept.summary())

# ------------------- why a report failed, carried out of the run (R2#6)

# **THE RUN HAS RECORDED THIS SINCE `runlog` WAS WRITTEN AND NOTHING CARRIED IT
# OUT.** The day board has one column whose whole job is to say WHY a report is
# late, and it was blank on every row on every night -- a seller was told a
# report was five days late and nothing else. Same shape as `could_not_flush`
# before it: a run ends, and what it knew ends with it unless something takes it.
broke = answered(lambda: tool.do_a_run(
    name="r-why", reports=[ORDERS], fetch=a_door(by_report={ORDERS.id: Answered(tool.FAILED, say="Amazon would not.")}),
    arrivals=nothing_arrived, in_flight=tool.InFlight(), sink=collect(),
    now=Tick(), today=TODAY))
check("a run that failed carries the reason out with it",
      bool(broke and broke.reasons))
check("and it is kept against the report it belongs to",
      answered(lambda: ORDERS.id in broke.reasons))
check("and it says what the door actually said",
      answered(lambda: "Amazon would not." in broke.reasons[ORDERS.id]))

# **AND A CLEAN RUN CARRIES NONE.** A reason standing against a report that
# worked is a reason somebody acts on for nothing.
fine = answered(lambda: tool.do_a_run(
    name="r-fine", reports=[ORDERS], fetch=a_door(),
    arrivals=nothing_arrived, in_flight=tool.InFlight(), sink=collect(),
    now=Tick(), today=TODAY))
check("a run where everything worked carries no reasons at all",
      answered(lambda: dict(fine.reasons) == {}))

# **AND THE BOARD REALLY USES THEM.** Handed the reasons, the row says why; not
# handed them, it says nothing -- which is what was shipping.
rows_with, _ = answered(lambda: tool.look(
    reports=[ORDERS], arrivals=nothing_arrived, run_days=[TODAY], today=TODAY,
    reason_for=broke.reasons.get, failed_ids=broke.failed))
check("the board's rows carry the reason when they are given it",
      any("Amazon would not." in (row.why_not or "") for row in rows_with))
rows_without, _ = answered(lambda: tool.look(
    reports=[ORDERS], arrivals=nothing_arrived, run_days=[TODAY], today=TODAY,
    failed_ids=broke.failed))
check("and say nothing at all when they are not -- which is what was shipping",
      all((row.why_not or "") == "" for row in rows_without))

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)


EXPECTED = 79
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
