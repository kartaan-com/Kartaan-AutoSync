/* Checks for AutoSync driven by the seller's AI (AD1, D818/D820).
 *
 * Run: node extension/bridge.test.js
 *
 * **THE ONES THAT MATTER:** (1) with the switch off every tool says so and nothing is kept; (2) an ask is refused, in words, before anything is
 * kept, for each reason in the brief; (3) an ask never starts while the computer is in use or a run is going, and never twice; (4) it goes through
 * the Run now door, not around it; (5) `connectNative` is opened in one file only, and only by turning the switch on.
 */

import { readFileSync, readdirSync } from 'node:fs';
import { deepStrictEqual } from 'node:assert';
import { installFakeChrome } from '../test/fake-chrome.js';
import {
  AI_ALARM, AI_ASKS, AI_NOTE, AI_SPENT, AI_SWITCH, BRIDGE_TOOLS, GIVE_UP_AFTER_MS, HOST, MOST_WAITING, NEEDS_THE_SWITCH, aiState, answerTheBridge,
  keepWatching, makeThePort, noteAFile, processTheAsks, setTheSwitch, slimAsk, whyThisAskIsRefused,
} from './bridge.js';
import { IDLE_SECONDS } from './idle.js';
import { LAST_LANDED, THE_NIGHT, theDay } from './nightly.js';
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
  const state = { runNow: [], left, driveAt, panel, refuseRunNow: '', cannot: [] };
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
            /* As the real panel answers: Meesho needs the panel name, Flipkart and Amazon only the Drive. */
            platforms: ['flipkart', 'meesho', 'amazon'].map((id) => ({
              id, ready: Boolean(state.driveAt) && (id !== 'meesho' || Boolean(state.panel)),
            })),
            flipkart: { allowedADay: 20, askedForToday: 20 - state.left, leftToday: state.left },
            timed: 'timed' in state ? state.timed : { said: 'The timed sync will fetch: 0 reports' },
            reports: state.reports || reportsOf.map((r) => ({ id: r.id, name: r.name, platform: r.platform, canBeFetched: true, state: '', say: '' })),
            cannotBeFetched: state.cannot,
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
const same = (a, b) => { try { deepStrictEqual(a, b); return true; } catch (wrong) { return false; } };
const FAR = new Date(2031, 2, 15, 10, 0).getTime(); // a clock nowhere near the real one, so an answer taken from the real clock is seen
const switchedOn = async (r, computer = 'active') => { await r.chrome.storage.local.set({ [AI_SWITCH]: true }); r.fake.setTheComputer(computer); };
const anAsk = (id, over = {}) => ({ id, reportIds: ['fk_orders'], from: '2026-05-01', to: '2026-05-02', askedAt: NOW, state: 'waiting', waitingFor: 'computer', results: [], files: [], ...over });
const keepAsks = (r, list) => r.chrome.storage.local.set({ [AI_ASKS]: list });
const nameOf = (id) => BOOK.reports.find((x) => x.id === id).name;

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
  check('BR1: the finished ask carries the run\'s end time and the results exactly as the night wrote them',
    asks[0].finishedAt === NOW + 5000 && asks[0].startedAt === NOW && asks[0].nightStartedAt === NOW
    && same(asks[0].results, [{ report: 'fk_orders', day: '2026-05-31', state: 'landed', said: 'ok' }]));
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

/* ================================================================ BR1: exact words and fields (the prover's survivors) */
{
  // What an ask says about itself: every field, every state.
  const book = { reports: [{ id: 'a', name: 'Alpha' }, { id: 'c', name: 'Gamma' }, { id: 'n' }] };
  const base = { id: 'abcd', reportIds: ['c', 'zzz', 'n'], from: '2026-05-01', to: '2026-05-02', askedAt: 0, state: 'waiting', waitingFor: 'computer', results: [], files: [] };
  check('BR1: report names come from the book, fall back to the id when unknown or unnamed', same(slimAsk(book, base).report_names, ['Gamma', 'zzz', 'n']));
  check('BR1: a book with no reports at all gives the ids', same(slimAsk({}, base).report_names, ['c', 'zzz', 'n']));
  const full = {
    ...base,
    state: 'done',
    startedAt: 1000,
    finishedAt: 2000,
    results: [
      { report: 'c', day: '2026-05-01', state: 'landed', said: 'ok', extra: 'x' },
      { report: 'zzz', day: '', state: 'failed', said: 'no' },
      { report: 'n', day: 'd', state: 'nothing-to-fetch', said: '' },
    ],
    files: ['f1.xlsx'],
  };
  check('BR1: a finished ask says everything about itself, in these fields and no others', same(slimAsk(book, full), {
    ask_id: 'abcd',
    reports: ['c', 'zzz', 'n'],
    report_names: ['Gamma', 'zzz', 'n'],
    from: '2026-05-01',
    to: '2026-05-02',
    state: 'done',
    message: 'Finished: 1 landed, 1 did not, 1 had nothing to fetch.',
    asked_at: '1970-01-01T00:00:00.000Z',
    started_at: '1970-01-01T00:00:01.000Z',
    finished_at: '1970-01-01T00:00:02.000Z',
    results: [
      { report: 'c', day: '2026-05-01', state: 'landed', said: 'ok' },
      { report: 'zzz', day: '', state: 'failed', said: 'no' },
      { report: 'n', day: 'd', state: 'nothing-to-fetch', said: '' },
    ],
    files_landed: ['f1.xlsx'],
  }));
  const bare = slimAsk(book, base);
  check('BR1: an ask not yet started or finished has no started_at or finished_at', !('started_at' in bare) && !('finished_at' in bare) && bare.asked_at === '1970-01-01T00:00:00.000Z');
  const said = (over) => slimAsk(book, { ...base, ...over }).message;
  check('BR1: waiting for the computer', said({}) === 'Waiting for the computer to be free (it has to be left alone for 3 minutes).');
  check('BR1: waiting for a run', said({ waitingFor: 'run' }) === 'Waiting for the run that is going now to finish.');
  check('BR1: running', said({ state: 'running' }) === 'AutoSync is fetching these now.');
  check('BR1: done with nothing recorded', said({ state: 'done' }) === 'Finished, with nothing recorded against the reports.');
  check('BR1: refused says why, or says Refused.', said({ state: 'refused', why: 'because' }) === 'because' && said({ state: 'refused' }) === 'Refused.');
  check('BR1: failed says why, or says Did not finish.', said({ state: 'failed', why: 'because' }) === 'because' && said({ state: 'failed' }) === 'Did not finish.');
  check('BR1: a state it does not know says nothing', said({ state: 'strange' }) === '');
}

{
  // Status: every field.
  const r = rig();
  await switchedOn(r);
  r.state.reports = [
    { id: 'fk_orders', name: 'FK Orders', platform: 'flipkart', canBeFetched: true, state: 'landed', say: 'fine' },
    { id: 'fk_returns', name: 'FK Returns', platform: 'flipkart', canBeFetched: false, state: 'failed' },
    { id: 'me_orders', name: 'ME Orders', platform: 'meesho', canBeFetched: true, state: '' },
  ];
  r.state.cannot = [{ id: 'x', name: 'X', why: 'because', junk: 1 }];
  await r.chrome.storage.local.set({ [LAST_LANDED]: { fk_orders: ['2026-05-02', '2026-05-30', '2026-05-10'], fk_returns: [] } });
  const s = (await call(r, 'autosync_status', {})).result;
  check('BR1: status says each report\'s id, name, platform, whether it can be fetched, its last run and the last day that landed', same(s.reports, [
    { id: 'fk_orders', name: 'FK Orders', platform: 'flipkart', can_be_fetched: true, last_run: { state: 'landed', said: 'fine' }, last_landed_day: '2026-05-30' },
    { id: 'fk_returns', name: 'FK Returns', platform: 'flipkart', can_be_fetched: false, last_run: { state: 'failed', said: '' }, last_landed_day: null },
    { id: 'me_orders', name: 'ME Orders', platform: 'meesho', can_be_fetched: true, last_run: null, last_landed_day: null },
  ]));
  check('BR1: status lists what cannot be fetched with its reason, and nothing else about it', same(s.cannot_be_fetched, [{ id: 'x', name: 'X', why: 'because' }]));
  check('BR1: status top fields', s.ready_to_run === true && s.drive_connected === true && s.run_going_now === false && s.waiting_asks === 0
    && s.computer_in_use_now === true && s.flipkart_requests_left_today === 20 && s.flipkart_requests_a_day === 20
    && s.timed_sync === 'The timed sync will fetch: 0 reports' && s.latest_ask === null);
  r.state.timed = undefined;
  r.state.cannot = undefined;
  const none = (await call(r, 'autosync_status', {})).result;
  check('BR1: no timed sync and nothing listed as unfetchable read as empty, not as a crash', none.timed_sync === '' && same(none.cannot_be_fetched, []));
  r.state.timed = {};
  check('BR1: a timed sync with no words reads as empty', (await call(r, 'autosync_status', {})).result.timed_sync === '');
  await r.chrome.storage.local.set({ [THE_NIGHT]: { startedAt: NOW - 1000, finishedAt: 0, doing: 'fk_orders', left: [], done: [] } });
  check('BR1: a run that has not finished is going now', (await call(r, 'autosync_status', {})).result.run_going_now === true);
  await r.chrome.storage.local.set({ [THE_NIGHT]: { startedAt: NOW - 1000, finishedAt: NOW - 500, doing: null, left: [], done: [] } });
  check('BR1: a run that has finished is not going now', (await call(r, 'autosync_status', {})).result.run_going_now === false);
  r.state.driveAt = 0;
  const nodrive = (await call(r, 'autosync_status', {})).result;
  check('BR1: with no Drive, not ready and not connected', nodrive.ready_to_run === false && nodrive.drive_connected === false);
  r.state.driveAt = 1;
  r.state.panel = '';
  const nopanel = (await call(r, 'autosync_status', {})).result;
  check('BR1: with a Drive but no panel name, connected and still ready (Flipkart and Amazon need no panel name, AJ9 6)', nopanel.ready_to_run === true && nopanel.drive_connected === true);
  const asks = [anAsk('a1111111'), anAsk('a2222222', { state: 'done' })];
  await keepAsks(r, asks);
  const withAsks = (await call(r, 'autosync_status', {})).result;
  check('BR1: status counts only the waiting asks and shows the latest', withAsks.waiting_asks === 1 && withAsks.latest_ask.ask_id === 'a2222222' && withAsks.latest_ask.state === 'done');
}

{
  // Flipkart's allowance already promised to earlier asks.
  const r = rig({ left: 2 });
  await switchedOn(r);
  await keepAsks(r, [anAsk('a1111111'), anAsk('a2222222', { reportIds: ['fk_payments'] }), anAsk('a3333333', { reportIds: ['fk_orders', 'fk_payments'], state: 'done' })]);
  const said = await call(r, 'autosync_run', { reportIds: ['fk_orders'], from: '2026-06-01', to: '2026-06-02' });
  check('BR1: what waiting asks have promised counts against the day\'s allowance, and says so', said.ok === false
    && said.error === 'Not asked: Flipkart allows 20 reports a day and 2 are left today, 2 of them already promised to earlier asks; this ask needs 1. '
    + 'The count starts again after midnight on the seller\'s computer. Ask for fewer, or ask again tomorrow.');
  const r2 = rig({ left: 2 });
  await switchedOn(r2);
  await keepAsks(r2, [anAsk('a1111111'), anAsk('a3333333', { reportIds: ['fk_orders', 'fk_payments'], state: 'done' }), anAsk('a4444444', { reportIds: ['fk_orders', 'fk_payments'], state: 'running' })]);
  const fine = await call(r2, 'autosync_run', { reportIds: ['fk_payments'], from: '2026-06-01', to: '2026-06-02' });
  check('BR1: asks that are done or running have promised nothing more', fine.ok === true && fine.result.state === 'waiting');
}

{
  // The ask as kept; the same ask twice; the AI's own count of the day.
  const r = rig({ clock: () => FAR });
  await switchedOn(r);
  const first = await call(r, 'autosync_run', FK);
  const kept = (await asksOf(r))[0];
  check('BR1: an ask is kept as asked, at the time it was asked, waiting for the computer', kept.id === first.result.ask_id && same(kept.reportIds, ['fk_orders']) && kept.from === FK.from && kept.to === FK.to
    && kept.askedAt === FAR && kept.state === 'waiting' && kept.waitingFor === 'computer' && same(kept.results, []) && same(kept.files, []));
  check('BR1: and the answer says it was asked, what it waits for, and where to read the outcome', first.result.message === 'Asked. Waiting for the computer to be free (it has to be left alone for 3 minutes). Read the outcome with autosync_result.');
  check('BR1: the AI\'s count of the day is kept in the seller\'s own day', same((await r.chrome.storage.local.get(AI_SPENT))[AI_SPENT], { day: theDay(FAR), flipkart: 1, asks: 1 }));
  const again = await call(r, 'autosync_run', FK);
  check('BR1: the same ask while it waits says so in words', again.ok === true && again.result.ask_id === first.result.ask_id && again.result.state === 'waiting'
    && again.result.message === 'This same ask is already in. Waiting for the computer to be free (it has to be left alone for 3 minutes).');
  await settle(); // the start the ask above set going has to finish before the stored asks are rewritten
  await keepAsks(r, (await asksOf(r)).map((x) => ({ ...x, state: 'running' })));
  const running = await call(r, 'autosync_run', { ...FK, reportIds: ['fk_orders'] });
  await settle();
  check('BR1: the same ask while it runs says so in words', running.ok === true && running.result.state === 'running' && running.result.message === 'This same ask is already in. AutoSync is fetching these now.');
  await keepAsks(r, (await asksOf(r)).map((x) => ({ ...x, state: 'done' })));
  const next = await call(r, 'autosync_run', FK);
  check('BR1: the same ask once it is done is a new ask', next.ok === true && next.result.ask_id !== first.result.ask_id && (await asksOf(r)).length === 2);
  const order = rig();
  await switchedOn(order);
  const one = await call(order, 'autosync_run', { reportIds: ['fk_orders', 'fk_payments'], from: '2026-05-01', to: '2026-05-31' });
  const two2 = await call(order, 'autosync_run', { reportIds: ['fk_payments', 'fk_orders'], from: '2026-05-01', to: '2026-05-31' });
  check('BR1: the same reports named in another order are the same ask', two2.result.ask_id === one.result.ask_id);
  const other = await call(order, 'autosync_run', { reportIds: ['fk_orders', 'fk_payments'], from: '2026-05-01', to: '2026-05-30' });
  check('BR1: another last day is another ask', other.ok === true && other.result.ask_id !== one.result.ask_id);
}

{
  // Reading an ask back, and the words on a bad request.
  const r = rig();
  await switchedOn(r);
  check('BR1: with no ask yet, the result says so', same(await call(r, 'autosync_result', {}), { ok: true, result: { message: 'No ask has been made yet.' } }));
  check('BR1: null or missing arguments are read as none', same(await call(r, 'autosync_result', null), { ok: true, result: { message: 'No ask has been made yet.' } })
    && same(await call(r, 'autosync_result', undefined), { ok: true, result: { message: 'No ask has been made yet.' } }));
  await keepAsks(r, [anAsk('a1111111'), anAsk('a2222222', { state: 'done' })]);
  const bad = { ok: false, error: 'ask_id is the id autosync_run gave.' };
  check('BR1: an ask_id that is not text is refused in words', same(await call(r, 'autosync_result', { ask_id: 5 }), bad));
  check('BR1: an ask_id that is not hexadecimal is refused in words', same(await call(r, 'autosync_result', { ask_id: 'zzzzzzzz' }), bad) && same(await call(r, 'autosync_result', { ask_id: 'ABCDEF12' }), bad));
  check('BR1: an ask_id too short is refused in words', same(await call(r, 'autosync_result', { ask_id: 'abc1234' }), bad));
  const unknown = await call(r, 'autosync_result', { ask_id: 'abcdef12' });
  check('BR1: an id that is no ask names the ones that are', unknown.ok === false && unknown.error === 'No ask has the id abcdef12. The latest ones are: a1111111, a2222222.');
  check('BR1: no id reads the latest ask', (await call(r, 'autosync_result', {})).result.ask_id === 'a2222222' && (await call(r, 'autosync_result', { ask_id: 'a1111111' })).result.ask_id === 'a1111111');
  const listError = { ok: false, error: 'reportIds must be a list of 1 to 30 report ids from autosync_status.' };
  const days = { from: '2026-05-01', to: '2026-05-02' };
  check('BR1: reportIds that is not a list is refused in words', same(await call(r, 'autosync_run', { ...days, reportIds: 'fk_orders' }), listError) && same(await call(r, 'autosync_run', { ...days }), listError)
    && same(await call(r, 'autosync_run', null), listError) && same(await call(r, 'autosync_run', undefined), listError) && same(await call(r, 'autosync_run', ['fk_orders']), listError));
  check('BR1: an empty list is refused in words', same(await call(r, 'autosync_run', { ...days, reportIds: [] }), listError));
  const many = Array.from({ length: 31 }, (_, i) => `fk_${i}`);
  check('BR1: more than 30 is refused in words', same(await call(r, 'autosync_run', { ...days, reportIds: many }), listError));
  check('BR1: exactly 30 passes this test (and is then judged on what it names)', (await call(r, 'autosync_run', { ...days, reportIds: many.slice(0, 30) })).error.startsWith('Not asked: '));
  check('BR1: something that is not text in the list is refused in words', same(await call(r, 'autosync_run', { ...days, reportIds: [5] }), listError) && same(await call(r, 'autosync_run', { ...days, reportIds: ['fk_orders', null] }), listError));
  check('BR1: an id with capitals, spaces or marks is refused in words', same(await call(r, 'autosync_run', { ...days, reportIds: ['FK_ORDERS'] }), listError) && same(await call(r, 'autosync_run', { ...days, reportIds: ['fk orders'] }), listError)
    && same(await call(r, 'autosync_run', { ...days, reportIds: ['x'.repeat(41)] }), listError));
  const dayError = { ok: false, error: 'from and to must be days written like 2026-05-01.' };
  check('BR1: a first or last day that is not text is refused in words', same(await call(r, 'autosync_run', { reportIds: ['fk_orders'], from: 20260501, to: '2026-05-31' }), dayError)
    && same(await call(r, 'autosync_run', { reportIds: ['fk_orders'], from: '2026-05-01', to: 20260531 }), dayError) && same(await call(r, 'autosync_run', { reportIds: ['fk_orders'] }), dayError));
  const broke = rig();
  await switchedOn(broke);
  broke.parts.panelAnswer = async () => { throw new Error('boom'); };
  check('BR1: if AutoSync cannot read how it stands, the AI is told so in words', same(await call(broke, 'autosync_status', {}), { ok: false, error: 'AutoSync could not answer: boom' }));
  broke.parts.panelAnswer = async () => { throw 'plain words'; };
  check('BR1: a thing thrown that is plain text is told as it is', same(await call(broke, 'autosync_status', {}), { ok: false, error: 'AutoSync could not answer: plain words' }));
  broke.parts.panelAnswer = async () => { throw new Error('y'.repeat(300)); };
  check('BR1: and no more than 200 characters of it', (await call(broke, 'autosync_status', {})).error === `AutoSync could not answer: ${'y'.repeat(200)}`);
  check('BR1: a tool that is not AutoSync\'s is named, cut short', same(await call(r, 'nonsense', {}), { ok: false, error: '"nonsense" is not an AutoSync tool.' }));
}

{
  // Starting: when the door itself throws, and what a refused or vanished ask looks like.
  const boom = rig({ clock: () => FAR });
  await switchedOn(boom, 'idle');
  const quick = boom.parts.panelAnswer;
  boom.parts.panelAnswer = async (asked) => { if (asked.do === 'run-now') throw new Error('door broke'); return quick(asked); };
  await call(boom, 'autosync_run', FK);
  await settle();
  const k = (await asksOf(boom))[0];
  check('BR1: if the Run now door throws, the ask is refused with the words and the time', k.state === 'refused' && k.why === 'AutoSync would not start it: door broke' && k.finishedAt === FAR && k.nightStartedAt === undefined);
  const text = rig();
  await switchedOn(text, 'idle');
  const q2 = text.parts.panelAnswer;
  text.parts.panelAnswer = async (asked) => { if (asked.do === 'run-now') throw 'plain words'; return q2(asked); };
  await call(text, 'autosync_run', FK);
  await settle();
  check('BR1: a plain text thrown is told as it is', (await asksOf(text))[0].why === 'AutoSync would not start it: plain words');
  const refusing = rig({ clock: () => FAR });
  await switchedOn(refusing, 'idle');
  refusing.state.refuseRunNow = 'No, said Kartaan.';
  await call(refusing, 'autosync_run', FK);
  await settle();
  const rf = (await asksOf(refusing))[0];
  check('BR1: if the door answers no, the ask is refused with its words and the time', rf.state === 'refused' && rf.why === 'AutoSync would not start it: No, said Kartaan.' && rf.finishedAt === FAR);

  const gone = rig();
  await switchedOn(gone, 'idle');
  const q3 = gone.parts.panelAnswer;
  gone.parts.panelAnswer = async (asked) => { if (asked.do === 'run-now') { await keepAsks(gone, []); return { wrong: 'x' }; } return q3(asked); };
  await keepAsks(gone, [anAsk('a1111111')]);
  await processTheAsks(gone.chrome, gone.parts);
  check('BR1: an ask that vanished while it was being started is left vanished', (await asksOf(gone)).length === 0);
  const other = rig();
  await switchedOn(other, 'idle');
  const q4 = other.parts.panelAnswer;
  other.parts.panelAnswer = async (asked) => { if (asked.do === 'run-now') { await keepAsks(other, (await asksOf(other)).map((x) => ({ ...x, state: 'done' }))); return { wrong: 'x' }; } return q4(asked); };
  await keepAsks(other, [anAsk('a1111111')]);
  await processTheAsks(other.chrome, other.parts);
  const od = (await asksOf(other))[0];
  check('BR1: an ask that is no longer running when the door answers is not turned into a refusal', od.state === 'done' && od.why === undefined);

  const stale = rig();
  await switchedOn(stale, 'idle');
  stale.state.writesANight = false;
  await stale.chrome.storage.local.set({ [THE_NIGHT]: { startedAt: NOW - 100000, finishedAt: NOW - 90000, doing: null, left: [], done: [] } });
  await keepAsks(stale, [anAsk('a1111111')]);
  await processTheAsks(stale.chrome, stale.parts);
  const sa = (await asksOf(stale))[0];
  check('BR1: an older run already in storage is not taken for the ask\'s own', sa.state === 'running' && sa.nightStartedAt === undefined && stale.state.runNow.length === 1);
  const quiet = rig();
  await switchedOn(quiet, 'idle');
  quiet.state.writesANight = false;
  await keepAsks(quiet, [anAsk('a1111111')]);
  await processTheAsks(quiet.chrome, quiet.parts);
  check('BR1: with no run in storage at all, starting is still written down and does not fall over', (await asksOf(quiet))[0].state === 'running' && (await asksOf(quiet))[0].nightStartedAt === undefined);
}

{
  // Starting only while the switch is on; asked again at the moment of starting.
  const off = rig();
  await keepAsks(off, [anAsk('a1111111')]);
  off.fake.setTheComputer('idle');
  await processTheAsks(off.chrome, off.parts);
  check('BR1: with the switch off nothing waiting is started, whoever moves things on', off.state.runNow.length === 0 && (await asksOf(off))[0].state === 'waiting');
  const drive = rig({ clock: () => FAR });
  await switchedOn(drive);
  await call(drive, 'autosync_run', FK);
  drive.state.driveAt = 0;
  drive.fake.setTheComputer('idle');
  await processTheAsks(drive.chrome, drive.parts);
  const d = (await asksOf(drive))[0];
  check('BR1: a Drive lost while the ask waited refuses it at the moment of starting, in words, with the time', d.state === 'refused' && drive.state.runNow.length === 0 && d.finishedAt === FAR
    && d.why === 'Checked again when it was about to start, and no longer possible: the seller\'s Google Drive is not connected');
}

{
  // A run that never began: only a quiet gap fails the ask.
  const never = async (setup) => {
    let t = NOW;
    const r = rig({ clock: () => t });
    await switchedOn(r, 'idle');
    r.state.writesANight = false;
    await call(r, 'autosync_run', FK);
    await settle();
    t = NOW + GIVE_UP_AFTER_MS + 1000;
    if (setup) await setup(r);
    await processTheAsks(r.chrome, r.parts);
    return (await asksOf(r))[0];
  };
  check('BR1: while a run is going, an ask that seems not to have begun is still waited for',
    (await never((r) => r.chrome.storage.local.set({ [THE_NIGHT]: { startedAt: NOW + 5000, finishedAt: 0, doing: 'fk_orders', left: [], done: [] } }))).state === 'running');
  check('BR1: while the list of runs is not empty, it is still waited for',
    (await never((r) => r.chrome.storage.local.set({ [THE_QUEUE]: ['fk_orders'] }))).state === 'running');
  const finished = await never((r) => r.chrome.storage.local.set({ [THE_NIGHT]: { startedAt: NOW - 50000, finishedAt: NOW - 40000, doing: null, left: [], done: [] } }));
  check('BR1: an older run that has finished does not hold it, and the failure carries the time', finished.state === 'failed' && finished.finishedAt === NOW + GIVE_UP_AFTER_MS + 1000);
  check('BR1: an empty list of runs does not hold it either',
    (await never((r) => r.chrome.storage.local.set({ [THE_QUEUE]: [] }))).state === 'failed');
}

{
  // What the night wrote, read as the ask's own.
  const r = rig();
  await switchedOn(r, 'idle');
  await call(r, 'autosync_run', FK);
  await settle();
  await r.chrome.storage.local.set({ [THE_NIGHT]: { startedAt: NOW, finishedAt: NOW + 1000, doing: null, left: [], done: [{ reportId: 'fk_returns', state: 'failed' }] } });
  await processTheAsks(r.chrome, r.parts);
  const a = (await asksOf(r))[0];
  check('BR1: a result with no day and no words reads as an empty day and empty words', a.state === 'done' && same(a.results, [{ report: 'fk_returns', day: '', state: 'failed', said: '' }]) && a.finishedAt === NOW + 1000);
  check('BR1: and the ask says how it went in words', slimAsk(BOOK, a).message === 'Finished: 0 landed, 1 did not, 0 had nothing to fetch.');
}

{
  // Files that landed.
  const r = rig();
  await switchedOn(r);
  await noteAFile(r.chrome, 'nothing-running.xlsx');
  check('BR1: a file landing with no ask running is not kept anywhere', (await asksOf(r)).length === 0);
  await keepAsks(r, [anAsk('a1111111', { state: 'running', startedAt: NOW, files: Array.from({ length: 200 }, (_, i) => `f${i}.xlsx`) })]);
  await noteAFile(r.chrome, 'one-too-many.xlsx');
  check('BR1: at 200 files no more are kept', (await asksOf(r))[0].files.length === 200 && !(await asksOf(r))[0].files.includes('one-too-many.xlsx'));
  await keepAsks(r, [anAsk('a1111111', { state: 'running', startedAt: NOW })]);
  await noteAFile(r.chrome, 'a.xlsx');
  await noteAFile(r.chrome, 'a.xlsx');
  await noteAFile(r.chrome, 'x'.repeat(300));
  check('BR1: a file is kept once, and a long name is cut at 200', same((await asksOf(r))[0].files, ['a.xlsx', 'x'.repeat(200)]));
}

{
  // The panel's view.
  const r = rig();
  await switchedOn(r);
  const ids = ['fk_orders', 'fk_payments'];
  const line = (a) => `Asked by your AI: ${ids.map(nameOf).join(', ')}, 2026-05-01 to 2026-05-02`;
  await keepAsks(r, [
    anAsk('a1111111', { reportIds: ids }),
    anAsk('a2222222', { reportIds: ids, waitingFor: 'run' }),
    anAsk('a3333333', { reportIds: ids, state: 'running', startedAt: NOW }),
    anAsk('a4444444', { reportIds: ids, state: 'done' }),
    anAsk('a5555555', { reportIds: ids, state: 'refused' }),
    anAsk('a6666666', { reportIds: ids, state: 'failed' }),
  ]);
  await r.chrome.storage.local.set({ [AI_NOTE]: 'a note for the seller' });
  const shown = await aiState(r.chrome, r.parts);
  check('BR1: the panel shows the switch, the note, and the waiting and running asks only, in words', shown.on === true && shown.note === 'a note for the seller' && shown.connected === false
    && shown.asks.map((x) => x.ask_id).join() === 'a1111111,a2222222,a3333333'
    && same(shown.asks.map((x) => x.panel_line), [`${line()} -- waiting for the computer to be free`, `${line()} -- waiting for the run that is going now to finish`, `${line()} -- running now`])
    && shown.asks[0].state === 'waiting' && shown.asks[2].message === 'AutoSync is fetching these now.' && same(shown.asks[0].report_names, ids.map(nameOf)));
  check('BR1: and how long the computer must be left alone', shown.idle_seconds === IDLE_SECONDS && IDLE_SECONDS === 180);
  r.parts.isConnected = () => true;
  check('BR1: the panel says when the helper is connected', (await aiState(r.chrome, r.parts)).connected === true);
  delete r.parts.isConnected;
  check('BR1: and reads no word from the helper as not connected', (await aiState(r.chrome, r.parts)).connected === false);
  await r.chrome.storage.local.set({ [AI_SWITCH]: false });
  const offShown = await aiState(r.chrome, r.parts);
  check('BR1: with the switch off the panel shows it off and no asks', offShown.on === false && same(offShown.asks, []));
  const clean = rig();
  check('BR1: with no note the note is empty', (await aiState(clean.chrome, clean.parts)).note === '');
}

{
  // The switch.
  const r = rig({ clock: () => FAR });
  const removed = [];
  r.chrome.permissions = { remove: async (x) => { removed.push(x); return true; } };
  await r.chrome.storage.local.set({ [AI_NOTE]: 'an old note' });
  r.fake.setTheComputer('active');
  check('BR1: turning it on answers on', same(await setTheSwitch(r.chrome, r.parts, true), { on: true }));
  check('BR1: and clears the old note', (await r.chrome.storage.local.get(AI_NOTE))[AI_NOTE] === '' && (await r.chrome.storage.local.get(AI_SWITCH))[AI_SWITCH] === true);
  await keepAsks(r, [anAsk('a1111111'), anAsk('a2222222', { state: 'running', startedAt: NOW }), anAsk('a3333333', { state: 'done' })]);
  check('BR1: turning it off answers off', same(await setTheSwitch(r.chrome, r.parts, false), { on: false }));
  check('BR1: and hands the helper permission back', same(removed, [{ permissions: ['nativeMessaging'] }]));
  const kept = await asksOf(r);
  check('BR1: and drops only the waiting asks, with the time and the words', kept[0].state === 'failed' && kept[0].finishedAt === FAR
    && kept[0].why === 'The seller turned AutoSync\'s AI switch off before this ask started.' && kept[1].state === 'running' && kept[1].finishedAt === undefined && kept[2].state === 'done');
  const lone = rig();
  check('BR1: with no permission calls to make, turning it off still works', same(await setTheSwitch(lone.chrome, lone.parts, false), { on: false }));
}

{
  // The port in detail.
  const r = rig();
  const opened = [];
  const sent = [];
  let listeners;
  let disconnected = 0;
  let broken = false;
  r.chrome.runtime.connectNative = (name) => {
    if (broken) throw new Error('nope');
    opened.push(name);
    listeners = { msg: [], gone: [] };
    return { onMessage: { addListener: (f) => listeners.msg.push(f) }, onDisconnect: { addListener: (f) => listeners.gone.push(f) }, postMessage: (m) => sent.push(m), disconnect: () => { disconnected += 1; } };
  };
  const thePort = makeThePort(r.chrome, r.parts);
  thePort.close();
  check('BR1: closing a port that is not open does nothing', disconnected === 0 && !thePort.isOpen());
  thePort.open();
  thePort.open();
  check('BR1: opening twice opens one connection', opened.length === 1 && thePort.isOpen());
  thePort.close();
  thePort.close();
  check('BR1: closing disconnects the helper once and the port is shut', disconnected === 1 && !thePort.isOpen());

  broken = true;
  let threw = false;
  try { thePort.open(); } catch (wrong) { threw = true; }
  await settle();
  check('BR1: when Chrome will not open the helper, it does not fall over, stays shut, and says why', threw === false && !thePort.isOpen()
    && (await aiState(r.chrome, r.parts)).note === 'Chrome would not open the helper: nope');
  broken = false;

  await switchedOn(r);
  await r.chrome.storage.local.set({ [AI_NOTE]: '' });
  thePort.open();
  const old = listeners;
  thePort.close();
  r.chrome.runtime.lastError = { message: 'Specified native messaging host not found.' };
  await Promise.all(old.gone.map((f) => f()));
  r.chrome.runtime.lastError = undefined;
  check('BR1: a goodbye from a port that was already closed does nothing', (await r.chrome.storage.local.get(AI_SWITCH))[AI_SWITCH] === true && (await aiState(r.chrome, r.parts)).note === '');

  thePort.open();
  r.chrome.runtime.lastError = { message: 'It went quiet.' };
  await Promise.all(listeners.gone.map((f) => f()));
  r.chrome.runtime.lastError = undefined;
  check('BR1: a helper that closes is noted in words, the port is shut, and the switch stays on', !thePort.isOpen() && (await r.chrome.storage.local.get(AI_SWITCH))[AI_SWITCH] === true
    && (await aiState(r.chrome, r.parts)).note === 'The AI helper closed (It went quiet.). It is opened again within a minute while the switch is on.');
  thePort.open();
  await Promise.all(listeners.gone.map((f) => f()));
  check('BR1: with no reason given it says so', (await aiState(r.chrome, r.parts)).note === 'The AI helper closed (no reason given). It is opened again within a minute while the switch is on.');
  thePort.open();
  r.chrome.runtime.lastError = { message: 'z'.repeat(200) };
  await Promise.all(listeners.gone.map((f) => f()));
  r.chrome.runtime.lastError = undefined;
  check('BR1: and no more than 120 characters of the reason', (await aiState(r.chrome, r.parts)).note.includes(`(${'z'.repeat(120)})`) && !(await aiState(r.chrome, r.parts)).note.includes('z'.repeat(121)));

  thePort.open();
  sent.length = 0;
  await Promise.all(listeners.msg.map((f) => f(null)));
  await settle();
  check('BR1: a message that is nothing is answered, with no id, as not a tool', same(sent, [{ id: null, ok: false, error: '"null" is not an AutoSync tool.' }]));
  sent.length = 0;
  await Promise.all(listeners.msg.map((f) => f({ id: 9, tool: 'autosync_run', args: FK })));
  await settle();
  check('BR1: a tool call carries its own arguments', sent.length === 1 && sent[0].id === 9 && sent[0].ok === true && sent[0].result.state === 'waiting');
  const tooLate = listeners;
  thePort.close();
  sent.length = 0;
  await Promise.all(tooLate.msg.map((f) => f({ id: 10, tool: 'autosync_status', args: {} })));
  await settle();
  check('BR1: an answer for a port that has since closed is not sent', sent.length === 0);
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
