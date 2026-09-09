"""Checks for driving a page, with no browser anywhere.

**A FAKE MEESHO, DELIBERATELY AWKWARD.** It covers itself with a promotion the
way the real one does, it offers two things of the same name the way the payments
page does, and it hands back nothing when a file is built inside the page. A
stand-in kinder than the real thing is this project's most expensive recurring
fault -- four times over -- so this one is written to be nasty.

**AND THE MOST IMPORTANT CHECK IS THAT THIS DOOR ANSWERS EXACTLY WHAT THE AMAZON
DOOR ANSWERS.** If the runner can tell them apart, D100's whole idea -- one report
list, one log, one board, the door a detail underneath -- is not true.

Run: python autosync/browser_door_checks.py
"""

import dataclasses
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import browser as pages  # noqa: E402
import recipes as book  # noqa: E402
import browser_door as tool  # noqa: E402
import amazon_door  # noqa: E402

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


DAY = date(2026, 8, 26)
# **THE SLUG ALONE**, the short word in the middle of every Meesho address --
# not the section around it, which is Meesho's own and lives in the recipe.
PANEL = "some-slug"

SAID = []


def say(line):
    SAID.append(line)


class FakeMeesho:
    """The Meesho panel, as it really behaves."""

    def __init__(self, **how):
        self.how = how
        self.went = []
        self.clicked = []
        self.ranges = []
        self.cursor_told_for = []
        self.steps_seen = 0
        # **HOW LONG IT WAS TOLD TO WAIT, kept for every call that can wait.**
        # These numbers are set on every step in the recipe book and none of
        # them used to arrive here at all, so a page that draws in its own time
        # was read as a page that had renamed its buttons.
        self.patience_told = []
        # **HOW LONG IT WAS TOLD TO PASS, AND IN WHAT ORDER THINGS HAPPENED.**
        # Meesho's orders export is built where the page cannot see it, so the
        # recipe can only wait -- and whether the wait came before or after the
        # page was loaded again is the whole of whether it works. Nothing is
        # really slept for; the numbers are kept.
        self.waited = []
        self.order = []
        # **THE MENU, AS MEESHO REALLY BEHAVES.** Its list of finished exports is
        # drawn AS it opens and never again while it is open. So the stand-in
        # holds the two facts that follow from that and nothing else: whether it
        # is open, and how many times it has been SHUT and opened again. Counting
        # clicks instead would let a loop that never shut it pass.
        self.menu_open = False
        self.shut_since_last_opened = False
        self.reopened = 0
        self.clicked_away = 0

    # -- what the door asks it
    def go(self, address, patience):
        self.went.append(address)
        self.order.append("went")
        self.patience_told.append(("go", patience))
        # A page that has been loaded again has nothing open on it.
        self.menu_open = False
        self.shut_since_last_opened = False

    def wait(self, seconds):
        self.waited.append(seconds)
        self.order.append(f"waited {seconds}")
        self.patience_told.append(("wait", seconds))

    def needs_signing_in(self):
        return bool(self.how.get("signed_out"))

    def overlays(self):
        # **COVERED ONLY FROM A GIVEN STEP ONWARDS**, so the check can put the
        # promotion in front of the LAST step rather than the first -- which is
        # how it really behaves when it appears while a page is working.
        after = self.how.get("covered_after")
        if after is not None and self.steps_seen < after:
            return []
        if self.how.get("covered") or after is not None:
            # **THE REAL ONE, off his own Chrome.**
            # **A PROMOTION ON A FULL-SCREEN BACKDROP.** The backdrop is what a
            # click aimed at the page hits and it carries no words of its own;
            # the words are on the panel sitting on it.
            return [
                {"width": 1280, "height": 800, "text": "", "blocks": True},
                {"width": 414, "height": 330,
                 "text": "Abhi Update Karein ! Participate Now", "blocks": False},
            ]
        if self.how.get("own_menu"):
            # **THE DOWNLOAD MENU THE RECIPE OPENS ITSELF**, measured on his own
            # payments page: a dialog, 232 x 196, laid over nothing.
            # **MEASURED ON HIS OWN INVENTORY PAGE.** The "Bulk Stock Update"
            # panel the recipe opens sits on a backdrop the size of the whole
            # window -- and the Download it wants is inside it.
            return [
                {"width": 1600, "height": 664,
                 "text": "Bulk Stock Update Step 1 Download", "blocks": True},
                {"width": 280, "height": 136,
                 "text": "Bulk Stock Update Step 1 Download", "blocks": False},
            ]
        if self.how.get("small_notice"):
            return [{"width": 250, "height": 60, "text": "Saved", "blocks": False}]
        return []

    def find(self, how, what, exact, patience, near=""):
        self.steps_seen += 1
        self.patience_told.append(("find", patience))
        # **THE FINISHED FILE IS NOT IN THE LIST YET, and this is the only way to
        # say so.** Meesho draws the list of finished exports as the download
        # menu OPENS, so the list only ever changes when the menu is shut and
        # opened again. Here the row appears once the menu has been reopened this
        # many times -- and with nothing reopening it, it never appears at all.
        reopens = self.how.get("appears_after_reopens")
        if reopens is not None and what == "Download" and near:
            return 1 if self.menu_open and self.reopened >= reopens else 0
        if not self._opener_still_there(what):
            return 0
        at = self.how.get("matches_at_step")
        if at and self.steps_seen in at:
            return at[self.steps_seen]
        matches = self.how.get("matches", {})
        if what in matches:
            return matches[what]
        if self.how.get("nothing_at_all"):
            return 0
        # **A PROMOTION HIDES WHAT IS UNDERNEATH IT.** That is what makes a
        # covering worth reporting: the lookup fails, and the reason is not that
        # the button was renamed. A panel the recipe opened itself hides nothing
        # -- it CONTAINS the thing being looked for -- which is why `own_menu`
        # leaves this alone.
        after = self.how.get("covered_after")
        if self.how.get("covered") or (after is not None and self.steps_seen > after):
            return 0
        return 1

    def _opener_still_there(self, what):
        """Is the download menu's opener still on the page?

        **A CONTROL THE PORTAL TAKES AWAY PART WAY THROUGH.** Meesho redraws its
        own page while a walk is on it, and the opener being there when the walk
        arrived does not mean it is still there a round later. Told to, this one
        takes it away the moment the menu is shut -- which is the one moment in
        the whole walk when nothing is holding it open.
        """
        if not self.how.get("opener_goes_when_shut") or what != "Download Orders Data":
            return True
        return not self.clicked_away

    def click(self, how, what, exact, near=""):
        # **A CONTROL THAT IS NOT THERE CANNOT BE CLICKED, AND THE REAL DOOR
        # THROWS.** `driver.js` looks the thing up and refuses when nothing
        # matches. A stand-in that quietly accepted the click would let a door
        # which never checked first look exactly like one that did.
        if not self._opener_still_there(what):
            raise RuntimeError(
                "Nothing on the page matches 'Download Orders Data'."
            )
        self.clicked.append(what)
        self.order.append(f"clicked {what}")
        # **OPENING A SHUT MENU IS THE ONLY THING THAT REDRAWS ITS LIST.** Pressed
        # while it is already open, this counts for nothing at all -- which is
        # exactly what a second press of the opener would be worth if Meesho's
        # opener does not toggle, and the whole reason the shutting is a click
        # away rather than a second press.
        if not self.menu_open:
            self.menu_open = True
            if self.shut_since_last_opened:
                self.reopened += 1
                self.shut_since_last_opened = False

    def click_away(self):
        # **CLICKING WHERE NOTHING IS SHUTS WHAT IS OPEN**, which is the
        # reference's own gesture (`content/meesho.js:865`).
        self.clicked_away += 1
        self.order.append("clicked away")
        self.menu_open = False
        self.shut_since_last_opened = True

    def pick_range(self, start, end, patience, also_by_the_cursor):
        self.ranges.append((start, end))
        # **WHICH CALENDAR IT IS STANDING IN FRONT OF IS KEPT TOO.** Flipkart
        # switches a day off two ways and one of them shows only in the cursor;
        # a stand-in that dropped it would let the recipe say so and the door
        # never hear it, with nothing anywhere looking wrong.
        self.cursor_told_for.append(also_by_the_cursor)
        self.patience_told.append(("pick_range", patience))

    def take_file(self, patience):
        self.patience_told.append(("take_file", patience))
        if self.how.get("built_in_page"):
            return None
        if self.how.get("empty_file"):
            return b""
        return self.how.get("bytes", b"sub-order,sku\n1,ABC\n")

    def page_text(self):
        return self.how.get("page", "Welcome back   Manage and grow your business")


# **A RUN THAT STOPS IS NOT A CHECK GOING RED.**
#
# The proving tool breaks one line of the door at a time and requires a check to
# notice. Sixty-one of those breakages were "noticed" only by this file falling
# over with a traceback -- no FAIL printed, nothing said about whether any check
# here is any good. It is the same shape as a checks file printing FAIL and
# exiting 0, and it has been found and fixed twice already in this project: fifty
# -one of them in `dev_server_checks.py` and a hundred and nine in
# `check_product_checks.py`, both cured the same way -- **the call is asked
# through something that answers with NOTHING when it throws, so the check
# compares against what it expected and goes red.**
THREW = []

# What "it threw instead of answering" looks like. **Deliberately not one of the
# four words a real answer uses**, and everything else left empty, so every
# assertion made about a real answer fails against it.
NOTHING = tool.Fetched(state="it threw instead of answering", report_id="", data_date=DAY)


def a_fetch(fake, panel=PANEL):
    """The door, with anything it throws turned into an answer of nothing.

    **THE SIGNED-OUT CASE DOES NOT COME THROUGH HERE.** `NeedsSigningIn` is a
    deliberate answer rather than a fault, and the check for it calls the door
    directly so that it can catch it by name -- while one raised anywhere else
    lands in THREW below and goes red, which is what it should do.
    """
    door = tool.a_door(fake, panel, say)

    def fetch(report_id, day, **rest):
        try:
            return door(report_id, day, **rest)
        except Exception as wrong:  # noqa: BLE001 -- a door that threw answered nothing
            THREW.append(f"{report_id}: {wrong!r}")
            return NOTHING

    return fetch


# ------------------------------------------------ it answers what Amazon answers

# **IF THE RUNNER CAN TELL THE DOORS APART, D100 IS NOT TRUE.**
check("the two doors use the same four words for what happened",
      answered(lambda: (tool.LANDED, tool.NOTHING_TO_FETCH, tool.STILL_WAITING, tool.FAILED)
      == (amazon_door.LANDED, amazon_door.NOTHING_TO_FETCH, amazon_door.STILL_WAITING, amazon_door.FAILED)))
mine = {f.name for f in tool.Fetched.__dataclass_fields__.values()}
theirs = {f.name for f in amazon_door.Fetched.__dataclass_fields__.values()}
check("and everything the Amazon door answers, this one answers too", answered(lambda: theirs <= mine))
# The door is handed to the runner as the same callable shape.
fetch = a_fetch(FakeMeesho())
check("and it takes the same three things the runner passes",
      answered(lambda: fetch("me_orders", DAY, asked_already=None).report_id == "me_orders"))

# ------------------------------------------------------------ an ordinary run

SAID.clear()
fake = FakeMeesho()
got = a_fetch(fake)("me_orders", DAY)
check("a report is fetched all the way through", answered(lambda: got.state == tool.LANDED))
check("named for its platform, report and day", answered(lambda: got.file_name == "meesho_me_orders_2026-08-26.csv"))
check("and the bytes are counted", answered(lambda: got.size > 0))
# **REACHED BY ADDRESS.** That is what steps round the promotion.
check("it went straight to the page's address", answered(lambda: any("/orders" in a for a in fake.went)))
check("and the panel name was filled in", answered(lambda: any(PANEL in a for a in fake.went)))
check("the date range was set to the day being fetched", answered(lambda: fake.ranges == [(DAY, DAY)]))
# **AND MEESHO'S CALENDAR IS TOLD THE OPPOSITE, plainly rather than by omission.**
# "Anything that is not a pointer is switched off" is Flipkart's own habit; read
# on Meesho's calendar it would refuse days that are perfectly available.
check("and Meesho's calendar was told it is not one that says so in the cursor",
      answered(lambda: fake.cursor_told_for == [False]))
check("and every step said what it was doing", answered(lambda: len(SAID) > 0))

# The catalogue has no date range at all -- it is a picture of right now.
fake = FakeMeesho()
a_fetch(fake)("me_catalog", DAY)
check("a snapshot report is not asked for a date range", answered(lambda: fake.ranges == []))

# ---------------------------- SOMETHING COVERING THE PAGE IS ITS OWN FAILURE

# **THE FAULT FOUND IN HIS OWN CHROME ON 2026-08-27.** Every one of me_orders,
# me_catalog and me_returns had been reporting this as "button not found" for a
# month, which sent a month of diagnosis at the wrong thing.
fake = FakeMeesho(covered=True)
got = a_fetch(fake)("me_orders", DAY)
check("a promotion covering the panel is a failure", answered(lambda: got.state == tool.FAILED))
check("and it says the page is covered, NOT that a button is missing",
      answered(lambda: "covering the page" in got.say and "renamed" not in got.say))
check("and it says the button is there, underneath", answered(lambda: "underneath something" in got.say))
check("nothing was clicked while something was in the way", answered(lambda: fake.clicked == []))
# **THE PAGE IS CAPTURED, AUTOMATICALLY.**
check("and what was on the page is kept with the failure", answered(lambda: got.page_was != ""))

# A small notice is ordinary furniture and does not stop anything.
# **AND NEITHER DOES THE DOOR'S OWN DOWNLOAD MENU.** Judged by size it was four
# pixels from stopping every Meesho report because of a menu the door opened.
fake = FakeMeesho(own_menu=True)
check("a panel the door opened itself, over the whole window, does not stop the run",
      a_fetch(fake)("me_orders", DAY).state == tool.LANDED)

fake = FakeMeesho(small_notice=True)
check("a small notice does not stop the run", answered(lambda: a_fetch(fake)("me_orders", DAY).state == tool.LANDED))

# ------------------------------ AMBIGUITY IS A FAILURE, NOT A COIN TOSS

# **THE NINE-DAY PAYMENTS OUTAGE.** A chart legend read "Payments to Date",
# exactly like the menu item, and sat earlier in the page.
fake = FakeMeesho(matches={"Payments to Date": 2})
got = a_fetch(fake)("me_payments", DAY)
check("two things of the same name is a failure", answered(lambda: got.state == tool.FAILED))
check("and it says how many matched", answered(lambda: "2 things match" in got.say))
check("and that NOTHING was clicked", answered(lambda: "Nothing was clicked" in got.say))
check("and nothing really was", answered(lambda: "Payments to Date" not in fake.clicked))
check("and the page is kept so it can be worked out", answered(lambda: got.page_was != ""))

# ------------------------------------------------ a thing that is not there

fake = FakeMeesho(matches={"Download Orders Data": 0})
got = a_fetch(fake)("me_orders", DAY)
check("something that is not on the page is a failure", answered(lambda: got.state == tool.FAILED))
check("and it says what was being attempted, not only what was missing",
      answered(lambda: "waiting for the orders page" in got.say))
check("and names the thing in words a person reads", answered(lambda: "the download menu" in got.say))
check("and suggests it may have been renamed", answered(lambda: "renamed" in got.say))
check("and keeps the page", answered(lambda: got.page_was != ""))

# ------------------------- A FILE BUILT INSIDE THE PAGE IS A DOOR CLOSING

# **Flipkart started doing this on 2026-08-22.** An extension cannot fetch that
# handle twice; retrying it for ever is doing nothing slowly.
fake = FakeMeesho(built_in_page=True)
got = a_fetch(fake)("me_orders", DAY)
check("a file built inside the page is a failure", answered(lambda: got.state == tool.FAILED))
check("and it says the platform changed how it hands the file over",
      answered(lambda: "builds this file inside the page" in got.say))
check("and that it is a door closing rather than something to retry", answered(lambda: "door closing" in got.say))

# A file of nothing is not an arrival.
fake = FakeMeesho(empty_file=True)
got = a_fetch(fake)("me_orders", DAY)
check("a file with nothing in it does not land", answered(lambda: got.state == tool.FAILED))
check("and says nothing was written", answered(lambda: "nothing has been written" in got.say))

# ------------------------- SIGNING IN IS NOT THIS REPORT'S FAULT

# **EVERY REPORT AFTER IT WOULD HIT THE SAME WALL.** Calling each of them broken
# buries the one thing that actually needs doing -- and the reference's queue died
# on the spot, abandoning every report behind it.
fake = FakeMeesho(signed_out=True)
was_its_own_kind = False
# **SET BEFORE THE TRY, not inside it.** Written only where it is raised, a
# change that stops it being raised leaves the two checks below reading a name
# that does not exist -- and the run ends with a NameError instead of going red,
# which says nothing about whether these checks are any good.
message = ""
try:
    tool.a_door(fake, PANEL, say)("me_orders", DAY)
except tool.NeedsSigningIn as wrong:
    was_its_own_kind = True
    message = str(wrong)
check("being signed out is its own kind of problem", answered(lambda: was_its_own_kind is True))
check("and it says nothing can be fetched until somebody signs in", answered(lambda: "until somebody does" in message))
check("and that every report after it would fail the same way", answered(lambda: "every report after this one" in message))

# --------------------------------------------------- a recipe that is wrong

fake = FakeMeesho()
got = a_fetch(fake)("me_nonsense", DAY)
check("a report nobody has ever heard of is a failure, not a crash", answered(lambda: got.state == tool.FAILED))
check("and it says Kartaan does not know it", answered(lambda: "not a report Kartaan knows about" in got.say))

# **A REPORT KARTAAN KNOWS BUT THIS DOOR HAS NO RECIPE FOR IS A DIFFERENT THING**,
# and it says so. `fk_keywords` is real and deliberately has no recipe: it needs
# somebody sitting on the page, so it is named that way in the report list rather
# than pretended at here.
quiet_fake = FakeMeesho()
got = a_fetch(quiet_fake)("fk_keywords", DAY)
check("a real report this door has no recipe for is a failure", answered(lambda: got.state == tool.FAILED))
check("and says the browser door does not know how to fetch it",
      answered(lambda: "browser door knows how to fetch" in got.say))
check("and nothing was driven at all", answered(lambda: quiet_fake.went == []))
# **AND AN AMAZON REPORT IS NOT DRIVEN THROUGH A BROWSER EITHER.** It has an API
# door; reaching it through this one would be fetching the same thing twice.
check("an Amazon report is refused by the browser door",
      answered(lambda: a_fetch(FakeMeesho())("az_orders", DAY).state == tool.FAILED))

# **A BAD RECIPE IS A FAULT IN THE PRODUCT, and says so** -- rather than reading
# as the platform having changed, which would send somebody to look at Meesho.
bad = a_fetch(FakeMeesho(), "")
got = bad("me_orders", DAY)
check("a door with no panel name is a failure", answered(lambda: got.state == tool.FAILED))
check("and it says the panel name is the seller's own data", answered(lambda: "seller's own data" in got.say))


# ---------------------------------------- clicking, and NOT clicking

# **A `WAIT_FOR` STEP LOOKS BUT DOES NOT CLICK.** Without that difference the
# door would click the thing it was only waiting to appear -- on the orders page
# that is the download menu, opened once and then opened again, which closes it.
fake = FakeMeesho()
a_fetch(fake)("me_orders", DAY)
clicked = fake.clicked
# The last one is the download itself: a take-file step names what to press
# before it collects, so it appears here too.
check("the things meant to be clicked were clicked",
      answered(lambda: clicked == ["Download Orders Data", "Select Date Range", "Export data",
                                   "Download Orders Data", "Download"]))
# **THE MENU IS OPENED TWICE AND WAITED FOR TWICE**, because the page is loaded
# again in between -- Meesho does not show a finished file until it is. So the
# menu is in the recipe four times (waited for, clicked, waited for, clicked) and
# among the clicks exactly twice.
check("the menu is opened once per visit, not once per time it is waited for",
      answered(lambda: clicked.count("Download Orders Data") == 2))
check("and the page really was loaded twice",
      answered(lambda: sum(1 for a in fake.went if a.endswith("/orders/")) == 2))
# The catalogue's single click, to be sure it is not the orders recipe answering.
fake = FakeMeesho()
a_fetch(fake)("me_catalog", DAY)
check("the catalogue clicks only what it needs to", answered(lambda: fake.clicked == ["Bulk Stock Update", "Download"]))

# ------------------------------- the LAST step has the same guards as the rest

# **SOMETHING COVERING THE PAGE AT THE MOMENT THE FILE IS TAKEN.** The promotion
# does not always arrive first; a run that had got all the way to the download and
# then hit one would otherwise report a missing button.
# Two finds happen before the last step, so this puts the promotion in front
# of the download and nothing earlier.
fake = FakeMeesho(covered_after=2)
got = a_fetch(fake)("me_catalog", DAY)
check("a page covered at the last step is still reported as covered", answered(lambda: got.state == tool.FAILED))
check("and says so rather than blaming the download", answered(lambda: "covering the page" in got.say))
check("and keeps the page", answered(lambda: got.page_was != ""))

# The file's own control missing.
fake = FakeMeesho(matches={"Download": 0})
got = a_fetch(fake)("me_catalog", DAY)
check("no download control at the last step is a failure", answered(lambda: got.state == tool.FAILED))
check("and it says what was being attempted", answered(lambda: "taking the stock file" in got.say))
# **THE PAGE IS KEPT AT THE LAST STEP TOO.** Every failure carries its evidence,
# not only the ones early in the recipe -- and the last step is where the reference
# lost most of its files.
check("and the page is kept, exactly as for a failure earlier in the recipe", answered(lambda: got.page_was != ""))

# Two of them -- ambiguity at the last step refuses, exactly as anywhere else.
fake = FakeMeesho(matches={"Download": 3})
got = a_fetch(fake)("me_catalog", DAY)
check("several download controls is a failure, not a guess", answered(lambda: got.state == tool.FAILED))
check("and it says how many", answered(lambda: "3 things match" in got.say))
check("and nothing was clicked", answered(lambda: "Download" not in fake.clicked))

# **THE PAGE IS KEPT WHEN THE FILE IS BUILT INSIDE IT TOO.**
fake = FakeMeesho(built_in_page=True)
got = a_fetch(fake)("me_catalog", DAY)
check("a file built in the page keeps the page as well", answered(lambda: got.page_was != ""))

# ------------------------------------ a recipe that never takes a file

# **A RECIPE THAT CLICKS ABOUT AND TAKES NOTHING RUNS PERFECTLY AND PRODUCES
# NOTHING**, which reads as the platform being broken. It says what it really is.
was = dict(book.RECIPES)
try:
    book.RECIPES["me_orders"] = book.Recipe(to_take=(
        pages.Step(pages.GO, address=book.FULFILMENT + "/orders/", why="opening the page"),
        pages.Step(pages.CLICK, find=pages.Find(pages.BY_TEXT, "Something"), why="clicking about"),
    ))
    got = a_fetch(FakeMeesho())("me_orders", DAY)
    check("a recipe that never takes a file is a failure", answered(lambda: got.state == tool.FAILED))
    check("and it says the recipe is missing its last step",
          answered(lambda: "missing its last step" in got.say))
    check("and does not blame the platform", answered(lambda: "renamed" not in got.say and "covering" not in got.say))

    # A take-file step that names nothing to click still takes whatever came.
    book.RECIPES["me_orders"] = book.Recipe(to_take=(
        pages.Step(pages.GO, address=book.FULFILMENT + "/orders/", why="opening the page"),
        pages.Step(pages.TAKE_FILE, why="taking whatever the page produced"),
    ))
    fake = FakeMeesho()
    got = a_fetch(fake)("me_orders", DAY)
    check("a take-file step with nothing to click still takes the file", answered(lambda: got.state == tool.LANDED))
    check("and clicked nothing on the way", answered(lambda: fake.clicked == []))
finally:
    book.RECIPES.clear()
    book.RECIPES.update(was)

check("and the real recipes are back afterwards", answered(lambda: len(book.every_recipe()) == 18))

# ------------------------------------------------------------ the record

def _cannot_edit(thing, field, value):
    try:
        setattr(thing, field, value)
    except AttributeError:
        return True
    return False


check("what a fetch came to cannot be edited afterwards",
      answered(lambda: _cannot_edit(tool.Fetched(tool.LANDED, "me_orders", DAY), "state", tool.FAILED)))


# ------------------------- TWO-PHASE: ASKED ONCE, COLLECTED LATER

# **FLIPKART'S REPORTS CENTRE ALLOWS TWENTY REQUESTS A DAY.** The reference burned
# through them re-submitting reports that had actually worked, then spent the rest
# of the day locked out. This is the check that says it cannot happen here.
fake = FakeMeesho()
got = a_fetch(fake)("fk_orders", DAY)
check("asking for a two-phase report is NOT a failure", answered(lambda: got.state == tool.STILL_WAITING))
check("it says the platform is building it", answered(lambda: "Asked for it" in got.say))
check("and roughly how long", answered(lambda: "30 minutes" in got.say))
check("and that a later run will collect rather than ask again",
      answered(lambda: "collect it rather than asking again" in got.say))
# **WHAT IT WAS ASKED UNDER IS CARRIED BACK**, or the next run has nothing to
# collect it by and would ask a second time.
check("and it carries the day it was asked under", answered(lambda: got.their_id == "2026-08-26"))
check("it pressed Submit", answered(lambda: "Submit" in fake.clicked))
check("and it set the TWO-day range Flipkart insists on",
      answered(lambda: fake.ranges == [(date(2026, 8, 25), DAY)]))
# **AND IT TOLD THE DOOR WHICH CALENDAR IT IS STANDING IN FRONT OF.** Flipkart's
# Reports Centre switches a day off two different ways -- one leaves the day
# looking ordinary and gives it `pointer-events: none`, the other leaves
# pointer-events alone entirely and says so only in the cursor. The second is
# caught by nothing unless the door is told to read the cursor, and it is told
# only here because an unstyled cell on any other calendar has no pointer cursor
# either.
check("and it told the door that this calendar switches a day off in the cursor",
      answered(lambda: fake.cursor_told_for == [True]))

# The next run collects, and must NOT press Submit again.
fake = FakeMeesho()
got = a_fetch(fake)("fk_orders", DAY, )
again = a_fetch(fake2 := FakeMeesho())("fk_orders", DAY, asked_already="2026-08-26")
check("the next run collects the finished report", answered(lambda: again.state == tool.LANDED))
check("and NEVER presses Submit again", answered(lambda: "Submit" not in fake2.clicked))
check("and it opened the requested tab instead", answered(lambda: "Requested" in fake2.clicked))

# A one-shot report ignores it and simply fetches -- the safer way round.
fake = FakeMeesho()
got = a_fetch(fake)("me_catalog", DAY, asked_already="anything")
check("a one-shot report handed a stale in-flight id just fetches", answered(lambda: got.state == tool.LANDED))

# --------------------------- a door closing, with the day it started

fake = FakeMeesho(built_in_page=True)
got = a_fetch(fake)("fk_orders", DAY, asked_already="2026-08-26")
check("a Flipkart report built inside the page is a failure", answered(lambda: got.state == tool.FAILED))
# **SAID WITH THE DAY IT STARTED**, so it reads as a known door closing rather
# than as tonight's news.
check("and it says how long this has been happening", answered(lambda: "since 2026-08-22" in got.say))
# **AND THE PAGE IS STILL KEPT.** Naming it as a known door closing must not cost
# the evidence -- that is what the whole capture rule exists for.
check("and the page is still kept alongside it", answered(lambda: got.page_was != ""))
# A report it has NOT been happening to says nothing extra.
fake = FakeMeesho(built_in_page=True)
got = a_fetch(fake)("me_catalog", DAY)
check("while a report it has not happened to says nothing about a date", answered(lambda: "since" not in got.say))

# ------------------------------------- Flipkart needs no panel name

fk = a_fetch(FakeMeesho(), "")
got = fk("fk_claims", DAY)
check("a Flipkart report needs no panel name at all", answered(lambda: got.state == tool.LANDED))
# **WHILE MEESHO STILL DOES.** A requirement that applies to one platform must not
# be dropped for the other.
check("while a Meesho one still refuses without it", answered(lambda: fk("me_orders", DAY).state == tool.FAILED))

# ----------------------------- how long to wait actually reaches the browser

# **THE NUMBER ON EVERY STEP USED TO GO NOWHERE.** Each step says how patient to
# be -- 300 seconds while Meesho builds an orders export, 45 while a page draws
# -- and none of it was ever handed over, so every wait asked once and gave up.
# A page half a second from being drawn read as a platform that had renamed its
# buttons, and a file five minutes from being built read as an empty one.
fake = FakeMeesho()
got = a_fetch(fake)("me_orders", DAY)
check("the orders report still lands", answered(lambda: got.state == tool.LANDED))
told = dict(fake.patience_told)
check("going somewhere is told how long to wait", answered(lambda: told.get("go") is not None))
check("looking for something is told how long to wait", answered(lambda: told.get("find") is not None))
check("setting the dates is told how long to wait", answered(lambda: told.get("pick_range") is not None))
check("and taking the file is told how long to wait", answered(lambda: told.get("take_file") is not None))

# **AND IT IS EACH STEP'S OWN NUMBER, not one number for the whole recipe.**
# "Wait five minutes for Meesho to build the file" and "wait twenty seconds for a
# date box" are not the same instruction, and a single shared number would make
# the long waits short or the short waits pointless.
STEPS = book.steps_for("me_orders", PANEL)
WHICH_CALL = {
    pages.GO: "go",
    pages.CLICK: "find",
    pages.WAIT_FOR: "find",
    pages.PICK_RANGE: "pick_range",
    pages.TAKE_FILE: "take_file",
    # **THE ONE STEP THAT LOOKS AT NOTHING.** Meesho builds an orders export
    # where the page cannot see it, so this passes time rather than watching.
    pages.WAIT: "wait",
}
wanted = [(WHICH_CALL[step.do], step.patience) for step in STEPS]
# The last step asks twice -- once to find the download control, once for the
# file itself -- and both carry that step's own number.
wanted = wanted[:-1] + [("find", STEPS[-1].patience), ("take_file", STEPS[-1].patience)]
check("every call was told exactly what its own step says",
      answered(lambda: fake.patience_told == wanted))
check("and those are not all the same number, so one shared value cannot pass this",
      answered(lambda: len({one for _, one in wanted}) > 1))
# **THIS USED TO ASK FOR FIVE MINUTES OF PATIENCE ON THE LAST STEP, and it is
# rewritten with the change rather than deleted for going red.** Those five
# minutes were spent looking at an open download menu -- and Meesho draws the
# list of finished exports as that menu OPENS, so it never changed while it was
# being watched. The waiting that actually matters is the thirty-five seconds
# BEFORE the page is loaded again, because the list is built as it loads.
check("the wait between asking for the export and loading the page again reaches the browser",
      answered(lambda: ("wait", 35) in fake.patience_told))
check("and it comes after the export was asked for and before the page was loaded again",
      answered(lambda: "clicked Export data" in fake.order
               and fake.order.index("clicked Export data")
               < fake.order.index("waited 35") < fake.order.index("went", 1)))

# **CLICKING IS NOT TOLD, AND THAT IS DELIBERATE.** What it clicks was found a
# moment ago; waiting again would be waiting for something already in front of
# it.
check("clicking is not given a wait at all",
      answered(lambda: all(call != "click" for call, _ in fake.patience_told)))

# ------------------------- the menu is shut and opened again between looks

# **MEESHO DRAWS ITS LIST OF FINISHED EXPORTS AS THE DOWNLOAD MENU OPENS**, so an
# open menu shows what was ready at that moment and never changes. This step used
# to wait 300 seconds on one and call that patience; the reference shuts it by
# clicking where nothing is, leaves it shut for thirty seconds, looks the opener
# up again and presses it once -- six times (`content/meesho.js:860-878`), every
# night, for months.
fake = FakeMeesho(appears_after_reopens=2)
got = a_fetch(fake)("me_orders", DAY)
check("a file not in the list yet is still fetched, by shutting the menu and opening it again",
      answered(lambda: got.state == tool.LANDED))
# **THE ORDER IS THE CHECK, AND IT IS THE REFERENCE'S ORDER.** Shut, wait while
# it is shut, open. A round that waited on the OPEN menu would read
# "clicked Download Orders Data -> waited 30 -> clicked away" and match none of
# this; so would a round that pressed the opener twice and never shut anything.
check("and each round was: clicked away, left shut for thirty seconds, opened again",
      answered(lambda: " -> ".join(fake.order).count(
          "clicked away -> waited 30 -> clicked Download Orders Data") == 2))
# **AND THE STAND-IN COUNTED THE SHUTTING, NOT THE CLICKING.** Its list only
# reappears once the menu has genuinely been shut and opened again, which is why
# a loop that pressed the opener twice cannot reach this line at all.
check("and the menu really was shut and reopened, twice, not merely pressed at",
      answered(lambda: (fake.clicked_away, fake.reopened) == (2, 2)))

# **AND IT GIVES UP.** A menu reopened until morning holds the night on one
# report and every report behind it goes unfetched.
fake = FakeMeesho(appears_after_reopens=99)
got = a_fetch(fake)("me_orders", DAY)
check("a file that never appears is a failure, not a menu reopened all night",
      answered(lambda: got.state == tool.FAILED))
check("having been tried the six times the reference tries it, and no more",
      answered(lambda: fake.reopened == 6))
# **AND THE FAILURE SAYS WHAT IT WAS DOING.** A walk that ran out of rounds must
# not report a bare "nothing matched": the whole reason a step carries a `why` is
# that "button not found" with nothing beside it cost this project a month.
check("and the failure carries the step's own reason with it",
      answered(lambda: "taking the finished file" in got.say))

# **THE OPENER IS LOOKED FOR BEFORE IT IS PRESSED, AND IF IT HAS GONE THIS STOPS.**
# The reference does exactly this (`if (!dlDropdown2) ... break`). Without it the
# click throws straight past every failure this door writes, and the seller is
# told a control could not be found with no word of what was being attempted.
fake = FakeMeesho(appears_after_reopens=99, opener_goes_when_shut=True)
got = a_fetch(fake)("me_orders", DAY)
check("an opener that has gone ends the walk rather than throwing out of it",
      answered(lambda: got.state == tool.FAILED))
check("and it stops at the first round rather than shutting a menu that is not there five more times",
      answered(lambda: fake.clicked_away == 1))
check("and the failure still carries the step's own reason",
      answered(lambda: "taking the finished file" in got.say))

# ------------- and the numbers come off the recipe, not out of this door
#
# **THE ANTIDOTE THIS FILE ALREADY WRITES DOWN, APPLIED TO THE NEW NUMBERS.**
# Every check above uses the recipe's own 6, 30 and 35 -- and so does the door,
# so a door that ignored the recipe and used its own 6 and 30 would pass every
# one of them. Here the recipe is given numbers no line of the door would ever
# choose, and the door is asked to prove it read them.
def _with_the_last_step(**changed):
    """His orders recipe, with its take-file step altered, put back afterwards."""
    was = book.RECIPES["me_orders"]
    steps = list(was.to_take)
    steps[-1] = dataclasses.replace(steps[-1], **changed)
    book.RECIPES["me_orders"] = dataclasses.replace(was, to_take=tuple(steps))
    return was


ODD = pages.LookAgain(by=pages.Find(pages.BY_PRESSABLE_TEXT, "Download Orders Data"),
                      times=2, after=3)
_was = _with_the_last_step(patience=7, look_again=ODD)
try:
    fake = FakeMeesho(appears_after_reopens=99)
    got = a_fetch(fake)("me_orders", DAY)
    check("how long to leave it shut is the recipe's, not a number inside the door",
          answered(lambda: fake.waited == [35, 3, 3]))
    check("and how many times to try is the recipe's too",
          answered(lambda: (fake.clicked_away, fake.reopened) == (2, 2)))
    check("and the patience on that step is the recipe's, on both of its lookups",
          answered(lambda: [one for call, one in fake.patience_told if call == "find"][-3:]
                   == [7, 7, 7]))
finally:
    book.RECIPES["me_orders"] = _was
check("and the book was put back exactly as it was found",
      answered(lambda: book.recipe("me_orders").to_take[-1].look_again.times == 6))

# ---------------------------------- and nothing here ended by falling over

# **THE FLOOR UNDER EVERYTHING ABOVE, and there is ONE of it.** Answering with
# nothing when the door throws stops the run dying, but on its own it is not
# enough: a check written as "this word is NOT in what it said" passes against an
# empty answer, and would go green for the worst possible reason. This is the one
# check that cannot be fooled that way -- it goes red the moment anything above
# ended by throwing rather than by answering, and it names what threw.

# **THERE WERE TWO OF THESE, six lines apart, saying the same sentence** -- two
# records of one fact, and the tally counted the same assurance twice.

# **AND NOTHING ABOVE ENDED BY THROWING RATHER THAN BY ANSWERING.** Answering
# with nothing keeps the run alive; this is what stops a check phrased as "this
# word is NOT in what it said" going green because there was nothing to look in.
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)


EXPECTED = 108
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
