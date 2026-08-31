/* The eight things the Python side asks of a page, and nothing else.
 *
 * THIS FILE HOLDS NO KNOWLEDGE OF ANY PLATFORM. There is no Meesho in it, no
 * Flipkart, no report, no button name, no decision about whether to retry.
 * Every one of those lives in `autosync/recipes.py` and `autosync/browser.py`,
 * where it is checked without a browser existing. This carries out one
 * instruction at a time and reports what it saw.
 *
 * That is the whole point. The reference drove both portals from about 3,800
 * lines of JavaScript that nothing could check, and every failure it had for
 * three months was the same shape: a button had moved. Written this way, a
 * moved button is one entry in a Python list, and the part that actually
 * touches the page is small enough to read in one sitting.
 *
 * THE CONTRACT IS WRITTEN AT THE TOP OF `autosync/browser_door.py`:
 *
 *     go(address)                    -> nothing, or throws
 *     find(how, what, exact, patience, near) -> HOW MANY things match
 *     click(how, what, exact, near)  -> nothing, or throws
 *     pick_range(start, end)         -> nothing, or throws
 *     take_file()                    -> the bytes, or null if nothing came
 *     overlays()                     -> [{width, height, text, blocks}, ...]
 *     page_text()                    -> what is on the page now
 *     needs_signing_in()             -> true when the portal is asking
 *
 * **SIX OF THE EIGHT ARE QUESTIONS ABOUT THE PAGE, AND THEY ARE ANSWERED HERE.
 * TWO ARE ABOUT THE BROWSER ITSELF AND ARE HANDED IN.** `go` changes which page
 * is open, which tears down anything running inside the old one; `take_file`
 * reads the bytes of a download, which nothing inside a page is allowed to see.
 * Both belong to the extension's background half. They are passed to
 * `pageDoor()` rather than reached for, which is the same shape the whole of
 * `autosync/` already uses -- and it is what lets every rule below be checked
 * with no browser, no extension and no seller account.
 *
 * **`find` ANSWERS A COUNT, NEVER AN ELEMENT, AND THAT IS THE POINT.** Meesho
 * added a chart whose legend read "Payments to Date" -- exactly like the menu
 * item, and earlier in the page. The reference took the first match, clicked the
 * legend, and payments were dead for nine days behind an error blaming a button
 * two steps later. Answering a count is what lets the Python side refuse.
 */

/* The eight names, spelt exactly as the Python side spells them. The message
 * bridge passes these straight through, so there is no table anywhere turning
 * one spelling into another -- two records of one fact is the fault this
 * project has been caught by four times. */
export const THE_CALLS = Object.freeze([
  'go',
  'find',
  'click',
  'pick_range',
  'take_file',
  'overlays',
  'page_text',
  'needs_signing_in',
]);

/* The three ways of describing a thing on a page. **These same three words are
 * in `autosync/browser.py`**, because they cross the wire in every step. That
 * duplication is real and is not hidden: `tools/export_recipes.py` refuses to
 * write a recipe file naming a way of finding something that is not in this
 * list. */
export const BY_TEXT = 'text';
export const BY_ROLE_AND_TEXT = 'role';
export const BY_TEST_ID = 'test-id';
export const BY_PRESSABLE_TEXT = 'pressable';
const WAYS_OF_FINDING = Object.freeze([BY_TEXT, BY_ROLE_AND_TEXT, BY_TEST_ID, BY_PRESSABLE_TEXT]);

/* How often to look again while waiting, and how long to wait after something
 * first appears before answering how many there are. */
const LOOK_AGAIN_MS = 120;
const SETTLE_MS = 250;

/* How much of the page to hand back. The Python side keeps 400 characters of
 * it as evidence, so this is generous rather than tight -- and it is capped at
 * all so that a run cannot try to push a whole rendered portal through the
 * message bridge. */
const PAGE_LIMIT = 5000;

/* How much of an overlay's words to report. Enough to recognise which
 * promotion it was, short enough that a log stays readable. */
const OVERLAY_LIMIT = 300;

/* How much of the window something has to cover before a click aimed at the page
 * would hit it instead. Not all of it: a backdrop often leaves a hairline. */
const MOST_OF_THE_PAGE = 0.9;

/* What a thing that can be clicked is, in ordinary HTML terms. No platform
 * knows anything about this list; it is what a browser itself treats as a
 * control. */
const CONTROL_TAGS = Object.freeze(['button', 'a', 'summary']);
const CONTROL_ROLES = Object.freeze(['button', 'link', 'tab', 'menuitem', 'option']);

/* ------------------------------------------------------------ reading words */

/** One space between words, nothing at either end. A portal lays its text out
 *  across several lines and a checked-in phrase does not. */
function words(text) {
  /* Nothing, written as nothing. `String(null)` is the four-letter word "null"
   * and `String(undefined)` the nine-letter one -- plausible-looking answers
   * that would match a phrase nobody put on the page. A real `textContent` is
   * null on some nodes, and a control with no value has none. */
  return String(text ?? '').replace(/\s+/g, ' ').trim();
}

/* MATCHED WITHOUT REGARD TO CAPITALS, and that is deliberate rather than
 * careless. Portals shout their buttons in capitals through a stylesheet, and
 * the words underneath stay as they were written -- so which case reaches here
 * depends on how the page was built that week. It does not weaken the exact
 * match that matters: the nine-day outage was two things reading the SAME
 * words, and both of them still match, which is what makes it refuse. */
function sameWords(a, b) {
  return words(a).toLowerCase() === words(b).toLowerCase();
}

function holdsWords(a, b) {
  return words(a).toLowerCase().includes(words(b).toLowerCase());
}

/* ------------------------------------------------------------ reading a page */

function thePage() {
  const doc = globalThis.document;
  if (!doc || !doc.body) {
    throw new Error('There is no page here to read. Nothing can be looked for.');
  }
  return doc.body;
}

/** Everything on the page, in the order it is written. */
function everything(node, found = []) {
  found.push(node);
  for (const child of node.children || []) everything(child, found);
  return found;
}

/* PAINTED, NOT MERELY PRESENT.
 *
 * A portal keeps whole menus in the page with no size at all, ready to show.
 * Counted, they turn one visible button into three matches and every lookup
 * refuses for a reason that is not true. Asked of the box the browser actually
 * gave it, they are not there -- which is the same rule this project's own
 * checker enforces on the product (D88: measuring a painted thing by its
 * declared size is refused). */
function isPainted(node) {
  if (node.hidden === true) return false;
  const box = node.getBoundingClientRect();
  return box.width > 0 && box.height > 0;
}

/* WHAT A PERSON CAN PRESS -- EITHER because the page says what it is, OR
 * because the cursor changes over it.
 *
 * **READ OFF HIS OWN MEESHO PANEL, 2026-08-28.** Its sidebar is built from an
 * `h5` and a row of `p` elements with no role, no tabindex and no test id: the
 * only thing telling a person "Orders" can be pressed is that the cursor
 * changes. Asked for a control, that sidebar answers nothing at all.
 *
 * **BUT IT IS A SUPERSET, NOT A REPLACEMENT, and that matters.** A plain
 * `<button>` in Chrome has the ordinary arrow cursor unless somebody styled it,
 * so asking only about the cursor would MISS real buttons -- and the same
 * Meesho panel's home page has twenty-three ordinary controls on it. Either
 * signal counts, so this can never find less than asking for a control would.
 *
 * The innermost rule is what keeps it from matching half the page: `cursor`
 * passes down to everything inside a pressable thing, so plenty of elements
 * answer yes -- and only the smallest one carrying exactly the words being
 * looked for is counted. */
function looksPressable(node) {
  if (actsLikeAControl(node)) return true;
  return String(globalThis.getComputedStyle(node).cursor || '').toLowerCase() === 'pointer';
}

function actsLikeAControl(node) {
  const tag = String(node.tagName || '').toLowerCase();
  if (CONTROL_TAGS.includes(tag)) return true;
  if (tag === 'input') {
    const kind = String(node.type || '').toLowerCase();
    return kind === 'button' || kind === 'submit';
  }
  return CONTROL_ROLES.includes(String(node.getAttribute('role') ?? '').toLowerCase());
}

/** The words a person reads on this one thing. A button drawn as an `input`
 *  carries them in its value rather than between its tags. */
function wordsOn(node) {
  const tag = String(node.tagName || '').toLowerCase();
  if (tag === 'input') return node.value;
  return node.textContent;
}

function testIdOf(node) {
  return node.getAttribute('data-testid') ?? '';
}

function looksLike(node, how, what, exact) {
  if (how === BY_TEST_ID) {
    const id = testIdOf(node);
    return exact ? sameWords(id, what) : holdsWords(id, what);
  }
  if (how === BY_ROLE_AND_TEXT && !actsLikeAControl(node)) return false;
  if (how === BY_PRESSABLE_TEXT && !looksPressable(node)) return false;
  const said = wordsOn(node);
  return exact ? sameWords(said, what) : holdsWords(said, what);
}

/** Everything on the page that matches, innermost only.
 *
 *  **THE INNERMOST RULE IS NOT A REFINEMENT, IT IS WHAT MAKES COUNTING WORK.**
 *  A button with a span inside it holds the same words twice over -- so does
 *  every wrapper up to the body. Counted plainly, an ordinary button matches
 *  four or five times and every single lookup would refuse as ambiguous. What
 *  is meant is the smallest thing carrying those words, so anything that
 *  contains another match is not one itself.
 *
 *  For a control it is the same rule applied among controls only: a `span`
 *  inside a button is not a control, so the button stays the one match, and
 *  clicking a control is what the recipes ask for. */
function whatMatches(how, what, exact, near = '') {
  const all = everything(thePage()).filter(
    (node) => isPainted(node) && looksLike(node, how, what, exact)
  );
  const innermost = all.filter(
    (node) => !all.some((other) => other !== node && node.contains(other))
  );
  if (!near) return innermost;
  /* **WHICH ROW IT IS ON.** When a page lists every export ever made, each row
   * with its own Download, the words are identical and only the row differs.
   * The recipe says which day it wants; this keeps the ones sitting beside
   * those words.
   *
   * **IT ONLY EVER TAKES MATCHES AWAY.** So it cannot turn one right answer
   * into a wrong one -- at worst it removes the right one too, and then the
   * count is nought and the step refuses, which is the safe direction. */
  const wanted = words(near).toLowerCase();
  return innermost.filter((node) => {
    let up = node.parentNode;
    while (up) {
      /* **THE MOMENT IT TAKES IN ANOTHER MATCH, IT IS NO LONGER A ROW.** Walked
       * up without this, every match eventually reaches the whole page -- which
       * of course contains the words being looked for, so every row "matched"
       * and nothing was narrowed at all. That was the first version of this and
       * it read as working. */
      if (innermost.some((other) => other !== node && up.contains(other))) return false;
      if (words(up.textContent).toLowerCase().includes(wanted)) return true;
      up = up.parentNode;
    }
    return false;
  });
}

function refuseAnUnknownWay(how) {
  if (!WAYS_OF_FINDING.includes(how)) {
    /* NOT ANSWERED WITH NOUGHT. A way of finding something that this does not
     * understand, answered "nothing found", looks exactly like the thing
     * genuinely being absent -- and would be recorded as the platform having
     * renamed a button. */
    throw new Error(
      `"${how}" is not a way of finding something on a page. This knows ${WAYS_OF_FINDING.join(', ')}.`
    );
  }
}

function rest(ms) {
  return new Promise((done) => setTimeout(done, ms));
}

/* --------------------------------------------------- is somebody being asked
 *                                                       to sign in? */

/** A box a password goes into. The plainest sign a portal is asking. */
function aPasswordIsBeingAskedFor(page) {
  return everything(page).some(
    (node) =>
      String(node.tagName || '').toLowerCase() === 'input' &&
      String(node.type || '').toLowerCase() === 'password' &&
      isPainted(node)
  );
}

/* --------------------------------------------------------------- the door */

/**
 * The eight calls, ready to be handed one at a time from the background half.
 *
 * `go` and `takeFile` are handed in: see the note at the top of this file.
 * `signedOutSigns` are the words a signed-out portal puts on the screen, and
 * they come from the recipe file rather than from here -- this file knows no
 * platform.
 */
/** What the catcher said, if it really was the catcher. Otherwise nothing.
 *
 *  **THIS IS THE WHOLE OF A SECURITY FIX, AND IT IS FOUR LINES (D135).** The
 *  file a portal builds inside its own page can only be noticed from inside that
 *  page, beside the portal's own code and whatever adverts it carries. Before
 *  this, the extension believed anything that page said -- so an advert could
 *  hand over bytes of its own and they would have gone into the seller's Drive
 *  under a real report's name.
 *
 *  **THE SECRET IS MADE IN THE BACKGROUND AND PUT INTO THE PAGE AS AN ARGUMENT**,
 *  which is the only channel into that page the page itself cannot listen to. It
 *  is fresh for every file, so learning it from the genuine message -- which is
 *  the first moment it exists anywhere the page can see -- is learning it too
 *  late.
 *
 *  **NOTHING IS BELIEVED WHEN NOTHING IS BEING WAITED FOR**, which is what stops
 *  a message arriving between two reports being read as belonging to the second.
 */
export function theCatcherSaid(said, waitingFor) {
  if (!waitingFor) return null;
  if (!said || said.source !== said.currentTarget) return null;
  const data = said.data;
  if (!data || data.kartaan !== CAUGHT_A_FILE) return null;
  if (data.secret !== waitingFor) return null;
  return data;
}

/** What the catcher calls itself. One spelling, read by both halves. */
export const CAUGHT_A_FILE = 'kartaan-caught-a-file';

export function pageDoor({ go, takeFile, signedOutSigns } = {}) {
  if (typeof go !== 'function') {
    throw new Error('A door needs to be given a way of going to an address.');
  }
  if (typeof takeFile !== 'function') {
    throw new Error('A door needs to be given a way of taking the file a download produced.');
  }
  const signs = (signedOutSigns || []).map(words).filter(Boolean);
  if (signs.length < 2) {
    /* REFUSED RATHER THAN LEFT TO ANSWER "SIGNED IN" FOREVER. With no signs
     * to look for, `needs_signing_in` could only ever say no -- and a run that
     * cannot tell it has been signed out reports every report as a broken
     * button, which is how the reference's queue died on the spot. Two,
     * because the rule below needs two. */
    throw new Error(
      'A door needs at least two words that only a signed-out portal shows. Without them it '
      + 'could never tell that somebody has been signed out.'
    );
  }

  /**
   * How many things on the page match. Never which one.
   *
   * `patienceSeconds` is how long to keep looking before answering none. A
   * portal draws itself in pieces, so asking once and giving up is the same as
   * asking before the page exists.
   *
   * **IT WAITS A MOMENT LONGER AFTER THE FIRST THING APPEARS, AND THAT IS THE
   * NINE-DAY OUTAGE AGAIN.** A page part-way through drawing can hold the chart
   * legend and not yet the menu item of the same name. Answering the instant
   * one thing matches would say "exactly one" about a page that is about to
   * hold two -- and one is the answer that clicks.
   */
  async function find(how, what, exact = true, patienceSeconds = 0, near = '') {
    refuseAnUnknownWay(how);
    const giveUpAt = Date.now() + Math.max(0, Number(patienceSeconds) || 0) * 1000;
    for (;;) {
      if (whatMatches(how, what, exact, near).length > 0) {
        await rest(SETTLE_MS);
        return whatMatches(how, what, exact, near).length;
      }
      if (Date.now() >= giveUpAt) return 0;
      await rest(LOOK_AGAIN_MS);
    }
  }

  /**
   * Click the one thing that matches.
   *
   * **IT COUNTS AGAIN RATHER THAN TRUSTING THE COUNT IT WAS GIVEN.** The page
   * carries on drawing between one call and the next, and picking one of two is
   * the single thing this whole design exists to prevent. If it is not exactly
   * one now, nothing is clicked and the number is reported.
   */
  function click(how, what, exact = true, near = '') {
    refuseAnUnknownWay(how);
    const found = whatMatches(how, what, exact, near);
    if (found.length === 0) {
      throw new Error(`Nothing on the page matches "${what}", so nothing was clicked.`);
    }
    if (found.length > 1) {
      throw new Error(
        `${found.length} things on the page match "${what}", so which one was meant cannot be `
        + 'known. Nothing was clicked.'
      );
    }
    if (isSwitchedOff(found[0])) {
      /* **SAID, NOT SWALLOWED.** A browser ignores a click on a switched-off
       * button entirely, so this would otherwise report success having done
       * nothing at all -- and the step after it would fail somewhere else
       * saying something unrelated. Portals switch Submit off until a date
       * range is accepted, which is exactly the state worth being told about. */
      throw new Error(
        `"${what}" is on the page but switched off, so nothing was clicked.`
      );
    }
    found[0].click();
  }

  /**
   * Put a date range into the page.
   *
   * **EXACTLY TWO DATE BOXES, OR IT REFUSES AND SAYS HOW MANY IT FOUND.** Same
   * rule as everything else here: guessing which of three boxes is the start
   * date exports the wrong days, and a file of the wrong days is worse than no
   * file, because nothing about it looks wrong afterwards.
   *
   * **KNOWN LIMIT, WRITTEN DOWN RATHER THAN LEFT TO BE DISCOVERED:** it finds
   * boxes the page declares as dates. A portal that draws a calendar out of
   * plain text boxes is not driven by this, and it fails loudly saying it found
   * none -- it never half-works.
   */
  async function pickRange(start, end, patienceSeconds = 0) {
    const giveUpAt = Date.now() + Math.max(0, Number(patienceSeconds) || 0) * 1000;
    for (;;) {
      /* **WAITED FOR, because a date picker is drawn by the click before it.**
       * Asked the instant that click returns, the boxes are not there yet and
       * the step refuses saying it found none -- which reads as the portal
       * having changed and is nothing of the kind. */
      const boxes = everything(thePage()).filter(
        (node) =>
          String(node.tagName || '').toLowerCase() === 'input' &&
          String(node.type || '').toLowerCase() === 'date' &&
          isPainted(node)
      );
      if (boxes.length === 2) {
        putIn(boxes[0], start);
        putIn(boxes[1], end);
        return;
      }
      if (Date.now() >= giveUpAt) {
        throw new Error(
          `A date range needs two date boxes on the page and ${boxes.length} were found, so no `
          + 'dates were set.'
        );
      }
      await rest(LOOK_AGAIN_MS);
    }
  }

  /**
   * Anything sitting over the page, reported rather than closed.
   *
   * **REPORTED, NEVER CLOSED, AND THAT IS FROM HIS OWN CHROME ON 2026-08-27.**
   * The Meesho promotion's close control is an `<img>` with no class, no label,
   * no name and no text, and Escape does not close it -- so there is nothing to
   * aim at. What is worth doing is saying clearly that something is in the way,
   * because "button not found" sent a month of diagnosis at a button that was
   * there the whole time, underneath a dialog.
   *
   * **KNOWN LIMIT:** it reports what says of itself that it is a dialog. A
   * covering that declares nothing at all is invisible here.
   */
  function overlays() {
    return everything(thePage())
      .filter((node) => (saysItIsADialog(node) || sitsOverTheWholePage(node)) && isPainted(node))
      .map((node) => {
        const box = node.getBoundingClientRect();
        return {
          width: Math.round(Number(box && box.width) || 0),
          height: Math.round(Number(box && box.height) || 0),
          text: words(node.textContent).slice(0, OVERLAY_LIMIT),
          /* **WHETHER IT WOULD ACTUALLY SWALLOW A CLICK**, which is the only
           * thing that matters and is not the same as being big. */
          blocks: sitsOverTheWholePage(node),
        };
      });
  }

  /** What is on the page now, for a failure to carry with it. */
  function pageText() {
    return words(thePage().textContent).slice(0, PAGE_LIMIT);
  }

  /**
   * Is the portal asking somebody to sign in?
   *
   * **TWO STATES THAT LOOK ALIKE AND ARE NOT THE SAME THING.** Signed out,
   * Flipkart serves its public marketing site. Signed IN but part-way through
   * drawing, it shows the seller's own top bar and no sidebar yet. Across 71
   * real occurrences in the reference's log, 54 were the second and harmless --
   * and one message for both is why a month of them read as one problem.
   *
   * So a page that is merely unfinished says no: nothing here looks at what is
   * MISSING. It says yes on two things only, both of which are something being
   * present -- a box asking for a password, or the words a signed-out portal
   * puts up.
   *
   * **TWO OF THOSE WORDS, NOT ONE.** A single one of them turns up on a
   * signed-in page easily enough -- the reference's own signed-in Flipkart
   * sidebar carries "Growth". The public menu carries the whole set at once.
   */
  function needsSigningIn() {
    if (aPasswordIsBeingAskedFor(thePage())) return true;
    /* **EACH SIGN IS A WHOLE MENU ITEM, NOT A RUN OF LETTERS SOMEWHERE ON THE
     * PAGE, and that was found live on his own Meesho on 2026-08-27.** Read as
     * text anywhere, "Grow" matched inside "Grow Business" -- a word that is not
     * on the page at all as a thing you can press. That is the same loose match
     * that cost nine days of payments, sitting inside the fix for a different
     * problem. Asked for as a control carrying exactly those words, "Grow"
     * answers none and "Grow Business" answers one. */
    const seen = signs.filter((sign) => whatMatches(BY_ROLE_AND_TEXT, sign, true).length > 0);
    return seen.length >= 2;
  }

  return {
    go,
    find,
    click,
    pick_range: pickRange,
    take_file: takeFile,
    overlays,
    page_text: pageText,
    needs_signing_in: needsSigningIn,
  };
}

/** Switched off, either the way a form control says it or the way a portal's
 *  own `div` pretending to be a button says it. */
function isSwitchedOff(node) {
  if (node.disabled === true) return true;
  return String(node.getAttribute('aria-disabled') ?? '').toLowerCase() === 'true';
}

/* SOMETHING LAID OVER THE WHOLE PAGE -- what actually swallows a click.
 *
 * **THIS REPLACES JUDGING BY SIZE, and the reason is a near-miss measured on his
 * own Meesho on 2026-08-28.** The download menu the recipe opens ON PURPOSE
 * declares itself a dialog and is 232 x 196; the promotion that cost a month of
 * "button not found" is 414 x 330. The old rule refused at 300 x 200 -- **the
 * menu missed being called a covering by four pixels in one direction.** A
 * slightly larger menu, and the door would have refused to carry on because of a
 * menu it had just opened.
 *
 * **WHAT THEY REALLY DIFFER BY IS NOT SIZE.** The promotion sits on a full-screen
 * backdrop, laid over everything -- that is what a click aimed at the page hits.
 * A dropdown has no backdrop at all; a click outside it simply closes it.
 *
 * So: laid over the page rather than flowing with it, and covering nearly all of
 * it. Both are asked of the browser, not guessed. */
function sitsOverTheWholePage(node) {
  const laidOver = String(globalThis.getComputedStyle(node).position || '').toLowerCase();
  if (laidOver !== 'fixed' && laidOver !== 'absolute') return false;
  const box = node.getBoundingClientRect();
  const wide = Number(globalThis.window.innerWidth) || 0;
  const tall = Number(globalThis.window.innerHeight) || 0;
  if (!wide || !tall) return false;
  return box.width >= wide * MOST_OF_THE_PAGE && box.height >= tall * MOST_OF_THE_PAGE;
}

function saysItIsADialog(node) {
  if (String(node.tagName || '').toLowerCase() === 'dialog') return true;
  const role = String(node.getAttribute('role') ?? '').toLowerCase();
  if (role === 'dialog' || role === 'alertdialog') return true;
  return String(node.getAttribute('aria-modal') ?? '').toLowerCase() === 'true';
}

/* PUT INTO THE BOX THE WAY A PERSON WOULD, NOT THE WAY CODE WOULD.
 *
 * Both portals are built with React, and React keeps its own copy of what is in
 * every box. Assigning to `value` changes what is on the screen and not what
 * React believes, so the page submits the date it had before -- silently, with
 * the right date visible in the box the whole time. Going through the browser's
 * own setter and then saying the box changed is what a real key press does.
 *
 * The setter is asked for rather than assumed: it exists in a browser and not
 * in the stand-in the checks run against, and this is the one place in this
 * file where the two genuinely differ. */
function putIn(box, value) {
  const text = String(value);
  const asABrowserWould = browsersOwnSetter();
  if (asABrowserWould) asABrowserWould.call(box, text);
  else box.value = text;
  box.dispatchEvent(new Event('input', { bubbles: true }));
  box.dispatchEvent(new Event('change', { bubbles: true }));
}

function browsersOwnSetter() {
  const input = globalThis.HTMLInputElement;
  if (!input || !input.prototype) return null;
  const described = Object.getOwnPropertyDescriptor(input.prototype, 'value');
  return (described && described.set) || null;
}
