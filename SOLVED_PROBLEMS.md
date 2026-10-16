# SOLVED_PROBLEMS -- Kartaan-AutoSync

Golden Rule 19, "the loop, made real" (2026-09-14). **Read this before writing any code here, and hand it to every
reviewer.** One line per mistake already caught and fixed, written as the rule that would have prevented it, with
the file where it happened. A reviewer finding something already on this list is the loop failing -- say so.

## Finding things on a portal page

- A row lookup stops climbing after six levels, and the moment it takes in another match it is no longer a row. -- `extension/driver.js` `whatMatches`
- A page heading is waited for as words (`BY_TEXT`), never pressed as a control. -- `autosync/recipes.py` `fk_claims`
- A portal menu item is pressable text (`BY_PRESSABLE_TEXT`), not a role control, until measured to be a real control. -- `autosync/recipes.py` (views chips, `Request New Report`)
- Words are often a label: press the control or button beside them (`BY_THE_CONTROL_BESIDE`, `BY_THE_BUTTON_BESIDE`), not the words. -- `autosync/recipes.py` (Reports Centre date box, `REQUEST REPORT` rows)
- When a `div role="button"` and a real `<button>` carry the same words, ask for the real button (`BY_A_REAL_BUTTON`). -- `autosync/recipes.py` `me_payments`
- A box somebody types into is never a pressable match for words. -- `extension/driver.js` `looksLike`
- A click goes to the nearest pressable thing; an `<svg>` has no `click()`. -- `extension/driver.js` `pressIt`
- A refusal on several matches says where each one sits, or the cause cannot be seen. -- `extension/walk.js` `gaveUp`, `driver.js` `where_they_sit`
- A button's words can carry its icon's text (`downloadDownload`, `Request Listings Reportdownload`); match loosely only on a row already pinned by day and kind. -- `autosync/recipes.py` `_reports_centre`, `fk_views`
- A row control can change between days: re-measure the row before trusting a recipe written earlier (listings rows gained a `Download` button). -- `autosync/recipes.py` `fk_listings`
- A settle that finds nought keeps waiting while patience remains; nought is not an answer mid-draw. -- `extension/driver.js` `find`
- "Something is covering the page" is a guess: Flipkart's own layout is a fixed full-window section, so check the page before believing it. -- `extension/driver.js` `sitsOverTheWholePage`
- A full-window backdrop that is `visibility: hidden`, `opacity: 0` or `pointer-events: none` covers nothing (Seller Insights keeps a hidden drawer backdrop at full window; every miss there read "covered"). -- `extension/driver.js` `sitsOverTheWholePage`
- A covering is judged by width and height alone, never by where the box sits: a picker kept mounted off-screen after its own "Done" click would still count as covering the whole page. -- `extension/driver.js` `sitsOverTheWholePage`
- A failure that says something is covering the page threw its own words away: it named that a covering happened, never what it was, so naming it again cost a live session every time. -- `extension/walk.js` `gaveUp`

## Dates and calendars

- A calendar day refused by `cursor: not-allowed` must be read as switched off, or Flipkart silently clamps to another day. -- `autosync/recipes.py` `switched_off_days_change_the_cursor`
- A day the portal has not built is "not available yet", remembered and retried oldest first, never "failed"; after three different days it needs the seller. -- `extension/walk.js`, `extension/nightly.js` `NOT_BUILT_YET`
- A Flipkart request counted before a Submit that never happened is given back. -- `extension/nightly.js` `theCountGivenBack`
- A Reports Centre day switched off in the morning can be open by the afternoon: Flipkart's last open day moves (the weekend 09-19/20 was off at 14:19 IST and open by 17:30). Measure the calendar before blaming the range; the start day is named only because it is checked first. -- `docs/FLIPKART.md` (Job 4), `extension/driver.js` `clickTheDay`
- A month's grid also draws the next month's first days, greyed: on a calendar that marks days off in the cursor, only pressable cells count as the day (09-01 found two "1"s). -- `extension/driver.js` `clickTheDay`

## Pages, tabs and waiting

- A fresh Flipkart tab restores its last route: load the base page, then set the address, and measure on the right tab of the right page. -- `autosync/recipes.py` `TRAFFIC`
- An address that differs only after `#` is not a page load: force a reload or the page half never runs again. -- `extension/doors.js` `goTo`
- Never reload a deep Flipkart `#` address (it lands on `#dashboard/page-not-found`): load the page before the `#`, then set the route from inside the page. Proved 2026-09-15 by `flipkart_fk_ads_daily_2026-09-12.csv`. -- `extension/doors.js` `goTo`, `routeInThePage`
- Load Flipkart's plain `https://seller.flipkart.com/`, never `.../index.html`: `index.html` with no route bounced to `#dashboard/page-not-found` before every report (the seller saw it every time); the recipe addresses keep `index.html#...` and only what the door loads changed. Proved live 2026-09-23 (every report landed, no flash). `sameDocumentAs` is untouched: the load address never has a `#`, so it answers yes only for the very same address twice, and `goTo` still reloads then. -- `extension/doors.js` `thePageToLoad`, `goTo`
- Chrome's "finished loading" on Flipkart takes 30-50 s; a slow finish is not a failure once a page has already taken the walk up. -- `extension/background.js` `startAWalk`
- A page-load wait counts the browser's whole load, not first paint; heavy pages (Seller Insights, 38 s) need 60 s. -- `extension/background.js` `startAWalk`, `fk_views` `go`
- A run's own window must come to the front when a report starts: an unfocused window behind the seller's is slowed like a hidden tab (three Meesho reports failed their first page load). -- `extension/doors.js` `aTabToWalkIn`
- Every report a run puts away needs a file name in the recipe file, including those another report's run lands (`me_ads_summary`, `me_ads_catalog`). -- `tools/export_recipes.py` `fileNames`
- A Flipkart walk's tab must be the one on screen; never open or select a tab while a walk runs, and release runs in its own window. -- `extension/doors.js` `WALK_IN_HIS_OWN_WINDOW`
- "NO ANSWER" from Run now does not mean it did not start: read the status before starting again. -- working rule
- A remembered value is written to the same storage it is read from: the replacement walk tab went to `local` but was read from `session`, so it was never found again. -- `extension/doors.js` `aTabToWalkIn`
- Test one report at a time. -- working rule
- Reloading a Flipkart tab means a real page load: changing only what follows `#` keeps the old page half (add or change something before the `#`). -- working rule
- After every extension reload, reload EVERY open platform tab: a tab left open keeps the old page half, which cannot reach the extension, and a file handed through it never reaches Drive ("Receiving end does not exist"). -- working rule

## Taking the file

- The page half gives up later than the background, so a bare `null` from a timeout never beats the background's real answer. -- `extension/content.js` `takeFile`
- The file catcher must be in the page at `document_start`, before the portal's own scripts copy `URL.createObjectURL`. -- `extension/manifest.json`, `extension/catch-early.js`
- A handle the catcher just caught is not also downloaded when the page clicks a link to it. -- `extension/catch-blob.js` `justCaught`
- A download link is taken only from a known report address, or from the page's own platform site and then kept only if its bytes open as a spreadsheet; a link let go is named in the failure. -- `extension/catch-blob.js`, `extension/driver.js`
- Allowing pop-ups is never the fix: an allowed pop-up downloads into the seller's Downloads folder, not Drive. -- `extension/catch-blob.js`
- A 200 is not the report: a web page answered for a file address is refused. -- `extension/walk.js` `looksLikeAPage`
- The extension's word is not the file: confirm every landing by reading Drive itself. -- working rule

- A banner is watched for as it is drawn, not looked for afterwards: it can vanish before a slowed tab looks again. -- `extension/driver.js` `aBannerRecorder`
- A confirmation that can vanish needs a durable second proof -- a banner already seen, or the platform's own list row. -- `extension/walk.js` `whatElseCounts`, `autosync/browser.py` `Step.or_find`
- Close pop-ups only by controls that say they close something, never by words like "OK", and never in the top bar. -- `extension/driver.js` `closePopUps`
- A list that picks on button down selects nothing on a bare click: measure it, and mark only that step to press like a mouse (down, up, click), never every press. -- `autosync/recipes.py` `_ads_overall`, `extension/driver.js` `pressIt`
- Setting a box's value does not start a portal's search; type with the page's own insert-text command. -- `extension/driver.js` `typeIn`
- A search box's list may open only when the box is pressed: after typing, press the box, then the suggestion (Flipkart campaign id). -- `autosync/recipes.py` `_ads_overall`
- Wait for a label exactly as measured, never as the reference's loose words suggest (`Ad Group ID (optional)`, not `Ad Group`). -- `autosync/recipes.py` `_ads_overall`

- A way out of a promotion can be a picture rather than a word: an `<img>` named `cross-grey.svg`, with no label, no role and no pointer cursor, is still the only way to shut it. -- `extension/driver.js` `looksLikeACloseButton`
- Every file name the walk can build must be checked against the Drive guard, built by the walk's own function: the per-campaign name (`..._<day>_<campaign>.csv`) was refused because the guard wanted the day last. -- `extension/background.js` `whyTheseAreNotNames`, `NAMED_PER_CAMPAIGN`

## Runs and records

- A two-phase report remembers what it was asked under across runs, so the next run collects instead of asking again. -- `extension/nightly.js` `WHAT_IS_BEING_BUILT`
- Everything that can move a night on runs one at a time, or two callers book one finished walk twice (`fk_ads_fsn` listed twice, 2026-09-14). -- `extension/nightly.js` `carryTheNightOn`
- A walk's answer that arrives after its own night ended belongs to that night: a new night clears it, never books it. -- `extension/nightly.js` `carryItOn`, `background.js` `beginTheWalk`
- A message sent to a page straight after it was opened can be lost: check the page answers, then send, and read the status before sending again. -- working rule
- The seller's own panel name travels with the night, not through untested wiring. -- `extension/nightly.js` `startTheNight`
- A file named by one day is not the only shape: a running list covers many days. -- `autosync/landing.py` `Arrived.covers`
- A report fetched by another report's run is not "cannot be fetched". -- `autosync/recipes.py` `MADE_BY_ANOTHER`
- A report that reads another's list pulls that report in front of it, for every day it owes; a day whose list was never fetched is owed, never counted towards "needs you" (`fk_ads_overall` ticked alone, 09-18..09-21). -- `extension/screen.js` `withTheListsTheyRead`, `extension/nightly.js` `listFrom`, `rememberWhatIsNotBuilt`

- The timed sync keeps its own list (every report by default, less what he put off: `fk_keywords`) and the panel says how many; Run now ticks never feed it (two ticked ad reports became the whole daily sync, no Meesho, 09-18..09-20). -- `extension/screen.js` `theTimedList`, `startTheScheduledSync`

- A row a seller can tick must be a report the worker will accept on its own: one untickable id in the set makes "Tick all" save nothing and Run now start nothing, silently. -- `extension/screen.js` `buildOneReportRow`
- What the panel's boxes hold has to be passed on by the code that answers it, or the seller's chosen days become yesterday. -- `extension/screen.js` `answerThePanelsQuestion` (`run-now`)

- A report that is a picture of how things stand now is left out of a past day by name, not failed on it -- and that is not the same as a rolling window, which still hands over what is in the tab. -- `extension/nightly.js` `ONLY_ITS_NEWEST_DAY`
- The hourly recheck asks whether a report was already seen asking for something; a report with no asking phase never is, so it got one try and was written off while every two-phase report got three (`me_views`, 2026-09-22 -- landed on the very next try with nothing else changed). -- `extension/nightly.js` `RECHECK_EVEN_WITHOUT_AN_ASK`, `thatOneIsDone`

- A day a report owes only when SOMETHING has already tried it and been refused is not the same as every day it is owed: a day the timed sync's own list simply left out (F5, two Flipkart ad reports standing in for the whole daily list 09-18..09-20) is nowhere in that record at all, and nothing was ever going to fetch it. Owed the other way too -- calendar time since the last real file, never whether an attempt happened -- the same rule `autosync/schedule.py` already keeps for the API door. -- `extension/nightly.js` `daysNobodyTried`, `LAST_LANDED`
- Remembering only the NEWEST day a report has landed cannot find a hole a later day already landed past: a real Drive held a report for one day, then a gap of three days, then a later day landed anyway (that sync caught up its own day, not the hole behind it). Caught before the live proof, from reading what the real Drive held rather than trusting a simpler design; the whole SET of landed days is kept instead, the same shape `autosync/schedule.py` already uses for the same question on the other door. -- `extension/nightly.js` `LAST_LANDED`, `extension/drive.js` `landTheFile`'s `alreadyThere`

- A page that runs when nobody is watching has to say when it next wakes; without it, an hour saved after that minute had passed looks exactly like a clock that is broken. -- `extension/screen.js` `whenItNextWakes`

- Chrome never releases a saved password to a click a script made, so no extension can sign a seller in by itself; try once, then ask them and wait. -- `extension/driver.js` `trySigningIn`
- A notification whose picture is a `data:` image is refused silently: ship a real icon file and read `lastError`. -- `extension/worker.js`, `tools/write_icon.mjs`
- Save only what he unticked, never just the ticks: then a report he never chose opens ticked, and files one request brings show that request's tick instead of a box of their own. Both websites ticked go through the timed sync's queue (Flipkart, then Meesho), with every part checked before anything starts. -- `extension/screen.js` `showWhatIsTicked`, `run-now` (A61, Job 5b)
- A once-only flag two different callers share for two different jobs can be spent by the wrong one: `rememberTheNight`'s ledger-filing flag is meant to be called by anybody, any time (`howItStands` does, every panel poll) -- but `carryOn` used that SAME flag to decide whether to write the run log, the end-of-sync notice, and the next scheduled platform, so a poll landing the instant a walk finished could win the race and leave all three silently skipped. The fix is a second, separate once, touched by nothing but the thing it gates. -- `extension/screen.js` `alreadyCarriedOn`/`markCarriedOn`, `extension/worker.js` `carryOn` (A64, Job 7)
- A day handed to him as "needs you" does not clear itself just because the platform will never build it -- the ordinary clear only fires when a later sync really lands the day. Clearing one by hand needs its own function, and it must take an exact named list (report and day, or report and month), never a wildcard, so it can only ever remove what he actually said yes to. -- `extension/nightly.js` `clearNamedNeedsYouEntries` (A64, Job 7)
- "N of M reports were reached" counted every ATTEMPT (`night.done.length`), not every real outcome, and a report asked then collected later gets two entries for one report-day -- so a night could say "reached" for a day that was refused, and count a two-step report twice. Five real states (landed, waiting on the platform, not started, needs him, failed) have to be counted separately, from the LAST entry per report-day only. -- `extension/nightly.js` `theNightsCounts`, `howTheNightWent` (Job 8, F6, A65, 2026-09-23)
- "Every report was reached" is a claim about the ATTEMPT, not the outcome, and writing it unconditionally whenever the night's owed list empties out reads as a clean night even when reports needed the seller or failed -- dozens did. It is written only when nothing behind it needed him or failed; otherwise the reason names what did not land. -- `extension/nightly.js` `startTheNextOne`'s ending branch (Job 8, F6, A65, 2026-09-23)
- A count's own wording has to name exactly what it counts, or a true number reads as a false one: "N of M allowed Flipkart requests were spent" only ever counted the Reports Centre's twenty (`fk_orders`, `fk_payments`) -- every ad report asks Flipkart by a different door and was never in the count. a count of nought on a night that ticked only ad reports was genuinely true and not a counting bug, but the generic wording read as if it covered everything asked of Flipkart that night. Named explicitly, or a correct number is read as a lie. -- `extension/nightly.js` `howTheNightWent` (Job 8, F6 part 3, A65, 2026-09-23)
- The size that lands and the size that was downloaded are not the same number for a zip: `drive.js` `landTheFile` opens a zip holding one spreadsheet for real before it uploads (`unzip.js` `theSpreadsheetInside`), so Drive ends up holding more bytes than the walk's own download -- measured on a payments file, the log said one size (the zip) and Drive held another (the spreadsheet inside it). The size that really landed has to travel back across the same boundary the bytes crossed (`background.js`'s `land-the-file` answer), or the walk has no way to report anything but the zip's own number. -- `extension/background.js` (`land-the-file`), `extension/walk.js` (TAKE_FILE) (Job 8, F15, A65, 2026-09-23)

## Reading the reference

- Where the reference's `DOCS.md` and its code disagree, the code is the truth -- `fk_returns` uses the Returns page, not the Reports Centre `DOCS.md` names. -- `autosync/recipes.py` `fk_returns`
- When stuck, read how the reference does that report before probing a live panel. -- working rule
- Before building a recipe, compare it with the reference's CODE for that report, not only its guide; a recipe built from the guide alone took a route the reference had already abandoned. -- `autosync/recipes.py` `fk_returns`
- Words that open a calendar may be a plain label: press what the reference presses and confirm on the page (the text box beside `Date of Closure` opened nothing). -- `autosync/recipes.py` `fk_returns`
- Not every fact has a written reference: Flipkart's own official Report Management API docs name only Listing, Order and Report(Settlement/FBF) -- no ads/advertising section exists there at all. Where no official doc covers it, the live product's own behaviour (the calendar's own `cursor: not-allowed`) is the reference, read directly and dated, not guessed from a blog. -- `docs/FLIPKART.md` "How far back the ads calendar reaches" (A64, Job 7)
- The ERP cannot read the run's Drive record (`drive.file` reaches only files its own Google app made), so the run copies the landed-against-read cross-check into the seller's `sync_check` (`<reportId>::<day>`, four fields, no counts, last 60 days; older rows found by one query on `dataDate` and deleted). It is its own step with its own `try` AFTER the manifest save, using the merged record kept in memory, so a Drive blip on the manifest or a refused database write costs the fetching nothing and is said as a fault. Up to 29 reports x 60 days = 1,740 writes a run, plus one query and any deletes. -- `autosync/nightly.py` `one_tick`, `autosync/firestore_door.py` `a_check_sink`
- A return is named by the platform's own key for it (Amazon's RMA id), never by order plus SKU: two returns of one line collided and the second was lost with the manifest saying every row was read. -- `autosync/returns.py`
- A key named twice in one file with different words is said by name, never silently the first. -- `autosync/returns.py` `read_returns`
- A campaign id with a slash is refused by name in every kind of ad record, or the writer refuses the whole file every night and it is never marked read. -- `autosync/ads.py` `read_ads`
- A Flipkart ads file for a range of days has no one day to be filed under and is refused, not filed under its first day. -- `autosync/ads.py` `refuse_a_range`
- Month names are read as `Sept` as well as `Sep`, or one return's date refuses it for ever. -- `autosync/returns.py` `_MONTHS`
- A check that reads past a record that may not be there crashes the run rather than failing a named check; and a sink must be tested with more records than one call of 100 can ask about, or records past the first hundred are rewritten every night. -- `autosync/returns_ads_checks.py`
- A hourly re-check that Kartaan refused (or could not be reached for) must not re-arm its fifteen-minute alarm: each ask counts against the thirty a day and would end in a 429 for the seller's own run. -- `extension/worker.js` `onRecheck` (PROOF in `extension/kartaan.test.js`)
- A record that could not be READ is not a first run: with nothing found by name, refuse and make no sheet; only a cleanly read 'no record' with nothing by name or in the bin makes one. -- `autosync/returns_sheet.py` `_make_sure` (PROOF in `autosync/returns_sheet_checks.py`)
- A call carrying the run pass sets `redirect: 'error'`, so a redirect can never take the pass elsewhere; it reads as the could-not-reach words. -- `extension/kartaan.js` `post` (PROOF in `extension/kartaan.test.js`)
- Run from a commit hook, the check that reads the other repository's HEAD asked THIS repository (git's GIT_DIR leaks in) and called a committed file missing; every GIT_ pointer is now taken out of that call. -- `autosync/the_other_half.py` (check in `autosync/the_other_half_checks.py`)
- Kartaan is told a sync finished ONCE per whole sync (after the last platform), not at each platform's end: an earlier platform's night remembers its failed and needs-you ids and says it is waiting; the last one tells with all of them and forgets them; a new whole sync starts with nothing remembered. -- `extension/nightly.js` `tellThatItEnded`, `extension/screen.js` `startASyncInTurn` (PROOF in `extension/kartaan.test.js`)
- Compare a sender's scheme and host, never `URL.origin`: a `blob:` address's origin is the page that made it, so an origin test lets it through. -- `extension/background.js` `answerAnExternalAsk`
- A field added to a screen record must be read by the screen; one only a check reads is dead. -- `extension/screen.js` Amazon platform entry
- Edit CRLF files through `newline=''`; a default Python text write flipped a whole check file's line endings and buried a 24-line change in a 3,300-line diff. -- `extension/screen.test.js`
- Two offers of one Amazon ASIN are two listings, keyed `ASIN::seller-sku`; keyed by the ASIN alone the second offer was refused as a repeat and its price and stock lost (D326). -- `autosync/listings.py` `AMAZON` (PROOF in `autosync/listings_checks.py`)
- A key rule built from tidy ids (no space in any part) drops names the seller typed: 26 of the 88 SKUs in his real Amazon file have a space, and D326's new key made them part of the id. Run a new key rule over his real file before calling it done. -- `autosync/listings.py` `_the_key` (PROOF in `autosync/listings_checks.py`)
- A time a platform writes with its own offset is moved to the seller's day (India) before the day is taken, and a time with no offset is refused by name, never guessed: three of nineteen Amazon rows were dated a day early because the first ten characters of a UTC time were used. -- `autosync/orders.py` `the_day_in_india`
- A status word is translated from the platform's own documented list (Amazon's `Order.OrderStatus`) plus the report phrases seen in his real files, and a word nobody has listed stays 'not understood yet' AND is named with its count in the night's report: fourteen of nineteen Amazon rows read 'not understood yet' with nothing saying which word. -- `autosync/orders.py` `what_happened`, `autosync/reading.py` `words_not_understood`
- A return whose platform ID can be blank is keyed by what is always there (order, SKU, request day) and a row that later gains its ID is written over that earlier record, not beside it: rows with a blank Amazon RMA ID were dropped, and keying by RMA alone would have made a second return the day it arrived. -- `autosync/returns.py` `a_return_without_an_rma`, `autosync/firestore_door.py` `a_returns_sink`
- A payments file with lines whose order has not arrived is not written down as read, and the night says how many lines wait; marked read, the 142 Flipkart lines whose orders came later would never have been tried again. -- `autosync/reading.py` `payments_waiting`
- A guard that drives a reader with a made-up cell must write the cell in the shape the platform really writes (Amazon's time carries an offset); a bare day was refused by the new reader and the guard stopped all writing. -- `autosync/reading.py` `would_a_file_say_which_day_it_is`
