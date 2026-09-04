"""Reading a file that lives in the OTHER repository.

**WHY THIS EXISTS.** Two checks in this package are pinned against files that
are not here: `firestore_checks.py` reads Kartaan's own `sync.js` to make sure
the three collection names this job WRITES are the three names the screens READ,
and `firestore_door_checks.py` reads `server/going_off.py` to make sure the
Google scope this door needs is the scope the seller is actually asked for.

Both are the same shape and it is the shape this project keeps paying for: **one
fact written down twice, in two languages, with nothing mechanical joining them.**
Left unpinned, the nightly job writes to one collection name and the seller's
"What ran" screen reads another -- and that tab is silently empty for ever, with
nothing anywhere saying why.

**THE SPLIT INTO TWO REPOSITORIES BROKE THAT, and this is the cost being paid
rather than dodged.** Before the split, one folder held both halves and the
check just worked. Now no single checkout has both.

**AND IT READS WHAT IS COMMITTED, NEVER WHAT IS ON DISK.** A check that reads
the other repository's working file goes green against work nobody has committed
-- which can still change, or be abandoned -- and red against work in progress
that says nothing about the contract. `git show HEAD:` is the only reading that
is a fact about the other half rather than about what somebody has open.

**IT REFUSES; IT DOES NOT SKIP.** A check that quietly stops checking when it
cannot find what it needs is worse than no check at all, because it is still
counted in the tally. So this raises, and says exactly what to do about it.

**HOW TO POINT IT AT THE OTHER HALF:**

    set KARTAAN=D:\\Kartaan-ERP      (Windows)
    export KARTAAN=~/Kartaan-ERP     (anywhere else)

and if that is not set, a sibling folder called `Kartaan-ERP` next to this one
is tried, which is the ordinary way somebody has both checked out.
"""

import os
import pathlib

HERE = pathlib.Path(__file__).resolve().parent.parent

NEWLINE = chr(10)
SLASH = chr(92)


def whereKartaanIs():
    """The ERP's folder, or where it would be.

    **ONE NAME, and the old one is gone.** The repository was renamed to
    `Kartaan-ERP` (D148) and for a while both spellings were accepted, because a
    folder cannot be renamed by a session running inside it. The rename is done
    -- so the fallback came out on 2026-09-02, and a check goes red if it comes
    back. A fallback nobody wrote down is how two spellings of one thing survive
    for a year.
    """
    said = os.environ.get('KARTAAN', '').strip()
    if said:
        return pathlib.Path(said)
    here = HERE.parent / 'Kartaan-ERP'
    if here.is_dir():
        return here
    return here


def whereTheServerIs():
    """The server's folder, or where it would be.

    **`going_off.py` MOVED AGAIN (D148).** It was in Kartaan, then the server
    was split out and took it. The check that reads it asks for the scope this
    door needs against the scope the seller is actually asked for -- so it now
    looks in a third place.
    """
    said = os.environ.get('SERVER', '').strip()
    if said:
        return pathlib.Path(said)
    return HERE.parent / 'Kartaan-Server'


def _asItWasCommitted(root, parts, why):
    """A file as it is COMMITTED in the other repository, never as it sits on disk.

    **THIS IS THE WHOLE POINT OF THE DOOR AND IT WAS WRONG.** Reading the working
    file means a check here can go GREEN against work in another folder that
    nobody has committed and that might still change -- or RED against work that
    was tried and abandoned. Neither is a fact about the contract between two
    repositories; both are a fact about what somebody happens to have open.

    **IT REALLY HAPPENED, 2026-09-02.** The ERP had seventeen new ledger columns
    written into `sheet-store.js` and NOT committed. Read off the disk, the check
    pinning the two column lists went red -- against a file that, at the ERP's
    own HEAD, still said exactly what this repository says. **A gate built while
    that was red would have refused the commit containing the gate.**

    **IT REFUSES RATHER THAN FALLING BACK TO THE DISK.** A fallback is the exact
    fault a gate exists to prevent: waving something through because it could not
    look, while everybody believes it looked.
    """
    import subprocess

    where = '/'.join(parts)
    try:
        done = subprocess.run(
            ['git', '-C', str(root), 'show', 'HEAD:' + where],
            capture_output=True,
        )
    except OSError as wrong:
        raise SystemExit(
            f"{NEWLINE}CANNOT CHECK THIS: git could not be run to read {where}"
            f" out of {root} -- {wrong}." + NEWLINE + NEWLINE
            + "  It is NOT skipped. A check that quietly stops checking is worse"
            + NEWLINE
            + "  than no check, because it is still counted." + NEWLINE
        )
    if done.returncode != 0:
        raise SystemExit(
            f"{NEWLINE}CANNOT CHECK THIS: {where} is not committed at HEAD in"
            f" {root}." + NEWLINE + NEWLINE
            + "  " + why + NEWLINE + NEWLINE
            + "  **The file may well be sitting there on disk. That is not the"
            + NEWLINE
            + "  same thing.** This check pins what the other repository has"
            + NEWLINE
            + "  actually COMMITTED, because work that is not committed can still"
            + NEWLINE
            + "  change, and a check that goes green against it is green about"
            + NEWLINE
            + "  nothing." + NEWLINE + NEWLINE
            + "  git said: " + (done.stderr.decode('utf-8', 'replace').strip()
                                or '(nothing)') + NEWLINE
        )
    return done.stdout.decode('utf-8', 'replace')


def readFromServer(*parts):
    """A file out of the server's repository, or a refusal that says what to do."""
    root = whereTheServerIs()
    if root.is_dir():
        return _asItWasCommitted(
            root, parts,
            'This pins the Google scope this door NEEDS against the scope the '
            'seller is actually ASKED for.')
    raise SystemExit(
        f"{NEWLINE}CANNOT CHECK THIS: {'/'.join(parts)} is not at {root}."
        + NEWLINE + NEWLINE
        + "  This pins the Google scope this door NEEDS against the scope the"
        + NEWLINE
        + "  seller is actually ASKED for. Unpinned, the seller grants one thing"
        + NEWLINE
        + "  and the job needs another, and every night fails on a permission"
        + NEWLINE
        + "  nobody withheld." + NEWLINE + NEWLINE
        + "  Point it at the server and run again:" + NEWLINE
        + "      set SERVER=D:" + SLASH + SLASH + "Kartaan-Server" + NEWLINE
        + "      export SERVER=~/Kartaan-Server" + NEWLINE + NEWLINE
        + "  It is NOT skipped when it cannot be found. A check that quietly"
        + NEWLINE
        + "  stops checking is worse than no check, because it is still counted."
        + NEWLINE
    )


def readFromKartaan(*parts):
    """A file out of the other repository, or a refusal that says what to do.

    **THE MESSAGE IS THE POINT.** `FileNotFoundError: sync.js` tells somebody
    nothing about a contract between two repositories -- it reads as a broken
    checkout. This says which fact is unpinned and what it would cost.
    """
    root = whereKartaanIs()
    if root.is_dir():
        return _asItWasCommitted(
            root, parts,
            'This pins something written down in BOTH repositories, with nothing '
            'mechanical joining them.')
    raise SystemExit(
        f"\nCANNOT CHECK THIS: {'/'.join(parts)} is not at {root}.\n\n"
        "  This check pins something written down in BOTH repositories -- Kartaan\n"
        "  and Kartaan AutoSync -- with nothing mechanical joining them. Without\n"
        "  it, the two can drift and the first anybody knows is a screen that is\n"
        "  silently empty.\n\n"
        "  Point it at the other half and run again:\n"
        "      set KARTAAN=D:\\Kartaan-ERP        (Windows)\n"
        "      export KARTAAN=~/Kartaan-ERP       (anywhere else)\n\n"
        "  It is NOT skipped when it cannot be found. A check that quietly stops\n"
        "  checking is worse than no check, because it is still counted.\n"
    )
