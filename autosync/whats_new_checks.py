"""Checks for what starts a read.

**THE MOST IMPORTANT CHECK IN THIS FILE READS THE SOURCE ITSELF**: that
`what_is_new` is handed nothing through which a fetch's success or failure could
reach the decision. His rule is that a read starts SOLELY on what is new, and a
rule that depends on nobody passing the wrong thing is remembered, not enforced.

Run: python autosync/whats_new_checks.py
"""

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import whats_new as tool  # noqa: E402

ran = 0
failures = []
THREW = []


def answered(work):
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


def refused_by(work):
    try:
        work()
    except tool.CannotTell:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


def _catch(work):
    try:
        work()
    except Exception as e:  # noqa: BLE001
        return e
    return None


def f(which, name="", size=10):
    return tool.InTheFolder(which=which, name=name or which, size=size)


# ------------------------------------------- the rule, made structural

TAKES = list(inspect.signature(tool.what_is_new).parameters)
check("what starts a read is given the folder and what was already read",
      TAKES == ["in_the_folder", "already_read"])
check("AND NOTHING ELSE -- there is nowhere for a fetch's opinion to get in",
      len(TAKES) == 2)
# **AND WHAT IS FORGOTTEN IS DECIDED ON THE SAME TWO THINGS.** A cap that could
# be handed anything else -- a date, a run, a count -- is a cap that can be made
# to forget a file that is still sitting in the folder.
LETS_GO = list(inspect.signature(tool.still_worth_remembering).parameters)
check("what is forgotten is decided on the folder and what was already read",
      LETS_GO == ["in_the_folder", "already_read"])
check("AND NOTHING ELSE -- no date, no count, nowhere for a day-cap to get in",
      len(LETS_GO) == 2)
# **A WORD-SCAN OF THE SOURCE WAS TRIED FIRST AND WAS THE WRONG CHECK.** It read
# the docstring too, so the sentence explaining that a day fetched again must
# still be read made the check go red about the word "fetch". Prose is not code.
#
# **WHAT IS CHECKED INSTEAD IS WHAT THIS FILE CAN REACH AT ALL.** A run's
# success or failure lives in `runlog`, `board`, `schedule` and `reports`; if
# none of them can be imported here, the rule cannot be broken by somebody
# passing the wrong thing later.
SOURCE = Path(tool.__file__).read_text(encoding="utf-8")
IMPORTS = [l.strip() for l in SOURCE.splitlines()
           if l.startswith("import ") or l.startswith("from ")]
for forbidden in ("runlog", "board", "schedule", "reports", "runner", "nightly"):
    check(f"nothing that knows whether a fetch worked is even reachable: {forbidden}",
          not any(forbidden in one for one in IMPORTS))
# **THE MODULES, not the exact wording.** Written as an exact list of import
# LINES, this went red the moment a dead name was tidied out of the typing
# import -- which says nothing about whether a fetch's opinion can reach here.
# What matters is WHICH modules are reachable.
_MODULES = {one.split()[1] for one in IMPORTS if one.startswith("from ")}
_MODULES |= {one.split()[1].split(".")[0] for one in IMPORTS if one.startswith("import ")}
check("what it can reach is only shapes and the one refusal kind",
      _MODULES == {"dataclasses", "typing", "table"})
if _MODULES != {"dataclasses", "typing", "table"}:
    print(f"      it reaches: {sorted(_MODULES)}")

# --------------------------------------------------------- what is new

now = answered(lambda: tool.what_is_new([f("A"), f("B")], []))
check("on a first night every file is new", now is not None and len(now.new) == 2)
check("and there is something to do", now is not None and now.anything_to_do)

now = answered(lambda: tool.what_is_new([f("A"), f("B")], ["A"]))
check("a file already read is not read again", now is not None and len(now.new) == 1)
check("and it is still reported as already read", now is not None and len(now.already) == 1)
check("the one that is new is the right one", now is not None and now.new[0].which == "B")

now = answered(lambda: tool.what_is_new([f("A")], ["A"]))
check("a folder with nothing new leaves nothing to do",
      now is not None and not now.anything_to_do)
check("what it found is said in one line, every count including the noughts",
      now is not None and "0 new files" in now.says() and "0 arrived empty" in now.says()
      and "1 already read" in now.says())

# --------------------------------- identity is the ID, never the name

SAME_NAME = [f("id-one", "meesho_me_orders_2026-08-30.csv"),
             f("id-two", "meesho_me_orders_2026-08-30.csv")]
now = answered(lambda: tool.what_is_new(SAME_NAME, ["id-one"]))
check("A DAY FETCHED AGAIN LANDS UNDER THE SAME NAME AND IS STILL READ",
      now is not None and len(now.new) == 1 and now.new[0].which == "id-two")
check("keyed by name instead, that correction would never have been read",
      len({one.name for one in SAME_NAME}) == 1)
check("two files with one name are both new when neither has been read",
      (lambda x: x is not None and len(x.new) == 2)(
          answered(lambda: tool.what_is_new(SAME_NAME, []))))
check("and a file whose NAME was read but whose id was not is still new",
      (lambda x: x is not None and len(x.new) == 1)(
          answered(lambda: tool.what_is_new(
              [f("id-two", "meesho_me_orders_2026-08-30.csv")],
              ["meesho_me_orders_2026-08-30.csv"]))))

# ------------------------------------------------------ an empty file

now = answered(lambda: tool.what_is_new([f("A", size=0), f("B")], []))
check("a nought-byte file is not handed on to be read",
      now is not None and len(now.new) == 1 and now.new[0].which == "B")
check("it is reported by name rather than dropped",
      now is not None and len(now.empty) == 1 and now.empty[0].which == "A")
check("and said out loud", now is not None and "1 arrived empty" in now.says())
# **WRITTEN AS A ONE-LINER WITH A DEAD `if False` FIRST -- green by construction,
# the third such check written on this project. This one really asks it.**
check("A FILE THAT ARRIVED EMPTY IS NOT MARKED AS READ",
      now is not None and "A" not in tool.now_read([], now.new))
check("and the file that WAS read is marked",
      now is not None and "B" in tool.now_read([], now.new))
check("so tomorrow's real file for that day is still new",
      (lambda x: x is not None and len(x.new) == 1)(
          answered(lambda: tool.what_is_new(
              [f("A", size=900)], tool.now_read([], tool.what_is_new([f("A", size=0)], []).new)))))
check("a file of negative size is treated as empty, not as data",
      (lambda x: x is not None and len(x.empty) == 1)(
          answered(lambda: tool.what_is_new([f("A", size=-1)], []))))

# ------------------------------------------------------- what it refuses

check("a file with no id is refused -- there is no way to tell if it was read",
      refused_by(lambda: tool.InTheFolder(which="", name="something.csv")))
check("and the refusal says what both mistakes would cost",
      (lambda e: e is not None and "second time" in str(e) and "lose the day" in str(e))(
          _catch(lambda: tool.InTheFolder(which=" ", name="something.csv"))))
check("a folder holding something that is not a file is refused",
      refused_by(lambda: tool.what_is_new(["just a name"], [])))
check("and so is marking something that is not a file as read",
      refused_by(lambda: tool.now_read([], ["just a name"])))

# ---------------------------------------- the same file listed twice

now = answered(lambda: tool.what_is_new([f("A"), f("A"), f("A")], []))
check("the same file listed three times is ONE file, not three reads",
      now is not None and len(now.new) == 1)

# ------------------------------------------------- remembering what was read

check("what was read is remembered by id", tool.now_read([], [f("A"), f("B")]) == ("A", "B"))
check("and added to what was already remembered",
      tool.now_read(["Z"], [f("A")]) == ("A", "Z"))
check("remembering the same file twice remembers it once",
      tool.now_read(["A"], [f("A")]) == ("A",))
check("the record is sorted, so two runs that read the same files leave the same thing",
      tool.now_read([], [f("B"), f("A")]) == tool.now_read([], [f("A"), f("B")]))
check("nothing read leaves what was there untouched", tool.now_read(["A"], []) == ("A",))
check("blank entries in the old record are dropped rather than kept for ever",
      tool.now_read(["", "  ", "A"], []) == ("A",))

# **THE WHOLE POINT, END TO END.**
folder = [f("A"), f("B"), f("C", size=0)]
first = tool.what_is_new(folder, [])
remembered = tool.now_read([], first.new)
again = answered(lambda: tool.what_is_new(folder, remembered))
check("READING THE SAME FOLDER AGAIN FINDS NOTHING NEW",
      again is not None and not again.anything_to_do)
check("except the empty one, which is still waiting to arrive properly",
      again is not None and len(again.empty) == 1)
check("and a file that turns up tomorrow is new",
      (lambda x: x is not None and len(x.new) == 1 and x.new[0].which == "D")(
          answered(lambda: tool.what_is_new(folder + [f("D")], remembered))))

print()
# ------------------- HIS CAP: THE FOLDER, AND NOTHING ELSE (2026-09-02)

# **HIS WORDS: "cap on folder".** An id is let go of only when its file has gone.

FOLDER = [f("id-1"), f("id-2"), f("id-3")]

kept = answered(lambda: tool.still_worth_remembering(FOLDER, ["id-1", "id-2", "id-3"]))
check("a file still in the folder is still remembered as read",
      kept.keep == ("id-1", "id-2", "id-3"))
check("and nothing is let go of while everything is still there", kept.forgotten == ())

# **THE ONE THING THE CAP IS FOR.** He tidies Drive; the list shrinks with it.
tidied = answered(lambda: tool.still_worth_remembering([f("id-3")], ["id-1", "id-2", "id-3"]))
check("A FILE THAT HAS GONE FROM THE FOLDER IS LET GO OF", tidied.forgotten == ("id-1", "id-2"))
check("and the ones still there are kept", tidied.keep == ("id-3",))
check("so the list can never be longer than the folder",
      len(tidied.keep) <= len([f("id-3")]))

# **NOT A DAY-COUNT, AND THIS IS THE WHOLE REASON.** A landed file is never
# removed, so a day-cap would let go of an id whose file is still sitting there
# -- and that file, read again, puts its old figures back over newer ones.
old_but_there = answered(lambda: tool.still_worth_remembering(
    [f("id-1", "meesho_orders_2026-01-01.csv")], ["id-1"]))
check("A FILE FROM MONTHS AGO IS STILL REMEMBERED WHILE IT IS STILL IN THE FOLDER",
      old_but_there.forgotten == () and old_but_there.keep == ("id-1",))

# **A FOLDER THAT COMES BACK EMPTY IS A LISTING THAT FAILED, not a folder
# somebody emptied.** Letting go of everything would re-read the whole history.
gone = answered(lambda: tool.still_worth_remembering([], ["id-1", "id-2"]))
check("AN EMPTY FOLDER LISTING LETS GO OF NOTHING AT ALL", gone.forgotten == ())
check("and everything is still remembered", gone.keep == ("id-1", "id-2"))
check("and the reason is said, not left to be guessed at",
      "listing looks like when it failed" in gone.refused_to_forget)
check("and it says how many were saved from being forgotten",
      "2 " in gone.refused_to_forget or " 2 " in gone.refused_to_forget)
# But an empty folder on a first night is simply an empty folder.
check("an empty folder with nothing remembered is not a refusal, just nothing",
      answered(lambda: tool.still_worth_remembering([], [])).refused_to_forget == "")

# **HOW MANY WERE LET GO OF IS SAID EVERY NIGHT**, or a night that forgot six
# hundred reads the same as a night that forgot none.
check("what was kept and what was let go of is said in one line",
      tidied.says() == "1 files still remembered as read, 2 let go of")
check("and a night that let go of nothing says so too",
      "0 let go of" in kept.says())

# An id remembered for a file that was never in the folder is let go of -- there
# is nothing there for it to protect.
check("an id for a file that is not in the folder at all is let go of",
      answered(lambda: tool.still_worth_remembering(FOLDER, ["id-9"])).forgotten == ("id-9",))
check("a folder holding something that is not a file is refused here too",
      refused_by(lambda: tool.still_worth_remembering(["id-1"], [])))
check("and blanks in what was remembered are dropped rather than kept for ever",
      answered(lambda: tool.still_worth_remembering(FOLDER, ["", "  ", "id-1"])).keep == ("id-1",))
# **FOUND BY PUTTING THE FAULT BACK, 2026-09-02.** Keeping the blanks left the
# line above green, because a blank is not in the folder either so the
# intersection dropped it anyway. It came out as something LET GO OF instead --
# a run log reporting that it forgot two files that never existed.
check("and blanks are not reported as files that were let go of either",
      answered(lambda: tool.still_worth_remembering(FOLDER, ["", "  ", "id-1"])).forgotten == ())

# **END TO END: HE TIDIES DRIVE AND THE TIDIED FILES ARE NOT READ AGAIN.**
# The cap must not become the very re-read it exists to prevent.
after_tidy = answered(lambda: tool.still_worth_remembering([f("id-3")], ["id-1", "id-2", "id-3"]))
next_night = answered(lambda: tool.what_is_new([f("id-3")], after_tidy.keep))
check("THE NIGHT AFTER A TIDY, WHAT IS LEFT IN THE FOLDER IS NOT READ AGAIN",
      next_night.anything_to_do is False)
# And if he ever puts one back, it is a file in the folder that nothing has read.
check("and a tidied file put back IS read again, which is right -- nothing remembers it",
      [one.which for one in answered(
          lambda: tool.what_is_new([f("id-3"), f("id-1")], after_tidy.keep)).new] == ["id-1"])

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 63
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print(f"all {ran} checks passed")
