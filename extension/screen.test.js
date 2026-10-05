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
  A_DAYS_ALLOWANCE, KEPT_FOR_HIS_OWN_RUNS, THE_NIGHT, carryTheNightOn, endTheNight, howTheNightWent, oneWasAskedFor,
  startTheNight, thatOneIsBeingTried, theNight,
} from './nightly.js';
import { hasNotFinished, theWalk } from './walk.js';
import {
  CALLED,
  THE_NIGHTS,
  THE_PANEL_ASKS,
  THROUGH_THE_BROWSER,
  alreadyCarriedOn,
  answerThePanelsQuestion,
  askingFirst,
  markCarriedOn,
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
  whenItNextWakes,
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
  check('the default timed list leaves out fk_keywords (his decision E)',
    !theTimedList(BOOK, { timed: null }).includes('fk_keywords')
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
    && fresh.timed.meesho === every('meesho').length && every('meesho').length > 0);
  check('and the panel says it: "The timed sync will fetch: N reports (Flipkart x, Meesho y)"',
    Boolean(fresh.timed) && fresh.timed.said === `The timed sync will fetch: `
      + `${every('flipkart').length + every('meesho').length} reports `
      + `(Flipkart ${every('flipkart').length}, Meesho ${every('meesho').length})`);
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-ticks', reportIds: ['fk_claims'] });
  const after = await howItStands(chrome, { book: BOOK, now: Date.UTC(2026, 8, 16, 3, 0) });
  check('Run now ticks do not change the timed list',
    Boolean(after.timed) && after.timed.said === (fresh.timed && fresh.timed.said));
  const first = await startTheScheduledSync(chrome, parts);
  check('and the timed sync runs every Flipkart report, not the one tick',
    Boolean(first.started) && [...first.started].sort().join() === [...every('flipkart')].sort().join());
  check('and the timed sync keeps a few of the twenty for his own runs, so it may spend less than all of them',
    (await theNight(chrome)).mayAskFor === A_DAYS_ALLOWANCE - KEPT_FOR_HIS_OWN_RUNS);
  await endTheNight(chrome, { at: Date.UTC(2026, 8, 16, 3, 30), why: 'Every report was reached.' });
  const second = await startTheNextPlatform(chrome, parts);
  check('then every Meesho report, though none was ticked',
    Boolean(second.started) && [...second.started].sort().join() === [...every('meesho')].sort().join());
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
  MANIFEST.permissions.join(',') === 'alarms,storage,downloads,scripting,identity,notifications');
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
check('Amazon is not fetched through the browser at all',
  !THROUGH_THE_BROWSER.includes('amazon') && CALLED.amazon === 'Amazon');

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
  /* **THE KEYWORDS WERE THE LAST REPORT THIS DOOR COULD NOT FETCH, AND SINCE
   * 2026-09-15 THEY CAN BE**, so they are allowed like any other. */
  check('the keywords, now built, can be started like any other report',
    no({ reportIds: ['fk_keywords'] }) === null);
  /* **AND `me_views` IS NO LONGER ONE OF THEM, which is the point of the change
   * on 2026-09-11.** The door learned to read a number off a card and to add a
   * row to a running list, so the one report Meesho sells no export of became
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
  check('Amazon is on the page, and says it is not fetched here',
    stands.platforms.some((one) => one.id === 'amazon' && one.throughTheBrowser === false));
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
  check('so every report can be ticked',
    stands.reports.filter((one) => !one.canBeFetched).length === 0);
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
      === BOOK.reports.filter((one) => THROUGH_THE_BROWSER.includes(one.platform)).length);
  /* Two since 2026-09-14: returns left the Reports Centre. */
  check('the two that cost the seller something are marked as costing it',
    stands.reports.filter((one) => one.spends).map((one) => one.id).join(',')
      === 'fk_orders,fk_payments');
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
{
  const banner = whatTheBannerSays({
    setUp: { done: true },
    night: { finishedAt: 2000, doing: null, left: [], done: [{ state: 'landed' }] },
    needsYou: [{ reportId: 'fk_orders', dataDate: '2026-09-13' }],
  });
  check('A DAY THAT NEEDS THE SELLER IS NAMED IN THE BANNER, even after a clean run',
    banner.how === 'wrong' && banner.said.includes('fk_orders for 2026-09-13')
      && banner.said.includes('by hand'));
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
  check('the default hour is in the middle of the night, when nobody is watching',
    UNTIL_A_SELLER_CHOOSES.hour >= 0 && UNTIL_A_SELLER_CHOOSES.hour <= 5);
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
  const say = (asked) => answerThePanelsQuestion(chrome, panelParts(chrome, held), asked);
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
    whenItNextWakes(told.stands.clock).startsWith('Next wakes'));
  check('an hour saved with no clock behind it is called out, not shown as fine',
    whenItNextWakes({ chosen: '03:45', nextAt: null }).includes('nothing will start by itself'));
  check('and an hour nobody ever chose says what happens instead',
    whenItNextWakes(null).includes('half past two'));
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
    === stands.reports.filter((one) => one.fetchedBy).map((one) => one.id).join(','));
  check('what cannot be fetched is on the page with its reason',
    parts.cannot.children.length === 1);
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
  check('the setup screen goes when both halves are done', parts.setup.hidden === true);
  check('and Run now comes on', parts.runNow.disabled === false);

  /* **A61, JOB 5b: EVERYTHING STARTS TICKED, and he unticks it all to run one
   * report** -- his way since "make it like Rumee". The checks below then run from
   * nothing ticked, as they always have. */
  check('5b: the panel opens with every report ticked, and the button says Untick all',
    whatIsTicked(parts).length > 0 && parts.selectAll.textContent === 'Untick all');
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
    parts.platformTicks.size === 2
    && parts.platformTicks.get('flipkart').textContent === 'Tick all Flipkart'
    && parts.platformTicks.get('meesho').textContent === 'Tick all Meesho');
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

reachedTheEnd = true;
console.log(`\n${ran} checks, ${failures} failed.`);
process.exit(failures ? 1 : 0);
