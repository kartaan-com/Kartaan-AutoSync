"""Checks for asking Kartaan's Server whether this run may fetch, before it fetches (plan job 30).

**NOTHING HERE TOUCHES A NETWORK.** The question is a stand-in function handed in, so every answer the Server can give --
and every way of getting none -- is driven with nothing connected (Golden Rule 1). What is checked:

| The rule | Driven by |
|---|---|
| A yes goes; nothing else does | 200 with `fetch` true; every other status, shape and spelling of "true" |
| A no stops, in the Server's own words, exit 0 | 200 `fetch` false, 403, 429, 503, with and without a sentence |
| An answer nobody can read, or none, stops and says so, exit 1 | unreachable, timeout, not JSON, wrong shape |
| No pass: carries on, loudly | unset, empty, blank |
| The pass is never printed or put in an address | every case above, read back for it |
| The wiring in `start.py` asks first | the parsed file, never searched as text |

**EACH RULE IS PROVED BY BREAKING IT** at the end, the way `nightly_checks.py` does: the module's own function is swapped for
a version without the rule and the very predicate that guards the rule must go red.

Run: python autosync/may_fetch_checks.py
"""

import ast
import sys
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from datetime import date  # noqa: E402

import may_fetch as tool  # noqa: E402

ran = 0
failures = []


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


THE_PASS = "pass-SECRET-7f3a91"
EVERYTHING_SAID = []  # every line any case printed, read back for the pass at the end


class Server:
    """A stand-in for the Server: answers what it was told to, remembers every ask."""

    def __init__(self, status=200, body=None, raises=None):
        self.status = status
        self.body = body
        self.raises = raises
        self.asked = []

    def __call__(self, address, form):
        self.asked.append((address, dict(form)))
        if self.raises is not None:
            raise self.raises
        return self.status, self.body


def run(server, the_pass=THE_PASS):
    """(what the run does -- None to go, else its exit code, what it said, the server)."""
    said = []
    result = tool.the_check(the_pass, server, said.append)
    EVERYTHING_SAID.extend(said)
    return result, said, server


def goes(server):
    return run(server)[0] is None


# ------------------------------------------------------------- a yes goes

result, said, server = run(Server(200, {"fetch": True, "said": "Your Kartaan plan includes the fetching, so it runs."}))
check("A YES GOES: the run carries on to fetch", result is None)
check("and the Server's sentence is printed as it stands", said == ["Your Kartaan plan includes the fetching, so it runs."])
check("it asked exactly once, at the Server's /may-fetch address",
      len(server.asked) == 1 and server.asked[0][0] == "https://api.kartaan.com/may-fetch")
check("and the pass travels as the one form field called pass, and nowhere else",
      server.asked[0][1] == {"pass": THE_PASS} and THE_PASS not in server.asked[0][0])
check("a yes with no sentence goes and says nothing", run(Server(200, {"fetch": True}))[:2] == (None, []))

# ------------------------------------------------------------- a no stops, in the Server's words

result, said, server = run(Server(200, {"fetch": False, "said": "Your trial has ended and was not paid for."}))
check("A NO STOPS and exits 0, because a deliberate stop is not a defect", result == 0)
check("and prints the Server's sentence, then that nothing was fetched and nothing was deleted",
      said == ["Your trial has ended and was not paid for.", tool.NOTHING_FETCHED]
      and "nothing was deleted" in tool.NOTHING_FETCHED)

for status, expect in ((403, tool.BY_STATUS[403]), (429, tool.BY_STATUS[429]), (503, tool.BY_STATUS[503])):
    result, said, _ = run(Server(status, {"fetch": False, "said": f"the Server's own words for {status}"}))
    check(f"a {status} with the Server's sentence stops (exit 0) and says that sentence",
          result == 0 and said[0] == f"the Server's own words for {status}" and said[-1] == tool.NOTHING_FETCHED)
    result, said, _ = run(Server(status, {"fetch": False}))
    check(f"a {status} with no sentence stops (exit 0) and says what that status means",
          result == 0 and said[0] == expect and said[-1] == tool.NOTHING_FETCHED)

result, said, _ = run(Server(200, {"fetch": False}))
check("a no with no sentence at all still says something, in this file's words",
      result == 0 and said[0] == "Kartaan says this run may not fetch.")
check("a sentence with stray line breaks is printed as one tidy line",
      run(Server(200, {"fetch": False, "said": "one\n\n   two"}))[1][0] == "one two")

# **A "YES" THAT IS NOT PLAINLY A YES IS NOT A YES.**
check("fetch true on a status that is not 200 is not a go", not goes(Server(403, {"fetch": True})))
check("and neither on 429 or 503", not goes(Server(429, {"fetch": True})) and not goes(Server(503, {"fetch": True})))
for odd in ("true", "yes", 1, "1", "True", None, [True], {"a": 1}):
    check(f"fetch spelt {odd!r} is not the boolean true, so it is not a go", not goes(Server(200, {"fetch": odd})))
    check(f"and it exits 1: nothing readable was said", run(Server(200, {"fetch": odd}))[0] == 1)

# ------------------------------------------------------------- unreachable, timed out, not JSON, wrong shape

for why, raised in (
    ("the network is down", urllib.error.URLError("no route")),
    ("the call timed out", TimeoutError("timed out")),
    ("the connection was reset", ConnectionResetError("reset")),
    ("something nobody planned for", RuntimeError("boom")),
):
    result, said, server = run(Server(raises=raised))
    check(f"WHEN {why.upper()}, NOTHING IS FETCHED and the run exits 1", result == 1)
    check(f"and when {why}, it says so in words and that the next run asks again",
          tool.COULD_NOT_REACH in said and "the next run asks again" in said[0] and "nothing was fetched" in said[0])

for why, body in (("not JSON at all", None), ("a list", [1, 2]), ("an empty object", {}),
                  ("an object with no fetch", {"said": "hello"}), ("a string", "fetch")):
    result, said, _ = run(Server(200, body))
    check(f"AN ANSWER THAT IS {why.upper()} DOES NOT FETCH, exits 1 and says it could not be read",
          result == 1 and said == [tool.GARBLED])
check("a 502 page that is not JSON does not fetch either", run(Server(502, None))[0] == 1)
check("and an unknown status with a sensible no is a no", run(Server(418, {"fetch": False, "said": "teapot"}))[:2]
      == (0, ["teapot", tool.NOTHING_FETCHED]))

# ------------------------------------------------------------- no pass: carries on, loudly

for none in (None, "", "   ", "\n"):
    server = Server(200, {"fetch": False})
    said = []
    result = tool.the_check(none, server, said.append)
    EVERYTHING_SAID.extend(said)
    check(f"WITH NO PASS ({none!r}) THE RUN CARRIES ON FETCHING", result is None)
    check(f"and says loudly that the check was not made, and why ({none!r})",
          said == [tool.NO_PASS] and "THE CHECK WITH KARTAAN WAS NOT MADE" in said[0]
          and "no run pass" in said[0] and "Connect GitHub" in said[0])
    check(f"and asks nobody anything ({none!r})", server.asked == [])
check("the pass is read with its edges trimmed, so a stray newline in a secret cannot make a bad ask",
      run(Server(200, {"fetch": True}), the_pass=f"  {THE_PASS}\n")[2].asked[0][1] == {"pass": THE_PASS})

# ------------------------------------------------------------- no pass: warns before the date, stops from it (v0.1.21 job 5)

check("until Control sets a day, the stop day is not set and the run carries on as it did", tool.NO_PASS_STOPS_FROM is None)
THE_DAY = date(2026, 11, 20)


def no_pass_on(today, stops_from=THE_DAY, the_pass=""):
    """(what the run does, what it said, the Server) with the stop day set to `stops_from` for the length of the call."""
    server = Server(200, {"fetch": True})
    said = []
    was = tool.NO_PASS_STOPS_FROM
    tool.NO_PASS_STOPS_FROM = stops_from
    try:
        result = tool.the_check(the_pass, server, said.append, today=today)
    finally:
        tool.NO_PASS_STOPS_FROM = was
    EVERYTHING_SAID.extend(said)
    return result, said, server


before_result, before_said, before_server = no_pass_on(date(2026, 11, 17))
check("BEFORE THE DAY a run with no pass still fetches, and says how many days are left and what to do",
      before_result is None and len(before_said) == 1 and "3 days left" in before_said[0] and "run pass" in before_said[0]
      and "Connect GitHub" in before_said[0] and before_server.asked == [])
check("the last day before it says '1 day left', not '1 days left'", "1 day left" in no_pass_on(date(2026, 11, 19))[1][0]
      and "1 days" not in no_pass_on(date(2026, 11, 19))[1][0])
check("a week out says 7 days", "7 days left" in no_pass_on(date(2026, 11, 13))[1][0])
on_result, on_said, on_server = no_pass_on(THE_DAY)
check("ON THE DAY a run with no pass does NOT fetch, and exits 0 -- a deliberate stop, as a Server 'no' is",
      on_result == tool.EXIT_TOLD_NO == 0)
check("and says why in words, that nothing was fetched and nothing was deleted, and asks nobody",
      "run pass" in " ".join(on_said) and "Connect GitHub" in " ".join(on_said) and tool.NOTHING_FETCHED in on_said and on_server.asked == [])
check("AFTER THE DAY it is the same stop", no_pass_on(date(2027, 3, 1))[0] == 0 and tool.NOTHING_FETCHED in no_pass_on(date(2027, 3, 1))[1])
check("a blank pass is no pass, from the day as before it", no_pass_on(THE_DAY, the_pass="  \n")[0] == 0)
check("a run WITH a pass is not touched by the day: it asks the Server, and a yes goes",
      (lambda r: r[0] is None and len(r[2].asked) == 1)(no_pass_on(date(2027, 3, 1), the_pass=THE_PASS)))
check("a clock that gave no day is never a reason to stop a seller: warned, not stopped",
      (lambda r: r[0] is None and "run pass" in r[1][0])(no_pass_on(None)))

# ------------------------------------------------------------- the pass is never printed

leaky_server = Server(200, {"fetch": False, "said": f"your pass {THE_PASS} is old"})
leaky_said = run(leaky_server)[1]
check("a sentence from the Server that contained the pass is printed without it", all(THE_PASS not in line for line in leaky_said))
leaky_error = run(Server(raises=RuntimeError(f"bad call with {THE_PASS}")))[1]
check("an error whose own text held the pass is named by kind only, never by text",
      all(THE_PASS not in line for line in leaky_error) and any("RuntimeError" in line for line in leaky_error))
check("NOT ONE LINE ANY CASE PRINTED CONTAINS THE PASS", len(EVERYTHING_SAID) > 30 and all(THE_PASS not in line for line in EVERYTHING_SAID))
check("and no sentence this module owns has a place for it",
      all(THE_PASS not in text and "{" not in text
          for text in (tool.NO_PASS, tool.NOTHING_FETCHED, tool.COULD_NOT_REACH, tool.GARBLED, *tool.BY_STATUS.values())))
check("the address has no question in it for a pass to ride on", "?" not in tool.THE_ADDRESS and "{" not in tool.THE_ADDRESS)

# ------------------------------------------------------------- the small facts

check("the secret is called what the workflow files call it", tool.THE_SECRET == "KARTAAN_RUN_PASS")
check("the question has a timeout, and a short one", 0 < tool.HOW_LONG_TO_WAIT <= 60)
check("a deliberate stop exits 0 and an unanswered question exits 1", (tool.EXIT_TOLD_NO, tool.EXIT_NO_ANSWER) == (0, 1))

# ------------------------------------------------------------- start.py asks first

START = ast.parse((HERE / "start.py").read_text(encoding="utf-8"))
MAIN = next(node for node in START.body if isinstance(node, ast.FunctionDef) and node.name == "main")


def _calls_in_main(attr_or_name):
    return sorted(
        node.lineno for node in ast.walk(MAIN)
        if isinstance(node, ast.Call)
        and ((isinstance(node.func, ast.Attribute) and node.func.attr == attr_or_name)
             or (isinstance(node.func, ast.Name) and node.func.id == attr_or_name))
    )


the_asking = _calls_in_main("the_check")
check("start.main asks, and asks once", len(the_asking) == 1)
OPENS = [name for name in ("the_google_connection", "FirebaseSeller", "AmazonDoor", "fetch_one", "one_tick",
                           "the_kartaan_folder", "run_the_merge", "why_the_merge_comes_first") if _calls_in_main(name)]
check("main opens connections, so the ordering check below has something to compare against", len(OPENS) >= 4)
check("AND IT ASKS BEFORE ANY CONNECTION IS OPENED",
      bool(the_asking) and all(the_asking[0] < line for name in OPENS for line in _calls_in_main(name)))
the_if = [node for node in MAIN.body if isinstance(node, ast.If) and "stopped" in ast.dump(node.test)]
check("and a stop returns before anything else runs, with the number it was told",
      len(the_if) == 1 and isinstance(the_if[0].body[-1], ast.Return) and "stopped" in ast.dump(the_if[0].body[-1]))
check("it hands the check the real network function and the environment's pass, through the module's own names",
      "the_real_post" in ast.dump(MAIN) and "THE_SECRET" in ast.dump(MAIN))


# ------------------------------------------------------------- each rule, PROVED BY BEING BROKEN
#
# **A RULE NOBODY HAS WATCHED FAIL IS A COMMENT (D170).** Each predicate below is the exact question the checks above ask.
# The module's own function is swapped for a version without the rule, and the predicate must go red; then it is put back.


def a_yes_needs_a_real_true():
    return not goes(Server(200, {"fetch": "yes"})) and not goes(Server(200, {"fetch": 1}))


def a_yes_needs_status_200():
    return not goes(Server(503, {"fetch": True}))


def a_no_says_nothing_was_deleted():
    return tool.NOTHING_FETCHED in run(Server(200, {"fetch": False, "said": "no"}))[1]


def a_no_is_a_clean_stop():
    return run(Server(200, {"fetch": False, "said": "no"}))[0] == 0


def silence_is_not_a_yes():
    return not goes(Server(raises=TimeoutError())) and not goes(Server(200, None))


def the_server_sentence_loses_the_pass():
    return all(THE_PASS not in line for line in run(Server(200, {"fetch": False, "said": f"x {THE_PASS} y"}))[1])


def no_pass_is_said_loudly():
    said = []
    return tool.the_check("", Server(), said.append) is None and said == [tool.NO_PASS]


def an_error_is_never_quoted():
    return all(THE_PASS not in line for line in run(Server(raises=RuntimeError(THE_PASS)))[1])


# The real ones, kept before anything is swapped, so a broken variant can lean on the rest of the real rule.
REAL_DECIDE = tool.decide


def broken(name, replacement, predicate):
    """True when `predicate` goes red with `tool.<name>` swapped for `replacement` -- and is green again once put back."""
    original = getattr(tool, name)
    setattr(tool, name, replacement)
    try:
        red_when_broken = not predicate()
    finally:
        setattr(tool, name, original)
    return red_when_broken and predicate()


def _decide_with_a_loose_true(status, body, the_pass=""):
    if isinstance(body, dict) and body.get("fetch"):
        return tool.Decision(True, ())
    return REAL_DECIDE(status, body, the_pass)


def _decide_ignoring_status(status, body, the_pass=""):
    return REAL_DECIDE(200, body, the_pass)


def _decide_forgetting_the_deletion_line(status, body, the_pass=""):
    done = REAL_DECIDE(status, body, the_pass)
    return tool.Decision(done.go, tuple(line for line in done.lines if line != tool.NOTHING_FETCHED), done.exit_code)


def _decide_with_a_red_stop(status, body, the_pass=""):
    done = REAL_DECIDE(status, body, the_pass)
    return tool.Decision(done.go, done.lines, 0 if done.go else 1)


def _decide_keeping_the_pass(status, body, the_pass=""):
    return REAL_DECIDE(status, body, "")


def _ask_that_goes_when_it_cannot_reach(the_pass, post):
    try:
        return REAL_DECIDE(*post(tool.THE_ADDRESS, {tool.THE_FIELD: the_pass}), the_pass)
    except Exception:  # noqa: BLE001
        return tool.Decision(True, ())


def _ask_that_goes_on_nothing(the_pass, post):
    try:
        status, body = post(tool.THE_ADDRESS, {tool.THE_FIELD: the_pass})
    except Exception:  # noqa: BLE001
        return tool.Decision(False, (tool.COULD_NOT_REACH,), tool.EXIT_NO_ANSWER)
    return tool.Decision(True, ()) if body is None else REAL_DECIDE(status, body, the_pass)


def _ask_that_quotes_the_error(the_pass, post):
    try:
        status, body = post(tool.THE_ADDRESS, {tool.THE_FIELD: the_pass})
    except Exception as wrong:  # noqa: BLE001
        return tool.Decision(False, (tool.COULD_NOT_REACH, str(wrong)), tool.EXIT_NO_ANSWER)
    return REAL_DECIDE(status, body, the_pass)


def _the_check_that_stops_without_a_pass(the_pass, post, say):
    say(tool.NO_PASS)
    return 0


check("PROOF: a loose reading of true (any truthy value) is caught", broken("decide", _decide_with_a_loose_true, a_yes_needs_a_real_true))
check("PROOF: a yes that ignores the status is caught", broken("decide", _decide_ignoring_status, a_yes_needs_status_200))
check("PROOF: a no that forgets to say nothing was deleted is caught",
      broken("decide", _decide_forgetting_the_deletion_line, a_no_says_nothing_was_deleted))
check("PROOF: a deliberate stop that turned the job red is caught", broken("decide", _decide_with_a_red_stop, a_no_is_a_clean_stop))
check("PROOF: a server sentence that keeps the pass in it is caught",
      broken("decide", _decide_keeping_the_pass, the_server_sentence_loses_the_pass))
check("PROOF: an unreachable Server that quietly lets the run fetch is caught",
      broken("ask", _ask_that_goes_when_it_cannot_reach, silence_is_not_a_yes))
check("PROOF: an unreadable body that is taken for a yes is caught", broken("ask", _ask_that_goes_on_nothing, silence_is_not_a_yes))
check("PROOF: an error quoted by its text is caught", broken("ask", _ask_that_quotes_the_error, an_error_is_never_quoted))
check("PROOF: a run with no pass that stops instead of carrying on is caught",
      broken("the_check", _the_check_that_stops_without_a_pass, no_pass_is_said_loudly))

def stops_before_the_day():
    return no_pass_on(date(2026, 11, 17))[0] is None and no_pass_on(THE_DAY)[0] == 0


def _the_check_that_stops_a_no_pass_early(the_pass, post, say, today=None):
    if not (the_pass or "").strip():
        say(tool.NO_PASS)
        say(tool.NOTHING_FETCHED)
        return 0
    return REAL_THE_CHECK(the_pass, post, say, today=today)


def _the_check_that_never_stops_a_no_pass(the_pass, post, say, today=None):
    if not (the_pass or "").strip():
        say("a run pass is missing, 3 days left. Connect GitHub")
        return None
    return REAL_THE_CHECK(the_pass, post, say, today=today)


REAL_THE_CHECK = tool.the_check
check("PROOF: a no-pass run that stops before the day is caught", broken("the_check", _the_check_that_stops_a_no_pass_early, stops_before_the_day))
check("PROOF: a no-pass run that is never stopped, even from the day, is caught",
      broken("the_check", _the_check_that_never_stops_a_no_pass, stops_before_the_day))
check("start.main hands the check today's date, so the day can be reached",
      any(keyword.arg == "today" for node in ast.walk(MAIN) if isinstance(node, ast.Call)
          and isinstance(node.func, ast.Attribute) and node.func.attr == "the_check" for keyword in node.keywords))
check("and that day is worked out on HIS clock (clock.his_clock), never the machine's own day",
      any(keyword.arg == "today" and "his_clock" in ast.dump(keyword.value)
          for node in ast.walk(MAIN) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
          and node.func.attr == "the_check" for keyword in node.keywords))

EXPECTED = 97
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
