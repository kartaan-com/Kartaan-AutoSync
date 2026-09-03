"""Checks for the review-tag gate -- by RUNNING it, never by reading it (D172).

WHY THIS FILE EXISTS. Six rounds of independent review each found a different
spelling of one hole in `.github/workflows/pm_check.yml`, and every round closed
the spelling it was shown: a second assignment below the first, `export` in front
of it, `NOT_CODE` emptied so nothing counts as code and the whole walk switches
itself off, `MISSING` set to nought so it finds untagged commits and passes
anyway. **There is no last spelling.** A check that reads the file has to guess
which forms a future author might write, and is wrong the moment somebody writes
one it did not think of.

D171 says where the holes live: the file that is only ever read. The same
`NOT_CODE` fault put back in `.githooks/commit-msg` turns eleven checks red at
once, because something runs that file; put back here it left every check in
three repositories green.

So the question changes. Every check below makes a real history, runs the
workflow's own two steps against it with real bash and real git, and asks the
only question that matters: **does this file refuse an unreviewed commit, and
does it say which one and why.** Then it breaks the workflow every way the six
rounds found -- forty-one of them -- and requires the answer to stop being
right.

**AND THE SHELL IS NOT THE WHOLE GATE.** Running it is necessary and NOT
sufficient: `continue-on-error: true` on the tag step leaves the step failing and
still naming the untagged commit, and GitHub marks the job GREEN and takes the
commit. Taking `push:` out of `on:`, and an `if` on the job that cannot be true,
do the same, and **none of the three is inside a `run:` block** -- so this file
ran the shell while GitHub decided whether the shell's answer counted. The
harness is now asked a question of its own, as STRUCTURE and not as text, and the
last faults below are those three put back (D172, corrected the same day).

**AND A FAULT IS CAUGHT BY ITS OWN NAMED QUESTION, NEVER BY ANY QUESTION (D175).**
This file used to count a fault caught the moment ANY question answered wrong. On
a pull request GitHub checks out a merge commit of its own making, which carries
no tag, so the question that walks this repository's real history is permanently
wrong there -- and every fault check passed while testing nothing. Each fault now
names the question that exists to detect it, and a question already wrong on the
workflow as written attributes nothing: the faults naming it are reported RED.

**WHAT THIS CANNOT SEE HERE, AND WHY THAT IS DIFFERENT FROM THE ERP.** A commit
made today is a descendant of every commit a marker could name, so `GATE_BORN`
moved FORWARD can only be seen through a commit that was already in the history
and carries no tag. The ERP has such commits -- twenty-five of them, measured
2026-09-04, where this entry first said eleven. **This repository has none**
-- every commit the rule reaches carries the tag on a line of its own -- so there
is nothing a marker moved forward could hide, and that is measured below rather
than assumed: the whole history is walked and must pass. The day an untagged
commit lands inside the rule's reach, that check goes red and this paragraph
stops being true.

**AND WHERE THE STRICT RULE STARTS IS UNOBSERVABLE HERE FOR THE SAME REASON.**
The Server has two commits that only MENTION the tag, so moving that marker back
over them condemns work that was genuinely reviewed, and a run sees it happen.
Nothing in this history mentions the tag without carrying it, so the strict and
the loose question give the same answer about every commit here and the marker's
exact value changes nothing a run can measure. Only an emptied or a deleted one
can be seen, and both are below. **That sentence is PINNED BY A CHECK at the foot
of this file rather than believed** -- the Server's copy carried D164's withdrawn
claim as prose for a day, written after the sweep that took it out of six other
places (D169, amended).

**AND THAT IS WHY THE FIFTH QUESTION HERE ASKS FOR A PASS WHERE THE ERP'S ASKS FOR
A REFUSAL. IT IS NOT A WEAKER CHECK AND IT IS NOT A BUG.** The ERP walks one real
untagged commit and requires the gate to refuse it, because it HAS them to walk.
Here there are none, so a refusal is not available to ask for -- and the same fact
from the other side is that the whole history must PASS. Both questions fail the
moment the marker stops covering what it should: there, by a commit stopping being
refused; here, by one starting to be. The question differs because the histories
differ, not because the gate does.

Run: python tools/gate_run_checks.py
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate_run  # noqa: E402

ran = 0
failures = []


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


# =============================================== WHAT IS ASKED, NAMED UP HERE
#
# **NAMED BEFORE ANYTHING CAN GO WRONG.** A checks file that raises at its top
# level stops there and every check below it silently never runs -- the fault
# Kartaan-Server lost an hour to on 2026-09-02, where thirty-one checks were
# silent while a run looked green. With no bash, no PyYAML, or a repository that
# be cloned, every name below is reported RED and the count still comes out the
# same.

ASKED = (
    "THE GATE RUNS AND PASSES A COMMIT THAT CARRIES THE REVIEW TAG ON A LINE OF ITS OWN "
    "-- run, not read: the workflow's own two steps, through real bash, against a real "
    "history made for the purpose. RUNS is half the question: a step whose condition is "
    "false is SKIPPED, and GitHub counts a skipped step as a success, so a gate that never "
    "ran looks exactly like one that passed",

    "AND REFUSES ONE THAT CARRIES NO TAG, NAMING THAT COMMIT AND WHY -- and NOT naming "
    "the reviewed commit sitting under it in the same range, so the refusal has to be "
    "about the right commit rather than merely happening",

    "AND REFUSES ONE WHOSE MESSAGE ONLY MENTIONS THE TAG IN A SENTENCE -- the bug D164 "
    "caught in the act in Kartaan-Server, where two commits reached GitHub reviewed and "
    "untagged because the hook found its own name in the author's prose, decided the tag "
    "was already there and appended nothing. Nothing here has ever been in that state, "
    "and this is what keeps it that way",

    "AND REFUSES AN UNREVIEWED MERGE WHOSE FILES MERGE CLEANLY -- without `-m` git shows "
    "a combined diff that omits every cleanly-merged file, so the merge hands the walk an "
    "empty file list and is waved through as carrying no code. Nothing had ever run a "
    "merge past this gate. **AND THIS IS THE SAFE HALF OF D173, SAID PLAINLY RATHER THAN "
    "LEFT TO BE FOUND:** an UNTAGGED merge is the case this layer can see. The dangerous "
    "one is a merge WEARING the tag, because a review record lying about was consumed by "
    "`commit-msg` while `pre-commit` never ran -- and nothing read from a message can "
    "tell that from a real review, so this file cannot ask it. It is asked where it can "
    "be answered, against the real hooks, in `tools/gate_checks.py`",

    "AND EVERY COMMIT THE RULE ALREADY REACHES PASSES -- the whole history walked as a "
    "FIRST PUSH, where GitHub sends no previous commit at all and the workflow answers a "
    "row of noughts with the empty tree and a range of HEAD alone. That is what makes a "
    "marker moved forward unable to hide anything HERE: there is nothing behind it to "
    "exempt. Measured rather than assumed, so the day an untagged commit lands inside the "
    "reach this goes red rather than the limit going unnoticed",
    "AND A BRANCH THAT STARTED BEFORE THE ANCHOR IS NOT CONDEMNED FOR IT, WHILE STILL "
    "BEING ASKED -- each COMMIT is asked the question that applied to it, never the "
    "branch it sits on (D164). **THIS REPLACED A GUARD THAT FAILED THE WHOLE RUN** when "
    "the anchor was not an ancestor of HEAD: measured in the ERP, `GATE_BORN` is in the "
    "products branch's history and its `TAG_ANCHORED_FROM` is not, so a branch 14 "
    "commits behind master carrying 53 REVIEWED files would have gone red for a reason "
    "having nothing to do with whether anybody read it -- D164 in terms (*a check that "
    "tightens never condemns history*) and D145's shape. **BOTH HALVES ARE ASKED AT "
    "ONCE:** the commit that names the tag in prose must PASS, because the rule that "
    "applied when it was made is the loose one; and the commit beside it carrying no tag "
    "at all must be REFUSED BY NAME, because *the rule that existed before the anchor* "
    "is the looser TEST and not an exemption. A replacement that let a divergent branch "
    "off altogether would satisfy the first half and fail this",
)


# **WHAT THE TWO RULES DISAGREE ABOUT, PINNED BY IDENTITY (D169, amended).**
#
# A commit whose message NAMES the tag without carrying it on a line of its own
# is judged one way by the loose rule and the other way by the strict one, so
# this list is exactly what makes where the strict rule starts matter. The
# opening of this file says nothing here mentions the tag without carrying it --
# **and that is the sentence a check now pins, rather than a reader believing
# it.** The Server's copy of this file carried D164's WITHDRAWN claim as prose
# for a day, in a file written after the sweep that took it out of six others.
ONLY_MENTION_THE_TAG = ()

WHOLE = (
    "AND THE COMMITS THE TWO RULES DISAGREE ABOUT ARE EXACTLY THE ONES NAMED IN THIS "
    "FILE -- pinned by identity, never left to a sentence of prose. There are NONE "
    "here, which is what makes where the strict rule starts unobservable to a run, so "
    "the day one lands this goes red rather than the limit going unnoticed",

    "AND THAT ANSWER CHANGES WHEN A COMMIT THAT ONLY MENTIONS THE TAG IS PUT IN FRONT "
    "OF IT -- the `mentions` commit this file already builds, walked instead. The "
    "measurement above had no fault ever put back, and it is the backstop for the one "
    "thing the runner admits it cannot test",
)


# ==================================================== BREAKING IT ON PURPOSE
#
# **EVERY MUTATION IS A REWRITE OF THE TEXT, THEN A RUN.** Not a claim about what
# the text says -- the mutated file is handed to the same parser, the same bash and
# the same git, and what is asked is whether the ONE question that exists to detect
# this fault stops answering correctly -- never whether any of the six above does
# (D175). A mutation that cannot be applied (because the line it
# names is no longer there) RAISES, and the check goes red saying so, rather than
# quietly doing nothing and passing.

class CannotBreakIt(Exception):
    """The fault could not be put back, so nothing was proved by trying."""


def _assignment(text, name, which=0):
    """The whole logical line the workflow assigns that shell name on.

    A continuation line ending in a backslash is part of the same assignment, so
    it is followed rather than cut at the first newline.
    """
    found = list(re.finditer(
        r"^[ \t]*%s=(?:\\\r?\n|[^\n])*\r?\n" % re.escape(name), text, re.M))
    if len(found) <= which:
        raise CannotBreakIt("the workflow has no assignment number %d to %s"
                            % (which + 1, name))
    return found[which]


def _indent(line):
    return re.match(r"[ \t]*", line).group(0)


def a_second_assignment(name, value, which=0, word=""):
    """A second line below the first. Bash runs both and the LAST one wins."""
    def to(text):
        at = _assignment(text, name, which)
        return "%s%s%s%s=%s\n%s" % (text[:at.end()], _indent(at.group(0)),
                                    word, name, value, text[at.end():])
    return to


def the_value_changed(name, value, which=0, word=""):
    def to(text):
        at = _assignment(text, name, which)
        return "%s%s%s%s=%s\n%s" % (text[:at.start()], _indent(at.group(0)),
                                    word, name, value, text[at.end():])
    return to


def the_line_deleted(name, which=0):
    def to(text):
        at = _assignment(text, name, which)
        return text[:at.start()] + text[at.end():]
    return to


def the_text_changed(old, new, expect=1, only=None):
    """A rewrite of something that is not an assignment.

    The count is required BEFORE the rewrite is made. A `replace` that matches
    nothing changes nothing and the check over it then passes a workflow it never
    broke -- a mutation that silently does not apply is the same lie as a check
    that cannot go red.
    """
    def to(text):
        if text.count(old) != expect:
            raise CannotBreakIt("expected %d of %r in the workflow, found %d"
                                % (expect, old[:60], text.count(old)))
        if only is None:
            return text.replace(old, new)
        pieces = text.split(old)
        return old.join(pieces[:only + 1]) + new + old.join(pieces[only + 1:])
    return to


def in_order(*breakings):
    def to(text):
        for one in breakings:
            text = one(text)
        return text
    return to


def the_step_taken_out(name):
    """The whole step, from its `- name:` line to the next step's."""
    def to(text):
        opens = re.search(r"^([ \t]*)- name: %s[ \t]*$" % re.escape(name),
                          text, re.M)
        if opens is None:
            raise CannotBreakIt("there is no step named %r to take out" % name)
        after = re.compile(r"^%s- " % re.escape(opens.group(1)), re.M)
        closes = after.search(text, opens.end())
        return text[:opens.start()] + (text[closes.start():] if closes else "")
    return to


# The exact lines the mutations name, written out once so a mutation that stops
# applying says which line went rather than failing somewhere unreadable.
THE_WALKED_RANGE = 'RANGE="${RANGE:-$BASE..$HEAD}"'
THE_FINAL_WORD = '[ "$MISSING" -eq 0 ] || exit 1'
THE_MERGE_FLAG = "git show -m --pretty=format: --name-only"
NOTHING_TO_TAG = '[ -z "$FILES" ] && continue'
THE_OLD_QUESTION = 'TAG_TEST="$TAG_BEFORE_THAT"'
THE_STRICT_QUESTION = 'TAG_TEST="$TAG_ANCHORED"'

# The lines the harness faults name -- none of them inside a `run:` block.
THE_EMPTY_TREE = '              BASE="$(git hash-object -t tree /dev/null)"\n'
THE_TAG_STEP = "      - name: %s\n" % gate_run.THE_TAG_WALK
THE_JOB_LINE = "  pm-discipline:\n"
THE_JOB_CONDITION = "    if: github.repository_owner == 'kartaan-com'\n"
THE_PUSH_TRIGGER = '  push:\n    branches: [main]\n'

# The root commit: before the hook that writes the tag existed, so nothing
# from here back could ever carry one.
BEFORE_THIS_REPOSITORY_BEGAN = '2a6f6586db32ccae62e35d45df735c94f572b9c4'

# D164 -- the two lines that make the anchored rule a question about a COMMIT
# rather than about a BRANCH. Written out so a mutation that stops applying says
# which line went rather than failing somewhere unreadable.
THE_ANCHOR_RESOLVED = (
    '          ANCHOR="$(git rev-parse --verify "$TAG_ANCHORED_FROM^{commit}")"\n')
THE_PER_COMMIT_TEST = (
    '            if [ "$THIS" != "$ANCHOR" ] && git merge-base --is-ancestor '
    '"$ANCHOR" "$THIS"; then\n'
    '              TAG_TEST="$TAG_ANCHORED"\n'
    '            else\n'
    '              TAG_TEST="$TAG_BEFORE_THAT"\n'
    '            fi\n')
# What it said until 2026-09-03: asked of the commit against the anchor rather
# than the anchor against the commit. It answers "no" for a DIVERGENT branch
# exactly as it does for a newer commit, so every commit on a branch made before
# the anchor was judged by a rule that did not exist when it was written.
THE_TEST_ASKED_BACKWARDS = (
    '            if git merge-base --is-ancestor "$THIS" "$TAG_ANCHORED_FROM" '
    '2>/dev/null; then\n'
    '              TAG_TEST="$TAG_BEFORE_THAT"\n'
    '            else\n'
    '              TAG_TEST="$TAG_ANCHORED"\n'
    '            fi\n')
# The guard that used to sit where the resolve does, and what it cost.
THE_BRANCH_WIDE_GUARD = (
    '          if ! git merge-base --is-ancestor "$TAG_ANCHORED_FROM" HEAD '
    '2>/dev/null; then\n'
    '            echo "::error::the commit the anchored tag rule starts after '
    '($TAG_ANCHORED_FROM) is not an ancestor of HEAD."\n'
    '            exit 1\n'
    '          fi\n')

MATCHES_ANYWHERE = "'" + r"^.*\[PM-REVIEWED\].*$" + "'"
# A commit this history does not reach -- the ERP's own gate commit, which is a
# real commit somewhere and nothing here descends from. Named rather than invented
# so the value is a real forty-character id and not obvious nonsense.
NOT_ON_THIS_LINE = "69d584544d0d74003ba20927b0b20e3d1414893f"

# ==================== WHICH QUESTION EACH FAULT IS CAUGHT BY (D175)
#
# **A FAULT IS CAUGHT BY ITS OWN NAMED QUESTION, NEVER BY ANY QUESTION.** This
# file used to count a fault caught the moment ANY question answered wrong. On a
# pull request GitHub checks out a merge commit of its own making, which carries
# no tag, so the question that walks THIS repository's real history is
# PERMANENTLY wrong there -- and every fault check below then passed while
# testing nothing at all. The report read green and meant nothing.
#
# So each fault names the question that exists to detect it, and counts as caught
# only when THAT question answers wrong. **And a question already wrong on the
# workflow AS WRITTEN can attribute nothing:** the faults naming it are reported
# RED, because a fault "caught" by a question that was going to be wrong anyway is
# not caught. That is this project's own standard -- put a fault back and watch a
# NAMED check go red -- applied at last to the thing that checks the checks.
PASSES_THE_REVIEWED = 0
REFUSES_THE_UNTAGGED = 1
REFUSES_THE_MENTION = 2
REFUSES_THE_MERGE = 3
THE_FIRST_PUSH = 4
THE_OLDER_BRANCH = 5

BREAKINGS = (
    # ---- NOT_CODE: nothing counts as code, so every commit is skipped (round six).
    ("WHAT COUNTS AS CODE, EMPTIED -- an empty pattern makes `grep -v` throw every file "
     "away, so every commit hands the walk an empty list and is skipped. The whole walk "
     "switches off. The same fault put back in the commit hook turns seven checks red; "
     "put back here it left every check in three repositories green (D171)",
     the_value_changed("NOT_CODE", "''"),
     REFUSES_THE_UNTAGGED),
    ("AND WIDENED TO MATCH EVERY FILENAME, which does the same thing and reads as an "
     "ordinary pattern",
     the_value_changed("NOT_CODE", "'.'"),
     REFUSES_THE_UNTAGGED),
    ("AND WITH A SECOND ASSIGNMENT BELOW THE FIRST, which is the form bash actually runs "
     "-- the right line stays in the file, spelled perfectly, and is overwritten",
     a_second_assignment("NOT_CODE", "'.'"),
     REFUSES_THE_UNTAGGED),
    ("AND WITH `export` IN FRONT OF THAT SECOND LINE -- the form that beat the list check "
     "in all three repositories on 2026-09-03, because `export NAME=` is not the shape a "
     "list of `NAME=` lines is looking for and is the same assignment to bash",
     a_second_assignment("NOT_CODE", "'.'", word="export "),
     REFUSES_THE_UNTAGGED),
    ("AND WITH THE LINE TAKEN OUT ALTOGETHER -- unset, not empty: GitHub's default shell "
     "has nounset off, so the pattern expands to nothing and `grep -v` throws every file "
     "away just the same",
     the_line_deleted("NOT_CODE"),
     REFUSES_THE_UNTAGGED),

    # ---- MISSING: the walk finds the untagged commit and passes anyway (round six).
    ("WHETHER ANYTHING WAS MISSING, RESET AFTER THE WALK -- the loop finds the untagged "
     "commit, prints the error naming it, and the reset below throws the answer away. The "
     "run says exactly the right thing and goes green",
     the_text_changed(THE_FINAL_WORD, "MISSING=0\n          " + THE_FINAL_WORD),
     REFUSES_THE_UNTAGGED),
    ("AND THE SAME LINE WITH `export` IN FRONT OF IT",
     the_text_changed(THE_FINAL_WORD, "export MISSING=0\n          " + THE_FINAL_WORD),
     REFUSES_THE_UNTAGGED),
    ("AND WITH THE WALK NO LONGER RECORDING WHAT IT FOUND -- the error is still printed, "
     "naming the commit, and the step exits 0. A gate that says the right thing and passes "
     "anyway is Golden Rule 24 itself",
     the_value_changed("MISSING", "0", which=1),
     REFUSES_THE_UNTAGGED),
    ("AND WITH THAT LINE DELETED RATHER THAN CHANGED",
     the_line_deleted("MISSING", which=1),
     REFUSES_THE_UNTAGGED),
    ("AND WITH THE COUNT IT STARTS FROM EMPTIED -- `[ \"\" -eq 0 ]` is not a false answer, "
     "it is an error, so the step refuses the reviewed commit too. A gate that refuses "
     "everything gets switched off within a week",
     the_value_changed("MISSING", '""'),
     PASSES_THE_REVIEWED),
    ("AND WITH THAT LINE TAKEN OUT ALTOGETHER",
     the_line_deleted("MISSING"),
     PASSES_THE_REVIEWED),
    ("AND WITH THE LAST WORD -- the line that turns what was found into a refusal -- "
     "deleted, so the walk reports and nothing acts on it",
     the_text_changed(THE_FINAL_WORD, ""),
     REFUSES_THE_UNTAGGED),

    # ---- GATE_BORN. Only what a run can see here; see the file's opening note.
    ("WHERE THE RULE STARTS, EMPTIED -- the walk cannot say which commits the rule covers "
     "and must refuse rather than guess",
     the_value_changed("GATE_BORN", '""'),
     PASSES_THE_REVIEWED),
    ("AND WITH THAT LINE TAKEN OUT",
     the_line_deleted("GATE_BORN"),
     PASSES_THE_REVIEWED),
    ("AND POINTED AT A COMMIT THIS HISTORY DOES NOT REACH -- the marker naming something "
     "that is not an ancestor of what is being looked at, which is what a rewritten branch "
     "leaves behind. The walk must refuse rather than carry on with a rule whose starting "
     "point it cannot place",
     the_value_changed("GATE_BORN", NOT_ON_THIS_LINE),
     PASSES_THE_REVIEWED),
    ("AND MOVED BY A SECOND ASSIGNMENT BELOW THE FIRST -- the round-five form, put back "
     "with a value the run can see. A move to a real ancestor cannot be seen here and is "
     "not asserted: every commit this rule reaches already carries the tag, which the last "
     "of the five questions above measures",
     a_second_assignment("GATE_BORN", NOT_ON_THIS_LINE),
     PASSES_THE_REVIEWED),
    ("AND BY A SECOND ASSIGNMENT WITH `export` IN FRONT OF IT",
     a_second_assignment("GATE_BORN", NOT_ON_THIS_LINE, word="export "),
     PASSES_THE_REVIEWED),

    # ---- TAG_ANCHORED: the strict question, loosened back to a substring (round two).
    ("THE STRICT QUESTION, LOOSENED BACK TO MATCHING ANYWHERE IN THE MESSAGE -- the rule "
     "two of Kartaan-Server's commits already walked past once, and the pattern still "
     "reads as anchored at a glance",
     the_value_changed("TAG_ANCHORED", MATCHES_ANYWHERE),
     REFUSES_THE_MENTION),
    ("AND LOOSENED BY A SECOND ASSIGNMENT BELOW THE FIRST",
     a_second_assignment("TAG_ANCHORED", MATCHES_ANYWHERE),
     REFUSES_THE_MENTION),
    ("AND BY A SECOND ASSIGNMENT WITH `export` IN FRONT OF IT",
     a_second_assignment("TAG_ANCHORED", MATCHES_ANYWHERE, word="export "),
     REFUSES_THE_MENTION),
    ("AND WITH THE STRICT PATTERN EMPTIED -- an empty pattern matches every message, so "
     "every commit is tagged",
     the_value_changed("TAG_ANCHORED", "''"),
     REFUSES_THE_UNTAGGED),
    ("AND WITH ITS LINE TAKEN OUT, which leaves the same empty pattern",
     the_line_deleted("TAG_ANCHORED"),
     REFUSES_THE_UNTAGGED),

    # ---- where the strict rule starts.
    ("WHERE THE STRICT RULE STARTS, EMPTIED -- the walk cannot say which commits the "
     "stricter form covers and must refuse rather than guess",
     the_value_changed("TAG_ANCHORED_FROM", '""'),
     PASSES_THE_REVIEWED),
    ("AND WITH THAT LINE TAKEN OUT",
     the_line_deleted("TAG_ANCHORED_FROM"),
     PASSES_THE_REVIEWED),
    ("AND THE LINE THAT RESOLVES IT DELETED ALTOGETHER -- **the marker is untouched, "
     "spelled perfectly, and the anchored rule is off for every commit in the "
     "repository.** `ANCHOR` is then unset, `--is-ancestor \"\" \"$THIS\"` fails for "
     "everything, and every commit falls to the loose side. **THIS FAULT EXISTS "
     "BECAUSE THE LINE WAS ADDED WITHOUT ONE AND THE GAP WAS FOUND BY MEASURING "
     "RATHER THAN BY READING:** the comment beside it claimed it mattered only to an "
     "emptied marker, and measured on 2026-09-03 deleting it alone -- emptying "
     "nothing -- already stopped a mentions-only commit being refused. It is the "
     "`CODE=\"\"` shape of round six, in the line written to close a different hole",
     the_text_changed(THE_ANCHOR_RESOLVED, ""),
     REFUSES_THE_MENTION),

    # ---- D164: THE QUESTION IS ABOUT A COMMIT, NEVER ABOUT A BRANCH.
    ("THE BRANCH-WIDE GUARD PUT BACK -- failing the whole run when the anchor is not an "
     "ancestor of HEAD. **This is not invented: it is what the file said until "
     "2026-09-03**, and measured in the ERP it would have failed a branch 14 commits "
     "behind master carrying 53 REVIEWED files, for a reason having nothing to do with "
     "whether anybody read them. A gate that is red on work nobody can fix is a gate "
     "everybody learns to ignore (D164, D145)",
     the_text_changed(THE_ANCHOR_RESOLVED,
                      THE_ANCHOR_RESOLVED + THE_BRANCH_WIDE_GUARD),
     THE_OLDER_BRANCH),
    ("AND THE PER-COMMIT TEST ASKED BACKWARDS -- the commit against the anchor rather "
     "than the anchor against the commit. It reads as an ordinary tightening and every "
     "line of it is spelled perfectly; what it does is answer `no` for a DIVERGENT "
     "branch exactly as it answers `no` for a newer commit, so work written before the "
     "rule existed is judged by it. The guard above only made that visible by failing "
     "loudly -- **this is the same fault with the noise taken off**",
     the_text_changed(THE_PER_COMMIT_TEST, THE_TEST_ASKED_BACKWARDS),
     THE_OLDER_BRANCH),

    # ---- the shape of the decision, not the words in it (round one).
    ("THE TWO QUESTIONS SWAPPED -- one word, both patterns still in the file spelled "
     "perfectly, and every commit judged by the loose rule again",
     in_order(the_text_changed(THE_OLD_QUESTION, "TAG_TEST=SWAPPED"),
              the_text_changed(THE_STRICT_QUESTION, THE_OLD_QUESTION),
              the_text_changed("TAG_TEST=SWAPPED", THE_STRICT_QUESTION)),
     REFUSES_THE_MENTION),

    # ---- forms nobody had tried before this file existed.
    ("A MERGE SHOWN WITHOUT `-m` -- git then gives a combined diff that omits every "
     "cleanly-merged file, the merge hands the walk an empty file list, and an unreviewed "
     "merge goes through carrying every file it merged",
     the_text_changed(THE_MERGE_FLAG, "git show --pretty=format: --name-only"),
     REFUSES_THE_MERGE),
    ("THE RANGE NARROWED TO NOTHING -- the walk runs, prints nothing, and passes. Every "
     "check over what the walk ASKS is satisfied by a walk with no commits in it",
     the_text_changed(THE_WALKED_RANGE, 'RANGE="${RANGE:-$HEAD..$HEAD}"'),
     REFUSES_THE_UNTAGGED),
    ("THE TEST FOR AN EMPTY FILE LIST INVERTED -- every commit that changes code is "
     "skipped and every one that changes none is asked for a tag",
     the_text_changed(NOTHING_TO_TAG, '[ -n "$FILES" ] && continue'),
     REFUSES_THE_UNTAGGED),
    ("THE WHOLE STEP TAKEN OUT -- the loudest form, and the one a file that is only ever "
     "read is least likely to be asked about",
     the_step_taken_out(gate_run.THE_TAG_WALK),
     REFUSES_THE_UNTAGGED),
    ("AND THE STEP THAT WORKS OUT WHAT CHANGED TAKEN OUT -- the walk is then handed an "
     "empty range. Nothing is wrong with the walk itself and nothing reading it would "
     "notice",
     the_step_taken_out(gate_run.WHAT_CHANGED),
     REFUSES_THE_UNTAGGED),
    # ---- THE FIRST PUSH. Nothing had ever run this path: the sentinel sat in
    # `gate_run.py` unused, and an untested path in the gate is where the last two
    # weeks say the next fault will be.
    ("WHERE THE RULE STARTS, MOVED BACK BEFORE THIS REPOSITORY BEGAN -- to the root "
     "commit, which carries no tag and structurally could not: the hook did not exist "
     "when it was made. The gate then refuses the whole history on every run, for ever. "
     "**A check that is red on the branch permanently is a check everybody learns to "
     "ignore** (D164), and this is the only question that walks far enough back to see "
     "it happen",
     the_value_changed("GATE_BORN", BEFORE_THIS_REPOSITORY_BEGAN),
     THE_FIRST_PUSH),

    # **AND WHY NEITHER FAULT ON THE FIRST-PUSH BRANCH ITSELF IS HERE, said rather
    # than left to be found.** Taking out the empty-tree line leaves `BASE` a row of
    # noughts, so nothing counts as code -- and in the ERP that switches the tag step
    # off, because its step is gated on it. **This repository's step is gated on
    # nothing**, so the walk still runs and still refuses; what breaks is the secret
    # scan, which this file makes no claim about. And taking out the line that widens
    # the range to the whole history changes NOTHING, measured: `git rev-list
    # <tree>..<commit>` walks everything rather than refusing, so the workflow's own
    # comment beside that line -- "a tree cannot be one end of a commit range" -- is
    # not true of `rev-list`. Neither is asserted to be a fault of the tag rule,
    # because neither is.

    # ---- THE HARNESS AROUND THE SHELL (D172, corrected the same day it was set).
    #
    # **NOT ONE OF THESE IS INSIDE A `run:` BLOCK.** Until 2026-09-03 this file ran
    # the shell and GitHub decided whether the shell's answer counted, and the
    # runner never executed that part -- so each of them left the workflow saying
    # "refused" with every check green and the commit landing anyway. They are
    # caught by one guard rather than by the walk: the gate cannot be run at all,
    # and a gate nothing can run is a gate nothing is enforcing.
    ("THE TAG STEP LET OFF -- `continue-on-error: true` on it. The step still fails and "
     "still names the untagged commit, and GitHub marks the job GREEN and takes the "
     "commit. The seventh spelling of one hole, and the first to leave the shell "
     "altogether",
     the_text_changed(THE_TAG_STEP, THE_TAG_STEP + "        continue-on-error: true\n"),
     REFUSES_THE_UNTAGGED),
    ("AND THE WHOLE JOB LET OFF THE SAME WAY -- that no step may fail without failing "
     "the job is a fact about the JOB, so it is asked of the job as well as of every "
     "step in it, wherever the line is put",
     the_text_changed(THE_JOB_LINE, THE_JOB_LINE + "    continue-on-error: true\n"),
     REFUSES_THE_UNTAGGED),
    ("THE JOB GIVEN A CONDITION THAT IS FALSE HERE -- its owner pointed at an account "
     "this repository does not live in. The job is skipped, and GitHub counts a skipped "
     "job a success exactly as it counts a skipped step",
     the_text_changed(THE_JOB_CONDITION,
                      "    if: github.repository_owner == 'not-kartaan-com'\n"),
     REFUSES_THE_UNTAGGED),
    ("AND A CONDITION NOTHING CAN READ -- `&& false` on the end of the real one, which "
     "leaves every character a reader looks for still there. A condition this runner "
     "cannot evaluate is the gate being unrunnable, never one it may quietly assume is "
     "true -- assuming is how a check ends up agreeing with the bug",
     the_text_changed(THE_JOB_CONDITION,
                      THE_JOB_CONDITION.rstrip("\n") + " && false\n"),
     REFUSES_THE_UNTAGGED),
    ("THE PUSH TRIGGER TAKEN OUT OF `on:` -- nothing runs on the push at all. Every "
     "line of the job is untouched and perfectly spelled, and none of it ever runs",
     the_text_changed(THE_PUSH_TRIGGER, ""),
     REFUSES_THE_UNTAGGED),
    ("AND FILTERED TO NO BRANCH AT ALL, which is the same thing said quietly",
     the_text_changed(THE_PUSH_TRIGGER, "  push:\n    branches: []\n"),
     REFUSES_THE_UNTAGGED),
    ("AND FILTERED BY A FORM THIS RUNNER CANNOT READ -- every branch ignored. Not "
     "understood is not the same as harmless, so it is refused rather than waved "
     "through",
     the_text_changed(THE_PUSH_TRIGGER, "  push:\n    branches-ignore: ['**']\n"),
     REFUSES_THE_UNTAGGED),
)


# ============================================================== ASKING THEM ALL

WORKFLOW_AS_WRITTEN = gate_run.the_workflow()

_WHY = "[PM-REVIEWED]"


def _names(verdict, sha):
    """Whether the gate said which commit AND why, on one line."""
    return any(sha in line and _WHY in line for line in verdict.said.splitlines())


class Question:
    def __init__(self, base, head, refuse, name=None, never_name=None):
        self.base, self.head = base, head
        self.refuse, self.name, self.never_name = refuse, name, never_name

    def answered_right_by(self, text, where):
        try:
            said = gate_run.run_the_gate(text, where, self.base, self.head)
        except (gate_run.GateGone, OSError):
            # The gate could not be run. That is never a pass: a workflow nothing
            # can run is a workflow nothing is enforcing -- and it is how the
            # harness faults are caught, since none of them is in the shell.
            return False
        if said.refused != self.refuse:
            return False
        if not said.walked:
            return False
        if self.name and not _names(said, self.name):
            return False
        if self.never_name and _names(said, self.never_name):
            return False
        return True


class CannotAsk(Question):
    """A question whose fixture could not be built. Never a pass.

    **A QUESTION THAT CANNOT BE ASKED IS REPORTED RED, NEVER SKIPPED.** Skipping
    it would take a name off the report and the count would move with it, which
    is the silent-check failure this whole file exists to make impossible.
    """

    def __init__(self, why):
        Question.__init__(self, None, None, refuse=False)
        self.why = why

    def answered_right_by(self, text, where):
        print("    (%s)" % self.why)
        return False


def _only_mention_the_tag(where, tip):
    """Commits reachable from `tip` that name the tag but do not carry it alone.

    **A NAMED COMMIT, NEVER `HEAD`.** This walked `HEAD` in the probe clone until
    2026-09-03, and every run above moves `HEAD` to the commit it is asking about
    -- so the answer depended on which question happened to fail first and on the
    order the faults happen to be written in. Measured: with `HEAD` left on the
    untagged probe commit it passed, and left on the one that merely mentions the
    tag it failed, naming a commit this file had invented itself.
    """
    ran = subprocess.run(
        ["git", "log", "--format=%H%x00%B%x00%x00", tip],
        cwd=str(where), env=gate_run.no_pointers_to_here(),
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if ran.returncode != 0:
        return None
    found = []
    for one in ran.stdout.split("\x00\x00"):
        if "\x00" not in one:
            continue
        sha, _, body = one.partition("\x00")
        if _WHY in body and not re.search(r"^\[PM-REVIEWED\][ \t]*$", body, re.M):
            found.append(sha.strip())
    return tuple(sorted(found))


# **AND THE HARNESS LEAVES NOTHING BEHIND (D178).** Named here with the rest, so
# that it is reported red rather than silently skipped when the history could not
# be made at all.
TAKEN_AWAY = (
    "THE THROWAWAY CLONE IS REALLY TAKEN AWAY, AND THIS SAYS SO WHEN IT IS NOT -- "
    "`ignore_errors=True` left TWENTY-EIGHT of them in the temporary folder, because git writes "
    "its objects read-only and a read-only file refuses to be deleted. It does not try harder; "
    "it stops asking. **A tool that breaks things on purpose and cannot clean up after itself "
    "is not the one to trust with a throwaway clone** (D178)",
)

# **THE ANCHOR IS READ OUT OF THE WORKFLOW, NEVER WRITTEN DOWN TWICE.** The
# divergent-branch fixture is built from the anchor's own parent, so a second copy
# of the value here would go stale the day the marker moves and the fixture would
# quietly stop being divergent at all -- a check testing the wrong thing while
# staying green. Where it cannot be found, the fixture is not built and the
# question over it goes red saying so.
_ANCHOR_IN_THE_FILE = re.search(r"TAG_ANCHORED_FROM=([0-9a-f]{40})",
                                WORKFLOW_AS_WRITTEN)

_WENT = None
_holder = None
try:
    _holder = Path(tempfile.mkdtemp(prefix=gate_run.TEMP_PREFIX))
    history = gate_run.History(
        _holder, anchor=_ANCHOR_IN_THE_FILE and _ANCHOR_IN_THE_FILE.group(1))
except Exception as could_not:
    history = None
    print("the history could not be made: %s" % could_not)

if history is None:
    for _name in ASKED + tuple(one[0] for one in BREAKINGS) + WHOLE:
        check(_name, False)
else:
    try:
        QUESTIONS = (
            Question(history.base, history.tagged, refuse=False),
            Question(history.base, history.untagged, refuse=True,
                     name=history.untagged, never_name=history.tagged),
            Question(history.base, history.mentions, refuse=True,
                     name=history.mentions, never_name=history.tagged),
            Question(history.base, history.merged, refuse=True,
                     name=history.merged, never_name=history.merged_parents[0]),
            # **THE FIRST PUSH, AND NOTHING HAD EVER RUN THAT PATH.** GitHub sends
            # a row of noughts as `before`, and the workflow answers with the empty
            # tree and a range of HEAD alone -- the whole history in a single walk.
            # Every commit the rule reaches must pass it.
            Question(gate_run.NOTHING_CAME_BEFORE, history.base, refuse=False),
            # **A BRANCH THAT STARTED BEFORE THE ANCHOR (D164).** Both halves in
            # one question, so neither can be satisfied on its own: the commit
            # naming the tag in prose must PASS, and the commit beside it with no
            # tag at all must be REFUSED **and named**, while the first is NOT
            # named. Put the branch-wide guard back and the refusal stops naming
            # the right commit; ask the per-commit test backwards and the prose
            # commit starts being named; exempt the branch altogether and nothing
            # is refused at all. Three ways of getting it wrong, one question.
            Question(history.off_branch, history.off_untagged, refuse=True,
                     name=history.off_untagged, never_name=history.off_mentions)
            if history.off_branch else
            CannotAsk("the anchor could not be read out of the workflow, so no "
                      "branch starting before it could be built"),
        )
        # ---- the questions, of the workflow as it stands. **WHETHER EACH ONE
        # ANSWERED RIGHT IS KEPT**, because a question that is already wrong here
        # can attribute nothing below it (D175).
        ANSWERED = []
        for _i, _name in enumerate(ASKED):
            ANSWERED.append(QUESTIONS[_i].answered_right_by(
                WORKFLOW_AS_WRITTEN, history.where))
            check(_name, ANSWERED[_i])

        # ---- and every fault, judged by ITS OWN question and by no other (D175).
        for _name, _breaking, _which in BREAKINGS:
            try:
                _broken = _breaking(WORKFLOW_AS_WRITTEN)
            except CannotBreakIt as why:
                print("    (could not put the fault back: %s)" % why)
                check(_name, False)
                continue
            if not ANSWERED[_which]:
                print("    (question %d is already wrong on the workflow as "
                      "written, so it can attribute nothing)" % (_which + 1))
                check(_name, False)
                continue
            check(_name, not QUESTIONS[_which].answered_right_by(
                _broken, history.where))

        # ---- and the one thing the runner cannot see: measured, pinned, and then
        # broken with the fixture already sitting in this file.
        check(WHOLE[0], _only_mention_the_tag(history.where, history.base)
              == ONLY_MENTION_THE_TAG)
        _with_one_in_front = _only_mention_the_tag(history.where, history.mentions)
        check(WHOLE[1], _with_one_in_front is not None
              and history.mentions in _with_one_in_front)
    finally:
        _WENT = gate_run.take_it_away(_holder)

if _holder is not None and _WENT is None:
    _WENT = gate_run.take_it_away(_holder)
check(TAKEN_AWAY[0], _WENT is not False)


EXPECTED = len(ASKED) + len(BREAKINGS) + len(WHOLE) + len(TAKEN_AWAY)
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures
      else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
