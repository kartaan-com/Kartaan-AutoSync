/* Checks for Flipkart's top search keywords (2026-09-15).
 *
 * Run: node extension/keywords.test.js
 *
 * **WHAT IS CHECKED HERE IS WHAT CAN BE WRONG WITHOUT A PAGE**: which buttons are
 * page numbers, where a row's SKU is, and the file that is made. Opening the
 * pop-ups is checked on his own traffic report, the reference's own route.
 */

import { THE_HEADER, readTheKeywords, theCsv, theDayShown, thePageCount, theSkuOf } from './keywords.js';

let failures = 0;
let ran = 0;

function check(name, passed) {
  ran++;
  console.log(`${passed ? 'PASS' : 'FAIL'}  ${name}`);
  if (!passed) failures++;
}

check('PAGE NUMBERS ARE READ OFF BUTTONS WHOSE WORDS ARE ONLY A NUMBER',
  thePageCount(['1', '2', '3', 'Next', '12 items']) === 3);
check('and a page with no numbers on it is one page', thePageCount(['Next', '']) === 1);

check('A LISTING ROW\'S SKU IS ITS SECOND LINE, the reference\'s own reading',
  theSkuOf('Rumee Antique Jhumka\nDJ 14 Bahubali\n2,133') === 'DJ 14 Bahubali');
check('and a row with one line has no SKU to read', theSkuOf('only one') === 'N/A');

const csv = theCsv('2026-09-13', [
  ['DJ 14 Bahubali', 'jhumka earrings', '45%', '12%'],
  ['DJ-15', 'temple "gold" jhumka', '33%', '18%'],
]);
check('THE FILE IS THE REFERENCE\'S: its header first',
  csv.split('\n')[0] === 'Date,SKU,Keyword,Impression %,Clicks %' && THE_HEADER === csv.split('\n')[0]);
check('then one row per keyword, the day first, every cell quoted',
  csv.split('\n')[1] === '"2026-09-13","DJ 14 Bahubali","jhumka earrings","45%","12%"');
check('and a quote inside a keyword is doubled, never left to break the row',
  csv.split('\n')[2].includes('"temple ""gold"" jhumka"'));

check('THE DAY SHOWN IS READ OFF THE ADDRESS, the reference\'s way',
  theDayShown('https://seller.flipkart.com/index.html#dashboard/growth/seller-insights?selectedPeriod=latest'
    + '&startDate=2026-09-13&endDate=2026-09-13') === '2026-09-13');
check('and an address naming no day shows none', theDayShown('https://seller.flipkart.com/') === '');
{
  /* **A LATEST DAY THAT IS NOT THE DAY ASKED FOR PRESSES NOTHING.** The page here
   * would throw if touched, so an answer at all proves nothing was looked at. */
  const untouchable = new Proxy({}, { get: () => { throw new Error('the page was touched'); } });
  const got = await readTheKeywords(untouchable, {
    dataDate: '2026-09-14', whereNow: () => '#x?selectedPeriod=latest&startDate=2026-09-13',
  });
  check('A LATEST DAY THAT IS NOT THE DAY ASKED FOR IS ANSWERED BEFORE ANYTHING IS PRESSED',
    got.shownDay === '2026-09-13' && got.rows.length === 0 && got.listings === 0);
}

{
  /* **A DAY THAT CANNOT BE TOLD FAILS CLOSED (review finding, 2026-10-05).** */
  const untouchable = new Proxy({}, { get: () => { throw new Error('the page was touched'); } });
  const got = await readTheKeywords(untouchable, { dataDate: '2026-09-14', whereNow: () => '#x?selectedPeriod=latest' });
  check('an address that names no day is answered before anything is pressed, saying the day could not be told',
    got.dayNotShown === true && got.rows.length === 0 && got.listings === 0);
}

const EXPECTED = 11;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
