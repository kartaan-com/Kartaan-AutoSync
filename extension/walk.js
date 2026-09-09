/* Walking one report's recipe, step by step, and saying what came of it.
 *
 * **THIS IS THE HALF D107 MOVED.** The deciding is still Python -- which reports
 * exist, what to look for on each page, what a failure is called and what it
 * means. **None of that is written here.** It arrives as `book`, generated out of
 * `autosync/recipes.py` and `autosync/browser.py` by `tools/export_recipes.py`,
 * never edited by hand. What is here is only the walking, and the walking has to
 * be here because the Python cannot reach this page: it runs on a schedule in the
 * seller's own GitHub Actions and this runs in the seller's Chrome.
 *
 * **AND IT RUNS IN THE PAGE, NOT IN THE BACKGROUND, and that is Chrome's rule
 * rather than a preference.** Chrome shuts an idle service worker down after
 * thirty seconds. A Meesho orders export takes up to five minutes to build and
 * the recipe says so. A walk living in the background would be killed a tenth of
 * the way through, every time.
 *
 * **BUT A WALK IS BIGGER THAN ONE PAGE, AND FOR THE SAME KIND OF REASON (D200).**
 * Its first step is to GO somewhere, and going somewhere destroys the page it is
 * running in. `doors.js` has said so in its own header from the beginning --
 * "going somewhere tears down whatever is running in the old page" -- and
 * nothing here reconciled that with the walk living in the page. Three walks
 * died on his own Meesho panel on 5 September saying "the message channel closed
 * before a response was received", which is that teardown seen from the other
 * side.
 *
 * **SO A WALK IS A SEQUENCE OF TURNS, ONE PER PAGE.** A `go` ends the turn: the
 * walk says which step comes next, the background writes that number where
 * neither the page nor the worker can lose it, and the page Chrome draws next
 * asks for it and carries on. The reference has worked this way for months --
 * its own `goToPage` returns false meaning "I have navigated; the reload will
 * re-fire me", and the job it is walking lives in the background, never in the
 * page.
 *
 * **IT ANSWERS THE SAME FOUR WORDS THE AMAZON DOOR ANSWERS.** That is the whole
 * of D100: one report list, one log, one board, and the door a detail underneath.
 * A report moving to an API is one word in the report list and nothing here
 * changes at all.
 *
 * **THE RULES BELOW ARE NOT NEW.** Every one was paid for by a real failure and
 * every one is already checked in Python. They are carried across one at a time,
 * each with the check that proves it -- not re-derived.
 */

/* The same four words, spelt the same. A fifth spelling of "it worked" is a
 * report the runner cannot read. */
export const LANDED = 'landed';
export const NOTHING_TO_FETCH = 'nothing-to-fetch';
export const STILL_WAITING = 'still-waiting';
export const FAILED = 'failed';

/* **WHAT A WALK SAYS WHEN IT HAS NOT FINISHED, AND IT IS DELIBERATELY NOT ONE OF
 * THE FOUR WORDS ABOVE.** A walk now spans several pages -- going somewhere ends
 * the page's turn -- so there has to be a way of saying "the walk is alive and
 * somewhere else now" that the runner can never mistake for an outcome.
 *
 * **IT IS SAID WITH NO `state` AT ALL, and that is the safety.** Everything the
 * runner reads asks for `state` first. A fifth spelling of "it worked" is a
 * report the runner cannot read; a thing with no `state` is a thing the runner
 * cannot read AS an outcome, which is what is wanted. It never leaves the page
 * half: `content.js` takes it and says nothing to anybody. */
export const CARRYING_ON = 'carrying-on';

function carryingOn(at) {
  return { carryingOn: CARRYING_ON, at };
}

/** Is this a walk that has moved to another page rather than an outcome? */
export function hasNotFinished(answer) {
  return Boolean(answer && answer.carryingOn === CARRYING_ON);
}

/* What a step can be. These cross the wire in every recipe, so they are the
 * Python spellings exactly. */
export const GO = 'go';
export const CLICK = 'click';
export const WAIT_FOR = 'wait-for';
export const PICK_RANGE = 'pick-range';
export const TAKE_FILE = 'take-file';
/* **THE ONE STEP THAT LOOKS AT NOTHING.** Every other kind of waiting here waits
 * for something to appear. Meesho builds an orders export on its own servers and
 * the page it was asked from does not change at all while it happens, so there
 * is nothing to look at -- only time to pass. `autosync/browser.py` holds the
 * whole reason under `WAIT`, and the number lives in the recipe. */
export const WAIT = 'wait';

/* What went wrong, by name. **Every one of these is its own failure and that is
 * the point.** The reference had one -- "button not found" -- and it covered all
 * of them, so a month of diagnosis went at the wrong thing because "it is
 * underneath a dialog" and "it has been renamed" arrived wearing the same words.
 * The sentence each of them means is NOT here: it comes from the book. */
export const FOUND_NOTHING = 'found-nothing';
export const FOUND_SEVERAL = 'found-several';
export const COVERED_UP = 'covered-up';
export const BUILT_IN_THE_PAGE = 'built-in-the-page';

/** How big a file is worth carrying across to the browser half at all.
 *
 *  **THE SAME NUMBER `catch-blob.TOO_BIG` USES, AND `extension/walk.test.js`
 *  HOLDS THE TWO TO EACH OTHER (A33R).** Written here as its own literal and
 *  nothing comparing them, it could be changed on one side and every one of the
 *  JavaScript checks stayed green -- driven, and that is `drive.js`'s own rule
 *  met again: a rule SPELT differently in two places is a bug nobody finds.
 *
 *  **AND IT IS SAID HERE AT ALL BECAUSE THE TWO WAYS A FILE ARRIVES HAD
 *  DIFFERENT ANSWERS.** A file the page builds inside
 *  itself is refused above this by the catcher; a file fetched back from an
 *  address was refused by nothing at all, and the bytes cross to the background
 *  as text -- one number and one comma per byte, four times their own size.
 *  A stock file for a large catalogue is a few hundred kilobytes; his real
 *  files measure one to a hundred. */
export const TOO_BIG_TO_CARRY = 40 * 1024 * 1024;

/* How much of the page to keep when something could not be found. The same 400
 * the Python keeps: enough to see what was really there, small enough that a log
 * stays readable and carries nothing of the seller's worth hiding. */
const PAGE_SNIPPET = 400;

/** The kind of problem that is nobody's report's fault.
 *
 *  **ITS OWN KIND, because every report after it hits the same wall.** Calling
 *  each of them broken buries the one thing that actually needs doing -- and the
 *  reference's queue died on the spot, abandoning everything behind it.
 */
export class NeedsSigningIn extends Error {}

/** What the page looked like, trimmed. Never absent. */
export function capture(pageText) {
  return String(pageText ?? '').replace(/\s+/g, ' ').trim().slice(0, PAGE_SNIPPET);
}

/**
 * Is something sitting over the page?
 *
 * **ASKED BEFORE EVERY CLICK, NOT AFTER ONE FAILS.** Asked afterwards, the
 * failure has already been written down as "button not found" -- which is exactly
 * what happened, for a month, to three Meesho reports whose buttons were there
 * the whole time.
 *
 * **IT ASKS WHETHER ANYTHING WOULD SWALLOW A CLICK, NOT HOW BIG ANYTHING IS.**
 * Judged by size, the download menu the recipe opens on purpose -- 232 x 196 on
 * his own panel -- and the promotion that blocks it -- 414 x 330 -- are four
 * pixels apart in one direction. What separates them is that the promotion is
 * laid over the whole window and the menu is not.
 */
export function whatIsCovering(overlays) {
  const seen = overlays || [];
  const blocking = seen.find((one) => one.blocks);
  if (!blocking) return null;
  /* **A BACKDROP HAS NO WORDS OF ITS OWN.** It is a sheet laid over everything,
   * and the words are on whatever sits on top of it. Reported without them, a
   * failure says "something is covering the page" and nothing about WHICH
   * something -- and recognising the same promotion again is the whole reason
   * the words are kept at all. */
  const wordsOf = (one) => String(one.text ?? '').replace(/\s+/g, ' ').trim().slice(0, 120);
  if (wordsOf(blocking)) return wordsOf(blocking);
  const onTop = seen.find((one) => one !== blocking && wordsOf(one));
  return onTop ? wordsOf(onTop) : '';
}

function anAnswer(state, reportId, dataDate, rest = {}) {
  return {
    state,
    reportId,
    dataDate,
    fileName: null,
    size: 0,
    say: '',
    theirId: null,
    /* **THE EVIDENCE TRAVELS WITH THE FAILURE.** Written somewhere else to be
     * correlated later is written somewhere nobody ever looks. */
    pageWas: '',
    ...rest,
  };
}

/**
 * Everything wrong with a step, or nothing.
 *
 * **A BAD RECIPE IS A FAULT IN THE PRODUCT, NOT IN THE PORTAL**, and it has to
 * say so -- otherwise it reads as the platform having changed and sends somebody
 * to look at Meesho.
 */
export function whyStepIsRefused(step) {
  if (!step || typeof step !== 'object') return 'That is not a step.';
  if (![GO, CLICK, WAIT_FOR, PICK_RANGE, TAKE_FILE, WAIT].includes(step.do)) {
    return `"${step.do}" is not something this door knows how to do.`;
  }
  if (step.do === GO && !step.address) return 'A step that goes somewhere has to say where.';
  if ((step.do === CLICK || step.do === WAIT_FOR) && !step.find) {
    return `A ${step.do} step has to say what to look for.`;
  }
  if (step.do === WAIT && step.find) {
    /* **A WAIT AND A WAIT-FOR ARE NOT THE SAME STEP.** One passes time; the other
     * watches the page. Written with something to look for, a wait would pass its
     * time and never look at it, and the recipe would read as though it had
     * waited FOR that thing. */
    return 'A step that only waits has nothing to look for. Waiting for something is a wait-for.';
  }
  if (step.lookAgain) {
    /* **WHAT TO SHUT AND OPEN AGAIN BETWEEN LOOKS.** Meesho draws its list of
     * finished exports as the download menu opens, so an open menu shows what was
     * ready at that moment and never changes. The same rules the Python holds. */
    if (step.do !== TAKE_FILE) {
      return 'Only a step that takes a file can close and open something again between looks.';
    }
    if (!step.lookAgain.by || !step.lookAgain.by.what) {
      return 'Looking again has to say what to close and open again.';
    }
    if (!(Number(step.lookAgain.times) >= 1)) {
      return 'Looking again no times at all is not looking again.';
    }
    if (!(Number(step.lookAgain.after) >= 1)) {
      return 'Looking again has to leave it closed for some time, or nothing is redrawn.';
    }
  }
  if (step.find && !step.find.what) return 'A way of finding something has to say what to look for.';
  if (!(Number(step.patience) > 0)) return 'A step that waits no time at all cannot succeed.';
  if (!step.why) {
    /* **NOT DECORATION.** A failure says what was being attempted, and without
     * this it can only say what could not be found -- which is how a month of
     * "button not found" told nobody the button was underneath a dialog. */
    return 'A step has to say what it is for, so a failure can say what was being attempted.';
  }
  return null;
}

/**
 * Why this is not a day a walk can be given, or null.
 *
 * **THE DAY IS THE ONE THING IN A WALK THAT NOBODY HERE WROTE.** It arrives as
 * an argument to `startTheNight`, is carried through the night's record and the
 * background's messages, and comes out the far end in TWO places that both
 * matter: the address a step goes to (`{day}`, filled in by `filledIn`) and the
 * NAME the file is put away under (`theFileName`). Until this existed neither
 * asked anything of it -- `theFileName` checked only that it was not empty.
 *
 * **AND THE NAME IS THE HALF THAT LOSES THE SELLER'S DATA IN SILENCE.**
 * `05/09/2026` makes `me_orders_05/09/2026.csv`; `landing.data_date_in` reads a
 * day back out of a name with `(\d{4}-\d{2}-\d{2})` and answers None for that
 * one. **A file whose name has no day in it is a file no reader can ever
 * reach** -- `landing.undated` exists because seven real files sat like that for
 * six weeks. So the day is refused HERE, before one of the seller's rationed
 * report requests is spent on it, rather than after the bytes are already in
 * their Drive under a name nothing will ever open.
 *
 * **ASKED OF THE VALUE, NOT OF ITS SHAPE ALONE.** `2026-02-31` matches the
 * pattern and is not a day, so it is built and read back -- the same question
 * `landing.data_date_in` asks with `date.fromisoformat`.
 */
export function whyTheDayIsRefused(dataDate) {
  /* **ASKED OF EXACTLY WHAT THE CALLER WILL USE, never of a tidied copy of it
   * (A33R).** The first version of this trimmed the value before testing it, so
   * `" 2026-09-08 "` came back as a good day and `filledIn` then put the spaces
   * straight into the address a step goes to. **A guard that answers about a
   * value nobody uses is the shape of fault this whole session is about.** A day
   * with anything round it is not a day this run wrote, and it is refused rather
   * than tidied -- tidying here would leave the caller still holding the untidy
   * one. */
  const day = String(dataDate ?? '');
  if (!day) {
    return 'This walk was not told which day it is fetching. A file put away without one '
      + 'would be under a name the nightly run cannot read a day out of, and never read.';
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) {
    return `"${day}" is not a day written the way the nightly run reads one back out of a `
      + 'file name (YYYY-MM-DD), so a file put away under it would never be read.';
  }
  const [y, m, d] = day.split('-').map(Number);
  const built = new Date(Date.UTC(y, m - 1, d));
  if (built.getUTCFullYear() !== y || built.getUTCMonth() !== m - 1 || built.getUTCDate() !== d) {
    return `"${day}" is written the right way round but is not a real day.`;
  }
  return null;
}

/**
 * The walk.
 *
 * `door` is the ten calls from `driver.js`. `book` is what came out of the
 * Python. `say` is how a line reaches the run log.
 */
export function theWalk({
  door, book, say,
  /* **WHERE THE BYTES GO, AND UNTIL NOW THERE WAS NOWHERE (D171 again).**
   *
   * The walk took the file, counted it, answered LANDED and **dropped the bytes
   * on the floor.** `extension/drive.js` -- 24 KB, 66 checks, finished and
   * proved against a stand-in Drive -- was imported by nothing but its own test
   * file. So not one byte has ever reached a real Drive from the browser half,
   * and **that is why a perfectly configured seller would see Amazon and
   * nothing else**: `me_orders` and `fk_orders` are browser-sourced, and the
   * nightly run reads a folder the browser never put anything in.
   *
   * **IT IS HANDED IN, LIKE `go` AND `take_file`, AND FOR THE SAME REASON.**
   * Putting a file in Drive needs `chrome.identity`, which a content script
   * cannot reach at all -- so it belongs to the background half, and this side
   * only asks. Handed in, the whole of the rule below is checked with no
   * browser, no extension, no Google account and no internet.
   *
   * **AND IT IS REQUIRED, NOT OPTIONAL.** A walk built without it would fetch
   * the seller's report, report LANDED, and put it nowhere -- which is exactly
   * the state this closes, and it would look identical to working. */
  putTheFile,
  /* **ARMING THE CATCHER FOR THE NEXT FILE THE PAGE BUILDS INSIDE ITSELF (A44).**
   *
   * **HANDED IN LIKE `putTheFile`, AND NOT ON THE DOOR, FOR THE REASON THE DOOR
   * SAYS AT THE TOP OF ITSELF.** The door is the ten calls the Python side
   * makes, spelt the way the Python spells them -- and the Python has no catcher
   * to arm, because a file built inside a page only exists in a browser. A ninth
   * call would be a spelling the two halves do not share, which is the fault this
   * project has been caught by four times.
   *
   * **AND IT IS REQUIRED, NOT OPTIONAL, WHICH IS SECURITY RATHER THAN
   * TIDINESS.** A walk built without it never arms for the file it is about to
   * ask for, so a file the page builds inside itself never arrives at all -- and
   * that failure wears the clothes of a portal that renamed a button, which is a
   * month of looking in the wrong place. */
  armTheCatcher,
}) {
  if (!door) throw new Error('A walk needs a door to the page.');
  if (!book || !book.recipes) throw new Error('A walk needs the book of recipes.');
  if (typeof say !== 'function') throw new Error('A walk needs somewhere to say what it is doing.');
  if (typeof putTheFile !== 'function') {
    throw new Error(
      'A walk needs somewhere to put the file it takes. Without one it would fetch the '
      + "seller's report and drop it, and report that it had landed."
    );
  }
  /* Asked last, so the refusals above keep their own words. */
  if (typeof armTheCatcher !== 'function') {
    throw new Error(
      'A walk needs a way of arming the catcher for the next file the page builds inside '
      + 'itself. Without one, a file that only ever exists inside the page would never arrive.'
    );
  }

  function meaningOf(kind) {
    /* **NOT INVENTED HERE.** If the book has no sentence for a failure, that is a
     * fault in what was generated, and saying so is better than making up a
     * reassuring sentence nobody can trace. */
    return book.whatItMeans && book.whatItMeans[kind]
      ? book.whatItMeans[kind]
      : `There is no explanation in the recipe file for "${kind}".`;
  }

  async function gaveUp(reportId, dataDate, { kind, lookingFor, doing, matches = 0 }) {
    const pageWas = capture(await door.page_text());
    const said = kind === FOUND_SEVERAL
      ? `${doing}: ${matches} things match "${lookingFor}". ${meaningOf(kind)}`
      : `${doing}: could not find "${lookingFor}". ${meaningOf(kind)}`;
    return anAnswer(FAILED, reportId, dataDate, { say: said, pageWas });
  }

  /** The seller's own panel, and the day being fetched, put into a step.
   *
   *  **THE DAY IS WRITTEN THE WAY THE PLATFORM WRITES IT**, which the recipe
   *  says, because a row on his returns page reads `25 Aug 2026` and no two
   *  platforms agree on that.
   */
  function filledIn(step, panel, dataDate, dayInWords) {
    /* **EVERY OCCURRENCE, NOT THE FIRST (cycle 46, R6#15).**
     *
     * What stood here said `{day_in_words}` had to be filled before `{day}`
     * because the short name sits inside the long one. **It does not** --
     * `{day_in_words}` has no `{day}` in it, so the order never mattered and
     * the comment was describing a danger that does not exist. A reason that is
     * not true is worse than no reason: the next person keeps the ordering,
     * believes it is load-bearing, and never looks at what is.
     *
     * **What IS load-bearing is this line.** Filling by name replaces the FIRST
     * one only, so a recipe naming the same day twice -- a page that wants it in
     * the address and again in the row it looks for -- would go out half-filled
     * and find nothing, on the platform, at night, with no one watching. No
     * recipe does that today. Nothing stopped one, and a recipe is data, added
     * without touching this file. */
    const put = (into) => String(into || '')
      .split('{panel}').join(panel || '')
      .split('{day_in_words}').join(dayInWords || dataDate)
      .split('{day}').join(dataDate);
    return {
      ...step,
      address: put(step.address),
      find: step.find ? { ...step.find, near: put(step.find.near) } : step.find,
    };
  }

  function stepsFor(reportId, panel, collecting) {
    const recipe = book.recipes[reportId];
    if (!recipe) {
      throw new Error(`"${reportId}" is not a report the browser door knows how to fetch.`);
    }
    const twoPhase = Boolean(recipe.toAsk && recipe.toAsk.length);
    const steps = twoPhase && !collecting ? recipe.toAsk : recipe.toTake;
    if (steps.some((one) => String(one.address || '').includes('{panel}')) && !panel) {
      /* **THE PANEL NAME IS THE SELLER'S OWN AND IS NEVER IN THE PRODUCT.** The
       * reference holds one supplier's slug in its own source; a product that
       * ships to every seller cannot. */
      throw new Error(
        "This report needs the seller's own panel name, which is in the address of their supplier "
        + "panel. It is the seller's own data and is never written into the product."
      );
    }
    return { recipe, twoPhase, steps };
  }

  /** What to call a lookup that found nothing: covered up, or simply not there.
   *
   *  **ASKED ONLY WHEN THE LOOKUP HAS ALREADY FAILED, and that is a correction
   *  made on 2026-08-28 with the evidence in front of it.** It used to be asked
   *  BEFORE every click, on the reasoning that a covering has to be named before
   *  a failure is written down as "button not found". Two things seen on his own
   *  panel say otherwise:
   *
   *    - **the panel a recipe opens ON PURPOSE sits on a full-screen backdrop
   *      too.** Meesho's "Bulk Stock Update" panel measures the whole window and
   *      contains the very Download the recipe is about to press. Asked
   *      beforehand, the door would refuse to carry on because of a panel it had
   *      just opened itself;
   *    - **and a covering never actually stopped anything here.** A click is
   *      sent straight to the thing being clicked, so a sheet laid over the page
   *      does not intercept it the way it intercepts a person's mouse.
   *
   *  So the covering is not what stops a step -- it is what EXPLAINS one that
   *  stopped. Asked in this order, the failure still says "something is covering
   *  the page" rather than "button not found", which was the whole point, and a
   *  panel the recipe opened costs nothing.
   */
  async function whyNothingWasFound(step, reportId, dataDate) {
    const covering = whatIsCovering(await door.overlays());
    /* Only ever asked about a step that was looking for something: a click and a
     * wait are refused without one, and the take-file step asks this only inside
     * its own lookup. */
    const name = step.find.called || step.find.what;
    return gaveUp(reportId, dataDate, {
      kind: covering !== null ? COVERED_UP : FOUND_NOTHING,
      lookingFor: name,
      doing: step.why,
    });
  }

  async function takeTheFile(step, reportId, dataDate) {
    if (step.find) {
      let many = await door.find(step.find.how, step.find.what, step.find.exact, step.patience, step.find.near);
      /* **NOT THERE YET IS NOT THE SAME AS NOT THERE, WHEN IT LIVES IN A MENU.**
       *
       * This step used to wait 300 seconds on an open menu and call that
       * patience. **Meesho draws its list of finished exports AS the download
       * menu opens**, so an open menu shows whatever was ready at that moment and
       * never changes -- five minutes of looking at it is five minutes of looking
       * at the same picture. The only way to see a newer list is to shut the
       * menu, leave it shut while the platform finishes, and open it again.
       *
       * **THE REFERENCE HAS DONE EXACTLY THIS EVERY NIGHT FOR MONTHS**
       * (`content/meesho.js:860-878`): six times, thirty seconds apart. How many
       * and how long are the recipe's, because they are Meesho's; that a list can
       * be drawn once and go stale is the page's business and is here.
       *
       * **AND THE GESTURE IS THE REFERENCE'S OWN, NOT ONE DERIVED FROM IT.** It
       * shuts the menu by clicking where nothing is (`document.body.click()`,
       * `content/meesho.js:865`) and then looks the opener up afresh and presses
       * it once. Pressing the opener twice instead would assume it toggles --
       * and nothing here can settle whether Meesho's does. If it does not, both
       * presses do nothing, the list is never redrawn, and six rounds of this
       * are three minutes of a walk that looks exactly like one that works.
       *
       * **AND IF THE OPENER HAS GONE, THIS STOPS RATHER THAN THROWING.** The
       * reference does the same (`if (!dlDropdown2) ... break`). Clicking at
       * something that is not there throws past every failure this walk writes,
       * and the seller is left with a bare "nothing matches" and no word of what
       * was being attempted -- the shape that cost this project a month.
       * Stopping here falls into `whyNothingWasFound` below, which carries
       * `step.why` and the page with it. */
      const again = step.lookAgain;
      for (let tried = 0; many === 0 && again && tried < Number(again.times); tried += 1) {
        await door.click_away();
        await door.wait(Number(again.after));
        const stillThere = await door.find(
          again.by.how, again.by.what, again.by.exact, step.patience, again.by.near
        );
        if (stillThere === 0) break;
        await door.click(again.by.how, again.by.what, again.by.exact, again.by.near);
        many = await door.find(step.find.how, step.find.what, step.find.exact, step.patience, step.find.near);
      }
      if (many === 0) {
        return { failed: await whyNothingWasFound(step, reportId, dataDate) };
      }
      if (many > 1) {
        return { failed: await gaveUp(reportId, dataDate, {
          kind: FOUND_SEVERAL, lookingFor: step.find.called || step.find.what,
          doing: step.why, matches: many,
        }) };
      }
      /* **THE CATCHER IS ARMED HERE, AND NOWHERE EARLIER (A44).**
       *
       * **WHAT WAS WRONG WITH EARLIER.** `content.js` armed it at the start of
       * every walk turn, before the first step ran -- and the file is not asked
       * for until the last one. In between, the portal draws itself (10 to 25
       * seconds, measured on his own Flipkart account) with the catcher sitting
       * armed the whole time. A portal page is somebody else's code carrying
       * somebody else's adverts, and **any script on it can call
       * `URL.createObjectURL` with a file of its own and be caught** -- it does
       * not have to stand in front of anything, it stands beside it. The catcher
       * is spent on the first file that comes past, `content.js` takes the first
       * message it accepts, and the genuine Download that follows is ignored.
       * Those bytes go on to `land-the-file`, `drive.js` REPLACES the genuine
       * file of that day under the genuine report name, and the Python reads it
       * into the seller's ledger as real sales. **Not a crash: wrong money in a
       * seller's books, silently, under a real report name.**
       *
       * **WHY THIS IS THE LAST HONEST MOMENT.** Every recipe in this product
       * takes its file in a step that does its own lookup and its own click, and
       * that click is what makes the page build the file. So this is after the
       * lookup -- which may wait out its whole patience on a slow morning -- and
       * immediately before the click. There is no later moment, and an earlier
       * one is only a wider window.
       *
       * **ARMING AFRESH ALSO THROWS AWAY ANYTHING ALREADY CAUGHT.**
       * `content.js` clears what it is holding and starts waiting for a new
       * secret, so a file caught during the draw is not merely un-believed --
       * it is gone. That is the half of this that actually matters.
       *
       * **AND THIS IS NOT A FIX. IT IS A NARROWING, AND IT IS WRITTEN DOWN AS
       * ONE.** A script that simply keeps calling `URL.createObjectURL` is
       * caught the instant this arming lands, however close to the click it
       * happens -- the arming is a round trip to the background and the page's
       * own scripts run during it. **The hole is not closed and cannot be closed
       * from here**: `catch-blob.js` says in its own header that a page which has
       * replaced `window.postMessage` sees the genuine message, secret and all,
       * before `content.js` does. There is no pristine copy to be had in the
       * page's own world. `walk.test.js` pins the fault that is left, and the
       * check goes red the day it is really closed.
       *
       * **THERE IS NO CLOCK IN THIS, ON PURPOSE.** Believing a catch only within
       * some short time of the click would lose a genuine file on a real
       * seller's Meesho at nine in the morning, and would close nothing -- the
       * script above fires inside any window.
       *
       * **AND IT FAILS CLOSED, WHICH IS SAID RATHER THAN LEFT TO BE INFERRED.**
       * If this arming cannot be done -- the background half being restarted is
       * the ordinary reason -- `content.js` is left waiting for nothing and
       * refuses every message, including one the earlier arming would have
       * believed. So a file the page builds inside itself is LOST rather than
       * taken on an older secret, and the report fails out loud. Falling back to
       * the older secret would be the one thing this change exists to stop. */
      await armTheCatcher();
      await door.click(step.find.how, step.find.what, step.find.exact, step.find.near);
    }

    const body = await door.take_file(step.patience);
    if (body === null || body === undefined) {
      /* **THE DOOR THAT HAS CLOSED.** The platform now builds the file inside the
       * page and hands over a handle that belongs to that page -- nothing can
       * fetch it a second time, and no amount of retrying changes that. */
      const gone = await gaveUp(reportId, dataDate, {
        kind: BUILT_IN_THE_PAGE, lookingFor: 'the file itself', doing: step.why,
      });
      const since = book.buildsInThePageSince && book.buildsInThePageSince[reportId];
      if (since) {
        /* **SAID WITH THE DAY IT STARTED**, so it reads as a known door closing
         * rather than as tonight's news. */
        gone.say += ` This has been happening to ${reportId} since ${since}.`;
      }
      return { failed: gone };
    }
    if (!body.length) {
      /* **PRESENCE IS NOT ARRIVAL.** A nought-byte file counted as arrived would
       * stop its day ever being fetched again. */
      return { failed: anAnswer(FAILED, reportId, dataDate, {
        say: 'The page produced a file with nothing in it, so nothing has been written.',
      }) };
    }
    /* **AND A SIGN-IN PAGE IS NOT A REPORT, WHICHEVER HALF FETCHED IT.**
     *
     * `doors.js` calls this the worst possible outcome in its own words: a portal
     * that has signed the browser out answers a file address with its sign-in
     * page, cheerfully, at 200 -- it is a file, it has a size, and everything
     * downstream believes the day arrived.
     *
     * **THE GUARD EXISTED AND SAT ON ONE OF THREE PATHS.** `content.js` applied
     * it only to its own fallback fetch; the background's fetch and the blob the
     * page catches went straight past it. That cost nothing while the bytes were
     * being dropped on the floor. **The moment they started reaching the
     * seller's Drive it became the difference between a clean failure and a
     * sign-in page filed as their day's report** -- so it is asked here, at the
     * one point every path passes through, rather than three times.
     *
     * **IT IS A GUARD, NOT THE ANSWER.** The Python half sniffs the real bytes
     * properly (`landing.the_file_that_matters`) and this half still has no
     * counterpart. Said rather than left to be assumed. */
    if (looksLikeAPage(body)) {
      return { failed: anAnswer(FAILED, reportId, dataDate, {
        size: body.length,
        say: `What came back is a web page, not a report -- the platform has almost `
          + `certainly signed this browser out. ${body.length} bytes were thrown away `
          + "rather than put in the seller's Drive as this day's report.",
      }) };
    }
    return { body };
  }

  /**
   * Walk one report, and answer what came of it.
   *
   * `askedAlready` is what a two-phase report was asked under. Given, this
   * collects rather than asking again -- **and on Flipkart that is not
   * politeness: its Reports Centre allows twenty requests a day**, and the
   * reference burned through them re-submitting reports that had worked, then
   * spent the rest of the day locked out.
   */
  return async function walk(reportId, dataDate, {
    panel = '', askedAlready = null, fileName = '', dayInWords = '',
    /* **WHERE TO PICK THE WALK UP, because the page that started it is gone.**
     * Nought on the first turn. After a `go`, the background holds the next
     * number and hands it to whichever page Chrome draws next. */
    startAt = 0,
  } = {}) {
    /* **THE DAY IS ASKED FIRST, BEFORE A REPORT IS SPENT.** It reaches the
     * address a step goes to and the name the file is put away under, and
     * nothing between here and Drive asks anything of it. Refused as this
     * report's own failure, the night writes it down and moves on -- the same
     * shape as a bad recipe two lines below. */
    const notADay = whyTheDayIsRefused(dataDate);
    if (notADay) return anAnswer(FAILED, reportId, dataDate, { say: notADay });

    let plan;
    try {
      /* **BOTH LOOKUPS INSIDE THE SAME GUARD.** A door answers; it does not throw
       * at its caller. Thrown, the runner would write a bare error as the reason
       * a seller's data is missing. */
      const recipe = book.recipes[reportId];
      const collecting = Boolean(askedAlready) || !(recipe && recipe.toAsk && recipe.toAsk.length);
      const found = stepsFor(reportId, panel, collecting);
      plan = {
        ...found,
        steps: found.steps.map((one) => filledIn(one, panel, dataDate, dayInWords)),
        collecting,
      };
    } catch (wrong) {
      return anAnswer(FAILED, reportId, dataDate, { say: wrong.message });
    }

    for (let at = 0; at < plan.steps.length; at += 1) {
      const step = plan.steps[at];
      const wrong = whyStepIsRefused(step);
      if (wrong) {
        return anAnswer(FAILED, reportId, dataDate, { say: `This recipe is wrong: ${wrong}` });
      }

      /* **THE STEPS AN EARLIER PAGE ALREADY WALKED ARE STILL READ, AND STILL
       * REFUSED IF THEY ARE WRONG -- they are simply not done again.** A recipe
       * being wrong is a fault in this product whichever turn notices it, and a
       * walk that resumed past the bad step would report the fault on some later
       * night and not on this one. What is skipped is the DOING, because it has
       * already been done in a page that no longer exists. */
      if (at < startAt) continue;

      /* **ASKED FIRST, EVERY STEP, AND IT IS NOT THIS REPORT'S FAULT.**
       *
       * **THIS IS ALSO WHAT CATCHES A SESSION THAT EXPIRED HALF WAY THROUGH A
       * WALK.** A walk now spans several pages, and the portal can sign the
       * seller out between any two of them -- the first step of the new page
       * asks again, before anything is clicked, and the answer is the same
       * "somebody has to sign in" it would have been at the start. */
      if (await door.needs_signing_in()) {
        throw new NeedsSigningIn(
          'The panel is asking to be signed in to. Nothing can be fetched from it until somebody '
          + 'does, and every report after this one would fail the same way.'
        );
      }

      /* **EVERY STEP THIS PAGE ACTUALLY WALKS SAYS WHAT IT IS ABOUT TO DO,
       * BEFORE IT DOES IT.**
       *
       * **HIS INSTRUCTION, 2026-09-09**, after a Meesho walk stopped at the date
       * step and said nothing at all: *"because it is opening in different
       * different tabs you will not be able to control that -- so better option
       * is you should make that report each step."*
       *
       * **BEFORE, NOT AFTER, AND THAT IS THE WHOLE POINT.** The one line that
       * existed sat under `CLICK` and ran once the click had SUCCEEDED, so the
       * step that never returns is exactly the step that never reports.
       *
       * **NOT EVERY STEP IN THE RECIPE -- every step THIS page walks.** It sits
       * below the `at < startAt` skip on purpose, so a walk resuming in a new
       * page does not announce again the steps an earlier page already did.
       * Said here because that placement is the one a later edit is most likely
       * to break.
       *
       * **WHERE THESE LINES GO, SAID PLAINLY: `console.info` in the service
       * worker, and NOWHERE ELSE.** Not the run's record, not storage, not the
       * seller's Drive. **Chrome evicts an idle service worker and the console
       * goes with it** -- so this is visibility while somebody is watching, and
       * it is NOT evidence available the next morning. The run's own record is
       * the piece of work that fixes that, and `worker.js` already says so.
       *
       * **THE STEP'S OWN NUMBER IS SAID TOO**, because a walk resumes at a
       * number after a page is torn down, and "step 4 of 10" is what makes two
       * halves of one walk readable as one walk. */
      say(`${reportId}: step ${at + 1} of ${plan.steps.length}, ${step.why}.`);

      if (step.do === GO) {
        /* **GOING SOMEWHERE ENDS THIS PAGE'S TURN, AND THAT IS THE WHOLE OF
         * D200.** The walk runs inside the portal's own page. Telling the
         * background to go somewhere destroys that page -- so there is no
         * "afterwards" here to continue in, and the `continue` that used to be
         * on this line could never have run. Three walks died on his own panel
         * with "the message channel closed before a response was received",
         * which is what a page being torn down mid-sentence looks like from the
         * other side.
         *
         * **SO THE PLACE IN THE WALK IS HANDED OVER BEFORE THE PAGE GOES**, and
         * the page that Chrome draws next asks for it and carries on from there.
         * The reference answers this the same way and has for months: its own
         * `goToPage` returns false meaning "I have navigated; the reload will
         * re-fire me", and the job it is walking lives in the background, not in
         * the page. */
        await door.go(step.address, step.patience, at + 1);
        return carryingOn(at + 1);
      }

      if (step.do === WAIT) {
        /* **NOTHING TO LOOK AT, ONLY TIME TO PASS.** The step after this one
         * loads the page again, and Meesho's list of finished exports is drawn as
         * that load happens -- so a page loaded before the file is built is a
         * page loaded without it, and no amount of patience further down can
         * recover a row that was never drawn. */
        await door.wait(step.patience);
        continue;
      }

      if (step.do === PICK_RANGE) {
        /* **A RANGE IS NOT ALWAYS ONE DAY.** Flipkart's Reports Centre needs the
         * start strictly before the end, so its smallest range is two days -- and
         * it names the row it produces by the END date, which is the day actually
         * being fetched. */
        await door.pick_range(daysBefore(dataDate, (step.rangeDays || 1) - 1), dataDate, step.patience);
        continue;
      }

      if (step.do === TAKE_FILE) {
        const got = await takeTheFile(step, reportId, dataDate);
        if (got.failed) return got.failed;
        /* **THE NAME IS THE PYTHON'S, NEVER THIS FILE'S.** The nightly run takes
         * the day out of the file NAME and refuses a file that has none, so a
         * name invented here is a file that reaches the seller's Drive and can
         * never be read out of it -- the folder simply fills up, silently.
         * `fileName` given by the caller still wins, because a caller that knows
         * better than the book is a caller that has been told. */
        const called = fileName || theFileName(book, reportId, dataDate);
        if (!called) {
          return anAnswer(FAILED, reportId, dataDate, {
            say: `There is nothing in the recipe file saying what ${reportId}'s file is `
              + 'called, so it has not been put anywhere. A file put away under a name the '
              + 'nightly run cannot read the day out of would never be read at all.',
          });
        }
        /* **HOW BIG IS WORTH CARRYING, AND NOTHING ASKED UNTIL NOW.** The bytes
         * do not go straight to Drive from here: they cross to the background
         * half as a message, and a message is turned into TEXT on the way --
         * `bytes: [...body]`, one number and one comma per byte, so a 40 MB
         * catch crosses as roughly 160 MB and nothing anywhere refused it.
         *
         * **THE CATCHER ALREADY REFUSES A FILE THIS BIG** (`catch-blob.TOO_BIG`)
         * and the take-file half does not, so one of the two ways a file arrives
         * was capped and the other was not. His real files are one to a hundred
         * kilobytes, so this has never fired -- which is exactly why it needs
         * writing down rather than leaving to be noticed. */
        if (got.body.length > TOO_BIG_TO_CARRY) {
          return anAnswer(FAILED, reportId, dataDate, {
            fileName: called,
            size: got.body.length,
            say: `${got.body.length} bytes came back for ${called}, which is more than the `
              + `${TOO_BIG_TO_CARRY} this can carry across to the browser half. Nothing has `
              + 'been put in the seller\'s Drive and the day is owed again.',
          });
        }
        /* **LANDED NOW MEANS IT REACHED THE SELLER'S DRIVE**, which is what the
         * word was always supposed to mean: `drive.js` says in its own header
         * that "a report that reached Drive and a report that reached the
         * browser are the same report, and the runner reads one list". Until
         * this line the walk said LANDED for the second of those.
         *
         * **AND A DRIVE THAT REFUSED IS THIS REPORT'S FAILURE, NOT A CRASH.**
         * Answered as a failure, the night writes it down, moves on, and the day
         * is fetched again -- nothing is marked, nothing is lost. */
        try {
          await putTheFile({ reportId, fileName: called, body: got.body });
        } catch (wrong) {
          return anAnswer(FAILED, reportId, dataDate, {
            fileName: called,
            size: got.body.length,
            say: `${got.body.length} bytes came back and could not be put in the seller's `
              + `Drive: ${(wrong && wrong.message) || wrong}`,
          });
        }
        return anAnswer(LANDED, reportId, dataDate, {
          fileName: called,
          size: got.body.length,
          say: `Landed ${got.body.length} bytes in the seller's Drive as ${called}.`,
        });
      }

      const many = await door.find(step.find.how, step.find.what, step.find.exact, step.patience, step.find.near);
      if (many === 0) {
        /* **ITS OWN NAMED FAILURE, decided after the lookup rather than before
         * it.** "Button not found" sent a month of diagnosis at a button that was
         * there all along, underneath a promotion -- so a failure still has to
         * say which of the two happened. Asked beforehand it refused on panels
         * the recipe had opened itself; see `whyNothingWasFound`. */
        return whyNothingWasFound(step, reportId, dataDate);
      }
      if (many > 1) {
        /* **AMBIGUITY IS A FAILURE, NOT A COIN TOSS.** Nine days of payments were
         * lost to a chart legend that read like a menu item. */
        return gaveUp(reportId, dataDate, {
          kind: FOUND_SEVERAL, lookingFor: step.find.called || step.find.what,
          doing: step.why, matches: many,
        });
      }

      if (step.do === CLICK) {
        await door.click(step.find.how, step.find.what, step.find.exact, step.find.near);
        /* **NOT SAID TWICE.** Every step announces itself above, before it is
         * attempted, and a second line here would double every click.
         *
         * **ONE THING IS GENUINELY LOST AND IT IS NOT NOTHING:** the old line ran
         * only if the click RETURNED, so its presence confirmed that. That is now
         * read from the next step's line instead -- which works for every recipe
         * in this product, because none of them ends on a click; each `toTake`
         * ends in `take-file`. **The day one ends on a click, a click that hangs
         * looks exactly like a click that worked.** */
      }
      /* A WAIT_FOR looks and does not click. Without that difference the door
       * would press the thing it was only waiting to appear -- on the orders page
       * that is the download menu, opened and then opened again, which closes
       * it. */
    }

    if (!plan.collecting) {
      /* **THE ASKING PHASE FINISHED, AND THAT IS A SUCCESS, NOT A FAILURE.** The
       * platform is building it now. What it was asked under is how the row is
       * found when a later run comes back -- and holding it is what stops this
       * being asked a second time. */
      return anAnswer(STILL_WAITING, reportId, dataDate, {
        theirId: dataDate,
        say: `Asked for it. About ${plan.recipe.readyInMinutes} minutes before it is ready; `
          + 'a later run will collect it rather than asking again.',
      });
    }

    /* **A RECIPE THAT NEVER TOOK A FILE IS A FAULT IN THE RECIPE**, and it says
     * so rather than reporting a missing file as the platform's doing. */
    return anAnswer(FAILED, reportId, dataDate, {
      say: 'Every step ran and none of them took a file. The recipe is missing its last step.',
    });
  };
}

/**
 * Do these bytes begin like a web page rather than like a file?
 *
 * **THIS IS HERE RATHER THAN IN `content.js` BECAUSE IT CAN BE WRONG, AND
 * ANYTHING THAT CAN BE WRONG IS CHECKED.** That is the rule at the top of
 * `content.js`, and a guard against a seller's sign-in page being filed as their
 * day's report is not the place to make an exception to it.
 *
 * **WHAT IT IS FOR.** A portal that has signed the browser out answers a file
 * address with its sign-in page, cheerfully, at 200. `doors.js` names that the
 * worst possible outcome in its own words: it is a file, it has a size, and
 * everything downstream believes the day arrived.
 *
 * **THE NARROWEST TEST THAT CATCHES IT.** It asks one question -- does this
 * start with markup -- and nothing about what kind of file it might be instead.
 * A spreadsheet begins `PK`, a CSV begins with a column name, a zip begins `PK`.
 * None of them begin with `<`.
 *
 * **AND IT IS NOT THE ANSWER, only a guard.** The Python half sniffs the real
 * bytes properly (`landing.the_file_that_matters`, which also unwraps a zip
 * holding one spreadsheet and refuses what is not a report at all) and this half
 * still has no counterpart. Said here rather than left to be assumed.
 */
/**
 * What one report's file is called once it is in the seller's Drive.
 *
 * **THE RULE IS THE PYTHON'S AND IT CROSSES IN THE RECIPE FILE, exactly as the
 * steps do (D107).** `autosync/landing.file_name_for` is
 * `<platform>_<report id>_<data date>.<extension>`, and the two parts a report
 * decides -- its platform and its extension -- are exported into
 * `recipes.json` by `tools/export_recipes.py`. **Nothing here knows a platform
 * or a file type**, which is the same rule the rest of this file lives by.
 *
 * **AND IT IS NOT DECORATION.** `landing.data_date_in` takes the day out of the
 * NAME, and `reading.a_reading` refuses a file with no day in its name. A file
 * put away under a name of this side's own invention is a file the nightly run
 * can never read -- it sits in the folder for ever while the seller's ledger
 * stays empty, and nothing anywhere says why.
 *
 * **NOTHING IS GUESSED. A report the book says nothing about answers nothing**,
 * and the walk turns that into a named failure rather than putting a file away
 * under a name it made up.
 */
export function theFileName(book, reportId, dataDate) {
  const how = book && book.fileNames && book.fileNames[reportId];
  if (!how || !how.platform || !how.extension) return '';
  /* **THE SAME QUESTION THE WALK ASKS, ASKED ONCE.** This used to check only
   * that the day was not empty, which let `05/09/2026` through into a name
   * `landing.data_date_in` cannot read a day out of -- the exact fault the
   * comment above exists to prevent. The walk refuses a bad day before it gets
   * here; this is the second lock on the same door, and it is the same rule
   * rather than a second copy of it. */
  if (whyTheDayIsRefused(dataDate)) return '';
  return `${how.platform}_${reportId}_${dataDate}.${how.extension}`;
}

export function looksLikeAPage(bytes) {
  if (!bytes || !bytes.length) return false;
  const opening = new TextDecoder('utf-8', { fatal: false })
    .decode(bytes.slice(0, 200)).trim().toLowerCase();
  return opening.startsWith('<');
}

/** A day, some days earlier, written the way the platforms write one. */
export function daysBefore(day, howMany) {
  if (!howMany) return day;
  const [y, m, d] = String(day).split('-').map(Number);
  const moved = new Date(Date.UTC(y, m - 1, d - howMany));
  return moved.toISOString().slice(0, 10);
}
