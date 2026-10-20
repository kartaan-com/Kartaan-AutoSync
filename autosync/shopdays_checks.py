"""Checks for reading Meesho's whole-shop dashboard figures into a record per day (A87, D473).

The fixture is his real kept file `meesho_me_views.csv` (`Date,Views,Orders`).

Run: python autosync/shopdays_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import firestore  # noqa: E402
import firestore_door  # noqa: E402
import reading  # noqa: E402
import shopdays  # noqa: E402
import table  # noqa: E402
import whats_new  # noqa: E402

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
check("a field the record may not hold is refused by the writer",
      caught(lambda: firestore.a_shop_day_write("p", "x", dict(made["meesho__2026-10-06"], secret=1))) is not None)


class Reply:
    def __init__(self, status=200, body=None):
        self.status, self._body, self.text = status, body if body is not None else {}, str(body or "")

    ok = property(lambda self: 200 <= self.status < 300)

    def json(self):
        return self._body

    def records(self):
        return self._body if isinstance(self._body, list) else None


class Database:
    def __init__(self, held=None):
        self.held, self.posts = held or {}, []

    def post(self, url, params=None, headers=None, json=None, data=None):
        self.posts.append({"url": url, "json": json})
        if url.endswith(":batchGet"):
            found = []
            for name in json["documents"]:
                got = self.held.get(name.rsplit("/", 1)[-1])
                found.append({"found": {"name": name, "fields": {got[0]: {"stringValue": got[1]}, got[2]: {"stringValue": got[3]}}}}
                             if got else {"missing": name})
            return Reply(200, found)
        return Reply(200, {})


db = Database()
check("THE SHOP DAYS ARE ASKED ABOUT FIRST, THEN WRITTEN, and the sink says how many",
      answered(lambda: firestore_door.a_shop_days_sink(db, "p")("me_views", "2026-10-20", made)) == 3
      and [p["url"].rsplit(":", 1)[-1] for p in db.posts] == ["batchGet", "commit"])
same = Database({k: ("digest", v["digest"], "fileDay", "2026-10-20") for k, v in made.items()})
check("a second run on the same file writes nothing",
      answered(lambda: firestore_door.a_shop_days_sink(same, "p")("me_views", "2026-10-20", made)) == 0)
newer = Database({k: ("digest", "different", "fileDay", "2026-10-25") for k in made})
check("and an older file never puts a newer file's figures back",
      answered(lambda: firestore_door.a_shop_days_sink(newer, "p")("me_views", "2026-10-20", made)) == 0)
later = Database({k: ("digest", "different", "fileDay", "2026-10-15") for k in made})
check("while a later file's figure for a day replaces an earlier file's",
      answered(lambda: firestore_door.a_shop_days_sink(later, "p")("me_views", "2026-10-20", made)) == 3)

_files = {"me_views": [whats_new.InTheFolder(which="v1", name="meesho_me_views_2026-10-20.csv", size=200)]}
_written = []
night = answered(lambda: reading.read_what_is_new(
    already_read=(), what_is_in_the_folder=lambda r: list(_files.get(r, ())), bring_it_back=lambda w: REAL.encode("utf-8"),
    record_the_sales=lambda readings: None,
    record_shop_days=lambda report_id, day, records: _written.append((day, sorted(records))) or len(records)))
check("THE NIGHT WRITES EVERY SHOP DAY, reading the file named by its day, and the file is read",
      night is not None and night.read_tonight == ("v1",) and night.shop_days_written == 3 and _written[0][0] == "2026-10-20")
nowhere = answered(lambda: reading.read_what_is_new(
    already_read=(), what_is_in_the_folder=lambda r: list(_files.get(r, ())), bring_it_back=lambda w: REAL.encode("utf-8"),
    record_the_sales=lambda readings: None))
check("and with nowhere to write them the file is left unread, not lost",
      nowhere is not None and nowhere.read_tonight == () and nowhere.shop_days_waiting == 1)
check("the report is read and no longer said to be waiting",
      [o.report_id for o in reading.WHAT_SHOP_DAYS_CAN_BE_READ] == ["me_views"]
      and "me_views" not in reading.WHAT_IS_FETCHED_AND_NOT_READ_YET and reading.why_a_report_has_no_decision() == "")

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 15
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")
print(f"\n{len(failures)} FAILED: {failures}" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
