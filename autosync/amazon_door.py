"""Fetching one report from Amazon, end to end. Phase 2 of the plan.

**THE ONLY FILE IN THE PACKAGE THAT TALKS TO ANYTHING**, and even here it does not:
the thing that makes the call is handed in. That is the same seam `store.js` is on,
and it is what lets the whole flow -- token, request, waiting, the five-minute link,
paging, throttling, unzipping -- be checked without an account, a token, or a
network.

**WHAT `transport` HAS TO BE**, written down because it is a contract somebody else
implements:

    transport(method, url, headers=None, params=None, form=None, json_body=None)
        -> Answer(status, headers, json, body)

`status` is the HTTP status, `headers` a mapping, `json` the decoded body or None,
`body` the raw bytes or None. It raises for anything that stopped it reaching
Amazon at all. It never retries -- retrying is a decision, and decisions are made
here where they can be read.

**THE FOUR RULES THIS FLOW IS SHAPED BY**, all from Amazon's own documentation
(read 2026-08-27, `docs/WORKING.md`):

  - **Asking costs a minute; polling costs half a second.** `createReport` allows
    one call per sixty seconds, `getReport` two per second. So a report is asked
    for ONCE and then waited for patiently. **A request that actually worked is
    never sent again** -- re-submitting is how the reference burned Flipkart's
    twenty-a-day quota and locked itself out for a day.
  - **The download link lasts five minutes.** It is used at once. A stale one is
    re-requested, never retried.
  - **`CANCELLED` normally means there was no data**, so it is an outcome, not a
    failure.
  - **Settlements cannot be asked for.** They are found.
"""

import gzip
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import amazon
from landing import file_name_for
from reports import report as kartaan_report

# What a fetch came to. Four outcomes, and only one of them is a failure.
LANDED = "landed"
NOTHING_TO_FETCH = "nothing-to-fetch"
STILL_WAITING = "still-waiting"
FAILED = "failed"


@dataclass(frozen=True)
class Answer:
    """What the transport got back. Plain, so a check can build one by hand."""

    status: int
    headers: Dict
    json: Optional[Dict] = None
    body: Optional[bytes] = None


@dataclass(frozen=True)
class Fetched:
    """What one attempt at one report came to.

    `say` is the sentence that goes in the run log. It is built here, where the
    reason is actually known -- not by whoever displays it, who would have to
    guess.
    """

    state: str
    report_id: str
    data_date: date
    file_name: Optional[str] = None
    size: int = 0
    say: str = ""
    # **WHAT AMAZON CALLS THE REPORT IT IS BUILDING**, carried back so the next run
    # can collect it instead of asking again. Without this the runner had nothing
    # to remember, and every run would spend a rationed request on a report Amazon
    # was already building -- which is the exact fault this door was shaped to
    # prevent. Found by wiring the runner to it.
    their_id: Optional[str] = None


class AmazonDoor:
    """One seller's way in to Amazon.

    Holds the token between calls, because a token lasts an hour and asking for a
    new one on every call is both slow and rude. **It holds nothing else** -- no
    report state, no queue, no marker. Everything about what is owed lives in
    `schedule.py`, and everything about what arrived lives in the folder.
    """

    def __init__(
        self,
        transport: Callable[..., Answer],
        credentials: Dict,
        now: Callable[[], datetime],
        marketplace_id: str = amazon.INDIA,
    ):
        for needed in ("client_id", "client_secret", "refresh_token"):
            if not credentials.get(needed):
                # **REFUSED HERE, NAMED.** A door built without a secret fails on
                # its first call with an authorization error that says nothing
                # about which of the three is missing.
                raise ValueError(f"The Amazon door needs {needed} and was not given one.")
        self._transport = transport
        self._credentials = credentials
        self._now = now
        self.marketplace_id = marketplace_id
        self.host = amazon.host_for(marketplace_id)
        # **ONE FIELD, NOT TWO.** It was a token and an expiry side by side, and
        # the expiry could never be read on its own -- the token being empty
        # short-circuited before it. Two fields for one fact, and one of them
        # unreachable. Held together, so they cannot disagree.
        self._token: Optional[Tuple[str, datetime]] = None

    # ------------------------------------------------------------- getting in

    def token(self) -> str:
        """A live access token, asked for again only when the old one is near its end.

        **NEVER LOGGED, NEVER RETURNED ANYWHERE IT COULD BE WRITTEN DOWN.** It is a
        credential; the run log carries what happened, never what it was carrying.
        """
        if self._token and self._now() < self._token[1]:
            return self._token[0]
        answer = self._transport(
            "POST",
            amazon.TOKEN_ENDPOINT,
            form={
                "grant_type": "refresh_token",
                "refresh_token": self._credentials["refresh_token"],
                "client_id": self._credentials["client_id"],
                "client_secret": self._credentials["client_secret"],
            },
        )
        if answer.status != 200 or not answer.json or not answer.json.get("access_token"):
            # **THE STATUS, NOT THE BODY.** An authorization failure's body can
            # carry back what was sent to it, and this sentence goes in a log.
            raise PermissionError(
                f"Amazon would not give an access token (HTTP {answer.status}). "
                "The client id, secret or refresh token is wrong or has been revoked."
            )
        # Amazon says an hour; treated as slightly less so a token cannot go stale
        # between deciding to call and calling.
        self._token = (
            str(answer.json["access_token"]),
            self._now() + amazon.TOKEN_LASTS - amazon.TOKEN_RENEW_EARLY,
        )
        return self._token[0]

    def _call(self, method: str, path: str, params: Optional[Dict] = None, json_body: Optional[Dict] = None) -> Answer:
        return self._transport(
            method,
            self.host + path,
            headers={amazon.TOKEN_HEADER: self.token()},
            params=params,
            json_body=json_body,
        )

    # ----------------------------------------------------------- asking for one

    def ask_for(self, report_id: str, start: date, end: date) -> str:
        """Ask Amazon to make a report. Answers its id.

        **THE REFUSAL COMES FIRST, before the call.** Asking is rationed at one a
        minute, so a request that was never going to work is a minute of the day
        spent on nothing -- and a settlement report asked for here would fail every
        day for ever with an error about the request rather than about the fact
        that it can never be asked for.
        """
        wrong = amazon.why_request_is_refused(report_id, start, end)
        if wrong:
            raise ValueError(wrong)
        answer = self._call(
            "POST",
            amazon.REPORTS_PATH,
            json_body=amazon.create_body(report_id, start, end, self.marketplace_id),
        )
        if answer.status == 429:
            raise Throttled(f"Amazon is rate-limiting requests for {report_id}.")
        # **`is None`, NOT `not`.** An empty answer is `{}`, which is falsy -- so
        # `not answer.json` sent an accepted-but-silent reply down the "Amazon
        # refused it" path, and the sentence blamed the request instead of saying
        # the report may already be building. Found by the checks below.
        if answer.status not in (200, 201, 202) or answer.json is None:
            raise RuntimeError(f"Amazon would not take the request for {report_id} (HTTP {answer.status}).")
        given = answer.json.get("reportId")
        if not given:
            # **A REQUEST THAT LANDED AND SAID NOTHING IS A FAILURE, not a retry.**
            # Retried, it makes a second report Amazon is now building twice.
            raise RuntimeError(
                f"Amazon accepted the request for {report_id} but did not say what it is called, "
                "so it cannot be collected. It has NOT been asked for again -- that would leave "
                "two reports being built."
            )
        return str(given)

    def where_it_got(self, amazon_report_id: str) -> amazon.WhereItGot:
        """Ask how a report is getting on. Cheap: two a second."""
        answer = self._call("GET", amazon.REPORT_PATH.format(report_id=amazon_report_id))
        if answer.status == 429:
            raise Throttled("Amazon is rate-limiting status checks.")
        if answer.status != 200 or not answer.json:
            raise RuntimeError(f"Amazon would not say how {amazon_report_id} is getting on (HTTP {answer.status}).")
        return amazon.read_status(answer.json)

    # ------------------------------------------------------- finding one Amazon made

    def find_the_newest(self, report_id: str, since: date, until: date) -> Optional[Dict]:
        """The most recent finished report of this kind that Amazon made itself.

        For settlements, which cannot be asked for. Answers the report, or None
        when Amazon has not made one in that window -- **which is not a failure**:
        settlements arrive on Amazon's fortnightly cycle, so most days there is
        genuinely nothing new.
        """
        query = amazon.find_query(report_id, since, until, self.marketplace_id)
        newest = None
        while True:
            answer = self._call("GET", amazon.REPORTS_PATH, params=query)
            if answer.status == 429:
                raise Throttled("Amazon is rate-limiting the search for reports.")
            if answer.status != 200 or answer.json is None:
                raise RuntimeError(f"Amazon would not list its own reports (HTTP {answer.status}).")
            for one in answer.json.get("reports") or ():
                if newest is None or str(one.get("createdTime", "")) > str(newest.get("createdTime", "")):
                    newest = one
            token = answer.json.get("nextToken")
            if not token:
                return newest
            # **THE TOKEN GOES ON ITS OWN.** Amazon refuses a request that sends it
            # alongside the filters, which is the obvious way to write this.
            query = amazon.next_page_query(str(token))

    # ------------------------------------------------------------- the document

    def download(self, document_id: str) -> bytes:
        """Get the file itself.

        **THE LINK IS ASKED FOR AND USED IN THE SAME BREATH.** It lasts five
        minutes; anything that fetched it and queued the download for later would
        work in testing and fail on a slow day.
        """
        answer = self._call("GET", amazon.DOCUMENT_PATH.format(document_id=document_id))
        if answer.status == 429:
            raise Throttled("Amazon is rate-limiting document links.")
        if answer.status != 200 or not answer.json or not answer.json.get("url"):
            raise RuntimeError(f"Amazon would not give a link for the file (HTTP {answer.status}).")
        # Asked BEFORE the download, so an unknown compression stops this before a
        # file of rubbish is written anywhere.
        zipped = amazon.is_gzipped(answer.json)
        got = self._transport("GET", str(answer.json["url"]))
        if got.status != 200 or got.body is None:
            raise RuntimeError(
                f"The file itself would not download (HTTP {got.status}). The link lasts five "
                "minutes; if it has gone stale, ask for a new one rather than trying this again."
            )
        if not zipped:
            return got.body
        try:
            return gzip.decompress(got.body)
        except (OSError, EOFError) as wrong:
            # **NOT WRITTEN ANYWHERE.** A half-unzipped file that lands is a day
            # that reads as arrived and is not.
            raise RuntimeError(
                f"Amazon said the file was zipped and it could not be opened: {wrong}. "
                "Nothing has been written."
            ) from wrong


class Throttled(RuntimeError):
    """Amazon asked us to slow down.

    Its own class because it is the one failure that is not a fault: the answer is
    to wait, not to report anything. Told apart from a real failure so a day of
    being busy never reads as a day of being broken.
    """


# ------------------------------------------------------------ the whole thing


def fetch_one(
    door: AmazonDoor,
    report_id: str,
    data_date: date,
    put_file: Callable[[str, bytes], None],
    say: Callable[[str], None],
    asked_already: Optional[str] = None,
) -> Fetched:
    """One report, one day, from asking to landed.

    `asked_already` is the Amazon report id from a previous run that was still
    being built. **Given one, this never asks again** -- it waits. That is the rule
    that keeps a rationed request from being spent twice on one report, and it is
    the shape the reference got wrong on Flipkart.

    **NOTHING IS WRITTEN UNTIL THE BYTES ARE IN HAND AND READABLE.** The file
    lands, and only then does anything call it arrived.
    """
    which = kartaan_report(report_id)
    try:
        # What Amazon calls it, so a report still being built can be collected by
        # the next run rather than asked for again.
        theirs: Optional[str] = asked_already
        if amazon.must_be_found_not_asked(report_id):
            found = door.find_the_newest(report_id, data_date, data_date)
            if not found:
                return Fetched(
                    NOTHING_TO_FETCH, report_id, data_date,
                    say="Amazon has not published one for that day. Settlements arrive on its own cycle.",
                )
            where = amazon.read_status(found)
        else:
            if asked_already:
                say(f"{report_id}: already asked for, waiting rather than asking again.")
                where = door.where_it_got(asked_already)
            else:
                theirs = door.ask_for(report_id, data_date, data_date)
                say(f"{report_id}: asked Amazon for it.")
                where = door.where_it_got(theirs)

        if where.state == amazon.WAITING:
            # **CARRIED BACK.** This is what stops the next run asking again.
            return Fetched(STILL_WAITING, report_id, data_date, say=where.say, their_id=theirs)
        if where.state == amazon.NOTHING_TO_FETCH:
            # **NOT A FAILURE.** Amazon's own words for CANCELLED.
            return Fetched(NOTHING_TO_FETCH, report_id, data_date, say=where.say)
        # **`READY` ALREADY MEANS THERE IS A DOCUMENT.** `read_status` only answers
        # READY from the arm that has just checked for one, so a second test here
        # could never fire -- and a guard nothing can make fail reads as protection
        # that is not there.
        if where.state != amazon.READY:
            return Fetched(FAILED, report_id, data_date, say=where.say)

        body = door.download(where.document_id)
        if not body:
            # A file of nothing is not an arrival. The board would call it empty
            # anyway; saying it here means the reason is recorded with the run.
            return Fetched(
                FAILED, report_id, data_date,
                say="Amazon gave a file with nothing in it, so nothing has been written.",
            )
        name = file_name_for(which, data_date)
        put_file(name, body)
        return Fetched(LANDED, report_id, data_date, file_name=name, size=len(body),
                       say=f"Landed {name} ({len(body)} bytes).")
    except Throttled as slow:
        # **BUSY IS NOT BROKEN.** Reported as still waiting, so the day is tried
        # again rather than being written off with a reason that blames the report.
        #
        # **AND WHAT AMAZON CALLED IT GOES BACK WITH IT (cycle 46, R2#5).** The
        # request may already have been spent: `ask_for` succeeds, Amazon starts
        # building the report, and the very next call -- asking how it is getting
        # on -- is the one that is throttled. Answered without the id, nothing is
        # remembered, so tomorrow asks Amazon for a report it is already
        # building: **a rationed request spent, and two reports where there
        # should be one.** That is the fault the reference had on Flipkart, which
        # allows twenty requests a day.
        return Fetched(STILL_WAITING, report_id, data_date, say=str(slow), their_id=theirs)
    except (ValueError, PermissionError, RuntimeError) as wrong:
        return Fetched(FAILED, report_id, data_date, say=str(wrong))
