"""Checks for how a page is driven.

**THIS FILE CHECKS THE LANGUAGE, NOT THE RECIPES.** What a step is, what a failure
is called, what counts as something covering the page. The recipes themselves are
in `recipes.py` and are checked by `recipes_checks.py`.

**EVERY CASE HERE COMES FROM A REAL FAILURE**, most of them read out of the
reference's own live log and one of them out of his own Chrome on 2026-08-27:

  - the promotion covering the Meesho panel, whose close control is an `<img>`
    with no class, no label and no text, and which **Escape does not close**;
  - the chart legend reading "Payments to Date" that was clicked instead of the
    menu item of the same name -- nine days of payments lost;
  - the Flipkart files now built inside the page, which cannot be fetched twice.

Run: python autosync/browser_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import browser as tool  # noqa: E402

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


# ------------------------------------------------------------ bad steps

check("a step that is not a step is refused", answered(lambda: tool.why_step_is_refused("go somewhere") is not None))
check("a kind nobody knows is refused",
      answered(lambda: tool.why_step_is_refused(tool.Step("teleport", why="x")) is not None))
check("going nowhere is refused", answered(lambda: tool.why_step_is_refused(tool.Step(tool.GO, why="x")) is not None))
check("clicking nothing in particular is refused",
      answered(lambda: tool.why_step_is_refused(tool.Step(tool.CLICK, why="x")) is not None))
check("waiting for nothing in particular is refused",
      answered(lambda: tool.why_step_is_refused(tool.Step(tool.WAIT_FOR, why="x")) is not None))
check("a way of finding nobody knows is refused",
      answered(lambda: tool.why_step_is_refused(tool.Step(tool.CLICK, find=tool.Find("by vibes", "x"), why="y")) is not None))
check("finding something with no words to look for is refused",
      answered(lambda: tool.why_step_is_refused(tool.Step(tool.CLICK, find=tool.Find(tool.BY_TEXT, ""), why="y")) is not None))
check("a step that waits no time at all is refused",
      answered(lambda: tool.why_step_is_refused(tool.Step(tool.GO, address="x", patience=0, why="y")) is not None))
# **A RANGE IS NOT ALWAYS ONE DAY.** Flipkart's Reports Centre needs the start
# strictly before the end, so its smallest range is two days -- and a single-day
# one is refused by a Submit that does nothing at all, silently.
check("a range of no days at all is refused",
      answered(lambda: tool.why_step_is_refused(tool.Step(tool.PICK_RANGE, range_days=0, why="y")) is not None))
check("a range of two days is fine",
      answered(lambda: tool.why_step_is_refused(tool.Step(tool.PICK_RANGE, range_days=2, why="y")) is None))
check("and one day is what a step means unless it says otherwise",
      answered(lambda: tool.Step(tool.GO, address="x", why="y").range_days == 1))
# **ONLY A RANGE STEP MAY SAY HOW MANY DAYS.** A click that carried a day count
# would be saying something nothing reads, which is how a setting silently stops
# working.
check("a step that is not a range may not say how many days it covers",
      answered(lambda: tool.why_step_is_refused(tool.Step(tool.GO, address="x", range_days=2, why="y")) is not None))
check("while a range step may", answered(lambda: tool.why_step_is_refused(tool.Step(tool.PICK_RANGE, range_days=2, why="y")) is None))
# **AND HOW A CALENDAR SWITCHES A DAY OFF IS THE SAME KIND OF THING.** Flipkart's
# Reports Centre disables a day two different ways and one of them shows only in
# the cursor -- that portal's own habit, not a rule of browsers, so it is asked
# for on the one step that stands in front of a calendar. Anywhere else it would
# read as a rule about the whole page.
check("a calendar's own way of switching a day off is not assumed",
      answered(lambda: tool.Step(tool.PICK_RANGE, why="y").switched_off_days_change_the_cursor is False))
check("a range step may say that its calendar says it in the cursor",
      answered(lambda: tool.why_step_is_refused(
          tool.Step(tool.PICK_RANGE, switched_off_days_change_the_cursor=True, why="y")) is None))
check("and no other step may say it",
      answered(lambda: tool.why_step_is_refused(
          tool.Step(tool.CLICK, find=tool.Find(tool.BY_TEXT, "x"),
                    switched_off_days_change_the_cursor=True, why="y")) is not None))
# ------------------------- a step that only waits, and a menu reopened

# **WAITING FOR SOMETHING AND JUST WAITING ARE NOT THE SAME STEP.** Meesho builds
# an orders export on its own servers and the page it was asked from shows
# nothing at all while it happens, so there is nothing a `wait-for` could watch.
check("waiting is something this door knows how to do",
      answered(lambda: tool.WAIT in tool.STEP_KINDS))
check("a step that only waits needs nothing to look for",
      answered(lambda: tool.why_step_is_refused(tool.Step(tool.WAIT, patience=35, why="y")) is None))
# **REFUSED RATHER THAN IGNORED.** Written with something to look for, a wait
# would pass its time and never look at it -- and the recipe would read as though
# it had waited FOR that thing.
waiting_at = tool.why_step_is_refused(
    tool.Step(tool.WAIT, find=tool.Find(tool.BY_TEXT, "Download"), patience=35, why="y"))
check("but a wait that names something to look for is refused",
      answered(lambda: waiting_at is not None))
check("and the reason sends whoever wrote it to the step that does look",
      answered(lambda: "wait-for" in waiting_at))

# **SHUTTING A MENU AND OPENING IT AGAIN.** Meesho draws its list of finished
# exports as the download menu opens, so an open menu never changes -- the only
# way to see a newer list is to shut it, leave it shut, and open it again.
def _taking(**how):
    return tool.Step(tool.TAKE_FILE, find=tool.Find(tool.BY_TEXT, "Download"),
                     patience=30, why="y", look_again=tool.LookAgain(**how))


_menu = tool.Find(tool.BY_TEXT, "Download Orders Data")
check("a take-file step may say what to shut and open again between looks",
      answered(lambda: tool.why_step_is_refused(_taking(by=_menu, times=6, after=30)) is None))
# **ONLY THE STEP THAT TAKES THE FILE.** A click or a wait-for that reopened a
# menu would be a second, quieter way of doing what the recipe already says in
# steps of its own.
check("but nothing else may",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find(tool.BY_TEXT, "x"), why="y",
          look_again=tool.LookAgain(by=_menu, times=6, after=30))) is not None))
check("it has to say what to shut and open again",
      answered(lambda: tool.why_step_is_refused(
          _taking(by=tool.Find(tool.BY_TEXT, ""), times=6, after=30)) is not None))
check("and how to find it",
      answered(lambda: tool.why_step_is_refused(
          _taking(by=tool.Find("by vibes", "x"), times=6, after=30)) is not None))
check("looking again no times at all is refused",
      answered(lambda: tool.why_step_is_refused(_taking(by=_menu, times=0, after=30)) is not None))
# **NOUGHT SECONDS SHUT IS A MENU THAT WAS NEVER SHUT.** It would be opened again
# on the same list it was closed on, every time, and read as having tried.
check("and so is shutting it for no time at all",
      answered(lambda: tool.why_step_is_refused(_taking(by=_menu, times=6, after=0)) is not None))

# **A STEP HAS TO SAY WHAT IT IS FOR.** Without it a failure can only say what
# could not be found -- which is how a month of "button not found" told nobody the
# button was underneath a dialog.
no_why = tool.why_step_is_refused(tool.Step(tool.GO, address="x"))
check("a step that does not say what it is for is refused", answered(lambda: no_why is not None))
check("and the reason says why that matters", answered(lambda: "what was being attempted" in no_why))

# ----------------------------------- EXACT BY DEFAULT: the nine-day outage

# **Meesho added a chart whose legend read "Payments to Date", exactly like the
# menu item. The legend sits earlier in the page, so the code clicked the chart.**
check("a way of finding something is exact unless it says otherwise",
      answered(lambda: tool.Find(tool.BY_TEXT, "Payments to Date").exact is True))
check("and a loose match has to be asked for deliberately",
      answered(lambda: tool.Find(tool.BY_TEXT, "x", exact=False).exact is False))
# A thing can be given a readable name for when it is missing.
check("something can be given a name a person reads",
      answered(lambda: tool.Find(tool.BY_ROLE_AND_TEXT, "Download Orders Data", called="the download menu").name() == "the download menu"))
check("and falls back to its own words when it has none",
      answered(lambda: tool.Find(tool.BY_TEXT, "Export data").name() == "Export data"))

# ------------------------------- SIX FAILURES, NOT ONE -- and each says itself

check("every kind of failure has its own meaning written down",
      answered(lambda: set(tool.WHAT_IT_MEANS) == {tool.FOUND_NOTHING, tool.FOUND_SEVERAL, tool.COVERED_UP,
                                  tool.NEEDS_SIGNING_IN, tool.BUILT_IN_THE_PAGE,
                                  tool.DAY_NOT_AVAILABLE, tool.TOOK_TOO_LONG}))
# **THE REFERENCE HAD ONE MESSAGE FOR ALL SIX**, and a month of diagnosis went at
# the wrong thing because "it is underneath a dialog" and "it has been renamed"
# arrived wearing the same words.
check("and no two of them read the same", answered(lambda: len(set(tool.WHAT_IT_MEANS.values())) == 7))

# **A DAY THE PORTAL DRAWS AND THEN REFUSES.** Flipkart does this for a period it
# has not finished preparing, by two different mechanisms found weeks apart -- and
# a date picked anyway reads back as "Invalid date", after which Submit does
# nothing at all, silently.
day = tool.WentWrong(tool.DAY_NOT_AVAILABLE, "26 August", "setting the day to fetch")
check("a day drawn and then refused is its own failure", answered(lambda: "refuses it" in day.say()))
check("and says waiting is the answer", answered(lambda: "Waiting is the only answer" in day.say()))
check("and it is worth trying again", answered(lambda: day.worth_retrying is True))

# **SIGNED OUT IS TOLD APART FROM NOT-YET-DRAWN, and they are not the same.**
# Across 71 real occurrences, 54 were a page mid-draw and harmless.
out = tool.WHAT_IT_MEANS[tool.NEEDS_SIGNING_IN]
check("being signed out names the public site Flipkart serves instead", answered(lambda: "Sell Online" in out))
check("and says a page mid-draw is a different thing", answered(lambda: "not finished drawing" in out))

nothing = tool.WentWrong(tool.FOUND_NOTHING, "the download menu", "opening the download menu", page_was="Welcome back")
check("a thing that is not there says what was being attempted", answered(lambda: "opening the download menu" in nothing.say()))
check("and what it was looking for", answered(lambda: "the download menu" in nothing.say()))
check("and that it may have been renamed", answered(lambda: "renamed" in nothing.say()))
check("and it is worth trying again tomorrow", answered(lambda: nothing.worth_retrying is True))

several = tool.WentWrong(tool.FOUND_SEVERAL, "Payments to Date", "choosing the payments export", matches=2)
check("several matches says how many", answered(lambda: "2 things match" in several.say()))
check("and that nothing was clicked", answered(lambda: "Nothing was clicked" in several.say()))
check("and names the nine days it cost", answered(lambda: "nine days" in several.say()))

covered = tool.WentWrong(tool.COVERED_UP, "the download menu", "opening the download menu")
check("something covering the page says the button is there", answered(lambda: "The button is there" in covered.say()))
check("and that it is underneath something", answered(lambda: "underneath something" in covered.say()))

# **A DOOR THAT HAS CLOSED IS NOT RETRIED.**
blob = tool.WentWrong(tool.BUILT_IN_THE_PAGE, "the file itself", "taking the finished file")
check("a file built inside the page is not worth retrying", answered(lambda: blob.worth_retrying is False))
check("and it says it is a door closing rather than a fault", answered(lambda: "door closing" in blob.say()))
check("while everything else IS worth retrying",
      answered(lambda: all(tool.WentWrong(k, "x", "y").worth_retrying for k in tool.WHAT_IT_MEANS if k != tool.BUILT_IN_THE_PAGE)))

# ------------------------------ THE PAGE IS CAPTURED, AUTOMATICALLY

# **Two reports went undiagnosed for over a month** because the evidence had to be
# added afterwards and then somebody had to wait for the failure to happen again.
messy = "Welcome   back,\n\n  Rumee\t\tManage and grow" + ("x" * 900)
kept = tool.capture(messy)
check("the page is kept when something cannot be found", answered(lambda: kept != ""))
check("tidied up so a log stays readable", answered(lambda: "\n" not in kept and "  " not in kept))
check("and cut short rather than filling the log", answered(lambda: len(kept) == tool.PAGE_SNIPPET))
check("nothing at all captures nothing, rather than falling over", answered(lambda: tool.capture(None) == ""))
check("and the failure carries it", answered(lambda: tool.WentWrong(tool.FOUND_NOTHING, "x", "y", page_was=kept).page_was == kept))

# ------------------- SOMETHING COVERING THE PAGE -- read off his own Chrome

# **THE REAL ONE.** `role="dialog"` over a full-screen backdrop; close control an
# `<img>` with no class, no label, no text, and Escape does not work. **The
# backdrop is what a click aimed at the page hits, and it carries no words -- the
# words are on the panel sitting on it.**
REAL_MODAL = [
    {"width": 1280, "height": 800, "text": "", "blocks": True},
    {"width": 414, "height": 330, "text": "Abhi Update Karein ! Participate Now", "blocks": False},
]
found = tool.is_covered(REAL_MODAL)
check("a promotion covering the panel is found", answered(lambda: found is not None))
check("and named as its own failure, not as a missing button", answered(lambda: found.kind == tool.COVERED_UP))
check("and the words come from the panel, since the backdrop has none",
      answered(lambda: "Abhi Update" in found.page_was))
check("nothing in the way is nothing to report", answered(lambda: tool.is_covered([]) is None))
check("and neither is no list at all", answered(lambda: tool.is_covered(None) is None))
# Ordinary furniture is not an overlay. A small notice does not swallow a click.
check("a small notice is not treated as covering the page",
      answered(lambda: tool.is_covered([{"width": 250, "height": 80, "text": "Saved", "blocks": False}]) is None))
check("nor a wide but shallow banner",
      answered(lambda: tool.is_covered([{"width": 1200, "height": 60, "text": "Upcoming Policy Update", "blocks": False}]) is None))

# **THE NEAR-MISS THAT CHANGED THIS RULE, both sides measured on his own panel on
# 2026-08-28.** The download menu the recipe opens ON PURPOSE calls itself a
# dialog and is 232 x 196. The old rule refused at 300 x 200 -- **four pixels in
# one direction from stopping every Meesho report because of a menu the door had
# just opened itself.**
OWN_MENU = [{"width": 232, "height": 196, "text": "GST Report Payments to Date", "blocks": False}]
check("the menu the door opens itself is not something covering the page",
      answered(lambda: tool.is_covered(OWN_MENU) is None))
check("and neither is a big dialog that is not laid over anything",
      answered(lambda: tool.is_covered([{"width": 600, "height": 400, "text": "", "blocks": False}]) is None))
# **WHAT IT IS JUDGED ON NOW: whether it would swallow a click.**
check("while something laid over the whole page is, whatever size it is called",
      answered(lambda: tool.is_covered([{"width": 0, "height": 0, "text": "x", "blocks": True}]) is not None))
check("and a missing size is not read as a huge one",
      answered(lambda: tool.is_covered([{"text": "no size given"}]) is None))
# A blocking thing with no words anywhere still reports, rather than falling over.
check("something in the way that says nothing at all is still reported",
      answered(lambda: tool.is_covered([{"blocks": True}]) is not None))
check("with no words rather than the word None",
      answered(lambda: tool.is_covered([{"blocks": True}]).page_was == ""))

# ------------------------------------- the third way of finding something

# **READ OFF HIS OWN MEESHO PANEL, 2026-08-27, signed in and fully drawn: there
# is not one control on it.** No button, no link, no role attribute anywhere --
# the sidebar's "Orders" is an `h5` and "Manage Orders" is a `p`, and the only
# thing marking either as pressable is the mouse cursor.
check("there is a way of finding something by the words on a pressable thing",
      answered(lambda: tool.BY_PRESSABLE_TEXT in tool.WAYS_OF_FINDING))
check("and a step may use it",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find(tool.BY_PRESSABLE_TEXT, "Orders"), why="x")) is None))
# **THE OTHER THREE ARE UNCHANGED.** Flipkart's pages are full of real controls
# -- thirty-two painted ones and eight kinds of role on its dashboard -- so the
# role way is right there and stays.
# **AND THE FIFTH IS FLIPKART'S DATE BOX.** The words "Select Date Range" are a
# plain label with nothing pressable about them, and the box beside them carries
# its own value rather than those words -- so no way above can reach it, and a
# step that pressed the words could never have worked.
check("there is a way of finding the box a label names",
      answered(lambda: tool.BY_THE_CONTROL_BESIDE in tool.WAYS_OF_FINDING))
check("and a step may use it",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find(tool.BY_THE_CONTROL_BESIDE, "Select Date Range"),
          why="x")) is None))
check("and all five ways are known", answered(lambda: len(tool.WAYS_OF_FINDING) == 5))
check("a way nobody has heard of is still refused",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find("xpath", "//div"), why="x")) is not None))
check("and the refusal names what was asked for",
      answered(lambda: "xpath" in tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find("xpath", "//div"), why="x"))))


# --------------------- whose wording of a day a row is named by (A52)

# **A ROW NAMED BY THE DAY IN THE PLATFORM'S OWN WORDING IS NAMED BY ONE OF TWO
# DIFFERENT THINGS.** Meesho writes `1 Sep 2026` and Flipkart's Reports Centre
# writes `05 Jun 2026`, so a lookup that does not say which of them it means can
# only be filled in by guessing -- and a guess is wrong on one of the two portals
# for the nine days of every month whose number is under ten. Wrong in the silent
# direction: no row matches, and the night reports a renamed button.
#
# **THIS FILE STILL KNOWS NOTHING ABOUT EITHER PORTAL.** All it insists on is
# that whose wording is SAID. Which wordings exist, and which portal each belongs
# to, is `recipes.py`'s to answer.
check("a row named by the day in words, saying whose wording and which day, is allowed",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find(tool.BY_TEXT, "Download", near="{day_in_words}",
                                     day_in_words_is="meesho",
                                     day_in_words_of=tool.THE_DAY_IT_WAS_MADE),
          why="x")) is None))
check("and the same row with nobody's wording said is refused",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find(tool.BY_TEXT, "Download", near="{day_in_words}",
                                     day_in_words_of=tool.THE_DAY_IT_WAS_MADE),
          why="x")) is not None))
check("and the refusal says why -- no two platforms write a day the same way",
      answered(lambda: "no two platforms write a day the same way" in tool.why_step_is_refused(
          tool.Step(tool.CLICK,
                    find=tool.Find(tool.BY_TEXT, "Download", near="{day_in_words}",
                                   day_in_words_of=tool.THE_DAY_IT_WAS_MADE),
                    why="x"))))

# ------------------- WHICH day names the row, which is the other half (A53)
#
# **WHOSE WORDING AND WHICH DAY ARE TWO QUESTIONS AND ONLY ONE WAS ASKED.** A
# lookup that says Meesho's wording and is then filled with the day being fetched
# asks for `24 Aug 2026` on a row reading `25 Aug 2026, 04:49 PM` -- right
# wording, wrong day, nothing found, in silence. Meesho's panel names a row by
# the day the export was MADE; Flipkart's Reports Centre by the end of the range,
# which is the day the data is about.
#
# **THIS FILE STILL KNOWS NOTHING ABOUT EITHER PORTAL.** All it insists on is
# that WHICH day is said, and that it is one of the two.
check("a row named by the day in words with nobody saying WHICH day is refused",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find(tool.BY_TEXT, "Download", near="{day_in_words}",
                                     day_in_words_is="meesho"),
          why="x")) is not None))
check("and the refusal offers both answers, so the fix is obvious",
      answered(lambda: ("the day the data is about" in tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find(tool.BY_TEXT, "Download", near="{day_in_words}",
                                     day_in_words_is="meesho"), why="x"))
          and "the day the export was made" in tool.why_step_is_refused(tool.Step(
              tool.CLICK, find=tool.Find(tool.BY_TEXT, "Download", near="{day_in_words}",
                                         day_in_words_is="meesho"), why="x")))))
check("the day the data is about is one of the two",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find(tool.BY_TEXT, "Download", near="{day_in_words}",
                                     day_in_words_is="flipkart",
                                     day_in_words_of=tool.THE_DAY_IT_IS_ABOUT),
          why="x")) is None))
check("and a day nobody has heard of is refused by name",
      answered(lambda: "yesterday" in tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find(tool.BY_TEXT, "Download", near="{day_in_words}",
                                     day_in_words_is="meesho", day_in_words_of="yesterday"),
          why="x"))))
check("and there are exactly two days a row can be named by",
      answered(lambda: len(tool.WHICH_DAY_A_ROW_IS_NAMED_BY) == 2))
# **SAID WHERE THERE IS NO DAY IN WORDS TO WRITE, it describes a placeholder the
# lookup does not carry** -- the same shape as the rule about whose wording.
check("saying which day where no row is named in words is refused",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find(tool.BY_TEXT, "Download", near="{day}",
                                     day_in_words_of=tool.THE_DAY_IT_WAS_MADE),
          why="x")) is not None))

# ------------------------ a row is never named by the seller's panel name (A53)
#
# **IT PASSED EVERY RULE ON BOTH SIDES AND THE TWO SIDES DID DIFFERENT THINGS
# WITH IT.** The Python filled `{panel}` into the address only; the JavaScript
# filled it into `near` as well. So one half would have narrowed to a real row
# and the other to a row carrying the literal characters `{panel}`.
check("a row named by the seller's own panel name is refused",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find(tool.BY_TEXT, "Download", near="{panel} {day}"),
          why="x")) is not None))
check("and the refusal says what a row IS named by",
      answered(lambda: "named by the day" in tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find(tool.BY_TEXT, "Download", near="{panel} {day}"),
          why="x"))))
check("while an address may still carry it, which is where it belongs",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.GO, address="https://x/{panel}/orders", why="x")) is None))

# ------------------------- a control that toggles, pressed again (A53)
#
# **THE REFERENCE PRESSES BOTH OF FLIPKART'S DATE CONTROLS AGAIN WHILE IT
# WAITS**, because both toggle: the date box on every third look for the Custom
# chip, and the chip once while waiting for the calendar. Both were dropped when
# those steps were carried across, with no reason given -- and dropped, the only
# symptom is a step that waits its whole patience out in silence.
A_TOGGLE = tool.PressAgain(by=tool.Find(tool.BY_PRESSABLE_TEXT, "Custom"), after=3, times=2)
check("a step waiting for something may press a control that toggles again",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find(tool.BY_PRESSABLE_TEXT, "Custom"),
          press_again=A_TOGGLE, why="x")) is None))
check("and so may a step picking a range, which is what waits for the calendar",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.PICK_RANGE, press_again=A_TOGGLE, why="x")) is None))
check("but a step that only goes somewhere has nothing to press again for",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.GO, address="https://x", press_again=A_TOGGLE, why="x")) is not None))
check("and neither has the step that takes the file, which has its own way",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.TAKE_FILE, press_again=A_TOGGLE, why="x")) is not None))
check("pressing again has to say what to press",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.PICK_RANGE, why="x",
          press_again=tool.PressAgain(by=tool.Find(tool.BY_PRESSABLE_TEXT, ""), after=3,
                                      times=2))) is not None))
check("and by a way of finding something that is known",
      answered(lambda: "xpath" in tool.why_step_is_refused(tool.Step(
          tool.PICK_RANGE, why="x",
          press_again=tool.PressAgain(by=tool.Find("xpath", "//div"), after=3, times=2)))))
check("pressing again no times at all is refused",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.PICK_RANGE, why="x",
          press_again=tool.PressAgain(by=tool.Find(tool.BY_PRESSABLE_TEXT, "Custom"),
                                      after=3, times=0))) is not None))
# **NOUGHT SECONDS IS NOT WAITING, IT IS DOUBLE-CLICKING** -- the second press
# lands on a control the first one has just opened, and shuts it.
check("and pressing again with no time in between is refused, because it would shut it",
      answered(lambda: "shuts it" in tool.why_step_is_refused(tool.Step(
          tool.PICK_RANGE, why="x",
          press_again=tool.PressAgain(by=tool.Find(tool.BY_PRESSABLE_TEXT, "Custom"),
                                      after=0, times=2)))))
# **A ROW NAMED BY THE PLAIN DAY NEEDS NOBODY'S WORDING**, and saying one there
# describes a placeholder the lookup does not carry -- the same shape as a step
# that is not a range saying how its calendar switches a day off.
check("a row named by the plain day needs nobody's wording",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find(tool.BY_TEXT, "Download", near="{day}"),
          why="x")) is None))
check("and one that names a wording with no day in words to write is refused",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find(tool.BY_TEXT, "Download", near="{day}",
                                     day_in_words_is="meesho"),
          why="x")) is not None))
check("and so is one that names a wording with no row named at all",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.CLICK, find=tool.Find(tool.BY_TEXT, "Download", day_in_words_is="meesho"),
          why="x")) is not None))
# **AN ADDRESS CANNOT SAY WHOSE WORDING IT WANTS**, because whose wording is said
# on a lookup and an address has none. Filled in anyway it could only be filled
# from a guess.
check("an address may name the day plainly",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.GO, address="https://example.invalid/{day}", why="x")) is None))
check("but naming it in a platform's own wording is refused",
      answered(lambda: tool.why_step_is_refused(tool.Step(
          tool.GO, address="https://example.invalid/{day_in_words}", why="x")) is not None))
check("and the refusal says an address names the day plainly",
      answered(lambda: "names the day plainly" in tool.why_step_is_refused(tool.Step(
          tool.GO, address="https://example.invalid/{day_in_words}", why="x"))))


# ------------------------------------------------------------ the records

check("a step cannot be edited after it is written",
      answered(lambda: refuses(lambda: setattr(tool.Step(tool.GO, address="a", why="b"), "address", "x"))))
check("nor a way of finding something",
      answered(lambda: refuses(lambda: setattr(tool.Find(tool.BY_TEXT, "x"), "exact", False))))
check("nor a failure once it has happened",
      answered(lambda: refuses(lambda: setattr(tool.WentWrong(tool.FOUND_NOTHING, "x", "y"), "kind", "z"))))


# **AND NOTHING ABOVE ENDED BY THROWING RATHER THAN BY ANSWERING.** Answering
# with nothing keeps the run alive; this is what stops a check phrased as "this
# word is NOT in what it said" going green because there was nothing to look in.
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)


EXPECTED = 106
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
