"""Checks for the one-time merge, against a stand-in Drive that remembers where every file is.

**THE ONES THAT MATTER MOST:** the reading pass writes nothing at all; every file keeps its
id when it moves; a collision is named and left, never guessed at; a yes to different
figures moves nothing; and the second run moves nothing.

Run: python autosync/merge_checks.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import layout  # noqa: E402
import merge as tool  # noqa: E402
from drive import FOLDER  # noqa: E402

SHEET = "application/vnd.google-apps.spreadsheet"
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


class Reply:
    def __init__(self, body=None, ok=True, status=200):
        self.ok, self.status, self._body, self.text = ok, status, body, ""

    def json(self):
        return self._body


class Drive:
    """A Drive that knows parents, answers searches by name and parent, and can move."""

    def __init__(self):
        self.things = {}
        self.next = 1
        self.writes = []

    def add(self, name, parents, kind="text/plain"):
        which = f"id-{self.next}"
        self.next += 1
        self.things[which] = {"id": which, "name": name, "parents": list(parents), "mimeType": kind}
        return which

    def folder(self, name, parents):
        return self.add(name, parents, FOLDER)

    def get(self, url, params=None, headers=None):
        params = params or {}
        tail = url.rsplit("/files", 1)[1]
        if tail.startswith("/"):
            one = self.things.get(tail[1:])
            if one is None:
                return Reply(ok=False, status=404)
            return Reply({"id": one["id"], "parents": one["parents"], "trashed": one.get("trashed", False)})
        q = params.get("q", "")
        name = re.search(r"name = '((?:[^'\\]|\\.)*)'", q)
        parent = re.search(r"'((?:[^'\\]|\\.)*)' in parents", q)
        kind = re.search(r"mimeType = '([^']*)'", q)
        trashed = "trashed = true" in q
        found = []
        for one in self.things.values():
            if name and one["name"] != name.group(1).replace("\\'", "'"):
                continue
            if parent and parent.group(1) not in one["parents"]:
                continue
            if kind and one["mimeType"] != kind.group(1):
                continue
            if trashed:
                continue
            found.append(dict(one))
        return Reply({"files": found})

    def post(self, url, params=None, headers=None, json=None, data=None):
        self.writes.append(("post", json))
        return Reply({"id": self.folder(json["name"], json["parents"])})

    def patch(self, url, params=None, headers=None, json=None, data=None):
        self.writes.append(("patch", url, params))
        if json is None and data is None:
            return Reply(ok=False, status=411)
        one = self.things[url.rsplit("/", 1)[1]]
        gone = (params or {}).get("removeParents", "").split(",")
        one["parents"] = [p for p in one["parents"] if p not in gone] + [params["addParents"]]
        return Reply({"id": one["id"]})

    def delete(self, url, params=None, headers=None):
        self.writes.append(("delete", url))
        return Reply({})


def his_drive():
    """What his Drive looks like today: the Server's folder, the extension's, a loose ledger."""
    d = Drive()
    data = d.folder("Kartaan data", ["root"])
    ext = d.folder("Kartaan AutoSync", ["root"])
    a = d.folder("autosync", [data])
    d.add("autosync-state.json", [a])
    d.add("autosync-manifest.json", [a])
    d.add("autosync-log-2026-09-20.txt", [a])
    d.add("something-odd.txt", [a])
    az = d.folder("az_orders", [data])
    d.add("amazon_az_orders_2026-09-20.csv", [az])
    d.add("amazon_az_orders_2026-09-21.csv", [az])
    fk = d.folder("fk_orders", [ext])
    d.add("flipkart_fk_orders_2026-09-20.xlsx", [fk])
    mo = d.folder("me_orders", [ext])
    d.add("meesho_me_orders_2026-09-20.csv", [mo])
    kw = d.folder("fk_keywords", [ext])
    d.add("flipkart_fk_keywords_2026-09-20.csv", [kw])
    odd = d.folder("a_folder_nobody_knows", [data])
    d.add("x.csv", [odd])
    d.add("loose.csv", [data])
    ledger = d.add("Kartaan sales ledger", ["root"], SHEET)
    return d, data, ext, ledger


def plan_of(d, data):
    return tool.read_the_plan(d, data)


# ------------------------------------------------------- the reading pass

d, data, ext, ledger = his_drive()
before = {k: dict(v) for k, v in d.things.items()}
plan = answered(lambda: plan_of(d, data))
check("the reading pass writes nothing and makes nothing", d.writes == [] and d.things == before)
by = {(one.came_from, one.name): one for one in plan.items}
check("an Amazon orders file goes to Reports / Amazon / Orders",
      by[("Kartaan data / az_orders", "amazon_az_orders_2026-09-20.csv")].to == ("Reports", "Amazon", "Orders"))
check("a Flipkart orders file goes to Reports / Flipkart / Orders",
      by[("Kartaan AutoSync / fk_orders", "flipkart_fk_orders_2026-09-20.xlsx")].to == ("Reports", "Flipkart", "Orders"))
check("the run's memory and manifest go to System, and its log to System / Logs",
      by[("Kartaan data / autosync", "autosync-state.json")].to == ("System",)
      and by[("Kartaan data / autosync", "autosync-manifest.json")].to == ("System",)
      and by[("Kartaan data / autosync", "autosync-log-2026-09-20.txt")].to == ("System", "Logs"))
check("the loose sales ledger goes to the top of Kartaan, by its own id",
      by[("My Drive", "Kartaan sales ledger")].to == () and by[("My Drive", "Kartaan sales ledger")].file_id == ledger
      and by[("My Drive", "Kartaan sales ledger")].what == tool.MOVE)
check("Flipkart's organic keywords have no folder, so the file stays and says why",
      by[("Kartaan AutoSync / fk_keywords", "flipkart_fk_keywords_2026-09-20.csv")].what == tool.LEFT
      and "ruling" in by[("Kartaan AutoSync / fk_keywords", "flipkart_fk_keywords_2026-09-20.csv")].why)
check("a file Kartaan does not know the place of stays",
      by[("Kartaan data / autosync", "something-odd.txt")].what == tool.LEFT)
check("a folder his layout does not have stays, with its files",
      by[("Kartaan data / a_folder_nobody_knows", "x.csv")].what == tool.LEFT)
check("and a file loose at the top of an old folder stays",
      by[("Kartaan data", "loose.csv")].what == tool.LEFT)
check("the figures are the three numbers he gives back",
      plan.figures().startswith("moves=8 collisions=0 left=4 stamp="))

# ---------------------------------------------------------- collisions

d, data, ext, ledger = his_drive()
az2 = d.folder("az_orders", [ext])
d.add("amazon_az_orders_2026-09-20.csv", [az2])
plan = plan_of(d, data)
named = [one for one in plan.items if one.what == tool.COLLISION]
check("two old files wanting the same name in the same place are BOTH named as a collision",
      len(named) == 2 and {one.came_from for one in named} == {"Kartaan data / az_orders", "Kartaan AutoSync / az_orders"})
check("and the one with no rival still moves",
      any(one.name == "amazon_az_orders_2026-09-21.csv" and one.what == tool.MOVE for one in plan.items))

d, data, ext, ledger = his_drive()
kartaan = d.folder("Kartaan", ["root"])
reports = d.folder("Reports", [kartaan])
amazon = d.folder("Amazon", [reports])
orders = d.folder("Orders", [amazon])
d.add("amazon_az_orders_2026-09-20.csv", [orders])
plan = plan_of(d, data)
check("a file already standing in the destination makes it a collision, not an overwrite",
      [one.what for one in plan.items if one.name == "amazon_az_orders_2026-09-20.csv"] == [tool.COLLISION])

# ------------------------------------------------------------- the yes

d, data, ext, ledger = his_drive()
plan = plan_of(d, data)
check("a yes with no figures is refused in words", "figures" in tool.why_it_will_not_apply(plan, ""))
check("a yes to other figures is refused, naming both",
      "moves=1 " in tool.why_it_will_not_apply(plan, "moves=1 collisions=0 left=4 stamp=00000000")
      and plan.figures() in tool.why_it_will_not_apply(plan, "moves=1 collisions=0 left=4 stamp=00000000"))
check("a yes to exactly these figures is accepted", tool.why_it_will_not_apply(plan, plan.figures()) == "")
said = []
code = answered(lambda: tool.run_the_merge(d, data, "apply", "moves=1 collisions=0 left=4 stamp=00000000", said.append))
check("apply with the wrong figures moves nothing and ends red",
      code == 1 and d.writes == [] and d.things[ledger]["parents"] == ["root"])
code = answered(lambda: tool.run_the_merge(d, data, "plan", "", said.append))
check("plan ends green, says nothing was moved, and prints the figures",
      code == 0 and d.writes == [] and any("MERGE PLAN FIGURES" in s for s in said) and any("Nothing was moved" in s for s in said))

# **THE SAME COUNTS WITH DIFFERENT FILES IS NOT THE SAME PLAN.**
other, other_data, _, _ = his_drive()
swapped = next(k for k, v in other.things.items() if v["name"] == "amazon_az_orders_2026-09-21.csv")
the_folder = other.things.pop(swapped)["parents"]
other.add("amazon_az_orders_2026-09-22.csv", the_folder)
check("a Drive that changed by the same amounts gives other figures, so a yes to the old plan is refused",
      "stamp=" in plan.figures() and plan_of(other, other_data).figures() != plan.figures()
      and plan.figures().split(" stamp=")[0] == plan_of(other, other_data).figures().split(" stamp=")[0])

# --------------------------------------------------------------- the move

ids_before = {k for k, v in d.things.items() if v["mimeType"] != FOLDER}
code = answered(lambda: tool.run_the_merge(d, data, "apply", plan.figures(), said.append))
check("apply on his figures ends green", code == 0)
check("every file that existed before still exists, once, by the same id",
      ids_before <= set(d.things) and ids_before == {k for k, v in d.things.items() if v["mimeType"] != FOLDER})
kartaan_id = next(k for k, v in d.things.items() if v["name"] == "Kartaan" and v["parents"] == ["root"])


def path_of(which):
    names = []
    here = d.things[which]
    while here["parents"] != ["root"]:
        names.append(d.things[here["parents"][0]]["name"])
        here = d.things[here["parents"][0]]
    return list(reversed(names))


check("the ledger is inside Kartaan, with the same id, and no longer loose",
      d.things[ledger]["parents"] == [kartaan_id])
az_file = next(k for k, v in d.things.items() if v["name"] == "amazon_az_orders_2026-09-20.csv")
check("an Amazon file now stands at Kartaan / Reports / Amazon / Orders",
      path_of(az_file) == ["Kartaan", "Reports", "Amazon", "Orders"])
log = next(k for k, v in d.things.items() if v["name"] == "autosync-log-2026-09-20.txt")
check("the log now stands at Kartaan / System / Logs", path_of(log) == ["Kartaan", "System", "Logs"])
odd_one = next(k for k, v in d.things.items() if v["name"] == "something-odd.txt")
check("what was left is exactly where it was",
      d.things[odd_one]["parents"] == [next(k for k, v in d.things.items() if v["name"] == "autosync" and v["parents"] == [data])])
check("nothing was ever deleted, and no file was copied", not any(w[0] == "delete" for w in d.writes))
made = {w[1]["name"] for w in d.writes if w[0] == "post"}
check(f"every folder it made is in his layout -- {sorted(made)}", made <= layout.every_name())
check("the old folders are left for him to delete", all(k in d.things for k in (data, ext)))

# ------------------------------------------------------- the second run

writes_before = len(d.writes)
said = []
code = answered(lambda: tool.run_the_merge(d, data, "plan", "", said.append))
check("the second reading pass finds nothing to move", code == 0 and "moves=0" in said[-2])
second = answered(lambda: plan_of(d, data))
moved_again = answered(lambda: tool.apply(d, second, kartaan_id, said.append))
check("and applying it again moves nothing and writes nothing", moved_again == 0 and len(d.writes) == writes_before)

# ------------------------------------------------------ a collision stays put

d, data, ext, ledger = his_drive()
az2 = d.folder("az_orders", [ext])
rival = d.add("amazon_az_orders_2026-09-20.csv", [az2])
plan = plan_of(d, data)
answered(lambda: tool.run_the_merge(d, data, "apply", plan.figures(), said.append))
check("a collision is left exactly where it was, and never decided", d.things[rival]["parents"] == [az2])
check("and the pair is still named afterwards", plan_of(d, data).count(tool.COLLISION) == 2)

# --------------------------------------------------------- not found

d = Drive()
plan = answered(lambda: tool.read_the_plan(d, "no-such-folder"))
check("with none of his old folders to be seen, the plan says so and moves nothing",
      plan is not None and plan.count(tool.MOVE) == 0 and len(plan.not_found) == 3)

# **A RUN BEFORE THE MERGE REFUSES, AND THE MERGE CLEARS IT.**
d, data, ext, ledger = his_drive()
check("while the run's memory is still in the old folder, a night refuses and says to merge first",
      "Run the merge first" in tool.why_the_merge_comes_first(d, data))
plan = plan_of(d, data)
answered(lambda: tool.run_the_merge(d, data, "apply", plan.figures(), said.append))
check("and after the merge it does not", tool.why_the_merge_comes_first(d, data) == "")
check("a seller with no old folder at all is not held up", tool.why_the_merge_comes_first(Drive(), "none") == "")

# **A DRIVE REFUSAL, A TRASHED FOLDER AND TWO FOLDERS OF ONE NAME ARE SAID IN WORDS, NEVER A TRACEBACK.**
twice = Drive()
twice.folder("Kartaan AutoSync", ["root"])
twice.folder("Kartaan AutoSync", ["root"])
words = []
code = answered(lambda: tool.run_the_merge(twice, "no-such-folder", "plan", "", words.append))
check("two extension folders of one name end the merge red, in a sentence",
      code == 1 and any("Which one" in w or "cannot be known" in w for w in words))
gone = Drive()
trashed_data = gone.folder("Kartaan data", ["root"])
gone.things[trashed_data]["trashed"] = True
plan = answered(lambda: tool.read_the_plan(gone, trashed_data))
check("a trashed Kartaan data folder is not a source", plan is not None and any("Kartaan data" in n for n in plan.not_found))

# **A MOVE THAT LEAVES ANYTHING STILL TO MOVE IS RED.** Pinned by driving it: a Drive whose move changes nothing.
class Stuck(Drive):
    def patch(self, url, params=None, headers=None, json=None, data=None):
        self.writes.append(("patch", url, params))
        return Reply({"id": "x"})


stuck, stuck_data, _, _ = his_drive()
stuck.__class__ = Stuck
stuck_plan = plan_of(stuck, stuck_data)
code = answered(lambda: tool.run_the_merge(stuck, stuck_data, "apply", stuck_plan.figures(), words.append))
check("an apply after which something still waits to move ends red", code == 1)

# **MOVING TO WHERE A FILE ALREADY ONLY IS MOVES NOTHING AND WRITES NOTHING.**
there = Drive()
home = there.folder("Kartaan", ["root"])
filed = there.add("a.csv", [home])
check("a file already only in the folder is not moved, and nothing is sent",
      tool.move_the_file(there, filed, home) is False and there.writes == [])

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 41
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
