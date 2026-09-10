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
check('it carries the recipes', Object.keys(BOOK.recipes).length === 18);
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
    waited: [], clickedAway: 0,
    /* **WHICH ROW EACH LOOKUP WAS NARROWED TO.** A page lists every export ever
     * made, so the recipe names the row by the day -- and until A52 the day was
     * never put in, so the row was named by the characters `{day_in_words}`,
     * which no page carries. Dropped here, that crosses unfilled with nothing
     * anywhere looking wrong. */
    nearAsked: [],
    rowsAsked: [],
    /* **THE MENU, AS MEESHO REALLY BEHAVES.** Its list of finished exports is
     * drawn AS it opens and never again while it is open. So this holds the two
     * facts that follow: whether it is open, and how many times it has been SHUT
     * and opened again. Counting clicks instead would let a loop that never shut
     * it pass. */
    menuOpen: false, shutSinceLastOpened: false, reopened: 0,
    /* **WHAT HAPPENED AND IN WHAT ORDER (A44).** The catcher for a file the page
     * builds inside itself must be armed AFTER the lookup and immediately before
     * the click that builds it -- armed any earlier and it sits armed through the
     * whole of the portal drawing itself, where any script on the page can hand
     * over a file of its own and be caught instead. This is where that is proved
     * against HIS OWN recipes rather than a stand-in book. */
    whatHappened: [],
  };
  it.armTheCatcher = async () => { it.whatHappened.push('armed'); };
  /* **WHERE THE BYTES GO.** Recorded rather than answered "yes": a stand-in that
   * agreed would leave every recipe below looking perfectly walked with the file
   * on the floor, which is the state this whole wiring closes. */
  it.putTheFile = async ({ reportId, fileName, body }) => {
    it.putAway.push({ reportId, fileName, size: body ? body.length : 0 });
    return { put: 'an-id' };
  };
  it.door = {
    async go(address, patience, nextAt) {
      it.went.push(address);
      it.handedOver.push(nextAt);
      /* **GOING SOMEWHERE IS PART OF THE ORDER OF THINGS.** `me_orders` waits for
       * Meesho to finish building the file and only THEN loads the page again --
       * and whether the wait came before or after the load is the whole of it. */
      it.whatHappened.push('went somewhere');
      /* A page that has been loaded again has nothing open on it. */
      it.menuOpen = false;
      it.shutSinceLastOpened = false;
    },
    async needs_signing_in() { return Boolean(how.signedOut); },
    async overlays() { return []; },
    async find(kind, what, exact, patience, near) {
      /* **LOOKING IS PART OF THE ORDER OF THINGS.** The opener is looked up
       * afresh between rounds and pressed only if it is still there, and an
       * order is the only thing that can be checked about a "before". */
      it.whatHappened.push(`found ${what}`);
      it.nearAsked.push(near);
      /* **AND EVERY WAY THE ROW COULD BE NAMED, FLAT.** A lookup is narrowed to
       * several spellings of one day and matches on any of them, so a check
       * asking whether one spelling reached the page needs them apart. */
      it.rowsAsked.push(...(Array.isArray(near) ? near : [near]));
      /* **THE FINISHED FILE IS NOT IN THE LIST YET, and this is the only way to
       * say so.** Meesho draws its list of finished exports as the download menu
       * opens, so the list only ever changes when the menu is shut and opened
       * again. Here the row appears once the menu has been reopened this many
       * times -- and with nothing reopening it, it never appears at all. */
      if (how.appearsAfterReopens !== undefined && what === 'Download' && near) {
        return it.menuOpen && it.reopened >= how.appearsAfterReopens ? 1 : 0;
      }
      /* **A CONTROL THE PORTAL TAKES AWAY PART WAY THROUGH.** Told to, this one
       * takes the opener away the moment the menu is shut -- the one moment in
       * the whole walk when nothing is holding it open. */
      if (how.openerGoesWhenShut && what === 'Download Orders Data' && it.clickedAway) return 0;
      return how.matches && what in how.matches ? how.matches[what] : 1;
    },
    async click(kind, what) {
      /* **A CONTROL THAT IS NOT THERE CANNOT BE CLICKED, AND THE REAL DOOR
       * THROWS.** A stand-in that quietly accepted the click would let a walk
       * which never looked first look exactly like one that did. */
      if (how.openerGoesWhenShut && what === 'Download Orders Data' && it.clickedAway) {
        throw new Error("Nothing on the page matches 'Download Orders Data'.");
      }
      it.clicked.push(what);
      it.whatHappened.push(`clicked ${what}`);
      /* **OPENING A SHUT MENU IS THE ONLY THING THAT REDRAWS ITS LIST.** Pressed
       * while it is already open this counts for nothing at all -- which is
       * exactly what a second press of the opener is worth if Meesho's opener
       * does not toggle. */
      if (!it.menuOpen) {
        it.menuOpen = true;
        if (it.shutSinceLastOpened) { it.reopened += 1; it.shutSinceLastOpened = false; }
      }
    },
    /* **SHUTTING IT IS A CLICK WHERE NOTHING IS**, which is the reference's own
     * gesture (`content/meesho.js:865`, `document.body.click()`). */
    async click_away() {
      it.clickedAway += 1;
      it.whatHappened.push('clicked away');
      it.menuOpen = false;
      it.shutSinceLastOpened = true;
    },
    async pick_range(from, to) { it.ranges.push([from, to]); },
    async take_file() {
      it.tookFile += 1;
      it.whatHappened.push('took the file');
      return new Uint8Array([1, 2, 3]);
    },
    async page_text() { return 'Welcome back'; },
    /* **NOTHING IS REALLY SLEPT FOR, AND THE NUMBER IS KEPT.** A stand-in that
     * really waited thirty-five seconds would put six minutes into this file;
     * one that forgot the number would let a wait of nought seconds pass as a
     * wait of thirty-five. */
    async wait(seconds) { it.waited.push(seconds); it.whatHappened.push(`waited ${seconds}`); },
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
        armTheCatcher: portal.armTheCatcher,
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

  /* **THE THIRTY-FIVE SECONDS, AND WHERE THEY SIT.**
   *
   * Meesho builds the export on its own servers and shows the page nothing at
   * all while it does -- and the list of finished files is drawn AS the page
   * loads. So a page loaded the instant "Export data" is pressed is a page
   * loaded before the file exists, and the file is simply not in its list.
   * **The 300 seconds of patience the last step used to carry could not recover
   * that**: the list was already drawn without it.
   *
   * **THE ORDER IS THE CHECK, not the presence of a wait somewhere.** A wait
   * after the reload would be exactly as useless as no wait at all, and would
   * read in the recipe as though the fault had been fixed. */
  const order = portal.whatHappened.join(' -> ');
  check('his orders recipe waits after asking for the export and before loading the page again',
    order.includes('clicked Export data -> waited 35 -> went somewhere'));
}

{
  /* **THE FILE IS NOT IN THE LIST ON THE FIRST LOOK, WHICH IS THE ORDINARY
   * CASE.** Meesho draws that list as the download menu opens, so an open menu
   * shows what was ready at that moment and never changes -- five minutes of
   * looking at it is five minutes of looking at the same picture. The reference
   * shuts it by clicking where nothing is, leaves it shut thirty seconds, looks
   * the opener up again and presses it once -- six times
   * (`content/meesho.js:860-878`). Until that was carried across, this walk
   * failed: the stand-in below never shows the row to a menu that is not
   * reopened, and nothing reopened it. */
  const portal = aPortal({ appearsAfterReopens: 2 });
  const got = await aWalk(portal)('me_orders', DAY);
  check('a file that is not in the list yet is still fetched, by shutting the menu and opening it again',
    got.state === LANDED && portal.tookFile === 1);
  /* **THE ORDER IS THE CHECK, AND IT IS THE REFERENCE'S ORDER, ALL FOUR PARTS OF
   * IT.** Shut it, wait while it is shut, look the opener up AGAIN, press it
   * once. A round that waited on the OPEN menu, or pressed the opener twice and
   * shut nothing, or pressed at it without looking first, matches none of this.
   * **AND ONE THAT PASSED BY NOTHING HAPPENING CANNOT**: the count has to be the
   * two rounds the stand-in demands before it shows the row at all. */
  const reopened = (portal.whatHappened.join(' -> ').match(
    /clicked away -> waited 30 -> found Download Orders Data -> clicked Download Orders Data/g
  ) || []).length;
  check('and each round was: clicked away, left shut thirty seconds, looked again, opened again',
    reopened === 2);
  /* **AND THE STAND-IN COUNTED THE SHUTTING, NOT THE CLICKING.** Its list only
   * reappears once the menu has genuinely been shut and opened again. */
  check('and the menu really was shut and reopened, not merely pressed at',
    portal.clickedAway === 2 && portal.reopened === 2);
}

{
  /* **AND IT GIVES UP, rather than reopening a menu until the morning.** Six is
   * the reference's own number. A walk that never stopped would hold the night
   * on one report and every report behind it would go unfetched. */
  const portal = aPortal({ appearsAfterReopens: 99 });
  const got = await aWalk(portal)('me_orders', DAY);
  check('a file that never appears is a failure, not a walk that runs all night',
    got.state === 'failed');
  check('and it was tried the six times the reference tries it, no more',
    portal.clickedAway === 6 && portal.waited.filter((one) => one === 30).length === 6);
  /* **THE FAILURE SAYS WHAT IT WAS DOING, NOT ONLY WHAT WAS MISSING.** That is
   * the whole reason a step carries a `why`: "button not found" with nothing
   * beside it cost this project a month. */
  check('and the failure carries the step\'s own reason with it',
    got.say.includes('taking the finished file'));
}

{
  /* **THE OPENER IS LOOKED FOR BEFORE IT IS PRESSED, AND IF IT HAS GONE THIS
   * STOPS** (`content/meesho.js`: `if (!dlDropdown2) ... break`). Without it the
   * click throws straight past every failure this walk writes, and the seller is
   * told a control could not be found with no word of what was being attempted.
   * The stand-in takes the opener away the moment the menu is shut and throws at
   * a click aimed at it, exactly as the real door does. */
  const portal = aPortal({ appearsAfterReopens: 99, openerGoesWhenShut: true });
  const got = await aWalk(portal)('me_orders', DAY);
  check('an opener that has gone ends his orders walk rather than throwing out of it',
    got.state === 'failed');
  check('and it stops at the first round rather than shutting a menu that is not there again',
    portal.clickedAway === 1);
  check('and the failure still carries the step\'s own reason',
    got.say.includes('taking the finished file'));
}

{
  /* **EVERY ONE OF HIS REAL RECIPES ARMS THE CATCHER IMMEDIATELY BEFORE THE
   * CLICK THAT TAKES ITS FILE (A44), AND THAT IS CHECKED AGAINST THE REAL BOOK
   * RATHER THAN A STAND-IN ONE.**
   *
   * **WHY IT MATTERS THAT IT IS EVERY ONE.** The catcher used to be armed once
   * at the start of every walk turn, before the first step ran, and the file is
   * not asked for until the last. In between the portal draws itself -- 10 to 25
   * seconds, measured on his own Flipkart account -- and any script on that page
   * can call `URL.createObjectURL` with a file of its own and be caught instead.
   * Those bytes go on to `land-the-file`, `drive.js` replaces the genuine file of
   * that day under the genuine report name, and the Python reads it into the
   * seller's ledger as real sales.
   *
   * **AND THIS IS WHERE A RECIPE THAT DID NOT FIT WOULD SHOW UP.** Every recipe
   * in the book today takes its file in a step that does its own lookup and its
   * own click. The day somebody writes one whose file arrives from an earlier
   * click, this goes red -- and that recipe needs its own answer, not a wider
   * window for everybody. */
  const armedLate = [];
  for (const reportId of Object.keys(BOOK.recipes)) {
    const portal = aPortal();
    // eslint-disable-next-line no-await-in-loop
    const got = await aWalk(portal)(reportId, DAY, { panel: PANEL, askedAlready: DAY });
    if (got.state !== LANDED) continue;
    const order = portal.whatHappened.join(' -> ');
    const last = order.lastIndexOf('armed');
    const rest = order.slice(last);
    if (!/^armed -> clicked [^>]+ -> took the file$/.test(rest)) armedLate.push(reportId);
  }
  check(`every recipe that lands a file arms the catcher immediately before the click that `
    + `builds it -- ${armedLate.join(', ') || 'none late'}`,
    armedLate.length === 0);
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
    armTheCatcher: async () => {},
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

{
  /* ---------- THE FIVE ROWS NAMED BY THE DAY, ON HIS REAL RECIPES (A52)
   *
   * **THIS IS THE HALF THAT ACTUALLY RUNS ON THE NIGHT.** The wording checks in
   * `walk.test.js` are asked of a stand-in book with invented month names; these
   * are asked of the file that ships, walked by the walk that ships, on the five
   * reports the hole was found in.
   *
   * **A DAY UNDER TEN ON PURPOSE.** The whole of what the two portals disagree
   * about is the leading nought, and on the twenty-sixth of a month they agree --
   * which is why this went unnoticed. The expected words are typed out by hand. */
  const FIFTH_OF_JUNE = '2026-06-05';

  /* **AND THE DAY MEESHO'S ROW IS NAMED BY IS THE DAY THE EXPORT WAS MADE, WHICH
   * IS TODAY (A53).** Its exported-files panel stamps a row with the moment the
   * file was built -- a returns export is always the last two weeks, so there is
   * no data date on the row at all. Filled with the day being fetched, a run on
   * 25 August looked for `24 Aug 2026` on a row reading `25 Aug 2026, 04:49 PM`.
   *
   * **THE EXPECTATION IS ARITHMETIC DONE HERE, not the walk's answer read back.**
   * The month names are the real ones because this is the real book. */
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const now = new Date();
  const todayPlainly = `${now.getDate()} ${MONTHS[now.getMonth()]} ${now.getFullYear()}`;

  const meesho = aPortal();
  await aWalk(meesho)('me_returns', FIFTH_OF_JUNE);
  check('HIS REAL MEESHO RETURNS RECIPE LOOKS FOR THE ROW BY THE DAY IT WAS MADE',
    meesho.rowsAsked.includes(todayPlainly));
  check('and NOT by the day being fetched, which is on no row of that panel',
    !meesho.rowsAsked.includes('5 Jun 2026'));

  const claims = aPortal();
  await aWalk(claims)('me_claims', FIFTH_OF_JUNE);
  check('and so does claims, which has had the same hole since it was written',
    claims.rowsAsked.includes(todayPlainly) && !claims.rowsAsked.includes('5 Jun 2026'));

  /* **AND EVERY WAY MEESHO WRITES IT, NOT ONE.** The working reference builds six
   * spellings and takes a row carrying any of them. */
  check('and every spelling Meesho writes goes with it, plain day included',
    meesho.rowsAsked.includes(
      `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
      + `-${String(now.getDate()).padStart(2, '0')}`));

  /* **FLIPKART'S THREE, COLLECTED RATHER THAN ASKED FOR**, which is the half
   * that names a row -- and it names it by the END of the range, after " To ",
   * which IS the day the data is about. **The other way round from Meesho, and
   * that is the whole of what A53 corrected.** */
  for (const which of ['fk_orders', 'fk_returns', 'fk_payments']) {
    const flipkart = aPortal();
    // eslint-disable-next-line no-await-in-loop
    await aWalk(flipkart)(which, FIFTH_OF_JUNE, { askedAlready: FIFTH_OF_JUNE });
    check(`${which} looks for the row by the day the data is ABOUT`,
      flipkart.rowsAsked.includes('To 05 Jun 2026')
      && !flipkart.rowsAsked.includes(`To ${todayPlainly}`));
    /* **AND IN EVERY SPELLING THE REFERENCE TRIES, month-first included.**
     * Committing to one is what chose, on Flipkart, a spelling the reference's
     * own working matcher excludes. */
    check(`and ${which} tries the reference's month-first spelling too`,
      flipkart.rowsAsked.includes('To Jun 5 2026')
      && flipkart.rowsAsked.includes('To 5 Jun 2026'));
  }

  /* **AND NOTHING ANYWHERE REACHES A PAGE STILL HOLDING A PLACEHOLDER.** That is
   * the whole fault: `{day_in_words}` crossed to the browser as those very
   * characters, and no row of either portal carries them. */
  const stillHolding = [];
  for (const one of Object.keys(BOOK.recipes)) {
    const portal = aPortal();
    // eslint-disable-next-line no-await-in-loop
    await aWalk(portal)(one, FIFTH_OF_JUNE, { askedAlready: FIFTH_OF_JUNE });
    stillHolding.push(...portal.rowsAsked.filter((row) => String(row || '').includes('{')));
  }
  check(`no real recipe reaches the page still holding a placeholder -- ${stillHolding.slice(0, 3)}`,
    stillHolding.length === 0);
}

const EXPECTED = 56;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
