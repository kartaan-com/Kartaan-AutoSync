"""Checks for the door onto the OTHER repository.

**IT HAD NONE, AND THAT IS WHY BOTH ITS REFUSALS WERE BROKEN.** This file's whole
job is to say, in words a person can act on, that a fact written down in two
repositories could not be pinned. Both of those sentences named a variable that
does not exist anywhere -- so a reader got a `NameError` where the explanation
should have been, and nobody found out because no check had ever taken either
path. **An error path nobody has ever run is the most common shape in this
project.**

**AND THE FOLDER NAME IS ASKED, NOT SEARCHED FOR.** D148 renamed the ERP's folder
to `Kartaan-ERP`, and four sentences here went on telling a reader to set the old
one. The question below is not *"does the old word appear"* -- it is **"does every
folder this file TELLS somebody to set name the folder it actually looks in?"**
(D169, D170). Searching for a phrase is the mistake D169 names against itself.

Run: python autosync/the_other_half_checks.py
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import the_other_half as tool  # noqa: E402

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


def raised(work):
    """Whatever came out of it, or None if nothing did.

    **IT CATCHES `BaseException`, ON PURPOSE.** `SystemExit` is not an `Exception`,
    so catching only `Exception` here would let the very thing being checked walk
    straight out and end the run -- which is D175's own *a run that did not finish
    counts nothing*.
    """
    try:
        work()
    except BaseException as wrong:  # noqa: BLE001 - this is the thing under test
        return wrong
    return None


# **WHAT THE ENVIRONMENT SAYS IS PUT BACK.** These two variables are how somebody
# points the checks at their own checkouts. A checks file that left them changed
# would break every checks file that runs after it (D178: the tool that breaks
# things on purpose must never leave damage).
WAS = {name: os.environ.get(name) for name in ("KARTAAN", "SERVER")}


def say_where(name, value):
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


# ------------------------------------------ which folder it really looks in

# **ASKED OF THE CODE, NEVER TYPED HERE.** Typing `Kartaan-ERP` into this file
# would make it one more hand-written copy of the same name, and the check would
# then agree with itself rather than with the door.
say_where("KARTAAN", None)
say_where("SERVER", None)
THE_ERP = answered(lambda: tool.whereKartaanIs().name)
THE_SERVER = answered(lambda: tool.whereTheServerIs().name)

check("the folder the ERP is looked for in can be asked of the code", bool(THE_ERP))
check("and the server's can be too", bool(THE_SERVER))
check("they are two different folders, which is what D148 split", THE_ERP != THE_SERVER)

# --------------------------------------- the refusal is words, never a crash

NOWHERE = str(Path(__file__).resolve().parent / "no-such-folder-at-all")


def refusal_from(which, *parts):
    """What comes out when the other repository is not where it was looked for."""
    say_where(which, NOWHERE)
    try:
        if which == "KARTAAN":
            return raised(lambda: tool.readFromKartaan(*parts))
        return raised(lambda: tool.readFromServer(*parts))
    finally:
        say_where(which, WAS[which])


KARTAAN_REFUSAL = refusal_from("KARTAAN", "src", "shared", "data", "sync.js")
SERVER_REFUSAL = refusal_from("SERVER", "server", "going_off.py")

# **THE NAMED QUESTION FOR THE FAULT (D175).** Put `wanted` back and the f-string
# raises `NameError` while the refusal is still being built, so the sentence a
# reader was meant to see never exists. These two are what go red for it.
check("a missing ERP folder is REFUSED IN WORDS, not crashed on",
      isinstance(KARTAAN_REFUSAL, SystemExit))
check("a missing server folder is REFUSED IN WORDS, not crashed on",
      isinstance(SERVER_REFUSAL, SystemExit))

KARTAAN_SAID = str(KARTAAN_REFUSAL.code) if isinstance(KARTAAN_REFUSAL, SystemExit) else ""
SERVER_SAID = str(SERVER_REFUSAL.code) if isinstance(SERVER_REFUSAL, SystemExit) else ""

check("and the ERP refusal says it could not check, and which file it wanted",
      "CANNOT CHECK THIS" in KARTAAN_SAID and "sync.js" in KARTAAN_SAID)
check("and the server refusal says it could not check, and which file it wanted",
      "CANNOT CHECK THIS" in SERVER_SAID and "going_off.py" in SERVER_SAID)
check("and the ERP refusal names the folder it actually looked in",
      NOWHERE in KARTAAN_SAID)
check("and the server refusal names the folder it actually looked in",
      NOWHERE in SERVER_SAID)

# ------------------------------------ every folder it TELLS somebody to set

SAYS = re.compile(r"(KARTAAN|SERVER)=(\S+)")


def folders_named(text):
    """The folder each `KARTAAN=` or `SERVER=` instruction in this text points at.

    **THE LAST SEGMENT, whichever slash the sentence used.** A Windows path and a
    home-folder path are the same instruction written for two machines.
    """
    out = []
    for which, value in SAYS.findall(text or ""):
        plain = value.strip().rstrip(".,").replace(chr(92), "/")
        out.append((which, plain.rstrip("/").split("/")[-1]))
    return out


def all_name(named, which, folder):
    """Does every instruction of this kind name this folder -- and is there one?"""
    mine = [name for kind, name in named if kind == which]
    # **BOTH DIRECTIONS (D190).** Without the first half an empty list passes:
    # delete every instruction and the check goes on saying they are all right.
    return bool(mine) and all(name == folder for name in mine)


check("the module says how to point it at the ERP, and names the folder it looks in",
      all_name(folders_named(tool.__doc__), "KARTAAN", THE_ERP))
check("the ERP refusal says how to point it there, and names that same folder",
      all_name(folders_named(KARTAAN_SAID), "KARTAAN", THE_ERP))
check("the server refusal says how to point it there, and names the server folder",
      all_name(folders_named(SERVER_SAID), "SERVER", THE_SERVER))

# **THE SENTENCE IS ASKED WHAT IT CLAIMS.** It promises that a sibling folder is
# tried when nothing is set, and `whereKartaanIs` is what actually tries one.
SIBLING = re.findall(r"sibling folder called `([^`]+)`", tool.__doc__ or "")
check("the sentence about a sibling folder names the folder that is really tried",
      SIBLING == [THE_ERP])

# ------------------------------------------- and the old name is still gone

# **THE ONE LINE `firestore_door_checks.py` HAS, ASKED RATHER THAN SEARCHED.**
# The rename is done (D148); a fallback nobody writes down is how two spellings
# of one thing survive for a year.
say_where("KARTAAN", None)
check("with nothing set, one folder is tried and only one",
      answered(lambda: tool.whereKartaanIs().name) == THE_ERP)

for _name, _value in WAS.items():
    say_where(_name, _value)

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 15
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
