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
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 7 + 4
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")
print(f"\n{len(failures)} FAILED: {failures}" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
