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
import os
import io
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate as tool  # noqa: E402
import gate_run  # noqa: E402

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

# ------------------------- WHY THERE IS NO TREE TEST IN THIS REPOSITORY'S HOOK
#
# **THE HOOK'S OWN COMMENT SAID THERE WAS ONE, AND THERE IS NOT.** It was copied
# from the ERP with the paragraph around it, and it claimed a guard that is not
# built here -- found by an independent reviewer on 2026-09-02, inside the change
# whose whole purpose was to stop this gate claiming things it does not do. The
# comment is corrected; this is the check that holds the correction, so the same
# sentence cannot drift back in with nothing to contradict it.
#
# WHAT IS TRUE HERE: a commit with nothing staged never reaches the tag hook at
# all, because this refuses it first. D163's free path -- a rewrite whose tree is
# identical goes through and keeps its tag -- is built in the ERP and NOT here.
_was_asked = tool.staged_files
_nothing_staged = None
try:
    tool.staged_files = lambda: []
    tool.main()
except Exception as wrong:  # noqa: BLE001
    _nothing_staged = wrong
finally:
    tool.staged_files = _was_asked

check(
    "A COMMIT WITH NOTHING STAGED IS REFUSED HERE, BEFORE THE TAG HOOK EVER RUNS -- which is "
    "why this repository needs no SAME-TREE REWRITE test of its own and why its hook may not "
    "say it has one. D163's free path is the ERP's; here a message-only rewrite is refused "
    "outright. **NOT `write-tree` IN GENERAL:** D173's merge fix added one to both hooks on "
    "2026-09-03, to ask whether the note pre-commit left is about this commit. Naming the "
    "narrower thing is the point -- the sentence that said `no tree test` was true when it "
    "was written and false a day later",
    isinstance(_nothing_staged, tool.Refused)
    and "nothing is staged" in str(_nothing_staged),
)


# ------------------------------------------- THE TAG HOOK, DRIVEN RATHER THAN READ
#
# **EVERY CHECK ABOVE ABOUT THE HOOKS READS THEM AS TEXT.** Text checks hold a
# spelling steady; they cannot say whether the thing refuses. A hole sat behind
# them until 2026-09-02: the review tag was grepped for ANYWHERE in the message,
# so a commit whose prose merely MENTIONED it was judged already tagged -- and
# the hook printed that it had added one regardless. The ERP's commit logging
# D156 landed untagged that way, and pm_check.yml read the same substring the
# same way, so the layer D156 calls unskippable was passable too.
#
# **THIS GATE WAS COPIED FROM THAT ONE AND CARRIED THE FAULT.** That is D156's
# own warning in its last paragraph. So these run the real hook file.

# **GIT'S OWN POINTERS TAKEN OUT OF THE ENVIRONMENT.** Git hands the location of
# the repository it was called from to every hook it runs, and a child inherits
# it -- so `git init` and `git add` below would be aimed at the REAL repository
# whatever their working directory says. Not a theory: on 2026-08-31 that staged
# a temporary copy as the whole of the real repository and wiped the index (264
# files marked deleted), and re-initialising left `bare = true` behind, which
# `git reset` cannot undo. Either GIT_DIR or GIT_INDEX_FILE alone is enough.
#
# **ONE LIST, NOT TWO.** The check below seeds exactly these names and asks that
# none survive -- written out a second time, deleting a name from BOTH would take
# the pointer out of the stripping and out of the checking together, and the check
# would go green with the hole open. That is the shape the tag check next door was
# built with a count to avoid, and this one was written with it. Reviewer, cycle 51.
POINTERS = (
    "GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY",
    "GIT_COMMON_DIR", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_PREFIX",
    "GIT_NAMESPACE",
)


def _no_pointers_to_here():
    without = dict(os.environ)
    for pointer in POINTERS:
        without.pop(pointer, None)
    return without


# **AND THE STRIPPING IS CHECKED, not left to be discovered by the damage.**
# Take one name out of POINTERS and every check below still passes on an ordinary
# run; the first symptom under a real hook is the real repository being
# re-initialised. There is no second chance to notice it.
_seeded = {name: "somewhere-else" for name in POINTERS}
_was_env = {name: os.environ.get(name) for name in POINTERS}
try:
    os.environ.update(_seeded)
    _stripped = _no_pointers_to_here()
finally:
    for name, before in _was_env.items():
        if before is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = before
check(
    "EVERY POINTER GIT HANDS DOWN IS TAKEN OUT before any of that runs -- with even one "
    "left in, `git init` below is aimed at the REAL repository whatever its working "
    "directory says, which on 2026-08-31 wiped the index and left `bare = true` behind",
    len(POINTERS) == 8
    and not any(name in _stripped for name in POINTERS)
    and "PATH" in _stripped,
)


def _in(where, *argv, feed=None):
    return subprocess.run(
        list(argv), cwd=str(where), env=_no_pointers_to_here(), input=feed,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

THE_ROOT = ROOT
TEMP_PREFIX = "kartaan-tag-checks-"
SOURCE_FILE = "a.py"
# **THE EMPTY-STAGED REFUSAL IS NOT CHECKED HERE**, because this repository does
# not have that fault: `tools/gate.py` raises Refused("nothing is staged") on an
# empty list, so an amend is blocked already. The ERP's pre-commit exited 0
# instead, and that is where the check for it lives.
EXTRA_DRIVEN = ()

# **WHAT THE DRIVEN CHECKS ARE CALLED, IN ONE PLACE.** Named up here because they
# have to be reportable when there is no bash to run them with: a checks file that
# raises at its top level stops there and everything below it silently never runs.
# That is the trap already on this project's board, and the first draft of this
# block walked straight into it.
DRIVEN = (
    "A MESSAGE THAT ONLY MENTIONS THE REVIEW TAG IN A SENTENCE IS NOT TAGGED BY IT -- "
    "the hook puts the tag on a line of its own, rather than reading its own name in "
    "somebody's prose and appending nothing",

    "AND UNDER `git commit -v` THE TAG REACHES THE COMMIT, not merely the file -- the "
    "diff goes into that same file below a scissors line and git throws everything from "
    "it down away, so a tag appended at the end was announced and then dropped. ASKED OF "
    "A REAL COMMIT: the whole bug was a tag that was in the file and not in the commit",

    "AND A MESSAGE THAT MERELY LOOKS LIKE IT HAS A CUT LINE IS NOT TREATED AS ONE -- git "
    "cuts only at its comment marker, one space and EXACTLY 24 dashes either side of >8. "
    "**ASKED BY WHERE THE TAG LANDS.** Asked only that nothing was deleted, this could not "
    "fail: nothing is ever deleted now, so the pattern loosened to match six dashes left "
    "every check green -- measured 2026-09-02 by an independent reviewer, who put that "
    "fault back and watched 449 pass. Left alone, the tag goes at the END, below the "
    "author's last word; mistaken for a cut line it goes ABOVE. Position is the difference",

    "AND UNDER A COMMENT CHARACTER THAT IS NOT `#` TOO -- `core.commentChar` and "
    "`core.commentString` are ordinary settings, git builds its cut line from whichever "
    "is set, and a hook that recognises only `#` puts the tag below the cut and loses it "
    "exactly as before. Asked of a real commit made with core.commentChar=';'",

    "AND IT NEVER ANNOUNCES A TAG IT COULD NOT WRITE -- a hook that says it tagged a "
    "commit it did not is Golden Rule 24 itself, and it is what this hook exists to "
    "prevent. Asked for the hook's OWN refusal, because any failure to start it at all "
    "would otherwise satisfy this",

    "AND A MESSAGE HOLDING A **REAL** CUT LINE KEEPS EVERY WORD BELOW IT -- the check "
    "above feeds six dashes, which is a line git keeps and this hook never cuts at, so "
    "it tests the case where nothing happens. Nothing anywhere used a line git actually "
    "cuts at, and the worst fault this hook has ever had -- deleting the author's own "
    "paragraphs -- went straight back in with every check still green. Twenty-four "
    "dashes, `>8`, twenty-four dashes, in the default configuration with no -v",

    "AND UNDER A COMMENT MARKER LONGER THAN ONE CHARACTER -- `core.commentString` takes "
    "a string, not a character, and with it set to `REM` the pattern anchored to a "
    "single character missed git's cut line, the tag went below it, git threw it away "
    "and the hook reported success. The check next door only ever tried the "
    "one-character kind, so it agreed. Asked of a real commit made with "
    "core.commentString=REM",

    "AND A GIT THAT CANNOT SAY WHAT IS STAGED IS A REFUSAL, NOT AN EMPTY ANSWER -- read as "
    "empty it means `no code, nothing to tag` a few lines down, so the commit lands "
    "untagged and the hook prints nothing at all. This refusal was asked for by a reviewer "
    "and then went in with NOTHING CHECKING IT: deleted, all 449 / 109 / 107 checks stayed "
    "green in all three repositories, measured 2026-09-02. Driven against a REALLY damaged "
    "index -- the case the hook names -- and asked for the hook's OWN words, because bash "
    "failing to start would otherwise satisfy `it did not exit 0`",
)

# ------------------------------------------------- D173: A MERGE IS A COMMIT
#
# **MEASURED WITH REAL HOOKS, NOT REASONED ABOUT.** On a merge that goes through
# cleanly git does NOT run `pre-commit` and DOES run `commit-msg` -- so the half
# that demands a review record is skipped while the half that stamps the tag is
# not. **The inversion is the whole finding:** with no record about, the merge
# lands untagged and CI refuses it, loudly and safely; with a record lying about,
# `commit-msg` consumes it, writes the tag, and the merge reaches GitHub WEARING
# it while nothing recorded that anybody read it. Two untagged merges are already
# on the ERP's master.
#
# **AND THESE ASK WHETHER ANYTHING DEMANDED A READ, NOT WHETHER THE TAG LANDED.**
# The tag is the surface, and in exactly the broken case the surface is green
# (D170, D173).
LEFT_BEHIND = (
    "THE THROWAWAY CLONE IS REALLY TAKEN AWAY, AND THIS SAYS SO WHEN IT IS NOT -- "
    "`ignore_errors=True` left TWENTY-EIGHT of them in the temporary folder, because git writes "
    "its objects read-only and a read-only file refuses to be deleted. It does not try harder; "
    "it stops asking. **A tool that breaks things on purpose and cannot clean up after itself "
    "is not the one to trust with a throwaway clone** (D178)",
)

MERGING = (
    "A CLEAN MERGE IS REFUSED WHILE A REVIEW RECORD IS LYING ABOUT -- D173's dangerous "
    "case, driven end to end with the real hook. Before this, the record was consumed "
    "here and the tag written onto a merge nobody had read, and the merge landed",

    "AND THE RECORD IS STILL THERE AFTERWARDS -- a refusal that used the record up would "
    "leave the next commit with nothing to show, and this merge was never made",

    "AND THE SAME MERGE WITH NO RECORD AT ALL IS REFUSED TOO -- and HERE that was already "
    "true before D173: this hook refuses a code commit with no record whatever kind of "
    "commit it is, which the ERP's does not. **Measured rather than assumed:** with the "
    "merge guard taken back out, the three checks around this one go red and this one does "
    "not. It is kept because it says which half of D173 was ever open here -- the loud one "
    "never was, and the stale record was the whole hole",

    "AND A NOTE NAMING SOME OTHER TREE IS NOT THIS COMMIT'S NOTE -- a note saying only "
    "that something ran once is a stale record of exactly the kind D173 is about, and a "
    "commit abandoned between the two hooks leaves one behind",

    "AND THE ROUTE D173 PRESCRIBES GOES THROUGH -- the merge held back with `--no-commit` "
    "and then committed ordinarily: two parents, the tag written, and the review record "
    "and the note both used up. A gate with no way through is a gate that gets switched "
    "off, which is D163's lesson costing a full review",

    "AND AN ORDINARY COMMIT IS UNTOUCHED BY ANY OF IT -- nothing is asked where no merge "
    "is in progress, because `pre-commit` always runs there. Measured on all five paths, "
    "amend included",

    "AND `pre-commit` LEAVES THE NOTE, NAMING THE TREE IT APPROVED -- the other half of "
    "the same fact, driven against the real hook rather than read out of it",

    "AND LEAVES NONE WHEN IT REFUSES -- a note left by a hook that refused would say the "
    "opposite of what happened, and the next merge would consume it",

    "AND A NOTE PLANTED BY HAND IS NOT ENOUGH ON ITS OWN -- held back with `--no-commit`, "
    "the tree taken, the merge aborted, the note written by hand and the merge made again: "
    "**no tag is written unless a review record is there too.** What this does NOT claim "
    "is that the note cannot be forged. It can, it is measured, and `.githooks/commit-msg` "
    "says so plainly: nothing a hook writes is unforgeable by somebody who can write files, "
    "and the same person can skip both hooks and type the tag by hand in fewer steps. This "
    "pins the half that IS true",
)


_BASH = shutil.which("bash")
# **NO BASH MEANS THESE CHECKS DID NOT RUN**, and a check that silently does not
# run is the failure this whole file is about. Every one of them is reported red
# instead, and the count below stays the same either way.
check("the hooks can actually be run, so the checks below mean something",
      _BASH is not None)

# **AND GIT RECORDS THEM EXECUTABLE.** Read out of the INDEX, never off disk:
# `core.filemode` is false on Windows, so the working-tree bit there is a
# fiction git neither stores nor restores, and the mode in the index is the only
# thing a clone on any other machine actually receives.
#
# **WHAT A MISSING BIT DOES IS WORSE THAN A RED RUN.** Installed the way this
# repository installs itself -- `core.hooksPath=.githooks` -- git SKIPS a hook
# that is not executable, prints a hint, and exits 0: the commit lands untagged
# with nothing having asked for a review, which is precisely the gate being off.
# Measured 2026-09-07 on Linux, both modes, against this very hook. Both hooks
# stood at 100644 from the day this repository was split out, so the gate had
# never once run on Linux or macOS, and eight of the driven checks below had
# been red on the runner since 2026-09-05.
#
# **NOT `every check that makes a real commit` -- that sentence stood here and
# was wrong.** TWELVE checks below drive a real commit through the wrapper that
# `exec`s this hook, and only eight of them went red. `MERGING[1]`, `[2]`, `[3]`
# and `[8]` ask for a REFUSAL -- a non-zero return, one parent, no tag -- and a
# hook that could not start at all satisfies every one of those. They were green
# for the whole three days the gate was off, VACUOUSLY. `MERGING[0]` is the only
# one of the refusal checks that went red, and only because it also demands the
# hook's OWN words. That is the trap `DRIVEN[4]`'s comment already names, still
# open in its three siblings, and it is written down in `tools/work.json` rather
# than fixed here because it is a different fault from this one.
#
# The ERP's two hooks were 100755 and its identical checks passed throughout,
# which is what made the mode rather than the hook text the difference.
#
# **ASKED THROUGH `_in`, LIKE EVERY OTHER GIT CHILD IN THIS FILE**, so the
# pointers git hands down are stripped: with `GIT_INDEX_FILE` or `GIT_DIR` set,
# `cwd` is ignored and `ls-files` answers about somebody else's index. And a git
# that is not on the machine is reported RED rather than allowed to throw,
# because this is the first git this file runs and an exception here would take
# the fifty checks below down with it, unreported.
_MODE_OF = {}
try:
    _LS = _in(ROOT, "git", "ls-files", "-s", "--",
              ".githooks/commit-msg", ".githooks/pre-commit")
    _LS_RC = _LS.returncode
    for _row in _LS.stdout.splitlines():
        _bits = _row.split(maxsplit=3)
        # `mode SP oid SP stage TAB path`. **THE STAGE IS NOT DECORATION:** on an
        # unmerged index the same path appears at stages 1, 2 and 3, and keeping
        # the last row seen let a 100755 side of a conflict answer for a 100644
        # one. Only stage 0 -- what would actually be committed -- counts.
        if len(_bits) == 4 and _bits[2] == "0":
            _MODE_OF[_bits[3].strip().replace("\\", "/")] = _bits[0]
except OSError as _no_git:  # noqa: BLE001
    _LS_RC = -1
check(
    "AND GIT RECORDS BOTH HOOKS EXECUTABLE AT STAGE 0 -- read out of the index, "
    "because `core.filemode` is false on Windows and the bit on disk there is a "
    "fiction. At 100644 `core.hooksPath` makes git SKIP the hook, hint, and exit 0: "
    "the commit lands untagged and unreviewed, which is the gate switched off rather "
    "than red. Both stood at 100644 from the split until 2026-09-07",
    _LS_RC == 0
    and set(_MODE_OF) == {".githooks/commit-msg", ".githooks/pre-commit"}
    and all(_mode == "100755" for _mode in _MODE_OF.values()),
)

if _BASH is None:
    for _name in DRIVEN + EXTRA_DRIVEN + MERGING:
        check(_name, False)
    check(LEFT_BEHIND[0], True)
else:
    _gate_there = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX))
    try:
        # **A HOOKS FOLDER HOLDING ONLY THE ONE HOOK**, so a real commit can be made
        # through the real tag hook without pre-commit (which runs the whole product)
        # coming with it. Forward slashes: bash is what reads this line.
        REAL_HOOK = str(THE_ROOT / ".githooks" / "commit-msg").replace("\\", "/")

        def _a_repository(name, committed=False):
            where = _gate_there / name
            where.mkdir()
            # **NOT THIS MACHINE'S HOOKS.** `core.hooksPath` is an ordinary global
            # git setting, and where one is set the commits below would run the real
            # gate -- this file, from inside itself.
            (where / "nohooks").mkdir()
            (where / "hooks").mkdir()
            (where / "hooks" / "commit-msg").write_text(
                "#!/usr/bin/env bash\nexec \"%s\" \"$@\"\n" % REAL_HOOK, encoding="utf-8")
            (where / "hooks" / "commit-msg").chmod(0o755)
            _in(where, "git", "init", "-q", ".")
            (where / SOURCE_FILE).write_text("a = 1\n", encoding="utf-8")
            _in(where, "git", "add", SOURCE_FILE)
            (where / "review_pass.json").write_text("{}\n", encoding="utf-8")
            if committed:
                _in(where, "git", "-c", "user.name=t", "-c", "user.email=t@t",
                    "-c", "core.hooksPath=nohooks", "commit", "-q", "-m", "first")
            return where

        def _hook(which, where, *argv):
            return _in(where, _BASH, str(THE_ROOT / ".githooks" / which), *argv)

        def _really_commit(where, body, *extra, config=()):
            """Make a real commit through the real hook, and hand back its message.

            The only faithful model of what git keeps. The draft that used
            `git stripspace --strip-comments` instead was blind to the whole
            fault: stripspace removes comment lines and never truncates at a
            scissors line at all.
            """
            (where / "body.txt").write_text(body, encoding="utf-8")
            (where / SOURCE_FILE).write_text("a = %d\n" % len(body), encoding="utf-8")
            _in(where, "git", "add", SOURCE_FILE)
            (where / "review_pass.json").write_text("{}\n", encoding="utf-8")
            env = _no_pointers_to_here()
            # **THE EDITOR ADDS TO WHAT GIT PREPARED, IT DOES NOT REPLACE IT.**
            # `cp body.txt "$1"` was the first draft and it threw git's own
            # template away -- so under `-v` there was no scissors line and no
            # diff in the file at all, and the two checks about them could not
            # go red. Caught by putting the fault back and watching nothing
            # happen. Written as a shell function because git runs the editor
            # through `sh -c` with the file as the last argument.
            env["GIT_EDITOR"] = (
                'p(){ cat body.txt "$1" > body.new && mv body.new "$1"; }; p')
            subprocess.run(
                ["git", "-c", "user.name=t", "-c", "user.email=t@t",
                 "-c", "core.hooksPath=hooks", *config, "commit", "-q", *extra, "-e"],
                cwd=str(where), env=env, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
            )
            return _in(where, "git", "log", "-1", "--format=%B").stdout

        TAG_ON_ITS_OWN_LINE = re.compile(r"^\[PM-REVIEWED\][ \t]*$", re.M)

        # ---- the tag matched anywhere in the message
        _tagging = _a_repository("tagging")
        _message = _tagging / "msg.txt"
        _message.write_text(
            "a message whose subject is the [PM-REVIEWED] tag itself\n", encoding="utf-8")
        _tagged = _hook("commit-msg", _tagging, str(_message))
        check(
            DRIVEN[0],
            _tagged.returncode == 0
            and len(TAG_ON_ITS_OWN_LINE.findall(_message.read_text(encoding="utf-8"))) == 1,
        )

        # ---- the same fault under `git commit -v`, asked of a real commit
        _verbose = _a_repository("verbose")
        _landed = _really_commit(_verbose, "an ordinary message\n", "-v")
        check(
            DRIVEN[1],
            len(TAG_ON_ITS_OWN_LINE.findall(_landed)) == 1
            and "an ordinary message" in _landed
            and "diff --git" not in _landed,
        )

        # ---- and the other direction: a cut line that git would NOT cut at.
        # Fewer than 24 dashes, so git keeps every word of it -- measured against
        # git 2.52, in the default configuration and under --cleanup=scissors alike.
        _intact = _a_repository("intact")
        _kept = _really_commit(
            _intact,
            "real title\n\nTHIS PARAGRAPH IS REAL\n------ >8 ------\nAND SO IS THIS LINE\n")
        check(
            DRIVEN[2],
            "THIS PARAGRAPH IS REAL" in _kept
            and "AND SO IS THIS LINE" in _kept
            and "------ >8 ------" in _kept
            and len(TAG_ON_ITS_OWN_LINE.findall(_kept)) == 1
            # **THE PART THAT CAN ACTUALLY FAIL.** Everything above holds whether
            # or not the hook took that line for a cut line, because the hook
            # deletes nothing. Treated as one, the tag is inserted ABOVE it and
            # this ordering flips.
            and _kept.index("AND SO IS THIS LINE") < _kept.index("[PM-REVIEWED]"),
        )

        # ---- and with a comment character that is not `#`. Git builds its cut
        # line from whatever `core.commentChar` says, so recognising only `#`
        # restores the whole fault for anyone who has changed it.
        _semicolon = _a_repository("semicolon")
        _semi = _really_commit(
            _semicolon, "an ordinary message\n", "-v",
            config=("-c", "core.commentChar=;"))
        check(
            DRIVEN[3],
            len(TAG_ON_ITS_OWN_LINE.findall(_semi)) == 1
            and "an ordinary message" in _semi
            and "diff --git" not in _semi,
        )

        # ---- and it never announces a tag it could not write. The message file is
        # put somewhere that does not exist, so the write cannot happen. ASKED FOR
        # THE HOOK'S OWN WORDS: a condition of "failed and said nothing" is satisfied
        # by bash failing to start at all, which is not this check's subject.
        _nowhere = _a_repository("nowhere")
        _lost = _hook("commit-msg", _nowhere, str(_nowhere / "no-such-folder" / "msg.txt"))
        check(
            DRIVEN[4],
            _lost.returncode != 0 and "the tag could not be written" in _lost.stderr,
        )

        # ---- AND THE ONE THE SIX-DASH CHECK ABOVE CANNOT ASK: a line git really
        # does cut at, with the author's own words below it.
        #
        # **THE CHECK ABOVE GUARDS THE OTHER DIRECTION AND BOTH ARE NEEDED.** It
        # asks that a lookalike is not treated as a cut line; this asks that a real
        # one is not treated as a truncation point. Six dashes is a line this hook
        # never matches, so deleting the line that puts the rest of the message back
        # changed nothing and every check stayed green -- measured on 2026-09-02, in
        # all three repositories, with the author's paragraphs vanishing from real
        # commits.
        #
        # **DEFAULT CONFIGURATION, NO -v, WHICH IS THE WHOLE POINT.** Under -v git
        # would throw this away itself and the hook's damage would be invisible.
        # In the default cleanup git strips the marker line as a comment and KEEPS
        # everything below it -- measured, not assumed -- so what lands is the plain
        # evidence of whether the hook deleted anything.
        _realcut = _a_repository("realcut")
        _whole = _really_commit(
            _realcut,
            "real title\n\nTHIS PARAGRAPH IS REAL\n"
            "# ------------------------ >8 ------------------------\n"
            "AND SO IS THIS LINE\n")
        check(
            DRIVEN[5],
            "THIS PARAGRAPH IS REAL" in _whole
            and "AND SO IS THIS LINE" in _whole
            and len(TAG_ON_ITS_OWN_LINE.findall(_whole)) == 1,
        )

        # ---- and with a comment marker of more than one character. `core.commentChar`
        # takes one; `core.commentString` takes a string, and the check next door only
        # ever tried the first kind, so a pattern anchored to a single character passed
        # it while losing the tag outright on an ordinary setting.
        _multichar = _a_repository("multichar")
        _rem = _really_commit(
            _multichar, "an ordinary message\n", "-v",
            config=("-c", "core.commentString=REM"))
        check(
            DRIVEN[6],
            len(TAG_ON_ITS_OWN_LINE.findall(_rem)) == 1
            and "an ordinary message" in _rem
            and "diff --git" not in _rem,
        )

        # ---- AND A GIT THAT CANNOT ANSWER IS A REFUSAL, NOT AN EMPTY ANSWER.
        #
        # **REAL DAMAGE, NOT A STAND-IN.** `.git/index` is overwritten with bytes
        # that are not an index, which is exactly the case the hook's own comment
        # names. git then fails the staged-list question outright while still
        # answering `rev-parse --show-toplevel`, so the hook reaches the question
        # and gets a failure rather than an empty list.
        _broken = _a_repository("broken-index")
        (_broken / "msg.txt").write_text("an ordinary message\n", encoding="utf-8")
        (_broken / ".git" / "index").write_bytes(b"this is not an index")
        _refused = _hook("commit-msg", _broken, str(_broken / "msg.txt"))
        check(
            DRIVEN[7],
            _refused.returncode != 0
            and "could not say what is staged" in _refused.stderr
            and "[PM-REVIEWED]" not in (_broken / "msg.txt").read_text(encoding="utf-8"),
        )

        # ------------------------------------------- D173: A MERGE IS A COMMIT
        #
        # **THE HOOKS FOLDER HOLDS ONLY `commit-msg`, AND THAT IS FAITHFUL RATHER
        # THAN CONVENIENT** -- on a clean merge git runs only that one anyway.
        # Where the note `pre-commit` leaves is needed below it is WRITTEN OUT,
        # because the real `pre-commit` cannot run in a repository that is not this
        # one. That is the interface between the two hooks, not a stand-in for
        # either: the two checks at the foot of this block drive the real
        # `pre-commit` and require it to leave exactly that.
        def _two_branches(name):
            """A repository whose two branches change different files."""
            where = _a_repository(name, committed=True)
            _on = _in(where, "git", "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
            _in(where, "git", "checkout", "-q", "-b", "side")
            (where / "b.js").write_text("b = 1\n", encoding="utf-8")
            _in(where, "git", "add", "b.js")
            _in(where, "git", "-c", "user.name=t", "-c", "user.email=t@t",
                "-c", "core.hooksPath=nohooks", "commit", "-q", "-m", "on the branch")
            _in(where, "git", "checkout", "-q", _on)
            (where / "c.js").write_text("c = 1\n", encoding="utf-8")
            _in(where, "git", "add", "c.js")
            _in(where, "git", "-c", "user.name=t", "-c", "user.email=t@t",
                "-c", "core.hooksPath=nohooks", "commit", "-q", "-m",
                "so the merge cannot fast-forward")
            return where

        def _merge(where):
            return _in(where, "git", "-c", "user.name=t", "-c", "user.email=t@t",
                       "-c", "core.hooksPath=hooks", "merge", "--no-ff",
                       "-m", "a merge nobody read", "side")

        def _hold_back(where):
            """Start the merge and keep it uncommitted, WITH AN IDENTITY.

            **`git merge` DEMANDS A COMMITTER BEFORE IT WILL START**, `--no-commit`
            and all, and the two calls here were the only git children in this file
            that did not carry one. On a machine with a global `user.email` -- every
            machine this was written on -- they worked; on the GitHub runner, which
            has none, the merge refused outright, nothing was ever held back, and
            the check below went red for a reason that had nothing to do with the
            hook it was asking about. Red on the runner from 2026-09-05.
            """
            return _in(where, "git", "-c", "user.name=t", "-c", "user.email=t@t",
                       "merge", "--no-commit", "--no-ff", "side")

        def _commit(where, message):
            return _in(where, "git", "-c", "user.name=t", "-c", "user.email=t@t",
                       "-c", "core.hooksPath=hooks", "commit", "-q", "-m", message)

        def _parents(where):
            return len(_in(where, "git", "rev-list", "--parents", "-n1",
                           "HEAD").stdout.split()) - 1

        def _the_note(where):
            return (where / _in(where, "git", "rev-parse", "--git-dir").stdout.strip()
                    / "kartaan-pre-commit-approved")

        def _message_of(where):
            return _in(where, "git", "log", "-1", "--format=%B").stdout

        # ---- the dangerous case: a record lying about turns the merge into a pass.
        _dangerous = _two_branches("merge-with-a-record-lying-about")
        _said = _merge(_dangerous)
        check(
            MERGING[0],
            _said.returncode != 0
            and _parents(_dangerous) == 1
            and "[PM-REVIEWED]" not in _message_of(_dangerous)
            and "the half of the gate that demands a review"
                in (_said.stdout + _said.stderr),
        )
        check(MERGING[1], (_dangerous / "review_pass.json").exists())

        # ---- and the loud case, asked the same way.
        _loud = _two_branches("merge-with-no-record")
        (_loud / "review_pass.json").unlink()
        _said = _merge(_loud)
        check(MERGING[2], _said.returncode != 0 and _parents(_loud) == 1)

        # ---- and a note that is not about this commit.
        _elsewhere = _two_branches("merge-with-a-note-from-elsewhere")
        _the_note(_elsewhere).write_text("0" * 40 + "\n", encoding="utf-8")
        _said = _merge(_elsewhere)
        check(
            MERGING[3],
            _said.returncode != 0
            and "[PM-REVIEWED]" not in _message_of(_elsewhere),
        )

        # ---- and the way through, which has to exist.
        _held = _two_branches("merge-held-back")
        _holding = _hold_back(_held)
        _the_note(_held).write_text(
            _in(_held, "git", "write-tree").stdout.strip() + "\n", encoding="utf-8")
        _said = _commit(_held, "the merge, read like any other commit")
        _landed = _message_of(_held)
        check(
            MERGING[4],
            # **THE SETUP IS ASSERTED, NOT ASSUMED.** A held-back merge that never
            # started leaves nothing staged, so the commit below fails and this
            # check goes red -- looking exactly like a verdict about the hook when
            # it is a verdict about `git merge` having no committer. Named here so
            # the next reader is told which of the two happened.
            _holding.returncode == 0
            and _said.returncode == 0
            and _parents(_held) == 2
            and len(TAG_ON_ITS_OWN_LINE.findall(_landed)) == 1
            and not (_held / "review_pass.json").exists()
            and not _the_note(_held).exists(),
        )

        # ---- and nothing about an ordinary commit changed.
        _plain = _two_branches("an-ordinary-commit")
        (_plain / SOURCE_FILE).write_text("a = 2\n", encoding="utf-8")
        _in(_plain, "git", "add", SOURCE_FILE)
        _said = _commit(_plain, "an ordinary commit")
        check(
            MERGING[5],
            _said.returncode == 0
            and len(TAG_ON_ITS_OWN_LINE.findall(_message_of(_plain))) == 1,
        )

        # ---- AND THE OTHER HALF: `pre-commit` really leaves the note.
        #
        # **THE RULE FILE IS THE FIXTURE, THE HOOK IS THE REAL ONE.** This hook is
        # four lines of work around `python tools/gate.py`, and that tool cannot
        # run against a repository that is not this one. So the probe repository is
        # given a `tools/gate.py` that passes, and then one that refuses, and what
        # is asked is the REAL hook's own behaviour around it -- the same technique
        # this file already uses to put a stand-in `git` in front of a hook.
        def _with_a_rule_file(name, how_it_goes):
            where = _a_repository(name, committed=True)
            (where / "tools").mkdir()
            (where / "tools" / "gate.py").write_text(
                "raise SystemExit(%d)\n" % how_it_goes, encoding="utf-8")
            return where

        _left = _with_a_rule_file("the-note-is-left", 0)
        _ran = _hook("pre-commit", _left)
        check(
            MERGING[6],
            _ran.returncode == 0
            and _the_note(_left).exists()
            and _the_note(_left).read_text(encoding="utf-8").strip()
                == _in(_left, "git", "write-tree").stdout.strip(),
        )

        _refused_it = _with_a_rule_file("no-note-when-it-refuses", 1)
        _ran = _hook("pre-commit", _refused_it)
        check(MERGING[7],
              _ran.returncode != 0 and not _the_note(_refused_it).exists())

        # ---- and the note is not unforgeable, which is SAID rather than guarded.
        # The bypass an independent reviewer found, driven: the note is taken
        # during a held-back merge, the merge is thrown away, the note is planted,
        # and the merge is made again cleanly. What is asked is the half that
        # holds -- no record, no tag -- because the other half does not hold and
        # the hook says so instead of pretending.
        _planted = _two_branches("a-note-planted-by-hand")
        (_planted / "review_pass.json").unlink()
        _planting = _hold_back(_planted)
        _tree = _in(_planted, "git", "write-tree").stdout.strip()
        _in(_planted, "git", "merge", "--abort")
        _the_note(_planted).write_text(_tree + "\n", encoding="utf-8")
        _merge(_planted)
        check(MERGING[8],
              _planting.returncode == 0
              and "[PM-REVIEWED]" not in _message_of(_planted))

    finally:
        _WENT = gate_run.take_it_away(_gate_there)
    check(LEFT_BEHIND[0], _WENT)
# **THE SAME SPELLING IN BOTH PLACES.** The local hook can be walked past with
# --no-verify; the check on GitHub is the half that cannot. They test the same
# thing, so the day they disagree one of them is passing a commit the other
# would stop -- which is exactly how this fault reached past the hook.
#
# Reached for by the NAME it is bound to, not by the pattern's own spelling:
# asked for by its spelling, this stops matching the moment the spelling changes,
# and the check below would then compare one site against nothing and pass.
#
# **D164 put a SECOND pattern in that file** -- the looser form, for commits made
# before the anchored rule started. This deliberately reads only the anchored one:
# the other is a fixed historical question and is not supposed to match this hook.
TAG_ON_GITHUB = re.compile(r"""TAG_ANCHORED='([^']+)'""")

tag_tests = (
    re.findall(r"TAG_LINE='([^']+)'", HOOK)
    + re.findall(TAG_ON_GITHUB, WORKFLOW)
)
check(
    "THE REVIEW TAG IS TESTED FOR THE SAME WAY IN THE HOOK AND ON GITHUB -- the count is "
    "asserted too, so a site that stops matching drops out of the comparison rather than "
    "being free to drift",
    len(tag_tests) == 2 and len(set(tag_tests)) == 1,
)
# **FED TO REAL grep, NOT READ FOR ITS PUNCTUATION.** This asked only that the
# pattern starts with `^` and ends with `$`. `^.*\[PM-REVIEWED\].*$` does both and
# anchors nothing: changed at both sites together it left every check green and put
# the GitHub side back to the substring test the D156 commit fell to -- measured
# 2026-09-02 by an independent reviewer, who put that fault back and watched 449
# pass. So the pattern is now handed the two messages it exists to tell apart,
# through the same `grep -qE` both sites use to ask the question for real.
A_SENTENCE_ABOUT_THE_TAG = "a message whose subject is the [PM-REVIEWED] tag itself"
THE_TAG_ON_ITS_OWN = "[PM-REVIEWED]"


# **THE PATTERN AND THE MESSAGE GO IN FILES, NEVER IN ARGUMENTS.** Handed to a
# Git-for-Windows tool as an argument, `^\[PM-REVIEWED\]...` arrives with
# its backslashes eaten -- measured: the child was handed `^[PM-REVIEWED]...`, which
# is a character class matching any ONE of those letters. The strict pattern then
# fails against its own tag and the loose one passes everything, so asked that way
# this check goes red on correct code and green on the fault -- the exact inversion
# of what it is for. Read from a file, the pattern arrives as it is written.
_THE_GREP = shutil.which("grep")
if _THE_GREP is None and _BASH is not None:
    _beside_bash = Path(_BASH).with_name("grep.exe")
    _THE_GREP = str(_beside_bash) if _beside_bash.exists() else None


def _grep_matches(pattern, text):
    """What `grep -qE` really says. None when there is no grep to ask with."""
    if _THE_GREP is None:
        return None
    _asking = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX))
    try:
        for name, what in (("pattern", pattern), ("message", text)):
            io.open(_asking / name, "w", encoding="utf-8", newline="\n").write(what + "\n")
        return subprocess.run(
            [_THE_GREP, "-qE", "-f",
             str(_asking / "pattern").replace("\\", "/"),
             str(_asking / "message").replace("\\", "/")],
            capture_output=True, text=True,
        ).returncode == 0
    finally:
        shutil.rmtree(_asking, ignore_errors=True)


check(
    "and both are anchored to a WHOLE LINE -- FED to the same `grep -qE` both sites use: a "
    "sentence that merely mentions the tag must not match, the bare tag must. Asked instead "
    "for a `^` and a `$`, a pattern that matches anything at all satisfies it",
    _THE_GREP is not None
    and len(set(tag_tests)) == 1
    and all(_grep_matches(one, A_SENTENCE_ABOUT_THE_TAG) is False for one in tag_tests)
    and all(_grep_matches(one, THE_TAG_ON_ITS_OWN) is True for one in tag_tests),
)

# ------------------------------ WHAT THE WORKFLOW DOES IS NO LONGER READ HERE (D172)
#
# **SIX CHECKS STOOD HERE AND THEY ARE GONE, NOT WEAKENED.** They read
# `.github/workflows/pm_check.yml` and asserted that its markers, its two tag
# patterns, the branch choosing between them and its handling of a merge were
# spelled the way this file remembered. Six rounds of independent review each
# found a spelling that satisfied them and switched the gate off anyway -- a
# second assignment below the first, `export` in front of it, `NOT_CODE` emptied
# so nothing counts as code, `MISSING` reset so the walk finds an untagged commit
# and passes. Each round closed the spelling it was shown and the next found
# another. **There is no last spelling.**
#
# **THE SAME FACTS ARE NOW ESTABLISHED BY RUNNING THE FILE**, in
# `tools/gate_run_checks.py`: a real history with a reviewed commit, an unreviewed
# one, one that merely mentions the tag in a sentence, and an unreviewed merge, put
# through the workflow's own steps with real bash and real git -- and then the
# workflow broken every way those six rounds found, and the YAML harness around
# it broken every way that switches the gate off without touching the shell,
# with the answer required to stop being right each time -- and each fault
# judged by the ONE question that exists to detect it (D175).
#
# **NOT KEPT ALONGSIDE, DELETED.** Two checks over one fact read as two guarantees,
# and the day the fact changes one of them gets updated and the other quietly
# lies. **Six went; the six that covered the two steps the runner now runs.**
#
# **AND WHAT IS LEFT IS MORE THAN THIS NOTE USED TO SAY, WHICH A COLD READER
# MEASURED AND THIS SENTENCE HAD TO BE CORRECTED FOR (2026-09-04).** It said only
# one thing was left -- that what counts as code is spelled the same way in all
# three places. **That is still here and is still the reason the sweep exists.**
# But so are two other kinds, deliberately, and saying otherwise pointed the next
# reader away from a dozen checks that are genuinely read rather than run:
#
#  * the steps the runner NEVER runs -- the secret scan, node, the checks sweep,
#    the sibling checkouts, the seller-account guard, the recipes, the empty-tree
#    sentinel, the rewritten-history refusal. The runner makes no claim about any
#    of them (D171 is why they are worth naming) and a reading check is the only
#    thing standing over them until something runs them.
#  * that `GATE_BORN` is a real commit id and not the placeholder left behind.
#
# **NO COUNT IS WRITTEN HERE ON PURPOSE.** The sentence this replaces was wrong
# because a number in prose goes stale the moment a check is added, and nothing
# tests it -- which is the whole of D170 arriving from the direction of a comment.
# **A reading check kept for a reason is not a weakness; a note that hides one is.**

EXPECTED = 114
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print(f"all {ran} checks passed")
