"""Checks for tools/proving.py -- AutoSync's proving setup over the ERP's prover (AP11, plan part B).

What is AutoSync's here is asked of it directly: which files are sources, which checks are named for each, which are
written down as unproven, and that a change of line endings alone is not a change to prove. The prover itself is the
ERP's and is held by the ERP's own checks. Nothing here needs the ERP checkout.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import proving as pc  # noqa: E402

ran = 0
failures = []


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


found = pc.sources()
check("every source with no checks of its own is written down as unproven, with a reason, or covered by named checks",
      all(checks is not None or rel in pc.NOT_PROVEN for rel, checks in found.items()))
check("nothing written down as unproven has checks named for it -- two records of one fact, disagreeing",
      not [rel for rel in pc.NOT_PROVEN if found.get(rel)])
check("every unproven entry is a file that is there, so the list cannot become a record of what used to be",
      all(rel in found for rel in pc.NOT_PROVEN))
check("every reason is a reason, not a word",
      all(len(why.strip()) >= 80 for why in pc.NOT_PROVEN.values()))
check("every checks file named in COVERED_BY is there, and covers a file that is there",
      all((pc.HERE / checks).is_file() and rel in found for rel, checks in pc.COVERED_BY.items()))
check("a checks file is never a source, including those that check several modules at once",
      not [rel for rel in found if rel.endswith("_checks.py") or rel.endswith(".test.js")]
      and "tools/proving_checks.py" not in found
      and "autosync/a81_checks.py" not in found and "tools/the_look_checks.py" not in found)
check("the extension, the stand-ins, the reading package and the tools are all measured",
      {"extension/walk.js", "test/fake-chrome.js", "autosync/listings.py", "tools/gate.py"} <= set(found))
check("a file with a sibling is proved by that sibling, this one included",
      found.get("autosync/listings.py") == "autosync/listings_checks.py" and found.get("extension/walk.js") == "extension/walk.test.js"
      and found.get("tools/proving.py") == "tools/proving_checks.py")
check("A CHANGE TO THE LEDGER IS ALSO PUT TO THE CHECKS THAT DRIVE IT FROM ITS CALLERS (claims, payments), never only to its own",
      {"autosync/claims_checks.py", "autosync/payments_checks.py"} <= set(pc.also_proved_by("autosync/ledger.py"))
      and "autosync/ledger_checks.py" not in pc.also_proved_by("autosync/ledger.py"))
check("and a module no other checks file imports has none, a page script none",
      pc.also_proved_by("tools/move_group.py") == () and pc.also_proved_by("extension/walk.js") == ())


def away_from_the_real_repository():
    """The environment with every pointer git hands down taken out.

    **RUN FROM THE COMMIT HOOK, GIT HANDS DOWN `GIT_DIR` AND `GIT_INDEX_FILE` FOR THE REAL REPOSITORY, AND THEY BEAT `cwd`.** On 26 Oct the
    first version of this file ran `git init` from the hook and set `bare = true` on the real AutoSync repository (put back by hand) -- the
    exact fault the ERP's prover writes up in `away_from_the_real_repository`. The same list as there.
    """
    without = dict(os.environ)
    for pointer in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR",
                    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX", "GIT_NAMESPACE"):
        without.pop(pointer, None)
    return without


def a_repository_with_a_line_ending_change():
    """A two-commit repository: one file whose line endings changed, one with one line really changed."""
    where = Path(tempfile.mkdtemp(prefix="prove-checks-checks-"))
    env = away_from_the_real_repository()
    git = lambda *a: subprocess.run(["git", "-c", "core.autocrlf=false", *a], cwd=where, capture_output=True, text=True, env=env)
    git("init", "-q")
    (where / "endings.py").write_bytes(b"a = 1\r\nb = 2\r\n")
    (where / "real.py").write_bytes(b"a = 1\nb = 2\n")
    git("add", "-A")
    git("-c", "user.name=x", "-c", "user.email=x@x", "commit", "-qm", "one")
    (where / "endings.py").write_bytes(b"a = 1\nb = 2\n")
    (where / "real.py").write_bytes(b"a = 1\nb = 3\n")
    git("add", "-A")
    git("-c", "user.name=x", "-c", "user.email=x@x", "commit", "-qm", "two")
    return where, git


where, git = a_repository_with_a_line_ending_change()
hunks, _ = pc._diff_args("HEAD~1")
endings = git(*hunks, "endings.py").stdout
real = git(*hunks, "real.py").stdout
check("A FILE WHOSE LINE ENDINGS ALONE CHANGED HAS NO LINE TO PROVE (77705cd: 1485 survivors, most of them untouched lines)",
      "@@" not in endings)
check("and a line that really changed is still asked about", "+b = 3" in real)
check("the staged question ignores line endings too", "--ignore-cr-at-eol" in pc._diff_args(None)[0])
try:
    pc.the_erps_prover(where / "no-such-prover.py")
    stopped = ""
except SystemExit as said:
    stopped = str(said)
check("a missing ERP checkout stops in words naming KARTAAN, never a copy of the prover", "KARTAAN" in stopped)

EXPECTED = 14
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
