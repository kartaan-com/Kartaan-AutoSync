"""Checks for tools/move_group.py -- by CALLING it with made-up facts (A88, D426).

The tool decides one thing: may group-N be pointed at tag vX.Y.Z. Every question
below hands it a world (which tags exist, which have a published release, where
each group points now) and asks whether it refuses or prints the push commands.
It must never run anything that writes to GitHub: it only prints.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import move_group as mg  # noqa: E402

ran = 0
failures = []


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


def world(**over):
    base = dict(
        tags={"v0.1.0": "a0", "v0.1.19": "a19", "v0.1.20": "a20", "v0.1.21": "a21"},
        releases={"v0.1.19": "published", "v0.1.20": "published", "v0.1.21": "draft",
                  "v0.1.0": "published"},
        groups={"group-1": "v0.1.19", "group-2": "v0.1.19", "group-3": "v0.1.19"},
        branches={"v0.1.20": "a20"})
    base.update(over)
    return mg.Facts(**base)


def says(group, tag, facts=None, rollback=False):
    return mg.refusals(group, tag, facts or world(), rollback)


def answered(work):
    """What the work gives, or None when it throws -- so a throw turns one check red by name instead of stopping the file (AP11)."""
    try:
        return work()
    except Exception:  # noqa: BLE001
        return None


check("a released tag may be given to group-1", says("group-1", "v0.1.20") == [])
for bad in ("group-4", "group-0", "group-", "group-1.0", "main", "stable", "", "Group-1", "group-11"):
    check(f"group name {bad!r} is refused", says(bad, "v0.1.20") != [])
for bad in ("main", "group-1", "v0.1", "v0.1.20.1", "0.1.20", "v0.1.x", "", "v0.1.20-rc1", "v0.1.20 "):
    check(f"target {bad!r} is refused as not a whole version tag", says("group-1", bad) != [])
check("a tag that does not exist is refused", says("group-1", "v0.1.99") != [])
check("a tag with no published release is refused", says("group-1", "v0.1.18", world(tags={**world().tags, "v0.1.18": "a18"})) != [])
check("a draft release is refused", says("group-1", "v0.1.21") != [])
check("a prerelease is refused", says("group-1", "v0.1.21", world(releases={**world().releases, "v0.1.21": "prerelease"})) != [])
check("a name that is only a branch, not a tag, is refused",
      says("group-1", "v0.1.22", world(releases={**world().releases, "v0.1.22": "published"},
                                       branches={"v0.1.22": "b22"})) != [])
check("v0.1.0 is burnt and refused even though it is released", says("group-1", "v0.1.0") != [])
check("moving a group backwards is refused without --rollback",
      says("group-1", "v0.1.19", world(groups={"group-1": "v0.1.20", "group-2": "v0.1.19", "group-3": "v0.1.19"})) != [])
check("and allowed with --rollback",
      says("group-1", "v0.1.19", world(groups={"group-1": "v0.1.20", "group-2": "v0.1.19", "group-3": "v0.1.19"}), True) == [])
check("pointing a group at the tag it already has is refused (nothing to do)", says("group-1", "v0.1.19") != [])
check("group-2 may not run ahead of group-1", says("group-2", "v0.1.20") != [])
check("group-3 may not run ahead of group-2",
      says("group-3", "v0.1.20", world(groups={"group-1": "v0.1.20", "group-2": "v0.1.19", "group-3": "v0.1.19"})) != [])
check("group-2 may follow group-1",
      says("group-2", "v0.1.20", world(groups={"group-1": "v0.1.20", "group-2": "v0.1.19", "group-3": "v0.1.19"})) == [])
check("a group that does not exist yet may be created at a released tag",
      says("group-1", "v0.1.20", world(groups={"group-1": None, "group-2": None, "group-3": None})) == [])

AT20 = dict(groups={"group-1": "v0.1.20", "group-2": "v0.1.19", "group-3": "v0.1.19"})
live = world(branches={"v0.1.20": "a20", "group-1": "a19", "group-2": "a19", "group-3": "a19"})
cmds = mg.commands("group-1", "v0.1.20", live)
check("it prints one command that moves the group to the commit GitHub reported for the tag",
      len(cmds) == 1 and "-X PATCH" in cmds[0] and "git/refs/heads/group-1" in cmds[0] and "sha=a20" in cmds[0])
check("a group that does not exist yet is created, not patched",
      "-X POST" in mg.commands("group-1", "v0.1.20", world())[0] and "ref=refs/heads/group-1" in mg.commands("group-1", "v0.1.20", world())[0])
back = mg.commands("group-1", "v0.1.19", world(branches={"group-1": "a20"}, **AT20))
check("a rollback names the older tag's commit", "sha=a19" in back[0])
check("the printed command names the public repository", "kartaan-com/Kartaan-AutoSync" in cmds[0])
check("--rollback never lets a group jump FORWARD past the order rule",
      says("group-3", "v0.1.20", world(), True) != [])
check("--rollback to a tag that is not older is refused", says("group-1", "v0.1.20", world(), True) != [])
check("a version tag with non-English digits is refused", says("group-1", "v١.1.20") != [])
check("the tool says out loud that it ran nothing", "ran nothing" in mg.farewell().lower())

import re
SRC = (Path(__file__).resolve().parent / "move_group.py").read_text(encoding="utf-8")
check("the tool's own code never calls a git or gh command that writes",
      SRC != "" and not re.search(r"""["'](push|tag|branch|create|edit|delete|api|-f|--force)["']""", SRC))

# ---- gather(): what it makes of GitHub's own answers (git ls-remote, gh release list) ----
LS = "\n".join([
    "aaa1\trefs/tags/v0.1.19", "bbb2\trefs/tags/v0.1.20", "ccc3\trefs/tags/v0.1.20^{}",
    "ccc3\trefs/heads/group-1", "aaa1\trefs/heads/group-2", "ddd4\trefs/heads/main",
    "ccc3\trefs/heads/v0.1.20-fix"])
RL = json.dumps([{"tagName": "v0.1.19", "isDraft": False, "isPrerelease": False},
                 {"tagName": "v0.1.20", "isDraft": False, "isPrerelease": False},
                 {"tagName": "v0.1.21", "isDraft": True, "isPrerelease": False},
                 {"tagName": "v0.1.22", "isDraft": False, "isPrerelease": True}])
_real_read = mg._read
mg._read = lambda *args: LS if args[0] == "git" else RL
try:
    got = mg.gather()
finally:
    mg._read = _real_read
check("an annotated tag is read as the commit it points at, not the tag object", got.tags["v0.1.20"] == "ccc3")
check("a plain tag is read as itself", got.tags["v0.1.19"] == "aaa1")
check("a group is named by the tag at its commit", got.groups["group-1"] == "v0.1.20" and got.groups["group-2"] == "v0.1.19")
check("a group that does not exist has no tag", got.groups["group-3"] is None and "group-3" not in got.branches)
check("branches are listed", got.branches["main"] == "ddd4" and "group-1" in got.branches)
check("releases are read as published, draft or prerelease",
      got.releases == {"v0.1.19": "published", "v0.1.20": "published", "v0.1.21": "draft", "v0.1.22": "prerelease"})
check("a branch whose name looks like a tag is not counted as a tag", "v0.1.20-fix" not in got.tags)
check("and only tags are tags: no branch is ever read as one", sorted(got.tags) == ["v0.1.19", "v0.1.20"])

# ---- each refusal alone (AP11, from the proving run): no rule may lean on another one to look right
FRESH = dict(groups={"group-1": None, "group-2": None, "group-3": None})
check("THE BURNT TAG IS REFUSED FOR BEING BURNT, even for a group that does not exist yet and even with --rollback",
      all("burnt" in " ".join(answered(lambda: says("group-1", "v0.1.0", world(**FRESH), back)) or []) for back in (False, True)))
odd = world(tags={**world().tags, "v0.1.20-rc1": "rc"}, releases={**world().releases, "v0.1.20-rc1": "published"})
check("a tag GitHub really has, published, that is not a whole version is refused as one, never weighed as a version",
      "whole version" in " ".join(answered(lambda: says("group-1", "v0.1.20-rc1", odd)) or []))
check("asked with no word about rolling back, a move backwards is refused",
      "--rollback" in " ".join(answered(lambda: mg.refusals("group-1", "v0.1.19", world(**AT20))) or []))

# ---- reading GitHub: the one place a command is run, and it only reads
import contextlib  # noqa: E402
import io  # noqa: E402


class Done:
    def __init__(self, code, out="", err=""):
        self.returncode, self.stdout, self.stderr = code, out, err


def read_with(done):
    """`_read` with GitHub's answer made up: (what it handed back, or the words it stopped with)."""
    real = getattr(mg, "subprocess", None)
    fake = type("FakeSubprocess", (), {"run": staticmethod(lambda args, **kw: (ASKED_WITH.update(kw), done)[1])})
    try:
        mg.subprocess = fake
        return answered(lambda: mg._read("git", "ls-remote")), ""
    except SystemExit as said:
        return None, str(said)
    finally:
        mg.subprocess = real


import subprocess  # noqa: E402
check("when nothing is made up, the tool reads GitHub through the real subprocess module", getattr(mg, "subprocess", None) is subprocess)
ASKED_WITH = {}
read_ok, _ = read_with(Done(0, "answer"))
check("GitHub is asked with its answer kept, as text, and a refusal left for the tool to say rather than thrown",
      ASKED_WITH == {"capture_output": True, "text": True, "check": False})
_, read_bad = read_with(Done(128, "", "not found"))
check("what GitHub answers is handed back as it came", read_ok == "answer")
check("a read GitHub refuses stops the tool in words, naming the command and what GitHub said",
      "could not read from GitHub" in read_bad and "git ls-remote" in read_bad and "not found" in read_bad)


def run_main(argv, facts):
    real = mg.gather
    mg.gather = lambda: facts
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            code = answered(lambda: mg.main(argv))
    finally:
        mg.gather = real
    return code, out.getvalue()


code, said = run_main(["--check"], world(groups={"group-1": "v0.1.19", "group-2": None, "group-3": None}, branches={"group-2": "zz"}))
check("--check says where each group points, a group off any released tag, and a group not made yet",
      code == 0 and "group-1: v0.1.19" in said and "group-2: NOT AT A RELEASED TAG" in said and "group-3: does not exist yet" in said)
code, said = run_main([], world())
check("asked wrongly it prints how to ask and answers 2", code == 2 and "prints, never pushes" in said)
code, said = run_main(["group-1", "v0.1.99"], world())
check("a refused move answers 1 and says REFUSED with the reason", code == 1 and "REFUSED" in said and "v0.1.99" in said)
code, said = run_main(["group-1", "v0.1.20"], world())
check("an allowed move answers 0, prints the command, and says it ran nothing",
      code == 0 and "OK. To point group-1 at v0.1.20" in said and "gh api" in said and "ran nothing" in said)
code, said = run_main(["group-1", "v0.1.19", "--rollback"], world(**AT20))
check("--rollback reaches the rule, wherever it is written", code == 0 and "sha=a19" in said)

EXPECTED = 48 + 13
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
