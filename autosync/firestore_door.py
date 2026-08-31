"""Talking to the seller's own Firestore. The doing half of `firestore.py` (D114).

**THE TRANSPORT IS HANDED IN**, exactly as it is for Drive and for Amazon, so
every line here is checked with no account, no token and no internet. The thing
handed in is the same `Google` from `transport.py` that Drive already uses --
**one connection, one refresh token, two Google services** -- because they are
the same seller's same permission, and building a second way to hold that token
would be a second place it could leak.

**WHAT IT WRITES: the run log, the day board and the runs, and nothing else.**
Every name it writes is built by `firestore.where_a_document_lives`, which
refuses anything outside those three by name. That refusal is the only lock there
is -- the `datastore` scope is authorised by IAM rather than by
`firestore.rules`, which is Google's own documented behaviour and is written out
in full at the top of `firestore.py`.

**WHAT IT READS: the hour the seller chose, and nothing else.** It never writes
it. That setting is the seller's, written from the This business tab, and a job
that could write it would be a second author of one fact (D114).

**AND A REFUSAL SAYS WHICH OF THE TWO IT IS.** "Google will not let this job into
that database" and "there is no such record" send a person to completely
different places, and one message for both is a wasted evening.
"""

from typing import Callable, Dict, Optional, Sequence

import firestore
from firestore import (
    API,
    ROOM,
    BOARD,
    DATABASE,
    LOG,
    RUNS,
    a_board_row,
    a_log_line,
    a_run,
    in_calls,
    one_write,
)

# What Google calls the two things this makes. Read from its own documentation.
COMMIT = "{api}/projects/{project}/databases/{database}/documents:commit"
ONE_DOCUMENT = "{api}/{name}"

# **THE SCOPE D114 ADDED, and this is the file that needs it.** Written here as
# well as in `server/going_off.py` because this is where its absence is felt, and
# a check pins the two against each other -- asked for in one place and needed in
# another is how a permission quietly stops being asked for.
SCOPE = "https://www.googleapis.com/auth/datastore"


class TheirDatabaseSaidNo(RuntimeError):
    """The seller's database refused, and it says what it said.

    **ITS OWN KIND.** `firestore.Refused` is this job deciding not to do
    something; this is Google deciding not to let it. One is a defect here, the
    other is a permission or a project id, and they are fixed in different places.
    """


def _answered(reply, doing: str):
    """What came back, or a refusal naming what was being done.

    **THE LIKELIEST CAUSE OF A 403 IS NAMED, because it is documented and it is
    silent.** A seller who connected before D114 granted `drive.file` and nothing
    else; their token can put files in Drive all night and cannot write one
    record. Without this sentence that reads as a broken database.
    """
    if reply is None:
        raise TheirDatabaseSaidNo(f"{doing}: the seller's database said nothing at all.")
    if not reply.ok:
        code = reply.status
        said = reply.text
        if code == 403:
            raise TheirDatabaseSaidNo(
                f"{doing}: Google would not let this job into the seller's database (403). "
                "The likeliest reason is that the seller connected before Kartaan started "
                "asking for it -- connecting again grants it. " + said[:200]
            )
        if code == 404:
            raise TheirDatabaseSaidNo(
                f"{doing}: there is nothing at that name in the seller's database (404). "
                "Either the project id is not theirs, or the record is not there. " + said[:200]
            )
        raise TheirDatabaseSaidNo(f"{doing}: the seller's database refused ({code}). {said}"[:400])
    return reply


# ------------------------------------------------------------------- writing


def write_them(transport, project: str, writes: Sequence[Dict], doing: str, room: int = ROOM) -> int:
    """Send these writes, in as many calls as their size needs. Answers how many went.

    **A CALL THAT FAILS STOPS THE REST**, and it is thrown rather than counted.
    The caller is a log flush, and a flush that reported success having sent half
    is exactly the silent evidence loss this package exists against -- the marker
    would advance over lines that never left the building.

    `room` is how much of one call the writes may fill. It has one real value,
    named in `firestore.py` from Google's own limits page; it is an argument only
    so that the rule above can be checked without building ten megabytes of log.
    """
    sent = 0
    for batch in in_calls(writes, room=room):
        where = COMMIT.format(api=API, project=project, database=DATABASE)
        _answered(transport.post(where, json={"writes": batch}), doing)
        sent += len(batch)
    return sent


def a_log_sink(transport, project: str) -> Callable[[Sequence], None]:
    """The run log, into the seller's own database.

    **THE SECOND PLACE, NEVER THE ONLY ONE (D100).** The copy in the seller's own
    Drive stays: it is what survives when Kartaan itself is the broken thing, and
    what can be sent for support. This is the everyday view.
    """

    def sink(lines: Sequence) -> None:
        # **NO GUARD ON THERE BEING ANYTHING TO SEND.** `write_them` makes no call
        # for an empty list, so a guard here would be a line no check could ever
        # make go red -- and an unreachable guard reads exactly like a working one.
        writes = [one_write(project, LOG, *a_log_line(line)) for line in lines or ()]
        write_them(transport, project, writes, "writing the run log down")

    return sink


def a_board_sink(transport, project: str) -> Callable[[Sequence], None]:
    """The day board, into the seller's own database.

    **THE WHOLE BOARD, EVERY RUN.** Each row is named for its report and its day,
    so tonight's answer about the 12th replaces last night's rather than sitting
    beside it -- and a day that has since arrived stops reading as missing without
    anything having to go and delete the old row.
    """

    def sink(rows: Sequence) -> None:
        writes = [one_write(project, BOARD, *a_board_row(row)) for row in rows or ()]
        write_them(transport, project, writes, "writing the day board down")

    return sink


def a_run_sink(transport, project: str) -> Callable[..., None]:
    """One run: written when it starts, and written again when it finishes.

    **WRITTEN AT THE START AS WELL AS THE END, and that is the point of it.** A
    run that started and never finished is the case the reference could not
    report at all -- four days in twenty-six -- and it can only be seen by
    something having been written down before the thing that ended it happened.
    """

    def sink(name: str, started_at, finished_at=None, why: str = "") -> None:
        named, record = a_run(name, started_at, finished_at=finished_at, why=why)
        write_them(transport, project, [one_write(project, RUNS, named, record)], "writing the run down")

    return sink


# ------------------------------------------------------------------- reading


def what_they_chose(transport, project: str) -> Optional[str]:
    """The hour of their own day the seller chose, or None if they have not.

    **A BUSINESS RECORD THAT IS NOT THERE IS NOT A FAILURE**, and this is the one
    place a 404 is an answer rather than a refusal. A seller who has connected
    their platforms but not yet finished setting the business up has no record,
    and the job fetches at its own default rather than refusing to run at all.

    **EVERYTHING ELSE IS THROWN.** A database that would not answer is not the
    same as a seller who has not chosen, and quietly treating the two alike would
    fetch at two in the morning for a seller who asked for eleven at night, for
    ever, with nothing anywhere saying why.
    """
    where = ONE_DOCUMENT.format(api=API, name=firestore.where_the_business_is(project))
    reply = transport.get(where)
    # **`getattr` RATHER THAN `reply.status`, because this is the one call whose
    # answer may be nothing at all** -- and an answer that never came is
    # `_answered`'s to refuse, in its own words, rather than something to be read
    # as "they have not chosen an hour".
    if getattr(reply, "status", 0) == 404:
        return None
    got = _answered(reply, "asking what hour the seller chose")
    return firestore.the_hour_they_chose(got.json())


def both_places(first: Callable[[Sequence], None], then: Callable[[Sequence], None]) -> Callable[[Sequence], None]:
    """One sink that writes to two places, in that order.

    **THE ORDER IS THE WHOLE DESIGN, and it is decided by which one is safe to
    repeat.** A flush advances its marker only if the sink returned, so anything
    that throws sends the same lines again next time. Every record written to the
    seller's database is named from its own content, so writing it twice writes
    it once; the Drive copy is a file that is READ and APPENDED TO, so writing it
    twice writes the lines twice.

    **So the database goes FIRST and Drive goes second.** Drive failing repeats a
    harmless write; the other way round would put a second copy of every line in
    the seller's Drive file each time Drive was slow.
    """

    def sink(lines: Sequence) -> None:
        first(lines)
        then(lines)

    return sink
