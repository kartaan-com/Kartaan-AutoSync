/* The extension's own record of what it landed in the seller's Drive (job 38).
 *
 * **ONE RECORD PER WRITER, AND THIS IS THE EXTENSION'S.** The run keeps `autosync-manifest.json`; this
 * keeps `extension-manifest.json`, beside it in `Kartaan / System`. Two writers on one file lose a line
 * whenever both save at the same minute -- each reads the whole file, changes its own lines and writes the
 * whole file back, so the later save puts the other's old lines back. With one writer per file there is
 * nothing to race: this file is written only here, replaced in place, and a reader joins the two
 * (`autosync/manifest.py` `cross_check`).
 *
 * **THE SHAPE IS THE RUN'S, LETTER FOR LETTER** -- `autosync/manifest.py` reads this file with the same
 * reader it reads its own with -- so a line here is a line there: report, data day, `verified`, the file's
 * name and size, and the day it was checked. A check holds the file name and the shape to the Python's.
 *
 * **ONLY `verified` IS EVER WRITTEN HERE.** This half lands files; it does not go and look for ones that did
 * not arrive. A day with no line is "nobody has checked", which is not the same as missing.
 *
 * **PURE, LIKE `drive.js` `theListWith`:** every rule below can be driven with no Drive and no token.
 */

/** What the file is called. The same words as `manifest.EXTENSION_FILE_NAME` in the Python. */
export const THE_EXTENSIONS_RECORD = 'extension-manifest.json';

/** Which shape of record this writes. The same number as `manifest.SHAPE`. */
export const THE_RECORDS_SHAPE = 2;

const A_DAY_IN_A_NAME = /(\d{4}-\d{2}-\d{2})/;

/** Is this a real calendar day, written as `YYYY-MM-DD`? */
function aRealDay(text) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return false;
  const made = new Date(`${text}T00:00:00Z`);
  return !Number.isNaN(made.getTime()) && made.toISOString().slice(0, 10) === text;
}

/** The data day inside a file's name, or '' when it has none. */
export function theDayInAName(fileName) {
  const found = A_DAY_IN_A_NAME.exec(String(fileName || ''));
  return found && aRealDay(found[1]) ? found[1] : '';
}

/** One line: this report's file for this day is really in the Drive. */
export function aLineFor({ reportId, fileName, size, day, on }) {
  if (!reportId || !fileName || !aRealDay(day)) return null;
  if (!(Number(size) > 0)) return null; // a file of nothing is not a file that arrived
  return {
    dataDate: day,
    reportId,
    state: 'verified',
    fileName,
    fileSize: Number(size),
    checkedOn: aRealDay(on) ? on : '',
  };
}

/** The lines for one landing: a file named by its day, or a running list holding many days. */
export function theLinesFor({ reportId, fileName, size, days, on }) {
  const inside = (days && days.length) ? days : [theDayInAName(fileName)];
  return inside
    .map((day) => aLineFor({ reportId, fileName, size, day, on }))
    .filter(Boolean);
}

/** Thrown when the record is there and cannot be read. **Never read as empty**: that would say nothing has
 *  ever landed, and the next save would write that over the seller's whole history. */
export class TheRecordIsDamaged extends Error {}

/** The lines already in the record's text, or nothing when there is no text yet. */
export function theLinesIn(text) {
  if (text === null || text === undefined || text === '') return [];
  let said;
  try {
    said = JSON.parse(text);
  } catch (wrong) {
    throw new TheRecordIsDamaged(`${THE_EXTENSIONS_RECORD} is there and cannot be read: ${wrong.message}`);
  }
  if (!said || typeof said !== 'object' || !Array.isArray(said.lines)) {
    throw new TheRecordIsDamaged(`${THE_EXTENSIONS_RECORD} is there and is not a record of this kind.`);
  }
  if (said.shape !== 1 && said.shape !== THE_RECORDS_SHAPE) {
    throw new TheRecordIsDamaged(
      `${THE_EXTENSIONS_RECORD} is written in shape ${said.shape} and this writes shape ${THE_RECORDS_SHAPE}.`
    );
  }
  for (const one of said.lines) {
    if (!one || !aRealDay(one.dataDate) || !one.reportId || one.state !== 'verified') {
      throw new TheRecordIsDamaged(`${THE_EXTENSIONS_RECORD} holds a line that is not one of this writer's.`);
    }
  }
  return said.lines;
}

/**
 * The record's text with these lines put in place, and nothing else moved.
 *
 * **ONE LINE PER (DAY, REPORT), REPLACED WHERE IT STANDS.** A day landed again replaces its own line; every
 * line not named comes through exactly as it was. Sorted, so the same landings always write the same bytes.
 */
export function theRecordWith(standingText, lines) {
  const kept = new Map();
  for (const one of theLinesIn(standingText)) kept.set(`${one.dataDate}|${one.reportId}`, one);
  for (const one of lines || []) kept.set(`${one.dataDate}|${one.reportId}`, one);
  const ordered = [...kept.values()].sort((a, b) => (
    a.dataDate === b.dataDate ? a.reportId.localeCompare(b.reportId) : a.dataDate.localeCompare(b.dataDate)
  ));
  return `${JSON.stringify({ shape: THE_RECORDS_SHAPE, reads: [], lines: ordered }, null, 1)}\n`;
}
