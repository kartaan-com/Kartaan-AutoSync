/* Checks for putting a file into the seller's own Drive.
 *
 * Run: node extension/drive.test.js
 *
 * **THE MOST IMPORTANT ONE IS THE SECOND COPY.** The reference put three
 * wrongly-dated duplicates into a seller's Drive, and a folder holding two files
 * for one day is a folder where nobody can say which one the numbers came from.
 * Everything about naming, replacing and refusing here exists for that.
 *
 * **AND THE ONE THAT WOULD BE WORST IF IT WERE WRONG: asking interactively.**
 * A nightly run that asks Chrome for permission the interactive way puts a
 * window in front of a sleeping seller and waits for ever -- the same silent
 * unattended hang as the Save-as window, arriving by a different door.
 *
 * **A STAND-IN DRIVE, DELIBERATELY AWKWARD.** It answers with real HTTP shapes,
 * it pages its answers rather than handing everything back at once, it can
 * refuse with a 401 the way a stale permission does, and it hands back a
 * `Location` header only when it feels like it. A stand-in kinder than the real
 * thing is this project's most expensive recurring fault.
 */

import { installFakeChrome } from '../test/fake-chrome.js';
import {
  A_TOKEN_LASTS_MS,
  DriveIsNotConnected,
  DriveSaidNo,
  FOLDER,
  MULTIPART,
  RESUMABLE,
  SCOPE,
  SMALL_ENOUGH_FOR_ONE_REQUEST,
  STOP_TRUSTING_IT_MS,
  THE_TOKEN,
  aDriveToken,
  aFolderFor,
  aWayOfAsking,
  forgetTheToken,
  folderFor,
  howToUpload,
  kindOf,
  landTheFile,
  putTheFile,
  theMetadata,
  whatIsAlreadyThere,
  theKartaanFolder,
  whatToDoAbout,
  whyItCannotBePut,
} from './drive.js';

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

async function said(fn) {
  try {
    await fn();
  } catch (wrong) {
    return (wrong && wrong.message) || String(wrong);
  }
  return '';
}

async function itsKind(fn) {
  try {
    await fn();
  } catch (wrong) {
    return wrong.constructor.name;
  }
  return 'nothing was thrown';
}

/* --------------------------------------------------------- a stand-in Drive */

/**
 * Something that answers like Drive does.
 *
 * `holds` is what is already in the seller's Drive, as {id, name, mimeType,
 * parents}. Everything asked of it is recorded, because WHAT WAS SENT is most of
 * what these checks are about.
 */
function aDrive({ holds = [], pageAt = 0, refuseWith = 0, noLocation = false } = {}) {
  const it = { asked: [], made: [], put: [], nextId: 1 };
  const reply = (status, body, headers = {}) => ({
    ok: status >= 200 && status < 300,
    status,
    headers: { get: (name) => headers[name] || null },
    async json() { return body; },
    async text() { return JSON.stringify(body); },
  });

  it.ask = async ({ address, how = 'GET', kind = null, body = null, headers = {} }) => {
    it.asked.push({ address, how, kind, headers, body });
    if (refuseWith) return reply(refuseWith, { error: { message: 'no' } });

    /* **THE TWO ADDRESSES OVERLAP AND THE ORDER MATTERS.** Google's upload
     * address is the files address with /upload in front of it, so anything
     * matching loosely on the second will swallow the first. Getting this wrong
     * in the stand-in made an upload look like a folder being created. */
    const uploading = address.includes('/upload/drive/v3/files');

    if (!uploading && how === 'GET' && address.includes('/drive/v3/files?')) {
      const q = decodeURIComponent((address.match(/[?&]q=([^&]*)/) || [])[1] || '');
      const wanted = (q.match(/name = '([^']*)'/) || [])[1];
      const inside = (q.match(/'([^']*)' in parents/) || [])[1];
      const wantsAFolder = q.includes(FOLDER);
      let found = holds.filter((one) => (one.parents || []).includes(inside));
      if (wanted) found = found.filter((one) => one.name === wanted);
      if (wantsAFolder) found = found.filter((one) => one.mimeType === FOLDER);
      /* **PAGED, because Drive pages.** A second folder of one name sitting on a
       * later page is exactly the case that reads as "there is exactly one" to
       * anything that asks only once. */
      const token = (address.match(/[&?]pageToken=([^&]*)/) || [])[1];
      if (pageAt && !token && found.length > pageAt) {
        return reply(200, { files: found.slice(0, pageAt).map(bare), nextPageToken: 'more' });
      }
      if (pageAt && token) return reply(200, { files: found.slice(pageAt).map(bare) });
      return reply(200, { files: found.map(bare) });
    }

    if (!uploading && how === 'POST' && address.includes('/drive/v3/files?')) {
      const asked = JSON.parse(body);
      const made = { id: `made-${it.nextId++}`, ...asked };
      it.made.push(made);
      holds.push(made);
      return reply(200, { id: made.id });
    }

    if (how === 'POST' && address.includes('uploadType=resumable')) {
      it.put.push({ address, how, kind, headers, body });
      return noLocation
        ? reply(200, {}, {})
        : reply(200, {}, { Location: 'https://upload.example.invalid/session-1' });
    }

    if (how === 'PUT' || how === 'PATCH'
        || (how === 'POST' && address.includes('uploadType=multipart'))) {
      it.put.push({ address, how, kind, body });
      const size = body && body.size !== undefined ? body.size : (body ? body.length : 0);
      return reply(200, { id: 'landed-1', name: 'whatever', size: String(size) });
    }

    return reply(404, { error: { message: 'the stand-in Drive does not know that request' } });
  };
  const bare = (one) => ({ id: one.id, name: one.name });
  return it;
}

/* ------------------------------------------------- the rules, mirrored from Python */

/* **EVERY NAME HERE IS THE PYTHON'S NAME.** `autosync/drive.py` decides the same
 * things for the GitHub Actions half, and the two are a second description of
 * one set of rules (D107). Spelt differently they would be a bug nobody finds. */

check('the one scope asked for is the narrow one, and nothing wider',
  SCOPE === 'https://www.googleapis.com/auth/drive.file');
check('a folder is named after the report itself, so nobody keeps a list of ids',
  aFolderFor('me_orders') === 'me_orders');
check('and a folder for no report at all is refused rather than named',
  (await said(async () => aFolderFor(''))).includes('has to be for some report'));

check('a spreadsheet is labelled as a spreadsheet',
  kindOf('me_catalog_2026-09-05.xlsx').includes('spreadsheetml'));
check('and a csv as a csv', kindOf('x.csv') === 'text/csv');
/* **UNKNOWN IS UNKNOWN, NOT GUESSED.** Drive takes a file it is told nothing
 * about, and a spreadsheet labelled as text opens as nonsense for the seller. */
check('and something nobody has a name for is said to be unknown, not guessed',
  kindOf('x.wat') === 'application/octet-stream');
check('and a file with no name at all does not fall over',
  kindOf('') === 'application/octet-stream');

/* **THE BOUNDARY IS GOOGLE'S, AND A FILE EXACTLY ON IT GOES THE FIRST WAY.** */
check('a small file goes up in one request', howToUpload(1024) === MULTIPART);
check('a file exactly on Google own boundary still goes in one request',
  howToUpload(SMALL_ENOUGH_FOR_ONE_REQUEST) === MULTIPART);
check('and one byte over it asks for a session first',
  howToUpload(SMALL_ENOUGH_FOR_ONE_REQUEST + 1) === RESUMABLE);

check('what Drive is told about a file carries its name and one parent',
  theMetadata({ fileName: 'a.csv', folderId: 'f1' }).name === 'a.csv'
  && theMetadata({ fileName: 'a.csv', folderId: 'f1' }).parents.join() === 'f1');

/* **ASKED BEFORE ANYTHING IS SENT.** The reference uploaded into a folder whose
 * id was the literal word PLACEHOLDER for weeks, reporting success every night. */
check('nowhere to put it is refused', whyItCannotBePut('', 'a.csv', new Uint8Array([1])) !== null);
check('nothing to call it is refused', whyItCannotBePut('f1', '', new Uint8Array([1])) !== null);
check('nothing to put is refused', whyItCannotBePut('f1', 'a.csv', null) !== null);
/* **PRESENCE IS NOT ARRIVAL.** A nought-byte file counted as arrived would stop
 * its day ever being fetched again. */
check('and a file with nothing in it is refused, saying why that matters',
  (whyItCannotBePut('f1', 'a.csv', new Uint8Array(0)) || '').includes('ever being fetched again'));
check('a real file is not refused',
  whyItCannotBePut('f1', 'a.csv', new Uint8Array([1, 2])) === null);

check('a name not there yet is put', whatToDoAbout('a.csv', []) === 'put');
/* **REPLACED, NOT ADDED BESIDE.** The day is the same day, and the newer fetch
 * is the one that was asked for. */
check('a name already there is replaced', whatToDoAbout('a.csv', [{ name: 'a.csv' }]) === 'replace');
/* **AND TWO ALREADY THERE IS NOT SOMETHING TO TIDY UP SILENTLY.** */
check('but two of one name is somebody having to look',
  whatToDoAbout('a.csv', [{ name: 'a.csv' }, { name: 'a.csv' }]) === 'somebody has to look');
check('and other files in the folder are none of its business',
  whatToDoAbout('a.csv', [{ name: 'b.csv' }]) === 'put');

/* ------------------------------------------------------ asking Chrome for a token */

{
  const browser = installFakeChrome();
  const token = await aDriveToken(browser.chrome, { now: () => 1000 });
  check('a token is asked of Chrome and comes back', token === 'token-1');
  /* **THE NIGHTLY RUN ASKS QUIETLY.** Asked the interactive way at two in the
   * morning, Chrome puts a window in front of a sleeping seller and waits for
   * ever -- the same silent hang as the Save-as window, by another door. */
  check('and it is asked in the way that cannot put a window in front of a sleeping seller',
    browser.askedForTokens()[0].interactive === false);
  check('and it is kept, with when it stops being good for',
    browser.stored()[THE_TOKEN].token === 'token-1'
    && browser.stored()[THE_TOKEN].until === 1000 + A_TOKEN_LASTS_MS);

  const again = await aDriveToken(browser.chrome, { now: () => 1000 });
  check('asking again does not go back to Chrome for a second one',
    again === 'token-1' && browser.askedForTokens().length === 1);

  /* **STOPPED BEING TRUSTED FIVE MINUTES EARLY.** A token used in the last
   * moments of its life expires between being read and being answered, and that
   * is a 401 in the middle of an upload rather than a clean refusal before. */
  const nearlyGone = 1000 + A_TOKEN_LASTS_MS - STOP_TRUSTING_IT_MS;
  const fresh = await aDriveToken(browser.chrome, { now: () => nearlyGone });
  check('a token in its last five minutes is replaced rather than used',
    fresh === 'token-2' && browser.askedForTokens().length === 2);
}

{
  /* **THE SELLER HAS NOT CONNECTED THEIR DRIVE, AND THAT IS ITS OWN KIND.** It
   * is nobody's report's fault and every report after it hits the same wall --
   * exactly the shape of being signed out of a portal. */
  const browser = installFakeChrome({ identityIsOn: false });
  check('with no way to ask at all, it says the Drive is not connected',
    (await itsKind(() => aDriveToken(browser.chrome))) === 'DriveIsNotConnected');
  check('and says so in words rather than blaming Google',
    (await said(() => aDriveToken(browser.chrome))).includes('no OAuth client of its own'));
}

{
  /* **CHROME REPORTS A REFUSAL BY SETTING lastError, NOT BY THROWING.** Code
   * that only catches exceptions sails straight past with no token. */
  const browser = installFakeChrome({ refuseTheToken: 'The user is not signed in.' });
  check('a refusal Chrome reports without throwing is still a refusal',
    (await itsKind(() => aDriveToken(browser.chrome))) === 'DriveIsNotConnected');
  check('and it carries what Chrome actually said',
    (await said(() => aDriveToken(browser.chrome))).includes('not signed in'));
}

{
  /* **FORGOTTEN IN BOTH PLACES, OR IT COMES STRAIGHT BACK.** Chrome caches the
   * token itself and hands the same dead one over again. */
  const browser = installFakeChrome();
  await aDriveToken(browser.chrome, { now: () => 0 });
  await forgetTheToken(browser.chrome);
  check('forgetting a token clears it from our own store',
    browser.stored()[THE_TOKEN] === undefined);
  check('and tells Chrome to forget it too, or the dead one comes straight back',
    browser.forgottenTokens().join() === 'token-1');
}

/* --------------------------------------------------------------- finding the folder */

{
  const browser = installFakeChrome();
  const drive = aDrive({
    holds: [{ id: 'f-me_orders', name: 'me_orders', mimeType: FOLDER, parents: ['kartaan'] }],
  });
  const id = await folderFor(browser.chrome, drive.ask, 'me_orders', 'kartaan');
  check('a folder already there is found by name rather than made again', id === 'f-me_orders');
  /* **MADE EVERY NIGHT WOULD BE THIRTY FOLDERS OF ONE NAME**, with the files
   * spread across them and nothing that reads them ever saying so. */
  check('and nothing was made', drive.made.length === 0);
}

{
  const browser = installFakeChrome();
  const drive = aDrive({ holds: [] });
  const id = await folderFor(browser.chrome, drive.ask, 'me_orders', 'kartaan');
  check('a folder that is not there yet is made', id === 'made-1');
  check('and it is made as a folder, inside the Kartaan folder, named after the report',
    drive.made[0].mimeType === FOLDER
    && drive.made[0].parents.join() === 'kartaan'
    && drive.made[0].name === 'me_orders');
}

{
  /* **TWO OF THE SAME NAME IS NOT SOMETHING TO CHOOSE BETWEEN.** Picking one
   * puts tonight's file somewhere different from last night's, silently. */
  const browser = installFakeChrome();
  const drive = aDrive({
    holds: [
      { id: 'a', name: 'me_orders', mimeType: FOLDER, parents: ['kartaan'] },
      { id: 'b', name: 'me_orders', mimeType: FOLDER, parents: ['kartaan'] },
    ],
  });
  const wrong = await said(() => folderFor(browser.chrome, drive.ask, 'me_orders', 'kartaan'));
  check('two folders of one name is a refusal, not a coin toss',
    wrong.includes('There are 2 folders called me_orders'));
  check('and it says plainly that nothing was put', wrong.includes('nothing has been put'));
}

{
  /* **AND THE SECOND ONE MIGHT BE ON THE NEXT PAGE.** Asked once, Drive would
   * have answered "there is exactly one" and the refusal above would never
   * fire -- which is the whole reason everything goes through the pager. */
  const browser = installFakeChrome();
  const drive = aDrive({
    pageAt: 1,
    holds: [
      { id: 'a', name: 'me_orders', mimeType: FOLDER, parents: ['kartaan'] },
      { id: 'b', name: 'me_orders', mimeType: FOLDER, parents: ['kartaan'] },
    ],
  });
  check('a second folder hiding on a later page is still found',
    (await said(() => folderFor(browser.chrome, drive.ask, 'me_orders', 'kartaan')))
      .includes('There are 2 folders'));
}

{
  const browser = installFakeChrome();
  const drive = aDrive();
  check('with no Kartaan folder to put it in, it refuses rather than making one loose',
    (await said(() => folderFor(browser.chrome, drive.ask, 'me_orders', '')))
      .includes('no Kartaan folder was given'));
  check('and nothing was asked of Drive at all', drive.asked.length === 0);
}

/* ------------------------------------------------------------------ the two ways up */

{
  const browser = installFakeChrome();
  const drive = aDrive();
  const body = new Uint8Array([1, 2, 3, 4, 5]);
  const landed = await putTheFile(browser.chrome, drive.ask, {
    folderId: 'f1', fileName: 'a.csv', kind: 'text/csv', size: 5, by: MULTIPART,
  }, body);
  check('a small file goes up in exactly one request', drive.put.length === 1);
  check('and it goes the multipart way, with our own boundary',
    drive.put[0].address.includes('uploadType=multipart')
    && drive.put[0].kind.includes('boundary=kartaan-autosync-boundary'));
  check('and Drive answers with what it made', landed.id === 'landed-1');
}

{
  const browser = installFakeChrome();
  const drive = aDrive();
  const big = new Uint8Array(10);
  await putTheFile(browser.chrome, drive.ask, {
    folderId: 'f1', fileName: 'big.xlsx', kind: 'text/csv', size: 10, by: RESUMABLE,
  }, big);
  check('a big file asks for a session and then sends the body', drive.put.length === 2);
  /* **WHAT IS COMING IS SAID UP FRONT.** A session opened without them can be
   * refused after the whole file has already gone up. */
  check('and the session is told what is coming and how much of it',
    drive.put[0].headers['X-Upload-Content-Length'] === '10'
    && drive.put[0].headers['X-Upload-Content-Type'] === 'text/csv');
  check('and the body goes to the address Drive gave back, not to the files address',
    drive.put[1].address === 'https://upload.example.invalid/session-1'
    && drive.put[1].how === 'PUT');
}

{
  /* **NAMED RATHER THAN GUESSED AT.** Without the address there is nowhere to
   * send the body, and carrying on would send a seller's report into the blue. */
  const browser = installFakeChrome();
  const drive = aDrive({ noLocation: true });
  check('a session Drive agrees to but does not say where is a refusal',
    (await said(() => putTheFile(browser.chrome, drive.ask, {
      folderId: 'f1', fileName: 'big.xlsx', kind: 'text/csv', size: 10, by: RESUMABLE,
    }, new Uint8Array(10)))).includes('did not say where'));
}

{
  const browser = installFakeChrome();
  const drive = aDrive();
  check('a file with nothing in it never reaches Drive at all',
    (await said(() => putTheFile(browser.chrome, drive.ask, {
      folderId: 'f1', fileName: 'a.csv', kind: 'text/csv', size: 0, by: MULTIPART,
    }, new Uint8Array(0)))).includes('nothing in it'));
  check('and nothing was sent', drive.put.length === 0);
}

/* ------------------------------------------------------ all the way in, end to end */

{
  const browser = installFakeChrome();
  const drive = aDrive({ holds: [] });
  const landed = await landTheFile(browser.chrome, drive.ask, {
    reportId: 'me_catalog',
    fileName: 'meesho_me_catalog_2026-09-05.xlsx',
    inside: 'kartaan',
    body: new Uint8Array([80, 75, 3, 4]),
  });
  check('a report with no folder yet gets one made and its file put in',
    landed.id === 'landed-1' && drive.made[0].name === 'me_catalog');
  check('and the file went up as a spreadsheet, not as unknown bytes',
    drive.put[0].kind.includes('multipart/related'));
}

{
  /* **THE SAME DAY AGAIN IS REPLACED, NOT ADDED BESIDE.** Three wrongly-dated
   * duplicates is what happened to the reference. */
  const browser = installFakeChrome();
  const drive = aDrive({
    holds: [
      { id: 'f1', name: 'me_catalog', mimeType: FOLDER, parents: ['kartaan'] },
      { id: 'old', name: 'a.csv', parents: ['f1'] },
    ],
  });
  await landTheFile(browser.chrome, drive.ask, {
    reportId: 'me_catalog', fileName: 'a.csv', inside: 'kartaan', body: new Uint8Array([1, 2]),
  });
  check('a day already there is replaced in place rather than added beside',
    drive.put.length === 1 && drive.put[0].how === 'PATCH');
  check('and it replaces that very file, by its own id',
    drive.put[0].address.includes('/old?'));
}

{
  /* **NOT TIDIED UP SILENTLY.** Replacing one leaves the others, and deleting
   * the rest is a decision nothing here is entitled to make. */
  const browser = installFakeChrome();
  const drive = aDrive({
    holds: [
      { id: 'f1', name: 'me_catalog', mimeType: FOLDER, parents: ['kartaan'] },
      { id: 'one', name: 'a.csv', parents: ['f1'] },
      { id: 'two', name: 'a.csv', parents: ['f1'] },
    ],
  });
  const wrong = await said(() => landTheFile(browser.chrome, drive.ask, {
    reportId: 'me_catalog', fileName: 'a.csv', inside: 'kartaan', body: new Uint8Array([1]),
  }));
  check('two copies of one day already there is somebody having to look',
    wrong.includes('more than one a.csv'));
  check('and nothing at all was sent', drive.put.length === 0);
}

/* ------------------------------------------------------------ what Drive says back */

{
  /* **A STALE PERMISSION IS NOT A FAILED REPORT.** Calling it one would bury a
   * day's data behind a problem that fixes itself on the next run. */
  const browser = installFakeChrome();
  await aDriveToken(browser.chrome, { now: () => 0 });
  const drive = aDrive({ refuseWith: 401 });
  const kind = await itsKind(() => whatIsAlreadyThere(browser.chrome, drive.ask, 'f1'));
  check('Drive saying the permission is stale is its own kind, not a broken report',
    kind === 'DriveIsNotConnected');
  check('and the stale token is thrown away so the next run asks for a fresh one',
    browser.stored()[THE_TOKEN] === undefined
    && browser.forgottenTokens().join() === 'token-1');
}

{
  const browser = installFakeChrome();
  const drive = aDrive({ refuseWith: 403 });
  check('Drive refusing for any other reason is a refusal that says what it said',
    (await itsKind(() => whatIsAlreadyThere(browser.chrome, drive.ask, 'f1'))) === 'DriveSaidNo');
  check('and it names what was being done at the time',
    (await said(() => whatIsAlreadyThere(browser.chrome, drive.ask, 'f1')))
      .includes('looking at what is already in the folder'));
}

/* ------------------------------------------------------ the seller own permission */

{
  /* **EVERY REQUEST CARRIES IT, and it is fetched per request rather than held**
   * -- this worker is shut down after thirty seconds of quiet and anything in a
   * variable goes with it. */
  const browser = installFakeChrome();
  const sent = [];
  const ask = aWayOfAsking(browser.chrome, {
    fetch: async (address, how) => { sent.push({ address, how }); return { ok: true, status: 200, async json() { return {}; } }; },
  });
  await ask({ address: 'https://x/', how: 'GET' });
  await ask({ address: 'https://y/', how: 'GET' });
  check('every request to Drive carries the seller own permission',
    sent.length === 2 && sent.every((one) => one.how.headers.Authorization === 'Bearer token-1'));
  check('and the permission was asked of Chrome once, not once per request',
    browser.askedForTokens().length === 1);
  check('and it was asked quietly, so a nightly run cannot hang on a window',
    browser.askedForTokens()[0].interactive === false);
}

{
  /* **ONE FOLDER FOUND BY NAME REPLACES THE REFERENCE'S TWENTY-SEVEN IDS
   * (D100).** It keeps one id per report in its own source, every one of them
   * created by hand and pasted in; here nobody keeps anything. */
  const browser = installFakeChrome();
  const drive = aDrive({ holds: [] });
  const id = await theKartaanFolder(browser.chrome, drive.ask);
  check('the Kartaan folder is made in the seller own Drive if it is not there',
    id === 'made-1' && drive.made[0].parents.join() === 'root');
  const again = await theKartaanFolder(browser.chrome, drive.ask);
  check('and found by name next time rather than made again',
    again === 'made-1' && drive.made.length === 1);
}

{
  const browser = installFakeChrome();
  const drive = aDrive({
    holds: [
      { id: 'a', name: 'Kartaan AutoSync', mimeType: FOLDER, parents: ['root'] },
      { id: 'b', name: 'Kartaan AutoSync', mimeType: FOLDER, parents: ['root'] },
    ],
  });
  check('and two of them is the same refusal as two report folders, not a coin toss',
    (await said(() => theKartaanFolder(browser.chrome, drive.ask))).includes('There are 2 folders'));
}

const EXPECTED = 65;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
