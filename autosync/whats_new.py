"""What starts a read: solely what NEW file is in the seller's Drive folder.

**HIS RULE, and the word "solely" is his:** *"The data read from Google Drive and
writing to Firestore is going to be solely based on what is new."*

**NEVER WHETHER A FETCH SUCCEEDED OR FAILED.** That is not a detail -- it is the
whole shape, and D148 says why in as many words: **one platform having a bad
night must not cost the day's numbers.** The fetching and the reading are two
sections that meet at a folder, not a pipeline where the second waits on the
first.

**IT IS ENFORCED STRUCTURALLY, not remembered.** Nothing in this file takes a run,
a log, a report's state or anything else that could carry a fetch's opinion. It
takes what is in the folder and what has already been read, and there is nowhere
for a success or a failure to enter. A check proves that by reading this file's
own arguments.

---

**A FILE IS THE SAME FILE ONLY IF IT IS THE SAME FILE. Identity is Drive's own
id, NEVER the name.**

This is the one decision in here and it is load-bearing both ways:

- **A NAME IS NOT UNIQUE and is not meant to be.** `landing.py` names a landed
  file for the day its data is about, so a day fetched again lands under the
  same name. Keyed by name, **that second file would never be read** -- and D110
  exists precisely because somebody naming a day by hand *"usually knows what
  arrived was wrong"*. The correction would be fetched, land, and be ignored.
- **AND AN ID CANNOT COLLIDE.** Two files with one name are two files, and both
  are read. The ledger's own rules then decide which statement stands (D150):
  each report writes only what it knows, and the newest file wins.

**So a re-fetch works by construction rather than by a special case for it.**

---

**AN EMPTY FILE IS NEW, AND IT IS NOT DATA.** A nought-byte file is the third
thing, and this package has been caught by it before: `landing.days_that_arrived`
refuses to count one as a day, because a file that counted would stop its day
ever being fetched again -- the quietest possible way to lose a day for good.

Here it is **reported by name and not handed on to be read**, and it is **not
marked as read** either, so tomorrow's real file for that day is still new.

---

**NOTHING HERE OPENS A FOLDER.** The listing is handed in, exactly as every door
in this package has its transport handed in, so every rule below is checked with
no Drive, no token and no internet.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from table import CannotRead


class CannotTell(CannotRead):
    """Whether this file has been read cannot be decided, so nothing is read.

    **ITS OWN KIND, and it stops rather than guesses.** Reading a file twice
    writes a sale twice; never reading it loses a day. Neither is a thing to
    fall into quietly, so a folder that cannot be understood refuses.
    """


@dataclass(frozen=True)
class InTheFolder:
    """One file really sitting in the seller's folder.

    `which` is Drive's own id. `name` is only ever used to SAY which file is
    meant -- never to decide whether it has been read.

    `size` is here because **presence is not correctness, and a nought-byte file
    is the one kind of wrongness presence alone can catch.** The reference's
    manifest checked only that a name existed, and recorded a truncated
    catalogue file as Verified.
    """

    which: str
    name: str = ""
    size: int = 0

    def __post_init__(self):
        if not str(self.which or "").strip():
            raise CannotTell(
                f"A file in the folder ({self.name or 'unnamed'}) has no id, so "
                "there is no way to tell whether it has been read before. "
                "Nothing has been read -- reading it again would write every sale "
                "in it a second time, and skipping it would lose the day."
            )

    @property
    def is_empty(self) -> bool:
        return int(self.size or 0) <= 0


@dataclass(frozen=True)
class WhatToRead:
    """What is new, what is empty, and what was already done."""

    new: Tuple[InTheFolder, ...] = ()
    empty: Tuple[InTheFolder, ...] = ()
    already: Tuple[InTheFolder, ...] = ()

    def says(self) -> str:
        """One line for the run log. **Every count, even the noughts.**

        A sentence that mentions empty files only when there are some makes a
        clean folder and a folder nobody looked at read the same.
        """
        return (
            f"{len(self.new)} new files to read, {len(self.empty)} arrived empty, "
            f"{len(self.already)} already read"
        )

    @property
    def anything_to_do(self) -> bool:
        return bool(self.new)


def what_is_new(
    in_the_folder: Sequence[InTheFolder],
    already_read: Sequence[str],
) -> WhatToRead:
    """Which files in the folder have not been read yet.

    **THESE ARE THE ONLY TWO THINGS IT IS GIVEN**, and that is the rule made
    structural: there is no argument here through which a fetch's success or
    failure could reach the decision, so it cannot.

    **THE SAME FILE LISTED TWICE IS ONE FILE.** A folder listing that repeats an
    id is Drive answering oddly, not two files, and reading it twice would write
    every sale in it twice.
    """
    done = {str(one).strip() for one in (already_read or ()) if str(one).strip()}

    new: List[InTheFolder] = []
    empty: List[InTheFolder] = []
    already: List[InTheFolder] = []
    seen: set = set()

    for one in in_the_folder or ():
        if not isinstance(one, InTheFolder):
            raise CannotTell(
                "A folder is a list of files this job understands, and one of "
                f"these is a {type(one).__name__}. Nothing has been read."
            )
        if one.which in seen:
            continue
        seen.add(one.which)

        if one.which in done:
            already.append(one)
            continue
        if one.is_empty:
            # **NOT READ, AND NOT MARKED AS READ.** Marking it would stop the
            # real file for that day ever being read when it arrives.
            empty.append(one)
            continue
        new.append(one)

    return WhatToRead(new=tuple(new), empty=tuple(empty), already=tuple(already))


def now_read(already_read: Sequence[str], files: Iterable[InTheFolder]) -> Tuple[str, ...]:
    """What has been read, once these have been.

    **ONLY WHAT ACTUALLY READ.** Marking a file read before it is read is how a
    run that dies halfway loses a day for ever; so this is called with what came
    back, never with what was going to be attempted.

    Sorted and deduplicated, so two runs that read the same files leave the same
    record -- which is what makes a difference between two of them mean anything.
    """
    done = {str(one).strip() for one in (already_read or ()) if str(one).strip()}
    for one in files or ():
        if not isinstance(one, InTheFolder):
            raise CannotTell(
                "Only a file this job understands can be marked as read, and this "
                f"is a {type(one).__name__}."
            )
        done.add(one.which)
    return tuple(sorted(done))
