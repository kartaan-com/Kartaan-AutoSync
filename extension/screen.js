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

import {
  theNight, endTheNight, howTheNightWent, theDay, thatOneIsDone,
  A_DAYS_ALLOWANCE, spendsTheAllowance,
} from './nightly.js';
import { THE_WALK } from './background.js';
import { aDriveToken } from './drive.js';

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
  };
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
 * takes the address of the first step that has one and keeps only its origin,
 * which is the seller's own portal and nothing more specific.
 */
export function whereToStartFrom(book, reportIds) {
  for (const reportId of reportIds) {
    const recipe = (book.recipes || {})[reportId];
    if (!recipe) continue;
    for (const step of [...(recipe.toAsk || []), ...(recipe.toTake || [])]) {
      if (!step.address) continue;
      const upTo = String(step.address).indexOf('/', 'https://'.length);
      return upTo === -1 ? String(step.address) : String(step.address).slice(0, upTo);
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
export function whyItCannotBeStarted(book, { reportIds, panel, night }) {
  if (night && !night.finishedAt) {
    return 'A run is already going. Stop it first, or wait for it to finish.';
  }
  if (!reportIds || !reportIds.length) {
    return 'Nothing is ticked, so there is nothing to fetch.';
  }
  const platforms = [...new Set(reportIds.map((one) => thePlatformOf(book, one)))];
  if (platforms.length > 1) {
    return 'One platform at a time. A run starts at one portal page and every report in it is '
      + `fetched from there, and these are ${platforms.map((one) => CALLED[one] || one).join(' and ')}.`;
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
  if (!whereToStartFrom(book, reportIds)) {
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
export async function howItStands(chrome, { book, now = Date.now() } = {}) {
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
  const cannot = declared
    .filter((one) => THROUGH_THE_BROWSER.includes(one.platform) && !(book.recipes || {})[one.id])
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
        canBeFetched: Boolean((book.recipes || {})[one.id]),
        spends: spendsTheAllowance(one.id),
        ...(byReport[one.id] || { state: '', say: '', size: 0 }),
      })),
    cannotBeFetched: cannot,
    theDayItWouldFetch: theDayToFetch(now),
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
  'run-now', 'stop', 'set-the-hour',
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
    return { stands: await howItStands(chrome, { book, now: now() }) };
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

  if (asked.do === 'run-now') {
    const reportIds = [...new Set(asked.reportIds || [])];
    const setUp = await theSetup(chrome);
    const night = await theNight(chrome);
    const wrong = whyItCannotBeStarted(book, { reportIds, panel: setUp.panel, night });
    if (wrong) return { wrong };
    if (!setUp.driveConnectedAt) {
      return {
        wrong: 'Your Google Drive is not connected yet, so anything fetched would have nowhere '
          + 'to go. Connect it first.',
      };
    }
    const kept = await theNights(chrome);
    const started = await parts.startTheNight(chrome, {
      doing: reportIds,
      mayAskFor: howManyItMaySpend(book, { reportIds, kept, night, now: now() }),
      at: now(),
      openAt: whereToStartFrom(book, reportIds),
      dataDate: theDayToFetch(now()),
    });
    await parts.carryOn();
    return { started: (started && started.left) || [] };
  }

  return { wrong: `The panel asked for "${asked.do}", which is not something it may ask for.` };
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

  parts.actions = make('div', `${OURS}actions`);
  parts.runNow = make('button', 'k-button k-button--main', 'Run now');
  parts.runNow.type = 'button';
  parts.stop = make('button', 'k-button k-button--danger', 'Stop');
  parts.stop.type = 'button';
  parts.said = make('p', `${OURS}said`, '');
  parts.said.hidden = true;
  put(parts.actions, parts.runNow, parts.stop);
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
    'This is the clock inside your browser. It is NOT the clock the nightly job in your '
    + 'own GitHub account runs on -- that one is set there, and changing this does not move '
    + 'it. Nothing decides tonight\'s list yet either, so until it does, a run is started '
    + 'from this page.'));
  put(body, clock);

  /* ----------------------------------------------------------------- the log */
  const log = make('section', `${OURS}card`);
  put(log, make('h2', `${OURS}title`, 'What happened, in words'));
  parts.log = make('pre', `${OURS}log`, '');
  put(log, parts.log);
  put(body, log);

  into.append(page);

  parts.connectDrive.addEventListener('click', () => doing.connectTheDrive());
  parts.savePanel.addEventListener('click', () => doing.saveThePanelName(parts.panelName.value));
  parts.runNow.addEventListener('click', () => doing.runNow(whatIsTicked(parts)));
  parts.stop.addEventListener('click', () => doing.stop());
  parts.saveHour.addEventListener('click', () => doing.setTheHour(parts.hour.value));
  parts.selectAll.addEventListener('click', () => tickAll(parts));

  /* What is ticked, kept here rather than read back off the page every poll. */
  parts.ticked = new Set();
  parts.boxes = new Map();
  parts.states = new Map();
  return parts;
}

/** Which reports are ticked right now. */
export function whatIsTicked(parts) {
  return [...parts.ticked];
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

  /* ------------------------------------------------------------- platforms */
  parts.platforms.textContent = '';
  for (const one of stands.platforms) {
    const card = make('div', `${OURS}platform`);
    put(card, make('span', `${OURS}platform-name`, one.name));
    if (!one.throughTheBrowser) {
      put(card, make('span', `${OURS}state`, 'not fetched here'));
      put(card, make('span', `${OURS}note`,
        'Amazon comes in through its own door in the nightly job, with your own Amazon '
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
    for (const one of stands.reports) {
      const row = make('label', `${OURS}report`);
      const box = make('input');
      box.type = 'checkbox';
      box.disabled = !one.canBeFetched;
      box.addEventListener('change', () => {
        if (box.checked) parts.ticked.add(one.id);
        else parts.ticked.delete(one.id);
      });
      const state = make('span', `${OURS}state`, '');
      put(row, box, make('span', `${OURS}report-name`, one.name),
        make('span', `${OURS}report-id`, one.id), state);
      if (one.spends) put(row, make('span', `${OURS}spends`, 'spends 1 of 20'));
      put(parts.reports, row);
      parts.boxes.set(one.id, box);
      parts.states.set(one.id, state);
    }
  }
  for (const one of stands.reports) {
    const state = parts.states.get(one.id);
    if (!state) continue;
    state.textContent = one.canBeFetched
      ? whatThatStateIsCalled(one.state) + (one.say ? ` -- ${one.say}` : '')
      : 'cannot be fetched';
  }

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

  parts.log.textContent = stands.inWords;
}

/** Say something back to whoever pressed a button, or take the message away. */
export function saySomething(parts, said) {
  parts.said.textContent = said || '';
  parts.said.hidden = !said;
}
