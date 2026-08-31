"""Checks for putting a file in the seller's own Drive.

**THE ONE THAT MATTERS MOST: a second copy is refused.** The reference put three
wrongly-dated duplicates into a seller's Drive, and a folder holding two files for
one day is a folder where nobody can say which one the numbers came from.

Run: python autosync/drive_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import drive as tool  # noqa: E402

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


# ------------------------------------------- which way it goes up

# **GOOGLE'S OWN BOUNDARY, not one we chose:** 5 MB or less in one request with
# its metadata; larger than that, resumable.
check("a small file goes up in one request",
      answered(lambda: tool.how_to_upload(900)) == tool.MULTIPART)
check("a file exactly on the boundary is still 'five megabytes or less'",
      answered(lambda: tool.how_to_upload(5 * 1024 * 1024)) == tool.MULTIPART)
check("and one byte over it goes the resumable way",
      answered(lambda: tool.how_to_upload(5 * 1024 * 1024 + 1)) == tool.RESUMABLE)
# His listing file is comfortably over it.
check("a listing file goes the resumable way",
      answered(lambda: tool.how_to_upload(9 * 1024 * 1024)) == tool.RESUMABLE)
check("a file with nothing in it still has a way", answered(lambda: tool.how_to_upload(0)) == tool.MULTIPART)

# ------------------------------------------- what a file is

check("a spreadsheet is called a spreadsheet",
      answered(lambda: tool.kind_of("meesho_me_catalog_2026-08-26.xlsx"))
      == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
check("a csv is called a csv", answered(lambda: tool.kind_of("a.csv")) == "text/csv")
check("a zip is called a zip", answered(lambda: tool.kind_of("payments.zip")) == "application/zip")
check("and capitals do not change what it is", answered(lambda: tool.kind_of("A.CSV")) == "text/csv")
# The other three the platforms actually hand over.
check("an older spreadsheet is called one too",
      answered(lambda: tool.kind_of("a.xls")) == "application/vnd.ms-excel")
check("a json answer is called json", answered(lambda: tool.kind_of("a.json")) == "application/json")
check("and plain text is called plain text", answered(lambda: tool.kind_of("a.txt")) == "text/plain")
# **AND EVERY ONE OF THEM IS DIFFERENT.** Two endings sharing an answer would put
# a spreadsheet in Drive labelled as something else, which opens as gibberish.
check("no two endings are given the same answer",
      answered(lambda: len(set(tool.BY_EXTENSION.values())) == len(tool.BY_EXTENSION)))

# **WHAT DRIVE CALLS A FOLDER**, straight out of Google's own documentation. A
# folder is looked for by this, and a wrong value here finds nothing and quietly
# makes a new folder every night.
check("a folder is what Google calls a folder",
      answered(lambda: tool.FOLDER) == "application/vnd.google-apps.folder")
# **NEVER GUESSED AT SOMETHING PLAUSIBLE.** A spreadsheet uploaded as plain text
# opens as gibberish, and nothing about it says the labelling was the problem.
check("something nobody recognises is not called text",
      answered(lambda: tool.kind_of("a.wibble")) == "application/octet-stream")
check("and neither is a name with no ending at all",
      answered(lambda: tool.kind_of("payments")) == "application/octet-stream")
check("nor no name at all", answered(lambda: tool.kind_of("")) == "application/octet-stream")

# ------------------------------------------- what is refused, and why

check("a file with nowhere to go is refused",
      "nowhere to put it" in (answered(lambda: tool.why_it_cannot_be_put("", "a.csv", b"x")) or ""))
check("a file with no name is refused",
      "nothing to call it" in (answered(lambda: tool.why_it_cannot_be_put("f1", "", b"x")) or ""))
check("nothing at all is refused, rather than an empty file being written",
      "no file came back" in (answered(lambda: tool.why_it_cannot_be_put("f1", "a.csv", None)) or ""))
# **AN EMPTY FILE COUNTED AS ARRIVED WOULD STOP ITS DAY EVER BEING FETCHED
# AGAIN**, which is the quietest way to lose a day for good.
check("a file with nothing in it is refused",
      "nothing in it" in (answered(lambda: tool.why_it_cannot_be_put("f1", "a.csv", b"")) or ""))
check("and the refusal says why that matters",
      "ever being fetched again" in (answered(lambda: tool.why_it_cannot_be_put("f1", "a.csv", b"")) or ""))
check("a real file is not refused",
      answered(lambda: tool.why_it_cannot_be_put("f1", "a.csv", b"row")) is None)

# ------------------------------------------- never a second copy

check("a name nothing else has is simply put there",
      answered(lambda: tool.what_to_do_about("a.csv", [])) == "put")
check("and a folder nobody has read yet is the same",
      answered(lambda: tool.what_to_do_about("a.csv", None)) == "put")
check("another day's file does not get in the way",
      answered(lambda: tool.what_to_do_about("a.csv", [{"name": "b.csv"}])) == "put")
# **THE SAME DAY FETCHED AGAIN REPLACES, NEVER SITS BESIDE.** A folder with two
# files for one day is one where nobody can say which the numbers came from.
check("the same name already there is replaced, not added beside",
      answered(lambda: tool.what_to_do_about("a.csv", [{"name": "a.csv"}])) == "replace")
# **AND TWO ALREADY THERE IS NOT SOMETHING TO TIDY UP SILENTLY.** Replacing one
# leaves the other; deleting the rest is a decision nothing here is entitled to
# make.
check("two of the same name already there needs a person",
      answered(lambda: tool.what_to_do_about("a.csv", [{"name": "a.csv"}, {"name": "a.csv"}]))
      == "somebody has to look")

# ------------------------------------------- what Drive is told

LANDING = tool.Landing(folder_id="f1", file_name="meesho_me_orders_2026-08-26.csv",
                       kind="text/csv", size=900)
check("the file is named as it will appear",
      answered(lambda: tool.the_metadata(LANDING)["name"]) == "meesho_me_orders_2026-08-26.csv")
check("and put in the folder it was told to go in",
      answered(lambda: tool.the_metadata(LANDING)["parents"]) == ["f1"])
check("in a list, because that is what Drive takes",
      answered(lambda: isinstance(tool.the_metadata(LANDING)["parents"], list)))
check("and the landing knows which way it goes up", answered(lambda: LANDING.by) == tool.MULTIPART)
check("a landing cannot be edited once it is decided",
      answered(lambda: setattr(LANDING, "folder_id", "somewhere else")) is None and bool(THREW))
THREW.clear()

# ------------------------------------------- one folder per report

check("a report's folder is named after the report",
      answered(lambda: tool.a_folder_for("me_orders")) == "me_orders")
check("and a folder for no report at all is refused",
      answered(lambda: tool.a_folder_for("")) is None and bool(THREW))
THREW.clear()

# ------------------------------------------- what it asks the seller for

# **THE NARROWEST SCOPE THAT CAN CREATE A FILE.** A product that asks a seller for
# their whole Drive when it needs one folder is one they are right to refuse.
check("it asks for the narrowest thing that can create a file",
      answered(lambda: tool.SCOPE) == "https://www.googleapis.com/auth/drive.file")
check("and not for the seller's whole Drive",
      answered(lambda: tool.SCOPE.endswith("/auth/drive")) is False)

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 38
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
