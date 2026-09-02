"""Checks for talking to the seller's own Drive, with no Drive anywhere.

**A STAND-IN DRIVE, DELIBERATELY AWKWARD.** It refuses when a real one refuses, it
can hold two folders of one name the way a real one can, and it says nothing back
when a real one might.

**THE ONES THAT MATTER MOST:** a folder is made only when it is missing -- one
made every night is a Drive holding thirty folders of one name with the files
spread across them, and nothing that reads them would ever say so; and the same
day fetched twice REPLACES rather than sitting beside, because a folder with two
files for one day is one where nobody can say which the numbers came from.

Run: python autosync/drive_door_checks.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import drive_door as tool  # noqa: E402
from drive import FOLDER, Landing  # noqa: E402

ran = 0
failures = []
THREW = []


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


def answered(work):
    try:
        return work()
    except Exception as wrong:  # noqa: BLE001
        THREW.append(repr(wrong))
        return None


def refused(work):
    """The words it refused with, or empty when it did not refuse."""
    try:
        work()
    except tool.DriveSaidNo as wrong:
        return str(wrong)
    except Exception as wrong:  # noqa: BLE001
        THREW.append(repr(wrong))
        return ""
    return ""


class Reply:
    def __init__(self, body=None, ok=True, status=200, headers=None, text="", raw=b""):
        self.ok = ok
        self.status = status
        self.headers = headers or {}
        self.text = text
        # The bytes themselves, which is what reading a file back hands over. A
        # real reply carries both; so does this one.
        self.raw = raw
        self._body = body

    def json(self):
        return self._body


class FakeDrive:
    """A Drive, as far as this needs one."""

    def __init__(self, **how):
        self.how = how
        self.asked = []
        self.folders = list(how.get("folders", []))
        self.files = list(how.get("files", []))
        self.deleted = []
        self.sent = []

    def get(self, where, params=None, headers=None):
        self.asked.append(("get", where, params))
        if self.how.get("refuse_reads"):
            return Reply(ok=False, status=503, text="Drive is unwell")
        if "/" in where.replace("https://www.googleapis.com/drive/v3/files", "", 1):
            # Asking for one file BY ID rather than searching -- which is how a
            # file is read back out again.
            return Reply(raw=self.how.get("contents", b""))
        looking = (params or {}).get("q", "")
        whose = self.folders if FOLDER in looking else self.files

        # **IT ANSWERS IN PAGES, because the real one does and that was the whole
        # fault.** A stand-in that always hands back everything in one go is a
        # stand-in that cannot fail the way the real thing failed -- and this
        # file's checks went green against a listing that read one page of eight
        # hundred files for as long as it did.
        if self.how.get("said_incomplete"):
            return Reply({"files": [dict(one) for one in whose], "incompleteSearch": True})
        if self.how.get("same_token_for_ever"):
            return Reply({"files": [dict(one) for one in whose], "nextPageToken": "stuck"})

        a_page = self.how.get("a_page")
        if a_page:
            start = int((params or {}).get("pageToken") or 0)
            page = [dict(one) for one in whose[start:start + a_page]]
            said = {"files": page}
            if start + a_page < len(whose):
                said["nextPageToken"] = str(start + a_page)
            return Reply(said)

        return Reply({"files": [dict(one) for one in whose]})

    def post(self, where, params=None, headers=None, json=None, data=None):
        self.asked.append(("post", where, params))
        self.last_headers = headers or {}
        self.last_json = json
        if self.how.get("refuse_writes"):
            return Reply(ok=False, status=403, text="not allowed")
        kind = (params or {}).get("uploadType")
        if kind is None:
            made = {"id": f"folder-{len(self.folders) + 1}", "name": (json or {}).get("name")}
            self.folders.append(made)
            return Reply(made)
        if kind == "resumable":
            self.sent.append(("asked", headers))
            if self.how.get("no_address"):
                return Reply({}, headers={})
            return Reply({}, headers={"Location": "https://upload.example.invalid/here"})
        self.sent.append(("one-request", data))
        return Reply({"id": "file-1", "name": (params or {}).get("fields")})

    def put(self, where, headers=None, data=None):
        self.asked.append(("put", where, None))
        self.sent.append(("two-requests", data))
        return Reply({"id": "file-2", "name": "sent"})

    def delete(self, where):
        self.asked.append(("delete", where, None))
        self.deleted.append(where)
        return Reply({})


SAID = []


def say(line):
    SAID.append(line)


# ------------------------------------------------ the folder

check("a folder that is already there is used, not made again",
      answered(lambda: tool.folder_for(
          FakeDrive(folders=[{"id": "f9", "name": "me_orders"}]), "me_orders", "root")) == "f9")

made = FakeDrive()
check("and one that is missing is made",
      answered(lambda: tool.folder_for(made, "me_orders", "root")) == "folder-1")
check("named after the report", answered(lambda: made.folders[0]["name"]) == "me_orders")
# **MADE ONLY ONCE.** A folder made every night is a Drive with thirty folders of
# one name and the files spread across them, and nothing that reads them says so.
check("and asking again finds the one that was made, rather than making another",
      answered(lambda: tool.folder_for(made, "me_orders", "root")) == "folder-1"
      and len(made.folders) == 1)

# **TWO OF ONE NAME IS NOT SOMETHING TO CHOOSE BETWEEN.** Picking one would put
# tonight's file in a different folder from last night's, silently.
two = FakeDrive(folders=[{"id": "a", "name": "me_orders"}, {"id": "b", "name": "me_orders"}])
check("two folders of one name is refused rather than guessed between",
      "2 folders called me_orders" in refused(lambda: tool.folder_for(two, "me_orders", "root")))
check("and it says nothing has been put",
      "nothing has been put" in refused(lambda: tool.folder_for(two, "me_orders", "root")))

check("a Drive that will not answer is said, not swallowed",
      "Drive refused" in refused(
          lambda: tool.folder_for(FakeDrive(refuse_reads=True), "me_orders", "root")))
check("and the refusal says what was being done",
      "looking for the me_orders folder" in refused(
          lambda: tool.folder_for(FakeDrive(refuse_reads=True), "me_orders", "root")))

# ------------------------------------------------ which way it goes up

small = FakeDrive()
check("a small file goes up in one request",
      answered(lambda: tool.put_the_file(
          small, Landing("f1", "a.csv", "text/csv", 900), b"x" * 900)) is not None
      and small.sent[0][0] == "one-request")
# **THE FILE AND WHAT IT IS, IN ONE GO** -- and the metadata really carries the
# folder, or the file lands loose in the seller's Drive where nothing finds it.
check("and it carries the folder it belongs in",
      b'"parents": ["f1"]' in small.sent[0][1] or b'"parents":["f1"]' in small.sent[0][1])
check("and the file's own name", b"a.csv" in small.sent[0][1])
check("and the file itself", b"x" * 900 in small.sent[0][1])

big = FakeDrive()
BIG = b"y" * (6 * 1024 * 1024)
check("a large file is asked about first, then sent",
      answered(lambda: tool.put_the_file(
          big, Landing("f1", "b.xlsx", "text/x", len(BIG)), BIG)) is not None
      and [one[0] for one in big.sent] == ["asked", "two-requests"])
check("and Drive is told how big it will be before it is sent",
      big.sent[0][1].get("X-Upload-Content-Length") == str(len(BIG)))
# **SAID, NOT ASSUMED.** Without the address there is nowhere to send it, and
# carrying on would send a large file to the wrong place.
check("Drive agreeing and not saying where is its own refusal",
      "did not say where to send it" in refused(lambda: tool.put_the_file(
          FakeDrive(no_address=True), Landing("f1", "b.xlsx", "text/x", len(BIG)), BIG)))

# --------------------- the request really is the shape Google documents

# **EVERY ONE OF THESE IS GOOGLE'S, NOT OURS (Golden Rule 1), and a wrong one
# fails in a way that reads like the seller's Drive being broken.**
asking = FakeDrive(folders=[{"id": "f9", "name": "me_orders"}])
answered(lambda: tool.folder_for(asking, "me_orders", "root-folder"))
FOLDER_Q = (asking.asked[0][2] or {}).get("q", "")
check("a folder is looked for inside the one folder Kartaan was given",
      "'root-folder' in parents" in FOLDER_Q)
# **AND NOT AMONG THE THINGS THE SELLER HAS THROWN AWAY.** A folder in the bin
# would be found, written into, and never seen again.
check("and not among what has been thrown away", "trashed = false" in FOLDER_Q)
check("and it is looked for as a folder, not as any file with that name",
      FOLDER in FOLDER_Q)
check("and only the id and name are asked for, not the whole of it",
      (asking.asked[0][2] or {}).get("fields") == "nextPageToken,incompleteSearch,files(id,name)")

reading = FakeDrive(folders=[{"id": "f9", "name": "me_orders"}])
answered(lambda: tool.what_is_already_there(reading, "f9"))
FILES_Q = (reading.asked[0][2] or {}).get("q", "")
check("what is already there is read from that folder",
      "'f9' in parents" in FILES_Q and "trashed = false" in FILES_Q)
check("and only the id and name of each",
      (reading.asked[0][2] or {}).get("fields") == "nextPageToken,incompleteSearch,files(id,name)")

making = FakeDrive()
answered(lambda: tool.folder_for(making, "me_returns", "root-folder"))
check("a folder that is made asks only for its id back",
      (making.asked[1][2] or {}).get("fields") == "id")

# **THE MULTIPART SHAPE.** Two parts, one boundary, the metadata as JSON and the
# file as itself -- Google refuses anything else, and a refusal here reads like
# the seller's Drive being at fault.
shaped = FakeDrive()
answered(lambda: tool.put_the_file(shaped, Landing("f1", "a.csv", "text/csv", 3), b"row"))
BODY = shaped.sent[0][1]
check("the multipart body is separated by the boundary",
      BODY.count(tool.BOUNDARY.encode()) == 3)
check("and it ends the way Google says a multipart body ends",
      BODY.endswith(f"--{tool.BOUNDARY}--".encode()))
check("the first part says it is JSON",
      b"Content-Type: application/json; charset=UTF-8" in BODY)
check("and the second says what the file really is", b"Content-Type: text/csv" in BODY)
check("and the request itself names the boundary, or Google cannot read it",
      shaped.last_headers.get("Content-Type") == f"multipart/related; boundary={tool.BOUNDARY}")

# **THE RESUMABLE SHAPE.** What it is and how big, said before it is sent.
asked_big = FakeDrive()
BIGGER = b"z" * (6 * 1024 * 1024)
answered(lambda: tool.put_the_file(asked_big, Landing("f2", "b.xlsx", "text/x", len(BIGGER)), BIGGER))
check("asking where to put a large file is sent as JSON",
      asked_big.last_headers.get("Content-Type") == "application/json; charset=UTF-8")
check("and says what the file will be", asked_big.last_headers.get("X-Upload-Content-Type") == "text/x")
check("and the metadata carries the folder", (asked_big.last_json or {}).get("parents") == ["f2"])
check("and the name", (asked_big.last_json or {}).get("name") == "b.xlsx")

# **A DRIVE THAT ANSWERS NOTHING IS ANSWERED WITH NOTHING**, rather than falling
# over one line later on something that is not there.
class NoOkAtAll:
    """Something that came back without saying whether it worked.

    **TREATED AS A REFUSAL, which is the safe direction.** Read as success, a
    file nobody put anywhere would be recorded as landed and its day never
    fetched again.
    """


class SaysNothing(FakeDrive):
    def post(self, where, params=None, headers=None, json=None, data=None):
        super().post(where, params, headers, json, data)
        return Reply(None, headers={"Location": "https://upload.example.invalid/x"})

    def put(self, where, headers=None, data=None):
        super().put(where, headers, data)
        return Reply(None)

check("a Drive that says nothing about the file is answered with nothing, not a crash",
      answered(lambda: tool.put_the_file(
          SaysNothing(), Landing("f1", "a.csv", "text/csv", 3), b"row")) == {})
check("and the same for a large one",
      answered(lambda: tool.put_the_file(
          SaysNothing(), Landing("f1", "b.xlsx", "text/x", 6 * 1024 * 1024),
          b"z" * (6 * 1024 * 1024))) == {})

# **SOMETHING THAT DOES NOT SAY WHETHER IT WORKED IS A REFUSAL.** Read as
# success, a file nobody put anywhere would be recorded as landed and its day
# never fetched again.
class SaysNeither(FakeDrive):
    def get(self, where, params=None, headers=None):
        super().get(where, params, headers)
        return NoOkAtAll()

check("an answer that does not say whether it worked is treated as a refusal",
      "Drive refused" in refused(lambda: tool.folder_for(SaysNeither(), "me_orders", "root")))

# **A REFUSAL WITH NO WORDS STILL REFUSES**, and still says what was being done.
class RefusesSilently(FakeDrive):
    def get(self, where, params=None, headers=None):
        super().get(where, params, headers)
        return Reply(ok=False, status=500, text=None)

silent = refused(lambda: tool.folder_for(RefusesSilently(), "me_orders", "root"))
check("a refusal with no words of its own still refuses", "Drive refused" in silent)
check("and still says what was being done", "looking for the me_orders folder" in silent)
check("without the word None where the reason should be", "None" not in silent)

# ------------------------------------------------ what is refused before sending

check("a file with nothing in it is refused before anything is sent",
      "nothing in it" in refused(lambda: tool.put_the_file(
          FakeDrive(), Landing("f1", "a.csv", "text/csv", 0), b"")))
empty = FakeDrive()
refused(lambda: tool.put_the_file(empty, Landing("f1", "a.csv", "text/csv", 0), b""))
check("and nothing was sent", answered(lambda: empty.sent) == [])

# ------------------------------------------------ the whole door

SAID.clear()
plain = FakeDrive()
put = tool.a_door(plain, "root", say)
check("a file lands", answered(lambda: put("me_orders", "meesho_me_orders_2026-08-26.csv", b"row")) is not None)
check("under the one folder Kartaan was given",
      answered(lambda: plain.folders[0]["name"]) == "me_orders")

# **THE SAME DAY AGAIN REPLACES, NEVER SITS BESIDE.**
again = FakeDrive(
    folders=[{"id": "f1", "name": "me_orders"}],
    files=[{"id": "old", "name": "meesho_me_orders_2026-08-26.csv"}],
)
SAID.clear()
check("the same day fetched again lands",
      answered(lambda: tool.a_door(again, "root", say)(
          "me_orders", "meesho_me_orders_2026-08-26.csv", b"newer")) is not None)
check("and the one that was there is taken away first, not left beside it",
      answered(lambda: len(again.deleted)) == 1)
check("and it says so, so nobody wonders where the older one went",
      answered(lambda: any("replacing" in one for one in SAID)))

# **MORE THAN ONE ALREADY THERE NEEDS A PERSON.** Replacing one leaves the
# others, and deleting the rest is a decision nothing here is entitled to make.
muddle = FakeDrive(
    folders=[{"id": "f1", "name": "me_orders"}],
    files=[{"id": "a", "name": "x.csv"}, {"id": "b", "name": "x.csv"}],
)
check("more than one of the same name is refused",
      "somebody has to look" in refused(
          lambda: tool.a_door(muddle, "root", say)("me_orders", "x.csv", b"row")))
# **AND IT NAMES BOTH THE FILE AND THE FOLDER**, or somebody is told to look and
# not told where.
check("and it says which file, in which folder",
      "x.csv" in refused(lambda: tool.a_door(muddle, "root", say)("me_orders", "x.csv", b"row"))
      and "me_orders" in refused(
          lambda: tool.a_door(muddle, "root", say)("me_orders", "x.csv", b"row")))

# **NOTHING AT ALL IS REFUSED RATHER THAN COUNTED AS AN EMPTY FILE.** A door
# handed nothing must not put a nought-byte file in the seller's Drive.
check("a door handed nothing at all refuses",
      "no file came back" in refused(
          lambda: tool.a_door(FakeDrive(folders=[{"id": "f1", "name": "me_orders"}]), "root", say)(
              "me_orders", "a.csv", None)))
check("and nothing is taken away", answered(lambda: muddle.deleted) == [])

# **ANOTHER DAY'S FILE IS NOT IN THE WAY.**
beside = FakeDrive(
    folders=[{"id": "f1", "name": "me_orders"}],
    files=[{"id": "old", "name": "meesho_me_orders_2026-08-25.csv"}],
)
check("yesterday's file is left exactly where it is",
      answered(lambda: tool.a_door(beside, "root", say)(
          "me_orders", "meesho_me_orders_2026-08-26.csv", b"row")) is not None
      and beside.deleted == [])

# ------------------------------------------------ it handles no credential

# **IT IS GIVEN SOMETHING THAT CAN ALREADY TALK.** Where the seller's token comes
# from and where it is kept has to pass through Jaiswal's own hands (Golden Rule
# 8), and code that took one would be code that could leak one.
SOURCE = (Path(__file__).resolve().parent / "drive_door.py").read_text(encoding="utf-8")
for word in ("client_secret", "refresh_token", "private_key", "Authorization", "Bearer"):
    check(f"nothing here handles a credential -- no {word}", word not in SOURCE)


# ------------------------------------------- reading a folder to see what arrived

# **A DIFFERENT QUESTION FROM "IS THIS NAME TAKEN", which is why it asks for a
# different thing.** That one needs a name; this one needs a SIZE, because
# presence is not correctness -- a nought-byte file is the one kind of wrongness
# presence alone can catch, and the reference's manifest recorded a truncated
# catalogue file as Verified.
counting = FakeDrive(files=[
    {"id": "a", "name": "amazon_az_orders_2026-08-27.csv", "size": "120"},
    {"id": "b", "name": "amazon_az_orders_2026-08-26.csv", "size": "0"},
])
arrived = answered(lambda: tool.what_has_arrived(counting, "f9"))
ARRIVED_Q = (counting.asked[0][2] or {}).get("q", "")
check("what has arrived is read from that folder",
      "'f9' in parents" in ARRIVED_Q and "trashed = false" in ARRIVED_Q)
check("and the size is asked for as well as the name",
      (counting.asked[0][2] or {}).get("fields")
      == "nextPageToken,incompleteSearch,files(id,name,size)")
check("every file in the folder comes back", len(arrived or []) == 2)
check("and its size comes back as a number, not as the text Drive sends",
      [one["size"] for one in (arrived or [])] == [120, 0])
check("and its name and id come with it",
      (arrived or [{}])[0].get("name") == "amazon_az_orders_2026-08-27.csv"
      and (arrived or [{}])[0].get("id") == "a")

# **DRIVE LEAVES THE SIZE OUT for anything that has no size of its own -- a
# folder, or one of its own documents. Missing is read as nought, which is the
# safe direction: the day is fetched again rather than written off as arrived.**
sizeless = FakeDrive(files=[{"id": "c", "name": "a_folder"}])
check("a file Drive gave no size for counts as empty, not as unknown",
      [one["size"] for one in (answered(lambda: tool.what_has_arrived(sizeless, "f9")) or [])] == [0])
odd = FakeDrive(files=[{"id": "d", "name": "x", "size": "not a number"}])
check("and a size that is not a number counts as empty rather than stopping the run",
      [one["size"] for one in (answered(lambda: tool.what_has_arrived(odd, "f9")) or [])] == [0])

# ------------------- THE FOLDER IS READ TO THE END (found and fixed 2026-09-02)

# **THE FAULT: DRIVE WAS ASKED ONCE AND THE FIRST PAGE TAKEN AS THE WHOLE
# FOLDER.** His `flipkart` folder holds around eight hundred files and `meesho`
# around four hundred and seventy. Read one page deep, the reader would never see
# most of them -- and what has already been read would let go of their ids,
# because from inside `whats_new` a short listing is a tidied folder.
#
# **AND `fields` WAS WHY IT COULD NOT BE NOTICED.** Google's documentation on
# partial responses (read 2026-09-02) says a mask of `files(id,name)` returns only
# that, so `nextPageToken` never arrived. The one thing that would have said the
# listing was short had been filtered out of the reply.

MANY = [{"id": f"id-{n}", "name": f"file-{n}.csv", "size": "10"} for n in range(850)]
paged = FakeDrive(files=MANY, a_page=100)
all_of_them = answered(lambda: tool.what_has_arrived(paged, "f9"))
check("A FOLDER OF 850 FILES COMES BACK AS 850, NOT AS ONE PAGE",
      len(all_of_them or []) == 850)
check("and it took as many requests as there were pages", len(paged.asked) == 9)
check("and every file is there, not just the first page's",
      {one["id"] for one in (all_of_them or [])} == {one["id"] for one in MANY})
check("the page marker Drive sent is handed back on the next request",
      (paged.asked[1][2] or {}).get("pageToken") == "100")
check("and the first request carries no page marker at all",
      "pageToken" not in (paged.asked[0][2] or {}))

# **`nextPageToken` IS ASKED FOR BY NAME, or it never comes back.** This is the
# half of the fault that made the other half invisible.
check("nextPageToken is asked for by name in the fields Drive is sent",
      "nextPageToken" in ((paged.asked[0][2] or {}).get("fields") or ""))
check("and so is incompleteSearch",
      "incompleteSearch" in ((paged.asked[0][2] or {}).get("fields") or ""))

# **THE PAGE SIZE IS ASKED FOR RATHER THAN LEFT TO DRIVE.** Its own reference
# gives two different defaults depending on the kind of Drive -- 100 for a shared
# one, the whole list otherwise -- and a page size nobody can name is a page size
# nobody can reason about. 1000 is the documented maximum.
check("how many to send is asked for explicitly, not left to the default",
      (paged.asked[0][2] or {}).get("pageSize") == tool.A_PAGEFUL)
check("and it is the most Drive will give, so a big folder takes the fewest asks",
      tool.A_PAGEFUL == 1000)

# **A FOLDER THAT FITS IN ONE PAGE STILL TAKES ONE REQUEST.** The fix must not
# make an ordinary night cost anything.
small = FakeDrive(files=MANY[:5], a_page=100)
check("a folder that fits in one page is read in one request",
      len(answered(lambda: tool.what_has_arrived(small, "f9")) or []) == 5
      and len(small.asked) == 1)

# **AN INCOMPLETE SEARCH REFUSES.** Drive's own word for "some results might be
# missing". A short listing that says it is short is the one kind this can catch,
# and acting on it would let go of ids for files that are still there.
incomplete = FakeDrive(files=MANY[:20], said_incomplete=True)
check("A LISTING DRIVE ITSELF CALLS INCOMPLETE REFUSES RATHER THAN BEING BELIEVED",
      "incomplete" in refused(lambda: tool.what_has_arrived(incomplete, "f9")))
check("and it says nothing is being decided on a folder only partly known",
      "only partly known" in refused(lambda: tool.what_has_arrived(incomplete, "f9")))
check("and it says how many it did get, so somebody can tell how bad it was",
      "20 files" in refused(lambda: tool.what_has_arrived(incomplete, "f9")))

# A page marker that never advances is Drive answering oddly, and following it
# for ever is a job that never ends.
stuck = FakeDrive(files=MANY[:10], same_token_for_ever=True)
check("a page marker that comes back a second time refuses rather than looping",
      "same page marker twice" in refused(lambda: tool.what_has_arrived(stuck, "f9")))

# **THE FOLDER-BY-NAME LISTING GOES THROUGH THE SAME PAGER**, or a second folder
# of one name on page two reads as "there is exactly one" -- and tonight's file
# goes somewhere else from last night's, silently.
TWO_PAGES_OF_FOLDERS = [
    {"id": "wrong-1", "name": "amazon"},
    {"id": "wrong-2", "name": "amazon"},
]
doubled = FakeDrive(folders=TWO_PAGES_OF_FOLDERS, a_page=1)
check("A SECOND FOLDER OF THE SAME NAME ON A LATER PAGE IS STILL SEEN",
      "2 folders called" in refused(lambda: tool.folder_for(doubled, "az_orders", "root")))
check("and finding it took more than one request -- it was not on the first page",
      len(doubled.asked) > 1)

check("a folder Drive will not read refuses rather than reading as empty",
      "Drive refused" in refused(lambda: tool.what_has_arrived(FakeDrive(refuse_reads=True), "f9")))
check("and the refusal says what it was doing at the time",
      "what has arrived" in refused(lambda: tool.what_has_arrived(FakeDrive(refuse_reads=True), "f9")))

# ------------------------------------------- reading a file back out

# **THE ONE THING THIS DOOR COULD NOT DO.** What a run leaves for the next one
# has to be read again the following night, and a door that could only write
# would begin from nothing every time.
back = FakeDrive(contents=b"what the last run left")
got = answered(lambda: tool.bring_the_file_back(back, "file-77"))
check("a file is fetched back by its own id", "file-77" in (back.asked[0][1] or ""))
# From Google's own documentation: without `alt=media` Drive answers the RECORD
# describing the file, so a run would read its own memory as a paragraph about a
# file instead of the file.
check("and asked for as its contents, not as the record describing it",
      (back.asked[0][2] or {}).get("alt") == "media")
check("and the bytes come back exactly as they were put", got == b"what the last run left")

check("a file Drive will not hand over refuses",
      "Drive refused" in refused(lambda: tool.bring_the_file_back(FakeDrive(refuse_reads=True), "file-77")))
check("and the refusal says what it was doing at the time",
      "reading a file back" in refused(lambda: tool.bring_the_file_back(FakeDrive(refuse_reads=True), "f")))

# ------------------------------- named for what it is, not what was expected

# **THIS IS THE ONE PLACE A NAME AND A BODY MEET**, so it is the one place that
# can tell them apart. Eleven of his real files landed as a zip wearing an
# `.xlsx` name and nothing could open a single one of them.
import io as _io  # noqa: E402
import zipfile as _zip  # noqa: E402


def _a_zip_of(files):
    held = _io.BytesIO()
    with _zip.ZipFile(held, "w") as book:
        for name, body in files.items():
            book.writestr(name, body)
    return held.getvalue()


A_SPREADSHEET = _a_zip_of({"xl/workbook.xml": "<x/>"})
A_WRAPPER = _a_zip_of({"SP_ORDER_PAYMENT_2026-06-29.xlsx": A_SPREADSHEET})

wrapped = FakeDrive(folders=[{"id": "f1", "name": "me_payments"}])
told = []
answered(lambda: tool.a_door(wrapped, "root", told.append)(
    "me_payments", "meesho_me_payments_2026-06-29.zip", A_WRAPPER))
# The bytes that actually went up carry the file, wrapped in the multipart
# envelope -- so the spreadsheet is in there and the wrapper is not.
sent_up = b"".join(bytes(one[1] or b"") for one in wrapped.sent if one[0] == "one-request")
check("a wrapped file is unwrapped before it is put away",
      A_SPREADSHEET in sent_up and A_WRAPPER not in sent_up)
check("and it is put away named for what it now is",
      b"meesho_me_payments_2026-06-29.xlsx" in sent_up)
# **SAID OUT LOUD.** Silence is what hid eleven of his files for two months.
check("and the run is told it happened", any("zip" in one for one in told))

plain = FakeDrive(folders=[{"id": "f1", "name": "me_payments"}])
quiet = []
answered(lambda: tool.a_door(plain, "root", quiet.append)(
    "me_payments", "meesho_me_payments_2026-08-27.xlsx", A_SPREADSHEET))
plain_up = b"".join(bytes(one[1] or b"") for one in plain.sent if one[0] == "one-request")
check("an ordinary file is put away exactly as it came", A_SPREADSHEET in plain_up)
check("and nothing is said about it", not any("zip" in one for one in quiet))

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 90
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
