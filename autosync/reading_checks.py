"""Checks for reading what is new in the seller's folder.

**THE ONE THIS FILE EXISTS FOR: A FILE IS WRITTEN DOWN AS READ ONLY WHEN ITS
SALES HAVE ACTUALLY LANDED SOMEWHERE.** Written down any earlier -- before the
recording, in a batch at the end, or at all on a night when there is nowhere to
put a sale -- that file is never read again and everything in it is lost
silently. That is the exact hole D157's list of files was written to close, and
it would have been re-opened by the code that implements it.

**AND THE SECOND ONE: A NIGHT THAT READ NOTHING MUST NOT LOOK LIKE A NIGHT THAT
READ EVERYTHING.** Two nightly runs have already "succeeded" in eleven and
forty-seven seconds while doing nothing at all.

Run: python autosync/reading_checks.py
"""

import sys
import zipfile
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import orders as orders_reader  # noqa: E402
import reading as tool  # noqa: E402
import reports  # noqa: E402
import sales  # noqa: E402
import whats_new  # noqa: E402

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
    """Did this refuse? Answers the refusal, or None if it did not."""
    try:
        work()
        return None
    except Exception as wrong:  # noqa: BLE001
        return wrong


# ------------------------------------------------------------ files to read

MEESHO_HEADER = (
    "Sub Order No,SKU,Quantity,Order Date,Reason for Credit Entry,"
    "Supplier Discounted Price (Incl GST and Commision)"
)


def a_meesho_file(*rows):
    lines = [MEESHO_HEADER] + list(rows)
    return ("\n".join(lines) + "\n").encode("utf-8")


AMAZON_HEADER = "\t".join(
    ["amazon-order-id", "sku", "quantity", "purchase-date", "order-status", "item-price"]
)


def an_amazon_file(*rows):
    # **CARRIAGE-RETURN CARRIAGE-RETURN NEWLINE, the way Amazon really writes
    # one.** Read with ordinary line splitting this is 2n lines, half of them
    # empty.
    lines = [AMAZON_HEADER] + list(rows)
    return ("\r\r\n".join(lines) + "\r\r\n").encode("utf-8")


NS = ('xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')


def a_spreadsheet(sheets):
    """A real `.xlsx`: a zip of XML parts, written the way a platform writes one.

    **THE PART NAMES DELIBERATELY DO NOT FOLLOW THE SHEET ORDER**, the way his
    real Flipkart payments file's do not -- its first sheet is `sheet17.xml`.
    """
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        book = [f"<workbook {NS}><sheets>"]
        rels = ['<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for at, (name, rows) in enumerate(sheets, start=1):
            rid = f"rId{100 + at}"
            part = f"worksheets/sheet{90 - at}.xml"
            book.append(f'<sheet name="{name}" sheetId="{at}" r:id="{rid}"/>')
            rels.append(
                f'<Relationship Id="{rid}" Target="{part}" '
                'Type="http://schemas.openxmlformats.org/officeDocument/'
                'relationships/worksheet"/>'
            )
            body = []
            for number, cells in enumerate(rows, start=1):
                inside = "".join(
                    f'<c r="{chr(65 + n)}{number}" t="inlineStr"><is><t>{said}</t></is></c>'
                    for n, said in enumerate(cells)
                )
                body.append(f'<row r="{number}">{inside}</row>')
            z.writestr(
                "xl/" + part,
                f'<worksheet {NS}><dimension ref="A1"/><sheetData>'
                + "".join(body) + "</sheetData></worksheet>",
            )
        book.append("</sheets></workbook>")
        rels.append("</Relationships>")
        z.writestr("xl/workbook.xml", "".join(book))
        z.writestr("xl/_rels/workbook.xml.rels", "".join(rels))
    return out.getvalue()


FLIPKART_COLUMNS = ["order_id", "sku", "quantity", "order_date", "order_item_status"]


def a_flipkart_file(*rows):
    return a_spreadsheet([
        # **`Help` FIRST, exactly like his real file.** A reader that takes the
        # first sheet reports that the seller had no orders.
        ("Help", [["How to read this report"]]),
        ("Orders", [FLIPKART_COLUMNS] + [list(r) for r in rows]),
    ])


# --------------------------------------------------- what this says it can read

check("every report this says it can read is a report Kartaan actually has",
      all(one.report_id in reports.BY_ID for one in tool.WHAT_CAN_BE_READ))
check("and every column an orders report claims is a column the ledger has",
      all(c in sales.COLUMNS for c in tool.WHAT_ORDERS_KNOWS))
# **RETURNS, PAYMENTS AND CLAIMS ARE NOT IN THE LIST, and that is not an
# oversight.** Nothing anywhere knows what their columns mean, so a file of one
# read tonight would be written down as read and never seen again by the reader
# somebody writes next month.
check("nothing that cannot be turned into sales is listed as readable",
      set(tool.what_this_can_read()) == {"me_orders", "fk_orders", "az_orders"})
check("the report ids it can read are asked of it rather than worked out",
      tool.what_this_can_read() == tuple(o.report_id for o in tool.WHAT_CAN_BE_READ))


# ---------------------------------------------------------------- the harness


class Folder:
    """A seller's Drive, as far as the reading half can tell.

    Everything is recorded in the order it happened, so a file marked read
    before its sales were recorded is visible rather than merely wrong at the
    end.
    """

    def __init__(self, files=None, bodies=None, listing_throws=(),
                 recording_throws=(), no_ledger=False, into=None):
        self.files = files or {}
        self.bodies = bodies or {}
        self.events = []
        self.recorded = []
        self._listing_throws = set(listing_throws)
        self._recording_throws = set(recording_throws)
        self._no_ledger = no_ledger
        # **WHERE THE SALES ACTUALLY GO, when a check needs a real one.** Left
        # out, this harness only remembers that it was called -- which is enough
        # for every rule about MARKING a file read, and is exactly what made the
        # ordering fault invisible here for as long as it was.
        self._into = into

    def in_the_folder(self, report_id):
        self.events.append(f"listed {report_id}")
        if report_id in self._listing_throws:
            raise RuntimeError("Drive would not answer")
        return list(self.files.get(report_id, ()))

    def bring_it_back(self, file_id):
        self.events.append(f"fetched {file_id}")
        return self.bodies[file_id]

    def record(self, readings):
        for one in readings:
            if one.which in self._recording_throws:
                raise RuntimeError("the ledger would not take it")
            self.events.append(f"recorded {one.which}")
            self.recorded.append(one)
        if self._into is not None:
            self._into(readings)

    def go(self, already=()):
        return answered(lambda: tool.read_what_is_new(
            already_read=already,
            what_is_in_the_folder=self.in_the_folder,
            bring_it_back=self.bring_it_back,
            record_the_sales=None if self._no_ledger else self.record,
        ))


def a_file(which, name, size=100):
    return whats_new.InTheFolder(which=which, name=name, size=size)


ONE_MEESHO = a_meesho_file("SO-1,DJ 14,2,2026-08-01 10:00:00,SHIPPED,199")
TWO_MEESHO = a_meesho_file(
    "SO-1,DJ 14,2,2026-08-02 10:00:00,SHIPPED,199",
    "SO-2,DJ 15,1,2026-08-02 11:00:00,CANCELLED,99",
)


def one_night(**rest):
    return Folder(
        files={"me_orders": [a_file("id-1", "meesho_me_orders_2026-08-01.csv")]},
        bodies={"id-1": ONE_MEESHO},
        **rest,
    )


# ------------------------------------------------- one real file, end to end

night = one_night()
was = night.go()
check("a new file in the folder is fetched, read and recorded",
      was is not None and len(night.recorded) == 1)
# **NOTHING BELOW INDEXES INTO A LIST THAT MIGHT BE EMPTY.** A check that
# crashes is not a check answering, and a proving pass counts a crash as a fault
# that survived -- found by running one.
_one = night.recorded[0] if night.recorded else None
check("and what was recorded says which report it came from",
      _one is not None and _one.report == "me_orders")
check("AND THE DAY IT CARRIES IS THE FILE'S OWN DATA DATE, not tonight",
      _one is not None and _one.on == "2026-08-01")
check("and it carries Drive's own id, so two files of one day are two statements",
      _one is not None and _one.which == "id-1")
check("and it may only write the columns an orders report knows",
      _one is not None and _one.knows == tool.WHAT_ORDERS_KNOWS)
check("the sale in it was read", _one is not None and len(_one.sales) == 1)
check("and the file is now written down as read", was.files_read == ("id-1",))
check("and what it read is counted, not merely done",
      was.new_files == 1 and was.sales == 1 and len(was.read_tonight) == 1)

# **THE ORDER IS THE POINT.** Marked before the recording, a run that died
# between the two would lose the file for ever.
check("the file is recorded before anything says it has been read",
      night.events == ["listed me_orders", "listed fk_orders", "listed az_orders",
                       "fetched id-1", "recorded id-1"])

# ------------------------------------------- a file already read is not read again

again = one_night()
was = again.go(already=("id-1",))
check("a file already written down as read is not fetched a second time",
      "fetched id-1" not in again.events)
check("and nothing is recorded from it", again.recorded == [])
check("and it is counted as already read rather than as nothing",
      was is not None and was.already_read == 1 and was.new_files == 0)
check("and it stays in the record", was.files_read == ("id-1",))

# ------------------------------------------------ NOWHERE TO PUT A SALE

# **TODAY'S REAL STATE.** The seller's sales ledger does not exist: nothing
# creates the sheet and nothing supplies its id. A file opened tonight would have
# to be opened again anyway, and one written down as read would be lost.
nothing_yet = one_night(no_ledger=True)
was = nothing_yet.go()
check("WITH NOWHERE TO PUT A SALE, NO FILE IS OPENED", "fetched id-1" not in nothing_yet.events)
check("AND NO FILE IS WRITTEN DOWN AS READ", was is not None and was.files_read == ())
check("and the folder is still listed, so what is waiting is known",
      "listed me_orders" in nothing_yet.events)
check("and how many are waiting is counted", was.new_files == 1)
check("and it says in words that it read nothing, rather than printing noughts",
      "nowhere yet to put a sale" in was.says())
check("and it says how many are sitting there unread", "1 file(s) are sitting" in was.says())
check("and a night with nowhere to put a sale is not our own defect",
      was.is_a_defect is False)

# **THE WATCH: a night that read nothing must not read like a night that read
# everything.** Said as two sentences that cannot be confused for each other.
read_everything = one_night().go()
# **ASKED SO THAT COUNTS ALONE CANNOT SATISFY IT.** Two summaries of the same
# shape differing only in their numbers ARE confusable -- a night of noughts is
# what a night with nothing connected already produces. So the night that read
# nothing must not be reporting a count of files it read at all.
check("A NIGHT THAT READ NOTHING DOES NOT SAY WHAT A NIGHT THAT READ EVERYTHING SAYS",
      was.says() != read_everything.says()
      and "new file(s):" not in was.says()
      and "new file(s):" in read_everything.says())
check("and the night that read something says how many it read",
      "Read 1 of 1 new file(s)" in read_everything.says())

# **AND THE SAME AGAIN WITH NO FOLDER AT ALL**, which is what a run driven with
# no Drive looks like. It is not a failure and it is not silent.
none_at_all = answered(lambda: tool.read_what_is_new(already_read=("id-9",)))
check("a run given no folder at all changes nothing in the record",
      none_at_all is not None and none_at_all.files_read == ("id-9",))
check("and says that it was given no folder", "no folder to look in" in none_at_all.says())

# ------------------------------------- a file whose sales did not land is not marked

would_not_take = one_night(recording_throws=("id-1",))
was = would_not_take.go()
check("A FILE THE LEDGER WOULD NOT TAKE IS NOT WRITTEN DOWN AS READ",
      was is not None and was.files_read == ())
_why = was.could_not_read[0] if was and was.could_not_read else ""
check("and why is said by name, never as a count alone",
      was is not None and len(was.could_not_read) == 1 and "would not take it" in _why)
check("and the file it was about is named", "meesho_me_orders_2026-08-01.csv" in _why)
check("and one file the ledger refused is not our own defect", was.is_a_defect is False)

# **ONE BAD FILE MUST NEVER LOSE THE OTHERS.**
two_files = Folder(
    files={"me_orders": [a_file("id-1", "meesho_me_orders_2026-08-01.csv"),
                         a_file("id-2", "meesho_me_orders_2026-08-02.csv")]},
    bodies={"id-1": ONE_MEESHO, "id-2": TWO_MEESHO},
    recording_throws=("id-1",),
)
was = two_files.go()
check("a file that could not be recorded does not stop the next one",
      was is not None and was.files_read == ("id-2",))
check("and the good one's sales are all there", was.sales == 2)

# ----------------------------------------------- files that cannot be read at all

no_day = Folder(
    files={"me_orders": [a_file("id-1", "meesho_me_orders.csv")]},
    bodies={"id-1": ONE_MEESHO},
)
was = no_day.go()
check("A FILE WITH NO DAY IN ITS NAME IS REFUSED, NEVER DATED TONIGHT",
      was is not None and was.files_read == () and no_day.recorded == [])
check("and the refusal says why the day matters",
      "newer or older" in "  ".join(was.could_not_read))

a_page = Folder(
    files={"me_orders": [a_file("id-1", "meesho_me_orders_2026-08-01.csv")]},
    bodies={"id-1": b"<!doctype html><html>Please sign in</html>"},
)
was = a_page.go()
check("A PORTAL'S SIGN-IN PAGE IS NOT READ AS A REPORT", was is not None and was.files_read == ())
check("and it is called what it is rather than a file with no columns",
      "a-web-page" in "  ".join(was.could_not_read))

moved = Folder(
    files={"me_orders": [a_file("id-1", "meesho_me_orders_2026-08-01.csv")]},
    bodies={"id-1": b"Order,SKU,Qty\nSO-1,DJ 14,2\n"},
)
was = moved.go()
check("a file whose columns have moved is refused once, by name",
      was is not None and was.files_read == ()
      and "Sub Order No" in "  ".join(was.could_not_read))

# **AN EMPTY FILE IS THE THIRD THING: not new data, and not already done.**
came_empty = Folder(
    files={"me_orders": [a_file("id-1", "meesho_me_orders_2026-08-01.csv", size=0)]},
    bodies={"id-1": b""},
)
was = came_empty.go()
check("a file that arrived empty is not opened", "fetched id-1" not in came_empty.events)
check("and is not written down as read, so tomorrow's real file is still new",
      was is not None and was.files_read == ())
check("and is counted as arrived empty rather than as new",
      was.empty_files == 1 and was.new_files == 0)

# ------------------------------------------------------ the other two platforms

flipkart = Folder(
    files={"fk_orders": [a_file("fk-1", "flipkart_fk_orders_2026-08-03.xlsx")]},
    bodies={"fk-1": a_flipkart_file(
        ['OD-1', '"""SKU:DJ 14 Bahubali"""', "1", "2026-08-03", "APPROVED"],
    )},
)
was = flipkart.go()
check("A FLIPKART FILE IS READ FROM ITS `Orders` SHEET, NOT FROM `Help`",
      was is not None and was.sales == 1)
_fk = flipkart.recorded[0].sales[0] if flipkart.recorded and flipkart.recorded[0].sales else None
check("and its SKU comes out unwrapped, the way his listing spells it",
      _fk is not None and _fk.sku == "DJ 14 Bahubali")
check("and its money is left blank, because a Flipkart orders file has none",
      _fk is not None and _fk.gmv is None)

amazon = Folder(
    files={"az_orders": [a_file("az-1", "amazon_az_orders_2026-08-04.csv")]},
    bodies={"az-1": an_amazon_file(
        "\t".join(["407-1", "DJ 14", "1", "2026-08-04T10:00:00+05:30", "Shipped", "249"]),
    )},
)
was = amazon.go()
check("AN AMAZON FILE'S DOUBLED LINE ENDINGS DO NOT DOUBLE ITS ROWS",
      was is not None and was.sales == 1)
_az = amazon.recorded[0].sales[0] if amazon.recorded and amazon.recorded[0].sales else None
check("and its money is read", _az is not None and _az.gmv == "249")

# ---------------------------------------------- letting go of an id (D161)

gone = Folder(
    files={"me_orders": [a_file("id-2", "meesho_me_orders_2026-08-02.csv")],
           "fk_orders": [a_file("fk-1", "flipkart_fk_orders_2026-08-02.xlsx")],
           "az_orders": [a_file("az-1", "amazon_az_orders_2026-08-02.csv")]},
    bodies={"id-2": TWO_MEESHO},
)
was = gone.go(already=("id-1", "id-2", "fk-1", "az-1"))
check("AN ID IS LET GO OF WHEN ITS FILE HAS GONE FROM THE FOLDER",
      was is not None and was.let_go_of == ("id-1",))
check("and one whose file is still there is kept", "id-2" in was.files_read)
check("and how many were let go of is said even when nothing else happened",
      "1 id(s) let go of" in was.says())

# **THE COST OF THE WIDENED GUARD, WRITTEN DOWN RATHER THAN DISCOVERED.** The
# record is one flat list of ids and does not say which folder each came from,
# so an empty folder cannot be told from an empty folder that matters. While any
# one of the three is empty, NOTHING is ever let go of and the list only grows.
# That is the safe direction -- forgetting too much is a re-read, and a re-read
# puts old figures back over newer ones -- and it is said out loud every night.
one_short = Folder(
    files={"me_orders": [a_file("id-2", "meesho_me_orders_2026-08-02.csv")],
           "fk_orders": [], "az_orders": [a_file("az-1", "amazon_az_orders_2026-08-02.csv")]},
    bodies={"id-2": TWO_MEESHO},
)
was = one_short.go(already=("id-1", "id-2", "az-1"))
check("while any folder is empty the list only grows, and that is the safe way round",
      was is not None and was.let_go_of == () and "id-1" in was.files_read)
check("and the night says which folder stopped it rather than going quiet",
      "fk_orders" in was.says())

# **A FOLDER THAT COULD NOT BE LISTED LETS GO OF NOTHING, ANYWHERE.** This is
# D161's guard widened, and the widening is the whole point: with three folders,
# one failing while the others answer leaves a union that looks healthy, and
# every id belonging to the failed folder reads as a file somebody tidied away.
# **EVERY OTHER FOLDER HAS FILES IN IT, deliberately.** With one of them empty
# as well, the empty-folder guard below would stop the forgetting instead and
# this check would pass with the failed-listing guard switched off entirely --
# found by switching it off.
one_folder_down = Folder(
    files={"me_orders": [a_file("id-2", "meesho_me_orders_2026-08-02.csv")],
           "az_orders": [a_file("az-2", "amazon_az_orders_2026-08-02.csv")]},
    bodies={"id-2": TWO_MEESHO, "az-2": an_amazon_file(
        "	".join(["407-9", "DJ 14", "1", "2026-08-02T10:00:00+05:30", "Shipped", "50"]))},
    listing_throws=("fk_orders",),
)
was = one_folder_down.go(already=("id-1", "fk-9"))
check("ONE FOLDER THAT COULD NOT BE LISTED STOPS ALL FORGETTING",
      was is not None and was.let_go_of == ())
check("and every id is still remembered, including the failed folder's",
      sorted(was.files_read) == ["az-2", "fk-9", "id-1", "id-2"])
check("and it says nothing was let go of, and why",
      "could not be listed" in was.says())
check("AND A FOLDER NOBODY COULD LIST IS OUR OWN DEFECT", was.is_a_defect is True)
check("and the folders that did answer were still read", was.sales == 3)

# **A FOLDER THAT COMES BACK EMPTY IS NOT A FOLDER SOMEBODY EMPTIED**, and with
# three folders the other two would otherwise carry it straight past the guard.
one_folder_empty = Folder(
    files={"me_orders": [a_file("id-2", "meesho_me_orders_2026-08-02.csv")],
           "fk_orders": [], "az_orders": []},
    bodies={"id-2": TWO_MEESHO},
)
was = one_folder_empty.go(already=("id-1", "id-2", "fk-9"))
check("A FOLDER THAT CAME BACK EMPTY STOPS ALL FORGETTING TOO",
      was is not None and was.let_go_of == ())
check("and it names which folders came back empty",
      "fk_orders" in was.says() and "az_orders" in was.says())

# **AND AN EMPTY FOLDER ON A FIRST NIGHT IS ORDINARY.** Nothing is remembered, so
# there is nothing to refuse to forget, and saying so would be noise every night
# until the first file lands.
first_night = Folder(files={"me_orders": [], "fk_orders": [], "az_orders": []})
was = first_night.go()
check("an empty folder with nothing remembered is not reported as a refusal",
      was is not None and was.refused_to_forget == "")

# ------------- HIS CASE: THE FOURTH FILE ARRIVES AFTER THE FIFTH, THROUGH HERE

# 1st, 2nd, 3rd downloaded. The 4th fails. The 5th downloads. Later the 4th
# arrives. **The reason the record holds a list and not a date**, driven here
# through the real reading rather than through `whats_new` on its own.
FIRST_THREE_AND_FIFTH = [
    a_file("d-1", "meesho_me_orders_2026-09-01.csv"),
    a_file("d-2", "meesho_me_orders_2026-09-02.csv"),
    a_file("d-3", "meesho_me_orders_2026-09-03.csv"),
    a_file("d-5", "meesho_me_orders_2026-09-05.csv"),
]
THE_FOURTH = a_file("d-4", "meesho_me_orders_2026-09-04.csv")
BODIES = {
    "d-1": a_meesho_file("SO-1,DJ 14,1,2026-09-01 10:00:00,SHIPPED,100"),
    "d-2": a_meesho_file("SO-2,DJ 14,1,2026-09-02 10:00:00,SHIPPED,100"),
    "d-3": a_meesho_file("SO-3,DJ 14,1,2026-09-03 10:00:00,SHIPPED,100"),
    # **THE FIFTH CORRECTS THE FIRST SALE'S QUANTITY to 9.**
    "d-5": a_meesho_file("SO-1,DJ 14,9,2026-09-05 10:00:00,SHIPPED,100"),
    # **AND THE FOURTH, WHICH ARRIVES LATE, STILL SAYS 1.**
    "d-4": a_meesho_file("SO-1,DJ 14,1,2026-09-04 10:00:00,SHIPPED,100"),
}

first_four = Folder(files={"me_orders": list(FIRST_THREE_AND_FIFTH)}, bodies=BODIES)
was = first_four.go()
check("on the first night the four files that arrived are all read",
      was is not None and len(was.read_tonight) == 4)
check("and all four are written down as read",
      was.files_read == ("d-1", "d-2", "d-3", "d-5"))

late = Folder(files={"me_orders": FIRST_THREE_AND_FIFTH + [THE_FOURTH]}, bodies=BODIES)
was_late = late.go(already=was.files_read)
check("THE FOURTH FILE, ARRIVING AFTER THE FIFTH, IS READ ON THE NEXT NIGHT",
      was_late is not None and was_late.read_tonight == ("d-4",))
check("and the four already read are not fetched a second time",
      [e for e in late.events if e.startswith("fetched")] == ["fetched d-4"])
check("and all five are now written down as read",
      was_late.files_read == ("d-1", "d-2", "d-3", "d-4", "d-5"))

# **KEPT AS A DATE INSTEAD, THE FOURTH IS SKIPPED FOR EVER AND SILENTLY.** Shown
# rather than asserted, so this fails the day somebody makes it a date.
check("keyed by the last date read instead, the fourth would never have been read",
      THE_FOURTH.name < max(one.name for one in FIRST_THREE_AND_FIFTH))

# ---- AND THE LATE FOURTH'S OLDER FIGURES MUST NOT WIN, DRIVEN AS THE JOB RUNS

# **THIS CHECK USED TO POOL BOTH NIGHTS' READINGS INTO ONE `ledger.plan` CALL
# AGAINST AN EMPTY SHEET, and it was green.** What that proved was `plan`'s own
# sort -- already committed, already true -- and nothing whatever about the chain
# these files build, because **the job never hands `plan` more than one reading.**
# `read_what_is_new` calls `record_the_sales` with ONE file at a time (that is
# what makes the marking safe), and the writing half reads the sheet back and
# plans again for each one, so the sort is handed a list of one every time. A
# check whose green answer does not mean its own name is worse than no check
# (D175), and this is that shape one level up.
#
# So it is driven below through the real recorder, a real `LedgerDoor`, and a
# sheet that actually keeps what it was written.

import ledger  # noqa: E402
import ledger_door  # noqa: E402
import ledger_sheet  # noqa: E402


class PretendLedgerSheet:
    """A Google Sheets that KEEPS WHAT IT WAS TOLD.

    A stand-in that answered every write with `{}` would leave every plan looking
    perfectly right and the sheet empty -- which is exactly how a chain that
    plans against a stale reading passes. So `:append` really appends, and
    `values:batchUpdate` really overwrites the row it names, and `qty_for` reads
    the answer back out of the cells the seller would actually see.
    """

    def __init__(self):
        self.rows = [list(sales.COLUMNS)]

    def __call__(self, method, path, query=None, body=None):
        if method == "GET" and "/values/" not in path:
            return {"sheets": [{"properties": {"title": sales.THE_TAB}}]}
        if method == "GET":
            return {"values": [list(r) for r in self.rows]}
        if ":append" in path:
            self.rows += [list(r) for r in (body or {}).get("values", ())]
            return {}
        if "values:batchUpdate" in path:
            for one in (body or {}).get("data", ()):
                # `orders!A7:AS7` -- the row number is the plan's own, and a plan
                # built against a stale reading names the wrong one.
                at = int(one["range"].split("!A")[1].split(":")[0])
                self.rows[at - 1] = list(one["values"][0])
            return {}
        return {}

    def qty_for(self, name):
        return self.cell_for(name, "qty")

    def cell_for(self, name, column):
        """One cell of one sale, read back out of what the seller would see.

        **READ BACK OUT OF THE SHEET, never off the plan.** A plan says what it
        meant to write; this says what is actually in the row -- which is the
        only place a column that is declared and never filled shows up as blank.
        """
        at_id = sales.COLUMNS.index("id")
        at = sales.COLUMNS.index(column)
        for row in self.rows[1:]:
            if len(row) > at and row[at_id] == name:
                return row[at]
        return None


def a_sales_ledger(the_sheet=None):
    """The REAL writing half, writing into a sheet that keeps things.

    **THIS USED TO BE THREE LINES THAT LOOKED LIKE `ledger_sheet.recording_into`
    AND WERE NOT IT.** They were written out here rather than imported, on the
    reasoning that the writing half could not be committed until D157's four
    date-marker columns exist. That reasoning is gone: the writing half is in this
    batch and REFUSES to run until those columns exist, so it can land.

    **AND THE COPY WAS ALREADY WRONG BY THEN, WHICH IS THE POINT.** The real one
    makes ONE memory of what the night has decided and hands it to every file,
    which is the whole of how D150's rule 3 fires across a one-file-at-a-time
    handover. The three lines here made a fresh empty one per file, so the tie
    could never be seen -- **a copy of the code under check that had quietly
    stopped being a copy.** Imported now, so it cannot drift again.

    **HANDED A SHEET, THIS IS A SECOND NIGHT AGAINST THE SAME LEDGER.** What the
    night has decided is made once per night by the writing half, and a real
    second night is a new run that remembers none of it. A check that reused one
    recorder across two nights would be handing tomorrow what only tonight knew.
    """
    keeping = the_sheet if the_sheet is not None else PretendLedgerSheet()
    door = ledger_door.LedgerDoor(keeping, "the-sellers-own-ledger")
    told = []
    return keeping, ledger_sheet.recording_into(door, told.append), told


THE_SALE = "meesho::SO-1::DJ 14"

# **THE HALF THAT CAN BE FIXED: BOTH FILES ARE NEW IN THE ONE RUN.** The fourth
# failed on the night it was due and both it and the fifth are sitting there when
# the next run looks. Drive answers a listing in its own order, and **the figure
# the seller ends up with must not depend on that order.**
newest_first, into_the_ledger, _ = a_sales_ledger()
one_run = Folder(
    files={"me_orders": FIRST_THREE_AND_FIFTH + [THE_FOURTH]},
    bodies=BODIES,
    into=into_the_ledger,
)
was_one_run = one_run.go()
check("all five files are read in the one run",
      was_one_run is not None and len(was_one_run.read_tonight) == 5)
check("THE FOURTH'S OLDER FIGURE DOES NOT OVERWRITE THE FIFTH'S",
      newest_first.qty_for(THE_SALE) == "9")

# ---------------------------------- THE ROW SAYS WHICH DAY'S FILE WROTE IT (D157)

# **THE COLUMN EXISTING IS NOT THE COLUMN BEING FILLED, and for two days those
# two were read as one thing.** The ERP landed `ordersOn` in its column list on
# 2026-09-06, every refusal built around the four lifted itself the same day --
# and nothing anywhere ever put a date in one. Every row written was still a row
# that could not say which day's file produced it.
#
# **READ OUT OF THE SHEET, NOT OUT OF THE PLAN.** A plan that meant to write it
# and a sheet that holds it are the same sentence and different facts.
check("A WRITTEN ROW SAYS WHICH DAY'S ORDERS FILE PRODUCED IT",
      newest_first.cell_for(THE_SALE, "ordersOn") == "2026-09-05")
# **THE NEWEST FILE'S DAY, not the first one's and not tonight's.** Five files
# touched this sale and the fifth is the one whose figures are standing, so the
# marker has to be the fifth's -- a marker left at the oldest file's day is worse
# than none, because it says an older statement is what is in the row.
check("and it is the day of the file whose figures are standing, not the first one's",
      newest_first.cell_for(THE_SALE, "ordersOn")
      == max(one.name.split("_")[-1].split(".")[0] for one in FIRST_THREE_AND_FIFTH))
# **AND NOTHING INVENTS THE OTHER THREE.** No returns, payments or claims file is
# read by anything, so a date in one of those columns would be a date nobody
# measured. **Blank is honest; a wrong date is the fault D157 exists to prevent.**
check("and the three markers no file has been read for stay blank, not guessed",
      all(newest_first.cell_for(THE_SALE, one) == ""
          for one in ("returnsOn", "paymentsOn", "claimsOn")))

# **AND LISTED THE OTHER WAY ROUND IT MUST SAY THE SAME THING**, or the answer is
# luck. This is the one that tells an ordering fix from a coincidence: with the
# files handed over one at a time in Drive's order, one of these two answers 9
# and the other answers 1, and neither is the sheet knowing anything.
oldest_first, other_ledger, _ = a_sales_ledger()
the_other_way = Folder(
    files={"me_orders": FIRST_THREE_AND_FIFTH[:3] + [THE_FOURTH, FIRST_THREE_AND_FIFTH[3]]},
    bodies=BODIES,
    into=other_ledger,
)
was_other_way = the_other_way.go()
check("and the same five files listed the other way round are all read",
      was_other_way is not None and len(was_other_way.read_tonight) == 5)
check("AND THE ORDER DRIVE LISTED THEM IN DECIDES NOTHING",
      oldest_first.qty_for(THE_SALE) == newest_first.qty_for(THE_SALE) == "9")

check("and the sales the other files brought are all there",
      {r[sales.COLUMNS.index("id")] for r in newest_first.rows[1:]}
      == {THE_SALE, "meesho::SO-2::DJ 14", "meesho::SO-3::DJ 14"})
check("and it decided that on the files' own days, not on the night they arrived",
      sorted(r.on for r in one_run.recorded)
      == ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05"])


# **AND THE ID DRIVE GAVE THE FILE DECIDES NOTHING EITHER.** The ids above are
# written `d-1` to `d-5` so that a check about days can be read at all -- and
# that made them sort in the same order as the days, so a sort keyed on Drive's
# id passed every check above. **A real Drive id is an opaque string with no
# order in it.** So the same two files are driven once more with ids whose
# alphabetical order is the exact reverse of their days, and listed in that
# order too: keyed on the id, the fifth would be applied first and the fourth's
# 1 would stand. Found by putting that fault back and watching nothing go red.
opaque, opaque_ledger, _ = a_sales_ledger()
by_id_it_is_backwards = Folder(
    files={"me_orders": [a_file("a-1c", "meesho_me_orders_2026-09-05.csv"),
                         a_file("z-9f", "meesho_me_orders_2026-09-04.csv")]},
    bodies={"a-1c": BODIES["d-5"], "z-9f": BODIES["d-4"]},
    into=opaque_ledger,
)
was_opaque = by_id_it_is_backwards.go()
check("both files are read whatever their ids look like",
      was_opaque is not None and len(was_opaque.read_tonight) == 2)
check("AND THE ID DRIVE GAVE THE FILE DECIDES NOTHING EITHER",
      opaque.qty_for(THE_SALE) == "9")

# ---- THREE FOLDERS, FOUR DIFFERENT DAYS. **THE FIXTURE THAT WAS MISSING.**
#
# **EVERY ORDERING FIXTURE ABOVE USES ONE FOLDER, AND EVERY MULTI-FOLDER FIXTURE
# IN THIS FILE PUTS EVERY FILE ON ONE DAY.** So nothing anywhere drove two folders
# with files on different days -- and inside one folder every landed name is
# `meesho_me_orders_<date>`, one fixed prefix, so **sorting on the file's NAME and
# sorting on its DAY are the same string in every fixture above.** A sort keyed on
# the name passed all of them.
#
# Measured rather than argued (landed names are `{platform}_{report}_{date}`):
#
#     by DAY :  meesho 09-01, flipkart 09-03, amazon 09-05, meesho 09-06
#     by NAME:  amazon 09-05, flipkart 09-03, meesho 09-01, meesho 09-06
#
# Four files, four days, three folders, and **four different orderings** -- by
# day, by name, by folder-then-day, and by Drive's own id. Only one of them is
# the rule.
THREE_FOLDERS = {
    # Listed in each folder in an order that is not the day order either, so the
    # fixture cannot pass by having been handed things already sorted.
    "me_orders": [a_file("b-6", "meesho_me_orders_2026-09-06.csv"),
                  a_file("q-1", "meesho_me_orders_2026-09-01.csv")],
    "fk_orders": [a_file("z-3", "flipkart_fk_orders_2026-09-03.xlsx")],
    "az_orders": [a_file("c-5", "amazon_az_orders_2026-09-05.csv")],
}
ACROSS_FOLDERS = {
    "q-1": a_meesho_file("SO-A,DJ 14,1,2026-09-01 10:00:00,SHIPPED,100"),
    "b-6": a_meesho_file("SO-A,DJ 14,6,2026-09-06 10:00:00,SHIPPED,100"),
    "z-3": a_flipkart_file(["FK-1", "DJ 15", "1", "2026-09-03", "APPROVED"]),
    "c-5": an_amazon_file(
        "	".join(["AZ-1", "DJ 16", "1", "2026-09-05T10:00:00+05:30", "Shipped", "249"])),
}
BY_DAY = ("q-1", "z-3", "c-5", "b-6")

everywhere, into_everywhere, _ = a_sales_ledger()
across = Folder(files=THREE_FOLDERS, bodies=ACROSS_FOLDERS, into=into_everywhere)
was_across = across.go()
check("all four files, from all three folders, are read",
      was_across is not None and len(was_across.read_tonight) == 4)
check("EVERY FOLDER'S FILES ARE HANDED OVER AS ONE LIST, OLDEST DAY FIRST",
      tuple(r.which for r in across.recorded) == BY_DAY)

# **AND THE THREE WRONG ORDERINGS ARE SHOWN TO BE DIFFERENT ORDERINGS**, rather
# than a reader being asked to take it on trust that they are the same. Each of
# these is a sort somebody could reasonably write, and each gives a different
# answer from the one above.
_all = [(how, one) for how in tool.WHAT_CAN_BE_READ
        for one in THREE_FOLDERS.get(how.report_id, ())]
check("sorting on the file's NAME is NOT the same ordering, across platforms",
      tuple(one.which for _, one in sorted(_all, key=lambda p: p[1].name)) != BY_DAY)
check("nor is sorting each folder on its own and then by day",
      tuple(one.which for how, one in
            sorted(_all, key=lambda p: (p[0].report_id, p[1].name))) != BY_DAY)
check("nor is sorting on the id Drive happened to give the file",
      tuple(one.which for _, one in sorted(_all, key=lambda p: p[1].which)) != BY_DAY)

# **WHAT THE ORDER IS FOR.** Within one platform it decides a figure outright:
# the sixth's 6 must stand over the first's 1 however the folders were listed.
check("and within a platform the newest day's figure is the one standing",
      everywhere.qty_for("meesho::SO-A::DJ 14") == "6")
check("while the other platforms' sales are all there beside it",
      {r[sales.COLUMNS.index("id")] for r in everywhere.rows[1:]}
      == {"meesho::SO-A::DJ 14", "flipkart::FK-1::DJ 15", "amazon::AZ-1::DJ 16"})

# **AND THIS IS WHERE THE OLD NOTE WAS WRONG, said plainly rather than left.**
# It recorded two injections as not-faults, and the reason it gave for the first
# was measurably false:
#
#   > sorting on the file's NAME instead of its day: this package names a landed
#   > file itself, from the data date, so for every file that can reach here the
#   > two orders are the same string.
#
# **They are the same string only INSIDE ONE FOLDER**, where the prefix never
# changes. Across platforms the prefix is the platform's own name and the two
# orderings come apart, which is what the check above measures.
#
# What is true is the OTHER reason, and it covers both injections at once: a sale
# is named `platform::orderId::sku` and each orders report carries exactly one
# platform (`reports.py`), so **no figure this package can produce today changes
# under either wrong ordering** -- two platforms cannot write the same row. The
# handover ORDER does change, which is why it is checked directly above rather
# than through a figure that cannot feel it.
#
# **AND THAT PROTECTION HAS A DATE ON IT.** It ends the day a second report of ONE
# platform can be read -- returns and payments, same platform, different report,
# different folder. Then `meesho_me_orders_2026-09-05` sorts before
# `meesho_me_returns_2026-09-04` by name and after it by day, both write the same
# row, and the name sort is simply wrong.

# ---- HIS RE-FETCH-BY-HAND CASE: TWO FILES, ONE REPORT, ONE DAY (D110, D150 r3)
#
# **A DAY FETCHED AGAIN LANDS AS A SECOND FILE UNDER THE SAME NAME**, so two files
# of one report and one data date is not a curiosity -- it is the thing he does by
# hand. D150 rule 3: keep what is there, REPORT the disagreement, never a silent
# pick.
#
# **IT COULD NOT FIRE, AND THE CODE SAID IT COULD.** `plan` decides the rule in a
# memory that was its own, and a sale lands ONE FILE AT A TIME -- so the memory
# was empty on every call, the two files never met, and **which figure the seller
# ended up with was settled by which Drive id sorted higher, silently.** Measured:
# both listing orders answered `1`, and nought disagreements were reported either
# way. Driven here end to end, through the real reading and the real writing half.
SAME_DAY = {
    "fetched-first": a_meesho_file("SO-1,DJ 14,9,2026-09-05 10:00:00,SHIPPED,100"),
    "fetched-again": a_meesho_file("SO-1,DJ 14,1,2026-09-05 10:00:00,SHIPPED,100"),
}
SAME_DAY_FILES = [a_file("fetched-first", "meesho_me_orders_2026-09-05.csv"),
                  a_file("fetched-again", "meesho_me_orders_2026-09-05.csv")]


def a_day_fetched_twice(listed):
    sheet_of, into, told = a_sales_ledger()
    night = Folder(files={"me_orders": list(listed)}, bodies=SAME_DAY, into=into)
    was = night.go()
    return (was, night, sheet_of.qty_for(THE_SALE),
            [one for one in told if "DISAGREEMENT" in one])


# **WHAT THE RULE PROMISES IS NOT WHICH FIGURE SURVIVES.** It promises that the
# second claim does not silently overwrite the first and that the clash is said
# out loud. Which file speaks first is settled by Drive's id, deterministically
# (`_oldest_first` breaks a same-day tie on it), and that is checked as what it
# is rather than dressed up as a judgement about the figures.
WHAT_EACH_SAID = {"fetched-first": "9", "fetched-again": "1"}

was_tie, tie_night, qty_tie, told_tie = a_day_fetched_twice(SAME_DAY_FILES)
check("both files of the same day are read, because both are new",
      was_tie is not None and len(was_tie.read_tonight) == 2)
# **NOTHING BELOW INDEXES INTO A LIST THAT COULD BE EMPTY.** A check that CRASHES
# is not a check answering: the file dies where it stands, prints no count, and
# says nothing at all about everything under it. Found by a reviewer, who made
# the reading refuse and watched this line throw `IndexError` instead of going
# red -- taking the D180 check below down with it, unread.
_tie_first = tie_night.recorded[0].which if tie_night.recorded else None
check("TWO FILES OF ONE REPORT AND ONE DAY: WHAT THE FIRST ONE WROTE IS KEPT",
      _tie_first is not None and qty_tie == WHAT_EACH_SAID[_tie_first])
check("AND THE DISAGREEMENT IS REPORTED -- never a silent pick (D150 rule 3)",
      len(told_tie) == 1)
check("and the report names both files, so somebody can go and answer it",
      told_tie and "fetched-first" in told_tie[0] and "fetched-again" in told_tie[0])
check("and it names the sale and the column that disagree",
      told_tie and THE_SALE in told_tie[0] and "qty" in told_tie[0])

# **AND THE ORDER DRIVE LISTED THEM IN CHANGES NEITHER ANSWER**, which is what
# tells a rule from a coin toss.
_, back_night, qty_back, told_back = a_day_fetched_twice(list(reversed(SAME_DAY_FILES)))
check("listed the other way round it keeps the same figure and reports the same tie",
      qty_back == qty_tie and len(told_back) == len(told_tie)
      and _tie_first is not None and back_night.recorded
      and back_night.recorded[0].which == _tie_first)

# **BOTH FILES ARE STILL WRITTEN DOWN AS READ.** A reported disagreement is not a
# file that failed: it was opened, understood, and its sales reached the sheet.
# Left unmarked, it would be read again every night for ever and report the same
# tie every night.
check("and both files are written down as read, tie or no tie",
      was_tie is not None and was_tie.files_read == ("fetched-again", "fetched-first"))


# **THE HALF THAT COULD NOT BE FIXED HERE UNTIL 2026-09-08 -- D180, NOW CLOSED.**
#
# When the fourth arrives on a LATER night, the fifth's 9 is already in the sheet
# and the fourth is the only reading this run has. `ledger.plan` decides newer
# from older by the data date a READING carries, and **a row in the sheet carried
# no date at all** -- the ledger has 49 columns, four of which are supposed to
# say which day's file last wrote each figure. So the fourth's 1 went over the
# fifth's 9 and nothing anywhere could tell that it should not have.
#
# **The check below asserted the WRONG answer on purpose from 2026-09-04**, so
# that it would go red the day the fix landed rather than waiting for anybody to
# remember. **It went red on 2026-09-08 and this is it turned round.**
#
# **THE COLUMNS LANDING WAS NOT THE FIX.** The ERP put the four names in its
# column list on 2026-09-06 and this check stayed green for two more days,
# because a column nothing fills and a column that does not exist are the same
# column to a run reading it back.
across_nights, over_two_nights, _ = a_sales_ledger()
night_one = Folder(files={"me_orders": list(FIRST_THREE_AND_FIFTH)},
                   bodies=BODIES, into=over_two_nights)
was_first = night_one.go()
check("on the first night the fifth's correction lands in the sheet",
      was_first is not None and across_nights.qty_for(THE_SALE) == "9")

check("and the row says which day's file wrote that correction",
      across_nights.cell_for(THE_SALE, "ordersOn") == "2026-09-05")

# **A NEW NIGHT IS A NEW RUN**, and it remembers nothing of what last night
# decided -- only what is written in the sheet. **That is why the marker had to
# be in the sheet: it is the run's only memory of which day's file wrote a
# figure, and until 2026-09-08 nothing put one there.**
_, the_next_night, _across_told = a_sales_ledger(across_nights)
night_two = Folder(files={"me_orders": FIRST_THREE_AND_FIFTH + [THE_FOURTH]},
                   bodies=BODIES, into=the_next_night)
was_second = night_two.go(already=was_first.files_read)
check("and on the next night the fourth is the only file read",
      was_second is not None and was_second.read_tonight == ("d-4",))
# **THIS CHECK ASSERTED THE WRONG ANSWER ON PURPOSE FROM 2026-09-04 TO
# 2026-09-08, and it is the reason it was written that way.** It said the older
# file still wins, so that it would go red the day the fix landed rather than
# waiting for anybody to remember. **It went red on 2026-09-08 and this is it
# turned round.**
#
# **THE COLUMNS LANDING WAS NOT THE FIX, and that is worth writing down here
# because it was believed twice.** The ERP put the four names in its column list
# on 2026-09-06 and this check stayed green, because a column nothing fills and a
# column that does not exist are the same column to a run reading it back.
check("ACROSS TWO NIGHTS THE FOURTH'S OLDER FIGURE NO LONGER WINS -- D180 CLOSED",
      across_nights.qty_for(THE_SALE) == "9")
check("and the marker is not rolled backwards to the older file's day either",
      across_nights.cell_for(THE_SALE, "ordersOn") == "2026-09-05")
# **AND IT IS SAID OUT LOUD, NEVER QUIETLY DROPPED.** A by-hand backfill (D110)
# is a deliberately old file somebody fetched on purpose; a night that ignored it
# in silence would look exactly like a night that applied it.
_told_second = [one for one in _across_told if "OLDER THAN THE ROW" in one]
check("AND THE NIGHT SAYS THE OLDER FILE WAS LEFT ALONE, rather than dropping it quietly",
      len(_told_second) == 1)
check("and what it says names the sale, the report and both days",
      len(_told_second) == 1 and THE_SALE in _told_second[0]
      and "2026-09-04" in _told_second[0] and "2026-09-05" in _told_second[0])

# ------- A READER THAT STOPPED FILLING ITS MARKER, DRIVEN THROUGH A WHOLE NIGHT
#
# **THE CLAIM "NOTHING IS LOST" IS MADE IN FOUR PLACES AND WAS DRIVEN IN NONE.**
# `ledger.Reading` refuses a reading that names a date marker and carries no
# date; three files, `ledger.py`, `ledger_checks.py` and the night's own refusal
# text, all say that `read_what_is_new` then names the file and leaves it for
# tomorrow. **An independent reviewer traced it by eye and said so: in a project
# whose standard is "driven, not assumed", that was the one new claim taken on
# trust.** This drives it.
_the_real_reader = orders_reader.read_orders


def _a_reader_that_forgets_the_marker(rows, platform, data_date=None):
    """`read_orders` with the marker assignment taken out, and nothing else."""
    return _the_real_reader(rows, platform)


orders_reader.read_orders = _a_reader_that_forgets_the_marker
_lost, _lost_ledger, _ = a_sales_ledger()
_lost_night = Folder(files={"me_orders": [a_file("m-1", "meesho_me_orders_2026-09-01.csv")]},
                     bodies={"m-1": BODIES["d-1"]}, into=_lost_ledger)
_was_lost = _lost_night.go()
orders_reader.read_orders = _the_real_reader
assert orders_reader.read_orders is _the_real_reader

check("A READER THAT STOPPED FILLING ITS MARKER HAS ITS FILE REFUSED",
      _was_lost is not None and len(_was_lost.the_ledger_refused) == 1)
check("AND THE FILE IS NOT WRITTEN DOWN AS READ -- it is opened again tomorrow",
      _was_lost is not None and _was_lost.read_tonight == ()
      and _was_lost.files_read == ())
check("and not one sale reached the sheet",
      _lost.qty_for("meesho::SO-1::DJ 14") is None)
check("and the file is named, so somebody knows which one to go and look at",
      _was_lost is not None and "meesho_me_orders_2026-09-01.csv" in
      _was_lost.the_ledger_refused[0])
check("and the reason names the marker that was missing",
      _was_lost is not None and "ordersOn" in _was_lost.the_ledger_refused[0])
# **AND THE NIGHT IS NOT GREEN.** Counted among the platform's unreadable files,
# a night where our own rule refused every file would report perfectly well while
# the seller's folder filled up for ever -- Golden Rule 29.
check("AND THE NIGHT IS OUR OWN DEFECT, not a quiet count of the platform's",
      _was_lost is not None and _was_lost.is_a_defect
      and _was_lost.could_not_read == ())
check("and the night says out loud that it was Kartaan's ledger that refused",
      _was_lost is not None and "KARTAAN'S OWN LEDGER REFUSED A FILE" in _was_lost.says())

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 106
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
