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
check("what it does import is only shapes and the one refusal kind",
      sorted(IMPORTS) == ["from dataclasses import dataclass",
                          "from table import CannotRead",
                          "from typing import Dict, Iterable, List, Optional, Sequence, Tuple"])

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
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 42
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print(f"all {ran} checks passed")
