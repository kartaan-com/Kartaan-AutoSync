"""Write the recipes out for the extension, and refuse when they have drifted.

    python tools/export_recipes.py            write extension/recipes.json
    python tools/export_recipes.py --check    say whether what is on disk is current

**WHY THIS EXISTS, and it is the cost D107 named out loud.** The steps for driving
Meesho and Flipkart are decided in Python, where they are checked without a
browser. They are carried out in the seller's own Chrome, in JavaScript, because
the Python runs on a schedule in the seller's GitHub Actions and cannot reach a
browser on the seller's desk. **Two languages, and the steps must never become two
records of one fact** -- the failure this project has already been caught by four
times.

**SO THE JAVASCRIPT SIDE IS NOT WRITTEN. IT IS GENERATED**, here, and a check
regenerates it and compares. **That is exactly how `STATUS.md` already works** --
written byte for byte from `tools/work.json`, with the commit gate refusing a
stale one -- and the shape was chosen because it is already proven here.

**NOTHING IS TRANSLATED ON THE WAY OUT.** Every word that crosses -- what a step
does, how a thing is found, what a failure is called -- is the Python spelling
exactly, so there is no table anywhere turning one spelling into another. The one
thing that changes is the shape of a name: Python writes `range_days` and
JavaScript reads `rangeDays`, because a JavaScript file full of Python spellings
is a file nobody there will maintain. **That mapping is in one place, below, and
a check reads the JSON back and asserts every name in it.**

**THE PANEL PLACEHOLDER IS LEFT AS IT IS.** `{panel}` is the seller's own supplier
panel and is filled in at the moment of use. Filling it here would put one
seller's address into a file that ships to every seller (D27, D30, D92).
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "autosync"))

import browser as language  # noqa: E402
import recipes as book  # noqa: E402
import reports as list_of_reports  # noqa: E402

# Where it goes, written once. **The name is its own constant and the path is
# worked out from it**, so a message naming the file and the file itself can
# never be two different answers -- and so a refusal can name it without having
# to work out where it sits, which threw the moment anything pointed the tool
# somewhere else.
SHOWN = "extension/recipes.json"
WHERE = ROOT / SHOWN

# **AND THE PRODUCT NEEDS THE REPORT LIST TOO**, because the screen where a person
# asks for a day again has to offer the reports and say which of them cannot be
# had for a past day. That list is decided in `autosync/reports.py`, so it is
# generated here rather than typed a second time -- the same reason the recipes
# are.
REPORTS_SHOWN = "src/shared/definitions/reports.json"
REPORTS_WHERE = ROOT / REPORTS_SHOWN

# The one place a Python name becomes a JavaScript one. Everything not named here
# crosses unchanged, and a check asserts that what came out carries exactly these.
AS_JAVASCRIPT_SPELLS_IT = {
    "day_in_words_is": "dayInWordsIs",
    "day_in_words_of": "dayInWordsOf",
    "press_again": "pressAgain",
    "range_days": "rangeDays",
    "switched_off_days_change_the_cursor": "switchedOffDaysChangeTheCursor",
    "ready_in_minutes": "readyInMinutes",
    "to_ask": "toAsk",
    "to_take": "toTake",
    "look_again": "lookAgain",
}


def a_find(find):
    """How to find one thing on a page, as the extension reads it."""
    if find is None:
        return None
    return {
        "how": find.how,
        "what": find.what,
        "exact": find.exact,
        # **WHAT TO CALL IT WHEN IT IS NOT THERE, in words a person reads.** Left
        # out, a failure names the raw text on the button -- and "could not find
        # 'Download Orders Data'" tells a seller far less than "could not find the
        # download menu".
        "called": find.called,
        # **WHICH ROW IT IS ON**, when a page lists every export ever made and the
        # words on each one are identical. `{day}` and `{day_in_words}` are filled
        # in where the walk runs, with the day being fetched.
        "near": find.near,
        # **AND WHOSE WORDING OF A DAY `{day_in_words}` MEANS.** Meesho writes
        # `1 Sep 2026` and Flipkart's Reports Centre writes `05 Jun 2026`, so a
        # walker handed the placeholder and not the portal could only guess --
        # and a wrong guess finds no row at all for nine days of every month.
        # Empty on every lookup that does not name a row in words.
        AS_JAVASCRIPT_SPELLS_IT["day_in_words_is"]: find.day_in_words_is,
        # **AND WHICH DAY IT MEANS -- the day the data is about, or the day the
        # export was made.** Flipkart's Reports Centre names a row by the end of
        # its range, which is the data date; Meesho's exported-files panel names
        # one by the day the export was made, which is the day of the run. Left
        # on this side, the walker would fill in whichever it happened to hold
        # and find nothing on one of the two portals every single night.
        AS_JAVASCRIPT_SPELLS_IT["day_in_words_of"]: find.day_in_words_of,
    }


def a_press_again(press):
    """A control that toggles, pressed again while a step waits, as the extension
    reads it.

    **NO USE AT ALL ON THIS SIDE.** The thing that presses it runs in the
    seller's own Chrome. Said in the Python and not carried across, Flipkart's
    date box and Custom chip are pressed once each and the night waits quietly at
    a calendar that was never drawn.
    """
    if press is None:
        return None
    return {
        "by": a_find(press.by),
        "after": press.after,
        "times": press.times,
    }


def a_look_again(again):
    """What to close and open again between looks, as the extension reads it."""
    if again is None:
        return None
    return {
        "by": a_find(again.by),
        "times": again.times,
        "after": again.after,
    }


def a_step(step):
    """One thing to do to a page, as the extension reads it."""
    return {
        "do": step.do,
        "find": a_find(step.find),
        "address": step.address,
        "patience": step.patience,
        "why": step.why,
        AS_JAVASCRIPT_SPELLS_IT["range_days"]: step.range_days,
        # **HOW THE CALENDAR THIS STEP STANDS IN FRONT OF SWITCHES A DAY OFF.**
        # Flipkart's Reports Centre says it in the cursor and in nothing else on
        # one of its two mechanisms, and that is its own habit rather than a rule
        # of browsers -- so it crosses as a fact about that calendar. False on
        # every step but three.
        AS_JAVASCRIPT_SPELLS_IT["switched_off_days_change_the_cursor"]:
            step.switched_off_days_change_the_cursor,
        # **A LIST DRAWN WHEN A MENU OPENS DOES NOT CHANGE WHILE IT IS OPEN**, so
        # the step says what to shut and open again between looks. Null on every
        # step but one.
        AS_JAVASCRIPT_SPELLS_IT["look_again"]: a_look_again(step.look_again),
        # **A CONTROL THAT TOGGLES, PRESSED AGAIN WHILE THIS STEP WAITS.** Null on
        # every step but two, both of them on Flipkart's Reports Centre.
        AS_JAVASCRIPT_SPELLS_IT["press_again"]: a_press_again(step.press_again),
    }


def a_recipe(recipe):
    return {
        AS_JAVASCRIPT_SPELLS_IT["ready_in_minutes"]: recipe.ready_in_minutes,
        AS_JAVASCRIPT_SPELLS_IT["to_ask"]: [a_step(s) for s in recipe.to_ask],
        AS_JAVASCRIPT_SPELLS_IT["to_take"]: [a_step(s) for s in recipe.to_take],
    }


def what_the_extension_reads():
    """Everything the extension needs, worked out from the Python every time.

    **THE WHOLE OF `WHAT_IT_MEANS` GOES, not the part the walk happens to use
    today.** Splitting one map into "the bit that crosses" and "the bit that does
    not" is two records of one fact by another name, and the day the walk starts
    naming a fifth kind of failure, the sentence for it is already there rather
    than being invented on the JavaScript side.
    """
    return {
        "recipes": {name: a_recipe(book.RECIPES[name]) for name in sorted(book.RECIPES)},
        "whatItMeans": dict(sorted(language.WHAT_IT_MEANS.items())),
        "buildsInThePageSince": dict(sorted(book.BUILDS_IN_THE_PAGE_SINCE.items())),
        # **HOW EACH PORTAL WRITES A DAY -- SEVERAL SPELLINGS PER PORTAL, BECAUSE
        # EACH HAS BEEN MET WRITING MORE THAN ONE.** A row in a list of finished
        # exports is named by the day, and a row matches if it carries ANY of the
        # spellings that portal writes. The working reference builds six on
        # Meesho and five on Flipkart rather than choosing one.
        #
        # **THE PARTS CROSS, NOT A SECOND COPY OF THE RULE.** A spelling is a
        # shape -- `{d} {Mon} {yyyy}` -- and the walker in the extension only
        # puts the day into it. Nothing on that side carries its own month names,
        # its own opinion about a leading nought, or its own idea of what order
        # the pieces come in.
        "daysInWords": {
            whose: {
                "months": list(book.MONTHS),
                "spellings": list(shapes),
            }
            for whose, shapes in sorted(book.HOW_A_DAY_IS_WRITTEN.items())
        },
        # **THE WORDS ONLY A SIGNED-OUT PORTAL SHOWS.** The extension refuses to
        # build a door without them rather than answering "signed in" for ever --
        # which is what it did, out loud, the first time it was loaded into a real
        # Chrome with this list not yet crossing.
        "signedOutSigns": list(book.SIGNED_OUT_SIGNS),
        # **WHAT A LANDED FILE IS CALLED, and it crosses because the reader on
        # the other side will not read a file that is named any other way.**
        #
        # `landing.data_date_in` takes the day out of the NAME, and
        # `reading.a_reading` REFUSES a file with no day in its name -- so a file
        # the extension put in the seller's Drive under a name of its own
        # invention is a file the nightly run can never read. **The whole point
        # of putting it there would be lost, silently, and the folder would just
        # fill up.**
        #
        # **THE PATTERN ITSELF IS NOT SENT -- THE TWO PARTS THAT VARY ARE.**
        # `landing.file_name_for` is `<platform>_<report id>_<data date>.<ext>`,
        # and the platform and the extension are what a report decides. A check
        # holds the JavaScript that joins them to `landing.file_name_for`'s own
        # answer, report by report, so the two spellings cannot drift.
        "fileNames": {
            one: {
                "platform": list_of_reports.report(one).platform,
                "extension": list_of_reports.report(one).extension,
            }
            for one in sorted(book.RECIPES)
        },
        # **EVERY REPORT THAT EXISTS, not only the ones this door can fetch.**
        # The panel has to show a seller the whole of their own business, and a
        # list built from the recipes alone shows only what already works --
        # which is the exact shape of "Meesho has never run and nothing says so".
        # The same list `src/shared/definitions/reports.json` carries for the
        # ERP's screens, written from `the_report_list()` so there is one source
        # and not two.
        "reports": the_report_list(),
        # **AND WHY THE FIVE THAT CANNOT BE FETCHED CANNOT BE, IN WORDS.**
        # `NOT_YET_A_RECIPE` names each one with its reason and until now the
        # reason reached nobody: the panel could only have shown a report that
        # was simply absent, which reads as a fault rather than as a limit
        # somebody wrote down on purpose.
        "notYetARecipe": dict(sorted(book.NOT_YET_A_RECIPE.items())),
    }


# The note that goes at the top of the file, so somebody opening it knows not to
# edit it. It is part of what is compared, so removing it is drift like any other.
DO_NOT_EDIT = [
    "GENERATED BY tools/export_recipes.py. DO NOT EDIT.",
    "The steps are decided in autosync/recipes.py and the words a failure means in",
    "autosync/browser.py, where both are checked without a browser. This file is",
    "how they reach the extension, which runs in the seller's own Chrome (D107).",
    "Edit the Python and run the tool again; a check refuses a stale copy.",
]


def the_report_list():
    """Every report, as the product reads it.

    **ONLY WHAT A SCREEN NEEDS.** Which door a report comes through, how often it
    runs and what its file is called are the runner's business, and a copy of
    them in the product is a copy that goes stale.
    """
    return [
        {
            "id": one.id,
            "platform": one.platform,
            "name": one.name,
            # **WHY IT CANNOT BE HAD FOR A PAST DAY, in words, or nothing at
            # all.** Never a bare true-or-false: a screen that greys something
            # out without saying why is a screen somebody argues with.
            "cannotBeAskedForAgain": one.cannot_backfill,
        }
        for one in sorted(list_of_reports.REPORTS, key=lambda r: r.id)
    ]


def report_list_written_out():
    whole = {"_generated": DO_NOT_EDIT, "reports": the_report_list()}
    return json.dumps(whole, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def written_out():
    """The file's exact contents, as text.

    Settled on purpose -- names in order, two spaces, a newline at the end -- so
    that two runs of this tool on two machines produce the same bytes and the
    comparison below means something.
    """
    whole = {"_generated": DO_NOT_EDIT, **what_the_extension_reads()}
    return json.dumps(whole, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def on_disk(where=None):
    """What is really in the file, or nothing at all when there is none."""
    where = where or WHERE
    if not where.is_file():
        return None
    with open(where, "r", encoding="utf-8", newline="") as handle:
        return handle.read()


def what_is_stale():
    """Why the file on disk is not what the Python says, or None.

    **SAID IN WORDS RATHER THAN AS A DIFFERENCE.** A person reading a refusal
    needs to know what to do about it, and "run the tool again" is the whole
    answer in every case.
    """
    have = on_disk()
    want = written_out()
    if have is None:
        return (
            f"{SHOWN} does not exist. The extension has no recipes "
            f"at all. Run: python tools/export_recipes.py"
        )
    if have != want:
        return (
            f"{SHOWN} is not what autosync/recipes.py and "
            f"autosync/browser.py now say. The extension would drive the portals by an older set "
            f"of steps than the ones that were checked. Run: python tools/export_recipes.py"
        )

    have_reports = on_disk(REPORTS_WHERE)
    want_reports = report_list_written_out()
    if have_reports is None:
        return (
            f"{REPORTS_SHOWN} does not exist. The product has no report list at all. "
            f"Run: python tools/export_recipes.py"
        )
    if have_reports != want_reports:
        return (
            f"{REPORTS_SHOWN} is not what autosync/reports.py now says. The screen where a day is "
            f"asked for again would offer an older list of reports than the one that exists. "
            f"Run: python tools/export_recipes.py"
        )
    return None


def write():
    WHERE.parent.mkdir(parents=True, exist_ok=True)
    with open(WHERE, "w", encoding="utf-8", newline="") as handle:
        handle.write(written_out())
    REPORTS_WHERE.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORTS_WHERE, "w", encoding="utf-8", newline="") as handle:
        handle.write(report_list_written_out())
    return WHERE


def main():
    asked = argparse.ArgumentParser(description=__doc__)
    asked.add_argument("--check", action="store_true",
                       help="say whether what is on disk is current, and change nothing")
    args = asked.parse_args()

    if args.check:
        stale = what_is_stale()
        if stale:
            print(stale, file=sys.stderr)
            return 1
        print(f"{SHOWN} is what the Python says.")
        return 0

    write()
    holds = what_the_extension_reads()
    print(f"wrote {SHOWN} -- {len(holds['recipes'])} recipes, "
          f"{len(holds['whatItMeans'])} failure meanings; "
          f"and {REPORTS_SHOWN} -- {len(the_report_list())} reports.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
