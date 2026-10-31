"""Point group-1 at a version the moment GitHub publishes its release (AJ9 piece 5, D426).

Run ONLY by `.github/workflows/move-group-1.yml`, which runs ONLY on `release: published`
in the kartaan-com organisation. It moves `group-1` and nothing else: group-2 and group-3
wait for clean nights, which only the Server can count (see docs/RELEASING-GROUPS.md).

It uses the same refusals as `move_group.py` (a published release only, never a burnt
tag, never backwards), so a release that must not be followed turns the job red and
nothing moves. A group that already points at the tag is a success, not a failure.

    TAG=v0.1.26 GH_TOKEN=... python tools/move_group_on_release.py
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import move_group as mg  # noqa: E402

GROUP = "group-1"


def decide(tag, facts):
    """('skip', why) when nothing is to be done, ('refuse', why) when it must not move, ('move', command)."""
    wrong = mg.refusals(GROUP, tag, facts)
    if len(wrong) == 1 and "nothing to do" in wrong[0]:
        return "skip", wrong[0]
    if wrong:
        return "refuse", "; ".join(wrong)
    return "move", mg.commands(GROUP, tag, facts)[0]


def main(env, run=subprocess.run, gather=mg.gather):
    tag = env.get("TAG", "")
    verdict, what = decide(tag, gather())
    if verdict == "skip":
        print(f"Nothing to do: {what}")
        return 0
    if verdict == "refuse":
        print(f"REFUSED, {GROUP} NOT moved: {what}")
        return 1
    # `what` is the one `gh api ...` command the shared tool builds from GitHub's own facts; run as words, no shell.
    done = run(what.split(), capture_output=True, text=True, check=False)
    if done.returncode:
        print(f"{GROUP} could not be moved to {tag}: {done.stderr.strip()[:300]}")
        return 1
    print(f"{GROUP} now points at {tag}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(os.environ))
