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
  THE_EXTENSIONS_RECORD_STARTS, THE_RECORDS_SHAPE, aFreshInstallId, theRecordNameFor, TheRecordIsDamaged, aLineFor, theDayInAName, theLinesFor, theLinesIn,
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
check("every install record starts with what the Python says the extension records start with",
  PYTHON.includes(`EXTENSION_FILE_PREFIX = "${THE_EXTENSIONS_RECORD_STARTS}"`));
check("and the name is built to the pattern the Python recognises one by",
  PYTHON.includes('EXTENSION_FILE_SHAPE = r"extension-manifest-[0-9a-f]{8}')
  && /^extension-manifest-[0-9a-f]{8}[.]json$/.test(theRecordNameFor('0a1b2c3d')));
check("an install id is eight lowercase hex digits, a fresh one every time it is made",
  /^[0-9a-f]{8}$/.test(aFreshInstallId()) && aFreshInstallId() !== aFreshInstallId());
check("an id that is not one makes no name, so no stray file is ever written",
  [undefined, '', 'XYZ', '0A1B2C3D', '0a1b2c3', '0a1b2c3dd'].every((one) => {
    try { theRecordNameFor(one); return false; } catch (wrong) { return true; }
  }));
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
check('a written row is recorded for the days it reports, not for the day it was last touched',
  theLinesFor({
    reportId: 'me_views', fileName: 'meesho_me_views_2026-09-19.csv', size: 90, days: ['2026-09-19'], on: '2026-09-22',
  }).map((one) => one.dataDate).join() === '2026-09-19');
check('and a file named by its day is recorded for that day',
  theLinesFor({ reportId: 'me_orders', fileName: 'meesho_me_orders_2026-09-20.csv', size: 5 })
    .map((one) => one.dataDate).join() === '2026-09-20');

check('A RANGE FILE IS RECORDED FOR EVERY DAY IT NAMES, not for its first day alone (P16)',
  theLinesFor({ reportId: 'fk_orders', fileName: 'flipkart_fk_orders_2026-09-29_to_2026-10-03.xlsx', size: 5 })
    .map((one) => one.dataDate).join() === '2026-09-29,2026-09-30,2026-10-01,2026-10-02,2026-10-03');
check('and a name that only looks like a range is recorded for no day at all',
  theLinesFor({ reportId: 'fk_orders', fileName: 'flipkart_fk_orders_2026-10-03_to_2026-09-29.xlsx', size: 5 }).length === 0);

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

/* ---------------------------------------------------- AS7a: the pipeline's own record, read for what it verified */
{
  const { THE_PIPELINES_RECORD, theVerifiedDaysIn } = await import('./record.js');
  const line = (day, report, state) => ({ dataDate: day, reportId: report, state, fileName: 'x', fileSize: 5, checkedOn: day });
  const mixed = JSON.stringify({ shape: 2, reads: [], lines: [line('2026-11-01', 'az_suppressed', 'verified'), line('2026-11-02', 'az_suppressed', 'missing')] });
  check('AS7a: the pipeline record is named as the Python names it', THE_PIPELINES_RECORD === 'autosync-manifest.json'
    && readFileSync(new URL('../autosync/manifest.py', import.meta.url), 'utf8').includes(`FILE_NAME = "${THE_PIPELINES_RECORD}"`));
  const read = theVerifiedDaysIn(mixed);
  check('AS7a: a verified day is read, a missing line is not counted as landed', read && read.days.az_suppressed.join() === '2026-11-01');
  check('AS7a: text that is not JSON is "nobody has checked" (null), never an empty answer', theVerifiedDaysIn('{not a record') === null && theVerifiedDaysIn('') === null);
  check('AS7a: a record in a shape this does not know, or without lines, is null', theVerifiedDaysIn('{"shape": 99, "lines": []}') === null && theVerifiedDaysIn('{"shape": 2}') === null);
  check('AS7a: one line that is not the pipeline\'s (an unknown state) makes the whole record null',
    theVerifiedDaysIn(JSON.stringify({ shape: 2, lines: [line('2026-11-01', 'a', 'verified'), line('2026-11-01', 'b', 'maybe')] })) === null);
  check('AS7a: a record of over 50000 lines, or a report id that is not text, is null',
    theVerifiedDaysIn(JSON.stringify({ shape: 2, lines: new Array(50001).fill(line('2026-11-01', 'a', 'verified')) })) === null
    && theVerifiedDaysIn(JSON.stringify({ shape: 2, lines: [{ ...line('2026-11-01', 'a', 'verified'), reportId: { x: 1 } }] })) === null);
  check('AS7a: a report id like __proto__ is only a key, and pollutes nothing',
    theVerifiedDaysIn(JSON.stringify({ shape: 2, lines: [line('2026-11-01', '__proto__', 'verified')] })).days.__proto__.join() === '2026-11-01'
    && ({}).polluted === undefined && Object.getPrototypeOf(theVerifiedDaysIn('{"shape":2,"lines":[]}').days) === null);
  const day = '2026-11-01';
  const wrongs = [
    ['the same day and report twice', [line(day, 'a', 'missing'), line(day, 'a', 'verified')]],
    ['a verified file of nothing', [{ ...line(day, 'a', 'verified'), fileSize: 0 }]],
    ['a verified line with no file name', [{ ...line(day, 'a', 'verified'), fileName: '' }]],
    ['a size that is not a number', [{ ...line(day, 'a', 'verified'), fileSize: 'big' }]],
    ['a check date that is not a day', [{ ...line(day, 'a', 'verified'), checkedOn: 'yesterday' }]],
  ];
  for (const [what, lines] of wrongs) {
    check(`AS7a: ${what} is a record the Python calls damaged: null`, theVerifiedDaysIn(JSON.stringify({ shape: 2, lines })) === null);
  }
  const okRead = { dataDate: day, reportId: 'a', fileName: 'x', into: 'sheet', rowsInFile: 3, rowsRead: 3 };
  const withReads = (reads) => JSON.stringify({ shape: 2, lines: [line(day, 'a', 'verified')], reads });
  check('AS7a: a good reads list is kept and the day is read', theVerifiedDaysIn(withReads([okRead])).days.a.join() === day);
  for (const [what, reads] of [
    ['a read that is junk', [{ junk: 1 }]], ['reads that is not a list', 5],
    ['more rows read than in the file', [{ ...okRead, rowsRead: 4 }]], ['a read counted in fractions', [{ ...okRead, rowsInFile: 2.5, rowsRead: 1 }]],
    ['the same read twice', [okRead, okRead]], ['a read that says nowhere it went', [{ ...okRead, into: '' }]],
  ]) {
    check(`AS7a: ${what} is a record the Python calls damaged: null`, theVerifiedDaysIn(withReads(reads)) === null);
  }
  check('AS7a: a fractional size that the Python reads as nought is null',
    theVerifiedDaysIn(JSON.stringify({ shape: 2, lines: [{ ...line(day, 'a', 'verified'), fileSize: 0.5 }] })) === null);
}

const EXPECTED = 45;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}
console.log(failures ? `${failures} FAILED (${ran} checks)` : `all ${ran} checks passed`);
if (failures) process.exit(1);
