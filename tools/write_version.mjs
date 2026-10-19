/* Writes `version.json`, the file that tells every installed copy a newer extension is out (A82, 2026-10-20).
 *
 * Copied from Kartaan Click's release (`D:\kartaan-click\tools\release.js:43-67, 206-232`): the file is written HERE,
 * from the manifest that was just released, so it cannot disagree with the release and cannot be forgotten.
 *
 * Run, as the LAST step of a release, after the GitHub release and its ZIP exist:
 *   node tools/write_version.mjs "One line about what is new"
 *   git add version.json && git commit -m "Announce <version>" && git push
 *
 * **LAST, NOT FIRST.** Pushed before the release exists, it tells every seller to download a ZIP that is not there.
 * **AND IT REFUSES TO STACK ON A RELEASE NEVER ANNOUNCED**: a leftover, uncommitted `version.json` naming an older
 * version means that release was built and nobody was told.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

export const ZIP = 'https://github.com/kartaan-com/Kartaan-AutoSync/releases/latest/download/kartaan-autosync-extension.zip';

/** What the file holds, and nothing else. An empty note is left empty rather than guessed at. */
export function theVersionFile(manifest, note) {
  return { version: String(manifest.version), url: ZIP, notes: String(note || '').trim() };
}

/** The reason a release must not be announced yet, or null. `status` is `git status --porcelain`. */
export function whyNotToAnnounce(status, announced, version) {
  const leftover = status.split('\n').some((line) => /\sversion\.json$/.test(line));
  if (leftover && announced && announced !== version) {
    return `version.json still says ${announced} and has never been committed, so that release was built but never `
      + `announced. Commit it first (git add version.json && git commit -m "Announce ${announced}" && git push), `
      + `only if the ${announced} release really exists on GitHub.`;
  }
  return null;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const root = new URL('..', import.meta.url);
  const manifest = JSON.parse(readFileSync(new URL('extension/manifest.json', root), 'utf8'));
  const file = new URL('version.json', root);
  let announced = null;
  try { announced = JSON.parse(readFileSync(file, 'utf8')).version; } catch (wrong) { /* none yet */ }
  const status = execFileSync('git', ['status', '--porcelain'], { cwd: fileURLToPath(root), encoding: 'utf8' });
  const refused = whyNotToAnnounce(status, announced, manifest.version);
  if (refused) {
    console.error(`NOT ANNOUNCING -- ${refused}`);
    process.exit(1);
  }
  const note = process.argv[2] || '';
  writeFileSync(file, `${JSON.stringify(theVersionFile(manifest, note), null, 2)}\n`);
  console.log(`version.json written (${manifest.version}).${note ? '' : ' NO NOTE given: the notice will show the version alone.'}`);
  console.log('Now, LAST: git add version.json && git commit -m "Announce ' + manifest.version + '" && git push');
}
