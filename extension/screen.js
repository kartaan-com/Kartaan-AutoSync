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
  theNight, endTheNight, howTheNightWent, theDay, thatOneIsDone, theReportTable, theIdleLine,
  A_DAYS_ALLOWANCE, KEPT_FOR_HIS_OWN_RUNS, inTheNightsOwnLine, spendsTheAllowance, whatNeedsYou,
  CATCH_UP_REACH_DAYS, clearNamedNeedsYouEntries, rememberLastLanded, LAST_LANDED,
} from './nightly.js';
import { theUpdateNotice } from './update.js';
import { whatIsWaiting } from './idle.js';
import { THE_WALK } from './background.js';
import { aDriveToken } from './drive.js';
import {
  PAUSED, RECHECKS, THE_NIGHT, THE_SCHEDULED_QUEUE, THE_SYNC_FAILED, whatIsPaused,
} from './nightly.js';
import {
  askMayFetch, saveTheRunPass, whatKartaanLastSaid,
} from './kartaan.js';

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

/* Which platforms this extension WALKS reports for. **Amazon joined with its first walker, the
 * traffic by child item (`az_traffic`, AutoSync v0.1.21 lane 1 job 7).** It was kept out until then
 * (A79, his D317 of 12 Oct 2026) because, put in earlier, every Amazon report would have shown in
 * the report list as one that cannot be fetched. Amazon's orders, returns and settlements still
 * come in through its own door in the scheduled sync with the seller's own SP-API credentials,
 * and are not in this list's reports: only a report with a recipe is shown. */
export const THROUGH_THE_BROWSER = Object.freeze(['flipkart', 'meesho', 'amazon']);

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
export function whyThatDayCannotBeFetched(day, now = Date.now(), todayIsAllowed = false) {
  const said = String(day || '');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(said) || theDay(Date.parse(`${said}T12:00:00`)) !== said) {
    return `"${said}" is not a day. Write it as year-month-day, like 2026-09-01.`;
  }
  /* **R208 (D1005): TODAY IS NEVER A HARD BLOCK.** Where every report asked for is set to "today", today passes. */
  if (said > theDayToFetch(now) && !(todayIsAllowed && said === theDay(now))) {
    return `${said} is not over yet, so no platform has built it. Pick yesterday or earlier.`;
  }
  return '';
}

/* **HOW MANY DAYS ONE PRESS MAY FETCH (A53, 2026-09-16).** A range is walked a day at
 * a time -- except Flipkart's orders and payments, which take the whole stretch in ONE
 * request (P16, D424) -- so a year in one press would be hundreds of visits to a seller's
 * portal in one go. A file named for a range names at most this many days too
 * (`walk.js` `MOST_DAYS_IN_A_RANGE_FILE`; a check holds the two equal). A month is what Meesho's own orders export allows in one range
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
export function whyThatRangeCannotBeFetched(from, to, now = Date.now(), todayIsAllowed = false) {
  const first = whyThatDayCannotBeFetched(from, now, todayIsAllowed);
  if (first) return first;
  const last = whyThatDayCannotBeFetched(to, now, todayIsAllowed);
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
    /* **R208 (D968, D1005, D1006): EACH REPORT'S OWN DAY AND RUN, chosen on the panel.** Only the two words each may be (`THE_DAY_CHOICES`, `THE_RUNS`);
     * anything else reads as "not chosen", which is the default (`theDayOf`, `theRunOf`). */
    days: Object.fromEntries(Object.entries(kept.days || {}).filter(([, one]) => THE_DAY_CHOICES.includes(one))),
    runs: Object.fromEntries(Object.entries(kept.runs || {}).filter(([, one]) => THE_RUNS.includes(one))),
    /* R250 (D1035): the own time of each report that has one (only real times of day). */
    ownAt: Object.fromEntries(Object.entries(kept.ownAt || {}).filter(([, one]) => A_TIME_OF_DAY.test(String(one)))),
  };
}

/**
 * What the timed sync fetches: its own list, or every report that needs
 * downloading when none was ever kept. Never the Run now ticks: on 09-18..09-20
 * two ticked ad reports became the whole daily sync, and no Meesho ran.
 */
/* Put off by him (decision E: organic keywords). **NEVER FETCHED -- NOT BY THE TIMER, NOT BY A RUN NOW TICK (A84).** `fk_ads_kw` is back on
 * (his correction 6 Nov 2026, AS9 R238: his 12 Oct words were about organic keywords; keyword ADS are still on Flipkart). */
const OFF_THE_TIMED_LIST = Object.freeze(['fk_keywords']);

/** **THE REPORTS THAT ARE NOT READY IN THE MORNING (AJ13a, his order of 3 Nov 2026, evidence `R184-MORNING-FETCH-2026-11-03.md`).** The 4 pm run fetches
 *  ONLY these; the morning run fetches every other timed report. **The split is this one list -- moving a report to the other run is one line here.** A
 *  report on this list is not a failure when the morning run does not fetch it. */
export const THE_EVENING_REPORTS = Object.freeze(['fk_orders', 'fk_views', 'az_fee_preview', 'me_views']);

/** **R208 (his D968, 7 Nov 2026): THE RETURNS ARE FETCHED AT 6 PM FOR TODAY**, the whole day, and the next morning does not fetch that day again. */
export const THE_RETURNS_REPORTS = Object.freeze(['fk_returns', 'me_returns', 'az_returns']);
/** The three timed runs, and the two days a report may be for. A report's own choice is kept on the panel (`theSetup`). */
export const THE_RUNS = Object.freeze(['morning', 'evening', 'own']);

/** R250 (his D1035): a report on "Own time" runs at a time of its own; the returns default to 18:00. */
export const A_TIME_OF_DAY = /^([01]\d|2[0-3]):[0-5]\d$/;
export const THE_OWN_DEFAULT = '18:00';

/**
 * R250 (his D1035): WHEN EACH REPORT IS USUALLY READY, for the warning shown while an own time is set. A small FIXED table; nothing is read from a platform.
 * Where each time came from:
 *  - fk_orders, fk_views, az_fee_preview, me_views = `THE_EVENING_REPORTS`: the morning fetch of 3 Nov 2026 found them not ready (`R184-MORNING-FETCH-2026-11-03.md`), which is why the evening run (4 pm) exists (AJ13a, D918).
 *  - fk_returns, me_returns, az_returns = `THE_RETURNS_REPORTS`: his D968 and 7 Nov 2026, the day's returns are all in by 6 pm.
 * A report not in the table is not warned about.
 */
export const USUALLY_READY_AFTER = Object.freeze({
  fk_orders: '16:00', fk_views: '16:00', az_fee_preview: '16:00', me_views: '16:00',
  fk_returns: '18:00', me_returns: '18:00', az_returns: '18:00',
});

/** The warning for an own time earlier than the report is usually ready, or ''. */
export function theReadyWarning(id, at) {
  const ready = USUALLY_READY_AFTER[id];
  return ready && A_TIME_OF_DAY.test(at || '') && at < ready ? `You may not get this report at ${at}. It is usually ready after ${ready}.` : '';
}
export const THE_DAY_CHOICES = Object.freeze(['yesterday', 'today']);

/** Which timed run a report belongs to: the seller's choice, else the returns' own run, else the evening list, else the morning. */
export function theRunOf(setUp, id) {
  const chosen = (setUp.runs || {})[id];
  if (THE_RUNS.includes(chosen)) return chosen;
  if (THE_RETURNS_REPORTS.includes(id)) return 'own';
  return THE_EVENING_REPORTS.includes(id) ? 'evening' : 'morning';
}

/** Which day a report is for: the seller's choice, else today for the returns, else yesterday. */
export function theDayOf(setUp, id) {
  const chosen = (setUp.days || {})[id];
  if (THE_DAY_CHOICES.includes(chosen)) return chosen;
  return THE_RETURNS_REPORTS.includes(id) ? 'today' : 'yesterday';
}

/** A report's own time: the seller's, else 18:00. */
export function theOwnAtOf(setUp, id) {
  const chosen = (setUp.ownAt || {})[id];
  return A_TIME_OF_DAY.test(chosen || '') ? chosen : THE_OWN_DEFAULT;
}

/** The distinct own times the reports have now, earliest first: one alarm each. */
export function theOwnTimesOf(book, setUp) {
  return [...new Set(theTimedList(book, setUp).filter((id) => theRunOf(setUp, id) === 'own').map((id) => theOwnAtOf(setUp, id)))].sort();
}

/** What ONE timed run fetches: the reports whose run it is; for an own-time run (`at` given), the reports whose own time it is. */
export function theTimedListFor(book, setUp, run, at = null) {
  return theTimedList(book, setUp).filter((id) => theRunOf(setUp, id) === run && (run !== 'own' || !at || theOwnAtOf(setUp, id) === at));
}

export function theTimedList(book, setUp) {
  const every = (book.reports || [])
    .filter((one) => THROUGH_THE_BROWSER.includes(one.platform) && (book.recipes || {})[one.id]
      && !OFF_THE_TIMED_LIST.includes(one.id))
    .map((one) => one.id);
  return setUp.timed ? setUp.timed.filter((id) => every.includes(id)) : every;
}

/** Every report with a tick box of its own on the Run now panel (A61, Job 5b). */
export function theTickableReports(book) {
  return (book.reports || [])
    .filter((one) => THROUGH_THE_BROWSER.includes(one.platform) && (book.recipes || {})[one.id]
      && !OFF_THE_TIMED_LIST.includes(one.id))
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

/** PN2a: one "needs you" day with what the box prints: platform, report name and the Drive folder to put the file in. */
export function theNeedsYouRow(book, one) {
  const report = ((book && book.reports) || []).find((each) => each.id === one.reportId) || {};
  const platform = thePlatformOf(book, one.reportId);
  const { folders = {} } = book || {};
  const path = Object.hasOwn(folders, one.reportId) ? folders[one.reportId] : null;
  return {
    ...one,
    name: report.name || one.reportId,
    platformName: CALLED[platform] || platform,
    folder: Array.isArray(path) ? [(book && book.kartaan) || 'Kartaan', ...path].join(' > ') : '',
  };
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
  const before = (platform && kept.byPlatform[platform]) || {};
  const filed = {
    ...kept,
    filedNight: night.startedAt,
    byPlatform: {
      ...kept.byPlatform,
      ...(platform ? {
        /* **A RE-CHECK NEVER REPLACES THE RUN IT RE-CHECKS (review findings)**: the run, and the card's counts drawn
         * from it, stay as they were, and the re-check is kept beside it as its own small table. */
        [platform]: isARecheck(night) && (before.night || before.startedAt) ? { ...before, recheck: aCopyToKeep(night) } : {
          startedAt: night.startedAt,
          finishedAt: night.finishedAt,
          reached: (night.done || []).length,
          landed: landed.length,
          failed: (night.done || []).filter((one) => one.state === 'failed' || one.state === 'partial').length,
          why: String(night.why || ''),
          night: aCopyToKeep(night),
          recheck: null,
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
 * The finished night, kept under its platform so the panel's Last run can show EVERY platform of the sync (his ask,
 * 1 Nov 2026: the box showed only the last platform that ran). Only what the report table and the event list read;
 * the long words are cut, because the full ones are in the run log on the Drive.
 */
export function aCopyToKeep(night) {
  const cut = (text, most) => String(text || '').slice(0, most);
  return {
    startedAt: night.startedAt,
    finishedAt: night.finishedAt,
    why: cut(night.why, 400),
    idle: night.idle || null,
    toldKartaan: night.toldKartaan ? { said: cut(night.toldKartaan.said, 400), told: Boolean(night.toldKartaan.told) } : null,
    /* The newest rows, at most KEEP_AT_MOST_ROWS: a long catch-up range must not make the panel read megabytes. */
    done: (night.done || []).slice(-KEEP_AT_MOST_ROWS).map((one) => ({
      at: one.at, reportId: one.reportId, dataDate: one.dataDate, state: one.state, size: one.size,
      say: cut(one.say, 600), pageWas: cut(one.pageWas, 300),
    })),
  };
}

export const KEEP_AT_MOST_ROWS = 300;

/** An hourly re-check is a night of its own, and says so: it got past the idle wait as a `recheck`. */
export function isARecheck(night) {
  return Boolean(night && night.idle && night.idle.kind === 'recheck');
}

export const A_RECHECK_IS_CALLED = 'hourly re-check';

/**
 * Every platform's last run, in the order a sync walks them, each followed by its latest hourly re-check if any. The
 * night still going stands for its own platform -- beside its kept run when it is a re-check. A platform that has not
 * run in this sync shows its last kept run (with its own date on the table).
 */
export function theRuns(book, night, byPlatform) {
  const tonight = night ? thePlatformOfTheNight(book, night) : '';
  const runs = [];
  if (night && !tonight) runs.push({ platform: '', name: '', night });
  for (const platform of THROUGH_THE_BROWSER) {
    const name = CALLED[platform] || platform;
    const kept = (byPlatform || {})[platform] || {};
    const live = platform === tonight ? night : null;
    /* The kept run is a run of its own only when it is not the live night itself (review finding: a re-check filed
     * with no run before it was drawn twice). */
    const keptRun = kept.night && !(live && kept.night.startedAt === live.startedAt) ? kept.night : null;
    const run = live && !(isARecheck(live) && keptRun) ? live : keptRun;
    const recheck = live && isARecheck(live) && keptRun ? live : (live ? null : kept.recheck);
    const titled = (one) => (isARecheck(one) ? `${name} (${A_RECHECK_IS_CALLED})` : name);
    if (run) runs.push({ platform, name: titled(run), night: run });
    if (recheck) runs.push({ platform, name: titled(recheck), night: recheck });
  }
  return runs;
}

/** All the runs' events in time order, each line starting with its platform; a line with no time (fetching now) last. */
export function allTheEvents(runs, nameOf) {
  const all = [];
  for (const run of runs) {
    for (const one of theNightsEvents(run.night, nameOf)) {
      all.push({ ...one, words: run.name ? `${run.name}: ${one.words}` : one.words });
    }
  }
  return all.sort((a, b) => (a.at === null) - (b.at === null) || (a.at || 0) - (b.at || 0));
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

/** Give the claim back: the follow-through threw part way, so the next call must try it again (review finding,
 *  2026-10-05). `markCarriedOn` claims first so two calls cannot both do the work; if the work then fails, the
 *  claim must not stay spent, or the recheck clock, the notice and the next platform are never started. */
export async function releaseCarriedOn(chrome, night) {
  if (!night || !night.finishedAt) return;
  const kept = await theNights(chrome);
  if (kept.loggedNight !== night.startedAt) return;
  await chrome.storage.local.set({
    [THE_NIGHTS]: onlyRecentDays({ ...kept, loggedNight: null }),
  });
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
export function howManyItMaySpend(book, { reportIds, kept, night, now = Date.now(), timed = false }) {
  const spending = reportIds.filter((one) => spendsTheAllowance(one)).length;
  if (!spending) return 0;
  const left = Math.max(0, A_DAYS_ALLOWANCE - askedForToday(kept, night, now));
  /* **WHAT IS LEFT OF THE DAY, NOT ONE PER REPORT (review finding, 2026-10-05).** The cap used to be the number
   * of reports, so a sync owed several days spent its asks on the oldest and the day it was for was refused.
   * A TIMED sync keeps a few for his own runs the same day, but never less than its own day for each report. */
  const reserve = timed ? KEPT_FOR_HIS_OWN_RUNS : 0;
  return Math.min(left, Math.max(spending, left - reserve));
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
  const runs = theRuns(book, night, kept.byPlatform);

  const byReport = {};
  for (const one of (night && night.done) || []) {
    byReport[one.reportId] = { state: one.state, say: one.say || '', size: one.size || 0 };
  }
  if (night && night.doing) byReport[night.doing] = { state: 'fetching', say: '', size: 0 };
  for (const one of (night && night.left) || []) {
    if (!byReport[one]) byReport[one] = { state: 'waiting', say: '', size: 0 };
  }

  /* **ONLY THE REPORTS THIS DOOR IS MEANT TO FETCH.** Amazon's orders, returns and settlements come in by the API door with the seller's own keys; listed
   * here they would all read "cannot be fetched" (lane 1 job 7). */
  const declared = (book.reports || []).filter((one) => !(book.onTheApiDoor || []).includes(one.id));
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
    /* **EVERY PLATFORM OF THE SYNC, NOT ONLY THE LAST (his ask, 1 Nov 2026).** */
    runs,
    /* **WHAT HAPPENED, IN ORDER (AJ9 piece 6, BR1 lesson 5)** -- across all three platforms, each line naming its own. */
    events: allTheEvents(runs, (id) => ((book.reports || []).find((one) => one.id === id) || {}).name || id),
    /* **EVERY DAY GIVEN UP ON, KEPT ACROSS NIGHTS** until a later run fetches it,
     * so the banner can name it however many runs have happened since. */
    needsYou: (await whatNeedsYou(chrome)).map((one) => theNeedsYouRow(book, one)),
    paused: await whatIsPaused(chrome),
    /* **WHETHER A RUN PASS IS SAVED AND WHAT KARTAAN LAST SAID -- NEVER THE PASS (plan job 30).** */
    kartaan: await whatKartaanLastSaid(chrome),
    platforms: THROUGH_THE_BROWSER.map((platform) => ({
      id: platform,
      name: CALLED[platform] || platform,
      throughTheBrowser: true,
      /* Meesho cannot be walked at all without the seller's own panel name;
       * Flipkart and Amazon need nothing set up. All need the Drive, or what is
       * fetched goes nowhere. Whether the seller is signed in to a portal is found
       * out by a walk. */
      ready: Boolean(setUp.driveConnectedAt)
        && (platform !== 'meesho' || Boolean(setUp.panel)),
      lastRun: kept.byPlatform[platform] || null,
    })),
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
        /* The switched-off report has no tick box and cannot be started (A84). */
        canBeFetched: Boolean((book.recipes || {})[one.id] || fetchedByAnother[one.id]) && !OFF_THE_TIMED_LIST.includes(one.id),
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
    /* **R208 (D1006): EACH TIMED REPORT'S DAY AND RUN, for the panel to show and change.** */
    schedule: theTimedList(book, setUp).map((id) => ({
      id, name: ((book.reports || []).find((one) => one.id === id) || {}).name || id,
      platform: thePlatformOf(book, id),
      day: theDayOf(setUp, id), run: theRunOf(setUp, id), at: theOwnAtOf(setUp, id),
    })),
    /* **AJ8: A RUN THAT IS WAITING FOR THE COMPUTER TO BE LEFT ALONE**, or null. */
    waitingForIdle: await whatIsWaiting(chrome),
  };
}

/** The timed list counted, and said the way the panel shows it (A60, Job 5). */
function whatTheTimedSyncFetches(book, timed) {
  const flipkart = timed.filter((id) => thePlatformOf(book, id) === 'flipkart').length;
  const meesho = timed.filter((id) => thePlatformOf(book, id) === 'meesho').length;
  const amazon = timed.filter((id) => thePlatformOf(book, id) === 'amazon').length;
  return {
    flipkart,
    meesho,
    amazon,
    said: `The timed sync will fetch: ${timed.length} reports `
      + `(Flipkart ${flipkart}, Meesho ${meesho}, Amazon ${amazon})`,
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
  'save-the-run-pass', 'clear-needs-you', 'save-the-report-times', 'set-a-run-time',
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
    return {
      stands: {
        ...await howItStands(chrome, { book, now: now(), theClock: parts.theClock }),
        update: await theUpdateNotice(chrome, {
          installed: parts.installed, fetch: parts.fetchTheVersion, now: now(), opened: asked.opened === true,
        }),
      },
    };
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

  if (asked.do === 'save-the-run-pass') {
    /* **THE PASS GOES IN AND NOTHING OF IT COMES BACK (plan job 30).** The answer is "saved" or the reason it was
     * refused, in words; never the pass, which the page also empties from its box. */
    return saveTheRunPass(chrome, asked.pass);
  }

  if (asked.do === 'save-the-ticks') {
    const reportIds = [...new Set((asked.reportIds || []).map(String))];
    const unknown = reportIds.filter((id) => !(book.recipes || {})[id]);
    if (unknown.length) return { wrong: `${unknown.join(', ')} is not a report this can fetch.` };
    const unticked = theTickableReports(book).filter((id) => !reportIds.includes(id));
    await keepTheSetup(chrome, { ticked: reportIds, unticked });
    return { saved: true };
  }

  if (asked.do === 'save-the-report-times') {
    const setUp = await theSetup(chrome);
    const id = String(asked.reportId);
    if (!theTimedList(book, setUp).includes(id)) return { wrong: `${id} is not a report that runs by itself.` };
    if (!THE_DAY_CHOICES.includes(asked.day) || !THE_RUNS.includes(asked.run)) return { wrong: 'Pick yesterday or today, and morning, evening or own time.' };
    let ownAt = setUp.ownAt || {};
    if (asked.run === 'own') {
      const wrong = (parts.whyAnOwnTimeIsRefused && await parts.whyAnOwnTimeIsRefused(chrome, asked.at))
        || (A_TIME_OF_DAY.test(String(asked.at)) ? null : 'An own time is a time of day, like 18:00.');
      if (wrong) return { wrong };
      ownAt = { ...ownAt, [id]: String(asked.at) };
    }
    const kept = await keepTheSetup(chrome, { days: { ...setUp.days, [id]: asked.day }, runs: { ...setUp.runs, [id]: asked.run }, ownAt });
    /* R250: the alarms follow the reports: one for each own time that is left. */
    if (parts.setTheOwnTimes) await parts.setTheOwnTimes(chrome, theOwnTimesOf(book, kept));
    return { saved: true };
  }

  if (asked.do === 'set-the-hour') {
    const wrong = parts.whyThatIsNotATimeOfDay(asked.at);
    if (wrong) return { wrong };
    /* R250: two runs may not share a time. */
    const taken = parts.whyThatRunTimeIsRefused && await parts.whyThatRunTimeIsRefused(chrome, 'morning', asked.at);
    if (taken) return { wrong: taken };
    const set = await parts.setTheHour(chrome, { at: asked.at, now });
    return { at: set };
  }

  /* R250: the evening time, saved like the morning one. */
  if (asked.do === 'set-a-run-time') {
    if (asked.which !== 'evening') return { wrong: 'Only the evening time is set here.' };
    const wrong = parts.whyThatRunTimeIsRefused && await parts.whyThatRunTimeIsRefused(chrome, asked.which, asked.at);
    if (wrong) return { wrong };
    const set = await parts.setARunTime(chrome, { which: asked.which, at: asked.at, now });
    return { at: set };
  }

  if (asked.do === 'stop') return inTheNightsOwnLine(async () => {
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
    /* Stop never tells Kartaan: nothing remembered from earlier platforms may linger or be sent later. */
    await chrome.storage.local.remove(THE_SYNC_FAILED);
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
    /* **N039: THE WINDOW THIS PRODUCT OPENED GOES TOO, never his own.** Only when a run really was going. */
    if (wasGoing && parts.closeOurWindow) await parts.closeOurWindow();
    return { stopped: wasGoing, was: (walk && walk.reportId) || '' };
  });

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
    await forgetTheSwitchedOff(chrome);
    const paused = await whatIsPaused(chrome);
    if (!paused) return { wrong: 'Nothing is paused, so there is nothing to resume.' };
    const said = await startASync(chrome, parts, { reportIds: paused.reportIds, day: paused.dataDate });
    if (said && said.started) await chrome.storage.local.remove(PAUSED);
    return said;
  }

  if (asked.do === 'clear-needs-you') {
    /* J016: "I placed these by hand." Only the days the panel showed him (named exactly, never a wildcard) are cleared AND marked as landed,
     * so the next night does not write them back. Not while a run is going: its own writes to the same lists could cross with this one. */
    const night = await theNight(chrome);
    if (night && !night.finishedAt) return { wrong: 'A run is going now. Press this again when it has finished.' };
    const named = (Array.isArray(asked.days) ? asked.days : []).map((one) => ({ reportId: String(one && one.reportId), dataDate: String(one && one.dataDate) }));
    const cleared = await clearNamedNeedsYouEntries(chrome, named);
    for (const one of cleared) await rememberLastLanded(chrome, one.reportId, one.dataDate);
    return { cleared: cleared.length };
  }

  return { wrong: `The panel asked for "${asked.do}", which is not something it may ask for.` };
}

/** The platforms still to run in the scheduled sync, each as its ticked reports. */
export const THE_QUEUE = THE_SCHEDULED_QUEUE;
/* **FLIPKART FIRST**, so its requests are made at the start of the scheduled sync --
 * Rumee's order (`D:\rumee-auto-sync\config.js:62-64`). */
export const PLATFORM_ORDER = Object.freeze(['flipkart', 'meesho', 'amazon']);

/**
 * Start the scheduled sync: its own list, one platform after another.
 *
 * **CONTROL'S RULING FOR A53 (`D:\Control\JOBS.md`)**, with the list replaced by his
 * decision B (A60): the timed list (`theTimedList`), plus the days already owed (the
 * sync adds those itself); one sync, one platform at a time, never side by side; a
 * platform that is signed out stops only itself.
 */
export async function startTheScheduledSync(chrome, parts, run = 'morning', at = null) {
  const { book } = parts;
  const setUp = await theSetup(chrome);
  const timed = theTimedListFor(book, setUp, run, at);
  /* Reports fetched for YESTERDAY although their setting is "today": the morning's fallback below. */
  const fallback = new Set();
  /* **R208 (Control, 7 Nov): A "TODAY" REPORT THAT DID NOT LAND IS FETCHED THE NEXT MORNING AS AN ORDINARY YESTERDAY REPORT.** A platform that cannot give today loses nothing. A report that
   * did land (its yesterday is in what landed) is not fetched again. */
  if (run === 'morning') {
    const landed = (await chrome.storage.local.get(LAST_LANDED))[LAST_LANDED] || {};
    const yesterday = theDayToFetch((parts.now || Date.now)());
    for (const id of theTimedList(book, setUp)) {
      if (theDayOf(setUp, id) === 'today' && theRunOf(setUp, id) !== 'morning' && !(landed[id] || []).includes(yesterday)) fallback.add(id);
    }
    timed.push(...fallback);
  }
  /* A report set to "today" is walked as a run of its own for today. The morning's yesterday reports stay the plain list, exactly as before. */
  const byPlatform = [];
  for (const platform of PLATFORM_ORDER) {
    const ofIt = timed.filter((id) => (book.recipes || {})[id] && thePlatformOf(book, id) === platform);
    const yesterday = ofIt.filter((id) => fallback.has(id) || theDayOf(setUp, id) === 'yesterday');
    const today = ofIt.filter((id) => !fallback.has(id) && theDayOf(setUp, id) === 'today');
    /* `today: false` says these are for yesterday whatever their setting, so a platform holding only fallbacks is not taken for a today run. */
    const forYesterday = yesterday.some((id) => fallback.has(id));
    if (yesterday.length) byPlatform.push(run === 'morning' && !forYesterday ? yesterday : { reportIds: yesterday, run, ...(forYesterday ? { today: false } : {}) });
    if (today.length) byPlatform.push({ reportIds: today, run, today: true });
  }
  /* **A RUN STARTED WHILE ANOTHER NIGHT IS STILL GOING ADDS TO THE QUEUE AND NEVER REPLACES IT (AJ13a review: the 4 pm run must not take the morning's remaining platforms).** What is
   * already queued is kept; a report already queued is not queued twice. */
  const going = await theNight(chrome);
  if (going && !going.finishedAt) {
    const queued = ((await chrome.storage.local.get(THE_QUEUE))[THE_QUEUE] || []).map((entry) => (Array.isArray(entry) ? entry : entry.reportIds));
    const already = new Set([...queued.flat(), ...(going.left || []), ...(going.doing ? [going.doing] : [])]);
    const added = byPlatform
      .map((entry) => (Array.isArray(entry) ? entry.filter((id) => !already.has(id))
        : { ...entry, reportIds: entry.reportIds.filter((id) => !already.has(id)) }))
      .filter((entry) => (Array.isArray(entry) ? entry : entry.reportIds).length);
    await chrome.storage.local.set({ [THE_QUEUE]: [...((await chrome.storage.local.get(THE_QUEUE))[THE_QUEUE] || []), ...added] });
    return { started: null, waiting: true, refused: [] };
  }
  await chrome.storage.local.set({ [THE_QUEUE]: byPlatform });
  const result = await startTheNextPlatform(chrome, parts);
  return result;
}

/** Start the next platform of the scheduled sync, if any is left. A sync already
 *  going keeps the queue, and the next platform starts when that one ends. */
export async function startTheNextPlatform(chrome, parts) {
  const left = [...((await chrome.storage.local.get(THE_QUEUE))[THE_QUEUE] || [])];
  const refused = [];
  const neverTried = [];
  while (left.length) {
    /* A Run now entry carries its days (A61, Job 5b); a timed one is the ids alone. */
    const entry = left.shift();
    const { reportIds, ...how } = Array.isArray(entry) ? { reportIds: entry } : entry;
    /* A timed entry is the ids alone; it is the only kind that keeps a few of the day's twenty for him. */
    const timed = Array.isArray(entry) || Boolean(how.run);
    // eslint-disable-next-line no-await-in-loop
    const night = await theNight(chrome);
    if (night && !night.finishedAt) return { started: null, waiting: true, refused };
    // eslint-disable-next-line no-await-in-loop
    await chrome.storage.local.set({ [THE_QUEUE]: left });
    // eslint-disable-next-line no-await-in-loop
    const said = await startASync(chrome, parts, {
      reportIds, ...how, run: how.run || (timed ? 'morning' : ''), timed, continuing: Boolean(parts.continuing),
    });
    if (said && said.started) return { started: reportIds, refused };
    refused.push({ reportIds, wrong: (said && said.wrong) || '' });
    /* **A PLATFORM REFUSED IN THE MIDDLE OF A SYNC IS REMEMBERED AS NOT FETCHED (AJ9 3b review).** Otherwise a later platform
     * that does start would end the sync and tell only what that one and the first one failed. Only for a sync already going. */
    if (parts.continuing) {
      // eslint-disable-next-line no-await-in-loop
      const before = (await chrome.storage.local.get(THE_SYNC_FAILED))[THE_SYNC_FAILED] || [];
      // eslint-disable-next-line no-await-in-loop
      await chrome.storage.local.set({ [THE_SYNC_FAILED]: [...new Set([...before, ...reportIds])] });
    }
    /* **KARTAAN'S NO (OR NO ANSWER) STOPS THE WHOLE QUEUE.** The next platform would only ask the same question and
     * get the same answer -- and the server counts every ask against a thirty-a-day allowance. */
    if (said && said.kartaanSaid) {
      /* **THE PLATFORMS NEVER TRIED ARE KEPT (neverTried), AND THE EARLIER PLATFORMS' FAILED LIST IS KEPT TOO (AJ9 3b).** The
       * one place that tells (`tellForASyncThatCannotContinue`) names both, so a report that did not get fetched is not
       * left without a word to him just because Kartaan said no to starting the next platform. */
      for (const rest of left) neverTried.push(...(Array.isArray(rest) ? rest : rest.reportIds));
      await chrome.storage.local.set({ [THE_QUEUE]: [] });
      break;
    }
  }
  return { started: null, refused, neverTried };
}

/**
 * **A WHOLE SYNC THAT CANNOT CONTINUE STILL TELLS ONCE (Control's follow-up, 2026-10-12).** Called after the next
 * platform was tried: when none started, none is waiting for a running night, and failed ids are still remembered
 * (the later platforms were refused for a reason other than Kartaan's no, or a pause/Stop, which both clear the
 * list), Kartaan is told with them, then the list is forgotten. Never throws, never changes any night's outcome;
 * the answer is written onto the earlier night if it is still the stored one.
 */
export async function tellForASyncThatCannotContinue(chrome, next, doneNight, tell) {
  try {
    if (!next || next.started || next.waiting || typeof tell !== 'function') return null;
    const held = (await chrome.storage.local.get(THE_SYNC_FAILED))[THE_SYNC_FAILED];
    if (held === undefined) return null;
    await chrome.storage.local.remove(THE_SYNC_FAILED);
    /* A platform that never started has fetched nothing, so every report of it is told as one that did not land (AJ9 3b). */
    const neverStarted = [...(next.refused || []).flatMap((one) => (Array.isArray(one.reportIds) ? one.reportIds : [])),
      ...(next.neverTried || [])];
    /* The night's end names the message, never the clock, so a restart sends the same id again (AJ9 review). */
    const said = await tell({
      failed: [...new Set([...held, ...neverStarted])], endedAt: doneNight && doneNight.finishedAt,
    });
    const toldKartaan = {
      startedAt: doneNight && doneNight.startedAt,
      finishedAt: doneNight && doneNight.finishedAt,
      told: Boolean(said && said.told),
      kind: String((said && said.kind) || 'unreachable'),
      said: String((said && said.said)
        || 'Kartaan could not be told this sync finished. The run still runs on its own schedule.'),
    };
    const now = await theNight(chrome);
    if (now && doneNight && now.startedAt === doneNight.startedAt && now.finishedAt === doneNight.finishedAt) {
      await chrome.storage.local.set({ [THE_NIGHT]: { ...now, toldKartaan } });
    }
    return toldKartaan;
  } catch (wrong) {
    return null;
  }
}

/**
 * Start a sync of these reports, for this day or yesterday.
 *
 * **ONE WAY IN FOR RUN NOW, THE HOURLY RE-CHECK AND THE SCHEDULED SYNC (A53)**, so
 * the three can never start a sync three different ways.
 */
export async function startASync(chrome, parts, asked) {
  /* **IN THE NIGHT'S OWN LINE, SO TWO STARTERS CANNOT BOTH SEE "NO NIGHT GOING" (review finding, 2026-10-05).**
   * The first starter's night is written before the second looks. The follow-up `carryOn` is outside the line,
   * because it takes its own turn in it. */
  let carryOnAfter = false;
  const said = await inTheNightsOwnLine(async () => {
    const outcome = await startASyncInTurn(chrome, parts, asked);
    carryOnAfter = Boolean(outcome && outcome.started);
    return outcome;
  });
  if (carryOnAfter) await parts.carryOn();
  return said;
}

/**
 * **A PAUSE OR A RE-CHECK KEPT BY THE 15 OCT BUILD MAY HOLD THE SWITCHED-OFF PAIR (A84, review).** They are taken out of what is kept, and a
 * record left with nothing is removed, so nothing keeps saying "Nothing is ticked" and a re-check of only the switched-off report never blocks the days behind it.
 */
async function forgetTheSwitchedOff(chrome) {
  const paused = (await chrome.storage.local.get(PAUSED))[PAUSED];
  if (paused && Array.isArray(paused.reportIds)) {
    const kept = paused.reportIds.filter((id) => !OFF_THE_TIMED_LIST.includes(id));
    if (!kept.length) await chrome.storage.local.remove(PAUSED);
    else if (kept.length !== paused.reportIds.length) await chrome.storage.local.set({ [PAUSED]: { ...paused, reportIds: kept } });
  }
  /* Read again here, not with the pause: the resume branch runs outside the night's own line, and a write made in between must not be overwritten. */
  const rechecks = (await chrome.storage.local.get(RECHECKS))[RECHECKS];
  if (rechecks && typeof rechecks === 'object') {
    const kept = Object.fromEntries(Object.entries(rechecks).filter(([, one]) => !(one && OFF_THE_TIMED_LIST.includes(one.reportId))));
    if (Object.keys(kept).length !== Object.keys(rechecks).length) await chrome.storage.local.set({ [RECHECKS]: kept });
  }
}

async function startASyncInTurn(chrome, parts, asked) {
  const { book, now = () => Date.now() } = parts;
  await forgetTheSwitchedOff(chrome);
  {
    /* **EVERY WAY A RUN STARTS COMES THROUGH HERE**: a resumed run, a queue kept by an older build and the hourly re-check carry ids saved
     * before the report was switched off (A84, review). */
    const reportIds = withTheListsTheyRead(book, [...new Set(asked.reportIds || [])].filter((id) => !OFF_THE_TIMED_LIST.includes(id)));
    const setUp = await theSetup(chrome);
    const night = await theNight(chrome);
    const wrong = whyItCannotBeStarted(book, { reportIds, panel: setUp.panel, night });
    if (wrong) return { wrong };
    /* **ONE DAY OR A STRETCH OF THEM (A53, his "add the box to input date range").**
     * Nothing in the boxes is yesterday, as it has always been. */
    const from = String(asked.from || '');
    const to = String(asked.to || asked.day || '');
    /* **R208 (D1005): TODAY IS ALLOWED WHEN EVERY REPORT ASKED FOR IS SET TO "TODAY"** -- the 6 pm returns, a re-check of them, or a seller's own choice. Never otherwise. */
    const asking = (asked.reportIds || []).filter((id) => !OFF_THE_TIMED_LIST.includes(id));
    const todayIsAllowed = asked.today !== false && asking.length > 0 && asking.every((id) => theDayOf(setUp, id) === 'today');
    let days = [];
    if (from && to) {
      const rangeWrong = whyThatRangeCannotBeFetched(from, to, now(), todayIsAllowed);
      if (rangeWrong) return { wrong: rangeWrong };
      days = theDaysBetween(from, to);
    } else if (from || to) {
      const one = to || from;
      const dayWrong = whyThatDayCannotBeFetched(one, now(), todayIsAllowed);
      if (dayWrong) return { wrong: dayWrong };
      days = [one];
    }
    if (!setUp.driveConnectedAt) {
      return {
        wrong: 'Your Google Drive is not connected yet, so anything fetched would have nowhere '
          + 'to go. Connect it first.',
      };
    }
    /* **KARTAAN IS ASKED LAST OF THE REFUSALS AND FIRST OF THE WRITES (plan jobs 30 and 48).** After every refusal
     * this file can make by itself, so a sync that could never have started does not spend one of the seller's
     * thirty asks a day; before the night is written, so a "no" leaves the walk and night records exactly as they
     * were. **ONLY A CLEAR YES, OR NO PASS SAVED, GOES ON** (`askMayFetch`). The same door serves Run now, resume,
     * the hourly re-check and the timed sync, so none of them can start a sync another could not. */
    const mayFetch = await askMayFetch(chrome, parts.fetch);
    if (!mayFetch.go) return { wrong: mayFetch.said, kartaanSaid: mayFetch.kind };
    /* **A NEW WHOLE SYNC STARTS WITH NO FAILED IDS REMEMBERED** (a list left by an abandoned sync is never sent).
     * The next platform of a sync already going (`asked.continuing`) keeps what the earlier ones left. */
    if (!asked.continuing) await chrome.storage.local.remove(THE_SYNC_FAILED);
    /* **A FINISHED NIGHT IS FILED BEFORE A NEW ONE WRITES OVER IT**, or Stop and then Run now inside the panel's
     * poll would lose that night's Flipkart spend from the day's count. */
    if (night && night.finishedAt) await rememberTheNight(chrome, { book });
    const kept = await theNights(chrome);
    const started = await parts.startTheNight(chrome, {
      doing: askingFirst(book, reportIds),
      listFrom: theListsRead(book, reportIds),
      mayAskFor: howManyItMaySpend(book, {
        reportIds, kept, night, now: now(), timed: Boolean(asked.timed),
      }),
      at: now(),
      openAt: whereToStartFrom(book, reportIds, setUp.panel),
      dataDate: days.length ? days[days.length - 1] : (todayIsAllowed ? theDay(now()) : theDayToFetch(now())),
      /* Which timed run this is (R208), so a morning failure is known to be the morning's. */
      run: String(asked.run || ''),
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
    return {
      started: (started && started.left) || [],
      /* Said when the check could not be made, so the seller reads that it was skipped and why. */
      ...(mayFetch.asked ? {} : { note: mayFetch.said }),
    };
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

/**
 * **THE NIGHT'S EVENTS, IN ORDER AND IN PLAIN WORDS (AJ9 piece 6).** Built from what the night already holds
 * (start, the idle wait, each report with its own sentence, the end, and what Kartaan was told), so there is no second
 * record to drift from the first. Words only: no pass, no customer data. Answers `[{ at, words }]`, oldest first.
 */
export function theNightsEvents(night, nameOf = (id) => id) {
  if (!night || !night.startedAt) return [];
  const events = [{ at: night.startedAt, words: 'The run started.' }, { at: night.startedAt, words: theIdleLine(night) }];
  for (const one of night.done || []) {
    events.push({
      at: one.at || night.startedAt,
      words: `${nameOf(one.reportId)}: ${whatThatStateIsCalled(one.state)}${one.say ? ` -- ${one.say}` : ''}`,
    });
  }
  if (night.doing) events.push({ at: null, words: `Fetching now: ${nameOf(night.doing)}.` });
  if (night.finishedAt) {
    events.push({ at: night.finishedAt, words: `The run ended${night.why ? `: ${night.why}` : '.'}` });
    if (night.toldKartaan && night.toldKartaan.said) {
      events.push({ at: night.finishedAt, words: `Kartaan: ${night.toldKartaan.said}` });
    }
  }
  return events;
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
    partial: 'partly fetched',
    fetching: 'fetching now',
    waiting: 'waiting',
    'nothing-to-fetch': 'skipped',
    'not-asked': 'not asked (allowance used up)',
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
  const failed = done.filter((one) => one.state === 'failed' || one.state === 'partial');
  const needsYou = done.filter((one) => one.state === 'needs-you');
  const notAsked = done.filter((one) => one.state === 'not-asked');
  const failures = failed.length
    ? `: ${failed.map((one) => `${one.reportId} (${String(one.say || '').slice(0, 60)})`).join(', ')}`
    : '';
  const byHand = needsYou.length
    ? ` ${needsYou.map((one) => `${one.reportId} for ${one.dataDate}`).join(', ')} `
      + `${needsYou.length === 1 ? 'needs' : 'need'} you: fetch by hand.`
    : '';
  const unasked = notAsked.length
    ? ` ${notAsked.length} day${notAsked.length === 1 ? ' was' : 's were'} not asked for (the day's allowance was used up) and `
      + `${notAsked.length === 1 ? 'is' : 'are'} still owed.`
    : '';
  return {
    title: failed.length || needsYou.length || notAsked.length
      ? 'Kartaan AutoSync: sync finished with problems' : 'Kartaan AutoSync: sync finished',
    message: `${landed} landed, ${failed.length} failed${failures}.${byHand}${unasked}`
      + `${night.toldKartaan && night.toldKartaan.said ? ` ${night.toldKartaan.said}` : ''}`,
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
  /* R250 (his look, D1034): the days that need him are in the amber box at the top, not repeated here. */
  if (!stands.night) {
    return { how: 'idle', said: 'No runs yet. Tick what you want and press Run now.' };
  }
  const failed = stands.night.done.filter((one) => one.state === 'failed' || one.state === 'partial').length;
  if (failed) {
    return {
      how: 'wrong',
      said: `The last run finished with ${failed} report${failed === 1 ? '' : 's'} that failed.`,
    };
  }
  const notAsked = stands.night.done.filter((one) => one.state === 'not-asked').length;
  if (notAsked) {
    return {
      how: 'setup',
      said: `The last run finished, but ${notAsked} day${notAsked === 1 ? ' was' : 's were'} not asked for `
        + 'because the Flipkart allowance for the day was used up. They are still owed.',
    };
  }
  return {
    how: 'done',
    said: `The last run finished at ${inWordsWhen(stands.night.finishedAt)}.`,
  };
}

/* ---------------------------------------------------------------- light or dark (R250, his look D1034) */
const THEME_KEY = 'kartaan-autosync-theme';

/** What the seller chose: 'light', 'dark', or 'system' (the computer's own setting, the default). */
export function theThemeChosen() {
  try {
    const kept = globalThis.localStorage && globalThis.localStorage.getItem(THEME_KEY);
    return kept === 'light' || kept === 'dark' ? kept : 'system';
  } catch (storageRefused) {
    return 'system'; // a browser that will not let a page keep a setting: the computer's own setting, as if nothing was chosen
  }
}

/** Put the colours on: the ERP's own `dark` class on the body, switched by the choice or, for 'system', by the computer's setting. Answers whether it is dark. */
export function applyTheTheme(choice, doc = globalThis.document, match = globalThis.matchMedia) {
  const dark = choice === 'dark' || (choice !== 'light' && Boolean(match && match('(prefers-color-scheme: dark)').matches));
  doc.body.classList.toggle('dark', dark);
  return dark;
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
  /* R250 (drawing row "Version line"): the version sits in the top bar, always. Filled in by `showHowItStands`. */
  parts.version = make('span', `${OURS}version`, '');
  put(bar, parts.version);
  /* R250 (his approved drawing, D968): the one-time set-up and the run pass sit behind a gear in the top bar once set-up is done. */
  /* R250 (his look 2, D1035): a day/night switch beside Settings, always on the panel face. It flips light <-> dark and is remembered; Settings keeps the three-way choice. */
  parts.modeSwitch = make('button', `${OURS}gear ${OURS}modeSwitch`, '');
  parts.modeSwitch.type = 'button';
  put(bar, parts.modeSwitch);
  parts.gear = make('button', `${OURS}gear`, '⚙ Settings');
  parts.gear.type = 'button';
  parts.gear.setAttribute('aria-expanded', 'false');
  parts.gear.hidden = true;
  parts.gear.setAttribute('aria-label', 'Settings');
  put(bar, parts.gear);
  put(page, bar);

  const body = make('div', `${OURS}body`);
  put(page, body);

  /* ----------------------------------------------- PN2a: needs you, at the very top */
  parts.doing = doing;
  parts.needs = make('section', `${OURS}needs`);
  parts.needs.hidden = true;
  put(body, parts.needs);

  /* ----------------------------------------------------------- what is happening: the status line, drawn under the run controls (below) */
  parts.banner = make('div', `${OURS}banner`);
  /* **"A NEWER VERSION IS OUT" (his ask, 2026-10-20; Kartaan Click's way).** Hidden until the repository says so. */
  parts.update = make('div', `${OURS}banner ${OURS}banner--setup`);
  parts.update.hidden = true;
  put(body, parts.update);

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
  /* R250 (his look, D1034): Run now and Stop sit beside the From / To dates, in one row. */
  put(whichDays, parts.actions);
  put(body, parts.said);

  /* ----------------------------------------------- PN2b: instant download, one report, ticks untouched */
  const instant = make('div', `${OURS}row`);
  parts.instantPlatform = make('select', 'k-control');
  for (const platform of THROUGH_THE_BROWSER) {
    const option = make('option', '', CALLED[platform] || platform);
    option.value = platform;
    put(parts.instantPlatform, option);
  }
  parts.instantReport = make('select', 'k-control');
  parts.instantRun = make('button', 'k-button k-button--ordinary', 'Run');
  parts.instantRun.type = 'button';
  const instantHint = make('span', `${OURS}hint`, 'i');
  instantHint.title = 'Fetches just this one report for the days above. Your ticks are not touched.';
  put(instant, make('span', `${OURS}label`, 'Instant download'), parts.instantPlatform, parts.instantReport, parts.instantRun, instantHint);
  put(body, instant);
  put(body, parts.banner);

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
  parts.settings = make('div', `${OURS}settings`);
  put(parts.settings, parts.setup);
  put(body, parts.settings);

  /* ------------------------------------------------------ the run pass, optional
   * **NOT PART OF "SET UP, ONCE", AND NOT HIDDEN WHEN THAT IS DONE.** Nothing is refused for lacking it -- a sync
   * without one goes ahead, saying the check was not made -- so it must stay where it can be added later. A
   * password box, so a pasted pass is not read over his shoulder, and emptied after Save so it is not left in the
   * page. */
  parts.kartaan = make('section', `${OURS}card`);
  put(parts.kartaan, make('h2', `${OURS}title`, 'Kartaan run pass'));
  const passRow = make('div', `${OURS}row`);
  parts.runPass = make('input', 'k-control');
  parts.runPass.type = 'password';
  parts.runPass.autocomplete = 'off';
  parts.runPass.placeholder = 'paste the run pass';
  parts.saveRunPass = make('button', 'k-button k-button--ordinary', 'Save');
  parts.saveRunPass.type = 'button';
  parts.runPassState = make('span', `${OURS}state`, '');
  put(passRow, make('span', `${OURS}label`, 'Run pass'), parts.runPass, parts.saveRunPass, parts.runPassState);
  put(parts.kartaan, passRow);
  parts.kartaanSaid = make('p', `${OURS}note`, '');
  put(parts.kartaan, make('p', `${OURS}note`,
    'Copy it from Kartaan\'s page. With it saved, each sync first asks Kartaan whether it may run, and Kartaan is '
    + 'told when a sync ends. Without it, syncs run as before and say the check was not made.'));
  put(parts.kartaan, parts.kartaanSaid);
  put(parts.settings, parts.kartaan);

  /* R250 (his look, D1034): Light, Dark or Same as computer, remembered. */
  const look = make('section', `${OURS}card`);
  parts.theme = make('select', 'k-control');
  for (const [value, label] of [['system', 'Same as computer'], ['light', 'Light'], ['dark', 'Dark']]) {
    const option = make('option', '', label);
    option.value = value;
    put(parts.theme, option);
  }
  parts.theme.value = theThemeChosen();
  parts.theme.setAttribute('aria-label', 'Light or dark');
  const chooseTheTheme = (choice) => {
    try { globalThis.localStorage.setItem(THEME_KEY, choice); } catch (storageRefused) { /* not kept this time; it still applies now */ }
    applyTheTheme(choice);
    parts.theme.value = choice;
    parts.showMode();
  };
  parts.theme.addEventListener('change', () => chooseTheTheme(parts.theme.value));
  /* What the switch says is what pressing it does: from dark it says Light, from light it says Dark. */
  parts.showMode = () => {
    const dark = String((globalThis.document && globalThis.document.body.className) || '').includes('dark');
    parts.modeSwitch.textContent = dark ? '☀ Light' : '☾ Dark';
    parts.modeSwitch.title = dark ? 'Switch to the light colours' : 'Switch to the dark colours';
  };
  parts.modeSwitch.addEventListener('click', () => chooseTheTheme(String((globalThis.document && globalThis.document.body.className) || '').includes('dark') ? 'light' : 'dark'));
  parts.showMode();
  const lookRow = make('div', `${OURS}row`);
  put(lookRow, make('span', `${OURS}label`, 'Light or dark'), parts.theme);
  put(look, lookRow);
  put(parts.settings, look);

  /* ----------------------------------------------------------- your AI (AD1, D818)
   * **OFF UNTIL HE TURNS IT ON, and only here.** With it on, his AI app can read how the reports stand and ask for a run through the Kartaan
   * Bridge helper; every ask waits for the computer to be left alone for 3 minutes. */
  parts.ai = make('section', `${OURS}card`);
  const aiRow = make('div', `${OURS}row`);
  parts.aiSwitch = make('button', 'k-button k-button--ordinary', 'AI may run AutoSync: Off');
  parts.aiSwitch.type = 'button';
  parts.aiState = make('span', `${OURS}state`, '');
  put(aiRow, parts.aiSwitch, parts.aiState);
  put(parts.ai, aiRow);
  put(parts.ai, make('p', `${OURS}note`,
    'With this on, your AI app (needs the Kartaan AI helper installed) can read how your reports stand and ask AutoSync to fetch reports for '
    + 'dates it names. It cannot do anything else, and every ask waits until you have left the computer alone for 3 minutes.'));
  parts.aiNote = make('p', `${OURS}note`, '');
  parts.aiAsks = make('div', `${OURS}note`, '');
  put(parts.ai, parts.aiNote, parts.aiAsks);

  /* --------------------------------------------------------------- platforms */
  parts.platforms = make('div', `${OURS}tabs`);
  parts.chosen = 'flipkart';
  put(body, parts.platforms);

  /* R250 (drawing rows "Last run table", "Flipkart requests left today", "What to fetch", "What this cannot fetch"): ONE card for the chosen platform. */
  const platformCard = make('section', `${OURS}card`);
  parts.log = make('div', `${OURS}run`);
  put(platformCard, parts.log);

  /* ------------------------------------------------------- Flipkart's twenty: one line, Flipkart's view only */
  const allowance = make('div', `${OURS}row`);
  parts.allowance = make('span', `${OURS}figure`, '');
  parts.allowanceNote = make('span', `${OURS}hint`, 'i');
  parts.allowanceNote.tabIndex = 0;
  put(allowance, make('span', `${OURS}label`, 'Flipkart requests left today'), parts.allowance, parts.allowanceNote);
  parts.allowanceCard = allowance;
  put(platformCard, allowance);

  /* ----------------------------------------------------------------- reports (and, at their end, what cannot be fetched) */
  parts.foldTitle = make('summary', '', 'What to fetch');
  parts.selectAll = make('button', 'k-button k-button--quiet k-button--small', 'Tick all platforms');
  parts.selectAll.type = 'button';
  parts.reports = make('div', `${OURS}list`);
  parts.cannot = make('div', `${OURS}list`);
  parts.fold = make('details');
  put(parts.fold, parts.foldTitle, parts.selectAll, parts.reports, parts.cannot);
  put(platformCard, parts.fold);
  put(body, platformCard);

  /* ------------------------------------------- the three buttons under the platform: AI, Run times, How this works */
  const buttons = make('div', `${OURS}three`);
  const drawers = [];
  const addDrawer = (button, section) => {
    section.hidden = true;
    drawers.push([button, section]);
    button.type = 'button';
    button.setAttribute('aria-expanded', 'false');
    button.addEventListener('click', () => {
      const open = section.hidden;
      for (const [other, one] of drawers) { one.hidden = true; other.setAttribute('aria-expanded', 'false'); }
      section.hidden = !open;
      button.setAttribute('aria-expanded', String(open));
    });
    put(buttons, button);
  };
  const threeButton = (title) => {
    const button = make('button', `k-button k-button--ordinary ${OURS}drawerButton`);
    const small = make('small', '', '');
    put(button, make('b', '', title), small);
    return [button, small];
  };
  [parts.aiButton, parts.aiButtonState] = threeButton('AI may run it');
  [parts.timesButton, parts.timesButtonState] = threeButton('Run times');
  [parts.helpButton, parts.helpButtonState] = threeButton('How this works');
  parts.helpButtonState.textContent = '›';
  put(body, buttons);

  /* -------------------------------------------------------------- the clock */
  const clock = make('section', `${OURS}card`);
  put(clock, make('h2', `${OURS}title`, 'When each report is fetched by itself'));
  /* R250: the three daily runs, each changeable, each with its why. The morning one keeps its original boxes (`hour`, `saveHour`, `hourState`). */
  const runRow = (label, time, save, fetches, why) => {
    const row = make('div', `${OURS}runRow`);
    const line = make('div', `${OURS}row`);
    put(line, make('span', `${OURS}label`, label), time, save);
    put(row, line, make('p', `${OURS}note`, fetches), make('p', `${OURS}note`, why));
    return row;
  };
  parts.hour = make('input', 'k-control');
  parts.hour.type = 'time';
  parts.hour.setAttribute('aria-label', 'Morning run time');
  parts.saveHour = make('button', 'k-button k-button--ordinary', 'Save');
  parts.saveHour.type = 'button';
  parts.hourState = make('p', `${OURS}note`, '');
  put(clock, runRow('Morning run', parts.hour, parts.saveHour, 'Fetches yesterday, every report on this run.',
    'Why 8:00 by default: yesterday is complete by then, and the ERP is up to date before your working day.'));
  const otherRun = (which, label, fetches, why) => {
    parts[`${which}Time`] = make('input', 'k-control');
    parts[`${which}Time`].type = 'time';
    parts[`${which}Time`].setAttribute('aria-label', `${label} time`);
    parts[`${which}Save`] = make('button', 'k-button k-button--ordinary', 'Save');
    parts[`${which}Save`].type = 'button';
    parts[`${which}Save`].addEventListener('click', () => doing.setARunTime && doing.setARunTime(which, parts[`${which}Time`].value));
    put(clock, runRow(label, parts[`${which}Time`], parts[`${which}Save`], fetches, why));
  };
  otherRun('evening', 'Evening run', 'Fetches the reports that are not ready in the morning.',
    'Why 4 pm by default: these reports are ready by then.');
  put(clock, make('p', `${OURS}note`, 'Own time: any report can have a time of its own, set below under "Which report runs when". The returns reports are on 18:00 and the day Today until you change them.'));
  put(clock, parts.hourState);
  parts.clash = make('p', `${OURS}clash`, '');
  parts.clash.hidden = true;
  put(clock, parts.clash);
  put(clock, make('p', `${OURS}note`, 'Retry: a report that failed in the morning, evening or an own-time run is tried again every hour, up to 3 tries, and never spends more Flipkart requests than the day\'s 20 allow. That is not a setting.'));
  put(clock, make('p', `${OURS}note`,
    'This is the clock inside your browser. It is NOT the clock the scheduled sync in your '
    + 'own GitHub account runs on -- that one is set there, and changing this does not move '
    + 'it. At the time you save here, this extension fetches its own list by itself, '
    + 'one platform after the other. Chrome has to be open and the machine awake.'));
  /* **WHAT THE TIMED SYNC WILL FETCH, SAID -- HIS DECISION B (A60).** The ticks above
   * are for Run now only and never change it. */
  parts.timed = make('p', `${OURS}note`, '');
  put(clock, parts.timed);

  /* --------------------------------------------- each report's day and run (R208), folded inside the run times */
  /* R250 (drawing: "Which report runs when"): folded by default; its rows are in order (platform, run, name). */
  const timesFold = make('details', `${OURS}fold`);
  parts.timesFoldTitle = make('summary', `${OURS}foldHead`, 'Which report runs when');
  put(timesFold, parts.timesFoldTitle);
  parts.scheduleList = make('div', `${OURS}list ${OURS}schedGrid`);
  put(timesFold, parts.scheduleList);
  put(timesFold, make('p', `${OURS}note`,
    'Yesterday is the usual. The returns are on their own time (18:00) for today. Platforms often do not have the numbers for today yet, so a report set to today may land blank or partial.'));
  put(clock, timesFold);
  addDrawer(parts.timesButton, clock);
  put(body, clock);
  addDrawer(parts.aiButton, parts.ai);
  put(body, parts.ai);

  /* ------------------------------------------------------- what happened, in order (AJ9 piece 6) */
  /* R250 (drawing: "off panel"): NOT drawn. It is still worked out here (`showTheEvents` fills this list, as the drawing says) and the full words stay in the run log in Drive. */
  parts.events = make('ul', `${OURS}helpSteps`);

  /* ------------------------------------------------------------- the manual */
  /* **THE LONGER ANSWER, AND IT IS ON THE SAME PAGE AS THE THING.** His
   * instruction, 2026-09-11: a tooltip beside the control, a manual for somebody
   * who wants to be shown, and a developer's document for whoever works on this
   * next. **The words are `manual.js`'s, never invented here** -- the same rule
   * the failure reasons follow, so there is one place to correct and not two. */
  const help = make('section', `${OURS}card`);
  put(help, make('h2', `${OURS}title`, 'Questions'));
  for (const entry of MANUAL) {
    const one = make('details', `${OURS}help`);
    put(one, make('summary', `${OURS}helpTitle`, `${entry.label} -- ${entry.crux}`));
    const steps = make('ul', `${OURS}helpSteps`);
    for (const said of entry.steps) put(steps, make('li', '', said));
    put(one, steps);
    for (const said of entry.more || []) put(one, make('p', `${OURS}note`, said));
    put(help, one);
  }
  /* R250 (drawing): "Read more" on docs.kartaan.com. That site is planned, so it is said as plain text, not a link that goes nowhere. */
  const docs = make('a', '', 'Read more on docs.kartaan.com');
  docs.href = 'https://docs.kartaan.com';
  docs.target = '_blank';
  docs.rel = 'noopener';
  put(help, put(make('p', `${OURS}note`), docs));
  parts.help = help;
  addDrawer(parts.helpButton, help);
  put(body, help);
  parts.body = body;

  /* **WHICH VERSION THIS IS, ALWAYS (his ask, 2026-10-20, D425).** Until this line the number showed only
   * inside "A newer version is out" and only when an update existed; otherwise it took a visit to
   * chrome://extensions. Filled in by `showHowItStands` from the version the extension itself reports. */

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
  parts.saveRunPass.addEventListener('click', () => doing.saveTheRunPass && doing.saveTheRunPass(parts.runPass.value));
  parts.aiSwitch.addEventListener('click', () => doing.aiSwitch && doing.aiSwitch(!parts.aiOn));
  parts.runNow.addEventListener('click', () => doing.runNow(
    whatIsTicked(parts), parts.from.value, parts.to.value,
  ));
  parts.stop.addEventListener('click', () => doing.stop());
  parts.instantPlatform.addEventListener('change', () => parts.lastStands && fillTheInstantRow(parts, parts.lastStands));
  parts.instantRun.addEventListener('click', () => parts.instantReport.value && doing.runNow && doing.runNow([parts.instantReport.value], parts.from.value, parts.to.value));
  parts.resume.addEventListener('click', () => doing.resume && doing.resume());
  parts.saveHour.addEventListener('click', () => doing.setTheHour(parts.hour.value));
  parts.selectAll.addEventListener('click', () => tickAll(parts));
  parts.gear.addEventListener('click', () => {
    parts.settings.hidden = !parts.settings.hidden;
    parts.gear.setAttribute('aria-expanded', String(!parts.settings.hidden));
  });

  /* What is ticked, kept here rather than read back off the page every poll. */
  parts.ticked = new Set();
  /* The report rows that are open in the last-run table, kept across the two-second redraws. */
  parts.opened = new Set();
  parts.boxes = new Map();
  parts.groups = new Map();
  parts.states = new Map();
  /* One tick-all button per platform, so a seller picks a whole platform in one press. */
  parts.platformTicks = new Map();
  /* **EVERY CHANGE OF TICKS IS SAVED**, so the panel opens with them again. They
   * are for Run now only; the timed sync keeps its own list (A60). */
  parts.ticksChanged = () => {
    showWhatIsTicked(parts);
    if (parts.lastStands) showThePlatforms(parts, parts.lastStands);
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
  parts.selectAll.textContent = allOn([...parts.boxes.keys()]) ? 'Untick all platforms' : 'Tick all platforms';
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
  if (parts.ticksChanged) parts.ticksChanged();
}

/**
 * Put what the worker said onto the page.
 *
 * **NOTHING IS BUILT AGAIN THAT DOES NOT HAVE TO BE.** The report rows are built
 * once, the first time a list arrives, and only their state changes after that
 * -- so a tick a seller made two seconds ago is still there.
 */
/** PN2a: the small download arrow on the newer-version button (a plain character, so it needs no image). */
function downloadIcon() {
  const arrow = make('span', '', '⬇ ');
  arrow.setAttribute('aria-hidden', 'true');
  return arrow;
}

/** PN2a: the amber box at the very top: one row per report-day he has to fetch by hand. Rebuilt only when the list changes, so a press is never lost to a redraw. */
function showTheNeedsYou(parts, list) {
  const key = JSON.stringify(list.map((one) => [one.reportId, one.dataDate, (one.triedOn || []).length, one.name, one.folder]));
  parts.needs.hidden = !list.length;
  if (parts.needsKey === key) return;
  parts.needsKey = key;
  parts.needs.textContent = '';
  if (!list.length) return;
  const place = (days) => parts.doing && parts.doing.clearNeedsYou && parts.doing.clearNeedsYou(days);
  /* R250 (drawing + his 8 Nov "expand collapse"): folded by default, so 104 rows are one line with the count. Opened, ONE ROW PER REPORT-DAY, each with its own "I placed it", in order (platform, report, date), scrolling inside the box. What is open is kept across the two-second redraws, for this visit only. */
  const outer = make('details', `${OURS}fold`);
  outer.open = Boolean(parts.needsOpen);
  outer.addEventListener('toggle', () => { parts.needsOpen = outer.open; });
  const hint = make('span', `${OURS}hint`, 'i');
  hint.title = 'AutoSync could not fetch these. Download each one yourself from the platform, put it in your Kartaan folder in Drive, inside that report\'s own folder (named on its row), then press I placed it. Nothing is asked for again after that.';
  const head = make('summary', `${OURS}foldHead`);
  put(head, make('span', `${OURS}count`, String(list.length)), make('span', `${OURS}title`, 'Needs you: download by hand'), hint);
  put(outer, head);
  if (list.length > 1) {
    const all = make('button', 'k-button k-button--main', 'I placed all');
    all.type = 'button';
    all.addEventListener('click', () => place(list.map((one) => ({ reportId: one.reportId, dataDate: one.dataDate }))));
    put(outer, all);
  }
  const order = (name) => { const at = PLATFORM_NAMES_IN_ORDER.indexOf(name); return at < 0 ? PLATFORM_NAMES_IN_ORDER.length : at; };
  const groups = new Map();
  for (const one of list) {
    if (!groups.has(one.reportId)) groups.set(one.reportId, []);
    groups.get(one.reportId).push(one);
  }
  const byReport = [...groups.values()].sort((a, b) => order(a[0].platformName) - order(b[0].platformName)
    || String(a[0].name || a[0].reportId).localeCompare(String(b[0].name || b[0].reportId)));
  const rows = make('div', `${OURS}needsList`);
  for (const days of byReport) {
    days.sort((a, b) => String(a.dataDate).localeCompare(String(b.dataDate)));
    put(rows, make('div', `${OURS}needsGroup`,
      `${days[0].platformName || ''} · ${days[0].name || days[0].reportId} -- ${days.length} day${days.length === 1 ? '' : 's'}`));
    for (const one of days) {
      const tries = (one.triedOn || []).length;
      const row = make('div', `${OURS}needsRow`);
      const where = one.folder ? ` Put it in: ${one.folder}` : '';
      const button = make('button', 'k-button k-button--ordinary', 'I placed it');
      button.type = 'button';
      button.addEventListener('click', () => place([{ reportId: one.reportId, dataDate: one.dataDate }]));
      const words = make('div');
      put(words, make('b', '', one.dataDate),
        make('div', `${OURS}note`, `${tries ? `tried ${tries} time${tries === 1 ? '' : 's'}` : 'too old for AutoSync to fetch'}.${where}`));
      put(row, words, button);
      put(rows, row);
    }
  }
  put(outer, rows);
  put(parts.needs, outer);
}

/* R250: the platform names in the order they are shown, wherever a list is sorted by platform. */
const PLATFORM_NAMES_IN_ORDER = PLATFORM_ORDER.map((id) => CALLED[id] || id);

function showTheUpdate(parts, update) {
  if (!parts.update) return;
  const out = Boolean(update && update.updateAvailable);
  parts.update.hidden = !out;
  parts.update.textContent = '';
  if (!out) return;
  put(parts.update, make('span', '',
    `A newer version is out: ${update.latest} (this one is ${update.installed}).${update.notes ? ` ${update.notes}` : ''} `));
  if (update.url) {
    const link = make('a', 'k-button k-button--main');
    put(link, downloadIcon(), make('span', '', `Download ${update.latest}`));
    link.href = update.url;
    link.target = '_blank';
    link.rel = 'noopener';
    put(parts.update, link);
  }
}

export function showHowItStands(parts, stands) {
  parts.showMode();
  const banner = whatTheBannerSays(stands);
  parts.banner.className = `${OURS}banner ${OURS}banner--${banner.how}`;
  /* R250 (drawing: ONE status line, "Ready. Next timed run wakes ..."): a quiet panel also says when the next timed run wakes. */
  const wakes = whenItNextWakes(stands.clock || null);
  parts.banner.textContent = banner.how === 'idle' ? `Ready. ${wakes}` : banner.how === 'done' ? `${banner.said} ${wakes}` : banner.said;
  showTheUpdate(parts, stands.update);
  if (parts.version) {
    const installed = stands.update && stands.update.installed;
    parts.version.textContent = installed ? `AutoSync ${installed}` : '';
  }
  if (parts.resume) parts.resume.hidden = !stands.paused;
  showTheNeedsYou(parts, stands.needsYou || []);
  if (parts.aiSwitch) {
    const ai = stands.ai || { on: false, note: '', asks: [] };
    parts.aiOn = Boolean(ai.on);
    parts.aiSwitch.textContent = `AI may run AutoSync: ${ai.on ? 'On' : 'Off'}`;
    parts.aiButtonState.textContent = ai.on ? 'On' : 'Off';
    parts.aiState.textContent = ai.on ? (ai.connected ? 'helper connected' : 'waiting for the helper') : '';
    parts.aiNote.textContent = ai.note || '';
    parts.aiAsks.textContent = (ai.asks || []).map((one) => one.panel_line).join('\n');
  }

  /* R250 (drawing): until Drive and the panel name are set the panel shows ONLY the set-up steps and no gear; after that Set up (done) and the password are behind the gear, closed on every visit. */
  const setUpDone = Boolean(stands.setUp.driveConnectedAt && stands.setUp.panel);
  parts.body.classList.toggle(`${OURS}pre`, !setUpDone);
  parts.gear.hidden = !setUpDone;
  if (parts.setUpDone !== setUpDone) {
    parts.setUpDone = setUpDone;
    parts.settings.hidden = setUpDone;
    parts.gear.setAttribute('aria-expanded', 'false');
  }
  parts.driveState.textContent = stands.setUp.driveConnectedAt
    ? `connected ${inWordsWhen(stands.setUp.driveConnectedAt)}`
    : (stands.setUp.driveSaid || 'not connected yet');
  if (document.activeElement !== parts.panelName) {
    parts.panelName.value = stands.setUp.panel;
  }
  parts.panelState.textContent = stands.setUp.panel ? 'saved' : 'not set yet';
  if (parts.runPassState) {
    const kartaan = stands.kartaan || { saved: false, last: null };
    parts.runPassState.textContent = kartaan.saved ? 'saved' : 'not saved';
    /* R160: a "no run pass is saved" line is not shown beside a pass that is saved now -- it was true when said, and is not now. */
    const stale = kartaan.saved && kartaan.last && kartaan.last.said.includes('no run pass is saved');
    parts.kartaanSaid.textContent = kartaan.last && kartaan.last.said && !stale
      ? `Kartaan, ${inWordsWhen(kartaan.last.at)}: ${kartaan.last.said}` : '';
  }

  const going = Boolean(stands.night && !stands.night.finishedAt);
  parts.runNow.disabled = going || !stands.setUp.done;
  parts.stop.disabled = !going;
  parts.instantRun.disabled = parts.runNow.disabled;
  if (parts.timed) parts.timed.textContent = (stands.timed && stands.timed.said) || '';

  /* ------------------------------------------------------------- platforms */

  /* ----------------------------------------------------- Flipkart's twenty */
  parts.allowance.textContent = `${stands.flipkart.leftToday} of ${stands.flipkart.allowedADay}`;
  parts.allowanceNote.title
    = `${stands.flipkart.askedForToday} used today. Only Flipkart's orders and payments `
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
    parts.groups.clear();
    /* **GROUPED BY PLATFORM, EACH WITH ITS OWN TICK-ALL -- HIS ASK, 2026-09-16.** A sync
     * runs one platform at a time, so this is also how a seller picks a sync's worth of
     * reports in one press. */
    const platforms = [...new Set(stands.reports.map((one) => one.platform))];
    for (const platform of platforms) {
      const named = CALLED[platform] || platform;
      const ofThisPlatform = stands.reports.filter((one) => one.platform === platform);
      const group = make('div');
      parts.groups.set(platform, group);
      put(parts.reports, group);
      const heading = make('div', `${OURS}platform-group`);
      const tickThese = make('button', 'k-button k-button--ordinary', `Tick all ${named}`);
      tickThese.type = 'button';
      tickThese.addEventListener('click', () => {
        const nowOn = tickAllOf(parts, ofThisPlatform.map((one) => one.id));
        tickThese.textContent = `${nowOn ? 'Untick' : 'Tick'} all ${named}`;
      });
      put(heading, make('span', `${OURS}report-name`, named), tickThese);
      put(group, heading);
      parts.platformTicks.set(platform, tickThese);
      parts.platformIds.set(platform, ofThisPlatform.map((one) => one.id));
      for (const one of ofThisPlatform) {
        buildOneReportRow(parts, stands, one, group);
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
  showThePlatforms(parts, stands);
  showTheRestOfIt(parts, stands);
}

/** PN2b: the three platform buttons, and only the chosen platform's own tick list, requests line and last run below them. */
function showThePlatforms(parts, stands) {
  parts.lastStands = stands;
  const tickable = (platform) => (parts.platformIds.get(platform) || [])
    .filter((id) => parts.boxes.get(id) && !parts.boxes.get(id).disabled);
  const ticked = (platform) => tickable(platform).filter((id) => parts.ticked.has(id)).length;
  parts.platforms.textContent = '';
  for (const one of stands.platforms) {
    const waiting = (stands.needsYou || []).filter((day) => day.platformName === one.name).length;
    const button = make('button', `k-button k-button--ordinary ${OURS}tab${one.id === parts.chosen ? ` ${OURS}tab--chosen` : ''}`);
    button.type = 'button';
    const top = make('span', `${OURS}tabTop`);
    put(top, make('b', '', one.name));
    if (waiting) put(top, make('span', `${OURS}count`, String(waiting)));
    put(button, top);
    put(button, make('small', '', `${ticked(one.id)} ticked${one.ready ? '' : ' \u00B7 not ready'}${one.lastRun ? ` \u00B7 last run ${inWordsWhen(one.lastRun.finishedAt)}: ${one.lastRun.landed} fetched, ${one.lastRun.failed} failed` : ' \u00B7 never run'}`));
    button.addEventListener('click', () => { parts.chosen = one.id; showHowItStands(parts, parts.lastStands); });
    put(parts.platforms, button);
  }
  for (const [platform, group] of parts.groups) group.hidden = platform !== parts.chosen;
  parts.allowanceCard.hidden = parts.chosen !== 'flipkart';
  if (parts.cannotRows) for (const [platform, row] of parts.cannotRows) row.hidden = platform !== parts.chosen;
  parts.foldTitle.textContent = `What to fetch \u00B7 ${ticked(parts.chosen)} of ${tickable(parts.chosen).length} ticked`;
  fillTheInstantRow(parts, stands);
}

/** PN2b: the instant-download row lists the chosen platform's reports that can be fetched on their own. */
function fillTheInstantRow(parts, stands) {
  const mine = stands.reports.filter((one) => one.platform === parts.instantPlatform.value && one.canBeFetched && !one.fetchedBy);
  const key = `${parts.instantPlatform.value}:${mine.map((one) => one.id).join()}`;
  if (parts.instantKey === key) return;
  parts.instantKey = key;
  parts.instantReport.textContent = '';
  for (const one of mine) {
    const option = make('option', '', one.name);
    option.value = one.id;
    put(parts.instantReport, option);
  }
}

/** One report's own row: its box, its name, and where it got to. */
function buildOneReportRow(parts, stands, one, into = parts.reports) {
  const row = make('label', `${OURS}report`);
  /* R250 (drawing): a report that cannot be fetched is not a tick row; it is a greyed row at the end of the list with its reason behind an i (`showTheRestOfIt`). */
  row.hidden = !one.canBeFetched;
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
  put(into, row);
  parts.boxes.set(one.id, box);
  parts.states.set(one.id, state);
}

/** Everything under the report list, drawn on every poll. */
function showTheRestOfIt(parts, stands) {
  /* ------------------------------------------------ what it cannot fetch */
  /* R250 (drawing: "greyed rows at the end of that platform's tick list, the reason behind an i"): built once, shown with the chosen platform. */
  if (!parts.cannotRows || !parts.cannotRows.length) {
    parts.cannotRows = [];
    for (const one of stands.cannotBeFetched) {
      const row = make('div', `${OURS}cannot`);
      put(row, make('span', `${OURS}report-name`, `${one.name} · cannot be fetched`), make('span', `${OURS}note`, one.why));
      put(parts.cannot, row);
      parts.cannotRows.push([one.platform, row]);
    }
  }

  /* ------------------------------------------------------ the day and run of each report (R208) */
  const scheduleNow = JSON.stringify(stands.schedule || []);
  const picking = globalThis.document && parts.scheduleList.contains(globalThis.document.activeElement);
  if (parts.scheduleShown !== scheduleNow && !picking) {
    parts.scheduleShown = scheduleNow;
    parts.scheduleList.textContent = '';
    for (const head of ['Report', 'Day', 'Run']) put(parts.scheduleList, make('span', `${OURS}gridHead`, head));
    const platformRank = (one) => { const at = PLATFORM_ORDER.indexOf(one.platform); return at < 0 ? PLATFORM_ORDER.length : at; };
    const runRank = (one) => THE_RUNS.indexOf(one.run);
    const inOrder = [...(stands.schedule || [])].sort((a, b) => platformRank(a) - platformRank(b)
      || runRank(a) - runRank(b) || String(a.name).localeCompare(String(b.name)));
    let platformShown = null;
    for (const one of inOrder) {
      if (one.platform && one.platform !== platformShown) {
        platformShown = one.platform;
        put(parts.scheduleList, make('div', `${OURS}schedPlatform`, CALLED[one.platform] || one.platform));
      }
      const row = make('div', `${OURS}schedRow`);
      const day = make('select', 'k-control');
      for (const [value, label] of [['yesterday', 'Yesterday'], ['today', 'Today']]) {
        const option = make('option', '', label);
        option.value = value;
        put(day, option);
      }
      day.value = one.day;
      const run = make('select', 'k-control');
      for (const [value, label] of [['morning', 'Morning run'], ['evening', 'Evening run'], ['own', 'Own time']]) {
        const option = make('option', '', label);
        option.value = value;
        put(run, option);
      }
      run.value = one.run;
      /* R250 (D1035): Own time shows a time box, and a warning when the time is earlier than the report is usually ready. */
      const time = make('input', 'k-control');
      time.type = 'time';
      time.value = one.at || THE_OWN_DEFAULT;
      time.setAttribute('aria-label', `${one.name} own time`);
      const warn = make('div', `${OURS}schedWarn`);
      const showOwn = () => {
        time.hidden = run.value !== 'own';
        warn.textContent = run.value === 'own' ? theReadyWarning(one.id, time.value) : '';
        warn.hidden = !warn.textContent;
      };
      showOwn();
      const save = () => parts.doing.saveTheReportTimes && parts.doing.saveTheReportTimes(one.id, day.value, run.value, run.value === 'own' ? time.value : undefined);
      day.addEventListener('change', save);
      run.addEventListener('change', () => { showOwn(); save(); });
      time.addEventListener('input', showOwn);
      time.addEventListener('change', () => { showOwn(); save(); });
      const cell = make('span', `${OURS}runCell`);
      put(cell, run, time);
      put(row, make('span', `${OURS}label`, one.name), day, cell);
      put(parts.scheduleList, row, warn);
    }
    const offMorning = inOrder.filter((one) => one.run !== 'morning').length;
    parts.timesFoldTitle.textContent = `Which report runs when${offMorning ? ` · ${offMorning} not on the morning run` : ''}`;
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
  parts.hourState.textContent = theClockLine(clock, stands.waitingForIdle);
  /* R250: the evening and returns boxes show what is saved (unless being typed in), and two runs at one time are said in red. */
  if (clock && clock.times) {
    for (const which of ['evening']) {
      const box = parts[`${which}Time`];
      if (box.value !== clock.times[which] && !(globalThis.document && globalThis.document.activeElement === box)) box.value = clock.times[which];
    }
    if (!clock.chosen && parts.hour.value !== clock.times.morning && !(globalThis.document && globalThis.document.activeElement === parts.hour)) parts.hour.value = clock.times.morning;
    parts.clash.textContent = theClashLine(clock.times);
    parts.clash.hidden = !parts.clash.textContent;
    parts.timesButtonState.textContent = [clock.times.morning, clock.times.evening, ...(clock.own || []).map((one) => `own ${one.time}`)].join(' · ');
    parts.timesButtonState.classList.toggle(`${OURS}clashing`, Boolean(parts.clash.textContent));
  }

  /* **ONE TABLE FOR THE LAST RUN, REPLACING THE WORDS BOX (AJ6).** The full words still go to the Drive; the panel draws only when the run changed, so an open row is not rebuilt for nothing. */
  /* **ONE TABLE PER PLATFORM OF THE SYNC (his ask, 1 Nov 2026)**, Flipkart, Meesho, Amazon in walking order. */
  const names = new Map(stands.reports.map((one) => [one.id, one.name]));
  const ofPlatform = (stands.night && stands.night.platform) || '';
  const runs = (stands.runs && stands.runs.length) ? stands.runs
    : (stands.night ? [{ platform: ofPlatform, name: CALLED[ofPlatform] || ofPlatform, night: stands.night }] : []);
  const shown = runs.filter((run) => !run.platform || run.platform === parts.chosen)
    .map((run) => ({ name: run.name, table: theReportTable(run.night, (id) => names.get(id) || '') }));
  const drawn = JSON.stringify(shown);
  if (parts.drawn !== drawn) {
    parts.drawn = drawn;
    showTheRuns(parts.log, shown, parts.opened);
  }
  showTheEvents(parts, stands.events || []);
}

/** Every platform's table under the one Last run box; with no run at all, the table's own "No sync has been run". */
export function showTheRuns(into, shown, opened) {
  into.textContent = '';
  if (!shown.length) showTheReportTable(into, null, '', opened);
  for (const one of shown) {
    const box = make('div', `${OURS}run-platform`);
    put(into, box);
    showTheReportTable(box, one.table, one.name, opened);
  }
}

/** The event list, redrawn only when it changed. Text nodes only: what a sentence says is never read as markup. */
export function showTheEvents(parts, events) {
  const drawn = JSON.stringify(events);
  if (parts.eventsDrawn === drawn) return;
  parts.eventsDrawn = drawn;
  parts.events.textContent = '';
  if (!events.length) {
    put(parts.events, make('li', '', 'Nothing has run yet.'));
    return;
  }
  for (const one of [...events].reverse()) {
    put(parts.events, make('li', '', `${one.at ? `${inWordsWhen(one.at)} -- ` : ''}${one.words}`));
  }
}

export function showTheReportTable(into, table, platformName, opened) {
  into.textContent = '';

  if (table === null) {
    put(into, make('p', `${OURS}note`, 'No sync has been run.'));
    return;
  }

  const runHead = make('div', `${OURS}run-head`);
  const whenText = !table.finishedAt
    ? `${inWordsWhen(table.startedAt)} · still going`
    : `${inWordsWhen(table.startedAt)} to ${inWordsWhen(table.finishedAt)} · ${table.minutes} min`;
  put(
    runHead,
    make('span', `${OURS}run-title`, platformName ? `Last run: ${platformName}` : 'Last run'),
    make('span', `${OURS}note`, whenText)
  );

  const counts = make('div', `${OURS}counts`);
  const countBoxes = [
    ['landed', 'Landed', table.counts.landed],
    ['asked', 'Asked, not yet in', table.counts.asked],
    ['tofetch', 'Still to fetch', table.counts.toFetch],
    ['failed', 'Failed', table.counts.failed]
  ];
  for (const [name, label, value] of countBoxes) {
    put(
      counts,
      put(
        make('div', `${OURS}count ${OURS}count--${name}`),
        make('span', `${OURS}count-number`, String(value)),
        make('span', `${OURS}count-label`, label)
      )
    );
  }

  const tableEl = make('table', `${OURS}table`);
  const thead = make('thead');
  const headRow = make('tr');
  put(
    headRow,
    make('th', '', 'Report'),
    make('th', '', 'Status'),
    make('th', '', 'Time'),
    make('th', '', 'What it means')
  );
  put(thead, headRow);

  const tbody = make('tbody');
  for (const row of table.rows) {
    const reportRow = make('tr', `${OURS}report-row ${OURS}report-row--${row.status.toLowerCase()}`);
    reportRow.setAttribute('tabindex', '0');
    reportRow.setAttribute('aria-expanded', opened.has(row.key) ? 'true' : 'false');
    reportRow.setAttribute('title', 'Tap to open the full detail');

    const nameCell = make('td', `${OURS}cell-name`, row.name);
    const wordCell = put(make('td'), make('span', `${OURS}word ${OURS}word--${row.status.toLowerCase()}`, row.word));
    const timeCell = make('td');
    timeCell.textContent = row.seconds === null ? '' : `${row.seconds} s${row.star ? ' *' : ''}`;
    const meansCell = make('td', '', row.means);
    put(reportRow, nameCell, wordCell, timeCell, meansCell);

    const detailRow = make('tr', `${OURS}detail-row`);
    detailRow.hidden = !opened.has(row.key);
    const detailCell = make('td');
    detailCell.setAttribute('colspan', '4');
    put(
      detailCell,
      make('pre', `${OURS}log`, row.detail || 'Nothing more to show yet.')
    );
    put(detailRow, detailCell);

    const toggle = () => {
      if (opened.has(row.key)) {
        opened.delete(row.key);
      } else {
        opened.add(row.key);
      }
      const isOpen = opened.has(row.key);
      detailRow.hidden = !isOpen;
      reportRow.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    };

    reportRow.addEventListener('click', toggle);
    reportRow.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') toggle();
    });

    put(tbody, reportRow, detailRow);
  }
  put(tableEl, thead, tbody);

  put(
    into,
    runHead,
    counts,
    tableEl,
    make('p', `${OURS}note`, '* Time spent waiting for the platform, not working.')
  );
}

/** When the extension next wakes by itself, in the seller's own words. */
export function whenItNextWakes(clock) {
  const evening = (clock && clock.eveningAt ? ` The evening run wakes ${inWordsWhen(clock.eveningAt)}.` : '')
    + ((clock && clock.own) || []).map((one) => (one.at ? ` The own-time run at ${one.time} wakes ${inWordsWhen(one.at)}.` : '')).join('');
  if (!clock || !clock.chosen) return `No time saved yet, so the morning run wakes at 8:00.${evening}`;
  if (!clock.nextAt) {
    return `Saved as ${clock.chosen}, but its clock is not set -- nothing will start by itself. `
      + `Press Save again.${evening}`;
  }
  return `Next morning run wakes ${inWordsWhen(clock.nextAt)}.${evening}`;
}

/** Say something back to whoever pressed a button, or take the message away. */
export function saySomething(parts, said) {
  parts.said.textContent = said || '';
  parts.said.hidden = !said;
}

/** What the panel says while an automatic run waits for the computer to be left alone (AJ8, his N063). */
export function theWaitingSaid(waiting) {
  return waiting ? 'Waiting until the computer has not been used for 3 minutes. Then the sync starts by itself.' : '';
}

/** R250: "Morning run is at 4:00 pm, the same as the evening run" for the first two runs that share a time, or ''. */
export function theClashLine(times) {
  const names = { morning: 'Morning', evening: 'Evening' };
  const words = (hhmm) => { const [h, m] = hhmm.split(':').map(Number); return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h < 12 ? 'am' : 'pm'}`; };
  const keys = Object.keys(names);
  for (let a = 0; a < keys.length; a += 1) {
    for (let b = a + 1; b < keys.length; b += 1) {
      if (times[keys[a]] === times[keys[b]]) return `${names[keys[a]]} run is at ${words(times[keys[a]])}, the same as the ${names[keys[b]].toLowerCase()} run. Change one of them.`;
    }
  }
  return '';
}

/** The clock's line on the panel: when it next wakes, and that a run is waiting when one is (AJ8). */
export function theClockLine(clock, waiting) {
  return [whenItNextWakes(clock), theWaitingSaid(waiting)].filter(Boolean).join(' ');
}
