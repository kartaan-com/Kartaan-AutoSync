"""The only file in the package that opens a connection.

**EVERY OTHER FILE HAS A TRANSPORT HANDED IN.** That is what lets the whole of
auto-sync -- tokens, requests, waiting, paging, throttling, unzipping, uploading
-- be checked with no account, no token and no internet. This is the one place
where that stops being true, so it is deliberately the smallest and dullest file
here: it makes a call and says what came back. **It decides nothing.**

**NOTHING IS ADDED TO THE PACKAGE TO DO THIS.** `urllib.request` is in Python
itself. A fetching library would be one more thing to keep current, one more
thing to trust, and one more thing that could be swapped under the job in a
seller's own repository -- for something two doors need and neither of them needs
much of.

**THE TWO DOORS ASK FOR DIFFERENT SHAPES, and they are not made into one.**
Amazon's door takes a plain callable; Drive's takes something with `get`, `post`,
`put` and `delete`. Both contracts are written down at the top of their own door
and were built before this file existed. Bending either one to match the other
would be changing a checked thing to suit an unchecked one.

**AND IT NEVER RETRIES.** Retrying is a decision -- how long to wait, whether the
failure is even the kind worth trying again -- and every one of those decisions
already lives in a door where it can be read and checked. A quiet retry in here
would be a second, invisible policy underneath the visible one.

**WHAT IT REFUSES TO DO WITH A CREDENTIAL:** it never writes one anywhere. Not to
the log, not into an error message, not into the address of a request. The one
place a secret is read is the environment, and the one place it goes is the
header of the call it is for. Golden Rule 8.
"""

import json as _json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional

from amazon_door import Answer

# How long any one call may take before it is given up on.
#
# **EVERY CALL OUT OF THIS PACKAGE HAS ONE.** A hung call with no timeout does not
# fail -- it parks, silently, until something else kills the job, and the run log
# ends mid-sentence with nothing saying why. That is on the register twice.
#
# Generous, because a large report genuinely takes a while to come down, and a
# timeout that fires on a slow-but-working day is a failure this invented.
HOW_LONG_TO_WAIT = 300

# Google's own token endpoint, and the shape of the request to it, read from
# Google's documentation for a refresh token exchange (2026-08-28): POST, form
# encoded, `client_id`, `client_secret`, `refresh_token`, `grant_type`.
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

# Google says how long its access token lasts in the answer. Treated as ending
# slightly sooner, so a token cannot go stale between deciding to use it and
# using it -- the same margin `AmazonDoor` keeps, for the same reason.
RENEW_EARLY = timedelta(minutes=5)

# What a token is assumed to last if Google does not say. It always says; this is
# only here so a missing field cannot mean "lasts for ever".
IF_GOOGLE_DOES_NOT_SAY = timedelta(minutes=30)


def _address(url: str, params: Optional[Dict]) -> str:
    """The address with its questions attached.

    **BUILT WITH THE ENCODER, NEVER BY JOINING STRINGS.** Drive's searches contain
    spaces, quotes and apostrophes -- `name = 'az_orders' and ... in parents` --
    and a hand-built address turns the first space into a broken request that
    comes back as a refusal about the query rather than about the address.
    """
    if not params:
        return url
    joined = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    if not joined:
        return url
    return f"{url}{'&' if '?' in url else '?'}{joined}"


def _headers_of(reply) -> Dict[str, str]:
    """What came back, as a plain mapping that can be asked about by name.

    Kept case-insensitive on purpose. Drive's resumable upload answers a
    `Location` header, and a server is free to send it back as `location` --
    which would read as Drive having agreed to take a file and not said where,
    and stop an upload that was working.
    """
    out: Dict[str, str] = {}
    for name, value in (reply.headers or {}).items():
        out[name] = value
        out[name.lower()] = value
    return out


def _call(
    method: str,
    url: str,
    headers: Optional[Dict] = None,
    params: Optional[Dict] = None,
    body: Optional[bytes] = None,
    timeout: int = HOW_LONG_TO_WAIT,
):
    """One call. Answers `(status, headers, bytes)`.

    **A REFUSAL IS AN ANSWER, NOT AN ACCIDENT.** `urllib` treats every 4xx and 5xx
    as an exception to be thrown. Both doors read the status themselves -- 429 is
    "wait", 404 can be "there is nothing there", and Drive's own refusals carry
    the sentence a person needs -- so a thrown 429 would arrive as a broken run
    instead of a busy one. Turned back into a plain answer here.

    **What is still thrown is the case where the call never got there at all**:
    no network, no name, no route. That is what the Amazon door's contract says
    this raises for, and it is genuinely different from being told no.
    """
    request = urllib.request.Request(
        _address(url, params),
        data=body,
        headers={k: v for k, v in (headers or {}).items() if v is not None},
        method=method.upper(),
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as reply:
            return reply.status, _headers_of(reply), reply.read()
    except urllib.error.HTTPError as refused:
        # The body of a refusal is the part that says what was wrong with it.
        return refused.code, _headers_of(refused), refused.read()


def _decoded(raw: Optional[bytes]) -> Optional[Dict]:
    """The answer read as Google or Amazon meant it, or None.

    **None MEANS THERE WAS NOTHING TO READ, and both doors are built to tell that
    apart from an empty answer.** `amazon_door` had a real fault here once -- an
    accepted-but-silent reply is `{}`, which is falsy, and testing it with `not`
    sent it down the "Amazon refused this" path with a sentence blaming the
    request. So a body that is genuinely not readable answers None and a body
    that is an empty object answers an empty object.
    """
    if not raw:
        return None
    try:
        got = _json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return got if isinstance(got, dict) else None


# --------------------------------------------------------------------- Amazon


def for_amazon(timeout: int = HOW_LONG_TO_WAIT) -> Callable[..., Answer]:
    """The callable `AmazonDoor` was written against.

    Its contract, from the top of `amazon_door.py` and matched here exactly:

        transport(method, url, headers=None, params=None, form=None, json_body=None)
            -> Answer(status, headers, json, body)

    **`form` AND `json_body` ARE NOT THE SAME THING and cannot be merged.** The
    token call is form-encoded because that is what Amazon's sign-in expects; the
    report calls are JSON because that is what its reports service expects.
    Sending either as the other gets a refusal that names neither.
    """

    def talk(
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        params: Optional[Dict] = None,
        form: Optional[Dict] = None,
        json_body: Optional[Dict] = None,
    ) -> Answer:
        sending = dict(headers or {})
        body: Optional[bytes] = None
        if form is not None:
            body = urllib.parse.urlencode(form).encode("utf-8")
            sending["Content-Type"] = "application/x-www-form-urlencoded"
        elif json_body is not None:
            body = _json.dumps(json_body).encode("utf-8")
            sending["Content-Type"] = "application/json"
        status, got_headers, raw = _call(method, url, sending, params, body, timeout)
        # **THE BYTES ARE KEPT AS WELL AS THE READING.** A report document is a
        # file, not an object, and `download` reads `body`; the status calls read
        # `json`. One answer carries both so the transport never has to guess
        # which kind of call it was just used for.
        return Answer(status=status, headers=got_headers, json=_decoded(raw), body=raw)

    return talk


# --------------------------------------------------------------------- Google


@dataclass
class Reply:
    """What came back, in the shape `drive_door.py` reads.

    `ok`, `status`, `text`, `headers` and `json()` -- the five things that file
    asks for, and nothing else.
    """

    status: int
    headers: Dict[str, str]
    raw: bytes

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    @property
    def text(self) -> str:
        return (self.raw or b"").decode("utf-8", "replace")

    def json(self) -> Optional[Dict]:
        return _decoded(self.raw)


class Google:
    """A way of talking to Drive that keeps the seller's token alive.

    **THE REFRESH TOKEN IS READ ONCE AND NEVER LEAVES THIS OBJECT.** It goes to
    Google's own token endpoint and nowhere else. Nothing here puts it in a
    message, an address or a log line, and the sentence raised when Google says
    no names the status and not what was sent.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        now: Callable[[], datetime],
        timeout: int = HOW_LONG_TO_WAIT,
    ):
        for named, value in (
            ("client id", client_id),
            ("client secret", client_secret),
            ("refresh token", refresh_token),
        ):
            if not value:
                # **REFUSED HERE, NAMED.** Built without one, the first call comes
                # back as an authorization failure that says nothing about which
                # of the three is missing -- and that is a person's evening.
                raise ValueError(f"Talking to Drive needs a Google {named} and was not given one.")
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._now = now
        self._timeout = timeout
        # **ONE FIELD, NOT TWO.** The token and when it ends held together, so
        # they cannot disagree -- the fault `AmazonDoor` was corrected for, where
        # an empty token short-circuited before the expiry could ever be read.
        self._token: Optional[tuple] = None

    def token(self) -> str:
        """A live access token, asked for again only when the old one is near its end."""
        if self._token and self._now() < self._token[1]:
            return self._token[0]
        status, _, raw = _call(
            "POST",
            GOOGLE_TOKEN_ENDPOINT,
            {"Content-Type": "application/x-www-form-urlencoded"},
            None,
            urllib.parse.urlencode(
                {
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "refresh_token": self._refresh_token,
                    "grant_type": "refresh_token",
                }
            ).encode("utf-8"),
            self._timeout,
        )
        said = _decoded(raw)
        if status != 200 or not said or not said.get("access_token"):
            # **THE STATUS, NOT THE BODY.** A refusal from a sign-in can carry
            # back what was sent to it, and this sentence goes into a log that
            # ends up in the seller's own Drive.
            #
            # And the likeliest cause is named, because it is documented and it
            # is silent: while the Kartaan app is still in Google's "Testing"
            # state, every refresh token it issues dies after SEVEN DAYS.
            raise PermissionError(
                f"Google would not give an access token (HTTP {status}). The client id, secret "
                "or refresh token is wrong, has been revoked, or has expired -- a refresh token "
                "issued while the app is in Testing lasts seven days."
            )
        lasts = said.get("expires_in")
        for_how_long = timedelta(seconds=int(lasts)) if lasts else IF_GOOGLE_DOES_NOT_SAY
        self._token = (str(said["access_token"]), self._now() + for_how_long - RENEW_EARLY)
        return self._token[0]

    def _talk(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        json: Optional[Dict] = None,
        data: Optional[bytes] = None,
    ) -> Reply:
        sending = dict(headers or {})
        sending["Authorization"] = f"Bearer {self.token()}"
        body = data
        if json is not None and data is None:
            body = _json.dumps(json).encode("utf-8")
            sending.setdefault("Content-Type", "application/json; charset=UTF-8")
        status, got_headers, raw = _call(method, url, sending, params, body, self._timeout)
        return Reply(status=status, headers=got_headers, raw=raw)

    def get(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Reply:
        return self._talk("GET", url, params=params, headers=headers)

    def post(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        json: Optional[Dict] = None,
        data: Optional[bytes] = None,
    ) -> Reply:
        return self._talk("POST", url, params=params, headers=headers, json=json, data=data)

    def put(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        json: Optional[Dict] = None,
        data: Optional[bytes] = None,
    ) -> Reply:
        return self._talk("PUT", url, params=params, headers=headers, json=json, data=data)

    def delete(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Reply:
        return self._talk("DELETE", url, params=params, headers=headers)
