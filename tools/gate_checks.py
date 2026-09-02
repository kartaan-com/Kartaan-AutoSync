"""Checks for the gate.

**A GATE COPIED IS NOT A GATE PROVED.** Every rule in `tools/gate.py` is checked
here, and the rules were then broken on purpose one at a time to watch a named
check go red -- because the ERP's own gate carried the Golden Rule 24 fault
INSIDE the gate written to prevent it, and it was found by review, not by running.

**THE ONE THAT MATTERS MOST:** `NOT_CODE` is written down THREE TIMES -- here in
Python, in `.githooks/commit-msg` as shell, and in `.github/workflows/pm_check.yml`
as shell. Three copies of one fact. The day they disagree, one of them lets a
commit past that another would have stopped, and nothing would say so. **All
three are read off disk and compared.**

Run: python tools/gate_checks.py
"""

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate as tool  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

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
    """True when that raises `Refused`, and nothing else."""
    try:
        work()
    except tool.Refused:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


# ------------------------------------------ the three copies of one fact

HOOK = (ROOT / ".githooks" / "commit-msg").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "pm_check.yml").read_text(encoding="utf-8")
PRE_COMMIT = (ROOT / ".githooks" / "pre-commit").read_text(encoding="utf-8")


def _not_code_in(text):
    """The NOT_CODE pattern as that file writes it, or None."""
    found = re.search(r"NOT_CODE='([^']+)'", text)
    return found.group(1) if found else None


check("the commit-msg hook writes NOT_CODE down", _not_code_in(HOOK) is not None)
check("and so does the workflow", _not_code_in(WORKFLOW) is not None)
check("THE THREE COPIES OF NOT_CODE ARE IDENTICAL",
      _not_code_in(HOOK) == _not_code_in(WORKFLOW) == tool.NOT_CODE.pattern)
if not (_not_code_in(HOOK) == _not_code_in(WORKFLOW) == tool.NOT_CODE.pattern):
    print(f"      gate.py:    {tool.NOT_CODE.pattern}")
    print(f"      commit-msg: {_not_code_in(HOOK)}")
    print(f"      workflow:   {_not_code_in(WORKFLOW)}")
    print("      One of them is letting a commit through that another would stop.")

# ---------------------------------------------- what counts as code

check("a python file is code", tool.code_among(["autosync/ledger.py"]) == ["autosync/ledger.py"])
check("a javascript file is code", tool.code_among(["extension/walk.js"]) == ["extension/walk.js"])
check("a workflow is code", tool.code_among([".github/workflows/autosync.yml"]))
check("A GIT HOOK IS CODE -- it has no extension, and an allowlist leaked twice on that",
      tool.code_among([".githooks/pre-commit"]) == [".githooks/pre-commit"])
check("the work register is code, because the gate reads it",
      tool.code_among(["tools/work.json"]) == ["tools/work.json"])
check("the README is not code", tool.code_among(["README.md"]) == [])
check("nor is .gitignore", tool.code_among([".gitignore"]) == [])
check("nor the review record or its template",
      tool.code_among(["review_pass.json", "review_pass.template.json"]) == [])
check("A FILE TYPE NOBODY HAS THOUGHT OF IS CODE BY DEFAULT",
      tool.code_among(["autosync/something.rs", "Makefile", "deploy.sh"])
      == ["autosync/something.rs", "Makefile", "deploy.sh"])

# --------------------------------------------------- a credential

for what, line in (
    ("a github token", "TOKEN = 'ghp_" + "a" * 36 + "'"),
    ("a github fine-grained token", "T = 'github_pat_" + "b" * 40 + "'"),
    ("a google access token", "t = 'ya29." + "c" * 40 + "'"),
    ("a google api key", "k = 'AIzaSy" + "d" * 33 + "'"),
    ("an amazon lwa client id", "i = 'amzn1.application-oa2-client." + "e" * 32 + "'"),
    ("an amazon refresh token", "r = 'Atzr|" + "f" * 30 + "'"),
    ("a slack token", "s = 'xox" + "b-1234567890-abcdefghij'"),
    ("a private key", "-----BEGIN RSA PRIVATE" + " KEY-----"),
    ("a service account file", '  "private_' + 'key": "-----BEGIN"'),
    ("a client secret", '  "client_' + 'secret": "abcdefghijkl"'),
    ("an aws key", "AWS = 'AKIA" + "A" * 16 + "'"),
    ("a discord webhook", "url = 'https://discord.com/api/web" + "hooks/123/abc'"),
):
    check(f"a credential is refused: {what}",
          tool.why_a_credential_is_refused([line]) is not None)

check("ordinary code is not refused",
      tool.why_a_credential_is_refused(["def read(content):", "    return content"]) is None)
check("and the word 'secret' on its own is not a credential",
      tool.why_a_credential_is_refused(["# the secret goes in GitHub Actions Secrets"]) is None)
check("THIS FILE'S OWN PATTERNS DO NOT MATCH THEIR OWN SOURCE",
      tool.why_a_credential_is_refused(
          Path(tool.__file__).read_text(encoding="utf-8").splitlines()) is None)
# **THIS CHECK WAS TOO CRUDE AND THE GATE CAUGHT WHAT IT MISSED.** It filtered
# by how a line began, which the three offending example lines did not share --
# so it passed while three of them matched their own patterns, and the gate
# refused the very commit that introduced itself. It now asks the real question
# of every line, exactly as the gate does.
check("NO LINE OF THIS CHECKS FILE MATCHES ITS OWN PATTERNS",
      tool.why_a_credential_is_refused(
          Path(__file__).read_text(encoding="utf-8").splitlines()) is None)

# ----------------------------------------------------- the register

GOOD = {"items": [{"id": "a", "files": ["tools/gate.py"], "findings": []}]}
check("a register naming a real file, owned once, is fine",
      [w for w in tool.why_the_register_is_refused(GOOD) if "gate.py" in w] == [])
check("a register with no pieces at all is refused",
      tool.why_the_register_is_refused({"items": []}))
check("a file owned by two pieces is refused",
      any("owned by both" in w for w in tool.why_the_register_is_refused(
          {"items": [{"id": "a", "files": ["tools/gate.py"]},
                     {"id": "b", "files": ["tools/gate.py"]}]})))
check("a file the register names that is not there is refused",
      any("no such file" in w for w in tool.why_the_register_is_refused(
          {"items": [{"id": "a", "files": ["autosync/imaginary.py"]}]})))
check("A FILE THAT EXISTS AND NOBODY OWNS IS REFUSED",
      any("no piece of work owns it" in w for w in tool.why_the_register_is_refused(GOOD)))
check("and the javascript is swept too, which the Server had none of",
      any(w.startswith("extension/") for w in tool.why_the_register_is_refused(GOOD)))
check("a finding marked fixed that names no check is refused",
      any("names no check" in w for w in tool.why_the_register_is_refused(
          {"items": [{"id": "a", "files": [], "findings": [{"fixed": True, "proved_by": ""}]}]})))
check("a finding marked fixed that DOES name one is fine",
      not any("names no check" in w for w in tool.why_the_register_is_refused(
          {"items": [{"id": "a", "files": [],
                      "findings": [{"fixed": True, "proved_by": "x_checks.py"}]}]})))
check("THE REAL REGISTER IN THIS REPOSITORY MATCHES WHAT IS ON DISK",
      tool.why_the_register_is_refused(tool.the_register()) == [])

# ------------------------------------------------- the review record

FULL = {
    "written_by": "the session that built the ledger",
    "reviewer": "a second session",
    "independent": True,
    "read": ["autosync/ledger.py"],
    "checked_against_decision_log": True,
    "found": ["the row numbers in a plan go stale if anything appends first"],
    "security": "nothing is sent anywhere; the transport is handed in",
}
TOUCHED = ["autosync/ledger.py"]
check("a full record is accepted", tool.why_the_review_is_refused(FULL, TOUCHED) == [])
check("NO RECORD AT ALL IS REFUSED", tool.why_the_review_is_refused(None, TOUCHED))


def without(field, value=None):
    one = dict(FULL)
    if value is None:
        one.pop(field, None)
    else:
        one[field] = value
    return tool.why_the_review_is_refused(one, TOUCHED)


check("a record naming no author is refused", any("written_by" in w for w in without("written_by")))
check("a record naming no reviewer is refused", any("reviewer" in w for w in without("reviewer")))
check("A REVIEW BY THE AUTHOR IS REFUSED",
      any("not a review" in w for w in tool.why_the_review_is_refused(
          {**FULL, "reviewer": FULL["written_by"]}, TOUCHED)))
check("and it is refused however the case is written",
      any("not a review" in w for w in tool.why_the_review_is_refused(
          {**FULL, "reviewer": FULL["written_by"].upper()}, TOUCHED)))
check("a non-independent review with no reason is refused",
      any("if_not_independent_why" in w for w in without("independent", False)))
check("a non-independent review that SAYS WHY is accepted -- recorded, not refused",
      tool.why_the_review_is_refused(
          {**FULL, "independent": False,
           "if_not_independent_why": "one session alone on this machine, so it leaned on "
                                     "putting faults back and watching named checks go red"},
          TOUCHED) == [])
check("a record that did not read the decision log is refused",
      any("decision_log" in w for w in without("checked_against_decision_log", False)))
check("A RECORD THAT LEAVES OUT A CHANGED FILE IS REFUSED",
      any("did not open a changed file" in w for w in tool.why_the_review_is_refused(
          FULL, ["autosync/ledger.py", "autosync/sales.py"])))
check("windows backslashes in the record still match the paths git gives",
      tool.why_the_review_is_refused(
          {**FULL, "read": ["autosync\\ledger.py"]}, TOUCHED) == [])
check("an empty findings list is refused", any("found is empty" in w for w in without("found", [])))
for shrug in ("fine", "OK", "looks good", "passed", "no issues", "  none  ", "lgtm"):
    check(f"a finding of {shrug!r} is refused as a result, not a finding",
          any("results, not findings" in w
              for w in tool.why_the_review_is_refused({**FULL, "found": [shrug]}, TOUCHED)))
check("a real finding is accepted",
      tool.why_the_review_is_refused(
          {**FULL, "found": ["a blank was overwriting a real settlement"]}, TOUCHED) == [])
check("SECURITY SAYING NOTHING IS REFUSED", any("security" in w for w in without("security", "")))
check("and a shrug there is refused too", any("security" in w for w in without("security", "fine")))
check("the security refusal says WHY this repository's lens is what it is",
      any("EVERY SELLER'S OWN GITHUB ACCOUNT" in w for w in without("security", "")))

# -------------------------------------------------- every checks file

FOUND = tool.every_checks_file()
check("the checks files are FOUND, not listed", len(FOUND) > 30)
check("the python ones are found", any(f.name == "ledger_checks.py" for f in FOUND))
check("THE JAVASCRIPT ONES ARE FOUND TOO -- 400 checks the Server had none of",
      any(f.name == "walk.test.js" for f in FOUND))
check("the gate's own checks are among them -- a gate that skips itself is not a gate",
      any(f.name == "gate_checks.py" for f in FOUND))
check("every checks file on disk is one the gate would run",
      {p.name for p in ROOT.glob("autosync/*_checks.py")}
      | {p.name for p in ROOT.glob("tools/*_checks.py")}
      | {p.name for p in ROOT.glob("extension/*.test.js")}
      == {f.name for f in FOUND})
check("a javascript file is run with node, never with python",
      tool.how_to_run(Path("extension/walk.test.js"))[0] == "node")
check("and a python file with this very python",
      tool.how_to_run(Path("autosync/x_checks.py"))[0] == sys.executable)
check("a runner that is not on the machine is a failure, not a quiet skip",
      tool.run_one(ROOT / "autosync" / "nothing_here.py") is not None)

# ------------------------------------------------------ the hooks

check("the pre-commit hook exists and is not where the rules live",
      "tools/gate.py" in PRE_COMMIT and len(PRE_COMMIT.splitlines()) < 40)
check("it refuses when git cannot say where the repository is",
      "BLOCKED" in PRE_COMMIT and "exit 1" in PRE_COMMIT)
check("THE TAG IS ADDED IN commit-msg, because pre-commit structurally cannot",
      "[PM-REVIEWED]" in HOOK and "[PM-REVIEWED]" not in PRE_COMMIT)
check("the review record is consumed, so one record covers one commit",
      "rm -f review_pass.json" in HOOK)
check("the commit-msg hook refuses a code commit with no record",
      "BLOCKED" in HOOK)
check("the record is never tracked -- it is a per-commit working file",
      "review_pass.json" in (ROOT / ".gitignore").read_text(encoding="utf-8"))

# -------------------------------------------------- the workflow

check("there is a workflow, which is the half --no-verify cannot skip",
      "[PM-REVIEWED]" in WORKFLOW)
check("it re-runs every checks file rather than trusting the local hook",
      "_checks.py" in WORKFLOW and ".test.js" in WORKFLOW)
check("it installs node, or the javascript checks would silently not run",
      "setup-node" in WORKFLOW)
check("it scans the pushed diff for credentials",
      "a credential appears in the pushed diff" in WORKFLOW)
check("it refuses a tracked review record",
      "review_pass.json is committed" in WORKFLOW)
check("it checks the gate is actually IN the repository",
      "is not tracked" in WORKFLOW)
check("it fetches the other two repositories, because four checks are pinned to them",
      "Kartaan-ERP" in WORKFLOW and "Kartaan-Server" in WORKFLOW)
check("IT RUNS ONLY IN KARTAAN'S OWN ORGANISATION, never in a seller's account",
      "github.repository_owner == 'kartaan-com'" in WORKFLOW)
check("and it says why, because that is a decision and not a condition",
      "EVERY SELLER'S OWN GITHUB ACCOUNT" in WORKFLOW)
check("it uses the empty tree as the sentinel for a first push",
      "hash-object -t tree /dev/null" in WORKFLOW)
check("it expands merge commits, or a merge shows an empty file list",
      "git show -m" in WORKFLOW)
check("it refuses when the history has been rewritten under it",
      "The history was rewritten" in WORKFLOW)
check("it checks the generated recipes are not stale",
      "export_recipes.py --check" in WORKFLOW)

# **THE COMMIT THE RULE STARTS AT.** Written as a placeholder until the gate's
# own commit exists -- and this check is what stops that being forgotten, which
# would leave the workflow refusing every push with "not an ancestor of HEAD".
BORN = re.search(r"GATE_BORN=(\S+)", WORKFLOW)
check("the workflow names the commit the rule starts at", BORN is not None)
if BORN and BORN.group(1) == "__GATE_BORN__":
    print("      NOT YET SET: it is still the placeholder. It must become the gate's")
    print("      own commit id, once that commit exists. Until then the workflow")
    print("      would refuse every push.")
check("and it is a real commit id, not the placeholder left behind",
      BORN is not None and re.fullmatch(r"[0-9a-f]{40}", BORN.group(1)) is not None)

# -------------------------------------------------------- git refuses

check("a git question that cannot be answered is a refusal, never an empty answer",
      refused_by(lambda: tool._git("rev-parse", "--verify", "definitely-not-a-ref")))

print()
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 91
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print(f"all {ran} checks passed")
