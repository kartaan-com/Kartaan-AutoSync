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
  'meesho-product-performance', 'meesho-pricing', 'flipkart-quality-insights',
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
    kids.forEach(walk);
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
 * in Excel would run `=...` or `@...`. A sign before a figure (`-3%`, `+4`) is left alone; a sign before words is not. */
export const plain = (value) => {
  const text = String(value ?? '');
  return /^([=@\t\r]|[+-][^\d.\u20B9])/.test(text) ? `'${text}` : text;
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
  const way = TABLE_FOR[table];
  if (!way) throw new Error(`"${table}" is not a table this knows how to read.`);
  return way.fileHeader;
}

function theTableOn(page, way) {
  return below(page, 'table').find((one) => textOf(one).includes(way.words)) || null;
}

/** The header cells of a table: their words, in order, with the empty ones kept in place (a tick box has no words). */
function headerCellsOf(table) {
  return below(table, 'th').map(textOf);
}

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
  if (way.pageLabel) {
    for (let waited = 0; waited < 15000 && !pagesNamed(); waited += 500) {
      // eslint-disable-next-line no-await-in-loop
      await rest(500);
    }
    if (!pagesNamed()) throw new Error('the page numbers never appeared on the pager, so there is no telling how many pages the table has. Nothing was read.');
  }

  for (let guard = 0; guard < 500; guard += 1) {
    const now = theTableOn(page, way);
    if (!now) throw new Error(`the table went from the page after page ${pages}, so nothing was put away.`);
    const here = below(now, 'tr').filter((one) => below(one, 'td').length);
    pages += 1;
    declared = Math.max(declared, pagesNamed());
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
    say(`${table}: page ${pages}, ${here.length} rows.`);

    /* **A PAGER THAT NAMES ITS PAGES IS FINISHED WHEN THE LAST NAMED PAGE IS READ**, whatever its next button then looks like. */
    if (declared && pages >= declared) break;
    const next = labelled(page, way.next);
    if (!next || isOff(next)) break;
    next.click();
    /* **THE NEXT PAGE IS WAITED FOR BY ITS FIRST ROW CHANGING**, never by time alone. */
    let moved = false;
    for (let waited = 0; waited < Math.min(patience, 30) * 1000; waited += 500) {
      // eslint-disable-next-line no-await-in-loop
      await rest(500);
      const after = theTableOn(page, way);
      const rowsAfter = after ? below(after, 'tr').filter((one) => below(one, 'td').length) : [];
      if (rowsAfter.length && textOf(rowsAfter[0]) !== firstKey) { moved = true; break; }
    }
    /* **A PAGER WITH NO PAGE NUMBERS (Flipkart's) HAS NO OTHER WAY TO SAY IT HAS ENDED**: a next button that is still on and moves
     * nothing, after the whole wait, is the end of the table. A pager that names its pages never ends this way. */
    if (!moved && !way.pageLabel) break;
    if (!moved) throw new Error(`page ${pages + 1} did not draw after the pager was pressed, so nothing was put away.`);
  }

  if (declared && pages !== declared) {
    throw new Error(`the pager lists ${declared} pages and ${pages} were read, so nothing was put away rather than a part of the table.`);
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
