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

from dataclasses import dataclass, field, replace
from typing import Dict, Optional, Tuple

from browser import (
    BY_PRESSABLE_TEXT,
    BY_ROLE_AND_TEXT,
    BY_TEXT,
    CLICK,
    GO,
    PICK_RANGE,
    TAKE_FILE,
    WAIT,
    WAIT_FOR,
    Find,
    LookAgain,
    Step,
)


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

    @property
    def two_phase(self) -> bool:
        return bool(self.to_ask)


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
TRAFFIC = FLIPKART.format(
    where="dashboard/growth/seller-insights?businessVertical=ALL&section=purchase_funnel"
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
            Step(WAIT_FOR, find=Find(BY_ROLE_AND_TEXT, "Request New Report", called="the request button"),
                 patience=60, why="waiting for the reports centre to finish drawing"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Request New Report", called="the request button"),
                 why="starting a new request"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, kind), why=f"choosing {kind}"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, sub_kind), why=f"choosing {sub_kind}"),
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
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Select Date Range",
                                  called="the date range box"),
                 patience=30,
                 why="opening the date range box, which is what the calendar is hidden behind"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Custom", called="the custom range chip"),
                 patience=30, why="choosing a custom range, which is what draws the days"),
            # **TWO DAYS, NOT ONE.** Flipkart requires the start to be strictly
            # before the end; a single-day range is refused by a Submit that does
            # nothing at all, with no message.
            #
            # **AND A DAY THIS ONE CALENDAR HAS SWITCHED OFF SAYS SO IN THE
            # CURSOR AND IN NOTHING ELSE.** Flipkart disables a day two different
            # ways and only one of them can be read any other way -- see the note
            # on the step in `browser.py`. No other calendar here is asked.
            Step(PICK_RANGE, range_days=2, patience=30,
                 switched_off_days_change_the_cursor=True,
                 why="setting the two-day range Flipkart insists on"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Submit"), why="submitting the request"),
            # **THE BANNER IS WAITED FOR, and its absence is a real failure.** The
            # reference read a submitted report as failed because the banner had
            # already faded on a throttled tab, and then re-submitted three times.
            Step(WAIT_FOR, find=Find(BY_TEXT, "successfully", exact=False, called="the confirmation"),
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
            Step(WAIT_FOR, find=Find(BY_TEXT, "Generated", exact=False,
                                     near="To {day_in_words}", called="a finished report"),
                 patience=120, why="looking for a finished report for the day being fetched"),
            Step(TAKE_FILE, find=Find(BY_ROLE_AND_TEXT, "Download", near="To {day_in_words}"),
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
            Step(WAIT_FOR, find=Find(BY_ROLE_AND_TEXT, "Other Reports", called="the other reports tab"),
                 patience=60, why="waiting for the ads page to finish drawing"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Other Reports", called="the other reports tab"),
                 why="opening the other reports tab"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, report_type), why=f"choosing {report_type}"),
            Step(PICK_RANGE, patience=30, why="setting the day to fetch"),
            Step(TAKE_FILE, find=Find(BY_ROLE_AND_TEXT, "Download"), patience=90,
                 why=f"taking the {report_type} file"),
        ),
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
            Step(TAKE_FILE, find=Find(BY_PRESSABLE_TEXT, "Download", near="{day_in_words}"),
                 patience=120, why="taking the finished file"),
        ),
    ),
    "me_payments": Recipe(
        to_take=(
            Step(GO, address=PAYOUTS + "/payments", why="opening the payments page"),
            # **THE NINE-DAY OUTAGE LIVES HERE.** A chart legend on this very page
            # reads "Payments to Date", exactly like the menu item, and sits
            # earlier in the page. Matched exactly, and two matches refuse.
            Step(WAIT_FOR, find=Find(BY_PRESSABLE_TEXT, "Download", called="the download menu"),
                 patience=45, why="waiting for the payments page to finish drawing"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Download", called="the download menu"),
                 why="opening the download menu"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Payments to Date"), why="choosing the payments export"),
            # **THE DAYS ARE ASKED FOR EVEN THOUGH MEESHO IGNORES THEM.** Its
            # payments export always hands back the current settlement batch
            # whatever range is given -- proven by reading the file after three
            # wrongly-dated duplicates were written believing otherwise -- but the
            # page will not hand anything over until a range has been chosen.
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Custom Date Range"), why="opening the date range"),
            Step(PICK_RANGE, patience=30, why="setting the day, which Meesho then ignores"),
            Step(TAKE_FILE, find=Find(BY_PRESSABLE_TEXT, "Download"), patience=120,
                 why="taking the finished file"),
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
            # **THE MENU HAS TO BE OPENED AGAIN, and it is not the same reopening
            # as orders.** Orders needs the whole page loaded again before a
            # finished file appears; claims does not -- the reference reopens
            # this menu and steps into "Exported Files" on every poll, from the
            # same page. So the menu is reopened and nothing is reloaded.
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Download", called="the download menu"),
                 why="opening the download menu again, where the finished file now is"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Exported Files"),
                 why="opening the list of files already exported"),
            # **NAMED BY THE DAY IT WAS MADE, because that is all a claims row
            # carries.** The panel keeps every export ever made, so "Download"
            # alone finds all of them and refuses -- which is right, and useless.
            # A claims export is a rolling window and carries no data date, so
            # the words are the platform's own wording of the day, exactly as
            # returns does.
            Step(TAKE_FILE, find=Find(BY_PRESSABLE_TEXT, "Download", near="{day_in_words}"),
                 patience=300, why="taking the finished file"),
        ),
    ),

    # ---- Flipkart: the Reports Centre three, two-phase
    "fk_orders": _reports_centre("Fulfilment Reports", "Orders", "orders"),
    "fk_returns": _reports_centre("Fulfilment Reports", "Returns", "returns"),
    "fk_payments": _reports_centre("Payment Reports", "Settled Transactions", "payments"),

    # ---- Flipkart: the traffic report, two-phase and the live selector fix
    "fk_views": Recipe(
        ready_in_minutes=30,
        to_ask=(
            Step(GO, address=TRAFFIC, why="opening the traffic report"),
            # **THE LIVE FIX, read off his own Flipkart on 2026-08-27.** The words
            # "Custom Dates" DO NOT EXIST on this page any more -- Flipkart replaced
            # the button with a dropdown whose label is one word, `Custom`. That is
            # the whole of a 29-day outage, and it is one entry here.
            #
            # **MATCHED EXACTLY, and that matters on this page**: a loose match for
            # "custom" also hits the "Customer Segments" tab sitting beside it,
            # which is the chart-legend trap all over again.
            Step(WAIT_FOR, find=Find(BY_ROLE_AND_TEXT, "Custom", called="the date range dropdown"),
                 patience=60, why="waiting for the traffic report to finish drawing"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Custom", called="the date range dropdown"),
                 why="opening the date range dropdown"),
            Step(PICK_RANGE, patience=30, why="setting the day to fetch"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Request Listings Report", called="the request button"),
                 why="asking Flipkart to build the report"),
        ),
        to_take=(
            Step(GO, address=TRAFFIC, why="coming back for the traffic report"),
            Step(WAIT_FOR, find=Find(BY_ROLE_AND_TEXT, "Download Listings Report", called="the download button"),
                 patience=120, why="waiting for the finished report"),
            Step(TAKE_FILE, find=Find(BY_ROLE_AND_TEXT, "Download Listings Report"), patience=90,
                 why="taking the finished traffic file"),
        ),
    ),

    # ---- Flipkart: one-shot
    "fk_claims": Recipe(
        to_take=(
            Step(GO, address=CLAIMS, why="opening the claims page"),
            Step(WAIT_FOR, find=Find(BY_ROLE_AND_TEXT, "SPF Claims", called="the claims tab"),
                 patience=60, why="waiting for the claims page to finish drawing"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "SPF Claims", called="the claims tab"),
                 why="opening the claims tab"),
            Step(CLICK, find=Find(BY_ROLE_AND_TEXT, "Download Report", called="the download menu"),
                 why="opening the download menu"),
            Step(CLICK, find=Find(BY_PRESSABLE_TEXT, "Custom Date Range"), why="choosing the days"),
            Step(PICK_RANGE, patience=30, why="setting the day to fetch"),
            Step(TAKE_FILE, find=Find(BY_ROLE_AND_TEXT, "Done"), patience=90,
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
            Step(TAKE_FILE, find=Find(BY_ROLE_AND_TEXT, "Download"), patience=90,
                 why="taking the finished listing file"),
        ),
    ),

    # ---- Flipkart: the seven ad reports, from one template
    "fk_ads_daily": _ads("Consolidated Daily Report"),
    "fk_ads_fsn": _ads("Consolidated FSN Report"),
    "fk_ads_placements": _ads("Placement Performance Report"),
    "fk_ads_overall": _ads("Overall Performance Report"),
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


# **HOW EACH PLATFORM WRITES A DAY, because no two agree and a row is named by
# it.** Meesho's exported-files panel reads `25 Aug 2026, 04:49 PM` -- read off
# his own returns page on 2026-08-28. Written here rather than worked out in the
# extension, for the same reason every other decision is.
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def as_meesho_writes_a_day(day) -> str:
    """`25 Aug 2026`. No leading nought on the date, which is what the page shows."""
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


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
NOT_YET_A_RECIPE: Dict[str, str] = {
    "fk_keywords": (
        "The keywords are not a file Flipkart hands over. Somebody has to be on "
        "the traffic report with the day and all products chosen, and then every "
        "row's own keyword panel is opened in turn and read off the screen. The "
        "door has no step for reading a page, and no step for waiting on a person."
    ),
    "me_views": (
        "The views figure is not a file. It is two numbers read off the Meesho "
        "dashboard and added to a running list. The door has no step for reading "
        "a number off a page."
    ),
    "me_ads": (
        "The ads figures are not a file either. Meesho's own ads addresses are "
        "called from inside the signed-in page -- the campaign list, then each "
        "live campaign in turn -- and the rows are built from what comes back. "
        "The door has no step for calling an address."
    ),
    "me_ads_summary": (
        "It comes out of the same sweep as the campaigns, and for the same "
        "reason cannot be reached by the five steps this door has."
    ),
    "me_ads_catalog": (
        "It comes out of the same sweep as the campaigns, and for the same "
        "reason cannot be reached by the five steps this door has."
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
