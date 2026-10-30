/* AutoSync driven by the seller's AI (AD1, rulings D818 and D820).
 *
 * **THE SELLER'S AI ASKS, AUTOSYNC DECIDES.** Tool calls arrive ONLY on the one native-messaging port to the Kartaan Bridge helper
 * (`com.kartaan.bridge`, its own product), opened ONLY while the seller's own "AI may run AutoSync" switch on the panel is on, which is OFF
 * until he turns it on. `connectNative` appears nowhere else in this extension (a check holds that).
 *
 * **WHAT THE AI CAN DO IS THREE THINGS:** read how the reports stand (`autosync_status`), ask for a run (`autosync_run`: reports from the
 * list, a From day and a To day), read how an ask went (`autosync_result`). It cannot press anything on a portal, change a setting, connect
 * a Drive or stop a run.
 *
 * **AN ASK GOES THROUGH THE SAME DOOR AS THE RUN NOW BUTTON** (`answerThePanelsQuestion` with `run-now`), so every rule that button has is
 * kept: Kartaan's yes or no, the Drive being connected, the Meesho panel name, one platform after another. Before it is kept at all, the
 * ask is refused in plain words if it names a report AutoSync cannot fetch, a day that is not over, a range longer than one press takes, a
 * report that cannot be fetched for a past day, or more of Flipkart's twenty a day than are left.
 *
 * **AND NEVER WHILE THE SELLER IS AT THE COMPUTER (N063).** An ask waits until the computer has been left alone for three minutes
 * (`computerInUse`, the same question the night run asks), and until any run already going has finished. Asks run one at a time, in the
 * order they came. The panel says so ("Asked by your AI: ... -- waiting for the computer to be free") and so does the status.
 *
 * **AN ASK THAT IS RUNNING IS NEVER STARTED A SECOND TIME.** It is written down as running BEFORE the run is started. If AutoSync is
 * updated or Chrome restarts, a waiting ask is still waiting afterwards; a running one is followed to its end by reading the night, and
 * one that never began is marked failed, in words, for the AI to ask again. The answers are plain JSON, so the Server route (D820, later)
 * can serve the same tool names unchanged.
 */

import { IDLE_SECONDS } from './idle.js';
import {
  THE_QUEUE, theTickableReports, thePlatformOf, whyItCannotBeStarted, withTheListsTheyRead, whyThatRangeCannotBeFetched,
  theDayToFetch, theDaysBetween, CALLED,
} from './screen.js';
import {
  theNight, theDay, LAST_LANDED, SPENDS_THE_ALLOWANCE, A_DAYS_ALLOWANCE, KEPT_FOR_HIS_OWN_RUNS,
} from './nightly.js';

/** **FOR THE AI, "IN USE" IS THE ANSWER WHENEVER CHROME CANNOT SAY.** The night run starts when it cannot tell; an ask from the AI never does. */
async function seatedAtTheComputer(chrome) {
  try {
    return (await chrome.idle.queryState(IDLE_SECONDS)) === 'active';
  } catch (wrong) {
    return true;
  }
}

export const HOST = 'com.kartaan.bridge';
export const AI_SWITCH = 'kartaan-autosync-ai-switch';
export const AI_ASKS = 'kartaan-autosync-ai-asks';
export const AI_NOTE = 'kartaan-autosync-ai-note';
export const AI_ALARM = 'kartaan-autosync-ai-ask-wait';
export const AI_SPENT = 'kartaan-autosync-ai-spent-today';
/** **THE AI'S OWN CEILING FOR A DAY, so it can never starve the seller's timed sync of Flipkart's twenty.** It may ask for the day's twenty
 *  less the ones kept for his own runs, and for this many asks. Counted when an ask is kept. */
export const AI_MOST_FLIPKART_A_DAY = A_DAYS_ALLOWANCE - KEPT_FOR_HIS_OWN_RUNS;
export const AI_MOST_ASKS_A_DAY = 12;
/** A two-website ask has a gap between its websites; it is called finished only this long after its last run ended. */
export const SETTLE_MS = 3 * 60 * 1000;
/** The tools this extension answers, exactly as the Kartaan Bridge lists them for AutoSync (a check in the bridge repo holds the names equal). */
export const BRIDGE_TOOLS = Object.freeze(['autosync_status', 'autosync_run', 'autosync_result']);
/** At most this many asks wait at once; the newest twenty are kept for reading back. */
export const MOST_WAITING = 5;
export const KEEP_ASKS = 20;
/** An ask that is running but whose run never began is given this long before it is called failed. */
export const GIVE_UP_AFTER_MS = 10 * 60 * 1000;
export const NEEDS_THE_SWITCH = 'AutoSync\'s "AI may run AutoSync" switch is off. Ask the seller to turn it on in the AutoSync panel.';

const two = (n) => String(n).padStart(2, '0');
const stamp = (at) => new Date(at).toISOString();
const names = (book, ids) => ids.map((id) => ((book.reports || []).find((one) => one.id === id) || {}).name || id);

export async function aiIsOn(chrome) {
  return (await chrome.storage.local.get(AI_SWITCH))[AI_SWITCH] === true;
}
async function theAsks(chrome) {
  const held = (await chrome.storage.local.get(AI_ASKS))[AI_ASKS];
  return Array.isArray(held) ? held : [];
}
async function keepTheAsks(chrome, asks) {
  await chrome.storage.local.set({ [AI_ASKS]: asks.slice(-KEEP_ASKS) });
}
/** One line the panel shows under the switch (why it turned itself off, what Chrome said). Plain words only. */
async function note(chrome, text) {
  await chrome.storage.local.set({ [AI_NOTE]: String(text || '').slice(0, 300) });
}

/* **EVERYTHING THAT READS AND WRITES THE ASKS TAKES ITS TURN**, so the alarm, a tool call, a landing and the panel cannot each read the same list
 * and the last write win (which is how an ask would be started twice or lost). */
let turn = Promise.resolve();
const inTurn = (job) => { const done = turn.then(job); turn = done.then(() => undefined, () => undefined); return done; };
export const answerTheBridge = async (chrome, parts, call) => {
  const answered = await inTurn(() => answerInner(chrome, parts, call));
  /* **AN ASK IS ANSWERED AT ONCE and started AFTER the answer, outside the turn**: starting a run waits on Kartaan's network check and a portal
   * page, up to a minute, and nothing else (the AI's status, the panel's two-second poll, Tune) may be held up behind that. */
  if (call && call.tool === 'autosync_run' && answered && answered.ok) processTheAsks(chrome, parts).catch(() => {});
  return answered;
};
/** Start the oldest waiting ask if it may start. **The turn is held only to decide and to write it down; the run itself is started outside it.** */
export async function processTheAsks(chrome, parts) {
  const going = await inTurn(() => prepareInner(chrome, parts));
  if (!going) return;
  let said;
  try {
    said = await parts.panelAnswer({ do: 'run-now', reportIds: going.reportIds, from: going.from, to: going.to });
  } catch (wrong) {
    said = { wrong: String((wrong && wrong.message) || wrong).slice(0, 200) };
  }
  await inTurn(() => afterStarting(chrome, parts, going, said));
}
export const noteAFile = (chrome, fileName) => inTurn(() => noteInner(chrome, fileName));
export const aiState = (chrome, parts) => inTurn(() => stateInner(chrome, parts));
export const setTheSwitch = (chrome, parts, on) => inTurn(() => switchInner(chrome, parts, on));

/* ------------------------------------------------------------------ words */

/** What an ask says about itself, in plain words, for the AI and for the panel. */
export function slimAsk(book, ask) {
  const said = {
    waiting: ask.waitingFor === 'run'
      ? 'Waiting for the run that is going now to finish.'
      : 'Waiting for the computer to be free (it has to be left alone for 3 minutes).',
    running: 'AutoSync is fetching these now.',
    done: ask.results.length
      ? `Finished: ${ask.results.filter((r) => r.state === 'landed').length} landed, `
        + `${ask.results.filter((r) => r.state !== 'landed' && r.state !== 'nothing-to-fetch').length} did not, `
        + `${ask.results.filter((r) => r.state === 'nothing-to-fetch').length} had nothing to fetch.`
      : 'Finished, with nothing recorded against the reports.',
    refused: ask.why || 'Refused.',
    failed: ask.why || 'Did not finish.',
  }[ask.state] || '';
  return {
    ask_id: ask.id,
    reports: ask.reportIds,
    report_names: names(book, ask.reportIds),
    from: ask.from,
    to: ask.to,
    state: ask.state,
    message: said,
    asked_at: stamp(ask.askedAt),
    ...(ask.startedAt ? { started_at: stamp(ask.startedAt) } : {}),
    ...(ask.finishedAt ? { finished_at: stamp(ask.finishedAt) } : {}),
    results: ask.results.map((r) => ({ report: r.report, day: r.day, state: r.state, said: r.said })),
    files_landed: [...ask.files],
  };
}

/* ------------------------------------------------------------ refusing */

/**
 * Why an ask must be refused before it is kept, or '' when it may wait. **EVERY REFUSAL SAYS WHAT TO DO INSTEAD**, because the reader is an AI
 * that will tell the seller.
 */
export function whyThisAskIsRefused(book, { reportIds, from, to }, { now, panel, leftToday, spentByOthers, waitingCount }) {
  const ids = reportIds;
  if (new Set(ids).size !== ids.length) return 'A report is named twice. Name each report once.';
  const tickable = theTickableReports(book);
  const unknown = ids.filter((id) => !tickable.includes(id));
  if (unknown.length) {
    return `${unknown.join(', ')} ${unknown.length > 1 ? 'are not reports' : 'is not a report'} AutoSync can fetch. It can fetch: ${tickable.join(', ')}.`;
  }
  const rangeWrong = whyThatRangeCannotBeFetched(from, to, now);
  if (rangeWrong) return rangeWrong;
  const latest = theDayToFetch(now);
  const days = theDaysBetween(from, to);
  const onlyNow = ids.filter((id) => {
    const one = (book.reports || []).find((r) => r.id === id) || {};
    return one.cannotBeAskedForAgain !== null && one.cannotBeAskedForAgain !== undefined && days.some((d) => d !== latest);
  });
  if (onlyNow.length) {
    return `${onlyNow.join(', ')} can only be fetched for yesterday (${latest}), not for ${from} to ${to}. Ask for yesterday alone, or leave ${onlyNow.length > 1 ? 'those' : 'it'} out.`;
  }
  /* One run walks one website; the Run now door runs the websites one after another, so each website is asked on its own terms. */
  const byPlatform = [...new Set(ids.map((id) => thePlatformOf(book, id)))]
    .map((platform) => ids.filter((id) => thePlatformOf(book, id) === platform));
  for (const group of byPlatform) {
    const wrong = whyItCannotBeStarted(book, { reportIds: withTheListsTheyRead(book, group), panel, night: null });
    if (wrong) return `${CALLED[thePlatformOf(book, group[0])] || thePlatformOf(book, group[0])}: ${wrong}`;
  }
  /* **FLIPKART'S TWENTY A DAY.** The orders and payments reports each cost one request for the whole stretch, whatever its length. */
  const spend = ids.filter((id) => SPENDS_THE_ALLOWANCE.includes(id)).length;
  if (spend && spend + spentByOthers > leftToday) {
    return `Flipkart allows ${20} reports a day and ${leftToday} are left today${spentByOthers ? `, ${spentByOthers} of them already promised to earlier asks` : ''}; this ask needs ${spend}. `
      + 'The count starts again after midnight on the seller\'s computer. Ask for fewer, or ask again tomorrow.';
  }
  if (waitingCount >= MOST_WAITING) return `${MOST_WAITING} asks are already waiting. Wait for some to finish, then ask again.`;
  return '';
}

/* ------------------------------------------------------------ the tools */

async function status(chrome, parts) {
  const book = await parts.theBook();
  const stands = (await parts.panelAnswer({ do: 'how-it-stands' })).stands;
  const landed = (await chrome.storage.local.get(LAST_LANDED))[LAST_LANDED] || {};
  const asks = await refreshTheAsks(chrome, parts);
  const latest = asks.length ? asks[asks.length - 1] : null;
  const going = Boolean(stands.night && !stands.night.finishedAt);
  return {
    ready_to_run: Boolean(stands.setUp.done),
    drive_connected: Boolean(stands.setUp.driveConnectedAt),
    run_going_now: going,
    waiting_asks: asks.filter((a) => a.state === 'waiting').length,
    computer_in_use_now: await seatedAtTheComputer(chrome),
    flipkart_requests_left_today: stands.flipkart.leftToday,
    flipkart_requests_a_day: stands.flipkart.allowedADay,
    timed_sync: (stands.timed && stands.timed.said) || '',
    reports: stands.reports.map((r) => ({
      id: r.id,
      name: r.name,
      platform: r.platform,
      can_be_fetched: Boolean(r.canBeFetched),
      last_run: r.state ? { state: r.state, said: r.say || '' } : null,
      last_landed_day: Array.isArray(landed[r.id]) && landed[r.id].length ? [...landed[r.id]].sort().pop() : null,
    })),
    cannot_be_fetched: (stands.cannotBeFetched || []).map((c) => ({ id: c.id, name: c.name, why: c.why })),
    latest_ask: latest ? slimAsk(book, latest) : null,
  };
}

/** The reports and days already promised to waiting asks, as a count of Flipkart requests. */
const promised = (asks) => asks.filter((a) => a.state === 'waiting')
  .reduce((all, a) => all + a.reportIds.filter((id) => SPENDS_THE_ALLOWANCE.includes(id)).length, 0);

async function run(chrome, parts, args) {
  const now = (parts.now || Date.now)();
  const book = await parts.theBook();
  const reportIds = args.reportIds.map(String);
  const { from, to } = args;
  const stands = (await parts.panelAnswer({ do: 'how-it-stands' })).stands;
  const asks = await refreshTheAsks(chrome, parts);
  const why = whyThisAskIsRefused(book, { reportIds, from, to }, {
    now, panel: stands.setUp.panel, leftToday: stands.flipkart.leftToday, spentByOthers: promised(asks),
    waitingCount: asks.filter((a) => a.state === 'waiting').length,
  });
  if (why) return { ok: false, error: `Not asked: ${why}` };
  if (!stands.setUp.driveConnectedAt) return { ok: false, error: 'Not asked: the seller\'s Google Drive is not connected in AutoSync yet, so nothing fetched would have anywhere to go. Ask the seller to connect it.' };
  /* The same ask already waiting is the same ask: answered with its id, never kept twice. */
  const key = (a) => `${[...a.reportIds].sort().join(',')}|${a.from}|${a.to}`;
  const wanted = key({ reportIds, from, to });
  const twin = asks.find((a) => (a.state === 'waiting' || a.state === 'running') && key(a) === wanted);
  if (twin) return { ok: true, result: { ask_id: twin.id, state: twin.state, message: 'This same ask is already in. ' + slimAsk(book, twin).message } };
  /* **THE AI'S OWN DAILY CEILING (security review M1).** Counted in the seller's own day, when an ask is kept. */
  const today = theDay(now);
  const spent = (await chrome.storage.local.get(AI_SPENT))[AI_SPENT];
  const so = spent && spent.day === today ? spent : { day: today, flipkart: 0, asks: 0 };
  const cost = reportIds.filter((id) => SPENDS_THE_ALLOWANCE.includes(id)).length;
  if (so.asks + 1 > AI_MOST_ASKS_A_DAY) return { ok: false, error: `Not asked: your AI has already made ${so.asks} asks today and ${AI_MOST_ASKS_A_DAY} is the most a day. Ask again tomorrow (the count starts again after midnight on the seller's computer).` };
  if (so.flipkart + cost > AI_MOST_FLIPKART_A_DAY) {
    return { ok: false, error: `Not asked: of Flipkart's ${A_DAYS_ALLOWANCE} reports a day, your AI may use ${AI_MOST_FLIPKART_A_DAY} (the rest are kept for the seller's own runs) and ${so.flipkart} are already used or promised today. Ask again tomorrow, after midnight on the seller's computer.` };
  }
  const id = Array.from(crypto.getRandomValues(new Uint8Array(8)), (b) => two(b.toString(16))).join('');
  const ask = { id, reportIds, from, to, askedAt: now, state: 'waiting', waitingFor: 'computer', results: [], files: [] };
  await chrome.storage.local.set({ [AI_SPENT]: { day: today, flipkart: so.flipkart + cost, asks: so.asks + 1 } });
  await keepTheAsks(chrome, [...asks, ask]);
  await ensureTheAlarm(chrome);
  return { ok: true, result: { ask_id: id, state: 'waiting', message: `Asked. ${slimAsk(book, ask).message} Read the outcome with autosync_result.` } };
}

async function result(chrome, parts, args) {
  const book = await parts.theBook();
  const asks = await refreshTheAsks(chrome, parts);
  if (!asks.length) return { ok: true, result: { message: 'No ask has been made yet.' } };
  const ask = args.ask_id ? asks.find((a) => a.id === args.ask_id) : asks[asks.length - 1];
  if (!ask) return { ok: false, error: `No ask has the id ${String(args.ask_id).slice(0, 20)}. The latest ones are: ${asks.map((a) => a.id).join(', ')}.` };
  return { ok: true, result: slimAsk(book, ask) };
}

/** The one door the native port uses. Tool names are the bridge's; anything else is refused. */
async function answerInner(chrome, parts, { tool, args }) {
  if (!(await aiIsOn(chrome))) return { ok: false, error: NEEDS_THE_SWITCH };
  const given = args && typeof args === 'object' && !Array.isArray(args) ? args : {};
  try {
    if (tool === 'autosync_status') return { ok: true, result: await status(chrome, parts) };
    if (tool === 'autosync_run') {
      if (!Array.isArray(given.reportIds) || !given.reportIds.length || given.reportIds.length > 30 || given.reportIds.some((r) => typeof r !== 'string' || !/^[a-z0-9_]{1,40}$/.test(r))) {
        return { ok: false, error: 'reportIds must be a list of 1 to 30 report ids from autosync_status.' };
      }
      if (typeof given.from !== 'string' || typeof given.to !== 'string') return { ok: false, error: 'from and to must be days written like 2026-05-01.' };
      return await run(chrome, parts, given);
    }
    if (tool === 'autosync_result') {
      if (given.ask_id !== undefined && (typeof given.ask_id !== 'string' || !/^[0-9a-f]{8,32}$/.test(given.ask_id))) return { ok: false, error: 'ask_id is the id autosync_run gave.' };
      return await result(chrome, parts, given);
    }
  } catch (wrong) {
    return { ok: false, error: `AutoSync could not answer: ${String((wrong && wrong.message) || wrong).slice(0, 200)}` };
  }
  return { ok: false, error: `"${String(tool).slice(0, 40)}" is not an AutoSync tool.` };
}

/* ------------------------------------------------- following the asks */

async function ensureTheAlarm(chrome) {
  if (!(await chrome.alarms.get(AI_ALARM))) await chrome.alarms.create(AI_ALARM, { delayInMinutes: 1, periodInMinutes: 1 });
}

/**
 * Bring every running ask up to date from the night, and say when it is over. Reads only; starts nothing.
 */
export async function refreshTheAsks(chrome, parts) {
  const asks = await theAsks(chrome);
  const running = asks.find((a) => a.state === 'running');
  if (!running) return asks;
  const night = await theNight(chrome);
  const queue = (await chrome.storage.local.get(THE_QUEUE))[THE_QUEUE];
  const now = (parts.now || Date.now)();
  /* **ONLY A RUN THIS ASK STARTED IS THIS ASK'S** (review M2): the night its own start created, written down right after the start, and the ones
   * after it. A timed sync or a re-check that began in some other gap is never adopted. */
  const mine = night && running.nightStartedAt !== undefined && night.startedAt >= running.nightStartedAt;
  if (mine) {
    const seen = new Map(running.results.map((r) => [`${r.report}|${r.day}`, r]));
    for (const one of night.done || []) {
      seen.set(`${one.reportId}|${one.dataDate || ''}`, { report: one.reportId, day: one.dataDate || '', state: one.state, said: one.say || '' });
    }
    running.results = [...seen.values()];
    /* **A TWO-WEBSITE ASK HAS A GAP BETWEEN ITS WEBSITES** (the next one is taken off the list, then Kartaan is asked, then its run is written),
     * so it is finished only once the list is empty AND the last run ended a few minutes ago. */
    const book = await parts.theBook();
    const twoSites = new Set(running.reportIds.map((id) => thePlatformOf(book, id))).size > 1;
    const settled = !twoSites || now - night.finishedAt >= SETTLE_MS;
    if (night.finishedAt && settled && !(Array.isArray(queue) && queue.length)) {
      running.state = 'done';
      running.finishedAt = night.finishedAt;
    }
  } else if (now - running.startedAt > GIVE_UP_AFTER_MS && !(night && !night.finishedAt) && !(Array.isArray(queue) && queue.length)) {
    running.state = 'failed';
    running.finishedAt = now;
    running.why = 'AutoSync did not begin this run (the extension was probably restarted at that moment). Nothing was fetched. Ask again.';
  }
  await keepTheAsks(chrome, asks);
  return asks;
}

/**
 * Start the oldest waiting ask if, and only if, nothing else is running and the computer has been left alone for three minutes. Called when an
 * ask is made, on the one-minute alarm, and whenever the worker wakes. **Never starts two, never starts one twice.**
 */
async function prepareInner(chrome, parts) {
  if (!(await aiIsOn(chrome))) return null;
  const asks = await refreshTheAsks(chrome, parts);
  const next = asks.find((a) => a.state === 'waiting');
  if (asks.some((a) => a.state === 'running') || !next) return null;
  const night = await theNight(chrome);
  if (night && !night.finishedAt) { next.waitingFor = 'run'; await keepTheAsks(chrome, asks); return null; }
  if (await seatedAtTheComputer(chrome)) { next.waitingFor = 'computer'; await keepTheAsks(chrome, asks); return null; }
  /* **ASKED AGAIN AT THE MOMENT OF STARTING** (security review M2): storage is the only thing between a waiting ask and a start, so what was
   * checked when it was kept is checked once more, against how things stand now (the Drive, the allowance spent meanwhile). */
  const book = await parts.theBook();
  const stands = (await parts.panelAnswer({ do: 'how-it-stands' })).stands;
  const now = (parts.now || Date.now)();
  const why = whyThisAskIsRefused(book, next, { now, panel: stands.setUp.panel, leftToday: stands.flipkart.leftToday, spentByOthers: 0, waitingCount: 0 })
    || (stands.setUp.driveConnectedAt ? '' : 'the seller\'s Google Drive is not connected');
  if (why) {
    next.state = 'refused';
    next.finishedAt = now;
    next.why = `Checked again when it was about to start, and no longer possible: ${why}`;
    await keepTheAsks(chrome, asks);
    return null;
  }
  /* **WRITTEN DOWN AS RUNNING BEFORE IT IS STARTED**, so a restart between the two can never start it again. */
  next.state = 'running';
  next.startedAt = now;
  await keepTheAsks(chrome, asks);
  return { ...next };
}

/** After the run was asked for: refused in words, or the night it began is written against the ask so only that run is ever read as its own. */
async function afterStarting(chrome, parts, going, said) {
  const latest = await theAsks(chrome);
  const mine = latest.find((a) => a.id === going.id);
  if (!mine || mine.state !== 'running') return;
  if (said && said.wrong) {
    mine.state = 'refused';
    mine.finishedAt = (parts.now || Date.now)();
    mine.why = `AutoSync would not start it: ${said.wrong}`;
  } else {
    const night = await theNight(chrome);
    if (night && night.startedAt >= mine.startedAt) mine.nightStartedAt = night.startedAt;
  }
  await keepTheAsks(chrome, latest);
}

/** Remember a file that landed against the ask that is running (called after every landing; does nothing when no ask is running). */
async function noteInner(chrome, fileName) {
  try {
    const asks = await theAsks(chrome);
    const running = asks.find((a) => a.state === 'running');
    if (!running || running.files.length >= 200) return;
    if (!running.files.includes(String(fileName))) running.files.push(String(fileName).slice(0, 200));
    await keepTheAsks(chrome, asks);
  } catch (ignored) { /* a note that cannot be kept must never stop a landing */ }
}

/* ------------------------------------------------------- the switch */

/** What the panel shows: the switch, a note, and the asks that are waiting or running, in words. */
async function stateInner(chrome, parts) {
  const on = await aiIsOn(chrome);
  const book = await parts.theBook();
  const asks = on ? await refreshTheAsks(chrome, parts) : [];
  const live = asks.filter((a) => a.state === 'waiting' || a.state === 'running');
  return {
    on,
    note: (await chrome.storage.local.get(AI_NOTE))[AI_NOTE] || '',
    connected: Boolean(parts.isConnected && parts.isConnected()),
    asks: live.map((a) => ({
      ...slimAsk(book, a),
      panel_line: `Asked by your AI: ${names(book, a.reportIds).join(', ')}, ${a.from} to ${a.to}`
        + (a.state === 'waiting'
          ? (a.waitingFor === 'run' ? ' -- waiting for the run that is going now to finish' : ' -- waiting for the computer to be free')
          : ' -- running now'),
    })),
    idle_seconds: IDLE_SECONDS,
  };
}

/** The switch, from the panel only. Turning it on opens the port; turning it off closes it and refuses nothing already running. */
async function switchInner(chrome, parts, on) {
  if (on) {
    await chrome.storage.local.set({ [AI_SWITCH]: true });
    await note(chrome, '');
    await ensureTheAlarm(chrome);
    parts.openThePort();
    return { on: true };
  }
  await chrome.storage.local.set({ [AI_SWITCH]: false });
  parts.closeThePort();
  await chrome.alarms.clear(AI_ALARM);
  /* The permission to talk to a helper is given back with the switch (security review M2); turning it on asks for it again. */
  try { if (chrome.permissions && chrome.permissions.remove) await chrome.permissions.remove({ permissions: ['nativeMessaging'] }); } catch (ignored) { /* already gone */ }
  /* Asks still waiting are dropped: with the switch off nothing may start by itself. A run already going is left to finish. */
  const asks = await theAsks(chrome);
  const kept = asks.map((a) => (a.state === 'waiting' ? { ...a, state: 'failed', finishedAt: (parts.now || Date.now)(), why: 'The seller turned AutoSync\'s AI switch off before this ask started.' } : a));
  await keepTheAsks(chrome, kept);
  return { on: false };
}

/* ------------------------------------------------------- the port */

/**
 * The one native port. **Opened only while the switch is on**, closed when it goes off or the helper goes. Nothing else in this extension
 * may call `connectNative`. A tool call is answered one at a time, in the order it came.
 */
export function makeThePort(chrome, parts) {
  let port = null;
  let queue = Promise.resolve();
  const open = () => {
    if (port) return;
    let p;
    try {
      p = chrome.runtime.connectNative(HOST);
    } catch (wrong) {
      note(chrome, `Chrome would not open the helper: ${String((wrong && wrong.message) || wrong).slice(0, 150)}`);
      return;
    }
    port = p;
    p.onMessage.addListener((msg) => {
      queue = queue.then(async () => {
        const answered = await answerTheBridge(chrome, parts, { tool: msg && msg.tool, args: msg && msg.args });
        if (port === p) p.postMessage({ id: (msg && msg.id) ?? null, ...answered });
      }).catch(() => {});
    });
    p.onDisconnect.addListener(async () => {
      if (port !== p) return;
      port = null;
      const said = String((chrome.runtime.lastError && chrome.runtime.lastError.message) || '');
      if (/not found|forbidden|not allowed/i.test(said)) {
        /* No helper on this computer, or it does not list this extension: the switch cannot work, so it says so and goes off. */
        await setTheSwitch(chrome, { ...parts, openThePort: open, closeThePort: close }, false);
        await note(chrome, 'The Kartaan AI helper is not set up on this computer. Install it first (Kartaan-AI-helper.exe), then turn this on again.');
      } else {
        await note(chrome, `The AI helper closed (${said.slice(0, 120) || 'no reason given'}). It is opened again within a minute while the switch is on.`);
      }
    });
  };
  const close = () => {
    const p = port;
    port = null;
    try { if (p) p.disconnect(); } catch (ignored) { /* already closed */ }
  };
  return { open, close, isOpen: () => Boolean(port) };
}

/** On every waking and every minute: open the port if the switch is on and it is closed, and move the asks on. */
export async function keepWatching(chrome, parts, thePort) {
  if (!(await aiIsOn(chrome))) return;
  /* **THE ALARM IS PUT BACK ON EVERY WAKING** (review H1): Chrome can clear alarms when an extension updates or the browser restarts, and nothing
   * else starts a waiting ask; background.js:240-249 says what the same oversight once cost. */
  await ensureTheAlarm(chrome);
  if (!thePort.isOpen()) thePort.open();
  await processTheAsks(chrome, parts);
}
