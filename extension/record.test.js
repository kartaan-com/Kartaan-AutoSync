/* Checks for the extension's own record of what it landed (job 38).
 *
 * Run: node extension/record.test.js
 *
 * **THE ONES THAT MATTER MOST:** the record is read as damaged rather than as empty (written over, empty would say
 * nothing has ever landed); a day landed again replaces its own line and every other line comes through untouched;
 * and the file name and shape are the Python's, read out of the Python's own source.
 */

import { readFileSync } from 'node:fs';
import {
  THE_EXTENSIONS_RECORD, THE_RECORDS_SHAPE, TheRecordIsDamaged, aLineFor, theDayInAName, theLinesFor, theLinesIn,
  theRecordWith,
} from './record.js';

process.on('uncaughtException', (err) => {
  console.log(`FAIL  the checks stopped part way through: ${(err && err.message) || String(err)}`);
  process.exit(1);
});

let failures = 0;
let ran = 0;

function check(name, passed) {
  ran++;
  console.log(`${passed ? 'PASS' : 'FAIL'}  ${name}`);
  if (!passed) failures++;
}

const threw = (work) => {
  try {
    work();
  } catch (wrong) {
    return wrong;
  }
  return null;
};

/* ---------------------------------------------------- the same words as the Python */

const PYTHON = readFileSync(new URL('../autosync/manifest.py', import.meta.url), 'utf8');
check('the record is called what the Python says the extension\'s record is called',
  PYTHON.includes(`EXTENSION_FILE_NAME = "${THE_EXTENSIONS_RECORD}"`));
check('and it is written in the shape the Python reads and writes',
  new RegExp(`^SHAPE = ${THE_RECORDS_SHAPE}$`, 'm').test(PYTHON));

/* ---------------------------------------------------------------- one line */

check('a day is read out of a file\'s name', theDayInAName('meesho_me_orders_2026-09-20.csv') === '2026-09-20');
check('and a name with no real day gives nothing', theDayInAName('meesho_me_views.csv') === ''
  && theDayInAName('x_2026-13-45.csv') === '');
const LINE = aLineFor({
  reportId: 'me_orders', fileName: 'meesho_me_orders_2026-09-20.csv', size: 400, day: '2026-09-20', on: '2026-09-21',
});
check('a landing is a line in the run\'s own shape', LINE && LINE.state === 'verified' && LINE.dataDate === '2026-09-20'
  && LINE.fileSize === 400 && LINE.checkedOn === '2026-09-21' && LINE.fileName.endsWith('.csv'));
check('a file of nothing is not a file that arrived, so it has no line',
  aLineFor({ reportId: 'me_orders', fileName: 'x_2026-09-20.csv', size: 0, day: '2026-09-20' }) === null);
check('and neither has one with no real day',
  aLineFor({ reportId: 'me_orders', fileName: 'x.csv', size: 9, day: '' }) === null);
check('a running list is recorded for every day inside it, not for the day it was last touched',
  theLinesFor({
    reportId: 'me_views', fileName: 'meesho_me_views.csv', size: 90, days: ['2026-09-19', '2026-09-21'], on: '2026-09-22',
  }).map((one) => one.dataDate).join() === '2026-09-19,2026-09-21');
check('and a file named by its day is recorded for that day',
  theLinesFor({ reportId: 'me_orders', fileName: 'meesho_me_orders_2026-09-20.csv', size: 5 })
    .map((one) => one.dataDate).join() === '2026-09-20');

/* ----------------------------------------------------------- the whole record */

const FIRST = theRecordWith('', [LINE]);
const parsed = JSON.parse(FIRST);
check('the first landing writes a record with the shape, no reads of its own and one line',
  parsed.shape === THE_RECORDS_SHAPE && parsed.reads.length === 0 && parsed.lines.length === 1);
const NL = String.fromCharCode(10);
check('and its text begins exactly as the Python checks sample of it does, and ends with a line break',
  FIRST.startsWith(`{${NL} "shape": 2,${NL} "reads": [],${NL} "lines": [${NL}`) && FIRST.endsWith(`}${NL}`));
const OTHER = aLineFor({
  reportId: 'fk_orders', fileName: 'flipkart_fk_orders_2026-09-20.xlsx', size: 70, day: '2026-09-20', on: '2026-09-21',
});
const TWO = theRecordWith(FIRST, [OTHER]);
check('another report on the same day is added beside the first and nothing else moves',
  theLinesIn(TWO).length === 2 && theLinesIn(TWO).some((one) => one.reportId === 'me_orders' && one.fileSize === 400));
const AGAIN = aLineFor({
  reportId: 'me_orders', fileName: 'meesho_me_orders_2026-09-20.csv', size: 410, day: '2026-09-20', on: '2026-09-22',
});
const REPLACED = theLinesIn(theRecordWith(TWO, [AGAIN]));
check('a day landed again replaces its own line where it stands, and keeps one line',
  REPLACED.length === 2 && REPLACED.find((one) => one.reportId === 'me_orders').fileSize === 410);
check('and the same landings always write the same bytes',
  theRecordWith(theRecordWith('', [LINE, OTHER]), []) === theRecordWith(theRecordWith('', [OTHER, LINE]), []));
check('lines come out oldest day first, then by report',
  theLinesIn(theRecordWith('', [aLineFor({ reportId: 'a', fileName: 'a_2026-09-21.csv', size: 1, day: '2026-09-21' }), LINE, OTHER]))
    .map((one) => `${one.dataDate}/${one.reportId}`).join() === '2026-09-20/fk_orders,2026-09-20/me_orders,2026-09-21/a');

/* ------------------------------------- damaged is never read as empty */

const damage = threw(() => theRecordWith('{not a record', [LINE]));
check('a record that is there and cannot be read refuses, and says so', damage instanceof TheRecordIsDamaged
  && damage.message.includes('cannot be read'));
check('a record in another shape refuses rather than reading the fields it recognises',
  threw(() => theRecordWith('{"shape": 99, "lines": []}', [LINE])) instanceof TheRecordIsDamaged);
check('a record holding a line that is not this writer\'s refuses',
  threw(() => theRecordWith('{"shape": 2, "lines": [{"dataDate": "2026-09-20", "reportId": "x", "state": "missing"}]}', [LINE]))
    instanceof TheRecordIsDamaged);
check('a shape-1 record (before reads existed) is read and kept',
  theLinesIn('{"shape": 1, "lines": []}').length === 0);
check('no text at all is a first landing, which is not damage', theLinesIn(null).length === 0 && theLinesIn('').length === 0);

const EXPECTED = 20;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}
console.log(failures ? `${failures} FAILED (${ran} checks)` : `all ${ran} checks passed`);
if (failures) process.exit(1);
