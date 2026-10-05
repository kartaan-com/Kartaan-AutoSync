/* Checks for the Meesho ads sweep.
 *
 * Run: node extension/ads.test.js
 *
 * **THE MOST IMPORTANT ONE IS THAT NO SELLER IS WRITTEN DOWN ANYWHERE.** His
 * instruction, 2026-09-11: *"make sure it is not hard coded to any one seller...
 * it should be able to handle the multi seller thing."* The working reference
 * holds one real panel name in its own config and falls back to it, and its other
 * way of finding a seller -- scraping localStorage key names -- returns nothing at
 * all on that same seller's panel today. Both of those are what this file exists
 * to stop being repeated.
 *
 * **AND THE ONE THAT WOULD BE WORST IF IT WERE WRONG: a campaign name with a
 * comma in it.** Sellers name their own campaigns and sellers type commas. Written
 * plainly, one such name shifts every column after it by one, for that row only --
 * which nothing downstream would notice and no total would reveal.
 *
 * **A STAND-IN MEESHO, DELIBERATELY AWKWARD.** It pages its answers the way the
 * real one does, it mixes running and paused campaigns, it can answer nothing at
 * all for one campaign, and it never hands back a tidy single page.
 */

import {
  AT_MOST_PAGES,
  A_PAGE_OF_CAMPAIGNS,
  CATALOGUE_COLUMNS,
  MASTER_COLUMNS,
  ONE_CAMPAIGN,
  RUNNING,
  SUMMARY_COLUMNS,
  THE_CAMPAIGN_LIST,
  asARow,
  asAValue,
  everyCampaign,
  sweepTheAds,
  theCatalogueRows,
  theHeadersFor,
  theMasterRow,
  theSummaryRow,
  whoIsSignedIn,
} from './ads.js';

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

const DAY = '2026-09-10';

/** The columns of one row, read back the way a reader would.
 *
 *  **NOT `split(',')`, AND THE FIRST DRAFT OF THIS FILE USED IT AND WENT RED.**
 *  Every value is written inside quotes precisely so a comma inside one cannot
 *  split the row -- so a check that splits on commas is testing the fault it
 *  exists to catch. Values are separated by a quote, a comma and a quote. */
const columnsOf = (row) => row.slice(1, -1).split('","');

/* ------------------------------------------------------ who is signed in */

/* **THE TWO COOKIE NAMES ARE MEASURED, NOT GUESSED.** Read off a real supplier
 * panel on 2026-09-11: `current_az_identifier` held the panel slug and matched
 * the address bar, `s_id` held the numeric supplier id and matched the number
 * Meesho puts on its own download file names. */
const A_REAL_JAR = 'browser_uid=x; current_az_identifier=abcde; s_id=1234567; _ga=GA1.2.3';

{
  const who = whoIsSignedIn(A_REAL_JAR);
  check('the seller is read out of Meesho\'s own cookies', Boolean(who));
  check('and both halves come back', who.slug === 'abcde' && who.supplierId === '1234567');
  /* **THIS IS THE WHOLE OF THE MULTI-SELLER ANSWER.** A different browser signed
   * in as somebody else answers somebody else, with nothing configured and
   * nothing to change. */
  const other = whoIsSignedIn('current_az_identifier=zzzzz; s_id=9999999');
  check('a different seller signed in answers that different seller',
    other.slug === 'zzzzz' && other.supplierId === '9999999');
  check('and neither of them is written down anywhere in this file',
    !JSON.stringify([THE_CAMPAIGN_LIST, ONE_CAMPAIGN]).includes('abcde'));
}

{
  /* **NOT SIGNED IN IS ANSWERED, NEVER GUESSED AT.** A blank identifier would go
   * into a header and the addresses would answer for nobody -- which reads as
   * Meesho having changed rather than as somebody being signed out. */
  check('no cookies at all is nobody', whoIsSignedIn('') === null);
  check('a slug with no supplier id is nobody',
    whoIsSignedIn('current_az_identifier=abcde') === null);
  check('a supplier id with no slug is nobody', whoIsSignedIn('s_id=1234567') === null);
  check('and an id that is not a number is nobody',
    whoIsSignedIn('current_az_identifier=abcde; s_id=not-a-number') === null);
  /* **AND A COOKIE CARRYING SOMETHING ENORMOUS IS REFUSED**, because it would
   * otherwise go straight into a request header. */
  check('and something far too long to be an id is nobody',
    whoIsSignedIn(`current_az_identifier=abcde; s_id=${'9'.repeat(40)}`) === null);
}

{
  const headers = theHeadersFor(whoIsSignedIn(A_REAL_JAR));
  check('the headers carry the seller Meesho is signed in as',
    headers.identifier === 'abcde' && headers['supplier-id'] === '1234567');
  check('and say what kind of client they come from, as the reference does',
    headers['client-type'] === 'd-web');
}

/* ------------------------------------------------------------ writing a row */

{
  check('an ordinary value is written plainly enough to read', asAValue('hello') === '"hello"');
  /* **SELLERS TYPE COMMAS INTO THEIR OWN CAMPAIGN NAMES.** */
  check('a value with a comma in it cannot split the row',
    asARow(['a,b', 'c']) === '"a,b","c"');
  check('and a value with a quote in it cannot end it early',
    asAValue('he said "hi"') === '"he said ""hi"""');
  /* **NOTHING AT ALL IS AN EMPTY COLUMN, NOT THE WORD `undefined`.** Meesho
   * leaves fields out of its answers, and the word would read downstream as a
   * value somebody could add up. */
  check('a field Meesho left out is an empty column, not the word undefined',
    asARow([undefined, null]) === '"",""');
}

/* ---------------------------------------------------------------- the rows */

const A_CAMPAIGN = {
  campaign_id: 77, campaign_name: 'Rings, small', status: 'LIVE', start_date: '2026-04-01',
};
const ITS_DETAILS = {
  start_date: '2026-04-01T00:00:00',
  campaign_overall_performance: {
    total_budget_utilized: 900, total_revenue: 4000, total_orders: 40, total_views: 90000,
    total_clicks: 800, roi: 4.4, conversion_rate: 0.05, average_order_value: 100, cpo: 22.5,
  },
  campaign_performance: {
    total_budget_utilized: 30, total_revenue: 120, roi: 4, cpo: 15,
    total_views: 3000, total_clicks: 40, total_orders: 2, conversion_rate: 0.05,
    average_order_value: 60,
  },
  catalogs: [
    { catalog_id: 5, category: ['Jewellery', 'Rings'], catalog_status: 'ACTIVE', bid: 3,
      perf_details: { budget_utilised: 20, revenue: 80, order_count: 4, total_views: 2000,
        total_clicks: 30, cpc: 0.6, conversion_rate: 0.04, roi: 4, average_rating: 4.1 },
      roi_bidding_catalog_feedback_details: { catalog_feedback_state: 'RED_ATTENTION' } },
    { catalog_id: 6, category: 'Earrings', catalog_status: 'ACTIVE', bid: 2,
      perf_details: { budget_utilised: 10, revenue: 40, order_count: 0 } },
  ],
};

{
  const row = columnsOf(theMasterRow(DAY, A_CAMPAIGN, ITS_DETAILS));
  check('the master row has a column for every heading',
    row.length === MASTER_COLUMNS.length);
  /* **THE DAY IS THE DAY THE FIGURES ARE ABOUT, NOT THE DAY THE RUN HAPPENED.**
   * The reference writes the run's own date, which is why a past day can never be
   * asked for there. Every other report in this product is named by the day it is
   * about, and this is the same rule. */
  check('and it begins with the day the figures are about', row[0] === DAY);
  check('and carries what the campaign has taken since it began',
    row[MASTER_COLUMNS.indexOf('Revenue')] === '4000');
  check('and the day the campaign started, cut to the day',
    row[MASTER_COLUMNS.indexOf('Start Date')] === '2026-04-01');
  /* **A NAME WITH A COMMA IN IT, DRIVEN RATHER THAN ASSUMED.** */
  check('and a campaign name with a comma in it is still one column',
    theMasterRow(DAY, A_CAMPAIGN, ITS_DETAILS).includes('"Rings, small"'));
}

{
  const row = columnsOf(theSummaryRow(DAY, A_CAMPAIGN, ITS_DETAILS));
  check('the summary row has a column for every heading',
    row.length === SUMMARY_COLUMNS.length);
  /* **THE DAY'S FIGURES AND NOT THE LIFETIME ONES.** They sit in two different
   * parts of the same answer and are the same shape, so taking the wrong one
   * would look perfectly right and be forty times too big. */
  check('and it carries the DAY figures, not the lifetime ones',
    row[SUMMARY_COLUMNS.indexOf('Revenue')] === '120');
}

{
  const rows = theCatalogueRows(DAY, A_CAMPAIGN, ITS_DETAILS);
  check('one row per catalogue inside the campaign', rows.length === 2);
  const first = columnsOf(rows[0]);
  check('each has a column for every heading', first.length === CATALOGUE_COLUMNS.length);
  /* **A CATEGORY CAN BE A LIST OR ONE WORD, and both really come back.** */
  check('a category that is a list is written as one column',
    first[CATALOGUE_COLUMNS.indexOf('Category')] === 'Jewellery|Rings');
  check('and a category that is one word is written plainly',
    columnsOf(rows[1])[CATALOGUE_COLUMNS.indexOf('Category')] === 'Earrings');
  /* **MEESHO'S OWN WORD FOR HEALTH, PUT INTO WORDS A PERSON READS.** */
  check('and Meesho\'s word for a struggling catalogue is turned into plain words',
    first[CATALOGUE_COLUMNS.indexOf('Current Performance')] === 'Low Orders');
  check('spend per order is worked out from what was spent and what sold',
    first[CATALOGUE_COLUMNS.indexOf('Ad Spend Per Order')] === '5.00');
  /* **AND NOTHING SOLD IS NOUGHT, NOT A DIVISION BY NOTHING.** Left to work
   * itself out that column would read `Infinity` on every new catalogue. */
  check('and a catalogue that sold nothing costs nought per order, not infinity',
    columnsOf(rows[1])[CATALOGUE_COLUMNS.indexOf('Ad Spend Per Order')] === '0');
}

/* ---------------------------------------------------------------- the sweep */

/** A stand-in Meesho. Pages its answers, mixes statuses, and counts what it was
 *  asked -- because how MANY times somebody else's server is asked is part of
 *  what this has to get right. */
function aMeesho({ campaigns = [], detailsFor = () => ITS_DETAILS } = {}) {
  const it = { asked: [], pages: 0, details: 0 };
  it.ask = async (address, body) => {
    it.asked.push(address);
    if (address === THE_CAMPAIGN_LIST) {
      it.pages += 1;
      const from = (body.page_number - 1) * A_PAGE_OF_CAMPAIGNS;
      return { data: { campaigns: campaigns.slice(from, from + A_PAGE_OF_CAMPAIGNS) } };
    }
    it.details += 1;
    it.lastAsked = body;
    /* **WRAPPED IN `data` THE WAY MEESHO REALLY ANSWERS**, confirmed live on
     * 2026-09-11: the campaign list came back as `{ data: { campaigns: [...] } }`.
     * A stand-in that handed back the bare object would have let a sweep that
     * never reads `.data` pass -- which is exactly what the first draft of this
     * file did, and it showed as three campaigns swept and no files written. */
    const answered = detailsFor(body.campaign_id);
    return answered ? { data: answered } : null;
  };
  return it;
}

const someCampaigns = (howMany, everyNthLive = 1) => Array.from({ length: howMany }, (_, i) => ({
  campaign_id: i, campaign_name: `c${i}`, status: i % everyNthLive === 0 ? RUNNING : 'PAUSED',
  start_date: '2026-04-01',
}));

{
  /* **TWENTY-THREE CAMPAIGNS IS THREE PAGES, THE LAST ONE SHORT.** A sweep that
   * stopped at the first page would quietly miss every campaign after the tenth,
   * and a seller with eleven would never know. */
  const meesho = aMeesho({ campaigns: someCampaigns(23) });
  const all = await everyCampaign(meesho.ask, { supplierId: '1234567' });
  check('every page of campaigns is asked for, not just the first', all.length === 23);
  check('and it stops at the short page rather than asking for ever', meesho.pages === 3);
}

{
  /* **A LIST THAT NEVER ENDS IS A LOOP THAT NEVER ENDS, at night, against
   * somebody else's server.** A stand-in that always answers a full page is
   * exactly the shape of a platform paging wrongly. */
  const meesho = aMeesho({ campaigns: someCampaigns(500) });
  let gaveUp = '';
  try { await everyCampaign(meesho.ask, { supplierId: '1234567' }); } catch (wrong) { gaveUp = wrong.message; }
  check('a list that never says it has ended is given up on, and says so rather than writing a part of it',
    meesho.pages === AT_MOST_PAGES && gaveUp.includes('more than'));
}

{
  /* **ONLY THE ONES RUNNING, WHICH IS HIS RULING OF 2026-09-11**, asked as a
   * question with the consequence stated. */
  const meesho = aMeesho({ campaigns: someCampaigns(9, 3) });
  const swept = await sweepTheAds(meesho.ask, { supplierId: '1234567' }, DAY);
  check('every campaign is looked at', swept.lookedAt === 9);
  check('and only the ones running are asked about', swept.running === 3 && meesho.details === 3);
  check('and three files come back, one per report',
    swept.files.map((one) => one.reportId).join(',')
      === 'me_ads,me_ads_summary,me_ads_catalog');
  /* **THE DAY IS ASKED FOR AT BOTH ENDS**, which is what makes a past day a real
   * thing to ask Meesho for. */
  check('and the day is asked for at both ends of the range',
    meesho.lastAsked.start_date === DAY && meesho.lastAsked.end_date === DAY);
  const master = swept.files[0].text.split('\n');
  check('the master file has a heading and a row per running campaign',
    master.length === 4 && master[0] === asARow(MASTER_COLUMNS));
  const catalogue = swept.files[2].text.split('\n');
  check('and the catalogue file has a row per catalogue per campaign',
    catalogue.length === 1 + 3 * 2);
}

{
  /* **NONE RUNNING IS THE CASE HE IS IN TODAY: 37 campaigns, every one paused.**
   * No files at all, and the count said out loud so the walk can turn it into a
   * sentence rather than an empty folder. */
  const meesho = aMeesho({ campaigns: someCampaigns(37).map((one) => ({ ...one, status: 'PAUSED' })) });
  const swept = await sweepTheAds(meesho.ask, { supplierId: '1234567' }, DAY);
  check('no campaign running writes no file at all', swept.files.length === 0);
  check('and says how many there were to look at', swept.lookedAt === 37 && swept.running === 0);
  /* **AND NOTHING IS ASKED ABOUT A PAUSED CAMPAIGN.** Thirty-seven needless calls
   * to somebody else's server is how a nightly run starts looking like a
   * nuisance. */
  check('and not one campaign was asked about', meesho.details === 0);
}

{
  /* **A CAMPAIGN MEESHO ANSWERED NOTHING FOR IS SKIPPED, NOT WRITTEN AS BLANKS.**
   * A row of empty columns reads downstream as a campaign that spent nothing,
   * which is a different and entirely believable fact. */
  const meesho = aMeesho({
    campaigns: someCampaigns(3),
    /* **THE ID ARRIVES AS TEXT, because Meesho is sent it as text** -- the sweep
     * writes `campaign_id: String(...)`, which is what the reference does too. A
     * stand-in comparing it as a number matches nothing and quietly answers for
     * every campaign, which is how this check first passed while proving nothing. */
    detailsFor: (id) => (String(id) === '1' ? null : ITS_DETAILS),
  });
  let failedWhy = '';
  try { await sweepTheAds(meesho.ask, { supplierId: '1234567' }, DAY); } catch (wrong) { failedWhy = wrong.message; }
  check('a campaign that answered nothing fails the whole day rather than being left out of a part-written one',
    failedWhy.includes('campaign 1') && failedWhy.includes('no part of this day was written'));

  /* A campaign LIST page that did not answer is not the end of the list either. */
  let listFailedWhy = '';
  try {
    await sweepTheAds(async () => null, { supplierId: '1234567' }, DAY);
  } catch (wrong) { listFailedWhy = wrong.message; }
  check('a campaign list that would not answer fails the day, instead of reading as no campaigns running',
    listFailedWhy.includes('page 1'));
  let laterPageWhy = '';
  const dropsPageTwo = async (address, body) => (body.page_number === 2 ? null
    : { data: { campaigns: someCampaigns(10) } });
  try { await everyCampaign(dropsPageTwo, { supplierId: '1234567' }); } catch (wrong) { laterPageWhy = wrong.message; }
  check('and a later page that would not answer does not quietly cut the list short',
    laterPageWhy.includes('page 2'));
}

{
  /* **THE PACING IS THE WALK'S, AND IT REALLY HAPPENS BETWEEN CALLS.** A portal
   * that reads the run as a machine can block the seller, which is the whole
   * reason the rest of the walk paces itself. */
  const meesho = aMeesho({ campaigns: someCampaigns(12) });
  let paused = 0;
  await sweepTheAds(meesho.ask, { supplierId: '1234567' }, DAY,
    { pause: async () => { paused += 1; } });
  check('it pauses between one call and the next', paused >= 12);
}

const EXPECTED = 45;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
