/* Checks for opening a zip for real (A53, 2026-09-16).
 *
 * Run: node extension/unzip.test.js
 *
 * **THE ONE THAT MATTERS MOST: a zip is opened, never renamed.** His Meesho payments
 * file landed as a zip under a spreadsheet's name. And an xlsx is itself a zip, so a
 * real spreadsheet must come through untouched.
 */

import { deflateRawSync } from 'node:zlib';
import {
  looksLikeAZip, theEntriesOf, theLatestDateInside, theSpreadsheetInside,
} from './unzip.js';

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

function check(name, passed) {
  ran++;
  console.log(`${passed ? 'PASS' : 'FAIL'}  ${name}`);
  if (!passed) failures++;
}

/** A real zip, built the way a zip is built: local entries, then the list, then its end. */
function aZip(entries) {
  const locals = [];
  const centrals = [];
  let offset = 0;
  for (const { name, text, stored = false } of entries) {
    const raw = Buffer.from(text);
    const packed = stored ? raw : deflateRawSync(raw);
    const nameBytes = Buffer.from(name);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(stored ? 0 : 8, 8);
    local.writeUInt32LE(packed.length, 18);
    local.writeUInt32LE(raw.length, 22);
    local.writeUInt16LE(nameBytes.length, 26);
    locals.push(local, nameBytes, packed);
    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(stored ? 0 : 8, 10);
    central.writeUInt32LE(packed.length, 20);
    central.writeUInt32LE(raw.length, 24);
    central.writeUInt16LE(nameBytes.length, 28);
    central.writeUInt32LE(offset, 42);
    centrals.push(central, nameBytes);
    offset += 30 + nameBytes.length + packed.length;
  }
  const list = Buffer.concat(centrals);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(entries.length, 8);
  end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(list.length, 12);
  end.writeUInt32LE(offset, 16);
  return new Uint8Array(Buffer.concat([...locals, list, end]));
}

const inside = 'the spreadsheet inside, with its own rows';
const wrapped = aZip([{ name: '1244938_SP_ORDER_ADS_REFERRAL_PAYMENT_FILE_PREVIOUS_PAYMENT_2026-09-14.xlsx', text: inside }]);

check('a zip is recognised by its first bytes', looksLikeAZip(wrapped));
check('and its entries are read from its own list',
  theEntriesOf(wrapped).map((one) => one.name).join() === '1244938_SP_ORDER_ADS_REFERRAL_PAYMENT_FILE_PREVIOUS_PAYMENT_2026-09-14.xlsx');

const opened = await theSpreadsheetInside('meesho_me_payments_2026-09-14.xlsx', wrapped);
check('a zip holding one spreadsheet is opened for real, not renamed',
  new TextDecoder().decode(opened) === inside);

const storedOpen = await theSpreadsheetInside('a.xlsx', aZip([{ name: 'b.xlsx', text: inside, stored: true }]));
check('and so is one stored without compression', new TextDecoder().decode(storedOpen) === inside);

const realXlsx = aZip([{ name: '[Content_Types].xml', text: '<Types/>' }, { name: 'xl/workbook.xml', text: '<w/>' }]);
check('a real spreadsheet, which is itself a zip, comes through untouched',
  (await theSpreadsheetInside('a.xlsx', realXlsx)) === realXlsx);

const csv = new TextEncoder().encode('a,b\n1,2\n');
check('and a file that is not a zip at all comes through untouched',
  (await theSpreadsheetInside('a.csv', csv)) === csv);

let refused = '';
try {
  await theSpreadsheetInside('a.xlsx', aZip([{ name: 'one.xlsx', text: 'x' }, { name: 'two.xlsx', text: 'y' }]));
} catch (wrong) { refused = wrong.message; }
check('a zip holding more than one file is refused in words, never guessed at',
  refused.includes('one.xlsx') && refused.includes('not one spreadsheet'));

const sheet = aZip([
  { name: '[Content_Types].xml', text: '<Types/>' },
  { name: 'xl/worksheets/sheet1.xml', text: '<row><c>2026-09-01</c></row><row><c>2026-09-03</c></row>' },
  { name: 'xl/sharedStrings.xml', text: '<si><t>2026-09-02</t></si>' },
]);
check('the latest day written inside a spreadsheet is read from its sheet and its shared text',
  (await theLatestDateInside(sheet)) === '2026-09-03');

const onlyBegins = new Uint8Array([80, 75, 3, 4]);
check('something that only begins like a zip, with no list of contents, comes through untouched',
  (await theSpreadsheetInside('a.xlsx', onlyBegins)) === onlyBegins);

const EXPECTED = 9;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}
console.log(failures ? `${failures} FAILED (${ran} checks)` : `all ${ran} checks passed`);
if (failures) process.exit(1);
