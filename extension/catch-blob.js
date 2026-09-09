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
 * **FOUR THINGS ABOUT THIS FILE ARE SECURITY, NOT TIDINESS (D135).** The first
 * three were found by an independent reviewer in cycle 46; the fourth this file
 * named as its own limit and A42 closed. All four were real:
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
 *    the portal had embedded, could read a seller's settlement file. **What
 *    leaves is now addressed to the page's own origin and nowhere else**, so no
 *    frame the portal embedded from somebody else is handed anything at all.
 *
 * 3. **IT HELD THE SECRET WHERE THE PAGE COULD JUST READ IT** -- as a plain
 *    property on the very function it installed into the page's own world
 *    (`URL.createObjectURL.kartaanArmedFor`). Any advert, tag manager or
 *    injected script on the portal could read that property and post its own
 *    `kartaan-caught-a-file` carrying the genuine secret, and **it did not even
 *    have to be quick about it**: the arming happens at the start of every walk
 *    turn, long before any Download is pressed, so a page that simply reads the
 *    property and posts wins every time -- `content.js` takes the FIRST message
 *    it accepts. Those bytes go on to `land-the-file`, and `drive.js` REPLACES
 *    the genuine file of that day under the genuine report name, which the
 *    Python then reads into the seller's ledger as real sales. **The secret is
 *    now held in a closure and written nowhere the page can look.** A closure's
 *    variables cannot be read by any script -- that is the language, not the
 *    browser, and it is the only privacy the page's own world has to offer.
 *
 * 4. **IT POSTED THE HANDLE IT WAS GIVEN BACK, SO A PAGE THAT GOT HERE FIRST
 *    CHOSE THE BYTES (A42, and this file named it before it was closed).** A
 *    page script that replaced `URL.createObjectURL` BEFORE this was installed
 *    is called by this one as though it were the browser. It never learns the
 *    secret and does not need to: it simply answers with a handle for bytes of
 *    its own, and those bytes went on to `land-the-file`, where `drive.js`
 *    REPLACES the genuine file of that day under the genuine report name and
 *    the Python reads it into the seller's ledger AS REAL SALES. **So the
 *    failure was never a crash -- it was wrong money in a seller's books,
 *    silently, under a real report name.**
 *
 *    **WHAT IS POSTED NOW IS THE FILE THIS WAS HANDED, NEVER THE HANDLE IT WAS
 *    GIVEN BACK.** The portal's own Download code passes its own genuine file
 *    straight in as the argument, and nothing can stand in front of an
 *    argument. The impostor's answer is still handed back to the page
 *    untouched, so nothing about what the page does changes.
 *
 *    **AND THE BROWSER COPIES IT, NOT `arrayBuffer()`.** A file crossing
 *    `postMessage` is copied by the browser reading the file's own bytes -- no
 *    method on it is called -- so a page that has replaced `Blob.prototype
 *    .arrayBuffer` cannot make the file read back as something else either.
 *    Something that is not a file the browser recognises either refuses to
 *    cross, which is said out loud below, or crosses empty, which the other
 *    half names when it finds nothing to read.
 *
 * -------------------------------------------------------------------------
 * **AND THE ONE THAT IS STILL OPEN, WRITTEN DOWN HERE BECAUSE IT IS THE SAME
 * HARM AND A SHORTER ROAD TO IT (found by an independent reviewer, A42).**
 *
 * **NOTHING HERE ASKS WHO CALLED.** Between the moment this is armed and the
 * moment the seller's Download really produces a file, ANY script on the portal
 * page can simply call `URL.createObjectURL` with a file of its own and be
 * caught -- it does not have to stand in front of anything, it stands beside it.
 * `armedFor` is spent on the first one, `content.js` takes the first message it
 * accepts, and the genuine Download that follows is then ignored. The bytes go
 * on to `land-the-file` exactly as above: wrong money in a seller's books under
 * a real report's name.
 *
 * **AND THE WINDOW IS WIDE ON PURPOSE.** `background.js` explains why arming
 * happens at the start of the walk turn rather than at the click: armed later,
 * the platform's own server is being raced, and losing that race puts Chrome's
 * Save-as window up in front of a seller nobody is watching. So the window is
 * seconds to tens of seconds per report, every report.
 *
 * **THERE IS NO WAY TO ASK WHO CALLED FROM IN HERE**, which is why this is
 * written down rather than patched: closing it means narrowing WHEN a catch is
 * believed, and that is a change to the walk and to `content.js`, not a line in
 * this file. **Until it is closed, this file is not the whole of the answer.**
 * -------------------------------------------------------------------------
 *
 * **AND THE LIMIT OF ALL THAT, SAID PLAINLY RATHER THAN LEFT TO BE ASSUMED.**
 * Code in the page's own world cannot hide from the page: it can see this
 * function and unpick it. Chrome's own documentation is explicit that the two
 * worlds share nothing but the DOM and that `window.postMessage` is the whole of
 * the documented channel between them -- **there is no private wire to be had
 * here, so the secret has to be unreadable rather than unreachable.**
 *
 * **WHAT THE SECRET BUYS, EXACTLY:** a page script cannot READ, GUESS or REPLAY
 * the proof that a file came from Kartaan's own click. It is thirty-two random
 * bytes, it lives in a closure, it is fresh for every file, and it is sent
 * nowhere until the genuine file is already caught.
 *
 * **AND WHAT IS STILL NOT BOUGHT, WRITTEN DOWN RATHER THAN LEFT TO BE ASSUMED.**
 * `window.postMessage` is itself the page's, and a page that has replaced THAT
 * sees this message -- secret, file and all -- before `content.js` does, and can
 * post its own carrying the same secret first. There is no pristine copy to be
 * had in the page's own world, which is the same wall as the one above: the
 * secret can be unreadable, never unreachable. A page that tampers can also
 * simply stop a report arriving, and a report that does not arrive is loud
 * (D108).
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

  /* **THE SECRET LIVES HERE AND IN NO OTHER PLACE.** It used to be written onto
   * the wrapper below as a property, which put it in plain sight of every script
   * on the portal's page -- the one thing it exists to be hidden from. A
   * variable held in a closure is the opposite: no script anywhere can read it,
   * and that is the JavaScript language rather than anything Chrome promises.
   *
   * **AND NOTHING IS EXPOSED IN ITS PLACE.** No marker, no re-arm hook: a hook
   * the page can reach is a hook the page can REPLACE, and the next arming would
   * then hand the secret straight to it. */
  let armedFor = secret;

  /* **WRAPPED AFRESH EVERY TIME, NEVER RE-ARMED.** Re-arming needed a way in
   * from outside the closure, which is exactly what must not exist. The reason
   * re-arming was there was that a second wrapper reports one file twice -- and
   * it still would: the older wrapper posts under a secret `content.js` has
   * stopped waiting for, so `driver.theCatcherSaid` refuses it. That is noise,
   * not a forged file. **And it is not reached in this extension anyway:**
   * `content.js` arms once per page, at the start of its one turn, and a walk
   * that moves the page starts a new page with a clean world. */
  const asTheBrowserDoes = URL.createObjectURL.bind(URL);

  const watching = function (thing) {
    /* **THE PAGE GETS EXACTLY WHAT IT ASKED FOR, ALWAYS AND FIRST.** If anything
     * here went wrong the page must be none the wiser -- an extension that breaks
     * a seller's own downloads is worse than one that fetches nothing. */
    const handle = asTheBrowserDoes(thing);
    const only = armedFor;
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

    armedFor = null;
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

    /* **THE FILE THIS WAS HANDED, NEVER THE HANDLE IT WAS GIVEN BACK (A42).**
     * The handle above comes out of whatever is standing in for the browser, and
     * a page that replaced `URL.createObjectURL` first is exactly that. The
     * argument is the page's own genuine file.
     *
     * **AND IF IT WILL NOT CROSS, IT WAS NOT A FILE THE BROWSER RECOGNISED.**
     * That refusal is said out loud rather than swallowed, because a walk that
     * hears nothing waits out its patience and the day goes missing with no line
     * saying why -- **and the browser's own reason goes with it**, because a
     * sentence this file invented is a diagnosis and the browser's is evidence.
     * **What this cannot tell apart is a page that replaced `window.postMessage`
     * with something that throws**, so the sentence says what happened rather
     * than why. **Nor is it the whole of a shape check**: an object built on a
     * prototype crosses as an empty one, which the other half names when it
     * finds nothing to read.
     *
     * **AND SAYING SO MUST NOT ITSELF BREAK THE PAGE.** If even that will not
     * go, there is nothing left to say it with, and the page still gets its
     * handle -- the walk then runs out of patience, which is loud (D108).
     *
     * **AND NO SIZE RIDES ALONG WITH IT.** It was a number the page had said,
     * nothing anywhere read it, and beside a file whose own size the other half
     * can simply ask for it would be one measurement spelt two ways -- which
     * `drive.js` names in its own header as the kind of rule nobody ever finds
     * the bug in. What is refused above is still refused above. */
    try {
      window.postMessage({
        kartaan: CAUGHT_HERE, secret: only, file: thing,
      }, here);
    } catch (wouldNotCross) {
      try {
        window.postMessage({
          kartaan: CAUGHT_HERE,
          secret: only,
          wrong: 'What the page handed to the browser would not cross as a file: '
            + ((wouldNotCross && wouldNotCross.message) || String(wouldNotCross)),
        }, here);
      } catch (norWouldSayingSo) {
        /* Nothing left. The page keeps its handle and the walk runs out of
         * patience, which is the loud ending rather than the quiet one. */
      }
    }
    return handle;
  };

  URL.createObjectURL = watching;
}
