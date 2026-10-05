/* Flipkart's top search keywords, read off the traffic report (2026-09-15).
 *
 * **THE REFERENCE'S OWN READING, CARRIED ACROSS AS IT IS -- HIS RULING: "do the
 * same thing."** `D:/rumee-auto-sync/content/flipkart.js` `handleFkKeywords`: on the
 * Traffic Report with the day and all products chosen, every listing row carries a
 * `View top search keywords` button; pressed, a pop-up titled `Top 10 Searched
 * Keywords` holds a table of keyword, impression share and click share. Each row's
 * pop-up is opened, read and closed in turn, on every page of listings, and one CSV
 * is made of all of it -- there is no file to download.
 *
 * **THE ONLY PART A PERSON DID IN THE REFERENCE IS DONE BY THE RECIPE**: opening the
 * traffic report and choosing the day. Everything here is what ran by itself there.
 *
 * **TWO NARROWINGS, NOT CHANGES.** A page number is a button whose words are ONLY a
 * number (the reference read the leading number of any words), and the pop-up is
 * the smallest block holding both its title and a table (the reference took the
 * first block holding the title, which is only safe while the pop-up is drawn apart
 * from the listing table).
 */

export const THE_BUTTON = 'View top search keywords';
export const THE_POP_UP = 'Top 10 Searched Keywords';
export const THE_HEADER = 'Date,SKU,Keyword,Impression %,Clicks %';

/** How many pages of listings, from the words on the page's buttons and links. */
export function thePageCount(texts) {
  const numbers = (texts || [])
    .map((one) => String(one || '').trim())
    .filter((one) => /^\d{1,3}$/.test(one))
    .map(Number)
    .filter((one) => one > 0);
  return numbers.length ? Math.max(...numbers) : 1;
}

/** A listing row's SKU: its second line, the reference's own reading. */
export function theSkuOf(rowText) {
  const lines = String(rowText || '').split('\n').map((one) => one.trim()).filter(Boolean);
  return lines.length >= 2 ? lines[1] : 'N/A';
}

/** The file: one row per keyword, the day first, every cell quoted. */
export function theCsv(dataDate, rows) {
  const quoted = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`;
  return `${THE_HEADER}\n${(rows || []).map((one) => [dataDate, ...one].map(quoted).join(',')).join('\n')}`;
}

/** The day the traffic report is showing, read off its own address -- the
 *  reference's way (`startDate=` in the address), never the `Latest` chip's words. */
export function theDayShown(address) {
  const found = /startDate=(\d{4}-\d{2}-\d{2})/.exec(String(address || ''));
  return found ? found[1] : '';
}

/** The pop-up: the smallest block holding both its title and a table. */
function thePopUpIn(page) {
  const holding = [...page.querySelectorAll('div')]
    .filter((one) => String(one.innerText || '').includes(THE_POP_UP) && one.querySelector('table'));
  return holding.find((one) => !holding.some((other) => other !== one && one.contains(other))) || null;
}

/**
 * Read every listing's top search keywords, on every page.
 *
 * `rest` is handed in so the pacing is the walk's own; the reference's pauses are
 * kept: about a second before a press, four seconds for the pop-up, two after
 * closing it, five after moving to another page.
 */
export async function readTheKeywords(page, {
  dataDate, patience = 60, rest = (ms) => new Promise((done) => { setTimeout(done, ms); }),
  say = () => {}, dice = Math.random, whereNow = () => '',
} = {}) {
  /* **THE DAY SHOWN IS ASKED FIRST, BEFORE ANYTHING IS PRESSED.** The keywords are
   * offered for Flipkart's latest day only; read under another day's name they
   * would be the wrong day's figures in the right day's file. */
  const shownDay = theDayShown(whereNow());
  if (dataDate && shownDay && shownDay !== dataDate) {
    return { rows: [], listings: 0, pages: 0, shownDay, csv: '' };
  }
  /* **A DAY THAT CANNOT BE TOLD FAILS CLOSED (review finding, 2026-10-05).** An address naming no day used to skip
   * the check and read the page under the day asked for -- the wrong day's figures in the right day's file.
   * Nothing is pressed, and the walk says it could not tell. */
  if (dataDate && !shownDay) {
    return { rows: [], listings: 0, pages: 0, shownDay: '', csv: '', dayNotShown: true };
  }
  const buttonsOnThe = (row) => [...row.querySelectorAll('button')]
    .filter((one) => String(one.textContent || '').includes(THE_BUTTON));
  /* **THE LIST IS WAITED FOR**, because the traffic report draws its listing table
   * a while after the day is accepted. */
  for (let waited = 0; waited < patience * 1000 && !buttonsOnThe(page).length; waited += 1000) {
    // eslint-disable-next-line no-await-in-loop
    await rest(1000);
  }
  const pages = thePageCount([...page.querySelectorAll('button, a')].map((one) => one.textContent));
  const rows = [];
  let listings = 0;
  /* Listings whose keyword pop-up never opened: counted and named, never skipped quietly -- a file missing
   * those listings would land as the whole day. */
  const notOpened = [];
  for (let at = 1; at <= pages; at += 1) {
    if (at > 1) {
      const next = [...page.querySelectorAll('button, a')]
        .find((one) => String(one.textContent || '').trim() === String(at));
      if (!next) {
        say(`keywords: page ${at} of ${pages} could not be found, so the pages after it were not read.`);
        break;
      }
      next.click();
      // eslint-disable-next-line no-await-in-loop
      await rest(5000);
    }
    let here = 0;
    for (const row of [...page.querySelectorAll('tr')]) {
      const button = buttonsOnThe(row)[0];
      if (!button) continue;
      listings += 1;
      const sku = theSkuOf(row.innerText);
      if (typeof button.scrollIntoView === 'function') button.scrollIntoView({ block: 'center' });
      // eslint-disable-next-line no-await-in-loop
      await rest(800 + dice() * 400);
      button.click();
      // eslint-disable-next-line no-await-in-loop
      await rest(4000);
      const popUp = thePopUpIn(page);
      if (!popUp) {
        notOpened.push(sku);
        continue;
      }
      for (const line of [...popUp.querySelectorAll('table tbody tr')]) {
        const cells = [...line.querySelectorAll('td')].map((one) => String(one.innerText || '').trim());
        if (cells.length >= 3 && cells[0]) rows.push([sku, cells[0], cells[1], cells[2]]);
      }
      const close = popUp.querySelector('[aria-label="close"]') || page.querySelector('[aria-label="close"]');
      if (close) close.click();
      here += 1;
      // eslint-disable-next-line no-await-in-loop
      await rest(2000 + dice() * 500);
    }
    say(`keywords: page ${at} of ${pages}, ${here} listings read.`);
  }
  return { rows, listings, pages, shownDay, notOpened, csv: theCsv(dataDate, rows) };
}
