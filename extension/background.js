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
import { ARMED_FOR_MS, aTabToWalkIn, goTo } from './doors.js';
import { FAILED } from './walk.js';
import { carryTheNightOn } from './nightly.js';

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

/* The one name the keeping-awake alarm has. */
export const STAY_AWAKE = 'kartaan-autosync-awake';

/* How often it fires, in minutes. **TWO, WHICH IS THE REFERENCE'S NUMBER**, and
 * comfortably above the half minute Chrome refuses to honour. */
export const EVERY_TWO_MINUTES = 2;

/**
 * Make sure something wakes this worker regularly, whatever else has happened.
 *
 * **WHAT THIS IS FOR, SAID EXACTLY, BECAUSE IT IS EASY TO BELIEVE IT DOES MORE
 * THAN IT DOES:**
 *
 * `makeSureTheClockIsSet` is asked every time this worker starts, which is the
 * right shape -- **but nothing starts a worker that nothing is waking.** If the
 * daily alarm is cleared while Chrome is running, the one thing that would have
 * woken this worker tomorrow is the thing that is gone, so the check that would
 * have put it back never runs. That is the nine-day outage, and the current
 * shape narrows it rather than closing it. An alarm every two minutes closes it:
 * whatever else happens, something wakes this worker, and waking is when the
 * daily alarm is put back.
 *
 * **WHAT IT DOES NOT DO, and this matters more than what it does.** It does NOT
 * keep the worker alive. Chrome still shuts it down after thirty seconds of
 * quiet; this only means it is started again soon. **So anything held in a
 * variable is still lost between walks' steps** -- including the armed
 * download-cancel in `doors.js`, which has to be a variable because the cancel
 * must happen with no `await` in front of it. That hole is real, it is not this,
 * and pretending this closes it would be worse than leaving it open.
 */
export async function makeSureTheWorkerIsWoken(chrome) {
  const already = await chrome.alarms.get(STAY_AWAKE);
  if (already) return false;
  await chrome.alarms.create(STAY_AWAKE, {
    periodInMinutes: EVERY_TWO_MINUTES,
    persistAcrossSessions: true,
  });
  return true;
}

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

/* ------------------------------------------------- the walk that outlives its page */

/* What the walk in flight is called in storage.
 *
 * **A WALK NO LONGER FITS IN ONE PAGE, AND THAT IS CHROME'S RULE RATHER THAN A
 * CHOICE (D200).** The walk runs inside the portal's own page, because a service
 * worker is shut down after thirty seconds and a Meesho orders export takes five
 * minutes. But the walk's first step is to GO somewhere, and going somewhere
 * destroys the page that asked. Three walks died on his own Meesho panel on
 * 5 September with "the message channel closed before a response was received",
 * which is what that teardown looks like from this side.
 *
 * **SO THE PLACE IN THE WALK LIVES HERE, IN STORAGE, WHICH IS THE ONE THING
 * THAT SURVIVES BOTH THE PAGE AND THIS WORKER.** The page that Chrome draws next
 * asks for it and carries on. The reference has answered it this way for months:
 * its content script announces itself on every page load and asks the background
 * which job it is on, and the job lives in the background, never in the page. */
export const THE_WALK = 'kartaan-autosync-walk';

/* How long a walk in flight is still believed, in milliseconds.
 *
 * **THE SAME NUMBER AS THE DOWNLOAD-CANCEL'S, TAKEN FROM IT RATHER THAN WRITTEN
 * AGAIN.** They bound the same thing -- how long one walk may go on -- and two
 * copies of one number is how they come to disagree without anybody noticing.
 *
 * **AND IT HAS TO RUN OUT.** A tab the seller closes mid-walk, or a page that
 * never draws, would otherwise leave a record here for ever -- and the next
 * portal page that happened to open with that same tab number would pick up a
 * walk from some earlier night and start clicking. */
export const A_WALK_LASTS_MS = ARMED_FOR_MS;

/**
 * Start a walk, and write where it is before anything can tear the page down.
 *
 * **WRITTEN DOWN FIRST, for the same reason the run is.** A place recorded after
 * the navigation is a place recorded after the page that would have recorded it
 * has already gone.
 */
export async function beginTheWalk(chrome, { tabId, at = 0, startedAt = Date.now(), ...rest }) {
  const walk = { tabId, at, carryOnUntil: startedAt + A_WALK_LASTS_MS, answer: null, ...rest };
  await chrome.storage.local.set({ [THE_WALK]: walk });
  return walk;
}

/**
 * The walk this page should carry on, or nothing.
 *
 * **REFUSED FOR ANY OTHER TAB, AND FOR ONE THAT HAS RUN OUT OF TIME.** Every
 * portal page the seller opens asks this question -- it is a manifest content
 * script, it runs on all of them -- so answering loosely means an ordinary page
 * the seller opened themselves starts clicking through a report.
 */
export async function theWalkInFlight(chrome, { tabId, at = Date.now(), pickingItUp = false }) {
  const held = await chrome.storage.local.get(THE_WALK);
  const walk = held[THE_WALK] || null;
  if (!walk) return null;
  if (walk.tabId !== tabId) return null;
  if (walk.answer) return null;
  if (at >= walk.carryOnUntil) return null;
  /* **A PAGE TAKING IT UP SAYS WHICH STEP IT TOOK UP, AND THAT IS NOT
   * BOOKKEEPING (see the `go` below).** It is the only thing that can tell "the
   * page never drew" apart from "the page drew, carried on walking, and is still
   * loading the last advert".
   *
   * **THE STEP, NOT THE TIME.** Two readings of the clock a few lines apart come
   * back with the same millisecond on any quick machine, so a comparison of
   * times answers "no" to something that really did happen -- which fails in the
   * direction that kills a good walk. The step number cannot tie. */
  if (pickingItUp) {
    await chrome.storage.local.set({ [THE_WALK]: { ...walk, pickedUpFrom: walk.at } });
  }
  return walk;
}

/**
 * Move the place on, and say nothing else about it.
 *
 * **CALLED WHILE THE PAGE IS STILL THERE AND BEFORE IT IS SENT ANYWHERE.** This
 * is the one ordering in the whole file that cannot be got wrong: written
 * afterwards, the page is already gone and there is nothing left to write it.
 */
export async function theWalkMovedOn(chrome, { tabId, at }) {
  const held = await chrome.storage.local.get(THE_WALK);
  const walk = held[THE_WALK] || null;
  if (!walk || walk.tabId !== tabId) return null;
  const moved = { ...walk, at };
  await chrome.storage.local.set({ [THE_WALK]: moved });
  return moved;
}

/**
 * End the walk, whatever ended it, and leave the answer behind.
 *
 * **THE ONLY WAY OUT, and it always writes** -- the same shape as `endTheRun`
 * and for the same reason. The page that finished the walk is about to be
 * forgotten; if the answer is not written here it is not written anywhere.
 */
export async function endTheWalk(chrome, { tabId, answer, at = Date.now() }) {
  const held = await chrome.storage.local.get(THE_WALK);
  const walk = held[THE_WALK] || null;
  if (!walk) return null;
  if (tabId !== undefined && walk.tabId !== tabId) return null;
  const ended = { ...walk, answer: answer || null, finishedAt: at };
  await chrome.storage.local.set({ [THE_WALK]: ended });
  return ended;
}

/**
 * Start one report's walk in a tab, and hand it to the page half.
 *
 * **THE BOOKS ARE OPENED BEFORE THE PAGE IS TOLD ANYTHING, and that ordering is
 * the same one as `go`'s.** The walk's very first step is a `go`, so the page
 * that is being asked to start may be destroyed within a second of hearing. If
 * the record is not already written by then, `go` has nothing to move on, the
 * next page asks where the walk was and is told nothing, and the walk is over
 * before it began -- which reads exactly like the fault this all exists to fix.
 *
 * **AND THE ANSWER IS NOT AWAITED, because it is not coming.** The message that
 * starts a walk is replied to by a page that will be gone. Where the walk got to
 * is read back out of the record, which is why the record exists.
 */
export async function startAWalk(chrome, {
  reportId, dataDate, openAt, patience = 30,
  /* Handed in only so a check can stand at the moment the page is sent
   * anywhere and read what was already written down. Everything else in this
   * file takes `chrome` the same way and for the same reason. */
  go = goTo,
  ...rest
}) {
  if (!openAt) {
    /* **NAMED RATHER THAN GUESSED.** Which portal page a report's walk starts
     * from is the recipe's business, not this file's -- this half knows no
     * platform and must not learn one. */
    throw new Error('A walk has to be told which portal page to start from.');
  }

  /* **THE TAB IS OURS, NOT WHICHEVER ONE SOMEBODY HAPPENED TO HAND OVER, and
   * that is the difference between this working at two in the morning and
   * not.** Chrome throttles a tab's timers when a different tab is selected in
   * that tab's window, or when that window is minimised -- **not** when the
   * screen is unattended and nobody is looking. A tab in the seller's own window
   * is, at night, one of many unselected tabs, and every wait in the walk is
   * stretched: the reference measured a fifteen-second wait taking nine minutes.
   * `aTabToWalkIn` answers with the only tab of a window of our own, unfocused
   * and not minimised. */
  const tab = await aTabToWalkIn(chrome, { address: 'about:blank' });
  if (!tab || tab.id === undefined) {
    throw new Error('There is nowhere to walk: no tab could be opened.');
  }

  /* **THE BOOKS ARE OPENED BEFORE THE PAGE EXISTS, not merely before it is told
   * anything.** The page asks for its walk the moment it loads. Written after,
   * the page has already asked and been told nothing, and the walk is over
   * before it began.
   *
   * **AND THAT IS WHY THE TAB IS OPENED BLANK FIRST.** Opened straight at the
   * portal it would start loading while this line was still being written, and
   * which of the two won would depend on the night. */
  const walk = await beginTheWalk(chrome, { tabId: tab.id, reportId, dataDate, ...rest });

  /* **NOTHING IS PUSHED AT THE PAGE. THE PAGE ASKS.** An earlier version of this
   * sent the page a `walk` message the instant the tab was made -- at a blank
   * page, where our own half is not running and nothing was listening. The
   * reference has never done it that way: its content script announces itself on
   * every page load and asks the background which job it is on. **One way in,
   * used by the first page and by every page after it**, rather than a special
   * path for the first that only the first can get wrong. */
  await go(chrome, { tabId: tab.id, address: openAt, patienceSeconds: patience });
  return walk;
}

/**
 * Write down a walk that nobody is ever going to finish.
 *
 * **UNTIL THIS EXISTED, NOTHING ANYWHERE TURNED AN ABANDONED WALK INTO A
 * RECORDED FAILURE (A26R3).** A walk's answer was only ever written by the page
 * saying `walk-done` or by the tab being closed. If the page could not speak at
 * all -- the message failing, the worker gone, the page torn down between two
 * lines -- the record simply sat there saying nothing. Past its fifteen minutes
 * `theWalkInFlight` stopped handing it back, and that was the end of it: no
 * answer, no line, no report, and nothing anywhere saying why.
 *
 * **THAT IS THE FAULT `background.js` OPENS BY NAMING** -- "a run that was
 * interrupted wrote nothing down" -- arriving by a door nobody had watched.
 *
 * **IT HANGS OFF THE ALARM THAT WAKES THIS WORKER EVERY TWO MINUTES**, which is
 * the only thing that reliably happens when nothing else is happening. That is
 * the second job that alarm now does, and it is the more useful one.
 */
export async function sweepUpAnAbandonedWalk(chrome, { at = Date.now() } = {}) {
  const held = await chrome.storage.local.get(THE_WALK);
  const walk = held[THE_WALK] || null;
  if (!walk || walk.answer) return null;
  if (at < walk.carryOnUntil) return null;
  return endTheWalk(chrome, {
    tabId: walk.tabId,
    at,
    answer: {
      state: FAILED,
      reportId: walk.reportId || null,
      dataDate: walk.dataDate || null,
      /* **SAID AS WHAT IT IS.** "It stopped and never said why" is a different
       * problem from any of the named ones, and reporting it as one of those
       * would send somebody to look at the portal. */
      say: 'This report stopped part way through and never said what happened. '
        + 'Nothing has been written for it, and the run gave up waiting.',
      pageWas: '',
    },
  });
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
export const KNOWN = ['go', 'arm-the-catcher', 'take-file', 'say', 'resume?', 'walk-done'];

async function carryOut(chrome, parts, asked, tabId) {
  const { goTo, takeTheFile, watching, say, secret } = parts;
  if (asked.do === 'resume?') {
    /* **EVERY PORTAL PAGE THE SELLER OPENS ASKS THIS**, because the page half is
     * a manifest content script and runs on all of them. Almost every answer is
     * nothing, and nothing is the safe answer: the alternative is an ordinary
     * page somebody opened themselves starting to click through a report. */
    return { walk: await theWalkInFlight(chrome, { tabId, pickingItUp: true }) };
  }
  if (asked.do === 'walk-done') {
    /* **THE ANSWER COMES BACK AS ITS OWN MESSAGE, NOT AS A REPLY.** A walk spans
     * several pages now, so the reply to the message that STARTED it went down
     * with the first page -- which is exactly the "message channel closed before
     * a response was received" seen three times on his own panel.
     *
     * **AND ONLY THE PAGE THAT CURRENTLY HAS THE WALK MAY END IT. THIS IS NOT
     * TIDINESS -- IT IS A FAULT HIS OWN CHROME REPORTED WHILE THIS WAS BEING
     * BUILT:** "The page keeping the extension port is moved into back/forward
     * cache, so the message channel is closed."
     *
     * A page the walk has LEFT is not always destroyed. Chrome may put it in the
     * back/forward cache instead -- frozen, not gone -- with its `go` message
     * still half-said. If anything ever thaws it (the seller pressing Back is
     * enough), that message fails, the walk in that old page throws, and the old
     * page reports a FAILURE for a walk that a newer page is running perfectly.
     * The day's report would be recorded as broken while it was in fact being
     * fetched.
     *
     * **SO EVERY PAGE SAYS WHICH STEP IT PICKED THE WALK UP AT, and only the
     * page whose number still matches is heard.** */
    const held = await theWalkInFlight(chrome, { tabId });
    if (held && asked.from !== undefined && Number(held.pickedUpFrom || 0) !== Number(asked.from)) {
      return { ended: false, stale: true };
    }
    watching.stopExpecting();
    const ended = Boolean(await endTheWalk(chrome, { tabId, answer: asked.answer }));
    /* **THE NIGHT IS MOVED ON THE MOMENT A WALK ENDS**, rather than waiting up
     * to two minutes for the alarm. The alarm is the safety net, not the
     * mechanism. */
    if (ended && parts.carryOn) await parts.carryOn();
    return { ended };
  }
  if (asked.do === 'go') {
    watching.forget();
    /* **THE PLACE IS HANDED OVER BEFORE THE PAGE IS SENT ANYWHERE, and this
     * ordering is the whole of D200.** The line below destroys the page that
     * asked for it. Written after, there is no page left to write it, no page
     * asks where the walk was, and the walk stops for ever -- silently, at
     * night, with nobody watching. */
    if (asked.at !== undefined) await theWalkMovedOn(chrome, { tabId, at: asked.at });
    try {
      await goTo(chrome, { tabId, address: asked.address, patienceSeconds: asked.patience });
    } catch (wrong) {
      /* **A PAGE THAT NEVER DRAWS ENDS THE WALK HERE, because there is nobody
       * else left to end it.** The page that asked is already gone, so throwing
       * this at its caller throws it at nothing: the walk would simply never be
       * picked up again and would sit in storage until its time ran out, with no
       * word anywhere of what went wrong.
       *
       * **UNLESS A PAGE HAS ALREADY TAKEN THE WALK UP, AND THAT IS NOT A CORNER
       * -- IT IS AN ORDINARY SLOW NIGHT.** "The page finished drawing" means
       * Chrome finished fetching EVERYTHING on it, adverts and trackers
       * included. The page half runs long before that, at `document_idle`, so on
       * a heavy portal the walk can be several steps along while Chrome still
       * calls the tab busy. Ending the walk here on that timer would kill a walk
       * that is working perfectly -- and it would only ever happen on a slow
       * connection, at night, never once while somebody was watching. */
      const since = await chrome.storage.local.get(THE_WALK);
      const now = since[THE_WALK];
      if (now && now.tabId === tabId && now.pickedUpFrom === asked.at) throw wrong;
      await endTheWalk(chrome, {
        tabId,
        answer: {
          state: FAILED,
          reportId: (asked.reportId || null),
          dataDate: (asked.dataDate || null),
          say: wrong.message,
          pageWas: '',
        },
      });
      throw wrong;
    }
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
export function wireUp(chrome, { onDue, answer = null, whenATabGoes = null, carryOn = null }) {
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
  /* **A TAB THAT IS CLOSED MID-WALK ENDS THE WALK, and says so.** A walk lives
   * across several pages now, so the seller closing the tab is not a small thing
   * -- nothing will ever ask where that walk was again. Without this it is a
   * silent hang: the record sits in storage saying "running" until its time runs
   * out, and the day's report is simply missing with no line anywhere saying
   * why. **And the download-cancel stays armed**, so the next file the seller
   * downloaded by hand would vanish in front of them. */
  if (chrome.tabs && chrome.tabs.onRemoved) {
    chrome.tabs.onRemoved.addListener(async (tabId) => {
      const walk = await theWalkInFlight(chrome, { tabId });
      if (!walk) return;
      if (whenATabGoes) whenATabGoes();
      await endTheWalk(chrome, {
        tabId,
        answer: {
          state: FAILED,
          reportId: walk.reportId || null,
          dataDate: walk.dataDate || null,
          say: 'The tab this report was being fetched in was closed before the walk finished.',
          pageWas: '',
        },
      });
    });
  }
  chrome.runtime.onInstalled.addListener(() => bothClocks(chrome));
  chrome.runtime.onStartup.addListener(() => bothClocks(chrome));
  chrome.alarms.onAlarm.addListener(async (alarm) => {
    /* **THE CLOCK IS PUT BACK EVEN HERE.** An alarm firing proves it existed a
     * moment ago and proves nothing about the next one -- an update between now
     * and tomorrow clears it, and this is the last moment anything is listening.
     */
    await bothClocks(chrome);
    /* **AND ON EVERY WAKING, NOT ONLY THE DAILY ONE.** A walk nobody is going to
     * finish has to be written down by something, and this is the only thing
     * that happens when nothing else is happening. */
    await sweepUpAnAbandonedWalk(chrome);
    /* **AND THE NIGHT IS MOVED ON HERE TOO, not only when a walk says it is
     * done.** A night that could only advance on one message is a night that
     * stalls for ever the one time that message does not arrive -- and nobody is
     * awake to notice. This is the only thing that reliably happens when nothing
     * else is happening. */
    if (carryOn) await carryOn();
    if (alarm && alarm.name !== DAILY) return;
    await onDue();
  });

  /* **AND ON THE WAY PAST, EVERY SINGLE TIME THIS WORKER WAKES.** This is the
   * one that catches an alarm cleared while Chrome was running, which is the
   * case neither event above covers and the one that leaves it idle for ever. */
  return bothClocks(chrome);
}

/** Both alarms, asked for together. **Written once**: two places asking for one
 *  of them and not the other is how the missing one goes unnoticed. */
async function bothClocks(chrome) {
  const daily = await makeSureTheClockIsSet(chrome);
  const awake = await makeSureTheWorkerIsWoken(chrome);
  return daily || awake;
}
