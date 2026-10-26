"""Checks for reading Meesho's whole-shop dashboard figures into a record per day (A87, D473).

The fixture is his real kept file `meesho_me_views.csv` (`Date,Views,Orders`).

Run: python autosync/shopdays_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import shopdays  # noqa: E402
import table  # noqa: E402

ran = 0
failures = []
THREW = []


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


def answered(work):
    try:
        return work()
    except Exception as wrong:  # noqa: BLE001
        THREW.append(repr(wrong))
        return None


def caught(work):
    try:
        work()
    except Exception as wrong:  # noqa: BLE001
        return wrong
    return None


REAL = "Date,Views,Orders\n2026-10-06,42088,19\n2026-10-07,38976,27\n2026-10-14,52750,23\n"


def file_of(text):
    return table.read(text.encode("utf-8"))


made, not_read = answered(lambda: shopdays.read_shop_days("me_views", "meesho", file_of(REAL), "2026-10-20")) or ({}, ())
check("A DAY OF THE WHOLE SHOP IS A RECORD NAMED BY ITS DAY, with views and orders",
      set(made) == {"meesho__2026-10-06", "meesho__2026-10-07", "meesho__2026-10-14"} and not_read == ()
      and made["meesho__2026-10-07"]["views"] == 38976 and made["meesho__2026-10-07"]["orders"] == 27)
check("nothing is derived from it: two days are two records, none summed or differenced",
      all(set(r) <= set(shopdays.SHOP_FIELDS) for r in made.values()) and len(made) == 3)
blank, _ = answered(lambda: shopdays.read_shop_days("me_views", "meesho", file_of("Date,Views,Orders\n2026-10-06,,5\n"), "2026-10-20")) or ({}, ())
check("a blank is nothing, not nought", "views" not in blank["meesho__2026-10-06"] and blank["meesho__2026-10-06"]["orders"] == 5)
_, bad = answered(lambda: shopdays.read_shop_days("me_views", "meesho", file_of("Date,Views,Orders\nsoon,1,1\n2026-10-06,x,1\n2026-10-07,-4,1\n2026-10-08,5,1\n"),
                                                  "2026-10-20")) or ({}, ())
check("a day or a figure this cannot read is refused by name and the rest are read", len(bad) == 3)
_twice, twice_said = answered(lambda: shopdays.read_shop_days("me_views", "meesho", file_of("Date,Views,Orders\n2026-10-06,1,1\n2026-10-06,2,2\n"), "2026-10-20")) or ({}, ())
check("A DAY NAMED TWICE IN ONE FILE IS SAID, the later line standing",
      len(_twice) == 1 and _twice["meesho__2026-10-06"]["views"] == 2 and len(twice_said) == 1)
no_columns = caught(lambda: shopdays.read_shop_days("me_views", "meesho", file_of("A,B\n1,2\n"), "2026-10-20"))
check("a file without the columns is refused in words naming what it has",
      no_columns is not None and "Views" in str(no_columns) and "Nothing was read" in str(no_columns))
# ---------------------------------------------------------------- R20 proving
import records  # noqa: E402

_sd = (answered(lambda: shopdays.read_shop_days("me_views", "meesho", file_of(REAL), "2026-10-20")) or ({}, ()))[0]
_sdwant = {"platform": "meesho", "report": "me_views", "day": "2026-10-07", "views": 38976, "orders": 27, "fileDay": "2026-10-20"}
check("A SHOP DAY'S RECORD HOLDS EXACTLY its day, views, orders and the file's day (R20 proving)",
      _sd.get("meesho__2026-10-07") == dict(_sdwant, digest=records.the_digest(_sdwant)))
_, _frac = answered(lambda: shopdays.read_shop_days("me_views", "meesho", file_of("Date,Views,Orders\n2026-10-06,12.5,1\n2026-10-07,1,2.5\n"), "2026-10-20")) or ({}, ())
check("views and orders are whole counts: a fraction is refused by line (R20 proving)", len(_frac) == 2)
_no_orders = (answered(lambda: shopdays.read_shop_days("me_views", "meesho", file_of("Date,Views,Orders\n2026-10-06,5,\n"), "2026-10-20")) or ({}, ()))[0]
check("a blank Orders cell is nothing, not nought (R20 proving)", "orders" not in _no_orders.get("meesho__2026-10-06", {"orders": 0}))
check("a file without the Orders column is refused in words (R20 proving)",
      "Nothing was read" in str(caught(lambda: shopdays.read_shop_days("me_views", "meesho", file_of("Date,Views\n2026-10-06,1\n"), "2026-10-20"))))
# ---------------------------------------------------------------- N018: AMAZON'S ACCOUNT HEALTH, one record per day
# **THE FIGURES ARE FROM HIS OWN ACCOUNT HEALTH PAGE (26 Oct 2026); the file is the one-row-per-day file the walk writes** (`Date`, then the five labels the recipe reads). A rate is a percentage with decimals,
# the rating a whole number; a blank is nothing, never nought (a late dispatch rate of 0 is a good day, a blank is a page that did not draw).
HEALTH_HEAD = "Date,Account Health Rating,Order Defect Rate,Late Dispatch Rate,Pre-fulfilment Cancel Rate,Valid Tracking Rate"
_hd = (answered(lambda: shopdays.read_health_days("az_health", "amazon", file_of(HEALTH_HEAD + "\n2026-10-26,204,0,1.8,0,100\n"), "2026-10-26")) or ({}, ()))
_hwant = {"platform": "amazon", "report": "az_health", "day": "2026-10-26", "healthRating": 204, "orderDefectRate": 0.0, "lateDispatchRate": 1.8,
          "cancelRate": 0.0, "validTrackingRate": 100.0, "fileDay": "2026-10-26"}
check("AN ACCOUNT HEALTH DAY'S RECORD HOLDS EXACTLY its day, the rating, the four rates (as numbers) and the file's day, named platform__day",
      _hd[0].get("amazon__2026-10-26") == dict(_hwant, digest=records.the_digest(_hwant)) and _hd[1] == ())
_hnone = (answered(lambda: shopdays.read_health_days("az_health", "amazon", file_of(HEALTH_HEAD + "\n2026-10-26,204,,1.8,,100\n"), "2026-10-26")) or ({}, ()))[0]
check("a blank figure is nothing, not nought: a late dispatch rate of 0 is kept as 0 and a blank is left out",
      "orderDefectRate" not in _hnone.get("amazon__2026-10-26", {"orderDefectRate": 0}) and _hnone["amazon__2026-10-26"]["lateDispatchRate"] == 1.8)
_, _hbad = answered(lambda: shopdays.read_health_days("az_health", "amazon", file_of(HEALTH_HEAD + "\nsoon,204,0,1.8,0,100\n2026-10-27,x,0,1.8,0,100\n2026-10-28,204,0,-1,0,100\n2026-10-29,204,0,150,0,100\n"), "2026-10-29")) or ({}, ())
check("a day, a rating or a rate this cannot read (not a number, below nought, over a hundred percent) is refused by name and the rest are read", len(_hbad) == 4)
check("a file without the Account Health columns is refused in words naming what it has",
      "Nothing was read" in str(caught(lambda: shopdays.read_health_days("az_health", "amazon", file_of("Date,Views,Orders\n2026-10-06,1,1\n"), "2026-10-26"))))
check("every field a health record carries is one the shop-day record kind accepts", all(set(r) <= set(shopdays.SHOP_FIELDS) for r in _hd[0].values()))
# **AMAZON'S OWN STATUS WORD (Control's word 26 Oct 2026): one text field per rate EXACTLY as the page prints it, and the overall one if the page shows it.** Optional columns: a file without them (older, or a page with no word) still reads.
STATUS_HEAD = HEALTH_HEAD + ",Account Health Status,Order Defect Rate Status,Late Dispatch Rate Status,Pre-fulfilment Cancel Rate Status,Valid Tracking Rate Status"
_hs = (answered(lambda: shopdays.read_health_days("az_health", "amazon", file_of(STATUS_HEAD + "\n2026-10-26,204,0,1.8,0,100,Healthy,Healthy,At Risk,Healthy,Healthy\n"), "2026-10-26")) or ({}, ()))
_hs_rec = _hs[0].get("amazon__2026-10-26", {})
check("EVERY RATE'S STATUS WORD IS KEPT AS TEXT EXACTLY AS AMAZON PRINTS IT, and the overall status too, in fields of their own",
      (_hs_rec.get("healthStatus"), _hs_rec.get("orderDefectRateStatus"), _hs_rec.get("lateDispatchRateStatus"), _hs_rec.get("cancelRateStatus"), _hs_rec.get("validTrackingRateStatus"))
      == ("Healthy", "Healthy", "At Risk", "Healthy", "Healthy") and _hs[1] == () and _hs_rec.get("lateDispatchRate") == 1.8)
_hsb = (answered(lambda: shopdays.read_health_days("az_health", "amazon", file_of(STATUS_HEAD + "\n2026-10-26,204,0,1.8,0,100,,,At Risk,,\n"), "2026-10-26")) or ({}, ()))[0].get("amazon__2026-10-26", {})
check("a blank status word is left out, never written as an empty text, and the figures still land",
      "healthStatus" not in _hsb and "orderDefectRateStatus" not in _hsb and _hsb.get("lateDispatchRateStatus") == "At Risk" and _hsb.get("orderDefectRate") == 0.0)
check("a status word is part of the record's digest, so a rate that turns At Risk is a changed record",
      _hs_rec.get("digest") != _hd[0]["amazon__2026-10-26"]["digest"])

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 7 + 4 + 5 + 3
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")
print(f"\n{len(failures)} FAILED: {failures}" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
