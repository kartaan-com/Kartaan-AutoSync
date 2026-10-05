/* The background, started.
 *
 * **DELIBERATELY ALMOST EMPTY, and the emptiness is the point.** Chrome's own
 * documentation says event handlers "should be at the top level of the script and
 * not be nested inside functions", because a handler registered inside a function
 * does not exist until something calls that function -- and after a restart,
 * nothing has. So the wiring happens here, at the top, with nothing in between.
 *
 * Everything that could be wrong is in `background.js` and `doors.js`, which are
 * checked against a stand-in Chrome with no browser anywhere. This has no checks
 * of its own for the same reason `content.js` has none: what is left is wiring,
 * and wiring is proved by loading it.
 */

import {
  DAILY, THE_PANEL, THE_WALK, aFreshSecret, answerThePage, answerThePanel, setTheHour, startAWalk,
  theHourItRuns, whyThatIsNotATimeOfDay, wireUp,
} from './background.js';
import {
  RECHECK_ALARM, carryTheNightOn, clearNamedNeedsYouEntries, howTheNightWent, setTheRecheckClock,
  startTheNight, theDay, theNight, theRecheckSync, theRunLog, whatIsBeingRechecked, whatIsPaused,
  whatNeedsYou,
} from './nightly.js';
import { goTo, routeInThePage, takeTheFile, watchForDownloads } from './doors.js';
import {
  aDriveToken, aWayOfAsking, addARowTo, landTheFile, recordWhatLanded, theKartaanFolder,
} from './drive.js';
import { aFreshInstallId, theLinesFor, theRecordNameFor } from './record.js';
import {
  THE_PANEL_ASKS, alreadyCarriedOn, answerThePanelsQuestion, markCarriedOn, releaseCarriedOn, rememberTheNight,
  startASync, startTheNextPlatform, startTheScheduledSync, theSetup, theSignInAlert, theSyncSummary,
} from './screen.js';

/* **THE CLOCK IS SET ON THE WAY PAST, EVERY TIME THIS WAKES.** Google's own
 * words: "it is best to make sure important alarms exists each time your service
 * worker starts up." That is stronger than the two lifecycle events, and the
 * difference is the whole of the nine days nothing ran -- neither of them fires
 * when an alarm is cleared while Chrome is running. */
/* **THE WATCHING STARTS WHEN THIS WORKER DOES, at the top level like every
 * listener.** A download tells Chrome about itself once, at the moment it
 * begins; started later, the address is already gone and the only way back to it
 * is the long way round, which arrives at nothing on a `blob:` address. */
const watching = watchForDownloads(chrome);

/* **THE ONE HANDLE, AND IT IS HOW A WALK IS STARTED BY HAND UNTIL THE QUEUE
 * EXISTS.** Until `onDue` has a queue behind it, nothing in this product starts
 * a walk, so nothing could ever be run against a real portal -- and a thing that
 * has never done its job is not a thing anybody should be asked to review.
 *
 * **IT IS NOT A WAY IN FOR ANYTHING.** A service worker's own global is not
 * reachable from a web page, from a content script, or from another extension.
 * The only thing that can see this is the DevTools console of this extension's
 * own worker, which is to say the person whose browser it is.
 *
 * **AND IT CARRIES THE SELLER'S OWN PANEL NAME UNLESS IT IS TOLD ONE.** This is
 * the handle every live run of this product has so far been started by, and it
 * took three arguments, none of them the panel -- so a Meesho report started
 * this way failed with "this report needs the seller's own panel name" however
 * carefully the name had been saved on the page. A handle that fails for a
 * reason the product has already solved teaches the wrong lesson at two in the
 * morning. An explicit `panel` still wins, because a person typing one here has
 * said what they mean. */
self.startAWalk = async (how) => startAWalk(chrome, {
  panel: (await theSetup(chrome)).panel, ...how,
});

/* **HOW A NIGHT IS MOVED ON, wired once here and handed to everything that could
 * mean a walk is over.** It reads the walk and the night back out of storage
 * every time, so being called by three different things costs nothing and being
 * called too often is a no-op. */
const carryOn = async () => {
  const moved = await carryTheNightOn(chrome, theNightsParts);
  /* **A FINISHED NIGHT IS FILED HERE, NOT ONLY WHEN SOMEBODY OPENS THE PANEL.**
   * `THE_NIGHT` holds one night and the next one writes over it -- so a night
   * that finished while nobody was looking would leave no trace at all, and the
   * panel could never say which platforms have run and which never have. This is
   * the only thing that runs after every night whether or not anybody is
   * watching. This filing is for the LEDGER (Flipkart's daily count) and is
   * meant to be called by anybody, any number of times -- `howItStands` also
   * calls it, on every panel poll. */
  await rememberTheNight(chrome, { book: theBook });
  /* **AND ITS LOG GOES TO THE SELLER'S DRIVE, ONCE -- ON ITS OWN "ONCE",
   * NEVER THE LEDGER'S (A53; Job 7, A64, 2026-09-23).** The ledger's "filed"
   * flag above can be spent by a panel poll that wins the race against this
   * very call, which used to leave this whole block silently skipped -- no
   * log, no end-of-sync notice, no next platform. `alreadyCarriedOn` is set by
   * nothing but this function, so the panel being open can never swallow it. A
   * Drive that refuses is said in the console and stops nothing. */
  const doneNight = await theNight(chrome);
  if (!(await alreadyCarriedOn(chrome, doneNight))) {
    await markCarriedOn(chrome, doneNight);
    try {
      await followTheNightThrough(doneNight);
    } catch (wrong) {
      /* **THE CLAIM IS GIVEN BACK** so the next wake tries the rest again -- the follow-through is safe to repeat
       * (the log replaces itself, a notification has a fixed id, the next platform only starts when none is going). */
      await releaseCarriedOn(chrome, doneNight);
      throw wrong;
    }
  }
  return moved;
};

const followTheNightThrough = async (doneNight) => {
  {
    const log = theRunLog(doneNight);
    try {
      if (log) {
        await putOneFileAway({
          reportId: log.reportId, fileName: log.fileName, body: new TextEncoder().encode(log.text),
        });
      }
    } catch (wrong) {
      console.warn('Kartaan Auto-sync: the run log could not be put in Drive.', wrong);
    }
    /* **AND ANY REPORT NOT READY YET IS CHECKED AGAIN IN AN HOUR (A53).** */
    await setTheRecheckClock(chrome);
    /* **A SYNC PAUSED FOR A SIGN-IN SAYS SO WHERE HE WILL SEE IT (A53, his ruling;
     * Rumee's "Login Required" notification).** It stays until he acts on it. */
    const paused = await whatIsPaused(chrome);
    const ended = await theNight(chrome);
    if (paused && ended && paused.at === ended.finishedAt) {
      const alert = theSignInAlert(await theBook(), paused);
      if (alert && chrome.notifications) {
        chrome.notifications.create(`kartaan-sign-in-${paused.at}`, {
          type: 'basic', iconUrl: chrome.runtime.getURL(THE_ICON), title: alert.title,
          message: alert.message, requireInteraction: true, priority: 2,
        }, () => {
          if (chrome.runtime.lastError) {
            console.warn('Kartaan Auto-sync: Chrome refused the sign-in notification.',
              chrome.runtime.lastError.message);
          }
        });
      }
      /* **AND THE PANEL IS PUT IN FRONT OF HIM, WHICH IS THE PART THAT CANNOT BE
       * SILENCED.** His ruling: the alert must "grab the user's attention". A
       * notification is at the mercy of Windows -- switched off for Chrome, or
       * held back by Focus Assist -- and a sync that is waiting for a person is
       * waiting for ever if that person is never told. The panel says it in full,
       * with the Resume button, and a window is a thing nobody can miss. */
      await showThePanel();
    }
    /* **AND EVERY FINISHED SYNC SAYS HOW IT WENT -- RUMEE'S "SYNC COMPLETE" (A53).**
     * A sync stopped for a sign-in already has its own alert above. */
    const summary = theSyncSummary(ended);
    if (summary && chrome.notifications && !(paused && ended && paused.at === ended.finishedAt)) {
      chrome.notifications.create(`kartaan-sync-${ended.startedAt}`, {
        type: 'basic', iconUrl: chrome.runtime.getURL(THE_ICON), title: summary.title,
        message: summary.message, priority: 1,
      }, () => {
        if (chrome.runtime.lastError) {
          console.warn('Kartaan Auto-sync: Chrome refused the end-of-sync notification.',
            chrome.runtime.lastError.message);
        }
      });
    }
    /* **THE NEXT PLATFORM OF THE SCHEDULED SYNC STARTS WHEN THIS ONE IS FILED.**
     * When nothing is left to start, the scheduled sync has ended -- here. The
     * server's "I am done" call belongs at this point and is A51's (Control's
     * ruling); it is not built in this session. */
    const next = await startTheNextPlatform(chrome, {
      book: await theBook(), startTheNight, carryOn,
    });
    if (next.refused.length) {
      console.warn('Kartaan Auto-sync: part of the scheduled sync could not start.', next.refused);
    }
  }
};

const theNightsParts = {
  theWalkNow: async () => {
    /* **THE NAME COMES FROM THE ONE PLACE IT IS DEFINED.** Spelt again here it
     * is a second record of one fact, and the day one of them changes the night
     * silently stops noticing that any walk ever finished. */
    const held = await chrome.storage.local.get(THE_WALK);
    return held[THE_WALK] || null;
  },
  endTheWalkNow: async () => chrome.storage.local.remove(THE_WALK),
  /* **THE SELLER'S OWN PANEL NAME USED TO BE PUT IN ON THIS LINE, AND IT IS NOW
   * THE NIGHT'S.** All five Meesho recipes carry `{panel}` in an address and
   * `walk.js` refuses a step carrying one without it, in words -- so this one
   * line was the whole of whether a Meesho report could be fetched at all.
   *
   * **THIS FILE HAS NO CHECKS BY DESIGN, so nothing anywhere could go red if it
   * were wrong or missing.** It is carried by the night now (`startTheNight`),
   * which `nightly.test.js` and `screen.test.js` both drive -- the same reason
   * `content.js` keeps its refusals in `walk.js`: a decision does not belong in
   * a file nothing can prove. What is left here is wiring. */
  startAWalk: async (how) => startAWalk(chrome, how),
};

/* **THE TWO HANDLES A NIGHT IS RUN AND READ BY, until there is a screen for
 * it.** Same reasoning as `startAWalk` above: a service worker's own global is
 * not reachable from a web page, a content script, or another extension -- the
 * only thing that can see these is the DevTools console of this extension's own
 * worker, which is to say the person whose browser it is.
 *
 * **AND THIS ONE CARRIES THE PANEL NAME TOO, FOR THE SAME REASON AND TO KEEP A
 * PATH THAT ALREADY WORKED.** While the join lived in the wiring below, a night
 * started from this console got the seller's own name whatever it was told;
 * now that the night carries it, a night started here with no name would reach
 * every Meesho walk with none. That would be this change breaking the one way
 * this product has actually been run. What is typed still wins. */
self.startTheNight = async (how) => {
  const night = await startTheNight(chrome, { panel: (await theSetup(chrome)).panel, ...how });
  await carryOn();
  return night;
};
self.howTheNightWent = async () => howTheNightWent(await theNight(chrome));

/* **CLEARING A NAMED "NEEDS YOU" ENTRY BY HAND, THE SAME KIND OF HANDLE AND FOR
 * THE SAME REASON (Job 7, A64, 2026-09-23).** This is his record; the ordinary
 * way off it is a later sync landing the day for real. `clearNamedNeedsYouEntries`
 * refuses to touch anything not named, so this console handle can only ever
 * clear exactly what he said yes to -- never "everything", never a whole report. */
self.clearNamedNeedsYouEntries = async (entries) => clearNamedNeedsYouEntries(chrome, entries);
self.whatNeedsYou = async () => whatNeedsYou(chrome);

/* **AND THE ONE THING A PERSON HAS TO DO ONCE, AWAKE.** Every other ask for a
 * Drive token in this extension asks Chrome for the seller's permission QUIETLY,
 * because a night runs with nobody watching and an account-chooser at two in
 * the morning waits for ever.
 * **But a permission that has never been granted cannot be had quietly at all**,
 * so without this the wiring is complete and the first file can never land: the
 * run would say "the seller's Drive is not connected" every night, for ever,
 * correctly and uselessly.
 *
 * **IT IS A HANDLE, NOT A WAY IN**, exactly like `startAWalk` and
 * `startTheNight` above and for the same reason: a service worker's own global
 * is not reachable from a web page, from a content script, or from another
 * extension. The only thing that can see it is the DevTools console of this
 * extension's own worker -- which is to say the person whose browser it is.
 *
 * **AND IT IS THE ONLY INTERACTIVE ASK IN THE WHOLE EXTENSION.** Connecting a
 * Drive is something somebody does once, on purpose, looking at the screen. A
 * proper onboarding screen is its own piece of work; this is what stands in for
 * it until there is one, and it is written down as that rather than left as a
 * hole nobody meets. */
self.connectTheDrive = async () => aDriveToken(chrome, { interactive: true });

/* **THE ONE PLACE `drive.js` IS ACTUALLY CALLED, and until this line there was
 * none.** It is 24 KB, 66 checks, finished and proved against a stand-in Drive
 * -- and it was imported by nothing but its own test file. So no report the
 * browser fetched has ever reached a real Google Drive, and **that is why a
 * seller who had set everything up correctly would still see Amazon and nothing
 * else**: `me_orders` and `fk_orders` come through here, and the nightly run
 * was reading folders the browser had never put anything in.
 *
 * **QUIETLY, NEVER INTERACTIVELY.** A night runs with nobody watching. Asked
 * interactively, Chrome puts up an account-chooser and waits for ever -- the
 * same unattended hang as a Save-as window, by a different door. With no
 * permission to be had quietly this says the Drive is not connected and the
 * report fails, which is a sentence somebody can act on in the morning.
 *
 * **AND THE `Kartaan` FOLDER IS FOUND OR MADE HERE, ONCE PER FILE.**
 * Under `drive.file` this extension can only ever see files it made itself, so
 * there is nothing to keep and nothing anybody has to paste in. */
const putOneFileAway = async ({ reportId, fileName, body }) => {
  const ask = aWayOfAsking(chrome, { fetch: (...args) => fetch(...args) });
  const layout = await theLayout();
  const inside = await theKartaanFolder(chrome, ask, layout);
  const landed = await landTheFile(chrome, ask, { reportId, fileName, inside, body, layout });
  /* **WRITTEN DOWN IN THE EXTENSION'S OWN RECORD (job 38)** -- only for a report, never for the night log. */
  if (reportId !== THE_NIGHT_LOG) {
    await writeItDown(ask, layout, inside, theLinesFor({
      reportId,
      fileName: landed.name || fileName,
      size: Number(landed.size) || (body ? body.length : 0),
      on: theDay(Date.now()),
    }));
  }
  return landed;
};

/** This install's own id, made once and kept, so its record is the only file it ever writes (Control, 2026-10-05). */
const THE_INSTALL_ID = 'kartaan-install-id';
const theInstallId = async () => {
  const held = (await chrome.storage.local.get(THE_INSTALL_ID))[THE_INSTALL_ID];
  if (typeof held === 'string' && /^[0-9a-f]{8}$/.test(held)) return held;
  const made = aFreshInstallId();
  await chrome.storage.local.set({ [THE_INSTALL_ID]: made });
  return made;
};

/** What the night log is called to the layout. Not a report, so it has no line in the record. */
const THE_NIGHT_LOG = 'run_log';

/* **THE RECORD IS WRITTEN ONE AT A TIME, AND A FAILURE TO WRITE IT NEVER FAILS THE LANDING.** The file is
 * already in the seller's Drive; a walk reported as failed because a bookkeeping line would not go in would
 * be refetched and burn a Flipkart request for nothing. The failure is said where a person can see it. Only
 * this worker writes this file, so serialising here is all that is needed to keep two landings from reading
 * the same standing record and each writing back without the other's line. */
let theRecordQueue = Promise.resolve();
const writeItDown = (ask, layout, inside, lines) => {
  theRecordQueue = theRecordQueue
    .then(async () => recordWhatLanded(chrome, ask, {
      layout, inside, lines, fileName: theRecordNameFor(await theInstallId()),
    }))
    .catch((wrong) => {
      // eslint-disable-next-line no-console
      console.warn(`What landed could not be written in the extension's own record: ${wrong && wrong.message}`);
    });
  return theRecordQueue;
};

/* **AND THE OTHER WAY A DAY REACHES A DRIVE: one row added to a running list.**
 * Same door, same folder, same quiet permission -- the only difference is that
 * there is no file to fetch. Meesho sells no export of the day's views. */
const addOneRow = async ({ reportId, fileName, header, row, forTheDay }) => {
  const ask = aWayOfAsking(chrome, { fetch: (...args) => fetch(...args) });
  const layout = await theLayout();
  const inside = await theKartaanFolder(chrome, ask, layout);
  const added = await addARowTo(chrome, ask, { reportId, fileName, inside, header, row, forTheDay, layout });
  /* **A RUNNING LIST IS RECORDED PER DAY BY LOOKING INSIDE IT** -- the days the file now holds, not the day
   * it was last touched (the old extension did exactly this). */
  await writeItDown(ask, layout, inside, theLinesFor({
    reportId, fileName, size: added.size, days: added.days, on: theDay(Date.now()),
  }));
  return added;
};

/* **THE RECIPE BOOK, READ OUT OF THE EXTENSION'S OWN FILE.** The page half
 * already reads it exactly this way. It is read again on every wake rather than
 * held, because Chrome shuts this worker down after thirty seconds of quiet and
 * anything held in a variable is gone -- reading a local file is cheap and
 * believing a stale one is not. */
let bookInHand = null;
const theBook = async () => {
  /* **HELD FOR AS LONG AS THIS WORKER LIVES, WHICH IS NOT LONG.** The panel asks
   * how things stand every two seconds and every answer needs the book, so
   * reading and parsing 58 KB each time is a real cost for a page somebody has
   * open -- found by an independent reviewer, 2026-09-09. Chrome shuts this
   * worker down after thirty seconds of quiet and this goes with it, so what is
   * held can only ever be as old as the last wake. */
  if (!bookInHand) {
    /* A failed read is not kept: a rejected promise held here would stay rejected until the worker restarts. */
    bookInHand = fetch(chrome.runtime.getURL('recipes.json')).then((got) => got.json()).catch((wrong) => { bookInHand = null; throw wrong; });
  }
  return bookInHand;
};

/* **HIS DRIVE LAYOUT, FROM THE SAME RECIPE FILE.** The folders a report's files go in
 * are `autosync/layout.py`'s, so the run and this half cannot disagree about where. */
const theLayout = async () => {
  const book = await theBook();
  return { kartaan: book.kartaan, folders: book.folders };
};

/* **THE TOOLBAR BUTTON, WHICH IS THE WHOLE OF HOW ANYBODY GETS IN.** With no
 * `default_popup` in the manifest, Chrome sends the press here instead of
 * opening one -- which is what makes this a PAGE rather than a popup, his
 * instruction: *"the user will have more space, and you will also have more
 * space to build things and organise things."*
 *
 * **AND IT IS THE SAME TAB EACH TIME.** The number is kept in the storage that
 * does not outlive the session, because a tab number means nothing after a
 * browser restart -- and a number believed past that points at whatever tab
 * Chrome numbered next, which could be the seller's own. `tabs.update` on a tab
 * that has gone throws, and that is the ordinary case, so it falls back to
 * opening one. */
const THE_PANEL_TAB = 'kartaan-autosync-panel-tab';

/* **A NOTIFICATION MUST CARRY A PICTURE, AND A REAL FILE IS THE ONLY KIND THAT
 * WORKS (A53, 2026-09-16).** This was a one-pixel `data:` image, and when he
 * signed out of Meesho on purpose to test the sign-in alert, NOTHING APPEARED --
 * the sync paused correctly, wrote it all down correctly, and told him where he
 * was not looking. Chrome refuses a notification without a word any program can
 * read, so the picture is a file in the extension and the refusal is now logged.
 * `tools/write_icon.mjs` writes it. */
const THE_ICON = 'icon128.png';

/* **PRESSING THE SIGN-IN NOTIFICATION OPENS THE PANEL (A53).** */
if (chrome.notifications) {
  chrome.notifications.onClicked.addListener(() => {
    chrome.tabs.create({ url: chrome.runtime.getURL(THE_PANEL) });
  });
}
/** Bring the panel up: the one it already has, or a new one. **Written once**,
 *  because the toolbar button and a sync that stopped for a sign-in both need it
 *  and two copies would drift. */
async function showThePanel() {
  const held = await chrome.storage.session.get(THE_PANEL_TAB);
  const already = held[THE_PANEL_TAB];
  if (already !== undefined) {
    try {
      const up = await chrome.tabs.update(already, { active: true });
      if (up && up.windowId !== undefined && chrome.windows) {
        await chrome.windows.update(up.windowId, { focused: true });
      }
      return;
    } catch (gone) {
      /* It was closed, or the browser restarted under it. Open a new one. */
    }
  }
  const tab = await chrome.tabs.create({ url: chrome.runtime.getURL(THE_PANEL) });
  await chrome.storage.session.set({ [THE_PANEL_TAB]: tab.id });
}

chrome.action.onClicked.addListener(showThePanel);

wireUp(chrome, {
  carryOn,
  /* **A SELLER CLOSING THE WALK'S TAB PUTS THE DOWNLOAD-CANCEL AWAY, and until
   * now nothing did.** `wireUp` has always taken this and nothing has ever
   * passed it, so the cancel stayed armed for the rest of its quarter of an hour
   * and the next file the seller downloaded by hand vanished in front of them.
   * Found by an independent reviewer, 2026-09-09, made visible by Stop -- which
   * disarms -- doing what closing the tab did not. */
  whenATabGoes: () => watching.stopExpecting(),
  /* **WHAT THE PANEL MAY ASK, AND ONLY FROM THE PANEL.** See `answerThePanel`:
   * it refuses anything whose sender is not this extension's own `panel.html`,
   * which is a stronger test than the page half's and has to be, because these
   * messages start nights and connect Drives. */
  answerPanel: answerThePanel(chrome, {
    mayAsk: THE_PANEL_ASKS,
    answer: async (asked) => answerThePanelsQuestion(chrome, {
      book: await theBook(),
      startTheNight,
      carryOn,
      watching,
      setTheHour,
      whyThatIsNotATimeOfDay,
      /* **WHEN IT NEXT WAKES BY ITSELF (A53, 2026-09-16).** The hour as it was
       * saved, and the moment Chrome's own clock will next fire -- the two
       * together are what say whether anything will happen at all. */
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
    }, asked),
  }),
  answer: answerThePage(chrome, {
    carryOn,
    goTo,
    routeInThePage,
    takeTheFile,
    landTheFile: putOneFileAway,
    addARow: addOneRow,
    watching,
    /* Where a line said in the page ends up. **Written down rather than left as
     * an empty function** -- the run's own record is the next piece, and until
     * it is there, a line going nowhere has to be visible. */
    say: (line) => console.info('Kartaan Auto-sync:', line),
    secret: () => aFreshSecret(crypto),
  }),
  /* **THE HOURLY RE-CHECK (A53, Rumee's way)**: a sync of the reports still not
   * ready, for their day. A sync already going puts it off by fifteen minutes. */
  onRecheck: async () => {
    const plan = theRecheckSync(await whatIsBeingRechecked(chrome));
    if (!plan) return;
    const said = await startASync(chrome, { book: await theBook(), startTheNight, carryOn }, plan);
    if (said && said.wrong) {
      console.warn('Kartaan Auto-sync: the hourly re-check could not start yet.', said.wrong);
      await chrome.alarms.create(RECHECK_ALARM, { delayInMinutes: 15 });
    }
  },
  onDue: async () => {
    /* **THE SCHEDULED SYNC STARTS HERE, AT THE SELLER'S SAVED TIME -- CONTROL'S
     * RULING FOR A53 (`D:\Control\JOBS.md`, 2026-09-15).** D107 decides where a
     * report's STEPS are decided (Python, generated into `recipes.json`), not when a
     * sync runs; starting one is walking, so the extension does it. It runs its own
     * timed list, never the Run now ticks (A60), one platform after another (`screen.js`
     * `startTheScheduledSync`). A sync already going keeps the queue. */
    const said = await startTheScheduledSync(chrome, {
      book: await theBook(), startTheNight, carryOn,
    });
    if (said.refused.length) {
      console.warn('Kartaan Auto-sync: part of the scheduled sync could not start.', said.refused);
    }
  },
});
