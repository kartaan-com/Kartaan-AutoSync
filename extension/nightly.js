/* Working through a list of reports, one at a time, with nobody watching.
 *
 * **UNTIL THIS EXISTED NOTHING IN THIS PRODUCT COULD START A WALK.** `onDue` was
 * an empty stub and every live run so far happened because a person pasted a
 * line into the service worker's console. A product that cannot begin its own
 * night is not unattended, whatever else is true of it.
 *
 * **ONE AT A TIME, AND NEVER TWICE.** Two walks at once share one tab and one
 * armed download-cancel, and the file that came down could belong to either.
 *
 * **AND IT DOES NOT RETRY. THAT IS THE RULE, NOT A SETTING.** A failed report is
 * written down and the run moves on. The reference's own worst day was an
 * unattended retry loop against a portal that was refusing it, and on Flipkart
 * that spends a seller's daily allowance on the same broken thing twenty times.
 *
 * **THE ALLOWANCE IS THE OTHER HALF OF THIS FILE, AND IT IS COUNTED RATHER THAN
 * TRUSTED.** Flipkart's Reports Centre allows twenty requests a day. Exactly
 * two reports spend from it -- `fk_orders` and `fk_payments`, the two built by
 * `_reports_centre` in `autosync/recipes.py` (returns left it on 2026-09-14). Asking for one of
 * those is a WRITE against the seller's own account and cannot be taken back.
 * So the count is kept where a shut-down worker cannot lose it, it is spent
 * BEFORE the request rather than after, and a run given a limit of nought asks
 * for none of them at all.
 */

/* What the night's own record is called in storage. */
export const THE_NIGHT = 'kartaan-autosync-night';

/* **THE THREE THAT SPEND THE SELLER'S DAILY ALLOWANCE.** Written here as the
 * names they are, because this is the one place that has to know. Flipkart's
 * Reports Centre allows twenty a day; the other ten Flipkart reports and every
 * Meesho one cost nothing.
 *
 * **IF A FOURTH REPORT EVER GOES THROUGH THE REPORTS CENTRE AND IS NOT ADDED
 * HERE, IT WILL SPEND WITHOUT BEING COUNTED.** That is the fault this list can
 * have, and it is why the check beside it compares this list against the recipe
 * file rather than against itself. */
/* **TWO SINCE 2026-09-14, NOT THREE.** `fk_returns` moved to the Returns page by
 * his ruling -- the reference's own route -- and asking there spends none of the
 * twenty. The check beside this list compares it to the recipe file, which is
 * what caught it. */
export const SPENDS_THE_ALLOWANCE = Object.freeze(['fk_orders', 'fk_payments']);

/* **HOW MANY OF THEM A SELLER GETS IN A DAY.** Flipkart's Reports Centre allows
 * twenty. The number was written into the prose at the top of this file and into
 * nothing a program could read, so nothing anywhere could say how many were left
 * -- and `mayAskFor` was therefore decided by whoever started a night, which
 * until there was a screen was nobody, which is why every night was allowed
 * nought and skipped every Flipkart report by name.
 *
 * **IT IS A DAY'S ALLOWANCE, NOT A RUN'S**, and this file counts a run. What
 * counts the day is `screen.js`, which files each finished night's spend under
 * the day it started. */
export const A_DAYS_ALLOWANCE = 20;

/** **HOW MANY OF THE TWENTY THE TIMED SYNC LEAVES FOR HIS OWN RUNS (Control, 2026-10-05).** The timed sync
 *  may spend up to what is left of the day minus this, so his manual runs the same day are not locked out;
 *  its own day for each report is always allowed whatever this says. Both numbers are settings, not code. */
export const KEPT_FOR_HIS_OWN_RUNS = 4;

/**
 * A day, written the way a file name and a report's day are written.
 *
 * **HERE RATHER THAN ON THE SCREEN, because the allowance is a day's and this is
 * the file that counts it.** Written in the seller's own time, because the
 * twenty is a day of theirs.
 */
export function theDay(at) {
  const when = new Date(at);
  const two = (n) => String(n).padStart(2, '0');
  return `${when.getFullYear()}-${two(when.getMonth() + 1)}-${two(when.getDate())}`;
}

/** Does asking for this report cost the seller one of their twenty? */
export function spendsTheAllowance(reportId) {
  return SPENDS_THE_ALLOWANCE.includes(reportId);
}

/**
 * Start a night, and write it down before a single report is touched.
 *
 * `mayAskFor` is how many of the seller's twenty this night is allowed to spend.
 * **NOUGHT IS A REAL ANSWER AND THE SAFE ONE**: a night that is only learning
 * asks for none of them and every one is skipped by name rather than attempted
 * and refused.
 */
export async function startTheNight(chrome, {
  doing, mayAskFor = 0, at = Date.now(), openAt = '', dataDate = '', panel = '', canGoBack = [],
  days = [], latestDay = '', listFrom = {},
}) {
  if (!openAt) {
    /* **REFUSED HERE, BECAUSE THE ALTERNATIVE IS A NIGHT THAT SPENDS AND NEVER
     * FETCHES (A26R4).** With nowhere to start from, every walk this night tries
     * to start throws -- and the allowance is spent BEFORE the walk, so each
     * throw costs one of the seller's twenty and produces nothing. It is the
     * easiest way to reach the retry loop below and it was reachable by simply
     * leaving one argument off. */
    throw new Error('A sync has to be told which portal page its reports start from.');
  }
  const night = {
    startedAt: at,
    /* Where the night's reports are walked from, and which day they are for.
     * **ONE PLATFORM PER NIGHT**, because one portal page is where every walk in
     * this list begins -- said here rather than worked out from a report's name,
     * which would be platform knowledge in a file that has none. */
    openAt,
    dataDate,
    /* **AND THE SELLER'S OWN PANEL NAME, WHICH IS THE SAME KIND OF FACT AS THE
     * TWO ABOVE.** All five Meesho recipes carry `{panel}` in an address, and
     * `walk.js` refuses a step carrying one without it, in words -- which is the
     * sentence he read twice on 9 September with the name saved on the page.
     *
     * **IT IS DECIDED ONCE, WHEN THE NIGHT STARTS, AND NOT READ AGAIN.** Read
     * afresh at each walk, a seller editing the box while a run is going would
     * have report three walking a different panel from report one. A night is
     * already one platform's and one day's; it is one panel's too.
     *
     * **IT IS HERE RATHER THAN IN THE WIRING BECAUSE THE WIRING CANNOT BE
     * CHECKED.** The join used to be one line in `worker.js`, which has no
     * checks by design -- so deleting it left every check green and left a
     * seller with a report that fails for the one reason the panel had already
     * asked him about. What a run needs to do its job is a decision, and a
     * decision does not belong in a file nothing can prove.
     *
     * **THE REFUSAL STAYS WHERE IT IS.** Nothing here guesses a name and nothing
     * here fails quietly: a night with no panel hands none to the walk, and the
     * walk refuses that report by name, in the seller's own words. */
    panel: String(panel || ''),
    /* **WHICH OF THESE REPORTS CAN BE FETCHED FOR A PAST DAY (A53).** Only those
     * have a failed day tried again on later syncs -- Rumee's `gap-catchup.js`,
     * which leaves out reports the platform only gives as a rolling window. */
    canGoBack: [...(canGoBack || [])],
    /* **THE NEWEST DAY ANY PLATFORM HAS PUBLISHED WHEN THIS SYNC STARTED**, so a
     * day the seller typed can be told apart from the ordinary one. A report that
     * cannot go back is left out of a past day rather than failed on it (his
     * ruling, 2026-09-16: *"when run is for past day it will ignore meesho views
     * as it is not available"*). */
    latestDay: String(latestDay || ''),
    /* **EVERY DAY THIS SYNC IS FOR, oldest first (A53).** One day unless the seller
     * asked for a stretch of them in the panel's two date boxes. */
    days: [...(days || [])],
    /* **A57, JOB 2: WHICH REPORT READS WHICH ONE'S LIST** (`fk_ads_overall` reads
     * `fk_ads_daily`), so the list is fetched for every day its reader owes. */
    listFrom: { ...(listFrom || {}) },
    finishedAt: null,
    left: [...doing],
    done: [],
    /* **SPENT, NOT REMAINING.** A number that counts down reads as "how many are
     * left" from every angle and is right from none of them: two runs both
     * reading 6 both believe they may spend 6. What was spent only ever grows. */
    spent: 0,
    /* **AND WHICH DAY EACH ONE WAS SPENT ON.** `spent` is this night's total and
     * says nothing about when. **A night begun at five to midnight spends
     * requests on two different days**, and Flipkart's twenty is a DAY's, so a
     * total filed under the day the night started puts today's requests on
     * yesterday's ledger -- and today then reads twenty left while three have
     * already gone. Found by an independent reviewer, 2026-09-09, who called it
     * blocking: twenty-three real, irrevocable writes against a seller's own
     * account in one day. */
    spentOn: {},
    mayAskFor: Math.max(0, Number(mayAskFor) || 0),
  };
  await chrome.storage.local.set({ [THE_NIGHT]: night });
  return night;
}

/** The night as it stands, read back rather than remembered. */
export async function theNight(chrome) {
  const held = await chrome.storage.local.get(THE_NIGHT);
  return held[THE_NIGHT] || null;
}

/* ------------------------------------------- what a platform is still building
 *
 * **WHAT ONE RUN ASKED FOR AND A LATER RUN HAS TO COLLECT, AND IT IS NOT ON THE
 * NIGHT.** The night is one record, rewritten by the next run -- and a report
 * asked for tonight is collected tomorrow night, or an hour later, by a run that
 * has never heard of this one. Kept on the night it would be gone by then.
 *
 * **WITHOUT THIS, EVERY RUN ASKS AGAIN. MEASURED ON HIS OWN FLIPKART,
 * 2026-09-11.** `fk_orders` was asked for, Flipkart built it and listed it as
 * Generated -- and the very next run walked the ASKING phase again from the top.
 * `walk.js` had handed back what it was asked under all along, with its own
 * comment saying *"holding it is what stops this being asked a second time"*,
 * and **nothing anywhere stored it or read it back.** Five reports could never
 * produce a file: `fk_orders`, `fk_returns`, `fk_payments`, `fk_views`,
 * `fk_listings`. **And on Flipkart it is worse than a missing file** -- its
 * Reports Centre allows twenty requests a day, so re-asking burns the seller's
 * allowance on reports the platform already has in hand, which is the
 * reference's own lock-out arriving by another door.
 *
 * **AND THE SELLER WAS TOLD THE OPPOSITE IN PLAIN WORDS**: *"a later run will
 * collect it rather than asking again."* That sentence is true from here on. It
 * was not before.
 *
 * **IT IS THE SAME RECORD THE PYTHON HALF ALREADY KEEPS, and it is deliberately
 * the same word for it** -- `between_runs.Between.in_flight`, a map from a
 * report and the day it is about to what the platform calls the thing it is
 * making. Two halves inventing two vocabularies for one fact is how they come to
 * disagree.
 */
export const WHAT_IS_BEING_BUILT = 'kartaan-autosync-being-built';

/** One report and one day, as one key. **Both, because a report can be owed two
 *  days at once** -- a day that failed and last night's -- and they are being
 *  built separately, under different names. */
function thatOneAndThatDay(reportId, dataDate) {
  return `${reportId}|${dataDate}`;
}

/** What every platform is still building, as it stands. */
export async function whatIsBeingBuilt(chrome) {
  const held = await chrome.storage.local.get(WHAT_IS_BEING_BUILT);
  const record = held[WHAT_IS_BEING_BUILT];
  /* **A MISSING RECORD IS AN ORDINARY FIRST NIGHT.** Nothing has been asked for
   * yet, so nothing is being built. */
  return (record && typeof record === 'object') ? record : {};
}

/** What this one report, for this one day, was asked for under -- or nothing. */
export async function whatThatWasAskedUnder(chrome, reportId, dataDate) {
  const being = await whatIsBeingBuilt(chrome);
  return being[thatOneAndThatDay(reportId, dataDate)] || null;
}

/* ------------------------------------------ a day the platform has not built yet
 *
 * **HIS RULING, 2026-09-14, IN HIS WORDS:** *"this is a permanent problem in
 * Flipkart. There will be scenarios when a report will not be available for a
 * date. In that case Rumee AutoSync used to mark that as not available and moves
 * ahead... that is a better way to implement in Kartaan also."*
 *
 * **MEASURED THE SAME DAY.** On the 14th Flipkart's Reports Centre greyed out
 * every day after the 11th, and Seller Insights' own `Latest` read the 12th. Both
 * walks refused at the calendar exactly as they should -- and were written down
 * as FAILED, never tried again, and the Reports Centre one still used one of the
 * seller's twenty without asking Flipkart for anything.
 *
 * **SO IT IS DONE THE REFERENCE'S WAY** (`content/flipkart.js:1331-1346`,
 * `gap-catchup.js`): the day is not a failure, it is OWED. Every later run that
 * does the report tries its oldest owed day first and its own day after, and a
 * day still not built on the THIRD different day it was tried is no longer tried
 * and is written down as needing the seller. **Three is the reference's
 * `GAP_CATCHUP_MAX_DAYS` and this product's own `schedule.GIVE_UP_AFTER_DAYS`.**
 *
 * **THREE DIFFERENT DAYS, NOT THREE TRIES.** Pressing Run now twice in one
 * morning must not use up a day that simply is not there yet.
 */
export const NOT_BUILT_YET = 'kartaan-autosync-not-built-yet';
export const NEEDS_YOU = 'kartaan-autosync-needs-you';
export const GIVE_UP_AFTER_DAYS = 3;
/* The walk's own word for it (`walk.NOT_AVAILABLE_YET`, which a check holds this
 * to) and the word the night turns it into on the last day. */
export const NOT_AVAILABLE_YET = 'not-available-yet';
export const NEEDS_YOU_STATE = 'needs-you';

/** Every report-day still owed because the platform had not built it. */
export async function whatIsNotBuiltYet(chrome) {
  const held = await chrome.storage.local.get(NOT_BUILT_YET);
  const record = held[NOT_BUILT_YET];
  return (record && typeof record === 'object') ? record : {};
}

/** Every report-day given up on, for the seller to fetch by hand. */
export async function whatNeedsYou(chrome) {
  const held = await chrome.storage.local.get(NEEDS_YOU);
  return Array.isArray(held[NEEDS_YOU]) ? held[NEEDS_YOU] : [];
}

/**
 * Clear specific "needs you" entries by hand -- his yes, once, never a general
 * escape hatch (Job 7, A64, 2026-09-23).
 *
 * **NAMED ENTRIES ONLY, NEVER A WILDCARD.** This is his record of what still
 * needs him; the ordinary way OFF it is a later sync landing the day
 * (`rememberWhatIsNotBuilt` above, state `landed`/`still-waiting`) -- a day is
 * only ever cleared THAT way because it was really dealt with. This function
 * exists for the rare case a day never will be (Flipkart's own calendar will
 * not reach it, or the platform no longer offers it), and it takes an exact
 * list of `{reportId, dataDate}` (or `{reportId, month}` for a whole month) to
 * remove -- so calling it can only ever clear what was actually named and
 * approved, never "everything" or "everything for a report".
 */
export async function clearNamedNeedsYouEntries(chrome, entries) {
  const list = Array.isArray(entries) ? entries : [];
  const matches = (one) => list.some((named) => named && one
    && named.reportId === one.reportId
    && (named.dataDate ? named.dataDate === one.dataDate
      : named.month ? String(one.dataDate).startsWith(named.month)
        : false));
  const needsYou = await whatNeedsYou(chrome);
  const cleared = needsYou.filter(matches);
  const kept = needsYou.filter((one) => !matches(one));
  await chrome.storage.local.set({ [NEEDS_YOU]: kept });
  return cleared;
}

/* **A COLLECT THAT IS NOT READY IS CHECKED AGAIN EVERY HOUR, THREE TIMES --
 * RUMEE'S WAY (A53, his explanation 2026-09-16).** Rumee schedules a one-hour
 * recheck per report, at most three, then gives up for the day
 * (`D:\rumee-auto-sync\content\flipkart.js:2595-2609`, `background.js:1937-1976`).
 * After the third, the day is "not ready today" and the next sync tries again. */
export const RECHECKS = 'kartaan-autosync-rechecks';
export const RECHECK_ALARM = 'kartaan-autosync-recheck';
export const RECHECK_TIMES = 3;
export const RECHECK_AFTER_MINUTES = 60;

/** Reports with no asking phase -- a live page is read once, nothing is
 *  requested from the platform -- so a failed one never appears in
 *  `WHAT_IS_BEING_BUILT`, which is what the recheck below asks for before it
 *  will try again. **Measured live, Job 3b, 2026-09-22:** `me_views` failed
 *  once ("the views card for the day... not on the page at all") and landed
 *  on the very next try with nothing else changed -- the dashboard had
 *  simply not finished drawing. Named here rather than left to the same
 *  rule as a two-phase report, because there is no `theirId` to have missed. */
export const RECHECK_EVEN_WITHOUT_AN_ASK = Object.freeze(['me_views']);

/* **FLIPKART TRAFFIC IS ASKED FROM THE DAY AFTER THE LAST ONE CAPTURED -- RUMEE'S WAY
 * (A53, his "yes").** Rumee remembers `fk_views_last_to` from the latest date inside
 * the file, never from the request (`D:\rumee-auto-sync\content\flipkart.js:2522-2585`):
 * a file for 07-03 once held only 07-02. */
export const LAST_CAPTURED = 'kartaan-autosync-last-captured';
export const RANGE_FROM_LAST = Object.freeze(['fk_views']);

/** Remember the last day a report's file really held. It never moves backwards. */
export async function rememberLastCaptured(chrome, reportId, day) {
  const held = (await chrome.storage.local.get(LAST_CAPTURED))[LAST_CAPTURED] || {};
  if (held[reportId] && String(held[reportId]) >= String(day)) return held[reportId];
  await chrome.storage.local.set({ [LAST_CAPTURED]: { ...held, [reportId]: String(day) } });
  return String(day);
}

/** The day after the last one captured, when that is before this day; otherwise nothing. */
export async function theDayAfterTheLastCaptured(chrome, reportId, day) {
  if (!RANGE_FROM_LAST.includes(reportId)) return '';
  const last = ((await chrome.storage.local.get(LAST_CAPTURED))[LAST_CAPTURED] || {})[reportId];
  if (!last) return '';
  const after = new Date(`${last}T00:00:00Z`);
  after.setUTCDate(after.getUTCDate() + 1);
  const from = after.toISOString().slice(0, 10);
  return from < String(day) ? from : '';
}

/* ------------------------------------------ days nobody ever tried (A63, Job 6)
 *
 * **A DAY IN `NOT_BUILT_YET` IS A DAY SOMETHING TRIED AND THE PLATFORM REFUSED.
 * A DAY NOBODY EVER TRIED IS NOWHERE AT ALL.** Meesho orders for 09-17, 09-18
 * and 09-19 went missing exactly this way (F14): the timed sync's own list held
 * only two Flipkart ad reports for three days running (F5), so `me_orders`
 * never even started for those days -- no walk, no refusal, nothing written
 * down. Every mechanism above this line only ever retries a day it already
 * knows about, so nothing was ever going to fetch them.
 *
 * **THE SAME RULE `autosync/schedule.py` ALREADY WRITES FOR THE OTHER DOOR
 * (its own Rule 13): a day is owed from CALENDAR TIME since the last real
 * file, never from whether an attempt happened to run.** This is that rule,
 * kept for the browser door, which has no Drive listing of its own the way the
 * Python side reads -- so it is kept locally, per report, as EVERY day this
 * browser knows a file really landed for -- never only the newest one.
 *
 * **A SINGLE HIGH-WATER MARK CANNOT SEE A HOLE BEHIND A LATER LANDED DAY, AND
 * F14 IS EXACTLY THAT SHAPE.** His own Drive has `me_orders` landed for 09-16,
 * then missing for 09-17..09-19, then landed again for 09-20 (a later sync
 * caught up on the days it was itself given, past the hole). A record of only
 * "the newest day landed" would already read 09-20 and would never look
 * backward through it -- so this keeps the full set, the same shape
 * `schedule.py`'s own `days_that_arrived`/`what_is_owed` already use for the
 * identical question on the other door (its `have: Set[date]`, not a single
 * newest date). */
export const LAST_LANDED = 'kartaan-autosync-last-landed';

/* **KEPT BOUNDED, so a report that lands roughly once a day does not grow this
 * record without limit over the product's life.** Comfortably more than
 * `CATCH_UP_REACH_DAYS` below, since nothing older than that window is ever
 * read by `daysNobodyTried` anyway. */
const REMEMBER_AT_MOST_LANDED_DAYS = 60;

/**
 * **HOW FAR BACK A CATCH-UP MAY REACH, so a report broken for months is not
 * silently walked back through all of it in one sync -- that is Job 15's job,
 * asked of him, not this one's.** One number, changeable in one place
 * (`docs/PLAN_TO_FINISH.md`, Job 6).
 *
 * **14, FROM WHAT IS ALREADY IN THIS CODEBASE FOR THE SAME QUESTION ON THE
 * OTHER DOOR**, not a fresh guess: `autosync/runner.py` already calls
 * `schedule.what_is_owed(..., look_back_days=14)` for Amazon's own nightly
 * catch-up (`schedule.py`'s own default is 30; 14 is the number actually
 * running). Comfortably inside what either platform documents here: Flipkart's
 * Reports Centre opens its own calendar with a 30-day range already chosen
 * (`docs/FLIPKART.md`, Job 4), and Meesho's date-ranged reports are asked for a
 * month at a time (`docs/PLAN_A53_BEFORE_CODING.md` item 8).
 */
export const CATCH_UP_REACH_DAYS = 14;

/** Add one more day to what this report is known to have really landed.
 *  **A SET, NOT A SCALAR** -- see the block comment above for why a single
 *  newest day cannot find F14's own hole. Silently no-ops on a day already
 *  known, and trims the oldest once the bound is passed. */
export async function rememberLastLanded(chrome, reportId, day) {
  const held = (await chrome.storage.local.get(LAST_LANDED))[LAST_LANDED] || {};
  const already = held[reportId] || [];
  if (already.includes(String(day))) return already;
  const days = [...already, String(day)].sort();
  const kept = days.length > REMEMBER_AT_MOST_LANDED_DAYS
    ? days.slice(days.length - REMEMBER_AT_MOST_LANDED_DAYS) : days;
  await chrome.storage.local.set({ [LAST_LANDED]: { ...held, [reportId]: kept } });
  return kept;
}

/**
 * Every day in the last `CATCH_UP_REACH_DAYS` before this sync's own day that
 * this report has no landed file for, and nothing has ever recorded a reason
 * for either -- not tried and refused (`NOT_BUILT_YET`), not already handed to
 * him (`NEEDS_YOU`). Oldest first.
 *
 * **NOTHING IS OWED WITH NO KNOWN STARTING POINT.** A report that has never
 * landed a single file yet has nothing to measure a gap against, so this
 * answers nothing for it -- exactly as today, before a first file has ever
 * landed there is no gap to speak of, only the ordinary first fetch.
 */
export async function daysNobodyTried(chrome, reportId, day) {
  const held = (await chrome.storage.local.get(LAST_LANDED))[LAST_LANDED] || {};
  const landedDays = held[reportId];
  if (!landedDays || !landedDays.length) return [];
  const landed = new Set(landedDays);
  const notBuilt = await whatIsNotBuiltYet(chrome);
  const needsYou = await whatNeedsYou(chrome);
  const known = new Set([
    ...Object.values(notBuilt).filter((one) => one && one.reportId === reportId).map((one) => one.dataDate),
    ...needsYou.filter((one) => one && one.reportId === reportId).map((one) => one.dataDate),
  ]);
  const cursor = new Date(`${day}T00:00:00Z`);
  cursor.setUTCDate(cursor.getUTCDate() - CATCH_UP_REACH_DAYS);
  /* **NOTHING IS OWED BEFORE THE FIRST DAY THIS REPORT EVER LANDED (review finding, 2026-10-05):** that is the
   * "known starting point" the paragraph above promises; the reach used to run past it. */
  const firstLanded = [...landedDays].sort()[0];
  if (cursor.toISOString().slice(0, 10) < firstLanded) cursor.setTime(new Date(`${firstLanded}T00:00:00Z`).getTime());
  const gap = [];
  while (cursor.toISOString().slice(0, 10) < String(day)) {
    const one = cursor.toISOString().slice(0, 10);
    if (!landed.has(one) && !known.has(one)) gap.push(one);
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return gap;
}

/** A sync paused because a platform asked to be signed in to: what to resume from. */
export const PAUSED = 'kartaan-autosync-paused';

/** The paused sync, or null when nothing is paused. */
export async function whatIsPaused(chrome) {
  const held = (await chrome.storage.local.get(PAUSED))[PAUSED];
  return held && Array.isArray(held.reportIds) && held.reportIds.length ? held : null;
}

/** Every report-day waiting for its next hourly check. */
export async function whatIsBeingRechecked(chrome) {
  const held = await chrome.storage.local.get(RECHECKS);
  const record = held[RECHECKS];
  return (record && typeof record === 'object') ? record : {};
}

/** Put the hourly check on the clock when anything is waiting for one. */
export async function setTheRecheckClock(chrome) {
  if (!Object.keys(await whatIsBeingRechecked(chrome)).length) return false;
  await chrome.alarms.create(RECHECK_ALARM, { delayInMinutes: RECHECK_AFTER_MINUTES });
  return true;
}

/** The one sync an hourly check runs: the oldest day waiting, and its reports. */
export function theRecheckSync(rechecks) {
  const all = Object.values(rechecks || {}).filter((one) => one && one.reportId && one.dataDate);
  if (!all.length) return null;
  const day = all.map((one) => String(one.dataDate)).sort()[0];
  return {
    day,
    reportIds: [...new Set(all.filter((one) => one.dataDate === day).map((one) => one.reportId))],
  };
}

/** The days before this one still owed for this report, oldest first. */
export async function theDaysStillOwed(chrome, reportId, dataDate) {
  const held = await whatIsNotBuiltYet(chrome);
  return Object.values(held)
    .filter((one) => one && one.reportId === reportId && one.dataDate
      && String(one.dataDate) < String(dataDate))
    .map((one) => one.dataDate)
    .sort();
}

/** Remember, forget or give up on a day not built, and say what to write down. */
async function rememberWhatIsNotBuilt(chrome, {
  reportId, day, state, say, at, owed = false, listMissing = false,
}) {
  const key = thatOneAndThatDay(reportId, day);
  const notBuilt = await whatIsNotBuiltYet(chrome);
  const needsYou = await whatNeedsYou(chrome);
  /* **A57, JOB 2: A DAY WHOSE CAMPAIGN LIST WAS NEVER FETCHED IS OWED, NOT COUNTED.**
   * Nothing is wrong on the platform; the next sync pulls the list in first (`listFrom`).
   * Counted, it reached "needs you" on 09-18..09-21 with the list never fetched. */
  if (state === NOT_AVAILABLE_YET && listMissing) {
    const held = notBuilt[key] || { reportId, dataDate: day, triedOn: [] };
    await chrome.storage.local.set({ [NOT_BUILT_YET]: { ...notBuilt, [key]: held } });
    return { state, say: `${say} Its campaign list is fetched first on the next sync.` };
  }
  /* **A FAILED DAY IS OWED TOO, FOR A REPORT THAT CAN GO BACK (A53, his ruling;
   * Rumee's `gap-catchup.js`).** Same record, same three days, same "needs you". */
  if (state === NOT_AVAILABLE_YET || (state === 'failed' && owed)) {
    const on = theDay(at || Date.now());
    const held = notBuilt[key] || { reportId, dataDate: day, triedOn: [] };
    const triedOn = held.triedOn.includes(on) ? held.triedOn : [...held.triedOn, on];
    if (triedOn.length < GIVE_UP_AFTER_DAYS) {
      await chrome.storage.local.set({ [NOT_BUILT_YET]: { ...notBuilt, [key]: { ...held, triedOn } } });
      return {
        state,
        say: `${say} Tried on ${triedOn.length} of ${GIVE_UP_AFTER_DAYS} days.`
          + `${state === 'failed' ? ' It is tried again on the next sync.' : ''}`,
      };
    }
    const without = { ...notBuilt };
    delete without[key];
    const told = `${day} ${state === 'failed' ? 'still failed' : 'was still not available'} `
      + `after being tried on ${GIVE_UP_AFTER_DAYS} `
      + `different days (${triedOn.join(', ')}), so it will not be tried again. `
      + 'It needs you: fetch it by hand from the platform.';
    await chrome.storage.local.set({
      [NOT_BUILT_YET]: without,
      [NEEDS_YOU]: [
        ...needsYou.filter((one) => thatOneAndThatDay(one.reportId, one.dataDate) !== key),
        { reportId, dataDate: day, triedOn, since: on, say: told },
      ],
    });
    return { state: NEEDS_YOU_STATE, say: told };
  }
  /* **FORGOTTEN THE MOMENT THE DAY TURNS OUT TO BE THERE** -- landed, or asked
   * for and being built -- and taken off what needs the seller too, so a day
   * fetched by a later run stops being shown as theirs to do. */
  if (state === 'landed' || state === 'still-waiting') {
    if (notBuilt[key] !== undefined) {
      const without = { ...notBuilt };
      delete without[key];
      await chrome.storage.local.set({ [NOT_BUILT_YET]: without });
    }
    if (needsYou.some((one) => thatOneAndThatDay(one.reportId, one.dataDate) === key)) {
      await chrome.storage.local.set({
        [NEEDS_YOU]: needsYou.filter((one) => thatOneAndThatDay(one.reportId, one.dataDate) !== key),
      });
    }
  }
  return { state, say };
}

/** The night with the one request it counted for this report-day given back.
 *
 *  **ONLY EVER THE ONE IT COUNTED, AND ONLY BEFORE A SUBMIT.** A day refused at
 *  the calendar asked Flipkart for nothing -- the calendar comes before Submit --
 *  so the count said a request went that did not. */
function theCountGivenBack(night) {
  const spentOn = { ...(night.spentOn || {}) };
  const on = night.lastCounted.on;
  if (Number(spentOn[on]) > 0) spentOn[on] = Number(spentOn[on]) - 1;
  return { spent: Math.max(0, (Number(night.spent) || 0) - 1), spentOn, lastCounted: null };
}

/**
 * May this report be asked for, and what to say if not.
 *
 * **ASKED BEFORE THE REQUEST, NEVER AFTER.** A request that has gone cannot be
 * taken back, so a count checked afterwards is a count that has already been
 * exceeded.
 */
/* **THE REPORTS THAT EXIST ONLY FOR THE DAY THEY ARE TAKEN, AND THIS IS NOT THE
 * SAME AS "CANNOT BE ASKED FOR AGAIN".** Both kinds say a past day cannot be
 * asked for, and the difference decides whether a seller gets a file at all:
 *  - a PICTURE OF NOW (these three) has no history behind it. Meesho's dashboard
 *    card reads `Views (15 Sep)` and nothing else, so a sync for the 6th looks
 *    for a card that can never be drawn. MEASURED on his own panel, 2026-09-16.
 *  - a ROLLING WINDOW -- `me_returns`, `me_claims` -- hands over whatever is in
 *    the tab now. Overlapping days are expected and settled by the ticket or
 *    tracking number, and those DID land on his past-day run this morning. Left
 *    out here they would be lost, so they are not in this list.
 * The check beside it compares this list to the recipe file, the same way
 * `SPENDS_THE_ALLOWANCE` is compared, so the two records cannot drift apart. */
export const ONLY_ITS_NEWEST_DAY = Object.freeze(['me_views', 'me_catalog', 'me_ads']);

/**
 * Is this a report the platform only gives for its newest day, asked for an older one?
 *
 * **HIS RULING, 2026-09-16: *"when run is for past day it will ignore meesho views
 * as it is not available"*.** Meesho's dashboard card says `Views (15 Sep)` and
 * nothing else -- there is no history behind it -- so a sync for the 6th was
 * looking for a card that can never be drawn. It failed, and the failure blamed a
 * promotion that happened to be covering the page, which sent a whole session
 * after the wrong thing.
 *
 * **LEFT OUT BY NAME, NOT DROPPED.** It is written down as nothing to fetch with
 * the reason in words, so the run log says why the file is not there.
 */
export function whyOnlyItsNewestDay(night, reportId, day) {
  if (!ONLY_ITS_NEWEST_DAY.includes(reportId)) return null;
  if (!night || !night.latestDay || !day) return null;
  if (String(day) >= String(night.latestDay)) return null;
  return `${reportId} is a picture of how things stand now -- the platform keeps no history `
    + `to ask for -- so ${day} is not available and was not asked for.`;
}

export function whyItCannotBeAskedFor(night, reportId, collecting = false) {
  if (!spendsTheAllowance(reportId)) return null;
  /* **COLLECTING SOMETHING ALREADY BUILT SPENDS NOTHING, AND REFUSING IT WOULD
   * BE THE WORST OF BOTH.** The twenty are REQUESTS; coming back for a finished
   * report is a page and a download. Refused here, a day that had spent its
   * allowance could never collect the very reports it spent it on -- so the
   * requests would be gone and the files would never arrive. */
  if (collecting) return null;
  if (!night) return 'There is no run to count this against.';
  if (night.spent >= night.mayAskFor) {
    return `Asking for ${reportId} spends one of the seller's twenty Flipkart requests for the `
      + `day, and this run was allowed ${night.mayAskFor} and has used ${night.spent}. `
      + 'It has not been asked for.';
  }
  return null;
}

/**
 * Write down that one of the seller's twenty has been spent.
 *
 * **CALLED BEFORE THE REQUEST GOES, and that ordering is the whole of it.** A
 * worker shut down between the request and the counting leaves a request that
 * happened and a count that says it did not -- and the next run spends it again.
 * Counted first, the worst case is a request counted that never went, which
 * costs a report and not an allowance.
 */
export async function oneWasAskedFor(chrome, { at = Date.now(), counting = '' } = {}) {
  const night = await theNight(chrome);
  if (!night) return null;
  /* **STAMPED WITH THE DAY IT IS BEING SPENT ON, at the one moment that day is
   * known for certain.** Worked out afterwards from when the night started, or
   * from when a report finished, it is a guess about a request that has already
   * gone. */
  const day = theDay(at);
  const spentOn = { ...(night.spentOn || {}) };
  spentOn[day] = (Number(spentOn[day]) || 0) + 1;
  /* **AND WHICH REPORT-DAY IT WAS COUNTED FOR**, so a day then refused at the
   * calendar -- before anything was asked -- can have exactly this one back. */
  const spent = {
    ...night, spent: night.spent + 1, spentOn, lastCounted: counting ? { key: counting, on: day } : null,
  };
  await chrome.storage.local.set({ [THE_NIGHT]: spent });
  return spent;
}

/**
 * Take one report off what the night still owes, because it is being attempted.
 *
 * **THIS IS WHAT MAKES A RETRY LOOP IMPOSSIBLE, AND IT IS THE WHOLE OF A26R4'S
 * WORST FINDING.** A report used to leave `left` only when it FINISHED. So a
 * report whose walk could not even be STARTED stayed owed -- while the allowance
 * for it had already been spent -- and the alarm that wakes this worker every
 * two minutes walked straight back into it. Measured on a copy: **twenty real
 * Flipkart requests for one report in eighty minutes**, and the summary blaming
 * the allowance. That is the exact catastrophe the top of this file says it
 * exists to prevent, arriving through the one door nobody had watched.
 *
 * **ATTEMPTED IS ENOUGH. A report is never attempted twice, whatever happened.**
 */
export async function thatOneIsBeingTried(chrome, reportId, day = null) {
  const night = await theNight(chrome);
  if (!night) throw new Error('Nothing can be attempted against a sync that is not going.');
  /* **AND WHICH ONE IT IS, BECAUSE OTHERWISE IT IS IN NEITHER LIST.** Taking a
   * report off `left` the moment it is attempted is what makes a retry loop
   * impossible -- but it also means a report being walked right now is neither
   * owed nor done, and a summary built from those two lists would not mention it
   * at all. On the night of 6 September the opposite fault showed: `fk_views`
   * was walking, was still in `left`, and the summary called it "never
   * reached". It had reached; it was in the middle of the job. */
  /* **ONE DAY OFF, AND THE REPORT OFF THE LIST ONLY WHEN IT HAS NO DAYS LEFT.**
   * A report owed an earlier day the platform had not built is walked once per
   * day this night -- see `NOT_BUILT_YET` -- and every attempt takes a day away,
   * so the list still only ever shrinks. */
  const daysLeft = { ...(night.daysLeft || {}) };
  if (day !== null && daysLeft[reportId]) {
    daysLeft[reportId] = daysLeft[reportId].filter((one) => one !== day);
  }
  const stillOwed = (daysLeft[reportId] || []).length > 0;
  const moved = {
    ...night,
    doing: reportId,
    daysLeft,
    left: stillOwed ? night.left : night.left.filter((one) => one !== reportId),
  };
  await chrome.storage.local.set({ [THE_NIGHT]: moved });
  return moved;
}

/**
 * Write down what became of one report, and move the night on.
 *
 * **WRITTEN AS IT HAPPENS, NOT AT THE END.** The reference kept the whole run in
 * memory and wrote it out when it finished, so an interruption took the lot.
 */
export async function thatOneIsDone(chrome, {
  reportId, state, say = '', size = 0, at, pageWas = '', theirId = null, dataDate = '',
  listMissing = false, needsSigningIn = false, settled = false,
}) {
  const night = await theNight(chrome);
  if (!night) throw new Error('Nothing can be recorded against a sync that is not going.');

  /* **WHAT THE PLATFORM IS BUILDING IS WRITTEN DOWN HERE, at the one moment it
   * is known, and it is the only thing in this function that outlives the
   * night.** See `WHAT_IS_BEING_BUILT` above for what it cost not to have it.
   *
   * **THE DAY COMES FROM THE NIGHT WHEN THE CALLER DOES NOT SAY**, because that
   * is the day the night is fetching and a walk cannot be walking another one. */
  const day = dataDate || night.dataDate || '';
  /* **WHAT IS WRITTEN DOWN IS NOT ALWAYS WHAT THE WALK SAID.** A day still not
   * built on its third day becomes one that needs the seller. */
  let written = { state, say };
  /* **A SIGN-IN WALL IS NOT A FACT ABOUT THE PLATFORM, SO IT IS BOOKED AS NOTHING.** It used to be
   * counted as one more "tried" day for a report that can go back, so three syncs on three days with
   * the seller signed out (Flipkart's sign-in takes a code they must type) turned a day nobody ever
   * reached into "the platform never built it, it will not be tried again" and dropped it for good.
   * The failure is still written in the night's own list; nothing else remembers it. */
  if (day && !needsSigningIn) {
    const being = await whatIsBeingBuilt(chrome);
    const key = thatOneAndThatDay(reportId, day);
    if (state === 'still-waiting' && theirId) {
      await chrome.storage.local.set({
        [WHAT_IS_BEING_BUILT]: { ...being, [key]: theirId },
      });
    } else if (state === 'landed' || state === 'nothing-to-fetch') {
      /* **FORGOTTEN ONLY WHEN THERE IS NOTHING LEFT TO COLLECT.** A collect that
       * FAILED is still a report the platform has in hand -- forgetting it there
       * would send the next run round to ask for it again, which is the whole
       * fault this record exists against. `landed` is done; `nothing-to-fetch`
       * means there was never anything to come. */
      if (being[key] !== undefined) {
        const without = { ...being };
        delete without[key];
        await chrome.storage.local.set({ [WHAT_IS_BEING_BUILT]: without });
      }
    }
    /* **A COLLECT THAT FAILED IS CHECKED AGAIN IN AN HOUR, THREE TIMES** (see
     * `RECHECKS`). A report is being collected when the platform is already
     * building it. After the third, it is "not ready today" for the next sync. */
    const rechecks = await whatIsBeingRechecked(chrome);
    let asState = state;
    let asSay = say;
    let rechecking = false;
    if (state === 'failed' && (being[key] !== undefined || RECHECK_EVEN_WITHOUT_AN_ASK.includes(reportId))) {
      const tries = ((rechecks[key] && rechecks[key].tries) || 0) + 1;
      if (tries <= RECHECK_TIMES) {
        await chrome.storage.local.set({
          [RECHECKS]: { ...rechecks, [key]: { reportId, dataDate: day, tries } },
        });
        rechecking = true;
        written = {
          state: 'still-waiting',
          say: `${say} Not ready yet, so it is checked again in an hour (${tries} of ${RECHECK_TIMES}).`,
        };
      } else {
        asState = NOT_AVAILABLE_YET;
        asSay = `${say} Still not ready after ${RECHECK_TIMES} hourly checks: not ready today, `
          + 'and tried again on the next sync.';
      }
    }
    if (!rechecking && rechecks[key] !== undefined) {
      const without = { ...rechecks };
      delete without[key];
      await chrome.storage.local.set({ [RECHECKS]: without });
    }
    if (!rechecking) {
      written = await rememberWhatIsNotBuilt(chrome, {
        reportId, day, state: asState, say: asSay, at,
        owed: (night.canGoBack || []).includes(reportId),
        listMissing,
      });
    }
  }
  /* **A DAY THE WALK FOUND NOTHING TO FETCH FOR IS SETTLED, NOT OWED AGAIN (review finding, 2026-10-05).** Only
   * days that really landed were remembered, so a day with no campaign running (or none to record) was walked
   * again on every sync for the whole reach. `settled` comes from the walk's own answer only -- never from the
   * allowance or the only-its-newest-day refusals, which are not facts about the platform. */
  if (settled && day) await rememberLastLanded(chrome, reportId, day);
  const counted = thatOneAndThatDay(reportId, day);
  const givenBack = ((written.state === NOT_AVAILABLE_YET || written.state === NEEDS_YOU_STATE)
    && night.lastCounted && night.lastCounted.key === counted)
    ? theCountGivenBack(night) : {};
  const daysLeft = { ...(night.daysLeft || {}) };
  if (daysLeft[reportId]) daysLeft[reportId] = daysLeft[reportId].filter((one) => one !== day);
  const stillOwed = (daysLeft[reportId] || []).length > 0;
  /* **ASKED FOR NOW, COLLECTED AT THE END OF THIS SAME SYNC -- RUMEE'S WAY (A53,
   * his explanation 2026-09-16).** Rumee requests these first and collects them
   * last, so the platform has the rest of the sync to build them
   * (`D:\rumee-auto-sync\config.js:62-64, 291-296`). So the report goes back to
   * the end of the list for that day -- once, so a collect can never loop. */
  const collectLater = { ...(night.collectLater || {}) };
  const toCollect = state === 'still-waiting' && Boolean(theirId) && Boolean(day)
    && !collectLater[counted];
  if (toCollect) {
    collectLater[counted] = true;
    daysLeft[reportId] = [...(daysLeft[reportId] || []), day];
  }
  /* **ONCE THE REQUEST IS KNOWN TO HAVE GONE, IT CANNOT BE HANDED BACK LATER (review finding, 2026-10-05).**
   * `lastCounted` was never cleared after a successful ask, so a later hourly-recheck failure for the same report
   * and day, written as not-available, would have refunded a request that really went. */
  const settledForGood = night.lastCounted && night.lastCounted.key === counted && !Object.keys(givenBack).length
    ? { lastCounted: null } : {};
  const moved = {
    ...night,
    ...givenBack,
    ...settledForGood,
    /* **WHAT THE PAGE ACTUALLY WAS IS KEPT, AND THE NIGHT OF 6 SEPTEMBER IS WHY.**
     * Nine reports failed on three different Flipkart pages looking for three
     * different things, and all nine were one cause. **The walk had ALREADY
     * captured four hundred characters of what was really on each page** --
     * `walk.js` does it in `gaveUp`, and it says there that the evidence must
     * travel with the failure because written anywhere else it is written where
     * nobody looks. **And this line threw it away, nine times.**
     *
     * The page said "Oops! We can't seem to find the page you're looking for."
     * Had one of those nine sentences reached the morning, the cause would have
     * been obvious at a glance instead of costing a night and a live
     * investigation. */
    done: [...night.done, {
      reportId, state: written.state, say: written.say, size, at, pageWas,
      ...(day ? { dataDate: day } : {}),
    }],
    /* Finished, so nothing is being walked -- until the next one starts. */
    doing: night.doing === reportId ? null : night.doing,
    daysLeft,
    /* **STILL ON THE LIST WHILE IT HAS ANOTHER DAY TO WALK TONIGHT**, and off it
     * the moment it has none. */
    left: toCollect
      ? [...night.left.filter((one) => one !== reportId), reportId]
      : (stillOwed ? night.left : night.left.filter((one) => one !== reportId)),
    collectLater,
  };
  await chrome.storage.local.set({ [THE_NIGHT]: moved });
  return moved;
}

/** Which report the night should do next, or nothing when it is finished. */
export function whatIsNext(night) {
  if (!night || !night.left || !night.left.length) return null;
  return night.left[0];
}

/**
 * End the night, and leave the record behind.
 *
 * **THE ONLY WAY OUT, AND IT ALWAYS WRITES**, the same shape as `endTheRun`. A
 * night that ended because a portal asked for a sign-in has usually done real
 * work first, and calling the whole night a failure throws that away.
 */
export async function endTheNight(chrome, { why = '', at = Date.now() } = {}) {
  const night = await theNight(chrome);
  if (!night) return null;
  const ended = { ...night, finishedAt: at, why };
  await chrome.storage.local.set({ [THE_NIGHT]: ended });
  return ended;
}

/**
 * The night's real states, counted separately -- Job 8 (A65, 2026-09-23).
 *
 * **"REACHED" IS NOT A STATE, IT IS FIVE OF THEM COLLAPSED INTO ONE WORD.**
 * `howTheNightWent` used to count `night.done.length` -- every ATTEMPT, not
 * every real outcome -- against `left`, and called the result "reached". A
 * night where 35 reports never produced a file still said "every report was
 * reached", because a day tried and refused, a day handed to him as needing
 * him, and a day genuinely fetched all counted the same: attempted once.
 *
 * **ONE OUTCOME PER REPORT-DAY, NOT ONE PER ATTEMPT.** A report asked for now
 * and collected later in the same night gets TWO entries in `night.done` --
 * `still-waiting` when asked, then its real outcome when collected -- so
 * counting every entry would count that one report-day twice. Only the LAST
 * entry for a given report and day is kept.
 */
export function theNightsCounts(night) {
  const resolved = [];
  const seen = new Map();
  for (const one of (night && night.done) || []) {
    const key = `${one.reportId}|${one.dataDate || ''}`;
    const at = seen.get(key);
    if (at === undefined) { seen.set(key, resolved.length); resolved.push(one); } else { resolved[at] = one; }
  }
  const landed = resolved.filter((one) => one.state === 'landed');
  /* **"WAITING ON THE PLATFORM" IS THE DAY NOT BUILT YET, PLUS A REPORT STILL
   * BEING COLLECTED -- BOTH ARE THE PLATFORM'S OWN PACE, NOT A FAULT.** */
  const waiting = resolved.filter((one) => one.state === 'still-waiting' || one.state === NOT_AVAILABLE_YET);
  const needsHim = resolved.filter((one) => one.state === NEEDS_YOU_STATE);
  const failed = resolved.filter((one) => one.state === 'failed');
  const nothingToFetch = resolved.filter((one) => one.state === 'nothing-to-fetch');
  /* **A REPORT ALREADY TOUCHED TONIGHT IS NOT "NOT STARTED", EVEN IF IT IS
   * STILL ON `left` FOR ANOTHER DAY.** Only a report with no entry at all this
   * night has genuinely not begun. */
  const notStarted = ((night && night.left) || [])
    .filter((one) => one !== (night && night.doing) && !resolved.some((r) => r.reportId === one));
  const bytes = landed.reduce((all, one) => all + (Number(one.size) || 0), 0);
  const total = landed.length + waiting.length + needsHim.length + failed.length
    + nothingToFetch.length + notStarted.length + ((night && night.doing) ? 1 : 0);
  return {
    landed, waiting, needsHim, failed, nothingToFetch, notStarted, bytes, total,
  };
}

/**
 * What the night did, in words somebody can read over breakfast.
 *
 * **IT SAYS WHAT DID NOT HAPPEN AS WELL AS WHAT DID.** A report skipped because
 * the allowance was spent, and a report that was never reached because the run
 * stopped, are different things and both matter -- and a summary listing only
 * what ran reads as a clean night either way.
 */
export function howTheNightWent(night) {
  if (!night) return 'No sync has been run.';
  const {
    landed, waiting, needsHim, failed, nothingToFetch, notStarted, bytes, total,
  } = theNightsCounts(night);
  const lines = [
    /* **FIVE COUNTS, NOT ONE WORD.** Every different thing that can be true of
     * a report-day is its own number here, so nothing that went wrong can hide
     * behind one that went right. */
    `${landed.length} landed, ${waiting.length} waiting on the platform (the day is not built `
      + `yet), ${notStarted.length} not started, ${needsHim.length} need him, ${failed.length} `
      + `failed${nothingToFetch.length ? `, ${nothingToFetch.length} correctly had nothing to fetch` : ''} `
      + `-- ${total} in all.`,
    `${landed.length} produced a real file, ${bytes} bytes in all.`,
    /* **NAMED, NOT "FLIPKART REQUESTS" IN GENERAL (Job 8, part 3).** Only
     * `fk_orders` and `fk_payments` ever spend from the Reports Centre's
     * twenty; every other Flipkart report -- including every ad report -- asks
     * Flipkart by a different door and spends nothing from this count. A night
     * that ticked only ad reports genuinely spends none of the twenty, and the
     * old wording ("allowed Flipkart requests") read as if it covered
     * everything asked of Flipkart that night, when it never did. */
    `${night.spent} of the ${night.mayAskFor} allowed Flipkart Reports Centre requests `
      + `(${SPENDS_THE_ALLOWANCE.join(', ')}) were spent.`,
  ];
  /* **THREE STATES, NOT TWO, AND THE MIDDLE ONE IS THE ONE THAT MISLED.** A
   * report being walked right now has not failed and has not been skipped, and
   * calling it either is how one report in progress was read as a tenth
   * failure. */
  if (night.doing) lines.push(`Being fetched right now: ${night.doing}.`);
  if (notStarted.length) lines.push(`Not started: ${notStarted.join(', ')}.`);
  for (const one of night.done) {
    lines.push(`  ${one.reportId}: ${one.state}${one.size ? ` (${one.size} bytes)` : ''}`
      + `${one.say ? ` -- ${one.say}` : ''}`);
    /* **AND UNDER IT, WHAT WAS ACTUALLY THERE.** A summary that says only what
     * was looked for cannot tell one cause from nine. */
    if (one.pageWas) lines.push(`      the page said: ${one.pageWas}`);
  }
  return lines.join('\n');
}

/**
 * The night written out as a file for the seller's Drive (A53, 2026-09-15).
 *
 * **SO A FAILURE CAN BE READ WITHOUT ANYBODY AT THE BROWSER.** A failed report
 * leaves nothing in Drive, and the panel's words lived only in the browser. One
 * file per night, in a `run_log` folder, like the reference's `rumee_sync_log.csv`.
 */
export function theRunLog(night) {
  if (!night || !night.startedAt) return null;
  const started = new Date(night.startedAt).toISOString();
  const lines = [
    'Kartaan AutoSync run log',
    `Started: ${started}`,
    `Finished: ${night.finishedAt ? new Date(night.finishedAt).toISOString() : 'not yet'}`,
    `Why it ended: ${night.why || ''}`,
    '',
    howTheNightWent(night),
  ];
  return {
    reportId: 'run_log',
    fileName: `run_log_${started.replace(/[:.]/g, '-')}.txt`,
    text: `${lines.join('\n')}\n`,
  };
}

/**
 * Move the night on: record whatever the last walk did, and start the next one.
 *
 * **IT IS CALLED BY EVERYTHING THAT COULD MEAN A WALK IS OVER, and it decides
 * for itself whether anything has changed.** A walk saying it is done calls it, a
 * tab being closed calls it, and the alarm that wakes this worker every two
 * minutes calls it -- so a night cannot stall because the one message that was
 * supposed to move it on never arrived. Anything that is not a change is a
 * no-op, so being called too often costs nothing.
 *
 * **NOTHING IS REMEMBERED BETWEEN CALLS.** The night and the walk are both read
 * back out of storage every time, because Chrome shuts this worker down after
 * thirty seconds of quiet and a night takes hours.
 *
 * `theWalk` is what a walk in flight looks like, and `startAWalk` starts one --
 * both handed in so the whole of this can be checked with no browser.
 *
 * **ONE AT A TIME, QUEUED (A53, 2026-09-15).** Walk-done, the two-minute alarm
 * and Run now can all call this at the same moment. Two calls overlapping both
 * read the same finished walk, and each booked it and started a walk -- which
 * is how `fk_ads_fsn` was listed twice in one night on 2026-09-14. Each call now
 * waits for the one before it to finish, so the second reads what the first
 * wrote.
 */
let carryingOn = Promise.resolve();
export function carryTheNightOn(chrome, parts) {
  return inTheNightsOwnLine(() => carryItOn(chrome, parts));
}

/**
 * Run something that reads and writes the night in the night's own line, after everything already in it.
 *
 * **STOP AND STARTING A SYNC USE THIS TOO (review finding, 2026-10-05).** `carryTheNightOn` read the night, made
 * several storage calls, and wrote it back from what it had read -- so a Stop landing inside that window had
 * its `finishedAt` written over and the night was revived, and two starters could both see "no night going"
 * and each write a night over the other's. All three now take their turn in one line.
 *
 * **NEVER CALL `carryTheNightOn` FROM INSIDE A JOB HANDED TO THIS**: it would wait for the line it is standing in.
 */
export function inTheNightsOwnLine(job) {
  const mine = carryingOn.then(job);
  carryingOn = mine.catch(() => {});
  return mine;
}

async function carryItOn(chrome, {
  theWalkNow, startAWalk, endTheWalkNow, at = Date.now(),
}) {
  const night = await theNight(chrome);
  if (!night || night.finishedAt) return null;

  const walk = await theWalkNow();
  /* **A FINISHED WALK FROM AN EARLIER NIGHT IS NOT THIS NIGHT'S ANSWER (A53,
   * 2026-09-15).** A walk written off by its own night can still end later; the
   * next night read that answer and booked it as its own, ending in 18 seconds
   * without walking anything. Cleared, not booked. */
  if (walk && walk.answer && Number(walk.startedAt) < Number(night.startedAt)) {
    await endTheWalkNow();
    return startTheNextOne(chrome, { startAWalk, at });
  }
  /* **A WALK STILL GOING IS LEFT ALONE.** One at a time: two walks share one tab
   * and one armed download-cancel, and the file that came down could belong to
   * either. */
  if (walk && !walk.answer) return { doing: walk.reportId };

  if (walk && walk.answer) {
    /* **WRITTEN DOWN BEFORE THE NEXT ONE STARTS**, or an interruption between
     * the two loses the one that just finished. */
    await thatOneIsDone(chrome, {
      reportId: walk.answer.reportId || walk.reportId,
      state: walk.answer.state,
      say: walk.answer.say || '',
      size: Number(walk.answer.size) || 0,
      /* **CARRIED, NOT DROPPED.** See `thatOneIsDone`. */
      pageWas: walk.answer.pageWas || '',
      /* **AND WHAT THE PLATFORM IS BUILDING, WHICH IS THE ONE THING THAT HAS TO
       * OUTLIVE THIS NIGHT.** The walk has handed this back since it was
       * written; this line is what finally catches it. Dropped here, every run
       * asks again -- see `WHAT_IS_BEING_BUILT`. */
      theirId: walk.answer.theirId || null,
      dataDate: walk.answer.dataDate || walk.dataDate || '',
      listMissing: Boolean(walk.answer.listMissing),
      needsSigningIn: Boolean(walk.answer.needsSigningIn),
      settled: walk.answer.state === 'nothing-to-fetch',
      at,
    });
    /* **AND THE WALK IS CLEARED, or the next call reads this same finished walk
     * again and records it twice.** */
    await endTheWalkNow();
    /* **A PORTAL ASKING TO BE SIGNED IN TO ENDS THE NIGHT, IT DOES NOT SKIP ONE
     * REPORT.** Every report after it hits the same wall, and attempting them
     * all writes thirteen identical failures over the one thing that needs
     * doing -- which is exactly how the reference's queue died. */
    if (walk.answer.needsSigningIn) {
      /* **PAUSED, NOT THROWN AWAY -- RUMEE'S WAY, IMPROVED (A53, his ruling
       * 2026-09-16).** Rumee keeps the rest of the queue as `pausedQueue` and its
       * Resume Sync carries on from it (`D:\rumee-auto-sync\background.js:712-726,
       * 1015-1034`). Rumee drops the report that met the sign-in; it never ran, so
       * here it is kept first. */
      const stopped = walk.answer.reportId || walk.reportId;
      const after = await theNight(chrome);
      await chrome.storage.local.set({
        [PAUSED]: {
          reportIds: [stopped, ...((after && after.left) || []).filter((one) => one !== stopped)],
          dataDate: (after && after.dataDate) || '',
          at,
        },
      });
      return endTheNight(chrome, {
        at,
        why: 'The portal asked to be signed in to, so the rest of the sync was not attempted. '
          + 'Sign in, then press Resume to carry on from this report.',
      });
    }
  }

  return startTheNextOne(chrome, { startAWalk, at });
}

/** Start the next report the night owes, skipping any it may not ask for. */
async function startTheNextOne(chrome, { startAWalk, at }) {
  for (;;) {
    // eslint-disable-next-line no-await-in-loop
    const night = await theNight(chrome);
    const next = whatIsNext(night);
    if (!next) {
      /* **"EVERY REPORT WAS REACHED" IS NEVER WRITTEN WHEN SOMETHING NEEDS HIM
       * OR FAILED (Job 8, part 2, his words).** This sentence is what the run
       * log's "Why it ended" line says, and it is the seller's one line about
       * the whole night -- so it is true only when nothing behind it needed
       * him or failed. */
      // eslint-disable-next-line no-await-in-loop
      const { needsHim, failed } = theNightsCounts(night);
      const wrong = [...needsHim, ...failed];
      const why = wrong.length
        ? `${wrong.length} report${wrong.length === 1 ? '' : 's'} did not land: `
          + `${wrong.map((one) => `${one.reportId}${one.dataDate ? ` (${one.dataDate})` : ''} `
            + `${one.state === NEEDS_YOU_STATE ? 'needs you' : 'failed'}`).join(', ')}.`
        : 'Every report was reached.';
      // eslint-disable-next-line no-await-in-loop
      return endTheNight(chrome, { at, why });
    }
    /* **ASKED FIRST: IS THE PLATFORM ALREADY BUILDING THIS?** Given, the walk
     * collects rather than asking again -- it already accepts this and already
     * switches phase on it. See `WHAT_IS_BEING_BUILT` for what it cost to have
     * nothing here. */
    // eslint-disable-next-line no-await-in-loop
    /* **WHICH DAY, AND IT IS NOT ALWAYS THE NIGHT'S.** A day this report was
     * refused on earlier because the platform had not built it is tried first,
     * oldest first, and the night's own day after it -- the reference's order
     * (`gap-catchup.js`). Worked out once per report per night and written down;
     * every attempt or skip takes one day off, so it cannot loop. */
    let daysLeft = night.daysLeft || {};
    if (!daysLeft[next]) {
      // eslint-disable-next-line no-await-in-loop
      const owed = await theDaysStillOwed(chrome, next, night.dataDate);
      /* **JOB 6: AND EVERY DAY NOBODY EVER TRIED, FOR A REPORT THAT CAN GO
       * BACK** -- see `daysNobodyTried`. `theDaysStillOwed` alone only ever
       * finds a day something already tried and the platform refused; a day no
       * sync ever started for (F14, Meesho orders 09-17..09-19 while the timed
       * list held two Flipkart ad reports and nothing else, F5) is nowhere in
       * it at all. */
      if ((night.canGoBack || []).includes(next)) {
        // eslint-disable-next-line no-await-in-loop
        owed.push(...await daysNobodyTried(chrome, next, night.dataDate));
      }
      /* **A57, JOB 2: AND EVERY DAY A REPORT READING ITS LIST STILL OWES**, or the
       * list is never fetched for those days and they wait for ever. */
      const readers = Object.keys(night.listFrom || {})
        .filter((one) => night.listFrom[one] === next && night.left.includes(one));
      for (const reader of readers) {
        // eslint-disable-next-line no-await-in-loop
        owed.push(...await theDaysStillOwed(chrome, reader, night.dataDate));
        if ((night.canGoBack || []).includes(reader)) {
          // eslint-disable-next-line no-await-in-loop
          owed.push(...await daysNobodyTried(chrome, reader, night.dataDate));
        }
      }
      const asked = (night.days && night.days.length) ? night.days : [night.dataDate];
      /* **A REPORT THAT SPENDS THE FLIPKART ALLOWANCE ASKS FOR ITS OWN DAYS FIRST, THEN THE GAPS (review
       * finding, 2026-10-05).** Oldest first meant the gap days used the request cap and yesterday -- the day
       * the sync is for -- was refused first, so with a backlog it was never fetched until the gap was gone. */
      daysLeft = {
        ...daysLeft,
        [next]: spendsTheAllowance(next)
          ? [...new Set([...[...asked].sort(), ...[...owed].sort()])]
          : [...new Set([...owed, ...asked])].sort(),
      };
      // eslint-disable-next-line no-await-in-loop
      await chrome.storage.local.set({ [THE_NIGHT]: { ...night, daysLeft } });
    }
    const day = daysLeft[next].length ? daysLeft[next][0] : night.dataDate;
    // eslint-disable-next-line no-await-in-loop
    const askedAlready = await whatThatWasAskedUnder(chrome, next, day);
    /* **A REPORT THE PLATFORM ONLY GIVES FOR ITS NEWEST DAY IS LEFT OUT OF AN
     * OLDER ONE (his ruling, 2026-09-16), before anything is opened.** */
    const onlyNewest = whyOnlyItsNewestDay(night, next, day);
    if (onlyNewest) {
      // eslint-disable-next-line no-await-in-loop
      await thatOneIsDone(chrome, {
        reportId: next, state: 'nothing-to-fetch', say: onlyNewest, at, dataDate: day,
      });
      // eslint-disable-next-line no-await-in-loop
      continue;
    }
    const cannot = whyItCannotBeAskedFor(night, next, Boolean(askedAlready));
    if (cannot) {
      /* **SKIPPED BY NAME AND WRITTEN DOWN, NOT SILENTLY DROPPED.** A report
       * missing from a seller's Drive with nothing anywhere saying why is the
       * fault this whole product is built against. */
      // eslint-disable-next-line no-await-in-loop
      await thatOneIsDone(chrome, {
        reportId: next, state: 'nothing-to-fetch', say: cannot, at, dataDate: day,
      });
      // eslint-disable-next-line no-await-in-loop
      continue;
    }
    /* **TAKEN OFF THE LIST BEFORE IT IS ATTEMPTED, NOT AFTER IT FINISHES.** See
     * `thatOneIsBeingTried`: left on the list, a report whose walk cannot even be
     * started is attempted again by the next alarm, for ever, having already
     * spent one of the seller's twenty each time. */
    // eslint-disable-next-line no-await-in-loop
    await thatOneIsBeingTried(chrome, next, day);
    /* **COUNTED BEFORE IT IS ASKED FOR.** A request that has gone cannot be
     * taken back, so a worker shut down between the two must leave a count that
     * is too high rather than too low: that costs a report, and the other way
     * costs a seller's allowance. */
    /* **AND NOTHING IS COUNTED FOR A COLLECTION.** The twenty are requests. A
     * run coming back for a report Flipkart has already built asks for nothing,
     * so counting one here would spend the seller's allowance on a page view --
     * and after four collections of one report their day would be a fifth
     * shorter for no requests at all. */
    if (spendsTheAllowance(next) && !askedAlready) {
      // eslint-disable-next-line no-await-in-loop
      await oneWasAskedFor(chrome, { counting: thatOneAndThatDay(next, day) });
    }
    try {
      // eslint-disable-next-line no-await-in-loop
      await startAWalk({
        reportId: next,
        dataDate: day,
        openAt: night.openAt,
        /* **THE SELLER'S OWN, CARRIED BY THE NIGHT.** See `startTheNight`: every
         * Meesho recipe's address holds `{panel}` and the walk refuses without
         * it. Left off this line, a Meesho night reaches the walk with nothing
         * and every report in it fails saying so. */
        panel: night.panel,
        /* **WHAT IT WAS ASKED UNDER, WHICH IS WHAT TURNS AN ASK INTO A
         * COLLECT.** Nothing else about the walk changes: it has accepted this
         * since it was written (`walk.js`) and picks its phase from it. */
        askedAlready,
        fromDay: await theDayAfterTheLastCaptured(chrome, next, day),
      });
    } catch (wrong) {
      /* **A WALK THAT COULD NOT BE STARTED IS WRITTEN DOWN AND THE NIGHT MOVES
       * ON.** Thrown onwards instead, it reaches the alarm listener as an
       * unhandled rejection and the next tick tries the same report again. */
      // eslint-disable-next-line no-await-in-loop
      await thatOneIsDone(chrome, {
        reportId: next,
        state: 'failed',
        say: `This report could not be started at all: ${wrong.message}`,
        at,
        dataDate: day,
      });
      // eslint-disable-next-line no-continue
      continue;
    }
    return { started: next };
  }
}
