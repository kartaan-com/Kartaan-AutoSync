# A COPY of Kartaan-ERP/tools/prove_checks.py (private repo), made public for the GitHub proving run (PV1). Changed only with the ERP file; PROVER-SHA256.txt holds the hash of every line below this one.
#!/usr/bin/env python3
"""Prove that the checks can actually FAIL.

    python tools/prove_checks.py            every source file that has checks
    python tools/prove_checks.py --changed  only what this commit touches
    python tools/prove_checks.py --only src/modules/items/items.js

WHY THIS EXISTS, and it is the most expensive lesson on this project.

"A check that cannot fail" has been the top finding of THIRTEEN review cycles.
Every other repeat offender is downstream of it: nothing catches the weak check,
so the next fix goes in unproven, and an independent reviewer finds it a cycle
later. Twenty-three cycles, and the worst finding has been inside the previous
cycle's fixes every single time.

The habit that works is: take the fix out, watch a check go red. That is a
mechanical act, and this does it -- for every line, every time, instead of for
whichever fix somebody remembered to prove.

HOW IT WORKS. For each source file it makes small, deliberate changes to a COPY
of the code -- flipping a comparison, swapping and for or, turning true into
false, dropping a not, deleting a line -- and runs the checks named for that
file. A change that the checks do not notice is called a SURVIVOR: the code
could be broken that way and every check would still say the product is fine.

WHAT IT DOES NOT PROVE. A survivor is not automatically a bug, and a killed
change is not proof the check is good. Some changes make no difference to
behaviour at all -- a guard that is unreachable, a message nobody reads back --
and those can never be caught by anything. Those are listed in
`proven_survivors.json` with a written reason each. Two rules keep that list
honest, and both are failures:

  - a survivor that is NOT on the list;
  - an entry on the list that no longer matches any survivor.

The second matters as much as the first: without it the list quietly rots into a
record of what used to be true, which is the "two records of one fact" fault
this project has already been caught by four times.

WHAT COVERS WHAT. The rule is the sibling: `x.js` is proven by `x.test.js` in
the same folder. That is deliberate -- "the checks named for this file must be
able to catch a change to this file" is the property worth having. A source file
with no sibling is NOT quietly skipped: it must appear in COVERED_BY with the
checks that do cover it, or in NOT_PROVEN with the reason nothing does.

KNOWN LIMITS, written down rather than left to be discovered:

  - It reads the code as text, not as a program. Comments and strings are
    skipped by a small scanner that understands quotes and comments but NOT
    regular expressions -- so a pattern containing a quote character would
    confuse it. There is no such pattern in the product today; if one is added,
    the mutants around it will look odd rather than silently vanish.
  - A change that will not parse is discarded, not counted as caught. Otherwise
    a syntax error would look like a check doing its job.
  - A change that makes the checks file fall over before it runs -- deleting an
    import, say -- is reported on its own as CRASHED rather than folded into
    "caught". It was noticed, so it is not a survivor; but nothing went red, so
    it says nothing about whether the checks are any good. Reading the exit code
    alone hid that number inside the good one.
  - It runs the SIBLING checks only. A change to the table that only
    `items.test.js` would catch counts as a survivor here, and that is the
    intended reading: the table's own checks should catch changes to the table.
"""

import argparse
import atexit
import json
import os


import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

# Where the sibling rule does not apply. Every entry is a deliberate decision
# with the reason beside it, not a convenience.
# The reason for both entries below, stated honestly after a review took the
# first version of it apart. It is NOT that these files hold "knowledge, not
# behaviour" -- they hold branching decisions with real edge cases, and the same
# words would exempt `definitions/products.js` sitting beside them, which has a
# sibling of its own and needs one.
#
# It is that both are driven by the SAME FIXTURES as the reader: real rows out
# of Jaiswal's two listing files, forty-odd lines of headings and help text. A
# sibling for each would be a third and fourth copy of those rows, and three
# copies of one fact is the exact failure D21 exists to stop. So the checks sit
# where the fixtures are, and both files are named by them directly -- 14 checks
# call into `listing-files.js` by name and 20 into `listing-blocks.js`, not
# merely through `readListingFile`.
COVERED_BY = {
    'src/shared/definitions/listing-files.js': 'src/modules/listings/reader.test.js',
    'src/shared/definitions/listing-blocks.js': 'src/modules/listings/reader.test.js',
    # Storing and reading who else may use a business. It has no checks file of
    # its own; the section that uses it drives every one of its writes, and
    # imports it by name to do so.
    'src/modules/people/people.js': 'src/modules/people/people-section.test.js',
    # The blocks the Master and platform tabs share (cards, trend, cash row, SKU
    # table). It has no checks file of its own: the cockpit screen builds every one
    # of them, and its checks read what each draws.
    'src/modules/cockpit/blocks.js': 'src/modules/cockpit/cockpit-screen.test.js',
    # The two panels that open over the job list. Same shape: the screen opens
    # them and its checks drive them through the screen.
    'src/modules/jobwork/jobwork-panels.js': 'src/modules/jobwork/jobwork-screen.test.js',
    # Listing health's two pieces that draw or read, driven end to end by the screen's own checks: the numbers table is
    # opened through the tab and through Settings, and the loader is what the tab reads everything with.
    'src/modules/listing-health/limits-table.js': 'src/modules/listing-health/listing-health-screen.test.js',
    'src/modules/listing-health/load.js': 'src/modules/listing-health/listing-health-screen.test.js',
}

# Source files nothing can prove yet. Each one is a written admission, not an
# exemption: an entry here says "no checks name this file", and that is a gap
# somebody chose to leave open. Anything not listed here and with no sibling is
# a failure, so a new file cannot slip through by having no checks at all.
NOT_PROVEN = {
    'test/fake-browser.js':
        'The stand-in browser. Nothing names checks for it, and nothing can in '
        'the way the sibling rule means: it is not code that decides anything, '
        'it is the thing every other checks file is driven against. **Break it '
        'on purpose and the answer is not one red line -- it is that some other '
        'file goes red for a reason that has nothing to do with that file.** '
        'WHAT ACTUALLY HOLDS IT: every way it differs from a real browser is '
        'written in its own header, and the register carries four separate '
        'cycles where a defect hid behind a stand-in that was kinder than the '
        'real thing. WHAT THIS EXEMPTION DOES NOT COVER: a DECISION drifting '
        'into it. If a rule about what is refused, allowed or retried ever '
        'appears here, it belongs in the product and this entry has stopped '
        'being true.',
    'src/app/main.js':
        'The wiring that starts the app. It has no checks of its own; what it '
        'does is visible only by opening the product, and D86 names the one '
        'line in it that has to be deleted when a real business can connect.',
    'src/app/local-only-store.js':
        'The stand-in list from D86. It is driven hard by items.test.js and by '
        'store.test.js but no checks are NAMED for it, so nothing here proves '
        'its behaviour line by line -- which is exactly why D86 writes down what '
        'it cannot do. WHAT THIS EXEMPTION DOES NOT COVER, learnt the hard way: '
        'when the first hard delete in the product went in (D94), this entry '
        'still read "driven hard by items.test.js" and that had stopped being '
        'true of the new line -- the one line that actually erases anything '
        'could be removed with every checks file in the product still green. '
        'Anything ADDED here needs something driving it, named or not, and this '
        'text has to be re-read when it is.',
    'src/shared/components/alerts.js':
        'The notification centre. Driven by alerts-storage.test.js and by every '
        'screen, and named by none of them.',
    'src/shared/values.js':
        'The copy helper. Used everywhere, named by nothing.',
    # THE FOUR FILES OF THE RULES PROOF. They are checks themselves, and they run only
    # inside the Firestore emulator (`firebase emulators:exec`), which this tool cannot
    # start for each of its changes. Breaking them on purpose here would end every run
    # as a crash, noticed by the file failing to load and not by a check going red.
    'test/rules/checks.js':
        'The rules proof itself: every allowed and refused case against `firestore.rules`. '
        'It runs only inside the emulator, so this tool cannot mutate it and read a check '
        'go red. WHAT HOLDS IT: `putting-the-fault-back.js` loosens one line of the rules at a '
        'time and requires a NAMED check here to fail, and `run.js` pins the tally.',
    'test/rules/run.js':
        'Starts the rules proof and pins how many checks must run, so one that quietly '
        'stops running is caught. It runs only inside the emulator, so this tool cannot '
        'break it and see a check go red. WHAT HOLDS IT: the tally it pins fails the run when '
        'it is wrong. WHAT THIS EXEMPTION DOES NOT COVER: nothing proves the pin itself.',
    'test/rules/lookup-limit.js':
        'Measures the ten-lookup limit against the emulator. It runs only inside the '
        'emulator, so this tool cannot mutate it and see a check go red. WHAT HOLDS IT: '
        'its measured figures are printed and counted by `run.js`.',
    'test/rules/putting-the-fault-back.js':
        'Puts each rules fault back and requires a named check to go red -- the proof that '
        'the rules checks can fail. It runs only inside the emulator, so this tool cannot '
        'mutate it. WHAT HOLDS IT: it pins how many faults it puts back, and it fails any '
        'loosening that changes nothing. WHAT THIS EXEMPTION DOES NOT COVER: nothing proves '
        'those two guards in turn.',
}

# WHAT CAME OFF THIS LIST ON 2026-09-06, AND WHAT IT COST.
#
# `src/app/screens/alerts-screen.js` was here, admitting that nothing named it.
# It now has `alerts-screen.test.js`, so it may not stay -- a file with a sibling
# in this list makes `prove_checks_checks.py` go red, and rightly.
#
# **BUT COMING OFF THIS LIST IS NOT THE SAME AS BEING PROVEN, and without this
# note the record goes from an out-loud gap to silence.** Measured with this tool
# on the day the entry was removed:
#
#     alerts-screen.js       50 survived, 0 accepted, 23 ended in a crash
#     table-file.js           2 survived, 0 accepted, 12 crashed   (new, shared)
#     spreadsheet.js          2 survived, 0 accepted,  0 crashed   (new, shared)
#
# The eleven checks that file now carries are about ONE thing -- naming which
# part of Kartaan an alert came from. The rest of the screen is still unproven.
#
# **AND THE TWO SHARED FILES ARE THE ONES TO WATCH**, because every table in the
# product now depends on `table-file.js`. The register's own words when this was
# last argued: a file that is NEW and SHARED is the last place to accept
# unproved. That finding closed at zero; this stands at four, written down here
# rather than left for the next reader to discover (D180).
#
# The commit gate does not run this tool -- a full run takes hours and it is
# excluded by name in `.githooks/pre-commit`. So nothing above was slipped past a
# gate; it is proof debt, and this is the note that keeps it visible.

# How long one run of a checks file is allowed to take before it is treated as
# hung. A change that makes the product loop forever has certainly been noticed,
# so a timeout counts as caught -- and is reported separately so it cannot hide.
#
# **240, NOT 90, SINCE 2026-10-07.** This is also the limit for the first pass, when
# every checks file is run once with nothing changed and nothing has been measured
# yet. tools/status_checks.py takes 89 s on an idle machine, so at 90 the v0.1.9
# proving run died in that pass with no record. After the first pass each change
# gets four times the slowest measured run anyway (`patience` in `main`); this
# number only has to outlast the slowest checks file on a busy machine.
# prove_checks_checks.py holds it at twice the slowest measured.
TIMEOUT_SECONDS = 240

SURVIVORS_FILE = ROOT / 'tools' / 'proven_survivors.json'

# ---------------------------------------------------------------- reading code


def language_of(relpath):
    """Which language this file is written in.

    The product is JavaScript and the tools that guard it are Python, and until
    now only the first was ever broken on purpose. The gate's own code -- this
    file, the board, the product scan -- was the part nobody measured, which is
    exactly where a check that cannot fail hides longest.
    """
    return 'python' if relpath.endswith('.py') else 'javascript'


def python_mask(text):
    """Which characters are real code, in Python.

    Same job as the JavaScript one below and a different language: `#` starts a
    comment, there is no block comment, and a string can be tripled -- which is
    how every docstring in these tools is written, so getting that wrong would
    mean breaking words in prose and calling the result a survivor.
    """
    mask = bytearray(len(text))
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '#':
            while i < n and text[i] != '\n':
                i += 1
            continue
        if c in ('"', "'"):
            quote = text[i:i + 3] if text[i:i + 3] in ('"""', "'''") else c
            i += len(quote)
            while i < n:
                if text[i] == '\\':
                    i += 2
                    continue
                if text[i:i + len(quote)] == quote:
                    i += len(quote)
                    break
                i += 1
            continue
        mask[i] = 1
        i += 1
    return mask


def code_mask(text):
    """Which characters are real code.

    False for anything inside a comment or a string, so a `true` in a sentence
    is never mistaken for a `true` in the product. Deliberately does not
    understand regular expressions -- see the known limits at the top.
    """
    mask = bytearray(len(text))
    state = 'code'
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        after = text[i + 1] if i + 1 < n else ''
        if state == 'code':
            if c == '/' and after == '/':
                state = 'line'
                i += 2
                continue
            if c == '/' and after == '*':
                state = 'block'
                i += 2
                continue
            if c in ('"', "'", '`'):
                state = c
                i += 1
                continue
            mask[i] = 1
            i += 1
            continue
        if state == 'line':
            if c == '\n':
                state = 'code'
            i += 1
            continue
        if state == 'block':
            if c == '*' and after == '/':
                state = 'code'
                i += 2
                continue
            i += 1
            continue
        # inside a string
        if c == '\\':
            i += 2
            continue
        if c == state:
            state = 'code'
        i += 1
    return mask


def line_starts(text):
    """The offset each line begins at, so a change can be reported by line."""
    starts = [0]
    for i, c in enumerate(text):
        if c == '\n':
            starts.append(i + 1)
    return starts


def line_of(starts, offset):
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid] <= offset:
            lo = mid
        else:
            hi = mid - 1
    return lo


# ------------------------------------------------------- the deliberate changes

# Each one stands for a mistake this project has actually made.
SWAPS = (
    ('equality', '===', '!=='),
    ('equality', '!==', '==='),
    ('logic', '&&', '||'),
    ('logic', '||', '&&'),
)

WORD_SWAPS = (
    ('boolean', 'true', 'false'),
    ('boolean', 'false', 'true'),
)

# The same four shapes in the other language, and these DO need a fence, unlike
# the JavaScript pair. Not for the reason first written here: `==` is two signs
# and `!=`, `<=`, `>=` are one apiece, so a search for `==` cannot land inside
# any of them, and `===` is not Python at all. **The real overlap is `>>=` and
# `<<=`** -- each holds a `>=` or a `<=` with another sign in front -- and
# rewriting half of one produces something that will not parse, which is
# discarded, quietly shrinking what is measured while the count of changes tried
# goes up. Nothing here uses those operators today, which is exactly why the
# three checks standing over the fence could not go red until one was written
# against `x >>= 1`.
PY_SWAPS = (
    ('equality', '==', '!='),
    ('equality', '!=', '=='),
    ('comparison', '>=', '<'),
    ('comparison', '<=', '>'),
)

PY_WORD_SWAPS = (
    ('boolean', 'True', 'False'),
    ('boolean', 'False', 'True'),
    ('logic', 'and', 'or'),
    ('logic', 'or', 'and'),
)

# The dropped negation, which in Python is a word rather than a mark. `not in`
# is left alone: dropping the `not` there is already covered by swapping `in`
# for `not in` and back, and taking it out separately produces the same mutant
# twice under two names.
PY_DROPPED = (('not', re.compile(r'\bnot (?!in\b)')),)


def python_changes_for(text):
    """Every deliberate change to try on a Python file."""
    mask = python_mask(text)
    found = []

    for operator, was, becomes in PY_SWAPS:
        start = 0
        while True:
            at = text.find(was, start)
            if at < 0:
                break
            start = at + 1
            if not all(mask[at:at + len(was)]):
                continue
            # A sign on either side means this is part of a longer operator
            # rather than the comparison being aimed at. **The case that really
            # happens is `>>=` and `<<=`**, which hold a `>=` and a `<=` with a
            # sign in front of them; the `==` cases cannot occur at all, since
            # `!=`, `<=` and `>=` are one sign each and `==` is two. Left
            # unguarded, rewriting half of a `>>=` produces something that will
            # not parse -- discarded, so the count of changes tried would rise
            # while what is actually measured fell.
            before = text[at - 1] if at else ''
            after = text[at + len(was):at + len(was) + 1]
            if before in ('!', '<', '>', '=') or after == '=':
                continue
            found.append((operator, at, at + len(was), becomes))

    for operator, was, becomes in PY_WORD_SWAPS:
        for hit in re.finditer(r'\b' + was + r'\b', text):
            if all(mask[hit.start():hit.end()]):
                found.append((operator, hit.start(), hit.end(), becomes))

    for operator, pattern in PY_DROPPED:
        for hit in pattern.finditer(text):
            if all(mask[hit.start():hit.end()]):
                found.append((operator, hit.start(), hit.end(), ''))

    return found


def changes_for(text, language='javascript'):
    """Every deliberate change to try on this file, as (operator, start, end, replacement)."""
    if language == 'python':
        return python_changes_for(text)
    mask = code_mask(text)
    found = []

    for operator, was, becomes in SWAPS:
        start = 0
        while True:
            at = text.find(was, start)
            if at < 0:
                break
            start = at + 1
            # No fence here like the Python one above, and none is needed:
            # neither of these sits inside anything else. The fence that used to
            # be here read `===` as part of `!==` -- three signs against two --
            # so it could never fire, and the check standing over it could never
            # go red. The Python fence beside it had the same wrong reason
            # written on it and a real job underneath; this one had neither.
            if all(mask[at:at + len(was)]):
                found.append((operator, at, at + len(was), becomes))

    for operator, was, becomes in WORD_SWAPS:
        for hit in re.finditer(r'\b' + was + r'\b', text):
            if all(mask[hit.start():hit.end()]):
                found.append((operator, hit.start(), hit.end(), becomes))

    # A dropped `not` -- the shape behind "the filter did the exact opposite of
    # what it said". Never `!=`, which is a comparison, not a negation.
    for at, c in enumerate(text):
        if c != '!' or not mask[at]:
            continue
        if text[at + 1:at + 2] == '=':
            continue
        if at > 0 and text[at - 1] == '!':
            continue
        found.append(('not', at, at + 1, ''))

    return found


def line_changes_for(text, language='javascript'):
    """Deleting one whole line -- literally "take the fix out and see".

    Only lines that carry code. Deleting a comment changes nothing that can ever
    be noticed, so it would be pure noise on the survivors list.

    In Python a great many of these will not parse -- take the only line out of
    an `if` body and the file is broken -- and those are discarded rather than
    counted as caught, which is the same rule as everywhere else here.
    """
    mask = python_mask(text) if language == 'python' else code_mask(text)
    starts = line_starts(text)
    lines = text.split('\n')
    out = []
    for index, start in enumerate(starts):
        end = start + len(lines[index])
        # At least one character that is code AND not blank. Counting the
        # indentation as code made every indented comment line look like a line
        # of code -- and an indented comment is what most comments in this
        # project are. Deleting one changes nothing that could ever be noticed,
        # so each was a survivor nobody could kill.
        if not any(mask[at] and not text[at].isspace() for at in range(start, end)):
            continue
        out.append(index)
    return out


def mutant_id(relpath, operator, line_text, occurrence):
    return {
        'file': relpath,
        'operator': operator,
        'line': line_text.strip(),
        'occurrence': occurrence,
    }


def same_mutant(a, b):
    return (a['file'] == b['file'] and a['operator'] == b['operator']
            and a['line'] == b['line'] and a['occurrence'] == b['occurrence'])


# The line that decides whether a file is being RUN or merely imported. Break
# it and the file runs itself the moment its checks file imports it: the product
# scan runs and exits 0 with no check having run at all (a survivor nothing can
# ever kill), the local server starts and blocks until the timeout, and this
# tool starts a whole run of itself inside its own copy. None of those four
# verdicts is decided by a check, so none of them means anything.
RUNS_ITSELF = re.compile(r'^\s*if\s+__name__\s*==')


def on_a_line_that_runs_itself(text, starts, at):
    index = line_of(starts, at)
    end = starts[index + 1] if index + 1 < len(starts) else len(text)
    return RUNS_ITSELF.match(text[starts[index]:end]) is not None


def plan_for(relpath, text):
    """Every change to try on one file, each with the text that results."""
    language = language_of(relpath)
    starts = line_starts(text)
    lines = text.split('\n')
    seen = {}
    plan = []

    for operator, start, end, replacement in changes_for(text, language):
        if on_a_line_that_runs_itself(text, starts, start):
            continue
        index = line_of(starts, start)
        key = (operator, lines[index].strip())
        occurrence = seen.get(key, 0)
        seen[key] = occurrence + 1
        plan.append({
            'id': mutant_id(relpath, operator, lines[index], occurrence),
            'line_number': index + 1,
            'text': text[:start] + replacement + text[end:],
        })

    for index in line_changes_for(text, language):
        if RUNS_ITSELF.match(lines[index]):
            continue
        key = ('line', lines[index].strip())
        occurrence = seen.get(key, 0)
        seen[key] = occurrence + 1
        remaining = lines[:index] + lines[index + 1:]
        plan.append({
            'id': mutant_id(relpath, 'line', lines[index], occurrence),
            'line_number': index + 1,
            'text': '\n'.join(remaining),
        })

    return plan


# --------------------------------------------------------------- running them

# One private copy of the code per worker process. Without this the workers
# would write over each other's file and every answer would be a coincidence.
_TREE = None


def away_from_the_real_repository():
    """The environment with git's own pointers taken out of it.

    **EVERYTHING THIS TOOL RUNS, IT RUNS SOMEWHERE ELSE** -- a copy of the
    product in a temporary folder, made into a repository of its own. That only
    holds if the programs it starts cannot see the repository it was called
    from, and by default they can: git hands its own location to every hook it
    runs, and a child process inherits it.

    **WHAT THAT COST, on 2026-08-31.** A commit made from a git WORKTREE ran
    this tool from the pre-commit hook. `git init` and `git add -A` below were
    aimed at the temporary copy by `cwd` -- and `cwd` loses to what git hands
    down. So `git add -A` staged a four-file temporary product as the whole of
    the real repository: 264 files marked deleted, and everything that was
    staged for that commit gone.

    **AND THE INDEX WAS THE RECOVERABLE HALF.** `git init` aimed at the real
    git directory re-initialises it and leaves `bare = true` behind, after
    which every command in that working tree answers *"this operation must be
    run in a work tree"*. `git reset` does not undo that.

    **TWO VARIABLES DO IT, AND EITHER ALONE IS ENOUGH.** An independent
    reviewer put the fault back three ways and measured it: stripping neither
    wipes the index, stripping only `GIT_DIR` still wipes it, stripping only
    `GIT_INDEX_FILE` still wipes it. So this is not a rule about `GIT_DIR`; it
    is a rule about every pointer git hands down, which is why the list below
    is the whole documented set rather than the one that was noticed first.

    **WHY IT HAD NEVER SHOWN UP, and the first answer written here was wrong.**
    It was not that git failed quietly from an ordinary checkout. Git sets no
    `GIT_DIR` at all there; what it sets is `GIT_INDEX_FILE=.git/index`, and
    that is RELATIVE -- so from the temporary folder it resolved to the
    temporary repository's own index and everything worked by luck. A worktree
    hands down both, ABSOLUTE, and they resolve from anywhere. That correction
    came from an independent reviewer capturing the real hook environment on
    both, after this docstring had asserted the wrong reason three times over.

    The node runs get this too, not only the git ones. A checks file inside the
    copy can ask git about the product; inheriting these would have it answer
    about the real repository instead, which is the same fault one level down.

    **WHAT DELIBERATELY DOES NOT GET THIS: `changed_files` and `changed_lines`.**
    They ask the real repository what is staged, and under `git commit <path>`
    git stages into a temporary index and hands it down. Taking that away makes
    them answer about the wrong content -- proved by the same reviewer. A
    pointer is only wrong when the thing being pointed at is somewhere else.
    """
    without = dict(os.environ)
    for pointer in (
        'GIT_DIR', 'GIT_INDEX_FILE', 'GIT_WORK_TREE', 'GIT_OBJECT_DIRECTORY',
        'GIT_COMMON_DIR', 'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_PREFIX',
        'GIT_NAMESPACE',
    ):
        without.pop(pointer, None)
    return without


def files_to_copy(source_root):
    """Every file a checks run can reach: what git tracks, plus what is new.

    Whole folders were copied before, which was enough while only the product
    was being broken. The tools that guard the product read the repository
    itself -- the register, the hooks, the workflow -- and one of them asks git
    what it holds, so the copy has to be a repository too.

    New files that are not ignored are copied as well. They are part of the
    product as it stands even though no commit carries them yet, and leaving
    them out would quietly drop a screen and its checks from the measurement.
    """
    listed = []
    for question in (['ls-files'], ['ls-files', '--others', '--exclude-standard']):
        answer = subprocess.run(args=['git', '-c', 'core.quotePath=false', *question],
            cwd=str(source_root), capture_output=True, text=True,
            env=away_from_the_real_repository(),
        )
        if answer.returncode == 0:
            listed += [line for line in answer.stdout.splitlines() if line]
    if listed:
        return sorted(set(listed))

    # Not a repository at all -- which is what this tool's OWN checks hand it: a
    # made-up two-file product in a temporary folder. Copy what is there. Asking
    # git and taking silence for "there is nothing" would have copied an empty
    # tree and every answer after it would have been about a product with no
    # files in it.
    root = Path(source_root)
    return sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob('*')
        if p.is_file() and '.git' not in p.relative_to(root).parts
    )


def scrub(path):
    """Remove a copied tree, including the read-only files git leaves behind.

    `ignore_errors=True` was not enough, and it hid the failure rather than
    reporting one. Every copy made here is a git repository of its own, git
    marks its own object files read-only, and Windows refuses to delete a
    read-only file -- so the `.git` folder was left behind on EVERY run this
    tool has ever done, while the cleanup said nothing at all. Twenty-nine
    thousand of them had built up in the temp folder of the machine this was
    written on before anybody looked, and a run finally died of it.

    Anything still there afterwards is somebody else holding a file open, and
    there is nothing useful to do about that from here -- but the read-only
    mark, which is the whole of this failure, is dealt with.
    """
    def make_it_writable(remove, name, problem):
        try:
            os.chmod(name, stat.S_IWRITE)
            remove(name)
        except OSError:
            pass

    try:
        shutil.rmtree(str(path), onexc=make_it_writable)
    except TypeError:
        # An older Python: the same handler, under the name it had then.
        shutil.rmtree(str(path), onerror=make_it_writable)
    except OSError:
        pass


def _make_tree(source_root, prefix):
    """A private copy of the repository, and a repository in its own right.

    `git init` and one `git add` are what make it one. The board's checks ask
    git what the commit will carry; against a plain directory git answers
    nothing at all, and every one of those questions would have come back empty
    while the checks that read them stayed green.
    """
    tree = Path(tempfile.mkdtemp(prefix=prefix))
    for rel in files_to_copy(source_root):
        source = Path(source_root) / rel
        if not source.is_file():
            continue
        target = tree / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    quiet = {
        'capture_output': True,
        'cwd': str(tree),
        'env': away_from_the_real_repository(),
    }
    subprocess.run(['git', 'init', '-q'], **quiet)
    subprocess.run(['git', 'add', '-A'], **quiet)
    return tree


def stage(tree, relpath, text):
    """Put this text in the copy -- on the disk AND in what git would commit.

    The copy is a repository, and the board's checks read a file's content out
    of the index rather than off the disk, because the board describes what a
    commit will carry. Writing the change to the disk alone left the index
    holding the ORIGINAL: every check that reads a file that way was handed the
    unbroken version and reported a survivor, and the board's own rule that the
    files it is generated from must match the commit went red for every single
    change to those files, whatever the change was.
    """
    target = Path(tree) / relpath
    with open(target, 'w', encoding='utf-8', newline='') as handle:
        handle.write(text)
    subprocess.run(
        ['git', 'add', '--', relpath], cwd=str(tree), capture_output=True,
        env=away_from_the_real_repository(),
    )


def _prepare(source_root, patience=None):
    """Get a worker ready: its own copy of the code, and how long to wait.

    The limit is passed in rather than read off the top of this file. Each
    worker is a separate process that loads this file afresh, so a limit worked
    out in the parent would never reach it -- and the workers are the only place
    it is used.
    """
    global _TREE, TIMEOUT_SECONDS
    if patience:
        TIMEOUT_SECONDS = patience
    _TREE = _make_tree(source_root, 'kartaan-prove-')
    atexit.register(scrub, str(_TREE))



def is_checks_only(wanted, jobs, scoped, touched):
    """Is this a change to CHECKS files with no source touched?

    True only when all three hold: there are source files in scope, there is
    nothing to try on any of them, and not one of them was itself changed. The
    last is what tells this apart from a change that touched a source and
    happened to add no code -- a comment, a rename -- which is still refused,
    because that one CAN hide a weakened check beside it.

    Unscoped runs are never checks-only: with nothing scoped there is always
    something to try, and if there is not, that is the empty run this tool
    exists to refuse.
    """
    if not scoped or not wanted or jobs:
        return False
    return not (set(wanted) & set(touched or ()))

def baseline_passes(source_root, checks_files):
    """Do the checks pass with NOTHING changed?

    Without this, "the checks can fail" is proven and "the checks can pass" is
    assumed -- and a checks file that fails for a reason of its own scores a
    perfect hundred per cent, because every single change to the file it covers
    is reported as caught. That is the very shape this tool exists to catch,
    inside the tool.

    AND HOW LONG THE SLOWEST OF THEM TAKES with nothing changed, which decides
    how long a change is given before it is stopped. A stopped run is counted as
    CAUGHT -- a change that makes the product never finish has certainly been
    noticed -- and that reading only holds while the checks file itself finishes
    comfortably inside the limit. When it stops doing so, every slow run is
    scored as proof: 355 of the 545 changes to this very file were once
    "caught" by the clock and by nothing else, and the answer it gave --
    nothing survived -- was worth nothing at all.

    It also proves the copied tree is complete. What is copied is what git
    lists -- everything tracked, plus anything new that is not ignored -- so a
    checks file that reads something git has never heard of fails here rather
    than silently making its whole source file look proven.
    """
    tree = _make_tree(source_root, 'kartaan-prove-base-')
    try:
        broken = []
        slowest = 0.0
        for checks_rel in sorted(set(checks_files)):
            began = time.monotonic()
            finished = subprocess.run(
                runner_for(checks_rel) + [str(tree / checks_rel)],
                capture_output=True, timeout=TIMEOUT_SECONDS,
                cwd=str(tree), env=away_from_the_real_repository(),
            )
            slowest = max(slowest, time.monotonic() - began)
            if finished.returncode != 0:
                said = (finished.stderr or finished.stdout or b'').decode('utf-8', 'replace')
                broken.append(
                    f'{checks_rel} does not pass with nothing changed. '
                    f'It said: {said.strip()[-500:]}')
        return broken, slowest
    finally:
        scrub(tree)


def python_parses(text):
    """Would Python accept this as a program at all?

    Asked of Python itself, in this process -- there is nothing to start up and
    nothing to guess at, and it is why a Python run gets through its changes as
    fast as it does. A file that will not compile is discarded, exactly as an
    unparseable JavaScript one is: a syntax error is not a check doing its job.
    """
    try:
        compile(text, '<a deliberate change>', 'exec')
        return True
    except (SyntaxError, ValueError):
        return False


def runner_for(relpath):
    """What runs the checks named for this file.

    `-B` is not a detail. Python validates a saved .pyc on the file's SIZE and
    its time to the nearest WHOLE SECOND, and swapping `==` for `!=` changes
    neither -- so the second of two same-size changes in the same second would
    be imported from the first one's bytecode, and the verdict recorded would
    belong to a different change entirely. Nothing anywhere would notice.
    """
    return [sys.executable, '-B'] if language_of(relpath) == 'python' else ['node']


def parses(text):
    """Would Node accept this as a module at all?

    ASKED, not guessed. This used to be decided by looking for the word
    "SyntaxError" in whatever node printed -- and reading a damaged setting with
    JSON.parse throws one of those, as does a checks file printing the failure
    it caught. Both were then filed under "would not parse" and dropped: neither
    caught nor survived, and never reported. A whole run of them would have
    printed a clean bill of health.

    Node is the only thing that knows, so Node is asked.
    """
    finished = subprocess.run(
        ['node', '--input-type=module', '--check'],
        input=text.encode('utf-8'), capture_output=True, timeout=TIMEOUT_SECONDS,
        env=away_from_the_real_repository(),
    )
    return finished.returncode == 0


def _try_one(job):
    """Put one change in, run the checks, put the file back."""
    relpath, checks_rel, original, mutated, ident, line_number = job
    readable = python_parses if language_of(relpath) == 'python' else parses
    try:
        if not readable(mutated):
            return {'id': ident, 'verdict': 'unparseable', 'timed_out': False,
                    'line_number': line_number}
    except subprocess.TimeoutExpired:
        return {'id': ident, 'verdict': 'unparseable', 'timed_out': False,
                'line_number': line_number}
    stage(_TREE, relpath, mutated)
    try:
        finished = subprocess.run(
            runner_for(checks_rel) + [str(_TREE / checks_rel)],
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            cwd=str(_TREE),
            env=away_from_the_real_repository(),
        )
        # WHETHER A CHECK WENT RED, not merely whether the run failed. Reading
        # the exit code alone was the worst fault ever found in this gate, in
        # its other half: a checks file can fail for a reason of its own -- a
        # mutation that deletes an import, so the file dies before its first
        # check -- and every one of those was being counted as a check doing
        # its job. It is the same shape as a checks file printing FAIL and
        # exiting 0, and it hides in the same place.
        #
        # A checks file here says PASS or FAIL on every line it checks. A run
        # that failed with no FAIL in it did not catch anything; it fell over.
        said = (finished.stdout or b'') + (finished.stderr or b'')
        if finished.returncode == 0:
            verdict = 'survived'
        elif re.search(br'^FAIL', said, re.M):
            verdict = 'caught'
        else:
            verdict = 'crashed'
        timed_out = False
    except subprocess.TimeoutExpired:
        verdict = 'caught'
        timed_out = True
    finally:
        stage(_TREE, relpath, original)
    return {'id': ident, 'verdict': verdict, 'timed_out': timed_out, 'line_number': line_number}


# ------------------------------------------------------------- what to look at


def read(path):
    with open(path, 'r', encoding='utf-8', newline='') as handle:
        return handle.read()


def sources():
    """Every source file, and the checks named for it.

    Two families, and the sibling rule holds in both: `x.js` is proven by
    `x.test.js`, and `x.py` by `x_checks.py`. The product was the only one
    measured until now, which left the code of the gate itself -- the part that
    decides whether anything else is allowed through -- as the one place a check
    that cannot fail could sit indefinitely.
    """
    out = {}
    # **AND THE EXTENSION, on the same sibling rule.** It is not served with the
    # product -- it runs inside the seller's own Chrome -- so nothing else here
    # looks at it at all. Left out, the one piece of this project that actually
    # touches a live portal would be the one piece nothing measures, which is
    # precisely what leaving the gate's own code unmeasured used to cost.
    # **AND THE STAND-INS (cycle 46, R6#9).** `test/` sat outside the whole
    # measurement while this docstring said the sibling rule held -- and the two
    # files in it are the browser and the Chrome every checks file is driven
    # against. **A stand-in kinder than the real thing is this register's
    # most-repeated failure class**, four cycles running, each one a defect that
    # hid behind a generous fake. Leaving the pair that must be faithful as the
    # pair nothing measures is the same shape as leaving the gate's own code out.
    for path in (sorted((ROOT / 'src').rglob('*.js'))
                 + sorted((ROOT / 'extension').rglob('*.js'))
                 + sorted((ROOT / 'test').rglob('*.js'))):
        rel = path.relative_to(ROOT).as_posix()
        if rel.endswith('.test.js'):
            continue
        sibling = path.with_name(path.stem + '.test.js')
        if rel in COVERED_BY:
            out[rel] = COVERED_BY[rel]
        elif sibling.exists():
            out[rel] = sibling.relative_to(ROOT).as_posix()
        else:
            out[rel] = None

    # **AND THE AUTO-SYNC PACKAGE, on the same sibling rule.** Written when it was
    # added: a package the prover cannot see is a package where a check that
    # cannot fail sits indefinitely, which is exactly what leaving the gate's own
    # code unmeasured cost. Two loops rather than one glob because `tools` is
    # flat and this is a package -- and a `rglob` over both would sweep up
    # anything either of them ever grows.
    # `server` joined them the day Kartaan gained one (D112). Same sibling rule,
    # and named rather than swept up by a wildcard for the reason above.
    for path in (sorted((ROOT / 'autosync').glob('*.py'))
                 + sorted((ROOT / 'server').glob('*.py'))
                 + sorted((ROOT / 'tools').glob('*.py'))):
        rel = path.relative_to(ROOT).as_posix()
        # A file is the CHECKS for another only if that other one exists. Going
        # by the ending alone dropped `prove_checks.py` -- this file, the one
        # thing here nothing else can measure -- out of the measurement
        # entirely, because its name happens to end the same way.
        if rel.endswith('_checks.py') and path.with_name(
            path.name[: -len('_checks.py')] + '.py'
        ).exists():
            continue
        # No COVERED_BY branch here: every entry in it is a .js path, and a
        # check enforces that every value ends .test.js -- so the branch could
        # never fire. Code that can never run is found by the build, not by a
        # reader months later.
        sibling = path.with_name(path.stem + '_checks.py')
        if sibling.exists():
            out[rel] = sibling.relative_to(ROOT).as_posix()
        else:
            out[rel] = None
    return out


def _diff_args(against):
    """How to ask git what changed.

    Two callers with the same question. The commit hook asks about what is
    staged; CI has no staging area at all and asks about the range that was
    pushed. One place decides, so the two cannot drift into asking different
    questions and both reporting "proven".
    """
    if against:
        return ['diff', '-U0', against, '--'], ['diff', '--name-only', against, '--']
    return (['diff', '--cached', '-U0', 'HEAD', '--'],
            ['diff', '--cached', '--name-only', 'HEAD', '--'])


def changed_files(against):
    _, names = _diff_args(against)
    finished = subprocess.run(env=away_from_the_real_repository(), args=['git'] + names, cwd=str(ROOT), capture_output=True, text=True)
    if finished.returncode != 0:
        return None
    return {line.strip() for line in finished.stdout.splitlines() if line.strip()}


HUNK = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')


def changed_lines(relpath, against):
    """Which line numbers this change ADDS or CHANGES in one file.

    The gate's whole rule is "prove the fix you just wrote", so it looks only at
    what the commit is putting in. Everything already in the product is a
    separate, recorded backlog -- blocking a commit on lines it never touched
    would be a gate nobody could pass and would be switched off within a week.
    """
    hunks, _ = _diff_args(against)
    finished = subprocess.run(env=away_from_the_real_repository(), args=['git'] + hunks + [relpath],
                              cwd=str(ROOT), capture_output=True, text=True)
    if finished.returncode != 0:
        return None
    return lines_from_diff(finished.stdout)


def lines_from_diff(diff_text):
    """The line numbers a diff adds, read from its hunk headers.

    `@@ -a,b +c,d @@` means d lines starting at c in the new file. A missing
    count means exactly one line; a count of zero means the hunk only removes
    things, so it adds no line at all.
    """
    touched = set()
    for line in diff_text.splitlines():
        hit = HUNK.match(line)
        if not hit:
            continue
        start = int(hit.group(1))
        count = 1 if hit.group(2) is None else int(hit.group(2))
        for number in range(start, start + count):
            touched.add(number)
    return touched


def crash_reasons():
    """Which files have a written reason for the changes that stop them loading."""
    try:
        with open(SURVIVORS_FILE, 'r', encoding='utf-8') as handle:
            written = json.load(handle).get('cannot_load', {})
    except (OSError, ValueError):
        return {}
    return {
        where: why for where, why in written.items()
        if isinstance(why, str) and len(why.strip()) >= 40
    }


def load_accepted():
    if not SURVIVORS_FILE.exists():
        return []
    with open(SURVIVORS_FILE, 'r', encoding='utf-8') as handle:
        data = json.load(handle)
    return data.get('accepted', [])


def mutant_key(ident):
    return (ident.get('file'), ident.get('operator'), ident.get('line'), ident.get('occurrence'))


def judge(accepted, survivors, tried):
    """Which survivors nobody recorded, and which records no longer hold.

    AN ENTRY IS ONLY JUDGED IF ITS OWN CHANGE WAS ACTUALLY TRIED, and that is
    the whole point of `tried`. Judging by FILE was wrong, and quietly so: a
    scoped run tries only the changed lines, so every accepted survivor sitting
    on a line the commit did not touch was reported as no longer surviving --
    and the message told whoever read it to delete a true entry. One line
    changed in the table would have produced six of those; one line in the items
    screen, thirty-four. Doing as it said would have gutted the list, and the
    next full run would then have blocked on the very survivors just deleted.
    """
    unexpected = [hit for hit in survivors
                  if not any(same_mutant(hit['id'], entry) for entry in accepted)]
    stale = [entry for entry in accepted
             if mutant_key(entry) in tried
             and not any(same_mutant(hit['id'], entry) for hit in survivors)]
    return unexpected, stale


def unrecorded(reasons, crashed):
    """Crashes in files nobody wrote a reason for.

    A crash is not a survivor -- the change WAS noticed -- but nothing went red,
    so it says nothing about whether the checks are any good. Letting them
    through unremarked is how "neither caught nor survived, never reported"
    happened the first time.

    Written down PER FILE rather than per change, and that is a considered
    trade. Almost every one is the same fact said again -- take out a line the
    module needs to load and its checks file cannot import it -- so fifty-six
    near-identical entries would be padding, and padding is how a list stops
    being read. The cost is that a NEW crash in a file that already has a reason
    is covered by it; the count is printed on every run so a jump is visible.
    """
    return [hit for hit in crashed if hit['id']['file'] not in reasons]


def vanished(accepted, texts):
    """Accepted entries whose LINE is no longer anywhere in the file.

    A SECOND KIND OF ROT, and `judge` above cannot see it. An entry is only
    judged there if its own change was tried -- and a line that has been deleted
    outright produces no change to try, so the entry is never judged at all, on
    a scoped run OR a full one. It just sits there reading like a decision
    somebody made about code that is gone.

    Found the day this was written: `findSheet` was rewritten to `findSheets`
    during a review fix, its `return null;` went with it, and the entry
    exempting that line went on being carried with the tool reporting a clean
    run. Exactly the "record of what used to be true" the header of this file
    calls a failure equal to a missing entry.

    `texts` is {file: its source}, for the files this run actually read. An
    entry for a file that was not read is left alone -- saying nothing about it
    is honest, and guessing is what the bug above was made of.
    """
    gone = []
    for entry in accepted:
        source = texts.get(entry.get('file'))
        if source is None:
            continue
        if entry.get('line', '') not in source:
            gone.append(entry)
    return gone


def impossible(accepted, whole_plan):
    """Accepted entries naming a change that cannot even be ATTEMPTED.

    A THIRD KIND OF ROT, and the two guards above both miss it. `judge` only
    judges an entry whose own change was tried. `vanished` only asks whether the
    LINE is still somewhere in the file -- as text, anywhere. Between the two
    sits an entry whose line is still there but whose OCCURRENCE is not: three
    copies of a line became two, and the entry naming the third goes on being
    carried, judged by nothing at all.

    Found 2026-08-20 by counting rather than by trusting the tick: ninety-eight
    entries on the list, ninety-four survivors, and a clean bill of health.
    All four of the difference were real -- lines lifted out of the items screen
    into the shared one, with their entries left behind, carried across several
    commits. `return false;` slipped past `vanished` for the extra reason that
    the words appear inside a longer line elsewhere.

    `whole_plan` is {file: every change that CAN be made to it}, built before any
    scoping is applied -- so this answers the same on a scoped run as on a full
    one, which is the mistake `judge` was already caught by once.
    """
    gone = []
    for entry in accepted:
        plan = whole_plan.get(entry.get('file'))
        if plan is None:
            continue
        if mutant_key(entry) not in plan:
            gone.append(entry)
    return gone


def badly_written(accepted):
    """Anything on the accepted list that does not say what it is or why.

    An exemption with no reason is the shape this project has been caught by
    before: it reads as a decision and is really just a silence.
    """
    complaints = []
    for index, entry in enumerate(accepted):
        where = entry.get('file') or f'entry {index + 1}'
        for field in ('file', 'operator', 'line'):
            if not str(entry.get(field) or '').strip():
                complaints.append(f'accepted survivor {where} has no "{field}".')
        if not isinstance(entry.get('occurrence'), int):
            complaints.append(f'accepted survivor {where} has no whole-number "occurrence".')
        if len(str(entry.get('why') or '').strip()) < 20:
            complaints.append(
                f'accepted survivor {where} has no reason worth reading. '
                'Say why no check can ever catch this, or take it off the list.')
    return complaints


# --------------------------------------------------------------------- the run


def measured_nothing(offered, runnable):
    """A run in which every change was discarded is not a clean bill of health.

    Ordinary in Python: take the only line out of an indented block and the file
    will not compile. The run then has no survivors, nothing stale and no
    coverage problem -- and used to print that everything was proven.
    """
    if offered and not runnable:
        return ['not one of the changes to these lines could be made at all -- every one '
                'was discarded as unparseable, so nothing was measured. Lines that cannot '
                'be broken on purpose need a reader, not a green tick.']
    return []


def answered_by_the_clock(timed_out, runnable):
    """A run the clock answered is not an answer, and has to say so itself.

    A change that was STOPPED is counted as caught -- one that makes the product
    never finish has certainly been noticed -- and that reading only holds while
    the checks file finishes comfortably inside the limit. When it stops doing
    so, every slow run is scored as proof. **355 of the 545 changes to this very
    file were once caught by the clock and by nothing else**, and the answer it
    gave -- nothing survived -- was worth nothing at all.

    The limit adapting to how slow the checks honestly are makes that rarer. It
    does not make it VISIBLE, and the first time it happened it was found by a
    person adding up two numbers in a tally, days later. A gate that stays honest
    only while somebody remembers to read a number is not a gate.
    """
    if runnable and len(timed_out) * 10 > runnable:
        return [f'{len(timed_out)} of the {runnable} changes that were actually run were '
                'STOPPED by the time limit rather than noticed by a check, and a stopped '
                "run is counted as caught. Past a tenth of them the answer is the clock's "
                "and not the checks'. Make the checks files faster, or run fewer at once."]
    return []


def tally(results):
    """Sort every answer into its own bucket, once.

    Lifted out of the run for the same reason the verdict was: this is where a
    whole class of answer went missing without anything being able to notice.
    Every bucket is named, and `changes tried` is the sum of them, so a kind of
    answer that stops being counted stops adding up.
    """
    return {
        'survived': [r for r in results if r['verdict'] == 'survived'],
        'unparseable': [r for r in results if r['verdict'] == 'unparseable'],
        'caught': [r for r in results if r['verdict'] == 'caught'],
        'crashed': [r for r in results if r['verdict'] == 'crashed'],
        'timed out': [r for r in results if r['timed_out']],
    }


def verdict(unexpected, unexplained_crashes, stale, problems, checks_only):
    """Pass or fail, and the last word -- lifted out of the run so it can be checked.

    This is the one decision the whole tool exists to make, and it was buried at
    the bottom of a two-hundred-line function that nothing drives. A review found
    a class of failure had been dropped from it -- changes that stopped the
    checks file loading were counted, printed, and then let through -- and there
    was no check anywhere that could have noticed.
    """
    wrong = len(unexpected) + len(unexplained_crashes) + len(stale) + len(problems)
    if checks_only and not wrong:
        return 0, ('prove_checks: nothing was broken on purpose, because this change adds no '
                   'source lines. See above for what that does and does not cover.')
    if wrong:
        return 1, (
            f'\n{len(unexpected)} change(s) no check noticed, {len(unexplained_crashes)} that '
            f'stopped the checks file loading with no reason recorded, {len(stale)} stale '
            f'entr(ies), {len(problems)} coverage problem(s).')
    return 0, 'every deliberate change was either caught or recorded with a reason'


def main():
    # The product's own code carries arrows and long dashes, and a survivor is
    # reported by quoting the line it is on. On Windows the console hands back a
    # codec that cannot write those, so a full run did all its work and then
    # died printing the answer.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('--changed', action='store_true',
                        help='only the lines this commit stages')
    parser.add_argument('--against', default=None,
                        help='only the lines added since this commit -- for CI, '
                             'which has nothing staged')
    parser.add_argument('--only', action='append', default=[],
                        help='one source file, whole, repeatable')
    parser.add_argument('--workers', type=int, default=0)
    parser.add_argument('--json', default=None,
                        help='also write the survivors to this file, so a long '
                             'run does not have to be repeated to read it again')
    args = parser.parse_args()

    if args.changed and args.against:
        print('prove_checks: --changed and --against ask git two different '
              'questions. Pick one.', file=sys.stderr)
        return 1
    scoped = bool(args.changed or args.against)

    covers = sources()
    problems = []
    # Which files this change actually touched. Empty when nothing is scoped,
    # which is the same as "everything", and the loop below reads it that way.
    touched = set()

    # A source file nothing names is a gap, and it has to be a written one.
    for rel, checks in sorted(covers.items()):
        if checks is None and rel not in NOT_PROVEN:
            problems.append(
                f'{rel} has no checks named for it and no reason recorded. '
                'Add a sibling <name>.test.js, an entry in COVERED_BY, or an '
                'entry in NOT_PROVEN saying plainly that nothing proves it.')
        if checks is not None and rel in NOT_PROVEN:
            problems.append(
                f'{rel} is listed in NOT_PROVEN and yet has checks named for '
                'it. Two records of one fact, disagreeing. Remove the entry.')
        if checks is not None and not (ROOT / checks).exists():
            problems.append(f'{rel} is said to be covered by {checks}, which does not exist.')

    wanted = {rel: checks for rel, checks in covers.items() if checks is not None}

    if args.only:
        asked = {Path(one).as_posix() for one in args.only}
        unknown = asked - set(covers)
        for one in sorted(unknown):
            problems.append(f'{one} is not a source file in this product.')
        wanted = {rel: checks for rel, checks in wanted.items() if rel in asked}
    elif scoped:
        touched = changed_files(args.against)
        if touched is None:
            print('prove_checks: could not ask git what changed.', file=sys.stderr)
            return 1
        wanted = {rel: checks for rel, checks in wanted.items()
                  if rel in touched or checks in touched}

    jobs = []
    # The source of every file this run actually read, so an accepted entry
    # naming a line that no longer exists can be found. See vanished().
    texts = {}
    # And every change that COULD be made to each of those files, before any
    # scoping narrows it -- so an entry naming an occurrence the file no longer
    # has can be found too. See impossible(). Built unscoped on purpose: judged
    # against the scoped list, every entry outside the change would read as
    # rotten, which is the exact mistake judge() was caught by.
    whole_plan = {}
    for rel, checks in sorted(wanted.items()):
        text = read(ROOT / rel)
        texts[rel] = text
        full = plan_for(rel, text)
        whole_plan[rel] = {mutant_key(change['id']) for change in full}
        only_lines = None
        if scoped:
            only_lines = changed_lines(rel, args.against)
            if only_lines is None:
                print(f'prove_checks: could not ask git what changed in {rel}.', file=sys.stderr)
                return 1
        for change in full:
            if only_lines is not None and change['line_number'] not in only_lines:
                continue
            jobs.append((rel, checks, text, change['text'], change['id'], change['line_number']))

    # THE FLOOR. Reporting success over an empty run is the exact shape this
    # tool exists to catch. Files in scope with nothing to try means the change
    # touched only comments, or was a pure rename, or -- worst -- weakened a
    # CHECKS file while leaving its source alone.
    #
    # A CHECKS-ONLY CHANGE IS A REAL AND ORDINARY THING, and refusing it outright
    # was wrong: closing the backlog of code nothing checks is BY DEFINITION a
    # change to checks files with no source touched, so the work could never be
    # committed at all. That was found the first time anybody tried.
    #
    # What is honest about it, said rather than papered over:
    #
    #   - Nothing here proves the NEW checks catch anything. Proving the whole of
    #     every source they cover would block on every gap already known and
    #     being worked through, which would refuse the very commits that close
    #     them.
    #   - What DOES still protect a weakened checks file: every checks file must
    #     pass, and each carries a count of how many checks it runs -- so a check
    #     that is deleted is caught by its own file, every time. A check whose
    #     assertion is quietly loosened is NOT caught, and that is the gap this
    #     leaves. It is why a checks-only change still needs a reader.
    #
    # So it is allowed, and it says exactly what it did not do.
    checks_only = is_checks_only(wanted, jobs, scoped, touched)
    if checks_only:
        print()
        print('prove_checks: this change touches checks files and no source, so there are no '
              'new lines to break.')
        print('  Nothing here proves the new checks catch anything -- a checks file each one '
              'covers must pass, and')
        print('  each file counts its own checks, so a DELETED check is still caught. A check '
              'quietly loosened is not.')
        print('  Prove new checks yourself against the code they cover: '
              'python tools/prove_checks.py --only <source file>')
        print()
    elif wanted and not jobs:
        problems.append(
            'there are ' + str(len(wanted)) + ' file(s) in scope and not one deliberate change '
            'to try on them. That happens when a change touches only comments or when a file was '
            'renamed rather than edited. Say which it is, or widen the scope: '
            'python tools/prove_checks.py --only <file>')
    if not wanted and not problems:
        print('prove_checks: no source file with checks is in scope for this change.')
        return 0

    # AND THE CHECKS HAVE TO PASS WITH NOTHING CHANGED, before a single change
    # is tried. Otherwise every mutant is "caught" for a reason that has nothing
    # to do with it, and a broken checks file scores a perfect hundred per cent.
    patience = TIMEOUT_SECONDS
    if jobs:
        broken, slowest = baseline_passes(str(ROOT), [job[1] for job in jobs])
        # Four times as long as the checks take when nothing is wrong, and never
        # less than the written-down limit. Anything slower than that is not
        # slow, it is stuck.
        patience = max(TIMEOUT_SECONDS, int(slowest * 4) + 5)
        for one in broken:
            problems.append(one)
        if broken:
            print()
            print('prove_checks: refusing to prove anything -- the checks do not '
                  'pass with nothing changed.')
            print()
            for one in broken:
                print(f'  - {one}')
            return 1

    workers = args.workers or min(8, (os.cpu_count() or 2))
    results = []
    if jobs:
        print(f'prove_checks: {len(jobs)} deliberate changes across '
              f'{len(wanted)} file(s), {workers} at a time, stopping any that '
              f'takes longer than {patience}s. This takes a while.',
              flush=True)
        with ProcessPoolExecutor(max_workers=workers,
                                 initializer=_prepare,
                                 initargs=(str(ROOT), patience)) as pool:
            for done in pool.map(_try_one, jobs):
                results.append(done)

    counted = tally(results)
    survivors = counted['survived']
    unparseable = counted['unparseable']
    timed_out = counted['timed out']
    caught = counted['caught']
    crashed = counted['crashed']

    accepted = load_accepted()
    problems.extend(badly_written(accepted))

    tried = {mutant_key(job[4]) for job in jobs}
    unexpected, stale = judge(accepted, survivors, tried)
    unexplained_crashes = unrecorded(crash_reasons(), crashed)
    # A change that crashed is not a survivor, so an accepted entry naming it
    # would be judged stale -- but its change WAS tried and it did what the
    # entry says. Left standing.
    still_standing = {mutant_key(hit['id']) for hit in crashed}
    stale = [entry for entry in stale if mutant_key(entry) not in still_standing]
    stale = stale + [entry for entry in vanished(accepted, texts)
                     if entry not in stale]
    stale = stale + [entry for entry in impossible(accepted, whole_plan)
                     if entry not in stale]

    if args.json:
        with open(args.json, 'w', encoding='utf-8') as handle:
            json.dump([{**hit['id'], 'line_number': hit['line_number']}
                       for hit in survivors], handle, indent=2, ensure_ascii=False)

    print()
    runnable = len(results) - len(unparseable)
    print(f'  changes tried      {len(results)}')
    print(f'  actually run       {runnable} (the rest would not parse)')
    print(f'  caught by a check  {len(caught)}')
    print(f'  ended in a crash   {len(crashed)} (noticed, but by the file failing to load)')
    print(f'  would not parse    {len(unparseable)} (discarded, not counted as caught)')
    print(f'  hung and stopped   {len(timed_out)} (counted as caught)')
    print(f'  survived           {len(survivors)}')
    print(f'  survived, accepted {len(survivors) - len(unexpected)}')
    print()

    for hit in sorted(unexpected, key=lambda r: (r['id']['file'], r['line_number'])):
        ident = hit['id']
        print(f"NOT PROVEN  {ident['file']}:{hit['line_number']}  ({ident['operator']})")
        print(f"            {ident['line']}")
        print('            Changing this is not noticed by the checks named for the file.')

    for entry in stale:
        source = texts.get(entry.get('file'))
        plan = whole_plan.get(entry.get('file'))
        if source is not None and entry.get('line', '') not in source:
            why = 'and that line is not in the file any more.'
        elif plan is not None and mutant_key(entry) not in plan:
            why = ('and that change cannot be made any more -- the line is still '
                   'there, but not that many times.')
        else:
            why = 'and it no longer survives.'
        print(f"STALE       {entry['file']}  ({entry['operator']})")
        print(f"            {entry['line']}")
        print(f'            Recorded as an accepted survivor, {why}')
        print('            Remove the entry -- a list that is not true is worse than no list.')

    for hit in sorted(unexplained_crashes, key=lambda r: (r['id']['file'], r['line_number'])):
        ident = hit['id']
        print(f"CRASHED     {ident['file']}:{hit['line_number']}  ({ident['operator']})")
        print(f"            {ident['line']}")
        print('            The checks file could not run at all, and no reason is '
              'recorded for')
        print('            this file. The change was noticed -- but by')
        print('            the file failing to load, not by a check going red, so it says '
              'nothing')
        print('            about whether the checks are any good.')

    problems.extend(measured_nothing(len(jobs), runnable))
    problems.extend(answered_by_the_clock(timed_out, runnable))

    for note in problems:
        print(f'COVERAGE    {note}')

    code, last_word = verdict(unexpected, unexplained_crashes, stale, problems, checks_only)
    print(last_word)
    return code


if __name__ == '__main__':
    sys.exit(main())
