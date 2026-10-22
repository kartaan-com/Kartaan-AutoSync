"""Asking Kartaan's Server whether this run may fetch, BEFORE it fetches (plan job 30, the run's half).

**WHY THE RUN ASKS.** A seller's run holds its secrets in their own repository and, until this file, asked Kartaan
nothing before it fetched. Kartaan's Server now answers `POST /may-fetch` (Kartaan-Server `server/fetching.py`,
tag v0.1.9): the body is a FORM with one field, `pass` -- the run pass, a repository secret named
`KARTAAN_RUN_PASS` -- and the answer is JSON `{"fetch": true|false, "said": "a sentence"}`. `said` is written for
the seller and is printed as it stands. Statuses: 200 with `fetch` true is a yes. 403 (a bad or old pass), 429 (too
many asks today), 503 (the Server could not check) and a 200 with `fetch` false are all a no.

**EVERY RULE AND EVERY SENTENCE IS HERE, NOT IN `start.py`.** `start.py` needs a real network and is `pragma: no cover`;
a rule written there is a rule nobody ever watches fail (D171). So the asking is a plain function, the network is
handed in as `post`, and `may_fetch_checks.py` drives every case with nothing connected and proves each rule by
breaking it. The ONE real-network function, `the_real_post`, is a few lines over `transport._call` and decides nothing.

**THE RULES, AS CONTROL DECIDED THEM:**

| What the run finds | What it does |
|---|---|
| No pass in the environment | CANNOT ask: carries on fetching, and says so loudly (transitional -- see below). **From `NO_PASS_STOPS_FROM`, once Control sets it, it does not fetch and exits 0; before it, it warns with the days left** |
| Pass, Server says `fetch` true | goes |
| Pass, Server says `fetch` false (any status) | does NOT fetch; prints the Server's sentence, then that nothing was fetched and nothing was deleted; exits 0 -- a deliberate stop is not a defect |
| Pass, Server unreachable / timed out / not JSON / an unexpected shape | does NOT fetch; says in words that Kartaan could not be reached and the next run asks again; exits 1 (nothing was asked of anyone, so it is not a deliberate stop) |

**NEEDS A DECISION FROM CONTROL -- THE NO-PASS CASE IS TRANSITIONAL.** A repository set up before job 48 holds no
`KARTAAN_RUN_PASS`. Stopping those runs would stop every existing seller the day this ships; carrying on fetching
means a seller who never presses Connect GitHub again is never checked. It carries on, loudly, until Control says the
day it becomes a stop. Also for Control: a 503 with the Server's own sentence ("could not check your plan") is treated
as the Server speaking, so exits 0 like any other no; if a Server that cannot check should leave the job red, that is
one line in `decide`.

**THE PASS IS NEVER PRINTED, LOGGED OR PUT IN AN ADDRESS.** It travels in the body of the one call it is for. No
sentence here includes it, an error is named by its kind and never by its text, and a sentence the Server sends is
stripped of the pass if it ever contained it. Golden Rule 8.

**NOTHING IS EVER DELETED BY A NO.** The Server's sentences say so too; the line printed after them says it once more
in this file's own words, because it is the part a seller most needs to be told.
"""

import urllib.parse
from dataclasses import dataclass
from datetime import date
from typing import Callable, Dict, Optional, Tuple

# Where the question goes, and the name of the one field it carries.
THE_ADDRESS = "https://api.kartaan.com/may-fetch"
THE_FIELD = "pass"

# **THE NAME OF THE REPOSITORY SECRET.** Spelt once; the workflow files and `nightly_checks.py` hold the same name.
THE_SECRET = "KARTAAN_RUN_PASS"

# How long the question may take. Shorter than `transport.HOW_LONG_TO_WAIT` on purpose: that is for a report that
# genuinely takes minutes, this is one small question, and a Server that does not answer in half a minute is one the run
# should say so about and stop on rather than sit parked.
HOW_LONG_TO_WAIT = 30

# **THE LINES THIS FILE SAYS ITSELF.**
NO_PASS = (
    "THE CHECK WITH KARTAAN WAS NOT MADE: this repository has no run pass yet (the secret "
    f"{THE_SECRET} is not set), so the run could not ask whether it may fetch. It is fetching anyway. "
    "To be checked, press Connect GitHub on Kartaan's page again; that writes the pass into this repository."
)
# **THE DAY A RUN WITH NO PASS STOPS (v0.1.21 job 5). CONTROL SETS IT, NOT THIS FILE'S AUTHOR.** The plan's gate: only once the ERP page
# that shows the run pass is live and `KARTAAN_RUN_PASS` has been seen in the pipeline repository's secret names, and then with 7 days'
# warning. `None` is "not set yet": a run with no pass carries on and says so (`NO_PASS`), exactly as before. From a set day it stops
# (`NO_PASS_STOPPED`, exit 0, like a Server "no"); before it, it carries on and says how many days are left (`no_pass_warning`).
NO_PASS_STOPS_FROM: Optional[date] = None
NO_PASS_STOPPED = (
    "THIS RUN WAS STOPPED: this repository has no run pass (the secret "
    f"{THE_SECRET} is not set), and a run without one no longer fetches. "
    "To start fetching again, press Connect GitHub on Kartaan's page again, or copy your run pass from your Kartaan account "
    "into this repository's secrets; that writes the pass here."
)


def no_pass_warning(days_left: Optional[int]) -> str:
    """The warning a run with no pass prints before the stop day. `None` when the day could not be worked out."""
    left = "" if days_left is None else f" {days_left} {'day' if days_left == 1 else 'days'} left."
    return (
        "THE CHECK WITH KARTAAN WAS NOT MADE: this repository has no run pass yet (the secret "
        f"{THE_SECRET} is not set), so the run could not ask whether it may fetch. It is fetching anyway,"
        f" but runs without a run pass will stop being fetched.{left} "
        "Copy your run pass now: press Connect GitHub on Kartaan's page again; that writes the pass into this repository."
    )


NOTHING_FETCHED = "Nothing was fetched and nothing was deleted: your records and files are as they were."
COULD_NOT_REACH = (
    "Kartaan could not be reached, so nothing was fetched; the next run asks again. "
    "Nothing was deleted: your records and files are as they were."
)
GARBLED = (
    "Kartaan answered, but not in a way this run can read, so nothing was fetched; the next run asks again. "
    "Nothing was deleted: your records and files are as they were."
)
# A no from the Server whose own sentence did not come with it (a body that cannot be read, or has no sentence).
BY_STATUS = {
    403: "Kartaan did not accept this run's pass, so nothing was fetched. Press Connect GitHub on Kartaan's page again to write a new one.",
    429: "This pipeline has asked too many times today whether it may fetch, so nothing was fetched. The next day's run asks again.",
    503: "Kartaan could not check your plan just now, so nothing was fetched. The next run asks again.",
}

# What the run exits with. A deliberate stop is not a defect; a question that got no usable answer is.
EXIT_TOLD_NO = 0
EXIT_NO_ANSWER = 1


@dataclass(frozen=True)
class Decision:
    """What to do, and what to say. `go` False carries the number the run exits with."""

    go: bool
    lines: Tuple[str, ...]
    exit_code: int = 0


def _clean(sentence: str, the_pass: str) -> str:
    """The Server's sentence, one tidy line, with the pass taken out if it was ever in it."""
    out = " ".join(str(sentence).split())
    return out.replace(the_pass, "") if the_pass else out


def decide(status: int, body: Optional[Dict], the_pass: str = "") -> Decision:
    """The pure rule: what the Server said, as what the run does.

    **A YES NEEDS ALL THREE: status 200, `fetch` the actual boolean true, and a body that is an object.** Anything
    short of that is a no or an answer nobody can read -- never a quiet go. `True` is asked for as a boolean because
    `1`, `"true"` and `"yes"` are what a garbled or hostile answer looks like.
    """
    if not isinstance(body, dict) or not isinstance(body.get("fetch"), bool):
        return Decision(False, (GARBLED,), EXIT_NO_ANSWER)
    said = body.get("said")
    said = _clean(said, the_pass) if isinstance(said, str) and said.strip() else ""
    if body["fetch"] is True:
        if status == 200:
            return Decision(True, (said,) if said else ())
        # A yes on any other status is not the Server's yes.
        return Decision(False, (GARBLED,), EXIT_NO_ANSWER)
    sentence = said or BY_STATUS.get(status, "Kartaan says this run may not fetch.")
    return Decision(False, (sentence, NOTHING_FETCHED), EXIT_TOLD_NO)


def ask(the_pass: str, post: Callable[[str, Dict[str, str]], Tuple[int, Optional[Dict]]]) -> Decision:
    """Ask once and decide.

    `post(address, form)` answers `(status, the body read as an object or None)` and may throw when the call never
    got there. **THE PASS IS HANDED ONLY AS A FORM FIELD**, never in the address.
    """
    try:
        status, body = post(THE_ADDRESS, {THE_FIELD: the_pass})
    except Exception as wrong:  # noqa: BLE001 - named by kind, never by text, and never swallowed
        return Decision(False, (COULD_NOT_REACH, f"({type(wrong).__name__})"), EXIT_NO_ANSWER)
    return decide(status, body, the_pass)


def the_check(
    the_pass: Optional[str],
    post: Callable[[str, Dict[str, str]], Tuple[int, Optional[Dict]]],
    say: Callable[[str], None],
    today: Optional[date] = None,
) -> Optional[int]:
    """What `start.main` calls first: `None` to carry on fetching, or the number to exit with.

    **EVERYTHING IT HAS TO SAY IS SAID HERE**, through `say`, so a check can read every word. `today` is his day; a clock that gave
    none is never a reason to stop a seller, so with the stop day set and no `today` the run is warned, not stopped.
    """
    held = (the_pass or "").strip()
    if not held:
        if NO_PASS_STOPS_FROM is None:
            say(NO_PASS)
            return None
        if today is not None and today >= NO_PASS_STOPS_FROM:
            say(NO_PASS_STOPPED)
            say(NOTHING_FETCHED)
            return EXIT_TOLD_NO
        say(no_pass_warning(None if today is None else (NO_PASS_STOPS_FROM - today).days))
        return None
    decision = ask(held, post)
    for line in decision.lines:
        say(line)
    return None if decision.go else decision.exit_code


def the_real_post(address: str, form: Dict[str, str]) -> Tuple[int, Optional[Dict]]:  # pragma: no cover - the real network
    """The one real call. It decides nothing.

    Over `transport._call`, which turns a 4xx or 5xx into an answer instead of an exception -- the Server's refusals
    carry the sentence a seller needs -- and which throws only when the call never got there at all.
    """
    from transport import _call, _decoded  # noqa: PLC0415

    status, _headers, raw = _call(
        "POST",
        address,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=urllib.parse.urlencode(form).encode("utf-8"),
        timeout=HOW_LONG_TO_WAIT,
    )
    return status, _decoded(raw)
