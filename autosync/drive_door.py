"""Talking to the seller's own Drive. The doing half of `drive.py`.

**THE TRANSPORT IS HANDED IN**, exactly as it is for Amazon, so every line here
can be checked with no account, no token and no internet. Nothing in this package
opens a connection of its own.

**READ FROM GOOGLE'S OWN DOCUMENTATION FIRST (Golden Rule 1).** The two upload
addresses, the two ways up and where the boundary sits are all its, not ours --
see the note at the top of `drive.py`.

**AND WHAT IT DELIBERATELY DOES NOT DO: it does not handle a credential.** It is
given something that can already talk, and asks it to. Where the seller's token
comes from and where it is kept is a decision that has to pass through Jaiswal's
own hands (Golden Rule 8), and code that took one would be code that could leak
one.
"""

import json
from typing import Callable, Dict, List, Optional, Sequence

from landing import the_file_that_matters
from drive import (
    FOLDER,
    MULTIPART,
    Landing,
    a_folder_for,
    kind_of,
    the_metadata,
    what_to_do_about,
    why_it_cannot_be_put,
)

FILES = "https://www.googleapis.com/drive/v3/files"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"

# What separates the two parts of a multipart upload. Any string neither part
# contains would do; this one is ours so nothing can collide with it by accident.
BOUNDARY = "kartaan-autosync-boundary"


class DriveSaidNo(RuntimeError):
    """Drive refused, and it says what it said.

    **ITS OWN KIND.** "The file could not be put anywhere" and "the seller has
    run out of Drive" need different things doing about them, and one message for
    both is how a month of failures reads as one problem.
    """


def _answered(reply, doing: str):
    """What came back, or a refusal naming what was being done."""
    if reply is None:
        raise DriveSaidNo(f"{doing}: Drive said nothing at all.")
    if not getattr(reply, "ok", False):
        said = getattr(reply, "text", "") or ""
        code = getattr(reply, "status", "")
        raise DriveSaidNo(f"{doing}: Drive refused ({code}). {said}"[:400])
    return reply


def folder_for(transport, report_id: str, inside: str) -> str:
    """The id of one report's folder, made if it is not there yet.

    **FOUND BY NAME, MADE ONLY IF MISSING.** A folder made every night is a Drive
    with thirty folders of one name and the files spread across them -- and
    nothing that reads them would ever say so.

    **AND TWO OF THE SAME NAME IS NOT SOMETHING TO CHOOSE BETWEEN.** Picking one
    would put tonight's file in a different folder from last night's, silently.
    """
    name = a_folder_for(report_id)
    looking = (
        f"name = '{name}' and mimeType = '{FOLDER}' "
        f"and '{inside}' in parents and trashed = false"
    )
    reply = _answered(
        transport.get(FILES, params={"q": looking, "fields": "files(id,name)"}),
        f"looking for the {name} folder",
    )
    found = (reply.json() or {}).get("files", [])
    if len(found) > 1:
        raise DriveSaidNo(
            f"There are {len(found)} folders called {name} in the seller's Drive. "
            "Which one tonight's file belongs in cannot be known, so nothing has been put."
        )
    if found:
        return found[0]["id"]

    made = _answered(
        transport.post(
            FILES,
            params={"fields": "id"},
            json={"name": name, "mimeType": FOLDER, "parents": [inside]},
        ),
        f"making the {name} folder",
    )
    return (made.json() or {})["id"]


def what_is_already_there(transport, folder_id: str) -> List[Dict]:
    """Every file in one folder, so a second copy can be refused."""
    reply = _answered(
        transport.get(
            FILES,
            params={
                "q": f"'{folder_id}' in parents and trashed = false",
                "fields": "files(id,name)",
            },
        ),
        "reading what is already in the folder",
    )
    return list((reply.json() or {}).get("files", []))


def what_has_arrived(transport, folder_id: str) -> List[Dict]:
    """Every file in one folder, WITH ITS SIZE, so a day can be called arrived.

    **A DIFFERENT QUESTION FROM `what_is_already_there`, which is why it is a
    different function.** That one asks "is this name taken?", so a name is all it
    needs. This one asks "did this day really arrive?", and presence is not
    correctness: **a nought-byte file is the one kind of wrongness presence alone
    can catch**, and the reference's manifest recorded a truncated catalogue file
    as Verified because it only ever looked at the name.

    Drive hands the size back as text, and leaves it out altogether for anything
    that has no size of its own -- a folder, or one of its own documents. Missing
    is read as nought, which is the safe direction: it means the day is fetched
    again rather than written off as arrived.
    """
    reply = _answered(
        transport.get(
            FILES,
            params={
                "q": f"'{folder_id}' in parents and trashed = false",
                "fields": "files(id,name,size)",
            },
        ),
        "reading what has arrived in the folder",
    )
    out: List[Dict] = []
    for one in (reply.json() or {}).get("files", []):
        try:
            size = int(one.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        out.append({"id": one.get("id"), "name": one.get("name"), "size": size})
    return out


def bring_the_file_back(transport, file_id: str) -> bytes:
    """The contents of one file that is already in the seller's Drive.

    **THE ONE THING THIS DOOR COULD NOT DO, and the run's own memory needs it.**
    Everything else here puts things away; what a run leaves for the next one has
    to be read again the following night, and a job that could only write would
    begin from nothing every time.

    From Google's own documentation (read 2026-08-28): the file's ordinary
    address with `alt=media`, which is what tells Drive to hand back the contents
    rather than the record describing them. Without it Drive answers the
    description, and a run would read its own memory as a paragraph of JSON about
    a file instead of the file.

    **THE BYTES ARE ASKED FOR PLAINLY, not politely.** A transport that cannot
    hand back what it downloaded stops the run and names itself, rather than
    quietly answering nothing -- which here would read as "there is no memory of
    the last run" and ask Amazon again for every report it is already building.
    """
    reply = _answered(
        transport.get(f"{FILES}/{file_id}", params={"alt": "media"}),
        "reading a file back out of the seller's Drive",
    )
    return reply.raw


def put_the_file(transport, landing: Landing, body: bytes) -> Dict:
    """Put one file where the landing says, the way its size says.

    Answers what Drive said about the file it now holds.
    """
    wrong = why_it_cannot_be_put(landing.folder_id, landing.file_name, body)
    if wrong:
        raise DriveSaidNo(wrong)

    if landing.by == MULTIPART:
        return _in_one_request(transport, landing, body)
    return _in_two_requests(transport, landing, body)


def _in_one_request(transport, landing: Landing, body: bytes) -> Dict:
    """Google's `multipart`: the file and what it is, in one go.

    Documented for "a small file (5 MB or less) along with metadata that
    describes the file, in a single request".
    """
    front = (
        f"--{BOUNDARY}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(the_metadata(landing))}\r\n"
        f"--{BOUNDARY}\r\n"
        f"Content-Type: {landing.kind}\r\n\r\n"
    ).encode("utf-8")
    back = f"\r\n--{BOUNDARY}--".encode("utf-8")

    reply = _answered(
        transport.post(
            UPLOAD,
            params={"uploadType": "multipart", "fields": "id,name,size"},
            headers={"Content-Type": f"multipart/related; boundary={BOUNDARY}"},
            data=front + body + back,
        ),
        f"putting {landing.file_name} in the seller's Drive",
    )
    return reply.json() or {}


def _in_two_requests(transport, landing: Landing, body: bytes) -> Dict:
    """Google's `resumable`: ask where to put it, then put it.

    Documented for "large files (greater than 5 MB) and when there's a high
    chance of network interruption" -- which is every listing file he has.
    """
    asking = _answered(
        transport.post(
            UPLOAD,
            params={"uploadType": "resumable", "fields": "id,name,size"},
            headers={
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": landing.kind,
                "X-Upload-Content-Length": str(len(body)),
            },
            json=the_metadata(landing),
        ),
        f"asking Drive where to put {landing.file_name}",
    )
    where = (getattr(asking, "headers", {}) or {}).get("Location")
    if not where:
        # **SAID, NOT ASSUMED.** Without the address there is nowhere to send the
        # file, and carrying on would send a large file to the wrong place.
        raise DriveSaidNo(
            f"Drive agreed to take {landing.file_name} and did not say where to send it."
        )

    reply = _answered(
        transport.put(where, headers={"Content-Type": landing.kind}, data=body),
        f"sending {landing.file_name} to the seller's Drive",
    )
    return reply.json() or {}


def a_door(transport, inside: str, say: Callable[[str], None]) -> Callable[..., Dict]:
    """Putting a file away, in the shape the runner expects.

    `inside` is the one folder in the seller's own Drive that Kartaan was given.
    Everything it writes goes under that and nowhere else -- which is what the
    narrow `drive.file` scope is for, and what makes it honest to say the product
    cannot see the rest of their Drive.
    """

    def put_file(report_id: str, file_name: str, body: bytes) -> Dict:
        # **NAMED FOR WHAT IT IS, NEVER FOR WHAT WAS EXPECTED, and this is the one
        # place a name and a body meet.** Between 14 June and 6 July 2026 Meesho
        # served its payment export as a zip with the spreadsheet inside it; the
        # extension saved those bytes under the name it had already chosen, and
        # eleven of his files sat in Drive looking exactly like the other
        # eighty-four while nothing could open a single one of them. They were
        # the right name, the right size, the right folder, and ARRIVED on the
        # day board. **Said out loud when it happens, because that silence is
        # what hid them for two months.**
        file_name, body, note = the_file_that_matters(file_name, body)
        if note:
            say(note)
        folder_id = folder_for(transport, report_id, inside)
        already = what_is_already_there(transport, folder_id)
        landing = Landing(
            folder_id=folder_id,
            file_name=file_name,
            kind=kind_of(file_name),
            size=len(body or b""),
        )
        doing = what_to_do_about(file_name, already)
        if doing == "somebody has to look":
            raise DriveSaidNo(
                f"There is already more than one {file_name} in the {report_id} folder. "
                "Replacing one would leave the others, so nothing has been put and somebody "
                "has to look."
            )
        if doing == "replace":
            # **REPLACED, NEVER PUT BESIDE.** A folder with two files for one day
            # is a folder where nobody can say which the numbers came from -- and
            # the reference put three wrongly-dated duplicates into a real one.
            same = next(one for one in already if one.get("name") == file_name)
            _answered(
                transport.delete(f"{FILES}/{same['id']}"),
                f"taking away the older {file_name}",
            )
            say(f"{report_id}: replacing the {file_name} that was already there.")
        return put_the_file(transport, landing, body)

    return put_file
