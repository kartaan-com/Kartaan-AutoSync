/* Checks that the generated recipes and the walk actually agree.
 *
 * Run: node extension/recipes.test.js
 *
 * **THIS IS THE JOIN D107 NAMED AS ITS COST.** The steps are decided in Python
 * and walked in JavaScript, and the two halves could drift. Two things stop that,
 * and they stop different things:
 *
 *   - `tools/export_recipes_checks.py` refuses a `recipes.json` that is not what
 *     the Python now says. That catches the file going stale.
 *   - **this catches the other half: a file that IS current and that the walk
 *     cannot actually use.** Every real recipe is put through the walk's own
 *     judgement of what a step may be, and one is driven end to end against a
 *     stand-in portal. A generated file nobody drives is a file that agrees with
 *     the Python and works with nothing.
 *
 * Neither of them is the other's job, and having only one is how a green tick
 * comes to mean less than it looks.
 */

import { readFileSync } from 'node:fs';
import { NeedsSigningIn, LANDED, FAILED, STILL_WAITING, theWalk, whyStepIsRefused } from './walk.js';

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

const HERE = new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const BOOK = JSON.parse(readFileSync(`${HERE}recipes.json`, 'utf8'));

const DAY = '2026-08-26';
const PANEL = 'growth/some-panel';

/* ------------------------------------------------------------ it is there */

check('the recipe file is there and can be read', typeof BOOK === 'object' && BOOK !== null);
check('and it says plainly that it is generated',
  Array.isArray(BOOK._generated) && BOOK._generated.join(' ').includes('DO NOT EDIT'));
check('it carries the recipes', Object.keys(BOOK.recipes).length === 17);
check('and both platforms are in it',
  Object.keys(BOOK.recipes).some((one) => one.startsWith('me_'))
  && Object.keys(BOOK.recipes).some((one) => one.startsWith('fk_')));
check('and the words each failure means', Object.keys(BOOK.whatItMeans).length > 0);

/* --------------------------- every real step is one the walk will accept */

/* **THE WALK'S OWN JUDGEMENT, NOT A SECOND ONE WRITTEN HERE.** A checks file that
 * decided for itself what a good step looks like would be a third record of the
 * same fact, and the one most likely to go quietly out of date. */
{
  const wrong = [];
  for (const [name, recipe] of Object.entries(BOOK.recipes)) {
    for (const step of [...recipe.toAsk, ...recipe.toTake]) {
      const why = whyStepIsRefused(step);
      if (why) wrong.push(`${name}: ${why}`);
    }
  }
  check(`every step of every real recipe is one the walk accepts -- ${wrong.slice(0, 3)}`,
    wrong.length === 0);
}

{
  /* **AND EVERY RECIPE ENDS BY TAKING A FILE, or it can only ever ask.** A
   * one-shot recipe whose last step is not the file is the fault the walk reports
   * as "the recipe is missing its last step" -- better found here than on the
   * night it runs. */
  const missing = Object.entries(BOOK.recipes)
    .filter(([, r]) => !r.toTake.length || r.toTake[r.toTake.length - 1].do !== 'take-file')
    .map(([name]) => name);
  check(`every recipe finishes by taking a file -- ${missing}`, missing.length === 0);

  /* A two-phase recipe says how long the platform takes, because the log says so
   * to whoever reads it. A one-shot one is not built by anybody and says nothing
   * rather than a number nothing reads. */
  const twoPhase = Object.entries(BOOK.recipes).filter(([, r]) => r.toAsk.length);
  check('the two-phase recipes say how long the platform takes',
    twoPhase.length > 0 && twoPhase.every(([, r]) => r.readyInMinutes > 0));
  check('and the one-shot ones say nothing rather than a number nothing reads',
    Object.values(BOOK.recipes).filter((r) => !r.toAsk.length)
      .every((r) => r.readyInMinutes === 0));
}

/* --------------------------------- and one of them is really driven */

function aPortal(how = {}) {
  const it = { went: [], clicked: [], ranges: [], tookFile: 0 };
  it.door = {
    async go(address) { it.went.push(address); },
    async needs_signing_in() { return Boolean(how.signedOut); },
    async overlays() { return []; },
    async find(kind, what) { return how.matches && what in how.matches ? how.matches[what] : 1; },
    async click(kind, what) { it.clicked.push(what); },
    async pick_range(from, to) { it.ranges.push([from, to]); },
    async take_file() { it.tookFile += 1; return new Uint8Array([1, 2, 3]); },
    async page_text() { return 'Welcome back'; },
  };
  return it;
}

{
  const portal = aPortal();
  const walking = theWalk({ door: portal.door, book: BOOK, say: () => {} });
  const got = await walking('me_orders', DAY, { panel: PANEL });
  check('his real Meesho orders recipe walks all the way through', got.state === LANDED);
  /* **THE SELLER'S OWN PANEL IS FILLED IN, and the placeholder is gone.** A
   * placeholder left in the address is a page that does not exist. */
  check('the seller\'s own panel name went into the address',
    portal.went.some((one) => one.includes(PANEL)));
  check('and no placeholder was left in it',
    !portal.went.some((one) => one.includes('{panel}')));
  check('the day being fetched was set', portal.ranges.length === 1 && portal.ranges[0][1] === DAY);
  check('and a file was taken', portal.tookFile === 1);
}

{
  /* **THE LIVE FIX IS REALLY IN THE FILE.** Flipkart replaced "Custom Dates" with
   * a dropdown labelled `Custom`, and that one word is the whole of a 29-day
   * outage. It is matched exactly, because a loose match also hits the "Customer
   * Segments" tab beside it -- the chart-legend trap again. */
  const views = BOOK.recipes.fk_views;
  const custom = [...views.toAsk, ...views.toTake]
    .filter((s) => s.find && s.find.what === 'Custom');
  check('the Flipkart date dropdown is looked for as the one word it now is',
    custom.length > 0);
  check('and matched exactly, so it cannot hit Customer Segments beside it',
    custom.every((s) => s.find.exact === true));
  check('and the words that no longer exist on that page are gone from the file',
    !JSON.stringify(BOOK).includes('Custom Dates'));
}

{
  /* Flipkart's Reports Centre refuses a single-day range with a Submit that does
   * nothing at all, and names the row it produces by the END date. */
  const asking = BOOK.recipes.fk_orders.toAsk.filter((s) => s.do === 'pick-range');
  check('the Flipkart reports centre asks for the two-day range it insists on',
    asking.length === 1 && asking[0].rangeDays === 2);

  const portal = aPortal();
  const walking = theWalk({ door: portal.door, book: BOOK, say: () => {} });
  const asked = await walking('fk_orders', DAY, { panel: '' });
  check('and asking for it is a success rather than a failure', asked.state === STILL_WAITING);
  check('with the range ending on the day being fetched',
    portal.ranges[0][0] === '2026-08-25' && portal.ranges[0][1] === DAY);
  check('a Flipkart report needs no panel name at all', asked.state !== FAILED);
}

{
  /* **WHILE MEESHO STILL DOES.** A requirement of one platform must not be
   * dropped for the other. */
  const walking = theWalk({ door: aPortal().door, book: BOOK, say: () => {} });
  const got = await walking('me_orders', DAY, { panel: '' });
  check('a Meesho report with no panel name refuses', got.state === FAILED);
  check('and says the panel name is the seller\'s own data',
    got.say.includes("seller's own data"));
}

{
  /* The failure sentences really reach the walk, rather than being invented. */
  const portal = aPortal({ matches: { 'Download Orders Data': 0 } });
  const walking = theWalk({ door: portal.door, book: BOOK, say: () => {} });
  const got = await walking('me_orders', DAY, { panel: PANEL });
  check('a missing button uses the words from the recipe file',
    got.say.includes(BOOK.whatItMeans['found-nothing']));
  check('and names the thing in the words a person reads',
    got.say.includes('the download menu'));
}

{
  const portal = aPortal({ signedOut: true });
  const walking = theWalk({ door: portal.door, book: BOOK, say: () => {} });
  let itsOwnKind = false;
  try {
    await walking('me_orders', DAY, { panel: PANEL });
  } catch (wrong) {
    itsOwnKind = wrong instanceof NeedsSigningIn;
  }
  check('being signed out is still its own kind of problem on a real recipe',
    itsOwnKind === true);
}

const EXPECTED = 26;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
