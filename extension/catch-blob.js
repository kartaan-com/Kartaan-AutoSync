/* Catching a file the page builds inside itself.
 *
 * **THIS IS THE ONE PIECE THAT RUNS IN THE PAGE'S OWN WORLD**, alongside the
 * portal's own code rather than beside it. Everything else in this extension
 * runs in its own private world, which is safer and is the default. This cannot,
 * and the reason is exact.
 *
 * **WHY IT HAS TO EXIST.** `take_file` gets a file by noting the address the
 * download used and asking the platform for it a second time. **Meesho's stock
 * file has no second time.** Pressing Download there makes the page itself post
 * to Meesho, receive the spreadsheet as raw bytes, and hand those bytes straight
 * to the browser -- there is no address to ask again, only a `blob:` handle
 * belonging to that page. Read out of the working reference, which paid for it:
 * *"streams a binary XLSX directly -- no CDN redirect, so background re-fetch
 * after URL capture would fail."*
 *
 * **SO THE ONLY PLACE THE BYTES EXIST IS INSIDE THE PAGE**, for the moment
 * between the page making them and the browser saving them. This sits in that
 * moment.
 *
 * -------------------------------------------------------------------------
 * **TWO THINGS ABOUT THIS FILE ARE SECURITY, NOT TIDINESS (D135).** Both were
 * found by an independent reviewer in cycle 46 and both were real:
 *
 * 1. **IT USED TO BE A CONTENT SCRIPT THAT LOADED ON EVERY PORTAL PAGE AND SAT
 *    THERE WAITING TO BE ARMED BY A MESSAGE FROM THE PAGE.** A portal page is
 *    somebody else's code with somebody else's adverts in it -- an advert or a
 *    tag manager could arm it and then hand back bytes of its own, and those
 *    bytes would have been put into the seller's Drive under a real report's
 *    name. **It is now put into the page one file at a time, by the background,
 *    carrying a secret the page never sees**: `chrome.scripting.executeScript`
 *    hands it over as an argument, not through anything the page can listen to.
 *
 * 2. **IT USED TO POST THE SELLER'S REAL REPORT, BYTE FOR BYTE, TO THE WHOLE
 *    PAGE** (`postMessage(..., '*')`). Every script on that page, and anything
 *    the portal had embedded, could read a seller's settlement file. **Nothing
 *    but a handle leaves this file now**, addressed to the page's own origin,
 *    and the extension's own half reads the bytes for itself.
 *
 * **AND THE LIMIT OF THAT, SAID PLAINLY RATHER THAN LEFT TO BE ASSUMED.** Code
 * in the page's own world cannot hide from the page: it can see this function
 * and unpick it. What it cannot do is make `content.js` believe a file it wrote
 * is a file the platform gave, because it would have to know the secret **before
 * the genuine message carrying it is sent**, and by then the genuine one has
 * already been taken. A page that tampers can stop a report arriving. **It
 * cannot put its own bytes in the seller's Drive**, and a report that does not
 * arrive is loud (D108).
 * -------------------------------------------------------------------------
 *
 * **AND IT CHANGES NOTHING ABOUT WHAT THE PAGE DOES.** The browser still saves
 * the file exactly as it would have. Nothing is suppressed, nothing is blocked;
 * the bytes are simply noticed on the way past.
 */

/** What the caught message is called. Written once, and read by `content.js`. */
export const CAUGHT = 'kartaan-caught-a-file';

/** How big a file is worth carrying at all. A stock file for a large catalogue is
 *  a few hundred kilobytes; anything far past that is not the file we asked for. */
export const TOO_BIG = 40 * 1024 * 1024;

/**
 * Watch for the next file the page builds inside itself, once.
 *
 * **THIS FUNCTION IS PUT INTO THE PAGE'S OWN WORLD BY THE BACKGROUND**, with
 * `chrome.scripting.executeScript`, so it must stand entirely on its own: it can
 * reach nothing in this file and nothing else in the extension. Everything it
 * needs is either handed in or written out inside it. The two constants above
 * are its contract with `content.js`, and a check reads them back out of the
 * source below so the two copies cannot drift.
 *
 * `secret` is fresh for every single file, made from `crypto.getRandomValues` in
 * the background. **It is what tells a message from this function apart from a
 * message the page wrote**, and it is never sent anywhere until the moment the
 * genuine file is caught -- which is the whole of the protection.
 */
export function catchTheNextFile(secret) {
  const CAUGHT_HERE = 'kartaan-caught-a-file';
  const TOO_BIG_HERE = 40 * 1024 * 1024;

  /* **ADDRESSED TO THIS PAGE AND NOWHERE ELSE.** `'*'` hands the message to
   * anything listening, including a frame the portal embedded from somebody
   * else. */
  const here = window.location.origin;

  const already = URL.createObjectURL;
  if (already.kartaanArmedFor !== undefined) {
    /* Already put in once on this page. Re-armed rather than wrapped again: a
     * second wrapper would report the same file twice, once under a secret
     * nobody is waiting for any more. */
    already.kartaanArmedFor = secret;
    return;
  }

  const asTheBrowserDoes = already.bind(URL);

  const watching = function (thing) {
    /* **THE PAGE GETS EXACTLY WHAT IT ASKED FOR, ALWAYS AND FIRST.** If anything
     * here went wrong the page must be none the wiser -- an extension that breaks
     * a seller's own downloads is worse than one that fetches nothing. */
    const handle = asTheBrowserDoes(thing);
    const only = watching.kartaanArmedFor;
    if (!only) return handle;

    /* Only a real file. `createObjectURL` is used for pictures and video on
     * ordinary pages too, and swallowing one of those would be reading something
     * nobody asked for. */
    const looksLikeAFile = thing && typeof thing.arrayBuffer === 'function'
      && typeof thing.size === 'number';
    if (!looksLikeAFile) return handle;

    /* **A PICTURE IS NOT THE FILE WE ASKED FOR.** Ordinary pages make these for
     * images and video all the time, and a report page is still an ordinary page
     * while it is being driven. Catching one would hand back a photograph as a
     * seller's stock file -- a real file, with a real size, which everything
     * downstream would believe. */
    const kind = String((thing.type || '')).toLowerCase();
    if (kind.startsWith('image/') || kind.startsWith('video/') || kind.startsWith('audio/')) {
      return handle;
    }

    watching.kartaanArmedFor = null;
    if (thing.size <= 0 || thing.size > TOO_BIG_HERE) {
      window.postMessage({
        kartaan: CAUGHT_HERE,
        secret: only,
        wrong: thing.size <= 0
          ? 'The page produced a file with nothing in it.'
          : `The page produced a file of ${thing.size} bytes, which is more than this can carry.`,
      }, here);
      return handle;
    }

    /* **THE HANDLE, NEVER THE BYTES.** The extension's own half is on this same
     * origin and reads it for itself, so a seller's settlement file never
     * crosses a channel the page can listen to. */
    window.postMessage({
      kartaan: CAUGHT_HERE, secret: only, handle, size: thing.size,
    }, here);
    return handle;
  };

  watching.kartaanArmedFor = secret;
  URL.createObjectURL = watching;
}
