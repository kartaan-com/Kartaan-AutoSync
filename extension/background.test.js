/* Checks for the clock and the record.
 *
 * Run: node extension/background.test.js
 *
 * **THESE ARE THE TWO FAILURES THAT COST HIM THE MOST**, and neither of them
 * could be checked at all in the reference, because both live in code that only
 * runs inside a real Chrome. Against a stand-in they are ordinary:
 *
 *   - **the clock stops and nothing puts it back.** Nine days with nothing run
 *     at all. The check that matters is not "an alarm is created" -- the
 *     reference creates one too. It is **what happens when the alarm is taken
 *     away while Chrome is running**, which is the case neither of Chrome's two
 *     lifecycle events covers;
 *   - **a run that was interrupted writes nothing down.** Ten real files fetched
 *     on 25 August and every layer that exists to record them silent, because
 *     one path out of a run skipped the one function that writes.
 *
 * And the third thing, which is why the first two are written the way they are:
 * **Chrome shuts this worker down after thirty seconds and takes every variable
 * with it.** The stand-in can be told to do exactly that, and the checks below
 * do it in the middle of a run.
 */

import { installFakeChrome } from '../test/fake-chrome.js';
import {
  DAILY,
  EVERY_DAY_IN_MINUTES,
  EVERY_TWO_MINUTES,
  STAY_AWAKE,
  makeSureTheWorkerIsWoken,
  sweepUpAnAbandonedWalk,
  FINISHED,
  NEEDS_SIGNING_IN,
  RUNNING,
  STOPPED,
  THE_RUN,
  endTheRun,
  makeSureTheClockIsSet,
  recordOneReport,
  startTheRun,
  aFreshSecret,
  answerThePage,
  armTheCatcher,
  stillOwedFrom,
  theRun,
  wireUp,
  A_WALK_LASTS_MS,
  THE_WALK,
  beginTheWalk,
  endTheWalk,
  startAWalk,
  theWalkInFlight,
  theWalkMovedOn,
  theRelayAllows,
  afterALanding,
  whyTheseAreNotNames,
  NAMED_PER_CAMPAIGN,
} from './background.js';
import { LAST_LANDED } from './nightly.js';
import { CAUGHT, TOO_BIG, catchTheNextFile } from './catch-blob.js';
import {
  A_PLATFORM_OR_ITS_STORAGE, DECLINED_A_LINK, RELAY_TO_THE_PAGE, WHERE_A_FILE_REALLY_COMES_FROM, aFileReallyComesFrom,
} from './driver.js';
import { TOO_BIG_TO_CARRY, theCampaignsFileName } from './walk.js';
import { OUR_TAB, OUR_WINDOW, WALK_IN_HIS_OWN_WINDOW, aTabToWalkIn, watchForDownloads } from './doors.js';
import { readFileSync } from 'node:fs';

process.on('uncaughtException', (err) => {
  console.log(`FAIL  the checks stopped part way through: ${(err && err.message) || String(err)}`);
  process.exit(1);
});
process.on('unhandledRejection', (err) => {
  console.log(`FAIL  something was waited on and never came back: ${(err && err.message) || String(err)}`);
  process.exit(1);
});

let failures = 0;
let ran = 0;

let reachedTheEnd = false;
process.on('exit', (code) => {
  if (reachedTheEnd || code !== 0) return;
  console.log('FAIL  the checks stopped before the end -- something they waited on never came back');
  process.exitCode = 1;
});

/** Is the named alarm really set? **NAMED RATHER THAN COUNTED.** Counting
 *  alarms said "the clock is set" about any alarm at all, and went red the day a
 *  second, unrelated alarm was added -- which is a check measuring the wrong
 *  thing and saying so only by accident. */
function theAlarm(browser, name) {
  return browser.alarms().find((one) => one.name === name) || null;
}

function check(name, passed) {
  ran++;
  console.log(`${passed ? 'PASS' : 'FAIL'}  ${name}`);
  if (!passed) failures++;
}

/** What a call refused with, or empty text if it did not refuse. */
async function said(fn) {
  try {
    await fn();
  } catch (wrong) {
    return (wrong && wrong.message) || String(wrong);
  }
  return '';
}

const AT = '2026-08-27T16:00:00.000Z';
const LATER = '2026-08-27T16:04:00.000Z';

/* -------------------------------------------------------------- the clock */

{
  const browser = installFakeChrome();
  const made = await makeSureTheClockIsSet(browser.chrome);
  check('the clock is set when there is none', made === true);
  check('and there is exactly one alarm', browser.alarms().length === 1);
  check('by the one name', browser.alarms()[0].name === DAILY);
  check('going off every day', browser.alarms()[0].periodInMinutes === EVERY_DAY_IN_MINUTES);
  /* **ASKED FOR OUT LOUD.** The documentation asks for it explicitly "to
   * maximize compatibility across browsers", and it is the difference between
   * an alarm surviving a browser restart and not. */
  check('and asked to survive a browser restart',
    browser.alarms()[0].persistAcrossSessions === true);

  const again = await makeSureTheClockIsSet(browser.chrome);
  check('asking a second time does not make a second one', again === false);
  check('and there is still only one', browser.alarms().length === 1);
}

{
  /* **A DAY IS NOT HALF AN HOUR.** Chrome refuses anything under half a minute
   * outright; a period nobody checked could be asked for and never arrive. */
  const browser = installFakeChrome();
  await makeSureTheClockIsSet(browser.chrome);
  check('a day is a real number of minutes, not a fraction Chrome refuses',
    EVERY_DAY_IN_MINUTES >= 0.5 && EVERY_DAY_IN_MINUTES === 1440);
  check('and the stand-in refuses one Chrome would refuse',
    (await said(() => browser.chrome.alarms.create('too-often', { periodInMinutes: 0.2 })))
      .includes('will not honour'));
}

{
  /* **THIS IS THE NINE-DAY OUTAGE, BUILT AS IT REALLY HAPPENED.**
   *
   * The alarm goes -- a reload, a restart, an update, anything -- while Chrome
   * carries on running. Neither of the two lifecycle events fires: the profile
   * did not launch and the extension was not installed. The reference asks for
   * its alarm in one of those two places only, so nothing was ever going to ask
   * again, and it sat idle with an empty queue for ever. */
  const browser = installFakeChrome();
  let due = 0;
  await wireUp(browser.chrome, { onDue: async () => { due += 1; } });
  check('wiring the worker up sets the clock on the way past', theAlarm(browser, DAILY) !== null);

  browser.forgetTheAlarms();
  check('and here the alarm is gone, with Chrome still running', browser.alarms().length === 0);

  /* Chrome shuts an idle worker down and starts it again when something wakes
   * it. Starting it again is wiring it up again -- and that is the moment the
   * clock has to come back. */
  browser.shutTheWorkerDown();
  await wireUp(browser.chrome, { onDue: async () => { due += 1; } });
  check('the next time the worker wakes, the clock is put back',
    theAlarm(browser, DAILY) !== null);
}

{
  const browser = installFakeChrome();
  let due = 0;
  await wireUp(browser.chrome, { onDue: async () => { due += 1; } });
  /* **THAT SOMETHING IS LISTENING, NOT HOW MANY.** Counting listeners said "the
   * profile launching is listened for" about the NUMBER of them, and went red
   * the day a second, unrelated thing was hung off the same event -- a check
   * measuring the wrong thing, saying so only by accident. */
  check('the profile launching is listened for', browser.chrome.runtime.onStartup.many >= 1);
  check('and the extension being installed or updated too',
    browser.chrome.runtime.onInstalled.many >= 1);
  check('and the alarm itself', browser.chrome.alarms.onAlarm.many === 1);

  browser.forgetTheAlarms();
  await browser.chrome.runtime.onStartup.happened();
  check('a profile launching with no alarm puts it back', theAlarm(browser, DAILY) !== null);

  browser.forgetTheAlarms();
  await browser.chrome.runtime.onInstalled.happened({ reason: 'update' });
  check('and so does an update', theAlarm(browser, DAILY) !== null);
}

{
  const browser = installFakeChrome();
  let due = 0;
  await wireUp(browser.chrome, { onDue: async () => { due += 1; } });

  await browser.chrome.alarms.onAlarm.happened({ name: DAILY });
  check('the daily alarm going off starts a run', due === 1);

  /* **THE CLOCK IS PUT BACK EVEN HERE.** An alarm firing proves it existed a
   * moment ago and nothing about tomorrow. This is the last moment anything is
   * listening. */
  browser.forgetTheAlarms();
  await browser.chrome.alarms.onAlarm.happened({ name: DAILY });
  check('and the alarm going off also puts the clock back for next time',
    theAlarm(browser, DAILY) !== null);

  await browser.chrome.alarms.onAlarm.happened({ name: 'something-else' });
  check('somebody else\'s alarm does not start a run', due === 2);
}

{
  /* **A53: THE HOURLY RE-CHECK STARTS ITS OWN SYNC, NEVER THE DAILY ONE.** */
  const browser = installFakeChrome();
  let due = 0;
  let rechecked = 0;
  await wireUp(browser.chrome, {
    onDue: async () => { due += 1; }, onRecheck: async () => { rechecked += 1; },
  });
  await browser.chrome.alarms.onAlarm.happened({ name: 'kartaan-autosync-recheck' });
  check('the hourly re-check alarm starts the re-check and not the daily sync',
    rechecked === 1 && due === 0);
}

{
  /* **A53: AFTER A FLIPKART TRAFFIC FILE LANDS, ITS LAST DAY IS REMEMBERED.** A file
   * that cannot be read falls back to the day in its name. */
  const browser = installFakeChrome();
  await afterALanding(browser.chrome, {
    reportId: 'fk_views', fileName: 'flipkart_fk_views_2026-09-12.xlsx', bytes: new Uint8Array([1, 2]),
  });
  check('after a traffic file lands, the last day it holds is remembered',
    (await browser.chrome.storage.local.get('kartaan-autosync-last-captured'))['kartaan-autosync-last-captured'].fk_views
      === '2026-09-12');
  check('and nothing is remembered for a report without that rule',
    (await afterALanding(browser.chrome, {
      reportId: 'fk_ads_daily', fileName: 'flipkart_fk_ads_daily_2026-09-12.csv', bytes: new Uint8Array([1]),
    })) === null);
}

{
  /* **JOB 6: EVERY LANDING ADDS TO `daysNobodyTried`'S RECORD OF WHAT HAS
   * REALLY LANDED, NOT ONLY FLIPKART TRAFFIC.** Without this, a day no sync
   * ever tried (F14) has nothing to measure a gap against at all. */
  const browser = installFakeChrome();
  await afterALanding(browser.chrome, {
    reportId: 'me_orders', fileName: 'meesho_me_orders_2026-09-16.csv', bytes: new Uint8Array([1]),
  });
  check('an ordinary report landing also remembers the day it was for',
    JSON.stringify((await browser.chrome.storage.local.get(LAST_LANDED))[LAST_LANDED].me_orders)
      === JSON.stringify(['2026-09-16']));
  await afterALanding(browser.chrome, {
    reportId: 'me_views', fileName: 'meesho_me_views.csv', bytes: new Uint8Array([1]),
  });
  check('and a running list, whose name carries no day, remembers nothing',
    (await browser.chrome.storage.local.get(LAST_LANDED))[LAST_LANDED].me_views === undefined);
  await afterALanding(browser.chrome, {
    reportId: 'fk_ads_overall',
    fileName: 'flipkart_fk_ads_overall_2026-09-20_0PTESTCAMP001.csv',
    bytes: new Uint8Array([1]),
  });
  check('the day is read correctly out of a per-campaign file name too',
    JSON.stringify((await browser.chrome.storage.local.get(LAST_LANDED))[LAST_LANDED].fk_ads_overall)
      === JSON.stringify(['2026-09-20']));
}

{
  /* **JOB 6: THE FOLDER LISTING ALREADY FETCHED FOR THE PUT-OR-REPLACE
   * DECISION BACKFILLS EVERY DAY IT SEES, NOT ONLY THE ONE JUST LANDED.**
   * This is the only way the very first landing after this code ever ran can
   * know about days that landed before it existed -- and it is what lets a
   * hole BEHIND a later landed day (F14 itself: `me_orders` 09-16, missing
   * 09-17..09-19, landed again 09-20) be found at all, at no extra Drive
   * cost: `drive.landTheFile` was already asking for this list anyway. */
  const browser = installFakeChrome();
  await afterALanding(browser.chrome, {
    reportId: 'me_orders',
    fileName: 'meesho_me_orders_2026-09-20.csv',
    bytes: new Uint8Array([1]),
    alreadyThere: [
      { name: 'meesho_me_orders_2026-09-14.csv' },
      { name: 'meesho_me_orders_2026-09-15.csv' },
      { name: 'meesho_me_orders_2026-09-16.csv' },
      { name: 'meesho_me_orders_2026-09-20.csv' },
    ],
  });
  check('every day already in the folder is backfilled from the one listing',
    JSON.stringify((await browser.chrome.storage.local.get(LAST_LANDED))[LAST_LANDED].me_orders)
      === JSON.stringify(['2026-09-14', '2026-09-15', '2026-09-16', '2026-09-20']));
}

/* ------------------------------------------------------------ the record */

{
  const browser = installFakeChrome();
  const run = await startTheRun(browser.chrome, { at: AT, doing: ['me_orders', 'me_payments'] });
  check('a run says it is going', run.state === RUNNING);
  check('and it is written down before anything is attempted',
    browser.stored()[THE_RUN].state === RUNNING);
  check('with everything it means to do', browser.stored()[THE_RUN].left.length === 2);
  check('and nothing done yet', browser.stored()[THE_RUN].done.length === 0);
  check('and it says when it started', browser.stored()[THE_RUN].startedAt === AT);
  /* **A RUN THAT HAS NOT ENDED SAYS SO OUT LOUD RATHER THAN LEAVING THE FIELD
   * OFF.** A missing finish time and a finish time of nothing read the same to a
   * person and differently to code, and the day board asks this to decide
   * whether a run is still going. */
  check('a run that has not ended has a finish time of nothing, not a missing one',
    'finishedAt' in browser.stored()[THE_RUN] && browser.stored()[THE_RUN].finishedAt === null);
  check('and a reason of nothing, for the same reason',
    'why' in browser.stored()[THE_RUN] && browser.stored()[THE_RUN].why === '');
}

{
  /* **THE WORKER IS SHUT DOWN IN THE MIDDLE OF THE RUN.** Chrome does this after
   * thirty quiet seconds and takes every variable with it. A run that lives in a
   * variable ends here, silently. */
  const browser = installFakeChrome();
  await startTheRun(browser.chrome, { at: AT, doing: ['me_orders', 'me_payments'] });
  await recordOneReport(browser.chrome, {
    reportId: 'me_orders', state: 'landed', say: 'Landed 900 bytes.', at: AT,
  });
  browser.shutTheWorkerDown();

  const after = await recordOneReport(browser.chrome, {
    reportId: 'me_payments', state: 'landed', say: 'Landed 40 bytes.', at: AT,
  });
  /* **RECORDING ANSWERS WITH THE RUN AS IT NOW STANDS**, so the thing driving it
   * knows what is left without reading storage again -- and reads the same
   * answer storage would give. */
  check('recording a report answers with the run as it now stands',
    after.done.length === 2 && after.left.length === 0);

  const found = await theRun(browser.chrome);
  check('the run survives the worker being shut down', found !== null);
  check('and remembers what was already done', found.done.length === 2);
  check('and what is still left', found.left.length === 0);
  check('and it is still going', found.state === RUNNING);
}

{
  const browser = installFakeChrome();
  await startTheRun(browser.chrome, { at: AT, doing: ['me_orders'] });
  await recordOneReport(browser.chrome, {
    reportId: 'me_orders', state: 'landed', say: 'Landed 900 bytes.', at: AT,
  });
  const ended = await endTheRun(browser.chrome, { state: FINISHED, at: LATER });
  check('a run that finished says so', ended.state === FINISHED);
  check('and says when', browser.stored()[THE_RUN].finishedAt === LATER);
  check('and nothing is left', ended.left.length === 0);

  check('a run cannot be ended by saying it is still going',
    (await said(() => endTheRun(browser.chrome, { state: RUNNING, at: LATER })))
      .includes('still going'));
}

{
  /* **THE 25 AUGUST FAILURE, BUILT AS IT REALLY HAPPENED.**
   *
   * The run fetched real files, then a portal asked for a sign-in and it
   * stopped. In the reference that path skipped the only function that writes
   * anything, so ten files that really landed left no trace in the log, the
   * board or the summary. */
  const browser = installFakeChrome();
  await startTheRun(browser.chrome, {
    at: AT, doing: ['me_orders', 'me_payments', 'fk_ads_daily'],
  });
  await recordOneReport(browser.chrome, {
    reportId: 'me_orders', state: 'landed', say: 'Landed 900 bytes.', at: AT,
  });
  await recordOneReport(browser.chrome, {
    reportId: 'me_payments', state: 'landed', say: 'Landed 40 bytes.', at: AT,
  });
  const stopped = await endTheRun(browser.chrome, {
    state: NEEDS_SIGNING_IN,
    why: 'Flipkart is asking to be signed in to.',
    at: LATER,
  });

  check('a run stopped by a sign-in is written down like any other',
    browser.stored()[THE_RUN].finishedAt === LATER);
  /* **AND IT IS NOT CALLED A FAILURE.** Every report after it would hit the same
   * wall; calling them all broken buries the one thing that needs doing. */
  check('and it says what actually stopped it', stopped.state === NEEDS_SIGNING_IN);
  check('in words a person reads', stopped.why.includes('signed in'));
  /* **THE REAL WORK IS KEPT.** This is the whole of what was lost. */
  check('and the files that really landed are still recorded', stopped.done.length === 2);
  check('every one of them', browser.stored()[THE_RUN].lines.length === 2);

  /* **AND WHAT IT NEVER GOT TO IS STILL OWED.** The reference emptied its queue
   * on a sign-in prompt and the reports behind it were never mentioned again. */
  check('what it never reached is still owed',
    stillOwedFrom(stopped).length === 1 && stillOwedFrom(stopped)[0] === 'fk_ads_daily');
}

{
  const browser = installFakeChrome();
  await startTheRun(browser.chrome, { at: AT, doing: ['me_orders', 'me_payments'] });
  const cut = await endTheRun(browser.chrome, { state: STOPPED, why: 'The tab was closed.', at: LATER });
  check('a run cut off any other way is written down too', cut.state === STOPPED);
  check('and everything it never reached is owed', stillOwedFrom(cut).length === 2);

  /* A run still going owes nothing to the NEXT run -- it is the one doing them. */
  const browser2 = installFakeChrome();
  const going = await startTheRun(browser2.chrome, { at: AT, doing: ['me_orders'] });
  check('a run that is still going is not owing anything to anybody else',
    stillOwedFrom(going).length === 0);
  check('and nothing at all owes nothing', stillOwedFrom(null).length === 0);
}

{
  const browser = installFakeChrome();
  await startTheRun(browser.chrome, { at: AT, doing: ['me_orders'] });
  const second = await startTheRun(browser.chrome, { at: LATER, doing: ['me_payments'] });
  /* **TWO RUNS AT ONCE IS TWO COPIES OF EVERY FILE.** The second is told one is
   * already going rather than replacing the record of the first, which would
   * lose whatever the first had already done. */
  check('a second run started while one is going is told so', second.alreadyGoing === true);
  check('and it did not replace what the first one is doing',
    browser.stored()[THE_RUN].startedAt === AT);
  check('nor what it means to do',
    browser.stored()[THE_RUN].left[0] === 'me_orders');

  await endTheRun(browser.chrome, { state: FINISHED, at: LATER });
  const third = await startTheRun(browser.chrome, { at: LATER, doing: ['me_payments'] });
  check('once it has ended, the next run starts normally', third.alreadyGoing === false);
  check('and it is the new one that is written down',
    browser.stored()[THE_RUN].left[0] === 'me_payments');
}

{
  const browser = installFakeChrome();
  check('recording against a run that is not going is refused',
    (await said(() => recordOneReport(browser.chrome, {
      reportId: 'me_orders', state: 'landed', say: 'x', at: AT,
    }))).includes('not going'));

  await startTheRun(browser.chrome, { at: AT, doing: ['me_orders'] });
  await endTheRun(browser.chrome, { state: FINISHED, at: LATER });
  check('and so is recording against one that has ended',
    (await said(() => recordOneReport(browser.chrome, {
      reportId: 'me_orders', state: 'landed', say: 'x', at: AT,
    }))).includes('not going'));

  const nothing = installFakeChrome();
  check('ending a run that never started writes no phantom run',
    (await endTheRun(nothing.chrome, { state: FINISHED, at: LATER })) === null);
  check('and stores nothing at all', Object.keys(nothing.stored()).length === 0);
}

{
  /* **WHAT IS STORED IS A COPY.** Editing what came back must not change what
   * was saved, or code could read back something it never wrote. */
  const browser = installFakeChrome();
  await startTheRun(browser.chrome, { at: AT, doing: ['me_orders'] });
  const run = await theRun(browser.chrome);
  run.left.push('me_payments');
  const again = await theRun(browser.chrome);
  check('changing what was read back does not change what was stored',
    again.left.length === 1);
}


/* ------------------------------ the way back from the page (cycle 46, R6#7) */

/* **WITHOUT THIS THE EXTENSION CANNOT FETCH A SINGLE REPORT.** `content.js` asks
 * the background to go somewhere, to take a file and to write a line, and nothing
 * anywhere was listening. Everything was built and nothing was joined up. */
{
  const browser = installFakeChrome();
  const tab = await browser.chrome.tabs.create({ url: 'https://supplier.meesho.com/' });
  const said = [];
  const went = [];
  const putAway = [];
  let driveRefuses = '';
  wireUp(browser.chrome, {
    onDue: async () => {},
    answer: answerThePage(browser.chrome, {
      goTo: async (_chrome, where) => { went.push(where); },
      routeInThePage: async (_chrome, where) => { went.push({ ...where, routed: true }); return { arrived: true }; },
      takeTheFile: async () => new Uint8Array([1, 2, 3]),
      landTheFile: async (what) => {
        if (driveRefuses) throw new Error(driveRefuses);
        putAway.push(what);
        return { id: 'an-id-from-drive' };
      },
      watching: { forget: () => {}, seen: () => [], expectAFile: () => {} },
      say: (line) => said.push(line),
      secret: () => 'a-secret',
    }),
  });

  check('the background answers the page half at all',
    (await browser.aPageAsked({ do: 'go', address: 'https://x/', patience: 5 })) !== undefined);
  check('and it really went there', went.length === 1 && went[0].address === 'https://x/');
  check('and it went in the tab that asked', went[0].tabId === tab.id);

  /* **A53: A PAGE MAY BE MOVED TO A ROUTE ON ITS OWN SITE, NEVER ANOTHER.** */
  const flipkartPage = {
    tab: { id: tab.id }, id: 'stand-in-extension-id', url: 'https://seller.flipkart.com/index.html',
  };
  const routed = await browser.aPageAsked(
    { do: 'route-to', address: 'https://seller.flipkart.com/index.html#dashboard/payments/spf' },
    flipkartPage,
  );
  check('a page is moved to a route on its own site, in its own tab',
    Boolean(routed) && routed.arrived === true
    && went.some((one) => one.routed && one.tabId === tab.id));
  const otherSite = await browser.aPageAsked(
    { do: 'route-to', address: 'https://somewhere-else.example/#dashboard' }, flipkartPage,
  );
  /* **A53: THE ONE SIGN-IN ATTEMPT IS MARKED ON THE WALK, FOR ITS OWN TAB.** */
  await browser.chrome.storage.local.set({
    [THE_WALK]: { tabId: tab.id, reportId: 'me_orders', at: 1, carryOnUntil: Date.now() + 60000, answer: null },
  });
  await browser.aPageAsked({ do: 'tried-signing-in' }, flipkartPage);
  check('the one sign-in attempt is written on the walk of the tab that made it',
    (await browser.chrome.storage.local.get(THE_WALK))[THE_WALK].triedSigningIn === true);
  await browser.chrome.storage.local.remove(THE_WALK);
  check('but never to another site',
    String(otherSite && otherSite.wrong).includes('only be moved within its own site')
    && went.filter((one) => one.routed).length === 1);

  const file = await browser.aPageAsked({ do: 'take-file', patience: 5 });
  check('a file comes back as something a message can carry',
    Array.isArray(file.bytes) && file.bytes.length === 3);

  /* ---- THE LINK THE PORTAL WAS ABOUT TO OPEN, FETCHED FROM THIS HALF (2026-09-11)
   *
   * **MEASURED ON HIS OWN PANEL.** The page half was written to fetch the caught
   * link itself and came back "Failed to fetch": a signed Google storage link
   * answers the extension's own half, which holds the host permissions the
   * manifest names, and answers a portal page with nothing at all. */
  const askedFor = [];
  const itsOwnFetch = globalThis.fetch;
  globalThis.fetch = async (address) => {
    askedFor.push(address);
    if (String(address).includes('refused')) throw new Error('Failed to fetch');
    if (String(address).includes('said-404')) return { ok: false, status: 404 };
    if (String(address).includes('a-sheet')) {
      return { ok: true, status: 200, arrayBuffer: async () => new Uint8Array([0x50, 0x4b, 0x03, 0x04, 1, 2]).buffer };
    }
    if (String(address).includes('a-web-page')) {
      return { ok: true, status: 200, arrayBuffer: async () => new TextEncoder().encode('<!doctype html><html>').buffer };
    }
    return { ok: true, status: 200, arrayBuffer: async () => new Uint8Array([7, 8, 9]).buffer };
  };

  const theLink = 'https://storage.googleapis.com/meesho-prod/stock.xlsx?X-Goog-Signature=ab';
  const got = await browser.aPageAsked({ do: 'fetch-this', address: theLink });
  check('THE BACKGROUND FETCHES A CAUGHT LINK AND HANDS BACK THE BYTES',
    Array.isArray(got.bytes) && got.bytes.length === 3 && got.bytes[0] === 7);
  check('and it asked the platform for exactly the address it was given',
    askedFor.length === 1 && askedFor[0] === theLink);

  /* **AND IT DOES NOT TAKE THE OTHER HALF'S WORD FOR WHERE IT IS SENDING THE
   * SELLER'S COOKIES.** `driver.theCatcherSaid` already refused anything but a
   * report store -- but this is the half that holds the seller's Drive. */
  const elsewhere = await browser.aPageAsked({
    do: 'fetch-this', address: 'https://an-advert.example.com/whatever.xlsx',
  });
  check('AN ADDRESS THAT IS NOT A REPORT STORE IS REFUSED, and nothing is fetched',
    Boolean(elsewhere.wrong) && elsewhere.wrong.includes('not an address a report comes from')
      && askedFor.length === 1);

  /* **A WALL COMES BACK AS WORDS AND AN ADDRESS, NEVER AS A THROW.** The page
   * half then gets one more go from an origin the store may answer (D198). */
  const wouldNotAnswer = await browser.aPageAsked({
    do: 'fetch-this', address: 'https://storage.googleapis.com/refused.xlsx',
  });
  check('and a platform that would not answer comes back as words, not a throw',
    wouldNotAnswer.couldNotFetch === 'Failed to fetch' && wouldNotAnswer.bytes === undefined);
  const saidNo = await browser.aPageAsked({
    do: 'fetch-this', address: 'https://storage.googleapis.com/said-404.xlsx',
  });
  check('and so does one that answered with a number', saidNo.couldNotFetch === 'the platform said 404');

  /* **A NEW LINK ON THE ASKING PAGE'S OWN SITE (HIS RULING, 2026-09-14)** --
   * fetched, and kept only if the bytes really open as a spreadsheet. The page's
   * site is the one Chrome gives this half. */
  const fromAFlipkartPage = {
    tab: { id: 1 }, id: 'stand-in-extension-id',
    url: 'https://seller.flipkart.com/index.html#dashboard/listings-management',
  };
  const aNewSheet = await browser.aPageAsked({
    do: 'fetch-this', address: 'https://seller.flipkart.com/napi/listing/a-sheet?x=1',
  }, fromAFlipkartPage);
  check('A NEW LINK ON THE PLATFORM\'S OWN SITE THAT REALLY IS A SPREADSHEET IS FETCHED AND KEPT',
    Boolean(aNewSheet) && Array.isArray(aNewSheet.bytes) && aNewSheet.bytes[0] === 0x50);
  const aNewPage = await browser.aPageAsked({
    do: 'fetch-this', address: 'https://seller.flipkart.com/napi/listing/a-web-page',
  }, fromAFlipkartPage);
  check('but one that gives back a web page is refused, and nothing is kept',
    Boolean(aNewPage) && Boolean(aNewPage.wrong) && aNewPage.wrong.includes('not a spreadsheet')
      && aNewPage.bytes === undefined);
  const askedFromElsewhere = await browser.aPageAsked({
    do: 'fetch-this', address: 'https://seller.flipkart.com/napi/listing/a-sheet',
  }, { tab: { id: 1 }, id: 'stand-in-extension-id', url: 'https://supplier.meesho.com/panel/v3/new/' });
  check('and the same link asked for by a page on another site is refused outright',
    Boolean(askedFromElsewhere) && Boolean(askedFromElsewhere.wrong)
      && askedFromElsewhere.wrong.includes('not an address a report comes from'));

  globalThis.fetch = itsOwnFetch;

  /* ------------------- AND THE FILE GOES SOMEWHERE (D171)
   *
   * **`extension/drive.js` WAS FINISHED, CHECKED AND IMPORTED BY NOTHING BUT ITS
   * OWN TEST FILE.** So no report a browser fetched had ever reached a real
   * Drive -- which is why a seller who had set everything up correctly would
   * still have seen Amazon and nothing else. The page cannot do it itself:
   * `chrome.identity` is not exposed to a content script at all. */
  /* **NOT AN INDEX INTO AN ANSWER THAT MIGHT NOT EXIST.** A message the
   * background does not know is answered with nothing, and reading `.put` off
   * nothing THROWS -- so the checks file dies where it stands, prints no count,
   * and says nothing about everything below it. Found by breaking it: dropping
   * `land-the-file` from `KNOWN` crashed this file instead of reddening it. */
  const putBack = await browser.aPageAsked({
    do: 'land-the-file', reportId: 'me_orders',
    fileName: 'meesho_me_orders_2026-09-05.csv', bytes: [1, 2, 3],
  });
  check('THE BACKGROUND PUTS A FILE THE PAGE HANDS IT INTO THE DRIVE',
    Boolean(putBack) && putBack.put === 'an-id-from-drive');
  check('and it is handed the report, the name and the real bytes',
    putAway.length === 1 && putAway[0].reportId === 'me_orders'
    && putAway[0].fileName === 'meesho_me_orders_2026-09-05.csv'
    && putAway[0].body instanceof Uint8Array && putAway[0].body.length === 3);
  /* **A DRIVE THAT REFUSED COMES BACK AS WORDS, NEVER AS A THROW.** Thrown, it
   * reaches the page as "the message port closed" -- a sentence about the
   * bridge, said instead of the one somebody could act on. */
  driveRefuses = 'the seller has run out of Drive';
  /* **A NAME THIS PRODUCT REALLY WRITES.** It used to be `x.csv`, which reached
   * Drive only because nothing on this boundary asked anything of a name -- so
   * this check would go on passing on a name the run could never read a day out
   * of. The question it asks is unchanged: does a Drive that refused come back
   * as words. */
  const refused = await browser.aPageAsked({
    do: 'land-the-file', reportId: 'me_orders',
    fileName: 'meesho_me_orders_2026-09-05.csv', bytes: [1],
  });
  check('a Drive that refused comes back as words rather than as a broken channel',
    refused && refused.wrong === 'the seller has run out of Drive' && !refused.put);
  driveRefuses = '';

  /* ---------- WHICH AD CAMPAIGNS RAN ON A DAY (2026-09-15)
   *
   * Kept when the ads daily file lands, read back by the overall report. Not known
   * and none ran are two different answers, and only one of them is "nothing to
   * fetch". */
  const kept = await browser.aPageAsked({
    do: 'keep-the-campaigns', reportId: 'fk_ads_daily', dataDate: '2026-09-13', campaigns: ['0PTESTCAMP001'],
  });
  check('the campaigns the ads daily file named are kept', Boolean(kept) && kept.kept === 1);
  const readBack = await browser.aPageAsked({ do: 'the-campaigns', reportId: 'fk_ads_daily', dataDate: '2026-09-13' });
  check('and read back for the same report and day',
    Boolean(readBack) && JSON.stringify(readBack.campaigns) === '["0PTESTCAMP001"]');
  const unknown = await browser.aPageAsked({ do: 'the-campaigns', reportId: 'fk_ads_daily', dataDate: '2026-09-12' });
  check('a day nothing was kept for is not known, rather than none ran',
    Boolean(unknown) && unknown.campaigns === null);
  const noneRan = await browser.aPageAsked({
    do: 'keep-the-campaigns', reportId: 'fk_ads_daily', dataDate: '2026-09-11', campaigns: [],
  });
  const noneRead = await browser.aPageAsked({ do: 'the-campaigns', reportId: 'fk_ads_daily', dataDate: '2026-09-11' });
  check('while a day no campaign ran is kept as none',
    Boolean(noneRan) && noneRan.kept === 0 && Array.isArray(noneRead.campaigns) && noneRead.campaigns.length === 0);
  const notAnId = await browser.aPageAsked({
    do: 'keep-the-campaigns', reportId: 'fk_ads_daily', dataDate: '2026-09-10', campaigns: ['0P5"><b>'],
  });
  const afterNotAnId = await browser.aPageAsked({ do: 'the-campaigns', reportId: 'fk_ads_daily', dataDate: '2026-09-10' });
  check('something that is not a campaign id is refused, and nothing is kept',
    Boolean(notAnId) && Boolean(notAnId.wrong) && afterNotAnId.campaigns === null);

  /* ---------- WHAT CROSSES THIS BOUNDARY IS ASKED SOMETHING (A33)
   *
   * **THIS IS THE ONE PLACE A NAME CROSSES FROM THE HALF THAT RUNS BESIDE THE
   * PORTAL'S OWN CODE INTO THE HALF THAT HOLDS THE SELLER'S DRIVE PERMISSION**,
   * and until now it asked nothing at all. `reportId` becomes the name of a
   * folder in the seller's Drive and goes into a Drive search inside a quoted
   * string; `fileName` becomes the name the file is put away under, and the
   * nightly run reads the day back out of exactly that name.
   *
   * **DRIVEN, NOT READ: each of these is sent, and Drive must not be reached.**
   * `putAway` is what `landTheFile` was really called with, so a guard that let
   * one through would show up as a longer list rather than as a nicer sentence. */
  const asManyAsHadLanded = putAway.length;
  const refusedNames = [
    ['a report id that is not a report', { reportId: "me_orders' or name != '", fileName: 'meesho_me_orders_2026-09-05.csv' }],
    ['a report id with a slash in it', { reportId: '../fk_orders', fileName: 'meesho_me_orders_2026-09-05.csv' }],
    ['a name with no day in it at all', { reportId: 'me_orders', fileName: 'x.csv' }],
    ['a name with a path in it', { reportId: 'me_orders', fileName: '../../meesho_me_orders_2026-09-05.csv' }],
    ['a name whose day is the right shape and not a day', { reportId: 'me_orders', fileName: 'meesho_me_orders_2026-02-31.csv' }],
  ];
  for (const [what, sent] of refusedNames) {
    // eslint-disable-next-line no-await-in-loop
    const no = await browser.aPageAsked({ do: 'land-the-file', bytes: [1], ...sent });
    check(`${what} is refused in words, and nothing is put in the Drive`,
      Boolean(no) && typeof no.wrong === 'string' && no.wrong.length > 0 && !no.put);
  }
  check('and not one of them reached the Drive at all', putAway.length === asManyAsHadLanded);

  /* **AND THE SECOND NAME THIS PRODUCT WRITES IS LET THROUGH -- FOR ITS OWN
   * REPORT AND NO OTHER.** A running list is one file added to every day, so its
   * name carries no day at all (`reports.a_running_list`). **This guard was the
   * fifth place assuming every name has a day in it**, and it was found on his
   * own panel with the walk otherwise finished: the figures read, the row built,
   * refused here.
   *
   * **THE UNDATED SHAPE IS NARROWER THAN THE DATED ONE, WHICH IS THE WHOLE
   * SAFETY OF IT.** The report id in the name has to be the very report the
   * message is about, so there is exactly one undated name per report and it is
   * fixed. The dated form has never asked that. */
  check("a running list's own undated name is allowed",
    whyTheseAreNotNames('me_views', 'meesho_me_views.csv') === null);
  check('but the same shape naming a DIFFERENT report is refused',
    typeof whyTheseAreNotNames('me_views', 'meesho_me_orders.csv') === 'string');
  check('and an undated name is still refused a path, however it is dressed up',
    typeof whyTheseAreNotNames('me_views', '../meesho_me_views.csv') === 'string');
  /* **AND NOTHING ABOUT THE DATED FORM MOVED.** Everything above still refuses,
   * and a real day is still required in the names that carry one. */
  check('while the dated name this product writes is still let through',
    whyTheseAreNotNames('me_orders', 'meesho_me_orders_2026-09-05.csv') === null);
  check('and a day that is the right shape and not a day is still refused',
    typeof whyTheseAreNotNames('me_orders', 'meesho_me_orders_2026-02-31.csv') === 'string');

  /* **THE THIRD NAME: ONE FILE PER CAMPAIGN, THE DAY NO LONGER LAST.** When
   * more than one campaign ran, the walk puts the campaign id after the day
   * (`walk.theCampaignsFileName`, the reference's own rule). The guard refused
   * exactly that name on the 2026-09-21 run, so no day with live ads was saved.
   * The name below is built by the walk's own function, not typed out. */
  const perCampaign = theCampaignsFileName('flipkart_fk_ads_overall_2026-09-20.csv', '0PTESTCAMP001', 2);
  check('a per-campaign ads file, named the way the walk names it, is allowed',
    whyTheseAreNotNames('fk_ads_overall', perCampaign) === null);
  check('but the same shape for a report not fetched per campaign is refused',
    typeof whyTheseAreNotNames('me_orders', 'meesho_me_orders_2026-09-20_0PTESTCAMP001.csv') === 'string');
  check('and the same shape naming a DIFFERENT report is refused',
    typeof whyTheseAreNotNames('fk_ads_overall', 'flipkart_fk_ads_daily_2026-09-20_0PTESTCAMP001.csv') === 'string');
  check('and a per-campaign name on a day that is not a day is refused',
    typeof whyTheseAreNotNames('fk_ads_overall', 'flipkart_fk_ads_overall_2026-02-31_0PTESTCAMP001.csv') === 'string');
  for (const [what, name] of [
    ['a path climbing out', 'flipkart_fk_ads_overall_2026-09-20_../x.csv'],
    ['a slash', 'flipkart_fk_ads_overall_2026-09-20_a/b.csv'],
    ['a quote', 'flipkart_fk_ads_overall_2026-09-20_a".csv'],
    ['a dot in the campaign', 'flipkart_fk_ads_overall_2026-09-20_a.b.csv'],
    ['an empty campaign', 'flipkart_fk_ads_overall_2026-09-20_.csv'],
  ]) {
    check(`a per-campaign name with ${what} is refused`,
      typeof whyTheseAreNotNames('fk_ads_overall', name) === 'string');
  }
  const fetchedPerCampaign = Object.entries(JSON.parse(readFileSync(new URL('./recipes.json', import.meta.url), 'utf8')).recipes)
    .filter(([, recipe]) => recipe && recipe.campaignsFrom).map(([id]) => id).sort();
  check('and the reports allowed that name are exactly the ones recipes.json fetches per campaign',
    JSON.stringify([...NAMED_PER_CAMPAIGN].sort()) === JSON.stringify(fetchedPerCampaign));

  /* **AND A FILE TOO BIG TO CARRY IS REFUSED HERE TOO.** The bytes cross as one
   * number and one comma each, so a 40 MB catch is about 160 MB of message.
   * `walk.js` refuses one before sending it; this refuses one that arrived
   * anyway, because a boundary that trusts the other half is not one. */
  const tooBig = await browser.aPageAsked({
    do: 'land-the-file', reportId: 'me_orders',
    fileName: 'meesho_me_orders_2026-09-05.csv',
    bytes: { length: TOO_BIG_TO_CARRY + 1 },
  });
  check('a file bigger than this will carry is refused, and says how big it was',
    Boolean(tooBig) && typeof tooBig.wrong === 'string'
    && tooBig.wrong.includes(String(TOO_BIG_TO_CARRY + 1)) && !tooBig.put);
  check('and it never reached the Drive either', putAway.length === asManyAsHadLanded);

  /* **AND THE NAME THE PRODUCT ITSELF WRITES IS STILL LET THROUGH.** A guard
   * that refused everything would pass every check above and land nothing, for
   * ever -- which is the shape of fault this repository keeps finding. */
  const good = await browser.aPageAsked({
    do: 'land-the-file', reportId: 'fk_claims',
    fileName: 'flipkart_fk_claims_2026-09-05.xlsx', bytes: [1, 2],
  });
  check('and a name this product really writes still lands, five-letter extension and all',
    Boolean(good) && good.put === 'an-id-from-drive'
    && putAway.length === asManyAsHadLanded + 1);

  await browser.aPageAsked({ do: 'say', line: 'something happened' });
  check('and a line said in the page is written down by the background',
    said.length === 1 && said[0] === 'something happened');

  /* **A MESSAGE WITH NO TAB BEHIND IT IS NOT ONE OF OURS.** `onMessage` also
   * carries messages from other extensions. */
  check('a message from no tab at all is not answered',
    (await browser.aPageAsked({ do: 'go', address: 'https://x/' }, { id: 'stand-in-extension-id' }))
      === undefined);
  check('and one from another extension is not answered',
    (await browser.aPageAsked({ do: 'go', address: 'https://x/' },
      { tab: { id: tab.id }, id: 'somebody-else' })) === undefined);
  check('and something it has never heard of is not answered',
    (await browser.aPageAsked({ do: 'something-else' })) === undefined);

  /* **A FAILURE COMES BACK AS WORDS, NOT AS SILENCE.** A page half waiting on an
   * answer that never comes hangs until its own patience runs out, and reports
   * the wrong thing when it does. */
  const broken = installFakeChrome();
  await broken.chrome.tabs.create({ url: 'https://supplier.meesho.com/' });
  wireUp(broken.chrome, {
    onDue: async () => {},
    answer: answerThePage(broken.chrome, {
      goTo: async () => { throw new Error('the page never finished drawing'); },
      takeTheFile: async () => null,
      watching: { forget: () => {}, seen: () => [], expectAFile: () => {} },
      say: () => {},
      secret: () => 'a-secret',
    }),
  });
  const wrong = await broken.aPageAsked({ do: 'go', address: 'https://x/', patience: 1 });
  check('a call that went wrong comes back saying so',
    String(wrong && wrong.wrong).includes('never finished drawing'));
  /* **AND A BACKGROUND WIRED WITH NO WAY TO REACH THE DRIVE SAYS SO, out loud.**
   * Left to fall through, it would answer nothing, the page would read that as
   * the file being put away, and the walk would report LANDED for a report that
   * is nowhere -- which is exactly the state this whole wiring closes. */
  const noDrive = await broken.aPageAsked({
    do: 'land-the-file', reportId: 'me_orders', fileName: 'x.csv', bytes: [1],
  });
  check('a background with no way to reach the Drive says so rather than saying nothing',
    String(noDrive && noDrive.wrong).includes('no way of putting a file in the Drive'));
}

/* ----------------------- the secret that stops a page forging a file (D135) */

{
  /* **THIRTY-TWO BYTES FROM THE BROWSER'S OWN RANDOM SOURCE.** `Math.random` is
   * documented as unsuitable for exactly this. */
  const one = aFreshSecret(globalThis.crypto);
  const other = aFreshSecret(globalThis.crypto);
  check('a secret is long enough to be worth having', one.length === 64);
  check('and it is not the same one twice', one !== other);
  check('and it is made of nothing but plain letters and figures', /^[0-9a-f]+$/.test(one));

  const browser = installFakeChrome();
  const tab = await browser.chrome.tabs.create({ url: 'https://supplier.meesho.com/' });
  /* The injected function runs in a page, and a stand-in has no `window`. It is
   * given one, so the injection can be watched all the way through. */
  const posted = [];
  const itsOwnURL = globalThis.URL;
  globalThis.window = {
    location: { origin: 'https://supplier.meesho.com' },
    postMessage: (data, to) => posted.push({ data, to }),
  };
  /* A page's `URL` is a constructor AS WELL AS holder of `createObjectURL`; the stand-in keeps both, because
   * the catcher now reads an address's host and path through `new URL(...)`. */
  globalThis.URL = Object.assign(function APagesURL(...given) { return new itsOwnURL(...given); }, {
    createObjectURL: () => 'blob:https://supplier.meesho.com/abc',
  });
  /* **THE OTHER TWO WAYS A FILE LEAVES A PORTAL, given to the stand-in so they
   * can be driven.** Meesho's stock file goes out through neither a blob nor a
   * download: an `<a target="_blank">` to a signed Google storage link, which
   * Chrome refuses to open because no person asked for it. */
  const opened = [];
  const followed = [];
  globalThis.window.open = (address) => { opened.push(address); return 'a-real-window'; };
  globalThis.HTMLAnchorElement = function () {};
  globalThis.HTMLAnchorElement.prototype = { click() { followed.push(this.href); } };
  const anAnchorTo = (href) => Object.assign(
    Object.create(globalThis.HTMLAnchorElement.prototype), { href }
  );

  await armTheCatcher(browser.chrome, { tabId: tab.id, secret: 'the-secret' });
  const put = browser.putIntoPages();
  check('the catcher is put into the page rather than loaded on every page',
    put.length === 1 && put[0].tabId === tab.id);
  /* **THE PAGE'S OWN WORLD, because that is the only place the bytes exist.** */
  check('and into the page\u2019s own world', put[0].world === 'MAIN');
  /* **AND THE SECRET GOES AS AN ARGUMENT**, which is the whole point: it never
   * crosses anything the page can listen to. */
  check('and the secret goes with it as an argument', put[0].args[0] === 'the-secret');

  /* **AND ONCE IT IS IN THE PAGE, NOTHING ON THAT PAGE CAN READ IT BACK (A32).**
   *
   * **THIS IS THE FINDING, NOT A TIDY-UP.** The secret used to be written onto
   * the very function the extension installs into the page's own world, as a
   * plain property -- `URL.createObjectURL.kartaanArmedFor`. An advert, a tag
   * manager or an injected script on `supplier.meesho.com` could read it, post
   * `kartaan-caught-a-file` carrying it, and have its own bytes go through
   * `content.js` -> `land-the-file` -> `drive.js`, which REPLACES the genuine
   * file of that day under the genuine report name. The Python then reads it
   * into the seller's ledger as real sales.
   *
   * **AND IT DID NOT HAVE TO WIN A RACE.** `content.js` arms at the start of
   * every walk turn, long before any Download is pressed, so a page that simply
   * reads the property and posts wins every time -- the first accepted message
   * is the one taken.
   *
   * **DRIVEN THE WAY A PAGE WOULD DRIVE IT:** everything a script can reach on
   * the installed function is read, and the secret must be in none of it. */
  const asAPageWould = (fn) => Reflect.ownKeys(fn).map((key) => {
    try {
      return fn[key];
    } catch (cannot) {
      return null;
    }
  });
  const inPlainSight = asAPageWould(globalThis.URL.createObjectURL);
  check('nothing a page script can read off the catcher carries the secret',
    !inPlainSight.some((one) => one === 'the-secret'));

  /* **THE FILE IT WAS HANDED, NEVER THE HANDLE IT WAS GIVEN BACK (A42), AND
   * NEVER LOOSE BYTES.** It used to post a seller's whole settlement file to the
   * page with `targetOrigin '*'`, and after that the handle its own caller
   * answered with -- which a page that got there first is free to choose. */
  const itsOwnFile = { size: 2048, type: '', arrayBuffer: async () => new ArrayBuffer(2048) };
  const madeAFile = globalThis.URL.createObjectURL(itsOwnFile);
  check('a file the page built is reported', posted.length === 1 && madeAFile.startsWith('blob:'));
  check('and it carries the secret', posted[0].data.secret === 'the-secret');
  check('and the file it was handed rather than the handle it was given back',
    posted[0].data.file === itsOwnFile && posted[0].data.handle === undefined
      && posted[0].data.asLetters === undefined);
  check('and it is addressed to this page and nowhere else',
    posted[0].to === 'https://supplier.meesho.com');
  check('and it says what it is', posted[0].data.kartaan === CAUGHT);

  /* ---- AND THE LINK A PORTAL OPENS RATHER THAN BUILDS (2026-09-11)
   *
   * **MEASURED ON HIS OWN SIGNED-IN MEESHO PANEL, four walks and two hand
   * clicks.** Pressing Download on Bulk Stock Update builds an `<a>` whose
   * `href` is an 884-character signed `storage.googleapis.com` link and whose
   * `target` is `_blank`. **Chrome refuses a new tab that no person asked for**,
   * so nothing downloaded, nothing said why, and the walk waited out its whole
   * patience. Clicked with a real mouse it downloads in seconds -- into the
   * seller's DOWNLOADS FOLDER, which is where a report must never go.
   *
   * **SO THE CLICK IS SUPPRESSED AND THE ADDRESS IS TAKEN.** Nothing downloads,
   * so there is no Save-as window to race and nothing to cancel. */
  await armTheCatcher(browser.chrome, { tabId: tab.id, secret: 'for-the-link' });
  const theRealOne = anAnchorTo(
    'https://storage.googleapis.com/meesho-prod/Inventory-Update-File.xlsx?X-Goog-Signature=ab'
  );
  theRealOne.click();
  check('A LINK TO WHERE A REPORT REALLY COMES FROM IS TAKEN, not followed',
    posted.length === 2 && followed.length === 0);
  check('and what crosses is the address, under this file’s own secret',
    posted[1].data.address === theRealOne.href && posted[1].data.secret === 'for-the-link'
      && posted[1].data.kartaan === CAUGHT);
  check('and the address is addressed to this page and nowhere else',
    posted[1].to === 'https://supplier.meesho.com');

  /* **AND THE SELLER’S OWN PAGE IS LEFT ALONE.** While this sits in the page
   * he may still be using it, and an extension that breaks his own links is
   * worse than one that fetches nothing. */
  await armTheCatcher(browser.chrome, { tabId: tab.id, secret: 'for-an-ordinary-link' });
  const anOrdinaryLink = anAnchorTo('https://supplier.meesho.com/panel/v3/new/payouts/x');
  anOrdinaryLink.click();
  check('while an ordinary link on the portal is followed exactly as before',
    followed.length === 1 && followed[0] === anOrdinaryLink.href && posted.length === 2);

  /* **AND A PORTAL THAT OPENS ITS FILE RATHER THAN LINKING IT IS CAUGHT TOO**,
   * which is the other patch the working reference carries
   * (`content/intercept.js:262-268`). */
  const throughAWindow = 'https://storage.googleapis.com/meesho-prod/other.xlsx?X-Goog-Signature=cd';
  const answered = globalThis.window.open(throughAWindow);
  check('a file opened in a window is taken, and no window is opened',
    posted.length === 3 && posted[2].data.address === throughAWindow
      && opened.length === 0 && answered === null);
  check('and it went under the secret that was still waiting',
    posted[2].data.secret === 'for-an-ordinary-link');

  /* **AND NOTHING IS SUPPRESSED WHEN NOTHING IS ARMED.** Spent on that one, the
   * page is an ordinary page again. */
  const afterwards = anAnchorTo(
    'https://storage.googleapis.com/meesho-prod/third.xlsx?X-Goog-Signature=ef'
  );
  afterwards.click();
  globalThis.window.open('https://storage.googleapis.com/meesho-prod/fourth.xlsx?X-Goog-Sig=gh');
  check('with nothing armed, a link is followed and a window is opened as always',
    posted.length === 3 && followed.length === 2 && opened.length === 1);

  await armTheCatcher(browser.chrome, { tabId: tab.id, secret: 'the-secret' });
  posted.length = 0;

  /* **ONCE, AND ONCE ONLY.** Armed for one file; a second is not ours. */
  globalThis.URL.createObjectURL({
    size: 2048, type: '', arrayBuffer: async () => new ArrayBuffer(2048),
  });
  check('and a second file is not reported without being armed again', posted.length === 1);

  /* **ARMING THE SAME PAGE AGAIN STILL CATCHES, AND STILL HIDES (A32).** The
   * re-arm branch went with the property it was written around: re-arming needed
   * a way in from outside the closure, and a way in the page can reach is a way
   * in the page can REPLACE -- the next arming would hand the secret to it. So
   * a fresh wrapper goes on instead. What that costs is one file reported twice,
   * the older wrapper posting under a secret `content.js` has stopped waiting
   * for, which `driver.theCatcherSaid` refuses. Noise, not a forged file. */
  await armTheCatcher(browser.chrome, { tabId: tab.id, secret: 'a-second-secret' });
  globalThis.URL.createObjectURL({
    size: 2048, type: '', arrayBuffer: async () => new ArrayBuffer(2048),
  });
  check('arming the same page again catches the next file', posted.length === 2);
  check('and under the newest secret, which is the only one anybody is waiting for',
    posted[1].data.secret === 'a-second-secret');
  check('and the second secret is no more readable than the first',
    !asAPageWould(globalThis.URL.createObjectURL).some((one) => one === 'a-second-secret'));

  /* Put back what was borrowed. **Deleted rather than restored, the checks
   * below lost Node's own URL and stopped part way through** -- a stand-in that
   * takes something away has to give it back. */
  globalThis.window = undefined;
  globalThis.URL = itsOwnURL;
}

{
  /* **A PAGE THAT GOT TO `createObjectURL` FIRST, WHICH THE CATCHER NAMED AS ITS
   * OWN LIMIT AND THIS CLOSES (A42).**
   *
   * A seller's portal page carries adverts, tag managers and injected scripts
   * nobody at Kartaan controls. One of them can replace `URL.createObjectURL`
   * BEFORE the catcher is put in. The catcher then calls THAT as though it were
   * the browser -- and if what it reports is the handle it was GIVEN BACK, the
   * bytes that go on to `land-the-file` are whatever that script chose.
   * `drive.js` REPLACES the genuine file of that day under the genuine report
   * name, and the Python reads it into the seller's ledger AS REAL SALES.
   *
   * **SO WHAT THIS CATCHES IS NOT A CRASH. IT IS WRONG MONEY IN A SELLER'S
   * BOOKS, SILENTLY, UNDER A REAL REPORT NAME.** The impostor never learns the
   * secret and does not need to.
   *
   * **THE ANSWER IS THAT THE CATCHER REPORTS THE FILE IT WAS HANDED, NEVER THE
   * HANDLE IT WAS GIVEN BACK.** The impostor's own answer still goes straight
   * back to the page, untouched. */
  const browser = installFakeChrome();
  const tab = await browser.chrome.tabs.create({ url: 'https://supplier.meesho.com/' });
  const posted = [];
  const itsOwnURL = globalThis.URL;
  globalThis.window = {
    location: { origin: 'https://supplier.meesho.com' },
    postMessage: (data, to) => posted.push({ data, to }),
  };

  /* The file the portal's own Download really built, and the file an advert
   * would rather the seller's ledger were fed. Different lengths, so what would
   * be landed can be named rather than guessed at. */
  const genuine = new Blob([new Uint8Array([7, 7, 7, 7])]);
  const theirs = new Blob([new Uint8Array([6, 6, 6, 6, 6, 6])]);

  /* **THE IMPOSTOR, INSTALLED BEFORE THE CATCHER.** It ignores what it is handed
   * and answers with a handle of its own. `handles` stands in for the browser's
   * own table of them: `content.js` fetches a handle and gets back whatever that
   * handle was made from. */
  const handles = new Map([
    ['blob:https://supplier.meesho.com/genuine', genuine],
    ['blob:https://supplier.meesho.com/theirs', theirs],
  ]);
  let handedTo = null;
  globalThis.URL = {
    createObjectURL: (thing) => {
      handedTo = thing;
      return 'blob:https://supplier.meesho.com/theirs';
    },
  };

  await armTheCatcher(browser.chrome, { tabId: tab.id, secret: 'the-secret' });
  const backToThePage = globalThis.URL.createObjectURL(genuine);

  /* **WHAT WOULD ACTUALLY REACH `land-the-file`, IN `content.js`'S OWN ORDER.**
   * Written out here because `content.js` has no checks of its own by design,
   * and the question this asks is about the BYTES that reach the seller's Drive
   * -- not about the shape of a message. */
  const whatWouldBeLanded = async (message) => {
    if (message.handle) return new Uint8Array(await handles.get(message.handle).arrayBuffer());
    if (message.file) return new Uint8Array(await message.file.arrayBuffer());
    return null;
  };

  check('a page that replaced createObjectURL first still has its file caught',
    posted.length === 1 && posted[0].data.secret === 'the-secret');
  check('and it is still addressed to this page and nowhere else',
    posted[0].to === 'https://supplier.meesho.com');
  const landed = await whatWouldBeLanded(posted[0].data);
  check('and what would reach the seller\u2019s Drive is the file the page was HANDED',
    !!landed && landed.length === 4 && [...landed].every((one) => one === 7));
  check('and never the bytes the impostor handed back',
    !(landed && landed.length === 6));
  /* **AND THE PAGE IS STILL NONE THE WISER.** Whatever the impostor answered is
   * what the page gets: an extension that breaks a seller's own downloads is
   * worse than one that fetches nothing. */
  check('and the page still gets exactly what its own createObjectURL answered',
    backToThePage === 'blob:https://supplier.meesho.com/theirs' && handedTo === genuine);

  globalThis.window = undefined;
  globalThis.URL = itsOwnURL;
}

{
  /* **WHAT THE PAGE HANDED OVER WOULD NOT CROSS, AND THAT IS SAID OUT LOUD
   * (A42).** A file crossing to the other half is copied by the browser reading
   * its own bytes; anything that is not a file the browser recognises is refused
   * outright. **Swallowed, that refusal is a walk that hears nothing, waits out
   * its patience, and a day missing with no line anywhere saying why.**
   *
   * **AND THE BROWSER'S OWN REASON GOES WITH IT.** A sentence this extension
   * invented is a diagnosis; the browser's is evidence -- "the evidence travels
   * with the failure" is this repository's own rule. */
  const browser = installFakeChrome();
  const tab = await browser.chrome.tabs.create({ url: 'https://supplier.meesho.com/' });
  const posted = [];
  const itsOwnURL = globalThis.URL;
  globalThis.URL = { createObjectURL: () => 'blob:https://supplier.meesho.com/abc' };
  globalThis.window = {
    location: { origin: 'https://supplier.meesho.com' },
    postMessage: (data, to) => {
      if (data.file) throw new Error('DataCloneError: it could not be cloned.');
      posted.push({ data, to });
    },
  };

  await armTheCatcher(browser.chrome, { tabId: tab.id, secret: 'the-secret' });
  const stillAnswered = globalThis.URL.createObjectURL({
    size: 2048, type: '', arrayBuffer: async () => new ArrayBuffer(2048),
  });
  check('something that will not cross as a file is said out loud rather than swallowed',
    posted.length === 1 && typeof posted[0].data.wrong === 'string');
  check('and the browser\u2019s own reason goes with it',
    posted[0].data.wrong.includes('DataCloneError'));
  check('and it still carries the secret, so the other half believes the refusal',
    posted[0].data.secret === 'the-secret');
  check('and the page still got what it asked for', stillAnswered.startsWith('blob:'));

  /* **AND IF SAYING SO WILL NOT GO EITHER, THE PAGE IS STILL NONE THE WISER.** A
   * page can replace `window.postMessage` with something that simply throws.
   * Left to throw out of the wrapper, that is the seller's own Download broken
   * by this extension -- which its first rule says is worse than fetching
   * nothing. The walk then runs out of patience, which is loud (D108). */
  globalThis.window.postMessage = () => { throw new Error('No.'); };
  await armTheCatcher(browser.chrome, { tabId: tab.id, secret: 'another-secret' });
  let broke = null;
  let answeredAnyway = null;
  try {
    answeredAnyway = globalThis.URL.createObjectURL({
      size: 2048, type: '', arrayBuffer: async () => new ArrayBuffer(2048),
    });
  } catch (wrong) {
    broke = wrong;
  }
  check('a page whose own postMessage throws does not get its download broken',
    broke === null && String(answeredAnyway).startsWith('blob:'));

  globalThis.window = undefined;
  globalThis.URL = itsOwnURL;
}

{
  /* **THE FUNCTION PUT INTO A PAGE CANNOT REACH ANYTHING AROUND IT**, because a
   * real Chrome sends its SOURCE and runs that with nothing of the extension in
   * scope. The stand-in rebuilds it the same way, so this would throw if it read
   * a constant off the top of its own file -- which is why it writes them out a
   * second time. */
  const source = catchTheNextFile.toString();
  check('the catcher names what it says out loud, inside itself',
    source.includes(`'${CAUGHT}'`));
  check('and the size it will not carry, inside itself',
    source.includes('40 * 1024 * 1024') && TOO_BIG === 40 * 1024 * 1024);
  /* **AND WHERE A REPORT REALLY COMES FROM, WHICH IS NOW WRITTEN IN TWO
   * PLACES.** The copy in the injected function decides what is SUPPRESSED on
   * the page; `driver.aFileReallyComesFrom` decides what is BELIEVED. **Drifted
   * apart, the page would suppress a click and the other half would then refuse
   * the address it handed over** -- a report that simply never arrives, with
   * both halves behaving exactly as written. */
  check('and where a report really comes from, inside itself, every one of them',
    WHERE_A_FILE_REALLY_COMES_FROM.every((one) => source.includes(`'${one}'`)));
  check('and it carries no address the other half would refuse',
    (source.match(/'[a-z0-9.\-]+\.(com|in)'|'download[a-z]+'/g) || [])
      .every((one) => WHERE_A_FILE_REALLY_COMES_FROM.includes(one.slice(1, -1))
        || A_PLATFORM_OR_ITS_STORAGE.includes(one.slice(1, -1))));
  check('and the hosts a bare path word may count on are the same in both halves',
    A_PLATFORM_OR_ITS_STORAGE.every((one) => source.includes(`'${one}'`)));
  /* **AND BOTH HALVES INSIST ON A SECURE CONNECTION.** A report fetched over
   * `http:` can be replaced in flight by anything between here and there. */
  check('and both halves refuse a plain connection',
    source.includes("'https:'") && !aFileReallyComesFrom('http://storage.googleapis.com/x'));
  /* **AND NOTHING IN IT BROADCASTS.** The finding was one character wide. */
  check('and nothing in it posts to anything but this page',
    !/postMessage\([^)]*,\s*['\"]\*['\"]/.test(source));

  /* **AND THE OTHER END READS WHAT THIS END SENDS, WHICH NOTHING HELD (A42).**
   * `content.js` has no checks of its own by design, so the two halves of this
   * one message could be changed apart: an independent reviewer put the old
   * `answer.handle` line back in `content.js` ALONE and all 823 JavaScript
   * checks stayed green -- the half that actually reads the bytes was bound by
   * nothing. **And it is not a spelling mistake that is being guarded against.**
   * `answer.handle` is the handle the catcher was GIVEN BACK by whatever the
   * page left standing where `URL.createObjectURL` should be; a `content.js`
   * that reads it again reopens the whole of this, quietly, on its own. */
  const theOtherHalf = readFileSync(new URL('./content.js', import.meta.url), 'utf8');
  check('the catcher sends the file it was handed under the name the other half reads',
    source.includes('file: thing') && theOtherHalf.includes('answer.file.arrayBuffer()'));
  check('and the other half never goes back to reading the handle it was given back',
    !theOtherHalf.includes('answer.handle'));

  /* ---- EVERYTHING `content.js` BORROWS IS ACTUALLY GIVEN TO IT (2026-09-11)
   *
   * **`looksLikeAPage` WAS DECLARED THERE AND NEVER ASSIGNED**, and nothing
   * anywhere said so. It is the guard that stops a portal's sign-in page being
   * put in the seller's Drive as that day's report -- so the one moment it
   * mattered would have been a bare "looksLikeAPage is not a function" instead
   * of the refusal. **Found by a real report failing on his own panel**, not by
   * any check, because that file has none by design.
   *
   * **SO THE CHECK LIVES HERE AND READS THAT FILE.** Every name it declares to
   * borrow must be taken out of one of the two modules it imports. */
  const borrows = [...theOtherHalf.matchAll(/^ {2}let ([A-Za-z_$][\w$]*);$/gm)]
    .map((one) => one[1]);
  /* **THE COMMENTS COME OUT BEFORE THE COMMAS ARE COUNTED.** A sentence inside
   * the list has commas of its own, and split on those it reads as half a dozen
   * names nobody imports -- which reddens this check for the wrong reason. */
  const takenOut = [...theOtherHalf.matchAll(/\(\{([^}]*)\} = await import/g)]
    .flatMap((one) => one[1].replace(/\/\*[\s\S]*?\*\//g, '').split(',')
      .map((word) => word.trim())
      .filter(Boolean));
  check('there are names to check that the other half borrows at all',
    borrows.length >= 8);
  check('EVERY NAME content.js BORROWS IS REALLY TAKEN OUT OF A MODULE',
    borrows.filter((one) => one !== 'book').every((one) => takenOut.includes(one)));
  /* **AND THE ONE THAT WAS MISSING IS NAMED, so this cannot go green by the
   * pattern above quietly matching nothing.** */
  check('and the guard against a sign-in page being saved as a report is one of them',
    borrows.includes('looksLikeAPage') && takenOut.includes('looksLikeAPage'));
}

{
  /* **RUMEE'S WAY, HIS DECISION OF 2026-09-14: ONE CATCHER, IN THE PAGE BEFORE
   * THE PAGE, SWITCHED ON BY A FRESH SECRET PER FILE.**
   *
   * **WHY.** His ads Search Term Report would not land. The catcher used to be
   * put into the page only at the moment of arming -- after Flipkart's own code
   * had loaded, and code that took its own copy of `URL.createObjectURL` when it
   * loaded never calls a catcher installed later. The page then clicked an
   * anchor whose address was `blob:`, nothing stopped it, and Chrome downloaded
   * a file nobody could fetch a second time.
   *
   * **DRIVEN THE WAY CHROME DRIVES IT:** the generated `catch-early.js` runs
   * first with no secret, exactly as a `document_start` content script does,
   * and the background then arms it the way it always has. */
  const browser = installFakeChrome();
  const tab = await browser.chrome.tabs.create({ url: 'https://seller.flipkart.com/' });
  const posted = [];
  const followed = [];
  /* Read before `URL` is borrowed below -- the stand-in has no constructor. */
  const theEarlySource = readFileSync(new URL('./catch-early.js', import.meta.url), 'utf8');
  const itsOwnURL = globalThis.URL;
  const itsOwnAnchor = globalThis.HTMLAnchorElement;
  globalThis.window = {
    location: { origin: 'https://seller.flipkart.com' },
    postMessage: (data, to) => posted.push({ data, to }),
  };
  let handlesMade = 0;
  globalThis.URL = {
    createObjectURL: () => {
      handlesMade += 1;
      return `blob:https://seller.flipkart.com/h${handlesMade}`;
    },
  };
  globalThis.HTMLAnchorElement = function () {};
  globalThis.HTMLAnchorElement.prototype = { click() { followed.push(this.href); } };
  const anAnchorTo = (href) => Object.assign(
    Object.create(globalThis.HTMLAnchorElement.prototype), { href }
  );
  const theReportBytes = new Blob([new Uint8Array([4, 4, 4, 4, 4, 4, 4, 4])]);
  globalThis.window.fetch = async (address) => ({
    blob: async () => (String(address).startsWith('blob:') ? theReportBytes : null),
  });

  // eslint-disable-next-line no-new-func
  new Function(theEarlySource)();
  const theWayIn = Object.getOwnPropertyDescriptor(globalThis.window, '__kartaanArmTheCatcher');
  check('THE EARLY CATCHER LOCKS ITS ONE WAY IN AS IT LOADS',
    !!theWayIn && theWayIn.writable === false && theWayIn.configurable === false);
  const theCatcherFromTheStart = globalThis.URL.createObjectURL;

  globalThis.URL.createObjectURL({
    size: 2048, type: '', arrayBuffer: async () => new ArrayBuffer(2048),
  });
  anAnchorTo('blob:https://seller.flipkart.com/before-anything-is-armed').click();
  check('and loaded switched off, it catches nothing and stops nothing',
    posted.length === 0 && followed.length === 1);

  await armTheCatcher(browser.chrome, { tabId: tab.id, secret: 'the-flipkart-secret' });
  check('arming a page that already has it switches it on, and puts no second catcher in',
    globalThis.URL.createObjectURL === theCatcherFromTheStart);

  anAnchorTo('blob:https://seller.flipkart.com/the-report').click();
  await new Promise((done) => setTimeout(done, 10));
  check('A blob: DOWNLOAD WHILE ARMED IS STOPPED, NOT HANDED TO CHROME',
    followed.length === 1);
  check('and the file it points to is handed over, under the secret',
    posted.length === 1 && posted[0].data.file === theReportBytes
      && posted[0].data.secret === 'the-flipkart-secret');
  check('and it is addressed to this page and nowhere else',
    posted.length === 1 && posted[0].to === 'https://seller.flipkart.com');

  anAnchorTo('blob:https://seller.flipkart.com/afterwards').click();
  check('and once spent, the next one is left to the browser exactly as before',
    followed.length === 2 && posted.length === 1);

  /* **HIS CLAIMS REPORT, 2026-09-14: CAUGHT AS IT IS BUILT, THEN CLICKED.** The
   * page makes the handle and then clicks an in-page link to it. Let through,
   * Chrome starts a download whose answer beats the caught file to the walk. */
  await armTheCatcher(browser.chrome, { tabId: tab.id, secret: 'the-claims-secret' });
  const theClaimsFile = {
    size: 23462, type: 'application/octet-stream', arrayBuffer: async () => new ArrayBuffer(23462),
  };
  const theClaimsHandle = globalThis.URL.createObjectURL(theClaimsFile);
  anAnchorTo(theClaimsHandle).click();
  check('A FILE CAUGHT AS IT IS BUILT IS NOT ALSO DOWNLOADED WHEN THE PAGE CLICKS ITS HANDLE',
    followed.length === 2 && posted.length === 2 && posted[1].data.file === theClaimsFile
      && posted[1].data.secret === 'the-claims-secret');
  anAnchorTo(theClaimsHandle).click();
  anAnchorTo('blob:https://seller.flipkart.com/the-sellers-own').click();
  check('and only that one handle, once: every click after it is left to the browser',
    followed.length === 4 && posted.length === 2);

  const whatAPageCanRead = (fn) => Reflect.ownKeys(fn).map((key) => {
    try {
      return fn[key];
    } catch (cannot) {
      return null;
    }
  });
  check('and nothing a page can read off the way in or the catcher carries the secret',
    ![...whatAPageCanRead(theWayIn.value), ...whatAPageCanRead(theCatcherFromTheStart)]
      .includes('the-flipkart-secret'));

  globalThis.window = undefined;
  globalThis.URL = itsOwnURL;
  globalThis.HTMLAnchorElement = itsOwnAnchor;
}

{
  /* **A WAY IN THE PAGE COULD STILL REPLACE IS NOT OURS, AND IS NEVER HANDED
   * THE SECRET.** On a tab opened before the extension was reloaded there is no
   * early catcher, and a hostile script could have put a function of its own at
   * the same name to be called with the real secret. Unlocked, it is ignored and
   * a fresh catcher is installed as it always was. */
  const browser = installFakeChrome();
  const tab = await browser.chrome.tabs.create({ url: 'https://seller.flipkart.com/' });
  const itsOwnURL = globalThis.URL;
  const stolen = [];
  globalThis.window = {
    location: { origin: 'https://seller.flipkart.com' },
    postMessage: () => {},
  };
  globalThis.URL = { createObjectURL: () => 'blob:https://seller.flipkart.com/x' };
  globalThis.window.__kartaanArmTheCatcher = (secret) => stolen.push(secret);
  await armTheCatcher(browser.chrome, { tabId: tab.id, secret: 'must-not-leak' });
  check('A WAY IN THE PAGE COULD STILL REPLACE IS NEVER HANDED THE SECRET',
    stolen.length === 0);
  globalThis.window = undefined;
  globalThis.URL = itsOwnURL;
}

{
  /* **A LINK THAT IS NOT ON THE LIST, IN THE PAGE (HIS RULING, 2026-09-14).**
   * Flipkart's listing file came out of `window.open` on an address nobody had
   * listed, Chrome refused the pop-up, and the failure never named it. Now: a new
   * window on the page's own site is taken for the other half to prove; an
   * ordinary in-page link is left alone; a window on another site is let go and
   * SAID, with no secret, so a failure can name it. */
  const browser = installFakeChrome();
  const tab = await browser.chrome.tabs.create({ url: 'https://seller.flipkart.com/' });
  const posted = [];
  const followed = [];
  const opened = [];
  const itsOwnAnchor = globalThis.HTMLAnchorElement;
  const itsOwnCreate = URL.createObjectURL;
  globalThis.window = {
    location: {
      origin: 'https://seller.flipkart.com',
      href: 'https://seller.flipkart.com/index.html#dashboard/listings-management',
      pathname: '/index.html',
    },
    postMessage: (data, to) => posted.push({ data, to }),
    open: (address) => { opened.push(address); return {}; },
  };
  globalThis.HTMLAnchorElement = function () {};
  globalThis.HTMLAnchorElement.prototype = { click() { followed.push(this.href); } };
  const anAnchor = (href, target) => Object.assign(
    Object.create(globalThis.HTMLAnchorElement.prototype), { href, target }
  );

  await armTheCatcher(browser.chrome, { tabId: tab.id, secret: 'the-listing-secret' });
  const theListing = 'https://seller.flipkart.com/napi/listing/stockFileDownloadV2?fileName=S_listing.xls';
  const whatOpenSaid = globalThis.window.open(theListing, '_blank');
  check('A NEW WINDOW ON THE PLATFORM\'S OWN SITE, NOT ON THE LIST, IS TAKEN RATHER THAN OPENED',
    whatOpenSaid === null && opened.length === 0 && posted.length === 1
      && posted[0].data.address === theListing && posted[0].data.secret === 'the-listing-secret');

  await armTheCatcher(browser.chrome, { tabId: tab.id, secret: 'the-next-secret' });
  anAnchor('https://seller.flipkart.com/index.html#dashboard/orders').click();
  check('while an ordinary link on the same site, in the same page, is followed and not taken',
    followed.length === 1 && posted.length === 1);

  const elsewhere = 'https://files.example.com/report.xls?token=abc';
  globalThis.window.open(elsewhere, '_blank');
  check('AND A WINDOW ON ANOTHER SITE IS LET GO -- AND SAID, SO A FAILURE CAN NAME IT',
    opened.length === 1 && posted.length === 2 && posted[1].data.kartaan === DECLINED_A_LINK
      && posted[1].data.address === elsewhere);
  check('and what it says carries no secret, so nothing can be forged from it',
    posted[1].data.secret === undefined);

  globalThis.window = undefined;
  globalThis.HTMLAnchorElement = itsOwnAnchor;
  URL.createObjectURL = itsOwnCreate;
}

{
  /* **ONE RECORD OF THE CATCHER, NOT TWO.** The early file is written from
   * `catchTheNextFile`'s own source; edited by hand, or left behind after the
   * function changed, the page would catch by one rule and the background arm
   * by another. */
  const { whatTheEarlyFileHolds } = await import('../tools/write_catch_early.mjs');
  check('the early catcher on disk is exactly what its own source writes',
    readFileSync(new URL('./catch-early.js', import.meta.url), 'utf8') === whatTheEarlyFileHolds());
}

{
  /* **THE PERMISSION IT ASKS FOR IS THE ONE IT NEEDS (D135, cycle 46 R6#17).**
   * `tabs` was asked for and never used: it grants the address and title of
   * every tab the seller has open, on a machine full of their own business. */
  const manifest = JSON.parse(readFileSync(new URL('./manifest.json', import.meta.url), 'utf8'));
  check('the extension does not ask to read every tab',
    !manifest.permissions.includes('tabs'));
  check('and it asks for what putting the catcher into a page needs',
    manifest.permissions.includes('scripting'));
  /* **THE CATCHER'S OWN MODULE IS STILL NOT A CONTENT SCRIPT -- BUT ITS
   * GENERATED EARLY COPY IS, ON FLIPKART, AND THAT IS HIS DECISION OF
   * 2026-09-14.** His ads Search Term Report would not land: a catcher put in
   * only at the moment of arming comes after Flipkart's own code has loaded, and
   * code that took its own copy of `URL.createObjectURL` never calls it. He asked
   * which way has the higher success rate, was told it is the working
   * reference's -- a content script in the page's own world at `document_start`
   * -- and what that costs (D135 took exactly that away), and chose it.
   *
   * **SO THESE SAY WHAT IS NOW TRUE, NARROWLY.** One early catcher, on Flipkart
   * only, switched off until armed; nothing on Meesho, whose seven reports all
   * land without it; and nothing else at all in the page's own world. */
  const inPages = (manifest.content_scripts || []).flatMap((one) => one.js || []);
  check('the catcher\u2019s own module is not loaded on any portal page',
    !inPages.includes('catch-blob.js'));
  check('and the page half still is', inPages.includes('content.js'));
  const theEarlyOnes = (manifest.content_scripts || [])
    .filter((one) => (one.js || []).includes('catch-early.js'));
  check('THE EARLY CATCHER RUNS IN THE PAGE\u2019S OWN WORLD BEFORE THE PAGE DOES, ON FLIPKART',
    theEarlyOnes.length === 1 && theEarlyOnes[0].world === 'MAIN'
      && theEarlyOnes[0].run_at === 'document_start'
      && (theEarlyOnes[0].matches || []).length === 1
      && theEarlyOnes[0].matches[0] === 'https://seller.flipkart.com/*');
  check('and not on Meesho, whose reports all land without it',
    !theEarlyOnes.some((one) => (one.matches || []).some((m) => m.includes('meesho'))));
  check('and nothing else runs in the page\u2019s own world by default',
    (manifest.content_scripts || []).filter((one) => one.world === 'MAIN')
      .every((one) => (one.js || []).join() === 'catch-early.js'));

  /* **THE REPORT DOES NOT LIVE ON THE PORTAL'S OWN HOST, AND NOTHING ASKED THIS
   * UNTIL A25R.** Meesho hands its stock file over as a plain cross-origin
   * `.xlsx` on Google's storage host -- measured on his live panel 2026-09-05,
   * one anchor click, host `storage.googleapis.com`, and the re-fetch answered
   * 200 with 44,593 bytes. **Without this line in the manifest that re-fetch is
   * refused even though the address is right**, and every report fails with the
   * platform blamed for it. It is half of what the cancel exists to make
   * possible, and it was held by no question at all: A25R deleted the host, then
   * emptied the whole list, and all 412 checks stayed green. */
  const hosts = manifest.host_permissions || [];
  check('the host the file really lives on is allowed',
    hosts.some((one) => one.startsWith('https://storage.googleapis.com/')));
  /* **AND STILL NOT EVERYTHING.** The reference asks for `<all_urls>`; a product
   * copied into every seller's own account asks for the hosts it can name. */
  check('and it still does not ask for every address there is',
    !hosts.includes('<all_urls>') && hosts.length <= 4);
}

/* --------------- arming the download cancel, which is one line and load-bearing */

{
  /* **THE WIRE FROM THE WALK TO THE CANCEL, PROVED END TO END.** `doors.js` can
   * cancel a download inside the event and its own checks say so -- but if
   * nothing ever ARMS it, all of that is dead code and the Save-as window still
   * goes up. This asks the background the one message the page half sends before
   * a walk starts, with the REAL watcher behind it, and then starts a download.
   *
   * **AND IT IS THIS MESSAGE BECAUSE IT IS THE ONLY ONE EARLY ENOUGH.** Every
   * other message the page half sends arrives after the click that produces the
   * file. */
  const browser = installFakeChrome();
  await browser.chrome.tabs.create({ url: 'https://supplier.meesho.com/' });
  /* The catcher this message also puts into the page needs a page to be put
   * into. Lent for this block and handed back at the end of it, the same way the
   * catcher's own checks above do it. */
  const itsOwnURL = globalThis.URL;
  globalThis.window = {
    location: { origin: 'https://supplier.meesho.com' },
    postMessage: () => {},
  };
  globalThis.URL = { createObjectURL: () => 'blob:https://supplier.meesho.com/abc' };
  const watching = watchForDownloads(browser.chrome);
  wireUp(browser.chrome, {
    onDue: async () => {},
    answer: answerThePage(browser.chrome, {
      goTo: async () => {},
      takeTheFile: async () => null,
      watching,
      say: () => {},
      secret: () => 'a-secret',
    }),
  });

  await browser.aDownloadStarted({ id: 1, url: 'https://storage.example.invalid/before.xlsx' });
  check('before a walk arms anything, a download is left alone',
    browser.cancelledDownloads().length === 0);

  const armed = await browser.aPageAsked({ do: 'arm-the-catcher' });
  check('arming the catcher is answered with its secret', armed && armed.secret === 'a-secret');
  await browser.aDownloadStarted({ id: 2, url: 'https://storage.example.invalid/ours.xlsx' });
  check('and it armed the download cancel as well, so the Save-as window never appears',
    browser.cancelledDownloads().length === 1 && browser.cancelledDownloads()[0] === 2);

  globalThis.window = undefined;
  globalThis.URL = itsOwnURL;
}

/* ------------------------------- D200: the walk that outlives its own page */

/* **THE FAULT.** The walk runs inside the portal's own page, and its first step
 * is to GO somewhere -- which destroys that page. Three walks died on his own
 * Meesho panel on 5 September with "the message channel closed before a response
 * was received", which is what that teardown looks like from this side. So the
 * place in the walk has to live HERE, in storage, which is the only thing that
 * survives both the page and this worker. */

{
  const browser = installFakeChrome();
  const started = 1000;
  await beginTheWalk(browser.chrome, {
    tabId: 7, reportId: 'me_orders', dataDate: '2026-09-05', panel: 'x', startedAt: started,
  });
  check('a walk in flight is written where a page cannot lose it',
    browser.stored()[THE_WALK].reportId === 'me_orders');
  check('and the step it should be picked up at is nought to begin with',
    browser.stored()[THE_WALK].at === 0);

  const mine = await theWalkInFlight(browser.chrome, { tabId: 7, at: started + 1000 });
  check('the tab the walk is in gets it back', mine && mine.reportId === 'me_orders');
  /* **EVERY PORTAL PAGE THE SELLER OPENS ASKS THIS.** Answered loosely, an
   * ordinary page somebody opened for themselves starts clicking through a
   * report of its own accord. */
  check('and no other tab does',
    (await theWalkInFlight(browser.chrome, { tabId: 8, at: started + 1000 })) === null);
  /* **AND IT RUNS OUT.** A tab closed mid-walk, or a page that never draws,
   * would otherwise leave this here for ever -- and the next portal page that
   * happened to open with that same tab number would pick up an old night's walk
   * and start clicking. */
  check('and a walk that has run out of time is not picked up by anybody',
    (await theWalkInFlight(browser.chrome, { tabId: 7, at: started + A_WALK_LASTS_MS })) === null);

  await theWalkMovedOn(browser.chrome, { tabId: 7, at: 4 });
  check('moving the place on writes it down', browser.stored()[THE_WALK].at === 4);
  check('and moving it on for some other tab does nothing at all',
    (await theWalkMovedOn(browser.chrome, { tabId: 8, at: 99 })) === null
    && browser.stored()[THE_WALK].at === 4);

  /* **THE PLACE SURVIVES THE WORKER BEING SHUT DOWN, which is the whole reason
   * it is in storage.** Chrome kills an idle service worker after thirty
   * seconds; a Meesho orders export takes five minutes and goes somewhere twice
   * on the way. Anything held in a variable here is gone before the second page
   * has finished drawing. */
  browser.shutTheWorkerDown();
  const after = await theWalkInFlight(browser.chrome, { tabId: 7, at: started + 1000 });
  check('and the place survives Chrome shutting the worker down mid-walk',
    after && after.at === 4 && after.reportId === 'me_orders');

  await endTheWalk(browser.chrome, {
    tabId: 7, answer: { state: 'landed', reportId: 'me_orders' }, at: started + 2000,
  });
  check('ending the walk leaves the answer behind rather than throwing it away',
    browser.stored()[THE_WALK].answer.state === 'landed');
  check('and a finished walk is not picked up again by the next page that loads',
    (await theWalkInFlight(browser.chrome, { tabId: 7, at: started + 2100 })) === null);
}

{
  /* **THE ORDERING THAT IS THE WHOLE OF D200: the place is written BEFORE the
   * page is sent anywhere.** Written after, the page that would have written it
   * has already been destroyed, nothing ever asks where the walk was, and the
   * walk stops for ever -- silently, at night, with nobody watching. */
  const browser = installFakeChrome();
  await browser.chrome.tabs.create({ url: 'https://supplier.meesho.com/panel/x/orders/' });
  let placeWhenItWentSomewhere = 'the page was sent away before the place was written';
  const watching = watchForDownloads(browser.chrome);
  wireUp(browser.chrome, {
    onDue: async () => {},
    answer: answerThePage(browser.chrome, {
      /* Read at the very moment the page is being destroyed. */
      goTo: async () => {
        const held = await browser.chrome.storage.local.get(THE_WALK);
        placeWhenItWentSomewhere = held[THE_WALK] && held[THE_WALK].at;
      },
      takeTheFile: async () => null,
      watching,
      say: () => {},
      secret: () => 'a-secret',
    }),
  });
  await beginTheWalk(browser.chrome, {
    tabId: 1, reportId: 'me_orders', dataDate: '2026-09-05', startedAt: Date.now(),
  });
  await browser.aPageAsked({
    do: 'go', address: 'https://supplier.meesho.com/panel/x/o', patience: 5, at: 7,
  });
  check('the place is already written down at the moment the page is sent away',
    placeWhenItWentSomewhere === 7);
}

{
  /* **A PAGE THAT NEVER DRAWS ENDS THE WALK, because there is nobody else left
   * to end it.** The page that asked is already gone, so a failure thrown at its
   * caller is thrown at nothing: the walk would sit in storage until its time ran
   * out, and the day's report would simply be missing with no word anywhere. */
  const browser = installFakeChrome();
  await browser.chrome.tabs.create({ url: 'https://supplier.meesho.com/panel/x/orders/' });
  const watching = watchForDownloads(browser.chrome);
  wireUp(browser.chrome, {
    onDue: async () => {},
    answer: answerThePage(browser.chrome, {
      goTo: async () => {
        throw new Error('The page at https://x had not finished drawing after 30 seconds.');
      },
      takeTheFile: async () => null,
      watching,
      say: () => {},
      secret: () => 'a-secret',
    }),
  });
  await beginTheWalk(browser.chrome, {
    tabId: 1, reportId: 'me_orders', dataDate: '2026-09-05', startedAt: Date.now(),
  });
  await browser.aPageAsked({
    do: 'go', address: 'https://x', patience: 30, at: 1,
    reportId: 'me_orders', dataDate: '2026-09-05',
  });
  const stuck = browser.stored()[THE_WALK];
  check('a page that never draws ends the walk rather than leaving it hanging',
    stuck.answer && stuck.answer.state === 'failed');
  check('and the failure says the page never drew, against the report it was for',
    stuck.answer.say.includes('had not finished drawing')
    && stuck.answer.reportId === 'me_orders');
}

{
  /* **THE ANSWER COMES BACK AS ITS OWN MESSAGE, NOT AS A REPLY**, because the
   * reply to the message that started the walk went down with the first page.
   * **And the download-cancel is disarmed with it** -- left armed, the next file
   * the seller downloaded by hand would vanish in front of them. A25R found this
   * open and nothing could close it, because nothing here knew a walk had
   * ended. */
  const browser = installFakeChrome();
  await browser.chrome.tabs.create({ url: 'https://supplier.meesho.com/panel/x/orders/' });
  const watching = watchForDownloads(browser.chrome);
  wireUp(browser.chrome, {
    onDue: async () => {},
    answer: answerThePage(browser.chrome, {
      goTo: async () => {},
      takeTheFile: async () => null,
      watching,
      say: () => {},
      secret: () => 'a-secret',
    }),
  });
  await beginTheWalk(browser.chrome, {
    tabId: 1, reportId: 'me_orders', dataDate: '2026-09-05', startedAt: Date.now(),
  });
  watching.expectAFile();
  await browser.aPageAsked({
    do: 'walk-done', answer: { state: 'landed', reportId: 'me_orders', size: 44593 },
  });
  check('a walk saying it is done writes its answer where a run can read it',
    browser.stored()[THE_WALK].answer.size === 44593);
  await browser.aDownloadStarted({ id: 9, url: 'https://storage.example.invalid/the-sellers.xlsx' });
  check('and the cancel is disarmed, so the next download the seller starts is left alone',
    browser.cancelledDownloads().length === 0);
}

{
  /* **A TAB CLOSED MID-WALK IS A NAMED FAILURE, NOT A SILENT HANG.** Nothing
   * will ever ask where that walk was again. Without this the record sits saying
   * "running" until its time runs out and the day's report is simply missing. */
  const browser = installFakeChrome();
  const tab = await browser.chrome.tabs.create({ url: 'https://supplier.meesho.com/panel/x/o/' });
  const watching = watchForDownloads(browser.chrome);
  wireUp(browser.chrome, {
    onDue: async () => {},
    answer: answerThePage(browser.chrome, {
      goTo: async () => {},
      takeTheFile: async () => null,
      watching,
      say: () => {},
      secret: () => 's',
    }),
  });
  await beginTheWalk(browser.chrome, {
    tabId: tab.id, reportId: 'me_orders', dataDate: '2026-09-05', startedAt: Date.now(),
  });
  await browser.chrome.tabs.remove(tab.id);
  const ended = browser.stored()[THE_WALK];
  check('a tab closed part way through a walk ends it rather than leaving it hanging',
    ended.answer && ended.answer.state === 'failed');
  check('and it says the tab was closed, against the report it was fetching',
    ended.answer.say.includes('was closed') && ended.answer.reportId === 'me_orders');
}

{
  /* **AND CLOSING SOME OTHER TAB DOES NOTHING.** The seller has their own tabs
   * open; closing one of them must not end a walk going on elsewhere. */
  const browser = installFakeChrome();
  const walkTab = await browser.chrome.tabs.create({ url: 'https://supplier.meesho.com/p/o/' });
  const otherTab = await browser.chrome.tabs.create({ url: 'https://supplier.meesho.com/p/home' });
  const watching = watchForDownloads(browser.chrome);
  wireUp(browser.chrome, {
    onDue: async () => {},
    answer: answerThePage(browser.chrome, {
      goTo: async () => {},
      takeTheFile: async () => null,
      watching,
      say: () => {},
      secret: () => 's',
    }),
  });
  await beginTheWalk(browser.chrome, {
    tabId: walkTab.id, reportId: 'me_orders', dataDate: '2026-09-05', startedAt: Date.now(),
  });
  await browser.chrome.tabs.remove(otherTab.id);
  check('closing one of the seller other tabs leaves the walk alone',
    browser.stored()[THE_WALK].answer === null);
}

{
  /* **AND THE PAGE HALF CAN ASK FOR IT.** This is the message every portal page
   * the seller opens sends, and the answer is almost always nothing. */
  const browser = installFakeChrome();
  await browser.chrome.tabs.create({ url: 'https://supplier.meesho.com/panel/x/orders/' });
  const watching = watchForDownloads(browser.chrome);
  wireUp(browser.chrome, {
    onDue: async () => {},
    answer: answerThePage(browser.chrome, {
      goTo: async () => {},
      takeTheFile: async () => null,
      watching,
      say: () => {},
      secret: () => 's',
    }),
  });
  check('an ordinary portal page asking is told there is nothing to carry on',
    ((await browser.aPageAsked({ do: 'resume?' })) || {}).walk === null);
  await beginTheWalk(browser.chrome, {
    tabId: 1, reportId: 'me_orders', dataDate: '2026-09-05', at: 4, startedAt: Date.now(),
  });
  const carryOn = (await browser.aPageAsked({ do: 'resume?' })).walk;
  check('and the page the last go landed on is told where to pick the walk up',
    carryOn && carryOn.reportId === 'me_orders' && carryOn.at === 4);
}

{
  /* **THE SLOW NIGHT, AND IT IS THE ONE THAT COULD NEVER FAIL WHILE SOMEBODY WAS
   * WATCHING.** "The page finished drawing" means Chrome finished fetching
   * everything on it -- adverts and trackers included. The page half runs long
   * before that, at `document_idle`. So on a heavy portal on a slow connection
   * the walk can be several steps further on while Chrome still calls the tab
   * busy, and the go's own patience runs out on a walk that is working
   * perfectly. Ending it there kills a good walk, at night, on a slow line, and
   * never once on a fast one. */
  const browser = installFakeChrome();
  await browser.chrome.tabs.create({ url: 'https://supplier.meesho.com/panel/x/orders/' });
  const watching = watchForDownloads(browser.chrome);
  wireUp(browser.chrome, {
    onDue: async () => {},
    answer: answerThePage(browser.chrome, {
      goTo: async () => {
        /* The page really drew and really took the walk up -- and only THEN did
         * Chrome give up on the last advert. */
        await browser.aPageAsked({ do: 'resume?' });
        throw new Error('The page at https://x had not finished drawing after 30 seconds.');
      },
      takeTheFile: async () => null,
      watching,
      say: () => {},
      secret: () => 'a-secret',
    }),
  });
  await beginTheWalk(browser.chrome, {
    tabId: 1, reportId: 'me_orders', dataDate: '2026-09-05', startedAt: Date.now(),
  });
  await browser.aPageAsked({
    do: 'go', address: 'https://x', patience: 30, at: 1,
    reportId: 'me_orders', dataDate: '2026-09-05',
  });
  check('a walk a page has already taken up is not killed by the go running out of patience',
    browser.stored()[THE_WALK].answer === null);
  check('and it is still there for that page to finish',
    (await theWalkInFlight(browser.chrome, { tabId: 1 })) !== null);
}

{
  /* **THE BOOKS ARE OPENED BEFORE THE PAGE IS TOLD ANYTHING.** The walk's very
   * first step is a `go`, so the page being asked to start can be destroyed
   * within a second of hearing. With no record written by then, `go` has nothing
   * to move on, the next page asks where the walk was and is told nothing, and
   * the walk is over before it began -- which reads exactly like the fault all
   * of this exists to fix. */
  const browser = installFakeChrome();
  const openAt = 'https://supplier.meesho.com/panel/v3/new/';
  /* The window our walk gets is made by the product, so let it finish drawing
   * the way a real one does. */
  const started = startAWalk(browser.chrome, {
    reportId: 'me_catalog', dataDate: '2026-09-05', panel: 'xuptj', openAt, patience: 30,
  });
  for (let round = 0; round < 40; round += 1) {
    // eslint-disable-next-line no-await-in-loop
    await Promise.resolve();
    for (const one of browser.tabs()) browser.theTabFinishedDrawing(one.id);
  }
  await started;

  check('starting a walk opens a window of our own rather than using the seller own',
    browser.windows().length === 1
    && (!WALK_IN_HIS_OWN_WINDOW || browser.windows()[0].focused === true)
    && browser.windows()[0].state === 'maximized');
  check('and the walk was written down before that window went anywhere near the portal',
    browser.stored()[THE_WALK].reportId === 'me_catalog'
    && browser.stored()[THE_WALK].at === 0);
  check('and the seller own panel name was written with it',
    browser.stored()[THE_WALK].panel === 'xuptj');
  /* **NOTHING IS PUSHED AT THE PAGE.** An earlier version messaged the tab the
   * instant it was made -- at a blank page, where our own half is not running
   * and nothing was listening. The page asks; it is never told. */
  check('and nothing was pushed at a page that was not there to hear it',
    browser.sentToPages().length === 0);
  check('and the walk is there for the first page to ask for',
    (await theWalkInFlight(browser.chrome, { tabId: browser.stored()[THE_WALK].tabId })) !== null);
  check('and the tab it is in really went to the portal',
    browser.tabs().find((one) => one.id === browser.stored()[THE_WALK].tabId).url === openAt);
  /* **AND WHERE IT STARTS FROM IS THE RECIPE'S BUSINESS, NOT THIS FILE'S.** */
  check('a walk with nowhere to start from is refused rather than guessed at',
    (await said(() => startAWalk(browser.chrome, { reportId: 'x', dataDate: 'y' })))
      .includes('which portal page to start from'));
}

{
  /* **THE BOOKS ARE OPEN BEFORE THE TAB IS SENT AT THE PORTAL, and this stands
   * at the exact moment it happens rather than looking afterwards.** The page
   * asks for its walk the instant it loads. Written after, the first page has
   * already asked and been told nothing, and the walk is over before it began --
   * which reads exactly like the fault all of this exists to fix. */
  const browser = installFakeChrome();
  let writtenWhenItWentToThePortal = 'the tab was sent at the portal with the books still shut';
  await startAWalk(browser.chrome, {
    reportId: 'me_catalog',
    dataDate: '2026-09-05',
    openAt: 'https://supplier.meesho.com/panel/v3/new/',
    go: async () => {
      const held = await browser.chrome.storage.local.get(THE_WALK);
      writtenWhenItWentToThePortal = held[THE_WALK] ? held[THE_WALK].reportId : 'nothing written';
    },
  });
  check('the walk is already written down at the moment the tab is sent at the portal',
    writtenWhenItWentToThePortal === 'me_catalog');
}

{
  /* **A53: A SLOW FIRST LOAD IS NOT "COULD NOT BE STARTED" WHEN A PAGE ALREADY HAS
   * THE WALK.** His `fk_claims` was written off at 60 s while its walk went on and
   * put the file in Drive. */
  const browser = installFakeChrome();
  const slow = () => ({
    reportId: 'fk_claims',
    dataDate: '2026-09-14',
    openAt: 'https://seller.flipkart.com/index.html#dashboard/payments/spf',
    go: async ({ storage }, { tabId }) => {
      const held = (await storage.local.get(THE_WALK))[THE_WALK];
      if (pickedUp) await storage.local.set({ [THE_WALK]: { ...held, tabId, pickedUpFrom: 0 } });
      throw new Error('The page had not finished drawing after 60 seconds.');
    },
  });
  let pickedUp = true;
  const kept = await said(() => startAWalk(browser.chrome, slow()));
  check('a walk a page already picked up is not failed for a slow first load', kept === '');
  pickedUp = false;
  await browser.chrome.storage.local.remove(THE_WALK);
  const lost = await said(() => startAWalk(browser.chrome, slow()));
  check('while one no page picked up still fails, in the load\'s own words',
    lost.includes('had not finished drawing'));
}

{
  /* **ONLY THE PAGE THAT CURRENTLY HAS THE WALK MAY END IT, and this is a fault
   * his own Chrome reported while this was being built:** "The page keeping the
   * extension port is moved into back/forward cache, so the message channel is
   * closed."
   *
   * A page the walk has LEFT is not always destroyed. Chrome may freeze it in
   * the back/forward cache instead, with its `go` message still half-said. Thaw
   * it -- the seller pressing Back is enough -- and that message fails, the walk
   * inside that old page throws, and the OLD page reports a failure for a walk a
   * NEWER page is running perfectly. The day's report would be filed as broken
   * while it was in fact being fetched. */
  const browser = installFakeChrome();
  await browser.chrome.tabs.create({ url: 'https://supplier.meesho.com/p/o/' });
  const watching = watchForDownloads(browser.chrome);
  wireUp(browser.chrome, {
    onDue: async () => {},
    answer: answerThePage(browser.chrome, {
      goTo: async () => {},
      takeTheFile: async () => null,
      watching,
      say: () => {},
      secret: () => 's',
    }),
  });
  await beginTheWalk(browser.chrome, {
    tabId: 1, reportId: 'me_orders', dataDate: '2026-09-05', at: 0, startedAt: Date.now(),
  });
  /* The first page hands the walk on at step 4, and the page that lands there
   * takes it up. */
  await browser.aPageAsked({ do: 'go', address: 'https://x', patience: 5, at: 4 });
  await browser.aPageAsked({ do: 'resume?' });

  /* Now the frozen first page thaws and says the walk failed. */
  const refused = await browser.aPageAsked({
    do: 'walk-done', from: 0,
    answer: { state: 'failed', reportId: 'me_orders', say: 'the message channel closed' },
  });
  check('a page the walk has left cannot end the walk that is still running',
    refused && refused.ended === false && refused.stale === true);
  check('and the walk is untouched, still there for the page that really has it',
    browser.stored()[THE_WALK].answer === null);

  /* And the page that really has it is heard. */
  const heard = await browser.aPageAsked({
    do: 'walk-done', from: 4, answer: { state: 'landed', reportId: 'me_orders', size: 44593 },
  });
  check('while the page that really has the walk is heard',
    heard && heard.ended === true && browser.stored()[THE_WALK].answer.size === 44593);
}

/* ------------------------------ D200: something has to wake this worker at all */

{
  /* **`makeSureTheClockIsSet` IS ASKED EVERY TIME THIS WORKER STARTS, WHICH IS
   * THE RIGHT SHAPE -- BUT NOTHING STARTS A WORKER THAT NOTHING IS WAKING.** If
   * the daily alarm is cleared while Chrome is running, the one thing that would
   * have woken this worker tomorrow is the thing that has gone, so the check
   * that would have put it back never runs. That is the nine-day outage, and the
   * shape above narrows it rather than closing it. */
  const browser = installFakeChrome();
  const made = await makeSureTheWorkerIsWoken(browser.chrome);
  check('something is asked to wake this worker regularly', made === true);
  check('and it goes off every two minutes',
    theAlarm(browser, STAY_AWAKE).periodInMinutes === EVERY_TWO_MINUTES);
  /* **CHROME REFUSES ANYTHING UNDER HALF A MINUTE**, in its own words, so an
   * alarm asked for too often is an alarm that never arrives. */
  check('and that is comfortably above the half minute Chrome refuses to honour',
    EVERY_TWO_MINUTES >= 0.5);
  check('and it is asked to survive a browser restart',
    theAlarm(browser, STAY_AWAKE).persistAcrossSessions === true);
  check('and asking twice does not make a second one',
    (await makeSureTheWorkerIsWoken(browser.chrome)) === false);
}

{
  /* **THE OUTAGE, CLOSED.** The daily alarm is cleared while Chrome runs.
   * Neither lifecycle event fires. But something still wakes this worker -- and
   * waking is when the daily alarm is put back. */
  const browser = installFakeChrome();
  await wireUp(browser.chrome, { onDue: async () => {} });
  check('wiring the worker up asks for both alarms, not just the daily one',
    theAlarm(browser, DAILY) !== null && theAlarm(browser, STAY_AWAKE) !== null);

  browser.forgetTheAlarms();
  check('and here they are both gone, with Chrome still running',
    browser.alarms().length === 0);

  /* Whatever wakes it next -- and with a two-minute alarm something will --
   * puts the daily clock back. */
  await browser.chrome.alarms.create(STAY_AWAKE, { periodInMinutes: EVERY_TWO_MINUTES });
  await browser.chrome.alarms.onAlarm.happened({ name: STAY_AWAKE });
  check('and the waking alarm going off puts the daily clock back',
    theAlarm(browser, DAILY) !== null);
}

{
  /* **AND IT IS NOT THE DAILY RUN.** A worker woken every two minutes that also
   * ran the night's fetch would fetch every report seven hundred times a day. */
  const browser = installFakeChrome();
  let due = 0;
  await wireUp(browser.chrome, { onDue: async () => { due += 1; } });
  await browser.chrome.alarms.onAlarm.happened({ name: STAY_AWAKE });
  check('being woken is not the same as being due, so nothing is fetched',
    due === 0);
  await browser.chrome.alarms.onAlarm.happened({ name: DAILY });
  check('while the daily alarm really is the one that fetches', due === 1);
}

{
  /* **WHICH WINDOW WAS OURS CANNOT OUTLIVE THE SESSION THAT GAVE THE NUMBER
   * MEANING (A26R, A26R3).** The full case, and why `onStartup` was not enough,
   * is driven in `doors.test.js`. What is checked here is that nothing in the
   * wiring puts it back into storage that outlives a session. */
  const browser = installFakeChrome();
  const ours = await aTabToWalkIn(browser.chrome);
  await wireUp(browser.chrome, { onDue: async () => {} });
  check('our own window is remembered only for as long as the numbers mean anything',
    browser.storedForTheSession()[OUR_WINDOW] === ours.windowId
    && browser.stored()[OUR_WINDOW] === undefined);
  /* **AND NOTHING HAS TO REMEMBER TO CLEAR IT**, which is the point of putting
   * it there: an earlier fix hung it on `chrome.runtime.onStartup`, and that
   * fires at nobody when the extension is switched off. */
  browser.theSessionEnded();
  check('and it is gone once the session that gave it meaning has ended',
    browser.storedForTheSession()[OUR_WINDOW] === undefined);
  /* **WHILE THE WALK ITSELF STAYS IN `local`**, because a walk in flight must
   * survive the worker being shut down mid-step, which is a different thing
   * from the session ending. */
  await beginTheWalk(browser.chrome, {
    tabId: 1, reportId: 'me_orders', dataDate: '2026-09-05', startedAt: Date.now(),
  });
  browser.shutTheWorkerDown();
  check('while the walk in flight is kept where the worker being shut down cannot lose it',
    browser.stored()[THE_WALK].reportId === 'me_orders');
}

{
  /* **A CHECK THAT SAYS WHAT IS TRUE RATHER THAN WHAT IS WANTED (A26R).**
   *
   * The armed download-cancel lives in a VARIABLE in this worker, and it has to
   * -- the cancel must happen with no `await` in front of it or Chrome's Save-as
   * window is already up. But Chrome shuts this worker down after thirty seconds
   * of quiet, and during a `wait-for` step NOTHING reaches this worker at all:
   * `driver.js` never touches `chrome`, so every look, click and page read
   * happens in the page. `me_orders` waits up to 60 seconds at step 7 and
   * `fk_orders` up to 120 at step 3.
   *
   * **SO THE ARM IS LOST ACROSS THE LONGEST RECIPES, AND THAT IS A DEPARTURE
   * FROM D196**, which was set the same day this was written and says a Save-as
   * window on an unattended seller is "the worst failure this product can have".
   * **IT IS NOT FIXED HERE AND THIS CHECK DOES NOT PRETEND IT IS.** It pins the
   * fault so that whoever fixes it sees this go red, rather than leaving a check
   * that reads as covering something it never touches. */
  const browser = installFakeChrome();
  let watching = watchForDownloads(browser.chrome);
  watching.expectAFile();
  browser.shutTheWorkerDown();
  /* What Chrome does next: starts the worker again, and `worker.js`'s top-level
   * line builds a brand new watcher with nothing armed. */
  watching = watchForDownloads(browser.chrome);
  await browser.aDownloadStarted({ id: 1, url: 'https://storage.example.invalid/ours.xlsx' });
  check('KNOWN FAULT, not fixed: the armed cancel does NOT survive the worker being shut down',
    browser.cancelledDownloads().length === 0);
  check('and the address is still caught, so the file itself is not lost -- only the cancel is',
    watching.seen().length === 1);
}

{
  /* **A WALK NOBODY IS GOING TO FINISH IS WRITTEN DOWN, and until this existed
   * NOTHING ANYWHERE DID THAT (A26R3).** A walk's answer was only ever written
   * by the page saying `walk-done` or by the tab being closed. A page that could
   * not speak at all -- the message failing, the worker gone, the page torn down
   * between two lines -- left the record sitting saying nothing, for ever. That
   * is "a run that was interrupted wrote nothing down", arriving by a door
   * nobody had watched. */
  const browser = installFakeChrome();
  const began = 1000;
  await beginTheWalk(browser.chrome, {
    tabId: 1, reportId: 'me_orders', dataDate: '2026-09-05', startedAt: began,
  });

  check('a walk still within its time is left alone',
    (await sweepUpAnAbandonedWalk(browser.chrome, { at: began + 1000 })) === null
    && browser.stored()[THE_WALK].answer === null);

  const swept = await sweepUpAnAbandonedWalk(browser.chrome, { at: began + A_WALK_LASTS_MS });
  check('but one that has run out of time is written down rather than left silent',
    swept !== null && browser.stored()[THE_WALK].answer.state === 'failed');
  check('and it says it stopped and never said why, against the report it was for',
    browser.stored()[THE_WALK].answer.say.includes('never said what happened')
    && browser.stored()[THE_WALK].answer.reportId === 'me_orders');
  /* **AND IT IS NOT SWEPT TWICE.** A second answer written over the first would
   * turn a real failure into this one. */
  check('and a walk that already has an answer is not written over',
    (await sweepUpAnAbandonedWalk(browser.chrome, { at: began + A_WALK_LASTS_MS + 1 })) === null);
}

{
  /* **AND IT REALLY HANGS OFF THE ALARM THAT WAKES THIS WORKER**, which is the
   * only thing that happens when nothing else is happening. */
  const browser = installFakeChrome();
  await wireUp(browser.chrome, { onDue: async () => {} });
  await beginTheWalk(browser.chrome, {
    tabId: 1, reportId: 'me_orders', dataDate: '2026-09-05', startedAt: 0,
  });
  await browser.chrome.alarms.onAlarm.happened({ name: STAY_AWAKE });
  check('being woken is what notices a walk nobody is going to finish',
    browser.stored()[THE_WALK].answer !== null
    && browser.stored()[THE_WALK].answer.state === 'failed');
}

/* ── The debug relay, and the two things about it worth proving ──────────────
 *
 * **THE WHOLE SAFETY CLAIM IS THAT TURNING IT OFF LEAVES NOTHING TO REACH.**
 * `content.js` has no checks by design, so the one thing that can be proved
 * about it from here is the shape of the file: its relay listener sits inside
 * `if (RELAY_TO_THE_PAGE)`, which means off it is never registered at all --
 * not registered and ignoring, not there. */
/* **AND IT SHIPS OFF (review finding, 2026-10-05).** On, any script on a portal page -- an advert, a
 * tag manager -- shares the page's origin and could ask the extension to run syncs, burn the
 * allowance, reload itself or read the panel's state. It is a development aid he switches on by hand. */
check('the page relay is OFF in what ships, so no script on a portal page can drive the extension',
  RELAY_TO_THE_PAGE === false);
{
  const page = readFileSync(new URL('./content.js', import.meta.url), 'utf8');
  const behindTheConstant = page.slice(page.indexOf('if (RELAY_TO_THE_PAGE) {'));
  const relayListens = behindTheConstant.indexOf("window.addEventListener('message'");
  check('with the relay off no relay listener is registered at all',
    page.indexOf('if (RELAY_TO_THE_PAGE) {') !== -1 && relayListens !== -1
    /* And it is the only `message` listener after that point, so the guarded
     * one above it is untouched and outside. */
    && behindTheConstant.indexOf("window.addEventListener('message'",
      relayListens + 1) === -1);

  /* **AND OFF IT ALSO STOPS BEING ANSWERED**, which is the other half: the
   * panel's door opens for the relay only while it is on, and never for the
   * questions that connect a Drive or move the clock. */
  check('the relay is answered two questions while it is on, and none while it is off',
    theRelayAllows(true, { do: 'run-now' }) === true
    && theRelayAllows(true, { do: 'how-it-stands' }) === true
    && theRelayAllows(true, { do: 'reload-the-extension' }) === true
    && theRelayAllows(true, { do: 'connect-the-drive' }) === false
    && theRelayAllows(false, { do: 'run-now' }) === false);
}

const EXPECTED = 247;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
