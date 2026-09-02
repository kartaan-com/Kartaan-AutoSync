"""Checks for what one run hands to the next.

**THE ONE THIS FILE EXISTS FOR: A MISSING RECORD AND A DAMAGED ONE ARE NOT THE
SAME THING.** Missing is an ordinary first night. Damaged, read as empty, throws
away what Amazon is already building -- and asking again is one rationed call a
minute and two reports where there should be one. Reading them alike is how a
system quietly begins again every night for ever.

Run: python autosync/between_runs_checks.py
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import between_runs as tool  # noqa: E402

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


def refused(work):
    """Did this refuse? Answers the refusal, or None if it did not refuse."""
    try:
        work()
        return None
    except Exception as wrong:  # noqa: BLE001
        return wrong


AT = datetime(2026, 8, 28, 20, 30)

# ------------------------------------------- missing is not the same as damaged

check("nothing at all is a first night, not a fault",
      answered(lambda: tool.read(None)) == tool.empty())

# **AN EMPTY FILE IS NOT A FIRST NIGHT.** Something wrote it. Read as a fresh
# start it would throw away whatever it was meant to hold.
check("an empty file refuses rather than reading as a first night",
      isinstance(refused(lambda: tool.read(b"")), tool.Damaged))
check("and it says an empty file is not the same as no file",
      "not the same as no file" in str(refused(lambda: tool.read(b""))))

# **THE SENTENCE IS PART OF THE ANSWER.** Whoever reads it at seven in the
# morning has to be told why nothing was started, or the refusal is just a job
# that went red.
check("a record that will not read says so, and says why nothing was started",
      "could not be read" in str(refused(lambda: tool.read(b"{not json"))))
check("and it names what reading it as empty would have cost",
      "already building" in str(refused(lambda: tool.read(b"{not json"))))

check("something that is not a record at all refuses",
      isinstance(refused(lambda: tool.read(b"this is not a record")), tool.Damaged))
check("a list where a record should be refuses",
      isinstance(refused(lambda: tool.read(b'[1, 2, 3]')), tool.Damaged))
check("and a refusal says nothing has been started",
      "Nothing has been started" in str(refused(lambda: tool.read(b'[1, 2, 3]'))))

# **A RECORD OF A SHAPE THIS JOB DOES NOT KNOW IS NOT READ HALFWAY.** Reading the
# fields it recognises and dropping the rest is how the dropped part goes missing
# silently.
check("a record written in a shape this job does not read refuses",
      isinstance(refused(lambda: tool.read(b'{"shape": 99}')), tool.Damaged))
check("and it names both shapes",
      "99" in str(refused(lambda: tool.read(b'{"shape": 99}')))
      and str(tool.SHAPE) in str(refused(lambda: tool.read(b'{"shape": 99}'))))

# ------------------------------------------- what Amazon is building

WITH_ONE = (
    b'{"shape": 2, "in_flight": [{"report": "az_orders", "day": "2026-08-27", '
    b'"theirs": "5555"}], "run_days": [], "standing": []}'
)
check("what Amazon is building is read back under its report and its day",
      answered(lambda: tool.read(WITH_ONE).in_flight) == {("az_orders", "2026-08-27"): "5555"})

# **REFUSED, NOT SKIPPED.** Skipping one line is how a report Amazon is already
# building gets asked for a second time -- the single thing this record is for.
for missing, what in (
    (b'{"shape": 2, "in_flight": [{"day": "2026-08-27", "theirs": "5555"}]}', "no report"),
    (b'{"shape": 2, "in_flight": [{"report": "az_orders", "theirs": "5555"}]}', "no day"),
    (b'{"shape": 2, "in_flight": [{"report": "az_orders", "day": "2026-08-27"}]}', "nothing Amazon calls it"),
    (b'{"shape": 2, "in_flight": [{"report": "az_orders", "day": "not a day", "theirs": "5"}]}', "a day that is not a day"),
    (b'{"shape": 2, "in_flight": ["az_orders"]}', "a line that is not a record"),
):
    check(f"a line with {what} refuses the whole record rather than being skipped",
          isinstance(refused(lambda m=missing: tool.read(m)), tool.Damaged))

check("an incomplete line says which line it was, or nobody can mend it",
      "az_orders" in str(refused(lambda: tool.read(
          b'{"shape": 2, "in_flight": [{"report": "az_orders", "theirs": "5555"}]}'))))
check("and it says it is a line about what Amazon is building",
      "Amazon is building" in str(refused(lambda: tool.read(
          b'{"shape": 2, "in_flight": [{"report": "az_orders", "theirs": "5555"}]}'))))

check("a day a run happened that is not a day refuses",
      isinstance(refused(lambda: tool.read(b'{"shape": 2, "run_days": ["never"]}')), tool.Damaged))

# ------------------------------------------- there and back again

FULL = tool.Between(
    in_flight={("az_orders", "2026-08-27"): "5555", ("az_returns", "2026-08-26"): "6666"},
    last_started=datetime(2026, 8, 28, 20, 30),
    last_finished=datetime(2026, 8, 28, 20, 44),
    run_days=(date(2026, 8, 26), date(2026, 8, 27), date(2026, 8, 28)),
    standing=("autosync::nothing-ran", "az_orders::late"),
    files_read=("1AbC", "2DeF"),
)
check("everything written down comes back the same",
      answered(lambda: tool.read(tool.write(FULL))) == FULL)

# **THE SAME RECORD WRITES THE SAME BYTES**, or a difference between two of them
# means nothing.
shuffled = tool.Between(
    in_flight={("az_returns", "2026-08-26"): "6666", ("az_orders", "2026-08-27"): "5555"},
    last_started=FULL.last_started,
    last_finished=FULL.last_finished,
    run_days=(date(2026, 8, 28), date(2026, 8, 26), date(2026, 8, 27)),
    standing=("az_orders::late", "autosync::nothing-ran"),
    files_read=("2DeF", "1AbC"),
)
check("the same record written in a different order gives the same bytes",
      answered(lambda: tool.write(shuffled)) == answered(lambda: tool.write(FULL)))

# **IT IS READ BY A PERSON ON THE NIGHT SOMETHING HAS GONE WRONG.** It sits in
# the seller's own Drive, and one very long line is a file nobody can read.
check("the record is written so a person can read it",
      len((answered(lambda: tool.write(FULL)) or b"").splitlines()) > 1)

# ------------------------------------------- starting and finishing

started = answered(lambda: tool.empty().started(AT))
check("a run that starts is written down as started", started.last_started == AT)
# **CLEARED, NOT LEFT.** A record saying it started at nine and finished at eight
# is a record the clock reads as a run that has already finished.
check("and whatever the last run's finish was, it is cleared", started.last_finished is None)
check("the day is written down the moment a run starts, not when it succeeds",
      started.run_days == (AT.date(),))

again = answered(lambda: started.started(AT + timedelta(minutes=5)))
check("two runs on one day leave one day, not two", again.run_days == (AT.date(),))

done = answered(lambda: started.finished(AT + timedelta(minutes=14)))
check("a run that finishes is written down as finished",
      done.last_finished == AT + timedelta(minutes=14))
check("and finishing does not disturb when it started", done.last_started == AT)

# **THE LIST OF DAYS IS TRIMMED**, or the file grows for ever and stops being
# writable on the one night it matters.
many = tool.Between(run_days=tuple(date(2026, 1, 1) + timedelta(days=n) for n in range(200)))
check("a long history is trimmed when it is written and read back",
      len(answered(lambda: tool.read(tool.write(many)).run_days) or ()) == tool.KEEP_RUN_DAYS)
check("and the days that are kept are the most recent ones",
      answered(lambda: tool.read(tool.write(many)).run_days[-1]) == date(2026, 1, 1) + timedelta(days=199))
check("starting a run also trims the history",
      len(answered(lambda: many.started(AT).run_days) or ()) == tool.KEEP_RUN_DAYS)
check("and the day just started is one of the ones kept",
      AT.date() in (answered(lambda: many.started(AT).run_days) or ()))

# ------------------------------------------- what must never be written down

check("an ordinary record may be saved",
      answered(lambda: tool.why_it_cannot_be_saved(FULL)) is None)
check("a first night may be saved",
      answered(lambda: tool.why_it_cannot_be_saved(tool.empty())) is None)
check("a run still going may be saved -- that is the whole point of writing it early",
      answered(lambda: tool.why_it_cannot_be_saved(started)) is None)

# **A BROKEN CLOCK IS CAUGHT ON THE WAY OUT**, where it is still one run's
# problem. Written down, it makes the clock refuse every later run for a day on
# the strength of something that never happened.
finished_only = tool.Between(last_finished=AT)
check("a run recorded as finished without ever starting is refused",
      answered(lambda: tool.why_it_cannot_be_saved(finished_only)) is not None)
backwards = tool.Between(last_started=AT, last_finished=AT - timedelta(minutes=1))
check("a run that finished before it started is refused",
      answered(lambda: tool.why_it_cannot_be_saved(backwards)) is not None)
# **BOTH MOMENTS, TOLD APART.** Naming only one of them reads as true whichever
# half of the sentence survives, which is exactly what it did before.
check("the refusal says a run cannot finish before it started",
      "cannot finish" in (answered(lambda: tool.why_it_cannot_be_saved(backwards)) or ""))
check("and it names when it started and when it says it finished, separately",
      AT.isoformat() in (answered(lambda: tool.why_it_cannot_be_saved(backwards)) or "")
      and (AT - timedelta(minutes=1)).isoformat()
      in (answered(lambda: tool.why_it_cannot_be_saved(backwards)) or ""))
# Exactly together is not backwards -- a run that started and finished in the
# same second is a run that had nothing to do, which is an ordinary night.
together = tool.Between(last_started=AT, last_finished=AT)
check("a run that started and finished in the same second may be saved",
      answered(lambda: tool.why_it_cannot_be_saved(together)) is None)

# ------------------------------------------- handing it to the pieces that use it

reads = answered(lambda: tool.as_the_clock_reads_it(started))
check("the clock is handed when the run started", reads.started == AT)
check("and is told the run has not finished", reads.still_going is True)
check("a finished run is not still going",
      answered(lambda: tool.as_the_clock_reads_it(done).still_going) is False)

flight = answered(lambda: tool.carried_in_flight(FULL))
check("the runner is handed what Amazon is already building",
      answered(lambda: flight.what_was_asked("az_orders", date(2026, 8, 27))) == "5555")
check("and nothing for a day nobody asked about",
      answered(lambda: flight.what_was_asked("az_orders", date(2026, 8, 20))) is None)

# **THE RECORD IS UPDATED FROM WHAT THE RUN LEFT, not the other way round.**
flight.remember("az_settlements", date(2026, 8, 27), "7777")
after = answered(lambda: tool.with_in_flight(FULL, flight))
check("what the run left in flight is taken back into the record",
      after.in_flight.get(("az_settlements", "2026-08-27")) == "7777")
check("and the record it came from is untouched",
      ("az_settlements", "2026-08-27") not in FULL.in_flight)

spoken = answered(lambda: tool.with_standing(FULL, ["one", "two"]))
check("the alarms that have gone out are taken back into the record",
      spoken.standing == ("one", "two"))
check("and that record is untouched too", FULL.standing == ("autosync::nothing-ran", "az_orders::late"))

# **A RECORD ANYTHING CAN EDIT IN PLACE IS A RECORD TWO PARTS OF A RUN CAN
# DISAGREE ABOUT.** The reference's job objects were mutable and a backfill
# changed one under the job that was reading it.
check("a record cannot be edited after it is made",
      answered(lambda: setattr(FULL, "last_started", AT)) is None and bool(THREW))
THREW.clear()

check("the file it lives in has one name, so nothing can write a second beside it",
      answered(lambda: tool.FILE_NAME) == "autosync-state.json")

# ------------------- a moment that cannot be read is damage (R2#2)

# **NOTHING WRITTEN DOWN AND SOMETHING UNREADABLE ARE NOT THE SAME THING, and
# this is the field where that costs the most.** Anything unreadable used to come
# back as nothing -- and nothing is what the clock reads as "no run has ever
# started", which is exactly the state in which a run is allowed to begin. **So a
# record saying a run IS GOING, damaged in this one field, let a second one
# start**, and two at once fetch every file twice into two differently-named
# copies.
import json as _json  # noqa: E402

def _record(**fields):
    return _json.dumps({"shape": tool.SHAPE, **fields}).encode("utf-8")

hurt = refused(lambda: tool.read(_record(last_started="yesterday-ish")))
check("a start time that is not a moment is damage, not a first night",
      isinstance(hurt, tool.Damaged))
check("and it says nothing has been started", "nothing has been started" in str(hurt).lower())
check("and it says why -- a run may already be going",
      "already be going" in str(hurt))
check("and it says what it actually found",
      "yesterday-ish" in str(hurt))
check("a finish time that is not a moment is damage too",
      isinstance(refused(lambda: tool.read(_record(last_finished="soon"))), tool.Damaged))

# **BUT A FIELD THAT IS SIMPLY NOT THERE IS AN ORDINARY FIRST NIGHT.** Refusing
# that would stop the very first run of every seller for ever.
first = answered(lambda: tool.read(_record()))
check("a record with no start time at all is an ordinary first night",
      answered(lambda: first.last_started) is None)
check("and one written down as nothing is too",
      answered(lambda: tool.read(_record(last_started=None)).last_started) is None)
# And a real moment still reads as one.
check("and a real moment still reads as itself",
      answered(lambda: tool.read(_record(last_started="2026-08-29T02:23:00")).last_started)
      == datetime(2026, 8, 29, 2, 23))

# ------------------- which files have already been READ (2026-09-02)

# **THE WHOLE POINT: A LIST OF FILES, NEVER A DATE.** His own case, and it is
# checked below end to end rather than described.

check("a record with no list of read files is an ordinary first night",
      answered(lambda: tool.read(_record()).files_read) == ())
check("and so is one written down as an empty list",
      answered(lambda: tool.read(_record(files_read=[])).files_read) == ())
check("the files that have been read are written down and come back the same",
      answered(lambda: tool.read(tool.write(FULL)).files_read) == ("1AbC", "2DeF"))
check("the same files in a different order give the same bytes",
      answered(lambda: tool.write(shuffled)) == answered(lambda: tool.write(FULL)))
check("the same file written down twice comes back once",
      answered(lambda: tool.read(_record(files_read=["1AbC", "1AbC"])).files_read) == ("1AbC",))
# **FOUND BY PUTTING THE FAULT BACK, 2026-09-02.** Writing the list without
# deduplicating it went in and NOTHING went red -- because reading it back
# deduplicates, so the round trip still matched. Two records that mean the same
# thing were writing different bytes, which is the one thing that makes a
# difference between two of them mean anything.
check("a record holding the same file twice writes the same bytes as one holding it once",
      answered(lambda: tool.write(tool.Between(files_read=("1AbC", "1AbC"))))
      == answered(lambda: tool.write(tool.Between(files_read=("1AbC",)))))

# **REFUSED, NOT SKIPPED.** A dropped id is a file that is read a second time,
# and an old file re-read puts its old figures back over a newer file's.
for bad, what in ((["", "1AbC"], "a blank id"), ([{"id": "1AbC"}], "a line that is not an id"),
                  ([12345], "a number where an id should be")):
    check(f"{what} in the list of read files refuses the whole record",
          isinstance(refused(lambda b=bad: tool.read(_record(files_read=b))), tool.Damaged))
hurt_files = refused(lambda: tool.read(_record(files_read=[""])))
check("and it says nothing has been started", "Nothing has been started" in str(hurt_files))
check("and it names what reading past it would have cost",
      "read again" in str(hurt_files) and "over a newer" in str(hurt_files))

# **A RECORD FROM BEFORE THIS FIELD EXISTED REFUSES.** Read halfway it would say
# nothing had ever been read -- and re-read the seller's entire history.
older = refused(lambda: tool.read(b'{"shape": 1, "run_days": [], "standing": []}'))
check("a record written before this field existed refuses rather than reading as a first night",
      isinstance(older, tool.Damaged))
check("and it names both shapes so somebody can tell what happened",
      "1" in str(older) and str(tool.SHAPE) in str(older))

# **TAKEN BACK INTO THE RECORD THE SAME WAY THE ALARMS ARE.**
having_read = answered(lambda: tool.with_files_read(FULL, ["9XyZ", "1AbC"]))
check("what the run read is taken back into the record",
      having_read.files_read == ("1AbC", "9XyZ"))
check("and the record it came from is untouched", FULL.files_read == ("1AbC", "2DeF"))
check("blanks handed in are dropped rather than written down as files",
      answered(lambda: tool.with_files_read(FULL, ["", "  ", "9XyZ"]).files_read) == ("9XyZ",))

# ------------------- HIS CASE: THE FOURTH FILE ARRIVES AFTER THE FIFTH

# 1st, 2nd, 3rd downloaded. The 4th fails. The 5th downloads. Later the 4th
# arrives. **This is the reason the record holds a list and not a date**, and it
# is checked across a real write and read rather than in one run's memory.
import whats_new  # noqa: E402

def _f(which, name, size=100):
    return whats_new.InTheFolder(which=which, name=name, size=size)

FIRST_THREE_AND_FIFTH = [
    _f("id-1", "meesho_orders_2026-08-01.csv"),
    _f("id-2", "meesho_orders_2026-08-02.csv"),
    _f("id-3", "meesho_orders_2026-08-03.csv"),
    _f("id-5", "meesho_orders_2026-08-05.csv"),
]
THE_FOURTH = _f("id-4", "meesho_orders_2026-08-04.csv")

# Run one: four files land and are read, and what was read is written to Drive.
night_one = answered(lambda: whats_new.what_is_new(FIRST_THREE_AND_FIFTH, ()))
check("on the first night the four files that arrived are all new", len(night_one.new) == 4)
after_one = answered(lambda: tool.with_files_read(
    tool.empty().started(AT), whats_new.now_read((), night_one.new)))
on_drive = answered(lambda: tool.write(after_one))

# Run two, a different night, reading the record back off Drive.
night_two_record = answered(lambda: tool.read(on_drive))
night_two = answered(lambda: whats_new.what_is_new(
    FIRST_THREE_AND_FIFTH + [THE_FOURTH], night_two_record.files_read))
check("THE FOURTH FILE, ARRIVING AFTER THE FIFTH, IS READ ON THE NEXT NIGHT",
      [one.which for one in night_two.new] == ["id-4"])
check("and the four already read are not read a second time", len(night_two.already) == 4)

# **KEPT AS A DATE INSTEAD, THE FOURTH IS SKIPPED FOR EVER AND SILENTLY.** Shown
# rather than asserted, so the check fails the day somebody makes it a date.
read_up_to = max(one.name for one in FIRST_THREE_AND_FIFTH)   # ..._2026-08-05.csv
check("keyed by the last date read instead, the fourth would never have been read",
      THE_FOURTH.name < read_up_to)
check("and nothing in the record is a high-water date -- it is a list of file ids",
      sorted(_json.loads(on_drive).get("files_read") or ()) == ["id-1", "id-2", "id-3", "id-5"])

# Run three: the fourth is in the record now, and the folder holds nothing new.
after_two = answered(lambda: tool.with_files_read(
    night_two_record, whats_new.now_read(night_two_record.files_read, night_two.new)))
night_three = answered(lambda: whats_new.what_is_new(
    FIRST_THREE_AND_FIFTH + [THE_FOURTH],
    answered(lambda: tool.read(tool.write(after_two)).files_read)))
check("once the fourth has been read it is not read again the night after",
      night_three.anything_to_do is False)

# **AND A FILE THAT ARRIVED EMPTY IS STILL NOT IN THE RECORD**, so tomorrow's
# real file for that day is still new. `whats_new` decides that; this checks the
# record does not quietly undo it on its way through Drive.
with_empty = answered(lambda: whats_new.what_is_new([_f("id-6", "late.csv", size=0)], ()))
kept = answered(lambda: tool.read(tool.write(tool.with_files_read(
    tool.empty(), whats_new.now_read((), with_empty.new)))).files_read)
check("a file that arrived empty is not written down as read", "id-6" not in kept)

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 83
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
