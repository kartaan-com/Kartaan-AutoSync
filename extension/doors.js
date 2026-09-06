/* The two things a page cannot do for itself.
 *
 * **SIX OF THE EIGHT CALLS ARE ANSWERED IN THE PAGE, BY `driver.js`. THESE ARE
 * THE OTHER TWO**, and they are here rather than there because Chrome will not
 * have it any other way:
 *
 *   - **going somewhere tears down whatever is running in the old page.** A page
 *     cannot walk itself to the next address and still be there afterwards to say
 *     what happened, so the background does it and waits for the new page to
 *     finish drawing.
 *
 *     **AND FOR MONTHS NOTHING RECONCILED THAT SENTENCE WITH THE WALK LIVING IN
 *     THE PAGE (D200).** It was right all along and the walk was built as though
 *     it were not: three walks died on his own Meesho panel on 5 September with
 *     "the message channel closed before a response was received", which is this
 *     very teardown seen from the other side. A walk is now a sequence of turns,
 *     one per page, and the place between them is held in storage by
 *     `background.js`. **Nobody is waiting on this call to come back** -- the
 *     page that made it is already gone. What it still does is notice a page
 *     that never draws, so that a walk which can never be picked up again is
 *     ended and named rather than left hanging;
 *   - **nothing inside a page may read the bytes of a download.** And nor may the
 *     background: `chrome.downloads` manages downloads and cannot read one. The
 *     only way to the bytes is to take the download's own address as it starts
 *     and **ask the platform for it a second time**, with the seller's own
 *     cookies.
 *
 * **AND THAT SECOND POINT IS THE WHOLE EXPLANATION OF A FAILURE ALREADY WRITTEN
 * INTO THE RECIPES.** Flipkart began handing over `blob:` addresses on 22 August.
 * A blob address belongs to the page that made it; nobody can ask for it twice,
 * so there is nothing to fetch and no amount of retrying changes that. The
 * reference's own error was "Blob URL - re-fetch not possible" and it was
 * recorded as a symptom. This is the reason.
 *
 * Everything here takes `chrome` as something handed in, so all of it can be
 * checked with no browser and no extension installed.
 */

/* How often to look again while waiting for a page or a download, in
 * milliseconds. */
const LOOK_AGAIN_MS = 200;

/* What a download address that cannot be asked for twice begins with. */
const BUILT_IN_THE_PAGE = 'blob:';

/* How long an armed walk may go on expecting its file, in milliseconds.
 *
 * **THE ARM HAS TO RUN OUT, and this is the number that makes it run out.**
 * Without a limit, a walk that armed and then never produced a file would leave
 * the cancel armed for the rest of the day, and the next thing the SELLER
 * downloaded by hand would vanish in front of them.
 *
 * **FIFTEEN, BECAUSE THE LONGEST WALK THAT CAN EXIST IS 10.58 MINUTES.** That is
 * `me_orders` -- **not `fk_orders`, which an earlier version of this comment
 * named and got wrong** (A25R). A walk runs a recipe's ask list OR its take
 * list, never both, so `fk_orders` at its longest is 5.5 minutes and the two
 * halves must never be added together.
 *
 * **THE REFERENCE IS NOT THE SAME SHAPE, AND SAYING IT WAS WOULD BE WRONG.** It
 * bounds its own uncaptured-download fallback at FIVE minutes and arms seconds
 * before the click; this arms at the start of the walk, because that is the only
 * message this product sends before the click, and so it has further to reach. */
export const ARMED_FOR_MS = 15 * 60 * 1000;

/* What our own window and our own tab are called in storage. **Written down
 * rather than remembered, because the worker that made the window is shut down
 * thirty seconds later and everything it held in a variable goes with it.**
 *
 * **AND THEY LIVE IN `session` STORAGE, NOT `local`, WHICH IS THE WHOLE OF
 * WHETHER THIS PRODUCT CAN NAVIGATE THE SELLER'S OWN PAGE AWAY FROM UNDER THEM
 * (A26R, A26R3).**
 *
 * A window number and a tab number mean something only for as long as one
 * browser session. Chrome hands them out again from the start next time. So a
 * number kept anywhere that outlives the session is a number that will one day
 * point at something of the seller's own -- their inbox -- and this file would
 * make it the selected tab and then walk it to a portal page, destroying
 * whatever they had open. And the walk would then be running in THEIR window
 * beside their other tabs, which is the throttled arrangement this file exists
 * to avoid, reached silently.
 *
 * **`local` IS CLEARED ONLY WHEN THE EXTENSION IS REMOVED. `session` IS CLEARED,
 * IN CHROME'S OWN WORDS, "IF THE EXTENSION IS DISABLED, RELOADED, UPDATED, AND
 * WHEN THE BROWSER RESTARTS."** That is exactly the set of moments after which
 * these two numbers stop meaning what they meant -- so this is not a tidying-up
 * that something has to remember to do, it is the numbers being kept somewhere
 * that cannot outlive them.
 *
 * **AN EARLIER VERSION CLEARED THEM ON `chrome.runtime.onStartup` INSTEAD, AND
 * THAT WAS NOT ENOUGH -- said out loud rather than quietly replaced (D169).**
 * `onStartup` fires when a profile starts. If the seller has switched the
 * extension OFF, it fires at nobody; there is no event at all for an extension
 * being switched back on. So: off, close Chrome, open Chrome, on -- and last
 * night's numbers are this morning's Gmail. A26R3 drove exactly that and got the
 * seller's own tab handed back and navigated away.
 *
 * It also needs no new permission (`storage` already covers it) and is not
 * exposed to content scripts, so the portal's page cannot see it either. */
export const OUR_WINDOW = 'kartaan-autosync-window';
export const OUR_TAB = 'kartaan-autosync-tab';

/* How big to make it. Big enough that the portal draws its DESKTOP layout: a
 * narrow window makes Meesho draw its phone layout, which has no "Bulk Stock
 * Update" button at all, and the walk then truthfully reports a button that
 * genuinely is not there. */
const WINDOW_SIZE = { width: 1000, height: 700 };

/**
 * A tab to walk in: the only tab of our own window, never the seller's.
 *
 * **THIS IS THE WHOLE OF WHETHER THIS PRODUCT WORKS AT TWO IN THE MORNING, AND
 * IT IS ONE SENTENCE OF CHROME'S:**
 *
 *   **CHROME THROTTLES A TAB'S TIMERS WHEN A DIFFERENT TAB IS SELECTED IN THAT
 *   TAB'S WINDOW, OR WHEN THAT WINDOW IS MINIMISED. IT IS NOT TRIGGERED BY
 *   SCREEN FOCUS, AND NOT BY WHETHER ANYBODY IS SITTING THERE.**
 *   (developer.chrome.com/blog/timer-throttling-in-chrome-88)
 *
 * That single fact is why walking whatever tab we are handed does not work
 * unattended and this does. At night the seller's own window is full of their
 * own tabs; ours would be one of the unselected ones, and every wait in the walk
 * would be stretched. **The reference measured what that costs: a fifteen-second
 * wait silently taking NINE MINUTES OR MORE.** A walk under that reports a
 * perfectly good page as a missing button.
 *
 * **SO THE TAB IS THE ONLY TAB OF A WINDOW OF OUR OWN, and that window is made
 * UNFOCUSED and NOT MINIMISED.** Unfocused, because it must never take the
 * screen away from somebody who is using their computer -- and it does not need
 * to, because focus is not what throttling watches. Not minimised, because that
 * IS what throttling watches.
 *
 * **AND WHAT THE REFERENCE ACTUALLY DOES IS NOT QUITE THIS, WHICH AN EARLIER
 * VERSION OF THIS COMMENT GOT WRONG AND IS CORRECTED HERE RATHER THAN QUIETLY
 * (D169, found by A26R).** `getOrCreateRumeeTab` is the shape copied, but it is
 * the reference's SECOND choice: `openTabForJob` looks for a portal tab the
 * seller already has open and BORROWS it, and only opens its own window when
 * there is none. So always using a window of our own is an improvement ON the
 * reference, not a copy of it -- **which also means it is new, and the months of
 * nightly running do not vouch for it.**
 *
 * **AND THE NINE-MINUTE MEASUREMENT IS OF THE BORROWED TAB, NOT OF AN UNFOCUSED
 * WINDOW.** It is what an unselected tab in the seller's own window costs, which
 * is the case this avoids -- it is not evidence about the case this creates.
 * **There is also a third trigger nobody here has measured:** Windows tells
 * Chrome when a window is completely covered by another, and Chrome throttles
 * that the same way. A window like this one sitting behind a maximised one at
 * two in the morning is exactly that, and whether it is throttled is NOT KNOWN.
 * Said plainly rather than assumed either way.
 *
 * **AND THE SAME TAB IS USED AGAIN NEXT TIME.** A tab per report leaves a
 * window filling up with dead tabs, and the moment there are two of them one of
 * them is not selected -- which is the throttled case, arrived at by tidiness.
 */
export async function aTabToWalkIn(chrome, { address = 'about:blank' } = {}) {
  const held = await chrome.storage.session.get([OUR_WINDOW, OUR_TAB]);
  const ourWindow = held[OUR_WINDOW];
  const ourTab = held[OUR_TAB];

  if (ourWindow !== undefined && ourWindow !== null) {
    try {
      const window = await chrome.windows.get(ourWindow);
      /* **PUT BACK IF SOMEBODY MINIMISED IT, because minimised is throttled.**
       * Still not focused: putting a window back on screen is not the same as
       * taking somebody's screen, and only one of those is needed. */
      if (window.state === 'minimized') {
        await chrome.windows.update(ourWindow, { state: 'normal', focused: false });
      }
      if (ourTab !== undefined && ourTab !== null) {
        const tab = await chrome.tabs.get(ourTab);
        if (tab.windowId === ourWindow) {
          /* **MADE THE SELECTED TAB, every time.** If anything else was ever
           * opened in this window, ours is no longer the selected one -- and an
           * unselected tab is a throttled tab whatever window it is in. */
          await chrome.tabs.update(ourTab, { active: true });
          return tab;
        }
      }
      const made = await chrome.tabs.create({ url: address, windowId: ourWindow, active: true });
      await chrome.storage.local.set({ [OUR_TAB]: made.id });
      return made;
    } catch (wrong) {
      /* The window or the tab has been closed. Said plainly rather than
       * treated as a failure: a seller closing a window is not a fault. */
    }
  }

  const made = await chrome.windows.create({
    url: address,
    /* **NEVER TAKES THE SCREEN.** See above: focus is not what throttling
     * watches, so there is nothing to be gained by stealing it. */
    focused: false,
    /* **AND NEVER MINIMISED, which IS what throttling watches.** */
    state: 'normal',
    ...WINDOW_SIZE,
  });
  const tab = (made.tabs && made.tabs[0]) || null;
  await chrome.storage.session.set({ [OUR_WINDOW]: made.id, [OUR_TAB]: tab && tab.id });
  return tab;
}

/**
 * Go to an address in the working tab, and wait for the page to finish drawing.
 *
 * **WAITED FOR, not fired and forgotten.** Handing back the moment the address
 * is set puts every following step on a page that is still blank -- and a blank
 * page reports every button as renamed, which is the commonest wrong answer this
 * whole design exists to stop.
 *
 * Answers the tab it left the seller on.
 */
export async function goTo(chrome, { tabId, address, patienceSeconds, now = () => Date.now(),
                                     rest = pause }) {
  if (!address) throw new Error('There is nowhere to go: no address was given.');
  /* **READ BEFORE, because where the tab already is decides whether telling it
   * where to go is a real page load at all.** See `sameDocumentAs` below. */
  const before = await chrome.tabs.get(tabId);
  await chrome.tabs.update(tabId, { url: address });
  /* **AND IF THAT WAS NOT A REAL PAGE LOAD, MAKE ONE.** This is the whole of
   * Flipkart. Every Flipkart address in the recipe file is
   * `https://seller.flipkart.com/index.html#...` -- the page is always
   * `index.html` and the part that says WHICH report is after the `#`. Telling a
   * tab to go to an address that differs only after the `#` moves the address
   * bar and does not reload anything, so the content script is never put into
   * the page again, so nothing ever asks the background where the walk was, and
   * the walk stops for ever with no error anywhere. Silent, unattended, at
   * night.
   *
   * **THE REFERENCE HIT THIS AND WROTE IT DOWN**, in its own words at
   * `background.js:345`: "chrome.tabs.update only triggers a full page reload
   * when the base URL (origin + pathname) changes... Chrome performs a
   * same-document hashchange -- page does NOT reload, manifest content scripts
   * are NOT re-injected, CONTENT_READY never fires -> silent stall." It forces a
   * reload for exactly this reason and has done for months. */
  if (sameDocumentAs(before && before.url, address)) await chrome.tabs.reload(tabId);
  const giveUpAt = now() + Math.max(0, Number(patienceSeconds) || 0) * 1000;
  for (;;) {
    const tab = await chrome.tabs.get(tabId);
    if (tab.status === 'complete') return tab;
    if (now() >= giveUpAt) {
      /* **SAID AS WHAT IT IS.** "The page never finished drawing" is a different
       * problem from "the button is not there", and the reference reported both
       * as the second. */
      throw new Error(
        `The page at ${address} had not finished drawing after ${patienceSeconds} seconds.`
      );
    }
    await rest(LOOK_AGAIN_MS);
  }
}

/**
 * Watch for a download starting, so that its address is caught as it goes past.
 *
 * **CAUGHT AT THE MOMENT IT STARTS, not looked up afterwards.** Chrome tells you
 * everything about a download when it begins and only what CHANGED after that --
 * so the address has to be taken here or found again the long way round. And on
 * a blob address, the long way round arrives at nothing.
 *
 * Answers something that can be asked what it saw, and told to stop watching.
 */
export function watchForDownloads(chrome, { now = () => Date.now() } = {}) {
  const seen = [];
  let expectingUntil = 0;
  const heard = (item) => {
    /* **THE CANCEL IS THE FIRST THING, AND NOTHING IS WAITED FOR BEFORE IT.**
     * This is the whole trick, and it is invisible unless you look for it: with
     * "Ask where to save each file" switched on, Chrome puts the Save-as window
     * up the moment it has nowhere to put the file, and a seller who has that
     * setting on would hang there FOR EVER, silently, while the platform records
     * the download as done. Cancelling inside the event, before a single `await`,
     * gets there first and no window ever appears. The reference's own comment
     * says it in one line: "no await, so cancel() fires BEFORE Chrome has a
     * chance to show the Save-As dialog." **Anything added above this line that
     * waits for anything undoes it.** */
    if (now() < expectingUntil) {
      /* **CONSUMED, so this arms for ONE file and not for the day.** A walk that
       * armed and produced nothing must not still be armed when the seller
       * downloads something of their own. */
      expectingUntil = 0;
      chrome.downloads.cancel(item.id, () => {
        /* Erased as well, so a download the seller never asked for does not sit
         * in their own downloads list looking like a failure. */
        chrome.downloads.erase({ id: item.id }, () => {});
      });
    }
    /* **RECORDED WHETHER IT WAS CANCELLED OR NOT.** The bytes are never read
     * from the download -- Chrome cannot hand them over -- so what is kept here
     * is the address, and the address survives the cancel. */
    seen.push({ ...item });
  };
  chrome.downloads.onCreated.addListener(heard);
  return {
    /** Everything that has started since the watching began. */
    seen: () => seen.map((one) => ({ ...one })),
    /** Forget everything so far -- called before a step that should produce a
     *  file, so that a download from an earlier step is not taken for this
     *  one. */
    forget: () => { seen.length = 0; },
    /** A walk is starting and one of its steps will produce a file, so the next
     *  download is ours to take rather than the seller's own.
     *
     *  **ARMED BEFORE THE CLICK, never after it.** After it is a race against
     *  the platform's own server, and losing that race is the Save-as window
     *  going up -- which is exactly what waiting for the download to appear in a
     *  list and acting a moment later does, every time. */
    expectAFile: () => { expectingUntil = now() + ARMED_FOR_MS; },
    /** The walk is over, so the next download is the SELLER'S and none of ours.
     *
     *  **WITHOUT THIS THE CANCEL STAYS ARMED FOR THE REST OF THE FIFTEEN
     *  MINUTES**, and the next thing the seller downloaded by hand would vanish
     *  in front of them with no explanation. A25R found this open and nothing
     *  could close it, because nothing in the background knew when a walk had
     *  ended. The walk saying so is what makes it closable. */
    stopExpecting: () => { expectingUntil = 0; },
  };
}

/**
 * The bytes of whatever download the last click produced, or nothing.
 *
 * **NOTHING MEANS THE DOOR HAS CLOSED, NOT THAT IT FAILED.** The walk reads
 * nothing as "the platform now builds this file inside the page", which is what a
 * blob address is, and stops rather than retrying for ever.
 */
export async function takeTheFile(chrome, watching, {
  patienceSeconds, fetch, now = () => Date.now(), rest = pause,
}) {
  if (typeof fetch !== 'function') {
    throw new Error('Taking a file needs a way of asking the platform for it.');
  }
  const giveUpAt = now() + Math.max(0, Number(patienceSeconds) || 0) * 1000;
  for (;;) {
    const started = watching.seen();
    if (started.length) {
      const address = started[0].finalUrl || started[0].url;
      if (!address) {
        /* **NAMED RATHER THAN ASKED FOR.** An empty address asked for anyway
         * fetches the page the seller happens to be on, and a portal page saved
         * as a report is a file with a real size that everything downstream
         * believes. */
        throw new Error('A download started with no address, so there is nothing to ask for.');
      }
      if (address.startsWith(BUILT_IN_THE_PAGE)) {
        /* **THE DOOR THAT HAS CLOSED.** The page built the file itself and the
         * address belongs to that page. There is nothing to ask for. */
        return null;
      }
      /* **ASKED FOR A SECOND TIME, WITH THE SELLER'S OWN COOKIES.** Without them
       * the platform answers with its sign-in page, and a sign-in page saved as a
       * report is the worst possible outcome: it is a file, it has a size, and
       * everything downstream believes the day arrived. */
      let answer = null;
      let refused = '';
      try {
        answer = await fetch(address, { credentials: 'include' });
      } catch (wrong) {
        /* **A FETCH THAT THROWS HERE IS ALMOST ALWAYS CORS, AND IT IS NOT THE
         * END OF THE REPORT.** See below. */
        refused = (wrong && wrong.message) || String(wrong);
      }
      if (!answer || !answer.ok) {
        /* **THE PAGE IS ASKED TO FETCH IT INSTEAD, AND THIS IS NOT A GUESS**
         * (D198; the reference's own DOCS.md section 11, Method 7). It moved
         * ONLY the catching and cancelling of a download into its background
         * half and deliberately left the FETCHING in the page, saying why in one
         * line: its content script "does its OWN fetch(url, credentials
         * include) -- NOT background's fetch, because background's fetch fails
         * CORS on some FK CDN endpoints (confirmed for FK_CLAIMS)".
         *
         * **SO A REFUSAL HERE HANDS BACK AN ADDRESS RATHER THAN A FAILURE**, and
         * the page half gets one more go from an origin the CDN will answer.
         * Reported as a failure instead, a report that is perfectly fetchable is
         * lost every night behind a message blaming the platform. */
        return {
          couldNotFetch: refused
            || `the platform said ${(answer && answer.status) || 'nothing'}`,
          address,
        };
      }
      const holds = new Uint8Array(await answer.arrayBuffer());
      /* A file of nothing is not a file. Said here as well as in the walk,
       * because a nought-byte answer to a fetch and a page that produced no
       * download are two different things and both have to be told apart from a
       * real file. */
      return holds;
    }
    if (now() >= giveUpAt) {
      /* **NOT THE SAME AS A CLOSED DOOR.** Nothing started at all, which means
       * the click did not produce a download -- a different problem, and it says
       * so rather than being read as the platform having changed. */
      throw new Error(
        `Nothing began downloading in ${patienceSeconds} seconds after the file was asked for.`
      );
    }
    await rest(LOOK_AGAIN_MS);
  }
}

/**
 * Would going from one address to the other leave the same page in place?
 *
 * **IT ASKS ABOUT THE PART BEFORE THE `#`, AND NOTHING ELSE.** Two addresses
 * that agree up to the `#` are the same document to a browser: going between
 * them scrolls, it does not load. The page, its scripts and everything the
 * extension put in it all stay exactly as they were.
 *
 * **AND THE SAME ADDRESS TWICE COUNTS.** The real `me_orders` goes to the orders
 * page, asks for the export, and then goes to that same address again to collect
 * it -- so "am I being asked to go where I already am" is not a hypothetical.
 *
 * **UNSURE IS ANSWERED NO.** Without host permission for the tab it is on,
 * Chrome does not hand over its address at all. Answering yes there would reload
 * a page nobody asked to reload; answering no leaves the ordinary path, which is
 * what a tab the extension has no business in should get.
 */
export function sameDocumentAs(wasAt, goingTo) {
  if (!wasAt || !goingTo) return false;
  const upToTheHash = (one) => String(one).split('#')[0];
  return upToTheHash(wasAt) === upToTheHash(goingTo);
}

function pause(ms) {
  return new Promise((done) => setTimeout(done, ms));
}
