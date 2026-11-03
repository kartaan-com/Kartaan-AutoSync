"""Checks for tools/proving.py -- AutoSync's proving setup over the ERP's prover (AP11, plan part B).

What is AutoSync's here is asked of it directly: which files are sources, which checks are named for each, which are
written down as unproven, and that a change of line endings alone is not a change to prove. The prover itself is the
ERP's and is held by the ERP's own checks. Nothing here needs the ERP checkout.
"""
import hashlib
import os
import shutil
import stat
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
      pc.also_proved_by("tools/dry_run.py") == () and pc.also_proved_by("extension/walk.js") == ())


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
    # **AND GIT MAY NOT CLIMB OUT OF THE FOLDER** (AP11 review): if `git init` here ever failed, the commands after it would find whatever
    # repository sits above the temp folder.
    env["GIT_CEILING_DIRECTORIES"] = str(where.parent)
    git = lambda *a: subprocess.run(["git", "-c", "core.autocrlf=false", *a], cwd=where, capture_output=True, text=True, env=env)
    if git("init", "-q").returncode != 0:
        raise SystemExit(f"proving_checks: git init failed in {where}; nothing else was run there.")
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


def stops_with(work):
    try:
        work()
        return ""
    except SystemExit as said:
        return str(said)


_kartaan = os.environ.pop("KARTAAN", None)
try:
    check("KARTAAN not set stops in words, never read as this folder (an old worktree's prover could sit here)",
          "KARTAAN is not set" in stops_with(lambda: pc.the_erps_prover()))
finally:
    if _kartaan is not None:
        os.environ["KARTAAN"] = _kartaan
an_older_prover = type(sys)("an_older_prover")
for _name in pc.THE_ERPS_NAMES:
    setattr(an_older_prover, _name, None)
del an_older_prover._diff_args
check("an ERP prover that has renamed a name this file replaces stops it in words naming the name, before anything is measured",
      "_diff_args" in stops_with(lambda: pc.set_up(an_older_prover)) and an_older_prover.ROOT is None)
check("A CHECKS FILE THAT FELL OVER (failed with no FAIL line) CATCHES NOTHING; only a failed run with a FAIL line is caught",
      pc.a_check_went_red(1, b"PASS  a\nFAIL  b\n") and not pc.a_check_went_red(1, b"Traceback (most recent call last):\n")
      and not pc.a_check_went_red(0, b"FAIL  printed but passed\n") and not pc.a_check_went_red(1, b"PASS  FAIL in the middle\n"))

# The scratch repository is taken away again, read-only object files included (git marks them so on Windows; the ERP prover's `scrub`).
shutil.rmtree(where, onerror=lambda remove, name, _: (os.chmod(name, stat.S_IWRITE), remove(name)))
check("and the scratch repository is gone again", not where.exists())

# --part i/N: one share of the changed lines (PV1), so N machines try the same changes between them.
check("--part 2/4 is taken out of the arguments and the rest are left for the ERP's prover",
      pc.the_part_asked_for(["--against", "abc", "--part", "2/4", "--workers", "1"]) == ((2, 4), ["--against", "abc", "--workers", "1"])
      and pc.the_part_asked_for(["--part=3/3"]) == ((3, 3), []) and pc.the_part_asked_for(["--changed"]) == (None, ["--changed"]))
check("a share that is not i/N with 1 <= i <= N stops in words",
      all("--part wants i/N" in stops_with(lambda given=given: pc.the_part_asked_for(["--part", given]))
          for given in ("0/4", "5/4", "x", "2", "2/0", "")))
_erp = type(sys)("erp"), sys.modules.get(pc.NAME)
_erp[0]._the_erps_changed_lines = lambda relpath, against: None if relpath == "gone.py" else set(range(1, 13))
sys.modules[pc.NAME] = _erp[0]
try:
    shares = []
    for _one in (1, 2, 3, 4):
        pc.PART = (_one, 4)
        shares.append(pc._changed_lines("a.py", "x"))
    pc.PART = None
    whole = pc._changed_lines("a.py", "x")
    pc.PART = (1, 4)
    unknown = pc._changed_lines("gone.py", "x")
finally:
    pc.PART = None
    if _erp[1] is None:
        del sys.modules[pc.NAME]
    else:
        sys.modules[pc.NAME] = _erp[1]
check("the shares together are every changed line exactly once, no line in two, and none empty for a change this size",
      sorted(n for one in shares for n in one) == sorted(whole) == list(range(1, 13)) and all(len(one) == 3 for one in shares))
check("no share asked for is the whole run, and git failing to answer is still 'could not ask' (None), never an empty share",
      whole == set(range(1, 13)) and unknown is None)

# The code to prove can be named (PROVING_CODE), and the ERP's prover held here as a copy is the file whose hash is written down (PV1).
named = subprocess.run([sys.executable, "-c", "import proving; print(proving.HERE)"], capture_output=True, text=True, cwd=str(Path(__file__).resolve().parent),
                       env={**os.environ, "PROVING_CODE": str(Path(tempfile.gettempdir()))}).stdout.strip()
check("PROVING_CODE names the code to prove; unset, it is this checkout", named == str(Path(tempfile.gettempdir()).resolve()) and pc.HERE == Path(__file__).resolve().parent.parent)
_copy = pc.HERE / "vendor" / "kartaan-erp"
_body = (_copy / "tools" / "prove_checks.py").read_bytes().split(b"\n", 1)
check("THE ERP PROVER COPY HAS ITS RECORDED HASH, and a first line naming the ERP file as its source",
      hashlib.sha256(_body[1]).hexdigest() == (_copy / "PROVER-SHA256.txt").read_text().strip() and b"Kartaan-ERP/tools/prove_checks.py" in _body[0])
_erp = os.environ.get("KARTAAN", "").strip()
if _erp:
    check("and it is the ERP's own file, line endings aside (KARTAAN is set, so the two can be compared)",
          (Path(_erp) / "tools" / "prove_checks.py").read_bytes().replace(b"\r\n", b"\n") == _body[1])

EXPECTED = 14 + 4 + 4 + 2 + (1 if _erp else 0)
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
