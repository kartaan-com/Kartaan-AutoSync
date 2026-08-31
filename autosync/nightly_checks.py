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

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import between_runs  # noqa: E402
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

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 137
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
