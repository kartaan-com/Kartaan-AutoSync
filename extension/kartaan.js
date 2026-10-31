/* Talking to Kartaan's server: may this sync fetch, and this sync has finished (plan jobs 30 and 48, extension half).
 *
 * **WHY THE EXTENSION ASKS AT ALL.** A seller's fetching used to start on Chrome's own alarm and ask Kartaan
 * nothing, so a trial that ended unpaid went on fetching. The server now answers `POST /may-fetch` with the seller's
 * run pass, and `POST /finished` starts the seller's own GitHub run once the browser half has put its files in Drive
 * (Kartaan-Server v0.1.9, `server/fetching.py` and `server/starting_a_run.py`). Both take a FORM, not JSON.
 *
 * **THE RUN PASS IS PASTED BY THE SELLER, NEVER FETCHED.** It is copied from Kartaan's page (`/run-pass`) into the
 * panel. It is a credential for one pipeline, so: kept under its own storage key and nowhere else; trimmed of the
 * space and line break a paste brings; refused in words when empty or over the 1024 characters the server reads;
 * **NEVER SHOWN BACK, NEVER LOGGED, NEVER WRITTEN INTO A NIGHT, A LOG OR A SENTENCE.** The only things that leave this
 * file about it are "saved" or "not saved". Every sentence that comes back from the server is checked for the pass
 * before it is stored or shown, because a server that echoed one would otherwise put it on the seller's screen.
 *
 * **EVERY WAY OUT SAYS SOMETHING.** Not reachable, no answer in fifteen seconds, an answer that is not JSON, JSON of
 * a shape the server does not send: each comes back as plain words for the seller's screen, with a `kind` for the
 * code to decide on. A silent nothing is how a seller's sync stops with no reason anywhere, which is the fault this
 * whole product is built against.
 *
 * **NOTHING HERE OPENS A CONNECTION ON ITS OWN (Golden Rule 1).** `fetchImpl` is handed in, so every answer and every
 * sentence is checked with nothing connected. No fetch handed in reads as "could not be reached", never as a real call.
 *
 * **NOTHING HERE THROWS AT ITS CALLER.** What it is asked about -- starting a sync, ending one -- must never be broken
 * by this file having a bad day.
 */

export const KARTAAN = 'https://api.kartaan.com';
export const MAY_FETCH_ADDRESS = `${KARTAAN}/may-fetch`;
export const FINISHED_ADDRESS = `${KARTAAN}/finished`;

/** Where the pass is kept. Its own key: nothing else reads it and nothing else is written beside it. */
export const THE_RUN_PASS = 'kartaan-autosync-run-pass';
/** What Kartaan last said, in words only -- never the pass. The panel shows it. */
export const KARTAAN_LAST_SAID = 'kartaan-autosync-kartaan-last-said';

/** The most the server reads of a pass (`run_pass`, 1024). Over this the server would refuse it unread. */
export const PASS_AT_MOST = 1024;
/** **THE SERVER'S OWN LIMITS ON `failed`** (`starting_a_run.py`: `LOOKS_LIKE_A_REPORT`, `AT_MOST_FAILED`). */
const LOOKS_LIKE_A_REPORT = /^[a-z][a-z0-9_]{0,39}$/;
export const AT_MOST_FAILED = 40;
/** How long to wait for Kartaan before saying it could not be reached. */
export const WAIT_AT_MOST_MS = 15000;
const SAID_AT_MOST = 600;

const STILL_RUNS = 'The run still runs on its own schedule.';

/* -------------------------------------------------------------- the pass */

/**
 * Why this is not a run pass, in words -- or '' when it may be kept. The trimmed text is what is kept.
 */
export function whyThatIsNotARunPass(raw) {
  const pass = String(raw === undefined || raw === null ? '' : raw).trim();
  if (!pass) {
    return 'The run pass box is empty. Copy the run pass from Kartaan\'s page, paste it here, then press Save.';
  }
  if (pass.length > PASS_AT_MOST) {
    return `That is longer than a run pass can be (${PASS_AT_MOST} characters at most), so it was not `
      + 'saved. Copy the run pass again from Kartaan\'s page, only the pass itself.';
  }
  if (/\s/.test(pass)) {
    return 'That has a space or a line break inside it, and a run pass has none, so it was not saved. '
      + 'Copy the whole run pass again from Kartaan\'s page.';
  }
  return '';
}

/** Keep the pass, or refuse it in words. Answers `{ saved: true }` or `{ wrong }`; never the pass. */
export async function saveTheRunPass(chrome, raw) {
  const wrong = whyThatIsNotARunPass(raw);
  if (wrong) return { wrong };
  await chrome.storage.local.set({ [THE_RUN_PASS]: String(raw).trim() });
  return { saved: true };
}

async function thePass(chrome) {
  const held = await chrome.storage.local.get(THE_RUN_PASS);
  const pass = held[THE_RUN_PASS];
  return typeof pass === 'string' && pass && !whyThatIsNotARunPass(pass) ? pass : '';
}

/** Whether a pass is saved. A yes or a no, and nothing of the pass. */
export async function isARunPassSaved(chrome) {
  return Boolean(await thePass(chrome));
}

/* ------------------------------------------------------------ what was said */

/** A sentence of Kartaan's or this file's, kept short and with the pass taken out of it if it somehow got in. */
function cleaned(text, pass) {
  let said = String(text === undefined || text === null ? '' : text).replace(/\s+/g, ' ').trim();
  if (pass && said.includes(pass)) said = said.split(pass).join('[run pass]');
  return said.length > SAID_AT_MOST ? `${said.slice(0, SAID_AT_MOST)}...` : said;
}

async function rememberWhatWasSaid(chrome, what) {
  try {
    await chrome.storage.local.set({ [KARTAAN_LAST_SAID]: what });
  } catch (wrong) {
    /* Words for the panel only; a store that refuses must not stop a sync. */
  }
}

/** What Kartaan last said and whether a pass is saved -- the whole of what the panel is told about Kartaan. */
export async function whatKartaanLastSaid(chrome) {
  const saved = await isARunPassSaved(chrome);
  const held = await chrome.storage.local.get(KARTAAN_LAST_SAID);
  const last = held[KARTAAN_LAST_SAID];
  return {
    saved,
    last: last && typeof last === 'object'
      ? { at: Number(last.at) || 0, kind: String(last.kind || ''), said: String(last.said || '') }
      : null,
  };
}

/* ------------------------------------------------------- one call, one way */

/**
 * POST a form to Kartaan and read the answer. **Answers `{ kind, status, body, said }`, never throws.**
 * `kind` is 'answered' (a JSON object came back), 'unreachable' (no answer, or nothing in time) or 'garbled'
 * (an answer that is not a JSON object).
 */
async function postForm(fetchImpl, address, fields, timeoutMs) {
  if (typeof fetchImpl !== 'function') {
    return { kind: 'unreachable', said: 'Kartaan could not be reached from here (no way to connect was given).' };
  }
  const controller = typeof AbortController === 'function' ? new AbortController() : null;
  let timer = null;
  const tooLong = new Promise((resolve) => {
    timer = setTimeout(() => {
      if (controller) controller.abort();
      resolve({ kind: 'unreachable', timedOut: true });
    }, timeoutMs);
  });
  const body = new URLSearchParams();
  for (const [name, value] of Object.entries(fields)) body.set(name, value);
  const asking = (async () => {
    try {
      const got = await fetchImpl(address, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString(),
        credentials: 'omit',
        /* A redirect must never carry the pass anywhere else: it becomes a failed ask, so the could-not-reach words. */
        redirect: 'error',
        signal: controller ? controller.signal : undefined,
      });
      const status = Number(got && got.status) || 0;
      let parsed;
      try {
        parsed = await got.json();
      } catch (wrong) {
        return { kind: 'garbled', status };
      }
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return { kind: 'garbled', status };
      return { kind: 'answered', status, body: parsed };
    } catch (wrong) {
      return { kind: 'unreachable', why: (wrong && wrong.message) || String(wrong) };
    }
  })();
  try {
    return await Promise.race([asking, tooLong]);
  } finally {
    clearTimeout(timer);
  }
}

/** The words for a call that did not give an answer worth reading. */
function whyNoAnswer(got, doing) {
  if (got.kind === 'garbled') {
    return `Kartaan answered, but not in a way this extension can read (status ${got.status || 'unknown'}), `
      + `so ${doing}.`;
  }
  if (got.timedOut) {
    return `Kartaan could not be reached: it did not answer in ${Math.round(WAIT_AT_MOST_MS / 1000)} seconds, `
      + `so ${doing}.`;
  }
  const why = got.why ? ` (${String(got.why).slice(0, 100)})` : '';
  return `Kartaan could not be reached${why}, so ${doing}.`;
}

/* ---------------------------------------------------------- may it fetch */

/**
 * Ask Kartaan whether this seller's fetching may run.
 *
 * Answers `{ go, asked, kind, said }`:
 *   - `no-pass`      go: true,  asked: false -- **CONTROL'S DECISION**: with no pass saved the check cannot be made, so the
 *                    sync goes ahead as it did before, and `said` says plainly that it was not checked;
 *   - `go`           go: true,  asked: true  -- Kartaan said yes;
 *   - `no`           go: false -- Kartaan said no (`said` is its own sentence), whether as `fetch: false` or as a
 *                    403/429/503 or any other refusal;
 *   - `unreachable`  go: false -- no answer, or none in time;
 *   - `garbled`      go: false -- an answer this cannot read, or one that contradicts itself.
 * **ONLY A CLEAR YES IS A GO.** Anything this cannot read as a yes is a no, and says why.
 */
export async function askMayFetch(chrome, fetchImpl, { timeoutMs = WAIT_AT_MOST_MS, at = Date.now() } = {}) {
  let answer;
  try {
    answer = await askMayFetchInWords(chrome, fetchImpl, timeoutMs);
  } catch (wrong) {
    answer = {
      go: false, asked: true, kind: 'unreachable',
      said: `Kartaan could not be asked (${String((wrong && wrong.message) || wrong).slice(0, 100)}), so the sync was not started.`,
    };
  }
  await rememberWhatWasSaid(chrome, {
    at, kind: 'may-fetch', said: answer.said, go: answer.go, asked: answer.asked,
  });
  return answer;
}

async function askMayFetchInWords(chrome, fetchImpl, timeoutMs) {
  const pass = await thePass(chrome);
  if (!pass) {
    return {
      go: true, asked: false, kind: 'no-pass',
      said: 'Kartaan was not asked whether this sync may run, because no run pass is saved. '
        + 'The sync went ahead without the check. Save a run pass from Kartaan\'s page to have it made.',
    };
  }
  const got = await postForm(fetchImpl, MAY_FETCH_ADDRESS, { pass }, timeoutMs);
  if (got.kind !== 'answered') {
    return {
      go: false, asked: true, kind: got.kind, said: cleaned(whyNoAnswer(got, 'the sync was not started'), pass),
    };
  }
  const { status, body } = got;
  const theirWords = typeof body.said === 'string' ? cleaned(body.said, pass) : '';
  if (typeof body.fetch !== 'boolean') {
    return {
      go: false, asked: true, kind: 'garbled',
      said: `Kartaan answered (status ${status}) but not with a yes or a no, so the sync was not started.`
        + `${theirWords ? ` It said: ${theirWords}` : ''}`,
    };
  }
  if (body.fetch === true && status === 200) {
    return { go: true, asked: true, kind: 'go', said: theirWords || 'Kartaan said this sync may run.' };
  }
  if (body.fetch === true) {
    /* A yes under a 403, 429 or 503 contradicts itself; a refusal wins, because starting on a doubt is the wrong way round. */
    return {
      go: false, asked: true, kind: 'garbled',
      said: `Kartaan's answer did not agree with itself (status ${status}), so the sync was not started.`
        + `${theirWords ? ` It said: ${theirWords}` : ''}`,
    };
  }
  return {
    go: false, asked: true, kind: 'no',
    said: theirWords || `Kartaan said this sync may not run (status ${status}).`,
  };
}

/* ----------------------------------------------------------- it finished */

/** The failed reports' ids as the server reads them: only well-formed ones, each once, at most forty. */
export function theFailedReportsToSend(ids) {
  const names = [];
  for (const one of ids || []) {
    const name = String(one || '').trim();
    if (LOOKS_LIKE_A_REPORT.test(name) && !names.includes(name)) names.push(name);
  }
  return names.slice(0, AT_MOST_FAILED);
}

/**
 * Tell Kartaan a sync has finished, naming the reports that failed or need the seller.
 *
 * `failed` is sent as ONE form field, comma-separated -- the only format `the_failed_reports` reads -- and left out
 * when nothing failed. Answers `{ told, kind, said }` and **never throws**. `told` is true only when Kartaan
 * answered and said it started the run. A failure to tell says "The run still runs on its own schedule", because it
 * does: this call is a nudge, and the seller's own daily run happens without it.
 */
export async function tellFinished(chrome, fetchImpl, { failed = [], timeoutMs = WAIT_AT_MOST_MS, at = Date.now() } = {}) {
  let answer;
  try {
    answer = await tellFinishedInWords(chrome, fetchImpl, failed, timeoutMs);
  } catch (wrong) {
    answer = {
      told: false, kind: 'unreachable',
      said: `Kartaan could not be told this sync finished (${String((wrong && wrong.message) || wrong).slice(0, 100)}). ${STILL_RUNS}`,
    };
  }
  await rememberWhatWasSaid(chrome, { at, kind: 'finished', said: answer.said, told: answer.told });
  return answer;
}

async function tellFinishedInWords(chrome, fetchImpl, failed, timeoutMs) {
  const pass = await thePass(chrome);
  if (!pass) {
    return {
      told: false, kind: 'no-pass',
      said: `Kartaan was not told this sync finished, because no run pass is saved. ${STILL_RUNS}`,
    };
  }
  const names = theFailedReportsToSend(failed);
  const fields = { pass };
  if (names.length) fields.failed = names.join(',');
  const got = await postForm(fetchImpl, FINISHED_ADDRESS, fields, timeoutMs);
  if (got.kind !== 'answered') {
    return {
      told: false, kind: got.kind,
      said: cleaned(`${whyNoAnswer(got, 'Kartaan was not told this sync finished')} ${STILL_RUNS}`, pass),
    };
  }
  const { status, body } = got;
  if (typeof body.started !== 'boolean' && typeof body.said !== 'string') {
    return {
      told: false, kind: 'garbled',
      said: `Kartaan answered (status ${status}) but not in a way this extension can read. ${STILL_RUNS}`,
    };
  }
  const theirWords = typeof body.said === 'string' ? cleaned(body.said, pass) : '';
  const theirFailed = Array.isArray(body.failed)
    ? theFailedReportsToSend(body.failed.map(String)) : [];
  const named = theirFailed.length ? ` Reports Kartaan was told did not land: ${theirFailed.join(', ')}.` : '';
  if (body.started === true && status >= 200 && status < 300) {
    return { told: true, kind: 'started', said: `${theirWords || 'Kartaan has started your run.'}${named}` };
  }
  return {
    told: false, kind: 'refused',
    said: `${theirWords || `Kartaan did not start a run (status ${status}).`}${named} ${STILL_RUNS}`,
  };
}

/* ------------------------------------------- a failed night reaches him (AJ9 piece 3) */

export const TELL_ADDRESS = `${KARTAAN}/tell`;
const PLATFORM_WORDS = { fk: 'Flipkart', me: 'Meesho', az: 'Amazon' };

/** A report id in the words he uses: `fk_orders` is "Flipkart orders". Only the platform prefix is known; the rest is
 *  the id with its underscores as spaces. */
export function aReportInWords(id) {
  const [first, ...rest] = String(id || '').split('_');
  const platform = PLATFORM_WORDS[first];
  return (platform ? [platform, ...rest] : [first, ...rest]).join(' ');
}

/**
 * Tell him, through Kartaan's message centre (`/tell`, the Server's one sender: D588/D589; Discord by default, D666),
 * which reports of this sync failed or need him. **No new channel**: the centre already has AutoSync's `problem` kind
 * and proves who is speaking by the run pass. The words carry report names only -- no customer data, never the pass.
 * Answers `{ queued, said }`, **never throws**, and never changes how the sync went.
 */
export async function tellTheProblem(chrome, fetchImpl, { names, timeoutMs = WAIT_AT_MOST_MS, at = Date.now() } = {}) {
  try {
    const pass = await thePass(chrome);
    if (!pass) {
      return { queued: false, said: 'His messages were not told which reports failed, because no run pass is saved.' };
    }
    const words = names.map(aReportInWords).join(', ');
    const facts = {
      text: `AutoSync did not get: ${words}. Some are tried again by itself; if one is still missing tomorrow, `
        + 'open the AutoSync panel -- a few have to be fetched by hand.',
    };
    /* **THE ID IS THE NIGHT'S END, NOT THE CLOCK**, so a worker restarted between the post and the note that it was told
     * sends the same id again and the centre keeps one message (review finding). */
    const got = await postForm(fetchImpl, TELL_ADDRESS, {
      source: 'autosync', kind: 'problem', id: `autosync-failed-${at}`, facts: JSON.stringify(facts), pass,
    }, timeoutMs);
    if (got.kind === 'answered' && got.body.queued === true) {
      return { queued: true, said: 'His messages were told which reports failed.' };
    }
    const why = got.kind === 'answered' && typeof got.body.said === 'string'
      ? cleaned(got.body.said, pass) : cleaned(whyNoAnswer(got, 'his messages were not told'), pass);
    return { queued: false, said: `His messages were not told which reports failed. ${why}` };
  } catch (wrong) {
    return { queued: false, said: 'His messages were not told which reports failed (something went wrong sending it).' };
  }
}

/** The night a "save the run pass" notice was last shown for (AJ9 3b): one notice per night, never repeated. */
export const THE_NO_PASS_NOTICE = 'kartaan-autosync-no-pass-notice-night';

/**
 * **WITH NO RUN PASS SAVED NOTHING CAN BE SENT, SO HE IS TOLD AT THE COMPUTER, ONCE A NIGHT (AJ9 3b, A12's real cause).**
 * A browser notification in plain words saying what to press. Remembered by the night's end, so a second tell the
 * same night shows nothing. Never throws, never changes how the night went. Answers whether one was shown.
 */
export async function tellHimToSaveThePass(chrome, nightKey) {
  try {
    if (!chrome.notifications) return false;
    const done = (await chrome.storage.local.get(THE_NO_PASS_NOTICE))[THE_NO_PASS_NOTICE];
    if (done === nightKey) return false;
    await chrome.storage.local.set({ [THE_NO_PASS_NOTICE]: nightKey });
    chrome.notifications.create(`kartaan-no-pass-${nightKey}`, {
      type: 'basic', iconUrl: chrome.runtime.getURL('icon128.png'), title: 'AutoSync cannot tell Kartaan yet',
      message: 'Open the AutoSync panel, paste the run pass from Kartaan\'s page (Run pass), and press Save. '
        + 'Until then your reports are fetched but Kartaan is not told.',
      requireInteraction: true, priority: 2,
    }, () => { void chrome.runtime.lastError; });
    return true;
  } catch (wrong) {
    return false;
  }
}

/**
 * `tellFinished`, and then -- only when some report failed or needs him -- the message to him. **The sentence that
 * comes back says both**, so the run log's "Told Kartaan" line shows whether his messages were told. Never throws.
 */
export async function tellFinishedAndAlert(chrome, fetchImpl, {
  failed = [], endedAt = null, timeoutMs = WAIT_AT_MOST_MS, at = Date.now(),
} = {}) {
  const answer = await tellFinished(chrome, fetchImpl, { failed, timeoutMs, at });
  if (answer.kind === 'no-pass') await tellHimToSaveThePass(chrome, Number.isFinite(endedAt) && endedAt ? endedAt : at);
  const names = theFailedReportsToSend(failed);
  if (!names.length) return answer;
  const alert = await tellTheProblem(chrome, fetchImpl, {
    names, timeoutMs, at: Number.isFinite(endedAt) && endedAt ? endedAt : at,
  });
  return { ...answer, said: `${answer.said} ${alert.said}` };
}
