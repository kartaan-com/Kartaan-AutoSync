/* "A newer version is out" -- copied from Kartaan Click (`D:\kartaan-click\background.js:86-150`), not redesigned.
 *
 * **ONE ADDRESS, READ ONLY.** `version.json` in this extension's own public repository, written and pushed LAST by
 * `tools/write_version.mjs` as part of a release, so it can never name a version whose download does not exist yet.
 * It sends no body and nothing of the seller's. Nothing else is called from here.
 *
 *   { "version": "0.1.17",
 *     "url": "https://github.com/kartaan-com/Kartaan-AutoSync/releases/latest/download/kartaan-autosync-extension.zip",
 *     "notes": "One line about what is new" }
 */

export const VERSION_URL = 'https://raw.githubusercontent.com/kartaan-com/Kartaan-AutoSync/main/version.json';
export const THE_UPDATE = 'kartaan-autosync-update';
/** Once a day is plenty. */
export const CHECK_EVERY_MS = 24 * 60 * 60 * 1000;

/** A link is kept only if it is an ordinary secure address on GitHub; anything else is dropped and the notice shows
 *  no link, because a notice with no link is a nuisance and a bad one is a hazard. */
export function safeLink(raw) {
  try {
    const link = new URL(String(raw || ''));
    return link.protocol === 'https:' && link.hostname === 'github.com' ? link.href : '';
  } catch (wrong) {
    return '';
  }
}

/** Is `a` a later version than `b`? Part by part, so 0.1.10 beats 0.1.9, which comparing them as text would not. */
export function isNewer(a, b) {
  const left = String(a || '').split('.').map((one) => parseInt(one, 10) || 0);
  const right = String(b || '').split('.').map((one) => parseInt(one, 10) || 0);
  for (let i = 0; i < Math.max(left.length, right.length); i += 1) {
    const x = left[i] || 0;
    const y = right[i] || 0;
    if (x !== y) return x > y;
  }
  return false;
}

let asking = false;

/** Ask the repository what is newest and keep the answer. Never throws; a failed ask keeps what was last known and
 *  says why, and being offline is not shown as an alarm. */
export async function checkForUpdate(chrome, { fetch, now = Date.now() }) {
  if (asking) return;
  asking = true;
  try {
    const before = (await chrome.storage.local.get(THE_UPDATE))[THE_UPDATE] || {};
    let kept;
    try {
      const reply = await fetch(VERSION_URL, { cache: 'no-store' });
      if (!reply.ok) throw new Error(`the server answered ${reply.status}`);
      const data = await reply.json();
      const latest = String(data.version || '');
      if (!latest) throw new Error('no version in the file');
      kept = {
        checkedAt: now, latest, url: safeLink(data.url), notes: String(data.notes || ''), error: '',
      };
    } catch (wrong) {
      kept = { ...before, checkedAt: now, error: (wrong && wrong.message) || String(wrong) };
    }
    await chrome.storage.local.set({ [THE_UPDATE]: kept });
  } finally {
    asking = false;
  }
}

/**
 * What the panel shows about versions, read from what was last kept, and a fresh ask started in the background when
 * the answer is a day old. **WORKED OUT AGAIN AGAINST THE VERSION INSTALLED NOW**, or somebody who has just updated is
 * told for a day that the version they are running is available.
 */
export async function theUpdateNotice(chrome, { installed, fetch = null, now = Date.now() }) {
  const kept = (await chrome.storage.local.get(THE_UPDATE))[THE_UPDATE] || {};
  if (fetch && (!kept.checkedAt || now - kept.checkedAt >= CHECK_EVERY_MS)) {
    checkForUpdate(chrome, { fetch, now }).catch(() => {});
  }
  return {
    installed: String(installed || ''),
    latest: String(kept.latest || ''),
    url: kept.url || '',
    notes: kept.notes || '',
    updateAvailable: isNewer(kept.latest, installed),
  };
}
