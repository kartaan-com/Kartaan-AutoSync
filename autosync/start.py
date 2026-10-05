"""The file the workflow runs. It reads the secrets and opens the connections.

**IT DECIDES NOTHING.** Every rule about what a run does, and in what order, is
in `nightly.py`, where it is proved by being broken on purpose. This file exists
so that all of that can be proved: what is left here is the part that genuinely
cannot be, because it needs a real Amazon account, a real Google account, and a
real network.

**THE TEN VALUES IT READS ARE GITHUB ACTIONS SECRETS on the seller's own
repository** (job 25, route (e)): the device client's id, secret and refresh
token for Drive and Sheets, the seller's own Firebase API key and refresh token
for their database, the project, and Amazon's three. They are read once, handed straight to the door each belongs to,
and never written to the log, the run's record or an error message. Golden Rule
8: nothing here stores one, prints one, or puts one in an address.

**AND THE HOUR THE SELLER CHOSE IS NOT ONE OF THEM ANY MORE (D114).** It is read
off the business record in the seller's own database, every run, where the This
business tab writes it. A setting with two homes is a setting that disagrees with
itself, and the one the seller can see has to win.

Run: python autosync/start.py
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import clock  # noqa: E402
import ledger_sheet  # noqa: E402
import nightly  # noqa: E402
import views  # noqa: E402


def the_old_data_folder() -> str:  # pragma: no cover - one secret, read in one place
    """The id of the old "Kartaan data" folder the Server made: only the merge reads inside it."""
    return nightly._needed("DRIVE_FOLDER_ID")


def the_google_connection(now):  # pragma: no cover - the device client, read once for the night and the merge
    """Drive and Sheets, through the device client's refresh token (job 25, route (e))."""
    from transport import Google  # noqa: PLC0415

    return Google(
        client_id=nightly._needed("GOOGLE_DEVICE_CLIENT_ID"),
        client_secret=nightly._needed("GOOGLE_DEVICE_CLIENT_SECRET"),
        refresh_token=nightly._needed("GOOGLE_DEVICE_REFRESH_TOKEN"),
        now=now,
    )


def main() -> int:  # pragma: no cover - the only part that opens a connection
    """Read the secrets, build the doors, do one tick, say what happened.

    **IT DECIDES NOTHING.** Everything worth checking is in `one_tick`, and the
    only reason this is a separate function is that a real connection cannot be
    checked without one.
    """
    from amazon_door import AmazonDoor, fetch_one
    import merge
    from drive_door import a_door, the_kartaan_folder
    from firestore_door import (
        a_board_sink, a_listings_sink, a_log_sink, a_run_sink, a_views_sink, both_places, what_they_chose,
    )
    from transport import FirebaseSeller, Google, for_amazon

    def now() -> datetime:
        # **HIS TIME, AND THIS IS THE ONLY PLACE IT IS WORKED OUT.** The machine
        # runs on Greenwich; he does not. Everything downstream of this line --
        # every log line, every record of when a run started, every day worked
        # out -- is his, and nothing converts again. His words: *"I live and
        # speak and work in IST, so everything should be according to that
        # only."*
        return clock.his_clock(datetime.now(timezone.utc).replace(tzinfo=None))

    # **WHICH DATABASE THE RUN LOG, THE DAY BOARD AND THE RUNS GO INTO (D114).**
    # The seller's own Firebase project. Not a credential -- it names a project
    # and grants nothing; what grants anything is the seller's own sign-in below
    # and the Security Rules in their project.
    their_project = nightly._needed("FIREBASE_PROJECT_ID")
    # **TWO SIGN-INS, AND NEITHER IS KARTAAN'S SERVER (job 25, route (e)).** Drive
    # and Sheets go through the device client's refresh token below; the seller's
    # database goes through the seller's OWN Firebase sign-in, as the seller, under
    # their own Security Rules. Google calls a device client's secret "not a
    # secret", so nothing Kartaan has to keep private is in this repository.
    their_login = FirebaseSeller(
        api_key=nightly._needed("FIREBASE_API_KEY"),
        refresh_token=nightly._needed("FIREBASE_REFRESH_TOKEN"),
        now=now,
    )
    # **ONE CONNECTION, ONE REFRESH TOKEN, TWO GOOGLE SERVICES.** Drive and Sheets
    # are the same seller's same permission; a second way of holding that token
    # would be a second place it could leak.
    #
    # **AND THE THIRD IS WHY THE SALES LEDGER COSTS NO NEW PERMISSION (D137).**
    # `drive.file` reaches only the files this app created -- so the ledger has to
    # be MADE by this connection, and it is: the same object below both makes it
    # and writes to it, which is what makes the everyday permission carry.
    google = the_google_connection(now)
    # **THE ONE `Kartaan` FOLDER AT THE TOP OF HIS DRIVE, FOUND BY NAME (job 34).** Everything
    # the run puts away is inside it, in his layout, and the extension finds the same folder
    # the same way. No folder id is kept anywhere.
    inside = the_kartaan_folder(google)
    # **NOT BEFORE THE ONE-TIME MERGE (job 34).** The run's memory moves to `Kartaan / System` in
    # the merge; a night before it would start from nothing and fetch everything again.
    first = merge.why_the_merge_comes_first(google, the_old_data_folder())
    if first:
        print(first)
        return 1
    amazon = AmazonDoor(
        transport=for_amazon(),
        credentials={
            "client_id": nightly._needed("AMAZON_CLIENT_ID"),
            "client_secret": nightly._needed("AMAZON_CLIENT_SECRET"),
            "refresh_token": nightly._needed("AMAZON_REFRESH_TOKEN"),
        },
        now=now,
    )

    said: List[str] = []

    def say(line: str) -> None:
        said.append(line)
        print(line)

    put_file = a_door(google, inside, say)
    read_state, save_state = nightly._state_in_drive(google, inside)
    read_manifest, save_manifest = nightly._manifest_in_drive(google, inside)
    today = now().date()

    def fetch(report_id: str, data_date, asked_already=None):
        return fetch_one(
            door=amazon,
            report_id=report_id,
            data_date=data_date,
            put_file=lambda file_name, body: put_file(report_id, file_name, body),
            say=say,
            asked_already=asked_already,
        )

    # **WHERE A SALE GOES, AND THIS IS THE JOIN THAT WAS MISSING.** For two days
    # every part of the sales ledger was finished and none of them was called by
    # anything: the door, the ERP's own half, and the id that nothing supplied.
    #
    # **IT IS RESOLVED BEFORE THE RUN, not on the first sale.** A seller whose
    # ledger has gone must be told at the start of the night, not a hundred files
    # in -- and told once, rather than once for every file.
    #
    # **AND EVERY RULE IN IT IS IN `ledger_sheet.the_writing_half`, WHERE IT CAN
    # BE DRIVEN.** This file needs a real Google account, so a rule written here
    # is a rule nobody ever watches fail -- which is exactly how the ledger came
    # to be finished at both ends and called by nothing.
    record_the_sales, could_not_write_sales = ledger_sheet.the_writing_half(
        google, read_state, save_state, say, inside=inside,
    )

    def send(lines: Sequence[str]) -> None:
        # **WHERE AN ALARM GOES IS NOT DECIDED HERE and is not decided yet.** D100
        # says the seller's own destination, the operator's separately. Until that
        # is built it is printed, which is visible in the job's own record -- and
        # a printed alarm is not a silent one.
        for line in lines:
            print(f"ALARM  {line}")

    tick = nightly.one_tick(
        now=now,
        read_state=read_state,
        save_state=save_state,
        arrivals=nightly._arrivals_from_drive(google, inside, say),
        fetch=fetch,
        # **WRITTEN TWICE, ON PURPOSE (D100), AND THE ORDER IS THE DESIGN.** The
        # seller's own database is what the three screens read; the copy in their
        # Drive is what survives when Kartaan itself is the broken thing. The
        # database goes FIRST because a flush that throws sends the same lines
        # again -- and every record there is named from its own content, so
        # writing it twice writes it once, while the Drive copy is a file that is
        # appended to.
        sink=both_places(
            a_log_sink(their_login, their_project),
            nightly._log_to_drive(google, inside, today),
        ),
        # **THE BOARD AND THE RUNS, D114.** They were worked out on every run and
        # thrown away: the three screens built for them were drawn, proved, and
        # reading nothing.
        save_board=a_board_sink(their_login, their_project),
        save_run=a_run_sink(their_login, their_project),
        # **AND THE STANDING ANSWER TO "IS THE FILE REALLY THERE", IN THE
        # SELLER'S OWN DRIVE (specification 25).** Read as well as written,
        # because this half replaces only its own three lines and leaves the
        # extension's twenty-three exactly as they were.
        read_manifest=read_manifest,
        save_manifest=save_manifest,
        # **AND THE HOUR THE SELLER CHOSE, READ AND NEVER WRITTEN (D113, D114).**
        # It is written on the business record from the This business tab. Until
        # this line it reached nothing, and a seller who chose eight in the
        # morning was fetched at the default hour for ever with nothing saying
        # so.
        ask_the_hour=lambda: what_they_chose(their_login, their_project),
        send=send,
        # **WHAT IS NEW IN THE SELLER'S FOLDER.** Both of these are real and both
        # are used tonight: the folders are listed and the night's summary says
        # how many files are sitting there unread.
        what_is_in_the_folder=nightly._the_folder_itself(google, inside),
        bring_the_file_back=nightly._one_file_back(google),
        # **AND THE ONE PLACE A SALE LANDS.** `None` when the seller's ledger could
        # not be reached, AND `None` today for a second reason: the writing half
        # refuses to run at all until D157's four date-marker columns exist, and
        # says so by name. Either way `read_what_is_new` answers it the same -- no
        # file opened, none marked read, and the night's summary saying so.
        record_the_sales=record_the_sales,
        # **AND WHERE HOW EACH LISTING IS DOING GOES (job 86 part A):** a record per listing in the seller's own database, a
        # figure at a time, held to the newest sixty days.
        record_views=a_views_sink(their_login, their_project, today.isoformat(), views.DAYS_KEPT),
        # **AND THE LISTINGS A LISTING FILE NAMES (job 41):** one record each, for the ERP to put in front of the seller to let in.
        record_listings=a_listings_sink(their_login, their_project),
        # Set only by somebody pressing the button in GitHub. The workflow passes
        # it through; nothing on a schedule ever sets it.
        even_if_not_due=os.environ.get("EVEN_IF_NOT_DUE", "").strip().lower() == "true",
    )

    print(tick.summary())

    # **WHAT IS SAID LAST, AND THE NUMBER THIS JOB EXITS WITH, IS DECIDED IN
    # `nightly.how_the_night_ends`.** It was decided here for one round -- a
    # night that could not write the sales ledger returning 1 -- and nothing
    # anywhere read this file, so that rule was never once watched fail. **A rule
    # nobody asks about is a comment (D170).** It is in `nightly.py` now, where
    # `nightly_checks.py` puts it back and watches its own named check go red.
    lines, code = nightly.how_the_night_ends(tick, could_not_write_sales)
    for one in lines:
        print(one)
    # **TIDYING COMES LAST AND NEVER STOPS A NIGHT (job 40):** logs past sixty days and report files
    # past the GST period go to his bin, each one said. A fault in it is printed and makes the job red
    # -- after everything else is done, never instead of it.
    for one in nightly.tidy_the_drive(google, inside, today, print):
        print(f"TIDY FAULT  {one}")
        code = code or 1
    return code


def the_merge(mode: str) -> int:  # pragma: no cover - opens a connection, like `main`
    """The one-time merge of his old folders into `Kartaan /`. `plan` writes nothing; `apply` is his yes.

    Everything it decides is in `merge.py`, where it is checked against a stand-in Drive. Only
    the Google connection is read here: the same three device values, and the one folder id the
    repository already holds for the old "Kartaan data".
    """
    import merge  # noqa: PLC0415

    def now() -> datetime:
        return clock.his_clock(datetime.now(timezone.utc).replace(tzinfo=None))

    return merge.run_the_merge(
        the_google_connection(now), the_old_data_folder(), mode,
        os.environ.get("MERGE_FIGURES", ""), print,
    )


def not_ready() -> int:  # pragma: no cover - opens a connection, like `main`
    """The job could not fetch because secrets are not set: say that it ran.

    **NEVER RED BY ITSELF AND NEVER RAISES.** The gate step before this one has
    already ended the job red and named what is missing; this writes the record
    that the job RAN, where it can, and prints plainly where it cannot. Only
    names are read from the environment for the list -- the Google values are
    used to reach the seller's own Drive and are never printed.
    """
    try:
        from firestore_door import a_run_sink  # noqa: PLC0415
        from transport import FirebaseSeller, Google  # noqa: PLC0415

        not_set = [n for n in os.environ.get("NOT_SET", "").split() if n]
        needed = ("GOOGLE_DEVICE_CLIENT_ID", "GOOGLE_DEVICE_CLIENT_SECRET", "GOOGLE_DEVICE_REFRESH_TOKEN")
        absent = [n for n in needed if not os.environ.get(n, "").strip()]
        if absent:
            print("The run could not write down that it ran, because these are not set: "
                  + ", ".join(absent))
            return 0

        def now() -> datetime:
            return clock.his_clock(datetime.now(timezone.utc).replace(tzinfo=None))

        google = Google(
            client_id=os.environ["GOOGLE_DEVICE_CLIENT_ID"],
            client_secret=os.environ["GOOGLE_DEVICE_CLIENT_SECRET"],
            refresh_token=os.environ["GOOGLE_DEVICE_REFRESH_TOKEN"],
            now=now,
        )
        from drive_door import the_kartaan_folder  # noqa: PLC0415

        read_state, save_state = nightly._state_in_drive(google, the_kartaan_folder(google))
        project = os.environ.get("FIREBASE_PROJECT_ID", "").strip()
        api_key = os.environ.get("FIREBASE_API_KEY", "").strip()
        sign_in = os.environ.get("FIREBASE_REFRESH_TOKEN", "").strip()
        # The run row goes in the seller's own database as the seller, so it needs
        # all three of project, key and sign-in; without them only Drive's copy is written.
        their_login = FirebaseSeller(api_key, sign_in, now) if (project and api_key and sign_in) else None
        if their_login is None:
            print("The run row was not written to the seller's database, because the project, "
                  "Firebase API key or Firebase sign-in is not set; Drive's copy is still written.")
        faults = nightly.a_run_that_could_not_fetch(
            not_set, now, read_state, save_state,
            a_run_sink(their_login, project) if their_login else None,
        )
        for one in faults:
            print(one)
        print("Written down that the run happened and could not fetch." if not faults else "")
    except Exception as wrong:  # noqa: BLE001 - the job is already red for its real reason
        print(f"The run could not write down that it ran: {wrong}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    # **THE MERGE IS ASKED FOR BY HAND, NEVER BY A SCHEDULE.** The workflow passes `MERGE` only
    # from the button; anything but `plan` or `apply` is refused rather than read as "no".
    _merge = os.environ.get("MERGE", "").strip().lower()
    if sys.argv[1:] == ["not-ready"]:
        sys.exit(not_ready())
    elif _merge in ("plan", "apply"):
        sys.exit(the_merge(_merge))
    elif _merge:
        print(f"MERGE is {_merge!r}; it can only be plan or apply, so nothing was done.")
        sys.exit(1)
    else:
        sys.exit(main())
