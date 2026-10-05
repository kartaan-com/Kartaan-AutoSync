"""Checks for how each listing is doing: the readers, the record's writer, and the night that joins them (plan job 86 part A).

**EVERY FIGURE IN HERE IS MADE UP.** The columns are the ones the working reference read off his real files (`process.py` in
the old dashboard); no value of his is written here.

Run: python autosync/views_checks.py
"""

import sys
from io import BytesIO
from pathlib import Path
import zipfile
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))

import firestore  # noqa: E402
import firestore_door  # noqa: E402
import reading  # noqa: E402
import reports  # noqa: E402
import table  # noqa: E402
import views as tool  # noqa: E402
import whats_new  # noqa: E402

ran = 0
failures = []
THREW = []


def answered(work):
    try:
        return work()
    except Exception as wrong:  # noqa: BLE001
        THREW.append(repr(wrong))
        return None


def check(name, passed):
    global ran
    ran += 1
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
    if not passed:
        failures.append(name)


def refused(work, kind=Exception):
    try:
        work()
    except kind:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


def csv(*lines):
    return ("\n".join(lines) + "\n").encode("utf-8")


FK_VIEWS_HEADER = "Impression Date,SKU Id,Product Views,Product Clicks,Sales,Revenue"
FSN_HEADER = "Campaign ID,Campaign Name,Sku Id,Product Name,Views,Clicks,Direct Units Sold,Indirect Units Sold,Total Revenue (Rs.),Ad Spend,ROI"
ME_HEADER = "Date,Campaign ID,Campaign Name,Catalog ID,Catalog Name,Spend,Revenue,Orders,Views,Clicks,CPC"


def read(report, body, header_row=1, day=None):
    return tool.read_views(report, table.read(body, header_row=header_row), day)


# ------------------------------------------------------------ Flipkart traffic

fk = answered(lambda: read("fk_views", csv(
    FK_VIEWS_HEADER,
    "2026-10-04,SKU-A,100,10,2,398.5",
    "2026-10-05,SKU-A,80,8,1,199",
    "2026-10-04,SKU-B,5,0,0,0",
)))
check("a traffic file gives each listing's figures day by day",
      fk is not None and fk.records["SKU-A"]["2026-10-05"] == {"views": 80, "clicks": 8, "sales": 1, "revenue": 199.0})
check("and a listing that sold nothing says nought, because the file said nought",
      fk is not None and fk.records["SKU-B"]["2026-10-04"]["sales"] == 0)
check("the platform is Flipkart and the report is named", fk is not None and fk.platform == "flipkart" and fk.report == "fk_views")
check("counts are whole numbers and money is money",
      fk is not None and isinstance(fk.records["SKU-A"]["2026-10-04"]["views"], int)
      and isinstance(fk.records["SKU-A"]["2026-10-04"]["revenue"], float))

blank = answered(lambda: read("fk_views", csv(FK_VIEWS_HEADER, "2026-10-04,SKU-A,100,,2,")))
check("A BLANK IS LEFT OUT OF THE DAY, NEVER WRITTEN AS NOUGHT",
      blank is not None and blank.records["SKU-A"]["2026-10-04"] == {"views": 100, "sales": 2})

twice = answered(lambda: read("fk_views", csv(FK_VIEWS_HEADER, "2026-10-04,SKU-A,100,10,2,10", "2026-10-04,SKU-A,50,5,1,5.25")))
check("two rows for one listing and day are added together",
      twice is not None and twice.records["SKU-A"]["2026-10-04"] == {"views": 150, "clicks": 15, "sales": 3, "revenue": 15.25})

wrapped = answered(lambda: read("fk_views", csv(FK_VIEWS_HEADER, '2026-10-04,"""SKU:DJ 14",3,0,0,0')))
check("a listing wrapped the way Flipkart wraps it in orders is unwrapped",
      wrapped is not None and "DJ 14" in wrapped.records)

bad = answered(lambda: read("fk_views", csv(
    FK_VIEWS_HEADER, "04-10-2026,SKU-A,1,1,1,1", "2026-10-04,SKU-B,x,1,1,1", "2026-10-04,SKU-C,1.5,1,1,1",
    "2026-10-04,SKU/D,1,1,1,1", "2026-10-04,,1,1,1,1", "2026-10-04,SKU-E,-3,1,1,1", "2026-10-04,SKU-F,9,1,1,1",
)))
check("a day not written year-month-day, a word for a figure, half a view, a slash in the name, no listing, and a negative are each refused by name",
      bad is not None and len(bad.not_read) == 6 and set(bad.records) == {"SKU-F"})
check("and the good row beside them is still read", bad is not None and bad.records["SKU-F"]["2026-10-04"]["views"] == 9)
check("a row is named by its line in the file", bad is not None and bad.not_read[0].startswith("line 2:"))

check("a file whose traffic column has moved stops, naming the columns it does have",
      refused(lambda: read("fk_views", csv("Impression Date,SKU Id,Views,Product Clicks,Sales,Revenue", "2026-10-04,A,1,1,1,1")),
              table.CannotRead))
check("a file with a column twice stops rather than taking the first",
      refused(lambda: read("fk_views", csv(FK_VIEWS_HEADER + ",Sales", "2026-10-04,A,1,1,1,1,1")), table.CannotRead))
check("a report it does not know is refused", refused(lambda: tool.way_for("zz"), table.CannotRead))

# ------------------------------------------------------------ Flipkart ads by product

FSN = csv("Start Time, 2026-06-18 00:00:00", "End Time, 2026-06-18 23:59:59", FSN_HEADER,
          "c1,Camp,SKU-A,Name,100,5,1,2,300,50.5,6", "c2,Camp 2,SKU-A,Name,10,1,0,1,10,5,2", "c1,Camp,SKU-B,Name,7,0,0,0,0,1.25,0")
check("the day of the ads-by-product file is on its first line", tool.day_in_ads_header(FSN) == "2026-06-18")
check("and a first line that is not a start time gives nothing", tool.day_in_ads_header(csv("Date, 2026-06-18")) is None)
fsn = answered(lambda: read("fk_ads_fsn", FSN, header_row=3, day="2026-06-18"))
check("a listing in two campaigns has its ad figures added",
      fsn is not None and fsn.records["SKU-A"]["2026-06-18"] == {"adViews": 110, "adClicks": 6, "adSpend": 55.5, "adSales": 4})
check("an ad unit count is direct plus indirect units", fsn is not None and fsn.records["SKU-A"]["2026-06-18"]["adSales"] == 4)
check("and it says nothing of the traffic fields", fsn is not None and "views" not in fsn.records["SKU-A"]["2026-06-18"])
check("a file with no day given is refused rather than dated today",
      refused(lambda: read("fk_ads_fsn", FSN, header_row=3), table.CannotRead))

# ------------------------------------------------------------ Meesho ads by catalogue

me = answered(lambda: read("me_ads_catalog", csv(
    ME_HEADER, "2026-10-04,1,Camp,CAT1,Name,100.5,900,3,2000,40,2.5", "2026-10-05,1,Camp,CAT1,Name,10,0,0,100,1,10")))
check("a catalogue's ad figures are read day by day under the catalogue's id",
      me is not None and me.records["CAT1"]["2026-10-04"] == {"adViews": 2000, "adClicks": 40, "adSpend": 100.5, "adSales": 3})
check("Meesho is the platform", me is not None and me.platform == "meesho")
REAL_ME_HEADER = ("Date,Campaign ID,Campaign Name,Catalog ID,Category,Catalog Status,Spend,Revenue,Orders,Views,Clicks,CPC,"
                  "Conversion %,Delivered ROI,Ad Spend Per Order,Current Performance,Avg Rating,Selected Min ROI")
real_me = answered(lambda: read("me_ads_catalog", csv(
    REAL_ME_HEADER, "2026-10-04,1,Camp,CAT1,Earrings,ACTIVE,10.5,50,3,200,4,0.13,1,2,3.5,EMPTY,4.1,10")))
check("his real file's columns (Spend beside Ad Spend Per Order) are read, and the per-order figure is not the spend",
      real_me is not None and real_me.records["CAT1"]["2026-10-04"] == {"adViews": 200, "adClicks": 4, "adSpend": 10.5, "adSales": 3})
check("two columns that could both be the orders column stop the file",
      refused(lambda: read("me_ads_catalog", csv(ME_HEADER + ",Total Orders", "2026-10-04,1,C,CAT1,N,1,1,1,1,1,1,1")), table.CannotRead))

# ------------------------------------------------------------ the record's write

write = firestore.a_views_write("p", "flipkart__SKU-A", "flipkart", "SKU-A",
                                {"2026-10-04": {"views": 5, "revenue": 1.5}}, ["2026-07-01"], "2026-10-05")
paths = write["updateMask"]["fieldPaths"]
check("a figure is its own field path, so another report's figures on the same day are not touched",
      "days.`2026-10-04`.views" in paths and "days.`2026-10-04`.revenue" in paths and "days.`2026-10-04`" not in paths)
check("a day to drop is in the mask and not in the record, which is how Firestore deletes it",
      "days.`2026-07-01`" in paths and "2026-07-01" not in write["update"]["fields"]["days"]["mapValue"]["fields"])
check("the record says whose it is",
      write["update"]["fields"]["platform"] == {"stringValue": "flipkart"}
      and write["update"]["fields"]["listingId"] == {"stringValue": "SKU-A"})
check("a count goes as a whole number and money as a double",
      write["update"]["fields"]["days"]["mapValue"]["fields"]["2026-10-04"]["mapValue"]["fields"]["views"] == {"integerValue": "5"}
      and write["update"]["fields"]["days"]["mapValue"]["fields"]["2026-10-04"]["mapValue"]["fields"]["revenue"] == {"doubleValue": 1.5})
check("it is named in the listing_views collection", write["update"]["name"].endswith("/documents/listing_views/flipkart__SKU-A"))
check("a day that is not a day is refused, since it would be written into a field path",
      refused(lambda: firestore.a_views_write("p", "x", "flipkart", "x", {"2026-10-04`.views": {"views": 1}}, [], "2026-10-05"), firestore.Refused))
check("a field the record does not have is refused",
      refused(lambda: firestore.a_views_write("p", "x", "flipkart", "x", {"2026-10-04": {"stock": 1}}, [], "2026-10-05"), firestore.Refused))
check("a true is not a figure",
      refused(lambda: firestore.a_views_write("p", "x", "flipkart", "x", {"2026-10-04": {"views": True}}, [], "2026-10-05"), firestore.Refused))
check("a slash in a name is refused by the one place that names records",
      refused(lambda: firestore.a_views_write("p", "a/b", "flipkart", "x", {}, [], "2026-10-05"), firestore.Refused))
check("days held are read out of what Firestore answered",
      firestore.days_held({"fields": {"days": {"mapValue": {"fields": {"2026-10-05": {}, "2026-10-04": {}}}}}})
      == ("2026-10-04", "2026-10-05") and firestore.days_held(None) == ())


class Reply:
    def __init__(self, status=200, body=None):
        self.status, self._body, self.text = status, body if body is not None else {}, str(body or "")

    ok = property(lambda self: 200 <= self.status < 300)

    def json(self):
        return self._body


class Transport:
    def __init__(self, held=None, fail_on=None):
        self.posts, self.held, self.fail_on = [], held or {}, fail_on

    def post(self, url, params=None, headers=None, json=None, data=None):
        self.posts.append({"url": url, "json": json})
        if url.endswith(":batchGet"):
            found = [{"found": {"name": n, "fields": {"days": {"mapValue": {"fields": {d: {} for d in self.held[n.rsplit('/', 1)[-1]]}}}}}}
                     if n.rsplit("/", 1)[-1] in self.held else {"missing": n} for n in json["documents"]]
            return Reply(200, found)
        return Reply(self.fail_on or 200, {})


# ------------------------------------------------------------ the sink

there = Transport()
put = answered(lambda: firestore_door.a_views_sink(there, "p", "2026-10-05", 60)("flipkart", {"SKU-A": {"2026-10-04": {"views": 1}}}))
check("a new listing is asked about first, then written", [p["url"].rsplit(":", 1)[-1] for p in there.posts] == ["batchGet", "commit"])
check("and the sink says how many records it wrote", put == 1)
check("the record is named platform, two underscores, listing",
      there.posts[1]["json"]["writes"][0]["update"]["name"].endswith("/listing_views/flipkart__SKU-A"))

days = [f"2026-{m:02d}-{d:02d}" for m, d in [(7, n) for n in range(1, 32)] + [(8, n) for n in range(1, 32)]]  # 62 days
trim = Transport(held={"flipkart__SKU-A": days})
answered(lambda: firestore_door.a_views_sink(trim, "p", "2026-10-05", 60)("flipkart", {"SKU-A": {"2026-10-04": {"views": 1}}}))
mask = trim.posts[1]["json"]["writes"][0]["updateMask"]["fieldPaths"]
dropped = [m for m in mask if m.startswith("days.`") and m.count(".") == 1]
check("a record is held to its newest sixty days: the three oldest of sixty-three go",
      sorted(dropped) == [f"days.`{d}`" for d in days[:3]])
check("and the new day is written", "days.`2026-10-04`.views" in mask)

old = Transport(held={"flipkart__SKU-A": days[2:]})
answered(lambda: firestore_door.a_views_sink(old, "p", "2026-10-05", 60)("flipkart", {"SKU-A": {"2026-01-01": {"views": 1}}}))
check("a day older than all sixty already held is not written at all",
      not any("2026-01-01" in m for m in old.posts[1]["json"]["writes"][0]["updateMask"]["fieldPaths"]))

check("a database that says no stops the sink",
      refused(lambda: firestore_door.a_views_sink(Transport(fail_on=403), "p", "2026-10-05", 60)(
          "flipkart", {"A": {"2026-10-04": {"views": 1}}}), firestore_door.TheirDatabaseSaidNo))


neg = answered(lambda: read("fk_views", csv(FK_VIEWS_HEADER, "2026-10-04,SKU-A,5,1,1,-10.5")))
check("money can be negative (a refund), a count cannot",
      neg is not None and neg.records["SKU-A"]["2026-10-04"]["revenue"] == -10.5)
check("revenue is kept to the paisa",
      answered(lambda: read("fk_views", csv(FK_VIEWS_HEADER, "2026-10-04,SKU-A,5,1,1,10.456")).records["SKU-A"]["2026-10-04"]["revenue"]) == 10.46)

class NotAList(Transport):
    def post(self, url, params=None, headers=None, json=None, data=None):
        self.posts.append({"url": url, "json": json})
        return Reply(200, {"error": "a proxy page"})


check("a reply that is not a list of records stops the sink rather than meaning nothing is held",
      refused(lambda: firestore_door.a_views_sink(NotAList(), "p", "2026-10-05", 60)("flipkart", {"A": {"2026-10-04": {"views": 1}}}),
              firestore_door.TheirDatabaseSaidNo))

# ------------------------------------------------------------ the night


NS = ('xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')


def an_xlsx(rows):
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("xl/workbook.xml", f'<workbook {NS}><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" '
                   'Target="worksheets/sheet1.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/></Relationships>')
        body = []
        for number, cells in enumerate(rows, start=1):
            inside = "".join(f'<c r="{chr(65 + n)}{number}" t="inlineStr"><is><t>{escape(c)}</t></is></c>' for n, c in enumerate(cells) if c != "")
            body.append(f'<row r="{number}">{inside}</row>')
        z.writestr("xl/worksheets/sheet1.xml", f'<worksheet {NS}><sheetData>' + "".join(body) + "</sheetData></worksheet>")
    return out.getvalue()


XLSX = an_xlsx([FK_VIEWS_HEADER.split(","), "2026-10-04,SKU-A,100,10,2,398.5".split(",")])


def a_file(which, name, size=100):
    return whats_new.InTheFolder(which=which, name=name, size=size)


class Night:
    def __init__(self, files, bodies, record=True, throws=False):
        self.files, self.bodies, self.written, self.throws = files, bodies, [], throws
        self.record = self.write if record else None

    def write(self, platform, records):
        if self.throws:
            raise RuntimeError("the database would not take it")
        self.written.append((platform, records))
        return len(records)

    def go(self, already=()):
        return answered(lambda: reading.read_what_is_new(
            already_read=already,
            what_is_in_the_folder=lambda r: list(self.files.get(r, ())),
            bring_it_back=lambda w: self.bodies[w],
            record_the_sales=lambda readings: None,
            record_views=self.record,
        ))


FILES = {
    "fk_views": [a_file("v1", "flipkart_fk_views_2026-10-04.xlsx")],
    "fk_ads_fsn": [a_file("a1", "flipkart_fk_ads_fsn_2026-06-19.csv")],
    "me_ads_catalog": [a_file("m1", "meesho_me_ads_catalog_2026-10-04.csv")],
}
BODIES = {"v1": XLSX, "a1": FSN, "m1": csv(ME_HEADER, "2026-10-04,1,C,CAT1,N,10,0,3,200,4,1")}
night = Night(FILES, BODIES)
was = night.go()
check("a night reads the traffic file, the ads file and the catalogue file into records",
      was is not None and len(was.read_tonight) == 3 and [w[0] for w in night.written].count("flipkart") == 2
      and ("meesho" in [w[0] for w in night.written]))
check("the traffic figures reached the writer from a real spreadsheet",
      any(r.get("SKU-A", {}).get("2026-10-04", {}).get("views") == 100 for _, r in night.written))
check("the ads file dated itself from its first line, not from the name",
      any("SKU-A" in r and "2026-06-18" in r["SKU-A"] for _, r in night.written))
check("all three are written down as read, and the figures are counted",
      was is not None and set(was.files_read) == {"v1", "a1", "m1"} and was.listing_figures == 16)
check("the standing record says what each file held and what was read, into listing records",
      was is not None and {r.into for r in was.reads} == {"listing records"} and all(r.rows_read == r.rows_in_file for r in was.reads))
check("and it is said in the night's summary", was is not None and "16 listing figure(s)" in was.says())

again = Night(FILES, BODIES).go(already=("v1", "a1", "m1"))
check("a file already read is not read again", again is not None and again.read_tonight == () and again.already_read == 3)

nowhere = Night(FILES, BODIES, record=False)
was = nowhere.go()
check("with nowhere to write them the files are not opened and not marked read",
      was is not None and was.read_tonight == () and set(was.files_read) == set() and was.views_waiting == 3)
check("and the night says so in words", was is not None and "left unread" in was.says())

broken = Night(FILES, BODIES, throws=True)
was = broken.go()
check("a database that refuses leaves the files unread and says why, by name",
      was is not None and was.read_tonight == () and len(was.could_not_read) == 3
      and "the database would not take it" in was.could_not_read[0])

class Refusing(Night):
    def write(self, platform, records):
        raise firestore_door.TheirDatabaseSaidNo("403")


refusing = Refusing(FILES, BODIES)
was = refusing.go()
check("a database that says no is OUR defect, named as the database's, and the files stay unread",
      was is not None and was.is_a_defect and len(was.the_database_refused) == 3 and was.read_tonight == ()
      and "DATABASE REFUSED" in was.says())

hopeless = Night({"fk_views": [a_file("v2", "flipkart_fk_views_2026-10-04.xlsx")]},
                 {"v2": an_xlsx([FK_VIEWS_HEADER.split(","), "04-10-2026,SKU-A,1,1,1,1".split(",")])})
was = hopeless.go()
check("a file in which no row could be read is NOT marked read, since it would never be opened again",
      was is not None and was.read_tonight == () and "no row of" in was.could_not_read[0])

nameless = Night({"fk_views": [a_file("v3", "views.xlsx")]}, {"v3": XLSX})
was = nameless.go()
check("a file with no day in its name is refused like every other reader's",
      was is not None and was.read_tonight == () and "no day in its name" in was.could_not_read[0])

# ------------------------------------------------------------ the rule that no report is fetched and dropped

check("every report has a reader or a reason, with the three views readers counted",
      reading.why_a_report_has_no_decision() == "")
check("the three listing readers are the three reports named",
      {o.report_id for o in reading.WHAT_VIEWS_CAN_BE_READ} == {"fk_views", "fk_ads_fsn", "me_ads_catalog"})
check("and each is a report that exists", all(o.report_id in reports.BY_ID for o in reading.WHAT_VIEWS_CAN_BE_READ))
check("none of them is also said to be unread", not ({"fk_views", "fk_ads_fsn", "me_ads_catalog"} & set(reading.WHAT_IS_FETCHED_AND_NOT_READ_YET)))
check("and they write no ledger column", all(o.knows == () for o in reading.WHAT_VIEWS_CAN_BE_READ))

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 62
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
