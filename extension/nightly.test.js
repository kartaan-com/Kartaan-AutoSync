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
  ONLY_ITS_NEWEST_DAY,
  whyOnlyItsNewestDay,
  THE_NIGHT,
  endTheNight,
  NOT_ASKED,
  howTheNightWent, secondsPerReport, theSlowestLine, theSlowestThree, theReportTable,
  oneWasAskedFor,
  spendsTheAllowance,
  startTheNight,
  thatOneIsDone,
  theNight,
  whatIsNext,
  whyItCannotBeAskedFor,
  whatIsBeingBuilt,
  whatThatWasAskedUnder,
  carryTheNightOn,
  thatOneIsBeingTried,
  NOT_BUILT_YET,
  NOT_AVAILABLE_YET,
  NEEDS_YOU_STATE,
  NEEDS_YOU,
  GIVE_UP_AFTER_DAYS,
  whatIsNotBuiltYet,
  whatNeedsYou,
  theRunLog,
  RECHECK_ALARM,
  setTheRecheckClock,
  theRecheckSync,
  whatIsBeingRechecked,
  whatIsPaused,
  rememberLastCaptured,
  theDayAfterTheLastCaptured,
  rememberLastLanded,
  daysNobodyTried,
  CATCH_UP_REACH_DAYS,
  clearNamedNeedsYouEntries,
  theRangeOfTheDays,
  TAB_CLOSED_SAY,
} from './nightly.js';
import { STARTED_AFTER_IDLE, startWhenFree } from './idle.js';
import { NOT_AVAILABLE_YET as THE_WALKS_WORD } from './walk.js';

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
  /* **THE SAME QUESTION ASKED OF THE PICTURE-OF-NOW LIST.** Each of them must be
   * a real report the recipe file already declares cannot be asked for a past day
   * -- otherwise this list quietly stops a seller's report from ever being
   * fetched, which is the worst thing in here. */
  check('every report that only exists for now is real and is declared as such',
    ONLY_ITS_NEWEST_DAY.every((one) => book.recipes[one]
      && (book.reports.find((r) => r.id === one) || {}).cannotBeAskedForAgain));
  /* **AND A ROLLING WINDOW IS NOT ONE OF THEM.** Meesho returns and claims hand
   * over whatever is in the tab now; left out of a past-day sync they would be
   * lost, and they landed on his own run of 6 September. */
  check('and the three tables read off a page are on it, so a past day never reads the page of today',
    ['me_product_performance', 'me_pricing', 'fk_quality_insights', 'az_listings', 'az_fee_preview', 'az_ads'].every((one) => ONLY_ITS_NEWEST_DAY.includes(one)));
  check('while a rolling-window report is not on that list',
    !ONLY_ITS_NEWEST_DAY.includes('me_returns') && !ONLY_ITS_NEWEST_DAY.includes('me_claims'));
  /* **A PAST DAY OF THE ADS REPORT IS NOT WALKED AGAIN, AND IS TOLD WHY IN ITS OWN WORDS (the fresh review of 27 Oct 2026):** every run takes the saved report's last 30 days, so a day missed is already in the newest file, and a walk per owed day would pay the pause and visit the ads site again each time. */
  const adsWhy = whyOnlyItsNewestDay({ latestDay: '2026-10-27' }, 'az_ads', '2026-10-24');
  check('a past day of the Amazon ads report is left out and says the newest file already holds it', typeof adsWhy === 'string' && adsWhy.includes('30 days') && !adsWhy.includes('picture of how things stand'));
}

/* **RETURNS LEFT THE REPORTS CENTRE ON 2026-09-14**, by his ruling, so asking for
 * it spends none of the twenty. */
check('asking for a Reports Centre report spends one of the twenty, and returns no longer does',
  spendsTheAllowance('fk_orders') && spendsTheAllowance('fk_payments')
  && !spendsTheAllowance('fk_returns'));
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
  await startTheNight(browser.chrome, { doing: ['fk_orders', 'fk_payments'], mayAskFor: 1, at: 1, openAt: 'https://x/' });
  check('with one allowed, the first is let through',
    whyItCannotBeAskedFor(await theNight(browser.chrome), 'fk_orders') === null);

  /* **COUNTED BEFORE THE REQUEST GOES.** A worker shut down between the request
   * and the counting leaves a request that happened and a count that says it did
   * not -- and the next run spends it again. */
  await oneWasAskedFor(browser.chrome);
  check('and once it is spent, the next one is refused',
    (whyItCannotBeAskedFor(await theNight(browser.chrome), 'fk_payments') || '')
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
  check('nothing can be recorded against a sync that is not going',
    (await said(() => thatOneIsDone(browser.chrome, { reportId: 'a', state: 'landed', at: 1 })))
      .includes('a sync that is not going'));
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
    pageWas: 'Oops! We can\'t seem to find the page you\'re looking for.',
  });
  const ended = await endTheNight(browser.chrome, { why: 'the seller was signed out', at: 4 });
  const words = howTheNightWent(ended);

  /* **JOB 8 (A65, 2026-09-23): FIVE COUNTS, NOT ONE WORD "REACHED".** A report
   * that landed and a report that failed used to count the same, as one of
   * "N reports reached" -- so a night that landed nothing still read as a
   * night where everything was "reached". */
  check('the headline counts landed and failed separately',
    words.includes('1 landed,') && words.includes('1 failed'));
  check('and says the total in all', words.includes('-- 3 in all.'));
  check('and how many produced a real file, with the bytes',
    words.includes('1 produced a real file, 1200 bytes'));
  check('and how much of the seller allowance went', words.includes('0 of the 0 allowed'));
  /* **IT SAYS WHAT DID NOT HAPPEN AS WELL AS WHAT DID.** A summary listing only
   * what ran reads as a clean night whether or not it was one. */
  /* **"NEVER REACHED" WAS THE WRONG WORDS AND IT COST AN HOUR (6 September).**
   * `fk_views` was being walked at that very moment and the summary called it
   * never reached, so a report doing its job read as a tenth failure. A report
   * that has not been started yet is NOT STARTED; one being walked is said
   * separately; and they are different things. */
  check('and names what was never started, in those words', words.includes('Not started: fk_views'));
  check('and names each report with what became of it',
    words.includes('fk_ads_daily: landed (1200 bytes)')
    && words.includes('fk_claims: failed -- nothing matched Download'));
  /* **AND WHAT THE PAGE ACTUALLY WAS, WHICH IS THE WHOLE LESSON OF 6 SEPTEMBER.**
   * Nine reports failed on three different pages looking for three different
   * things. The walk had captured "Oops! We can't seem to find the page you're
   * looking for" every time, and the night threw it away every time -- so nine
   * failures with one cause arrived looking like nine faults. */
  check('and under each failure, what the page actually said',
    words.includes('the page said: Oops!'));
  check('and the night keeps why it ended', ended.why === 'the seller was signed out');
}

{
  /* **THE ONE LINE THIS WHOLE CHANGE EXISTS FOR, AND IT HAD NO CHECK AT ALL
   * (A26R5).** `carryTheNightOn` carries `pageWas` off the walk's answer and
   * into the night's record -- one line -- and every check for the new evidence
   * reached it by calling `thatOneIsDone` DIRECTLY with the page already in
   * hand. Deleting that line left all 654 checks green, and the seller's night
   * silently goes back to throwing the evidence away, which is the exact
   * regression this change was written to prevent.
   *
   * **THIS REPOSITORY'S OWN HANDOVER CALLS THAT ITS WORST RECURRING FAULT, AND
   * THIS CHANGE SHIPPED ONE.** So this check walks it the way the night does:
   * the walk answers with a page, and the record is read back afterwards. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_ads_daily'], mayAskFor: 0, at: 1, openAt: 'https://x/',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  walk.itFinished({
    state: 'failed',
    reportId: 'fk_ads_daily',
    say: 'could not find "the other reports tab"',
    pageWas: 'Oops! We cannot seem to find the page you are looking for.',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 3 });
  const kept = (await theNight(browser.chrome)).done[0];
  check('the page the walk saw is carried from the walk into the night record',
    kept.pageWas === 'Oops! We cannot seem to find the page you are looking for.');
  check('and it comes out again in what a person reads at breakfast',
    howTheNightWent(await theNight(browser.chrome)).includes('the page said: Oops!'));
}

{
  /* **A REPORT BEING WALKED RIGHT NOW IS IN NEITHER LIST, AND MUST STILL BE
   * NAMED.** Taking it off the owed list the moment it is attempted is what
   * makes a retry loop impossible -- and it is also how a report in progress
   * could vanish from the summary altogether. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_ads_daily', 'fk_claims'], mayAskFor: 0, at: 1, openAt: 'https://x/',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  const mid = howTheNightWent(await theNight(browser.chrome));
  check('a report being walked right now is named as being fetched',
    mid.includes('Being fetched right now: fk_ads_daily'));
  /* **AND IT IS COUNTED IN THE TOTAL (A26R5).** The first line used to say "0 of
   * 1 reports were reached" on a two-report night with one walking -- the report
   * in flight vanished from the count while the list one line below named it.
   * That first line is the one a person reads. */
  check('and the total counts it rather than dropping it',
    mid.includes('-- 2 in all.'));
  check('and it is not called never-started while it is being walked',
    !mid.includes('Not started: fk_ads_daily'));
  check('while the one behind it is correctly not started yet',
    mid.includes('Not started: fk_claims'));

  walk.itFinished({ state: 'landed', reportId: 'fk_ads_daily', size: 5 });
  await carryTheNightOn(browser.chrome, { ...walk, at: 3 });
  const after = howTheNightWent(await theNight(browser.chrome));
  check('and once it finishes it is no longer said to be being fetched',
    !after.includes('Being fetched right now: fk_ads_daily'));
}

{
  /* **AND THE CASE THAT ACTUALLY PROVES IT: THE LAST REPORT OF THE NIGHT.**
   * With another report behind it, the next one overwrites the name anyway --
   * so the check above passes whether or not anything clears it. Driven, it
   * stayed green with the clearing removed. **A night of ONE report is the only
   * shape where the clearing is the thing being tested**, and a summary still
   * claiming a report is being fetched at breakfast is a night that reads as
   * hung when it finished hours ago. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_ads_daily'], mayAskFor: 0, at: 1, openAt: 'https://x/',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  walk.itFinished({ state: 'landed', reportId: 'fk_ads_daily', size: 5 });
  await carryTheNightOn(browser.chrome, { ...walk, at: 3 });
  const ended = howTheNightWent(await theNight(browser.chrome));
  check('the last report of the night stops being named as in progress when it ends',
    !ended.includes('Being fetched right now'));
  check('and it is named as done instead', ended.includes('fk_ads_daily: landed'));
}

check('a summary of no night at all says so rather than falling over',
  howTheNightWent(null) === 'No sync has been run.');


/* --------------------------------- the seller's own panel name, on the night */

{
  /* **THE NIGHT CARRIES THE SELLER'S OWN PANEL NAME, AND NOTHING DID UNTIL NOW
   * (2026-09-09).** All five Meesho recipes carry `{panel}` in an address and
   * `walk.js` refuses a step carrying one without it, in words. The only thing
   * joining the name the seller saved on the panel to the walk that needs it was
   * one line in `worker.js` -- a file with no checks by design. **Delete that
   * line and all 896 checks stayed green**, while every Meesho report a seller
   * ran failed with the one sentence the panel had already asked him about. He
   * met it twice in one night with the name saved.
   *
   * **SO IT IS ON THE NIGHT, BESIDE `openAt` AND `dataDate`.** A night is
   * already one platform's and one day's -- it is one panel's too -- and being
   * on the night is what makes it something a check can reach. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['me_orders', 'me_payments'], mayAskFor: 0, at: 1,
    openAt: 'https://supplier.meesho.com', dataDate: '2026-09-08', panel: 'rumee-panel',
  });
  check('the night keeps the seller\'s own panel name',
    (await theNight(browser.chrome)).panel === 'rumee-panel');

  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  check('and hands it to the walk it starts', walk.started[0].panel === 'rumee-panel');

  /* **AND TO THE SECOND REPORT AS WELL.** The night reads itself back out of
   * storage for every report, so a name kept only in the caller's hand would
   * reach the first walk and nothing after it. */
  walk.itFinished({ state: 'landed', reportId: 'me_orders', size: 44600 });
  await carryTheNightOn(browser.chrome, { ...walk, at: 3 });
  check('and to every report after it, not only the first',
    walk.started[1].reportId === 'me_payments' && walk.started[1].panel === 'rumee-panel');
}

{
  /* **AND A NIGHT NOBODY GAVE A NAME HANDS NONE, RATHER THAN GUESSING ONE.**
   * `walk.js` is where that is refused and it refuses in the seller's own words.
   * Nothing here may quietly put something plausible in its place: a made-up
   * name is a walk on somebody else's supplier panel. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['me_orders'], mayAskFor: 0, at: 1, openAt: 'https://supplier.meesho.com',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  check('a night told no panel name hands the walk an empty one, never a guess',
    walk.started[0].panel === '');
}

/* ------------------------------------------- moving the night on, one at a time */

/** A stand-in for the walk in flight, driven by hand. */
function aWalkThat() {
  const it = { held: null, started: [], cleared: 0 };
  it.theWalkNow = async () => it.held;
  it.endTheWalkNow = async () => { it.held = null; it.cleared += 1; };
  /* **EVERYTHING THE NIGHT HANDS OVER IS KEPT, NOT THREE NAMED FIELDS.** It
   * used to name the three it knew about, so a fourth the night stopped
   * carrying -- the seller's own panel name -- could not be seen from a check at
   * all. What the walk is told is what a check has to be able to read. */
  it.startAWalk = async (how) => {
    it.started.push({ ...how });
    it.held = { reportId: how.reportId, answer: null };
  };
  it.itFinished = (answer) => { it.held = { ...it.held, answer }; };
  return it;
}

{
  /* **A53: TWO CALLS AT ONCE BOOK A FINISHED WALK ONCE.** Walk-done, the alarm and
   * Run now can overlap; on 2026-09-14 `fk_ads_fsn` was listed twice in one night. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_ads_daily', 'fk_claims'], mayAskFor: 0, at: 1,
    openAt: 'https://seller.flipkart.com/index.html', dataDate: '2026-09-04',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  walk.itFinished({ state: 'landed', reportId: 'fk_ads_daily', size: 10 });
  await Promise.all([
    carryTheNightOn(browser.chrome, { ...walk, at: 3 }),
    carryTheNightOn(browser.chrome, { ...walk, at: 3 }),
  ]);
  const booked = (await theNight(browser.chrome)).done.filter((one) => one.reportId === 'fk_ads_daily');
  check('two calls at once book a finished walk once', booked.length === 1);
  check('and start the next report once', walk.started.length === 2);
}

{
  /* **A53: A FINISHED WALK LEFT OVER FROM AN EARLIER NIGHT IS NOT BOOKED.** Run 4
   * of 2026-09-15 ended in 18 s, booking run 3's late failure as its own. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  walk.held = {
    reportId: 'fk_ads_daily', startedAt: 5,
    answer: { state: 'failed', reportId: 'fk_ads_daily', say: 'an earlier night' },
  };
  await startTheNight(browser.chrome, {
    doing: ['fk_ads_daily'], mayAskFor: 0, at: 10, openAt: 'https://x/', dataDate: '2026-09-12',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 11 });
  const night = await theNight(browser.chrome);
  check('a finished walk from an earlier night is not booked as this night\'s answer',
    night.done.length === 0 && !night.finishedAt);
  check('and this night walks its own report instead',
    walk.started.length === 1 && walk.started[0].reportId === 'fk_ads_daily');
}

{
  /* **A53: THE NIGHT AS A FILE FOR DRIVE**, so a failure is readable with nobody at
   * the browser. */
  const browser = installFakeChrome();
  await startTheNight(browser.chrome, {
    doing: ['me_returns'], mayAskFor: 0, at: Date.UTC(2026, 8, 15, 15, 10), openAt: 'https://x/',
  });
  await thatOneIsDone(browser.chrome, {
    reportId: 'me_returns', state: 'failed', say: 'Nothing began downloading in 30 seconds',
    pageWas: 'Download Table Data', at: Date.UTC(2026, 8, 15, 15, 20),
  });
  await endTheNight(browser.chrome, { at: Date.UTC(2026, 8, 15, 15, 20), why: 'Every report was reached.' });
  const log = theRunLog(await theNight(browser.chrome));
  check('a night is written out as one text file named by when it started',
    log.reportId === 'run_log' && log.fileName === 'run_log_2026-09-15T15-10-00-000Z.txt');
  check('and it carries each failure in its own words and what the page said',
    log.text.includes('me_returns: failed -- Nothing began downloading in 30 seconds')
    && log.text.includes('the page said: Download Table Data')
    && log.text.includes('Finished: 2026-09-15T15:20:00.000Z'));
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
  /* **JOB 8, PART 2 (A65, 2026-09-23): "EVERY REPORT WAS REACHED" IS NEVER
   * WRITTEN WHEN SOMETHING FAILED.** `fk_claims` failed here -- the old code
   * still wrote "Every report was reached." as why the night ended, which is
   * exactly the sentence his words called out: true of the ATTEMPT, read as a
   * clean night by anyone who did not open the file. */
  check('and it says why it ended -- naming what did not land, not "reached"',
    ended.why.includes('1 report did not land: fk_claims')
    && ended.why.includes('failed')
    && !ended.why.includes('Every report was reached'));

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
    && night.done[0].state === NOT_ASKED
    && night.done[0].say.includes('has not been asked for'));
  check('and nothing was spent', night.spent === 0);
  const words = howTheNightWent(night);
  check('and the summary says NOT ASKED FOR, never "correctly had nothing to fetch" (A82)',
    words.includes('1 NOT ASKED FOR') && !words.includes('correctly had nothing to fetch'));
  check('and the refused day still counts in the total, once', words.includes('-- 2 in all'));
  await carryTheNightOn(browser.chrome, { ...walk, at: 3 });
  walk.itFinished({ state: 'landed', reportId: 'fk_ads_daily', size: 5 });
  await carryTheNightOn(browser.chrome, { ...walk, at: 4 });
  const ended = await theNight(browser.chrome);
  check('and the night never ends "Every report was reached" while a day was not asked for (A82)',
    Boolean(ended.finishedAt) && ended.why.includes('not asked, allowance used up')
    && !ended.why.includes('Every report was reached'));
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
  /* **A53: PAUSED TO RESUME FROM THAT REPORT, RUMEE'S WAY IMPROVED.** */
  const paused = await whatIsPaused(browser.chrome);
  check('and the sync is paused to resume from the report that met the sign-in',
    Boolean(paused) && paused.reportIds.join() === 'fk_ads_daily,fk_claims,fk_views');
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
  /* Returns spends nothing since 2026-09-14, so two of the three spend. */
  check('and the seller allowance is spent twice -- once for each report that spends -- not twenty',
    night.spent === 2);
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
      .includes('a sync that is not going'));
}

/* --------------- what the platform is already building, and collecting it */

/* **THE FAULT THIS WHOLE BLOCK EXISTS FOR, MEASURED ON HIS OWN FLIPKART ON
 * 2026-09-11.** `fk_orders` was asked for, Flipkart built it and listed it as
 * Generated -- and the very next run walked the ASKING phase again from the top.
 * `walk.js` had handed back what it was asked under since it was written, with
 * its own comment saying *"holding it is what stops this being asked a second
 * time"*, and nothing anywhere stored it or read it back.
 *
 * **AND IT IS NOT A MISSING FILE, IT IS A SELLER'S ALLOWANCE.** Flipkart's
 * Reports Centre allows twenty requests a day. Re-asking spends them on reports
 * the platform already has in hand.
 *
 * **SO THESE ARE WALKED THE WAY A NIGHT WALKS THEM**, never by calling the
 * storage helpers directly -- which is this repository's own worst recurring
 * fault and the reason the `pageWas` check above is written the way it is. */
{
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_orders'], mayAskFor: 1, at: 1,
    openAt: 'https://seller.flipkart.com/index.html', dataDate: '2026-09-10',
  });

  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  check('the first run is told nothing is being built yet, so it asks',
    walk.started[0].askedAlready === null);
  check('and asking spent one of the twenty',
    (await theNight(browser.chrome)).spent === 1);

  walk.itFinished({
    state: 'still-waiting', reportId: 'fk_orders', dataDate: '2026-09-10',
    theirId: '2026-09-10', say: 'Asked for it.',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 3 });
  check('what Flipkart is building is remembered, not thrown away with the night',
    (await whatIsBeingBuilt(browser.chrome))['fk_orders|2026-09-10'] === '2026-09-10');
  check('and it is asked for by the report and the day together',
    (await whatThatWasAskedUnder(browser.chrome, 'fk_orders', '2026-09-10')) === '2026-09-10');
  check('while another day of the same report is not being built',
    (await whatThatWasAskedUnder(browser.chrome, 'fk_orders', '2026-09-09')) === null);

  /* **AND THE NEXT RUN COLLECTS. THIS IS THE LINE HE ASKED FOR.** */
  const second = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_orders'], mayAskFor: 1, at: 10,
    openAt: 'https://seller.flipkart.com/index.html', dataDate: '2026-09-10',
  });
  await carryTheNightOn(browser.chrome, { ...second, at: 11 });
  check('THE NEXT RUN IS TOLD WHAT IT WAS ASKED UNDER, so it collects instead of asking',
    second.started[0].askedAlready === '2026-09-10');
  /* **AND COLLECTING COSTS NOTHING.** The twenty are requests; coming back for a
   * finished report is a page and a download. Counted, four collections of one
   * report would take a fifth of the seller's day for no requests at all. */
  check('and collecting spends none of the twenty',
    (await theNight(browser.chrome)).spent === 0);

  /* **AND A DAY WITH NOTHING LEFT TO SPEND CAN STILL COLLECT**, or the requests
   * would be gone and the files would never arrive. */
  check('a run with no allowance left may still collect what it already asked for',
    whyItCannotBeAskedFor({ spent: 20, mayAskFor: 20 }, 'fk_orders', true) === null);
  check('but may not ask for something new',
    whyItCannotBeAskedFor({ spent: 20, mayAskFor: 20 }, 'fk_orders', false) !== null);

  /* **A COLLECT THAT FAILED IS STILL A REPORT FLIPKART HAS IN HAND.** Forgotten
   * there, the next run goes round and asks again, which is the whole fault. */
  second.itFinished({
    state: 'failed', reportId: 'fk_orders', dataDate: '2026-09-10',
    say: 'the row was not on the page',
  });
  await carryTheNightOn(browser.chrome, { ...second, at: 12 });
  check('a collection that failed is still remembered, or the next run asks again',
    (await whatThatWasAskedUnder(browser.chrome, 'fk_orders', '2026-09-10')) === '2026-09-10');

  /* **AND IT IS FORGOTTEN THE MOMENT THE FILE LANDS**, or every later run
   * collects a report that arrived days ago. */
  const third = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_orders'], mayAskFor: 1, at: 20,
    openAt: 'https://seller.flipkart.com/index.html', dataDate: '2026-09-10',
  });
  await carryTheNightOn(browser.chrome, { ...third, at: 21 });
  third.itFinished({
    state: 'landed', reportId: 'fk_orders', dataDate: '2026-09-10', size: 4096,
  });
  await carryTheNightOn(browser.chrome, { ...third, at: 22 });
  check('and once the file lands it is forgotten',
    (await whatThatWasAskedUnder(browser.chrome, 'fk_orders', '2026-09-10')) === null);
}

{
  /* **A FIRST NIGHT HAS NO RECORD AT ALL, AND THAT IS ORDINARY.** Read as
   * anything but empty it would either refuse to start or believe a report was
   * being built that nobody ever asked for. */
  const browser = installFakeChrome();
  check('a first night finds nothing being built rather than failing',
    Object.keys(await whatIsBeingBuilt(browser.chrome)).length === 0);
}

/* ----------------------- a day the platform has not built yet (his ruling, 2026-09-14)
 *
 * **HIS WORDS:** *"There will be scenarios when a report will not be available
 * for a date. In that case Rumee AutoSync used to mark that as not available and
 * moves ahead."* Measured the same day: Flipkart's Reports Centre greyed out every
 * day after the 11th, and both refusals were written down as FAILED, never tried
 * again, and one of them used one of the seller's twenty for nothing. */
const ON = (day) => new Date(`${day}T10:00:00`).getTime();
const FLIPKART_HOME = 'https://seller.flipkart.com/index.html';

check('the night and the walk spell "not available yet" the same way',
  NOT_AVAILABLE_YET === THE_WALKS_WORD);
check('and three days of trying is the reference\'s own number', GIVE_UP_AFTER_DAYS === 3);

{
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_orders', 'fk_claims'], mayAskFor: 2, at: ON('2026-09-14'),
    openAt: FLIPKART_HOME, dataDate: '2026-09-13',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: ON('2026-09-14') });
  check('a Reports Centre report is counted before it is walked',
    (await theNight(browser.chrome)).spent === 1);
  walk.itFinished({
    state: NOT_AVAILABLE_YET, reportId: 'fk_orders', dataDate: '2026-09-13',
    say: '2026-09-13 is on the calendar but the portal has it switched off.',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: ON('2026-09-14') });
  const night = await theNight(browser.chrome);
  check('A DAY THE PLATFORM HAS NOT BUILT IS WRITTEN DOWN AS NOT AVAILABLE YET, NOT AS FAILED',
    night.done[0].state === NOT_AVAILABLE_YET);
  check('and the night moves on to the next report',
    Boolean(walk.started[1]) && walk.started[1].reportId === 'fk_claims');
  check('AND THE REQUEST IT COUNTED IS GIVEN BACK, because the calendar comes before Submit',
    night.spent === 0 && Object.values(night.spentOn || {}).every((n) => n === 0));
  const owed = (await whatIsNotBuiltYet(browser.chrome))['fk_orders|2026-09-13'];
  check('and the day is remembered as owed, tried on one day so far',
    Boolean(owed) && owed.triedOn.join() === '2026-09-14');
  check('and the seller is told how many days of trying are left',
    night.done[0].say.includes('Tried on 1 of 3 days'));
}

{
  const browser = installFakeChrome();
  const walk = aWalkThat();
  const start = (dataDate, at) => startTheNight(browser.chrome, {
    doing: ['fk_views'], mayAskFor: 0, at, openAt: FLIPKART_HOME, dataDate,
  });
  await start('2026-09-13', ON('2026-09-14'));
  await carryTheNightOn(browser.chrome, { ...walk, at: ON('2026-09-14') });
  walk.itFinished({ state: NOT_AVAILABLE_YET, reportId: 'fk_views', dataDate: '2026-09-13', say: 'not built.' });
  await carryTheNightOn(browser.chrome, { ...walk, at: ON('2026-09-14') });

  await start('2026-09-14', ON('2026-09-15'));
  await carryTheNightOn(browser.chrome, { ...walk, at: ON('2026-09-15') });
  check('THE NEXT RUN TRIES THE DAY IT IS OWED FIRST',
    walk.started[1].reportId === 'fk_views' && walk.started[1].dataDate === '2026-09-13');
  walk.itFinished({ state: 'landed', reportId: 'fk_views', dataDate: '2026-09-13', size: 9 });
  await carryTheNightOn(browser.chrome, { ...walk, at: ON('2026-09-15') });
  check('and then its own day, in the same run',
    Boolean(walk.started[2]) && walk.started[2].dataDate === '2026-09-14');
  check('and a day that turns out to be there is forgotten',
    !(await whatIsNotBuiltYet(browser.chrome))['fk_views|2026-09-13']);
  walk.itFinished({ state: 'landed', reportId: 'fk_views', dataDate: '2026-09-14', size: 9 });
  await carryTheNightOn(browser.chrome, { ...walk, at: ON('2026-09-15') });
  check('and the run ends having walked the report once per day and no more',
    walk.started.length === 3 && Boolean((await theNight(browser.chrome)).finishedAt));
}

{
  const browser = installFakeChrome();
  const walk = aWalkThat();
  /* A run of one report, answered "not built" every time, to the end. */
  const oneRun = async (runDay, dataDate) => {
    await startTheNight(browser.chrome, {
      doing: ['fk_views'], mayAskFor: 0, at: ON(runDay), openAt: FLIPKART_HOME, dataDate,
    });
    for (let turn = 0; turn < 6; turn += 1) {
      // eslint-disable-next-line no-await-in-loop
      await carryTheNightOn(browser.chrome, { ...walk, at: ON(runDay) });
      // eslint-disable-next-line no-await-in-loop
      if ((await theNight(browser.chrome)).finishedAt) return;
      const walking = walk.started[walk.started.length - 1];
      walk.itFinished({
        state: NOT_AVAILABLE_YET, reportId: 'fk_views', dataDate: walking.dataDate, say: 'not built.',
      });
    }
  };
  await oneRun('2026-09-14', '2026-09-13');
  await oneRun('2026-09-14', '2026-09-13');
  check('running twice on one day uses up one day of trying, not two',
    (await whatIsNotBuiltYet(browser.chrome))['fk_views|2026-09-13'].triedOn.length === 1);
  await oneRun('2026-09-15', '2026-09-14');
  await oneRun('2026-09-16', '2026-09-15');
  check('A DAY STILL NOT BUILT ON THE THIRD DIFFERENT DAY NEEDS THE SELLER',
    (await whatNeedsYou(browser.chrome)).some((one) => one.reportId === 'fk_views'
      && one.dataDate === '2026-09-13'));
  check('and it is no longer owed, so it is not tried again',
    !(await whatIsNotBuiltYet(browser.chrome))['fk_views|2026-09-13']);
  const given = (await theNight(browser.chrome)).done.find((one) => one.dataDate === '2026-09-13');
  check('and that run writes it down as needing the seller, in words they can act on',
    Boolean(given) && given.state === NEEDS_YOU_STATE && given.say.includes('fetch it by hand'));
  /* **JOB 8, PART 2 (A65, 2026-09-23): THE NIGHT THAT ESCALATED A DAY TO
   * "NEEDS YOU" DOES NOT END SAYING "EVERY REPORT WAS REACHED".** This is the
   * exact shape his words named: three tries, needing him, and the log's
   * "Why it ended" line the old code still wrote as a clean night. */
  check('and the night does not end saying "every report was reached"',
    (await theNight(browser.chrome)).why.includes('needs you')
    && !(await theNight(browser.chrome)).why.includes('Every report was reached'));
  const before = walk.started.length;
  await oneRun('2026-09-17', '2026-09-16');
  check('and the next run does not walk that day again',
    walk.started.length > before
    && walk.started.slice(before).every((one) => one.dataDate !== '2026-09-13'));
}

/* ------------------------------------------- Job 8: a truthful headline (A65) */

{
  /* **FIVE REAL STATES, COUNTED SEPARATELY -- NOT COLLAPSED INTO ONE WORD
   * "REACHED" (his words, 2026-09-23).** One of everything: landed, waiting
   * on the platform two different ways (a day not built yet, and a report
   * still being collected), needing him, failed, correctly nothing to fetch,
   * and one never started. */
  const browser = installFakeChrome();
  await startTheNight(browser.chrome, {
    doing: ['fk_landed', 'fk_not_built', 'fk_collecting', 'fk_needs_you', 'fk_failed', 'fk_nothing', 'fk_never'],
    mayAskFor: 0, at: 1, openAt: FLIPKART_HOME, dataDate: '2026-09-20',
  });
  await thatOneIsDone(browser.chrome, {
    reportId: 'fk_landed', state: 'landed', size: 500, at: 2, dataDate: '2026-09-20',
  });
  await thatOneIsDone(browser.chrome, {
    reportId: 'fk_not_built', state: NOT_AVAILABLE_YET, say: 'not built.', at: 3, dataDate: '2026-09-20',
  });
  await thatOneIsDone(browser.chrome, {
    reportId: 'fk_collecting', state: 'still-waiting', say: 'asked.', at: 4, dataDate: '2026-09-20',
  });
  await thatOneIsDone(browser.chrome, {
    reportId: 'fk_needs_you', state: NEEDS_YOU_STATE, say: 'fetch it by hand.', at: 5, dataDate: '2026-09-19',
  });
  await thatOneIsDone(browser.chrome, {
    reportId: 'fk_failed', state: 'failed', say: 'the button was not there', at: 6, dataDate: '2026-09-20',
  });
  await thatOneIsDone(browser.chrome, {
    reportId: 'fk_nothing', state: 'nothing-to-fetch', say: 'no campaign ran.', at: 7, dataDate: '2026-09-20',
  });
  const words = howTheNightWent(await theNight(browser.chrome));
  check('the headline counts landed', words.includes('1 landed,'));
  check('and counts waiting on the platform, both a day not built and a collect in flight',
    words.includes('2 waiting on the platform (the day is not built yet)'));
  check('and counts not started', words.includes('1 not started'));
  check('and counts needing him', words.includes('1 need him'));
  check('and counts failed', words.includes('1 failed'));
  check('and counts a correct nothing-to-fetch separately, never as a failure',
    words.includes('1 correctly had nothing to fetch'));
  check('and the total accounts for every one of them, once each', words.includes('-- 7 in all.'));
}

{
  /* **A REPORT ASKED THEN COLLECTED IS ONE OUTCOME, NOT TWO.** It gets a
   * `still-waiting` entry when asked and a final entry when collected; the
   * headline counts its LAST entry only, or the same report-day would be
   * both "waiting" and "landed" at once. */
  const browser = installFakeChrome();
  await startTheNight(browser.chrome, {
    doing: ['fk_two_step'], mayAskFor: 0, at: 1, openAt: FLIPKART_HOME, dataDate: '2026-09-20',
  });
  await thatOneIsDone(browser.chrome, {
    reportId: 'fk_two_step', state: 'still-waiting', say: 'asked.', at: 2, dataDate: '2026-09-20',
  });
  await thatOneIsDone(browser.chrome, {
    reportId: 'fk_two_step', state: 'landed', size: 900, at: 3, dataDate: '2026-09-20',
  });
  const words = howTheNightWent(await theNight(browser.chrome));
  check('a report asked then collected counts once, as landed',
    words.includes('1 landed,') && words.includes('0 waiting on the platform'));
  check('and the total is not doubled', words.includes('-- 1 in all.'));
}

{
  /* **A CLEAN NIGHT STILL SAYS SO, IN FULL (the regression guard for Job 8,
   * part 2).** The fix is that "Every report was reached." is withheld when
   * something is wrong -- not that it is withheld always. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_ads_daily'], mayAskFor: 0, at: 1, openAt: FLIPKART_HOME, dataDate: '2026-09-20',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  walk.itFinished({ state: 'landed', reportId: 'fk_ads_daily', size: 5 });
  const ended = await carryTheNightOn(browser.chrome, { ...walk, at: 3 });
  check('a night where everything landed says exactly "Every report was reached."',
    ended.why === 'Every report was reached.');
}

{
  /* **JOB 8, PART 3: THE REQUEST LINE NAMES WHAT IT ACTUALLY COUNTS.** Only
   * `fk_orders` and `fk_payments` ever spend from Flipkart's Reports Centre
   * twenty; every ad report asks Flipkart by a different door and spends
   * none of it. His own words: "0 of the 2 allowed requests were spent" read
   * as false on a night that DID ask Flipkart for ad reports -- it was true
   * of the Reports Centre count, which is not what the old wording said it
   * was counting. */
  const browser = installFakeChrome();
  await startTheNight(browser.chrome, {
    doing: ['fk_ads_overall', 'fk_ads_orders'], mayAskFor: 2, at: 1, openAt: FLIPKART_HOME, dataDate: '2026-09-18',
  });
  const words = howTheNightWent(await theNight(browser.chrome));
  check('the request line names the Reports Centre and the two reports it counts',
    words.includes('0 of the 2 allowed Flipkart Reports Centre requests (fk_orders, fk_payments) were spent.'));
  check('and it does not claim to cover every Flipkart request in general',
    !/\d+ of the \d+ allowed Flipkart requests were spent/.test(words));
}

{
  /* **AT LEAST ONE CHECK BUILT FROM THE SHAPE OF A REAL LOG (Job 8, "done
   * when" #3).** Adapted from `docs/PLAN_TO_FINISH.md`'s own table for the
   * real `run_log_2026-09-18T11-00-00-089Z.txt` (not the raw file itself,
   * which this job did not need to open a browser for): two Flipkart ad
   * reports ticked, one landed, the rest not built yet (`fk_ads_overall`'s
   * January days, F3/F4) or needing him (`fk_ads_orders`'s January days past
   * the calendar). Given a night shaped like that one, the headline must not
   * say every report was reached, and must not claim the Reports Centre
   * allowance was spent -- neither ticked report uses that door. */
  const browser = installFakeChrome();
  await startTheNight(browser.chrome, {
    doing: ['fk_ads_overall', 'fk_ads_orders'], mayAskFor: 2, at: 1, openAt: FLIPKART_HOME, dataDate: '2026-09-18',
  });
  await thatOneIsDone(browser.chrome, {
    reportId: 'fk_ads_overall', state: 'landed', size: 373, at: 2, dataDate: '2026-09-18',
  });
  for (let day = 1; day <= 31; day += 1) {
    // eslint-disable-next-line no-await-in-loop
    await thatOneIsDone(browser.chrome, {
      reportId: 'fk_ads_overall', state: NOT_AVAILABLE_YET, say: 'campaigns not known.', at: 2,
      dataDate: `2026-01-${String(day).padStart(2, '0')}`,
    });
  }
  for (let day = 1; day <= 3; day += 1) {
    // eslint-disable-next-line no-await-in-loop
    await thatOneIsDone(browser.chrome, {
      reportId: 'fk_ads_orders', state: NEEDS_YOU_STATE, say: 'not on the calendar.', at: 2,
      dataDate: `2026-01-0${day}`,
    });
  }
  const words = howTheNightWent(await theNight(browser.chrome));
  check('a night shaped like the real 09-18 log never says every report was reached',
    !words.startsWith('Every report was reached')
    && !words.includes('0 of 2 reports were reached'));
  check('and it separates the day-not-built-yet reports from the ones needing him',
    words.includes('31 waiting on the platform (the day is not built yet)')
    && words.includes('3 need him'));
  check('and it does not credit either ticked ad report with spending the Reports Centre allowance',
    words.includes('0 of the 2 allowed Flipkart Reports Centre requests (fk_orders, fk_payments) were spent.'));
}

{
  /* **A REPORT THE ALLOWANCE REFUSES IS SKIPPED ONCE PER DAY OWED, AND THE RUN
   * STILL ENDS.** Every skip takes a day off; none of them walks anything. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await browser.chrome.storage.local.set({
    [NOT_BUILT_YET]: {
      'fk_orders|2026-09-12': { reportId: 'fk_orders', dataDate: '2026-09-12', triedOn: ['2026-09-13'] },
    },
  });
  await startTheNight(browser.chrome, {
    doing: ['fk_orders'], mayAskFor: 0, at: ON('2026-09-14'), openAt: FLIPKART_HOME, dataDate: '2026-09-13',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: ON('2026-09-14') });
  const night = await theNight(browser.chrome);
  check('a report that may not be asked for is skipped once per owed day, and the run ends',
    walk.started.length === 0 && night.done.length === 2 && Boolean(night.finishedAt));
  check('and a day skipped for the allowance is still owed, because it was never tried',
    Boolean((await whatIsNotBuiltYet(browser.chrome))['fk_orders|2026-09-12']));
}

{
  /* **A53: ASKED FOR FIRST, COLLECTED AT THE END OF THE SAME SYNC -- RUMEE'S WAY.** */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_orders', 'fk_ads_daily'], mayAskFor: 5, at: 1,
    openAt: 'https://seller.flipkart.com/index.html', dataDate: '2026-09-14',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  walk.itFinished({
    state: 'still-waiting', reportId: 'fk_orders', theirId: '2026-09-14', dataDate: '2026-09-14',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 3 });
  walk.itFinished({ state: 'landed', reportId: 'fk_ads_daily', size: 10 });
  await carryTheNightOn(browser.chrome, { ...walk, at: 4 });
  check('a report that was asked for is collected at the end of the same sync',
    walk.started.map((one) => one.reportId).join() === 'fk_orders,fk_ads_daily,fk_orders'
    && Boolean(walk.started[2].askedAlready));
  walk.itFinished({ state: 'failed', reportId: 'fk_orders', say: 'not generated yet' });
  await carryTheNightOn(browser.chrome, { ...walk, at: 5 });
  check('and only once: a collect that fails does not come round again in that sync',
    walk.started.length === 3 && Boolean((await theNight(browser.chrome)).finishedAt));
}

{
  /* **N037: ASKS ALL FIRST, DOWNLOADS NEXT, COLLECTS LAST -- FOR EVERY DAY OF A RANGE TOO (his 28 Oct 2026).** Two days, one report with a request step and one without: both days of the first are asked before the second report is touched, then the download-only, then the asked ones are collected, and none is asked twice. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  const days = ['2026-09-13', '2026-09-14'];
  await startTheNight(browser.chrome, {
    doing: ['az_orders', 'az_traffic'], mayAskFor: 0, at: 1, openAt: 'https://sellercentral.example.test/', dataDate: days[1], days,
  });
  const finish = async (answer, at) => { walk.itFinished(answer); await carryTheNightOn(browser.chrome, { ...walk, at }); };
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  for (let at = 3; at < 12 && walk.held; at += 1) {
    const now = walk.started.at(-1);
    // eslint-disable-next-line no-await-in-loop
    if (now.reportId === 'az_orders' && !now.askedAlready) await finish({ state: 'still-waiting', reportId: 'az_orders', theirId: now.dataDate, dataDate: now.dataDate }, at);
    // eslint-disable-next-line no-await-in-loop
    else await finish({ state: 'landed', reportId: now.reportId, size: 10, dataDate: now.dataDate }, at);
    if (!(await theNight(browser.chrome)) || (await theNight(browser.chrome)).finishedAt) break;
  }
  const order = walk.started.map((one) => `${one.reportId}${one.askedAlready ? '+collect' : ''}`).join();
  check('N037: every ask of every day comes first, then the download-only report, then the collects, and none is asked twice',
    order === 'az_orders,az_orders,az_traffic,az_traffic,az_orders+collect,az_orders+collect');
}

{
  /* **A53: A COLLECT NOT READY IS CHECKED AGAIN EVERY HOUR, THREE TIMES, THEN "NOT
   * READY TODAY" FOR THE NEXT SYNC -- RUMEE'S WAY.** */
  const browser = installFakeChrome();
  const c = browser.chrome;
  const day = '2026-09-14';
  await startTheNight(c, { doing: ['fk_orders'], mayAskFor: 5, at: 1, openAt: 'https://x/', dataDate: day });
  await thatOneIsDone(c, { reportId: 'fk_orders', state: 'still-waiting', theirId: day, dataDate: day, at: 2 });
  const first = await thatOneIsDone(c, {
    reportId: 'fk_orders', state: 'failed', say: 'Download not offered.', dataDate: day, at: 3,
  });
  check('a collect that is not ready is checked again in an hour rather than failed',
    first.done.at(-1).state === 'still-waiting' && first.done.at(-1).say.includes('(1 of 3)'));
  check('and the hourly check is put on the clock',
    (await setTheRecheckClock(c)) === true && Boolean(await c.alarms.get(RECHECK_ALARM)));
  check('and that check is a sync of the report for its own day',
    JSON.stringify(theRecheckSync(await whatIsBeingRechecked(c)))
      === JSON.stringify({ day, reportIds: ['fk_orders'] }));
  for (const at of [4, 5]) {
    // eslint-disable-next-line no-await-in-loop
    await thatOneIsDone(c, { reportId: 'fk_orders', state: 'failed', say: 'x', dataDate: day, at });
  }
  const last = await thatOneIsDone(c, {
    reportId: 'fk_orders', state: 'failed', say: 'Download not offered.', dataDate: day, at: 6,
  });
  check('after three hourly checks it is not ready today, and owed to the next sync',
    last.done.at(-1).state === NOT_AVAILABLE_YET
    && Object.keys(await whatIsBeingRechecked(c)).length === 0
    && Object.values(await whatIsNotBuiltYet(c))
      .some((one) => one.reportId === 'fk_orders' && one.dataDate === day));
}

{
  /* **JOB 3B, 2026-09-22: A REPORT WITH NO ASKING PHASE NEVER GETS THIS SAFETY
   * NET, THOUGH IT NEEDS IT JUST AS MUCH.** `me_views` has only a `to_take`
   * step -- there is nothing to ask Meesho for, only a live dashboard to read --
   * so it never appears in `WHAT_IS_BEING_BUILT`, and the recheck above asks
   * for exactly that before it tries again. **Measured live, 2026-09-22:**
   * `me_views` failed once ("the views card for the day... not on the page at
   * all") and landed on the very next try with nothing else changed -- the
   * dashboard had simply not finished drawing. Without this, a report shaped
   * like `me_views` gets one look and is written off, while every two-phase
   * report gets three. */
  const browser = installFakeChrome();
  const c = browser.chrome;
  const day = '2026-09-21';
  await startTheNight(c, { doing: ['me_views'], at: 1, openAt: 'https://x/', dataDate: day });
  const first = await thatOneIsDone(c, {
    reportId: 'me_views', state: 'failed', say: 'the views card for the day... not on the page at all.',
    dataDate: day, at: 2,
  });
  check('a report with no asking phase is checked again in an hour too',
    first.done.at(-1).state === 'still-waiting' && first.done.at(-1).say.includes('(1 of 3)'));
}

{
  /* **THE AMAZON ADS REPORT IS ONE PHASE NOW (the ads site is visited once in a run, 27 Oct 2026), SO IT HAS NO ASK TO MAKE IT CHECKED AGAIN -- AND IT STILL NEEDS THE HOURLY LOOK** (the fresh review): a run that is slow to
   * finish must not be written off for the day on one look. */
  const browser = installFakeChrome();
  const c = browser.chrome;
  const day = '2026-10-26';
  await startTheNight(c, { doing: ['az_ads'], at: 1, openAt: 'https://x/', dataDate: day });
  const first = await thatOneIsDone(c, {
    reportId: 'az_ads', state: 'failed', say: 'waiting for the saved report row to show today.', dataDate: day, at: 2,
  });
  check('the Amazon ads report is checked again in an hour when it fails, though it has no asking phase',
    first.done.at(-1).state === 'still-waiting' && first.done.at(-1).say.includes('(1 of 3)'));
}

{
  /* **AJ9 PIECE 2: THE RUN LOG SAYS WHETHER THE 3-MINUTE WAIT WAS KEPT.** */
  const waited = installFakeChrome();
  const at = 5_000_000_000_000;
  await waited.chrome.storage.local.set({ [STARTED_AFTER_IDLE]: { kind: 'daily', waitedMs: 7 * 60000, at: at - 1000 } });
  const night = await startTheNight(waited.chrome, { doing: ['fk_views'], at, openAt: 'https://x/', dataDate: '2026-10-29' });
  check('a night started after waiting carries how long it waited, and the note is spent',
    night.idle.waitedMs === 7 * 60000 && !(await waited.chrome.storage.local.get(STARTED_AFTER_IDLE))[STARTED_AFTER_IDLE]);
  check('the run log says it waited 7 min and started after 3 min idle',
    theRunLog({ ...night, finishedAt: at + 1 }).text.includes('Idle wait: waited 7 min for the computer to be free, then started after 3 min idle.'));
  /* the real flow: the idle wait lets the run start, and the night it starts carries the note */
  const flow = installFakeChrome();
  flow.setTheComputer('idle');
  let flowNight = null;
  await startWhenFree(flow.chrome, 'daily', async () => {
    flowNight = await startTheNight(flow.chrome, { doing: ['fk_views'], at: Date.now(), openAt: 'https://x/', dataDate: '2026-10-29' });
  });
  check('through the real wait, the night started carries the idle note and the note is gone after',
    flowNight.idle && flowNight.idle.kind === 'daily' && !(await flow.chrome.storage.local.get(STARTED_AFTER_IDLE))[STARTED_AFTER_IDLE]);
  const stale = installFakeChrome();
  await stale.chrome.storage.local.set({ [STARTED_AFTER_IDLE]: { kind: 'daily', waitedMs: 0, at: at - 3 * 3600000 } });
  const byHand = await startTheNight(stale.chrome, { doing: ['fk_views'], at, openAt: 'https://x/', dataDate: '2026-10-29' });
  check('a note from hours ago is not mistaken for this start, and the log says it did not go through the wait',
    byHand.idle === undefined && theRunLog({ ...byHand, finishedAt: at + 1 }).text.includes('did not go through the 3-minute wait'));
  const free = installFakeChrome();
  await free.chrome.storage.local.set({ [STARTED_AFTER_IDLE]: { kind: 'daily', waitedMs: 0, at } });
  const now = await startTheNight(free.chrome, { doing: ['fk_views'], at, openAt: 'https://x/', dataDate: '2026-10-29' });
  check('a start that never had to wait says the computer was already free',
    theRunLog({ ...now, finishedAt: at + 1 }).text.includes('already free when the run was due'));
}

{
  /* **AJ9 PIECE 1 (30 Oct 01:26 UTC): A TAB CLOSED MID-WALK IS CHECKED AGAIN IN AN HOUR, FOR ANY REPORT.** fk_listings
   * and fk_ads_search failed on "the tab was closed" with no asking phase and were not in the list above, so they were
   * lost until the next sync. Another failure for the same report is still just a failure. */
  const browser = installFakeChrome();
  const c = browser.chrome;
  const day = '2026-10-29';
  await startTheNight(c, { doing: ['fk_listings', 'fk_ads_search'], at: 1, openAt: 'https://x/', dataDate: day });
  const closed = await thatOneIsDone(c, {
    reportId: 'fk_listings', state: 'failed', dataDate: day, at: 2,
    say: `${TAB_CLOSED_SAY} The computer was being used at that moment, so it was most likely closed by hand.`,
  });
  check('a report whose tab was closed is checked again in an hour, not lost',
    closed.done.at(-1).state === 'still-waiting' && closed.done.at(-1).say.includes('(1 of 3)')
    && closed.done.at(-1).say.includes('closed by hand'));
  const other = await thatOneIsDone(c, {
    reportId: 'fk_ads_search', state: 'failed', dataDate: day, at: 3, say: 'Failed to fetch.',
  });
  check('any other failure of such a report is not swept into the hourly check',
    other.done.at(-1).state === 'failed');
  check('the closed-tab line says it once, and does not call a closed tab "not ready"',
    (closed.done.at(-1).say.match(/checked again in an hour/g) || []).length === 1
    && !closed.done.at(-1).say.includes('Not ready'));

  /* Review finding 1: a request that spends Flipkart's twenty is never pressed again by a recheck of a closed tab. */
  const spend = installFakeChrome();
  await startTheNight(spend.chrome, { doing: ['fk_orders'], at: 1, openAt: 'https://x/', dataDate: day });
  const orders = await thatOneIsDone(spend.chrome, {
    reportId: 'fk_orders', state: 'failed', dataDate: day, at: 2, say: `${TAB_CLOSED_SAY} x`,
  });
  check('a closed tab on a report that spends the twenty, with nothing asked yet, is not rechecked',
    orders.done.at(-1).state === 'failed' && Object.keys(await whatIsBeingRechecked(spend.chrome)).length === 0);

  /* Review findings 2 and 3: tabs closed every time stay a plain failure, never "the platform has not built it". */
  const again = installFakeChrome();
  await startTheNight(again.chrome, {
    doing: ['fk_listings'], at: 1, openAt: 'https://x/', dataDate: day, canGoBack: ['fk_listings'],
  });
  let last = null;
  for (const at of [2, 3, 4, 5]) {
    // eslint-disable-next-line no-await-in-loop
    last = await thatOneIsDone(again.chrome, {
      reportId: 'fk_listings', state: 'failed', dataDate: day, at, say: `${TAB_CLOSED_SAY} x`,
    });
  }
  check('after the third recheck a closed tab is a plain failure, not "not available yet"',
    last.done.at(-1).state === 'failed' && last.done.at(-1).say.includes('tab was closed each time')
    && Object.keys(await whatIsBeingRechecked(again.chrome)).length === 0);
}

{
  /* **MEESHO'S OWN "SOMETHING WENT WRONG" AND AN ORDERS PAGE IN ANOTHER STATE ARE CHECKED AGAIN IN AN HOUR (his live runs of 27 Oct 2026):** returns failed on Meesho's own error twice running, and orders failed once when an
   * order had just been accepted and the page showed "No orders yet" with no date control; the same reports landed on the runs either side. Neither is the platform saying the day is not there. */
  for (const reportId of ['me_returns']) {
    const browser = installFakeChrome();
    const c = browser.chrome;
    const day = '2026-10-26';
    await startTheNight(c, { doing: [reportId], at: 1, openAt: 'https://x/', dataDate: day });
    const first = await thatOneIsDone(c, {
      reportId, state: 'failed', say: 'could not find the control the page was in another state.', dataDate: day, at: 2,
    });
    check(`${reportId} is checked again in an hour when it fails, though it has no asking phase`,
      first.done.at(-1).state === 'still-waiting' && first.done.at(-1).say.includes('(1 of 3)'));
  }
}

{
  /* **A53: A FAILED DAY OF A REPORT THAT CAN GO BACK IS TRIED AGAIN ON LATER SYNCS --
   * RUMEE'S gap-catchup, EVERY OWED DAY RATHER THAN ONE.** */
  const browser = installFakeChrome();
  const c = browser.chrome;
  const day = '2026-09-14';
  const oneDay = 24 * 60 * 60 * 1000;
  const start = Date.UTC(2026, 8, 15, 3);
  await startTheNight(c, {
    doing: ['me_orders', 'me_returns'], at: start, openAt: 'https://x/', dataDate: day,
    canGoBack: ['me_orders'],
  });
  const first = await thatOneIsDone(c, {
    reportId: 'me_orders', state: 'failed', say: 'Download not found.', dataDate: day, at: start,
  });
  check('a failed day of a report that can go back is owed to the next sync',
    Object.values(await whatIsNotBuiltYet(c)).some((one) => one.reportId === 'me_orders' && one.dataDate === day)
    && first.done.at(-1).say.includes('tried again on the next sync'));
  await thatOneIsDone(c, { reportId: 'me_returns', state: 'failed', say: 'x', dataDate: day, at: start });
  check('while a report the platform cannot give for a past day is not owed',
    !Object.values(await whatIsNotBuiltYet(c)).some((one) => one.reportId === 'me_returns'));
  for (const n of [1, 2]) {
    // eslint-disable-next-line no-await-in-loop
    await thatOneIsDone(c, { reportId: 'me_orders', state: 'failed', say: 'x', dataDate: day, at: start + n * oneDay });
  }
  check('and a day that failed on three different days needs the seller',
    (await whatNeedsYou(c)).some((one) => one.reportId === 'me_orders' && one.dataDate === day));
}

{
  /* **A REQUEST KNOWN TO HAVE GONE IS NEVER HANDED BACK LATER (review finding, 2026-10-05).** */
  const browser = installFakeChrome();
  const c = browser.chrome;
  await startTheNight(c, { doing: ['fk_orders'], mayAskFor: 5, at: Date.UTC(2026, 8, 21, 3), openAt: 'https://x/', dataDate: '2026-09-20' });
  await oneWasAskedFor(c, { counting: 'fk_orders|2026-09-20', at: Date.UTC(2026, 8, 21, 3) });
  check('the request just counted is remembered as the last one, so it can be given back if the day is refused',
    (await theNight(c)).lastCounted.key === 'fk_orders|2026-09-20');
  await thatOneIsDone(c, { reportId: 'fk_orders', state: 'landed', size: 5, dataDate: '2026-09-20', at: Date.UTC(2026, 8, 21, 3) });
  check('but once the report landed the count is settled: it can no longer be handed back by a later failure',
    (await theNight(c)).lastCounted === null && (await theNight(c)).spent === 1);
}

{
  /* **A SIGN-IN WALL IS NOT "THE PLATFORM NEVER BUILT THAT DAY" (review finding, 2026-10-05).** Three
   * syncs on three different days with the seller signed out used to put a day nobody ever reached into
   * "needs you ... will not be tried again" and drop it for good. */
  const browser = installFakeChrome();
  const c = browser.chrome;
  const day = '2026-09-20';
  const oneDay = 24 * 60 * 60 * 1000;
  const start = Date.UTC(2026, 8, 21, 3);
  await startTheNight(c, {
    doing: ['me_orders'], at: start, openAt: 'https://x/', dataDate: day, canGoBack: ['me_orders'],
  });
  for (const n of [0, 1, 2, 3]) {
    // eslint-disable-next-line no-await-in-loop
    await thatOneIsDone(c, {
      reportId: 'me_orders', state: 'failed', say: 'sign in', dataDate: day, at: start + n * oneDay,
      needsSigningIn: true,
    });
  }
  check('four signed-out syncs on four days never put the day in needs-you',
    (await whatNeedsYou(c)).length === 0);
  check('and nothing is remembered as tried, so it is still fetched when they are signed in again',
    Object.keys(await whatIsNotBuiltYet(c)).length === 0);
  check('and the failure is still written in the night itself, so it is not hidden',
    (await theNight(c)).done.filter((one) => one.state === 'failed').length === 4);
  const hourly = await whatIsBeingRechecked(c);
  check('and the hourly recheck is not used up by it', Object.keys(hourly).length === 0);
  /* The control: the very same failures WITHOUT a sign-in wall still count, as they always did. */
  await thatOneIsDone(c, { reportId: 'me_orders', state: 'failed', say: 'x', dataDate: day, at: start });
  check('a failure that is not a sign-in wall is still remembered as tried',
    Object.keys(await whatIsNotBuiltYet(c)).length === 1);
}

{
  /* **A53: FLIPKART TRAFFIC IS ASKED FROM THE DAY AFTER THE LAST ONE CAPTURED --
   * RUMEE'S WAY.** */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await rememberLastCaptured(browser.chrome, 'fk_views', '2026-09-10');
  check('the last day captured never moves backwards',
    (await rememberLastCaptured(browser.chrome, 'fk_views', '2026-09-08')) === '2026-09-10');
  await startTheNight(browser.chrome, {
    doing: ['fk_views'], at: 1, openAt: 'https://x/', dataDate: '2026-09-14',
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  check('Flipkart traffic is asked from the day after the last one captured',
    walk.started[0].fromDay === '2026-09-11');
  check('while any other report is asked for its own day alone',
    (await theDayAfterTheLastCaptured(browser.chrome, 'fk_ads_daily', '2026-09-14')) === '');
}

{
  /* **A53: A SYNC ASKED FOR A STRETCH OF DAYS WALKS EACH REPORT THROUGH ALL OF THEM,
   * OLDEST FIRST** -- the panel's two date boxes. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['me_returns'], at: 1, openAt: 'https://x/', dataDate: '2026-09-14',
    days: ['2026-09-12', '2026-09-13', '2026-09-14'],
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  walk.itFinished({ state: 'landed', reportId: 'me_returns', size: 10, dataDate: '2026-09-12' });
  await carryTheNightOn(browser.chrome, { ...walk, at: 3 });
  check('a sync asked for several days walks the oldest first, then the next',
    walk.started.map((one) => one.dataDate).join() === '2026-09-12,2026-09-13');
}

{
  /* **P16 (D424): A TYPED RANGE FOR A REPORT THAT SPENDS THE TWENTY IS ONE REQUEST.** Three days of
   * `fk_orders` used to be three walks and three of Flipkart's twenty. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_orders'], mayAskFor: 20, at: 1, openAt: 'https://x/', dataDate: '2026-09-14',
    days: ['2026-09-12', '2026-09-13', '2026-09-14'],
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  check('fk_orders over three days is walked ONCE, for the last day, from the first',
    walk.started.length === 1 && walk.started[0].dataDate === '2026-09-14'
    && walk.started[0].fromDay === '2026-09-12' && walk.started[0].namedAsARange === true);
  check('and it counts ONE of the twenty, not three', (await theNight(browser.chrome)).spent === 1);
  walk.itFinished({ state: 'landed', reportId: 'fk_orders', size: 10, dataDate: '2026-09-14' });
  await carryTheNightOn(browser.chrome, { ...walk, at: 3 });
  check('and once it has landed there is no second walk for the days inside it',
    walk.started.length === 1 && (await theNight(browser.chrome)).spent === 1);
}

{
  /* **A REPORT THAT COSTS NOTHING PER REQUEST STAYS A DAY AT A TIME**, and so does a stretch with a gap
   * in it or one longer than a file's name may hold. */
  check('a run of days is one range from the first to the last',
    JSON.stringify(theRangeOfTheDays(['2026-09-14', '2026-09-12', '2026-09-13']))
    === JSON.stringify({ from: '2026-09-12', to: '2026-09-14' }));
  check('across a month end too',
    JSON.stringify(theRangeOfTheDays(['2026-09-30', '2026-10-01'])) === JSON.stringify({ from: '2026-09-30', to: '2026-10-01' }));
  check('one day is not a range, and nor is nothing',
    theRangeOfTheDays(['2026-09-14']) === null && theRangeOfTheDays([]) === null && theRangeOfTheDays(undefined) === null);
  check('days with a gap are not one range', theRangeOfTheDays(['2026-09-12', '2026-09-14']) === null);
  const days = (n) => Array.from({ length: n }, (_, at) => new Date(Date.UTC(2026, 7, 1 + at)).toISOString().slice(0, 10));
  check('31 days are a range and 32 are not', theRangeOfTheDays(days(31)) !== null && theRangeOfTheDays(days(32)) === null);
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_orders'], mayAskFor: 20, at: 1, openAt: 'https://x/', dataDate: '2026-09-14',
    days: ['2026-09-12', '2026-09-14'],
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  check('a gap in the typed days is walked a day at a time as ever, with no range name',
    walk.started[0].dataDate === '2026-09-12' && !walk.started[0].namedAsARange);
  const meesho = installFakeChrome();
  const meeshoWalk = aWalkThat();
  await startTheNight(meesho.chrome, {
    doing: ['me_returns'], at: 1, openAt: 'https://x/', dataDate: '2026-09-14',
    days: ['2026-09-12', '2026-09-13', '2026-09-14'],
  });
  await carryTheNightOn(meesho.chrome, { ...meeshoWalk, at: 2 });
  check('a Meesho report over three days is still walked the oldest day first and not as a range',
    meeshoWalk.started[0].dataDate === '2026-09-12' && !meeshoWalk.started[0].namedAsARange);
}

{
  /* **A RANGE REQUEST THAT IS NOT READY IS RE-CHECKED AS THE SAME RANGE (P16, review finding).** The row Flipkart finishes holds every day,
   * so collected as one day it would be named for one day and the rest asked for again. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await startTheNight(browser.chrome, {
    doing: ['fk_orders'], mayAskFor: 20, at: 1, openAt: 'https://x/', dataDate: '2026-09-14',
    days: ['2026-09-12', '2026-09-13', '2026-09-14'],
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  walk.itFinished({ state: 'failed', reportId: 'fk_orders', size: 0, dataDate: '2026-09-14', say: 'not ready' });
  await thatOneIsDone(browser.chrome, { reportId: 'fk_orders', state: 'still-waiting', say: 'asked', at: 3, dataDate: '2026-09-14', theirId: 'req-1' });
  await thatOneIsDone(browser.chrome, { reportId: 'fk_orders', state: 'failed', say: 'not ready', at: 4, dataDate: '2026-09-14' });
  const waiting = Object.values(await whatIsBeingRechecked(browser.chrome));
  check('the re-check entry remembers the first day of the range',
    waiting.length === 1 && waiting[0].dataDate === '2026-09-14' && waiting[0].fromDay === '2026-09-12');
  const plan = theRecheckSync(await whatIsBeingRechecked(browser.chrome));
  check('and the hourly re-check is a sync of that range, not of one day', plan.from === '2026-09-12' && plan.day === '2026-09-14');
  const grouped = theRecheckSync({
    a: { reportId: 'fk_orders', dataDate: '2026-09-14', fromDay: '2026-09-12' },
    b: { reportId: 'fk_claims', dataDate: '2026-09-14' },
  });
  check('a report asked for a single day is not swept into the range re-check',
    grouped.reportIds.length === 1 && grouped.from === '2026-09-12');
  check('and an ordinary re-check has no range at all',
    theRecheckSync({ a: { reportId: 'fk_claims', dataDate: '2026-09-14' } }).from === undefined);
}

{
  /* **JOB 9 (AP7): MEESHO ORDERS AND PAYMENTS ASK A TYPED RANGE IN ONE REQUEST TOO.** They spend none of
   * Flipkart's twenty, so the range is kept apart from the allowance list: three owed days are ONE walk
   * carrying the range's first day, and nothing is counted against the twenty. */
  for (const report of ['me_orders']) {
    const browser = installFakeChrome();
    const walk = aWalkThat();
    await startTheNight(browser.chrome, {
      doing: [report], mayAskFor: 0, at: 1, openAt: 'https://x/', dataDate: '2026-10-20', panel: 'p',
      days: ['2026-10-18', '2026-10-19', '2026-10-20'],
    });
    await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
    check(`${report} over three days is walked ONCE, for the last day, from the first, named as a range`,
      walk.started.length === 1 && walk.started[0].dataDate === '2026-10-20'
      && walk.started[0].fromDay === '2026-10-18' && walk.started[0].namedAsARange === true);
    check(`and ${report} spends nothing of the twenty`, (await theNight(browser.chrome)).spent === 0);
    walk.itFinished({ state: 'landed', reportId: report, size: 10, dataDate: '2026-10-20' });
    await carryTheNightOn(browser.chrome, { ...walk, at: 3 });
    check(`and once it has landed ${report} has no second walk for the days inside it`,
      walk.started.length === 1);
  }
  /* me_payments is NOT ranged: Meesho ignores the days, so a range name would claim days the file lacks. */
  const pay = installFakeChrome();
  const payWalk = aWalkThat();
  await startTheNight(pay.chrome, {
    doing: ['me_payments'], at: 1, openAt: 'https://x/', dataDate: '2026-10-20', panel: 'p',
    days: ['2026-10-18', '2026-10-19', '2026-10-20'],
  });
  await carryTheNightOn(pay.chrome, { ...payWalk, at: 2 });
  check('me_payments over three days is still walked a day at a time, never named as a range',
    payWalk.started[0].dataDate === '2026-10-18' && !payWalk.started[0].namedAsARange);
  const gap = installFakeChrome();
  const gapWalk = aWalkThat();
  await startTheNight(gap.chrome, {
    doing: ['me_orders'], at: 1, openAt: 'https://x/', dataDate: '2026-10-20', panel: 'p',
    days: ['2026-10-18', '2026-10-20'],
  });
  await carryTheNightOn(gap.chrome, { ...gapWalk, at: 2 });
  check('a Meesho run whose days have a gap is still walked a day at a time',
    gapWalk.started.length === 1 && gapWalk.started[0].dataDate === '2026-10-18' && !gapWalk.started[0].namedAsARange);
}

{
  /* **DAYS OWED INSIDE THE RANGE ARE COVERED BY IT; DAYS OWED OUTSIDE ARE STILL WALKED.** */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await rememberLastLanded(browser.chrome, 'fk_orders', '2026-09-05');
  await rememberLastLanded(browser.chrome, 'fk_orders', '2026-09-10');
  await startTheNight(browser.chrome, {
    doing: ['fk_orders'], mayAskFor: 20, at: 1, openAt: 'https://x/', dataDate: '2026-09-14',
    days: ['2026-09-12', '2026-09-13', '2026-09-14'], canGoBack: ['fk_orders'],
  });
  const walked = [];
  for (let turn = 2; turn < 14; turn += 1) {
    // eslint-disable-next-line no-await-in-loop
    await carryTheNightOn(browser.chrome, { ...walk, at: turn });
    if (walk.started.length === walked.length) break;
    walked.push(walk.started[walked.length]);
    walk.itFinished({ state: 'landed', reportId: 'fk_orders', size: 10, dataDate: walked[walked.length - 1].dataDate });
  }
  check('the range is walked first, then each owed day outside it, and none inside it',
    walked.map((one) => one.dataDate).join() === '2026-09-14,2026-09-06,2026-09-07,2026-09-08,2026-09-09,2026-09-11');
  check('and only the range walk carries the range',
    walked[0].namedAsARange === true && walked[0].fromDay === '2026-09-12'
    && walked.slice(1).every((one) => !one.namedAsARange && !one.fromDay));
}

{
  /* **A53, HIS RULING 2026-09-16: *"when run is for past day it will ignore meesho
   * views as it is not available"*.** Meesho's dashboard card shows its newest day
   * and nothing else, so a sync for an older day was looking for a card that can
   * never be drawn -- and the failure blamed whatever happened to be covering the
   * page. Left out by name, with the reason in words, so the run log says why. */
  const browser = installFakeChrome();
  const c = browser.chrome;
  const walk = aWalkThat();
  await startTheNight(c, {
    doing: ['me_views', 'me_orders'], at: 1, openAt: 'https://x/', dataDate: '2026-09-06',
    days: ['2026-09-06'], latestDay: '2026-09-15', canGoBack: ['me_orders'],
  });
  await carryTheNightOn(c, { ...walk, at: 2 });
  const told = (await theNight(c)).done.find((one) => one.reportId === 'me_views');
  check('A REPORT THAT ONLY EXISTS FOR NOW IS LEFT OUT OF A PAST DAY, BY NAME',
    Boolean(told) && told.state === 'nothing-to-fetch' && told.say.includes('not available'));
  check('and no page was ever opened for it',
    !walk.started.some((one) => one.reportId === 'me_views'));
  check('while a report that can go back is still walked for that day',
    walk.started.some((one) => one.reportId === 'me_orders' && one.dataDate === '2026-09-06'));

  const ordinary = installFakeChrome();
  const asUsual = aWalkThat();
  await startTheNight(ordinary.chrome, {
    doing: ['me_views'], at: 1, openAt: 'https://x/', dataDate: '2026-09-15', latestDay: '2026-09-15',
  });
  await carryTheNightOn(ordinary.chrome, { ...asUsual, at: 2 });
  check('and an ordinary sync fetches it exactly as before',
    asUsual.started.some((one) => one.reportId === 'me_views'));
}

{
  /* **A57, JOB 2: A DAY WHOSE CAMPAIGN LIST WAS NEVER FETCHED IS NOT HIS TO DO.** The
   * runs of 09-18..09-21 handed `fk_ads_overall` days to him as "needs you" when
   * nothing had ever fetched `fk_ads_daily` for them. Four runs on four days. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  for (const runDay of ['2026-09-18', '2026-09-19', '2026-09-20', '2026-09-21']) {
    // eslint-disable-next-line no-await-in-loop
    await startTheNight(browser.chrome, {
      doing: ['fk_ads_overall'], at: ON(runDay), openAt: FLIPKART_HOME, dataDate: '2026-09-17',
    });
    // eslint-disable-next-line no-await-in-loop
    await carryTheNightOn(browser.chrome, { ...walk, at: ON(runDay) });
    walk.itFinished({
      state: NOT_AVAILABLE_YET, reportId: 'fk_ads_overall', dataDate: '2026-09-17',
      say: 'Which ad campaigns ran on 2026-09-17 is not known yet.', listMissing: true,
    });
    // eslint-disable-next-line no-await-in-loop
    await carryTheNightOn(browser.chrome, { ...walk, at: ON(runDay) });
  }
  check('A DAY WHOSE CAMPAIGN LIST WAS NEVER FETCHED IS NOT ESCALATED TO "NEEDS YOU"',
    !(await whatNeedsYou(browser.chrome)).some((one) => one.reportId === 'fk_ads_overall'));
  const owed = (await whatIsNotBuiltYet(browser.chrome))['fk_ads_overall|2026-09-17'];
  check('and it stays owed with no day of trying used up, so the next sync fetches it',
    Boolean(owed) && owed.triedOn.length === 0);
}

{
  /* **A57, JOB 2: AND THE LIST IS FETCHED FOR EVERY DAY THE CAMPAIGN REPORT WALKS.**
   * `fk_ads_overall` owes 09-19; the sync is for 09-20. `fk_ads_daily` walks 09-19
   * too, first, so the owed day finally has its list. */
  const browser = installFakeChrome();
  const walk = aWalkThat();
  await browser.chrome.storage.local.set({
    [NOT_BUILT_YET]: {
      'fk_ads_overall|2026-09-19': { reportId: 'fk_ads_overall', dataDate: '2026-09-19', triedOn: [] },
    },
  });
  await startTheNight(browser.chrome, {
    doing: ['fk_ads_daily', 'fk_ads_overall'], at: ON('2026-09-21'), openAt: FLIPKART_HOME,
    dataDate: '2026-09-20', listFrom: { fk_ads_overall: 'fk_ads_daily' },
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: ON('2026-09-21') });
  check('THE CAMPAIGN LIST IS FETCHED FIRST FOR A DAY THE CAMPAIGN REPORT STILL OWES',
    walk.started[0].reportId === 'fk_ads_daily' && walk.started[0].dataDate === '2026-09-19');
}

/** Every day from `from` to `to`, both included, as `YYYY-MM-DD`. Test-only. */
function daysBetweenForTest(from, to) {
  const out = [];
  const cursor = new Date(`${from}T00:00:00Z`);
  const end = new Date(`${to}T00:00:00Z`);
  while (cursor <= end) {
    out.push(cursor.toISOString().slice(0, 10));
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return out;
}

async function seedLandedRangeForTest(c, reportId, from, to) {
  for (const d of daysBetweenForTest(from, to)) {
    // eslint-disable-next-line no-await-in-loop
    await rememberLastLanded(c, reportId, d);
  }
}

{
  /* **JOB 6: A DAY NOBODY EVER TRIED IS NOWHERE IN `NOT_BUILT_YET` AT ALL,
   * SO NOTHING ABOVE THIS LINE EVER FOUND IT.** F14: Meesho orders for
   * 09-17..09-19 went missing because the timed list held nothing that would
   * have asked for `me_orders` on those days -- not a refusal, not an
   * attempt, nothing written down anywhere. */
  const browser = installFakeChrome();
  const c = browser.chrome;
  check('every landed day is remembered as a set, not only the newest',
    JSON.stringify(await rememberLastLanded(c, 'me_orders', '2026-09-16')) === JSON.stringify(['2026-09-16'])
    && JSON.stringify(await rememberLastLanded(c, 'me_orders', '2026-09-10'))
      === JSON.stringify(['2026-09-10', '2026-09-16'])
    && JSON.stringify(await rememberLastLanded(c, 'me_orders', '2026-09-16'))
      === JSON.stringify(['2026-09-10', '2026-09-16']));
  check('nothing is owed for a report that has never landed a single file yet',
    (await daysNobodyTried(c, 'me_payments', '2026-09-20')).length === 0);
  await seedLandedRangeForTest(c, 'me_orders', '2026-09-06', '2026-09-16');
  check('the gap inside the reach window is owed, oldest first',
    (await daysNobodyTried(c, 'me_orders', '2026-09-20')).join()
      === '2026-09-17,2026-09-18,2026-09-19');
}

{
  /* **NOTHING IS OWED BEFORE THE FIRST DAY A REPORT EVER LANDED (review finding, 2026-10-05).** The reach used to
   * run back 14 days from the sync's day whatever the report's history, so a report first landed on 09-10 was
   * walked for 09-06..09-09 -- days nobody ever asked for. */
  const browser = installFakeChrome();
  const c = browser.chrome;
  await rememberLastLanded(c, 'me_orders', '2026-09-10');
  const owed = await daysNobodyTried(c, 'me_orders', '2026-09-20');
  check('a report first landed on 09-10 owes nothing before 09-10, and every day after it up to its own day',
    owed.join() === '2026-09-11,2026-09-12,2026-09-13,2026-09-14,2026-09-15,2026-09-16,2026-09-17,2026-09-18,2026-09-19');
}

{
  /* **A DAY THE WALK FOUND NOTHING TO FETCH FOR IS SETTLED (review finding, 2026-10-05).** */
  const browser = installFakeChrome();
  const c = browser.chrome;
  await rememberLastLanded(c, 'fk_ads_daily', '2026-09-10');
  await startTheNight(c, {
    doing: ['fk_ads_daily'], at: Date.UTC(2026, 8, 21, 3), openAt: 'https://x/', dataDate: '2026-09-15',
    canGoBack: ['fk_ads_daily'],
  });
  const before = await daysNobodyTried(c, 'fk_ads_daily', '2026-09-20');
  await thatOneIsDone(c, {
    reportId: 'fk_ads_daily', state: 'nothing-to-fetch', say: 'no campaign ran', dataDate: '2026-09-15',
    at: Date.UTC(2026, 8, 21, 3), settled: true,
  });
  const after = await daysNobodyTried(c, 'fk_ads_daily', '2026-09-20');
  check('a day with nothing to fetch is not walked again on the next sync',
    before.includes('2026-09-15') && !after.includes('2026-09-15') && after.length === before.length - 1);
  await thatOneIsDone(c, {
    reportId: 'fk_ads_daily', state: NOT_ASKED, say: 'only asked for what is left of the twenty',
    dataDate: '2026-09-16', at: Date.UTC(2026, 8, 21, 3),
  });
  check('but one skipped for any other reason (the allowance, the newest-day rule) is still owed',
    (await daysNobodyTried(c, 'fk_ads_daily', '2026-09-20')).includes('2026-09-16'));
}

{
  /* **JOB 6, THE ACTUAL SHAPE OF F14: A HOLE BEHIND A LATER LANDED DAY.** His
   * real Drive has `me_orders` landed 09-16, missing 09-17..09-19, landed
   * again 09-20 (a later sync caught up on ITS OWN day, past the hole). A
   * record of only the newest day landed would already read 09-20 and could
   * never look backward through it -- this is why the whole set is kept, not
   * a single high-water mark. */
  const browser = installFakeChrome();
  const c = browser.chrome;
  await seedLandedRangeForTest(c, 'me_orders', '2026-09-06', '2026-09-16');
  await rememberLastLanded(c, 'me_orders', '2026-09-20');
  check('a hole is found even with a later day already landed past it',
    (await daysNobodyTried(c, 'me_orders', '2026-09-21')).join()
      === '2026-09-17,2026-09-18,2026-09-19');
}

{
  /* **JOB 6: A DAY ALREADY KNOWN -- TRIED AND REFUSED, OR ALREADY HANDED TO
   * HIM -- IS NOT REDISCOVERED AS A FRESH GAP.** Re-adding a day already in
   * `NEEDS_YOU` would silently undo the escalation he was told about. */
  const browser = installFakeChrome();
  const c = browser.chrome;
  await seedLandedRangeForTest(c, 'me_orders', '2026-09-06', '2026-09-16');
  await c.storage.local.set({
    [NOT_BUILT_YET]: {
      'me_orders|2026-09-17': { reportId: 'me_orders', dataDate: '2026-09-17', triedOn: ['2026-09-18'] },
    },
    [NEEDS_YOU]: [{ reportId: 'me_orders', dataDate: '2026-09-18', triedOn: ['x', 'y', 'z'], since: 'x', say: 'x' }],
  });
  check('a day already tried and refused, or already handed to him, is not counted twice',
    (await daysNobodyTried(c, 'me_orders', '2026-09-20')).join() === '2026-09-19');
}

{
  /* **JOB 7: A NAMED "NEEDS YOU" ENTRY IS CLEARED BY HAND, AND ONLY THE ONE
   * NAMED -- never a wildcard.** This is his record; the stale January entries
   * and fk_ads_overall's 09-17/09-18 will never clear themselves the ordinary
   * way, because Flipkart's own calendar will never let a later sync land
   * them. Proves both a single-day match and a whole-month match, and proves
   * an entry that merely LOOKS similar -- same report, a neighbouring day; same
   * day, a different report -- is left exactly alone. */
  const browser = installFakeChrome();
  const c = browser.chrome;
  const entry = (reportId, dataDate) => (
    { reportId, dataDate, triedOn: ['x', 'y', 'z'], since: 'x', say: 'x' });
  await c.storage.local.set({
    [NEEDS_YOU]: [
      entry('fk_ads_orders', '2026-01-05'),
      entry('fk_ads_orders', '2026-01-31'),
      entry('fk_ads_orders', '2025-12-31'),
      entry('fk_ads_orders', '2026-02-01'),
      entry('fk_ads_overall', '2026-09-17'),
      entry('fk_ads_overall', '2026-09-18'),
      entry('fk_ads_overall', '2026-09-19'),
      entry('fk_ads_daily', '2026-09-17'),
    ],
  });
  const cleared = await clearNamedNeedsYouEntries(c, [
    { reportId: 'fk_ads_orders', month: '2026-01' },
    { reportId: 'fk_ads_overall', dataDate: '2026-09-17' },
    { reportId: 'fk_ads_overall', dataDate: '2026-09-18' },
  ]);
  check('the named month and the named days are cleared, and nothing else',
    cleared.map((one) => `${one.reportId}|${one.dataDate}`).sort().join() === [
      'fk_ads_orders|2026-01-05', 'fk_ads_orders|2026-01-31',
      'fk_ads_overall|2026-09-17', 'fk_ads_overall|2026-09-18',
    ].sort().join());
  const left = await whatNeedsYou(c);
  check('a day one month either side of the named month is left alone',
    left.some((one) => one.reportId === 'fk_ads_orders' && one.dataDate === '2025-12-31')
    && left.some((one) => one.reportId === 'fk_ads_orders' && one.dataDate === '2026-02-01'));
  check('the same report, a day not named, is left alone',
    left.some((one) => one.reportId === 'fk_ads_overall' && one.dataDate === '2026-09-19'));
  check('the same day, a different report, is left alone',
    left.some((one) => one.reportId === 'fk_ads_daily' && one.dataDate === '2026-09-17'));
  check('exactly the four named entries are gone and nothing more',
    left.length === 4);
}

{
  /* **JOB 6: THE LIMIT HOLDS -- A CATCH-UP REACHES NO FURTHER BACK THAN
   * `CATCH_UP_REACH_DAYS`.** A report broken for months is not silently
   * walked back through all of it in one sync; that is Job 15's job. */
  const browser = installFakeChrome();
  const c = browser.chrome;
  await rememberLastLanded(c, 'me_orders', '2026-01-01');
  const gap = await daysNobodyTried(c, 'me_orders', '2026-09-20');
  check('the catch-up reaches back no further than the limit',
    gap.length === CATCH_UP_REACH_DAYS && gap[0] === '2026-09-06');
}

{
  /* **JOB 6, THE LIVE CASE (F14): MEESHO ORDERS FOR 09-17..09-19 WERE NEVER
   * OWED BY ANYTHING, BECAUSE NOTHING EVER TRIED THEM.** A sync for 09-20,
   * with `me_orders` landed every day up to and including 09-16, walks all
   * four owed days in the one run, oldest first -- not one day per run
   * (Rumee's own fault, not to be copied). */
  const browser = installFakeChrome();
  const c = browser.chrome;
  const walk = aWalkThat();
  await seedLandedRangeForTest(c, 'me_orders', '2026-09-06', '2026-09-16');
  await startTheNight(c, {
    doing: ['me_orders'], at: ON('2026-09-20'), openAt: 'https://x/', dataDate: '2026-09-20',
    canGoBack: ['me_orders'],
  });
  await carryTheNightOn(c, { ...walk, at: ON('2026-09-20') });
  for (const d of ['2026-09-17', '2026-09-18', '2026-09-19']) {
    walk.itFinished({ state: 'landed', reportId: 'me_orders', size: 10, dataDate: d });
    // eslint-disable-next-line no-await-in-loop
    await carryTheNightOn(c, { ...walk, at: ON('2026-09-20') });
  }
  check('a gap of several days nobody ever tried is owed in full, oldest first, in one run',
    walk.started.map((one) => one.dataDate).join() === '2026-09-17,2026-09-18,2026-09-19,2026-09-20');
}

{
  /* **JOB 6: A REPORT THE PLATFORM ONLY EVER GIVES FOR NOW NEVER OWES A GAP
   * DAY THIS WAY EITHER** -- `me_catalog` is not in `canGoBack`, so a gap
   * since its last landed day is never even asked about. */
  const browser = installFakeChrome();
  const c = browser.chrome;
  const walk = aWalkThat();
  await rememberLastLanded(c, 'me_catalog', '2026-09-10');
  await startTheNight(c, {
    doing: ['me_catalog'], at: ON('2026-09-20'), openAt: 'https://x/', dataDate: '2026-09-20',
    canGoBack: [],
  });
  await carryTheNightOn(c, { ...walk, at: ON('2026-09-20') });
  check('a picture-of-now report never owes a gap day, whatever the gap since it last landed',
    walk.started.length === 1 && walk.started[0].dataDate === '2026-09-20');
}

{
  /* **JOB 6 x FLIPKART'S TWENTY: A GAP DAY THAT DOES NOT FIT WAITS FOR THE
   * NEXT SYNC, IT IS NEVER SPENT PAST WHAT IS LEFT.** `fk_orders` landed every
   * day up to 09-16; the sync of 09-20 is allowed only one of the twenty. */
  const browser = installFakeChrome();
  const c = browser.chrome;
  const walk = aWalkThat();
  await seedLandedRangeForTest(c, 'fk_orders', '2026-09-06', '2026-09-16');
  await startTheNight(c, {
    doing: ['fk_orders'], mayAskFor: 1, at: ON('2026-09-20'), openAt: FLIPKART_HOME,
    dataDate: '2026-09-20', canGoBack: ['fk_orders'],
  });
  await carryTheNightOn(c, { ...walk, at: ON('2026-09-20') });
  check('the OWN day of the sync is asked for first, ahead of the older gap days (review finding, 2026-10-05)',
    walk.started.length === 1 && walk.started[0].reportId === 'fk_orders' && walk.started[0].dataDate === '2026-09-20');
  walk.itFinished({ state: 'landed', reportId: 'fk_orders', size: 5, dataDate: '2026-09-20' });
  await carryTheNightOn(c, { ...walk, at: ON('2026-09-20') });
  const night = await theNight(c);
  check('and the allowance spent stays exactly one, never past what the sync was allowed',
    night.spent === 1);
  check('the days that did not fit are named, not silently dropped',
    night.done.filter((one) => one.state === NOT_ASKED
      && one.say.includes('has not been asked for')).length === 3);
}

{
  const consecutiveNight = {
    startedAt: 1000,
    done: [
      { reportId: 'a1', at: 4000 },
      { reportId: 'b2', at: 9000 },
      { reportId: 'c3', at: 12000 }
    ]
  };
  check(
    'N038: seconds per entry use consecutive finish times',
    JSON.stringify(secondsPerReport(consecutiveNight)) === JSON.stringify([3, 5, 3])
  );

  const firstStartNight = {
    startedAt: 2000,
    done: [
      { reportId: 'a1', at: 5000 },
      { reportId: 'b2', at: 9000 }
    ]
  };
  check(
    'N038: first entry is measured from startedAt',
    JSON.stringify(secondsPerReport(firstStartNight)) === JSON.stringify([3, 4])
  );

  const backwardsNight = {
    startedAt: 10000,
    done: [
      { reportId: 'a1', at: 9000 },
      { reportId: 'b2', at: 8000 }
    ]
  };
  check(
    'N038: a backwards clock gives 0 seconds',
    JSON.stringify(secondsPerReport(backwardsNight)) === JSON.stringify([0, 0])
  );

  const roundedNight = {
    startedAt: 0,
    done: [
      { reportId: 'a1', at: 1499 },
      { reportId: 'b2', at: 3000 }
    ]
  };
  check(
    'N038: seconds are rounded to whole seconds',
    JSON.stringify(secondsPerReport(roundedNight)) === JSON.stringify([1, 2])
  );

  const tieNight = {
    startedAt: 0,
    done: [
      { reportId: 'a1', dataDate: '2026-01-01', at: 5000 },
      { reportId: 'b2', dataDate: '2026-01-02', at: 15000 },
      { reportId: 'c3', at: 25000 },
      { reportId: 'd4', dataDate: '2026-01-04', at: 45000 }
    ]
  };
  check(
    'N038: slowest three are slowest first and ties keep finish order',
    JSON.stringify(theSlowestThree(tieNight)) === JSON.stringify([
      { reportId: 'd4', dataDate: '2026-01-04', seconds: 20 },
      { reportId: 'b2', dataDate: '2026-01-02', seconds: 10 },
      { reportId: 'c3', dataDate: '', seconds: 10 }
    ])
  );

  const twoNight = {
    startedAt: 0,
    done: [
      { reportId: 'a1', dataDate: '2026-01-01', at: 1000 },
      { reportId: 'b2', at: 4000 }
    ]
  };
  check(
    'N038: fewer than three entries returns only those entries',
    JSON.stringify(theSlowestThree(twoNight)) === JSON.stringify([
      { reportId: 'b2', dataDate: '', seconds: 3 },
      { reportId: 'a1', dataDate: '2026-01-01', seconds: 1 }
    ])
  );

  check(
    'N038: empty done gives no slow reports',
    JSON.stringify(theSlowestThree({ startedAt: 0, done: [] })) === JSON.stringify([])
  );

  check(
    'N038: missing done gives no slow reports',
    JSON.stringify(theSlowestThree({ startedAt: 0 })) === JSON.stringify([])
  );

  check(
    'N038: empty done gives an empty slowest line',
    theSlowestLine({ startedAt: 0, done: [] }) === ''
  );

  const exampleNight = {
    startedAt: 0,
    done: [
      { reportId: 'b2', dataDate: '2026-01-02', at: 95000 },
      { reportId: 'a1', at: 135000 },
      { reportId: 'c3', at: 147000 }
    ]
  };
  check(
    'N038: slowest line matches the example text',
    theSlowestLine(exampleNight) === 'Slowest reports: b2 2026-01-02 95 s, a1 40 s, c3 12 s.'
  );
}

{
  /* **N038 WIRING: THE RUN LOG NAMES THE SLOWEST THREE AT THE TOP AND EACH REPORT LINE SAYS ITS SECONDS.** */
  const wired = {
    startedAt: 1, finishedAt: 200000, why: 'x',
    left: [], doing: null, spent: 0, mayAskFor: 0,
    done: [
      { reportId: 'a1', state: 'landed', size: 5, at: 40001 },
      { reportId: 'b2', state: 'landed', size: 5, at: 135001 },
    ],
  };
  const log = theRunLog(wired).text;
  check('N038: the run log names the slowest reports above the counts', log.indexOf('Slowest reports: b2 95 s, a1 40 s.') > -1
    && log.indexOf('Slowest reports') < log.indexOf('landed,'));
  check('N038: and each report line says how many seconds it took', log.includes('  a1: landed (5 bytes) [40 s]') && log.includes('  b2: landed (5 bytes) [95 s]'));
}
/* AJ6: the per-report table of the panel. */
check('report table: null night gives null', theReportTable(null, () => '') === null);

{
  const night = {
    startedAt: 0,
    finishedAt: 60000,
    doing: null,
    left: [],
    done: [
      { reportId: 'r1', state: 'landed', say: 'ok', size: 10, at: 1000, dataDate: '2026-01-02' },
      { reportId: 'r2', state: 'failed', say: 'bad', size: 0, at: 2000, dataDate: '2026-01-02' },
      { reportId: 'r3', state: 'needs-you', say: 'auth', size: 0, at: 3000, dataDate: '2026-01-02' },
      { reportId: 'r4', state: 'nothing-to-fetch', say: 'empty', size: 0, at: 4000, dataDate: '2026-01-02' },
      { reportId: 'r5', state: 'not-asked', say: 'later', size: 0, at: 5000, dataDate: '2026-01-02' },
      { reportId: 'r6', state: 'still-waiting', say: 'asked', size: 0, at: 6000, dataDate: '2026-01-02' },
      { reportId: 'r6', state: 'landed', say: 'got', size: 123, at: 7000, dataDate: '2026-01-02' }
    ]
  };
  const table = theReportTable(night, (id) => id);
  check(
    'report table: mixed run counts and one row per report-day',
    table.counts.landed === 3 &&
    table.counts.asked === 0 &&
    table.counts.toFetch === 1 &&
    table.counts.failed === 2 &&
    table.rows.length === 6
  );
}

{
  const night = {
    startedAt: 0,
    finishedAt: 60000,
    doing: null,
    left: [],
    done: [
      { reportId: 'r1', state: 'still-waiting', say: 'wait', size: 0, at: 1000, dataDate: '2026-01-02' },
      { reportId: 'r2', state: 'still-waiting', say: 'wait', size: 0, at: 2000, dataDate: '2026-01-02' },
      { reportId: 'r3', state: 'not-available-yet', say: 'not built', size: 0, at: 3000, dataDate: '2026-01-02' },
      { reportId: 'r2', state: 'not-available-yet', say: 'still not', size: 0, at: 4000, dataDate: '2026-01-02' }
    ]
  };
  const table = theReportTable(night, (id) => id);
  const r1 = table.rows.find((row) => row.key === 'r1|2026-01-02');
  const r2 = table.rows.find((row) => row.key === 'r2|2026-01-02');
  const r3 = table.rows.find((row) => row.key === 'r3|2026-01-02');
  check(
    'report table: still-waiting is asked with star and earlier wait makes not-built asked',
    r1.status === 'asked' &&
    r1.star === true &&
    r2.status === 'asked' &&
    r3.status === 'toFetch'
  );
}

{
  const night = {
    startedAt: 0,
    finishedAt: null,
    doing: 'r-doing',
    left: ['r-wait'],
    done: []
  };
  const table = theReportTable(night, (id) => id);
  const doing = table.rows.find((row) => row.key === 'r-doing|');
  const waiting = table.rows.find((row) => row.key === 'r-wait|');
  check(
    'report table: doing and notStarted rows are toFetch with no seconds',
    doing.word === 'Fetching now' &&
    doing.status === 'toFetch' &&
    doing.seconds === null &&
    waiting.word === 'Waiting' &&
    waiting.status === 'toFetch' &&
    waiting.seconds === null
  );
}

{
  const night = {
    startedAt: 0,
    finishedAt: 3000,
    doing: null,
    left: [],
    done: [
      { reportId: 'r1', state: 'still-waiting', say: 'waiting', size: 0, at: 1000, dataDate: '2026-01-02', pageWas: 'checking' },
      { reportId: 'r1', state: 'landed', say: 'done', size: 200, at: 2000, dataDate: '2026-01-02', pageWas: 'ok page' }
    ]
  };
  const table = theReportTable(night, (id) => id);
  const lines = table.rows[0].detail.split('\n');
  check(
    'report table: detail has two steps in order and pageWas under each',
    lines[0] === 'r1: still-waiting -- waiting [1 s]' &&
    lines[1] === '    the page said: checking' &&
    lines[2] === 'r1: landed (200 bytes) -- done [1 s]' &&
    lines[3] === '    the page said: ok page'
  );
}

{
  const night = {
    startedAt: 0,
    finishedAt: 33 * 60 * 1000,
    doing: null,
    left: [],
    done: [
      { reportId: 'r1', state: 'landed', say: 'ok', size: 10, at: 1000, dataDate: '2026-01-02' },
      { reportId: 'r2', state: 'failed', say: 'bad', size: 0, at: 2000, dataDate: '2026-01-02' }
    ]
  };
  const nameOf = (id) => (id === 'r1' ? 'Sales' : '');
  const table = theReportTable(night, nameOf);
  const named = table.rows.find((row) => row.key === 'r1|2026-01-02');
  const fallback = table.rows.find((row) => row.key === 'r2|2026-01-02');
  const stopped = theReportTable({ ...night, finishedAt: 0 }, nameOf);
  check(
    'report table: name uses nameOf, falls back to id, adds date, and minutes is 33 or 0',
    named.name === 'Sales (2026-01-02)' &&
    fallback.name === 'r2 (2026-01-02)' &&
    table.minutes === 33 &&
    stopped.minutes === 0
  );
}

{
  const night = {
    startedAt: 0,
    finishedAt: 6000,
    doing: null,
    left: [],
    done: [
      { reportId: 'r1', state: 'still-waiting', say: 'wait', size: 0, at: 2000, dataDate: '2026-01-02' },
      { reportId: 'r1', state: 'landed', say: 'done', size: 100, at: 5000, dataDate: '2026-01-02' }
    ]
  };
  const ticks = secondsPerReport(night);
  const table = theReportTable(night, () => '');
  check(
    'report table: seconds on a row is the report-day last entry seconds',
    table.rows.length === 1 && table.rows[0].seconds === ticks[1]
  );
}

{
  const night = { startedAt: 0, finishedAt: 60000, doing: null, left: [], done: [{ reportId: 'r1', state: 'odd-thing', say: 'x', size: 0, at: 1000 }] };
  const { counts, rows } = theReportTable(night, () => '');
  check('report table: a state nobody named goes to still to fetch with its own word',
    counts.toFetch === 1 && counts.landed + counts.asked + counts.failed === 0 && rows[0].word === 'odd-thing' && rows[0].means === 'x');
}
{
  const D = '2026-01-02';
  const one = (reportId, state, say) => ({ reportId, state, say, size: 0, at: 1000, dataDate: D });
  const night = {
    startedAt: 5000,
    finishedAt: 125000,
    doing: 'rd',
    left: ['rw'],
    done: [
      one('a', 'landed', 'saved ok'),
      one('b', 'landed', ''),
      one('c', 'nothing-to-fetch', 'empty day'),
      one('d', 'still-waiting', 'asked it'),
      one('e', 'not-available-yet', 'not built'),
      one('f', 'not-asked', 'later'),
      one('g', 'failed', 'broke'),
      one('h', 'needs-you', 'log in'),
      one('i', 'odd-thing', 'odd say')
    ]
  };
  const table = theReportTable(night, (id) => (id === 'rd' ? 'Doing name' : id === 'rw' ? 'Waiting name' : ''));
  const row = (id) => table.rows.find((r) => r.key === `${id}|${D}`);
  const same = (r, word, means, star) => r.word === word && r.means === means && r.star === star;
  check('report table: landed row says Landed with its words, and "file saved" when it has none',
    same(row('a'), 'Landed', 'saved ok', false) && same(row('b'), 'Landed', 'file saved', false));
  check('report table: nothing-to-fetch row says Nothing to fetch with its words and no star',
    same(row('c'), 'Nothing to fetch', 'empty day', false) && row('c').status === 'landed');
  check('report table: still-waiting row says Asked with its words and a star',
    same(row('d'), 'Asked', 'asked it', true));
  check('report table: not-built row says Not built yet with its words and a star',
    same(row('e'), 'Not built yet', 'not built', true));
  check('report table: not-asked row says Not asked with its words and no star',
    same(row('f'), 'Not asked', 'later', false) && row('f').status === 'toFetch');
  check('report table: failed row says Failed with its words and no star',
    same(row('g'), 'Failed', 'broke', false) && row('g').status === 'failed');
  check('report table: needs-you row says Needs you with its words and no star',
    same(row('h'), 'Needs you', 'log in', false) && row('h').status === 'failed');
  check('report table: unnamed state keeps its own words and no star',
    same(row('i'), 'odd-thing', 'odd say', false));
  const doing = table.rows.find((r) => r.key === 'rd|');
  const waiting = table.rows.find((r) => r.key === 'rw|');
  check('report table: the running and not-started rows carry the name, no star, no words, no detail',
    doing.name === 'Doing name' && doing.star === false && doing.means === '' && doing.detail === '' &&
    waiting.name === 'Waiting name' && waiting.star === false && waiting.means === '' && waiting.detail === '');
  const bare = theReportTable({ ...night, doing: 'x1', left: ['x2'] }, () => '');
  const bd = bare.rows.find((r) => r.key === 'x1|');
  const bw = bare.rows.find((r) => r.key === 'x2|');
  check('report table: the running and not-started rows fall back to the id when there is no name',
    bd.name === 'x1' && bw.name === 'x2');
  check('report table: carries the night start and finish times',
    table.startedAt === 5000 && table.finishedAt === 125000);
}
{
  const D = '2026-01-02';
  const night = {
    startedAt: 0, finishedAt: 60000, doing: null, left: [],
    done: [
      { reportId: 'q1', state: 'not-asked', say: 'x', size: 0, at: 1000, dataDate: D },
      { reportId: 'q1', state: 'not-available-yet', say: 'y', size: 0, at: 2000, dataDate: D }
    ]
  };
  const q = theReportTable(night, (id) => id).rows[0];
  check('report table: an earlier step that was not "still waiting" does not make not-built asked',
    q.status === 'toFetch' && q.word === 'Not built yet');
}
const EXPECTED = 180 + 16 + 5 + 1 + 1 + 1 + 1 + 12 + 8 + 11 + 1 + 2 + 5 + 3;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
