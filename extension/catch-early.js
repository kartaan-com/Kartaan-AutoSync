/* GENERATED from extension/catch-blob.js by tools/write_catch_early.mjs.
 * Do not edit by hand -- change catchTheNextFile and run the tool again.
 *
 * Loaded on every Flipkart page in the page's own world at document_start, so
 * it is in place before any Flipkart script can take its own copy of the
 * functions it watches. Installed switched off: nothing is caught until the
 * background arms it with a fresh secret for one file. */
(function catchTheNextFile(secret) {
  const CAUGHT_HERE = 'kartaan-caught-a-file';
  const TOO_BIG_HERE = 40 * 1024 * 1024;

  /* **ADDRESSED TO THIS PAGE AND NOWHERE ELSE.** `'*'` hands the message to
   * anything listening, including a frame the portal embedded from somebody
   * else. */
  const here = window.location.origin;

  /* **RUMEE'S WAY, AND IT IS HIS DECISION OF 2026-09-14: IN THE PAGE BEFORE
   * THE PAGE'S OWN CODE RUNS.** His ads Search Term Report would not land: this
   * used to be put in only at the moment of arming, after Flipkart's own code
   * had loaded -- and code that took its own copy of `URL.createObjectURL` when
   * it loaded never calls a catcher installed later. The page then clicked an
   * anchor whose address was `blob:`, nothing stopped it, Chrome started a real
   * download, and the background read `blob:` as a platform change. The working
   * reference has never had that miss: its `content/intercept.js` is a manifest
   * content script in the page's own world at `document_start`. He asked which
   * way has the higher success rate, was told it is the reference's and what it
   * costs, and chose it.
   *
   * **SO THIS SAME FUNCTION NOW RUNS TWICE ON A FLIPKART PAGE, DOING TWO
   * DIFFERENT THINGS.** First, as `catch-early.js` at `document_start` with no
   * secret: it installs every wrapper, switched off. Then, each time a file is
   * wanted, the background puts it in again with a fresh secret -- and finding
   * itself already there, it only switches the installed catcher on.
   *
   * **HOW THE SECRET REACHES IT WITHOUT THE PAGE SEEING IT.** Through ONE entry
   * on `window`, defined here with `writable: false, configurable: false`, so no
   * script can replace it or delete it once it exists. **It is trusted only
   * because nothing on the page can have run first:** Chrome documents that a
   * `document_start` content script runs before any other script is run. A page
   * CAN call the entry itself -- which only arms the catcher for a secret
   * `content.js` is not waiting for, so everything it causes is refused.
   *
   * **AND AN ENTRY THAT CAN STILL BE REPLACED IS NOT OURS, AND IS NEVER HANDED
   * THE SECRET.** On a page this did not load early into -- a tab opened before
   * the extension was reloaded -- a hostile script could have put its own
   * function there to be called with the real secret. So the entry is used only
   * if it is locked; otherwise this installs its own wrappers exactly as it
   * always did, and nothing is called. **A page script that defines a LOCKED
   * entry of its own first, on such a stale tab, is not stopped by this -- that
   * is the limit of the check, written down rather than assumed away.** Walks
   * always load their own page after the extension, so they always have the
   * early catcher. */
  const ARM_HERE = '__kartaanArmTheCatcher';
  const described = Object.getOwnPropertyDescriptor(window, ARM_HERE);
  if (described && described.configurable === false && described.writable === false
      && typeof described.value === 'function') {
    if (secret) described.value(secret);
    return;
  }

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
  /* **THE HANDLE OF A FILE ALREADY CAUGHT AS IT WAS BUILT -- HIS FLIPKART CLAIMS
   * REPORT, 2026-09-14.** Measured on his own panel with every download stopped:
   * the page asks `napi/payments/downloadClaimReport` for the bytes, calls
   * `createObjectURL` on them (`application/octet-stream`, 23,462 bytes), then
   * clicks an in-page `<a download="claim_report.xlsx">` pointing at that handle.
   * **Caught at the first, the arm was spent -- so the click was let through,**
   * Chrome began a `blob:` download, and the background's answer to that reached
   * the walk before the page's caught file did: *"the platform builds this file
   * inside the page"*, with the file sitting caught and unused.
   *
   * **THE REFERENCE NEVER HAS THIS RACE:** `content/intercept.js:314` suppresses
   * every `blob:` click for as long as it is capturing, not once. This is
   * narrower: only the one handle this caught, and only once. */
  let justCaught = null;
  const wasJustCaught = (address) => {
    const handle = justCaught;
    if (!handle || String(address || '') !== handle) return false;
    justCaught = null;
    return true;
  };

  /* **WRAPPED AFRESH EVERY TIME, NEVER RE-ARMED.** Re-arming needed a way in
   * from outside the closure, which is exactly what must not exist. The reason
   * re-arming was there was that a second wrapper reports one file twice -- and
   * it still would: the older wrapper posts under a secret `content.js` has
   * stopped waiting for, so `driver.theCatcherSaid` refuses it. That is noise,
   * not a forged file. **And it IS reached in this extension, twice per turn
   * since A44:** once at the start of the turn and once immediately before the
   * click that builds the file. The first wrapper is left installed and, if it
   * caught nothing, still armed -- so the genuine file makes both of them speak,
   * the older one under a secret `content.js` has stopped waiting for. That is
   * the noise described above, and it is refused. A walk that moves the page
   * starts a new page with a clean world. */
  const asTheBrowserDoes = URL.createObjectURL.bind(URL);

  /* **AND THE OTHER WAY A FILE LEAVES A PORTAL, WHICH IS THE COMMONER ONE.**
   * Measured on his own signed-in Meesho panel on 2026-09-11, four runs and two
   * hand-clicks: pressing Download on Bulk Stock Update builds an `<a>` in the
   * document whose `href` is an 884-character
   * `https://storage.googleapis.com/...` signed link, whose `target` is
   * `_blank`, and calls `.click()` on it.
   *
   * **`target="_blank"` MAKES IT A NEW TAB, AND CHROME REFUSES A NEW TAB THAT
   * NO PERSON ASKED FOR.** `element.click()` from an extension carries no such
   * permission, so the pop-up is blocked, no download is ever created, and the
   * walk waits out its whole patience with nothing to say. Clicked with a real
   * mouse the same button downloads in seconds -- **into the seller's Downloads
   * folder, which is exactly where a report must never go.**
   *
   * **SO IT IS SUPPRESSED AND THE ADDRESS IS TAKEN INSTEAD.** Nothing is
   * downloaded, so there is no Save-as window to race and nothing to cancel;
   * the extension asks the platform for that address itself and the bytes go
   * straight to the seller's Drive. **This is the working reference's own
   * method** (`content/intercept.js:305-327`, which suppresses the anchor click
   * and relays the URL) and his own instruction of 2026-09-11: *"it finds the
   * download links and refetches that file to the drive."*
   *
   * **AND IT IS THE SAME ONE-USE SECRET, ON THE SAME TERMS.** An address is a
   * string the page chose, so believing one is believing the page -- which is
   * why the other half asks the same question of it again before acting.
   *
   * **NOTHING IS SUPPRESSED WHEN NOTHING IS ARMED, AND NOTHING THAT IS NOT A
   * REPORT ADDRESS IS SUPPRESSED EVER.** While this sits in the page the seller
   * may still be using it; an extension that breaks his own links is worse than
   * one that fetches nothing. */
  /* **AND FLIPKART'S LISTING FILE, MEASURED ON HIS OWN PANEL 2026-09-14.** The
   * Download button on a Downloads History row calls `window.open` on
   * `https://seller.flipkart.com/napi/listing/stockFileDownload?...` with
   * `_blank`. Not on this list, it was let through, Chrome refused a window no
   * person asked for ("pop-up blocked"), and the collect waited ninety seconds
   * for nothing. Asked for by its own path, not by the portal's name, so nothing
   * else the portal opens is ever taken. `driver.js` holds the same entry. */
  const REALLY_FROM_HERE = [
    'storage.googleapis.com',
    'amazonaws.com',
    'seller-api.flipkart',
    'downloadorders',
    'downloadreturns',
    'downloadpayments',
    'seller.flipkart.com/napi/listing/stockfiledownload',
  ];
  const worthTaking = (address) => {
    const low = String(address || '').toLowerCase();
    if (!low.startsWith('https://')) return false;
    return REALLY_FROM_HERE.some((one) => low.includes(one));
  };
  /* **A NEW LINK ON THIS VERY SITE, OPENED AS A NEW WINDOW -- HIS RULING,
   * 2026-09-14.** Taken so the other half can fetch it and keep it only if it
   * really is a spreadsheet (`driver.js` `THE_PLATFORMS_OWN_SITES`). **Never an
   * ordinary in-page link**: an anchor that is not a new window or a download is
   * the page moving itself, and stopping it would break the walk and the seller's
   * own page. **Never this page itself**, which is what a `#` link resolves to. */
  const onThisSiteAsANewWindow = (address, asANewWindow) => {
    if (!asANewWindow) return false;
    try {
      const there = new URL(String(address || ''), window.location.href);
      return there.protocol === 'https:' && there.origin === here
        && there.pathname !== window.location.pathname;
    } catch (notAnAddress) {
      return false;
    }
  };
  /* The whole address, so a link written relative to the page crosses as one the
   * other half can fetch. */
  const theWholeAddress = (address) => {
    try {
      return new URL(String(address || ''), window.location.href).href;
    } catch (notAnAddress) {
      return String(address);
    }
  };
  const takeTheAddress = (address, asANewWindow = false) => {
    const only = armedFor;
    if (!only || !(worthTaking(address) || onThisSiteAsANewWindow(address, asANewWindow))) return false;
    armedFor = null;
    try {
      window.postMessage({ kartaan: CAUGHT_HERE, secret: only, address: theWholeAddress(address) }, here);
    } catch (wouldNotCross) {
      /* **THE PAGE IS NOT LEFT BROKEN BY OUR OWN FAILURE.** Nothing was said, so
       * nothing is suppressed either and the page does what it always did -- the
       * walk then runs out of patience, which is the loud ending (D108). */
      return false;
    }
    return true;
  };

  /* **AND A FILE THE PAGE HAS ALREADY BUILT, ON ITS WAY OUT AS A `blob:`
   * ADDRESS -- THE REFERENCE SUPPRESSES THESE WHILE IT IS CATCHING, AND SO DOES
   * THIS NOW** (`content/intercept.js`, its anchor-click and `window.open`
   * patches). Let through, Chrome starts a real download with an address that
   * belongs to this page and cannot be asked for a second time, which is exactly
   * how the ads Search Term Report was lost.
   *
   * **AND IT IS NOT ONLY SUPPRESSED, IT IS TAKEN.** A `blob:` address can be
   * read by the page that made it, so it is read here, with the page's own
   * `fetch` as it stood when this was installed, and handed over as the FILE --
   * the same shape and the same one-use secret as a file caught at
   * `createObjectURL`. So a file the page built by a road the other wrapper never
   * saw still reaches the seller's Drive rather than their Downloads folder.
   *
   * **NOTHING IS TAKEN WHEN NOTHING IS ARMED**, which leaves the seller's own
   * downloads exactly as they were. */
  const readsAsTheBrowserDoes = typeof window.fetch === 'function' ? window.fetch.bind(window) : null;
  const takeTheBlob = (address) => {
    const only = armedFor;
    if (!only || !readsAsTheBrowserDoes || !String(address || '').startsWith('blob:')) return false;
    armedFor = null;
    const sayWhatWentWrong = (sentence) => {
      try {
        window.postMessage({ kartaan: CAUGHT_HERE, secret: only, wrong: sentence }, here);
      } catch (norWouldSayingSo) {
        /* Nothing left to say it with. The walk runs out of patience, which is
         * the loud ending rather than the quiet one. */
      }
    };
    readsAsTheBrowserDoes(String(address))
      .then((answer) => answer.blob())
      .then((file) => {
        if (!file || file.size <= 0) {
          sayWhatWentWrong('The page produced a file with nothing in it.');
          return;
        }
        if (file.size > TOO_BIG_HERE) {
          sayWhatWentWrong(`The page produced a file of ${file.size} bytes, which is more than this can carry.`);
          return;
        }
        try {
          window.postMessage({ kartaan: CAUGHT_HERE, secret: only, file }, here);
        } catch (wouldNotCross) {
          sayWhatWentWrong('What the page handed to the browser would not cross as a file: '
            + ((wouldNotCross && wouldNotCross.message) || String(wouldNotCross)));
        }
      })
      .catch((couldNotRead) => {
        sayWhatWentWrong('The file the page built could not be read back from its address: '
          + ((couldNotRead && couldNotRead.message) || String(couldNotRead)));
      });
    return true;
  };

  /* **AND A LINK THIS DID NOT TAKE IS SAID, NEVER FETCHED -- HIS RULING,
   * 2026-09-14.** While armed, every new window or download link let go is named
   * to the page half, so a failure can say what the platform tried to open instead
   * of a bare "nothing began downloading". **It carries no secret**: a secret
   * posted before the file would hand an advert exactly what it needs to forge the
   * file. The page half treats it as words and nothing more. */
  const DECLINED_HERE = 'kartaan-declined-a-link';
  const sayItWasNotTaken = (address) => {
    if (!armedFor) return;
    const said = String(address || '');
    if (!said || said.startsWith('blob:') || said.startsWith('data:')) return;
    try {
      window.postMessage({ kartaan: DECLINED_HERE, address: theWholeAddress(said) }, here);
    } catch (norCouldItSaySo) {
      /* Nothing to say it with; the failure is simply less specific. */
    }
  };

  /* **ASKED FOR RATHER THAN ASSUMED.** Every real page has these; nothing else
   * that runs this does, and a catcher that threw on the way in would leave the
   * page with no catcher at all and nothing saying so. */
  if (typeof HTMLAnchorElement !== 'undefined' && HTMLAnchorElement.prototype) {
    const clicksAsTheBrowserDoes = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function () {
      const asANewWindow = this.target === '_blank'
        || (typeof this.hasAttribute === 'function' && this.hasAttribute('download'));
      if (wasJustCaught(this.href) || takeTheAddress(this.href, asANewWindow)
        || takeTheBlob(this.href)) return undefined;
      if (asANewWindow) sayItWasNotTaken(this.href);
      return clicksAsTheBrowserDoes.call(this);
    };
  }

  /* **AND THE SAME FOR A PORTAL THAT OPENS ITS FILE RATHER THAN LINKING IT.**
   * The reference patches this one too (`intercept.js:262-268`) because some
   * portals do, and a report opened in a window is a report nobody catches. */
  if (typeof window.open === 'function') {
    const opensAsTheBrowserDoes = window.open;
    window.open = function (address, ...rest) {
      if (wasJustCaught(address) || takeTheAddress(address, true) || takeTheBlob(address)) return null;
      sayItWasNotTaken(address);
      return opensAsTheBrowserDoes.call(window, address, ...rest);
    };
  }

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
    /* **AND ITS HANDLE IS NOT TO BE DOWNLOADED AS WELL.** See `justCaught`. */
    justCaught = typeof handle === 'string' ? handle : null;
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

  /* **THE ONE WAY IN, LOCKED AS SOON AS IT EXISTS.** Defined last, so it is
   * never there while any wrapper above is still missing. If the page somehow
   * holds the name already, it cannot be taken back from it -- and then there
   * is simply no entry, this closure keeps its own secret, and the next arming
   * installs a fresh catcher exactly as before. */
  try {
    Object.defineProperty(window, ARM_HERE, {
      value: (fresh) => { armedFor = fresh || null; },
      writable: false,
      configurable: false,
      enumerable: false,
    });
  } catch (theNameIsTaken) {
    /* See above. Nothing is exposed and nothing is called. */
  }
})(null);
