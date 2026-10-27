/* Checks for the three tables read off their pages (job 15).
 *
 * Run: node extension/tables.test.js
 *
 * **EVERY PAGE HERE IS MADE UP**, built to the shape Control read off his panels on 2026-10-05 (read only): the table, its header
 * cells, its rows, the pager's `aria-label`s. Not one figure of his is in this file. What is checked is what can be wrong without his
 * pages: which columns are required, that a pager that did not move or stopped short fails the whole read, that nothing but the
 * named page buttons is pressed, and the file that is made.
 */

import { readFileSync } from 'node:fs';
import { THE_TABLES, afterTheLabel, leavesOf, plain, readTheTable, theCsv, theHeaderOf, theStatementPeriod } from './tables.js';

process.on('uncaughtException', (err) => {
  console.log(`FAIL  the checks stopped part way through: ${(err && err.message) || String(err)}`);
  process.exit(1);
});
process.on('unhandledRejection', (err) => {
  console.log(`FAIL  something was waited on and never came back: ${(err && err.message) || String(err)}`);
  process.exit(1);
});

let ran = 0;
let failures = 0;
function check(name, passed) {
  ran += 1;
  console.log(`${passed ? 'PASS' : 'FAIL'}  ${name}`);
  if (!passed) failures += 1;
}

/* ---------------------------------------------------------------- a page made of plain objects */

class Collection {
  constructor(list) {
    this.length = list.length;
    list.forEach((one, at) => { this[at] = one; });
  }

  [Symbol.iterator]() {
    return Array.prototype[Symbol.iterator].call(this);
  }
}

class El {
  constructor(tagName, { text = '', attrs = {}, kids = [] } = {}) {
    this.tagName = tagName.toUpperCase();
    this.attrs = attrs;
    this._kids = kids;
    this.ownText = text;
    this.disabled = attrs.disabled === true;
    this.clicks = 0;
    this.onClick = null;
  }

  /* **A REAL PAGE'S `children` IS AN HTMLCollection: it can be counted, indexed and looped over, and it has no `forEach`** (the live fault
   * "kids.forEach is not a function", 15 Oct). Switched on for the checks that need it; every other check keeps a plain list. */
  get children() {
    return El.realistic ? new Collection(this._kids) : this._kids;
  }

  set children(list) {
    this._kids = list;
  }

  get textContent() {
    return this.ownText + this._kids.map((one) => one.textContent).join(' ');
  }

  getAttribute(name) {
    return name in this.attrs ? String(this.attrs[name]) : null;
  }

  click() {
    this.clicks += 1;
    if (this.onClick) this.onClick();
  }
}

const el = (tag, text, kids, attrs) => new El(tag, { text, kids: kids || [], attrs: attrs || {} });
const p = (text) => el('p', text);

function aPage({ headers, pages, tableText = "", extra = [], pager }) {
  /* `pages` is a list of pages, each a list of rows, each a list of cells, each a list of leaf words (or an El). */
  const state = { at: 0 };
  const cell = (leaves) => (leaves instanceof El ? leaves : el('td', '', leaves.map(p)));
  const body = el('tbody', '');
  const draw = () => {
    body.children = pages[state.at].map((row) => el('tr', '', row.map(cell)));
  };
  draw();
  const table = el('table', tableText, [el('thead', '', [el('tr', '', headers.map((one) => el('th', one)))]), body]);
  const buttons = (pager || []).map((spec) => {
    const b = el('button', spec.label, [], { 'aria-label': spec.label, ...(spec.disabled ? { 'aria-disabled': 'true' } : {}) });
    if (spec.label.toLowerCase() === 'next page') {
      b.onClick = () => { if (state.at < pages.length - 1) { state.at += 1; draw(); } };
      /* The platform's own habit, as Control read it: the next button is switched off on the last page. */
      if (!spec.disabled) Object.defineProperty(b, 'disabled', { get: () => state.at >= pages.length - 1 });
    }
    return b;
  });
  const page = el('div', '', [...extra, table, ...buttons]);
  return { page, table, state, buttons };
}

const noWaiting = () => Promise.resolve();
const PAGER = (n) => [
  { label: 'Previous page' }, ...Array.from({ length: n }, (_, i) => ({ label: `Page ${i + 1}` })), { label: 'Next page' },
];
const thrown = async (work) => { try { await work(); return ''; } catch (wrong) { return String(wrong.message || wrong); } };

/* ---------------------------------------------------------------- the small helpers */

check('the words below an element are its smallest pieces, in order',
  leavesOf(el('td', '', [p('Name'), el('div', '', [p('Catalog ID: 7'), p('4.1')])])).join('|') === 'Name|Catalog ID: 7|4.1');
check('a label is read in its own line', afterTheLabel(['x', 'Catalog ID: 123'], 'Catalog ID:') === '123');
check('or in the piece after it', afterTheLabel(['SKU ID:', 'ABC'], 'SKU ID:') === 'ABC');
check('and a label that is not there gives nothing', afterTheLabel(['x'], 'SKU ID:') === '');
check('a file quotes every cell and doubles a quote inside one',
  theCsv(['a', 'b'], [['x "y"', '2']]) === '"a","b"\n"x ""y""","2"');
check('the four tables are named', THE_TABLES.length === 4 && THE_TABLES.every((one) => theHeaderOf(one).length > 5));

/* ---------------------------------------------------------------- Meesho product performance */

const PERF_HEADERS = ['Product Details', 'Views', 'Clicks', 'Orders', 'Conversions', 'Sales', 'Returns', 'Insights', 'Recommendations'];
const perfRow = (name, id) => [[name, `Catalog ID: ${id}`, '3.9'], ['100', '5%'], ['10'], ['2', '1%'], ['2%', '1%'], ['199'], ['8.6%'], [], []];
const PRINTED = [p("28th Sep '26 - 4th Oct '26"), p('Last updated 4th Oct | 10:39')];

{
  const { page, state, buttons } = aPage({
    headers: PERF_HEADERS,
    pages: [[perfRow('A', '1'), perfRow('B', '2')], [perfRow('C', '3')]],
    extra: PRINTED,
    pager: PAGER(2),
  });
  const got = await readTheTable(page, { table: 'meesho-product-performance', rest: noWaiting });
  const lines = got.csv.split('\n');
  check('EVERY PAGE OF THE TABLE IS READ, in order', got.rows === 3 && got.pages === 2 && state.at === 1);
  check('the file starts with the header the table makes', lines[0] === theHeaderOf('meesho-product-performance').map((x) => `"${x}"`).join(','));
  check('each row carries the days the table covers and when it was updated',
    lines[1].startsWith(`"28th Sep '26 - 4th Oct '26","Last updated 4th Oct | 10:39"`));
  check('and the product, its catalogue id and its rating', lines[1].includes('"A","1","3.9"'));
  check('and each other cell is kept as the page showed it, its pieces joined', lines[1].includes('"100 | 5%"') && lines[1].includes('"2% | 1%"'));
  check('the only buttons pressed were the pager\'s next button',
    buttons.filter((one) => one.clicks).map((one) => one.getAttribute('aria-label')).join() === 'Next page');
}

{
  const { page } = aPage({ headers: PERF_HEADERS, pages: [[perfRow('A', '1')]], extra: [p('no days printed here')], pager: PAGER(1) });
  const why = await thrown(() => readTheTable(page, { table: 'meesho-product-performance', rest: noWaiting }));
  check('A PAGE THAT DOES NOT PRINT ITS DAYS IS REFUSED, since a file would not say what it holds', why.includes('which days'));
}

{
  const { page } = aPage({
    headers: ['Product Details', 'Views', 'Clicks', 'Orders', 'Sales', 'Conversions', 'Returns', 'Insights', 'Recommendations'],
    pages: [[perfRow('A', '1')]], extra: PRINTED, pager: PAGER(1),
  });
  const why = await thrown(() => readTheTable(page, { table: 'meesho-product-performance', rest: noWaiting }));
  check('A TABLE WHOSE COLUMNS HAVE MOVED IS REFUSED, naming the columns it has',
    why.includes('Sales, Conversions') && why.includes('Nothing was read'));
}

{
  /* The pager says 3 pages and the next button runs out after 2: a part of the table, which must never be put away. */
  const { page } = aPage({ headers: PERF_HEADERS, pages: [[perfRow('A', '1')], [perfRow('B', '2')]], extra: PRINTED, pager: PAGER(3) });
  const why = await thrown(() => readTheTable(page, { table: 'meesho-product-performance', rest: noWaiting }));
  check('A RUN OF PAGES THAT STOPS SHORT OF THE PAGER IS REFUSED', why.includes('lists 3 pages and 2 were read'));
}

{
  /* A next button that does nothing. */
  const built = aPage({ headers: PERF_HEADERS, pages: [[perfRow('A', '1')], [perfRow('B', '2')]], extra: PRINTED, pager: PAGER(2) });
  built.buttons.forEach((one) => { one.onClick = null; });
  const why = await thrown(() => readTheTable(built.page, { table: 'meesho-product-performance', rest: noWaiting, patience: 1 }));
  check('A PAGER THAT DID NOT MOVE IS REFUSED rather than read as the same page twice', why.includes('did not draw'));
}

{
  /* **A86 (his 20 Oct run: Meesho pricing, "page 7 did not draw", the page text only the left menu).** Meesho can take the whole
   * content area away while a page loads. A table that is gone gets the whole patience, not the thirty seconds a table that is still
   * there and unchanged gets. `rest` here counts the half-seconds that really pass. */
  const three = () => aPage({
    headers: PERF_HEADERS, pages: [[perfRow('A', '1')], [perfRow('B', '2')], [perfRow('C', '3')]], extra: PRINTED, pager: PAGER(3),
  });
  const built = three();
  const nextButton = built.buttons.find((one) => one.getAttribute('aria-label') === 'Next page');
  const drawn = nextButton.onClick;
  let lateAfter = -1;
  let slept = 0;
  nextButton.onClick = () => {
    if (built.state.at === 1) {
      // the move to the third page takes the content area away, and brings it back 50 seconds later
      built.page.children = built.page.children.filter((one) => one !== built.table);
      lateAfter = slept + 100;
    } else drawn();
  };
  const rest = async () => {
    slept += 1;
    if (slept === lateAfter) {
      built.state.at = 2;
      built.table._kids[1].children = [el('tr', '', [perfRow('C', '3')][0].map((leaves) => el('td', '', leaves.map(p))))];
      built.page.children = [...built.page.children, built.table];
    }
  };
  const got = await readTheTable(built.page, { table: 'meesho-product-performance', rest });
  check('A PAGE THAT TAKES FIFTY SECONDS TO DRAW IS WAITED FOR, not given up on at thirty', got.rows === 3 && got.pages === 3);
  const stuck = three();
  const stuckNext = stuck.buttons.find((one) => one.getAttribute('aria-label') === 'Next page');
  const stuckDraw = stuckNext.onClick;
  stuckNext.onClick = () => { if (stuck.state.at === 1) stuck.page.children = stuck.page.children.filter((one) => one !== stuck.table); else stuckDraw(); };
  const why = await thrown(() => readTheTable(stuck.page, { table: 'meesho-product-performance', rest: noWaiting, patience: 2 }));
  check('A PAGE THAT NEVER DRAWS STILL FAILS THE WHOLE READ, naming the page, with nothing put away',
    why.includes('page 3 did not draw') || why.includes('went from the page'));
}

{
  /* **A86: A PRESS THE PAGE DID NOT HEAR IS MADE AGAIN.** The first press on the way to page 2 does nothing; the second is heard. */
  const built = aPage({ headers: PERF_HEADERS, pages: [[perfRow('A', '1')], [perfRow('B', '2')]], extra: PRINTED, pager: PAGER(2) });
  const nextButton = built.buttons.find((one) => one.getAttribute('aria-label') === 'Next page');
  const heard = nextButton.onClick;
  nextButton.onClick = () => { if (nextButton.clicks > 1) heard(); };
  const said = [];
  const got = await readTheTable(built.page, { table: 'meesho-product-performance', rest: noWaiting, say: (line) => said.push(line) });
  check('A LOST PRESS IS ASKED AGAIN AND THE TABLE IS WHOLE', got.rows === 2 && got.pages === 2 && nextButton.clicks === 2);
  check('and the run says the pager was pressed again', said.some((line) => line.includes('pressed again')));
}

{
  /* **A86: AND IT IS ONLY TWICE MORE** -- a pager that never answers is pressed three times in all, then the read fails. */
  const built = aPage({ headers: PERF_HEADERS, pages: [[perfRow('A', '1')], [perfRow('B', '2')]], extra: PRINTED, pager: PAGER(2) });
  const nextButton = built.buttons.find((one) => one.getAttribute('aria-label') === 'Next page');
  nextButton.onClick = null;
  const why = await thrown(() => readTheTable(built.page, { table: 'meesho-product-performance', rest: noWaiting, patience: 1 }));
  check('A PAGER THAT NEVER ANSWERS IS PRESSED THREE TIMES IN ALL AND THEN FAILS THE READ',
    nextButton.clicks === 3 && why.includes('did not draw'));
}

{
  /* R20 proving: a next button that switched itself off after the first press is not pressed again. */
  const built = aPage({ headers: PERF_HEADERS, pages: [[perfRow('A', '1')], [perfRow('B', '2')]], extra: PRINTED, pager: PAGER(2) });
  const nextButton = built.buttons.find((one) => one.getAttribute('aria-label') === 'Next page');
  nextButton.onClick = null;
  Object.defineProperty(nextButton, 'disabled', { get: () => nextButton.clicks >= 1 });
  await thrown(() => readTheTable(built.page, { table: 'meesho-product-performance', rest: noWaiting, patience: 1 }));
  check('a pager button that has switched itself off is never pressed again (R20 proving)', nextButton.clicks === 1);
}

{
  /* **A86: FLIPKART'S PAGER, WHICH NAMES NO PAGES, ENDS BY NOT MOVING AND IS NEVER PRESSED AGAIN** -- three waits at the real end of a
   * table would be a minute and a half for nothing. */
  const { page, buttons } = aPage({
    headers: ['', 'Product Details', 'Yearly Sales', '1Y Ratings Trend', '5M Returns Trend', 'FA', 'Suppression Risk', 'Issue Details', ''],
    pages: [[[[], ['P', 'SKU ID:', 'S-1'], ['1'], ['2'], ['3'], [], ['No Risk'], ['x'], []]], [[[], ['Q', 'SKU ID:', 'S-2'], ['1'], ['2'], ['3'], [], ['No Risk'], ['x'], []]]],
    tableText: 'Suppression Risk', pager: [{ label: 'Next Page' }],
  });
  const next = buttons[0];
  Object.defineProperty(next, 'disabled', { get: () => false });
  next.onClick = null;
  const got = await readTheTable(page, { table: 'flipkart-quality-insights', rest: noWaiting, patience: 1 });
  check('a pager with no page numbers is pressed once and ends the table when it does not move', got.rows === 1 && next.clicks === 1);
}

{
  const { page } = aPage({ headers: PERF_HEADERS, pages: [[[['x'], ['1']]]], extra: PRINTED, pager: PAGER(1) });
  const why = await thrown(() => readTheTable(page, { table: 'meesho-product-performance', rest: noWaiting }));
  check('a row with the wrong number of cells refuses the read, never a part of the table', why.includes('not the shape of the table'));
}

{
  const why = await thrown(() => readTheTable(el('div', ''), { table: 'meesho-product-performance', rest: noWaiting, patience: 1 }));
  check('a page with no such table never appears, and says so', why.includes('never appeared'));
  check('a table that is not one of the three is refused', (await thrown(() => readTheTable(el('div', ''), { table: 'nope' }))).includes('not a table'));
}

{
  /* A pager that wraps round to the first page must not be read as more of the table. */
  const { page } = aPage({ headers: PERF_HEADERS, pages: [[perfRow('A', '1')], [perfRow('B', '2')], [perfRow('A', '1')]],
    extra: PRINTED, pager: PAGER(4) });
  const why = await thrown(() => readTheTable(page, { table: 'meesho-product-performance', rest: noWaiting }));
  check('A PAGE SHOWING AN EARLIER FIRST ROW AGAIN IS REFUSED', why.includes('same first row'));
}

{
  const { page } = aPage({ headers: PERF_HEADERS, pages: [[]], extra: PRINTED, pager: PAGER(1) });
  const why = await thrown(() => readTheTable(page, { table: 'meesho-product-performance', rest: noWaiting }));
  check('a table with no rows is refused, never put away as an empty day', why.includes('no rows'));
}

{
  /* The platform keeps its next button on after the last page; the named pages say when to stop. */
  const built = aPage({ headers: PERF_HEADERS, pages: [[perfRow('A', '1')], [perfRow('B', '2')]], extra: PRINTED, pager: PAGER(2) });
  built.buttons.forEach((one) => { if (one.getAttribute('aria-label') === 'Next page') Object.defineProperty(one, 'disabled', { get: () => false }); });
  const got = await readTheTable(built.page, { table: 'meesho-product-performance', rest: noWaiting });
  check('A PAGER THAT NAMES ITS PAGES STOPS AT THE LAST NAMED ONE even when its next button stays on',
    got.pages === 2 && got.rows === 2 && built.buttons.filter((one) => one.getAttribute('aria-label') === 'Next page')[0].clicks === 1);
}

{
  /* A pager drawn after its table must not make a one-page read look complete. */
  const { page } = aPage({ headers: PERF_HEADERS, pages: [[perfRow('A', '1')]], extra: PRINTED, pager: [{ label: 'Next page' }] });
  const why = await thrown(() => readTheTable(page, { table: 'meesho-product-performance', rest: noWaiting }));
  check('A PAGER WITH NO PAGE NUMBERS ON A TABLE THAT HAS THEM IS REFUSED, not read as one page', why.includes('page numbers never appeared'));
}

{
  const make = (count) => aPage({ headers: PERF_HEADERS, pages: [[perfRow('A', '1'), perfRow('B', '2')]], extra: [...PRINTED, p(`All (${count})`)], pager: PAGER(1) });
  const whole = await readTheTable(make(2).page, { table: 'meesho-product-performance', rest: noWaiting });
  check('the page count of everything agrees with the rows read', whole.rows === 2);
  const why = await thrown(() => readTheTable(make(142).page, { table: 'meesho-product-performance', rest: noWaiting }));
  check('A COUNT THAT DISAGREES WITH THE ROWS READ REFUSES THE FILE (a filtered tab, or a short read)', why.includes('counts 142 in all and 2 rows'));
}

/* ---------------------------------------------------------------- Meesho pricing */

const PRICE_HEADERS = ['', 'Product Details', 'Current Stock', 'Growth in 30 days', 'Current Customer Price',
  'Recommended Customer Price', 'Insights', 'Action'];
const priceRow = (name, id, sku, label) => [[], [name, `Catalog ID: ${id}`, `SKU ID: ${sku}`, 'Size: Free'], ['5'], ['3%'],
  ['₹199', 'Margin: ₹100'], ['₹179', 'Margin: ₹80'], [label], ['Accept', 'Edit']];

{
  const { page, buttons } = aPage({
    headers: PRICE_HEADERS,
    pages: [[priceRow('A', '1', 'S-1', 'Losing Views')], [priceRow('B', '2', 'S-2', 'Best Priced')]],
    extra: [p('Losing Orders (0)'), p('Losing Views (48)'), p('Best Priced (106)'), el('button', 'Bulk Price Update')],
    pager: PAGER(2),
  });
  const got = await readTheTable(page, { table: 'meesho-pricing', rest: noWaiting });
  const lines = got.csv.split('\n');
  check('PRICING: both pages are read', got.rows === 2 && got.pages === 2);
  check('the product, catalogue id and SKU are separated', lines[1].startsWith('"A","1","S-1"'));
  check('the tab counts the page shows go on every row', lines[1].includes('Losing Orders (0); Losing Views (48); Best Priced (106)'));
  check('both prices are kept with their margins, and the label', lines[1].includes('199 | Margin') && lines[1].includes('"Losing Views"'));
  check('THE ACTION CELL (Accept, Edit) IS NOT IN THE FILE', !got.csv.includes('Accept') && !got.csv.includes('Edit'));
  check('and nothing but the pager was pressed: not the bulk update button',
    page.children.filter((one) => one.clicks).length === 1 && buttons.filter((one) => one.clicks).length === 1);
}

/* ---------------------------------------------------------------- Flipkart quality insights */

const QI_HEADERS = ['', 'Product Details', 'Yearly Sales', '1Y Ratings Trend', '5M Returns Trend', 'FA', 'Suppression Risk', 'Issue Details', ''];
const qiRow = (name, sku, badge) => [[], [name, 'SKU ID:', sku], ['₹1.2L'], ['4.1'], ['12.3%'],
  badge ? el('td', '', [el('img', '')]) : [], ['No Risk'], ['Quality'], []];

{
  const { page } = aPage({
    headers: QI_HEADERS, tableText: 'Suppression Risk',
    pages: [[qiRow('A', 'S-1', true), qiRow('B', 'S-2', false)], [qiRow('C', 'S-3', true)]],
    pager: [{ label: 'Previous Page' }, { label: 'Next Page' }],
  });
  const got = await readTheTable(page, { table: 'flipkart-quality-insights', rest: noWaiting });
  const lines = got.csv.split('\n');
  check('QUALITY: pages are read until the next button is spent (no page numbers on this pager)', got.rows === 3 && got.pages === 2);
  check('the product and its SKU, where the label stands apart from the value', lines[1].startsWith('"A","S-1"'));
  check('the assured badge is yes when the picture is there and no when it is not',
    lines[1].includes('"Yes"') && lines[2].includes('"No"'));
  check('sales stay as the page wrote them, lakh shorthand and all', lines[1].includes('1.2L'));
}

{
  const { page } = aPage({
    headers: QI_HEADERS, tableText: 'Suppression Risk', pages: [[qiRow('A', 'S-1', true)]],
    pager: [{ label: 'Previous Page' }, { label: 'Next Page', disabled: true }],
  });
  const got = await readTheTable(page, { table: 'flipkart-quality-insights', rest: noWaiting });
  check('a next button that is switched off ends the read', got.pages === 1 && got.rows === 1);
}

{
  /* Flipkart's pager has no page numbers: a next button that stays on and moves nothing is the end. */
  const built = aPage({ headers: QI_HEADERS, tableText: 'Suppression Risk', pages: [[qiRow('A', 'S-1', true)], [qiRow('B', 'S-2', true)]],
    pager: [{ label: 'Previous Page' }, { label: 'Next Page' }] });
  built.buttons.forEach((one) => { if (one.getAttribute('aria-label') === 'Next Page') Object.defineProperty(one, 'disabled', { get: () => false }); });
  const got = await readTheTable(built.page, { table: 'flipkart-quality-insights', rest: noWaiting });
  check('A NEXT BUTTON THAT STAYS ON AND MOVES NOTHING ENDS A PAGER WITH NO PAGE NUMBERS, every row kept', got.rows === 2 && got.pages === 2);
}

check('a title that begins like a formula is made plain text, and a figure with a sign is left alone',
  plain('=HYPERLINK("x")') === "'=HYPERLINK(\"x\")" && plain('@SUM(1)') === "'@SUM(1)" && plain('-cmd') === "'-cmd"
  && plain('-3%') === '-3%' && plain('+4') === '+4' && plain('\u20B9199') === '\u20B9199' && plain('Ring') === 'Ring');
check('and the file carries the guard', theCsv(['a'], [['=1+1']]).split('\n')[1] === `"'=1+1"`);
check('A SIGN FOLLOWED BY A DIGIT IS ONLY LEFT ALONE WHEN THE WHOLE CELL IS A FIGURE (the AJ2 security read): -1+1 and +1+cmd are still formulas',   plain('-1+1') === "'-1+1" && plain('+1+cmd|x') === "'+1+cmd|x" && plain('-.5') === '-.5' && plain('-1,250.50') === '-1,250.50' && plain('+₹1,199') === '+₹1,199' && plain('-12.5%') === '-12.5%');

{
  /* The names the recipes ask for and the names this reads must be the same list, so a drift reads red here. */
  const book = JSON.parse(readFileSync(new URL('./recipes.json', import.meta.url), 'utf8'));
  const asked = new Set();
  Object.values(book.recipes).forEach((r) => [...r.toAsk, ...r.toTake].forEach((one) => { if (one.table) asked.add(one.table); }));
  check('EVERY TABLE A RECIPE ASKS FOR IS ONE THIS READS, AND EVERY ONE THIS READS IS ASKED FOR',
    [...asked].sort().join() === [...THE_TABLES].sort().join());
}

/* ---------------------------------------------------------------- the faults of 15 Oct (A84) */

{
  /* **A84, FAULT 1: a real page's `children` has no `forEach`.** Every other check here hands `children` a plain list. */
  El.realistic = true;
  const { page } = aPage({ headers: PERF_HEADERS, pages: [[perfRow('A', '1')]], extra: PRINTED, pager: PAGER(1) });
  const got = await readTheTable(page, { table: 'meesho-product-performance', rest: noWaiting });
  El.realistic = false;
  check('A84: A PAGE WHOSE CHILDREN ARE AN HTMLCollection (NO forEach) IS READ, not refused with "kids.forEach is not a function"',
    got.rows === 1 && got.csv.split('\n')[1].includes('"A","1","3.9"'));
  check('and the same words are read when the leaves are asked for directly',
    (() => { El.realistic = true; const out = leavesOf(el('td', '', [p('Name'), el('div', '', [p('x')])])).join('|'); El.realistic = false; return out === 'Name|x'; })());
}

{
  /* **A84, FAULT 2: Meesho's header cell now reads "Growthin 30 days" (its words run together).** Both spellings are the one column. */
  const joinedHeaders = PRICE_HEADERS.map((one) => (one === 'Growth in 30 days' ? 'Growthin 30 days' : one));
  const { page } = aPage({
    headers: joinedHeaders, pages: [[priceRow('A', '1', 'S-1', 'Losing Views')]],
    extra: [p('Losing Orders (0)'), p('Losing Views (1)'), p('Best Priced (0)')], pager: PAGER(1),
  });
  const got = await readTheTable(page, { table: 'meesho-pricing', rest: noWaiting });
  check('A84: PRICING WITH "Growthin 30 days" IS READ, and the file still names the column the old way', got.rows === 1
    && got.csv.split('\n')[0].includes('"Growth in 30 days"'));
  const other = PRICE_HEADERS.map((one) => (one === 'Growth in 30 days' ? 'Growt hin 30 days' : one));
  const why = await thrown(() => readTheTable(aPage({
    headers: other, pages: [[priceRow('A', '1', 'S-1', 'x')]], extra: [p('All Products (1)')], pager: PAGER(1),
  }).page, { table: 'meesho-pricing', rest: noWaiting }));
  check('and any other spelling is still refused, naming the columns it has', why.includes('not the ones expected') && why.includes('Growt hin'));
}

{
  /* **A84, FAULT 3: Flipkart's tick-box header cell now carries its icon's name as words.** */
  const iconHeaders = QI_HEADERS.map((one, at) => (at === 0 ? 'CheckBoxOutlineBlank' : one));
  const { page } = aPage({
    headers: iconHeaders, tableText: 'Suppression Risk', pages: [[qiRow('A', 'S-1', true)]],
    pager: [{ label: 'Previous Page' }, { label: 'Next Page', disabled: true }],
  });
  const got = await readTheTable(page, { table: 'flipkart-quality-insights', rest: noWaiting });
  check('A84: QUALITY WITH THE TICK-BOX CELL READING "CheckBoxOutlineBlank" IS READ', got.rows === 1 && got.csv.split('\n')[1].startsWith('"A","S-1"'));
  const why = await thrown(() => readTheTable(aPage({
    headers: QI_HEADERS.map((one, at) => (at === 0 ? 'SomethingElseIcon' : one)), tableText: 'Suppression Risk',
    pages: [[qiRow('A', 'S-1', true)]], pager: [{ label: 'Previous Page' }, { label: 'Next Page', disabled: true }],
  }).page, { table: 'flipkart-quality-insights', rest: noWaiting }));
  check('and any other word in that cell is still refused', why.includes('not the ones expected') && why.includes('SomethingElseIcon'));
}

{
  /* **ROWS THAT ARE STILL DRAWING WHEN THE PAGE'S FIRST ROW CHANGES (his Meesho run of 27 Oct 2026: 25, 24, 25, 20, 16, 20 rows on pages of 25, the page counting 159).** A new page is known to have come by its first row
   * changing, and the rest of its rows can still be arriving; a read taken that instant is a short page. The page is read once its rows have stopped arriving. */
  const rows = (names) => names.map((n) => priceRow(n, n, `S-${n}`, 'Best Priced'));
  const built = aPage({ headers: PRICE_HEADERS, pages: [rows(['A', 'B', 'C']), rows(['D', 'E', 'F'])], extra: [p('All Products (6)'), p('Losing Orders (0)')], pager: PAGER(2) });
  const body = built.table.children[1];
  const next = built.buttons.find((one) => one.getAttribute('aria-label') === 'Next page');
  const original = next.onClick;
  const stillComing = [];
  next.onClick = () => {
    original();
    stillComing.push(...body.children.slice(1));
    body.children = body.children.slice(0, 1);
  };
  const arriving = async () => { if (stillComing.length) body.children = [...body.children, stillComing.shift()]; };
  const got = await readTheTable(built.page, { table: 'meesho-pricing', rest: arriving });
  check('A PAGE WHOSE ROWS ARE STILL ARRIVING IS READ WHOLE, once they have stopped, never as a short page', got.rows === 6 && got.pages === 2);
}

{
  /* **A NEXT BUTTON THAT IS SWITCHED OFF WHILE THE PAGER STILL NAMES MORE PAGES IS WAITED FOR (his Meesho run of 27 Oct 2026: "7 pages and 6 were read" every night).** Meesho switches the button off while a page
   * is still loading; a read that takes it for the end of the table stops one page short. It is given time to come on again before it is believed. */
  const rows = (names) => names.map((n) => priceRow(n, n, `S-${n}`, 'Best Priced'));
  const built = aPage({ headers: PRICE_HEADERS, pages: [rows(['A']), rows(['B']), rows(['C'])], extra: [p('All Products (3)'), p('Losing Orders (0)')], pager: PAGER(3) });
  const next = built.buttons.find((one) => one.getAttribute('aria-label') === 'Next page');
  let loading = 0;
  Object.defineProperty(next, 'disabled', { get: () => loading > 0 || built.state.at >= 2 });
  const original = next.onClick;
  next.onClick = () => { original(); if (built.state.at === 1) loading = 4; };
  const slow = async () => { if (loading > 0) loading -= 1; };
  const got = await readTheTable(built.page, { table: 'meesho-pricing', rest: slow });
  check('A NEXT BUTTON SWITCHED OFF FOR A MOMENT WHILE MORE PAGES ARE NAMED IS WAITED FOR, never read as the end of the table', got.rows === 3 && got.pages === 3);
}

{
  /* **"STOPPED ARRIVING" MEANS THE SAME COUNT TWICE RUNNING, NOT ONCE (the fresh review of 27 Oct 2026):** rows that pause for one look and then arrive are still read whole. */
  const rows = (names) => names.map((n) => priceRow(n, n, `S-${n}`, 'Best Priced'));
  const built = aPage({ headers: PRICE_HEADERS, pages: [rows(['A', 'B', 'C']), rows(['D', 'E', 'F'])], extra: [p('All Products (6)'), p('Losing Orders (0)')], pager: PAGER(2) });
  const body = built.table.children[1];
  const next = built.buttons.find((one) => one.getAttribute('aria-label') === 'Next page');
  const original = next.onClick;
  const stillComing = [];
  let looks = 0;
  next.onClick = () => {
    original();
    stillComing.push(...body.children.slice(1));
    body.children = body.children.slice(0, 1);
    looks = 0;
  };
  const withAPause = async () => {
    looks += 1;
    if (stillComing.length && looks !== 2) body.children = [...body.children, stillComing.shift()];
  };
  const got = await readTheTable(built.page, { table: 'meesho-pricing', rest: withAPause });
  check('ROWS THAT PAUSE FOR ONE LOOK AND THEN ARRIVE ARE STILL READ WHOLE, the same count being needed twice running', got.rows === 6 && got.pages === 2);
}

{
  /* **N017 (his D726; the run logs of 22-25 Oct): "the pager lists 7 pages and 6 were read" EVERY NIGHT.** The pager names a page the table does not have
   * (or whose button is switched off), and the page's own count of everything is the last word on whether the table is whole. */
  const short = (count) => aPage({
    headers: PRICE_HEADERS, pages: [[priceRow('A', '1', 'S-1', 'Losing Views')], [priceRow('B', '2', 'S-2', 'Best Priced')]],
    extra: [p(`All Products (${count})`), p('Losing Orders (0)')], pager: PAGER(3),
  });
  const said = [];
  const got = await readTheTable(short(2).page, { table: 'meesho-pricing', rest: noWaiting, say: (line) => said.push(line) });
  check('N017: A PAGER THAT NAMES ONE PAGE TOO MANY IS WHOLE WHEN THE PAGE\'S OWN COUNT EQUALS THE ROWS READ', got.rows === 2 && got.pages === 2);
  check('and the run says the pager named more pages than there were', said.some((line) => line.includes('lists 3 pages') && line.includes('2 in all')));
  const why = await thrown(() => readTheTable(short(3).page, { table: 'meesho-pricing', rest: noWaiting }));
  check('N017: BUT A COUNT THE ROWS DO NOT REACH STILL REFUSES THE READ, saying the rows each page gave and the count',
    why.includes('lists 3 pages and 2 were read') && why.includes('1, 1') && why.includes('counts 3 in all'));
  const noCount = aPage({
    headers: PRICE_HEADERS, pages: [[priceRow('A', '1', 'S-1', 'x')], [priceRow('B', '2', 'S-2', 'y')]], extra: [p('Losing Orders (0)')], pager: PAGER(3),
  });
  const why2 = await thrown(() => readTheTable(noCount.page, { table: 'meesho-pricing', rest: noWaiting }));
  check('N017: A PAGE THAT PRINTS NO COUNT CANNOT EXCUSE A SHORT PAGER', why2.includes('lists 3 pages and 2 were read') && why2.includes('prints no count'));
  /* **A SHORT READ SAYS WHAT THE PAGER LOOKED LIKE AND WHY THE READ STOPPED (his Meesho run of 27 Oct 2026: "7 pages and 6 were read" with no way to tell whether the next button was gone, switched off, or never pressed).** */
  check('and a short read says why it stopped and what the pager buttons were, so the next run shows the cause',
    why2.includes('stopped because') && why2.includes('the pager showed') && why2.includes('Page 3'));
}

/* ---------------------------------------------------------------- Meesho's QUALITY page (N025, his Product Quality page, seen 26 Oct 2026; every figure here is made up)
 * **THE PAGE'S SHAPE IS FROM HIS OWN PANEL:** a store block (`Quality Score`, `1 and 2 star ratings` and a number, `Total Ratings` and a number, a percentage and a band in brackets), `Top Customer Feedback` reasons each with
 * `N products`, three tab buttons (`role="tab"`) `Blocking Soon (n)`, `Action Pending (n)`, `Fixed (n)`, and, for the chosen tab, one block per product: its name, `Style ID: ...`, a band word, `(19.7%)` and reasons
 * `Color is not good (5 ratings)`. The products shown change with the tab, so each tab is pressed and read. */
function aQualityPage({ tabs, products, store = true, reasons = true }) {
  const state = { tab: 0 };
  const list = el('div', '');
  const draw = () => {
    list.children = (products[tabs[state.tab].name] || []).flatMap((one) => [
      el('p', one.name), el('p', `Style ID: ${one.style}`), el('h5', one.band), el('h5', `(${one.pct}%)`),
      ...(one.reasons || []).map((r) => el('p', r)), el('p', 'View all customer feedback'), el('p', 'No listing improvements needed.'), el('button', 'Save'),
    ]);
  };
  draw();
  const buttons = tabs.map((one, at) => {
    const b = el('button', `${one.name} (${one.count})`, [], { role: 'tab' });
    b.onClick = () => { state.tab = at; draw(); };
    return b;
  });
  const top = [el('h1', 'Product Quality'), el('p', 'Quality Score')];
  if (store) top.push(el('p', '1 and 2 star ratings'), el('p', '46'), el('p', 'Total Ratings'), el('p', '307'), el('p', '15.0%'), el('p', '15.0%'), el('p', '(Good)'));
  top.push(el('p', 'Top Customer Feedback'));
  if (reasons) top.push(el('p', 'Color is not good'), el('p', '2 products'), el('p', 'View Products'), el('p', 'Design is not good'), el('p', '1 product'), el('p', 'View Products'));
  const page = el('div', '', [...top, el('p', 'Quality Recommendations'), ...buttons,
    el('p', 'Product Details and Quality Score'), el('p', 'Top Customer Feedback'), el('p', 'Product Listing Improvements'), el('p', 'Action'), list, el('p', 'SAH Shipping Estimate')]);
  return { page, state };
}
const THE_QUALITY_TABS = [{ name: 'Blocking Soon', count: 0 }, { name: 'Action Pending', count: 2 }, { name: 'Fixed', count: 1 }];
const THE_QUALITY_PRODUCTS = {
  'Action Pending': [
    { name: 'Traditional Jhumka Earrings ...', style: 'DJ-5 Test Five', band: 'Yellow', pct: '19.7', reasons: ['Color is not good (5 ratings)', 'Size is not proper (4 ratings)'] },
    { name: '=Ethnic Drops ...', style: 'DJ-6 Test Six', band: 'Green', pct: '12', reasons: ['Size is not proper (5 ratings)'] },
  ],
  Fixed: [{ name: 'Gold Hoops ...', style: 'DJ-7 Test Seven', band: 'Green', pct: '3.5', reasons: [] }],
};
{
  const { page } = aQualityPage({ tabs: THE_QUALITY_TABS, products: THE_QUALITY_PRODUCTS });
  const got = await readTheTable(page, { table: 'meesho-quality', patience: 1, rest: noWaiting });
  const lines = got.csv.split('\n');
  check('THE QUALITY PAGE IS READ INTO ONE FILE: its header is kind, tab, name, style id, band, percent, count and detail',
    lines[0] === '"Kind","Tab","Name","Style ID","Band","Percent","Count","Detail"');
  check('the store line carries the score as a percentage, its band, the total ratings and the low ratings in words',
    lines.includes('"store","","Quality score","","Good","15.0","307","46 of 307 ratings were 1 or 2 stars"'));
  check('every top customer feedback reason is a line with its number of products',
    lines.includes('"feedback","","Color is not good","","","","2",""') && lines.includes('"feedback","","Design is not good","","","","1",""'));
  check('each tab is a line with its count, including the one with none',
    lines.includes('"tab","Blocking Soon","","","","","0",""') && lines.includes('"tab","Action Pending","","","","","2",""') && lines.includes('"tab","Fixed","","","","","1",""'));
  check('EVERY PRODUCT OF EVERY TAB IS A LINE with its tab, name, style id, band, percent and its reasons with their counts, the tabs pressed one after another',
    lines.includes('"product","Action Pending","Traditional Jhumka Earrings ...","DJ-5 Test Five","Yellow","19.7","9","Color is not good (5 ratings) | Size is not proper (4 ratings)"')
    && lines.includes('"product","Action Pending","\'=Ethnic Drops ...","DJ-6 Test Six","Green","12","5","Size is not proper (5 ratings)"')
    && lines.includes('"product","Fixed","Gold Hoops ...","DJ-7 Test Seven","Green","3.5","0",""'));
  check('and a title that begins like a formula is made plain text', !lines.some((one) => one.includes('"=Ethnic')));
  check('the answer says how many lines it holds', got.rows === lines.length - 1 && got.rows === 1 + 2 + 3 + 3);
}
{
  const { page } = aQualityPage({ tabs: THE_QUALITY_TABS, products: THE_QUALITY_PRODUCTS, store: false });
  const why = await thrown(() => readTheTable(page, { table: 'meesho-quality', patience: 1, rest: noWaiting }));
  check('a page with no store score is refused in words, nothing put away', why.includes('store') && why.includes('Nothing was read'));
}
{
  const { page } = aQualityPage({ tabs: [{ name: 'Blocking Soon', count: 0 }, { name: 'Action Pending', count: 3 }, { name: 'Fixed', count: 1 }], products: THE_QUALITY_PRODUCTS });
  const why = await thrown(() => readTheTable(page, { table: 'meesho-quality', patience: 1, rest: noWaiting }));
  check('A TAB THAT SAYS THREE AND SHOWS TWO IS REFUSED: the page\'s own count is the last word on whether the whole list was read',
    why.includes('Action Pending') && why.includes('nothing was put away'));
}
{
  const bare = el('div', '', [el('p', 'Welcome')]);
  const why = await thrown(() => readTheTable(bare, { table: 'meesho-quality', patience: 1, rest: noWaiting }));
  check('a page that is not the quality page never gets a file made of it', why.includes('Product Quality') && why.includes('nothing was read'));
}

/* ---------------------------------------------------------------- Amazon's settlement statements (N018)
 * **THE ROW WORDS ARE FROM HIS OWN ALL STATEMENTS PAGE, 26 Oct 2026** (the figures here are made up): one row per weekly statement, the period written day first with no noughts and an en dash --
 * `13/10/2026 – 20/10/2026`, `6/10/2026 – 13/10/2026`, `29/9/2026 – 6/10/2026` -- and the open one `20/10/2026 – Present`, which has no Download. */
{
  const closed = theStatementPeriod('13/10/2026 – 20/10/2026 View summary ₹0.00 ₹6,491.00 -₹1,110.95 Download Flat File V2');
  check('a closed statement row gives its period as written and the day it ENDED, in ISO',
    closed !== null && closed.period === '13/10/2026 – 20/10/2026' && closed.start === '2026-10-13' && closed.end === '2026-10-20');
  const crossing = theStatementPeriod('29/9/2026 – 6/10/2026 View summary');
  check('a period with no noughts, crossing a month, reads the same way',
    crossing !== null && crossing.start === '2026-09-29' && crossing.end === '2026-10-06');
  check('a period written with a hyphen or spaces broken by the page is still read, and the words are kept as the page spaces them',
    theStatementPeriod('6/10/2026\n -  13/10/2026').end === '2026-10-13' && theStatementPeriod('6/10/2026\n -  13/10/2026').period === '6/10/2026 - 13/10/2026');
  check('the open statement, which runs to "Present", is not a period at all', theStatementPeriod('20/10/2026 – Present Available after settlement close') === null);
  check('a row with no period, an impossible day, or an end before its start is nothing',
    theStatementPeriod('View summary') === null && theStatementPeriod('31/2/2026 – 6/3/2026') === null && theStatementPeriod('20/10/2026 – 13/10/2026') === null);
}

/* ---------------------------------------------------------------- Meesho product quality (the proving survivors of the AJ2 join)
 * **A PAGE MADE OF ITS WORDS, AS THE REAL ONE IS READ:** the heading, the store score, the customer feedback, three tabs (drawn a while after the page opens), and under the tab pressed, the products with their
 * band and reasons. Every word and figure is made up. What is checked is what the read does with a page that is wrong in one small way. */
/* A read that throws is a FAILED check here, never a crash of the whole file. */
const orNothing = (work) => work().catch(() => ({ csv: '', rows: 0, pages: 0 }));
const QUALITY_HEADER = '"Kind","Tab","Name","Style ID","Band","Percent","Count","Detail"';
/* A year written with four figures that is really a year of the last century to a Date (0026 is 1926) is not a real day: nothing is guessed. */
check('a statement whose year is one a date would quietly move is nothing, not a day filed under a made-up year',
  theStatementPeriod('1/1/0026 – 2/1/0026') === null);
const aMeeshoQualityPage = ({
  tabs = [{ name: 'Blocking Soon', products: ['a', 'b'] }, { name: 'Action Pending', products: ['c'] }, { name: 'Fixed', products: [] }],
  store = ['1 and 2 star ratings', '12', 'Total Ratings', '400', '3%', '(Good)', 'Something else'],
  feedback = ['Top Customer Feedback', 'Poor fit', '5 products', 'Colour differs', '2 products', 'Quality Recommendations'],
  withRoles = true, extraButtons = [], drawnAfter = 0,
} = {}) => {
  const state = { at: -1, drawn: drawnAfter === 0 };
  const page = el('div', '');
  const buttons = tabs.map((one, at) => {
    const b = el('button', `${one.name} (${one.products.length})`, [], withRoles ? { role: 'tab' } : {});
    b.onClick = () => { state.at = at; redraw(); };
    return b;
  });
  const productLeaves = (name) => [p(`Product ${name}`), p(`Style ID: S-${name}`), p('Red'), p('(12.5%)'), p('Poor fit (4 ratings)'), p('Torn (1 rating)')];
  function redraw() {
    const shown = state.at < 0 ? [] : tabs[state.at].products.flatMap(productLeaves);
    page.children = [
      p('Product Quality'), ...store.map(p), ...feedback.map(p),
      ...(state.drawn ? buttons : []), ...extraButtons,
      p('Action'), ...shown, p('SAH Shipping Estimate'),
    ];
  }
  redraw();
  const draw = () => { state.drawn = true; redraw(); };
  return { page, draw, buttons };
};

{
  const built = aMeeshoQualityPage({ drawnAfter: 2 });
  const slept = [];
  const said = [];
  let calls = 0;
  const rest = async (ms) => { slept.push(ms); calls += 1; if (calls === 2) built.draw(); };
  const got = await orNothing(() => readTheTable(built.page, { table: 'meesho-quality', rest, say: (line) => said.push(line) }));
  const lines = got.csv.split('\n');
  check('QUALITY: a page whose tabs draw late is waited for a second at a time, and then every tab is pressed after a half-second and read after a second and a half',
    JSON.stringify(slept) === JSON.stringify([1000, 1000, 500, 1500, 500, 1500, 500, 1500]));
  check('and the store score, the feedback, the three tabs and their products are all in the file',
    got.pages === 3 && got.rows === 1 + 2 + 3 + 3 && lines[0] === QUALITY_HEADER && lines[1].includes('"store"') && lines[1].includes('"Good","3","400"')
    && lines.filter((one) => one.startsWith('"feedback"')).length === 2 && lines.filter((one) => one.startsWith('"product"')).length === 3
    && lines.some((one) => one.startsWith('"product","Blocking Soon","Product a","S-a","Red","12.5","5","Poor fit (4 ratings) | Torn (1 rating)"')));
  check('and it says how much it read', said.length === 1 && said[0] === 'meesho-quality: read the store score, 3 tabs and 3 products.');
}

{
  const two = aMeeshoQualityPage({ tabs: [{ name: 'Blocking Soon', products: [] }, { name: 'Fixed', products: [] }] });
  const why = await thrown(() => readTheTable(two.page, { table: 'meesho-quality', rest: noWaiting, patience: 1 }));
  check('QUALITY: a page with only two of the three tabs is refused in words, never read as the whole', why.includes('were not all on the page (2 found)') && why.includes('nothing was read'));
  const crowded = aMeeshoQualityPage({
    extraButtons: [el('button', 'Fixed (3)'), el('button', 'Somewhere else', [], { role: 'tab' })],
  });
  const got = await orNothing(() => readTheTable(crowded.page, { table: 'meesho-quality', rest: noWaiting, patience: 1 }));
  check('and a button that says a tab\'s words without being a tab, or is a tab with other words, is not counted as one', got.pages === 3);
}

{
  const refused = async (store) => thrown(() => readTheTable(aMeeshoQualityPage({ store }).page, { table: 'meesho-quality', rest: noWaiting, patience: 1 }));
  const NOT_THERE = 'the store quality score';
  check('QUALITY: no low-ratings count beside its label is refused, the rest of the score being there',
    (await refused(['1 and 2 star ratings', 'n/a', 'Total Ratings', '400', '3%', '(Good)'])).includes(NOT_THERE));
  check('and no total beside its label is refused, the rest being there',
    (await refused(['1 and 2 star ratings', '12', 'Total Ratings', 'n/a', '3%', '(Good)'])).includes(NOT_THERE));
  check('and a percentage with no band beside it is refused too',
    (await refused(['1 and 2 star ratings', '12', 'Total Ratings', '400', '3%'])).includes(NOT_THERE));
  check('while the whole score is read', (await refused(['1 and 2 star ratings', '12', 'Total Ratings', '400', '3%', '(Good)'])) === '');
}

{
  const feedbackRows = async (feedback, around = []) => {
    const built = aMeeshoQualityPage({ feedback, tabs: [{ name: 'Blocking Soon', products: [] }, { name: 'Action Pending', products: [] }, { name: 'Fixed', products: [] }] });
    built.page.children = [...around.map(p), ...built.page.children];
    const got = await orNothing(() => readTheTable(built.page, { table: 'meesho-quality', rest: noWaiting, patience: 1 }));
    return got.csv.split('\n').filter((one) => one.startsWith('"feedback"'));
  };
  check('QUALITY: feedback is each reason with its count of products', (await feedbackRows(['Top Customer Feedback', 'Poor fit', '5 products', 'Quality Recommendations'])).length === 1);
  check('and with no feedback heading nothing before the recommendations is taken for feedback, even a count of products',
    (await feedbackRows(['Quality Recommendations'], ['Stray reason', '7 products'])).length === 0);
  check('and with no recommendations heading nothing after the feedback heading is taken for feedback',
    (await feedbackRows(['Top Customer Feedback', 'Poor fit', '5 products', 'Colour differs', '2 products'])).length === 0);}

console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
const EXPECTED = 52 + 1 + 4 + 5 + 10 + 1 + 3 + 2 + 4 + 3 + 1 + 1 + 1 + 1 + 1;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  process.exit(1);
}
process.exit(failures ? 1 : 0);
