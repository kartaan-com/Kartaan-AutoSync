"""The browser door: how a page is driven, written as data rather than as code.

Phase 4. **Meesho first, because Meesho has no API and is not waiting for one** --
there is no published API and Akamai sits in front of the portal, so this door is
permanent rather than a staging post.

**WHY THE STEPS ARE DATA AND NOT CODE, which is the whole decision in this file.**
The reference drove Meesho and Flipkart from about 3,800 lines of JavaScript, and
every failure it had for three months was the same shape: a button moved, was
renamed, or was covered up. Nothing could check any of it without a real browser
and a real login, so a broken selector was found by a seller noticing missing data
days later. Written as data:

  - a moved button is **one entry to change**, not a code change;
  - **every rule below is checked without a browser** -- ambiguity, overlays,
    what a failure is called, what it captures;
  - and the thing that actually touches the page becomes small enough to trust.

**WHAT RUNS WHERE, said plainly.** These steps are decided here, in Python, where
they can be checked. **The thing that carries them out is the seller's own Chrome**
-- it has to be: driving Meesho from a server would need the seller's password,
which this project does not handle, and a server browser is exactly what Akamai
exists to stop. The extension executes steps and reports back. It holds no
knowledge of its own.

**THE FIVE RULES PAID FOR BY REAL FAILURES, all built in below:**

1. **A lookup that matches more than one thing REFUSES.** Meesho added a chart
   whose legend read "Payments to Date", exactly like the menu item; the legend
   came first in the page, so the code clicked the chart, and payments were dead
   for nine days -- with an error blaming a button two steps later that was never
   the problem. **Ambiguity is a failure, not a coin toss.**
2. **Every failed lookup captures the page as it was, automatically, first time.**
   Two reports went undiagnosed for over a month because the evidence had to be
   added afterwards and then somebody had to wait for it to fail again.
3. **"A dialog is covering the page" is its own named failure.** Seen live in his
   own Chrome on 2026-08-27: a full-screen Meesho promotion whose close control is
   an `<img>` with no class, no label, no text -- and **Escape does not close it**.
   Every one of `me_orders`, `me_catalog` and `me_returns` has been reporting this
   as "button not found" for a month, which sent a month of diagnosis at the wrong
   thing. **The button was there. It was underneath something.**
4. **Reach a section by its address, not by clicking the sidebar**, wherever the
   portal allows. That is what the overlay actually defeats -- a click aimed at the
   sidebar hits the dialog instead.
5. **A file the page builds inside itself cannot be fetched twice.** Say so and
   stop, rather than retrying for ever.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence, Tuple

# ------------------------------------------------------------- finding things

# How a thing on the page is described. **BY WHAT IT IS, not by where it sits.**
# A position breaks the first time anything moves; a role and a name survive a
# redesign far more often, and when they do not they fail loudly.
BY_TEXT = "text"            # its exact words
BY_ROLE_AND_TEXT = "role"   # a button/link/tab with these words
BY_TEST_ID = "test-id"      # what the page itself calls it, when it says
BY_PRESSABLE_TEXT = "pressable"  # these words, on something the page shows as pressable

# **THE FOURTH ONE EXISTS BECAUSE OF MEESHO, read off his own panel 2026-08-28.**
#
# **ITS SIDEBAR SAYS NOTHING ABOUT ITSELF.** "Orders" is an `h5` and "Manage
# Orders" a `<p>`, with no role, no tabindex and no test id between them -- **the
# only thing telling a person either can be pressed is that the cursor changes.**
# Asked for a control, that sidebar answers nothing at all.
#
# **AND `BY_TEXT` ALONE IS NOT THE ANSWER EITHER.** The payments page carries a
# chart legend reading "Payments to Date" exactly like the menu item, so matching
# on words finds two, refuses, and payments never fetch again -- safe, and
# useless. That is the nine-day outage in its other form.
#
# **IT IS A SUPERSET OF THE CONTROL WAY, NOT A REPLACEMENT.** A plain `<button>`
# has the ordinary arrow cursor unless somebody styled it, so asking only about
# the cursor would miss real buttons -- and the same Meesho panel that says
# nothing about its sidebar has twenty-three ordinary controls on its home page.
# Either signal counts, so this can never find less than asking for a control.
#
# **CORRECTED THE SAME DAY, and the correction is the point:** the first reading
# said the panel "has no controls at all". That came from the orders page, which
# had only half drawn -- the sidebar and nothing else. A claim about a whole
# platform taken from a page that had not finished drawing is exactly the mistake
# this door exists to stop being made about buttons.


WAYS_OF_FINDING = (BY_TEXT, BY_ROLE_AND_TEXT, BY_TEST_ID, BY_PRESSABLE_TEXT)


@dataclass(frozen=True)
class Find:
    """How to find one thing on a page.

    **`exact` DEFAULTS TO TRUE, and that is the nine-day-outage fix.** A loose
    match found "Payments to Date" on a chart legend before the menu item of the
    same name. Where a loose match is genuinely needed it has to be asked for.
    """

    how: str
    what: str
    exact: bool = True
    # What to call it when it is not there, in words a person reads.
    called: str = ""
    # **WHICH ROW IT IS ON, when the same thing appears on every row.**
    #
    # Read off his own returns page on 2026-08-28: Meesho keeps every export ever
    # made, each row reading `completed_delivered_last_2_week | 25 Aug 2026,
    # 04:49 PM | Download`. **Ten of them.** Looking for "Download" finds ten and
    # refuses -- which is right, and useless.
    #
    # The recipe already knows which day it is fetching, so it says so: this is
    # words that must appear ALONGSIDE the thing, on the same row. One of two
    # placeholders is filled in with that day:
    #
    #   `{day}`          the day itself, `2026-08-23`
    #   `{day_in_words}` the day as the platform writes it, `25 Aug 2026`
    #
    # **BOTH ARE NEEDED, AND ON THE SAME PLATFORM.** Read off his own panel on
    # 2026-08-28: an orders row reads
    # `2026-08-23_2026-08-23_2026-08-28 | 25 Aug 2026, 04:47 PM | Download`, so
    # the day it is ABOUT is written plainly and the day it was MADE is in words.
    # A returns row carries only the second. **Naming the day a file is ABOUT is
    # the stronger of the two** -- it still finds the right file when an old day
    # is being fetched, which is exactly when it matters.
    #
    # **IT NARROWS, IT NEVER LOOSENS.** Everything else still has to match; this
    # only takes matches away. So it cannot turn one right answer into a wrong
    # one -- at worst it takes the right one away too, and that refuses.
    near: str = ""

    def name(self) -> str:
        return self.called or self.what


# --------------------------------------------------------------- the steps

GO = "go"                  # to an address
CLICK = "click"            # the one thing that matches
WAIT_FOR = "wait-for"      # something to appear
PICK_RANGE = "pick-range"  # a date range
TAKE_FILE = "take-file"    # whatever download the last click produced
WAIT = "wait"              # this long, for something that is not on the page
STEP_KINDS = (GO, CLICK, WAIT_FOR, PICK_RANGE, TAKE_FILE, WAIT)

# **WHY THERE IS A STEP THAT ONLY WAITS, AND WHY NOTHING ELSE COULD DO IT.**
#
# Every other kind of waiting here waits for something to APPEAR on the page.
# `wait-for` looks, `take-file` looks, and both stop the moment they find it.
# **Meesho's orders export gives the page nothing to look at.** The file is
# built on Meesho's own servers and the page it was asked from does not change
# at all -- the finished file appears only in a list that is drawn when the page
# is LOADED AGAIN. So the only correct thing to do between asking and reloading
# is to wait, and nothing here could say that.
#
# **THE REFERENCE WAITS 35 SECONDS AND HAS DONE EVERY NIGHT FOR MONTHS**
# (`content/meesho.js:947`, "usually < 10 s, 35 s is safe"). Kartaan reloaded
# straight away, so the list was drawn before the file existed and the file was
# never in it. **The 300 seconds of patience on taking the file cannot recover
# that**: by then the list has already been built without it, and no amount of
# looking at a drawn list makes a row appear in it.


@dataclass(frozen=True)
class LookAgain:
    """Close something, wait, open it again, and look once more.

    **BECAUSE A LIST THAT IS DRAWN WHEN A MENU OPENS DOES NOT CHANGE WHILE IT IS
    OPEN.** Meesho's finished exports are listed inside the download menu, and
    the menu draws that list at the moment it is opened. Waiting on an open menu
    for five minutes is watching a photograph -- whatever was ready when it
    opened is all it will ever show.

    **THE REFERENCE CLOSES IT AND OPENS IT AGAIN, SIX TIMES, THIRTY SECONDS
    APART** (`content/meesho.js:860-878`), and has done every night for months.
    Kartaan opened the menu once and then waited 300 seconds on it, which is the
    same as not waiting at all.

    **`by` IS THE CONTROL THAT OPENS THE MENU, AND IT IS USED FOR OPENING ONLY.**
    Shutting is a click on the page where nothing is (`browser.click_away()`),
    which is the reference's own gesture -- `document.body.click()` at
    `content/meesho.js:865`.

    **AN EARLIER VERSION OF THIS PRESSED `by` TWICE INSTEAD, and it was written
    down as an assumption rather than a measurement.** Nothing in this
    repository can say whether Meesho's opener shuts the menu when it is pressed
    a second time. If it does not, both presses do nothing, the list is never
    redrawn, and six rounds of this are three minutes of a night that looks
    exactly like one that is working. Clicking away needs no such answer, and it
    is what has run every night for months.
    """

    by: Find
    # How many times to close it and open it again before giving up.
    times: int
    # How long to leave it CLOSED, in seconds. The waiting has to happen while it
    # is shut, because that is the only state in which reopening redraws anything.
    after: int


@dataclass(frozen=True)
class Step:
    """One thing to do to a page."""

    do: str
    find: Optional[Find] = None
    address: str = ""
    # How long to wait for it, in seconds. Its own number per step, because
    # "export this" and "click that" are not the same wait.
    patience: int = 30
    # What this step is for, in a sentence -- so a failure says what was being
    # attempted rather than only what could not be found.
    why: str = ""
    # **HOW MANY DAYS THE RANGE COVERS, because one is not always allowed.**
    # Flipkart's Reports Centre requires the start to be strictly before the end,
    # so the smallest range it will take is two days -- and it matches the row it
    # produces by the END date. A single-day range is simply refused, silently, by
    # a Submit that does nothing.
    range_days: int = 1
    # **WHAT TO CLOSE AND OPEN AGAIN BETWEEN LOOKS**, when the thing being looked
    # for is inside a menu that only draws its contents as it opens. See
    # `LookAgain`. It is on the step rather than in the door because which
    # control opens which menu is a platform fact, and platform facts live in
    # the recipe.
    look_again: Optional[LookAgain] = None


def why_step_is_refused(step: Step) -> Optional[str]:
    """What is wrong with a step, or None. Asked of every recipe by a check."""
    if not isinstance(step, Step):
        return "That is not a step."
    if step.do not in STEP_KINDS:
        return f"{step.do!r} is not something this door knows how to do."
    if step.do == GO and not step.address:
        return "A step that goes somewhere has to say where."
    if step.do in (CLICK, WAIT_FOR) and step.find is None:
        return f"A {step.do} step has to say what to look for."
    if step.do == WAIT and step.find is not None:
        # **A WAIT AND A WAIT-FOR ARE NOT THE SAME STEP.** One passes time; the
        # other watches the page. Written with something to look for, a wait
        # would pass its time and never look at it, and the recipe would read as
        # though it had waited FOR that thing.
        return "A step that only waits has nothing to look for. Waiting for something is a wait-for."
    if step.find is not None and step.find.how not in WAYS_OF_FINDING:
        return f"{step.find.how!r} is not a way of finding something."
    if step.find is not None and not step.find.what:
        return "A way of finding something has to say what to look for."
    if (step.find is not None and step.find.near
            and "{day}" not in step.find.near and "{day_in_words}" not in step.find.near):
        # **A ROW NAMED BY SOMETHING THAT NEVER CHANGES IS THE SAME ROW FOR
        # EVER.** The whole point of naming a row is that today's is not
        # yesterday's, and a row named without the day would fetch the same old
        # file every night while looking like it worked.
        return "Saying which row something is on has to name the day, or it is the same row every time."
    if step.patience <= 0:
        return "A step that waits no time at all cannot succeed."
    if step.range_days < 1:
        return "A range has to cover at least one day."
    if step.do != PICK_RANGE and step.range_days != 1:
        return "Only a step that picks a range can say how many days it covers."
    if step.look_again is not None:
        again = step.look_again
        if step.do != TAKE_FILE:
            # **THE ONLY STEP THAT LOOKS FOR SOMETHING IN A MENU IS THE ONE THAT
            # TAKES THE FILE.** A click or a wait-for that reopened a menu would
            # be a second, quieter way of doing what the recipe already says in
            # steps of its own, and two ways of saying one thing is what this
            # door exists to avoid.
            return "Only a step that takes a file can close and open something again between looks."
        if not isinstance(again.by, Find):
            return "Looking again has to say what to close and open again."
        if again.by.how not in WAYS_OF_FINDING:
            return f"{again.by.how!r} is not a way of finding something."
        if not again.by.what:
            return "Looking again has to say what to close and open again."
        if again.times < 1:
            return "Looking again no times at all is not looking again."
        if again.after < 1:
            # **NOUGHT SECONDS CLOSED IS A MENU THAT WAS NEVER SHUT.** The point
            # of closing it is that the platform gets time to finish while
            # nothing is watching; with no time it is opened again on the same
            # list it was closed on, every time, and reads as having tried.
            return "Looking again has to leave it closed for some time, or nothing is redrawn."
    if not step.why:
        # **NOT DECORATION.** A failure says what was being attempted, and without
        # this it can only say what could not be found -- which is how a month of
        # "button not found" told nobody that the button was underneath a dialog.
        return "A step has to say what it is for, so a failure can say what was being attempted."
    return None


# ------------------------------------------------------- what went wrong

FOUND_NOTHING = "found-nothing"
DAY_NOT_AVAILABLE = "day-not-available"
FOUND_SEVERAL = "found-several"
COVERED_UP = "covered-up"
NEEDS_SIGNING_IN = "needs-signing-in"
BUILT_IN_THE_PAGE = "built-in-the-page"
TOOK_TOO_LONG = "took-too-long"

# **EVERY ONE OF THESE IS ITS OWN FAILURE**, and that is the point. The reference
# had one -- "button not found" -- and it covered all seven. A month of diagnosis
# went at the wrong thing because "it is underneath a dialog" and "it has been
# renamed" arrived wearing the same words.
WHAT_IT_MEANS = {
    FOUND_NOTHING: (
        "It is not on the page at all. Either the platform renamed it, or the page "
        "had not finished drawing."
    ),
    FOUND_SEVERAL: (
        "More than one thing on the page matches, so which one was meant cannot be "
        "known. Nothing was clicked. Picking the first is how nine days of payments "
        "were lost to a chart legend that read like a menu item."
    ),
    COVERED_UP: (
        "Something is covering the page -- a promotion or a notice -- so a click "
        "aimed at the page hits that instead. The button is there; it is underneath "
        "something."
    ),
    NEEDS_SIGNING_IN: (
        "The portal is asking to be signed in to. **This is told apart from a page "
        "that has simply not finished drawing, and they are not the same thing:** "
        "Flipkart signed out serves its PUBLIC MARKETING SITE, whose menu reads "
        "'Sell Online, Fees and Commission, Grow, Shopsy' -- while a signed-in page "
        "mid-draw shows the seller's own top bar and no sidebar yet. Read across 71 "
        "real occurrences, 54 were the second and harmless. One message for both is "
        "why a month of these read as one problem."
    ),
    BUILT_IN_THE_PAGE: (
        "The platform now builds this file inside the page itself and hands over a "
        "temporary handle, which cannot be fetched a second time. This is a door "
        "closing, not something to retry."
    ),
    DAY_NOT_AVAILABLE: (
        "The platform draws that day in the calendar and then refuses it. Flipkart "
        "does this for a period it has not finished preparing, by two different "
        "mechanisms found weeks apart -- and a date picked anyway reads back as "
        "\"Invalid date\", after which submitting does nothing at all. Waiting is "
        "the only answer; the day usually becomes available later."
    ),
    TOOK_TOO_LONG: "The page never got to where it was supposed to be.",
}


@dataclass(frozen=True)
class WentWrong:
    """A failure, with everything needed to work out why -- captured at the time.

    **THE PAGE IS CAPTURED AUTOMATICALLY, FIRST TIME, NOT BEHIND A FLAG.** Two of
    the reference's reports went undiagnosed for over a month because the evidence
    had to be added afterwards and then somebody had to wait for the failure to
    happen again. By then it had happened thirty more times, and nobody had a
    single one of them written down.
    """

    kind: str
    looking_for: str
    doing: str
    # What the page actually looked like. Trimmed, never absent.
    page_was: str = ""
    # How many things matched, when that is the problem.
    matches: int = 0

    def say(self) -> str:
        """The sentence that goes in the run log."""
        meaning = WHAT_IT_MEANS.get(self.kind, "Something went wrong.")
        if self.kind == FOUND_SEVERAL:
            return f"{self.doing}: {self.matches} things match {self.looking_for!r}. {meaning}"
        return f"{self.doing}: could not find {self.looking_for!r}. {meaning}"

    @property
    def worth_retrying(self) -> bool:
        """Is trying again tomorrow worth anything?

        **A DOOR THAT HAS CLOSED IS NOT RETRIED.** Flipkart has started building
        files inside the page; an extension cannot fetch that handle twice, and no
        amount of retrying changes it. Reported as what it is -- the platform
        changed how it hands the file over -- rather than as a nightly failure.
        """
        return self.kind != BUILT_IN_THE_PAGE


# How much of the page to keep. Enough to see what was really there, small enough
# that a log is still readable and carries nothing of the seller's worth hiding.
PAGE_SNIPPET = 400


def capture(page_text: str) -> str:
    """What to keep of the page when something could not be found."""
    return " ".join(str(page_text or "").split())[:PAGE_SNIPPET]


# ---------------------------------------------------- is the page covered?

# **WHAT A COVERING LOOKS LIKE, read off his own Meesho panel.** The promotion
# sits on `role="dialog"` over a full-screen backdrop. Its close control is an
# `<img>` with no class, no aria-label, no data-testid and no text -- and
# **Escape does not close it**, tested. So there is no selector-based way to shut
# it, and the answer is not to try: it is to reach the section by its address and
# to say clearly when something is in the way.
def is_covered(overlays: Sequence[Dict]) -> Optional[WentWrong]:
    """Is something sitting over the page? Answers the failure, or None.

    `overlays` is what the browser found: anything calling itself a dialog, and
    anything laid over the whole window -- each with its size, whatever words are
    on it, and **whether it would actually swallow a click**.

    **ASKED BEFORE EVERY CLICK, not after one fails.** Asked afterwards, the
    failure has already been recorded as "button not found" -- which is exactly
    what happened for a month.

    **IT ASKS WHETHER ANYTHING WOULD SWALLOW A CLICK, NOT HOW BIG ANYTHING IS,
    and that is a correction made on 2026-08-28 with both sides measured live.**
    This used to refuse at 300 x 200. The download menu the recipe opens ON
    PURPOSE calls itself a dialog and is **232 x 196** -- it missed being called a
    covering by FOUR PIXELS in one direction, and a slightly larger menu would
    have stopped every Meesho report because of a menu the door had just opened.
    The promotion that really does block is 414 x 330. **What separates them is
    not size: the promotion is laid over the whole window and the menu is not.**
    """
    seen = list(overlays or ())
    blocking = next((one for one in seen if one.get("blocks")), None)
    if blocking is None:
        return None

    def words_of(one):
        return " ".join(str(one.get("text") or "").split())[:120]

    # **A BACKDROP CARRIES NO WORDS OF ITS OWN.** They are on whatever sits on
    # top of it, and without them a failure cannot say WHICH promotion it was --
    # which is the whole reason the words are kept.
    said = words_of(blocking)
    if not said:
        said = next((words_of(one) for one in seen
                     if one is not blocking and words_of(one)), "")
    return WentWrong(
        kind=COVERED_UP,
        looking_for="the page itself",
        doing="checking nothing is in the way",
        page_was=said,
    )


# **THE RECIPES ARE NOT IN THIS FILE.** This is the LANGUAGE -- what a step is,
# what a failure is called, and what counts as something covering the page. The
# recipes for each platform are in `recipes.py`, one list for all of them, so that
# adding a report is one entry and nothing else (D100).
