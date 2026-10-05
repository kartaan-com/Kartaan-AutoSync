/* Putting one fetched file into the seller's own Google Drive, from the browser.
 *
 * **WHY THIS EXISTS AT ALL, WHEN `autosync/drive.py` ALREADY DOES IT.** The
 * Python runs on a schedule in the seller's own GitHub Actions. The bytes of a
 * Meesho or Flipkart report exist only inside the seller's Chrome, because that
 * is the only place that can reach the portal at all. They cannot be handed to
 * the Python, so this half has to put them away itself.
 *
 * **SO THIS IS A SECOND DESCRIPTION OF ONE SET OF RULES, AND THAT IS THE COST
 * D107 NAMED WHEN IT MOVED THE WALK.** It is paid deliberately here rather than
 * arrived at: every name below is the Python's name, spelt the Python's way, so
 * the two can be read side by side by a person and seen to agree. `folder_at`
 * is `folderAt`, `what_to_do_about` is `whatToDoAbout`, and nothing is renamed
 * on the way across. **A rule that DIFFERS between the two is a bug in one of
 * them; a rule that is SPELT differently is a bug nobody will ever find.**
 *
 * **AND WHAT IT DELIBERATELY DOES NOT DO: it does not hold a credential.**
 * Exactly as the Python door says of itself. It asks Chrome for a token when it
 * needs one and hands it straight to Google. Where the seller's permission comes
 * from is `chrome.identity`, which is Chrome's own store and not ours -- so
 * there is no secret in this file, nothing to leak, and nothing that a copy of
 * this repository sitting in a seller's own GitHub account carries with it
 * (Golden Rule 8).
 *
 * **THE UPLOAD SHAPE IS THE REFERENCE'S, TAKEN AS IT STANDS (D198).** It has put
 * files into this same Drive nightly for months: ask for a session, then send
 * the body to the address that comes back; keep the token with an expiry; and
 * treat 401 as "the token has gone stale, throw it away and let the next run
 * have another go" rather than as a failure of the report.
 *
 * Everything here takes `chrome` and a way of asking as something handed in, so
 * all of it can be checked with no browser, no extension, no Google account and
 * no internet.
 */

import { theRecordWith } from './record.js';
import { theSpreadsheetInside } from './unzip.js';

/* The one scope this asks for. **`drive.file` and nothing wider**: it reaches
 * only files this extension itself created, so a seller granting it is not
 * handing over the rest of their Drive. The same scope the Python asks for, and
 * the two must never drift apart. */
export const SCOPE = 'https://www.googleapis.com/auth/drive.file';

/* Google's own cut-off between the two ways of uploading, in bytes. **A file
 * exactly on it is "5 MB or less" and goes the first way** -- the boundary is
 * Google's, not ours. */
export const SMALL_ENOUGH_FOR_ONE_REQUEST = 5 * 1024 * 1024;

export const MULTIPART = 'multipart';
export const RESUMABLE = 'resumable';

/* What Drive calls a folder. */
export const FOLDER = 'application/vnd.google-apps.folder';

/* Where Drive is asked about files, and where files are sent. Two addresses,
 * because Google has two. */
export const FILES = 'https://www.googleapis.com/drive/v3/files';
export const UPLOAD = 'https://www.googleapis.com/upload/drive/v3/files';

/* What separates the two parts of a multipart upload. Ours, so nothing can
 * collide with it by accident. */
const BOUNDARY = 'kartaan-autosync-boundary';

/* What our files are. The Python's table, copied rather than reasoned about. */
export const BY_EXTENSION = {
  csv: 'text/csv',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  xls: 'application/vnd.ms-excel',
  zip: 'application/zip',
  json: 'application/json',
  txt: 'text/plain',
};

/* What a token is called where it is kept, how long one lasts, and how long
 * before the end we stop trusting it.
 *
 * **THE MARGIN IS NOT DECORATION.** A token used in the last moments of its life
 * expires between being read and being answered, and what that produces is a 401
 * in the middle of an upload rather than a clean refusal before one. The
 * reference keeps the same five minutes. */
export const THE_TOKEN = 'kartaan-autosync-drive-token';
export const A_TOKEN_LASTS_MS = 60 * 60 * 1000;
export const STOP_TRUSTING_IT_MS = 5 * 60 * 1000;

/** Drive refused, and it says what it said.
 *
 *  **ITS OWN KIND, the same as the Python's.** "The file could not be put
 *  anywhere" and "the seller has run out of Drive" need different things doing
 *  about them, and one message for both is how a month of failures reads as one
 *  problem.
 */
export class DriveSaidNo extends Error {}

/** The seller's Drive has not been connected, or the permission has been taken
 *  back.
 *
 *  **ITS OWN KIND, BECAUSE IT IS NOBODY'S REPORT'S FAULT AND EVERY REPORT AFTER
 *  IT HITS THE SAME WALL.** Exactly the shape of `NeedsSigningIn` in the walk,
 *  and for exactly the same reason: calling each of them broken buries the one
 *  thing that actually needs doing, and the reference's queue died on the spot.
 */
export class DriveIsNotConnected extends Error {}

/** What one file is, by its name. **Unknown is unknown, not guessed** -- Drive
 *  will take a file it is told nothing about, and a spreadsheet labelled as a
 *  text file opens as nonsense in front of the seller. */
export function kindOf(fileName) {
  const after = String(fileName || '').split('.').pop().toLowerCase();
  return BY_EXTENSION[after] || 'application/octet-stream';
}

/** Which of Drive's two ways a file of this size goes. */
export function howToUpload(size) {
  return Number(size) <= SMALL_ENOUGH_FOR_ONE_REQUEST ? MULTIPART : RESUMABLE;
}

/** What Drive is told about the file. The parent is given as a list because
 *  Drive takes a list -- a file can sit in more than one place. Ours never does,
 *  and saying so once here is better than every caller remembering. */
export function theMetadata(landing) {
  return { name: landing.fileName, parents: [landing.folderId] };
}

/**
 * What is wrong with putting this file there, in words, or nothing.
 *
 * **ASKED BEFORE ANYTHING IS SENT.** A folder id that is empty, or a file with
 * nothing in it, is a fault here -- and the reference uploaded into a folder
 * whose id was the literal word PLACEHOLDER for weeks, reporting success every
 * night.
 */
export function whyItCannotBePut(folderId, fileName, body) {
  if (!folderId) return 'There is nowhere to put it: no folder was given.';
  if (!fileName) return 'There is nothing to call it: no file name was given.';
  if (body === null || body === undefined) {
    return `${fileName}: there is nothing to put -- no file came back.`;
  }
  if (!body.length) {
    return `${fileName}: the file has nothing in it, so it has not been put anywhere. `
      + 'An empty file counted as arrived would stop its day ever being fetched again.';
  }
  return null;
}

/**
 * One of three words: put it, replace it, or somebody has to look.
 *
 * **A SECOND COPY IS THE FAULT THIS EXISTS TO PREVENT.** The reference put three
 * wrongly-dated duplicates into a seller's Drive, and a folder with two files
 * for one day is a folder where nobody can say which one the numbers came from.
 *
 * So a name already there is REPLACED rather than added beside -- the day is the
 * same day, and the newer fetch is the one that was asked for. **More than one
 * already there is not something to tidy up silently**: replacing one leaves the
 * others, and deleting the rest is a decision nothing here is entitled to make.
 */
export function whatToDoAbout(fileName, alreadyThere) {
  const same = (alreadyThere || []).filter((one) => one && one.name === fileName);
  if (!same.length) return 'put';
  if (same.length > 1) return 'somebody has to look';
  return 'replace';
}

/**
 * The running list, with this day's row in it once.
 *
 * **PURE, AND THAT IS DELIBERATE.** Everything that can be got wrong about
 * adding a row -- losing the header, writing the same day twice, silently
 * changing what the columns mean -- is decided here, where it can be driven with
 * no Drive, no token and no network.
 *
 * **A DAY ALREADY IN THE FILE IS REPLACED WHERE IT STANDS, NOT ADDED BELOW.**
 * That is the same rule `whatToDoAbout` applies to whole files, and it is his
 * instruction in his own words: *"if the same report for the same date is
 * downloaded and placed again, it'll blow up the data."* Replaced in place rather
 * than moved to the end, so a file a person has scrolled through does not shuffle
 * itself every night.
 *
 * **AND A HEADER THAT NO LONGER MATCHES IS A REFUSAL, NOT A REWRITE.** If the
 * columns have changed, every row already in the file means something different
 * from every row about to be added -- and a file whose older half and newer half
 * mean different things, with nothing saying where the join is, is worse than two
 * files. Somebody has to look.
 */
export function theListWith(existing, header, row, forTheDay) {
  const clean = String(existing ?? '').split('\r\n').join('\n').replace(/\s+$/, '');
  if (!clean) return `${header}\n${row}`;
  const lines = clean.split('\n');
  if (lines[0].trim() !== String(header).trim()) {
    throw new Error(
      `The list already there begins "${lines[0].slice(0, 60)}" and this run writes `
      + `"${header}". The columns have changed, so nothing has been added: the rows already `
      + 'in it would mean something different from the rows about to go in.'
    );
  }
  const firstColumn = (one) => String(one).split(',')[0].trim();
  const at = lines.findIndex((one, i) => i > 0 && firstColumn(one) === String(forTheDay));
  if (at > 0) {
    lines[at] = row;
    return lines.join('\n');
  }
  return `${lines.join('\n')}\n${row}`;
}

/**
 * Which days a running list already holds, read out of its own first column.
 *
 * **THE DAY BOARD'S WHOLE IDEA OF THIS SHAPE RESTS ON THIS.** A running list has
 * no day in its name, so `landing.Arrived.days_inside` is filled from here -- one
 * place reads those days, exactly as one place writes them.
 *
 * **AND ONLY A REAL DAY COUNTS.** A half-written line, a stray blank, or a note
 * somebody typed into the file by hand is not a day that arrived, and counting
 * one would stop that day ever being fetched again.
 */
export function theDaysInTheList(existing) {
  const clean = String(existing ?? '').split('\r\n').join('\n').trim();
  if (!clean) return [];
  return clean.split('\n').slice(1)
    .map((one) => String(one).split(',')[0].trim())
    .filter((one) => /^\d{4}-\d{2}-\d{2}$/.test(one));
}

/* ---------------------------------------------------- asking Chrome for a token */

/**
 * A token for the seller's own Drive, from Chrome's own store.
 *
 * **NOTHING HERE HOLDS A CREDENTIAL, AND THAT IS THE POINT (Golden Rule 8).**
 * Chrome keeps the seller's permission; this asks for a token when it needs one
 * and hands it straight to Google. This repository is copied into every seller's
 * own GitHub account, so a file that held a secret would copy it into all of
 * them.
 *
 * **KEPT WITH AN EXPIRY, AND STOPPED BEING TRUSTED FIVE MINUTES EARLY.** A token
 * used in the last moments of its life expires between being read and being
 * answered, and what that produces is a 401 in the middle of an upload rather
 * than a clean refusal before one.
 *
 * **AND `interactive` IS FALSE FOR A RUN NOBODY IS WATCHING.** Asked
 * interactively at two in the morning, Chrome puts up a window asking the seller
 * to choose an account and waits for ever -- the same silent unattended hang as
 * the Save-as window, arriving by a different door. So the nightly run asks
 * quietly and, if there is nothing to be had quietly, says the Drive is not
 * connected and stops. Connecting it is something somebody does once, awake.
 */
export async function aDriveToken(chrome, { interactive = false, now = () => Date.now() } = {}) {
  const held = await chrome.storage.local.get(THE_TOKEN);
  const kept = held[THE_TOKEN];
  if (kept && kept.token && now() < Number(kept.until) - STOP_TRUSTING_IT_MS) {
    return kept.token;
  }
  if (!chrome.identity || typeof chrome.identity.getAuthToken !== 'function') {
    /* **SAID AS WHAT IT IS.** Without the `identity` permission and an OAuth
     * client of our own there is no way to ask at all, and reporting that as
     * "Drive refused" would send somebody to look at Google. */
    throw new DriveIsNotConnected(
      'This extension cannot ask for permission to the seller\'s Drive: it has no identity '
      + 'permission and no OAuth client of its own yet.'
    );
  }
  const token = await new Promise((answer, refuse) => {
    chrome.identity.getAuthToken({ interactive, scopes: [SCOPE] }, (got) => {
      const wrong = chrome.runtime && chrome.runtime.lastError;
      if (wrong || !got) {
        refuse(new DriveIsNotConnected(
          `The seller's Drive is not connected: ${(wrong && wrong.message) || 'Chrome gave no token'}.`
        ));
        return;
      }
      answer(got);
    });
  });
  await chrome.storage.local.set({
    [THE_TOKEN]: { token, until: now() + A_TOKEN_LASTS_MS },
  });
  return token;
}

/**
 * Throw the token away, here and in Chrome's own store.
 *
 * **BOTH, OR IT COMES STRAIGHT BACK.** Chrome caches the token itself and will
 * hand the same dead one over again; forgetting it only here would loop for ever
 * on a token Google has already refused.
 */
export async function forgetTheToken(chrome) {
  const held = await chrome.storage.local.get(THE_TOKEN);
  const kept = held[THE_TOKEN];
  if (kept && kept.token && chrome.identity
      && typeof chrome.identity.removeCachedAuthToken === 'function') {
    await new Promise((done) => chrome.identity.removeCachedAuthToken({ token: kept.token }, done));
  }
  await chrome.storage.local.remove(THE_TOKEN);
}

/* ------------------------------------------------------------- talking to Drive */

/** What came back, or a refusal naming what was being done.
 *
 *  **A STALE PERMISSION IS NOT A FAILED REPORT.** 401 means throw the token away
 *  and let the next run have another go; calling it a broken report would bury a
 *  day's data behind a problem that fixes itself.
 */
async function answered(chrome, reply, doing) {
  if (!reply) throw new DriveSaidNo(`${doing}: Drive said nothing at all.`);
  if (reply.status === 401) {
    await forgetTheToken(chrome);
    throw new DriveIsNotConnected(
      `${doing}: the Drive permission has gone stale. It has been thrown away, and the next `
      + 'run will ask for a fresh one.'
    );
  }
  if (!reply.ok) {
    const said = typeof reply.text === 'function' ? await reply.text() : '';
    throw new DriveSaidNo(`${doing}: Drive said ${reply.status}. ${String(said).slice(0, 200)}`);
  }
  return reply;
}

/* **1000 IS DRIVE'S DOCUMENTED MAXIMUM** for files.list, and asking for the most
 * it will give means the fewest requests for a folder of eight hundred files.
 *
 * **ASKED FOR EXPLICITLY RATHER THAN LEFT TO THE DEFAULT**, because the default
 * is not one number: Drive's own reference says 100 for a shared drive and "the
 * entire list" otherwise. A page size that depends on which kind of Drive the
 * seller happens to have is a page size nobody can reason about. */
const A_PAGEFUL = 1000;

/* 1000 a page, so this is a million files in one folder -- far past anything
 * real, and there only so that a page token that never advances cannot spin for
 * ever. */
const TOO_MANY_PAGES = 200;

/** Every file matching, through every page there is.
 *
 *  **THROUGH THE PAGER, NEVER ONE REQUEST.** Asked once, a second folder of the
 *  same name sitting on a later page reads as "there is exactly one" -- which
 *  puts tonight's file somewhere different from last night's, silently. That is
 *  the fault the refusal in `oneFolder` exists to prevent, and asking once would
 *  walk straight past it.
 */
async function everyFile(chrome, ask, looking, doing) {
  const all = [];
  let page = '';
  for (let round = 0; round < TOO_MANY_PAGES; round += 1) {
    const address = `${FILES}?q=${encodeURIComponent(looking)}`
      + `&fields=${encodeURIComponent('nextPageToken,files(id,name,size)')}`
      + `&pageSize=${A_PAGEFUL}${page ? `&pageToken=${encodeURIComponent(page)}` : ''}`;
    // eslint-disable-next-line no-await-in-loop
    const reply = await answered(chrome, await ask({ address, how: 'GET' }), doing);
    // eslint-disable-next-line no-await-in-loop
    const said = await reply.json();
    for (const one of (said.files || [])) all.push(one);
    page = said.nextPageToken || '';
    if (!page) return all;
  }
  throw new DriveSaidNo(`${doing}: Drive kept offering more pages and never finished.`);
}

/**
 * A value put inside a Drive search, quoted the way Drive says to quote one.
 *
 * **A DRIVE SEARCH IS A LANGUAGE, AND EVERY NAME BELOW WAS DROPPED INTO IT
 * WHOLE.** `name = '${name}'` closes its own quote the moment `name` holds one,
 * and what follows is read as more of the search rather than as part of the
 * name. Drive's own documentation is explicit about the fix: a value goes in
 * single quotes, a single quote inside it is written `\'`, and a backslash is
 * written `\\`. That is the whole rule, and it is written here once so that
 * every search below is built the same way.
 *
 * **NOTHING HERE HAS EVER HELD A QUOTE.** Report ids are `me_orders` and
 * `fk_payments`, and `background.js` now refuses anything that is not that
 * shape before a name gets this far. This is the second lock, on a door where
 * one lock is one mistake away from none -- the ids come out of a recipe file
 * that is generated, and generated data is data.
 *
 * **AND `autosync/drive_door.py` DOES THE SAME, SPELT THE SAME.** This file's
 * own header: a rule that DIFFERS between the two halves is a bug in one of
 * them; a rule that is SPELT differently is a bug nobody will ever find.
 */
export function asAQuotedValue(value) {
  return String(value ?? '').split('\\').join('\\\\').split("'").join("\\'");
}

/**
 * The id of one folder inside another, made only if it is not there yet.
 *
 * **FOUND BY NAME, MADE ONLY IF MISSING.** A folder made every night is a Drive
 * with thirty folders of one name and the files spread across them -- and
 * nothing that reads them would ever say so.
 *
 * **AND TWO OF THE SAME NAME IS NOT SOMETHING TO CHOOSE BETWEEN.** Picking one
 * would put tonight's file in a different folder from last night's, silently.
 * The same refusal, in the same words, as `autosync/drive_door.py`.
 *
 * **THE ONLY PLACE IN THIS HALF A FOLDER IS EVER MADE, AND IT REFUSES A NAME HIS
 * LAYOUT DOES NOT HAVE.** *"No other separate folders or files should be
 * created."* The layout is `autosync/layout.py`'s, handed across in `recipes.json`.
 */
async function oneFolder(chrome, ask, layout, name, inside) {
  if (!inside) {
    throw new DriveSaidNo('There is nowhere to make it: no Kartaan folder was given.');
  }
  if (!theNamesInTheLayout(layout).has(name)) {
    throw new DriveSaidNo(
      `${name} is not a folder in his layout, so it has not been made. A new stream's `
      + 'folder is added to autosync/layout.py first.'
    );
  }
  const looking = `name = '${asAQuotedValue(name)}' and mimeType = '${FOLDER}' `
    + `and '${asAQuotedValue(inside)}' in parents and trashed = false`;
  const found = await everyFile(chrome, ask, looking, `looking for the ${name} folder`);
  if (found.length > 1) {
    throw new DriveSaidNo(
      `There are ${found.length} folders called ${name} in the seller's Drive. Which one `
      + "tonight's file belongs in cannot be known, so nothing has been put."
    );
  }
  if (found.length) return found[0].id;
  const made = await answered(chrome, await ask({
    address: `${FILES}?fields=id`,
    how: 'POST',
    kind: 'application/json',
    body: JSON.stringify({ name, mimeType: FOLDER, parents: [inside] }),
  }), `making the ${name} folder`);
  return (await made.json()).id;
}

/** Every folder name his layout allows, from the list `recipes.json` carries. */
function theNamesInTheLayout(layout) {
  const names = new Set(['Reports', 'System', 'Logs']);
  if (layout && layout.kartaan) names.add(layout.kartaan);
  for (const path of Object.values((layout && layout.folders) || {})) {
    for (const one of path) names.add(one);
  }
  return names;
}

/** The folders that hold one report's files, from the top of `Kartaan /` down. */
export function thePathFor(layout, reportId) {
  const path = layout && layout.folders && Object.hasOwn(layout.folders, reportId)
    ? layout.folders[reportId] : null;
  if (!path || !path.length) {
    throw new DriveSaidNo(
      `${reportId} has no folder in his layout, so nothing has been put. A new stream gets its `
      + 'own folder in autosync/layout.py.'
    );
  }
  return path;
}

/** The id of the folder at the end of a path, each step found or made. The same
 *  one folder-finder as `autosync/drive_door.py`'s `folder_at`. */
export async function folderAt(chrome, ask, layout, path, inside) {
  let here = inside;
  for (const name of path) {
    // eslint-disable-next-line no-await-in-loop
    here = await oneFolder(chrome, ask, layout, name, here);
  }
  return here;
}

/** What is already in a folder, so that a second copy of one day can be
 *  refused rather than added beside the first. */
export async function whatIsAlreadyThere(chrome, ask, folderId) {
  return everyFile(
    chrome, ask,
    `'${asAQuotedValue(folderId)}' in parents and trashed = false`,
    'looking at what is already in the folder'
  );
}

/* ------------------------------------------------------------- the two ways up */

/**
 * Put one file into Drive, whichever of Google's two ways its size calls for.
 *
 * **THE SIZE PICKS THE WAY, AND THE BOUNDARY IS GOOGLE'S.** Five megabytes or
 * less goes up in one request; anything larger asks for a session first and then
 * sends the body to the address that comes back. The reference uses the second
 * way for everything, which is safe but is two requests for a file that needs
 * one -- and the Python here already picks between them, so this picks the same
 * way for the same reason.
 */
export async function putTheFile(chrome, ask, landing, body) {
  const wrong = whyItCannotBePut(landing.folderId, landing.fileName, body);
  if (wrong) throw new DriveSaidNo(wrong);
  return landing.by === RESUMABLE
    ? inTwoRequests(chrome, ask, landing, body)
    : inOneRequest(chrome, ask, landing, body);
}

/** Small enough to go up whole: what it is and what it holds, in one request. */
async function inOneRequest(chrome, ask, landing, body) {
  const opening = `--${BOUNDARY}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n`
    + `${JSON.stringify(theMetadata(landing))}\r\n`
    + `--${BOUNDARY}\r\nContent-Type: ${landing.kind}\r\n\r\n`;
  const closing = `\r\n--${BOUNDARY}--`;
  /* **THE BYTES ARE NOT TURNED INTO TEXT ON THE WAY.** A spreadsheet run through
   * a string is a spreadsheet Excel refuses to open, and it arrives with a real
   * size so everything downstream believes the day landed. */
  const parts = new Blob([opening, body, closing]);
  const reply = await ask({
    address: `${UPLOAD}?uploadType=multipart&fields=id,name,size`,
    how: 'POST',
    kind: `multipart/related; boundary=${BOUNDARY}`,
    body: parts,
  });
  return (await answered(chrome, reply, `putting ${landing.fileName} in`)).json();
}

/** Too big for one request: ask for a session, then send the body to it. */
async function inTwoRequests(chrome, ask, landing, body) {
  const opened = await answered(chrome, await ask({
    address: `${UPLOAD}?uploadType=resumable&fields=id,name,size`,
    how: 'POST',
    kind: 'application/json; charset=UTF-8',
    /* **WHAT IS COMING IS SAID UP FRONT.** Google asks for the kind and the
     * length here, and a session opened without them can be refused later, after
     * the whole file has already gone up. */
    headers: {
      'X-Upload-Content-Type': landing.kind,
      'X-Upload-Content-Length': String(body.length),
    },
    body: JSON.stringify(theMetadata(landing)),
  }), `asking Drive where to put ${landing.fileName}`);

  const where = opened.headers && opened.headers.get && opened.headers.get('Location');
  if (!where) {
    /* **NAMED RATHER THAN GUESSED AT.** Without the address there is nowhere to
     * send the body, and carrying on would send a seller's report into the
     * blue. */
    throw new DriveSaidNo(
      `asking Drive where to put ${landing.fileName}: it agreed but did not say where.`
    );
  }
  const reply = await ask({ address: where, how: 'PUT', kind: landing.kind, body });
  return (await answered(chrome, reply, `putting ${landing.fileName} in`)).json();
}

/**
 * Take one report's file all the way into the seller's own Drive.
 *
 * **THIS IS THE WHOLE HALF THE EXTENSION DID NOT HAVE**, and it is deliberately
 * the only thing outside this file that anybody has to call. It finds or makes
 * the report's own folder, refuses a second copy of a day it already has,
 * replaces a day it is being given again, and puts the bytes in.
 *
 * **IT ANSWERS WHAT THE WALK ANSWERS, IN THE SAME WORDS.** A report that reached
 * Drive and a report that reached the browser are the same report, and the
 * runner reads one list.
 */
export async function landTheFile(chrome, ask, { reportId, fileName, inside, body: given, layout }) {
  /* **A ZIP HOLDING ONE SPREADSHEET IS OPENED FOR REAL BEFORE IT LANDS -- HIS RULING,
   * 2026-09-16** (see `unzip.js`). Every file that reaches the Drive passes here. */
  const body = await theSpreadsheetInside(fileName, given);
  const folderId = await folderAt(chrome, ask, layout, thePathFor(layout, reportId), inside);
  const already = await whatIsAlreadyThere(chrome, ask, folderId);
  const doWhat = whatToDoAbout(fileName, already);
  if (doWhat === 'somebody has to look') {
    /* **NOT TIDIED UP SILENTLY.** Replacing one of them leaves the others, and
     * deleting the rest is a decision nothing here is entitled to make. */
    throw new DriveSaidNo(
      `There is already more than one ${fileName} in the ${reportId} folder. `
      + 'Which of them tonight\'s file should replace cannot be known, so nothing has been put.'
    );
  }
  const landing = {
    folderId,
    fileName,
    kind: kindOf(fileName),
    size: body ? body.length : 0,
    by: howToUpload(body ? body.length : 0),
  };
  /* **JOB 6: EVERY NAME ALREADY IN THE FOLDER, HANDED BACK WITH THE ANSWER.**
   * `whatIsAlreadyThere` was already asked, for the put-or-replace decision
   * above -- so this costs nothing extra. `background.js` reads the days out
   * of these names to seed `daysNobodyTried`'s record of what has really
   * landed, which is how a hole BEHIND a later landed day (F14: 09-20 landed
   * after 09-17..09-19 went missing) is ever found at all. A day this browser
   * only ever tracked by its own high-water mark could never see that. */
  if (doWhat === 'replace') {
    /* **REPLACED, NOT ADDED BESIDE.** The day is the same day and the newer
     * fetch is the one that was asked for -- and two files for one day is a
     * folder where nobody can say which one the numbers came from. */
    const same = already.find((one) => one.name === fileName);
    const wrong = whyItCannotBePut(folderId, fileName, body);
    if (wrong) throw new DriveSaidNo(wrong);
    /* **THE BIGGER FILE STAYS -- HIS RULING, 2026-09-16.** *"auto sync should keep
     * the bigger one because that's what going to have more information."* A new
     * file smaller than the one already there is not put. */
    if (Number(same.size) > body.length) {
      return {
        id: same.id, name: same.name, size: String(same.size), keptTheBigger: true, alreadyThere: already,
      };
    }
    const reply = await ask({
      address: `${UPLOAD}/${same.id}?uploadType=media&fields=id,name,size`,
      how: 'PATCH',
      kind: landing.kind,
      body,
    });
    const landed = await (await answered(chrome, reply, `replacing ${fileName}`)).json();
    return { ...landed, alreadyThere: already };
  }
  const put = await putTheFile(chrome, ask, landing, body);
  return { ...put, alreadyThere: already };
}

/**
 * Add one day's row to a report's running list, and answer how big it now is.
 *
 * **THE OTHER HALF OF `landTheFile`, FOR THE REPORTS THAT ARE NOT A FILE
 * ANYWHERE.** Meesho sells no export of the day's views, so there is nothing to
 * fetch: the figure is read off the dashboard and written down here.
 *
 * **IT IS READ, MERGED AND WRITTEN BACK -- three round trips where a download is
 * one -- and that is the cost of the shape he chose.** It is stated rather than
 * hidden, because it is also why nothing else in this product works this way.
 */
export async function addARowTo(chrome, ask, { reportId, fileName, inside, header, row, forTheDay, layout }) {
  const folderId = await folderAt(chrome, ask, layout, thePathFor(layout, reportId), inside);
  const already = await whatIsAlreadyThere(chrome, ask, folderId);
  const doWhat = whatToDoAbout(fileName, already);
  if (doWhat === 'somebody has to look') {
    /* **THE SAME REFUSAL A WHOLE FILE GETS, and here it matters more.** Adding a
     * row to one of two lists leaves the other standing with a gap in it, and
     * nothing afterwards could say which of them the numbers came from. */
    throw new DriveSaidNo(
      `There is already more than one ${fileName} in the ${reportId} folder. `
      + 'Which of them this day should be added to cannot be known, so nothing has been added.'
    );
  }

  let standing = '';
  let sameId = null;
  if (doWhat === 'replace') {
    const same = already.find((one) => one.name === fileName);
    sameId = same.id;
    const got = await ask({ address: `${FILES}/${same.id}?alt=media` });
    standing = await (await answered(chrome, got, `reading ${fileName}`)).text();
  }

  /* **MERGED BEFORE ANYTHING IS SENT.** A refusal about the columns has to
   * happen while the file in Drive is still untouched. */
  const whole = theListWith(standing, header, row, forTheDay);
  const body = new TextEncoder().encode(whole);
  const wrong = whyItCannotBePut(folderId, fileName, body);
  if (wrong) throw new DriveSaidNo(wrong);

  if (sameId) {
    const reply = await ask({
      address: `${UPLOAD}/${sameId}?uploadType=media&fields=id,name,size`,
      how: 'PATCH',
      kind: kindOf(fileName),
      body,
    });
    await answered(chrome, reply, `adding ${forTheDay} to ${fileName}`);
    return { fileName, size: body.length, days: theDaysInTheList(whole) };
  }
  await putTheFile(chrome, ask, {
    folderId, fileName, kind: kindOf(fileName), size: body.length, by: howToUpload(body.length),
  }, body);
  return { fileName, size: body.length, days: theDaysInTheList(whole) };
}

/**
 * A way of asking Drive things, with the seller's own permission on every one.
 *
 * **THE TOKEN IS FETCHED PER REQUEST RATHER THAN HELD**, because this worker is
 * shut down after thirty seconds of quiet and anything held in a variable goes
 * with it. It is cached in storage with its expiry, so this is one read and not
 * one round trip to Google.
 */
export function aWayOfAsking(chrome, { fetch, interactive = false }) {
  return async ({ address, how = 'GET', kind = null, body = null, headers = {} }) => {
    const token = await aDriveToken(chrome, { interactive });
    const sending = { Authorization: `Bearer ${token}`, ...headers };
    if (kind) sending['Content-Type'] = kind;
    return fetch(address, { method: how, headers: sending, body });
  };
}

/**
 * Write what has just landed into this install's own record, `Kartaan / System / extension-manifest-<id>.json`.
 * `fileName` is `record.js` `theRecordNameFor` of the install's id.
 *
 * **READ, MERGED AND REPLACED IN PLACE -- BY THE ONLY WRITER THERE IS (job 38).** The run keeps its own
 * file beside it, so nothing here can race anything: two writers on one file lose a line whenever both
 * save at the same minute. A record that is there and cannot be read refuses and is left untouched, never
 * read as empty -- written over, that would say nothing has ever landed. Two files of the name refuse
 * too: which one holds the history cannot be known.
 */
export async function recordWhatLanded(chrome, ask, { layout, inside, lines, fileName }) {
  if (!lines || !lines.length) return { written: 0 };
  const folderId = await folderAt(chrome, ask, layout, ['System'], inside);
  const already = await whatIsAlreadyThere(chrome, ask, folderId);
  const mine = already.filter((one) => one && one.name === fileName);
  if (mine.length > 1) {
    throw new DriveSaidNo(
      `There are ${mine.length} copies of ${fileName} in the seller's Drive, so nothing `
      + 'has been added to either: which one holds what landed cannot be known.'
    );
  }
  let standing = '';
  if (mine.length === 1) {
    const got = await ask({ address: `${FILES}/${mine[0].id}?alt=media` });
    standing = await (await answered(chrome, got, `reading ${fileName}`)).text();
  }
  const whole = theRecordWith(standing, lines); // refuses a record that is there and cannot be read
  const body = new TextEncoder().encode(whole);
  if (mine.length === 1) {
    const reply = await ask({
      address: `${UPLOAD}/${mine[0].id}?uploadType=media&fields=id,name,size`,
      how: 'PATCH',
      kind: kindOf(fileName),
      body,
    });
    await answered(chrome, reply, `adding to ${fileName}`);
  } else {
    await putTheFile(chrome, ask, {
      folderId,
      fileName,
      kind: kindOf(fileName),
      size: body.length,
      by: howToUpload(body.length),
    }, body);
  }
  return { written: lines.length };
}

/** The seller's own `Kartaan` folder at the top of their Drive, made if it is not there yet.
 *
 *  **FOUND BY NAME, NEVER BY AN ID ANYBODY HAS TO KEEP.** Under `drive.file` this
 *  extension can only ever see what its own project made, so a name is all there
 *  is to look for -- and the daily run finds the same folder the same way.
 */
export async function theKartaanFolder(chrome, ask, layout) {
  return oneFolder(chrome, ask, layout, layout.kartaan, 'root');
}
