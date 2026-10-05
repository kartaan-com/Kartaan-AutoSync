"""Checks for his Drive layout, with no Drive anywhere.

**THE ONES THAT MATTER MOST:** every report in `reports.REPORTS` has a folder or a
written reason it has none (so a new stream cannot be added without one -- his
rule, mechanised), no two reports share a folder, and **no code path in either
half can make a folder whose name is not in his layout.**

Run: python autosync/layout_checks.py
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import layout as tool  # noqa: E402
import reports  # noqa: E402

ran = 0
failures = []


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


def refused(work):
    try:
        work()
    except KeyError as wrong:
        return str(wrong)
    return ""


check("every report has a folder or a written reason it has none", tool.why_a_report_has_no_place() == "")
check("his one report with no folder is Flipkart's organic keywords, and the reason is written",
      list(tool.HAS_NO_FOLDER) == ["fk_keywords"] and "ruling" in tool.HAS_NO_FOLDER["fk_keywords"])
check("no two reports share one folder",
      len(set(tool.BELOW_REPORTS.values())) == len(tool.BELOW_REPORTS))
check("a report's path starts at Reports and ends at its own folder",
      tool.where_it_goes("fk_ads_fsn") == ("Reports", "Flipkart", "Ads", "products"))
check("Amazon's three are Orders, Returns and Settlements, as he wrote them",
      [tool.where_it_goes(one)[-1] for one in ("az_orders", "az_returns", "az_settlements")]
      == ["Orders", "Returns", "Settlements"])
check("Meesho's three ads folders are ads, catalog and summary",
      sorted(tool.where_it_goes(one)[-1] for one in ("me_ads", "me_ads_catalog", "me_ads_summary"))
      == ["ads", "catalog", "summary"])
check("Flipkart's seven ads folders are the seven he named",
      sorted(p[-1] for one, p in tool.BELOW_REPORTS.items() if one.startswith("fk_ads_"))
      == ["daily", "keywords-ads", "orders", "overall", "placements", "products", "search"])
check("the run's own files go in System, and its logs in System / Logs",
      tool.SYSTEM == ("System",) and tool.LOGS == ("System", "Logs"))
check("a report with no folder is refused in words, not given a name",
      "switched off" in refused(lambda: tool.where_it_goes("fk_keywords")))
check("and so is one nobody declared",
      "no folder in his layout" in refused(lambda: tool.where_it_goes("zz_new")))
tool.BELOW_REPORTS["zz_new"] = ("X",)
said_stray = tool.why_a_report_has_no_place()
del tool.BELOW_REPORTS["zz_new"]
check("a folder listed here for a report that does not exist is said", "do not exist" in said_stray)

standing = tool.reports.REPORTS
tool.reports.REPORTS = standing + (reports.Report("zz_new", "meesho", "x", "browser", "daily", "csv"),)
said_lost = tool.why_a_report_has_no_place()
tool.reports.REPORTS = standing
check("a report added with no folder and no reason is said", "no folder and no reason" in said_lost)
check("and the layout is whole again after those two", tool.why_a_report_has_no_place() == "")

# **THE FOLDER NAMES THE EXTENSION RECEIVES ARE THE SAME LIST.**
crossing = tool.for_the_extension()
check("what crosses to the extension is the whole list",
      crossing["kartaan"] == "Kartaan" and set(crossing["folders"]) == set(tool.BELOW_REPORTS)
      and all(crossing["folders"][one] == list(tool.where_it_goes(one)) for one in crossing["folders"]))

# **NOTHING MAKES A FOLDER EXCEPT ONE PLACE THAT REFUSES A NAME OUTSIDE THE LAYOUT.** The
# extension's half of this check is in `extension/drive.test.js`.
makes_a_folder_py = []
for one in sorted(HERE.glob("*.py")):
    if one.name.endswith("_checks.py"):
        continue
    for number, line in enumerate(one.read_text(encoding="utf-8").splitlines(), 1):
        if re.search(r'"mimeType":\s*FOLDER', line):
            makes_a_folder_py.append(f"{one.name}:{number}")
check(f"the run makes a folder in exactly one place, in drive_door.py -- {makes_a_folder_py}",
      len(makes_a_folder_py) == 1 and makes_a_folder_py[0].startswith("drive_door.py:"))

EXPECTED = 15
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
