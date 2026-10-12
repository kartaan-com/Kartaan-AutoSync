/* Checks for talking to Kartaan's server: may this sync fetch, and this sync has finished (plan jobs 30 and 48).
 *
 * Run: node extension/kartaan.test.js
 *
 * **THE ONE THAT MATTERS MOST IS THE PASS.** It is a credential for one seller's pipeline, pasted by hand. Whatever
 * else goes wrong, it must never come back out: not in a stored night, not in the run log, not in a sentence on the
 * panel, not in what the panel is told about Kartaan. Those are checked by searching every one of them for it.
 *
 * **AND THE SECOND IS THAT NO ANSWER IS A SILENT ONE.** Not reachable, too slow, not JSON, JSON of the wrong shape,
 * a refusal: each is plain words, and each one stops a sync from starting (only a clear yes, or no pass saved,
 * goes ahead). **AND A FAILURE TO TELL KARTAAN A SYNC FINISHED MUST NEVER CHANGE HOW THAT SYNC WENT.**
 *
 * **NOTHING HERE CONNECTS TO ANYTHING (Golden Rule 1).** Every fetch is a stand-in handed in.
 */

import { readFileSync } from 'node:fs';
import { installFakeChrome } from '../test/fake-chrome.js';
import { installFakeBrowser } from '../test/fake-browser.js';
import {
  FINISHED_ADDRESS,
  KARTAAN_LAST_SAID,
  MAY_FETCH_ADDRESS,
  PASS_AT_MOST,
  THE_RUN_PASS,
  askMayFetch,
  isARunPassSaved,
  saveTheRunPass,
  tellFinished,
  theFailedReportsToSend,
  whatKartaanLastSaid,
  whyThatIsNotARunPass,
} from './kartaan.js';
import {
  THE_SYNC_FAILED, THE_SCHEDULED_QUEUE, THE_NIGHT, carryTheNightOn, endTheNight, startTheNight, theNight, theRunLog,
} from './nightly.js';
import {
  THE_PANEL_ASKS, THE_QUEUE, answerThePanelsQuestion, buildThePanel, howItStands, showHowItStands,
  startTheNextPlatform, startTheScheduledSync, tellForASyncThatCannotContinue, theSyncSummary,
} from './screen.js';

process.on('uncaughtException', (err) => {
  console.log(`FAIL  the checks stopped part way through: ${(err && err.message) || String(err)}`);
  process.exit(1);
});
process.on('unhandledRejection', (err) => {
  console.log(`FAIL  something was waited on and never came back: ${(err && err.message) || String(err)}`);
  process.exit(1);
});

let failures = 0;
let ran = 0;
let reachedTheEnd = false;
process.on('exit', (code) => {
  if (reachedTheEnd || code !== 0) return;
  console.log('FAIL  the checks stopped before the end -- something they waited on never came back');
  process.exitCode = 1;
});

function check(name, passed) {
  ran++;
  console.log(`${passed ? 'PASS' : 'FAIL'}  ${name}`);
  if (!passed) failures++;
}

const HERE = new URL('./', import.meta.url);
const BOOK = JSON.parse(readFileSync(new URL('recipes.json', HERE), 'utf8'));
const MANIFEST = JSON.parse(readFileSync(new URL('manifest.json', HERE), 'utf8'));
const WORKER = readFileSync(new URL('worker.js', HERE), 'utf8');

/* A pass as long and as plain as the real one: letters, digits and the dots and dashes a signed pass has. */
const PASS = `${'abcDEF0123456789-_'.repeat(8)}.${'xyz789'.repeat(10)}`;
const NOW = Date.UTC(2026, 9, 12, 3, 0);

/** A stand-in for `fetch` that records every call and answers what it is told. */
function aServerThat(answer) {
  const it = { calls: [] };
  it.fetch = async (address, init) => {
    it.calls.push({ address, init });
    const got = typeof answer === 'function' ? await answer(address, init) : answer;
    return {
      status: got.status === undefined ? 200 : got.status,
      json: async () => {
        if (got.notJson) throw new SyntaxError('Unexpected token < in JSON');
        return got.body;
      },
    };
  };
  return it;
}

const formOf = (call) => Object.fromEntries(new URLSearchParams(call.init.body));
const withAPass = async (chrome) => saveTheRunPass(chrome, PASS);

/* ---------------------------------------------------------------- the pass */

{
  const { chrome } = installFakeChrome();
  check('nothing is saved to begin with', (await isARunPassSaved(chrome)) === false);
  const kept = await saveTheRunPass(chrome, `  \n${PASS}\r\n  `);
  const held = (await chrome.storage.local.get(THE_RUN_PASS))[THE_RUN_PASS];
  check('a pasted pass with a stray space and line break is trimmed, and kept', kept.saved === true && held === PASS);
  check('and what comes back says saved and never the pass', !JSON.stringify(kept).includes(PASS));
  check('a pass is "saved" as a yes or a no for the panel', (await isARunPassSaved(chrome)) === true);

  const empty = await saveTheRunPass(chrome, '   \n ');
  check('an empty box is refused in words', Boolean(empty.wrong) && empty.wrong.includes('empty') && !empty.saved);
  const tooLong = await saveTheRunPass(chrome, 'a'.repeat(PASS_AT_MOST + 1));
  check('a pass over 1024 characters is refused in words, naming the limit',
    Boolean(tooLong.wrong) && tooLong.wrong.includes('1024') && !tooLong.saved);
  const atTheLimit = whyThatIsNotARunPass('a'.repeat(PASS_AT_MOST));
  check('exactly 1024 characters is not refused', atTheLimit === '');
  const inside = await saveTheRunPass(chrome, `${PASS.slice(0, 40)}\n${PASS.slice(40)}`);
  check('a pass with a line break inside it is refused rather than guessed at', Boolean(inside.wrong) && !inside.saved);
  check('and a refused paste leaves the saved pass exactly as it was',
    (await chrome.storage.local.get(THE_RUN_PASS))[THE_RUN_PASS] === PASS);
  check('the panel may ask to save a pass', THE_PANEL_ASKS.includes('save-the-run-pass'));
  const viaThePanel = await answerThePanelsQuestion(chrome, { book: BOOK }, { do: 'save-the-run-pass', pass: PASS });
  check('the panel\'s ask saves it and answers without the pass',
    viaThePanel.saved === true && !JSON.stringify(viaThePanel).includes(PASS));
}

/* ------------------------------------------------------------ may it fetch */

{
  const { chrome } = installFakeChrome();
  await withAPass(chrome);
  const server = aServerThat({ body: { fetch: true, said: 'Your Kartaan plan includes the fetching, so it runs.' } });
  const got = await askMayFetch(chrome, server.fetch, { at: NOW });
  check('go: a 200 with fetch true is a go, in the server\'s words',
    got.go === true && got.asked === true && got.kind === 'go' && got.said.includes('includes the fetching'));
  check('it posted to /may-fetch, once, as a form carrying only the pass',
    server.calls.length === 1 && server.calls[0].address === MAY_FETCH_ADDRESS
    && server.calls[0].init.method === 'POST'
    && server.calls[0].init.headers['Content-Type'] === 'application/x-www-form-urlencoded'
    && JSON.stringify(formOf(server.calls[0])) === JSON.stringify({ pass: PASS }));
  check('and it is a form string, not JSON', typeof server.calls[0].init.body === 'string'
    && !server.calls[0].init.body.startsWith('{'));
  check('and without the browser\'s cookies', server.calls[0].init.credentials === 'omit');
}

{
  const { chrome } = installFakeChrome();
  await withAPass(chrome);
  const no = await askMayFetch(chrome, aServerThat({
    status: 403, body: { fetch: false, said: 'Your trial has ended and was not paid for.' },
  }).fetch);
  check('no: fetch false is a no, in the server\'s own sentence',
    no.go === false && no.kind === 'no' && no.said === 'Your trial has ended and was not paid for.');
  const tooMany = await askMayFetch(chrome, aServerThat({
    status: 429, body: { fetch: false, said: 'Asked too many times today.' },
  }).fetch);
  check('a 429 is a no', tooMany.go === false && tooMany.said === 'Asked too many times today.');
  const busy = await askMayFetch(chrome, aServerThat({
    status: 503, body: { fetch: false, said: 'Try again in a while.' },
  }).fetch);
  check('a 503 is a no', busy.go === false && busy.kind === 'no');
  const bare = await askMayFetch(chrome, aServerThat({ status: 403, body: { fetch: false } }).fetch);
  check('a no with no sentence still says something, with the status',
    bare.go === false && bare.said.includes('403'));
  const contradicts = await askMayFetch(chrome, aServerThat({ status: 403, body: { fetch: true, said: 'ok' } }).fetch);
  check('a yes under a 403 is not trusted: it is a no, said as such',
    contradicts.go === false && contradicts.kind === 'garbled');
}

{
  const { chrome } = installFakeChrome();
  await withAPass(chrome);
  const down = await askMayFetch(chrome, async () => { throw new TypeError('Failed to fetch'); });
  check('unreachable: a fetch that throws is a no, with words that say Kartaan could not be reached',
    down.go === false && down.kind === 'unreachable' && down.said.includes('Kartaan could not be reached')
    && down.said.includes('not started'));
  const noWay = await askMayFetch(chrome, undefined);
  check('and no way to connect at all reads the same, never a real call',
    noWay.go === false && noWay.kind === 'unreachable');
  const slow = await askMayFetch(chrome, (address, init) => new Promise((resolve, reject) => {
    init.signal.addEventListener('abort', () => reject(new Error('aborted')));
  }), { timeoutMs: 30 });
  check('too slow: nothing in time is a no, saying it did not answer, and the call is aborted',
    slow.go === false && slow.kind === 'unreachable' && slow.said.includes('did not answer'));
  const stuck = await askMayFetch(chrome, () => new Promise(() => {}), { timeoutMs: 30 });
  check('even a fetch that ignores the abort cannot hold the sync for ever',
    stuck.go === false && stuck.said.includes('did not answer'));
  const html = await askMayFetch(chrome, aServerThat({ status: 502, notJson: true }).fetch);
  check('garbled: an answer that is not JSON is a no, in words',
    html.go === false && html.kind === 'garbled' && html.said.includes('502'));
  const odd = await askMayFetch(chrome, aServerThat({ body: { yes: 'please' } }).fetch);
  check('garbled: JSON of a shape the server never sends is a no, in words',
    odd.go === false && odd.kind === 'garbled' && odd.said.includes('not with a yes or a no'));
  const list = await askMayFetch(chrome, aServerThat({ body: [true] }).fetch);
  check('garbled: JSON that is not an object is a no', list.go === false && list.kind === 'garbled');
  const sayingIt = await askMayFetch(chrome, aServerThat({ body: { fetch: false, said: `your pass ${PASS} is bad` } }).fetch);
  check('a server that echoed the pass back has it taken out of the sentence',
    !sayingIt.said.includes(PASS));
}

{
  const { chrome } = installFakeChrome();
  const server = aServerThat({ body: { fetch: true, said: 'yes' } });
  const got = await askMayFetch(chrome, server.fetch);
  check('no pass: the sync may go ahead, but cannot ask -- and nothing is sent',
    got.go === true && got.asked === false && got.kind === 'no-pass' && server.calls.length === 0);
  check('and it says plainly that the check was not made because no run pass is saved',
    got.said.includes('not asked') && got.said.includes('no run pass is saved'));
}

/* ------------------------------------------------------------ it finished */

{
  const { chrome } = installFakeChrome();
  await withAPass(chrome);
  const server = aServerThat({
    body: { started: true, said: 'Kartaan has started your run.', failed: ['fk_orders', 'me_returns'] },
  });
  const got = await tellFinished(chrome, server.fetch, { failed: ['fk_orders', 'me_returns', 'fk_orders'] });
  const form = formOf(server.calls[0]);
  check('finished: posted to /finished as a form with the pass and the failed ids, comma-separated, each once',
    server.calls.length === 1 && server.calls[0].address === FINISHED_ADDRESS
    && server.calls[0].init.method === 'POST' && form.pass === PASS && form.failed === 'fk_orders,me_returns'
    && Object.keys(form).sort().join() === 'failed,pass');
  check('told: the server\'s sentence is what comes back, with the failed reports named',
    got.told === true && got.said.includes('Kartaan has started your run.') && got.said.includes('fk_orders, me_returns'));

  const clean = aServerThat({ body: { started: true, said: 'Kartaan has started your run.', failed: [] } });
  await tellFinished(chrome, clean.fetch, { failed: [] });
  check('nothing failed: the failed field is left out, not sent empty',
    JSON.stringify(formOf(clean.calls[0])) === JSON.stringify({ pass: PASS }));

  const odd = theFailedReportsToSend(['fk_orders', 'Bad Name', '', 'me_x', 'ok;drop', 'fk_orders', '1abc']);
  check('only ids the server accepts are sent (a bad name would refuse the whole tell)',
    odd.join() === 'fk_orders,me_x');
  const many = theFailedReportsToSend(Array.from({ length: 60 }, (_, i) => `fk_r${i}`));
  check('and at most forty, the server\'s own limit', many.length === 40);

  const refused = await tellFinished(chrome, aServerThat({
    status: 429, body: { started: false, said: 'Kartaan has already started 6 runs today.', failed: [] },
  }).fetch, { failed: [] });
  check('a refusal is not "told": the server\'s words and the run still runs on its schedule',
    refused.told === false && refused.said.includes('already started 6 runs')
    && refused.said.includes('still runs on its own schedule'));
  const down = await tellFinished(chrome, async () => { throw new Error('offline'); }, { failed: [] });
  check('unreachable: explicit words, and the run still runs on its schedule',
    down.told === false && down.said.includes('Kartaan could not be reached')
    && down.said.includes('still runs on its own schedule'));
  const slow = await tellFinished(chrome, () => new Promise(() => {}), { failed: [], timeoutMs: 30 });
  check('too slow: the same words, saying it did not answer', slow.told === false && slow.said.includes('did not answer'));
  const garbled = await tellFinished(chrome, aServerThat({ status: 500, notJson: true }).fetch, { failed: [] });
  check('not JSON: explicit words, not a silent nothing',
    garbled.told === false && garbled.kind === 'garbled' && garbled.said.includes('still runs on its own schedule'));
  const wrongShape = await tellFinished(chrome, aServerThat({ body: { hello: 1 } }).fetch, { failed: [] });
  check('JSON of an odd shape: explicit words', wrongShape.told === false && wrongShape.kind === 'garbled');
}

{
  const { chrome } = installFakeChrome();
  const server = aServerThat({ body: { started: true, said: 'x' } });
  const got = await tellFinished(chrome, server.fetch, { failed: ['fk_orders'] });
  check('no pass: nothing is sent, and it says so in words',
    got.told === false && got.kind === 'no-pass' && server.calls.length === 0 && got.said.includes('no run pass is saved'));
}

/* ------------------------------------- starting a sync asks first (screen.js) */

const FORM_PANEL = 'xuptj';
async function aSetUpPanel(extra = {}) {
  const browser = installFakeChrome();
  const { chrome } = browser;
  const started = [];
  const parts = {
    book: BOOK,
    now: () => Date.UTC(2026, 8, 16, 3, 0),
    startTheNight: async (c, how) => { started.push(how.doing); return startTheNight(c, how); },
    carryOn: async () => {},
    ...extra,
  };
  await answerThePanelsQuestion(chrome, parts, { do: 'save-the-panel-name', panel: FORM_PANEL });
  await answerThePanelsQuestion(chrome, parts, { do: 'check-the-drive' });
  return { chrome, parts, started };
}

{
  const server = aServerThat({ body: { fetch: true, said: 'yes' } });
  const { chrome, parts, started } = await aSetUpPanel({ fetch: server.fetch });
  await withAPass(chrome);
  const said = await answerThePanelsQuestion(chrome, parts, { do: 'run-now', reportIds: ['fk_claims'] });
  check('run now: pass saved and fetch true -- the sync starts, after one ask',
    Boolean(said.started) && started.length === 1 && server.calls.length === 1
    && server.calls[0].address === MAY_FETCH_ADDRESS);
}

{
  const server = aServerThat({ status: 403, body: { fetch: false, said: 'Your trial has ended and was not paid for.' } });
  const { chrome, parts, started } = await aSetUpPanel({ fetch: server.fetch });
  await withAPass(chrome);
  const said = await answerThePanelsQuestion(chrome, parts, { do: 'run-now', reportIds: ['fk_claims'] });
  check('run now: fetch false -- NOT started, and the server\'s sentence is what the panel is given',
    !said.started && said.wrong === 'Your trial has ended and was not paid for.' && started.length === 0);
  check('and no night was written at all', (await theNight(chrome)) === null);
  const stands = await howItStands(chrome, { book: BOOK, now: NOW });
  check('and the panel\'s state carries that sentence under Kartaan, with the pass saved as a yes',
    stands.kartaan.saved === true && stands.kartaan.last.said === 'Your trial has ended and was not paid for.');
}

{
  const { chrome, parts, started } = await aSetUpPanel({ fetch: async () => { throw new Error('offline'); } });
  await withAPass(chrome);
  const said = await answerThePanelsQuestion(chrome, parts, { do: 'run-now', reportIds: ['fk_claims'] });
  check('run now: Kartaan unreachable -- NOT started, and the words say why',
    !said.started && said.wrong.includes('Kartaan could not be reached') && started.length === 0
    && (await theNight(chrome)) === null);
}

{
  const server = aServerThat({ body: { fetch: true, said: 'yes' } });
  const { chrome, parts, started } = await aSetUpPanel({ fetch: server.fetch });
  const said = await answerThePanelsQuestion(chrome, parts, { do: 'run-now', reportIds: ['fk_claims'] });
  check('run now: NO PASS -- starts as it did, nothing is asked, and the answer says the check was not made',
    Boolean(said.started) && started.length === 1 && server.calls.length === 0
    && said.note.includes('no run pass is saved'));
  const stands = await howItStands(chrome, { book: BOOK, now: NOW });
  check('and the panel\'s state says the same under Kartaan',
    stands.kartaan.saved === false && stands.kartaan.last.said.includes('no run pass is saved'));
}

{
  const server = aServerThat({ body: { fetch: true, said: 'yes' } });
  const { chrome, parts } = await aSetUpPanel({ fetch: server.fetch });
  await withAPass(chrome);
  const nothingTicked = await answerThePanelsQuestion(chrome, parts, { do: 'run-now', reportIds: ['not_a_report'] });
  check('a sync that could never start is refused before Kartaan is asked (the ask is rationed)',
    Boolean(nothingTicked.wrong) && server.calls.length === 0);
}

{
  const server = aServerThat({ body: { fetch: true, said: 'yes' } });
  const { chrome, parts } = await aSetUpPanel({ fetch: server.fetch });
  await withAPass(chrome);
  const first = await startTheScheduledSync(chrome, parts);
  check('the scheduled sync asks too, and when told yes starts as it always did',
    Boolean(first.started) && server.calls.length === 1 && server.calls[0].address === MAY_FETCH_ADDRESS);
  const night = await theNight(chrome);
  check('and the night it writes is the ordinary one: no new field on it, still going',
    night.finishedAt === null && night.toldKartaan === undefined && night.kartaanSaid === undefined);
}

{
  const server = aServerThat({ status: 403, body: { fetch: false, said: 'Not on your plan.' } });
  const { chrome, parts, started } = await aSetUpPanel({ fetch: server.fetch });
  await withAPass(chrome);
  const first = await startTheScheduledSync(chrome, parts);
  check('the scheduled sync obeys a no: nothing started, no night, the sentence is in what was refused',
    first.started === null && started.length === 0 && (await theNight(chrome)) === null
    && first.refused.length === 1 && first.refused[0].wrong === 'Not on your plan.');
  check('and a no ends the whole timed queue (the next platform would only ask the same, and asks are rationed)',
    server.calls.length === 1 && ((await chrome.storage.local.get(THE_QUEUE))[THE_QUEUE] || []).length === 0);
}

{
  const server = aServerThat({ body: { fetch: true, said: 'yes' } });
  const { chrome, parts } = await aSetUpPanel({ fetch: server.fetch });
  await withAPass(chrome);
  await chrome.storage.local.set({
    'kartaan-autosync-paused': { reportIds: ['fk_claims'], dataDate: '2026-09-15', at: 1 },
  });
  const said = await answerThePanelsQuestion(chrome, parts, { do: 'resume' });
  check('resume asks too', Boolean(said.started) && server.calls.length === 1);
}

{
  const server = aServerThat({ status: 403, body: { fetch: false, said: 'Not on your plan.' } });
  const { chrome, parts } = await aSetUpPanel({ fetch: server.fetch });
  await withAPass(chrome);
  await chrome.storage.local.set({
    'kartaan-autosync-paused': { reportIds: ['fk_claims'], dataDate: '2026-09-15', at: 1 },
  });
  const said = await answerThePanelsQuestion(chrome, parts, { do: 'resume' });
  check('resume obeys a no, and the sync stays paused for when it may run',
    !said.started && said.wrong === 'Not on your plan.'
    && Boolean((await chrome.storage.local.get('kartaan-autosync-paused'))['kartaan-autosync-paused']));
}

/* ----------------------------- a night's natural end tells Kartaan (nightly.js) */

const OPEN_AT = 'https://seller.flipkart.com/index.html';

function aWalkThat() {
  const it = { held: null, started: [], cleared: 0 };
  it.theWalkNow = async () => it.held;
  it.endTheWalkNow = async () => { it.held = null; it.cleared += 1; };
  it.startAWalk = async (how) => { it.started.push({ ...how }); it.held = { reportId: how.reportId, answer: null }; };
  it.itFinished = (answer) => { it.held = { ...it.held, answer }; };
  return it;
}

/** A night of two reports, run to its end: one fails, one needs the seller. */
async function aNightThatRanToItsEnd({ makeTell }) {
  const { chrome } = installFakeChrome();
  await withAPass(chrome);
  const tell = makeTell(chrome);
  const walk = aWalkThat();
  await startTheNight(chrome, {
    doing: ['fk_claims', 'fk_returns'], mayAskFor: 0, at: NOW, openAt: OPEN_AT, dataDate: '2026-10-11',
  });
  await carryTheNightOn(chrome, { ...walk, tellKartaan: tell, at: NOW });
  walk.itFinished({ state: 'failed', reportId: 'fk_claims', say: 'the page broke', dataDate: '2026-10-11' });
  await carryTheNightOn(chrome, { ...walk, tellKartaan: tell, at: NOW });
  walk.itFinished({ state: 'needs-you', reportId: 'fk_returns', say: 'not built', dataDate: '2026-10-11', size: 0 });
  await carryTheNightOn(chrome, { ...walk, tellKartaan: tell, at: NOW + 1000 });
  return { chrome, walk };
}

{
  const server = aServerThat({ body: { started: true, said: 'Kartaan has started your run.', failed: ['fk_claims', 'fk_returns'] } });
  const installed = installFakeChrome();
  const tell = ({ failed }) => tellFinished(installed.chrome, server.fetch, { failed });
  await withAPass(installed.chrome);
  const walk = aWalkThat();
  await startTheNight(installed.chrome, {
    doing: ['fk_claims', 'fk_returns'], mayAskFor: 0, at: NOW, openAt: OPEN_AT, dataDate: '2026-10-11',
  });
  const part = { ...walk, tellKartaan: tell, at: NOW };
  await carryTheNightOn(installed.chrome, part);
  walk.itFinished({ state: 'failed', reportId: 'fk_claims', say: 'the page broke', dataDate: '2026-10-11' });
  await carryTheNightOn(installed.chrome, part);
  check('mid-night, nothing is told: Kartaan hears only of an end', server.calls.length === 0);
  walk.itFinished({ state: 'needs-you', reportId: 'fk_returns', say: 'not built', dataDate: '2026-10-11', size: 0 });
  await Promise.all([carryTheNightOn(installed.chrome, part), carryTheNightOn(installed.chrome, part)]);
  const night = await theNight(installed.chrome);
  check('the natural end tells /finished once, even with two wakes together',
    night.finishedAt !== null && server.calls.length === 1 && server.calls[0].address === FINISHED_ADDRESS);
  check('with the failed and the needs-you reports\' ids, as the server reads them',
    formOf(server.calls[0]).failed === 'fk_claims,fk_returns' && formOf(server.calls[0]).pass === PASS);
  check('the answer is kept on the night as toldKartaan, for this very start and end',
    night.toldKartaan.told === true && night.toldKartaan.said.includes('Kartaan has started your run.')
    && night.toldKartaan.startedAt === night.startedAt && night.toldKartaan.finishedAt === night.finishedAt);
  await carryTheNightOn(installed.chrome, part);
  await carryTheNightOn(installed.chrome, part);
  check('and later wakes of the finished night tell nothing more', server.calls.length === 1);
  check('the run log shows what Kartaan was told', theRunLog(night).text.includes('Told Kartaan: Kartaan has started your run.'));
  check('and the end-of-sync notice carries it', theSyncSummary(night).message.includes('Kartaan has started your run.'));
  check('the pass is in none of the stored night, the run log or the notice',
    ![JSON.stringify(night), theRunLog(night).text, theSyncSummary(night).message].some((one) => one.includes(PASS)));

  /* A retried or resumed sync is a new night with its own end, and it tells again. */
  await startTheNight(installed.chrome, {
    doing: ['fk_claims'], mayAskFor: 0, at: NOW + 60000, openAt: OPEN_AT, dataDate: '2026-10-11',
  });
  await carryTheNightOn(installed.chrome, { ...part, at: NOW + 60000 });
  walk.itFinished({ state: 'landed', reportId: 'fk_claims', size: 5, dataDate: '2026-10-11' });
  await carryTheNightOn(installed.chrome, { ...part, at: NOW + 61000 });
  check('a retried night tells again at its own end, with nothing failed this time',
    server.calls.length === 2 && formOf(server.calls[1]).failed === undefined
    && (await theNight(installed.chrome)).toldKartaan.told === true);
}

{
  const unreachable = async () => { throw new Error('offline'); };
  const { chrome } = await aNightThatRanToItsEnd({
    makeTell: (c) => ({ failed }) => tellFinished(c, unreachable, { failed }),
  });
  const night = await theNight(chrome);
  check('a failure to tell is words on the night, naming that the run still runs on its schedule',
    night.toldKartaan.told === false && night.toldKartaan.said.includes('Kartaan could not be reached')
    && night.toldKartaan.said.includes('still runs on its own schedule'));
  check('and it never changes how the night went: same ending, same reports, same reason',
    night.finishedAt !== null && night.why.startsWith('2 reports did not land:')
    && night.done.length === 2 && night.left.length === 0);
}

{
  const { chrome } = await aNightThatRanToItsEnd({
    makeTell: () => async () => { throw new Error('the tell itself broke'); },
  });
  const night = await theNight(chrome);
  check('even a tell that throws changes nothing: the night ends as it would, with words about it',
    night.finishedAt !== null && night.why.startsWith('2 reports did not land:')
    && night.toldKartaan.told === false && night.toldKartaan.said.includes('could not be told'));
}

{
  const { chrome } = await aNightThatRanToItsEnd({ makeTell: () => undefined });
  const night = await theNight(chrome);
  check('with nothing handed in to tell with, the night ends exactly as before and carries no toldKartaan',
    night.finishedAt !== null && night.toldKartaan === undefined);
}

{
  const server = aServerThat({ body: { started: true, said: 'x' } });
  const installed = installFakeChrome();
  const walk = aWalkThat();
  const tell = ({ failed }) => tellFinished(installed.chrome, server.fetch, { failed });
  await startTheNight(installed.chrome, {
    doing: ['fk_claims'], mayAskFor: 0, at: NOW, openAt: OPEN_AT, dataDate: '2026-10-11',
  });
  await carryTheNightOn(installed.chrome, { ...walk, tellKartaan: tell, at: NOW });
  walk.itFinished({ state: 'landed', reportId: 'fk_claims', size: 5, dataDate: '2026-10-11' });
  await carryTheNightOn(installed.chrome, { ...walk, tellKartaan: tell, at: NOW + 1 });
  const night = await theNight(installed.chrome);
  check('with no run pass saved the night still ends, nothing is sent, and the night says why',
    night.finishedAt !== null && server.calls.length === 0 && night.toldKartaan.told === false
    && night.toldKartaan.said.includes('no run pass is saved'));
}

{
  /* STOP ends a night by its own door, and never tells. */
  const server = aServerThat({ body: { started: true, said: 'x' } });
  const { chrome, parts } = await aSetUpPanel({ fetch: server.fetch });
  await withAPass(chrome);
  server.calls.length = 0;
  await startTheNight(chrome, {
    doing: ['fk_claims'], mayAskFor: 0, at: NOW, openAt: OPEN_AT, dataDate: '2026-10-11',
  });
  await answerThePanelsQuestion(chrome, parts, { do: 'stop' });
  const walk = aWalkThat();
  await carryTheNightOn(chrome, { ...walk, tellKartaan: () => { throw new Error('must not be called'); } });
  const night = await theNight(chrome);
  check('Stop does not tell Kartaan, and later wakes of the stopped night do not either',
    night.finishedAt !== null && night.why === 'Stopped from the panel.' && server.calls.length === 0
    && night.toldKartaan === undefined);
}

{
  /* A sign-in pause ends the night by its own door too. */
  const server = aServerThat({ body: { started: true, said: 'x' } });
  const installed = installFakeChrome();
  await withAPass(installed.chrome);
  const walk = aWalkThat();
  const tell = ({ failed }) => tellFinished(installed.chrome, server.fetch, { failed });
  await startTheNight(installed.chrome, {
    doing: ['fk_claims', 'fk_returns'], mayAskFor: 0, at: NOW, openAt: OPEN_AT, dataDate: '2026-10-11',
  });
  await carryTheNightOn(installed.chrome, { ...walk, tellKartaan: tell, at: NOW });
  walk.itFinished({ state: 'failed', reportId: 'fk_claims', say: 'sign in', needsSigningIn: true, dataDate: '2026-10-11' });
  await carryTheNightOn(installed.chrome, { ...walk, tellKartaan: tell, at: NOW + 1 });
  const night = await theNight(installed.chrome);
  check('the sign-in pause does not tell Kartaan: the sync is not over, it is waiting for him',
    night.finishedAt !== null && night.why.includes('signed in to') && server.calls.length === 0
    && night.toldKartaan === undefined);
}

/* ------------------ told once per WHOLE sync, not per platform (Control's ruling, 2026-10-12) */

async function oneNightThatEnds({ chrome, tell, doing, failedId, at }) {
  const walk = aWalkThat();
  await startTheNight(chrome, { doing, mayAskFor: 0, at, openAt: OPEN_AT, dataDate: '2026-10-11' });
  await carryTheNightOn(chrome, { ...walk, tellKartaan: tell, at });
  walk.itFinished({ state: 'failed', reportId: failedId, say: 'the page broke', dataDate: '2026-10-11' });
  await carryTheNightOn(chrome, { ...walk, tellKartaan: tell, at });
  return theNight(chrome);
}

{
  const server = aServerThat({ body: { started: true, said: 'Kartaan has started your run.' } });
  const { chrome } = installFakeChrome();
  await withAPass(chrome);
  const tell = ({ failed }) => tellFinished(chrome, server.fetch, { failed });
  /* Platform one ends while platform two is still queued. */
  await chrome.storage.local.set({ [THE_SCHEDULED_QUEUE]: [['fk_returns']] });
  const first = await oneNightThatEnds({ chrome, tell, doing: ['fk_claims'], failedId: 'fk_claims', at: NOW });
  check('tell deferred while another platform is queued: the server is not called at that night\'s end',
    first.finishedAt !== null && server.calls.length === 0);
  check('and that night says in plain words that Kartaan is told when the whole sync is done',
    first.toldKartaan.told === false && first.toldKartaan.kind === 'waiting'
    && first.toldKartaan.said === 'Kartaan is told when the whole sync is done.'
    && first.toldKartaan.finishedAt === first.finishedAt && first.why.includes('fk_claims'));
  check('its failed ids are remembered as a list under their own key, never the pass',
    JSON.stringify((await chrome.storage.local.get(THE_SYNC_FAILED))[THE_SYNC_FAILED]) === '["fk_claims"]');
  check('the run log and the finished notice print the waiting words readably',
    theRunLog(first).text.includes('Told Kartaan: Kartaan is told when the whole sync is done.')
    && theSyncSummary(first).message.includes('Kartaan is told when the whole sync is done.'));
  /* The queue is emptied as the last platform starts; its night ends. */
  await chrome.storage.local.set({ [THE_SCHEDULED_QUEUE]: [] });
  const last = await oneNightThatEnds({ chrome, tell, doing: ['fk_returns'], failedId: 'fk_returns', at: NOW + 5000 });
  const sent = server.calls.length === 1 ? formOf(server.calls[0]) : {};
  check('one tell at the end of the whole sync, carrying the union of every platform\'s failed ids',
    server.calls.length === 1 && server.calls[0].address === FINISHED_ADDRESS
    && (sent.failed || '').split(',').sort().join() === 'fk_claims,fk_returns' && last.toldKartaan.told === true);
  check('and the remembered list is cleared after the tell',
    (await chrome.storage.local.get(THE_SYNC_FAILED))[THE_SYNC_FAILED] === undefined);
}

{
  const server = aServerThat({ body: { started: true, said: 'ok' } });
  const { chrome } = installFakeChrome();
  await withAPass(chrome);
  const tell = ({ failed }) => tellFinished(chrome, server.fetch, { failed });
  const night = await oneNightThatEnds({ chrome, tell, doing: ['fk_claims'], failedId: 'fk_claims', at: NOW });
  check('a single-platform sync (nothing queued) still tells at its natural end, as before',
    server.calls.length === 1 && night.toldKartaan.told === true);
}

{
  const { chrome } = installFakeChrome();
  await withAPass(chrome);
  await chrome.storage.local.set({ [THE_SCHEDULED_QUEUE]: [['fk_returns']] });
  let called = 0;
  const tell = () => { called++; throw new Error('boom'); };
  const night = await oneNightThatEnds({ chrome, tell, doing: ['fk_claims'], failedId: 'fk_claims', at: NOW });
  check('a deferred night never calls the tell at all, so nothing it does can change how the night went',
    called === 0 && night.finishedAt !== null && night.toldKartaan.kind === 'waiting');
  await chrome.storage.local.set({ [THE_SCHEDULED_QUEUE]: [] });
  const ending = await oneNightThatEnds({ chrome, tell, doing: ['fk_returns'], failedId: 'fk_returns', at: NOW + 9 });
  check('a throwing tell at the whole sync\'s end still leaves the night finished, with words, and the list cleared',
    ending.finishedAt !== null && ending.toldKartaan.told === false && ending.toldKartaan.said.includes('could not be told')
    && (await chrome.storage.local.get(THE_SYNC_FAILED))[THE_SYNC_FAILED] === undefined);
}

{
  /* A sync already going (the next platform) keeps what the earlier ones left. */
  const server = aServerThat({ body: { fetch: true, said: 'yes' } });
  const { chrome, parts } = await aSetUpPanel({ fetch: server.fetch });
  await withAPass(chrome);
  await chrome.storage.local.set({ [THE_SYNC_FAILED]: ['left_by_platform_one'] });
  const kept = await startTheScheduledSync(chrome, { ...parts, continuing: true });
  check('the next platform of a sync already going keeps what the earlier ones left',
    Boolean(kept.started) && (await chrome.storage.local.get(THE_SYNC_FAILED))[THE_SYNC_FAILED].join() === 'left_by_platform_one');
}

{
  const server = aServerThat({ body: { fetch: true, said: 'yes' } });
  const { chrome, parts } = await aSetUpPanel({ fetch: server.fetch });
  await withAPass(chrome);
  await chrome.storage.local.set({ [THE_SYNC_FAILED]: ['stale_one'] });
  const refused = await answerThePanelsQuestion(chrome, parts, { do: 'resume' });
  check('a start that is refused (nothing paused) leaves the remembered list alone',
    Boolean(refused.wrong) && (await chrome.storage.local.get(THE_SYNC_FAILED))[THE_SYNC_FAILED].join() === 'stale_one');
  const said = await answerThePanelsQuestion(chrome, parts, { do: 'run-now', reportIds: ['fk_claims'] });
  check('accumulator cleared at a new whole sync: Run now starts with nothing remembered',
    Boolean(said.started) && (await chrome.storage.local.get(THE_SYNC_FAILED))[THE_SYNC_FAILED] === undefined);
}

{
  const server = aServerThat({ status: 403, body: { fetch: false, said: 'Not on your plan.' } });
  const { chrome, parts } = await aSetUpPanel({ fetch: server.fetch });
  await withAPass(chrome);
  await chrome.storage.local.set({ [THE_SYNC_FAILED]: ['left_by_platform_one'] });
  await startTheScheduledSync(chrome, { ...parts, continuing: true });
  check('Kartaan\'s no empties the queue and drops the remembered list: no half-done whole sync is ever told',
    ((await chrome.storage.local.get(THE_QUEUE))[THE_QUEUE] || []).length === 0
    && (await chrome.storage.local.get(THE_SYNC_FAILED))[THE_SYNC_FAILED] === undefined);
}

{
  /* The real flow: platform one ends deferred, the next start is refused, the stalled whole sync tells ONCE. */
  const server = aServerThat({ body: { started: true, said: 'Kartaan has started your run.' } });
  const { chrome } = installFakeChrome();
  await withAPass(chrome);
  const tell = ({ failed }) => tellFinished(chrome, server.fetch, { failed });
  await chrome.storage.local.set({ [THE_SCHEDULED_QUEUE]: [{ reportIds: ['me_orders'] }] });
  const first = await oneNightThatEnds({ chrome, tell, doing: ['fk_claims'], failedId: 'fk_claims', at: NOW });
  const told = () => server.calls.filter((one) => one.address === FINISHED_ADDRESS);
  const next = await startTheNextPlatform(chrome, {
    book: BOOK, startTheNight, carryOn: async () => {}, fetch: server.fetch, continuing: true,
  });
  check('the second platform start is refused (nothing started, not waiting) and nothing is told yet',
    next.started === null && !next.waiting && next.refused.length === 1 && told().length === 0);
  const answer = await tellForASyncThatCannotContinue(chrome, next, first, tell);
  check('then exactly ONE tell goes out, with the first platform\'s ids, and the list is forgotten',
    told().length === 1 && formOf(told()[0]).failed === 'fk_claims' && answer.told === true
    && (await chrome.storage.local.get(THE_SYNC_FAILED))[THE_SYNC_FAILED] === undefined);
  check('and the answer replaces "waiting" on the earlier night',
    (await theNight(chrome)).toldKartaan.told === true);
  await tellForASyncThatCannotContinue(chrome, next, first, tell);
  check('asked again, it does not tell a second time', told().length === 1);
  const empty = await tellForASyncThatCannotContinue(chrome, { started: null, waiting: true, refused: [] }, first, tell);
  check('a next platform that started, or is waiting for a running night, tells nothing', empty === null && told().length === 1);
}

{
  const { chrome } = installFakeChrome();
  await chrome.storage.local.set({ [THE_SYNC_FAILED]: [] });
  let called = 0;
  const night = await startTheNight(chrome, { doing: ['fk_claims'], mayAskFor: 0, at: NOW, openAt: OPEN_AT, dataDate: '2026-10-11' });
  const answered = await tellForASyncThatCannotContinue(chrome, { started: null, refused: [] }, night,
    () => { called++; throw new Error('boom'); });
  check('an empty remembered list still counts as a sync to tell about; a throwing tell is swallowed and the list forgotten',
    called === 1 && answered === null && (await chrome.storage.local.get(THE_SYNC_FAILED))[THE_SYNC_FAILED] === undefined);
  const none = await tellForASyncThatCannotContinue(chrome, { started: null, refused: [] }, night, () => { called++; });
  check('with no list at all (Kartaan\'s no, a pause, Stop, or a natural end) nothing is told', none === null && called === 1);
}

{
  /* Sign-in pause and Stop forget the list, so the fallback cannot send after them. */
  const server = aServerThat({ body: { started: true, said: 'x' } });
  const installed = installFakeChrome();
  await withAPass(installed.chrome);
  const walk = aWalkThat();
  const tell = ({ failed }) => tellFinished(installed.chrome, server.fetch, { failed });
  await installed.chrome.storage.local.set({ [THE_SYNC_FAILED]: ['fk_returns'] });
  await startTheNight(installed.chrome, {
    doing: ['fk_claims', 'fk_returns'], mayAskFor: 0, at: NOW, openAt: OPEN_AT, dataDate: '2026-10-11',
  });
  await carryTheNightOn(installed.chrome, { ...walk, tellKartaan: tell, at: NOW });
  walk.itFinished({ state: 'failed', reportId: 'fk_claims', say: 'sign in', needsSigningIn: true, dataDate: '2026-10-11' });
  await carryTheNightOn(installed.chrome, { ...walk, tellKartaan: tell, at: NOW + 1 });
  const paused = await theNight(installed.chrome);
  const after = await tellForASyncThatCannotContinue(installed.chrome, { started: null, refused: [] }, paused, tell);
  check('after a sign-in pause the remembered list is gone and nothing is told, even by the fallback',
    (await installed.chrome.storage.local.get(THE_SYNC_FAILED))[THE_SYNC_FAILED] === undefined
    && after === null && server.calls.length === 0);
}

{
  const server = aServerThat({ body: { started: true, said: 'x' } });
  const { chrome, parts } = await aSetUpPanel({ fetch: server.fetch });
  await withAPass(chrome);
  await startTheNight(chrome, {
    doing: ['fk_claims'], mayAskFor: 0, at: NOW, openAt: OPEN_AT, dataDate: '2026-10-11',
  });
  server.calls.length = 0;
  await chrome.storage.local.set({ [THE_SYNC_FAILED]: ['fk_returns'] });
  await answerThePanelsQuestion(chrome, parts, { do: 'stop' });
  const stopped = await theNight(chrome);
  const after = await tellForASyncThatCannotContinue(chrome, { started: null, refused: [] }, stopped,
    ({ failed }) => tellFinished(chrome, server.fetch, { failed }));
  check('after Stop the remembered list is gone and nothing is told, even by the fallback',
    (await chrome.storage.local.get(THE_SYNC_FAILED))[THE_SYNC_FAILED] === undefined
    && after === null && server.calls.length === 0);
}

{
  const NIGHTLY = readFileSync(new URL('nightly.js', HERE), 'utf8');
  const SCREEN = readFileSync(new URL('screen.js', HERE), 'utf8').replace(/\r\n/g, '\n');
  check('the two keys are spelt once (nightly.js) and screen.js\'s queue is the very same key',
    THE_QUEUE === THE_SCHEDULED_QUEUE && THE_SYNC_FAILED === 'kartaan-autosync-sync-failed');
  const defers = (t) => /if \(queued\) \{[\s\S]*?kind: 'waiting'[\s\S]*?return written;/.test(t);
  check('nightly.js defers the tell while a platform is queued', defers(NIGHTLY));
  check('PROOF: with the deferral removed from nightly.js that check goes red',
    !defers(NIGHTLY.replace('if (queued) {', 'if (false) {')));
  const unions = (t) => t.includes('const ids = [...new Set([...before, ...thisNights])]');
  check('nightly.js tells with the earlier platforms\' ids joined to this night\'s', unions(NIGHTLY));
  check('PROOF: with the union removed from nightly.js that check goes red',
    !unions(NIGHTLY.replace('const ids = [...new Set([...before, ...thisNights])]', 'const ids = [...new Set([...thisNights])]')));
  const clearsAtStart = (t) => t.includes('if (!asked.continuing) await chrome.storage.local.remove(THE_SYNC_FAILED)')
    && t.includes('timed, continuing: Boolean(parts.continuing)');
  check('screen.js clears the list when a whole sync starts, but not for the next platform of one', clearsAtStart(SCREEN));
  check('PROOF: with the clearing removed from screen.js that check goes red',
    !clearsAtStart(SCREEN.replace('if (!asked.continuing) await', 'if (false) await')));
  const block = (t) => t.slice(t.indexOf('const followTheNightThrough'), t.indexOf('const theNightsParts'));
  const outside = (t) => t.slice(0, t.indexOf('const followTheNightThrough')) + t.slice(t.indexOf('const theNightsParts'));
  const marks = (t) => block(t).includes('fetch: kartaanFetch, continuing: true,') && !outside(t).includes('continuing');
  check('worker.js: exactly the followTheNightThrough call is marked continuing; onDue, onRecheck, run-now and resume are not',
    marks(WORKER));
  check('PROOF: with the mark removed, or put on another starter, that check goes red',
    !marks(WORKER.replace('continuing: true', ''))
    && !marks(WORKER.replace('fetch: kartaanFetch }, plan)', 'fetch: kartaanFetch, continuing: true }, plan)')));
  const falls = (t) => block(t).includes('tellForASyncThatCannotContinue(chrome, next, doneNight');
  check('worker.js tells for a whole sync that cannot continue, right after trying the next platform', falls(WORKER));
  check('PROOF: with that call removed from worker.js that check goes red',
    !falls(WORKER.replace('tellForASyncThatCannotContinue(chrome, next, doneNight', 'noop(chrome, next, doneNight')));
  const pauseClears = (t) => /A sign-in pause never tells[\s\S]{0,200}remove\(THE_SYNC_FAILED\)/.test(t);
  const stopClears = (t) => /Stop never tells[\s\S]{0,200}remove\(THE_SYNC_FAILED\)/.test(t);
  check('the sign-in pause and Stop both forget the remembered list', pauseClears(NIGHTLY) && stopClears(SCREEN));
  check('PROOF: with either clearing removed that check goes red',
    !pauseClears(NIGHTLY.replace('remove(THE_SYNC_FAILED)', 'remove(NOTHING)'))
    && !stopClears(SCREEN.replace('remove(THE_SYNC_FAILED)', 'remove(NOTHING)')));
}

/* ---------------------------------------- the pass is never shown (the page) */

{
  installFakeBrowser();
  const server = aServerThat({ status: 403, body: { fetch: false, said: 'Not on your plan.' } });
  const { chrome, parts } = await aSetUpPanel({ fetch: server.fetch });
  await withAPass(chrome);
  await answerThePanelsQuestion(chrome, parts, { do: 'run-now', reportIds: ['fk_claims'] });
  const stands = await howItStands(chrome, { book: BOOK, now: NOW });
  const pressed = [];
  const panel = buildThePanel(document.body, {
    connectTheDrive() {}, saveThePanelName() {}, runNow() {}, stop() {}, setTheHour() {},
    saveTheRunPass: (pass) => pressed.push(pass),
  });
  showHowItStands(panel, stands);
  check('the panel has a box for the pass, hidden as a password box, and a Save button',
    panel.runPass.type === 'password' && panel.saveRunPass.textContent === 'Save');
  check('the panel says whether a pass is saved, and what Kartaan last said',
    panel.runPassState.textContent === 'saved' && panel.kartaanSaid.textContent.includes('Not on your plan.'));
  check('and nothing the panel was told or shows holds the pass',
    !JSON.stringify(stands).includes(PASS) && !panel.runPassState.textContent.includes(PASS)
    && !panel.kartaanSaid.textContent.includes(PASS));
  panel.runPass.value = PASS;
  panel.saveRunPass.click();
  check('pressing Save hands the pasted text to the worker\'s ask', pressed.length === 1 && pressed[0] === PASS);
  const everythingStored = JSON.stringify(Object.keys(await chrome.storage.local.get(null)));
  const keysHoldingIt = Object.entries(await chrome.storage.local.get(null))
    .filter(([, value]) => JSON.stringify(value).includes(PASS)).map(([key]) => key);
  check('in storage the pass lives under its own key and nowhere else (no night, setup, log or last-said)',
    keysHoldingIt.length === 1 && keysHoldingIt[0] === THE_RUN_PASS && everythingStored.includes(KARTAAN_LAST_SAID));
  check('whatKartaanLastSaid answers a yes or no and words, never the pass',
    !JSON.stringify(await whatKartaanLastSaid(chrome)).includes(PASS));
}

/* ------------------------------------------------------------- the wiring */

check('the manifest lets the extension reach api.kartaan.com and nothing wider',
  MANIFEST.host_permissions.includes('https://api.kartaan.com/*'));
check('the worker hands a night the way to tell Kartaan, and starts the sync with a way to ask',
  WORKER.includes('tellKartaan:') && WORKER.split('fetch: kartaanFetch').length - 1 >= 4);
check('kartaan.js opens no connection of its own: it is handed one',
  !/\bglobalThis\.fetch\b|[^.\w]fetch\(/.test(readFileSync(new URL('kartaan.js', HERE), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '')));

/* ----------------------- a redirect never carries the pass; Kartaan's no never re-arms the re-check */

{
  const { chrome } = installFakeChrome();
  await withAPass(chrome);
  const server = aServerThat({ body: { fetch: true, said: 'ok' } });
  await askMayFetch(chrome, server.fetch, { at: NOW });
  check('the ask refuses redirects (redirect: error), so the pass cannot be carried elsewhere',
    server.calls[0].init.redirect === 'error');
  const redirected = await askMayFetch(chrome, async (address, init) => {
    if (init.redirect === 'error') throw new TypeError('Failed to fetch: redirect');
    return { status: 302, json: async () => ({ fetch: true, said: 'followed' }) };
  }, { at: NOW });
  check('a redirect is the could-not-reach words and no go', redirected.go === false && redirected.kind === 'unreachable' && /could not be reached/i.test(redirected.said));
  const KSRC = readFileSync(new URL('kartaan.js', HERE), 'utf8');
  const refusesRedirects = (text) => /credentials: 'omit',[\s\S]*?redirect: 'error'/.test(text);
  check('kartaan.js sets redirect: error on the ask', refusesRedirects(KSRC));
  check('PROOF: with redirect: error removed from kartaan.js that check goes red',
    !refusesRedirects(KSRC.replace("redirect: 'error'", "redirect: 'follow'")));
  const recheck = (text) => {
    const at = text.indexOf('onRecheck: async');
    const block = text.slice(at, text.indexOf('onDue:', at));
    return /if \(!said\.kartaanSaid\)\s*await chrome\.alarms\.create\(RECHECK_ALARM/.test(block)
      && /said\.wrong/.test(block);
  };
  check('the hourly re-check does not re-arm its alarm when Kartaan said no (worker.js)', recheck(WORKER));
  check('PROOF: with the guard removed from worker.js that check goes red',
    !recheck(WORKER.replace('if (!said.kartaanSaid) await', 'await')));
}

const EXPECTED = 121;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
