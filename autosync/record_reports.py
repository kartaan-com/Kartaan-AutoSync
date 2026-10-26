"""The reports whose files become records of their own in the seller's database -- ONE table, ONE reader loop, ONE sink (A87; his standing order D458 / D482).

Claims, Meesho product performance, Flipkart listing quality and Meesho's whole-shop figures are all "a platform file in, a record per row out". What differs is only
what is written in this table: the kind of record (`records.RecordKind`), how a file's rows become records, what a record keeps of the one already held (`merge`),
and the words the night's summary uses. `reading.py` has one branch that walks this table and `firestore_door.the_record_sinks` has one sink that serves it;
a fifth report is a fifth row here, not a fifth copy of either.

Nothing here opens a file, a clock or a connection.
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional

import claims
import performance
import quality
import records
import shopdays


@dataclass(frozen=True)
class RecordReport:
    """One report that is written as records. `read(report_id, platform, rows, day, context)` answers `(records by name, rows refused)`."""

    kind: records.RecordKind
    read: Callable
    # The words of the night's summary: "N <label> were new or changed in the <files> files and were recorded".
    label: str
    files: str
    # What the record keeps of the one already held (`merge(record, held)`), or nothing to keep.
    merge: Optional[Callable] = None
    # The product weeks are matched to the seller's own Meesho listings by title; the reading hands over their titles as `context`.
    wants_the_catalog_titles: bool = False


RECORD_REPORTS: Dict[str, RecordReport] = {
    "me_claims": RecordReport(
        claims.KIND, claims.read_claim_records, "claim(s)", "claims", merge=claims.merge,
    ),
    # **AMAZON'S SAFE-T CLAIMS (N018, D726): the same kind of record as Meesho's claims, one per SAFE-T claim id**, written to the same claims collection.
    "az_claims": RecordReport(
        claims.KIND, claims.read_safet_records, "SAFE-T claim(s)", "SAFE-T claims", merge=claims.merge,
    ),
    "me_product_performance": RecordReport(
        performance.KIND, performance.read_performance, "product week(s)", "product performance", wants_the_catalog_titles=True,
    ),
    "fk_quality_insights": RecordReport(
        quality.KIND, lambda report_id, platform, rows, day, context: quality.read_quality(report_id, platform, rows, day),
        "listing quality record(s)", "quality", merge=quality.merge,
    ),
    # **MEESHO'S PRODUCT QUALITY PAGE (N025): one file a day, a record per product and one for the store**, in the same listing-quality collection as Flipkart's, each with its short history.
    "me_quality": RecordReport(
        quality.KIND, lambda report_id, platform, rows, day, context: quality.read_meesho_quality(report_id, platform, rows, day),
        "quality record(s)", "product quality", merge=quality.merge,
    ),
    # **AMAZON'S ACCOUNT HEALTH (N018): a figure for the WHOLE SHOP on a day, the same kind of fact as Meesho's views**, written to the same shop-day collection as `amazon__<day>`.
    "az_health": RecordReport(
        shopdays.KIND, lambda report_id, platform, rows, day, context: shopdays.read_health_days(report_id, platform, rows, day),
        "account health day(s)", "account health",
    ),
    "me_views": RecordReport(
        shopdays.KIND, lambda report_id, platform, rows, day, context: shopdays.read_shop_days(report_id, platform, rows, day),
        "shop day(s)", "shop figures",
    ),
}
