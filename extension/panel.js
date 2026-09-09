/* The panel, started.
 *
 * **DELIBERATELY ALMOST EMPTY, for the same reason `worker.js` is.** Everything
 * that could be wrong lives in `screen.js`, which is checked against a stand-in
 * browser and a stand-in Chrome with neither anywhere near it. What is left here
 * is wiring, and wiring is proved by loading it.
 *
 * **THE PAGE ASKS THE WORKER; IT DOES NOT REACH INTO IT.** `worker.js` keeps
 * four globals -- `startAWalk`, `startTheNight`, `howTheNightWent` and
 * `connectTheDrive` -- and says in as many words that they are "a handle, not a
 * way in": a service worker's own global is not reachable from a page at all. So
 * this talks the way the content script already does, through
 * `chrome.runtime.sendMessage`, and `background.js` answers.
 *
 * **AND ALL FOUR GLOBALS STAY.** They are what is left when this page is
 * broken. (Three, this said, until an independent reviewer counted them.)
 */

import { buildThePanel, showHowItStands, saySomething } from './screen.js';

/* **THE ERP'S OWN DARK RULE, not a second one.** `from-the-erp/tokens.css` puts
 * every dark colour under `body.dark`, exactly as the product does, so the class
 * is what switches it. Following the browser's own setting rather than adding a
 * switch: this is a page somebody opens to look at a run, not a place to keep
 * preferences. */
if (globalThis.matchMedia && globalThis.matchMedia('(prefers-color-scheme: dark)').matches) {
  document.body.classList.add('dark');
}

/**
 * Ask the worker something, and never throw at whoever asked.
 *
 * **A MESSAGE TO A WORKER THAT IS NOT LISTENING REJECTS**, with Chrome's own
 * "Could not establish connection". Thrown out of a timer nobody is awaiting,
 * that is an unhandled rejection: the page silently stops refreshing and looks
 * exactly like a run that has stalled. **Caught and SAID rather than swallowed**
 * -- an error nobody can see is the fault this whole product is built against.
 */
const ask = async (asked) => {
  try {
    return await chrome.runtime.sendMessage(asked);
  } catch (wrong) {
    return { wrong: `The extension did not answer: ${(wrong && wrong.message) || wrong}` };
  }
};

/* **HOW OFTEN THIS ASKS, and it is a timer this page owns.** The fault he asked
 * about by name -- *"sometimes it used to get stuck"* -- was measured in
 * `kartaan-click`: a loop polling four times a second, reading `innerText`, which
 * makes the browser lay the whole page out again every call. Two seconds, on a
 * timer, asking one question, and never reading a page at all. */
const EVERY_TWO_SECONDS = 2000;

const parts = buildThePanel(document.body, {
  connectTheDrive: async () => {
    saySomething(parts, 'Chrome will ask which Google account to use...');
    const said = await ask({ do: 'connect-the-drive' });
    saySomething(parts, said && said.connected ? 'Drive connected.' : (said && said.said) || '');
    await refresh();
  },
  saveThePanelName: async (name) => {
    const said = await ask({ do: 'save-the-panel-name', panel: name });
    saySomething(parts, (said && said.wrong) || 'Panel name saved.');
    await refresh();
  },
  runNow: async (reportIds) => {
    const said = await ask({ do: 'run-now', reportIds });
    saySomething(parts, (said && said.wrong) || 'Started.');
    await refresh();
  },
  stop: async () => {
    const said = await ask({ do: 'stop' });
    saySomething(parts, said && said.stopped ? 'Stopped.' : 'There was nothing going to stop.');
    await refresh();
  },
  setTheHour: async (at) => {
    /* **THE BOX'S OWN TEXT GOES ACROSS, UNTOUCHED.** Turned into two numbers
     * here, an unanswered box becomes midnight on the way -- and the guard on
     * the other side would then be asked about a value nobody chose. */
    const said = await ask({ do: 'set-the-hour', at });
    saySomething(parts, (said && said.wrong) || 'Saved.');
    await refresh();
  },
});

async function refresh() {
  /* **NOTHING IS ASKED WHILE NOBODY IS LOOKING.** Every question wakes a service
   * worker Chrome shuts down after thirty seconds of quiet, and a panel left open
   * in a background tab would wake it for ever, for nobody. */
  if (document.hidden) return;
  const said = await ask({ do: 'how-it-stands' });
  if (said && said.stands) showHowItStands(parts, said.stands);
  else if (said && said.wrong) saySomething(parts, said.wrong);
}

/* **THE DRIVE IS ASKED ABOUT ONCE, WHEN THIS OPENS, AND QUIETLY.** Asked on
 * every poll it would be a Google call every two seconds; asked interactively it
 * would put an account chooser in front of somebody who pressed nothing. */
ask({ do: 'check-the-drive' }).then(refresh);
setInterval(refresh, EVERY_TWO_SECONDS);
document.addEventListener('visibilitychange', refresh);
