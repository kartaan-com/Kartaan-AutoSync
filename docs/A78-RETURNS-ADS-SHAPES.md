# A78 -- what the run writes for returns and ads (the shapes E85 and E87 build against)

Current as of 2026-10-12, after the readers were built and run over his real files (10 files in
`D:\Kartaan-Samples\autosync-returns-ads-2026-10-12`, read only, never copied here -- returns hold customer details). The module
docstrings in `autosync/returns.py` and `autosync/ads.py` say the same and are checked by `autosync/returns_ads_checks.py`.
Three collections, all written by the run as the owner (the ERP's rules must let the run write them, as for `listing_views`):
`platform_returns`, `platform_ads_days`, `platform_ads_detail`.

## 1. `platform_returns` -- one record per returned line

**Id:** `<platform>__<key>` where key = Flipkart `Return ID`; Meesho `Suborder Number`; Amazon `Amazon RMA ID`.

| Field | Meaning | Flipkart column | Meesho column | Amazon column |
|---|---|---|---|---|
| `platform` | `flipkart` / `meesho` / `amazon` | | | |
| `report` | `fk_returns` / `me_returns` / `az_returns` | | | |
| `returnKey` | the key above, as the platform gives it | Return ID | Suborder Number | Amazon RMA ID |
| `orderId` | joins to the ledger | Order ID | Suborder Number (= the ledger's `Sub Order No`) | Order ID |
| `sku` | absent when the file gives none | SKU | SKU | Merchant SKU |
| `saleKey` | `platform::orderId::sku` -- the ledger row's own name | | | |
| `trackingId` | the AWB the returns screen is scanned with; **query this field** | Tracking ID | AWB Number | Tracking ID |
| `qty` | whole number; absent when the file gives none | Quantity | Qty | Return quantity |
| `returnType` | **platform's own word** | Return Type | Type of Return | Return type |
| `reason` | **platform's own word** | Return Reason | Return Reason | Return Reason |
| `subReason` | **platform's own word** | Return Sub-reason | Detailed Return Reason | -- |
| `status` | **platform's own word** | Completion Status | -- | Return request status |
| `startedOn` | `yyyy-mm-dd` | Return Requested Date | Return Created Date | Return request date |
| `closedOn` | `yyyy-mm-dd` | Completed Date | Delivered Date | Return delivery date |
| `fileDay` | day of the file that last said this | | | |
| `digest` | fingerprint of what the record says (not of its day) | | | |

A cell the platform left blank is **absent**, never `0` or `""`. Meesho writes `NA` for some courier returns; it is stored as the platform's own word
(`NA`) -- the ERP groups or hides it when showing, never the run. A return named twice in one file with different words is said (the first stands).
**Written only when new or different, and never over a record from a newer file.** Second run on the same file: 0 writes.

## 2. `platform_ads_days` -- one record per platform per day

**Id:** `<platform>__<yyyy-mm-dd>`. Written with a field mask, so the files that feed a day never undo each other.

| Field | Content |
|---|---|
| `platform`, `day`, `updatedOn` | |
| `campaigns` | map `campaignId -> {campaignName, spend, views, clicks, units, revenue}` from `fk_ads_daily` (Flipkart: Ad Spend, Views, Clicks, Total converted units, Total Revenue (Rs.)) and `me_ads_summary` (Meesho: Ad Spend, Views, Clicks, Orders, Revenue). Money to two places; a blank figure is absent; a campaign named twice on a day is added. |
| `campaignsDigest`, `campaignsFileDay` | fingerprint and day of the file that wrote `campaigns` |

`charged` (what Meesho took out for ads) is **not written**: `me_ads` is a lifetime file and no real one has been seen. The ledger charge (plan 78) is the ERP's, from `campaigns`.

## 3. `platform_ads_detail` -- one record per platform per day per kind (Flipkart only)

**Id:** `<platform>__<yyyy-mm-dd>__<kind>`, kind in `placements | overall | search | orders`; **`overall` is `..__overall__<campaignId>`** (Flipkart gives a file per campaign). Written whole.

Fields: `platform`, `day`, `kind`, `fileDay`, `updatedOn`, `digest`, `rows` (list of maps), `rowsInFile`, `rowsKept`, and `campaignId` on `overall`.
**Never silently cut:** a record may hold about 700 KB of rows (Firestore's limit is 1 MiB); past that the biggest-spend rows are kept and `rowsKept < rowsInFile` says so.

| kind | report | row fields |
|---|---|---|
| `placements` | `fk_ads_placements` | campaignId, campaignName, placementType, views, clicks, spend, unitsDirect, unitsIndirect, revenueDirect, revenueIndirect |
| `overall` | `fk_ads_overall` | campaignId, skuId, listingId, productName, cpc, views, clicks, spend, unitsDirect, unitsIndirect, revenueDirect, revenueIndirect |
| `search` | `fk_ads_search` | campaignId, campaignName, query, views, clicks, spend (SUM(cost)), unitsDirect, unitsIndirect, revenueDirect, revenueIndirect |
| `orders` | `fk_ads_orders` | campaignId, orderId, advertisedFsn, purchasedFsn (FSNs, not SKUs), listingId, productName, revenue, unitsDirect, unitsIndirect |

A file that covers more than one day (`End Time` on another day than `Start Time`) is refused; `orders` files are split by each row's own Date.
**Flipkart keyword ads (`fk_ads_kw`) are discontinued by Flipkart** (his ruling, 12 Oct): not read, and switched off like `fk_keywords`.

## Writes and reads per run (his free daily allowance is 20,000 writes / 50,000 reads)

| | Writes | Reads (to avoid rewriting) |
|---|---|---|
| Returns | one per **new or changed** returned line in the new files (about as many as returns that day; 0 when nothing changed) | one per line in the files |
| Ads days | 1 Flipkart + 1 Meesho per day the files name (about 2) | same |
| Ads detail | up to 4 per Flipkart day, plus one per extra campaign for `overall` (about 4 to 6) | same |
| **Typical day** | **about 8 plus the day's new returns** | **about the same count** |
| **First catch-up** | one write per record in the files already in his Drive (500 per call) | |

## Samples still missing

None of the nine readers is missing a real file. **`me_ads` (a campaign's lifetime takings) has no real sample and is not read.** The returns files hold customer details; the sample copies stay in `D:\Kartaan-Samples`.
