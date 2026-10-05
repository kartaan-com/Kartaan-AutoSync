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

import { readFileSync } from 'node:fs';
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
  asAQuotedValue,
  aWayOfAsking,
  forgetTheToken,
  folderAt,
  howToUpload,
  kindOf,
  landTheFile,
  putTheFile,
  recordWhatLanded,
  theMetadata,
  whatIsAlreadyThere,
  theKartaanFolder,
  thePathFor,
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

/* **HIS LAYOUT, FROM THE RECIPE FILE THE EXTENSION REALLY SHIPS** -- `autosync/layout.py`'s list. */
const THE_BOOK = JSON.parse(readFileSync(new URL('./recipes.json', import.meta.url), 'utf8'));
const LAYOUT = { kartaan: THE_BOOK.kartaan, folders: THE_BOOK.folders };

/* The three folders a report's file goes in, already in a stand-in Drive, under `parent`. */
const theFoldersFor = (reportId, parent = 'kartaan') => {
  const path = thePathFor(LAYOUT, reportId);
  return path.map((name, at) => ({
    id: at === path.length - 1 ? 'f1' : `step-${at}`,
    name,
    mimeType: FOLDER,
    parents: [at === 0 ? parent : `step-${at - 1}`],
  }));
};

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

    /* **A FILE READ BACK BY ITS ID, AND CONTENTS REPLACED IN PLACE** -- what `recordWhatLanded` does to the
     * extension's own record. The stand-in keeps each file's text so what was written can be read again. */
    const readingOne = !uploading && how === 'GET' && address.match(/\/drive\/v3\/files\/([^?/]+)\?alt=media/);
    if (readingOne) {
      const there = holds.find((one) => one.id === readingOne[1]);
      return { ok: true, status: 200, headers: { get: () => null }, async text() { return (there && there.contents) || ''; } };
    }
    const replacing = uploading && how === 'PATCH' && address.match(/\/upload\/drive\/v3\/files\/([^?/]+)/);
    if (replacing) {
      const there = holds.find((one) => one.id === replacing[1]);
      if (there) there.contents = new TextDecoder().decode(body);
      it.put.push({ address, how, kind, body });
      return reply(200, { id: replacing[1], name: there && there.name, size: String(body.length) });
    }

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
  /* The size comes back too, because `everyFile` asks Drive for it (A53, the bigger
   * file stays). */
  const bare = (one) => ({
    id: one.id, name: one.name, ...(one.size !== undefined ? { size: one.size } : {}),
  });
  return it;
}

/* ------------------------------------------------- the rules, mirrored from Python */

/* **EVERY NAME HERE IS THE PYTHON'S NAME.** `autosync/drive.py` decides the same
 * things for the GitHub Actions half, and the two are a second description of
 * one set of rules (D107). Spelt differently they would be a bug nobody finds. */

check('the one scope asked for is the narrow one, and nothing wider',
  SCOPE === 'https://www.googleapis.com/auth/drive.file');
check('the folder for a report comes from his layout, so nobody keeps a list of ids',
  thePathFor(LAYOUT, 'me_orders').join('/') === 'Reports/Meesho/Orders'
  && thePathFor(LAYOUT, 'fk_ads_fsn').join('/') === 'Reports/Flipkart/Ads/products');
check('the night log the extension writes goes with the logs of the run, so the sixty-day tidy reaches it',
  thePathFor(LAYOUT, 'run_log').join('/') === 'System/Logs');
check('a name that is only an object property is refused like any other unknown report',
  (await said(async () => thePathFor(LAYOUT, 'constructor'))).includes('no folder in his layout'));
check('and a report with no folder in it is refused rather than named',
  (await said(async () => thePathFor(LAYOUT, 'fk_keywords'))).includes('no folder in his layout'));

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
    holds: [{ id: 'f-orders', name: 'Orders', mimeType: FOLDER, parents: ['kartaan'] }],
  });
  const id = await folderAt(browser.chrome, drive.ask, LAYOUT, ['Orders'], 'kartaan');
  check('a folder already there is found by name rather than made again', id === 'f-orders');
  /* **MADE EVERY NIGHT WOULD BE THIRTY FOLDERS OF ONE NAME**, with the files
   * spread across them and nothing that reads them ever saying so. */
  check('and nothing was made', drive.made.length === 0);
}

{
  const browser = installFakeChrome();
  const drive = aDrive({ holds: [] });
  const id = await folderAt(browser.chrome, drive.ask, LAYOUT, ['Orders'], 'kartaan');
  check('a folder that is not there yet is made', id === 'made-1');
  check('and it is made as a folder, inside the Kartaan folder, named as his layout names it',
    drive.made[0].mimeType === FOLDER
    && drive.made[0].parents.join() === 'kartaan'
    && drive.made[0].name === 'Orders');
}

{
  /* **TWO OF THE SAME NAME IS NOT SOMETHING TO CHOOSE BETWEEN.** Picking one
   * puts tonight's file somewhere different from last night's, silently. */
  const browser = installFakeChrome();
  const drive = aDrive({
    holds: [
      { id: 'a', name: 'Orders', mimeType: FOLDER, parents: ['kartaan'] },
      { id: 'b', name: 'Orders', mimeType: FOLDER, parents: ['kartaan'] },
    ],
  });
  const wrong = await said(() => folderAt(browser.chrome, drive.ask, LAYOUT, ['Orders'], 'kartaan'));
  check('two folders of one name is a refusal, not a coin toss',
    wrong.includes('There are 2 folders called Orders'));
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
      { id: 'a', name: 'Orders', mimeType: FOLDER, parents: ['kartaan'] },
      { id: 'b', name: 'Orders', mimeType: FOLDER, parents: ['kartaan'] },
    ],
  });
  check('a second folder hiding on a later page is still found',
    (await said(() => folderAt(browser.chrome, drive.ask, LAYOUT, ['Orders'], 'kartaan')))
      .includes('There are 2 folders'));
}

{
  const browser = installFakeChrome();
  const drive = aDrive();
  check('with no Kartaan folder to put it in, it refuses rather than making one loose',
    (await said(() => folderAt(browser.chrome, drive.ask, LAYOUT, ['Orders'], '')))
      .includes('no Kartaan folder was given'));
  check('and nothing was asked of Drive at all', drive.asked.length === 0);
}

{
  /* ---------- A DRIVE SEARCH IS A LANGUAGE, NOT A SENTENCE (A33)
   *
   * **EVERY NAME WAS DROPPED INTO IT WHOLE.** `name = '${name}'` closes its own
   * quote the moment the name holds one, and what follows is read as more of
   * the search rather than as part of the name. Drive's own documentation says
   * how a value is written: single quotes round it, `\'` for a quote inside it,
   * `\\` for a backslash.
   *
   * **NOTHING HERE HAS EVER HELD A QUOTE, AND THAT IS THE POINT.** Report ids
   * come out of a generated recipe file, `background.js` now refuses anything
   * that is not `me_orders`-shaped before a name gets this far, and this is the
   * second lock on a door where one lock is one mistake away from none.
   * `autosync/drive_door.as_a_quoted_value` is the same rule, spelt the same. */
  const Q = String.fromCharCode(39);
  const B = String.fromCharCode(92);
  check('a quote inside a value is escaped rather than closing the search',
    asAQuotedValue(`me${Q}orders`) === `me${B}${Q}orders`);
  check('and a backslash is escaped too, so it cannot escape the escaping',
    asAQuotedValue(`me${B}orders`) === `me${B}${B}orders`);
  check('and an ordinary report id is left exactly as it is',
    asAQuotedValue('me_orders') === 'me_orders');
  check('and nothing at all comes back as nothing, never as the word undefined',
    asAQuotedValue(undefined) === '' && asAQuotedValue(null) === '');

  /* **DRIVEN THROUGH THE REAL SEARCH, never asserted about the helper alone.**
   * A helper that escapes perfectly and is not called is the shape of fault
   * this repository keeps finding. */
  const browser = installFakeChrome();
  const drive = aDrive({ holds: [] });
  /* A name with a quote in it is not in his layout, so it is lent to this one check. */
  const lent = { kartaan: 'Kartaan', folders: { a_check: [`me${Q}orders`] } };
  await folderAt(browser.chrome, drive.ask, lent, [`me${Q}orders`], `kar${Q}taan`);
  const sent = decodeURIComponent(drive.asked[0].address.split('q=')[1].split('&')[0]);
  check('the search Drive is really sent carries the escaped name',
    sent.includes(`name = 'me${B}${Q}orders'`));
  check('and the escaped parent as well', sent.includes(`'kar${B}${Q}taan' in parents`));
  check('and no bare quote is left in it to end a value early',
    !sent.includes(`me${Q}orders`) && !sent.includes(`kar${Q}taan`));
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
    layout: LAYOUT,
    body: new Uint8Array([80, 75, 3, 4]),
  });
  check('a report with no folder yet gets one made and its file put in',
    landed.id === 'landed-1'
    && drive.made.map((one) => one.name).join('/') === 'Reports/Meesho/Catalog');
  check('and the file went up as a spreadsheet, not as unknown bytes',
    drive.put[0].kind.includes('multipart/related'));
}

{
  /* **THE SAME DAY AGAIN IS REPLACED, NOT ADDED BESIDE.** Three wrongly-dated
   * duplicates is what happened to the reference. */
  const browser = installFakeChrome();
  const drive = aDrive({
    holds: [
      ...theFoldersFor('me_catalog'),
      { id: 'old', name: 'a.csv', parents: ['f1'] },
    ],
  });
  await landTheFile(browser.chrome, drive.ask, {
    reportId: 'me_catalog', fileName: 'a.csv', inside: 'kartaan', layout: LAYOUT, body: new Uint8Array([1, 2]),
  });
  check('a day already there is replaced in place rather than added beside',
    drive.put.length === 1 && drive.put[0].how === 'PATCH');
  check('and it replaces that very file, by its own id',
    drive.put[0].address.includes('/old?'));
}

{
  /* **A53: THE BIGGER FILE STAYS -- HIS RULING, 2026-09-16.** */
  const browser = installFakeChrome();
  const drive = aDrive({
    holds: [
      ...theFoldersFor('me_catalog'),
      { id: 'old', name: 'a.csv', size: '100', parents: ['f1'] },
    ],
  });
  const kept = await landTheFile(browser.chrome, drive.ask, {
    reportId: 'me_catalog', fileName: 'a.csv', inside: 'kartaan', layout: LAYOUT, body: new Uint8Array([1, 2]),
  });
  check('a smaller file does not replace a bigger one already in the Drive',
    drive.put.length === 0 && kept.keptTheBigger === true && kept.id === 'old');
}

{
  /* **A53: A ZIP HOLDING ONE SPREADSHEET LANDS AS THAT SPREADSHEET, OPENED -- HIS
   * RULING.** A zip with one entry stored uncompressed, built by hand. */
  const inner = new TextEncoder().encode('the payments sheet');
  const name = new TextEncoder().encode('payments.xlsx');
  const zip = new Uint8Array(30 + name.length + inner.length + 46 + name.length + 22);
  const v = new DataView(zip.buffer);
  v.setUint32(0, 0x04034b50, true);
  v.setUint32(18, inner.length, true);
  v.setUint32(22, inner.length, true);
  v.setUint16(26, name.length, true);
  zip.set(name, 30);
  zip.set(inner, 30 + name.length);
  const listAt = 30 + name.length + inner.length;
  v.setUint32(listAt, 0x02014b50, true);
  v.setUint32(listAt + 20, inner.length, true);
  v.setUint32(listAt + 24, inner.length, true);
  v.setUint16(listAt + 28, name.length, true);
  zip.set(name, listAt + 46);
  const endAt = listAt + 46 + name.length;
  v.setUint32(endAt, 0x06054b50, true);
  v.setUint16(endAt + 8, 1, true);
  v.setUint16(endAt + 10, 1, true);
  v.setUint32(endAt + 16, listAt, true);
  const browser = installFakeChrome();
  const drive = aDrive({ holds: [...theFoldersFor('me_payments')] });
  await landTheFile(browser.chrome, drive.ask, {
    reportId: 'me_payments', fileName: 'meesho_me_payments_2026-09-14.xlsx', inside: 'kartaan', layout: LAYOUT, body: zip,
  });
  /* The upload goes as a Blob (`drive.js` `inOneRequest`), so its text is read out. */
  const sent = drive.put.length ? await drive.put[0].body.text() : '';
  check('a zip holding one spreadsheet lands as the spreadsheet inside it, not the zip',
    drive.put.length === 1 && sent.includes('the payments sheet') && !sent.includes('payments.xlsx'));
}

{
  /* **NOT TIDIED UP SILENTLY.** Replacing one leaves the others, and deleting
   * the rest is a decision nothing here is entitled to make. */
  const browser = installFakeChrome();
  const drive = aDrive({
    holds: [
      ...theFoldersFor('me_catalog'),
      { id: 'one', name: 'a.csv', parents: ['f1'] },
      { id: 'two', name: 'a.csv', parents: ['f1'] },
    ],
  });
  const wrong = await said(() => landTheFile(browser.chrome, drive.ask, {
    reportId: 'me_catalog', fileName: 'a.csv', inside: 'kartaan', layout: LAYOUT, body: new Uint8Array([1]),
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
  const id = await theKartaanFolder(browser.chrome, drive.ask, LAYOUT);
  check('the Kartaan folder is made in the seller own Drive if it is not there',
    id === 'made-1' && drive.made[0].parents.join() === 'root');
  const again = await theKartaanFolder(browser.chrome, drive.ask, LAYOUT);
  check('and found by name next time rather than made again',
    again === 'made-1' && drive.made.length === 1);
}

{
  const browser = installFakeChrome();
  const drive = aDrive({
    holds: [
      { id: 'a', name: 'Kartaan', mimeType: FOLDER, parents: ['root'] },
      { id: 'b', name: 'Kartaan', mimeType: FOLDER, parents: ['root'] },
    ],
  });
  check('and two of them is the same refusal as two report folders, not a coin toss',
    (await said(() => theKartaanFolder(browser.chrome, drive.ask, LAYOUT))).includes('There are 2 folders'));
}

{
  /* **A FOLDER NOT IN HIS LAYOUT IS NEVER MADE, AND THE EXTENSION MAKES A FOLDER IN ONE PLACE ONLY.**
   * *"No other separate folders or files should be created."* */
  const browser = installFakeChrome();
  const drive = aDrive({ holds: [] });
  check('a folder his layout does not have is refused',
    (await said(() => folderAt(browser.chrome, drive.ask, LAYOUT, ['Kartaan data'], 'kartaan')))
      .includes('not a folder in his layout'));
  check('and nothing was asked of Drive at all', drive.asked.length === 0 && drive.made.length === 0);
  const source = readFileSync(new URL('./drive.js', import.meta.url), 'utf8').split(String.fromCharCode(10));
  const sites = source.filter((line) => /mimeType:\s*FOLDER/.test(line));
  check('and the extension makes a folder in exactly one place', sites.length === 1);
}

/* ------------------------------------------------------ the extension's own record (job 38) */

{
  const aLine = (day, report = 'me_orders', size = 400) => ({
    dataDate: day, reportId: report, state: 'verified', fileName: `x_${day}.csv`, fileSize: size, checkedOn: day,
  });
  const browser = installFakeChrome();
  const drive = aDrive({ holds: [] });
  const first = await recordWhatLanded(browser.chrome, drive.ask, {
    layout: LAYOUT, inside: 'kartaan', fileName: 'extension-manifest-0a1b2c3d.json', lines: [aLine('2026-09-20')],
  });
  check('the first landing makes System and puts the extension own record in it, saying how many lines',
    first.written === 1 && drive.made.map((one) => one.name).join() === 'System'
    && drive.made[0].parents.join() === 'kartaan' && drive.put.length === 1);
  check('and it made nothing outside his layout', drive.made.every((one) => one.name === 'System'));
}

{
  /* **A SECOND LANDING FINDS THE RECORD AND REPLACES IT IN PLACE, BY ITS ID, WITH BOTH DAYS IN IT.** */
  const aLine = (day, report = 'me_orders', size = 400) => ({
    dataDate: day, reportId: report, state: 'verified', fileName: `x_${day}.csv`, fileSize: size, checkedOn: day,
  });
  const browser = installFakeChrome();
  const system = { id: 'sys', name: 'System', mimeType: FOLDER, parents: ['kartaan'] };
  const record = { id: 'rec', name: 'extension-manifest-0a1b2c3d.json', parents: ['sys'], contents: '' };
  const drive = aDrive({ holds: [system, record] });
  await recordWhatLanded(browser.chrome, drive.ask, { layout: LAYOUT, inside: 'kartaan', fileName: 'extension-manifest-0a1b2c3d.json', lines: [aLine('2026-09-20')] });
  await recordWhatLanded(browser.chrome, drive.ask, { layout: LAYOUT, inside: 'kartaan', fileName: 'extension-manifest-0a1b2c3d.json', lines: [aLine('2026-09-21')] });
  const lines = JSON.parse(record.contents).lines;
  check('the second landing is added to the first in the same file, and both are there',
    lines.map((one) => one.dataDate).join() === '2026-09-20,2026-09-21');
  check('it was replaced in place by its id, and nothing was made',
    drive.made.length === 0 && drive.put.every((one) => one.how === 'PATCH' && one.address.includes('/rec')));
}

{
  /* **A RECORD THAT IS THERE AND CANNOT BE READ IS LEFT EXACTLY AS IT WAS.** */
  const browser = installFakeChrome();
  const system = { id: 'sys', name: 'System', mimeType: FOLDER, parents: ['kartaan'] };
  const broken = { id: 'rec', name: 'extension-manifest-0a1b2c3d.json', parents: ['sys'], contents: '{not a record' };
  const drive = aDrive({ holds: [system, broken] });
  const wrong = await said(() => recordWhatLanded(browser.chrome, drive.ask, {
    layout: LAYOUT, inside: 'kartaan', fileName: 'extension-manifest-0a1b2c3d.json',
    lines: [{ dataDate: '2026-09-20', reportId: 'me_orders', state: 'verified', fileName: 'x', fileSize: 1, checkedOn: '' }],
  }));
  check('a record that cannot be read refuses and says so', wrong.includes('cannot be read'));
  check('and what was in it is exactly as it was, nothing written over it',
    broken.contents === '{not a record' && drive.put.length === 0);
}

{
  const browser = installFakeChrome();
  const system = { id: 'sys', name: 'System', mimeType: FOLDER, parents: ['kartaan'] };
  const drive = aDrive({
    holds: [system,
      { id: 'one', name: 'extension-manifest-0a1b2c3d.json', parents: ['sys'], contents: '' },
      { id: 'two', name: 'extension-manifest-0a1b2c3d.json', parents: ['sys'], contents: '' }],
  });
  const wrong = await said(() => recordWhatLanded(browser.chrome, drive.ask, {
    layout: LAYOUT, inside: 'kartaan', fileName: 'extension-manifest-0a1b2c3d.json',
    lines: [{ dataDate: '2026-09-20', reportId: 'me_orders', state: 'verified', fileName: 'x', fileSize: 1, checkedOn: '' }],
  }));
  check('two records of the name refuse, naming how many, rather than choosing between them',
    wrong.includes('2 copies') && drive.put.length === 0);
}

{
  const browser = installFakeChrome();
  const drive = aDrive({ holds: [] });
  check('landing nothing writes nothing at all and asks Drive nothing',
    (await recordWhatLanded(browser.chrome, drive.ask, { layout: LAYOUT, inside: 'kartaan', fileName: 'extension-manifest-0a1b2c3d.json', lines: [] })).written === 0
    && drive.asked.length === 0);
}

{
  /* **TWO INSTALLS ON ONE GOOGLE ACCOUNT NEVER TOUCH EACH OTHER'S RECORD (Control, 2026-10-05).** */
  const browser = installFakeChrome();
  const system = { id: 'sys', name: 'System', mimeType: FOLDER, parents: ['kartaan'] };
  const first = { id: 'a', name: 'extension-manifest-0a1b2c3d.json', parents: ['sys'], contents: '{"shape":2,"reads":[],"lines":[]}' };
  const drive = aDrive({ holds: [system, first] });
  await recordWhatLanded(browser.chrome, drive.ask, {
    layout: LAYOUT, inside: 'kartaan', fileName: 'extension-manifest-ffeeddcc.json',
    lines: [{ dataDate: '2026-09-20', reportId: 'me_orders', state: 'verified', fileName: 'x', fileSize: 1, checkedOn: '' }],
  });
  check('a second install writes its own file and leaves the first install record exactly as it was',
    first.contents === '{"shape":2,"reads":[],"lines":[]}' && drive.put.length === 1 && !drive.put[0].address.includes('/a'));
}

const EXPECTED = 88;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  failures++;
}

reachedTheEnd = true;
console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
process.exit(failures ? 1 : 0);
