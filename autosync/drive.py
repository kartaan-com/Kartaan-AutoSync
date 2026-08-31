"""Putting a file in the seller's own Drive: what is decided, not what is done.

**THE FILE GOES TO THE SELLER'S OWN DRIVE, UNTOUCHED, BEFORE ANYTHING READS IT
(D100).** Keeping the original is what makes a bad reading fixable without going
back to the platform -- and for Meesho payments there is no going back at all:
the portal ignores the date and always hands over the current settlement batch.

**NOTHING HERE TOUCHES A NETWORK.** Every decision is made against plain values so
it can be checked with no account, no token and no internet; `drive_door.py` does
the talking, with the transport handed in.

**READ FROM GOOGLE'S OWN DOCUMENTATION BEFORE A LINE WAS WRITTEN (Golden Rule 1),
and two facts shape everything below:**

  - **an upload of 5 MB or less goes one way and a larger one goes another.**
    Google documents `multipart` for "a small file (5 MB or less) along with
    metadata ... in a single request", and `resumable` for "large files (greater
    than 5 MB) and when there's a high chance of network interruption". His
    listing file is comfortably over that;
  - **the narrowest scope that can create a file is `drive.file`**, which reaches
    only files this app itself made or that were explicitly shared with it -- not
    the seller's other files. **That is the one to ask for**, and it is worth
    saying out loud: a product that asks a seller for their whole Drive when it
    needs one folder is a product they are right to refuse.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Sequence

# Google's own cut-off between the two ways of uploading, in bytes.
SMALL_ENOUGH_FOR_ONE_REQUEST = 5 * 1024 * 1024

MULTIPART = "multipart"
RESUMABLE = "resumable"

# The one scope this asks for. See the note at the top of this file.
SCOPE = "https://www.googleapis.com/auth/drive.file"

# What Drive calls a folder.
FOLDER = "application/vnd.google-apps.folder"

# What our files are.
BY_EXTENSION = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "zip": "application/zip",
    "json": "application/json",
    "txt": "text/plain",
}


def kind_of(file_name: str) -> str:
    """What a file is, worked out from its name.

    **NEVER GUESSED AT SOMETHING PLAUSIBLE.** A spreadsheet uploaded as plain text
    opens as gibberish, and a seller looking at it has no way to tell that the
    fetching worked and only the labelling was wrong.
    """
    at = str(file_name or "").rsplit(".", 1)
    if len(at) != 2 or not at[1]:
        return "application/octet-stream"
    return BY_EXTENSION.get(at[1].lower(), "application/octet-stream")


def how_to_upload(size: int) -> str:
    """Which of Google's two ways this file goes up by.

    Documented: 5 MB or less in one request with its metadata; larger than that,
    resumable. **The boundary is Google's, not ours** -- a file exactly on it is
    "5 MB or less" and goes the first way.
    """
    return MULTIPART if int(size) <= SMALL_ENOUGH_FOR_ONE_REQUEST else RESUMABLE


@dataclass(frozen=True)
class Landing:
    """Where one file is going, and what it will be called."""

    folder_id: str
    file_name: str
    kind: str
    size: int

    @property
    def by(self) -> str:
        return how_to_upload(self.size)


def why_it_cannot_be_put(folder_id: str, file_name: str, body) -> Optional[str]:
    """What is wrong with putting this file there, in words, or None.

    **ASKED BEFORE ANYTHING IS SENT.** A folder id that is empty, or a file with
    nothing in it, is a fault here -- and the reference uploaded into a folder
    whose id was the literal word PLACEHOLDER for weeks, reporting success every
    night.
    """
    if not folder_id:
        return "There is nowhere to put it: no folder was given."
    if not file_name:
        return "There is nothing to call it: no file name was given."
    if body is None:
        return f"{file_name}: there is nothing to put -- no file came back."
    if len(body) == 0:
        return (
            f"{file_name}: the file has nothing in it, so it has not been put anywhere. "
            "An empty file counted as arrived would stop its day ever being fetched again."
        )
    return None


def what_to_do_about(file_name: str, already_there: Sequence[Dict]) -> str:
    """One of three words: put it, replace it, or leave it.

    **A SECOND COPY IS THE FAULT THIS EXISTS TO PREVENT.** The reference put three
    wrongly-dated duplicates into a seller's Drive, and a folder with two files
    for one day is a folder where nobody can say which one the numbers came from.

    So a name that is already there is REPLACED rather than added beside -- the
    day is the same day, and the newer fetch is the one that was asked for.
    """
    same = [one for one in (already_there or ()) if one.get("name") == file_name]
    if not same:
        return "put"
    if len(same) > 1:
        # **MORE THAN ONE ALREADY THERE IS NOT SOMETHING TO TIDY UP SILENTLY.**
        # Somebody has to look: replacing one of them leaves the others, and
        # deleting the rest is a decision nothing here is entitled to make.
        return "somebody has to look"
    return "replace"


def the_metadata(landing: Landing) -> Dict:
    """What Drive is told about the file.

    The parent folder is given as a list because Drive takes a list -- a file can
    sit in more than one place. Ours never does, and saying so once here is
    better than every caller remembering.
    """
    return {"name": landing.file_name, "parents": [landing.folder_id]}


def a_folder_for(report_id: str) -> str:
    """What the folder for one report is called.

    **ONE FOLDER PER REPORT (D100), named after the report itself.** The reference
    kept folder ids in its own source; a name worked out from the report is one
    nobody has to keep a list of.
    """
    if not report_id:
        raise ValueError("A folder has to be for some report.")
    return report_id
