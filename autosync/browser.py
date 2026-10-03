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


BY_THE_CONTROL_BESIDE = "beside"  # the box these words label, not the words

# **THE FIFTH ONE EXISTS BECAUSE OF FLIPKART'S REPORTS CENTRE, and it is the
# 2026-09-10 correction.** That sub-page shows the words **Select Date Range**
# with the calendar hidden behind a box beside them. A step here pressed the
# WORDS, and it could never have worked twice over:
#
#   - the words are a plain label with nothing pressable about them, so
#     `BY_PRESSABLE_TEXT` refuses them -- no control tag, no role, no pointer
#     cursor;
#   - and the box itself does not carry the words at all. What an input carries
#     is its VALUE, which on that page is the range currently showing --
#     `01 Jun 2026 - 06 Jun 2026` (`DOCS.md:1803`), never the words being looked
#     for. So no way of finding that reads words could reach it either.
#
# **THE REFERENCE HAS NEVER PRESSED THE LABEL** (`content/flipkart.js` StepD-0):
# it finds the leaf holding those words, walks up as far as five ancestors, and
# presses the input, the calendar icon or the date value sitting beside them.
# That is what this is, and it is nothing else -- the words say WHICH box, and
# the box is what is pressed.
#
# **IT IS ASKED FOR BY NAME, NEVER FALLEN BACK TO.** A way of finding that
# quietly tried the label and then the box beside it would be two lookups
# wearing one name, and the day one of them stopped working nothing would say so.


BY_A_REAL_BUTTON = "button"  # a real <button> carrying these words, nothing pretending

# **THE SIXTH ONE EXISTS BECAUSE OF MEESHO'S PAYMENTS MODAL, read off his own
# panel on 2026-09-11 with that modal open.** By the time the last step runs, two
# things on that page read the single word "Download":
#
#   DIV role="button" tabindex="0"   the opener, top right, inside the HEADER
#   BUTTON type="button"             the one inside the export modal
#
# **EVERY WAY OF FINDING ABOVE MATCHES BOTH, so the step refuses as ambiguous** --
# which is what his own run said twice: *"2 things match 'Download'."* Words match
# both. Pressable matches both (Meesho styles the opener's cursor). **And asking
# for a CONTROL matches both too, because `role="button"` is exactly how a page
# says a div is a control** -- that is the whole purpose of the attribute, and
# taking it away would break Flipkart, which has real roles everywhere.
#
# **THE REFERENCE TELLS THEM APART BY THE TAG AND HAS FOR MONTHS**
# (`content/meesho.js handlePayments`): for the opener it searches
# `p, button, [role="button"]`, and for the final button it searches
# `querySelectorAll('button')` and nothing else. Two different searches on one
# page, on purpose. This is that second search, named.
#
# **IT IS THE NARROWEST WAY THERE IS, AND THAT IS THE POINT.** Everything it
# finds, `BY_ROLE_AND_TEXT` finds too; it can never reach something the others
# could not. So it is asked for by name where a page has both kinds and means
# different things by them -- never fallen back to, for the same reason
# `BY_THE_CONTROL_BESIDE` is not.


BY_THE_BUTTON_BESIDE = "button-beside"  # the button on the row these words name

# **THE SEVENTH ONE EXISTS BECAUSE OF THE REPORTS CENTRE REQUEST DIALOG, read off
# his own Flipkart on 2026-09-11 with that dialog open, row by row.**
#
# **THE SUB-KIND IS NOT A CONTROL AND NEVER WAS.** Choosing the report to request
# looked like pressing `Orders`, and measured, `Orders` is a **`span` with
# `cursor: auto`** -- a row heading. Pressing it does nothing at all, and nothing
# on this list could even find it. **What starts a request is a real `button`
# reading `REQUEST REPORT`, and there is one on every row:**
#
#   DIV  ->  SPAN "DBD Breached Shipments Report"   BUTTON "REQUEST REPORT"
#   DIV  ->  SPAN "Orders"                          BUTTON "REQUEST REPORT"
#   DIV  ->  SPAN "Pickup Report"                   BUTTON "REQUEST REPORT"
#   DIV  ->  SPAN "Returns"                         BUTTON "REQUEST REPORT"
#   DIV  ->  SPAN "Seller Cancelled Shipments"      BUTTON "REQUEST REPORT"
#
# **SO FIVE BUTTONS READ THE SAME WORDS AND ONLY THE ROW TELLS THEM APART.**
# Asked for by its words alone the step finds five and refuses -- which is right,
# and useless. The words that name the row are the sub-kind, and what is pressed
# is the button beside them.
#
# **THE REFERENCE HAS DONE EXACTLY THIS FOR MONTHS** (`content/flipkart.js`
# StepC): it finds the leaf whose text is the sub-type, walks up as far as eight
# ancestors, finds the element matching `/request\s*report/i` inside that
# ancestor, and presses that.
#
# **WHY IT IS NOT `near` INSTEAD.** `near` names a row BY THE DAY, and the door
# refuses a `near` with no day in it on purpose -- a row named by something that
# never changes is the same row every night, which would fetch last month's file
# while looking like it worked. **This dialog is a fixed menu, not a list of
# files**, so the day has no part in it. Bending `near` would have put a hole in
# the rule that stops a year-old file being fetched under today's name.
#
# **AND IT IS THE SAME SHAPE AS `BY_THE_CONTROL_BESIDE`, deliberately.** The
# words say WHICH row; the thing pressed is what sits beside them. That one takes
# the box something is typed in; this one takes a real button, and nothing
# pretending -- for the same reason `BY_A_REAL_BUTTON` exists.


WAYS_OF_FINDING = (BY_TEXT, BY_ROLE_AND_TEXT, BY_TEST_ID, BY_PRESSABLE_TEXT,
                   BY_THE_CONTROL_BESIDE, BY_A_REAL_BUTTON, BY_THE_BUTTON_BESIDE)

# ---------------------------------------------------- which day names the row

# **WHICH DAY A ROW IS NAMED BY, and the two portals answer it differently.**
#
# **THIS IS THE 2026-09-10 CORRECTION AND IT REPLACED ONE WRONG STRING WITH
# ANOTHER BEFORE IT WAS CAUGHT.** Naming a row by "the day, in the portal's own
# wording" is not one question but two, and only the first was ever asked:
#
#   whose wording  -- `1 Sep 2026` or `01 Sep 2026`; already said, and needed;
#   WHICH DAY      -- the day the data is about, or the day the export was made.
#
# **MEESHO'S PANEL NAMES A ROW BY THE DAY THE EXPORT WAS MADE.** Read off his own
# returns page on 2026-08-28: `completed_delivered_last_2_week | 25 Aug 2026,
# 04:49 PM | Download`. A returns export is always the last two weeks, so there
# is no data date on the row at all -- the only day it carries is the moment the
# file was built, which is the day the run is happening. The reference says so
# in one function: `content/meesho.js:1055` matches the row with `todayISO()`
# and names the saved file with `yesterdayISO()`, two lines apart.
#
# **FLIPKART'S REPORTS CENTRE NAMES A ROW BY THE END OF ITS RANGE**, which IS the
# day the data is about: `... 05 Jun 2026 To 06 Jun 2026 Generated`, and the
# reference passes yesterday to its row matcher.
#
# **FILLED IN WITH THE WRONG ONE IT FINDS NOTHING, EVERY NIGHT, IN SILENCE.** On
# a run of 25 August, Meesho's row was looked for as `24 Aug 2026` on a row
# reading `25 Aug 2026` -- and that reads as the portal having renamed something.
THE_DAY_IT_IS_ABOUT = "about"   # the data date: Flipkart's Reports Centre
THE_DAY_IT_WAS_MADE = "made"    # the day of the run: Meesho's exported-files panel
WHICH_DAY_A_ROW_IS_NAMED_BY = (THE_DAY_IT_IS_ABOUT, THE_DAY_IT_WAS_MADE)


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
    # **AND WHAT ELSE THAT ROW HAS TO SAY, when the day alone names more than one
    # of them. This is ANDed with `near`, never ORed with it.**
    #
    # **Flipkart's Reports Centre is the whole reason it exists.** Orders,
    # returns and settled transactions are all requested on the same night for
    # the same range, so all three rows read `... To 06 Jun 2026`. Narrowed by
    # the day alone, one lookup matches three rows -- and the step that takes the
    # newest of several then takes whichever is topmost. **That is the payments
    # file landing under the orders name, silently, in the seller's books.**
    #
    # The working reference asks the two questions separately and asks the
    # sub-type FIRST (`content/flipkart.js` `findReportRowDownloadBtn`: its first
    # test is `if (!rowLow.includes(subLow)) continue;`, with the sub-type held
    # beside each job in `REPORTS_CENTRE_CFG`). This is that test.
    #
    # **IT NEVER NAMES A DAY.** The day is `near`'s question, and only `near`
    # carries the rules about whose wording and which day. Something that named
    # the day here would be a second, unchecked way of saying the same thing.
    #
    # **IT NARROWS, IT NEVER LOOSENS** -- same as `near`. At worst it takes the
    # right row away too, and then nothing is found and the step refuses, which
    # is the safe direction.
    also_saying: str = ""
    # **WHOSE WORDING OF A DAY `{day_in_words}` MEANS, and it has to be said
    # because no two portals write a day the same way.**
    #
    #   Meesho   `1 Sep 2026`   -- no leading nought
    #   Flipkart `05 Jun 2026`  -- with one
    #
    # Both were read off the real thing, and each is written down beside its own
    # measurement in `recipes.py`. **ONE SHARED WAY OF WRITING A DAY WOULD BE
    # WRONG ON ONE PORTAL FOR NINE DAYS OF EVERY MONTH** -- every day whose
    # number is under ten -- and wrong in the way that quietly finds nothing
    # rather than the way that complains.
    #
    # **THIS FILE STILL KNOWS NOTHING ABOUT EITHER PLATFORM.** All it insists on
    # is that a lookup naming a row by the day in a portal's own wording says
    # WHOSE wording it means. The wordings themselves, and which portal each
    # belongs to, are platform facts and live in `recipes.py` with everything
    # else that was measured off a real page.
    day_in_words_is: str = ""
    # **AND WHICH DAY `{day_in_words}` MEANS -- the day the data is about, or the
    # day the export was made. The two portals answer it differently.** See
    # `WHICH_DAY_A_ROW_IS_NAMED_BY` above for the measurements.
    #
    # **IT IS A SECOND QUESTION, NOT A REFINEMENT OF THE FIRST.** Saying whose
    # wording answers `1 Sep` against `01 Sep`; it says nothing at all about
    # WHICH day is written there, and a lookup that gets the wording right and
    # the day wrong finds exactly as little as one that gets both wrong.
    day_in_words_of: str = ""

    def name(self) -> str:
        return self.called or self.what


# --------------------------------------------------------------- the steps

GO = "go"                  # to an address
CLICK = "click"            # the one thing that matches
WAIT_FOR = "wait-for"      # something to appear
PICK_RANGE = "pick-range"  # a date range
TAKE_FILE = "take-file"    # whatever download the last click produced
WAIT = "wait"              # this long, for something that is not on the page
READ_NUMBER = "read-number"        # the number a label on the page names
ADD_TO_THE_LIST = "add-to-the-list"  # what was read, as a row on a running list
SWEEP_THE_ADS = "sweep-the-ads"    # ask the platform's own ads addresses, from its page
TYPE_IN = "type-in"                # words into the one box that matches
READ_THE_KEYWORDS = "read-the-keywords"  # every listing's top search keywords, off the page
STEP_KINDS = (GO, CLICK, WAIT_FOR, PICK_RANGE, TAKE_FILE, WAIT,
              READ_NUMBER, ADD_TO_THE_LIST, SWEEP_THE_ADS, TYPE_IN, READ_THE_KEYWORDS)

# **THE ELEVENTH READS FLIPKART'S TOP SEARCH KEYWORDS OFF THE TRAFFIC REPORT
# (2026-09-15).** Named for exactly what it does, like the ads sweep: every listing
# row's keyword pop-up opened, read and closed, on every page, made into one CSV --
# the reference's `handleFkKeywords`, whose Flipkart words live in one checked file
# (`extension/keywords.js`) rather than in a table of steps.

# **THE TENTH TYPES, AND IT EXISTS FOR ONE REPORT: FLIPKART'S OVERALL PERFORMANCE
# REPORT (2026-09-15).** Its Download stays switched off until a campaign is
# chosen, and a campaign is chosen by typing its id into a search box and pressing
# the suggestion. The reference types it with the page's own insert-text command,
# because setting the box's value does not start Flipkart's search
# (`content/flipkart.js` `_handleFkAdsOverall`).
#
# **AND THOSE STEPS ARE DONE ONCE PER CAMPAIGN**, because the report is one file per
# campaign that ran. Which campaigns ran is read from the ads daily file for the
# same day -- see `recipes.CampaignsFrom`.
ONCE_PER_CAMPAIGN = (TYPE_IN, CLICK, WAIT_FOR, TAKE_FILE)

# **THE NINTH IS THE ONE THAT PRESSES NOTHING AT ALL, and it is named for exactly
# what it does rather than pretending to be general.**
#
# **WHY IT IS NOT A GENERAL "CALL AN ADDRESS" STEP.** Meesho's ads figures come
# from two of its own addresses, called from inside the signed-in page: a list of
# campaigns, ten at a time, and then one call per campaign for a day's numbers.
# Turning that into recipe steps would need paging, a loop over what came back,
# and a way of saying which field goes in which column -- **a recipe pretending to
# be a program.** The names of those fields are Meesho's, they change when Meesho
# changes them, and they belong in one file that can be read and checked
# (`extension/ads.js`) rather than scattered through a table of steps.
#
# **AND THE SELLER IS NEVER WRITTEN DOWN ANYWHERE. HIS INSTRUCTION, 2026-09-11:**
# *"make sure it is not hard coded to any one seller... it should be able to
# handle the multi seller thing."* Both things those addresses need -- the panel
# slug and the numeric supplier id -- are read from cookies Meesho sets for
# whoever is signed in (`current_az_identifier` and `s_id`), measured on a real
# panel. **The reference hard-codes one seller's slug in its own config
# (`config.js:11`) and finds the numeric id by scraping localStorage key names --
# which returns nothing at all on that same panel today.**

# **THE LAST TWO EXIST BECAUSE SOME NUMBERS ARE NOT A DOWNLOAD AT ALL, and until
# 2026-09-11 this door could not reach them.**
#
# Meesho shows the day's views and orders on a card on its dashboard and sells no
# export of them short of a paid subscription. **There is no button to press and
# no file to take.** Every step above is about making a platform hand over a file;
# these two are about reading a figure off the page and writing it down.
#
# **THEY ARE TWO STEPS AND NOT ONE, because a card is one number and a row is
# several.** Views and orders sit in two different cards on the same page, and a
# single step that did both would have to carry a list of labels and a column
# order and a file name -- which is a recipe pretending to be a program. Two
# plain steps read two numbers; the third writes the row.
#
# **AND THE ROW IS ADDED TO ONE FILE, NOT WRITTEN AS A NEW ONE EACH DAY.** That is
# his decision of 2026-09-11, put to him as a question and answered: the working
# reference has kept these in one running CSV since it was written, and
# `reports.a_running_list` is where that shape is declared and explained.
#
# **THE DAY IS WRITTEN THE WAY EVERYTHING ELSE HERE WRITES A DAY -- ISO, the same
# `date.isoformat()` the file names use and the same spelling that reaches the
# ledger** (`reading.a_reading` hands the ERP `data_date=when.isoformat()`). A
# second spelling of a day is a second record of one fact.

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
class PressAgain:
    """Press a control again, while this step is still waiting for what it opens.

    **BECAUSE THE CONTROL TOGGLES, AND A PRESS THAT WENT ASTRAY LEAVES IT SHUT.**
    Flipkart's Reports Centre hides its calendar behind two controls in a row --
    a date box, and a **Custom** chip underneath it -- and both of them toggle.
    A press that arrives while the sub-page is still drawing opens nothing; a
    press that arrives twice shuts what it opened. Either way the step after it
    waits out its whole patience at a page that will never change.

    **THE REFERENCE DOES BOTH OF THESE AND HAS DONE EVERY NIGHT FOR MONTHS**
    (`content/flipkart.js` StepD): while polling for the Custom chip it presses
    the date box again on every third look, and while polling for the calendar
    it presses the chip again once. **Both were dropped when those two steps were
    carried across on 2026-09-10, with no reason given** -- and dropped, the only
    symptom is a step that quietly waits its full patience out.

    **IT IS NOT `LookAgain`, AND THE TWO ARE NOT TO BE FOLDED TOGETHER.**
    `LookAgain` shuts a menu on purpose, leaves it shut so the platform can
    finish, and opens it again to make it REDRAW. This presses one control again
    because the first press may not have landed. Different gesture, different
    reason, different portal.
    """

    by: Find
    # How long to wait before pressing it again, in seconds.
    after: int
    # At most how many extra presses. Never unlimited: a control pressed for ever
    # is a control being toggled open and shut for ever.
    times: int


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
    # **THIS CALENDAR SWITCHES A DAY OFF TWO DIFFERENT WAYS, AND ONE OF THEM CAN
    # ONLY BE READ IN THE CURSOR.** Both were confirmed live on his own Flipkart
    # with the browser's own tools, weeks apart, and written into the reference's
    # own record:
    #
    #   - a day whose report period is not open yet keeps every ordinary class
    #     and is given `pointer-events: none`;
    #   - a day genuinely outside the range gets a `blocked_out_of_range` class
    #     which **does not touch pointer-events at all** -- it reports
    #     `cursor: no-drop` where a day that can be pressed reports
    #     `cursor: pointer`.
    #
    # **ONE CHECK COULD NEVER CATCH BOTH**, which is why the reference reads both
    # and why it does so on Flipkart's three Reports Centre reports only.
    #
    # **AND THAT IS WHY IT IS ASKED FOR HERE RATHER THAN BUILT INTO THE DOOR.**
    # "Anything that is not a pointer is switched off" is this platform's own
    # habit, not a rule of browsers -- an ordinary unstyled cell has no pointer
    # cursor either, and a door that read that everywhere would refuse days that
    # are perfectly available on some other portal's calendar. So the platform
    # fact stays in the recipe, like every other platform fact here, and the door
    # is told which calendar it is standing in front of.
    switched_off_days_change_the_cursor: bool = False
    # **WHAT TO CLOSE AND OPEN AGAIN BETWEEN LOOKS**, when the thing being looked
    # for is inside a menu that only draws its contents as it opens. See
    # `LookAgain`. It is on the step rather than in the door because which
    # control opens which menu is a platform fact, and platform facts live in
    # the recipe.
    look_again: Optional[LookAgain] = None
    # **A CONTROL THAT TOGGLES, PRESSED AGAIN WHILE THIS STEP WAITS.** See
    # `PressAgain`. On the step rather than in the door for the same reason as
    # everything else here: which control toggles is a platform fact.
    press_again: Optional[PressAgain] = None
    # **SOMETHING ELSE A WAIT MAY COUNT INSTEAD -- HIS RULING, 2026-09-14.** A
    # confirmation banner can come and go before a slowed tab looks, and the
    # reference then checks the durable place the platform lists what was asked
    # for (`content/flipkart.js` `decideReportSubmissionOutcome`). So a wait may
    # name that place too, and finding it counts as finding what was waited for.
    or_find: Optional[Find] = None
    # **WHAT A TYPING STEP TYPES.** `{campaign}` is the one placeholder it may carry.
    words: str = ""
    # **DONE ONCE FOR EACH CAMPAIGN THAT RAN THAT DAY** (2026-09-15). A run of these
    # steps is repeated per campaign, with `{campaign}` filled in each time.
    for_each_campaign: bool = False
    # **PRESSED THE WAY A MOUSE PRESSES: BUTTON DOWN, BUTTON UP, CLICK** (2026-09-15).
    # Flipkart's campaign suggestion picks a campaign when the button goes DOWN, so
    # a bare click lands and selects nothing -- measured on his own page: the same
    # element, pressed all three ways, drew `Ad Group` and switched Download on.
    # A flag on the one step rather than a change to every press, his ruling.
    press_like_a_mouse: bool = False


def why_step_is_refused(step: Step) -> Optional[str]:
    """What is wrong with a step, or None. Asked of every recipe by a check."""
    if not isinstance(step, Step):
        return "That is not a step."
    if step.do not in STEP_KINDS:
        return f"{step.do!r} is not something this door knows how to do."
    if step.do == GO and not step.address:
        return "A step that goes somewhere has to say where."
    if step.do in (CLICK, WAIT_FOR, READ_NUMBER, TYPE_IN) and step.find is None:
        return f"A {step.do} step has to say what to look for."
    # **A NUMBER IS READ BY THE LABEL BESIDE IT, so the label is what names the
    # column it lands in.** Unnamed, two cards on one page would both write into
    # a column called nothing, and the row would be built in whatever order the
    # steps happened to run.
    if step.do == ADD_TO_THE_LIST and step.find is not None:
        return ("A step that adds a row looks for nothing. It writes down what the "
                "read-number steps before it already read.")
    # **A SWEEP LOOKS AT NO PAGE.** It asks the platform's own addresses from
    # inside the signed-in page; there is nothing on the screen for it to find,
    # and a lookup written on one would never be used.
    if step.do == SWEEP_THE_ADS and step.find is not None:
        return ("A step that sweeps the ads addresses looks for nothing on the page. "
                "It asks the platform directly.")
    if step.do == READ_THE_KEYWORDS and step.find is not None:
        return ("A step that reads the keywords looks for nothing of its own. What it reads "
                "is written down in one place.")
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
    if (step.find is not None and "{day_in_words}" in step.find.near
            and not step.find.day_in_words_is):
        # **A DAY IN THE PLATFORM'S OWN WORDING IS NOT ONE THING, AND THIS IS THE
        # WHOLE OF THE HOLE THIS RULE CLOSES.** Meesho writes `1 Sep 2026` and
        # Flipkart's Reports Centre writes `05 Jun 2026`, and a lookup that does
        # not say which of the two it means can only be filled in by guessing.
        # Guessed wrong it finds nothing at all -- on nine days of every month,
        # silently, on the platform, at night.
        return ("A row named by the day in the platform's own wording has to say whose wording, "
                "because no two platforms write a day the same way.")
    if (step.find is not None and step.find.day_in_words_is
            and "{day_in_words}" not in step.find.near):
        # **IT DESCRIBES ONE PLACEHOLDER, AND ONLY ONE LOOKUP CARRIES ONE.**
        # The same shape as the rule above about which calendar a range step
        # stands in front of: said anywhere else it reads as a fact about the
        # whole step, and the day somebody believed that, a lookup with no day in
        # it at all would look as though it had one.
        return ("Only a lookup that names a row by the day in the platform's own wording can say "
                "whose wording of a day it means.")
    if (step.find is not None and "{day_in_words}" in step.find.near
            and not step.find.day_in_words_of):
        # **WHOSE WORDING IS ONLY HALF THE QUESTION, and the other half cost a
        # night.** A row named `25 Aug 2026` on Meesho is named by the day the
        # export was MADE; a row named `06 Jun 2026` on Flipkart is named by the
        # day the data is ABOUT. Said in Meesho's wording and filled with the
        # data date, the lookup asks for `24 Aug 2026` on a row that reads
        # `25 Aug 2026` -- right wording, wrong day, nothing found, in silence.
        return ("A row named by the day in the platform's own wording has to say WHICH day -- "
                "the day the data is about, or the day the export was made.")
    if (step.find is not None and step.find.day_in_words_of
            and step.find.day_in_words_of not in WHICH_DAY_A_ROW_IS_NAMED_BY):
        # **A TYPO HERE IS NOT A DIFFERENT DAY, IT IS NO DAY AT ALL**, and it says
        # so by name rather than falling back to one of the two.
        return (f"{step.find.day_in_words_of!r} is not a day a row can be named by. It is either "
                "the day the data is about or the day the export was made.")
    if (step.find is not None and step.find.day_in_words_of
            and "{day_in_words}" not in step.find.near):
        # Same shape as the rule about whose wording: it describes one
        # placeholder, and only one lookup carries one.
        return ("Only a lookup that names a row by the day in the platform's own wording can say "
                "which day it means.")
    if (step.find is not None and step.find.also_saying
            and not step.find.near
            and step.find.how != BY_THE_BUTTON_BESIDE):
        # **WHAT ELSE A ROW SAYS NARROWS; IT DOES NOT NAME A ROW ON ITS OWN.**
        # The report's own kind is on the same row every night, so a lookup
        # narrowed by it alone is narrowed to the whole of that report's history
        # -- and would take last month's file while looking like it worked. It is
        # the second of two tests, and the first one is the day.
        #
        # **AND THE ONE WAY OF FINDING THIS DOES NOT APPLY TO, WITH THE REASON,
        # BECAUSE AN EXCEPTION WITHOUT ONE IS HOW A RULE ROTS.** The rule exists
        # because a row in a LIST OF FILES has to be named by the day, or the
        # same old file is fetched every night. `BY_THE_BUTTON_BESIDE` does not
        # look at a list of files: it looks at a FIXED MENU of reports that can
        # be requested, where the day has no part at all -- and there is nothing
        # there to fetch, only a button to press. **What it needs narrowing
        # against is the same words somewhere else on the page**: read off his
        # own Reports Centre on 2026-09-11 with the dialog open, the word
        # `Orders` is a leaf in the dialog's row AND a leaf in the list of
        # reports already requested behind it. Both walk up to a button, so the
        # step finds two and refuses. **The dialog's row also says
        # `REQUEST REPORT` and the list's row does not**, which is exactly what
        # this field means and is what tells them apart.
        return ("What else a row says only narrows a row already named by the day. "
                "On its own it is the same row every time.")
    if (step.find is not None and ("{day}" in step.find.also_saying
                                   or "{day_in_words}" in step.find.also_saying)):
        # **THE DAY IS ASKED IN ONE PLACE, and this is not it.** Every rule about
        # whose wording a day is written in, and which day a row is named by,
        # hangs off `near`. A day named here would be filled in by nothing and
        # would cross to the page as the literal characters -- finding no row at
        # all, in silence, which is the fault those rules were written after.
        return "The day belongs in the row a lookup names, not in what else that row says."
    if step.find is not None and "{panel}" in step.find.near:
        # **A ROW IS NEVER NAMED BY THE SELLER'S OWN PANEL NAME**, and until this
        # rule existed nothing said so on either side: the Python filled `{panel}`
        # into the address only, while the JavaScript filled it into `near` as
        # well. So one half would have narrowed to a real row and the other to a
        # row containing the literal characters `{panel}`. **Two halves quietly
        # disagreeing is the fault the whole generated crossing exists to stop**,
        # and the cheaper cure is to refuse the placeholder in the one place it
        # has no business being. The panel name belongs in an address.
        return "A row is named by the day, never by the seller's own panel name."
    if "{day_in_words}" in step.address:
        # **AN ADDRESS CANNOT SAY WHOSE WORDING IT WANTS**, because whose wording
        # is said on the lookup and an address has no lookup. Filled in anyway it
        # would be filled from whichever wording happened to be nearest, which is
        # the guess this whole rule exists to stop. A day in an address is the
        # plain `{day}`.
        return "An address names the day plainly, not in a platform's own wording."
    if step.patience <= 0:
        return "A step that waits no time at all cannot succeed."
    if step.range_days < 1:
        return "A range has to cover at least one day."
    if step.do != PICK_RANGE and step.range_days != 1:
        return "Only a step that picks a range can say how many days it covers."
    if step.do != PICK_RANGE and step.switched_off_days_change_the_cursor:
        # **IT DESCRIBES A CALENDAR, AND ONLY ONE STEP STANDS IN FRONT OF ONE.**
        # Anywhere else it would read as a rule about the whole page -- and the
        # day somebody believed that, every ordinary label on the portal would be
        # a thing this door thought was switched off.
        return "Only a step that picks a range can say how that calendar switches a day off."
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
    if step.press_again is not None:
        press = step.press_again
        if step.do not in (CLICK, WAIT_FOR, PICK_RANGE):
            # **ONLY A STEP THAT WAITS FOR SOMETHING TO APPEAR HAS ANYTHING TO
            # PRESS AGAIN FOR.** A `go` or a `wait` is not waiting on a control,
            # and a `take-file` already has `look_again` for the one menu that
            # needs redrawing -- two mechanisms on one step would be two ways of
            # saying one thing, which is what this door exists to avoid.
            return ("Only a step waiting for something to appear can press a control again while "
                    "it waits.")
        if not isinstance(press.by, Find):
            return "Pressing again has to say what to press."
        if press.by.how not in WAYS_OF_FINDING:
            return f"{press.by.how!r} is not a way of finding something."
        if not press.by.what:
            return "Pressing again has to say what to press."
        if press.times < 1:
            return "Pressing again no times at all is not pressing again."
        if press.after < 1:
            # **NOUGHT SECONDS IS NOT WAITING, IT IS DOUBLE-CLICKING.** The whole
            # reason to press a toggling control again is that time has passed and
            # what it opens has still not appeared. With no time between them the
            # second press lands on a control the first one has just opened, and
            # shuts it.
            return "Pressing again has to wait some time first, or the second press shuts it."
    if step.or_find is not None:
        if step.do != WAIT_FOR:
            # **ONLY A WAIT HAS SOMETHING ELSE IT COULD COUNT.** A click presses one
            # thing; letting it press another instead would be the coin toss.
            return "Only a step that waits for something can accept something else instead."
        if (not isinstance(step.or_find, Find) or step.or_find.how not in WAYS_OF_FINDING
                or not step.or_find.what):
            return "Something else a wait may count has to say what to look for."
    if step.press_like_a_mouse and step.do != CLICK:
        return "Only a step that presses something can say how to press it."
    if step.do == TYPE_IN and not step.words:
        return "A step that types has to say what to type."
    if step.do != TYPE_IN and step.words:
        return "Only a step that types can say what to type."
    if step.for_each_campaign and step.do not in ONCE_PER_CAMPAIGN:
        # **A CAMPAIGN'S STEPS STAY ON ONE PAGE.** Going somewhere ends the page the
        # walk is running in, and a range or a wait is set once for the report.
        return ("Only typing, pressing, waiting for something or taking a file can be done "
                "once per campaign.")
    if (("{campaign}" in step.words or (step.find is not None and "{campaign}" in step.find.what))
            and not step.for_each_campaign):
        return "Only a step done once per campaign can name the campaign."
    if "{campaign}" in step.address or (step.find is not None and (
            "{campaign}" in step.find.near or "{campaign}" in step.find.also_saying)):
        return "A campaign is named in what a step types or looks for, never in an address or a row."
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
