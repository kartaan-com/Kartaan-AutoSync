import { installFakeChrome } from '../test/fake-chrome.js';
import { ASK_AGAIN_MINUTES, IDLE_ALARM, IDLE_SECONDS, WAITING, carryOnWaiting, computerInUse, startWhenFree, whatIsWaiting } from './idle.js';
process.on('uncaughtException', (err) => { console.log(`FAIL  the checks stopped part way through: ${(err && err.message) || String(err)}`); process.exit(1); });
process.on('unhandledRejection', (err) => { console.log(`FAIL  something was waited on and never came back: ${(err && err.message) || String(err)}`); process.exit(1); });
let failures = 0; let ran = 0;
function check(name, passed) { ran++; console.log(`${passed ? 'PASS' : 'FAIL'}  ${name}`); if (!passed) failures++; }

{
  const { chrome, setTheComputer } = installFakeChrome();
  setTheComputer('active');
  check('computerInUse is true while the computer is active', (await computerInUse(chrome)) === true);
  setTheComputer('idle');
  check('computerInUse is false while the computer is idle', (await computerInUse(chrome)) === false);
  setTheComputer('locked');
  check('computerInUse is false while the computer is locked', (await computerInUse(chrome)) === false);
}

{
  const { chrome } = installFakeChrome();
  let asked = null;
  chrome.idle.queryState = async (seconds) => { asked = seconds; return 'idle'; };
  await computerInUse(chrome);
  check('computerInUse asks Chrome for three minutes', asked === IDLE_SECONDS);
  check('the idle wait is three minutes in seconds', IDLE_SECONDS === 180);
}

{
  const { chrome } = installFakeChrome();
  chrome.idle.queryState = () => { throw new Error('no answer'); };
  const warnings = [];
  const originalWarn = console.warn;
  console.warn = (...args) => warnings.push(args);
  let result = true;
  try {
    result = await computerInUse(chrome);
  } catch (error) {
    result = error;
  } finally {
    console.warn = originalWarn;
  }
  check('computerInUse carries on when Chrome cannot answer', result === false);
  check('computerInUse warns when Chrome cannot answer', warnings.length === 1 && warnings[0][0] === 'Kartaan Auto-sync: could not ask whether the computer is in use.');
}

{
  const { chrome, setTheComputer, alarms } = installFakeChrome();
  setTheComputer('active');
  let started = 0;
  const now = new Date(2024, 0, 2, 10, 0).getTime();
  const result = await startWhenFree(chrome, 'daily', async () => { started++; }, now);
  const waiting = (await chrome.storage.local.get(WAITING))[WAITING];
  check('startWhenFree does not start while the computer is active', started === 0);
  check('startWhenFree says it is waiting', result === false);
  check('startWhenFree remembers why it waits', waiting && waiting.daily === now);
  check('startWhenFree sets the ask-again alarm', alarms().some((alarm) => alarm.name === IDLE_ALARM));
}

{
  const { chrome, setTheComputer, alarms } = installFakeChrome();
  setTheComputer('idle');
  await chrome.storage.local.set({ [WAITING]: { daily: Date.now() } });
  let started = 0;
  const result = await startWhenFree(chrome, 'daily', async () => { started++; });
  const waiting = (await chrome.storage.local.get(WAITING))[WAITING];
  check('startWhenFree starts once when the computer is idle', started === 1);
  check('startWhenFree reports that it started', result === true);
  check('startWhenFree leaves no ask-again alarm', !alarms().some((alarm) => alarm.name === IDLE_ALARM));
  check('startWhenFree clears the waiting entry', waiting === undefined);
}

{
  const { chrome, setTheComputer } = installFakeChrome();
  setTheComputer('active');
  const first = new Date(2024, 0, 2, 10, 0).getTime();
  const laterSameDay = new Date(2024, 0, 2, 11, 0).getTime();
  const nextDay = new Date(2024, 0, 3, 9, 0).getTime();
  let started = 0;
  const start = async () => { started++; };
  await startWhenFree(chrome, 'daily', start, first);
  await startWhenFree(chrome, 'daily', start, laterSameDay);
  let waiting = (await chrome.storage.local.get(WAITING))[WAITING];
  check('startWhenFree keeps the first wait from the same day', waiting && waiting.daily === first);
  await startWhenFree(chrome, 'daily', start, nextDay);
  waiting = (await chrome.storage.local.get(WAITING))[WAITING];
  check('startWhenFree replaces a wait from an earlier day', waiting && waiting.daily === nextDay);
  check('startWhenFree never started while active', started === 0);
}

{
  const { chrome, setTheComputer, alarms } = installFakeChrome();
  setTheComputer('active');
  const now = new Date(2024, 0, 2, 10, 0).getTime();
  await chrome.storage.local.set({ [WAITING]: { daily: now } });
  let started = 0;
  await carryOnWaiting(chrome, { daily: async () => { started++; }, recheck: async () => { started += 10; } }, now);
  const waiting = (await chrome.storage.local.get(WAITING))[WAITING];
  check('carryOnWaiting does not start while the computer is active', started === 0);
  check('carryOnWaiting asks again while the computer is active', alarms().some((alarm) => alarm.name === IDLE_ALARM));
  check('carryOnWaiting leaves the wait unchanged while active', waiting && waiting.daily === now);
}

{
  const { chrome, setTheComputer, alarms } = installFakeChrome();
  setTheComputer('idle');
  const now = new Date(2024, 0, 2, 10, 0).getTime();
  await chrome.storage.local.set({ [WAITING]: { daily: now, recheck: now } });
  await chrome.alarms.create(IDLE_ALARM, { delayInMinutes: 1 });
  const order = [];
  await carryOnWaiting(chrome, {
    daily: async () => { order.push('daily'); },
    recheck: async () => { order.push('recheck'); }
  }, now);
  const waiting = (await chrome.storage.local.get(WAITING))[WAITING];
  check('carryOnWaiting starts both waiting kinds when idle', order.length === 2 && order[0] === 'daily' && order[1] === 'recheck');
  check('carryOnWaiting clears the ask-again alarm', !alarms().some((alarm) => alarm.name === IDLE_ALARM));
  check('carryOnWaiting clears the waiting list', waiting === undefined);
}

{
  const { chrome, setTheComputer } = installFakeChrome();
  setTheComputer('idle');
  const now = new Date(2024, 0, 2, 10, 0).getTime();
  await chrome.storage.local.set({ [WAITING]: { daily: now } });
  const warnings = [];
  const originalWarn = console.warn;
  console.warn = (...args) => warnings.push(args);
  let failed = null;
  try {
    await carryOnWaiting(chrome, { recheck: async () => {} }, now);
  } catch (error) {
    failed = error;
  } finally {
    console.warn = originalWarn;
  }
  const waiting = (await chrome.storage.local.get(WAITING))[WAITING];
  check('carryOnWaiting warns and skips a waiting kind with no start function', failed === null && waiting === undefined && warnings.length === 1);
}

{
  const { chrome, setTheComputer, alarms } = installFakeChrome();
  setTheComputer('active');
  await chrome.alarms.create(IDLE_ALARM, { delayInMinutes: 1 });
  let started = 0;
  await carryOnWaiting(chrome, { daily: async () => { started++; }, recheck: async () => { started++; } });
  check('carryOnWaiting starts nothing when nothing waits', started === 0);
  check('carryOnWaiting clears the alarm when nothing waits', !alarms().some((alarm) => alarm.name === IDLE_ALARM));
}
{
  const { chrome, setTheComputer } = installFakeChrome();
  setTheComputer('idle');
  const yesterday = Date.now() - 24 * 60 * 60 * 1000;
  await chrome.storage.local.set({ [WAITING]: { daily: yesterday } });
  let dailyStarts = 0;
  await carryOnWaiting(chrome, {
    daily: async () => { dailyStarts += 1; },
    recheck: async () => {}
  });
  check('carryOnWaiting starts a wait from a day earlier instead of dropping it', dailyStarts === 1);
}

{
  const { chrome, setTheComputer } = installFakeChrome();
  setTheComputer('idle');
  const now = Date.now();
  await chrome.storage.local.set({ [WAITING]: { daily: now, recheck: now } });
  let dailyStarts = 0;
  let recheckStarts = 0;
  const dailyStart = async () => { dailyStarts += 1; };
  const recheckStart = async () => { recheckStarts += 1; };
  await Promise.all([
    startWhenFree(chrome, 'daily', dailyStart),
    carryOnWaiting(chrome, { daily: dailyStart, recheck: recheckStart })
  ]);
  check('startWhenFree and carryOnWaiting together start each waiting run exactly once', dailyStarts === 1 && recheckStarts === 1);
}

{
  const { chrome, setTheComputer } = installFakeChrome();
  setTheComputer('idle');
  await chrome.storage.local.set({ [WAITING]: { daily: Date.now(), recheck: Date.now() } });
  let recheckStarts = 0;
  const warnings = [];
  const oldWarn = console.warn;
  console.warn = (...args) => { warnings.push(args); };
  let thrown = null;
  try {
    await carryOnWaiting(chrome, {
      daily: async () => { throw new Error('daily failed'); },
      recheck: async () => { recheckStarts += 1; }
    });
  } catch (error) {
    thrown = error;
  } finally {
    console.warn = oldWarn;
  }
  check('carryOnWaiting warns and still starts recheck when daily throws', recheckStarts === 1 && thrown === null && warnings.some((args) => String(args[0]).includes('waiting daily run could not start')));
}

{
  const { chrome, setTheComputer } = installFakeChrome();
  setTheComputer('idle');
  const waiting = JSON.parse('{"__proto__": 1, "toString": "x"}');
  waiting.daily = NaN;
  waiting.x = 123;
  await chrome.storage.local.set({ [WAITING]: waiting });
  let starts = 0;
  let thrown = null;
  try {
    await carryOnWaiting(chrome, {
      daily: async () => { starts += 1; },
      recheck: async () => { starts += 1; }
    });
  } catch (error) {
    thrown = error;
  }
  check('carryOnWaiting ignores junk waiting entries without throwing', thrown === null && starts === 0);
}

{
  const { chrome } = installFakeChrome();
  const waiting = JSON.parse('{"__proto__": 1, "toString": "x"}');
  waiting.daily = NaN;
  waiting.x = 123;
  waiting.recheck = 1000;
  await chrome.storage.local.set({ [WAITING]: waiting });
  const result = await whatIsWaiting(chrome);
  check('whatIsWaiting ignores junk waiting entries and never returns NaN', result && result.since === 1000 && result.kinds.length === 1 && result.kinds[0] === 'recheck');
}

{
  const { chrome, setTheComputer } = installFakeChrome();
  setTheComputer('idle');
  await chrome.alarms.create(IDLE_ALARM, { delayInMinutes: ASK_AGAIN_MINUTES });
  await startWhenFree(chrome, 'daily', async () => {});
  check('startWhenFree clears the ask-again alarm when no waits remain', !(await chrome.alarms.get(IDLE_ALARM)));
}

{
  const { chrome } = installFakeChrome();
  const nothing = await whatIsWaiting(chrome);
  check('whatIsWaiting is null when nothing waits', nothing === null);
  const first = new Date(2024, 0, 2, 9, 0).getTime();
  const second = new Date(2024, 0, 2, 10, 0).getTime();
  await chrome.storage.local.set({ [WAITING]: { recheck: second, daily: first } });
  const waiting = await whatIsWaiting(chrome);
  check('whatIsWaiting reports the earliest moment and the kinds', waiting && waiting.since === first && waiting.kinds.includes('daily') && waiting.kinds.includes('recheck') && waiting.kinds.length === 2);
}

{
  const { chrome, setTheComputer } = installFakeChrome();
  setTheComputer('active');
  let dailyStarts = 0;
  const now = new Date(2024, 0, 2, 10, 0).getTime();
  await startWhenFree(chrome, 'daily', async () => { dailyStarts++; }, now);
  await carryOnWaiting(chrome, { daily: async () => { dailyStarts++; }, recheck: async () => {} }, now);
  check('a waiting run is not started while the computer is still active', dailyStarts === 0);
  setTheComputer('idle');
  await carryOnWaiting(chrome, { daily: async () => { dailyStarts++; }, recheck: async () => {} }, now);
  check('a waiting run starts exactly once when the computer is free', dailyStarts === 1);
}

console.log(`\n${ran - failures} of ${ran} passed`);
process.exit(failures ? 1 : 0);
