"""How to fetch every report that needs a browser. One list, both platforms.

Phases 4 and 5. **This is the whole design in one file (D100): adding a report is
one entry here and nothing else.** The language it is written in -- what a step is,
what a failure is called -- is `browser.py`, and it knows nothing about either
platform.

**FLIPKART'S REPORTS CENTRE IS TWO-PHASE, and that is the shape phase 5 added.**
You ask for a report, Flipkart goes away and builds it for twenty minutes or so,
and a later run collects it. That is exactly what Amazon's `createReport` does, and
it maps onto the same two things the runner already carries: **still waiting**, and
**what it was asked under**. So the runner cannot tell an Amazon report being built
from a Flipkart one, which is the point.

**A REPORT ASKED FOR IS NEVER ASKED FOR AGAIN.** On Flipkart this is not politeness
-- its Reports Centre allows **twenty requests a day**, and the reference burned
through them re-submitting reports that had actually worked, then spent the rest of
the day locked out. The runner already holds what is in flight; this just has to
declare which reports have an asking phase at all.

**WHERE FLIPKART STANDS TODAY, said plainly so nobody re-derives it:** its Seller
API application has been **Pending since 27 May** and answers a rate-limit error;
a support ticket is open. So every Flipkart report below is on the browser door.
**Moving one to the API is one word in `reports.py`** -- `door=API` -- and nothing
here or above changes at all. That was the whole reason for the two doors.
"""

import re
from dataclasses import dataclass, field, replace
from typing import Dict, Optional, Tuple

from browser import (
    BY_PRESSABLE_TEXT,
    ADD_TO_THE_LIST,
    SWEEP_THE_ADS,
    BY_A_REAL_BUTTON,
    BY_ROLE_AND_TEXT,
    READ_NUMBER,
    READ_THE_KEYWORDS,
    BY_TEXT,
    BY_THE_CONTROL_BESIDE,
    BY_THE_BUTTON_BESIDE,
    CLICK,
    GO,
    PICK_RANGE,
    TAKE_FILE,
    THE_DAY_IT_IS_ABOUT,
    THE_DAY_IT_WAS_MADE,
    TYPE_IN,
    WAIT,
    WAIT_FOR,
    Find,
    LookAgain,
    PressAgain,
    Step,
)
# **WHICH PLATFORM A REPORT BELONGS TO IS THE REPORT LIST'S ANSWER, not this
# file's.** It is needed here for one thing only: to refuse a recipe that names
# another portal's wording of a day. Read off the front of the report's name it
# would be a spelling, and a spelling is not a fact (D170).
from reports import report as kartaan_report


@dataclass(frozen=True)
class CampaignsFrom:
    """Where the campaigns that ran on a day are read from (2026-09-15).

    **THE REFERENCE'S OWN SOURCE FOR THEM** (`background.js`
    `_setFkAdsDailyCacheFromBuffer`): the ads daily file for the same day, the rows
    whose day column is that day, each campaign id once. Kept in the browser when
    that file lands, and read back by the report that is done once per campaign.
    """

    report: str
    id_column: str
    day_column: str


@dataclass(frozen=True)
class Recipe:
    """How one report is fetched.

    `to_ask` is empty for a report you simply take. It is filled in for one the
    platform has to go away and build -- and **a recipe with an asking phase is
    never asked twice**, which on Flipkart is the difference between working and
    being locked out for the day.
    """

    to_take: Tuple[Step, ...]
    to_ask: Tuple[Step, ...] = ()
    # Roughly how long the platform takes to build it, for the log to say so.
    # **Only meaningful for a two-phase report** -- a one-shot one is not built by
    # anybody, so it says nothing rather than a number nothing reads.
    ready_in_minutes: int = 0
    # **WHICH CAMPAIGNS RAN, FOR A REPORT DONE ONCE PER CAMPAIGN.** None on every
    # recipe but Flipkart's overall performance report.
    campaigns_from: Optional[CampaignsFrom] = None

    @property
    def two_phase(self) -> bool:
        return bool(self.to_ask)


# **HOW EACH PLATFORM WRITES A DAY -- SEVERAL SPELLINGS PER PLATFORM, BECAUSE
# EACH PLATFORM HAS BEEN MET WRITING MORE THAN ONE.**
#
# **THIS IS THE CORRECTION OF 2026-09-10, AND IT IS THE SUBTLEST OF THE WEEK.**
# What stood here was one spelling per portal, each picked off one recorded row.
# The working reference does not do that on either portal: it builds a LIST of
# spellings and takes a row that matches ANY of them --
# `content/flipkart.js findReportRowDownloadBtn` builds five, and
# `content/meesho.js findExportDownloadByTodayDate` builds six. **It does not
# commit to one because it met more than one.** Committing to one here chose,
# on Flipkart, a spelling that the reference's own working matcher excludes.
#
# **SO WHAT IS COPIED IS THE TOLERANCE, NOT THE STRING.** Every spelling below
# names the SAME ONE DAY, so trying more of them can never match a different
# day's row -- it can only stop a right row being missed over a leading nought.
#
# **AND THE CALENDAR SPELLINGS ARE NOT THESE.** The month headings a calendar
# draws, and the wording of a row in a list of finished reports, are different
# facts about different places on different portals. They look similar today.
# They are not one thing and they are not to be folded into one.
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

# The two portals whose wording of a day is written down here. **The same words
# `reports.py` uses for a platform**, so a recipe's wording and the report it
# belongs to are compared without anything translating between them.
MEESHO_WRITES_IT = "meesho"
FLIPKART_WRITES_IT = "flipkart"

# **THE FIVE PIECES A SPELLING IS BUILT FROM, and they are the whole of what
# crosses to the extension.** A spelling is a shape with these in it; both halves
# put the day into the shape and neither carries an opinion of its own about
# noughts, month names or the order the pieces come in. That is what keeps the
# two halves from becoming two records of one fact.
#
#   {yyyy}  2026        {mm}  06        {dd}  05
#   {Mon}   Jun         {d}   5
THE_PIECES_OF_A_DAY = ("yyyy", "mm", "dd", "Mon", "Month", "d")
_A_PIECE = re.compile(r"\{(" + "|".join(THE_PIECES_OF_A_DAY) + r")\}")

# **HOW MEESHO WRITES A DAY. Six spellings, taken one for one from
# `content/meesho.js findExportDownloadByTodayDate`**, which has read that panel
# every night for months, in its own order.
#
# **HIS OWN RETURNS PAGE ON 2026-08-28** shows rows reading
# `completed_delivered_last_2_week | 25 Aug 2026, 04:49 PM | Download`, which is
# the second of these. The reference did not stop there, and neither does this.
#
# **THE LAST ONE CARRIES NO YEAR, and that is the reference's, kept knowingly.**
# It is the loosest thing in this file: `31 May` sits inside `31 May 2025` as
# well as `31 May 2026`. It stays because narrowing to a row only ever takes
# matches away -- an extra candidate cannot invent a row -- and because the
# reference met a panel that wrote a day that way.
HOW_MEESHO_WRITES_A_DAY = (
    "{yyyy}-{mm}-{dd}",       # 2026-05-31
    "{d} {Mon} {yyyy}",       # 31 May 2026   <- his own panel, 2026-08-28
    "{dd} {Mon} {yyyy}",      # 05 May 2026
    "{d} {Mon}",              # 31 May
    "{dd}/{mm}/{yyyy}",       # 31/05/2026
    "{dd}-{mm}-{yyyy}",       # 31-05-2026
)

# **HOW FLIPKART'S REPORTS CENTRE WRITES A DAY. The reference's five, plus the
# one the document recorded, and the sixth is the point.**
#
# The first five are `findReportRowDownloadBtn`'s own `buildFmts`, in its order.
# **Four of the five put the month FIRST** -- its own comment shows a real row
# reading `Jun 10 2026 To Jun 11 2026`.
#
# **`DOCS.md:1766` records a row reading `05 Jun 2026` instead: day first, with
# a nought -- and that spelling is not among the reference's five.** Two written
# records of the same portal disagree. Choosing between them is what went wrong
# on 2026-09-10, in both directions on two different nights; carrying both is
# what the reference itself does when it meets more than one. So the sixth is
# here, marked for what it is.
#
# **AND CONTAINMENT DOES NOT RESCUE IT, which is why it has to be listed.** A
# row is narrowed by the words `To 06 Jun 2026`; `To 6 Jun 2026` is not inside
# that, because the nought falls between the `To ` and the `6`.
HOW_FLIPKART_WRITES_A_DAY = (
    "{Mon} {d} {yyyy}",       # Jun 5 2026
    "{Mon} {dd} {yyyy}",      # Jun 05 2026
    "{Mon} {d}, {yyyy}",      # Jun 5, 2026
    # **WITH THE NOUGHT, read off his own returns Previous Downloads on
    # 2026-09-14**: `16:24, Sep 06, 2026`. `Sep 6, 2026` is not inside that.
    "{Mon} {dd}, {yyyy}",     # Jun 05, 2026
    "{d} {Mon} {yyyy}",       # 5 Jun 2026
    "{yyyy}-{mm}-{dd}",       # 2026-06-05
    "{dd} {Mon} {yyyy}",      # 05 Jun 2026  <- DOCS.md:1766, not in the reference's five
    # **THE FULL MONTH NAME AND NO YEAR, read off his own listings Downloads
    # History on 2026-09-11.** Its rows say `11 September, 11:10 PM` -- and not
    # one of the six spellings above matches that, so the row holding the file
    # the walk had just asked for could not be found.
    #
    # **IT IS THE LOOSEST SPELLING IN THIS FILE AND IT IS KEPT KNOWINGLY, for the
    # same reason the Meesho list keeps its own no-year one:** narrowing to a row
    # only ever takes candidates away, and an extra candidate cannot invent a
    # row. **What it costs is that `11 September` sits inside `11 September 2025`
    # as well**, so it is only ever used where the day being matched is TODAY --
    # the day a file was made -- and never to pick a day out of a history.
    "{d} {Month}",            # 11 September  <- his own Downloads History
)

# **THE MONTH NAMES IN FULL, because one portal writes them out.** Kept beside
# the short ones rather than derived from them: a name is a spelling, and a
# spelling worked out by slicing another is two records of one fact.
MONTHS_IN_FULL = ("January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December")

# Whose wording is whose. **Nothing works this out from a report's name** -- a
# name is a spelling and a spelling is not a fact (D170).
HOW_A_DAY_IS_WRITTEN = {
    MEESHO_WRITES_IT: HOW_MEESHO_WRITES_A_DAY,
    FLIPKART_WRITES_IT: HOW_FLIPKART_WRITES_A_DAY,
}


def a_day_written(shape: str, day) -> str:
    """One day put into one spelling. **No opinion of its own** -- the shape says
    the order, the noughts and the month name, and this only fills it in.

    **EVERY PIECE CARRIES ITS OWN BRACES, WHICH IS WHAT MAKES THE ORDER NOT
    MATTER**, and that is worth saying because the first version of this note
    said the opposite. `{d}` cannot be found inside `{dd}` -- the closing brace
    is in the way -- so no piece can eat another's name whichever way round they
    are filled. **The reason a check watches this is not the order: it is that
    BOTH HALVES have to recognise the same five names**, and a half that had
    never heard of `{dd}` would leave it on the page as those four characters.
    """
    pieces = {
        "yyyy": f"{day.year}",
        "mm": f"{day.month:02d}",
        "dd": f"{day.day:02d}",
        "Mon": MONTHS[day.month - 1],
        # **THE SIXTH PIECE, ADDED 2026-09-11 for Flipkart's listings history.**
        "Month": MONTHS_IN_FULL[day.month - 1],
        "d": f"{day.day}",
    }
    return _A_PIECE.sub(lambda found: pieces[found.group(1)], shape)


def the_days_in_words(whose: str, day) -> Tuple[str, ...]:
    """Every way that one portal has been met writing one day, or a refusal.

    **SEVERAL, NEVER ONE.** A row matches if it carries any of them, which is
    what the reference does on both portals. They all name the same day, so a
    longer list cannot match a different day -- only a right row that would
    otherwise have been missed over a leading nought.
    """
    shapes = HOW_A_DAY_IS_WRITTEN.get(whose)
    if shapes is None:
        raise KeyError(f"{whose!r} is not a portal whose wording of a day is written down here.")
    return tuple(a_day_written(shape, day) for shape in shapes)


def why_the_wording_is_wrong(report_id: str) -> Optional[str]:
    """A step naming another portal's wording of a day, or None.

    **A RECIPE CAN ONLY BE FILLED IN WITH ITS OWN PORTAL'S WORDING**, and this is
    the rule that says so out loud rather than leaving it to whoever writes the
    next recipe. `fk_returns` written with Meesho's wording would look perfectly
    correct here, submit perfectly correctly on the night, and then look for
    `6 Jun 2026` on a page that only ever says `06 Jun 2026`.

    **THE PLATFORM IS THE REPORT'S OWN, read off `reports.py`** -- never taken
    off the front of the report's name, which is a spelling (D170).
    """
    which = recipe(report_id)
    belongs_to = kartaan_report(report_id).platform
    for step in which.to_ask + which.to_take:
        whose = step.find.day_in_words_is if step.find is not None else ""
        if not whose:
            continue
        if whose not in HOW_A_DAY_IS_WRITTEN:
            return (f"{report_id} asks for a day written the way {whose!r} writes one, and no "
                    "wording of a day is written down for that.")
        if whose != belongs_to:
            return (f"{report_id} is a {belongs_to} report and asks for a day written the way "
                    f"{whose} writes one. A row on {belongs_to}'s own page is never written "
                    f"the way {whose} writes it.")
    return None


# ---------------------------------------------------------------- Meesho

# **EVERY MEESHO LOOKUP ASKS FOR A PRESSABLE THING RATHER THAN A CONTROL**, read
# off his own panel on 2026-08-28. Its sidebar says nothing about itself --
# "Orders" is an `h5`, "Manage Orders" a `<p>`, no role and no test id between
# them -- so asked for a control it answers nothing at all.
#
# **THIS LOSES NOTHING.** A pressable thing is a control OR something the cursor
# changes over, so every real button Meesho does have is still found. Its home
# page has twenty-three of them.
#
# Flipkart below keeps `BY_ROLE_AND_TEXT` on purpose: its dashboard carries
# thirty-two painted controls and eight kinds of role, so the stronger signal is
# there to be used, and a finding about one platform is not applied to the other.

# **REACHED BY ADDRESS, NOT BY CLICKING THE SIDEBAR.** The reference clicked the
# sidebar to look human for Akamai -- and that is exactly what the promotion
# defeats, because a click aimed at the sidebar hits the dialog. Going to the
# address is what a bookmark does, and it steps round the overlay entirely.
#
# **MEESHO DOES NOT KEEP ITS SECTIONS UNDER ONE ADDRESS, and getting that wrong
# is worth more than it sounds.** Orders live under `fulfillment`, payments under
# `payouts`, the stock file under `services`, and only the dashboard under
# `growth`. There is no single prefix.
#
# **READ LIVE ON 2026-08-28.** `…/growth/<slug>/orders` was loaded four times: once
# it drew the sidebar and nothing else, and three times it drew NOTHING AT ALL,
# still blank after forty-two seconds. **Meesho does not refuse an address it does
# not know -- it serves a page that never finishes.** The moment the same report
# was asked for at `…/fulfillment/<slug>/orders/` it drew instantly.
#
# The seller's own part is the SLUG ALONE and is never written here (D27, D30,
# D92) -- the reference holds one supplier's slug in its own source, which is
# exactly what cannot ship.
FULFILMENT = "https://supplier.meesho.com/panel/v3/new/fulfillment/{panel}"
PAYOUTS = "https://supplier.meesho.com/panel/v3/new/payouts/{panel}"
SERVICES = "https://supplier.meesho.com/panel/v3/new/services/{panel}"
# **THE SELLER'S OWN DASHBOARD**, which is where the day's views are shown and
# nowhere else. Same address the working reference starts every Meesho job from
# (`config.js` `startUrl`), which is also why it is known to be a panel page and
# not the public site -- the sign-in check depends on that.
GROWTH = "https://supplier.meesho.com/panel/v3/new/growth/{panel}"
# **WHERE THE ADS SWEEP STANDS WHILE IT ASKS.** Same address the reference uses
# (`content/meesho.js` JOB_PAGES `me_ads`), and it presses nothing on it.
ADS = "https://supplier.meesho.com/panel/v3/new/ads/{panel}"

# **EVERY MENU ITEM ON BOTH PLATFORMS IS ASKED FOR AS A PRESSABLE THING, NOT AS
# WORDS ON THE PAGE, and that is measured rather than tidy.** Read off his own
# Flipkart Reports Centre on 2026-08-28, with the request dialog open:
#
#   `Fulfilment Reports` as words: **8** matches -- refuses, for ever
#   `Fulfilment Reports` as something pressable: **1**
#   `Orders` as words: **3** -- refuses
#   `Orders` as something pressable: **1**
#
# The words appear in headings, in the list of reports already requested, and in
# the menu. Only one of them can be pressed. **A report that refuses every night
# is indistinguishable from one nobody built**, which is why this is worth being
# exact about.
#
# ---------------------------------------------------------------- Flipkart

# Flipkart is a single page that routes on the part after the hash. Deep-linking
# works and does not upset it -- unlike Meesho, it has no aggressive bot
# protection, which is why its own reports are reachable this way.
#
# **BUT IT ONLY ROUTES TO ROUTES THAT EXIST, AND A WRONG ONE FAILS SILENTLY AND
# CONVINCINGLY.** Flipkart does not refuse an address it does not know: it draws
# a complete, signed-in page carrying the whole sidebar, and quietly puts
# `#dashboard/page-not-found` in the address bar. Nothing about it looks broken
# to a walk that only asks whether the button it wants is there. **Every address
# below has been driven against his real account and seen to land where it says.**
FLIPKART = "https://seller.flipkart.com/index.html#{where}"

REPORTS_CENTRE = FLIPKART.format(where="dashboard/metrics/report-centre")
# **THE LAST THREE PIECES WERE MISSING AND THE PAGE DREW SOMETHING ELSE ENTIRELY.**
# Read off his own Flipkart on 2026-09-11, twice, with the address bar copied back
# both times:
#
#   without them   `...selectedPeriod=weekly&startDate=2026-09-04&endDate=2026-09-10
#                   &activeProductType=significant_visibility_drop`
#   with them      `...selectedPeriod=latest&startDate=2026-09-10&endDate=2026-09-10
#                   &activeProductType=ALL`
#
# **SO THE SHORT ADDRESS ASKS FOR A WEEK, AND FOR ONLY THE LISTINGS WHOSE VIEWS
# HAVE DROPPED.** Not an error, not a page-not-found -- a real, signed-in, fully
# drawn traffic report of the wrong week and a filtered slice of his catalogue.
# A file fetched from it would have been believed.
#
# **THE THREE PIECES ARE THE REFERENCE'S OWN** (`content/flipkart.js`
# `fkViewsSelectRange`, its `cleanHash`), and `DOCS.md:957` asks in bold for the
# platform selector to stay on "All".
TRAFFIC = FLIPKART.format(
    where="dashboard/growth/seller-insights?businessVertical=ALL&section=purchase_funnel"
          "&selectedPeriod=latest&activeMetric=impression&activeProductType=ALL"
)
# **THESE THREE WERE WRONG, AND THEY COST A WHOLE NIGHT (2026-09-06).** Nine of
# ten reports failed within twenty minutes of each other -- seven ads reports
# looking for "the other reports tab", claims looking for "the claims tab",
# listings looking for "the downloads menu". Three different pages, three
# different targets, one cause: **every one of these addresses redirects to
# `#dashboard/page-not-found`.** The walk arrived at a real, signed-in, fully
# drawn Flipkart page that simply was not the page it asked for, and then looked
# for a tab that was not on it.
#
# **MEASURED ON HIS OWN ACCOUNT, NOT INFERRED**, and measured twice so that the
# obvious rival explanation could be ruled out rather than argued with. The
# reference's own comment at `content/flipkart.js:492` says Flipkart "routes to
# 404 when a deep hash URL is opened in a fresh background tab (Angular auth
# hasn't initialised yet)" -- **which would have been a satisfying answer and is
# not this one.** On an already-bootstrapped tab the old addresses still went to
# not-found, and on a brand new tab the new ones did not. The addresses were
# simply stale. **The reference's comment is itself out of date, which is the
# third documentation-versus-reality drift found in it in three days.**
#
# **AND THE PART THAT IS STILL TRUE AND WORTH KEEPING FROM IT:** on a fresh tab
# the page routes immediately but its CONTENT takes between ten and twenty-five
# seconds to draw. Every `wait-for` after a `go` has to outlast that, and the
# reason it does is that the walk runs in a window of its own where Chrome does
# not throttle it.
ADS_REPORTS = FLIPKART.format(where="dashboard/ads/reports/others")
CLAIMS = FLIPKART.format(where="dashboard/payments/spf")
# **THE ALL RETURNS TAB, BY ITS OWN ADDRESS -- THE REFERENCE'S ROUTE, READ IN ITS
# CODE AND MEASURED ON HIS PANEL 2026-09-14.** `#dashboard/returnsV2` alone opens
# on `Important for Today`, and the words `All Returns` match TWO things on the
# page (a `button role=tab` and a `label`), so the tab is reached by the address
# the reference collects from (`content/flipkart.js:2812`), never by clicking it.
RETURNS = FLIPKART.format(where="dashboard/returnsV2?tab=all_returns&state=all")
LISTINGS = FLIPKART.format(where="dashboard/listings-management")


def _reports_centre(kind: str, sub_kind: str, why_it_is: str) -> Recipe:
    """One of the three Reports Centre reports: orders, returns, payments.

    **THEY ARE IDENTICAL BUT FOR TWO DROPDOWN VALUES**, so they are built from one
    place. Three near-copies is three chances for one of them to drift, and the
    reference had exactly that -- a fix applied to orders and not to payments.
    """
    return Recipe(
        ready_in_minutes=30,
        to_ask=(
            Step(GO, address=REPORTS_CENTRE, why=f"opening the reports centre for {why_it_is}"),
            # **A `span`, NOT A CONTROL. MEASURED ON HIS OWN REPORTS CENTRE,
            # 2026-09-11.** `Request New Report` carries no role and no control
            # tag; the only thing marking it is `cursor: pointer`. Asked for as a
            # control the page answers nothing, so **all three of these reports
            # would have stopped one step in, every night** -- which is the same
            # fault that cost the traffic report its first run the same day.
            Step(WAIT_FOR, find=Find(BY_PRESSABLE_TEXT, "Request New Report", called="the request button"),
                 patience=60, why="waiting for the reports centre to finish drawing"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Request New Report", called="the request button"),
                 why="starting a new request"),
            # **THE KIND REALLY IS A BUTTON** -- measured, and the only one of
            # these four that was already right. The five on offer are
            # `Fulfilment Reports`, `Invoices`, `Listings reports`,
            # `Payment Reports` and `Tax Reports`.
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, kind), why=f"choosing {kind}"),
            # **AND THE SUB-KIND IS NOT A CONTROL AT ALL. THIS STEP PRESSED A ROW
            # HEADING.** Measured in the open dialog, row by row: each row is a
            # `span` naming the report and a real `button` reading
            # `REQUEST REPORT` beside it. `Orders` is a `span` with
            # `cursor: auto` -- pressing it does nothing whatever, and nothing on
            # the door's list could even find it.
            #
            #   SPAN "DBD Breached Shipments Report"   BUTTON "REQUEST REPORT"
            #   SPAN "Orders"                          BUTTON "REQUEST REPORT"
            #   SPAN "Pickup Report"                   BUTTON "REQUEST REPORT"
            #   SPAN "Returns"                         BUTTON "REQUEST REPORT"
            #   SPAN "Seller Cancelled Shipments..."   BUTTON "REQUEST REPORT"
            #
            # **FIVE BUTTONS READING THE SAME WORDS, AND ONLY THE ROW TELLS THEM
            # APART.** So the words name the row and the button beside them is
            # what is pressed -- which is what the reference has done for months
            # (`content/flipkart.js` StepC).
            #
            # **AND `REQUEST REPORT` IS SAID AS WHAT ELSE THAT ROW SAYS, BECAUSE
            # THE SAME WORD IS ON THE PAGE TWICE.** `Orders` is also a leaf in
            # the list of reports already requested sitting behind the dialog,
            # and that row walks up to a Download button -- so without this the
            # step finds two and refuses. That row does not say
            # `REQUEST REPORT`; this one does.
            Step(CLICK, find=Find(BY_THE_BUTTON_BESIDE, sub_kind,
                                  also_saying="REQUEST REPORT",
                                  called=f"the request button on the {sub_kind} row"),
                 patience=30, why=f"asking for {sub_kind}"),
            # **THERE IS NO CALENDAR ON THIS PAGE UNTIL TWO THINGS ARE PRESSED,
            # and without them the step below has nothing whatever to press days
            # on.** This went straight from choosing the report to picking a
            # range, and picking a range on a page with no calendar and no date
            # boxes can only ever answer "nought were found, so no dates were
            # set" -- which reads as the portal having changed and is nothing of
            # the kind.
            #
            # **THE REFERENCE'S OWN TWO STEPS, carried across as they are**
            # (`content/flipkart.js` StepD-0 and StepD, which have opened this
            # calendar every night for months): the sub-page shows a **Select
            # Date Range** box with the calendar hidden behind it, and pressing
            # that box offers a **Custom** chip. Only the chip draws the days.
            #
            # **AND THE WAIT FOR THE MONTH HEADING IS THE NEXT STEP'S OWN.** The
            # reference polls for the heading after the chip; here `pick-range`
            # already keeps looking for the whole of its patience before it
            # answers that no calendar was showing, so a third step here would be
            # a second way of saying one thing.
            #
            # **AND THE WORDS ARE A LABEL. THE BOX IS BESIDE THEM.** This pressed
            # the words themselves, which was carried over from Meesho's orders
            # step where Meesho really does have a pressable box. On Flipkart it
            # could never have worked: **Select Date Range** is a plain leaf with
            # no control tag, no role and no pointer cursor, so nothing pressable
            # matches it -- and the box beside it does not carry those words
            # either, because what an input carries is its value, which here is
            # the range currently showing (`DOCS.md:1803`). The reference has
            # never pressed the label: it finds the leaf, walks up as far as five
            # ancestors and presses the input, calendar icon or date value beside
            # it. That is what `BY_THE_CONTROL_BESIDE` is.
            Step(CLICK, find=Find(BY_THE_CONTROL_BESIDE, "Select Date Range",
                                  called="the date range box"),
                 patience=30,
                 why="opening the date range box, which is what the calendar is hidden behind"),
            # **THE DATE BOX IS PRESSED AGAIN WHILE THE CHIP IS WAITED FOR,
            # BECAUSE THE BOX TOGGLES.** The reference re-presses it on every
            # third look, eight looks a second apart. It was dropped when this
            # step was carried across, with no reason given -- and dropped, a
            # press that arrived while the sub-page was still drawing leaves this
            # step waiting out its whole patience at a page that will never
            # change, then reporting the chip as missing.
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Custom", called="the custom range chip"),
                 patience=30,
                 press_again=PressAgain(
                     by=Find(BY_THE_CONTROL_BESIDE, "Select Date Range",
                             called="the date range box"),
                     after=3, times=4),
                 why="choosing a custom range, which is what draws the days"),
            # **TWO DAYS, NOT ONE.** Flipkart requires the start to be strictly
            # before the end; a single-day range is refused by a Submit that does
            # nothing at all, with no message.
            #
            # **AND A DAY THIS ONE CALENDAR HAS SWITCHED OFF SAYS SO IN THE
            # CURSOR AND IN NOTHING ELSE.** Flipkart disables a day two different
            # ways and only one of them can be read any other way -- see the note
            # on the step in `browser.py`. No other calendar here is asked.
            #
            # **AND THE CHIP IS PRESSED AGAIN WHILE THE CALENDAR IS WAITED FOR,
            # BECAUSE THE CHIP TOGGLES TOO.** The reference re-presses it once,
            # part-way through its wait for the month heading, "in case it
            # toggled off". Dropped with the step above, and the symptom is the
            # same: a quiet wait, then no calendar.
            Step(PICK_RANGE, range_days=2, patience=30,
                 switched_off_days_change_the_cursor=True,
                 press_again=PressAgain(
                     by=Find(BY_PRESSABLE_TEXT, "Custom", called="the custom range chip"),
                     after=4, times=1),
                 why="setting the two-day range Flipkart insists on"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Submit"), why="submitting the request"),
            # **THE BANNER IS WAITED FOR, and its absence is a real failure.** The
            # reference read a submitted report as failed because the banner had
            # already faded on a throttled tab, and then re-submitted three times.
            # **AND IF THE BANNER CAME AND WENT, THE REQUEST'S OWN ROW COUNTS -- HIS
            # RULING, 2026-09-14.** The reference falls back to the Requested list
            # for exactly this (`content/flipkart.js:1382-1390`): a toast can vanish
            # between two looks on a slowed tab, and the row does not.
            Step(WAIT_FOR, find=Find(BY_TEXT, "successfully", exact=False, called="the confirmation"),
                 or_find=Find(BY_TEXT, sub_kind, near="To {day_in_words}",
                              day_in_words_is=FLIPKART_WRITES_IT,
                              day_in_words_of=THE_DAY_IT_IS_ABOUT,
                              called=f"the {why_it_is} request in the requested list"),
                 patience=45, why="confirming Flipkart took the request"),
        ),
        to_take=(
            Step(GO, address=REPORTS_CENTRE, why=f"coming back for {why_it_is}"),
            Step(WAIT_FOR, find=Find(BY_ROLE_AND_TEXT, "Requested", called="the requested tab"),
                 patience=60, why="waiting for the reports centre to finish drawing"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Requested", called="the requested tab"),
                 why="opening the list of requested reports"),
            # **MATCHED BY THE END DATE OF ITS RANGE -- AND UNTIL NOW THIS
            # COMMENT SAID SO AND THE TWO STEPS UNDER IT DID NOTHING OF THE
            # KIND.** They looked for the word "Generated" anywhere on the page
            # and for a "Download" anywhere on the page. **The Requested list
            # holds every report the seller has ever asked for**, so on any
            # normal night that finds several Downloads, refuses as ambiguous,
            # and fetches nothing -- and on the night it finds exactly one, that
            # one is whichever report happened to be alone, which is worse.
            #
            # **WHY THE END DATE AND NOT THE START.** A row reads
            # `Fulfilment Reports  Orders  05 Jun 2026 To 06 Jun 2026
            # Generated`. The range asked for is [the day before, the day], so
            # the END is the day actually being fetched and is the only part of
            # the row that names it. The reference matches the date after
            # `" To "` for exactly this reason (`findReportRowDownloadBtn`), and
            # the word `To` is carried across with it -- without it, last
            # night's row, whose START is today's day, matches just as well.
            #
            # **AND THE WAIT IS NARROWED TOO, not only the taking.** Waiting for
            # any "Generated" anywhere and then looking for this day's Download
            # is a wait that passes on somebody else's row and hands the next
            # step a report that is still being built. The reference asks both
            # questions of the same row, in one pass.
            #
            # **AND IT IS WRITTEN THE WAY FLIPKART WRITES A DAY, WHICH IS NOT THE
            # WAY MEESHO DOES.** The row says `05 Jun 2026`, with the leading
            # nought; Meesho's own panel says `1 Sep 2026` without one. Filled in
            # Meesho's way, this looks for `5 Jun 2026` on a row that reads
            # `05 Jun 2026` -- nothing matches, for the first nine days of every
            # month, and it reads as the portal having changed.
            # **AND THE DAY IS THE ONE THE DATA IS ABOUT, which on this portal is
            # also the end of the range.** Said out loud because the other portal
            # answers it the other way: Meesho's panel names a row by the day the
            # export was MADE. The range asked for is [the day before, the day],
            # so the end of it IS the data date, and the reference passes
            # yesterday to its row matcher.
            # **AND BY THE REPORT'S OWN KIND AS WELL AS BY THE DAY, WHICH IS
            # THE ONE THING THE DAY CANNOT DO HERE.** All three Reports Centre
            # reports are asked for on the same night over the same range, so on
            # any ordinary morning the Requested list holds
            # `Fulfilment Reports Orders ... To 06 Jun 2026`,
            # `Fulfilment Reports Returns ... To 06 Jun 2026` and
            # `Payment Reports Settled Transactions ... To 06 Jun 2026` --
            # **three rows, one end date, and nothing between them but the
            # kind.** Narrowed by the day alone, this matches all three, the step
            # that takes the newest of several takes whichever is topmost, and
            # **the payments file lands under the orders name and is read into
            # the seller's books as sales.** That is the nine-day payments
            # outage again, arriving by the other door.
            #
            # The reference asks the kind FIRST and the date second, of the same
            # row, in one pass -- `content/flipkart.js` `findReportRowDownloadBtn`
            # opens with `if (!rowLow.includes(subLow)) continue;`, and the
            # sub-type it tests is the same wording asked for in the request
            # (`REPORTS_CENTRE_CFG`: `Orders`, `Settled Transactions`). So the
            # words used here are `sub_kind` itself, not a second spelling of it.
            #
            # **ON THE WAIT AS WELL AS ON THE TAKING.** A wait that passes on
            # somebody else's finished row hands the next step a report that is
            # still being built -- the same reason the day is asked of both.
            Step(WAIT_FOR, find=Find(BY_TEXT, "Generated", exact=False,
                                     near="To {day_in_words}", called="a finished report",
                                     also_saying=sub_kind,
                                     day_in_words_is=FLIPKART_WRITES_IT,
                                     day_in_words_of=THE_DAY_IT_IS_ABOUT),
                 patience=120, why=f"looking for a finished {why_it_is} report for the day being fetched"),
            # **THE ROW'S DOWNLOAD IS A REAL `<button>` WHOSE WORDS ARE
            # `downloadDownload`, NOT `Download`. MEASURED ON HIS OWN REPORTS
            # CENTRE, 2026-09-14,** on the row `Orders | Sep 12 2026 To Sep 13
            # 2026 | Generated`: an icon whose own text is `download`, then the
            # label. Asked for the exact words, nothing on the page matched, and
            # the collect failed with the file sitting there -- the same shape as
            # the traffic report's `Request Listings Reportdownload`. **Holding
            # the word is enough here, because the row is already pinned** by the
            # day and by the report's own kind, and the reference matches a
            # download control in the row by the word alone.
            Step(TAKE_FILE, find=Find(BY_ROLE_AND_TEXT, "Download", exact=False, near="To {day_in_words}",
                                      also_saying=sub_kind,
                                      day_in_words_is=FLIPKART_WRITES_IT,
                                      day_in_words_of=THE_DAY_IT_IS_ABOUT),
                 patience=90,
                 why=f"taking the finished {why_it_is} file for the day being fetched"),
        ),
    )


def _ads(report_type: str) -> Recipe:
    """One of the seven ad reports.

    **SEVEN REPORTS, ONE PAGE, ONE DROPDOWN VALUE BETWEEN THEM.** Built from one
    place for the same reason the Reports Centre three are: seven near-copies is
    seven chances to drift.
    """
    return Recipe(
        to_take=(
            Step(GO, address=ADS_REPORTS, why=f"opening the ads reports page for {report_type}"),
            # **A REAL BUTTON WITH `role="tab"`, measured 2026-09-11 -- the one
            # thing on this page that was already asked for correctly.** The same
            # words also appear as a `div` heading with `cursor: auto`, so asking
            # for a control finds exactly one and asking for pressable words
            # would too.
            Step(WAIT_FOR, find=Find(BY_ROLE_AND_TEXT, "Other Reports", called="the other reports tab"),
                 patience=60, why="waiting for the ads page to finish drawing"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Other Reports", called="the other reports tab"),
                 why="opening the other reports tab"),
            # **THE STEP THAT WAS MISSING, AND WITHOUT IT CHOOSING A REPORT TYPE
            # COULD NEVER HAVE WORKED.** The list of report types is not on the
            # page until its control is opened, so the step below stood in front
            # of a page that did not carry those words and answered that nothing
            # matched.
            #
            # **`Report Type` IS A `div` LABEL WITH `cursor: auto` AND THE
            # CONTROL IS A SIBLING** -- and that sibling is a real `input`, so the
            # door's first choice reaches it with nothing new needed.
            #
            # **AND `Ad Product` IS NOT SET AT ALL, WHICH THE REFERENCE DOES SET.**
            # Measured with it untouched: the Report Type list already offers all
            # seven. **And its step could not have been copied anyway** -- `PLA`
            # is also a `role="tab"` button at the top of this page, so asking for
            # it finds two and refuses.
            Step(CLICK, find=Find(BY_THE_CONTROL_BESIDE, "Report Type",
                                  called="the report type box"),
                 patience=30, why="opening the list of report types"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, report_type), why=f"choosing {report_type}"),
            # **AND THE DAY CANNOT BE SET UNTIL ITS OWN CONTROL IS OPENED EITHER.**
            # `Date` is a `div` label whose ONLY sibling is a
            # `div role="presentation"` with a pointer cursor, reading the range
            # currently showing (`This Week : 06-Sep-26 - 11-Sep-26`). **No input
            # and no calendar icon**, which is why the door needed the third way
            # of reaching what a label names.
            Step(CLICK, find=Find(BY_THE_CONTROL_BESIDE, "Date", called="the date box"),
                 patience=30, why="opening the date box, which is what the calendar is behind"),
            # **THE PRESETS ARE NOT USED, AND THAT IS DELIBERATE.** This page
            # offers `Yesterday`, which is one press and is what the reference
            # takes. **But the day this run is fetching is not always yesterday**
            # -- a day that was missed is fetched later, and `Yesterday` would
            # then fetch the wrong one and file it under the right name. The
            # calendar is always the day asked for.
            Step(PICK_RANGE, patience=30, why="setting the day to fetch"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Done", called="the accept button"),
                 patience=30, why="accepting the day, which is what draws the download control"),
            # **`Download` IS NOT ON THIS PAGE UNTIL A REPORT TYPE AND A DAY ARE
            # BOTH CHOSEN**, measured -- so this step could not have run even if
            # everything above it had.
            Step(TAKE_FILE, find=Find(BY_PRESSABLE_TEXT, "Download"), patience=90,
                 why=f"taking the {report_type} file"),
        ),
    )


def _ads_overall() -> Recipe:
    """The overall performance report: the ads page, then once per campaign.

    **ITS DOWNLOAD STAYS SWITCHED OFF UNTIL A CAMPAIGN IS CHOSEN**, measured on his
    own Flipkart on 2026-09-14: choosing the report adds a `Campaign ID` box whose
    placeholder reads `Search by Campaign name or ID`. **The reference's route,
    read in its code** (`content/flipkart.js` `_handleFkAdsOverall`): the day is set
    first, then for each campaign the id is typed, its suggestion pressed, `Ad Group`
    waited for, and Download pressed -- one file per campaign.
    """
    everything_but_the_download = _ads("Overall Performance Report").to_take[:-1]
    return Recipe(
        to_take=everything_but_the_download + (
            # **THE REFERENCE'S ORDER, COPIED AS IT IS -- HIS RULING, 2026-09-15.**
            # `_handleFkAdsOverall`: click the box, then type the id, then press the
            # smallest thing holding the id that is not the box itself.
            Step(CLICK, find=Find(BY_THE_CONTROL_BESIDE, "Campaign ID", called="the campaign id box"),
                 for_each_campaign=True, patience=30,
                 why="pressing the campaign id box first, as the reference does"),
            Step(TYPE_IN, find=Find(BY_THE_CONTROL_BESIDE, "Campaign ID", called="the campaign id box"),
                 words="{campaign}", for_each_campaign=True, patience=30,
                 why="typing the campaign id into the campaign search box"),
            # **PRESSABLE, SO THE BOX IS NOT COUNTED -- MEASURED 2026-09-15.** Asked as
            # plain words, the typed id in the box matched as well as the suggestion,
            # and the step refused on two. A box is never a pressable match, which is
            # the reference's own "not the input" rule.
            Step(WAIT_FOR, find=Find(BY_PRESSABLE_TEXT, "{campaign}", exact=False,
                                     called="the campaign's suggestion"),
                 for_each_campaign=True, patience=30,
                 why="waiting for Flipkart to suggest that campaign"),
            # **PRESSED LIKE A MOUSE, MEASURED 2026-09-15.** The suggestion is a
            # `div.item` holding the name and a `div.subTitle` reading `ID <id>`,
            # both `cursor: pointer`. The walk found the subtitle and clicked it, and
            # the list stayed open; the same element given button down, button up and
            # click drew `Ad Group` and switched Download on.
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "{campaign}", exact=False,
                                  called="the campaign's suggestion"),
                 for_each_campaign=True, press_like_a_mouse=True,
                 why="pressing that campaign's suggestion"),
            # **THE LABEL READS `Ad Group ID (optional)`, MEASURED ON HIS PAGE
            # 2026-09-15** with a campaign chosen -- the reference's loose "ad group"
            # hid the rest of it, and an exact `Ad Group` could never have matched.
            Step(WAIT_FOR, find=Find(BY_TEXT, "Ad Group ID (optional)", called="the ad group box"),
                 for_each_campaign=True, patience=30,
                 why="waiting for the campaign to be chosen, which draws the ad group box"),
            Step(TAKE_FILE, find=Find(BY_PRESSABLE_TEXT, "Download"), for_each_campaign=True,
                 patience=90, why="taking this campaign's overall performance file"),
        ),
        campaigns_from=CampaignsFrom("fk_ads_daily", id_column="Campaign ID", day_column="Date"),
    )


RECIPES: Dict[str, Recipe] = {
    # ---- Meesho
    "me_orders": Recipe(
        to_take=(
            Step(GO, address=FULFILMENT + "/orders/", why="opening the orders page"),
            Step(WAIT_FOR, find=Find(BY_PRESSABLE_TEXT, "Download Orders Data", called="the download menu"),
                 patience=45, why="waiting for the orders page to finish drawing"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Download Orders Data", called="the download menu"),
                 why="opening the download menu"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Select Date Range"), why="choosing which days to export"),
            Step(PICK_RANGE, patience=20, why="setting the day to export"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Export data"), why="asking for the export"),
            # **THIRTY-FIVE SECONDS, AND THE RELOAD BELOW IS WORTHLESS WITHOUT
            # THEM.** The file is built on Meesho's own servers and this page
            # shows nothing at all while it happens -- so there is nothing to
            # wait FOR, only time to wait. Reloaded straight away, the list is
            # drawn before the file exists and the file is simply not in it;
            # **the 300 seconds of patience on the last step cannot recover
            # that**, because a drawn list does not gain rows while it is looked
            # at.
            #
            # **THE NUMBER IS THE REFERENCE'S OWN** (`content/meesho.js:947`),
            # which has waited exactly this long every night for months and
            # writes down why: the file is usually ready in under ten seconds and
            # thirty-five is safe.
            Step(WAIT, patience=35,
                 why="waiting for Meesho to finish building the file, because the list below is "
                     "drawn as the page loads and a page loaded too early is loaded without it"),
            # **THE PAGE HAS TO BE LOADED AGAIN, and this is the whole of why the
            # first version of this recipe could never have worked.** Meesho
            # builds the file almost instantly, and **it does not appear in the
            # exported files list until the page is loaded again -- reopening the
            # menu is not enough.** Written down in the reference's own source
            # after it was paid for. Waiting three hundred seconds for a list
            # that will never change is what this replaces.
            Step(GO, address=FULFILMENT + "/orders/", patience=60,
                 why="loading the page again, which is the only way the finished file appears"),
            Step(WAIT_FOR, find=Find(BY_PRESSABLE_TEXT, "Download Orders Data", called="the download menu"),
                 patience=60, why="waiting for the orders page to finish drawing again"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Download Orders Data", called="the download menu"),
                 why="opening the download menu again, where the finished file now is"),
            # **THE DOWNLOAD ON THE ROW FOR THE DAY THIS IS ABOUT.** The menu
            # lists every export ever made -- ten on his own page -- each row
            # reading `2026-08-23_2026-08-23_2026-08-28 | 25 Aug 2026, 04:47 PM |
            # Download`. **The first part is the day the file is ABOUT**, which is
            # the one worth naming: it still finds the right file when an older
            # day is being fetched, which is exactly when it matters.
            # **AND IF IT IS NOT THERE YET, THE MENU IS SHUT AND OPENED AGAIN.**
            # This used to wait 300 seconds on an open menu. **The list of
            # finished exports is drawn AS the menu opens**, so an open menu
            # shows whatever was ready at the moment it opened and never changes
            # -- five minutes of looking at it is five minutes of looking at the
            # same picture. The reference closes it and opens it again, six times,
            # thirty seconds apart (`content/meesho.js:860-878`), and that is
            # carried across as it is rather than derived again.
            Step(TAKE_FILE, find=Find(BY_PRESSABLE_TEXT, "Download", near="{day}"),
                 patience=30,
                 look_again=LookAgain(
                     by=Find(BY_PRESSABLE_TEXT, "Download Orders Data", called="the download menu"),
                     times=6, after=30),
                 why="taking the finished file"),
        ),
    ),
    "me_catalog": Recipe(
        to_take=(
            Step(GO, address=SERVICES + "/inventory", why="opening the inventory page"),
            Step(WAIT_FOR, find=Find(BY_PRESSABLE_TEXT, "Bulk Stock Update", called="the bulk stock button"),
                 patience=45, why="waiting for the inventory page to finish drawing"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Bulk Stock Update", called="the bulk stock button"),
                 why="opening the bulk stock panel"),
            # **TWO AND A HALF SECONDS, ROUNDED UP TO THE WHOLE ONE THIS STEP
            # COUNTS IN, AND IT IS WHAT THIS RECIPE HAS BEEN MISSING ALL ALONG.**
            #
            # Run against his own live panel on 2026-09-11 this recipe said
            # **"Download is on the page but switched off, so nothing was
            # clicked"** -- so the panel HAD opened and the right button HAD been
            # found. Meesho draws that button switched off and switches it on a
            # moment later, and the step below looks the instant the panel
            # appears: a lookup answers as soon as one thing matches, a quarter
            # of a second in, and a switched-off button matches. Waiting longer
            # on the lookup cannot help, because it has already found what it was
            # asked for.
            #
            # **THE REFERENCE NEVER MEETS THIS, AND THE NUMBER IS ITS OWN**
            # (`content/meesho.js handleCatalog`: `clickAndWait(bulkBtn, 2500)`).
            # It waits two and a half seconds after opening the panel before it
            # so much as looks -- by which time the button is on -- and it never
            # asks whether a button is switched off at all. So the fix is the
            # wait it already does, not a different way of naming the button.
            Step(WAIT, patience=3,
                 why="letting the bulk stock panel switch its download button on, because it "
                     "is drawn switched off and a switched-off button is not clicked"),
            # **MEASURED ON HIS OWN INVENTORY PAGE, 2026-08-28.** This used to
            # look for the word "Download" loosely, anywhere: that finds TWO --
            # the button, and the line of writing above it that reads "Download
            # file with existing stock". Two matches refuse, so the stock file
            # could never have been fetched. Asked for as the whole word on
            # something pressable, it finds exactly one.
            Step(TAKE_FILE, find=Find(BY_PRESSABLE_TEXT, "Download"), patience=60,
                 why="taking the stock file"),
        ),
    ),
    "me_returns": Recipe(
        to_take=(
            # **THE TAB IS PART OF THE ADDRESS.** Returns opens on a tab, and the one
            # carrying what has actually come back is named in the address itself.
            Step(GO, address=FULFILMENT + "/returns/returnTracking-completed_delivered",
                 why="opening the returns page"),
            Step(WAIT_FOR, find=Find(BY_PRESSABLE_TEXT, "Return Tracking", called="the return tracking tab"),
                 patience=45, why="waiting for the returns page to finish drawing"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Return Tracking", called="the return tracking tab"),
                 why="opening return tracking"),
            # **AND THEN DELIVERED, WHICH THE STEP ABOVE HAS JUST THROWN AWAY.**
            #
            # **MEASURED ON HIS OWN SIGNED-IN PANEL, 2026-09-11.** The address at
            # the top of this recipe lands on
            # `returnTracking-completed_delivered`, which is the right list.
            # **Pressing the Return Tracking tab moves the page to
            # `returnTracking-intransit`** -- the tab's own default sub-list --
            # so the recipe navigated away from the only list it wanted, and the
            # panel it opened next belonged to returns that have not come back
            # yet. **That is not a failure, it is the wrong file under the right
            # name**, which is the quiet kind.
            #
            # **THE DOCUMENT SAID SO ALL ALONG AND NOBODY DID IT.**
            # `D:
            # the reference's own `DOCS.md:498-506` lists six numbered steps and
            # the fourth is *"Click 'Delivered' filter (shows completed returns,
            # not in-transit)"*. The reference's own code does it two lines after
            # the tab click (`content/meesho.js:1032-1034`). **This recipe had
            # steps 1, 3, 5, 6 and 7 and was missing step 4.**
            #
            # **`Delivered` ALONE, AND IT IS EXACT ON PURPOSE.** The sub-tabs read
            # `In transit`, `Out for Delivery`, `Delivered`, `Lost`,
            # `No Return No Charge`, `New`, `Disposed` -- read off the page on
            # 2026-09-11. A loose match would take `Out for Delivery` as well.
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Delivered", called="the delivered list"),
                 why="going back to the returns that have actually come back"),
            # **THERE IS NO "EXPORT" BUTTON ON THIS PAGE, read live 2026-08-28.**
            # The way in is a control whose whole label is a COUNT -- it reads
            # "0/0 files ready" and changes as exports are made -- so it is the
            # one place a loose match is not a shortcut but the only honest way
            # to name a thing. It opens a panel headed "Download Table Data".
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "files ready", exact=False,
                                  called="the exported files panel"),
                 why="opening the panel that exports and lists the files"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Export Data"), why="asking for the export"),
            # **THE DOWNLOAD ON TODAY'S ROW, and nobody else's.** The panel
            # lists every export ever made -- ten on his own page today -- each
            # row reading `completed_delivered_last_2_week | 25 Aug 2026, 04:49
            # PM | Download`. Looking for "Download" alone finds ten and refuses.
            # The day is what tells them apart.
            # **NAMED BY THE DAY IT WAS MADE, because that is all a returns row
            # carries.** Its rows read `completed_delivered_last_2_week | 25 Aug
            # 2026, 04:49 PM | Download` -- no data date anywhere, since a returns
            # export is always the last two weeks. So the words are the platform's
            # own wording of the day rather than the day itself.
            # **AND MEESHO'S WORDING IS NAMED, WHICH IT WAS NOT UNTIL NOW.**
            # Nothing anywhere filled this placeholder, so the row was looked for
            # as `2026-08-25` -- a form that appears on no row of that panel --
            # and `me_returns` has been broken this way since the day it was
            # written. Meesho writes `25 Aug 2026`, with no leading nought.
            # **AND IT IS THE DAY THE EXPORT WAS MADE, WHICH IS TODAY.** The row
            # carries the moment the file was built and nothing else, so filled
            # with the day being fetched it asks for yesterday's date on a row
            # stamped with today's -- which is what the second fix on 2026-09-10
            # left in place. `content/meesho.js:1055` takes today for the row and
            # yesterday for the file name, two lines apart, on purpose.
            # **AND IF TODAY'S ROW IS NOT THERE YET, THE PANEL IS SHUT AND OPENED
            # AGAIN -- WHICH IS WHY THIS FAILED ON HIS OWN PANEL ON 2026-09-11
            # WITH "could not find Download. It is not on the page at all".**
            # The export had been asked for; the file was not in the list. This
            # step then waited a hundred and twenty seconds at an OPEN panel --
            # **and Meesho draws that list AS the panel opens**, so those two
            # minutes were two minutes of looking at the same picture, exactly as
            # `me_orders` above says of its own menu. Nought matching rows, and
            # the failure reads as a portal that has changed.
            #
            # **THE REFERENCE HAS DONE THE SHUTTING AND REOPENING EVERY NIGHT FOR
            # MONTHS** (`content/meesho.js handleReturns`, the poll loop at
            # 1053-1081): `document.body.click()` to shut it, thirty seconds
            # shut, then the `\d+/\d+ files ready` control looked up afresh and
            # pressed once. **Nine rounds, because the reference's own bound is
            # five minutes at thirty seconds apart** -- it is a deadline rather
            # than a count, and five minutes of thirty-second sleeps is nine of
            # them. Orders is written as six because the reference writes six
            # there in so many words; the two numbers are different because the
            # reference's two loops are different, and folding them into one
            # would be inventing a third.
            #
            # **AND THE PATIENCE COMES DOWN FROM 120 TO 30, WHICH IS NOT TIDYING.**
            # Each round may burn the patience twice over, so nine rounds at 120
            # is a worst case of forty-seven minutes -- **past the twenty-five
            # `doors.ARMED_FOR_MS` believes a walk for**, which would have it
            # swept up as "stopped part way through and never said why". Thirty
            # is the number the same step in `me_orders` carries.
            Step(TAKE_FILE, find=Find(BY_PRESSABLE_TEXT, "Download", near="{day_in_words}",
                                      day_in_words_is=MEESHO_WRITES_IT,
                                      day_in_words_of=THE_DAY_IT_WAS_MADE),
                 patience=30,
                 look_again=LookAgain(
                     by=Find(BY_PRESSABLE_TEXT, "files ready", exact=False,
                             called="the exported files panel"),
                     times=9, after=30),
                 why="taking the finished file"),
        ),
    ),
    "me_payments": Recipe(
        to_take=(
            Step(GO, address=PAYOUTS + "/payments", why="opening the payments page"),
            # **THE NINE-DAY OUTAGE LIVES HERE.** A chart legend on this very page
            # reads "Payments to Date", exactly like the menu item, and sits
            # earlier in the page. Matched exactly, and two matches refuse.
            # **ASKED FOR AS WORDS ON THE PAGE, NOT AS SOMETHING PRESSABLE, AND
            # THAT IS THE MEASURED FIX OF 2026-09-11.** Run against his own live
            # panel, this step said "could not find the download menu. It is not
            # on the page at all" -- after forty-five seconds, with nothing
            # covering the page, on a page that has this control on it.
            #
            # **THE REFERENCE DOES NOT ASK FOR ANYTHING PRESSABLE HERE, AND SAYS
            # WHY IN ITS OWN SOURCE** (`content/meesho.js handlePayments`): "The
            # element is a `<P class="dropdown_la">` -- not a `<button>` or
            # role="button"." It looks through `p, button, [role="button"]` for
            # the whole word, and a bare `<p>` passes. **Kartaan's `pressable`
            # asks for a control OR the cursor changing over it, and this `<p>` is
            # neither** -- Meesho styles the cursor on some of its own panels and
            # not on others, which is also why the identically-shaped claims
            # opener two recipes down WAS found the same morning. Payments lives
            # under `payouts` and claims under `fulfillment`: two sub-sites, two
            # stylesheets, and this product had been treating one measurement as
            # covering both.
            #
            # **STILL THE WHOLE WORD, WHICH IS THE HALF THAT MATTERS.** The
            # nine-day outage was a loose match, not a pressable one. Nothing
            # here is loosened.
            Step(WAIT_FOR, find=Find(BY_TEXT, "Download", called="the download menu"),
                 patience=45, why="waiting for the payments page to finish drawing"),
            Step(CLICK, find=Find(BY_TEXT, "Download", called="the download menu"),
                 why="opening the download menu"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Payments to Date"), why="choosing the payments export"),
            # **THE DAYS ARE ASKED FOR EVEN THOUGH MEESHO IGNORES THEM.** Its
            # payments export always hands back the current settlement batch
            # whatever range is given -- proven by reading the file after three
            # wrongly-dated duplicates were written believing otherwise -- but the
            # page will not hand anything over until a range has been chosen.
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Custom Date Range"), why="opening the date range"),
            Step(PICK_RANGE, patience=30, why="setting the day, which Meesho then ignores"),
            # **TWO THINGS ARE CALLED "Download" BY THE TIME THIS STEP RUNS, AND
            # BOTH ARE PRESSABLE. MEASURED ON HIS OWN PANEL, 2026-09-11**, with the
            # modal open exactly as this step meets it:
            #
            #   DIV role="button" tabindex="0"   the opener, top right, in the HEADER
            #   BUTTON type="button"             the one inside the export modal
            #
            # The opener never goes away when the modal opens. **ASKING FOR A
            # CONTROL DOES NOT SEPARATE THEM EITHER, AND THAT WAS TRIED FIRST:**
            # the first reading saw only the opener's inner `<span>`, which is not
            # a control, and missed the `div` wrapping it that carries the role. A
            # second run said the same thing as the first -- *"2 things match
            # 'Download'"* -- which is what sent the measurement back to the page.
            # `role="button"` is exactly how a page declares a div to be a
            # control, so no test of control-ness can tell these two apart.
            #
            # **THIS IS THE REFERENCE'S OWN ANSWER, NOT ONE DERIVED FROM IT**
            # (`content/meesho.js handlePayments`): for the final button it
            # searches `querySelectorAll('button')` and nothing else, while for
            # the opener two steps above it searches `p, button, [role="button"]`.
            # It tells the two apart by the same thing this line does.
            #
            # **AND IT IS NARROWER THAN WHAT IT REPLACES, NOT LOOSER.** Everything
            # a control finds, pressable found too; this only takes away the
            # things that merely look pressable. It cannot reach a row it could
            # not reach before.
            Step(TAKE_FILE, find=Find(BY_A_REAL_BUTTON, "Download"), patience=120,
                 why="taking the finished file"),
        ),
    ),
    # **THE ADS SWEEP: NOTHING IS PRESSED AND NO FILE IS OFFERED.** Meesho's ads
    # figures are not an export at all -- they come from two of its own addresses,
    # called from inside the seller's signed-in page. `extension/ads.js` carries
    # what those addresses are and what their fields are called; this recipe
    # carries only where to stand while asking.
    #
    # **WHY IT STANDS ON THE ADS PAGE AT ALL, since it presses nothing.** Those
    # addresses answer to the session the page carries. Asked from anywhere else
    # they answer to nobody. The reference stands on the same page for the same
    # reason, and this is also what makes the sign-in check in front of every step
    # mean something here.
    #
    # **THE PATIENCE IS THE WHOLE SWEEP, and it is the largest in the book.**
    # Every campaign is one call, paced like a person so a portal does not read
    # the run as a machine -- so the time it takes is the seller's own number of
    # live campaigns, not a fixed cost. `doors.test.js` holds the total against
    # how long a walk is believed for.
    "me_ads": Recipe(
        to_take=(
            Step(GO, address=ADS + "/advertisement?tab=ALL", patience=60,
                 why="opening the ads page"),
            Step(SWEEP_THE_ADS, patience=600,
                 why="asking Meesho for every campaign that is running"),
        ),
    ),
    # **THE ONE REPORT THAT IS NOT A FILE ANYWHERE, and until 2026-09-11 this door
    # could not reach it at all.** Meesho shows the day's views and orders on two
    # cards on the seller's own dashboard and sells no export of them short of a
    # paid subscription. There is no button to press. So the figures are read off
    # the page and added to a running list -- his decision, put to him as a
    # question and answered, and `reports.a_running_list` carries the reasoning.
    #
    # **MEASURED ON HIS OWN DASHBOARD, 2026-09-11, rather than taken from the
    # reference, whose own version of this is a pile of fallbacks that gives up
    # saying "selectors need updating".** The card is built like this:
    #
    #     Views        <- the label, a <p>
    #     (10 Sep)     <- THE CARD'S OWN DAY, one level up with the label
    #     34,877       <- the figure, two levels up
    #     14.15%       <- how much it moved, in the same card
    #
    # **THE CARD CARRYING ITS OWN DAY SETTLES TWO THINGS AT ONCE.** `DOCS.md:666`
    # asks in bold that the day be read off the page rather than assumed -- it
    # showed `(10 Sep)` while the day was the 11th. **And `Orders` on its own
    # matches TWICE**, because the sidebar has an `Orders` item as well; narrowing
    # by the day the card carries is what tells them apart, and it makes reading
    # the wrong day impossible rather than unlikely.
    "me_views": Recipe(
        to_take=(
            Step(GO, address=GROWTH + "/home", why="opening the dashboard"),
            # **A LONG WAIT BEFORE ANYTHING IS READ.** The reference sleeps five
            # seconds on this page in so many words -- "dashboard takes time to
            # hydrate" -- and a figure read while a card is still drawing is a
            # figure read wrong, which is worse than one not read at all.
            Step(WAIT_FOR,
                 find=Find(BY_TEXT, "Views", near="{day_in_words}",
                           day_in_words_is=MEESHO_WRITES_IT,
                           day_in_words_of=THE_DAY_IT_IS_ABOUT,
                           called="the views card for the day"),
                 patience=60, why="waiting for the dashboard cards to finish drawing"),
            Step(READ_NUMBER,
                 find=Find(BY_TEXT, "Views", near="{day_in_words}",
                           day_in_words_is=MEESHO_WRITES_IT,
                           day_in_words_of=THE_DAY_IT_IS_ABOUT),
                 patience=30, why="reading the views for the day"),
            Step(READ_NUMBER,
                 find=Find(BY_TEXT, "Orders", near="{day_in_words}",
                           day_in_words_is=MEESHO_WRITES_IT,
                           day_in_words_of=THE_DAY_IT_IS_ABOUT),
                 patience=30, why="reading the orders for the day"),
            Step(ADD_TO_THE_LIST, patience=30,
                 why="adding the day to the running list"),
        ),
    ),
    # **DECLARED SINCE THE LIST WAS WRITTEN AND NEVER BUILT.** Its steps are read
    # off the working reference's own claims handler, which has been fetching
    # this file every night for months.
    "me_claims": Recipe(
        to_take=(
            Step(GO, address=FULFILMENT + "/claims", why="opening the claims page"),
            # **THE WAY IN IS A `<p>` READING THE ONE WORD "Download", not a
            # button** -- the same shape as payments, and the reference says so
            # in its own source. Asked for as a control it answers nothing;
            # asked for as something pressable it answers the one thing.
            Step(WAIT_FOR, find=Find(BY_PRESSABLE_TEXT, "Download", called="the download menu"),
                 patience=45, why="waiting for the claims page to finish drawing"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Download", called="the download menu"),
                 why="opening the download menu"),
            # **NO RANGE IS PICKED, AND THAT IS THE ENTRY MATCHING THE LIST.**
            # `reports.py` already says Meesho hands back a rolling window here
            # rather than a chosen day. The reference confirms it: it sets the
            # period once, on the very first run, and never again. A range step
            # would be asking for something this page does not offer.
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Export Data"), why="asking for the export"),
            # **THE STEP THAT REOPENED THIS MENU IS GONE, AND IT IS GONE BECAUSE
            # OF WHAT HIS OWN PANEL SAID ON 2026-09-11:** "opening the download
            # menu again: 11 things match the download menu. More than one thing
            # on the page matches, so which one was meant cannot be known."
            #
            # **ELEVEN, AND THE FIRST CLICK ON THE VERY SAME WORDS TWO STEPS
            # ABOVE FOUND EXACTLY ONE.** So the ten arrived because "Export Data"
            # was pressed: the list of exports already made is now on the page,
            # each row with its own Download, exactly as the returns panel has ten
            # of on his account. The menu was never shut, so there was nothing to
            # reopen -- **the step was asking to open something that was already
            # open, and paying for it with ten rows of ambiguity.**
            #
            # **AND THE REFERENCE'S REOPENING IS NOT EVIDENCE FOR KEEPING IT
            # HERE, which is the part worth being careful about.** It does press
            # this opener on every poll (`content/meesho.js handleClaims`,
            # 1493-1503) -- but it presses it at the top of a LOOP whose bottom
            # is `document.body.click()`, which shuts the menu. It is reopening
            # what its own previous round closed. Nothing closes it here, so the
            # press has no work to do. **The one press that does real work is
            # "Exported Files", and that is kept.**
            #
            # **AND ITS OWN LOOKUP TAKES THE FIRST MATCH RATHER THAN REFUSING ON
            # SEVERAL**, so eleven never troubled it and it never had to tell
            # these two states apart. This half does refuse, which is how the
            # eleven came to be known at all.
            #
            # **AND THE "Exported Files" PRESS HAS GONE TOO, 2026-09-11, AND THE
            # PARAGRAPH ABOVE CALLING IT "the one press that does real work" WAS
            # WRONG.** Measured on his own claims panel, element by element:
            #
            #   `Exported Files`  a `<p>`, **`cursor: auto`**
            #   `Export Data`     a `<button>`, `cursor: pointer`
            #   `Download`        a `<p>`, `cursor: pointer`
            #
            # **IT IS A HEADING, NOT A CONTROL.** Something pressable is asked for
            # and a heading is not pressable, so this step could never find it on
            # any day -- and it did not: the run of 2026-09-11 waited out its
            # whole thirty seconds and said *"could not find 'Exported Files'. It
            # is not on the page at all."* The words were on the page the entire
            # time.
            #
            # **AND THERE IS NOTHING FOR IT TO DO.** The moment the Download menu
            # opens, the list of exports already made is drawn with it -- eleven
            # Downloads where a shut menu has one, today's row among them. There
            # is no second view to switch to.
            #
            # **A CORRECTION OWED TO THE REFERENCE (Rule 36.4).**
            # `content/meesho.js:1502-1505` presses this same heading on every
            # poll, finding it with `querySelectorAll('p')` and no test of whether
            # it is a control at all. Pressing a `<p>` that is not one does
            # nothing, so it has been a no-op there for months and nothing ever
            # said so. **Copied here into a door that asks for something
            # pressable, the same no-op became a report that never arrives.**
            # **NAMED BY THE DAY IT WAS MADE, because that is all a claims row
            # carries.** The panel keeps every export ever made, so "Download"
            # alone finds all of them and refuses -- which is right, and useless.
            # A claims export is a rolling window and carries no data date, so
            # the words are the platform's own wording of the day, exactly as
            # returns does.
            # **MEESHO'S WORDING, NAMED.** Like returns, this placeholder was
            # filled by nothing at all, so the row was looked for as `2026-08-25`
            # -- which that panel never writes -- and claims has been broken this
            # way since it was written.
            # **AND IT IS THE DAY THE EXPORT WAS MADE, WHICH IS TODAY, NOT THE
            # DAY BEING FETCHED.** Filled with the data date this looked for
            # `24 Aug 2026` on a row reading `25 Aug 2026, 04:49 PM` -- right
            # wording, wrong day, nothing found. The reference keeps the two
            # apart in one function: `content/meesho.js:1055` matches the row
            # with today and names the saved file with yesterday.
            Step(TAKE_FILE, find=Find(BY_PRESSABLE_TEXT, "Download", near="{day_in_words}",
                                      day_in_words_is=MEESHO_WRITES_IT,
                                      day_in_words_of=THE_DAY_IT_WAS_MADE),
                 patience=300, why="taking the finished file"),
        ),
    ),

    # ---- Flipkart: the Reports Centre three, two-phase
    "fk_orders": _reports_centre("Fulfilment Reports", "Orders", "orders"),
    # **RETURNS DO NOT GO THROUGH THE REPORTS CENTRE, AND THEY NEVER DID IN THE
    # REFERENCE'S CODE.** Its `DOCS.md:688-746` says they do; its code
    # (`content/flipkart.js:2620-2900`) goes to the Returns page, and his ruling of
    # 2026-09-14 is to do it exactly that way: *"going through the entire flow,
    # picking the date, on apply, and then requesting download, then going to the
    # previous downloads and getting it."* This recipe used the Reports Centre and
    # refused twice on two `Request New Report` matches. **It also spends none of
    # Flipkart's twenty** -- that allowance is the Reports Centre's.
    "fk_returns": Recipe(
        ready_in_minutes=30,
        to_ask=(
            Step(GO, address=RETURNS, patience=60, why="opening all returns"),
            # **A `DIV` WITH `cursor: auto`, MEASURED.** Waited for as words.
            Step(WAIT_FOR, find=Find(BY_TEXT, "Date of Closure", called="the returns page"),
                 patience=60, why="waiting for the returns page to finish drawing"),
            # **THE WORDS THEMSELVES OPEN THE CALENDAR, AND THE BOX BESIDE THEM DOES
            # NOT.** Measured: clicking the text `INPUT` next to them drew nothing;
            # clicking the `DIV` drew two months (`Sep 2026`). The reference clicks
            # the words too (`content/flipkart.js:2658-2679`).
            Step(CLICK, find=Find(BY_TEXT, "Date of Closure", called="the date of closure filter"),
                 why="opening the date of closure calendar"),
            # **A DAY IT HAS NOT BUILT SAYS SO IN THE CURSOR**: the 15th read
            # `not-allowed` on the 14th while the 12th-14th read `pointer`.
            Step(PICK_RANGE, patience=30, switched_off_days_change_the_cursor=True,
                 why="setting the day to fetch"),
            # A `span` inside a real `button`, measured, as is `Request Download`.
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Apply"), why="applying the day"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Request Download"),
                 why="asking for the returns file"),
        ),
        to_take=(
            Step(GO, address=RETURNS, patience=60, why="coming back for the returns file"),
            Step(WAIT_FOR, find=Find(BY_ROLE_AND_TEXT, "Previous Downloads",
                                     called="the previous downloads button"),
                 patience=60, why="waiting for the returns page to finish drawing"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Previous Downloads",
                                  called="the previous downloads button"),
                 why="opening the returns files already asked for"),
            # **EVERY ROW IS A `TR` READING `16:24, Sep 14, 2026 | 1 Locations |
            # 17/06/26 -> 14/09/26 | 3 Filters | Ready to download | Download`,
            # with a real `<button>` `Download`. MEASURED 2026-09-14.** Named by the
            # day it was ASKED FOR, and only a row that is ready. The reference
            # matches the row by its request time (`content/flipkart.js:2824-2845`).
            Step(TAKE_FILE, find=Find(BY_ROLE_AND_TEXT, "Download", near="{day_in_words}",
                                      also_saying="Ready to download",
                                      day_in_words_is=FLIPKART_WRITES_IT,
                                      day_in_words_of=THE_DAY_IT_WAS_MADE,
                                      called="the finished returns file"),
                 patience=90, why="taking the finished returns file"),
        ),
    ),
    "fk_payments": _reports_centre("Payment Reports", "Settled Transactions", "payments"),

    # ---- Flipkart: the traffic report, two-phase and the live selector fix
    "fk_views": Recipe(
        ready_in_minutes=30,
        to_ask=(
            # **SIXTY SECONDS TO LOAD, MEASURED 2026-09-14.** A `go` waits for the
            # browser to call the page finished, and this one took 38 seconds in
            # his own Chrome -- the default thirty failed the report before its
            # first step. The content itself was ready at 3.
            Step(GO, address=TRAFFIC, patience=60, why="opening the traffic report"),
            # **THE LIVE FIX, read off his own Flipkart on 2026-08-27.** The words
            # "Custom Dates" DO NOT EXIST on this page any more -- Flipkart replaced
            # the button with a dropdown whose label is one word, `Custom`. That is
            # the whole of a 29-day outage, and it is one entry here.
            #
            # **MATCHED EXACTLY, and that matters on this page**: a loose match for
            # "custom" also hits the "Customer Segments" tab sitting beside it,
            # which is the chart-legend trap all over again.
            # **NOT A CONTROL. MEASURED ON HIS OWN PANEL, 2026-09-11, ELEMENT BY
            # ELEMENT, AFTER THE FIRST FLIPKART RUN THIS PRODUCT HAS EVER MADE
            # FAILED HERE.** The run said *"could not find the date range
            # dropdown"*. It was on the page the whole time:
            #
            #   `Custom`   a `div`, **no role, no control tag, `cursor: pointer`**
            #   `Latest`   the same
            #   `Done`     a `span`, the same
            #
            # **THIS WHOLE PAGE IS BUILT OUT OF DIVS WITH A POINTER CURSOR.** Of
            # the eighty-six pressable things read off it, not one of the period
            # chips is a button, a link or carries a role. Asked for as a control
            # the page answers nothing at all -- which is the Meesho sidebar
            # fault (`driver.js:243`) on the other portal, and it is why
            # `BY_PRESSABLE_TEXT` exists.
            #
            # **AND THE MATCH IS EXACT, WHICH ON THIS PAGE IS NOT A DETAIL.**
            # `Customer Segments` sits beside it and is also a pointer div, so a
            # loose match finds two and refuses.
            # **AND THE TRAFFIC REPORT IS ITS OWN TAB, WHICH NOTHING HERE HAD
            # EVER PRESSED. HE POINTED THIS OUT ON 2026-09-14 AND HE WAS RIGHT.**
            #
            # **WHAT WAS WRITTEN HERE ON THE 11TH -- that Flipkart had removed the
            # export -- WAS WRONG, and it is corrected rather than left standing.**
            # This address opens Seller Insights on a tab row reading
            # `Today's Sales | Business Health | Traffic Report | Earn More |
            # Search Trends | Category Research | Customer Segments`, and the
            # listings-report button lives on the **Traffic Report** tab only.
            # Everything measured that day was measured on the wrong tab.
            #
            # **IT IS A REAL `button` WITH `role="tab"`**, measured -- the one
            # control on this page that is not a bare div. The same words also
            # appear as a `div` leaf inside it, so asking for a control finds
            # exactly one.
            Step(WAIT_FOR, find=Find(BY_ROLE_AND_TEXT, "Traffic Report", called="the traffic report tab"),
                 patience=60, why="waiting for seller insights to finish drawing"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Traffic Report", called="the traffic report tab"),
                 why="opening the traffic report tab"),
            Step(WAIT_FOR, find=Find(BY_PRESSABLE_TEXT, "Custom", called="the date range chip"),
                 patience=60, why="waiting for the traffic report to finish drawing"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Custom", called="the date range chip"),
                 why="opening the date range chip"),
            # **AND A DAY FLIPKART HAS NO DATA FOR IS SWITCHED OFF IN THE CURSOR
            # AND IN NOTHING ELSE -- WHICH IS THE WHOLE OF WHAT HE ASKED FOR.**
            # His words, 2026-09-14: the `Latest` chip announces its own day, and
            # *"if the report is not generated for yesterday it will be showing
            # the day before yesterday. In that case code has to understand this
            # is not available for the intended date."*
            #
            # **MEASURED ON HIS OWN CALENDAR THE SAME DAY, and it was exactly that
            # case:** `Latest` read `12 Sep 26` while the day was the 14th, and in
            # the open calendar **the 13th reported `cursor: not-allowed` on both
            # panels** while the 12th reported `pointer`. Of 84 cells, 58 were
            # switched off.
            #
            # **SO NO NEW KIND OF STEP IS NEEDED. The door already refuses a day
            # whose cursor says it is off** -- it simply had never been told that
            # this calendar says it that way. Told, the report fails out loud
            # naming the day, instead of Flipkart quietly clamping the range to
            # the latest day it does have and the file landing under the name of
            # the day that was asked for. **That clamping is real: this address
            # was opened asking for 09-10 and came back reading
            # `startDate=2026-09-12&endDate=2026-09-12`.**
            Step(PICK_RANGE, patience=30,
                 switched_off_days_change_the_cursor=True,
                 why="setting the day to fetch, and refusing a day Flipkart has no data for"),
            # **AND THE RANGE HAS TO BE ACCEPTED BEFORE THE REQUEST BUTTON EXISTS
            # AT ALL.** Read off the page with the period left on `Latest`: there
            # is no `Request Listings Report` anywhere on it, shown or hidden --
            # only the app's own stylesheet carrying `generateReportCard` and
            # `downloadReport` classes for a component that is not drawn. The
            # reference's step 7 says the page reloads for the chosen range and
            # step 8 then presses the request button (`DOCS.md:962-970`).
            #
            # **`Done` IS A `span` WITH A POINTER CURSOR**, measured in the open
            # calendar. The reference looks for it with `findBtn`, which searches
            # buttons, links and roles only -- so **the reference has never found
            # this control either**, and gets away with it because its own call
            # is `if (doneBtn)`. A correction is owed to it (Rule 36.4).
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Done", called="the accept button"),
                 patience=30, why="accepting the range, which is what draws the request button"),
            # **MATCHED LOOSELY, AND THAT IS MEASURED RATHER THAN CAUTIOUS.** The
            # button is a real `<button>` with a pointer cursor, and **its words
            # read `Request Listings Reportdownload`** -- the trailing word comes
            # from the icon inside it. Asked for exactly, nothing matches.
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Request Listings Report", exact=False,
                                  called="the request button"),
                 patience=60, why="asking Flipkart to build the report"),
        ),
        to_take=(
            # Sixty for the same measured reason as the asking phase's `go`.
            Step(GO, address=TRAFFIC, patience=60, why="coming back for the traffic report"),
            # **THE SAME RANGE HAS TO BE CHOSEN AGAIN, AND WITHOUT THIS THE
            # DOWNLOAD BUTTON CAN NEVER APPEAR.** The report Flipkart built is
            # keyed to the range that was asked for, and arriving at this address
            # puts the page back on `Latest` every time -- the reference says so
            # in its own words at `DOCS.md:1832`: *"navigating directly to the
            # Traffic Report page resets to the Latest preset, so the range must
            # be re-applied each time"*, and it calls the identical
            # `fkViewsSelectRange` in both of its phases for exactly this.
            #
            # **THIS HALF ASKED FOR THE DOWNLOAD BUTTON ON A PAGE SHOWING THE
            # WRONG RANGE**, waited out two minutes, and would have reported
            # Flipkart as still building a report that was finished.
            Step(WAIT_FOR, find=Find(BY_ROLE_AND_TEXT, "Traffic Report", called="the traffic report tab"),
                 patience=60, why="waiting for seller insights to finish drawing"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Traffic Report", called="the traffic report tab"),
                 why="opening the traffic report tab"),
            Step(WAIT_FOR, find=Find(BY_PRESSABLE_TEXT, "Custom", called="the date range chip"),
                 patience=60, why="waiting for the traffic report to finish drawing"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Custom", called="the date range chip"),
                 why="opening the date range chip"),
            Step(PICK_RANGE, patience=30,
                 switched_off_days_change_the_cursor=True,
                 why="choosing the same range the report was built for"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Done", called="the accept button"),
                 patience=30, why="accepting the range, which is what draws the download button"),
            # **LOOSELY, for the same measured reason as the request button: the
            # icon inside it puts `download` on the end of its words.** And the
            # two never sit on the page together -- the same button changes from
            # one to the other once the report has been asked for, which is his
            # own description of it.
            Step(WAIT_FOR, find=Find(BY_PRESSABLE_TEXT, "Download Listings Report", exact=False,
                                     called="the download button"),
                 patience=120, why="waiting for the finished report"),
            Step(TAKE_FILE, find=Find(BY_PRESSABLE_TEXT, "Download Listings Report", exact=False),
                 patience=90, why="taking the finished traffic file"),
        ),
    ),

    # ---- Flipkart: the top search keywords, read off the traffic report
    # **THE REFERENCE'S `handleFkKeywords`, WITH THE ONE PART A PERSON DID DONE HERE
    # (2026-09-15).** There a person opened the Traffic Report and pressed `Latest`
    # and `All`; here the recipe does. **LATEST, NOT A CHOSEN DAY -- the reference
    # requires it** ("only Latest is single-day") and his first run, on a Custom
    # day, drew the listings with no keyword buttons at all. So the keywords are
    # Flipkart's latest day only; the reading step compares that day with the day
    # asked for before it presses anything. `All` products is in the address and
    # already chosen on arrival.
    "fk_keywords": Recipe(
        to_take=(
            Step(GO, address=TRAFFIC, patience=60, why="opening the traffic report"),
            Step(WAIT_FOR, find=Find(BY_ROLE_AND_TEXT, "Traffic Report", called="the traffic report tab"),
                 patience=60, why="waiting for seller insights to finish drawing"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Traffic Report", called="the traffic report tab"),
                 why="opening the traffic report tab"),
            Step(WAIT_FOR, find=Find(BY_PRESSABLE_TEXT, "Latest", called="the latest day chip"),
                 patience=60, why="waiting for the traffic report to finish drawing"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Latest", called="the latest day chip"),
                 why="choosing the latest day, the only period the keywords are offered for"),
            # **SIXTY SECONDS FOR THE LISTING TABLE TO DRAW**, which is what this
            # patience waits for. The reading itself takes the reference's own pace,
            # about seven seconds a listing -- ten to fifteen minutes on his catalogue,
            # inside the twenty-five a walk is believed for.
            Step(READ_THE_KEYWORDS, patience=60,
                 why="reading every listing's top search keywords, page by page"),
        ),
    ),

    # ---- Flipkart: one-shot
    "fk_claims": Recipe(
        to_take=(
            Step(GO, address=CLAIMS, why="opening the claims page"),
            # **`SPF Claims` IS THE PAGE'S OWN `h1`, NOT A TAB. MEASURED ON HIS
            # OWN PANEL, 2026-09-11.** It has no role, no control tag and
            # `cursor: auto`. This waited for it as a CONTROL and then PRESSED
            # it, so the report could never get past its second step -- and the
            # failure would have read as a renamed tab.
            #
            # **THE STEP THAT PRESSED IT IS GONE, because there is nothing to
            # press.** The words are still waited for, as words, because they
            # are the honest signal that this page has finished drawing.
            #
            # **AND THE TWO REAL TABS ARE NOT WORTH PRESSING EITHER:** they read
            # `NFBF  Raised by you (150)` and `FBF  Auto approved (12)`, **with
            # the counts inside the words**, so nothing can match them exactly
            # and they change every day. The page opens on the first of them
            # already, measured -- its own address says `SELLER_PENDING`.
            Step(WAIT_FOR, find=Find(BY_TEXT, "SPF Claims", called="the claims page"),
                 patience=60, why="waiting for the claims page to finish drawing"),
            # **A `div` WITH A POINTER CURSOR, like almost everything on this
            # portal.** Asked for as a control it answers nothing.
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Download Report", called="the download menu"),
                 why="opening the download menu"),
            # The menu offers `Last 3 days`, `Last 7 days`, `Last 15 days`,
            # `Last 30 days` and `Custom Date Range` -- each a `div` with a
            # pointer cursor. **The custom range is the only one that can name
            # the day this run is fetching.**
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Custom Date Range"), why="choosing the days"),
            # **ITS CALENDAR OPENS TWO MONTHS BEHIND, measured: `Jul 2026` and
            # `Aug 2026` while the day was the 11th of September.** So the door
            # has to step it forward, which it does by the arrows -- and the
            # headings are `label` elements, which is a second reason `label` had
            # to become something the door can see.
            Step(PICK_RANGE, patience=30, why="setting the day to fetch"),
            # **`Done` IS A `span` WITH A POINTER CURSOR**, and pressing it is
            # what starts the download. Asked for as a control, nothing matched.
            Step(TAKE_FILE, find=Find(BY_PRESSABLE_TEXT, "Done"), patience=90,
                 why="taking the claims file"),
        ),
    ),
    "fk_listings": Recipe(
        ready_in_minutes=30,
        to_ask=(
            Step(GO, address=LISTINGS, why="opening the listings page"),
            Step(WAIT_FOR, find=Find(BY_ROLE_AND_TEXT, "Downloads", called="the downloads menu"),
                 patience=60, why="waiting for the listings page to finish drawing"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Downloads", called="the downloads menu"),
                 why="opening the downloads menu"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Download Listing File"), why="asking for the listing file"),
        ),
        to_take=(
            Step(GO, address=LISTINGS, why="coming back for the listing file"),
            Step(WAIT_FOR, find=Find(BY_ROLE_AND_TEXT, "Downloads", called="the downloads menu"),
                 patience=60, why="waiting for the listings page to finish drawing"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Downloads", called="the downloads menu"),
                 why="opening the downloads menu"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "View Recent Downloads"), why="opening the downloads history"),
            # **THERE IS NO "Download" ON A ROW AT ALL. THE FILE NAME IS THE
            # CONTROL.** Read off his own Downloads History on 2026-09-11, and
            # this is what the run of the same evening refused on -- *"9 things
            # match Download"*, because the page's own menu and every other
            # control on it carry that word and no row does.
            #
            #   Document                              File Type   Requested On
            #   S_listing--ui--group_..._default.xls  Listing     11 September, 11:10 PM
            #   S_listing--ui--group_..._default.xls  Listing     10 September, 11:46 AM
            #   E_bangle-bracelet-armlet_...xls       Catalog     16 August, 10:34 PM
            #
            # **THE FILE NAME IS A `div` WITH A POINTER CURSOR and pressing it is
            # the download** -- but it is the seller's own name and cannot be
            # written here. **What can is `Listing`**, the File Type cell, which
            # is the only stable word separating the listing file from the
            # catalogue file. So the words name the row and the pressable thing
            # beside them is taken, exactly as the date box is reached.
            #
            # **AND NARROWED BY THE DAY THE FILE WAS MADE, NOT THE DAY IT IS
            # ABOUT.** A listings file is a snapshot of the whole catalogue and
            # carries no data date; his panel holds four `Listing` rows from four
            # different days, so `Listing` alone finds four and refuses. The row
            # says `11 September, 11:10 PM` -- **the full month name and no year,
            # which is why `{d} {Month}` had to be added to Flipkart's
            # spellings.**
            #
            # **AND BY 2026-09-14 THE ROW HAS A REAL `Download` BUTTON, AND THE
            # FILE NAME PRESSES NOTHING.** Measured on his own Downloads History
            # that afternoon, row by row: `S_listing--ui--group_..._default.xls
            # | Listing | 14 September, 04:30 PM | Download`, the last a real
            # `<button>`. The collect pressed the file name as written above and
            # waited ninety seconds for a download that never began. **The
            # reference presses the button in the Listing row that is not still
            # generating** (`content/flipkart.js` `findReadyListingDownloadBtn`),
            # so this now asks for that button, on the row made on the run's day
            # that says `Listing` -- which also keeps it off the Catalog rows.
            Step(TAKE_FILE, find=Find(BY_ROLE_AND_TEXT, "Download",
                                      near="{day_in_words}",
                                      also_saying="Listing",
                                      day_in_words_is=FLIPKART_WRITES_IT,
                                      day_in_words_of=THE_DAY_IT_WAS_MADE,
                                      called="the finished listing file"),
                 patience=90,
                 why="taking the finished listing file"),
        ),
    ),

    # ---- Flipkart: the seven ad reports, from one template
    "fk_ads_daily": _ads("Consolidated Daily Report"),
    "fk_ads_fsn": _ads("Consolidated FSN Report"),
    "fk_ads_placements": _ads("Placement Performance Report"),
    "fk_ads_overall": _ads_overall(),
    "fk_ads_search": _ads("Search Term Report"),
    "fk_ads_orders": _ads("Campaign Order Report"),
    "fk_ads_kw": _ads("Keyword Report"),
}


# ------------------------------------------- how a signed-out portal is known

# **TWO STATES THAT LOOK ALIKE AND ARE NOT THE SAME THING**, and telling them
# apart is worth its own list. Signed OUT, Flipkart serves its PUBLIC MARKETING
# SITE, whose menu reads these four things. Signed IN but part-way through
# drawing, it shows the seller's own top bar and none of them. **Across 71 real
# occurrences in the reference's log, 54 were the second and harmless** -- and
# one message for both is why a month of them read as one problem.
#
# **TWO OF THEM HAVE TO BE ON THE PAGE, NOT ONE.** A single one turns up on a
# signed-in page easily enough -- Flipkart's own signed-in sidebar carries
# "Growth" -- while the public menu carries the whole set at once.
#
# **EACH ONE IS A WHOLE MENU ITEM, and that matters.** Read as a run of letters
# anywhere on the page, "Grow" matches inside Meesho's "Grow Business" -- a thing
# that is not on the page at all as something you could press. Read off his own
# Meesho on 2026-08-27, live. So each of these is asked for as a control carrying
# exactly those words, and a fragment of a longer name is not one.
#
# **BOTH PLATFORMS ARE IN ONE LIST ON PURPOSE.** A Flipkart word does not appear
# on a Meesho page, so combining them costs nothing -- and the rule needs TWO of
# them, which is what guards against a stray one.
#
# **AND MEESHO'S MARKETING SITE IS SERVED FOR ANY ADDRESS IT DOES NOT KNOW**, not
# only when somebody is signed out. Read live: `supplier.meesho.com/panel` gives
# the marketing site and the words "Page Not Found" while the seller is signed in.
# That is why two are needed rather than one, and why the panel's own address has
# to be right.
SIGNED_OUT_SIGNS: Tuple[str, ...] = (
    # Flipkart's public menu.
    "Sell Online",
    "Fees and Commission",
    "Grow",
    "Shopsy",
    # Meesho's public menu, read off the real page.
    "How it works",
    "Pricing & Commission",
    "Shipping & Returns",
    "Grow Business",
    "Start Selling",
)


# **KNOWN TO HAND THE FILE OVER IN A WAY AN EXTENSION CANNOT TAKE TWICE.**
# Flipkart began building these inside the page on 2026-08-22 -- confirmed twice in
# its own log the same evening. Marked so the failure reads as what it is, a door
# closing, rather than as something to retry every night for ever.
BUILDS_IN_THE_PAGE_SINCE = {
    "fk_orders": "2026-08-22",
    "fk_returns": "2026-08-22",
}


def recipe(report_id: str) -> Recipe:
    """How one report is fetched, or a refusal naming it."""
    found = RECIPES.get(report_id)
    if found is None:
        raise KeyError(f"{report_id!r} is not a report the browser door knows how to fetch.")
    return found


def steps_for(report_id: str, panel: str, collecting: bool = False) -> Tuple[Step, ...]:
    """The steps to run now, with the seller's own panel name filled in.

    `collecting` picks the second half of a two-phase report. **A one-shot report
    has only the one set and `collecting` changes nothing** -- so a caller that
    gets it wrong fetches the report rather than doing nothing, which is the safer
    way round.

    **THE PANEL NAME IS THE SELLER'S AND IS NEVER IN THIS FILE.** It is the short
    slug in the middle of every Meesho address -- not the section around it, which
    is Meesho's own and belongs here. The reference holds one supplier's slug in
    its own source; a product that ships to every seller cannot (D27, D30, D92).
    Flipkart needs none, so only Meesho asks.
    """
    which = recipe(report_id)
    # **ASKED BEFORE A SINGLE STEP IS HANDED OUT.** A recipe naming the wrong
    # portal's wording of a day would run beautifully, spend one of the seller's
    # rationed Flipkart requests, and then look for a row written a way that
    # portal never writes. Refused here, the door answers it as a fault in this
    # product -- which is what it is -- rather than as the platform changing.
    wrong_wording = why_the_wording_is_wrong(report_id)
    if wrong_wording:
        raise ValueError(wrong_wording)
    steps = which.to_ask if (which.two_phase and not collecting) else which.to_take
    if any("{panel}" in s.address for s in steps) and not panel:
        raise ValueError(
            "This report needs the seller's own panel name, which is in the address of their "
            "supplier panel. It is the seller's own data and is never written into the product."
        )
    # **THE STEP IS COPIED WITH ONE FIELD CHANGED, NEVER REBUILT FIELD BY FIELD.**
    #
    # It used to be rebuilt by naming every field, and the day a field was added
    # to `Step` it was silently dropped here -- the step came out of this
    # function with the new field back at its default and nothing anywhere said
    # so. **That happened**: `look_again` was added for Meesho's orders export
    # and this function quietly took it off again, so the door was handed a step
    # that had never been told to reopen anything, and the recipe read as though
    # it had been. Two of the checks written the same hour caught it.
    #
    # `replace` copies everything and changes what is named, so a field added
    # tomorrow arrives here by itself.
    return tuple(
        replace(s, address=s.address.format(panel=panel)) if "{panel}" in s.address else s
        for s in steps
    )


def every_recipe() -> Tuple[str, ...]:
    """Every report this door can fetch."""
    return tuple(sorted(RECIPES))


# **THE REPORTS THIS DOOR CANNOT FETCH YET, NAMED ONE BY ONE WITH THE REASON.**
#
# **A HOLE THAT IS NOT WRITTEN DOWN IS A HOLE NOBODY CAN SEE.** Until this list
# existed, `reports.py` declared reports that had no recipe at all and the only
# thing measuring the door counted the recipes -- so "how many Meesho reports
# need a browser" answered four while the list declared seven, and the three with
# nothing behind them were invisible to every check in the project. Naming them
# here does not fetch them; it makes the difference between what is declared and
# what is built a thing that is stated rather than a thing that is missing.
#
# **EVERY ONE OF THESE NEEDS A STEP THE DOOR DOES NOT HAVE, and that is one
# reason, five times over.** The five steps -- go, click, wait for, pick a range,
# take the file -- all end in a file the platform hands over. These four end in
# rows the page was made to give up: read off the screen, or asked for from the
# platform's own addresses from inside the signed-in page. **Adding that step is
# its own piece of work, not a recipe**: it reaches into the language in
# `browser.py`, the checks beside it, what the exporter carries across, and the
# walker in the extension that carries the steps out.
#
# **THE CHECK BESIDE THIS ONE IS WHAT MAKES IT WORTH HAVING.** Every declared
# report on the browser door is either in `RECIPES` or named here -- so the day
# somebody adds a report and forgets its recipe, that goes red, instead of the
# report quietly never being fetched.
# **EMPTY SINCE 2026-09-15.** `fk_keywords` was the last: the door learned to read
# the keyword pop-ups off the traffic report, and the part the reference left to a
# person -- opening the report and choosing the day -- is the traffic report's own
# steps.
NOT_YET_A_RECIPE: Dict[str, str] = {}


# **REPORTS THAT ARE REAL AND ARE FETCHED BY A DIFFERENT REPORT'S RUN.**
#
# **THIS IS A THIRD ANSWER AND IT HAD TO EXIST.** Until now a report either had a
# recipe or was written down as one this door cannot reach -- and the ads sweep is
# neither. `me_ads_summary` and `me_ads_catalog` are fetched every time `me_ads`
# runs, out of the same two calls, because asking Meesho for the same campaign
# three times to write three files would be three times the load for the same
# answer. **Left in `NOT_YET_A_RECIPE` they would show a seller "cannot be
# fetched" about two reports that arrive in their Drive**, which is worse than
# saying nothing.
MADE_BY_ANOTHER: Dict[str, str] = {
    "me_ads_summary": (
        "Fetched by the Meesho ads sweep, which asks for a campaign's day once "
        "and writes all three files from the one answer."
    ),
    "me_ads_catalog": (
        "Fetched by the Meesho ads sweep, which asks for a campaign's day once "
        "and writes all three files from the one answer."
    ),
}


# Which prefix belongs to which platform. **WRITTEN DOWN, NOT WORKED OUT.** This
# was `platform[:2]`, which gives "fl" for Flipkart while every id begins `fk_` --
# so it answered "no Flipkart reports need a browser", which is the opposite of the
# truth and exactly the number this is for. A rule cleverly derived from a name is
# a rule nobody notices being wrong.
PREFIXES = {"flipkart": "fk_", "meesho": "me_", "amazon": "az_"}


def on_the_browser_door_for(platform: str) -> Tuple[str, ...]:
    """Which of one platform's reports this door can actually fetch.

    **THIS COUNTS RECIPES, NOT DECLARATIONS, and saying so is the correction.**
    It used to say it answered "the reports still needing a browser", which is
    what `reports.py` declares -- a different and larger number. Two checks read
    it as the declared one and so went green on thirteen and four while fourteen
    and seven were declared, which is how four reports came to have nothing
    behind them with nothing anywhere saying so. What is declared and not built
    is `NOT_YET_A_RECIPE` above, and a check holds the two together.

    **THE FLIPKART NUMBER IS THE ONE THAT SHOULD FALL TO NOTHING**, the day its
    Seller API application stops being Pending. The Meesho one will not.
    """
    prefix = PREFIXES.get(platform)
    if prefix is None:
        raise KeyError(f"{platform!r} is not a platform this knows the reports of.")
    return tuple(r for r in every_recipe() if r.startswith(prefix))
