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

**IT REFUSES; IT DOES NOT SKIP.** A check that quietly stops checking when it
cannot find what it needs is worse than no check at all, because it is still
counted in the tally. So this raises, and says exactly what to do about it.

**HOW TO POINT IT AT THE OTHER HALF:**

    set KARTAAN=D:\\Kartaan          (Windows)
    export KARTAAN=~/Kartaan         (anywhere else)

and if that is not set, a sibling folder called `Kartaan` next to this one is
tried, which is the ordinary way somebody has both checked out.
"""

import os
import pathlib

HERE = pathlib.Path(__file__).resolve().parent.parent

NEWLINE = chr(10)
SLASH = chr(92)


def whereKartaanIs():
    """The ERP's folder, or where it would be.

    **TWO NAMES ARE TRIED, and that is deliberate rather than a guess.** The
    repository was renamed to `Kartaan-ERP` (D148) and the folder on a machine
    may still be the old `Kartaan` -- a folder cannot be renamed by a session
    running inside it. New name first, old name second.

    **THIS IS TEMPORARY AND SAYS SO.** When the folder is renamed everywhere,
    the second name comes out. A fallback nobody wrote down is how two spellings
    of one thing survive for a year.
    """
    said = os.environ.get('KARTAAN', '').strip()
    if said:
        return pathlib.Path(said)
    for name in ('Kartaan-ERP', 'Kartaan'):
        here = HERE.parent / name
        if here.is_dir():
            return here
    return HERE.parent / 'Kartaan-ERP'


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


def readFromServer(*parts):
    """A file out of the server's repository, or a refusal that says what to do."""
    wanted = whereTheServerIs().joinpath(*parts)
    if wanted.is_file():
        return wanted.read_text(encoding='utf-8')
    raise SystemExit(
        f"{NEWLINE}CANNOT CHECK THIS: {'/'.join(parts)} is not at {wanted}."
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
    wanted = root.joinpath(*parts)
    if wanted.is_file():
        return wanted.read_text(encoding='utf-8')
    raise SystemExit(
        f"\nCANNOT CHECK THIS: {'/'.join(parts)} is not at {wanted}.\n\n"
        "  This check pins something written down in BOTH repositories -- Kartaan\n"
        "  and Kartaan AutoSync -- with nothing mechanical joining them. Without\n"
        "  it, the two can drift and the first anybody knows is a screen that is\n"
        "  silently empty.\n\n"
        "  Point it at the other half and run again:\n"
        "      set KARTAAN=D:\\Kartaan        (Windows)\n"
        "      export KARTAAN=~/Kartaan       (anywhere else)\n\n"
        "  It is NOT skipped when it cannot be found. A check that quietly stops\n"
        "  checking is worse than no check, because it is still counted.\n"
    )
