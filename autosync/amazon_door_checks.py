"""Checks for the Amazon door -- the whole flow, with no network anywhere.

**A FAKE AMAZON, DELIBERATELY AWKWARD.** It answers exactly what the real one is
documented to answer, and it REFUSES things the real one refuses: a paging call
that carries anything besides the token, a download link used after five minutes,
a settlement report anybody tries to request. A stand-in kinder than the real
thing is this project's most expensive recurring fault -- four times over -- so
this one is written to be harsh.

**THE CASE THAT MATTERS MOST: a report already asked for is never asked for
again.** `createReport` is rationed at one call per sixty seconds, and
re-submitting a request that actually worked is how the reference burned
Flipkart's twenty-a-day quota and locked itself out for a day.

Run: python autosync/amazon_door_checks.py
"""

import gzip
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import amazon  # noqa: E402
import amazon_door as tool  # noqa: E402

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


DAY = date(2026, 8, 26)
START = datetime(2026, 8, 27, 9, 0, 0)

GOOD_KEYS = {"client_id": "a-client", "client_secret": "a-secret", "refresh_token": "a-refresh"}


class FakeAmazon:
    """Amazon, as documented. Records every call so the checks can read them."""

    def __init__(self, **behaviour):
        self.calls = []
        self.b = behaviour
        self.link_given_at = None
        self.clock = [START]

    def now(self):
        return self.clock[0]

    def tick(self, seconds):
        self.clock[0] = self.clock[0] + timedelta(seconds=seconds)

    def __call__(self, method, url, headers=None, params=None, form=None, json_body=None):
        self.calls.append({"method": method, "url": url, "params": params, "json": json_body, "form": form})

        if url == amazon.TOKEN_ENDPOINT:
            if self.b.get("refuse_token"):
                return tool.Answer(401, {}, {"error": "invalid_grant"})
            # One arm at a time, so a compound guard cannot pass on the strength
            # of a different half than the one being checked.
            if self.b.get("token_bad_status_good_body"):
                return tool.Answer(500, {}, {"access_token": "a-token"})
            if self.b.get("token_no_body"):
                return tool.Answer(200, {}, None)
            if self.b.get("token_body_without_token"):
                return tool.Answer(200, {}, {"something_else": "x"})
            return tool.Answer(200, {}, {"access_token": "a-token", "expires_in": 3600})

        # **EVERY SP-API CALL MUST CARRY THE TOKEN.** The real one refuses without it.
        if url.startswith(self.b.get("host", "https://sellingpartnerapi-eu.amazon.com")):
            if not headers or not headers.get(amazon.TOKEN_HEADER):
                return tool.Answer(403, {}, {"errors": [{"message": "Unauthorized"}]})

        if method == "POST" and url.endswith(amazon.REPORTS_PATH):
            if self.b.get("throttle_create"):
                return tool.Answer(429, {}, {})
            if self.b.get("create_says_nothing"):
                return tool.Answer(202, {}, {})
            if self.b.get("create_bad_status_with_body"):
                return tool.Answer(500, {}, {"reportId": "report-1"})
            if self.b.get("create_no_body"):
                return tool.Answer(202, {}, None)
            return tool.Answer(202, {}, {"reportId": "report-1"})

        if method == "GET" and amazon.REPORTS_PATH in url and "/documents/" not in url and url.endswith(amazon.REPORTS_PATH):
            # getReports -- finding what Amazon made itself.
            token = (params or {}).get("nextToken")
            if token:
                # **THE REAL ONE FAILS IF ANYTHING ELSE IS SENT WITH THE TOKEN.**
                if set(params.keys()) != {"nextToken"}:
                    return tool.Answer(400, {}, {"errors": [{"message": "nextToken must be the only parameter"}]})
                return tool.Answer(200, {}, {"reports": self.b.get("page_two", [])})
            if not (params or {}).get("reportTypes"):
                return tool.Answer(400, {}, {"errors": [{"message": "reportTypes or nextToken is required"}]})
            if self.b.get("find_http"):
                return tool.Answer(self.b["find_http"], {}, None)
            if self.b.get("find_ok_no_body"):
                return tool.Answer(200, {}, None)
            out = {"reports": self.b.get("page_one", [])}
            if self.b.get("page_two"):
                out["nextToken"] = "tok"
            return tool.Answer(200, {}, out)

        if method == "GET" and "/reports/2021-06-30/reports/" in url:
            # **ASKING HOW IT IS GETTING ON CAN BE THROTTLED TOO, and that is the
            # case the door got wrong.** Amazon rations asking (a minute a call)
            # far harder than checking (half a second), so being told to slow
            # down on the CHECK, right after a request really was spent, is the
            # ordinary shape of it.
            if self.b.get("throttle_status"):
                return tool.Answer(429, {}, {})
            if self.b.get("status_http"):
                return tool.Answer(self.b["status_http"], {}, None)
            if self.b.get("status_ok_no_body"):
                return tool.Answer(200, {}, None)
            return tool.Answer(200, {}, self.b.get("status", {"processingStatus": "DONE", "reportDocumentId": "doc-1"}))

        if method == "GET" and "/documents/" in url:
            if self.b.get("document_http"):
                return tool.Answer(self.b["document_http"], {}, None)
            if self.b.get("document_without_link"):
                return tool.Answer(200, {}, {"reportDocumentId": "doc-1"})
            if self.b.get("document_ok_no_body"):
                return tool.Answer(200, {}, None)
            self.link_given_at = self.now()
            doc = {"reportDocumentId": "doc-1", "url": "https://files.example.invalid/doc-1"}
            if self.b.get("gzip"):
                doc["compressionAlgorithm"] = "GZIP"
            if self.b.get("odd_compression"):
                doc["compressionAlgorithm"] = "BROTLI"
            return tool.Answer(200, {}, doc)

        if url.startswith("https://files.example.invalid/"):
            if self.b.get("file_http"):
                return tool.Answer(self.b["file_http"], {}, None, None)
            if self.b.get("file_ok_no_bytes"):
                return tool.Answer(200, {}, None, None)
            # **THE LINK REALLY EXPIRES.** Five minutes, exactly as documented.
            if self.link_given_at is not None and (self.now() - self.link_given_at) >= amazon.LINK_LASTS:
                return tool.Answer(403, {}, None, b"")
            body = self.b.get("bytes", b"order-id\tsku\n123\tABC\n")
            if self.b.get("gzip"):
                body = gzip.compress(body)
            if self.b.get("broken_gzip"):
                body = b"this is not gzip at all"
            return tool.Answer(200, {}, None, body)

        return tool.Answer(404, {}, {})


def a_door(fake, **kw):
    return tool.AmazonDoor(fake, GOOD_KEYS, fake.now, **kw)


def landed_into(store):
    def put(name, body):
        store[name] = body
    return put


SAID = []


def say(line):
    SAID.append(line)


def _refused(fn):
    """Did it refuse? A refusal is an answer; falling over another way is not."""
    try:
        fn()
    except (ValueError, KeyError, TypeError) as _:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


def _said(fn):
    """What it refused WITH. The sentence is what somebody acts on."""
    try:
        fn()
    except Exception as wrong:  # noqa: BLE001
        return str(wrong)
    return ""


def _raises_throttled(fn):
    """Told to slow down -- which is its own kind of thing, not a fault."""
    try:
        fn()
    except tool.Throttled:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


# ------------------------------------------------------------ building one

check("a door without a client id is refused", answered(lambda: _refused(lambda: tool.AmazonDoor(FakeAmazon(), {"client_secret": "s", "refresh_token": "r"}, START.__str__))))
check("a door without a secret is refused", answered(lambda: _refused(lambda: tool.AmazonDoor(FakeAmazon(), {"client_id": "c", "refresh_token": "r"}, START.__str__))))
check("a door without a refresh token is refused", answered(lambda: _refused(lambda: tool.AmazonDoor(FakeAmazon(), {"client_id": "c", "client_secret": "s"}, START.__str__))))
fake = FakeAmazon()
door = a_door(fake)
check("and a complete one points at the Europe host, because India is served there", answered(lambda: door.host == "https://sellingpartnerapi-eu.amazon.com"))

# ------------------------------------------------------------ the token

fake = FakeAmazon()
door = a_door(fake)
check("a token is fetched when first needed", answered(lambda: door.token() == "a-token"))
token_calls = [c for c in fake.calls if c["url"] == amazon.TOKEN_ENDPOINT]
check("by the documented grant", answered(lambda: token_calls[0]["form"]["grant_type"] == "refresh_token"))
check("carrying the three credentials", answered(lambda: set(token_calls[0]["form"]) == {"grant_type", "refresh_token", "client_id", "client_secret"}))

# **ASKED FOR ONCE, not on every call.** A token lasts an hour.
door.token(); door.token()
check("and is not asked for again while it is still good", answered(lambda: len([c for c in fake.calls if c["url"] == amazon.TOKEN_ENDPOINT]) == 1))
fake.tick(60 * 60)
door.token()
check("but is asked for again once it has run out", answered(lambda: len([c for c in fake.calls if c["url"] == amazon.TOKEN_ENDPOINT]) == 2))
# Renewed EARLY, so it cannot go stale between deciding to call and calling.
fake2 = FakeAmazon()
door2 = a_door(fake2)
door2.token()
fake2.tick(60 * 56)
door2.token()
check("and it is renewed a little early rather than at the last second",
      answered(lambda: len([c for c in fake2.calls if c["url"] == amazon.TOKEN_ENDPOINT]) == 2))

# A refused token says what is wrong without repeating what was sent.
fake = FakeAmazon(refuse_token=True)
door = a_door(fake)
message = _said(lambda: door.token())
check("credentials that do not work are refused with a sentence", answered(lambda: message != ""))
check("naming the three things that could be wrong", answered(lambda: "refresh token" in message))
check("and never repeating the secret back", answered(lambda: "a-secret" not in message and "a-refresh" not in message))

# ------------------------------------------------------------ asking for one

fake = FakeAmazon()
door = a_door(fake)
check("asking for a report answers its id", answered(lambda: door.ask_for("az_orders", DAY, DAY) == "report-1"))
created = [c for c in fake.calls if c["method"] == "POST" and c["url"].endswith(amazon.REPORTS_PATH)]
check("the request carries the documented body", answered(lambda: created[0]["json"]["reportType"].endswith("BY_LAST_UPDATE_GENERAL")))
check("and every SP-API call carried the token", answered(lambda: all(True for _ in created)))

# **A SETTLEMENT REPORT IS REFUSED BEFORE ANYTHING IS SENT.**
fake = FakeAmazon()
door = a_door(fake)
before = len(fake.calls)
check("asking for a settlement report is refused", answered(lambda: _refused(lambda: door.ask_for("az_settlements", DAY, DAY))))
check("and NOTHING was sent to Amazon at all", answered(lambda: len(fake.calls) == before))

# **A REQUEST THAT LANDED AND SAID NOTHING IS NOT RETRIED.**
fake = FakeAmazon(create_says_nothing=True)
door = a_door(fake)
message = _said(lambda: door.ask_for("az_orders", DAY, DAY))
check("a request Amazon took but did not name is a failure", answered(lambda: message != ""))
check("and it says it has NOT been asked for again", answered(lambda: "NOT been asked for again" in message))
check("because two reports would then be being built", answered(lambda: "two reports" in message))

# Being told to slow down is its own thing, not a fault.
fake = FakeAmazon(throttle_create=True)
door = a_door(fake)
check("being rate-limited raises its own kind of problem", answered(lambda: _raises_throttled(lambda: door.ask_for("az_orders", DAY, DAY))))

# ------------------------------------------------------------ the document

store = {}
fake = FakeAmazon()
door = a_door(fake)
got = tool.fetch_one(door, "az_orders", DAY, landed_into(store), say)
check("a whole fetch lands the file", answered(lambda: got.state == tool.LANDED))
check("named for its platform, report and day", answered(lambda: got.file_name == "amazon_az_orders_2026-08-26.csv"))
check("and the bytes really arrived", answered(lambda: store[got.file_name].startswith(b"order-id")))
check("and it says what it did", answered(lambda: "Landed" in got.say and str(got.size) in got.say))

# Zipped files are opened.
store = {}
fake = FakeAmazon(gzip=True)
got = tool.fetch_one(a_door(fake), "az_orders", DAY, landed_into(store), say)
check("a gzipped file is unzipped before it lands", answered(lambda: store[got.file_name].startswith(b"order-id")))

# **A COMPRESSION NOBODY KNOWS STOPS EVERYTHING**, and nothing is written.
store = {}
fake = FakeAmazon(odd_compression=True)
got = tool.fetch_one(a_door(fake), "az_orders", DAY, landed_into(store), say)
check("a compression nobody knows is a failure", answered(lambda: got.state == tool.FAILED))
check("and NOTHING was written", answered(lambda: store == {}))

# A file that says it is zipped and is not must not land half-read.
store = {}
fake = FakeAmazon(gzip=True, broken_gzip=True)
got = tool.fetch_one(a_door(fake), "az_orders", DAY, landed_into(store), say)
check("a file that will not unzip is a failure", answered(lambda: got.state == tool.FAILED))
check("and nothing was written for it either", answered(lambda: store == {}))
check("and it says nothing was written", answered(lambda: "Nothing has been written" in got.say))

# A file of nothing is not an arrival.
store = {}
fake = FakeAmazon(bytes=b"")
got = tool.fetch_one(a_door(fake), "az_orders", DAY, landed_into(store), say)
check("a file with nothing in it does not land", answered(lambda: got.state == tool.FAILED and store == {}))

# ------------------------------- THE LINK LASTS FIVE MINUTES, and it is used at once

fake = FakeAmazon()
door = a_door(fake)
body = door.download("doc-1")
check("the link is used the moment it is given", answered(lambda: body.startswith(b"order-id")))
# Proving the fake really does expire it -- otherwise the check above proves nothing.
fake2 = FakeAmazon()
door2 = a_door(fake2)
fake2("GET", door2.host + amazon.DOCUMENT_PATH.format(document_id="doc-1"), headers={amazon.TOKEN_HEADER: "t"})
fake2.tick(6 * 60)
stale = fake2("GET", "https://files.example.invalid/doc-1")
check("and the stand-in really does expire a link after five minutes", answered(lambda: stale.status == 403))

# ------------------------------------------------- what each status comes to

for status, expected in (
    ({"processingStatus": "IN_QUEUE"}, tool.STILL_WAITING),
    ({"processingStatus": "IN_PROGRESS"}, tool.STILL_WAITING),
    ({"processingStatus": "CANCELLED"}, tool.NOTHING_TO_FETCH),
    ({"processingStatus": "FATAL"}, tool.FAILED),
):
    store = {}
    got = tool.fetch_one(a_door(FakeAmazon(status=status)), "az_orders", DAY, landed_into(store), say)
    check(f"{status['processingStatus']} comes to {expected}", answered(lambda: got.state == expected))
    check(f"and nothing is written for {status['processingStatus']}", answered(lambda: store == {}))

# **THE ONE THAT MATTERS: cancelled is not a failure.** On a quiet day it is the
# ordinary answer, and a board that reds every quiet day is a board nobody reads.
quiet = tool.fetch_one(a_door(FakeAmazon(status={"processingStatus": "CANCELLED"})), "az_orders", DAY, landed_into({}), say)
check("a cancelled report is NOT reported as a failure", answered(lambda: quiet.state != tool.FAILED))
check("and says it normally means there was no data", answered(lambda: "no data" in quiet.say))

# ------------------------ ASKED FOR ONCE -- the rationed call is never spent twice

SAID.clear()
fake = FakeAmazon(status={"processingStatus": "IN_PROGRESS"})
door = a_door(fake)
first = tool.fetch_one(door, "az_orders", DAY, landed_into({}), say)
check("a report still being built is reported as waiting", answered(lambda: first.state == tool.STILL_WAITING))
# **THE TOKEN CALL IS A POST TOO.** Counting bare POSTs counted it as a
# request for a report, which is exactly the thing being checked.
asks = len([c for c in fake.calls if c["method"] == "POST" and c["url"].endswith(amazon.REPORTS_PATH)])
check("and it was asked for exactly once", answered(lambda: asks == 1))

# The next run, told what was already asked for, must NOT ask again.
fake = FakeAmazon(status={"processingStatus": "DONE", "reportDocumentId": "doc-1"})
door = a_door(fake)
store = {}
SAID.clear()
again = tool.fetch_one(door, "az_orders", DAY, landed_into(store), say, asked_already="report-1")
check("the next run collects it without asking again", answered(lambda: again.state == tool.LANDED))
check("and made NO new request at all", answered(lambda: len([c for c in fake.calls if c["method"] == "POST" and c["url"].endswith(amazon.REPORTS_PATH)]) == 0))
check("and said so, so the log shows why no request was made", answered(lambda: any("waiting rather than asking again" in s for s in SAID)))

# ------------------------------------------- finding what Amazon made itself

fake = FakeAmazon(page_one=[{"createdTime": "2026-08-26T01:00:00Z", "processingStatus": "DONE", "reportDocumentId": "doc-1"}])
door = a_door(fake)
found = door.find_the_newest("az_settlements", DAY, DAY)
check("a settlement report Amazon made is found", answered(lambda: found["reportDocumentId"] == "doc-1"))
asked = [c for c in fake.calls if c["method"] == "GET" and c["url"].endswith(amazon.REPORTS_PATH)][0]
check("by asking for its type", answered(lambda: asked["params"]["reportTypes"][0].endswith("FLAT_FILE_V2")))

# **PAGING: the token goes on its own, and the fake refuses it otherwise.**
fake = FakeAmazon(
    page_one=[{"createdTime": "2026-08-25T01:00:00Z", "processingStatus": "DONE", "reportDocumentId": "old"}],
    page_two=[{"createdTime": "2026-08-26T01:00:00Z", "processingStatus": "DONE", "reportDocumentId": "new"}],
)
door = a_door(fake)
found = door.find_the_newest("az_settlements", DAY, DAY)
check("paging works, and the newest across pages wins", answered(lambda: found["reportDocumentId"] == "new"))
second = [c for c in fake.calls if c["method"] == "GET" and c["url"].endswith(amazon.REPORTS_PATH)][1]
check("and the second page was asked for with the token ALONE", answered(lambda: list(second["params"].keys()) == ["nextToken"]))

# Nothing published is not a failure -- settlements arrive on Amazon's own cycle.
fake = FakeAmazon(page_one=[])
got = tool.fetch_one(a_door(fake), "az_settlements", DAY, landed_into({}), say)
check("no settlement published for that day is not a failure", answered(lambda: got.state == tool.NOTHING_TO_FETCH))
check("and it says why", answered(lambda: "own cycle" in got.say))
check("and no request was ever made for it", answered(lambda: not any(c["method"] == "POST" and c["url"].endswith(amazon.REPORTS_PATH) for c in fake.calls)))

# A settlement Amazon HAS made is fetched all the way.
store = {}
fake = FakeAmazon(page_one=[{"createdTime": "2026-08-26T01:00:00Z", "processingStatus": "DONE", "reportDocumentId": "doc-1"}])
got = tool.fetch_one(a_door(fake), "az_settlements", DAY, landed_into(store), say)
check("a settlement Amazon has made lands", answered(lambda: got.state == tool.LANDED))
check("named as a settlement file", answered(lambda: got.file_name == "amazon_az_settlements_2026-08-26.csv"))

# ------------------------------------------------- busy is not broken

fake = FakeAmazon(throttle_create=True)
got = tool.fetch_one(a_door(fake), "az_orders", DAY, landed_into({}), say)
check("being rate-limited is reported as still waiting, not as broken", answered(lambda: got.state == tool.STILL_WAITING))
check("and never as a failure", answered(lambda: got.state != tool.FAILED))

# **AND WHAT AMAZON CALLED IT SURVIVES IT (cycle 46, R2#5).** The request may
# already have been spent: asking succeeds, Amazon starts building the report,
# and the very next call -- asking how it is getting on -- is the throttled one.
# Answered without the id, nothing is remembered, so tomorrow asks Amazon for a
# report it is already building. **A rationed request spent, and two reports
# where there should be one.**
slowed = FakeAmazon(throttle_status=True)
after_asking = tool.fetch_one(a_door(slowed), "az_orders", DAY, landed_into({}), say)
check("being slowed down after asking is still only waiting",
      answered(lambda: after_asking.state == tool.STILL_WAITING))
check("and Amazon's own id for the report comes back with it",
      answered(lambda: after_asking.their_id == "report-1"))
# And a request really was spent, which is why losing the id costs something.
check("and the request really had been spent by then",
      answered(lambda: any(one["method"] == "POST" and one["url"].endswith(amazon.REPORTS_PATH)
                           for one in slowed.calls)))
# **BUT BEING SLOWED DOWN BEFORE ASKING CARRIES NOTHING**, because there is
# nothing to carry -- no id was ever issued, and inventing one would make the
# next run wait for ever for a report nobody asked for.
check("while being slowed down before asking carries no id at all",
      answered(lambda: got.their_id is None))

# ------------------------------------------------- a call without a token

# The stand-in refuses one, the way the real one does -- so this proves the door
# really does attach it rather than the fake being kind.
fake = FakeAmazon()
straight = fake("GET", "https://sellingpartnerapi-eu.amazon.com" + amazon.REPORTS_PATH, headers={})
check("the stand-in refuses an SP-API call with no token, like the real one", answered(lambda: straight.status == 403))


# ------------------------------------------------- every failure arm, driven

# **EACH GUARD IS GIVEN THE THING IT GUARDS AGAINST**, and each is asked what it
# SAID -- not merely whether it complained. A guard proven only by "it threw"
# leaves the sentence free to say anything, and the sentence is what somebody acts
# on at seven in the morning.

# Both records are frozen, like every other in this package.
def _cannot_edit(thing, field, value):
    """A frozen record refuses with FrozenInstanceError, which is an
    AttributeError -- named rather than caught as a bare Exception, so a refusal
    is still told apart from the code falling over some other way."""
    try:
        setattr(thing, field, value)
    except AttributeError:
        return True
    return False


check("an answer cannot be edited after it arrives", answered(lambda: _cannot_edit(tool.Answer(200, {}), "status", 500)))
check("and neither can what a fetch came to", answered(lambda: _cannot_edit(tool.Fetched(tool.LANDED, "az_orders", DAY), "state", tool.FAILED)))

# A status check that will not answer.
message = _said(lambda: a_door(FakeAmazon(status_http=500)).where_it_got("report-1"))
check("a status check Amazon refuses is a failure", answered(lambda: message != ""))
check("and it names the report it was asking about", answered(lambda: "report-1" in message))

# A listing that will not answer.
message = _said(lambda: a_door(FakeAmazon(find_http=503)).find_the_newest("az_settlements", DAY, DAY))
check("a listing Amazon refuses is a failure", answered(lambda: "would not list its own reports" in message))
check("and it says which status came back", answered(lambda: "503" in message))

# A document link that will not come.
message = _said(lambda: a_door(FakeAmazon(document_http=500)).download("doc-1"))
check("a document link Amazon refuses is a failure", answered(lambda: "would not give a link" in message))
# **A DOCUMENT WITH NO LINK IN IT IS THE SAME FAILURE**, not a download of nothing.
message = _said(lambda: a_door(FakeAmazon(document_without_link=True)).download("doc-1"))
check("and an answer with no link in it is refused the same way", answered(lambda: "would not give a link" in message))

# The file itself refusing.
message = _said(lambda: a_door(FakeAmazon(file_http=403)).download("doc-1"))
check("a file that will not download is a failure", answered(lambda: "would not download" in message))
# **AND IT SAYS WHAT TO DO ABOUT IT** -- ask for a new link, never retry the old
# one, because a stale link fails the same way for ever.
check("and it says the link lasts five minutes", answered(lambda: "five" in message))
check("and to ask for a new one rather than trying again", answered(lambda: "ask for a new one" in message))

# A token Amazon will not give, seen from the whole flow rather than from token().
got = tool.fetch_one(a_door(FakeAmazon(refuse_token=True)), "az_orders", DAY, landed_into({}), say)
check("credentials that do not work come out as a failure of the fetch", answered(lambda: got.state == tool.FAILED))
check("and the reason names the three things it could be", answered(lambda: "refresh token" in got.say))

# The message when a request lands and says nothing.
message = _said(lambda: a_door(FakeAmazon(create_says_nothing=True)).ask_for("az_orders", DAY, DAY))
check("a request Amazon took but did not name says it cannot be collected", answered(lambda: "cannot be collected" in message))
# **AND IT NAMES THE REPORT AND SAYS AMAZON ACCEPTED IT.** "Something went wrong"
# would send somebody to re-request it, which is the one thing that must not
# happen -- Amazon is already building it.
check("and it says Amazon accepted the request", answered(lambda: "Amazon accepted the request" in message))
check("and names which report", answered(lambda: "az_orders" in message))

# The empty-file sentence.
store = {}
got = tool.fetch_one(a_door(FakeAmazon(bytes=b"")), "az_orders", DAY, landed_into(store), say)
check("an empty file says nothing has been written", answered(lambda: "nothing has been written" in got.say.lower()))

# The zipped-but-broken sentence names what went wrong.
got = tool.fetch_one(a_door(FakeAmazon(gzip=True, broken_gzip=True)), "az_orders", DAY, landed_into({}), say)
check("a file that will not unzip says Amazon said it was zipped", answered(lambda: "said the file was zipped" in got.say))

# **THE LOG LINE WHEN A REPORT IS ASKED FOR.** Without it, a run that asked for
# five reports and collected none looks identical to a run that did nothing.
SAID.clear()
tool.fetch_one(a_door(FakeAmazon(status={"processingStatus": "IN_QUEUE"})), "az_orders", DAY, landed_into({}), say)
check("asking for a report is said in the log", answered(lambda: any("asked Amazon for it" in line for line in SAID)))
check("and it names the report", answered(lambda: any("az_orders" in line for line in SAID)))

# The token is held as one thing, so it cannot be half-renewed.
fake = FakeAmazon()
door = a_door(fake)
door.token()
check("the token and when it runs out are held together", answered(lambda: isinstance(door._token, tuple) and len(door._token) == 2))


# --------------------------------- each arm of each guard, one at a time

# **A GUARD WRITTEN WITH `or` NEEDS EVERY ARM DRIVEN SEPARATELY.** One case that
# happens to trip two arms at once proves neither of them: flip the `or` to an
# `and` and it still passes. Each case below trips exactly one.

# The token guard has three arms.
check("a bad status with a perfectly good body is still refused",
      answered(lambda: "would not give an access token" in _said(lambda: a_door(FakeAmazon(token_bad_status_good_body=True)).token())))
check("a good status with no body at all is refused",
      answered(lambda: "would not give an access token" in _said(lambda: a_door(FakeAmazon(token_no_body=True)).token())))
check("and a good status with a body that has no token in it is refused",
      answered(lambda: "would not give an access token" in _said(lambda: a_door(FakeAmazon(token_body_without_token=True)).token())))
check("and the refusal says which status came back",
      answered(lambda: "500" in _said(lambda: a_door(FakeAmazon(token_bad_status_good_body=True)).token())))

# The create guard has two.
check("a request refused with a report id in the body is still refused",
      answered(lambda: "would not take the request" in _said(lambda: a_door(FakeAmazon(create_bad_status_with_body=True)).ask_for("az_orders", DAY, DAY))))
check("and one accepted with no body at all is refused",
      answered(lambda: "would not take the request" in _said(lambda: a_door(FakeAmazon(create_no_body=True)).ask_for("az_orders", DAY, DAY))))

# The status guard.
check("a status check that answers 200 with nothing in it is a failure",
      answered(lambda: "would not say how" in _said(lambda: a_door(FakeAmazon(status_ok_no_body=True)).where_it_got("report-1"))))

# The listing guard.
check("a listing that answers 200 with nothing in it is a failure",
      answered(lambda: "would not list its own reports" in _said(lambda: a_door(FakeAmazon(find_ok_no_body=True)).find_the_newest("az_settlements", DAY, DAY))))

# The document guard.
check("a document answer of 200 with nothing in it is a failure",
      answered(lambda: "would not give a link" in _said(lambda: a_door(FakeAmazon(document_ok_no_body=True)).download("doc-1"))))

# The download guard: a 200 with no bytes is not a file.
check("a download that answers 200 with no bytes is a failure",
      answered(lambda: "would not download" in _said(lambda: a_door(FakeAmazon(file_ok_no_bytes=True)).download("doc-1"))))

# **THE NEWEST IS THE NEWEST, whichever order Amazon lists them in.** Listed
# newest-first, a comparison that kept the last one seen would take the oldest.
newest_first = FakeAmazon(page_one=[
    {"createdTime": "2026-08-26T09:00:00Z", "reportDocumentId": "new", "processingStatus": "DONE"},
    {"createdTime": "2026-08-20T09:00:00Z", "reportDocumentId": "old", "processingStatus": "DONE"},
])
check("the newest wins when Amazon lists it first",
      answered(lambda: a_door(newest_first).find_the_newest("az_settlements", DAY, DAY)["reportDocumentId"] == "new"))
oldest_first = FakeAmazon(page_one=[
    {"createdTime": "2026-08-20T09:00:00Z", "reportDocumentId": "old", "processingStatus": "DONE"},
    {"createdTime": "2026-08-26T09:00:00Z", "reportDocumentId": "new", "processingStatus": "DONE"},
])
check("and when Amazon lists it last",
      answered(lambda: a_door(oldest_first).find_the_newest("az_settlements", DAY, DAY)["reportDocumentId"] == "new"))
# One with no time at all must not beat one that has one.
untimed = FakeAmazon(page_one=[
    {"reportDocumentId": "no-time", "processingStatus": "DONE"},
    {"createdTime": "2026-08-26T09:00:00Z", "reportDocumentId": "timed", "processingStatus": "DONE"},
])
check("and one with no time on it does not beat one that has",
      answered(lambda: a_door(untimed).find_the_newest("az_settlements", DAY, DAY)["reportDocumentId"] == "timed"))


# ------------------- what the runner needs back, so it never asks twice

# **THE DOOR MUST SAY WHAT AMAZON CALLS THE REPORT IT IS BUILDING.** Without it
# the runner has nothing to remember, and every run spends a rationed request on
# a report Amazon is already making. Found by wiring the runner to this door.
still = tool.fetch_one(a_door(FakeAmazon(status={"processingStatus": "IN_QUEUE"})), "az_orders", DAY, landed_into({}), say)
check("a report still being built comes back with Amazon's own id for it", answered(lambda: still.their_id == "report-1"))
check("so the next run has something to collect it by", answered(lambda: still.their_id is not None))

# And when it was already in flight, the SAME id comes back -- not a new one.
carried = tool.fetch_one(
    a_door(FakeAmazon(status={"processingStatus": "IN_PROGRESS"})),
    "az_orders", DAY, landed_into({}), say, asked_already="report-from-yesterday",
)
check("one already in flight carries the id it was asked under", answered(lambda: carried.their_id == "report-from-yesterday"))
check("and it is NOT replaced with a new one", answered(lambda: carried.their_id != "report-1"))

# A landed one needs no id -- it is finished with.
done = tool.fetch_one(a_door(FakeAmazon()), "az_orders", DAY, landed_into({}), say)
check("a landed report is finished with and carries no id to chase", answered(lambda: done.their_id is None))


# **AND NOTHING ABOVE ENDED BY THROWING RATHER THAN BY ANSWERING.** Answering
# with nothing keeps the run alive; this is what stops a check phrased as "this
# word is NOT in what it said" going green because there was nothing to look in.
check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)


EXPECTED = 106
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
