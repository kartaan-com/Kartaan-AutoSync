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
} from './nightly.js';
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
  check('while a rolling-window report is not on that list',
    !ONLY_ITS_NEWEST_DAY.includes('me_returns') && !ONLY_ITS_NEWEST_DAY.includes('me_claims'));
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
    doing: ['me_orders'], at: 1, openAt: 'https://x/', dataDate: '2026-09-14',
    days: ['2026-09-12', '2026-09-13', '2026-09-14'],
  });
  await carryTheNightOn(browser.chrome, { ...walk, at: 2 });
  walk.itFinished({ state: 'landed', reportId: 'me_orders', size: 10, dataDate: '2026-09-12' });
  await carryTheNightOn(browser.chrome, { ...walk, at: 3 });
  check('a sync asked for several days walks the oldest first, then the next',
    walk.started.map((one) => one.dataDate).join() === '2026-09-12,2026-09-13');
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
  check('the oldest owed day is the one actually asked for',
    walk.started.length === 1 && walk.started[0].reportId === 'fk_orders' && walk.started[0].dataDate === '2026-09-17');
  walk.itFinished({ state: 'landed', reportId: 'fk_orders', size: 5, dataDate: '2026-09-17' });
  await carryTheNightOn(c, { ...walk, at: ON('2026-09-20') });
  const night = await theNight(c);
  check('and the allowance spent stays exactly one, never past what the sync was allowed',
    night.spent === 1);
  check('the days that did not fit are named, not silently dropped',
    night.done.filter((one) => one.state === 'nothing-to-fetch'
      && one.say.includes('has not been asked for')).length === 3);
}

const EXPECTED = 171;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
