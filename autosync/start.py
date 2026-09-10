"""The file the workflow runs. It reads the secrets and opens the connections.

**IT DECIDES NOTHING.** Every rule about what a run does, and in what order, is
in `nightly.py`, where it is proved by being broken on purpose. This file exists
so that all of that can be proved: what is left here is the part that genuinely
cannot be, because it needs a real Amazon account, a real Google account, and a
real network.

**THE EIGHT VALUES IT READS ARE GITHUB ACTIONS SECRETS on the seller's own
repository.** They are read once, handed straight to the door each belongs to,
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


def main() -> int:  # pragma: no cover - the only part that opens a connection
    """Read the secrets, build the doors, do one tick, say what happened.

    **IT DECIDES NOTHING.** Everything worth checking is in `one_tick`, and the
    only reason this is a separate function is that a real connection cannot be
    checked without one.
    """
    from amazon_door import AmazonDoor, fetch_one
    from drive_door import a_door
    from firestore_door import a_board_sink, a_log_sink, a_run_sink, both_places, what_they_chose
    from transport import Google, for_amazon

    def now() -> datetime:
        # **HIS TIME, AND THIS IS THE ONLY PLACE IT IS WORKED OUT.** The machine
        # runs on Greenwich; he does not. Everything downstream of this line --
        # every log line, every record of when a run started, every day worked
        # out -- is his, and nothing converts again. His words: *"I live and
        # speak and work in IST, so everything should be according to that
        # only."*
        return clock.his_clock(datetime.now(timezone.utc).replace(tzinfo=None))

    inside = nightly._needed("DRIVE_FOLDER_ID")
    # **WHICH DATABASE THE RUN LOG, THE DAY BOARD AND THE RUNS GO INTO (D114).**
    # The seller's own Firebase project. Not a credential -- it names a project
    # and grants nothing; what grants anything is the Google permission below,
    # which the seller gave and which now covers their own database too.
    their_project = nightly._needed("FIREBASE_PROJECT_ID")
    # **ONE CONNECTION, ONE REFRESH TOKEN, THREE GOOGLE SERVICES.** Drive,
    # Firestore and now Sheets are the same seller's same permission; a second way
    # of holding that token would be a second place it could leak.
    #
    # **AND THE THIRD IS WHY THE SALES LEDGER COSTS NO NEW PERMISSION (D137).**
    # `drive.file` reaches only the files this app created -- so the ledger has to
    # be MADE by this connection, and it is: the same object below both makes it
    # and writes to it, which is what makes the everyday permission carry.
    google = Google(
        client_id=nightly._needed("GOOGLE_CLIENT_ID"),
        client_secret=nightly._needed("GOOGLE_CLIENT_SECRET"),
        refresh_token=nightly._needed("GOOGLE_REFRESH_TOKEN"),
        now=now,
    )
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
        google, read_state, save_state, say,
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
        arrivals=nightly._arrivals_from_drive(google, inside),
        fetch=fetch,
        # **WRITTEN TWICE, ON PURPOSE (D100), AND THE ORDER IS THE DESIGN.** The
        # seller's own database is what the three screens read; the copy in their
        # Drive is what survives when Kartaan itself is the broken thing. The
        # database goes FIRST because a flush that throws sends the same lines
        # again -- and every record there is named from its own content, so
        # writing it twice writes it once, while the Drive copy is a file that is
        # appended to.
        sink=both_places(
            a_log_sink(google, their_project),
            nightly._log_to_drive(google, inside, today),
        ),
        # **THE BOARD AND THE RUNS, D114.** They were worked out on every run and
        # thrown away: the three screens built for them were drawn, proved, and
        # reading nothing.
        save_board=a_board_sink(google, their_project),
        save_run=a_run_sink(google, their_project),
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
        ask_the_hour=lambda: what_they_chose(google, their_project),
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
    return code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
