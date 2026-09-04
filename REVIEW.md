# What a review of this repository found

Newest at the top. A review is of a moment, so each one is dated and nothing in
an older one is edited afterwards.

---

## 2026-09-04 (sixth) — A6R on M7's three commits. IT HOLDS: nothing found lets a bad commit through. Two findings, both prose, both left to the author.

**Reviewed against** `D:\Kartaan-ERP\DECISION_LOG.md` — D166, D169, D170, D172,
D175, D179, D180, D181, read there read-only, and D158 for the push. **Scope:
`D:\Kartaan-AutoSync` only**, the three commits `05f418b`, `f2dd79d`, `b1cd092`.
**I repaired nothing** (D166). Every fault I put back went into a copy of the
repository in scratch; this folder was never written to until this entry.

**THE TREE DID NOT MOVE.** 121 files fingerprinted by content on entry and again
before this was written — all 121 byte-identical, working tree clean, `HEAD` at
`b1cd092` throughout (D181).

**THE BAR I WAS GIVEN:** only something that lets a bad commit through blocks.
Neither finding below can. Both are sentences in comments that no check reads.

---

### What holds, measured on the committed tree

| | |
|---|---|
| `tools/gate_checks.py` | **113 pass, 0 red** |
| `tools/gate_run_checks.py` | **50 pass, 0 red** |
| The register's `163 checks` | **113 + 50 = 163.** Counted, not read |
| `41 faults` / `6 questions` | Counted off the file's own `BREAKINGS` and `ASKED` by parsing it, not by trusting the prose |

---

### FINDING A — THE UNCHECKED `update-ref` WAS A REAL HOLE, AND I RE-DROVE IT MYSELF RATHER THAN TAKE IT

The fifth round (M3R, below) filed it *"small"* and *"harmless today"*. **It was
not.** The author said so, and I did not take the author's word for it either.

A move that cannot work put back in place of the real one — `git update-ref HEAD`
pointed at a well-formed forty-character id this repository does not have — in
two copies that differ by nothing but the five lines that ask whether it worked:

| The copy | The run |
|---|---|
| **With the check** (as committed) | **47 RED of 50**, exit 1 |
| **With those five lines deleted** | **all 50 GREEN**, exit 0 |

**That is the whole difference between a run that stops and a run that lies.**
Without the check, `HEAD` stays wherever the clone left it and every one of the
fifty questions is asked of the wrong commit, confidently, in green. It is
D175's shape — a prover that cannot fail — in the prover written to close D175.
**The correction is right, and the round that called it cosmetic was wrong.**

### The other four counts, each measured against what is there

| The claim | How I measured it | Answer |
|---|---|---|
| 41 faults, not thirty-eight | parsed `BREAKINGS` | **41** |
| six questions, not five | parsed `ASKED` | **6** |
| eleven checks red from the commit-hook fault, not seven | emptied `NOT_CODE` in `.githooks/commit-msg`, ran `gate_checks.py` | **11 red, 102 pass** |
| runner-first is 12 red, not 9 | built the runner-first tree — `936b0e3` plus `f2dd79d`'s six files, hooks left as they were — and ran `gate_checks.py` | **12 red, 101 pass** |
| merge-fix-first leaves commit one green | ran `gate_checks.py` on `05f418b` itself | **91 pass, 0 red** |

**And the order the commits were actually made in matches the order that was
measured.** `05f418b` (00:36) is the parent of `f2dd79d` (00:57), which is the
parent of `b1cd092` (01:38). The merge fix went first. Had the runner gone first,
commit one would have carried 12 red checks — the twelve that drive the real
hooks through D173's merge, which did not exist yet.

---

### FINDING B — non-blocking. The ERP count of 25 is true of the sentence as written and is not the number the argument needs.

`tools/gate_run_checks.py:44` says the ERP has **twenty-five** commits *"already
in the history and carrying no tag"*, where it first said eleven. Measured in
`D:\Kartaan-ERP` read-only, walking `master` with that repository's own
`GATE_BORN`, its own anchor and its own exemption list:

| What was counted | How many |
|---|---|
| Commits at or after `GATE_BORN` whose message carries no tag | **25** |
| **Of those, the ones that change code** — the only ones the walk ever asks for a tag | **11** |
| The other 14 | touch nothing but exempt files, so the walk skips them whatever the marker says |

The paragraph exists to say what a `GATE_BORN` moved forward could **hide there
and cannot here**. A commit the walk skips hides nothing, so the number that
carries the argument is **11** — the number the entry had before it was
corrected. 25 is a true count of a wider set than the sentence is about. **This
is D169 from the other side: the number was measured, and what the sentence
CLAIMS was not re-asked.**

**It cannot let a bad commit through** — no check reads it, and the ERP's own
gate is unaffected either way. Left to the author.

**The other half of the same sentence I checked, and it holds.** *"This
repository has none"* is true under **both** definitions: all 10 AutoSync commits
at or after `d538efd` carry `[PM-REVIEWED]` on a line of its own, and there is no
untagged commit in reach of any kind. The comparison is not resting on two
different questions.

### FINDING C — non-blocking. THE THIRD INSTANCE. `b1cd092` fixed the second; there is a third, of exactly the same shape.

`b1cd092` exists because a count was corrected in the file's opening and the
identical sentence 200 lines below was left standing. **The same thing happened
to the other count in the same batch**, and neither sweep caught it:

`tools/gate_run_checks.py:430`

> *"every commit this rule reaches already carries the tag, which the last of
> **the five questions** above measures"*

**There are six.** The file says so at line 185 (*"any of the six above"*) and the
register says `6 questions`. Both were corrected; this one was not.

**And it is worse than a stale number, because it points at the wrong question.**
The question that measures *"every commit the rule reaches passes"* is the
**fifth** of the six — *"AND EVERY COMMIT THE RULE ALREADY REACHES PASSES"*, the
whole history walked as a first push. When there were five it was the last one and
the sentence was right. With six, **"the last" is now question six**, the
divergent-branch question, which measures something else entirely. A reader sent
to it finds no such measurement and has no way to tell which of the two is wrong.

Introduced by `f2dd79d`, this round. **It cannot let a bad commit through** —
which question judges that fault is decided in code (`PASSES_THE_REVIEWED`) and
is not touched by the sentence. Left to the author.

**I swept for a fourth and did not find one.** Every count in the five changed
files naming checks, faults, questions, commits, places, copies, hooks or steps
was pulled out and grouped by what it claims; the only outlier was line 430.
`REVIEW.md`'s "5 questions / 30 faults" sit inside dated entries this file
forbids editing, and the "four checks pinned to the siblings" pair predates this
round (`d538efd`).

---

### Where I could not satisfy myself

- **The intermittent crash in the prover did not happen to me.** Six full runs of
  `gate_run_checks.py` and `gate_checks.py`, and not one `WinError 267`. I did
  not reproduce it, so I cannot say what it is; the author's account of it stands
  as the only measurement of it, and it makes the prover REFUSE rather than pass.
- **Nothing was run on GitHub.** Everything is bash on Windows against this
  machine's git. GitHub's behaviour on a skipped job, on `continue-on-error` and
  on `refs/pull/N/merge` is still taken from documentation.
- **I did not count leftover temporary folders as evidence of anything.** Windows
  deletes them lazily; a finished run settles to nought or one, and the author's
  own near-miss on this is what stopped me making the same claim.
- **The ERP was opened read-only**, to read eight decisions and to measure that
  one count. The Server was not opened.
- **I read the three commits and the files they touch.** Nothing else in this
  repository was re-reviewed; it has been read cold three times already.

---

## 2026-09-03 (fifth) — M3R on the D172 runner. NOT COMMITTED: the runner is right about the two blocks it runs, and everything around them still holds nothing.

**Reviewed against** `D:\Kartaan-ERP\DECISION_LOG.md` — D170, D171, D172, D173,
read there read-only. **Scope: this repository only.** I wrote no product code, I
did not read the author's report before measuring, and every file I touched was
restored and the restore verified by `sha256sum` against a copy taken first.
**I refused to commit.**

---

### What holds. Run, not read.

| | |
|---|---|
| `tools/gate_checks.py` | **103 pass** — 109 less the six reading checks |
| `tools/gate_run_checks.py` | **35 pass** — 5 questions, 30 faults put back, all 30 caught |
| Total | **138**, as claimed |
| The register against disk | no refusals, with both new files owned by `the-gate` |

**THE FIFTH QUESTION IS ASKING FOR THE RIGHT ANSWER ON A PUSH, AND I CHECKED IT
RATHER THAN TAKING IT.** I walked all 18 commits with the workflow's own rule by
hand. Seven sit inside the reach (`d538efd` onwards); **all seven carry the tag on
a line of its own**, not merely in prose; there are **no merge commits at all**.
So there is genuinely nothing behind the marker to hide, a refusal is not
available to ask for, and demanding a PASS is correct. The author's claim that it
"does not port cleanly" is true for the reason given.

`tools/gate_run.py` itself is careful in the places that usually go wrong: real
YAML parser, real bash with `-e`, real git, a **skipped** step modelled as the
success GitHub counts it as, `walked` asserted separately so a gate that never ran
cannot look like one that passed, and every `GIT_`-prefixed pointer swept rather
than listed.

---

### FINDING 1 — BLOCKING. The gate can be switched off with one line, in three different places, and all 138 checks stay green.

The runner reads `jobs`, finds the job by a step name, and runs the two `run:`
blocks. **Nothing it does looks at anything else in the file**, and the reading
checks that survive are `in WORKFLOW` substring tests. Three faults put back one at
a time, each restored and verified byte for byte:

| The line | What it does on GitHub | gate_checks | gate_run_checks |
|---|---|---|---|
| `if: github.repository_owner == 'kartaan-com'` **`&& false`** | the whole job never runs — tag walk, secret scan, every checks file | **103 pass** | **35 pass** |
| **`continue-on-error: true`** added to `Every code commit carries the review tag` | the walk still refuses and the run stays green — the refusal becomes advice | **103 pass** | **35 pass** |
| `on: push/pull_request` replaced by `on: workflow_dispatch:` | the workflow never fires on a push to `main` at all | **103 pass** | **35 pass** |

The first one **still contains the exact string** `github.repository_owner ==
'kartaan-com'`, so the check named *"IT RUNS ONLY IN KARTAAN'S OWN
ORGANISATION"* passes while the job it names is dead. That is D172's own table —
"a second assignment below the first", "`export` in front of it" — one level up
from where the runner looks. **There is no last spelling outside the `run:` block
either.**

The second is the sharpest of the three: it is inside the very step this whole
change exists to prove, it is one word of YAML, and it reads as a considerate
thing to add.

### FINDING 2 — BLOCKING. On a pull request the fifth question must fail, and all 30 fault checks then pass without proving anything.

`actions/checkout@v4` on a `pull_request` checks out `refs/pull/N/merge` — a merge
commit **GitHub** makes, whose message is `Merge <sha> into <sha>` and which
carries no tag. `History` clones and detaches at that commit, and the fifth
question walks the whole history up to it. Measured, with a real merge commit
carrying GitHub's own message:

```
::error::commit 395b0c1... changes code and carries no [PM-REVIEWED] tag
MISSING=1  ->  the walk REFUSES.   The fifth question demands a PASS.
```

The workflow's own tag walk is right about this — on a PR it uses
`merge-base(base, head)..head`, so it never walks GitHub's merge commit. **The
runner does not follow it there.** `History.base` is whatever is checked out.

**And the consequence is larger than one red check.** A fault counts as caught
when **any** of the five questions answers wrong, and `FASTEST_FIRST` reaches the
fifth. With the fifth permanently wrong on a PR, **all 30 fault checks pass
vacuously** — the file reports 34 of 35 green while proving nothing at all. This
repository pushes straight to `main`, so it may never be seen; the workflow
declares `pull_request:` regardless.

### FINDING 3 — D173's merge is live in this repository's hooks, and question four asks the surface instead of the question.

D173 says it in terms: *"Did anything demand that somebody read this — not did the
tag land. The tag is the surface, and in exactly the broken case the surface is
green."* Question four asks an **untagged** merge to be refused. That is the loud,
safe case. The dangerous one is a merge that lands **tagged**, and CI cannot see
it by design.

Driven through this repository's real `commit-msg`, in a throwaway repository with
git's pointers stripped, with a `review_pass.json` left over from an earlier gate
run:

```
git merge --no-ff side          (the files merge cleanly)
  PRE-COMMIT RAN                -- absent. It never ran.
  COMMIT-MSG RAN
  gate: [PM-REVIEWED] added, and the review record is used up.
Merge made by the 'ort' strategy.   exit=0
the message that landed:  an unreviewed merge, nobody read this
                          [PM-REVIEWED]
the review record:        CONSUMED
parents:                  2
```

**A merge nobody read reached the commit wearing the review tag, and the workflow
passes it** — correctly, by its own rule. The half that demands a record never
ran. `.githooks/commit-msg` already knows *"`git merge` runs commit-msg and NEVER
runs pre-commit"*, in a comment added by this same change; nothing anywhere asks
the question, and it is not in "what is still not covered" either.

### FINDING 4 — the note over the deleted six says the wrong thing about what is left.

> *"What is left in this file about that workflow is what running it cannot say:
> that what counts as code is spelled the same way in all three places."*

**Twelve reading checks over that workflow are still in the file** — the secret
scan, node, the recipes, the tracked record, the seller-account guard, the empty
tree sentinel, the rewritten-history refusal, `GATE_BORN` being a real forty
characters. Keeping them is defensible; they cover steps the runner does not run.
Saying only one is left is not, and finding 1 is what one of the twelve costs.
D170, and it is the same shape as D169's own fourth instance.

### FINDING 5 — a `proved_by` in the register names a check that cannot fail for it.

`tools/work.json`, `the-gate`, second finding: the seller-account guard is
*"proved_by: tools/gate_checks.py -- 'IT RUNS ONLY IN KARTAAN'S OWN
ORGANISATION'."* Finding 1 measured that check green with the guard switched off.

### FINDING 6 — this round is not written down.

`REVIEW.md`'s newest entry is the fourth, and it still closes with
**"Nothing runs `.github/workflows/pm_check.yml` ... Not built, and not
claimed."** It is built. Nothing in the file records the D172 work, the six
deleted checks or the thirty faults, and the register carries no finding for it
either. (This entry is mine, not the author's.)

### FINDING 7 — small, and against this file's own rule.

`run_the_gate` moves the clone's `HEAD` with `git update-ref` and **does not look
at whether it worked**. It is the one subprocess in `gate_run.py` outside `_must`,
in a file whose opening paragraph says it raises rather than guesses. Harmless
today — `HEAD` already sits on a descendant, so the two ancestry guards answer the
same either way — which is exactly why a failure here would never be noticed.

### FINDING 8 — an observation, not a fault, and it should be written down before it becomes one.

`TAG_ANCHORED_FROM` is `936b0e3` — **the current HEAD**. Every commit in this
history is at or before it, so **the strict, anchored form governs no real commit
at all today**, and the fifth question exercises only the loose branch against
real history. The strict branch is genuinely exercised, but only against the probe
commits. The file explains why the marker's value is unobservable here; unlike the
`GATE_BORN` paragraph, that explanation has **no tripwire under it** — no check
goes red the day a commit lands that mentions the tag without carrying it.

---

### Where I could not satisfy myself

- **Only two steps of the workflow are ever run**, here or by the runner. The
  secret scan, the sibling checkouts, the checks sweep and the board are still
  read and not run — D171's own category. The runner says so; it is still true.
- I checked the register's own rule and did not run the full sixty-file check
  sweep.
- **Nothing outside this repository was reviewed.** The ERP was read for D170 to
  D173 and nothing else; the Server was not opened.
- Everything was driven under `bash` on Windows against this machine's git, and
  GitHub's behaviour on the job `if`, on `continue-on-error` and on
  `refs/pull/N/merge` is taken from GitHub's documentation, not from a real run.

---

## 2026-09-02 (fourth) — M2R reviewed the replaced fix, and its six findings are closed

**Reviewed against** `D:\Kartaan-ERP\DECISION_LOG.md`, which D40 calls binding.
**M2R held all three repositories and wrote no code.** It read the diff cold, did
not read the author's report, and measured git itself rather than the comments
about it. **It refused to commit.** Everything below is what it found and what the
author then did — and the author is not the reviewer, so **this change has NOT yet
been independently reviewed.**

---

### What M2R confirmed by measuring, not reading

Real commits against git 2.52: git cuts at **exactly** 24 dashes each side (23 and
25 are kept whole); it cuts under `core.commentString=REM` and `core.commentChar=;`;
it keeps everything in the default cleanup and under `--cleanup=whitespace`. The
hook's pattern matches every case git cuts and none it keeps. **Two things nobody
had written down:** `core.commentString=//` makes git write ONE slash, not two;
and `--cleanup=scissors` only cuts **when the message is edited**, so `git commit
-F` with scissors and no `-e` does not cut at all.

It put **twelve faults back by hand in the ERP, four here, two in AutoSync.** Nine
of the twelve turned exactly one named check red and named the right one. Four
turned nothing red. Those four are findings 3 to 6.

---

### The six findings, and what was done

| # | Finding | Closed by |
|---|---|---|
| 1 | `.githooks/commit-msg` said *"The tree test above catches the case where nothing at all changed"* — **and there is no tree test in this file, or anywhere in this repository.** The sentence was copied from the ERP with the paragraph around it, inside the change whose purpose was to stop this gate claiming what it does not do | The sentence is corrected and says what actually covers that case here: `tools/gate.py` refuses an empty staged list before this hook runs, and **D163's free path is the ERP's and is not built here.** A new check drives that refusal, so the claim is held by something |
| 2 | *"they were reviewed and they carry the tag"* was still written in the workflow comment and in the check's own name, in all three repositories — **D164 withdrew that claim the same evening** and the log now says the opposite | Corrected in all six places to what D164 says: they WERE reviewed, a record was demanded and consumed for each, and the hook then found its own name in the author's prose and **appended nothing.** That is the bug caught in the act |
| 3 | *"a message that merely looks like it has a cut line is not damaged"* **could not go red for the fault it names.** Nothing is ever deleted now, so a lookalike mistaken for a cut line costs nothing; loosened until it matched, every check stayed green | The check now asks **where the tag lands** — left alone it goes at the end, below the author's last word; mistaken for a cut line it goes above. Position is the only difference, and it is now the thing asserted |
| 4 | (ERP) D163's tree comparison could be swapped for the `nothing is staged` test **the decision forbids by name**, green | (ERP) A `git` that answers the staged list emptily is put in front of the hook while the index really does differ from HEAD. The two questions are made to disagree, and the gate must refuse |
| 5 | The refusal for a git that cannot say what is staged — **a reviewer's own finding, added by this change** — had no check at all. Deleted, all 109 checks stayed green | A new check drives the real hook against a **really damaged `.git/index`**, which is the case the hook's own comment names, and asks for the hook's own words |
| 6 | *"anchored to a WHOLE LINE"* asked only that the pattern starts with `^` and ends with `$`. `^.*\[PM-REVIEWED\].*$` does both and anchors nothing: changed at both sites together, every check stayed green and the GitHub side went back to a substring test | The pattern is now **fed to the same `grep -qE` both sites use** — a sentence that merely mentions the tag must not match, the bare tag must |

**Found while fixing 6:** handed to a Git-for-Windows tool as an argument, a
pattern arrives with its backslashes eaten — the child was given
`^[PM-REVIEWED]...`, a character class matching any one of those letters. Asked
that way the check would have gone **red on correct code and green on the fault.**
The pattern and the message are read from files now.

---

### Every check in this change, broken the way its own rule is written

Nineteen faults were put back one at a time, each on its own, with every touched
file restored and the restore verified byte for byte. **Not one of them left the
checks green.** The four that used to are the four findings above.

The four that turn on **two** named checks rather than one do so honestly — a
cut-line pattern that recognises only `#` breaks both the `;` case and the `REM`
case; a shortened anchor breaks both the pinning and the forty-character rule.

### What is still not covered, said plainly

**Nothing runs `.github/workflows/pm_check.yml`.** Findings 4 and 6 both existed
because that file is only ever read as text. What would settle it: run that
workflow's shell against a fabricated history. Not built, and not claimed.

---

## 2026-09-02 (third) — M1R: the replaced fix, and why it is still uncommitted

## M1R — NOT COMMITTED. The hooks are right; the checks guarding them are not, and two decisions they cite do not exist.

**Reviewed against** `D:\Kartaan-ERP\DECISION_LOG.md`, which D40 calls binding.
This is a second review, of a **replaced** diff. Nothing from my earlier record was
carried forward — every round below was run again from scratch against the code
as it stands now.

---

### What holds. Driven, not read.

Seven behaviours, run through the real hooks in throwaway repositories with git's
own environment pointers stripped first:

| | ERP | Server | AutoSync |
|---|---|---|---|
| `git commit -v` — tag reaches the **commit**, diff does not leak in | 1 / 0 | 1 / 0 | 1 / 0 |
| A message that merely *looks* like it has a cut line is not damaged | survives | survives | survives |
| A **real** 24-dash cut line, no `-v` — git keeps it, and so does the hook | survives | survives | survives |
| Amend, same tree, HEAD tagged → tag carried + `[NO-CODE-CHANGE]` | 1 / 1 | **0 / 0** | **0 / 0** |
| Amend, same tree, HEAD untagged → no tag invented | correct | — | — |
| Broken index → the tag hook **refuses** | exit 1 | exit 1 | exit 1 |
| Cut line on line 1 → left alone | correct | correct | correct |

**My previous blocking finding is genuinely fixed.** The truncation is gone; the
tag is inserted above the cut and nothing is deleted. **My previous finding 2 is
also fixed** — a damaged index now makes the tag hook refuse instead of exiting 0
silently, in all three.

**The amend-cannot-be-detected comment is honest.** I checked it rather than
believing it: I dumped every `GIT*` variable and the whole `.git` directory
listing during a hook run, for an ordinary commit and for an amend. **Byte for
byte identical, and no marker file.** The claim does not overclaim, and its
pointer to `pm_check.yml` as the layer that catches it is sound — an amended
commit still shows its code against its real parent, so a dropped tag is refused
there.

**Faults put back, named checks red:** the git-cannot-answer refusal removed
(3 red), the cut line narrowed to `#` only (1 red), the tag no longer carried
across a rewrite (1 red), `[NO-CODE-CHANGE]` removed (1 red), the D163 free path
removed (3 red), the CI pattern back to a substring (2 red).

---

### FINDING 1 — BLOCKING. The worst regression this change has ever had can be put straight back, and every check still passes.

Draft two of this fix silently deleted the author's own paragraphs from a commit
message. That was the finding that stopped the last round. **I reintroduced it
with a three-line edit:**

```
survived = 0   <-- the hook deleted the author's words
  PM Discipline: [PM-REVIEWED] added, review record consumed.
all 445 checks passed
```

Same result in all three: **Server 105 passed, AutoSync 103 passed**, with the
data loss present.

**Why nothing notices.** The check named *"AND A MESSAGE THAT MERELY LOOKS LIKE IT
HAS A CUT LINE IS NOT DAMAGED"* feeds the hook `------ >8 ------` — six dashes.
Neither git nor the hook cuts at that line, so the truncation path is never
entered. **The check exercises the case where nothing happens.** No check in any
of the three repositories puts a real 24-dash cut line inside a message git will
keep — which is the only shape that can lose anything.

By D156's own standard, this part is not finished: the fault goes back and no
named check goes red.

### FINDING 2 — LIVE. `core.commentString` with three or more characters loses the tag, exactly as before.

The hook says it covers `core.commentChar`, `core.commentString` and `auto` by
allowing "ANY single character". **`core.commentString` is not limited to one
character.** Measured against real commits:

| setting | what git writes | tag in the commit |
|---|---|---|
| `core.commentChar=#` | `# ---- >8 ----` | 1 |
| `core.commentChar=;` | `; ---- >8 ----` | 1 |
| `core.commentString=//` | `/ ---- >8 ----` (git keeps one char) | 1 |
| **`core.commentString=REM`** | **`REM ---- >8 ----`** | **0** |

`^. -{24}` cannot match three characters, so the hook finds no cut, appends at the
end, git discards it — and the hook prints that it added the tag. **The original
bug, in full, in a supported configuration.**

The check named for this says *"`core.commentChar` **and** `core.commentString`
are ordinary settings"* — and its fixture only ever sets `core.commentChar=;`. It
tests the easy half of its own claim.

### FINDING 3 — the CI's anchored rule can be switched off, and nothing notices.

Change one line — `TAG_TEST="$TAG_ANCHORED"` to `TAG_TEST="$TAG_BEFORE_THAT"` —
and **every** commit is judged by the loose substring rule for ever. The strict
pattern stays in the file, correctly spelt, and entirely dead. **All checks green
in all three repositories.** The checks assert the pattern's *spelling* and that
the loose branch *exists*; nothing asserts which branch is reached.

### FINDING 4 — the anchor can be moved, and nothing notices.

I replaced `TAG_ANCHORED_FROM` with a different 40-character ancestor. **No check
went red.** The checks pin that there is exactly one, that it is 40 characters,
and that an ancestry test is performed — never *which commit*.

So a commit failing the strict rule is fixed by moving the anchor past it: a
one-hash diff, indistinguishable from a correction. D164 says a marker names
where a rule started, "never which commits were let off" — **an unpinned movable
marker is a let-off list, written as a range.** In the ERP, `GATE_BORN` — the
stronger lever, which exempts commits outright — is pinned by nothing at all;
`status_checks.py` mentions it only in a comment. Server and AutoSync do check
theirs.

### FINDING 5 — the anchor's stated reason is false for the only two commits it actually exempts.

I walked all three histories rather than taking this from anyone:

| repo | commits the anchor actually lets through |
|---|---|
| ERP | **none** — every code commit after `GATE_BORN` already passes the strict rule |
| AutoSync | **none** — same |
| Server | **exactly two**: `e374995`, `b1904b1` |

**The anchor exists for those two commits and nothing else.** The comment and the
check both justify it as *"they were reviewed and they carry the tag; the check
got stricter, they did not get worse."* **They do not carry the tag** — they
mention it in prose, one of them inside a quoted error message. That is the whole
reason they need exempting. Both are substantial, self-documenting commits and
were very probably reviewed, but that is not provable from the repository, and
"they carry the tag" is plainly untrue of them.

### FINDING 6 — D163 is built in one repository of three.

`NO-CODE-CHANGE`, `write-tree`, `D163`: **zero occurrences** in
`Kartaan-Server` and `Kartaan-AutoSync`, in the hook and in `tools/gate.py`.
Driven there, an amend drops the review tag and records nothing (the table above).
In practice their `gate.py` refuses every amend, so no tag is lost today — but the
free path D163 describes does not exist, and the two conditions that protect it
are absent.

### FINDING 7 — the anchor does not reconcile the ERP's history, and three pushed commits still carry code with no tag at all.

The anchor only relaxes strict to loose. It does nothing for commits carrying no
tag under **either** rule, and the ERP has them, already pushed, after `GATE_BORN`:

| commit | carries | tag |
|---|---|---|
| `0e241eb` | `src/modules/products/assign-file.js`, `catalogue.js`, … | none |
| `89425a8` | `src/modules/products/assign-file-screen.js` | none |
| `be4237b` (merge) | `firestore.rules`, `guides/costing.html`, `DECISION_LOG.md` | none |

plus several `docs:` commits carrying `DECISION_LOG.md`, which became code when
D99 scoped the `.md` exemption to paths. **The tag rule was tightened and given an
anchor; the not-code rule was tightened and given none.** I could not determine
whether CI has ever walked these — that needs the Actions history, which I cannot
reach from here.

### FINDING 8 — the code is built to two decisions that are not in the decision log.

`.githooks/commit-msg`, `.githooks/pre-commit`, `.github/workflows/pm_check.yml`
and `tools/status_checks.py` all cite **D163** and **D164** as their authority.
`DECISION_LOG.md` ends at **D156**. There is no D157, D158, D159, D160, D161,
D162, D163 or D164, in any of the three repositories.

D40 makes that log binding and requires a logged entry — this is the rule the
gate itself enforces, with a lock of its own, and the change is on the wrong side
of it. **And I am still told to push per D158, which also does not exist.**

---

### Where I could not satisfy myself

- **Nothing runs `pm_check.yml`.** Findings 3 and 4 are both consequences: the
  workflow is only ever read as text, so which branch is taken and which commit
  is named are unasked questions. What would settle it: a check that runs that
  workflow's shell against a fabricated history.
- **Whether CI has ever walked the untagged ERP commits in finding 7** — that
  needs the GitHub Actions history.
- Hooks were driven only under `bash` on Windows, against git 2.52.
- The secret scan, the board locks and the register were not exercised. This
  review is scoped to the tag, the cut line, the amend path and the anchor.

---

# One review of this repository as it stands — 2026-09-02

**Why this exists.** Nine commits reached GitHub with no record that anybody read
them, and 2,206 checks were green because a session remembered to run them. D156
does not have those nine re-reviewed one at a time, and does not have the history
rewritten — **this repository's history is copied into every seller's own GitHub
account.** Instead: one review of the code as it stands today, read against
`D:\Kartaan-ERP\DECISION_LOG.md`, and committed through the gate that was built
first, so it is not a file anybody could have written.

**It records what was FOUND. Not that it passed.**

**How independent it is, said plainly:** one session on one machine, so there was
no second pair of eyes. What it leaned on instead is the only thing that does not
care who wrote the code — **putting faults back one at a time and watching a
NAMED check go red.** 96 were put back across the reader's seven pieces before
this review, and 23 more against the ledger during it.

---

## FIXED BY THIS REVIEW

### 1. Two files of one report and one date silently overwrote each other

**D150 rule 3 says a same-date disagreement is KEPT and REPORTED, never a silent
pick.** The code applied that only when the two statements came from *different
reports*. Two files of the **same** report and the **same** data date — which is
exactly what a day fetched again produces (D110), and which `whats_new` correctly
calls a new file — looked like one statement. The second overwrote the first and
nothing said so.

Fixed: a `Reading` now carries **which file** it came from, and one statement is
one FILE, not one report. `whats_new.InTheFolder.which` is what goes there.

*Proved by:* `ledger_checks.py` — "RULE 3: TWO FILES OF ONE REPORT AND ONE DATE
ARE TWO STATEMENTS", and "but TWO ROWS OF ONE FILE are still one statement".

### 2. …and the fix was only half a fix. The sort still tied on the report.

Caught by the check written for finding 1, minutes after the first half went in.
The readings were sorted by `(date, report)`, so two files of one report and one
date **tied** — and a stable sort then keeps whatever order they were handed over
in. **The order of FETCHING decided which figure stood**, which is precisely what
D150 rule 2 exists to stop.

*Proved by:* "RULE 3: the order they were handed over in decides nothing", which
went red with the first half of the fix already in place.

### 3. The door still accepted the ERP's old folder name

`Kartaan` alongside `Kartaan-ERP`, left over from D148's rename. The rename is
done. A fallback nobody writes down is how two spellings of one thing survive for
a year.

*Proved by:* `firestore_door_checks.py` — "the door no longer accepts the old
folder name".

### 4. The door read the other repository's WORKING files, not its committed ones

Fixed earlier the same day and recorded here because it is the same class as the
rest. A check that reads another repository's working file goes green against
work nobody has committed — which can still change or be abandoned — and red
against work in progress. **It really bit:** the ERP has seventeen new ledger
columns written and not committed, so the check pinning the two column lists was
red against a file that, at the ERP's own HEAD, agreed exactly. **A gate built
while that was red would have refused the commit containing the gate.** It now
reads `git show HEAD:` and refuses if git cannot answer, with no fallback.

---

## FOUND AND NOT FIXED

### 5. What has been read grows for ever

`whats_new.now_read` never drops an id. At his volume that is roughly 7,000 file
ids a year, in a record that lives in the seller's own Drive. `between_runs.py`
caps its own history at `KEEP_RUN_DAYS`; this has no cap at all.

**Not fixed because the cap belongs where the record lives, and nothing carries
this across runs yet** (finding 6). Capping it here would be guessing at a
retention rule for a store that does not exist.

**STILL OPEN, and now it really does grow — 2026-09-02.** Finding 6 is fixed, so
the store exists. The cap is deliberately not in it, and the reason is not
laziness: `KEEP_RUN_DAYS` can trim safely because nothing reads further back than
the last day, and **nothing similar is true here.** Landed files are never
removed from the folder, so dropping an id whose file is still there makes that
file new again — and an old file re-read puts its old figures back over the newer
ones that had already corrected them (finding 7 is exactly why that is not
harmless). **Put to Jaiswal on 2026-09-02 with a recommendation rather than
picked quietly.**

**ANSWERED AND FIXED THE SAME DAY. His words: "cap on folder".**
`whats_new.still_worth_remembering` lets go of an id **only when its file has
gone from the folder** — never after so many days. The list is then a mirror of
the folder: it can never be longer than it, it shrinks the night he tidies Drive,
and no number was guessed at. An empty folder listing lets go of **nothing**, and
says why: that is what a listing looks like when it failed, and acting on it
would re-read the seller's whole history. *Proved by:* eight faults put back;
seven caught by a named check, **the eighth caught nothing** — the blanks check
was looking at what was KEPT when the fault came out in what was LET GO OF, so a
run log would have reported forgetting two files that never existed. Closed.

**AND IT SURFACED A REAL FAULT ELSEWHERE — finding 10 below.**

### 6. Nothing remembers which files have been read across runs

`between_runs.Between` has no field for it. Adding one bumps its `SHAPE`, which
makes an existing record refuse and stop the run — deliberate on that file's
part, and **costless today because no seller record exists anywhere.** Not done
here: that file has its own contract and 60 checks, and working code is not
touched without confirming first.

**FIXED 2026-09-02, by one field and nothing else.** `Between.files_read` holds
the Drive ids of the files that have been read, `SHAPE` went 1 → 2, and
`with_files_read` takes back what `whats_new.now_read` hands over. **The claim
that the bump is costless was checked rather than repeated:** there is no
`autosync-state.json` anywhere in the seller's Drive, and the only two scheduled
runs this repository has ever had both stopped at *"no platform is connected"*
before any of this code ran. **It is a LIST OF FILE IDS AND NEVER A DATE**, and
his own case is a check: three files land, the fourth fails, the fifth lands, the
fourth arrives later — and it is read. A high-water date would skip it for ever
and say nothing. *Proved by:* seven faults put back one at a time, six caught by
a named check and **the seventh caught nothing — a gap in the checks, not in the
code**, now closed by "a record holding the same file twice writes the same bytes
as one holding it once".

### 7. D150 rule 2 cannot be enforced ACROSS runs with the columns that exist

The ledger's 28 columns record no trace of **which file** last wrote each value,
so tomorrow's run cannot tell whether a cell came from an older or newer file
than the one it is holding. Harmless on ordinary nights — a new file is newer by
construction. **Not harmless for a by-hand backfill (D110)**, where a
deliberately old file is fetched after newer ones have written. Within one run
recency is now exact. Fixing it needs a column that is not in D152's list.

### 8. Ten files carry dead imports

`amazon.py`, `amazon_door.py`, `board.py`, `browser.py`, `browser_door.py`,
`clock.py`, `drive_door.py`, `landing.py`, `recipes.py`, `runner.py`.

**Reported, not touched.** They predate this session and are somebody else's
change to make; the two written this session were cleaned. Nothing depends on
them and nothing breaks.

### 9. The ERP's seventeen new ledger columns are written and NOT COMMITTED

D152 adds `status`, `isShopsy`, `cogs`, `packagingCost`, `adSpend`,
`returnReason`, the three conditions, the three losses, the three claim fields,
`netPnl` and `returnPnl`. They are in the ERP's working file and not at its HEAD.
**This side deliberately does not follow them** — matching uncommitted work in
another folder is matching something that can still change. `sales_checks.py`
pins the two lists, so whichever side moves alone goes red.

---

### 10. The folder listing was not paged, so it never saw a folder of 800 files

`drive_door.what_has_arrived` and `what_is_already_there` both call Drive's
`files.list` with **no page token and no page size**, and neither follows
`nextPageToken`. Drive returns one page and this code takes it as the whole
folder. His `flipkart\` folder holds roughly 800 files and `meesho\` roughly 470.

**This is worse than a cap problem, and it was found while building the cap.**
The reader would never even SEE the files past the first page, so they would
never be read at all — the folder cap then compounds it, because a short listing
looks exactly like a tidied folder and their ids would be let go of.

**FIXED THE SAME DAY, on his say-so: "fix the paging thing".** One pager for all
three listings, with every parameter read off Google's live reference first
(Golden Rule 1):

- `pageSize` asked for **explicitly** at Drive's documented maximum of 1000 —
  the default is not one number (100 for a shared drive, "the entire list"
  otherwise), and a page size that depends on which kind of Drive the seller has
  is one nobody can reason about.
- `nextPageToken` **asked for by name in the mask** and followed to the end.
- **A listing Drive itself calls `incompleteSearch` is refused, not believed** —
  its own words are *"some search results might be missing"*. That is a short
  listing that says it is short, and it is exactly what the cap must never act on.
- A page marker that comes back a second time refuses rather than looping.
- **The folder-by-name listing goes through the same pager.** It only wants to
  know whether there are none, one, or more than one — but a second folder of the
  same name on page two read as "exactly one", which would have put tonight's
  file somewhere else from last night's. The refusal that exists to prevent that
  was being undone by the listing beneath it.

*Proved by:* nine faults put back one at a time, **all nine caught by a named
check**, including the original fault itself.

**AND THREE OF THAT FILE'S OWN CHECKS WERE PINNING THE FAULT** — they asserted
the mask was exactly `files(id,name)`, which is precisely the thing that stopped
`nextPageToken` ever arriving. A check can hold a bug in place. They now pin the
fixed mask.

---

## FOUND IN THE REVIEWING ITSELF

These are worth more than most of the code findings, because they are about
whether any of the rest can be believed.

### 10. A proving harness destroyed uncommitted work with `git reset --hard`

It threw away a reviewer's fix to `firestore.py` and `firestore_checks.py` that
had been sitting in the working tree since 2026-08-31, and an uncommitted edit to
the workflow. Both were reconstructed from a diff captured earlier in the session
and re-proved. **A harness must never reach past what it created.** It now uses
`--soft`.

### 11. A check placed after a file's own verdict never runs. Twice in one day.

First in the gate's proving harness — a deliberate failure appended to the end of
a checks file, after its `sys.exit`, and the gate let the commit straight
through. Then again an hour later, in a check added to
`firestore_door_checks.py` by appending to the file.

**Anything after a checks file's own verdict is not counted.** Both were moved
above it. Neither was caught by reading; both were caught by the count.

### 12. Five checks written this session could not fail for what they were named for

Recorded in `tools/work.json` against their pieces. The pattern is always the
same: the sample did not actually trigger the fault, or the assertion was written
so it could not be false. **A green check is not evidence that a check works.**

---

## THE STANDING FACT

**Not one piece of this repository has ever run for real.** No Amazon call, no
byte uploaded to a real Drive, no document written to a real Firestore, no cell
written to a real Google Sheet, no alarm sent to anybody, and the nightly
workflow has never run. `start.py` — the one file that reads the real secrets and
opens the real connections — has no checks file of its own and has never been
executed.

Everything above is a review of code that is checked and has never been used.
