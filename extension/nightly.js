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
 * three reports spend from it -- `fk_orders`, `fk_returns`, `fk_payments`, the
 * three built by `_reports_centre` in `autosync/recipes.py`. Asking for one of
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
export const SPENDS_THE_ALLOWANCE = Object.freeze(['fk_orders', 'fk_returns', 'fk_payments']);

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
  doing, mayAskFor = 0, at = Date.now(), openAt = '', dataDate = '', panel = '',
}) {
  if (!openAt) {
    /* **REFUSED HERE, BECAUSE THE ALTERNATIVE IS A NIGHT THAT SPENDS AND NEVER
     * FETCHES (A26R4).** With nowhere to start from, every walk this night tries
     * to start throws -- and the allowance is spent BEFORE the walk, so each
     * throw costs one of the seller's twenty and produces nothing. It is the
     * easiest way to reach the retry loop below and it was reachable by simply
     * leaving one argument off. */
    throw new Error('A night has to be told which portal page its reports start from.');
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

/**
 * May this report be asked for, and what to say if not.
 *
 * **ASKED BEFORE THE REQUEST, NEVER AFTER.** A request that has gone cannot be
 * taken back, so a count checked afterwards is a count that has already been
 * exceeded.
 */
export function whyItCannotBeAskedFor(night, reportId) {
  if (!spendsTheAllowance(reportId)) return null;
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
export async function oneWasAskedFor(chrome, { at = Date.now() } = {}) {
  const night = await theNight(chrome);
  if (!night) return null;
  /* **STAMPED WITH THE DAY IT IS BEING SPENT ON, at the one moment that day is
   * known for certain.** Worked out afterwards from when the night started, or
   * from when a report finished, it is a guess about a request that has already
   * gone. */
  const day = theDay(at);
  const spentOn = { ...(night.spentOn || {}) };
  spentOn[day] = (Number(spentOn[day]) || 0) + 1;
  const spent = { ...night, spent: night.spent + 1, spentOn };
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
export async function thatOneIsBeingTried(chrome, reportId) {
  const night = await theNight(chrome);
  if (!night) throw new Error('Nothing can be attempted against a night that is not going.');
  /* **AND WHICH ONE IT IS, BECAUSE OTHERWISE IT IS IN NEITHER LIST.** Taking a
   * report off `left` the moment it is attempted is what makes a retry loop
   * impossible -- but it also means a report being walked right now is neither
   * owed nor done, and a summary built from those two lists would not mention it
   * at all. On the night of 6 September the opposite fault showed: `fk_views`
   * was walking, was still in `left`, and the summary called it "never
   * reached". It had reached; it was in the middle of the job. */
  const moved = { ...night, doing: reportId, left: night.left.filter((one) => one !== reportId) };
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
  reportId, state, say = '', size = 0, at, pageWas = '',
}) {
  const night = await theNight(chrome);
  if (!night) throw new Error('Nothing can be recorded against a night that is not going.');
  const moved = {
    ...night,
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
    done: [...night.done, { reportId, state, say, size, at, pageWas }],
    /* Finished, so nothing is being walked -- until the next one starts. */
    doing: night.doing === reportId ? null : night.doing,
    left: night.left.filter((one) => one !== reportId),
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
 * What the night did, in words somebody can read over breakfast.
 *
 * **IT SAYS WHAT DID NOT HAPPEN AS WELL AS WHAT DID.** A report skipped because
 * the allowance was spent, and a report that was never reached because the run
 * stopped, are different things and both matter -- and a summary listing only
 * what ran reads as a clean night either way.
 */
export function howTheNightWent(night) {
  if (!night) return 'No night has been run.';
  const landed = night.done.filter((one) => one.state === 'landed');
  const bytes = landed.reduce((all, one) => all + (Number(one.size) || 0), 0);
  const lines = [
    /* **THE ONE BEING WALKED IS PART OF THE TOTAL (A26R5).** It is in neither
     * list -- that is what makes a retry loop impossible -- so a count built
     * from the two lists dropped it, and the first line of the summary said
     * "0 of 2" on a three-report night. The line below names it; this one has
     * to count it. */
    `${night.done.length} of ${night.done.length + night.left.length
      + (night.doing ? 1 : 0)} reports were reached.`,
    `${landed.length} produced a real file, ${bytes} bytes in all.`,
    `${night.spent} of the ${night.mayAskFor} allowed Flipkart requests were spent.`,
  ];
  /* **THREE STATES, NOT TWO, AND THE MIDDLE ONE IS THE ONE THAT MISLED.** A
   * report being walked right now has not failed and has not been skipped, and
   * calling it either is how one report in progress was read as a tenth
   * failure. */
  if (night.doing) lines.push(`Being fetched right now: ${night.doing}.`);
  if (night.left.length) lines.push(`Not started: ${night.left.join(', ')}.`);
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
 */
export async function carryTheNightOn(chrome, {
  theWalkNow, startAWalk, endTheWalkNow, at = Date.now(),
}) {
  const night = await theNight(chrome);
  if (!night || night.finishedAt) return null;

  const walk = await theWalkNow();
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
      return endTheNight(chrome, {
        at,
        why: 'The portal asked to be signed in to, so the rest of the night was not attempted.',
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
      // eslint-disable-next-line no-await-in-loop
      return endTheNight(chrome, { at, why: 'Every report was reached.' });
    }
    const cannot = whyItCannotBeAskedFor(night, next);
    if (cannot) {
      /* **SKIPPED BY NAME AND WRITTEN DOWN, NOT SILENTLY DROPPED.** A report
       * missing from a seller's Drive with nothing anywhere saying why is the
       * fault this whole product is built against. */
      // eslint-disable-next-line no-await-in-loop
      await thatOneIsDone(chrome, { reportId: next, state: 'nothing-to-fetch', say: cannot, at });
      // eslint-disable-next-line no-await-in-loop
      continue;
    }
    /* **TAKEN OFF THE LIST BEFORE IT IS ATTEMPTED, NOT AFTER IT FINISHES.** See
     * `thatOneIsBeingTried`: left on the list, a report whose walk cannot even be
     * started is attempted again by the next alarm, for ever, having already
     * spent one of the seller's twenty each time. */
    // eslint-disable-next-line no-await-in-loop
    await thatOneIsBeingTried(chrome, next);
    /* **COUNTED BEFORE IT IS ASKED FOR.** A request that has gone cannot be
     * taken back, so a worker shut down between the two must leave a count that
     * is too high rather than too low: that costs a report, and the other way
     * costs a seller's allowance. */
    if (spendsTheAllowance(next)) {
      // eslint-disable-next-line no-await-in-loop
      await oneWasAskedFor(chrome);
    }
    try {
      // eslint-disable-next-line no-await-in-loop
      await startAWalk({
        reportId: next,
        dataDate: night.dataDate,
        openAt: night.openAt,
        /* **THE SELLER'S OWN, CARRIED BY THE NIGHT.** See `startTheNight`: every
         * Meesho recipe's address holds `{panel}` and the walk refuses without
         * it. Left off this line, a Meesho night reaches the walk with nothing
         * and every report in it fails saying so. */
        panel: night.panel,
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
      });
      // eslint-disable-next-line no-continue
      continue;
    }
    return { started: next };
  }
}
