# What a review of this repository found

Newest at the top. A review is of a moment, so each one is dated and nothing in
an older one is edited afterwards.

---

## 2026-09-05 (eighth) -- A20R on `442599c`, the fresh pair of eyes A20 asked for before it could be pushed. **SAFE TO PUSH.** Seventeen faults driven; none of the three new checks can fail. **And it caught a wrong number in the entry below this one.**

`442599c` was committed on 2026-09-05 and deliberately left unpushed: A20 wrote
every line and read its own diff, and D158 requires an **independent** review
before anything goes to GitHub. This is that read, done when two later commits
needed it out of the way.

**Read at** `abd8536`, 93 tracked files, clean. **Reviewed against**
`D:\Kartaan-ERP\DECISION_LOG.md` -- D40, D158, D166, D169, D170, D174, D175,
D180, D190, D192, read there read-only. **Repaired nothing** (D166).
**Fingerprint of all 93 tracked files, sha256 over path plus bytes:**
`1e026c5c...1ab28e6` **before the work and the identical value after**, `git
status` clean both times. Every fault went into a throwaway copy.

### The counts, run in Python and not in a shell loop

**A20's own lesson, applied to the instrument that judged A20:** a Git Bash loop
hit its fork limit part way through and printed RED for a file that was never
STARTED. This sweeper reports NOT RUN and RED as two different things.

| suite | files | count | red | failed to start |
|---|---|---|---|---|
| `extension/*.test.js` | 5 | **414** | 0 | 0 |
| `autosync/*_checks.py` | 30 | **2,519** | 0 | 0 |
| `tools/*_checks.py` | 3 | **224** | 0 | 0 |
| **everything** | **38** | **3,157** | **0** | **0** |

### SEVENTEEN FAULTS DRIVEN. ALL THREE NEW CHECKS CAN FAIL, AND EACH REDDENS ALONE

Seven single-fault runs each reddened **exactly one** check out of 81 and left
the other 80 green -- D175 satisfied properly, not by "something went red".
Gutting the field to a stub reddens the presence check and only it; widening the
exemption list without the limit reddens the both-directions check and only it;
aiming the pointer at another file reddens the pointer check and only it. All ten
of A20's own claimed faults reproduced word for word, **including the two whose
expected answer was GREEN** and the cut-out that prints `checks went missing --
78 ran, 81 expected`.

Every byte count A20 claimed is exact, measured in Python on the bytes and never
with grep: `work.json` 1,214 to 1,234 CRLF with 0 bare LF both sides;
`sales_checks.py` 481 to 538 bare LF with 0 CRLF both sides; the diff 58/1 and
22/2 (D174 clean). Extension was **400** at `442599c`, exactly as claimed.

### FINDING -- **IT CAUGHT A WRONG NUMBER IN THE ENTRY BELOW THIS ONE, AND NOTHING HAD ASKED IT TO**

Reviewing `442599c`, A20R noticed that the record and the tree disagreed about a
**different** commit: the tree said 414 extension checks, the seventh entry said
412, and `active.md` said **432**. **432 was an arithmetic slip** -- 412 plus the
two new manifest checks is 414 -- **and it had been copied into three files at
once.** Corrected in all three, out loud (D169). *A review of one commit finding
a fault in the record of another is the argument for independent reads in one
line.*

### FOUR MORE, NONE OF THEM BLOCKING, ALL ABOUT WHAT IS **NOT** HELD

The bar is "does it let a bad commit through". None of these do. All four are the
same shape: **the thing this commit was ABOUT is held, and the reasons for it are
not.**

| what was driven | what the checks said |
|---|---|
| swapped 44 and 74 in the `sales_checks.py` comment, so it states the **opposite** of what the code does | **all 81 green.** The comment is a second, unheld copy of the limit |
| moved the field to the far end of `work.json` | **all 81 green.** **Placement is the entire justification of this commit** -- that the limit sits where somebody widening the list is standing -- and nothing holds it |
| deleted the four signpost lines beside the exemption list | **all 81 green.** The words a person actually meets can vanish silently while the field they point at stays held |
| changed the register's `81 checks` to 99 | **all 81 green.** The number this commit just un-staled is read by no check, and will go stale a fourth time |

**And one that is D169's own subject:** the comment states the limit in full and
then, eight lines later, says *"AND THE LIMIT IS NOT RECORDED IN THIS COMMENT,
BECAUSE NOBODY MEETS A COMMENT"* -- a confident sentence untrue of the eight
lines above it. A20's memory shows it knew and left it.

### What was looked for and not found

- **Working code touched needlessly:** none. The only two removals are the
  required `EXPECTED` 78 to 81 and the declared correction of a stale count.
  Every removed line was read.
- **Secrets:** nothing. Grepped for token shapes, for `googleapis` and Drive
  hosts, and for the seller strings this repository has leaked before -- the
  panel slug and the Drive folder id included. The only personal string anywhere
  is the author email in git's own metadata, already on every pushed commit.
- **A check that cannot fail:** none in this diff. Each of the three also reddens
  when `work.json` is deleted or made unreadable, and refuses rather than skips.

### What it could not settle

- Whether the pointer check reddens for a **wrong-case** path on the Linux
  GitHub runner. It is case-insensitive on Windows, so it is looser here than it
  will be there.
- Whether the sentence in the register is TRUE to a person reading it. The check
  holding it is a presence check, so 300 characters of nonsense would pass. A20R
  read it and found it accurate, but only a human read settles that.
- A verdict at an hour (D192): the sweep ran 18:41 IST, outside the
  18:30-UTC-to-midnight window. Nothing this commit adds reads a clock.
- **"Nothing in this repository has ever run for real, so 3,157 green checks
  still prove nothing about a real night."** Its words, and worth keeping.

---

## 2026-09-05 (seventh) -- A25R on A25's download-cancel commit. IT HOLDS as code. **One of its three claims was held by nothing at all**, and three of its comments said things that were not true.

**Reviewed against** `D:\Kartaan-ERP\DECISION_LOG.md` -- D175, D190, D174, D169,
D40, read there read-only. **Scope: the six staged files of one commit.** I
repaired nothing (D166). Every fault I drove went into a throwaway copy under my
own scratch directory; this folder was never written to. Read at `442599c`, 93
tracked files, restored byte for byte and checked by sha256 before and after.

---

### The counts, run, each read off its own last line

| suite | count | red |
|---|---|---|
| extension, 5 files | **412** (was 400) | 0 |
| `autosync/*_checks.py`, 30 files | **2,519** | 0 |
| `tools/*_checks.py`, 3 files | **224** | 0 |
| **everything** | **3,155** over 38 files | **0 red, 0 that failed to start** |

autosync and tools match A20's recorded numbers exactly, so nothing outside the
extension moved. All six touched files pure LF, 0 CRLF -- measured in Python on
the bytes, not with grep (A19R's broken instrument). 238 added / 7 removed, which
is the size of the change and not a line-ending rewrite (D174 clean).

---

### TWELVE FAULTS DRIVEN. TEN CAUGHT BY THE CHECK NAMED FOR THEM, ONE ONLY BY THE RUN ABORTING, **TWO NOT CAUGHT AT ALL**

**The author's two claimed red checks are true, and I drove them rather than
taking them on trust:**

| fault put in | run | result |
|---|---|---|
| `heard` made `async` with one `await` in front of the cancel | `doors.test.js` | **1 FAILED of 39** -- the single red is *the download is cancelled inside the event, before anything is waited for* |
| `watching.expectAFile();` deleted from `background.js` | `background.test.js` | **1 FAILED of 88** -- the single red is *and it armed the download cancel as well* |

Each reddened exactly ONE check and it was the check NAMED for it (D175). Cutting
the five new `doors.test.js` blocks out was caught by *checks went missing -- 30
ran, 39 expected* (D190: reached, not merely green).

---

### FINDING A -- **THE MANIFEST CHANGE WAS HELD BY NOTHING, AND IT IS THE HALF THAT DECIDES WHETHER ANYTHING LANDS AT ALL**

`host_permissions` was read by **nothing** in this repository. `background.test.js`
opened the manifest and asked about `permissions` and `content_scripts`, and never
about `host_permissions`.

| what I did | what the checks said |
|---|---|
| deleted the new `storage.googleapis.com` line | **all 412 green** |
| emptied `host_permissions` entirely | **all 412 green** |

The symptom of either is the exact one A23 spent a whole session diagnosing: the
re-fetch refused, the walk reporting *"the platform would not hand it over"*, and
a night that quietly lands nothing. **A commit whose stated purpose is "the
re-fetch is refused without it" ought to leave behind a question that goes red
when it is taken away.** It did not.

**FIXED BEFORE THE COMMIT LANDED.** Two checks were added to
`background.test.js` and both were driven to red by removing the host: *the host
the file really lives on is allowed*, and *and it still does not ask for every
address there is* -- the second so that "allow everything" cannot be the answer.
Extension total 412 -> **414**.

**AND THAT NUMBER WAS WRONG WHEN THIS ENTRY WAS COMMITTED. It said 432.** 412
plus two is 414; 432 is an arithmetic slip A25 made and then repeated into
`active.md` and `KARTAAN-STATUS.md`, so the same wrong figure stood in three
places at once. **A20R caught it while reviewing a DIFFERENT commit** -- it
noticed the record and the tree disagreed and said so, though nothing had asked
it to. Measured at HEAD: background 90 + doors 39 + driver 131 + recipes 26 +
walk 128 = **414**. Corrected here rather than quietly overwritten (D169), and
the lesson is the plain one: **a check count is measured, never added up in your
head** -- which is the whole reason the register pins these numbers at all.

### FINDING B -- THREE COMMENTS STATED THINGS THAT ARE NOT TRUE OF THE CODE BESIDE THEM

All three were corrected before the commit, and the corrections say what was
wrong rather than quietly replacing it (D169).

| the comment said | what is actually so |
|---|---|
| *"The longest recipe here -- fk_orders -- adds up to about ten and a half minutes"* | `walk.js:209` runs a recipe's `toAsk` **or** its `toTake`, never both. `fk_orders`' longest single walk is **5.5 min**; the longest that can exist is **`me_orders` at 10.58 min**. The conclusion survived by luck -- 15 still clears it -- but the arithmetic beside the number was wrong, and the next person to change a patience would have checked it against the wrong recipe |
| `arm-the-catcher` is *"the only point that is ahead of the click"* | `go` and `say` are ahead of it too. It is the **earliest**, and the reason to prefer it is that the others arrive again and again, so an arm re-set every few seconds would never run out |
| *"The reference bounds its own fallback the same way, for the same reason"* | The reference bounds its at **five** minutes and arms **seconds before the click**; this arms at the start of the walk and holds fifteen. Same intent, different shape |

### FINDING C -- NOTHING DISARMS THE CANCEL WHEN A WALK ENDS

The five two-phase Flipkart recipes produce no file at all in their ask walk, by
design. Each one arms and then finishes, leaving the cancel live over the
seller's own downloads for the rest of the fifteen minutes. It is bounded and it
is one file, so it cannot run away. **Left, and recorded, rather than fixed.**

### What I looked for and did NOT find

- **Working code touched that did not need to be:** none. `fake-chrome.js` is 29
  additions and 0 removals; all seven deleted lines in the whole diff are lines
  replaced in place, three of them stand-ins that had to gain `expectAFile` so
  they do not behave better than the real watcher.
- **A stand-in gentler than Chrome in a way that hides a defect:** the callback
  shape is load-bearing -- making `cancel` promise-shaped turns the timing check
  red, so that check genuinely depends on it. Two ways it is still gentler and
  neither is read by anything in `extension/`: its callback fires synchronously
  where Chrome's does not, and it can never fail or set `lastError`.
- **Secrets:** clean. Every address in the new checks is a reserved `.invalid`
  domain; no token, key, panel slug or query string anywhere in the diff; and the
  new code logs **nothing at all** -- the reference logs 120 characters of every
  download URL and this does not.

### What this review could not settle

- **Whether the cancel wins on a profile where "Ask where to save each file" is
  ON.** His is OFF, so the live run proved the download was cancelled, erased,
  and never reached disk -- but not that no dialog would have appeared. One run
  on a profile with that setting on would settle it.
- **No check covers an armed download whose address is a `blob:`.** The blob
  branch is checked unarmed and the arming does not touch it, so this is a gap in
  coverage rather than a defect in behaviour.

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

---

## 2026-09-04 (seventh) — A10R on the two uncommitted units, A8 (the reading) and A9 (the sales ledger). **A9 HOLDS. A8 DOES NOT. NOTHING COMMITTED.**

**Reviewed against** `D:\Kartaan-ERP\DECISION_LOG.md` — D137, D150, D151, D152,
D157, D161, D166, D174, D175, D176, D183, D184, read there read-only. **Scope:
`D:\Kartaan-AutoSync` only.** **I repaired nothing** (D166). Every fault I put
back went into a throwaway copy in scratch; this folder was never written to
until this entry.

**THE TREE DID NOT MOVE.** The ten files under review fingerprinted by content on
entry and again before this was written — all ten byte-identical, `git status`
unchanged, `HEAD` at `e7d8b89` throughout (D181).

**All 29 checks files in `autosync/` are green — 70 + 155 + 99 + 87 in the four
under review — and every run was read from its last line first (D175).** Green is
not why this stops. Finding A below is a check that is green and whose name is not
true of the run it describes.

---

### THE SPLIT IS REAL, AND I VERIFIED IT RATHER THAN TAKING IT

A8 owns `reading.py`, `reading_checks.py`, `nightly.py`, `nightly_checks.py`,
`tools/work.json`. A9 owns `ledger_sheet.py`, `ledger_sheet_checks.py`,
`between_runs.py`, `between_runs_checks.py`. **`between_runs.py` is not shared —
all six changed places are A9's.** `start.py` is shared, and it does **not**
separate by hunk: A8's `what_is_in_the_folder=` and `bring_the_file_back=` and
A9's `record_the_sales=` land together in `@@ -133,12 +155,36 @@`. They separate
by line, so two commits are constructible by hand.

**AND THE ORDER IS FORCED: A9 CANNOT GO FIRST.** A9's `start.py` passes
`record_the_sales=` into `nightly.one_tick`, and that parameter is A8's. A commit
of A9 alone raises `TypeError` on the first run. **So a defect in A8 blocks both.**

---

### FINDING A — BLOCKING. THE ORDER DRIVE LISTS FILES IN DECIDES THE SELLER'S FIGURES, AND THE CHECK THAT SAYS OTHERWISE PROVES SOMETHING ELSE

`ledger.py:294` says, in its own words: *"an order of fetching must never decide
what a figure is."* `ledger.plan` enforces that by sorting its readings oldest
first, so the newest data date wins (D150 rule 2).

**IT NEVER HAS MORE THAN ONE READING TO SORT.** `reading.py` calls
`record_the_sales([reading])` — one file at a time, which is correct and is what
makes the marking safe. `ledger_sheet.recording_into` then does
`rows = door.everything()` and `ledger.plan(rows, readings)` **once per file**.
So the sort is handed a list of one, every time, and sorts nothing.

Driven, on his own case — the 5th says the quantity is 9, the older 4th says 1:

| how Drive listed them | per-file plan (**production**) | one pooled plan (**the check**) |
|---|---|---|
| 4th then 5th | 9 | 9 |
| **5th then 4th** | **1** | 9 |

And across two nights, which is his case exactly — the 5th read one night, the
late 4th the next, against the sheet the first night wrote: **the sheet ends at 1.
The 9 is gone.**

**THE CHECK NAMED FOR THIS IS GREEN AND TESTS A CONFIGURATION THAT NEVER OCCURS.**
`reading_checks.py:526` and `nightly_checks.py:954`, both called *"THE FOURTH'S
OLDER FIGURE DOES NOT OVERWRITE THE FIFTH'S"*, pool **both nights'** readings into
a **single** `ledger.plan` call against an **empty** sheet:

```
everything = list(first_four.recorded) + list(late.recorded)
plan = answered(lambda: ledger.plan([list(sales.COLUMNS)], everything))
```

That proves `plan`'s internal sort, which is real and was already committed. It
proves nothing about the chain the two units build. **This is D175's shape one
level up: not a fault caught by the wrong question, but a question whose green
answer does not mean what its name says — and it says it about money.**

**IT IS NEWLY REACHABLE BECAUSE OF THIS WORK.** Before it, nothing called the
reader and nothing wrote to the ledger, so the overwrite could not happen. The
half that reads the late file (A8) and the half that writes it (A9) are each
sound alone; the defect is in the join, which is why neither unit's own checks
see it.

**AND THE FIX IS ALREADY WRITTEN DOWN AND IS NOT BUILT.** D157's second half
requires *"four columns, each holding the data date of the newest file of that
kind that has touched the row"*, and says in terms that the rule *"cannot be
enforced across runs today because nothing records which file wrote a value."*
`ledger.COLUMNS` is 45 wide and **none of them is such a marker.** With markers on
the row, a per-file plan could refuse an older file's figure on its own.

**Not repaired, not designed here** (D166). Whether the answer is the markers, or
pooling a night's readings into one plan, is the author's and it has a cost either
way.

---

### FINDING B — BLOCKING FOR THE COMMIT, ALREADY KNOWN: `nightly_checks.py` LINE ENDINGS

Measured against `HEAD`, not by looking:

| file | worktree | in HEAD |
|---|---|---|
| **`nightly_checks.py`** | **0 CRLF / 1007 LF** | **847 CRLF** |
| `ledger_sheet.py` (new, A9) | **0 CRLF / 619 LF** | — |
| `ledger_sheet_checks.py` (new, A9) | **0 CRLF / 581 LF** | — |
| `reading.py`, `reading_checks.py` (new, A8) | CRLF | — |
| `nightly.py`, `between_runs*.py`, `start.py` | CRLF | CRLF |

`nightly_checks.py` is flipped CRLF → LF, so 161 real lines read as 1,854. **I read
it with `git diff -w` rather than skimming it** (D174): the whole change is **161
insertions and exactly ONE deletion — `EXPECTED = 137`**, replaced by
`EXPECTED = 155`. **No check was removed and nothing is hiding in the noise.** It
must still be put back to CRLF before that unit is committed.

**AND ONE NOBODY HAS RECORDED: A9's two new files are LF while every other file in
this repository is CRLF.** A new file has no diff for a removal to hide in, so it
is smaller than the above — but this repository has **no `.gitattributes`**
(`git check-attr text` → `unspecified`), so nothing normalises it and the next
edit of either file by a session on a different setting produces exactly the diff
D174 exists to prevent.

---

### FINDING C — NOT BLOCKING. THE SELLER IS TOLD THREE THINGS AND FOUR ARE TRUE

A9's D184 measurement is correct and I checked it against the 45 columns rather
than reading it: **all 45 measured, none missed, none spare — 28 come back from
the platform files, 14 from Kartaan's own records, 3 cannot come back** (`notes`,
`adSpend`, `rev`). Removing one column's entry makes
`what_a_rebuild_cannot_put_back` refuse in words. That guard holds.

**But `netPnl` and `returnPnl` are measured as coming back with TODAY'S answer
rather than the day's (D151 snapshots), and the seller is never told.**
`what_to_tell_them_about_a_deleted_ledger` emits only `CANNOT_COME_BACK`, so step
4 names three columns. A seller reading *"what writing it again cannot put back:
notes, adSpend, rev"* would reasonably believe their profit column comes back as
it was. It will not. **D184's step 5 warns against a ledger that reappears with a
different history in it; two columns of that difference are measured and unsaid.**

---

### WHAT I DROVE MYSELF, AND WHAT HELD

| | |
|---|---|
| **A8's central rule** — a file is written down as read **only** when its sales landed | **HOLDS**, four ways: landing raises → not marked; the next night re-reads it and the sales land; one file of three failing loses exactly that one; baseline marks it |
| **A9's 26-vs-45** | **HOLDS.** `columnCount` is set **in** the creating call and is `len(sales.COLUMNS)` — no number typed anywhere. A 26-wide sheet is refused **loudly** at the first write, in Google's own words, and never written to |
| **A9's 14 faults** | **Re-drove 8 of my own, all caught by the check NAMED for it** (D175) — the un-widened grid, a binned ledger read as "no ledger", two ledgers of one name, a wrong header accepted, a gone ledger answered by making a new one, and three of A8's. One earlier attempt of mine reported "not caught" and **the injection was wrong, not the code** — twice: a field name I guessed, and a replacement that broke the file's syntax |
| **A9's SHAPE 2 → 3** | **HOLDS.** A shape-2 record is refused in words; a shape-3 record with no ledger reads as a first night; forgetting the address and moving it to a different sheet are both refused |
| **The open question — one Google application or two** | **THE READING IS RIGHT.** One `GOOGLE_CLIENT_ID` enters this repository, in `start.py:71`. Creating and writing both come from the same handed-in `transport`, and no function in the writing path takes a second identity — so the **nightly job is unaffected by the answer**. What breaks on "two" is the **page**, which cannot open the sheet at all. **And one thing the reports do not say: the record that holds the id is itself a Drive file this app created, so a second application cannot read the id either** |

---

### WHAT I DID NOT SATISFY MYSELF ABOUT

- **Nothing here has ever touched a real Google account.** No sheet has been
  created, no seller's Drive listed, no sale written. Every finding above is from
  driving the code with the transport handed in, which is what makes that
  possible — and it is still a review of code that has never run for real.
- **`tools/work.json` will be false the moment both commits land.** Its entry says
  *"`record_the_sales` is deliberately NOT handed in by `start.py`"* — A9 now hands
  it in — and it files the check in Finding A as the proof of his case. A8's commit
  carries that text and A9's commit does not correct it.
- **`reviews: []`** in the new register entry. I have not written into it; that is
  the author's file to correct (D166).

---

### THE ANSWER

**A9 holds on everything I was asked to test and everything I drove.** It is
blocked only because it cannot be committed before A8, and A8 has Finding A in it.

**NOTHING COMMITTED. NOTHING PUSHED. NOTHING REPAIRED.** Findings A and B go back
to their author; C is a sentence in the seller's own words and is theirs too.


## 2026-09-04 (eighth) — A11, the AUTHOR of the reading, answering A10R's Finding A. **THE CHECK THAT DENIED IT NOW MEANS ITS NAME. HALF THE FAULT IS FIXED; THE OTHER HALF CANNOT BE FIXED HERE AND IS LEFT OUT LOUD (D180).**

**This is not a review.** It is the author's repair of the one blocking finding
A10R left, written here because that is where the finding is. A fresh reviewer
still has to read it, and nothing below is committed.

---

### 1. THE CHECK WAS LYING, AND IT WAS PUT RIGHT BEFORE ANYTHING WAS FIXED

`THE FOURTH'S OLDER FIGURE DOES NOT OVERWRITE THE FIFTH'S` existed twice
(`reading_checks.py`, `nightly_checks.py`) and both copies **pooled both nights'
readings into ONE `ledger.plan` call against an EMPTY sheet.** That proves
`plan`'s own sort — already committed, already true — and nothing about the chain
these files build, because **the job never hands `plan` more than one reading.**

Both were rewritten to run the way the job runs: the reading hands files over one
at a time, the writing half reads the sheet back and plans again for each one,
and **the sheet actually keeps what it was written.** A stand-in that answers
every write with `{}` leaves every plan looking perfectly right and the sheet
empty, which is how a chain planning against a stale reading passes.

**Then they were run against the code as it stood, and they went red** — both
copies, before a line of the fix existed (D175).

| driven, on his own D157 case | the sheet ends up saying |
|---|---|
| one run, folder listed fourth-then-fifth | **9** — right, by luck |
| one run, folder listed fifth-then-fourth | **1** — the correction destroyed |
| the fifth one night, the fourth the next | **1** — his exact case |

### 2. WHAT IS FIXED: WITHIN ONE RUN, THE ORDER DRIVE ANSWERED IN DECIDES NOTHING

`reading.read_what_is_new` now gathers tonight's new files from **all three
folders together** and hands them over **oldest first, by the day each file is
about**, before the handover rather than during it (`reading._oldest_first`).
The one-file-at-a-time handover is untouched — it is what makes the marking safe.

All three rows above now answer **9, 9, 1**: the two one-run cases agree, and the
across-nights case is the half that cannot be fixed here.

**Proved by breaking it on purpose, six ways, in a throwaway copy — never in the
tree (D176, D178).**

| the fault put back | what happened |
|---|---|
| no sort at all | **RED**, both named checks, both files |
| sorted newest-first | **RED**, both named checks, both files |
| sorted on Drive's id | **RED**, `AND THE ID DRIVE GAVE THE FILE DECIDES NOTHING EITHER` |
| the sort is there and the loop walks the folders anyway | **RED**, both named checks, both files |
| sorted on the file's NAME | nothing went red — **and it is not a fault** |
| each folder sorted on its own | nothing went red — **and it is not a fault** |

**The third row found a hole in the CHECKS, not in the code**, and it is the one
worth carrying: the fixtures' ids read `d-1` … `d-5`, so they happened to sort in
the same order as the days and a sort keyed on Drive's id passed everything. **A
real Drive id has no order in it.** A drive with ids running backwards to their
days was added, and it catches it.

**The last two survived and were not forced into a red**, because neither changes
a figure this package can produce, and saying so is worth more than a fake:

- **sorting on the file's name** — this package names a landed file itself, from
  the data date (D110), so for every file that can reach here the two orders are
  the same string. A weaker key, not a wrong answer.
- **sorting each folder on its own** — a sale is named `platform::orderId::sku`
  and each orders report carries exactly one platform, so two folders' files can
  never write the same row. Sorting them as one list is one rule instead of
  three, and it is what will matter the day returns and payments files — same
  platform, different report — can be read.

### 3. WHAT REMAINS, AND IT IS NOT A DETAIL: THE ACROSS-NIGHTS CASE

**When the late fourth arrives on a LATER night, the fifth's 9 is already in the
sheet and the fourth is the only reading the run has to sort.** `ledger.plan`
tells newer from older by the data date a READING carries, and **no row in the
sheet carries a date at all** — 45 columns and not one says which day's file last
wrote each figure. So the fourth's 1 goes over the fifth's 9 and **nothing
anywhere can tell that it should not have.**

**D157's second half asked for four date-marker columns and they were never
built.** They are pinned to the ERP's own column list, so the ERP moves first or
this repository's check on the sheet's shape goes red. **Not built here.**

It is recorded on its own line in `tools/work.json` in D180's state — *left, with
a reason* — and it is checked: `ACROSS TWO NIGHTS THE OLDER FILE STILL WINS —
D180, AND IT CANNOT BE FIXED WITHOUT THE FOUR DATE COLUMNS D157 ASKED FOR`
**asserts today's wrong answer on purpose**, in both files, so it goes red the day
those columns land rather than waiting for somebody to remember.

**THE SHEET WRITING IS NOT SAFE TO LAND UNTIL THOSE FOUR COLUMNS EXIST.**

### 4. THE LINE ENDINGS, AND WHAT THE DIFF SAYS NOW

`nightly_checks.py` was 0 CRLF / 1007 LF against a HEAD of 847 CRLF, so ~160
lines of change read as 1,854. **Put back to CRLF before anything else was
touched** (D174). Its diff now reads **304 insertions / 1 deletion**, and
`git diff -w` says exactly the same — nothing is hiding in the noise. The one
deletion is the expected-count line.

### 5. THE CHECKS ARE NOT CHAINED TO WORK THAT CANNOT LAND

The rewritten checks first imported `ledger_sheet.recording_into` — the real
writing half — which would have chained this unit to the one that is **not safe
to land** (§3). They now build those same three lines over the **committed**
`ledger_door.LedgerDoor` and `ledger.plan`, and the unit was proved to stand
alone: HEAD plus these four files, **with neither of A9's new files present**,
runs **241 checks and all pass.**

### 6. NOT COMMITTED, AND THE GATE SAYS WHY IN TWO PLACES

```
BLOCKED: the work register does not match what is here:
    autosync/ledger_sheet.py exists and no piece of work owns it.
    autosync/ledger_sheet_checks.py exists and no piece of work owns it.
```

**The register sweeps what is on DISK, not what is staged**, so this blocks every
commit in this tree, mine included, until A9's piece has an entry. **That is A9's
own record to write, and A10R did not name it** — it is the one thing on A9's
repair list that was missed.

**And behind it, a second block that is by design:** the gate wants a
`review_pass.json` naming a reviewer who is not the author, there is none, and
**I am the author.** D162 says the reviewer must be a fresh session that did not
write the code. So this unit was never mine to commit.

### 7. WHAT THE REGISTER WAS SAYING THAT WAS NO LONGER TRUE

A10R's last section said `tools/work.json` would be false the moment both commits
land. Two things in the `reading-what-is-new` entry are corrected, in place:

- it filed the lying check as the proof of his case — **the claim is withdrawn in
  the entry itself**, and the ordering finding beneath it names what proves it now;
- it said `record_the_sales` is *"deliberately NOT handed in by `start.py`"*,
  which stopped being true in the same batch.

`reviews: []` is still empty. **That is the reviewer's line, not mine.**

## 2026-09-04 (ninth) — A14, answering the cold reader's two blocking findings. **THE TIE RULE FIRES. THE WRITING HALF REFUSES. BOTH PROVED BY BREAKING THEM. NOTHING COMMITTED — the gate refuses the one thing an author cannot sign.**

**A14 wrote the code below, so A14 is not its reader.** This entry is the author
answering, in the shape A11's is: what was measured, what was changed, what was
put back to watch it go red, and what is still open.

---

## 1. D150 RULE 3 COULD NOT FIRE, AND THREE PLACES SAID IT COULD

**The case is his own (D110): a day fetched again lands as a second file under
the same name.** Two files, one report, one data date, disagreeing. The rule is
*keep what is there and REPORT it, never a silent pick*.

**Measured first, through the real chain — `read_what_is_new` into
`recording_into` into `plan` into a `LedgerDoor` over a sheet that keeps its
rows:**

| listed | the seller's quantity ends | disagreements reported |
|---|---|---|
| the 9-file then the 1-file | **1** | **0** |
| the 1-file then the 9-file | **1** | **0** |

**Both orders answer the same thing and neither says a word.** The figure is not
decided by the files; it is decided by whichever Drive id sorts higher, because
that is what breaks the same-day tie in the handover. Silent, and in the money.

**THE CAUSE IS ONE WORD: WHOSE MEMORY.** `ledger.plan` decides the rule in
`decided_on` — which file last claimed which column of which sale. That was
state inside the call, and **the job calls `plan` once per file**, because a sale
lands one file at a time and that is what makes marking a file read safe. So it
began empty every time, `before` was always `None`, and the two halves of a tie
were never in one call to be compared. `recording_into`'s
`for one in what.disagreements: speak(...)` was dead code under a comment reading
*"REPORTED, NEVER SWALLOWED."*

**AND `a_reading`'s OWN NOTE NAMED THIS CASE AS THE REASON IT CARRIES DRIVE'S
ID** — which reads to the next person as though it were handled. Carrying the id
buys determinism, not rule 3. That sentence is corrected where it stands, and it
now says which half it is and where the other half lives.

**THE FIX DID NOT TOUCH THE HANDOVER.** One file at a time, still. What crosses
it is the memory: `ledger.WhatTheNightHasDecided`, made **once per night** by
`ledger_sheet.recording_into` and handed to every file. `plan` takes it as
`so_far` and writes into it; left out, it makes its own and behaves exactly as
before, which is right for a caller that really does hold every reading at once.

**Driven again, the same three ways:**

| listed | quantity ends | disagreements reported |
|---|---|---|
| the 9-file then the 1-file | **9** | **1** |
| the 1-file then the 9-file | **9** | **1** |

Nothing is overwritten, and the report says so out loud:

    SALES LEDGER DISAGREEMENT  meesho::SO-1::DJ 14: qty says '9' and me_orders
    of 2026-09-05 says '1'. Both are as current as each other, so nothing was
    changed. The two files are aaa (which is the one standing) and zzz.

**THE REPORT NAMES BOTH FILES, and that is not decoration.** The two sides of a
tie are the same report of the same day — that is what makes it a tie — so
"me_orders of 2026-09-05" says it twice and points at neither. `Disagreement`
carries `kept_from` and `also_from`, which are Drive's own ids, which is what a
person opens.

**And both files are still written down as read.** A reported disagreement is not
a file that failed: it was opened, understood, and its sales reached the sheet.
Left unmarked it would be read again every night for ever and report the same tie
every night.

---

## 2. THE BATCH LANDED WHAT ITS OWN RECORD SAID COULD NOT LAND

`tools/work.json` said, on its own line: **"UNTIL THEY EXIST, WRITING TO THE
SELLER'S SHEET IS NOT SAFE TO LAND."** `start.py` wired the writing half in
anyway. **The record was not softened and the work was not unwired. The code now
refuses.**

`ledger.what_the_sheet_cannot_yet_say` asks `sales.COLUMNS` for D157's four
date-marker columns — `ordersOn`, `paymentsOn`, `returnsOn`, `claimsOn`, each
holding the data date of the newest file of that kind that touched the row. While
any is missing, `ledger_sheet.the_writing_half` refuses **before it touches
Google at all** — so no sheet is made that would then be refused — and hands back
this, which `start.py` already prints line by line as an ALARM:

    NOTHING HAS BEEN WRITTEN TO THE SELLER'S SALES LEDGER TONIGHT, AND NO FILE
    HAS BEEN MARKED AS READ. This is Kartaan refusing, not Google.
    1. WHY. The sheet has no column saying which day's file last wrote each
       figure. Without that, a file that arrives late -- say the 4th, turning up
       after the 5th has already corrected a quantity -- puts its older figure
       back over the newer one, in the money, with nothing anywhere saying so.
    2. WHAT IS MISSING, by name: ordersOn, paymentsOn, returnsOn, claimsOn. ...
    3. NOTHING IS LOST WHILE THIS STANDS. The seller's platform reports still
       land in their own Drive every night, and every one of them is still
       waiting to be read. Not one file is written down as read, so not one is
       skipped later.
    4. IT ENDS BY ITSELF. The day those four columns are in the ledger's columns,
       this stops refusing and the night writes. Nobody has to remember to come
       back.

**THE FETCHING IS NOT REFUSED.** Files still land in the seller's own Drive. What
stops is reading and, above all, marking — which `read_what_is_new` already
answers safely (D157, D184).

**AND IT LIFTS ITSELF.** `sales.COLUMNS` is pinned to the ERP's committed column
list, so the day those four land the refusal goes away with nobody remembering to
delete anything. **The names are the ERP's to set; these are the names this looks
for.** If the ERP lands them under different names, this keeps refusing and says
exactly what it looked for — which is the loud answer, and the one to want.

**Both sides are driven**, not one taken on trust: the refusal today, and — with
the one line that refuses stood down and put back at the end — the writing half
finding, making and filling the ledger the day the columns exist. A refusal
nobody has watched lift is a refusal that could be permanent by accident.

---

## 3. THE SECOND ACCIDENTAL FIXTURE, AND A REASON THAT WAS FALSE

**Every ordering fixture used ONE folder, and every multi-folder fixture put every
file on ONE day.** Inside one folder every landed name carries one fixed prefix,
so sorting on the NAME and sorting on the DAY are the same string. A name sort
passed all 78.

**And the reason the check file recorded for that survivor was measurably false.**
It said *"for every file that can reach here the two orders are the same string."*
Landed names are `{platform}_{report}_{date}`:

    by DAY :  meesho 09-01, flipkart 09-03, amazon 09-05, meesho 09-06
    by NAME:  amazon 09-05, flipkart 09-03, meesho 09-01, meesho 09-06

**The fixture is fixed:** four files, four days, three folders, whose day order
differs from the name order, from the folder-then-day order **and** from Drive's
id order. **And it checks the HANDOVER ORDER directly**, because that is what the
rule is about — no figure this package can produce today feels a cross-platform
ordering, since a sale is `platform::orderId::sku` and each orders report carries
exactly one platform.

**The sentence is fixed too**, and it now says what was measured, which reason
actually protects both injections, and **the date that protection ends**: the day
a second report of ONE platform can be read — returns and payments, same
platform, different report, different folder. Then
`meesho_me_orders_2026-09-05` sorts before `meesho_me_returns_2026-09-04` by name
and after it by day, both write the same row, and the name sort is simply wrong.

---

## 4. AND THE CHECK FILES HELD A COPY THAT HAD STOPPED BEING A COPY

`reading_checks.py` and `nightly_checks.py` each wrote out three lines that
*looked* like `ledger_sheet.recording_into` rather than importing it, on the
reasoning that the writing half could not be committed. **That reasoning is gone —
it refuses instead of not landing — and the copy had already drifted:** the real
one makes one night's memory and hands it to every file; the three lines made a
fresh empty one per file. **A check driving a copy of the thing it is named for is
the whole of how this fault stayed invisible.** Both now import the real thing,
and a second night gets a fresh recorder against the same sheet, because a second
run really does remember nothing.

---

## PROVED BY BREAKING IT — TEN FAULTS, ALL TEN RED, NONE SURVIVED

Put back one at a time in a **throwaway copy of `autosync/`** in the scratchpad.
The tree was never edited.

| put back | what went red |
|---|---|
| `plan` makes its own memory on every call (the fault as it stood) | **15** across all four files, led by *TWO FILES OF ONE REPORT AND ONE DAY: WHAT THE FIRST ONE WROTE IS KEPT* |
| the writing half makes the memory per FILE instead of per night | **13** -- the same, less the two that call `plan` directly |
| the writing half never asks whether it may write | **9** -- every refusal check |
| the four columns reported as already there | **12**, including *the refusal is back where it was, and still refuses* |
| files handed over sorted on the file's NAME | **2** -- *EVERY FOLDER'S FILES ARE HANDED OVER AS ONE LIST, OLDEST DAY FIRST*, and the same-day tie no longer answering the same either way |
| each folder sorted on its own | **1** -- that same one |
| sorted on Drive's own id | **4** -- that one, the two named for the id, and the figure inside one platform |
| no sort at all | **9**, across both files |
| a disagreement stops naming which two files disagreed | **4**, the ones named for it |
| a disagreement picked silently instead of reported | **10**, across all four files |

**The first two are the fault the reader found.** The fifth and sixth are the two
that the day before's exercise had recorded as **not-faults** — they survived
because the one-folder fixture could not feel them. They do not survive now.

**AND TWO RUNS FOUND A HOLE IN THE CHECKS RATHER THAN IN THE CODE.** Two checks
reached `disagreements[0]` straight, so a fault that stops the tie firing made
them **throw rather than go red** — and a check file that dies half way through
has no count and says nothing about anything below it. One was mine, one was
already committed. Both are guarded now, and the injection harness was changed to
show a crash instead of hiding it behind the FAILs above it.

---

## EVERY COUNT BELOW WAS RUN, AND READ OFF THE RUN'S OWN LAST LINE

Never off a file's `EXPECTED` constant — four wrong counts on this project this
week were read that way.

| | |
|---|---|
| `autosync` | **29 check files, 2,477 checks, all green** (was 2,427) |
| `ledger_checks.py` | 62 to **74** |
| `ledger_sheet_checks.py` | 87 to **106** |
| `reading_checks.py` | 78 to **92** |
| `nightly_checks.py` | 163 to **168** |
| `tools/gate_checks.py` | **113** green |
| `tools/export_recipes_checks.py` | **61** green |
| `extension` | 5 files, **400** checks green |

**D174 clean.** `git diff -w --numstat` equals the plain one on every file
touched. Line endings are unchanged per file: `reading.py`, `reading_checks.py`,
`nightly_checks.py` and `start.py` are pure CRLF as they were; `ledger.py`,
`ledger_sheet.py` and their checks are pure LF as they were.

---

## THE REGISTER, AND THE THREE STALE THINGS THE READER NAMED

- **`landing` added to `reading-what-is-new`'s `rests_on`.** It is imported and it
  was missing, against the register's own stated rule — and it is the most
  load-bearing of the lot: `landing.data_date_in` **is** the ordering key.
- **The third stale sentence in the register's note is corrected where it
  stands.** It said nothing yet remembers which files have been read across runs
  and that adding a field would bump `SHAPE`. Both halves are false: the field is
  `files_read` and `SHAPE` went to 3 on 2026-09-02 — and this is the piece that
  actually fills it.
- **The stale count is corrected, by running.** It claimed *"27 more in
  `nightly_checks.py`"*; `EXPECTED` had moved 137 to 163, which is 26, and both
  numbers were stale by the time a reader checked them.
- **`NOBODY HAS EVER WATCHED THESE CHECKS FAIL` is withdrawn** on
  `making-the-ledger`, because now somebody has.

---

## WHAT IS STILL OPEN, AND NOTHING HERE WAITS ON JAISWAL

1. **THE ERP BUILDS D157'S FOUR DATE-MARKER COLUMNS.** Until then the writing
   half refuses, loudly, by name — and the across-nights tripwire in both check
   files still asserts today's wrong answer on purpose, so it reddens the day
   they land. **The four columns are already his decision; they need the ERP to
   build them, not him to choose again.**
2. **A9's finding C**, unchanged and untouched: `netPnl` and `returnPnl` come back
   with today's answer rather than the day's, and the seller is never told.
3. **A READER WHO IS NOT THE AUTHOR.** `reviews: []` is still empty on both
   entries. That is the reviewer's line, not mine.

---

## NOT COMMITTED, AND THE GATE'S OWN WORDS FOR WHY

    BLOCKED: nothing records that anybody READ this commit:
      there is no review_pass.json.

A14 wrote all of it, and the gate refuses a record whose `written_by` and
`reviewer` are the same words — *"that is not a review"* (D162). The cold reader
read the state before this work, not this work. **Nothing was faked and
`--no-verify` was not used.**

---

## 2026-09-04 (tenth) — A15R on the whole uncommitted batch (A9's ledger, A11's reading, A14's two answers). **IT HOLDS: nothing found lets a bad commit through. Six findings, every one non-blocking, every one left to the author (D166, D180).**

**Reviewed against** `D:\Kartaan-ERP\DECISIONS.md` — D150, D157, D158, D161,
D166, D169, D174, D175, D176, D180, D181, read there read-only. **Scope:
`D:\Kartaan-AutoSync` only.** **I repaired nothing** (D166). Every fault I put
back went into a throwaway copy of `autosync/` in scratch; this folder was never
written to until this entry.

**THE TREE DID NOT MOVE.** 93 files fingerprinted by content on entry and again
before this was written — all 93 byte-identical, nothing gone, nothing new
(D181).

**THE BAR I WAS GIVEN:** only something that lets a bad commit through blocks.
Everything else is recorded and left (D180). Nothing below meets that bar.

**I WAS TOLD TWO FINDINGS WERE CLOSED. I DID NOT READ THE CLAIM — I DROVE BOTH,
with my own fixtures, through the running job rather than through the author's
harness.**

---

## 1. THE TIE RULE FIRES, AND IT IS REPORTED RATHER THAN RESOLVED

Driven through `reading.read_what_is_new` — the real reader, the real
`ledger_sheet.recording_into`, a real `LedgerDoor`, and a sheet that keeps what
it is written. Two files of ONE report (`me_orders`) and ONE data date
(`2026-09-05`), one saying the quantity is 1 and one saying 9. Built from the
real Meesho orders header.

| listed | quantity left in the sheet | disagreements said | files marked read |
|---|---|---|---|
| id-AAA then id-ZZZ | `1` | **1** | 2, one at a time |
| id-ZZZ then id-AAA | `1` | **1** | 2, one at a time |

The sentence the seller's log gets, verbatim:

> SALES LEDGER DISAGREEMENT  meesho::M-77::RING-77: qty says '1' and me_orders
> of 2026-09-05 says '9'. Both are as current as each other, so nothing was
> changed. The two files are id-AAA-fetched-first (which is the one standing)
> and id-ZZZ-fetched-again.

**Kept, said out loud, both files named by Drive's own id, and the same answer
whichever way Drive lists them.** The one-file-at-a-time handover is untouched —
both files are still marked read separately, which is what makes the marking
safe. D150 rule 3, met.

**AND I WENT PAST WHAT THE CHECKS COVER, because two files is the easy case:**

| what I drove | what happened |
|---|---|
| THREE files of one report and one date (1, 9, 5) | `1` kept, **2 disagreements reported**, all three still marked read |
| a tie, then a genuinely NEWER file (the 6th, saying 7) | **`7` won outright** and the tie was **still** reported — rule 2 and rule 3 at once |
| the same three listed backwards | identical: `7`, one disagreement |

A newer file still wins, and a tie is still not a quarrel that swallows the
correction. Neither of those two rows has a check named for it.

---

## 2. THE REFUSAL FIRES BEFORE GOOGLE, AND IT TAKES ITSELF AWAY

`ledger_sheet.the_writing_half` was handed a transport that **records and then
raises on any attribute touched at all**, so anything reaching Google would say
so by name.

| asked | measured |
|---|---|
| does it refuse? | yes — `record_the_sales` came back `None` |
| was Google touched? | **nothing. Not one attribute, no search, no sheet made** |
| was the seller's record written? | **no** |
| does it name all four columns? | `ordersOn`, `paymentsOn`, `returnsOn`, `claimsOn` — all four, by name, in step 2 of four numbered steps |
| does the fetching carry on? | **29 reports fetched** in a whole `one_tick`, under the refusal |
| is any file marked read? | **none.** `files_read` came back empty with a new file sitting in the folder, and the night said so: *"1 file(s) are sitting in the folder unread and will still be there when there is"* |

**AND IT LIFTS ITSELF — I did not take the claim on trust, because
monkey-patching `sales.COLUMNS` in a live process proves nothing here:
`ledger.py:90` binds `COLUMNS` at import.** So I did it the way the ERP will:
edited `COLUMNS` in a **throwaway copy of `sales.py`** and ran a **fresh
process**.

| | `what_the_sheet_cannot_yet_say()` | writing |
|---|---|---|
| the tree as it stands | all four missing | **refused** |
| the copy, with the ERP's four columns landed | nothing missing | **allowed** |

Nobody has to remember to come back and delete anything.

**AND THE DAY IT LANDS, THE REPOSITORY SHOUTS.** I ran all 29 check files in
that same copy: **47 checks go red**, including `sales_checks.py` — *"and the
whole column list matches, end to end"* — and the across-nights tripwire in both
`reading_checks.py` and `nightly_checks.py`, which asserts today's wrong answer
on purpose. The tripwire is real, and I watched it fire.

---

## 3. THE TEN FAULTS, PUT BACK AGAIN BY ME — ALL TEN RED, NO SURVIVORS, NO CRASHES

Not the author's harness. Mine: a throwaway copy of `autosync/`, one fault at a
time, all 29 check files run each time, **line endings honoured on every edit
(D174)** and an injection that does not match exactly refuses rather than
quietly doing nothing.

**The baseline was measured first: 0 red, 0 crashes.** An earlier run of my own
harness showed four check files crashing — that was my harness, not the code,
and finding 1 below is what it turned up.

| put back | red | led by |
|---|---|---|
| `plan` makes its own memory every call | **19** | *RULE 3 FIRES ONE FILE AT A TIME: the tie is REPORTED, not resolved* |
| the writing half makes the memory per FILE | **13** | the same, less the two that call `plan` directly |
| the writing half never asks whether it may write | **9** | *WHILE THE FOUR DATE COLUMNS DO NOT EXIST THERE IS NOWHERE TO PUT A SALE* |
| the four columns reported as already there | **12** | *AND GOOGLE IS NOT TOUCHED AT ALL — no search, no sheet made* |
| **files handed over sorted on the file's NAME** | **2** | *EVERY FOLDER'S FILES ARE HANDED OVER AS ONE LIST, OLDEST DAY FIRST* |
| **each folder sorted on its own** | **1** | that same one |
| sorted on Drive's own id | **4** | *AND THE ID DRIVE GAVE THE FILE DECIDES NOTHING EITHER* |
| no sort at all | **9** | *THE FOURTH'S OLDER FIGURE DOES NOT OVERWRITE THE FIFTH'S* |
| a disagreement stops naming which two files | **5** | *the report names BOTH files, not one report twice* |
| a disagreement picked silently | **17** | *AND THE DISAGREEMENT IS REPORTED, not resolved* |

**Every one was caught by a check NAMED for it (D175), not by something else
going red on the way past.**

**THE TWO IN BOLD ARE THE ONES A READER RECORDED AS NOT-FAULTS.** That judgement
was wrong and I confirmed it is wrong: both go red now, both under the check
named for them. The one-folder fixture is what had been hiding them.

**AND I SWEPT WIDER THAN THE TEN.** Every guard in `ledger.py`,
`ledger_sheet.py`, `reading.py` and `nightly.py` neutered one at a time, all 29
check files run each time:

| file | nothing caught it |
|---|---|
| `reading.py` | **0** |
| `ledger.py` | 2, both measured inert |
| `ledger_sheet.py` | 1, measured inert |
| `nightly.py` | **1 — finding 5 below, and it is not inert** |

---

## 4. THE THIRD HAND-WRITTEN COPY — AND IT IS IN THE REGISTER THE GATE TRUSTS

I was asked to go looking for one. It is `tools/work.json`, `the-sales-ledger`,
the fourth finding, still open:

> *"RULE 2 CANNOT BE ENFORCED ACROSS RUNS with the columns that exist. **The
> ledger's 28 columns** hold no record of WHICH FILE last wrote each value...
> Fixing it needs a column that is not in D152's list."*

**The ledger has 45 columns.** Measured: `len(sales.COLUMNS)` is 45. Five other
places in this repository say 45 — `ledger.py:68`, `reading.py:456`,
`reading_checks.py:829`, `nightly_checks.py:1127`, and `work.json`'s own
`reading-what-is-new` entry. **This one site was left, and it is the only "28
columns" anywhere in the file.**

**It is a hand-written copy of `reading-what-is-new`'s finding that stopped
being a copy, and it is stale in three ways, not one:**

1. the count — 28 against a measured 45;
2. *"a column that is not in D152's list"* — D157 named the four, and
   `ledger.WHICH_FILE_LAST_WROTE` holds their names in code today;
3. **it does not say that the writing half now REFUSES because of it** — which
   is the single most important fact about this finding, and the thing that
   makes this batch safe to land at all.

D169 exactly: *"a reference that survives a correction is worse than one that
breaks: it reads correctly and sends the reader somewhere false."* The register
entry beside it was corrected; this one was not swept. **A correction that names
no sweep is half a correction.**

**Not blocking:** the gate reads a finding's `proved_by`, never its prose, and
this finding is not marked fixed so it needs none. Nothing about it lets a
commit through. **Left for the author (D166) — I do not edit the record I am
reviewing.**

---

## 5. THE OTHER FIVE FINDINGS — none blocking, all left

### FINDING 1 — the two refusals whose whole point is the message crash before printing a word.

`autosync/the_other_half.py`, lines 144 and 177. Both raise a `SystemExit` whose
text interpolates `wanted`, and **`wanted` is defined nowhere in the file.**
Driven: `KARTAAN` pointed at a folder that does not exist gives

> NameError: name 'wanted' is not defined

Four check files reach it — `sales_checks.py`, `firestore_checks.py`,
`firestore_door_checks.py`, `ledger_door_checks.py`. The file's own docstring
says *"THE MESSAGE IS THE POINT. `FileNotFoundError: sync.js` tells somebody
nothing about a contract between two repositories."* A bare `NameError` tells
them less.

**Not blocking, and I checked rather than assumed:** the exit code is still 1
and `tools/gate.py`'s `run_one` refuses on a non-zero return code, so the gate
stops the commit either way. What is lost is the four paragraphs telling
somebody what to do about it.

### FINDING 2 — the same file still points at a folder name D148 withdrew, in four places.

`whereKartaanIs()` looks for **`Kartaan-ERP`**, and its own docstring records
that the `Kartaan` fallback *"came out on 2026-09-02, and a check goes red if it
comes back."* But the module docstring (three times) and `readFromKartaan`'s
refusal message still tell the reader to set `KARTAAN` to `D:\Kartaan`, and
still say a sibling folder called `Kartaan` is tried. `sales_checks.py:25-26`
already says `Kartaan-ERP`.

**The check meant to sweep this — `firestore_door_checks.py:293` — searches for
the code fallback as a PHRASE rather than asking what each site CLAIMS.** That
is D169's own named mistake, repeated inside the check written to stop it.
Compounded by finding 1: nobody has ever seen this message, so nobody has ever
noticed it is wrong.

### FINDING 3 — `start.py` gained a rule and nothing in this repository watches it fail.

The new block that turns a refused sales ledger into `ALARM` lines and a return
code of 1 is a rule about what a night does. **Nothing reads or drives
`start.py`** — there is no `start_checks.py`, and no check anywhere reads its
source. Measured by search. The file's own docstring says *"IT DECIDES NOTHING.
Every rule about what a run does... is in `nightly.py`, where it is proved by
being broken on purpose"*, and the same batch quotes D171 twice for exactly
this. **It is the identical blind spot that left the sales ledger finished at
both ends and called by nothing** — the fault this batch exists to close,
reappearing one file up. A check reading the source, as
`firestore_door_checks.py:291` already does for another file, would cover it.

### FINDING 4 — an observation, and it should be written down before it becomes one.

The eight GitHub secret names are written down **three times**: the `if` guard in
`.github/workflows/autosync.yml`, the `env:` block in the same file, and
`start.py`'s `_needed` calls. **I measured all three and they agree today** —
same eight, no drift. But nothing joins them, and **nothing anywhere reads
`.github/workflows/autosync.yml` at all**: `gate_checks.py`'s `WORKFLOW` is
`pm_check.yml`. `NOT_CODE` is the same shape — three copies of one fact — and it
has a check holding the three to each other. This has none. It is the workflow
that actually runs the seller's night.

### FINDING 5 — a guard nothing catches, and it is not inert.

`autosync/nightly.py:336`, the check on whether the run's own record may be
saved. Neutered, **not one check goes red.** It is the only thing between a
broken clock and the seller's Drive, and I measured what it holds back:
`between_runs.write()` will cheerfully write a record whose run finished two
hours before it started, and `read()` takes it straight back as fact.
`why_it_cannot_be_saved`'s own docstring says the cost — *"written down it would
make `clock.py` refuse every later run for a day on the strength of something
that never happened."*

**It is already committed and is not this batch's work** — `HEAD` at `2a6f658`
has the same three lines — which is why it is recorded rather than treated as a
reason to hold the batch. D176's deployment line covers it.

### The three inert survivors, named so nobody re-finds them

`ledger.py:339` (a wholly blank sheet row is passed over — neutered it becomes a
reported unreadable row, noise rather than money), `ledger.py:448` (`id` skipped
— the values cannot differ, so it is belt-and-braces), `ledger_sheet.py:332` (a
`None` reply — the check below refuses it anyway, with a worse sentence).

---

## 6. EVERY COUNT BELOW WAS RUN, AND READ OFF THE RUN'S OWN LAST LINE

| | |
|---|---|
| `autosync` | **29 check files, 2,477 checks, all green** — matches the author's claim exactly |
| `tools/gate_checks.py` | **113** |
| `tools/gate_run_checks.py` | **50** |
| `tools/export_recipes_checks.py` | **61** |
| `extension` | **400** — 85 + 30 + 131 + 26 + 128 |

**D174 checked on every touched file:** `git diff --numstat` equals
`git diff -w --numstat` on all nine, and `REVIEW.md` showed **573 insertions and
0 deletions** before this entry — a true append, not a rewritten file.

---

## 7. WHAT THIS REVIEW COULD NOT SETTLE

- **Nothing here has ever reached Google**, so the refusal, the tie report and
  the reading are all proved against handed-in transports and never against a
  real account. That is the standing fact of this whole repository, not a gap in
  this batch.
- **`SHAPE` went 2 to 3.** The read is strict equality both ways, so a new job
  meeting an old record refuses too — and it never repairs itself, because it
  refuses before it can write a shape-3 record over the shape-2 one. The comment
  says *"this costs a night"*; measured, it costs **every** night until somebody
  deletes the file by hand. It costs nothing today only because no
  `autosync-state.json` exists anywhere — **and I could not verify that myself**,
  since it needs the seller's Drive. Recorded, not blocking, and the refusing
  direction is the safe one.
- **The four column names are a guess at the ERP's.** If the ERP lands them
  under other names the refusal keeps firing and says what it looked for. That
  is the loud failure and it is deliberate.

---

## 8. AND SO IT IS COMMITTED

The one thing that stood between this folder and a landing was a reader who did
not write any of it. **That is what this entry is.** Committed as units, each
one standing on its own imports, each through the gate with its own review
record and no `--no-verify`, then pushed (D158). Nothing was faked.

---

## 2026-09-04 (eleventh) — A17R on `b4e402e`, the author's own six. **IT HOLDS: nothing found lets a bad commit through. Three findings and two notes, every one non-blocking, every one left to the author (D166, D180).**

**Reviewed against** `D:\Kartaan-ERP\DECISION_LOG.md` — D148, D152, D157, D166,
D169, D170, D174, D175, D176, D180, D190, read there read-only, and D158 for the
push. **Scope: `D:\Kartaan-AutoSync` only**, the one commit `b4e402e`, not pushed.
**I repaired nothing** (D166).

**THE TREE DID NOT MOVE** (D181). `HEAD` at `b4e402e` on entry and again before
this was written, 93 tracked files, working tree clean both times. Unlike the
sixth and tenth entries I drove the faults in this folder rather than in a copy —
every file was restored from a byte-for-byte backup and its md5 checked against
the original before the next fault went in, and `git status` was empty after each.

**THE BAR I WAS GIVEN:** only something that lets a bad commit through blocks.
Nothing below can. Three findings are prose or an unwatched error path; two are
smaller than that.

---

### 1. THE COUNTS, RUN, AND EACH READ FROM ITS OWN LAST LINE FIRST (D175)

| | |
|---|---|
| `autosync` | **30 check files, 2,509 checks, 0 red** |
| `tools/export_recipes_checks.py` | **61** |
| `tools/gate_checks.py` | **113** |
| `tools/gate_run_checks.py` | **50** — 224 in `tools` |
| `extension` | **400** |

All three of the commit's numbers match what I ran. No file ended on anything but
its own summary line.

---

### 2. THE RE-RULING ON FINDING 5 IS RIGHT, AND I DROVE BOTH SAVES MYSELF

A15R called it *a guard nobody watches*. The author called it *a guard that does
nothing*. **Confirmed at `988f34d` directly**, before any fault: the guard sits at
`nightly.py:335`, and **fifty-one lines below it** a second
`save_state(between_runs.write(state))` with no question asked of it at all.

Driven on the committed tree, one at a time:

| fault put back | the run's last line | what went red |
|---|---|---|
| first guard neutered — `wrong_with_it = None` | `2 FAILED (183 checks)` | A RUN THAT FINISHED BEFORE IT STARTED IS NEVER WRITTEN DOWN, and *and it is our own defect, said in words rather than swallowed* |
| second guard neutered — `cannot_be_saved = None` | `1 FAILED (183 checks)` | A RUN THAT FINISHED BEFORE IT STARTED IS NEVER WRITTEN DOWN |

**The second row is the author's claim reproduced exactly.** The first guard still
fires and its fault line is still appended — which is why the second check stays
green on that row — and the impossible record lands anyway. The refusal cost a
fault line and prevented nothing, and `read` would have taken the impossible
finish back as fact on the next run.

That is a reader's ruling overturned by driving it, for the second time in this
repository. **The author is not the third.**

---

### 3. THE EIGHT SECRET NAMES HOLD IN EVERY DIRECTION I COULD BREAK THEM

Three hand-written copies of one list, and D190 asks that each pair be held both
ways. Five faults, one at a time, each restored before the next:

| fault put back | the run's last line | what went red |
|---|---|---|
| `DRIVE_FOLDER_ID` dropped from the gate — handed over, never gated | `1 FAILED (183 checks)` | EVERY SECRET THE WORKFLOW REFUSES TO RUN WITHOUT IS HANDED TO THE RUN, AND EVERY ONE HANDED OVER IS ONE IT REFUSES TO RUN WITHOUT |
| `DRIVE_FOLDER_ID` dropped from `env` — gated, never handed over | `2 FAILED (183 checks)` | that one, and the `start.py` join |
| `start.py` stops asking for `FIREBASE_PROJECT_ID` | `1 FAILED (183 checks)` | AND EVERY ONE HANDED OVER IS ONE THE RUN ASKS FOR, AND EVERY ONE IT ASKS FOR IS HANDED OVER |
| `start.py` asks for `MEESHO_TOKEN`, which nothing hands it | `1 FAILED (183 checks)` | the same one, from the other side |
| one value in `env` wired to a different secret of the same family | `3 FAILED (183 checks)` | *every value handed to the run is set from the secret of the same name*, and both joins |

**This is the shape that let a credential pattern sit unwatched in
`Kartaan-Server` (D190), and here it is closed in both directions on both joins.**
The last row is the question nobody had asked before: a name that is present,
spelled right, and wired to the wrong secret.

---

### 4. FINDING — THE LEDGER'S WIDTH IS NOW HELD IN ONE PLACE OF SIX. NON-BLOCKING.

The commit says the register said 28, five other places said 45, *"nothing held
any of them to `len(sales.COLUMNS)`. Something does now."* **What is held is the
register. The other five are not.**

Driven: `The ledger's 45 columns` changed to `28` in `autosync/ledger.py`, then
the whole suite — **30 files, 2,509 checks, 0 red.** The same drift, in the same
shape, in a file nothing reads for it.

And those sites are not out of reach. Three of them state the width in a phrasing
the new pattern **already parses** — `ledger.py:68`, `reading.py:456`,
`reading_checks.py:829` — and the check simply is not pointed at them; the fourth,
`nightly_checks.py:1129`, is not.

**Why it is not blocking:** prose, not behaviour, and there is a real tripwire
underneath it. `sales_checks.py:295` pins `len(tool.COLUMNS) == 45` against the
ERP's committed `sheet-store.js`, so the day D157's four date markers land that
check goes red and somebody must touch the number. What nothing holds is whether
they sweep the other five while they are there — **which is D169 exactly, and D169
is the entry the new check's own comment cites.**

---

### 5. FINDING — THE STATED LIMIT ON THAT CHECK IS NARROWER THAN THE REAL HOLE. NON-BLOCKING.

The comment records the escape as *"a sentence that gives the ledger's width
without using the word `ledger` within the same clause"*. Driven against
`tools/work.json`, one wrong width at a time:

| the wrong width written as | word `ledger` in the clause | caught |
|---|---|---|
| `the ledger's 28 columns` | yes | **yes** |
| `the sales ledger is 28 columns wide` | yes | **yes** |
| `28 columns in the ledger` | **yes** | **no** |
| `the ledger, which the seller reads without opening Kartaan, has 28 columns` | **yes** | **no** |
| `the sheet is 28 columns wide` | no | no — the limit as recorded |

**Rows three and four use the word and still escape.** The pattern only reads
forwards from `ledger`, and only across forty characters. So the recorded limit
describes a smaller hole than the one that is really there.

D180 permits a finding being left undone; what it asks for is **a reason somebody
else can weigh**, and a limit stated narrower than it is cannot be weighed. That is
D180's own argument about a check that tells a future reader where to stop looking,
one level up.

**AND ON WHETHER THE NUMBER CAN BE HELD TO SOMETHING STRONGER, WHICH I WAS ASKED
TO JUDGE: YES, AND D180 IS NOT THE RIGHT ANSWER HERE.** The comment's reason —
*"the register has no field carrying the number"* — is a fact about the register's
shape today, not a limit on what can be done to it. `tools/work.json` is JSON and
the gate already reads it. A field on the ledger piece's `state` holding the width,
pinned to `len(sales.COLUMNS)`, would take the number **out of prose entirely** and
make it the kind of fact that cannot drift; the sentence sweep would then sit on
top of it as best-effort rather than as the only thing there is. **A number living
only in prose is how item one of this same commit came to be wrong**, and the fix
chosen leaves it living only in prose. Changing the register is the author's to do,
not mine (D166).

---

### 6. FINDING — TWO MORE REFUSALS IN THE SAME FILE HAVE NEVER BEEN RUN BY ANYTHING. NON-BLOCKING.

**It is in the file this commit just gave fifteen checks to.**
`the_other_half.py:108` (git could not be run at all) and `:116` (the file is not
committed at `HEAD` in the other repository). Neither has ever been executed.

I established that rather than assumed it: every line of `autosync/` and `tools/`
traced under all **33** checks files, and those two lines appear in nothing. Then I
drove both by hand — **both print in full, no crash** — so this is an absent alarm,
not a broken path.

**And `:116` is the most important of the file's four refusals.** The
folder-missing case is the obvious one, and it is the one the new checks cover. The
not-committed case is the one the file's whole design rests on — *"it reads what is
COMMITTED, never what is on disk"* — and the docstring records it really firing on
2026-09-02 against seventeen uncommitted ledger columns. **It is the refusal most
likely to meet a real person, and it is the one with nothing watching it.**

Not blocking, for the author's own stated reason about the other two: a refusal
that breaks still exits 1, so the gate still refuses and nothing bad is let
through. What is lost is the words.

---

### 7. TWO NOTES, SMALLER THAN FINDINGS

- **The server refusal prints an instruction nobody should type.** It says to set
  the folder with two backslashes after the drive letter, out of `SLASH + SLASH`
  in the concatenation, where the ERP refusal beside it prints one. Driven:
  Windows tolerates it, the path resolves and the file reads, so it costs nothing
  but the look of it. **The new check cannot see it** — `folders_named` replaces
  every backslash with a slash before comparing, so it reads the folder name and
  never the separator.
- **One blank line between `how_the_night_ends` and `_try`** in `nightly.py`,
  where the file uses two everywhere else.

---

### 8. WHAT I LOOKED FOR AND FOUND NOTHING WRONG WITH

- **The `wanted` class is gone repository-wide, not only in the two refusals.**
  Every `.py` file walked as a syntax tree for a name loaded and bound nowhere in
  its module: **0**. Both original refusals driven for real — the whole sentence,
  no `NameError`.
- **`start.py`'s rule moved without changing.** Same order, same exit codes, same
  lines printed. `how_the_night_ends` driven through all four of its cases.
- **D174 on all seven touched files.** No file was rewritten: the largest deletion
  in the commit is 18 lines, in `start.py`, where 18 lines really were removed.
  Each file is internally consistent in its line endings and none flipped.
- **The width is not a hand-typed number where it decides anything.**
  `sales.COLUMNS` is built from the ERP's committed `sheet-store.js` through
  `readFromKartaan`, which reads `git show HEAD:` and refuses rather than falling
  back to the disk.
- **Security.** Nothing this commit adds holds, sends or names a secret. The one
  place it comes near them, `nightly_checks.py` reads the workflow as text to
  compare eight **names**; no value is read, and that file has never held one.

---

### 9. WHAT THIS REVIEW COULD NOT SETTLE

- **Nothing here has ever reached Google or Amazon**, so every refusal and every
  save is proved against handed-in transports. `start.py` still has no checks file
  and has still never been executed. The commit does not claim otherwise, and the
  register says so.
- **The gate's own error paths.** The same trace found **twenty-five** `raise`
  lines in `tools/gate.py` and `tools/gate_run.py` that no check has ever
  executed. They are older than this unit and outside it, and I did not drive
  them. Recorded so the next reader does not have to re-find them.
- **Whether the ERP names the four date-marker columns as this repository guessed.**
  If it does not, the refusal keeps firing and says what it looked for, which is
  the loud direction.

---

### 10. AND SO IT IS COMMITTED

`b4e402e` had no reader who did not write it, and its own record said so rather
than pretending otherwise. **That is what this entry is.** It holds: three findings
and two notes, not one of them able to let a bad commit through, all five left for
the author (D166, D180). This entry goes through the gate with its own review
record and no `--no-verify`, and `b4e402e` goes up with it (D158).

---

## 2026-09-05 (twelfth) — A19R on `2c120d7`, the author's answer to A17R's findings A and B. **IT HOLDS: the number that was only prose is a field, the pin goes to the thing that knows, and the half that mattered is genuinely held. Two findings, both non-blocking, both left to the author (D166, D180).**

**Reviewed against** `D:\Kartaan-ERP\DECISION_LOG.md` — D152, D166, D169, D174,
D175, D176, D180, D190, D192, read there read-only, and D158 for the push.
**Scope: `D:\Kartaan-AutoSync` only**, the one commit `2c120d7`, not pushed.
**I repaired nothing** (D166), including the finding I could have closed by adding
one line to a list.

**THE TREE DID NOT MOVE** (D181). `HEAD` at `2c120d7` on entry and again before
this was written, 93 tracked files, `git status` empty both times. Every fault was
driven in this folder rather than in a copy, every file restored from its own
bytes and its md5 compared against the original before the next fault went in.

**THE BAR I WAS GIVEN:** only something that lets a bad commit through blocks.
Neither finding below can.

**THE HOUR, AND IT IS NOT A FORMALITY (D192).** I ran everything between **09:18
and 09:50 IST on 2026-09-05** — outside the 18:30 UTC to midnight IST window where
a check that builds its moment from the machine's calendar goes red against a
correct screen. **So this sweep is a verdict at that hour and not a verdict on the
code.** Nothing this commit adds reads a clock or a calendar — the seven new checks
read text, JSON and `len(sales.COLUMNS)` — so the window cannot reach *them*. It
can still reach the other 2,438 checks I ran green, and I did not run in it.

---

### 1. THE COUNTS, RUN, AND EACH READ FROM ITS OWN LAST LINE FIRST (D175)

| | |
|---|---|
| `autosync` | **30 check files, 2,516 checks, 0 red** |
| `tools/export_recipes_checks.py` | **61** |
| `tools/gate_checks.py` | **113** |
| `tools/gate_run_checks.py` | **50** — **224** in `tools` |
| `extension` | **400** — 85 + 30 + 131 + 26 + 128 across five files |

**33 checks files, 0 red, and not one of them ended on anything but its own
summary line** — I checked that before reading any number above it, and a file
whose last line was not `all N checks passed` would have counted nothing. All
three of the commit's numbers match what I ran, and the `2,509` it names as the
previous figure is the `71 -> 78` in `sales_checks.py` and nothing else.

---

### 2. THE PLACE THAT ESCAPED, AND THE OTHER FIVE — THIRTEEN FAULTS, THIRTEEN NAMED REDS

A wrong width in `autosync/ledger.py` used to leave all 2,509 checks green. I put
one there myself first, then went round the other five one at a time. **Each was
caught by the check NAMED for it (D175), never by whichever question happened to
answer wrong**, and every file was restored byte for byte with its md5 compared:

| the fault I put back | where | the check that went red |
|---|---|---|
| `45` -> `44` | `autosync/ledger.py` | `autosync/ledger.py SAYS HOW WIDE THE LEDGER IS...` |
| `45` -> `44` | `autosync/reading.py` | `autosync/reading.py SAYS HOW WIDE THE LEDGER IS...` |
| `45` -> `44` | `autosync/reading_checks.py` | `autosync/reading_checks.py SAYS HOW WIDE...` |
| `45` -> `44` | `autosync/nightly_checks.py` | `autosync/nightly_checks.py SAYS HOW WIDE...` |
| `45` -> `44` **in the field** | `tools/work.json` | `THE REGISTER CARRIES THE LEDGER'S WIDTH IN A FIELD OF ITS OWN...` |
| `45` -> `44` | `autosync/sales_checks.py` | `and it is 45 columns wide today, which is AS` |
| **the field DELETED** | `tools/work.json` | `THE REGISTER CARRIES THE LEDGER'S WIDTH IN A FIELD OF ITS OWN...` |
| **the accounting list renamed away** | `tools/work.json` | `AND EVERY OTHER COLUMN COUNT IN THE REGISTER IS ONE THE REGISTER ITSELF ACCOUNTS FOR...` |
| **the sentence DELETED** | `autosync/ledger.py` | `autosync/ledger.py SAYS HOW WIDE THE LEDGER IS...` |
| **the sentence DELETED** | `autosync/reading.py` | `autosync/reading.py SAYS HOW WIDE THE LEDGER IS...` |
| `44`, number BEFORE the word | `tools/work.json` prose | `THE REGISTER SAYS HOW WIDE THE LEDGER IS, AND EVERY PLACE IT SAYS SO...` |
| `44`, **no `ledger` in the sentence** | `tools/work.json` prose | `AND EVERY OTHER COLUMN COUNT IN THE REGISTER IS ONE THE REGISTER ITSELF ACCOUNTS FOR...` |
| `44`, **no `ledger` in the sentence** | `autosync/ledger.py` prose | `autosync/ledger.py SAYS HOW WIDE THE LEDGER IS...` |

**BOTH DIRECTIONS, AND THAT IS THE HALF THAT USUALLY GETS MISSED.** Deleting the
sentence is as red as making it wrong, in every one of the six — so a place that
simply stops saying the width cannot go quiet, which is what would otherwise leave
the number unheld the next time somebody wrote it back.

**AND THE HALF THAT MATTERED IS GENUINELY HELD.** A17R's finding was that a width
worded without the word `ledger` beside it slips past. Rows twelve and thirteen are
exactly that fault, in the register and in `ledger.py`, and both go red — the
register's through the accounting list, `ledger.py`'s because that file is scanned
whole and states no other column count. **The claim the D180 deferral said could
not be met is met.**

**TWO OF MY OWN INJECTIONS WERE BAD FAULTS AND I RE-DROVE THEM.** My first attempt
at rows twelve and thirteen put a bare string where JSON wanted a key, so `and it
reads as JSON, which is what makes a field possible at all` went red as well — a
true answer to a question I had not meant to ask. Re-driven inside the register's
own prose array with the JSON left valid, the named check goes red on its own. **A
fault that breaks the file it is testing proves the parser, not the check**, and I
was not going to file the first run as evidence.

---

### 3. THE PIN GOES TO THE THING THAT KNOWS, AND IT IS NOT A SIXTH COPY

I was asked to satisfy myself that `len(sales.COLUMNS)` is the list that knows,
rather than a number retyped or a sentence parsed somewhere else. **It is, and the
hop between it and the ERP is itself held by a check.**

`sales_checks.py:174` compares `tool.COLUMNS` name by name and in order against
`THEIR_PLAIN` and `THEIR_CHARGES`, which `the_other_half.readFromKartaan` reads out
of the ERP's **committed** `src/shared/data/sheet-store.js`,
`definitions/charges.js` and `definitions/orders.js` — through `git show HEAD:`,
refusing rather than falling back to whatever is loose on disk. So the width is
pinned to a list that is pinned to the ERP. **A column added, renamed, removed or
reordered on either side turns this red the same day**, and the number cannot drift
from the thing it counts without something saying so.

---

### 4. FINDING — THE REGISTER'S `no ledger` HALF HAS A FIVE-NUMBER BLIND SPOT. NON-BLOCKING.

The new check exempts every count the register accounts for: `22`, `26`, `39`,
`43`, `74`. **A wrong width written into the register's prose without the word
`ledger`, whose number happens to be one of those five, is not caught.** Driven:

| the wrong width written into `tools/work.json` prose | caught |
|---|---|
| `the sheet the seller reads is 44 columns wide today` | **yes** — red on the named check |
| `the sheet the seller reads is 74 columns wide today` | **no — all 78 green** |

**The four source files do not share it.** The same `74` sentence put into
`ledger.py` goes red, because those files carry no accounting list and every
column count in them is asked about directly. **The hole is the register's alone,
and it is the price of the exemption that makes the register's half work at all.**

**WHY IT DOES NOT BLOCK, and I want the reason weighed rather than taken:** the
register's prose is documentation, not behaviour — a wrong sentence there misleads
a reader, it does not make the ledger wrong, and the width that decides anything is
the field, which is pinned. The escape needs the wrong number to land on one of
five values *and* the sentence to avoid a word it would naturally use.

**AND THE CODE DOES NOT OVERCLAIM IT.** `sales_checks.py:363` says *"a count that
is neither the ledger's width nor one listed there is a count nobody has accounted
for"* — which is exactly and only what it does. **The register's own entry is a
hair broader**: *"a wrong width in a sentence that never says 'ledger' is caught as
a number nobody accounts for"*. Read strictly that sentence is self-limiting; read
as prose it reads wider than the five-number exemption allows. **D169's whole
subject is a confident sentence outliving the thing it describes**, so I am naming
it rather than letting it sit. **Left for the author.**

---

### 5. NOTE — THE ACCOUNTING LIST IS THE WHOLE OF THE EXEMPTION, AND IT GROWS BY HAND

Each entry in `other_column_counts_this_register_states` describes itself in words
that contain its own count (`"22": "his real Meesho returns file -- 22 columns..."`),
so the list accounts for its own text. That is necessary and it works. **What
follows from it is that every number added to that list is a number that stops
being asked about anywhere in the register** — the exemption widens by one each
time, silently, and nothing marks the difference between "this is a real count of
something else" and "this is how the check was quieted". The commit says the price
out loud in the other direction (a new count turns it red until listed); this is
the same price seen from the far side. **Not a fault today, and not blocking.**

---

### 6. WHAT I LOOKED FOR AND FOUND NOTHING WRONG WITH

- **THE WITHDRAWN D180 DEFERRAL IS GONE, NOT SITTING BESIDE THE FIX (D169).** The
  deferral lived in one place only — the comment at `sales_checks.py`, removed in
  this commit's 18 deleted lines and replaced by an explicit withdrawal. It was
  never a `left_with_a_reason` entry in the register; I checked `55eb1aa`'s
  `work.json` for it and it is not there. The three surviving occurrences of *"there
  is nothing stronger to hold"* are all quotations **of a claim being withdrawn**:
  two in this commit, and A17R's own finding in this file, which is the argument
  that produced the withdrawal. Removing those would hide that a correction
  happened, which is the opposite of what D169 asks.
- **NO LINE-ENDING CHANGE SURVIVED INTO THE COMMIT (D174).** Measured on the stored
  blobs, not the working copy: `sales_checks.py` **400 of 400 CRLF at `55eb1aa`,
  481 of 481 at `2c120d7`**; `work.json` **1,188 of 1,188 and 1,214 of 1,214**. Both
  files pure CRLF on both sides, so the text-mode flip that hit `sales_checks.py`
  mid-work did not reach the commit. `git diff` against `--ignore-cr-at-eol` gives
  the identical `99/18` and `27/1`. `git diff -w` reports `28/2` on `work.json` —
  **one line more, not fewer**, which is a different alignment of the closing `],`
  and not a whitespace-only edit hiding in the diff; I read every `-w` line to be
  sure.
- **THE NEW CHECKS ARE REACHED, NOT MERELY GREEN (D190).** I neutered the four-file
  loop so it ran over nothing. **`FAIL checks went missing -- 74 ran, 78 expected`.**
  The absent-alarm case is held by the count guard, which is the second question
  D190 says nobody asks.
- **THE CHECK DEGRADES LOUDLY, NOT QUIETLY.** A register that cannot be read, cannot
  be parsed as JSON, carries no field, or carries no accounting list each reddens a
  check rather than skipping one — `bool(ACCOUNTED_FOR)` and `bool(WIDTHS_CLAIMED)`
  are both asserted, so an empty result is a failure and not a pass. A named source
  file that goes missing is red too, through `bool(said)`.
- **SECURITY.** Nothing this commit adds holds, sends or names a secret. It adds one
  integer and five short descriptive strings to a register the gate already reads,
  and seven checks that read files already in the repository. **This repository is
  copied into every seller's own GitHub account** — after this commit their copy
  contains one number and five sentences about spreadsheet widths, and nothing else
  changed.

---

### 7. WHAT THIS REVIEW COULD NOT SETTLE

- **THE HOUR (D192).** My sweep ran at 09:18-09:50 IST, so the 18:30 UTC to midnight
  IST window is untested by me for the whole 2,516. It cannot touch this commit's
  own checks, which read no clock; I cannot speak for the rest.
- **THE TWENTY-FIVE `raise` LINES A17R FOUND** in `tools/gate.py` and
  `tools/gate_run.py` that no check has ever executed are still there and still
  outside this unit. I did not drive them.
- **`the_other_half.py:108` AND `:116`** — A17R's absent alarms in the file this
  commit's pin depends on — are unchanged and still uncovered. **The pin at section
  3 runs through `:116`'s design**, so it is worth naming here even though it is
  older than this unit and outside it.

---

### 8. AND SO IT IS COMMITTED

`2c120d7` had no reader who did not write it, and it holds. **The number that lived
only in prose is a field, the field is pinned to the list the ERP owns, all six
places are asked about by their own names, and the fault A17R said could not be
caught is caught in both of the places it can be written.** Two findings, neither
able to let a bad commit through, both left to the author (D166, D180). This entry
goes through the gate with its own review record and no `--no-verify`, and
`2c120d7` goes up with it (D158).

---

## 2026-09-05 (twelfth, CORRECTED SAME HOUR) — A19R correcting its own entry above. **THE LINE-ENDING MEASUREMENT IN SECTION 6 WAS TAKEN WITH A BROKEN INSTRUMENT AND ITS LABEL IS WRONG. The conclusion it supported is unchanged and still true.**

**This correction is appended rather than edited into the entry above** (D174,
and D166's reason one level up: hiding that a claim was corrected is the fault
D169 exists to stop). The entry above is left exactly as it was written.

### WHAT I GOT WRONG

Section 6 says `sales_checks.py` was **"400 of 400 CRLF at `55eb1aa`, 481 of 481
at `2c120d7`"** and that **"both files"** are **"pure CRLF on both sides"**. The
commit message of `9465cf0` says the same thing, and it is already pushed.

**`sales_checks.py` is pure LF, not CRLF.** Measured again, in Python, on the
blobs git actually stores:

| file | `55eb1aa` | `2c120d7` | `9465cf0` |
|---|---|---|---|
| `autosync/sales_checks.py` | **400 LF, 0 CRLF** | **481 LF, 0 CRLF** | 481 LF, 0 CRLF |
| `tools/work.json` | **1,188 CRLF, 0 LF** | **1,214 CRLF, 0 LF** | 1,214 CRLF, 0 LF |
| `REVIEW.md` | 1,920 CRLF, 0 LF | 1,920 CRLF, 0 LF | **2,138 CRLF, 0 LF** |

**The two files do not share an ending, and never did.** `sales_checks.py` is LF
and `work.json` is CRLF — which is precisely the four-files-four-answers mess
D174 describes, and I flattened it into one wrong word.

### WHY THE INSTRUMENT WAS BROKEN, BECAUSE IT WILL CATCH THE NEXT PERSON TOO

I counted with `grep -c $'\r$'` from inside a double-quoted command substitution.
**It matches every line of any file, LF or CRLF.** Demonstrated both ways:

    printf 'a\nb\n'     > lf.txt    ; grep -c $'\r$' lf.txt    -> 2
    printf 'a\r\nb\r\n' > crlf.txt  ; grep -c $'\r$' crlf.txt  -> 2

**It never returns anything but the line count**, so it agreed with `wc -l` every
time and looked like confirmation. It is a check that cannot fail — D180's own
subject, and I built one by accident inside a review whose whole business is
finding them. **It also told me `KARTAAN-STATUS.md` was 11,997 of 11,997 CRLF
when that file is pure LF**, and I only caught it because a byte-level append
there reported a number the grep could not have produced.

### WHAT SURVIVES, AND IT IS THE PART THAT MATTERED

**Nothing about the verdict changes.** The question D174 asks is whether a
line-ending flip survived into the commit, and the answer is still no:

- **`sales_checks.py`: 0 CRLF before, 0 CRLF after.** Pure LF on both sides. The
  text-mode write that flipped all 400 of its lines mid-work did not reach
  `2c120d7`.
- **`work.json`: 0 bare LF before, 0 bare LF after.** Pure CRLF on both sides.
- **Each file is internally consistent and unchanged in its endings across the
  commit.** `git diff --ignore-cr-at-eol` still gives the identical `99/18` and
  `27/1`, and that comparison was never affected by the broken counter.
- **My own append is right too.** `REVIEW.md` is pure CRLF and I appended CRLF to
  it, 218 insertions and 0 deletions, verified in Python rather than by grep.

**So section 6's conclusion holds and its label was wrong.** I am correcting the
label rather than quietly leaving a sentence that names the wrong ending for a
file the next reader will edit.

### AND ONE THING THE RE-MEASURE TURNED UP

**The five-number limit at section 4 is not written down anywhere a reader will
meet it.** The author's own note records it as being "in the check's own
comment". It is not. The comment at `sales_checks.py:369-372` states the
*mechanism* — *"a number that is neither the ledger's width nor one of the counts
the register lists"* — from which the limit follows if you work it out, but **it
never says that a wrong width equal to one of the five accounted numbers passes.**

**A limit that lives only in a session's private memory is the shape D169 is
about.** The memory will be gone; the code will not. This does not change my
ruling — still non-blocking, still left for the author (D166, D180) — but it
raises the reason for naming it: the limit is not merely worded broadly in the
register, it is absent from the two places the next person will actually read.

### THE HOUR IS UNCHANGED

Still 09:18 to 09:50 IST on 2026-09-05 for the sweep, and this correction was
written and re-measured at 10:05 IST (D192). The tree was clean at `9465cf0`
before this append and nothing in `autosync/` or `tools/` was touched by it.
