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
/* **AND ONE THAT IS NEITHER "IT WORKED" NOR "IT BROKE" -- HIS RULING, 2026-09-14.**
 * *"There will be scenarios when a report will not be available for a date...
 * Rumee AutoSync used to mark that as not available and moves ahead."* A day the
 * portal has not built yet is refused at the calendar, before anything is asked
 * for, and the night remembers the day and tries it again on a later run
 * (`nightly.js`, `NOT_BUILT_YET`). **Only the extension speaks this word**: the
 * Python runner never reads a walk's answer, so the four above stay its four. */
export const NOT_AVAILABLE_YET = 'not-available-yet';

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

/* HOW LONG A PERSON TAKES, AND WHY A MACHINE HAS TO TAKE IT TOO.
 *
 * **HIS INSTRUCTION, 2026-09-11:** *"portals may block if it is an automated
 * approach which is downloading theirs"*, and the working reference has paced
 * itself for exactly that reason since it was written.
 *
 * **THE TWO NUMBERS ARE THE REFERENCE'S OWN, ROUNDED TO WHAT IT ACTUALLY DOES.**
 * `content/meesho.js` sleeps `4000 + random()*1000` on landing at payments,
 * `3000 + random()*1000` on landing at ads, and `clickAndWait(button, 1200)`
 * after pressing something. So: a few seconds to take in a page that has just
 * drawn, and about a second between one action and the next.
 *
 * **THE RANDOM PART IS THE POINT, NOT DECORATION.** A fixed pause is itself a
 * signature -- a thing that pauses 3.000 seconds, 3.000 seconds, 3.000 seconds is
 * more obviously a machine than one that never pauses at all. The reference adds
 * a random part to every one of its sleeps and this does the same.
 *
 * **AND THIS IS NOT PLATFORM KNOWLEDGE, so it is here and not in a recipe.** How
 * long a person takes to look at a page is the same on Meesho and on Flipkart.
 * `autosync/recipes.py` stays untouched by it, which is the rule this whole
 * product is built to.
 *
 * **IT IS COUNTED INTO THE BOUND ON HOW LONG A WALK MAY GO ON.**
 * `doors.test.js` adds the worst of these onto every step when it works out the
 * longest walk that can exist, because a pause nobody counted is exactly how
 * `ARMED_FOR_MS` became shorter than the thing it bounds once before. */
export const A_PERSON_LOOKS_AT_A_NEW_PAGE = Object.freeze({ least: 3000, upTo: 2000 });
export const A_PERSON_BETWEEN_TWO_STEPS = Object.freeze({ least: 800, upTo: 700 });

/** One pause, somewhere in the range, in milliseconds. */
export function aMomentLikeAPerson(how, dice = Math.random) {
  const spread = Math.floor(Math.max(0, dice()) * (how.upTo + 1));
  return how.least + Math.min(how.upTo, spread);
}

/* What a step can be. These cross the wire in every recipe, so they are the
 * Python spellings exactly. */
export const GO = 'go';
export const CLICK = 'click';
export const WAIT_FOR = 'wait-for';
export const PICK_RANGE = 'pick-range';
export const TAKE_FILE = 'take-file';
/* **THE TWO THAT ARE NOT ABOUT GETTING A FILE AT ALL.** Meesho sells no export of
 * the day's views: the figure is on a card on its dashboard and nowhere else. So
 * one step reads a number the page names, and another writes what was read as a
 * row on a file that is added to rather than replaced. `autosync/browser.py`
 * carries the reasoning; these are its spellings. */
export const READ_NUMBER = 'read-number';
export const ADD_TO_THE_LIST = 'add-to-the-list';
/* **THE ONE THAT PRESSES NOTHING.** Meesho's ads figures are not an export:
 * they come from two of its own addresses, called from inside the signed-in
 * page. `extension/ads.js` carries what those are. */
export const SWEEP_THE_ADS = 'sweep-the-ads';
/* **THE ONE THAT TYPES** (2026-09-15): a campaign id into Flipkart's campaign
 * search box, for the overall performance report. */
export const TYPE_IN = 'type-in';
/* **THE ONE THAT READS FLIPKART'S TOP SEARCH KEYWORDS OFF THE PAGE** (2026-09-15).
 * `extension/keywords.js` carries what is read. */
export const READ_THE_KEYWORDS = 'read-the-keywords';
/* **THE ONE STEP THAT LOOKS AT NOTHING.** Every other kind of waiting here waits
 * for something to appear. Meesho builds an orders export on its own servers and
 * the page it was asked from does not change at all while it happens, so there
 * is nothing to look at -- only time to pass. `autosync/browser.py` holds the
 * whole reason under `WAIT`, and the number lives in the recipe. */
export const WAIT = 'wait';

/* **WHICH DAY NAMES A ROW, and the two portals answer it differently.** The
 * Python spellings exactly (`autosync/browser.py`), because they cross the wire
 * on every lookup that narrows to a row. Meesho's exported-files panel names a
 * row by the day the export was MADE -- the day of the run -- and Flipkart's
 * Reports Centre by the end of the range, which is the day the data is about. */
export const THE_DAY_IT_IS_ABOUT = 'about';
export const THE_DAY_IT_WAS_MADE = 'made';

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
  if (![GO, CLICK, WAIT_FOR, PICK_RANGE, TAKE_FILE, WAIT,
    READ_NUMBER, ADD_TO_THE_LIST, SWEEP_THE_ADS, TYPE_IN, READ_THE_KEYWORDS].includes(step.do)) {
    return `"${step.do}" is not something this door knows how to do.`;
  }
  if (step.do === GO && !step.address) return 'A step that goes somewhere has to say where.';
  if ((step.do === CLICK || step.do === WAIT_FOR || step.do === READ_NUMBER || step.do === TYPE_IN)
    && !step.find) {
    return `A ${step.do} step has to say what to look for.`;
  }
  /* **THE SAME SENTENCE THE PYTHON REFUSES WITH.** A step that adds a row looks
   * for nothing: what it writes down was already read by the steps before it. */
  if (step.do === ADD_TO_THE_LIST && step.find) {
    return 'A step that adds a row looks for nothing. It writes down what the '
      + 'read-number steps before it already read.';
  }
  /* **A SWEEP LOOKS AT NO PAGE.** The same sentence the Python refuses with. */
  if (step.do === SWEEP_THE_ADS && step.find) {
    return 'A step that sweeps the ads addresses looks for nothing on the page. '
      + 'It asks the platform directly.';
  }
  if (step.do === READ_THE_KEYWORDS && step.find) {
    return 'A step that reads the keywords looks for nothing of its own. What it reads '
      + 'is written down in one place.';
  }
  if (step.do === WAIT && step.find) {
    /* **A WAIT AND A WAIT-FOR ARE NOT THE SAME STEP.** One passes time; the other
     * watches the page. Written with something to look for, a wait would pass its
     * time and never look at it, and the recipe would read as though it had
     * waited FOR that thing. */
    return 'A step that only waits has nothing to look for. Waiting for something is a wait-for.';
  }
  if (step.orFind && step.do !== WAIT_FOR) {
    /* **SOMETHING ELSE THAT COUNTS IS ONLY FOR A WAIT.** The same sentence the
     * Python refuses with. */
    return 'Only a step that waits for something can accept something else instead.';
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
  if (step.pressAgain) {
    /* **A CONTROL THAT TOGGLES, PRESSED AGAIN WHILE THIS STEP WAITS.** Flipkart's
     * Reports Centre hides its calendar behind a date box and a Custom chip, both
     * of which toggle. The same rules the Python holds. */
    if (![CLICK, WAIT_FOR, PICK_RANGE].includes(step.do)) {
      return 'Only a step waiting for something to appear can press a control again while it '
        + 'waits.';
    }
    if (!step.pressAgain.by || !step.pressAgain.by.what) {
      return 'Pressing again has to say what to press.';
    }
    if (!(Number(step.pressAgain.times) >= 1)) {
      return 'Pressing again no times at all is not pressing again.';
    }
    if (!(Number(step.pressAgain.after) >= 1)) {
      return 'Pressing again has to wait some time first, or the second press shuts it.';
    }
  }
  /* **TYPING, AND WHAT IS DONE ONCE PER CAMPAIGN** (2026-09-15). The same
   * sentences the Python refuses with. */
  if (step.pressLikeAMouse && step.do !== CLICK) {
    return 'Only a step that presses something can say how to press it.';
  }
  if (step.do === TYPE_IN && !step.words) return 'A step that types has to say what to type.';
  if (step.do !== TYPE_IN && step.words) return 'Only a step that types can say what to type.';
  if (step.forEachCampaign && ![TYPE_IN, CLICK, WAIT_FOR, TAKE_FILE].includes(step.do)) {
    return 'Only typing, pressing, waiting for something or taking a file can be done once '
      + 'per campaign.';
  }
  if ((String(step.words || '').includes('{campaign}')
    || String((step.find && step.find.what) || '').includes('{campaign}')) && !step.forEachCampaign) {
    return 'Only a step done once per campaign can name the campaign.';
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

/** What a campaign id may look like before it is typed into a portal's page. */
export const A_CAMPAIGN_ID = /^[A-Za-z0-9_-]{1,64}$/;

/** The cells of one line of a CSV, quotes honoured -- a campaign NAME can hold a
 *  comma, and splitting on every comma would read its day out of the wrong column. */
function theCellsOf(line) {
  const cells = [];
  let cell = '';
  let quoted = false;
  for (let at = 0; at < line.length; at += 1) {
    const c = line[at];
    if (quoted) {
      if (c === '"' && line[at + 1] === '"') {
        cell += '"';
        at += 1;
      } else if (c === '"') {
        quoted = false;
      } else {
        cell += c;
      }
    } else if (c === '"') {
      quoted = true;
    } else if (c === ',') {
      cells.push(cell.trim());
      cell = '';
    } else {
      cell += c;
    }
  }
  cells.push(cell.trim());
  return cells;
}

/**
 * The campaigns that ran on a day, read out of the file that names them.
 *
 * **THE REFERENCE'S OWN READING** (`background.js` `_setFkAdsDailyCacheFromBuffer`):
 * the header row carrying both columns, the rows whose day is that day, each id
 * once. **Null when the file has no such header** -- which is "not known", and is
 * not the same answer as "none ran".
 */
export function theCampaignsIn(text, { idColumn, dayColumn } = {}, dataDate = '') {
  if (!idColumn || !dayColumn) return null;
  const lines = String(text || '').split(/\r?\n/);
  const headerAt = lines.findIndex((line) => {
    const named = theCellsOf(line);
    return named.includes(idColumn) && named.includes(dayColumn);
  });
  if (headerAt < 0) return null;
  const header = theCellsOf(lines[headerAt]);
  const idAt = header.indexOf(idColumn);
  const dayAt = header.indexOf(dayColumn);
  const ids = [];
  for (const line of lines.slice(headerAt + 1)) {
    if (!line.trim()) continue;
    const row = theCellsOf(line);
    const id = row[idAt] || '';
    if (row[dayAt] === dataDate && A_CAMPAIGN_ID.test(id) && !ids.includes(id)) ids.push(id);
  }
  return ids;
}

/**
 * A recipe's steps with its once-per-campaign run repeated for each campaign.
 *
 * **WORKED OUT ONCE, AT THE START OF EVERY TURN, FROM THE SAME LIST**, so a walk
 * picking up on a new page counts its steps exactly as the page before did.
 */
export function withEachCampaign(steps, campaigns) {
  const out = [];
  let at = 0;
  while (at < steps.length) {
    if (!steps[at].forEachCampaign) {
      out.push(steps[at]);
      at += 1;
    } else {
      let end = at;
      while (end < steps.length && steps[end].forEachCampaign) end += 1;
      const run = steps.slice(at, end);
      campaigns.forEach((campaign, which) => {
        const put = (into) => String(into || '').split('{campaign}').join(campaign);
        for (const one of run) {
          out.push({
            ...one,
            words: put(one.words),
            find: one.find ? { ...one.find, what: put(one.find.what) } : one.find,
            campaign,
            campaignNumber: which + 1,
            campaignsInAll: campaigns.length,
          });
        }
      });
      at = end;
    }
  }
  return out;
}

/** A campaign's file name: the report's own, with the campaign id before the
 *  extension -- only when more than one campaign ran, the reference's rule. */
export function theCampaignsFileName(called, campaign, inAll) {
  if (!called || !campaign || !(inAll > 1)) return called;
  const dot = called.lastIndexOf('.');
  return dot < 0 ? `${called}_${campaign}` : `${called.slice(0, dot)}_${campaign}${called.slice(dot)}`;
}

/**
 * Every way one portal has been met writing one day.
 *
 * **SEVERAL, NEVER ONE, AND THAT IS THE 2026-09-10 CORRECTION.** What stood here
 * built a single string per portal from a single leading-nought rule. Neither
 * portal writes a day only one way, and the working reference does not pretend
 * they do: `content/flipkart.js findReportRowDownloadBtn` builds five spellings
 * and `content/meesho.js findExportDownloadByTodayDate` builds six, and a row
 * matches if it carries ANY of them. Committing to one chose, on Flipkart, a
 * spelling the reference's own matcher excludes.
 *
 * **THE RULE IS NOT WRITTEN HERE. IT CROSSES.** `book.daysInWords` comes out of
 * `autosync/recipes.py` through `tools/export_recipes.py`, one entry per portal,
 * carrying that portal's month names and its spellings. A spelling is a SHAPE --
 * `{d} {Mon} {yyyy}` -- and all this does is put the day into it. **Nothing on
 * this side has an opinion about noughts, month names or the order the pieces
 * come in**, which is the only way the two halves cannot drift.
 *
 * **THE FIVE NAMES ARE THE WHOLE OF WHAT BOTH HALVES HAVE TO AGREE ABOUT.** A
 * half that had never heard of `{dd}` would leave those four characters sitting
 * on the page, and the lookup would narrow to a row nothing carries. The order
 * is not the point -- each piece carries its own braces, so none can be found
 * inside another -- and a check runs this side against the Python's answer.
 *
 * **A PORTAL THAT DID NOT CROSS IS A REFUSAL, NOT A FALLBACK.** Filled in with
 * anything else, the lookup narrows to a row the page does not carry and the
 * night reports a renamed button -- the failure this whole door was built to
 * stop being reported that way.
 */
export function theDaysInWords(book, whose, dataDate) {
  const rule = book && book.daysInWords && book.daysInWords[whose];
  if (!rule) {
    throw new Error(
      `There is no wording of a day for "${whose || ''}" in the recipe file, so a row named by `
      + "the day in a platform's own wording cannot be filled in."
    );
  }
  const [year, month, day] = String(dataDate).split('-').map(Number);
  const pieces = {
    yyyy: String(year),
    mm: String(month).padStart(2, '0'),
    dd: String(day).padStart(2, '0'),
    Mon: rule.months[month - 1],
    /* **THE SIXTH PIECE, ADDED 2026-09-11.** Flipkart's listings Downloads
     * History writes the month out in full -- `11 September, 11:10 PM` -- and
     * none of the six spellings it had could match that, so the row holding the
     * file the walk had just asked for could not be found. The names cross from
     * the Python half like the short ones; nothing here has an opinion. */
    Month: (rule.monthsInFull || [])[month - 1],
    d: String(day),
  };
  return rule.spellings.map(
    (shape) => String(shape).replace(/\{(yyyy|mm|dd|Mon|Month|d)\}/g, (_, piece) => pieces[piece])
  );
}

/**
 * Every way the row one lookup wants could be named. **Empty when it wants any
 * row at all**, which is most lookups.
 *
 * **OUTSIDE THE WALK ON PURPOSE, so that both halves can be asked the same
 * question directly.** `tools/export_recipes_checks.py` runs this against the
 * shipped `extension/walk.js` and `extension/recipes.json`, lookup by lookup
 * across every recipe, and holds its answers to `browser_door`'s own -- which is
 * what makes "the two halves fill a step the same way" a thing that is measured
 * rather than a thing that is claimed.
 */
export function theRowsItCouldBe(book, find, dataDate, runDay) {
  const near = String(find.near || '');
  if (!near) return [];
  if (!near.includes('{day_in_words}')) {
    return [near.split('{day}').join(dataDate)];
  }
  /* **WHICH DAY NAMES THE ROW IS THE LOOKUP'S OWN ANSWER, and there is no
   * default here either.** A lookup that has not said is refused by the Python
   * before it is ever written out, and a walker that quietly picked one would be
   * the guess the whole field exists to remove. */
  const namedBy = find.dayInWordsOf === THE_DAY_IT_WAS_MADE ? runDay : dataDate;
  return theDaysInWords(book, find.dayInWordsIs, namedBy).map(
    (inWords) => near.split('{day_in_words}').join(inWords).split('{day}').join(dataDate)
  );
}

/**
 * The day this run is happening, as `YYYY-MM-DD`.
 *
 * **THIS IS NOT THE DAY BEING FETCHED, AND THAT IS THE WHOLE POINT.** The day
 * being fetched is yesterday on an ordinary night and can be weeks back on a
 * catch-up. **Meesho's exported-files panel names a row by the day the export
 * was MADE**, which is neither of those -- it is now.
 *
 * **IT IS READ OFF THE BROWSER'S OWN CLOCK BECAUSE THE BROWSER IS THE ONLY
 * THING THAT KNOWS.** The export is made by this machine, at this moment, in
 * the seller's own timezone, and Meesho stamps the row in that same timezone.
 * The reference reads exactly this and calls it `todayISO()`.
 *
 * **AND IT IS NOT AN OPTION A CALLER MAY HAND IN.** That shape is what A52 had
 * to take out of this very function: a value nothing ever supplied, quietly
 * defaulting, filling five lookups with a day no page carries.
 */
export function theDayOfTheRun(now = new Date()) {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
    + `-${String(now.getDate()).padStart(2, '0')}`;
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
      + 'would be under a name the scheduled sync cannot read a day out of, and never read.';
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) {
    return `"${day}" is not a day written the way the scheduled sync reads one back out of a `
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
  /* **WHERE THE RANDOM PART OF EVERY PAUSE COMES FROM.** Handed in so a check can
   * drive the pacing to its slowest and its fastest on purpose, rather than
   * running a hundred times and hoping. The real walk uses the browser's own. */
  dice = Math.random,
  /* **THE PAUSE IS HANDED IN, AND IT IS NOT A DOOR CALL. THAT IS THE SAME
   * REASONING `putTheFile` AND `armTheCatcher` ARE GIVEN ABOVE.** The door is
   * the ten calls the Python side makes, spelt the way the Python spells them.
   * **And `wait` is one of them and is NOT this**: `wait` is a step the recipe
   * asks for, in whole seconds, because Meesho builds a file on its own servers
   * and shows nothing while it does. This is the walk moving like a person, which
   * no recipe asks for and no recipe may change. Four checks that count what the
   * recipe waited proved the difference the moment the two were the same call. */
  pause = (ms) => new Promise((done) => { setTimeout(done, ms); }),
  /* **WHERE A ROW GOES WHEN THERE IS NO FILE TO FETCH.** Required for the same
   * reason `putTheFile` is: a walk built without it would read the seller's
   * figures off the page, report that it had landed, and put them nowhere. */
  addToTheList,
  /* **THE ADS SWEEP, HANDED IN LIKE THE TWO ABOVE AND FOR THE SAME REASON.** It
   * reaches Meesho's own addresses with the seller's session, which only the half
   * running inside the page can do. What is checked here is what this file does
   * with the answer; what it asks for is checked in `ads.test.js`.
   *
   * **NOT REQUIRED, and that is the one difference.** Every walk needs somewhere
   * to put a file; only one recipe in the book sweeps. A walk built without it
   * refuses that step by name instead of every walk refusing to be built. */
  sweepTheAds = null,
  /* **WHICH CAMPAIGNS RAN ON A DAY, KEPT AND READ BACK BY THE BACKGROUND HALF**
   * (2026-09-15). Not required: only the ads daily file keeps them, and only
   * Flipkart's overall performance report reads them. */
  keepTheCampaigns = null,
  theCampaigns = null,
  /* **FLIPKART'S TOP SEARCH KEYWORDS, READ OFF THE PAGE** (2026-09-15). Not
   * required, like the sweep: only one recipe reads them. */
  readTheKeywords = null,
  /* **MOVES THE PAGE TO A ROUTE AFTER `#`, FROM INSIDE IT** (A53, 2026-09-15). A `go`
   * to such an address loads only the page before the `#`; see `doors.js`
   * `routeInThePage`. Not required: only a walk that meets such an address needs it,
   * and it refuses in words there. */
  routeTo = null,
  /* **MARKS THE ONE SIGN-IN ATTEMPT AS MADE, in the half that outlives the page (A53).** */
  markTriedSigningIn = null,
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
  /* **AND THIS ONE AFTER THAT, FOR THE SAME REASON, which is not an ordering
   * anybody should have to guess at.** Every refusal here is asked in the order
   * it was added, so a walk missing two things still names the one that has been
   * named since before this was written. */
  if (typeof addToTheList !== 'function') {
    throw new Error(
      'A walk needs somewhere to add a row for the reports that are not a file anywhere. '
      + "Without one it would read the seller's figures off the page and drop them, and "
      + 'report that they had landed.'
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

  async function gaveUp(reportId, dataDate, {
    kind, lookingFor, doing, matches = 0, lookup = null, coveringWords = '',
  }) {
    const pageWas = capture(await door.page_text());
    /* **AND WHERE EACH MATCH SITS, WHEN THERE ARE SEVERAL.** His own ads FSN
     * report refused twice on 2026-09-14 saying *"2 things match Consolidated
     * FSN Report"* -- and by hand, on the same page, opening the same list, there
     * was ONE. The page kept here was 400 characters and did not hold the words,
     * so a count alone could only be answered by guessing. **The door can name
     * the shape of each match -- a tag, a role, an id -- and nothing of the
     * page's own words**, and the next refusal is then the measurement.
     *
     * **ASKED INSIDE A FAILURE, SO IT MUST NOT BECOME ONE.** A door without the
     * question, or one that throws answering it, leaves the sentence exactly as
     * it was rather than losing the failure it is attached to. */
    let where = '';
    if (kind === FOUND_SEVERAL && lookup && typeof door.where_they_sit === 'function') {
      try {
        const sits = await door.where_they_sit(
          lookup.how, lookup.what, lookup.exact, lookup.near, lookup.alsoSaying,
        );
        if (sits && sits.length) where = ` They sit: ${sits.join('; ')}.`;
      } catch (couldNotSay) {
        where = '';
      }
    }
    /* **THE COVERING'S OWN WORDS, SO THE NEXT ONE OF THESE NAMES ITSELF.**
     * `whatIsCovering` already reads them off whatever is blocking (or, for a
     * backdrop with none of its own, off whatever sits on top of it) -- they
     * were worked out and then thrown away. Job 3b, 2026-09-22, spent a live
     * session finding what covered `fk_views` because the run log that failed
     * never said. */
    const coveringNote = kind === COVERED_UP && coveringWords ? ` It reads: "${coveringWords}".` : '';
    const said = kind === FOUND_SEVERAL
      ? `${doing}: ${matches} things match "${lookingFor}".${where} ${meaningOf(kind)}`
      : `${doing}: could not find "${lookingFor}". ${meaningOf(kind)}${coveringNote}`;
    return anAnswer(FAILED, reportId, dataDate, { say: said, pageWas });
  }

  /** The seller's own panel, and the days, put into a step.
   *
   *  **THE DAY IN WORDS IS WORKED OUT HERE, FROM THE RECIPE, AND IS NOT HANDED
   *  IN (A52).** It used to be an option on the walk, defaulting to the plain
   *  ISO day -- and NOTHING anywhere ever supplied one. So every lookup narrowed
   *  to a row in the platform's own wording was narrowed to `2026-06-06`, which
   *  appears on no row of either portal.
   *
   *  **AND WHOSE WORDING IS THE RECIPE'S TO SAY, because the two portals
   *  disagree.** Meesho writes `1 Sep 2026`, Flipkart's Reports Centre writes
   *  `05 Jun 2026`. A lookup that names a row in words without saying whose
   *  wording it means cannot be filled in at all, and this refuses rather than
   *  guessing -- guessed wrong it finds nothing for nine days of every month.
   *
   *  **AND SO IS WHICH DAY, WHICH IS THE 2026-09-10 CORRECTION.** Whose wording
   *  answers `1 Sep` against `01 Sep`; it says nothing about WHICH day is on the
   *  row. Meesho's exported-files panel names a row by the day the export was
   *  MADE -- that is `runDay`, not `dataDate` -- and Flipkart's Reports Centre
   *  names one by the end of its range, which is the data date. Filled with the
   *  wrong one, a run on 25 August looked for `24 Aug 2026` on a row reading
   *  `25 Aug 2026, 04:49 PM`.
   *
   *  **`near` COMES OUT AS AN ARRAY, ALWAYS, EVEN OF ONE.** A row matches if it
   *  carries any of the ways that portal writes a day. A value that is sometimes
   *  one row and sometimes several would be two things wearing one name.
   */
  function filledIn(step, panel, dataDate, runDay) {
    /* **EVERY OCCURRENCE, NOT THE FIRST (cycle 46, R6#15).**
     *
     * Filling by name replaces the FIRST one only, so a recipe naming the same
     * day twice -- a page that wants it in the address and again in the row it
     * looks for -- would go out half-filled and find nothing, on the platform,
     * at night, with no one watching. No recipe does that today. Nothing
     * stopped one, and a recipe is data, added without touching this file.
     *
     * **AND `{panel}` IS NOT FILLED INTO A ROW ANY MORE.** It was, here and
     * nowhere else: the Python filled it into the address only, so one half
     * would have narrowed to a real row and the other to a row holding the
     * literal characters `{panel}`. A row is named by the day, never by the
     * seller's own panel name, and the Python now refuses a recipe that says
     * otherwise. */
    const put = (into) => String(into || '')
      .split('{panel}').join(panel || '')
      .split('{day}').join(dataDate);
    /* **AN ADDRESS NAMES THE DAY PLAINLY OR NOT AT ALL.** Whose wording is said
     * on a lookup, and an address has no lookup -- so there is nothing to fill
     * it from but a guess. The Python refuses such a recipe outright; this is
     * the same refusal on the side that would actually walk it. */
    if (String(step.address || '').includes('{day_in_words}')) {
      throw new Error(
        "An address names the day plainly, not in a platform's own wording."
      );
    }
    return {
      ...step,
      address: put(step.address),
      find: step.find
        ? { ...step.find, near: theRowsItCouldBe(book, step.find, dataDate, runDay) }
        : step.find,
      /* **AND WHAT ELSE A WAIT MAY COUNT INSTEAD, FILLED THE SAME WAY** -- the row
       * Flipkart lists a request under (his ruling, 2026-09-14). */
      orFind: step.orFind
        ? { ...step.orFind, near: theRowsItCouldBe(book, step.orFind, dataDate, runDay) }
        : step.orFind,
    };
  }


  /** How many things on the page match this step's lookup.
   *
   *  **AND A CONTROL THAT TOGGLES IS PRESSED AGAIN WHILE IT WAITS, when the step
   *  says one does.** Flipkart's Reports Centre hides its calendar behind a date
   *  box and then a Custom chip, and both toggle: a press that arrived while the
   *  sub-page was still drawing opened nothing, and this step would then wait out
   *  its whole patience at a page that will never change. The reference presses
   *  the date box again on every third look (`content/flipkart.js` StepD).
   *
   *  **THE SAME SHAPE THE PYTHON HALF HOLDS** (`browser_door._how_many_match`),
   *  because a walk driven from one and checked against the other has to be one
   *  walk.
   */
  async function howManyMatch(step, reportId) {
    const look = (patience) => door.find(
      step.find.how, step.find.what, step.find.exact, patience, step.find.near,
      step.find.alsoSaying);
    const press = step.pressAgain;
    if (!press) return look(step.patience);
    let spent = 0;
    for (let turn = 0; turn < press.times; turn += 1) {
      /* **A GO THAT THREW IS A GO THAT DID NOT FIND IT, AND NOTHING MORE.** The
       * last go below is NOT caught, so a real failure still carries its own
       * words out -- what is passed over here is only the middle of the wait,
       * and every press in between is said out loud. */
      const many = await answered(() => look(press.after));
      if (many) return many;
      spent += press.after;
      await pressItAgain(press, reportId);
    }
    return look(Math.max(1, step.patience - spent));
  }

  /** Put the range into the page, pressing again the control that draws it. */
  async function theRangeGoesIn(step, reportId, start, end) {
    const putIn = async (patience) => {
      await door.pick_range(start, end, patience,
        Boolean(step.switchedOffDaysChangeTheCursor));
      return true;
    };
    const press = step.pressAgain;
    if (!press) { await putIn(step.patience); return; }
    let spent = 0;
    for (let turn = 0; turn < press.times; turn += 1) {
      if (await answeredUnlessNotBuilt(() => putIn(press.after))) return;
      spent += press.after;
      await pressItAgain(press, reportId);
    }
    await putIn(Math.max(1, step.patience - spent));
  }

  /** What one go answered, or nothing at all when it threw. */
  async function answered(work) {
    try {
      return await work();
    } catch (wrong) {
      return null;
    }
  }

  /** The same, except that a day the portal has not built is said at once.
   *
   *  **PRESSING THE CHIP AGAIN CANNOT BUILD A DAY**, and a press that shut the
   *  calendar would turn the true answer into "no calendar was showing" by the
   *  last look -- the misreading this whole ruling exists to end. */
  async function answeredUnlessNotBuilt(work) {
    try {
      return await work();
    } catch (wrong) {
      if (wrong && wrong.dayNotAvailable) throw wrong;
      return null;
    }
  }

  /** What else a wait counts when its words are not on the page right now.
   *
   *  **HIS RULING, 2026-09-14: "a banner it missed doesn't turn success into a
   *  failure."** Two things, in the reference's own order (`content/flipkart.js`
   *  `decideReportSubmissionOutcome`): a banner that already said the words
   *  (for a loose wait only -- an exact wait is waiting for a thing, not a
   *  message), then the durable place the platform lists what was asked for. */
  async function whatElseCounts(step, reportId) {
    if (step.find && step.find.exact === false && typeof door.banners_seen === 'function') {
      try {
        const heard = (await door.banners_seen()) || [];
        const wanted = String(step.find.what || '').toLowerCase();
        const one = heard.find((banner) => String((banner && banner.words) || '').toLowerCase().includes(wanted));
        if (one) {
          say(`${reportId}: "${step.find.what}" was not on the page any more, but a banner had said it: `
            + `"${one.words}".`);
          return 1;
        }
      } catch (couldNotAsk) {
        /* A door that cannot say what it saw leaves the wait as it was. */
      }
    }
    if (step.orFind) {
      const other = await door.find(step.orFind.how, step.orFind.what, step.orFind.exact, 1,
        step.orFind.near, step.orFind.alsoSaying);
      if (other === 1) {
        say(`${reportId}: ${step.orFind.called || step.orFind.what} was found instead, which confirms it.`);
        return 1;
      }
    }
    return 0;
  }

  /** Press the toggling control once more. **Said, never swallowed.** */
  async function pressItAgain(press, reportId) {
    try {
      await door.click(press.by.how, press.by.what, press.by.exact, []);
    } catch (wrong) {
      say(`${reportId}: ${press.by.called || press.by.what} could not be pressed again -- `
        + `${(wrong && wrong.message) || wrong}`);
      return;
    }
    say(`${reportId}: pressed ${press.by.called || press.by.what} again, because it is a `
      + 'control that toggles.');
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
    const wrongWording = whyTheWordingIsWrong(reportId, steps);
    if (wrongWording) throw new Error(wrongWording);
    return { recipe, twoPhase, steps };
  }

  /** Why this recipe names another portal's wording of a day, or null.
   *
   *  **THE PYTHON ALREADY REFUSES THIS AND THAT WAS NOT ENOUGH.** Its refusal
   *  lives in `recipes.steps_for`, which the tool that writes `recipes.json` has
   *  never called -- so a wording edited by hand into the shipped file reached
   *  the portal with nothing anywhere complaining. This is the same refusal on
   *  the side that would actually walk it.
   *
   *  **AND THE PORTAL IS THE REPORT'S OWN, taken from the report list that
   *  already crosses** (`book.fileNames`), never off the front of the report's
   *  name -- a name is a spelling and a spelling is not a fact (D170).
   */
  function whyTheWordingIsWrong(reportId, steps) {
    const belongsTo = (book.fileNames && book.fileNames[reportId]
      && book.fileNames[reportId].platform) || '';
    for (const one of steps) {
      const whose = one.find ? String(one.find.dayInWordsIs || '') : '';
      if (!whose) continue;
      if (!(book.daysInWords && book.daysInWords[whose])) {
        return `${reportId} asks for a day written the way "${whose}" writes one, and no wording `
          + 'of a day is written down for that.';
      }
      if (belongsTo && whose !== belongsTo) {
        return `${reportId} is a ${belongsTo} report and asks for a day written the way ${whose} `
          + `writes one. A row on ${belongsTo}'s own page is never written the way ${whose} `
          + 'writes it.';
      }
    }
    return null;
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
      coveringWords: covering || '',
    });
  }

  async function takeTheFile(step, reportId, dataDate) {
    if (step.find) {
      let many = await door.find(step.find.how, step.find.what, step.find.exact, step.patience,
        step.find.near, step.find.alsoSaying);
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
        many = await door.find(step.find.how, step.find.what, step.find.exact, step.patience,
          step.find.near, step.find.alsoSaying);
      }
      if (many === 0) {
        return { failed: await whyNothingWasFound(step, reportId, dataDate) };
      }
      /* **A STEP THAT NARROWED TO A DAY AND STILL HAS SEVERAL TAKES THE NEWEST;
       * ONE THAT NARROWED NOTHING STILL REFUSES.** Measured on his own Meesho on
       * 2026-09-11: ten Download rows on the page, and `near` cut them to TWO --
       * both reading `2026-09-10_2026-09-10_2026-09-11`, one made at 08:51 and
       * one at 08:30, because he ran the export twice that morning. Those are two
       * RIGHT rows, not two wrong ones, and refusing them leaves the day
       * unfetched for a reason that is no fault at all. The payments outage this
       * refusal was built for had nothing narrowing its candidates, which is
       * exactly the case `near` being empty still covers. Newest is topmost; the
       * door says why. */
      const newestOfSeveral = (step.find.near || []).length > 0;
      if (many > 1 && !newestOfSeveral) {
        return { failed: await gaveUp(reportId, dataDate, {
          kind: FOUND_SEVERAL, lookingFor: step.find.called || step.find.what,
          doing: step.why, matches: many, lookup: step.find,
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
      await door.click(step.find.how, step.find.what, step.find.exact, step.find.near,
        newestOfSeveral, step.find.alsoSaying);
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
    /* **THERE IS NO `dayInWords` HERE ANY MORE, AND THAT IS THE FIX (A52).** It
     * was an option the caller could hand in, defaulting to the plain ISO day,
     * and no caller anywhere ever handed one in -- so five reports looked for a
     * row named `2026-06-06` on pages that write `06 Jun 2026` or `6 Jun 2026`.
     * The wording is the recipe's to say and the day is already here, so there
     * was never anything for a caller to supply. Taking it away also closes what
     * an independent reviewer found on 2026-09-08: a value reaching a step's
     * address and its `find.near` with nothing asking anything of it. */
    panel = '', askedAlready = null, fileName = '',
    /* **THE FIRST DAY OF THE RANGE, WHEN IT IS EARLIER THAN THE DAY (A53).** Flipkart
     * traffic is asked from the day after the last one captured -- Rumee's way. */
    fromDay = '',
    /* **WHETHER THE ONE SIGN-IN ATTEMPT HAS ALREADY BEEN MADE FOR THIS REPORT (A53).** */
    triedSigningIn: triedAlready = false,
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
    let triedSigningIn = Boolean(triedAlready);

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
        steps: found.steps.map((one) => filledIn(one, panel, dataDate, theDayOfTheRun())),
        collecting,
      };
    } catch (wrong) {
      return anAnswer(FAILED, reportId, dataDate, { say: wrong.message });
    }

    /* **A REPORT DONE ONCE PER CAMPAIGN ASKS WHICH CAMPAIGNS RAN, FIRST** (2026-09-15).
     * Not known yet is "not available yet": the file that names them has not landed
     * for that day, and a later run tries again. None is nothing to fetch. */
    const campaignsFrom = plan.recipe && plan.recipe.campaignsFrom;
    if (campaignsFrom) {
      const campaigns = typeof theCampaigns === 'function'
        ? await theCampaigns({ reportId: campaignsFrom.report, dataDate })
        : null;
      if (!Array.isArray(campaigns)) {
        return anAnswer(NOT_AVAILABLE_YET, reportId, dataDate, {
          say: `Which ad campaigns ran on ${dataDate} is not known yet: ${campaignsFrom.report} has `
            + 'not landed for that day in this browser. Nothing was asked for; this day will be '
            + 'tried again on a later run.',
          /* A57, Job 2: the list was never fetched, which is not the platform holding
           * the day back -- so the night keeps the day owed without counting it. */
          listMissing: true,
        });
      }
      if (!campaigns.length) {
        return anAnswer(NOTHING_TO_FETCH, reportId, dataDate, {
          say: `No ad campaign ran on ${dataDate}, according to ${campaignsFrom.report}, so there `
            + 'is nothing to record.',
        });
      }
      plan = { ...plan, steps: withEachCampaign(plan.steps, campaigns) };
    }
    const campaignFilesLanded = [];

    /* **WHETHER THIS PAGE HAS DONE ANYTHING YET**, which is what tells the
     * landing pause apart from the between-steps one. A walk resuming after a
     * `go` starts false again, because it really is a new page. */
    let walkedHereAlready = false;

    /* **WHAT THE PAGE HAS BEEN READ FOR SO FAR, IN THE ORDER IT WAS READ.** A
     * `Map` and not an object: the column order of the row is the order of the
     * steps in the recipe, and that has to be the recipe's business rather than
     * whatever order a browser happens to hand back keys in. **A file whose
     * columns can change order between two nights is a file nothing can read.**
     *
     * **AND IT LIVES FOR ONE PAGE, WHICH IS A LIMIT AND IS SAID OUT LOUD.** A
     * walk that read a number and then went somewhere else would lose it -- so
     * every read-number step and the add-to-the-list step after them have to sit
     * on the same page. The one recipe that uses them does. */
    const readSoFar = new Map();
    /* **POP-UPS ARE SHUT ONCE A PAGE, BEFORE ITS FIRST STEP** -- his ruling,
     * 2026-09-14, the reference's own `dismissFkPopups`. */
    let closedPopUpsHere = false;

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

      /* **A PAUSE BEFORE EVERY STEP THIS PAGE WALKS, BECAUSE A PORTAL THAT READS
       * THE WALK AS A MACHINE CAN BLOCK THE SELLER'S ACCOUNT.** His instruction,
       * 2026-09-11. The first step a page walks gets the longer one -- that is the
       * moment a person is looking at a page that has just drawn, and it is where
       * the reference puts its own four-to-five seconds.
       *
       * **IT SITS ABOVE THE SIGN-IN CHECK ON PURPOSE.** The reference sleeps
       * before it so much as looks at a page, and a page part-way through drawing
       * is exactly the page that answers "signed out" when nobody is. */
      await pause(aMomentLikeAPerson(
        walkedHereAlready ? A_PERSON_BETWEEN_TWO_STEPS : A_PERSON_LOOKS_AT_A_NEW_PAGE,
        dice,
      ));
      walkedHereAlready = true;

      /* **ASKED FIRST, EVERY STEP, AND IT IS NOT THIS REPORT'S FAULT.**
       *
       * **THIS IS ALSO WHAT CATCHES A SESSION THAT EXPIRED HALF WAY THROUGH A
       * WALK.** A walk now spans several pages, and the portal can sign the
       * seller out between any two of them -- the first step of the new page
       * asks again, before anything is clicked, and the answer is the same
       * "somebody has to sign in" it would have been at the start. */
      if (await door.needs_signing_in()) {
        /* **ONE ATTEMPT TO SIGN IN FIRST -- HIS RULING, 2026-09-16.** Marked before it
         * is made, because signing in reloads the page and the next page must not try
         * again. Still signed out, the sync pauses and asks the seller (Resume). */
        let signedIn = false;
        if (!triedSigningIn && typeof door.try_signing_in === 'function') {
          triedSigningIn = true;
          if (typeof markTriedSigningIn === 'function') await markTriedSigningIn();
          say(`${reportId}: the platform asked to be signed in to, so signing in is tried once.`);
          signedIn = await door.try_signing_in();
        }
        if (!signedIn) {
          throw new NeedsSigningIn(
            'The panel is asking to be signed in to. Nothing can be fetched from it until somebody '
            + 'does, and every report after this one would fail the same way.'
          );
        }
      }

      /* **A PAGE PICKED UP AFTER A `go` TO AN ADDRESS WITH `#` IS MOVED TO THAT ROUTE
       * FIRST** (A53). The `go` loaded only the page before the `#`. */
      const cameFrom = at === startAt && at > 0 ? plan.steps[at - 1] : null;
      if (cameFrom && cameFrom.do === GO && String(cameFrom.address || '').includes('#')) {
        if (typeof routeTo !== 'function') {
          return anAnswer(FAILED, reportId, dataDate, {
            say: `${cameFrom.why}: this walk has no way to move the page to its route after the #.`,
          });
        }
        try {
          await routeTo({ address: cameFrom.address });
        } catch (couldNotMove) {
          return anAnswer(FAILED, reportId, dataDate, {
            say: `${cameFrom.why}: ${(couldNotMove && couldNotMove.message) || couldNotMove}`,
          });
        }
      }

      if (!closedPopUpsHere && step.do !== GO && typeof door.close_pop_ups === 'function') {
        closedPopUpsHere = true;
        try {
          const closed = (await door.close_pop_ups()) || [];
          if (closed.length) say(`${reportId}: closed what was in the way first -- ${closed.join('; ')}.`);
        } catch (couldNotClose) {
          say(`${reportId}: could not close what was in the way -- `
            + `${(couldNotClose && couldNotClose.message) || couldNotClose}`);
        }
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
        /* **AND WHICH CALENDAR IT IS STANDING IN FRONT OF GOES WITH IT.**
         * Flipkart's Reports Centre switches a day off two different ways and
         * one of them shows only in the cursor -- which is that portal's own
         * habit, not a rule of browsers, so it is a fact the recipe carries
         * rather than something the door assumes about every calendar. */
        /* **AND THE CHIP THAT DRAWS THE CALENDAR IS PRESSED AGAIN WHILE THIS
         * WAITS, BECAUSE IT TOGGLES.** The reference re-presses it once, part
         * way through its own wait for the month heading, "in case it toggled
         * off" -- and without that the only symptom is a quiet wait followed by
         * "no calendar was showing", which reads as the portal having changed. */
        try {
          await theRangeGoesIn(step, reportId,
            fromDay && fromDay < dataDate ? fromDay : daysBefore(dataDate, (step.rangeDays || 1) - 1),
            dataDate);
        } catch (wrong) {
          if (!(wrong && wrong.dayNotAvailable)) throw wrong;
          /* **NOT A FAILURE, AND NOTHING HAS BEEN ASKED FOR.** The calendar comes
           * before every Submit in every recipe that has one, so a refusal here
           * has spent nothing on the platform -- which is what lets the night give
           * the seller's request back. Rumee's own words for it: "not yet
           * available on Flipkart -- will retry automatically". */
          return anAnswer(NOT_AVAILABLE_YET, reportId, dataDate, {
            say: `${wrong.message} Nothing was asked for; this day will be tried again on a later run.`,
          });
        }
        continue;
      }

      if (step.do === SWEEP_THE_ADS) {
        if (typeof sweepTheAds !== 'function') {
          return anAnswer(FAILED, reportId, dataDate, {
            say: "This recipe sweeps a platform's own addresses and this walk was built with "
              + 'no way of reaching them, so nothing was asked for.',
          });
        }
        let swept;
        try {
          swept = await sweepTheAds({ dataDate, patience: step.patience });
        } catch (wrong) {
          return anAnswer(FAILED, reportId, dataDate, {
            say: `${step.why}: ${(wrong && wrong.message) || wrong}`,
            pageWas: capture(await door.page_text()),
          });
        }
        /* **NOTHING RUNNING IS NOT A FAILURE AND NOT A SUCCESS, AND SAYING SO IS
         * THE WHOLE POINT.** His ruling of 2026-09-11 was to collect only the
         * campaigns that are running, told plainly that he has none. **The
         * reference reports the job done and writes nothing** -- so a seller sees
         * an empty folder and a clean night, which is the exact shape of fault
         * this product exists against. This is the fourth word: there was nothing
         * to fetch, and here is why. */
        if (!swept.files.length) {
          return anAnswer(NOTHING_TO_FETCH, reportId, dataDate, {
            say: `${swept.running} of ${swept.lookedAt} campaigns were running on `
              + `${dataDate}, so there is nothing to record. Only campaigns that are `
              + 'running are collected.',
          });
        }
        /* **ONE SWEEP, THREE REPORTS' FILES, because it is one pair of calls.**
         * Asking Meesho for the same campaign three times to write three files
         * would be three times the load for the same answer -- `recipes.py`
         * `MADE_BY_ANOTHER` is where the other two say who fetches them. */
        const landed = [];
        for (const one of swept.files) {
          const called = theFileName(book, one.reportId, dataDate);
          if (!called) {
            return anAnswer(FAILED, reportId, dataDate, {
              say: `There is nothing in the recipe file saying what ${one.reportId}'s file `
                + 'is called, so nothing has been put anywhere.',
            });
          }
          const body = new TextEncoder().encode(one.text);
          try {
            // eslint-disable-next-line no-await-in-loop
            await putTheFile({ reportId: one.reportId, fileName: called, body });
          } catch (wrong) {
            return anAnswer(FAILED, reportId, dataDate, {
              fileName: called,
              say: `${called} could not be put in the seller's Drive: `
                + `${(wrong && wrong.message) || wrong}`,
            });
          }
          landed.push({ called, size: body.length });
        }
        return anAnswer(LANDED, reportId, dataDate, {
          fileName: landed[0].called,
          size: landed.reduce((all, one) => all + one.size, 0),
          say: `${swept.running} of ${swept.lookedAt} campaigns were running. Landed `
            + `${landed.map((one) => `${one.called} (${one.size} bytes)`).join(', ')} in the `
            + "seller's Drive.",
        });
      }

      if (step.do === READ_THE_KEYWORDS) {
        if (typeof readTheKeywords !== 'function') {
          return anAnswer(FAILED, reportId, dataDate, {
            say: 'This recipe reads the keywords off the page and this walk was built with no way '
              + 'of reading them, so nothing was read.',
          });
        }
        let read;
        try {
          read = await readTheKeywords({ dataDate, patience: step.patience });
        } catch (wrong) {
          return anAnswer(FAILED, reportId, dataDate, {
            say: `${step.why}: ${(wrong && wrong.message) || wrong}`,
            pageWas: capture(await door.page_text()),
          });
        }
        /* **ONLY FLIPKART'S LATEST DAY HAS KEYWORDS** (the reference's rule), so a
         * latest day before the one asked for is "not available yet", and one after
         * it means the day asked for can no longer be read. Nothing was pressed. */
        if (read && read.shownDay && read.shownDay !== dataDate) {
          if (read.shownDay < dataDate) {
            return anAnswer(NOT_AVAILABLE_YET, reportId, dataDate, {
              say: `Flipkart's latest day on the traffic report is ${read.shownDay}, so the keywords `
                + `for ${dataDate} are not built yet. Nothing was read; this day will be tried again `
                + 'on a later run.',
            });
          }
          return anAnswer(FAILED, reportId, dataDate, {
            say: `Flipkart offers the top search keywords for its latest day only, which is `
              + `${read.shownDay}, so ${dataDate} can no longer be read. Nothing was read.`,
          });
        }
        /* **NO KEYWORDS IS A FAILURE, THE REFERENCE'S OWN WORD FOR IT** -- "no keyword
         * data found". A day with listings and not one keyword read is a page that was
         * not what it looked like, not a quiet day. */
        if (!read || !Array.isArray(read.rows) || !read.rows.length) {
          return anAnswer(FAILED, reportId, dataDate, {
            say: `${(read && read.listings) || 0} listings were looked at and no search keywords `
              + 'were read, so nothing was put away.',
            pageWas: capture(await door.page_text()),
          });
        }
        const called = fileName || theFileName(book, reportId, dataDate);
        if (!called) {
          return anAnswer(FAILED, reportId, dataDate, {
            say: `There is nothing in the recipe file saying what ${reportId}'s file is `
              + 'called, so the keywords have not been put anywhere.',
          });
        }
        const body = new TextEncoder().encode(read.csv);
        try {
          await putTheFile({ reportId, fileName: called, body });
        } catch (wrong) {
          return anAnswer(FAILED, reportId, dataDate, {
            fileName: called,
            size: body.length,
            say: `${body.length} bytes of keywords could not be put in the seller's Drive: `
              + `${(wrong && wrong.message) || wrong}`,
          });
        }
        return anAnswer(LANDED, reportId, dataDate, {
          fileName: called,
          size: body.length,
          say: `Read the top search keywords of ${read.listings} listings over ${read.pages} `
            + `page(s): ${read.rows.length} rows. Landed ${body.length} bytes in the seller's Drive `
            + `as ${called}.`,
        });
      }

      if (step.do === ADD_TO_THE_LIST) {
        /* **NOTHING READ IS A FAILURE, NOT AN EMPTY ROW.** A row of blanks
         * written every night is the quietest way to lose a figure: the day
         * board would say the day arrived, the file would grow, and the numbers
         * would all be missing. */
        if (!readSoFar.size) {
          return anAnswer(FAILED, reportId, dataDate, {
            say: 'Nothing was read off the page, so there is no row to add. A row of blanks '
              + 'would read as a day that arrived.',
          });
        }
        const called = fileName || theFileName(book, reportId, dataDate);
        if (!called) {
          return anAnswer(FAILED, reportId, dataDate, {
            say: `There is nothing in the recipe file saying what ${reportId}'s file is `
              + 'called, so the row has not been added anywhere.',
          });
        }
        const columns = [...readSoFar.keys()];
        /* **THE DAY IS WRITTEN THE WAY EVERYTHING ELSE HERE WRITES ONE.** ISO,
         * the same spelling the file names carry and the same one that reaches
         * the ERP (`reading.a_reading` hands it `data_date=when.isoformat()`). A
         * second spelling of a day is a second record of one fact. */
        const header = ['Date', ...columns].join(',');
        const row = [dataDate, ...columns.map((one) => readSoFar.get(one))].join(',');
        try {
          const added = await addToTheList({
            reportId, fileName: called, header, row, forTheDay: dataDate,
          });
          const size = Number(added && added.size) || 0;
          return anAnswer(LANDED, reportId, dataDate, {
            fileName: called,
            size,
            say: `Added ${dataDate} to ${called} in the seller's Drive: ${row}.`,
          });
        } catch (wrong) {
          return anAnswer(FAILED, reportId, dataDate, {
            fileName: called,
            say: `The row for ${dataDate} could not be added to ${called}: `
              + `${(wrong && wrong.message) || wrong}`,
          });
        }
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
        const called = theCampaignsFileName(fileName || theFileName(book, reportId, dataDate),
          step.campaign, step.campaignsInAll);
        if (!called) {
          return anAnswer(FAILED, reportId, dataDate, {
            say: `There is nothing in the recipe file saying what ${reportId}'s file is `
              + 'called, so it has not been put anywhere. A file put away under a name the '
              + 'scheduled sync cannot read the day out of would never be read at all.',
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
        let put;
        try {
          put = await putTheFile({ reportId, fileName: called, body: got.body });
        } catch (wrong) {
          return anAnswer(FAILED, reportId, dataDate, {
            fileName: called,
            size: got.body.length,
            say: `${got.body.length} bytes came back and could not be put in the seller's `
              + `Drive: ${(wrong && wrong.message) || wrong}`,
          });
        }
        /* **THE SIZE THAT LANDED, NOT THE SIZE THAT CAME DOWN (F15, Job 8, A65,
         * 2026-09-23).** A zip holding one spreadsheet is opened for real before
         * it reaches Drive (`drive.js` `landTheFile`, `unzip.js`
         * `theSpreadsheetInside`), so Drive ends up holding more bytes than the
         * download `got.body` -- measured on `me_payments` 09-20: the log said
         * 8,155 (the zip), Drive held 9,033 (the spreadsheet inside it). `put`
         * carries back what Drive actually has now; a caller with no size to
         * give (a test stub, or an older wiring) still gets the old number. */
        const landedSize = put && put.size !== undefined ? (Number(put.size) || 0) : got.body.length;
        /* **THE FILE THAT NAMES A DAY'S CAMPAIGNS IS READ FOR THEM AS IT LANDS**
         * (2026-09-15), the reference's own moment for it. A failure here is said and
         * never undoes the landing: this report's own file is safely in Drive. */
        const readsTheCampaigns = Object.values(book.recipes)
          .map((one) => one && one.campaignsFrom)
          .find((one) => one && one.report === reportId);
        if (readsTheCampaigns && typeof keepTheCampaigns === 'function') {
          const campaigns = theCampaignsIn(new TextDecoder().decode(got.body), readsTheCampaigns, dataDate);
          if (!campaigns) {
            say(`${reportId}: no "${readsTheCampaigns.idColumn}" and "${readsTheCampaigns.dayColumn}" `
              + 'columns were found in the file, so which campaigns ran is not known.');
          } else {
            try {
              await keepTheCampaigns({ reportId, dataDate, campaigns });
              say(`${reportId}: ${campaigns.length} campaign(s) ran on ${dataDate}.`);
            } catch (wrong) {
              say(`${reportId}: which campaigns ran could not be kept -- `
                + `${(wrong && wrong.message) || wrong}`);
            }
          }
        }
        if (step.campaign) {
          campaignFilesLanded.push({ called, size: landedSize });
          if (step.campaignNumber < step.campaignsInAll) continue;
          return anAnswer(LANDED, reportId, dataDate, {
            fileName: campaignFilesLanded[0].called,
            size: campaignFilesLanded.reduce((all, one) => all + one.size, 0),
            say: `Landed ${campaignFilesLanded.map((one) => `${one.called} (${one.size} bytes)`)
              .join(', ')} in the seller's Drive, one per campaign.`,
          });
        }
        return anAnswer(LANDED, reportId, dataDate, {
          fileName: called,
          size: landedSize,
          say: `Landed ${landedSize} bytes in the seller's Drive as ${called}.`,
        });
      }

      let many = await howManyMatch(step, reportId);
      if (many === 0 && step.do === WAIT_FOR) many = await whatElseCounts(step, reportId);
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
          doing: step.why, matches: many, lookup: step.find,
        });
      }

      if (step.do === READ_NUMBER) {
        /* **THE COLUMN IS NAMED BY THE LOOKUP, not by the order it ran in.** A
         * `called` wins where a recipe gives one, exactly as every failure
         * message in this file uses `called` for what a person would say. */
        const column = step.find.called || step.find.what;
        try {
          readSoFar.set(column, await door.read_number(
            step.find.how, step.find.what, step.find.exact, step.patience,
            step.find.near, step.find.alsoSaying,
          ));
        } catch (wrong) {
          /* **ITS OWN FAILURE, WITH THE DOOR'S OWN WORDS.** The door says which
           * of the three things went wrong -- nothing matched, several matched,
           * or the label is there with no number beside it -- and all three send
           * somebody to a different place. */
          return anAnswer(FAILED, reportId, dataDate, {
            say: `${step.why}: ${(wrong && wrong.message) || wrong}`,
            pageWas: capture(await door.page_text()),
          });
        }
      }

      if (step.do === CLICK) {
        await door.click(step.find.how, step.find.what, step.find.exact, step.find.near,
          false, step.find.alsoSaying, Boolean(step.pressLikeAMouse));
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
      if (step.do === TYPE_IN) {
        await door.type_in(step.find.how, step.find.what, step.find.exact, step.find.near,
          step.find.alsoSaying, step.words);
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
          + 'it is collected at the end of this sync rather than asked for again.',
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
  /* **A RUNNING LIST HAS ONE NAME FOR EVERY DAY, AND THE DAY IS STILL REFUSED
   * FIRST.** The name does not carry it, but the ROW inside does -- so a bad day
   * has to stop here either way, or it reaches the file instead of the name and
   * the day board reads it back as a row nothing can place.
   * `landing.the_running_list_is_called` is the same sentence on the Python
   * side, and `export_recipes.py` carries the flag across so there is one rule
   * and not two. */
  if (whyTheDayIsRefused(dataDate)) return '';
  if (how.aRunningList) return `${how.platform}_${reportId}.${how.extension}`;
  return `${how.platform}_${reportId}_${dataDate}.${how.extension}`;
}

/** An answer with the banners the page showed added to what it says.
 *
 *  **ON SUCCESS AND ON FAILURE ALIKE** (his ruling, 2026-09-14), words only, the
 *  last five. A walk still carrying on is left alone. */
export function withWhatThePageShowed(answer, banners) {
  if (!answer || typeof answer !== 'object' || hasNotFinished(answer)) return answer;
  const said = [];
  for (const one of banners || []) {
    const shown = String((one && one.words) || '').trim();
    if (shown && !said.includes(shown)) said.push(shown);
  }
  if (!said.length) return answer;
  const lastFive = said.slice(-5);
  return {
    ...answer,
    say: `${answer.say ? `${answer.say} ` : ''}The page showed: `
      + `${lastFive.map((one) => `"${one.slice(0, 160)}"`).join(', ')}.`,
    banners: lastFive,
  };
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
