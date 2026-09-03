"""Runs the review-tag gate the way GitHub runs it, against a history made here.

**WHY THIS FILE EXISTS (D172).** Six rounds of independent review each closed the
spelling of the hole it was shown, and the next round found another spelling: a
second assignment below the first, then `export` in front of it, then variables
nobody had pinned at all -- `CODE` emptied so nothing counts as code and the walk
switches itself off, `MISSING` set to nought so it finds untagged commits and
passes anyway. There is no last spelling. A check that READS the workflow has to
guess which forms a future author might write, and is wrong the moment somebody
writes a new one.

**SO THE QUESTION CHANGES.** Not *is the file spelled the way we remember*, but
*does this file refuse an unreviewed commit*. That question cannot be defeated by
a spelling, because the spelling is executed rather than matched -- which is
D170's rule ("a check asks a question; it does not match a surface") applied to
the file D171 says every hole this week has lived in: the one that is only ever
read.

**AND THE SHELL IS NOT THE WHOLE GATE (D172, corrected the same day it was
written).** Running the shell is necessary and NOT sufficient.
`continue-on-error: true` on the tag step leaves the step failing and still
naming the untagged commit, and GitHub marks the job GREEN and the commit
lands. Taking `push:` out of `on:`, and an `if` on the job that cannot be true,
do the same. **None of the three is inside a `run:` block**, so a runner that
executes the shell and nothing else sees none of them -- the harness around the
shell decides whether the shell's answer counts. So the YAML is asked a question
of its own, as STRUCTURE rather than as text: does this job run on a push, can
anything switch it off, and may any step fail without failing the job. That is
`nothing_can_switch_it_off` below.

**WHAT IT RUNS AND WHAT IT DOES NOT.** Two steps of `pm_check.yml`: the one that
works out what changed, and the one that walks the commits for the review tag.
They are the pair the tag rule lives in -- the first decides whether the second
runs at all, which is where `CODE` matters. The rest of the workflow (the secret
scan, the board, the node and python checks) enforces other rules and is checked
elsewhere; this file makes no claim about it.

**NOTHING HERE IS REMEMBERED ABOUT THE FILE.** The steps are found by name in
YAML parsed by a real YAML parser; the shell is run by real bash; the history is
real git. Where this runner meets something it was not built to understand -- a
step that has gone, an expression it has no value for, a condition in a form it
cannot evaluate -- it RAISES rather than guessing, and the caller counts a raise
as the gate being unrunnable, which is a refusal. Guessing is how a check ends up
agreeing with the bug it was written to catch.
"""

import io
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "pm_check.yml"
TEMP_PREFIX = "kartaan-gate-run-"

# The account the gate protects something in. One of the three repositories
# deliberately scopes its job to this owner -- D36 copies that repository into
# every seller's GitHub account, where these checks cannot possibly pass -- so
# the job's own condition is EVALUATED here rather than assumed away.
THE_OWNER = "kartaan-com"

# The two steps, by the names they carry in the file.
WHAT_CHANGED = "Determine what changed"
THE_TAG_WALK = "Every code commit carries the review tag"

# GitHub's default shell for a `run:` step on a Linux runner is `bash -e {0}`:
# errexit ON, pipefail OFF, nounset OFF. All three matter here -- `|| true` on the
# end of a pipeline is load-bearing in this workflow, and an unset variable expands
# to nothing rather than stopping the script, which is what makes a DELETED
# assignment behave differently from an emptied one. Anything else would be a
# different shell answering a different question.
HOW_GITHUB_RUNS_IT = ("-e",)

BASH = shutil.which("bash")


class GateGone(Exception):
    """The gate could not be run at all, so nothing it might have said counts."""


# What GitHub calls the event when the checkout is a pull request's.
A_PULL_REQUEST = "pull_request"


def take_it_away(where):
    """Take a throwaway folder away, and say whether it really went (D178).

    **`ignore_errors=True` IS WHAT LEFT TWENTY-EIGHT CLONES IN THE TEMPORARY
    FOLDER.** It does not try harder; it stops asking.

    **AND THE REASON IT FAILS WAS MEASURED, NOT ASSUMED.** The obvious guess is
    the read-only bit git puts on every object it writes; that is real and is
    cleared below. But what the leftovers actually reported is `WinError 32`, the
    folder still being held by a process -- git on Windows lets go a moment after
    it exits. So the answer is to clear the bit, wait, and ask again.

    **AND NEITHER RAISES NOR IGNORES.** Whether the folder is gone is RETURNED:
    the file that made it asks, and reports red if it is still there. Raising here
    would be worse than ignoring -- this is called from a `finally`, where it
    would replace whatever went wrong with itself.
    """
    def make_it_writable(action, name, _):
        os.chmod(name, stat.S_IWRITE)
        action(name)

    for attempt in range(5):
        if not Path(where).exists():
            return True
        try:
            shutil.rmtree(where, onerror=make_it_writable)
        except OSError:
            time.sleep(0.2 * (attempt + 1))
    return not Path(where).exists()


def the_line_of_history_here():
    """The commit this repository's own history actually reaches.

    **ON A PULL REQUEST GITHUB CHECKS OUT A MERGE COMMIT OF ITS OWN MAKING**, of
    the branch into the base, carrying no review tag and belonging to no branch;
    it exists for the run and is thrown away. Every question below about *the
    commits already in this repository* is then asked about a commit that is not
    in this repository, and answers wrong -- which turned every pull request red.

    **THAT IS A KNOWN CONTEXT, NOT A FAULT, AND D175 SAYS WHAT TO DO WITH ONE:**
    recognise it, rather than let a permanently wrong answer poison every case.
    The recognition is not to excuse the question -- it is to ask it of the right
    commit. On a pull request the repository's own history is the branch the
    request is against, which is the FIRST PARENT of the commit GitHub made.

    **TWO CONDITIONS, AND EACH IS FOR SOMETHING.** GitHub's own event name says
    the context; that HEAD really is a merge says the checkout is the merge ref
    rather than the branch head, which `actions/checkout` can be told to take
    instead. Either one alone would be a guess.

    **AND THE WORKFLOW UNDER TEST IS STILL THE ONE IN THE CHECKOUT** -- the pull
    request's own version of `pm_check.yml`, read from the working tree. Only the
    HISTORY the probe commits sit on comes from the branch, because that is what
    "already in this repository" means.
    """
    def ask(*argv):
        ran = subprocess.run(["git", *argv], cwd=str(ROOT),
                             env=no_pointers_to_here(), capture_output=True,
                             text=True, encoding="utf-8", errors="replace")
        if ran.returncode != 0:
            raise GateGone("git could not answer `git %s` about this repository: %s"
                           % (" ".join(argv), ran.stderr.strip()[:200]))
        return ran.stdout

    here = ask("rev-parse", "HEAD").strip()
    if os.environ.get("GITHUB_EVENT_NAME") != A_PULL_REQUEST:
        return here
    said = ask("rev-list", "--parents", "-n1", here).split()
    if len(said) != 3:
        return here
    return said[1]


def the_workflow():
    """The file as the runner that runs it would see it.

    **ENDINGS NORMALISED, AND THAT IS FAITHFUL RATHER THAN CONVENIENT.**
    GitHub's Linux runner always gets Unix endings, and bash will not run a script
    whose lines end with a carriage return -- so reading this file any other way
    would ask the question of a file GitHub never sees.

    **AND WHAT IS ON DISK HERE IS NOT THE SAME QUESTION IN ALL THREE REPOSITORIES.**
    This said `.gitattributes` sets `* text=auto`; measured 2026-09-03, **only
    Kartaan-ERP has that file. Kartaan-Server and Kartaan-AutoSync have none**, so
    a checkout there keeps whatever endings each file was written with. A comment
    carried between repositories describing a file that is not in two of them is
    D169's fault in its smallest form. Normalising here is right either way, and
    for the reason above rather than because of any file.
    """
    return WORKFLOW.read_bytes().decode("utf-8").replace("\r\n", "\n")


def _yaml():
    """The real YAML parser, or a refusal.

    **NOT HAND-PARSED.** Reaching into a YAML file with regular expressions to pull
    out a block scalar is the exact fault this file replaces: it matches a surface.
    If PyYAML is not installed the answer is that the gate could not be run -- never
    a home-made parser that agrees with itself.
    """
    try:
        import yaml
    except ImportError as absent:
        raise GateGone("PyYAML is not installed, so the workflow cannot be parsed "
                       "as YAML: %s" % absent)
    return yaml


def the_job(workflow_text):
    """The whole document, and the job the tag walk lives in."""
    doc = _yaml().safe_load(workflow_text)
    jobs = (doc or {}).get("jobs") or {}
    holding = [job for job in jobs.values()
               if any((step or {}).get("name") == THE_TAG_WALK
                      for step in (job or {}).get("steps") or [])]
    if len(holding) != 1:
        raise GateGone("%d jobs in the workflow carry a step named %r -- expected "
                       "exactly one" % (len(holding), THE_TAG_WALK))
    return doc, holding[0]


def no_pointers_to_here():
    """The environment with every pointer git hands its hooks taken out.

    **EVERY `GIT_` NAME, NOT A LIST OF THEM.** A list has to be kept level with
    git's own, and the day it falls behind, the clone and the commits below are
    aimed at the REAL repository whatever their working directory says -- which on
    2026-08-31 wiped the index and left `bare = true` behind. Sweeping the prefix
    cannot fall behind.
    """
    return {name: value for name, value in os.environ.items()
            if not name.startswith("GIT_")}


THE_EXPRESSIONS = re.compile(r"\$\{\{(.*?)\}\}", re.S)


def _value_of(name, values):
    """What GitHub would put here, or a refusal.

    **A MISSING STEP OUTPUT IS AN EMPTY STRING, NOT AN ERROR.** That is what
    GitHub does, and it is the whole point of one of the faults below: take the
    step that works out the range away and the walk is handed nothing to walk,
    quietly. Refusing to guess here would model a stricter runner than the real
    one and let a real hole go unmeasured. Anything ELSE this runner has no value
    for is a refusal, because guessing is how a check ends up agreeing with the
    bug it was written to catch.
    """
    if name in values:
        return values[name]
    if name.startswith("steps."):
        return ""
    raise GateGone("the workflow uses `%s` and this runner has no value for it"
                   % name)


def _fill_in(script, values):
    return THE_EXPRESSIONS.sub(
        lambda found: _value_of(found.group(1).strip(), values), script)


# One term of a condition: a context value compared with a quoted word, with `||`
# between terms. **NOTHING ELSE IS UNDERSTOOD, AND THAT IS THE POINT.** `if: false`
# and `if: <something true> && false` are both conditions this runner cannot
# evaluate, and a condition it cannot evaluate is the gate being unrunnable --
# never a condition it may quietly assume is true.
ONE_CONDITION = re.compile(r"^([A-Za-z0-9_.\-]+) == '([^']*)'$")


def _condition_holds(expression, values):
    """Whether GitHub would run this. A form not understood is a refusal."""
    if expression is None:
        return True
    for part in str(expression).split("||"):
        said = ONE_CONDITION.match(part.strip())
        if said is None:
            raise GateGone("the condition %r is in a form this runner cannot "
                           "evaluate" % (expression,))
        name, wanted = said.groups()
        # A step that never ran has no outputs, and GitHub reads a missing one as
        # the empty string rather than as an error -- so taking the earlier step
        # out SKIPS this one and the run goes green. Modelled the way GitHub does
        # it, not the way it ought to be: the whole point is what really happens.
        if _value_of(name, values) == wanted:
            return True
    return False


def nothing_can_switch_it_off(doc, job, values):
    """Whether GitHub would let the shell's answer count. A no is the gate gone.

    **THE QUESTION, IN ONE SENTENCE: if the step says refused, does the run go red
    and the commit stop?** Running the shell answers only half of that, and D172
    was corrected the same day it was written for saying otherwise. Three lines
    switch the gate off without changing a character of shell:

    * `continue-on-error: true` on the step -- it still fails, still names the
      untagged commit, and GitHub marks the job GREEN and takes the commit.
    * `push:` taken out of `on:` -- nothing runs on the push at all.
    * an `if` on the job that cannot be true -- the job is skipped, and GitHub
      counts a skipped job as a success.

    **NONE OF THE THREE IS INSIDE A `run:` BLOCK.** They are asked here as
    STRUCTURE -- what the document MEANS, never whether some text appears in it
    (D170). The file already raised for a step naming its own shell; this is that
    guard extended to the rest of the harness, which it never was.

    **AND IT IS THE WHOLE JOB, NOT ONLY THE TWO STEPS THAT ARE RUN.** "No step may
    fail without failing the job" is a fact about the job, and a step let off in
    the middle of it is the same hole wherever it sits.
    """
    # `on` is a YAML 1.1 boolean, so a real parser hands this key back as True.
    # Both spellings are read, because a quoted "on" is the same document.
    on = doc.get("on", doc.get(True))
    if not isinstance(on, dict) or "push" not in on:
        raise GateGone("the workflow does not run on a push, so nothing this job "
                       "says can stop a commit reaching the branch")
    push = on["push"]
    if push is not None:
        # A branch filter is allowed -- two of the three repositories name their
        # branch -- but only in the one shape this runner can read. **WHICH
        # branches are named is not asked here**, said plainly rather than left to
        # be discovered: that would need the runner to know which branch this
        # checkout is for, and on a pull request GitHub does not check out a
        # branch at all.
        if not isinstance(push, dict) or set(push) - {"branches"}:
            raise GateGone("the push trigger is filtered in a form this runner "
                           "cannot read: %r" % (push,))
        if not isinstance(push.get("branches"), list) or not push["branches"]:
            raise GateGone("the push trigger names no branch to run on: %r"
                           % (push,))
    if "if" in job and not _condition_holds(job["if"], values):
        raise GateGone("the job's own condition %r is not true for a push to this "
                       "repository, so the job is skipped -- and GitHub counts a "
                       "skipped job as a success" % (job["if"],))
    for whose, holder in ([("the job", job)] +
                          [("the step %r" % (step or {}).get("name"), step or {})
                           for step in job.get("steps") or []]):
        let_off = holder.get("continue-on-error", False)
        if let_off is not False:
            raise GateGone("%s carries `continue-on-error: %r`, so it may fail "
                           "without failing the job -- its answer is printed and "
                           "thrown away" % (whose, let_off))


def _outputs_written(where):
    written = {}
    for line in where.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if "=" not in line:
            raise GateGone("a step wrote %r to GITHUB_OUTPUT, which is not the "
                           "name=value form this runner reads" % line)
        name, _, value = line.partition("=")
        written[name] = value
    return written


class Verdict:
    """What the gate did: whether it refused, what it said, and whether it walked."""

    def __init__(self, refused, said, walked):
        self.refused = refused
        self.said = said
        self.walked = walked

    def named(self, sha):
        return sha in self.said

    def __repr__(self):
        return "<Verdict refused=%s walked=%s>" % (self.refused, self.walked)


def run_the_gate(workflow_text, where, base, head):
    """Run the two steps against a real repository, as a push of base..head.

    Answers with a Verdict. `refused` is true when a step exited non-zero, which is
    what turns a GitHub run red. A step whose condition is false is SKIPPED, and
    GitHub counts a skipped step as a success -- so the gate not running is a PASS,
    which is exactly the shape of the `CODE` hole and has to be modelled rather
    than smoothed over.
    """
    if BASH is None:
        raise GateGone("there is no bash on this machine to run the workflow with")

    values = {
        "github.event_name": "push",
        "github.event.before": base,
        "github.sha": head,
        "github.repository_owner": THE_OWNER,
        # Substituted by GitHub before bash sees the script. On a push these are
        # empty, and the branch that reads them is not taken.
        "github.event.pull_request.head.sha": "",
        "github.event.pull_request.base.sha": "",
    }
    doc, job = the_job(workflow_text)
    # **ASKED BEFORE A LINE OF SHELL IS RUN.** If the harness would not let
    # the answer count, there is no point in having one.
    nothing_can_switch_it_off(doc, job, values)
    said = []
    walked = False
    holder = Path(tempfile.mkdtemp(prefix=TEMP_PREFIX))
    try:
        # **HEAD IS PUT WHERE GITHUB WOULD HAVE PUT IT.** Two guards in the walk
        # ask about `HEAD` itself rather than about the range -- is the commit the
        # rule starts at an ancestor of what we are looking at -- and on a runner
        # HEAD is the pushed commit. Left wherever the last branch was made, those
        # two would be asked about a commit GitHub never checked out.
        #
        # Moved without touching the working tree: the steps only read history, and
        # checking out three hundred files for each of sixty runs would cost more
        # than the whole rest of this file.
        #
        # **AND WHETHER IT WORKED IS ASKED.** This was the one subprocess in this
        # file outside `_must`, in a file whose opening says it RAISES rather than
        # guesses. It is harmless only while `HEAD` already happens to sit on a
        # descendant, so the two ancestry guards answer the same either way --
        # **which is exactly why a failure here would never have been noticed.**
        # A move that did not happen leaves every question below asked of the
        # wrong commit, and answered confidently.
        moved = subprocess.run(
            ["git", "update-ref", "--no-deref", "HEAD", head],
            cwd=str(where), env=no_pointers_to_here(),
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if moved.returncode != 0:
            raise GateGone("HEAD could not be moved to %s in the throwaway "
                           "repository, so every question below would be asked "
                           "of the wrong commit: %s"
                           % (head[:12], (moved.stdout + moved.stderr).strip()[:200]))
        for step in job.get("steps") or []:
            name = (step or {}).get("name")
            if name not in (WHAT_CHANGED, THE_TAG_WALK):
                continue
            if "shell" in step:
                raise GateGone("the step %r names its own shell; this runner only "
                               "models GitHub's default" % name)
            if "run" not in step:
                raise GateGone("the step %r has no script to run" % name)
            if not _condition_holds(step.get("if"), values):
                said.append("(GitHub would SKIP the step %r, and count it a "
                            "success)" % name)
                continue
            script = holder / "step.sh"
            io.open(script, "w", encoding="utf-8", newline="\n").write(
                _fill_in(step["run"], values))
            wrote = holder / "outputs"
            wrote.write_text("", encoding="utf-8")
            env = no_pointers_to_here()
            env["GITHUB_OUTPUT"] = str(wrote).replace("\\", "/")
            ran = subprocess.run(
                [BASH, *HOW_GITHUB_RUNS_IT, str(script).replace("\\", "/")],
                cwd=str(where), env=env, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
            )
            said.append(ran.stdout + ran.stderr)
            if name == THE_TAG_WALK:
                walked = True
            if ran.returncode != 0:
                return Verdict(True, "\n".join(said), walked)
            if step.get("id"):
                for key, value in _outputs_written(wrote).items():
                    values["steps.%s.outputs.%s" % (step["id"], key)] = value
        return Verdict(False, "\n".join(said), walked)
    finally:
        take_it_away(holder)


# ============================================== A HISTORY TO ASK THE GATE ABOUT
#
# **REAL COMMITS IN A REAL REPOSITORY, NOT A STAND-IN FOR ONE.** Every expensive
# fault on this project has run the same way -- a stand-in less capable than the
# thing it stood in for, agreeing with the bug (D167). The gate asks git about
# ancestry, about merge parents and about message bodies, so it is given git.
#
# **AND IT IS A CLONE OF THIS REPOSITORY, not a fresh one.** The walk begins by
# refusing outright unless the commit that created the gate is an ancestor of
# HEAD, so a history that does not contain it makes every question below answer
# "refused" for a reason that has nothing to do with the tag -- four vacuous
# checks that could never go green, which is the same lie as one that can never
# go red.
THE_PROBE = "gate-probe"
TAGGED = "[PM-REVIEWED]"
# What GitHub really sends as `before` when a branch has no previous commit.
NOTHING_CAME_BEFORE = "0" * 40


class History:
    """A clone of this repository with four commits put on top of it.

    tagged      -- carries the tag on a line of its own. The gate must PASS it.
    untagged    -- carries no tag at all. The gate must REFUSE it, by name.
    mentions    -- names the tag in an ordinary sentence and nowhere else. The
                   gate must REFUSE it: that is the bug D164 caught in the act,
                   where the hook read its own name in the author's prose.
    merged      -- an untagged MERGE commit whose files merge cleanly. The gate
                   must REFUSE it. Without `-m` git shows a combined diff that
                   omits every cleanly-merged file, so the merge presents an
                   empty file list and is skipped as though it carried no code.

    **THE BAD ONES SIT ON TOP OF THE GOOD ONE, DELIBERATELY.** Every range asked
    about below therefore holds a commit that must pass and one that must not, so
    a refusal has to NAME the right commit rather than merely happening. A gate
    that refuses everything is as broken as one that refuses nothing, and asked of
    a range holding only the bad commit, the two look identical.
    """

    def __init__(self, holder, anchor=None):
        self.where = Path(holder) / "history"
        here = the_line_of_history_here()
        # `--shared` rather than a copy. A hardlink clone cannot cross drives on
        # Windows, and a full copy of this repository takes thirty seconds every
        # run. The clone only ever READS the real object store -- every object it
        # writes goes in its own -- and it is deleted at the end.
        #
        # **AND `--no-checkout`, THEN THE COMMIT BY NAME.** On GitHub a pull
        # request is checked out DETACHED, at a merge commit no branch points at,
        # so a plain clone has no HEAD to follow and hands back an empty tree --
        # every question below would then be asked of a repository with no history
        # in it. Named explicitly, the commit is found through the shared object
        # store whether or not a ref reaches it.
        self._must(["git", "clone", "--shared", "--no-checkout", "--quiet",
                    str(ROOT), str(self.where)], Path.cwd())
        self._must(["git", "checkout", "--detach", "--quiet", here], self.where)
        # **NOT THIS MACHINE'S HOOKS.** `core.hooksPath` is an ordinary global git
        # setting, and where one is set the commits below would run the real gate
        # from inside the checks that are testing it.
        self.nohooks = self.where / ".git" / "nohooks"
        self.nohooks.mkdir()
        self.base = self._said(["git", "rev-parse", "HEAD"])

        self.tagged = self._commit(
            "tagged", self.base, "a.js",
            "probe: a commit somebody reviewed\n\n%s\n" % TAGGED)
        self.untagged = self._commit(
            "untagged", self.tagged, "b.js",
            "probe: a commit nobody reviewed\n")
        self.mentions = self._commit(
            "mentions", self.tagged, "c.js",
            "probe: a commit whose message talks about the %s tag in a sentence, "
            "the way D164's two commits did, and carries it nowhere\n" % TAGGED)

        side = self._commit(
            "side", self.base, "d.js",
            "probe: the branch being merged in\n\n%s\n" % TAGGED)
        first = self._commit(
            "merged", self.base, "e.js",
            "probe: so the merge below cannot fast-forward\n\n%s\n" % TAGGED)
        self._must(["git", "-c", "user.name=probe", "-c", "user.email=probe@probe",
                    "-c", "core.hooksPath=%s" % str(self.nohooks).replace("\\", "/"),
                    "merge", "--no-ff", "-q", "-m",
                    "probe: an unreviewed merge, whose files merge cleanly", side],
                   self.where)
        self.merged = self._said(["git", "rev-parse", "HEAD"])
        self.merged_parents = (first, side)

        # ------------------- A BRANCH THAT STARTED BEFORE THE ANCHOR (D164)
        #
        # **THE SHAPE THAT WAS FAILING REAL WORK.** Measured in the ERP: its
        # `GATE_BORN` is in the products branch's history and its
        # `TAG_ANCHORED_FROM` is NOT, so a branch 14 commits behind master with 53
        # reviewed files would have failed CI for a reason having nothing to do
        # with whether anybody read it. **D164: a check that tightens names the
        # commit it starts from, and it NEVER condemns history.**
        #
        # **BUILT FROM THE ANCHOR'S OWN PARENT, not from `base~1`.** The anchor is
        # today's tip only until the next commit lands; derived from the anchor
        # itself, this stays the right fixture whatever else arrives. Where the
        # anchor has no parent, `_must` raises and the checks over it go red saying
        # so, rather than quietly testing the wrong thing.
        #
        # **TWO COMMITS ON IT, AND BOTH ARE THE POINT.** The looser question is
        # still a question:
        #
        # off_mentions  -- names the tag in a sentence only. Its history does not
        #                  contain the anchor, so the rule that applied when it was
        #                  made is the rule it is asked, and it must PASS.
        # off_untagged  -- carries no tag at all. It must be REFUSED, BY NAME, even
        #                  here -- because "the rule that existed before the anchor"
        #                  is the loose tag test, NOT an exemption. A replacement
        #                  that let a divergent branch off altogether would satisfy
        #                  the first of these and fail this one.
        self.off_branch = None
        if anchor:
            before = self._said(["git", "rev-parse", "%s^1" % anchor])
            self.off_mentions = self._commit(
                "off-mentions", before, "f.js",
                "probe: reviewed work on a branch made BEFORE the anchor, whose "
                "message talks about the %s tag in a sentence and carries it "
                "nowhere\n" % TAGGED)
            self.off_untagged = self._commit(
                "off-untagged", self.off_mentions, "g.js",
                "probe: work on that same branch with no tag anywhere at all\n")
            self.off_branch = before

    # ------------------------------------------------------------------ plumbing
    def _must(self, argv, cwd):
        ran = subprocess.run(argv, cwd=str(cwd), env=no_pointers_to_here(),
                             capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
        if ran.returncode != 0:
            raise GateGone("%s failed: %s" % (" ".join(argv[:3]),
                                              (ran.stdout + ran.stderr)[:400]))
        return ran

    def _said(self, argv):
        return self._must(argv, self.where).stdout.strip()

    def _commit(self, branch, parent, name, message):
        """One real commit on its own branch, with its message written to a file.

        **THE MESSAGE GOES IN A FILE, NEVER IN AN ARGUMENT.** A multi-line value
        handed to a Git-for-Windows tool as an argument comes back changed -- the
        same class of fault as the pattern whose backslashes were eaten, which
        left a check red on correct code and green on the fault.
        """
        self._must(["git", "checkout", "-q", "-B", "%s/%s" % (THE_PROBE, branch),
                    parent], self.where)
        (self.where / ("%s-%s.js" % (THE_PROBE, name))).write_text(
            "// %s\n" % branch, encoding="utf-8")
        self._must(["git", "add", "-A"], self.where)
        note = self.where / ".git" / "probe-message"
        io.open(note, "w", encoding="utf-8", newline="\n").write(message)
        self._must(["git", "-c", "user.name=probe", "-c", "user.email=probe@probe",
                    "-c", "core.hooksPath=%s" % str(self.nohooks).replace("\\", "/"),
                    "commit", "-q", "-F", str(note)], self.where)
        return self._said(["git", "rev-parse", "HEAD"])
