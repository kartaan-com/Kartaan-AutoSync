"""Where everything goes in the seller's own Drive. His layout, and nothing outside it.

**HIS APPROVAL, 2026-10-03 (20:05), COPIED RATHER THAN PARAPHRASED:**

    My Drive / Kartaan /
      Kartaan sales ledger                 (the sheet he opens)
      Reports /                            (shared by the daily run AND the Chrome extension)
        Amazon /   Orders, Returns, Settlements
        Flipkart / Orders, Returns, Payments, Claims, Listings, Views (one rolling file),
                   Ads / (daily, products, keywords-ads, orders, overall, placements, search: one folder each)
        Meesho /   Orders, Returns, Payments, Claims, Catalog, Views (one rolling file), Price (new stream),
                   Ads / (ads, catalog, summary: one folder each)
      System /                             (Kartaan's working files)
        one record of what was fetched and what was read  (what the Data tab shows)
        Logs / one per day, last 60 days only

*"No other separate folders or files should be created, other than what we add in
the AutoSync new streams."* So **a new AutoSync stream gets its own folder here, in
this same pattern, and that is the only addition there is.** `Price` is in his
layout and is not below: it is a stream nobody has built, and a folder for a report
that does not exist yet would be a folder nothing writes to.

**ONE LIST, USED BY BOTH HALVES.** The extension reads this through `recipes.json`
(`tools/export_recipes.py`), so a report, its folder and its reader cannot drift
apart the way the hand-kept second list did (Finding 51).

**NOTHING HERE TOUCHES A NETWORK.** `drive_door.py` and `extension/drive.js` find
or make what this names, and neither makes a folder whose name is not in it.
"""

from typing import Dict, FrozenSet, Tuple

import reports

# What the one folder everything goes inside is called, at the top of My Drive.
KARTAAN = "Kartaan"
THE_REPORTS = "Reports"
THE_SYSTEM = "System"
THE_LOGS = "Logs"

# Where the run's own working files go, and where its log goes.
SYSTEM: Tuple[str, ...] = (THE_SYSTEM,)
LOGS: Tuple[str, ...] = (THE_SYSTEM, THE_LOGS)

AMAZON = "Amazon"
FLIPKART = "Flipkart"
MEESHO = "Meesho"
ADS = "Ads"

# Every report's folder, below `Reports /`, in his words.
BELOW_REPORTS: Dict[str, Tuple[str, ...]] = {
    "az_orders": (AMAZON, "Orders"),
    "az_returns": (AMAZON, "Returns"),
    "az_settlements": (AMAZON, "Settlements"),
    "fk_orders": (FLIPKART, "Orders"),
    "fk_returns": (FLIPKART, "Returns"),
    "fk_payments": (FLIPKART, "Payments"),
    "fk_claims": (FLIPKART, "Claims"),
    "fk_listings": (FLIPKART, "Listings"),
    "fk_views": (FLIPKART, "Views"),
    "fk_ads_daily": (FLIPKART, ADS, "daily"),
    "fk_ads_fsn": (FLIPKART, ADS, "products"),
    "fk_ads_kw": (FLIPKART, ADS, "keywords-ads"),
    "fk_ads_orders": (FLIPKART, ADS, "orders"),
    "fk_ads_overall": (FLIPKART, ADS, "overall"),
    "fk_ads_placements": (FLIPKART, ADS, "placements"),
    "fk_ads_search": (FLIPKART, ADS, "search"),
    "me_orders": (MEESHO, "Orders"),
    "me_returns": (MEESHO, "Returns"),
    "me_payments": (MEESHO, "Payments"),
    "me_claims": (MEESHO, "Claims"),
    "me_catalog": (MEESHO, "Catalog"),
    "me_views": (MEESHO, "Views"),
    "me_ads": (MEESHO, ADS, "ads"),
    "me_ads_catalog": (MEESHO, ADS, "catalog"),
    "me_ads_summary": (MEESHO, ADS, "summary"),
}

# **FLIPKART SEARCH KEYWORDS (ORGANIC) HAS NO FOLDER -- HIS RULING: IT IS OFF.** It
# is a report, it is not fetched, and nothing is put anywhere for it.
HAS_NO_FOLDER: Dict[str, str] = {
    "fk_keywords": "it is switched off by his ruling, so nothing is fetched and no folder is made",
}


# **THE EXTENSION'S OWN NIGHT LOG IS NOT A REPORT, AND IT STILL HAS TO GO SOMEWHERE.** Its file is
# `run_log_<time>.txt` and it belongs with the run's logs in `System / Logs` -- which is also where
# the sixty-day tidy looks, so it cannot grow for ever.
THE_EXTENSIONS_LOG = "run_log"


def where_it_goes(report_id: str) -> Tuple[str, ...]:
    """The folders, from the top of `Kartaan /` down, that hold one report's files.

    **REFUSES RATHER THAN INVENTING A NAME.** A report with no folder here is a
    report whose files would land somewhere nobody approved.
    """
    if report_id in HAS_NO_FOLDER:
        raise KeyError(f"{report_id} has no folder: {HAS_NO_FOLDER[report_id]}.")
    below = BELOW_REPORTS.get(report_id)
    if below is None:
        raise KeyError(
            f"{report_id!r} has no folder in his layout. A new stream gets its own folder "
            "in this same pattern -- add it to BELOW_REPORTS in layout.py."
        )
    return (THE_REPORTS,) + below


def every_name() -> FrozenSet[str]:
    """Every folder name that may ever be made. Nothing else may be."""
    names = {KARTAAN, THE_REPORTS, THE_SYSTEM, THE_LOGS}
    for below in BELOW_REPORTS.values():
        names.update(below)
    return frozenset(names)


def for_the_extension() -> Dict:
    """What crosses into `recipes.json`, so the extension keeps no second list."""
    return {
        "kartaan": KARTAAN,
        "folders": {
            **{one: list(where_it_goes(one)) for one in sorted(BELOW_REPORTS)},
            THE_EXTENSIONS_LOG: list(LOGS),
        },
    }


def why_a_report_has_no_place() -> str:
    """Words naming any report in `reports.REPORTS` that has neither a folder nor a reason, or ''."""
    lost = [
        r.id for r in reports.REPORTS
        if r.id not in BELOW_REPORTS and r.id not in HAS_NO_FOLDER
    ]
    stray = [one for one in list(BELOW_REPORTS) + list(HAS_NO_FOLDER) if one not in reports.BY_ID]
    said = []
    if lost:
        said.append("reports with no folder and no reason: " + ", ".join(lost))
    if stray:
        said.append("folders for reports that do not exist: " + ", ".join(stray))
    return "; ".join(said)
