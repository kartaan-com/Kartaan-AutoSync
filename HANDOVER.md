# Handover from A26 — 2026-09-05/06

Written for a session that starts with nothing. Everything below is either
measured or named as unmeasured. Where I was wrong, it says so, because you
inherit my code and not my memory.

**Read `C:\Users\jaisw\.claude\projects\D--Kartaan-AutoSync\memory\active.md`
first — it is longer and it is the record. This is the short road map.**

---

## THE ONE THING TO KNOW BEFORE YOU TOUCH ANYTHING

**A night may still be running in his Chrome, walking his real Flipkart seller
account.** If it is, do not reload the extension and do not edit
`extension/recipes.json` — the content script re-fetches that file on every page
load, so editing it changes the book underneath a walk in progress.

Read the result with one line in the extension's own service worker console
(`chrome://extensions` -> Kartaan Auto-sync -> "service worker"):

```
await self.howTheNightWent()
```

---

## NOTHING BELOW IS ON GITHUB

**Five commits are unpushed** (`main...origin/main [ahead 5]`), including the
columns. Everything this document reports as landed exists only on this machine.
Pushing is his decision and he had not given it in this session — a peer session
relayed that he had, and a relayed authorisation is not one.

---

## WHAT WORKS NOW, AND WHAT HAS ACTUALLY BEEN PROVED

**Proved live, unattended, in a window nobody was looking at (2026-09-05):**
`me_catalog` off his real Meesho panel — state `landed`, **44,600 real bytes**.
Both of `me_orders`' `go` steps were separately proved to destroy their own page
and be picked up again by the next one.

**Never proved:** the Drive half. **Nothing in the product imports
`extension/drive.js`** — only its own `drive.test.js` does, and its 65 checks
pass against a stand-in. No
file has ever reached a real Google Drive from this extension, and there is no
interactive path by which a seller could connect one for the first time. "A real
report reaches Drive unattended" has been impossible since before I started and
is still impossible.

---

## THE COLUMNS — DONE, AND THE REFUSAL HAS LIFTED

**This is the thing that changed today and the next session should know it
first.** The ledger writing had refused to touch Google since it was built, and
that refusal is why no sale has ever reached a sheet. It was waiting on four
columns. The ERP landed its half (`fc82dc7`), this repository landed the other,
and the refusal ended **by itself**:

```
ledger.what_the_sheet_cannot_yet_say()    ()     was all four
ledger_sheet.why_it_must_not_write_yet()  ''     was a paragraph
```

Nothing was written to make that happen — `sales.COLUMNS` is pinned to the ERP's
committed list, so it lifts the day they land, exactly as `work.json` said it
would a day before it did.

**WHAT IS STILL NOT TRUE: nothing has ever been written to a real Google Sheet.**
The refusal stopping is not the write happening. And **nothing fills the four
columns yet** — deliberately, matching the ERP's half: the columns are declared,
and what puts a date in one belongs with whatever reads a file. **Until something
does, D150 rule 2 is enforceable in principle and not yet in fact.** That is the
next piece of this thread.

### What to carry from how it was done

**The order was `ordersOn, returnsOn, paymentsOn, claimsOn`, and THREE places in
this repository had `returnsOn` and `paymentsOn` swapped** — `work.json:970`,
`work.json:1221`, and `ledger.py:112`, the last of which is joined straight into
the nightly alarm that tells a person which columns to add. **The instruction
asking for the work had them swapped too.** Only the ERP's own committed file was
right. All three are corrected now.

**AND `REVIEW.md` STILL CARRIES THE SWAPPED ORDER IN THREE PLACES — `:1433`,
`:1445`, `:1683` — AND THAT IS CORRECT. DO NOT EDIT IT.** It is an append-only
dated record quoting real output from the day it was wrong. **This sentence was
in an earlier draft of this document, I deleted it while rewriting, and a
reviewer caught that the deletion turned a known-and-explained residue into a
trap:** grep for the swapped order, find three hits, read "all corrected", and
either edit an append-only record or copy the order out of `:1445`, which reads
like the alarm's own output.

**If you ever carry these names anywhere, take them from `Kartaan-ERP`
`src/shared/data/sheet-store.js` and from nothing else.**

**The width was written in FOURTEEN places, not the eleven I first counted** —
three more turned up in `ledger_door_checks.py` as hand-typed ranges. Everything
is derived now except one number that cannot be: `work.json`'s
`the_ledger_is_this_many_columns_wide`, held to `len(sales.COLUMNS)` by
`sales_checks.py`.

**Twelve checks encoded the old answer and were rewritten with the change, never
deleted for going red.** The interesting group: `ledger_sheet_checks.py` used to
stand the refusal DOWN so the rest of the file could run. It now takes the
columns AWAY for one block and puts them back — **the refusal is driven rather
than waited for, because a guard nobody has watched fire is a guard that could
have stopped working the day it was needed again.**

---

## D220 — DESIGNED, NOT BUILT

A seller runs the platforms they are set up for. Today
`.github/workflows/autosync.yml:132-141` gates on **all eight** secrets with one
`&&` chain: one missing and the whole fetch is skipped **with a green tick**.
`start.py:56-83` calls `nightly._needed` eight times unconditionally and
`SystemExit`s on the first gap. **A seller waiting weeks on Amazon's
private-developer registration (D83) fetches nothing from Flipkart or Meesho
either, green every night.**

**The eight are not eight of a kind:**

| | |
|---|---|
| `DRIVE_FOLDER_ID`, `FIREBASE_PROJECT_ID`, the three `GOOGLE_*` | **Kartaan's own plumbing.** Evidence about no platform. |
| the three `AMAZON_*` | the only ones that are about a platform |

**Proposed:** two questions, not one. *Can Kartaan land anything?* — the five
plumbing secrets, missing means loud red. *Which platforms are connected?* —
per platform, and a platform that is not is **skipped by name in the run log,
never silently**. `_needed` stays exactly as it is; only *when* it is called
moves.

**AND THE THING TO SETTLE BEFORE BUILDING IT:** the browser platforms need **no
secrets at all** — they run in the seller's Chrome. So "is Meesho connected?" is
not answerable from the secrets, and the gate has been speaking for two platforms
it does not run. That is a product decision, not a code one.

---

## FOUR PARKED JOBS

1. **The armed download-cancel does not survive the walk (a declared departure
   from D196, which was set the same day).** `expectingUntil` is a variable in the
   service worker and has to be — the cancel must run with no `await` in front of
   it. Chrome kills that worker after 30 seconds of quiet, and during a `wait-for`
   step **nothing reaches the worker at all** (`driver.js` never touches
   `chrome`). `me_orders` waits 60s at step 7. **A reviewer proved it: worker died
   between arm and click, cancelled 0, erased 0.** Two checks in
   `background.test.js` PIN this as a known fault. **Only one of the two reddens
   when it is fixed** -- the other says the address is still caught, which stays
   true either way, so do not read the pair as a matched set. The real answer is probably the reference's PRIMARY layer, which this
   product still lacks: `content/intercept.js:305-324` patches
   `HTMLAnchorElement.prototype.click` in the MAIN world and SUPPRESSES the click.

2. **What a timeout means (D205).** All **132** steps across 17 recipes have a
   patience under the 540s the reference measured a throttled 15s wait stretching
   to. Today a timeout MEANS failed. The reference re-scans DURABLE page state
   instead (`report-confirm-fallback.js`). **AND SIX CHECKS IN `doors.test.js`
   WILL FIGHT THE FIX** — they assert we give up when the outside world is slow.
   They are the current answer written down as checks; rewrite them **inside** the
   change, never leave them red and never delete them.

3. **Meesho's date range is two TEXT boxes, not date boxes.** Measured live:
   placeholders "Select From Date" and "DD/MM/YYYY", `dateInputs: 0`.
   `driver.js pickRange` looks for `input[type=date]` and names this exact limit
   in its own comment. **Not fixed because the boxes want DD/MM/YYYY and the walk
   carries 2026-09-04** — which way round a portal writes a date is a per-platform
   fact that belongs in the recipe, not in the driver.

4. **The Drive half's wiring**, and the faults a reviewer found in it while it is
   still latent: no `incompleteSearch` check (a short listing from Drive reads as
   an empty folder -> a second copy of a day); the replace path sends
   `uploadType=media` whatever the size and Google caps that at 5MB; `landing.by`
   is a plain field in JS where the Python derives it; and **there is no
   counterpart to `landing.the_file_that_matters`**, which in the Python sniffs
   the real bytes, unwraps a zip holding one spreadsheet, and refuses what is not
   a report — its absence reintroduces two faults the Python records as having
   already happened to this seller.

---

## WHAT I GOT WRONG, AND HOW IT WAS FOUND

**Every one was found by somebody else driving it, not by me reading it.**

1. **`startAWalk` messaged a blank tab** where no content script was running.
   Nothing was listening. Fixed to the reference's shape: the page asks, the
   background never pushes.
2. **A guard compared two `Date.now()` readings a few lines apart**, which tie on
   a quick machine — so it answered "no" to something that really happened, in the
   direction that kills a good walk. Compares a step NUMBER now, which cannot tie.
3. **I said clearing the remembered window/tab ids on `onStartup` covered it. It
   does not.** `onStartup` fires when a profile starts; if the extension is
   switched OFF it fires at nobody, and **there is no event at all for an
   extension being switched back on**. Off, restart Chrome, on — and last night's
   tab number is this morning's Gmail, which the walk would have made the selected
   tab and navigated away. **Now in `chrome.storage.session`, which Chrome clears
   at exactly those moments.**
4. **My own CORS fallback opened a data-corruption hole** the same day I added it:
   the page-side retry checked only `held.ok`, so a CDN answering **200 with an
   HTML sign-in page** would have been filed as the day's report.
5. **An unattended retry loop in the night runner** — a report left the list only
   when it FINISHED, so one whose walk could not be STARTED stayed owed with its
   allowance already spent. **Twenty real Flipkart requests for one report in
   eighty minutes.** In the file whose own header says it prevents exactly that.
6. **I rewrote `work.json` from CRLF to LF**, turning a one-item edit into 1,187
   insertions — D174's exact signature, from the session that had just recorded
   D174.
7. **I reported a check count of 635 when it was 628**, having counted the string
   `check(` with a regex instead of reading each run's own last line.

### AND THE ONE THAT MATTERS MOST

**THREE separate checks I wrote could not fail for the thing they were named
for.** Each passed with the fault put back, because some other mechanism happened
to cover the same case. **All three were caught only by driving them, never by
reading them.**

- "a report whose walk cannot be started is attempted ONCE" — a `catch` added in
  the same change covered it by accident.
- "no longer said to be being fetched" — the NEXT report overwrites the name
  anyway; only a night of ONE report tests it.
- "after the extension is switched off and Chrome restarted, their tab is NOT
  taken" — **the stand-in Chrome kept counting tab numbers upwards and so could
  never reissue an old one.** The stand-in had to be made harsher before the check
  could fail at all.

**A green check proves nothing until it has been made to go red.** If you write a
check today, break the thing it names and watch it. If it stays green, the check
is worse than nothing, because it reads as cover.

---

## THE NIGHT OF 2026-09-06, AND WHAT IT TAUGHT

Ten free Flipkart reports, zero quota, no retry. **Nine failed identically on
three different pages looking for three different things** — which is one cause,
not nine.

**It was three stale addresses.** Every one redirected to
`#dashboard/page-not-found`, which draws a complete, signed-in page with the
whole sidebar and quietly changes the hash. Corrected in `autosync/recipes.py`,
each replacement driven against his live account BEFORE being written down:

```
#dashboard/advertising/reports  ->  #dashboard/ads/reports/others
#claims                         ->  #dashboard/payments/spf
#dashboard/listings/my-listings ->  #dashboard/listings-management
```

**The obvious rival explanation was wrong and was worth ruling out.** The
reference says at `content/flipkart.js:492` that Flipkart 404s a deep hash opened
in a fresh background tab. Tested both ways: on an already-bootstrapped tab the
OLD addresses still 404'd, and on a brand new tab the NEW one did not. **Cold-tab
bootstrap cannot produce that pattern.** The reference's comment is itself out of
date — the third drift found in it in three days, and the first where the stale
half is its CODE COMMENT rather than its documentation.

**Still true from it, and it matters:** content takes **10 to 25 seconds** to
draw. Every `wait-for` after a `go` must outlast that, and the reason it can is
that the walk runs in a window of its own where Chrome does not throttle it.

**AND THE REASON NINE FAILURES LOOKED LIKE NINE FAULTS WAS MINE.** `walk.js` had
captured *"Oops! We can't seem to find the page you're looking for"* on every one
of them, and `nightly.js:160` threw it away, keeping only
`{reportId, state, say, size, at}`. **One of those sentences reaching the morning
would have ended it in a glance.** Now kept and printed.

**`fk_views` needed no separate cause.** It was mid-walk when we looked
(`at:1`, `pickedUpFrom:1`). My summary printed anything still owed as "never
reached", so a report doing its job read as a tenth failure. **There are three
states, not two** — being fetched / not started / done — and it says so now.
`fk_views` is the control case: it is the one report whose address was never
wrong.

---

## HOW TO WORK HERE

- **D209: the reference answers HOW, never WHETHER.** Go to `D:\rumee-auto-sync`
  before going to him. **Documentation for the answer, CODE for the truth** — they
  disagree, proven three times in three days. And "the reference does X" is not
  enough; "the reference does X TODAY, and here is where I saw it" is.
- **D198: make it work against the real thing before asking anybody to review it.**
- **Measure, never derive.** Check counts come off each run's own last line. Four
  wrong counts on this project in a week came from doing it another way.
- **The stand-ins must be harsher than the real thing, not kinder.** Every place
  `test/fake-chrome.js` is awkward is a real failure that already happened.
