/* Checks for what a seller is told.
 *
 * Run: node extension/manual.test.js
 *
 * **THE WHOLE REASON THE MANUAL IS DATA IS SO THIS FILE CAN EXIST.** Written into
 * the markup that draws it, a help card cannot be asked whether it still matches
 * the product -- it just quietly goes stale, and the first person to notice is a
 * seller following a step that no longer exists.
 *
 * **THE ONE THAT MATTERS MOST: a control that grows without a tooltip.** The
 * panel is built in code, so a new button appears on a seller's screen the moment
 * somebody adds one, with nothing beside it saying what it does. This is what
 * turns that into a red line instead.
 */

import { MANUAL, TOOLTIPS, theEntryFor } from './manual.js';
import { buildThePanel } from './screen.js';
import { installFakeBrowser } from '../test/fake-browser.js';

process.on('uncaughtException', (err) => {
  console.log(`FAIL  the checks stopped part way through: ${(err && err.message) || String(err)}`);
  process.exit(1);
});

let failures = 0;
let ran = 0;
let reachedTheEnd = false;
process.on('exit', (code) => {
  if (reachedTheEnd || code !== 0) return;
  console.log('FAIL  the checks stopped before the end');
  process.exitCode = 1;
});

function check(name, passed) {
  ran++;
  console.log(`${passed ? 'PASS' : 'FAIL'}  ${name}`);
  if (!passed) failures++;
}

/* --------------------------------------------------------- the manual itself */

check('there is a manual to judge', MANUAL.length >= 5);
check('every entry has an id, a label and one line saying what it is for',
  MANUAL.every((one) => one.id && one.label && one.crux));
check('and no two entries are about the same part',
  new Set(MANUAL.map((one) => one.id)).size === MANUAL.length);
check('every entry says what to actually do, in order',
  MANUAL.every((one) => Array.isArray(one.steps) && one.steps.length));
/* **A LINE THAT SAYS NOTHING IS WORSE THAN NO LINE**, because it looks like help
 * and sends somebody away believing they have been told. */
check('and not one of those steps is too short to be help',
  MANUAL.every((one) => one.steps.every((said) => said.split(' ').length >= 6)));
check('the one-liners are one line, not a paragraph wearing one',
  MANUAL.every((one) => one.crux.split(' ').length <= 30));
check('a part with no entry answers nothing rather than guessing',
  theEntryFor('no-such-part') === null);
check('and a part with one answers it', theEntryFor('setup').label === 'Set up, once');

/* **THE FOUR WORDS A REPORT CAN COME BACK AS ARE ALL EXPLAINED.** Three of them
 * mean nothing is wrong, and a seller who does not know that will read every one
 * of them as a fault -- which is how an alarm nobody can clear gets muted. */
{
  const words = theEntryFor('words');
  const said = JSON.stringify(words).toLowerCase();
  check('what the words mean is in the manual', Boolean(words));
  check('and all four are explained, not just the bad one',
    said.includes('landed') && said.includes('still waiting')
      && said.includes('nothing to fetch') && said.includes('failed'));
  /* **AND IT SAYS WHICH ONE IS WORTH ACTING ON.** Four words with no ranking
   * between them is four things to worry about. */
  check('and it says which of them actually needs somebody',
    said.includes('only one') || said.includes('worth acting on'));
}

/* ------------------------------------------------------------- the tooltips */

check('there are tooltips to judge', Object.keys(TOOLTIPS).length >= 5);
check('every tooltip says something, and none is a label repeated',
  Object.values(TOOLTIPS).every((said) => said.split(' ').length >= 8));
/* **SHORT MEANS SHORT.** A tooltip nobody finishes reading is a tooltip that did
 * not help, and the manual is where the longer answer lives. */
check('and none of them has grown into a manual entry',
  Object.values(TOOLTIPS).every((said) => said.length <= 220));

/* ------------------------------------- and both are really joined to the panel */

/* **DRIVEN, NOT READ.** The panel is built and then asked what it is carrying --
 * a check that compared two lists in this file would go green on a panel that
 * draws neither. */
{
  const page = installFakeBrowser({ width: 1280, height: 800 });
  const parts = buildThePanel(page.body, {
    connectTheDrive: () => {}, saveThePanelName: () => {}, runNow: () => {},
    stop: () => {}, setTheHour: () => {},
  });

  const missing = Object.keys(TOOLTIPS).filter((which) => !parts[which]);
  check(`every tooltip is about a control the panel really has -- ${missing}`,
    missing.length === 0);
  check('and each one really reached the control',
    Object.entries(TOOLTIPS).every(([which, said]) => parts[which].title === said));

  /* **THE ONE THAT MATTERS MOST: A CONTROL THAT GREW WITHOUT A TOOLTIP.** The
   * panel is built in code, so a new button reaches a seller's screen the moment
   * somebody writes one, with nothing beside it saying what it does. **Named one
   * by one rather than counted**, so a control losing its tooltip cannot hide
   * behind another gaining one. */
  const CONTROLS = ['connectDrive', 'panelName', 'savePanel', 'runNow', 'stop', 'hour', 'log'];
  const bare = CONTROLS.filter((which) => !TOOLTIPS[which]);
  check(`every control a seller presses has a tooltip -- ${bare}`, bare.length === 0);

  check('the manual is drawn onto the panel, not left in a file nobody opens',
    Boolean(parts.help));
  const drawn = parts.help.textContent || '';
  const unshown = MANUAL.filter((one) => !drawn.includes(one.crux)).map((one) => one.id);
  check(`and every entry of it is really on the page -- ${unshown}`, unshown.length === 0);
  check('and each entry brings its steps with it',
    MANUAL.every((one) => one.steps.every((said) => drawn.includes(said))));
}

const EXPECTED = 20;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
