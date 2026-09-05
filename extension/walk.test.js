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
  daysBefore,
  theWalk,
  whatIsCovering,
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
        step({ do: 'pick-range', rangeDays: 2, why: "setting the two-day range Flipkart insists on" }),
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
};

/* ------------------------------------------------------- a stand-in portal */

function aPortal(how = {}) {
  const it = {
    went: [], clicked: [], ranges: [], stepsSeen: 0, patienceTold: [], tookFile: 0,
    handedOver: [], turns: 0,
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
      if (how.matches && what in how.matches) return how.matches[what];
      /* **A PROMOTION HIDES WHAT IS UNDERNEATH IT.** That is what makes a
       * covering worth reporting at all: the lookup fails, and the reason is
       * not that the button was renamed. A panel the recipe opened itself does
       * NOT hide anything -- it contains the very thing being looked for --
       * which is why `ownMenu` below leaves this alone. */
      const after = how.coveredAfter;
      const covered = how.covered || (after !== undefined && it.stepsSeen > after);
      return covered ? 0 : 1;
    },
    async click(kind, what) {
      it.clicked.push(what);
    },
    async pick_range(from, to, patience) {
      it.ranges.push([from, to]);
      it.patienceTold.push(['pick_range', patience]);
    },
    async take_file(patience) {
      it.tookFile += 1;
      it.patienceTold.push(['take_file', patience]);
      if (how.builtInPage) return null;
      if (how.emptyFile) return new Uint8Array(0);
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
      const walking = theWalk({ door: portal.door, book, say: (line) => SAID.push(line) });
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
  check('and it says so in words a person reads', got.say === 'Landed 5 bytes.');
  /* **THE ANSWER CARRIES EVERY FIELD, ALWAYS.** A field that is simply absent
   * and a field that is empty read the same to a person and differently to the
   * runner, which asks all of them. */
  check('the answer names the report it is about', got.reportId === 'me_orders');
  check('and the day it is about', got.dataDate === DAY);
  check('and carries a file name, empty here because none was given',
    'fileName' in got && got.fileName === null);
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
  check('and every step said what it was doing', SAID.length > 0);
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
  const walking = theWalk({ door: aPortal().door, book: BOOK, say: () => {} });
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
  /* The walk cannot be built without its three parts. */
  const refused = (fn) => { try { fn(); return ''; } catch (e) { return e.message; } };
  check('a walk with no door is refused',
    refused(() => theWalk({ book: BOOK, say: () => {} })).includes('door to the page'));
  check('a walk with no recipes is refused',
    refused(() => theWalk({ door: {}, say: () => {} })).includes('book of recipes'));
  check('a walk with nowhere to say what it is doing is refused',
    refused(() => theWalk({ door: {}, book: BOOK })).includes('say what it is doing'));
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
  const walking = theWalk({ door: portal.door, book: BOOK, say: () => {} });
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
  const walking = theWalk({ door: portal.door, book: BOOK, say: () => {} });
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
  const walking = theWalk({ door: portal.door, book: bent, say: () => {} });
  const got = await walking('me_two_pages', DAY, { panel: PANEL, startAt: 4 });
  check('a bad step before the resume point is still a refusal, not skipped past',
    got.state === FAILED && got.say.includes('This recipe is wrong'));
}

check(`nothing above ended by throwing rather than by answering -- ${THREW}`, THREW.length === 0);

const EXPECTED = 145;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
