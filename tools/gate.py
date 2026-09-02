"""The gate. What this repository refuses to commit.

**2,206 CHECKS PASSED HERE AND NOTHING MADE THEM RUN.** They were green because a
session remembered to run them. One that forgets puts a red commit straight in,
and nobody finds out until something else breaks, later, somewhere else. **And 0
of this repository's 11 commits carry any record that a person read the diff.**

Follows `Kartaan-Server`'s gate (`cf648d9`) rather than inventing a shape. What
is different here is written down where it differs, and nothing was dropped
without saying so.

---

**EVERY RULE LIVES IN THIS FILE, not in the git hook.** A rule written inside a
hook is a rule nothing can test. The ERP paid for that: a hook that PRINTED it
had tagged a commit and never did, undetected across three commits.
`tools/gate_checks.py` checks the rules here.

**IT REFUSES RATHER THAN SKIPS AT EVERY POINT, INCLUDING WHEN GIT CANNOT
ANSWER.** A gate that waves a commit through because it could not look is worse
than no gate, because everybody believes it looked. The ERP's own hook records
exactly this: an empty staged-file list read as "nothing is staged" and exited 0.

---

**WHAT IS DIFFERENT HERE, AND WHY:**

- **THE JAVASCRIPT CHECKS RUN TOO.** The Server had none; this repository has 400
  of them in `extension/`, which is the half that runs in the seller's own
  Chrome. A gate that ran only the Python would report green while a fifth of the
  checking never happened -- the same shape as the Server's gate not sweeping its
  own `tools/`, which it found by reading what it printed.
- **THE CREDENTIAL PATTERNS ARE WRITTEN HERE.** The Server imports them from
  `handshake.py`, because that file has to answer the same question every time it
  speaks. Nothing in this package does, so there is no second copy to drift from
  -- and this is the only place they are written down.
- **THE SECURITY LENS IS DIFFERENT and it is the sharpest one in Kartaan.** This
  repository is **copied into every seller's own GitHub account**, and sits there
  beside their Amazon and Google credentials. A secret committed here is copied
  into every seller's account with it.

**WHAT WAS DROPPED FROM THE SERVER'S GATE, and why -- dropping a tick is a
decision:**

- **"the server actually starts"** -- there is no server here. What corresponds is
  the checks, which already run.
- **the hosted-site tick and the `STATUS.html` board** -- the ERP's, not this
  repository's. There is no hosted site here and nothing generates a board;
  `tools/work.json` is written by hand and read by a person.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# **WHAT A CREDENTIAL LOOKS LIKE. Written here and nowhere else in this package.**
#
# Note the `[y]` and `[s]`: written plainly, these patterns match their own source
# and the gate would refuse every commit that touches this file. The Server's gate
# and the ERP's hook both carry the same note, and both found it by testing the
# gate rather than trusting it.
LOOKS_LIKE_A_CREDENTIAL = (
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{30,}"),
    re.compile(r"ya29\.[A-Za-z0-9._-]{20,}"),
    re.compile(r"AIzaSy[A-Za-z0-9_-]{30,}"),
    re.compile(r"amzn1\.application-oa2-client\.[a-f0-9]{32,}"),
    re.compile(r"Atzr\|[A-Za-z0-9_-]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r'"private_ke[y]"'),
    re.compile(r'"client_secre[t]"\s*:\s*"[^"]{8,}"'),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"discord(app)?\.com/api/webhooks/"),
)

# **WHAT IS NOT CODE. A DENYLIST, NEVER AN ALLOWLIST.**
#
# Everything counts as code unless named here, so a new kind of file is covered
# by default and an exemption has to be added deliberately, in a diff somebody
# reads. The ERP's hook learnt this the expensive way: an allowlist of extensions
# leaked twice in one session, because the hooks themselves have no extension.
#
# **`tools/work.json` IS CODE HERE, deliberately.** The gate reads it, and
# something the gate trusts must not be outside the gate.
#
# **MUST STAY IDENTICAL TO THE COPY IN `.githooks/commit-msg` AND IN
# `.github/workflows/pm_check.yml`.** Three copies of one fact, and
# `tools/gate_checks.py` holds them to each other -- because the day they
# disagree, one of them lets a commit through that another would have stopped.
NOT_CODE = re.compile(
    r"(^|/)(README|LICENSE|CHANGELOG|NOTICE)(\.md)?$"
    r"|^\.gitignore$|^\.gitattributes$"
    r"|^review_pass\.json$|^review_pass\.template\.json$"
)

THE_RECORD = "review_pass.json"

# **WORDS THAT ARE A RESULT, NOT A FINDING.** "It passed" is what a check says.
# A review says what was looked for and what was there.
NOT_A_FINDING = (
    "fine", "ok", "okay", "good", "looks good", "lgtm", "passed", "pass",
    "passes", "all good", "no issues", "none", "nothing", "n/a", "na", "-",
    "clean", "no problems", "all fine", "yes", "done",
)

# Where the code lives. **Swept, never listed** -- see `every_checks_file`.
CODE_FOLDERS = ("autosync", "tools")
JAVASCRIPT_FOLDERS = ("extension", "test")


class Refused(Exception):
    """This commit does not go in, and the sentence says why."""


def _git(*args):
    """One git question, or a refusal.

    **A GIT THAT CANNOT ANSWER IS A REFUSAL, NOT AN EMPTY ANSWER.** Read as
    empty, "nothing is staged" becomes the answer and every rule below then
    passes by having nothing to look at.
    """
    try:
        done = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False,
        )
    except OSError as wrong:
        raise Refused(
            f"git could not be run at all ({wrong}), so nothing here could be checked."
        )
    if done.returncode != 0:
        raise Refused(
            f"git could not answer `git {' '.join(args)}`, so nothing here could be checked.\n\n"
            f"{done.stderr.strip()}"
        )
    return done.stdout


# ------------------------------------------------------------ 1. what is staged


def staged_files():
    """The paths this commit touches. **Deletions included.**

    Filtered out, the one commit that takes a checks file away is the one commit
    this gate does not look at.
    """
    said = _git("diff", "--cached", "--name-only", "-z")
    return [one for one in said.split("\0") if one]


def the_lines_being_added():
    """Only the lines this commit ADDS.

    Reading the whole file instead would refuse a commit for a credential
    somebody else committed years ago, which teaches everybody to pass
    `--no-verify` -- and that is how a gate stops being a gate.
    """
    said = _git("diff", "--cached", "-U0", "--diff-filter=ACMR")
    return [
        line[1:] for line in said.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


# --------------------------------------------------------------- 2. no credential


def why_a_credential_is_refused(added_lines):
    """The pattern a credential-shaped thing matched, or None."""
    for line in added_lines or ():
        for shape in LOOKS_LIKE_A_CREDENTIAL:
            if shape.search(line):
                return shape.pattern
    return None


# ------------------------------------------------------------- 3. the register


def the_register():
    """`tools/work.json`, or a refusal. It is not optional."""
    where = ROOT / "tools" / "work.json"
    if not where.is_file():
        raise Refused(
            "tools/work.json is missing. It is the only record of which file belongs to\n"
            "  which piece of work, and without it nothing can say what this commit is part of."
        )
    try:
        return json.loads(where.read_text(encoding="utf-8"))
    except ValueError as wrong:
        raise Refused(
            f"tools/work.json cannot be read as JSON, so the register says nothing.\n\n  {wrong}"
        )


def why_the_register_is_refused(register):
    """Everything wrong with the register, in words, or an empty list."""
    wrong = []
    items = register.get("items")
    if not isinstance(items, list) or not items:
        return ["tools/work.json lists no pieces of work at all."]

    # **ONE OWNER PER FILE.** Two owners means two answers to "has this been
    # reviewed" about the same bytes.
    owners = {}
    for piece in items:
        for path in piece.get("files") or ():
            if path in owners:
                wrong.append(f"{path} is owned by both {owners[path]} and {piece.get('id')}.")
            owners[path] = piece.get("id")
            if not (ROOT / path).is_file():
                wrong.append(f"{piece.get('id')} lists {path}, and there is no such file.")

    # **AND EVERY FILE THAT EXISTS IS OWNED.** Without this the register stays
    # true by saying less: a new file simply never appears, and the register goes
    # on describing a repository that has grown underneath it.
    #
    # **`tools/` IS SWEPT TOO, and this gate is the reason.** It is code, it
    # decides what may be committed, and a gate that exempted itself from the
    # register would be the one file nobody had to account for.
    for folder in CODE_FOLDERS:
        for found in sorted((ROOT / folder).glob("*.py")):
            path = f"{folder}/{found.name}"
            if path not in owners:
                wrong.append(f"{path} exists and no piece of work owns it.")
    # **AND THE JAVASCRIPT, which the Server had none of.** The extension is half
    # of what this repository ships.
    for folder in JAVASCRIPT_FOLDERS:
        for found in sorted((ROOT / folder).glob("*.js")):
            path = f"{folder}/{found.name}"
            if path not in owners:
                wrong.append(f"{path} exists and no piece of work owns it.")

    # **A FINDING IS CLOSED BY NAMING THE CHECK THAT GOES RED WITHOUT THE FIX.**
    # "It looks right now" has closed findings in this product before, and they
    # came back.
    for piece in items:
        for finding in piece.get("findings") or ():
            if finding.get("fixed") and not str(finding.get("proved_by") or "").strip():
                wrong.append(
                    f"{piece.get('id')} has a finding marked fixed that names no check going "
                    "red when the fix is taken back out."
                )
    return wrong


# ------------------------------------------------- 4. somebody read the diff


def code_among(staged):
    """The staged paths that count as code. See NOT_CODE."""
    return [one for one in staged if not NOT_CODE.search(one)]


def the_review_record():
    """`review_pass.json`, or None if there is not one.

    **NOT A REFUSAL BY ITSELF.** Whether one is needed depends on what is being
    committed, and that is decided in one place below rather than here.
    """
    where = ROOT / THE_RECORD
    if not where.is_file():
        return None
    try:
        return json.loads(where.read_text(encoding="utf-8"))
    except ValueError as wrong:
        raise Refused(
            f"{THE_RECORD} cannot be read as JSON, so there is no record of anybody\n"
            f"  having read this commit.\n\n  {wrong}"
        )


def _a_real_sentence(said):
    """Is this somebody's words, or a shrug?"""
    plain = " ".join(str(said or "").lower().split()).strip(" .!")
    return bool(plain) and plain not in NOT_A_FINDING and len(plain) >= 8


def why_the_review_is_refused(record, code_staged):
    """Everything missing from the review record, in words, or an empty list.

    **THE ONE QUESTION IT EXISTS TO ASK: what was FOUND?** Not whether it passed.
    A check answers a question somebody thought to ask; a review is what catches
    the question nobody thought of. **This repository found twelve faults in its
    own checks on 2026-09-02 by putting faults back, and five of them were checks
    that could not fail for the thing they were named for.** No check catches
    that. Reading it does.
    """
    if record is None:
        return [
            f"there is no {THE_RECORD}. Copy review_pass.template.json to it, fill it in,",
            "and commit again. It is deleted for you afterwards, so the next commit needs its own.",
        ]
    wrong = []
    written_by = str(record.get("written_by") or "").strip()
    reviewer = str(record.get("reviewer") or "").strip()
    if not written_by:
        wrong.append("written_by is empty -- name the session that wrote this.")
    if not reviewer:
        wrong.append("reviewer is empty -- name who read it.")
    if written_by and reviewer and written_by.lower() == reviewer.lower():
        # **A REVIEW BY THE AUTHOR IS NOT A REVIEW.** Its own refusal, so it
        # cannot be satisfied by leaving both blank.
        wrong.append("the reviewer and the author are the same words. That is not a review.")
    if not record.get("independent"):
        # **NOT REFUSED -- RECORDED.** A session alone on a machine cannot conjure
        # a second pair of eyes, and pretending otherwise is worse than saying so.
        # What is refused is a weak review recorded as a strong one.
        if not _a_real_sentence(record.get("if_not_independent_why")):
            wrong.append(
                "independent is false and if_not_independent_why says nothing. A review by "
                "one pair of eyes is worth recording -- as what it is.")
    if not record.get("checked_against_decision_log"):
        wrong.append("checked_against_decision_log is false. D40 calls that log binding.")

    read = {str(one).replace("\\", "/") for one in record.get("read") or ()}
    missed = [one for one in code_staged if one not in read]
    if missed:
        wrong.append(
            "the record does not say these were read: " + ", ".join(sorted(missed))
            + ". A reviewer who did not open a changed file did not review this commit.")

    found = [one for one in (record.get("found") or []) if str(one).strip()]
    if not found:
        wrong.append("found is empty. Say what was looked for and what was there.")
    else:
        shrugs = [one for one in found if not _a_real_sentence(one)]
        if shrugs:
            wrong.append(
                "these are results, not findings: " + ", ".join(repr(one) for one in shrugs)
                + ". 'It passed' is what a check says.")
    if not _a_real_sentence(record.get("security")):
        wrong.append(
            "security says nothing. THIS REPOSITORY IS COPIED INTO EVERY SELLER'S OWN GITHUB "
            "ACCOUNT, beside their Amazon and Google credentials -- 'nothing changes' is an "
            "answer, with a reason.")
    return wrong


# --------------------------------------------------------------- 5. every check


def every_checks_file():
    """Every checks file there is, Python and JavaScript. **FOUND, NOT LISTED.**

    A list goes stale the first time somebody adds one, and it goes stale
    silently -- the new file simply never runs while the gate goes on saying the
    checks passed.

    **THE JAVASCRIPT IS SWEPT TOO.** The Server's gate had none to sweep; here
    they are 400 checks over the half that runs in the seller's own Chrome, and a
    gate that ran only the Python would report green while a fifth of the
    checking never happened.
    """
    found = []
    for folder in CODE_FOLDERS:
        found += sorted((ROOT / folder).glob("*_checks.py"))
    for folder in JAVASCRIPT_FOLDERS:
        found += sorted((ROOT / folder).glob("*.test.js"))
    return found


def how_to_run(where):
    """What runs that checks file. Its own kind decides, never its folder."""
    if where.suffix == ".js":
        return ["node", str(where)]
    return [sys.executable, str(where)]


def run_one(where):
    """One checks file. Answers its output if it failed, or None."""
    try:
        done = subprocess.run(
            how_to_run(where), cwd=ROOT, capture_output=True, text=True, check=False,
        )
    except OSError as wrong:
        # **A RUNNER THAT IS NOT THERE IS A REFUSAL.** No node on the machine
        # must not mean the JavaScript checks quietly did not run.
        return f"could not be run at all: {wrong}"
    if done.returncode != 0:
        return (done.stdout + done.stderr).strip()
    return None


# ---------------------------------------------------------------------- the gate


def main():
    staged = staged_files()
    if not staged:
        raise Refused("nothing is staged, so there is nothing to commit.")

    shape = why_a_credential_is_refused(the_lines_being_added())
    if shape:
        raise Refused(
            "something shaped like a credential is in what this commit adds.\n\n"
            f"  It matches: {shape}\n\n"
            "  Take it out, and treat it as compromised -- a committed secret is\n"
            "  compromised even if the commit never leaves this machine (Golden Rule 8).\n"
            "  **AND THIS REPOSITORY IS COPIED INTO EVERY SELLER'S OWN GITHUB ACCOUNT**,\n"
            "  so it would be copied into all of them with it.\n\n"
            "  This is pattern matching and it is not a guarantee. The rule is that no\n"
            "  secret is in the code at all."
        )

    wrong = why_the_register_is_refused(the_register())
    if wrong:
        raise Refused(
            "the work register does not match what is here:\n\n"
            + "\n".join(f"    {one}" for one in wrong)
        )

    # **ONLY WHEN CODE IS BEING COMMITTED.** A commit that changes nothing but the
    # README does not need somebody to have read a diff of it -- and demanding one
    # would teach everybody to write a record that means nothing, which is worse
    # than not asking.
    code_staged = code_among(staged)
    if code_staged:
        wrong = why_the_review_is_refused(the_review_record(), code_staged)
        if wrong:
            raise Refused(
                "nothing records that anybody READ this commit:\n\n"
                + "\n".join(f"    {one}" for one in wrong)
            )

    files = every_checks_file()
    if not files:
        raise Refused(
            "no checks files were found at all. Either they have been deleted, or this\n"
            "  gate can no longer see them -- and both mean the checks are not running."
        )
    for where in files:
        failed = run_one(where)
        if failed:
            raise Refused(
                f"checks failed in {where.parent.name}/{where.name}:\n\n{failed}"
            )

    python = len([f for f in files if f.suffix == ".py"])
    print(
        f"  gate: {python} Python and {len(files) - python} JavaScript checks files pass, "
        "the register matches, nothing leaked."
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Refused as no:
        print(f"\n  BLOCKED: {no}\n", file=sys.stderr)
        sys.exit(1)
