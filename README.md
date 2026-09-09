# Kartaan Auto-sync

**The fetching.** It brings a seller's own reports off Amazon, Meesho and
Flipkart into their own Google Drive, every night, with nobody present.

It is not the ERP. Kartaan itself — the screens, the records, the money — lives
in [kartaan-com/Kartaan](https://github.com/kartaan-com/Kartaan). This is the
half that runs while nobody is watching.

---

## Why this is its own repository

**D36: the pipeline runs in the SELLER'S OWN GitHub account, with the seller's
own secrets.** You cannot hand somebody an entire ERP so they can run a nightly
fetch.

**NOTHING IS COPIED INTO A SELLER'S ACCOUNT, AND THIS PARAGRAPH USED TO SAY THE
OPPOSITE.** A copy is frozen the day it is made: a fix pushed here would never
reach it. The seller's own repository holds ONE file -- a caller, which says
`uses:` this repository's nightly workflow **at a version tag**. The code runs
from here, and a fix reaches every seller who moves to the next tag. That is
D121 and D122, and it is why this repository is **public**.

**IT WAS PRIVATE UNTIL 2026-09-09, AND THE REASON IT WAS IS NOT ANSWERED.**
`autosync/recipes.py` holds the click-by-click steps for Meesho and Flipkart.
That path works only because it runs in a real person's real Chrome and looks
like one (D100, D107) -- and those steps can now be read by anybody. **Publishing
them hands the people trying to stop it an exact map.** D121 traded that away for
a fix that reaches every seller at once. It is written down here rather than
solved, because what to do about it is his.

**The seller's own repository stays private.** Their Amazon and Google
credentials are written into it.

GitHub Actions minutes are the usual reason to go public. They were not the
reason here: one run a day is roughly 150 minutes a month, against a seller's own
free allowance.

---

## What is in here

| | |
|---|---|
| `autosync/` | The connector. Pure Python, no dependencies outside the standard library |
| `extension/` | The browser half. Meesho has no published API and Akamai in front of it, so those reports are fetched in the seller's own Chrome (D100, D107) |
| `.github/workflows/autosync.yml` | What wakes it up: one tick a day, and the trigger that lets a seller's own repository call it |
| `pipeline-template/` | The one file a seller's repository holds -- a caller, naming the workflow above at a tag. Not run from here |
| `tools/export_recipes.py` | Writes `extension/recipes.json` out of `autosync/recipes.py`, so the steps are decided in ONE place and the extension only carries them |
| `test/` | The stand-in browser and the stand-in Chrome |

---

## Running the checks

```
for f in autosync/*_checks.py tools/*_checks.py; do python "$f"; done
for f in extension/*.test.js; do node "$f"; done
```

**Some of them need another repository (D148).** `firestore_checks.py` pins the
three collection names this job WRITES against the names Kartaan's screens READ;
`firestore_door_checks.py` pins the Google scope this door needs against the
scope `Kartaan-Server` actually asks the seller for; and `sales_checks.py` pins
**every column of the seller's sales ledger, and the way a sale is named**,
against the ERP's own `sheet-store.js`, `charges.js` and `orders.js`. One fact,
written down twice, with nothing mechanical joining them -- which is the exact
shape this project keeps paying for.

**They compare the two sides; they do not look for a string.** That distinction
is not pedantry: a check in this package was once named for exactly the fault it
was passing through, because it asserted that the other side CONTAINED some text
rather than reading what each side actually builds. It was green for days while
the Python built a six-part log-line name and the page built a five-part one.

They **refuse rather than skip** when they cannot find Kartaan. A check that
quietly stops checking is worse than no check, because it is still counted.

```
set KARTAAN=D:\Kartaan          set SERVER=D:\Kartaan-Server      # Windows
export KARTAAN=~/Kartaan        export SERVER=~/Kartaan-Server    # anywhere else
```

Sibling folders called `Kartaan` and `Kartaan-Server` are found without being
told.

---

## Where the credentials go

**Settings → Secrets and variables → Actions → New repository secret**, on the
seller's own repository. They live there and nowhere else — not in a file, not
in the workflow, not in a message. Golden Rule 8.

The workflow names them one per line in its `env` block, and the number is
written down nowhere: a hand-typed count is wrong from the moment the next one
lands.

---

## What is known and not fixed

- **The Google app must leave Testing.** Until it does, every refresh token dies
  after seven days.
- **`fake-browser.js` exists in both repositories.** The extension needs it and
  so do Kartaan's screens. Nothing joins the two copies; if one changes, the
  other does not know.
