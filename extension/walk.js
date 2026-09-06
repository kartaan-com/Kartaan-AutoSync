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

/* What went wrong, by name. **Every one of these is its own failure and that is
 * the point.** The reference had one -- "button not found" -- and it covered all
 * of them, so a month of diagnosis went at the wrong thing because "it is
 * underneath a dialog" and "it has been renamed" arrived wearing the same words.
 * The sentence each of them means is NOT here: it comes from the book. */
export const FOUND_NOTHING = 'found-nothing';
export const FOUND_SEVERAL = 'found-several';
export const COVERED_UP = 'covered-up';
export const BUILT_IN_THE_PAGE = 'built-in-the-page';

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
  if (![GO, CLICK, WAIT_FOR, PICK_RANGE, TAKE_FILE].includes(step.do)) {
    return `"${step.do}" is not something this door knows how to do.`;
  }
  if (step.do === GO && !step.address) return 'A step that goes somewhere has to say where.';
  if ((step.do === CLICK || step.do === WAIT_FOR) && !step.find) {
    return `A ${step.do} step has to say what to look for.`;
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
 * The walk.
 *
 * `door` is the eight calls from `driver.js`. `book` is what came out of the
 * Python. `say` is how a line reaches the run log.
 */
export function theWalk({ door, book, say }) {
  if (!door) throw new Error('A walk needs a door to the page.');
  if (!book || !book.recipes) throw new Error('A walk needs the book of recipes.');
  if (typeof say !== 'function') throw new Error('A walk needs somewhere to say what it is doing.');

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
      const many = await door.find(step.find.how, step.find.what, step.find.exact, step.patience, step.find.near);
      if (many === 0) {
        return { failed: await whyNothingWasFound(step, reportId, dataDate) };
      }
      if (many > 1) {
        return { failed: await gaveUp(reportId, dataDate, {
          kind: FOUND_SEVERAL, lookingFor: step.find.called || step.find.what,
          doing: step.why, matches: many,
        }) };
      }
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
        return anAnswer(LANDED, reportId, dataDate, {
          fileName: fileName || null,
          size: got.body.length,
          say: `Landed ${got.body.length} bytes.`,
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
        say(`${reportId}: ${step.why}.`);
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
