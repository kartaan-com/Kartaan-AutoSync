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
import {
  NeedsSigningIn, LANDED, FAILED, STILL_WAITING, hasNotFinished, theFileName, theWalk,
  whyStepIsRefused,
} from './walk.js';

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

/* --------------- what a walk landing somewhere unexpected runs into (D200) */

{
  /* **EVERY `go` IS FOLLOWED BY SOMETHING THAT LOOKS BEFORE IT TOUCHES
   * ANYTHING, and that is what protects a walk that lands in the wrong place.**
   * A walk now resumes on whatever page Chrome drew, and Chrome may have drawn
   * something nobody expected -- a redirect, an interstitial, a promotion, the
   * platform's own error page. The step after a `go` is the guard: a `wait-for`
   * looks and does not click, so a page that is not the one asked for fails by
   * name, with four hundred characters of what was really there, instead of the
   * step after it clicking blind on a stranger's page.
   *
   * **THE REFERENCE GUARDS THE SAME THING WITH `isOnTargetPage`**, asked before
   * it navigates and again when the reloaded page picks the job back up. Here
   * the recipe carries the guard, which is better: it is data, and it says what
   * being in the right place looks like for that one page. */
  const unguarded = [];
  for (const [name, recipe] of Object.entries(BOOK.recipes)) {
    for (const which of ['toAsk', 'toTake']) {
      const steps = recipe[which] || [];
      steps.forEach((one, at) => {
        if (one.do !== 'go') return;
        const next = steps[at + 1];
        if (!next || next.do !== 'wait-for') unguarded.push(`${name}.${which}[${at}]`);
      });
    }
  }
  check(`every go is followed by something that looks before anything is touched -- ${unguarded}`,
    unguarded.length === 0);
}

{
  /* **AND THE ONE THAT WOULD HAVE STALLED SILENTLY FOR EVER.** Every Flipkart
   * address is `index.html#something`: the page never changes, only the part
   * after the `#`. Telling a tab to go between two of those does not reload
   * anything, so the content script is never put in again and nothing ever asks
   * where the walk was. `doors.js` forces a real load for exactly this, and this
   * pins the fact it is forced for -- if Flipkart ever moves off hash addresses,
   * this check is where somebody finds out. */
  const flipkartGos = Object.values(BOOK.recipes)
    .flatMap((r) => [...(r.toAsk || []), ...(r.toTake || [])])
    .filter((one) => one.do === 'go' && String(one.address).includes('seller.flipkart.com'));
  check('every Flipkart page is reached by an address that differs only after the #',
    flipkartGos.length > 0
    && flipkartGos.every((one) => String(one.address).split('#')[0]
      === 'https://seller.flipkart.com/index.html'));
}

/* --------------------------------- and one of them is really driven */

function aPortal(how = {}) {
  const it = {
    went: [], clicked: [], ranges: [], tookFile: 0, handedOver: [], turns: 0, putAway: [],
  };
  /* **WHERE THE BYTES GO.** Recorded rather than answered "yes": a stand-in that
   * agreed would leave every recipe below looking perfectly walked with the file
   * on the floor, which is the state this whole wiring closes. */
  it.putTheFile = async ({ reportId, fileName, body }) => {
    it.putAway.push({ reportId, fileName, size: body ? body.length : 0 });
    return { put: 'an-id' };
  };
  it.door = {
    async go(address, patience, nextAt) { it.went.push(address); it.handedOver.push(nextAt); },
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

/**
 * Walk a REAL recipe the way the extension really walks one: in TURNS.
 *
 * **THESE ARE HIS OWN RECIPES, AND THEY ARE WHY THIS MATTERS MOST HERE (D200).**
 * Going somewhere destroys the page the walk is running in, so a walk hands back
 * "carrying on, from step N" and the page Chrome draws next starts again at N.
 * **Every one of the seventeen real recipes begins with a `go`, and `me_orders`
 * has a second one half way through** -- so a harness that called the walk once
 * was testing something the product cannot do, on every single recipe.
 */
function aWalk(portal) {
  return async (reportId, day, rest = {}) => {
    let startAt = 0;
    for (let turn = 0; turn < 40; turn += 1) {
      portal.turns += 1;
      /* Built again every turn, exactly as the page half is: nothing a previous
       * page held survives into the next one. */
      const walking = theWalk({
        door: portal.door, book: BOOK, say: () => {}, putTheFile: portal.putTheFile,
      });
      // eslint-disable-next-line no-await-in-loop
      const answer = await walking(reportId, day, { panel: PANEL, startAt, ...rest });
      if (!hasNotFinished(answer)) return answer;
      startAt = answer.at;
    }
    throw new Error(`${reportId} kept carrying on and never finished`);
  };
}

{
  const portal = aPortal();
  const got = await aWalk(portal)('me_orders', DAY);
  check('his real Meesho orders recipe walks all the way through', got.state === LANDED);
  /* **AND IT REALLY DID SPAN THREE PAGES.** His orders recipe goes to the orders
   * page, asks for the export, and goes back to that same address to collect it.
   * A walk that survived only its first teardown would land every other report
   * and die on this one -- at night, on the report that matters most. */
  check('and it really did take three pages, because that recipe goes somewhere twice',
    portal.turns === 3 && portal.went.length === 2);
  check('and the place was handed over at each teardown',
    portal.handedOver.length === 2 && portal.handedOver.every((one) => Number.isInteger(one)));
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
  const asked = await aWalk(portal)('fk_orders', DAY, { panel: '' });
  check('and asking for it is a success rather than a failure', asked.state === STILL_WAITING);
  check('with the range ending on the day being fetched',
    portal.ranges[0][0] === '2026-08-25' && portal.ranges[0][1] === DAY);
  check('a Flipkart report needs no panel name at all', asked.state !== FAILED);
}

{
  /* **WHILE MEESHO STILL DOES.** A requirement of one platform must not be
   * dropped for the other. */
  const walking = theWalk({
    door: aPortal().door, book: BOOK, say: () => {}, putTheFile: async () => ({}),
  });
  const got = await walking('me_orders', DAY, { panel: '' });
  check('a Meesho report with no panel name refuses', got.state === FAILED);
  check('and says the panel name is the seller\'s own data',
    got.say.includes("seller's own data"));
}

{
  /* The failure sentences really reach the walk, rather than being invented. */
  const portal = aPortal({ matches: { 'Download Orders Data': 0 } });
  const got = await aWalk(portal)('me_orders', DAY);
  check('a missing button uses the words from the recipe file',
    got.say.includes(BOOK.whatItMeans['found-nothing']));
  check('and names the thing in the words a person reads',
    got.say.includes('the download menu'));
}

{
  const portal = aPortal({ signedOut: true });
  let itsOwnKind = false;
  try {
    await aWalk(portal)('me_orders', DAY);
  } catch (wrong) {
    itsOwnKind = wrong instanceof NeedsSigningIn;
  }
  check('being signed out is still its own kind of problem on a real recipe',
    itsOwnKind === true);
}

/* ------------------------- HIS REAL RECIPE FILE NAMES EVERY FILE IT COULD FETCH
 *
 * **A RECIPE THE BOOK CAN WALK AND CANNOT NAME IS A REPORT THAT REACHES THE
 * SELLER'S DRIVE AND CAN NEVER BE READ BACK OUT OF IT.** `landing.data_date_in`
 * takes the day out of the NAME and `reading.a_reading` refuses a file that has
 * none -- so the folder fills up while the ledger stays empty and nothing
 * anywhere says why. This asks it of the REAL generated file, not a fixture.
 */
{
  const walkable = Object.keys(BOOK.recipes).sort();
  const named = Object.keys(BOOK.fileNames || {}).sort();
  check('EVERY RECIPE THE EXTENSION CAN WALK HAS A FILE NAME TO PUT IT AWAY UNDER',
    walkable.length > 0 && walkable.join(',') === named.join(','));
  check('and every one of them names a platform and a file type, never a blank',
    walkable.every((one) => BOOK.fileNames[one].platform && BOOK.fileNames[one].extension));
  /* **THE SHAPE IS THE PYTHON'S** -- `<platform>_<report id>_<data date>.<ext>`
   * -- and `tools/export_recipes_checks.py` is what holds it to
   * `landing.file_name_for` itself, report by report, in the language that owns
   * the rule. This one only asks that the walk really builds that shape. */
  check('and the name the walk builds is the shape the nightly run reads a day out of',
    theFileName(BOOK, 'me_orders', DAY) === `meesho_me_orders_${DAY}.csv`
    && theFileName(BOOK, 'fk_orders', DAY) === `flipkart_fk_orders_${DAY}.xlsx`);
}

{
  /* **AND HIS REAL `me_orders` RECIPE REALLY PUTS ITS FILE SOMEWHERE.** This is
   * the report that has actually run against his own Meesho panel. */
  const portal = aPortal();
  const got = await aWalk(portal)('me_orders', DAY);
  check('HIS REAL MEESHO ORDERS RECIPE PUTS THE FILE AWAY, it does not drop it',
    got.state === LANDED && portal.putAway.length === 1
    && portal.putAway[0].fileName === `meesho_me_orders_${DAY}.csv`
    && portal.putAway[0].size === 3);
}

const EXPECTED = 34;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
