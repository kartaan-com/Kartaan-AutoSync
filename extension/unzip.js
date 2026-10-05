/* Opening a zip, for real (A53, 2026-09-16).
 *
 * **HIS RULING:** *"Unzipping, yes, that is very much needed. I am not saying that
 * you rename from .zip to .xlsx. It should be unzipping in the real sense."*
 * Measured the same day: `meesho_me_payments_2026-09-14.xlsx` in his Drive was a
 * zip holding one spreadsheet, landed under a spreadsheet's name.
 *
 * **RUMEE'S WAY, WITH ITS ONE FAULT TAKEN OUT.** Rumee inflates the first entry with
 * `DecompressionStream('deflate-raw')` (`D:\rumee-auto-sync\background.js:1271-1326`)
 * and takes the first entry blindly. Here the entries are read from the zip's own
 * list at its end, and a zip holding more than one file is refused in words.
 *
 * **AN XLSX IS ITSELF A ZIP**, which is what corrupted Rumee's files before it guarded
 * on the report's type. A real spreadsheet carries `[Content_Types].xml`; that is how
 * the two are told apart here, by what is inside rather than by a name.
 */

const LOCAL_HEADER = 0x04034b50;
const CENTRAL_ENTRY = 0x02014b50;
const END_OF_LIST = 0x06054b50;
const A_SPREADSHEET = /\.(xlsx|xls|csv)$/i;

/** Does this begin like a zip? */
export function looksLikeAZip(bytes) {
  return Boolean(bytes) && bytes.length >= 4
    && new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength).getUint32(0, true) === LOCAL_HEADER;
}

/** Does this carry a zip's list of contents at its end? */
function hasAListAtItsEnd(bytes) {
  if (bytes.length < 22) return false;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  for (let at = bytes.length - 22; at >= Math.max(0, bytes.length - 22 - 0xffff); at -= 1) {
    if (view.getUint32(at, true) === END_OF_LIST) return true;
  }
  return false;
}

/** Every entry in a zip, read from its central list: name, method, sizes, offset. */
export function theEntriesOf(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let end = -1;
  for (let at = bytes.length - 22; at >= Math.max(0, bytes.length - 22 - 0xffff); at -= 1) {
    if (view.getUint32(at, true) === END_OF_LIST) { end = at; break; }
  }
  if (end < 0) throw new Error('This zip has no list of what is inside it, so it cannot be opened.');
  const count = view.getUint16(end + 10, true);
  let at = view.getUint32(end + 16, true);
  const entries = [];
  for (let n = 0; n < count; n += 1) {
    if (view.getUint32(at, true) !== CENTRAL_ENTRY) {
      throw new Error('This zip\'s list of what is inside it is damaged, so it cannot be opened.');
    }
    const nameLength = view.getUint16(at + 28, true);
    const extraLength = view.getUint16(at + 30, true);
    const commentLength = view.getUint16(at + 32, true);
    entries.push({
      method: view.getUint16(at + 10, true),
      compressedSize: view.getUint32(at + 20, true),
      size: view.getUint32(at + 24, true),
      offset: view.getUint32(at + 42, true),
      name: new TextDecoder().decode(bytes.subarray(at + 46, at + 46 + nameLength)),
    });
    at += 46 + nameLength + extraLength + commentLength;
  }
  return entries;
}

/** The bytes of one entry, inflated when they were compressed. */
export async function theBytesOf(bytes, entry) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (view.getUint32(entry.offset, true) !== LOCAL_HEADER) {
    throw new Error(`${entry.name} is not where this zip says it is, so it cannot be opened.`);
  }
  const start = entry.offset + 30 + view.getUint16(entry.offset + 26, true)
    + view.getUint16(entry.offset + 28, true);
  const packed = bytes.subarray(start, start + entry.compressedSize);
  if (entry.method === 0) return packed.slice();
  if (entry.method !== 8) {
    throw new Error(`${entry.name} is packed a way this cannot open (method ${entry.method}).`);
  }
  const opened = new Response(new Blob([packed]).stream()
    .pipeThrough(new DecompressionStream('deflate-raw')));
  return new Uint8Array(await opened.arrayBuffer());
}

/**
 * The latest day written inside a spreadsheet, as `YYYY-MM-DD`, or '' when none.
 *
 * Rumee's `_fkViewsActualMaxDate` reads sheet one for dates
 * (`D:\rumee-auto-sync\content\flipkart.js:2512-2520`); the shared text of the sheet is
 * read as well, because a spreadsheet may keep its words there.
 */
export async function theLatestDateInside(bytes) {
  if (!looksLikeAZip(bytes) || !hasAListAtItsEnd(bytes)) return '';
  const wanted = theEntriesOf(bytes)
    .filter((one) => /^xl\/(worksheets\/sheet\d+|sharedStrings)\.xml$/.test(one.name));
  let latest = '';
  for (const entry of wanted) {
    // eslint-disable-next-line no-await-in-loop
    const text = new TextDecoder().decode(await theBytesOf(bytes, entry));
    for (const day of text.match(/\d{4}-\d{2}-\d{2}/g) || []) if (day > latest) latest = day;
  }
  return latest;
}

/**
 * What goes to Drive for a file that should be a spreadsheet.
 *
 * A real spreadsheet, or anything that is not a zip, comes back as it came. A zip
 * holding exactly one spreadsheet comes back as that spreadsheet, opened. A zip
 * holding anything else is refused, so nothing is landed under a name it is not.
 */
export async function theSpreadsheetInside(fileName, bytes) {
  if (!A_SPREADSHEET.test(String(fileName || '')) || !looksLikeAZip(bytes)) return bytes;
  /* **NO LIST OF CONTENTS, NOT A ZIP TO OPEN.** Something that only begins like one
   * is left exactly as it came; what it really is, is not this step's to judge. */
  if (!hasAListAtItsEnd(bytes)) return bytes;
  const entries = theEntriesOf(bytes);
  if (entries.some((one) => one.name === '[Content_Types].xml')) return bytes;
  const files = entries.filter((one) => !one.name.endsWith('/'));
  if (files.length !== 1 || !A_SPREADSHEET.test(files[0].name)) {
    throw new Error(`${fileName} came as a zip holding ${files.map((one) => one.name).join(', ') || 'nothing'}, `
      + 'not one spreadsheet, so it has not been put in the Drive.');
  }
  return theBytesOf(bytes, files[0]);
}
