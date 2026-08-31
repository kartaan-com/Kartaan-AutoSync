"""What a report IS. Shape 1 of the contract (D100).

**ONE LIST, AND IT IS THE WHOLE DESIGN.** The single best thing in the working
reference is that `config.js` is the only place a report is described: adding one
is one entry plus one handler, and nothing else. That idea carries over exactly,
with one field added -- `door` -- and that one word is what moves a report off the
browser the day its API arrives, instead of a rewrite.

**NOTHING TENANT-SPECIFIC EVER APPEARS HERE (D27, D30, D92).** The reference holds
a Meesho supplier slug, twenty-seven Drive folder ids and forty-five catalogue ids
in its own source. That cannot ship: this list is the same for every seller (D12),
and what differs per seller -- which reports are switched on (D7), their own folder
ids, their own account -- is the seller's data, entered once and stored. There is a
check below that reads this file and refuses an id, a slug or a folder key.

**THE FIELDS THAT ARE NOT DECORATION**, each paid for by a real failure:

  door             `api` or `browser`. Classes B, and most of A and C, do not
                   exist on the API side at all.
  owes_previous_day  A run today fetches YESTERDAY's data. Confusing the run date
                   with the data date means retrying the wrong day for ever.
  cannot_backfill  A sentence, or None, shown to the seller. **A report whose
                   past cannot be asked for at all** -- a picture of how things
                   stand now, or a rolling window the platform chooses.
                   **MEESHO PAYMENTS IS NOT ONE OF THEM AND USED TO BE LISTED AS
                   ONE (D132).** What was really measured is narrower: an UNDATED
                   daily fetch hands back whatever the current settlement batch
                   is. That is true, and it says nothing about whether a period
                   can be ASKED for -- which it can. A re-fetch that quietly
                   returns the wrong day is still worse than a refusal, and that
                   is what `owes_previous_day` and the day board are for.
  needs_a_person   A report that cannot run unattended says so. `fk_keywords`
                   waits five minutes for somebody to navigate to a page and then
                   fails; it has produced 11 files in 30 days. Naming it is what
                   lets the board stop counting it as a nightly failure.
  depends_on       Rule 10. A dependent report says "blocked by X", never its own
                   error. Six of the seven ad reports read a campaign list the
                   seventh produces; when that one fails, one cause is reported as
                   six failures.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple

# How often a report is fetched.
DAILY = "daily"
EVERY_THREE_DAYS = "every-three-days"
ONLY_WHEN_ASKED = "only-when-asked"
# **WHEN THE PLATFORM ITSELF PUBLISHES ONE, and no oftener (cycle 46, R2#7).**
#
# Amazon schedules settlement reports on its own cycle -- roughly a fortnight --
# and there is no way to ask for one. Declared `daily`, the board expected one
# every single day, every day without one read as missing, the days-late clock
# ticked up, and **the alarm could never be cleared, because nothing was ever
# going to arrive for that day.**
#
# **An alarm nobody can clear is an alarm everybody mutes**, and then the one
# that matters goes unread with it. That is the whole cost D108 is written
# against.
#
# It is NOT `only-when-asked`: those are left off the board entirely because
# nothing fetches them. These ARE fetched, every night, by looking for a new one
# -- so they belong on the board, and a day the platform published nothing is a
# day with nothing owed rather than a day that is late.
WHEN_THEY_PUBLISH_IT = "when-they-publish-it"
EVERY = (DAILY, EVERY_THREE_DAYS, ONLY_WHEN_ASKED, WHEN_THEY_PUBLISH_IT)

# Which door it comes through. The whole point of the design (D100).
API = "api"
BROWSER = "browser"
DOORS = (API, BROWSER)

PLATFORMS = ("flipkart", "meesho", "amazon")


@dataclass(frozen=True)
class Report:
    """One report. Frozen, because a list that anything can edit is not one list.

    The reference's job objects were plain mutable objects and a backfill tool
    mutated one in place; the next job in the same run read the mutation. Frozen
    is not tidiness -- it is that fault made impossible.
    """

    id: str
    platform: str
    name: str
    door: str
    every: str
    extension: str
    # A run today fetches yesterday's data. Almost all of them do.
    owes_previous_day: bool = True
    # None means it CAN be re-fetched. A string is the reason it cannot, in words
    # a person reads -- never a bare False, which tells nobody why.
    cannot_backfill: Optional[str] = None
    # Reports this one cannot run without. Rule 10.
    depends_on: Tuple[str, ...] = field(default_factory=tuple)
    # It needs somebody sitting there. Almost nothing should be this.
    needs_a_person: bool = False


def why_report_is_refused(report) -> Optional[str]:
    """What is wrong with a report entry, in words, or None.

    **ASKED OF EVERY ENTRY BY A CHECK, so a bad one cannot ship.** The reference
    had a report whose Drive folder id was the literal string `PLACEHOLDER` for
    weeks; the job ran, "succeeded", and uploaded into nowhere. A list nothing
    validates is a list that quietly contains that.
    """
    if not isinstance(report, Report):
        return "That is not a report entry."
    if not report.id:
        return "A report has to have an id."
    if report.id != report.id.lower() or " " in report.id:
        return f"{report.id!r} is not a usable id -- lower case, no spaces."
    if report.platform not in PLATFORMS:
        return f"{report.id}: {report.platform!r} is not a platform Kartaan knows."
    if report.door not in DOORS:
        return f"{report.id}: {report.door!r} is not a door. It is {API!r} or {BROWSER!r}."
    if report.every not in EVERY:
        return f"{report.id}: {report.every!r} is not how often anything runs."
    if not report.name:
        return f"{report.id}: a report needs a name somebody can read."
    if not report.extension or report.extension.startswith("."):
        return f"{report.id}: the extension is written without its dot -- 'csv', not '.csv'."
    # **A REFUSAL WITHOUT A REASON IS THE THING THIS FIELD EXISTS TO PREVENT.**
    if report.cannot_backfill is not None and not str(report.cannot_backfill).strip():
        return (
            f"{report.id}: says it cannot be re-fetched and does not say why. "
            "The reason is the whole point of the field."
        )
    if report.id in report.depends_on:
        return f"{report.id}: cannot depend on itself."
    return None


# --------------------------------------------------------------- the list


# **THE SNAPSHOT REPORTS, and why they are marked rather than just left alone.**
# A catalogue export and a views scrape are pictures of RIGHT NOW. There is no
# history to ask for, so "re-fetch me the 3rd" cannot be honoured by anybody -- and
# a re-fetch that silently returns today's picture under the 3rd's name is the
# Class E fault that put eleven unreadable files into Drive.
_SNAPSHOT = (
    "This is a picture of how things stand right now. The platform keeps no "
    "history to ask for, so a past day cannot be fetched again -- only the day it "
    "was taken."
)

# **WHAT USED TO BE HERE WAS UNTRUE, AND IT WAS SHOWN TO SELLERS (D132).**
#
# `_MEESHO_PAYMENTS` said Meesho "ignores the date range and always hands back
# the current settlement batch" and that "a past day cannot be fetched again".
# **His own Drive disproves it**: `05_2026.xlsx` holds 879 rows covering April
# AND May, downloaded well after both months ended. The portal offers a custom
# range and honours it.
#
# **The observation behind the sentence was real; the rule taken from it was
# not.** What was measured is that an UNDATED daily fetch returns the current
# batch -- re-measured on his 96 real payment files, eight groups of
# byte-identical files and every group consecutive days, because Meesho settles
# in batches. Nothing in that touched the question of asking for a period, and it
# was written into the log as proven anyway.
#
# So Meesho payments carries no such sentence, and a seller asking for a past
# period is asking for something real.

REPORTS: Tuple[Report, ...] = (
    # ---- Flipkart. Its Seller API exists; the application is not live, so these
    # ---- are on the browser door until it is. Moving one is one word.
    Report("fk_orders", "flipkart", "Flipkart orders", BROWSER, DAILY, "xlsx"),
    Report("fk_returns", "flipkart", "Flipkart returns", BROWSER, DAILY, "csv"),
    Report("fk_payments", "flipkart", "Flipkart payments", BROWSER, DAILY, "xlsx"),
    Report("fk_claims", "flipkart", "Flipkart claims", BROWSER, DAILY, "xlsx"),
    Report("fk_views", "flipkart", "Flipkart listing traffic", BROWSER, DAILY, "xlsx"),
    Report(
        "fk_keywords",
        "flipkart",
        "Flipkart search keywords",
        BROWSER,
        DAILY,
        "csv",
        cannot_backfill=_SNAPSHOT,
        # It waits for a person to navigate to a page. In thirty days it produced
        # eleven files. **Named, so the board stops reporting it as a nightly
        # failure and starts reporting it as a report that needs somebody.**
        needs_a_person=True,
    ),
    Report(
        "fk_listings",
        "flipkart",
        "Flipkart listings",
        BROWSER,
        EVERY_THREE_DAYS,
        "xls",
        cannot_backfill=_SNAPSHOT,
    ),
    # The seven ad reports. Six of them read a campaign list the daily one
    # produces -- so they DECLARE that, and one cause shows as one problem.
    Report("fk_ads_daily", "flipkart", "Flipkart ads, by day", BROWSER, DAILY, "csv"),
    Report("fk_ads_fsn", "flipkart", "Flipkart ads, by product", BROWSER, DAILY, "csv",
           depends_on=("fk_ads_daily",)),
    Report("fk_ads_placements", "flipkart", "Flipkart ads, where they showed", BROWSER, DAILY, "csv",
           depends_on=("fk_ads_daily",)),
    Report("fk_ads_overall", "flipkart", "Flipkart ads, overall", BROWSER, DAILY, "csv",
           depends_on=("fk_ads_daily",)),
    Report("fk_ads_search", "flipkart", "Flipkart ads, search terms", BROWSER, DAILY, "csv",
           depends_on=("fk_ads_daily",)),
    Report("fk_ads_orders", "flipkart", "Flipkart ads, orders won", BROWSER, DAILY, "csv",
           depends_on=("fk_ads_daily",)),
    Report("fk_ads_kw", "flipkart", "Flipkart ads, keywords", BROWSER, DAILY, "csv",
           depends_on=("fk_ads_daily",)),
    # ---- Meesho. No public API and Akamai in front of the portal, so the browser
    # ---- door is not a staging post here -- it is where these live until Meesho
    # ---- says otherwise.
    Report("me_orders", "meesho", "Meesho orders", BROWSER, DAILY, "csv"),
    Report(
        "me_returns",
        "meesho",
        "Meesho returns",
        BROWSER,
        DAILY,
        "csv",
        cannot_backfill=(
            "Meesho exports whatever is in the Delivered tab now, with no date "
            "range to ask for. Overlapping days are expected and are settled by "
            "the tracking number."
        ),
    ),
    # **`xlsx`, NOT `zip`, and that is what his own files say.** Eighty-four of
    # his ninety-five real payment exports are a plain spreadsheet; the other
    # eleven are a zip with one spreadsheet inside, and the door unwraps those on
    # the way in. So what lands is always a spreadsheet, and the name says so.
    Report("me_payments", "meesho", "Meesho payments", BROWSER, DAILY, "xlsx"),
    Report("me_claims", "meesho", "Meesho claims", BROWSER, DAILY, "csv",
           cannot_backfill=(
               "Meesho exports a rolling window rather than a chosen day. "
               "Overlapping days are expected and are settled by the ticket number."
           )),
    Report("me_catalog", "meesho", "Meesho catalogue and stock", BROWSER, DAILY, "xlsx",
           cannot_backfill=_SNAPSHOT),
    Report("me_views", "meesho", "Meesho views", BROWSER, DAILY, "csv",
           cannot_backfill=_SNAPSHOT),
    Report("me_ads", "meesho", "Meesho ads", BROWSER, DAILY, "xlsx"),
    # ---- Amazon. **The one platform already approved and documented, with no
    # ---- browser anywhere near it.** This is the report the whole spine gets
    # ---- proven on, precisely because nothing is built there yet and so nothing
    # ---- can break by being touched.
    Report("az_orders", "amazon", "Amazon orders", API, DAILY, "csv"),
    # **AMAZON MAKES THIS ONE ITSELF AND THERE IS NO WAY TO ASK FOR IT.** Its own
    # documentation: settlement reports cannot be requested. So a day it did not
    # publish one is not a day anybody is owed anything.
    Report("az_settlements", "amazon", "Amazon settlements", API, WHEN_THEY_PUBLISH_IT, "csv"),
    Report("az_returns", "amazon", "Amazon returns", API, DAILY, "csv"),
)


BY_ID = {r.id: r for r in REPORTS}


def report(report_id: str) -> Report:
    """One report by its id, or a refusal naming it.

    **REFUSES RATHER THAN ANSWERING None.** A lookup that answers nothing for an
    id nobody knows lets a typo travel: the reference had a job list and a
    manifest slot list keyed separately, and a slot naming a job that did not
    exist read as "missing" for ever with nothing to explain it.
    """
    found = BY_ID.get(report_id)
    if found is None:
        raise KeyError(f"{report_id!r} is not a report Kartaan knows about.")
    return found


def on_the_browser_door() -> Tuple[Report, ...]:
    """Every report that still needs a browser. The number that should fall."""
    return tuple(r for r in REPORTS if r.door == BROWSER)


def on_the_api_door() -> Tuple[Report, ...]:
    """Every report that can be fetched with nobody present.

    **THIS IS WHAT THE SCHEDULED JOB IS ALLOWED TO TRY, and it is asked here
    rather than worked out by whoever is asking.** The job runs in GitHub Actions
    and the browser is on the seller's own desk (D107) -- those two cannot reach
    each other, so a job that helped itself to the whole list would spend every
    night failing on twenty-one reports it was never able to fetch, and the log
    would say the platform was broken.

    Written beside its twin on purpose. Each caller filtering the list itself is
    a second copy of one fact, and the day a report moves from `browser` to `api`
    -- which D100 says is one word -- the copy that nobody remembered is the one
    that goes on being wrong.
    """
    return tuple(r for r in REPORTS if r.door == API)


def blocked_by(report_id: str, failed_ids) -> Optional[str]:
    """Which of this report's dependencies failed, or None. Rule 10.

    **THE POINT IS THAT ONE CAUSE SHOWS AS ONE PROBLEM.** Six ad reports failing
    because the campaign list did not arrive is one failure, not seven, and a
    board that counts seven tells nobody how many things are actually wrong.
    """
    failed = set(failed_ids or ())
    stopped = [d for d in report(report_id).depends_on if d in failed]
    if not stopped:
        return None
    return ", ".join(stopped)
