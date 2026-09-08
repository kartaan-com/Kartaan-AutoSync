"""Checks for the run that starts itself.

**WHAT IS ACTUALLY BEING CHECKED HERE IS THE ORDER OF THINGS**, because that is
what has gone wrong in the reference over and over: the record written after the
fetching instead of before it, the evidence flushed on one path out of several,
a run that died believed to be still going. None of those is a hard sum. Every
one of them is a step in the wrong place, and every one lost a day.

So most of what follows watches a list of what happened in what order, rather
than only what came back at the end.

Run: python autosync/nightly_checks.py
"""

import ast
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import between_runs  # noqa: E402
import clock  # noqa: E402
import runlog  # noqa: E402
import nightly as tool  # noqa: E402
from amazon_door import Fetched  # noqa: E402
from landing import Arrived, file_name_for  # noqa: E402
from reports import report  # noqa: E402

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


# **EVERY MOMENT HERE IS ALREADY HIS.** `clock.his_clock` is applied once, at the
# edge, before anything in this file is reached -- so two in the morning means
# two in the morning where he is, and the day it is about is the one that just
# ended.
AT = datetime(2026, 8, 29, 2, 0)
HIS_DAY = date(2026, 8, 29)
YESTERDAY = date(2026, 8, 28)

ONE_REPORT = [report("az_orders")]


class Harness:
    """One night, with everything the tick needs handed to it.

    Everything is recorded in the order it happened, so a step in the wrong place
    is visible rather than merely wrong at the end.
    """

    def __init__(self, state_bytes=None, fetch_gives=None, save_fails_on=(), read_throws=False,
                 gap_days_ago=None):
        self.events = []
        self.saved = []
        self.sent = []
        self.logged = []
        self.fetched = []
        self._state = state_bytes
        self._gives = fetch_gives or (lambda report_id, day: Fetched("landed", report_id, day,
                                                                    file_name="x", size=9, say="Landed."))
        self._save_fails_on = set(save_fails_on)
        self._read_throws = read_throws
        self._gap = gap_days_ago
        self._saves = 0

    def now(self):
        return AT

    def read_state(self):
        self.events.append("read the record")
        if self._read_throws:
            raise RuntimeError("Drive would not answer")
        return self._state

    def save_state(self, body):
        self._saves += 1
        self.events.append(f"saved the record ({self._saves})")
        if self._saves in self._save_fails_on:
            raise RuntimeError("Drive would not take it")
        self.saved.append(body)
        self._state = body

    def arrivals(self, report_id):
        # Everything up to the day before yesterday is already there, so only
        # yesterday is owed and one night is one fetch.
        which = report(report_id)
        return [
            Arrived(name=file_name_for(which, YESTERDAY - timedelta(days=n)), size=100)
            for n in range(1, 20) if n != self._gap
        ]

    def fetch(self, report_id, data_date, asked_already=None):
        self.events.append(f"fetched {report_id} for {data_date}")
        self.fetched.append((report_id, data_date, asked_already))
        return self._gives(report_id, data_date)

    def sink(self, lines):
        self.events.append("wrote the log out")
        self.logged.extend(lines)

    def send(self, lines):
        self.events.append("sent an alarm")
        self.sent.extend(lines)

    def go(self, **extra):
        asking = dict(reports=ONE_REPORT)
        asking.update(extra)
        return answered(lambda: tool.one_tick(
            now=self.now, read_state=self.read_state, save_state=self.save_state,
            arrivals=self.arrivals, fetch=self.fetch, sink=self.sink, send=self.send,
            **asking,
        ))


def a_record(**fields):
    return between_runs.write(between_runs.Between(**fields))


# ------------------------------------------- a first night

first = Harness()
first_tick = tick = first.go()
check("a first night runs", tick.ran is True)
check("and fetches the day that has just ended", first.fetched == [("az_orders", YESTERDAY, None)])
check("and nothing about it is our own defect", tick.is_a_defect is False)

# **THE RECORD IS WRITTEN BEFORE ANY FETCHING.** A run killed halfway must leave
# behind a record saying it started, or nothing can tell "one is going" from
# "none ever has" -- and the whole giving-up rule reads that difference.
order = first.events
check("the record is read before anything else", order[0] == "read the record")
check("and written down as started BEFORE the first fetch",
      order.index("saved the record (1)") < order.index(f"fetched az_orders for {YESTERDAY}"))
check("and the log is written out after the fetching, not before",
      order.index("wrote the log out") > order.index(f"fetched az_orders for {YESTERDAY}"))

after = between_runs.read(first.saved[-1])
check("what the run left behind says when it started", after.last_started == AT)
check("and that it finished", after.last_finished == AT)
check("and the day it ran on, so 'nothing is running at all' can ever be said",
      after.run_days == (AT.date(),))

# ------------------------------------------- his day, not Greenwich's

# **CONVERTED A SECOND TIME, this would ask for the 29th** -- a day that has not
# ended -- and record an empty answer as that day's data.
check("the day fetched is his yesterday, and the moment is not shifted again",
      first.fetched[0][1] == YESTERDAY and YESTERDAY == HIS_DAY - timedelta(days=1))

# ------------------------------------------- when it must not run

soon = Harness(a_record(last_started=AT - timedelta(hours=2), last_finished=AT - timedelta(hours=1)))
tick = soon.go()
check("a run an hour after the last one does not run", tick.ran is False)
check("and says the last one was today", "which is today" in (tick.why_not or ""))
check("and fetches nothing", soon.fetched == [])
check("and writes nothing down -- a tick that did not run is not a run",
      soon.saved == [])
check("and a tick that did not run is not our defect either", tick.is_a_defect is False)

going = Harness(a_record(last_started=AT - timedelta(minutes=20)))
tick = going.go()
check("a run already going stops another starting", tick.ran is False)
check("and says why, in words about fetching twice", "twice" in (tick.why_not or ""))

# **A RUN THAT DIED MUST NOT STOP EVERY LATER ONE FOR EVER.**
died = Harness(a_record(last_started=AT - timedelta(hours=5)))
tick = died.go()
check("a run that died hours ago does not stop the next one", tick.ran is True)
# **AND IT IS SAID, BEFORE ANYTHING IS FETCHED.** The reference had four runs
# vanish in twenty-six days and not one was written down anywhere.
said_first = [line for line in died.logged if "given up on" in line.message]
check("the run that was abandoned is written into the log", len(said_first) == 1)
check("and it names when that run started",
      (AT - timedelta(hours=5)).isoformat() in said_first[0].message)
check("and it is above the fetching, not after it",
      died.logged.index(said_first[0])
      < min(i for i, line in enumerate(died.logged) if line.report == "az_orders"))

# ------------------------------------------- started by hand

by_hand = Harness(a_record(last_started=AT - timedelta(hours=2), last_finished=AT - timedelta(hours=1)))
tick = by_hand.go(even_if_not_due=True)
check("a run asked for by hand goes even though one went an hour ago", tick.ran is True)

# **ONLY ONE OF THE TWO REASONS CAN BE OVERRIDDEN.** Two runs at once fetch every
# file twice, into two differently-named copies.
both = Harness(a_record(last_started=AT - timedelta(minutes=20)))
tick = both.go(even_if_not_due=True)
check("but one already going is not overridden by hand", tick.ran is False)
check("and it says so rather than pretending it ran",
      "not started" in (tick.why_not or ""))
check("and it names when the run that is going started",
      (AT - timedelta(minutes=20)).isoformat() in (tick.why_not or ""))
check("and says plainly that it was asked for by hand and still did not go",
      "by hand" in (tick.why_not or ""))
check("a run given up on may still be started by hand",
      Harness(a_record(last_started=AT - timedelta(hours=5))).go(even_if_not_due=True).ran is True)

# ------------------------------------------- the record cannot be read

damaged = Harness(b"{not a record")
tick = damaged.go()
check("a damaged record stops the run", tick.ran is False)
# **OURS, so the job goes red.** Read as empty it would ask Amazon again for
# every report it is already building.
check("and it is our own defect, not the platform's", tick.is_a_defect is True)
check("and nothing was fetched", damaged.fetched == [])

unreachable = Harness(read_throws=True)
tick = unreachable.go()
check("a record that cannot be fetched at all stops the run", tick.ran is False)
check("and that is our defect too", tick.is_a_defect is True)

# **IF IT CANNOT BE WRITTEN DOWN, IT DOES NOT START.** Started without a record
# saying so, a second tick would start another one alongside it.
cannot_start = Harness(save_fails_on=(1,))
tick = cannot_start.go()
check("a run that cannot record that it started does not start", tick.ran is False)
check("and nothing was fetched", cannot_start.fetched == [])
check("and it is our defect", tick.is_a_defect is True)

# ------------------------------------------- what Amazon is already building

carried = Harness(a_record(in_flight={("az_orders", YESTERDAY.isoformat()): "R-1"}))
carried.go()
# **CARRIED IN, so the report is waited for rather than asked for again.** Asking
# again spends a rationed call and leaves two reports being built.
check("a report Amazon is already building is handed to the fetch",
      carried.fetched == [("az_orders", YESTERDAY, "R-1")])

waiting = Harness(fetch_gives=lambda r, d: Fetched("still-waiting", r, d, say="Still coming.", their_id="R-2"))
waiting.go()
kept = between_runs.read(waiting.saved[-1])
check("a report still being built is written down for the next run",
      kept.in_flight == {("az_orders", YESTERDAY.isoformat()): "R-2"})

landed_now = Harness(a_record(in_flight={("az_orders", YESTERDAY.isoformat()): "R-1"}))
landed_now.go()
check("and once it lands it is forgotten, so it is never collected twice",
      between_runs.read(landed_now.saved[-1]).in_flight == {})

# **SAID LOUDLY WHEN IT CANNOT BE KEPT.** Lost, the next run asks Amazon again.
lost = Harness(save_fails_on=(2,))
lost_tick = tick = lost.go()
check("a run whose record could not be saved afterwards still ran", tick.ran is True)
check("but it is our defect", tick.is_a_defect is True)
check("and it says what could not be recorded",
      any("could not record what it left behind" in fault for fault in tick.our_faults))
check("and what that costs -- the next run may ask Amazon again",
      any("ask Amazon again" in fault for fault in tick.our_faults))

# ------------------------------------------- theirs is not ours

broke = Harness(fetch_gives=lambda r, d: Fetched("failed", r, d, say="Amazon would not give it up."))
tick = broke.go()
check("a report failing does not stop the run", tick.ran is True)
# **THEIRS IS RECORDED, NOT TURNED RED.** It is in the log, on the board and in
# an alarm; a red tick over it as well teaches everybody to ignore the red.
check("and a report failing is not our defect", tick.is_a_defect is False)
check("and it is in the log against its own report",
      any(line.report == "az_orders" and line.level == "failed" for line in broke.logged))
# **THE REPORT THAT FAILED IS NAMED TO THE BOARD.** Without it the board works
# out what is missing while knowing nothing about why, and the row says a day is
# late with no reason beside it.
check("and the run says which reports failed", tick.happened.failed == ("az_orders",))

# ------------------------------------------- alarms

# Nothing is late and everything arrived, so there is nothing to say.
quiet = Harness()
quiet.go()
check("a night with nothing wrong sends nothing", quiet.sent == [])

# **AND A JOB COMING BACK AFTER A WEEK OF SILENCE SAYS SO (cycle 46, R2#8).**
# The run writes today into the list of days it ran BEFORE the alarms are worked
# out, so the quiet alarm always saw a run today and never said a word -- **not
# even on the night it came back**, which is exactly when it is worth saying.
came_back = Harness(a_record(
    last_started=AT - timedelta(days=8), last_finished=AT - timedelta(days=8),
    run_days=[(AT - timedelta(days=8)).date()],
))
came_back.go()
check("a job coming back after a week of silence says how long it was quiet",
      any("quiet" in line.lower() or "nothing" in line.lower() for line in came_back.sent))

# **BUT A JOB THAT RAN YESTERDAY SAYS NOTHING**, which is every ordinary night.
ordinary = Harness(a_record(
    last_started=AT - timedelta(days=1), last_finished=AT - timedelta(days=1),
    run_days=[(AT - timedelta(days=1)).date()],
))
ordinary.go()
check("and one that ran yesterday says nothing about being quiet",
      not any("quiet" in line.lower() for line in ordinary.sent))

# **AND A BRAND-NEW SELLER'S VERY FIRST RUN SAYS NOTHING EITHER.** A first night
# has no days before it, so there is no gap -- and telling somebody their job is
# broken on the day they connect is the worst possible first impression.
check("and a brand-new seller's first night says nothing about being quiet",
      not any("quiet" in line.lower() for line in quiet.sent))

# **AND THE SAME ALARM DOES NOT GO OUT TWICE.** A channel that says the same
# thing every night is a channel people mute.
# A day six days back that never arrived and will not fetch is somebody's
# problem, not something to keep quietly retrying.
late = Harness(gap_days_ago=6, fetch_gives=lambda r, d: Fetched("failed", r, d, say="No."))
late_tick = late.go()
check("something newly wrong is sent", bool(late.sent))
# **THE TICK ITSELF SAYS WHICH ALARMS WENT OUT**, so whoever reads the job's own
# record knows a person was told, without going and looking at the channel.
check("and the tick says which alarms went out", bool(late_tick.alarms_sent))
check("and what is sent says which report and how late it is",
      any("az_orders" in line for line in late.sent))
again = Harness(between_runs.write(between_runs.read(late.saved[-1])),
                gap_days_ago=6,
                fetch_gives=lambda r, d: Fetched("failed", r, d, say="No."))
again.go()
check("and the same thing still wrong the next night is not sent again", again.sent == [])
check("what has been said is written down, so the next run knows",
      bool(between_runs.read(late.saved[-1]).standing))

# ------------------------------------------- which reports run here

# **AMAZON ONLY.** Meesho has no way in without a browser, and the browser is on
# the seller's own desk. Asked for here it would fail every night and make the
# log read as though the platform were broken.
default = Harness()
default.go(reports=None)
check("left to itself it fetches only what can be fetched with nobody present",
      {r for r, _, _ in default.fetched} == {"az_orders", "az_settlements", "az_returns"})

# ------------------------------------------- what a tick says it was

# **THE BOARD IS WORKED OUT AFTER THE RUN, AND IF THAT FAILS THE RUN STILL
# COUNTS.** The fetching already happened and is already written down; losing the
# summing-up must not turn a night's work into nothing.
class Awkward(Harness):
    def arrivals(self, report_id):
        if self._counted:
            raise RuntimeError("Drive stopped answering")
        self._counted = True
        return Harness.arrivals(self, report_id)


awkward = Awkward()
awkward._counted = False
tick = awkward.go()
check("a run whose board could not be worked out still ran", tick.ran is True)
check("and says nothing went out rather than falling over",
      tick.alarms_sent == ())
check("and it is our defect, because the seller was not told what was wrong",
      tick.is_a_defect is True)

check("a tick that did not run says so in one sentence",
      (answered(lambda: tool.Tick(ran=False, why_not="not due").summary()) or "").startswith("Did not run"))
check("and a tick with nothing wrong is not a defect",
      answered(lambda: tool.Tick(ran=True).is_a_defect) is False)
check("and one with something of ours wrong is",
      answered(lambda: tool.Tick(ran=True, our_faults=("x",)).is_a_defect) is True)
# **A TICK THAT RAN SAYS WHAT IT DID, not merely that it ran.** A run that tried
# nothing and a run where everything worked both report no failures.
check("a tick that ran says how many were tried and how many landed",
      "1 tried" in (answered(first_tick.summary) or ""))
check("and anything of ours that went wrong is said in the same sentence",
      "Drive would not take it" in (answered(lost_tick.summary) or ""))
# A record anything can edit is a record two readers can disagree about.
check("what a tick came to cannot be edited afterwards",
      answered(lambda: setattr(first_tick, "ran", False)) is None and bool(THREW))
THREW.clear()
check("what belongs to the job itself is kept somewhere no report can be called",
      answered(lambda: tool.OURS) == "autosync")


# ------------------------------------------- a Drive that is not kind

# **THE HALF THAT TOUCHES DRIVE IS CHECKED AGAINST A DRIVE, not excused.** It
# carries the rules that actually went wrong in the reference: a file replaced
# rather than put beside, a folder made only when missing, two files of one name
# refused rather than chosen between. Left unchecked, those are exactly the lines
# that put three wrongly-dated files into a real seller's Drive.
#
# **AND IT IS DELIBERATELY UNKIND.** It refuses what Drive refuses, hands back
# what Drive hands back, and will happily hold two files of one name -- because
# that is the state the rules exist for, and a stand-in that could not reach it
# would prove nothing.

import json as _json  # noqa: E402
import os as _os  # noqa: E402

from drive_door import BOUNDARY as MULTIPART_BOUNDARY  # noqa: E402
from drive_door import FILES, UPLOAD  # noqa: E402
from transport import Reply  # noqa: E402

FOLDER_KIND = "application/vnd.google-apps.folder"


def _between(body, boundary):
    """The record and the file out of a multipart upload, the way Drive reads it."""
    chunks = body.split(b"--" + boundary.encode())
    said = _json.loads(chunks[1].split(b"\r\n\r\n", 1)[1].rstrip(b"\r\n").decode("utf-8"))
    contents = chunks[2].split(b"\r\n\r\n", 1)[1]
    return said, contents[:-2] if contents.endswith(b"\r\n") else contents


class FakeDrive:
    """An in-memory Drive with just the questions `drive_door` actually asks."""

    def __init__(self):
        self.things = {}
        self.next = 0
        self.deleted = []

    def _add(self, name, parents, kind, body=b""):
        self.next += 1
        which = f"id-{self.next}"
        self.things[which] = {"id": which, "name": name, "parents": list(parents),
                              "mimeType": kind, "body": body}
        return which

    def file(self, name, inside, body=b"x"):
        return self._add(name, [inside], "text/plain", body)

    def named(self, name):
        return [one for one in self.things.values() if one["name"] == name]

    def get(self, url, params=None, headers=None):
        params = params or {}
        if url.startswith(FILES + "/"):
            which = url.rsplit("/", 1)[1]
            if which not in self.things:
                return Reply(404, {}, b"no such file")
            return Reply(200, {}, self.things[which]["body"])
        looking = params.get("q", "")
        found = []
        for one in self.things.values():
            if not any(f"'{where}' in parents" in looking for where in one["parents"]):
                continue
            if f"mimeType = '{FOLDER_KIND}'" in looking:
                if one["mimeType"] != FOLDER_KIND:
                    continue
                if f"name = '{one['name']}'" not in looking:
                    continue
            found.append({"id": one["id"], "name": one["name"], "size": str(len(one["body"]))})
        return Reply(200, {}, _json.dumps({"files": found}).encode("utf-8"))

    def post(self, url, params=None, headers=None, json=None, data=None):
        params = params or {}
        if url == UPLOAD:
            if params.get("uploadType") == "multipart":
                said, body = _between(data, MULTIPART_BOUNDARY)
                which = self._add(said["name"], said["parents"], "text/plain", body)
                return Reply(200, {}, _json.dumps({"id": which}).encode("utf-8"))
            waiting = self._add(json["name"], json["parents"], "text/plain", b"")
            return Reply(200, {"Location": f"https://up/{waiting}"}, b"{}")
        which = self._add(json["name"], json["parents"], json.get("mimeType", "text/plain"))
        return Reply(200, {}, _json.dumps({"id": which}).encode("utf-8"))

    def put(self, url, params=None, headers=None, json=None, data=None):
        which = url.rsplit("/", 1)[1]
        self.things[which]["body"] = data
        return Reply(200, {}, _json.dumps({"id": which}).encode("utf-8"))

    def delete(self, url, params=None, headers=None):
        which = url.rsplit("/", 1)[1]
        self.deleted.append(which)
        self.things.pop(which, None)
        return Reply(204, {}, b"")


INSIDE = "the-one-folder"

# **A FOLDER IS MADE ONLY WHEN IT IS MISSING.** One made every night is a Drive
# with thirty folders of one name and the files spread across them, and nothing
# reading them would ever say so.
drive = FakeDrive()
made = answered(lambda: tool._drive_folder(drive, INSIDE, tool.OURS))
check("a folder for the job's own files is made when it is not there",
      len(drive.named(tool.OURS)) == 1)
check("and the same one is used the next night, not a second one",
      answered(lambda: tool._drive_folder(drive, INSIDE, tool.OURS)) == made
      and len(drive.named(tool.OURS)) == 1)

# ------------------------------------------- the run's memory, in Drive

drive = FakeDrive()
read_it, save_it = answered(lambda: tool._state_in_drive(drive, INSIDE))
check("with nothing there yet, the record reads as a first night", answered(read_it) is None)

# **THE RECORD SHARES ITS FOLDER WITH THE LOGS**, so it has to be picked out by
# name. Everything in the folder taken as the record would read a log file as
# what the last run left -- and, worse, saving would take the logs away with it.
BESIDE = tool._drive_folder(drive, INSIDE, tool.OURS)
drive.file("autosync-log-2026-08-29.txt", BESIDE, b"an old log")

answered(lambda: save_it(b"FIRST"))
check("what is saved is really in the seller's Drive", answered(read_it) == b"FIRST")

# **REPLACED, NEVER PUT BESIDE.** Two records of what the last run left is two
# answers to what Amazon is building, and nothing could say which was real.
answered(lambda: save_it(b"SECOND"))
check("saving again replaces it rather than putting a second one beside it",
      len(drive.named(between_runs.FILE_NAME)) == 1)
check("and what comes back is the newer one", answered(read_it) == b"SECOND")
check("and the older one was actually taken away", len(drive.deleted) == 1)
check("and the log sitting beside it was left alone",
      len(drive.named("autosync-log-2026-08-29.txt")) == 1)
check("and reading the record does not hand back the log",
      answered(read_it) == b"SECOND")

# **TWO OF ONE NAME IS NOT SOMETHING TO CHOOSE BETWEEN.** Reading one of them
# would carry on with what might be the older run's record.
drive.file(between_runs.FILE_NAME, tool._drive_folder(drive, INSIDE, tool.OURS), b"A SECOND ONE")
two_of_them = None
try:
    read_it()
except Exception as caught:  # noqa: BLE001
    two_of_them = caught
check("two records of one name refuses rather than picking one", two_of_them is not None)
check("and it says nothing has started", "nothing has started" in str(two_of_them).lower())
check("and it says how many there are and what they are called",
      "2 copies" in str(two_of_them) and between_runs.FILE_NAME in str(two_of_them))

# ------------------------------------------- and nothing is taken away first
#
# **CYCLE 46, R2#3, AND IT IS THE WORST SHAPE OF FAILURE THERE IS.** The old file
# was deleted and the new one uploaded afterwards, so anything that threw between
# the two -- a dropped connection, a full Drive, a quota -- left the seller with
# NOTHING. **This file is the whole memory of what Amazon is building**: lost, the
# next run asks for every one of those reports again, spending a rationed call and
# making two reports where there should be one.
#
# **Two copies for a moment is recoverable. None is not.**


class DriveThatWillNotTake(FakeDrive):
    """A Drive that takes the folder listing and refuses the upload.

    **AS AWKWARD AS A REAL ONE IS AT THE ONE MOMENT THAT MATTERS.** A stand-in
    that always accepts an upload cannot tell the two orders apart at all -- both
    end with one good file -- which is exactly why this went unnoticed.
    """

    def post(self, url, params=None, headers=None, json=None, data=None):
        if "upload" in url:
            raise RuntimeError("Google would not take the file")
        return super().post(url, params=params, headers=headers, json=json, data=data)


stubborn = DriveThatWillNotTake()
keep_it, put_it = tool._state_in_drive(stubborn, INSIDE)
FOLDER = tool._drive_folder(stubborn, INSIDE, tool.OURS)
stubborn.file(between_runs.FILE_NAME, FOLDER, b"WHAT THE LAST RUN LEFT")
refused = None
try:
    put_it(b"TONIGHT")
except Exception as caught:  # noqa: BLE001
    refused = caught
check("a Drive that will not take the file makes the save fail", refused is not None)
# **AND THE ONE THAT WAS THERE IS STILL THERE.**
check("and what the last run left is still in the seller's Drive",
      len(stubborn.named(between_runs.FILE_NAME)) == 1)
check("and it still holds what it held",
      answered(keep_it) == b"WHAT THE LAST RUN LEFT")
check("and nothing was taken away at all", stubborn.deleted == [])

# **THE SAME FOR THE LOG, and it loses more.** The whole of today's log is
# rewritten every flush, because Drive cannot add to the end of a file -- so
# deleting first and then failing loses every line already written, which is the
# exact failure this package exists against.
stubborn_log = DriveThatWillNotTake()
LOG_FOLDER = tool._drive_folder(stubborn_log, INSIDE, tool.OURS)
LOG_CALLED = f"autosync-log-{date(2026, 8, 29).isoformat()}.txt"
stubborn_log.file(LOG_CALLED, LOG_FOLDER, b"everything that happened this morning\n")
log_sink = tool._log_to_drive(stubborn_log, INSIDE, date(2026, 8, 29))
log_refused = None
try:
    log_sink([runlog.Line(AT, "run-9", "az_orders", "done", "Landed.")])
except Exception as caught:  # noqa: BLE001
    log_refused = caught
check("a Drive that will not take the log makes the flush fail", log_refused is not None)
check("and this morning's log is still there",
      len(stubborn_log.named(LOG_CALLED)) == 1
      and b"this morning" in stubborn_log.named(LOG_CALLED)[0]["body"])
check("and nothing was taken away there either", stubborn_log.deleted == [])

# ------------------------------------------- the log, in Drive

drive = FakeDrive()
DAY = date(2026, 8, 29)
sink = answered(lambda: tool._log_to_drive(drive, INSIDE, DAY))
answered(lambda: sink([runlog.Line(AT, "run-1", "az_orders", "done", "Landed.")]))
CALLED = f"autosync-log-{DAY.isoformat()}.txt"
check("the log is written into the seller's own Drive", len(drive.named(CALLED)) == 1)
check("and it holds what happened", b"Landed." in drive.named(CALLED)[0]["body"])
check("and it says which run and which report each line was about",
      b"run-1" in drive.named(CALLED)[0]["body"]
      and b"az_orders" in drive.named(CALLED)[0]["body"])

# **DRIVE CANNOT ADD TO THE END OF A FILE**, so what is there is read, the new
# lines go under it, and the whole thing replaces it. Written any other way, the
# second flush of a run would throw the first one away.
answered(lambda: sink([runlog.Line(AT, "run-1", "az_returns", "failed", "Would not.")]))
KEPT = drive.named(CALLED)[0]["body"]
check("a second flush keeps what the first one wrote", b"Landed." in KEPT)
check("and adds the new lines under it", b"Would not." in KEPT)
check("and there is still only one log for the day", len(drive.named(CALLED)) == 1)

# **TWO LOGS OF ONE NAME REFUSES.** Adding to one of them loses whatever is in
# the other, and the log is the only evidence a failed night leaves behind.
drive.file(CALLED, tool._drive_folder(drive, INSIDE, tool.OURS), b"another one")
two_logs = None
try:
    sink([runlog.Line(AT, "run-1", "az_orders", "done", "More.")])
except Exception as caught:  # noqa: BLE001
    two_logs = caught
check("two logs of one name refuses rather than losing one", two_logs is not None)
check("and it says how many there are and which day they are for",
      "2 files" in str(two_logs) and CALLED in str(two_logs))

# ------------------------------------------- what really arrived

drive = FakeDrive()
ORDERS = tool._drive_folder(drive, INSIDE, "az_orders")
drive.file("amazon_az_orders_2026-08-27.csv", ORDERS, b"rows and rows")
drive.file("amazon_az_orders_2026-08-26.csv", ORDERS, b"")
arrivals = answered(lambda: tool._arrivals_from_drive(drive, INSIDE))
GOT = answered(lambda: list(arrivals("az_orders"))) or []
check("what has arrived is read out of the report's own folder", len(GOT) == 2)
# **PRESENCE IS NOT CORRECTNESS.** A nought-byte file is the one kind of wrongness
# presence alone can catch, and the reference's manifest recorded a truncated
# file as Verified because it only ever looked at the name.
check("and each file's size comes with it, so an empty one can be told apart",
      sorted(one.size for one in GOT) == [0, 13])
check("an empty file is not a day that arrived",
      [one.is_empty for one in GOT if one.size == 0] == [True])
check("and the name comes back as it is, so the day inside it can be read",
      sorted(one.name for one in GOT)[0].endswith("2026-08-26.csv"))

# ------------------------------------------- the secrets

_os.environ.pop("A_MADE_UP_SECRET", None)
not_set = None
try:
    tool._needed("A_MADE_UP_SECRET")
except SystemExit as caught:
    not_set = caught
# **NAMED, because the alternative is a whole evening.** A door built without a
# credential fails on its first call with an authorization error that says
# nothing about which of six values was left out.
check("a secret that is not set refuses and names which one", "A_MADE_UP_SECRET" in str(not_set))
check("and says where it is meant to live", "secret" in str(not_set).lower())

_os.environ["A_MADE_UP_SECRET"] = "  value  "
check("a secret that is set is handed over with no stray spaces",
      answered(lambda: tool._needed("A_MADE_UP_SECRET")) == "value")

# A secret pasted as a blank line is not a secret, and reading it as one gets an
# authorization failure that blames the platform.
_os.environ["A_MADE_UP_SECRET"] = "   "
only_spaces = None
try:
    tool._needed("A_MADE_UP_SECRET")
except SystemExit as caught:
    only_spaces = caught
check("and a secret that is only spaces is the same as not being set", only_spaces is not None)
_os.environ.pop("A_MADE_UP_SECRET", None)


# ------------------------------- the seller's own database (D114)

# **THE THREE THINGS THE JOB NOW WRITES AND READS ACROSS.** Before this, the page
# and the job had no shared writable place: the board and the runs were worked
# out and thrown away, and the hour the seller chose was written where nothing
# could read it.


class Database:
    """A stand-in for the seller's own database. Records what reached it."""

    def __init__(self, hour=None, hour_throws=False, board_throws=False, run_throws=False):
        self.boards = []
        self.runs = []
        self.hour_asked = 0
        self._hour = hour
        self._hour_throws = hour_throws
        self._board_throws = board_throws
        self._run_throws = run_throws

    def hour(self):
        self.hour_asked += 1
        if self._hour_throws:
            raise RuntimeError("Google would not let this job in")
        return self._hour

    def board(self, rows):
        if self._board_throws:
            raise RuntimeError("the database refused")
        self.boards.append(list(rows))

    def run(self, name, started_at, finished_at=None, why=""):
        if self._run_throws:
            raise RuntimeError("the database refused")
        self.runs.append((name, started_at, finished_at, why))


# The run record: written before the fetching, and again once it is over.
db = Database()
h = Harness()
tick = h.go(save_board=db.board, save_run=db.run)
check("the run is written down as started, and again as finished", len(db.runs) == 2)
check("both at the same name, so there are not two records of one run",
      db.runs[0][0] == db.runs[1][0])
# **A RUN THAT NEVER FINISHED IS NOT A RUN THAT FAILED**, and the first record is
# the only thing that can ever say so.
check("the first says nothing about finishing", db.runs[0][2] is None)
check("and the second says when it finished", db.runs[1][2] == AT)
check("and the first was written before the first fetch",
      h.events.index("saved the record (1)") < h.events.index(f"fetched az_orders for {YESTERDAY}"))
check("the day board is written once", len(db.boards) == 1)
check("and it has a row in it", len(db.boards[0]) > 0)
check("and none of that is our defect", tick.is_a_defect is False)

# **AND EVERY ROW ON IT THAT IS LATE SAYS WHY (cycle 46, R2#6).** The board has
# one column whose whole job is that, and it was blank on every row on every
# night -- so a seller was told a report was five days late and nothing else.
told = Database()
said_why = Harness(gap_days_ago=3,
                   fetch_gives=lambda r, d: Fetched("failed", r, d, say="Amazon would not give it up."))
said_why.go(save_board=told.board, save_run=told.run)
check("a report that failed puts its reason on the day board",
      any("would not give it up" in (row.why_not or "") for row in told.boards[0]))
# **AND NOTHING IS INVENTED FOR A DAY THAT SIMPLY ARRIVED.** A reason against a
# report that is fine is a reason somebody acts on for nothing.
fine = Database()
Harness().go(save_board=fine.board, save_run=fine.run)
check("and a night where everything arrived puts no reason anywhere",
      all((row.why_not or "") == "" for row in fine.boards[0]))

# **A SCREEN'S RECORD FAILING MUST NEVER STOP THE FETCHING.** What must survive a
# run is what Amazon is building, and that is saved on its own path; refusing to
# fetch over a board row would turn a database blip into a lost day (D108).
broken = Database(board_throws=True, run_throws=True)
h = Harness()
tick = h.go(save_board=broken.board, save_run=broken.run)
check("a database that will not take the board still lets the fetching happen",
      tick.ran is True and h.fetched == [("az_orders", YESTERDAY, None)])
check("but it is said out loud rather than swallowed", tick.is_a_defect is True)
check("and it names the board", any("day board" in one for one in tick.our_faults))
check("and it names the run, both times",
      len([one for one in tick.our_faults if "written down as" in one]) == 2)
check("and says which of the two it was",
      any("as started" in one for one in tick.our_faults)
      and any("as finished" in one for one in tick.our_faults))

# **A TICK CAN BE DRIVEN WITH NO DATABASE AT ALL**, which is how every other rule
# in this file is checked -- and it must not be quietly counted as a fault.
check("a tick handed no database at all is not a defect", first_tick.is_a_defect is False)

# ------------------------------- the hour the seller chose

chosen = Database(hour="23")
h = Harness()
tick = h.go(ask_the_hour=chosen.hour)
check("the hour the seller chose is asked for", chosen.hour_asked == 1)
# Two in the morning is before eleven at night, so a seller who chose the evening
# is not fetched at two -- which is exactly what used to happen, silently.
check("and a tick before it does not run", tick.ran is False)
check("and says which hour it is waiting for", "23" in (tick.why_not or ""))
check("and fetches nothing", h.fetched == [])

# **NOTHING CHOSEN IS NOT A FAULT.** A seller who has connected but not finished
# setting the business up has no record and no choice, and the default is right.
h = Harness()
check("a seller who has chosen nothing is fetched at the default hour",
      h.go(ask_the_hour=Database(hour=None).hour).ran is True)
h = Harness()
check("and so is one whose choice is empty",
      h.go(ask_the_hour=Database(hour="").hour).ran is True)

# **AN HOUR NOBODY CAN CHOOSE STOPS THE RUN AND SAYS SO (D113)**, rather than
# quietly becoming the default. A setting that silently does nothing is worse
# than one that says it is wrong.
h = Harness()
tick = h.go(ask_the_hour=Database(hour="elevenish").hour)
check("an hour nobody can choose stops the run", tick.ran is False)
check("and says what was wrong with it", "elevenish" in (tick.why_not or ""))

# **A QUESTION THAT CANNOT BE ANSWERED IS OUR OWN DEFECT AND STOPS THE RUN.**
# Falling back to the default would fetch at two in the morning for a seller who
# asked for eleven at night, for ever, with nothing saying why.
h = Harness()
tick = h.go(ask_the_hour=Database(hour_throws=True).hour)
check("an hour that cannot be read at all stops the run", tick.ran is False)
check("and it is our own defect, not the platform's", tick.is_a_defect is True)
check("and it says nothing was fetched because of it",
      "nothing has been fetched" in "  ".join(str(one) for one in tick.our_faults))
check("and it says what Google said", "would not let this job in" in str(tick.why_not or ""))
check("and nothing was fetched", h.fetched == [])
check("and nothing was written down as having started", h.saved == [])

# ------------------------------- the evidence not leaving the building

# **`runlog.Run` HAS RECORDED THIS SINCE IT WAS WRITTEN AND NOTHING EVER READ
# IT** -- so a run whose log reached neither the seller's Drive nor their
# database finished green and silent, which is the failure this package exists
# against.


class LogRefuses(Harness):
    def sink(self, lines):
        self.events.append("tried to write the log out")
        raise RuntimeError("Drive would not take the log")


h = LogRefuses()
tick = h.go()
check("a run whose log never got out of the building says so", tick.is_a_defect is True)
check("and says what stopped it", "Drive would not take the log" in "  ".join(tick.our_faults))
check("and says what that costs -- it is on no screen", "not on any screen" in "  ".join(tick.our_faults))
check("and the fetching itself still happened", tick.ran is True and h.fetched != [])
check("and its summary says it too", "out of the building" in tick.summary())

# ------------------- HIS CASE, THROUGH THE REAL CHAIN THIS TIME

# **THIS IS THE SAME CASE `between_runs_checks.py` ALREADY CHECKS, AND THAT IS
# THE POINT.** There it is driven by calling `whats_new` and `between_runs`
# directly -- which proved the two files agree with each other and proved nothing
# about the run, because **until this session nothing in this package called
# `whats_new` at all.** Every one of those checks would have stayed green with
# the reading never wired to anything. So it is driven here through
# `one_tick` itself: a real folder, a real record written to Drive and read back
# the next night, and the real reading in between.
#
# 1st, 2nd, 3rd downloaded. The 4th fails. The 5th downloads. Later the 4th
# arrives.

import ledger  # noqa: E402
import ledger_door  # noqa: E402
import ledger_sheet  # noqa: E402
import sales as the_sheet  # noqa: E402
import whats_new  # noqa: E402


def _a_meesho_file(*rows):
    header = ("Sub Order No,SKU,Quantity,Order Date,Reason for Credit Entry,"
              "Supplier Discounted Price (Incl GST and Commision)")
    return ("\n".join([header] + list(rows)) + "\n").encode("utf-8")


def _in_the_folder(which, name):
    return whats_new.InTheFolder(which=which, name=name, size=100)


FIRST_THREE_AND_FIFTH = [
    _in_the_folder("d-1", "meesho_me_orders_2026-09-01.csv"),
    _in_the_folder("d-2", "meesho_me_orders_2026-09-02.csv"),
    _in_the_folder("d-3", "meesho_me_orders_2026-09-03.csv"),
    _in_the_folder("d-5", "meesho_me_orders_2026-09-05.csv"),
]
THE_FOURTH = _in_the_folder("d-4", "meesho_me_orders_2026-09-04.csv")
BODIES = {
    "d-1": _a_meesho_file("SO-1,DJ 14,1,2026-09-01 10:00:00,SHIPPED,100"),
    "d-2": _a_meesho_file("SO-2,DJ 14,1,2026-09-02 10:00:00,SHIPPED,100"),
    "d-3": _a_meesho_file("SO-3,DJ 14,1,2026-09-03 10:00:00,SHIPPED,100"),
    # The fifth corrects the first sale's quantity to nine.
    "d-5": _a_meesho_file("SO-1,DJ 14,9,2026-09-05 10:00:00,SHIPPED,100"),
    # The fourth arrives later and still says one.
    "d-4": _a_meesho_file("SO-1,DJ 14,1,2026-09-04 10:00:00,SHIPPED,100"),
}


class TheSellersDrive:
    """The folders and the ledger, as far as a tick can tell."""

    def __init__(self, files, into=None):
        self.files = list(files)
        self.recorded = []
        # **WHERE THE SALES ACTUALLY GO, when a check needs a real one.** Left
        # out, this only remembers that it was called -- enough for every rule
        # about MARKING a file read, and exactly what hid the ordering fault.
        self._into = into

    def in_the_folder(self, report_id):
        return list(self.files) if report_id == "me_orders" else []

    def bring_it_back(self, file_id):
        return BODIES[file_id]

    def record(self, readings):
        self.recorded.extend(readings)
        if self._into is not None:
            self._into(readings)

    def wiring(self):
        return dict(what_is_in_the_folder=self.in_the_folder,
                    bring_the_file_back=self.bring_it_back,
                    record_the_sales=self.record)


class ANightLater(Harness):
    """The same harness, one night on. **Two nights cannot be the same moment**:
    the clock refuses a second run on the day the last one finished, which is
    exactly what it is there for."""

    def __init__(self, state_bytes=None, nights=1):
        super().__init__(state_bytes)
        self._nights = nights

    def now(self):
        return AT + timedelta(days=self._nights)


night_one_drive = TheSellersDrive(FIRST_THREE_AND_FIFTH)
night_one = Harness()
tick = night_one.go(**night_one_drive.wiring())
check("A TICK READS WHAT IS NEW IN THE FOLDER -- until now nothing did",
      tick is not None and tick.what_was_read is not None
      and len(tick.what_was_read.read_tonight) == 4)
check("and what it read is written into the record the run leaves behind",
      between_runs.read(night_one.saved[-1]).files_read == ("d-1", "d-2", "d-3", "d-5"))
check("and the record on Drive holds a list of file ids, never a high-water date",
      "2026-09" not in "".join(between_runs.read(night_one.saved[-1]).files_read))
check("and the night's summary says what it read", "Read 4 of 4 new file(s)" in tick.summary())
check("and reading a folder is not our own defect", tick.is_a_defect is False)

# **THE NEXT NIGHT, READING THE RECORD BACK OFF DRIVE.**
night_two_drive = TheSellersDrive(FIRST_THREE_AND_FIFTH + [THE_FOURTH])
night_two = ANightLater(night_one.saved[-1])
tick = night_two.go(**night_two_drive.wiring())
check("THE FOURTH FILE, ARRIVING AFTER THE FIFTH, IS READ ON THE NEXT NIGHT",
      tick is not None and tick.what_was_read is not None
      and tick.what_was_read.read_tonight == ("d-4",))
check("and the four already read are not read a second time",
      len(night_two_drive.recorded) == 1)
check("and all five are now in the record the run leaves behind",
      between_runs.read(night_two.saved[-1]).files_read
      == ("d-1", "d-2", "d-3", "d-4", "d-5"))

# **AND THE LATE FOURTH'S OLDER FIGURES DO NOT WIN -- DRIVEN AS THE JOB RUNS.**
#
# **THIS USED TO POOL BOTH NIGHTS' READINGS INTO ONE `ledger.plan` CALL AGAINST
# AN EMPTY SHEET, and it was green.** That proved `plan`'s own sort, which was
# already committed and already true, and proved nothing about the chain a tick
# actually walks: `read_what_is_new` hands `record_the_sales` ONE file at a time
# (that is what makes the marking safe), and the writing half reads the sheet
# back and plans again for each one -- so the sort is handed a list of one, every
# time, and **the order Drive happened to list the folder in decided the figure.**
# A check whose green answer does not mean its own name is worse than no check
# (D175).
#
# So the tick below writes into a real recorder, a real `LedgerDoor` and a sheet
# that keeps what it was written. **The stand-in is written out again here rather
# than shared with `reading_checks.py`** for the same reason the files and bodies
# above are: a check file that imports another check file runs it.


class PretendLedgerSheet:
    """A Google Sheets that KEEPS WHAT IT WAS TOLD.

    A stand-in answering every write with `{}` leaves every plan looking right
    and the sheet empty, which is how a chain planning against a stale reading
    passes. So `:append` really appends and `values:batchUpdate` really
    overwrites the row it names.
    """

    def __init__(self):
        self.rows = [list(the_sheet.COLUMNS)]

    def __call__(self, method, path, query=None, body=None):
        if method == "GET" and "/values/" not in path:
            return {"sheets": [{"properties": {"title": the_sheet.THE_TAB}}]}
        if method == "GET":
            return {"values": [list(r) for r in self.rows]}
        if ":append" in path:
            self.rows += [list(r) for r in (body or {}).get("values", ())]
            return {}
        if "values:batchUpdate" in path:
            for one in (body or {}).get("data", ()):
                at = int(one["range"].split("!A")[1].split(":")[0])
                self.rows[at - 1] = list(one["values"][0])
            return {}
        return {}

    def qty_for(self, name):
        return self.cell_for(name, "qty")

    def cell_for(self, name, column):
        """One cell of one sale, read back out of what the seller would see.

        **READ BACK OUT OF THE SHEET, never off the plan.** A plan says what it
        meant to write; this says what is in the row -- which is the only place
        a column that is declared and never filled shows up as blank.
        """
        at_id = the_sheet.COLUMNS.index("id")
        at = the_sheet.COLUMNS.index(column)
        for row in self.rows[1:]:
            if len(row) > at and row[at_id] == name:
                return row[at]
        return None


def a_sales_ledger(the_sheet=None):
    """THE REAL WRITING HALF, over a sheet that keeps what it is given.

    **THIS USED TO BE THREE LINES THAT LOOKED LIKE `ledger_sheet.recording_into`
    AND WERE NOT IT**, written out rather than imported because that half was not
    safe to land until D157's four date-marker columns exist. That reasoning is
    gone: the writing half now REFUSES to run until they do, so it can land.

    **AND THE COPY HAD ALREADY STOPPED BEING A COPY, which is the whole lesson.**
    The real one makes ONE memory of what the night has decided and hands it to
    every file, which is how D150's rule 3 fires across a one-file-at-a-time
    handover. These three lines made a fresh empty one per file, so a tie between
    two files of one report and one day could never be seen.

    **HANDED A SHEET, THIS IS A SECOND NIGHT AGAINST THE SAME LEDGER**, with a new
    night's memory -- which is what a second run really has.
    """
    keeping = the_sheet if the_sheet is not None else PretendLedgerSheet()
    door = ledger_door.LedgerDoor(keeping, "the-sellers-own-ledger")
    told = []
    return keeping, ledger_sheet.recording_into(door, told.append), told


THE_SALE = "meesho::SO-1::DJ 14"

# **THE HALF THAT CAN BE FIXED: A TICK THAT FINDS BOTH FILES NEW.** The fourth
# failed on its own night, so it and the fifth are both sitting there when this
# run looks -- and Drive answers a listing in its own order, newest first.
newest_first, into_the_ledger, _ = a_sales_ledger()
one_run_drive = TheSellersDrive(FIRST_THREE_AND_FIFTH + [THE_FOURTH],
                                into=into_the_ledger)
tick = Harness().go(**one_run_drive.wiring())
check("a tick that finds all five files reads all five",
      tick is not None and tick.what_was_read is not None
      and len(tick.what_was_read.read_tonight) == 5)
check("THE FOURTH'S OLDER FIGURE DOES NOT OVERWRITE THE FIFTH'S",
      newest_first.qty_for(THE_SALE) == "9")

# **AND LISTED THE OTHER WAY ROUND IT MUST SAY THE SAME THING**, or the answer is
# luck rather than a rule. One file at a time in Drive's order, one of these two
# says 9 and the other says 1.
oldest_first, other_ledger, _ = a_sales_ledger()
other_way_drive = TheSellersDrive(
    FIRST_THREE_AND_FIFTH[:3] + [THE_FOURTH, FIRST_THREE_AND_FIFTH[3]],
    into=other_ledger)
tick = Harness().go(**other_way_drive.wiring())
check("and listed the other way round all five are still read",
      tick is not None and len(tick.what_was_read.read_tonight) == 5)
check("AND THE ORDER DRIVE LISTED THEM IN DECIDES NOTHING",
      oldest_first.qty_for(THE_SALE) == newest_first.qty_for(THE_SALE) == "9")
check("and the days come off the files themselves, not off the nights they arrived",
      sorted(r.on for r in one_run_drive.recorded)
      == ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05"])


# **AND THE ID DRIVE GAVE THE FILE DECIDES NOTHING EITHER.** The ids above read
# `d-1` to `d-5` so a check about days can be read, and that made them sort in
# the same order as the days -- so a sort keyed on Drive's id passed everything
# above. **A real Drive id is an opaque string with no order in it.** Driven once
# more with ids whose alphabetical order is the reverse of their days, and listed
# in that order: keyed on the id the fourth's 1 would stand. Found by putting
# that fault back and watching nothing go red.
opaque, opaque_ledger, _ = a_sales_ledger()
BACKWARDS = [_in_the_folder("a-1c", "meesho_me_orders_2026-09-05.csv"),
             _in_the_folder("z-9f", "meesho_me_orders_2026-09-04.csv")]
BODIES["a-1c"] = BODIES["d-5"]
BODIES["z-9f"] = BODIES["d-4"]
backwards_drive = TheSellersDrive(BACKWARDS, into=opaque_ledger)
tick = Harness().go(**backwards_drive.wiring())
check("both files are read whatever their ids look like",
      tick is not None and tick.what_was_read is not None
      and len(tick.what_was_read.read_tonight) == 2)
check("AND THE ID DRIVE GAVE THE FILE DECIDES NOTHING EITHER",
      opaque.qty_for(THE_SALE) == "9")

# ---- HIS RE-FETCH-BY-HAND CASE, THROUGH A WHOLE TICK (D110, D150 rule 3)
#
# **A DAY FETCHED AGAIN LANDS AS A SECOND FILE UNDER THE SAME NAME**, so two files
# of one report and one data date is the thing he does by hand, not a curiosity.
# D150 rule 3: keep what is there, REPORT the disagreement, never a silent pick.
#
# **IT COULD NOT FIRE, AND THE CODE SAID IT COULD.** A sale lands one file at a
# time, so the memory `plan` decides the rule in started empty on every call and
# the two files never met: measured, both listing orders gave the same silent
# answer and reported nought disagreements. What settled the seller's quantity was
# which Drive id sorted higher.
BODIES["same-day-first"] = _a_meesho_file("SO-1,DJ 14,9,2026-09-05 10:00:00,SHIPPED,100")
BODIES["same-day-again"] = _a_meesho_file("SO-1,DJ 14,1,2026-09-05 10:00:00,SHIPPED,100")
FETCHED_TWICE = [_in_the_folder("same-day-first", "meesho_me_orders_2026-09-05.csv"),
                 _in_the_folder("same-day-again", "meesho_me_orders_2026-09-05.csv")]

tied, into_the_tie, tie_told = a_sales_ledger()
tie_drive = TheSellersDrive(FETCHED_TWICE, into=into_the_tie)
tie_night = Harness()
tick = tie_night.go(**tie_drive.wiring())
tie_said = [one for one in tie_told if "DISAGREEMENT" in one]
check("a tick reads both files of the same day, because both are new",
      tick is not None and tick.what_was_read is not None
      and len(tick.what_was_read.read_tonight) == 2)
# **NOT AN INDEX INTO A LIST THAT COULD BE EMPTY.** A check that CRASHES is not a
# check answering -- the file dies where it stands, prints no count, and says
# nothing about everything under it, including the D180 check further down.
_tie_first = tie_drive.recorded[0].which if tie_drive.recorded else None
check("TWO FILES OF ONE REPORT AND ONE DAY: WHAT THE FIRST ONE WROTE IS KEPT",
      _tie_first is not None
      and tied.qty_for(THE_SALE) == {"same-day-first": "9",
                                     "same-day-again": "1"}[_tie_first])
check("AND THE TICK REPORTS THE DISAGREEMENT -- never a silent pick (D150 rule 3)",
      len(tie_said) == 1)
check("and the report names both files, so somebody can go and answer it",
      tie_said and "same-day-first" in tie_said[0] and "same-day-again" in tie_said[0])
# **A REPORTED DISAGREEMENT IS NOT A FILE THAT FAILED.** It was opened, understood
# and its sales reached the sheet. Left unmarked it would be read again every
# night for ever and report the same tie every night.
check("and both files are still written down as read, tie or no tie",
      between_runs.read(tie_night.saved[-1]).files_read
      == ("same-day-again", "same-day-first"))

# **THE HALF THAT COULD NOT BE FIXED HERE UNTIL 2026-09-08 -- D180, NOW CLOSED.**
#
# When the fourth arrives on a LATER night, the fifth's 9 is already in the sheet
# and the fourth is the only reading this run has to sort. `ledger.plan` tells
# newer from older by the data date a READING carries, and **a row in the sheet
# carried no date at all** -- 49 columns, four of which are supposed to say which
# day's file wrote each figure. So the fourth's 1 went over the fifth's 9 and
# nothing anywhere could tell that it should not have.
#
# **The check below asserted today's WRONG answer on purpose from 2026-09-04,**
# so that it would go red the day the fix landed rather than waiting for anybody
# to remember. **It went red on 2026-09-08 and this is it turned round.**
#
# **THE COLUMNS LANDING WAS NOT THE FIX, and that is the part worth keeping.**
# The ERP put the four names in its column list on 2026-09-06 and this check
# stayed green for two more days, because a column nothing fills and a column
# that does not exist are the same column to a run reading it back. What closed
# it was `orders.read_orders` carrying the file's own day onto every sale and
# `ledger.older_than_the_row` reading it back before anything is applied.
across_nights, over_two_nights, _ = a_sales_ledger()
first_night_drive = TheSellersDrive(FIRST_THREE_AND_FIFTH, into=over_two_nights)
first_night = Harness()
tick = first_night.go(**first_night_drive.wiring())
check("on the first night the fifth's correction lands in the sheet",
      tick is not None and across_nights.qty_for(THE_SALE) == "9")

# **A SECOND NIGHT IS A SECOND RUN**, and it remembers nothing of what last
# night decided -- only what is written in the sheet. That is exactly why the
# fault below cannot be fixed here.
_, the_next_night, _ = a_sales_ledger(across_nights)
second_night_drive = TheSellersDrive(FIRST_THREE_AND_FIFTH + [THE_FOURTH],
                                     into=the_next_night)
tick = ANightLater(first_night.saved[-1]).go(**second_night_drive.wiring())
check("and on the next night the fourth is the only file read",
      tick is not None and tick.what_was_read.read_tonight == ("d-4",))
check("ACROSS TWO NIGHTS THE FOURTH'S OLDER FIGURE NO LONGER WINS -- D180 CLOSED",
      across_nights.qty_for(THE_SALE) == "9")
# **AND THE ROW STILL SAYS THE FIFTH WROTE IT.** A marker rolled backwards to the
# older file's day would leave the right figure standing and the wrong story
# beside it -- and the NEXT late file would then be allowed straight through.
check("and the marker is not rolled backwards to the older file's day",
      across_nights.cell_for(THE_SALE, "ordersOn") == "2026-09-05")

# **THE THIRD NIGHT: nothing new, and it must not read like a night that read
# everything.** Two runs have already "succeeded" in eleven and forty-seven
# seconds while doing nothing at all.
night_three = ANightLater(night_two.saved[-1], nights=2)
tick = night_three.go(**TheSellersDrive(FIRST_THREE_AND_FIFTH + [THE_FOURTH]).wiring())
check("once every file has been read none is read again the night after",
      tick is not None and tick.what_was_read.read_tonight == ())
check("AND THAT NIGHT DOES NOT SAY WHAT A NIGHT THAT READ EVERYTHING SAYS",
      "Read 0 of 0 new file(s)" in tick.summary()
      and "5 already read" in tick.summary())

# **AND A TICK WITH NO FOLDER HANDED IN SAYS SO, EVERY NIGHT.** That is where
# this stands until the seller's sales ledger exists, and it is the one state
# that must never be quiet.
bare = Harness()
tick = bare.go()
check("a tick given no folder still says what it read, which is nothing",
      tick is not None and "Read nothing" in tick.summary())
check("and nothing about that is our own defect", tick.is_a_defect is False)

# **A FOLDER THAT WOULD NOT LIST IS OUR OWN DEFECT (D108).** What is new cannot
# be worked out without it, and nothing is let go of.


class ADeadFolder(TheSellersDrive):
    def in_the_folder(self, report_id):
        raise RuntimeError("Drive would not answer")


dead = ANightLater(night_two.saved[-1], nights=3)
tick = dead.go(**ADeadFolder([]).wiring())
check("a folder that could not be listed is our own defect", tick.is_a_defect is True)
check("and it says so in words about what is new", "What is new" in "  ".join(tick.our_faults))
check("and nothing is let go of on the strength of it",
      between_runs.read(dead.saved[-1]).files_read
      == ("d-1", "d-2", "d-3", "d-4", "d-5"))
check("and the fetching itself still happened", tick.ran is True and dead.fetched != [])

# ------------------------------ a run that finished before it started (D190)

# **THE GUARD AT `one_tick` HAD NOTHING WATCHING IT.** Neuter it and every one of
# the checks above stayed green -- and it is not an inert guard either. Without
# it `between_runs.write` puts down a record saying a run finished before it
# started, `read` takes that back as fact on the next run, and the clock is then
# deciding on the strength of something that never happened.
#
# **This is D190's absent alarm rather than a dead one.** No tool that breaks a
# line and asks which checks notice can find a guard nobody ever wrote a check
# for, because there is no check to stay green.


class ClockWentBackwards(Harness):
    """A machine whose clock steps back between the start of a run and its end.

    **IT IS THE ONLY WAY THIS IS REACHED FROM A REAL NIGHT.** `one_tick` asks the
    time once at the top and again at the bottom, and everything in between
    assumes the second is later.
    """

    def __init__(self, *rest, **named):
        super().__init__(*rest, **named)
        self._asked = 0

    def now(self):
        self._asked += 1
        return AT if self._asked == 1 else AT - timedelta(hours=2)


backwards = ClockWentBackwards()
tick = backwards.go()
left_behind = between_runs.read(backwards.saved[-1])
check("A RUN THAT FINISHED BEFORE IT STARTED IS NEVER WRITTEN DOWN",
      left_behind.last_finished is None
      or left_behind.last_finished >= left_behind.last_started)
check("and it is our own defect, said in words rather than swallowed",
      tick is not None and tick.is_a_defect is True
      and any("The run's own record was not saved" in one for one in tick.our_faults))

# ---------------------------------- what the job says last, and its exit code

# **THIS RULE LIVED IN `start.py` FOR A ROUND, WHERE NOTHING COULD EVER WATCH IT
# FAIL.** That file needs a real Amazon account, a real Google account and a real
# network. A rule nobody asks about is a comment (D170).

D184_SAYS = ("The seller's ledger has gone.\n"
             "Restore it from the Drive bin first.\n"
             "Nothing here writes a second sheet in its place.")

lines, code = tool.how_the_night_ends(tool.Tick(ran=True), D184_SAYS)
check("A NIGHT THAT COULD NOT WRITE THE SALES LEDGER NEVER REPORTS SUCCESS",
      code == 1)
check("and what it could not do is said LINE BY LINE, not squeezed into one",
      lines == tuple(f"ALARM  {one}" for one in D184_SAYS.splitlines())
      and len(lines) == 3)

check("a night with one of our own defects is red",
      tool.how_the_night_ends(tool.Tick(ran=True, our_faults=("Drive would not answer",)),
                              None) == ((), 1))
check("a night with neither is green, and says nothing extra",
      tool.how_the_night_ends(tool.Tick(ran=True), None) == ((), 0))
check("and a tick that decided not to run at all is green too",
      tool.how_the_night_ends(tool.Tick(ran=False, why_not="too early"), None) == ((), 0))

# -------------------- the eight secret names, written down in three places

# **NOTHING ANYWHERE READ `autosync.yml`.** The eight names are typed out three
# times -- the workflow's own "is this repository set up to fetch?" gate, the
# workflow's `env` block, and `start.py`'s eight `_needed` calls -- and nothing
# held any of the three to another. All three agreed by luck.
#
# **D190: WHERE A LIST GOVERNS BEHAVIOUR, SOMETHING HOLDS THE TWO LISTS TO EACH
# OTHER, IN BOTH DIRECTIONS.** A name in the gate and not in `env` is a night
# that starts and then cannot read what it needs; a name in `env` and not in the
# gate is a repository declared ready without it. Both are silent.

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "autosync.yml"
check("the workflow the seller's own repository runs can be read at all",
      WORKFLOW.is_file())
SAID_IN_THE_WORKFLOW = WORKFLOW.read_text(encoding="utf-8") if WORKFLOW.is_file() else ""

# What the gate refuses to run without.
GATED_ON = tuple(re.findall(r"secrets\.([A-Z0-9_]+)\s*!=\s*''", SAID_IN_THE_WORKFLOW))
# What the run is actually handed, and under which name. **The pair matters:**
# `GOOGLE_CLIENT_ID: ${{ secrets.GOOGLE_CLIENT_SECRET }}` reads perfectly well.
HANDED_OVER = tuple(re.findall(
    r"^\s*([A-Z0-9_]+):\s*\$\{\{\s*secrets\.([A-Z0-9_]+)\s*\}\}\s*$",
    SAID_IN_THE_WORKFLOW, re.M))

# **WHAT THE RUN ASKS FOR IS ASKED OF THE CODE, not searched for in it.** Every
# `nightly._needed("X")` in `start.py`, read out of the parsed file, so a name
# built up out of pieces cannot pass for one.
START = ast.parse((Path(__file__).resolve().parent / "start.py").read_text(encoding="utf-8"))
ASKED_FOR = tuple(
    node.args[0].value
    for node in ast.walk(START)
    if isinstance(node, ast.Call)
    and isinstance(node.func, ast.Attribute) and node.func.attr == "_needed"
    and node.args and isinstance(node.args[0], ast.Constant)
    and isinstance(node.args[0].value, str)
)

# **NONE OF THE THREE MAY BE EMPTY.** Without this every comparison below passes
# by having nothing to compare -- which is the whole shape D190 is about.
check("the workflow refuses to run without some named secrets", len(GATED_ON) > 4)
check("and hands some named secrets to the run", len(HANDED_OVER) > 4)
check("and the run asks for some named secrets", len(ASKED_FOR) > 4)

check("no name is written twice in any one of the three lists",
      len(set(GATED_ON)) == len(GATED_ON)
      and len(set(ASKED_FOR)) == len(ASKED_FOR)
      and len({name for name, _ in HANDED_OVER}) == len(HANDED_OVER))

check("every value handed to the run is set from the secret of the same name",
      all(under == secret for under, secret in HANDED_OVER))

FROM_SECRETS = {secret for _, secret in HANDED_OVER}
check("EVERY SECRET THE WORKFLOW REFUSES TO RUN WITHOUT IS HANDED TO THE RUN, "
      "AND EVERY ONE HANDED OVER IS ONE IT REFUSES TO RUN WITHOUT",
      set(GATED_ON) == FROM_SECRETS)
check("AND EVERY ONE HANDED OVER IS ONE THE RUN ASKS FOR, AND EVERY ONE IT ASKS "
      "FOR IS HANDED OVER",
      set(ASKED_FOR) == FROM_SECRETS)


# ------------- the one tick a day, and the hours it can never reach (A33)

# **THE SELLER'S CHOSEN HOUR HAS NEVER REACHED THE SCHEDULE SINCE D120, AND
# NOTHING ANYWHERE ASKED WHETHER IT DID.**
#
# The cron line is the only thing that wakes this job -- `clock.why_not_now` can
# refuse a tick, it has nothing to start one with. The line ticks once a day at
# 20:53 UTC, which is 02:23 in his time, and the chosen hour is a FLOOR ("not
# before eight"). So every seller who chose an hour from 3 to 23 is refused on
# every tick, on every day, for ever -- and is told only "It is 02:23 and
# fetching is set for 11:00 or later", which reads exactly like a tick that will
# succeed later today.
#
# **DRIVEN AGAINST `clock.why_not_now`, HOUR BY HOUR, AND NOT ARGUED.** The hour
# the tick really lands at is read out of the cron line and moved into his time
# by `clock`'s own constants, so a change to either is a change here.
#
# **THIS PINS A FAULT RATHER THAN A REPAIR.** It is written this way round on
# purpose: the three ways out are all his (wake hourly again and reverse D120;
# build the onboarding step that writes his hour into the line; or let something
# rewrite a seller's workflow, which D113 refused). The day one is taken, this
# check goes red and somebody has to change it deliberately -- which is the only
# thing that stops the hole being quietly re-believed closed.
# **EVERY SCHEDULE LINE, NOT THE FIRST ONE (A33R).** Read with `re.search` this
# took whichever `cron:` came first and asked nothing about the rest -- so adding
# a SECOND line, `- cron: '53 * * * *'`, which is the wake-hourly repair named
# above, fixed the fault and left all these checks green. **A pin that survives
# the repair it exists to demand is not a pin.** Every entry is read, and the
# earliest hour of his day that any of them reaches is what the seller gets.
_CRONS = re.findall(r"cron:\s*'(\d+)\s+([\d*/,-]+)\s", SAID_IN_THE_WORKFLOW)
check("the schedule can be read out of the workflow at all", len(_CRONS) > 0)


def _hours_his_day_is_woken_at(crons):
    """Every hour of HIS day this workflow really wakes at, out of every line.

    A `*` in the hour field is every hour; a list or a step is expanded the same
    way, because the point is not the spelling but which hours are reachable.
    """
    woken = set()
    for minute, hour in crons:
        for one in _the_hours_meant(hour):
            woken.add(((one + clock.HOURS_AHEAD_OF_UTC)
                       + (1 if int(minute) + clock.MINUTES_AHEAD_OF_UTC >= 60 else 0)) % 24)
    return woken


def _the_hours_meant(field):
    """The UTC hours a cron hour field names. Raises on anything it cannot read."""
    if field == "*":
        return list(range(24))
    out = []
    for piece in field.split(","):
        every = 1
        if "/" in piece:
            piece, step = piece.split("/", 1)
            every = int(step)
        if piece == "*":
            piece = "0-23"
        if "-" in piece:
            first, last = (int(one) for one in piece.split("-", 1))
        else:
            first = last = int(piece)
        out += list(range(first, last + 1, every))
    return out


_WOKEN = _hours_his_day_is_woken_at(_CRONS)
check("and it wakes at at least one hour of his day", len(_WOKEN) > 0)

# **WHICH HOURS A SELLER COULD CHOOSE AND ACTUALLY BE FETCHED AT.** The chosen
# hour is a FLOOR, so a tick at 02:23 satisfies 0, 1 and 2 and nothing above.
_EARLIEST = min(_WOKEN)
_REACHED = tuple(
    hour for hour in range(clock.FIRST_HOUR, clock.LAST_HOUR + 1)
    if any(clock.why_not_now(None, datetime(2026, 9, 8, at, 23), hour) is None
           for at in sorted(_WOKEN))
)

# **THIS PINS A FAULT, NOT A REPAIR, AND IT IS WRITTEN THAT WAY ROUND ON
# PURPOSE.** The day somebody repairs it -- by any of the three ways -- this goes
# red by NAME rather than by the count at the bottom, and says what to do.
check("KNOWN FAULT, NOT FIXED: the workflow wakes at ONE hour of his day, so most "
      "of the hours a seller can choose are never reached. **IF THIS IS RED, THE "
      "SCHEDULE HAS CHANGED -- read the finding on `the-run-that-starts-itself` in "
      "tools/work.json and turn this check round rather than widening it.**",
      len(_WOKEN) == 1 and _EARLIEST == clock.NOT_BEFORE_HOUR)
check("and only the hours at or below that one tick are ever fetched at",
      _REACHED == tuple(range(clock.FIRST_HOUR, _EARLIEST + 1)))
# **SAID AS WHAT IT IS RATHER THAN OVERSTATED.** An earlier wording here said
# hours 3 to 23 never fetch "on any day", and that is not honest for the hour or
# two just above the tick: `clock.why_not_now` is a floor precisely because
# GitHub's own documentation says a scheduled run can be DELAYED, and a delayed
# tick does reach the hour after it. It is the hours well above the tick that
# never fetch, and there are twenty of them.
check("and the hours well above the one tick can never be reached, delay or no delay",
      all(hour not in _REACHED for hour in range(_EARLIEST + 2, clock.LAST_HOUR + 1)))
# **AND THE SENTENCE THAT HID IT IS GONE.** The workflow used to claim the clock
# made a run happen at the seller's hour whatever the cron line said.
check("and the workflow no longer claims the clock fetches at the chosen hour "
      "whatever this line says",
      "still fetches at the hour the seller can see" not in SAID_IN_THE_WORKFLOW)

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 190
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
