"""Talking to the seller's own Firestore. The doing half of `firestore.py` (D114).

**THE TRANSPORT IS HANDED IN**, exactly as it is for Drive and for Amazon, so
every line here is checked with no account, no token and no internet. **Since
job 25 (route (e)) the thing handed in is `transport.FirebaseSeller`: the seller's
OWN Firebase sign-in, as the seller, with no Kartaan key and no Kartaan server in
it.** It has the same `get`/`post` shape as the `Google` that Drive uses, so
nothing in this file changed to take it.

**WHAT IT WRITES: the run log, the day board and the runs, and nothing else.**
Every name it writes is built by `firestore.where_a_document_lives`, which
refuses anything outside those three by name. That refusal is the only lock there
is -- since job 25 the writes are made as the seller, so the seller's own
Security Rules (kept by the Kartaan ERP) decide as well; that is a second lock,
not a replacement for this one.

**WHAT IT READS: the hour the seller chose, and nothing else.** It never writes
it. That setting is the seller's, written from the This business tab, and a job
that could write it would be a second author of one fact (D114).

**AND A REFUSAL SAYS WHICH OF THE TWO IT IS.** "Google will not let this job into
that database" and "there is no such record" send a person to completely
different places, and one message for both is a wasted evening.
"""

from datetime import date, timedelta
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import firestore
import returns
from firestore import (
    API,
    ROOM,
    BOARD,
    CHECK,
    CHECK_KEPT_DAYS,
    DATABASE,
    LOG,
    RETURNS_SHEET,
    RUNS,
    SYNC_LEDGER,
    a_board_row,
    a_check_row,
    a_ledger_record,
    a_returns_sheet_record,
    a_log_line,
    a_run,
    in_calls,
    one_write,
)

# What Google calls the two things this makes. Read from its own documentation.
COMMIT = "{api}/projects/{project}/databases/{database}/documents:commit"
ONE_DOCUMENT = "{api}/{name}"

# **NO SCOPE IS NAMED HERE ANY MORE (job 25, route (e)).** This used to need the
# `datastore` scope on the seller's Google token. The transport handed in is now
# the seller's own Firebase sign-in (`transport.FirebaseSeller`), which carries a
# Firebase ID token, and Firestore applies the seller's own Security Rules to it.


class TheirDatabaseSaidNo(RuntimeError):
    """The seller's database refused, and it says what it said.

    **ITS OWN KIND.** `firestore.Refused` is this job deciding not to do
    something; this is Google deciding not to let it. One is a defect here, the
    other is a permission or a project id, and they are fixed in different places.
    """


def _answered(reply, doing: str):
    """What came back, or a refusal naming what was being done.

    **THE LIKELIEST CAUSE OF A 403 IS NAMED, because it is silent.** The writes
    are made as the seller, so a Security Rule that does not allow one of them
    (or a sign-in for another project) reads as a broken database without this.
    """
    if reply is None:
        raise TheirDatabaseSaidNo(f"{doing}: the seller's database said nothing at all.")
    if not reply.ok:
        code = reply.status
        said = reply.text
        if code == 403:
            raise TheirDatabaseSaidNo(
                f"{doing}: the seller's database would not let this job in (403). "
                "The likeliest reason is that the seller's Security Rules do not allow this "
                "write for the seller's own sign-in, or the Firebase sign-in handed to the run "
                "belongs to a different project. " + said[:200]
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


RUN_QUERY = "{api}/projects/{project}/databases/{database}/documents:runQuery"


def _check_rows_older_than(transport, project: str, first_kept: str):
    """The names of the `sync_check` records whose day is before `first_kept`, asked of the database (reads only those)."""
    where = RUN_QUERY.format(api=API, project=project, database=DATABASE)
    query = {"structuredQuery": {
        "from": [{"collectionId": CHECK}],
        "where": {"fieldFilter": {
            "field": {"fieldPath": "dataDate"}, "op": "LESS_THAN", "value": {"stringValue": first_kept}}},
        "select": {"fields": [{"fieldPath": "dataDate"}]},
    }}
    got = _answered(transport.post(where, json=query), "asking which old cross-check rows are still held").records()
    if not isinstance(got, list):
        # **A REPLY THAT IS NOT A LIST IS NOT "NOTHING OLD".** Taken so, old rows would never be cleared and the page would read them all.
        raise TheirDatabaseSaidNo("asking which old cross-check rows are still held: the answer was not a list.")
    return [one["document"]["name"].rsplit("/", 1)[-1] for one in got if one.get("document")]


def a_check_sink(transport, project: str) -> Callable[[Sequence, date], int]:
    """What landed against what was read, into the seller's own database, for the ERP's Data tab (job 19).

    **ONLY THE LAST `CHECK_KEPT_DAYS` DAYS ARE WRITTEN, AND EVERY OLDER ROW IS DELETED** (the page reads the whole collection on opening it).
    The rows are written first and the old ones come away after, so a failure part way leaves too many rows, never too few.
    Answers how many writes and deletes were sent, which is what counts against the seller's daily allowance.
    """

    def sink(crossings: Sequence, today: date) -> int:
        first_kept = (today - timedelta(days=CHECK_KEPT_DAYS)).isoformat()
        rows = [a_check_row(one) for one in crossings or () if firestore.as_text(one.data_date) >= first_kept]
        sent = write_them(
            transport, project, [one_write(project, CHECK, *row) for row in rows], "writing what landed against what was read")
        old = _check_rows_older_than(transport, project, first_kept)
        sent += write_them(
            transport, project, [firestore.one_delete(project, CHECK, name) for name in old],
            "clearing the cross-check rows older than sixty days")
        return sent

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


def a_ledger_sink(transport, project: str, version: str = "") -> Callable[..., None]:
    """Where the sales ledger is and when it was last written, into the one record the ERP reads (plan jobs 78 and 76).

    **REPLACED WHOLE, EVERY TIME IT IS WRITTEN** -- `one_write` sends no mask, so a field dropped here cannot linger.
    A refusal is thrown like every other write; it is `ledger_sheet.WhatWasWritten` that says a failure here and never
    lets it stop the run.
    """

    def sink(sheet_id: str, wrote_at, rows: int) -> None:
        named, record = a_ledger_record(sheet_id, wrote_at, rows, version)
        write_them(transport, project, [one_write(project, SYNC_LEDGER, named, record)], "writing where the sales ledger is")

    return sink


def a_returns_sheet_sink(transport, project: str) -> Callable[..., None]:
    """Where the returns sheet is, into the one record the ERP reads (job 77 / piece 34): `returns_sheet/sheet`, replaced whole.

    **WRITTEN ONLY WHEN `returns_sheet.py` DECIDES IT MUST BE** (the sheet was just made, or the record is missing or names a
    different sheet). A refusal is thrown like every other write; `returns_sheet` says it and never lets it stop the run.
    """

    def sink(sheet_id: str, created_at) -> None:
        named, record = a_returns_sheet_record(sheet_id, created_at)
        write_them(transport, project, [one_write(project, RETURNS_SHEET, named, record)], "writing where the returns sheet is")

    return sink


def a_returns_sheet_held(transport, project: str) -> Callable[[], Optional[str]]:
    """The sheet id the returns record already holds, or None when there is no record (a 404 is an answer, as for the hour).

    **EVERYTHING ELSE IS THROWN**, so a database that would not answer is never read as "no record" -- that reading would
    make the run write a fresh `createdAt` over a true one.
    """

    def held() -> Optional[str]:
        where = ONE_DOCUMENT.format(api=API, name=firestore.where_a_document_lives(project, RETURNS_SHEET, firestore.THE_RETURNS_RECORD))
        reply = transport.get(where)
        if getattr(reply, "status", 0) == 404:
            return None
        got = _answered(reply, "asking where the returns sheet is")
        found = firestore.plain((got.json() or {}).get("fields")).get("sheetId")
        return str(found).strip() if isinstance(found, str) and found.strip() else None

    return held


# ------------------------------------------------------------------- reading


def what_they_chose(transport, project: str) -> Optional[str]:
    """The hour of their own day the seller chose, or None if they have not.

    **A BUSINESS RECORD THAT IS NOT THERE IS NOT A FAILURE**, and this is the one
    place a 404 is an answer rather than a refusal. A seller who has connected
    their platforms but not yet finished setting the business up has no record,
    and the job fetches at its own default rather than refusing to run at all.

    **EVERYTHING ELSE IS THROWN.** A database that would not answer is not the
    same as a seller who has not chosen, and quietly treating the two alike would
    fetch at the default hour for a seller who asked for eight in the morning,
    for ever, with nothing anywhere saying why.
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


BATCH_GET = "{api}/projects/{project}/databases/{database}/documents:batchGet"
# How many records are asked for in one call. Google's page states no maximum, so this is only to keep a call small -- not a limit.
ASKED_AT_A_TIME = 100


def _what_is_held(transport, project: str, doc_ids: Sequence[str]) -> Dict[str, tuple]:
    """For each record asked for, the days it already holds (none for a record that is not there yet)."""
    held: Dict[str, tuple] = {}
    for at in range(0, len(doc_ids), ASKED_AT_A_TIME):
        chunk = list(doc_ids[at:at + ASKED_AT_A_TIME])
        names = [firestore.where_a_document_lives(project, firestore.LISTING_VIEWS, one) for one in chunk]
        where = BATCH_GET.format(api=API, project=project, database=DATABASE)
        got = _answered(transport.post(where, json={"documents": names}), "asking which days each listing already holds").records()
        if not isinstance(got, list):
            # **A REPLY THAT IS NOT A LIST IS NOT "NOTHING HELD".** Taken so, no old day would ever be dropped and a record would
            # grow past its sixty days with no error.
            raise TheirDatabaseSaidNo("asking which days each listing already holds: the answer was not a list of records.")
        for answer in got:
            found = answer.get("found")
            if found:
                held[found["name"].rsplit("/", 1)[-1]] = firestore.days_held(found)
    return held


def a_views_sink(transport, project: str, today: str, keep: int) -> Callable[..., int]:
    """How each listing is doing, into its record, one figure at a time (job 86 part A).

    **THE RECORDS ARE ASKED FOR FIRST** so a record can be held to its newest `keep` days: the days it has plus the days this
    file brings, newest `keep` of them, stay; every older day is deleted by the same write. A day older than all of them that a
    file brings is not written at all. Answers how many records were written.
    """

    def sink(platform: str, records: Dict[str, Dict[str, Dict]]) -> int:
        ids = {listing: firestore_name(platform, listing) for listing in records}
        held = _what_is_held(transport, project, sorted(ids.values()))
        writes = []
        for listing, days in sorted(records.items()):
            doc_id = ids[listing]
            have = set(held.get(doc_id, ()))
            stay = set(sorted(have | set(days))[-keep:])
            writes.append(firestore.a_views_write(
                project, doc_id, platform, listing,
                {day: figures for day, figures in days.items() if day in stay},
                sorted(have - stay), today,
            ))
        return write_them(transport, project, writes, "writing how each listing is doing")

    return sink


def _what_listings_are_held(transport, project: str, doc_ids: Sequence[str]) -> Dict[str, tuple]:
    """For each record asked for, the listing it already holds and the day it was last changed (nothing for a record that is not there yet)."""
    held: Dict[str, tuple] = {}
    for at in range(0, len(doc_ids), ASKED_AT_A_TIME):
        chunk = list(doc_ids[at:at + ASKED_AT_A_TIME])
        names = [firestore.where_a_document_lives(project, firestore.LISTINGS_SEEN, one) for one in chunk]
        where = BATCH_GET.format(api=API, project=project, database=DATABASE)
        got = _answered(transport.post(where, json={"documents": names}), "asking which listings are already held").records()
        if not isinstance(got, list):
            # **A REPLY THAT IS NOT A LIST IS NOT "NOTHING HELD".** Taken so, every listing would be written again, as new, every night.
            raise TheirDatabaseSaidNo("asking which listings are already held: the answer was not a list of records.")
        for answer in got:
            found = answer.get("found")
            if found:
                one = firestore.listing_held(found)
                if one is not None:
                    held[found["name"].rsplit("/", 1)[-1]] = (one, firestore.listing_day_held(found))
    return held


def a_listings_sink(transport, project: str) -> Callable[..., int]:
    """The listings a listing file names, into their records -- ONLY the ones that are new or that differ from what is held (job 41).

    **THE RECORDS ARE ASKED FOR FIRST**, so a night that brings a file naming the same listings as the last one writes nothing at all:
    his words for it were that a second run queues nothing new. Answers how many records were written.
    """

    def sink(report_id: str, day: str, listings: Dict[str, Dict]) -> int:
        held = _what_listings_are_held(transport, project, sorted(listings))
        writes = [
            firestore.a_listing_write(project, listing, report_id, day)
            for name, listing in sorted(listings.items())
            # **NEW, OR DIFFERENT -- AND NEVER OVER A NEWER FILE'S FIGURES.** A file uploaded late must not put an older stock over a newer one.
            if name not in held or (held[name][0] != listing and held[name][1] <= day)
        ]
        return write_them(transport, project, writes, "writing the listings the platforms' files name")

    return sink


def _the_held_records(transport, project: str, collection: str, doc_ids: Sequence[str]) -> Dict[str, Dict]:
    """The records already held under these names, each as plain data (nothing for a name that is not there). A reply that is not a list stops it."""
    held: Dict[str, Dict] = {}
    for at in range(0, len(doc_ids), ASKED_AT_A_TIME):
        names = [firestore.where_a_document_lives(project, collection, one) for one in doc_ids[at:at + ASKED_AT_A_TIME]]
        got = _answered(
            transport.post(BATCH_GET.format(api=API, project=project, database=DATABASE), json={"documents": names}),
            f"asking which {collection} records are already held",
        ).records()
        if not isinstance(got, list):
            # A reply that is not a list is not "nothing held": taken so, every record would be written again as new, every night.
            raise TheirDatabaseSaidNo(f"asking which {collection} records are already held: the answer was not a list of records.")
        for answer in got:
            found = answer.get("found")
            if found:
                held[found["name"].rsplit("/", 1)[-1]] = firestore.plain_deep({"mapValue": {"fields": found.get("fields") or {}}})
    return held


def a_listing_notes_sink(transport, project: str) -> Callable[..., Tuple[int, int, int]]:
    """What a side file says about each listing, put beside that listing's record -- ONLY for a listing whose record is held, and only what differs (AP9).

    **THE RECORDS ARE ASKED FOR FIRST.** A listing with no record yet is skipped, not made up: the listing file names it first (a note on its own would be a
    record with no `listing`). A second file saying the same writes nothing, and **a file of an earlier day never puts older words over newer ones**
    (the note's own day field, `firestore.NOTE_DAY_FIELD`). **Answers (records written, listings skipped for having no record, notes taken back)** -- the
    night says the second and the third in their own words, never counting a note taken back as a listing marked.

    **A NOTE A LATER COMPLETE FILE NO LONGER NAMES IS TAKEN BACK (D633, AP11)**, and only then: `complete` is true when every row of the file was read.
    A file with a row it could not read takes nothing back -- the row it lost may be the very listing -- and a file older than the note takes back nothing;
    one of the same day does, as a same-day file's note also replaces. A listing the file names with nothing to say (a fee row of `--`) is in `notes` with
    an empty note, so it is named and keeps what it has. The database is asked only for the records still carrying the note
    (`firestore.NOTE_STILL_SAID`), so a listing already taken back is not written again.
    """

    def sink(report_id: str, day: str, notes: Dict[str, Dict], complete: bool = False) -> Tuple[int, int, int]:
        day_field = firestore.NOTE_DAY_FIELD[report_id]
        held = _the_held_records(transport, project, firestore.LISTINGS_SEEN, sorted(notes))
        writes = []
        for name, note in sorted(notes.items()):
            have = held.get(name)
            if have is None:
                continue
            said = {**note, day_field: day}
            if any(have.get(field) != value for field, value in said.items() if field != day_field) and str(have.get(day_field) or "") <= day:
                writes.append(firestore.a_listing_note_write(project, name, said))
        taken_back = []
        if complete:
            still = _the_documents_of(transport, project, firestore.LISTINGS_SEEN, firestore.NOTE_STILL_SAID[report_id], (day_field,),
                                      "asking which listings still carry what an earlier side file said")
            taken_back = [
                firestore.a_listing_note_taken_back(project, name, report_id, day)
                for name, record in still
                if name not in notes and str(record.get(day_field) or "") <= day
            ]
        # A listing named with nothing to say (a `--` fee row) had nothing to write, so it is never counted as "had no record".
        skipped = sum(1 for name, note in notes.items() if note and name not in held)
        written = write_them(transport, project, writes, "writing what the side files say about each listing")
        return written, skipped, write_them(transport, project, taken_back, "taking back what an earlier side file said about a listing")

    return sink


def _what_is_held_of(transport, project: str, collection: str, doc_ids: Sequence[str], digest_field: str, day_field: str) -> Dict[str, tuple]:
    """For each record asked for, its fingerprint and file day (nothing for a record that is not there yet)."""
    return {
        name: (str(one.get(digest_field) or ""), str(one.get(day_field) or ""))
        for name, one in _the_held_records(transport, project, collection, doc_ids).items()
    }


def _is_news(held: Dict[str, tuple], doc_id: str, digest: str, day: str) -> bool:
    """New, or different -- and never over a newer file's figures (a file uploaded late must not undo a later one)."""
    if doc_id not in held:
        return True
    held_digest, held_day = held[doc_id]
    return held_digest != digest and held_day <= day


def a_returns_sink(transport, project: str, today: str) -> Callable[..., int]:
    """The returned lines a returns file names, into their records -- ONLY the ones that are new or that differ from what is held (A78).

    **THE RECORDS ARE ASKED FOR FIRST**, so a second run on the same file writes nothing. Answers how many records were written.
    """

    def sink(report_id: str, day: str, records: Dict[str, Dict]) -> int:
        # **AN AMAZON RETURN THAT HAS GOT ITS RMA ID SINCE IT WAS FIRST SEEN WITHOUT ONE STAYS ONE RECORD (A81).** The name it was
        # first stored under is asked for beside its own; if that one is held, the record is written there (still carrying the RMA
        # ID in `returnKey`), and no second record is made.
        earlier_name: Dict[str, str] = {}
        for doc_id, record in records.items():
            if (
                record.get("platform") == "amazon" and not str(record["returnKey"]).startswith(returns.NO_RMA + "-")
                and record.get("sku") and record.get("startedOn")
            ):
                earlier_name[doc_id] = "amazon__" + returns.a_return_without_an_rma(record["orderId"], record["sku"], record["startedOn"])
        # **TWO RETURNS OF ONE ORDER, SKU AND DAY IN ONE FILE ARE TWO RETURNS:** where more than one record would fold onto the same
        # earlier name, none is folded and each keeps its own RMA name, rather than one overwriting the other.
        shared = {alias for alias in earlier_name.values() if list(earlier_name.values()).count(alias) > 1}
        earlier_name = {doc_id: alias for doc_id, alias in earlier_name.items() if alias not in shared}
        held = _what_is_held_of(transport, project, firestore.RETURNS, sorted(set(records) | set(earlier_name.values())), "digest", "fileDay")
        writes = []
        for doc_id, record in sorted(records.items()):
            stored_as = earlier_name[doc_id] if earlier_name.get(doc_id) in held else doc_id
            if _is_news(held, stored_as, record["digest"], day):
                writes.append(firestore.a_return_write(project, record, named_by=stored_as.split("__", 1)[1]))
        return write_them(transport, project, writes, "writing the returns the platforms' files name")

    return sink


def _the_documents_of(transport, project: str, collection: str, where: object, select: Sequence[str], doing: str) -> List[tuple]:
    """`(record name, plain record)` for the documents of one collection that match, asked of the database. A reply that is not a list stops it."""
    query: Dict = {"from": [{"collectionId": collection}]}
    if select:
        query["select"] = {"fields": [{"fieldPath": one} for one in select]}
    if where:
        query["where"] = where
    got = _answered(
        transport.post(RUN_QUERY.format(api=API, project=project, database=DATABASE), json={"structuredQuery": query}), doing,
    ).records()
    if not isinstance(got, list):
        raise TheirDatabaseSaidNo(f"{doing}: the answer was not a list of records.")
    return [
        (one["document"]["name"].rsplit("/", 1)[-1], firestore.plain_deep({"mapValue": {"fields": one["document"].get("fields") or {}}}))
        for one in got if one.get("document")
    ]


def _the_days_between(first: str, last: str) -> Dict:
    return {"compositeFilter": {"op": "AND", "filters": [
        {"fieldFilter": {"field": {"fieldPath": "day"}, "op": "GREATER_THAN_OR_EQUAL", "value": {"stringValue": first}}},
        {"fieldFilter": {"field": {"fieldPath": "day"}, "op": "LESS_THAN_OR_EQUAL", "value": {"stringValue": last}}},
    ]}}


def a_records_sink(transport, project: str, kind, merge=None) -> Callable[..., int]:
    """The records of one `records.RecordKind` a file names, into the database -- ONLY the new or changed ones, never over a newer file's (A87, D482).

    **THE RECORDS ARE ASKED FOR FIRST**, so a second run on the same file writes nothing. `merge(record, held)` lets a kind keep what the held record
    knows (a paid claim's rupees, a listing's history) before the fingerprints are compared. Answers how many records were written.
    """

    def sink(report_id: str, day: str, records: Dict[str, Dict]) -> int:
        held = _the_held_records(transport, project, kind.collection, sorted(records))
        news = {name: (str(one.get("digest") or ""), str(one.get("fileDay") or "")) for name, one in held.items()}
        writes = []
        for doc_id, record in sorted(records.items()):
            if merge is not None:
                record = merge(record, held.get(doc_id))
            if _is_news(news, doc_id, record["digest"], day):
                writes.append(firestore.a_record_write(project, kind, doc_id, record))
        return write_them(transport, project, writes, f"writing the {kind.what} records")

    return sink


def the_record_sinks(transport, project: str) -> Dict[str, Callable[..., int]]:
    """The sink of every report in `record_reports.RECORD_REPORTS`, by report id -- built from the table, so a new report needs no new sink."""
    import record_reports  # noqa: PLC0415 - kept beside its one use

    return {
        report_id: a_records_sink(transport, project, one.kind, one.merge)
        for report_id, one in record_reports.RECORD_REPORTS.items()
    }


def an_ads_month_sink(transport, project: str, today: str) -> Callable[..., int]:
    """Rebuild each platform's month of ads whole, from that month's per-day records (D463). Answers how many month records were written.

    **WHICH MONTHS:** the ones tonight's ads files touched, and every month that has day records but no month record yet (the backfill, so the ERP
    can read the month records alone; it finishes itself if a night was cut off). A month is read ONCE, in two queries bounded by the month's days
    (the platform is told apart in memory, so no index is needed). A month that cannot be summarised or written is said after the others are done.
    """
    import ads  # noqa: PLC0415 - kept beside its one use

    def sink(touched: Sequence[tuple]) -> int:
        wanted = {(str(platform), str(month)) for platform, month in touched}
        held = {name for name, _ in _the_documents_of(transport, project, firestore.ADS_MONTH, None, ("platform",), "asking which month records exist")}
        # **EVERY MONTH THAT HAS DAY RECORDS BUT NO MONTH RECORD IS BUILT (the backfill, finished even if an earlier night was cut off):** the days
        # are the two-a-day `platform_ads_days` records, read by name only.
        for _, one in _the_documents_of(transport, project, firestore.ADS_DAYS, None, ("platform", "day"), "asking which months have days of ads"):
            at = (str(one.get("platform", "")), str(one.get("day", ""))[:7])
            if at[0] and at[1] and f"{at[0]}__{at[1]}" not in held:
                wanted.add(at)
        sent = 0
        refused: List[str] = []
        for month in sorted({month for _, month in wanted}):
            between = _the_days_between(f"{month}-01", f"{month}-31")
            days = [one for _, one in _the_documents_of(transport, project, firestore.ADS_DAYS, between, (), f"reading {month}'s days of ads")]
            details = [one for _, one in _the_documents_of(transport, project, firestore.ADS_DETAIL, between, (), f"reading {month}'s ad detail")]
            for platform in sorted({p for p, m in wanted if m == month}):
                mine = {str(one.get("day")): one for one in days if one.get("platform") == platform}
                if not mine and not any(one.get("platform") == platform for one in details):
                    continue
                try:
                    record = ads.build_month(platform, month, mine, details, today)
                except Exception as wrong:  # noqa: BLE001 - said below, after the other months are written
                    refused.append(str(wrong))
                    continue
                # One call per month, so one that Firestore refuses cannot take another month's write down with it.
                try:
                    sent += write_them(transport, project, [firestore.a_record_write(project, ads.MONTH, f"{platform}__{month}", record)], "writing a month of ads")
                except TheirDatabaseSaidNo as wrong:
                    refused.append(f"{platform} {month}: {wrong}")
        if refused:
            raise TheirDatabaseSaidNo(" ".join(refused))
        return sent

    return sink


def an_ads_sink(transport, project: str, today: str) -> Callable[..., int]:
    """The ad figures an ads file names, into their records -- ONLY the ones that are new or that differ from what is held (A78).

    `kind` is `days` (one record per platform per day, the campaigns) or a breakdown's name (one record per day per kind).
    Answers how many records were written.
    """

    def sink(report_id: str, platform: str, kind: str, day: str, records: Dict[str, Dict]) -> int:
        if kind == "days":
            held = _what_is_held_of(transport, project, firestore.ADS_DAYS, sorted(records), "campaignsDigest", "campaignsFileDay")
            writes = [
                firestore.a_ads_days_write(project, platform, one["day"], one["campaigns"], one["digest"], day, today)
                for doc_id, one in sorted(records.items())
                if _is_news(held, doc_id, one["digest"], day)
            ]
        else:
            held = _what_is_held_of(transport, project, firestore.ADS_DETAIL, sorted(records), "digest", "fileDay")
            writes = [
                firestore.a_ads_detail_write(project, doc_id, platform, one, day, today)
                for doc_id, one in sorted(records.items())
                if _is_news(held, doc_id, one["digest"], day)
            ]
        return write_them(transport, project, writes, "writing the ad figures the platforms' files name")

    return sink


def firestore_name(platform: str, listing: str) -> str:
    """`<platform>__<listingId>`, the name the ERP's rules and screens look a listing up by."""
    return f"{platform}__{listing}"
