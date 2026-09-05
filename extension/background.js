/* The half of the extension that a page cannot be: the clock, the queue, and
 * the record of what happened.
 *
 * **THE TWO FAULTS THIS FILE EXISTS TO MAKE IMPOSSIBLE**, both read live out of
 * his own Chrome on 2026-08-27, and between them they are why nothing has run
 * since 25 August and why the day it last ran left no trace:
 *
 *   1. **THE CLOCK STOPPED AND NOTHING PUT IT BACK.** The reference asks for its
 *      daily alarm in exactly one place -- when the extension is installed. An
 *      alarm is cleared by a reload, by a browser restart and by every update,
 *      so once it went, nothing was ever going to ask for it again, and the
 *      extension sat idle for ever with an empty queue.
 *   2. **A RUN THAT WAS INTERRUPTED WROTE NOTHING DOWN.** Everything the
 *      reference records -- the log, the day board, the summary -- is written in
 *      one function, and the path taken when a portal asks somebody to sign in
 *      does not call it. On 25 August ten real files were fetched and every
 *      layer that exists to record them stayed silent.
 *
 * **NEITHER IS FIXED BY REMEMBERING. BOTH ARE FIXED BY SHAPE:**
 *
 *   - the alarm is asked for **every time this worker starts**, which is Google's
 *     own advice and is stronger than the two events -- because neither
 *     `onStartup` nor `onInstalled` fires when an alarm is cleared while Chrome
 *     is running, and that is the case that leaves it idle for ever;
 *   - a run's record is written **before anything that can end a run**, and
 *     there is one way out of a run rather than several.
 *
 * **AND NOTHING IS KEPT IN A VARIABLE.** Chrome shuts this worker down after
 * thirty seconds of quiet and says plainly that "any global variables you set
 * will be lost". A run takes minutes -- a Meesho orders export alone can take
 * five. So the run's state lives in `chrome.storage.local`, which is cleared only
 * when the extension is removed, and every function here reads it back rather
 * than trusting anything held in memory.
 *
 * The whole of that reading is the "Chrome MV3" section of `docs/WORKING.md`.
 */

import { catchTheNextFile } from './catch-blob.js';

/* The one name the daily alarm has. Written once: two spellings of an alarm's
 * name is one alarm created and a different one looked for, and nothing would
 * ever say so. */
export const DAILY = 'kartaan-autosync-daily';

/* Every day, and it is a period rather than a one-off on purpose: a one-off that
 * fires while Chrome is shut is simply never delivered, and nothing reschedules
 * it. */
export const EVERY_DAY_IN_MINUTES = 24 * 60;

/* What the run's own record is called in storage. */
export const THE_RUN = 'kartaan-autosync-run';

/* What a run can be. **A run that was interrupted is its own word**, because
 * "failed" and "somebody has to sign in" are not the same thing and telling them
 * apart is what stops every report after the first being called broken. */
export const RUNNING = 'running';
export const FINISHED = 'finished';
export const NEEDS_SIGNING_IN = 'needs-signing-in';
export const STOPPED = 'stopped';

/**
 * Make sure the daily alarm exists, and say whether it had to be created.
 *
 * **ASKED EVERY TIME THE WORKER STARTS, not only when the extension is installed
 * or the profile launches.** Google's own words: "it is best to make sure
 * important alarms exists each time your service worker starts up." That is
 * stronger than the two events, and the difference is the whole of the outage:
 * `onStartup` fires when a profile first launches and `onInstalled` when the
 * extension is installed or updated, and **neither of them fires when an alarm
 * is cleared while Chrome is running.**
 */
export async function makeSureTheClockIsSet(chrome) {
  const already = await chrome.alarms.get(DAILY);
  if (already) return false;
  await chrome.alarms.create(DAILY, {
    periodInMinutes: EVERY_DAY_IN_MINUTES,
    /* Set out loud rather than left to the default. The documentation asks for
     * it explicitly "to maximize compatibility across browsers", and it is the
     * difference between an alarm surviving a browser restart and not. */
    persistAcrossSessions: true,
  });
  return true;
}

/**
 * Start a run, and write it down before anything is attempted.
 *
 * **WRITTEN DOWN FIRST, NOT AT THE END.** A record made only when a run finishes
 * is a record that does not exist for any run that did not -- which is every run
 * worth reading about. This is also what lets the next start see that one is
 * already going.
 */
export async function startTheRun(chrome, { at, doing }) {
  const held = await theRun(chrome);
  if (held && held.state === RUNNING) {
    return { ...held, alreadyGoing: true };
  }
  const run = {
    state: RUNNING,
    startedAt: at,
    finishedAt: null,
    /* What is still to do, and what has been done. **Both are written down at
     * every step**, because the worker can be shut down between any two of them
     * and whatever was only in a variable is gone. */
    left: [...doing],
    done: [],
    lines: [],
    why: '',
  };
  await write(chrome, run);
  return { ...run, alreadyGoing: false };
}

/**
 * Say what happened to one report, and write it down before going on.
 *
 * **ONE REPORT AT A TIME, EACH ONE SAVED AS IT HAPPENS.** The reference kept the
 * whole run in memory and wrote it out at the end, so an interruption took the
 * lot. Written as it goes, an interruption costs the report in flight and
 * nothing else.
 */
export async function recordOneReport(chrome, { reportId, state, say, at }) {
  const run = await theRun(chrome);
  if (!run || run.state !== RUNNING) {
    /* **REFUSED RATHER THAN INVENTED.** Recording against a run that is not
     * happening would build a record of a run nobody asked for, and it would
     * hide the real fault: something is calling this after the run ended. */
    throw new Error('Nothing can be recorded against a run that is not going.');
  }
  run.done.push({ reportId, state, say, at });
  run.left = run.left.filter((one) => one !== reportId);
  run.lines.push({ at, reportId, say });
  await write(chrome, run);
  return run;
}

/**
 * End the run, whatever ended it, and leave the record behind.
 *
 * **THE ONLY WAY OUT OF A RUN, AND IT ALWAYS WRITES.** The fault this replaces is
 * exactly one missing call: the reference's sign-in path skipped the one function
 * that writes the log, the board and the summary, so a run that fetched ten real
 * files left no trace of any of them. Here there is nothing to skip -- finishing,
 * being interrupted and being stopped all come through this one door, and the
 * record is written before anything else is done.
 *
 * **AND WHAT WAS ALREADY DONE IS KEPT.** A run that ends because a portal asks
 * for a sign-in has usually done real work first; calling the whole run a failure
 * throws that away and sends somebody looking for files that are already there.
 */
export async function endTheRun(chrome, { state, why = '', at }) {
  if (state === RUNNING) {
    throw new Error('A run cannot be ended by saying it is still going.');
  }
  const run = await theRun(chrome);
  if (!run) {
    /* Nothing to end. Said plainly rather than writing a run that never
     * started, which would put a phantom row on the day board. */
    return null;
  }
  const ended = { ...run, state, why, finishedAt: at };
  await write(chrome, ended);
  return ended;
}

/** The run as it stands, read back rather than remembered. */
export async function theRun(chrome) {
  const held = await chrome.storage.local.get(THE_RUN);
  return held[THE_RUN] || null;
}

async function write(chrome, run) {
  await chrome.storage.local.set({ [THE_RUN]: run });
}

/**
 * What a run that was cut short still owes.
 *
 * **A DAY IS NEVER LOST BECAUSE A RUN ENDED EARLY.** Whatever was left when it
 * stopped is what the next run starts with, on top of whatever is owed by then.
 * The reference emptied its queue on a sign-in prompt and the reports behind it
 * were simply never mentioned again.
 */
export function stillOwedFrom(run) {
  if (!run || run.state === RUNNING) return [];
  return [...run.left];
}

/**
 * A secret nothing but this extension can know, for one file.
 *
 * **THIS IS WHAT STOPS A PORTAL PAGE PUTTING ITS OWN BYTES IN THE SELLER'S
 * DRIVE (D135).** `catch-blob.js` has to run in the page's own world -- there is
 * nowhere else the bytes of a file the page built itself ever exist -- and
 * anything running there is beside somebody else's adverts. So the extension's
 * own half believes a message from that world only when it carries this, and it
 * is fresh for every file: the page cannot learn it before the genuine message
 * is sent, and by then the genuine message has been taken.
 *
 * **THIRTY-TWO BYTES FROM THE BROWSER'S OWN RANDOM SOURCE.** `Math.random` is
 * predictable by design and is documented as unsuitable for exactly this.
 */
export function aFreshSecret(crypto) {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return [...bytes].map((one) => one.toString(16).padStart(2, '0')).join('');
}

/**
 * Arm the catcher in one tab, and answer with the secret it will use.
 *
 * **PUT IN ONE FILE AT A TIME, NOT LOADED ON EVERY PORTAL PAGE.** It used to be
 * a content script sitting armed on every page the seller opened; now it exists
 * only for the moment a report is actually being fetched.
 *
 * **THE SECRET IS HANDED OVER AS AN ARGUMENT**, which is the whole point: it
 * never crosses `postMessage`, so nothing on the page can read it on the way in.
 */
export async function armTheCatcher(chrome, { tabId, secret }) {
  await chrome.scripting.executeScript({
    target: { tabId },
    world: 'MAIN',
    func: catchTheNextFile,
    args: [secret],
  });
  return secret;
}

/**
 * Answer the one question the page half cannot answer for itself.
 *
 * **WITHOUT THIS THE EXTENSION CANNOT FETCH A SINGLE REPORT** -- `content.js`
 * asks the background to go somewhere, to take a file and to write a line, and
 * cycle 46 found that nothing anywhere was listening. Everything was built and
 * nothing was joined up.
 *
 * **ONLY FROM OUR OWN PAGE HALF, and that is checked rather than assumed.**
 * `chrome.runtime.onMessage` also carries messages from other extensions and
 * from web pages that have been allowed to send them, and a message with no tab
 * behind it is not one of ours.
 */
export function answerThePage(chrome, parts) {
  /* **NOT ITSELF ASYNC, and that is not a detail.** A message this does not
   * recognise has to be refused BEFORE any promise exists, or the worker tells
   * Chrome it will answer later and then never does -- which holds the channel
   * open and throws away whatever another listener would have said. */
  return (asked, from) => {
    const tabId = from && from.tab && from.tab.id;
    if (!asked || !asked.do || !tabId) return null;
    if (from.id && from.id !== chrome.runtime.id) return null;
    if (!KNOWN.includes(asked.do)) return null;
    return carryOut(chrome, parts, asked, tabId);
  };
}

/** What the page half may ask for. Written once, so refusing an unknown message
 *  and carrying out a known one cannot disagree about which is which. */
export const KNOWN = ['go', 'arm-the-catcher', 'take-file', 'say'];

async function carryOut(chrome, parts, asked, tabId) {
  const { goTo, takeTheFile, watching, say, secret } = parts;
  if (asked.do === 'go') {
    watching.forget();
    await goTo(chrome, { tabId, address: asked.address, patienceSeconds: asked.patience });
    return { went: true };
  }
  if (asked.do === 'arm-the-catcher') {
    /* **THE DOWNLOAD IS ARMED HERE TOO, and here is the EARLIEST place.** This
     * is the one message the page half sends before the walk starts. `go` and
     * `say` also arrive before the click and would do -- **an earlier version of
     * this comment called this the only such point, and that was not true**
     * (A25R) -- but they arrive again and again, and an arm that is re-set every
     * few seconds never runs out. Armed on the take-file message instead --
     * after the click has already gone -- the platform's own server is being
     * raced, and losing that race is Chrome's Save-as window going up on a
     * seller nobody is watching. */
    watching.expectAFile();
    return { secret: await armTheCatcher(chrome, { tabId, secret: secret() }) };
  }
  if (asked.do === 'take-file') {
    const held = await takeTheFile(chrome, watching, {
      patienceSeconds: asked.patience, fetch: (...args) => fetch(...args),
    });
    /* **A LIST OF NUMBERS, because a message carries nothing else.** The page
     * half turns it back into bytes. */
    return held ? { bytes: [...held] } : null;
  }
  say(asked.line);
  return { said: true };
}

/**
 * Wire the worker up.
 *
 * **EVERY LISTENER IS ADDED AT THE TOP LEVEL, and the clock is checked on the
 * way past.** The documentation is explicit that handlers "should be at the top
 * level of the script and not be nested inside functions" -- one registered
 * inside a function does not exist until something calls that function, and
 * after a restart nothing has.
 *
 * It is a function only so that a check can call it against a stand-in Chrome.
 * The real worker calls it once, at the top of the file, with nothing in
 * between.
 */
export function wireUp(chrome, { onDue, answer = null }) {
  /* **THE PAGE HALF'S ONE WAY BACK.** Registered at the top level like every
   * other listener, because a listener added inside a function does not exist
   * until something calls that function -- and after a restart nothing has. */
  if (answer) {
    chrome.runtime.onMessage.addListener((asked, from, reply) => {
      const coming = answer(asked, from);
      if (!coming) return false;
      coming.then(reply).catch((wrong) => reply({ wrong: String((wrong && wrong.message) || wrong) }));
      /* Answering later is what this true means. Left off, Chrome closes the
       * channel the moment this returns and the answer is thrown away. */
      return true;
    });
  }
  chrome.runtime.onInstalled.addListener(() => makeSureTheClockIsSet(chrome));
  chrome.runtime.onStartup.addListener(() => makeSureTheClockIsSet(chrome));
  chrome.alarms.onAlarm.addListener(async (alarm) => {
    /* **THE CLOCK IS PUT BACK EVEN HERE.** An alarm firing proves it existed a
     * moment ago and proves nothing about the next one -- an update between now
     * and tomorrow clears it, and this is the last moment anything is listening.
     */
    await makeSureTheClockIsSet(chrome);
    if (alarm && alarm.name !== DAILY) return;
    await onDue();
  });

  /* **AND ON THE WAY PAST, EVERY SINGLE TIME THIS WORKER WAKES.** This is the
   * one that catches an alarm cleared while Chrome was running, which is the
   * case neither event above covers and the one that leaves it idle for ever. */
  return makeSureTheClockIsSet(chrome);
}
