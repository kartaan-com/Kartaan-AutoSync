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

import { aFreshSecret, answerThePage, wireUp } from './background.js';
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

wireUp(chrome, {
  answer: answerThePage(chrome, {
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
    /* Nothing is owed until the seller has connected a platform, and none of
     * that is built yet. **Said out loud rather than left as an empty function**
     * -- a run that quietly does nothing looks exactly like a run that worked. */
    console.warn('Kartaan Auto-sync: the daily alarm fired, and there is nothing wired to it yet.');
  },
});
