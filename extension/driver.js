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
 *     find(how, what, exact, patience, near) -> HOW MANY things match
 *                                    `near` is a LIST of ways the wanted row
 *                                    could be named; any one of them will do
 *     click(how, what, exact, near)  -> nothing, or throws
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
const WAYS_OF_FINDING = Object.freeze([BY_TEXT, BY_ROLE_AND_TEXT, BY_TEST_ID, BY_PRESSABLE_TEXT,
  BY_THE_CONTROL_BESIDE]);

/* **HOW FAR UP FROM THE LABEL TO LOOK FOR THE BOX IT LABELS.** Five, which is
 * the reference's own number. Not unlimited: walked far enough, every label's
 * ancestor is the page, and the page contains every input on it. */
const AS_FAR_UP_AS = 5;

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
function whatMatches(how, what, exact, near = []) {
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
  const all = how === BY_THE_CONTROL_BESIDE ? theBoxesBeside(smallest) : smallest;
  const innermost = how === BY_THE_CONTROL_BESIDE
    ? all.filter((node) => !all.some((other) => other !== node && node.contains(other)))
    : all;
  const rows = theRows(near);
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
    while (up) {
      /* **THE MOMENT IT TAKES IN ANOTHER MATCH, IT IS NO LONGER A ROW.** Walked
       * up without this, every match eventually reaches the whole page -- which
       * of course contains the words being looked for, so every row "matched"
       * and nothing was narrowed at all. That was the first version of this and
       * it read as working. */
      if (innermost.some((other) => other !== node && up.contains(other))) return false;
      const said = words(up.textContent).toLowerCase();
      if (rows.some((row) => said.includes(row))) return true;
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
      const box = inside.find(isABoxSomethingIsTypedIn) || inside.find(looksLikeACalendar);
      if (box && !found.includes(box)) { found.push(box); break; }
      up = up.parentNode;
    }
  }
  return found;
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

/* A HEADING SAYING WHICH MONTH IS ON SHOW: "June 2026", "Jun 2026". */
const A_MONTH_HEADING = /^([A-Za-z]{3,9})\s+(\d{4})$/;

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
  async function find(how, what, exact = true, patienceSeconds = 0, near = []) {
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
  function click(how, what, exact = true, near = []) {
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
      if (boxes.length === 0 && everyMonthOnShow().length > 0) {
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
          + `${boxes.length} date boxes were found and no calendar was showing, so no dates `
          + 'were set.'
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
    const cells = named.length > 0 ? named : everyCellShowingTheDay(day);

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
      throw new Error(
        `${iso} is on the calendar but the portal has it switched off, which is what it does `
        + 'with a day whose report it has not built yet. No dates were set.'
      );
    }
    cells[0].click();
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
      arrows[0].click();
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

  return {
    go,
    find,
    click,
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
