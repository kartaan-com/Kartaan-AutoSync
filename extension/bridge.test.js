/* Checks for AutoSync driven by the seller's AI (AD1, D818/D820).
 *
 * Run: node extension/bridge.test.js
 *
 * **THE ONES THAT MATTER:** (1) with the switch off every tool says so and nothing is kept; (2) an ask is refused, in words, before anything is
 * kept, for each reason in the brief; (3) an ask never starts while the computer is in use or a run is going, and never twice; (4) it goes through
 * the Run now door, not around it; (5) `connectNative` is opened in one file only, and only by turning the switch on.
 */

import { readFileSync, readdirSync } from 'node:fs';
import { installFakeChrome } from '../test/fake-chrome.js';
import {
  AI_ALARM, AI_ASKS, AI_SWITCH, BRIDGE_TOOLS, GIVE_UP_AFTER_MS, HOST, MOST_WAITING, NEEDS_THE_SWITCH, aiState, answerTheBridge,
  keepWatching, makeThePort, noteAFile, processTheAsks, setTheSwitch, whyThisAskIsRefused,
} from './bridge.js';
import { THE_NIGHT } from './nightly.js';
import { THE_QUEUE } from './screen.js';

process.on('uncaughtException', (err) => { console.log(`FAIL  the checks stopped part way through: ${(err && err.stack) || String(err)}`); process.exit(1); });
process.on('unhandledRejection', (err) => { console.log(`FAIL  something was waited on and never came back: ${(err && err.stack) || String(err)}`); process.exit(1); });
let failures = 0; let ran = 0;
function check(name, passed) { ran++; console.log(`${passed ? 'PASS' : 'FAIL'}  ${name}`); if (!passed) failures++; }

const BOOK = JSON.parse(readFileSync(new URL('recipes.json', import.meta.url), 'utf8'));
const NOW = new Date(2026, 9, 31, 10, 0).getTime(); // 31 Oct 2026, 10:00 local; yesterday is 2026-10-30
const reportsOf = BOOK.reports.filter((r) => ['flipkart', 'meesho'].includes(r.platform) && BOOK.recipes[r.id]);

/** A stand-in for "how it stands" and the Run now door, with just what the AI door reads and calls. */
function rig({ left = 20, driveAt = 1, panel = 'a-panel', clock = () => NOW } = {}) {
  const fake = installFakeChrome({ now: clock });
  const { chrome } = fake;
  const state = { runNow: [], left, driveAt, panel, refuseRunNow: '' };
  const parts = {
    theBook: async () => BOOK,
    now: clock,
    panelAnswer: async (asked) => {
      if (asked.do === 'how-it-stands') {
        const night = (await chrome.storage.local.get(THE_NIGHT))[THE_NIGHT] || null;
        return {
          stands: {
            setUp: { done: Boolean(state.driveAt && state.panel), driveConnectedAt: state.driveAt, panel: state.panel, driveSaid: '' },
            night,
            flipkart: { allowedADay: 20, askedForToday: 20 - state.left, leftToday: state.left },
            timed: { said: 'The timed sync will fetch: 0 reports' },
            reports: reportsOf.map((r) => ({ id: r.id, name: r.name, platform: r.platform, canBeFetched: true, state: '', say: '' })),
            cannotBeFetched: [],
          },
        };
      }
      if (asked.do === 'run-now') {
        state.runNow.push(asked);
        if (state.refuseRunNow) return { wrong: state.refuseRunNow };
        /* The real door writes the night before it answers. */
        if (state.writesANight !== false) await chrome.storage.local.set({ [THE_NIGHT]: { startedAt: clock(), finishedAt: 0, doing: asked.reportIds[0], left: [], done: [] } });
        return { started: ['x'] };
      }
      return {};
    },
    openThePort: () => { state.opened = (state.opened || 0) + 1; },
    closeThePort: () => { state.closed = (state.closed || 0) + 1; },
    isConnected: () => false,
  };
  return { fake, chrome, parts, state };
}
const call = (r, tool, args) => answerTheBridge(r.chrome, r.parts, { tool, args });
const asksOf = async (r) => (await r.chrome.storage.local.get(AI_ASKS))[AI_ASKS] || [];
const FK = { reportIds: ['fk_orders'], from: '2026-05-01', to: '2026-05-31' };
const settle = () => new Promise((res) => setTimeout(res, 40));

{
  check('the tools AutoSync answers are exactly the three the bridge lists', BRIDGE_TOOLS.join() === 'autosync_status,autosync_run,autosync_result');
  check('the helper is the shared Kartaan Bridge host', HOST === 'com.kartaan.bridge');
}

{
  const r = rig();
  for (const tool of BRIDGE_TOOLS) {
    const said = await call(r, tool, tool === 'autosync_run' ? FK : {});
    check(`${tool}: with the switch off it says so in plain words`, said.ok === false && said.error === NEEDS_THE_SWITCH);
  }
  check('with the switch off nothing was kept and nothing was started', (await asksOf(r)).length === 0 && r.state.runNow.length === 0);
}

{
  const r = rig();
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  r.fake.setTheComputer('active');
  const said = await call(r, 'autosync_status', {});
  check('status reads every report with its id, name, platform and whether it can be fetched', said.ok && said.result.reports.length === reportsOf.length
    && said.result.reports.every((x) => x.id && x.name && x.platform && x.can_be_fetched === true));
  check('status says plainly how many of Flipkart\'s twenty are left, and whether the computer is in use', said.result.flipkart_requests_left_today === 20 && said.result.computer_in_use_now === true);
  check('status has no ask yet', said.result.latest_ask === null && said.result.waiting_asks === 0);
  check('status is plain JSON (a Server could serve it unchanged)', JSON.stringify(JSON.parse(JSON.stringify(said))) === JSON.stringify(said));
}

/* ------------------------------------------------------------------ refusals */
const refuses = async (name, args, words, setup = null) => {
  const r = rig();
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  if (setup) await setup(r);
  const said = await call(r, 'autosync_run', args);
  check(`refused: ${name}`, said.ok === false && words.test(said.error) && (await asksOf(r)).length === 0 && r.state.runNow.length === 0);
  return said;
};
{
  await refuses('a report that is not on the list', { ...FK, reportIds: ['fk_nothing'] }, /not a report AutoSync can fetch/);
  await refuses('a report named twice', { ...FK, reportIds: ['fk_orders', 'fk_orders'] }, /named twice/);
  await refuses('a future day', { ...FK, to: '2026-11-05' }, /not over yet/);
  await refuses('today, which is not over', { ...FK, from: '2026-10-31', to: '2026-10-31' }, /not over yet/);
  await refuses('a range the wrong way round', { ...FK, from: '2026-05-31', to: '2026-05-01' }, /earlier day/);
  await refuses('a range longer than one press takes', { ...FK, from: '2026-03-01', to: '2026-05-31' }, /days at a time/);
  await refuses('not a day', { ...FK, from: '2026-02-30' }, /not a day/);
  await refuses('a report that only exists for now, asked for a past stretch', { reportIds: ['fk_listings'], from: '2026-05-01', to: '2026-05-31' }, /can only be fetched for yesterday/);
  await refuses('the Drive not connected', FK, /Drive is not connected/, async (r) => { r.state.driveAt = 0; });
  const fl = await refuses('more of Flipkart\'s twenty than are left', { reportIds: ['fk_orders', 'fk_payments'], from: '2026-05-01', to: '2026-05-31' }, /2 reports a day|20 reports a day and 1 are left/, async (r) => { r.state.left = 1; });
  check('the allowance refusal says when it can run again', /midnight|tomorrow/.test(fl.error));
  await refuses('Meesho without the seller\'s panel name', { reportIds: ['me_orders'], from: '2026-05-01', to: '2026-05-31' }, /panel/i, async (r) => { r.state.panel = ''; });
}

{
  check('a report that CAN go back is fine for a past stretch (Flipkart orders, 1-31 May)', whyThisAskIsRefused(BOOK, FK, { now: NOW, panel: 'p', leftToday: 20, spentByOthers: 0, waitingCount: 0 }) === '');
  check('a report that only exists for now is fine for yesterday alone', whyThisAskIsRefused(BOOK, { reportIds: ['fk_listings'], from: '2026-10-30', to: '2026-10-30' }, { now: NOW, panel: 'p', leftToday: 20, spentByOthers: 0, waitingCount: 0 }) === '');
  check('exactly the days left is allowed, one more is not', whyThisAskIsRefused(BOOK, { ...FK, reportIds: ['fk_orders', 'fk_payments'] }, { now: NOW, panel: 'p', leftToday: 2, spentByOthers: 0, waitingCount: 0 }) === ''
    && whyThisAskIsRefused(BOOK, { ...FK, reportIds: ['fk_orders', 'fk_payments'] }, { now: NOW, panel: 'p', leftToday: 2, spentByOthers: 1, waitingCount: 0 }) !== '');
  check('free reports never touch the allowance', whyThisAskIsRefused(BOOK, { reportIds: ['me_orders'], from: '2026-05-01', to: '2026-05-31' }, { now: NOW, panel: 'p', leftToday: 0, spentByOthers: 0, waitingCount: 0 }) === '');
}

/* ------------------------------------------------------------------ waiting */
{
  const r = rig();
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  r.fake.setTheComputer('active');
  const said = await call(r, 'autosync_run', FK);
  check('an ask while the computer is in use is kept as waiting and returns at once with an id', said.ok && said.result.state === 'waiting' && /^[0-9a-f]{16}$/.test(said.result.ask_id));
  check('it did NOT start, and the one-minute alarm will look again', r.state.runNow.length === 0 && Boolean(await r.chrome.alarms.get(AI_ALARM)));
  const result = await call(r, 'autosync_result', {});
  check('the result says it is waiting for the computer to be free', result.ok && result.result.state === 'waiting' && /waiting for the computer to be free/i.test(result.result.message));
  const st = await call(r, 'autosync_status', {});
  check('and so does the status', st.result.waiting_asks === 1 && st.result.latest_ask.state === 'waiting');
  const shown = await aiState(r.chrome, r.parts);
  check('the panel line reads "Asked by your AI: <reports>, <dates> -- waiting for the computer to be free"',
    shown.asks.length === 1 && /^Asked by your AI: .+, 2026-05-01 to 2026-05-31 -- waiting for the computer to be free$/.test(shown.asks[0].panel_line));
  const twin = await call(r, 'autosync_run', FK);
  check('the same ask again is the same ask, not kept twice', twin.ok && twin.result.ask_id === said.result.ask_id && (await asksOf(r)).length === 1);

  await processTheAsks(r.chrome, r.parts);
  check('while the computer stays in use, a minute later it still has not started', r.state.runNow.length === 0);
  r.fake.setTheComputer('idle');
  await processTheAsks(r.chrome, r.parts);
  check('once the computer has been left alone, it starts, through the Run now door with exactly the reports and days asked', r.state.runNow.length === 1
    && r.state.runNow[0].do === 'run-now' && r.state.runNow[0].reportIds.join() === 'fk_orders' && r.state.runNow[0].from === '2026-05-01' && r.state.runNow[0].to === '2026-05-31');
  check('and it is written down as running', (await asksOf(r))[0].state === 'running');
  await processTheAsks(r.chrome, r.parts);
  await processTheAsks(r.chrome, r.parts);
  check('asked to move on again (the alarm, a restart), it is NOT started a second time', r.state.runNow.length === 1);
}

{
  const r = rig();
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  r.fake.setTheComputer('idle');
  await r.chrome.storage.local.set({ [THE_NIGHT]: { startedAt: NOW - 60000, finishedAt: 0, doing: 'fk_returns', left: [], done: [] } });
  const said = await call(r, 'autosync_run', FK);
  check('with a run already going the ask waits for it (and the status says which wait)', said.ok && said.result.state === 'waiting' && r.state.runNow.length === 0
    && /run that is going now/.test((await call(r, 'autosync_result', {})).result.message));
  await r.chrome.storage.local.set({ [THE_NIGHT]: { startedAt: NOW - 60000, finishedAt: NOW - 1000, doing: null, left: [], done: [] } });
  await processTheAsks(r.chrome, r.parts);
  check('when that run is over, the ask starts', r.state.runNow.length === 1);
}

{
  const r = rig();
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  r.fake.setTheComputer('active');
  const a = (await call(r, 'autosync_run', FK)).result.ask_id;
  const b = (await call(r, 'autosync_run', { reportIds: ['me_orders'], from: '2026-05-01', to: '2026-05-31' })).result.ask_id;
  r.fake.setTheComputer('idle');
  await processTheAsks(r.chrome, r.parts);
  check('two asks at once: the first starts, the second keeps waiting', r.state.runNow.length === 1 && r.state.runNow[0].reportIds[0] === 'fk_orders'
    && (await asksOf(r)).map((x) => x.state).join() === 'running,waiting');
  // The first one's run finishes.
  await r.chrome.storage.local.set({ [THE_NIGHT]: { startedAt: NOW + 1, finishedAt: NOW + 5000, doing: null, left: [], done: [{ reportId: 'fk_orders', state: 'landed', say: 'ok', size: 10, dataDate: '2026-05-31' }] } });
  await noteAFile(r.chrome, 'flipkart_orders_2026-05-01_to_2026-05-31.xlsx');
  await processTheAsks(r.chrome, r.parts);
  const asks = await asksOf(r);
  check('when the first run ends it is done, with what landed and the file name', asks[0].id === a && asks[0].state === 'done' && asks[0].results[0].state === 'landed'
    && asks[0].files.join() === 'flipkart_orders_2026-05-01_to_2026-05-31.xlsx');
  check('and then, in order, the second starts', asks[1].id === b && r.state.runNow.length === 2 && r.state.runNow[1].reportIds[0] === 'me_orders');
  const done = await call(r, 'autosync_result', { ask_id: a });
  check('autosync_result reads the outcome back in plain words', done.ok && done.result.state === 'done' && /1 landed/.test(done.result.message) && done.result.files_landed.length === 1);
  const none = await call(r, 'autosync_result', { ask_id: 'ffffffffffffffff' });
  check('an unknown ask id is said so, with the ids there are', none.ok === false && /No ask has the id/.test(none.error) && none.error.includes(a));
}

{
  const r = rig();
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  r.fake.setTheComputer('idle');
  r.state.refuseRunNow = 'Kartaan said this sync may not run (status 403).';
  const said = await call(r, 'autosync_run', FK);
  await settle();
  const kept = (await asksOf(r))[0];
  check('the answer to the AI comes at once, as "asked, waiting" (the start is not waited for)', said.ok && said.result.state === 'waiting');
  check('if the Run now door itself says no, the ask is refused with its words and not retried', kept.state === 'refused' && /Kartaan said this sync may not run/.test(kept.why));
  await processTheAsks(r.chrome, r.parts);
  check('and nothing is started later', r.state.runNow.length === 1);
}

{
  // An update or restart while an ask is running: the running ask is followed by reading the night, never started again.
  let t = NOW;
  const r = rig({ clock: () => t });
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  r.fake.setTheComputer('idle');
  r.state.writesANight = false; // the extension is restarted before the run's night is written
  await call(r, 'autosync_run', FK);
  await settle();
  await processTheAsks(r.chrome, r.parts); // a fresh worker after the update
  check('after an update the running ask is still running and was not started again', (await asksOf(r))[0].state === 'running' && r.state.runNow.length === 1);
  t += GIVE_UP_AFTER_MS + 1000;
  await processTheAsks(r.chrome, r.parts);
  const failed = (await asksOf(r))[0];
  check('a run that never began is called failed, in words, after ten minutes -- and still never started again', failed.state === 'failed' && /Ask again/.test(failed.why) && r.state.runNow.length === 1);
}

{
  const r = rig();
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  r.fake.setTheComputer('active');
  const days = ['2026-05-01', '2026-05-02', '2026-05-03', '2026-05-04', '2026-05-05', '2026-05-06'];
  let last;
  for (const d of days) last = await call(r, 'autosync_run', { reportIds: ['me_orders'], from: d, to: d });
  check(`no more than ${MOST_WAITING} asks wait at once`, (await asksOf(r)).length === MOST_WAITING && last.ok === false && /already waiting/.test(last.error));
}

{
  // The switch.
  const r = rig();
  r.fake.setTheComputer('active');
  await setTheSwitch(r.chrome, r.parts, true);
  check('turning the switch on opens the helper and sets the one-minute alarm', r.state.opened === 1 && Boolean(await r.chrome.alarms.get(AI_ALARM)));
  await call(r, 'autosync_run', FK);
  await setTheSwitch(r.chrome, r.parts, false);
  const dropped = (await asksOf(r))[0];
  check('turning it off closes the helper and drops waiting asks, in words', r.state.closed === 1 && dropped.state === 'failed' && /turned AutoSync's AI switch off/.test(dropped.why) && !(await r.chrome.alarms.get(AI_ALARM)));
  check('with the switch off again every tool says so', (await call(r, 'autosync_status', {})).error === NEEDS_THE_SWITCH);
}

{
  // The port: opens only through the switch; a call comes in, an answer goes out; no helper installed turns the switch off in words.
  const r = rig();
  const opened = [];
  const sent = [];
  let listeners;
  r.chrome.runtime.connectNative = (name) => {
    opened.push(name);
    listeners = { msg: [], gone: [] };
    return { onMessage: { addListener: (f) => listeners.msg.push(f) }, onDisconnect: { addListener: (f) => listeners.gone.push(f) }, postMessage: (m) => sent.push(m), disconnect: () => {} };
  };
  const thePort = makeThePort(r.chrome, r.parts);
  await keepWatching(r.chrome, r.parts, thePort);
  check('with the switch off nothing opens the helper, however often the worker wakes', opened.length === 0 && !thePort.isOpen());
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  r.fake.setTheComputer('active');
  await keepWatching(r.chrome, r.parts, thePort);
  check('with it on, waking opens exactly one connection to com.kartaan.bridge', opened.join() === HOST && thePort.isOpen());
  await keepWatching(r.chrome, r.parts, thePort);
  check('and not a second', opened.length === 1);
  await Promise.all(listeners.msg.map((f) => f({ id: 7, tool: 'autosync_status', args: {} })));
  await new Promise((res) => setTimeout(res, 20));
  check('a tool call on the port is answered with the same id', sent.length === 1 && sent[0].id === 7 && sent[0].ok === true);
  await Promise.all(listeners.msg.map((f) => f({ id: 8, tool: 'fill_ticked', args: {} })));
  await new Promise((res) => setTimeout(res, 20));
  check('a tool that is not AutoSync\'s (say a Tune tool) is refused in words', sent[1].id === 8 && sent[1].ok === false && /not an AutoSync tool/.test(sent[1].error));
  r.chrome.runtime.lastError = { message: 'Specified native messaging host not found.' };
  await Promise.all(listeners.gone.map((f) => f()));
  r.chrome.runtime.lastError = undefined;
  check('no helper on the computer: the switch goes off and says why in plain words', (await r.chrome.storage.local.get(AI_SWITCH))[AI_SWITCH] === false
    && /helper is not set up/i.test((await aiState(r.chrome, r.parts)).note));
}

{
  // Review H1: the alarm is put back on every waking (Chrome can clear it on an update or restart), so a waiting ask is not stranded.
  const r = rig();
  const thePort = makeThePort(r.chrome, { ...r.parts });
  r.chrome.runtime.connectNative = () => ({ onMessage: { addListener() {} }, onDisconnect: { addListener() {} }, postMessage() {}, disconnect() {} });
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  r.fake.setTheComputer('active');
  await call(r, 'autosync_run', FK);
  await r.chrome.alarms.clear(AI_ALARM);
  await keepWatching(r.chrome, r.parts, thePort);
  check('a cleared alarm is back after the worker wakes', Boolean(await r.chrome.alarms.get(AI_ALARM)));
  r.fake.setTheComputer('idle');
  await keepWatching(r.chrome, r.parts, thePort);
  check('and the waiting ask then starts without anybody asking again', r.state.runNow.length === 1);
}

{
  // Review M1/M2/M3, security M1, idle error.
  const r = rig();
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  r.fake.setTheComputer('idle');
  r.chrome.idle.queryState = async () => { throw new Error('no answer'); };
  await call(r, 'autosync_run', FK);
  await settle();
  check('if Chrome cannot say whether the seller is at the computer, an ask from the AI does NOT start', r.state.runNow.length === 0);
}
{
  const r = rig();
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  r.fake.setTheComputer('active');
  let held = false;
  const quick = r.parts.panelAnswer;
  r.parts.panelAnswer = async (asked) => {
    if (asked.do !== 'run-now') return quick(asked);
    held = true;
    await new Promise((res) => setTimeout(res, 300)); // Kartaan's check and a slow portal page
    return { started: ['x'] };
  };
  await call(r, 'autosync_run', FK);
  r.fake.setTheComputer('idle');
  const slow = processTheAsks(r.chrome, r.parts);
  await settle();
  const t0 = Date.now();
  const st = await call(r, 'autosync_status', {});
  check('while a run is being started (slow), status is still answered at once and nothing waits behind it', held && st.ok && Date.now() - t0 < 200);
  await slow;
}
{
  // The AI's own daily ceiling.
  const r = rig();
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  r.fake.setTheComputer('active');
  const out = [];
  for (let i = 0; i < 9; i += 1) {
    out.push(await call(r, 'autosync_run', { reportIds: ['fk_orders', 'fk_payments'], from: `2026-05-0${i + 1}`, to: `2026-05-0${i + 1}` }));
    await settle();
    await r.chrome.storage.local.set({ [AI_ASKS]: (await asksOf(r)).map((x) => ({ ...x, state: 'done' })) }); // finished, so only the daily ceiling can stop the next
  }
  check('the AI may ask for at most 16 of Flipkart\'s 20 a day (4 are kept for the seller\'s own runs)', out.slice(0, 8).every((x) => x.ok) && out[8].ok === false && /may use 16/.test(out[8].error) && /midnight/.test(out[8].error));
  const many = rig();
  await many.chrome.storage.local.set({ [AI_SWITCH]: true });
  many.fake.setTheComputer('active');
  let blocked = null;
  for (let i = 1; i <= 13; i += 1) {
    // Free reports, one day each; each batch of five is allowed to finish so the five-waiting limit is not what stops it.
    const a = await many.parts.theBook();
    const said = await call(many, 'autosync_run', { reportIds: ['me_orders'], from: `2026-04-${String(i).padStart(2, '0')}`, to: `2026-04-${String(i).padStart(2, '0')}` });
    if (!said.ok && /already waiting/.test(said.error)) {
      const asks = await asksOf(many);
      await many.chrome.storage.local.set({ [AI_ASKS]: asks.map((x) => ({ ...x, state: 'done' })) });
      i -= 1;
    } else if (!said.ok) { blocked = said; break; }
  }
  check('and for at most 12 asks a day, however small', blocked && /12 is the most a day/.test(blocked.error));
}
{
  // Review M2: a run that some other start began in the gap is never adopted as the ask's.
  let t = NOW;
  const r = rig({ clock: () => t });
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  r.fake.setTheComputer('idle');
  r.state.writesANight = false;
  await call(r, 'autosync_run', FK);
  await settle();
  await r.chrome.storage.local.set({ [THE_NIGHT]: { startedAt: NOW + 5000, finishedAt: NOW + 9000, doing: null, left: [], done: [{ reportId: 'fk_returns', state: 'landed', say: 'x', size: 1 }] } });
  t = NOW + 20000;
  await processTheAsks(r.chrome, r.parts);
  const ask = (await asksOf(r))[0];
  check('a timed sync that started in the gap is not adopted: its results are not the ask\'s', ask.state === 'running' && ask.results.length === 0);
}
{
  // Review M1: a two-website ask is not called done in the gap between its websites.
  let t = NOW;
  const r = rig({ clock: () => t });
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  r.fake.setTheComputer('idle');
  await call(r, 'autosync_run', { reportIds: ['fk_orders', 'me_orders'], from: '2026-05-01', to: '2026-05-31' });
  await settle();
  await r.chrome.storage.local.set({ [THE_NIGHT]: { startedAt: NOW, finishedAt: NOW + 1000, doing: null, left: [], done: [{ reportId: 'fk_orders', state: 'landed', say: 'x', size: 1 }] }, [THE_QUEUE]: [] });
  t = NOW + 30000;
  await processTheAsks(r.chrome, r.parts);
  check('the list is empty and the first website has ended, yet the ask is still running (the next website is being started)', (await asksOf(r))[0].state === 'running');
  t = NOW + 1000 + 3 * 60 * 1000 + 1;
  await processTheAsks(r.chrome, r.parts);
  check('three minutes after the last run ended it is done', (await asksOf(r))[0].state === 'done');
}
{
  // Security review M2: asked again at the moment of starting.
  const r = rig();
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  r.fake.setTheComputer('active');
  await call(r, 'autosync_run', { reportIds: ['fk_orders', 'fk_payments'], from: '2026-05-01', to: '2026-05-31' });
  r.state.left = 1; // the seller's own timed run spent the day's allowance while the ask waited
  r.fake.setTheComputer('idle');
  await processTheAsks(r.chrome, r.parts);
  const ask = (await asksOf(r))[0];
  check('an ask whose allowance was spent while it waited is refused, in words, instead of started', ask.state === 'refused' && /no longer possible/.test(ask.why) && r.state.runNow.length === 0);
  const forged = rig();
  await forged.chrome.storage.local.set({ [AI_SWITCH]: true, [AI_ASKS]: [{ id: 'aaaaaaaaaaaaaaaa', reportIds: ['not_a_report'], from: '2026-05-01', to: '2026-05-31', askedAt: NOW, state: 'waiting', results: [], files: [] }] });
  forged.fake.setTheComputer('idle');
  await processTheAsks(forged.chrome, forged.parts);
  check('an ask written into storage by anything else is checked like any other, and refused', (await asksOf(forged))[0].state === 'refused' && forged.state.runNow.length === 0);
}

{
  // The only places the helper is opened, and the keys.
  const here = new URL('.', import.meta.url);
  const files = readdirSync(here).filter((f) => /\.js$/.test(f) && !/\.test\.js$/.test(f));
  const offenders = files.filter((f) => /connectNative/.test(readFileSync(new URL(f, here), 'utf8')) && f !== 'bridge.js');
  check('connectNative appears in bridge.js only', offenders.length === 0 && /connectNative/.test(readFileSync(new URL('bridge.js', here), 'utf8')));
  const manifest = JSON.parse(readFileSync(new URL('manifest.json', here), 'utf8'));
  check('nativeMessaging is an OPTIONAL permission (an update never switches the extension off), asked for at the switch', !manifest.permissions.includes('nativeMessaging')
    && manifest.optional_permissions.includes('nativeMessaging') && /permissions\.request\(\{ permissions: \['nativeMessaging'\] \}\)/.test(readFileSync(new URL('panel.js', here), 'utf8')));
  const worker = readFileSync(new URL('worker.js', here), 'utf8');
  check('the AI switch is a panel-only ask, answered by the panel door', /mayAsk: \[\.\.\.THE_PANEL_ASKS, 'ai-switch'\]/.test(worker));
  const bridge = readFileSync(new URL('bridge.js', here), 'utf8');
  check('the AI door goes through the Run now door and never calls a walk, a Drive or a portal itself', /panelAnswer\(\{ do: 'run-now'/.test(bridge) && !/tabs\.|scripting\.|fetch\(/.test(bridge));
  check('no key-looking text in the AI door', !/AIzaSy|ghp_|amzn1\./.test(bridge));
}

console.log(`\n${ran - failures} of ${ran} passed`);
process.exit(failures ? 1 : 0);
