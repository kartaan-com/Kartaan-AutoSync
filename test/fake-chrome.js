/* A small stand-in for the parts of Chrome an extension is given, so the
 * extension's own decisions can be checked without a browser, without the
 * extension being installed, and without a seller's account.
 *
 * ONE of these, beside `fake-browser.js`, and for the same reason: a second
 * copy is how the two drift apart, and this project's register records four
 * separate occasions where a defect hid behind a stand-in that behaved better
 * than the real thing.
 *
 * IT IS DELIBERATELY AWKWARD, in the places Chrome itself is awkward -- because
 * every one of those places is a real failure that has already happened here:
 *
 *   - **the worker can be shut down at any moment, and this can be told to do
 *     it.** Chrome kills an idle service worker after thirty seconds and says
 *     plainly that "any global variables you set will be lost". A stand-in that
 *     never shut down would let a run keep its state in a variable and pass
 *     every check, then lose ten real files in front of a seller -- which is
 *     what happened on 25 August;
 *   - **an alarm does not survive that shutdown unless it was really stored**,
 *     and `clearAll` is offered so a check can do to it what a browser restart
 *     or an extension update does;
 *   - **what is stored is copied on the way in and on the way out**, the way it
 *     is when it really crosses into a browser's own storage. Handing back the
 *     live object would let code edit what it never saved and still read it
 *     back;
 *   - **a download hands over its address and NEVER its contents**, because
 *     `chrome.downloads` genuinely cannot read a file. Anything that wants the
 *     bytes has to fetch that address again, and a `blob:` one cannot be
 *     fetched twice by anybody.
 *
 * WHERE IT IS HARSHER THAN CHROME, written down rather than left to be found:
 *
 *   - **it knows only the calls the extension actually makes.** Anything else
 *     throws rather than quietly answering nothing, for the same reason
 *     `fake-browser.js` throws at a question it does not understand: a silent
 *     "no" looks exactly like the real thing being absent;
 *   - **every call is answered immediately.** Chrome's are promises that take a
 *     moment, so an ordering fault that depends on real timing is invisible
 *     here. They are still promises, so `await` behaves, but nothing here can
 *     prove what happens when two of them land out of order.
 *
 * It lives outside src/ and outside extension/ on purpose: it is not part of
 * anything that ships.
 */

/** A copy, the way something that has really crossed into storage is a copy. */
function aCopyOf(value) {
  return value === undefined ? undefined : JSON.parse(JSON.stringify(value));
}

class FakeStore {
  constructor(owner) {
    this._owner = owner;
    this._held = new Map();
  }

  async get(asked) {
    this._owner._noteACall();
    const out = {};
    if (asked === null || asked === undefined) {
      for (const [name, value] of this._held) out[name] = aCopyOf(value);
      return out;
    }
    const names = typeof asked === 'string' ? [asked] : asked;
    if (!Array.isArray(names)) {
      throw new Error('The stand-in storage takes a name or a list of names, and nothing else.');
    }
    for (const name of names) {
      if (this._held.has(name)) out[name] = aCopyOf(this._held.get(name));
    }
    return out;
  }

  async set(given) {
    this._owner._noteACall();
    for (const [name, value] of Object.entries(given)) this._held.set(name, aCopyOf(value));
  }

  async remove(asked) {
    this._owner._noteACall();
    const names = typeof asked === 'string' ? [asked] : asked;
    for (const name of names) this._held.delete(name);
  }
}

/** Somewhere listeners can be added and a check can set them off. */
class Listeners {
  constructor(owner) {
    this._owner = owner;
    this._heard = [];
  }

  addListener(fn) {
    if (typeof fn !== 'function') {
      throw new Error('A listener has to be something that can be called.');
    }
    this._heard.push(fn);
  }

  /** How many are listening. A check asserts this: a listener registered inside
   *  a function is one that does not exist until something calls that function,
   *  and after a restart nothing has. */
  get many() {
    return this._heard.length;
  }

  /** Set them off, in the order they were added, and wait for each. Anything
   *  they call counts as the worker being busy. */
  async happened(...given) {
    this._owner._noteACall();
    for (const fn of [...this._heard]) await fn(...given);
  }
}

/**
 * Put a stand-in Chrome in place, and hand back the handle a check drives it by.
 */
export function installFakeChrome({ now = () => 0 } = {}) {
  const alarms = new Map();
  const tabs = new Map();
  const windows = new Map();
  let nextWindowId = 100;
  const downloads = [];
  const reloaded = [];
  const sentToPages = [];
  const cancelled = [];
  const erased = [];
  const putIntoPages = [];
  let nextTabId = 1;
  let calls = 0;

  const owner = { _noteACall: () => { calls += 1; } };

  const onStartup = new Listeners(owner);
  const onInstalled = new Listeners(owner);
  const onAlarm = new Listeners(owner);
  const onMessage = new Listeners(owner);
  const onDownloadCreated = new Listeners(owner);
  const onTabRemoved = new Listeners(owner);

  const local = new FakeStore(owner);

  const chrome = {
    runtime: {
      onStartup,
      onInstalled,
      onMessage,
      /* Every extension has one, and it is what tells a message from our own
       * half apart from one another extension sent. */
      id: 'stand-in-extension-id',
      /* What the extension's own files are addressed by. A real one is a
       * `chrome-extension://` address; the shape is what matters here. */
      getURL: (name) => `chrome-extension://stand-in/${String(name).replace(/^\/+/, '')}`,
      /* Chrome sets this when a call failed and the caller did not catch it.
       * Left undefined, the way a real one is when nothing went wrong. */
      lastError: undefined,
    },

    alarms: {
      onAlarm,
      async create(name, options) {
        owner._noteACall();
        if (!name) throw new Error('An alarm has to have a name.');
        const every = Number(options && options.periodInMinutes);
        /* **CHROME REFUSES ANYTHING UNDER HALF A MINUTE**, in its own words:
         * setting it "to less than 0.5 will not be honored and will cause a
         * warning". A stand-in that accepted it would let an alarm be asked for
         * that never arrives. */
        if (every && every < 0.5) {
          throw new Error(`Chrome will not honour an alarm every ${every} minutes.`);
        }
        alarms.set(name, {
          name,
          periodInMinutes: every || undefined,
          scheduledTime: now() + (Number(options && options.delayInMinutes) || 0) * 60000,
          /* Kept as given, so a check can see whether it was asked for at all.
           * The documentation says to set it explicitly for compatibility. */
          persistAcrossSessions: options && options.persistAcrossSessions,
        });
      },
      async get(name) {
        owner._noteACall();
        return alarms.has(name) ? { ...alarms.get(name) } : undefined;
      },
      async getAll() {
        owner._noteACall();
        return [...alarms.values()].map((one) => ({ ...one }));
      },
      async clear(name) {
        owner._noteACall();
        return alarms.delete(name);
      },
      async clearAll() {
        owner._noteACall();
        alarms.clear();
      },
    },

    storage: { local },

    /* **WINDOWS, BECAUSE WHICH WINDOW A TAB IS IN DECIDES WHETHER CHROME
     * THROTTLES IT** -- and throttling is the difference between this product
     * working at two in the morning and not. Chrome throttles a tab's timers
     * when a DIFFERENT TAB IS SELECTED IN THAT TAB'S WINDOW, or when that WINDOW
     * IS MINIMISED. Screen focus is not the trigger. So a stand-in that did not
     * model windows at all could not tell the working arrangement from the
     * broken one. */
    windows: {
      async create({ url, focused, state, width, height }) {
        owner._noteACall();
        const id = nextWindowId++;
        const tabId = nextTabId++;
        tabs.set(tabId, { id: tabId, url, status: 'loading', windowId: id, active: true });
        windows.set(id, { id, focused: Boolean(focused), state: state || 'normal', width, height });
        return { ...windows.get(id), tabs: [{ ...tabs.get(tabId) }] };
      },
      async get(id) {
        owner._noteACall();
        /* **THROWS WHEN IT IS GONE, the way Chrome's does.** A stand-in that
         * answered nothing would let code treat a closed window as an open one
         * and open every report in a window that no longer exists. */
        if (!windows.has(id)) throw new Error(`There is no window ${id}.`);
        return { ...windows.get(id) };
      },
      async update(id, how) {
        owner._noteACall();
        if (!windows.has(id)) throw new Error(`There is no window ${id}.`);
        windows.set(id, { ...windows.get(id), ...how });
        return { ...windows.get(id) };
      },
      async remove(id) {
        owner._noteACall();
        windows.delete(id);
        for (const [tabId, tab] of [...tabs]) if (tab.windowId === id) tabs.delete(tabId);
      },
    },

    tabs: {
      onRemoved: onTabRemoved,
      async create({ url, windowId, active }) {
        owner._noteACall();
        const id = nextTabId++;
        if (windowId !== undefined && !windows.has(windowId)) {
          throw new Error(`There is no window ${windowId}.`);
        }
        /* **A NEW SELECTED TAB DESELECTS THE OTHERS IN ITS WINDOW**, which is
         * the whole of how a tab becomes throttled. */
        if (active && windowId !== undefined) {
          for (const [other, tab] of [...tabs]) {
            if (tab.windowId === windowId) tabs.set(other, { ...tab, active: false });
          }
        }
        tabs.set(id, { id, url, status: 'loading', windowId, active: Boolean(active) });
        return { ...tabs.get(id) };
      },
      async update(id, { url, active }) {
        owner._noteACall();
        if (!tabs.has(id)) throw new Error(`There is no tab ${id}.`);
        if (active !== undefined) {
          const it = tabs.get(id);
          for (const [other, tab] of [...tabs]) {
            if (tab.windowId === it.windowId) tabs.set(other, { ...tab, active: false });
          }
          tabs.set(id, { ...tabs.get(id), active: Boolean(active) });
          if (url === undefined) return { ...tabs.get(id) };
        }
        /* **AND TELLING A TAB WHERE TO GO IS NOT ALWAYS A PAGE LOAD, WHICH IS
         * THE HARSHEST THING IN THIS FILE.** If the new address agrees with the
         * old one up to the `#`, a browser scrolls: the address bar moves, the
         * page stays, its scripts stay, and nothing is put into it again. Every
         * Flipkart address in the recipe file is `index.html#something`, so this
         * is not an edge -- it is thirteen of the seventeen reports.
         *
         * **A STAND-IN THAT RELOADED HERE WOULD HAVE PASSED THE WHOLE OF D200
         * GREEN** while every Flipkart walk stalled for ever in front of a
         * seller, at night, saying nothing. */
        const upToTheHash = (one) => String(one || '').split('#')[0];
        const held = tabs.get(id);
        if (upToTheHash(held.url) === upToTheHash(url)) {
          tabs.set(id, { ...held, url });
          return { ...tabs.get(id) };
        }
        /* **A REAL TAB DOES NOT FINISH THE MOMENT IT IS TOLD WHERE TO GO.** It
         * says it is loading, and something has to wait. A stand-in that jumped
         * straight to finished would let code that never waits pass every check
         * and then read every button as missing on a page that was still blank. */
        tabs.set(id, { ...held, url, status: 'loading' });
        return { ...tabs.get(id) };
      },
      /* **RELOADING IS THE ONE THING THAT ALWAYS LOADS.** It is how anything
       * gets a real page out of an address that differs only after the `#`. */
      async reload(id) {
        owner._noteACall();
        if (!tabs.has(id)) throw new Error(`There is no tab ${id}.`);
        reloaded.push(id);
        tabs.set(id, { ...tabs.get(id), status: 'loading' });
      },
      /* **AND A MESSAGE SENT TO A PAGE IS RECORDED, NOT DELIVERED.** The page
       * half is not here; what a check needs to see is that the message was sent
       * at all, and what was already written down by the time it was. */
      sendMessage(id, said) {
        owner._noteACall();
        sentToPages.push({ tabId: id, said: aCopyOf(said) });
        return Promise.resolve(undefined);
      },
      async remove(id) {
        owner._noteACall();
        tabs.delete(id);
        await onTabRemoved.happened(id, { windowId: 1, isWindowClosing: false });
      },
      async get(id) {
        owner._noteACall();
        if (!tabs.has(id)) throw new Error(`There is no tab ${id}.`);
        return { ...tabs.get(id) };
      },
    },

    scripting: {
      /* **AS HARSH AS CHROME IS HERE, and this is the one that matters.** A real
       * `executeScript` does not send the function -- it sends its SOURCE, and
       * runs that in the page with nothing of the extension around it. So a
       * function that reaches for anything outside itself works perfectly in a
       * check and throws in front of a seller. Rebuilding it from its own text
       * is exactly what a browser does, and it is why `catchTheNextFile` writes
       * its constants out a second time instead of reading them from the top of
       * its own file. */
      async executeScript({ target, world, func, args = [] }) {
        owner._noteACall();
        const id = target && target.tabId;
        if (!tabs.has(id)) throw new Error(`There is no tab ${id}.`);
        if (typeof func !== 'function') throw new Error('There is nothing to put into the page.');
        // eslint-disable-next-line no-new-func
        const asTheBrowserWould = new Function(`return (${func.toString()});`)();
        putIntoPages.push({ tabId: id, world, args: [...args] });
        return [{ frameId: 0, result: asTheBrowserWould(...args) }];
      },
    },

    downloads: {
      onCreated: onDownloadCreated,
      async search() {
        owner._noteACall();
        return downloads.map((one) => ({ ...one }));
      },
      /* **CALLBACK-SHAPED, LIKE CHROME'S OWN, and that is the whole point of
       * having it here.** A promise-shaped stand-in would let a `cancel` that
       * was awaited pass a check that exists to prove nothing is awaited. What
       * is recorded is WHEN it was called, in order, so a check can look before
       * anything has been waited for and see it already done. */
      cancel(id, then) {
        owner._noteACall();
        cancelled.push(id);
        if (then) then();
      },
      erase({ id }, then) {
        owner._noteACall();
        erased.push(id);
        if (then) then([id]);
      },
    },
  };

  globalThis.chrome = chrome;

  return {
    chrome,

    /** What is really stored right now, for a check to read. */
    stored() {
      const out = {};
      for (const [name, value] of local._held) out[name] = aCopyOf(value);
      return out;
    },

    /** Every alarm there is. */
    alarms() {
      return [...alarms.values()].map((one) => ({ ...one }));
    },

    /** Everything that has been put into a page, in order. */
    putIntoPages() {
      return putIntoPages.map((one) => ({ ...one, args: [...one.args] }));
    },

    /** Ask the background something, the way the page half does, and read what
     *  it answers. **Nothing is answered unless a listener says it will answer
     *  later** -- which is exactly the mistake that throws a reply away. */
    async aPageAsked(asked, from = { tab: { id: 1 }, id: 'stand-in-extension-id' }) {
      let reply;
      let willAnswerLater = false;
      for (const heard of onMessage._heard) {
        // eslint-disable-next-line no-loop-func
        const said = heard(asked, from, (answer) => { reply = answer; });
        if (said === true) willAnswerLater = true;
      }
      if (!willAnswerLater) return undefined;
      /* Let whatever the listener started finish, the way a real message does. */
      for (let round = 0; round < 50 && reply === undefined; round += 1) {
        // eslint-disable-next-line no-await-in-loop
        await Promise.resolve();
      }
      return reply;
    },

    /** Which downloads have been cancelled, in the order they were cancelled.
     *  **READ WITHOUT AWAITING ANYTHING** by the check that proves the cancel
     *  happens inside the event rather than a moment later. */
    cancelledDownloads() {
      return [...cancelled];
    },

    /** Which downloads have been erased from the seller's own downloads list. */
    erasedDownloads() {
      return [...erased];
    },

    /** Which tabs have been really reloaded, in order. **What separates a page
     *  that was drawn again from an address bar that merely moved.** */
    reloadedTabs() {
      return [...reloaded];
    },

    /** Everything the background has said to a page, in order. */
    sentToPages() {
      return sentToPages.map((one) => ({ ...one }));
    },

    /** Every window there is, and what state it is in. **A minimised window is
     *  a throttled window**, so this is what a check about running unattended
     *  reads. */
    windows() {
      return [...windows.values()].map((one) => ({ ...one }));
    },

    /** Every tab there is. */
    tabs() {
      return [...tabs.values()].map((one) => ({ ...one }));
    },

    /** How many times Chrome has been called. **A run that never calls Chrome
     *  is a run Chrome shuts down**, so this is what a check about staying
     *  alive reads. */
    calls() {
      return calls;
    },

    /** Say a download started. **The address is all there is** -- Chrome cannot
     *  hand over the contents of a file, so anything wanting the bytes has to
     *  fetch this address again. */
    async aDownloadStarted({ id = downloads.length + 1, url, finalUrl, filename = '' } = {}) {
      const item = { id, url, finalUrl: finalUrl || url, filename, state: 'in_progress' };
      downloads.push(item);
      await onDownloadCreated.happened({ ...item });
      return item;
    },

    /** Do to the worker what Chrome does after thirty idle seconds: take
     *  everything that was only ever in a variable. What is really in storage
     *  survives, and nothing else does. */
    shutTheWorkerDown() {
      onStartup._heard = [];
      onInstalled._heard = [];
      onAlarm._heard = [];
      onMessage._heard = [];
      onDownloadCreated._heard = [];
      onTabRemoved._heard = [];
    },

    /** Do to the alarms what a browser restart or an extension update does. */
    forgetTheAlarms() {
      alarms.clear();
    },

    /** Say a tab has finished drawing, the way a real one eventually does. */
    theTabFinishedDrawing(id) {
      if (!tabs.has(id)) throw new Error(`There is no tab ${id}.`);
      tabs.set(id, { ...tabs.get(id), status: 'complete' });
    },
  };
}
