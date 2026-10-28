/* Three tables read off their pages, page by page (plan jobs 44 and 43, and Flipkart's Product Quality Insights).
 *
 * **NONE OF THE THREE HAS A DOWNLOAD BUTTON THAT WORKS**, so the walker reads the table the way a person scrolls it: every page, in
 * order, kept exactly as the page showed it. No arithmetic is done here. Meesho's product performance is a seven-day window the
 * seller cannot move, and the day's own figure is worked out later, from two kept files; a figure worked out before saving would
 * have thrown away the only thing that could correct it (plan piece 44).
 *
 * **THE PAGES' SHAPES WERE READ OFF HIS OWN PANELS BY CONTROL ON 2026-10-05, READ ONLY, and are written down below and nowhere else.**
 * No selector was guessed. What is relied on, per table:
 *
 *   meesho-product-performance  one `table`; header cells Product Details, Views, Clicks, Orders, Conversions, Sales, Returns,
 *     Insights, Recommendations; ten rows a page; a cell's values are leaf elements; the first cell holds the name, a line
 *     `Catalog ID: <n>` and the star rating; a pager of buttons `Previous page`, `Page 1` .. `Page 15`, `Next page`; the page prints
 *     the days the table covers ("28th Sep '26 - 4th Oct '26") and "Last updated 4th Oct | 10:39".
 *   meesho-pricing  one `table`; header cells (an empty one for the tick box), Product Details, Current Stock, Growth in 30 days,
 *     Current Customer Price, Recommended Customer Price, Insights, Action; twenty-five rows a page; the first cell holds the name,
 *     `Catalog ID: <n>` and `SKU ID: <text>`; the same pager; tab chips `Losing Orders (n)`, `Losing Views (n)`, `Best Priced (n)`.
 *   flipkart-quality-insights  a `table` whose words include `Suppression Risk`; header cells (an empty one for the tick box),
 *     Product Details, Yearly Sales, 1Y Ratings Trend, 5M Returns Trend, FA, Suppression Risk, Issue Details, (an empty one); ten
 *     rows a page; a pager of two buttons, `Previous Page` and `Next Page`, and no page numbers.
 *
 * **ANYTHING ELSE ON THOSE PAGES IS NEVER TOUCHED.** The pricing page has Accept, Edit and Bulk Price Update beside its table; the
 * only things pressed here are the page buttons named above, found by their `aria-label` and nothing else.
 *
 * **A TABLE WHOSE COLUMNS ARE NOT THE ONES NAMED IS REFUSED, naming the columns it has**, and so is a pager that did not move or a
 * run of pages that stopped short: a part of the table is never put away as the whole of it.
 */

export const THE_TABLES = Object.freeze([
  'meesho-product-performance', 'meesho-pricing', 'flipkart-quality-insights', 'meesho-quality',
]);

/** Elements below `root` with this tag, document order. Walks `children`, so it needs no selector engine. */
function below(root, tag) {
  const out = [];
  const walk = (one) => {
    for (const child of one.children || []) {
      if (String(child.tagName || '').toLowerCase() === tag) out.push(child);
      walk(child);
    }
  };
  walk(root);
  return out;
}

const textOf = (one) => String((one && one.textContent) || '').replace(/\s+/g, ' ').trim();

/** The words of the elements with nothing inside them but words, in order: the page's own smallest pieces. */
export function leavesOf(root) {
  const out = [];
  const walk = (one) => {
    const kids = one.children || [];
    if (!kids.length) {
      const said = textOf(one);
      if (said) out.push(said);
      return;
    }
    /* A real page's `children` is an HTMLCollection, which has no `forEach` (A84, 15 Oct: "kids.forEach is not a function"). */
    Array.from(kids).forEach(walk);
  };
  walk(root);
  return out;
}

/** What follows a label, in a line (`Catalog ID: 123`) or in the next piece (`SKU ID:` then `ABC`). Empty when the label is absent. */
export function afterTheLabel(leaves, label) {
  for (let at = 0; at < leaves.length; at += 1) {
    if (leaves[at].startsWith(label)) {
      const same = leaves[at].slice(label.length).trim();
      return same || (leaves[at + 1] || '');
    }
  }
  return '';
}

/* **A CELL THAT BEGINS LIKE A SPREADSHEET FORMULA IS MADE PLAIN TEXT** (review finding): a product title is the seller's, and a file opened
 * in Excel would run `=...` or `@...`. A sign before a WHOLE figure (`-3%`, `+4`, `-1,250.50`) is left alone; a sign before words, or before a figure with
 * more after it (`-1+1`), is not (the security read of the AJ2 join). */
export const plain = (value) => {
  const text = String(value ?? '');
  return /^([=@\t\r]|[+-](?!\u20B9?(\d[\d,]*)?\.?\d+%?$))/.test(text) ? `'${text}` : text;
};
const quoted = (value) => `"${plain(value).replace(/"/g, '""')}"`;

/** The file: its header, then one row per table row, every cell quoted. */
export function theCsv(header, rows) {
  return `${header.map(quoted).join(',')}\n${rows.map((row) => row.map(quoted).join(',')).join('\n')}`;
}

const joined = (leaves) => leaves.join(' | ');

const RANGE = /\d{1,2}(st|nd|rd|th) \w{3} ['\u2019]\d{2}\s*-\s*\d{1,2}(st|nd|rd|th) \w{3} ['\u2019]\d{2}/;

/** What the page prints about the days a table covers, for the first columns of every row. Throws when the range is not printed. */
function meesho(page) {
  const all = leavesOf(page);
  const range = all.map((one) => RANGE.exec(one)).find(Boolean);
  if (!range) {
    throw new Error('the page does not print which days the table covers, so a file made from it could not say what it holds. '
      + 'Nothing was read.');
  }
  const at = all.findIndex((one) => /^Last updated/i.test(one));
  const updated = at < 0 ? '' : (/^Last updated\s*$/i.test(all[at]) ? `${all[at]} ${all[at + 1] || ''}`.trim() : all[at]);
  return { range: range[0], updated };
}

const TABLE_FOR = {
  'meesho-product-performance': {
    words: 'Product Details',
    headers: ['Product Details', 'Views', 'Clicks', 'Orders', 'Conversions', 'Sales', 'Returns', 'Insights', 'Recommendations'],
    next: 'Next page',
    pageLabel: (n) => `Page ${n}`,
    meta: meesho,
    all: /^All \((\d+)\)$/,
    fileHeader: ['Range', 'Last updated', 'Product', 'Catalog ID', 'Rating', 'Views', 'Clicks', 'Orders', 'Conversions', 'Sales', 'Returns',
      'Insights', 'Recommendations'],
    row(cells, by, meta) {
      const first = leavesOf(cells[by['Product Details']]);
      const rating = first.length && /^\d(\.\d+)?$/.test(first[first.length - 1]) ? first[first.length - 1] : '';
      return [meta.range, meta.updated, first[0] || '', afterTheLabel(first, 'Catalog ID:'), rating]
        .concat(this.headers.slice(1).map((name) => joined(leavesOf(cells[by[name]]))));
    },
  },
  'meesho-pricing': {
    words: 'Recommended Customer Price',
    all: /^All Products \((\d+)\)$/,
    headers: ['Product Details', 'Current Stock', 'Growth in 30 days', 'Current Customer Price', 'Recommended Customer Price',
      'Insights', 'Action'],
    // **THE ACTION CELL (Accept, Edit) IS NEVER READ OR TOUCHED**, so it is not a column of the file.
    kept: ['Current Stock', 'Growth in 30 days', 'Current Customer Price', 'Recommended Customer Price', 'Insights'],
    next: 'Next page',
    pageLabel: (n) => `Page ${n}`,
    meta(page) {
      const chips = [...new Set(leavesOf(page).filter((one) => /^(All Products|Losing Orders|Losing Views|Best Priced) \(\d+\)$/.test(one)))];
      return { counts: chips.join('; ') };
    },
    fileHeader: ['Product', 'Catalog ID', 'SKU ID', 'Tab counts', 'Current Stock', 'Growth in 30 days', 'Current Customer Price',
      'Recommended Customer Price', 'Insights'],
    row(cells, by, meta) {
      const first = leavesOf(cells[by['Product Details']]);
      return [first[0] || '', afterTheLabel(first, 'Catalog ID:'), afterTheLabel(first, 'SKU ID:'), meta.counts]
        .concat(this.kept.map((name) => joined(leavesOf(cells[by[name]]))));
    },
  },
  'flipkart-quality-insights': {
    words: 'Suppression Risk',
    headers: ['Product Details', 'Yearly Sales', '1Y Ratings Trend', '5M Returns Trend', 'FA', 'Suppression Risk', 'Issue Details'],
    next: 'Next Page',
    pageLabel: null,
    meta: () => ({}),
    fileHeader: ['Product', 'SKU ID', 'Yearly Sales', '1Y Ratings Trend', '5M Returns Trend', 'FA badge', 'Suppression Risk', 'Issue Details'],
    row(cells, by) {
      const first = leavesOf(cells[by['Product Details']]);
      const badge = below(cells[by.FA], 'img').length ? 'Yes' : 'No';
      return [first[0] || '', afterTheLabel(first, 'SKU ID:')].concat(
        ['Yearly Sales', '1Y Ratings Trend', '5M Returns Trend'].map((name) => joined(leavesOf(cells[by[name]]))),
        [badge],
        ['Suppression Risk', 'Issue Details'].map((name) => joined(leavesOf(cells[by[name]]))),
      );
    },
  },
};

/** The header of the file a table makes. */
export function theHeaderOf(table) {
  if (table === 'meesho-quality') return QUALITY_COLUMNS;
  const way = TABLE_FOR[table];
  if (!way) throw new Error(`"${table}" is not a table this knows how to read.`);
  return way.fileHeader;
}

function theTableOn(page, way) {
  return below(page, 'table').find((one) => textOf(one).includes(way.words)) || null;
}

/* **TWO HEADER CELLS ARE READ BY THEIR NAME FROM THE 15 OCT RUN, AND NO OTHER** (A84): Flipkart's tick-box cell now carries its icon's name
 * as words (`CheckBoxOutlineBlank`), so it is an empty cell as before; Meesho's pricing header runs two words together (`Growthin 30 days`),
 * so it is the column it always was. Any other word is still refused, naming the columns the table has. */
const ICON_NAMES = new Set(['CheckBoxOutlineBlank']);
const RUN_TOGETHER = { 'Growthin 30 days': 'Growth in 30 days' };

/** The header cells of a table: their words, in order, with the empty ones kept in place (a tick box has no words). */
function headerCellsOf(table) {
  return below(table, 'th').map(textOf).map((words) => (ICON_NAMES.has(words) ? '' : (RUN_TOGETHER[words] || words)));
}

/** How many times one page change is asked of the pager before it is called undrawn: the press, and two more. */
const A_PAGE_IS_ASKED_FOR_AT_MOST = 3;

const isOff = (button) => !!(button && (button.disabled === true || (button.getAttribute && button.getAttribute('aria-disabled') === 'true')));

const labelled = (page, label) => below(page, 'button').find((one) => one.getAttribute && one.getAttribute('aria-label') === label) || null;

/**
 * Read one table, every page of it. Answers `{ csv, rows, pages, columns }`, or throws saying what was wrong and that nothing was
 * put away.
 *
 * `rest(ms)` is the walk's own pacing. The page is waited for up to `patience` seconds, and so is each page change.
 */
export async function readTheTable(page, {
  table, patience = 120, rest = (ms) => new Promise((done) => { setTimeout(done, ms); }), say = () => {},
} = {}) {
  if (table === 'meesho-quality') return readTheQuality(page, { patience, rest, say });
  const way = TABLE_FOR[table];
  if (!way) throw new Error(`"${table}" is not a table this knows how to read.`);

  /* **THE TABLE IS WAITED FOR**, because all three pages draw it a while after they open. */
  let there = theTableOn(page, way);
  for (let waited = 0; waited < patience * 1000 && !there; waited += 1000) {
    // eslint-disable-next-line no-await-in-loop
    await rest(1000);
    there = theTableOn(page, way);
  }
  if (!there) throw new Error(`the table (${way.headers[0]}, ${way.headers[1]}, ...) never appeared on the page, so nothing was read.`);

  const headerCells = headerCellsOf(there);
  const named = headerCells.filter(Boolean);
  if (named.join('\n') !== way.headers.join('\n')) {
    throw new Error(`the table's columns are not the ones expected. It has: ${named.join(', ')}. Expected: ${way.headers.join(', ')}. `
      + 'Nothing was read, because a column that has moved would put one column\'s figures under another\'s name.');
  }
  const by = {};
  headerCells.forEach((name, at) => { if (name) by[name] = at; });

  const meta = way.meta(page);
  const rows = [];
  const perPage = [];
  const refused = [];
  const seen = new Set();
  let pages = 0;
  /* **THE PAGES THE PAGER NAMES ARE ASKED EVERY PAGE, not once**: a pager drawn a moment after its table, or one that shows a window
   * of numbers, must not make a one-page read look like the whole table. The most ever named is what has to have been read. */
  const pagesNamed = () => (way.pageLabel
    ? Math.max(0, ...below(page, 'button').map((one) => /^Page (\d{1,3})$/.exec((one.getAttribute && one.getAttribute('aria-label')) || ''))
      .filter(Boolean).map((one) => Number(one[1])))
    : 0);
  let declared = 0;
  let stopped = '';
  /* The pager's buttons as the page draws them (label, then ON or OFF), for a short read to say; the table's own buttons are not the pager's, so only ones named for a page or for next/previous are listed. */
  const pagerButtons = (where) => {
    const named = below(where, 'button').map((one) => {
      const said = (one.getAttribute && one.getAttribute('aria-label')) || '';
      return said && /page|next|previous/i.test(said) ? `${said} ${isOff(one) ? 'OFF' : 'ON'}` : '';
    }).filter(Boolean);
    return named.length ? named.slice(0, 40).join(', ') : 'no button named for a page';
  };
  if (way.pageLabel) {
    for (let waited = 0; waited < 15000 && !pagesNamed(); waited += 500) {
      // eslint-disable-next-line no-await-in-loop
      await rest(500);
    }
    if (!pagesNamed()) throw new Error('the page numbers never appeared on the pager, so there is no telling how many pages the table has. Nothing was read.');
  }

  /* **A PAGE IS READ WHEN ITS ROWS HAVE STOPPED ARRIVING (his Meesho run of 27 Oct 2026: pages of 25 rows read as 20, 16 and 20).** A new page is known to have come by its first row changing, and the rest of its rows can
   * still be drawing; the count of rows is looked at again, half a second apart, until it is the same twice running (at most twenty looks). */
  const rowsNow = () => { const there2 = theTableOn(page, way); return there2 ? below(there2, 'tr').filter((one) => below(one, 'td').length).length : 0; };
  const rowsHaveStoppedArriving = async () => {
    let count = rowsNow();
    for (let same = 0, looks = 0; same < 2 && looks < 20; looks += 1) {
      // eslint-disable-next-line no-await-in-loop
      await rest(500);
      const again = rowsNow();
      same = again === count ? same + 1 : 0;
      count = again;
    }
  };

  /* **EVERY PAGE BUT THE LAST GIVES THE PAGE SIZE THE PAGE PRINTS (his Meesho pricing run of 28 Oct 2026: the read gave 24 rows where his own count of that page was 25; the rows had stopped arriving for ten seconds and then came).**
   * "25 Items / page" is the page's own word for how many rows a full page holds, so a page before the last that shows fewer is still drawing: it is waited for, up to `patience`, and a page that never fills fails the read. */
  const printedPageSize = () => {
    if (!way.pageLabel) return 0;
    const said = leavesOf(page).map((one) => /^(\d{1,3})\s*Items?\s*\/\s*page$/i.exec(one)).find(Boolean);
    return said ? Number(said[1]) : 0;
  };
  for (let guard = 0; guard < 500; guard += 1) {
    await rowsHaveStoppedArriving();
    const size = printedPageSize();
    const notTheLast = () => { const named = pagesNamed(); return named > 0 && pages + 1 < named; };
    if (size && notTheLast()) {
      for (let waited = 0; waited < patience * 1000 && rowsNow() < size; waited += 500) {
        // eslint-disable-next-line no-await-in-loop
        await rest(500);
      }
      if (rowsNow() < size) {
        throw new Error(`page ${pages + 1} showed ${rowsNow()} rows, but the page prints ${size} Items / page and this is not the last page, so the rest of its rows never came and nothing was put away.`);
      }
    }
    const now = theTableOn(page, way);
    if (!now) throw new Error(`the table went from the page after page ${pages}, so nothing was put away.`);
    const here = below(now, 'tr').filter((one) => below(one, 'td').length);
    pages += 1;
    /* **THE PAGE COUNT IS THE PAGER AS IT STANDS NOW, not the highest "Page N" it ever showed (his run of 28 Oct 2026: a "Page 7" that stuck made a 6-page table read as short).** */
    declared = pagesNamed() || declared;
    const firstKey = here.length ? textOf(here[0]) : '';
    if (firstKey && seen.has(firstKey) && !way.pageLabel) break;
    if (firstKey && seen.has(firstKey)) {
      throw new Error(`page ${pages} showed the same first row as an earlier page, so the pager did not move and nothing was put away.`);
    }
    seen.add(firstKey);
    for (const row of here) {
      const cells = below(row, 'td');
      if (cells.length !== headerCells.length) {
        refused.push(`a row with ${cells.length} cells on page ${pages} (the table has ${headerCells.length} columns)`);
        continue;
      }
      rows.push(way.row(cells, by, meta));
    }
    perPage.push(here.length);
    say(`${table}: page ${pages}, ${here.length} rows.`);

    /* **A PAGER THAT NAMES ITS PAGES IS FINISHED WHEN THE LAST NAMED PAGE IS READ**, whatever its next button then looks like. */
    if (declared && pages >= declared) { stopped = `page ${pages} was the last the pager named`; break; }
    /* **A NEXT BUTTON SWITCHED OFF WHILE THE PAGER STILL NAMES MORE PAGES IS GIVEN TIME TO COME ON** (his Meesho run of 27 Oct 2026): the page switches it off while it loads, and taking that for the end of the table
     * stopped every night one page short. Up to ten seconds, only while more pages are named. */
    let next = labelled(page, way.next);
    for (let looks = 0; declared && pages < declared && (!next || isOff(next)) && looks < 20; looks += 1) {
      // eslint-disable-next-line no-await-in-loop
      await rest(500);
      next = labelled(page, way.next);
    }
    if (!next || isOff(next)) { stopped = next ? `the next button was there but switched off after page ${pages}` : `there was no next button after page ${pages}`; break; }
    next.click();
    /* **THE NEXT PAGE IS WAITED FOR BY ITS FIRST ROW CHANGING**, never by time alone.
     *
     * **A PAGE THAT HAS NOT DRAWN IS WAITED FOR LONGER, AND ASKED FOR AGAIN (A86, his 20 Oct run: Meesho pricing page 7 "did not draw",
     * the page text only the left menu).** Meesho can take the whole content area away while a page loads, and a table that is gone is
     * not a page that failed -- it gets the whole `patience`, not the thirty seconds a table that is still there and has not changed
     * gets. If that still draws nothing, the press may simply not have been heard: the pager is asked again, at most twice more, and
     * only after the wait above ended with the page still undrawn -- nothing can draw between that look and the press, so a press never lands on a page that had drawn. A pager
     * that names its pages is the only kind that retries -- Flipkart's ends by not moving, and would wait three times at its real end.
     * **NOTHING IS PUT AWAY UNTIL EVERY PAGE THE PAGER NAMES HAS BEEN READ** (below), so a page that never draws still fails the read
     * as a whole and never lands half a table. */
    let moved = false;
    const hasMoved = () => {
      const after = theTableOn(page, way);
      const rowsAfter = after ? below(after, 'tr').filter((one) => below(one, 'td').length) : [];
      return { rowsAfter, moved: rowsAfter.length > 0 && textOf(rowsAfter[0]) !== firstKey };
    };
    for (let pressed = 1; pressed <= (way.pageLabel ? A_PAGE_IS_ASKED_FOR_AT_MOST : 1) && !moved; pressed += 1) {
      if (pressed > 1) {
        const again = labelled(page, way.next);
        if (!again || isOff(again)) break;
        again.click();
        say(`${table}: page ${pages + 1} had not drawn, so the pager was pressed again.`);
      }
      for (let waited = 0; ; waited += 500) {
        // eslint-disable-next-line no-await-in-loop
        await rest(500);
        const seen = hasMoved();
        if (seen.moved) { moved = true; break; }
        if (waited >= (seen.rowsAfter.length ? Math.min(patience, 30) : patience) * 1000) break;
      }
    }
    /* **A PAGER WITH NO PAGE NUMBERS (Flipkart's) HAS NO OTHER WAY TO SAY IT HAS ENDED**: a next button that is still on and moves
     * nothing, after the whole wait, is the end of the table. A pager that names its pages never ends this way. */
    if (!moved && !way.pageLabel) break;
    if (!moved) throw new Error(`page ${pages + 1} did not draw after the pager was pressed, so nothing was put away.`);
  }

  /* **THE PAGE'S OWN COUNT OF EVERYTHING IS THE LAST WORD (N017, his D726; the run logs of 22-25 Oct: "the pager lists 7 pages and 6 were read" every
   * night).** A pager that names a page the table does not have is not a part of the table when the rows read are exactly the count the page prints;
   * with no count printed, or a count the rows do not reach, the read still fails, and now says what each page gave and what the pager showed. */
  const countOnPage = way.all ? leavesOf(page).map((one) => way.all.exec(one)).find(Boolean) : null;
  if (declared && pages !== declared) {
    if (countOnPage && Number(countOnPage[1]) === rows.length) {
      say(`${table}: the pager lists ${declared} pages and ${pages} were read, and the page counts ${countOnPage[1]} in all, which is every row read, so the table is whole.`);
    } else {
      throw new Error(`the pager lists ${declared} pages and ${pages} were read, so nothing was put away rather than a part of the table `
        + `(rows on each page: ${perPage.join(', ')}; ${countOnPage ? `the page counts ${countOnPage[1]} in all` : 'the page prints no count of everything'}; `
        + `the read stopped because ${stopped || 'the loop ended'}; the pager showed ${pagerButtons(page)}).`);
    }
  }
  if (refused.length) {
    throw new Error(`${refused.length} row(s) were not the shape of the table (${refused.slice(0, 3).join('; ')}), so nothing was put away.`);
  }
  if (!rows.length) throw new Error('the table had no rows, so nothing was put away.');
  /* **THE PAGE'S OWN COUNT OF EVERYTHING IS THE LAST WORD ON WHETHER THIS IS THE WHOLE TABLE**: a tab other than All (Losing Views, Low
   * Orders) lists fewer, and so does a short read. A count that is not on the page is said, not guessed. */
  if (way.all) {
    const chip = leavesOf(page).map((one) => way.all.exec(one)).find(Boolean);
    if (!chip) say(`${table}: the page prints no count of everything to compare ${rows.length} rows against.`);
    else if (Number(chip[1]) !== rows.length) {
      throw new Error(`the page counts ${chip[1]} in all and ${rows.length} rows were read (a filtered tab, or a part of the table), `
        + 'so nothing was put away.');
    }
  }
  return { csv: theCsv(theHeaderOf(table), rows), rows: rows.length, pages, columns: theHeaderOf(table).length };
}

/* **AMAZON'S WEEKLY SETTLEMENT STATEMENTS (N018, his All Statements page, seen 26 Oct 2026).** One row per statement, its period written DAY FIRST with no noughts and a dash --
 * `13/10/2026 – 20/10/2026`, `29/9/2026 – 6/10/2026` -- and the open one `20/10/2026 – Present`, which has no Download. The row's period names the statement, and the day it ENDED is the
 * day its file is filed under. Pure: a row's words in, its period out, or nothing.
 *
 * **NOTHING IS GUESSED:** a period whose day or month is not a real one, or that ends before it starts, is nothing; "Present" is nothing. */
const A_STATEMENT_PERIOD = /(\d{1,2})\/(\d{1,2})\/(\d{4})\s*[–—-]\s*(\d{1,2})\/(\d{1,2})\/(\d{4})/;

function anIsoDay(day, month, year) {
  const d = Number(day);
  const m = Number(month);
  const y = Number(year);
  const made = new Date(Date.UTC(y, m - 1, d));
  if (made.getUTCFullYear() !== y || made.getUTCMonth() !== m - 1 || made.getUTCDate() !== d) return null;
  return `${String(y).padStart(4, '0')}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}

export function theStatementPeriod(rowText) {
  const text = String(rowText ?? '').replace(/\s+/g, ' ').trim();
  const found = A_STATEMENT_PERIOD.exec(text);
  /* **SEVERAL PERIODS IN ONE ROW IS NOT ONE PERIOD (his second live Amazon run, 27 Oct 2026):** a climb that reached past its own row would otherwise file a statement under a neighbouring week. */
  if (found && new RegExp(A_STATEMENT_PERIOD.source, "g").exec(text.slice(found.index + found[0].length))) return null;
  if (!found) return null;
  const start = anIsoDay(found[1], found[2], found[3]);
  const end = anIsoDay(found[4], found[5], found[6]);
  if (!start || !end || end < start) return null;
  return { period: found[0].replace(/\s+/g, ' '), start, end };
}

/* **MEESHO'S PRODUCT QUALITY PAGE (N025; his panel, seen 26 Oct 2026, side menu Quality, `.../cataloging/<slug>/product-optimiser`, no download).** Read into ONE FILE A DAY (his yes):
 *   store     the quality score = 1-2 star ratings over total ratings, as a percentage, with the band the page names in brackets (`Good`)
 *   feedback  each Top Customer Feedback reason with the number of products it is on
 *   tab       each of `Blocking Soon (n)`, `Action Pending (n)`, `Fixed (n)` with its n
 *   product   every product of every tab: name, Style ID, band word and its own percentage, and its reasons with their rating counts
 * The products shown change with the tab, so each tab (`role="tab"`) is pressed in turn and read; **the page's own count on each tab is the last word on whether the whole list was read.**
 * Nothing but the three tabs is ever pressed (the page has `Save`, `View Products` and others beside them). **A page that is not this one, or has no store score, is refused in words and nothing is put away.** */
const QUALITY_COLUMNS = ['Kind', 'Tab', 'Name', 'Style ID', 'Band', 'Percent', 'Count', 'Detail'];
const A_QUALITY_TAB = /^(Blocking Soon|Action Pending|Fixed) \((\d+)\)$/;
const A_QUALITY_BAND = /^(Green|Yellow|Red|Blocked)$/;
const A_BAND_PERCENT = /^\((\d+(?:\.\d+)?)%\)$/;
const A_REASON = /^(.+) \((\d+) ratings?\)$/;
const A_PRODUCTS_COUNT = /^(\d+) products?$/;

function theQualityStore(leaves) {
  const next = (label) => {
    const at = leaves.indexOf(label);
    return at < 0 ? '' : (leaves[at + 1] || '');
  };
  const low = next('1 and 2 star ratings');
  const total = next('Total Ratings');
  const atTotal = leaves.indexOf('Total Ratings');
  const percent = atTotal < 0 ? undefined : leaves.slice(atTotal).find((one) => /^\d+(?:\.\d+)?%$/.test(one));
  const atPercent = percent === undefined ? -1 : leaves.indexOf(percent, atTotal);
  const band = atPercent < 0 ? '' : ((leaves.slice(atPercent, atPercent + 4).find((one) => /^\([A-Za-z ]+\)$/.test(one)) || '').slice(1, -1));
  if (!/^\d+$/.test(low) || !/^\d+$/.test(total) || percent === undefined || !band) return null;
  return { low, total, percent: percent.slice(0, -1), band };
}

function theQualityFeedback(leaves) {
  const from = leaves.indexOf('Top Customer Feedback');
  const to = leaves.indexOf('Quality Recommendations');
  if (from < 0 || to < 0 || to < from) return [];
  const section = leaves.slice(from + 1, to);
  const out = [];
  section.forEach((one, at) => {
    const found = A_PRODUCTS_COUNT.exec(one);
    if (found && at > 0) out.push({ reason: section[at - 1], count: found[1] });
  });
  return out;
}

function theQualityProducts(leaves) {
  const out = [];
  const from = leaves.indexOf('Action');
  const to = leaves.findIndex((one) => one.startsWith('SAH Shipping Estimate'));
  const area = leaves.slice(from < 0 ? 0 : from + 1, to < 0 ? leaves.length : to);
  area.forEach((one, at) => {
    if (!one.startsWith('Style ID:')) return;
    const band = area[at + 1] || '';
    const percent = A_BAND_PERCENT.exec(area[at + 2] || '');
    const reasons = [];
    for (let k = at + 3; k < area.length; k += 1) {
      const found = A_REASON.exec(area[k]);
      if (!found) break;
      reasons.push({ said: area[k], count: Number(found[2]) });
    }
    out.push({
      name: area[at - 1] || '', style: one.slice('Style ID:'.length).trim(), band: A_QUALITY_BAND.test(band) ? band : '',
      percent: percent ? percent[1] : '', reasons,
    });
  });
  return out;
}

export async function readTheQuality(page, {
  patience = 120, rest = (ms) => new Promise((done) => { setTimeout(done, ms); }), say = () => {},
} = {}) {
  const tabsOn = () => below(page, 'button').filter((one) => (one.getAttribute && one.getAttribute('role')) === 'tab' && A_QUALITY_TAB.test(textOf(one)));
  /* **THE PAGE IS WAITED FOR**: it draws its tabs a while after it opens. */
  let tabs = tabsOn();
  for (let waited = 0; waited < patience * 1000 && tabs.length < 3; waited += 1000) {
    // eslint-disable-next-line no-await-in-loop
    await rest(1000);
    tabs = tabsOn();
  }
  if (!leavesOf(page).includes('Product Quality')) {
    throw new Error('this is not the Product Quality page (its heading "Product Quality" is not on it), so nothing was read.');
  }
  if (tabs.length !== 3) {
    throw new Error(`the three tabs (Blocking Soon, Action Pending, Fixed) were not all on the page (${tabs.length} found), so nothing was read.`);
  }
  const store = theQualityStore(leavesOf(page));
  if (!store) {
    throw new Error('the store quality score (its low ratings, total ratings, percentage and band) is not on the page, so nothing was read. Nothing was read rather than a file without it.');
  }
  const rows = [['store', '', 'Quality score', '', store.band, store.percent, store.total, `${store.low} of ${store.total} ratings were 1 or 2 stars`]];
  theQualityFeedback(leavesOf(page)).forEach((one) => rows.push(['feedback', '', one.reason, '', '', '', one.count, '']));
  const counts = tabs.map((one) => ({ name: A_QUALITY_TAB.exec(textOf(one))[1], count: Number(A_QUALITY_TAB.exec(textOf(one))[2]) }));
  counts.forEach((one) => rows.push(['tab', one.name, '', '', '', '', one.count, '']));
  for (let at = 0; at < tabs.length; at += 1) {
    // eslint-disable-next-line no-await-in-loop
    await rest(500);
    tabs[at].click();
    // eslint-disable-next-line no-await-in-loop
    await rest(1500);
    const products = theQualityProducts(leavesOf(page));
    if (products.length !== counts[at].count) {
      throw new Error(`the ${counts[at].name} tab says ${counts[at].count} and ${products.length} products were read from it, so nothing was put away rather than a part of the list.`);
    }
    products.forEach((one) => rows.push(['product', counts[at].name, one.name, one.style, one.band, one.percent,
      one.reasons.reduce((all, r) => all + r.count, 0), one.reasons.map((r) => r.said).join(' | ')]));
  }
  say(`meesho-quality: read the store score, ${counts.length} tabs and ${rows.filter((r) => r[0] === 'product').length} products.`);
  return { csv: theCsv(QUALITY_COLUMNS, rows), rows: rows.length, pages: tabs.length, columns: QUALITY_COLUMNS.length };
}
