/* The ten things the Python side asks of a page, and nothing else.
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
 *     find(how, what, exact, patience, near, alsoSaying) -> HOW MANY things match
 *                                    `alsoSaying` is one more thing that same
 *                                    row must say, ANDed with `near`. It is what
 *                                    tells Flipkart's three Reports Centre rows
 *                                    apart, all of which carry the same day.
 *                                    `near` is a LIST of ways the wanted row
 *                                    could be named; any one of them will do
 *     click(how, what, exact, near, newestOfSeveral, alsoSaying)
 *                                    -> nothing, or throws
 *     pick_range(start, end)         -> nothing, or throws
 *     take_file()                    -> the bytes, or null if nothing came
 *     overlays()                     -> [{width, height, text, blocks}, ...]
 *     page_text()                    -> what is on the page now
 *     needs_signing_in()             -> true when the portal is asking
 *     wait(seconds)                  -> nothing, after that long
 *     click_away()                   -> nothing; shuts whatever is open
 *
 * **`wait` IS THE ONLY ONE THAT ASKS THE PAGE NOTHING**, and it exists because
 * a portal can be busy somewhere the page cannot see. Meesho builds an orders
 * export on its own servers and the page it was asked from does not change at
 * all while it happens -- so there is nothing a `find` could watch, and the
 * recipe can only say how long to leave it. The step kind that uses it is
 * `browser.WAIT`, and the reason is written there.
 *
 * **`click_away` IS THE ONLY ONE THAT NAMES NOTHING**, and it is here because
 * shutting a menu is not the same instruction as opening one. See the note on
 * the call itself.
 *
 * **EIGHT OF THE TEN ARE ANSWERED HERE. TWO ARE ABOUT THE BROWSER ITSELF AND
 * ARE HANDED IN.** `go` changes which page is open, which tears down anything
 * running inside the old one; `take_file` reads the bytes of a download, which
 * nothing inside a page is allowed to see.
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

/* The ten names, spelt exactly as the Python side spells them. The message
 * bridge passes these straight through, so there is no table anywhere turning
 * one spelling into another -- two records of one fact is the fault this
 * project has been caught by four times. */
/* **AND ONE QUESTION ONLY THE WALK ASKS, KEPT APART FROM THE PYTHON CONTRACT ON
 * PURPOSE.** `where_they_sit` names the shape of each match when a lookup finds
 * several -- added 2026-09-14, when his own ads FSN report refused twice on a
 * bare count that could not be reproduced by hand. **The Python door never asks
 * it**, so writing it into `THE_CALLS` would claim a contract that does not
 * exist; kept here, the list of eleven still says exactly what it always said. */
/* **AND TWO MORE, HIS RULING OF 2026-09-14:** `banners_seen` hands back every
 * banner the page showed while it was open -- words only, however fast it came
 * and went -- and `close_pop_ups` shuts Flipkart's notification panel and any
 * marked close button before a page's first step, the reference's own
 * `dismissFkPopups`. The Python door asks neither. */
export const ASKED_ONLY_BY_THE_WALK = Object.freeze(['where_they_sit', 'banners_seen', 'close_pop_ups',
  'try_signing_in',
  /* **AND TYPING (2026-09-15)** -- a campaign id into Flipkart's campaign search box.
   * The Python door refuses a report done once per campaign, so it asks none. */
  'type_in']);

export const THE_CALLS = Object.freeze([
  'go',
  'find',
  'click',
  'pick_range',
  'take_file',
  'overlays',
  'page_text',
  'needs_signing_in',
  'wait',
  'click_away',
  /* **THE ELEVENTH, AND THE ONLY ONE THAT BRINGS A VALUE BACK OUT OF A PAGE.**
   * Every other call here presses something, waits for something or counts
   * something. **Meesho sells no export of the day's views** -- the figure is on
   * a card on its dashboard and nowhere else -- so a door that could only make a
   * platform hand over files could never fetch it at all. */
  'read_number',
]);

/* The ways of describing a thing on a page. **These same words are in
 * `autosync/browser.py`**, because they cross the wire in every step. That
 * duplication is real and is not hidden: `tools/export_recipes.py` refuses to
 * write a recipe file naming a way of finding something that is not in this
 * list. */
export const BY_TEXT = 'text';
export const BY_ROLE_AND_TEXT = 'role';
export const BY_TEST_ID = 'test-id';
export const BY_PRESSABLE_TEXT = 'pressable';
/* **THE WORDS SAY WHICH BOX. THE BOX IS WHAT IS PRESSED.** Flipkart's Reports
 * Centre shows the words "Select Date Range" as a plain leaf with the calendar
 * hidden behind a box beside them -- no control tag, no role, no pointer cursor
 * on the words, and the box carries its own VALUE rather than the words. So no
 * way of finding above can reach it: `pressable` refuses the label, and anything
 * reading words refuses the box. The reference has never pressed the label
 * (`content/flipkart.js` StepD-0): it finds the leaf, walks up as far as five
 * ancestors and presses the input, calendar icon or date value beside it. */
export const BY_THE_CONTROL_BESIDE = 'beside';
/* **A REAL `<button>` AND NOTHING PRETENDING TO BE ONE.** Meesho's payments page
 * carries the single word "Download" twice by the time the last step runs: the
 * opener at the top right is a `div` with `role="button"`, and the one inside the
 * export modal is a real `<button>`. Every other way of finding matches both and
 * the step refuses as ambiguous -- measured on his own panel on 2026-09-11, and
 * said twice by his own runs. **Asking for a control cannot separate them**,
 * because `role="button"` is exactly how a page declares a div to be one.
 * `autosync/browser.py` carries the reasoning in full; the reference has told
 * them apart by the tag for months (`content/meesho.js handlePayments` searches
 * `querySelectorAll('button')` for this one button and `p, button, [role=button]`
 * for the opener two steps above it). */
export const BY_A_REAL_BUTTON = 'button';
/* **THE BUTTON ON THE ROW THESE WORDS NAME.** Flipkart's Reports Centre request
 * dialog lists five reports, each row a `span` naming it and a real `button`
 * reading `REQUEST REPORT` -- read off his own panel on 2026-09-11, row by row.
 * **The name is a `span` with `cursor: auto` and is not a control at all**, and
 * the five buttons read identical words, so by its words alone the step finds
 * five and refuses. The words say WHICH row; the button beside them is what is
 * pressed. `autosync/browser.py` carries the reasoning in full, including why
 * this is not `near` -- `near` names a row by the DAY, and a row named by
 * something that never changes is the same row every night. The reference has
 * done exactly this for months (`content/flipkart.js` StepC). */
export const BY_THE_BUTTON_BESIDE = 'button-beside';
const WAYS_OF_FINDING = Object.freeze([BY_TEXT, BY_ROLE_AND_TEXT, BY_TEST_ID, BY_PRESSABLE_TEXT,
  BY_THE_CONTROL_BESIDE, BY_A_REAL_BUTTON, BY_THE_BUTTON_BESIDE]);

/* **HOW FAR UP FROM THE LABEL TO LOOK FOR THE BOX IT LABELS.** Five, which is
 * the reference's own number. Not unlimited: walked far enough, every label's
 * ancestor is the page, and the page contains every input on it. */
const AS_FAR_UP_AS = 5;

/* **HOW FAR UP FROM A CONTROL TO LOOK FOR THE ROW IT SITS ON.** Six, which is
 * the reference's own number in both of its row matchers
 * (`content/meesho.js findExportDownloadByTodayDate` and
 * `findExportedFileDownloadBtn`, each `for (let lvl = 0; lvl < 6 ...)`).
 *
 * **AND IT IS A DIFFERENT QUESTION FROM THE FIVE ABOVE**, said out loud because
 * the two numbers look alike and are not one fact. That one asks how far a BOX
 * can sit from the words that label it. This asks how far a ROW can reach above
 * the control on it. Folded into one, a change made for one page would move the
 * other silently.
 *
 * **WITHOUT A LIMIT IT CLIMBS TO THE WHOLE PAGE, and on 2026-09-11 it did.** See
 * the claims panel, at the walk-up itself. */
const AS_FAR_UP_AS_A_ROW = 6;

/* HOW FAR ABOVE ITS LABEL A NUMBER SITS. **TWO, AND IT IS MEASURED, NOT CHOSEN.**
 *
 * Read off his own Meesho dashboard on 2026-09-11: the leaf reading `Views` has a
 * parent holding exactly `Views` and `(10 Sep)` -- the label and its own day, and
 * no number at all. **One level above that the card reads
 * `Views`, `(10 Sep)`, `34,877`, `14.15%`.** So one is too few.
 *
 * **AND THREE IS TOO MANY, which is the half worth writing down.** At three
 * levels the Views card and the Orders card MERGE into one block holding both
 * numbers -- so a climb of three would read the views figure for orders, quietly,
 * and a wrong number is worse than none because nothing about it looks wrong
 * afterwards. */
const A_NUMBER_SITS_THIS_FAR_ABOVE_ITS_LABEL = 2;

/* WHAT COUNTS AS A NUMBER: digits, and the commas a page groups them with.
 *
 * **BOTH OF THE THINGS IT HAS TO REFUSE SIT IN THE SAME CARD AS THE THING IT
 * WANTS.** `(10 Sep)` is the card's own day and `14.15%` is how much the figure
 * moved -- either would be taken by a rule that merely looked for digits. So the
 * shape is the whole of the leaf and nothing else: `34,877` yes, and neither of
 * those two. */
const A_PLAIN_NUMBER = /^\d{1,3}(?:,\d{3})*$|^\d+$/;

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
/* **`label` WAS ADDED ON 2026-09-11, WITH HIS WORD, AND IT IS THE ONLY WAY THE
 * REPORTS CENTRE TABS CAN BE REACHED.**
 *
 * Read off his own Flipkart Reports Centre, element by element: `Requested`,
 * `Scheduled` and `All` are each a **`<label>` with `cursor: default`** -- no
 * role, no button, and no pointer. **So neither way of looking could find them:**
 * not as a control, because `label` was not on this list, and not as something
 * pressable, because the cursor never changes over it. A recipe asking for the
 * Requested tab could only ever answer that it was not on the page.
 *
 * **A LABEL REALLY IS A CONTROL, WHICH IS WHY THIS IS NOT A WIDENING FOR
 * CONVENIENCE.** The browser itself gives a `<label>` its own behaviour: a
 * click on it is delivered to the input it labels. That is how these tabs work
 * -- each wraps a radio nobody can see. **It is the browser's own rule, not
 * Flipkart's**, which is the test everything on this list has to pass.
 *
 * **WHAT IT COULD HAVE COST AND WHY IT DOES NOT.** Widening what a lookup can
 * match can turn one match into two, and two is a refusal -- so a Meesho report
 * that works today could have started refusing. Two things stop it: only the
 * INNERMOST element carrying the words is counted, so a label wrapping a span of
 * the same text loses to the span; and every lookup that matters is matched
 * exactly. **Measured after the change: the four Meesho reports' own lookups
 * still answer exactly one each.** */
const CONTROL_TAGS = Object.freeze(['button', 'a', 'summary', 'label']);
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
/** An input somebody types into, rather than one drawn as a button. */
function isABoxSomebodyTypesInto(node) {
  if (String(node.tagName || '').toLowerCase() !== 'input') return false;
  const kind = String(node.type || '').toLowerCase();
  return kind !== 'button' && kind !== 'submit' && kind !== 'reset';
}

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
  /* **A BOX SOMEBODY TYPES INTO IS NEVER THE THING SOME WORDS NAME -- AND THE
   * POINTER CURSOR HAD LET IT BACK IN.** This door already says so for controls
   * ("a box somebody types into is not a control"), and a check holds it. But
   * asked for as something PRESSABLE, a search box with a pointer cursor passed,
   * and its words are its VALUE.
   *
   * **MEASURED ON HIS OWN ADS REPORT, 2026-09-14.** `fk_ads_fsn` refused three
   * times on *"2 things match Consolidated FSN Report"*, and the refusal finally
   * said where: *"<input> in <div> in <div>; <div> in <div> in
   * <div#popover-content>"*. **The second was the Report Type list's own search
   * box, holding the report's name as its value.** The option to press was the
   * `div` in the popover.
   *
   * **A BUTTON DRAWN AS AN INPUT STILL COUNTS** -- its value really is the words
   * on it -- which is the one case reading an input's value exists for. */
  if (how === BY_PRESSABLE_TEXT && isABoxSomebodyTypesInto(node)) return false;
  /* **THE TAG ITSELF, NOT WHAT THE PAGE CLAIMS ABOUT IT.** A `div` saying
   * `role="button"` is a control by every other test here and is not this. */
  if (how === BY_A_REAL_BUTTON && String(node.tagName || '').toLowerCase() !== 'button') {
    return false;
  }
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
function whatMatches(how, what, exact, near = [], alsoSaying = '') {
  const labels = everything(thePage()).filter(
    (node) => isPainted(node) && looksLike(node, how, what, exact)
  );
  const smallest = labels.filter(
    (node) => !labels.some((other) => other !== node && node.contains(other))
  );
  /* **AND FOR ONE WAY OF FINDING, WHAT WAS MATCHED IS NOT WHAT IS WANTED.** The
   * words are a label; the thing to press is the box beside them. Done here, so
   * the innermost rule has already picked the leaf that carries the words --
   * which is exactly what the reference starts from. */
  const asksForWhatIsBeside = how === BY_THE_CONTROL_BESIDE || how === BY_THE_BUTTON_BESIDE;
  const rows = theRows(near);
  const alsoSaid = words(String(alsoSaying || '')).toLowerCase();
  let all = smallest;
  if (how === BY_THE_CONTROL_BESIDE) all = theBoxesBeside(smallest);
  /* **THE ONE WAY OF FINDING THAT USES `alsoSaying` WITH NO DAY**, because it
   * looks at a fixed menu of reports rather than a list of files -- see the rule
   * and its reason in `autosync/browser.py`. */
  if (how === BY_THE_BUTTON_BESIDE) all = theButtonsBeside(smallest, alsoSaid);
  const innermost = asksForWhatIsBeside
    ? all.filter((node) => !all.some((other) => other !== node && node.contains(other)))
    : all;
  if (!rows.length) return innermost;
  /* **WHICH ROW IT IS ON.** When a page lists every export ever made, each row
   * with its own Download, the words are identical and only the row differs.
   * The recipe says which day it wants; this keeps the ones sitting beside
   * those words.
   *
   * **SEVERAL WAYS THE SAME DAY COULD BE WRITTEN, AND ANY OF THEM WILL DO.**
   * Neither portal writes a day only one way, and the working reference builds
   * five spellings on Flipkart and six on Meesho rather than choosing. They all
   * name the same day, so a longer list can only stop a right row being missed
   * over a leading nought -- it can never reach a different day's row.
   *
   * **IT ONLY EVER TAKES MATCHES AWAY.** So it cannot turn one right answer
   * into a wrong one -- at worst it removes the right one too, and then the
   * count is nought and the step refuses, which is the safe direction. */
  return innermost.filter((node) => {
    let up = node.parentNode;
    /* **AND IT STOPS CLIMBING, WHICH IT DID NOT UNTIL 2026-09-11.**
     *
     * **WHAT IT COST, MEASURED ON HIS OWN CLAIMS PANEL.** That panel's own
     * menu button carries the single word `Download`, exactly as every row in
     * the list below it does. Climbing from the button, **nine levels up**, the
     * page's own heading block happens to contain `11 Sep` -- so the button
     * counted as today's row. The real row matched **one level up**. Two
     * matched, the button is first in the page, and the step that takes the
     * newest of several took it: **the walk pressed the menu shut and then
     * waited five minutes for a file that was never asked for.**
     *
     * **THE SPELLING THAT DID IT IS THE ONE WITH NO YEAR** (`11 Sep`), which
     * `recipes.py` already calls the loosest thing in that file and keeps
     * knowingly. It is safe inside a row and is not safe nine levels above one.
     *
     * **SIX IS THE REFERENCE'S OWN NUMBER, not one chosen here.** Both of its
     * row matchers climb `for (let lvl = 0; lvl < 6 ...)` and give up --
     * `content/meesho.js findExportDownloadByTodayDate` and
     * `findExportedFileDownloadBtn`. **Kartaan generalised it to "keep going",
     * and this is what the generalisation bought.**
     *
     * **AND IT TAKES NOTHING AWAY FROM WHAT ALREADY WORKS.** Measured the same
     * day: Meesho's orders rows, its returns rows and its claims rows all match
     * at level one, and Flipkart's Reports Centre rows at their own row. */
    for (let howFar = 0; howFar < AS_FAR_UP_AS_A_ROW && up; howFar += 1) {
      /* **THE MOMENT IT TAKES IN ANOTHER MATCH, IT IS NO LONGER A ROW.** Walked
       * up without this, every match eventually reaches the whole page -- which
       * of course contains the words being looked for, so every row "matched"
       * and nothing was narrowed at all. That was the first version of this and
       * it read as working. */
      if (innermost.some((other) => other !== node && up.contains(other))) return false;
      const said = words(up.textContent).toLowerCase();
      /* **AND WHAT ELSE THE SAME ROW HAS TO SAY, ANDed WITH THE DAY.**
       * Flipkart's Reports Centre lists orders, returns and settled
       * transactions all asked for on the same night over the same range, so
       * all three rows end `To 06 Jun 2026` and only the report's own kind
       * separates them. The day alone matches three, the newest-of-several rule
       * then takes the topmost, and the payments file lands under the orders
       * name. **Asked of THIS ancestor, not of any other** -- the row that
       * carries the day is the row that must carry the kind, or the two tests
       * are being passed by two different rows. */
      if (rows.some((row) => said.includes(row))
          && (!alsoSaid || said.includes(alsoSaid))) return true;
      up = up.parentNode;
    }
    return false;
  });
}

/** The ways the wanted row could be named, tidied. **One string still counts as
 *  one way**, so a caller that has not been changed yet is not silently
 *  narrowing to nothing. */
function theRows(near) {
  const many = Array.isArray(near) ? near : [near];
  return many.map((one) => words(one).toLowerCase()).filter(Boolean);
}

/** For each label, the box it labels: the input, calendar icon or date value
 *  sitting beside it.
 *
 *  **THIS IS `content/flipkart.js` StepD-0, AND IT IS NOT A GENERALISATION OF
 *  IT.** From the label, walk up one ancestor at a time, at most five, and take
 *  the first of these inside that ancestor:
 *
 *    - a real input that is not hidden -- what the reference prefers;
 *    - failing that, an icon or anything a page calls a calendar;
 *    - failing that, anything painted, other than the label, that is an input.
 *
 *  **WHAT IS NOT COPIED IS THE REFERENCE'S LAST RESORT** -- clicking the whole
 *  container row, or the label's own next sibling, or its parent. That is the
 *  reference guessing, and a guess that presses a container is a click landing
 *  somewhere nobody has measured. Here, nothing found is nought found, and
 *  nought found refuses and says so. */
function theBoxesBeside(labels) {
  const found = [];
  for (const label of labels) {
    let up = label.parentNode;
    for (let step = 0; step < AS_FAR_UP_AS && up; step += 1) {
      const inside = everything(up).filter((node) => node !== label && isPainted(node));
      /* **AND A THIRD CHOICE, WHICH IS THE REFERENCE'S OWN AND WAS DROPPED FROM
       * HERE.** `D:\Control\WHAT-IS-NOT-DONE.md` names it: the reference has
       * three ways to reach Flipkart's date control and this had two.
       *
       * **MEASURED ON THE ADS OTHER REPORTS PAGE, 2026-09-11.** The `Date` label
       * there has exactly ONE sibling: a `div role="presentation"` with a
       * pointer cursor reading `This Week : 06-Sep-26 - 11-Sep-26`. **No input
       * and no calendar icon** -- so both branches above miss it, the step
       * refuses saying nothing is beside the label, and the seven ad reports can
       * never set a day.
       *
       * **IT IS LAST FOR A REASON AND THAT ORDER IS THE WHOLE SAFETY OF IT.** A
       * row with a real input still answers the input, so nothing that works
       * today changes. This only ever speaks where the first two found nothing.
       *
       * **AND IT IS STILL NOT THE REFERENCE'S LAST RESORT, which stays
       * refused** -- clicking the whole container row, or the label's own next
       * sibling whatever it is. Something the page shows as pressable is a
       * control; a container is a guess. */
      const box = inside.find(isABoxSomethingIsTypedIn)
        || inside.find(looksLikeACalendar)
        || inside.find(looksPressable);
      if (box && !found.includes(box)) { found.push(box); break; }
      up = up.parentNode;
    }
  }
  return found;
}

/** For each name, the real button on the row it names.
 *
 *  **THE SAME WALK AS `theBoxesBeside`, TAKING A BUTTON INSTEAD OF A BOX.** From
 *  the words, up one ancestor at a time, at most five, and the first real
 *  `<button>` painted inside that ancestor. **A real button and nothing
 *  pretending**, for the same reason `BY_A_REAL_BUTTON` exists: a row is full of
 *  divs and spans, and a guess that presses a container is a click landing
 *  somewhere nobody has measured.
 *
 *  **AND IT STOPS AT THE FIRST ANCESTOR THAT HAS ONE**, which is what keeps it
 *  on its own row. Flipkart's request dialog nests each row two levels deep
 *  inside a list of five, so a walk that kept going would reach the list and
 *  take the topmost row's button on every report. Measured on his own panel:
 *  the row's own button is one level up, and the list of five is three. */
function theButtonsBeside(names, alsoSaid = '') {
  const found = [];
  for (const name of names) {
    let up = name.parentNode;
    for (let step = 0; step < AS_FAR_UP_AS && up; step += 1) {
      /* **AND WHAT ELSE THAT ROW HAS TO SAY, WHICH IS WHAT KEEPS THIS OFF THE
       * WRONG HALF OF THE PAGE.** Read off his own Reports Centre with the
       * dialog open: the word `Orders` is a leaf in the dialog's own row AND a
       * leaf in the list of reports already requested behind it, and both walk
       * up to a button -- so without this the step finds two and refuses. The
       * dialog's row also says `REQUEST REPORT`; the list's row does not. */
      const said = words(up.textContent).toLowerCase();
      if (!alsoSaid || said.includes(alsoSaid)) {
        const button = everything(up).filter((node) => node !== name && isPainted(node))
          .find((node) => String(node.tagName || '').toLowerCase() === 'button');
        if (button && !found.includes(button)) { found.push(button); break; }
      }
      up = up.parentNode;
    }
  }
  return found;
}

/**
 * Where one match sits, in a few words: its tag, and what encloses it.
 *
 * **HIS OWN ADS FSN REPORT, 2026-09-14, IS WHY THIS EXISTS.** It refused saying
 * *"2 things match Consolidated FSN Report"* -- and by hand, on the same page,
 * opening the same list, there was exactly one. The page the walk kept was 400
 * characters and did not contain the words at all. **A refusal that names a
 * count and nothing else cannot be acted on, and the only way to find out was to
 * guess.** Named, the next refusal is the measurement.
 *
 * **ONLY THE SHAPE, NEVER THE PAGE'S WORDS OR ADDRESSES** -- a tag, a role, an
 * id, two levels up. Enough to tell a list option from a selected value or a
 * screen-reader announcement; nothing a seller would not want in a log.
 */
function whereItSits(node) {
  const one = (n) => {
    const tag = String(n.tagName || '?').toLowerCase();
    const role = n.getAttribute && n.getAttribute('role');
    /* **THE ATTRIBUTE AS WELL AS THE PROPERTY.** A browser keeps the two in
     * step; a page built by hand, or a check's stand-in, may set only one. */
    const rawId = n.id || (n.getAttribute && n.getAttribute('id')) || '';
    const id = rawId ? `#${String(rawId).slice(0, 24)}` : '';
    return `<${tag}${role ? ` role=${role}` : ''}${id}>`;
  };
  const chain = [one(node)];
  let up = node.parentNode;
  for (let step = 0; step < 2 && up && up.tagName; step += 1) {
    chain.push(one(up));
    up = up.parentNode;
  }
  return chain.join(' in ');
}

/**
 * Press one thing, or say plainly that it cannot be pressed.
 *
 * **`found[0].click is not a function` -- HIS OWN ADS REPORT, 2026-09-14, AND IT
 * IS WHY THIS EXISTS.** A calendar's month arrow is drawn as a picture, and the
 * innermost thing carrying it is an `<svg>` or a `<path>`. **`click()` is a
 * method of HTML elements and an SVG element has none**, so pressing the
 * innermost thing threw a JavaScript error -- which reached the seller as a
 * sentence about a function, saying nothing about which report, which page or
 * which control.
 *
 * **WALKING UP IS WHAT A PERSON'S CLICK DOES.** A picture inside a button is not
 * the button; the browser delivers the press to whatever encloses it. So this
 * starts at the thing that was found and takes the first ancestor that can
 * actually be pressed.
 *
 * **AND IF NOTHING ON THE WAY UP CAN BE, IT SAYS SO NAMING THE TAG** rather than
 * throwing a language error. A sentence a person can act on is the whole point
 * of this door.
 */
function pressIt(node, what, likeAMouse = false) {
  let up = node;
  for (let step = 0; step < AS_FAR_UP_AS && up; step += 1) {
    if (typeof up.click === 'function') {
      /* **BUTTON DOWN AND BUTTON UP FIRST, ONLY WHEN THE STEP SAYS SO** (2026-09-15).
       * Flipkart's campaign suggestion picks a campaign on button down; a bare
       * click selects nothing. Every other press is left exactly as it was. */
      if (likeAMouse && typeof up.dispatchEvent === 'function') {
        const AMouse = globalThis.MouseEvent || globalThis.Event;
        for (const kind of ['mousedown', 'mouseup']) {
          up.dispatchEvent(new AMouse(kind, { bubbles: true, cancelable: true }));
        }
      }
      up.click();
      return;
    }
    up = up.parentNode;
  }
  throw new Error(
    `"${what}" was found on the page as a <${String(node.tagName || '?').toLowerCase()}>, `
    + 'which is drawn rather than pressed, and nothing around it can be pressed either. '
    + 'Nothing was clicked.'
  );
}

/* A box something is typed in -- **any input the page has not hidden, not only
 * one the browser calls a date box.** Flipkart's is `type="text"` and holds the
 * range as its value (`DOCS.md:1803`), so asking for a real date box finds
 * nothing there. That is a different question from `isADateBox`, which is asked
 * when a range is being TYPED into two boxes, and the two are not folded
 * together. */
function isABoxSomethingIsTypedIn(node) {
  return String(node.tagName || '').toLowerCase() === 'input'
    && String(node.type || '').toLowerCase() !== 'hidden';
}

/* An icon or anything the page itself calls a calendar. **The reference's own
 * second choice**, and it is asked of what the page calls things rather than of
 * what they look like, because a picture has no words to read. */
function looksLikeACalendar(node) {
  if (String(node.tagName || '').toLowerCase() === 'svg') return true;
  const called = `${node.className || ''} ${node.getAttribute('class') ?? ''}`.toLowerCase();
  return called.includes('calendar') || called.includes('icon');
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
/* **A ONE-TIME CODE IS BEING ASKED FOR, AND ONLY THE SELLER HAS IT (A53, his
 * ruling 2026-09-16: *"for Flipkart it is 2 step ... third is OTP ... so seller
 * will be needed for the third step"*).** It matters twice over: nothing may
 * press on through a code box, and a code screen must not read as SIGNED IN --
 * it carries no password box, so without this the walk would carry on into a
 * portal it had never got into and fail somewhere else entirely, naming the
 * wrong thing. */
const A_CODE_IS_ASKED_FOR = /(otp|one[- ]?time|verification code|verify code|enter code)/i;

function aCodeIsBeingAskedFor(page) {
  return everything(page).some((node) => {
    if (String(node.tagName || '').toLowerCase() !== 'input' || !isPainted(node)) return false;
    const said = typeof node.getAttribute === 'function'
      ? ['name', 'id', 'placeholder', 'aria-label', 'autocomplete']
        .map((one) => String(node.getAttribute(one) ?? '')).join(' ')
      : '';
    return A_CODE_IS_ASKED_FOR.test(said) || String(node.getAttribute
      && node.getAttribute('autocomplete')).toLowerCase() === 'one-time-code';
  });
}

function aPasswordIsBeingAskedFor(page) {
  return everything(page).some(
    (node) =>
      String(node.tagName || '').toLowerCase() === 'input' &&
      String(node.type || '').toLowerCase() === 'password' &&
      isPainted(node)
  );
}

/* ------------------------------------------------------- reading a calendar
 *
 * **THE PART OF THIS FILE THAT WAS MISSING, AND ITS ABSENCE WAS A WHOLE
 * PLATFORM.** `pick_range` was written as "find two date boxes and type into
 * them". **Neither portal has date boxes.** Meesho draws a calendar and so does
 * Flipkart's Reports Centre, so the only strategy the step had was one that had
 * never worked anywhere. On his own panel on 2026-09-09: "0 were found, so no
 * dates were set" -- nought, because there never were any.
 *
 * **EVERY FORMAT AND EVERY COUNT BELOW IS THE WORKING REFERENCE'S**
 * (`content/meesho.js fillMeeshoDates`, `content/flipkart.js` StepD/StepE),
 * which has driven both calendars every night for months. None of it is
 * re-derived, because all of it was paid for against the real portals.
 *
 * **AND STILL NO PLATFORM IS NAMED HERE.** What is written down is how a
 * calendar is built in ordinary HTML terms -- a heading saying which month is
 * on show, cells saying which day they are, arrows to another month. Which
 * portal has one stays where every other portal fact in this product lives:
 * `autosync/recipes.py`.
 */

const WEEKDAYS = Object.freeze(['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']);
const MONTHS_SHORT = Object.freeze(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']);
const MONTHS_LONG = Object.freeze(['January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December']);

/* HOW MANY MONTHS TO STEP THROUGH BEFORE GIVING UP. Fourteen is the
 * reference's own number and covers more than a year, which is more than any
 * catching-up night has ever needed. */
const MONTHS_TO_STEP_THROUGH = 14;

/* HOW LONG A CALENDAR TAKES TO REDRAW ITSELF. All three are the reference's
 * numbers, measured against the real portals rather than chosen. */
const AFTER_A_MONTH_STEP_MS = 600;
const AFTER_A_DAY_MS = 300;
const BETWEEN_THE_TWO_DAYS_MS = 500;

/* HOW FAR UP FROM A MONTH'S HEADING ITS OWN PANEL OF DAYS CAN BE. Capped
 * because the walk otherwise reaches a container holding BOTH months of a
 * two-month calendar, and then "the 25th" means two different days. */
const LEVELS_UP_TO_A_MONTH_PANEL = 8;

/* A HEADING SAYING WHICH MONTH IS ON SHOW: "June 2026", "Jun 2026".
 *
 * **AND "September2026", WITH NOTHING BETWEEN THEM, WHICH IS NOT A TYPO.**
 * Measured on Flipkart's ads Other Reports calendar, 2026-09-11: it draws the
 * month and the year as TWO SEPARATE ELEMENTS -- a `div` reading `September` and
 * a `div` reading `2026` -- and their wrapper's own words run straight together.
 * This asked for whitespace between them, so **that calendar had no heading this
 * could see at all**, and its day cells carry no `aria-label` either. Nothing
 * could name a day on it, so the seven ad reports could never set one.
 *
 * **LOOSENING IT COSTS NOTHING, because the month name is checked separately.**
 * `whichMonth` has to recognise the first part as a real month, so a word that
 * merely ends in four digits is refused exactly as it was before. */
const A_MONTH_HEADING = /^([A-Za-z]{3,9})\s*(\d{4})$/;

/* WHAT AN ARROW TO ANOTHER MONTH LOOKS LIKE. Either it is named, or it is one
 * of the characters a portal draws instead of a word. */
const NAMED_ON = Object.freeze(['next']);
const NAMED_BACK = Object.freeze(['prev', 'back']);
/* **WRITTEN AS NUMBERS, NOT AS THE CHARACTERS THEMSELVES.** Every other file
 * in this extension is plain ASCII from end to end, and the commit gate reads
 * a diff through Windows' own default encoding -- which cannot read an arrow
 * and stops the commit with a decoding error rather than a sentence. These are
 * exactly the five characters the reference looks for, said in a way the whole
 * toolchain can read. */
const ARROWS_ON = Object.freeze(['>', '\u203a', '\u2192', '\u00bb', '\u25b6']);
const ARROWS_BACK = Object.freeze(['<', '\u2039', '\u2190', '\u00ab', '\u25c0']);

/** A box the page itself declares to be a date. */
function isADateBox(node) {
  return String(node.tagName || '').toLowerCase() === 'input'
    && String(node.type || '').toLowerCase() === 'date'
    && isPainted(node);
}

/** The smallest matches only -- the same rule `whatMatches` runs on, and for
 *  the same reason: a cell inside a cell is one thing, not two. */
function innermostOf(nodes) {
  return nodes.filter((node) => !nodes.some((other) => other !== node && node.contains(other)));
}

/** A day written `2026-08-25`, taken apart. Nothing else is a day. */
function aDay(iso) {
  const said = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso));
  if (!said) return null;
  const y = Number(said[1]);
  const m = Number(said[2]);
  const d = Number(said[3]);
  if (m < 1 || m > 12 || d < 1 || d > 31) return null;
  return { y, m, d };
}

/** One number per month, so two months can be compared and one can be told to
 *  be earlier than the other across a year end. */
function monthKey(y, m) {
  return y * 12 + (m - 1);
}

/** Which month a heading names, or -1. Read from the first three letters, so
 *  "Sep", "Sept" and "September" are all the same month -- which is the
 *  reference's own rule, and portals really do write all three. */
function whichMonth(said) {
  const start = words(said).slice(0, 3).toLowerCase();
  return MONTHS_SHORT.findIndex((one) => one.toLowerCase() === start);
}

/**
 * Every way a portal writes one day on the face of a calendar cell.
 *
 * **FOUR OF THEM, AND EACH ONE WAS PAID FOR.** The same seller's own Meesho
 * writes the same day two different ways -- "Fri May 01 2026" on orders and
 * returns, "Jun 2, 2026" on payments -- and that was found by payments quietly
 * not working. Flipkart writes "June 2, 2026" and "2 June 2026".
 *
 * **TRYING ALL FOUR IS NOT GUESSING.** Every one of them names the SAME day, so
 * whichever matches is the right cell. That is what makes this different from
 * guessing which of three boxes is the start date.
 */
function theWaysADayIsWritten(iso) {
  const day = aDay(iso);
  if (!day) return [];
  const { y, m, d } = day;
  const weekday = WEEKDAYS[new Date(y, m - 1, d).getDay()];
  return [
    `${weekday} ${MONTHS_SHORT[m - 1]} ${String(d).padStart(2, '0')} ${y}`,
    `${MONTHS_SHORT[m - 1]} ${d}, ${y}`,
    `${MONTHS_LONG[m - 1]} ${d}, ${y}`,
    `${d} ${MONTHS_LONG[m - 1]} ${y}`,
  ];
}

/** The two ways a month's heading is written, for a refusal to say what it
 *  looked for. */
function theWaysAMonthIsHeaded({ y, m }) {
  return [`${MONTHS_LONG[m - 1]} ${y}`, `${MONTHS_SHORT[m - 1]} ${y}`];
}

/** Every cell that says outright which day it is. */
function everyCellNaming(iso) {
  const ways = theWaysADayIsWritten(iso).map((one) => one.toLowerCase());
  return everything(thePage()).filter((node) => {
    if (!isPainted(node)) return false;
    const named = words(node.getAttribute('aria-label') ?? '').toLowerCase();
    if (named && ways.includes(named)) return true;
    return words(node.getAttribute('data-date') ?? '') === String(iso);
  });
}

/**
 * Every month heading on show, and which month each one is.
 *
 * **THIS IS ALSO WHAT SAYS A CALENDAR IS THERE AT ALL.** A page with no date
 * boxes and no month heading has no date picker drawn on it yet, which is a
 * page still being waited for rather than a page that has changed.
 */
function everyMonthOnShow() {
  const found = [];
  for (const node of everything(thePage())) {
    if (!isPainted(node)) continue;
    /* A HEADING IS A SMALL THING. Without this every wrapper up to the body
     * whose words happen to read as a month would count as one. The
     * reference caps it at three children and so does this. */
    if ((node.children || []).length > 3) continue;
    const said = A_MONTH_HEADING.exec(words(node.textContent));
    if (!said) continue;
    const which = whichMonth(said[1]);
    if (which === -1) continue;
    found.push({ node, key: monthKey(Number(said[2]), which + 1) });
  }
  const smallest = innermostOf(found.map((one) => one.node));
  return found.filter((one) => smallest.includes(one.node));
}

/**
 * Every cell carrying just the day number, under the heading of the month
 * wanted.
 *
 * **WALKED DOWN FROM THE HEADING, NEVER UP FROM THE CELL, AND THAT IS A FIX THE
 * REFERENCE PAID FOR.** A calendar draws two months side by side, and both
 * panels sit inside containers whose words hold BOTH headings -- so matching a
 * cell by what its ancestors say picked 10 May when 10 June was meant. Starting
 * at the right heading and looking down inside it cannot do that, and a
 * container that has taken in a second month is abandoned at once.
 */
function everyCellShowingTheDay({ y, m, d }) {
  const wanted = monthKey(y, m);
  const onShow = everyMonthOnShow();
  const dayOnItsOwn = String(d);
  for (const heading of onShow.filter((one) => one.key === wanted)) {
    let up = heading.node.parentNode;
    for (let level = 0; level < LEVELS_UP_TO_A_MONTH_PANEL && up; level += 1) {
      if (onShow.some((one) => one.key !== wanted && up.contains(one.node))) break;
      const inside = everything(up).filter(
        (node) => node !== up && isPainted(node) && words(wordsOn(node)) === dayOnItsOwn
      );
      const smallest = innermostOf(inside);
      if (smallest.length > 0) return smallest;
      up = up.parentNode;
    }
  }
  return [];
}

/** The arrow to the next month, or to the one before. */
function theWayToAnotherMonth(forwards) {
  const named = forwards ? NAMED_ON : NAMED_BACK;
  const arrows = forwards ? ARROWS_ON : ARROWS_BACK;
  return everything(thePage()).filter((node) => {
    if (!isPainted(node) || !looksPressable(node)) return false;
    const label = String(node.getAttribute('aria-label') ?? '').toLowerCase();
    const called = String(node.className || '').toLowerCase();
    if (named.some((word) => label.includes(word) || called.includes(word))) return true;
    return arrows.includes(words(wordsOn(node)));
  });
}

/**
 * A day a click would do nothing at all to.
 *
 * **READ OFF HIS OWN FLIPKART ON 2026-07-13.** A day whose report period the
 * portal has not opened yet keeps its ordinary look and every ordinary class,
 * and is given `pointer-events: none`. A click on it is swallowed silently, and
 * the step after it fails saying something unrelated -- which is exactly the
 * shape of failure this whole file exists to stop.
 *
 * **AND THERE IS A SECOND MECHANISM WHICH NOTHING ABOVE CAN SEE.** A day
 * genuinely outside the range gets a `blocked_out_of_range` class that **does
 * not touch pointer-events at all** -- confirmed live with the browser's own
 * tools a day later: such a cell reports `cursor: no-drop`, and a cell that can
 * really be pressed reports `cursor: pointer`. Same grey day on the screen, two
 * different techniques underneath, and one check could never catch both.
 *
 * **SO THE SECOND HALF IS ASKED FOR RATHER THAN ASSUMED, and that is the whole
 * of why it is an argument.** "Anything that is not a pointer is switched off"
 * is that one portal's habit and not a rule of browsers -- an ordinary unstyled
 * cell has no pointer cursor either, so a door that read it everywhere would
 * refuse days that are perfectly available on somebody else's calendar. The
 * recipe says which calendar this is; this file still knows no platform.
 */
function cannotBePressedAtAll(node, alsoByTheCursor = false) {
  if (isSwitchedOff(node)) return true;
  if (String(globalThis.getComputedStyle(node).pointerEvents || '').toLowerCase() === 'none') {
    return true;
  }
  if (!alsoByTheCursor) return false;
  return String(globalThis.getComputedStyle(node).cursor || '').toLowerCase() !== 'pointer';
}

/* --------------------------------------------------------------- the door */

/**
 * The ten calls, ready to be handed one at a time from the background half.
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
  /* **AN ADDRESS IS NOT A FILE, AND BELIEVING ONE IS BELIEVING THE PAGE.** The
   * bytes of a file crossed as bytes the browser itself copied; an address is a
   * string the page chose, and the extension will go and fetch whatever it names
   * with the seller's own cookies. **An address nobody narrowed is a way to put
   * anything at all into the seller's Drive under a real report's name** -- the
   * same harm D135 is about, by a shorter road.
   *
   * **SO IT IS ASKED THE SAME QUESTION AGAIN, HERE, WHERE IT CAN BE CHECKED.**
   * The catcher asks it too, but the catcher runs in the page's own world and
   * nothing decided there stands on its own. */
  if (data.address === undefined || aFileReallyComesFrom(data.address)) return data;
  /* **AND A LINK ON THE PLATFORM'S OWN SITE THAT IS NOT ON THE LIST IS BELIEVED
   * ONLY AS SOMETHING STILL TO BE PROVED** -- see `THE_PLATFORMS_OWN_SITES`. The
   * site is the one the browser stamped on the message, not anything the page
   * wrote into it. */
  if (onThePlatformsOwnSite(data.address, said.origin)) return { ...data, mustBeASpreadsheet: true };
  return null;
}

/** The addresses a caught link is worth taking, as text to be matched.
 *
 * **THIS IS THE WORKING REFERENCE'S OWN LIST, NOT ONE INVENTED HERE**
 * (`content/intercept.js` `_DOWNLOAD_PATTERNS`, lines 20-29, read on
 * 2026-09-11). It has been in daily use against both portals for months, and a
 * list guessed at fresh would be a list somebody adds to after each report it
 * quietly missed.
 *
 * **WHY THERE IS A LIST AT ALL, rather than taking any address.** While the
 * catcher is armed the portal is still an ordinary page: it fetches adverts, it
 * follows its own links, and the seller may still be using it. Suppressing
 * anything it opens would break his own browsing. These are the places a report
 * FILE actually comes from, and nothing else is touched.
 *
 * **AND IT IS ASKED ON BOTH SIDES** -- `theCatcherSaid` below asks the
 * same question of anything that arrives carrying an address, because the catcher
 * runs in the page's own world and nothing decided there can be trusted on its
 * own. That copy narrows what is SUPPRESSED; this one decides what is BELIEVED.
 */
export const WHERE_A_FILE_REALLY_COMES_FROM = Object.freeze([
  'storage.googleapis.com',
  'amazonaws.com',
  'seller-api.flipkart',
  'downloadorders',
  'downloadreturns',
  'downloadpayments',
  /* **NOT IN THE REFERENCE'S LIST, AND MEASURED, 2026-09-14.** Flipkart's listing
   * file is opened as `window.open("https://seller.flipkart.com/napi/listing/
   * stockFileDownload?...", "_blank")`; the reference's `/download` pattern needs
   * a slash before the word and does not match it. By its own path only, so the
   * portal's other addresses are never believed. */
  'seller.flipkart.com/napi/listing/stockfiledownload',
]);

/** The hosts a bare path word may count on: the platforms' own, and the storage they hand files out of. */
export const A_PLATFORM_OR_ITS_STORAGE = Object.freeze([
  'flipkart.com', 'flipkart.net', 'meesho.com', 'storage.googleapis.com', 'amazonaws.com',
]);

/** Is this an address a report file really comes from? **Written out a second
 *  time inside `catch-blob.js`'s injected function, for the same reason the name and the
 *  size are: it cannot reach anything outside itself.** A check reads both copies
 *  back out of the source so they cannot drift. */
export function aFileReallyComesFrom(address) {
  /* **THE HOST AND THE PATH ARE LOOKED AT, NEVER THE WHOLE STRING (review finding, 2026-10-05).** A
   * plain "contains" let `https://evil.example/x?storage.googleapis.com` and any host with
   * `downloadorders` in its name or path pass, and a script on the page could then have the
   * extension fetch any address with the seller's cookies. An entry with a dot and no slash is a
   * HOST (itself or a subdomain; `seller-api.flipkart` is a host prefix); an entry with a slash is
   * a host and path start; a bare word is a PATH word, and counts only on a host that belongs to
   * a platform or to the storage a platform hands its files out of. */
  let there;
  try {
    there = new URL(String(address || ''));
  } catch (notAnAddress) {
    return false;
  }
  if (there.protocol !== 'https:') return false;
  const host = there.hostname.toLowerCase();
  const path = there.pathname.toLowerCase();
  const aPlatformOrItsStorage = A_PLATFORM_OR_ITS_STORAGE
    .some((one) => host === one || host.endsWith(`.${one}`));
  return WHERE_A_FILE_REALLY_COMES_FROM.some((one) => {
    if (one.includes('/')) return `${host}${path}`.startsWith(one);
    if (!one.includes('.')) return aPlatformOrItsStorage && path.includes(one);
    if (one === 'seller-api.flipkart') return host.startsWith(one);
    return host === one || host.endsWith(`.${one}`);
  });
}

/* ----------------------- a link that is not on the list (his ruling, 2026-09-14)
 *
 * **HIS QUESTION, IN HIS WORDS:** *"what will it do if the download starts from a
 * real link like you just got, but it is not there on the list?"* Until now the
 * link was let through, Chrome refused it as a pop-up or nothing started, and the
 * report failed "Nothing began downloading" without naming the address -- which
 * is how the listing file's `stockFileDownload` went unseen for an afternoon.
 * **He asked for both halves of the answer:**
 *
 * 1. **A LINK NOTHING TOOK IS NAMED.** The catcher tells the page half every link
 *    or window it let go while armed -- the address only, never fetched -- and a
 *    failure then says what the platform tried to open.
 * 2. **A NEW LINK ON THE PLATFORM'S OWN SITE IS TAKEN, AND KEPT ONLY IF WHAT COMES
 *    BACK REALLY IS A SPREADSHEET.** Opened as a new window, on the very site the
 *    walk is on, and the bytes must open like an Excel or CSV file; a web page, a
 *    sign-in page or anything else is refused exactly as before.
 *
 * **THE LIMIT, WRITTEN DOWN RATHER THAN ASSUMED AWAY:** a script on the platform's
 * own page that opens a DIFFERENT real spreadsheet of that same site while a file
 * is awaited would have it kept under this report's name. The addresses on the
 * list above are not affected, and nothing from any other site is ever believed.
 */
export const THE_PLATFORMS_OWN_SITES = Object.freeze([
  'https://seller.flipkart.com',
  'https://supplier.meesho.com',
]);

/** Is this address on the same platform site as the page waiting for a file? */
export function onThePlatformsOwnSite(address, pageAddress) {
  let there;
  let here;
  try {
    there = new URL(String(address || ''));
    here = new URL(String(pageAddress || ''));
  } catch (notAnAddress) {
    return false;
  }
  if (there.protocol !== 'https:') return false;
  if (there.origin !== here.origin) return false;
  return THE_PLATFORMS_OWN_SITES.includes(there.origin);
}

/** Do these bytes open like an Excel workbook or a CSV file?
 *
 *  **ASKED OF THE BYTES, NEVER OF THE NAME OR THE TYPE THE SERVER CLAIMED.** An
 *  `.xlsx` is a zip and starts `PK\x03\x04`; an `.xls` starts `D0 CF 11 E0`; a
 *  CSV is text with no nought bytes, not a web page, with a line break and a
 *  comma, tab or semicolon on its first line. */
export function looksLikeASpreadsheet(bytes) {
  if (!bytes || bytes.length < 4) return false;
  const [a, b, c, d] = bytes;
  if (a === 0x50 && b === 0x4b && c === 0x03 && d === 0x04) return true;
  if (a === 0xd0 && b === 0xcf && c === 0x11 && d === 0xe0) return true;
  const opening = bytes.slice(0, 4096);
  if (opening.includes(0)) return false;
  const text = new TextDecoder('utf-8', { fatal: false }).decode(opening).replace(/^﻿/, '');
  if (text.trim().startsWith('<')) return false;
  const firstLine = text.split(/\r?\n/)[0];
  return /\r?\n/.test(text) && /[,\t;]/.test(firstLine);
}

/** What the catcher calls a link it did not take. **It carries no secret.** */
export const DECLINED_A_LINK = 'kartaan-declined-a-link';

/** The words a failure adds about links the page opened that nothing took.
 *
 *  **WITHOUT WHAT FOLLOWS THE `?`**, because a signed download link carries its
 *  key there, and a failure is written where people read it. At most three. */
export function whatThePageTriedToOpen(addresses) {
  const named = [];
  for (const one of addresses || []) {
    let shown;
    try {
      const at = new URL(String(one));
      if (at.protocol !== 'https:' && at.protocol !== 'http:') continue;
      shown = `${at.origin}${at.pathname}`.slice(0, 120);
    } catch (notAnAddress) {
      continue;
    }
    if (!named.includes(shown)) named.push(shown);
    if (named.length === 3) break;
  }
  if (!named.length) return '';
  return ` While it waited, the platform tried to open ${named.join(', ')}, which `
    + `${named.length === 1 ? 'is not a known report address, so it was' : 'are not known report addresses, so they were'} `
    + 'not taken.';
}

/* ------------------------------ banners and pop-ups (his ruling, 2026-09-14)
 *
 * **HIS WORDS:** *"Is extension designed to catch any banners ... successful or
 * failure? ... these banners come and go very frequently. So your code has to be
 * that fast."* A red banner on his returns page was gone before anybody could
 * read it, and nothing here had looked. **The reference watches for the banners
 * it expects** (`content/flipkart.js:1366-1380`, `:2771-2782`) and knows a toast
 * can vanish between two looks on a slowed tab (`:1382-1387`).
 *
 * **SO THIS IS NOT A LOOK, IT IS A WATCH.** The page is watched for anything that
 * says it is an alert or a status message, or is named like a toast, snackbar,
 * notification or banner, and its words are kept the moment it is drawn --
 * however quickly it goes again. Nothing in the seller's top bar or side menu. */
const A_BANNER_ROLE = Object.freeze(['alert', 'status']);
const A_BANNER_NAME = /toast|snack|notif|alert|banner|message/i;
const BANNERS_KEPT = 20;

/** The class a node carries, as text, whatever kind of node it is. */
function theClassOf(node) {
  const named = node && node.className;
  if (typeof named === 'string') return named;
  return (named && typeof named.baseVal === 'string') ? named.baseVal : '';
}

/** Is this inside the page's own top bar or side menu? */
function inTheTopBarOrMenu(node) {
  for (let up = node; up; up = up.parentNode) {
    const tag = String(up.tagName || '').toLowerCase();
    if (tag === 'header' || tag === 'nav') return true;
    if (/header|navigationrail|navbar|topbar|sidebar/i.test(theClassOf(up))) return true;
  }
  return false;
}

/** The words a banner shows, or nothing if this is not a banner. */
export function whatABannerSays(node) {
  if (!node || typeof node.getAttribute !== 'function') return '';
  const role = String(node.getAttribute('role') ?? '').toLowerCase();
  const live = String(node.getAttribute('aria-live') ?? '').toLowerCase();
  const looksLikeOne = A_BANNER_ROLE.includes(role) || live === 'polite' || live === 'assertive'
    || A_BANNER_NAME.test(theClassOf(node));
  if (!looksLikeOne || inTheTopBarOrMenu(node)) return '';
  const said = words(node.textContent);
  if (said.length < 3 || said.length > 240 || /^loading/i.test(said)) return '';
  return said;
}

/** Something that keeps every banner it is shown, in order, words only. */
export function aBannerRecorder({ now = () => Date.now() } = {}) {
  const seen = [];
  const look = (node) => {
    const queue = [node];
    let looked = 0;
    while (queue.length && looked < 60) {
      const one = queue.shift();
      looked += 1;
      const said = whatABannerSays(one);
      if (said) {
        const last = seen[seen.length - 1];
        if (!(last && last.words === said)) {
          seen.push({ at: now(), words: said });
          if (seen.length > BANNERS_KEPT) seen.shift();
        }
        continue;
      }
      for (const child of (one && one.children) || []) queue.push(child);
    }
  };
  return { look, seen: () => seen.map((one) => ({ ...one })) };
}

/** The words a control uses when it shuts something -- the reference's own list
 *  (`D:\rumee-auto-sync\content\meesho.js:301`). **Trusted only INSIDE an
 *  overlay**, because "ok" or "x" anywhere else on a portal page could mean
 *  anything at all. */
const THE_WORDS_THAT_CLOSE = Object.freeze(['close', 'skip', 'got it', 'dismiss',
  'maybe later', 'not now', 'no thanks', '\u2715', '\u2716', '\u00d7', 'x']);

/** Is this inside something laid over the page? */
function insideAnOverlay(node) {
  for (let up = node; up; up = up.parentNode) {
    if (/modal|overlay|dialog|popup|banner/i.test(theClassOf(up))) return true;
    const role = typeof up.getAttribute === 'function'
      ? String(up.getAttribute('role') ?? '').toLowerCase() : '';
    if (role === 'dialog' || role === 'alertdialog') return true;
  }
  return false;
}

/** A button that says it closes or dismisses something -- by its label, its
 *  test id or its class, never by words like "OK" that could mean anything.
 *
 *  **AND BY BEING A PICTURE OF A CROSS, MEASURED ON HIS OWN MEESHO PANEL,
 *  2026-09-16.** The promotion that stopped `me_views` is laid over the whole
 *  window and its only way out is an `<img>` whose source is named
 *  `cross-grey.svg`: no label, no test id, no role, not even a pointer cursor.
 *  Every rule above it asks the page to SAY it closes something, and that
 *  picture says nothing -- so nothing found it, three rounds running, and the
 *  report failed with the card sitting there readable underneath. */
function looksLikeACloseButton(node) {
  if (!node || typeof node.getAttribute !== 'function') return false;
  const label = String(node.getAttribute('aria-label') ?? '').trim().toLowerCase();
  if (label === 'close' || label === 'dismiss') return true;
  const testId = String(node.getAttribute('data-testid') ?? '').toLowerCase();
  if (testId.includes('close') || testId.includes('dismiss')) return true;
  const picture = `${node.getAttribute('src') ?? ''} ${node.getAttribute('alt') ?? ''}`;
  if (/cross|close|dismiss/i.test(picture)) return true;
  /* **THE REFERENCE'S OWN TEXT ROUTE**, kept to leaves inside an overlay. */
  if (insideAnOverlay(node) && !(node.children || []).length
    && THE_WORDS_THAT_CLOSE.includes(words(node.textContent || '').toLowerCase())) return true;
  const named = theClassOf(node).toLowerCase();
  return String(node.tagName || '').toLowerCase() === 'button'
    && (named.includes('close') || named.includes('dismiss'));
}

/** What the catcher calls itself. One spelling, read by both halves. */
export const CAUGHT_A_FILE = 'kartaan-caught-a-file';

/* **TEMPORARY, ASKED FOR ON 11 SEPTEMBER 2026, AND MEANT TO BE PUT BACK.**
 *
 * `true` lets a page in the walk's own tab ask the extension to run a report and
 * to read back what the panel shows -- which is the only way to watch the
 * fetching go wrong without asking the seller for a screenshot at every step.
 * `false` is the arrangement everything else here was built for: the page half
 * may ask for the seven things in `KNOWN` and nothing else, and the panel's own
 * questions are refused to anything that is not `panel.html`.
 *
 * **IT LIVES HERE BECAUSE BOTH HALVES HAVE TO AGREE ABOUT IT.** `content.js`
 * reads it to decide whether to listen at all, and `background.js` reads it to
 * decide whether to answer -- one fact, one place.
 *
 * **TURN IT OFF BY SETTING THIS LINE TO `false`.** Nothing else has to change:
 * `content.js` then registers no relay listener at all, so there is nothing on
 * the page left to reach, and `background.js` refuses those questions again. */
export const RELAY_TO_THE_PAGE = false;

/** Nothing, or the answer to give when this page's extension is gone for good.
 *
 *  **RELOADING THE EXTENSION DOES NOT STOP THE FILE ALREADY RUNNING IN AN OPEN
 *  TAB.** That file keeps going, and it belongs to the copy that was taken
 *  away -- so every word it tries to say to the other half throws "Extension
 *  context invalidated" for as long as that tab stays open. **Only reloading
 *  the page itself ends it.** Nothing here can end it, and nothing here should
 *  try: the seller may be working in that page.
 *
 *  **IT COST ABOUT AN HOUR TWICE ON 11 SEPTEMBER 2026**, both times because the
 *  swallow in `content.js` answered `null` -- and a `null` reads exactly like
 *  "the extension answered, and the answer was nothing". A dead page was read
 *  as an empty record, by the owner and by a session, on the same day.
 *
 *  **THE TWO CASES THROW ALIKE AND ARE NOTHING ALIKE.** A page torn down
 *  mid-sentence is the ORDINARY case here -- a walk goes somewhere on almost
 *  every turn -- and swallowing that is right and stays right. A page whose
 *  extension is gone is permanent, and everything it says afterwards is a lie.
 *
 *  **WHAT TELLS THEM APART IS `chrome.runtime.id`.** Chrome's own reference
 *  gives that as a string. **Chrome does not document what it becomes once a
 *  content script's context is invalidated** -- that gap is written down here
 *  rather than guessed past (Golden Rule 1) -- so the question is asked the way
 *  `webext-detect` asks it, `typeof chrome?.runtime?.id === 'string'`, and a
 *  handle that THROWS when it is read counts as gone as well, which is what
 *  Safari does with one.
 *
 *  **IT IS HERE AND NOT IN `content.js` BECAUSE IT IS A DECISION.** That file
 *  holds wiring by design, so that nothing in it needs proving.
 */
export function theExtensionIsGone(runtime) {
  let id;
  try {
    id = runtime && runtime.id;
  } catch (cannotEvenBeRead) {
    id = undefined;
  }
  if (typeof id === 'string') return null;
  return Object.freeze({
    extensionWasReloaded: true,
    /* **`wrong` IS THE WORD THE REST OF THIS EXTENSION ALREADY READS AS "this
     * failed, and here is why".** An answer carrying it cannot be filed as an
     * outcome by anything downstream, which is the whole point of it not being
     * `null`. */
    wrong: 'Kartaan Auto-sync was reloaded while this page was open. This page is still '
      + 'running the copy that was taken away and can no longer reach the extension, so '
      + 'nothing it says about a report is worth reading. Reload the page.',
  });
}

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
   *
   * **AND IF THE SETTLE FINDS NOUGHT, THE WAITING CARRIES ON. IT USED TO END
   * THERE, AND THAT IS WHAT BROKE `me_payments` (2026-09-11).** The count taken
   * after the settle was handed straight back, nought included -- so a thing
   * that was on the page and then was not ended the wait in a quarter of a
   * second, and a step allowed forty-five seconds spent 250 milliseconds of
   * them. **It was reported as "it is not on the page at all", which reads as a
   * portal that has changed rather than a page still drawing.** Measured on his
   * own payments panel twice: the whole night finished two to three seconds
   * after it started, which is a page load plus this settle and nothing else.
   *
   * **THE SETTLE ITSELF IS UNTOUCHED, AND SO IS WHAT IT ANSWERS.** A settle
   * that finds something still answers that number, second match included --
   * which is the whole reason it exists. The only change is that nought is no
   * longer an answer while there is patience left to spend.
   *
   * **THE REFERENCE NEVER MEETS THIS BECAUSE IT DOES NOT LOOK SO SOON**
   * (`content/meesho.js handlePayments`): it sleeps four to five seconds on
   * landing before it so much as looks, and then tries five times, two seconds
   * apart. This page half runs at `document_idle`, which is far earlier than
   * that -- so looking early is this product's own habit, and a lookup that
   * gives up on the first flicker is what makes it cost a report.
   */
  async function find(how, what, exact = true, patienceSeconds = 0, near = [],
    alsoSaying = '') {
    refuseAnUnknownWay(how);
    const giveUpAt = Date.now() + Math.max(0, Number(patienceSeconds) || 0) * 1000;
    for (;;) {
      let many = whatMatches(how, what, exact, near, alsoSaying).length;
      if (many > 0) {
        await rest(SETTLE_MS);
        many = whatMatches(how, what, exact, near, alsoSaying).length;
        if (many > 0) return many;
      }
      if (Date.now() >= giveUpAt) return 0;
      await rest(LOOK_AGAIN_MS);
    }
  }

  /**
   * The number the label on the page names, or a refusal saying why not.
   *
   * **THE ONE CALL THAT BRINGS A VALUE BACK OUT OF A PAGE**, and it exists
   * because Meesho sells no export of the day's views: the figure is on a card on
   * its dashboard and nowhere else.
   *
   * **IT REFUSES ON TWO MATCHES EXACTLY AS A CLICK DOES, and here that is not
   * caution, it is the difference between two real numbers.** `Orders` on his own
   * dashboard matches twice -- the card and the sidebar item of the same name --
   * and a rule that took the first would read whatever the sidebar happens to sit
   * beside. The recipe narrows by the day the card carries; this refuses if that
   * was not enough.
   */
  async function readNumber(how, what, exact = true, patienceSeconds = 0, near = [],
    alsoSaying = '') {
    refuseAnUnknownWay(how);
    const many = await find(how, what, exact, patienceSeconds, near, alsoSaying);
    if (many === 0) {
      throw new Error(`Nothing on the page matches "${what}", so no number was read.`);
    }
    if (many > 1) {
      throw new Error(
        `${many} things on the page match "${what}", so which number was meant cannot be `
        + 'known. Nothing was read.'
      );
    }
    const label = whatMatches(how, what, exact, near, alsoSaying)[0];
    let up = label.parentNode;
    for (let k = 0; k < A_NUMBER_SITS_THIS_FAR_ABOVE_ITS_LABEL && up; k += 1) {
      const found = theFirstPlainNumberIn(up);
      if (found !== null) return found;
      up = up.parentNode;
    }
    /* **SAID AS WHAT IT IS.** "Not found" would send somebody looking for a label
     * that is on the page in front of them. What is missing is the number. */
    throw new Error(
      `"${what}" is on the page and there is no plain number beside it. Either the card `
      + 'has not finished drawing, or the platform has changed how it is laid out.'
    );
  }

  /**
   * Click the one thing that matches.
   *
   * **IT COUNTS AGAIN RATHER THAN TRUSTING THE COUNT IT WAS GIVEN.** The page
   * carries on drawing between one call and the next, and picking one of two is
   * the single thing this whole design exists to prevent. If it is not exactly
   * one now, nothing is clicked and the number is reported.
   */
  function click(how, what, exact = true, near = [], newestOfSeveral = false,
    alsoSaying = '', likeAMouse = false) {
    refuseAnUnknownWay(how);
    const found = whatMatches(how, what, exact, near, alsoSaying);
    if (found.length === 0) {
      throw new Error(`Nothing on the page matches "${what}", so nothing was clicked.`);
    }
    /* **SEVERAL RIGHT ROWS IS NOT SEVERAL WRONG ONES, AND ONLY A CALLER THAT
     * NARROWED BY A DAY MAY SAY SO.** The nine-day payments outage was a chart
     * legend reading like a menu item with NOTHING narrowing the two apart.
     * Here `near` has already cut the page's ten rows down to the ones carrying
     * the day that was asked for, so everything left is genuinely that day --
     * and the seller having run the same export twice in one morning is the
     * ordinary reason two remain. **The newest is the topmost**, and
     * `everything` walks the page in the order it is written, so that is
     * `found[0]`. With nothing narrowed -- no `near`, or a `near` that named no
     * day -- this is the refusal it has always been. */
    if (found.length > 1 && !(newestOfSeveral && theRows(near).length)) {
      throw new Error(
        `${found.length} things on the page match "${what}", so which one was meant cannot be `
        + `known. Nothing was clicked. They are: ${found.slice(0, 4).map(whereItSits).join('; ')}.`
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
    pressIt(found[0], what, likeAMouse);
  }

  /**
   * Type words into the one box that matches (2026-09-15).
   *
   * **TYPED, NOT SET.** Flipkart's campaign search only starts when the box is
   * typed into. The reference types with the page's own insert-text command and
   * says why: setting the value "doesn't trigger search"
   * (`content/flipkart.js` `_handleFkAdsOverall`). The value is set directly only
   * when that command is missing or did not put the words in.
   */
  function typeIn(how, what, exact = true, near = [], alsoSaying = '', words = '') {
    refuseAnUnknownWay(how);
    const text = String(words);
    const found = whatMatches(how, what, exact, near, alsoSaying);
    if (found.length === 0) {
      throw new Error(`Nothing on the page matches "${what}", so nothing was typed.`);
    }
    if (found.length > 1) {
      throw new Error(
        `${found.length} things on the page match "${what}", so which box was meant cannot be `
        + 'known. Nothing was typed.'
      );
    }
    const box = aBoxAtOrIn(found[0]);
    if (!box) {
      throw new Error(`"${what}" is on the page but nothing there can be typed into, so nothing was typed.`);
    }
    if (isSwitchedOff(box)) {
      throw new Error(`"${what}" is on the page but switched off, so nothing was typed.`);
    }
    if (typeof box.focus === 'function') box.focus();
    if (typeof box.select === 'function') box.select();
    const page = box.ownerDocument;
    let typed = false;
    try {
      if (page && typeof page.execCommand === 'function') {
        page.execCommand('selectAll');
        typed = Boolean(page.execCommand('insertText', false, text));
      }
    } catch (wrong) {
      typed = false;
    }
    if (!typed || box.value !== text) putIn(box, text);
  }

  /**
   * Put a date range into the page.
   *
   * **TWO SHAPES, AND THE PRODUCT ONLY EVER HAD ONE OF THEM.** This was written
   * to find two date boxes and type into them. On his own Meesho panel on
   * 2026-09-09 it said "0 were found, so no dates were set" -- **nought,
   * because Meesho has no date boxes at all. It has a calendar**, and so does
   * Flipkart's Reports Centre. The one strategy this had worked on neither
   * portal. The knowledge below is carried across from the working reference,
   * `content/meesho.js fillMeeshoDates` and `content/flipkart.js` StepD/StepE,
   * which have driven both calendars every night for months.
   *
   * **AND IT IS STILL NO PLATFORM KNOWLEDGE.** Not one Meesho or Flipkart word
   * is in here. What is here is how a CALENDAR is built in ordinary HTML terms:
   * a heading saying which month is on show, cells saying which day they are,
   * and arrows to another month. Every recipe in `autosync/recipes.py` is
   * untouched by this.
   *
   * **EXACTLY TWO DATE BOXES, OR A CALENDAR, AND NOTHING IN BETWEEN.** Same
   * rule as everything else here: guessing which of three boxes is the start
   * date exports the wrong days, and a file of the wrong days is worse than no
   * file, because nothing about it looks wrong afterwards.
   */
  async function pickRange(start, end, patienceSeconds = 0, switchedOffDaysChangeTheCursor = false) {
    const giveUpAt = Date.now() + Math.max(0, Number(patienceSeconds) || 0) * 1000;
    for (;;) {
      /* **WAITED FOR, because a date picker is drawn by the click before it.**
       * Asked the instant that click returns, neither the boxes nor the
       * calendar is there yet and the step refuses saying it found none --
       * which reads as the portal having changed and is nothing of the kind. */
      const boxes = everything(thePage()).filter(isADateBox);
      if (boxes.length === 2) {
        putIn(boxes[0], start);
        putIn(boxes[1], end);
        return;
      }
      /* **A CALENDAR IS ONLY TRIED WHEN THERE ARE NO BOXES AT ALL.** One box
       * and a calendar, or three, is a page nobody has read yet -- and picking
       * a strategy in that state is the guess this whole file exists to
       * refuse. */
      /* **A MONTH HEADING IS NOT WHAT SAYS A CALENDAR IS THERE, and that was
       * read off his own Meesho on 2026-09-09.** Its month is a DROPDOWN of all
       * twelve names, so what the heading reads is
       * "JanuaryFebruaryMarch..." and never "September 2026" -- no heading here
       * can ever match. Meanwhile its day cells say outright
       * `aria-label="Tue Sep 01 2026"`, which is the first of the four ways
       * `theWaysADayIsWritten` already writes. So this refused while holding the
       * answer. **A cell naming the day wanted is a calendar, heading or no
       * heading**, which is the reference's own order: it never asks whether a
       * calendar is showing, it looks for the day. */
      if (boxes.length === 0
        && (everyCellNaming(start).length > 0 || everyMonthOnShow().length > 0)) {
        await clickTheDay(start, switchedOffDaysChangeTheCursor);
        /* HALF A SECOND BETWEEN THE TWO, WHICH IS THE REFERENCE'S OWN NUMBER.
         * A range picker redraws itself once the first day is taken. */
        await rest(BETWEEN_THE_TWO_DAYS_MS);
        await clickTheDay(end, switchedOffDaysChangeTheCursor);
        return;
      }
      if (Date.now() >= giveUpAt) {
        throw new Error(
          'A date range needs two date boxes on the page, or a calendar to press days on. '
          + `${boxes.length} date boxes were found, no cell on the page said it was `
          + `${theWaysADayIsWritten(start).map((w) => `"${w}"`).join(' or ')}, and no month `
          + 'heading was showing either, so no dates were set.'
        );
      }
      await rest(LOOK_AGAIN_MS);
    }
  }

  /**
   * Press one day on a calendar.
   *
   * Three things happen, in the order the reference does them: step the
   * calendar to the month the day is in, find the one cell that is that day,
   * and refuse rather than press anything ambiguous or switched off.
   */
  async function clickTheDay(iso, switchedOffDaysChangeTheCursor = false) {
    const day = aDay(iso);
    if (!day) {
      throw new Error(`"${iso}" is not a day, so it cannot be found on a calendar. No dates were set.`);
    }
    await bringTheMonthIntoView(day);

    /* **THE CELL THAT NAMES ITSELF COMES FIRST**, because it can only be one
     * day. The day NUMBER under a heading is a reading of the page; an
     * aria-label saying "Fri May 01 2026" is the page saying it outright. */
    const named = innermostOf(everyCellNaming(iso));
    let cells = named.length > 0 ? named : everyCellShowingTheDay(day);

    /* **A MONTH'S GRID ALSO DRAWS THE NEXT MONTH'S FIRST DAYS, GREYED -- MEASURED
     * ON HIS FLIPKART TRAFFIC CALENDAR, 2026-09-14.** The `Sep 2026` panel reads
     * `31 1 2 ... 30 1 2 3 4`, the spill-over days `cursor: not-allowed`, so
     * asking for 09-01 found two "1"s and refused. On a calendar that says a day
     * is off in the cursor, only the days that can be pressed are candidates;
     * none pressable is still the switched-off answer below. */
    if (cells.length > 1 && switchedOffDaysChangeTheCursor) {
      const pressable = cells.filter((cell) => !cannotBePressedAtAll(cell, true));
      cells = pressable.length > 0 ? pressable : [cells[0]];
    }

    if (cells.length === 0) {
      throw new Error(
        `${iso} is not on the calendar. It was looked for as a cell naming itself `
        + `${theWaysADayIsWritten(iso).map((w) => `"${w}"`).join(' or ')}, and as the day `
        + `"${day.d}" under a heading reading `
        + `${theWaysAMonthIsHeaded(day).map((w) => `"${w}"`).join(' or ')}. No dates were set.`
      );
    }
    if (cells.length > 1) {
      /* **AMBIGUITY IS A REFUSAL, NOT A COIN TOSS**, and it is the same rule
       * `find` answers a count for. The wrong day fetches a real file of the
       * wrong days, and nothing about it looks wrong afterwards. */
      throw new Error(
        `${cells.length} things on the calendar say they are ${iso}, so which one was meant `
        + 'cannot be known. No dates were set.'
      );
    }
    if (cannotBePressedAtAll(cells[0], switchedOffDaysChangeTheCursor)) {
      /* **SAID, NOT SWALLOWED, and this is read off his own Flipkart on
       * 2026-07-13.** A day whose report period the portal has not opened yet
       * keeps its ordinary look and is given `pointer-events: none` -- so a
       * click on it does nothing whatever, and the step AFTER this one fails
       * saying something unrelated. It is also not a fault: the day becomes
       * available later, and the night is meant to come back for it.
       *
       * **AND ON A CALENDAR THAT SAYS SO IN THE CURSOR, THAT IS ASKED TOO.**
       * Flipkart's second way of switching a day off leaves pointer-events
       * alone entirely, so the line above sees nothing at all -- see
       * `cannotBePressedAtAll`. Which calendar this is comes from the recipe. */
      const notBuilt = new Error(
        `${iso} is on the calendar but the portal has it switched off, which is what it does `
        + 'with a day whose report it has not built yet. No dates were set.'
      );
      /* **MARKED, NOT READ OUT OF THE WORDS -- HIS RULING, 2026-09-14.** A day
       * the portal has not built is "not available yet", not a failure: the walk
       * answers it as its own state and the night comes back for the day. The
       * walk tells the two apart by this mark, never by matching the sentence,
       * which is free to change. */
      notBuilt.dayNotAvailable = true;
      throw notBuilt;
    }
    pressIt(cells[0], iso);
    await rest(AFTER_A_DAY_MS);
  }

  /**
   * Step the calendar until the month wanted is on show.
   *
   * **FORWARDS OR BACKWARDS, up to fourteen steps -- the reference's own
   * number, which covers more than a year.** A night catching up an old day
   * needs the arrow the other way, and a calendar that only went forwards would
   * walk away from the day it wanted.
   */
  async function bringTheMonthIntoView(day) {
    const wanted = monthKey(day.y, day.m);
    for (let step = 0; step < MONTHS_TO_STEP_THROUGH; step += 1) {
      const onShow = everyMonthOnShow();
      /* Nothing to steer by. Say nothing here and let the day lookup report
       * what it could not find -- it says what it looked for, and this cannot. */
      if (onShow.length === 0) return;
      if (onShow.some((one) => one.key === wanted)) return;
      /* **A CALENDAR CAN SHOW TWO MONTHS AT ONCE**, so the direction is decided
       * against the whole of what is on show rather than the first heading
       * found. Every month on show earlier than the one wanted means forwards. */
      const forwards = Math.max(...onShow.map((one) => one.key)) < wanted;
      const arrows = innermostOf(theWayToAnotherMonth(forwards));
      if (arrows.length === 0) return;
      /* **THE FIRST ONE, AND THIS IS THE ONE PLACE HERE THAT DOES NOT REFUSE ON
       * SEVERAL.** Counting exists to stop an IRREVERSIBLE wrong action -- the
       * wrong menu item fetched the wrong thing for nine days, the wrong day
       * cell writes a file of the wrong days. A month arrow is neither: the
       * month on show is read again at the top of this loop, so pressing the
       * wrong one is a step that gets noticed and corrected, and pressing none
       * at all is a certain failure. The reference takes the first too. */
      pressIt(arrows[0], forwards ? 'the next month arrow' : 'the previous month arrow');
      await rest(AFTER_A_MONTH_STEP_MS);
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
    /* **A CODE SCREEN IS STILL SIGNED OUT.** See `aCodeIsBeingAskedFor`. */
    if (aCodeIsBeingAskedFor(thePage())) return true;
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

  /**
   * Let this much time pass, and look at nothing.
   *
   * **THE ONE CALL THAT ASKS THE PAGE NOTHING.** Everything else here waits FOR
   * something and stops the moment it appears. Meesho's orders export is built
   * on Meesho's own servers, and the page it was asked from shows nothing at
   * all while that happens -- so there is nothing to watch, only time to pass.
   * `browser.WAIT` says why, and `autosync/recipes.py` holds the number.
   */
  function waitFor(seconds) {
    return rest(Math.max(0, Number(seconds) || 0) * 1000);
  }

  /**
   * Shut whatever the page has open, by clicking where nothing is.
   *
   * **THIS IS THE REFERENCE'S OWN GESTURE, CARRIED ACROSS AS IT IS**
   * (`content/meesho.js:865`, `document.body.click()`). A menu on a portal is
   * shut by clicking OUTSIDE it -- that is what every one of them listens for.
   *
   * **AND IT IS HERE RATHER THAN BEING A SECOND PRESS OF THE CONTROL THAT
   * OPENED IT.** Pressing the opener again is a guess that the control toggles,
   * and a guess that is wrong is silent: both presses do nothing, the menu is
   * never redrawn, and six polls become three minutes of a walk that looks
   * exactly like one that is working. Nothing in this repository can settle
   * whether Meesho's opener toggles. Clicking away needs no such answer.
   *
   * **A CLICK ON THE BODY IS NOT A CLICK ON ANYTHING IN IT.** It is dispatched
   * at the body itself, so nothing inside the page is pressed by it; it travels
   * upward, which is where a menu's own "clicked outside me" listener sits.
   */
  function clickAway() {
    thePage().click();
  }

  /**
   * Where every match sits, as a few words each -- never the page's own words.
   *
   * **ASKED BY THE WALK WHEN A LOOKUP FINDS SEVERAL, because the walk refuses
   * on a COUNT and never reaches `click`'s own refusal.** His own ads FSN report
   * refused twice on 2026-09-14 saying *"2 things match"*, and the detail `click`
   * had been taught to give never surfaced -- the walk had asked `find` for a
   * number and written its own sentence. A count alone could only be answered by
   * guessing; this is the measurement instead.
   */
  function whereTheySit(how, what, exact = true, near = [], alsoSaying = '') {
    refuseAnUnknownWay(how);
    return whatMatches(how, what, exact, near, alsoSaying).slice(0, 4).map(whereItSits);
  }

  /* **THE WATCH STARTS WITH THE DOOR, WHICH IS AS SOON AS THE PAGE HALF LOADS.**
   * Every change the page makes is looked at as it happens, so a banner drawn
   * and removed within a second is still kept. A browser with nothing to watch
   * with -- the stand-in the checks use -- simply records nothing. */
  const bannersHere = aBannerRecorder();
  const Watching = globalThis.MutationObserver;
  const root = globalThis.document && (globalThis.document.body || globalThis.document.documentElement);
  if (typeof Watching === 'function' && root) {
    try {
      new Watching((changes) => {
        for (const change of changes) {
          for (const added of change.addedNodes || []) {
            if (added && added.nodeType === 1) bannersHere.look(added);
          }
          const target = change.target;
          if (change.type === 'characterData' && target && target.parentNode) {
            bannersHere.look(target.parentNode);
          }
          if (change.type === 'attributes' && target && target.nodeType === 1) bannersHere.look(target);
        }
      }).observe(root, {
        childList: true, subtree: true, characterData: true,
        attributes: true, attributeFilter: ['class', 'role', 'aria-live'],
      });
    } catch (couldNotWatch) {
      /* Nothing else depends on it: a failure just says less. */
    }
  }

  /** Shut what is in the way before a page's first step -- the reference's own
   *  `dismissFkPopups`, narrowed to controls that say they close something. */
  function closePopUps() {
    const closed = [];
    const markAllRead = everything(thePage()).find((node) => isPainted(node)
      && !(node.children || []).length && words(node.textContent) === 'Mark All as Read');
    if (markAllRead && typeof globalThis.KeyboardEvent === 'function'
      && globalThis.document && typeof globalThis.document.dispatchEvent === 'function') {
      globalThis.document.dispatchEvent(
        new globalThis.KeyboardEvent('keydown', { key: 'Escape', bubbles: true })
      );
      closed.push('the notification panel');
    }
    const pressed = new Set();
    for (let round = 0; round < 3; round += 1) {
      const next = everything(thePage()).find((node) => !pressed.has(node) && isPainted(node)
        && looksLikeACloseButton(node) && !inTheTopBarOrMenu(node));
      if (!next) break;
      pressed.add(next);
      try {
        pressIt(next, 'a close button');
        closed.push(whereItSits(next));
      } catch (couldNotPress) {
        /* One that cannot be pressed is left; the next round looks for another. */
      }
    }
    return closed;
  }

  /* **ONE ATTEMPT TO SIGN IN -- HIS RULING, 2026-09-16, RUMEE'S STEPS** (`D:\rumee-auto-sync\
   * content\meesho.js:115-145, 395-452`). *"Once you hit the login wall, you will try once by
   * clicking on the login. If it does work, it's fine. If it doesn't, then prompt the seller."*
   * It never types anything: it presses Login, clicks the box so a password Chrome has saved
   * can fill it, and presses Continue -- twice at most. Answers whether it is signed in now. */
  async function trySigningIn() {
    const kind = (node) => String((node && node.tagName) || '').toUpperCase();
    /* **THE PASSWORD BOX FIRST, THEN ANY BOX -- HIS RULING, 2026-09-16.** *"Try to
     * click on the password box; if a password is saved it will pop up, and then
     * click the login button."* Chrome offers a saved password when the seller
     * puts the caret in the box it belongs to, and the box it belongs to is the
     * password one. Clicking the email box first offers the address and leaves
     * the password empty, which is a Log in press that can only fail. */
    const everyBox = () => everything(thePage()).filter((node) => isPainted(node)
      && kind(node) === 'INPUT' && /^(tel|text|email|password|)$/i.test(String(node.type || '')));
    const aBox = () => everyBox().find((node) => String(node.type || '').toLowerCase() === 'password')
      || everyBox()[0];
    const aControl = (pattern) => everything(thePage()).find((node) => isPainted(node)
      && ['A', 'BUTTON'].includes(kind(node)) && pattern.test(words(node.textContent || '')));
    if (!aBox()) {
      const login = aControl(/^(login|log in|sign in)$/i);
      if (login && kind(login) === 'A' && login.href && globalThis.location) {
        /* Rumee's own note: the link opens a new tab, so the page is sent there itself. */
        globalThis.location.href = login.href;
        await rest(6000);
      } else if (login) {
        pressIt(login, 'the login link');
        await rest(6000);
      }
    }
    /* **THREE SCREENS, BECAUSE FLIPKART HAS THREE (his ruling, 2026-09-16):
     * the address, then the password, then a code only the seller has.** */
    for (let step = 0; step < 3; step += 1) {
      /* **IT STOPS AT THE CODE AND DOES NOT PRESS.** Nothing here can know a code
       * sent to his phone, and pressing Verify on an empty box spends one of the
       * platform's own tries. The seller is asked instead, and presses Resume. */
      if (aCodeIsBeingAskedFor(thePage())) return false;
      const box = aBox();
      if (!box) break;
      /* Focused AND clicked: Chrome shows the saved-password list on the click,
       * not on the focus, and gives it a moment to appear and fill. */
      if (typeof box.focus === 'function') box.focus();
      if (typeof box.click === 'function') box.click();
      await rest(2000);
      const submit = aControl(/^(continue|next|log in|login|verify|sign in)$/i)
        || everything(thePage()).find((node) => isPainted(node)
          && String(node.type || '').toLowerCase() === 'submit');
      if (!submit) break;
      pressIt(submit, 'the sign-in button');
      await rest(6000);
      if (!needsSigningIn()) return true;
    }
    return !needsSigningIn();
  }

  return {
    go,
    find,
    where_they_sit: whereTheySit,
    banners_seen: () => bannersHere.seen(),
    close_pop_ups: closePopUps,
    try_signing_in: trySigningIn,
    read_number: readNumber,
    click,
    type_in: typeIn,
    pick_range: pickRange,
    take_file: takeFile,
    overlays,
    page_text: pageText,
    needs_signing_in: needsSigningIn,
    wait: waitFor,
    click_away: clickAway,
  };
}

/** Switched off, either the way a form control says it or the way a portal's
 *  own `div` pretending to be a button says it. */
/** The first leaf under this that is a plain number, or nothing at all.
 *
 *  **LEAVES ONLY, AND IN THE ORDER THE PAGE IS WRITTEN.** A wrapper holds the
 *  words of everything inside it, so the card itself reads
 *  `Views(10 Sep)34,87714.15%` -- which is not a number and must not be tested as
 *  one. The smallest things carrying words are the only honest candidates, and
 *  the first of them in page order is the one beside the label.
 *
 *  **AND PAINTED, like everything else here.** A portal keeps figures in the page
 *  with no size at all, ready to show. */
function theFirstPlainNumberIn(node) {
  for (const one of everything(node)) {
    if ((one.children || []).length) continue;
    if (!isPainted(one)) continue;
    const said = words(one.textContent || '');
    if (!A_PLAIN_NUMBER.test(said)) continue;
    return Number(said.replace(/,/g, ''));
  }
  return null;
}

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
  const style = globalThis.getComputedStyle(node);
  const laidOver = String(style.position || '').toLowerCase();
  if (laidOver !== 'fixed' && laidOver !== 'absolute') return false;
  /* **A BACKDROP NOBODY CAN SEE, OR THAT LETS CLICKS THROUGH, COVERS NOTHING.**
   * Measured on his Flipkart Seller Insights, 2026-09-21: a drawer's backdrop kept
   * ready at full window with `visibility: hidden` and `opacity: 0` made every
   * miss on that page read "something is covering the page". */
  if (String(style.visibility || '').toLowerCase() === 'hidden') return false;
  if (String(style.opacity ?? '') === '0') return false;
  if (String(style.pointerEvents || '').toLowerCase() === 'none') return false;
  const box = node.getBoundingClientRect();
  const wide = Number(globalThis.window.innerWidth) || 0;
  const tall = Number(globalThis.window.innerHeight) || 0;
  if (!wide || !tall) return false;
  if (box.width < wide * MOST_OF_THE_PAGE || box.height < tall * MOST_OF_THE_PAGE) return false;
  /* **SIZE IS NOT COVERAGE -- A BOX MUST BE ON THE PAGE (EX1, 2026-10-03).** A
   * picker kept mounted and moved away (`transform: translate(-9999px, 0)`, or a
   * large negative `left`) still reports a full-size box, yet no click can land
   * on it. The box is asked WHERE it sits as well as how big it is: one that does
   * not overlap the window at all blocks nothing. **Only that.** A box partly on
   * the window still blocks what it covers, so nothing that blocked before stops
   * blocking. Coordinates are the window's own (`getBoundingClientRect`), so a
   * page scrolled past it or a container scrolled past it read the same way --
   * off the window. A box that gives no position at all is judged by size, as it
   * always was. */
  const left = Number(box.left);
  const top = Number(box.top);
  if (!Number.isFinite(left) || !Number.isFinite(top)) return true;
  const right = Number.isFinite(Number(box.right)) ? Number(box.right) : left + box.width;
  const bottom = Number.isFinite(Number(box.bottom)) ? Number(box.bottom) : top + box.height;
  return right > 0 && left < wide && bottom > 0 && top < tall;
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
/** The box a lookup found, or the one box inside what it found. */
function aBoxAtOrIn(node) {
  const isABox = (one) => ['input', 'textarea'].includes(String(one.tagName || '').toLowerCase());
  if (isABox(node)) return node;
  const boxes = [];
  const walkDown = (one) => {
    for (const child of one.children || []) {
      if (isABox(child)) boxes.push(child);
      walkDown(child);
    }
  };
  walkDown(node);
  return boxes.length === 1 ? boxes[0] : null;
}

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
