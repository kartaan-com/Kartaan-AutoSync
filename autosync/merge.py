"""The one-time merge of his old Drive folders into the one `Kartaan` folder.

**HIS LIVE DRIVE, SO IT ASKS BEFORE IT MOVES (plan piece 34, step 3).** *"His existing
folders get merged once with nothing lost."* Three places hold his files today:

  - **"Kartaan data"** -- the folder the Server made; the run worked inside it, and put its
    own memory, manifest and logs in a subfolder called `autosync`;
  - **"Kartaan AutoSync"** -- the folder the Chrome extension made at the top of his Drive;
  - **the sales ledger**, made loose at the top of his Drive on purpose, against his ruling.

**THE READING PASS WRITES NOTHING.** It lists every file, says where each would go in his
layout, and **names every pair that would collide** (same report folder, same file name). It
makes no folder and moves no file.

**HE SEES THAT LIST AND SAYS YES, TIED TO THE FIGURES.** The apply refuses unless he gives
back the figures the reading pass printed -- the same discipline as the 29 job-work bills. If
anything changed in between, the figures differ and nothing moves.

**MOVE, NEVER COPY-AND-DELETE.** A Drive move keeps the file's id, so nothing that points at
it breaks and there is never a moment with two copies. **A collision is shown to him and left
exactly where it is -- never resolved by guessing which is newer.** A file this does not
recognise is listed and left. **The empty old folders are left for him to delete** (Golden
Rule 9: recoverable over permanent).

**RUN TWICE: THE SECOND RUN MOVES NOTHING.** What moved is no longer in the sources, so the
plan it makes has nothing to move.

**NOTHING HERE MAKES A FOLDER HIS LAYOUT DOES NOT HAVE** -- the destination folders are made
by `drive_door.folder_at`, which refuses any other name.
"""

import hashlib
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import between_runs
import layout
import manifest
from drive import FOLDER
from drive_door import (
    DriveSaidNo,
    _every_file,
    _answered,
    FILES,
    as_a_quoted_value,
    folder_at,
    look_for_the_folder_at,
    move_the_file,
)

# What the folders are called today. Written here once, as what they WERE, because they are
# not in his layout and nothing else may name them.
THE_EXTENSIONS_OLD_FOLDER = "Kartaan AutoSync"
THE_RUNS_OLD_SUBFOLDER = "autosync"
THE_OLD_LOG_START = "autosync-log-"

MOVE = "move"
COLLISION = "collision"
LEFT = "left"


@dataclass(frozen=True)
class Item:
    """One file, where it is, and what is to be done about it."""

    file_id: str
    name: str
    came_from: str
    to: Tuple[str, ...]
    what: str
    why: str = ""

    def line(self) -> str:
        where = " / ".join((layout.KARTAAN,) + self.to) if self.what != LEFT else "(stays where it is)"
        why = f"  -- {self.why}" if self.why else ""
        return f"{self.what.upper():9} {self.came_from} / {self.name}  ->  {where}{why}"


@dataclass(frozen=True)
class Plan:
    items: Tuple[Item, ...]
    not_found: Tuple[str, ...] = ()

    def count(self, what: str) -> int:
        return sum(1 for one in self.items if one.what == what)

    def figures(self) -> str:
        """What he gives back to say yes: three counts and a short stamp of exactly which files.

        **THE STAMP IS WHAT TIES HIS YES TO THESE FILES AND NOT JUST THESE NUMBERS.** Counts alone
        would accept a Drive that changed between the reading pass and the apply, if it changed
        by the same amounts.
        """
        which = "|".join(sorted(f"{one.what}:{one.file_id}:{'/'.join(one.to)}" for one in self.items))
        stamp = hashlib.sha256(which.encode("utf-8")).hexdigest()[:8]
        return f"moves={self.count(MOVE)} collisions={self.count(COLLISION)} left={self.count(LEFT)} stamp={stamp}"


def _children(transport, folder_id: str) -> List[Dict]:
    return _every_file(
        transport,
        f"'{as_a_quoted_value(folder_id)}' in parents and trashed = false",
        "id,name,mimeType",
        "listing what is in an old folder",
    )


def _where_a_run_file_goes(name: str) -> Optional[Tuple[str, ...]]:
    if name in (between_runs.FILE_NAME, manifest.FILE_NAME):
        return layout.SYSTEM
    if name.startswith(THE_OLD_LOG_START) and name.endswith(".txt"):
        return layout.LOGS
    return None


def _what_is_in(transport, label: str, root_id: str) -> List[Tuple[Item, bool]]:
    """Every file under one old folder, as an item that would move or be left.

    The bool is only `True` for an item that would move -- collisions are worked out after.
    """
    out: List[Tuple[Item, bool]] = []
    for one in _children(transport, root_id):
        name = str(one.get("name") or "")
        if one.get("mimeType") != FOLDER:
            out.append((Item(one["id"], name, label, (), LEFT, "a file loose at the top, not in any report folder"), False))
            continue
        for inner in _children(transport, one["id"]):
            inner_name = str(inner.get("name") or "")
            came = f"{label} / {name}"
            if inner.get("mimeType") == FOLDER:
                out.append((Item(inner["id"], inner_name, came, (), LEFT, "a folder inside a folder"), False))
                continue
            if name in layout.HAS_NO_FOLDER:
                out.append((Item(inner["id"], inner_name, came, (), LEFT, layout.HAS_NO_FOLDER[name]), False))
                continue
            if name == THE_RUNS_OLD_SUBFOLDER:
                goes = _where_a_run_file_goes(inner_name)
            elif name in layout.BELOW_REPORTS:
                goes = layout.where_it_goes(name)
            else:
                out.append((Item(inner["id"], inner_name, came, (), LEFT, f"{name} is not a folder in his layout"), False))
                continue
            if goes is None:
                out.append((Item(inner["id"], inner_name, came, (), LEFT, "not a file Kartaan knows the place of"), False))
                continue
            out.append((Item(inner["id"], inner_name, came, goes, MOVE), True))
    return out


def the_plan(
    transport,
    sources: Sequence[Tuple[str, str]],
    the_ledger_id: Optional[str],
    the_ledger_name: str,
    not_found: Sequence[str] = (),
) -> Plan:
    """What would move where, and what would collide. **WRITES NOTHING AND MAKES NOTHING.**

    `sources` is `(what to call it, its folder id)` for each old folder that exists; a source
    that could not be found is simply not in it, and the caller says so.
    """
    inside = look_for_the_folder_at(transport, (layout.KARTAAN,), "root")
    found: List[Tuple[Item, bool]] = []
    for label, folder_id in sources:
        found.extend(_what_is_in(transport, label, folder_id))
    if the_ledger_id:
        parents = (_answered(
            transport.get(f"{FILES}/{the_ledger_id}", params={"fields": "parents"}),
            "asking where the sales ledger is now",
        ).json() or {}).get("parents") or []
        if not (inside and list(parents) == [inside]):
            found.append((Item(the_ledger_id, the_ledger_name, "My Drive", (), MOVE), True))

    # What is already standing at each destination, asked once per destination and only when it exists.
    standing: Dict[Tuple[str, ...], set] = {}

    def already_in(path: Tuple[str, ...]) -> set:
        if path not in standing:
            where = inside if not path else (look_for_the_folder_at(transport, path, inside) if inside else None)
            standing[path] = {str(f.get("name")) for f in _children(transport, where)} if where else set()
        return standing[path]

    claims: Dict[Tuple[Tuple[str, ...], str], int] = {}
    for item, goes in found:
        if goes:
            claims[(item.to, item.name)] = claims.get((item.to, item.name), 0) + 1

    decided: List[Item] = []
    for item, goes in found:
        if not goes:
            decided.append(item)
            continue
        if claims[(item.to, item.name)] > 1:
            decided.append(Item(item.file_id, item.name, item.came_from, item.to, COLLISION,
                                "another old file wants the same name in the same place"))
        elif item.name in already_in(item.to):
            decided.append(Item(item.file_id, item.name, item.came_from, item.to, COLLISION,
                                "a file of that name is already there"))
        else:
            decided.append(item)
    decided.sort(key=lambda one: (one.what, one.came_from, one.name))
    return Plan(items=tuple(decided), not_found=tuple(not_found))


def apply(transport, plan: Plan, inside: str, say: Callable[[str], None]) -> int:
    """Move every item the plan says moves. Collisions and leftovers are not touched.

    Answers how many files actually moved. **A file already where it is going counts for
    nothing**, which is what makes a second run move nothing.
    """
    moved = 0
    for item in plan.items:
        if item.what != MOVE:
            continue
        there = inside if not item.to else folder_at(transport, item.to, inside)
        if move_the_file(transport, item.file_id, there):
            moved += 1
    say(f"Merge: {moved} files moved.")
    return moved


def what_it_says_before_asking(plan: Plan) -> List[str]:
    """The reading pass, in words: every line, then the three figures he gives back."""
    lines = [one.line() for one in plan.items]
    lines.extend(f"NOT FOUND {one}" for one in plan.not_found)
    lines.append(f"MERGE PLAN FIGURES: {plan.figures()}")
    return lines


def why_it_will_not_apply(plan: Plan, figures_given: str) -> str:
    """Words, or '' when he has said yes to exactly this plan.

    **TIED TO THE FIGURES.** A yes to a different plan is not a yes -- anything that changed
    since the reading pass changes a figure, and nothing moves.
    """
    given = " ".join(str(figures_given or "").split())
    if not given:
        return "Nothing moves: the figures from the reading pass were not given back."
    if given != plan.figures():
        return (
            f"Nothing moves: the figures given back ({given}) are not the ones in the plan "
            f"as it stands now ({plan.figures()}). Run the reading pass again and say yes to that."
        )
    return ""


def why_the_merge_comes_first(transport, data_folder_id: str) -> str:
    """Words if the run's old memory still sits in the old folder, or '' when it is safe to run.

    **A NIGHT BEFORE THE MERGE WOULD START FROM NOTHING.** The run's memory and manifest now live
    in `Kartaan / System`; run first, it would find none, fetch everything again, and then the
    merge would meet a second memory in the way and leave the real one behind as a collision. So
    while the old memory is still where the run used to keep it, the run refuses -- red, in a
    sentence -- and the merge is what clears it.
    """
    old = look_for_the_folder_at(transport, (THE_RUNS_OLD_SUBFOLDER,), data_folder_id)
    if old and any(f.get("name") == between_runs.FILE_NAME for f in _children(transport, old)):
        return (
            "Nothing was fetched: the run's memory is still in the old 'Kartaan data' folder, and a run now "
            "would start from nothing. Run the merge first (the button, merge = plan, then apply), "
            "and this clears by itself."
        )
    return ""


def read_the_plan(transport, data_folder_id: str) -> Plan:
    """Look at his Drive and make the plan. **WRITES NOTHING.**

    "Kartaan data" is the folder the Server made, named by the id the repository already holds;
    "Kartaan AutoSync" is the extension's, found by name at the top of his Drive; the ledger is
    found by name, as every run finds it.
    """
    import ledger_sheet  # noqa: PLC0415 - kept beside its one use
    from drive_door import _the_folder_named  # noqa: PLC0415

    sources: List[Tuple[str, str]] = []
    missing: List[str] = []
    try:
        there = _answered(
            transport.get(f"{FILES}/{data_folder_id}", params={"fields": "id,trashed"}), "looking for Kartaan data")
        if (there.json() or {}).get("trashed"):
            raise DriveSaidNo("it is in the bin")
        sources.append(("Kartaan data", data_folder_id))
    except DriveSaidNo as wrong:
        missing.append(f"Kartaan data ({wrong})")
    ours = _the_folder_named(transport, THE_EXTENSIONS_OLD_FOLDER, "root")
    if ours:
        sources.append((THE_EXTENSIONS_OLD_FOLDER, ours))
    else:
        missing.append(f"{THE_EXTENSIONS_OLD_FOLDER} (none this connection can see at the top of his Drive)")
    ledger_id = ledger_sheet.find_the_ledger(transport)
    if not ledger_id:
        missing.append(f"{ledger_sheet.THE_SHEET_IS_CALLED} (no sales ledger found)")
    return the_plan(transport, sources, ledger_id, ledger_sheet.THE_SHEET_IS_CALLED, missing)


def run_the_merge(
    transport, data_folder_id: str, mode: str, figures_given: str, say: Callable[[str], None],
) -> int:
    """`plan` shows what would happen and writes nothing; `apply` does it, only on his figures.

    **THE EXIT NUMBER IS THE ANSWER.** A refused apply, or one that left something still to move,
    is red -- never a quiet green that nobody reads.
    """
    try:
        return _the_merge(transport, data_folder_id, mode, figures_given, say)
    except Exception as wrong:  # noqa: BLE001 - said in a sentence, never a traceback; a rerun is safe (moves are by id)
        say(f"The merge stopped: {wrong}. Nothing was copied or deleted; running it again is safe.")
        return 1


def _the_merge(
    transport, data_folder_id: str, mode: str, figures_given: str, say: Callable[[str], None],
) -> int:
    plan = read_the_plan(transport, data_folder_id)
    for line in what_it_says_before_asking(plan):
        say(line)
    if mode == "plan":
        say("Nothing was moved. To merge, run it again with apply and these figures.")
        return 0
    why = why_it_will_not_apply(plan, figures_given)
    if why:
        say(why)
        return 1
    from drive_door import the_kartaan_folder  # noqa: PLC0415

    apply(transport, plan, the_kartaan_folder(transport), say)
    after = read_the_plan(transport, data_folder_id)
    say(f"After the merge, the reading pass finds: {after.figures()}")
    if after.count(MOVE):
        say("Something that should have moved is still to move. Run it again.")
        return 1
    return 0
