"""Checks for tools/move_group_on_release.py and its workflow (AJ9 piece 5).

The job moves group-1 on a published release and nothing else. Each question hands it a made-up world
and a made-up `gh` runner, so nothing is read from or written to GitHub.
"""
import contextlib
import io
import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import move_group as mg  # noqa: E402
import move_group_on_release as mo  # noqa: E402

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
        releases={"v0.1.19": "published", "v0.1.20": "published", "v0.1.21": "prerelease", "v0.1.0": "published"},
        groups={"group-1": "v0.1.19", "group-2": "v0.1.19", "group-3": "v0.1.19"},
        branches={"group-1": "a19"})
    base.update(over)
    return mg.Facts(**base)


class Done:
    def __init__(self, code=0, err=""):
        self.returncode, self.stderr = code, err


def go(tag, facts, code=0, err=""):
    ran_cmds = []

    def run(cmd, **kw):
        ran_cmds.append((cmd, kw))
        return Done(code, err)
    return mo.main({"TAG": tag}, run=run, gather=lambda: facts), ran_cmds


code, cmds = go("v0.1.20", world())
check("a published release moves group-1 with one gh api call on the commit GitHub holds for the tag",
      code == 0 and len(cmds) == 1 and cmds[0][0][:3] == ["gh", "api", "-X"] and "sha=a20" in cmds[0][0]
      and "heads/group-1" in " ".join(cmds[0][0]))
check("the call is run as words with no shell", cmds[0][1].get("shell") in (None, False))
code, cmds = go("v0.1.21", world())
check("a release that is only a pre-release is refused and nothing is run", code == 1 and cmds == [])
code, cmds = go("v0.1.0", world())
check("the burnt v0.1.0 is refused and nothing is run", code == 1 and cmds == [])
code, cmds = go("v0.1.18", world(tags={"v0.1.18": "a18"}, releases={"v0.1.18": "published"}))
check("an older release is refused (a rollback is never automatic)", code == 1 and cmds == [])
code, cmds = go("v0.1.19", world())
check("group-1 already at the tag is a success and runs nothing", code == 0 and cmds == [])
code, cmds = go("v0.1.20; rm -rf /", world())
check("a tag name that is not a whole version is refused and nothing is run", code == 1 and cmds == [])
code, cmds = go("", world())
check("no tag at all is refused", code == 1 and cmds == [])
code, cmds = go("v0.1.20", world(), code=1, err="Rulesets forbid")
check("GitHub refusing the push (bypass not given yet) turns the job red", code == 1)
code, cmds = go("v0.1.20", world(groups={"group-1": None, "group-2": None, "group-3": None}, branches={}))
check("group-1 not created yet is created, and never group-2 or group-3",
      code == 0 and "POST" in cmds[0][0] and "ref=refs/heads/group-1" in cmds[0][0]
      and not any("group-2" in c or "group-3" in c for c in cmds[0][0]))

YML = (HERE.parent / ".github" / "workflows" / "move-group-1.yml").read_text(encoding="utf-8")
on_block = YML.split("jobs:")[0]
check("the workflow runs on release published and on nothing else",
      "release:" in on_block and "types: [published]" in on_block
      and not any(w in on_block.split("on:", 1)[1] for w in ("push:", "pull_request", "schedule:", "workflow_dispatch", "workflow_call")))
check("it asks only for contents write", "permissions:\n  contents: write" in YML and YML.count("write") == 1)
check("it runs only in kartaan-com", "github.repository_owner == 'kartaan-com'" in YML)
check("the tag reaches the script through the environment, never pasted into the command",
      "TAG: ${{ github.event.release.tag_name }}" in YML and "run: python3 tools/move_group_on_release.py" in YML)

check("two releases published together queue behind each other rather than racing",
      "concurrency:\n  group: move-group-1\n  cancel-in-progress: false" in YML)
check("the checkout leaves no write token in the working copy", "persist-credentials: false" in YML)



def said(tag, facts, code=0, err=""):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        back, cmds = go(tag, facts, code, err)
    return back, cmds, out.getvalue()


_, cmds, words = said("v0.1.20", world())
check("the gh call asks for its output back as text and does not throw on a refusal",
      cmds[0][1] == {"capture_output": True, "text": True, "check": False})
check("a move says where group-1 now points", words.strip() == "group-1 now points at v0.1.20.")
_, _, words = said("v0.1.19", world())
check("nothing to do says so, with the reason", words.startswith("Nothing to do: ") and len(words.strip()) > 15)
_, _, words = said("v0.1.21", world())
check("a refusal says group-1 was NOT moved, with the reason",
      words.startswith("REFUSED, group-1 NOT moved: ") and len(words.strip()) > 28)
_, _, words = said("v0.1.20", world(), code=1, err="  Rulesets forbid  ")
check("GitHub's own refusal is passed on, trimmed",
      words.strip() == "group-1 could not be moved to v0.1.20: Rulesets forbid")

# Run as the workflow runs it (`python3 tools/move_group_on_release.py`), GitHub's facts made up: group-1 already there.
real_gather, mg.gather = mg.gather, lambda: world()
real_tag = os.environ.get("TAG")
os.environ["TAG"] = "v0.1.19"
try:
    with contextlib.redirect_stdout(io.StringIO()):
        runpy.run_path(str(HERE / "move_group_on_release.py"), run_name="__main__")
    exit_code = None
except SystemExit as stop:
    exit_code = stop.code
except Exception as e:  # noqa: BLE001 -- a broken script is what this check is for
    exit_code = f"threw {type(e).__name__}"
finally:
    mg.gather = real_gather
    if real_tag is None:
        del os.environ["TAG"]
    else:
        os.environ["TAG"] = real_tag
check("run as a script, it reads TAG from the environment and exits with main's answer", exit_code == 0)

EXPECTED = 22
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
