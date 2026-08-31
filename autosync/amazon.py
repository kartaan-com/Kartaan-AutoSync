"""The Amazon door: everything Amazon's API makes true, decided here and nowhere else.

**PURE. There is no network in this file** -- no sockets, no requests library, no
token. It takes what an answer said and decides what that means. That is what
lets every rule below be checked without an account, a token or the internet, and
it is the same seam `shared/data/store.js` is on the JavaScript side.

**EVERY FACT HERE COMES FROM AMAZON'S OWN DOCUMENTATION**, read 2026-08-27 before
a line of it was written (Golden Rule 1). The whole reading is in
`docs/WORKING.md` under "Amazon SP-API -- read from Amazon's own docs". Nothing
here is remembered, guessed, or taken from a blog.

**THE FOUR THINGS THAT WOULD HAVE SUNK A BUILD THAT GUESSED:**

1. **India is on the EUROPE endpoint**, not the Far East one. Every call from the
   obvious guess would have failed.
2. **`CANCELLED` usually means "there was no data to send you"**, in Amazon's own
   words -- not a failure. Treated as one it puts a red row on the board every
   quiet day, and a board that cries wolf is a board nobody reads.
3. **The download link lasts five minutes.** A design that fetches it and
   downloads later is broken by the clock.
4. **Settlement reports cannot be asked for at all.** Amazon schedules them
   itself. There is no `createReport` for them -- they are found, not requested --
   so this door needs two flows, not one.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from clock import HOURS_AHEAD_OF_UTC, MINUTES_AHEAD_OF_UTC

# **HIS TIMEZONE, TAKEN FROM THE ONE PLACE IT IS WRITTEN DOWN.** Repeated here as
# a number, the day somebody corrects one of them the other goes on being wrong
# -- and the only sign would be a day's file quietly holding the wrong hours.
HIS_TIMEZONE = timezone(timedelta(hours=HOURS_AHEAD_OF_UTC, minutes=MINUTES_AHEAD_OF_UTC))
from typing import Dict, Optional, Sequence, Tuple

# ------------------------------------------------------------------ where

# **INDIA IS ON THE EUROPE ENDPOINT.** Amazon groups it under "Europe, Middle
# East, India, and Africa". The intuitive guess -- the Far East host -- is wrong,
# and every call made to it fails.
HOSTS = {
    "eu": "https://sellingpartnerapi-eu.amazon.com",
    "na": "https://sellingpartnerapi-na.amazon.com",
    "fe": "https://sellingpartnerapi-fe.amazon.com",
}

# Marketplace ids, from Amazon's own table. India is the one this is built for.
INDIA = "A21TJRUUN4KGV"
MARKETPLACE_REGION = {INDIA: "eu"}

# Where a token is got. Not an SP-API host -- a different service entirely.
TOKEN_ENDPOINT = "https://api.amazon.com/auth/o2/token"

# **An access token lasts one hour.** Asked for again a little early, so a long
# run never presents one that went stale between deciding to call and calling.
TOKEN_LASTS = timedelta(hours=1)
TOKEN_RENEW_EARLY = timedelta(minutes=5)

# The header the token travels in. **No AWS request signing: SP-API dropped IAM
# and Signature Version 4 on 2 October 2023, and a request that still carries a
# signature has it ignored.**
TOKEN_HEADER = "x-amz-access-token"


def host_for(marketplace_id: str) -> str:
    """Which host serves this marketplace.

    **REFUSES A MARKETPLACE IT DOES NOT KNOW** rather than defaulting to one. A
    default here sends a seller's calls to the wrong continent, where they fail
    with an error that says nothing about the real cause.
    """
    region = MARKETPLACE_REGION.get(marketplace_id)
    if region is None:
        raise KeyError(
            f"{marketplace_id!r} is not a marketplace this knows the endpoint for. "
            "Amazon's own marketplace-id table says which region it belongs to."
        )
    return HOSTS[region]


# ------------------------------------------------------------------ paths

REPORTS_PATH = "/reports/2021-06-30/reports"
REPORT_PATH = "/reports/2021-06-30/reports/{report_id}"
DOCUMENT_PATH = "/reports/2021-06-30/documents/{document_id}"


# ------------------------------------------------------- what a report is

# **TWO KINDS, AND THIS IS THE WHOLE SHAPE OF THE DOOR.** One is asked for; the
# other Amazon produces on its own schedule and you go looking for it.
ASK_FOR_IT = "ask-for-it"
AMAZON_MAKES_IT = "amazon-makes-it"


@dataclass(frozen=True)
class AmazonReport:
    """How one of Kartaan's reports maps onto Amazon's own.

    `max_days` is Amazon's cap on the range, written down beside the report it
    belongs to -- the order reports cap at 30 days, and a request wider than that
    is refused by Amazon rather than trimmed.
    """

    report_id: str
    report_type: str
    how: str
    max_days: Optional[int] = None
    note: str = ""


AMAZON_REPORTS: Tuple[AmazonReport, ...] = (
    # **BY LAST UPDATE, NOT BY ORDER DATE**, and the difference decides whether
    # the numbers ever come right. An order placed three weeks ago and cancelled
    # yesterday appears in by-last-update and NOT in by-order-date -- so a
    # by-order-date sync never learns it changed, and the stock and the money
    # stay wrong for ever. It is a run date against a data date, one level up.
    AmazonReport(
        "az_orders",
        "GET_FLAT_FILE_ALL_ORDERS_DATA_BY_LAST_UPDATE_GENERAL",
        ASK_FOR_IT,
        max_days=30,
        note="Orders updated in the period, so a change to an old order is caught.",
    ),
    AmazonReport(
        "az_returns",
        "GET_FLAT_FILE_RETURNS_DATA_BY_RETURN_DATE",
        ASK_FOR_IT,
        max_days=60,
        note="Returns by the date the return was made.",
    ),
    # **THIS ONE CANNOT BE ASKED FOR.** Amazon's own words: "Settlement reports
    # cannot be requested or scheduled. They are automatically scheduled by
    # Amazon." A connector that tried would fail for ever, and the failure would
    # read as a refused request rather than as something that can never be asked.
    AmazonReport(
        "az_settlements",
        "GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE_V2",
        AMAZON_MAKES_IT,
        note=(
            "Amazon schedules this itself. It is found, never requested. The two older "
            "settlement types are deprecated and are removed on 11 November 2026."
        ),
    ),
)

BY_REPORT_ID = {r.report_id: r for r in AMAZON_REPORTS}

# Named so nothing has to remember which strings are the dead ones. Kept rather
# than deleted because a seller's older reports still carry them, and a reader
# meeting one needs to know what it is looking at.
REMOVED_ON = date(2026, 11, 11)
RETIRED_SETTLEMENT_TYPES = (
    "GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE",
    "GET_V2_SETTLEMENT_REPORT_DATA_XML",
)


def amazon_report(report_id: str) -> AmazonReport:
    """How one of Kartaan's reports is fetched from Amazon, or a refusal."""
    found = BY_REPORT_ID.get(report_id)
    if found is None:
        raise KeyError(f"{report_id!r} is not a report this door knows how to fetch.")
    return found


def must_be_found_not_asked(report_id: str) -> bool:
    """Is this one Amazon makes on its own?"""
    return amazon_report(report_id).how == AMAZON_MAKES_IT


# ------------------------------------------------------- asking for one

def why_request_is_refused(report_id: str, start: date, end: date) -> Optional[str]:
    """What is wrong with a request before it is sent, or None.

    **REFUSED HERE RATHER THAN BY AMAZON**, because a refusal that arrives as an
    HTTP error is a sentence nobody can act on -- and because asking is rationed
    at one call a minute, so a request that was never going to work is a minute
    of the day spent on nothing.
    """
    which = BY_REPORT_ID.get(report_id)
    if which is None:
        return f"{report_id} is not a report this door knows how to fetch."
    if which.how == AMAZON_MAKES_IT:
        return (
            f"{report_id} cannot be asked for. Amazon schedules it itself, so it is found "
            "rather than requested."
        )
    if end < start:
        return f"{report_id}: the range ends before it starts."
    if which.max_days is not None and (end - start).days + 1 > which.max_days:
        return (
            f"{report_id}: Amazon allows at most {which.max_days} days in one request, and this "
            f"asks for {(end - start).days + 1}."
        )
    return None


def _moment(day: date, end_of_day: bool) -> str:
    """A day as the instant Amazon wants, in ISO 8601 with its timezone.

    **A DATE IS NOT AN INSTANT, and Amazon's fields are instants.**

    **AND THE DAY IS HIS DAY, NOT GREENWICH'S -- this line had the fault its own
    comment warned about.** It built midnight-to-midnight UTC, which in India is
    05:30 to 05:30: every day's file would have MISSED ITS OWN FIRST FIVE AND A
    HALF HOURS and picked up five and a half hours of the next day, for ever,
    with nothing to show for it but numbers that were quietly short. **Jaiswal
    found it by asking what "yesterday" means to Amazon.**

    So the two ends are built on HIS clock and then said in Greenwich's, which is
    the same instant written the way Amazon is certain to read it -- `2026-08-26`
    starts at `2026-08-25T18:30:00Z`. Sent with a `+05:30` on it instead, it
    would rest on Amazon parsing an offset, and there is no reason to find out.
    """
    at = datetime(day.year, day.month, day.day, tzinfo=HIS_TIMEZONE)
    if end_of_day:
        at = at + timedelta(days=1) - timedelta(seconds=1)
    return at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def create_body(report_id: str, start: date, end: date, marketplace_id: str = INDIA) -> Dict:
    """The body of a createReport call. Refuses rather than building a bad one."""
    wrong = why_request_is_refused(report_id, start, end)
    if wrong:
        raise ValueError(wrong)
    return {
        "reportType": amazon_report(report_id).report_type,
        "marketplaceIds": [marketplace_id],
        "dataStartTime": _moment(start, end_of_day=False),
        "dataEndTime": _moment(end, end_of_day=True),
    }


def find_query(report_id: str, since: date, until: date, marketplace_id: str = INDIA) -> Dict:
    """The query for finding a report Amazon made on its own.

    `createdSince` is always sent. Left off, Amazon defaults it to ninety days
    ago, and a run would wade through a quarter of settlements to find last
    night's.
    """
    which = amazon_report(report_id)
    return {
        "reportTypes": [which.report_type],
        "marketplaceIds": [marketplace_id],
        "processingStatuses": [DONE],
        "createdSince": _moment(since, end_of_day=False),
        "createdUntil": _moment(until, end_of_day=True),
        "pageSize": MAX_PAGE_SIZE,
    }


# Amazon's own maximum. Asked for in full because paging costs a call, and a call
# here is rationed at one per forty-five seconds.
MAX_PAGE_SIZE = 100


def next_page_query(next_token: str) -> Dict:
    """The query for the page after this one.

    **THE TOKEN GOES ON ITS OWN, and this is a documented trap.** Amazon: "Providing
    `nextToken` alongside other parameters causes request failure." The obvious way
    to write paging -- keep the filters and add the token -- is the one way that
    does not work.
    """
    if not next_token:
        raise ValueError("There is no next page to ask for.")
    return {"nextToken": next_token}


# --------------------------------------------------- what an answer means

IN_QUEUE = "IN_QUEUE"
IN_PROGRESS = "IN_PROGRESS"
DONE = "DONE"
CANCELLED = "CANCELLED"
FATAL = "FATAL"
EVERY_STATUS = (IN_QUEUE, IN_PROGRESS, DONE, CANCELLED, FATAL)

# What this door decides an answer MEANS. Four, not five -- because two of
# Amazon's statuses mean the same thing to us, and one of its statuses is not a
# failure at all.
WAITING = "waiting"
READY = "ready"
NOTHING_TO_FETCH = "nothing-to-fetch"
FAILED = "failed"


@dataclass(frozen=True)
class WhereItGot:
    """What a status means, and the sentence to record for it."""

    state: str
    document_id: Optional[str]
    say: str


def read_status(answer: Dict) -> WhereItGot:
    """What Amazon just told us about a report.

    **`CANCELLED` IS NOT A FAILURE, and that is the single most important line in
    this file.** Amazon's own words: a report is cancelled either by an explicit
    request, "or an automatic cancellation if there is no data to return". On a
    small seller's quiet day that is the ordinary answer. Recorded as a failure it
    would put a red row on the board most days, and the day board's whole value is
    that a red row means something.

    **AND `DONE` WITHOUT A DOCUMENT IS NOT READY.** Amazon gives a
    `reportDocumentId` on a finished report; a `DONE` with none is a state nothing
    can act on, and reporting it ready would send the next step to fetch a
    document that does not exist.
    """
    status = str((answer or {}).get("processingStatus") or "")
    document_id = (answer or {}).get("reportDocumentId") or None

    if status in (IN_QUEUE, IN_PROGRESS):
        return WhereItGot(WAITING, None, f"Amazon is still working on it ({status}).")
    if status == DONE:
        if not document_id:
            return WhereItGot(
                FAILED,
                None,
                "Amazon says the report is done but did not say where the file is.",
            )
        return WhereItGot(READY, str(document_id), "Ready to download.")
    if status == CANCELLED:
        return WhereItGot(
            NOTHING_TO_FETCH,
            None,
            "Amazon cancelled it, which normally means there was no data for that period.",
        )
    if status == FATAL:
        return WhereItGot(FAILED, None, "Amazon stopped the report with a fatal error.")
    # **AN ANSWER NOBODY RECOGNISES IS A FAILURE, NOT A WAIT.** Treated as a wait,
    # a status Amazon adds later would be polled for ever with nothing said.
    return WhereItGot(
        FAILED,
        None,
        f"Amazon answered with a status this does not recognise: {status or '(nothing)'}.",
    )


# ------------------------------------------------------------ the document

GZIP = "GZIP"

# **THE LINK LASTS FIVE MINUTES.** Amazon's own number.
LINK_LASTS = timedelta(minutes=5)
# Treated as stale a little early, because the time between deciding to download
# and the bytes arriving is not nothing.
LINK_TREAT_AS_STALE_AFTER = timedelta(minutes=4)


def is_gzipped(document: Dict) -> bool:
    """Does this document need unzipping?

    **GZIP IS THE ONLY VALUE THERE IS**, and absent means plain. Anything else is
    refused rather than assumed plain: a compression Amazon adds later, silently
    treated as plain text, writes a file of rubbish into the seller's Drive that
    reads as a successful day.
    """
    how = (document or {}).get("compressionAlgorithm")
    if how in (None, ""):
        return False
    if str(how).upper() == GZIP:
        return True
    raise ValueError(
        f"Amazon says this file is compressed with {how!r}, which this does not know how to "
        "open. It has not been written anywhere, because a file nobody can read is worse "
        "than a missing one."
    )


def link_is_stale(fetched_at: datetime, now: datetime) -> bool:
    """Has the download link gone off?

    Asked rather than assumed, because the answer changes what to do: a stale link
    is re-requested from Amazon, never retried as a download -- retrying it just
    fails again, which is how a retry loop becomes a way of doing nothing slowly.
    """
    return (now - fetched_at) >= LINK_TREAT_AS_STALE_AFTER


# ---------------------------------------------------------- being patient

# Amazon's published limits, per second, with the burst each allows.
# **TWO OF THESE ARE ONE CALL A MINUTE.**
RATE_LIMITS = {
    "createReport": (0.0167, 15),
    "getReport": (2.0, 15),
    "getReportDocument": (0.0167, 15),
    "getReports": (0.0222, 10),
}

# The header Amazon returns the applied limit in. Read rather than trusting the
# table for ever -- a seller with higher throughput is given more.
RATE_LIMIT_HEADER = "x-amzn-RateLimit-Limit"


def seconds_between(operation: str) -> float:
    """How long to leave between two calls of this operation."""
    rate = RATE_LIMITS.get(operation)
    if rate is None:
        raise KeyError(f"{operation!r} is not an operation this door makes.")
    return 1.0 / rate[0]


def how_long_to_wait(attempt: int, said: Optional[float] = None) -> float:
    """How long to wait before asking about a report again.

    **POLLING IS CHEAP AND ASKING IS EXPENSIVE**, and the whole shape of this door
    follows from that: `getReport` allows two calls a second, `createReport` one a
    minute. So a report already in the queue is waited for patiently and NEVER
    asked for again -- re-submitting a request that actually worked is how the
    reference burned Flipkart's twenty-a-day quota and got itself locked out.

    Backs off, and stops backing off at a ceiling: a wait that keeps doubling
    turns a report that took an hour into one nobody collects.
    """
    if attempt < 0:
        raise ValueError("There is no attempt before the first one.")
    if said is not None and said > 0:
        # What Amazon's own header asked for always wins over the table.
        return max(1.0 / said, 1.0)
    wait = min(FIRST_WAIT * (2 ** attempt), LONGEST_WAIT)
    return float(wait)


FIRST_WAIT = 30
LONGEST_WAIT = 300
