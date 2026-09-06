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

import { THE_WALK, aFreshSecret, answerThePage, startAWalk, wireUp } from './background.js';
import { carryTheNightOn, howTheNightWent, startTheNight, theNight } from './nightly.js';
import { goTo, takeTheFile, watchForDownloads } from './doors.js';

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
const carryOn = () => carryTheNightOn(chrome, {
  theWalkNow: async () => {
    /* **THE NAME COMES FROM THE ONE PLACE IT IS DEFINED.** Spelt again here it
     * is a second record of one fact, and the day one of them changes the night
     * silently stops noticing that any walk ever finished. */
    const held = await chrome.storage.local.get(THE_WALK);
    return held[THE_WALK] || null;
  },
  endTheWalkNow: async () => chrome.storage.local.remove(THE_WALK),
  startAWalk: (how) => startAWalk(chrome, how),
});

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

wireUp(chrome, {
  carryOn,
  answer: answerThePage(chrome, {
    carryOn,
    goTo,
    takeTheFile,
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
