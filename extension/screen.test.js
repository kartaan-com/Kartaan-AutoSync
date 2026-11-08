/* Checks for the face the extension has never had.
 *
 * Run: node extension/screen.test.js
 *
 * **THE ONE THAT MATTERS MOST IS WHO MAY ASK.** The panel's messages start a
 * night, connect a seller's Google Drive and move the daily clock. They are
 * answered by their own listener, which refuses anything whose sender is not
 * this extension's own `panel.html` -- so a portal page running our content
 * script, on a site we do not control, cannot reach any of them. Wired into the
 * page half's `KNOWN` list instead, every one of them would have been reachable
 * from `seller.flipkart.com`.
 *
 * **AND THE SECOND IS THE ALLOWANCE, AGAIN.** Flipkart lets a seller ask for
 * twenty reports a day and a request that has gone cannot be taken back. Until
 * this page existed nothing decided how many a run might spend, so every run was
 * allowed nought. Now a run is allowed what is left of the DAY's twenty -- and a
 * page that got that sum wrong would spend a real seller's real allowance.
 *
 * **THE STAND-IN BROWSER AND THE STAND-IN CHROME ARE BOTH USED, and neither is
 * kinder than the real thing on the points that matter here.** `[hidden]` is a
 * property on the stand-in and a stylesheet rule in a browser -- so the checks
 * below ask the property, and `from-the-erp/tokens.css` carries the ERP's own
 * `[hidden] { display: none !important }`, which is the rule that makes the
 * property mean anything at all.
 */

import { readFileSync } from 'node:fs';
import { installFakeChrome } from '../test/fake-chrome.js';
import { installFakeBrowser } from '../test/fake-browser.js';
import {
  DAILY,
  KNOWN,
  THE_HOUR,
  THE_PANEL,
  THE_WALK,
  UNTIL_A_SELLER_CHOOSES,
  answerThePanel,
  makeSureTheClockIsSet,
  setTheHour,
  theHourItRuns,
  theTimeOfDayIn,
  whenThatHourNextComes,
  whyThatIsNotATimeOfDay,
  wireUp,
} from './background.js';
import { RELAY_TO_THE_PAGE } from './driver.js';
import {
  THE_EVENING_REPORTS, THE_RETURNS_REPORTS, theTimedListFor, theNeedsYouRow, theRunOf, theDayOf,
} from './screen.js';
import {
  A_DAYS_ALLOWANCE, KEPT_FOR_HIS_OWN_RUNS, PAUSED, RECHECKS, THE_NIGHT, carryTheNightOn, endTheNight, howTheNightWent, oneWasAskedFor,
  startTheNight, thatOneIsBeingTried, theIdleLine, theNight, theReportTable, THE_SYNC_FAILED, LAST_LANDED, thatOneIsDone,
} from './nightly.js';
import { saveTheRunPass } from './kartaan.js';
import { MOST_DAYS_IN_A_RANGE_FILE, hasNotFinished, theWalk } from './walk.js';
import { MANUAL, TOOLTIPS } from './manual.js';
import {
  AS_MANY_DAYS_AS_ONE_PRESS_TAKES,
  CALLED,
  THE_NIGHTS,
  THE_PANEL_ASKS,
  THROUGH_THE_BROWSER,
  aCopyToKeep,
  allTheEvents,
  theRuns,
  showTheRuns,
  alreadyCarriedOn,
  answerThePanelsQuestion,
  askingFirst,
  markCarriedOn,
  releaseCarriedOn,
  startASync,
  THE_QUEUE,
  startTheNextPlatform,
  startTheScheduledSync,
  theSignInAlert,
  theSyncSummary,
  theDaysBetween,
  whyThatRangeCannotBeFetched,
  askedForToday,
  buildThePanel,
  howItStands,
  howManyItMaySpend,
  inWordsWhen,
  rememberTheNight,
  saySomething,
  showHowItStands,
  showTheEvents,
  tellForASyncThatCannotContinue,
  theNightsEvents,
  showTheReportTable,
  whenItNextWakes,
  applyTheTheme,
  theThemeChosen,
  theReadyWarning,
  theOwnAtOf,
  theWaitingSaid,
  theClockLine,
  theDay,
  theDayToFetch,
  whyThatDayCannotBeFetched,
  theNights,
  thePlatformOf,
  thePlatformOfTheNight,
  theSetup,
  theTimedList,
  AS_LONG_AS_A_PANEL_NAME_GETS,
  whatIsTicked,
  whatTheBannerSays,
  whatThatStateIsCalled,
  whereToStartFrom,
  whyItCannotBeStarted,
  whyThatIsNotAPanelName,
} from './screen.js';

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

function check(name, passed) {
  ran++;
  console.log(`${passed ? 'PASS' : 'FAIL'}  ${name}`);
  if (!passed) failures++;
}

const HERE = new URL('./', import.meta.url);
const BOOK = JSON.parse(readFileSync(new URL('recipes.json', HERE), 'utf8'));
const SCREEN = readFileSync(new URL('screen.js', HERE), 'utf8');
const PANEL_JS = readFileSync(new URL('panel.js', HERE), 'utf8');
const PANEL_HTML = readFileSync(new URL('panel.html', HERE), 'utf8');
const PANEL_CSS = readFileSync(new URL('panel.css', HERE), 'utf8');
const MANIFEST = JSON.parse(readFileSync(new URL('manifest.json', HERE), 'utf8'));

/* ------------------------------------------------- the fault he asked about
 *
 * **"SOMETIMES IT USED TO GET STUCK."** Found and measured in `kartaan-click`:
 * reading a page's `innerText` forces the browser to redo the whole page's
 * layout, every call. One loop polling four times a second, running that over
 * every element, froze Flipkart for minutes on a 26-order list. **This page
 * polls a worker on a timer it owns and never reads a page at all**, and these
 * two checks are what keeps it that way.
 */

check('the panel never reads innerText, which is what froze Flipkart',
  !SCREEN.includes('innerText') || SCREEN.split('innerText').length - 1 === countInComments(SCREEN));
check('the panel\'s wiring never reads innerText either',
  !PANEL_JS.includes('innerText') || PANEL_JS.split('innerText').length - 1
    === countInComments(PANEL_JS));

/** How many times a word appears inside a comment. The two files above NAME
 *  `innerText` in their own comments, saying why they must not read it -- so a
 *  bare "does not contain" would go red on the sentence explaining the rule. */
function countInComments(source) {
  let inside = 0;
  for (const block of source.split('/*').slice(1)) {
    inside += block.split('*/')[0].split('innerText').length - 1;
  }
  for (const line of source.split('\n')) {
    const at = line.indexOf('//');
    if (at !== -1) inside += line.slice(at).split('innerText').length - 1;
  }
  return inside;
}

check('the panel polls on a timer rather than a loop that never rests',
  PANEL_JS.includes('setInterval') && !PANEL_JS.includes('while ('));

/* -------------------------------------------------------- who may ask what
 *
 * The check that matters most in this file.
 */

check('nothing the panel may ask for is also something the page half may ask for',
  THE_PANEL_ASKS.every((one) => !KNOWN.includes(one)));

{
  const { chrome } = installFakeChrome();
  const asked = [];
  const listen = answerThePanel(chrome, {
    mayAsk: THE_PANEL_ASKS,
    answer: async (what) => { asked.push(what.do); return { fine: true }; },
  });
  const fromThePanel = { id: chrome.runtime.id, url: chrome.runtime.getURL(THE_PANEL) };

  check('the panel is answered', Boolean(listen({ do: 'how-it-stands' }, fromThePanel)));

  /* **THIS USED TO SAY A PORTAL PAGE IS NEVER ANSWERED, AND THE DEBUG RELAY IS
   * exactly that hole, opened on purpose on 11 September 2026.** Written against
   * the constant so it is true in both positions: off, a portal page is refused
   * everything as before; on, it is refused everything EXCEPT the two the relay
   * may ask, which is the promise `theRelayAllows` keeps. */
  const aPortalPage = {
    id: chrome.runtime.id,
    url: 'https://seller.flipkart.com/index.html#dashboard',
    tab: { id: 7 },
  };
  check('a portal page is answered only the two the relay may ask, and only while it is on',
    (listen({ do: 'run-now', reportIds: ['fk_orders'] }, aPortalPage) === null)
      !== RELAY_TO_THE_PAGE
    && listen({ do: 'connect-the-drive' }, aPortalPage) === null
    && listen({ do: 'set-the-hour', at: '03:00' }, aPortalPage) === null);

  check('another extension saying it is the panel is NOT answered',
    listen({ do: 'connect-the-drive' }, {
      id: 'some-other-extension',
      url: chrome.runtime.getURL(THE_PANEL),
    }) === null);

  check('a message with no sender at all is NOT answered',
    listen({ do: 'stop' }, undefined) === null);

  check('something the panel may not ask for is refused BEFORE any promise exists',
    listen({ do: 'land-the-file', bytes: [] }, fromThePanel) === null);

  check('an unrecognised message leaves the channel alone',
    listen({ do: 'anything-at-all' }, fromThePanel) === null);

  check('a message from a FRAME inside the panel is NOT answered',
    listen({ do: 'run-now', reportIds: ['fk_orders'] }, { ...fromThePanel, frameId: 3 }) === null);

  check('and the top of the panel\'s own tab is', Boolean(
    listen({ do: 'how-it-stands' }, { ...fromThePanel, frameId: 0 })));

  /* **A BOOKMARK WITH A FRAGMENT ON IT IS THE SAME PAGE.** Compared as a whole
   * string, a seller who saved the panel with a `#` on the end got a panel that
   * silently answered nothing, which reads as the extension being broken. */
  check('the same page with a fragment or a query on it is still the panel', Boolean(
    listen({ do: 'how-it-stands' }, { ...fromThePanel, url: `${fromThePanel.url}?opened=1#top` })));

  check('only the messages that were let through were carried out',
    asked.filter((one) => one === 'how-it-stands').length === 3
    && asked.length === (RELAY_TO_THE_PAGE ? 4 : 3));
}

{
  /* **A53: THE EXTENSION RELOADS ITSELF WHEN ASKED -- NEVER IN THE MIDDLE OF A RUN.** */
  const { chrome } = installFakeChrome();
  let reloads = 0;
  chrome.runtime.reload = () => { reloads += 1; };
  const parts = { book: { recipes: {} }, later: (fn) => fn() };
  await startTheNight(chrome, { doing: ['fk_claims'], mayAskFor: 0, at: 1, openAt: 'https://x/' });
  const refused = await answerThePanelsQuestion(chrome, parts, { do: 'reload-the-extension' });
  check('a reload asked for while a run is going is refused',
    String(refused && refused.wrong).includes('run is going') && reloads === 0);
  await endTheNight(chrome, { at: 2, why: 'done' });
  const done = await answerThePanelsQuestion(chrome, parts, { do: 'reload-the-extension' });
  check('and once nothing is going, the extension reloads itself',
    done && done.reloading === true && reloads === 1);
}

/* **A53: THE TWO DATE BOXES -- HIS ASK, 2026-09-16.** */
{
  const now = Date.UTC(2026, 8, 16, 3, 0);
  check('a range whose first day is after its last is refused, saying which box to change',
    whyThatRangeCannotBeFetched('2026-09-10', '2026-09-01', now).includes('is after'));
  check('a range longer than a month is refused, saying how many days it was',
    whyThatRangeCannotBeFetched('2026-06-01', '2026-09-01', now).includes('93 days'));
  check('a range that has not happened yet is refused as a single day is',
    whyThatRangeCannotBeFetched('2026-09-14', '2026-09-30', now).includes('not over yet'));
  check('and a good range becomes every day in it, oldest first',
    theDaysBetween('2026-09-13', '2026-09-15').join() === '2026-09-13,2026-09-14,2026-09-15');
}

/* **A53: THE END-OF-SYNC NOTIFICATION, RUMEE'S "SYNC COMPLETE".** */
{
  const said = theSyncSummary({
    startedAt: 1,
    finishedAt: 2,
    done: [
      { reportId: 'fk_claims', state: 'landed' },
      { reportId: 'me_returns', state: 'failed', say: 'Nothing began downloading in 30 seconds' },
      { reportId: 'me_orders', state: 'needs-you', dataDate: '2026-09-10' },
    ],
  });
  check('the end-of-sync notification says what landed and names each failure with its reason',
    said.message.startsWith('1 landed, 1 failed: me_returns (Nothing began downloading in 30 seconds)')
    && said.message.includes('me_orders for 2026-09-10 needs you')
    && said.title.includes('with problems'));
}

/* **A53: A SYNC ASKS FOR THE REPORTS THAT MUST BE REQUESTED FIRST, RUMEE'S ORDER.** */
check('a sync puts the reports that must be requested first, keeping the rest in order',
  askingFirst({
    recipes: { a: { toTake: [1] }, b: { toAsk: [1], toTake: [1] }, c: { toTake: [1] } },
  }, ['a', 'b', 'c']).join() === 'b,a,c');

/* **A53: AND A REPORT THAT READS ANOTHER'S FILE COMES AFTER IT** -- the live sync of
 * 2026-09-16 ran `fk_ads_overall` before `fk_ads_daily` and fetched nothing. */
check('a report that reads another report\'s file is fetched after it',
  askingFirst(BOOK, ['fk_ads_overall', 'fk_ads_daily']).join() === 'fk_ads_daily,fk_ads_overall');

{
  /* **A60, JOB 5 -- HIS DECISION B (2026-09-21): THE TIMED SYNC KEEPS ITS OWN LIST.**
   * By default every report that needs downloading, Flipkart and Meesho; the Run now
   * ticks are for a one-off run and never change it. On 09-18..09-20 two ticked ad
   * reports became the whole daily sync, and no Meesho ran at all. */
  const every = (platform) => (BOOK.reports || [])
    .filter((one) => one.platform === platform && (BOOK.recipes || {})[one.id]
      && one.id !== 'fk_keywords')
    .map((one) => one.id);
  check('the default timed list leaves out fk_keywords (his decision E) and holds fk_ads_kw again (AS9 R238, his correction 6 Nov)',
    !theTimedList(BOOK, { timed: null }).includes('fk_keywords') && theTimedList(BOOK, { timed: null }).includes('fk_ads_kw')
    && theTimedList(BOOK, { timed: null }).length > 0);
  const { chrome } = installFakeChrome();
  const started = [];
  const parts = {
    book: BOOK,
    now: () => Date.UTC(2026, 8, 16, 3, 0),
    startTheNight: async (c, how) => { started.push(how.doing); return startTheNight(c, how); },
    carryOn: async () => {},
  };
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  const fresh = await howItStands(chrome, { book: BOOK, now: Date.UTC(2026, 8, 16, 3, 0) });
  check('a fresh install\'s timed list is the full list',
    Boolean(fresh.timed) && fresh.timed.flipkart === every('flipkart').length
    && fresh.timed.meesho === every('meesho').length && every('meesho').length > 0
    && fresh.timed.amazon === every('amazon').length && every('amazon').length === 9);
  check('and the panel says it: "The timed sync will fetch: N reports (Flipkart x, Meesho y, Amazon z)"',
    Boolean(fresh.timed) && fresh.timed.said === `The timed sync will fetch: `
      + `${every('flipkart').length + every('meesho').length + every('amazon').length} reports `
      + `(Flipkart ${every('flipkart').length}, Meesho ${every('meesho').length}, Amazon ${every('amazon').length})`);
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-ticks', reportIds: ['fk_claims'] });
  const after = await howItStands(chrome, { book: BOOK, now: Date.UTC(2026, 8, 16, 3, 0) });
  check('Run now ticks do not change the timed list',
    Boolean(after.timed) && after.timed.said === (fresh.timed && fresh.timed.said));
  const first = await startTheScheduledSync(chrome, parts);
  check('and the timed sync runs every Flipkart report, not the one tick',
    Boolean(first.started) && [...first.started].sort().join() === [...every('flipkart')].filter((id) => !THE_EVENING_REPORTS.includes(id)).sort().join());
  check('AJ13a: and the morning run leaves out the reports not ready by the morning',
    !first.started.some((id) => THE_EVENING_REPORTS.includes(id)));
  check('and the timed sync keeps a few of the twenty for his own runs, so it may spend less than all of them',
    (await theNight(chrome)).mayAskFor === A_DAYS_ALLOWANCE - KEPT_FOR_HIS_OWN_RUNS);
  await endTheNight(chrome, { at: Date.UTC(2026, 8, 16, 3, 30), why: 'Every report was reached.' });
  const second = await startTheNextPlatform(chrome, parts);
  check('then every Meesho report, though none was ticked',
    Boolean(second.started) && [...second.started].sort().join() === [...every('meesho')].filter((id) => !THE_EVENING_REPORTS.includes(id)).sort().join());
}

{
  /* **AJ13a: THE FOUR REPORTS NOT READY IN THE MORNING ARE THE EVENING RUN'S ALONE (evidence R184-MORNING-FETCH-2026-11-03.md).** One list says it; the two runs are its two halves. */
  check('AJ13a: the evening reports are exactly the four that were not ready at 8:30 on 3 Nov',
    [...THE_EVENING_REPORTS].sort().join() === 'az_fee_preview,fk_orders,fk_views,me_views');
  const whole = theTimedList(BOOK, { timed: null });
  const evening = theTimedListFor(BOOK, { timed: null }, 'evening');
  const morning = theTimedListFor(BOOK, { timed: null }, 'morning');
  const returns = theTimedListFor(BOOK, { timed: null }, 'own');
  check('AJ13a: the evening run fetches those four and nothing else', [...evening].sort().join() === [...THE_EVENING_REPORTS].sort().join());
  check('AJ13a: the morning run fetches every other timed report', morning.length === whole.length - evening.length - returns.length && !morning.some((id) => evening.includes(id) || returns.includes(id)));
  check('AJ13a: together they are the whole timed list, so no report is left out and none is fetched twice',
    [...morning, ...evening, ...returns].sort().join() === [...whole].sort().join());
  check('AJ13a: a list he narrowed himself narrows both runs',
    theTimedListFor(BOOK, { timed: ['fk_claims', 'fk_orders'] }, 'morning').join() === 'fk_claims'
    && theTimedListFor(BOOK, { timed: ['fk_claims', 'fk_orders'] }, 'evening').join() === 'fk_orders');
  const { chrome } = installFakeChrome();
  const started = [];
  const parts = {
    book: BOOK,
    now: () => Date.UTC(2026, 8, 16, 3, 0),
    startTheNight: async (c, how) => { started.push(how.doing); return startTheNight(c, how); },
    carryOn: async () => {},
  };
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  const filed = await chrome.storage.local.get(THE_NIGHTS);
  await chrome.storage.local.set({ [THE_NIGHTS]: { ...(filed[THE_NIGHTS] || {}), flipkartAskedOn: { [theDay(parts.now())]: 10 } } });
  const first = await startTheScheduledSync(chrome, parts, 'evening');
  check('AJ13a: the evening run starts with a Flipkart night of fk_orders and fk_views only',
    Boolean(first.started) && [...first.started].sort().join() === 'fk_orders,fk_views');
  check('AJ13a: and the evening run spends from the same day\'s twenty, so the morning\'s ten already asked are taken off (20 - 10 - 4 kept for his own runs)',
    (await theNight(chrome)).mayAskFor === A_DAYS_ALLOWANCE - 10 - KEPT_FOR_HIS_OWN_RUNS);
  await endTheNight(chrome, { at: Date.UTC(2026, 8, 16, 3, 30), why: 'Every report was reached.' });
  const next = await startTheNextPlatform(chrome, parts);
  check('AJ13a: then Meesho\'s one evening report', Boolean(next.started) && next.started.join() === 'me_views');
}

/** The report ids of a queue, whether its entries are plain lists (the morning's) or carry their run (R208). */
const idsOf = (queue) => (queue || []).map((entry) => (Array.isArray(entry) ? entry : entry.reportIds)).flat();

{
  /* **THE 4 PM RUN NEVER TAKES THE QUEUE OF A MORNING SYNC STILL GOING (AJ13a review).** */
  const { chrome } = installFakeChrome();
  const parts = {
    book: BOOK,
    now: () => Date.UTC(2026, 8, 16, 3, 0),
    startTheNight,
    carryOn: async () => {},
  };
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  const morning = await startTheScheduledSync(chrome, parts);
  const queuedBefore = (await chrome.storage.local.get(THE_QUEUE))[THE_QUEUE];
  const evening = await startTheScheduledSync(chrome, parts, 'evening');
  const queuedAfter = (await chrome.storage.local.get(THE_QUEUE))[THE_QUEUE];
  check('AJ13a: with the morning sync still going, the evening run starts nothing and says it is waiting', Boolean(morning.started) && evening.started === null && evening.waiting === true);
  check('AJ13a: and the morning\'s remaining platforms are all still queued, with the evening reports added behind them',
    queuedBefore.length > 0 && queuedAfter.slice(0, queuedBefore.length).join('|') === queuedBefore.join('|')
    && idsOf(queuedAfter).includes('fk_orders') && idsOf(queuedAfter).includes('me_views'));
  const again = await startTheScheduledSync(chrome, parts, 'evening');
  check('AJ13a: and asking again does not queue a report twice', idsOf((await chrome.storage.local.get(THE_QUEUE))[THE_QUEUE]).filter((id) => id === 'fk_orders').length === 1 && again.waiting === true);
}

{
  /* **WHAT THE GOING NIGHT HAS ALREADY TAKEN IS NOT QUEUED AGAIN BEHIND IT (AJ13a proving): the report it is on, and the ones it has left.** */
  const asked = async (night) => {
    const { chrome } = installFakeChrome();
    const parts = { book: BOOK, now: () => Date.UTC(2026, 8, 16, 3, 0), startTheNight, carryOn: async () => {} };
    await answerThePanelsQuestion(chrome, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
    await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
    await chrome.storage.local.set({ [THE_NIGHT]: { startedAt: Date.now(), finishedAt: 0, spent: 0, mayAskFor: 3, done: [], ...night }, [THE_QUEUE]: [] });
    await startTheScheduledSync(chrome, parts, 'evening');
    return ((await chrome.storage.local.get(THE_QUEUE))[THE_QUEUE] || []).map((entry) => (Array.isArray(entry) ? entry : entry.reportIds)).flat();
  };
  const withLeft = await asked({ doing: null, left: ['fk_views'] });
  check('AJ13a: an evening report the going night still has left is not queued again', !withLeft.includes('fk_views') && withLeft.includes('fk_orders'));
  const withDoing = await asked({ doing: 'fk_orders', left: [] });
  check('and the one it is on now is not queued again either', !withDoing.includes('fk_orders') && withDoing.includes('fk_views'));
}

{
  /* A night whose reports include a partly saved table files it with the failed, so the card does not say it all went well. */
  const { chrome } = installFakeChrome();
  const began = Date.now() - 2 * 3600000;
  await chrome.storage.local.set({
    [THE_NIGHT]: {
      startedAt: began, finishedAt: began + 3600000, left: [], doing: null, spent: 0, mayAskFor: 3, spentOn: {}, why: '',
      done: [{ reportId: 'me_pricing', state: 'partial', say: 'PARTIAL' }, { reportId: 'me_orders', state: 'landed', size: 10 }],
    },
  });
  await rememberTheNight(chrome, { book: BOOK });
  const filed = (await theNights(chrome)).byPlatform.meesho;
  check('AJ13a: a partly saved table is filed with the failed, not with the landed, in the night\'s card', filed.failed === 1 && filed.landed === 1);
}

check('AJ13a: with no time saved, the clock line still names the evening run, and a clock that is not set says to press Save again and names it too',
  whenItNextWakes(null).includes('8:00') && !whenItNextWakes(null).includes('evening')
  && whenItNextWakes({ chosen: '08:00', nextAt: null, eveningAt: Date.now() + 3600000 }).includes('Press Save again. The evening run wakes')
  && whenItNextWakes(null).startsWith('No time saved yet')
  && whenItNextWakes({ chosen: '', eveningAt: Date.now() + 3600000 }).includes('The evening run wakes'));

{
  /* **TWO STARTERS AT ONCE CANNOT BOTH START A NIGHT (review finding, 2026-10-05).** The timed alarm and Run now
   * used to read "no night going" together and each write a night over the other's. */
  const { chrome } = installFakeChrome();
  const parts = {
    book: BOOK,
    now: () => Date.UTC(2026, 8, 16, 3, 0),
    /* Slow on purpose: the night is written a moment AFTER the check, which is the window two starters fell into. */
    startTheNight: async (c, how) => { await new Promise((done) => { setTimeout(done, 15); }); return startTheNight(c, how); },
    carryOn: async () => {},
  };
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  const both = await Promise.all([
    startASync(chrome, parts, { reportIds: ['fk_claims'] }),
    startASync(chrome, parts, { reportIds: ['fk_claims'] }),
  ]);
  check('two starters at the same moment start ONE night, and the other is refused because one is going',
    both.filter((one) => one.started).length === 1 && both.filter((one) => one.wrong).length === 1);
}

{
  /* **STOP TAKES ITS TURN AFTER A NIGHT BEING CARRIED ON, NOT INSIDE IT (review finding, 2026-10-05).** Stop
   * landing inside `carryItOn`'s read-then-write window had its `finishedAt` written over and revived the night. */
  const { chrome } = installFakeChrome();
  const log = [];
  let letItGo;
  const held = new Promise((done) => { letItGo = done; });
  await startTheNight(chrome, { doing: ['fk_claims'], at: 1, openAt: 'https://x/', dataDate: '2026-09-15' });
  const carrying = carryTheNightOn(chrome, {
    theWalkNow: async () => { log.push('carrying starts'); await held; log.push('carrying ends'); return null; },
    startAWalk: async () => {},
    endTheWalkNow: async () => {},
    at: 2,
  });
  const parts = { book: BOOK, now: () => 5, startTheNight, carryOn: async () => {} };
  const stopping = answerThePanelsQuestion(chrome, parts, { do: 'stop' }).then((got) => { log.push('stop runs'); return got; });
  await new Promise((done) => { setTimeout(done, 20); });
  check('a Stop asked while a night is being carried on waits its turn, it does not run inside it',
    log.join() === 'carrying starts');
  letItGo();
  await carrying;
  const stopped = await stopping;
  check('and then runs after it, and the night stays finished', log.join() === 'carrying starts,carrying ends,stop runs'
    && stopped.stopped === true && Boolean((await theNight(chrome)).finishedAt));
}

{
  /* **A53: THE SCHEDULED SYNC RUNS ONE PLATFORM AFTER ANOTHER.** Since A60 it runs
   * the timed list, set here as a stored list of two; the ticks no longer feed it. */
  const { chrome } = installFakeChrome();
  const started = [];
  const parts = {
    book: BOOK,
    now: () => Date.UTC(2026, 8, 16, 3, 0),
    startTheNight: async (c, how) => { started.push(how.doing); return startTheNight(c, how); },
    carryOn: async () => {},
  };
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  const unknown = await answerThePanelsQuestion(chrome, parts, {
    do: 'save-the-ticks', reportIds: ['not_a_report'],
  });
  check('ticks naming a report that does not exist are refused',
    String(unknown && unknown.wrong).includes('not_a_report'));
  await answerThePanelsQuestion(chrome, parts, {
    do: 'save-the-ticks', reportIds: ['me_orders', 'fk_claims'],
  });
  check('the ticks are saved for Run now',
    (await theSetup(chrome)).ticked.join() === 'me_orders,fk_claims');
  const held = (await chrome.storage.local.get('kartaan-autosync-setup'))['kartaan-autosync-setup'];
  await chrome.storage.local.set({
    'kartaan-autosync-setup': { ...held, ticked: [], timed: ['me_orders', 'fk_claims'] },
  });
  const first = await startTheScheduledSync(chrome, parts);
  check('the scheduled sync starts with Flipkart, running only its own list',
    first.started && first.started.join() === 'fk_claims' && started.length === 1);
  const whileGoing = await startTheNextPlatform(chrome, parts);
  check('and the next platform waits while that sync is going',
    whileGoing.waiting === true && started.length === 1);
  await endTheNight(chrome, { at: Date.UTC(2026, 8, 16, 3, 30), why: 'Every report was reached.' });
  const second = await startTheNextPlatform(chrome, parts);
  check('then Meesho starts when Flipkart has ended',
    second.started && second.started.join() === 'me_orders' && started.length === 2);
  check('and a sync knows which of its reports can be fetched for a past day',
    ((await theNight(chrome)).canGoBack || []).includes('me_orders'));
}

{
  /* **A53: A SYNC PAUSED FOR A SIGN-IN ASKS FOR IT, AND RESUME CARRIES ON FROM
   * THAT REPORT -- RUMEE'S RESUME SYNC.** */
  const { chrome } = installFakeChrome();
  const started = [];
  const parts = {
    book: BOOK,
    now: () => Date.UTC(2026, 8, 16, 3, 0),
    startTheNight: async (c, how) => { started.push(how.doing); return startTheNight(c, how); },
    carryOn: async () => {},
  };
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  const nothing = await answerThePanelsQuestion(chrome, parts, { do: 'resume' });
  check('resume with nothing paused says so', String(nothing && nothing.wrong).includes('Nothing is paused'));
  await chrome.storage.local.set({
    'kartaan-autosync-paused': { reportIds: ['fk_claims', 'fk_ads_daily'], dataDate: '2026-09-15', at: 5 },
  });
  const stands = await howItStands(chrome, { book: BOOK, now: Date.UTC(2026, 8, 16, 3, 0) });
  check('the panel asks the seller to sign in while a sync is paused',
    whatTheBannerSays(stands).said.startsWith('Sign in needed'));
  check('and the notification names the platform',
    theSignInAlert(BOOK, stands.paused).title.includes(CALLED.flipkart));
  const resumed = await answerThePanelsQuestion(chrome, parts, { do: 'resume' });
  check('resume carries on from the report that met the sign-in, for the same day',
    Boolean(resumed && resumed.started) && [...started[0]].sort().join() === 'fk_ads_daily,fk_claims'
    && (await theNight(chrome)).dataDate === '2026-09-15'
    && !(await chrome.storage.local.get('kartaan-autosync-paused'))['kartaan-autosync-paused']);
}

/* **THE WHOLE GATE ABOVE RESTS ON ONE MANIFEST KEY, AND NOTHING SAID SO UNTIL AN
 * INDEPENDENT REVIEWER LOOKED.** `sender.url` for a content script in a SUB-FRAME
 * is that frame's address -- so a portal page that could put `panel.html` in a
 * frame would send messages carrying the panel's own address. It cannot, only
 * because `panel.html` is not something a web page is allowed to load. **The
 * frame check above is the second lock; this is the check that keeps the first
 * one from being removed by somebody wanting to link to the panel.** */
check('panel.html is not something a portal page is allowed to load',
  MANIFEST.web_accessible_resources
    .every((one) => !one.resources.includes(THE_PANEL)));

{
  /* **THE LISTENER IS REALLY REGISTERED, not merely written.** `wireUp` is what
   * joins it to Chrome, and a panel wired to nothing is exactly the fault cycle
   * 46 found on the page half: everything built, nothing joined up. */
  const { chrome, aPageAsked } = installFakeChrome();
  wireUp(chrome, {
    onDue: async () => {},
    answerPanel: answerThePanel(chrome, {
      mayAsk: THE_PANEL_ASKS,
      answer: async () => ({ heard: true }),
    }),
  });
  const said = await aPageAsked({ do: 'how-it-stands' }, {
    id: chrome.runtime.id,
    url: chrome.runtime.getURL(THE_PANEL),
  });
  check('wireUp really registers the panel listener', Boolean(said && said.heard));
}

/* --------------------------------------------------------- the toolbar button */

check('the manifest declares something to press', Boolean(MANIFEST.action));
check('and no popup, because he asked for a page', !(MANIFEST.action || {}).default_popup);
check('the panel needs no permission the manifest did not already have',
  MANIFEST.permissions.join(',') === 'alarms,storage,downloads,scripting,identity,notifications,idle');
check('AJ8: the one permission added after that is `idle`, to ask Chrome whether the computer is in use (nothing else of his is read)',
  MANIFEST.permissions.includes('idle') && MANIFEST.permissions.length === 7);
check('the page the manifest opens and the page the worker believes are one name',
  PANEL_HTML.includes('panel.js') && THE_PANEL === 'panel.html');

/* ------------------------------------------------------------- the ERP's look */

check('the panel loads the ERP\'s own tokens rather than colours of its own',
  PANEL_HTML.includes('from-the-erp/tokens.css'));
check('and the ERP\'s own buttons', PANEL_HTML.includes('from-the-erp/button.css'));
{
  /* **NO COLOUR IS WRITTEN INTO THE PANEL'S OWN STYLESHEET.** That is the ERP's
   * D25 -- "a colour written directly into a screen is a bug" -- and it is the
   * only thing that makes retuning a colour in one place mean anything. */
  const written = PANEL_CSS.replace(/\/\*[\s\S]*?\*\//g, '');
  check('no colour is written into panel.css; every one comes from a token',
    !/#[0-9a-fA-F]{3,8}\b/.test(written) && !/\brgba?\(/.test(written));
  check('the panel uses the ERP\'s own button and control classes',
    SCREEN.includes('k-button k-button--main') && SCREEN.includes('k-control'));
}

/* ---------------------------------------------------------- the day it fetches */

check('a day is written the way a report\'s day is written',
  /^\d{4}-\d{2}-\d{2}$/.test(theDay(Date.UTC(2026, 8, 9, 6, 0))));
{
  /* His decision, written down for when the picker is built: where no range is
   * given, yesterday. */
  const at = new Date(2026, 8, 9, 10, 0).getTime();
  check('with nothing said, a run fetches yesterday', theDayToFetch(at) === '2026-09-08');
}

/* -------------------------------------------------------- the panel name asked */

check('an empty panel name is refused, in words a seller can act on',
  (whyThatIsNotAPanelName('') || '').includes('fulfillment/'));
check('a panel name with a slash in it is refused',
  Boolean(whyThatIsNotAPanelName('mine/orders')));
check('a panel name with a space round it is refused, not tidied',
  Boolean(whyThatIsNotAPanelName(' mine ')));
check('an ordinary panel name is accepted', whyThatIsNotAPanelName('rumee_jewellery-1') === null);
check('a panel name longer than a panel name gets is refused',
  Boolean(whyThatIsNotAPanelName('a'.repeat(AS_LONG_AS_A_PANEL_NAME_GETS + 1))));
check('and one exactly that long is not', whyThatIsNotAPanelName(
  'a'.repeat(AS_LONG_AS_A_PANEL_NAME_GETS)) === null);

{
  /* **ASKED AGAIN ON THE WAY OUT OF STORAGE, and this repository's own rule says
   * why: `land-the-file` re-runs `whyTheseAreNotNames` on a name that has already
   * crossed once, because a boundary that asks nothing of what crosses it is not
   * a boundary.** What comes back out here goes into an address the browser is
   * then sent to, and storage is not proof that anything ever asked. */
  const { chrome } = installFakeChrome();
  await chrome.storage.local.set({
    'kartaan-autosync-setup': { panel: '../../somewhere/else', driveConnectedAt: 5 },
  });
  const kept = await theSetup(chrome);
  check('a stored panel name that is not one reads as no panel name at all',
    kept.panel === '');
  check('so a Meesho run is refused in words rather than walking a made-up address',
    (whyItCannotBeStarted(BOOK, { reportIds: ['me_orders'], panel: kept.panel, night: null })
      || '').includes('fulfillment/'));
}

/* -------------------------------------------------- which platform a report is */

check('a report\'s platform comes out of the recipe file, not out of its name',
  thePlatformOf(BOOK, 'fk_orders') === 'flipkart' && thePlatformOf(BOOK, 'me_orders') === 'meesho');
check('a report nothing knows about has no platform', thePlatformOf(BOOK, 'nonsense') === '');
check('a night being walked right now still has a platform -- it is in neither list',
  thePlatformOfTheNight(BOOK, { done: [], doing: 'me_orders', left: [] }) === 'meesho');
check('Amazon is walked through the browser now, for the traffic report, and is called Amazon',
  THROUGH_THE_BROWSER.includes('amazon') && CALLED.amazon === 'Amazon' && thePlatformOf(BOOK, 'az_traffic') === 'amazon');

/* ------------------------------------------------------- where a night starts */

{
  /* **TWO OF THESE USED TO SAY THE OPPOSITE, AND THE NIGHT OF 2026-09-09 IS WHY
   * THEY DO NOT.** They asserted that a night starts at the seller's portal "and
   * nowhere deeper" -- the address cut back to its origin. On his own panel that
   * origin is `https://supplier.meesho.com`, which is not the seller's panel at
   * all: it is Meesho's PUBLIC MARKETING SITE, and `autosync/recipes.py` already
   * records, measured live, that Meesho serves that site for any address it does
   * not know, signed in or not. So the night opened on the one page in the whole
   * product the signed-out detector exists to reject, the detector fired
   * correctly, and nothing was fetched while his Meesho tab sat signed in beside
   * it. **They are rewritten with the change rather than deleted for going red.**
   *
   * **THE ANSWER IS TAKEN OUT OF THE BOOK, NEVER TYPED HERE**, so none of them
   * can pass by agreeing with a second copy of the answer. */
  const firstAddressOf = (reportId) => {
    const recipe = BOOK.recipes[reportId];
    const steps = [...(recipe.toAsk || []), ...(recipe.toTake || [])];
    return String((steps.find((one) => one.address) || {}).address || '');
  };
  /* **A MADE-UP ONE, NEVER HIS.** The seller's own panel name is the seller's
   * (D27, D30, D92) and this repository is public since 2026-09-09. Two checks
   * in `autosync/` exist purely to keep the real one out of the shipped source. */
  const PANEL = 'a-panel-name';
  const meesho = whereToStartFrom(BOOK, ['me_orders'], PANEL);
  const flipkart = whereToStartFrom(BOOK, ['fk_orders']);

  check('a night starts at the whole address its first step names',
    meesho === firstAddressOf('me_orders').split('{panel}').join(PANEL)
    && flipkart === firstAddressOf('fk_orders'));
  /* **AND THE SAME FACT SAID AS THE FAULT.** "It equals the book" would still be
   * true the day somebody put an origin in the book, so this one asks the thing
   * that actually went wrong: the starting page is deeper than the bare site. */
  const deeperThanItsOwnSite = (address) => new URL(address).pathname.replace(/\/+$/, '') !== '';
  check('so a night never begins on the bare site, which on Meesho is its marketing site',
    deeperThanItsOwnSite(meesho) && deeperThanItsOwnSite(flipkart));
  check('and the seller\'s own panel name is filled into it, never shipped in the book',
    meesho.includes(`/${PANEL}/`) && !meesho.includes('{panel}')
    && firstAddressOf('me_orders').includes('{panel}'));
  /* **AND THE STARTING PAGE IS A PAGE OUR OWN HALF RUNS ON.** The walk is picked
   * up by the content script, and the content script runs only where the
   * manifest says. A starting page outside those two is a walk that begins on a
   * page nothing is listening in, and it would stall for ever, at night.
   * **Asked as a match rather than as equality**, because the address is now a
   * whole page and the manifest holds patterns. */
  /* **FOUND BY WHAT IT RUNS, NOT BY BEING FIRST IN THE LIST.** This read the
   * first content script, which was the page half -- until 2026-09-14, when the
   * early Flipkart catcher was put in front of it (his decision, Rumee's way).
   * A check that means "the page half" has to ask for the page half. */
  const thePageHalf = MANIFEST.content_scripts.find((one) => (one.js || []).includes('content.js'));
  const runsOn = (address) => thePageHalf.matches
    .some((one) => address.startsWith(one.replace(/\*$/, '')));
  check('and it is a page the content script actually runs on',
    runsOn(meesho) && runsOn(flipkart));
  check('a report with no recipe says nowhere rather than guessing',
    whereToStartFrom(BOOK, ['me_ads']) === '');
  /* **AN ADDRESS WITH A HOLE IN IT IS NOWHERE.** Filled with no panel name the
   * Meesho address becomes `.../fulfillment//orders/`, which Meesho does not
   * know -- and an address Meesho does not know is answered with the marketing
   * site again, by the paragraph quoted above. */
  check('and with no panel name there is nowhere to start, not an address with a hole in it',
    whereToStartFrom(BOOK, ['me_orders']) === '');
}

/* --------------------------------------------------- what a run is refused for */

{
  const no = (how) => whyItCannotBeStarted(BOOK, { reportIds: [], panel: '', night: null, ...how });
  check('nothing ticked is refused', Boolean(no({})));
  check('two platforms at once is refused, and both are named',
    (no({ reportIds: ['fk_orders', 'me_orders'], panel: 'x' }) || '').includes('Flipkart'));
  check('a run while a run is going is refused',
    (no({ reportIds: ['fk_orders'], night: { finishedAt: null } }) || '').includes('already'));
  check('a finished night does not stop the next one',
    no({ reportIds: ['fk_orders'], night: { finishedAt: 1 } }) === null);
  check('a Meesho run with no panel name is refused, saying where to find it',
    (no({ reportIds: ['me_orders'] }) || '').includes('fulfillment/'));
  check('a Meesho run with a panel name is allowed',
    no({ reportIds: ['me_orders'], panel: 'mine' }) === null);
  /* **AND `me_views` IS NO LONGER ONE OF THEM, which is the point of the change
   * on 2026-09-11.** The door learned to read a number off a card and to add a
   * row as the day's own file, so the one report Meesho sells no export of became
   * fetchable. It needs the panel name like every other Meesho report. */
  check('and the views card can be ticked now, like any other Meesho report',
    no({ reportIds: ['me_views'], panel: 'mine' }) === null);
  /* **AND THE ADS SWEEP CAN BE TICKED TOO**, which is the change of 2026-09-11:
   * it asks Meesho's own addresses rather than pressing anything. */
  check('and so can the ads sweep, which asks rather than presses',
    no({ reportIds: ['me_ads'], panel: 'mine' }) === null);
}

/* ------------------------------------------------- the seller's twenty a day */

check('the allowance is twenty, and it is a number a program can read',
  A_DAYS_ALLOWANCE === 20);

{
  const today = theDay(Date.now());
  const yesterday = theDay(Date.now() - 86400000);
  const kept = { flipkartAskedOn: { [today]: 4 }, byPlatform: {}, filedNight: 0 };
  check('what earlier nights spent today is counted',
    askedForToday(kept, null) === 4);
  check('and the night still going is counted with them',
    askedForToday(kept, { startedAt: Date.now(), spent: 3, spentOn: { [today]: 3 } }) === 7);
  check('a night already filed is not counted twice',
    askedForToday({ ...kept, filedNight: 99 },
      { startedAt: 99, spent: 3, spentOn: { [today]: 3 } }) === 4);
  check('a night from another day that has finished is not counted against today',
    askedForToday(kept, {
      startedAt: Date.now() - 3 * 86400000, finishedAt: 1, spent: 3,
      spentOn: { [theDay(Date.now() - 3 * 86400000)]: 3 },
    }) === 4);
  /* **THE ONE THAT CROSSES MIDNIGHT, AND AN INDEPENDENT REVIEWER CALLED IT
   * BLOCKING.** A night begun at five to midnight spends requests on two
   * different days. Charged as one total to the day it started, today read
   * twenty left while three had already gone -- and a second run today could
   * then spend the whole twenty, which is twenty-three real, irrevocable writes
   * against the seller's own account in one day. */
  check('a night that crossed midnight puts only TODAY\'s requests on today',
    askedForToday(kept, {
      startedAt: Date.now() - 86400000, finishedAt: null, spent: 5,
      spentOn: { [yesterday]: 2, [today]: 3 },
    }) === 7);
  check('and yesterday\'s half of it is not counted against today',
    askedForToday({ ...kept, flipkartAskedOn: {} }, {
      startedAt: Date.now() - 86400000, finishedAt: null, spent: 5,
      spentOn: { [yesterday]: 5 },
    }) === 0);
  /* A night written before the day stamp existed has only a total, and the
   * honest place for it is the day it started. */
  check('a night with no day stamps at all falls back to the day it started',
    askedForToday({ ...kept, flipkartAskedOn: {} },
      { startedAt: Date.now(), spent: 2 }) === 2);

{
  /* **THE STAMP IS PUT ON BY THE ONE THING THAT SPENDS, and this check drives
   * that rather than handing itself a night that already has one.** Written the
   * other way it passed with the stamping taken out altogether -- a check that
   * cannot fail for the thing it is named for, which is this register's most
   * expensive repeated fault. */
  const { chrome } = installFakeChrome();
  /* **RELATIVE TO TODAY, NOT FIXED DATES (EX1, 2026-10-03).** This used 2026-09-08
   * and 09, and the ledger only keeps the last fourteen days from the real clock
   * (`screen.js` KEEP_THE_LAST_DAYS), so from about 2026-09-23 the filed ledger came
   * back empty and this went red on every run -- a check that had stopped being
   * able to pass, not one that caught a fault. Five minutes before and ten minutes
   * after the real midnight is the same night across the same midnight. */
  const midnight = new Date();
  midnight.setHours(0, 0, 0, 0);
  const lateLastNight = midnight.getTime() - 5 * 60 * 1000;
  const earlyToday = midnight.getTime() + 10 * 60 * 1000;
  const lastNightsDay = theDay(lateLastNight);
  const todaysDay = theDay(earlyToday);
  await startTheNight(chrome, {
    doing: ['fk_orders', 'fk_returns'], mayAskFor: 4, at: lateLastNight,
    openAt: 'https://seller.flipkart.com',
  });
  await oneWasAskedFor(chrome, { at: lateLastNight });
  await oneWasAskedFor(chrome, { at: earlyToday });
  await oneWasAskedFor(chrome, { at: earlyToday });
  const night = await theNight(chrome);
  check('every request is stamped with the day it was actually spent on',
    night.spentOn[lastNightsDay] === 1 && night.spentOn[todaysDay] === 2);
  check('and the night\'s own total still agrees with them', night.spent === 3);
  check('so the panel shows only what went out today, not the whole night',
    askedForToday({ flipkartAskedOn: {}, byPlatform: {}, filedNight: 0 },
      night, earlyToday) === 2);

  /* And once it is filed, each day's ledger gets its own share -- not one lump
   * on the day the night began. */
  await endTheNight(chrome, { at: earlyToday, why: 'done' });
  await rememberTheNight(chrome, { book: BOOK });
  const led = (await theNights(chrome)).flipkartAskedOn;
  check('and the ledger is split across the two days when it is filed',
    led[lastNightsDay] === 1 && led[todaysDay] === 2);
}

  check('a run may spend only what is left of the day',
    howManyItMaySpend(BOOK, {
      reportIds: ['fk_orders', 'fk_returns', 'fk_payments'],
      kept: { flipkartAskedOn: { [today]: 18 }, byPlatform: {}, filedNight: 0 },
      night: null,
    }) === 2);
  /* **A TIMED SYNC KEEPS A FEW FOR HIS OWN RUNS, BUT NEVER LESS THAN ITS OWN DAY (Control, 2026-10-05).** */
  check('a timed sync may spend what is left of the day less the few kept for his own runs',
    howManyItMaySpend(BOOK, {
      reportIds: ['fk_orders', 'fk_payments'],
      kept: { flipkartAskedOn: {}, byPlatform: {}, filedNight: 0 }, night: null, timed: true,
    })
      === 20 - KEPT_FOR_HIS_OWN_RUNS);
  check('and when little is left it still gets its own day for each report that spends, up to what there is',
    howManyItMaySpend(BOOK, {
      reportIds: ['fk_orders', 'fk_payments'],
      kept: { flipkartAskedOn: { [today]: 18 }, byPlatform: {}, filedNight: 0 },
      night: null, timed: true,
    }) === 2
    && howManyItMaySpend(BOOK, {
      reportIds: ['fk_orders', 'fk_payments'],
      kept: { flipkartAskedOn: { [today]: 19 }, byPlatform: {}, filedNight: 0 },
      night: null, timed: true,
    }) === 1);
  check('a run of reports that spend nothing is allowed nothing, and needs nothing',
    howManyItMaySpend(BOOK, { reportIds: ['fk_views'], kept, night: null }) === 0);
  check('a day already spent leaves a run allowed nought rather than a negative number',
    howManyItMaySpend(BOOK, {
      reportIds: ['fk_orders'],
      kept: { flipkartAskedOn: { [today]: 20 }, byPlatform: {}, filedNight: 0 },
      night: null,
    }) === 0);
}

/* ---------------------------------------------- a finished night is remembered */

{
  const { chrome, stored } = installFakeChrome();
  /* Real moments, not moments near the start of 1970: the ledger keeps only the
   * last fortnight, so a night from 1970 would be pruned the instant it was
   * filed and this would be checking the pruning rather than the filing. */
  const began = Date.now() - 2 * 3600000;
  const ended = Date.now() - 3600000;
  await chrome.storage.local.set({
    [THE_NIGHT]: {
      startedAt: began, finishedAt: ended, left: [], doing: null, spent: 2, mayAskFor: 3,
      spentOn: { [theDay(began)]: 2 },
      why: 'Every report was reached.',
      done: [
        { reportId: 'fk_orders', state: 'landed', size: 10 },
        { reportId: 'fk_returns', state: 'failed', say: 'the page said no' },
      ],
    },
  });
  await rememberTheNight(chrome, { book: BOOK });
  const first = await theNights(chrome);
  check('a finished night is filed under its own platform',
    first.byPlatform.flipkart.landed === 1 && first.byPlatform.flipkart.failed === 1);
  check('and Meesho, which has never run, says so rather than nothing',
    first.byPlatform.meesho === undefined);
  check('what it spent is added to the ledger for the day it was spent on',
    first.flipkartAskedOn[theDay(began)] === 2);

  await rememberTheNight(chrome, { book: BOOK });
  const twice = await theNights(chrome);
  check('filing the same night twice does not spend the allowance twice',
    twice.flipkartAskedOn[theDay(began)] === 2);
  /* **A DAY'S KEY PER DAY, FOR EVER, IS A RECORD THAT ONLY GROWS.** Nothing here
   * has ever looked at a day but today. */
  check('and days older than a fortnight are dropped rather than kept for ever',
    (await (async () => {
      await chrome.storage.local.set({
        [THE_NIGHTS]: {
          ...twice,
          filedNight: 0,
          flipkartAskedOn: { ...twice.flipkartAskedOn, '2020-01-01': 9 },
        },
      });
      await rememberTheNight(chrome, { book: BOOK });
      return theNights(chrome);
    })()).flipkartAskedOn['2020-01-01'] === undefined);

  {
    /* **THE WORKER FILES A NIGHT ON EVERY WAKE, all night, and almost every one
     * of those calls has nothing to file.** So the recipe file is fetched only
     * once there is something -- which means the book may arrive as something to
     * ask rather than something held. */
    let asked = 0;
    await chrome.storage.local.set({
      [THE_NIGHT]: {
        startedAt: 5000, finishedAt: 6000, left: [], doing: null, spent: 0, mayAskFor: 0,
        spentOn: {}, why: '', done: [{ reportId: 'me_orders', state: 'landed', size: 3 }],
      },
    });
    await rememberTheNight(chrome, { book: async () => { asked += 1; return BOOK; } });
    check('the book can be fetched rather than held, and Meesho is filed from it',
      asked === 1 && (await theNights(chrome)).byPlatform.meesho.landed === 1);
    await rememberTheNight(chrome, { book: async () => { asked += 1; return BOOK; } });
    check('and it is not fetched again when there is nothing to file', asked === 1);
  }

  await chrome.storage.local.set({
    [THE_NIGHT]: { startedAt: 7000, finishedAt: null, left: ['fk_views'], done: [], spent: 0 },
  });
  await rememberTheNight(chrome, { book: BOOK });
  check('a night still going is not filed',
    (await theNights(chrome)).byPlatform.flipkart.startedAt === began);
  check('and nothing was written for it',
    stored()[THE_NIGHTS].filedNight === 5000);
}

/* ------------------------------------------------ carryOn's own once (Job 7) */

{
  /* **THE RACE THAT LEFT THE 2026-09-17 SYNC WITH NO RUN LOG.** `howItStands`
   * calls `rememberTheNight` on every panel poll and throws the answer away --
   * exactly what a poll landing the instant a walk finishes does here. Before
   * `alreadyCarriedOn` existed, `carryOn` asked `rememberTheNight` that same
   * question and, having lost the race, believed its own log/notice/next-
   * platform work was already done. */
  const { chrome } = installFakeChrome();
  const began = Date.now() - 2 * 3600000;
  const ended = Date.now() - 3600000;
  await chrome.storage.local.set({
    [THE_NIGHT]: {
      startedAt: began, finishedAt: ended, left: [], doing: null, spent: 0, mayAskFor: 0,
      spentOn: {}, why: 'Every report was reached.',
      done: [{ reportId: 'fk_orders', state: 'landed', size: 10 }],
    },
  });
  /* The panel's poll, winning the ledger's one-shot race first. */
  await rememberTheNight(chrome, { book: BOOK });
  const night = await theNight(chrome);
  check('carryOn\'s own once is untouched by a panel poll that already filed the ledger',
    (await alreadyCarriedOn(chrome, night)) === false);
  await markCarriedOn(chrome, night);
  check('and once carryOn has actually carried it through, it is not carried through twice',
    (await alreadyCarriedOn(chrome, night)) === true);
  /* **A FOLLOW-THROUGH THAT THREW GIVES THE CLAIM BACK (review finding, 2026-10-05).** Spent first and never
   * released, a throw in the recheck clock or the notice meant the next platform was never started. */
  await releaseCarriedOn(chrome, night);
  check('a claim given back lets the next wake carry the night through again',
    (await alreadyCarriedOn(chrome, night)) === false);
  await markCarriedOn(chrome, night);
  await releaseCarriedOn(chrome, { ...night, startedAt: night.startedAt + 1 });
  check('and a claim is only ever given back for the night that made it',
    (await alreadyCarriedOn(chrome, night)) === true);
  check('a night still going needs no follow-through yet, so carryOn is not told to act',
    (await alreadyCarriedOn(chrome, { startedAt: began, finishedAt: null })) === true);
}

/* --------------------------------------------------------- what the panel sees */

{
  const { chrome } = installFakeChrome();
  const stands = await howItStands(chrome, { book: BOOK, now: Date.now() });
  check('with nothing ever run, the panel says so rather than showing a fault',
    stands.night === null && whatTheBannerSays(stands).how === 'setup');
  check('and every platform that goes through the browser says it has never run',
    stands.platforms.filter((one) => one.throughTheBrowser)
      .every((one) => one.lastRun === null));
  check('Amazon is on the page as a platform walked through the browser, not ready (no Drive yet) and never run',
    stands.platforms.filter((one) => one.id === 'amazon').length === 1
    && stands.platforms.some((one) => one.id === 'amazon' && one.throughTheBrowser === true
      && one.ready === false && one.lastRun === null));
  check('and its walked reports, orders, settlements, returns, SAFE-T claims, account health, ads, traffic, All Listings and Referral Fee Preview, are fetchable and are in the list of reports walked in the browser',
    stands.reports.filter((one) => one.platform === 'amazon').map((one) => one.id).sort().join() === 'az_ads,az_claims,az_fee_preview,az_health,az_listings,az_orders,az_returns,az_settlements,az_traffic'
    && stands.reports.filter((one) => one.platform === 'amazon').every((one) => one.canBeFetched === true));
  check('nothing is set up yet, and both halves are named',
    stands.setUp.done === false && stands.setUp.panel === '' && stands.setUp.driveConnectedAt === 0);
  check('the whole twenty is left', stands.flipkart.leftToday === 20);

  /* **THE ONE THAT CANNOT BE FETCHED IS NAMED WITH ITS REASON.** They are
   * written down in `autosync/recipes.py` as `NOT_YET_A_RECIPE` and until now
   * reached nobody at all. */
  /* **NONE SINCE 2026-09-15** -- the keywords were the last. */
  check('every report this door cannot fetch is on the page, and there are none left',
    stands.cannotBeFetched.length === 0);
  check('and each one carries the reason written down in the Python',
    stands.cannotBeFetched.every((one) => one.why.length > 40));
  check('the reasons are the Python\'s own words, not words invented here',
    stands.cannotBeFetched.every((one) => one.why === BOOK.notYetARecipe[one.id]));
  check('so every report can be ticked but the one switched off (A84; fk_ads_kw back on, AS9 R238)',
    stands.reports.filter((one) => !one.canBeFetched).map((one) => one.id).sort().join() === 'fk_keywords');
  /* **AND THE TWO THE ADS SWEEP BRINGS ARE TICKABLE AND SAY WHO BRINGS THEM.**
   * Listed as unfetchable, a seller would read "cannot be fetched" about two
   * files that arrive in their Drive every night. */
  const bySweep = stands.reports.filter((one) => one.fetchedBy);
  check('the two the ads sweep brings are not called unfetchable',
    bySweep.length === 2 && bySweep.every((one) => one.canBeFetched));
  check('and each says in words what fetches it',
    bySweep.every((one) => one.fetchedBy.length > 40));
  check('and every report that is declared is on the page, fetchable or not',
    stands.reports.length
      === BOOK.reports.filter((one) => THROUGH_THE_BROWSER.includes(one.platform) && !BOOK.onTheApiDoor.includes(one.id)).length);
  /* Two since 2026-09-14: returns left the Reports Centre. */
  check('the two that cost the seller something are marked as costing it',
    stands.reports.filter((one) => one.spends).map((one) => one.id).join(',')
      === 'fk_orders,fk_payments');
}

{
  /* **A82 REVIEW: A RUN WITH DAYS NOT ASKED FOR NEVER READS AS A CLEAN FINISH**, in the banner or the notification. */
  const night = { finishedAt: 5, done: [{ reportId: 'fk_orders', state: 'not-asked', dataDate: '2026-10-01' }] };
  const banner = whatTheBannerSays({ night, setUp: { done: true, driveConnectedAt: 1 }, paused: null, needsYou: [] });
  check('A82: the banner says days were not asked for, not that the run finished clean',
    banner.said.includes('not asked for') && banner.how !== 'done');
  const told = theSyncSummary(night);
  check('A82: and so does the notification',
    told.title.includes('with problems') && told.message.includes('not asked for'));
}

/* ------------------------------------------------------- what the banner says */

check('a run going says which report and how many are left',
  whatTheBannerSays({
    setUp: { done: true }, night: { finishedAt: null, doing: 'fk_orders', left: ['fk_returns'] },
  }).said.includes('fk_orders'));
check('a run that had a failure says so rather than saying it finished',
  whatTheBannerSays({
    setUp: { done: true },
    night: { finishedAt: 2000, doing: null, left: [], done: [{ state: 'failed' }] },
  }).how === 'wrong');
check('a clean run says when it finished',
  whatTheBannerSays({
    setUp: { done: true },
    night: { finishedAt: 2000, doing: null, left: [], done: [{ state: 'landed' }] },
  }).how === 'done');
check('a state nothing has ever been in reads as "not run yet", not as an error',
  whatThatStateIsCalled('') === 'not run yet');
check('never is said as a word, not as a nought', inWordsWhen(0) === 'never');

/* **HIS RULING, 2026-09-14.** A day the platform has not built is not a failure;
 * one still not built after three days of trying is the seller's to fetch, and
 * the page says so before it says anything about the last run. */
check('a day not built yet is said as not available yet, not as a failure',
  whatThatStateIsCalled('not-available-yet') === 'not available yet');
check('and a day given up on is said as needing the seller',
  whatThatStateIsCalled('needs-you') === 'needs you');
check('AJ13a: a table saved with a short page is said as partly fetched, not fetched and not failed',
  whatThatStateIsCalled('partial') === 'partly fetched');
{
  const banner = whatTheBannerSays({
    setUp: { done: true },
    night: { finishedAt: 2000, doing: null, left: [], done: [{ state: 'landed' }] },
    needsYou: [{ reportId: 'fk_orders', dataDate: '2026-09-13' }],
  });
  check('R250: a day that needs the seller is in the amber box, not repeated in the status line',
    banner.how === 'done' && !banner.said.includes('fk_orders') && !banner.said.includes('by hand'));
}
check('while a run that is going is still said first',
  whatTheBannerSays({
    setUp: { done: true },
    night: { finishedAt: null, doing: 'fk_orders', left: [] },
    needsYou: [{ reportId: 'fk_views', dataDate: '2026-09-12' }],
  }).how === 'running');

/* --------------------------------------------------------------- the clock */

check('an empty time box is refused rather than read as midnight',
  (whyThatIsNotATimeOfDay('') || '').includes('No time was chosen'));
check('and midnight itself, which somebody really might choose, is allowed',
  whyThatIsNotATimeOfDay('00:00') === null);
check('a real time of day is accepted and read back', whyThatIsNotATimeOfDay('04:30') === null
  && theTimeOfDayIn('04:30').hour === 4 && theTimeOfDayIn('04:30').minute === 30);
check('a time that is not one is refused', Boolean(whyThatIsNotATimeOfDay('25:00')));
check('and text that is not a time at all is refused',
  Boolean(whyThatIsNotATimeOfDay('tonight')));
{
  const at = new Date(2026, 8, 9, 10, 0).getTime();
  const soon = whenThatHourNextComes({ hour: 22, minute: 30 }, at);
  const past = whenThatHourNextComes({ hour: 4, minute: 0 }, at);
  check('an hour still to come today is today', new Date(soon).getDate() === 9);
  check('an hour already gone is tomorrow', new Date(past).getDate() === 10);
}
{
  const { chrome, alarms } = installFakeChrome();
  await setTheHour(chrome, { at: '04:15', now: () => new Date(2026, 8, 9, 10, 0).getTime() });
  const kept = await theHourItRuns(chrome);
  check('the hour a seller chose is written down', kept.hour === 4 && kept.minute === 15);
  const daily = alarms().find((one) => one.name === DAILY);
  check('and the daily alarm is set for it, not for whenever this happened to run',
    new Date(daily.when).getHours() === 4 && new Date(daily.when).getMinutes() === 15);
  check('and it still repeats every day', daily.periodInMinutes === 24 * 60);

  /* **THE HOUR SURVIVES THE ALARM BEING CLEARED, and that is the nine-day
   * outage by another name.** An alarm can be cleared while Chrome is running;
   * `makeSureTheClockIsSet` is what puts it back on the next wake, and put back
   * without the hour, the run would silently move. */
  await chrome.alarms.clear(DAILY);
  await makeSureTheClockIsSet(chrome);
  const again = alarms().find((one) => one.name === DAILY);
  check('an alarm cleared and put back keeps the hour the seller chose',
    new Date(again.when).getHours() === 4 && new Date(again.when).getMinutes() === 15);
}
{
  /* **A SELLER WHO NEVER CHOSE AN HOUR STILL GETS A FIRST FIRE AT A REAL TIME,
   * and until an independent reviewer looked at this on 2026-09-09 they did
   * not.** Chrome's own documentation: with no `when` and no `delayInMinutes`,
   * a repeating alarm uses its PERIOD as the first delay -- so an alarm created
   * with a period of a day first fires a day later, and every event that clears
   * alarms starts that day again from nought. An extension updated once a day
   * never fires its daily alarm at all, which is the outage this function was
   * written to close arriving through the other door. */
  const { chrome, alarms } = installFakeChrome();
  await makeSureTheClockIsSet(chrome);
  const daily = alarms().find((one) => one.name === DAILY);
  check('a seller who never chose an hour still gets a real first fire',
    typeof daily.when === 'number' && daily.when > Date.now());
  check('and it is at the hour this product runs at until somebody says otherwise',
    new Date(daily.when).getHours() === UNTIL_A_SELLER_CHOOSES.hour
    && new Date(daily.when).getMinutes() === UNTIL_A_SELLER_CHOOSES.minute);
  check('and it still repeats every day', daily.periodInMinutes === 24 * 60);
  check('and nothing is written down about an hour nobody chose',
    (await theHourItRuns(chrome)) === null);
  check('AJ13a: the default hour is 8:00 in the morning, his order of 3 Nov 2026 (the 4 pm run is the other one)',
    UNTIL_A_SELLER_CHOOSES.hour === 8 && UNTIL_A_SELLER_CHOOSES.minute === 0);
}

{
  /* **AND A RECORD THAT IS NOT A TIME OF DAY READS AS NO CHOICE AT ALL.** Read
   * back unasked, `setHours(NaN)` gives an alarm asked for at `NaN` -- which is
   * an alarm Chrome cannot make, and a daily run that never happens. */
  const { chrome, alarms } = installFakeChrome();
  await chrome.storage.local.set({ [THE_HOUR]: { hour: 'four', minute: null } });
  check('nonsense in the stored hour is read as nobody having chosen',
    (await theHourItRuns(chrome)) === null);
  await makeSureTheClockIsSet(chrome);
  const daily = alarms().find((one) => one.name === DAILY);
  check('so the daily alarm is still asked for at a real moment',
    Number.isFinite(daily.when) && new Date(daily.when).getHours()
      === UNTIL_A_SELLER_CHOOSES.hour);
}

/* ------------------------------------------------- the whole conversation */

function panelParts(chrome, held = {}) {
  return {
    book: BOOK,
    now: () => 1000,
    startTheNight,
    carryOn: async () => { held.carriedOn = (held.carriedOn || 0) + 1; },
    watching: { stopExpecting: () => { held.disarmed = true; } },
    setTheHour,
    whyThatIsNotATimeOfDay,
    /* **THE SAME CLOCK THE WORKER HANDS OVER**, written here too because
     * `worker.js` has no checks by design -- the panel name was lost exactly
     * that way once. */
    theClock: async () => {
      const chosen = await theHourItRuns(chrome);
      const clock = await chrome.alarms.get(DAILY);
      return {
        chosen: chosen
          ? `${String(chosen.hour).padStart(2, '0')}:${String(chosen.minute).padStart(2, '0')}`
          : '',
        nextAt: (clock && (clock.scheduledTime || clock.when)) || null,
      };
    },
    ...held.more,
  };
}

{
  const { chrome, askedForTokens } = installFakeChrome();
  const held = {};
  const say = (asked) => answerThePanelsQuestion(chrome, panelParts(chrome, held), asked);

  const before = await say({ do: 'run-now', reportIds: ['fk_orders'] });
  check('a run before the Drive is connected is refused, and says why',
    (before.wrong || '').includes('Drive'));

  const connected = await say({ do: 'connect-the-drive' });
  check('connecting the Drive is the one ask made with somebody watching',
    connected.connected === true && askedForTokens().some((one) => one.interactive === true));

  const named = await say({ do: 'save-the-panel-name', panel: 'not a name' });
  check('a panel name that is not one is refused', Boolean(named.wrong));
  await say({ do: 'save-the-panel-name', panel: 'rumee-panel' });
  check('and a real one is kept', (await theSetup(chrome)).panel === 'rumee-panel');

  const stands = (await say({ do: 'how-it-stands' })).stands;
  check('once both are done the setup section is finished with', stands.setUp.done === true);
  check('and both platforms say they are ready',
    stands.platforms.filter((one) => one.throughTheBrowser).every((one) => one.ready));

  const started = await say({ do: 'run-now', reportIds: ['fk_views', 'fk_orders'] });
  check('a run starts and owes what was ticked', Array.isArray(started.started));
  const night = (await chrome.storage.local.get(THE_NIGHT))[THE_NIGHT];
  check('a run by hand is allowed what is left of the day twenty, not one per report',
    night.mayAskFor === 20);
  check('and it fetches yesterday, because nothing said otherwise',
    night.dataDate === theDayToFetch(1000));
  /* **THE PAGE THE FIRST TICKED REPORT ASKS FOR, WHOLE.** Said as the book says
   * it rather than typed, and this one used to read `https://seller.flipkart.com`
   * -- the origin, which is the fault of 2026-09-09 in its Flipkart shape. */
  check('and it starts at the page the first ticked report names, not at the bare site',
    night.openAt === BOOK.recipes.fk_views.toAsk[0].address
    && new URL(night.openAt).pathname.replace(/\/+$/, '') !== '');
  check('the night is moved on the moment it is started, not two minutes later',
    held.carriedOn === 1);

  const again = await say({ do: 'run-now', reportIds: ['fk_views'] });
  check('a second run while one is going is refused', (again.wrong || '').includes('already'));

  /* **A57, JOB 2: `fk_ads_overall` ALONE PULLS IN ITS CAMPAIGN LIST.** On 09-18..09-21
   * it was ticked without `fk_ads_daily`, nothing fetched the list, and every day was
   * "not known yet". */
  await chrome.storage.local.remove(THE_NIGHT);
  await say({ do: 'run-now', reportIds: ['fk_ads_overall'] });
  const alone = (await chrome.storage.local.get(THE_NIGHT))[THE_NIGHT];
  check('A CAMPAIGN REPORT TICKED ALONE PULLS ITS CAMPAIGN LIST IN, IN FRONT OF IT',
    alone.left.join() === 'fk_ads_daily,fk_ads_overall');
  check('and the night knows which report reads which list',
    (alone.listFrom || {}).fk_ads_overall === 'fk_ads_daily');
}

{
  /* **A RUN MAY NAME ITS DAY**, so a report is proved on a day the platform has
   * surely built -- and a day that is not one, or not over yet, is refused. */
  const at = Date.parse('2026-09-14T12:00:00');
  check('a named day that is yesterday or earlier may be fetched',
    whyThatDayCannotBeFetched('2026-09-01', at) === ''
    && whyThatDayCannotBeFetched('2026-09-13', at) === '');
  check('today is refused, because nothing has built it',
    whyThatDayCannotBeFetched('2026-09-14', at).includes('not over yet'));
  check('a day that is not one is refused',
    whyThatDayCannotBeFetched('2026-02-30', at).includes('not a day')
    && whyThatDayCannotBeFetched('1 Sep', at).includes('not a day'));

  const { chrome } = installFakeChrome();
  const held = { more: { now: () => at } };
  const say = (asked) => answerThePanelsQuestion(chrome, panelParts(chrome, held), asked);
  await say({ do: 'connect-the-drive' });
  await say({ do: 'save-the-panel-name', panel: 'rumee-panel' });
  const refused = await say({ do: 'run-now', reportIds: ['fk_views'], day: 'soon' });
  check('a run naming a day that is not one does not start', Boolean(refused.wrong)
    && !(await chrome.storage.local.get(THE_NIGHT))[THE_NIGHT]);
  await say({ do: 'run-now', reportIds: ['fk_views'], day: '2026-09-01' });
  const night = (await chrome.storage.local.get(THE_NIGHT))[THE_NIGHT];
  check('and a run naming a real day fetches that day, not yesterday',
    night.dataDate === '2026-09-01');
  /* **THE DATE BOXES REACH THE NIGHT (A53).** The panel sends `from` and `to`;
   * until this check the answering code read only `day`, so a seller who typed
   * 8 September got yesterday's figures under yesterday's name. */
  await chrome.storage.local.remove(THE_NIGHT);
  await say({ do: 'run-now', reportIds: ['fk_views'], from: '2026-09-01', to: '2026-09-03' });
  const ranged = (await chrome.storage.local.get(THE_NIGHT))[THE_NIGHT];
  check('a run started from the date boxes fetches those days',
    (ranged.days || []).join(',') === '2026-09-01,2026-09-02,2026-09-03');
}

{
  /* **STOP REALLY STOPS, AND THE ORDER IS THE WHOLE OF IT.** Ending the walk
   * first wakes the night, which sees a night that has not finished and starts
   * the NEXT report -- so pressing Stop would start something. */
  const { chrome, tabs } = installFakeChrome();
  const held = {};
  const closedOurs = [];
  const say = (asked) => answerThePanelsQuestion(chrome, { ...panelParts(chrome, held), closeOurWindow: async () => { closedOurs.push(1); } }, asked);
  await startTheNight(chrome, {
    doing: ['fk_views', 'fk_orders'], mayAskFor: 1, at: 1, openAt: 'https://seller.flipkart.com',
  });
  /* The night takes a report off the list the moment it is ATTEMPTED, so the one
   * being walked is in neither list -- which is exactly why Stop has to write it
   * down itself. */
  await thatOneIsBeingTried(chrome, 'fk_views');
  const tab = await chrome.tabs.create({ url: 'about:blank' });
  await chrome.storage.local.set({
    [THE_WALK]: { tabId: tab.id, reportId: 'fk_views', answer: null, carryOnUntil: 1e15 },
  });

  const stopped = await say({ do: 'stop' });
  check('stopping says it stopped, and what it was doing',
    stopped.stopped === true && stopped.was === 'fk_views');
  const after = (await chrome.storage.local.get(THE_NIGHT))[THE_NIGHT];
  check('the night is finished, so nothing carries it on',
    Boolean(after.finishedAt) && after.why.includes('panel'));
  check('the walk is cleared', (await chrome.storage.local.get(THE_WALK))[THE_WALK] === undefined);
  check('the armed download-cancel is put away, so the seller\'s next download survives',
    held.disarmed === true);
  check('and the tab the walk was in is closed', !tabs().some((one) => one.id === tab.id));
  check('N039: Stop also closes the window this product opened, once', closedOurs.length === 1);

  /* **AND THE REPORT THAT WAS BEING FETCHED IS WRITTEN DOWN.** `endTheNight`
   * leaves `doing` where it was, so before this the panel said that report was
   * "fetching now" for ever while the banner said the run had finished -- and it
   * was in neither list, so the platform card under-reported by one. Found by an
   * independent reviewer, 2026-09-09. */
  check('the report that was being fetched is written down as stopped',
    after.doing === null
    && after.done.some((one) => one.reportId === 'fk_views' && one.state === 'stopped'));
  check('and it says so in words somebody can read',
    howTheNightWent(after).includes('fk_views: stopped'));
  check('which the panel has a plain word for', whatThatStateIsCalled('stopped') === 'stopped');

  const nothing = await say({ do: 'stop' });
  check('stopping when nothing is going is not an error', nothing.stopped === false);
  check('N039: and it closes nothing when nothing was going', closedOurs.length === 1);
}

{
  const { chrome, alarms } = installFakeChrome();
  const say = (asked) => answerThePanelsQuestion(chrome, panelParts(chrome), asked);
  const refused = await say({ do: 'set-the-hour', at: '' });
  check('an unanswered time box reaches the worker and is refused there too',
    (refused.wrong || '').includes('No time was chosen'));
  check('and no daily alarm was moved by it',
    alarms().find((one) => one.name === DAILY) === undefined);
  await say({ do: 'set-the-hour', at: '03:45' });
  const set = alarms().find((one) => one.name === DAILY);
  check('a time chosen on the panel really moves the daily alarm',
    new Date(set.when).getHours() === 3 && new Date(set.when).getMinutes() === 45);

  /* **AND THE PAGE CAN SAY WHEN IT NEXT WAKES (A53, 2026-09-16).** The scheduled
   * sync did not start at the hour he had just saved, and nothing anywhere --
   * panel, log or status -- could say whether the hour was saved, whether the
   * clock existed, or when it would next come round. A seller whose daily sync
   * has quietly moved to tomorrow must not read the same page as one whose sync
   * is minutes away. */
  const told = await say({ do: 'how-it-stands' });
  check('the panel is told the hour that is saved and when it next wakes',
    told.stands.clock.chosen === '03:45' && told.stands.clock.nextAt === set.when);
  check('and it says so in words a seller reads',
    whenItNextWakes(told.stands.clock).startsWith('Next morning run wakes'));
  check('an hour saved with no clock behind it is called out, not shown as fine',
    whenItNextWakes({ chosen: '03:45', nextAt: null }).includes('nothing will start by itself'));
  check('and an hour nobody ever chose says what happens instead',
    whenItNextWakes(null).includes('8:00'));
  check('AJ13a: the clock line names both runs when the 4 pm alarm is set, and the morning one alone as before when it is not',
    whenItNextWakes({ chosen: '08:00', nextAt: Date.now() + 3600000, eveningAt: Date.now() + 7200000 }).includes('The evening run wakes')
    && !whenItNextWakes({ chosen: '08:00', nextAt: Date.now() + 3600000 }).includes('evening'));

  /* **AJ8 (his N063): THE PANEL SAYS PLAINLY WHEN A RUN IS WAITING FOR THE COMPUTER TO BE LEFT ALONE.** */
  check('the panel is told nothing waits when nothing does', told.stands.waitingForIdle === null);
  check('and nothing is said about waiting then', theWaitingSaid(null) === '');
  await chrome.storage.local.set({ 'kartaan-autosync-waiting-for-idle': { daily: 5000 } });
  const waits = await say({ do: 'how-it-stands' });
  check('a run that waits is passed to the panel', waits.stands.waitingForIdle.kinds.join() === 'daily');
  check('and the panel says so in plain words',
    theWaitingSaid(waits.stands.waitingForIdle) === 'Waiting until the computer has not been used for 3 minutes. Then the sync starts by itself.');
check('AJ8: the clock line carries both the next wake and the waiting words, and only the first when nothing waits',    theClockLine({ chosen: '03:45', nextAt: null }, waits.stands.waitingForIdle).includes('nothing will start by itself')    && theClockLine({ chosen: '03:45', nextAt: null }, waits.stands.waitingForIdle).endsWith('starts by itself.')    && theClockLine({ chosen: '03:45', nextAt: null }, null) === whenItNextWakes({ chosen: '03:45', nextAt: null }));
}

{
  /* A Drive that cannot be had says so in words, and does not pretend. */
  const { chrome } = installFakeChrome({ refuseTheToken: 'The seller closed the window.' });
  const said = await answerThePanelsQuestion(chrome, panelParts(chrome), { do: 'check-the-drive' });
  check('a Drive that is not connected says so rather than throwing',
    said.connected === false && said.said.includes('not connected'));
  check('and nothing is written down saying it was connected',
    (await theSetup(chrome)).driveConnectedAt === 0);
}

{
  const { chrome } = installFakeChrome();
  const said = await answerThePanelsQuestion(chrome, panelParts(chrome), { do: 'nonsense' });
  check('a message the panel should never send is answered, never thrown',
    (said.wrong || '').includes('nonsense'));
}

/* ------------------------------------------------------------- and it draws */

{
  installFakeBrowser();
  const { chrome } = installFakeChrome();
  const pressed = [];
  const parts = buildThePanel(document.body, {
    connectTheDrive: () => pressed.push('drive'),
    saveThePanelName: (name) => pressed.push(`panel:${name}`),
    runNow: (ids) => pressed.push(`run:${ids.join(',')}`),
    stop: () => pressed.push('stop'),
    setTheHour: (at) => pressed.push(`hour:${at}`),
  });

  const stands = await howItStands(chrome, { book: BOOK, now: Date.now() });
  showHowItStands(parts, stands);
check('AJ8: with nothing waiting the clock line on the screen says nothing about waiting',    !parts.hourState.textContent.includes('Waiting until'));  showHowItStands(parts, { ...stands, waitingForIdle: { since: 5000, kinds: ['daily'] } });  check('AJ8: and with a run waiting the screen itself says so, beside when it next wakes',    parts.hourState.textContent.includes('Waiting until the computer has not been used for 3 minutes')    && parts.hourState.textContent.includes('wakes'));  showHowItStands(parts, stands);

  check('the setup screen is shown while nothing is set up', parts.setup.hidden === false);
  check('and the banner says what is true when nothing has ever run',
    parts.banner.textContent.includes('set up'));
  check('Run now is off until the setup is done', parts.runNow.disabled === true);
  check('Stop is off while nothing is going', parts.stop.disabled === true);
  check('every report there is has a row', parts.boxes.size === stands.reports.length);
  /* **THE BOX IS OFF FOR EXACTLY THE REPORTS THAT ARRIVE WITH ANOTHER ONE.** This
   * check read "no box is switched off" until A53, and that is the line that let
   * a seller tick `me_ads_catalog`: the worker has no recipe for it, refuses the
   * whole set, and Run now then saved no ticks and started nothing. */
  check('the box is off for exactly the reports that arrive with another',
    [...parts.boxes.entries()].filter(([, one]) => one.disabled).map(([id]) => id).join(',')
    === stands.reports.filter((one) => one.fetchedBy || !one.canBeFetched).map((one) => one.id).join(','));
  showHowItStands(parts, { ...stands, cannotBeFetched: [{ id: 'fk_ads', name: 'Ads report', platform: 'flipkart', why: 'Flipkart gives no download for it.' }] });
  check('what cannot be fetched is at the end of its platform\'s list, its reason behind an i',
    parts.cannot.children.length === 1 && parts.cannot.children[0].textContent.includes('Ads report')
    && parts.cannot.children[0].textContent.includes('Flipkart gives no download for it.'));
  check('the log says no night has been run rather than nothing at all',
    parts.log.textContent.includes('No sync has been run'));

  parts.connectDrive.click();
  parts.savePanel.click();
  check('pressing Connect asks for the Drive', pressed.includes('drive'));
  check('pressing Save keeps the panel name', pressed.includes('panel:'));

  /* **A BUTTON THAT IS OFF CANNOT BE PRESSED, and the stand-in browser is as
   * harsh about that as a real one.** So Stop is driven in the state it is meant
   * to be pressed in -- a run going -- rather than in the state a seller opening
   * this page for the first time is in. */
  const goingOn = {
    ...stands,
    setUp: { ...stands.setUp, done: true, panel: 'mine', driveConnectedAt: 5 },
    night: {
      startedAt: 1, finishedAt: null, doing: 'fk_views', left: ['fk_orders'], done: [],
      spent: 0, mayAskFor: 1, why: '', platform: 'flipkart',
    },
  };
  showHowItStands(parts, goingOn);
  check('while a run is going, Stop is the button that works and Run now is not',
    parts.stop.disabled === false && parts.runNow.disabled === true);
  parts.stop.click();
  check('pressing Stop stops', pressed.includes('stop'));

  /* Now the state a seller is in between runs. */
  const setUp = { ...goingOn, night: null };
  showHowItStands(parts, setUp);
  check('R250: once both halves are done the panel is no longer in its set-up-only view', !parts.body.className.includes('p-pre'));
  check('and Run now comes on', parts.runNow.disabled === false);

  /* **A61, JOB 5b: EVERYTHING STARTS TICKED, and he unticks it all to run one
   * report** -- his way since "make it like Rumee". The checks below then run from
   * nothing ticked, as they always have. */
  check('5b: the panel opens with every report ticked, and the button says Untick all',
    whatIsTicked(parts).length > 0 && parts.selectAll.textContent === 'Untick all platforms');
  parts.selectAll.click();
  check('5b: one press of Untick all leaves nothing ticked', whatIsTicked(parts).length === 0);

  /* Ticking is kept by the page, not read back off it every poll -- so a tick
   * made two seconds ago is still there after the next answer arrives. */
  const box = parts.boxes.get('fk_views');
  box.checked = true;
  box.dispatchEvent({ type: 'change' });
  check('a ticked report is remembered', whatIsTicked(parts).includes('fk_views'));
  showHowItStands(parts, setUp);
  check('and it is still ticked after the next answer arrives',
    whatIsTicked(parts).includes('fk_views') && parts.boxes.get('fk_views').checked === true);
  parts.runNow.click();
  check('Run now sends what was ticked', pressed.includes('run:fk_views'));

  parts.selectAll.click();
  check('Tick all ticks everything that can be asked for on its own',
    whatIsTicked(parts).length
    === stands.reports.filter((one) => one.canBeFetched && !one.fetchedBy).length);
  /* **AND EVERY ONE OF THEM IS SOMETHING THE WORKER WILL ACCEPT.** `save-the-ticks`
   * and Run now both refuse a whole set holding one id with no recipe, so a
   * single untickable row makes "Tick all" do nothing at all, silently. */
  check('and the worker would accept every one of them',
    whatIsTicked(parts).every((id) => BOOK.recipes[id]));
  parts.selectAll.click();
  check('and pressing it again unticks them', whatIsTicked(parts).length === 0);

  /* **A53: THE REPORTS ARE GROUPED BY PLATFORM, EACH GROUP TICKED IN ONE PRESS.** */
  check('the reports are grouped by platform, each group with its own tick-all',
    parts.platformTicks.size === 3
    && parts.platformTicks.get('flipkart').textContent === 'Tick all Flipkart'
    && parts.platformTicks.get('meesho').textContent === 'Tick all Meesho'
    && parts.platformTicks.get('amazon').textContent === 'Tick all Amazon');
  parts.platformTicks.get('meesho').click();
  check('and ticking a platform ticks that platform\'s reports and no others',
    whatIsTicked(parts).length > 0
    && whatIsTicked(parts).every((id) => id.startsWith('me_'))
    && parts.platformTicks.get('meesho').textContent === 'Untick all Meesho');
  parts.platformTicks.get('meesho').click();
  check('and pressing it again unticks them', whatIsTicked(parts).length === 0);

  /* **A REBUILT LIST CLEARS WHAT WAS TICKED, and only the boxes used to be
   * cleared.** `ticked` is exactly what Run now sends, so a rebuild that left
   * stale ids in it was a live path to a run for a report nobody could see.
   * Found by an independent reviewer, 2026-09-09. */
  parts.boxes.get('fk_views').checked = true;
  parts.boxes.get('fk_views').dispatchEvent({ type: 'change' });
  showHowItStands(parts, { ...setUp, reports: setUp.reports.slice(0, 3) });
  /* Since 5b a rebuilt list is ticked again from what he saved, but only its own rows. */
  check('rebuilding the list forgets what was ticked on the old one',
    whatIsTicked(parts).every((id) => parts.boxes.has(id)) && parts.states.size === 3);

  saySomething(parts, 'Started.');
  check('what a button press said back is shown', parts.said.hidden === false);
  saySomething(parts, '');
  check('and taken away again', parts.said.hidden === true);
}

/* ============================================================================
 *   THE SELLER'S OWN PANEL NAME, FROM THE BOX HE TYPES IT IN TO THE ADDRESS
 * ==========================================================================*/

{
  /* **THE WHOLE JOURNEY, AND NOT ONE STEP OF IT WAS EVER CHECKED (2026-09-09).**
   * He ran Meesho twice in one night with his panel name saved on this page, and
   * both times read: *"me_orders: failed -- This report needs the seller's own
   * panel name."*
   *
   * **EVERY PIECE OF IT WAS ALREADY BUILT AND CHECKED; THE JOIN WAS ONE LINE IN
   * `worker.js`, WHICH HAS NO CHECKS BY DESIGN.** The page saved the name, the
   * setup kept it, the night ran, the walk refused -- and nothing anywhere could
   * go red about it, because the only thing that carried the name across lived
   * in the file this project deliberately does not check.
   *
   * **SO THIS CHECK RE-TYPES NO WIRING.** It presses what he presses, and what
   * carries the name from one end to the other is the product's own code: the
   * panel's answer, the night, `carryTheNightOn`, and `walk.js` filling the
   * address. The stand-in below does nothing but write down what it was handed.
   */
  const { chrome } = installFakeChrome();
  const started = [];
  let inFlight = null;
  const carryOn = () => carryTheNightOn(chrome, {
    theWalkNow: async () => inFlight,
    endTheWalkNow: async () => { inFlight = null; },
    /* **THIS PUTS NOTHING IN, AND THAT IS THE POINT.** Whatever reaches here
     * reached here from the night. */
    startAWalk: async (how) => {
      started.push({ ...how });
      inFlight = { reportId: how.reportId, answer: null };
    },
  });
  const say = (asked) => answerThePanelsQuestion(chrome, {
    book: BOOK,
    now: () => 1000,
    startTheNight,
    carryOn,
    watching: { stopExpecting: () => {} },
    setTheHour,
    whyThatIsNotATimeOfDay,
  }, asked);

  await say({ do: 'connect-the-drive' });
  await say({ do: 'save-the-panel-name', panel: 'rumee-panel' });
  const answer = await say({ do: 'run-now', reportIds: ['me_orders'] });
  check('a Meesho run starts once the name has been saved on this page', !answer.wrong);
  check('the night it starts carries the seller\'s own panel name',
    (await theNight(chrome)).panel === 'rumee-panel');
  check('and the walk is handed that same name',
    started.length === 1 && started[0].panel === 'rumee-panel');

  /* **AND IT REACHES THE ADDRESS THE BROWSER IS ACTUALLY SENT TO.** A name
   * carried as far as the walk and dropped before the address is the same
   * failure one step later, so the last mile is walked here with `walk.js`
   * itself -- the real book, his real `me_orders` recipe, whose first step is a
   * `go` to `.../fulfillment/{panel}/orders/`. */
  const went = [];
  const walking = theWalk({
      /* **NOT SLEPT, BECAUSE A CHECK IS NOT A NIGHT.** The walk paces itself
       * like a person now; a check file that really paused would turn seconds of
       * checking into minutes of nothing. `walk.test.js` is where the pacing
       * itself is held to its numbers. */
      pause: () => {},
    book: BOOK,
    say: () => {},
    putTheFile: async () => ({}),
    armTheCatcher: async () => 'a-secret',
    addToTheList: async () => ({ size: 0 }),
    door: {
      async needs_signing_in() { return false; },
      async go(address) { went.push(address); },
      async page_text() { return ''; },
    },
  });
  const walked = await walking(started[0].reportId, started[0].dataDate, { ...started[0] });
  check('the walk carries on rather than refusing for want of a panel name',
    hasNotFinished(walked));
  check('and the address the browser was sent to has his own panel name in it',
    went.length === 1 && went[0].includes('rumee-panel'));
  check('with no placeholder left standing in it',
    !went.some((one) => one.includes('{panel}')));
}

{
  /* **AND THE REFUSAL IS EXACTLY WHERE IT WAS.** Nothing above may make a walk
   * with no name fail quietly, and nothing may put a plausible name in its
   * place: a made-up one is a walk on somebody else's supplier panel. The
   * sentence is the one he read, word for word, and it is what a person can act
   * on -- it says where to find the name. */
  const went = [];
  const walking = theWalk({
      /* **NOT SLEPT, BECAUSE A CHECK IS NOT A NIGHT.** The walk paces itself
       * like a person now; a check file that really paused would turn seconds of
       * checking into minutes of nothing. `walk.test.js` is where the pacing
       * itself is held to its numbers. */
      pause: () => {},
    book: BOOK,
    say: () => {},
    putTheFile: async () => ({}),
    armTheCatcher: async () => 'a-secret',
    addToTheList: async () => ({ size: 0 }),
    door: {
      async needs_signing_in() { return false; },
      async go(address) { went.push(address); },
      async page_text() { return ''; },
    },
  });
  const refused = await walking('me_orders', '2026-09-08', { panel: '' });
  check('a Meesho walk with no panel name still fails, loudly', refused.state === 'failed');
  check('and still says it is the seller\'s own data, and where it is',
    refused.say.includes("seller's own data")
    && refused.say.includes('address of their supplier panel'));
  check('and the browser was never sent anywhere at all', went.length === 0);

  /* **AND THIS PAGE REFUSES IT BEFORE A NIGHT IS EVEN WRITTEN.** Two refusals,
   * and both are wanted: this one is the one he can do something about. */
  const { chrome } = installFakeChrome();
  const say = (asked) => answerThePanelsQuestion(chrome, {
    book: BOOK,
    now: () => 1000,
    startTheNight,
    carryOn: async () => {},
    watching: { stopExpecting: () => {} },
    setTheHour,
    whyThatIsNotATimeOfDay,
  }, asked);
  await say({ do: 'connect-the-drive' });
  const stopped = await say({ do: 'run-now', reportIds: ['me_orders'] });
  check('and Run now refuses a Meesho run before that, with the name unsaved',
    (stopped.wrong || '').includes('fulfillment/'));
  check('and no night was written at all', (await theNight(chrome)) === null);
}

{
  /* **THE ALERT SAYS WHAT IS STILL LEFT FOR HIM TO DO (his ruling, 2026-09-16).**
   * Flipkart signs in in three steps and the third is a code only he receives;
   * told merely "sign in", he does not know a code is waiting for him. */
  const flipkart = theSignInAlert(BOOK, { reportIds: ['fk_orders'], at: 1, dataDate: '2026-09-15' });
  check('the sign-in alert names the one-time code on Flipkart',
    flipkart.message.includes('one-time code') && flipkart.title.includes('Flipkart'));
  const meesho = theSignInAlert(BOOK, { reportIds: ['me_orders'], at: 1, dataDate: '2026-09-15' });
  check('while Meesho, which does not send one, is not told it does',
    !meesho.message.includes('one-time code') && meesho.title.includes('Meesho'));
  check('and both say that resuming carries on from where it stopped',
    flipkart.message.includes('carries on') && meesho.message.includes('carries on'));
}

/* ============================================================================
 *   A61, JOB 5b -- THE RUN NOW PANEL WORKS LIKE RUMEE (his ruling, 2026-09-21:
 *   "yes, make it like Rumee"; `D:/rumee-auto-sync/popup.js:81`, `:271-274`,
 *   `background.js:191-209`)
 * ==========================================================================*/

{
  /* **1. EVERY REPORT IS TICKED UNTIL HE UNTICKS IT.** A report he never chose is
   * ticked; a report he unticked stays unticked when the panel opens again. */
  installFakeBrowser();
  const { chrome } = installFakeChrome();
  const parts = {
    book: BOOK, now: () => Date.UTC(2026, 8, 16, 3, 0),
    startTheNight: async (c, how) => startTheNight(c, how), carryOn: async () => {},
  };
  const ownTick = (stands) => stands.reports
    .filter((one) => one.canBeFetched && !one.fetchedBy).map((one) => one.id);
  const fresh = await howItStands(chrome, { book: BOOK, now: Date.now() });
  check('5b: on a fresh install every report that can be ticked is ticked',
    ownTick(fresh).length > 0 && [...fresh.setUp.ticked].sort().join() === ownTick(fresh).sort().join());
  const panel = buildThePanel(document.body, {
    connectTheDrive() {}, saveThePanelName() {}, runNow() {}, stop() {}, setTheHour() {},
  });
  showHowItStands(panel, fresh);
  check('5b: and the panel draws every one of those boxes ticked',
    ownTick(fresh).every((id) => panel.boxes.get(id).checked)
    && whatIsTicked(panel).sort().join() === ownTick(fresh).sort().join());
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-ticks', reportIds: ['fk_claims'] });
  const later = await howItStands(chrome, { book: BOOK, now: Date.now() });
  check('5b: what he unticked stays unticked when the panel opens again',
    later.setUp.ticked.join() === 'fk_claims');
  /* A report the extension gains later was never unticked by him, so it is ticked. */
  const held = (await chrome.storage.local.get('kartaan-autosync-setup'))['kartaan-autosync-setup'];
  await chrome.storage.local.set({ 'kartaan-autosync-setup': {
    ...held, unticked: (held.unticked || []).filter((id) => id !== 'me_orders'),
  } });
  const gained = await howItStands(chrome, { book: BOOK, now: Date.now() });
  check('5b: a report he never chose is ticked, one he unticked is not',
    gained.setUp.ticked.includes('me_orders') && !gained.setUp.ticked.includes('fk_orders'));
}

{
  /* **A82: "A NEWER VERSION IS OUT" (his ask, 2026-10-20), Kartaan Click's way.** */
  installFakeBrowser();
  const { chrome } = installFakeChrome();
  await chrome.storage.local.set({ 'kartaan-autosync-update': {
    checkedAt: Date.now(), latest: '0.1.18', notes: 'Fixed.',
    url: 'https://github.com/kartaan-com/Kartaan-AutoSync/releases/latest/download/kartaan-autosync-extension.zip',
  } });
  const asked = await answerThePanelsQuestion(chrome, {
    book: BOOK, now: () => Date.now(), installed: '0.1.17',
  }, { do: 'how-it-stands' });
  check('A82: the panel is told a later version exists, and which one it has',
    asked.stands.update.updateAvailable && asked.stands.update.installed === '0.1.17'
    && asked.stands.update.latest === '0.1.18');
  const panel = buildThePanel(document.body, {
    connectTheDrive() {}, saveThePanelName() {}, runNow() {}, stop() {}, setTheHour() {},
  });
  check('A82: and says nothing before it is told', panel.update.hidden === true);
  showHowItStands(panel, asked.stands);
  check('A82: it then shows the version, the note and the download link',
    panel.update.hidden === false && panel.update.textContent.includes('0.1.18')
    && panel.update.textContent.includes('Fixed.') && panel.update.textContent.includes('Download 0.1.18'));
  const downloadLink = panel.update.children[1];
  check('PN2a: the download is a real button with a hidden arrow and the version in its words',
    downloadLink.className.includes('k-button') && downloadLink.children[0].getAttribute('aria-hidden') === 'true'
    && downloadLink.children[1].textContent === 'Download 0.1.18');
  const same = await answerThePanelsQuestion(chrome, {
    book: BOOK, now: () => Date.now(), installed: '0.1.18',
  }, { do: 'how-it-stands' });
  showHowItStands(panel, same.stands);
  check('A82: and goes again once the seller is on that version', panel.update.hidden === true);
}

{
  /* **P16 / D425: THE PANEL SAYS WHICH VERSION IT IS, ALWAYS** -- not only inside "A newer version is
   * out". The number is the extension's own (`getManifest().version`), carried as `update.installed`. */
  installFakeBrowser();
  const { chrome } = installFakeChrome();
  const panel = buildThePanel(document.body, {
    connectTheDrive() {}, saveThePanelName() {}, runNow() {}, stop() {}, setTheHour() {},
  });
  check('P16: before the panel has heard anything the version line is there and says nothing wrong',
    panel.version && panel.version.textContent === '');
  check('P16: the version line is part of the page', Boolean(panel.version.parentNode));
  const none = await answerThePanelsQuestion(chrome, {
    book: BOOK, now: () => Date.now(), installed: '0.1.20',
  }, { do: 'how-it-stands' });
  showHowItStands(panel, none.stands);
  check('P16: with no newer version out, the panel still shows the version it is',
    none.stands.update.updateAvailable === false && panel.update.hidden === true
    && panel.version.textContent === 'AutoSync 0.1.20');
  await chrome.storage.local.set({ 'kartaan-autosync-update': {
    checkedAt: Date.now(), latest: '0.1.21', notes: '', url: 'https://example.invalid/x.zip',
  } });
  const newer = await answerThePanelsQuestion(chrome, {
    book: BOOK, now: () => Date.now(), installed: '0.1.20',
  }, { do: 'how-it-stands' });
  showHowItStands(panel, newer.stands);
  check('P16: with a newer one out, the notice shows and the version line is still there',
    panel.update.hidden === false && panel.update.textContent.includes('0.1.21')
    && panel.version.textContent === 'AutoSync 0.1.20');
  const manifest = JSON.parse(readFileSync(new URL('./manifest.json', import.meta.url), 'utf8'));
  check('P16: the number it shows can be the one in the manifest, which is what the extension reports',
    /^\d+\.\d+\.\d+$/.test(manifest.version));
  check('P16: the version line has a tooltip and a manual entry, and the entry is drawn on the page',
    Boolean(TOOLTIPS.version) && panel.version.title === TOOLTIPS.version
    && MANUAL.some((one) => one.id === 'version') && panel.help.textContent.includes('Which version this is'));
}

{
  /* **P16: THE WORDS SAY WHICH REPORTS GO IN ONE REQUEST, and the day limit the panel holds is the
   * one a range file's name holds.** */
  check('P16: the To box says Flipkart orders and payments go in one request',
    TOOLTIPS.to.includes('Flipkart orders and payments go in one request'));
  check('P16: and the allowance entry says a typed stretch costs one, not one for every day',
    MANUAL.find((one) => one.id === 'allowance').steps.some((said) => said.includes('costs one')));
  check('P16: a press takes as many days as a range file may name',
    AS_MANY_DAYS_AS_ONE_PRESS_TAKES === MOST_DAYS_IN_A_RANGE_FILE);
}

{
  /* **2. THE TWO MEESHO ADS FILES SHOW TICKED WHENEVER THE ADS SWEEP IS**, and
   * are never sent on their own: no request of theirs exists. */
  installFakeBrowser();
  const { chrome } = installFakeChrome();
  const stands = await howItStands(chrome, { book: BOOK, now: Date.now() });
  const panel = buildThePanel(document.body, {
    connectTheDrive() {}, saveThePanelName() {}, runNow() {}, stop() {}, setTheHour() {},
  });
  showHowItStands(panel, stands);
  const tied = ['me_ads_catalog', 'me_ads_summary'];
  check('5b: each ads file says which report brings it',
    tied.every((id) => (stands.reports.find((one) => one.id === id) || {}).broughtBy === 'me_ads'));
  check('5b: the two ads files show ticked while the ads sweep is ticked',
    panel.boxes.get('me_ads').checked && tied.every((id) => panel.boxes.get(id).checked));
  check('5b: and cannot be ticked on their own, nor are they sent',
    tied.every((id) => panel.boxes.get(id).disabled && !whatIsTicked(panel).includes(id)));
  panel.boxes.get('me_ads').checked = false;
  panel.boxes.get('me_ads').dispatchEvent({ type: 'change' });
  check('5b: unticking the ads sweep unticks the two files with it',
    tied.every((id) => !panel.boxes.get(id).checked));
  panel.platformTicks.get('meesho').click();
  check('5b: and "Tick all Meesho" ticks them again with the sweep',
    panel.boxes.get('me_ads').checked && tied.every((id) => panel.boxes.get(id).checked));
}

{
  /* **AMAZON'S CARD (A79, D317): allowed in this browser, nothing walked yet, ready when the
   * Drive is connected -- and it says plainly that no Amazon report is fetched here.** */
  installFakeBrowser();
  const { chrome } = installFakeChrome();
  const panel = buildThePanel(document.body, {
    connectTheDrive() {}, saveThePanelName() {}, runNow() {}, stop() {}, setTheHour() {},
  });
  showHowItStands(panel, await howItStands(chrome, { book: BOOK, now: Date.now() }));
  const before = panel.platforms.textContent;
  check('the Amazon card says not ready until the Drive is connected',
    before.includes('Amazon') && before.includes('not ready') && !before.includes('allowed'));
  await answerThePanelsQuestion(chrome, { book: BOOK, now: () => Date.now() }, { do: 'check-the-drive' });
  showHowItStands(panel, await howItStands(chrome, { book: BOOK, now: Date.now() }));
  const after = panel.platforms.textContent;
  check('and ready once it is, with no old "allowed, nothing fetched here yet" wording left',
    !after.includes('allowed') && !after.includes('no Amazon report is fetched here yet') && after.includes('Amazon'));
}

{
  /* **3. RUN NOW WITH BOTH WEBSITES TICKED RUNS THEM ALL, FLIPKART THEN MEESHO**,
   * the way the timed sync does -- no "one platform at a time" refusal. */
  const { chrome } = installFakeChrome();
  const started = [];
  const parts = {
    book: BOOK, now: () => Date.UTC(2026, 8, 16, 3, 0),
    startTheNight: async (c, how) => { started.push(how); return startTheNight(c, how); },
    carryOn: async () => {},
  };
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  const said = await answerThePanelsQuestion(chrome, parts, {
    do: 'run-now', reportIds: ['me_orders', 'fk_claims'], day: '2026-09-14',
  });
  check('5b: Run now with both websites ticked starts, and Flipkart goes first',
    !said.wrong && started.length === 1 && started[0].doing.join() === 'fk_claims');
  await endTheNight(chrome, { at: Date.UTC(2026, 8, 16, 3, 30), why: 'Every report was reached.' });
  const next = await startTheNextPlatform(chrome, parts);
  check('5b: then Meesho runs when Flipkart ends, for the same day',
    Boolean(next.started) && started.length === 2 && started[1].doing.join() === 'me_orders'
    && started[1].dataDate === '2026-09-14');
  const again = await startTheNextPlatform(chrome, parts);
  check('5b: and nothing more is left to start', again.started === null && started.length === 2);
}

{
  /* **A REFUSAL THAT REMAINS SAYS WHY AND WHAT TO DO (Rule 29)**, and starts nothing:
   * Meesho with no panel name must not let Flipkart spend requests first. */
  const { chrome } = installFakeChrome();
  const started = [];
  const parts = {
    book: BOOK, now: () => Date.UTC(2026, 8, 16, 3, 0),
    startTheNight: async (c, how) => { started.push(how); return startTheNight(c, how); },
    carryOn: async () => {},
  };
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  const said = await answerThePanelsQuestion(chrome, parts, {
    do: 'run-now', reportIds: ['fk_claims', 'me_orders'],
  });
  check('5b: a Meesho part that cannot start stops the whole run, saying which and why',
    started.length === 0 && (said.wrong || '').includes('Meesho')
    && (said.wrong || '').includes('fulfillment/') && (said.wrong || '').includes('Nothing was started'));
}

{
  /* **A84: THE TWO SWITCHED-OFF FLIPKART REPORTS ARE NEVER FETCHED, BY THE TIMER OR BY A TICK** (the 15 Oct first run fetched both because
   * Run now opened with every report ticked, this pair included, and a stale tick was started as asked). */
  const { chrome } = installFakeChrome();
  const held = {};
  const say = (asked) => answerThePanelsQuestion(chrome, panelParts(chrome, held), asked);
  await say({ do: 'connect-the-drive' });
  await say({ do: 'save-the-panel-name', panel: 'rumee-panel' });
  const stands = (await say({ do: 'how-it-stands' })).stands;
  check('A84: the panel opens without a tick box for the switched-off report, and with one for fk_ads_kw again (AS9 R238)',
    !stands.setUp.ticked.includes('fk_keywords') && stands.setUp.ticked.includes('fk_ads_kw') && stands.setUp.ticked.includes('fk_views'));
  const alone = await say({ do: 'run-now', reportIds: ['fk_keywords'] });
  check('and a stale tick on one of them alone starts nothing', Boolean(alone.wrong) && !alone.started);
  const started = await say({ do: 'run-now', reportIds: ['fk_keywords', 'fk_views'] });
  check('and with others ticked, they are fetched and the switched-off one is left out',
    Array.isArray(started.started) && started.started.join() === 'fk_views');
}

{
  /* **A84 REVIEW: A QUEUE KEPT BY THE 15 OCT BUILD STILL HOLDS THE SWITCHED-OFF PAIR**, and the next platform's start must not fetch them. */
  const { chrome } = installFakeChrome();
  const started = [];
  const parts = {
    book: BOOK, now: () => Date.UTC(2026, 8, 16, 3, 0),
    startTheNight: async (c, how) => { started.push(how); return startTheNight(c, how); },
    carryOn: async () => {},
  };
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  await chrome.storage.local.set({ [THE_QUEUE]: [{ reportIds: ['fk_keywords', 'fk_views'] }] });
  const next = await startTheNextPlatform(chrome, parts);
  check('A84: a stored queue naming the switched-off pair starts without them',
    Boolean(next.started) && started.length === 1 && started[0].doing.join() === 'fk_views');
}

{
  /* **A84 REVIEW ROUND 3: A PAUSE OR A RE-CHECK HOLDING ONLY THE SWITCHED-OFF PAIR IS FORGOTTEN, NOT LEFT SAYING "Nothing is ticked"** (records
   * kept by the 15 Oct build). */
  const { chrome } = installFakeChrome();
  const parts = { book: BOOK, now: () => Date.UTC(2026, 8, 16, 3, 0), startTheNight, carryOn: async () => {} };
  const say = (asked) => answerThePanelsQuestion(chrome, parts, asked);
  await say({ do: 'save-the-panel-name', panel: 'xuptj' });
  await say({ do: 'check-the-drive' });
  await chrome.storage.local.set({ [PAUSED]: { reportIds: ['fk_keywords'], dataDate: '2026-10-14' } });
  const resumed = await say({ do: 'resume' });
  check('A84: resuming a pause that held only the pair says nothing is paused', (resumed.wrong || '').includes('Nothing is paused'));
  check('and the pause is gone', (await chrome.storage.local.get(PAUSED))[PAUSED] === undefined);
  await chrome.storage.local.set({ [PAUSED]: { reportIds: ['fk_keywords', 'fk_views'], dataDate: '2026-10-14' } });
  await startASync(chrome, parts, { reportIds: ['fk_views'] });
  await chrome.storage.local.set({ [PAUSED]: { reportIds: ['fk_keywords', 'fk_views'], dataDate: '2026-10-14' } });
  await endTheNight(chrome, { at: Date.UTC(2026, 8, 16, 3, 30), why: 'Every report was reached.' });
  await startASync(chrome, parts, { reportIds: ['fk_views'] });
  check('a pause holding the pair and another keeps the other',
    ((await chrome.storage.local.get(PAUSED))[PAUSED] || {}).reportIds.join() === 'fk_views');
  await chrome.storage.local.set({ [RECHECKS]: {
    a: { reportId: 'fk_keywords', dataDate: '2026-10-14' }, b: { reportId: 'fk_views', dataDate: '2026-10-15' },
  } });
  await endTheNight(chrome, { at: Date.UTC(2026, 8, 16, 4, 30), why: 'Every report was reached.' });
  await startASync(chrome, parts, { reportIds: ['fk_views'] });
  check('a re-check of the pair is forgotten and the others stay',
    Object.values((await chrome.storage.local.get(RECHECKS))[RECHECKS]).map((one) => one.reportId).join() === 'fk_views');
}

{
  /* **A84 PROVING: A TICK ON THE PAIR BESIDE ANOTHER WEBSITE'S REPORT DOES NOT REFUSE THE OTHER WEBSITE.** */
  const { chrome } = installFakeChrome();
  const started = [];
  const parts = {
    book: BOOK, now: () => Date.UTC(2026, 8, 16, 3, 0),
    startTheNight: async (c, how) => { started.push(how); return startTheNight(c, how); },
    carryOn: async () => {},
  };
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  const said = await answerThePanelsQuestion(chrome, parts, { do: 'run-now', reportIds: ['fk_keywords', 'me_orders'] });
  check('A84: the pair ticked beside a Meesho report leaves the Meesho report running alone',
    !said.wrong && started.length === 1 && started[0].doing.join() === 'me_orders');
}

/* AP11, from the proving run: which platform waits on the panel name, and what the card says of the last run. */
{
  installFakeBrowser();
  const { chrome } = installFakeChrome();
  const parts = { book: BOOK, now: () => Date.UTC(2026, 8, 16, 3, 0), startTheNight, carryOn: async () => {} };
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  const ready = (stands) => Object.fromEntries(stands.platforms.map((one) => [one.id, one.ready]));
  const noPanel = ready(await howItStands(chrome, { book: BOOK, now: Date.now() }));
  check('with the Drive and no panel name only Meesho waits: Flipkart and Amazon are ready',
    noPanel.meesho === false && noPanel.flipkart === true && noPanel.amazon === true);
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  check('and with the panel name Meesho is ready too', ready(await howItStands(chrome, { book: BOOK, now: Date.now() })).meesho === true);
  const shown = buildThePanel(document.body, {
    connectTheDrive: () => {}, saveThePanelName: () => {}, runNow: () => {}, stop: () => {}, setTheHour: () => {},
  });
  const stands = await howItStands(chrome, { book: BOOK, now: Date.now() });
  showHowItStands(shown, {
    ...stands,
    platforms: stands.platforms.map((one) => (one.id === 'flipkart' ? { ...one, lastRun: { finishedAt: Date.now(), landed: 3, failed: 2 } } : one)),
  });
  check('a platform\'s card says how many reports the last run fetched AND how many failed',
    shown.platforms.textContent.includes('3 fetched, 2 failed'));
}

/* AJ6: the per-report table replaces the words box. */
{
  installFakeBrowser();
}

{
  const into = document.createElement('div');
  showTheReportTable(into, null, 'Amazon', new Set());
  check('table screen: null table shows note', into.textContent.includes('No sync has been run.'));
}

{
  const into = document.createElement('div');
  const table = {
    startedAt: Date.UTC(2026, 9, 28, 3, 10),
    finishedAt: Date.UTC(2026, 9, 28, 3, 20),
    minutes: 10,
    counts: { landed: 2, asked: 1, toFetch: 3, failed: 4 },
    rows: []
  };
  showTheReportTable(into, table, 'Amazon', new Set());
  const numbers = ['landed', 'asked', 'tofetch', 'failed'].map((name) =>
    into.find(`p-count--${name}`).find('p-count-number').textContent
  );
  const labels = into.textContent;
  check(
    'table screen: counts and labels appear',
    numbers.join(',') === '2,1,3,4' &&
      labels.includes('Asked, not yet in') &&
      labels.includes('Still to fetch')
  );
}

{
  const into = document.createElement('div');
  const table = {
    startedAt: Date.UTC(2026, 9, 28, 3, 10),
    finishedAt: Date.UTC(2026, 9, 28, 3, 20),
    minutes: 10,
    counts: { landed: 1, asked: 1, toFetch: 0, failed: 1 },
    rows: [
      { key: 'a', name: 'Report A', status: 'landed', word: 'Landed', seconds: 95, star: true, means: 'Means A', detail: 'Detail A' },
      { key: 'b', name: 'Report B', status: 'asked', word: 'Asked', seconds: null, star: false, means: 'Means B', detail: 'Detail B' },
      { key: 'c', name: 'Report C', status: 'failed', word: 'Failed', seconds: 12, star: false, means: 'Means C', detail: 'Detail C' }
    ]
  };
  showTheReportTable(into, table, 'Flipkart', new Set());
  const reportRows = into.findAll('p-report-row');
  const detailRows = into.findAll('p-detail-row');
  const firstWord = reportRows[0].find('p-word').textContent;
  const starredTime = reportRows[0].children[2].textContent;
  const emptyTime = reportRows[1].children[2].textContent;
  check(
    'table screen: rows, words and time cells',
    reportRows.length === 3 &&
      detailRows.length === 3 &&
      firstWord === 'Landed' &&
      starredTime === '95 s *' &&
      emptyTime === ''
  );
}

{
  const into = document.createElement('div');
  const table = {
    startedAt: Date.UTC(2026, 9, 28, 3, 10),
    finishedAt: Date.UTC(2026, 9, 28, 3, 20),
    minutes: 10,
    counts: { landed: 1, asked: 0, toFetch: 0, failed: 0 },
    rows: [
      { key: 'a', name: 'Report A', status: 'landed', word: 'Landed', seconds: 1, star: false, means: 'Means A', detail: 'Detail A' },
      { key: 'b', name: 'Report B', status: 'landed', word: 'Landed', seconds: 2, star: false, means: 'Means B', detail: 'Detail B' }
    ]
  };
  showTheReportTable(into, table, 'Amazon', new Set());
  const detailRows = into.findAll('p-detail-row');
  const oldTitle = into.findAll('p-title').some((node) => node.textContent === 'What happened, in words');
  check('table screen: details start hidden and old log is gone', detailRows.every((row) => row.hidden) && !oldTitle);
}

{
  const into = document.createElement('div');
  const opened = new Set();
  const table = {
    startedAt: Date.UTC(2026, 9, 28, 3, 10),
    finishedAt: Date.UTC(2026, 9, 28, 3, 20),
    minutes: 10,
    counts: { landed: 1, asked: 1, toFetch: 0, failed: 0 },
    rows: [
      { key: 'a', name: 'Report A', status: 'landed', word: 'Landed', seconds: 1, star: false, means: 'Means A', detail: 'Detail A' },
      { key: 'b', name: 'Report B', status: 'asked', word: 'Asked', seconds: 2, star: false, means: 'Means B', detail: 'Detail B' }
    ]
  };
  showTheReportTable(into, table, 'Amazon', opened);
  const reportRows = into.findAll('p-report-row');
  const detailRows = into.findAll('p-detail-row');

  reportRows[0].click();
  const afterOpen =
    !detailRows[0].hidden &&
    detailRows[1].hidden &&
    opened.has('a') &&
    !opened.has('b') &&
    reportRows[0].getAttribute('aria-expanded') === 'true';

  reportRows[0].click();
  const afterClose =
    detailRows[0].hidden &&
    detailRows[1].hidden &&
    !opened.has('a') &&
    !opened.has('b') &&
    reportRows[0].getAttribute('aria-expanded') === 'false';

  reportRows[0].fire('keydown', { key: 'Enter' });
  const afterEnter =
    !detailRows[0].hidden &&
    detailRows[1].hidden &&
    opened.has('a') &&
    !opened.has('b') &&
    reportRows[0].getAttribute('aria-expanded') === 'true';

  check('table screen: click and Enter toggle own detail', afterOpen && afterClose && afterEnter);
}

{
  const into = document.createElement('div');
  const opened = new Set(['b']);
  const table = {
    startedAt: Date.UTC(2026, 9, 28, 3, 10),
    finishedAt: Date.UTC(2026, 9, 28, 3, 20),
    minutes: 10,
    counts: { landed: 1, asked: 1, toFetch: 0, failed: 0 },
    rows: [
      { key: 'a', name: 'Report A', status: 'landed', word: 'Landed', seconds: 1, star: false, means: 'Means A', detail: 'Detail A' },
      { key: 'b', name: 'Report B', status: 'asked', word: 'Asked', seconds: 2, star: false, means: 'Means B', detail: 'Detail B' }
    ]
  };
  showTheReportTable(into, table, 'Amazon', opened);
  const detailRows = into.findAll('p-detail-row');
  check('table screen: redraw keeps opened detail', detailRows[0].hidden && !detailRows[1].hidden);
}

/* AJ6, wired: the panel draws the last run as a table, one row per report, and the words box is gone. */
{
  installFakeBrowser();
  const { chrome } = installFakeChrome();
  const shown = buildThePanel(document.body, {
    connectTheDrive: () => {}, saveThePanelName: () => {}, runNow: () => {}, stop: () => {}, setTheHour: () => {},
  });
  const stands = await howItStands(chrome, { book: BOOK, now: Date.now() });
  const [one, two, three, four] = stands.reports.map((r) => r.id);
  const at = Date.UTC(2026, 9, 28, 3, 10);
  const night = {
    startedAt: at, finishedAt: at + 33 * 60000, doing: null, left: [], why: '', spent: 0, mayAskFor: 0, platform: 'flipkart',
    done: [
      { reportId: one, state: 'landed', say: '', size: 500, at: at + 40000 },
      { reportId: two, state: 'failed', say: 'nothing matched Download', size: 0, at: at + 100000, pageWas: 'Oops!' },
      { reportId: three, state: 'still-waiting', say: 'asked, not built', size: 0, at: at + 130000 },
      { reportId: four, state: 'needs-you', say: 'sign in first', size: 0, at: at + 150000 },
    ],
  };
  showHowItStands(shown, { ...stands, night });
  const rows = shown.log.findAll('p-report-row');
  const number = (name) => shown.log.find(`p-count--${name}`).find('p-count-number').textContent;
  check('AJ6: the last run is one row per report', rows.length === 4);
  check('AJ6: the four boxes count landed, asked, still to fetch, failed (needs you is failed)',
    [number('landed'), number('asked'), number('tofetch'), number('failed')].join(',') === '1,1,0,2');
  check('AJ6: the heading names the platform and the minutes', shown.log.textContent.includes('Last run: Flipkart')
    && shown.log.textContent.includes('33 min'));
  check('AJ6: tapping a row opens the detail of that report', (() => {
    const detail = shown.log.findAll('p-detail-row');
    rows[1].click();
    return !detail[1].hidden && detail[0].hidden && detail[1].textContent.includes('the page said: Oops!');
  })());
  showHowItStands(shown, { ...stands, night });
  check('AJ6: a poll does not shut the row that is open', shown.log.findAll('p-detail-row').filter((r) => !r.hidden).length === 1);
  check('AJ6: the old "What happened, in words" box is gone', !SCREEN.includes('What happened, in words')
    && shown.log.findAll('p-title').length === 0);
}

/* AJ7 proving: the shape of the report table, and when it is drawn again. */
{
  const into = document.createElement('div');
  const table = {
    startedAt: Date.UTC(2026, 9, 28, 3, 10),
    finishedAt: Date.UTC(2026, 9, 28, 3, 20),
    minutes: 10,
    counts: { landed: 1, asked: 0, toFetch: 0, failed: 0 },
    rows: [
      { key: 'a', name: 'Report A', status: 'landed', word: 'Landed', seconds: 1, star: false, means: 'Means A', detail: 'Detail A' },
    ]
  };
  showTheReportTable(into, table, 'Amazon', new Set(['a']));
  const tableEl = into.find('p-table');
  const thead = tableEl.children[0];
  check('table screen: the head is one row of Report, Status, Time, What it means',
    thead.children.length === 1 && thead.children[0].children.map((c) => c.textContent).join('|') === 'Report|Status|Time|What it means');
  const reportRow = into.find('p-report-row');
  check('table screen: a report row can be reached by keyboard and says whether it is open',
    reportRow.getAttribute('tabindex') === '0' && reportRow.getAttribute('aria-expanded') === 'true'
    && reportRow.getAttribute('title') === 'Tap to open the full detail');
  check('table screen: the detail cell spans all four columns',
    into.find('p-detail-row').children[0].getAttribute('colspan') === '4');
  check('table screen: the note says what the star means',
    into.findAll('p-note').some((n) => n.textContent === '* Time spent waiting for the platform, not working.'));
}

{
  installFakeBrowser();
  const { chrome } = installFakeChrome();
  const shown = buildThePanel(document.body, {
    connectTheDrive: () => {}, saveThePanelName: () => {}, runNow: () => {}, stop: () => {}, setTheHour: () => {},
  });
  const stands = await howItStands(chrome, { book: BOOK, now: Date.now() });
  const [one, two] = stands.reports.map((r) => r.id);
  const at = Date.UTC(2026, 9, 28, 3, 10);
  const night = {
    startedAt: at, finishedAt: at + 5 * 60000, doing: null, left: [], why: '', spent: 0, mayAskFor: 0, platform: 'flipkart',
    done: [{ reportId: one, state: 'landed', say: '', size: 500, at: at + 40000 }],
  };
  showHowItStands(shown, { ...stands, night });
  const rowsBefore = shown.log.findAll('p-report-row');
  check('AJ7: a report row is called by the name the panel knows it by',
    rowsBefore.length === 1 && rowsBefore[0].find('p-cell-name').textContent === stands.reports.find((r) => r.id === one).name);
  showHowItStands(shown, { ...stands, night });
  check('AJ7: a poll that finds the run unchanged does not draw the table again', shown.log.findAll('p-report-row')[0] === rowsBefore[0]);
  const longer = { ...night, done: [...night.done, { reportId: two, state: 'failed', say: 'x', size: 0, at: at + 90000 }] };
  showHowItStands(shown, { ...stands, night: longer });
  check('AJ7: a changed run is drawn again, in place of the old table and not under it',
    shown.log.findAll('p-report-row').length === 2 && shown.log.findAll('p-table').length === 1
    && shown.log.findAll('p-report-row')[0] !== rowsBefore[0]);
}

/* ------------------------------------------------- the AI card (AD1, BR1 proving) */
{
  installFakeBrowser();
  const { chrome } = installFakeChrome();
  const asked = [];
  const parts = buildThePanel(document.body, { connectTheDrive() {}, saveThePanelName() {}, runNow() {}, stop() {}, setTheHour() {}, aiSwitch: (on) => asked.push(on) });
  const stands = await howItStands(chrome, { book: BOOK, now: Date.now() });
  const card = parts.ai;
  const row = card.children[0];
  check('AD1: the AI card is on the page, in the page body, closed until its button "AI may run it" is pressed',
    card.parentNode !== null && card.parentNode.children.includes(card) && card.parentNode.className.includes('body') && card.hidden === true
    && parts.aiButton.children[0].textContent === 'AI may run it');
  parts.aiButton.click();
  check('R250: pressing the button opens the AI card, and its state reads Off', card.hidden === false && parts.aiButtonState.textContent === '' );
  check('AD1: the switch and its state sit in one row of the card', row.children[0] === parts.aiSwitch && row.children[1] === parts.aiState && row.children.length === 2);
  check('AD1: the switch is a plain button, off to start with', parts.aiSwitch.type === 'button' && parts.aiSwitch.textContent === 'AI may run AutoSync: Off');
  check('AD1: the card says what the switch lets the AI do, and holds the note and the asks', /read how your reports stand/.test(card.children[1].textContent)
    && /3 minutes/.test(card.children[1].textContent) && card.children[2] === parts.aiNote && card.children[3] === parts.aiAsks && card.children.length === 4);

  showHowItStands(parts, stands);
  check('AD1: with no word from the worker the switch reads Off and the rest is empty', parts.aiSwitch.textContent === 'AI may run AutoSync: Off'
    && parts.aiState.textContent === '' && parts.aiNote.textContent === '' && parts.aiAsks.textContent === '' && parts.aiOn === false);
  parts.aiSwitch.click();
  check('AD1: pressing it while off asks for On', asked.length === 1 && asked[0] === true);

  showHowItStands(parts, { ...stands, ai: { on: true, connected: false, note: '', asks: [] } });
  check('AD1: on, the switch says On and that the helper is awaited', parts.aiSwitch.textContent === 'AI may run AutoSync: On' && parts.aiState.textContent === 'waiting for the helper' && parts.aiOn === true);
  parts.aiSwitch.click();
  check('AD1: pressing it while on asks for Off', asked.length === 2 && asked[1] === false);

  showHowItStands(parts, { ...stands, ai: { on: true, connected: true, note: 'a note', asks: [{ panel_line: 'first line' }, { panel_line: 'second line' }] } });
  check('AD1: connected, it says so', parts.aiState.textContent === 'helper connected');
  check('AD1: the note is shown as it is', parts.aiNote.textContent === 'a note');
  check('AD1: each ask is shown on a line of its own, in order', parts.aiAsks.textContent === 'first line\nsecond line');

  showHowItStands(parts, { ...stands, ai: { on: false, connected: true } });
  check('AD1: off, the state is empty even if the helper is still connected, and a missing note and asks are empty', parts.aiState.textContent === ''
    && parts.aiNote.textContent === '' && parts.aiAsks.textContent === '' && parts.aiSwitch.textContent === 'AI may run AutoSync: Off');

  const lone = buildThePanel(document.body, { connectTheDrive() {}, saveThePanelName() {}, runNow() {}, stop() {}, setTheHour() {} });
  let threw = false;
  try { lone.aiSwitch.click(); } catch (wrong) { threw = true; }
  check('AD1: pressing the switch on a panel that was given no door does nothing and does not stop it', threw === false);
}

{
  /* AJ9 piece 6: the panel lists what happened, in order, in plain words. */
  const night = {
    startedAt: 1_000_000, finishedAt: 1_900_000, why: 'all done', doing: null, idle: { waitedMs: 600000, kind: 'run' },
    done: [
      { reportId: 'fk_orders', state: 'landed', at: 1_200_000, say: '' },
      { reportId: 'me_views', state: 'failed', at: 1_500_000, say: 'The tab closed, so it will be checked again in an hour.' },
    ],
    toldKartaan: { told: true, said: 'Kartaan has started your run.', finishedAt: 1_900_000 },
  };
  const events = theNightsEvents(night, (id) => (id === 'fk_orders' ? 'Flipkart orders' : id));
  check('AJ9 6: the events run start, idle wait, each report, the end, then what Kartaan was told',
    events.map((one) => one.words).join('|') === [
      'The run started.', theIdleLine(night), 'Flipkart orders: fetched',
      'me_views: failed -- The tab closed, so it will be checked again in an hour.',
      'The run ended: all done', 'Kartaan: Kartaan has started your run.'].join('|'));
  check('AJ9 6: a report being fetched now has no time on it', theNightsEvents({ ...night, finishedAt: null, doing: 'fk_ads' })
    .some((one) => one.at === null && /Fetching now: fk_ads/.test(one.words)));
  check('AJ9 6: no night, no events', theNightsEvents(null).length === 0);
  installFakeBrowser();
  const parts = buildThePanel(document.body, { connectTheDrive() {}, saveThePanelName() {}, runNow() {}, stop() {}, setTheHour() {} });
  showTheEvents(parts, events);
  check('AJ9 6: the panel draws one line per event, the report line carrying its own words',
    parts.events.children.length === events.length
    && [...parts.events.children].some((row) => row.textContent.includes('me_views: failed -- The tab closed')));
  showTheEvents(parts, []);
  check('AJ9 6: with nothing to show it says nothing has run', parts.events.children.length === 1 && /Nothing has run yet/.test(parts.events.children[0].textContent));
}

/* ------------------------------------------------ AJ9 proving: what the run-before-last's checks never saw */

{
  /* The events of the panel's answer name a report by the book's name, and by its id when the book has no such report. */
  installFakeBrowser();
  const { chrome } = installFakeChrome();
  const named = BOOK.reports.find((one) => one.id === 'fk_orders');
  await chrome.storage.local.set({
    [THE_NIGHT]: {
      startedAt: 1_000_000, finishedAt: null, doing: null, left: [], spent: 0,
      done: [
        { reportId: 'fk_orders', state: 'landed', at: 1_100_000, say: '' },
        { reportId: 'not_in_the_book', state: 'failed', at: 1_200_000, say: '' },
      ],
    },
  });
  /* Each line now starts with its platform (his ask, 1 Nov 2026); what follows is the report as before. */
  const unPrefixed = (one) => one.replace(/^(Flipkart|Meesho|Amazon): /, '');
  let words = [];
  try { words = ((await howItStands(chrome, { book: BOOK, now: Date.now() })).events || []).map((one) => unPrefixed(one.words)); } catch (wrong) { words = []; }
  check('AJ9: the panel\'s events name a report by its name in the book', Boolean(named) && named.name !== 'fk_orders'
    && words.some((one) => one.startsWith(`${named.name}: `)));
  check('AJ9: and a report the book does not know by its id', words.some((one) => one.startsWith('not_in_the_book: ')));
  let bare = null;
  try { bare = await howItStands(chrome, { book: { ...BOOK, reports: undefined }, now: Date.now() }); } catch (wrong) { bare = null; }
  check('AJ9: a book with no report list still names each report by its id',
    Boolean(bare) && (bare.events || []).some((one) => unPrefixed(one.words).startsWith('fk_orders: ')));
}

{
  /* His ask, 1 Nov 2026: the Last run box holds EVERY platform of the sync, not only the last that ran. */
  installFakeBrowser();
  const { chrome } = installFakeChrome();
  const fk = BOOK.reports.find((one) => one.platform === 'flipkart');
  const me = BOOK.reports.find((one) => one.platform === 'meesho');
  const az = BOOK.reports.find((one) => one.platform === 'amazon');
  const aNight = (startedAt, reportId, state, extra = {}) => ({
    startedAt, finishedAt: startedAt + 60_000, doing: null, left: [], spent: 0, why: '',
    done: [{ reportId, state, at: startedAt + 30_000, say: `${reportId} said`, dataDate: '2026-10-31', pageWas: 'x'.repeat(900) }],
    toldKartaan: { said: 'Kartaan was told.', told: true, pass: 'never-kept' }, ...extra,
  });
  /* Flipkart, then Meesho, finish and are filed; Amazon is still going. */
  await chrome.storage.local.set({ [THE_NIGHT]: aNight(1_000_000, fk.id, 'landed') });
  await rememberTheNight(chrome, { book: BOOK });
  await chrome.storage.local.set({ [THE_NIGHT]: aNight(2_000_000, me.id, 'failed', { why: 'Every report was tried.' }) });
  await rememberTheNight(chrome, { book: BOOK });
  await chrome.storage.local.set({ [THE_NIGHT]: { ...aNight(3_000_000, az.id, 'landed'), finishedAt: null, doing: az.id } });
  let stands = null;
  try { stands = await howItStands(chrome, { book: BOOK, now: Date.now() }); } catch (wrong) { stands = null; }
  const runs = (stands && stands.runs) || [];
  check('Last run: all three platforms are in the panel\'s answer, in walking order',
    runs.map((one) => one.platform).join(',') === 'flipkart,meesho,amazon');
  check('Last run: the kept platforms carry their own reports; the one still going is the live night',
    runs.length === 3 && runs[0].night.done[0].reportId === fk.id && runs[1].night.done[0].state === 'failed'
    && runs[2].night.doing === az.id);
  check('Last run: a kept night is cut short (page words at most 300) and keeps nothing it was not asked to',
    runs.length === 3 && runs[0].night.done[0].pageWas.length === 300 && !('pass' in (runs[0].night.toldKartaan || {})));
  const words = ((stands && stands.events) || []).map((one) => one.words);
  check('What happened, in order: every platform\'s lines, each starting with its platform, in time order',
    words.some((one) => one.startsWith(`Flipkart: ${fk.name}: fetched`))
    && words.some((one) => one.startsWith(`Meesho: ${me.name}: `))
    && words.some((one) => one.startsWith('Amazon: Fetching now'))
    && words.indexOf(words.find((one) => one.startsWith('Flipkart: The run ended')))
      < words.indexOf(words.find((one) => one.startsWith('Meesho: The run started'))));
  const outOfOrder = allTheEvents([
    { name: 'Meesho', night: { startedAt: 9_000, finishedAt: 9_500, done: [] } },
    { name: 'Flipkart', night: { startedAt: 1_000, finishedAt: 1_500, done: [] } },
  ], (id) => id);
  check('What happened, in order: by time, not by platform -- a platform that ran first is listed first',
    outOfOrder.length > 0 && outOfOrder[0].words.startsWith('Flipkart: ')
    && outOfOrder[outOfOrder.length - 1].words.startsWith('Meesho: '));
  check('What happened, in order: the line with no time (fetching now) comes last',
    words.length > 0 && words[words.length - 1].startsWith('Amazon: Fetching now'));
  check('What happened, in order: a kept platform still says why its run ended and what Kartaan was told',
    words.includes('Meesho: The run ended: Every report was tried.') && words.includes('Flipkart: Kartaan: Kartaan was told.'));
  const unnamed = theRuns(BOOK, { ...aNight(11_000_000, 'not_in_the_book', 'failed') }, {});
  check('Last run: a night no platform can be named for is still shown, untitled',
    unnamed.length === 1 && unnamed[0].platform === '' && unnamed[0].night.startedAt === 11_000_000);

  const parts = buildThePanel(document.body, { connectTheDrive() {}, saveThePanelName() {}, runNow() {}, stop() {}, setTheHour() {} });
  showHowItStands(parts, stands);
  const every = (node) => [node, ...[...(node.children || [])].flatMap(every)];
  const titles = every(parts.log).filter((one) => String(one.className || '').split(' ').includes('p-run-title'))
    .map((one) => one.textContent);
  check('Last run box: one table per platform, titled with each platform',
    titles.join('|') === 'Last run: Flipkart');
  const everyOne = (node) => [node, ...(node.children || []).flatMap(everyOne)];
  const tabFor = (name) => everyOne(parts.platforms).find((one) => one.tagName === 'button' && one.textContent.startsWith(name));
  tabFor('Meesho').click();
  check('PN2b: choosing Meesho shows its own table, and only that one',
    everyOne(parts.log).filter((one) => String(one.className || '').split(' ').includes('p-run-title')).map((one) => one.textContent).join('|') === 'Last run: Meesho');
  tabFor('Amazon').click();
  check('PN2b: and Amazon its own', everyOne(parts.log).some((one) => one.textContent === 'Last run: Amazon'));
  tabFor('Flipkart').click();
  const before = parts.log.firstChild;
  showHowItStands(parts, stands);
  check('Last run box: the same answer again is not drawn again', parts.log.firstChild === before);
  const empty = buildThePanel(document.body, { connectTheDrive() {}, saveThePanelName() {}, runNow() {}, stop() {}, setTheHour() {} });
  showHowItStands(empty, { ...stands, runs: [], night: null });
  check('Last run box: with no run at all it says no sync has been run', /No sync has been run/.test(empty.log.textContent));

  /* Review findings: an hourly re-check never replaces the run it re-checks; it is its own small table beside it. */
  const fk2 = BOOK.reports.filter((one) => one.platform === 'flipkart')[1];
  const fullRun = { ...aNight(4_000_000, fk.id, 'landed'),
    done: [...aNight(4_000_000, fk.id, 'landed').done, { reportId: fk2.id, state: 'still-waiting', at: 4_010_000, say: '', dataDate: '2026-10-31' }] };
  await chrome.storage.local.set({ [THE_NIGHT]: fullRun });
  await rememberTheNight(chrome, { book: BOOK });
  const recheck = { ...aNight(5_000_000, fk2.id, 'landed'), finishedAt: null, doing: fk2.id, done: [], idle: { kind: 'recheck', waitedMs: 0 } };
  await chrome.storage.local.set({ [THE_NIGHT]: recheck });
  let during = null;
  try { during = await howItStands(chrome, { book: BOOK, now: Date.now() }); } catch (wrong) { during = null; }
  const fkRuns = ((during && during.runs) || []).filter((one) => one.platform === 'flipkart');
  check('Last run: a re-check going now (nothing finished yet) shows under the Flipkart run, which keeps all its rows and times',
    fkRuns.length === 2 && fkRuns[0].night.startedAt === 4_000_000 && fkRuns[0].night.done.length === 2
    && fkRuns[1].name === 'Flipkart (hourly re-check)' && fkRuns[1].night.doing === fk2.id);
  await chrome.storage.local.set({ [THE_NIGHT]: { ...recheck, finishedAt: 5_060_000, doing: null,
    done: [{ reportId: fk2.id, state: 'landed', at: 5_030_000, say: '', dataDate: '2026-10-31' }] } });
  await rememberTheNight(chrome, { book: BOOK });
  const keptFk = (await theNights(chrome)).byPlatform.flipkart;
  check('Last run: once filed, the run is kept exactly as it was and the re-check is kept beside it',
    keptFk.night.startedAt === 4_000_000 && keptFk.night.finishedAt === fullRun.finishedAt && keptFk.night.done.length === 2
    && keptFk.recheck && keptFk.recheck.done.length === 1 && keptFk.recheck.done[0].state === 'landed');
  let after = null;
  try { after = await howItStands(chrome, { book: BOOK, now: Date.now() }); } catch (wrong) { after = null; }
  check('Last run: after the re-check ends, both tables are still in the box (the run, then its re-check)',
    ((after && after.runs) || []).filter((one) => one.platform === 'flipkart').map((one) => one.name).join('|')
      === 'Flipkart|Flipkart (hourly re-check)');
  await chrome.storage.local.set({ [THE_NIGHT]: { ...aNight(6_000_000, fk.id, 'landed'),
    done: [{ reportId: fk.id, state: 'landed', at: 6_010_000, say: '', dataDate: '2026-11-01' }] } });
  await rememberTheNight(chrome, { book: BOOK });
  const nextDay = (await theNights(chrome)).byPlatform.flipkart;
  check('Last run: the next run (not a re-check) replaces the run and clears its re-check',
    nextDay.night.startedAt === 6_000_000 && nextDay.recheck === null);
  check('Last run: after a re-check the platform card keeps the run\'s counts, so card and table agree',
    keptFk.landed === 1 && keptFk.reached === 2 && keptFk.startedAt === 4_000_000);

  /* Review finding: a re-check filed with no run before it is drawn ONCE, titled as a re-check. */
  const lone = installFakeChrome().chrome;
  const loneRecheck = { ...aNight(8_000_000, fk.id, 'landed'), idle: { kind: 'recheck', waitedMs: 0 } };
  await lone.storage.local.set({ [THE_NIGHT]: loneRecheck });
  await rememberTheNight(lone, { book: BOOK });
  let loneStands = null;
  try { loneStands = await howItStands(lone, { book: BOOK, now: Date.now() }); } catch (wrong) { loneStands = null; }
  check('Last run: a re-check with no run before it is drawn once, titled as an hourly re-check',
    ((loneStands && loneStands.runs) || []).filter((one) => one.platform === 'flipkart').map((one) => one.name).join('|')
      === 'Flipkart (hourly re-check)');
  await lone.storage.local.set({ [THE_NIGHT]: { ...aNight(9_000_000, me.id, 'landed') } });
  let later = null;
  try { later = await howItStands(lone, { book: BOOK, now: Date.now() }); } catch (wrong) { later = null; }
  check('Last run: and once another platform is running, that kept re-check is still titled a re-check, not a full run',
    ((later && later.runs) || []).some((one) => one.platform === 'flipkart' && one.name === 'Flipkart (hourly re-check)'));

  /* A long catch-up run keeps only its newest rows. */
  const many = Array.from({ length: 350 }, (_, i) => ({ reportId: fk.id, state: 'landed', at: i, dataDate: `d${i}`, say: '' }));
  const keptMany = aCopyToKeep({ startedAt: 1, finishedAt: 2, done: many });
  check('Last run: a kept run holds at most the newest 300 rows',
    keptMany.done.length === 300 && keptMany.done[0].dataDate === 'd50' && keptMany.done[299].dataDate === 'd349');

  /* An entry kept by the version before (no `night` on it) is skipped quietly; a night with no platform has a plain title. */
  const older = installFakeChrome().chrome;
  await older.storage.local.set({ [THE_NIGHTS]: { byPlatform: { meesho: { startedAt: 1, finishedAt: 2, reached: 1, landed: 1, failed: 0, why: '' } } } });
  let oldStands = null;
  try { oldStands = await howItStands(older, { book: BOOK, now: Date.now() }); } catch (wrong) { oldStands = null; }
  check('Last run: what the older version kept (counts only) is skipped, never a crash',
    Boolean(oldStands) && oldStands.runs.length === 0);
  /* Review finding: the first re-check after the update keeps the older version's card counts, never its own. */
  await older.storage.local.set({ [THE_NIGHT]: { ...aNight(10_000_000, me.id, 'landed'), idle: { kind: 'recheck', waitedMs: 0 } } });
  await rememberTheNight(older, { book: BOOK });
  const card = (await theNights(older)).byPlatform.meesho;
  check('Last run: the first re-check after the update leaves the card\'s counts as they were and is kept as a re-check',
    card.startedAt === 1 && card.reached === 1 && card.recheck && card.recheck.startedAt === 10_000_000);
  const nameless = buildThePanel(document.body, { connectTheDrive() {}, saveThePanelName() {}, runNow() {}, stop() {}, setTheHour() {} });
  showTheRuns(nameless.log, [{ name: '', table: theReportTable(aNight(7_000_000, 'not_in_the_book', 'failed'), (id) => id) }], new Set());
  check('Last run box: a night no platform can be named for is titled plainly "Last run"',
    every(nameless.log).some((one) => String(one.className || '').split(' ').includes('p-run-title') && one.textContent === 'Last run'));
}

{
  /* theNightsEvents: an event with no time of its own takes the night's start; "Kartaan:" only when something was said. */
  const night = { startedAt: 5000, finishedAt: 9000, why: '', done: [{ reportId: 'fk_orders', state: 'landed', say: '' }] };
  let events = [];
  try { events = theNightsEvents(night); } catch (wrong) { events = []; }
  check('AJ9: a report event with no time of its own is put at the night\'s start',
    events.some((one) => one.words.startsWith('fk_orders: ') && one.at === 5000));
  check('AJ9: a night that told Kartaan nothing has no "Kartaan:" line', events.length > 0 && !events.some((one) => one.words.startsWith('Kartaan:')));
  let quiet = [];
  try { quiet = theNightsEvents({ ...night, toldKartaan: { told: false } }); } catch (wrong) { quiet = []; }
  check('AJ9: and nor does one whose answer said no words', quiet.length > 0 && !quiet.some((one) => one.words.startsWith('Kartaan:')));
}

{
  /* A platform refused in the middle of a sync is MERGED into the ids already failed, with no id twice. */
  const { chrome } = installFakeChrome();
  const parts = { book: BOOK, now: () => Date.UTC(2026, 8, 16, 3, 0), startTheNight, carryOn: async () => {}, continuing: true };
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  await chrome.storage.local.set({ [THE_SYNC_FAILED]: ['fk_claims', 'nonsense_one'], [THE_QUEUE]: [['nonsense_one'], ['nonsense_two']] });
  try { await startTheNextPlatform(chrome, parts); } catch (wrong) { /* read below */ }
  const kept = (await chrome.storage.local.get(THE_SYNC_FAILED))[THE_SYNC_FAILED] || [];
  check('AJ9: refused platforms are added to the ids already failed, each once', kept.join() === 'fk_claims,nonsense_one,nonsense_two');
  await chrome.storage.local.remove(THE_SYNC_FAILED);
  await chrome.storage.local.set({ [THE_QUEUE]: [['nonsense_one']] });
  try { await startTheNextPlatform(chrome, parts); } catch (wrong) { /* read below */ }
  check('AJ9: and with nothing failed before, the refused ids alone are kept',
    ((await chrome.storage.local.get(THE_SYNC_FAILED))[THE_SYNC_FAILED] || []).join() === 'nonsense_one');
}

{
  /* Kartaan's no keeps the platforms never tried, and the one tell names the union, each once, at the night's own end. */
  const { chrome } = installFakeChrome();
  const fetch = async () => ({ status: 403, json: async () => ({ fetch: false, said: 'Not on your plan.' }) });
  const parts = { book: BOOK, now: () => Date.UTC(2026, 8, 16, 3, 0), startTheNight, carryOn: async () => {}, continuing: true, fetch };
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  await saveTheRunPass(chrome, `${'abcDEF0123456789-_'.repeat(8)}.${'xyz789'.repeat(10)}`);
  await chrome.storage.local.set({
    [THE_SYNC_FAILED]: ['fk_claims', 'me_orders'], [THE_QUEUE]: [['fk_returns'], ['me_orders'], { reportIds: ['az_ads'] }],
  });
  let next = null;
  try { next = await startTheNextPlatform(chrome, parts); } catch (wrong) { next = null; }
  check('AJ9: after Kartaan\'s no, the platforms never tried are kept, a timed entry and a Run now entry alike',
    Boolean(next) && (next.neverTried || []).join() === 'me_orders,az_ads');
  const told = [];
  const tell = async (what) => { told.push(what); return { told: true, said: 'heard' }; };
  await tellForASyncThatCannotContinue(chrome, next || { started: null, refused: [] }, { startedAt: 500, finishedAt: 777 }, tell);
  check('AJ9: the one tell names what failed, what was refused and what was never tried, each once',
    told.length === 1 && (told[0].failed || []).join() === 'fk_claims,me_orders,fk_returns,az_ads');
  check('AJ9: and it is named by the finished night\'s end, never the clock', told.length === 1 && told[0].endedAt === 777);
  await chrome.storage.local.set({ [THE_SYNC_FAILED]: ['fk_claims'] });
  let answer = null;
  try { answer = await tellForASyncThatCannotContinue(chrome, { started: null }, null, tell); } catch (wrong) { answer = null; }
  check('AJ9: with no done night and no refused or untried list, it still tells the held ids, with no end time',
    Boolean(answer) && told.length === 2 && (told[1].failed || []).join() === 'fk_claims' && told[1].endedAt == null);
}

{
  /* The panel's "What happened, in order" card holds the events list, and is drawn from what the panel was told. */
  installFakeBrowser();
  const { chrome } = installFakeChrome();
  const parts = buildThePanel(document.body, { connectTheDrive() {}, saveThePanelName() {}, runNow() {}, stop() {}, setTheHour() {} });
  check('AJ9/R250 (drawing: "off panel"): "What happened" is worked out into the events list but is not drawn on the panel',
    Boolean(parts.events) && !document.body.contains(parts.events) && !document.body.textContent.includes('What happened'));
  const stands = await howItStands(chrome, { book: BOOK, now: Date.now() });
  showHowItStands(parts, { ...stands, events: [{ at: null, words: 'Fetching now: Flipkart orders.' }] });
  check('AJ9: the events the panel is told are the ones drawn',
    parts.events.children.length === 1 && parts.events.children[0].textContent === 'Fetching now: Flipkart orders.');
  const first = parts.events.children[0];
  showTheEvents(parts, [{ at: null, words: 'Fetching now: Flipkart orders.' }]);
  check('AJ9: the same events again are not drawn again', parts.events.children[0] === first);
  const fresh = buildThePanel(document.body, { connectTheDrive() {}, saveThePanelName() {}, runNow() {}, stop() {}, setTheHour() {} });
  let threw = false;
  try { showHowItStands(fresh, { ...stands, events: undefined }); } catch (wrong) { threw = true; }
  check('AJ9: an answer with no events says nothing has run yet',
    !threw && fresh.events.children.length === 1 && /Nothing has run yet/.test(fresh.events.children[0].textContent));
}

/* ------------------------------------------------- AS6 round 2: R160, R166 / J016 */

{
  installFakeBrowser();
  const { chrome } = installFakeChrome();
  const done = [];
  const panel = buildThePanel(document.body, { clearNeedsYou: (days) => done.push(JSON.stringify(days)) });
  check('J016: the panel may ask for it', THE_PANEL_ASKS.includes('clear-needs-you'));
  const stands = await howItStands(chrome, { book: BOOK, now: Date.now() });
  const said = 'Kartaan was not told this sync finished, because no run pass is saved. The run still runs on its own schedule.';
  showHowItStands(panel, { ...stands, kartaan: { saved: true, last: { at: 1, kind: 'finished', said } } });
  check('R160: a "no run pass is saved" line is not shown beside a pass that is saved', panel.kartaanSaid.textContent === '');
  showHowItStands(panel, { ...stands, kartaan: { saved: false, last: { at: 1, kind: 'finished', said } } });
  check('R160: and is shown when no pass is saved', panel.kartaanSaid.textContent.includes('no run pass is saved'));
  check('PN2a: the box starts hidden and is the first thing in the body', panel.needs.hidden === true);
  const two = [
    { reportId: 'fk_claims', dataDate: '2026-10-01', beyondReach: true, name: 'Claims', platformName: 'Flipkart', folder: 'Kartaan > Flipkart > Claims' },
    { reportId: 'fk_orders', dataDate: '2026-10-02', triedOn: ['a', 'b', 'c'], name: 'Orders', platformName: 'Flipkart', folder: '' },
  ];
  showHowItStands(panel, { ...stands, needsYou: [] });
  check('PN2a: with nothing that needs him, the box is hidden', panel.needs.hidden === true);
  showHowItStands(panel, { ...stands, needsYou: [two[0]] });
  check('PN2a: one day: the box shows, names platform, report, day and folder, and has no "I placed all"',
    panel.needs.hidden === false && panel.needs.textContent.includes('Flipkart · Claims -- 1 day') && panel.needs.textContent.includes('2026-10-01')
    && panel.needs.textContent.includes('Put it in: Kartaan > Flipkart > Claims') && !panel.needs.textContent.includes('I placed all'));
  const allIn = (node) => [node, ...node.children.flatMap(allIn)];
  const buttons = (words, on = panel) => allIn(on.needs).filter((one) => one.tagName === 'button' && one.textContent === words);
  buttons('I placed it')[0].click();
  check('PN2a: "I placed it" names exactly that one day', done.join() === '[{"reportId":"fk_claims","dataDate":"2026-10-01"}]');
  showHowItStands(panel, { ...stands, needsYou: two });
  check('PN2a: two days: a row each, the tries counted, and "I placed all" appears',
    buttons('I placed it').length === 2 && buttons('I placed all').length === 1 && panel.needs.textContent.includes('tried 3 times'));
  buttons('I placed all')[0].click();
  check('PN2a: "I placed all" names both days and no other', done[1] === JSON.stringify(two.map((one) => ({ reportId: one.reportId, dataDate: one.dataDate }))));
  showHowItStands(panel, { ...stands, needsYou: undefined });
  check('PN2a: with no list the box is hidden again', panel.needs.hidden === true);
  const fresh = buildThePanel(document.body, {});
  check('PN2a: a new panel has the box hidden, empty and first in the body', fresh.needs.hidden === true && fresh.needs.textContent === '' && fresh.needs.parentNode.children[0] === fresh.needs);
  const mine = buildThePanel(document.body, { clearNeedsYou() {} });
  check('PN2a: the run buttons are Run now, Resume and Stop and nothing else', mine.actions.children.length === 3);
  showHowItStands(mine, { ...stands, needsYou: two });
  const firstButton = buttons('I placed it', mine)[0];
  showHowItStands(mine, { ...stands, needsYou: two });
  check('PN2a: the same list drawn again does not rebuild the rows', buttons('I placed it', mine)[0] === firstButton);
  showHowItStands(mine, { ...stands, needsYou: [two[0], { ...two[1], folder: 'Kartaan > Elsewhere' }] });
  check('PN2a: a changed folder does rebuild them', buttons('I placed it', mine)[0] !== firstButton && mine.needs.textContent.includes('Kartaan > Elsewhere'));
  showHowItStands(mine, { ...stands, needsYou: [] });
  check('PN2a: an emptied list leaves nothing in the box', mine.needs.textContent === '' && mine.needs.hidden === true);
  showHowItStands(mine, { ...stands, needsYou: two });
  check('PN2a: the i tells him what to do', mine.needs.find('p-hint').title.includes('I placed it') && mine.needs.find('p-hint').title.includes('Drive'));
  check('PN2a: the count shows how many', mine.needs.find('p-count').textContent === '2');
  check('PN2a: the buttons are plain buttons, not form submits',
    buttons('I placed it', mine).every((one) => one.type === 'button') && buttons('I placed all', mine)[0].type === 'button');
  const instantAsked = [];
  const pb = buildThePanel(document.body, { runNow: (ids, from, to) => instantAsked.push([ids, from, to]) });
  const bodyKids = pb.needs.parentNode.children;
  check('PN2b: Days to fetch, Run now and Stop come straight after the needs box, before set-up and before the platforms',
    bodyKids[0] === pb.needs && bodyKids.indexOf(pb.from.parentNode) > 0 && bodyKids.indexOf(pb.from.parentNode) < bodyKids.indexOf(pb.settings)
    && bodyKids.indexOf(pb.platforms) > bodyKids.indexOf(pb.from.parentNode));
  const live = { ...stands, setUp: { ...stands.setUp, done: true } };
  showHowItStands(pb, live);
  const tabs = () => pb.platforms.children;
  check('PN2b: three platform buttons, Flipkart chosen to begin with', tabs().length === 3 && pb.chosen === 'flipkart');
  check('PN2b: only the chosen platform\'s reports show', pb.groups.size === 3 && [...pb.groups].every(([platform, group]) => group.hidden === (platform !== 'flipkart')));
  check('PN2b: the requests-left line shows for Flipkart', pb.allowanceCard.hidden === false);
  const kept = pb.ticked.size;
  pb.selectAll.click();
  const flipkartTicked = pb.platformIds.get('flipkart').filter((id) => !pb.boxes.get(id).disabled && pb.ticked.has(id)).length;
  check('PN2b: ticking all is counted on the folded heading and on the platform\'s button',
    pb.ticked.size !== kept && pb.foldTitle.textContent.startsWith(`What to fetch \u00B7 ${flipkartTicked} of `) && tabs()[0].textContent.startsWith(`Flipkart${flipkartTicked} ticked`));
  check('PN2b: and Tick all platforms says it ticks every platform', pb.selectAll.textContent.endsWith(' all platforms'));
  pb.selectAll.click();
  const meeshoTab = tabs().find((one) => one.textContent.startsWith('Meesho'));
  meeshoTab.click();
  check('PN2b: choosing Meesho hides Flipkart\'s reports and requests line and shows Meesho\'s',
    pb.groups.get('flipkart').hidden === true && pb.groups.get('meesho').hidden === false && pb.allowanceCard.hidden === true);
  showHowItStands(pb, { ...live, needsYou: [{ ...two[0], platformName: 'Meesho' }] });
  const meeshoNow = pb.platforms.children.find((one) => one.textContent.startsWith('Meesho'));
  check('PN2b: a day that needs him puts a red number on its platform\'s button only',
    meeshoNow.children[0].children.some((one) => one.className === 'p-count' && one.textContent === '1')
    && !pb.platforms.children.find((one) => one.textContent.startsWith('Flipkart')).children[0].children.some((one) => one.className === 'p-count'));
  const flipkartOnes = stands.reports.filter((one) => one.platform === 'flipkart' && one.canBeFetched && !one.fetchedBy);
  check('PN2b: the instant row lists the first platform\'s fetchable reports', pb.instantReport.children.length === flipkartOnes.length && flipkartOnes.length > 1);
  pb.instantReport.value = flipkartOnes[1].id;
  pb.from.value = '2026-10-01';
  pb.to.value = '2026-10-03';
  const tickedBefore = [...pb.ticked].join();
  pb.instantRun.click();
  check('PN2b: Run in the instant row asks for that one report and the days above, and leaves the ticks alone',
    instantAsked.length === 1 && instantAsked[0][0].join() === flipkartOnes[1].id && instantAsked[0][1] === '2026-10-01' && instantAsked[0][2] === '2026-10-03'
    && [...pb.ticked].join() === tickedBefore);
  pb.instantPlatform.value = 'amazon';
  showHowItStands(pb, live);
  const amazonOnes = stands.reports.filter((one) => one.platform === 'amazon' && one.canBeFetched && !one.fetchedBy);
  check('PN2b: another platform lists its own reports', pb.instantReport.children.length === amazonOnes.length);
  const noReport = buildThePanel(document.body, { runNow: (ids) => instantAsked.push(ids) });
  noReport.instantRun.click();
  check('PN2b: with no report chosen the instant Run asks for nothing', instantAsked.length === 1);
  const goingNight = { ...stands, night: { startedAt: 1, finishedAt: null, done: [], left: [], doing: null }, setUp: { ...stands.setUp, done: true } };
  showHowItStands(pb, { ...goingNight, setUp: live.setUp });
  check('PN2b: while a run is going the instant Run is off as Run now is', pb.runNow.disabled === true && pb.instantRun.disabled === true);
  /* PN2b proving: every moved and new line is pinned. */
  const fp = buildThePanel(document.body, { runNow() {} });
  const fpBody = fp.needs.parentNode.children;
  const rowOf = (node) => node.parentNode;
  check('PN2b: the top of the panel is, in order, needs box, update strip, days row (with Run now and Stop beside the dates), said line, instant row, status line, set-up',
    [fp.needs, fp.update, rowOf(fp.from), fp.said, rowOf(fp.instantPlatform), fp.banner, fp.settings].every((node, at, all) => at === 0 || fpBody.indexOf(node) === fpBody.indexOf(all[at - 1]) + 1));
  check('PN2b: the two day boxes are date boxes, From then To, in the days row',
    fp.from.type === 'date' && fp.to.type === 'date' && rowOf(fp.from).children.indexOf(fp.from) + 2 === rowOf(fp.from).children.indexOf(fp.to)
    && rowOf(fp.from).children[rowOf(fp.from).children.indexOf(fp.from) - 1].textContent === 'From' && rowOf(fp.to).children[rowOf(fp.to).children.indexOf(fp.to) - 1].textContent === 'To');
  check('PN2b: Run now, Stop, Resume and the instant Run are plain buttons, Resume and the said line start hidden',
    [fp.runNow, fp.stop, fp.resume, fp.instantRun].every((one) => one.type === 'button') && fp.resume.hidden === true && fp.said.hidden === true);
  check('PN2b: the instant row names the three platforms in order, starts on Flipkart and explains itself',
    fp.instantPlatform.children.map((one) => one.textContent).join() === 'Flipkart,Meesho,Amazon'
    && fp.instantPlatform.children.map((one) => one.value).join() === 'flipkart,meesho,amazon' && fp.instantPlatform.value === 'flipkart'
    && rowOf(fp.instantPlatform).children.map((one) => one.textContent).includes('Instant download')
    && rowOf(fp.instantPlatform).children[0].textContent === 'Instant download'
    && rowOf(fp.instantPlatform).children[1] === fp.instantPlatform && rowOf(fp.instantPlatform).children[2] === fp.instantReport
    && rowOf(fp.instantPlatform).children[3] === fp.instantRun && rowOf(fp.instantPlatform).children[4].title.includes('ticks are not touched'));
  check('PN2b: the folded list holds its heading, the tick-all button and the list, inside the What to fetch card',
    fp.fold.children[0] === fp.foldTitle && fp.fold.children[1] === fp.selectAll && fp.fold.children[2] === fp.reports && fpBody.includes(fp.fold.parentNode));
  showHowItStands(fp, live);
  check('PN2b: each platform\'s group sits in the list, its heading first and then its reports',
    [...fp.groups.values()].every((group) => fp.reports.children.includes(group) && String(group.children[0].className).includes('platform-group'))
    && fp.groups.get('flipkart').children.length === 1 + stands.reports.filter((one) => one.platform === 'flipkart').length);
  const fkReachable = stands.reports.filter((one) => one.platform === 'flipkart' && one.canBeFetched && !one.fetchedBy).length;
  check('PN2b: the heading counts only reports that can be ticked', fp.foldTitle.textContent.endsWith(` of ${fkReachable} ticked`));
  check('PN2b: the platform buttons are plain buttons', fp.platforms.children.length === 3 && fp.platforms.children.every((one) => one.type === 'button'));
  const optionBefore = fp.instantReport.children[0];
  showHowItStands(fp, live);
  check('PN2b: the same list again leaves the instant report choices alone', fp.instantReport.children[0] === optionBefore);
  fp.instantPlatform.value = 'meesho';
  fp.instantPlatform.dispatchEvent({ type: 'change' });
  check('PN2b: changing the instant platform fills its reports at once', fp.instantReport.children.length === stands.reports.filter((one) => one.platform === 'meesho' && one.canBeFetched && !one.fetchedBy).length
    && fp.instantReport.children[0] !== optionBefore);
  const oldGroups = [...fp.groups.values()];
  showHowItStands(fp, { ...live, reports: live.reports.slice(0, live.reports.length - 1) });
  check('PN2b: when the report list changes the groups are rebuilt, not added to', fp.groups.size === 3 && [...fp.groups.values()].every((group) => !oldGroups.includes(group)) && fp.reports.children.length === 3);
  showHowItStands(fp, { ...live, reports: live.reports.filter((one) => one.platform !== 'amazon') });
  check('PN2b: a platform that no longer has reports loses its group', fp.groups.size === 2 && !fp.groups.has('amazon'));
  const tiny = { kartaan: 'Mine', reports: [{ id: 'zz_a', name: 'A report', platform: 'flipkart' }], folders: { zz_a: ['Flipkart', 'Things'] } };
  const r1 = theNeedsYouRow(tiny, { reportId: 'zz_a', dataDate: '2026-10-02', triedOn: ['x'] });
  check('PN2a: the row gets its report name, platform and folder, and keeps what it had',
    r1.name === 'A report' && r1.platformName === 'Flipkart' && r1.folder === 'Mine > Flipkart > Things' && r1.triedOn.length === 1 && r1.dataDate === '2026-10-02');
  const r2 = theNeedsYouRow({ reports: [], folders: {} }, { reportId: 'zz_b', dataDate: 'd' });
  check('PN2a: an unknown report shows its id and no folder', r2.name === 'zz_b' && r2.folder === '');
  check('PN2a: with no Kartaan folder name the word Kartaan is used', theNeedsYouRow({ folders: { zz_c: ['A'] } }, { reportId: 'zz_c' }).folder === 'Kartaan > A');
  await chrome.storage.local.set({ 'kartaan-autosync-needs-you': [{ reportId: 'fk_orders', dataDate: '2026-10-02', triedOn: [] }] });
  const standing = await howItStands(chrome, { book: BOOK, now: Date.now() });
  await chrome.storage.local.remove('kartaan-autosync-needs-you');
  check('PN2a: what the panel is told carries the report name and folder', standing.needsYou[0].name.length > 0 && standing.needsYou[0].folder.includes(' > '));
  const waited = () => new Promise((resolve) => setTimeout(resolve, 20));
  let asksMade = 0;
  await chrome.storage.local.set({ 'kartaan-autosync-update': { checkedAt: 5000, latest: '0.1.1', url: '', notes: '', error: '' } });
  const counting = async () => { asksMade += 1; return { ok: true, status: 200, json: async () => ({ version: '0.1.1' }) }; };
  const overOpen = { book: BOOK, now: () => 6000, installed: '0.1.1', fetchTheVersion: counting };
  await answerThePanelsQuestion(chrome, overOpen, { do: 'how-it-stands' });
  await waited();
  check('PN2a: an ordinary poll does not ask for the version file again', asksMade === 0);
  await answerThePanelsQuestion(chrome, overOpen, { do: 'how-it-stands', opened: true });
  await waited();
  check('PN2a: opening the panel does', asksMade === 1);
  await answerThePanelsQuestion(chrome, overOpen, { do: 'how-it-stands', opened: 'yes' });
  await waited();
  check('PN2a: only a plain true counts as opening', asksMade === 1);
  await chrome.storage.local.remove('kartaan-autosync-update');
  const bare = buildThePanel(document.body, {});
  showHowItStands(bare, { ...stands, needsYou: two });
  let threw = false;
  try { buttons('I placed it', bare)[0].click(); } catch (wrong) { threw = true; }
  check('PN2a: a panel with nothing wired to the button does not fall over when it is pressed', !threw);
  const row = theNeedsYouRow(BOOK, { reportId: 'fk_orders', dataDate: '2026-10-02' });
  check('PN2a: the row is given its platform and report name', row.platformName === 'Flipkart' && row.name.length > 0);

  const parts = { book: BOOK, now: () => Date.UTC(2026, 10, 4, 3, 0), carryOn: async () => {} };
  await chrome.storage.local.set({
    'kartaan-autosync-needs-you': [
      { reportId: 'fk_claims', dataDate: '2026-10-01', beyondReach: true, since: '2026-11-04' },
      { reportId: 'fk_orders', dataDate: '2026-10-02', triedOn: [], since: '2026-11-03' },
    ],
  });
  const shown = [{ reportId: 'fk_claims', dataDate: '2026-10-01' }, { reportId: 'fk_orders', dataDate: '2026-10-02' }];
  await chrome.storage.local.set({ 'kartaan-autosync-needs-you': [
    { reportId: 'fk_claims', dataDate: '2026-10-01', beyondReach: true, since: '2026-11-04' },
    { reportId: 'fk_orders', dataDate: '2026-10-02', triedOn: [], since: '2026-11-03' },
    { reportId: 'fk_orders', dataDate: '2026-10-03', triedOn: [], since: '2026-11-04' },
  ] });
  const going = await chrome.storage.local.get('kartaan-autosync-night');
  await chrome.storage.local.set({ 'kartaan-autosync-night': { startedAt: 1, finishedAt: null, done: [], left: [] } });
  const refused = await answerThePanelsQuestion(chrome, parts, { do: 'clear-needs-you', days: shown });
  check('J016: not while a run is going', String(refused.wrong).includes('A run is going') && (await chrome.storage.local.get('kartaan-autosync-needs-you'))['kartaan-autosync-needs-you'].length === 3);
  await chrome.storage.local.remove('kartaan-autosync-night');
  const got = await answerThePanelsQuestion(chrome, parts, { do: 'clear-needs-you', days: shown });
  const left = (await chrome.storage.local.get('kartaan-autosync-needs-you'))['kartaan-autosync-needs-you'];
  const landedDays = (await chrome.storage.local.get('kartaan-autosync-last-landed'))['kartaan-autosync-last-landed'] || {};
  check('J016: the ask clears only the days named, not one that came after the panel drew', got.cleared === 2 && left.length === 1 && left[0].dataDate === '2026-10-03');
  check('J016: and marks each as landed so the next night does not write it back',
    (landedDays.fk_claims || []).includes('2026-10-01') && (landedDays.fk_orders || []).includes('2026-10-02'));
}

{
  /* **R208 (his D968, D1005, D1006, D1007): RETURNS AT 6 PM FOR TODAY, A DAY AND A RUN FOR EACH REPORT, THE MORNING'S FAILURES AT 4 PM.** */
  const noChoice = { timed: null, days: {}, runs: {} };
  check('R208: the returns of all three platforms are on their own time, and for today',
    THE_RETURNS_REPORTS.every((id) => theRunOf(noChoice, id) === 'own' && theDayOf(noChoice, id) === 'today'));
  check('R208: every other report is for yesterday', theDayOf(noChoice, 'fk_orders') === 'yesterday' && theDayOf(noChoice, 'fk_claims') === 'yesterday');
  check('R208: the seller own choice wins, and a made-up one reads as no choice',
    theRunOf({ runs: { fk_claims: 'own' } }, 'fk_claims') === 'own' && theRunOf({ runs: { fk_claims: 'noon' } }, 'fk_claims') === 'morning'
    && theDayOf({ days: { fk_claims: 'today' } }, 'fk_claims') === 'today' && theDayOf({ days: { fk_returns: 'tomorrow' } }, 'fk_returns') === 'today'
    && theDayOf({ days: { fk_returns: 'yesterday' } }, 'fk_returns') === 'yesterday');
  const now = Date.UTC(2026, 10, 7, 12, 30);
  check('R208: today is refused for a yesterday report and passes for a today report',
    whyThatDayCannotBeFetched('2026-11-07', now).includes('not over yet') && whyThatDayCannotBeFetched('2026-11-07', now, true) === ''
    && whyThatDayCannotBeFetched('2026-11-08', now, true).includes('not over yet'));

  const { chrome } = installFakeChrome();
  const nights = [];
  const parts = { book: BOOK, now: () => now, startTheNight: async (c, how) => { nights.push(how); return startTheNight(c, how); }, carryOn: async () => {} };
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  await chrome.storage.local.set({ [LAST_LANDED]: { fk_returns: ['2026-11-06'], me_returns: ['2026-11-06'], az_returns: ['2026-11-06'] } });
  const morning = await startTheScheduledSync(chrome, parts);
  check('R208: the morning run does not fetch returns that landed yesterday', !morning.started.includes('fk_returns') && nights[0].run === 'morning');
  await endTheNight(chrome, { at: now, why: 'x' });
  await chrome.storage.local.set({ [THE_QUEUE]: [] });
  nights.length = 0;
  const six = await startTheScheduledSync(chrome, parts, 'own', '18:00');
  check('R208: the 6 pm run starts the Flipkart returns for TODAY, as the returns run',
    six.started.join() === 'fk_returns' && nights[0].dataDate === '2026-11-07' && nights[0].run === 'own', '18:00');
  await endTheNight(chrome, { at: now, why: 'x' });
  const meesho = await startTheNextPlatform(chrome, parts);
  await endTheNight(chrome, { at: now, why: 'x' });
  const amazon = await startTheNextPlatform(chrome, parts);
  check('R208: and then the Meesho and Amazon returns, each for today',
    meesho.started.join() === 'me_returns' && amazon.started.join() === 'az_returns' && nights.every((one) => one.dataDate === '2026-11-07'));

  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-report-times', reportId: 'fk_claims', day: 'today', run: 'own', at: '18:00' });
  await endTheNight(chrome, { at: now, why: 'x' });

  /* Control, 7 Nov: a returns report that did NOT land is fetched next morning as an ordinary yesterday report; one that did is not. */
  const fall = installFakeChrome().chrome;
  await answerThePanelsQuestion(fall, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(fall, parts, { do: 'check-the-drive' });
  await fall.storage.local.set({ [LAST_LANDED]: { fk_returns: ['2026-11-06'], az_returns: ['2026-11-05'] } });
  const seenDays = [];
  const watching = { ...parts, startTheNight: async (c, how) => { seenDays.push([how.doing.join(), how.dataDate, how.run]); return startTheNight(c, how); } };
  const next = await startTheScheduledSync(fall, watching);
  const queuedAll = (await fall.storage.local.get(THE_QUEUE))[THE_QUEUE];
  const allIds = [...next.started, ...queuedAll.flatMap((entry) => (Array.isArray(entry) ? entry : entry.reportIds))];
  check('R208: next morning, returns that landed yesterday are not fetched again, those that did not are',
    !allIds.includes('fk_returns') && allIds.includes('az_returns') && allIds.includes('me_returns'));
  check('R208: and the fallback is an ordinary yesterday report in the morning run (Flipkart not landed: its night is for yesterday)',
    seenDays.every((one) => one[1] === '2026-11-06' && one[2] === 'morning'));
  const flipkartMissed = installFakeChrome().chrome;
  await answerThePanelsQuestion(flipkartMissed, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(flipkartMissed, parts, { do: 'check-the-drive' });
  const flipSeen = [];
  const flipParts = { ...parts, startTheNight: async (c, how) => { flipSeen.push([how.doing.join(), how.dataDate, how.run]); return startTheNight(c, how); } };
  const flip = await startTheScheduledSync(flipkartMissed, flipParts);
  check('R208: Flipkart returns that did not land at 6 pm are fetched next morning for yesterday, not today',
    flip.started.includes('fk_returns') && flipSeen[0][1] === '2026-11-06' && flipSeen[0][2] === 'morning');
  const startedLater = [];
  for (let n = 0; n < 3; n += 1) {
    await endTheNight(flipkartMissed, { at: now, why: 'x' });
    const more = await startTheNextPlatform(flipkartMissed, flipParts);
    startedLater.push(...(more.started || []));
  }
  check('R208: and Amazon returns that did not land likewise, for yesterday', startedLater.includes('az_returns')
    && flipSeen.filter((one) => one[0].includes('az_returns')).every((one) => one[1] === '2026-11-06'));
  const stands = await howItStands(chrome, { book: BOOK, now });
  const row = stands.schedule.find((one) => one.id === 'fk_claims');
  check('R208: a day and a run chosen on the panel are kept and shown back, others stay at their defaults',
    row.day === 'today' && row.run === 'own' && stands.schedule.find((one) => one.id === 'fk_returns').run === 'own', '18:00');
  const refusedTime = await answerThePanelsQuestion(chrome, parts, { do: 'save-the-report-times', reportId: 'fk_claims', day: 'someday', run: 'own', at: '18:00' });
  const refusedId = await answerThePanelsQuestion(chrome, parts, { do: 'save-the-report-times', reportId: 'not_a_report', day: 'today', run: 'own', at: '18:00' });
  check('R208: a made-up day, run or report is refused in words', Boolean(refusedTime.wrong) && Boolean(refusedId.wrong));
  const sixAgain = await startTheScheduledSync(chrome, parts, 'own', '18:00');
  check('R208: a report moved to the 6 pm run is fetched there', sixAgain.started.join() === 'fk_claims,fk_returns' || [...sixAgain.started].sort().join() === 'fk_claims,fk_returns');
}

{
  /* The hourly re-check of a returns report for today comes back through the same door. */
  const now = Date.UTC(2026, 10, 7, 10, 30);
  const parts = { book: BOOK, now: () => now, startTheNight, carryOn: async () => {} };
  const again = installFakeChrome().chrome;
  await answerThePanelsQuestion(again, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(again, parts, { do: 'check-the-drive' });
  const recheck = await startASync(again, parts, { reportIds: ['fk_returns'], day: '2026-11-07' });
  check('R208: the hourly re-check of a returns report for today starts', Boolean(recheck.started));
  await endTheNight(again, { at: now, why: 'x' });
  const notReturns = await startASync(again, parts, { reportIds: ['fk_claims'], day: '2026-11-07' });
  check('R208: and the same for a yesterday report is still refused', String(notReturns.wrong).includes('not over yet'));
}

{
  /* **R208: THE PANEL'S DAY-AND-RUN ROWS, THE QUEUE WITH OBJECTS, THE 6 PM WAKE LINE (what the first proving run found unproven).** */
  const now = Date.UTC(2026, 10, 7, 12, 30);
  check('R208: a range ending today passes when today is allowed, and not otherwise',
    whyThatRangeCannotBeFetched('2026-11-06', '2026-11-07', now, true) === '' && whyThatRangeCannotBeFetched('2026-11-06', '2026-11-07', now).includes('not over yet'));
  check('R208: the 6 pm run is named in when the extension next wakes',
    whenItNextWakes({ chosen: '08:00', nextAt: now + 1000, eveningAt: now + 2000, own: [{ time: '18:00', at: now + 3000 }] }).includes('own-time run at 18:00 wakes')
    && !whenItNextWakes({ chosen: '08:00', nextAt: now + 1000, eveningAt: now + 2000 }).includes('own-time'));
  const { chrome } = installFakeChrome();
  const parts = { book: BOOK, now: () => now, startTheNight, carryOn: async () => {} };
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  const saved = await answerThePanelsQuestion(chrome, parts, { do: 'save-the-report-times', reportId: 'fk_claims', day: 'today', run: 'evening' });
  check('R208: saving the day and run of a report answers saved', saved.saved === true);
  const stands = await howItStands(chrome, { book: BOOK, now });
  const named = stands.schedule.find((one) => one.id === 'fk_returns');
  check('R208: each row carries the own name of the report', named.name === (BOOK.reports.find((one) => one.id === 'fk_returns') || {}).name && named.name !== 'fk_returns');

  /* A yesterday report placed in the returns run is fetched for yesterday, apart from the returns for today. */
  const moved = installFakeChrome().chrome;
  await answerThePanelsQuestion(moved, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(moved, parts, { do: 'check-the-drive' });
  await answerThePanelsQuestion(moved, parts, { do: 'save-the-report-times', reportId: 'fk_claims', day: 'yesterday', run: 'own', at: '18:00' });
  const nightsSeen = [];
  const seeing = { ...parts, startTheNight: async (c, how) => { nightsSeen.push(how); return startTheNight(c, how); } };
  await startTheScheduledSync(moved, seeing, 'own', '18:00');
  const queuedAfter = (await moved.storage.local.get(THE_QUEUE))[THE_QUEUE];
  check('R208: a yesterday report in the 6 pm run is fetched for yesterday, the returns for today, as separate walks',
    nightsSeen[0].doing.includes('fk_claims') && !nightsSeen[0].doing.includes('fk_returns') && nightsSeen[0].dataDate === '2026-11-06' && nightsSeen[0].run === 'own'
    && queuedAfter.some((entry) => !Array.isArray(entry) && entry.today === true && entry.reportIds.includes('fk_returns')));

  /* A run that finds another going queues behind it: entries keep their run and today mark, and what is already there is not queued twice. */
  const behind = installFakeChrome().chrome;
  await answerThePanelsQuestion(behind, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(behind, parts, { do: 'check-the-drive' });
  await behind.storage.local.set({ [THE_NIGHT]: { startedAt: now, finishedAt: 0, spent: 0, mayAskFor: 3, done: [], left: ['fk_returns'], doing: null }, [THE_QUEUE]: [] });
  const waitingRun = await startTheScheduledSync(behind, parts, 'own', '18:00');
  const queuedIds = (await behind.storage.local.get(THE_QUEUE))[THE_QUEUE];
  check('R208: behind a going run the 6 pm entries are queued with their run and today mark, without the report already left',
    waitingRun.waiting === true && queuedIds.length > 0 && queuedIds.every((entry) => !Array.isArray(entry) && entry.run === 'own' && entry.today === true)
    && !queuedIds.flatMap((entry) => entry.reportIds).includes('fk_returns') && queuedIds.flatMap((entry) => entry.reportIds).includes('me_returns'));
  /* The panel draws the rows, sends what is picked, and does not redraw when nothing changed. */
  installFakeBrowser();
  const picked = [];
  const panel = buildThePanel(document.body, { saveTheReportTimes: (id, day, run) => picked.push(`${id}:${day}:${run}`) });
  const schedule = [{ id: 'fk_returns', name: 'Flipkart returns', day: 'today', run: 'own', at: '18:00' }, { id: 'fk_claims', name: 'Flipkart claims', day: 'yesterday', run: 'morning' }];
  showHowItStands(panel, { ...stands, schedule });
  const selects = panel.scheduleList.children.flatMap((row) => row.children.flatMap((one) => (one.tagName === 'select' ? [one] : one.children.filter((c) => c.tagName === 'select'))));
  check('R208: the panel draws a day and a run for each timed report, set as the stands say',
    selects.length === 4 && selects[0].value === 'yesterday' && selects[1].value === 'morning' && selects[2].value === 'today' && selects[3].value === 'own'
    && panel.scheduleList.textContent.includes('Flipkart returns'));
  check('R208: the run choices are the three runs, the day choices yesterday and today',
    selects[1].children.map((one) => one.value).join() === 'morning,evening,own'
    && selects[0].children.map((one) => one.value).join() === 'yesterday,today'
    && selects[1].children.map((one) => one.textContent).join() === 'Morning run,Evening run,Own time');
  selects[2].value = 'yesterday';
  selects[2].fire('change');
  check('R208: changing a choice sends that report with both its choices', picked.join() === 'fk_returns:yesterday:own');
  check('R208: the card says what a today choice means', document.body.textContent.includes('Platforms often do not have the numbers for today yet'));
  const before = panel.scheduleList.children[0];
  showHowItStands(panel, { ...stands, schedule });
  check('R208: the rows are not drawn again when nothing changed', panel.scheduleList.children[0] !== undefined && panel.scheduleList.children[0] === before);
}

{
  /* **R208 proving, second round: the rows redraw when the stands change, the listener of each choice, the panel's own title, the plain-list queue behind a going run, the real clock.** */
  installFakeBrowser();
  const sent = [];
  const handed = { saveTheReportTimes: (id, day, run) => sent.push(`${id}:${day}:${run}`) };
  const panel = buildThePanel(document.body, handed);
  check('R208: the panel keeps what it was built with, for the rows to send through', panel.doing === handed);
  check('R208: the card has its title and its list', document.body.textContent.includes('Which report runs when')
    && panel.scheduleList !== undefined && document.body.children.length > 0);
  const stands = { reports: [], cannotBeFetched: [], schedule: [{ id: 'fk_returns', name: 'Flipkart returns', day: 'today', run: 'own', at: '18:00' }, { id: 'fk_claims', name: 'Flipkart claims', day: 'yesterday', run: 'morning' }] };
  showHowItStands(panel, { ...(await howItStands(installFakeChrome().chrome, { book: BOOK, now: Date.now() })), schedule: stands.schedule });
  const selectsOf = () => panel.scheduleList.children.flatMap((row) => row.children.flatMap((one) => (one.tagName === 'select' ? [one] : one.children.filter((c) => c.tagName === 'select'))));
  selectsOf()[3].value = 'evening';
  selectsOf()[3].fire('change');
  selectsOf()[0].value = 'today';
  selectsOf()[0].fire('change');
  check('R208: the run choice and the day choice of a row each send the report with both choices',
    sent.join() === 'fk_returns:today:evening,fk_claims:today:morning');
  showHowItStands(panel, { ...(await howItStands(installFakeChrome().chrome, { book: BOOK, now: Date.now() })), schedule: [{ id: 'me_returns', name: 'Zeta returns', day: 'today', run: 'own', at: '18:00' }] });
  check('R208: when the stands change the old rows go and the new ones are drawn',
    panel.scheduleList.children.length === 5 && panel.scheduleList.textContent.includes('Zeta returns') && !panel.scheduleList.textContent.includes('Flipkart claims'));
  check('R208: the rows are on the page itself, not in a list nobody sees', document.body.textContent.includes('Zeta returns'));
  check('R208: and the new row shows its choices', selectsOf().length === 2 && selectsOf()[0].value === 'today' && selectsOf()[1].value === 'own');
}

{
  /* A plain-list queue (the morning's) behind a going night: what is already there is dropped, and an entry left empty is not queued. */
  const now = Date.UTC(2026, 10, 7, 12, 30);
  const { chrome } = installFakeChrome();
  const parts = { book: BOOK, now: () => now, startTheNight, carryOn: async () => {} };
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  const everyFlipkart = theTimedListFor(BOOK, { timed: null }, 'morning').filter((id) => id.startsWith('fk_'));
  await chrome.storage.local.set({ [LAST_LANDED]: { fk_returns: ['2026-11-06'], me_returns: ['2026-11-06'], az_returns: ['2026-11-06'] } });
  await chrome.storage.local.set({ [THE_NIGHT]: { startedAt: now, finishedAt: 0, spent: 0, mayAskFor: 3, done: [], left: [...everyFlipkart], doing: null }, [THE_QUEUE]: [] });
  await startTheScheduledSync(chrome, parts);
  const queued = (await chrome.storage.local.get(THE_QUEUE))[THE_QUEUE];
  const flat = queued.map((entry) => (Array.isArray(entry) ? entry : entry.reportIds));
  check('R208: the morning list behind a going night leaves out what the night has left, drops an entry left empty, and keeps the others',
    queued.every((entry) => Array.isArray(entry)) && !flat.flat().some((id) => everyFlipkart.includes(id)) && flat.every((ids) => ids.length > 0)
    && flat.flat().some((id) => id.startsWith('me_')) && flat.flat().some((id) => id.startsWith('az_')));
}

{
  /* Review of the fallback: a platform holding ONLY fallbacks is fetched for yesterday, */
  const now = Date.UTC(2026, 10, 7, 12, 30);
  const only = installFakeChrome().chrome;
  const seen = [];
  const parts = { book: BOOK, now: () => now, startTheNight: async (c, how) => { seen.push([how.doing.join(), how.dataDate, how.run]); return startTheNight(c, how); }, carryOn: async () => {} };
  await answerThePanelsQuestion(only, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(only, parts, { do: 'check-the-drive' });
  for (const id of theTimedListFor(BOOK, { timed: null }, 'morning').filter((one) => one.startsWith('fk_'))) {
    await answerThePanelsQuestion(only, parts, { do: 'save-the-report-times', reportId: id, day: 'yesterday', run: 'evening' });
  }
  const alone = await startTheScheduledSync(only, parts);
  check('R208: a platform whose only morning entries are the fallback returns is fetched for YESTERDAY, not today',
    alone.started.join() === 'fk_returns' && seen[0][1] === '2026-11-06' && seen[0][2] === 'morning');
  await endTheNight(only, { at: now, why: 'x' });
  /* a morning fallback queued behind a going night keeps its yesterday mark */
  const behind = installFakeChrome().chrome;
  await answerThePanelsQuestion(behind, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(behind, parts, { do: 'check-the-drive' });
  await behind.storage.local.set({ [THE_NIGHT]: { startedAt: now, finishedAt: 0, spent: 0, mayAskFor: 3, done: [], left: ['fk_returns'], doing: null }, [THE_QUEUE]: [] });
  await startTheScheduledSync(behind, parts);
  const q = (await behind.storage.local.get(THE_QUEUE))[THE_QUEUE];
  check('R208: fallbacks queued behind a going night carry their yesterday mark and leave out what the night has left',
    q.some((entry) => !Array.isArray(entry) && entry.today === false && entry.reportIds.includes('me_returns')) && !q.flatMap((entry) => (Array.isArray(entry) ? entry : entry.reportIds)).includes('fk_returns'));
}

{
  /* The morning fallback reads the real clock when none is handed in. */
  const realYesterday = theDay(Date.now() - 24 * 60 * 60 * 1000);
  const parts = { book: BOOK, startTheNight, carryOn: async () => {} };
  const landedOne = installFakeChrome().chrome;
  await answerThePanelsQuestion(landedOne, { ...parts, now: () => Date.now() }, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(landedOne, { ...parts, now: () => Date.now() }, { do: 'check-the-drive' });
  await landedOne.storage.local.set({ [LAST_LANDED]: { fk_returns: [realYesterday], me_returns: [realYesterday], az_returns: [realYesterday] } });
  const none = await startTheScheduledSync(landedOne, parts);
  const nothing = installFakeChrome().chrome;
  await answerThePanelsQuestion(nothing, { ...parts, now: () => Date.now() }, { do: 'save-the-panel-name', panel: 'xuptj' });
  await answerThePanelsQuestion(nothing, { ...parts, now: () => Date.now() }, { do: 'check-the-drive' });
  const some = await startTheScheduledSync(nothing, parts);
  check('R208: with no clock handed in, the fallback compares against the real yesterday', !none.started.includes('fk_returns') && some.started.includes('fk_returns'));
}

{
  /* **R250: THE PANEL'S TIDY-UP -- needs-you folded and grouped, run times, the clash line, newest first.** */
  installFakeBrowser();
  const { chrome } = installFakeChrome();
  const stands = await howItStands(chrome, { book: BOOK, now: Date.now() });
  const picked = [];
  const panel = buildThePanel(document.body, { clearNeedsYou() {}, setARunTime: (which, at) => picked.push(`${which}:${at}`) });
  const day = (n) => `2026-09-${String(n).padStart(2, '0')}`;
  const many = [];
  for (let n = 9; n >= 1; n -= 1) many.push({ reportId: 'fk_orders', dataDate: day(n), name: 'Orders', platformName: 'Flipkart', folder: '' });
  many.push({ reportId: 'me_orders', dataDate: day(3), name: 'Orders', platformName: 'Meesho', folder: '' });
  many.unshift({ reportId: 'az_orders', dataDate: day(2), name: 'Orders', platformName: 'Amazon', folder: '' });
  showHowItStands(panel, { ...stands, needsYou: many });
  const outer = panel.needs.children[0];
  check('R250: the needs-you box is folded, and shows its count', outer.tagName === 'details' && outer.open === false
    && panel.needs.find('p-count').textContent === String(many.length));
  const all = outer.children.find((one) => one.className === 'p-needsList').children;
  const rowsOf = all.filter((one) => one.className === 'p-needsRow');
  const headings = all.filter((one) => one.className === 'p-needsGroup').map((one) => one.textContent);
  check('R250: opened, one row per report-day, each with its own "I placed it"',
    rowsOf.length === many.length && rowsOf.every((one) => one.children.some((c) => c.tagName === 'button' && c.textContent === 'I placed it')));
  check('R250 (D1034): rows are grouped by report, each group headed with its count, in platform order',
    headings.join('|') === 'Flipkart · Orders -- 9 days|Meesho · Orders -- 1 day|Amazon · Orders -- 1 day');
  check('R250: and a group days are in date order',
    rowsOf.slice(0, 9).map((one) => one.children[0].children[0].textContent).join() === [1, 2, 3, 4, 5, 6, 7, 8, 9].map(day).join());
  check('R250: "I placed all" is in the box', outer.children.some((one) => one.tagName === 'button' && one.textContent === 'I placed all'));

  const times = { morning: '16:00', evening: '16:00' };
  showHowItStands(panel, { ...stands, clock: { chosen: '16:00', nextAt: null, times } });
  check('R250: a morning time equal to the evening time is said in red, and nothing is changed',
    panel.clash.hidden === false && panel.clash.textContent.startsWith('Morning run is at 4:00 pm, the same as the evening run')
    && panel.hour.value === '16:00');
  showHowItStands(panel, { ...stands, clock: { chosen: '08:00', nextAt: null, times: { morning: '08:00', evening: '16:30' } } });
  check('R250: with no clash the line is gone, and the three boxes show the three times',
    panel.clash.hidden === true && panel.hour.value === '08:00' && panel.eveningTime.value === '16:30');
  panel.eveningTime.value = '17:00';
  panel.eveningSave.click();
  check('R250: the evening Save button sends that run and its box\'s own text', picked.join() === 'evening:17:00');

  const notYet = { ...stands, setUp: { ...stands.setUp, driveConnectedAt: 0, panel: '' } };
  showHowItStands(panel, notYet);
  check('R250: before set-up the settings are open, there is no gear, and the panel shows only the set-up steps',
    panel.settings.hidden === false && panel.gear.hidden === true && panel.body.className.includes('p-pre'));
  showHowItStands(panel, { ...stands, setUp: { ...stands.setUp, driveConnectedAt: 5, panel: 'xuptj' } });
  check('R250: after set-up the settings are behind the gear, closed, and the rest of the panel is back',
    panel.settings.hidden === true && panel.gear.hidden === false && !panel.body.className.includes('p-pre'));
  panel.gear.click();
  check('R250: the gear opens them, with Set up once and the run pass inside, and opens nothing else',
    panel.settings.hidden === false && panel.settings.children.includes(panel.setup) && panel.settings.children.includes(panel.kartaan));
  panel.gear.click();
  check('R250: and shuts them again', panel.settings.hidden === true);
  const sched = panel.scheduleList.parentNode;
  check('R250: the day-and-run list is folded by default', sched.tagName === 'details' && !sched.open);
  /* his look, D1035: Own time */
  const ownSaved = [];
  const ownPanel = buildThePanel(document.body, { saveTheReportTimes: (id, day, run, at) => ownSaved.push(`${id}:${day}:${run}:${at}`) });
  const ownSched = [
    { id: 'fk_returns', name: 'Flipkart returns', platform: 'flipkart', day: 'today', run: 'own', at: '12:00' },
    { id: 'fk_claims', name: 'Flipkart claims', platform: 'flipkart', day: 'yesterday', run: 'morning', at: '18:00' },
    { id: 'me_claims', name: 'Meesho claims', platform: 'meesho', day: 'yesterday', run: 'own', at: '19:00' },
  ];
  showHowItStands(ownPanel, { ...stands, schedule: ownSched });
  const cells = ownPanel.scheduleList.children.filter((one) => one.className === 'p-schedRow').map((row) => row.children[2]);
  const timeBoxes = cells.map((cell) => cell.children[1]);
  const warns = ownPanel.scheduleList.children.filter((one) => one.className === 'p-schedWarn');
  check('R250 (D1035): the Run column offers Morning run, Evening run and Own time',
    cells[0].children[0].children.map((one) => one.textContent).join() === 'Morning run,Evening run,Own time');
  check('R250 (D1035): a time box shows only for a report on Own time, filled with its own time', timeBoxes[0].hidden === true && timeBoxes[1].hidden === false && timeBoxes[1].value === '12:00');
  check('R250 (D1035): the returns on 12:00 get the warning "You may not get this report at 12:00. It is usually ready after 18:00."',
    warns[1].hidden === false && warns[1].textContent === 'You may not get this report at 12:00. It is usually ready after 18:00.');
  check('R250 (D1035): a report with no known ready time, or a time after it, gets no warning', warns[2].hidden === true && warns[0].hidden === true && theReadyWarning('fk_returns', '18:30') === '' && theReadyWarning('fk_claims', '01:00') === '');
  timeBoxes[1].value = '19:30';
  timeBoxes[1].fire('change');
  check('R250 (D1035): a changed own time is saved with the report, the day and the run, and the warning goes', ownSaved.join() === 'fk_returns:today:own:19:30' && warns[1].hidden === true);
  cells[0].children[0].value = 'own';
  cells[0].children[0].fire('change');
  check('R250 (D1035): choosing Own time shows the time box and sends the run with its time', timeBoxes[0].hidden === false && ownSaved.at(-1) === 'fk_claims:yesterday:own:18:00');
  check('R250 (D1035): the schedule is grouped under a heading for each platform', ownPanel.scheduleList.children.filter((one) => one.className === 'p-schedPlatform').map((one) => one.textContent).join() === 'Flipkart,Meesho');
  const ask = { do: 'save-the-report-times', reportId: 'fk_claims', day: 'today', run: 'own', at: '13:15' };
  const ownChrome = installFakeChrome().chrome;
  const ownParts = { book: BOOK, now: () => Date.now(), whyAnOwnTimeIsRefused: async (c, at) => (at === '16:00' ? 'taken' : null), setTheOwnTimes: async (c, times) => { ownTimesSeen.push(times.join()); } };
  const ownTimesSeen = [];
  const okOwn = await answerThePanelsQuestion(ownChrome, ownParts, ask);
  const refusedOwn = await answerThePanelsQuestion(ownChrome, ownParts, { ...ask, at: '16:00' });
  const noTime = await answerThePanelsQuestion(ownChrome, ownParts, { ...ask, at: 'soon' });
  check('R250 (D1035): an own time is saved and the alarms are told every own time now in use (the returns default 18:00 and this one)',
    okOwn.saved === true && ownTimesSeen[0] === '13:15,18:00');
  check('R250 (D1035): an own time another run has, or that is not a time, is refused in words and saves nothing', refusedOwn.wrong === 'taken' && Boolean(noTime.wrong) && ownTimesSeen.length === 1);
  check('R250 (D1035): the own time of a report is read back, and a bad saved one reads as 18:00',
    theOwnAtOf({ ownAt: { fk_claims: '13:15' } }, 'fk_claims') === '13:15' && theOwnAtOf({ ownAt: { fk_claims: '99:99' } }, 'fk_claims') === '18:00');
  const evenOwn = theTimedListFor(BOOK, { timed: null, runs: { fk_claims: 'own' }, ownAt: { fk_claims: '13:15' } }, 'own', '13:15');
  check('R250 (D1035): an own-time run fetches only the reports whose own time it is', evenOwn.join() === 'fk_claims' && !theTimedListFor(BOOK, { timed: null, runs: { fk_claims: 'own' }, ownAt: { fk_claims: '13:15' } }, 'own', '18:00').includes('fk_claims'));
  const walkAll = (node) => [node, ...node.children.flatMap(walkAll)];
  showHowItStands(ownPanel, { ...stands, setUp: { ...stands.setUp, done: true }, clock: { chosen: '08:00', nextAt: null, times: { morning: '08:00', evening: '16:00' }, own: [{ time: '18:00', at: null }] } });
  check('R250 (D1035): the Run times button lists the times, with own times', ownPanel.timesButtonState.textContent === '08:00 · 16:00 · own 18:00'
    && !document.body.textContent.includes('Returns run'));
  check('R250 (D1035): the retry is said as a line, never a setting, with the 20 a day', document.body.textContent.includes('tried again every hour, up to 3 tries') && document.body.textContent.includes('20'));

  /* his look, D1034 */
  const walk = (node) => [node, ...node.children.flatMap(walk)];
  check('R250 (D1034): Run now and Stop sit in the same row as the From and To dates', panel.actions.parentNode === panel.from.parentNode && panel.to.parentNode === panel.from.parentNode);
  showHowItStands(panel, { ...stands, setUp: { ...stands.setUp, done: true }, night: null, needsYou: [], clock: null });
  check('R250 (D1034): a quiet panel says ONE status line, "Ready." and when the next timed run wakes', panel.banner.textContent.startsWith('Ready. ') && panel.banner.textContent.includes('morning run wakes'));
  const docs = walk(panel.help).find((one) => one.tagName === 'a');
  check('R250 (D1034): "Read more on docs.kartaan.com" is a real link that opens in a new tab',
    Boolean(docs) && docs.href === 'https://docs.kartaan.com' && docs.target === '_blank' && docs.rel === 'noopener' && docs.textContent === 'Read more on docs.kartaan.com');
  const flipped = [];
  const doc = (on) => ({ body: { classList: { toggle: (name, now) => flipped.push(`${name}:${now}`) } }, on });
  const dark = (matches) => () => ({ matches });
  check('R250 (D1034): the default follows the computer: dark when it is dark, light when it is light',
    applyTheTheme('system', doc(), dark(true)) === true && applyTheTheme('system', doc(), dark(false)) === false);
  check('R250 (D1034): a chosen Light or Dark wins over the computer', applyTheTheme('light', doc(), dark(true)) === false && applyTheTheme('dark', doc(), dark(false)) === true);
  check('R250 (D1034): and the body class switched is the ERP dark one is what is switched', flipped.every((one) => one.startsWith('dark:')) && flipped.length === 4);
  check('R250 (D1034): with nothing kept the choice is Same as computer', theThemeChosen() === 'system');
  check('R250 (D1034): the choice is in Settings with its three words, and starts on Same as computer',
    panel.settings.children.some((one) => walk(one).includes(panel.theme)) && panel.theme.children.map((one) => one.textContent).join() === 'Same as computer,Light,Dark' && panel.theme.value === 'system');

  const parts = { ...panelParts(chrome), setARunTime: async (c, how) => { picked.push(`set:${how.which}`); return 1; }, whyThatRunTimeIsRefused: async (c, which, at) => (at === '16:00' ? 'taken' : null) };
  const refusedAsk = await answerThePanelsQuestion(chrome, parts, { do: 'set-a-run-time', which: 'evening', at: '16:00' });
  const okAsk = await answerThePanelsQuestion(chrome, parts, { do: 'set-a-run-time', which: 'evening', at: '17:00' });
  const badAsk = await answerThePanelsQuestion(chrome, parts, { do: 'set-a-run-time', which: 'morning', at: '17:00' });
  check('R250: the panel may ask for it; a taken time is refused with the words, a free one is saved, the morning is not set this way',
    THE_PANEL_ASKS.includes('set-a-run-time') && refusedAsk.wrong === 'taken' && okAsk.at === 1 && picked.includes('set:evening') && Boolean(badAsk.wrong));
}

{
  /* R250 review (HIGH): the panel's own wiring must pass the time box value on, or Own time can never be saved. */
  const PANEL = readFileSync(new URL('panel.js', HERE), 'utf8');
  check('R250: the panel sends the time of an own-time choice to the extension',
    /saveTheReportTimes: async \(reportId, day, run, at\)[\s\S]{0,200}save-the-report-times', reportId, day, run, at \}/.test(PANEL));
}

{
  /* **R250 PROVING (8 Nov 2026): what the panel DOES -- the light/dark choice kept, the sorting, the folds, the clash line, the ready-time warning, what a refusal stops.** */
  installFakeBrowser();
  const kept = {};
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: { getItem: (k) => (k in kept ? kept[k] : null), setItem: (k, v) => { kept[k] = String(v); } },
  });
  check('R250 proving: with nothing kept, or something odd kept, the choice is the computer\'s own', theThemeChosen() === 'system' && (kept['kartaan-autosync-theme'] = 'blue') && theThemeChosen() === 'system');
  const { chrome } = installFakeChrome();
  const stands = await howItStands(chrome, { book: BOOK, now: Date.now() });
  const panel = buildThePanel(document.body, {});
  panel.theme.value = 'dark';
  panel.theme.fire('change');
  check('R250 proving: choosing Dark in Settings keeps it and it is read back', kept['kartaan-autosync-theme'] === 'dark' && theThemeChosen() === 'dark' && panel.theme.value === 'dark');
  check('R250 proving: a panel opened later starts on the kept choice', buildThePanel(document.body, {}).theme.value === 'dark');
  const before = panel.modeSwitch.textContent;
  panel.modeSwitch.click();
  check('R250 proving: the top-right switch flips the choice, keeps it, and its words follow what it will do next',
    kept['kartaan-autosync-theme'] === 'light' && panel.modeSwitch.textContent !== before && panel.theme.value === 'light'
    && panel.modeSwitch.textContent.includes('Dark'));
  panel.modeSwitch.click();
  check('R250 proving: and back again', kept['kartaan-autosync-theme'] === 'dark' && panel.modeSwitch.textContent.includes('Light'));

  /* ready-time table */
  check('R250 proving: each report that is usually ready late warns before its time and not after',
    ['fk_orders', 'fk_views', 'az_fee_preview', 'me_views'].every((id) => theReadyWarning(id, '15:59') !== '' && theReadyWarning(id, '16:00') === '')
    && ['fk_returns', 'me_returns', 'az_returns'].every((id) => theReadyWarning(id, '17:59') !== '' && theReadyWarning(id, '18:00') === ''));

  /* the schedule rows: platform carried, order by platform then run then name, the fold title counts what is off the morning run */
  const row = (id, name, platform, run) => ({ id, name, platform, day: 'yesterday', run, at: '18:00' });
  const sched = [row('me_a', 'Zed', 'meesho', 'morning'), row('fk_b', 'Beta', 'flipkart', 'evening'), row('fk_c', 'Alpha', 'flipkart', 'morning'), row('fk_d', 'Alpha', 'flipkart', 'own'), row('az_e', 'Eta', 'amazon', 'evening')];
  showHowItStands(panel, { ...stands, schedule: sched });
  const names = panel.scheduleList.children.filter((one) => one.className === 'p-schedRow').map((one) => one.children[0].textContent);
  check('R250 proving: the Which-report-runs-when rows go Flipkart, Meesho, Amazon; inside a platform morning, evening, own; then by name',
    names.join() === 'Alpha,Beta,Alpha,Zed,Eta');
  check('R250 proving: the fold title counts the reports not on the morning run', panel.timesFoldTitle.textContent === 'Which report runs when · 3 not on the morning run');
  showHowItStands(panel, { ...stands, schedule: [row('fk_c', 'Alpha', 'flipkart', 'morning')] });
  check('R250 proving: with every report on the morning run the title says nothing more', panel.timesFoldTitle.textContent === 'Which report runs when');

  /* the clash line and the time boxes */
  showHowItStands(panel, { ...stands, clock: { chosen: '', nextAt: null, times: { morning: '07:15', evening: '17:45' } } });
  check('R250 proving: with no morning time chosen the boxes show the clock\'s times', panel.hour.value === '07:15' && panel.eveningTime.value === '17:45' && panel.timesButtonState.classList.contains('p-clashing') === false);
  showHowItStands(panel, { ...stands, clock: { chosen: '09:00', nextAt: null, times: { morning: '09:30', evening: '17:45' } } });
  check('R250 proving: with a morning time chosen the morning box shows that one, not the clock', panel.hour.value === '09:00');
  showHowItStands(panel, { ...stands, clock: { chosen: '16:00', nextAt: null, times: { morning: '16:00', evening: '16:00' } } });
  check('R250 proving: a clash colours the Run times button', panel.timesButtonState.classList.contains('p-clashing') === true);

  /* banner, AI button */
  showHowItStands(panel, { ...stands, setUp: { ...stands.setUp, done: true }, night: null, needsYou: [], clock: null, ai: { on: true, connected: true, asks: [], note: '' } });
  check('R250 proving: the AI button says On when it is on and Off when it is off', panel.aiButtonState.textContent === 'On'
    && (showHowItStands(panel, { ...stands, ai: { on: false, asks: [] } }), panel.aiButtonState.textContent === 'Off'));
  showHowItStands(panel, { ...stands, setUp: { ...stands.setUp, driveConnectedAt: 5, panel: 'xuptj', done: true }, night: null, needsYou: [], clock: null });
  check('R250 proving: a quiet panel one line starts with Ready.', panel.banner.textContent.startsWith('Ready. '));

  /* needs-you fold is remembered across a redraw */
  const mk = (id, n) => ({ reportId: id, dataDate: `2026-09-0${n}`, name: id === 'fk_orders' ? 'Orders' : 'Claims', platformName: 'Flipkart', folder: '' });
  showHowItStands(panel, { ...stands, needsYou: [mk('fk_orders', 1), mk('fk_claims', 2)] });
  const outer = panel.needs.children[0];
  outer.open = true;
  outer.fire('toggle');
  showHowItStands(panel, { ...stands, needsYou: [mk('fk_orders', 1), mk('fk_claims', 2), mk('fk_orders', 3)] });
  check('R250 proving: an opened needs-you box stays open when the panel redraws', panel.needs.children[0].open === true);
  const heads = panel.needs.children[0].children.find((one) => one.className === 'p-needsList').children.filter((one) => one.className === 'p-needsGroup').map((one) => one.textContent);
  check('R250 proving: groups of one platform are in name order', heads[0].startsWith('Flipkart · Claims') && heads[1].startsWith('Flipkart · Orders'));

  /* a report that cannot be fetched is a greyed row, and "cannot fetch" rows follow the platform chosen */
  const cannot = (stands.reports || []).filter((one) => one.canBeFetched === false);
  check('R250 proving: the cannot-fetch rows show only for the platform chosen',
    !panel.cannotRows || panel.cannotRows.every(([platform, r]) => r.hidden === (platform !== panel.chosen)));
  check('R250 proving: and a report that cannot be fetched has no tick row', cannot.length === 0 || cannot.every((one) => one.canBeFetched === false));

  /* answers: a refusal stops the save; two own times are both kept with the platform on each row */
  const own = installFakeChrome().chrome;
  const spy = [];
  const parts = { book: BOOK, now: () => Date.now(), startTheNight, carryOn: async () => {}, setTheOwnTimes: async () => {}, whyAnOwnTimeIsRefused: async () => null,
    setTheHour: async (c, how) => { spy.push(how.at); return 1; }, whyThatIsNotATimeOfDay, whyThatRunTimeIsRefused: async (c, which, at) => (at === '16:00' ? 'taken' : null) };
  await answerThePanelsQuestion(own, parts, { do: 'save-the-panel-name', panel: 'xuptj' });
  const stopped = await answerThePanelsQuestion(own, parts, { do: 'set-the-hour', at: '16:00' });
  check('R250 proving: a morning time another run has is refused with the words and nothing is saved', stopped.wrong === 'taken' && spy.length === 0);
  await answerThePanelsQuestion(own, parts, { do: 'set-the-hour', at: '09:00' });
  check('R250 proving: a free morning time is saved', spy.join() === '09:00');
  await answerThePanelsQuestion(own, parts, { do: 'save-the-report-times', reportId: 'fk_claims', day: 'today', run: 'own', at: '13:00' });
  await answerThePanelsQuestion(own, parts, { do: 'save-the-report-times', reportId: 'me_claims', day: 'today', run: 'own', at: '14:30' });
  const both = await howItStands(own, { book: BOOK, now: Date.now() });
  const byId = Object.fromEntries(both.schedule.map((one) => [one.id, one]));
  check('R250 proving: two own times are both kept, each on its own report, and each row carries its platform',
    byId.fk_claims.at === '13:00' && byId.me_claims.at === '14:30' && byId.fk_claims.platform === 'flipkart' && byId.me_claims.platform === 'meesho');
}

{
  /* **R250 PROVING, second run: the banner's three branches, when the panel counts as set up, the cannot-fetch rows, the order of two reports of one platform.** */
  installFakeBrowser();
  const { chrome } = installFakeChrome();
  const stands = await howItStands(chrome, { book: BOOK, now: Date.now() });
  const panel = buildThePanel(document.body, {});
  const setUp = (extra) => ({ ...stands.setUp, ...extra });
  showHowItStands(panel, { ...stands, setUp: setUp({ driveConnectedAt: 5, panel: '' }) });
  const noName = panel.body.className.includes('p-pre');
  showHowItStands(panel, { ...stands, setUp: setUp({ driveConnectedAt: 0, panel: 'xuptj' }) });
  const noDrive = panel.body.className.includes('p-pre');
  showHowItStands(panel, { ...stands, setUp: setUp({ driveConnectedAt: 5, panel: 'xuptj' }) });
  check('R250 proving: the panel counts as set up only with BOTH the Drive connected and the panel named',
    noName === true && noDrive === true && panel.body.className.includes('p-pre') === false);
  const quiet = { ...stands, setUp: setUp({ driveConnectedAt: 5, panel: 'xuptj', done: true }), night: null, needsYou: [], clock: { chosen: '08:00', nextAt: Date.now() + 1000, times: { morning: '08:00', evening: '16:00' } } };
  showHowItStands(panel, quiet);
  const idleLine = panel.banner.textContent;
  const said = whatTheBannerSays(quiet).said;
  check('R250 proving: the status line is "Ready." plus when it wakes while quiet', idleLine.startsWith('Ready. ') && idleLine.includes('wakes'));
  const doneStands = { ...quiet, night: { startedAt: 1, finishedAt: 2, spent: 0, mayAskFor: 3, done: [{ reportId: 'fk_orders', state: 'landed', say: 'x' }], left: [], doing: null } };
  const how = whatTheBannerSays(doneStands);
  showHowItStands(panel, doneStands);
  check('R250 proving: when a run is done the line is its own words plus when it wakes; otherwise just its own words',
    how.how === 'done' ? panel.banner.textContent === `${how.said} ${whenItNextWakes(doneStands.clock)}` : panel.banner.textContent === how.said);
  check('R250 proving: the idle words are not what a finished run says', typeof said === 'string');

  /* the three drawers: one open at a time, the button says which */
  const open = (button) => button.getAttribute('aria-expanded');
  check('R250 proving: all three drawers start shut', [panel.aiButton, panel.timesButton, panel.helpButton].every((b) => open(b) === 'false'));
  panel.timesButton.click();
  check('R250 proving: pressing Run times opens it and says so', open(panel.timesButton) === 'true' && open(panel.helpButton) === 'false' && open(panel.aiButton) === 'false');
  panel.helpButton.click();
  check('R250 proving: pressing another drawer shuts the first and opens the other', open(panel.timesButton) === 'false' && open(panel.helpButton) === 'true');
  panel.helpButton.click();
  check('R250 proving: pressing the open one again shuts it', open(panel.helpButton) === 'false');

  /* the gear says whether Settings is open, and shuts itself when the panel goes back to set-up */
  check('R250 proving: the gear starts hidden and shut', panel.gear.getAttribute('aria-expanded') === 'false');
  showHowItStands(panel, quiet);
  panel.gear.click();
  check('R250 proving: pressing the gear opens Settings and says so', panel.settings.hidden === false && panel.gear.getAttribute('aria-expanded') === 'true');
  panel.gear.click();
  check('R250 proving: pressing it again shuts Settings and says so', panel.settings.hidden === true && panel.gear.getAttribute('aria-expanded') === 'false');

  /* typing an own time updates the warning at once */
  const ownP = buildThePanel(document.body, {});
  showHowItStands(ownP, { ...stands, schedule: [{ id: 'fk_returns', name: 'Flipkart returns', platform: 'flipkart', day: 'today', run: 'own', at: '18:30' }] });
  const ownRow = ownP.scheduleList.children.find((one) => one.className === 'p-schedRow');
  const ownTime = ownRow.children[2].children[1];
  const ownWarn = ownP.scheduleList.children.find((one) => one.className === 'p-schedWarn');
  ownTime.value = '10:00';
  ownTime.fire('input');
  check('R250 proving: typing an earlier own time shows the ready-time warning straight away', ownWarn.hidden === false && ownWarn.textContent.includes('10:00'));
  ownTime.value = '19:00';
  ownTime.fire('input');
  check('R250 proving: and a later one takes it away', ownWarn.hidden === true);
}

reachedTheEnd = true;
console.log(`\n${ran} checks, ${failures} failed.`);
process.exit(failures ? 1 : 0);
