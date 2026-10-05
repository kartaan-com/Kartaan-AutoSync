/* Writes `extension/catch-early.js` out of `extension/catch-blob.js`.
 *
 * **ONE RECORD OF THE CATCHER, NOT TWO.** A content script cannot be an ES
 * module and cannot be handed an argument, so the catcher that loads on every
 * Flipkart page at `document_start` cannot simply import `catchTheNextFile`.
 * Copied by hand, the two would drift -- the page would catch by one rule and the
 * background arm by another, and a report would stop arriving with both halves
 * doing exactly what they say. So the early file is written from the function's
 * own source, the same source `chrome.scripting.executeScript` sends, and
 * `extension/background.test.js` fails if it has fallen behind.
 *
 * Run: node tools/write_catch_early.mjs
 */

import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { catchTheNextFile } from '../extension/catch-blob.js';

export const THE_EARLY_FILE = new URL('../extension/catch-early.js', import.meta.url);

export function whatTheEarlyFileHolds() {
  return '/* GENERATED from extension/catch-blob.js by tools/write_catch_early.mjs.\n'
    + ' * Do not edit by hand -- change catchTheNextFile and run the tool again.\n'
    + ' *\n'
    + " * Loaded on every Flipkart page in the page's own world at document_start, so\n"
    + ' * it is in place before any Flipkart script can take its own copy of the\n'
    + ' * functions it watches. Installed switched off: nothing is caught until the\n'
    + ' * background arms it with a fresh secret for one file. */\n'
    + `(${catchTheNextFile.toString()})(null);\n`;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  writeFileSync(THE_EARLY_FILE, whatTheEarlyFileHolds());
  console.log('wrote extension/catch-early.js');
}
