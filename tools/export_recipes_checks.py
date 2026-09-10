"""Checks for writing the recipes out, and the one that refuses a stale copy.

**THE CHECK THAT MATTERS MOST IS THE LAST ONE.** Everything else here is about the
tool being right; that one is about the file on disk being current. D107 chose to
have the steps decided in Python and walked in JavaScript, and named the cost out
loud: two halves that could drift. **This is the thing that stops them** -- exactly
as the commit gate already refuses a stale `STATUS.md`.

Run: python tools/export_recipes_checks.py
"""

import datetime
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import export_recipes as tool  # noqa: E402

# **THE ONE MODULE REACHED BY THE TOOL'S OWN PATH RATHER THAN BY THE TOOL.**
# `export_recipes` does not import `landing` -- it has no need to -- but it is
# what puts `autosync/` on the path, so this rides that same route rather than
# inserting a second one. It is here because the file-name rule below has to be
# compared against the Python that owns it.
import landing  # noqa: E402
# **AND THE DOOR ITSELF, for the same reason and by the same route.** The two
# halves fill a step in two languages, and holding them to one answer means
# asking BOTH of them -- not comparing the JavaScript to a second description of
# what the Python is supposed to do.
import browser_door as door  # noqa: E402

# **THE TOOL'S OWN COPIES, not a second import of the same two modules.** Putting
# the autosync folder on the path here as well would be two records of one fact --
# and it hid something: with this file reaching those modules by its own route,
# the tool could stop reaching them at all and every check here would still pass.
language = tool.language
book = tool.book

ran = 0
failures = []


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


def answered(work, *given):
    """What this answers, or None when it threw.

    **A RUN THAT STOPS IS NOT A CHECK GOING RED.** Sixty-one deliberate breakages
    of `browser_door.py` were "noticed" only by its checks file falling over, on
    the day this was written. Same cure, from the start, here.

    **AND ON 2026-09-10 IT WAS PUT ROUND EVERY CHECK IN THIS FILE, not the ones
    that happened to look fragile.** An independent reviewer found seven that
    still read a name straight out of what crossed: a name taken away ended the
    whole run in a `KeyError`, the file's own count check never ran, and the
    breakage read as "noticed" while saying nothing at all about whether the
    checks here are any good. **A traceback is not a refusal.** Nothing is ever a
    pass -- every check reads its answer for truth, so nothing always fails,
    which is what makes this safe to put round all of them.
    """
    try:
        return work(*given)
    except Exception:  # noqa: BLE001
        return None


HELD = answered(tool.what_the_extension_reads) or {}

# ------------------------------------------------ everything crosses

check("every recipe the Python has crosses",
      answered(lambda: set(HELD.get("recipes", {})) == set(book.RECIPES)))
check("and there are eighteen of them, both platforms",
      answered(lambda: len(HELD.get("recipes", {})) == 18))
check("every meaning of a failure crosses",
      answered(lambda: set(HELD.get("whatItMeans", {})) == set(language.WHAT_IT_MEANS)))
# **THE WHOLE MAP, not the part the walk happens to use today.** Splitting it is
# two records of one fact by another name.
check("including the ones the walk does not name yet",
      answered(lambda: language.DAY_NOT_AVAILABLE in HELD.get("whatItMeans", {})
                       and language.TOOK_TOO_LONG in HELD.get("whatItMeans", {})))
check("and the reports known to build their file inside the page",
      answered(lambda:
          set(HELD.get("buildsInThePageSince", {})) == set(book.BUILDS_IN_THE_PAGE_SINCE)))
check("with the day each of them started",
      answered(lambda: HELD.get("buildsInThePageSince", {}).get("fk_orders") == "2026-08-22"))

# **AND THE WORDS ONLY A SIGNED-OUT PORTAL SHOWS.** Found by loading the
# extension into a real Chrome for the first time: the door refused to be built
# at all, out loud, because these were not crossing.
check("the words a signed-out portal shows cross",
      answered(lambda: list(HELD.get("signedOutSigns", [])) == list(book.SIGNED_OUT_SIGNS)))
# **TWO OF THEM ARE NEEDED ON A PAGE, so fewer than two could never fire.**
check("and there are enough of them for the rule that needs two",
      answered(lambda: len(HELD.get("signedOutSigns", [])) >= 2))
check("they are Flipkart's public menu, read off the real signed-out site",
      answered(lambda: "Fees and Commission" in HELD.get("signedOutSigns", [])))
# **NOTHING OF THE SELLER'S IS IN THEM.** These go into a file that ships to
# every seller.
check("and none of them names a seller or a panel",
      answered(lambda: all("meesho.com" not in one and "flipkart.com" not in one
                           for one in HELD.get("signedOutSigns", []))))

# ------------------------------------------------ nothing is translated

STEPS = [s for r in HELD.get("recipes", {}).values() for s in r["toAsk"] + r["toTake"]]
check("there are steps to look at", answered(lambda: len(STEPS) > 50))
check("what a step does is the Python word, not a new one",
      answered(lambda: {s["do"] for s in STEPS} <= set(language.STEP_KINDS)))
check("and every one of the Python's kinds is used somewhere",
      answered(lambda: {s["do"] for s in STEPS} == set(language.STEP_KINDS)))
# **EVERY LOOKUP THAT CROSSES, NOT ONLY THE STEP'S OWN.** A take-file step also
# carries the control it shuts and opens again between looks, and that is a
# lookup like any other -- left out of this sweep, a way of finding something
# that only the extension would ever see could cross unchecked.
WAYS = ({s["find"]["how"] for s in STEPS if s["find"]}
        | {s["lookAgain"]["by"]["how"] for s in STEPS if s.get("lookAgain")})
check("how a thing is found is the Python word too",
      answered(lambda: WAYS <= set(language.WAYS_OF_FINDING)))
# **AND THE THIRD WAY REALLY CROSSES.** Meesho's panel has no control on it at
# all, so every one of its lookups is by pressable words -- if that word did not
# reach the extension, not one Meesho report could ever be fetched.
check("the pressable way reaches the extension",
      answered(lambda: language.BY_PRESSABLE_TEXT in WAYS))
check("and so does the control way, which Flipkart still uses",
      answered(lambda: language.BY_ROLE_AND_TEXT in WAYS))

# **THE ONE PLACE A NAME CHANGES SHAPE, and it is asserted rather than assumed.**
check("a step says how many days its range covers, spelt for JavaScript",
      answered(lambda: all("rangeDays" in s for s in STEPS)))
check("and the Python spelling is not also in there, which would be two names for one thing",
      answered(lambda: all("range_days" not in s for s in STEPS)))
ONE = HELD.get("recipes", {}).get("fk_orders", {})
check("a recipe says how long the platform takes, spelt for JavaScript",
      answered(lambda: "readyInMinutes" in ONE and "ready_in_minutes" not in ONE))
check("and its two phases are spelt for JavaScript",
      answered(lambda:
          "toAsk" in ONE and "toTake" in ONE and "to_ask" not in ONE and "to_take" not in ONE))
check("and what to shut and open again between looks is spelt for JavaScript",
      answered(lambda: all("lookAgain" in s and "look_again" not in s for s in STEPS)))
# **AND HOW A CALENDAR SWITCHES A DAY OFF, WHICH IS NO USE ON THIS SIDE AT ALL.**
# The door that presses the day runs in the seller's own Chrome. Said in the
# Python and not carried across, Flipkart's second way of disabling a day -- the
# one that shows only in the cursor -- is caught by nothing, and nothing anywhere
# looks wrong.
check("a step says how its calendar switches a day off, spelt for JavaScript",
      answered(lambda: all("switchedOffDaysChangeTheCursor" in s for s in STEPS)))
check("and the Python spelling is not also in there",
      answered(lambda: all("switched_off_days_change_the_cursor" not in s for s in STEPS)))
# **WORKED OUT INSIDE `answered`, and that is not decoration.** Read straight,
# a deliberate breakage that takes the name away ends this whole run in a
# KeyError -- the file's own count check never runs, nothing goes red, and the
# breakage reads as "noticed" while saying nothing about whether these checks
# are any good. **A traceback is not a refusal.**
check("and it really crosses as true for the reports centre",
      answered(lambda: all(any(s["do"] == language.PICK_RANGE
                               and s["switchedOffDaysChangeTheCursor"]
                               for s in HELD["recipes"][r]["toAsk"])
                           for r in ("fk_orders", "fk_returns", "fk_payments"))))
# **AND FOR NOTHING ELSE.** Crossing as true everywhere would read exactly like
# crossing correctly, and would refuse days that are perfectly available.
check("and as false everywhere else, so a value that crossed true for all would fail here",
      answered(lambda: all(not s["switchedOffDaysChangeTheCursor"]
                           for name, one in HELD["recipes"].items()
                           if name not in ("fk_orders", "fk_returns", "fk_payments")
                           for s in (one["toAsk"] + one["toTake"]))))

# ---------------------- the two things Meesho's orders export needs, crossing
#
# **NEITHER OF THESE IS ANY USE UNTIL IT REACHES THE EXTENSION.** The steps are
# decided in Python and carried out in the seller's own Chrome, so a rule that
# stays on this side is a rule that never runs.
ORDERS = HELD.get("recipes", {}).get("me_orders", {}).get("toTake", [])
check("the wait Meesho's orders export needs crosses to the extension",
      answered(lambda: any(s["do"] == language.WAIT and s["patience"] == 35 for s in ORDERS)))
# **THE ORDER IS THE POINT.** A wait after the page is loaded again is exactly as
# useless as no wait at all -- the list of finished files is drawn as the page
# loads.
_kinds = [s["do"] for s in ORDERS]
check("and it crosses in its place, after the export is asked for and before the page reloads",
      answered(lambda: _kinds.index(language.WAIT) < len(_kinds) - 1
                       and _kinds[_kinds.index(language.WAIT) + 1] == language.GO))
_again = ORDERS[-1].get("lookAgain") if ORDERS else None
check("and so does what to shut and open again while it waits for the finished file",
      answered(lambda:
          isinstance(_again, dict) and _again["times"] == 6 and _again["after"] == 30))
check("with the whole of how to find it, so the extension needs nothing more",
      answered(lambda: isinstance(_again, dict) and _again["by"]["what"] == "Download Orders Data"
                       and _again["by"]["how"] in set(language.WAYS_OF_FINDING)))
# **AND NOTHING ELSE CARRIES ONE.** Every other step says null rather than
# leaving the field out, so the extension reads one shape everywhere.
check("and every other step says plainly that it has none",
      answered(lambda: sum(1 for s in STEPS if s["lookAgain"] is not None) == 1))

# ------------------------------------------------ what a step carries

check("every step says what it is for, so a failure can say what was attempted",
      answered(lambda: all(s["why"] for s in STEPS)))
check("every step says how long to wait", answered(lambda: all(s["patience"] > 0 for s in STEPS)))
check("a step that goes somewhere says where",
      answered(lambda: all(s["address"] for s in STEPS if s["do"] == language.GO)))
check("a step that clicks or waits says what to look for",
      answered(lambda:
          all(s["find"] for s in STEPS if s["do"] in (language.CLICK, language.WAIT_FOR))))
check("and everything it looks for says what to look for",
      answered(lambda: all(s["find"]["what"] for s in STEPS if s["find"])))
# **THE SELLER'S OWN WORDS FOR IT.** Without this a failure names the raw text on
# a button, and "could not find 'Download Orders Data'" says far less than "could
# not find the download menu".
check("a thing worth naming in a person's words carries that name",
      answered(lambda: sum(1 for s in STEPS if s["find"] and s["find"]["called"]) > 20))
# Matching loosely has to be asked for, because a loose match is what found a
# chart legend before a menu item and cost nine days of payments.
check("matching the whole phrase is what most steps do",
      answered(lambda: sum(1 for s in STEPS if s["find"] and s["find"]["exact"])
                       > sum(1 for s in STEPS if s["find"] and not s["find"]["exact"])))

# ------------------------------------------------ the seller's own panel

PANEL_STEPS = [s for s in STEPS if "{panel}" in s["address"]]
# Six, not five: there are five Meesho recipes, and orders loads its page twice
# because Meesho does not show a finished file until the page is loaded again.
check("every Meesho page carries the placeholder for the seller's own slug",
      answered(lambda: len(PANEL_STEPS) == 6))
check("and orders carries it twice, because it loads its page twice",
      answered(lambda: sum(1 for s in HELD["recipes"]["me_orders"]["toTake"]
                           if "{panel}" in s["address"]) == 2))
# **NOT FILLED IN HERE.** One seller's panel address in a file that ships to every
# seller is exactly what D27, D30 and D92 forbid, and the reference holds one
# supplier's slug in its own source.
WHOLE = tool.written_out()
check("and no real supplier panel name is anywhere in the file",
      answered(lambda: "supplier.meesho.com/panel/v3/new/growth" not in WHOLE))

# ------------------------------------------------ the same bytes every time

check("writing it out twice gives the same bytes",
      answered(lambda: tool.written_out() == tool.written_out()))
check("and it is real JSON", answered(lambda: answered(json.loads, WHOLE) is not None))
check("with the note telling a reader not to edit it",
      answered(lambda: "DO NOT EDIT" in WHOLE and "export_recipes.py" in WHOLE))
check("and it ends with a newline, the way a text file does",
      answered(lambda: WHOLE.endswith("\n")))

# ------------------------------------------------ THE ONE THAT MATTERS

# **THE FILE ON DISK IS WHAT THE PYTHON SAYS, OR THIS GOES RED.**
#
# Without it, the recipes are decided in one place and carried out from another
# that quietly stopped agreeing -- and the extension would drive his portals by an
# older set of steps than the ones anybody checked. That is the cost D107 named
# when it chose this shape, and this is the thing that pays it.
STALE = tool.what_is_stale()
check(f"extension/recipes.json is what the Python says -- {STALE or 'it is'}",
      answered(lambda: STALE is None))
check("and the refusal, when there is one, says how to put it right",
      answered(lambda: "python tools/export_recipes.py"
               in (tool.what_is_stale() or "python tools/export_recipes.py")))

# ------------------------------------------------ writing it, for real

# **THE TOOL IS RUN, not merely read.** Everything above asks what it would
# produce; none of it puts a file on a disk or works the command line, which is
# the half a person actually uses -- and the half that can be broken without a
# single check above noticing.
import io  # noqa: E402
import tempfile  # noqa: E402

REALLY = tool.WHERE
# **TWO FOLDERS DEEP, ON PURPOSE.** One deep and the tool making its folder
# "and every folder above it" reads the same as making just the one -- so the
# difference between them could not be seen.
SOMEWHERE = Path(tempfile.mkdtemp(prefix="kartaan-recipes-")) / "nested" / "deeper" / "recipes.json"
tool.WHERE = SOMEWHERE
try:
    missing = tool.what_is_stale()
    check("with no file at all it says so plainly",
          answered(lambda: "does not exist" in (missing or "")))
    check("and says the extension has no recipes at all",
          answered(lambda: "no recipes" in (missing or "")))
    check("and says how to put it right",
          answered(lambda: "python tools/export_recipes.py" in (missing or "")))

    written = tool.write()
    check("writing it makes the folder it needs", answered(lambda: SOMEWHERE.is_file()))
    check("and answers where it put it", answered(lambda: written == SOMEWHERE))
    with open(SOMEWHERE, "r", encoding="utf-8", newline="") as handle:
        back = handle.read()
    check("and what came back off the disk is exactly what it meant to write",
          answered(lambda: back == tool.written_out()))
    check("which is now current", answered(lambda: tool.what_is_stale() is None))

    # **AND A FILE THAT HAS DRIFTED IS CAUGHT, not just a missing one.**
    with open(SOMEWHERE, "w", encoding="utf-8", newline="") as handle:
        handle.write(back.replace("opening the orders page", "opening the ORDERS page"))
    drifted = tool.what_is_stale()
    check("a file that has drifted from the Python is refused",
          answered(lambda: drifted is not None and "does not exist" not in drifted))
    check("and the refusal says what has actually gone wrong",
          answered(lambda:
              "older set of steps than the ones that were checked" in (drifted or "")))
    check("and names both files it was generated from",
          answered(lambda:
              "autosync/recipes.py" in (drifted or "") and "autosync/browser.py" in (drifted or "")))
    check("and how to put it right",
          answered(lambda: "python tools/export_recipes.py" in (drifted or "")))

    # ---------------------------------------- the command line a person uses
    was = sys.argv
    was_stderr = sys.stderr
    was_stdout = sys.stdout
    try:
        sys.argv = ["export_recipes.py", "--check"]
        sys.stderr = io.StringIO()
        answered_with = tool.main()
        complained = sys.stderr.getvalue()
        sys.stderr = was_stderr
        check("asked to check a file that has drifted, it refuses",
              answered(lambda: answered_with == 1))
        # **AND IT SAYS SO OUT LOUD.** A refusal nobody can read is a gate that
        # stops a commit for a reason the person is left to guess at.
        check("and says why, where a person will see it",
              answered(lambda: "older set of steps" in complained))
        # **AND IT CHANGES NOTHING.** Asked to CHECK, writing the file would make
        # the answer true by rewriting the question.
        with open(SOMEWHERE, "r", encoding="utf-8", newline="") as handle:
            still = handle.read()
        check("and checking it leaves the file exactly as it was",
              answered(lambda: "opening the ORDERS page" in still))

        sys.argv = ["export_recipes.py"]
        check("asked to write it, it does", answered(lambda: tool.main() == 0))
        check("and the file is current afterwards", answered(lambda: tool.what_is_stale() is None))

        sys.argv = ["export_recipes.py", "--check"]
        sys.stderr = io.StringIO()
        sys.stdout = io.StringIO()
        happy = tool.main()
        quiet = sys.stderr.getvalue()
        told = sys.stdout.getvalue()
        sys.stderr = was_stderr
        sys.stdout = was_stdout
        check("and checking it again is happy", answered(lambda: happy == 0))
        check("with nothing complained about", answered(lambda: quiet == ""))
        # **AND IT SAYS SO.** A tool that answers nothing at all leaves the person
        # wondering whether it ran.
        check("and it says the file is what the Python says",
              answered(lambda: "is what the Python says" in told))
        # **AND IT STOPS THERE.** Asked to CHECK, carrying on and writing the file
        # would make the answer true by rewriting the question -- and on a file
        # that is already current, nothing about the bytes would ever show it.
        check("and does not go on to write it", answered(lambda: "wrote" not in told))
    finally:
        sys.argv = was
        sys.stderr = was_stderr
        sys.stdout = was_stdout
finally:
    tool.WHERE = REALLY
    # **PUT BACK BEFORE THE ONE THAT MATTERS RUNS.** Left pointing at a temporary
    # folder, the last check below would ask whether a file nobody ships is
    # current, pass, and say nothing at all about the real one.
    check("and the tool is pointed back at the real file", answered(lambda: tool.WHERE == REALLY))

# ------------------------------------------------ the shape of the bytes

# **THE ORDER IS SETTLED, and that is what makes comparing two runs mean
# anything.** Sorted differently, every line of the file moves and the comparison
# reports drift on a change that is not one.
check("the recipes come before what a failure means",
      answered(lambda: WHOLE.index('"recipes"') < WHOLE.index('"whatItMeans"')))
check("and what a failure means before the doors that have closed",
      answered(lambda: WHOLE.index('"whatItMeans"') < WHOLE.index('"buildsInThePageSince"')))
check("and the note to a reader comes first of all",
      answered(lambda: WHOLE.index('"_generated"') < WHOLE.index('"recipes"')))
check("the recipes themselves are in a settled order",
      answered(lambda: list(HELD["recipes"]) == sorted(HELD["recipes"])))

# ---------------------------------- WHAT A LANDED FILE IS CALLED, HELD TO PYTHON
#
# **THE EXTENSION PUTS THE FILE IN THE SELLER'S DRIVE AND THE NIGHTLY RUN READS
# IT BACK OUT, AND THE ONLY THING JOINING THE TWO IS THE NAME.**
# `landing.data_date_in` takes the day out of the NAME and `reading.a_reading`
# REFUSES a file with no day in its name -- so a name the JavaScript builds any
# other way is a file that reaches the seller's Drive and can never be read. The
# folder fills up, the ledger stays empty, and nothing anywhere says why.
#
# **SO THE TWO SIDES ARE COMPARED, report by report, rather than the rule being
# written down twice and trusted.** `landing.file_name_for` is the Python's
# answer; the expression below is what `extension/walk.js` builds out of what
# crossed. **This project has already shipped one fact written down twice with
# nothing joining it** -- a log line's name built with six parts in Python and
# five on the page -- and the check named for it passed anyway, because it looked
# for a string rather than comparing the two sides.

reports_list = tool.list_of_reports
A_DAY = datetime.date(2026, 9, 5)

check("every recipe the extension can walk has a file name crossing with it",
      answered(lambda: sorted(HELD["fileNames"]) == sorted(HELD["recipes"])))
check("and each one carries a platform and a file type, never a blank",
      answered(lambda: all(HELD["fileNames"][one]["platform"]
                           and HELD["fileNames"][one]["extension"]
                           for one in HELD["fileNames"])))
check("THE NAME THE JAVASCRIPT WOULD BUILD IS THE NAME PYTHON BUILDS, REPORT BY REPORT",
      answered(lambda: all(
                           "{platform}_{report}_{day}.{extension}".format(
                               platform=HELD["fileNames"][one]["platform"],
                               report=one,
                               day=A_DAY.isoformat(),
                               extension=HELD["fileNames"][one]["extension"],
                           ) == landing.file_name_for(reports_list.report(one), A_DAY)
                           for one in HELD["fileNames"]
                       )))
# **AND THE TWO PARTS ARE THE REPORT'S OWN, read off `reports.py` rather than
# off the recipe's id.** `me_orders` beginning `me_` is a spelling, and a
# spelling is not a fact (D170).
check("and the platform and the file type are the report's own, not read off its id",
      answered(lambda: all(
          HELD["fileNames"][one]["platform"] == reports_list.report(one).platform
          and HELD["fileNames"][one]["extension"] == reports_list.report(one).extension
          for one in HELD["fileNames"])))
check("the file names are in a settled order too",
      answered(lambda: list(HELD["fileNames"]) == sorted(HELD["fileNames"])))

# ----------------------------------------- what the panel needs, and only it
#
# **EVERY REPORT THAT EXISTS CROSSES, not only the ones this door can fetch.**
# The panel shows a seller the whole of their own business; a list built from
# the recipes alone shows only what already works, which is the exact shape of
# "Meesho has never run and nothing anywhere says so".
check("every report the product declares crosses to the extension",
      answered(lambda: [one["id"] for one in HELD["reports"]]
                       == sorted(one.id for one in reports_list.REPORTS)))
# **AND IT IS THE SAME LIST THE ERP'S SCREENS READ, written from one function.**
# Two lists built two ways is the fault this whole file exists to prevent.
check("and it is the same list the ERP's own screens are given",
      answered(lambda: HELD["reports"] == tool.the_report_list()))

# **AND WHY THE FIVE THAT CANNOT BE FETCHED CANNOT BE, IN WORDS.** They are
# named with their reasons in `recipes.NOT_YET_A_RECIPE` and until the panel
# existed the reasons reached nobody at all -- the report was simply absent,
# which reads as a fault rather than as a limit somebody wrote down on purpose.
check("every report this door cannot fetch crosses with its reason",
      answered(lambda: HELD["notYetARecipe"] == dict(sorted(book.NOT_YET_A_RECIPE.items()))))
check("and every one of them is a real sentence, not a shrug",
      answered(lambda: all(len(why) > 40 for why in HELD["notYetARecipe"].values())))
# **THE TWO LISTS MAY NOT OVERLAP, and that is not tidiness.** A report with a
# recipe AND a reason it has none would be shown on the panel as both fetchable
# and impossible, and whichever the seller believed would be wrong half the time.
check("nothing is both fetchable and named as not fetchable",
      answered(lambda: not (set(HELD["notYetARecipe"]) & set(HELD["recipes"]))))
# **AND EVERY REASON IS ABOUT A REPORT THAT EXISTS.** A reason for a report
# nobody declares is a sentence nothing will ever show.
check("every reason is about a report the product actually declares",
      answered(lambda: set(HELD["notYetARecipe"]) <= {one["id"] for one in HELD["reports"]}))
# **THE TWO TOGETHER COVER EVERY BROWSER REPORT THERE IS.** A report that is
# declared, has no recipe and has no reason would vanish from the panel
# altogether -- neither fetchable nor explained -- which is the silence this
# whole crossing exists to end.
THROUGH_THE_BROWSER = {"flipkart", "meesho"}
check("no browser report is left out of both lists",
      answered(lambda: all(one["id"] in HELD["recipes"] or one["id"] in HELD["notYetARecipe"]
                           for one in HELD["reports"] if one["platform"] in THROUGH_THE_BROWSER)))


# ------------- HOW EACH PORTAL WRITES A DAY, AND THE TWO HALVES ASKED TOGETHER
#
# **THIS IS THE ONE CHECK IN THE PROJECT THAT RUNS BOTH HALVES AND COMPARES WHAT
# THEY SAY.** Everywhere else the two sides are held together by regenerating a
# file and comparing bytes -- which catches the file going stale and says nothing
# about whether the JavaScript that reads it arrives at the same answer.
#
# **AND HERE THAT GAP WOULD BE EXPENSIVE.** The whole difference between the two
# portals is one leading nought, on the nine days of every month whose number is
# under ten. A half that got it wrong would find no row at all -- not an error, a
# silence -- and the night would report a renamed button.
#
# **SO THE JAVASCRIPT IS ACTUALLY RUN**, against the very `extension/walk.js` and
# `extension/recipes.json` that ship, and its answers are compared to the Python
# functions AND to a handful of days written out by hand below. A check compared
# only against something the source also builds from is an echo; these three
# answers are arrived at three different ways.

# **DAYS CHOSEN FOR WHAT THEY SEPARATE, not for being tidy.** Four of the six
# have a number under ten, because that is the only place the two portals
# disagree; one is the first day of the year and one the last, because a month
# taken from the wrong end of a list shows up nowhere else.
SOME_DAYS = ("2026-09-01", "2026-06-05", "2026-01-01", "2026-12-31",
             "2026-02-09", "2026-08-25")

# **WRITTEN OUT BY HAND, ONE PORTAL AT A TIME, EVERY SPELLING TYPED.** Not built
# from `MONTHS`, not built from the shapes -- typed, from the two rows that were
# measured (Meesho's exported-files panel, `25 Aug 2026`; Flipkart's Requested
# list, `05 Jun 2026 To 06 Jun 2026`) and from the reference's own two matchers.
#
# **SEVERAL SPELLINGS PER PORTAL, WHICH IS THE A53 CORRECTION.** One per portal
# was what the reference does NOT do on either of them, and committing to one
# chose, on Flipkart, a spelling its own working matcher excludes.
BY_HAND = {
    "meesho": [
        ["2026-09-01", "1 Sep 2026", "01 Sep 2026", "1 Sep", "01/09/2026", "01-09-2026"],
        ["2026-06-05", "5 Jun 2026", "05 Jun 2026", "5 Jun", "05/06/2026", "05-06-2026"],
        ["2026-01-01", "1 Jan 2026", "01 Jan 2026", "1 Jan", "01/01/2026", "01-01-2026"],
        ["2026-12-31", "31 Dec 2026", "31 Dec 2026", "31 Dec", "31/12/2026", "31-12-2026"],
        ["2026-02-09", "9 Feb 2026", "09 Feb 2026", "9 Feb", "09/02/2026", "09-02-2026"],
        ["2026-08-25", "25 Aug 2026", "25 Aug 2026", "25 Aug", "25/08/2026", "25-08-2026"],
    ],
    "flipkart": [
        ["Sep 1 2026", "Sep 01 2026", "Sep 1, 2026", "1 Sep 2026", "2026-09-01", "01 Sep 2026"],
        ["Jun 5 2026", "Jun 05 2026", "Jun 5, 2026", "5 Jun 2026", "2026-06-05", "05 Jun 2026"],
        ["Jan 1 2026", "Jan 01 2026", "Jan 1, 2026", "1 Jan 2026", "2026-01-01", "01 Jan 2026"],
        ["Dec 31 2026", "Dec 31 2026", "Dec 31, 2026", "31 Dec 2026", "2026-12-31",
         "31 Dec 2026"],
        ["Feb 9 2026", "Feb 09 2026", "Feb 9, 2026", "9 Feb 2026", "2026-02-09", "09 Feb 2026"],
        ["Aug 25 2026", "Aug 25 2026", "Aug 25, 2026", "25 Aug 2026", "2026-08-25",
         "25 Aug 2026"],
    ],
}

# **AND THE TWO HALVES ARE HELD TO ONE ANSWER ON THE WHOLE OF THE FILLING-IN,
# NOT ONLY ON THE DAY IN WORDS.** That narrower comparison was what stood here
# while `browser_door` claimed a check held both halves together -- and it said
# nothing at all about whose wording each lookup carries, which day it names, or
# whether the two sides fill `{day}` the same way. This asks the shipped
# `extension/walk.js` for the finished row candidates of EVERY lookup in EVERY
# recipe, and the Python answers the same question for itself.
ASK_THE_JAVASCRIPT = """
import { readFileSync } from 'node:fs';
import { theDaysInWords, theRowsItCouldBe } from './extension/walk.js';
const book = JSON.parse(readFileSync('./extension/recipes.json', 'utf8'));
const [dataDate, runDay, ...days] = process.argv.slice(1);
const said = {};
for (const whose of Object.keys(book.daysInWords)) {
  said[whose] = days.map((one) => theDaysInWords(book, whose, one));
}
const rows = {};
for (const [name, recipe] of Object.entries(book.recipes)) {
  for (const half of ['toAsk', 'toTake']) {
    recipe[half].forEach((step, at) => {
      if (!step.find) return;
      rows[`${name}/${half}/${at}`] = theRowsItCouldBe(book, step.find, dataDate, runDay);
    });
  }
}
console.log(JSON.stringify({ said, rows }));
"""

# **A DATA DATE AND A RUN DAY THAT ARE NOT THE SAME DAY, and both single-figure.**
# Held equal, the whole which-day question would answer identically either way --
# which is exactly how the fault survived a night of being fixed.
A_DATA_DATE = "2026-06-05"
A_RUN_DAY = "2026-09-01"


def what_the_javascript_says():
    """What `extension/walk.js` makes of each of those days, or nothing.

    **NODE NOT BEING THERE IS A FAILURE, NEVER A SKIP.** The gate already refuses
    a commit it cannot run the JavaScript checks for, and a check that quietly
    passed because it could not look is worse than no check at all -- everybody
    believes it looked.
    """
    try:
        done = subprocess.run(
            ["node", "--input-type=module", "-e", ASK_THE_JAVASCRIPT,
             A_DATA_DATE, A_RUN_DAY, *SOME_DAYS],
            cwd=tool.ROOT, capture_output=True, text=True, check=False,
        )
    except OSError:
        return None
    if done.returncode != 0:
        return None
    try:
        return json.loads(done.stdout)
    except ValueError:
        return None


ANSWERED_IN_JAVASCRIPT = what_the_javascript_says() or {}
SAID_IN_JAVASCRIPT = ANSWERED_IN_JAVASCRIPT.get("said", {})
ROWS_IN_JAVASCRIPT = ANSWERED_IN_JAVASCRIPT.get("rows", {})


def the_python_rows():
    """The same question, asked of the Python half, lookup by lookup."""
    data_date = datetime.date.fromisoformat(A_DATA_DATE)
    run_day = datetime.date.fromisoformat(A_RUN_DAY)
    mine = {}
    for name in book.RECIPES:
        for half, steps in (("toAsk", book.RECIPES[name].to_ask),
                            ("toTake", book.RECIPES[name].to_take)):
            for at, step in enumerate(steps):
                if step.find is None:
                    continue
                mine[f"{name}/{half}/{at}"] = list(
                    door._the_rows_it_could_be(step.find, data_date, run_day))
    return mine


check("the JavaScript half can be asked what it makes of a day at all",
      answered(lambda: isinstance(SAID_IN_JAVASCRIPT, dict) and bool(SAID_IN_JAVASCRIPT)))
check("both portals' wordings cross to the extension",
      answered(lambda: sorted(HELD["daysInWords"]) == sorted(book.HOW_A_DAY_IS_WRITTEN)
               == ["flipkart", "meesho"]))
check("and each carries the month names and that portal's own spellings",
      answered(lambda: all(one["months"] == list(book.MONTHS)
                           and len(one["spellings"]) >= 5
                           for one in HELD["daysInWords"].values())))
# **THE SPELLINGS CROSS AS SHAPES, so the JavaScript joins the parts and carries
# no opinion of its own about noughts, month names or the order of the pieces.**
check("and the spellings cross as shapes rather than as finished days",
      answered(lambda: all("{" in one for shapes in HELD["daysInWords"].values()
                           for one in shapes["spellings"])))
# **THE TWO PORTALS ARE NOT ONE PORTAL.** If their spellings were ever made the
# same, one shared list would do -- and that is precisely the generalisation this
# whole arrangement exists to refuse. It would pass every other check here.
check("and the two portals' spellings are not the same list",
      answered(lambda: HELD["daysInWords"]["flipkart"]["spellings"]
               != HELD["daysInWords"]["meesho"]["spellings"]))

check("THE PYTHON'S ANSWER IS THE ONE WRITTEN OUT BY HAND, day by day, portal by portal",
      answered(lambda: all(
          [list(book.the_days_in_words(whose, datetime.date.fromisoformat(one)))
           for one in SOME_DAYS] == BY_HAND[whose] for whose in BY_HAND)))
check("AND THE JAVASCRIPT'S ANSWER IS THE SAME ONE, run out of the file that ships",
      answered(lambda: all(SAID_IN_JAVASCRIPT[whose] == BY_HAND[whose] for whose in BY_HAND)))
# **AND THE TWO HALVES ARE COMPARED TO EACH OTHER AS WELL AS TO THE HAND-WRITTEN
# LIST.** The hand-written list could itself be edited to match a drift; whether
# the two halves agree with EACH OTHER is a separate question, and it is asked
# separately.
check("and the two halves agree with each other, portal by portal",
      answered(lambda: all(
          SAID_IN_JAVASCRIPT[whose]
          == [list(book.the_days_in_words(whose, datetime.date.fromisoformat(one)))
              for one in SOME_DAYS]
          for whose in book.HOW_A_DAY_IS_WRITTEN)))
check("and the two portals really do write a single-figure day differently",
      answered(lambda: SAID_IN_JAVASCRIPT["meesho"][0] != SAID_IN_JAVASCRIPT["flipkart"][0]))

# ---- and the WHOLE of the filling-in, lookup by lookup, across every recipe
#
# **THIS IS THE CHECK `browser_door` CLAIMS.** What it used to say held both
# halves to one answer compared the day-in-words and nothing else -- so whose
# wording each lookup carries, WHICH day it names, and how `{day}` is filled
# were all outside it. Asked this way, a half that filled Meesho's row with the
# data date goes red here even though its wording is perfectly right.
check("there are lookups on both sides to compare at all",
      answered(lambda: len(ROWS_IN_JAVASCRIPT) > 20))
check("THE TWO HALVES FILL EVERY LOOKUP IN EVERY RECIPE THE SAME WAY",
      answered(lambda: ROWS_IN_JAVASCRIPT == the_python_rows()))
# **AND THE COMPARISON IS NOT VACUOUS.** Two halves that both answered nothing
# would agree perfectly.
check("and the ones that name a row really did come out full of days",
      answered(lambda: len([one for one in ROWS_IN_JAVASCRIPT.values() if one]) >= 9))
# **THE TWO PORTALS COME OUT DIFFERENT, in the one way that matters.** Meesho's
# row carries the RUN day and Flipkart's the DATA date, and the two days handed
# in are deliberately not the same day.
check("a Meesho row comes out named by the day the run is happening",
      answered(lambda: any("1 Sep 2026" == one for one in
                           ROWS_IN_JAVASCRIPT["me_returns/toTake/5"])))
check("while a Flipkart row comes out named by the day the data is about",
      answered(lambda: any("To 05 Jun 2026" == one for one in
                           ROWS_IN_JAVASCRIPT["fk_returns/toTake/4"])))

# **WHOSE WORDING EACH LOOKUP MEANS CROSSES WITH IT.** Handed the placeholder and
# not the portal, the walker on the other side could only guess.
#
# **WORKED OUT INSIDE `answered` LIKE EVERYTHING ELSE HERE.** Read at the top
# level, a name taken out of what crosses ends the run in a KeyError before the
# count check ever runs.
def named_in_words():
    return [
        (name, step["find"])
        for name, recipe in HELD["recipes"].items()
        for half in ("toAsk", "toTake")
        for step in recipe[half]
        if step["find"] and "{day_in_words}" in step["find"]["near"]
    ]


check("there are lookups naming a row by the day in words to judge",
      answered(lambda: len(named_in_words()) == 8))
check("and every one of them says whose wording it means",
      answered(lambda: all(find["dayInWordsIs"] in book.HOW_A_DAY_IS_WRITTEN
                           for _, find in named_in_words())))
check("and each says its OWN report's portal, never the other one's",
      answered(lambda: all(find["dayInWordsIs"] == reports_list.report(name).platform
                           for name, find in named_in_words())))
# **AND WHICH DAY IT MEANS CROSSES TOO, which is the A53 half.** Whose wording
# answers `1 Sep` against `01 Sep` and says nothing about which day is on the
# row. Left on the Python side, the walker would fill in whichever it held and
# find nothing on one of the two portals every night.
check("and every one of them says WHICH day it means",
      answered(lambda: all(find["dayInWordsOf"] in ("about", "made")
                           for _, find in named_in_words())))
# **THE TWO PORTALS ANSWER IT DIFFERENTLY, SAID SEPARATELY.** "Every lookup says
# something" would pass just as well if all eight said the same thing -- which is
# the bug this closes.
check("Meesho's lookups cross as the day the export was MADE",
      answered(lambda: all(find["dayInWordsOf"] == "made"
                           for name, find in named_in_words() if name.startswith("me_"))))
check("and Flipkart's as the day the data is ABOUT",
      answered(lambda: all(find["dayInWordsOf"] == "about"
                           for name, find in named_in_words() if name.startswith("fk_"))))
# **AND NOTHING CARRIES A WORDING IT HAS NO DAY IN WORDS TO WRITE.**
check("nothing carries a wording it has no day in words to write",
      answered(lambda: all(step["find"]["dayInWordsIs"] == ""
                           or "{day_in_words}" in step["find"]["near"]
                           for recipe in HELD["recipes"].values()
                           for half in ("toAsk", "toTake")
                           for step in recipe[half] if step["find"])))
check("nor a WHICH day it has no day in words to write either",
      answered(lambda: all(step["find"]["dayInWordsOf"] == ""
                           or "{day_in_words}" in step["find"]["near"]
                           for recipe in HELD["recipes"].values()
                           for half in ("toAsk", "toTake")
                           for step in recipe[half] if step["find"])))

# ---------------- the control that toggles crosses, and the box-beside way
#
# **NEITHER IS ANY USE UNTIL IT REACHES THE EXTENSION.** The thing that presses
# Flipkart's date box runs in the seller's own Chrome. Said in the Python and not
# carried across, the box is pressed once, the chip never appears, and the night
# waits quietly at a calendar that was never drawn.
def presses_again():
    return sorted(name for name, recipe in HELD["recipes"].items()
                  for half in ("toAsk", "toTake")
                  for step in recipe[half] if step["pressAgain"])


check("a step that presses a toggling control again crosses to the extension",
      answered(lambda: sorted(set(presses_again()))
               == ["fk_orders", "fk_payments", "fk_returns"]))
check("and it crosses spelt for JavaScript, not for Python",
      answered(lambda: all("pressAgain" in s and "press_again" not in s for s in STEPS)))
check("and each of the three does it twice -- for the chip and for the calendar",
      answered(lambda: presses_again().count("fk_orders") == 2))
check("and what to press, how long to wait and how many times all cross with it",
      answered(lambda: all(one["by"]["what"] and one["after"] >= 1 and one["times"] >= 1
                           for recipe in HELD["recipes"].values()
                           for half in ("toAsk", "toTake")
                           for one in [recipe[half][at]["pressAgain"]
                                       for at in range(len(recipe[half]))]
                           if one)))
# **AND NULL ON EVERY OTHER STEP.** Crossing as something everywhere would read
# exactly like crossing correctly, and would press an unrelated control on every
# waiting step of every recipe.
check("and it is null on every step that has no toggling control",
      answered(lambda: len([1 for recipe in HELD["recipes"].values()
                            for half in ("toAsk", "toTake")
                            for step in recipe[half] if step["pressAgain"]]) == 6))
# **AND THE WAY THAT REACHES A BOX BY THE LABEL BESIDE IT.** Said in the Python
# and not crossed, Flipkart's date step would ask the extension for a way of
# finding something it has never heard of.
check("the way that presses the box a label names crosses too",
      answered(lambda: any(step["find"] and step["find"]["how"] == "beside"
                           for recipe in HELD["recipes"].values()
                           for half in ("toAsk", "toTake")
                           for step in recipe[half])))
check("and it is the Python's own spelling, so nothing translates on the way",
      answered(lambda: language.BY_THE_CONTROL_BESIDE == "beside"))


EXPECTED = 112
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
