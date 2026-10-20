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
import { THE_TABLES, afterTheLabel, leavesOf, plain, readTheTable, theCsv, theHeaderOf } from './tables.js';

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
check('the three tables are named', THE_TABLES.length === 3 && THE_TABLES.every((one) => theHeaderOf(one).length > 5));

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

console.log(failures ? `\n${failures} FAILED (${ran} checks)` : `\nall ${ran} checks passed`);
const EXPECTED = 52;
if (ran !== EXPECTED) {
  console.log(`FAIL  checks went missing -- ${ran} ran, ${EXPECTED} expected`);
  process.exit(1);
}
process.exit(failures ? 1 : 0);
