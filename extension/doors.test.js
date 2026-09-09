/* Checks for the two calls a page cannot answer for itself.
 *
 * Run: node extension/doors.test.js
 *
 * **THE ONE THAT MATTERS MOST IS THE BLOB.** Flipkart began building its orders
 * and returns files inside the page on 22 August, and the reference recorded
 * "Blob URL - re-fetch not possible" as a symptom without ever writing down the
 * reason. The reason is here: Chrome cannot hand over the bytes of a download at
 * all, so the only way to them is to ask the platform for the address a second
 * time -- and a blob address belongs to the page that made it, so there is
 * nobody to ask.
 *
 * And the one that would be worst if it were wrong: **asking without the
 * seller's own cookies gets the sign-in page**, which is a real file with a real
 * size, and everything downstream would believe the day had arrived.
 */

import { readFileSync } from 'node:fs';
import { installFakeChrome } from '../test/fake-chrome.js';
import {
  ARMED_FOR_MS, OUR_TAB, OUR_WINDOW, aTabToWalkIn, goTo, sameDocumentAs, takeTheFile,
  watchForDownloads,
} from './doors.js';

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

async function said(fn) {
  try {
    await fn();
  } catch (wrong) {
    return (wrong && wrong.message) || String(wrong);
  }
  return '';
}

/** A clock a check moves itself, so nothing here waits on a real one. */
function aClock() {
  let at = 0;
  return {
    now: () => at,
    /* Resting moves the clock rather than the wall. A check that really waited
     * ninety seconds is a check nobody runs. */
    rest: async (ms) => { at += ms; },
    goForward: (ms) => { at += ms; },
  };
}

/* ------------------------------------------------------------ going somewhere */

{
  const browser = installFakeChrome();
  const tab = await browser.chrome.tabs.create({ url: 'about:blank' });
  const clock = aClock();

  /* The page finishes drawing after a moment, the way a real one does. */
  setTimeout(() => browser.theTabFinishedDrawing(tab.id), 0);
  const landed = await goTo(browser.chrome, {
    tabId: tab.id, address: 'https://seller.example.invalid/orders', patienceSeconds: 30,
    now: clock.now, rest: async (ms) => { clock.goForward(ms); await new Promise((d) => setTimeout(d, 0)); },
  });
  check('going somewhere leaves the tab at the address it was sent to',
    landed.url === 'https://seller.example.invalid/orders');
  /* **WAITED FOR.** Handing back while the page is still blank puts every step
   * after it on nothing, and a blank page reports every button as renamed. */
  check('and it waits for the page to finish drawing', landed.status === 'complete');
}

{
  const browser = installFakeChrome();
  const tab = await browser.chrome.tabs.create({ url: 'about:blank' });
  const clock = aClock();
  const wrong = await said(() => goTo(browser.chrome, {
    tabId: tab.id, address: 'https://seller.example.invalid/slow', patienceSeconds: 20,
    now: clock.now, rest: clock.rest,
  }));
  /* **ITS OWN FAILURE, in its own words.** "The page never finished drawing" is
   * a different problem from "the button is not there", and the reference
   * reported both as the second. */
  check('a page that never finishes drawing is said as exactly that',
    wrong.includes('had not finished drawing'));
  check('and it names the address', wrong.includes('/slow'));
  check('and how long it waited', wrong.includes('20 seconds'));
}

/* -------------------------- D200: telling a tab where to go is not always a load */

/* **THE WHOLE OF FLIPKART SITS ON THIS.** Every Flipkart address in the recipe
 * file is `https://seller.flipkart.com/index.html#...` -- the page is always
 * `index.html` and the part naming the report is after the `#`. A browser going
 * between two such addresses SCROLLS: the address bar moves, the page stays, and
 * the content script is never put into it again. Nothing then asks the
 * background where the walk was, and the walk stops for ever, silently, at
 * night, with nobody watching. The reference met this and forces a reload. */

check('two addresses that agree up to the # are the same page',
  sameDocumentAs('https://seller.flipkart.com/index.html#a',
    'https://seller.flipkart.com/index.html#b'));
/* **THE SAME ADDRESS TWICE COUNTS, and it is not hypothetical**: his real
 * `me_orders` goes to the orders page, asks for the export, and goes back to
 * that same address to collect it. */
check('and so is the very same address twice',
  sameDocumentAs('https://supplier.meesho.com/panel/x/orders/',
    'https://supplier.meesho.com/panel/x/orders/'));
check('while a different page is a different page',
  !sameDocumentAs('https://supplier.meesho.com/panel/x/orders/',
    'https://supplier.meesho.com/panel/x/returns/'));
/* **UNSURE IS ANSWERED NO.** Chrome hands over no address at all for a tab the
 * extension has no permission for, and reloading such a tab is not ours to do. */
check('and a tab whose address Chrome will not hand over is not assumed to be the same',
  !sameDocumentAs(undefined, 'https://seller.flipkart.com/index.html#a'));

{
  const browser = installFakeChrome();
  const tab = await browser.chrome.tabs.create({ url: 'https://seller.flipkart.com/index.html#one' });
  browser.theTabFinishedDrawing(tab.id);
  const clock = aClock();
  setTimeout(() => browser.theTabFinishedDrawing(tab.id), 0);
  const landed = await goTo(browser.chrome, {
    tabId: tab.id, address: 'https://seller.flipkart.com/index.html#two', patienceSeconds: 30,
    now: clock.now, rest: async (ms) => { clock.goForward(ms); await new Promise((d) => setTimeout(d, 0)); },
  });
  check('moving between two Flipkart reports really draws the page again',
    browser.reloadedTabs().join(',') === String(tab.id));
  check('and it lands at the report that was asked for',
    landed.url === 'https://seller.flipkart.com/index.html#two');
}

{
  /* His real `me_orders`: back to the address it is already on, to collect the
   * export it asked for a moment ago. */
  const browser = installFakeChrome();
  const here = 'https://supplier.meesho.com/panel/v3/new/fulfillment/x/orders/';
  const tab = await browser.chrome.tabs.create({ url: here });
  browser.theTabFinishedDrawing(tab.id);
  const clock = aClock();
  setTimeout(() => browser.theTabFinishedDrawing(tab.id), 0);
  await goTo(browser.chrome, {
    tabId: tab.id, address: here, patienceSeconds: 30,
    now: clock.now, rest: async (ms) => { clock.goForward(ms); await new Promise((d) => setTimeout(d, 0)); },
  });
  check('and going back to the page it is already on draws it again too',
    browser.reloadedTabs().length === 1);
}

{
  /* **AND AN ORDINARY MOVE IS LEFT ALONE.** Reloading on top of a real page load
   * would draw every Meesho page twice, which is a second export asked for on a
   * platform that counts them. */
  const browser = installFakeChrome();
  const tab = await browser.chrome.tabs.create({ url: 'https://supplier.meesho.com/panel/x/home' });
  browser.theTabFinishedDrawing(tab.id);
  const clock = aClock();
  setTimeout(() => browser.theTabFinishedDrawing(tab.id), 0);
  await goTo(browser.chrome, {
    tabId: tab.id, address: 'https://supplier.meesho.com/panel/x/orders/', patienceSeconds: 30,
    now: clock.now, rest: async (ms) => { clock.goForward(ms); await new Promise((d) => setTimeout(d, 0)); },
  });
  check('a move to a genuinely different page is not drawn a second time',
    browser.reloadedTabs().length === 0);
}

{
  const browser = installFakeChrome();
  const tab = await browser.chrome.tabs.create({ url: 'about:blank' });
  check('going nowhere is refused rather than attempted',
    (await said(() => goTo(browser.chrome, { tabId: tab.id, address: '', patienceSeconds: 5 })))
      .includes('nowhere to go'));
  check('and nothing was asked of the tab', browser.tabs()[0].url === 'about:blank');
}

/* ------------------------------------------------------------ taking the file */

function aFetch(answers) {
  const asked = [];
  const fetch = async (address, how) => {
    asked.push({ address, how });
    const answer = answers[address];
    if (!answer) return { ok: false, status: 404 };
    return {
      ok: true,
      status: 200,
      async arrayBuffer() { return answer.buffer ? answer.buffer : new Uint8Array(answer).buffer; },
    };
  };
  return { fetch, asked };
}

{
  const browser = installFakeChrome();
  const watching = watchForDownloads(browser.chrome);
  const clock = aClock();
  const bytes = new Uint8Array([1, 2, 3, 4]);
  const { fetch, asked } = aFetch({ 'https://seller.example.invalid/report.csv': bytes });

  await browser.aDownloadStarted({ url: 'https://seller.example.invalid/report.csv' });
  const got = await takeTheFile(browser.chrome, watching, {
    patienceSeconds: 60, fetch, now: clock.now, rest: clock.rest,
  });
  check('the file that was downloaded comes back as its bytes', got.length === 4);
  check('and it is the address the download used',
    asked[0].address === 'https://seller.example.invalid/report.csv');
  /* **WITH THE SELLER'S OWN COOKIES.** Without them the platform answers with
   * its sign-in page -- a real file, with a real size, which everything
   * downstream would take for the day's data. */
  check('asked for with the seller own cookies', asked[0].how.credentials === 'include');
}

{
  /* **THE DOOR THAT CLOSED ON 22 AUGUST.** Flipkart builds the file inside the
   * page and hands over an address that belongs to that page. There is nobody to
   * ask for it a second time. */
  const browser = installFakeChrome();
  const watching = watchForDownloads(browser.chrome);
  const clock = aClock();
  const { fetch, asked } = aFetch({});
  await browser.aDownloadStarted({ url: 'blob:https://seller.flipkart.com/9d2a-4f' });
  const got = await takeTheFile(browser.chrome, watching, {
    patienceSeconds: 60, fetch, now: clock.now, rest: clock.rest,
  });
  check('a file built inside the page comes back as nothing at all', got === null);
  /* **AND NOBODY IS ASKED.** Asking would fail in a way that reads like the
   * platform being down, which is not what happened. */
  check('and the platform is not asked for it', asked.length === 0);
}

{
  /* Chrome tells you where a download really ended up, after any redirect. That
   * is the address to ask for, not the one it started at. */
  const browser = installFakeChrome();
  const watching = watchForDownloads(browser.chrome);
  const clock = aClock();
  const { fetch, asked } = aFetch({ 'https://cdn.example.invalid/real.csv': new Uint8Array([9]) });
  await browser.aDownloadStarted({
    url: 'https://seller.example.invalid/asked-for',
    finalUrl: 'https://cdn.example.invalid/real.csv',
  });
  const got = await takeTheFile(browser.chrome, watching, {
    patienceSeconds: 60, fetch, now: clock.now, rest: clock.rest,
  });
  check('where the download really ended up is what is asked for',
    asked[0].address === 'https://cdn.example.invalid/real.csv');
  check('and its bytes come back', got.length === 1);

  /* And one that ended up at a blob is still a closed door, however it began. */
  const second = installFakeChrome();
  const watchingToo = watchForDownloads(second.chrome);
  await second.aDownloadStarted({
    url: 'https://seller.flipkart.com/asked-for', finalUrl: 'blob:https://seller.flipkart.com/1',
  });
  check('and one that ended at a blob is still a closed door',
    (await takeTheFile(second.chrome, watchingToo, {
      patienceSeconds: 60, fetch: aFetch({}).fetch, now: clock.now, rest: clock.rest,
    })) === null);
}

{
  /* **A PLATFORM REFUSING THIS HALF IS NOT THE END OF THE REPORT, AND THAT IS
   * NOT A GUESS (D198; the reference's DOCS.md section 11, Method 7).** It moved
   * only the CATCHING and CANCELLING of a download into its background half and
   * deliberately left the FETCHING in the page, in one line: its content script
   * "does its OWN fetch(url, credentials include) -- NOT background's fetch,
   * because background's fetch fails CORS on some FK CDN endpoints (confirmed
   * for FK_CLAIMS)".
   *
   * **THIS CHECK USED TO REQUIRE A FAILURE HERE, AND THAT WAS WRONG.** Every
   * Flipkart report whose file sits on one of those endpoints would have been
   * lost every night behind a message blaming the platform, while the page half
   * one layer away could have fetched it perfectly. */
  const browser = installFakeChrome();
  const watching = watchForDownloads(browser.chrome);
  const clock = aClock();
  await browser.aDownloadStarted({ url: 'https://seller.example.invalid/gone.csv' });
  const got = await takeTheFile(browser.chrome, watching, {
    patienceSeconds: 60, fetch: aFetch({}).fetch, now: clock.now, rest: clock.rest,
  });
  check('a platform that refuses THIS half is not reported as a failure',
    got !== null && typeof got === 'object' && !(got instanceof Uint8Array));
  check('the address is handed back so the page half can try from its own origin',
    got.address === 'https://seller.example.invalid/gone.csv');
  check('and what the platform said is carried with it, not thrown away',
    String(got.couldNotFetch).includes('404'));
}

{
  /* **AND A FETCH THAT THROWS IS THE SAME CASE, NOT A DIFFERENT ONE.** A browser
   * refusing a cross-origin read throws rather than answering, and treating only
   * a bad status as recoverable would miss the very case this exists for. */
  const browser = installFakeChrome();
  const watching = watchForDownloads(browser.chrome);
  const clock = aClock();
  await browser.aDownloadStarted({ url: 'https://cdn.example.invalid/report.xlsx' });
  const got = await takeTheFile(browser.chrome, watching, {
    patienceSeconds: 60,
    fetch: async () => { throw new TypeError('Failed to fetch'); },
    now: clock.now,
    rest: clock.rest,
  });
  check('a fetch the browser refuses outright is handed on rather than reported broken',
    got.address === 'https://cdn.example.invalid/report.xlsx'
    && got.couldNotFetch.includes('Failed to fetch'));
}

{
  /* **NOTHING DOWNLOADING AT ALL IS A DIFFERENT PROBLEM FROM A CLOSED DOOR**, and
   * it says so. One means the platform changed how it hands files over; the
   * other means the click did not do what it was supposed to. */
  const browser = installFakeChrome();
  const watching = watchForDownloads(browser.chrome);
  const clock = aClock();
  const wrong = await said(() => takeTheFile(browser.chrome, watching, {
    patienceSeconds: 90, fetch: aFetch({}).fetch, now: clock.now, rest: clock.rest,
  }));
  check('nothing downloading at all is its own failure',
    wrong.includes('Nothing began downloading'));
  check('and it says how long it waited', wrong.includes('90 seconds'));
}

{
  /* **WAITED FOR.** Meesho takes up to five minutes to build an orders export.
   * Asked the instant the button is pressed, nothing has started. */
  const browser = installFakeChrome();
  const watching = watchForDownloads(browser.chrome);
  const clock = aClock();
  const { fetch } = aFetch({ 'https://supplier.example.invalid/late.csv': new Uint8Array([7, 7]) });
  let ticks = 0;
  const waiting = takeTheFile(browser.chrome, watching, {
    patienceSeconds: 300,
    fetch,
    now: clock.now,
    rest: async (ms) => {
      clock.goForward(ms);
      ticks += 1;
      if (ticks === 3) await browser.aDownloadStarted({ url: 'https://supplier.example.invalid/late.csv' });
      await new Promise((done) => setTimeout(done, 0));
    },
  });
  const got = await waiting;
  check('a file that takes its time is still taken', got.length === 2);
  check('and it really did wait rather than answering at once', ticks >= 3);
}

{
  /* A download from an earlier step must not be taken for this one's file. */
  const browser = installFakeChrome();
  const watching = watchForDownloads(browser.chrome);
  await browser.aDownloadStarted({ url: 'https://seller.example.invalid/earlier.csv' });
  check('what has already started is remembered', watching.seen().length === 1);
  watching.forget();
  check('and can be forgotten before a step that should produce its own file',
    watching.seen().length === 0);

  /* What it hands back is a copy: editing it must not change what it saw. */
  await browser.aDownloadStarted({ url: 'https://seller.example.invalid/a.csv' });
  const seen = watching.seen();
  seen[0].url = 'changed';
  check('and what it hands back is a copy',
    watching.seen()[0].url === 'https://seller.example.invalid/a.csv');
}

{
  const browser = installFakeChrome();
  const watching = watchForDownloads(browser.chrome);
  const clock = aClock();
  await browser.aDownloadStarted({ url: '', finalUrl: '' });
  const wrong = await said(() => takeTheFile(browser.chrome, watching, {
    patienceSeconds: 30, fetch: aFetch({}).fetch, now: clock.now, rest: clock.rest,
  }));
  /* An empty address asked for anyway fetches whatever page the seller is on,
   * and a portal page saved as a report is a file with a real size that
   * everything downstream believes. */
  check('a download with no address at all is named rather than asked for',
    wrong.includes('no address'));
}

{
  /* **THE REAL WAITING, not a clock a check moves itself.** Everything above
   * hands in its own resting so that nothing waits on a wall clock -- which
   * leaves the real one, the one that runs in front of a seller, never run at
   * all. */
  const browser = installFakeChrome();
  const real = watchForDownloads(browser.chrome);
  let looked = 0;
  const watching = { seen: () => { looked += 1; return real.seen(); }, forget: real.forget };
  const startedAt = Date.now();
  const wrong = await said(() => takeTheFile(browser.chrome, watching, {
    patienceSeconds: 0.4, fetch: aFetch({}).fetch,
  }));
  check('left to wait on its own, it still gives up and says so',
    wrong.includes('Nothing began downloading'));
  check('and it really waited', Date.now() - startedAt >= 300);
  /* **AND IT RESTED BETWEEN LOOKS RATHER THAN SPINNING.** Waiting five minutes
   * for Meesho to build a file while asking thousands of times a second is a
   * laptop with its fan on, and the seller notices that long before they notice
   * the data arriving. */
  check('looking a handful of times rather than thousands', looked > 0 && looked < 20);
}

{
  const browser = installFakeChrome();
  const watching = watchForDownloads(browser.chrome);
  check('taking a file with no way of asking the platform is refused',
    (await said(() => takeTheFile(browser.chrome, watching, { patienceSeconds: 5 })))
      .includes('way of asking the platform'));
  check('and it is listening for downloads from the moment it is set up',
    browser.chrome.downloads.onCreated.many === 1);
}

/* ------------------------------- cancelling the download as it starts */

/* **THE ONE THING IN THIS FILE THAT IS ABOUT WHEN, NOT WHAT.**
 *
 * A download Chrome has nowhere to put is a download Chrome asks about, in a
 * Save-as window, and a seller with "Ask where to save each file" switched on is
 * then waiting on a window nobody is there to click -- for ever, silently, while
 * the platform records the file as downloaded. Cancelling it INSIDE the event,
 * before a single `await`, gets there first. Cancelling it a moment later, off a
 * list, is always too late.
 *
 * The stand-in's `cancel` is callback-shaped exactly so that these can look
 * before anything has been waited for and see it already done.
 */

{
  const browser = installFakeChrome();
  const watching = watchForDownloads(browser.chrome);
  watching.expectAFile();

  /* **NOT AWAITED, AND THAT IS THE CHECK.** Everything the listener did
   * synchronously has already happened by the time this call hands back its
   * promise. An `await` put in front of the cancel would move it past this
   * line, and this check would go red -- which is the only reason it is written
   * this way. */
  const dispatching = browser.aDownloadStarted({ url: 'https://storage.example.invalid/r.xlsx' });
  check('the download is cancelled inside the event, before anything is waited for',
    browser.cancelledDownloads().length === 1);
  await dispatching;
  check('and it is erased as well, so it leaves nothing in the seller own list',
    browser.erasedDownloads().length === 1);
  /* **AND THE ADDRESS SURVIVES THE CANCEL.** Cancelling throws away the bytes,
   * which were never readable anyway; what the fetch needs is the address, and
   * it is taken before anything is cancelled. */
  check('and the address is still there to be asked for a second time',
    watching.seen()[0].url === 'https://storage.example.invalid/r.xlsx');
}

{
  /* **A DOWNLOAD NOBODY ARMED IS THE SELLER OWN, AND IT IS NEVER TOUCHED.**
   * Cancelling one of those is a file vanishing in front of them with no
   * explanation -- a worse fault than the one this whole thing exists to fix. */
  const browser = installFakeChrome();
  const watching = watchForDownloads(browser.chrome);
  await browser.aDownloadStarted({ url: 'https://anywhere.example.invalid/his-own.pdf' });
  check('a download nothing armed is left alone', browser.cancelledDownloads().length === 0);
  check('and it is still remembered, the way it always was', watching.seen().length === 1);
}

{
  /* **ARMED FOR ONE FILE, NOT FOR THE DAY.** A walk takes one file; the arm is
   * used up by it. Anything the seller downloads afterwards is theirs. */
  const browser = installFakeChrome();
  const watching = watchForDownloads(browser.chrome);
  watching.expectAFile();
  await browser.aDownloadStarted({ id: 1, url: 'https://storage.example.invalid/ours.xlsx' });
  await browser.aDownloadStarted({ id: 2, url: 'https://anywhere.example.invalid/his-own.pdf' });
  check('the file the walk asked for is cancelled', browser.cancelledDownloads().includes(1));
  check('and the next one, which is the seller own, is not',
    !browser.cancelledDownloads().includes(2));
}

{
  /* **AND THE ARM RUNS OUT.** A walk that armed and then never produced a file
   * -- the asking half of a two-phase report does exactly that -- must not still
   * be armed hours later when the seller downloads an invoice by hand. */
  let at = 0;
  const browser = installFakeChrome();
  const watching = watchForDownloads(browser.chrome, { now: () => at });
  watching.expectAFile();
  /* **TAKEN FROM THE DOOR RATHER THAN TYPED AGAIN.** Written here as its own
   * fifteen minutes, this check went on passing when the door's own number
   * changed -- two records of one fact, which is the fault this project has been
   * caught by four times. */
  at = ARMED_FOR_MS;
  await browser.aDownloadStarted({ url: 'https://anywhere.example.invalid/much-later.pdf' });
  check('an arm nobody used runs out rather than lasting the day',
    browser.cancelledDownloads().length === 0);
}

{
  /* **CANCELLED AND STILL FETCHED, which is the whole point of cancelling.**
   * Chrome never hands over the bytes of a download; the address is asked for a
   * second time with the seller own cookies, and that is where the file comes
   * from. */
  const browser = installFakeChrome();
  const watching = watchForDownloads(browser.chrome);
  const clock = aClock();
  const bytes = new Uint8Array([7, 7, 7]);
  const { fetch, asked } = aFetch({ 'https://storage.example.invalid/real.xlsx': bytes });
  watching.expectAFile();
  await browser.aDownloadStarted({
    url: 'https://supplier.example.invalid/asked-for',
    finalUrl: 'https://storage.example.invalid/real.xlsx',
  });
  const got = await takeTheFile(browser.chrome, watching, {
    patienceSeconds: 60, fetch, now: clock.now, rest: clock.rest,
  });
  check('a cancelled download still gives up its bytes, from the address',
    got.length === 3 && asked[0].address === 'https://storage.example.invalid/real.xlsx');
}

/* ------------------ D200: the window this product runs in at two in the morning */

/* **ONE SENTENCE OF CHROME'S DECIDES WHETHER THIS PRODUCT WORKS UNATTENDED:**
 *
 *   **CHROME THROTTLES A TAB'S TIMERS WHEN A DIFFERENT TAB IS SELECTED IN THAT
 *   TAB'S WINDOW, OR WHEN THAT WINDOW IS MINIMISED. IT IS NOT TRIGGERED BY
 *   SCREEN FOCUS, AND NOT BY WHETHER ANYBODY IS SITTING THERE.**
 *   (developer.chrome.com/blog/timer-throttling-in-chrome-88)
 *
 * Walking whatever tab we are handed puts the walk in the seller's own window,
 * as one of their many unselected tabs -- the throttled case. The reference
 * measured the cost: a fifteen-second wait silently taking NINE MINUTES OR MORE.
 * A walk under that reports a perfectly good page as a missing button, at night,
 * with nobody there to see it was fine. */

{
  const browser = installFakeChrome();
  const tab = await aTabToWalkIn(browser.chrome);
  const window = browser.windows()[0];
  check('a walk gets a window of its own rather than one of the seller own tabs',
    browser.windows().length === 1 && tab.windowId === window.id);
  /* **UNFOCUSED, because focus is not what throttling watches** -- so there is
   * nothing to be gained by taking the screen from somebody using their
   * computer, and everything to lose. */
  check('and it never takes the screen: the window is made unfocused',
    window.focused === false);
  /* **AND NOT MINIMISED, because that IS what throttling watches.** */
  check('and it is not minimised, which is the state that would be throttled',
    window.state === 'normal');
  check('and the tab is the selected tab of that window',
    browser.tabs().find((one) => one.id === tab.id).active === true);
  /* **WRITTEN DOWN, because the worker that made it is shut down thirty seconds
   * later and everything it held in a variable goes with it -- but written in
   * the storage that does NOT outlive the session**, because a window number
   * means nothing outside the session that issued it. */
  check('and both are written where the worker being shut down cannot lose them',
    browser.storedForTheSession()[OUR_WINDOW] === window.id
    && browser.storedForTheSession()[OUR_TAB] === tab.id);
  check('and NOT where they would outlive the session that gave them meaning',
    browser.stored()[OUR_WINDOW] === undefined && browser.stored()[OUR_TAB] === undefined);
}

{
  /* **THE SAME TAB NEXT TIME.** A tab per report leaves a window filling up with
   * dead tabs -- and the moment there are two, one of them is not selected,
   * which is the throttled case reached by tidiness. */
  const browser = installFakeChrome();
  const first = await aTabToWalkIn(browser.chrome);
  const again = await aTabToWalkIn(browser.chrome);
  check('the next report walks in the same tab rather than piling up new ones',
    again.id === first.id && browser.windows().length === 1);
  check('and there is still only one tab in that window',
    browser.tabs().filter((one) => one.windowId === first.windowId).length === 1);
}

{
  /* **PUT BACK IF SOMEBODY MINIMISED IT.** A minimised window is a throttled
   * window whatever else is true of it, so a walk starting into one would be
   * slowed from its first step. */
  const browser = installFakeChrome();
  const first = await aTabToWalkIn(browser.chrome);
  await browser.chrome.windows.update(first.windowId, { state: 'minimized' });
  await aTabToWalkIn(browser.chrome);
  const window = browser.windows()[0];
  check('a window somebody minimised is put back, because minimised is throttled',
    window.state === 'normal');
  check('and putting it back still does not take the screen', window.focused === false);
}

{
  /* **AND IF SOMETHING ELSE IS OPENED IN OUR WINDOW, OURS IS MADE THE SELECTED
   * ONE AGAIN.** An unselected tab is a throttled tab whatever window it is in,
   * so being in our own window is not on its own enough. */
  const browser = installFakeChrome();
  const ours = await aTabToWalkIn(browser.chrome);
  await browser.chrome.tabs.create({
    url: 'https://example.invalid/', windowId: ours.windowId, active: true,
  });
  check('something else opened in our window takes the selection away',
    browser.tabs().find((one) => one.id === ours.id).active === false);
  await aTabToWalkIn(browser.chrome);
  check('and the next walk takes it back rather than running throttled',
    browser.tabs().find((one) => one.id === ours.id).active === true);
}

{
  /* **A WINDOW THE SELLER CLOSED IS NOT A FAILURE.** Another one is made.
   * Treating it as a fault would stop a night's run over somebody tidying up. */
  const browser = installFakeChrome();
  const first = await aTabToWalkIn(browser.chrome);
  await browser.chrome.windows.remove(first.windowId);
  const second = await aTabToWalkIn(browser.chrome);
  check('a window the seller closed is replaced rather than reported as broken',
    second && second.windowId !== first.windowId);
  check('and the new one is remembered in place of the old',
    browser.storedForTheSession()[OUR_WINDOW] === second.windowId);
}

{
  /* **THE ONE THAT WOULD HAVE NAVIGATED THE SELLER'S OWN PAGE AWAY FROM UNDER
   * THEM (A26R, and driven to the letter by A26R3).**
   *
   * A window number and a tab number mean something only within one browser
   * session; Chrome hands them out again from the start next time. So the
   * sequence below needs nothing unusual at all:
   *
   *   the extension runs and remembers window 100, tab 1
   *   -> the seller switches the extension OFF
   *   -> the seller closes Chrome and opens it again the next morning
   *   -> Chrome gives the seller's OWN first window 100 and their first tab 1
   *   -> the seller switches the extension back on
   *
   * **AN EARLIER FIX CLEARED THESE ON `chrome.runtime.onStartup`, AND IT DOES
   * NOT COVER THAT.** `onStartup` fired while the extension was switched off, so
   * it reached nobody, and there is no event at all for an extension being
   * switched back on. Their inbox would have been made the selected tab and then
   * walked to a portal page.
   *
   * **KEEPING THEM IN `session` STORAGE IS WHAT CLOSES IT**, because Chrome
   * clears that "if the extension is disabled, reloaded, updated, and when the
   * browser restarts" -- every one of the moments above, with nothing having to
   * remember to do anything. */
  const browser = installFakeChrome();
  const ours = await aTabToWalkIn(browser.chrome);
  check('within one session our own tab is remembered and reused',
    (await aTabToWalkIn(browser.chrome)).id === ours.id);

  /* Switched off, Chrome closed and opened, switched back on. **The numbering
   * starts again, which is the whole reason those numbers stop meaning what
   * they meant.** */
  browser.theBrowserRestarted();

  /* And now those very numbers belong to the seller. */
  const theirs = await browser.chrome.windows.create({ url: 'https://mail.google.com/' });
  const theirTab = theirs.tabs[0];

  const got = await aTabToWalkIn(browser.chrome);
  check('after the extension is switched off and Chrome restarted, their tab is NOT taken',
    got.id !== theirTab.id);
  check('and their page is left exactly where it was',
    browser.tabs().find((one) => one.id === theirTab.id).url === 'https://mail.google.com/');
  check('and their window is not the one the walk runs in',
    got.windowId !== theirs.id);
}

/* ------------------- how long a walk may go on, worked out rather than guessed */

/* **THIS NUMBER USED TO BE ADDED UP BY HAND IN A COMMENT, AND NOTHING CHECKED
 * ANY PART OF IT.** It said the longest walk was 10.58 minutes and bounded a walk
 * at fifteen. Then `me_orders` grew a 35-second wait and six rounds of shutting
 * and reopening a menu, its worst case went past sixteen minutes, and the bound
 * silently became shorter than the thing it bounds -- which would have ended a
 * perfectly good night as "stopped part way through and never said why".
 *
 * So it is computed here, off the very file the extension reads, and
 * `ARMED_FOR_MS` is held to it in both directions: long enough to cover the
 * longest walk, and not so long that it stops bounding anything. */
{
  const BOOK = JSON.parse(readFileSync(new URL('./recipes.json', import.meta.url), 'utf8'));

  /* **THE WORST A SINGLE STEP CAN COST, IN SECONDS.** Every step may burn its
   * whole patience. The take-file step can burn it three ways over: once looking
   * for the file, once per round of shutting the menu and opening it again --
   * where the round also spends the time it is left shut -- and once waiting for
   * the bytes themselves. */
  const worstOf = (one) => {
    const patience = Number(one.patience) || 0;
    if (one.do !== 'take-file') return patience;
    const looking = one.find ? patience : 0;
    const rounds = one.lookAgain
      ? Number(one.lookAgain.times) * (Number(one.lookAgain.after) + 2 * patience)
      : 0;
    return looking + rounds + patience;
  };

  /* **A WALK RUNS A RECIPE'S ASK LIST OR ITS TAKE LIST, NEVER BOTH**, so the two
   * halves are measured apart and never added together. An earlier version of
   * the comment this replaces got that right and named the wrong recipe anyway. */
  let longest = 0;
  let named = '';
  for (const [id, recipe] of Object.entries(BOOK.recipes)) {
    for (const half of ['toAsk', 'toTake']) {
      const total = (recipe[half] || []).reduce((sum, one) => sum + worstOf(one), 0);
      if (total > longest) { longest = total; named = `${id}.${half}`; }
    }
  }
  const longestMs = longest * 1000;

  check('there is a longest walk, and it is worked out from the recipes themselves',
    longest > 0 && named.length > 0);
  check('AND A WALK IS BELIEVED FOR LONGER THAN THE LONGEST ONE THAT CAN EXIST',
    ARMED_FOR_MS >= longestMs);
  /* **AND NOT SO MUCH LONGER THAT IT BOUNDS NOTHING.** While this is armed, a
   * file the seller downloads by hand can be taken for the walk's and cancelled
   * in front of them, so the margin is a cost and is stated rather than left to
   * grow. */
  check('and not more than ten minutes longer, because an armed cancel is not free',
    ARMED_FOR_MS - longestMs <= 10 * 60 * 1000);
}

const EXPECTED = 70;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
