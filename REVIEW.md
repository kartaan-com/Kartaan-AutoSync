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
