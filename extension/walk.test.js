/* Checks for the walk.
 *
 * Run: node extension/walk.test.js
 *
 * **A FAKE MEESHO, DELIBERATELY AWKWARD.** It covers itself with a promotion the
 * way the real one does, it offers two things of the same name the way the
 * payments page does, and it hands back nothing when a file is built inside the
 * page. A stand-in kinder than the real thing is this project's most expensive
 * recurring fault -- four times over -- so this one is written to be nasty.
 *
 * **AND THE MOST IMPORTANT CHECK IS THAT THIS ANSWERS WHAT THE PYTHON DOOR
 * ANSWERS.** D107 moved the walking into JavaScript and named the cost out loud:
 * two descriptions of one walk, and nothing mechanical comparing them. These are
 * the same cases the Python's own checks make, deliberately -- so the two can be
 * read side by side by a person and seen to agree.
 */

import {
  BUILT_IN_THE_PAGE,
  COVERED_UP,
  FAILED,
  FOUND_NOTHING,
  FOUND_SEVERAL,
  LANDED,
  NOTHING_TO_FETCH,
  NeedsSigningIn,
  STILL_WAITING,
  capture,
  hasNotFinished,
  looksLikeAPage,
  daysBefore,
  theFileName,
  theWalk,
  TOO_BIG_TO_CARRY,
  whyTheDayIsRefused,
  whatIsCovering,
  whyStepIsRefused,
} from './walk.js';
import { TOO_BIG } from './catch-blob.js';

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

const DAY = '2026-08-26';
const PANEL = 'growth/some-panel';

/* **A RUN THAT ENDS BY THROWING IS NOT A CHECK GOING RED**, and this file is
 * where that lesson was learnt in Python the same day: sixty-one deliberate
 * breakages of `browser_door.py` were "noticed" only by its checks file falling
 * over. Same cure here. */
const THREW = [];
const NOTHING = { state: 'it threw instead of answering', reportId: '', say: '', pageWas: '' };

const SAID = [];

/* ------------------------------------------------------ the book, as data */

const step = (one) => ({ patience: 30, why: 'doing a thing', ...one });
const find = (what, rest = {}) => ({ how: 'role', what, exact: true, ...rest });

const BOOK = {
  recipes: {
    me_orders: {
      readyInMinutes: 0,
      toAsk: [],
      toTake: [
        step({ do: 'go', address: 'https://supplier.example.invalid/panel/{panel}/orders',
          why: 'opening the orders page' }),
        step({ do: 'wait-for', find: find('Download Orders Data', { called: 'the download menu' }),
          patience: 45, why: 'waiting for the orders page to finish drawing' }),
        step({ do: 'click', find: find('Download Orders Data', { called: 'the download menu' }),
          why: 'opening the download menu' }),
        step({ do: 'pick-range', patience: 20, why: 'setting the day to export' }),
        step({ do: 'click', find: find('Export data'), why: 'asking for the export' }),
        step({ do: 'take-file', find: find('Download'), patience: 300,
          why: 'taking the finished file' }),
      ],
    },
    /* **TWO PAGES, WHICH IS THE SHAPE THE REAL `me_orders` HAS.** Its take list
     * goes to the orders page, asks for the export, and then GOES BACK to the
     * same address to collect it -- so a real walk of it spans three pages and
     * two teardowns. Nothing in this file could see that before D200, because
     * the harness walked a recipe in one go and the product cannot. */
    me_two_pages: {
      readyInMinutes: 0,
      toAsk: [],
      toTake: [
        step({ do: 'go', address: 'https://supplier.example.invalid/panel/{panel}/orders',
          why: 'opening the orders page' }),
        step({ do: 'wait-for', find: find('Download Orders Data'), why: 'waiting for it to draw' }),
        step({ do: 'click', find: find('Export data'), why: 'asking for the export' }),
        step({ do: 'go', address: 'https://supplier.example.invalid/panel/{panel}/orders',
          patience: 60, why: 'going back for the finished file' }),
        step({ do: 'wait-for', find: find('Download'), why: 'waiting for the file to be offered' }),
        step({ do: 'take-file', find: find('Download'), patience: 300, why: 'taking it' }),
      ],
    },
    /* **A DAY AND A PANEL NAMED TWICE IN ONE ADDRESS (cycle 46, R6#15).** No
     * real recipe does this today; nothing stopped one, and a recipe is DATA --
     * added without touching walk.js, by whoever is fixing a platform at the
     * time. Filling by name replaces the first one only, so the second would go
     * out as the word {day}, on the platform, at night, with nobody watching. */
    me_twice_over: {
      readyInMinutes: 0,
      toAsk: [],
      toTake: [
        step({ do: 'go',
          address: 'https://supplier.example.invalid/panel/{panel}/o/{panel}?from={day}&to={day}',
          why: 'opening a page that names the day and the panel twice each' }),
        step({ do: 'take-file', find: find('Download'), patience: 60, why: 'taking the file' }),
      ],
    },
    /* A RECIPE THAT NAMES THE DAY IN WORDS. His returns page reads `25 Aug
     * 2026`, and no two platforms write it the same way. */
    me_in_words: {
      readyInMinutes: 0,
      toAsk: [],
      toTake: [
        step({ do: 'go', address: 'https://supplier.example.invalid/panel/{panel}/r/{day_in_words}',
          why: 'opening a page named by the day in words' }),
        step({ do: 'take-file', find: find('Download'), patience: 60, why: 'taking the file' }),
      ],
    },
    me_catalog: {
      readyInMinutes: 0,
      toAsk: [],
      toTake: [
        step({ do: 'go', address: 'https://supplier.example.invalid/panel/{panel}/inventory',
          why: 'opening the inventory page' }),
        step({ do: 'wait-for', find: find('Bulk Stock Update', { called: 'the bulk stock button' }),
          patience: 45, why: 'waiting for the inventory page to finish drawing' }),
        step({ do: 'click', find: find('Bulk Stock Update', { called: 'the bulk stock button' }),
          why: 'opening the bulk stock panel' }),
        step({ do: 'take-file', find: find('Download'), patience: 60, why: 'taking the stock file' }),
      ],
    },
    fk_orders: {
      readyInMinutes: 30,
      toAsk: [
        step({ do: 'go', address: 'https://seller.example.invalid/report-centre',
          why: 'opening the reports centre' }),
        step({ do: 'pick-range', rangeDays: 2, switchedOffDaysChangeTheCursor: true,
          why: "setting the two-day range Flipkart insists on" }),
        step({ do: 'click', find: find('Submit'), why: 'submitting the request' }),
      ],
      toTake: [
        step({ do: 'go', address: 'https://seller.example.invalid/report-centre',
          why: 'coming back for orders' }),
        step({ do: 'take-file', find: find('Download'), patience: 90, why: 'taking the file' }),
      ],
    },
    snapshot_no_ask: {
      readyInMinutes: 0,
      toTake: [
        step({ do: 'go', address: 'https://seller.example.invalid/s', why: 'going there' }),
        step({ do: 'take-file', find: find('Download', { called: 'the download button' }),
          patience: 60, why: 'taking the snapshot' }),
      ],
    },
    no_find_file: {
      readyInMinutes: 0,
      toAsk: [],
      toTake: [
        step({ do: 'go', address: 'https://seller.example.invalid/n', why: 'going there' }),
        step({ do: 'take-file', patience: 60, why: 'taking whatever the page produced' }),
      ],
    },
    no_file: {
      readyInMinutes: 0,
      toAsk: [],
      toTake: [
        step({ do: 'go', address: 'https://seller.example.invalid/x', why: 'going somewhere' }),
      ],
    },
    bad_recipe: {
      readyInMinutes: 0,
      toAsk: [],
      toTake: [step({ do: 'teleport', why: 'the impossible' })],
    },
  },
  whatItMeans: {
    'found-nothing': 'It is not on the page at all. Either the platform renamed it, or the page had not finished drawing.',
    'found-several': 'More than one thing on the page matches, so which one was meant cannot be known. Nothing was clicked.',
    'covered-up': 'Something is covering the page, so a click aimed at the page hits that instead. The button is there; it is underneath something.',
    'built-in-the-page': 'The platform now builds this file inside the page itself and hands over a temporary handle, which cannot be fetched a second time. This is a door closing, not something to retry.',
  },
  buildsInThePageSince: { fk_orders: '2026-08-22' },
  /* **WHAT A LANDED FILE IS CALLED, exported out of the Python by
   * `tools/export_recipes.py`.** Written out here by hand because this is a
   * stand-in book -- and `export_recipes_checks.py` is what holds the real one
   * to `landing.file_name_for`, report by report. */
  fileNames: {
    me_orders: { platform: 'meesho', extension: 'csv' },
    me_two_pages: { platform: 'meesho', extension: 'csv' },
    me_catalog: { platform: 'meesho', extension: 'csv' },
    snapshot_no_ask: { platform: 'meesho', extension: 'csv' },
    no_find_file: { platform: 'meesho', extension: 'csv' },
    fk_orders: { platform: 'flipkart', extension: 'xlsx' },
    bad_recipe: { platform: 'meesho', extension: 'csv' },
  },
};

/* ------------------------------------------------------- a stand-in portal */

/** A file nobody asked for, handed over by something else on the portal's page.
 *
 *  **NINES SO IT CANNOT BE MISTAKEN FOR THE GENUINE ONE.** The stand-in's real
 *  file is `1,2,3,4,5`; this is nine nines. A check that only counted bytes
 *  could be satisfied by the wrong file of the right length, which is the shape
 *  of a check that cannot fail. */
const SOMEBODY_ELSES = new Uint8Array([9, 9, 9, 9, 9, 9, 9, 9, 9]);

/** Let the page's own code have a turn. **A REAL AWAIT, NOT A PRETEND ONE.**
 *  Every `await` in the walk is a moment when the portal's own scripts run, and
 *  a stand-in that never yields is a stand-in kinder than the real thing. */
const aMoment = (ms = 0) => new Promise((done) => { setTimeout(done, ms); });

function aPortal(how = {}) {
  const it = {
    went: [], clicked: [], ranges: [], cursorToldFor: [], stepsSeen: 0, patienceTold: [], tookFile: 0,
    handedOver: [], turns: 0, waited: [], clickedAway: 0,
    /* **THE MENU, AS MEESHO REALLY BEHAVES.** Its list of finished exports is
     * drawn AS it opens and never again while it is open. So this holds the two
     * facts that follow: whether it is open, and how many times it has been SHUT
     * and opened again. Counting clicks instead would let a loop that never shut
     * it pass. */
    menuOpen: false, shutSinceLastOpened: false, reopened: 0,
    /* **WHAT HAPPENED AND IN WHAT ORDER.** The whole of this is about WHEN the
     * catcher is armed relative to the click that builds the file, and an order
     * is the only thing that can be checked about a when. */
    whatHappened: [],
    /* **THE PAGE'S OWN WORLD, IN MINIATURE.** `catch-blob.js` lives here in the
     * real thing: armed with one secret, it takes the FIRST file the page builds
     * and is then spent. Arming afresh throws away anything already caught,
     * exactly as `content.js` does (`caught = null` before the new secret). */
    theCatcher: { armedFor: null, caught: null, armedTimes: 0 },
    /* **WHAT WAS ACTUALLY PUT AWAY, recorded rather than counted.** A stand-in
     * that answered "yes" would leave every walk looking perfectly right with
     * the bytes on the floor -- which is exactly the state this recorded the
     * day it was added. */
    putAway: [],
  };
  /* **WHERE THE BYTES GO, in miniature.** The real one is a message to the
   * background half, which is the only side that can reach `chrome.identity`. */
  it.putTheFile = async ({ reportId, fileName, body }) => {
    if (how.driveRefuses) throw new Error(how.driveRefuses);
    it.putAway.push({
      reportId,
      fileName,
      size: body ? body.length : 0,
      /* **WHOSE FILE IT WAS, not just how big.** Two files of the same length
       * are not the same file, and this whole section is about one being swapped
       * for the other. */
      startsWith: body && body.length ? body[0] : null,
    });
    return { put: 'an-id' };
  };

  /** Something else on the portal's page hands the browser a file of its own.
   *
   *  **THIS IS NOT A HYPOTHETICAL.** A portal page carries adverts and tag
   *  managers, and every one of them can call `URL.createObjectURL`. It does not
   *  have to stand in front of anything -- it stands beside it. `armedFor` is
   *  spent on the first file that comes past, whoever built it. */
  const somethingElseOnThePage = (moment) => {
    if (!(how.alsoOnThePage || []).includes(moment)) return;
    if (!it.theCatcher.armedFor) return;
    it.theCatcher.caught = SOMEBODY_ELSES;
    it.theCatcher.armedFor = null;
    it.whatHappened.push(`somebody else handed over a file ${moment}`);
  };

  /* **ARMING THE CATCHER, WHICH IS A ROUND TRIP TO THE BACKGROUND** --
   * `chrome.scripting.executeScript` puts `catch-blob.js` into the page's own
   * world. The page's own scripts run during it, which is why the moment
   * straight after it is one this stand-in can be told to fire at.
   *
   * **NOT ON THE DOOR, because the door is the ten calls the Python side makes
   * and the Python has no catcher.** Handed to the walk on its own, like
   * `putTheFile`. */
  it.armTheCatcher = async () => {
    it.theCatcher.armedFor = `a fresh secret ${it.theCatcher.armedTimes}`;
    it.theCatcher.armedTimes += 1;
    it.theCatcher.caught = null;
    it.whatHappened.push('armed');
    await aMoment();
    somethingElseOnThePage('the instant it is armed');
  };

  it.door = {
    async go(address, patience, nextAt) {
      it.went.push(address);
      it.patienceTold.push(['go', patience]);
      /* **WHAT THE REAL BACKGROUND IS HANDED, and it is recorded because it is
       * the only thing that survives the page.** Everything else this stand-in
       * remembers would be lost with the page in front of a seller; this number
       * is the walk's whole memory. */
      it.handedOver.push(nextAt);
      /* A page that has been loaded again has nothing open on it. */
      it.menuOpen = false;
      it.shutSinceLastOpened = false;
    },
    async needs_signing_in() {
      /* **SIGNED OUT PART WAY THROUGH, which is a case that could not exist
       * before D200 and now can.** A walk spans several pages; the portal can
       * end the session between any two of them. */
      if (how.signedOutFromTurn !== undefined) return it.turns >= how.signedOutFromTurn;
      return Boolean(how.signedOut);
    },
    async overlays() {
      const after = how.coveredAfter;
      if (after !== undefined && it.stepsSeen < after) return [];
      if (how.covered || after !== undefined) {
        /* **THE REAL ONE, off his own Chrome: a promotion on a full-screen
         * backdrop.** The backdrop is what a click aimed at the page hits, and
         * it carries no words of its own -- the words are on the panel. */
        return [
          { width: 1280, height: 800, text: '', blocks: true },
          { width: 414, height: 330, text: 'Abhi Update Karein ! Participate Now', blocks: false },
        ];
      }
      /* **THE DOWNLOAD MENU THE RECIPE OPENS ITSELF**, measured on his own
       * payments page: a dialog, 232 x 196, nothing laid over anything. */
      if (how.ownMenu) {
        /* **MEASURED ON HIS OWN INVENTORY PAGE.** The "Bulk Stock Update" panel
         * the recipe opens sits on a backdrop the size of the whole window --
         * and the Download the recipe wants is inside it. */
        return [
          { width: 1600, height: 664, text: 'Bulk Stock Update Step 1 Download', blocks: true },
          { width: 280, height: 136, text: 'Bulk Stock Update Step 1 Download', blocks: false },
        ];
      }
      if (how.smallNotice) return [{ width: 250, height: 60, text: 'Saved', blocks: false }];
      return [];
    },
    async find(kind, what, exact, patience) {
      it.stepsSeen += 1;
      it.patienceTold.push(['find', patience]);
      it.whatHappened.push(`found ${what}`);
      /* **A PORTAL DRAWS ITSELF IN PIECES AND TAKES ITS TIME OVER IT** -- 10 to
       * 25 seconds was measured on his own Flipkart account. Every one of those
       * seconds is a moment the page's own scripts are running. */
      if (how.slowToDraw) await aMoment(how.slowToDraw);
      somethingElseOnThePage('while the page is drawing');
      if (how.matches && what in how.matches) return how.matches[what];
      /* **A PROMOTION HIDES WHAT IS UNDERNEATH IT.** That is what makes a
       * covering worth reporting at all: the lookup fails, and the reason is
       * not that the button was renamed. A panel the recipe opened itself does
       * NOT hide anything -- it contains the very thing being looked for --
       * which is why `ownMenu` below leaves this alone. */
      const after = how.coveredAfter;
      const covered = how.covered || (after !== undefined && it.stepsSeen > after);
      if (covered) return 0;
      /* **THE FINISHED FILE IS NOT IN THE LIST YET, and this is the only way to
       * say so.** Meesho draws its list of finished exports as the download menu
       * OPENS, so the list only ever changes when the menu is shut and opened
       * again. With nothing reopening it, the row never appears at all. */
      if (how.appearsAfterReopens !== undefined && what === 'Download') {
        return it.menuOpen && it.reopened >= how.appearsAfterReopens ? 1 : 0;
      }
      /* **A CONTROL THE PORTAL TAKES AWAY PART WAY THROUGH.** Told to, this one
       * takes the opener away the moment the menu is shut -- the one moment in
       * the whole walk when nothing is holding it open. */
      if (how.openerGoesWhenShut && what === 'Download Orders Data' && it.clickedAway) return 0;
      return 1;
    },
    async click(kind, what) {
      /* **A CONTROL THAT IS NOT THERE CANNOT BE CLICKED, AND THE REAL DOOR
       * THROWS.** `driver.js` looks the thing up and refuses when nothing
       * matches. A stand-in that quietly accepted the click would let a walk
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
    /* **NOTHING IS REALLY SLEPT FOR, AND THE NUMBER IS KEPT.** A stand-in that
     * really waited would put minutes into this file; one that forgot the number
     * would let a wait of nought seconds pass as a wait of thirty-five. */
    async wait(seconds) {
      it.waited.push(seconds);
      it.whatHappened.push(`waited ${seconds}`);
    },
    /* **WHICH CALENDAR IT IS STANDING IN FRONT OF IS RECORDED TOO.** Flipkart's
     * Reports Centre switches a day off two different ways and one of them shows
     * only in the cursor -- that portal's own habit, so the recipe carries it
     * and the door has to be told. A stand-in that dropped it would let a recipe
     * say so while the door never heard it, which is the exact shape of "the
     * comment said it and the code did not". */
    async pick_range(from, to, patience, alsoByTheCursor) {
      it.ranges.push([from, to]);
      it.cursorToldFor.push(alsoByTheCursor);
      it.patienceTold.push(['pick_range', patience]);
    },
    async take_file(patience) {
      it.tookFile += 1;
      it.patienceTold.push(['take_file', patience]);
      it.whatHappened.push('took the file');
      /* **THE PLATFORM'S OWN SERVER IS BEING WAITED ON HERE.** The click has
       * gone; the page is posting to Meesho and will build the file when the
       * answer comes back. On a slow morning that is not instant, and this is
       * the gap a fix with a clock in it would fail inside. */
      if (how.slowToBuildTheFile) await aMoment(how.slowToBuildTheFile);
      /* **WHOEVER GOT THERE FIRST IS WHAT ARRIVES.** `content.js` takes the
       * first message it accepts and the catcher is spent on the first file it
       * sees -- so a file somebody else built displaces the genuine one, which is
       * the whole of the harm. */
      if (it.theCatcher.caught) return it.theCatcher.caught;
      if (how.theFileIsBuiltInThePage) {
        /* **THE ONLY PLACE THESE BYTES EVER EXIST IS INSIDE THE PAGE**, so
         * nothing arrives at all unless the catcher was armed for them. Without
         * this, a change that stopped arming altogether would look like a fix. */
        if (!it.theCatcher.armedFor) return null;
        it.theCatcher.armedFor = null;
      }
      if (how.builtInPage) return null;
      if (how.emptyFile) return new Uint8Array(0);
      /* **THE PORTAL ANSWERING A FILE ADDRESS WITH ITS SIGN-IN PAGE.** It is a
       * file, it has a size, and everything downstream believes the day
       * arrived -- `doors.js` calls it the worst possible outcome. */
      if (how.signInPage) {
        return new TextEncoder().encode('<!doctype html><html><body>Sign in');
      }
      return how.bytes || new Uint8Array([1, 2, 3, 4, 5]);
    },
    async page_text() {
      return how.page || 'Welcome back   Manage and grow your business';
    },
  };
  return it;
}

/**
 * Walk a report the way the extension really walks one: in TURNS.
 *
 * **THIS IS NOT A CONVENIENCE, IT IS THE STAND-IN BEING HONEST (D200).** A walk
 * no longer runs to the end inside one page. Going somewhere destroys the page
 * that asked, so the walk hands back "carrying on, from step N", and the page
 * Chrome draws next starts again at N. A harness that called the walk once and
 * expected an outcome would be testing a product that does not exist -- and
 * would have gone green on the very fault that killed three walks on his own
 * panel.
 *
 * So this loop IS `content.js` and the background, in miniature: the number is
 * the only thing carried across, a fresh walk is built each turn, and nothing
 * the previous turn held survives.
 */
function aWalk(portal, book = BOOK) {
  return async (reportId, day, rest = {}) => {
    let startAt = 0;
    for (let turn = 0; turn < 40; turn += 1) {
      portal.turns += 1;
      /* **BUILT AGAIN EVERY TURN, exactly as the page half is.** Sharing one
       * walk across turns would let a variable carry state that a real page
       * loses, which is the kindness that hides this whole class of fault. */
      /* **THE CATCHER IS ARMED AT THE START OF THE TURN, WHICH IS WHERE
       * `content.js` ARMS IT TODAY** -- `takeATurn` sends `arm-the-catcher`
       * before the first step runs. It is here rather than inside the walk
       * because that is where the product puts it, and a harness that put it
       * somewhere kinder would be testing a product that does not exist. */
      // eslint-disable-next-line no-await-in-loop
      await portal.armTheCatcher();
      const walking = theWalk({
        door: portal.door, book, say: (line) => SAID.push(line), putTheFile: portal.putTheFile,
        armTheCatcher: portal.armTheCatcher,
      });
      let answer;
      try {
        // eslint-disable-next-line no-await-in-loop
        answer = await walking(reportId, day, { panel: PANEL, startAt, ...rest });
      } catch (wrong) {
        if (wrong instanceof NeedsSigningIn) throw wrong;
        THREW.push(`${reportId}: ${wrong && wrong.message}`);
        return NOTHING;
      }
      if (!hasNotFinished(answer)) return answer;
      startAt = answer.at;
    }
    THREW.push(`${reportId}: it kept carrying on and never finished`);
    return NOTHING;
  };
}

/* ----------------------------------------- the four words, and the answer */

/* **THE SAME FOUR WORDS THE PYTHON DOOR ANSWERS.** A fifth spelling of "it
 * worked" is a report the runner cannot read, and that is the whole of D100:
 * one report list, one log, one board, the door a detail underneath. */
check('a report that came back is "landed"', LANDED === 'landed');
check('one still being built is "still-waiting"', STILL_WAITING === 'still-waiting');
check('one that went wrong is "failed"', FAILED === 'failed');
check('and there being nothing to fetch is spelt as the Python spells it',
  NOTHING_TO_FETCH === 'nothing-to-fetch');
check('and every failure has its own name rather than one shared one',
  new Set([FOUND_NOTHING, FOUND_SEVERAL, COVERED_UP, BUILT_IN_THE_PAGE]).size === 4);

/* --------------------------------------------------------- the small parts */

check('a step that is not a step is refused',
  whyStepIsRefused('go somewhere') === 'That is not a step.');
/* **NOTHING AT ALL IS ASKED ABOUT FIRST**, or reading what it says to do falls
 * over and the failure is a crash rather than a refusal naming the recipe. */
check('and nothing at all is refused rather than falling over',
  whyStepIsRefused(null) === 'That is not a step.');
check('a kind nobody knows is refused', whyStepIsRefused(step({ do: 'teleport' })) !== null);
check('going nowhere is refused', whyStepIsRefused(step({ do: 'go', address: '' })) !== null);
check('a click with nothing to look for is refused',
  whyStepIsRefused(step({ do: 'click' })) !== null);
check('so is a wait with nothing to look for',
  whyStepIsRefused(step({ do: 'wait-for' })) !== null);
check('a way of finding something with no words is refused',
  whyStepIsRefused(step({ do: 'click', find: { how: 'role', what: '' } })) !== null);
check('a step that waits no time at all is refused',
  whyStepIsRefused(step({ do: 'go', address: 'x', patience: 0 })) !== null);
/* **NOT DECORATION.** Without it a failure can only say what could not be found. */
check('a step that does not say what it is for is refused',
  whyStepIsRefused({ do: 'go', address: 'x', patience: 5, why: '' }) !== null);
check('a good step is not refused',
  whyStepIsRefused(step({ do: 'go', address: 'x' })) === null);
/* **A STEP THAT ONLY WAITS, AND WHY IT IS NOT A WAIT-FOR.** Meesho builds an
 * orders export on its own servers and the page shows nothing at all while it
 * happens, so there is nothing to look at -- only time to pass. Written with
 * something to look for, a wait would pass its time and never look at it, and
 * the recipe would read as though it had waited FOR that thing. */
check('a step that only waits is not refused for having nothing to look for',
  whyStepIsRefused(step({ do: 'wait', patience: 35 })) === null);
check('but one that names something to look for is refused',
  whyStepIsRefused(step({ do: 'wait', patience: 35, find: find('Download') })) !== null);
check('and the reason sends whoever wrote it to the step that does look',
  String(whyStepIsRefused(step({ do: 'wait', patience: 35, find: find('D') }))).includes('wait-for'));
/* **SHUTTING SOMETHING AND OPENING IT AGAIN BETWEEN LOOKS.** The same rules the
 * Python holds, because a recipe reaching the extension has already left the
 * place those were checked. */
const reopening = (rest = {}) => step({
  do: 'take-file', find: find('Download'),
  lookAgain: { by: find('Download Orders Data'), times: 6, after: 30, ...rest },
});
check('a take-file step may say what to shut and open again',
  whyStepIsRefused(reopening()) === null);
check('but nothing else may',
  whyStepIsRefused(step({
    do: 'click', find: find('x'), lookAgain: { by: find('y'), times: 6, after: 30 },
  })) !== null);
check('it has to say what to shut and open again',
  whyStepIsRefused(reopening({ by: find('') })) !== null);
check('looking again no times at all is refused',
  whyStepIsRefused(reopening({ times: 0 })) !== null);
/* **NOUGHT SECONDS SHUT IS A MENU THAT WAS NEVER SHUT.** It would be opened
 * again on the same list it was closed on, every time. */
check('and so is shutting it for no time at all',
  whyStepIsRefused(reopening({ after: 0 })) !== null);

check('a page with nothing over it is clear', whatIsCovering([]) === null);
check('and no list at all is clear', whatIsCovering(null) === null);
check('a small notice is ordinary furniture',
  whatIsCovering([{ width: 250, height: 80, text: 'Saved', blocks: false }]) === null);
check('a wide but shallow banner is too',
  whatIsCovering([{ width: 1200, height: 60, text: 'Upcoming Policy Update', blocks: false }]) === null);
check('but something laid over the whole page is',
  whatIsCovering([{ width: 1280, height: 800, text: 'Abhi Update Karein', blocks: true }])
  === 'Abhi Update Karein');
/* **A BACKDROP CARRIES NO WORDS.** They are on the panel sitting on it, and
 * without them a failure cannot say WHICH promotion it was. */
check('and when the thing in the way says nothing, the words come from what sits on it',
  whatIsCovering([
    { width: 1280, height: 800, text: '', blocks: true },
    { width: 414, height: 330, text: 'Abhi Update Karein', blocks: false },
  ]) === 'Abhi Update Karein');
/* **THE NEAR-MISS.** Judged by size these were four pixels apart. */
check('a menu the door opened itself is not something covering the page',
  whatIsCovering([{ width: 232, height: 196, text: 'GST Report', blocks: false }]) === null);
check('and neither is a big dialog that is not laid over anything',
  whatIsCovering([{ width: 600, height: 400, text: 'big but in the flow', blocks: false }]) === null);

check('the page is kept as one line of words',
  capture('  Payments \n   settled ') === 'Payments settled');
check('and a very long page is cut to what a log can hold',
  capture('x'.repeat(900)).length === 400);
check('and nothing at all is kept as nothing', capture(null) === '');

check('a two-day range ends on the day being fetched',
  daysBefore('2026-08-26', 1) === '2026-08-25');
check('and a one-day range is the day itself', daysBefore('2026-08-26', 0) === '2026-08-26');
check('and it steps back over the end of a month',
  daysBefore('2026-08-01', 1) === '2026-07-31');
/* **AND ASKED TO STEP BACK BY NOTHING AT ALL, IT ANSWERS THE DAY.** Left to work
 * it out, "nothing" is not a number and the answer comes back as the words
 * "Invalid Date" -- a date the platform would simply refuse, silently. */
check('asked to step back by nothing at all, it answers the day itself',
  daysBefore('2026-08-26', undefined) === '2026-08-26');

/* ------------------------------------------------------------ an ordinary run */

{
  SAID.length = 0;
  const portal = aPortal();
  const got = await aWalk(portal)('me_orders', DAY);
  check('a report is fetched all the way through', got.state === LANDED);
  check('and the bytes are counted', got.size === 5);
  check('and it says so in words a person reads -- AND SAYS WHERE IT WENT',
    got.say === `Landed 5 bytes in the seller's Drive as meesho_me_orders_${DAY}.csv.`);
  /* **THE ANSWER CARRIES EVERY FIELD, ALWAYS.** A field that is simply absent
   * and a field that is empty read the same to a person and differently to the
   * runner, which asks all of them. */
  check('the answer names the report it is about', got.reportId === 'me_orders');
  check('and the day it is about', got.dataDate === DAY);
  /* **AND IT CARRIES THE NAME IT WAS PUT AWAY UNDER.** It used to carry `null`,
   * because nothing supplied one and nothing put the file anywhere -- the answer
   * had a field for a name and the product had no file. */
  check('and carries the name the file was put away under',
    'fileName' in got && got.fileName === `meesho_me_orders_${DAY}.csv`);
  check('and nothing in flight, because nothing is',
    'theirId' in got && got.theirId === null);
  check('and a page, empty because nothing went wrong',
    'pageWas' in got && got.pageWas === '');
  check('and a size', 'size' in got);

  const named = await aWalk(aPortal())('me_orders', DAY,
    { fileName: 'meesho_me_orders_2026-08-26.csv' });
  check('and given a name to land under, it carries that',
    named.fileName === 'meesho_me_orders_2026-08-26.csv');
  /* **REACHED BY ADDRESS.** That is what steps round the promotion. */
  check('it went straight to the page address', portal.went.some((a) => a.includes('/orders')));
  check('and the seller\'s own panel was filled in',
    portal.went.some((a) => a.includes(PANEL)));

  /* **EVERY OCCURRENCE, NOT THE FIRST.** What stood in walk.js said the long
   * name had to be filled before the short one because the short sits inside
   * it. It does not, so the ordering was never load-bearing -- and while a
   * false reason sat there, the thing that IS load-bearing had nothing on it. */
  const twice = aPortal();
  await aWalk(twice)('me_twice_over', DAY);
  check('a day and a panel named twice in one address are both filled, both times',
    twice.went.some((a) => !a.includes('{') && a.split(DAY).length === 3
      && a.split(PANEL).length === 3));

  /* **AND THE DAY WRITTEN THE WAY THE PLATFORM WRITES IT.** A row on his
   * returns page reads `25 Aug 2026`, and no two platforms agree -- so the
   * recipe says which, and the words are looked for on the page rather than the
   * short date. Given none, the short date is what goes in: a step looking for
   * the empty string matches the first thing on the page, which is how a walk
   * takes the wrong file and says it worked. */
  const inWords = aPortal();
  await aWalk(inWords)('me_in_words', DAY, { dayInWords: '26 Aug 2026' });
  check('a day written the way the platform writes it goes in as the words',
    inWords.went.some((a) => a.includes('26 Aug 2026')));
  const noWords = aPortal();
  await aWalk(noWords)('me_in_words', DAY);
  check('and with no words given, the plain date goes in rather than nothing',
    noWords.went.some((a) => a.includes(DAY) && !a.includes('{')));
  check('the date range was set to the day being fetched',
    portal.ranges.length === 1 && portal.ranges[0][0] === DAY && portal.ranges[0][1] === DAY);
  /* **THIS USED TO BE `SAID.length > 0` AND THAT READ NOTHING.** It passed
   * before every step announced itself and after, and it would pass if the line
   * printed `undefined`. A check that cannot tell those apart is not guarding
   * the thing its own name claims. */
  check('more was said than the three clicks -- every step announces itself now',
    SAID.length > portal.clicked.length);
  check('and each line names the report, its place in the walk, and why',
    SAID.every((line) => /^[a-z_]+: step \d+ of \d+, .+\.$/.test(line)));
  check('and no line says undefined',
    SAID.every((line) => !line.includes('undefined')));
  /* **A WAIT LOOKS AND DOES NOT CLICK.** Otherwise the download menu is opened
   * and then opened again, which closes it. */
  check('the things meant to be clicked were clicked',
    JSON.stringify(portal.clicked) === JSON.stringify(['Download Orders Data', 'Export data', 'Download']));
  check('and the thing only waited for was not clicked twice',
    portal.clicked.filter((one) => one === 'Download Orders Data').length === 1);
}

{
  /* A snapshot report has no date range at all -- it is a picture of right now. */
  const portal = aPortal();
  await aWalk(portal)('me_catalog', DAY);
  check('a snapshot report is not asked for a date range', portal.ranges.length === 0);
}

{
  /* **HOW A CALENDAR SWITCHES A DAY OFF REACHES THE DOOR, OR IT MIGHT AS WELL
   * NOT BE IN THE RECIPE.** Flipkart's Reports Centre has two mechanisms and one
   * of them shows only in the cursor; the door refuses to read the cursor unless
   * it is told to, because an ordinary unstyled cell has no pointer cursor
   * either. Said in the recipe and dropped on the way, the second mechanism is
   * caught by nothing at all -- and nothing in the walk would look wrong. */
  const flipkart = aPortal();
  await aWalk(flipkart)('fk_orders', DAY);
  check('a calendar the recipe says reads the cursor is passed on as such',
    JSON.stringify(flipkart.cursorToldFor) === JSON.stringify([true]));
  /* **AND EVERY OTHER CALENDAR IS TOLD THE OPPOSITE, not merely left unsaid.**
   * Undefined would read as false today and is one careless default away from
   * reading as true. */
  const meesho = aPortal();
  await aWalk(meesho)('me_orders', DAY);
  check('and a calendar that says nothing about it is told so plainly',
    JSON.stringify(meesho.cursorToldFor) === JSON.stringify([false]));
}

{
  /* **EVERY WAIT IS TOLD ITS OWN STEP'S NUMBER.** The Python had this missing
   * entirely for a while: a step that waits five minutes for Meesho to build a
   * file asked once and gave up. */
  const portal = aPortal();
  await aWalk(portal)('me_orders', DAY);
  const told = Object.fromEntries(portal.patienceTold);
  check('going somewhere is told how long to wait', told.go === 30);
  check('setting the dates is told its own number', told.pick_range === 20);
  check('and taking the file is told the five minutes the recipe says',
    portal.patienceTold.some(([call, n]) => call === 'take_file' && n === 300));
  check('and the numbers are not all the same, so one shared value cannot pass this',
    new Set(portal.patienceTold.map(([, n]) => n)).size > 1);
}

/* ------------------------------ something covering the page is its own failure */

{
  const portal = aPortal({ covered: true });
  const got = await aWalk(portal)('me_orders', DAY);
  check('a promotion covering the panel is a failure', got.state === FAILED);
  /* **AND THE ORDER MATTERS.** The covering is asked about only once the lookup
   * has already failed, so a panel the recipe opened itself costs nothing --
   * see the check below on the door's own menu. */
  check('and it says the page is covered, not that a button is missing',
    got.say.includes('covering the page') && !got.say.includes('renamed'));
  /* **NAMED IN THE SELLER'S WORDS, not by the raw text on the button.** */
  check('and it names what it was looking for, in words a person reads',
    got.say.includes('the download menu'));
  check('and what it was trying to do at the time',
    got.say.includes('waiting for the orders page'));
  check('and that the button is there, underneath', got.say.includes('underneath something'));
  check('nothing was clicked while something was in the way', portal.clicked.length === 0);
  check('and what was on the page is kept with the failure', got.pageWas !== '');
}

{
  const portal = aPortal({ smallNotice: true });
  check('a small notice does not stop the run',
    (await aWalk(portal)('me_orders', DAY)).state === LANDED);
}

{
  /* **THE PANEL THE RECIPE OPENS ITSELF, as it really is on his own inventory
   * page: it sits on a full-screen backdrop AND CONTAINS THE VERY DOWNLOAD the
   * recipe is about to press.** Asked about before the lookup, the door would
   * refuse to carry on because of a panel it had just opened. Asked after a
   * lookup that FAILED, it costs nothing at all. */
  const portal = aPortal({ ownMenu: true });
  check('a panel the door opened itself, over the whole window, does not stop the run',
    (await aWalk(portal)('me_orders', DAY)).state === LANDED);
}

{
  /* The promotion does not always arrive first. A run that got all the way to
   * the download and then hit one must not report a missing button. */
  const portal = aPortal({ coveredAfter: 2 });
  const got = await aWalk(portal)('me_catalog', DAY);
  check('a page covered at the last step is still reported as covered', got.state === FAILED);
  check('and says so rather than blaming the download', got.say.includes('covering the page'));
  check('and keeps the page', got.pageWas !== '');
  check('and says what it was doing at the time', got.say.includes('taking the stock file'));
}

{
  /* A take-file step that names what it presses says that name; one that presses
   * nothing at all says "the file", rather than the word "undefined". */
  const named = aPortal({ coveredAfter: 0 });
  const one = await aWalk(named)('snapshot_no_ask', DAY);
  check('a covered download names itself in the seller own words',
    one.say.includes('the download button'));

  /* **A TAKE-FILE STEP THAT PRESSES NOTHING HAS NO LOOKUP TO EXPLAIN.** The file
   * either comes or it does not, and a covering is not the reason either way --
   * so it goes straight to asking for the file. */
  const bare = aPortal({ coveredAfter: 0, builtInPage: true });
  const two = await aWalk(bare)('no_find_file', DAY);
  check('a take-file step that presses nothing goes straight for the file',
    two.say.includes('builds this file inside the page') && !two.say.includes('undefined'));
}

{
  /* A recipe with no asking phase written down at all is a one-shot report, the
   * same as one with an empty asking phase. */
  const portal = aPortal();
  check('a recipe that does not mention an asking phase is simply fetched',
    (await aWalk(portal)('snapshot_no_ask', DAY)).state === LANDED);
}

/* ------------------------------ ambiguity is a failure, not a coin toss */

{
  const portal = aPortal({ matches: { 'Export data': 2 } });
  const got = await aWalk(portal)('me_orders', DAY);
  check('two things of the same name is a failure', got.state === FAILED);
  check('and it says how many matched', got.say.includes('2 things match'));
  check('and that nothing was clicked', got.say.includes('Nothing was clicked'));
  check('and nothing really was', !portal.clicked.includes('Export data'));
  check('and the page is kept so it can be worked out', got.pageWas !== '');
  /* **A FAILURE CARRIES THE SAME FIELDS A SUCCESS DOES.** The runner asks all of
   * them whatever happened, and a field that is simply absent is not the same as
   * one that is empty. */
  check('a failure carries no file name rather than leaving the field off',
    'fileName' in got && got.fileName === null);
  check('and a size of nothing', 'size' in got && got.size === 0);
  check('and nothing in flight', 'theirId' in got && got.theirId === null);
}

{
  /* **NAMED IN THE SELLER'S WORDS WHEN TWO MATCH, TOO.** The nine-day outage was
   * two things of one name, and the line that reports it has to be readable or
   * nobody acts on it. */
  const portal = aPortal({ matches: { 'Download Orders Data': 2 } });
  const got = await aWalk(portal)('me_orders', DAY);
  check('two things of one name names it as a person reads it',
    got.say.includes('the download menu') && got.say.includes('2 things match'));
  check('and nothing was clicked', portal.clicked.length === 0);
}

{
  const portal = aPortal({ matches: { 'Download Orders Data': 0 } });
  const got = await aWalk(portal)('me_orders', DAY);
  check('something that is not on the page is a failure', got.state === FAILED);
  check('and it says what was being attempted, not only what was missing',
    got.say.includes('waiting for the orders page'));
  check('and names the thing in words a person reads', got.say.includes('the download menu'));
  check('and suggests it may have been renamed', got.say.includes('renamed'));
  check('and keeps the page', got.pageWas !== '');
}

{
  /* The same two guards on the LAST step, where the file is taken. */
  const portal = aPortal({ matches: { Download: 2 } });
  const got = await aWalk(portal)('me_catalog', DAY);
  check('two downloads of the same name is a failure too', got.state === FAILED);
  check('and no file was taken', portal.tookFile === 0);

  const none = aPortal({ matches: { Download: 0 } });
  const missing = await aWalk(none)('me_catalog', DAY);
  check('and a download that is not there is a failure', missing.state === FAILED);
  check('with the page kept', missing.pageWas !== '');

  const twoNamed = aPortal({ matches: { Download: 2 } });
  const several = await aWalk(twoNamed)('snapshot_no_ask', DAY);
  check('two downloads of one name says which name, as a person reads it',
    several.say.includes('the download button') && several.say.includes('2 things match'));
  check('and what it was doing', several.say.includes('taking the snapshot'));
  const noneNamed = aPortal({ matches: { Download: 0 } });
  const gone = await aWalk(noneNamed)('snapshot_no_ask', DAY);
  check('and a missing one says the same name', gone.say.includes('the download button'));
}

/* ------------------------- a file built inside the page is a door closing */

{
  const portal = aPortal({ builtInPage: true });
  const got = await aWalk(portal)('fk_orders', DAY, { askedAlready: DAY });
  check('a file built inside the page is a failure', got.state === FAILED);
  check('and it says the platform changed how it hands the file over',
    got.say.includes('builds this file inside the page'));
  check('and that it is a door closing rather than something to retry',
    got.say.includes('door closing'));
  /* **SAID WITH THE DAY IT STARTED**, so it reads as known rather than as
   * tonight's news. */
  check('and says how long this has been happening', got.say.includes('since 2026-08-22'));
  check('and the page is still kept alongside it', got.pageWas !== '');

  const other = aPortal({ builtInPage: true });
  const quiet = await aWalk(other)('me_catalog', DAY);
  check('a report it has not happened to says nothing about a date',
    !quiet.say.includes('since'));
}

{
  const portal = aPortal({ emptyFile: true });
  const got = await aWalk(portal)('me_catalog', DAY);
  check('a file with nothing in it does not land', got.state === FAILED);
  check('and says nothing was written', got.say.includes('nothing has been written'));
}

/* ----------------------------- signing in is not this report's fault */

{
  const portal = aPortal({ signedOut: true });
  let wasItsOwnKind = false;
  let message = '';
  try {
    await aWalk(portal)('me_orders', DAY);
  } catch (wrong) {
    wasItsOwnKind = wrong instanceof NeedsSigningIn;
    message = wrong.message;
  }
  check('being signed out is its own kind of problem', wasItsOwnKind === true);
  check('and it says nothing can be fetched until somebody signs in',
    message.includes('until somebody does'));
  check('and that every report after it would fail the same way',
    message.includes('every report after this one'));
  check('and nothing was driven at all', portal.clicked.length === 0);
}

/* --------------------------------------------- two phases, asked once */

{
  const portal = aPortal();
  const asked = await aWalk(portal)('fk_orders', DAY);
  check('asking for a two-phase report is a success, not a failure',
    asked.state === STILL_WAITING);
  check('and it holds what it was asked under', asked.theirId === DAY);
  check('and says roughly how long it will take', asked.say.includes('30 minutes'));
  /* **AND THAT A LATER RUN COLLECTS IT RATHER THAN ASKING AGAIN**, because a
   * line that only says "asked for it" reads like something went unfinished. */
  check('and that a later run will collect it rather than asking again',
    asked.say.includes('collect it rather than asking again'));
  check('and it pressed Submit', portal.clicked.includes('Submit'));
  /* **THE SMALLEST RANGE FLIPKART TAKES IS TWO DAYS**, and it names the row by
   * the END date, which is the day being fetched. */
  check('the two-day range ends on the day being fetched',
    portal.ranges[0][0] === '2026-08-25' && portal.ranges[0][1] === DAY);

  /* **NEVER ASKED TWICE.** Flipkart allows twenty requests a day and the
   * reference burned through them re-submitting reports that had worked. */
  const back = aPortal();
  const collected = await aWalk(back)('fk_orders', DAY, { askedAlready: DAY });
  check('the next run collects it', collected.state === LANDED);
  check('and never presses Submit again', !back.clicked.includes('Submit'));

  /* A one-shot report handed a stale in-flight id simply fetches -- the safer
   * way round. */
  const one = aPortal();
  check('a one-shot report handed a stale id just fetches',
    (await aWalk(one)('me_catalog', DAY, { askedAlready: 'anything' })).state === LANDED);
}

/* ------------------------------------------------ a recipe that is wrong */

{
  const portal = aPortal();
  const got = await aWalk(portal)('me_nonsense', DAY);
  check('a report nobody has heard of is a failure, not a crash', got.state === FAILED);
  check('and says the browser door does not know how to fetch it',
    got.say.includes('browser door knows how to fetch'));
  check('and nothing was driven at all', portal.went.length === 0);
}

{
  const portal = aPortal();
  const got = await aWalk(portal)('bad_recipe', DAY);
  check('a bad step is a fault in the product and says so', got.state === FAILED);
  check('rather than reading as the platform having changed',
    got.say.includes('This recipe is wrong'));
}

{
  const portal = aPortal();
  const got = await aWalk(portal)('no_file', DAY);
  check('a recipe that never takes a file is a fault in the recipe', got.state === FAILED);
  check('and says which end of it is missing',
    got.say.includes('missing its last step'));
}

{
  const walking = theWalk({
    door: aPortal().door, book: BOOK, say: () => {}, putTheFile: async () => ({}),
    armTheCatcher: async () => {},
  });
  const got = await walking('me_orders', DAY, { panel: '' });
  check('a Meesho report with no panel name is a failure', got.state === FAILED);
  check('and says the panel name is the seller\'s own data',
    got.say.includes("seller's own data"));
  /* **WHILE FLIPKART NEEDS NONE.** A requirement of one platform must not be
   * applied to the other. */
  /* **WALKED IN TURNS, because a Flipkart recipe really goes somewhere** and a
   * single call now answers "carrying on" rather than an outcome. Left as one
   * call this read as a failure, which is the harness lying about the product. */
  const fk = aPortal();
  check('while a Flipkart one needs no panel name at all',
    (await aWalk(fk)('fk_orders', DAY, { panel: '', askedAlready: DAY })).state === LANDED);
}

{
  /* The walk cannot be built without its four parts. */
  const refused = (fn) => { try { fn(); return ''; } catch (e) { return e.message; } };
  const put = async () => ({});
  const arm = async () => {};
  check('a walk with no door is refused',
    refused(() => theWalk({ book: BOOK, say: () => {}, putTheFile: put, armTheCatcher: arm }))
      .includes('door to the page'));
  check('a walk with no recipes is refused',
    refused(() => theWalk({ door: {}, say: () => {}, putTheFile: put, armTheCatcher: arm }))
      .includes('book of recipes'));
  check('a walk with nowhere to say what it is doing is refused',
    refused(() => theWalk({ door: {}, book: BOOK, putTheFile: put, armTheCatcher: arm }))
      .includes('say what it is doing'));
  /* **AND A WALK WITH NOWHERE TO PUT THE FILE IS REFUSED, which is the whole of
   * what was wrong.** It fetched the seller's report, counted the bytes,
   * reported LANDED and dropped them -- and it looked exactly like working. */
  check('A WALK WITH NOWHERE TO PUT THE FILE IS REFUSED',
    refused(() => theWalk({ door: {}, book: BOOK, say: () => {}, armTheCatcher: arm }))
      .includes('somewhere to put the file'));
  check('and the refusal says what would otherwise happen, not just that it is missing',
    refused(() => theWalk({ door: {}, book: BOOK, say: () => {}, armTheCatcher: arm }))
      .includes('report that it had landed'));
  /* **AND A WALK WITH NO WAY OF ARMING THE CATCHER IS REFUSED (A44).** It would
   * fetch every report that comes down as a download and quietly never notice
   * one the page builds inside itself -- which reads as a portal that renamed a
   * button, and sent a month of diagnosis at the wrong thing once already. */
  check('A WALK WITH NO WAY OF ARMING THE CATCHER IS REFUSED',
    refused(() => theWalk({ door: {}, book: BOOK, say: () => {}, putTheFile: put }))
      .includes('arming the catcher'));
  check('and that refusal says what would otherwise go missing',
    refused(() => theWalk({ door: {}, book: BOOK, say: () => {}, putTheFile: put }))
      .includes('would never arrive'));
}

/* ------------------------------------- THE BYTES ACTUALLY GO SOMEWHERE (D171)
 *
 * **`extension/drive.js` IS 24 KB, 66 CHECKS, FINISHED -- AND WAS IMPORTED BY
 * NOTHING BUT ITS OWN TEST FILE.** The walk took the file and dropped it. So no
 * report a browser fetched had ever reached a real Drive, and a seller who had
 * set everything up correctly would still have seen Amazon and nothing else:
 * `me_orders` and `fk_orders` come this way, and the nightly run was reading
 * folders the browser never put anything in.
 */
{
  const portal = aPortal();
  const got = await aWalk(portal)('me_orders', DAY);
  check('THE FILE THE WALK TOOK IS ACTUALLY PUT SOMEWHERE', portal.putAway.length === 1);
  check('and it is the bytes that came back, not a count of them',
    portal.putAway.length === 1 && portal.putAway[0].size === 5);
  check('and it is put away under the report it belongs to',
    portal.putAway.length === 1 && portal.putAway[0].reportId === 'me_orders');
  /* **THE NAME IS THE PYTHON'S RULE, and it is not decoration**: the nightly run
   * takes the day out of the NAME and refuses a file that has none, so a name
   * invented here is a file that can never be read back out of the folder. */
  check('AND UNDER THE NAME THE NIGHTLY RUN CAN READ THE DAY OUT OF',
    portal.putAway.length === 1
    && portal.putAway[0].fileName === `meesho_me_orders_${DAY}.csv`);
  check('and the walk says it landed, and says where',
    got.state === LANDED && got.fileName === `meesho_me_orders_${DAY}.csv`
    && got.say.includes("seller's Drive"));
}

{
  /* **A DRIVE THAT REFUSED IS THIS REPORT'S FAILURE, NOT A LANDING.** Reported
   * as landed, the day would be written down as fetched and never tried again --
   * and the file would be nowhere. */
  const portal = aPortal({ driveRefuses: 'the seller has run out of Drive' });
  const got = await aWalk(portal)('me_orders', DAY);
  check('A FILE THAT COULD NOT BE PUT IN THE DRIVE IS NOT REPORTED AS LANDED',
    got.state === FAILED);
  check('and the reason Drive gave is carried, not replaced with one of ours',
    got.say.includes('run out of Drive'));
  check('and it still says how many bytes came back, so it is plain the fetch worked',
    got.say.includes('5 bytes'));
  check('and nothing was put away', portal.putAway.length === 0);
}

{
  /* **A SIGN-IN PAGE IS NEVER PUT IN THE SELLER'S DRIVE AS THEIR DAY'S REPORT.**
   *
   * **THE GUARD EXISTED AND SAT ON ONE OF THREE PATHS.** `content.js` applied
   * `looksLikeAPage` only to its own fallback fetch; the background's fetch and
   * the blob the page catches went straight past it. That cost nothing while the
   * bytes were being dropped on the floor -- **the moment they started reaching
   * Drive it became the difference between a clean failure and a sign-in page
   * filed as the day's report.** */
  const portal = aPortal({ signInPage: true });
  const got = await aWalk(portal)('me_orders', DAY);
  check("A SIGN-IN PAGE IS NOT PUT IN THE DRIVE AS THE DAY'S REPORT",
    got.state === FAILED && portal.putAway.length === 0);
  check('and it says the browser has been signed out, not that the report is broken',
    got.say.includes('signed this browser out'));
  check('and it says the bytes were thrown away rather than filed',
    got.say.includes('thrown away'));
}

{
  /* **A REPORT THE BOOK SAYS NOTHING ABOUT IS NOT GIVEN A MADE-UP NAME.** A file
   * in the seller's Drive under a name the nightly run cannot read the day out
   * of sits there for ever while the ledger stays empty. */
  const bookWithNoNames = { ...BOOK, fileNames: {} };
  const portal = aPortal();
  const got = await aWalk(portal, bookWithNoNames)('me_orders', DAY);
  check('A REPORT WITH NO NAME IN THE BOOK IS A FAILURE, NOT A GUESSED NAME',
    got.state === FAILED && got.say.includes('is called'));
  check('and nothing is put away under a name nobody decided',
    portal.putAway.length === 0);
  check('the name is worked out from the book, never from anything in this file',
    theFileName(BOOK, 'me_orders', DAY) === `meesho_me_orders_${DAY}.csv`
    && theFileName(BOOK, 'me_orders', '') === ''
    && theFileName(BOOK, 'nothing_like_this', DAY) === ''
    && theFileName({}, 'me_orders', DAY) === '');
}

{
  /* ---------- THE DAY IS ASKED SOMETHING BEFORE IT BECOMES A FILE NAME (A33)
   *
   * **THE DAY IS THE ONE THING IN A WALK THAT NOBODY IN THIS REPOSITORY WROTE.**
   * It arrives as an argument to `startTheNight`, crosses the night's record and
   * the background's messages, and comes out in TWO places: the address a step
   * goes to, and the NAME the file is put away under. `theFileName` asked only
   * that it was not empty, so `05/09/2026` made `me_orders_05/09/2026.csv` --
   * and `landing.data_date_in` reads a day back out of a name with
   * `(\d{4}-\d{2}-\d{2})` and answers None for that one. **A file whose name has
   * no day in it is a file no reader can ever reach**, which is what
   * `landing.undated` exists for: seven real files sat like that for six weeks.
   */
  check('a day written the platform\'s way, not the run\'s, is refused',
    whyTheDayIsRefused('05/09/2026') !== null);
  check('and so is one with nothing in it at all', whyTheDayIsRefused('') !== null);
  check('and so is one that is the right shape and not a real day',
    whyTheDayIsRefused('2026-02-31') !== null);
  check('and a real day is not refused', whyTheDayIsRefused(DAY) === null);
  /* **AND A DAY WITH ANYTHING ROUND IT IS REFUSED RATHER THAN TIDIED (A33R).**
   * The first version of this guard trimmed before testing, so `" 2026-09-08 "`
   * came back good -- and `filledIn` then put the spaces straight into the
   * address a step goes to, because the caller uses the value it was HANDED and
   * not the tidy copy the guard made. **A guard that answers about a value
   * nobody uses is the fault this whole session is about.** Found by an
   * independent reviewer, not by these checks. */
  check('a day with spaces round it is refused, not quietly tidied',
    whyTheDayIsRefused(` ${DAY} `) !== null
    && whyTheDayIsRefused(`
${DAY}`) !== null
    && whyTheDayIsRefused(`${DAY}	`) !== null);
  check('and one that is only whitespace is refused too',
    whyTheDayIsRefused('   ') !== null);
  /* **AND THE ONE THAT MATTERS: IT IS REFUSED BEFORE A REPORT IS SPENT ON IT.**
   * The seller's Reports Centre allows twenty requests a day. */
  const portal = aPortal();
  const wrongDay = await aWalk(portal)('me_orders', '05/09/2026');
  check('A WALK GIVEN A DAY THE RUN CANNOT READ BACK FAILS BEFORE IT FETCHES',
    wrongDay.state === FAILED && wrongDay.say.includes('05/09/2026'));
  check('and nothing is put away under a name nothing would ever open',
    portal.putAway.length === 0);
  /* **AND `theFileName` ASKS THE SAME QUESTION, so a caller reaching it another
   * way gets the same answer rather than a name with a slash in it.** */
  check('and the name is never built out of a day like that',
    theFileName(BOOK, 'me_orders', '05/09/2026') === ''
    && theFileName(BOOK, 'me_orders', '2026-02-31') === '');
}

{
  /* ---------- HOW BIG IS WORTH CARRYING AT ALL (A33)
   *
   * **THE BYTES DO NOT GO STRAIGHT TO DRIVE FROM HERE.** They cross to the
   * background half as a message, and a message is turned into text on the way
   * -- one number and one comma per byte -- so a 40 MB file crosses as roughly
   * 160 MB. The catcher already refuses a file this big; the take-file half,
   * which is the OTHER way a file arrives, was refused by nothing at all.
   *
   * **HIS REAL FILES ARE ONE TO A HUNDRED KILOBYTES, WHICH IS WHY THIS NEEDED
   * WRITING DOWN RATHER THAN LEAVING TO BE NOTICED.** */
  /* **A REAL ARRAY OF REAL BYTES, allocated rather than pretended at.** A
   * stand-in with a `length` and nothing behind it would pass this check and
   * tell us nothing about what the walk does with a file that big. */
  const huge = aPortal({ bytes: new Uint8Array(TOO_BIG_TO_CARRY + 1) });
  const tooBig = await aWalk(huge)('me_orders', DAY);
  check('A FILE TOO BIG TO CARRY ACROSS IS REFUSED, AND SAYS HOW BIG IT WAS',
    tooBig.state === FAILED && tooBig.say.includes(String(TOO_BIG_TO_CARRY + 1)));
  check('and nothing that big is handed to the browser half',
    huge.putAway.length === 0);
  check('and the walk still names the file it was about, so the failure can be read',
    tooBig.fileName === `meesho_me_orders_${DAY}.csv`);
}

{
  /* **A FAILURE THE BOOK HAS NO WORDS FOR IS SAID PLAINLY, NOT INVENTED.** A
   * reassuring sentence nobody can trace back is worse than an awkward one. */
  const thin = { recipes: BOOK.recipes, whatItMeans: {}, buildsInThePageSince: {} };
  const portal = aPortal({ matches: { 'Download Orders Data': 0 } });
  const got = await aWalk(portal, thin)('me_orders', DAY);
  check('a failure the recipe file has no words for says exactly that',
    got.say.includes('no explanation in the recipe file'));
}

/* ------------------------------------- D200: a walk that outlives its own page */

/* **THE FAULT THESE EXIST FOR.** The walk runs inside the portal's own page and
 * its first `go` destroys that page. Three walks died on his own Meesho panel on
 * 5 September with "the message channel closed before a response was received",
 * which is what a page torn down mid-sentence looks like from the other side.
 * Every check below would have gone red on the old shape. */

{
  const portal = aPortal();
  const walking = theWalk({
    door: portal.door, book: BOOK, say: () => {}, putTheFile: portal.putTheFile,
    armTheCatcher: portal.armTheCatcher,
  });
  const first = await walking('me_orders', DAY, { panel: PANEL });
  check('going somewhere ends the turn rather than carrying on in a page that is gone',
    hasNotFinished(first));
  /* **NO `state` AT ALL, and that is the safety rather than a tidiness.**
   * Everything downstream reads `state` first. A thing without one cannot be
   * filed as an outcome by anybody, however carelessly it is passed on. */
  check('and it is not any kind of answer -- it carries no state for anything to read',
    first.state === undefined);
  check('and it says where the next page picks the walk up', first.at === 1);
  check('and the walk really did go somewhere before saying so', portal.went.length === 1);
  check('and it handed that same number to the background, which is all that survives',
    portal.handedOver.join(',') === '1');
  /* **NOTHING PAST THE `go` RAN.** In a real Chrome nothing COULD have; a walk
   * that clicked here would be clicking in a page that no longer exists. */
  check('and nothing after it was done, because there was no page left to do it in',
    portal.clicked.length === 0 && portal.tookFile === 0);
}

check('a walk still going is told apart from one that landed',
  hasNotFinished({ carryingOn: 'carrying-on', at: 3 })
  && !hasNotFinished({ state: LANDED })
  && !hasNotFinished(null));

{
  /* **PICKED UP WHERE IT WAS LEFT, and the steps before it are NOT done again.**
   * Done again, the download menu the first page opened is opened a second time
   * -- which closes it -- and the export is asked for twice. */
  const portal = aPortal();
  const walking = theWalk({
    door: portal.door, book: BOOK, say: () => {}, putTheFile: portal.putTheFile,
    armTheCatcher: portal.armTheCatcher,
  });
  const got = await walking('me_orders', DAY, { panel: PANEL, startAt: 1 });
  check('a walk picked up part way through finishes', got.state === LANDED);
  check('and it does not go anywhere a second time', portal.went.length === 0);
  check('and it clicks each thing once, not twice',
    portal.clicked.join(',') === 'Download Orders Data,Export data,Download');
}

{
  /* **THREE PAGES AND TWO TEARDOWNS, which is the real `me_orders`.** A walk
   * that survived only its FIRST teardown would pass every other check here and
   * still die on the one recipe that goes somewhere twice -- and that is exactly
   * the shape of "it worked once while somebody watched". */
  const portal = aPortal();
  const got = await aWalk(portal)('me_two_pages', DAY);
  check('a recipe that goes somewhere twice still lands', got.state === LANDED);
  check('and it took three pages to do it, one per turn', portal.turns === 3);
  check('and the place was handed over at each teardown, never the same number twice',
    portal.handedOver.join(',') === '1,4');
  check('and nothing was clicked twice across the three pages',
    portal.clicked.join(',') === 'Export data,Download');
}

{
  /* **THE SESSION ENDING BETWEEN TWO PAGES IS NOT A BROKEN BUTTON.** It is the
   * one failure that is nobody's report's fault, and calling it anything else
   * buries the only thing a person has to do. */
  /* **THE THIRD PAGE, so two pages of real work have already happened.** Caught
   * on the very first page this would prove nothing about a walk in flight. */
  const portal = aPortal({ signedOutFromTurn: 3 });
  let said = '';
  try {
    await aWalk(portal)('me_two_pages', DAY);
  } catch (wrong) {
    said = wrong instanceof NeedsSigningIn ? wrong.message : `the wrong kind: ${wrong.message}`;
  }
  check('a session that expires half way through a walk is caught on the next page',
    said.includes('asking to be signed in to'));
  check('and it is caught before anything on that page is clicked, the earlier work done',
    portal.clicked.join(',') === 'Export data');
}

{
  /* **A RECIPE THAT IS WRONG BEFORE THE RESUME POINT IS STILL REFUSED.** The
   * steps already walked are still read: a fault in the product must be found on
   * the night it exists, not on whichever later night a walk happens to start
   * from step nought. */
  const portal = aPortal();
  const bent = {
    ...BOOK,
    recipes: {
      ...BOOK.recipes,
      me_two_pages: {
        ...BOOK.recipes.me_two_pages,
        toTake: BOOK.recipes.me_two_pages.toTake.map(
          (one, at) => (at === 0 ? { ...one, do: 'teleport' } : one)
        ),
      },
    },
  };
  const walking = theWalk({
    door: portal.door, book: bent, say: () => {}, putTheFile: portal.putTheFile,
    armTheCatcher: portal.armTheCatcher,
  });
  const got = await walking('me_two_pages', DAY, { panel: PANEL, startAt: 4 });
  check('a bad step before the resume point is still a refusal, not skipped past',
    got.state === FAILED && got.say.includes('This recipe is wrong'));
}

/* ------------------------ a sign-in page is not a report, however big it is */

/* **`doors.js` NAMES THIS THE WORST POSSIBLE OUTCOME IN ITS OWN WORDS**: a
 * portal that has signed the browser out answers a file address with its sign-in
 * page, at 200 -- and it is a file, it has a size, and everything downstream
 * believes the day arrived. A26R4 found that the new page-side retry had
 * reopened exactly that door. */
const asBytes = (text) => new TextEncoder().encode(text);

check('a page served where a report was asked for is recognised as a page',
  looksLikeAPage(asBytes('<!DOCTYPE html><html><body>Sign in')));
check('and so is one with no doctype', looksLikeAPage(asBytes('<html lang="en">')));
/* **LEADING SPACE AND CAPITALS ARE HOW THIS GETS PAST A LOOSER TEST.** */
check('and one that begins with whitespace or capitals',
  looksLikeAPage(asBytes('\n  <!doctype HTML>')));
check('and any other markup a portal might answer with',
  looksLikeAPage(asBytes('<?xml version="1.0"?><error>')));

/* **AND EVERY REAL FILE THIS PRODUCT FETCHES IS LEFT ALONE.** A guard that
 * refused a real report would lose the day just as surely as one that let a page
 * through, and it would be blamed on the platform. */
check('a spreadsheet is not a page', !looksLikeAPage(new Uint8Array([80, 75, 3, 4, 20, 0])));
check('a csv is not a page', !looksLikeAPage(asBytes('Order Id,SKU,Quantity\n123,ABC,2')));
check('and a csv whose first column happens to be angle-bracketed is judged on its first byte',
  !looksLikeAPage(asBytes('Date,Views\n2026-09-05,9200')));
check('and nothing at all is not a page either, because it is a different failure',
  !looksLikeAPage(new Uint8Array(0)) && !looksLikeAPage(null));

/* --------------- somebody else's script on the same page as the report */

/* **THE HARM THESE ARE ABOUT, SAID ONCE.** A file the page builds inside itself
 * can only be noticed from inside that page, beside the portal's own code and
 * whatever adverts it carries. If something else on that page gets a file of its
 * own caught instead, those bytes go on to `land-the-file`, `drive.js` REPLACES
 * the genuine file of that day under the genuine report name, and the Python
 * reads it into the seller's ledger as real sales. **It is not a crash. It is
 * wrong money in a seller's books, silently, under a real report name.**
 *
 * **AND THE STAND-IN IS DELIBERATELY HARSHER THAN A REVIEWER WOULD BE.** The
 * page's own scripts get a turn at every await the walk makes, because in a real
 * Chrome they do. */

{
  /* **THE WIDE WINDOW: armed at the start of the turn, and the file not taken
   * until the last step.** In between the page draws itself -- 10 to 25 seconds
   * measured on his own account -- and every one of those seconds is a moment
   * something else on the page can hand over a file and be caught. */
  const portal = aPortal({
    theFileIsBuiltInThePage: true,
    alsoOnThePage: ['while the page is drawing'],
  });
  const came = await aWalk(portal)('me_catalog', DAY);
  check("a file handed over by something else on the page while the page is still drawing "
    + "does not reach the seller's Drive",
    portal.putAway.every((one) => one.startsWith !== 9));
  check('and the genuine file is the one that lands',
    came.state === LANDED && came.size === 5 && portal.putAway.length === 1);
}

{
  /* **THE NARROW WINDOW, AND IT IS STILL OPEN.** Arming is a round trip to the
   * background; the page's own scripts run during it. A script that simply keeps
   * calling `URL.createObjectURL` is caught the instant the catcher is armed,
   * however close to the click that arming happens.
   *
   * **THIS CHECK ASSERTS THE FAULT, NOT THE FIX, AND THAT IS DELIBERATE.** It is
   * written the way `background.test.js` pins the download-cancel not surviving
   * the walk: a known fault, held in place so it cannot quietly change. **THE DAY
   * THE HOLE IS REALLY CLOSED THIS GOES RED** -- and then it is rewritten inside
   * that change, never deleted for going red. */
  const portal = aPortal({
    theFileIsBuiltInThePage: true,
    alsoOnThePage: ['the instant it is armed'],
  });
  await aWalk(portal)('me_catalog', DAY);
  check('AND THE HOLE IS NOT CLOSED: a script that hands over a file the instant the catcher '
    + "is armed still reaches the seller's Drive, however late the arming happens",
    portal.putAway.some((one) => one.startsWith === 9));
}

{
  /* **A SLOW PORTAL ON A SLOW MORNING, WHICH IS THE OTHER HALF OF THE ANSWER.**
   * Narrowing WHEN a catch is believed is only worth having if it cannot lose a
   * genuine file, and the two obvious narrowings -- "only within N seconds of the
   * click" and "only while the page is quick" -- both lose one on a real seller's
   * Meesho at nine in the morning.
   *
   * **SO THIS IS THE CHECK THAT A CLOCK WOULD FAIL.** The portal takes its time
   * drawing AND takes its time between the click and the file, and the file still
   * lands. Nothing in what is believed measures time. */
  const portal = aPortal({
    theFileIsBuiltInThePage: true,
    slowToDraw: 60,
    slowToBuildTheFile: 250,
  });
  const came = await aWalk(portal)('me_catalog', DAY);
  check('a portal that is slow to draw and slow to build the file still lands it',
    came.state === LANDED && came.size === 5);
  check("and nothing in what is believed measures time, so a slow morning cannot lose a day",
    portal.putAway.length === 1 && portal.putAway[0].startsWith === 1);
}

{
  /* **WHERE THE ARMING SITS IN THE ORDER, WHICH IS THE WHOLE OF THIS CHANGE.**
   * The lookup can wait out its whole patience; the arming must come after it and
   * immediately before the click, because the click is what makes the page build
   * the file and there is no later moment. */
  const portal = aPortal({ theFileIsBuiltInThePage: true });
  await aWalk(portal)('me_catalog', DAY);
  const order = portal.whatHappened.join(' -> ');
  check('the catcher is armed after the lookup and immediately before the click that '
    + 'builds the file',
    order.includes('found Download -> armed -> clicked Download -> took the file'));
  /* **A RE-ARM, NOT A MOVE, AND THAT IS DELIBERATE.** The turn still arms at its
   * start, because the same message is what arms the download-cancel in the
   * background half and moving THAT is a different change with a different risk.
   * What closes the wide window is the SECOND arming: `content.js` throws away
   * whatever it is holding and starts waiting for a new secret, so a file caught
   * while the page was drawing is not merely disbelieved -- it is gone. */
  check('and it is armed again for the file even though the turn armed once already, so a file '
    + 'caught while the page was drawing is thrown away',
    order.indexOf('armed') < order.indexOf('found Download')
    && order.lastIndexOf('armed') > order.indexOf('found Download'));
}

{
  /* **AND IT FAILS CLOSED.** If the arming itself cannot be done -- the
   * background half being restarted is the ordinary reason -- `content.js` is
   * left waiting for nothing and refuses every message, including one the
   * earlier arming would have believed. **Falling back to the older secret would
   * be the one thing this change exists to stop**, so the walk stops instead and
   * the report fails out loud. */
  const portal = aPortal({ theFileIsBuiltInThePage: true });
  const walking = theWalk({
    door: portal.door, book: BOOK, say: () => {}, putTheFile: portal.putTheFile,
    armTheCatcher: async () => { throw new Error('The browser half is restarting.'); },
  });
  let stoppedWith = '';
  try {
    await walking('me_catalog', DAY, { panel: PANEL, startAt: 1 });
  } catch (wrong) {
    stoppedWith = (wrong && wrong.message) || '';
  }
  check('an arming that cannot be done stops the walk out loud rather than taking the file '
    + 'on an older secret',
    stoppedWith.includes('restarting') && portal.putAway.length === 0);
}

/* ------------- a step that only waits, and a menu shut and opened again */

/* Both of these are one recipe's steps swapped for the shape being asked about,
 * so nothing here depends on his real book -- `extension/recipes.test.js` drives
 * the real one. */
const bookWhere = (toTake) => ({
  ...BOOK,
  recipes: { ...BOOK.recipes, me_orders: { ...BOOK.recipes.me_orders, toAsk: [], toTake } },
});

/* **EVERY NUMBER HERE IS ONE HIS BOOK DOES NOT USE, AND THAT IS THE POINT.**
 * His orders recipe waits 35, shuts for 30 and tries 6 times. A walk that
 * ignored the recipe and carried those three numbers of its own would pass every
 * check written against them and fail nothing. So nothing below uses one:
 * eleven seconds, three seconds, twice, and seven seconds of patience.
 * `extension/recipes.test.js` drives his real book with his real numbers. */
const ODD = { patience: 7, times: 2, after: 3, waitFor: 11 };

{
  /* **THE WALK REALLY PASSES THE TIME, AND LOOKS AT NOTHING WHILE IT DOES.** A
   * `wait` that quietly did nothing would leave a recipe reading as though it
   * had waited for the platform to finish, and reloading the page instantly --
   * which is the fault it exists to fix, wearing the fix's own name.
   *
   * **THE STEP BEFORE IT LOOKS FOR SOMETHING, and it is there so this can go
   * red.** With the wait first in the list, "it looked at nothing before it" is
   * true of any wait at all -- there was nothing before it to look with. Sat
   * between two lookups, a wait that peeked at the page shows up. */
  const portal = aPortal();
  const got = await aWalk(portal, bookWhere([
    step({ do: 'wait-for', find: find('Ready'), why: 'waiting for the page to draw' }),
    step({ do: 'wait', patience: ODD.waitFor, why: 'waiting while the platform builds the file' }),
    step({ do: 'take-file', find: find('Download'), why: 'taking the finished file' }),
  ]))('me_orders', DAY);
  check('a step that only waits waits, and for exactly as long as the recipe says',
    got.state === LANDED && portal.waited.length === 1 && portal.waited[0] === ODD.waitFor);
  check('and it looked at nothing while it did, because there was nothing to look at',
    portal.whatHappened.join(' -> ').includes(
      `found Ready -> waited ${ODD.waitFor} -> found Download`));
}

{
  /* **A FILE THAT IS NOT IN THE LIST YET IS STILL FETCHED.** Meesho draws that
   * list as the download menu opens, so an open menu shows what was ready at
   * that moment and never changes -- five minutes of looking at it is five
   * minutes of looking at the same picture. The reference shuts it by clicking
   * where nothing is, leaves it shut, looks the opener up again and presses it
   * once. */
  const portal = aPortal({ appearsAfterReopens: 2 });
  const got = await aWalk(portal, bookWhere([
    step({
      do: 'take-file', find: find('Download'), patience: ODD.patience,
      why: 'taking the finished file',
      lookAgain: { by: find('Download Orders Data'), times: ODD.times, after: ODD.after },
    }),
  ]))('me_orders', DAY);
  check('a file not in the list yet is still fetched, by shutting the menu and opening it again',
    got.state === LANDED);
  /* **THE ORDER IS THE CHECK, AND IT IS THE REFERENCE'S ORDER, ALL FOUR PARTS OF
   * IT.** Shut it, wait while it is shut, look the opener up AGAIN, press it
   * once. A round that waited on the OPEN menu would read "clicked Download
   * Orders Data -> waited 3 -> clicked away" and match none of this; so would a
   * round that pressed the opener twice and shut nothing; and so would one that
   * pressed at the opener without looking for it first. */
  check('and each round was: clicked away, left shut, looked again, opened again',
    portal.whatHappened.join(' -> ').split(
      `clicked away -> waited ${ODD.after} -> found Download Orders Data`
      + ' -> clicked Download Orders Data'
    ).length - 1 === ODD.times);
  /* **AND THE STAND-IN COUNTED THE SHUTTING, NOT THE CLICKING.** Its list only
   * reappears once the menu has genuinely been shut and opened again, which is
   * why a loop that pressed the opener twice cannot reach this line at all. */
  check('and the menu really was shut and reopened, not merely pressed at',
    portal.clickedAway === ODD.times && portal.reopened === ODD.times);
  check(`and how long it was left shut is the recipe's, not a number inside the walk`,
    portal.waited.length === ODD.times && portal.waited.every((one) => one === ODD.after));
  /* **AND THAT STEP'S OWN PATIENCE WENT TO BOTH ITS LOOKUPS** -- the one for the
   * file and the one that checks the opener is still there. */
  check(`and the patience on both lookups is the recipe's too`,
    portal.patienceTold.filter(([call]) => call === 'find')
      .every(([, one]) => one === ODD.patience));
}

{
  /* **AND IT GIVES UP.** A menu reopened until morning holds the night on one
   * report, and every report behind it goes unfetched. */
  const portal = aPortal({ appearsAfterReopens: 99 });
  const got = await aWalk(portal, bookWhere([
    step({
      do: 'take-file', find: find('Download', { called: 'the download menu' }),
      patience: ODD.patience, why: 'taking the finished file',
      lookAgain: { by: find('Download Orders Data'), times: ODD.times, after: ODD.after },
    }),
  ]))('me_orders', DAY);
  check('a file that never appears is a failure, not a menu reopened all night',
    got.state === FAILED);
  check('and it was tried as many times as the recipe says, no more',
    portal.clickedAway === ODD.times && portal.waited.length === ODD.times);
  check('and the failure names the thing in the words a person reads',
    got.say.includes('the download menu'));
  check('and it carries what the step was for, not a bare "nothing matched"',
    got.say.includes('taking the finished file'));
}

{
  /* **THE OPENER IS LOOKED FOR BEFORE IT IS PRESSED, AND IF IT HAS GONE THIS
   * STOPS.** The reference does exactly this (`if (!dlDropdown2) ... break`).
   * Without it the click throws straight past every failure this walk writes,
   * and the seller is told a control could not be found with no word of what was
   * being attempted -- the bare "button not found" that cost this project a
   * month. The stand-in takes the opener away the moment the menu is shut, and
   * throws at a click aimed at it, exactly as the real door does. */
  const portal = aPortal({ appearsAfterReopens: 99, openerGoesWhenShut: true });
  const got = await aWalk(portal, bookWhere([
    step({
      do: 'take-file', find: find('Download', { called: 'the download menu' }),
      patience: ODD.patience, why: 'taking the finished file',
      lookAgain: { by: find('Download Orders Data'), times: ODD.times, after: ODD.after },
    }),
  ]))('me_orders', DAY);
  check('an opener that has gone ends the walk rather than throwing out of it',
    got.state === FAILED);
  check('and it stops at the first round rather than shutting a menu that is not there again',
    portal.clickedAway === 1);
  check('and the failure still carries what the step was for',
    got.say.includes('taking the finished file'));
}

check(`nothing above ended by throwing rather than by answering -- ${THREW}`, THREW.length === 0);

{
  /* **THE TWO SIZE LIMITS ARE HELD TO EACH OTHER (A33R).** `walk.TOO_BIG_TO_CARRY`
   * says in its own words that it is "the same number `catch-blob.TOO_BIG`
   * uses", and nothing compared them: an independent reviewer changed one to
   * 8 MB and every JavaScript check in this extension stayed green. That is
   * `drive.js`'s own rule met again -- a rule SPELT differently in two places is
   * a bug nobody will ever find. */
  check('the size the walk will carry is the size the catcher will catch',
    TOO_BIG_TO_CARRY === TOO_BIG);
}

const EXPECTED = 219;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
