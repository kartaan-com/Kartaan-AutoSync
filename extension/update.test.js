/* Checks for "a newer version is out" (A82, 2026-10-20; copied from Kartaan Click's way).
 *
 * Run: node extension/update.test.js
 *
 * **THE ONE THAT MATTERS MOST: the notice is worked out against the version installed NOW**, so somebody who has
 * just updated is not told for a day that the version they are running is available.
 */

import { readFileSync } from 'node:fs';
import { installFakeChrome } from '../test/fake-chrome.js';
import { ZIP as THE_ZIP, theVersionFile, whyNotToAnnounce } from '../tools/write_version.mjs';
import {
  CHECK_EVERY_MS, THE_UPDATE, VERSION_URL, checkForUpdate, isNewer, safeLink, theUpdateNotice,
} from './update.js';

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

const ZIP = 'https://github.com/kartaan-com/Kartaan-AutoSync/releases/latest/download/kartaan-autosync-extension.zip';
const answering = (body, ok = true, status = 200) => async () => ({ ok, status, json: async () => body });

check('0.1.10 is newer than 0.1.9, which comparing them as text would get wrong', isNewer('0.1.10', '0.1.9'));
check('the same version is not newer', !isNewer('0.1.17', '0.1.17'));
check('an older one is not newer', !isNewer('0.1.9', '0.1.17'));
check('an ordinary GitHub address is kept', safeLink(ZIP) === ZIP);
check('a javascript: address is dropped', safeLink('javascript:alert(1)') === '');
check('an insecure address is dropped', safeLink('http://github.com/x') === '');
check('and so is a secure address somewhere other than GitHub', safeLink('https://evil.example/x.zip') === '');
check('and so is another account releases on GitHub, which the banner would lend our name to',
  safeLink('https://github.com/attacker/x/releases/download/v1/kartaan-autosync-extension.zip') === '');

{
  const { chrome } = installFakeChrome();
  const asked = [];
  await checkForUpdate(chrome, {
    fetch: async (address, how) => { asked.push(address); return answering({ version: '0.1.18', url: ZIP, notes: 'Fixed.' })(address, how); },
    now: 1000,
  });
  check('it reads exactly one address, the version file', asked.length === 1 && asked[0] === VERSION_URL);
  const out = await theUpdateNotice(chrome, { installed: '0.1.17', now: 2000 });
  check('a later version in the file is announced, with its link and its note',
    out.updateAvailable && out.latest === '0.1.18' && out.url === ZIP && out.notes === 'Fixed.');
  const updated = await theUpdateNotice(chrome, { installed: '0.1.18', now: 3000 });
  check('and once the seller has installed it the notice goes, though the answer is still kept', !updated.updateAvailable);
}

{
  const { chrome } = installFakeChrome();
  await checkForUpdate(chrome, { fetch: answering({ version: '0.1.18', url: ZIP }), now: 1000 });
  await checkForUpdate(chrome, { fetch: answering({}, false, 404), now: 2000 });
  const kept = (await chrome.storage.local.get(THE_UPDATE))[THE_UPDATE];
  check('a failed ask keeps what was last known and says why, never pretending all is well',
    kept.latest === '0.1.18' && kept.error.includes('404') && kept.checkedAt === 2000);
  await checkForUpdate(chrome, { fetch: async () => { throw new Error('offline'); }, now: 3000 });
  check('and being offline is the same, without throwing',
    (await chrome.storage.local.get(THE_UPDATE))[THE_UPDATE].error === 'offline');
  await checkForUpdate(chrome, { fetch: answering({ url: ZIP }), now: 4000 });
  check('a file with no version in it is a failure, not an announcement',
    (await chrome.storage.local.get(THE_UPDATE))[THE_UPDATE].error.includes('no usable version'));
  await checkForUpdate(chrome, { fetch: answering({ version: '999.0.0-evil', url: ZIP }), now: 5000 });
  check('and so is a version that is not three plain numbers',
    (await chrome.storage.local.get(THE_UPDATE))[THE_UPDATE].latest === '0.1.18');
  await checkForUpdate(chrome, { fetch: answering({ version: '0.1.19', notes: 'x'.repeat(900) }), now: 6000 });
  check('and a note is cut to one short line',
    (await chrome.storage.local.get(THE_UPDATE))[THE_UPDATE].notes.length === 200);
}

{
  const { chrome } = installFakeChrome();
  let asks = 0;
  const counting = async () => { asks += 1; return { ok: true, status: 200, json: async () => ({ version: '0.1.17', url: ZIP }) }; };
  await theUpdateNotice(chrome, { installed: '0.1.17', fetch: counting, now: 10 });
  await new Promise((resolve) => setTimeout(resolve, 20));
  await theUpdateNotice(chrome, { installed: '0.1.17', fetch: counting, now: 20 });
  await new Promise((resolve) => setTimeout(resolve, 20));
  check('a day-old answer starts a fresh ask in the background and a fresh one does not', asks === 1);
  await theUpdateNotice(chrome, { installed: '0.1.17', fetch: counting, now: 20 + CHECK_EVERY_MS });
  await new Promise((resolve) => setTimeout(resolve, 20));
  check('and a day later it asks again', asks === 2);
}

{
  const manifest = JSON.parse(readFileSync(new URL('./manifest.json', import.meta.url), 'utf8'));
  check('the address the notice reads is the one the manifest lets the extension reach',
    manifest.host_permissions.some((one) => VERSION_URL.startsWith(one.replace(/\*$/, ''))));
  check('and the manifest names a real version, so the notice has something to compare',
    /^0\.1\.\d+$/.test(manifest.version) && manifest.version !== '0.1.0');
}

{
  /* **THE RELEASE WRITES THE FILE, and refuses to stack on one never announced** (Click's `release.js`). */
  const file = theVersionFile({ version: '0.1.17' }, ' Fixed. ');
  check('the file holds the version, the download link and the note, and nothing else',
    JSON.stringify(Object.keys(file)) === '["version","url","notes"]' && file.version === '0.1.17'
    && file.url === THE_ZIP && file.notes === 'Fixed.');
  check('the link it writes is the one the extension would keep', safeLink(file.url) === file.url);
  check('a leftover version.json naming an older release refuses the next announcement',
    String(whyNotToAnnounce(' M version.json', '0.1.16', '0.1.17')).includes('never announced'));
  check('but one naming this very release, or none, does not',
    whyNotToAnnounce(' M version.json', '0.1.17', '0.1.17') === null
    && whyNotToAnnounce('', '0.1.16', '0.1.17') === null);
}

const EXPECTED = 24;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}
console.log(failures ? `${failures} FAILED (${ran} checks)` : `all ${ran} checks passed`);
if (failures) process.exit(1);
