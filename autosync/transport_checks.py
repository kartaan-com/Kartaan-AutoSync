"""Checks for the one file that opens a connection.

**IT IS CHECKED WITH NO NETWORK, by standing in for the one function that makes
the call.** That is the only thing replaced -- everything above it is the real
code -- and the stand-in is deliberately UNKIND: it answers exactly what a server
answers, including refusals, and it records what it was handed so the checks can
ask whether the right request was actually built. **A stand-in kinder than the
real thing has been the second most expensive repeat fault in this project**, so
this one hands back 429s, empty bodies and bad JSON, and never guesses.

**THE ONE THAT MATTERS MOST: A CREDENTIAL NEVER COMES BACK OUT.** Not in an
answer, not in a refusal, not in the address of a request. Golden Rule 8, and it
is asked here rather than trusted.

Run: python autosync/transport_checks.py
"""

import email.message
import io
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import transport as tool  # noqa: E402

ran = 0
failures = []
THREW = []


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


def answered(work):
    try:
        return work()
    except Exception as wrong:  # noqa: BLE001
        THREW.append(repr(wrong))
        return None


def refused(work):
    try:
        work()
        return None
    except Exception as wrong:  # noqa: BLE001
        return wrong


# --------------------------------------------------- the address

check("no questions leaves the address alone",
      answered(lambda: tool._address("https://x/y", None)) == "https://x/y")
check("and an empty set of questions leaves it alone too",
      answered(lambda: tool._address("https://x/y", {})) == "https://x/y")
# **BUILT WITH THE ENCODER, NEVER BY JOINING STRINGS.** Drive's searches carry
# spaces and quotes, and a hand-built address turns the first space into a
# refusal about the query rather than about the address.
check("a search with spaces and quotes is encoded",
      " " not in (answered(lambda: tool._address("https://x", {"q": "name = 'a b'"})) or " "))
check("and the words themselves survive the encoding",
      "name" in (answered(lambda: tool._address("https://x", {"q": "name = 'a b'"})) or ""))
check("an address that already has a question gets an ampersand, not a second question mark",
      answered(lambda: tool._address("https://x?a=1", {"b": "2"})) == "https://x?a=1&b=2")
# Nothing is not a value. Sent, it becomes the four letters `None`.
check("a question with no answer is left out entirely",
      answered(lambda: tool._address("https://x", {"a": "1", "b": None})) == "https://x?a=1")

# --------------------------------------------------- reading what came back

check("nothing to read answers nothing", answered(lambda: tool._decoded(b"")) is None)
check("and no bytes at all answers nothing", answered(lambda: tool._decoded(None)) is None)
check("something that is not readable answers nothing",
      answered(lambda: tool._decoded(b"<html>no</html>")) is None)
# **AN EMPTY ANSWER IS NOT THE SAME AS NO ANSWER.** `amazon_door` had a real
# fault here: an accepted-but-silent reply is `{}`, which is falsy, and testing
# it with `not` sent it down the "Amazon refused this" path with a sentence
# blaming the request.
check("an empty answer comes back as an empty answer, not as nothing",
      answered(lambda: tool._decoded(b"{}")) == {})
check("a list where a record was expected answers nothing",
      answered(lambda: tool._decoded(b"[1,2]")) is None)
check("an ordinary answer is read", answered(lambda: tool._decoded(b'{"a": 1}')) == {"a": 1})


class FakeHeaders:
    """What a real reply's headers behave like -- a thing you can walk in pairs."""

    def __init__(self, pairs):
        self._pairs = pairs

    def items(self):
        return list(self._pairs)


class Said:
    def __init__(self, pairs):
        self.headers = FakeHeaders(pairs)


# **A SERVER MAY SEND A HEADER BACK IN ANY CASE IT LIKES.** Drive's resumable
# upload answers `Location`; asked for as `location` and not found, it would read
# as Drive having agreed to take a file and not said where -- and stop an upload
# that was working.
seen = answered(lambda: tool._headers_of(Said([("Location", "https://up/1")])))
check("a header can be asked for by the name it was sent under",
      (seen or {}).get("Location") == "https://up/1")
check("and by that name in small letters",
      (seen or {}).get("location") == "https://up/1")

# --------------------------------------------------- standing in for the network

# **THE STAND-IN SITS AT THE REAL BOUNDARY, not one step inside it.** It replaces
# `urlopen` -- the actual call out -- so everything this file does above that is
# the REAL code being checked: building the address, choosing the method, dropping
# headers with no value, and turning a refusal back into an answer.
#
# **Standing in for `_call` instead was the first attempt and it was wrong**: it
# left the whole of `_call` unchecked, and twenty-two deliberate breakages of it
# went unnoticed. A stand-in placed one step too high proves the code above it and
# quietly excuses everything below.

CALLS = []
ANSWERS = []


def head(pairs):
    """Headers exactly as a real reply carries them -- an email message."""
    made = email.message.Message()
    for name, value in pairs:
        made[name] = value
    return made


class FakeReply:
    def __init__(self, status, headers, body):
        self.status = status
        self.headers = head(headers)
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def fake_urlopen(request, timeout=None):
    CALLS.append({
        "method": request.get_method(),
        "url": request.full_url,
        "headers": dict(request.header_items()),
        "body": request.data,
        "timeout": timeout,
    })
    status, headers, body = ANSWERS.pop(0) if ANSWERS else (200, [], b"{}")
    if status >= 400:
        # **A REAL SERVER REFUSAL ARRIVES AS AN EXCEPTION**, and turning it back
        # into an answer is one of the things being checked. A stand-in that
        # politely returned a 429 would have proved nothing.
        raise tool.urllib.error.HTTPError(
            request.full_url, status, "no", head(headers), io.BytesIO(body)
        )
    return FakeReply(status, headers, body)


# **REACHED THROUGH THE MODULE ITSELF, not imported here.** Imported here, the
# checks file would have loaded `urllib.request` on its own account -- and then
# deleting that import from the file under check would go unnoticed, because the
# submodule was already there. The checks file must not prop up the thing it is
# checking.
tool.urllib.request.urlopen = fake_urlopen


def afresh(*answers):
    CALLS.clear()
    ANSWERS.clear()
    ANSWERS.extend(answers)


def sent(which, name):
    """One header of a recorded call, whatever case it was stored under.

    `urllib` rewrites header names as it stores them -- `Content-Type` becomes
    `Content-type` -- so asking for the name as written would answer nothing and
    the check would go red about the wrong thing.
    """
    for was, value in (which.get("headers") or {}).items():
        if was.lower() == name.lower():
            return value
    return None


# --------------------------------------------------- Amazon's shape

talk = tool.for_amazon()

afresh((200, [("x", "1")], b'{"reportId": "77"}'))
got = answered(lambda: talk("POST", "https://sp/reports", headers={"h": "v"}, json_body={"a": 1}))
check("what Amazon sent back is handed on as its status", got.status == 200)
check("and its headers", got.headers.get("x") == "1")
check("and read, for the calls that read it", got.json == {"reportId": "77"})
# **THE BYTES ARE KEPT AS WELL AS THE READING.** A report document is a file, not
# a record, and `download` reads the bytes.
check("and kept as bytes, for the calls that download a file", got.body == b'{"reportId": "77"}')
check("a request with a record in it is sent as JSON",
      sent(CALLS[0], "Content-Type") == "application/json")
check("and the record is actually in the body", b'"a": 1' in (CALLS[0]["body"] or b""))
check("and whatever headers it was given are still there", sent(CALLS[0], "h") == "v")

# **`form` AND `json_body` ARE NOT THE SAME THING.** The sign-in expects one and
# the reports service expects the other; sending either as the other gets a
# refusal that names neither.
afresh((200, [], b'{"access_token": "x"}'))
answered(lambda: talk("POST", "https://api.amazon.com/auth/o2/token", form={"grant_type": "refresh_token"}))
check("a sign-in is sent as a form, not as JSON",
      sent(CALLS[0], "Content-Type") == "application/x-www-form-urlencoded")
check("and the form is encoded, not written out as a record",
      CALLS[0]["body"] == b"grant_type=refresh_token")

afresh((200, [], b"{}"))
answered(lambda: talk("GET", "https://sp/reports", params={"p": "1"}))
check("a call with nothing to send sends nothing", CALLS[0]["body"] is None)
check("and its questions are put on the address", CALLS[0]["url"].endswith("?p=1"))
check("the method is used as it was given", CALLS[0]["method"] == "GET")

# **BEING TOLD TO SLOW DOWN IS AN ANSWER, NOT AN ACCIDENT.** The door reads 429
# itself and waits; thrown, it would arrive as a broken run instead of a busy
# one, and a day of being busy would read as a day of being broken.
afresh((429, [], b'{"errors": []}'))
check("a refusal comes back as an answer with its status on it",
      answered(lambda: talk("GET", "https://sp/reports")).status == 429)
afresh((404, [], b""))
check("and so does not-found, with nothing to read",
      answered(lambda: talk("GET", "https://sp/x")).json is None)

check("every call is given a limit on how long it may take",
      answered(lambda: tool.HOW_LONG_TO_WAIT) > 0)

# --------------------------------------------------- what came back, Drive's shape

check("a reply in the two hundreds is a yes", tool.Reply(204, {}, b"").ok is True)
check("a refusal is not", tool.Reply(400, {}, b"no").ok is False)
check("and neither is a server falling over", tool.Reply(500, {}, b"").ok is False)
check("a refusal can be read as words", tool.Reply(400, {}, b"no room").text == "no room")
check("and bytes that are not words do not stop it being read",
      isinstance(tool.Reply(400, {}, b"\xff\xfe").text, str))
check("a reply can be read as a record", tool.Reply(200, {}, b'{"id": "1"}').json() == {"id": "1"})
check("and the bytes themselves are there, which is how a file is read back",
      tool.Reply(200, {}, b"abc").raw == b"abc")

# --------------------------------------------------- Google

NOW = datetime(2026, 8, 28, 20, 30)


def a_google(client_id="cid", client_secret="secret", refresh_token="REFRESH-TOKEN-VALUE"):
    return tool.Google(client_id, client_secret, refresh_token, now=lambda: NOW)


# **REFUSED HERE, NAMED.** Built without one, the first call comes back as an
# authorization failure that says nothing about which of the three is missing --
# and that is somebody's evening.
for missing, named in (
    ({"client_id": ""}, "client id"),
    ({"client_secret": ""}, "client secret"),
    ({"refresh_token": ""}, "refresh token"),
):
    wrong = refused(lambda m=missing: a_google(**m))
    check(f"a way in built with no {named} refuses at once", wrong is not None)
    check(f"and the refusal says it was the {named} that was missing",
          named in str(wrong))

afresh((200, [], b'{"access_token": "AAA", "expires_in": 3600}'))
google = a_google()
check("a token is asked for and handed back", answered(google.token) == "AAA")
check("it is asked for at Google's own token address",
      CALLS[0]["url"] == tool.GOOGLE_TOKEN_ENDPOINT)
check("and asked for by POST, never by fetching an address",
      CALLS[0]["method"] == "POST")
check("as a form, which is what Google documents",
      sent(CALLS[0], "Content-Type") == "application/x-www-form-urlencoded")
check("and it says it is refreshing rather than signing in for the first time",
      b"grant_type=refresh_token" in (CALLS[0]["body"] or b""))
# **ALL THREE, OR GOOGLE REFUSES AND THE REASON NAMES NONE OF THEM.**
for part in (b"client_id=cid", b"client_secret=secret", b"refresh_token=REFRESH-TOKEN-VALUE"):
    check(f"the sign-in carries its {part.decode().split('=')[0].replace('_', ' ')}",
          part in (CALLS[0]["body"] or b""))
# **EVERY CALL OUT OF HERE IS GIVEN A LIMIT.** A hung call with no limit does not
# fail -- it parks until something else kills the job.
check("and the call is given a limit on how long it may take",
      CALLS[0]["timeout"] == tool.HOW_LONG_TO_WAIT)
# **THE LIMIT THIS WAY IN WAS GIVEN, not whatever the default happens to be.**
# Checked against a different number on purpose: asked with the same one, the
# check passes whether the limit is being carried through or quietly ignored.
afresh((200, [], b'{"access_token": "AAA", "expires_in": 3600}'))
answered(tool.Google("cid", "secret", "rt", now=lambda: NOW, timeout=7).token)
check("and it is the limit this way in was given, not the usual one",
      CALLS[0]["timeout"] == 7)

# **ASKED FOR ONCE.** A new token on every call is slow, and rude to Google.
before = len(CALLS)
check("a token still good is not asked for again", answered(google.token) == "AAA")
check("and nothing was sent to ask", len(CALLS) == before)

# **RENEWED EARLY**, so a token cannot go stale between deciding to use it and
# using it.
afresh((200, [], b'{"access_token": "BBB", "expires_in": 3600}'))
soon = tool.Google("cid", "secret", "rt", now=lambda: NOW + timedelta(minutes=56, seconds=30))
check("a token close to its end is replaced", answered(soon.token) == "BBB")

# **A REFUSAL SAYS THE STATUS AND NOTHING THAT WAS SENT.** The body of a refusal
# from a sign-in can carry back what was sent to it, and this sentence ends up in
# a log in the seller's own Drive.
afresh((400, [], b'{"error": "invalid_grant", "sent": "REFRESH-TOKEN-VALUE"}'))
turned_away = refused(a_google().token)
check("being turned away raises rather than answering an empty token",
      isinstance(turned_away, PermissionError))
check("and it says which status Google gave", "400" in str(turned_away))
check("THE REFRESH TOKEN IS NOT IN THE REFUSAL", "REFRESH-TOKEN-VALUE" not in str(turned_away))
# The likeliest cause is documented and silent, so it is named rather than left
# for somebody to find: a refresh token issued while the app is in Google's
# Testing state dies after seven days.
check("and it names the seven-day expiry, which is the likeliest cause",
      "seven days" in str(turned_away))

afresh((200, [], b'{"expires_in": 3600}'))
check("an answer with no token in it is a refusal, not an empty token",
      isinstance(refused(a_google().token), PermissionError))
# **EVERY ONE OF THE THREE REASONS IS ENOUGH ON ITS OWN.** A refusal that happens
# to carry a token-shaped field is still a refusal.
afresh((400, [], b'{"access_token": "SNEAKY"}'))
check("a token in a refused answer is not taken",
      isinstance(refused(a_google().token), PermissionError))
afresh((200, [], b"not a record at all"))
check("and neither is one in an answer that cannot be read",
      isinstance(refused(a_google().token), PermissionError))

# **A TOKEN WITH NO STATED LIFE DOES NOT LAST FOR EVER.** Google always says; this
# is only so that a missing field cannot mean "never renew".
afresh((200, [], b'{"access_token": "CCC"}'))
quiet = a_google()
check("a token Google did not put a life on is still taken", answered(quiet.token) == "CCC")
check("and it is treated as short-lived rather than endless",
      tool.IF_GOOGLE_DOES_NOT_SAY < timedelta(hours=2))

# --------------------------------------------------- talking to Drive

afresh(
    (200, [], b'{"access_token": "AAA", "expires_in": 3600}'),
    (200, {}, b'{"files": []}'),
)
drive = a_google()
reply = answered(lambda: drive.get("https://drive/files", params={"q": "x"}))
check("a call to Drive carries the token", sent(CALLS[1], "Authorization") == "Bearer AAA")
check("and its questions, on the address", "q=x" in CALLS[1]["url"])
check("and what came back is in the shape the door reads", reply.json() == {"files": []})
# **THE TOKEN IS NEVER PUT IN THE ADDRESS.** An address is written into logs by
# everything that handles it.
check("the token is not in the address", "AAA" not in CALLS[1]["url"])

afresh((200, [], b'{"access_token": "AAA", "expires_in": 3600}'), (200, [], b"{}"))
answered(lambda: drive.post("https://drive/files", json={"name": "a"}))
check("a record sent to Drive goes as JSON",
      "application/json" in (sent(CALLS[-1], "Content-Type") or ""))
check("and the record is in the body", b'"name": "a"' in (CALLS[-1]["body"] or b""))

# **A CALLER THAT SAYS WHAT IT IS SENDING IS BELIEVED.** The multipart upload
# builds its own body and its own content type, and a transport that overrode it
# would break every upload over five megabytes.
afresh((200, [], b'{"access_token": "AAA", "expires_in": 3600}'), (200, [], b"{}"))
answered(lambda: drive.post("https://up", headers={"Content-Type": "multipart/related; boundary=b"},
                            data=b"--b--"))
check("a body the caller built is sent exactly as given", CALLS[-1]["body"] == b"--b--")
check("and the kind it says it is, is not overruled",
      sent(CALLS[-1], "Content-Type") == "multipart/related; boundary=b")

# **THE BODY A CALLER BUILT WINS.** The multipart upload builds both its body and
# its own description of what is in it; writing a record over that would break
# every upload of a file over five megabytes.
afresh((200, [], b'{"access_token": "AAA", "expires_in": 3600}'), (200, [], b"{}"))
answered(lambda: drive.post("https://up", json={"name": "a"}, data=b"RAW"))
check("and it is still what is sent when a record is handed over as well",
      CALLS[-1]["body"] == b"RAW")

for method, use in (("PUT", lambda: drive.put("https://up/1", data=b"x")),
                    ("DELETE", lambda: drive.delete("https://drive/files/1"))):
    afresh((200, [], b'{"access_token": "AAA", "expires_in": 3600}'), (200, [], b"{}"))
    answered(use)
    check(f"a {method.lower()} is sent as a {method}", CALLS[-1]["method"] == method)

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 76
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
