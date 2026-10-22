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
back = mg.commands("group-1", "v0.1.19", world(branches={"group-1": "a20"}, **AT20), True)
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

EXPECTED = 48
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
