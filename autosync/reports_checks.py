"""Checks for the report list.

**THE ONE THAT MATTERS MOST READS THIS FILE'S OWN SOURCE.** The working reference
holds a Meesho supplier slug, twenty-seven Drive folder ids and forty-five
catalogue ids directly in `config.js`. That is one seller's business baked into a
product that ships to every seller (D27, D30, D92). A rule nobody can check is a
rule that comes back, so this one is checked by reading the bytes.

Run: python autosync/reports_checks.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reports as tool  # noqa: E402

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
    """Did it refuse? A refusal is an answer; a crash of another kind is not."""
    try:
        fn()
    except (ValueError, KeyError, TypeError, AttributeError):
        # A frozen dataclass refuses with FrozenInstanceError, which is an
        # AttributeError. Named here rather than caught as bare Exception, so a
        # refusal is still told apart from the code falling over some other way.
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


# ------------------------------------------------------- every entry is sound

for entry in tool.REPORTS:
    wrong = tool.why_report_is_refused(entry)
    check(f"{entry.id} is a usable entry", answered(lambda: wrong is None))

# **THE EXACT LIST, WRITTEN OUT.** Not a count -- a count taken from the list it
# is checking moves with it, so an entry disappearing looks like the list simply
# being shorter. The prover found exactly that: deleting `fk_orders` was noticed
# by nothing. This is the contract both doors and the board are built against, and
# a report leaving it silently is the whole failure it exists to prevent.
EVERY_ID = (
    "fk_orders", "fk_returns", "fk_payments", "fk_claims", "fk_views", "fk_keywords",
    "fk_listings", "fk_ads_daily", "fk_ads_fsn", "fk_ads_placements", "fk_ads_overall",
    "fk_ads_search", "fk_ads_orders", "fk_ads_kw",
    "me_orders", "me_returns", "me_payments", "me_claims", "me_catalog", "me_views",
    "me_ads", "me_ads_summary", "me_ads_catalog",
    "az_orders", "az_settlements", "az_returns",
)
check("the report list is exactly what it is meant to be", answered(lambda: tuple(r.id for r in tool.REPORTS) == EVERY_ID))
check("there are reports at all", answered(lambda: len(tool.REPORTS) == len(EVERY_ID)))
check("no id is used twice", answered(lambda: len({r.id for r in tool.REPORTS}) == len(tool.REPORTS)))
check("no name is used twice", answered(lambda: len({r.name for r in tool.REPORTS}) == len(tool.REPORTS)))

# --------------------------------------------- nothing of one seller's is here

SOURCE = Path(tool.__file__).read_text(encoding="utf-8")

# **THE REAL VALUES OUT OF THE REFERENCE.** Checked against the actual strings
# that are in its config.js today, not against an invented example -- a rule
# proven against an invention proves the invention.
check(
    "the Meesho supplier slug is not in here",
    answered(lambda: "xuptj" not in SOURCE),
)
check(
    "no Google Drive folder id is in here",
    # A Drive folder id: a long run of id characters. The reference has 27.
    answered(lambda: not re.search(r"['\"][A-Za-z0-9_-]{25,}['\"]", SOURCE)),
)
check(
    "no seller's own business name is in here",
    answered(lambda: "rumee" not in SOURCE.lower()),
)
check(
    "and no email address of anybody's",
    answered(lambda: not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", SOURCE)),
)
check(
    "and no supplier panel url with somebody's panel in it",
    answered(lambda: "supplier.meesho.com/panel" not in SOURCE),
)

# ------------------------------------------------------------ what is refused

check(
    "an entry with no id is refused",
    answered(lambda: tool.why_report_is_refused(tool.Report("", "meesho", "x", tool.BROWSER, tool.DAILY, "csv")) is not None),
)
# Both halves separately: one case covering two arms cannot tell which arm works.
check(
    "an id with a capital in it is refused",
    answered(lambda: tool.why_report_is_refused(tool.Report("MeOrders", "meesho", "x", tool.BROWSER, tool.DAILY, "csv")) is not None),
)
check(
    "and an id with a space in it is refused",
    answered(lambda: tool.why_report_is_refused(tool.Report("me orders", "meesho", "x", tool.BROWSER, tool.DAILY, "csv")) is not None),
)
check(
    "while an ordinary id is accepted",
    answered(lambda: tool.why_report_is_refused(tool.Report("me_orders", "meesho", "x", tool.BROWSER, tool.DAILY, "csv")) is None),
)
check(
    "a frequency nobody knows is refused",
    answered(lambda: tool.why_report_is_refused(tool.Report("x", "meesho", "x", tool.BROWSER, "every-full-moon", "csv")) is not None),
)
check(
    "a report with no name anybody can read is refused",
    answered(lambda: tool.why_report_is_refused(tool.Report("x", "meesho", "", tool.BROWSER, tool.DAILY, "csv")) is not None),
)
check(
    "a platform nobody knows is refused",
    answered(lambda: tool.why_report_is_refused(tool.Report("x", "etsy", "x", tool.BROWSER, tool.DAILY, "csv")) is not None),
)
check(
    "a door that is neither api nor browser is refused",
    answered(lambda: tool.why_report_is_refused(tool.Report("x", "meesho", "x", "magic", tool.DAILY, "csv")) is not None),
)
check(
    "an extension written with its dot is refused",
    answered(lambda: tool.why_report_is_refused(tool.Report("x", "meesho", "x", tool.BROWSER, tool.DAILY, ".csv")) is not None),
)
# **A REFUSAL WITHOUT A REASON IS THE FAULT THE FIELD EXISTS TO PREVENT.**
no_reason = tool.why_report_is_refused(
    tool.Report("x", "meesho", "x", tool.BROWSER, tool.DAILY, "csv", cannot_backfill="  ")
)
check("saying it cannot be re-fetched without saying why is refused", answered(lambda: no_reason is not None))
# **THE REFUSAL HAS TO SAY WHAT IS WRONG.** Asking only whether it refused leaves
# the message free to say anything at all -- and the message is the whole value of
# the field, since whoever reads it is deciding whether to go and fetch a day by
# hand.
check("and the refusal says that the reason is the point of the field", answered(lambda: "does not say why" in no_reason))
check(
    "and saying why is accepted",
    answered(lambda: tool.why_report_is_refused(
        tool.Report("x", "meesho", "x", tool.BROWSER, tool.DAILY, "csv", cannot_backfill="the portal ignores the range")
    ) is None),
)
check(
    "a report that depends on itself is refused",
    answered(lambda: tool.why_report_is_refused(
        tool.Report("x", "meesho", "x", tool.BROWSER, tool.DAILY, "csv", depends_on=("x",))
    ) is not None),
)
check("something that is not a report at all is refused", answered(lambda: tool.why_report_is_refused({"id": "x"}) is not None))

# ------------------------------------------------------------ the entry is frozen

# A list anything can edit is not one list. The reference's job objects were
# mutable and a backfill tool changed one in place mid-run.
check(
    "a report cannot be edited after it is made",
    answered(lambda: refuses(lambda: setattr(tool.REPORTS[0], "door", tool.API))),
)

# ------------------------------------------------------------ looking one up

check("a report can be looked up by its id", answered(lambda: tool.report("me_orders").platform == "meesho"))
check(
    "an id nobody knows is refused rather than answering nothing",
    answered(lambda: refuses(lambda: tool.report("me_nonsense"))),
)

# ------------------------------------------------- the doors, and what they mean

browser = tool.on_the_browser_door()
check("some reports still need a browser", answered(lambda: len(browser) > 0))
# **EXACTLY THE ONES ON THAT DOOR, and no others.** `len(...) > 0` was true whether
# the filter said `== BROWSER` or `!= BROWSER`, so it could not tell the two
# apart -- and the number on this door falling is how progress is measured.
check("and it is exactly the ones whose door is the browser", answered(lambda: set(browser) == {r for r in tool.REPORTS if r.door == tool.BROWSER}))
check("no report that has an API is on it", answered(lambda: not any(r.door == tool.API for r in browser)))

# **AND ITS TWIN: WHAT CAN BE FETCHED WITH NOBODY PRESENT.** This is what the
# scheduled job in the seller's own GitHub Actions is allowed to try. Asked for
# by hand at each caller instead, the day a report moves from `browser` to `api`
# -- which D100 says is one word -- the copy nobody remembered goes on being
# wrong.
api = tool.on_the_api_door()
check("some reports can be fetched with nobody present", answered(lambda: len(api) > 0))
check("and it is exactly the ones whose door is an API",
      answered(lambda: set(api) == {r for r in tool.REPORTS if r.door == tool.API}))
check("no report that needs a browser is on it",
      answered(lambda: not any(r.door == tool.BROWSER for r in api)))
# **THE TWO DOORS BETWEEN THEM ARE EVERY REPORT, and never the same one twice.**
# A report on neither would simply never be fetched, and nothing would say so.
check("every report is on one door or the other",
      answered(lambda: len(api) + len(browser) == len(tool.REPORTS)))
check("and none is on both", answered(lambda: not set(api) & set(browser)))
check("every Amazon report is left out of it", answered(lambda: not any(r.platform == "amazon" for r in browser)))
check(
    "every Meesho report is on the browser door, because Meesho has no API",
    answered(lambda: all(r.door == tool.BROWSER for r in tool.REPORTS if r.platform == "meesho")),
)
check(
    "every Amazon report is on the API door, because its API is approved and live",
    answered(lambda: all(r.door == tool.API for r in tool.REPORTS if r.platform == "amazon")),
)

# ---------------------------------------- the ones that cannot be fetched again

# **MEESHO PAYMENTS CAN BE FETCHED FOR A PAST PERIOD, AND USED TO SAY IT COULD
# NOT (D132).** His own `05_2026.xlsx` holds 879 rows covering April AND May,
# downloaded after both months ended. What was really measured is narrower -- an
# UNDATED daily fetch hands back the current batch -- and that was generalised
# into a rule and written into the log as proven. **The sentence was shown to
# sellers.**
payments = tool.report("me_payments")
check(
    "Meesho payments does not claim its past cannot be fetched",
    answered(lambda: payments.cannot_backfill is None),
)
check(
    "the catalogue snapshot says it cannot be re-fetched either",
    answered(lambda: tool.report("me_catalog").cannot_backfill is not None),
)
# **NAMED ONE BY ONE.** Every snapshot report says it, and losing the answer on
# any single one of them silently re-opens the Class E fault -- a re-fetch that
# returns today's picture under a past day's name.
check(
    "every report that is only ever a picture of right now says so",
    answered(lambda: all(
        tool.report(rid).cannot_backfill is not None
        for rid in ("me_catalog", "me_views", "fk_keywords", "fk_listings", "me_returns",
                    "me_claims", "me_ads")
    )),
)
check(
    "and every report that can genuinely be fetched again says nothing",
    answered(lambda: all(
        tool.report(rid).cannot_backfill is None
        for rid in ("me_orders", "me_payments", "fk_orders", "fk_payments", "fk_views", "az_orders")
    )),
)
# The default matters: almost every report is fetching yesterday.
check(
    "a report is taken to owe the previous day unless it says otherwise",
    answered(lambda: tool.Report("x", "meesho", "x", tool.BROWSER, tool.DAILY, "csv").owes_previous_day is True),
)
check(
    "and every report in the real list owes the previous day",
    answered(lambda: all(r.owes_previous_day for r in tool.REPORTS)),
)
check(
    "and orders, which genuinely can be, says nothing",
    answered(lambda: tool.report("me_orders").cannot_backfill is None),
)

# ------------------------------------------------- one cause is one problem

check(
    "an ads report that rests on the campaign list says so",
    answered(lambda: "fk_ads_daily" in tool.report("fk_ads_fsn").depends_on),
)
check(
    "and the campaign list itself rests on nothing",
    answered(lambda: tool.report("fk_ads_daily").depends_on == ()),
)
check(
    "when the campaign list fails, a report resting on it is blocked BY IT",
    answered(lambda: tool.blocked_by("fk_ads_fsn", ["fk_ads_daily"]) == "fk_ads_daily"),
)
check(
    "and when it has not failed, nothing is blocked",
    answered(lambda: tool.blocked_by("fk_ads_fsn", []) is None),
)
check(
    "a report resting on nothing is never reported as blocked",
    answered(lambda: tool.blocked_by("fk_ads_daily", ["fk_ads_daily", "me_orders"]) is None),
)

# ----------------------------------------- a report that needs somebody says so

check(
    "the report that needs a person on the page says so",
    answered(lambda: tool.report("fk_keywords").needs_a_person is True),
)
check(
    "and almost nothing else does",
    answered(lambda: sum(1 for r in tool.REPORTS if r.needs_a_person) == 1),
)


# **A PLAIN NUMBER, not one worked out from the list.** It was
# `len(REPORTS) + 34`, and the prover showed what that costs: deleting a report
# shrank the list AND shrank the expected count with it, so the entry vanishing
# was invisible to the very check meant to notice checks vanishing. A number that
# moves with the thing it measures measures nothing.
# **AND NOTHING ABOVE ENDED BY THROWING RATHER THAN BY ANSWERING.** Answering
# with nothing keeps the run alive; this is what stops a check phrased as "this
# word is NOT in what it said" going green because there was nothing to look in.
# ------------------- a report the platform publishes on its own cycle (R2#7)

# **AMAZON SCHEDULES SETTLEMENT REPORTS ITSELF AND THERE IS NO WAY TO ASK FOR
# ONE** -- its own documentation, and the door says so in its own words.
# Declared `daily`, the board expected one every single day, every day without
# one read as missing, the clock ticked up, and **the alarm could never be
# cleared, because nothing was ever going to arrive for that day.**
check("settlements are not asked for every day",
      answered(lambda: tool.report("az_settlements").every) != tool.DAILY)
check("they arrive when Amazon publishes one",
      answered(lambda: tool.report("az_settlements").every) == tool.WHEN_THEY_PUBLISH_IT)
# **AND THEY ARE STILL ON THE BOARD.** `only-when-asked` would take them off it
# altogether, and a stream nothing watches is a stream nobody notices stopping.
check("and that is not the same as one nobody fetches",
      answered(lambda: tool.report("az_settlements").every) != tool.ONLY_WHEN_ASKED)
check("it is one of the ways a report can be fetched",
      tool.WHEN_THEY_PUBLISH_IT in tool.EVERY)
# The other two Amazon reports ARE asked for every day, so the difference is
# about this one report rather than about the platform.
check("Amazon's orders are still fetched every day",
      answered(lambda: tool.report("az_orders").every) == tool.DAILY)
check("and its returns are too",
      answered(lambda: tool.report("az_returns").every) == tool.DAILY)

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)


EXPECTED = 84
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
