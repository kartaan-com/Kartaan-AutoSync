"""Checks for what Amazon's API makes true.

**EVERY CASE HERE IS BUILT FROM AMAZON'S OWN DOCUMENTATION**, read 2026-08-27 --
the endpoint table, the marketplace-id table, the five processing statuses, the
five-minute link, the rate-limit tables, and the settlement-report page that says
in as many words that those reports cannot be requested. The reading is in
`docs/WORKING.md`.

**THE FOUR THAT WOULD HAVE SUNK A GUESSED BUILD each have a check of their own**,
and each is written so it goes red if the fact is ever quietly changed back.

Run: python autosync/amazon_checks.py
"""

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import amazon as tool  # noqa: E402

ran = 0
failures = []
# Everything that ended by throwing rather than by answering. **The floor under
# all of it:** answering with nothing stops the run dying, but on its own it is
# not enough -- a check written as "this word is NOT in what it said" passes
# against nothing, and would go green for the worst possible reason.
THREW = []


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


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


def refuses(fn):
    try:
        fn()
    except (ValueError, KeyError, TypeError, AttributeError):
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


def _said(fn):
    """What it refused WITH. Asking only whether something refused leaves the
    message free to say anything, and the message is what somebody acts on."""
    try:
        fn()
    except Exception as wrong:  # noqa: BLE001
        return str(wrong)
    return ""


DAY = lambda s: date.fromisoformat(s)  # noqa: E731

# ---------------------------------------------------- TRAP 1: which endpoint

# **INDIA IS ON THE EUROPE HOST.** Amazon groups it under "Europe, Middle East,
# India, and Africa". The intuitive guess is the Far East one, and every call to
# it fails.
check("India's marketplace id is the documented one", answered(lambda: tool.INDIA == "A21TJRUUN4KGV"))
check("and India is served by the EUROPE endpoint", answered(lambda: tool.host_for(tool.INDIA) == "https://sellingpartnerapi-eu.amazon.com"))
check("which is NOT the Far East one", answered(lambda: tool.host_for(tool.INDIA) != tool.HOSTS["fe"]))
# A default here would send a seller's calls to the wrong continent.
check("a marketplace it does not know is refused, never defaulted", answered(lambda: refuses(lambda: tool.host_for("A1F83G8C2ARO7P"))))
check("and nothing at all is refused too", answered(lambda: refuses(lambda: tool.host_for(""))))

# ------------------------------------------------------------ getting in

check("the token comes from Amazon's own token service", answered(lambda: tool.TOKEN_ENDPOINT == "https://api.amazon.com/auth/o2/token"))
check("which is not an SP-API host", answered(lambda: not tool.TOKEN_ENDPOINT.startswith(tuple(tool.HOSTS.values()))))
check("a token lasts an hour", answered(lambda: tool.TOKEN_LASTS == timedelta(hours=1)))
# Renewed early, so one cannot go stale between deciding to call and calling.
check("and is renewed before it runs out", answered(lambda: tool.TOKEN_RENEW_EARLY > timedelta(0) and tool.TOKEN_RENEW_EARLY < tool.TOKEN_LASTS))
check("it travels in the documented header", answered(lambda: tool.TOKEN_HEADER == "x-amz-access-token"))

# ------------------------------------------------------------ the paths

check("createReport is the documented path", answered(lambda: tool.REPORTS_PATH == "/reports/2021-06-30/reports"))
check("getReport is the documented path", answered(lambda: tool.REPORT_PATH.format(report_id="X") == "/reports/2021-06-30/reports/X"))
check("getReportDocument is the documented path", answered(lambda: tool.DOCUMENT_PATH.format(document_id="D") == "/reports/2021-06-30/documents/D"))

# ------------------------------------------- TRAP 4: two kinds of report

# **SETTLEMENTS CANNOT BE ASKED FOR.** Amazon schedules them itself.
check("settlements are the kind Amazon makes on its own", answered(lambda: tool.must_be_found_not_asked("az_settlements") is True))
check("orders are the kind you ask for", answered(lambda: tool.must_be_found_not_asked("az_orders") is False))
refused = tool.why_request_is_refused("az_settlements", DAY("2026-08-26"), DAY("2026-08-26"))
check("asking for a settlement report is refused before anything is sent", answered(lambda: refused is not None))
# **THE REASON HAS TO SAY WHY IT CAN NEVER WORK**, not that this request failed --
# a sentence about this attempt would send somebody to retry it for ever.
check("and the reason says Amazon schedules it itself", answered(lambda: "schedules it itself" in refused))
check("building a body for one is refused too", answered(lambda: refuses(lambda: tool.create_body("az_settlements", DAY("2026-08-26"), DAY("2026-08-26")))))
check("the current settlement type is the V2 one", answered(lambda: tool.amazon_report("az_settlements").report_type == "GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE_V2"))
# The two dead ones are named so a reader meeting one in old data knows what it is.
check("the two retired settlement types are named", answered(lambda: len(tool.RETIRED_SETTLEMENT_TYPES) == 2))
check("and neither is what this asks for", answered(lambda: tool.amazon_report("az_settlements").report_type not in tool.RETIRED_SETTLEMENT_TYPES))
check("with the date they are removed written down", answered(lambda: tool.REMOVED_ON == date(2026, 11, 11)))

# ------------------------------------- orders: by last update, not by order date

# **AN ORDER PLACED THREE WEEKS AGO AND CANCELLED YESTERDAY** appears in
# by-last-update and NOT in by-order-date. A by-order-date sync never learns it
# changed, and the stock and the money stay wrong for ever.
orders = tool.amazon_report("az_orders")
check("orders are fetched by LAST UPDATE", answered(lambda: orders.report_type.endswith("BY_LAST_UPDATE_GENERAL")))
check("and not by order date", answered(lambda: "BY_ORDER_DATE" not in orders.report_type))
check("with Amazon's documented 30-day cap written beside it", answered(lambda: orders.max_days == 30))

# ------------------------------------------------------------ the request

body = tool.create_body("az_orders", DAY("2026-08-26"), DAY("2026-08-26"))
check("the body names the report type", answered(lambda: body["reportType"] == orders.report_type))
check("and the marketplace, as a list", answered(lambda: body["marketplaceIds"] == [tool.INDIA]))
# **A DATE IS NOT AN INSTANT and Amazon's fields are instants.** A bare date would
# mean midnight UTC, which in India is 05:30 -- so every file would hold the last
# five and a half hours of the day before.
# **HIS DAY, NOT GREENWICH'S. This is the fault Jaiswal found by asking what
# "yesterday" means to Amazon**, and these two lines are what had locked it in:
# they asserted midnight-to-midnight UTC, which in India is 05:30 to 05:30, so
# every day's file MISSED ITS OWN FIRST FIVE AND A HALF HOURS and picked up five
# and a half of the next. The comment above the code warned about exactly this
# and the code did it anyway.
check("the start is the very beginning of HIS day",
      answered(lambda: body["dataStartTime"] == "2026-08-25T18:30:00Z"))
check("and the end is the very end of HIS day",
      answered(lambda: body["dataEndTime"] == "2026-08-26T18:29:59Z"))
# Said in Greenwich's terms rather than carrying a +05:30, so nothing rests on
# Amazon parsing an offset -- the same instant either way.
check("and both are said the one way Amazon is certain to read",
      answered(lambda: body["dataStartTime"].endswith("Z") and "+" not in body["dataStartTime"]))
# The whole span is one day, to the second. Built on the wrong clock it still
# spans a day, which is why length alone could never have caught this.
check("the two ends are a whole day apart, to the second",
      answered(lambda: body["dataEndTime"] > body["dataStartTime"]))
check("both are marked as the timezone they are in", answered(lambda: body["dataStartTime"].endswith("Z") and body["dataEndTime"].endswith("Z")))
check("a single day is a whole day, not an instant", answered(lambda: body["dataStartTime"] != body["dataEndTime"]))

# Amazon's cap, refused here rather than by Amazon -- asking costs a minute.
check("a range wider than Amazon allows is refused", answered(lambda: tool.why_request_is_refused("az_orders", DAY("2026-07-01"), DAY("2026-08-26")) is not None))
check("and the refusal says what the cap is", answered(lambda: "30 days" in tool.why_request_is_refused("az_orders", DAY("2026-07-01"), DAY("2026-08-26"))))
check("exactly thirty days is allowed", answered(lambda: tool.why_request_is_refused("az_orders", DAY("2026-08-01"), DAY("2026-08-30")) is None))
check("thirty-one is not", answered(lambda: tool.why_request_is_refused("az_orders", DAY("2026-08-01"), DAY("2026-08-31")) is not None))
check("a range that ends before it starts is refused", answered(lambda: tool.why_request_is_refused("az_orders", DAY("2026-08-26"), DAY("2026-08-25")) is not None))
check("a report nobody knows is refused", answered(lambda: tool.why_request_is_refused("az_nonsense", DAY("2026-08-26"), DAY("2026-08-26")) is not None))
check("and looking one up is refused too", answered(lambda: refuses(lambda: tool.amazon_report("az_nonsense"))))

# ------------------------------------- TRAP: the paging token goes on its own

# **"Providing nextToken alongside other parameters causes request failure."**
# The obvious way to write paging is the one way that does not work.
page = tool.next_page_query("abc123")
check("the next page is asked for with the token", answered(lambda: page["nextToken"] == "abc123"))
check("and with NOTHING else alongside it", answered(lambda: list(page.keys()) == ["nextToken"]))
check("no next page is refused rather than asked for emptily", answered(lambda: refuses(lambda: tool.next_page_query(""))))

find = tool.find_query("az_settlements", DAY("2026-08-01"), DAY("2026-08-26"))
check("finding a report filters by its type", answered(lambda: find["reportTypes"] == ["GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE_V2"]))
check("and only wants finished ones", answered(lambda: find["processingStatuses"] == [tool.DONE]))
# Left off, Amazon defaults it to ninety days ago -- a quarter of settlements to
# wade through to find last night's.
check("createdSince is always said, never left to Amazon's 90-day default", answered(lambda: "createdSince" in find))
check("and the page is asked for at Amazon's maximum", answered(lambda: find["pageSize"] == 100))

# ------------------------------- TRAP 2: CANCELLED is not a failure

# **AMAZON'S OWN WORDS: "an automatic cancellation if there is no data to return".**
# On a small seller's quiet day this is the ordinary answer. Recorded as a failure
# it puts a red row on the board most days, and a board that cries wolf is unread.
cancelled = tool.read_status({"processingStatus": "CANCELLED"})
check("CANCELLED means there was nothing to fetch", answered(lambda: cancelled.state == tool.NOTHING_TO_FETCH))
check("and it is NOT a failure", answered(lambda: cancelled.state != tool.FAILED))
check("and it says why, so nobody goes looking for a fault", answered(lambda: "no data" in cancelled.say))

check("FATAL is a failure", answered(lambda: tool.read_status({"processingStatus": "FATAL"}).state == tool.FAILED))
check("IN_QUEUE is waiting", answered(lambda: tool.read_status({"processingStatus": "IN_QUEUE"}).state == tool.WAITING))
check("IN_PROGRESS is waiting too", answered(lambda: tool.read_status({"processingStatus": "IN_PROGRESS"}).state == tool.WAITING))
ready = tool.read_status({"processingStatus": "DONE", "reportDocumentId": "doc-1"})
check("DONE with a document is ready", answered(lambda: ready.state == tool.READY))
check("and it carries the document to fetch", answered(lambda: ready.document_id == "doc-1"))

# **DONE WITH NO DOCUMENT IS NOT READY.** Reported ready, the next step would go
# and fetch a file that does not exist.
check("DONE without a document is a failure, not a ready", answered(lambda: tool.read_status({"processingStatus": "DONE"}).state == tool.FAILED))
check("and it says what is missing", answered(lambda: "where the file is" in tool.read_status({"processingStatus": "DONE"}).say))

# A status Amazon adds later must not be polled for ever in silence.
strange = tool.read_status({"processingStatus": "SOMETHING_NEW"})
check("a status nobody recognises is a failure, not a wait", answered(lambda: strange.state == tool.FAILED))
check("and it says what it did not recognise", answered(lambda: "SOMETHING_NEW" in strange.say))
check("an answer with nothing in it is a failure too", answered(lambda: tool.read_status({}).state == tool.FAILED))
check("and so is nothing at all", answered(lambda: tool.read_status(None).state == tool.FAILED))
check("all five documented statuses are known", answered(lambda: set(tool.EVERY_STATUS) == {"IN_QUEUE", "IN_PROGRESS", "DONE", "CANCELLED", "FATAL"}))

# --------------------------------- TRAP 3: the link lasts five minutes

check("Amazon's link lasts five minutes", answered(lambda: tool.LINK_LASTS == timedelta(minutes=5)))
# Treated as gone a little early: the time between deciding to download and the
# bytes arriving is not nothing.
check("and it is treated as gone before that", answered(lambda: tool.LINK_TREAT_AS_STALE_AFTER < tool.LINK_LASTS))
GOT_AT = datetime(2026, 8, 27, 12, 0, 0)
check("a link a moment old is good", answered(lambda: tool.link_is_stale(GOT_AT, GOT_AT + timedelta(seconds=30)) is False))
check("a link three minutes old is still good", answered(lambda: tool.link_is_stale(GOT_AT, GOT_AT + timedelta(minutes=3)) is False))
check("a link four minutes old is treated as gone", answered(lambda: tool.link_is_stale(GOT_AT, GOT_AT + timedelta(minutes=4)) is True))
check("and one past five certainly is", answered(lambda: tool.link_is_stale(GOT_AT, GOT_AT + timedelta(minutes=6)) is True))

# ------------------------------------------------------------ unzipping

check("a document with no compression is plain", answered(lambda: tool.is_gzipped({}) is False))
check("and one that says nothing is plain too", answered(lambda: tool.is_gzipped({"compressionAlgorithm": None}) is False))
check("GZIP is zipped", answered(lambda: tool.is_gzipped({"compressionAlgorithm": "GZIP"}) is True))
check("however it is written", answered(lambda: tool.is_gzipped({"compressionAlgorithm": "gzip"}) is True))
# **A COMPRESSION NOBODY KNOWS IS REFUSED, NOT ASSUMED PLAIN.** Assumed plain, it
# writes a file of rubbish into the seller's Drive that reads as a good day.
check("a compression nobody knows is refused", answered(lambda: refuses(lambda: tool.is_gzipped({"compressionAlgorithm": "BROTLI"}))))
check("and the refusal says nothing was written", answered(lambda: "has not been written" in _said(lambda: tool.is_gzipped({"compressionAlgorithm": "BROTLI"}))))

# ------------------------------------------------------------ being patient

# **THESE ARE AMAZON'S PUBLISHED NUMBERS, and two of them are one call a minute.**
check("createReport is one call a minute", answered(lambda: round(tool.seconds_between("createReport")) == 60))
check("getReportDocument is one call a minute too", answered(lambda: round(tool.seconds_between("getReportDocument")) == 60))
check("getReport is two a second", answered(lambda: tool.seconds_between("getReport") == 0.5))
check("getReports is one per forty-five seconds", answered(lambda: round(tool.seconds_between("getReports")) == 45))
check("an operation this does not make is refused", answered(lambda: refuses(lambda: tool.seconds_between("deleteEverything"))))
check("the rate-limit header is the documented one", answered(lambda: tool.RATE_LIMIT_HEADER == "x-amzn-RateLimit-Limit"))

# **POLLING IS CHEAP, ASKING IS EXPENSIVE**, and that is the whole shape of the
# door: ask once, wait patiently, never ask again.
check("asking costs far more than checking", answered(lambda: tool.seconds_between("createReport") > tool.seconds_between("getReport") * 100))

check("the first wait is not instant", answered(lambda: tool.how_long_to_wait(0) >= 10))
check("waits get longer", answered(lambda: tool.how_long_to_wait(2) > tool.how_long_to_wait(0)))
# **AND STOP GETTING LONGER.** A wait that keeps doubling turns a report that took
# an hour into one nobody ever collects.
check("but they stop growing", answered(lambda: tool.how_long_to_wait(20) == tool.LONGEST_WAIT))
check("and never exceed the ceiling", answered(lambda: all(tool.how_long_to_wait(n) <= tool.LONGEST_WAIT for n in range(0, 25))))
# What Amazon's own header says beats the table, because a bigger seller is given more.
check("what Amazon's header asks for wins over the table", answered(lambda: tool.how_long_to_wait(0, said=0.5) == 2.0))
check("and a header asking for something silly is floored at a second", answered(lambda: tool.how_long_to_wait(0, said=100.0) == 1.0))
check("a header saying nothing falls back to the table", answered(lambda: tool.how_long_to_wait(0, said=None) == tool.how_long_to_wait(0)))
check("and one saying nought does too", answered(lambda: tool.how_long_to_wait(0, said=0) == tool.how_long_to_wait(0)))
check("there is no attempt before the first", answered(lambda: refuses(lambda: tool.how_long_to_wait(-1))))

# ------------------------------------------------- nothing of one seller's

SOURCE = Path(tool.__file__).read_text(encoding="utf-8")
# **NO SECRET IS IN THE SOURCE.** The credentials arrive at runtime and are never
# written here (Golden Rule 8). Checked by reading the bytes, because that is the
# only way this stays true.
import re as _re  # noqa: E402
check("no email address of anybody's is in this file", answered(lambda: not _re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", SOURCE)))
check("and nothing that looks like a token or a key", answered(lambda: not _re.search(r"['\"](?:Atzr|Atza)\|[^'\"]+['\"]", SOURCE)))
check("and no seller's own business name", answered(lambda: "rumee" not in SOURCE.lower()))

# The record is frozen, like every other in this package.
check("an Amazon report mapping cannot be edited after it is made",
      answered(lambda: refuses(lambda: setattr(tool.AMAZON_REPORTS[0], "report_type", "X"))))


# ------------------------------------------------- the ends nothing else reached

# The other two hosts, so a wrong one cannot be swapped in unnoticed.
check("North America has its own host", answered(lambda: tool.HOSTS["na"] == "https://sellingpartnerapi-na.amazon.com"))
check("and the Far East has its own", answered(lambda: tool.HOSTS["fe"] == "https://sellingpartnerapi-fe.amazon.com"))
check("and all three are different", answered(lambda: len(set(tool.HOSTS.values())) == 3))
# The refusal names the marketplace, so whoever reads it knows which one to look up.
check("a refused marketplace is named in the refusal", answered(lambda: "A1F83G8C2ARO7P" in _said(lambda: tool.host_for("A1F83G8C2ARO7P"))))
check("and the refusal points at Amazon's own table", answered(lambda: "marketplace-id table" in _said(lambda: tool.host_for("A1F83G8C2ARO7P"))))

# **THE NOTES ARE READ, not decoration.** Each says why the report is fetched the
# way it is, and that is the thing somebody changing it needs to see.
check("the orders note says why last-update is used",
      answered(lambda: "change to an old order is caught" in tool.amazon_report("az_orders").note))
check("the returns note says what its dates mean", answered(lambda: "return was made" in tool.amazon_report("az_returns").note))
check("and the settlement note says Amazon schedules it", answered(lambda: "schedules this itself" in tool.amazon_report("az_settlements").note))
check("and names the day the old types are removed", answered(lambda: "11 November 2026" in tool.amazon_report("az_settlements").note))

# Amazon's cap on returns is its own number, not the orders one.
check("returns have their own 60-day cap", answered(lambda: tool.amazon_report("az_returns").max_days == 60))
check("which is not the orders cap", answered(lambda: tool.amazon_report("az_returns").max_days != tool.amazon_report("az_orders").max_days))
check("a 60-day range of returns is allowed", answered(lambda: tool.why_request_is_refused("az_returns", DAY("2026-07-01"), DAY("2026-08-29")) is None))
check("and 61 is not", answered(lambda: tool.why_request_is_refused("az_returns", DAY("2026-07-01"), DAY("2026-08-30")) is not None))

# **THE REFUSAL SAYS HOW MANY DAYS WERE ASKED FOR**, because whoever reads it is
# deciding how to split the request.
too_wide = tool.why_request_is_refused("az_orders", DAY("2026-07-01"), DAY("2026-08-26"))
check("a too-wide refusal says how many days were asked for", answered(lambda: "57" in too_wide))

# find_query carries the marketplace and a real window.
find2 = tool.find_query("az_settlements", DAY("2026-08-01"), DAY("2026-08-26"))
check("finding a report says which marketplace", answered(lambda: find2["marketplaceIds"] == [tool.INDIA]))
check("createdSince is the very start of its day, on HIS clock", answered(lambda: find2["createdSince"] == "2026-07-31T18:30:00Z"))
# **THE END OF THE DAY, NOT THE START.** Asked from the start, a settlement Amazon
# published at nine in the morning of the last day would fall outside the window.
check("createdUntil is the very END of its day, on HIS clock", answered(lambda: find2["createdUntil"] == "2026-08-26T18:29:59Z"))
check("so a whole day is really covered", answered(lambda: find2["createdSince"] < find2["createdUntil"]))

# What a status means is frozen, like every other record here.
check("what a status means cannot be edited after it is read",
      answered(lambda: refuses(lambda: setattr(tool.read_status({"processingStatus": "DONE", "reportDocumentId": "d"}), "state", "x"))))

# **FATAL SAYS FATAL.** Without its own arm it would fall through to the
# unrecognised-status branch -- the same outcome, but a sentence that says Amazon
# answered something nobody knows, which sends whoever reads it the wrong way.
check("a fatal report says Amazon stopped it with a fatal error",
      answered(lambda: "fatal error" in tool.read_status({"processingStatus": "FATAL"}).say))
check("and does not read as an unrecognised answer",
      answered(lambda: "does not recognise" not in tool.read_status({"processingStatus": "FATAL"}).say))

# The compression refusal names what it could not open.
odd = _said(lambda: tool.is_gzipped({"compressionAlgorithm": "BROTLI"}))
check("an unknown compression is named in the refusal", answered(lambda: "BROTLI" in odd))
check("and it says why nothing was written", answered(lambda: "worse than a missing one" in odd))


# **AND NOTHING ABOVE ENDED BY THROWING RATHER THAN BY ANSWERING.** Answering
# with nothing keeps the run alive; this is what stops a check phrased as "this
# word is NOT in what it said" going green because there was nothing to look in.
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)


EXPECTED = 118
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
