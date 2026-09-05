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

import { installFakeChrome } from '../test/fake-chrome.js';
import { goTo, takeTheFile, watchForDownloads } from './doors.js';

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
  const browser = installFakeChrome();
  const watching = watchForDownloads(browser.chrome);
  const clock = aClock();
  await browser.aDownloadStarted({ url: 'https://seller.example.invalid/gone.csv' });
  const wrong = await said(() => takeTheFile(browser.chrome, watching, {
    patienceSeconds: 60, fetch: aFetch({}).fetch, now: clock.now, rest: clock.rest,
  }));
  check('a platform that will not hand it over a second time says so',
    wrong.includes('would not hand over'));
  check('and says what it answered instead', wrong.includes('404'));
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
  at = 15 * 60 * 1000;
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

const EXPECTED = 39;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
