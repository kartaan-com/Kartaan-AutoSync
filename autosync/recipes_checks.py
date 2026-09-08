"""Checks for the recipes -- Meesho's and Flipkart's, in one list.

**EACH RECIPE IS WRITTEN OUT STEP BY STEP BELOW.** Checking only that a recipe is
valid leaves the middle of it free to lose a step -- and a recipe that quietly
skips "choose the date range" exports the wrong days, which is the quietest kind of
wrong there is. The prover found exactly that on the Meesho four.

**AND THE TWO-PHASE ONES ARE CHECKED AS TWO.** Flipkart's Reports Centre allows
twenty requests a day; asking twice for one report is how the reference spent a
day locked out.

Run: python autosync/recipes_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from datetime import date  # noqa: E402

import browser as pages  # noqa: E402
import recipes as tool  # noqa: E402
from reports import BROWSER as NEEDS_A_BROWSER  # noqa: E402
from reports import BY_ID as KARTAAN_REPORTS  # noqa: E402

ran = 0
failures = []
# Everything that ended by throwing rather than by answering. **The floor under
# all of it:** answering with nothing stops the run dying, but on its own it is
# not enough -- a check written as "this word is NOT in what it said" passes
# against nothing, and would go green for the worst possible reason.
THREW = []


def answered(work):
    """What this answers, or nothing at all when it threw.

    **A RUN THAT STOPS IS NOT A CHECK GOING RED.** Worked out before it is handed
    over, one deliberate breakage anywhere ends the whole run and nothing goes
    red -- so the measurement reads "noticed" while saying nothing about whether
    any check here is any good. Worked out in here, a call that throws answers
    with nothing, that one check goes red by itself, and the rest still run.

    Nothing is never a pass: every check reads its answer for truth, so nothing
    always fails. That is what makes this safe to put round every one of them.
    """
    try:
        return work()
    except Exception as wrong:  # noqa: BLE001
        THREW.append(repr(wrong))
        return None


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


def refuses(fn):
    try:
        fn()
    except (ValueError, KeyError, TypeError, AttributeError):
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


def said(fn):
    try:
        fn()
    except Exception as wrong:  # noqa: BLE001
        return str(wrong)
    return ""


# **THE SLUG ALONE**, the short word in the middle of every Meesho address --
# not the section around it, which is Meesho's own and lives in the recipe.
PANEL = "some-slug"

# ------------------------------------------------------ every recipe is sound

for report_id in tool.every_recipe():
    one = tool.recipe(report_id)
    every = one.to_ask + one.to_take
    check(f"{report_id}'s steps are all usable", answered(lambda: not any(pages.why_step_is_refused(s) for s in every)))
    check(f"and every step of {report_id} says what it is for", answered(lambda: all(s.why for s in every)))
    # **THE LAST STEP TAKES THE FILE.** A recipe that clicks about and never takes
    # anything runs perfectly and produces nothing -- which reads as the platform
    # being broken rather than as a recipe missing its end.
    check(f"and {report_id} ends by taking a file", answered(lambda: one.to_take[-1].do == pages.TAKE_FILE))
    check(f"and {report_id} starts by going somewhere", answered(lambda: one.to_take[0].do == pages.GO))

# **EVERY RECIPE IS FOR A REPORT KARTAAN ACTUALLY HAS.** A recipe for a report that
# is not on the list is a recipe nothing will ever run, and the reference had
# exactly that between its job list and its manifest slots.
check("every recipe is for a report on Kartaan's own list",
      answered(lambda: all(r in KARTAAN_REPORTS for r in tool.every_recipe())))
check("and no report has two recipes", answered(lambda: len(set(tool.every_recipe())) == len(tool.every_recipe())))

# ------------------------------------------------ each recipe, step by step

SHAPES = {
    # **ORDERS LOADS THE PAGE A SECOND TIME, and that is the whole recipe.**
    # Meesho builds the file almost instantly and it does not appear in the
    # exported files list until the page is loaded again -- reopening the menu is
    # not enough. So: menu, range, export, THEN load again, open the menu again,
    # take it.
    "me_orders": ((), (pages.GO, pages.WAIT_FOR, pages.CLICK, pages.CLICK, pages.PICK_RANGE,
                       pages.CLICK, pages.GO, pages.WAIT_FOR, pages.CLICK, pages.TAKE_FILE)),
    "me_catalog": ((), (pages.GO, pages.WAIT_FOR, pages.CLICK, pages.TAKE_FILE)),
    # Returns has no Export button: the way in is a control whose whole label is
    # a count of files, and it opens the panel that exports and lists them.
    "me_returns": ((), (pages.GO, pages.WAIT_FOR, pages.CLICK, pages.CLICK, pages.CLICK,
                        pages.TAKE_FILE)),
    # Payments asks for a range that Meesho then ignores -- the page will not
    # hand anything over until one has been chosen.
    "me_payments": ((), (pages.GO, pages.WAIT_FOR, pages.CLICK, pages.CLICK, pages.CLICK,
                         pages.PICK_RANGE, pages.TAKE_FILE)),
    # **CLAIMS IS PAYMENTS WITHOUT THE RANGE, and that missing step is the whole
    # difference.** `reports.py` says Meesho hands back a rolling window here
    # rather than a chosen day, so there is no day to pick and a range step would
    # be asking for something the page does not offer. The menu is opened twice --
    # once to ask for the export, once to find the finished file -- and the page
    # is never loaded again, which is what makes it not the orders shape.
    "me_claims": ((), (pages.GO, pages.WAIT_FOR, pages.CLICK, pages.CLICK, pages.CLICK,
                       pages.CLICK, pages.TAKE_FILE)),
    "fk_orders": ((pages.GO, pages.WAIT_FOR, pages.CLICK, pages.CLICK, pages.CLICK,
                   pages.PICK_RANGE, pages.CLICK, pages.WAIT_FOR),
                  (pages.GO, pages.WAIT_FOR, pages.CLICK, pages.WAIT_FOR, pages.TAKE_FILE)),
    "fk_views": ((pages.GO, pages.WAIT_FOR, pages.CLICK, pages.PICK_RANGE, pages.CLICK),
                 (pages.GO, pages.WAIT_FOR, pages.TAKE_FILE)),
    "fk_claims": ((), (pages.GO, pages.WAIT_FOR, pages.CLICK, pages.CLICK, pages.CLICK,
                       pages.PICK_RANGE, pages.TAKE_FILE)),
    "fk_ads_daily": ((), (pages.GO, pages.WAIT_FOR, pages.CLICK, pages.CLICK,
                          pages.PICK_RANGE, pages.TAKE_FILE)),
    "fk_listings": ((pages.GO, pages.WAIT_FOR, pages.CLICK, pages.CLICK),
                    (pages.GO, pages.WAIT_FOR, pages.CLICK, pages.CLICK, pages.TAKE_FILE)),
    "fk_returns": ((pages.GO, pages.WAIT_FOR, pages.CLICK, pages.CLICK, pages.CLICK,
                    pages.PICK_RANGE, pages.CLICK, pages.WAIT_FOR),
                   (pages.GO, pages.WAIT_FOR, pages.CLICK, pages.WAIT_FOR, pages.TAKE_FILE)),
    "fk_payments": ((pages.GO, pages.WAIT_FOR, pages.CLICK, pages.CLICK, pages.CLICK,
                     pages.PICK_RANGE, pages.CLICK, pages.WAIT_FOR),
                    (pages.GO, pages.WAIT_FOR, pages.CLICK, pages.WAIT_FOR, pages.TAKE_FILE)),
}
for report_id, (ask, take) in sorted(SHAPES.items()):
    one = tool.recipe(report_id)
    check(f"{report_id}'s asking phase is exactly what it should be",
          answered(lambda: tuple(s.do for s in one.to_ask) == ask))
    check(f"and {report_id}'s taking phase is too",
          answered(lambda: tuple(s.do for s in one.to_take) == take))

# ------------------------------------------------- one place, not seven copies

# **SEVEN AD REPORTS, ONE PAGE, ONE DROPDOWN VALUE BETWEEN THEM.** Built from one
# template, so a fix to one is a fix to all -- the reference applied a fix to
# orders and not to payments, and they were meant to be identical.
ADS = [r for r in tool.every_recipe() if r.startswith("fk_ads_")]
check("all seven ad reports have recipes", answered(lambda: len(ADS) == 7))
check("and they are all the same shape",
      answered(lambda: len({tuple(s.do for s in tool.recipe(r).to_take) for r in ADS}) == 1))
check("differing only in which report is chosen",
      answered(lambda: len({tool.recipe(r).to_take[3].find.what for r in ADS}) == 7))

# The Reports Centre three, likewise.
RC = ["fk_orders", "fk_returns", "fk_payments"]
check("the three reports-centre reports are the same shape",
      answered(lambda: len({tuple(s.do for s in tool.recipe(r).to_ask) for r in RC}) == 1))
check("and all three are two-phase", answered(lambda: all(tool.recipe(r).two_phase for r in RC)))

# ------------------------------------- TWO-PHASE: asked once, collected later

two = [r for r in tool.every_recipe() if tool.recipe(r).two_phase]
check("the reports Flipkart has to go away and build are two-phase",
      answered(lambda: set(two) == {"fk_orders", "fk_returns", "fk_payments", "fk_views", "fk_listings"}))
check("and no Meesho report is", answered(lambda: not any(r.startswith("me_") for r in two)))
# **A ONE-SHOT REPORT SAYS NOTHING ABOUT HOW LONG IT TAKES TO BE READY**, because
# nobody is building it -- a number there would be read by nothing.
check("a one-shot report says nothing about how long it takes to be ready",
      answered(lambda: all(tool.recipe(r).ready_in_minutes == 0 for r in tool.every_recipe() if not tool.recipe(r).two_phase)))
for report_id in two:
    one = tool.recipe(report_id)
    check(f"{report_id} says roughly how long it takes to be ready", answered(lambda: one.ready_in_minutes > 0))
    # **THE TWO PHASES ARE DIFFERENT.** Identical ones would mean the collect phase
    # re-submits -- which on Flipkart spends one of twenty requests a day.
    check(f"and {report_id}'s two phases really are different",
          answered(lambda: tuple(s.do for s in one.to_ask) != tuple(s.do for s in one.to_take)))
    check(f"and {report_id}'s asking phase ends by triggering the build",
          answered(lambda: one.to_ask[-1].do in (pages.CLICK, pages.WAIT_FOR)))

# **WHAT EACH ASKING PHASE ACTUALLY PRESSES, WRITTEN OUT.** A check that looked for
# the words "Submit" or "Request" anywhere passed on four of the five and failed on
# the fifth for no good reason -- a pattern standing in for a fact. These are the
# facts.
ASKS_BY = {
    "fk_orders": "Submit",
    "fk_returns": "Submit",
    "fk_payments": "Submit",
    "fk_views": "Request Listings Report",
    "fk_listings": "Download Listing File",
}
for report_id, pressed in sorted(ASKS_BY.items()):
    check(f"{report_id} is asked for by pressing {pressed!r}",
          answered(lambda: any((s.find.what if s.find else "") == pressed for s in tool.recipe(report_id).to_ask)))
    # **AND THE TAKING PHASE DOES NOT PRESS IT AGAIN**, which on Flipkart would
    # spend one of twenty requests a day and leave two reports building.
    check(f"and {report_id}'s taking phase never presses it again",
          answered(lambda: not any((s.find.what if s.find else "") == pressed for s in tool.recipe(report_id).to_take)))

# **A ONE-SHOT REPORT IS UNCHANGED BY BEING ASKED TO COLLECT.** A caller that gets
# it wrong fetches the report rather than doing nothing, which is the safer way
# round.
check("asking a one-shot report to collect changes nothing",
      answered(lambda: tool.steps_for("me_catalog", PANEL, collecting=True) == tool.steps_for("me_catalog", PANEL)))
# **AND WHICH HALF IS WHICH, not merely that they differ.** Swapped, the first run
# would collect a report nobody had asked for and the second would submit -- so
# every day would end with a request in flight and no file, for ever.
check("not collecting gives the ASKING steps",
      answered(lambda: tool.steps_for("fk_views", PANEL, collecting=False) == tool.recipe("fk_views").to_ask))
check("and collecting gives the TAKING steps",
      answered(lambda: tool.steps_for("fk_views", PANEL, collecting=True) == tool.recipe("fk_views").to_take))
check("and the two really are different",
      answered(lambda: tool.steps_for("fk_views", PANEL, collecting=True) != tool.steps_for("fk_views", PANEL)))

# ------------------------------ EXACTLY WHICH LOOKUPS MATCH LOOSELY

# **A LOOSE MATCH IS HOW NINE DAYS OF PAYMENTS WERE LOST**, so each one is named
# here rather than counted. All three are headings or statuses the platform
# writes in its own case and padding -- never the name of a thing to click.
# `EXPORTED FILES` used to be a fourth and is gone: the list it named never
# changes without the page being loaded again, so waiting on it was waiting for
# something that could not happen.
loose = {s.find.what for r in tool.RECIPES.values()
         for s in (r.to_ask + r.to_take) if s.find is not None and not s.find.exact}
check("only these three things are matched loosely, and no others",
      answered(lambda: loose == {"successfully", "Generated", "files ready"}))
# **TWO OF THEM ARE WORDS THE PLATFORM SAYS**, written in its own case to report
# what has happened -- never the name of a thing to press. `Download` used to be
# a third and is gone: read loosely on his own inventory page it found TWO -- the
# button, and the line above it reading "Download file with existing stock" -- so
# the stock file could never have been fetched at all.
#
# **THE THIRD IS PRESSED, AND IT IS THE ONE EXCEPTION**, with a reason: on the
# returns page the whole label of the control IS a count -- "0/0 files ready" --
# so there is no exact wording to match. It is asked for on something PRESSABLE,
# which is what keeps it from matching the sentence elsewhere on that page that
# also says "files ready".
check("the one loose thing that is pressed is the count that has no fixed wording",
      answered(lambda: {s.find.what for r in tool.RECIPES.values()
                        for s in (r.to_ask + r.to_take)
                        if s.do == pages.CLICK and s.find is not None and not s.find.exact}
               == {"files ready"}))
# **AND NOTHING THAT IS CLICKED IS MATCHED LOOSELY.** Waiting for a heading
# loosely is safe; clicking on a loose match is the coin toss.
check("everything else that is CLICKED is matched exactly",
      answered(lambda: all(s.find.exact for r in tool.RECIPES.values()
          for s in (r.to_ask + r.to_take)
          if s.do == pages.CLICK and s.find is not None and s.find.what != "files ready")))

# ---------------------- FLIPKART'S REPORTS CENTRE NEEDS TWO DAYS, NOT ONE

# **Flipkart requires the start strictly before the end.** A single-day range is
# refused by a Submit that does nothing at all, with no message.
rc_range = [s for s in tool.recipe("fk_orders").to_ask if s.do == pages.PICK_RANGE][0]
check("the reports centre asks for a two-day range", answered(lambda: rc_range.range_days == 2))
me_range = [s for s in tool.recipe("me_orders").to_take if s.do == pages.PICK_RANGE][0]
check("while Meesho asks for the one day", answered(lambda: me_range.range_days == 1))
check("and a range of no days at all is refused",
      answered(lambda: pages.why_step_is_refused(pages.Step(pages.PICK_RANGE, range_days=0, why="x")) is not None))
check("and only a range step may say how many days it covers",
      answered(lambda: pages.why_step_is_refused(pages.Step(pages.GO, address="a", range_days=2, why="x")) is not None))

# ------------------------------------ THE LIVE FIX: "Custom Dates" is gone

# **READ OFF HIS OWN FLIPKART ON 2026-08-27.** The words "Custom Dates" do not
# exist on the traffic report page any more; Flipkart replaced the button with a
# dropdown whose label is one word. That is the whole of a 29-day outage.
views = tool.recipe("fk_views")
check("the traffic report no longer looks for 'Custom Dates'",
      answered(lambda: not any("Custom Dates" in (s.find.what if s.find else "") for s in views.to_ask)))
check("it looks for the dropdown Flipkart actually has now",
      answered(lambda: any((s.find.what if s.find else "") == "Custom" for s in views.to_ask)))
# **AND MATCHED EXACTLY**, because a loose match for "custom" also hits the
# "Customer Segments" tab sitting beside it -- the chart-legend trap again.
check("and matches it exactly, or it would also hit 'Customer Segments'",
      answered(lambda: all(s.find.exact for s in views.to_ask if s.find is not None)))
check("and still asks for the listings report, which has not changed",
      answered(lambda: any("Request Listings Report" in (s.find.what if s.find else "") for s in views.to_ask)))

# ----------------------- WHAT FLIPKART NOW BUILDS INSIDE THE PAGE

check("the two reports Flipkart builds inside the page are named",
      answered(lambda: set(tool.BUILDS_IN_THE_PAGE_SINCE) == {"fk_orders", "fk_returns"}))
check("with the day it started", answered(lambda: tool.BUILDS_IN_THE_PAGE_SINCE["fk_orders"] == "2026-08-22"))
check("and both are real reports", answered(lambda: all(r in tool.RECIPES for r in tool.BUILDS_IN_THE_PAGE_SINCE)))

# ------------------------------------------ nothing of one seller's is here

SOURCE = Path(tool.__file__).read_text(encoding="utf-8")
check("the seller's own panel name is not in this file", answered(lambda: "xuptj" not in SOURCE))
check("and no seller's business name", answered(lambda: "rumee" not in SOURCE.lower()))
# **MEESHO KEEPS ITS SECTIONS UNDER DIFFERENT ADDRESSES, and there is no single
# prefix.** Orders under `fulfillment`, payments under `payouts`, the stock file
# under `services`, the dashboard under `growth`. Read live on 2026-08-28 after
# `…/growth/<slug>/orders` drew NOTHING AT ALL four times running -- Meesho does
# not refuse an address it does not know, it serves a page that never finishes.
check("every Meesho section leaves room for the seller's own slug",
      answered(lambda: all("{panel}" in one
                           for one in (tool.FULFILMENT, tool.PAYOUTS, tool.SERVICES))))
check("orders and returns are under fulfillment",
      answered(lambda: "/fulfillment/" in tool.FULFILMENT))
check("payments are under payouts, not with them",
      answered(lambda: "/payouts/" in tool.PAYOUTS and tool.PAYOUTS != tool.FULFILMENT))
check("and the stock file is under services, not with either",
      answered(lambda: "/services/" in tool.SERVICES and tool.SERVICES != tool.FULFILMENT))
# **THE ONE THAT WOULD HAVE CAUGHT THE FAULT:** every Meesho report must go to the
# section it really lives in.
WHERE_EACH_GOES = {
    "me_orders": "/fulfillment/", "me_returns": "/fulfillment/",
    "me_claims": "/fulfillment/",
    "me_payments": "/payouts/", "me_catalog": "/services/",
}
check("each Meesho report goes to the section it really lives in",
      answered(lambda: all(
          any(section in s.address for s in tool.RECIPES[r].to_take if s.address)
          for r, section in WHERE_EACH_GOES.items())))
check("and not one of them is asked for under the dashboard's own section",
      answered(lambda: not any(
          "/growth/" in s.address
          for r in WHERE_EACH_GOES for s in tool.RECIPES[r].to_take if s.address)))
# **THE TAB IS PART OF THE ADDRESS ON RETURNS**, and it is the one carrying what
# has actually come back.
check("returns names the tab it needs in the address itself",
      answered(lambda: any("returnTracking" in s.address
                           for s in tool.RECIPES["me_returns"].to_take if s.address)))
check("a Meesho recipe asked for without one is refused", answered(lambda: refuses(lambda: tool.steps_for("me_orders", ""))))
check("with a reason saying it is the seller's own data",
      answered(lambda: "seller's own data" in said(lambda: tool.steps_for("me_orders", ""))))
# **FLIPKART NEEDS NONE**, so it is not asked for -- a requirement that applies to
# one platform must not block the other.
check("while a Flipkart recipe needs no panel name at all",
      answered(lambda: tool.steps_for("fk_claims", "")[0].address.startswith("https://seller.flipkart.com/")))
check("the panel name really is filled in", answered(lambda: PANEL in tool.steps_for("me_orders", PANEL)[0].address))
check("a report with no recipe is refused", answered(lambda: refuses(lambda: tool.recipe("me_nonsense"))))
check("and so is asking for its steps", answered(lambda: refuses(lambda: tool.steps_for("me_nonsense", PANEL))))

# ------------------------------------------- reached by address, every one

for report_id in tool.every_recipe():
    first = tool.steps_for(report_id, PANEL)[0]
    check(f"{report_id} reaches its page by address rather than by clicking about",
          answered(lambda: first.do == pages.GO and first.address.startswith("https://")))

# ------------------------------------------- which platform needs a browser

# **THESE TWO SAID "STILL NEED A BROWSER" AND COUNTED RECIPES, WHICH IS NOT THE
# SAME NUMBER.** `reports.py` declares fourteen Flipkart reports and seven Meesho
# ones on this door. Thirteen and four had a recipe. So both checks were green
# while four declared reports had nothing at all behind them, and nothing
# anywhere in the project said so -- the door was being measured by what it had
# built rather than by what it had been asked for. They now say what they count,
# and the coverage check below is the one that holds the two together.
check("thirteen Flipkart reports can be fetched by this door",
      answered(lambda: len(tool.on_the_browser_door_for("flipkart")) == 13))
check("and five Meesho ones", answered(lambda: len(tool.on_the_browser_door_for("meesho")) == 5))
# **AMAZON NEEDS NONE, and that is the number the others should fall to.**
check("Amazon needs none at all", answered(lambda: tool.on_the_browser_door_for("amazon") == ()))
check("a platform this does not know is refused", answered(lambda: refuses(lambda: tool.on_the_browser_door_for("etsy"))))
# The prefix is written down, not worked out. `platform[:2]` gives "fl" for
# Flipkart while every id begins `fk_`, which answered zero -- the opposite of
# the truth, and exactly the number this is for.
check("the prefixes are written down rather than derived from the name",
      answered(lambda: tool.PREFIXES["flipkart"] == "fk_"))

# ------------------------------- declared and built, held against each other

# **THE HOLE THIS CLOSES.** `reports.py` is the one list of what Kartaan fetches.
# This file is how the browser ones are fetched. Nothing anywhere compared the
# two, so a report could be declared and simply never fetched -- and four were:
# `fk_keywords`, `me_views`, `me_ads` and `me_claims`. `me_claims` has a recipe
# now; the ads sweep, declared as the three files it really is, brought two more
# with it -- so five stand here today. Every check about the door counted
# recipes, so every check was green.
#
# **THE RULE IS NOT "EVERY REPORT HAS A RECIPE".** Some genuinely cannot be
# fetched by this door yet. The rule is that every one of them is accounted for:
# built, or named with the reason it is not. A report that is neither is a report
# nobody will ever notice is missing.
DECLARED_ON_THE_BROWSER_DOOR = {
    rid for rid, r in KARTAAN_REPORTS.items() if r.door == NEEDS_A_BROWSER
}
check("every report that needs a browser is either built or says why it is not",
      answered(lambda: DECLARED_ON_THE_BROWSER_DOOR
               == set(tool.RECIPES) | set(tool.NOT_YET_A_RECIPE)))
check("and none of them is called both built and not built",
      answered(lambda: not set(tool.RECIPES) & set(tool.NOT_YET_A_RECIPE)))
# **NAMED ONE BY ONE RATHER THAN COUNTED.** A count taken from the list it checks
# moves with the list, so one of these quietly gaining a recipe -- or quietly
# losing one -- would look like the list simply being a different length. These
# five are the whole of what this door cannot reach, and the number should fall.
check("the five it cannot reach are exactly these five",
      answered(lambda: set(tool.NOT_YET_A_RECIPE) == {
          "fk_keywords", "me_views", "me_ads", "me_ads_summary", "me_ads_catalog"}))
check("each of them is a report Kartaan actually declares",
      answered(lambda: all(rid in KARTAAN_REPORTS for rid in tool.NOT_YET_A_RECIPE)))
# **A REFUSAL WITHOUT A REASON IS THE THING THE FIELD EXISTS TO PREVENT**, and
# the same holds here: "there is no recipe" tells the next person nothing at all
# about whether one can be written.
check("and each says why, in a sentence somebody can read",
      answered(lambda: all(len(why.split()) >= 8 for why in tool.NOT_YET_A_RECIPE.values())))
# The other way round: a recipe for something nobody declared would be fetched
# every night and land nowhere, because the file it lands as is named from the
# declaration.
check("and no recipe exists for something that was never declared",
      answered(lambda: set(tool.RECIPES) <= set(KARTAAN_REPORTS)))

# ------------------------------------------------------------ the records

check("a recipe cannot be edited after it is written",
      answered(lambda: refuses(lambda: setattr(tool.recipe("me_orders"), "ready_in_minutes", 99))))


# **A PLAIN NUMBER, not one worked out from the lists it is checking.** A count
# derived from the thing it measures moves with it, so a recipe disappearing looks
# like the list simply being shorter -- which the prover already caught once in
# this package.
# ------------------------------------------- which ROW something is on

# **HIS OWN RETURNS PAGE KEEPS EVERY EXPORT EVER MADE**, ten of them on
# 2026-08-28, each row reading `completed_delivered_last_2_week | 25 Aug 2026,
# 04:49 PM | Download`. Looking for "Download" finds ten and refuses -- right,
# and useless. The recipe knows which day it wants, so it says so.
NAMED_ROWS = [s.find for r in tool.RECIPES.values()
              for s in (r.to_ask + r.to_take) if s.find is not None and s.find.near]
check("something on the returns page is asked for by its row",
      answered(lambda: len(NAMED_ROWS) >= 1))
# **AND EVERY ONE OF THEM NAMES THE DAY.** A row named by something that never
# changes is the same row for ever -- it would fetch the same old file every
# night while looking like it worked.
check("and every row named is named by the day, one way or the other",
      answered(lambda: all("{day}" in f.near or "{day_in_words}" in f.near
                           for f in NAMED_ROWS)))

# **TWO WAYS OF WRITING A DAY, BOTH NEEDED, BOTH ON MEESHO**, read off his own
# panel on 2026-08-28.
#
# An ORDERS row reads `2026-08-23_2026-08-23_2026-08-28 | 25 Aug 2026, 04:47 PM |
# Download` -- the day it is ABOUT written plainly, and the day it was MADE in
# words. **The day it is about is the stronger of the two**: it still finds the
# right file when an older day is being fetched, which is exactly when it
# matters.
check("the orders file is named by the day it is ABOUT",
      answered(lambda: any(s.find is not None and s.find.near == "{day}"
                           for s in tool.RECIPES["me_orders"].to_take)))
# A RETURNS row carries no data date at all -- a returns export is always the
# last two weeks -- so all it has is the day it was made, in the platform's own
# wording.
check("while the returns file can only be named by the day it was MADE",
      answered(lambda: any(s.find is not None and s.find.near == "{day_in_words}"
                           for s in tool.RECIPES["me_returns"].to_take)))
# A recipe that named a row without the day is refused outright.
check("a row named without the day is refused",
      answered(lambda: pages.why_step_is_refused(pages.Step(
          pages.CLICK, find=pages.Find(pages.BY_TEXT, "Download", near="Exported Files"),
          why="x")) is not None))
check("and one that names the day is not",
      answered(lambda: pages.why_step_is_refused(pages.Step(
          pages.CLICK, find=pages.Find(pages.BY_TEXT, "Download", near="{day}"),
          why="x")) is None))

# **HOW MEESHO WRITES A DAY, read off that page: `25 Aug 2026`.**
check("a day is written the way Meesho writes one",
      answered(lambda: tool.as_meesho_writes_a_day(date(2026, 8, 25)) == "25 Aug 2026"))
# **NO LEADING NOUGHT.** The page shows `1 Sep 2026`, and "01 Sep 2026" is on no
# row at all -- which would find nothing, every time, for nine days a month.
check("with no leading nought, which is what the page shows",
      answered(lambda: tool.as_meesho_writes_a_day(date(2026, 9, 1)) == "1 Sep 2026"))
check("and the month by name, not by number",
      answered(lambda: tool.as_meesho_writes_a_day(date(2026, 12, 31)) == "31 Dec 2026"))


# ------------------------- which way each platform is looked at, and why

# **READ OFF BOTH OF HIS REAL PANELS ON 2026-08-27.** Meesho's has no control on
# it at all -- no button, no link, no role attribute anywhere -- so asking for a
# control there finds nothing, ever, and every Meesho report would have reported
# a renamed button that was never a button. Flipkart's dashboard has thirty-two
# painted controls and eight kinds of role.
MEESHO_LOOKUPS = [s.find for r in ("me_orders", "me_catalog", "me_returns", "me_payments",
                                   "me_claims")
                  for s in (tool.RECIPES[r].to_ask + tool.RECIPES[r].to_take) if s.find]
FLIPKART_LOOKUPS = [s.find for r in tool.every_recipe() if r.startswith("fk_")
                    for s in (tool.RECIPES[r].to_ask + tool.RECIPES[r].to_take) if s.find]

check("there are Meesho lookups to judge", answered(lambda: len(MEESHO_LOOKUPS) > 10))
check("and NOT ONE of them asks for a control, because Meesho has none",
      answered(lambda: not any(f.how == tool.BY_ROLE_AND_TEXT for f in MEESHO_LOOKUPS)))
check("every Meesho lookup is by words or by pressable words",
      answered(lambda: all(f.how in (tool.BY_TEXT, tool.BY_PRESSABLE_TEXT)
                           for f in MEESHO_LOOKUPS)))
# **AND FLIPKART IS NOT MOVED WITH IT.** A finding about one platform applied to
# the other is how a working thing gets broken alongside a broken one.
check("Flipkart still asks for controls, which it really has",
      answered(lambda: any(f.how == tool.BY_ROLE_AND_TEXT for f in FLIPKART_LOOKUPS)))

# **BUT EVERY MENU ITEM IS ASKED FOR AS A PRESSABLE THING ON BOTH PLATFORMS**,
# and that is measured. On his own Flipkart Reports Centre with the request
# dialog open: `Fulfilment Reports` as WORDS matches EIGHT things and refuses;
# as something pressable, one. `Orders` as words matches three; pressable, one.
# The words are in headings and in the list of reports already requested -- only
# one of them can be pressed.
CLICKED = [s.find for r in tool.RECIPES.values()
           for s in (r.to_ask + r.to_take) if s.do == pages.CLICK and s.find is not None]
check("there are things being clicked to judge", answered(lambda: len(CLICKED) > 20))
check("and not one of them is asked for as plain words on the page",
      answered(lambda: not any(f.how == tool.BY_TEXT for f in CLICKED)))
check("every one of them is asked for as something a person can press",
      answered(lambda: all(f.how in (tool.BY_PRESSABLE_TEXT, tool.BY_ROLE_AND_TEXT)
                           for f in CLICKED)))
# **WAITING IS DIFFERENT FROM PRESSING.** Waiting for a heading or a status to
# appear is safe as plain words -- it presses nothing.
check("while waiting for something may still be plain words, because it presses nothing",
      answered(lambda: any(s.find.how == tool.BY_TEXT for r in tool.RECIPES.values()
                           for s in (r.to_ask + r.to_take)
                           if s.do == pages.WAIT_FOR and s.find is not None)))


# ------------------------------------- how a signed-out portal is known

# **FOUND BY LOADING THE EXTENSION INTO A REAL CHROME**, which refused to build a
# door at all because this list did not exist yet. It said so out loud rather
# than answering "signed in" for ever, which is what the refusal is for.
check("there are words that only a signed-out portal shows",
      answered(lambda: len(tool.SIGNED_OUT_SIGNS) >= 2))
# **TWO OF THEM ARE NEEDED ON A PAGE.** One turns up on a signed-in page easily
# -- Flipkart's own signed-in sidebar carries "Growth" -- while the public menu
# carries the whole set at once. Fewer than two here and the rule could never
# fire at all.
check("they are Flipkart's public marketing menu, read off the real signed-out site",
      answered(lambda: "Fees and Commission" in tool.SIGNED_OUT_SIGNS
               and "Shopsy" in tool.SIGNED_OUT_SIGNS))
# **NOT A WORD OF A SIGNED-IN PAGE.** A sign that also appears once somebody is
# signed in would pause every run for a reason that is not true.
check("and none of them is a word the seller's own panel uses",
      answered(lambda: "Growth" not in tool.SIGNED_OUT_SIGNS
               and "Orders" not in tool.SIGNED_OUT_SIGNS))
# **MEESHO IS DELIBERATELY NOT IN IT.** Its signed-out page is a sign-in form,
# and a box asking for a password is a portal asking whoever reads it. Nothing
# has been read off a signed-out Meesho panel, and a guess would be worse.
check("nothing is guessed about Meesho, which is answered by the password box",
      answered(lambda: not any("meesho" in one.lower() for one in tool.SIGNED_OUT_SIGNS)))
# They ship to every seller, so nothing of one seller's is in them.
check("and none of them names a panel or an address",
      answered(lambda: not any("/" in one or "." in one for one in tool.SIGNED_OUT_SIGNS)))


# **AND NOTHING ABOVE ENDED BY THROWING RATHER THAN BY ANSWERING.** Answering
# with nothing keeps the run alive; this is what stops a check phrased as "this
# word is NOT in what it said" going green because there was nothing to look in.
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)


EXPECTED = 217
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
