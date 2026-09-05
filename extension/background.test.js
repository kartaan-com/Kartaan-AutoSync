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
} from './background.js';
import { CAUGHT, TOO_BIG, catchTheNextFile } from './catch-blob.js';
import { watchForDownloads } from './doors.js';
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
  check('wiring the worker up sets the clock on the way past', browser.alarms().length === 1);

  browser.forgetTheAlarms();
  check('and here the alarm is gone, with Chrome still running', browser.alarms().length === 0);

  /* Chrome shuts an idle worker down and starts it again when something wakes
   * it. Starting it again is wiring it up again -- and that is the moment the
   * clock has to come back. */
  browser.shutTheWorkerDown();
  await wireUp(browser.chrome, { onDue: async () => { due += 1; } });
  check('the next time the worker wakes, the clock is put back',
    browser.alarms().length === 1 && browser.alarms()[0].name === DAILY);
}

{
  const browser = installFakeChrome();
  let due = 0;
  await wireUp(browser.chrome, { onDue: async () => { due += 1; } });
  check('the profile launching is listened for', browser.chrome.runtime.onStartup.many === 1);
  check('and the extension being installed or updated too',
    browser.chrome.runtime.onInstalled.many === 1);
  check('and the alarm itself', browser.chrome.alarms.onAlarm.many === 1);

  browser.forgetTheAlarms();
  await browser.chrome.runtime.onStartup.happened();
  check('a profile launching with no alarm puts it back', browser.alarms().length === 1);

  browser.forgetTheAlarms();
  await browser.chrome.runtime.onInstalled.happened({ reason: 'update' });
  check('and so does an update', browser.alarms().length === 1);
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
    browser.alarms().length === 1);

  await browser.chrome.alarms.onAlarm.happened({ name: 'something-else' });
  check('somebody else\'s alarm does not start a run', due === 2);
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
  wireUp(browser.chrome, {
    onDue: async () => {},
    answer: answerThePage(browser.chrome, {
      goTo: async (_chrome, where) => { went.push(where); },
      takeTheFile: async () => new Uint8Array([1, 2, 3]),
      watching: { forget: () => {}, seen: () => [], expectAFile: () => {} },
      say: (line) => said.push(line),
      secret: () => 'a-secret',
    }),
  });

  check('the background answers the page half at all',
    (await browser.aPageAsked({ do: 'go', address: 'https://x/', patience: 5 })) !== undefined);
  check('and it really went there', went.length === 1 && went[0].address === 'https://x/');
  check('and it went in the tab that asked', went[0].tabId === tab.id);

  const file = await browser.aPageAsked({ do: 'take-file', patience: 5 });
  check('a file comes back as something a message can carry',
    Array.isArray(file.bytes) && file.bytes.length === 3);

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
  globalThis.URL = { createObjectURL: () => 'blob:https://supplier.meesho.com/abc' };

  await armTheCatcher(browser.chrome, { tabId: tab.id, secret: 'the-secret' });
  const put = browser.putIntoPages();
  check('the catcher is put into the page rather than loaded on every page',
    put.length === 1 && put[0].tabId === tab.id);
  /* **THE PAGE'S OWN WORLD, because that is the only place the bytes exist.** */
  check('and into the page\u2019s own world', put[0].world === 'MAIN');
  /* **AND THE SECRET GOES AS AN ARGUMENT**, which is the whole point: it never
   * crosses anything the page can listen to. */
  check('and the secret goes with it as an argument', put[0].args[0] === 'the-secret');

  /* **THE HANDLE, NEVER THE BYTES.** It used to post a seller's whole settlement
   * file to the page with `targetOrigin '*'`. */
  const madeAFile = globalThis.URL.createObjectURL({
    size: 2048, type: '', arrayBuffer: async () => new ArrayBuffer(2048),
  });
  check('a file the page built is reported', posted.length === 1 && madeAFile.startsWith('blob:'));
  check('and it carries the secret', posted[0].data.secret === 'the-secret');
  check('and a handle rather than the bytes',
    typeof posted[0].data.handle === 'string' && posted[0].data.asLetters === undefined);
  check('and it is addressed to this page and nowhere else',
    posted[0].to === 'https://supplier.meesho.com');
  check('and it says what it is', posted[0].data.kartaan === CAUGHT);

  /* **ONCE, AND ONCE ONLY.** Armed for one file; a second is not ours. */
  globalThis.URL.createObjectURL({
    size: 2048, type: '', arrayBuffer: async () => new ArrayBuffer(2048),
  });
  check('and a second file is not reported without being armed again', posted.length === 1);

  /* Put back what was borrowed. **Deleted rather than restored, the checks
   * below lost Node's own URL and stopped part way through** -- a stand-in that
   * takes something away has to give it back. */
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
  /* **AND NOTHING IN IT BROADCASTS.** The finding was one character wide. */
  check('and nothing in it posts to anything but this page',
    !/postMessage\([^)]*,\s*['\"]\*['\"]/.test(source));
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
  /* **AND THE CATCHER IS NO LONGER SITTING ON EVERY PORTAL PAGE.** */
  const inPages = (manifest.content_scripts || []).flatMap((one) => one.js || []);
  check('the catcher is not loaded on every portal page any more',
    !inPages.includes('catch-blob.js'));
  check('and the page half still is', inPages.includes('content.js'));
  check('and nothing else runs in the page\u2019s own world by default',
    !(manifest.content_scripts || []).some((one) => one.world === 'MAIN'));

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

const EXPECTED = 90;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
