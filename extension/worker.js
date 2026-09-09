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
  THE_PANEL, THE_WALK, aFreshSecret, answerThePage, answerThePanel, setTheHour, startAWalk,
  whyThatIsNotATimeOfDay, wireUp,
} from './background.js';
import { carryTheNightOn, howTheNightWent, startTheNight, theNight } from './nightly.js';
import { goTo, takeTheFile, watchForDownloads } from './doors.js';
import { aDriveToken, aWayOfAsking, landTheFile, theKartaanFolder } from './drive.js';
import {
  THE_PANEL_ASKS, answerThePanelsQuestion, rememberTheNight, theSetup,
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
 * own worker, which is to say the person whose browser it is. */
self.startAWalk = (how) => startAWalk(chrome, how);

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
   * watching. */
  await rememberTheNight(chrome, { book: theBook });
  return moved;
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
  /* **THE SELLER'S OWN PANEL NAME IS PUT IN HERE, and until this line no Meesho
   * report could ever be walked.** All five of them have `{panel}` in their
   * steps -- it is the piece of a supplier panel's address that is the seller's
   * own -- and `walk.js` refuses a step carrying one without it, in words. The
   * night does not carry it because it is not the night's: it is a thing the
   * seller told the panel once, and it belongs to the walk. */
  startAWalk: async (how) => startAWalk(chrome, { ...how, panel: (await theSetup(chrome)).panel }),
};

/* **THE TWO HANDLES A NIGHT IS RUN AND READ BY, until there is a screen for
 * it.** Same reasoning as `startAWalk` above: a service worker's own global is
 * not reachable from a web page, a content script, or another extension -- the
 * only thing that can see these is the DevTools console of this extension's own
 * worker, which is to say the person whose browser it is. */
self.startTheNight = async (how) => {
  const night = await startTheNight(chrome, how);
  await carryOn();
  return night;
};
self.howTheNightWent = async () => howTheNightWent(await theNight(chrome));

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
 * **AND THE `Kartaan AutoSync` FOLDER IS FOUND OR MADE HERE, ONCE PER FILE.**
 * Under `drive.file` this extension can only ever see files it made itself, so
 * there is nothing to keep and nothing anybody has to paste in. */
const putOneFileAway = async ({ reportId, fileName, body }) => {
  const ask = aWayOfAsking(chrome, { fetch: (...args) => fetch(...args) });
  const inside = await theKartaanFolder(chrome, ask);
  return landTheFile(chrome, ask, { reportId, fileName, inside, body });
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
  if (!bookInHand) bookInHand = (await fetch(chrome.runtime.getURL('recipes.json'))).json();
  return bookInHand;
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
chrome.action.onClicked.addListener(async () => {
  const held = await chrome.storage.session.get(THE_PANEL_TAB);
  const already = held[THE_PANEL_TAB];
  if (already !== undefined) {
    try {
      await chrome.tabs.update(already, { active: true });
      return;
    } catch (gone) {
      /* It was closed, or the browser restarted under it. Open a new one. */
    }
  }
  const tab = await chrome.tabs.create({ url: chrome.runtime.getURL(THE_PANEL) });
  await chrome.storage.session.set({ [THE_PANEL_TAB]: tab.id });
});

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
    }, asked),
  }),
  answer: answerThePage(chrome, {
    carryOn,
    goTo,
    takeTheFile,
    landTheFile: putOneFileAway,
    watching,
    /* Where a line said in the page ends up. **Written down rather than left as
     * an empty function** -- the run's own record is the next piece, and until
     * it is there, a line going nowhere has to be visible. */
    say: (line) => console.info('Kartaan Auto-sync:', line),
    secret: () => aFreshSecret(crypto),
  }),
  onDue: async () => {
    /* **THE NIGHT IS NOT STARTED BY THE CLOCK YET, AND THAT IS DELIBERATE.**
     * Which reports a seller owes on a given night is the Python's decision, and
     * nothing has brought that list across yet. Starting a night here would mean
     * this file deciding it, which is exactly the split D107 exists to keep.
     * **But a night already going is carried on**, so a run that began before
     * midnight is not abandoned at it. */
    console.warn('Kartaan Auto-sync: the daily alarm fired. Nothing decides tonight list yet.');
    await carryOn();
  },
});
