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
        return state.refuseRunNow ? { wrong: state.refuseRunNow } : { started: ['x'] };
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
  const kept = (await asksOf(r))[0];
  check('if the Run now door itself says no, the ask is refused with its words and not retried', kept.state === 'refused' && /Kartaan said this sync may not run/.test(kept.why) && said.result.state === 'refused');
  await processTheAsks(r.chrome, r.parts);
  check('and nothing is started later', r.state.runNow.length === 1);
}

{
  // An update or restart while an ask is running: the running ask is followed by reading the night, never started again.
  let t = NOW;
  const r = rig({ clock: () => t });
  await r.chrome.storage.local.set({ [AI_SWITCH]: true });
  r.fake.setTheComputer('idle');
  await call(r, 'autosync_run', FK);
  const running = (await asksOf(r))[0];
  await processTheAsks(r.chrome, r.parts); // a fresh worker after the update
  check('after an update the running ask is still running and was not started again', running.state === 'running' && r.state.runNow.length === 1);
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
