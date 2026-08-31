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

  const { pageDoor, theCatcherSaid } = await import(chrome.runtime.getURL('driver.js'));
  const { theWalk, NeedsSigningIn } = await import(chrome.runtime.getURL('walk.js'));
  const book = await (await fetch(chrome.runtime.getURL('recipes.json'))).json();

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
     * variable. */
    go: (address, patience) => chrome.runtime.sendMessage({ do: 'go', address, patience }),
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
      if (answer && answer.handle) {
        /* **THE BYTES ARE READ HERE, not sent across.** A `blob:` handle belongs
         * to this origin and a content script shares it, so this is the one
         * reader that can open it -- and the seller's report never crosses a
         * channel the page can listen to. */
        const held = await fetch(answer.handle);
        return new Uint8Array(await held.arrayBuffer());
      }
      if (answer && answer.bytes) return new Uint8Array(answer.bytes);
      return answer;
    },
  });

  const walk = theWalk({
    door,
    book,
    say: (line) => chrome.runtime.sendMessage({ do: 'say', line }),
  });

  chrome.runtime.onMessage.addListener((asked, from, answer) => {
    if (!asked || asked.do !== 'walk') return false;
    armTheCatcher()
      .then(() => walk(asked.reportId, asked.dataDate, asked))
      .then((came) => { stopCatching(); answer(came); })
      .catch((wrong) => {
        stopCatching();
        answer({
          state: 'failed',
          reportId: asked.reportId,
          dataDate: asked.dataDate,
          /* **SIGNING IN IS ITS OWN KIND AND MUST STAY THAT WAY ACROSS THE
           * MESSAGE.** A message carries no kinds of error, so it is said in a
           * word the other side can read back. */
          needsSigningIn: wrong instanceof NeedsSigningIn,
          say: wrong.message,
          pageWas: '',
        });
      });
    /* Answering later is what this true means. Left off, Chrome closes the
     * channel the moment this returns and the answer is thrown away. */
    return true;
  });
})();
