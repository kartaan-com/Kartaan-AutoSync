/* Checks for working through a night's reports with nobody watching.
 *
 * Run: node extension/nightly.test.js
 *
 * **THE ONE THAT MATTERS MOST IS THE ALLOWANCE.** Flipkart's Reports Centre lets
 * a seller ask for twenty reports a day. Asking is a WRITE against their own
 * account and cannot be taken back. Three reports spend from it; a run that
 * miscounts spends a real seller's real allowance on a real night, and no amount
 * of care afterwards puts it back.
 *
 * **AND THE SECOND IS THAT IT DOES NOT RETRY.** The reference's worst day was an
 * unattended retry loop against a portal that was refusing it -- twenty requests
 * gone by morning, on the same broken thing.
 */

import { readFileSync } from 'node:fs';
import { installFakeChrome } from '../test/fake-chrome.js';
import {
  SPENDS_THE_ALLOWANCE,
  THE_NIGHT,
  endTheNight,
  howTheNightWent,
  oneWasAskedFor,
  spendsTheAllowance,
  startTheNight,
  thatOneIsDone,
  theNight,
  whatIsNext,
  whyItCannotBeAskedFor,
  carryTheNightOn,
  thatOneIsBeingTried,
} from './nightly.js';

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

async function said(fn) {
  try {
    await fn();
  } catch (wrong) {
    return (wrong && wrong.message) || String(wrong);
  }
  return '';
}

/* ------------------------------------ which reports spend the seller's twenty */

/* **THIS IS THE CHECK THAT MATTERS MOST IN THE FILE, AND IT DELIBERATELY DOES
 * NOT COMPARE THE LIST TO ITSELF.** A list of three names checked against three
 * names proves only that somebody can copy. What it is checked against is the
 * RECIPE FILE: a report whose asking phase goes to Flipkart's Reports Centre
 * spends one of the seller's twenty, whatever it happens to be called.
 *
 * **SO IF A FOURTH REPORT IS EVER ADDED THAT GOES THROUGH THERE, THIS GOES RED**
 * -- rather than that report quietly spending an allowance nothing is counting. */
{
  const book = JSON.parse(readFileSync(new URL('./recipes.json', import.meta.url), 'utf8'));
  const throughTheReportsCentre = Object.entries(book.recipes)
    /* **BOTH PHASES, NOT JUST THE ASKING ONE (A26R4).** This read `toAsk` alone.
     * Thirteen of seventeen recipes have an EMPTY `toAsk`, so a one-phase
     * Reports Centre report -- the shape the next one is most likely to take --
     * would have spent the seller's allowance uncounted while this check stayed
     * green. It was driven: a fourth recipe added with report-centre only in its
     * take list passed 47 of 47. */
    .filter(([, r]) => [...(r.toAsk || []), ...(r.toTake || [])].some(
      (step) => String(step.address || '').includes('report-centre')
    ))
    .map(([id]) => id)
    .sort();
  check(`the reports that spend the allowance are exactly the ones that go through the `
    + `Reports Centre -- ${throughTheReportsCentre}`,
  throughTheReportsCentre.join() === [...SPENDS_THE_ALLOWANCE].sort().join());
  /* **AND THEY ARE REAL REPORTS.** A name misspelt here spends without counting,
   * which is the same fault wearing a typo. */
  check('and every one of them is a report that really exists',
    SPENDS_THE_ALLOWANCE.every((one) => book.recipes[one]));
}

check('asking for a Reports Centre report spends one of the twenty',
  spendsTheAllowance('fk_orders') && spendsTheAllowance('fk_returns')
  && spendsTheAllowance('fk_payments'));
/* **THE OTHER TEN FLIPKART REPORTS COST NOTHING**, and treating them as though
 * they did would leave a seller's data unfetched for no reason at all. */
check('while the ad reports cost nothing', !spendsTheAllowance('fk_ads_daily'));
check('and nor do claims, listings or the traffic report',
  !spendsTheAllowance('fk_claims') && !spendsTheAllowance('fk_listings')
  && !spendsTheAllowance('fk_views'));
check('and nor does anything on Meesho', !spendsTheAllowance('me_orders'));

/* ---------------------------------------------------------- counting them out */

{
  const browser = installFakeChrome();
  await startTheNight(browser.chrome, { doing: ['fk_ads_daily', 'fk_orders'], mayAskFor: 0, at: 1, openAt: 'https://x/' });
  const night = await theNight(browser.chrome);
  check('a night is written down before a single report is touched',
    browser.stored()[THE_NIGHT].left.join() === 'fk_ads_daily,fk_orders');
  /* **SPENT, NOT REMAINING.** A number that counts down reads as "how many are
   * left" from every angle and is right from none: two runs both reading six
   * both believe they may spend six. */
  check('and what it has spent starts at nothing and only ever grows',
    night.spent === 0);

  /* **NOUGHT IS A REAL ANSWER AND THE SAFE ONE.** A night that is only learning
   * asks for none of them, and each is skipped BY NAME rather than attempted
   * and refused by Flipkart. */
  check('with an allowance of nothing, a Reports Centre report is refused before it is asked for',
    (whyItCannotBeAskedFor(night, 'fk_orders') || '').includes('has not been asked for'));
  check('and the refusal says how many it was allowed and how many it has used',
    (whyItCannotBeAskedFor(night, 'fk_orders') || '').includes('allowed 0 and has used 0'));
  /* **AND IT DOES NOT STOP THE FREE ONES.** Ten Flipkart reports and every
   * Meesho one cost nothing, and a night that refused those too would leave a
   * seller's data unfetched for no reason. */
  check('while a report that costs nothing is not refused',
    whyItCannotBeAskedFor(night, 'fk_ads_daily') === null);
}

{
  const browser = installFakeChrome();
  await startTheNight(browser.chrome, { doing: ['fk_orders', 'fk_returns'], mayAskFor: 1, at: 1, openAt: 'https://x/' });
  check('with one allowed, the first is let through',
    whyItCannotBeAskedFor(await theNight(browser.chrome), 'fk_orders') === null);

  /* **COUNTED BEFORE THE REQUEST GOES.** A worker shut down between the request
   * and the counting leaves a request that happened and a count that says it did
   * not -- and the next run spends it again. */
  await oneWasAskedFor(browser.chrome);
  check('and once it is spent, the next one is refused',
    (whyItCannotBeAskedFor(await theNight(browser.chrome), 'fk_returns') || '')
      .includes('allowed 1 and has used 1'));

  /* **AND THE COUNT SURVIVES THE WORKER BEING SHUT DOWN**, which is the whole
   * reason it is in storage: Chrome kills an idle worker after thirty seconds
   * and a night takes hours. */
  browser.shutTheWorkerDown();
  check('and the count survives Chrome shutting the worker down mid-night',
    (await theNight(browser.chrome)).spent === 1);
}

{
  /* **NOTHING TO COUNT AGAINST IS A REFUSAL, NOT A FREE PASS.** */
  check('asking with no night at all is refused rather than allowed',
    (whyItCannotBeAskedFor(null, 'fk_orders') || '').includes('no run to count this against'));
}

/* ------------------------------------------------------- one at a time, no retry */

{
  const browser = installFakeChrome();
  await startTheNight(browser.chrome, { doing: ['a', 'b', 'c'], mayAskFor: 0, at: 1, openAt: 'https://x/' });
  check('the night knows which report is next', whatIsNext(await theNight(browser.chrome)) === 'a');

  await thatOneIsDone(browser.chrome, { reportId: 'a', state: 'landed', size: 44600, at: 2 });
  check('and once one is done it is off the list', whatIsNext(await theNight(browser.chrome)) === 'b');

  /* **A FAILED REPORT IS WRITTEN DOWN AND THE NIGHT MOVES ON. IT IS NOT TRIED
   * AGAIN.** The reference's worst day was an unattended retry loop against a
   * portal that was refusing it. */
  await thatOneIsDone(browser.chrome, {
    reportId: 'b', state: 'failed', say: 'the button was not there', at: 3,
  });
  check('a report that failed is not put back on the list to try again',
    whatIsNext(await theNight(browser.chrome)) === 'c');
  check('and what went wrong is kept rather than thrown away',
    (await theNight(browser.chrome)).done[1].say === 'the button was not there');

  await thatOneIsDone(browser.chrome, { reportId: 'c', state: 'failed', at: 4 });
  check('and when the list is empty there is nothing next',
    whatIsNext(await theNight(browser.chrome)) === null);
}

{
  const browser = installFakeChrome();
  check('nothing can be recorded against a night that is not going',
    (await said(() => thatOneIsDone(browser.chrome, { reportId: 'a', state: 'landed', at: 1 })))
      .includes('a night that is not going'));
}

/* ---------------------------------------------------- what he reads at breakfast */

{
  const browser = installFakeChrome();
  await startTheNight(browser.chrome, {
    doing: ['fk_ads_daily', 'fk_claims', 'fk_views'], mayAskFor: 0, at: 1, openAt: 'https://x/' });
  await thatOneIsDone(browser.chrome, {
    reportId: 'fk_ads_daily', state: 'landed', size: 1200, at: 2,
  });
  await thatOneIsDone(browser.chrome, {
    reportId: 'fk_claims', state: 'failed', say: 'nothing matched Download', at: 3,
  });
  const ended = await endTheNight(browser.chrome, { why: 'the seller was signed out', at: 4 });
  const words = howTheNightWent(ended);

  check('the summary says how many were reached', words.includes('2 of 3 reports were reached'));
  check('and how many produced a real file, with the bytes',
    words.includes('1 produced a real file, 1200 bytes'));
  check('and how much of the seller allowance went', words.includes('0 of the 0 allowed'));
  /* **IT SAYS WHAT DID NOT HAPPEN AS WELL AS WHAT DID.** A summary listing only
   * what ran reads as a clean night whether or not it was one. */
  check('and names what was never reached at all', words.includes('Never reached: fk_views'));
  check('and names each report with what became of it',
    words.includes('fk_ads_daily: landed (1200 bytes)')
    && words.includes('fk_claims: failed -- nothing matched Download'));
  check('and the night keeps why it ended', ended.why === 'the seller was signed out');
}

check('a summary of no night at all says so rather than falling over',
  howTheNightWent(null) === 'No night has been run.');


/* ------------------------------------------- moving the night on, one at a time */

/** A stand-in for the walk in flight, driven by hand. */
function aWalkThat() {
  const it = { held: null, started: [], cleared: 0 };
  it.theWalkNow = async () => it.held;
  it.endTheWalkNow = async () => { it.held = null; it.cleared += 1; };
  it.startAWalk = async ({ reportId, dataDate, openAt }) => {
    it.started.push({ reportId, dataDate, openAt });
    it.held = { reportId, answer: null };
  };
  it.itFinished = (answer) => { it.held = { ...it.held, answer }; };
  return it;
}

{
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_ads_daily', 'fk_claims'], mayAskFor: 0, at: 1,
    openAt: 'https://seller.flipkart.com/index.html', dataDate: '2026-09-04',
  });

  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  check('the night starts the first report', walk.started[0].reportId === 'fk_ads_daily');
  check('and tells it which day and which page to start from',
    walk.started[0].dataDate === '2026-09-04'
    && walk.started[0].openAt === 'https://seller.flipkart.com/index.html');

  /* **ONE AT A TIME.** Two walks share one tab and one armed download-cancel,
   * and the file that came down could belong to either. */
  await carryTheNightOn(browser.chrome, { ...walk, at: 3 });
  check('and while that one is still walking, nothing else is started',
    walk.started.length === 1);

  walk.itFinished({ state: 'landed', reportId: 'fk_ads_daily', size: 900 });
  await carryTheNightOn(browser.chrome, { ...walk, at: 4 });
  check('when it finishes, what it did is written down',
    (await theNight(browser.chrome)).done[0].size === 900);
  check('and the next report is started', walk.started[1].reportId === 'fk_claims');
  /* **CLEARED, or the next call reads that same finished walk and records it a
   * second time.** */
  check('and the finished walk is cleared rather than counted twice', walk.cleared === 1);

  walk.itFinished({ state: 'failed', reportId: 'fk_claims', say: 'nothing matched' });
  const ended = await carryTheNightOn(browser.chrome, { ...walk, at: 5 });
  check('a failed report is recorded and NOT tried again',
    (await theNight(browser.chrome)).done[1].state === 'failed' && walk.started.length === 2);
  check('and with nothing left the night ends itself', ended && ended.finishedAt === 5);
  check('and it says why it ended', ended.why.includes('Every report was reached'));

  /* **BEING CALLED AGAIN AFTER IT IS OVER DOES NOTHING.** The alarm that wakes
   * this worker keeps calling this all night. */
  await carryTheNightOn(browser.chrome, { ...walk, at: 6 });
  check('and calling it again after the night is over starts nothing',
    walk.started.length === 2);
}

{
  /* **A REPORT THE ALLOWANCE WILL NOT COVER IS SKIPPED BY NAME AND WRITTEN
   * DOWN.** Silently dropped, it is a report missing from a seller's Drive with
   * nothing anywhere saying why -- the fault this whole product is built
   * against. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_orders', 'fk_ads_daily'], mayAskFor: 0, at: 1, openAt: 'https://x/',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  const night = await theNight(browser.chrome);
  check('a Reports Centre report with no allowance is never asked for',
    walk.started.length === 1 && walk.started[0].reportId === 'fk_ads_daily');
  check('and it is written down as skipped, saying why',
    night.done[0].reportId === 'fk_orders'
    && night.done[0].state === 'nothing-to-fetch'
    && night.done[0].say.includes('has not been asked for'));
  check('and nothing was spent', night.spent === 0);
}

{
  /* **AND WHEN IT IS ALLOWED, IT IS COUNTED BEFORE IT IS ASKED FOR.** A request
   * that has gone cannot be taken back, so a worker shut down between the two
   * must leave a count too high rather than too low. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_orders'], mayAskFor: 2, at: 1, openAt: 'https://x/',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  check('an allowed Reports Centre report is asked for', walk.started[0].reportId === 'fk_orders');
  check('and the allowance was spent before the asking, not after',
    (await theNight(browser.chrome)).spent === 1);
}

{
  /* **A PORTAL ASKING TO BE SIGNED IN TO ENDS THE NIGHT, IT DOES NOT SKIP ONE
   * REPORT.** Every report after it hits the same wall, and attempting them all
   * writes thirteen identical failures over the one thing that needs doing --
   * which is exactly how the reference's queue died. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_ads_daily', 'fk_claims', 'fk_views'], mayAskFor: 0, at: 1, openAt: 'https://x/',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  walk.itFinished({
    state: 'failed', reportId: 'fk_ads_daily', needsSigningIn: true, say: 'sign in',
  });
  const ended = await carryTheNightOn(browser.chrome, { ...walk, at: 3 });
  check('being signed out ends the night rather than failing every report in turn',
    ended && ended.finishedAt === 3 && walk.started.length === 1);
  check('and it says that is why, so nobody looks for thirteen broken buttons',
    ended.why.includes('asked to be signed in to'));
  check('and the two never reached are still named as owed',
    ended.left.join() === 'fk_claims,fk_views');
}

{
  /* **AND THE COUNT SURVIVES THE WORKER BEING SHUT DOWN MID-NIGHT**, which is
   * the whole reason none of this is held in a variable. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_ads_daily', 'fk_claims'], mayAskFor: 0, at: 1, openAt: 'https://x/',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  walk.itFinished({ state: 'landed', reportId: 'fk_ads_daily', size: 10 });
  browser.shutTheWorkerDown();
  await carryTheNightOn(browser.chrome, { ...walk, at: 3 });
  check('a night carries on after Chrome shuts the worker down',
    walk.started[1].reportId === 'fk_claims'
    && (await theNight(browser.chrome)).done[0].size === 10);
}

{
  /* **THE WORST FAULT THIS FILE HAS HAD, AND IT WAS FOUND BY A REVIEWER DRIVING
   * IT RATHER THAN READING IT (A26R4).**
   *
   * A report used to leave `left` only when it FINISHED. So a report whose walk
   * could not even be STARTED stayed owed -- while the allowance for it had
   * already been spent -- and the two-minute alarm walked straight back into it.
   * Measured on a copy: **twenty real Flipkart requests for ONE report in eighty
   * minutes**, and the night's own summary blaming the allowance.
   *
   * That is the exact catastrophe the top of `nightly.js` says it exists to
   * prevent, reached through the one door nobody had watched. The header was
   * true about retrying a FAILED report and silent about never STARTING one. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  let tries = 0;
  /* **THE WALK STARTS AND THEN VANISHES, WHICH IS THE REAL CASE (A26R4's own
   * PROBE6).** The request genuinely goes to Flipkart -- the allowance is really
   * spent -- and then the walk record does not survive. Nothing ever records an
   * outcome, so if the report were still on the list the alarm would ask
   * Flipkart for it again, and again. **A walk that THROWS is caught and
   * recorded; only a walk that vanishes proves the early removal.** */
  const cannotStart = {
    ...walk,
    startAWalk: async () => { tries += 1; /* started, and then nothing */ },
    theWalkNow: async () => null,
  };
  await startTheNight(browser.chrome, {
    doing: ['fk_orders', 'fk_returns', 'fk_payments'],
    mayAskFor: 20, at: 1, openAt: 'https://x/',
  });
  /* Forty ticks of the alarm -- eighty minutes of a night that runs for hours. */
  for (let tick = 0; tick < 40; tick += 1) {
    // eslint-disable-next-line no-await-in-loop
    await carryTheNightOn(browser.chrome, { ...cannotStart, at: 2 + tick });
  }
  const night = await theNight(browser.chrome);
  check('a report whose walk cannot be started is attempted ONCE, never again',
    tries === 3);
  check('and the seller allowance is spent three times, not twenty',
    night.spent === 3);
  check('and the night stops owing them rather than spinning on them for ever',
    night.left.length === 0);
}

{
  /* **AND A WALK THAT THROWS OUTRIGHT IS RECORDED, not thrown onward.** Thrown,
   * it reaches the alarm listener as an unhandled rejection and the tick after
   * tries the same report again. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  let tries = 0;
  await startTheNight(browser.chrome, {
    doing: ['fk_ads_daily'], mayAskFor: 0, at: 1, openAt: 'https://x/',
  });
  await carryTheNightOn(browser.chrome, {
    ...walk,
    startAWalk: async () => { tries += 1; throw new Error('no tab could be opened'); },
    at: 2,
  });
  const night = await theNight(browser.chrome);
  check('a walk that throws on starting is written down rather than thrown onward',
    night.done.length === 1 && night.done[0].state === 'failed');
  check('and it says it never started, so nobody looks for a broken button',
    night.done[0].say.includes('could not be started'));
  check('and it was tried once', tries === 1);
}

{
  /* **AND THE EASIEST WAY IN IS CLOSED AT THE DOOR.** With nowhere to start
   * from, every walk throws -- and the allowance is spent before the walk, so
   * each throw cost one of the seller's twenty and produced nothing. It was
   * reachable by leaving one argument off. */
  const browser = installFakeChrome();
  check('a night with nowhere to start from is refused before anything is spent',
    (await said(() => startTheNight(browser.chrome, { doing: ['fk_orders'], mayAskFor: 20 })))
      .includes('which portal page its reports start from'));
  check('and no night was written at all',
    (await theNight(browser.chrome)) === null);
}

{
  /* **ATTEMPTED IS ENOUGH, ON ITS OWN.** */
  const browser = installFakeChrome();
  await startTheNight(browser.chrome, {
    doing: ['a', 'b'], mayAskFor: 0, at: 1, openAt: 'https://x/',
  });
  await thatOneIsBeingTried(browser.chrome, 'a');
  check('a report being attempted is off the list immediately',
    whatIsNext(await theNight(browser.chrome)) === 'b');
  check('and it is not yet counted as done, because nobody knows what it did',
    (await theNight(browser.chrome)).done.length === 0);
  check('and attempting against no night at all is refused',
    (await said(() => thatOneIsBeingTried(installFakeChrome().chrome, 'a')))
      .includes('a night that is not going'));
}

const EXPECTED = 58;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
