/* The two things a page cannot do for itself.
 *
 * **SIX OF THE EIGHT CALLS ARE ANSWERED IN THE PAGE, BY `driver.js`. THESE ARE
 * THE OTHER TWO**, and they are here rather than there because Chrome will not
 * have it any other way:
 *
 *   - **going somewhere tears down whatever is running in the old page.** A page
 *     cannot walk itself to the next address and still be there afterwards to say
 *     what happened, so the background does it and waits for the new page to
 *     finish drawing;
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
  await chrome.tabs.update(tabId, { url: address });
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
export function watchForDownloads(chrome) {
  const seen = [];
  const heard = (item) => { seen.push({ ...item }); };
  chrome.downloads.onCreated.addListener(heard);
  return {
    /** Everything that has started since the watching began. */
    seen: () => seen.map((one) => ({ ...one })),
    /** Forget everything so far -- called before a step that should produce a
     *  file, so that a download from an earlier step is not taken for this
     *  one. */
    forget: () => { seen.length = 0; },
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
      const answer = await fetch(address, { credentials: 'include' });
      if (!answer || !answer.ok) {
        throw new Error(
          `The platform would not hand over ${address} a second time`
          + `${answer && answer.status ? ` (it said ${answer.status})` : ''}.`
        );
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

function pause(ms) {
  return new Promise((done) => setTimeout(done, ms));
}
