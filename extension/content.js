/* The piece that runs inside the portal's own page.
 *
 * **IT IS DELIBERATELY THE SMALLEST FILE HERE, and it is the only one with no
 * checks of its own.** Everything it does that could be wrong -- counting,
 * refusing, waiting, naming a failure -- is in `driver.js` and `walk.js`, which
 * are checked against a stand-in browser with no Chrome anywhere. What is left is
 * wiring, and wiring is the part that can only be proved by loading it.
 *
 * **THIS FILE IS ALSO THE ONE OPEN QUESTION IN THE WHOLE EXTENSION.** Chrome's
 * own documentation does not say whether a content script may be an ES module,
 * and says only that `import()` is unsupported in the SERVICE WORKER -- it is
 * silent about here. What it does say plainly is that a content script reaches
 * the extension's own files through `chrome.runtime.getURL()`, that those files
 * must be declared web-accessible, and that they are then served with the headers
 * that make them fetchable.
 *
 * So this is written the documented-adjacent way and **must be loaded once in a
 * real Chrome before any of it is trusted** (Golden Rule 1: where the
 * documentation is ambiguous, the ambiguity is surfaced rather than guessed
 * past). If it does not hold, the fallback is a small step that joins those files
 * into one plain script -- the source stays exactly as it is, because the checks
 * import it.
 *
 * **AND THE ONE THING IN IT THAT IS SECURITY (D135).** This file used to believe
 * any message that came from its own page: an advert or a tag manager on a portal
 * page could post `kartaan-caught-a-file` with bytes of its own, and those bytes
 * would have gone into the seller's Drive under a real report's name. **A message
 * from the page is now believed only when it carries the secret the background
 * put into that page for this one file**, and the page never sees that secret
 * until the genuine message has already been taken.
 */

(async () => {
  /* Only ever one of these per page. A second copy would walk the same recipe
   * twice and download the same file into two differently-named copies, which is
   * how three wrongly-dated duplicates got into the reference's Drive. */
  if (window.__kartaanAutoSync) return;
  window.__kartaanAutoSync = true;

  /* **THESE THREE ARE INSIDE THE GUARD, AND THEY WERE NOT (A26R3).** They are
   * awaits, they are the first thing this file does, and the header above admits
   * Chrome's documentation does not say whether a content script may import like
   * this at all. Outside a guard, one of them failing rejects the whole file at
   * the top with `window.__kartaanAutoSync` already set, so nothing retries --
   * no message, no record, no line. It would fail on every page identically and
   * so announce itself the first time it was really loaded, which is the only
   * reason it never cost a silent night. The guard was one line too low. */
  let pageDoor;
  let theCatcherSaid;
  let theWalk;
  let NeedsSigningIn;
  let capture;
  let hasNotFinished;
  let looksLikeAPage;
  let book;
  try {
    ({ pageDoor, theCatcherSaid } = await import(chrome.runtime.getURL('driver.js')));
    ({
      theWalk, NeedsSigningIn, capture, hasNotFinished,
    } = await import(chrome.runtime.getURL('walk.js')));
    book = await (await fetch(chrome.runtime.getURL('recipes.json'))).json();
  } catch (wrong) {
    console.error('Kartaan Auto-sync: its own files could not be loaded into this page.', wrong);
    return;
  }

  /* **THE SIGNS OF BEING SIGNED OUT COME FROM THE RECIPE FILE**, not from here.
   * This file knows no platform. Until the Python declares them, the door cannot
   * be built -- and it refuses out loud rather than answering "signed in" for
   * ever, which is the whole point of that refusal. */
  const signedOutSigns = book.signedOutSigns || [];

  /* **A FILE THE PAGE BUILDS INSIDE ITSELF IS CAUGHT IN THE PAGE'S OWN WORLD**, by
   * `catch-blob.js`, because that is the only place its bytes ever exist. Meesho's
   * stock file is one of these: pressing Download makes the page fetch the
   * spreadsheet itself and hand the bytes straight to the browser, so there is no
   * address anybody can ask for a second time. */
  /* **WHAT THIS PAGE IS WALKING, held here so the `go` message can name it.**
   * A `go` destroys the page, and the background may have to write down that the
   * next page never drew -- which it cannot do against a report it was never
   * told the name of. */
  const walking = { busy: false, reportId: null, dataDate: null };

  let waitingFor = null;
  let caught = null;
  window.addEventListener('message', (said) => {
    /* **THE REFUSAL IS `theCatcherSaid`, and it is there rather than here so it
     * can be checked.** This file has no checks by design; a security decision
     * does not belong in a file nothing can prove. */
    const ours = theCatcherSaid(said, waitingFor);
    if (!ours) return;
    /* **THE FIRST ONE AND NO OTHER.** The page can read the secret out of the
     * genuine message the moment it arrives; taking only the first means it has
     * nothing left to forge. */
    waitingFor = null;
    caught = ours;
  });

  const armTheCatcher = async () => {
    caught = null;
    waitingFor = null;
    const armed = await chrome.runtime.sendMessage({ do: 'arm-the-catcher' });
    /* **NOTHING IS WAITED FOR IF NOTHING WAS ARMED.** Left set to something
     * falsy, every message would be refused -- which is the safe direction, and
     * it is said rather than left to be inferred. */
    waitingFor = (armed && armed.secret) || null;
    return waitingFor;
  };
  const stopCatching = () => { waitingFor = null; };

  const door = pageDoor({
    signedOutSigns,
    /* The two the background answers, asked for by message. Nothing here waits
     * on the background staying awake: Chrome starts it again when a message
     * arrives, which is why the run's own record lives in storage and not in a
     * variable.
     *
     * **AND THIS ONE IS THE LAST THING THIS PAGE EVER DOES (D200).** Going
     * somewhere destroys this page. The number handed over with it is where the
     * page Chrome draws next picks the walk up, and it is the only thing that
     * survives -- so it goes ACROSS with the message, not into a variable here.
     * **This call is not expected to come back.** Awaited, it is torn down
     * half-said, which is precisely the "message channel closed before a
     * response was received" that killed three walks on his own panel. Nothing
     * after it in this page will run, and nothing after it needs to. */
    go: (address, patience, at) => chrome.runtime.sendMessage({
      do: 'go', address, patience, at, reportId: walking.reportId, dataDate: walking.dataDate,
    }),
    /* **WHICHEVER ARRIVES.** Most files come down as a download, and the
     * background asks the platform for that address a second time. Meesho's
     * stock file never does, and is caught here instead. Both are the same
     * answer to the same question, so whichever comes first is it. */
    takeFile: async (patience) => {
      const fromTheBackground = chrome.runtime.sendMessage({ do: 'take-file', patience });
      const fromThePage = new Promise((done) => {
        const startedAt = Date.now();
        const look = () => {
          if (caught) return done(caught);
          if (Date.now() - startedAt > (Number(patience) || 0) * 1000) return done(null);
          setTimeout(look, 200);
        };
        look();
      });
      const answer = await Promise.race([fromTheBackground, fromThePage]);
      if (answer && answer.wrong) throw new Error(answer.wrong);
      if (answer && answer.file) {
        /* **THE FILE THE CATCHER WAS HANDED, READ HERE (A42).** It used to be a
         * `blob:` handle that was fetched here instead -- and that handle came
         * out of whatever the page had left standing where
         * `URL.createObjectURL` should be, so a page that got there first chose
         * the bytes that reached the seller's Drive.
         *
         * **AND IT IS READ IN THIS HALF ON PURPOSE.** The file crossed as a copy
         * the browser made of its own bytes; reading it here uses this half's
         * own `arrayBuffer`, which no portal page can replace.
         *
         * **AND WHAT CROSSED IS ASKED WHETHER IT IS READABLE AT ALL.** Something
         * built on a prototype rather than made of its own properties crosses as
         * an EMPTY object rather than refusing -- so the catcher cannot name that
         * one and this half can. Left unasked it is a bare "arrayBuffer is not a
         * function" in front of a seller, which says nothing anybody can act on. */
        if (typeof answer.file.arrayBuffer !== 'function') {
          throw new Error('What the page handed to the browser arrived with no file in it.');
        }
        return new Uint8Array(await answer.file.arrayBuffer());
      }
      if (answer && answer.bytes) return new Uint8Array(answer.bytes);
      if (answer && answer.couldNotFetch && answer.address) {
        /* **THE OTHER HALF WAS REFUSED, SO THIS ONE TRIES (D198, rumee DOCS.md
         * section 11 Method 7).** The reference moved only the catching and
         * cancelling of a download into its background and left the fetching
         * here on purpose -- its background fetch fails CORS on some Flipkart
         * CDN endpoints, confirmed for its claims report, and this page can
         * often read what that half cannot.
         *
         * **AND IF THIS IS REFUSED TOO, THE REASON IS THE ONE THE BACKGROUND
         * GAVE, not a second one.** Two different messages for one wall is how
         * a single cause reads as two problems. */
        try {
          const held = await fetch(answer.address, { credentials: 'include' });
          if (held.ok) {
            const bytes = new Uint8Array(await held.arrayBuffer());
            /* **A 200 IS NOT PROOF IT IS THE REPORT, AND THIS RETRY IS EXACTLY
             * WHERE THAT BITES (A26R4).** A portal that has signed the seller
             * out answers a file address with its sign-in page, cheerfully, at
             * 200. Before this fallback existed that case was a clean failure;
             * widening it to "the page fetches too" would have turned it into a
             * sign-in page recorded as the day's report -- which `doors.js` calls
             * the worst possible outcome in its own words, because it is a file,
             * it has a size, and everything downstream believes the day arrived.
             *
             * **THIS IS A GUARD, NOT THE ANSWER.** The Python half sniffs the
             * real bytes properly (`landing.the_file_that_matters`) and this
             * half still has no counterpart -- that gap is written down rather
             * than papered over here. */
            if (!looksLikeAPage(bytes)) return bytes;
            throw new Error(
              'What came back was a web page, not a report -- the platform has almost '
              + 'certainly signed this browser out.'
            );
          }
        } catch (wrong) {
          if (String(wrong.message).includes('not a report')) throw wrong;
          /* Anything else falls through to the sentence below, deliberately. */
        }
        throw new Error(
          'The platform would not hand the file over a second time, to either half: '
          + answer.couldNotFetch
        );
      }
      return answer;
    },
  });

  const walk = theWalk({
    door,
    book,
    say: (line) => chrome.runtime.sendMessage({ do: 'say', line }),
    /* **WHERE THE BYTES FINALLY GO.** The walk takes the file; until this line
     * existed it counted the bytes and dropped them, and `drive.js` -- finished
     * and checked -- was imported by nothing. Putting a file in the seller's
     * Drive needs `chrome.identity`, which this page cannot reach, so the bytes
     * go across to the background half exactly as they came from it.
     *
     * **A REFUSAL IS TURNED BACK INTO A THROW HERE**, because that is what the
     * walk reads: it names the report as failed, the night writes it down and
     * moves on, and the day is fetched again. Answered quietly instead, the
     * walk would report LANDED for a file that is nowhere. */
    putTheFile: async ({ reportId, fileName, body }) => {
      const answer = await chrome.runtime.sendMessage({
        do: 'land-the-file', reportId, fileName, bytes: [...body],
      });
      if (!answer) {
        throw new Error('The browser half said nothing about whether the file was put away.');
      }
      if (answer.wrong) throw new Error(answer.wrong);
      return answer;
    },
  });

  /** Say something to the other half, and never fail because of it.
   *
   *  **A MESSAGE THAT CANNOT BE DELIVERED IS NOT A REASON TO LOSE WHAT IT WAS
   *  CARRYING.** The page can be torn down mid-sentence -- that is the ordinary
   *  case here, not the odd one -- and the background can be starting up. */
  const said = async (what) => {
    try {
      return await chrome.runtime.sendMessage(what);
    } catch (wrong) {
      console.error('Kartaan Auto-sync: could not say what happened.', wrong);
      return null;
    }
  };

  /** What a walk ending is worth saying, whichever way it ended.
   *
   *  **AND WHAT THE PAGE LOOKED LIKE GOES WITH IT.** The walk's own failures
   *  have carried the page from the beginning -- "the evidence travels with the
   *  failure; written somewhere else to be correlated later is written somewhere
   *  nobody ever looks". **A failure the DOOR throws rather than the walk naming
   *  carried nothing**, and the first live `me_orders` run proved what that
   *  costs: "0 date boxes were found" with an empty page beside it, and no way
   *  to tell a changed portal from a page that had not finished drawing without
   *  running the whole thing again. */
  const howItEnded = async (asked, wrong) => ({
    state: 'failed',
    reportId: asked.reportId,
    dataDate: asked.dataDate,
    /* **SIGNING IN IS ITS OWN KIND AND MUST STAY THAT WAY ACROSS THE MESSAGE.**
     * A message carries no kinds of error, so it is said in a word the other
     * side can read back. */
    needsSigningIn: wrong instanceof NeedsSigningIn,
    say: wrong.message,
    /* **AND READING IT MUST NOT BE THE THING THAT FAILS**, for the same reason
     * the saying-so must not: this is the recovery. */
    pageWas: await whatThePageLookedLike(),
  });

  /** The page as words, trimmed the way the walk trims it, or nothing. */
  const whatThePageLookedLike = async () => {
    try {
      return capture(await door.page_text());
    } catch (wrong) {
      return '';
    }
  };

  /**
   * Walk one turn of a report, and say how it ended -- unless it did not end.
   *
   * **A TURN, NOT A WALK, AND THAT IS D200.** The walk's first step is to go
   * somewhere, and going somewhere destroys this page. So a turn either finishes
   * the report or hands back "carrying on, from step N" -- and in that second
   * case this page is already being torn down and there is nobody left to tell
   * anything to. Saying nothing is the correct thing to do.
   */
  const takeATurn = async (asked) => {
    walking.reportId = asked.reportId;
    walking.dataDate = asked.dataDate;
    /* **WHICH STEP THIS PAGE PICKED THE WALK UP AT, and it goes back with every
     * word this page says.** A page the walk has already left is not always
     * destroyed -- Chrome may freeze it in the back/forward cache instead, and
     * thawing it makes its half-said `go` fail and its walk throw. Without this
     * number that old page would report a failure for a walk a newer page is
     * running perfectly. His own Chrome named it while this was being built:
     * "The page keeping the extension port is moved into back/forward cache, so
     * the message channel is closed." */
    const startedAt = Number(asked.at || 0);
    await armTheCatcher();
    let came;
    try {
      /* **THE BACKGROUND CALLS IT `at` AND THE WALK CALLS IT `startAt`, and the
       * two have to be joined here by name.** Handed straight across, the walk
       * sees no `startAt`, begins at nought, and walks the whole recipe again on
       * every page -- which on Meesho means the export asked for a second time
       * and on Flipkart means one of a seller's twenty daily requests burnt for
       * nothing. It would have looked exactly like working. */
      came = await walk(asked.reportId, asked.dataDate, { ...asked, startAt: startedAt });
    } catch (wrong) {
      stopCatching();
      const ended = await howItEnded(asked, wrong);
      /* **THE SAYING-SO MUST NOT BE THE THING THAT FAILS.** This IS the recovery;
       * if it throws, the failure it was reporting is lost with it and the walk
       * ends in silence (A26R). */
      await said({ do: 'walk-done', answer: ended, from: startedAt });
      return ended;
    }
    /* **THE ONE ANSWER THAT IS NOT AN ANSWER.** It carries no `state`, so
     * nothing downstream can file it as an outcome even by accident. This page
     * is going; the next one asks where the walk was and carries on. */
    if (hasNotFinished(came)) return came;
    stopCatching();
    /* **SENT AS ITS OWN MESSAGE, NOT AS A REPLY.** The reply to the message that
     * started this walk went down with the first page, several pages ago. */
    await said({ do: 'walk-done', answer: came, from: startedAt });
    return came;
  };

  chrome.runtime.onMessage.addListener((asked, from, answer) => {
    if (!asked || asked.do !== 'walk') return false;
    /* **REFUSED IF THIS PAGE IS ALREADY WALKING.** A second walk in one page
     * would click the same recipe twice and download the same day into two
     * differently-named copies -- the fault the guard at the top of this file
     * exists for, arriving by a different door. */
    if (walking.busy) {
      answer({ state: 'failed', reportId: asked.reportId, dataDate: asked.dataDate,
        say: 'This page is already walking a report.', pageWas: '' });
      return true;
    }
    walking.busy = true;
    takeATurn(asked).then(answer).catch(async (wrong) => answer(await howItEnded(asked, wrong)));
    /* Answering later is what this true means. Left off, Chrome closes the
     * channel the moment this returns and the answer is thrown away. */
    return true;
  });

  /* **AND THE ONE THING THIS FILE DOES WITHOUT BEING ASKED (D200).**
   *
   * Every portal page the seller opens runs this file -- it is a manifest
   * content script on both portals. So every one of them asks the background the
   * same question: is there a walk in flight that belongs to this tab? Almost
   * always the answer is nothing, and nothing is what an ordinary page the
   * seller opened for themselves must get.
   *
   * **WHEN IT IS NOT NOTHING, THIS PAGE IS THE ONE THE LAST `go` LANDED ON**,
   * and it carries on from the step the background is holding. That is the whole
   * of how a walk outlives the page that started it. The reference does the same
   * thing on every page load and has for months.
   *
   * **NOTHING IS AWAITED BY ANYBODY HERE**, so a failure has nowhere to go but a
   * line in the log -- which is why the walk itself reports through
   * `walk-done` rather than by being returned to a caller. */
  /* **AND NOTHING HERE MAY THROW WITHOUT A WORD, BECAUSE THIS IS NOW THE ONLY
   * WAY A WALK EVER STARTS (A26R).** Nothing pushes a walk at a page any more --
   * every page asks. So this call is the whole of it, and there is no caller
   * above to catch anything: a rejection here would end the walk in silence, the
   * record would sit with no answer until its fifteen minutes ran out, and the
   * day's report would be missing with no line anywhere saying why. That is the
   * exact fault `background.js` opens by naming -- "a run that was interrupted
   * wrote nothing down". */
  try {
    const askedForOne = await chrome.runtime.sendMessage({ do: 'resume?' });
    const carryOn = askedForOne && askedForOne.walk;
    if (carryOn && !walking.busy) {
      walking.busy = true;
      await takeATurn(carryOn);
    }
  } catch (wrong) {
    /* Said where a person can see it. There is nowhere else to say it from:
     * whatever failed is the way of speaking to the other half. */
    console.error('Kartaan Auto-sync: this page could not take up its walk.', wrong);
  }
})();
