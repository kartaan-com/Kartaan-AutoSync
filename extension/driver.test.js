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
  BY_PRESSABLE_TEXT, BY_ROLE_AND_TEXT, BY_TEST_ID, BY_TEXT, CAUGHT_A_FILE, THE_CALLS,
  pageDoor, theCatcherSaid,
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
  check('the door answers exactly the ten calls the Python side makes',
    JSON.stringify(Object.keys(door).sort()) === JSON.stringify([...THE_CALLS].sort()));
  check('and there are ten of them', THE_CALLS.length === 10);
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
                     'completed_delivered_last_2_week')) === 3);
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
}

const EXPECTED = 158;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
