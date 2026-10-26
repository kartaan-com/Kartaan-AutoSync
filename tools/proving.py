"""AutoSync's own proving setup: the ERP's prover, pointed at this repository (AP11, plan part B).

**THE PROVER ITSELF IS THE ERP'S AND IS NOT COPIED.** `tools/prove_checks.py` in Kartaan-ERP breaks the code on purpose,
one change at a time, and requires the checks named for each file to go red. A copy here would drift from it the day
either changed, so this file loads it from the ERP checkout named by `KARTAAN` and changes only what is AutoSync's:

  - WHERE the code is (`ROOT`) and where this repository's survivor list lives (`tools/proven_survivors.json`);
  - WHICH files are sources and which checks are named for each (`sources`, `COVERED_BY`, `NOT_PROVEN`) -- this
    repository's layout, not the ERP's: `autosync/*.py` and `tools/*.py` beside `<name>_checks.py`, `extension/*.js`
    and `test/*.js` beside `<name>.test.js`, and a `*_checks.py` with no source of its own is checks, never a source;
  - **A CHANGE OF LINE ENDINGS ONLY IS NOT A CHANGE TO PROVE** (`_diff_args`). On 23 Oct the ERP's prover run on
    77705cd --against 49d8deb tried every line of walk.js, screen.js, background.js, drive.js and xls.py, because
    those files changed from one line ending to the other between the two commits, and reported 1485 survivors --
    most of them lines nobody touched. `--ignore-cr-at-eol` asks git for the lines that really changed.

Run (from a clone with Unix line endings, which the checks expect):

    git clone -c core.autocrlf=false -c core.eol=lf <this repository> <scratch folder>
    KARTAAN=D:/Kartaan-ERP python tools/proving.py --against <last release's commit>

Everything after loading -- the changes tried, the verdicts, the survivor and crash rules -- is the ERP prover's own.
"""

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
# **A NAME OF ITS OWN IN `sys.modules`.** The prover's workers are new processes; each loads this file again as the
# main module before it is handed a change, and finds the ERP's prover under this name, set up the same way.
NAME = "kartaan_erp_prove_checks"
# Every name of the ERP's prover this file replaces or calls. **A NAME THE ERP RENAMES MUST STOP THIS IN WORDS** (AP11 review): assigning over
# a name the module no longer has adds an attribute nothing reads, and the run would quietly measure the ERP's own files its own way.
THE_ERPS_NAMES = ("ROOT", "SURVIVORS_FILE", "COVERED_BY", "NOT_PROVEN", "sources", "_diff_args", "_try_one", "baseline_passes", "stage",
                  "runner_for", "away_from_the_real_repository", "TIMEOUT_SECONDS", "main")


def the_erps_prover(where: Path = None):
    """The ERP's prover module, loaded from its own file. Stops in words when `KARTAAN` is not set or does not lead to it."""
    if where is None:
        named = os.environ.get("KARTAAN", "").strip()
        if not named:
            # **NOT SET IS NOT "HERE"** (AP11 review): an empty KARTAAN read as the current folder would load whatever
            # tools/prove_checks.py sits there -- an old ERP worktree's, say -- the very drift this file exists to stop.
            raise SystemExit("proving: KARTAAN is not set. Set it to the Kartaan-ERP checkout (KARTAAN=D:/Kartaan-ERP).")
        where = Path(named) / "tools" / "prove_checks.py"
    if not where.is_file():
        raise SystemExit(
            f"proving: the ERP's prover is not at {where}. Set KARTAAN to the Kartaan-ERP checkout "
            "(KARTAAN=D:/Kartaan-ERP); AutoSync proves with the ERP's tool rather than a copy that could drift.")
    if NAME in sys.modules:
        return sys.modules[NAME]
    spec = importlib.util.spec_from_file_location(NAME, where)
    module = importlib.util.module_from_spec(spec)
    sys.modules[NAME] = module
    spec.loader.exec_module(module)
    return module


# Where the sibling rule does not apply, each with the checks that DO drive the file by name.
COVERED_BY = {
    # The Meesho and Flipkart ad files' readers; their checks are the month summary's and the database writes', which call
    # `ads.read_*` by name on rows in his files' shapes.
    "autosync/ads.py": "autosync/returns_ads_checks.py",
    # The returns readers: the same checks file reads return files through `returns.read_*` by name.
    "autosync/returns.py": "autosync/returns_ads_checks.py",
    # The shared record helpers (a figure, a digest, a record kind): every record reader leans on them; the record table's
    # checks drive each kind through them.
    "autosync/records.py": "autosync/record_reports_checks.py",
    # The two files the page loads before anything else, to catch a download the moment it is made; both are driven by
    # the background's checks, which load them by name.
    "extension/catch-blob.js": "extension/background.test.js",
    "extension/catch-early.js": "extension/background.test.js",
}

# Source files nothing can prove here. Each is a written admission, not an exemption.
NOT_PROVEN = {
    "autosync/fake_firestore.py":
        "The stand-in database every database check is driven against. Break it on purpose and the answer is not one red "
        "line but some other file going red for a reason of its own. WHAT HOLDS IT: it answers batchGet, runQuery and "
        "commit only, and says so in its header; a rule about what is refused or allowed drifting into it would belong in "
        "the code and this entry would stop being true.",
    "autosync/start.py":
        "The file the workflow runs: it reads the seller's secrets and opens the real connections, and decides nothing "
        "(its own header). What it does can only be seen on a real run against real accounts, which a proving run "
        "cannot make. Every rule it hands work to lives in nightly.py, which is proved.",
    "extension/content.js":
        "The script Chrome puts into each portal page to pass messages between the page and the extension. It can only "
        "run inside a real Chrome tab; the stand-in Chrome has no page for it to be put into.",
    "extension/panel.js":
        "The side panel's start-up wiring: it finds the panel's elements and hands them to screen.js, which is proved by "
        "screen.test.js. What is left here is visible only by opening the panel in Chrome.",
    "extension/worker.js":
        "The service worker's start-up line: it loads background.js, which is proved by background.test.js, and does "
        "nothing else. Only Chrome starts it.",
    "test/fake-browser.js":
        "The stand-in page every page check is driven against. Breaking it makes some other file go red for a reason "
        "that has nothing to do with that file. WHAT HOLDS IT: every way it differs from a real browser is written in "
        "its header.",
    "test/fake-chrome.js":
        "The stand-in Chrome every extension check is driven against. Same as the stand-in page: breaking it turns some "
        "other checks file red, not one named for it. WHAT HOLDS IT: its header lists what it does not do that Chrome "
        "does.",
}


def sources():
    """Every source file of this repository, and the checks named for it (None when there are none)."""
    out = {}
    for path in sorted((HERE / "extension").glob("*.js")) + sorted((HERE / "test").glob("*.js")):
        rel = path.relative_to(HERE).as_posix()
        if rel.endswith(".test.js"):
            continue
        sibling = path.with_name(path.stem + ".test.js")
        out[rel] = COVERED_BY.get(rel) or (sibling.relative_to(HERE).as_posix() if sibling.exists() else None)
    for path in sorted((HERE / "autosync").glob("*.py")) + sorted((HERE / "tools").glob("*.py")):
        rel = path.relative_to(HERE).as_posix()
        # **EVERY `_checks.py` HERE IS CHECKS**, including the ones that check several modules at once (a81, ads_month,
        # returns_ads, the_look). This file is `proving.py` rather than the ERP's `prove_checks.py` for that reason: the
        # commit gate runs every `_checks.py` as checks, and this measurement would have dropped it as one.
        if rel.endswith("_checks.py"):
            continue
        sibling = path.with_name(path.stem + "_checks.py")
        out[rel] = COVERED_BY.get(rel) or (sibling.relative_to(HERE).as_posix() if sibling.exists() else None)
    return out


def _diff_args(against):
    """The ERP's two git questions, asked with line endings ignored (see the header)."""
    if against:
        return (["diff", "-U0", "--ignore-cr-at-eol", against, "--"],
                ["diff", "--name-only", "--ignore-cr-at-eol", against, "--"])
    return (["diff", "--cached", "-U0", "--ignore-cr-at-eol", "HEAD", "--"],
            ["diff", "--cached", "--name-only", "--ignore-cr-at-eol", "HEAD", "--"])


def also_proved_by(relpath: str):
    """The OTHER checks files that import this Python module by name, besides the one named for it.

    **WHY: THE ERP'S PROVER RUNS ONLY THE CHECKS NAMED FOR A FILE, AND HERE A MODULE IS OFTEN CHECKED FROM ITS CALLERS.** The ledger's
    rules for claims and payments are checked in claims_checks.py and payments_checks.py (A90 had to join them by hand), so on 23 Oct
    every one of those lines read as a survivor. Read off the imports rather than written out, so a new checks file counts the day it
    is added and a list cannot fall behind.
    """
    path = HERE / relpath
    if path.suffix != ".py":
        return ()
    named = sources().get(relpath)
    pattern = re.compile(rf"^\s*(?:import\s+{re.escape(path.stem)}\b|from\s+{re.escape(path.stem)}\s+import\b)", re.M)
    return tuple(
        one.relative_to(HERE).as_posix()
        for one in sorted(path.parent.glob("*_checks.py"))
        if one.relative_to(HERE).as_posix() != named and pattern.search(one.read_text(encoding="utf-8"))
    )


def _try_one(job):
    """The ERP prover's own try first; a change that survives the file's own checks is then put to every other checks file importing it.

    Caught by any of them is caught. A crash in one of them is not a check going red, so it does not turn a survivor into a catch.
    """
    prover = sys.modules[NAME]
    first = prover._the_erps_try_one(job)
    if first["verdict"] != "survived":
        return first
    relpath, _checks, original, mutated, ident, line_number = job
    others = also_proved_by(relpath)
    if not others:
        return first
    prover.stage(prover._TREE, relpath, mutated)
    try:
        for checks in others:
            try:
                finished = subprocess.run(
                    prover.runner_for(checks) + [str(prover._TREE / checks)], capture_output=True, timeout=prover.TIMEOUT_SECONDS,
                    cwd=str(prover._TREE), env=prover.away_from_the_real_repository(),
                )
            except subprocess.TimeoutExpired:
                return {"id": ident, "verdict": "caught", "timed_out": True, "line_number": line_number}
            if a_check_went_red(finished.returncode, (finished.stdout or b"") + (finished.stderr or b"")):
                return {"id": ident, "verdict": "caught", "timed_out": False, "line_number": line_number}
    finally:
        prover.stage(prover._TREE, relpath, original)
    return first


def a_check_went_red(returncode: int, said: bytes) -> bool:
    """Caught means the run failed AND a check said FAIL -- the ERP prover's own rule. A run that failed with no FAIL line fell over; it caught nothing."""
    return returncode != 0 and re.search(rb"^FAIL", said, re.M) is not None


def set_up(prover):
    """Point the ERP's prover at this repository. Answers the same module, changed. Stops in words if the ERP's prover lacks a name this replaces or calls."""
    missing = [name for name in THE_ERPS_NAMES if not hasattr(prover, name)]
    if missing:
        raise SystemExit(f"proving: the ERP's prover no longer has {', '.join(missing)}, which this file replaces or calls. "
                         "tools/proving.py must be brought up to date with it before anything is proved.")
    prover.ROOT = HERE
    prover.SURVIVORS_FILE = HERE / "tools" / "proven_survivors.json"
    prover.COVERED_BY = COVERED_BY
    prover.NOT_PROVEN = NOT_PROVEN
    prover.sources = sources
    prover._diff_args = _diff_args
    if not hasattr(prover, "_the_erps_try_one"):
        prover._the_erps_try_one = prover._try_one
        prover._try_one = _try_one
        the_erps_baseline = prover.baseline_passes

        # **THE OTHER CHECKS FILES MUST PASS WITH NOTHING CHANGED TOO**, or every change put to one failing for its own reason would read as caught.
        def baseline_passes(source_root, checks_files):
            named = set(checks_files)
            others = {one for rel, checks in sources().items() if checks in named for one in also_proved_by(rel)}
            return the_erps_baseline(source_root, sorted(named | others))

        prover.baseline_passes = baseline_passes
    return prover


if __name__ == "__main__" or __name__ == "__mp_main__":
    PROVER = set_up(the_erps_prover())

if __name__ == "__main__":
    sys.exit(PROVER.main())
