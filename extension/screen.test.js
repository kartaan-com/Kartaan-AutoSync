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
import {
  A_DAYS_ALLOWANCE, THE_NIGHT, endTheNight, howTheNightWent, oneWasAskedFor, startTheNight,
  thatOneIsBeingTried, theNight,
} from './nightly.js';
import {
  CALLED,
  THE_NIGHTS,
  THE_PANEL_ASKS,
  THROUGH_THE_BROWSER,
  answerThePanelsQuestion,
  askedForToday,
  buildThePanel,
  howItStands,
  howManyItMaySpend,
  inWordsWhen,
  rememberTheNight,
  saySomething,
  showHowItStands,
  theDay,
  theDayToFetch,
  theNights,
  thePlatformOf,
  thePlatformOfTheNight,
  theSetup,
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

  check('a portal page running our own content script is NOT answered',
    listen({ do: 'run-now', reportIds: ['fk_orders'] }, {
      id: chrome.runtime.id,
      url: 'https://seller.flipkart.com/index.html#dashboard',
      tab: { id: 7 },
    }) === null);

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
    asked.length === 3 && asked.every((one) => one === 'how-it-stands'));
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
  MANIFEST.permissions.join(',') === 'alarms,storage,downloads,scripting,identity');
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
  const meesho = whereToStartFrom(BOOK, ['me_orders']);
  const flipkart = whereToStartFrom(BOOK, ['fk_orders']);
  check('a Meesho night starts at the seller\'s own portal and nowhere deeper',
    meesho === 'https://supplier.meesho.com');
  check('a Flipkart night starts at the seller\'s own portal and nowhere deeper',
    flipkart === 'https://seller.flipkart.com');
  /* **AND THE STARTING PAGE IS A PAGE OUR OWN HALF RUNS ON.** The walk is picked
   * up by the content script, and the content script runs only where the
   * manifest says. A starting page outside those two is a walk that begins on a
   * page nothing is listening in, and it would stall for ever, at night. */
  const where = MANIFEST.content_scripts[0].matches.map((one) => one.replace('/*', ''));
  check('and it is a page the content script actually runs on',
    where.includes(meesho) && where.includes(flipkart));
  check('a report with no recipe says nowhere rather than guessing',
    whereToStartFrom(BOOK, ['me_views']) === '');
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
  check('a report this door cannot fetch at all is refused by name',
    (no({ reportIds: ['me_views'] }) || '').includes('me_views'));
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
  const lateLastNight = new Date(2026, 8, 8, 23, 55).getTime();
  const earlyToday = new Date(2026, 8, 9, 0, 10).getTime();
  await startTheNight(chrome, {
    doing: ['fk_orders', 'fk_returns'], mayAskFor: 4, at: lateLastNight,
    openAt: 'https://seller.flipkart.com',
  });
  await oneWasAskedFor(chrome, { at: lateLastNight });
  await oneWasAskedFor(chrome, { at: earlyToday });
  await oneWasAskedFor(chrome, { at: earlyToday });
  const night = await theNight(chrome);
  check('every request is stamped with the day it was actually spent on',
    night.spentOn['2026-09-08'] === 1 && night.spentOn['2026-09-09'] === 2);
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
    led['2026-09-08'] === 1 && led['2026-09-09'] === 2);
}

  check('a run may spend only what is left of the day',
    howManyItMaySpend(BOOK, {
      reportIds: ['fk_orders', 'fk_returns', 'fk_payments'],
      kept: { flipkartAskedOn: { [today]: 18 }, byPlatform: {}, filedNight: 0 },
      night: null,
    }) === 2);
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

  /* **THE FIVE THAT CANNOT BE FETCHED ARE NAMED WITH THEIR REASONS.** They are
   * written down in `autosync/recipes.py` as `NOT_YET_A_RECIPE` and until now
   * reached nobody at all. */
  check('every report this door cannot fetch is on the page',
    stands.cannotBeFetched.length === 5);
  check('and each one carries the reason written down in the Python',
    stands.cannotBeFetched.every((one) => one.why.length > 40));
  check('the reasons are the Python\'s own words, not words invented here',
    stands.cannotBeFetched.every((one) => one.why === BOOK.notYetARecipe[one.id]));
  check('a report that cannot be fetched cannot be ticked either',
    stands.reports.filter((one) => !one.canBeFetched).length === 5);
  check('and every report that is declared is on the page, fetchable or not',
    stands.reports.length
      === BOOK.reports.filter((one) => THROUGH_THE_BROWSER.includes(one.platform)).length);
  check('the three that cost the seller something are marked as costing it',
    stands.reports.filter((one) => one.spends).map((one) => one.id).join(',')
      === 'fk_orders,fk_payments,fk_returns');
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
  check('the night is allowed exactly the one Flipkart request it needs',
    night.mayAskFor === 1);
  check('and it fetches yesterday, because nothing said otherwise',
    night.dataDate === theDayToFetch(1000));
  check('and it starts at the seller\'s own Flipkart portal',
    night.openAt === 'https://seller.flipkart.com');
  check('the night is moved on the moment it is started, not two minutes later',
    held.carriedOn === 1);

  const again = await say({ do: 'run-now', reportIds: ['fk_views'] });
  check('a second run while one is going is refused', (again.wrong || '').includes('already'));
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
  check('the five that cannot be fetched cannot be ticked',
    [...parts.boxes.values()].filter((one) => one.disabled).length === 5);
  check('what cannot be fetched is on the page with its reason',
    parts.cannot.children.length === 5);
  check('the log says no night has been run rather than nothing at all',
    parts.log.textContent.includes('No night has been run'));

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
  check('Tick all ticks everything that can be fetched',
    whatIsTicked(parts).length === stands.reports.filter((one) => one.canBeFetched).length);
  parts.selectAll.click();
  check('and pressing it again unticks them', whatIsTicked(parts).length === 0);

  /* **A REBUILT LIST CLEARS WHAT WAS TICKED, and only the boxes used to be
   * cleared.** `ticked` is exactly what Run now sends, so a rebuild that left
   * stale ids in it was a live path to a run for a report nobody could see.
   * Found by an independent reviewer, 2026-09-09. */
  parts.boxes.get('fk_views').checked = true;
  parts.boxes.get('fk_views').dispatchEvent({ type: 'change' });
  showHowItStands(parts, { ...setUp, reports: setUp.reports.slice(0, 3) });
  check('rebuilding the list forgets what was ticked on the old one',
    whatIsTicked(parts).length === 0 && parts.states.size === 3);

  saySomething(parts, 'Started.');
  check('what a button press said back is shown', parts.said.hidden === false);
  saySomething(parts, '');
  check('and taken away again', parts.said.hidden === true);
}

reachedTheEnd = true;
console.log(`\n${ran} checks, ${failures} failed.`);
process.exit(failures ? 1 : 0);
