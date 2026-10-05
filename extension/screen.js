/* What a seller sees, and everything behind it.
 *
 * **UNTIL THIS EXISTED THE EXTENSION HAD NO FACE AT ALL.** Its manifest declared
 * a background worker and two content scripts and nothing else -- no action, no
 * popup, no page, no icon anybody could press. So nothing could start a fetch:
 * not a seller, not a night, not the daily alarm, which fired and said in as many
 * words that nothing decides tonight's list yet. The only doors in were four
 * globals on the service worker, and `worker.js` calls them what they are -- "a
 * handle, not a way in", standing in "until there is a screen for it".
 *
 * **A PAGE, NOT A POPUP, AND THAT IS HIS INSTRUCTION.** His words: *"For
 * extension, it used to open a popup and it used to close. For auto sync I want
 * them to open a web page... it has to be part of the extension itself... the
 * user will have more space, and you will also have more space to build things
 * and organise things. But it'll work exactly like how the popup used to work."*
 * So `panel.html` is a full tab served from inside the extension, and pressing
 * the toolbar button opens it.
 *
 * **THE TWO HALVES ARE BOTH HERE, and the split down the middle of this file is
 * the only structure in it.** Above the line is what the WORKER does when the
 * page asks it something; below the line is what the PAGE draws. They are in one
 * file because they are two ends of one conversation and the shape of the answer
 * is the thing they must agree about -- which is exactly the fault this project
 * keeps paying for when one fact is written down in two places.
 *
 * **NOTHING HERE READS `innerText`, and that is a measured rule rather than a
 * style.** Reading a page's `innerText` forces the browser to lay the whole page
 * out again, every call; in `kartaan-click` a loop polling four times a second
 * did that over every element and froze Flipkart for minutes on a 26-order list.
 * This page polls the worker on a timer it owns, and it builds nodes rather than
 * sifting them. A check refuses the word `innerText` in this file and in
 * `panel.js`.
 */

import { MANUAL, TOOLTIPS } from './manual.js';
import {
  theNight, endTheNight, howTheNightWent, theDay, thatOneIsDone,
  A_DAYS_ALLOWANCE, spendsTheAllowance, whatNeedsYou,
} from './nightly.js';
import { THE_WALK } from './background.js';
import { aDriveToken } from './drive.js';
import { PAUSED, whatIsPaused } from './nightly.js';

/* ------------------------------------------------------------ what is stored
 *
 * **TWO RECORDS, AND NEITHER OF THEM IS THE NIGHT.** The night is `nightly.js`'s
 * and is rewritten by every step of a run; anything kept here that a run also
 * kept would be two records of one fact. What is here is what a run does NOT
 * know: what the seller told us once, and what became of the nights that have
 * already ended and been overwritten.
 */

/** What the seller set up once: their own panel name, and their Drive. **Not
 *  exported: `theSetup` below is the only way in, so nothing anywhere can read
 *  or write this record without going through the guards on it.** */
const THE_SETUP = 'kartaan-autosync-setup';

/** What became of the nights that have finished, one line per platform, and how
 *  many Flipkart requests went on each day.
 *
 *  **A LIMIT WRITTEN DOWN RATHER THAN BELIEVED AWAY: this count lives only in
 *  the seller's own browser.** Removing and re-adding the extension sets it back
 *  to nought, and Flipkart's twenty does not. Nothing here can fix that -- the
 *  platform is the only thing that really knows -- and it is recorded so nobody
 *  later reads this number as authoritative. */
export const THE_NIGHTS = 'kartaan-autosync-nights';

/* Which platforms this extension fetches for at all. **Amazon is not one of
 * them, and saying so is the point rather than an omission.** Amazon comes in
 * through its own door in the nightly Python, with the seller's own SP-API
 * credentials; no recipe here mentions it and no walk could fetch it. A panel
 * that showed Amazon as "not connected" would send a seller looking for a
 * setting that does not exist. */
export const THROUGH_THE_BROWSER = Object.freeze(['flipkart', 'meesho']);

/** What each platform is called on screen. Written here because the recipe file
 *  carries ids and a seller does not read ids. */
export const CALLED = Object.freeze({
  amazon: 'Amazon',
  flipkart: 'Flipkart',
  meesho: 'Meesho',
});

/* **THE DAY COMES FROM `nightly.js`, WHICH OWNS THE ALLOWANCE**, and is passed
 * straight back out so a check has one name for it. Written here as well it
 * would be two records of one fact, and the day one of them moved to a different
 * clock the seller's twenty would be counted against two different days. */
export { theDay };

/**
 * The day a night fetches when nobody says otherwise.
 *
 * **YESTERDAY, AND IT IS DECIDED RATHER THAN ASSUMED.** His instruction: certain
 * Flipkart and Meesho reports accept a date range, and where the panel offers one
 * and a range is given, that range is fetched; **where none is given, yesterday**.
 * The picker itself is deliberately NOT built in this round -- his words: *"at
 * this point I do not want you to get into too much of technicals, but I would
 * want you to first test if it is your code working. Once you have the working
 * code, then you can change all these things date and all."* This is the half of
 * that decision that exists today, written where the next session finds it.
 */
export function theDayToFetch(now = Date.now()) {
  return theDay(now - 24 * 60 * 60 * 1000);
}

/**
 * Why a day somebody named cannot be fetched, or '' when it can.
 *
 * **THE FIRST HALF OF THE DATE HE ASKED FOR, 2026-09-14** -- a run may name its
 * day, so a report can be proved on a day the platform has surely built. A real
 * calendar day, written `YYYY-MM-DD`, and no later than yesterday: today is not
 * finished, so no platform has built it.
 */
export function whyThatDayCannotBeFetched(day, now = Date.now()) {
  const said = String(day || '');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(said) || theDay(Date.parse(`${said}T12:00:00`)) !== said) {
    return `"${said}" is not a day. Write it as year-month-day, like 2026-09-01.`;
  }
  if (said > theDayToFetch(now)) {
    return `${said} is not over yet, so no platform has built it. Pick yesterday or earlier.`;
  }
  return '';
}

/* **HOW MANY DAYS ONE PRESS MAY FETCH (A53, 2026-09-16).** A range is walked a day at
 * a time, so a year in one press would be hundreds of visits to a seller's portal in
 * one go. A month is what Meesho's own orders export allows in one range
 * (`D:\rumee-auto-sync\DOCS.md:451, 1474`), so a month is what this takes at a time. */
export const AS_MANY_DAYS_AS_ONE_PRESS_TAKES = 31;

/** Every day from the first to the last, oldest first. */
export function theDaysBetween(from, to) {
  const days = [];
  for (let at = Date.parse(`${from}T12:00:00Z`); at <= Date.parse(`${to}T12:00:00Z`);
    at += 24 * 60 * 60 * 1000) {
    days.push(new Date(at).toISOString().slice(0, 10));
  }
  return days;
}

/** Why these two days cannot be fetched, or '' when they can. */
export function whyThatRangeCannotBeFetched(from, to, now = Date.now()) {
  const first = whyThatDayCannotBeFetched(from, now);
  if (first) return first;
  const last = whyThatDayCannotBeFetched(to, now);
  if (last) return last;
  if (String(from) > String(to)) {
    return `${from} is after ${to}. Put the earlier day in the first box.`;
  }
  const days = theDaysBetween(from, to);
  if (days.length > AS_MANY_DAYS_AS_ONE_PRESS_TAKES) {
    return `${from} to ${to} is ${days.length} days. This fetches up to `
      + `${AS_MANY_DAYS_AS_ONE_PRESS_TAKES} days at a time, so pick a shorter stretch and `
      + 'run it again for the rest.';
  }
  return '';
}

/**
 * What the seller has set up, read back rather than remembered.
 *
 * **THE PANEL NAME IS ASKED THE SAME QUESTION ON THE WAY OUT AS ON THE WAY IN,
 * and that is this repository's own rule about a boundary.** `land-the-file`
 * re-runs `whyTheseAreNotNames` on names that have already crossed once, saying
 * a boundary that asks nothing of what crosses it is not a boundary. This is the
 * same boundary: what comes back out of storage goes into an address the browser
 * is sent to, and storage is not proof that anything ever asked. A name that
 * does not pass reads as no name at all, so a Meesho run is refused in words
 * rather than walking a made-up address.
 */
export async function theSetup(chrome) {
  const held = await chrome.storage.local.get(THE_SETUP);
  const kept = held[THE_SETUP] || {};
  const panel = String(kept.panel || '');
  return {
    panel: whyThatIsNotAPanelName(panel) ? '' : panel,
    driveConnectedAt: Number(kept.driveConnectedAt) || 0,
    driveSaid: String(kept.driveSaid || ''),
    /* What the seller ticked for Run now, so the panel opens with the same ticks. */
    ticked: Array.isArray(kept.ticked) ? kept.ticked.map(String) : [],
    /* **WHAT HE UNTICKED, SO EVERY OTHER REPORT IS TICKED (A61, Job 5b, his "make it
     * like Rumee").** Only an untick is his choice; a report not listed here was never
     * unticked by him, so it opens ticked. Never written (null) = nothing unticked --
     * which is also how a save from before 5b reads, since it kept only the ticks. */
    unticked: Array.isArray(kept.unticked) ? kept.unticked.map(String) : null,
    /* **THE TIMED SYNC'S OWN LIST, KEPT APART FROM THE TICKS -- HIS DECISION B
     * (A60, 2026-09-21).** Never written yet means every report (`theTimedList`). */
    timed: Array.isArray(kept.timed) ? kept.timed.map(String) : null,
  };
}

/**
 * What the timed sync fetches: its own list, or every report that needs
 * downloading when none was ever kept. Never the Run now ticks: on 09-18..09-20
 * two ticked ad reports became the whole daily sync, and no Meesho ran.
 */
/* Put off by him (decision E): Flipkart offers keywords only for its latest day. */
const OFF_THE_TIMED_LIST = Object.freeze(['fk_keywords']);

export function theTimedList(book, setUp) {
  const every = (book.reports || [])
    .filter((one) => THROUGH_THE_BROWSER.includes(one.platform) && (book.recipes || {})[one.id]
      && !OFF_THE_TIMED_LIST.includes(one.id))
    .map((one) => one.id);
  return setUp.timed ? setUp.timed.filter((id) => every.includes(id)) : every;
}

/** Every report with a tick box of its own on the Run now panel (A61, Job 5b). */
function theTickableReports(book) {
  return (book.reports || [])
    .filter((one) => THROUGH_THE_BROWSER.includes(one.platform) && (book.recipes || {})[one.id])
    .map((one) => one.id);
}

async function keepTheSetup(chrome, changes) {
  const now = await theSetup(chrome);
  const kept = { ...now, ...changes };
  await chrome.storage.local.set({ [THE_SETUP]: kept });
  return kept;
}

/**
 * Why this is not a panel name, or nothing at all.
 *
 * **IT IS THE SELLER'S OWN AND IS NEVER IN THE PRODUCT** -- `walk.js` says so
 * where it refuses a Meesho step without one. It is the piece of a supplier
 * panel's address between `fulfillment/` and `/orders`, so it is asked for here
 * and asked something, rather than being pasted into a step unread.
 *
 * **THE SAME SHAPE OF QUESTION `whyTheseAreNotNames` ASKS OF A FILE NAME, not
 * the same question.** That one allows lower case only and bounds at 64; this
 * allows capitals and dashes, because a Meesho panel name really has them, and
 * bounds at 64 as well. Said as what it is rather than as parity it does not
 * have -- an independent reviewer caught this comment claiming the latter.
 *
 * **WHY IT IS ASKED AT ALL:** it goes into an address the browser is then sent
 * to. A slash would leave the seller's own panel for somewhere else entirely, a
 * `%2f` or a `..` would do it quietly, and a space would not survive the trip.
 */
export function whyThatIsNotAPanelName(said) {
  const name = String(said ?? '');
  if (!name) {
    return 'Meesho reports cannot be fetched without the name of your own supplier panel. '
      + 'It is the part of the address of your Meesho panel between "fulfillment/" and "/orders".';
  }
  if (name !== name.trim()) {
    return 'The panel name has a space at one end. Paste just the name itself.';
  }
  if (!/^[A-Za-z0-9_-]+$/.test(name)) {
    return `"${name}" is not a panel name: it may hold only letters, numbers, dashes and `
      + 'underscores. Copy it out of the address of your own Meesho panel.';
  }
  /* **AND IT IS BOUNDED.** Unbounded, a pasted essay becomes a multi-kilobyte
   * address the browser is then sent to. Found by an independent reviewer,
   * 2026-09-09, who also pointed out that the comment above claimed parity with
   * `whyTheseAreNotNames` -- which IS bounded -- and did not have it. */
  if (name.length > AS_LONG_AS_A_PANEL_NAME_GETS) {
    return `A panel name is at most ${AS_LONG_AS_A_PANEL_NAME_GETS} characters and this is `
      + `${name.length}. Copy just the name out of the address of your own Meesho panel.`;
  }
  return null;
}

/** How long a panel name may be. `whyTheseAreNotNames` bounds a file name at 64
 *  for the same reason and this matches it. */
export const AS_LONG_AS_A_PANEL_NAME_GETS = 64;

/* --------------------------------------------------- the nights already over
 *
 * **THE NIGHT'S OWN RECORD HOLDS ONE NIGHT AND IS OVERWRITTEN BY THE NEXT.** So
 * "Meesho has never run" -- the sentence he asked for by name, because nothing
 * today tells anybody -- cannot be answered from it: one Flipkart night wipes
 * out every trace that Meesho did or did not. This files a finished night under
 * its platform before that happens.
 *
 * **IT IS DONE BY NOTICING, NOT BY BEING TOLD.** Whoever finishes a night does
 * not have to remember to call this: it reads the night back, sees it has
 * finished, and files it if it has not been filed. Called twice, it does
 * nothing the second time. That is the same shape `carryTheNightOn` already
 * uses, and for the same reason -- a step that only happens if one particular
 * caller remembers it is a step that does not happen.
 */
export async function theNights(chrome) {
  const held = await chrome.storage.local.get(THE_NIGHTS);
  const kept = held[THE_NIGHTS] || {};
  return {
    byPlatform: kept.byPlatform || {},
    flipkartAskedOn: kept.flipkartAskedOn || {},
    filedNight: Number(kept.filedNight) || 0,
    loggedNight: Number(kept.loggedNight) || 0,
  };
}

/** Which platform a night belongs to, worked out from the reports in it.
 *
 *  **FROM THE RECIPE FILE, NEVER FROM THE SHAPE OF A NAME.** `autosync/recipes.py`
 *  already records what happens when a platform is worked out from a string:
 *  `platform[:2]` gave "fl" for Flipkart while every id begins `fk_`, and the
 *  answer that came back was the opposite of the truth. */
export function thePlatformOf(book, reportId) {
  const named = (book && book.fileNames && book.fileNames[reportId]) || null;
  if (named && named.platform) return named.platform;
  const declared = ((book && book.reports) || []).find((one) => one.id === reportId);
  return (declared && declared.platform) || '';
}

/** Which platform a whole night belongs to. One platform per night is already
 *  the rule -- one portal page is where every walk in it starts. */
export function thePlatformOfTheNight(book, night) {
  if (!night) return '';
  const every = [
    ...(night.done || []).map((one) => one.reportId),
    ...(night.doing ? [night.doing] : []),
    ...(night.left || []),
  ];
  for (const one of every) {
    const platform = thePlatformOf(book, one);
    if (platform) return platform;
  }
  return '';
}

/**
 * File a finished night under its platform, once.
 *
 * **THE FLIPKART REQUESTS ARE ADDED UP BY DAY HERE, and that is the only place
 * anything counts them across nights.** `nightly.js` counts what ONE night
 * spends, against what that night was allowed. Flipkart's allowance is twenty a
 * DAY -- so two nights of six each on one day is twelve of the seller's twenty,
 * and nothing anywhere knew that.
 */
export async function rememberTheNight(chrome, { book }) {
  const night = await theNight(chrome);
  if (!night || !night.finishedAt) return null;
  const kept = await theNights(chrome);
  if (kept.filedNight === night.startedAt) return null;
  /* **THE BOOK MAY BE FETCHED RATHER THAN HELD, and it is asked for only here.**
   * The worker calls this on every wake -- every two minutes, all night -- and
   * almost every one of those calls stops at one of the two lines above, so on
   * that path the recipe file is never read at all.
   *
   * **THE PANEL'S PATH IS DIFFERENT AND THIS COMMENT USED TO CLAIM OTHERWISE.**
   * `howItStands` genuinely needs the book on every poll, so `worker.js` holds
   * one for as long as the worker lives rather than reading 58 KB every two
   * seconds. Found by an independent reviewer, 2026-09-09: a reason that is not
   * true is worse than no reason. */
  const held = typeof book === 'function' ? await book() : book;
  const platform = thePlatformOfTheNight(held, night);
  const landed = (night.done || []).filter((one) => one.state === 'landed');
  const filed = {
    ...kept,
    filedNight: night.startedAt,
    byPlatform: {
      ...kept.byPlatform,
      ...(platform ? {
        [platform]: {
          startedAt: night.startedAt,
          finishedAt: night.finishedAt,
          reached: (night.done || []).length,
          landed: landed.length,
          failed: (night.done || []).filter((one) => one.state === 'failed').length,
          why: String(night.why || ''),
        },
      } : {}),
    },
    /* **EACH REQUEST GOES ON THE LEDGER FOR THE DAY IT WAS SPENT, and that is
     * the whole of the blocking finding of 2026-09-09.** The night stamps every
     * one as it spends it; this only adds them up. Filed as a single total under
     * the day the night STARTED, a run begun at five to midnight put today's
     * requests on yesterday's ledger and a second run today could then spend the
     * whole twenty again. */
    flipkartAskedOn: addUp(kept.flipkartAskedOn, whatItSpentByDay(night)),
  };
  await chrome.storage.local.set({ [THE_NIGHTS]: onlyRecentDays(filed) });
  return filed;
}

/**
 * Has THIS finished night's run log, its end-of-sync notice, and (for a
 * scheduled sync) the next platform already been carried through -- once?
 *
 * **A SEPARATE ONCE FROM `rememberTheNight`'S FILING, ON PURPOSE (Job 7, A64,
 * 2026-09-23).** `rememberTheNight`'s own doc says it is meant to be called by
 * anybody, any number of times, "done by noticing, not by being told" -- and
 * `howItStands` does exactly that on every panel poll, purely to keep the
 * panel's own numbers fresh, throwing away what it gets back. Until now
 * `worker.js` `carryOn` used THAT SAME "filed once" flag to decide whether to
 * write the run log, fire the end-of-sync notice, and start the next scheduled
 * platform. A panel poll landing in the same instant a walk finished could win
 * that race, file the night for the ledger, and leave `carryOn` believing its
 * own work was already done -- so the log (and the notice, and Meesho after
 * Flipkart) never happened, silently, with nothing in the console. **This is
 * why the 2026-09-17 sync that first added the January days left no run log
 * in Drive**: the ledger's one-shot was already spent by a poll before
 * `carryOn`'s own call to `rememberTheNight` ran. This flag belongs to
 * `carryOn` alone; nothing that is not `carryOn` may set it.
 */
export async function alreadyCarriedOn(chrome, night) {
  if (!night || !night.finishedAt) return true;
  const kept = await theNights(chrome);
  return kept.loggedNight === night.startedAt;
}

/** Mark this finished night's follow-through as done. See `alreadyCarriedOn`. */
export async function markCarriedOn(chrome, night) {
  if (!night || !night.finishedAt) return;
  const kept = await theNights(chrome);
  await chrome.storage.local.set({
    [THE_NIGHTS]: onlyRecentDays({ ...kept, loggedNight: night.startedAt }),
  });
}

/** What one night spent, day by day.
 *
 *  **A NIGHT WRITTEN BEFORE THE DAY STAMP EXISTED HAS ONLY A TOTAL**, and the
 *  honest thing to do with it is put it on the day it started -- which is what
 *  was done for every night up to now. Said out loud rather than left as an
 *  empty answer, which would quietly forget requests that really went. */
function whatItSpentByDay(night) {
  if (night.spentOn && Object.keys(night.spentOn).length) return night.spentOn;
  if (!night.spent) return {};
  return { [theDay(night.startedAt)]: night.spent };
}

function addUp(ledger, more) {
  const all = { ...ledger };
  for (const [day, many] of Object.entries(more)) {
    all[day] = (Number(all[day]) || 0) + (Number(many) || 0);
  }
  return all;
}

/** How many days of the ledger are kept. **Nothing here ever looked at a day but
 *  today, and a key per day for ever is a record that only grows.** Two weeks is
 *  enough for somebody to look back at a week and see what went. */
const KEEP_THE_LAST_DAYS = 14;

function onlyRecentDays(kept, now = Date.now()) {
  const oldest = theDay(now - KEEP_THE_LAST_DAYS * 24 * 60 * 60 * 1000);
  const days = {};
  for (const [day, many] of Object.entries(kept.flipkartAskedOn)) {
    if (day >= oldest) days[day] = many;
  }
  return { ...kept, flipkartAskedOn: days };
}

/**
 * How many of the seller's twenty Flipkart requests have gone today.
 *
 * **THE NIGHT THAT IS STILL GOING COUNTS TOWARDS IT**, or the number is right
 * only between runs, which is the one time nobody is looking at it.
 */
export function askedForToday(kept, night, now = Date.now()) {
  const today = theDay(now);
  let gone = Number(kept.flipkartAskedOn[today]) || 0;
  /* **THE NIGHT NOT YET FILED IS COUNTED FROM ITS OWN DAY STAMPS, not from its
   * total.** A night begun at five to midnight and still walking at five past
   * has spent requests on two days, and only the ones spent TODAY belong in
   * today's number. */
  const filed = Boolean(night) && kept.filedNight === night.startedAt;
  if (night && !filed) {
    gone += Number(whatItSpentByDay(night)[today]) || 0;
  }
  return gone;
}

/* ------------------------------------------------------- starting and stopping */

/**
 * Where a night's walks start from.
 *
 * **TAKEN OUT OF THE RECIPE, NEVER TYPED HERE.** Which portal page a report
 * begins at is the recipe's business -- `nightly.js` says so where it refuses a
 * night with no starting page, and this file must not learn a platform. So this
 * takes the address of the first step that has one, whole.
 *
 * **IT USED TO KEEP ONLY THE ORIGIN, AND THAT IS WHAT KILLED THE NIGHT OF
 * 2026-09-09 ON HIS OWN PANEL.** Cut back to `https://supplier.meesho.com`, the
 * address is not the seller's panel at all -- it is Meesho's PUBLIC MARKETING
 * SITE, the one page in the whole product the signed-out detector exists to
 * reject. `me_catalog` opened there and stopped the entire night with "the panel
 * is asking to be signed in to", while his Meesho tab sat signed in beside it.
 * The evidence is the page it captured: "Sell Online ... Pricing & Commission
 * ... Login ... Start Selling" -- six of the nine signs at once. **The detector
 * was right. The address it was pointed at was ours.**
 *
 * **AND THE ORIGIN WAS NEVER NEEDED.** Every recipe's first step is a `go` to
 * the page it actually wants, so the origin was one extra navigation whose only
 * job was to put the content script into a page -- which the recipe's own
 * address does just as well, on a page the seller is signed in to. `goTo`
 * already forces a reload when the address it is given is the same page it is
 * already on -- `sameDocumentAs` compares the part before the `#`, so an
 * identical address counts -- and the walk's own first step still hands the page
 * over exactly as before.
 *
 * **THE PANEL NAME IS FILLED HERE, NOT SHIPPED.** `{panel}` is the seller's own
 * (D27, D30, D92) and reaches this from storage at the moment a run starts, the
 * same way `walk.js` fills it into every step.
 */
export function whereToStartFrom(book, reportIds, panel = '') {
  for (const reportId of reportIds) {
    const recipe = (book.recipes || {})[reportId];
    if (!recipe) continue;
    for (const step of [...(recipe.toAsk || []), ...(recipe.toTake || [])]) {
      if (!step.address) continue;
      const address = String(step.address);
      /* **AN ADDRESS WITH A HOLE IN IT IS NOWHERE, NOT A PAGE, and that is the
       * same lesson the origin was.** Filled with no panel name the Meesho
       * address becomes `.../fulfillment//orders/`, which Meesho does not know
       * -- and `recipes.py` records, measured live, that Meesho answers any
       * address it does not know with the very marketing site this whole change
       * exists to stop a night opening at. `whyItCannotBeStarted` already
       * refuses a Meesho run with no panel name before it ever reaches here;
       * this makes the answer honest on its own rather than depending on a
       * caller having asked first. */
      if (address.includes('{panel}') && !panel) return '';
      return address.split('{panel}').join(panel);
    }
  }
  return '';
}

/**
 * Why a night of these reports cannot be started, or nothing at all.
 *
 * **REFUSED BEFORE ANYTHING IS SPENT, and every one of these was reachable.** A
 * night that starts and then cannot walk is not free: `nightly.js` spends a
 * Flipkart request BEFORE each walk, so a night that was going to fail anyway
 * fails having spent some of the seller's twenty.
 */
/**
 * The reports in the order a sync walks them: the ones that must be requested
 * first, then the rest -- Rumee's order (`D:\rumee-auto-sync\config.js:62-64`), so
 * the platform builds them while the others are fetched (A53, 2026-09-16).
 */
export function askingFirst(book, reportIds) {
  const asks = (id) => Boolean((((book.recipes || {})[id] || {}).toAsk || []).length);
  /* **AND A REPORT THAT READS ANOTHER'S FILE COMES AFTER IT (A53, the live sync of
   * 2026-09-16).** `fk_ads_overall` needs the campaigns out of `fk_ads_daily`'s file and
   * ran before it, so it said "which campaigns ran is not known yet" and fetched nothing. */
  const readsAnother = (id) => String((((book.recipes || {})[id] || {}).campaignsFrom || {}).report || '');
  const inOrder = [...reportIds.filter(asks), ...reportIds.filter((id) => !asks(id))];
  const later = inOrder.filter((id) => readsAnother(id) && inOrder.includes(readsAnother(id)));
  return [...inOrder.filter((id) => !later.includes(id)), ...later];
}

/**
 * The reports with every list one of them reads put in front of it (A57, Job 2).
 *
 * `fk_ads_overall` ticked alone never had `fk_ads_daily` fetched, so each day was
 * "not known yet" (09-18..09-21). Rumee always ran the daily file first
 * (`D:/rumee-auto-sync/content/flipkart.js:1524-1546`).
 */
export function withTheListsTheyRead(book, reportIds) {
  const readsFrom = (id) => String((((book.recipes || {})[id] || {}).campaignsFrom || {}).report || '');
  const all = [];
  for (const id of reportIds) {
    const list = readsFrom(id);
    if (list && (book.recipes || {})[list] && !all.includes(list)) all.push(list);
    if (!all.includes(id)) all.push(id);
  }
  return all;
}

/** Which report reads which one's list, for the night (A57, Job 2). */
export function theListsRead(book, reportIds) {
  const listFrom = {};
  for (const id of reportIds) {
    const list = String((((book.recipes || {})[id] || {}).campaignsFrom || {}).report || '');
    if (list && reportIds.includes(list)) listFrom[id] = list;
  }
  return listFrom;
}

export function whyItCannotBeStarted(book, { reportIds, panel, night }) {
  if (night && !night.finishedAt) {
    return 'A run is already going. Stop it first, or wait for it to finish.';
  }
  if (!reportIds || !reportIds.length) {
    return 'Nothing is ticked, so there is nothing to fetch.';
  }
  const platforms = [...new Set(reportIds.map((one) => thePlatformOf(book, one)))];
  if (platforms.length > 1) {
    return `These reports are from ${platforms.map((one) => CALLED[one] || one).join(' and ')}, `
      + 'and one run walks one website. Press Run now on the panel: it runs each website\'s '
      + 'reports one after another.';
  }
  const missing = reportIds.filter((one) => !(book.recipes || {})[one]);
  if (missing.length) {
    return `${missing.join(', ')} cannot be fetched by this extension at all. `
      + 'See "What this cannot fetch" below.';
  }
  const needsThePanel = reportIds.some(
    (one) => stepsMention(book, one, '{panel}'),
  );
  if (needsThePanel && !panel) {
    return whyThatIsNotAPanelName('');
  }
  if (!whereToStartFrom(book, reportIds, panel)) {
    return 'None of these reports says which portal page it starts at, so there is nowhere '
      + 'to begin.';
  }
  return null;
}

/** Does any step of this recipe carry that placeholder? */
function stepsMention(book, reportId, what) {
  const recipe = (book.recipes || {})[reportId];
  if (!recipe) return false;
  return [...(recipe.toAsk || []), ...(recipe.toTake || [])].some(
    (step) => String(step.address || '').includes(what)
      || String((step.find && step.find.near) || '').includes(what),
  );
}

/**
 * How many Flipkart requests this run may spend.
 *
 * **WHAT IS LEFT OF THE DAY'S TWENTY, NEVER A NUMBER TYPED INTO A RUN.** Until
 * now nothing decided `mayAskFor` at all, so every night started with the safe
 * default of nought and every Flipkart report in it was skipped by name -- which
 * is correct and useless, and is exactly the shape of "it never fetched
 * anything".
 */
export function howManyItMaySpend(book, { reportIds, kept, night, now = Date.now() }) {
  const spending = reportIds.filter((one) => spendsTheAllowance(one)).length;
  if (!spending) return 0;
  const left = A_DAYS_ALLOWANCE - askedForToday(kept, night, now);
  return Math.max(0, Math.min(spending, left));
}

/* --------------------------------------------------------- what the panel sees */

/**
 * Everything the page draws, in one answer.
 *
 * **ONE MESSAGE, NOT SEVEN.** The page polls this on a timer it owns; seven
 * messages on that timer is seven wakes of a worker Chrome shuts down after
 * thirty seconds of quiet.
 */
export async function howItStands(chrome, { book, now = Date.now(), theClock = null } = {}) {
  await rememberTheNight(chrome, { book });
  const night = await theNight(chrome);
  const held = await chrome.storage.local.get(THE_WALK);
  const walk = held[THE_WALK] || null;
  const setUp = await theSetup(chrome);
  const kept = await theNights(chrome);
  const gone = askedForToday(kept, night, now);

  const byReport = {};
  for (const one of (night && night.done) || []) {
    byReport[one.reportId] = { state: one.state, say: one.say || '', size: one.size || 0 };
  }
  if (night && night.doing) byReport[night.doing] = { state: 'fetching', say: '', size: 0 };
  for (const one of (night && night.left) || []) {
    if (!byReport[one]) byReport[one] = { state: 'waiting', say: '', size: 0 };
  }

  const declared = book.reports || [];
  /* **A REPORT FETCHED BY ANOTHER REPORT'S RUN IS NOT ONE THIS DOOR CANNOT
   * FETCH.** The Meesho ads sweep asks for a campaign's day once and writes all
   * three files from the one answer, so two real reports have no recipe of their
   * own. **Listed as unfetchable, a seller would be told "cannot be fetched"
   * about two files that arrive in their Drive every night** -- which is worse
   * than saying nothing at all. */
  const fetchedByAnother = book.madeByAnother || {};
  const cannot = declared
    .filter((one) => THROUGH_THE_BROWSER.includes(one.platform)
      && !(book.recipes || {})[one.id] && !fetchedByAnother[one.id])
    .map((one) => ({
      id: one.id,
      name: one.name,
      platform: one.platform,
      why: (book.notYetARecipe || {})[one.id]
        || 'This report is declared and this door has no steps for it. No reason is written down, '
        + 'which is itself worth knowing.',
    }));

  return {
    setUp: {
      panel: setUp.panel,
      driveConnectedAt: setUp.driveConnectedAt,
      driveSaid: setUp.driveSaid,
      ticked: theTickableReports(book).filter((id) => !(setUp.unticked || []).includes(id)),
      /* **BOTH, OR NOTHING WORKS AND THE PANEL DOES NOT SAY WHICH.** Without the
       * Drive nothing that is fetched is ever put anywhere; without the panel
       * name no Meesho report can be walked at all. */
      done: Boolean(setUp.driveConnectedAt) && Boolean(setUp.panel),
    },
    night: night ? {
      startedAt: night.startedAt,
      finishedAt: night.finishedAt,
      doing: night.doing || null,
      left: [...(night.left || [])],
      done: (night.done || []).map((one) => ({ ...one })),
      spent: night.spent || 0,
      mayAskFor: night.mayAskFor || 0,
      why: night.why || '',
      platform: thePlatformOfTheNight(book, night),
    } : null,
    walk: walk && !walk.answer ? { reportId: walk.reportId || '', at: walk.at || 0 } : null,
    /* **THE WORDS, THE SAME WORDS THE NIGHT ITSELF WRITES.** "Open the log" on
     * the reference opens a page of its own; here it is a section on this one,
     * because his instruction on the three backfill pages the reference grew was
     * one page, one place. */
    inWords: howTheNightWent(night),
    /* **EVERY DAY GIVEN UP ON, KEPT ACROSS NIGHTS** until a later run fetches it,
     * so the banner can name it however many runs have happened since. */
    needsYou: await whatNeedsYou(chrome),
    paused: await whatIsPaused(chrome),
    platforms: [
      ...THROUGH_THE_BROWSER.map((platform) => ({
        id: platform,
        name: CALLED[platform] || platform,
        throughTheBrowser: true,
        /* Meesho cannot be walked at all without the seller's own panel name;
         * Flipkart needs nothing set up. Both need the Drive, or what is fetched
         * goes nowhere. */
        ready: Boolean(setUp.driveConnectedAt)
          && (platform !== 'meesho' || Boolean(setUp.panel)),
        lastRun: kept.byPlatform[platform] || null,
      })),
      {
        id: 'amazon',
        name: CALLED.amazon,
        throughTheBrowser: false,
        ready: null,
        lastRun: null,
      },
    ],
    flipkart: {
      allowedADay: A_DAYS_ALLOWANCE,
      askedForToday: gone,
      leftToday: Math.max(0, A_DAYS_ALLOWANCE - gone),
    },
    reports: declared
      .filter((one) => THROUGH_THE_BROWSER.includes(one.platform))
      .map((one) => ({
        id: one.id,
        name: one.name,
        platform: one.platform,
        canBeFetched: Boolean((book.recipes || {})[one.id] || fetchedByAnother[one.id]),
        /* **AND WHICH RUN BRINGS IT, said rather than left to be guessed.** A
         * seller ticking it on its own would be ticking nothing. */
        fetchedBy: fetchedByAnother[one.id] || '',
        /* The report whose tick it shows (A61, Job 5b). */
        broughtBy: (book.broughtBy || {})[one.id] || '',
        spends: spendsTheAllowance(one.id),
        ...(byReport[one.id] || { state: '', say: '', size: 0 }),
      })),
    cannotBeFetched: cannot,
    timed: whatTheTimedSyncFetches(book, theTimedList(book, setUp)),
    theDayItWouldFetch: theDayToFetch(now),
    /* **WHEN IT NEXT WAKES BY ITSELF, AND NOTHING ANYWHERE COULD SAY (A53,
     * 2026-09-16).** The scheduled sync did not start at the hour he had just
     * saved, and there was no way to tell whether the hour had been saved, whether
     * the alarm existed, or when it would next come round -- so a seller whose
     * daily sync has quietly moved to tomorrow reads exactly the same page as one
     * whose sync is minutes away. The clock is the one setting in this product
     * that runs when nobody is watching; it has to say so out loud. */
    clock: typeof theClock === 'function' ? await theClock() : null,
  };
}

/** The timed list counted, and said the way the panel shows it (A60, Job 5). */
function whatTheTimedSyncFetches(book, timed) {
  const flipkart = timed.filter((id) => thePlatformOf(book, id) === 'flipkart').length;
  const meesho = timed.filter((id) => thePlatformOf(book, id) === 'meesho').length;
  return {
    flipkart,
    meesho,
    said: `The timed sync will fetch: ${timed.length} reports `
      + `(Flipkart ${flipkart}, Meesho ${meesho})`,
  };
}

/* ------------------------------------------------ what the page asks the worker
 *
 * **THE PANEL'S OWN MESSAGES, KEPT APART FROM THE CONTENT SCRIPT'S.** They are
 * answered by their own listener in `background.js`, which asks a question the
 * content script's listener cannot ask: that the message came from THIS
 * extension's own `panel.html`. The page half's listener requires a tab behind
 * the message instead, which is right for it and is not a thing this page should
 * depend on.
 */

/** What the panel may ask for. Written once, so refusing an unknown message and
 *  carrying out a known one cannot disagree about which is which. */
export const THE_PANEL_ASKS = Object.freeze([
  'how-it-stands', 'connect-the-drive', 'check-the-drive', 'save-the-panel-name',
  'run-now', 'stop', 'set-the-hour', 'reload-the-extension', 'save-the-ticks', 'resume',
]);

/**
 * Answer one thing the panel asked.
 *
 * `parts` are handed in -- the recipe book, the clock, the way a night is
 * started and the download watch -- so the whole of this can be checked with no
 * browser, the same way everything else in this extension takes them.
 */
export async function answerThePanelsQuestion(chrome, parts, asked) {
  const { book, now = () => Date.now() } = parts;

  if (asked.do === 'how-it-stands') {
    return { stands: await howItStands(chrome, { book, now: now(), theClock: parts.theClock }) };
  }

  if (asked.do === 'check-the-drive') {
    /* **QUIETLY, AND ONCE WHEN THE PAGE OPENS.** Asked on every poll this would
     * be a Google call every two seconds; asked interactively it would put an
     * account chooser in front of somebody who did not press anything. */
    try {
      await aDriveToken(chrome, { interactive: false, now });
      const kept = await keepTheSetup(chrome, { driveConnectedAt: now(), driveSaid: '' });
      return { connected: true, at: kept.driveConnectedAt };
    } catch (wrong) {
      return { connected: false, said: (wrong && wrong.message) || String(wrong) };
    }
  }

  if (asked.do === 'connect-the-drive') {
    /* **THE ONE INTERACTIVE ASK IN THE WHOLE EXTENSION**, and this is the screen
     * `worker.js` said stood in for. Every other ask is quiet on purpose,
     * because a night runs with nobody watching and an account chooser at two in
     * the morning waits for ever -- **but a permission that has never been
     * granted cannot be had quietly at all**, so without somebody pressing this
     * once the run says "the seller's Drive is not connected" every night, for
     * ever, correctly and uselessly. */
    try {
      await aDriveToken(chrome, { interactive: true, now });
      const kept = await keepTheSetup(chrome, { driveConnectedAt: now(), driveSaid: '' });
      return { connected: true, at: kept.driveConnectedAt };
    } catch (wrong) {
      const said = (wrong && wrong.message) || String(wrong);
      await keepTheSetup(chrome, { driveSaid: said });
      return { connected: false, said };
    }
  }

  if (asked.do === 'save-the-panel-name') {
    const wrong = whyThatIsNotAPanelName(asked.panel);
    if (wrong) return { wrong };
    await keepTheSetup(chrome, { panel: String(asked.panel) });
    return { saved: true };
  }

  if (asked.do === 'save-the-ticks') {
    const reportIds = [...new Set((asked.reportIds || []).map(String))];
    const unknown = reportIds.filter((id) => !(book.recipes || {})[id]);
    if (unknown.length) return { wrong: `${unknown.join(', ')} is not a report this can fetch.` };
    const unticked = theTickableReports(book).filter((id) => !reportIds.includes(id));
    await keepTheSetup(chrome, { ticked: reportIds, unticked });
    return { saved: true };
  }

  if (asked.do === 'set-the-hour') {
    const wrong = parts.whyThatIsNotATimeOfDay(asked.at);
    if (wrong) return { wrong };
    const set = await parts.setTheHour(chrome, { at: asked.at, now });
    return { at: set };
  }

  if (asked.do === 'stop') {
    /* **WHETHER ANYTHING WAS ACTUALLY GOING IS ASKED FIRST.** `endTheNight`
     * writes over whatever night is there, so asked afterwards it says "yes,
     * stopped" for a night that finished by itself yesterday -- and a seller
     * pressing Stop on an idle panel would be told they had stopped a run. */
    const going = await theNight(chrome);
    const wasGoing = Boolean(going && !going.finishedAt);
    /* **THE REPORT THAT WAS BEING FETCHED IS WRITTEN DOWN AS STOPPED, and until
     * an independent reviewer found this it was not.** `endTheNight` leaves
     * `doing` exactly as it was, so the panel went on saying that report was
     * "fetching now" for ever while the banner said the run had finished -- and
     * the report appeared in neither list, so the platform card under-reported
     * by one. **For a product built against "a report missing with nothing
     * saying why", that is the same silence in miniature.** */
    if (wasGoing && going.doing) {
      await thatOneIsDone(chrome, {
        reportId: going.doing,
        state: 'stopped',
        say: 'Stopped from the panel while it was being fetched.',
        at: now(),
      });
    }
    /* **THE NIGHT IS ENDED BEFORE THE WALK IS, and that ordering is the whole of
     * it.** Nothing here WAKES `carryTheNightOn` -- the alarm that fires every
     * two minutes calls it, and so does a page saying `walk-done`. Either of
     * them, arriving in the gap, reads a night that has not finished and a walk
     * that is over, and starts the NEXT report. So pressing Stop would start
     * something. Ended first, both stop at `if (!night || night.finishedAt)`.
     * (The reason, corrected by an independent reviewer; the ordering it defends
     * was right either way.) */
    await endTheNight(chrome, {
      at: now(),
      why: 'Stopped from the panel.',
    });
    const held = await chrome.storage.local.get(THE_WALK);
    const walk = held[THE_WALK] || null;
    await chrome.storage.local.remove(THE_WALK);
    /* **AND THE ARMED DOWNLOAD-CANCEL IS PUT AWAY.** Left armed it stays so for
     * a quarter of an hour, and the next file the seller downloaded by hand
     * would vanish in front of them. */
    if (parts.watching) parts.watching.stopExpecting();
    if (walk && walk.tabId !== undefined && chrome.tabs && chrome.tabs.remove) {
      try {
        await chrome.tabs.remove(walk.tabId);
      } catch (wrong) {
        /* A tab that has already gone is the ordinary case, not a failure: the
         * seller closing it is one of the ways a walk ends. */
      }
    }
    return { stopped: wasGoing, was: (walk && walk.reportId) || '' };
  }

  if (asked.do === 'reload-the-extension') {
    /* **THE EXTENSION RELOADS ITSELF, SO A FIX CAN BE PROVED WITH NOBODY AT THE
     * KEYBOARD (A53, 2026-09-15, his "do not depend on me").** Never while a night
     * or a walk is going: a reload in the middle drops the report on the floor. */
    const night = await theNight(chrome);
    const walk = (await chrome.storage.local.get(THE_WALK))[THE_WALK];
    if ((night && !night.finishedAt) || (walk && !walk.answer)) {
      return { wrong: 'A run is going, so the extension was not reloaded.' };
    }
    const later = parts.later || ((fn) => setTimeout(fn, 500));
    later(() => chrome.runtime.reload());
    return { reloading: true };
  }

  if (asked.do === 'run-now') {
    /* **THE DATE BOXES COME ACROSS (A53).** Until this line only `day` was passed
     * on, so a seller who typed a range in the boxes got yesterday instead --
     * silently, under the right report's name. */
    const how = { day: asked.day, from: asked.from, to: asked.to };
    /* **BOTH WEBSITES TICKED RUN ONE AFTER ANOTHER, FLIPKART FIRST (A61, Job 5b, his
     * "make it like Rumee"; `D:/rumee-auto-sync/background.js:191-209`)** -- the same
     * queue the timed sync uses. Every part is asked first, so a Meesho part that
     * cannot start never lets Flipkart spend its requests. */
    const byPlatform = PLATFORM_ORDER
      .map((platform) => [...new Set(asked.reportIds || [])]
        .filter((id) => thePlatformOf(book, id) === platform))
      .filter((ids) => ids.length);
    if (byPlatform.length < 2) return startASync(chrome, parts, { reportIds: asked.reportIds, ...how });
    const setUp = await theSetup(chrome);
    const night = await theNight(chrome);
    for (const ids of byPlatform) {
      const wrong = whyItCannotBeStarted(book, {
        reportIds: withTheListsTheyRead(book, ids), panel: setUp.panel, night,
      });
      if (wrong) {
        return { wrong: `${CALLED[thePlatformOf(book, ids[0])]}: ${wrong} Nothing was started.` };
      }
    }
    await chrome.storage.local.set({
      [THE_QUEUE]: byPlatform.map((reportIds) => ({ reportIds, ...how })),
    });
    const said = await startTheNextPlatform(chrome, parts);
    if (said.started) return { started: said.started };
    return { wrong: said.refused.map((one) => one.wrong).filter(Boolean)[0] || 'Nothing was started.' };
  }

  if (asked.do === 'resume') {
    /* **CARRIES ON FROM THE REPORT THAT MET THE SIGN-IN -- RUMEE'S RESUME SYNC
     * (`D:\rumee-auto-sync\background.js:712-726`).** */
    const paused = await whatIsPaused(chrome);
    if (!paused) return { wrong: 'Nothing is paused, so there is nothing to resume.' };
    const said = await startASync(chrome, parts, { reportIds: paused.reportIds, day: paused.dataDate });
    if (said && said.started) await chrome.storage.local.remove(PAUSED);
    return said;
  }

  return { wrong: `The panel asked for "${asked.do}", which is not something it may ask for.` };
}

/** The platforms still to run in the scheduled sync, each as its ticked reports. */
export const THE_QUEUE = 'kartaan-autosync-scheduled-queue';
/* **FLIPKART FIRST**, so its requests are made at the start of the scheduled sync --
 * Rumee's order (`D:\rumee-auto-sync\config.js:62-64`). */
export const PLATFORM_ORDER = Object.freeze(['flipkart', 'meesho']);

/**
 * Start the scheduled sync: its own list, one platform after another.
 *
 * **CONTROL'S RULING FOR A53 (`D:\Control\JOBS.md`)**, with the list replaced by his
 * decision B (A60): the timed list (`theTimedList`), plus the days already owed (the
 * sync adds those itself); one sync, one platform at a time, never side by side; a
 * platform that is signed out stops only itself.
 */
export async function startTheScheduledSync(chrome, parts) {
  const { book } = parts;
  const timed = theTimedList(book, await theSetup(chrome));
  const byPlatform = PLATFORM_ORDER
    .map((platform) => timed.filter(
      (id) => (book.recipes || {})[id] && thePlatformOf(book, id) === platform,
    ))
    .filter((ids) => ids.length);
  await chrome.storage.local.set({ [THE_QUEUE]: byPlatform });
  return startTheNextPlatform(chrome, parts);
}

/** Start the next platform of the scheduled sync, if any is left. A sync already
 *  going keeps the queue, and the next platform starts when that one ends. */
export async function startTheNextPlatform(chrome, parts) {
  const left = [...((await chrome.storage.local.get(THE_QUEUE))[THE_QUEUE] || [])];
  const refused = [];
  while (left.length) {
    /* A Run now entry carries its days (A61, Job 5b); a timed one is the ids alone. */
    const entry = left.shift();
    const { reportIds, ...how } = Array.isArray(entry) ? { reportIds: entry } : entry;
    // eslint-disable-next-line no-await-in-loop
    const night = await theNight(chrome);
    if (night && !night.finishedAt) return { started: null, waiting: true, refused };
    // eslint-disable-next-line no-await-in-loop
    await chrome.storage.local.set({ [THE_QUEUE]: left });
    // eslint-disable-next-line no-await-in-loop
    const said = await startASync(chrome, parts, { reportIds, ...how });
    if (said && said.started) return { started: reportIds, refused };
    refused.push({ reportIds, wrong: (said && said.wrong) || '' });
  }
  return { started: null, refused };
}

/**
 * Start a sync of these reports, for this day or yesterday.
 *
 * **ONE WAY IN FOR RUN NOW, THE HOURLY RE-CHECK AND THE SCHEDULED SYNC (A53)**, so
 * the three can never start a sync three different ways.
 */
export async function startASync(chrome, parts, asked) {
  const { book, now = () => Date.now() } = parts;
  {
    const reportIds = withTheListsTheyRead(book, [...new Set(asked.reportIds || [])]);
    const setUp = await theSetup(chrome);
    const night = await theNight(chrome);
    const wrong = whyItCannotBeStarted(book, { reportIds, panel: setUp.panel, night });
    if (wrong) return { wrong };
    /* **ONE DAY OR A STRETCH OF THEM (A53, his "add the box to input date range").**
     * Nothing in the boxes is yesterday, as it has always been. */
    const from = String(asked.from || '');
    const to = String(asked.to || asked.day || '');
    let days = [];
    if (from && to) {
      const rangeWrong = whyThatRangeCannotBeFetched(from, to, now());
      if (rangeWrong) return { wrong: rangeWrong };
      days = theDaysBetween(from, to);
    } else if (from || to) {
      const one = to || from;
      const dayWrong = whyThatDayCannotBeFetched(one, now());
      if (dayWrong) return { wrong: dayWrong };
      days = [one];
    }
    if (!setUp.driveConnectedAt) {
      return {
        wrong: 'Your Google Drive is not connected yet, so anything fetched would have nowhere '
          + 'to go. Connect it first.',
      };
    }
    const kept = await theNights(chrome);
    const started = await parts.startTheNight(chrome, {
      doing: askingFirst(book, reportIds),
      listFrom: theListsRead(book, reportIds),
      mayAskFor: howManyItMaySpend(book, { reportIds, kept, night, now: now() }),
      at: now(),
      openAt: whereToStartFrom(book, reportIds, setUp.panel),
      dataDate: days.length ? days[days.length - 1] : theDayToFetch(now()),
      /* **THE NEWEST DAY THERE IS TO FETCH**, so the sync can tell a day the seller
       * typed from the ordinary one and leave out the reports that only exist for
       * now (his ruling, 2026-09-16). */
      latestDay: theDayToFetch(now()),
      /* **EVERY DAY THIS SYNC IS FOR**, walked oldest first by each report. */
      days,
      /* **THE NAME THIS PAGE ASKED FOR GOES WITH THE NIGHT IT STARTS, and until
       * this line the only thing joining them was one line of wiring no check
       * could reach.** The guard a few lines above already refuses a Meesho run
       * without it, and `theSetup` asks the same question again on the way out
       * of storage -- so what is handed over here has been asked twice. */
      panel: setUp.panel,
      /* **THE REPORTS THAT CAN BE FETCHED FOR A PAST DAY (A53)** -- those with no
       * reason written for why they cannot be asked for again. */
      canGoBack: reportIds.filter((id) => ((book.reports || []).find((one) => one.id === id) || {})
        .cannotBeAskedForAgain === null),
    });
    await parts.carryOn();
    return { started: (started && started.left) || [] };
  }
}

/* ============================================================================
 *                            AND WHAT THE PAGE DRAWS
 * ==========================================================================*/

/* Every class on this page. **Written once here rather than typed into markup
 * and again into the file that styles it**, which is the two-records-of-one-fact
 * fault by its smallest shape. `k-` classes are the ERP's own, copied byte for
 * byte into `extension/from-the-erp/` and pinned there by a check. */
const OURS = 'p-';

function make(tag, className = '', text = '') {
  const node = document.createElement(tag);
  if (className) node.className = className;
  /* **`textContent`, NEVER `innerText`.** See the top of this file: reading
   * `innerText` lays the whole page out again, and writing anything at all is
   * cheaper on `textContent`. */
  if (text) node.textContent = text;
  return node;
}

function put(into, ...nodes) {
  /* `append`, not `appendChild`. Both are real; `append` takes several at once,
   * which is what every call here does. */
  into.append(...nodes);
  return into;
}

/** A day and a time, in the seller's own words rather than a number. */
export function inWordsWhen(at) {
  if (!at) return 'never';
  const when = new Date(at);
  const two = (n) => String(n).padStart(2, '0');
  return `${theDay(at)} at ${two(when.getHours())}:${two(when.getMinutes())}`;
}

/** What one report's state is called on screen. */
export function whatThatStateIsCalled(state) {
  return ({
    landed: 'fetched',
    failed: 'failed',
    fetching: 'fetching now',
    waiting: 'waiting',
    'nothing-to-fetch': 'skipped',
    /* **HIS RULING, 2026-09-14.** A day the platform has not built is not a
     * failure; one still not built on the third day is the seller's to fetch. */
    'not-available-yet': 'not available yet',
    'needs-you': 'needs you',
    stopped: 'stopped',
    'needs-signing-in': 'sign in first',
  })[state] || 'not run yet';
}

/**
 * What the banner across the top says.
 *
 * **THE STATE A SELLER SEES FIRST IS THE ONE NOTHING HAS EVER RUN IN, and it
 * must not look like a fault.** This extension has never fetched anything.
 */
/** What the notification says when a sync pauses for a sign-in (A53, Rumee's
 *  "Login Required" notification, `D:\rumee-auto-sync\background.js:1018-1019`). */
export function theSignInAlert(book, paused) {
  if (!paused || !paused.reportIds || !paused.reportIds.length) return null;
  const platform = thePlatformOf(book, paused.reportIds[0]);
  const name = CALLED[platform] || platform;
  /* **WHAT THE SELLER STILL HAS TO DO, PLATFORM BY PLATFORM (his ruling,
   * 2026-09-16).** Flipkart signs in in three steps -- the address, the password,
   * then a one-time code sent to him -- and nothing in this extension can know
   * that code. Told "sign in", he does not know a code is waiting; told this, he
   * does. */
  const alsoACode = platform === 'flipkart'
    ? ' Flipkart also sends you a one-time code, and only you can type that.'
    : '';
  return {
    title: `Kartaan AutoSync: sign in to ${name}`,
    message: `The sync stopped because ${name} asked you to sign in.${alsoACode} Sign in, then `
      + 'open Kartaan AutoSync and press Resume. It carries on from the report it stopped at.',
  };
}

/** What the notification says when a sync ends -- Rumee's "Sync Complete": how many
 *  landed, each failure with its reason (`D:\rumee-auto-sync\background.js:1133-1146`),
 *  and any day now left for the seller to fetch by hand (A53). */
export function theSyncSummary(night) {
  if (!night || !night.finishedAt) return null;
  const done = night.done || [];
  const landed = done.filter((one) => one.state === 'landed').length;
  const failed = done.filter((one) => one.state === 'failed');
  const needsYou = done.filter((one) => one.state === 'needs-you');
  const failures = failed.length
    ? `: ${failed.map((one) => `${one.reportId} (${String(one.say || '').slice(0, 60)})`).join(', ')}`
    : '';
  const byHand = needsYou.length
    ? ` ${needsYou.map((one) => `${one.reportId} for ${one.dataDate}`).join(', ')} `
      + `${needsYou.length === 1 ? 'needs' : 'need'} you: fetch by hand.`
    : '';
  return {
    title: failed.length || needsYou.length
      ? 'Kartaan AutoSync: sync finished with problems' : 'Kartaan AutoSync: sync finished',
    message: `${landed} landed, ${failed.length} failed${failures}.${byHand}`,
  };
}

export function whatTheBannerSays(stands) {
  if (!stands.setUp.done) {
    return { how: 'setup', said: 'Two things to set up, once. Nothing runs until they are done.' };
  }
  if (stands.night && !stands.night.finishedAt) {
    const doing = stands.night.doing;
    return {
      how: 'running',
      said: doing
        ? `Fetching ${doing}. ${stands.night.left.length} still to go.`
        : `A run is going. ${stands.night.left.length} still to go.`,
    };
  }
  /* **SIGN IN NEEDED COMES FIRST OF EVERYTHING ELSE (A53, his ruling).** */
  if (stands.paused) {
    return {
      how: 'wrong',
      said: `Sign in needed: the sync stopped at ${stands.paused.reportIds[0]} because the platform `
        + 'asked to be signed in to. Sign in on that platform, then press Resume -- it carries on '
        + 'from there.',
    };
  }
  /* **A DAY THAT NEEDS THE SELLER COMES BEFORE ANYTHING ABOUT THE LAST RUN.** It
   * stays true whatever the last run did, and it is the one thing on this page
   * nobody else can do. */
  const needsYou = stands.needsYou || [];
  if (needsYou.length) {
    const named = needsYou.map((one) => `${one.reportId} for ${one.dataDate}`).join(', ');
    return {
      how: 'wrong',
      said: `${needsYou.length === 1 ? 'One day needs' : `${needsYou.length} days need`} you: `
        + `${named}. The platform never made ${needsYou.length === 1 ? 'it' : 'them'} available `
        + `in three days of trying, so fetch ${needsYou.length === 1 ? 'it' : 'them'} by hand.`,
    };
  }
  if (!stands.night) {
    return { how: 'idle', said: 'No runs yet. Tick what you want and press Run now.' };
  }
  const failed = stands.night.done.filter((one) => one.state === 'failed').length;
  if (failed) {
    return {
      how: 'wrong',
      said: `The last run finished with ${failed} report${failed === 1 ? '' : 's'} that failed.`,
    };
  }
  return {
    how: 'done',
    said: `The last run finished at ${inWordsWhen(stands.night.finishedAt)}.`,
  };
}

/**
 * Build the page once, and hand back the pieces that change.
 *
 * **BUILT ONCE AND UPDATED, NEVER REDRAWN.** The page polls every two seconds;
 * rebuilding it on every poll would take the keyboard away from the time box
 * while somebody was typing in it, and would throw away which reports they had
 * ticked.
 */
export function buildThePanel(into, doing) {
  const parts = {};
  const page = make('div', `${OURS}page`);

  const bar = make('div', `${OURS}bar`);
  put(bar, make('span', `${OURS}brand`, 'KARTAAN'), make('span', `${OURS}what`, 'Auto-sync'));
  put(page, bar);

  const body = make('div', `${OURS}body`);
  put(page, body);

  /* ------------------------------------------------------- setting up, once */
  parts.setup = make('section', `${OURS}card`);
  put(parts.setup, make('h2', `${OURS}title`, 'Set up, once'));
  put(parts.setup, make('p', `${OURS}note`,
    'Neither of these can be done for you, and nothing runs until both are done.'));

  const driveRow = make('div', `${OURS}row`);
  parts.driveState = make('span', `${OURS}state`, '');
  parts.connectDrive = make('button', 'k-button k-button--main', 'Connect Google Drive');
  parts.connectDrive.type = 'button';
  put(driveRow, make('span', `${OURS}label`, '1. Your Google Drive'),
    parts.connectDrive, parts.driveState);
  put(parts.setup, driveRow);

  const panelRow = make('div', `${OURS}row`);
  parts.panelName = make('input', 'k-control');
  parts.panelName.type = 'text';
  parts.panelName.placeholder = 'your-panel-name';
  parts.savePanel = make('button', 'k-button k-button--ordinary', 'Save');
  parts.savePanel.type = 'button';
  parts.panelState = make('span', `${OURS}state`, '');
  put(panelRow, make('span', `${OURS}label`, '2. Your Meesho panel name'),
    parts.panelName, parts.savePanel, parts.panelState);
  put(parts.setup, panelRow);
  put(parts.setup, make('p', `${OURS}note`,
    'It is the part of the address of your own Meesho supplier panel between "fulfillment/" '
    + 'and "/orders". It is yours, so it is not in the extension.'));
  put(body, parts.setup);

  /* ----------------------------------------------------------- what is happening */
  parts.banner = make('div', `${OURS}banner`);
  put(body, parts.banner);

  /* **THE TWO DATE BOXES -- HIS ASK, 2026-09-16.** Empty is yesterday, which is what
   * every run did before they existed. Filled, Run now fetches every day between them,
   * oldest first. */
  const whichDays = make('div', `${OURS}row`);
  parts.from = make('input', 'k-control');
  parts.from.type = 'date';
  parts.to = make('input', 'k-control');
  parts.to.type = 'date';
  put(whichDays, make('span', `${OURS}label`, 'Days to fetch'),
    make('span', `${OURS}note`, 'From'), parts.from,
    make('span', `${OURS}note`, 'To'), parts.to,
    make('span', `${OURS}note`, 'Leave both empty for yesterday.'));
  put(body, whichDays);

  parts.actions = make('div', `${OURS}actions`);
  parts.runNow = make('button', 'k-button k-button--main', 'Run now');
  parts.runNow.type = 'button';
  parts.stop = make('button', 'k-button k-button--danger', 'Stop');
  parts.stop.type = 'button';
  parts.resume = make('button', 'k-button k-button--main', 'Resume');
  parts.resume.type = 'button';
  parts.resume.hidden = true;
  parts.said = make('p', `${OURS}said`, '');
  parts.said.hidden = true;
  put(parts.actions, parts.runNow, parts.resume, parts.stop);
  put(body, parts.actions, parts.said);

  /* --------------------------------------------------------------- platforms */
  const platforms = make('section', `${OURS}card`);
  put(platforms, make('h2', `${OURS}title`, 'Where your reports come from'));
  parts.platforms = make('div', `${OURS}grid`);
  put(platforms, parts.platforms);
  put(body, platforms);

  /* ------------------------------------------------------- Flipkart's twenty */
  const allowance = make('section', `${OURS}card`);
  put(allowance, make('h2', `${OURS}title`, 'Flipkart requests left today'));
  parts.allowance = make('p', `${OURS}figure`, '');
  parts.allowanceNote = make('p', `${OURS}note`, '');
  put(allowance, parts.allowance, parts.allowanceNote);
  put(body, allowance);

  /* ----------------------------------------------------------------- reports */
  const reports = make('section', `${OURS}card`);
  put(reports, make('h2', `${OURS}title`, 'What to fetch'));
  parts.selectAll = make('button', 'k-button k-button--quiet k-button--small', 'Tick all');
  parts.selectAll.type = 'button';
  put(reports, parts.selectAll);
  parts.reports = make('div', `${OURS}list`);
  put(reports, parts.reports);
  put(body, reports);

  /* --------------------------------------------------- what it cannot fetch */
  const cannot = make('section', `${OURS}card`);
  put(cannot, make('h2', `${OURS}title`, 'What this cannot fetch, and why'));
  parts.cannot = make('div', `${OURS}list`);
  put(cannot, parts.cannot);
  put(body, cannot);

  /* -------------------------------------------------------------- the clock */
  const clock = make('section', `${OURS}card`);
  put(clock, make('h2', `${OURS}title`, 'When this extension wakes each day'));
  const clockRow = make('div', `${OURS}row`);
  parts.hour = make('input', 'k-control');
  parts.hour.type = 'time';
  parts.saveHour = make('button', 'k-button k-button--ordinary', 'Save');
  parts.saveHour.type = 'button';
  parts.hourState = make('span', `${OURS}state`, '');
  put(clockRow, parts.hour, parts.saveHour, parts.hourState);
  put(clock, clockRow);
  put(clock, make('p', `${OURS}note`,
    'This is the clock inside your browser. It is NOT the clock the scheduled sync in your '
    + 'own GitHub account runs on -- that one is set there, and changing this does not move '
    + 'it. At the time you save here, this extension fetches its own list by itself, '
    + 'one platform after the other. Chrome has to be open and the machine awake.'));
  /* **WHAT THE TIMED SYNC WILL FETCH, SAID -- HIS DECISION B (A60).** The ticks above
   * are for Run now only and never change it. */
  parts.timed = make('p', `${OURS}note`, '');
  put(clock, parts.timed);
  put(body, clock);

  /* ----------------------------------------------------------------- the log */
  const log = make('section', `${OURS}card`);
  put(log, make('h2', `${OURS}title`, 'What happened, in words'));
  parts.log = make('pre', `${OURS}log`, '');
  put(log, parts.log);
  put(body, log);

  /* ------------------------------------------------------------- the manual */
  /* **THE LONGER ANSWER, AND IT IS ON THE SAME PAGE AS THE THING.** His
   * instruction, 2026-09-11: a tooltip beside the control, a manual for somebody
   * who wants to be shown, and a developer's document for whoever works on this
   * next. **The words are `manual.js`'s, never invented here** -- the same rule
   * the failure reasons follow, so there is one place to correct and not two. */
  const help = make('section', `${OURS}card`);
  put(help, make('h2', `${OURS}title`, 'How this works'));
  for (const entry of MANUAL) {
    const one = make('details', `${OURS}help`);
    put(one, make('summary', `${OURS}helpTitle`, `${entry.label} -- ${entry.crux}`));
    const steps = make('ul', `${OURS}helpSteps`);
    for (const said of entry.steps) put(steps, make('li', '', said));
    put(one, steps);
    for (const said of entry.more || []) put(one, make('p', `${OURS}note`, said));
    put(help, one);
  }
  parts.help = help;
  put(body, help);

  /* **AND THE SHORT ANSWER SITS ON THE CONTROL ITSELF.** Written from the same
   * file, so a tooltip and a manual entry cannot drift apart -- and a control
   * that grows without one goes red in `manual.test.js` rather than shipping
   * bare. */
  for (const [which, said] of Object.entries(TOOLTIPS)) {
    if (parts[which]) parts[which].title = said;
  }

  into.append(page);

  parts.connectDrive.addEventListener('click', () => doing.connectTheDrive());
  parts.savePanel.addEventListener('click', () => doing.saveThePanelName(parts.panelName.value));
  parts.runNow.addEventListener('click', () => doing.runNow(
    whatIsTicked(parts), parts.from.value, parts.to.value,
  ));
  parts.stop.addEventListener('click', () => doing.stop());
  parts.resume.addEventListener('click', () => doing.resume && doing.resume());
  parts.saveHour.addEventListener('click', () => doing.setTheHour(parts.hour.value));
  parts.selectAll.addEventListener('click', () => tickAll(parts));

  /* What is ticked, kept here rather than read back off the page every poll. */
  parts.ticked = new Set();
  parts.boxes = new Map();
  parts.states = new Map();
  /* One tick-all button per platform, so a seller picks a whole platform in one press. */
  parts.platformTicks = new Map();
  /* **EVERY CHANGE OF TICKS IS SAVED**, so the panel opens with them again. They
   * are for Run now only; the timed sync keeps its own list (A60). */
  parts.ticksChanged = () => {
    showWhatIsTicked(parts);
    if (doing.saveTheTicks) doing.saveTheTicks(whatIsTicked(parts));
  };
  /* Each report brought by another's run, and that report (A61, Job 5b). */
  parts.tied = new Map();
  parts.platformIds = new Map();
  return parts;
}

/**
 * The boxes that follow another's tick, and the tick-all words, made to match what
 * is ticked (A61, Job 5b). The two Meesho ads files show ticked exactly when the
 * ads sweep is, because that one request writes all three: what he sees is what is
 * fetched. They are never put into `ticked` -- no request of their own exists.
 */
function showWhatIsTicked(parts) {
  for (const [id, from] of parts.tied || []) {
    if (parts.boxes.get(id)) parts.boxes.get(id).checked = parts.ticked.has(from);
  }
  const allOn = (ids) => {
    const own = ids.filter((id) => parts.boxes.get(id) && !parts.boxes.get(id).disabled);
    return own.length > 0 && own.every((id) => parts.ticked.has(id));
  };
  parts.selectAll.textContent = allOn([...parts.boxes.keys()]) ? 'Untick all' : 'Tick all';
  for (const [platform, button] of parts.platformTicks) {
    const named = CALLED[platform] || platform;
    button.textContent = `${allOn(parts.platformIds.get(platform) || []) ? 'Untick' : 'Tick'} all ${named}`;
  }
}

/** Which reports are ticked right now. */
export function whatIsTicked(parts) {
  return [...parts.ticked];
}

/** Tick, or untick, exactly these reports -- one platform's (A53, his ask 2026-09-16).
 *  Answers whether they are now ticked, so the button can say what it will do next. */
function tickAllOf(parts, reportIds) {
  const every = reportIds.filter((id) => parts.boxes.get(id) && !parts.boxes.get(id).disabled);
  const allOn = every.length > 0 && every.every((id) => parts.ticked.has(id));
  for (const id of every) {
    if (allOn) parts.ticked.delete(id);
    else parts.ticked.add(id);
    parts.boxes.get(id).checked = !allOn;
  }
  if (parts.ticksChanged) parts.ticksChanged();
  return !allOn;
}

function tickAll(parts) {
  const every = [...parts.boxes.keys()].filter((id) => !parts.boxes.get(id).disabled);
  const allOn = every.every((id) => parts.ticked.has(id));
  for (const id of every) {
    if (allOn) parts.ticked.delete(id);
    else parts.ticked.add(id);
    parts.boxes.get(id).checked = !allOn;
  }
  parts.selectAll.textContent = allOn ? 'Tick all' : 'Untick all';
  if (parts.ticksChanged) parts.ticksChanged();
}

/**
 * Put what the worker said onto the page.
 *
 * **NOTHING IS BUILT AGAIN THAT DOES NOT HAVE TO BE.** The report rows are built
 * once, the first time a list arrives, and only their state changes after that
 * -- so a tick a seller made two seconds ago is still there.
 */
export function showHowItStands(parts, stands) {
  const banner = whatTheBannerSays(stands);
  parts.banner.className = `${OURS}banner ${OURS}banner--${banner.how}`;
  parts.banner.textContent = banner.said;
  if (parts.resume) parts.resume.hidden = !stands.paused;

  parts.setup.hidden = stands.setUp.done;
  parts.driveState.textContent = stands.setUp.driveConnectedAt
    ? `connected ${inWordsWhen(stands.setUp.driveConnectedAt)}`
    : (stands.setUp.driveSaid || 'not connected yet');
  if (document.activeElement !== parts.panelName) {
    parts.panelName.value = stands.setUp.panel;
  }
  parts.panelState.textContent = stands.setUp.panel ? 'saved' : 'not set yet';

  const going = Boolean(stands.night && !stands.night.finishedAt);
  parts.runNow.disabled = going || !stands.setUp.done;
  parts.stop.disabled = !going;
  if (parts.timed) parts.timed.textContent = (stands.timed && stands.timed.said) || '';

  /* ------------------------------------------------------------- platforms */
  parts.platforms.textContent = '';
  for (const one of stands.platforms) {
    const card = make('div', `${OURS}platform`);
    put(card, make('span', `${OURS}platform-name`, one.name));
    if (!one.throughTheBrowser) {
      put(card, make('span', `${OURS}state`, 'not fetched here'));
      put(card, make('span', `${OURS}note`,
        'Amazon comes in through its own door in the scheduled sync, with your own Amazon '
        + 'credentials. There is nothing to connect here.'));
    } else {
      put(card, make('span', `${OURS}state ${OURS}state--${one.ready ? 'yes' : 'no'}`,
        one.ready ? 'ready' : 'not ready'));
      put(card, make('span', `${OURS}note`, one.lastRun
        ? `Last run ${inWordsWhen(one.lastRun.finishedAt)} -- ${one.lastRun.landed} `
          + `fetched, ${one.lastRun.failed} failed.`
        : 'Has never run.'));
    }
    put(parts.platforms, card);
  }

  /* ----------------------------------------------------- Flipkart's twenty */
  parts.allowance.textContent = `${stands.flipkart.leftToday} of ${stands.flipkart.allowedADay}`;
  parts.allowanceNote.textContent
    = `${stands.flipkart.askedForToday} used today. Only Flipkart's orders, returns and payments `
    + 'reports spend one; everything else is free.';

  /* --------------------------------------------------------------- reports */
  if (parts.boxes.size !== stands.reports.length) {
    parts.reports.textContent = '';
    /* **ALL THREE ARE CLEARED TOGETHER, and only `boxes` used to be.** `states`
     * then held nodes that were no longer on the page, and `ticked` held report
     * ids that had no row -- **and Run now sends exactly what `ticked` holds**,
     * so a rebuild could have started a run for a report nobody could see. */
    parts.boxes.clear();
    parts.states.clear();
    parts.ticked.clear();
    parts.platformTicks.clear();
    parts.tied.clear();
    parts.platformIds.clear();
    /* **GROUPED BY PLATFORM, EACH WITH ITS OWN TICK-ALL -- HIS ASK, 2026-09-16.** A sync
     * runs one platform at a time, so this is also how a seller picks a sync's worth of
     * reports in one press. */
    const platforms = [...new Set(stands.reports.map((one) => one.platform))];
    for (const platform of platforms) {
      const named = CALLED[platform] || platform;
      const ofThisPlatform = stands.reports.filter((one) => one.platform === platform);
      const heading = make('div', `${OURS}platform-group`);
      const tickThese = make('button', 'k-button k-button--ordinary', `Tick all ${named}`);
      tickThese.type = 'button';
      tickThese.addEventListener('click', () => {
        const nowOn = tickAllOf(parts, ofThisPlatform.map((one) => one.id));
        tickThese.textContent = `${nowOn ? 'Untick' : 'Tick'} all ${named}`;
      });
      put(heading, make('span', `${OURS}report-name`, named), tickThese);
      put(parts.reports, heading);
      parts.platformTicks.set(platform, tickThese);
      parts.platformIds.set(platform, ofThisPlatform.map((one) => one.id));
      for (const one of ofThisPlatform) {
        buildOneReportRow(parts, stands, one);
      }
    }
    showWhatIsTicked(parts);
  }
  for (const one of stands.reports) {
    const state = parts.states.get(one.id);
    if (!state) continue;
    state.textContent = one.canBeFetched
      ? whatThatStateIsCalled(one.state) + (one.say ? ` -- ${one.say}` : '')
      : 'cannot be fetched';
  }
  showTheRestOfIt(parts, stands);
}

/** One report's own row: its box, its name, and where it got to. */
function buildOneReportRow(parts, stands, one) {
  const row = make('label', `${OURS}report`);
  const box = make('input');
  box.type = 'checkbox';
  /* **A REPORT THAT ARRIVES WITH ANOTHER HAS NO TICK OF ITS OWN**, and until this
   * line it had one that looked exactly like every other. Ticking it saved
   * nothing and started nothing: the worker refuses a whole set holding an id it
   * has no recipe for, so "Tick all" then pressing Run now saved no ticks at all
   * and the run never began. */
  box.disabled = !one.canBeFetched || Boolean(one.fetchedBy);
  /* **THE SAVED TICKS COME BACK WHEN THE PANEL OPENS.** */
  if (!box.disabled && ((stands.setUp && stands.setUp.ticked) || []).includes(one.id)) {
    box.checked = true;
    parts.ticked.add(one.id);
  }
  box.addEventListener('change', () => {
    if (box.checked) parts.ticked.add(one.id);
    else parts.ticked.delete(one.id);
    if (parts.ticksChanged) parts.ticksChanged();
  });
  const state = make('span', `${OURS}state`, '');
  put(row, box, make('span', `${OURS}report-name`, one.name),
    make('span', `${OURS}report-id`, one.id), state);
  if (one.spends) put(row, make('span', `${OURS}spends`, 'spends 1 of 20'));
  /* **AND THE ROW SAYS WHY IT HAS NO TICK**, which is what the manual has
   * promised a seller all along. */
  if (one.fetchedBy) put(row, make('span', `${OURS}note`, one.fetchedBy));
  if (one.fetchedBy && one.broughtBy) parts.tied.set(one.id, one.broughtBy);
  put(parts.reports, row);
  parts.boxes.set(one.id, box);
  parts.states.set(one.id, state);
}

/** Everything under the report list, drawn on every poll. */
function showTheRestOfIt(parts, stands) {
  /* ------------------------------------------------ what it cannot fetch */
  if (!parts.cannot.children.length) {
    for (const one of stands.cannotBeFetched) {
      const row = make('div', `${OURS}cannot`);
      put(row, make('span', `${OURS}report-name`, one.name),
        make('span', `${OURS}report-id`, one.id),
        make('span', `${OURS}note`, one.why));
      put(parts.cannot, row);
    }
    if (!stands.cannotBeFetched.length) {
      put(parts.cannot, make('p', `${OURS}note`, 'Every report this door declares can be fetched.'));
    }
  }

  /* ------------------------------------------------------------- the clock */
  /* **THE SAVED HOUR IS PUT BACK IN THE BOX, and it never was.** A seller who set
   * it yesterday opened this page to an empty box and no way to tell whether
   * anything had been saved at all. Only when they are not typing in it. */
  const clock = stands.clock || null;
  if (clock && clock.chosen && parts.hour.value !== clock.chosen
    && globalThis.document && globalThis.document.activeElement !== parts.hour) {
    parts.hour.value = clock.chosen;
  }
  parts.hourState.textContent = whenItNextWakes(clock);

  parts.log.textContent = stands.inWords;
}

/** When the extension next wakes by itself, in the seller's own words. */
export function whenItNextWakes(clock) {
  if (!clock || !clock.chosen) return 'No time saved yet, so it wakes at half past two in the morning.';
  if (!clock.nextAt) {
    return `Saved as ${clock.chosen}, but its clock is not set -- nothing will start by itself. `
      + 'Press Save again.';
  }
  return `Next wakes ${inWordsWhen(clock.nextAt)}.`;
}

/** Say something back to whoever pressed a button, or take the message away. */
export function saySomething(parts, said) {
  parts.said.textContent = said || '';
  parts.said.hidden = !said;
}
