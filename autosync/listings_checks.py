"""Checks for reading the platforms' listing files and handing the ERP the listings it can put in front of the seller (plan jobs 41 and 46).

**EVERY LISTING IN HERE IS MADE UP.** The column names are the platforms' real ones, read off his real files; no value of his is written
here. On 2026-10-05 the readers were also run over his real Flipkart (`.xls`), Meesho and Amazon files, and the Flipkart and Meesho listings
were compared, listing for listing and field for field, with what the ERP's own reader (`src/modules/listings/reader.js`, run in node over the
same files) makes of them: 186 of 186 and 535 of 535, none different. That needs his files and the ERP's vendored spreadsheet library, so it is
not a check.

**THE ONE THAT KEEPS THE TWO COPIES OF A SHAPE ONE:** the ERP's committed `listing-files.js` is read back, and the columns, sheet-finding
columns, help-text marker, selling word and Shopsy prefix must be the ones written here.

Run: python autosync/listings_checks.py
"""

import re
import sys
import zipfile
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))

import firestore  # noqa: E402
import firestore_door  # noqa: E402
import listings as tool  # noqa: E402
import reading  # noqa: E402
import sheet  # noqa: E402
import table  # noqa: E402
import whats_new  # noqa: E402
import xls_checks  # noqa: E402
from the_other_half import readFromKartaan  # noqa: E402

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


def why(work):
    try:
        work()
    except table.CannotRead as wrong:
        return str(wrong)
    except Exception as wrong:  # noqa: BLE001
        return "THREW " + repr(wrong)
    return ""


NS = ('xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')


def an_xlsx(sheets):
    """`sheets` is {name: rows}. Cells are text; an empty one is left out, as a spreadsheet leaves it."""
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        names = list(sheets)
        z.writestr("xl/workbook.xml", f'<workbook {NS}><sheets>' + "".join(
            f'<sheet name="{n}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(names, start=1)) + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(
                       f'<Relationship Id="rId{i}" Target="worksheets/sheet{i}.xml" '
                       'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/>'
                       for i, _ in enumerate(names, start=1)) + "</Relationships>")
        for i, name in enumerate(names, start=1):
            body = []
            for number, cells in enumerate(sheets[name], start=1):
                inside = "".join(f'<c r="{chr(65 + n)}{number}" t="inlineStr"><is><t>{escape(str(c))}</t></is></c>'
                                 for n, c in enumerate(cells) if c != "")
                body.append(f'<row r="{number}">{inside}</row>')
            z.writestr(f"xl/worksheets/sheet{i}.xml", f'<worksheet {NS}><sheetData>' + "".join(body) + "</sheetData></worksheet>")
    return out.getvalue()


def tsv(*lines):
    return ("﻿" + "\n".join("\t".join(cells) for cells in lines) + "\n").encode("utf-8")


# ---------------------------------------------------------------- made-up files in the platforms' real shapes

FK_HEAD = ["Product Title", "Seller SKU Id", "Processing errors (if any)", "Sub-category", "Flipkart Serial Number", "Listing ID",
           "Listing Status", "Inactive Reason", "MRP", "Bank Settlement", "Your Selling Price", "System Stock count", "Your Stock Count"]
FK_HELP = ["Title of your product", "Your Identifier for a product", "Any errors", "Category", "Flipkart's Identifier", "Listing",
           "Status", "Reason", "MRP", "Bank", "Selling", "Current stock", "Edit this"]


def fk_row(sku, serial, stock="10", sub="earring", status="ACTIVE", mrp="999", settlement="100", price="199", title="A title"):
    return [title, sku, "", sub, serial, "LST" + serial, status, "", mrp, settlement, price, stock, ""]


FK_ROWS = [FK_HEAD, FK_HELP, fk_row("A-1", "SERIALAAAA0001"), fk_row("B (2)", "SERIALBBBB0002", stock="0", sub="shopsy_earring"),
           fk_row("C", "SERIALCCCC0003", status="INACTIVE", price="250.5")]
COUNTRIES = [["Andorra", "United Arab Emirates"]]

ME_HEAD = ["SERIAL NO", "CATALOG NAME", "CATALOG ID", "PRODUCT NAME", "PRODUCT ID", "STYLE ID", "VARIATION ID", "VARIATION", "STOCK",
           "SYSTEM STOCK COUNT", "YOUR STOCK COUNT"]
ME_HELP = ["Row identifier", "Catalog name", "Catalog id", "Product name", "Product id", "Product ID/Style ID", "Variation id",
           "Variation", "Stock type", "Current system stock count", "Edit this"]


def me_row(n, product, variation, sku="S-1", stock="100", size="Free Size"):
    return [str(n), "Cat", "5001", "A product", product, sku, variation, size, "ALL", stock, ""]


ME_ROWS = [ME_HEAD, ME_HELP, me_row(1, "1084835398", "167", "LM-5 (1)"), me_row(2, "1084835398", "168", "LM-5 (2)", "7", "2.4"),
           me_row(3, "593036550", "167", "Butterfly", "0")]

AZ_HEAD = ["item-name", "item-description", "listing-id", "seller-sku", "price", "quantity", "open-date", "image-url",
           "item-is-marketplace", "product-id-type", "item-condition", "asin1", "asin2", "asin3", "product-id", "add-delete",
           "pending-quantity", "fulfillment-channel", "maximum-retail-price"]


def az_row(sku, asin, listing="0902HY3BXDT", price="399", quantity="200", mrp="1199.0", name="A title"):
    return [name, "a long—description", listing, sku, price, quantity, "2026-09-03 01:05:38 IST", "", "y", "1", "11", asin, "", "",
            asin, "", "0", "DEFAULT", mrp]


AZ = tsv(AZ_HEAD, az_row("SKU-1", "B0G5QH9F2V"), az_row("SKU-2", "B0AAAAAAAA", listing="0902HY3BXDU", price="250.5", quantity="99"))


def read_one(shape, content, name="the file"):
    return tool.read_listings(shape, content, name)


# ---------------------------------------------------------------- Meesho: an .xlsx, the sheet found by its columns

meesho_file = an_xlsx({"Inventory-Update-Data-Fill This": ME_ROWS, "A decoy": [["Andorra", "Spain"]]})
me = answered(lambda: tool.read_listing_file("me_catalog", meesho_file, "meesho_me_catalog_2026-10-04.xlsx"))
check("a Meesho file's listings are read: one per product and variation, the help row left out",
      me is not None and list(me.records) == ["meesho::1084835398::167", "meesho::1084835398::168", "meesho::593036550::167"]
      and me.rows_in_file == 3 and me.not_read == ())
first = me.records["meesho::1084835398::167"] if me else {}
check("a listing carries exactly the fields a listing has", me is not None and set(first) == set(firestore.LISTING_FIELDS))
check("its stock is a whole number, its money is nothing at all (Meesho's file has none), and it is live because it is in the file",
      first.get("stock") == 100 and isinstance(first.get("stock"), int) and first.get("mrp") is None
      and first.get("sellingPrice") is None and first.get("settlement") is None and first.get("state") == "live")
check("what Meesho says the row varies by, and its catalogue, are handed on exactly as written",
      me is not None and me.records["meesho::1084835398::168"]["platformVariation"] == "2.4" and first.get("catalogId") == "5001")
check("the buyer's page is the product id in base 36", first.get("buyerLink") == "https://www.meesho.com/product/p/hxvscm")
check("the SKU is kept as typed and is not what tells two listings apart",
      first.get("sku") == "LM-5 (1)" and first.get("platformId") == "1084835398::167")

# ---------------------------------------------------------------- Flipkart: an old .xls, found among a book's other sheets

old_book = xls_checks.an_old_spreadsheet(xls_checks.a_workbook({
    "dropDown": COUNTRIES, "7cef57d437f543f3-listing-ui-gro": FK_ROWS, "1791002986183_default": [[""] * 3]}))
fk = answered(lambda: tool.read_listing_file("fk_listings", old_book, "flipkart_fk_listings_2026-10-02.xls"))
check("a Flipkart .xls is read: the sheet is found by its columns, whatever it is called and wherever it sits",
      fk is not None and list(fk.records) == ["flipkart::SERIALAAAA0001", "shopsy::SERIALBBBB0002", "flipkart::SERIALCCCC0003"]
      and fk.not_read == ())
a1 = fk.records["flipkart::SERIALAAAA0001"] if fk else {}
check("Flipkart's three money figures, its listing id and its stock come through as numbers and text",
      (a1.get("mrp"), a1.get("settlement"), a1.get("sellingPrice"), a1.get("stock"), a1.get("listingId"))
      == (999, 100, 199, 10, "LSTSERIALAAAA0001") and a1.get("state") == "live")
check("a Shopsy listing is told by its own category, and gets the Shopsy address",
      fk is not None and fk.records["shopsy::SERIALBBBB0002"]["buyerLink"] == "https://www.shopsy.in/product/p/itme?pid=SERIALBBBB0002"
      and a1.get("buyerLink") == "https://www.flipkart.com/product/p/itme?pid=SERIALAAAA0001")
check("a status that is not ACTIVE is not live, and a decimal price stays a decimal",
      fk is not None and fk.records["flipkart::SERIALCCCC0003"]["state"] == "not_live"
      and fk.records["flipkart::SERIALCCCC0003"]["sellingPrice"] == 250.5)
as_xlsx = answered(lambda: tool.read_listing_file("fk_listings", an_xlsx({"x": FK_ROWS}), "flipkart_fk_listings_2026-10-02.xlsx"))
check("the same listings read from an .xlsx come out the same", as_xlsx is not None and fk is not None and as_xlsx.records == fk.records)

# ---------------------------------------------------------------- Amazon: tab-separated text, from his real file's columns

az = answered(lambda: tool.read_listings(tool.AMAZON, table.read(AZ, header_row=1), "the Amazon file"))
check("an Amazon file is read, with the ASIN as the key", az is not None and list(az.records) == ["amazon::B0G5QH9F2V", "amazon::B0AAAAAAAA"])
one = az.records["amazon::B0G5QH9F2V"] if az else {}
check("price is the selling price, the maximum retail price is the MRP, quantity is the stock, and Amazon's own listing id is carried",
      (one.get("sellingPrice"), one.get("mrp"), one.get("stock"), one.get("listingId"), one.get("settlement"))
      == (399, 1199, 200, "0902HY3BXDT", None) and one.get("sku") == "SKU-1")
check("it is live because the report lists active listings only, and the buyer's page is the ASIN's",
      one.get("state") == "live" and one.get("buyerLink") == "https://www.amazon.in/dp/B0G5QH9F2V")
check("an ASIN listed twice says so on the second row and is not dropped silently",
      "already uses the same id" in (answered(lambda: tool.read_listings(
          tool.AMAZON, table.read(tsv(AZ_HEAD, az_row("S1", "B0DUP00000"), az_row("S2", "B0DUP00000")), header_row=1), "x").not_read[0]) or ""))

# ---------------------------------------------------------------- a row that cannot be read says which line and why, and the rest are read


def the_rows(rows, shape=tool.FLIPKART):
    return answered(lambda: tool.read_listings(shape, sheet.table_from_rows(rows), "the file"))


bad = the_rows(FK_ROWS + [fk_row("D", ""), fk_row("E shopsy", "SERIALEEEE0005", sub=""), fk_row("F", "SERIALFFFF0006", status=""),
                          fk_row("G", "SERIALGGGG0007", stock="lots"), fk_row("A-1 again", "SERIALAAAA0001"),
                          fk_row("H", "HAS A SPACE")])
check("six rows that cannot be read are each said, with their line, and the three good ones are still read",
      bad is not None and len(bad.records) == 3 and len(bad.not_read) == 6 and all(line.startswith("line ") for line in bad.not_read))
check("a blank id, a sentence for an id, a Shopsy SKU with no category, a blank status, a stock that is not a number and a repeat are told apart",
      bad is not None and "could be an id" in bad.not_read[0] and "Shopsy" in bad.not_read[1] and "has not said whether" in bad.not_read[2]
      and "'lots'" in bad.not_read[3] and "already uses the same id" in bad.not_read[4] and "could be an id" in bad.not_read[5])
check("the help row is not a listing and not a refusal, and nothing about it is counted",
      bad is not None and bad.rows_in_file == 3 + 6 and all("Your Identifier" not in line for line in bad.not_read))
check("a number with an underscore or the word nan is not a number",
      the_rows(FK_ROWS[:2] + [fk_row("A", "SERIALAAAA0001", stock="1_000")]).not_read != ()
      and the_rows(FK_ROWS[:2] + [fk_row("A", "SERIALAAAA0001", stock="nan")]).not_read != ())
check("a number too big to be one (1e999) is a row to look at, not a file that fails every night",
      the_rows(FK_ROWS[:2] + [fk_row("A", "SERIALAAAA0001", stock="1e999"), fk_row("B", "SERIALBBBB0002")]).not_read != ()
      and len(the_rows(FK_ROWS[:2] + [fk_row("A", "SERIALAAAA0001", stock="1e999"), fk_row("B", "SERIALBBBB0002")]).records) == 1)
slashed = the_rows(FK_ROWS[:2] + [fk_row("A", "AB/CD"), fk_row("B", "SERIALBBBB0002"), fk_row("C", "X" * 1200)])
check("an id with a slash in it, or one too long to be a record's name, is a row to look at with what to do, and the rest are read",
      slashed is not None and len(slashed.records) == 1 and len(slashed.not_read) == 2 and "Check that row" in slashed.not_read[0])
check("a sheet holding only the platform's explanation row is refused, not read as no listings",
      "only the platform's explanation row" in why(lambda: tool.read_listings(tool.FLIPKART, sheet.table_from_rows(FK_ROWS[:2]), "x")))
check("a blank stock is not a stock of nothing: it is no figure at all",
      the_rows(FK_ROWS[:2] + [fk_row("A", "SERIALAAAA0001", stock="")]).records["flipkart::SERIALAAAA0001"]["stock"] is None)
check("a blank tail a spreadsheet leaves behind is not a row", the_rows(FK_ROWS + [[""] * 13]).rows_in_file == 3)

# ---------------------------------------------------------------- a file that cannot be read at all says what to do, in words

DO = "Download the listing file again"
no_column = why(lambda: tool.read_listings(tool.FLIPKART, sheet.table_from_rows([[c for c in FK_HEAD if c != "System Stock count"]] + [[]]), "the file"))
check("a missing column that a listing cannot be read without refuses the whole file, names the column and says what to do",
      "System Stock count" in no_column and DO in no_column)
check("a column a listing CAN be read without is not a refusal",
      the_rows([[c for c in FK_HEAD if c != "Bank Settlement"]] + [r[:9] + r[10:] for r in FK_ROWS[1:]]) is not None
      and the_rows([[c for c in FK_HEAD if c != "Bank Settlement"]] + [r[:9] + r[10:] for r in FK_ROWS[1:]]).records != {})
headings_only = why(lambda: tool.read_listings(tool.FLIPKART, sheet.table_from_rows([FK_HEAD]), "the file"))
check("headings with not one listing under them are refused rather than read as an empty catalogue",
      "not one listing" in headings_only and "Nothing was read" in headings_only)
check("a repeated heading among the ones read is refused, naming it",
      "'MRP'" in why(lambda: tool.read_listings(tool.FLIPKART, sheet.table_from_rows([FK_HEAD + ["MRP"]] + [r + ["1"] for r in FK_ROWS[1:]]), "x")))
wrong_file = why(lambda: tool.read_listing_file("fk_listings", meesho_file, "meesho_me_catalog_2026-10-04.xlsx"))
check("a Meesho file given as Flipkart's is told what it is not, with what to do", "does not look like a Flipkart listings file" in wrong_file and DO in wrong_file)
two = why(lambda: tool.read_listing_file("fk_listings", an_xlsx({"one": FK_ROWS, "two": FK_ROWS}), "x"))
check("two sheets that both look like the platform's are refused, not decided by which came first", "2 sheets" in two and DO in two)
check("a report that is no listing file is refused", "knows how to read" in why(lambda: tool.read_listing_file("fk_orders", meesho_file, "x")))
not_a_sheet = why(lambda: tool.read_listing_file("fk_listings", b"just text", "x"))
check("bytes that are no spreadsheet are refused in words", not_a_sheet != "" and not not_a_sheet.startswith("THREW"))

# ---------------------------------------------------------------- the ERP's own copy of the shapes, read back out of what is committed

THEIRS = readFromKartaan("src", "shared", "definitions", "listing-files.js")


def their_block(platform):
    start = THEIRS.index(f"id: '{platform}'")
    end = THEIRS.find("\n  {\n    id:", start + 1)
    return THEIRS[start: end if end > 0 else THEIRS.index("\n];", start)]


def their_columns(platform):
    inside = their_block(platform)
    inside = inside[inside.index("columns: {"):]
    inside = inside[: inside.index("\n    },")]
    return dict(re.findall(r"^ {6}(\w+): '([^']+)',?\s*$", inside, re.M))


def their_find_by(platform):
    return tuple(re.findall(r"'([^']+)'", re.search(r"findSheetBy: \[([^\]]*)\]", their_block(platform)).group(1)))


for mine in (tool.FLIPKART, tool.MEESHO):
    check(f"{mine.id}: the columns here are the ERP's columns, role for role", their_columns(mine.id) == mine.columns)
    check(f"{mine.id}: the columns that find the sheet are the ERP's", their_find_by(mine.id) == mine.find_by)
helps = dict(re.findall(r"(flipkart|meesho): \{ column: '([^']+)', says: '[^']+' \}", THEIRS))
says = dict((p, s) for p, s in re.findall(r"(flipkart|meesho): \{ column: '[^']+', says: '([^']+)' \}", THEIRS))
check("the help-text marker, the one cell only the help row has, is the ERP's for both",
      (helps["flipkart"], says["flipkart"]) == tool.FLIPKART.help_text and (helps["meesho"], says["meesho"]) == tool.MEESHO.help_text)
check("the word Flipkart uses for a selling listing and the prefix that marks a Shopsy one are the ERP's",
      f"const FLIPKART_SELLING = '{tool.FLIPKART_SELLING}';" in THEIRS and f"const SHOPSY_PREFIX = '{tool.SHOPSY_PREFIX}';" in THEIRS)
check("the columns a listing can be read without are the ERP's",
      tuple(re.findall(r"'(\w+)'", re.search(r"const CAN_BE_MISSING = \[([^\]]*)\]", THEIRS).group(1))) == tool.CAN_BE_MISSING)
check("a listing is named exactly as the ERP names one waiting to be placed: platform, two colons, the platform's own id",
      tool.the_review_id({"platform": "meesho", "platformId": "1::2"}) == "meesho::1::2"
      and "`${listing.platform}::${listing.platformId}`" in readFromKartaan("src", "modules", "products", "catalogue.js"))
check("until the ERP has an Amazon entry, nothing here pretends it does; when it has, it must say what this says",
      "id: 'amazon'" not in THEIRS or (their_columns("amazon") == tool.AMAZON.columns))

# ---------------------------------------------------------------- the record's write

listing = {k: ("x" if k not in firestore.LISTING_FIGURES else 1) for k in firestore.LISTING_FIELDS}
listing.update(platform="flipkart", platformId="SERIAL1", mrp=None, sellingPrice=250.5)
write = answered(lambda: firestore.a_listing_write("p", listing, "fk_listings", "2026-10-02"))
fields = write["update"]["fields"] if write else {}
check("the record is the ERP's own queue record, {id, listing}, with the report and the day added",
      set(fields) == {"id", "listing", "report", "changedOn"} and fields["id"] == {"stringValue": "flipkart::SERIAL1"}
      and fields["report"] == {"stringValue": "fk_listings"} and fields["changedOn"] == {"stringValue": "2026-10-02"})
inside = fields["listing"]["mapValue"]["fields"] if fields else {}
check("a whole stock is a whole number, money is a double, and a figure not given is null",
      (inside["stock"], inside["sellingPrice"], inside["mrp"]) == ({"integerValue": "1"}, {"doubleValue": 250.5}, {"nullValue": None}))
check("it is named by the ERP's own id, in the listings_seen collection",
      write is not None and write["update"]["name"].endswith("/documents/listings_seen/flipkart::SERIAL1"))
check("it is written whole, with no mask, so a field a listing no longer has does not stay behind", write is not None and "updateMask" not in write)
def refused(work):
    try:
        work()
    except firestore.Refused:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


check("a listing with a field it should not have, or one missing, is refused",
      refused(lambda: firestore.a_listing_write("p", dict(listing, extra="x"), "r", "2026-10-02"))
      and refused(lambda: firestore.a_listing_write("p", {k: v for k, v in listing.items() if k != "sku"}, "r", "2026-10-02")))
check("a figure that is text, a text field that is a number, and a day that is not a day are refused",
      refused(lambda: firestore.a_listing_write("p", dict(listing, stock="10"), "r", "2026-10-02"))
      and refused(lambda: firestore.a_listing_write("p", dict(listing, sku=5), "r", "2026-10-02"))
      and refused(lambda: firestore.a_listing_write("p", listing, "r", "yesterday")))
check("the collection is one the job may write, and one of a platform's own names is not", firestore.LISTINGS_SEEN in firestore.WHAT_IT_MAY_WRITE
      and refused(lambda: firestore.where_a_document_lives("p", "needs_review", "x")) and refused(lambda: firestore.where_a_document_lives("p", "products", "x")))
check("what a record holds is read back out of what Firestore answered",
      firestore.listing_held(write["update"]) == {**listing} and firestore.listing_held(None) is None and firestore.listing_held({"fields": {}}) is None)


# ---------------------------------------------------------------- the sink: the records are asked for first, and only what is new or different is written


class Reply:
    def __init__(self, status=200, body=None):
        self.status, self._body, self.text = status, body if body is not None else {}, str(body or "")

    ok = property(lambda self: 200 <= self.status < 300)

    def json(self):
        return self._body


class Transport:
    def __init__(self, held=None, fail_on=None, not_a_list=False):
        self.posts, self.held, self.fail_on, self.not_a_list = [], held or {}, fail_on, not_a_list

    def post(self, url, params=None, headers=None, json=None, data=None):
        self.posts.append({"url": url, "json": json})
        if url.endswith(":batchGet"):
            if self.not_a_list:
                return Reply(200, {"oops": 1})
            found = []
            for name in json["documents"]:
                key = name.rsplit("/", 1)[-1]
                found.append({"found": {"name": name, "fields": firestore.a_listing_write("p", self.held[key], "r", "2026-10-01")["update"]["fields"]}}
                             if key in self.held else {"missing": name})
            return Reply(200, found)
        return Reply(self.fail_on or 200, {})

    def commits(self):
        return [w for p in self.posts if p["url"].endswith(":commit") for w in p["json"]["writes"]]


names = {tool.the_review_id(v): v for v in (fk.records.values() if fk else ())}
fresh = Transport()
put = answered(lambda: firestore_door.a_listings_sink(fresh, "p")("fk_listings", "2026-10-02", names))
check("listings the ERP has never been given are asked about first, then all written",
      put == 3 and [p["url"].rsplit(":", 1)[-1] for p in fresh.posts] == ["batchGet", "commit"] and len(fresh.commits()) == 3)
same = Transport(held=names)
check("a second file naming the same listings writes nothing at all, which is how a second run queues nothing new",
      answered(lambda: firestore_door.a_listings_sink(same, "p")("fk_listings", "2026-10-03", names)) == 0 and same.commits() == [])
moved = dict(names)
key = "flipkart::SERIALAAAA0001"
moved[key] = dict(moved[key], stock=3)
one_changed = Transport(held=names)
check("a listing whose stock moved is written again, and only that one",
      answered(lambda: firestore_door.a_listings_sink(one_changed, "p")("fk_listings", "2026-10-03", moved)) == 1
      and [w["update"]["name"].rsplit("/", 1)[-1] for w in one_changed.commits()] == [key])
check("a listing that is new beside the ones held is written, and the ones held are not",
      answered(lambda: firestore_door.a_listings_sink(Transport(held={key: names[key]}), "p")("fk_listings", "2026-10-03", names)) == 2)
newer_held = Transport()
newer_held.post = lambda url, params=None, headers=None, json=None, data=None: (
    Reply(200, [{"found": {"name": n, "fields": firestore.a_listing_write("p", dict(names[key], stock=1), "r", "2026-10-09")["update"]["fields"]}}
                for n in json["documents"]]) if url.endswith(":batchGet") else Reply(200, {}))
check("a file uploaded late never puts older figures over newer ones: a held record of a later day is left alone",
      answered(lambda: firestore_door.a_listings_sink(newer_held, "p")("fk_listings", "2026-10-02", {key: names[key]})) == 0)
try:
    firestore_door.a_listings_sink(Transport(fail_on=403), "p")("fk_listings", "2026-10-02", names)
    check("a database that says no raises, so the file is not marked read", False)
except firestore_door.TheirDatabaseSaidNo:
    check("a database that says no raises, so the file is not marked read", True)
try:
    firestore_door.a_listings_sink(Transport(not_a_list=True), "p")("fk_listings", "2026-10-02", names)
    check("an answer that is not a list is not read as nothing held", False)
except firestore_door.TheirDatabaseSaidNo:
    check("an answer that is not a list is not read as nothing held", True)

# ---------------------------------------------------------------- the night


def a_file(which, name, size=100):
    return whats_new.InTheFolder(which=which, name=name, size=size)


class Night:
    def __init__(self, files, bodies, record=True, error=None):
        self.files, self.bodies, self.written, self.error = files, bodies, [], error
        self.record = self.write if record else None

    def write(self, report_id, day, found):
        if self.error:
            raise self.error
        self.written.append((report_id, day, found))
        return len(found)

    def go(self, already=()):
        return answered(lambda: reading.read_what_is_new(
            already_read=already,
            what_is_in_the_folder=lambda r: list(self.files.get(r, ())),
            bring_it_back=lambda w: self.bodies[w],
            record_the_sales=lambda readings: None,
            record_listings=self.record,
        ))


FILES = {"fk_listings": [a_file("f1", "flipkart_fk_listings_2026-10-02.xls")], "me_catalog": [a_file("m1", "meesho_me_catalog_2026-10-04.xlsx")]}
BODIES = {"f1": old_book, "m1": meesho_file}
night = Night(FILES, BODIES)
was = night.go()
check("a night reads both listing files and hands the listings over, each with its day",
      was is not None and len(was.read_tonight) == 2 and {(r, d) for r, d, _ in night.written} == {("fk_listings", "2026-10-02"), ("me_catalog", "2026-10-04")}
      and sum(len(f) for _, _, f in night.written) == 6)
check("both are written down as read, and the new listings are counted", was is not None and set(was.files_read) == {"f1", "m1"} and was.listings_written == 6)
check("the standing record says what each file held and what was read, into listings waiting to be let in",
      was is not None and {r.into for r in was.reads} == {"listings waiting to be let in"} and all(r.rows_read == r.rows_in_file for r in was.reads))
check("and the night's summary says how many are waiting for the seller", was is not None and "6 listing(s) were new or changed" in was.says())
check("a file already read is not read again",
      (answered(lambda: Night(FILES, BODIES).go(already=("f1", "m1"))) or was).read_tonight == ())
nowhere = Night(FILES, BODIES, record=False).go()
check("with nowhere to write them the files are not opened and not marked read, and the night says so",
      nowhere is not None and nowhere.read_tonight == () and not nowhere.files_read and nowhere.listings_waiting == 2 and "left unread" in nowhere.says())
broken = Night(FILES, BODIES, error=RuntimeError("the database would not take it")).go()
check("a database that fails leaves the files unread and says why, by name",
      broken is not None and broken.read_tonight == () and len(broken.could_not_read) == 2 and "would not take it" in broken.could_not_read[0])
refusing = Night(FILES, BODIES, error=firestore_door.TheirDatabaseSaidNo("403")).go()
check("a database that says no is OUR defect and the files stay unread",
      refusing is not None and refusing.is_a_defect and len(refusing.the_database_refused) == 2 and refusing.read_tonight == ())
partly = Night({"fk_listings": [a_file("f2", "flipkart_fk_listings_2026-10-02.xls")]},
               {"f2": xls_checks.an_old_spreadsheet(xls_checks.a_workbook({"d": FK_ROWS + [fk_row("D", "")]}))}).go()
check("a file with one bad row is read, marked read, and the bad row is said by line",
      partly is not None and partly.read_tonight == ("f2",) and partly.rows_refused == 1 and "1 row(s) not read" in partly.could_not_read[0])
hopeless = Night({"me_catalog": [a_file("m2", "meesho_me_catalog_2026-10-04.xlsx")]},
                 {"m2": an_xlsx({"s": [ME_HEAD, ME_HELP, me_row(1, "", "")]})}).go()
check("a file in which no row could be read is NOT marked read, since it would never be opened again",
      hopeless is not None and hopeless.read_tonight == () and "no row of" in hopeless.could_not_read[0])
nameless = Night({"me_catalog": [a_file("m3", "catalog.xlsx")]}, {"m3": meesho_file}).go()
check("a file with no day in its name is refused like every other reader's",
      nameless is not None and nameless.read_tonight == () and "no day in its name" in nameless.could_not_read[0])
check("every report is still read or says why it is not", reading.why_a_report_has_no_decision() == ""
      and {o.report_id for o in reading.WHAT_LISTINGS_CAN_BE_READ} == {"fk_listings", "me_catalog"}
      and not ({"fk_listings", "me_catalog"} & set(reading.WHAT_IS_FETCHED_AND_NOT_READ_YET)))

check("nothing above ended by throwing rather than by answering -- " + str(THREW), not THREW)
EXPECTED = 70
check(f"checks went missing -- {ran + 1} ran, {EXPECTED} expected", ran + 1 == EXPECTED)

if failures:
    print(f"\n{len(failures)} FAILED ({ran} checks)")
    sys.exit(1)
print(f"\nall {ran} checks passed")
