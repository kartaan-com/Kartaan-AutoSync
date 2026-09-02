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

**WHAT HAS BEEN READ IS CAPPED TO THE FOLDER, AND TO NOTHING ELSE. HIS
DECISION, 2026-09-02: "cap on folder".**

The list of what has been read cannot grow for ever, and the obvious cap -- keep
the last so many days -- is the wrong one HERE, for a reason that does not apply
to `between_runs.KEEP_RUN_DAYS`:

**A LANDED FILE IS NEVER REMOVED FROM THE FOLDER.** So an id dropped while its
file is still sitting there makes that file NEW again. It is read a second time,
and being an old file it puts its old figures back over the newer ones that had
already corrected them -- silently, because within one run recency is exact and
across runs the ledger records no trace of which file last wrote a value.

So an id is dropped **only when its file has actually gone from the folder.**
The list is then a mirror of the folder: it can never be longer than the folder,
it shrinks the night he tidies Drive, and no number had to be guessed at.

**IT RESTS ON THE LISTING BEING THE WHOLE FOLDER, and that is said out loud
because it is the one way this can go wrong.** A short listing looks exactly like
a tidied folder from in here. `still_worth_remembering` refuses to forget
anything at all when the folder comes back empty, which is the one case it can
tell apart by itself; everything past that is the door's to get right.

---

**NOTHING HERE OPENS A FOLDER.** The listing is handed in, exactly as every door
in this package has its transport handed in, so every rule below is checked with
no Drive, no token and no internet.
"""

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

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


@dataclass(frozen=True)
class StillRemembered:
    """What is worth going on remembering, and what has been let go of."""

    keep: Tuple[str, ...] = ()
    forgotten: Tuple[str, ...] = ()
    # Why nothing was let go of, when something would otherwise have been. Empty
    # when there was no such reason.
    refused_to_forget: str = ""

    def says(self) -> str:
        """One line for the run log. **Every count, even the noughts.**

        Forgetting is the one thing in here that can quietly cause a re-read, so
        how many were forgotten is said every night rather than only when it is
        interesting -- a night that forgot six hundred and a night that forgot
        none must not read the same.
        """
        said = f"{len(self.keep)} files still remembered as read, {len(self.forgotten)} let go of"
        if self.refused_to_forget:
            said += f"; nothing was let go of: {self.refused_to_forget}"
        return said


def still_worth_remembering(
    in_the_folder: Sequence[InTheFolder],
    already_read: Sequence[str],
) -> StillRemembered:
    """What stays in the record of what has been read. **HIS CAP: the folder.**

    **THE SAME TWO THINGS `what_is_new` IS GIVEN, and deliberately so.** The rule
    that nothing about a fetch can reach this decision holds here for the same
    structural reason: there is no argument through which it could arrive.

    **AN ID IS LET GO OF ONLY WHEN ITS FILE HAS GONE FROM THE FOLDER.** Not after
    so many days -- a landed file is never removed, so a day-count would let go of
    ids for files still sitting there, and each one would be read again and put
    its old figures back over newer ones.

    **AND A FOLDER THAT COMES BACK EMPTY IS NOT A FOLDER SOMEBODY EMPTIED.** It is
    what a listing looks like when it failed, or when the wrong folder was asked
    about. Letting go of everything on the strength of it would re-read the
    seller's entire history the following night, so nothing is let go of and the
    reason is said out loud. **It is the one bad listing this can tell apart by
    itself; a listing that is merely SHORT looks exactly like a tidied folder from
    in here, and that is the door's to get right, not this file's.**
    """
    remembered = {str(one).strip() for one in (already_read or ()) if str(one).strip()}

    there: set = set()
    for one in in_the_folder or ():
        if not isinstance(one, InTheFolder):
            raise CannotTell(
                "A folder is a list of files this job understands, and one of "
                f"these is a {type(one).__name__}. Nothing has been forgotten."
            )
        there.add(one.which)

    if not there and remembered:
        return StillRemembered(
            keep=tuple(sorted(remembered)),
            forgotten=(),
            refused_to_forget=(
                f"the folder came back with no files in it at all, and {len(remembered)} "
                "were remembered as read. That is what a listing looks like when it "
                "failed, and letting go of them would read the whole history again."
            ),
        )

    return StillRemembered(
        keep=tuple(sorted(remembered & there)),
        forgotten=tuple(sorted(remembered - there)),
    )


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
