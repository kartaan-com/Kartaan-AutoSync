"""Checks for talking to the seller's own Firestore (D114).

**THE TRANSPORT IS A STAND-IN**, so every one of these runs with no account, no
token and no internet. It is deliberately harsher than the real thing: it refuses
anything it was not told to expect, so a call built with the wrong shape fails
loudly here rather than at two in the morning on somebody's machine.

**THE ONE THAT MATTERS MOST: a 403 says WHY.** A seller who connected before D114
granted `drive.file` and nothing else; their token uploads files all night and
cannot write one record. Without the sentence that names it, that reads as a
broken database and costs a person an evening.

Run: python autosync/firestore_door_checks.py
"""

import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import board  # noqa: E402
import firestore  # noqa: E402
import firestore_door as tool  # noqa: E402
import runlog  # noqa: E402
from the_other_half import readFromServer  # noqa: E402

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


def _why(work):
    """The words a refusal came with, so a check can ask what it SAID."""
    try:
        work()
    except Exception as wrong:  # noqa: BLE001
        return str(wrong)
    return ""


PROJECT = "seller-project-1"
AT = datetime(2026, 8, 29, 2, 15, 30)


class Reply:
    """What came back. The five things the door asks about, and nothing else."""

    def __init__(self, status=200, body=None):
        self.status = status
        self._body = body if body is not None else {}
        self.text = str(body or "")

    @property
    def ok(self):
        return 200 <= self.status < 300

    def json(self):
        return self._body


class Transport:
    """A stand-in Google. Remembers every call; answers what it was told to."""

    def __init__(self, answers=None):
        self.posts = []
        self.gets = []
        self.answers = list(answers or [])

    def _next(self):
        return self.answers.pop(0) if self.answers else Reply(200, {})

    def post(self, url, params=None, headers=None, json=None, data=None):
        self.posts.append({"url": url, "json": json})
        return self._next()

    def get(self, url, params=None, headers=None):
        self.gets.append({"url": url, "params": params})
        return self._next()


LINE = runlog.Line(at=AT, run="20260829T021500", report="az_orders", level="done", message="ok")
ROW = board.Row(data_date=date(2026, 8, 28), report_id="az_orders", expected=True,
                state=board.MISSING, days_late=3)

# ------------------------------------------- where the calls go

check("a commit goes where Google says it does",
      tool.COMMIT.format(api=firestore.API, project=PROJECT, database=firestore.DATABASE)
      == f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents:commit")
check("and one document is asked for by its own full name",
      tool.ONE_DOCUMENT.format(api=firestore.API, name="projects/p/databases/(default)/documents/a/b")
      == "https://firestore.googleapis.com/v1/projects/p/databases/(default)/documents/a/b")

# **THE SCOPE THIS DOOR NEEDS IS THE SCOPE THE SELLER IS ASKED FOR.** Asked for in
# `server/going_off.py` and needed here, and nothing mechanical joins the two --
# so it is pinned, both ways.
check("the scope it needs is the datastore one", tool.SCOPE == "https://www.googleapis.com/auth/datastore")
GOING_OFF = readFromServer("server", "going_off.py")
check("and it is the one the seller is actually asked for", f'"{tool.SCOPE}"' in GOING_OFF)
check("and the seller is still asked for Drive as well",
      '"https://www.googleapis.com/auth/drive.file"' in GOING_OFF)

# ------------------------------------------- the run log

there = Transport()
answered(lambda: tool.a_log_sink(there, PROJECT)([LINE]))
check("a log line is sent as one write", len(there.posts) == 1)
check("and it goes to the commit address", there.posts[0]["url"].endswith("documents:commit"))
sent = there.posts[0]["json"]["writes"][0]
check("and it names the run log, in the seller's own project",
      sent["update"]["name"] == f"projects/{PROJECT}/databases/(default)/documents/sync_log/"
      + "20260829T021500::2026-08-29T02:15:30::0000::az_orders::done::"
      + firestore.fingerprint("ok"))
check("and the moment in it is text rather than a timestamp",
      sent["update"]["fields"]["at"] == {"stringValue": "2026-08-29T02:15:30"})

# **NOTHING TO SAY IS NOT A CALL.** A commit with no writes in it is a round trip
# spent learning nothing, on every tick that fetched nothing.
quiet = Transport()
answered(lambda: tool.a_log_sink(quiet, PROJECT)([]))
check("nothing to write makes no call at all", quiet.posts == [])

# The same line twice lands at the same name, which is what makes a retried flush
# safe -- the second write writes what is already there.
twice = Transport()
answered(lambda: tool.a_log_sink(twice, PROJECT)([LINE, LINE]))
check("the same line twice is written at the same name",
      twice.posts[0]["json"]["writes"][0]["update"]["name"]
      == twice.posts[0]["json"]["writes"][1]["update"]["name"])

# ------------------------------------------- the day board

board_there = Transport()
answered(lambda: tool.a_board_sink(board_there, PROJECT)([ROW]))
check("a board row is sent as one write", len(board_there.posts) == 1)
check("and it is named for its report and its day",
      board_there.posts[0]["json"]["writes"][0]["update"]["name"].endswith("/sync_board/az_orders::2026-08-28"))
check("and it says how late the day is",
      board_there.posts[0]["json"]["writes"][0]["update"]["fields"]["daysLate"] == {"integerValue": "3"})
empty_board = Transport()
answered(lambda: tool.a_board_sink(empty_board, PROJECT)([]))
check("an empty board makes no call at all", empty_board.posts == [])

# ------------------------------------------- the run itself

started = Transport()
answered(lambda: tool.a_run_sink(started, PROJECT)("20260829T021500", AT))
check("a run is written down when it starts", len(started.posts) == 1)
check("and it is named by its own name",
      started.posts[0]["json"]["writes"][0]["update"]["name"].endswith("/sync_runs/20260829T021500"))
# **BLANK IS HOW A RUN THAT NEVER FINISHED IS TOLD FROM ONE THAT FAILED.**
check("and a run still going says nothing about finishing",
      started.posts[0]["json"]["writes"][0]["update"]["fields"]["finishedAt"] == {"stringValue": ""})
finished = Transport()
answered(lambda: tool.a_run_sink(finished, PROJECT)(
    "20260829T021500", AT, finished_at=datetime(2026, 8, 29, 2, 20, 0)))
check("and a finished one says when",
      finished.posts[0]["json"]["writes"][0]["update"]["fields"]["finishedAt"]
      == {"stringValue": "2026-08-29T02:20:00"})
# Written at the same name both times, so finishing REPLACES starting rather than
# leaving two records of one run.
check("finishing writes over starting rather than beside it",
      finished.posts[0]["json"]["writes"][0]["update"]["name"]
      == started.posts[0]["json"]["writes"][0]["update"]["name"])

# ------------------------------------------- what it will not write

check("the door has no way to write a seller's own records",
      answered(lambda: firestore.one_write(PROJECT, "orders", "x", {"a": "b"})) is None and bool(THREW))
THREW.clear()

# ------------------------------------------- when Google says no

refused = Transport([Reply(403, "the caller does not have permission")])
check("a refusal is thrown rather than counted as sent",
      answered(lambda: tool.a_log_sink(refused, PROJECT)([LINE])) is None and bool(THREW))
THREW.clear()
# **THE LIKELIEST CAUSE IS NAMED**, because it is documented and it is silent.
words = _why(lambda: tool.a_log_sink(Transport([Reply(403, "no")]), PROJECT)([LINE]))
check("and a 403 says the seller may need to connect again", "connecting again" in words)
check("and it says what was being done at the time", "writing the run log down" in words)
check("a 404 says the record or the project is wrong",
      "project id" in _why(lambda: tool.a_log_sink(Transport([Reply(404, "no")]), PROJECT)([LINE])))
check("and that the record itself may simply not be there",
      "record is not there" in _why(lambda: tool.a_log_sink(Transport([Reply(404, "no")]), PROJECT)([LINE])))
# **AND IT SAYS WHAT WAS BEING DONE, AND WHAT GOOGLE ANSWERED.** Without both, a
# person reading the log has a sentence about a project id and no idea which call
# produced it or which of Google's refusals it was.
NOT_THERE = _why(lambda: tool.a_log_sink(Transport([Reply(404, "no")]), PROJECT)([LINE]))
check("and a 404 says what was being done at the time", "writing the run log down" in NOT_THERE)
check("and which refusal it was", "(404)" in NOT_THERE)
check("and anything else says what Google said",
      "500" in _why(lambda: tool.a_log_sink(Transport([Reply(500, "server on fire")]), PROJECT)([LINE])))
check("and an answer that never came at all is its own sentence",
      "said nothing at all" in _why(lambda: tool.a_log_sink(Transport([None]), PROJECT)([LINE])))

# **A HALF-SENT FLUSH MUST NOT REPORT SUCCESS.** The flush advances its marker
# only if the sink returned, and a sink that swallowed a failed second call would
# advance it over lines that never left the building.
MANY = [firestore.one_write(PROJECT, firestore.LOG, f"r{n}", {"a": "x"}) for n in range(4)]
SMALL = firestore.how_big(MANY[:1])
half = Transport([Reply(200, {}), Reply(500, "no")])
check("a call that fails part way through throws rather than answering how many went",
      answered(lambda: tool.write_them(half, PROJECT, MANY, "trying", room=SMALL)) is None and bool(THREW))
THREW.clear()
check("and it stopped there rather than carrying on with the rest", len(half.posts) == 2)

fine = Transport()
check("and when every call works, it says how many went",
      answered(lambda: tool.write_them(fine, PROJECT, MANY, "trying")) == 4)
check("and how much of one call may be filled comes from Google's own limit",
      firestore.ROOM == firestore.A_REQUEST_IS_AT_MOST - firestore.LEAVE_SPARE)

# ------------------------------------------- the hour it reads

asked = Transport([Reply(200, {"fields": {"fetchHour": {"stringValue": "23"}}})])
check("the chosen hour is read off the business record",
      answered(lambda: tool.what_they_chose(asked, PROJECT)) == "23")
check("and it is asked for by name, not searched for",
      asked.gets[0]["url"].endswith("/documents/businesses/business"))
# **NOTHING IS WRITTEN WHILE READING IT.** It is the seller's setting, and a job
# that could write it would be a second author of one fact (D114).
check("and reading it writes nothing at all", asked.posts == [])

# **A BUSINESS NOT SET UP YET IS AN ANSWER, NOT A FAILURE.** This is the one place
# a 404 means "they have not", rather than "something is wrong".
# **AND IT ANSWERED RATHER THAN THREW**, which is the whole difference: `None`
# returned means "they have not chosen"; `None` because it threw means the job
# never started. A check that only looked at the answer could not tell them apart.
check("no business record yet means no hour chosen, and the job still runs",
      answered(lambda: tool.what_they_chose(Transport([Reply(404, "no such document")]), PROJECT)) is None
      and not THREW)
check("but a database that would not answer is thrown, not read as no choice",
      answered(lambda: tool.what_they_chose(Transport([Reply(500, "no")]), PROJECT)) is None and bool(THREW))
THREW.clear()
check("and so is one that refuses the permission",
      answered(lambda: tool.what_they_chose(Transport([Reply(403, "no")]), PROJECT)) is None and bool(THREW))
THREW.clear()
check("a record with no hour in it means no hour chosen",
      answered(lambda: tool.what_they_chose(Transport([Reply(200, {"fields": {"name": {"stringValue": "R"}}})]),
                                            PROJECT)) is None)

# ------------------------------------------- both places, in that order

order = []
both = tool.both_places(lambda lines: order.append("database"), lambda lines: order.append("drive"))
answered(lambda: both([LINE]))
# **THE DATABASE FIRST AND DRIVE SECOND, and the order is the whole design.** A
# flush that throws sends the same lines again; the database write is named from
# the line itself so writing it twice writes it once, and the Drive copy is a file
# that is appended to, so writing it twice writes the lines twice.
check("the seller's database is written first and their Drive second", order == ["database", "drive"])


def _blows_up(lines):
    raise RuntimeError("Drive refused")


order.clear()
check("and if Drive fails the whole flush fails, so the lines go again",
      answered(lambda: tool.both_places(lambda lines: order.append("database"), _blows_up)([LINE]))
      is None and bool(THREW))
THREW.clear()
check("having written the database first, which is safe to repeat", order == ["database"])
check("and if the database fails, Drive is never written at all",
      _why(lambda: tool.both_places(_blows_up, lambda lines: order.append("drive"))([LINE])) != ""
      and order == ["database"])

# **THE OLD FOLDER NAME MUST NOT COME BACK (the ERP's open item 12).** It was
# accepted alongside `Kartaan-ERP` while the rename was in progress; the rename
# is done, and a fallback nobody writes down is how two spellings of one thing
# survive for a year.
_DOOR = Path(__file__).with_name("the_other_half.py").read_text(encoding="utf-8")
check("the door no longer accepts the old folder name",
      "'Kartaan-ERP', 'Kartaan'" not in _DOOR and '"Kartaan-ERP", "Kartaan"' not in _DOOR)

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 47
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
