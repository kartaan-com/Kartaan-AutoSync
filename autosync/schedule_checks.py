"""Checks for what is owed and when it is late.

**THE CENTRAL CHECK IN THIS FILE REPRODUCES THE REFERENCE'S WORST FAULT WITH ITS
REAL DATES AND MAKES THE NEW CODE ANSWER CORRECTLY WHERE THE OLD ONE DID NOT.**
Not an invented example: `fk_orders` owed 2026-08-09, handed off on 08-10, and
still reporting "day 2" on 08-24 -- fifteen calendar days stuck, never escalated,
because its counter only moved on days something actually ran.

Run: python autosync/schedule_checks.py
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import schedule as tool  # noqa: E402
from landing import Arrived  # noqa: E402
from reports import DAILY, EVERY_THREE_DAYS, ONLY_WHEN_ASKED, WHEN_THEY_PUBLISH_IT, Report, BROWSER, REPORTS  # noqa: E402

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


DAY = lambda s: date.fromisoformat(s)  # noqa: E731

ORDERS = Report("me_orders", "meesho", "Meesho orders", BROWSER, DAILY, "csv")
SNAPSHOT = Report("me_catalog", "meesho", "Meesho catalogue", BROWSER, DAILY, "xlsx",
                  cannot_backfill="a picture of right now")
SLOW = Report("fk_listings", "flipkart", "Flipkart listings", BROWSER, EVERY_THREE_DAYS, "xls")
ASKED = Report("fk_extra", "flipkart", "Only when asked", BROWSER, ONLY_WHEN_ASKED, "csv")
SAME_DAY = Report("me_views", "meesho", "Meesho views", BROWSER, DAILY, "csv", owes_previous_day=False)

# ------------------------------------------- the run date is not the data date

check(
    "a run today is fetching yesterday's data",
    answered(lambda: tool.data_date_for(ORDERS, DAY("2026-08-27")) == DAY("2026-08-26")),
)
check(
    "unless the report says otherwise",
    answered(lambda: tool.data_date_for(SAME_DAY, DAY("2026-08-27")) == DAY("2026-08-27")),
)
# The reference retried the wrong day for ever by confusing these two.
check(
    "and the two answers are genuinely different",
    answered(lambda: tool.data_date_for(ORDERS, DAY("2026-08-27")) != tool.data_date_for(SAME_DAY, DAY("2026-08-27"))),
)

# ------------------------------------------------- THE FAULT THIS FILE IS FOR

# **THE REAL CASE, WITH ITS REAL DATES.** fk_orders owed 2026-08-09. On 2026-08-24
# the reference was still calling it "day 2" and had never escalated it.
OWED = DAY("2026-08-09")
ON_THE_24TH = DAY("2026-08-24")

check(
    "data owed on the 9th is fifteen days late on the 24th",
    answered(lambda: tool.days_late(OWED, ON_THE_24TH) == 15),
)
check(
    "and fifteen days late is long past the point of asking a person",
    answered(lambda: tool.should_ask_a_person(OWED, ON_THE_24TH) is True),
)
# **THE PROPERTY THAT MAKES IT IMPOSSIBLE TO REGRESS: the answer cannot be
# influenced by how many times anything was tried, because there is nowhere to
# put that.** The reference's equivalent took an attempt count and a run history.
check(
    "how late something is takes only the two dates -- there is nothing to pass that could stop the clock",
    answered(lambda: tool.days_late.__code__.co_argcount == 2),
)

# The other two real ones, same fault.
check(
    "fk_payments owed 2026-08-05 is nineteen days late on the 24th",
    answered(lambda: tool.days_late(DAY("2026-08-05"), ON_THE_24TH) == 19),
)
check(
    "and it is asking for a person, not reporting day 2",
    answered(lambda: tool.should_ask_a_person(DAY("2026-08-05"), ON_THE_24TH) is True),
)

# The ordinary end of the same scale.
check("owed today is nought days late", answered(lambda: tool.days_late(DAY("2026-08-27"), DAY("2026-08-27")) == 0))
check("owed today does not ask for a person", answered(lambda: tool.should_ask_a_person(DAY("2026-08-27"), DAY("2026-08-27")) is False))
check("three days late still does not", answered(lambda: tool.should_ask_a_person(DAY("2026-08-24"), DAY("2026-08-27")) is False))
check("four days late does", answered(lambda: tool.should_ask_a_person(DAY("2026-08-23"), DAY("2026-08-27")) is True))
# A date in the future is not "minus one day late", which would read as fine from
# the wrong direction.
check(
    "a date in the future is nought, never a negative",
    answered(lambda: tool.days_late(DAY("2026-09-01"), DAY("2026-08-27")) == 0),
)
check("the limit can be set for a report that deserves longer", answered(lambda: tool.should_ask_a_person(DAY("2026-08-23"), DAY("2026-08-27"), limit=10) is False))

# ---------------------------------------------------------------- what is due

check("a daily report with nothing yet is due", answered(lambda: tool.is_due(ORDERS, DAY("2026-08-26"), []) is True))
check(
    "and is not due once that day has arrived",
    answered(lambda: tool.is_due(ORDERS, DAY("2026-08-26"), [DAY("2026-08-26")]) is False),
)
# **ASKED OF WHAT ARRIVED, not of what a job said.** Another day arriving does not
# settle this day.
check(
    "another day arriving does not make this day arrive",
    answered(lambda: tool.is_due(ORDERS, DAY("2026-08-26"), [DAY("2026-08-25"), DAY("2026-08-24")]) is True),
)
check("a report that only runs when asked is never due by itself", answered(lambda: tool.is_due(ASKED, DAY("2026-08-26"), []) is False))
check(
    "a three-day report is due when nothing arrived in its window",
    answered(lambda: tool.is_due(SLOW, DAY("2026-08-26"), [DAY("2026-08-20")]) is True),
)
check(
    "and is not due when something did",
    answered(lambda: tool.is_due(SLOW, DAY("2026-08-26"), [DAY("2026-08-25")]) is False),
)

# ------------------------------------------- the ends nothing else reaches

# **AN `every` NOBODY KNOWS IS NOT DUE.** The report list refuses one, so this is
# only reachable by building a Report by hand -- which a future door adapter can
# do. Answering "due" for a frequency nothing understands would queue a report
# every single day for ever.
UNKNOWN = Report("x", "meesho", "x", BROWSER, "every-full-moon", "csv")
check("a report whose frequency nothing understands is not due", answered(lambda: tool.is_due(UNKNOWN, DAY("2026-08-26"), []) is False))
check("not even when nothing has ever arrived for it", answered(lambda: tool.is_due(UNKNOWN, DAY("2026-08-26"), [DAY("2026-01-01")]) is False))

# An owed row is frozen for the same reason a report is: one list, not one anything
# can edit underneath whoever is reading it.
frozen = tool.Owed("me_orders", DAY("2026-08-26"), 1, False)
was_refused = False
try:
    frozen.days_late = 99
except AttributeError:
    was_refused = True
check("an owed row cannot be edited after it is made", answered(lambda: was_refused is True))

# **THE ROW READS DIFFERENTLY ON THE DAY IT IS OWED.** "0 days late" reads as a
# fault; "owed today" reads as the ordinary state, and they are different facts.
check(
    "a row owed today says so rather than reporting nought days late",
    answered(lambda: str(tool.Owed("me_orders", DAY("2026-08-26"), 0, False)) == "me_orders for 2026-08-26 -- owed today"),
)
check(
    "and a late one says how late",
    answered(lambda: "3 days late" in str(tool.Owed("me_orders", DAY("2026-08-23"), 3, False))),
)

# ------------------------------------------------------------- what is owed

def arrivals(days):
    """What is really in a folder, as the day board reads it.

    **RECORDS, NOT DATES.** This handed back bare dates once, while the board
    handed back files -- one argument name, two contracts. A caller giving one to
    the other believed nothing had ever arrived and re-fetched every day for ever.
    Found by wiring the runner up. `days_that_arrived` is the one translator now,
    so these checks go through the same door everything else does.
    """
    files = [Arrived(f"x_{d.isoformat()}.csv", 900) for d in days]
    return lambda _report_id: files


everything_missing = tool.what_is_owed([ORDERS], arrivals([]), DAY("2026-08-27"), look_back_days=5)
check("a report with nothing at all owes every day in the window", answered(lambda: len(everything_missing) == 5))
check("oldest first", answered(lambda: everything_missing[0].data_date < everything_missing[-1].data_date))
check("and each one says how late it is", answered(lambda: everything_missing[0].days_late == 5))
check(
    "the oldest is asking for a person and the newest is not",
    answered(lambda: everything_missing[0].ask_a_person is True and everything_missing[-1].ask_a_person is False),
)

nothing_owed = tool.what_is_owed(
    [ORDERS],
    arrivals([DAY(f"2026-08-{d:02d}") for d in range(20, 27)]),
    DAY("2026-08-27"),
    look_back_days=5,
)
check("a report that is up to date owes nothing", answered(lambda: nothing_owed == []))

# **AN EMPTY FILE IS NOT A DAY THAT ARRIVED.** Counted, it would stop its day ever
# being fetched again -- the quietest possible way to lose a day for good.
empty_file = lambda _r: [Arrived("x_2026-08-26.csv", 0)]
still_owed = tool.what_is_owed([ORDERS], empty_file, DAY("2026-08-27"), look_back_days=1)
check("a file of nothing leaves its day still owed", answered(lambda: len(still_owed) == 1))
check("and it is that very day", answered(lambda: still_owed[0].data_date == DAY("2026-08-26")))
# A file with no date in its name settles nothing either -- it is the third state.
undated_file = lambda _r: [Arrived("meesho_payments.xlsx", 900)]
check("and a file with no date in its name settles no day at all",
      answered(lambda: len(tool.what_is_owed([ORDERS], undated_file, DAY("2026-08-27"), look_back_days=1)) == 1))

# **A REPORT THAT CANNOT BE RE-FETCHED IS NOT LISTED AS OWED FOR A PAST DAY.**
# Listing it would put a permanent un-actionable row on the board for every day it
# was ever missed, which is how a board stops being read.
snapshot_owed = tool.what_is_owed([SNAPSHOT], arrivals([]), DAY("2026-08-27"), look_back_days=30)
check("a snapshot report owes only its most recent day", answered(lambda: len(snapshot_owed) == 1))
check("and that day is yesterday, not a month of them", answered(lambda: snapshot_owed[0].data_date == DAY("2026-08-26")))

# Rule 10 travels onto the row.
blocked = tool.what_is_owed(
    [ORDERS], arrivals([]), DAY("2026-08-27"), look_back_days=1, blocked={"me_orders": "fk_ads_daily"}
)
check("an owed row carries what is blocking it", answered(lambda: blocked[0].blocked_by == "fk_ads_daily"))
check("and says so when it is read out", answered(lambda: "blocked by fk_ads_daily" in str(blocked[0])))
check(
    "one that is not blocked says nothing about blocking",
    answered(lambda: "blocked" not in str(tool.what_is_owed([ORDERS], arrivals([]), DAY("2026-08-27"), look_back_days=1)[0])),
)

# ------------------------------------------------- two orderings, named apart

mixed = tool.what_is_owed([ORDERS], arrivals([]), DAY("2026-08-27"), look_back_days=4)
check("worst first really is the most overdue first", answered(lambda: tool.worst_first(mixed)[0].days_late == 4))
check("and oldest first is unchanged by it", answered(lambda: mixed[0].days_late == 4))
check(
    "the two orderings are different objects, so neither can quietly reorder the other",
    answered(lambda: tool.worst_first(mixed) is not mixed),
)

# **THE ORDER IS BY DAY ACROSS ALL REPORTS, not report by report.** Built without
# sorting, every day of the first report would come before the first day of the
# second -- so a person working the list oldest-first would do one report's whole
# backlog before touching another's older one.
SECOND = Report("fk_orders", "flipkart", "Flipkart orders", BROWSER, DAILY, "xlsx")
two = tool.what_is_owed([ORDERS, SECOND], arrivals([]), DAY("2026-08-27"), look_back_days=2)
check("two reports owing the same days are interleaved by day", answered(lambda: [o.report_id for o in two] == ["fk_orders", "me_orders", "fk_orders", "me_orders"]))
check("and strictly oldest day first", answered(lambda: [o.data_date for o in two] == [DAY("2026-08-25"), DAY("2026-08-25"), DAY("2026-08-26"), DAY("2026-08-26")]))

# --------------------------------------------- it holds against the real list

real = tool.what_is_owed(list(REPORTS), arrivals([]), DAY("2026-08-27"), look_back_days=3)
check("the whole real report list can be asked what it owes", answered(lambda: len(real) > 0))
check(
    "and every snapshot report in it owes exactly one day",
    answered(lambda: all(
        len([o for o in real if o.report_id == r.id]) == 1
        for r in REPORTS
        if r.cannot_backfill is not None and r.every != ONLY_WHEN_ASKED
    )),
)
check(
    "while a report that can be re-fetched owes the whole window",
    answered(lambda: len([o for o in real if o.report_id == "me_orders"]) == 3),
)


# ------------------------------ a person naming the days themselves

# **HIS ASK, 2026-08-28:** the catching-up already chases a missed day, but it can
# chase one for days and still not get it. When that happens he has to be able to
# name the day himself and have it fetched NOW, rather than waiting on a system
# that is already not working.
BY_HAND, WHY_NOT = answered(lambda: tool.asked_for_by_hand(
    REPORTS, ["me_orders"], DAY("2026-08-25"), DAY("2026-08-27"), DAY("2026-08-28"))) or ([], [])
check("three days asked for by hand are three days to fetch",
      answered(lambda: len(BY_HAND) == 3))
check("and they are the days that were asked for, not yesterday",
      answered(lambda: [o.data_date for o in BY_HAND]
               == [DAY("2026-08-25"), DAY("2026-08-26"), DAY("2026-08-27")]))
check("oldest first, the same as everything else",
      answered(lambda: BY_HAND == sorted(BY_HAND, key=lambda o: (o.data_date, o.report_id))))
# **AND THE CASE THAT TELLS THE ORDER APART IS TWO REPORTS, NOT ONE.** Asked for
# one report, the days come out in order whether anything sorts them or not --
# so the check above could not fail. Asked for two, an unsorted answer is every
# day of the first report and then every day of the second, and a run cut short
# would have fetched all of one and none of the other.
TWO_BY_HAND, _ = answered(lambda: tool.asked_for_by_hand(
    REPORTS, ["me_orders", "me_payments"],
    DAY("2026-08-25"), DAY("2026-08-27"), DAY("2026-08-28"))) or ([], [])
check("two reports asked for by hand are interleaved by day, not one after the other",
      answered(lambda: [o.data_date for o in TWO_BY_HAND]
               == sorted(o.data_date for o in TWO_BY_HAND)))
check("and both reports are really in it",
      answered(lambda: len({o.report_id for o in TWO_BY_HAND}) == 2))
check("nothing was refused", answered(lambda: WHY_NOT == []))
# **IT STILL SAYS HOW LATE EACH ONE IS**, because the log and the board read that
# from the record rather than working it out again.
check("and each one still knows how late it is",
      answered(lambda: [o.days_late for o in BY_HAND] == [3, 2, 1]))
# **BUT NOBODY IS CHASED ABOUT A DAY THEY JUST ASKED FOR THEMSELVES.**
check("and nobody is told to look at a day the person just asked for",
      answered(lambda: not any(o.ask_a_person for o in BY_HAND)))

# **ONE DAY IS A RANGE OF ONE**, which is the ordinary case: one day went wrong.
check("one day is asked for as itself",
      answered(lambda: len(tool.asked_for_by_hand(
          REPORTS, ["me_orders"], DAY("2026-08-26"), DAY("2026-08-26"), DAY("2026-08-28"))[0]) == 1))

# **A REPORT THAT CAN ONLY EVER BE CAUGHT ON THE DAY IS REFUSED, AND SAYS WHY.**
# Meesho's payments export ignores the range it is given and hands back the
# current settlement batch -- so asking for last Tuesday produces today's file
# wearing last Tuesday's name. That is worse than nothing, and it is what put
# three wrongly-dated files in the reference's Drive.
CANNOT = [r.id for r in REPORTS if r.cannot_backfill is not None]
_, refused = answered(lambda: tool.asked_for_by_hand(
    REPORTS, CANNOT[:1], DAY("2026-08-20"), DAY("2026-08-20"), DAY("2026-08-28"))) or ([], [])
check("a report that can only be caught on the day is refused", answered(lambda: len(refused) == 1))
check("and the refusal is in that report's own words, not a general apology",
      answered(lambda: refused[0].startswith(CANNOT[0]) and len(refused[0]) > len(CANNOT[0]) + 20))
nothing_to_do, _ = answered(lambda: tool.asked_for_by_hand(
    REPORTS, CANNOT[:1], DAY("2026-08-20"), DAY("2026-08-20"), DAY("2026-08-28"))) or ([], [])
check("and nothing is fetched for it", answered(lambda: nothing_to_do == []))

# A day that has not happened yet, and a range that ends before it starts.
_, ahead = answered(lambda: tool.asked_for_by_hand(
    REPORTS, ["me_orders"], DAY("2026-09-30"), DAY("2026-09-30"), DAY("2026-08-28"))) or ([], [])
check("a day that has not happened yet is refused", answered(lambda: len(ahead) == 1))
check("and says so plainly", answered(lambda: "not happened yet" in ahead[0]))
backwards, why = answered(lambda: tool.asked_for_by_hand(
    REPORTS, ["me_orders"], DAY("2026-08-27"), DAY("2026-08-25"), DAY("2026-08-28"))) or ([], [])
check("a range that ends before it starts is refused",
      answered(lambda: backwards == [] and len(why) == 1))
check("and says which way round it was", answered(lambda: "ends before it starts" in why[0]))

# A report nobody has heard of is named rather than skipped.
_, unknown = answered(lambda: tool.asked_for_by_hand(
    REPORTS, ["me_nonsense"], DAY("2026-08-26"), DAY("2026-08-26"), DAY("2026-08-28"))) or ([], [])
check("a report nobody has heard of is refused by name",
      answered(lambda: len(unknown) == 1 and "me_nonsense" in unknown[0]))

# **IT DOES NOT ASK WHETHER THE FILE IS ALREADY THERE.** Somebody naming a day by
# hand has a reason -- usually that what arrived was wrong -- and second-guessing
# that is how a person ends up unable to fix their own data.
check("a day whose file is already there is still fetched when it is asked for",
      answered(lambda: len(tool.asked_for_by_hand(
          REPORTS, ["me_orders"], DAY("2026-08-27"), DAY("2026-08-27"), DAY("2026-08-28"))[0]) == 1))


# **AND NOTHING ABOVE ENDED BY THROWING RATHER THAN BY ANSWERING.** Answering
# with nothing keeps the run alive; this is what stops a check phrased as "this
# word is NOT in what it said" going green because there was nothing to look in.
# ------------------- one the platform publishes on its own cycle (R2#7)

PUBLISHED = tool.Report("az_settlements", "amazon", "Settlements", "api",
                        WHEN_THEY_PUBLISH_IT, "csv")
# **ONE LOOK A NIGHT, not one per day of the window.** There is nothing to
# chase -- the platform publishes when it publishes -- so fourteen looks a night
# would be thirteen calls spent learning the same thing.
PUB_TODAY = DAY("2026-08-29")
looked = answered(lambda: tool.what_is_owed([PUBLISHED], lambda _r: [], PUB_TODAY))
check("a report the platform publishes itself is looked for once a night",
      len(looked) == 1)
check("and it is the most recent day, not a fortnight of them",
      looked[0].data_date == tool.data_date_for(PUBLISHED, PUB_TODAY))
# **AND A DAY ONE ALREADY ARRIVED ON IS NOT LOOKED FOR AGAIN.**
came = Arrived(f"amazon_az_settlements_{tool.data_date_for(PUBLISHED, PUB_TODAY)}.csv", 10)
check("and a day one already arrived on is not looked for again",
      answered(lambda: tool.what_is_owed([PUBLISHED], lambda _r: [came], PUB_TODAY)) == [])

# ------------------- oldest first, and it is not decoration

# **THE OLDEST OWED DAY IS FETCHED FIRST.** A run can be cut short by anything --
# a sign-in prompt, the machine being shut, the hour running out -- and whatever
# it did not reach is what the next run starts with. Fetched newest first, the
# oldest day is the one that never gets reached, and it is the one closest to
# falling out of the window for good.
MANY = [ORDERS, tool.Report("me_payments", "meesho", "Payments", BROWSER, DAILY, "xlsx")]
owed_in_order = answered(lambda: tool.what_is_owed(MANY, lambda _r: [], DAY("2026-08-29"),
                                                   look_back_days=3))
check("what is owed comes back oldest first",
      [one.data_date for one in owed_in_order]
      == sorted(one.data_date for one in owed_in_order))
# **AND TWO REPORTS OWED FOR ONE DAY COME BACK IN A SETTLED ORDER**, so a run
# that stops half way through a day stops in a knowable place rather than a
# different one every night.
same_day = [one.report_id for one in owed_in_order
            if one.data_date == owed_in_order[0].data_date]
check("and two reports owed for one day come back in a settled order",
      same_day == sorted(same_day))

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)


EXPECTED = 70
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
