/* Checks for the ten things the Python side asks of a page.
 *
 * Run: node extension/driver.test.js
 *
 * **THIS IS THE FILE THAT DID NOT EXIST BEFORE.** The reference drove both
 * portals from about 3,800 lines of JavaScript with no checks at all, because
 * none of it could run without a real login and a real portal. Every failure it
 * had for three months was a button that had moved, found days later by a
 * seller noticing missing data. The whole reason the driver holds no knowledge
 * is so that what it DOES hold -- counting, refusing, waiting, reporting -- can
 * be read by a checks file on an ordinary machine with no account.
 *
 * The things only this can prove:
 *
 *   - **A BUTTON WITH A SPAN INSIDE IT IS ONE THING, NOT TWO.** Without that
 *     rule every ordinary lookup would refuse as ambiguous and nothing would
 *     ever be clicked;
 *   - **TWO THINGS READING THE SAME WORDS ANSWER TWO.** That is the nine-day
 *     payments outage, and it is the single reason `find` answers a count;
 *   - **A PAGE PART-WAY THROUGH DRAWING IS NOT A PAGE THAT IS SIGNED OUT.**
 *     Across 71 real occurrences in the reference's log, 54 were the first and
 *     harmless;
 *   - **A SWITCHED-OFF BUTTON IS SAID, NOT SILENTLY CLICKED AT.**
 */

import { FakeNode, installFakeBrowser } from '../test/fake-browser.js';
import {
  BY_A_REAL_BUTTON,
  BY_PRESSABLE_TEXT, BY_ROLE_AND_TEXT, BY_TEST_ID, BY_TEXT, BY_THE_CONTROL_BESIDE,
  BY_THE_BUTTON_BESIDE,
  CAUGHT_A_FILE, THE_CALLS, ASKED_ONLY_BY_THE_WALK,
  pageDoor, theCatcherSaid, theExtensionIsGone, aFileReallyComesFrom,
  DECLINED_A_LINK, looksLikeASpreadsheet, onThePlatformsOwnSite, whatThePageTriedToOpen,
  aBannerRecorder, whatABannerSays,
} from './driver.js';

process.on('uncaughtException', (err) => {
  console.log(`FAIL  the checks stopped part way through: ${(err && err.message) || String(err)}`);
  process.exit(1);
});
process.on('unhandledRejection', (err) => {
  console.log(`FAIL  something was waited on and never came back: ${(err && err.message) || String(err)}`);
  process.exit(1);
});

let failures = 0;
let ran = 0;

/* IF THIS FILE STOPS BEFORE ITS TALLY, THE RUN MUST NOT READ AS A CLEAN PASS.
 * Everything below waits on something, so stopping half way is the likely
 * shape of a failure here rather than an unlikely one. */
let reachedTheEnd = false;
process.on('exit', (code) => {
  if (reachedTheEnd || code !== 0) return;
  console.log('FAIL  the checks stopped before the end -- something they waited on never came back');
  process.exitCode = 1;
});

function check(name, passed) {
  ran++;
  console.log(`${passed ? 'PASS' : 'FAIL'}  ${name}`);
  if (!passed) failures++;
}

/** What a call refused with, or empty text if it did not refuse. */
function said(fn) {
  try {
    fn();
  } catch (wrong) {
    return (wrong && wrong.message) || String(wrong);
  }
  return '';
}

/** The same, for a call that waits before it refuses. */
async function saidAfterWaiting(fn) {
  try {
    await fn();
  } catch (wrong) {
    return (wrong && wrong.message) || String(wrong);
  }
  return '';
}

/* ---------------------------------------------------------- building a page */

/** One thing on a page. `box` is where the browser painted it -- a real one
 *  gives a menu that is not showing no size at all, and that is what tells it
 *  apart from one that is. */
function thing(tag, text, { box, ...properties } = {}) {
  const made = new FakeNode(tag);
  if (text) made.textContent = text;
  for (const [name, value] of Object.entries(properties)) {
    if (name === 'attrs') for (const [a, v] of Object.entries(value)) made.setAttribute(a, v);
    else made[name] = value;
  }
  if (box) made.setRect(box);
  return made;
}

const NOT_PAINTED = { top: 0, bottom: 0, left: 0, right: 0, width: 0, height: 0 };
const BIG = { top: 0, bottom: 400, left: 0, right: 600, width: 600, height: 400 };

/* **HIS OWN EVIDENCE.** Signed out, Flipkart serves its public marketing site,
 * whose menu reads these four words. A signed-in page mid-draw shows the
 * seller's own top bar and none of them. */
const PUBLIC_MENU = ['Sell Online', 'Fees and Commission', 'Grow', 'Shopsy'];

function aPage() {
  return installFakeBrowser({ width: 1280, height: 800 });
}

function doorOn({ go = async () => {}, takeFile = async () => null } = {}) {
  return pageDoor({ go, takeFile, signedOutSigns: PUBLIC_MENU });
}

/** Every date box on a page, for reading back what was put into them. */
function everyDateBox(page) {
  const found = [];
  const walk = (node) => {
    if (node.tagName === 'input' && node.type === 'date') found.push(node);
    for (const child of node.children) walk(child);
  };
  walk(page.body);
  return found;
}

/* ------------------------------------------------------- the contract itself */

{
  const page = aPage();
  const door = doorOn();
  /* **THESE TWO SAID EIGHT UNTIL `wait` WAS ADDED AND NINE UNTIL `click_away`
   * WAS, and they are rewritten with each change rather than deleted for going
   * red.** The ninth asks the page nothing -- Meesho builds an orders export on
   * its own servers and the page shows nothing at all while it happens. The
   * tenth NAMES nothing: shutting a menu is a click where nothing is, and it is
   * its own instruction because pressing the opener a second time is a guess
   * that it toggles. */
  /* **AND THE ONE QUESTION ONLY THE WALK ASKS, NAMED SEPARATELY (2026-09-14).**
   * `where_they_sit` is not a call the Python side makes, so it is not in the
   * eleven -- and a door growing a twelfth thing nobody named still goes red. */
  /* **AND TWO MORE ONLY THE WALK ASKS, HIS RULING OF 2026-09-14:** the banners the
   * page showed, and shutting pop-ups before a page's first step. Named, and
   * still kept out of the Python eleven. */
  check('the door answers exactly the eleven Python calls and the three the walk asks',
    JSON.stringify(Object.keys(door).sort())
      === JSON.stringify([...THE_CALLS, ...ASKED_ONLY_BY_THE_WALK].sort()));
  check('and no walk-only question is dressed up as a Python call',
    ASKED_ONLY_BY_THE_WALK.length === 5
      && ASKED_ONLY_BY_THE_WALK.every((one) => !THE_CALLS.includes(one))
      && ['where_they_sit', 'banners_seen', 'close_pop_ups', 'type_in', 'try_signing_in']
        .every((one) => ASKED_ONLY_BY_THE_WALK.includes(one)));
  check('and there are eleven of them', THE_CALLS.length === 11);
  /* **THE ELEVENTH IS THE ONLY ONE THAT BRINGS A VALUE BACK.** Everything else
   * presses, waits or counts. Meesho sells no export of the day's views. */
  check('and the eleventh is the one that reads a number off a page',
    THE_CALLS.includes('read_number'));
  check('the names are spelt the way the Python side spells them',
    THE_CALLS.includes('pick_range') && THE_CALLS.includes('needs_signing_in')
    && THE_CALLS.includes('take_file') && THE_CALLS.includes('page_text')
    && THE_CALLS.includes('wait') && THE_CALLS.includes('click_away'));
  check('a page is there to be read', page.body.tagName === 'body');
}

{
  /* **THE ONE CALL THAT ASKS THE PAGE NOTHING, AND IT REALLY HAS TO PASS TIME.**
   * A `wait` that returned at once would leave the recipe reading as though it
   * had waited thirty-five seconds for Meesho to build a file while reloading
   * the page instantly -- which is the fault it exists to fix, wearing the fix's
   * own name. Driven with a fiftieth of a second rather than read.
   *
   * **SECONDS, NOT MILLISECONDS.** Every other patience on a step is in seconds,
   * and a `wait` that took milliseconds would make `patience=35` a thirty-fifth
   * of a second -- indistinguishable from no wait at all, and green everywhere. */
  const door = doorOn();
  const started = Date.now();
  await door.wait(0.05);
  const took = Date.now() - started;
  check('waiting passes real time', took >= 45);
  check('and it is counted in seconds, not in milliseconds', took < 5000);
  /* Nothing, and a number that is not one, are nought rather than for ever. A
   * step whose wait never returned would hang the walk with nothing to say. */
  const alsoStarted = Date.now();
  await door.wait(undefined);
  await door.wait(-3);
  check('and nothing to wait for is no wait at all, never a walk that hangs',
    Date.now() - alsoStarted < 1000);
}

{
  /* **THE ONE CALL THAT NAMES NOTHING, AND IT REALLY HAS TO CLICK.**
   *
   * **THIS IS THE REFERENCE'S OWN GESTURE** (`content/meesho.js:865`,
   * `document.body.click()`): a portal menu is shut by clicking OUTSIDE it,
   * which is what every one of them listens for. It is here as its own call, and
   * not as a second press of whatever opened the menu, because a second press is
   * a guess that the control toggles -- and a wrong guess is silent. Both
   * presses do nothing, the list is never redrawn, and six rounds of it look
   * exactly like a night that works.
   *
   * **AND IT MUST NOT PRESS ANYTHING ON THE PAGE.** A click that landed on a
   * control would be a button pressed that no recipe ever asked for. */
  const page = aPage();
  const door = doorOn();
  let bodyHeard = 0;
  let buttonHeard = 0;
  const button = thing('button', 'Export data', { box: BIG });
  button.addEventListener('click', () => { buttonHeard += 1; });
  page.body.append(button);
  page.body.addEventListener('click', () => { bodyHeard += 1; });

  door.click_away();
  check('clicking away really clicks, and it clicks the page itself', bodyHeard === 1);
  check('and it presses nothing that is on the page', buttonHeard === 0);
}

{
  /* THE TWO HANDED IN ARE PASSED STRAIGHT THROUGH, not wrapped. Anything this
   * added around them would be a second place for a rule to live. */
  const went = [];
  const door = doorOn({ go: async (where) => { went.push(where); }, takeFile: async () => 'bytes' });
  check('going somewhere is the one it was handed', typeof door.go === 'function');
  await door.go('https://example.test/panel');
  check('and it is called with the address it was given', went[0] === 'https://example.test/panel');
  check('taking the file is the one it was handed', (await door.take_file()) === 'bytes');
}

{
  check('a door with no way of going anywhere is refused',
    said(() => pageDoor({ takeFile: async () => null, signedOutSigns: PUBLIC_MENU }))
      .includes('going to an address'));
  check('a door with no way of taking a file is refused',
    said(() => pageDoor({ go: async () => {}, signedOutSigns: PUBLIC_MENU }))
      .includes('taking the file'));
  /* A door that cannot tell it has been signed out would report every report as
   * a broken button, which is how the reference's queue died on the spot. */
  check('a door with no signed-out words at all is refused',
    said(() => pageDoor({ go: async () => {}, takeFile: async () => null }))
      .includes('could never tell that somebody has been signed out'));
  check('and so is one with only a single word to go on',
    said(() => pageDoor({ go: async () => {}, takeFile: async () => null, signedOutSigns: ['Grow'] }))
      .includes('could never tell that somebody has been signed out'));
  check('two is enough to build one',
    said(() => pageDoor({ go: async () => {}, takeFile: async () => null, signedOutSigns: ['Grow', 'Shopsy'] })) === '');
}

{
  /* A content script starts running before the page it was put into has a body.
   * Asked then, everything here would report an empty page -- which reads
   * exactly like a portal that has renamed every button. */
  aPage();
  const door = doorOn();
  const wasThere = globalThis.document;
  globalThis.document = undefined;
  check('with no page there at all it refuses rather than reporting an empty one',
    said(() => door.page_text()).includes('no page here to read'));
  globalThis.document = { body: null };
  check('and a page with nothing in it yet is refused the same way',
    said(() => door.page_text()).includes('no page here to read'));
  globalThis.document = wasThere;
  check('and once the page is back it reads it', door.page_text() === '');
}

/* ------------------------------------------------------------ counting things */

{
  const page = aPage();
  const door = doorOn();
  /* A BUTTON WITH A SPAN INSIDE IT. This is what nearly every real portal
   * button is, and counted plainly it matches at the span, at the button and at
   * everything wrapping them. */
  const button = thing('button');
  button.append(thing('span', 'Download Orders Data'));
  page.body.append(button);

  check('a button with words inside a span is one thing, not several',
    (await door.find(BY_TEXT, 'Download Orders Data')) === 1);
  check('and asked for a control, it is still one thing',
    (await door.find(BY_ROLE_AND_TEXT, 'Download Orders Data')) === 1);
  check('something that is not there at all answers none',
    (await door.find(BY_TEXT, 'Download Returns Data')) === 0);
}

{
  const page = aPage();
  const door = doorOn();
  /* **THE NINE-DAY OUTAGE, BUILT AS IT REALLY WAS.** A chart legend reading
   * "Payments to Date", earlier in the page than the menu item of the same
   * name. The reference took the first match. */
  page.body.append(thing('span', 'Payments to Date'));
  page.body.append(thing('button', 'Payments to Date'));

  check('two things reading the same words answer two, not one',
    (await door.find(BY_TEXT, 'Payments to Date')) === 2);
  check('and nothing is clicked when it is two',
    said(() => door.click(BY_TEXT, 'Payments to Date')).includes('2 things'));
  check('the refusal says which words could not be settled',
    said(() => door.click(BY_TEXT, 'Payments to Date')).includes('Payments to Date'));
  check('and that nothing was clicked, so nobody goes looking for what it did',
    said(() => door.click(BY_TEXT, 'Payments to Date')).includes('Nothing was clicked'));
  /* ASKED FOR A CONTROL, the legend is not one -- which is the fix as well as
   * the trap. */
  check('asked for a control, a chart legend is not one of them',
    (await door.find(BY_ROLE_AND_TEXT, 'Payments to Date')) === 1);
}

{
  const page = aPage();
  const door = doorOn();
  const showing = thing('button', 'Export');
  const waitingToBeShown = thing('button', 'Export', { box: NOT_PAINTED });
  page.body.append(showing, waitingToBeShown);
  check('a menu the browser has not painted is not counted',
    (await door.find(BY_TEXT, 'Export')) === 1);

  const hidden = thing('button', 'Export', { hidden: true });
  page.body.append(hidden);
  check('nor one the page says is hidden', (await door.find(BY_TEXT, 'Export')) === 1);

  /* Wide and no height at all is a collapsed menu, not a button on the page. */
  page.body.append(thing('button', 'Export', {
    box: { top: 0, bottom: 0, left: 0, right: 300, width: 300, height: 0 },
  }));
  check('nor one with width but no height', (await door.find(BY_TEXT, 'Export')) === 1);
}

{
  const page = aPage();
  const door = doorOn();
  page.body.append(thing('button', 'Download Listings Report'));
  check('an exact match does not answer to a longer name',
    (await door.find(BY_TEXT, 'Download')) === 0);
  check('a loose match does', (await door.find(BY_TEXT, 'Download', false)) === 1);
  check('capitals do not decide it',
    (await door.find(BY_TEXT, 'download listings report')) === 1);
  check('and the words are read with the spacing squeezed out',
    (await door.find(BY_TEXT, '  Download   Listings Report ')) === 1);
}

{
  const page = aPage();
  const door = doorOn();
  /* Words laid out across several lines, the way a portal writes them. */
  const button = thing('button');
  button.append(thing('span', 'Request New\n   Report'));
  page.body.append(button);
  check('a button whose words run over two lines still matches the phrase',
    (await door.find(BY_ROLE_AND_TEXT, 'Request New Report')) === 1);
}

{
  const page = aPage();
  const door = doorOn();
  page.body.append(thing('div', 'Submit', { attrs: { role: 'button' } }));
  check('something that says it is a button counts as a control',
    (await door.find(BY_ROLE_AND_TEXT, 'Submit')) === 1);
  page.body.replaceChildren(thing('div', 'Submit'));
  check('and a plain box of words does not',
    (await door.find(BY_ROLE_AND_TEXT, 'Submit')) === 0);
  page.body.replaceChildren(thing('input', '', { type: 'submit', value: 'Submit' }));
  check('a button drawn as an input is found by the words on it',
    (await door.find(BY_ROLE_AND_TEXT, 'Submit')) === 1);
  page.body.replaceChildren(thing('input', '', { type: 'button', value: 'Submit' }));
  check('and so is one of the other kind of input button',
    (await door.find(BY_ROLE_AND_TEXT, 'Submit')) === 1);
  /* A box somebody types into is not something to press, however it is
   * labelled. */
  page.body.replaceChildren(thing('input', '', { type: 'text', value: 'Submit' }));
  check('but a box somebody types into is not a control',
    (await door.find(BY_ROLE_AND_TEXT, 'Submit')) === 0);
}

{
  /* **AND NOT SOMETHING PRESSABLE EITHER, HOWEVER ITS CURSOR IS STYLED -- HIS
   * OWN ADS FSN REPORT, 2026-09-14.** It refused three times on "2 things match
   * Consolidated FSN Report", and the refusal named them: the Report Type list's
   * own SEARCH BOX, pointer cursor, holding the report's name as its value; and
   * the real option, a `div` in the popover. */
  const page = aPage();
  const door = doorOn();
  const pressed = [];
  const search = thing('input', '', { type: 'text', value: 'Consolidated FSN Report' });
  search.style.cursor = 'pointer';
  search.click = () => pressed.push('the search box');
  const popover = thing('div', '', { attrs: { id: 'popover-content' } });
  const option = thing('div', 'Consolidated FSN Report');
  option.style.cursor = 'pointer';
  option.click = () => pressed.push('the option');
  popover.append(option);
  page.body.append(search, popover);
  check('a search box holding the words is not a pressable match for them',
    (await door.find(BY_PRESSABLE_TEXT, 'Consolidated FSN Report')) === 1);
  door.click(BY_PRESSABLE_TEXT, 'Consolidated FSN Report');
  check('and it is the option that is pressed, never the search box',
    pressed.length === 1 && pressed[0] === 'the option');
  /* **A BUTTON DRAWN AS AN INPUT STILL COUNTS**, which is the case reading an
   * input's value exists for. */
  page.body.replaceChildren(thing('input', '', { type: 'submit', value: 'Export data' }));
  check('while a button drawn as an input is still pressable by its words',
    (await door.find(BY_PRESSABLE_TEXT, 'Export data')) === 1);
}

{
  /* **MEESHO'S SUPPLIER PANEL, AS IT REALLY IS.** Read off his own on
   * 2026-08-27, signed in and fully drawn: no button, no link, and not one role
   * attribute on the whole page. The sidebar's "Orders" is an `h5` and "Manage
   * Orders" is a `p`, and the ONLY thing marking either as pressable is that the
   * cursor changes over it. */
  const page = aPage();
  const door = doorOn();
  const heading = thing('h5', 'Orders');
  heading.style.cursor = 'pointer';
  page.body.append(heading, thing('p', 'Orders placed this week'));

  check('a heading the page shows as pressable is found by its words',
    (await door.find(BY_PRESSABLE_TEXT, 'Orders')) === 1);
  /* **AND IT IS NOT A CONTROL, which is the whole reason this way exists.** */
  check('while asking for a control finds nothing on such a page',
    (await door.find(BY_ROLE_AND_TEXT, 'Orders')) === 0);

  /* Words that are merely written on the page are not pressable. */
  const plain = thing('p', 'Returns');
  page.body.append(plain);
  check('words nobody can press are not found this way',
    (await door.find(BY_PRESSABLE_TEXT, 'Returns')) === 0);
  plain.style.cursor = 'pointer';
  check('and the same words become findable once the page says they can be pressed',
    (await door.find(BY_PRESSABLE_TEXT, 'Returns')) === 1);
}

{
  /* **THE NINE-DAY OUTAGE, ON A PAGE WITH NO CONTROLS AT ALL.** The payments
   * page carries a chart legend reading "Payments to Date" exactly like the menu
   * item. Matching on words alone finds two and refuses -- safe, and useless,
   * because payments would then never fetch again. Asked for as something
   * pressable, the legend is not one. */
  const page = aPage();
  const door = doorOn();
  const legend = thing('p', 'Payments to Date');
  const menuItem = thing('p', 'Payments to Date');
  menuItem.style.cursor = 'pointer';
  page.body.append(legend, menuItem);

  check('words alone still find both and refuse',
    (await door.find(BY_TEXT, 'Payments to Date')) === 2);
  check('while the pressable one is found on its own',
    (await door.find(BY_PRESSABLE_TEXT, 'Payments to Date')) === 1);

  const pressed = [];
  menuItem.addEventListener('click', () => pressed.push('menu'));
  legend.addEventListener('click', () => pressed.push('legend'));
  door.click(BY_PRESSABLE_TEXT, 'Payments to Date');
  check('and it is the menu item that is pressed, not the chart', pressed.length === 1 && pressed[0] === 'menu');

  /* **AND IF THE LEGEND WERE PRESSABLE TOO, IT STILL REFUSES.** The rule that
   * two matches is a failure is not weakened by this way of looking. */
  legend.style.cursor = 'pointer';
  check('two pressable things of one name is still a refusal',
    (await door.find(BY_PRESSABLE_TEXT, 'Payments to Date')) === 2);
  check('and nothing more was pressed',
    said(() => door.click(BY_PRESSABLE_TEXT, 'Payments to Date')).includes('2 things')
    && pressed.length === 1);
}

{
  /* **A PRESSABLE THING PASSES ITS CURSOR DOWN TO EVERYTHING INSIDE IT**, which
   * is how a real page behaves and is why the innermost rule matters more here
   * than anywhere. The stand-in does not inherit, so this is built the way a
   * real page arrives: both marked. */
  const page = aPage();
  const door = doorOn();
  const wrapper = thing('div');
  const inner = thing('span', 'Bulk Stock Update');
  wrapper.style.cursor = 'pointer';
  inner.style.cursor = 'pointer';
  wrapper.append(inner);
  page.body.append(wrapper);
  check('a pressable thing wrapping a pressable thing is still one thing',
    (await door.find(BY_PRESSABLE_TEXT, 'Bulk Stock Update')) === 1);
}

{
  /* **ASKING FOR A PRESSABLE THING CAN NEVER FIND LESS THAN ASKING FOR A
   * CONTROL, and that is deliberate.** A plain button in Chrome has the ordinary
   * arrow cursor unless somebody styled it -- so a rule that asked only about
   * the cursor would miss real buttons, and the same Meesho panel that has no
   * controls in its sidebar has twenty-three of them on its home page. */
  const page = aPage();
  const door = doorOn();
  const button = thing('button', 'Export data');
  page.body.append(button);
  check('an ordinary button with no cursor of its own is still pressable',
    button.style.cursor === '' && (await door.find(BY_PRESSABLE_TEXT, 'Export data')) === 1);
  check('and it is a control as well', (await door.find(BY_ROLE_AND_TEXT, 'Export data')) === 1);

  /* And the two together are still one thing, not two. */
  const also = thing('div', 'Submit', { attrs: { role: 'button' } });
  also.style.cursor = 'pointer';
  page.body.append(also);
  check('something that is both a control and pressable is counted once',
    (await door.find(BY_PRESSABLE_TEXT, 'Submit')) === 1);
}

/* ------------- the button on the row some words name (A57), and both halves
 * of why it needs to know what else that row says */

{
  /* **FLIPKART'S REPORTS CENTRE REQUEST DIALOG, READ OFF HIS OWN PANEL ON
   * 2026-09-11, ROW BY ROW.** Each row is a `span` naming a report and a real
   * `button` reading `REQUEST REPORT` beside it. **The name is a `span` with
   * `cursor: auto`** -- a row heading, pressing it does nothing -- and the five
   * buttons read identical words, so by its words alone a step finds five and
   * refuses. */
  const page = aPage();
  const door = doorOn();
  const pressed = [];
  const dialog = thing('div');
  for (const name of ['DBD Breached Shipments Report', 'Orders', 'Returns']) {
    const row = thing('div');
    const label = thing('span', name);
    const button = thing('button', 'REQUEST REPORT');
    button.click = () => pressed.push(name);
    row.append(label, button);
    dialog.append(row);
  }
  page.body.append(dialog);

  check('the report name is not pressable, so nothing can find it that way',
    (await door.find(BY_PRESSABLE_TEXT, 'Orders')) === 0);
  check('and its words alone find every row button, which is a refusal',
    (await door.find(BY_A_REAL_BUTTON, 'REQUEST REPORT')) === 3);
  check('THE BUTTON ON THE ROW THOSE WORDS NAME IS FOUND, and it is exactly one',
    (await door.find(BY_THE_BUTTON_BESIDE, 'Orders')) === 1);
  door.click(BY_THE_BUTTON_BESIDE, 'Orders');
  check('and it is that row button that is pressed, and not another',
    pressed.length === 1 && pressed[0] === 'Orders');
}

{
  /* **AND THE SAME WORD IS ON THE PAGE TWICE, WHICH IS WHY IT ALSO ASKS WHAT
   * ELSE THAT ROW SAYS.** Behind the dialog sits the list of reports already
   * requested, and `Orders` is a leaf there too -- in a row with its own
   * Download button. Both walk up to a button, so without narrowing the step
   * finds two and refuses. **The dialog's row says `REQUEST REPORT`; the
   * list's row does not.** */
  const page = aPage();
  const door = doorOn();
  const pressed = [];

  const dialogRow = thing('div');
  const dialogName = thing('span', 'Orders');
  const request = thing('button', 'REQUEST REPORT');
  request.click = () => pressed.push('the request button');
  dialogRow.append(dialogName, request);

  const listRow = thing('div');
  const listName = thing('span', 'Orders');
  const range = thing('span', 'Aug 31 2026 To Sep 01 2026');
  const download = thing('button', 'Download');
  download.click = () => pressed.push('the download button');
  listRow.append(listName, range, download);

  page.body.append(dialogRow, listRow);

  check('both rows walk up to a button, so the words alone find two and refuse',
    (await door.find(BY_THE_BUTTON_BESIDE, 'Orders')) === 2);
  check('narrowed by what else that row says, it is one again',
    (await door.find(BY_THE_BUTTON_BESIDE, 'Orders', true, 0, [], 'REQUEST REPORT')) === 1);
  door.click(BY_THE_BUTTON_BESIDE, 'Orders', true, [], false, 'REQUEST REPORT');
  check('and it is the request button, never the one in the list behind it',
    pressed.length === 1 && pressed[0] === 'the request button');
}

/* ------------------------ a label is a control, and it has no pointer (A57) */

{
  /* **HIS OWN FLIPKART REPORTS CENTRE, READ ELEMENT BY ELEMENT ON 2026-09-11.**
   * The `Requested`, `Scheduled` and `All` tabs are each a **`<label>` with
   * `cursor: default`** -- no role, no button, no pointer. **So before `label`
   * joined the control tags, NEITHER way of looking could find them**: not as a
   * control, and not as something pressable, because the cursor never changes.
   * A recipe asking for the Requested tab could only answer that it was not on
   * the page, on every night, for ever.
   *
   * **AND IT IS THE BROWSER'S OWN RULE, NOT FLIPKART'S**, which is the test
   * everything on that list has to pass: a click on a `<label>` is delivered by
   * the browser to the input it labels. These tabs each wrap a radio nobody
   * sees. */
  const page = aPage();
  const door = doorOn();
  const tab = thing('label', 'Requested');
  page.body.append(tab);
  check('a tab drawn as a label with no pointer cursor is a control',
    tab.style.cursor === '' && (await door.find(BY_ROLE_AND_TEXT, 'Requested')) === 1);
  check('and so it is pressable too, which is what a recipe asks for',
    (await door.find(BY_PRESSABLE_TEXT, 'Requested')) === 1);
  /* **AND IT IS NOT A REAL BUTTON**, so the strictest way still tells them
   * apart -- the way `me_payments` needs to find the one thing in the modal. */
  check('but it is not a real button, so the strictest way still says no',
    (await door.find(BY_A_REAL_BUTTON, 'Requested')) === 0);
}

{
  /* **THE REASON WIDENING THIS LIST DID NOT BREAK A WORKING REPORT.** A label
   * wrapping words that something inside it also carries would be a SECOND
   * match of one thing -- and two matches is a refusal, so a Meesho report that
   * works today could have started refusing. **Only the innermost element
   * carrying the words is counted**, so the span wins and the label around it is
   * not a second answer. */
  const page = aPage();
  const door = doorOn();
  const pressed = [];
  const wrapper = thing('label');
  const inner = thing('span', 'Export Data');
  inner.style.cursor = 'pointer';
  inner.click = () => pressed.push('the span');
  wrapper.click = () => pressed.push('the label');
  wrapper.append(inner);
  page.body.append(wrapper);
  check('a label wrapping the same words is not a second match of them',
    (await door.find(BY_PRESSABLE_TEXT, 'Export Data')) === 1);
  door.click(BY_PRESSABLE_TEXT, 'Export Data');
  check('and it is the innermost thing that is pressed, not the label around it',
    pressed.length === 1 && pressed[0] === 'the span');
}

{
  const page = aPage();
  const door = doorOn();
  /* **MEESHO'S PAYMENTS PAGE, READ OFF HIS OWN PANEL ON 2026-09-11 WITH THE
   * EXPORT MODAL OPEN.** Two things read the single word "Download": the opener
   * at the top right, a `div` wearing `role="button"`, and the real `<button>`
   * inside the modal. His own runs said "2 things match" twice -- once asking for
   * something pressable, once asking for a control -- because both of those match
   * both things. `role="button"` is exactly how a page declares a div to be a
   * control, so no test of control-ness can ever separate them. */
  const opener = thing('div', 'Download', { attrs: { role: 'button', tabindex: '0' } });
  opener.style.cursor = 'pointer';
  const inTheModal = thing('button', 'Download');
  page.body.append(opener, inTheModal);

  check('asking for a control finds both, which is the refusal his run reported',
    (await door.find(BY_ROLE_AND_TEXT, 'Download')) === 2);
  check('and asking for pressable words finds both as well',
    (await door.find(BY_PRESSABLE_TEXT, 'Download')) === 2);
  check('asking for a real button finds the one in the modal and nothing else',
    (await door.find(BY_A_REAL_BUTTON, 'Download')) === 1);
  /* **AND IT IS THE RIGHT ONE OF THE TWO, not merely one of them.** A count of
   * one proves the step would click; it does not prove what it would click. */
  const pressed = [];
  inTheModal.click = () => pressed.push('the modal');
  opener.click = () => pressed.push('the opener');
  door.click(BY_A_REAL_BUTTON, 'Download');
  check('and it is the modal it presses, not the opener',
    pressed.length === 1 && pressed[0] === 'the modal');

  /* **A DIV THAT SAYS IT IS A BUTTON IS STILL NOT ONE.** Alone on a page it is
   * found by every other way here and by this one never. */
  const page2 = aPage();
  const door2 = doorOn();
  page2.body.append(thing('div', 'Export', { attrs: { role: 'button' } }));
  check('a div wearing the role alone is a control but not a real button',
    (await door2.find(BY_ROLE_AND_TEXT, 'Export')) === 1
      && (await door2.find(BY_A_REAL_BUTTON, 'Export')) === 0);
}

{
  const page = aPage();
  const door = doorOn();
  page.body.append(thing('button', 'anything at all', { attrs: { 'data-testid': 'export-button' } }));
  check('a thing the page names itself is found by that name',
    (await door.find(BY_TEST_ID, 'export-button')) === 1);
  check('and the words on it are not what is being matched',
    (await door.find(BY_TEST_ID, 'anything at all')) === 0);
}

{
  const door = doorOn();
  /* NOT ANSWERED WITH NOUGHT. A way of finding something this does not
   * understand, answered "nothing found", looks exactly like the button having
   * been renamed -- and would be written into the log as the platform
   * changing. */
  let refused = '';
  try {
    await door.find('xpath', '//button');
  } catch (wrong) {
    refused = wrong.message;
  }
  check('a way of finding something nobody knows is refused, not answered none',
    refused.includes('not a way of finding something'));
  check('and the refusal says which ways it does know',
    refused.includes('text') && refused.includes('role') && refused.includes('test-id')
    && refused.includes('pressable'));
  check('clicking through an unknown way is refused too',
    said(() => door.click('xpath', '//button')).includes('not a way of finding something'));
}

/* ------------------------------------------------- which row it is on */

{
  /* **HIS OWN RETURNS PAGE, AS IT REALLY IS.** Meesho keeps every export ever
   * made, each row reading `completed_delivered_last_2_week | 25 Aug 2026,
   * 04:49 PM | Download`. Ten of them today. Looking for "Download" finds ten
   * and refuses -- right, and useless. The recipe knows which day it wants. */
  const page = aPage();
  const door = doorOn();
  const pressed = [];
  const madeOn = ['25 Aug 2026, 04:49 PM', '24 Aug 2026, 06:29 PM', '22 Aug 2026, 08:09 PM'];
  for (const when of madeOn) {
    const row = thing('div');
    row.append(thing('span', 'completed_delivered_last_2_week'), thing('span', when));
    const press = thing('div', 'Download');
    press.style.cursor = 'pointer';
    press.addEventListener('click', () => pressed.push(when));
    row.append(press);
    page.body.append(row);
  }

  check('every row carries the same words, so asking plainly finds them all',
    (await door.find(BY_PRESSABLE_TEXT, 'Download')) === 3);
  check('and nothing is pressed, because which one was meant cannot be known',
    said(() => door.click(BY_PRESSABLE_TEXT, 'Download')).includes('3 things'));

  check('naming the day finds exactly the one on that row',
    (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0, '24 Aug 2026')) === 1);
  door.click(BY_PRESSABLE_TEXT, 'Download', true, '24 Aug 2026');
  check('and it is that row that is pressed, not the newest',
    pressed.length === 1 && pressed[0] === '24 Aug 2026, 06:29 PM');

  /* **A DAY THAT IS NOT THERE FINDS NOTHING, rather than the nearest one.** A
   * file from the wrong day looks perfectly fine afterwards. */
  check('a day with no row of its own finds nothing at all',
    (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0, '23 Aug 2026')) === 0);
  check('and nothing more was pressed', pressed.length === 1);

  /* **IT ONLY EVER TAKES MATCHES AWAY.** Words that are on every row narrow
   * nothing, and the step still refuses rather than guessing. */
  check('words that are on every row narrow nothing and still refuse',
    (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0,
                     ['completed_delivered_last_2_week'])) === 3);

  /* ---------- SEVERAL WAYS THE SAME ROW COULD BE NAMED (A53)
   *
   * **NEITHER PORTAL WRITES A DAY ONLY ONE WAY**, and the working reference does
   * not pretend they do: it builds five spellings on Flipkart and six on Meesho
   * and takes a row that carries ANY of them. Committing to one is what put a
   * spelling on Flipkart that the reference's own matcher excludes. */
  check('given several ways one day could be written, a row matching any of them counts',
    (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0,
                     ['Aug 24 2026', '24 Aug 2026', '2026-08-24'])) === 1);
  check('and the one that matched need not be the first tried',
    (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0,
                     ['nothing like it', 'still nothing', '22 Aug 2026'])) === 1);
  /* **THEY ALL NAME THE SAME DAY, so a longer list can never reach a different
   * row -- only a right row that would otherwise have been missed.** */
  check('while a list of spellings none of which is on the page still finds nothing',
    (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0,
                     ['Aug 23 2026', '23 Aug 2026', '2026-08-23'])) === 0);
  check('and an empty list narrows nothing at all, which is most lookups',
    (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0, [])) === 3);
  door.click(BY_PRESSABLE_TEXT, 'Download', true, ['Aug 22 2026', '22 Aug 2026']);
  check('and clicking with a list presses the row one of them named',
    pressed.length === 2 && pressed[1] === '22 Aug 2026, 08:09 PM');
}

/* ------------------- TWO RIGHT ROWS, WHICH IS NOT TWO WRONG ONES (2026-09-11)
 *
 * **HIS OWN MEESHO ORDERS PANEL, READ IN HIS SIGNED-IN CHROME THAT MORNING.**
 * Ten Download rows. `near` cut them to TWO, and both were genuinely the day
 * asked for -- `2026-09-10_2026-09-10_2026-09-11`, one made at 08:51 AM and one
 * at 08:30 AM, because he ran the export twice. The walk refused, and the day
 * went unfetched for a reason that was no fault at all. */
{
  const page = aPage();
  const door = doorOn();
  const pressed = [];
  /* The file name carries FROM, TO and the day the export was MADE. The two
   * that survive the day filter are the first two; the other eight are other
   * days, and are what makes this ten rows rather than two. */
  const rows = [
    ['2026-09-10_2026-09-10_2026-09-11', '11 Sep 2026, 08:51 AM'],
    ['2026-09-10_2026-09-10_2026-09-11', '11 Sep 2026, 08:30 AM'],
    ['2026-09-08_2026-09-08_2026-09-09', '9 Sep 2026, 09:02 AM'],
    ['2026-09-07_2026-09-07_2026-09-08', '8 Sep 2026, 08:44 AM'],
    ['2026-09-06_2026-09-06_2026-09-07', '7 Sep 2026, 08:40 AM'],
    ['2026-09-05_2026-09-05_2026-09-06', '6 Sep 2026, 08:55 AM'],
    ['2026-09-04_2026-09-04_2026-09-05', '5 Sep 2026, 08:31 AM'],
    ['2026-09-03_2026-09-03_2026-09-04', '4 Sep 2026, 08:38 AM'],
    ['2026-09-02_2026-09-02_2026-09-03', '3 Sep 2026, 08:47 AM'],
    ['2026-09-01_2026-09-01_2026-09-02', '2 Sep 2026, 08:52 AM'],
  ];
  for (const [called, when] of rows) {
    const row = thing('div');
    row.append(thing('p', called), thing('p', when));
    /* A `span` with a pointer cursor, which is what Meesho really draws. */
    const press = thing('span', 'Download');
    press.style.cursor = 'pointer';
    press.addEventListener('click', () => pressed.push(when));
    row.append(press);
    page.body.append(row);
  }
  /* **HOW MEESHO NAMES THE ROW: the day the export was MADE**, which is the
   * third date in the file name and the one `me_orders` narrows by. */
  const theDay = ['11 Sep 2026', '2026-09-11'];

  check('ten rows carry the word, which is what the panel really showed',
    (await door.find(BY_PRESSABLE_TEXT, 'Download')) === 10);
  check('and the day narrows the ten to the two he really made that morning',
    (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0, theDay)) === 2);
  /* **THE WHOLE RULE, IN ONE LINE.** Told it may take the newest of several that
   * a day already narrowed, it presses the topmost -- 08:51, not 08:30. */
  /* **`said` RATHER THAN A BARE CALL, so that the day this rule is taken out
   * again the check below goes red by its own name instead of stopping the whole
   * file on a throw nobody can place. */
  said(() => door.click(BY_PRESSABLE_TEXT, 'Download', true, theDay, true));
  check('TWO ROWS OF THE RIGHT DAY: THE NEWEST IS TAKEN, NOT REFUSED',
    pressed.length === 1 && pressed[0] === '11 Sep 2026, 08:51 AM');

  /* **AND THE PAYMENTS INCIDENT STAYS RED.** Nothing narrowed these ten: no
   * day, so nothing distinguishes a right row from a chart legend that reads
   * like a menu item. Permission to take the newest must not reach this. */
  check('SEVERAL WITH NOTHING NARROWING THEM STILL REFUSES, EVEN TOLD TO TAKE THE NEWEST',
    said(() => door.click(BY_PRESSABLE_TEXT, 'Download', true, [], true))
      .includes('10 things'));
  check('and nothing more was pressed', pressed.length === 1);
}

/* ------- THREE REPORTS, ONE END DATE, AND ONLY THE KIND BETWEEN THEM (2026-09-11)
 *
 * **FLIPKART'S REQUESTED LIST, AS THE REFERENCE DESCRIBES IT.** Orders, returns
 * and settled transactions are all asked for on the same night over the same
 * range, so on any ordinary morning all three rows end `To 06 Jun 2026`.
 * Narrowed by the day alone, one lookup matches three rows -- and the rule
 * directly above, which takes the newest of several a day already narrowed,
 * then presses whichever is topmost. **That is the payments file landing under
 * the orders name and being read into the seller's books as sales.**
 *
 * The reference asks the report's own kind FIRST and the date second, of the
 * same row (`content/flipkart.js` `findReportRowDownloadBtn` opens with
 * `if (!rowLow.includes(subLow)) continue;`). These checks are that test. */
{
  const page = aPage();
  const door = doorOn();
  const pressed = [];
  /* **THE ROW AS THE REFERENCE QUOTES IT:** kind, sub-kind, the range, the
   * state, then the control. The topmost is deliberately NOT the orders one --
   * taking the topmost is precisely the fault. */
  const rows = [
    ['Payment Reports', 'Settled Transactions'],
    ['Fulfilment Reports', 'Returns'],
    ['Fulfilment Reports', 'Orders'],
  ];
  for (const [kind, subKind] of rows) {
    const row = thing('div');
    row.append(thing('span', kind), thing('span', subKind),
      thing('span', '05 Jun 2026 To 06 Jun 2026'), thing('span', 'Generated'));
    const press = thing('span', 'Download');
    press.style.cursor = 'pointer';
    press.addEventListener('click', () => pressed.push(subKind));
    row.append(press);
    page.body.append(row);
  }
  const theDay = ['To 06 Jun 2026', 'To Jun 6 2026'];

  check('all three rows carry the same end date, which is what the night really shows',
    (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0, theDay)) === 3);
  /* **THE FAULT ITSELF, PINNED.** Told it may take the newest of several the day
   * narrowed, and with nothing else narrowing them, it presses the topmost --
   * and the topmost here is payments. */
  said(() => door.click(BY_PRESSABLE_TEXT, 'Download', true, theDay, true));
  check('and the day alone would have pressed the payments row under the orders name',
    pressed.length === 1 && pressed[0] === 'Settled Transactions');

  check('THE KIND OF REPORT THE ROW IS FOR CUTS THE THREE TO ONE',
    (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0, theDay, 'Orders')) === 1);
  door.click(BY_PRESSABLE_TEXT, 'Download', true, theDay, true, 'Orders');
  check('AND IT IS THE ORDERS ROW THAT IS PRESSED, NOT THE TOPMOST',
    pressed.length === 2 && pressed[1] === 'Orders');

  /* **THE OTHER TWO ARE REACHABLE BY THEIR OWN KIND**, which is what makes this
   * a narrowing rather than a rule that only ever finds orders. */
  check('and each of the other two is reached by its own kind',
    (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0, theDay,
                     'Settled Transactions')) === 1
    && (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0, theDay, 'Returns')) === 1);

  /* **IT NARROWS, IT NEVER LOOSENS.** A kind on no row takes the right row away
   * too, and nought found refuses -- which is the safe direction. */
  check('a kind that is on no row finds nothing at all, rather than the nearest',
    (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0, theDay, 'Tax Reports')) === 0);
  /* **AND BOTH TESTS ARE ASKED OF THE SAME ROW.** Asked of any row, the kind on
   * one row and the day on another would both be satisfied by the page. */
  check('and the kind is asked of the row the day named, not of the page',
    (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0,
                     ['To 07 Jun 2026'], 'Orders')) === 0);
  /* **AND WITH NOTHING NAMING THE DAY IT STILL REFUSES**, so this cannot become
   * a second way in for the incident the refusal exists for. */
  check('several with nothing narrowing them still refuses, kind or no kind',
    said(() => door.click(BY_PRESSABLE_TEXT, 'Download', true, [], true, 'Orders'))
      .includes('3 things'));
  check('and nothing more was pressed', pressed.length === 2);
}

/* ------ A ROW REACHES SIX LEVELS ABOVE ITS CONTROL AND NO FURTHER (2026-09-11)
 *
 * **HIS OWN MEESHO CLAIMS PANEL, MEASURED ANCESTOR BY ANCESTOR.** The panel's
 * own menu button carries the single word `Download`, exactly as every row in
 * the list below it does. Climbing from that button, **nine levels up**, the
 * page's heading block contains `11 Sep` -- so the button counted as today's
 * row. The real row matched **one level up**. Two matched, the button is first
 * in the page, and the rule that takes the newest of several took it: **the walk
 * pressed the menu shut and then waited five minutes for a file nobody had asked
 * for**, and reported it as the platform having changed. */
{
  const page = aPage();
  const door = doorOn();
  const pressed = [];
  /* **THE HEADING BLOCK, WHICH IS WHERE THE DAY REALLY IS.** Nine levels above
   * the menu button on the real page; three here, which is the same fault at a
   * size a checks file can hold. */
  const header = thing('div');
  header.append(thing('span', 'Claim Tracking All (146) Open (3) Filter by: Created Date 11 Sep'));
  const menu = thing('span', 'Download');
  menu.style.cursor = 'pointer';
  menu.addEventListener('click', () => pressed.push('the menu button'));
  /* **EIGHT WRAPPERS BETWEEN THE BUTTON AND THE HEADING**, so the day really is
   * further above it than a row ever reaches. Nine on the real page. */
  let inside = menu;
  for (let deep = 0; deep < 8; deep += 1) {
    const wrapper = thing('div');
    wrapper.append(inside);
    inside = wrapper;
  }
  header.append(inside);
  page.body.append(header);

  /* The exported files, each row with its own Download, below the heading. */
  for (const [called, when] of [
    ['Supplier-1244938_Status-all_Created-from-13-06-2026-to-11-09-2026', '11 Sept 2026, 10:20 AM'],
    ['Supplier-1244938_Status-all_Created-from-12-06-2026-to-10-09-2026', '10 Sept 2026, 08:01 PM'],
  ]) {
    const row = thing('div');
    row.append(thing('p', called), thing('p', when));
    const press = thing('span', 'Download');
    press.style.cursor = 'pointer';
    press.addEventListener('click', () => pressed.push(when));
    row.append(press);
    page.body.append(row);
  }

  /* **THE SPELLING THAT DID IT IS THE ONE WITH NO YEAR.** `recipes.py` calls it
   * the loosest thing in that file and keeps it knowingly; it is safe inside a
   * row and was not safe nine levels above one. */
  const theDay = ['11 Sep 2026', '11 Sep', '11-09-2026'];

  check('three things on the page carry the word, the menu button and two rows',
    (await door.find(BY_PRESSABLE_TEXT, 'Download')) === 3);
  check('AND THE DAY NARROWS THEM TO THE ONE ROW, not to the menu button as well',
    (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0, theDay)) === 1);
  door.click(BY_PRESSABLE_TEXT, 'Download', true, theDay, true);
  check('SO IT IS THE ROW THAT IS PRESSED, NOT THE BUTTON THAT SHUTS THE MENU',
    pressed.length === 1 && pressed[0] === '11 Sept 2026, 10:20 AM');

  /* **AND YESTERDAY'S ROW IS STILL REACHABLE BY ITS OWN DAY**, so this is a
   * narrowing and not a rule that only ever finds the topmost. */
  check('and yesterday is still reached by its own day',
    (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0, ['10-09-2026'])) === 1);
  /* **AND A DAY ON NO ROW FINDS NOTHING, rather than the heading that mentions
   * it.** This is the whole check in one line. */
  check('while a day that is only in the heading finds nothing at all',
    (await door.find(BY_PRESSABLE_TEXT, 'Download', true, 0, ['146'])) === 0);
  check('and nothing more was pressed', pressed.length === 1);
}

/* ------------------------------- the box a label names, not the label (A53) */

{
  /* **FLIPKART'S REPORTS CENTRE, AS THE DOCUMENT RECORDS IT.** The words
   * "Select Date Range" are a plain leaf with the calendar hidden behind a box
   * beside them. A step that pressed the WORDS could never have worked twice
   * over: the words are not pressable, and the box does not carry them -- what
   * an input carries is its VALUE, which there is the range currently showing
   * (`DOCS.md:1803`). */
  const page = aPage();
  const door = doorOn();
  const pressed = [];
  const row = thing('div');
  const label = thing('span', 'Select Date Range');
  const box = thing('input', '', { type: 'text', value: '01 Jun 2026 - 06 Jun 2026' });
  box.addEventListener('click', () => pressed.push('the box'));
  label.addEventListener('click', () => pressed.push('the label'));
  row.append(label, box);
  page.body.append(row);

  check('the label is not something a person can press, so pressable finds nothing',
    (await door.find(BY_PRESSABLE_TEXT, 'Select Date Range')) === 0);
  /* **AND NOTHING READING WORDS REACHES THE BOX EITHER**, which is the other
   * half of why a fifth way of finding had to exist. */
  check('and the box does not carry those words at all -- it carries its own value',
    (await door.find(BY_TEXT, 'Select Date Range')) === 1
    && (await door.find(BY_TEXT, '01 Jun 2026 - 06 Jun 2026')) === 1);

  check('THE BOX A LABEL NAMES IS FOUND, and it is exactly one thing',
    (await door.find(BY_THE_CONTROL_BESIDE, 'Select Date Range')) === 1);
  door.click(BY_THE_CONTROL_BESIDE, 'Select Date Range');
  check('and it is the BOX that is pressed, never the words',
    pressed.length === 1 && pressed[0] === 'the box');

  /* **A CALENDAR ICON WHERE THERE IS NO INPUT**, which is the second of the
   * three things the reference reaches for. */
  const page2 = aPage();
  const door2 = doorOn();
  const iconRow = thing('div');
  const iconLabel = thing('span', 'Select Date Range');
  const icon = thing('svg', '', { attrs: { class: 'calendar-icon' } });
  iconRow.append(iconLabel, icon);
  page2.body.append(iconRow);
  check('where the portal draws an icon instead of an input, the icon is the box',
    (await door2.find(BY_THE_CONTROL_BESIDE, 'Select Date Range')) === 1);

  /* **AND A LABEL WITH NOTHING BESIDE IT FINDS NOTHING, rather than pressing
   * the container it sits in.** The reference falls back to clicking the whole
   * row; that is a guess, and a click landing somewhere nobody has measured is
   * worse than a refusal that says what it was looking for. */
  const page3 = aPage();
  const door3 = doorOn();
  page3.body.append(thing('div', 'Select Date Range'));
  check('and a label with no box beside it finds nothing, rather than guessing',
    (await door3.find(BY_THE_CONTROL_BESIDE, 'Select Date Range')) === 0);
}

{
  /* **TYPING INTO THE BOX A LABEL NAMES (2026-09-15)** -- Flipkart's campaign
   * search, whose Download stays off until a campaign is typed and chosen. */
  const page = aPage();
  const door = doorOn();
  const row = thing('div');
  const label = thing('span', 'Campaign ID');
  const box = thing('input', '', { type: 'text', value: '' });
  const heard = [];
  box.addEventListener('input', () => heard.push('input'));
  row.append(label, box);
  page.body.append(row);
  door.type_in(BY_THE_CONTROL_BESIDE, 'Campaign ID', true, [], '', '0PTESTCAMP001');
  check('WORDS ARE TYPED INTO THE BOX A LABEL NAMES', box.value === '0PTESTCAMP001');
  check('and the page is told, the way typing tells it', heard.length >= 1);
  const page2 = aPage();
  const door2 = doorOn();
  page2.body.append(thing('div', 'Campaign ID'));
  let refused = '';
  try {
    door2.type_in(BY_TEXT, 'Campaign ID', true, [], '', 'x');
  } catch (wrong) {
    refused = wrong.message;
  }
  check('and something that is not a box is never typed into, and says so',
    refused.includes('nothing there can be typed into'));
}

{
  /* **A LIST THAT PICKS ON BUTTON DOWN (2026-09-15)** -- Flipkart's campaign
   * suggestion, measured on his page: a bare click selected nothing. */
  const page = aPage();
  const door = doorOn();
  const suggestion = thing('div', 'ID 0PTESTCAMP001');
  let picked = 0;
  suggestion.addEventListener('mousedown', () => { picked += 1; });
  page.body.append(suggestion);
  door.click(BY_TEXT, '0PTESTCAMP001', false);
  check('A PLAIN PRESS NEVER REACHES A LIST THAT PICKS ON BUTTON DOWN', picked === 0);
  door.click(BY_TEXT, '0PTESTCAMP001', false, [], false, '', true);
  check('while a press like a mouse does, once', picked === 1);
}

/* --------------------------------------------------------------- waiting */

{
  const page = aPage();
  const door = doorOn();
  check('with no patience at all, something absent answers none at once',
    (await door.find(BY_TEXT, 'Generated', false, 0)) === 0);

  setTimeout(() => page.body.append(thing('span', 'Generated')), 60);
  check('given time, it waits for the page to draw the thing',
    (await door.find(BY_TEXT, 'Generated', false, 3)) === 1);
}

{
  const door = doorOn();
  aPage();
  const startedAt = Date.now();
  const many = await door.find(BY_TEXT, 'never appears', true, 0.3);
  check('and when the time runs out it answers none', many === 0);
  check('having actually waited rather than answered at once', Date.now() - startedAt >= 250);
}

{
  const page = aPage();
  const door = doorOn();
  /* **THE MID-DRAW SHAPE OF THE NINE-DAY OUTAGE.** The legend is drawn, and the
   * menu item of the same name arrives a moment later. Answering the instant
   * one thing matched would say "exactly one" -- and one is the answer that
   * clicks. */
  page.body.append(thing('span', 'Payments to Date'));
  setTimeout(() => page.body.append(thing('button', 'Payments to Date')), 40);
  check('a second match arriving a moment later is counted, not missed',
    (await door.find(BY_TEXT, 'Payments to Date', true, 2)) === 2);
}

{
  const page = aPage();
  const door = doorOn();
  /* **THE OTHER HALF OF THAT SETTLE, AND IT COST `me_payments` (2026-09-11).**
   * The count taken after the settle used to be handed straight back -- nought
   * included -- so a thing that was on the page and then was not ended the wait
   * in a quarter of a second. A step allowed forty-five seconds spent 250
   * milliseconds of them and reported "it is not on the page at all", which
   * reads as a portal that has changed rather than a page still drawing.
   *
   * **THE MENU DOES NOT GO AWAY HERE, IT STOPS SAYING THE WORD**, which is the
   * shape a portal redrawing itself actually has: the same place on the page,
   * different words in it for a moment. */
  const early = thing('span', 'Download');
  page.body.append(early);
  setTimeout(() => { early.textContent = 'Downloading 1 of 3'; }, 100);
  setTimeout(() => page.body.append(thing('button', 'Download')), 600);
  const startedAt = Date.now();
  const many = await door.find(BY_TEXT, 'Download', true, 3);
  check('a thing that stops matching before the settle is waited for, not called absent',
    many === 1);
  check('and the waiting really carried on past the settle',
    Date.now() - startedAt >= 600);
}

/* ------------------------------------------- reading a number off a page */

/* **MEASURED ON HIS OWN MEESHO DASHBOARD, 2026-09-11.** The card is built exactly
 * like this: the label, the card's own day in brackets, the figure with a comma
 * in it, and how much it moved as a percentage. */
function aCard(label, day, figure, moved) {
  const card = thing('div');
  const head = thing('div');
  head.append(thing('p', label), thing('span', day));
  card.append(head, thing('p', figure), thing('span', moved));
  return card;
}

{
  const page = aPage();
  const door = doorOn();
  page.body.append(aCard('Views', '(10 Sep)', '34,877', '14.15%'));
  check('the number a label names is read, commas and all',
    (await door.read_number(BY_TEXT, 'Views')) === 34877);
  /* **THE TWO THINGS IN THE SAME CARD THAT MUST NOT BE TAKEN.** The day is the
   * card's own and the percentage is how much the figure moved -- either would
   * be taken by a rule that merely looked for digits, and a wrong number is
   * worse than none because nothing about it looks wrong afterwards. */
  check('and the day in the card is not mistaken for it',
    (await door.read_number(BY_TEXT, 'Views')) !== 10);
  check('and neither is how much it moved',
    (await door.read_number(BY_TEXT, 'Views')) !== 14);
}

{
  const page = aPage();
  const door = doorOn();
  /* **THREE LEVELS UP THE TWO CARDS MERGE**, which is why the climb is two. A
   * climb of three reads the views figure for orders, quietly. */
  const both = thing('div');
  both.append(aCard('Views', '(10 Sep)', '34,877', '14.15%'),
    aCard('Orders', '(10 Sep)', '6', '2.00%'));
  page.body.append(both);
  check('two cards side by side are read apart, not together',
    (await door.read_number(BY_TEXT, 'Views')) === 34877
      && (await door.read_number(BY_TEXT, 'Orders')) === 6);
}

{
  const page = aPage();
  const door = doorOn();
  /* **AND THE CLIMB REALLY STOPS AT TWO, WHICH THE CHECK ABOVE CANNOT SHOW.**
   * There the number is found at two and the loop returns, so a longer climb
   * would never be taken and raising the limit changes nothing. **This is the
   * card that proves it:** its own two levels hold no number at all, and the
   * block three levels up holds its NEIGHBOUR'S. A climb of three reads 34,877
   * as the order count, silently, and a wrong number is worse than none because
   * nothing about it looks wrong afterwards. */
  const both = thing('div');
  const mine = thing('div');
  const head = thing('div');
  head.append(thing('p', 'Orders'), thing('span', '(10 Sep)'));
  mine.append(head);
  const neighbour = thing('div');
  neighbour.append(thing('p', '34,877'));
  both.append(mine, neighbour);
  page.body.append(both);
  check("a card whose own levels hold no number refuses, rather than taking the next one's",
    (await saidAfterWaiting(() => door.read_number(BY_TEXT, 'Orders')))
      .includes('no plain number'));
}

{
  const page = aPage();
  const door = doorOn();
  /* **HIS SIDEBAR CARRIES `Orders` TOO**, so the words alone match twice. */
  page.body.append(thing('p', 'Orders'), aCard('Orders', '(10 Sep)', '6', '2.00%'));
  check('a label that matches twice is refused rather than guessed at',
    (await saidAfterWaiting(() => door.read_number(BY_TEXT, 'Orders'))).includes('2 things'));
  /* **AND THE DAY THE CARD CARRIES IS WHAT TELLS THEM APART**, which is the same
   * tool every other lookup here uses to say which row it means. */
  check('and narrowed by the day the card carries, it reads the one that has it',
    (await door.read_number(BY_TEXT, 'Orders', true, 0, ['10 Sep'])) === 6);
}

{
  const page = aPage();
  const door = doorOn();
  page.body.append(thing('p', 'Views'));
  check('a label with no number beside it says so, rather than saying not found',
    (await saidAfterWaiting(() => door.read_number(BY_TEXT, 'Views')))
      .includes('no plain number'));
  const empty = aPage();
  const door2 = doorOn();
  check('and a label that is not there at all says that instead',
    (await saidAfterWaiting(() => door2.read_number(BY_TEXT, 'Views')))
      .includes('Nothing on the page matches'));
  check('the page is there to be read', empty.body.tagName === 'body');
}

/* --------------------------------------------------------------- clicking */

{
  const page = aPage();
  const door = doorOn();
  const pressed = [];
  const button = thing('button', 'Export data');
  button.addEventListener('click', () => pressed.push('yes'));
  page.body.append(button);

  door.click(BY_ROLE_AND_TEXT, 'Export data');
  check('the one thing that matches is clicked', pressed.length === 1);
  /* **CLICKING MATCHES THE WHOLE PHRASE UNLESS IT IS TOLD NOT TO.** A part of a
   * name matching loosely is how a chart legend gets pressed instead of a menu
   * item. */
  check('a part of the name does not press the button',
    said(() => door.click(BY_TEXT, 'Export')).includes('Nothing on the page matches'));
  check('and pressed loosely on purpose, it does', pressed.length === 1
    && (door.click(BY_TEXT, 'Export', false), pressed.length === 2));
  check('nothing that is not there can be clicked',
    said(() => door.click(BY_TEXT, 'Export everything')).includes('Nothing on the page matches'));
  check('and that refusal names what was being looked for',
    said(() => door.click(BY_TEXT, 'Export everything')).includes('Export everything'));
}

{
  const page = aPage();
  const door = doorOn();
  const pressed = [];
  /* A click on the words inside a button reaches the button, the way a real
   * one does. */
  const button = thing('button');
  button.addEventListener('click', () => pressed.push('yes'));
  button.append(thing('span', 'Submit'));
  page.body.append(button);

  door.click(BY_TEXT, 'Submit');
  check('clicking the words inside a button presses the button', pressed.length === 1);
}

{
  const page = aPage();
  const door = doorOn();
  const pressed = [];
  const button = thing('button', 'Submit', { disabled: true });
  button.addEventListener('click', () => pressed.push('yes'));
  page.body.append(button);

  check('a switched-off button is said, not silently clicked at',
    said(() => door.click(BY_ROLE_AND_TEXT, 'Submit')).includes('switched off'));
  check('and nothing was pressed', pressed.length === 0);

  page.body.replaceChildren(thing('div', 'Submit', {
    attrs: { role: 'button', 'aria-disabled': 'true' },
  }));
  check('one that only says it is switched off is treated the same way',
    said(() => door.click(BY_ROLE_AND_TEXT, 'Submit')).includes('switched off'));
}

{
  const page = aPage();
  const door = doorOn();
  const pressed = [];
  const first = thing('button', 'Download');
  first.addEventListener('click', () => pressed.push('first'));
  page.body.append(first);
  check('one match now', (await door.find(BY_ROLE_AND_TEXT, 'Download')) === 1);

  /* THE PAGE CARRIES ON DRAWING BETWEEN ONE CALL AND THE NEXT. Clicking must
   * count again rather than trust what it was told a moment ago. */
  page.body.append(thing('button', 'Download'));
  check('a second one arriving after the count still refuses the click',
    said(() => door.click(BY_ROLE_AND_TEXT, 'Download')).includes('2 things'));
  check('and neither of them was pressed', pressed.length === 0);
}

/* ------------------------------------------------------------ a date range */

{
  const page = aPage();
  const door = doorOn();
  const heard = [];
  const from = thing('input', '', { type: 'date' });
  const to = thing('input', '', { type: 'date' });
  /* **HEARD FROM AROUND THE BOXES, NOT ON THEM.** React listens at the top of
   * the page, not on each box, so an event that does not travel upwards is one
   * React never hears -- and the page then submits the dates it had before,
   * with the right ones showing on the screen the whole time. */
  const form = thing('div');
  form.addEventListener('input', (e) => heard.push(`input:${e.target === from ? 'from' : 'to'}`));
  form.addEventListener('change', (e) => heard.push(`change:${e.target === from ? 'from' : 'to'}`));
  form.append(from, to);
  page.body.append(form);

  await door.pick_range('2026-08-25', '2026-08-26');
  check('the first date box takes the start of the range', from.value === '2026-08-25');
  check('the second takes the end', to.value === '2026-08-26');
  /* SAYING THE BOX CHANGED IS NOT DECORATION. Both portals are built with
   * React, which keeps its own copy of what is in every box and never looks at
   * the box again unless it is told. */
  check('the page is told the first box changed, from around it',
    heard.includes('input:from') && heard.includes('change:from'));
  /* AND THE STAND-IN REALLY IS CARRYING IT UPWARD RATHER THAN SHRUGGING. An
   * event that says it does not travel reaches only the box, so a check that
   * listens from around it would go on passing whether the driver said the
   * event travels or not. */
  const onlyHere = [];
  form.addEventListener('keyup', () => onlyHere.push('form'));
  from.addEventListener('keyup', () => onlyHere.push('box'));
  from.dispatchEvent(new Event('keyup'));
  check('an event that does not travel is heard at the box and nowhere else',
    onlyHere.length === 1 && onlyHere[0] === 'box');
  check('and the second one too',
    heard.includes('input:to') && heard.includes('change:to'));
}

{
  const page = aPage();
  const door = doorOn();
  check('with no date boxes at all it refuses and says so',
    (await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26'))).includes('0 date boxes were found'));
  check('and says plainly that nothing was set, so nobody reads it as half done',
    (await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26'))).includes('no dates were set'));

  page.body.append(thing('input', '', { type: 'date' }));
  check('with only one it refuses rather than guessing what the other would be',
    (await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26'))).includes('1 date boxes were found'));

  page.body.append(thing('input', '', { type: 'date' }), thing('input', '', { type: 'date' }));
  check('with three it refuses rather than picking two of them',
    (await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26'))).includes('3 date boxes were found'));
}

{
  const page = aPage();
  const door = doorOn();
  page.body.append(
    thing('input', '', { type: 'date' }),
    thing('input', '', { type: 'date' }),
    thing('input', '', { type: 'date', box: NOT_PAINTED }),
    /* A box somebody types a date into by hand is not a date box, and neither
     * is anything that is not a box at all. Counted, either of them would take
     * a range of two boxes up to three and the whole step would refuse. */
    thing('input', '', { type: 'text' }),
    thing('div', 'from', { type: 'date' })
  );
  check('a date box the browser never painted is not one of them, nor is a plain box',
    (await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26'))) === '');
}

{
  /* **PUT IN THE WAY A BROWSER PUTS IT IN.** React keeps its own copy of what is
   * in every box and ignores one that was changed behind its back, so the value
   * has to go through the browser's own setter. That setter exists in a browser
   * and not in the stand-in, which is the one place in the driver where the two
   * genuinely differ -- so here is one, behaving as a browser's does. */
  const page = aPage();
  const door = doorOn();
  const throughTheBrowser = [];
  const standInValue = Object.getOwnPropertyDescriptor(FakeNode.prototype, 'value');
  class PretendInputElement {}
  Object.defineProperty(PretendInputElement.prototype, 'value', {
    configurable: true,
    get() { return standInValue.get.call(this); },
    set(v) { throughTheBrowser.push(v); standInValue.set.call(this, v); },
  });
  globalThis.HTMLInputElement = PretendInputElement;

  const from = thing('input', '', { type: 'date' });
  const to = thing('input', '', { type: 'date' });
  page.body.append(from, to);
  await door.pick_range('2026-08-25', '2026-08-26');

  check("both dates go in through the browser's own setter when there is one",
    throughTheBrowser.length === 2);
  check('and they still end up in the boxes',
    from.value === '2026-08-25' && to.value === '2026-08-26');
  delete globalThis.HTMLInputElement;
}

{
  /* **THE DATE PICKER IS DRAWN BY THE CLICK BEFORE IT.** Asked the instant that
   * click returns, the boxes are not there yet -- and a step that refuses then
   * reads as the portal having changed, which it has not. */
  const page = aPage();
  const door = doorOn();
  setTimeout(() => page.body.append(
    thing('input', '', { type: 'date' }),
    thing('input', '', { type: 'date' })
  ), 80);
  check('given time, it waits for the date picker to be drawn',
    (await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26', 3))) === '');
  check('and the dates went in once it was',
    everyDateBox(page)[0].value === '2026-08-25' && everyDateBox(page)[1].value === '2026-08-26');

  const empty = aPage();
  const startedAt = Date.now();
  check('with no patience given it refuses at once rather than hanging',
    (await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26'))).includes('0 date boxes were found'));
  check('having not waited', Date.now() - startedAt < 200 && empty.body.children.length === 0);
}

/* ---------------------------------------- a date range on a CALENDAR
 *
 * **THIS IS THE HOLE THE PRODUCT FELL DOWN, AND IT IS WORTH SAYING PLAINLY.**
 * The step that sets a date range was written to find two date boxes and type
 * into them. **Meesho has no date boxes. It has a calendar.** On his own panel
 * on 2026-09-09 it reported "0 were found, so no dates were set" -- nought,
 * because there never were any, on any night. **Flipkart's Reports Centre is a
 * calendar too**, so the one strategy the step had worked on neither portal.
 *
 * Everything below is read off the working reference, which has driven both
 * calendars every night for months: `content/meesho.js fillMeeshoDates` and
 * `content/flipkart.js` StepD/StepE. Every label format and every count in here
 * was paid for against the real portals and is not re-derived.
 */

const MONTHS_IN_FULL = ['January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'];
const MONTHS_ABBREVIATED = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const WEEKDAYS_ABBREVIATED = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

/** How Meesho's orders and returns modals label a day: "Fri May 01 2026". */
function meeshoOrdersLabel(y, m, d) {
  return `${WEEKDAYS_ABBREVIATED[new Date(y, m - 1, d).getDay()]} `
    + `${MONTHS_ABBREVIATED[m - 1]} ${String(d).padStart(2, '0')} ${y}`;
}

/** How Meesho's payments page labels the same day: "Jun 2, 2026". */
function meeshoPaymentsLabel(y, m, d) {
  return `${MONTHS_ABBREVIATED[m - 1]} ${d}, ${y}`;
}

/**
 * One month's panel, drawn the way both portals draw one: a heading reading
 * "August 2026" and a grid of day cells under it.
 *
 * `label` decides which of the two shapes it is. Given one, the cells carry an
 * aria-label naming the whole day -- that is Meesho. Given none, they carry the
 * day number and nothing else, and the only thing saying which month they are
 * in is the heading above them -- that is Flipkart's react-dates calendar,
 * where the reference finds the day by walking DOWN from the heading.
 */
function aMonthPanel(y, m, { label = null, days = 30 } = {}) {
  const panel = thing('div');
  panel.append(thing('div', `${MONTHS_IN_FULL[m - 1]} ${y}`));
  const grid = thing('div');
  for (let d = 1; d <= days; d += 1) {
    const cell = thing('td', String(d));
    if (label) cell.setAttribute('aria-label', label(y, m, d));
    grid.append(cell);
  }
  panel.append(grid);
  return panel;
}

/** Which days on this panel got pressed, in order, written as whole days. */
function watchTheDays(panel, y, m) {
  const pressed = [];
  const walk = (node) => {
    if (node.tagName === 'td') {
      const d = Number(node.textContent);
      node.addEventListener('click', () => pressed.push(
        `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      ));
    }
    for (const child of node.children) walk(child);
  };
  walk(panel);
  return pressed;
}

/** Every day cell on a panel, for styling them the way a real one is styled.
 *  A react-dates day that can be pressed carries `cursor: pointer`; a plain
 *  stand-in cell carries nothing, which is the difference the cursor rule
 *  turns on. */
function everyDayCell(panel) {
  const found = [];
  const walk = (node) => {
    if (node.tagName === 'td') found.push(node);
    for (const child of node.children) walk(child);
  };
  walk(panel);
  return found;
}

/** One thing under here carrying that aria-label. */
function labelled(node, label) {
  if (node.getAttribute('aria-label') === label) return node;
  for (const child of node.children) {
    const found = labelled(child, label);
    if (found) return found;
  }
  return null;
}

{
  /* **MEESHO'S ORDERS MODAL, AND THIS IS THE CHECK THAT WAS RED.** No date box
   * anywhere on the page; a calendar, whose cells name the day they are. */
  const page = aPage();
  const door = doorOn();
  const panel = aMonthPanel(2026, 8, { label: meeshoOrdersLabel, days: 31 });
  const pressed = watchTheDays(panel, 2026, 8);
  page.body.append(panel);

  check('a calendar with no date boxes on the page still gets the range set',
    (await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26'))) === '');
  check('and the two days pressed are the two asked for, in that order',
    JSON.stringify(pressed) === JSON.stringify(['2026-08-25', '2026-08-26']));
}

{
  /* **HIS REAL MEESHO ORDERS MODAL, READ OFF THE LIVE PAGE ON 2026-09-11**, and
   * every line of it is a measurement rather than a reading of code:
   *
   *   - not one `input[type="date"]` anywhere on the modal;
   *   - the From and To boxes are `type="text"` and `readOnly`, placeholders
   *     "Select From Date" and "DD/MM/YYYY" -- **typing into them could never
   *     have worked**;
   *   - the day cells say `aria-label="Tue Sep 01 2026"`;
   *   - **and the month is a DROPDOWN of all twelve names, so what the heading
   *     reads is "JanuaryFebruaryMarch..." and never "September 2026".**
   *
   * The step used to ask whether a month heading was showing before it would
   * believe a calendar was there at all. On this page no heading can ever
   * match, so it refused -- "0 date boxes were found and no calendar was
   * showing" -- **while the cells beside it were naming the day outright.** */
  const page = aPage();
  const door = doorOn();

  const modal = thing('div');
  const months = thing('select');
  for (const name of MONTHS_IN_FULL) months.append(thing('option', name));
  modal.append(months);
  modal.append(thing('button', '', { attrs: { 'aria-label': 'Previous month' } }));
  modal.append(thing('button', '', { attrs: { 'aria-label': 'Next month' } }));

  const from = thing('input', '', { type: 'text', readOnly: true, placeholder: 'Select From Date' });
  const to = thing('input', '', { type: 'text', readOnly: true, placeholder: 'DD/MM/YYYY' });
  modal.append(from, to);

  const grid = thing('div');
  for (let d = 1; d <= 30; d += 1) {
    grid.append(thing('td', String(d), { attrs: { 'aria-label': meeshoOrdersLabel(2026, 9, d) } }));
  }
  modal.append(grid);
  const pressed = watchTheDays(grid, 2026, 9);
  page.body.append(modal);

  check('a calendar whose month is a dropdown, so no heading ever matches, still gets the range set',
    (await saidAfterWaiting(() => door.pick_range('2026-09-01', '2026-09-02'))) === '');
  check('and the two days pressed are the two asked for',
    JSON.stringify(pressed) === JSON.stringify(['2026-09-01', '2026-09-02']));
  check('and the read-only boxes it could never have typed into were left alone',
    from.value === '' && to.value === '');
}

{
  /* **THE SAME PORTAL WRITES THE SAME DAY TWO DIFFERENT WAYS**, and the
   * reference knows both because it was caught by the second: orders and
   * returns say "Fri May 01 2026", payments says "Jun 2, 2026". */
  const page = aPage();
  const door = doorOn();
  const panel = aMonthPanel(2026, 8, { label: meeshoPaymentsLabel, days: 31 });
  const pressed = watchTheDays(panel, 2026, 8);
  page.body.append(panel);

  check("the payments page's own way of writing a day is understood too",
    (await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26'))) === '');
  check('and it pressed the right two days',
    JSON.stringify(pressed) === JSON.stringify(['2026-08-25', '2026-08-26']));
}

{
  /* **FLIPKART'S REPORTS CENTRE, WHICH LABELS NOTHING.** Its cells carry the
   * day number and nothing else, so the only thing saying which month a "25"
   * belongs to is the heading above it -- and it draws TWO months side by side.
   * The reference picked the wrong month here once (10 May for 10 Jun) and
   * fixed it by walking down from the heading rather than up from the cell. */
  const page = aPage();
  const door = doorOn();
  const august = aMonthPanel(2026, 8, { days: 31 });
  const september = aMonthPanel(2026, 9, { days: 30 });
  const pressedInAugust = watchTheDays(august, 2026, 8);
  const pressedInSeptember = watchTheDays(september, 2026, 9);
  const both = thing('div');
  both.append(august, september);
  page.body.append(both);

  check('a calendar that labels nothing is driven by the heading above the days',
    (await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26'))) === '');
  check('and with two months side by side it pressed the days in the right one',
    JSON.stringify(pressedInAugust) === JSON.stringify(['2026-08-25', '2026-08-26']));
  check('and pressed nothing at all in the other month', pressedInSeptember.length === 0);
}

{
  /* **A CALENDAR OPENS ON WHATEVER MONTH IT LIKES**, and the day wanted is
   * often not on it. The reference steps through up to fourteen months, and it
   * goes BACKWARDS as readily as forwards -- a night catching up an old day
   * needs the arrow the other way. */
  const page = aPage();
  const door = doorOn();
  let showing = 10;
  const holder = thing('div');
  const draw = () => {
    holder.textContent = '';
    holder.append(aMonthPanel(2026, showing, { label: meeshoOrdersLabel, days: 31 }));
  };
  const back = thing('button', '', { attrs: { 'aria-label': 'Previous Month' } });
  back.addEventListener('click', () => { showing -= 1; draw(); });
  const on = thing('button', '', { attrs: { 'aria-label': 'Next Month' } });
  on.addEventListener('click', () => { showing += 1; draw(); });
  draw();
  page.body.append(back, on, holder);

  check('a calendar showing the wrong month is stepped backwards to the right one',
    (await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26'))) === '');
  check('and it stopped on the month it wanted rather than stepping past it', showing === 8);
}

{
  const page = aPage();
  const door = doorOn();
  let showing = 6;
  const holder = thing('div');
  const draw = () => {
    holder.textContent = '';
    holder.append(aMonthPanel(2026, showing, { label: meeshoOrdersLabel, days: 31 }));
  };
  const on = thing('button', '>');
  on.addEventListener('click', () => { showing += 1; draw(); });
  draw();
  page.body.append(on, holder);

  check('and forwards when the day wanted is later, with an arrow that has no name at all',
    (await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26'))) === '');
  check('landing on the right month', showing === 8);
}

{
  /* **AN ARROW DRAWN AS A CHARACTER RATHER THAN A WORD**, which is the commoner
   * shape. The driver spells these five characters as numbers because every
   * file here is plain ASCII and the commit gate reads a diff through Windows'
   * own encoding, which cannot read an arrow -- so this presses a real one and
   * proves the spelling is still the character it means. */
  const page = aPage();
  const door = doorOn();
  let showing = 7;
  const holder = thing('div');
  const draw = () => {
    holder.textContent = '';
    holder.append(aMonthPanel(2026, showing, { label: meeshoOrdersLabel, days: 31 }));
  };
  const on = thing('button', '\u203a');
  on.addEventListener('click', () => { showing += 1; draw(); });
  draw();
  page.body.append(on, holder);

  check('an arrow written as a character rather than a word still steps the month',
    (await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26'))) === '');
  check('and it landed on the month it wanted', showing === 8);
}

{
  /* **A DAY THAT IS NOT THERE IS SAID, AND WHAT WAS LOOKED FOR IS SAID WITH
   * IT.** "Not found" on its own is the failure this whole product exists to
   * stop: a month of diagnosis went at a button that had not moved. */
  const page = aPage();
  const door = doorOn();
  page.body.append(aMonthPanel(2026, 8, { label: meeshoOrdersLabel, days: 20 }));
  const refused = await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26'));
  check('a day the calendar does not carry is refused', refused !== '');
  check('and the refusal says both ways that day would have been written',
    refused.includes(meeshoOrdersLabel(2026, 8, 25))
    && refused.includes(meeshoPaymentsLabel(2026, 8, 25)));
  check('and says plainly that nothing was set', refused.includes('No dates were set'));
}

{
  /* **TWO THINGS CLAIMING TO BE THE SAME DAY IS A REFUSAL, NOT A COIN TOSS**,
   * and it is the same rule `find` answers a count for. A file of the wrong
   * days is worse than no file, because nothing about it looks wrong after. */
  const page = aPage();
  const door = doorOn();
  const one = thing('td', '25', { attrs: { 'aria-label': meeshoOrdersLabel(2026, 8, 25) } });
  const two = thing('td', '25', { attrs: { 'aria-label': meeshoOrdersLabel(2026, 8, 25) } });
  page.body.append(aMonthPanel(2026, 8, { days: 31 }), one, two);
  check('two things claiming to be the same day refuses rather than picking one',
    (await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26'))).includes('2 things'));
}

{
  /* **A DAY THE PORTAL HAS SWITCHED OFF IS SAID, NOT SILENTLY CLICKED AT.**
   * Read off his own Flipkart on 2026-07-13: a day whose report period has not
   * opened yet keeps its ordinary look and is given `pointer-events: none`, so
   * a click does nothing at all and the step after fails somewhere unrelated. */
  const page = aPage();
  const door = doorOn();
  const panel = aMonthPanel(2026, 8, { label: meeshoOrdersLabel, days: 31 });
  page.body.append(panel);
  labelled(panel, meeshoOrdersLabel(2026, 8, 26)).style.pointerEvents = 'none';
  const refused = await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26'));
  check('a day the portal has switched off is refused rather than clicked at',
    refused.includes('switched off'));
  check('and the refusal names the day', refused.includes('2026-08-26'));
  check('and it is not reported as the day being missing',
    !refused.includes('is not on the calendar'));
}

{
  /* **AND THE REFUSAL CARRIES A MARK, NOT ONLY WORDS -- HIS RULING, 2026-09-14.**
   * A day the portal has not built is "not available yet" rather than a failure,
   * and the walk tells the two apart by this mark alone, so the sentence stays
   * free to change. */
  const page = aPage();
  const door = doorOn();
  const panel = aMonthPanel(2026, 8, { label: meeshoOrdersLabel, days: 31 });
  page.body.append(panel);
  labelled(panel, meeshoOrdersLabel(2026, 8, 26)).style.pointerEvents = 'none';
  let thrown = null;
  try {
    await door.pick_range('2026-08-25', '2026-08-26');
  } catch (wrong) {
    thrown = wrong;
  }
  check('a day the portal has not built is marked as not available, not only described',
    Boolean(thrown) && thrown.dayNotAvailable === true);
}

{
  /* **THE SECOND WAY THE SAME PORTAL SWITCHES A DAY OFF, WHICH THE CHECK ABOVE
   * CANNOT SEE AT ALL.** Confirmed with the browser's own tools on 2026-07-14,
   * a day later than the one above: a day genuinely outside the range gets a
   * `blocked_out_of_range` class that **leaves pointer-events entirely alone**
   * and says so only in the cursor -- `no-drop` where a day that really can be
   * pressed says `pointer`. Two techniques, one grey day on the screen, and one
   * check could never have caught both.
   *
   * **AND IT IS ASKED FOR RATHER THAN ASSUMED, which is the other half of the
   * lesson.** "Anything that is not a pointer is switched off" is that one
   * portal's habit and not a rule of browsers, so the same page and the same
   * cell, with the recipe not saying so, is pressed. */
  const page = aPage();
  const door = doorOn();
  const panel = aMonthPanel(2026, 8, { days: 31 });
  for (const cell of everyDayCell(panel)) cell.style.cursor = 'pointer';
  everyDayCell(panel).find((one) => one.textContent === '26').style.cursor = 'no-drop';
  page.body.append(panel);
  const refused = await saidAfterWaiting(
    () => door.pick_range('2026-08-25', '2026-08-26', 0, true));
  check('on a calendar that says it in the cursor, a day switched off that way is refused',
    refused.includes('switched off') && refused.includes('2026-08-26'));
  /* **AND NOT ONE THAT KEEPS ITS POINTER**, or the rule would refuse every day
   * on the calendar and read exactly like the portal being shut. */
  const pressed = watchTheDays(panel, 2026, 8);
  check('and a day on that same calendar that keeps its pointer is still pressed',
    (await saidAfterWaiting(() => door.pick_range('2026-08-24', '2026-08-25', 0, true))) === ''
    && JSON.stringify(pressed) === JSON.stringify(['2026-08-24', '2026-08-25']));
}

{
  /* **THE NEXT MONTH'S FIRST DAYS, DRAWN GREYED AT THE END OF THIS MONTH'S GRID.**
   * Measured on his Flipkart traffic calendar, 2026-09-14: the `Sep 2026` panel
   * reads `1 ... 30 1 2 3 4`, the spill-over days `cursor: not-allowed`, and
   * asking for 09-01 refused on two "1"s. */
  const spillOver = (switchOffTheRealOne = false) => {
    const panel = aMonthPanel(2026, 9, { days: 30 });
    for (const cell of everyDayCell(panel)) cell.style.cursor = 'pointer';
    const grid = everyDayCell(panel)[0].parentNode;
    for (let d = 1; d <= 4; d += 1) {
      const next = thing('td', String(d));
      next.style.cursor = 'not-allowed';
      grid.append(next);
    }
    const real = everyDayCell(panel)[0];
    if (switchOffTheRealOne) real.style.cursor = 'not-allowed';
    return { panel, real, greyed: everyDayCell(panel)[30] };
  };

  {
    const page = aPage();
    const door = doorOn();
    const { panel, real, greyed } = spillOver();
    const hits = [];
    real.addEventListener('click', () => hits.push('real'));
    greyed.addEventListener('click', () => hits.push('greyed'));
    page.body.append(panel);
    check('a greyed spill-over day is not mistaken for the day asked for',
      (await saidAfterWaiting(() => door.pick_range('2026-09-01', '2026-09-01', 0, true))) === ''
      && hits.length > 0 && hits.every((one) => one === 'real'));
  }
  {
    const page = aPage();
    const door = doorOn();
    const { panel } = spillOver();
    page.body.append(panel);
    check('and on a calendar the recipe says nothing about, two matches are still refused',
      (await saidAfterWaiting(() => door.pick_range('2026-09-01', '2026-09-01'))).includes('2 things'));
  }
  {
    const page = aPage();
    const door = doorOn();
    const { panel } = spillOver(true);
    page.body.append(panel);
    check('and when the real day is greyed too, it is switched off, not ambiguous',
      (await saidAfterWaiting(() => door.pick_range('2026-09-01', '2026-09-01', 0, true)))
        .includes('switched off'));
  }
}

{
  /* **THE SAME CELL, ON A CALENDAR THE RECIPE SAYS NOTHING ABOUT, IS PRESSED.**
   * An ordinary unstyled cell has no pointer cursor either, so a door that read
   * the cursor everywhere would refuse days that are perfectly available on
   * somebody else's portal. That is why this is a fact the recipe carries. */
  const page = aPage();
  const door = doorOn();
  const panel = aMonthPanel(2026, 8, { days: 31 });
  everyDayCell(panel).find((one) => one.textContent === '26').style.cursor = 'no-drop';
  const pressed = watchTheDays(panel, 2026, 8);
  page.body.append(panel);
  check('the same day on a calendar the recipe says nothing about is pressed as normal',
    (await saidAfterWaiting(() => door.pick_range('2026-08-25', '2026-08-26'))) === ''
    && JSON.stringify(pressed) === JSON.stringify(['2026-08-25', '2026-08-26']));
}

{
  /* **BOXES STILL WIN WHERE A PORTAL REALLY HAS THEM.** Neither of his does
   * today -- both are calendars -- but the reference tries native date boxes
   * first on both platforms, and where exactly two exist there is nothing to
   * guess about which is which. */
  const page = aPage();
  const door = doorOn();
  const from = thing('input', '', { type: 'date' });
  const to = thing('input', '', { type: 'date' });
  const panel = aMonthPanel(2026, 8, { label: meeshoOrdersLabel, days: 31 });
  const pressed = watchTheDays(panel, 2026, 8);
  page.body.append(from, to, panel);
  await door.pick_range('2026-08-25', '2026-08-26');
  check('with two date boxes AND a calendar, the boxes are used',
    from.value === '2026-08-25' && to.value === '2026-08-26');
  check('and nothing on the calendar was pressed', pressed.length === 0);
}

/* ------------------------------------------------ something over the page */

{
  const page = aPage();
  const door = doorOn();
  check('a clear page has nothing over it', door.overlays().length === 0);

  /* **READ OFF HIS OWN MEESHO PANEL ON 2026-08-27.** The promotion sits on
   * role="dialog", its close control is an `<img>` with no class, no label and
   * no text, and Escape does not shut it. Nothing here tries. */
  page.body.append(thing('div', 'Abhi Update Karein', {
    attrs: { role: 'dialog' }, box: BIG,
  }));
  const over = door.overlays();
  check('a promotion sitting over the page is reported', over.length === 1);
  check('with the size the browser painted it', over[0].width === 600 && over[0].height === 400);
  check('and the words on it, so it can be recognised again',
    over[0].text === 'Abhi Update Karein');
  /* **A DIALOG THAT FLOWS WITH THE PAGE DOES NOT SWALLOW A CLICK.** */
  check('and it does not block, because nothing is laid over the page',
    over[0].blocks === false);
}

{
  /* **THE NEAR-MISS THAT CHANGED THIS RULE, both sides measured on his own
   * Meesho on 2026-08-28.** The download menu the recipe opens ON PURPOSE
   * declares itself a dialog and is 232 x 196. The promotion that cost a month
   * of "button not found" is 414 x 330 and sits on a full-screen backdrop.
   * Judged by size, four pixels separated them. */
  const page = aPage();
  const door = doorOn();
  const menu = thing('div', 'GST ReportTax InvoicePayments to Date', {
    attrs: { role: 'dialog' },
    box: { top: 0, bottom: 196, left: 0, right: 232, width: 232, height: 196 },
  });
  page.body.append(menu);
  check('a menu the door opened itself is not something covering the page',
    door.overlays().every((one) => one.blocks === false));

  /* Now the promotion: the same kind of dialog, but laid over everything. */
  const backdrop = thing('div', '', {
    box: { top: 0, bottom: 800, left: 0, right: 1280, width: 1280, height: 800 },
  });
  backdrop.style.position = 'fixed';
  page.body.append(backdrop);
  check('while a backdrop laid over the whole window does block',
    door.overlays().some((one) => one.blocks === true));

  /* And one that is laid over the page but only covers a corner does not. */
  page.body.replaceChildren();
  const corner = thing('div', 'Saved', {
    box: { top: 0, bottom: 80, left: 0, right: 250, width: 250, height: 80 },
  });
  corner.style.position = 'fixed';
  page.body.append(corner);
  check('and a small notice pinned to a corner does not block',
    door.overlays().every((one) => one.blocks === false));

  /* Nor does something the size of the window that simply flows with it -- that
   * is the page's own content, not a covering. */
  page.body.replaceChildren();
  page.body.append(thing('main', 'the whole page', {
    box: { top: 0, bottom: 800, left: 0, right: 1280, width: 1280, height: 800 },
  }));
  check('nor does the page own content, which is not laid over anything',
    door.overlays().length === 0);

  /* **MEASURED ON HIS OWN FLIPKART SELLER INSIGHTS, 2026-09-21 (A58, Job 3).**
   * The only full-window thing laid over that page was
   * `div.styles__Backdrop-sc-93p85o-1`: fixed, 1280 x 529, and
   * `visibility: hidden` with `opacity: 0` -- a drawer's backdrop kept ready,
   * not shown. It made every miss on that page read "something is covering the
   * page". A backdrop nobody can see, or that lets clicks through, covers
   * nothing. */
  const hiddenOne = (set) => {
    page.body.replaceChildren();
    const sheet = thing('div', '', {
      box: { top: 0, bottom: 800, left: 0, right: 1280, width: 1280, height: 800 },
    });
    sheet.style.position = 'fixed';
    set(sheet.style);
    page.body.append(sheet);
    return door.overlays().every((one) => one.blocks === false);
  };
  check('a full-window backdrop that is visibility:hidden does not block',
    hiddenOne((s) => { s.visibility = 'hidden'; }));
  check('nor one drawn with opacity 0',
    hiddenOne((s) => { s.opacity = '0'; }));
  check('nor one that lets every click through (pointer-events: none)',
    hiddenOne((s) => { s.pointerEvents = 'none'; }));

  /* **UNDER INVESTIGATION, JOB 3B, 2026-09-22 -- NOT YET NAMED AS THE CAUSE.**
   * `fk_views` read "something is covering the page" again in the 03:30 timed
   * sync, after Job 3's hidden-backdrop fix. Looking at what "sits over the
   * whole page" measures: `position`, `visibility`, `opacity`, `pointer-events`
   * and a box `width`/`height` at least 90% of the window -- **never where that
   * box actually SITS**. A React picker kept mounted and moved off-screen
   * (`transform: translate(-9999px, 0)`, or a large negative `left`) after its
   * own "Done" is clicked -- which is exactly what `fk_views` presses right
   * before this wait -- would still report a box that size and still pass
   * every check here, though it swallows no click at all. **This is written
   * down because it is a real gap, not because it is proved to be today's
   * cause** -- his console line settles that. */
  const offScreenOne = (left) => {
    page.body.replaceChildren();
    const sheet = thing('div', '', {
      box: { top: 0, bottom: 800, left, right: left + 1280, width: 1280, height: 800 },
    });
    sheet.style.position = 'fixed';
    page.body.append(sheet);
    return door.overlays().every((one) => one.blocks === false);
  };
  check('a full-size backdrop moved off-screen does not block',
    offScreenOne(-4000));

  /* **THE EDGES OF THAT MEASUREMENT (EX1, 2026-10-03).** Only a box that does
   * not overlap the window at all stops blocking. Anything that overlaps it
   * still blocks what it covers, so nothing that blocked before stops. */
  const placed = (box) => {
    page.body.replaceChildren();
    const sheet = thing('div', '', { box });
    sheet.style.position = 'fixed';
    page.body.append(sheet);
    return door.overlays().some((one) => one.blocks === true);
  };
  const full = (left, top) => ({
    top, bottom: top + 800, left, right: left + 1280, width: 1280, height: 800,
  });
  check('a full-size backdrop moved off to the right does not block', !placed(full(4000, 0)));
  check('nor one moved above the window', !placed(full(0, -4000)));
  check('nor one moved below it', !placed(full(0, 4000)));
  check('nor one whose right edge only just touches the window edge', !placed(full(-1280, 0)));
  check('a backdrop in its place still blocks', placed(full(0, 0)));
  check('and one slid part-way off to the left still blocks what it covers',
    placed(full(-640, 0)));
  check('and one slid part-way off the top still blocks what it covers',
    placed(full(0, -400)));
  check('and one slid just a little off the window still blocks', placed(full(-100, -50)));
  check('and one overhanging the window on every side still blocks',
    placed({ top: -50, bottom: 850, left: -50, right: 1330, width: 1380, height: 900 }));
  /* A box that gives a size and no position is judged by size, as it always was. */
  check('a box that reports only its size is still judged by size',
    placed({ width: 1280, height: 800 }));
  /* An absolutely positioned one scrolled out of a container reads the same way
   * as a translated one: its window position is off the window. */
  page.body.replaceChildren();
  const scrolledAway = thing('div', '', { box: full(0, -2400) });
  scrolledAway.style.position = 'absolute';
  page.body.append(scrolledAway);
  check('an absolute backdrop scrolled out of the window does not block',
    door.overlays().every((one) => one.blocks === false));
  /* A dialog moved off-screen is still said to be there, but not to block. */
  page.body.replaceChildren();
  const parkedDialog = thing('div', 'Pick a date', { attrs: { role: 'dialog' }, box: full(-4000, 0) });
  parkedDialog.style.position = 'fixed';
  page.body.append(parkedDialog);
  check('a dialog parked off-screen is still reported', door.overlays().length === 1);
  check('but it does not block', door.overlays()[0].blocks === false);
}

{
  const page = aPage();
  const door = doorOn();
  page.body.append(thing('div', 'a', { attrs: { 'aria-modal': 'true' }, box: BIG }));
  check('one that says only that it is modal is reported too', door.overlays().length === 1);
  check('and it says whether it would swallow a click',
    'blocks' in door.overlays()[0]);

  page.body.replaceChildren(thing('dialog', 'b', { box: BIG }));
  check('and so is a real dialog element', door.overlays().length === 1);

  page.body.replaceChildren(thing('div', 'c', { attrs: { role: 'dialog' }, box: NOT_PAINTED }));
  check('a dialog that is not being painted is not over anything',
    door.overlays().length === 0);
}

{
  const page = aPage();
  const door = doorOn();
  page.body.append(thing('div', 'x'.repeat(400), { attrs: { role: 'dialog' }, box: BIG }));
  check('a great deal of words on it is cut down to something a log can hold',
    door.overlays()[0].text.length === 300);
}

/* ---------------------------------------------------------- what is on the page */

{
  const page = aPage();
  const door = doorOn();
  page.body.append(thing('h1', 'Payments'), thing('p', '   settled    on\n 25 August '));
  check('the page is read back as the words on it',
    door.page_text() === 'Payments settled on 25 August');

  page.body.replaceChildren(thing('p', 'y'.repeat(9000)));
  check('and a very long page is cut down rather than sent whole',
    door.page_text().length === 5000);
}

/* -------------------------------------------------- is it asking to sign in? */

{
  const page = aPage();
  const door = doorOn();
  /* **A SIGNED-IN PAGE PART-WAY THROUGH DRAWING.** The seller's own top bar,
   * no sidebar yet. 54 of 71 real occurrences were this, and calling it
   * "signed out" is why a month of them read as one problem. */
  page.body.append(thing('div', 'Rumee Jewellery'), thing('div', 'Loading'));
  check('a page that has simply not finished drawing is not asking to sign in',
    door.needs_signing_in() === false);
}

{
  const page = aPage();
  const door = doorOn();
  /* **THE FAULT FOUND ON HIS OWN MEESHO, 2026-08-27.** Read as a run of letters
   * anywhere on the page, "Grow" matches inside "Grow Business" -- and that
   * word is not on the page at all as a thing anybody could press. It is the
   * loose match that cost nine days of payments, in the fix for a different
   * problem. */
  /* TWO of them, both hiding inside a longer name -- because the rule needs two
   * to fire, and one alone would pass whether the words were matched whole or
   * not. This is the check that would have caught the live fault. */
  page.body.append(thing('a', 'Grow Business'), thing('a', 'Shopsy Partner Programme'));
  check('signs hidden inside longer names are not signs',
    door.needs_signing_in() === false);
  check('and each of them really is on the page, loosely speaking',
    (await door.find(BY_ROLE_AND_TEXT, 'Grow', false)) === 1
    && (await door.find(BY_ROLE_AND_TEXT, 'Shopsy', false)) === 1);

  /* Nor is one that is merely written on the page rather than being a menu
   * item: the marketing site's menu is a row of things you can press. */
  page.body.replaceChildren(thing('p', 'Sell Online'), thing('p', 'Shopsy'));
  check('nor are two words merely written somewhere on the page',
    door.needs_signing_in() === false);

  page.body.replaceChildren(thing('a', 'Sell Online'));
  check('one menu item on its own is not enough either',
    door.needs_signing_in() === false);

  page.body.append(thing('a', 'Shopsy'));
  check('the public menu, which carries them together, is',
    door.needs_signing_in() === true);

  /* And a menu item the browser is not painting is not on the page. */
  page.body.replaceChildren(
    thing('a', 'Sell Online'), thing('a', 'Shopsy', { box: NOT_PAINTED })
  );
  check('and a menu item that is not being painted does not count',
    door.needs_signing_in() === false);
}


{
  const page = aPage();
  const door = doorOn();
  page.body.append(
    thing('input', '', { type: 'text' }),
    thing('input', '', { type: 'password' })
  );
  check('a box asking for a password is the portal asking, whatever else is on it',
    door.needs_signing_in() === true);

  page.body.replaceChildren(thing('input', '', { type: 'password', box: NOT_PAINTED }));
  check('and one that is not being painted is not being asked for',
    door.needs_signing_in() === false);

  page.body.replaceChildren(thing('input', '', { type: 'text' }));
  check('an ordinary box somebody types in is not the portal asking',
    door.needs_signing_in() === false);
  /* Stands for anything on the page that is not a box at all. A real one has no
   * kind to read; this one is given the kind that matters, so the rule that
   * only a box counts is the thing being proved. */
  page.body.replaceChildren(thing('div', 'password', { type: 'password' }));
  check('nor is something that merely says the word',
    door.needs_signing_in() === false);
}


/* --------------- a message from the page, and whether to believe it (D135) */

/* **THE PORTAL'S PAGE IS SOMEBODY ELSE'S CODE WITH SOMEBODY ELSE'S ADVERTS IN
 * IT.** Cycle 46 found that a message from it was believed on nothing but its
 * having come from that page -- so an advert could have posted bytes of its own
 * and they would have gone into the seller's Drive under a real report's name. */
{
  const theWindow = {};
  const genuine = {
    source: theWindow,
    currentTarget: theWindow,
    data: { kartaan: CAUGHT_A_FILE, secret: 'the-secret', file: 'the-genuine-file' },
  };
  const found = theCatcherSaid(genuine, 'the-secret');
  check('a message carrying the secret we are waiting for is ours', found !== null);
  check('and it hands back what was said', found.file === 'the-genuine-file');

  /* **THE FORGERY, and it is the whole reason this function exists.** Right
   * name, right page, right shape -- and no secret. */
  const forged = {
    source: theWindow,
    currentTarget: theWindow,
    data: { kartaan: CAUGHT_A_FILE, file: 'a-file-of-their-own' },
  };
  check('a message with no secret at all is refused',
    theCatcherSaid(forged, 'the-secret') === null);
  check('and one carrying the wrong secret is refused',
    theCatcherSaid({ ...forged, data: { ...forged.data, secret: 'a-guess' } }, 'the-secret') === null);
  /* **AND YESTERDAY'S SECRET IS THE WRONG SECRET.** The page can read one out of
   * the genuine message the moment it arrives; a fresh one every file is what
   * makes that too late to be any use. */
  check('and one carrying the secret from the file before is refused',
    theCatcherSaid({ ...forged, data: { ...forged.data, secret: 'the-one-before' } },
      'the-secret') === null);

  /* **NOTHING IS BELIEVED WHEN NOTHING IS BEING WAITED FOR.** Otherwise a
   * message arriving between two reports is read as belonging to the second. */
  check('nothing at all is believed when no file is being waited for',
    theCatcherSaid(genuine, null) === null);

  /* **AND NOT FROM ANOTHER FRAME.** A portal page can embed somebody else's, and
   * a message from it arrives at this same listener. */
  check('a message from a different window is refused',
    theCatcherSaid({ ...genuine, source: {} }, 'the-secret') === null);

  /* Ordinary page chatter is not an error, it is simply not ours. */
  check('a message that is not about a file at all is not ours',
    theCatcherSaid({ source: theWindow, currentTarget: theWindow, data: { hello: 1 } },
      'the-secret') === null);
  check('and neither is one with nothing in it',
    theCatcherSaid({ source: theWindow, currentTarget: theWindow }, 'the-secret') === null);
  check('and neither is nothing at all', theCatcherSaid(null, 'the-secret') === null);

  /* ---- AN ADDRESS IS NOT A FILE, AND IT IS NARROWED TWICE (2026-09-11)
   *
   * **THE BYTES OF A FILE CROSSED AS BYTES THE BROWSER ITSELF COPIED. AN
   * ADDRESS IS A STRING THE PAGE CHOSE**, and the extension goes and fetches
   * whatever it names with the seller's own cookies. An address nobody narrowed
   * is a way to put anything at all into the seller's Drive under a real
   * report's name -- the same harm as D135, by a shorter road. */
  const saying = (address) => theCatcherSaid({
    source: theWindow,
    currentTarget: theWindow,
    data: { kartaan: CAUGHT_A_FILE, secret: 'the-secret', address },
  }, 'the-secret');

  check('AN ADDRESS A REPORT REALLY COMES FROM IS BELIEVED',
    saying('https://storage.googleapis.com/meesho-prod/inventory.xlsx?X-Goog-Signature=aa')
      !== null);
  /* **THE ONE MEASURED ON HIS OWN PANEL ON 11 SEPTEMBER 2026**, 884 characters
   * of signed Google storage link behind a `target="_blank"` anchor. */
  check('and so is the one his own Meesho panel really hands over',
    aFileReallyComesFrom('https://storage.googleapis.com/x?y=1'));
  check('and a Flipkart one is reached by its own name, not by the Meesho one',
    aFileReallyComesFrom('https://seller-api.flipkart.com/a/b.csv'));
  /* **THE LISTING FILE, MEASURED ON HIS OWN PANEL 2026-09-14** -- opened with
   * `window.open(..., "_blank")`, which Chrome blocked while nothing took it. */
  check('AND FLIPKART\'S LISTING FILE, BY ITS OWN PATH, IS BELIEVED',
    saying('https://seller.flipkart.com/napi/listing/stockFileDownload?requestId=ab&fileName=S_listing.xls')
      !== null);
  check('while the portal\'s other addresses on the same name are still refused',
    saying('https://seller.flipkart.com/napi/riddler/fetchAssignedQuestionsCount?x=1') === null);

  /* **THE FORGERY THIS ONE STOPS.** Right page, right secret shape, right
   * everything -- and an address belonging to whoever wrote the advert. */
  check('AN ADDRESS THE PAGE CHOSE FOR ITSELF IS REFUSED, secret or no secret',
    saying('https://an-advert.example.com/whatever.xlsx') === null);
  check('and so is one on the portal own name, which is not where files come from',
    saying('https://supplier.meesho.com/panel/v3/new/services/x/inventory') === null);
  /* **AND NOT OVER A PLAIN CONNECTION.** A report fetched over `http:` can be
   * replaced in flight by anything between here and there. */
  check('and so is the same address without the secure connection',
    saying('http://storage.googleapis.com/x?y=1') === null);
  check('and so is one that is not an address at all',
    saying('') === null && saying('javascript:alert(1)') === null);
  /* **AND THE WORD IS NOT ENOUGH -- IT HAS TO BE THE HOST.** Otherwise anybody
   * can put it in their own path. This is written down as a known limit rather
   * than claimed as closed: the list matches anywhere in the address, which is
   * the reference's own rule, and a host that ENDS in one of these names is what
   * it really means. */
  check('a file that merely mentions the name in its path is still taken -- a known limit',
    saying('https://somewhere.example.com/storage.googleapis.com/x') !== null);

  /* **AND A FILE STILL CROSSES AS A FILE**, untouched by any of this. */
  check('and a message carrying a file rather than an address is unaffected',
    theCatcherSaid(genuine, 'the-secret') !== null);
}

{
  /* ---- A LINK THAT IS NOT ON THE LIST (HIS RULING, 2026-09-14)
   *
   * **HIS QUESTION:** what happens when a real report link is not on the list?
   * Named when it is let go, and -- on the platform's own site only -- taken and
   * kept only if the bytes really open as a spreadsheet. */
  const bytesOf = (...numbers) => new Uint8Array(numbers);
  const textOf = (text) => new TextEncoder().encode(text);
  check('AN .xlsx (A ZIP) OPENS AS A SPREADSHEET', looksLikeASpreadsheet(bytesOf(0x50, 0x4b, 0x03, 0x04, 1, 2)));
  check('and so does an old .xls', looksLikeASpreadsheet(bytesOf(0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1)));
  check('and so does a CSV', looksLikeASpreadsheet(textOf('Order ID,SKU,Quantity\nOD1,DJ-5,1\n')));
  check('A WEB PAGE DOES NOT, whatever the server called it',
    !looksLikeASpreadsheet(textOf('<!doctype html><html><body>Sign in</body></html>')));
  check('nor does plain text with no columns', !looksLikeASpreadsheet(textOf('hello\nworld\n')));
  check('nor does nothing at all', !looksLikeASpreadsheet(new Uint8Array(0)) && !looksLikeASpreadsheet(null));

  const flipkartPage = 'https://seller.flipkart.com/index.html#dashboard/listings-management';
  check('A LINK ON FLIPKART\'S OWN SITE, ASKED FROM A FLIPKART PAGE, IS ON THE PLATFORM\'S OWN SITE',
    onThePlatformsOwnSite('https://seller.flipkart.com/napi/listing/somethingNew?x=1', flipkartPage));
  check('but not when the page asking is Meesho\'s',
    !onThePlatformsOwnSite('https://seller.flipkart.com/napi/x', 'https://supplier.meesho.com/panel/v3/new/'));
  check('and never another site, whatever page asks',
    !onThePlatformsOwnSite('https://files.example.com/report.xls', flipkartPage));
  check('and never over a plain connection',
    !onThePlatformsOwnSite('http://seller.flipkart.com/napi/x', 'http://seller.flipkart.com/index.html'));

  const theSameWindow = {};
  const asTheCatcherSaysIt = (address, origin) => theCatcherSaid({
    source: theSameWindow, currentTarget: theSameWindow, origin,
    data: { kartaan: CAUGHT_A_FILE, secret: 's', address },
  }, 's');
  const unlisted = asTheCatcherSaysIt('https://seller.flipkart.com/napi/listing/somethingNew', 'https://seller.flipkart.com');
  check('A NEW LINK ON THE SAME SITE IS BELIEVED ONLY AS SOMETHING STILL TO BE PROVED A SPREADSHEET',
    unlisted !== null && unlisted.mustBeASpreadsheet === true);
  check('while a new link on another site is still refused outright',
    asTheCatcherSaysIt('https://files.example.com/report.xls', 'https://seller.flipkart.com') === null);
  const listed = asTheCatcherSaysIt('https://storage.googleapis.com/x.xlsx', 'https://supplier.meesho.com');
  check('and a link on the list is believed as before, with nothing added to prove',
    listed !== null && listed.mustBeASpreadsheet === undefined);

  check('NOTHING LET GO SAYS NOTHING', whatThePageTriedToOpen([]) === '' && whatThePageTriedToOpen(null) === '');
  const named = whatThePageTriedToOpen(['https://files.example.com/report.xls?token=the-key', 'not an address']);
  check('A LINK LET GO IS NAMED IN A FAILURE -- WITHOUT THE KEY AFTER THE ?',
    named.includes('https://files.example.com/report.xls') && !named.includes('the-key'));
  const { readFileSync: readIt } = await import('node:fs');
  check('and the catcher spells "a link it did not take" exactly as this file does',
    readIt(new URL('./catch-blob.js', import.meta.url), 'utf8').includes(`'${DECLINED_A_LINK}'`));
}


/* ------------- a page whose extension was reloaded under it (11 Sep 2026) */

/* **TWICE IN ONE DAY A DEAD PAGE WAS READ AS AN EMPTY RECORD.** The swallow in
 * `content.js` answered `null` to both the ordinary torn-down-mid-sentence case
 * and the permanent one, and `null` reads as "asked, and there was nothing
 * there". These two are the whole of the difference. */
{
  const gone = theExtensionIsGone({});
  check('a page whose extension is gone is answered, not given nothing',
    gone !== null && gone.extensionWasReloaded === true
      && /reload the page/i.test(gone.wrong));

  check('and an ordinary failure with the extension still there is still swallowed',
    theExtensionIsGone({ id: 'aaaabbbbccccddddeeeeffffgggghhhh' }) === null);
}


/* ------------- a thing drawn rather than pressed, and the press that walks up */

{
  /* **HIS OWN ADS REPORT, 2026-09-14: `found[0].click is not a function`.** A
   * calendar's month arrow is drawn as a picture, and the innermost thing
   * carrying it is an `<svg>`. **`click()` is a method of HTML elements and an
   * SVG element has none**, so pressing the innermost thing threw a JavaScript
   * error -- and what reached the seller was a sentence about a function, naming
   * no report, no page and no control.
   *
   * **WALKING UP IS WHAT A PERSON'S CLICK DOES.** A picture inside a button is
   * not the button. */
  const page = aPage();
  const door = doorOn();
  const pressed = [];
  const button = thing('button');
  const picture = thing('svg', 'Submit');
  picture.style.cursor = 'pointer';
  delete picture.click;
  Object.defineProperty(picture, 'click', { value: undefined, configurable: true });
  button.click = () => pressed.push('the button');
  button.append(picture);
  page.body.append(button);

  check('a picture with the words on it is what the innermost rule finds',
    (await door.find(BY_PRESSABLE_TEXT, 'Submit')) === 1);
  door.click(BY_PRESSABLE_TEXT, 'Submit');
  check('and the press goes to the button around it, not to the picture',
    pressed.length === 1 && pressed[0] === 'the button');
}

{
  /* **AND WHEN NOTHING AROUND IT CAN BE PRESSED, IT SAYS SO NAMING THE TAG**
   * rather than throwing a language error at a seller. */
  const page = aPage();
  const door = doorOn();
  const picture = thing('svg', 'Submit');
  picture.style.cursor = 'pointer';
  Object.defineProperty(picture, 'click', { value: undefined, configurable: true });
  Object.defineProperty(page.body, 'click', { value: undefined, configurable: true });
  page.body.append(picture);
  let said = '';
  try { door.click(BY_PRESSABLE_TEXT, 'Submit'); } catch (wrong) { said = wrong.message; }
  check('nothing pressable anywhere is a sentence, not a crash about a function',
    said.includes('drawn rather than pressed') && said.includes('<svg>'));
  check('and it never says anything about a function',
    !said.includes('is not a function'));
}


/* ------------ an ambiguous refusal names where each match sits (A58) */

{
  /* **HIS OWN ADS FSN REPORT, 2026-09-14.** It refused saying *"2 things match
   * Consolidated FSN Report"* -- and by hand, on the same page, there was one.
   * The page the walk kept did not contain the words at all, so a count and
   * nothing else could only be answered by guessing. **The refusal now carries
   * the shape of each match, and nothing of the page's own words.** */
  const page = aPage();
  const door = doorOn();
  const list = thing('div', '', { attrs: { id: 'popover-content' } });
  const option = thing('div', 'Consolidated FSN Report');
  option.style.cursor = 'pointer';
  list.append(option);
  const shown = thing('div', '', { attrs: { role: 'status' } });
  const echo = thing('span', 'Consolidated FSN Report');
  echo.style.cursor = 'pointer';
  shown.append(echo);
  page.body.append(list, shown);
  let said = '';
  try { door.click(BY_PRESSABLE_TEXT, 'Consolidated FSN Report'); } catch (wrong) { said = wrong.message; }
  check('an ambiguous refusal still says how many matched',
    said.includes('2 things on the page match'));
  check('and names where each one sits, so the next run is a measurement',
    said.includes('#popover-content') && said.includes('role=status'));
}

{
  /* ---- BANNERS AND POP-UPS (HIS RULING, 2026-09-14)
   *
   * **HIS WORDS:** banners "come and go very frequently. So your code has to be
   * that fast." A red banner on his returns page was gone before anybody read
   * it. Banners are kept by their words the moment they are drawn; pop-ups are
   * shut by a control that says it closes something, never in the top bar. */
  const alert = thing('div', 'Report is requested successfully.', { attrs: { role: 'alert' }, box: BIG });
  check('A BANNER THAT SAYS IT IS AN ALERT IS READ',
    whatABannerSays(alert) === 'Report is requested successfully.');
  const toast = thing('div', 'Report has already been requested',
    { className: 'styles__Toast-sc-1 red', box: BIG });
  check('and so is one named like a toast, however the page styles it',
    whatABannerSays(toast) === 'Report has already been requested');
  check('while an ordinary piece of the page is not a banner',
    whatABannerSays(thing('div', 'Date of Closure', { box: BIG })) === '');
  const topBar = thing('header', '', { box: BIG });
  const bell = thing('div', '3 new notifications', { className: 'notification-count', box: BIG });
  topBar.append(bell);
  check('and nothing in the top bar counts, though its bell is named like one',
    whatABannerSays(bell) === '');

  const recorder = aBannerRecorder({ now: () => 7 });
  const page = aPage();
  const holder = thing('div', '', { box: BIG });
  const flash = thing('div', 'Something went wrong. Please try again', { attrs: { role: 'status' }, box: BIG });
  holder.append(flash);
  page.body.append(holder);
  recorder.look(holder);
  flash.remove();
  check('A BANNER THAT CAME AND WENT AT ONCE IS STILL KEPT, WORDS ONLY',
    recorder.seen().length === 1 && recorder.seen()[0].words === 'Something went wrong. Please try again');
  recorder.look(flash);
  check('and the same banner seen twice in a row is kept once', recorder.seen().length === 1);

  const withAPopUp = aPage();
  const door = doorOn();
  const bar = thing('header', '', { box: BIG });
  const barClose = thing('button', '', { attrs: { 'aria-label': 'Close' }, box: BIG });
  bar.append(barClose);
  const dialog = thing('div', '', { attrs: { role: 'dialog' }, box: BIG });
  const dialogClose = thing('button', '', { attrs: { 'aria-label': 'Close' }, box: BIG });
  dialog.append(dialogClose);
  withAPopUp.body.append(bar, dialog);
  const pressedWhich = [];
  barClose.addEventListener('click', () => pressedWhich.push('top bar'));
  dialogClose.addEventListener('click', () => { pressedWhich.push('dialog'); dialog.remove(); });
  const closed = door.close_pop_ups();
  check('A POP-UP\'S OWN CLOSE BUTTON IS PRESSED BEFORE THE FIRST STEP', pressedWhich.includes('dialog'));
  check('BUT NOTHING IN THE TOP BAR IS EVER PRESSED', !pressedWhich.includes('top bar'));
  check('and it says what it closed', closed.length === 1);

  const nothingToClose = aPage();
  const quietDoor = doorOn();
  const okButton = thing('button', 'OK', { box: BIG });
  let okPressed = false;
  okButton.addEventListener('click', () => { okPressed = true; });
  nothingToClose.body.append(okButton);
  check('and a button that merely says "OK" is never pressed',
    quietDoor.close_pop_ups().length === 0 && !okPressed);

  /* **MEASURED ON HIS OWN MEESHO PANEL, 2026-09-16.** The promotion that stopped
   * `me_views` is laid over the whole window and its only way out is a picture of
   * a cross: an `<img src=".../cross-grey.svg">` with no label, no role and no
   * pointer cursor. Every rule here asked the page to SAY it closed something. */
  const withACross = aPage();
  const crossDoor = doorOn();
  const promo = thing('div', '', { className: 'fixed inset-0 z-modal', box: BIG });
  const cross = thing('img', '', { attrs: { src: 'https://x.com/merlin/lined/cross-grey.svg' }, box: BIG });
  const takePart = thing('button', 'Participate Now', { box: BIG });
  promo.append(cross, takePart);
  withACross.body.append(promo);
  let crossPressed = false;
  let tookPart = false;
  cross.addEventListener('click', () => { crossPressed = true; promo.remove(); });
  takePart.addEventListener('click', () => { tookPart = true; });
  const shut = crossDoor.close_pop_ups();
  check('A PROMOTION WHOSE ONLY WAY OUT IS A PICTURE OF A CROSS IS SHUT',
    crossPressed && shut.length === 1);
  check('and nothing that would join the promotion is ever pressed', !tookPart);

  /* The reference's own text route (`content/meesho.js:301`), and the reason it
   * is kept inside an overlay: a bare "x" on a portal page could be anything. */
  const withWords = aPage();
  const wordDoor = doorOn();
  const sheet = thing('div', '', { attrs: { role: 'dialog' }, box: BIG });
  const later = thing('span', 'Maybe later', { box: BIG });
  sheet.append(later);
  const looseX = thing('span', 'x', { box: BIG });
  withWords.body.append(sheet, looseX);
  let saidLater = false;
  let looseXPressed = false;
  later.addEventListener('click', () => { saidLater = true; sheet.remove(); });
  looseX.addEventListener('click', () => { looseXPressed = true; });
  const byWords = wordDoor.close_pop_ups();
  check('a way out named in words inside an overlay is pressed',
    saidLater && byWords.length === 1);
  check('and the same word loose on the page is left alone', !looseXPressed);
}

{
  /* **THE PASSWORD BOX IS CLICKED FIRST, THEN LOG IN -- HIS RULING, 2026-09-16.**
   * *"Try to click on the password box; if a password is saved it will pop up,
   * and then click the login button. If able to login continue with the job,
   * else send notification and wait for resume."* Chrome offers a saved password
   * on the box it belongs to, so clicking the email box first fills the address,
   * leaves the password empty, and presses Log in on a form that cannot pass. */
  const loginPage = aPage();
  const door = doorOn();
  const form = thing('form', '', { box: BIG });
  const email = thing('input', '', { type: 'text', box: BIG });
  const password = thing('input', '', { type: 'password', box: BIG });
  const logIn = thing('button', 'Log in', { box: BIG });
  form.append(email, password, logIn);
  loginPage.body.append(form);
  const order = [];
  email.addEventListener('click', () => order.push('email box'));
  password.addEventListener('click', () => order.push('password box'));
  logIn.addEventListener('click', () => {
    order.push('Log in');
    /* What a saved password getting through looks like: the wall is gone. */
    password.remove();
  });
  check('the page counts as asking to be signed in to', door.needs_signing_in() === true);
  const signedIn = await door.try_signing_in();
  check('THE PASSWORD BOX IS PRESSED FIRST, AND THE EMAIL BOX IS NOT',
    order[0] === 'password box' && !order.includes('email box'));
  check('and the Log in button is pressed after it', order[1] === 'Log in');
  check('and a sign-in that got through is answered as signed in, so the job carries on',
    signedIn === true && door.needs_signing_in() === false);

  /* Still walled: it answers no, and the walk pauses and asks the seller. */
  const stillOut = aPage();
  const shutDoor = doorOn();
  const shutForm = thing('form', '', { box: BIG });
  shutForm.append(thing('input', '', { type: 'password', box: BIG }),
    thing('button', 'Log in', { box: BIG }));
  stillOut.body.append(shutForm);
  check('a sign-in that did not get through is answered as still signed out',
    (await shutDoor.try_signing_in()) === false);
}

const EXPECTED = 309;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
