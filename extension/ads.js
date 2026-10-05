/* The Meesho ads sweep: the one report that is asked for rather than pressed.
 *
 * **WHY THIS FILE EXISTS AT ALL.** Every other report in this product is a file a
 * platform hands over when the right thing is pressed. **Meesho's ads figures are
 * not a file anywhere.** They come from two of Meesho's own addresses, called
 * from inside the seller's signed-in page: a list of campaigns, ten at a time,
 * and then one call per campaign for a day's numbers. Three CSVs are built out of
 * what comes back.
 *
 * **THE SELLER IS NEVER WRITTEN DOWN. HIS INSTRUCTION, 2026-09-11:** *"make sure
 * it is not hard coded to any one seller... it should be able to handle the multi
 * seller thing."* Both things those addresses need come from cookies Meesho sets
 * for whoever is signed in. **The reference hard-codes one seller's slug**
 * (`config.js:11`, a constant holding one real panel name) and finds the numeric
 * id by scraping localStorage KEY NAMES -- **which returns nothing at all on that
 * same seller's panel today, measured twice on 2026-09-11.**
 *
 * **EVERYTHING THAT CAN BE GOT WRONG IN HERE IS PURE.** Which campaigns count,
 * what a row says, how a value with a comma in it is written -- none of it needs
 * a network, a cookie or a browser, so all of it is driven by checks. What is
 * left is two addresses and a loop.
 */

/* Meesho's own two addresses. **Not a guess: read off the working reference**
 * (`content/meesho.js fetchMeeshoCampaignList` and `fetchMeeshoCampaignDetails`),
 * and the first one confirmed live on a real panel on 2026-09-11 -- HTTP 200,
 * `data.campaigns` a page of ten, `data.total_campaigns_count` 37. */
export const THE_CAMPAIGN_LIST = 'https://supplier.meesho.com/api/ads/campaigns/fetch-campaign-list';
export const ONE_CAMPAIGN = 'https://supplier.meesho.com/api/ads/campaigns/fetch-campaign-details';

/* Ten at a time, which is what the reference asks for and what a page really came
 * back as. A page shorter than this is the last one. */
export const A_PAGE_OF_CAMPAIGNS = 10;

/* **ONLY THE ONES THAT ARE RUNNING, WHICH IS HIS DECISION OF 2026-09-11**, asked
 * as a question with the consequence stated: on his own account 37 campaigns are
 * PAUSED and none is LIVE, so this sweep writes nothing until one is started.
 * **It says so rather than reporting a job well done** -- see `walk.js`. */
export const RUNNING = 'LIVE';

/* **HOW MANY PAGES ARE EVER ASKED FOR.** A list that never says it has ended is a
 * loop that never ends, at night, against somebody else's server. Ten pages is a
 * hundred campaigns; past that, something is wrong with the answer rather than
 * with the seller. */
export const AT_MOST_PAGES = 10;

/* ------------------------------------------------------------ who is signed in */

/**
 * The seller the browser is signed in as, out of Meesho's own cookies.
 *
 * **MEASURED ON A REAL PANEL, 2026-09-11.** `current_az_identifier` held the panel
 * slug and matched the one in the address bar; `s_id` held the numeric supplier id
 * and matched the number Meesho puts on its own download file names.
 *
 * **THIS IS THE WHOLE OF THE MULTI-SELLER ANSWER.** Meesho sets both for whoever
 * is signed in, so a second seller running this gets their own two without
 * anything being configured, and there is nowhere for one seller's name to be
 * written down.
 */
export function whoIsSignedIn(cookie) {
  const jar = {};
  for (const part of String(cookie || '').split(';')) {
    const at = part.indexOf('=');
    if (at < 0) continue;
    jar[part.slice(0, at).trim()] = part.slice(at + 1).trim();
  }
  const slug = jar.current_az_identifier || '';
  const supplierId = jar.s_id || '';
  /* **BOTH ARE ASKED FOR THE SHAPE THEY REALLY HAVE.** A blank one would go into
   * a header and the addresses would answer for nobody -- which reads as Meesho
   * having changed rather than as a seller being signed out. */
  if (!/^[a-z0-9]{2,32}$/i.test(slug)) return null;
  if (!/^[0-9]{4,12}$/.test(supplierId)) return null;
  return { slug, supplierId };
}

/** What Meesho wants on every one of those calls. The reference's own set. */
export function theHeadersFor(who) {
  return {
    Accept: 'application/json, text/plain, */*',
    'Content-Type': 'application/json',
    'client-type': 'd-web',
    identifier: who.slug,
    'supplier-id': who.supplierId,
    'browser-id': '',
  };
}

/* ------------------------------------------------------------------ the rows */

/* **THE COLUMNS ARE THE REFERENCE'S, because they are what anything reading these
 * files downstream already expects.** What changed is the FIRST column of each:
 * the reference writes the day it happened to run, this writes the day the
 * figures are ABOUT, which is the only thing that lets a past day be asked for
 * and the same rule every other report here follows. */
export const MASTER_COLUMNS = ['Date', 'Campaign ID', 'Campaign Name', 'Status', 'Start Date',
  'Ad Spend', 'Revenue', 'Orders', 'Views', 'Clicks', 'ROI', 'Conversion %',
  'Avg Order Value', 'Ad Spend Per Order'];
export const SUMMARY_COLUMNS = ['Date', 'Campaign ID', 'Campaign Name', 'Ad Spend', 'Revenue',
  'ROI', 'Ad Spend Per Order', 'Views', 'Clicks', 'Orders', 'Conversion %', 'Avg Order Value'];
export const CATALOGUE_COLUMNS = ['Date', 'Campaign ID', 'Campaign Name', 'Catalog ID', 'Category',
  'Catalog Status', 'Spend', 'Revenue', 'Orders', 'Views', 'Clicks', 'CPC', 'Conversion %',
  'Delivered ROI', 'Ad Spend Per Order', 'Current Performance', 'Avg Rating', 'Selected Min ROI'];

/** One value, written so a comma or a quote inside it cannot split a row.
 *
 *  **A CAMPAIGN NAME IS WHATEVER THE SELLER TYPED, AND SELLERS TYPE COMMAS.**
 *  Written plainly, one such name shifts every column after it by one for that
 *  row only -- which nothing downstream would notice and no total would reveal. */
export function asAValue(what) {
  const said = what === null || what === undefined ? '' : String(what);
  return '"' + said.split('"').join('""') + '"';
}

export function asARow(values) {
  return values.map(asAValue).join(',');
}

/** What a campaign has earned since it began, as at the day being fetched. */
export function theMasterRow(day, campaign, details) {
  const life = (details && details.campaign_overall_performance) || {};
  return asARow([
    day, campaign.campaign_id, campaign.campaign_name, campaign.status,
    String((details && details.start_date) || campaign.start_date || '').slice(0, 10),
    life.total_budget_utilized, life.total_revenue, life.total_orders, life.total_views,
    life.total_clicks, life.roi, life.conversion_rate, life.average_order_value, life.cpo,
  ]);
}

/** What one campaign did on the one day being fetched. */
export function theSummaryRow(day, campaign, details) {
  const on = (details && details.campaign_performance) || {};
  return asARow([
    day, campaign.campaign_id, campaign.campaign_name,
    on.total_budget_utilized, on.total_revenue, on.roi, on.cpo,
    on.total_views, on.total_clicks, on.total_orders, on.conversion_rate, on.average_order_value,
  ]);
}

/* How Meesho's own word for a catalogue's health reads to a person. The
 * reference's mapping, carried across rather than invented. */
const IN_WORDS = { RED_ATTENTION: 'Low Orders', GOOD: 'Good', GREEN: 'Good' };

/** What each catalogue inside one campaign did on that day. */
export function theCatalogueRows(day, campaign, details) {
  const each = (details && details.catalogs) || [];
  return each.map((one) => {
    const on = one.perf_details || {};
    const health = one.roi_bidding_catalog_feedback_details
      && one.roi_bidding_catalog_feedback_details.catalog_feedback_state;
    const spent = Number(on.budget_utilised);
    const orders = Number(on.order_count);
    const perOrder = orders > 0 ? (spent / orders).toFixed(2) : '0';
    return asARow([
      day, campaign.campaign_id, campaign.campaign_name, one.catalog_id,
      Array.isArray(one.category) ? one.category.join('|') : one.category, one.catalog_status,
      on.budget_utilised, on.revenue, on.order_count, on.total_views, on.total_clicks, on.cpc,
      on.conversion_rate, on.roi, perOrder,
      IN_WORDS[health] || health || '', on.average_rating, one.bid,
    ]);
  });
}

/* --------------------------------------------------------------- the sweep */

/** Every campaign the seller has, however many pages that takes. */
export async function everyCampaign(askMeesho, who, { pause = async () => {} } = {}) {
  const all = [];
  for (let page = 1; page <= AT_MOST_PAGES; page += 1) {
    // eslint-disable-next-line no-await-in-loop
    const answer = await askMeesho(THE_CAMPAIGN_LIST, {
      supplier_id: Number(who.supplierId),
      perf_details_required: true,
      page_number: page,
      page_size: A_PAGE_OF_CAMPAIGNS,
    });
    const got = (answer && answer.data && answer.data.campaigns) || [];
    all.push(...got);
    if (got.length < A_PAGE_OF_CAMPAIGNS) break;
    // eslint-disable-next-line no-await-in-loop
    await pause();
  }
  return all;
}

/**
 * The three files, built from what Meesho answered. Nothing is put anywhere here.
 *
 * **IT ANSWERS FILES RATHER THAN WRITING THEM**, so the whole of this can be
 * driven with no Drive and no browser -- the same reason `theListWith` in
 * `drive.js` is pure.
 *
 * **AND NO CAMPAIGNS RUNNING IS NOT A FAILURE AND NOT A SUCCESS.** It answers no
 * files and says how many it looked at, and the walk turns that into "there was
 * nothing to fetch" -- which is a thing a seller can act on, unlike an empty
 * folder and a job reporting itself done.
 */
export async function sweepTheAds(askMeesho, who, day, { pause = async () => {} } = {}) {
  const all = await everyCampaign(askMeesho, who, { pause });
  const running = all.filter((one) => one && one.status === RUNNING);
  const master = [];
  const summary = [];
  const catalogue = [];
  for (const campaign of running) {
    // eslint-disable-next-line no-await-in-loop
    const answer = await askMeesho(ONE_CAMPAIGN, {
      supplier_id: Number(who.supplierId),
      campaign_id: String(campaign.campaign_id),
      page_number: 1,
      page_size: 50,
      start_date: day,
      end_date: day,
      is_graph_required: false,
    });
    const details = (answer && answer.data) || null;
    /* **A CAMPAIGN THAT ANSWERED NOTHING IS SKIPPED, NOT FILLED WITH BLANKS.** A
     * row of empty columns reads downstream as a campaign that spent nothing,
     * which is a different and entirely believable fact. */
    // eslint-disable-next-line no-await-in-loop
    await pause();
    if (!details) continue;
    master.push(theMasterRow(day, campaign, details));
    summary.push(theSummaryRow(day, campaign, details));
    catalogue.push(...theCatalogueRows(day, campaign, details));
  }
  const asAFile = (columns, rows) => (rows.length ? [asARow(columns), ...rows].join('\n') : '');
  return {
    lookedAt: all.length,
    running: running.length,
    files: [
      { reportId: 'me_ads', text: asAFile(MASTER_COLUMNS, master) },
      { reportId: 'me_ads_summary', text: asAFile(SUMMARY_COLUMNS, summary) },
      { reportId: 'me_ads_catalog', text: asAFile(CATALOGUE_COLUMNS, catalogue) },
    ].filter((one) => one.text),
  };
}
