export const IDLE_SECONDS = 180;
/** The alarm that asks again while the computer is in use. */
export const IDLE_ALARM = 'kartaan-autosync-idle-wait';
/** chrome.storage.local key: { [kind]: millisecondsWhenItBecameDue } */
export const WAITING = 'kartaan-autosync-waiting-for-idle';
/** How long to wait before asking again. */
export const ASK_AGAIN_MINUTES = 1;

/** AJ9 piece 2: chrome.storage.local key: { kind, waitedMs, at } -- how the run just started got past the idle wait.
 *  `startTheNight` reads it into the night so the run log can say so; a start that did not come through here (Run now)
 *  leaves none. */
export const STARTED_AFTER_IDLE = 'kartaan-autosync-started-after-idle';

async function noteTheStart(chrome, kind, since, now) {
  const waitedMs = Number.isFinite(since) ? Math.max(0, now - since) : 0;
  await chrome.storage.local.set({ [STARTED_AFTER_IDLE]: { kind, waitedMs, at: now } });
}

let turn = Promise.resolve();

function oneAtATime(job) {
  const result = turn.then(job);
  turn = result.then(
    () => undefined,
    () => undefined
  );
  return result;
}

/** True only while the computer is active; idle and locked both mean left alone. */
export async function computerInUse(chrome) {
  try {
    return (await chrome.idle.queryState(IDLE_SECONDS)) === 'active';
  } catch (error) {
    console.warn('Kartaan Auto-sync: could not ask whether the computer is in use.', (error && error.message) || String(error));
    return false;
  }
}

/** Start a run now if the computer is free, otherwise remember it for later. */
export async function startWhenFree(chrome, kind, start, now = Date.now()) {
  return oneAtATime(async () => {
    if (await computerInUse(chrome)) {
      const stored = await chrome.storage.local.get(WAITING);
      const waiting = stored[WAITING] || {};
      const earlier = waiting[kind];
      if (typeof earlier === 'number' && new Date(earlier).toDateString() === new Date(now).toDateString()) {
        waiting[kind] = Math.min(earlier, now);
      } else {
        waiting[kind] = now;
      }
      await chrome.storage.local.set({ [WAITING]: waiting });
      await chrome.alarms.create(IDLE_ALARM, { delayInMinutes: ASK_AGAIN_MINUTES });
      return false;
    }

    const stored = await chrome.storage.local.get(WAITING);
    const waiting = stored[WAITING] || {};
    const since = waiting[kind];
    delete waiting[kind];
    if (Object.keys(waiting).length) {
      await chrome.storage.local.set({ [WAITING]: waiting });
    } else {
      await chrome.storage.local.remove(WAITING);
      await chrome.alarms.clear(IDLE_ALARM);
    }
    await noteTheStart(chrome, kind, since, now);
    await start();
    return true;
  });
}

/** Called when the ask-again alarm fires; starts any runs that are still waiting. */
export async function carryOnWaiting(chrome, starts, now = Date.now()) {
  return oneAtATime(async () => {
    const stored = await chrome.storage.local.get(WAITING);
    const waiting = stored[WAITING] || {};
    for (const kind of Object.keys(waiting)) {
      if ((kind !== 'daily' && kind !== 'recheck') || !Number.isFinite(waiting[kind])) {
        delete waiting[kind];
      }
    }

    if (Object.keys(waiting).length === 0) {
      await chrome.storage.local.remove(WAITING);
      await chrome.alarms.clear(IDLE_ALARM);
      return;
    }

    await chrome.storage.local.set({ [WAITING]: waiting });

    if (await computerInUse(chrome)) {
      await chrome.alarms.create(IDLE_ALARM, { delayInMinutes: ASK_AGAIN_MINUTES });
      return;
    }

    await chrome.alarms.clear(IDLE_ALARM);
    await chrome.storage.local.remove(WAITING);

    for (const kind of ['daily', 'recheck']) {
      if (!(kind in waiting)) continue;
      const start = starts[kind];
      if (typeof start !== 'function') {
        console.warn(`Kartaan Auto-sync: no start function for waiting ${kind}.`);
        continue;
      }
      try {
        await noteTheStart(chrome, kind, waiting[kind], now);
        await start();
      } catch (error) {
        console.warn(`Kartaan Auto-sync: the waiting ${kind} run could not start.`, (error && error.message) || String(error));
      }
    }
  });
}

/** What is waiting, if anything. */
export async function whatIsWaiting(chrome) {
  const stored = await chrome.storage.local.get(WAITING);
  const waiting = stored[WAITING] || {};
  for (const kind of Object.keys(waiting)) {
    if ((kind !== 'daily' && kind !== 'recheck') || !Number.isFinite(waiting[kind])) {
      delete waiting[kind];
    }
  }
  const kinds = Object.keys(waiting);
  if (kinds.length === 0) return null;
  const since = Math.min(...kinds.map((kind) => waiting[kind]));
  return { since, kinds };
}

/** A wait whose ask-again alarm was lost (Chrome can clear alarms) asks again, or the run would wait for ever. */
export async function askAgainIfWaiting(chrome) {
  if (!(await whatIsWaiting(chrome)) || await chrome.alarms.get(IDLE_ALARM)) return;
  await chrome.alarms.create(IDLE_ALARM, { delayInMinutes: ASK_AGAIN_MINUTES });
}
