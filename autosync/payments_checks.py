"""Checks for reading a platform's payment file onto the orders the ledger already has (job 36).

**EVERY FIGURE IN HERE IS MADE UP.** The shapes -- which columns, which sheet, which row the names are on, which sign a platform
writes a charge in -- come from his three real files, read on 2026-10-05; not one value from them is written in this file, and the
files themselves stay in `D:\\Kartaan-Samples`, never committed. The last group below reads those files if they are on this machine,
and asks only questions about their SHAPE (how many order lines, whether the money adds up against an independent sum) -- it never
prints a figure of his.

Run: python autosync/payments_checks.py
"""

import csv
import io
import os
import sys
import zipfile
from dataclasses import replace
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ledger  # noqa: E402
import ledger_sheet  # noqa: E402
import payments as tool  # noqa: E402
import reading  # noqa: E402
import sales  # noqa: E402
import table  # noqa: E402
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


def refused_by(work):
    try:
        work()
    except table.CannotRead:
        return True
    except Exception:  # noqa: BLE001
        return False
    return False


SAMPLES = Path(os.environ.get("KARTAAN_SAMPLES") or r"D:\Kartaan-Samples")

# ------------------------------------------------------------------ files, made by hand

NS = ('xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')


def letters(n):
    out = ""
    n += 1
    while n:
        n, rest = divmod(n - 1, 26)
        out = chr(65 + rest) + out
    return out


def a_spreadsheet(sheets):
    """A real `.xlsx`, the way a platform writes one: a zip of XML parts, the part names not in the sheet order."""
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        book = [f"<workbook {NS}><sheets>"]
        rels = ['<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for at, (name, rows) in enumerate(sheets, start=1):
            rid = f"rId{100 + at}"
            part = f"worksheets/sheet{90 - at}.xml"
            book.append(f'<sheet name="{name}" sheetId="{at}" r:id="{rid}"/>')
            rels.append(
                f'<Relationship Id="{rid}" Target="{part}" Type="http://schemas.openxmlformats.org/officeDocument/'
                'relationships/worksheet"/>'
            )
            body = []
            for number, cells in enumerate(rows, start=1):
                inside = "".join(
                    f'<c r="{letters(n)}{number}" t="inlineStr"><is><t>{escape(said)}</t></is></c>'
                    for n, said in enumerate(cells) if said != ""
                )
                body.append(f'<row r="{number}">{inside}</row>')
            z.writestr("xl/" + part, f'<worksheet {NS}><dimension ref="A1"/><sheetData>' + "".join(body) + "</sheetData></worksheet>")
        book.append("</sheets></workbook>")
        rels.append("</Relationships>")
        z.writestr("xl/workbook.xml", "".join(book))
        z.writestr("xl/_rels/workbook.xml.rels", "".join(rels))
    return out.getvalue()


def a_line(columns, **said):
    """One row, in the order of `columns`, from `{column: figure}`. Anything not said is blank."""
    return [str(said.get(c, "")) for c in columns]


FLIPKART_COLUMNS = list(tool.the_columns_a_file_of("flipkart"))
# The real file's columns have more in them than this reads; extra ones in the middle must not move anything.
FLIPKART_HEADER = FLIPKART_COLUMNS[:2] + ["Some Other Column"] + FLIPKART_COLUMNS[2:]


def a_flipkart_file(*rows, rename=None):
    cols = [(rename or {}).get(c, c) for c in FLIPKART_HEADER]
    # **THE SUB-HEADER ROW UNDER THE NAMES, like his real file:** it has no order id and no figure.
    sub = ["", "", "", "sub-heading"] + [""] * (len(cols) - 4)
    return a_spreadsheet([
        ("Report Help", [["How to read this report"]]),
        ("Orders", [["Payment Details"] + [""] * (len(cols) - 1), cols, sub] + [r for r in rows]),
    ])


def a_flipkart_line(order, sku, settlement, **charges):
    names = {
        "commission": "Commission (Rs.)", "fixedFee": "Fixed Fee  (Rs.)", "collectionFee": "Collection Fee (Rs.)",
        "shipping": "Shipping Fee (Rs.)", "returnShipping": "Reverse Shipping Fee (Rs.)", "tcs": "TCS (Rs.)",
        "tds": "TDS (Rs.)", "otherServicesTax": "GST on MP Fees (Rs.)", "penalty": "Product Cancellation Fee (Rs.)",
        "pickAndPack": "Pick And Pack Fee (Rs.)", "franchise": "Franchise Fee (Rs.)",
    }
    said = {"Order ID": order, "Seller SKU": sku, "Bank Settlement Value (Rs.)": settlement}
    for key, figure in charges.items():
        said[names[key]] = figure
    return a_line(FLIPKART_HEADER, **said)


MEESHO_COLUMNS = list(tool.the_columns_a_file_of("meesho"))
# **THE NAMES MEESHO USES TWICE, as its real file does:** `Fixed Fee (Incl. GST)` appears among the revenue columns and again
# among the deductions, and the first is not read.
MEESHO_HEADER = (
    ["Sub Order No", "Supplier SKU", "Final Settlement Amount", "Fixed Fee (Incl. GST)"]
    + MEESHO_COLUMNS[3:5]
    + MEESHO_COLUMNS[5:]
    + ["Live Order Status"]
)


def a_meesho_file(*rows, rename=None):
    cols = [(rename or {}).get(c, c) for c in MEESHO_HEADER]
    formulas = ["", "A", "(B + C)"] + [""] * (len(cols) - 3)
    return a_spreadsheet([
        ("Disclaimer", [["Meesho"]]),
        ("Order Payments", [["Order Related Details"] + [""] * (len(cols) - 1), cols, formulas] + [r for r in rows]),
        ("Ads Cost", [["Ads Cost"], ["Deduction Date"], ["No data is available for these dates."]]),
    ])


def a_meesho_line(order, sku, settlement, first_fixed_fee="", status="", **charges):
    names = {
        "commission": "Meesho Commission (Incl. GST)", "shipping": "Shipping Charge (Incl. GST)",
        "returnShipping": "Return Shipping Charge (Incl. GST)", "tcs": "TCS", "tds": "TDS",
        "warehousing": "Warehousing fee (Incl. GST)", "returnPremium": "Return premium (incl GST)",
        "returnPremiumOfReturn": "Return premium (incl GST) of Return",
    }
    cells = a_line(MEESHO_HEADER, **{
        "Sub Order No": order, "Supplier SKU": sku, "Final Settlement Amount": settlement, "Live Order Status": status,
        **{names[k]: v for k, v in charges.items() if k != "fixedFee"},
    })
    cells[3] = first_fixed_fee  # the first of the two `Fixed Fee`s
    if "fixedFee" in charges:
        cells[len(MEESHO_HEADER) - 1 - MEESHO_HEADER[::-1].index("Fixed Fee (Incl. GST)")] = charges["fixedFee"]
    return cells


AMAZON_COLUMNS = ["date/time", "settlement id", "type", "order id", "Sku", "description", "quantity",
                  "product sales", "selling fees", "fba fees", "other transaction fees", "other",
                  "TCS-CGST", "TCS-SGST", "TCS-IGST", "TDS (Section 194-O)", "total", "Transaction Status"]
AMAZON_DEFINITIONS = [
    '"Includes Amazon Marketplace, Fulfillment by Amazon (FBA), and Amazon Webstore transactions"',
    '"All amounts in INR, unless specified"',
    '"Definitions:"',
    '"Selling fees: Includes variable closing fees and referral fees."',
    '"Other transaction fees: Includes shipping chargebacks, shipping holdbacks, and sales tax collection fees."',
]


def an_amazon_file(*rows, definitions=AMAZON_DEFINITIONS, ending="\r\n"):
    out = io.StringIO()
    writer = csv.writer(out, quoting=csv.QUOTE_ALL, lineterminator=ending)
    for one in definitions:
        out.write(one + ending)
    writer.writerow(AMAZON_COLUMNS)
    for one in rows:
        writer.writerow(one)
    return ("\ufeff" + out.getvalue()).encode("utf-8")


def an_amazon_line(kind, order, sku, total, status="Released", **said):
    return a_line(AMAZON_COLUMNS, **{"type": kind, "order id": order, "Sku": sku, "total": total,
                                     "Transaction Status": status, **said})


def a_folder_file(which, name):
    return whats_new.InTheFolder(which=which, name=name, size=500)


def read_as(report_id, name, body):
    how = next(o for o in reading.WHAT_CAN_BE_READ if o.report_id == report_id)
    return reading.a_reading(how, a_folder_file("f-" + report_id, name), body)


def charges_of(reading_, order, sku=""):
    one = next((s for s in reading_.sales if s.order_id == order and s.sku == sku), None)
    return None if one is None else one


# ================================================================ the readers: AMAZON

AMAZON_BODY = an_amazon_file(
    an_amazon_line("Order", "404-1", "SKU-A", "100.50", **{"selling fees": "-10", "TCS-IGST": "-1", "TCS-CGST": "-0.25",
                                                          "TCS-SGST": "-0.25", "fba fees": "0"}),
    # The order's own shipping fee: its own line, with no SKU.
    an_amazon_line("Shipping Services", "404-1", "", "-20", **{"other transaction fees": "-20"}),
    # An order of TWO SKUs, whose one shipping line names neither.
    an_amazon_line("Order", "404-6", "SKU-D", "40"),
    an_amazon_line("Order", "404-6", "SKU-E", "60"),
    an_amazon_line("Shipping Services", "404-6", "", "-9", **{"other transaction fees": "-9"}),
    an_amazon_line("Refund", "404-2", "SKU-B", "-50", **{"selling fees": "5", "product sales": "-60"}),
    an_amazon_line("Order", "404-2", "SKU-B", "0.1", **{"other transaction fees": ""}),
    an_amazon_line("Order", "404-2", "SKU-B", "0.2"),
    an_amazon_line("Order", "404-3", "SKU-C", "30", status="Deferred", **{"selling fees": "-3"}),
    an_amazon_line("Transfer", "", "", "-500"),
    an_amazon_line("Service Fee", "", "", "-12"),
)
_az = answered(lambda: read_as("az_settlements", "amazon_az_settlements_2026-09-30.csv", AMAZON_BODY))
_az_reading, _az_refused = _az if _az else (None, None)
_az_sales = {(s.order_id, s.sku): s for s in (_az_reading.sales if _az_reading else ())}

check("AMAZON: THE HEADER IS FOUND BELOW THE BLOCK OF DEFINITIONS, however long that block is", _az_reading is not None
      and len(_az_sales) > 0)
_longer = answered(lambda: read_as("az_settlements", "amazon_az_settlements_2026-09-30.csv", an_amazon_file(
    an_amazon_line("Order", "404-1", "SKU-A", "5"), definitions=AMAZON_DEFINITIONS * 3)))
check("and a longer block moves nothing", _longer is not None and len(_longer[0].sales) == 1)
check("and a file with no header line at all is refused rather than read from line one",
      refused_by(lambda: read_as("az_settlements", "amazon_az_settlements_2026-09-30.csv", b'"a","b"\r\n"1","2"\r\n')))
check("the reading says it is only for orders the ledger already has, and which file it is",
      _az_reading is not None and _az_reading.only_existing and _az_reading.which == "f-az_settlements")
check("and its day is the file's own, out of its name", _az_reading is not None and _az_reading.on == "2026-09-30")
check("and every sale carries that day in the payments marker", _az_reading is not None and all(
    s.payments_on == "2026-09-30" for s in _az_reading.sales))

_a1 = _az_sales.get(("404-1", "SKU-A"))
check("AMAZON: what was paid for an order is its released total, its own shipping line included",
      _a1 is not None and _a1.settlement == "80.5")
check("and a charge is positive where money was taken, so selling fees of minus ten are a commission of ten",
      _a1 is not None and _a1.charges.get("commission") == "10")
check("and the three TCS columns are one tax, added", _a1 is not None and _a1.charges.get("tcs") == "1.5")
check("and a real nought the platform wrote is a nought, not a blank",
      _a1 is not None and _a1.charges.get("fba fees".replace("fba fees", "otherServices")) == "0")
check("and a charge no line of the file mentions is left out of the sale, never written as nought",
      _a1 is not None and "tds" not in _a1.charges and "penalty" not in _a1.charges)
check("AN ORDER'S SHIPPING LINE WITH NO SKU IS PLACED ON THE ONE SKU THE SAME FILE NAMES FOR THAT ORDER",
      _a1 is not None and _a1.charges.get("shipping") == "20" and ("404-1", "") not in _az_sales)
check("BUT WITH TWO SKUS IN THE FILE IT CANNOT BE SAID WHICH, so it stays a line of its own, for the ledger to say",
      ("404-6", "") in _az_sales and _az_sales[("404-6", "")].charges.get("shipping") == "9"
      and _az_sales[("404-6", "SKU-D")].charges.get("shipping") is None)
_short = an_amazon_file(an_amazon_line("Order", "404-1", "SKU-A", "5")) + b'"a","b"' + bytes([13, 10])
_short_read = answered(lambda: read_as("az_settlements", "amazon_az_settlements_2026-09-30.csv", _short))
check("and a line the table could not read is counted, not lost without a word",
      _short_read is not None and len(_short_read[0].sales) == 1 and _short_read[1] == 1)
_a2 = _az_sales.get(("404-2", "SKU-B"))
check("a refund's lines are added to the order's own: the fee given back makes a negative commission",
      _a2 is not None and _a2.charges.get("commission") == "-5")
check("AND THEY ARE ADDED IN DECIMALS: 0.1 and 0.2 and a refund of fifty make minus forty-nine point seven, exactly",
      _a2 is not None and _a2.settlement == "-49.7")
check("A LINE THE PLATFORM HAS NOT RELEASED IS NOT MONEY PAID, so it is not on the order",
      ("404-3", "SKU-C") not in _az_sales)
check("and it is said, by its own word, left for a later file",
      _az_reading is not None and any("Deferred" in x and "later file" in x for x in _az_reading.set_aside))
check("A PAYOUT AND A SERVICE FEE WITH NO ORDER ARE SAID BY KIND, and are on no sale",
      _az_reading is not None and any("Transfer" in x for x in _az_reading.set_aside)
      and any("Service Fee" in x for x in _az_reading.set_aside)
      and all(s.order_id for s in _az_reading.sales))
check("an Amazon file with doubled line endings reads the same",
      answered(lambda: len(read_as("az_settlements", "amazon_az_settlements_2026-09-30.csv", an_amazon_file(
          an_amazon_line("Order", "404-1", "SKU-A", "5"), ending="\r\r\n"))[0].sales)) == 1)
check("AN AMAZON FILE WHOSE COLUMN HAS MOVED IS REFUSED BY NAME, not read with a blank where the figure was",
      refused_by(lambda: read_as("az_settlements", "amazon_az_settlements_2026-09-30.csv",
                                 AMAZON_BODY.replace(b'"total"', b'"grand total"'))))

# ================================================================ the readers: FLIPKART

FLIPKART_BODY = a_flipkart_file(
    a_flipkart_line("OD1", "SKU:DJ 14", "-300.5", commission="-40", fixedFee="-5", tcs="-2", tds="-1",
                    otherServicesTax="-9", pickAndPack="-3", franchise="-2"),
    a_flipkart_line("OD1", "DJ 15", "80"),
    a_flipkart_line("OD2", "DJ 14", "12.25", fixedFee="4", shipping="0", penalty="-7"),
    a_flipkart_line("", "", ""),
)
_fk = answered(lambda: read_as("fk_payments", "flipkart_fk_payments_2026-08-28.xlsx", FLIPKART_BODY))
_fk_reading = _fk[0] if _fk else None
_fk_sales = {(s.order_id, s.sku): s for s in (_fk_reading.sales if _fk_reading else ())}
check("FLIPKART: THE ORDERS SHEET IS READ BY NAME, the names on the second row, not the first sheet", _fk_reading is not None
      and len(_fk_sales) == 3)
check("and the sub-header row under the names is not an order and is not a refusal", _fk is not None and _fk[1] == 0
      and _fk_reading is not None and _fk_reading.set_aside == ())
_f1 = _fk_sales.get(("OD1", "DJ 14"))
check("the SKU's wrapper is taken off, exactly as the orders reader does, so it names the same row", _f1 is not None)
check("what was paid is the signed bank settlement, as the platform states it",
      _f1 is not None and _f1.settlement == "-300.5")
check("a charge is positive where money was taken: commission of minus forty is forty",
      _f1 is not None and _f1.charges.get("commission") == "40")
check("and a column whose name has two spaces in it is found by exactly that name",
      _f1 is not None and _f1.charges.get("fixedFee") == "5")
check("and the small fees are added into other services, one figure",
      _f1 is not None and _f1.charges.get("otherServices") == "5")
check("and the tax on the fees is its own charge", _f1 is not None and _f1.charges.get("otherServicesTax") == "9")
_f3 = _fk_sales.get(("OD2", "DJ 14"))
check("a fee that was given back is a negative charge", _f3 is not None and _f3.charges.get("fixedFee") == "-4")
check("and a cancellation fee is a penalty", _f3 is not None and _f3.charges.get("penalty") == "7")
check("an order of two items is two lines, each with its own money",
      _fk_sales.get(("OD1", "DJ 15")) is not None and _fk_sales[("OD1", "DJ 15")].settlement == "80")
_empty = answered(lambda: read_as("fk_payments", "flipkart_fk_payments_2026-08-28.xlsx", a_flipkart_file(
    a_flipkart_line("OD7", "DJ 14", ""))))
check("A LINE THAT NAMES AN ORDER AND STATES NO MONEY IS NOT A SALE: it would only stamp a payments day on a row nothing was paid for",
      _empty is not None and _empty[0].sales == ())
check("A FLIPKART FILE WHOSE SETTLEMENT COLUMN HAS BEEN RENAMED IS REFUSED, by name",
      refused_by(lambda: read_as("fk_payments", "flipkart_fk_payments_2026-08-28.xlsx",
                                 a_flipkart_file(rename={"Bank Settlement Value (Rs.)": "Bank Money (Rs.)"}))))
_nameless = answered(lambda: read_as("fk_payments", "flipkart_fk_payments_2026-08-28.xlsx", a_flipkart_file(
    a_flipkart_line("", "", "10"))))
check("A LINE WITH MONEY AND NO ORDER ID IS SAID, not dropped",
      _nameless is not None and any("no order id" in x for x in _nameless[0].set_aside))

# ================================================================ the readers: MEESHO

MEESHO_BODY = a_meesho_file(
    a_meesho_line("M1_1", "SKU-M", "150", status="Delivered", commission="-20", shipping="-30", tcs="-1", tds="-0.5", fixedFee="-4",
                  first_fixed_fee="99"),
    a_meesho_line("M2_1", "SKU-N", "-60", status="Return", returnShipping="-60"),
)
_me = answered(lambda: read_as("me_payments", "meesho_me_payments_2026-10-03.xlsx", MEESHO_BODY))
_me_reading = _me[0] if _me else None
_me_sales = {(s.order_id, s.sku): s for s in (_me_reading.sales if _me_reading else ())}
check("MEESHO: THE FORMULA ROW UNDER THE NAMES IS NOT AN ORDER", _me_reading is not None and len(_me_sales) == 2)
_m1 = _me_sales.get(("M1_1", "SKU-M"))
check("MEESHO'S LIVE ORDER STATUS SAYS WHAT BECAME OF THE ORDER: Delivered is Delivered, Return is Came back (D447)",
      _m1 is not None and _m1.what_happened == "Delivered" and _me_sales[("M2_1", "SKU-N")].what_happened == "Came back")
check("what was paid is the final settlement", _m1 is not None and _m1.settlement == "150")
_rto = answered(lambda: read_as("me_payments", "meesho_me_payments_2026-10-04.xlsx", a_meesho_file(
    a_meesho_line("M3_1", "SKU-R", "-40", status="RTO"),
    a_meesho_line("M4_1", "SKU-T", "-60", status="Return"), a_meesho_line("M4_1", "SKU-T", "10", status="Delivered"))))
_rto_sales = {s.order_id: s for s in (_rto[0].sales if _rto else ())}
check("RTO (returned to origin) in Live Order Status is Came back too (R20 proving)",
      _rto_sales.get("M3_1") is not None and _rto_sales["M3_1"].what_happened == "Came back")
check("a sub-order with a Return line and a LATER Delivered line has still come back (R20 proving)",
      _rto_sales.get("M4_1") is not None and _rto_sales["M4_1"].what_happened == "Came back")
_twice = a_spreadsheet([
    ("Disclaimer", [["Meesho"]]),
    ("Order Payments", [["Order Related Details"] + [""] * len(MEESHO_HEADER), MEESHO_HEADER + ["Live Order Status"],
                        ["", "A", "(B + C)"] + [""] * (len(MEESHO_HEADER) - 2),
                        a_meesho_line("M5_1", "SKU-W", "150", status="Delivered") + ["Return"]]),
    ("Ads Cost", [["Ads Cost"], ["Deduction Date"], ["No data is available for these dates."]]),
])
_two_cols = answered(lambda: read_as("me_payments", "meesho_me_payments_2026-10-05.xlsx", _twice))
check("a file with TWO Live Order Status columns says nothing about what became of an order, rather than picking one (R20 proving)",
      _two_cols is not None and all(not s.what_happened for s in _two_cols[0].sales) and len(_two_cols[0].sales) == 1)
check("a charge is positive where money was taken", _m1 is not None and _m1.charges.get("commission") == "20"
      and _m1.charges.get("shipping") == "30" and _m1.charges.get("tcs") == "1" and _m1.charges.get("tds") == "0.5")
check("A NAME MEESHO USES TWICE IS READ FROM THE DEDUCTIONS BLOCK ONLY: the first Fixed Fee's 99 is not a charge",
      _m1 is not None and _m1.charges.get("fixedFee") == "4")
check("and a settlement that took money back is negative, a return shipping charge a positive one",
      _me_sales[("M2_1", "SKU-N")].settlement == "-60" and _me_sales[("M2_1", "SKU-N")].charges.get("returnShipping") == "60")
check("a charge Meesho did not state is not on the sale", _m1 is not None and "warehousing" not in _m1.charges)
check("A MEESHO FILE WITH THE COMMISSION COLUMN GONE IS REFUSED, because the second Fixed Fee could not be told from the first",
      refused_by(lambda: read_as("me_payments", "meesho_me_payments_2026-10-03.xlsx", a_meesho_file(
          a_meesho_line("M1_1", "SKU-M", "150"), rename={"Meesho Commission (Incl. GST)": "Commission"}))))

# ================================================================ every charge column, against a table typed here on its own
# **THE EXPECTED NAMES ARE TYPED OUT HERE, NOT TAKEN FROM THE READER'S LISTS** -- a table built from the reader's own list can only
# agree with it. Each platform's file gets ONE column at a time set to a figure of minus seven, and the sale must carry exactly
# that charge, positive, and no other.
FLIPKART_EXPECTED = {
    "Commission (Rs.)": "commission", "Fixed Fee  (Rs.)": "fixedFee", "Collection Fee (Rs.)": "collectionFee",
    "Shipping Fee (Rs.)": "shipping", "Reverse Shipping Fee (Rs.)": "returnShipping",
    "Pick And Pack Fee (Rs.)": "otherServices", "No Cost Emi Fee Reimbursement(Rs.)": "otherServices",
    "Installation Fee (Rs.)": "otherServices", "Tech Visit Fee (Rs.)": "otherServices",
    "Uninstallation & Packaging Fee (Rs.)": "otherServices", "Customer Add-ons Amount Recovery (Rs.)": "otherServices",
    "Franchise Fee (Rs.)": "otherServices", "Shopsy Marketing Fee (Rs.)": "otherServices",
    "Protection Fund (Rs.)": "otherServices", "GST on MP Fees (Rs.)": "otherServicesTax", "TCS (Rs.)": "tcs",
    "TDS (Rs.)": "tds", "Product Cancellation Fee (Rs.)": "penalty",
}
_wrong_flipkart = []
for _name_, _id_ in FLIPKART_EXPECTED.items():
    _got = answered(lambda n=_name_: read_as("fk_payments", "flipkart_fk_payments_2026-08-28.xlsx", a_flipkart_file(
        a_line(FLIPKART_HEADER, **{"Order ID": "OD1", "Seller SKU": "S", "Bank Settlement Value (Rs.)": "1", n: "-7"})))[0].sales)
    if not _got or _got[0].charges != {_id_: "7"}:
        _wrong_flipkart.append(_name_)
check(f"EVERY FLIPKART CHARGE COLUMN LANDS IN THE CHARGE IT IS TYPED AGAINST HERE, alone -- wrong: {_wrong_flipkart}",
      not _wrong_flipkart)
check("and the Flipkart columns that are sums of the others (marketplace fee, taxes) are never read as charges",
      answered(lambda: read_as("fk_payments", "flipkart_fk_payments_2026-08-28.xlsx", a_flipkart_file(a_line(
          FLIPKART_HEADER, **{"Order ID": "OD1", "Seller SKU": "S", "Bank Settlement Value (Rs.)": "1",
                              "Some Other Column": "-7"})))[0].sales[0].charges) == {})
MEESHO_EXPECTED = {
    "Meesho Commission (Incl. GST)": "commission", "Meesho gold platform fee (Incl. GST)": "otherServices",
    "Meesho mall platform fee (Incl. GST)": "otherServices", "Warehousing fee (Incl. GST)": "warehousing",
    "Return Shipping Charge (Incl. GST)": "returnShipping", "Shipping Charge (Incl. GST)": "shipping",
    "Net Other Support Service Charges (Excl. GST)": "otherServices",
    "GST on Net Other Support Service Charges": "otherServicesTax", "TCS": "tcs", "TDS": "tds",
}
_wrong_meesho = []
for _name_, _id_ in MEESHO_EXPECTED.items():
    _got = answered(lambda n=_name_: read_as("me_payments", "meesho_me_payments_2026-10-03.xlsx", a_meesho_file(
        a_line(MEESHO_HEADER, **{"Sub Order No": "M", "Supplier SKU": "S", "Final Settlement Amount": "1", n: "-7"})))[0].sales)
    if not _got or _got[0].charges != {_id_: "7"}:
        _wrong_meesho.append(_name_)
check(f"EVERY MEESHO CHARGE COLUMN LANDS IN THE CHARGE IT IS TYPED AGAINST HERE, alone -- wrong: {_wrong_meesho}",
      not _wrong_meesho)
AMAZON_EXPECTED = {
    "selling fees": "commission", "other transaction fees": "shipping", "fba fees": "otherServices",
    "other": "otherServices", "TCS-CGST": "tcs", "TCS-SGST": "tcs", "TCS-IGST": "tcs", "TDS (Section 194-O)": "tds",
}
_wrong_amazon = []
for _name_, _id_ in AMAZON_EXPECTED.items():
    _got = answered(lambda n=_name_: read_as("az_settlements", "amazon_az_settlements_2026-09-30.csv", an_amazon_file(
        an_amazon_line("Order", "404-1", "S", "1", **{n: "-7"})))[0].sales)
    if not _got or _got[0].charges != {_id_: "7"}:
        _wrong_amazon.append(_name_)
check(f"EVERY AMAZON CHARGE COLUMN LANDS IN THE CHARGE IT IS TYPED AGAINST HERE, alone -- wrong: {_wrong_amazon}",
      not _wrong_amazon)

# ================================================================ the figures themselves

check("a figure is written with no exponent and no trailing noughts", tool.as_text(Decimal("1.50")) == "1.5"
      and tool.as_text(Decimal("1E+2")) == "100" and tool.as_text(Decimal("-0.0")) == "0")
check("and nothing is nought: an empty cell and a word are nothing, a written 0 is nought",
      tool.a_decimal("") is None and tool.a_decimal("n/a") is None and tool.a_decimal("0") == Decimal(0))
check("A FIGURE NO CELL COULD HOLD IS NOT A FIGURE: a huge exponent is nothing, not a million characters and not an overflow",
      tool.a_decimal("1E999999") is None and tool.a_decimal("1E999999999") is None and tool.a_decimal("-1E20") is None
      and tool.a_decimal("123456789.25") == Decimal("123456789.25"))
check("and a said payment's name is shown with a newline in it as an escape, never as a second log line",
      chr(10) not in str(ledger.Unmatched(name="a::b" + chr(10) + "::add-mask::x", why="w", from_report="r", on="2026-01-01")))
check("and a thousands comma does not lose the figure", tool.a_decimal("1,234.5") == Decimal("1234.5"))
check("adding two figures where one is missing is the other, not nought", tool.add_up("5", None) == "5"
      and tool.add_up(None, None) is None and tool.add_up("0.1", "0.2") == "0.3")
check("the day a payments file is read under must be a day", refused_by(
    lambda: tool.read_payments(tool.a_table_to_ask_with("amazon"), "amazon", "yesterday")))
check("and the platform must be one it knows", refused_by(
    lambda: tool.read_payments(tool.a_table_to_ask_with("amazon"), "ebay", "2026-01-01")))
check("A PAYMENTS REPORT MAY WRITE THE SETTLEMENT, THE CHARGES, ITS OWN MARKER AND WHAT BECAME OF THE ORDER (Meesho's Live Order Status), AND NO OTHER ORDER COLUMN",
      set(reading.WHAT_PAYMENTS_KNOW) == {"settlement", "paymentsOn", "whatHappened"} | set(sales.CHARGE_COLUMNS)
      and not set(reading.WHAT_PAYMENTS_KNOW) & (set(reading.WHAT_ORDERS_KNOWS) - {"whatHappened"}))
check("and every charge the ledger has is one a payments report may write",
      all(c in reading.WHAT_PAYMENTS_KNOW for c in sales.CHARGE_COLUMNS))


# ================================================================ the ledger: matching on the order id


def sheet_with(*rows):
    """A ledger as the sheet would hold it: the header and one row for each sale given."""
    return [list(sales.COLUMNS)] + [list(sales.the_row_for(r)) for r in rows]


def after(values, what):
    """The sheet as it stands once a plan has been carried out. Row numbers count the header as row 1.

    **A PLAN THAT THREW (`answered` gave None) CHANGES NOTHING HERE**, so the check after it goes red by name; failing here instead ended the whole file
    with a traceback and no FAIL line, which the proving run reads as a crash, not a catch (AP11).
    """
    out = [list(r) for r in values]
    if what is None:
        return out
    for at, cells in what.update:
        out[at - 1] = list(cells)
    for cells in what.append:
        out.append(list(cells))
    return out


def a_row(values, name):
    header = values[0]
    for cells in values[1:]:
        if cells[header.index("id")] == name:
            return dict(zip(header, cells))
    return None


def an_order(platform, order, sku, orders_on="2026-08-02", **rest):
    return sales.Sale(platform=platform, order_id=order, sku=sku, on="2026-08-01", qty="2", gmv="199",
                      status="Delivered", orders_on=orders_on, **rest)


def pays(report, day, *those, which="", aside=()):
    return ledger.Reading(report=report, on=day, knows=reading.WHAT_PAYMENTS_KNOW, sales=tuple(those), which=which or report + day,
                          only_existing=True, set_aside=aside)


def a_payment(platform, order, sku, settlement, day="2026-09-05", **charges):
    return sales.Sale(platform=platform, order_id=order, sku=sku, settlement=settlement, charges=charges, payments_on=day)


HELD = sheet_with(
    an_order("amazon", "404-1", "SKU-A"),
    an_order("amazon", "404-5", "SKU-X"),
    an_order("amazon", "404-5", "SKU-Y"),
    an_order("flipkart", "OD1", "DJ 14"),
)
_name = sales.name_for("amazon", "404-1", "SKU-A")
_p1 = answered(lambda: ledger.plan(HELD, [pays("az_settlements", "2026-09-05",
                                               a_payment("amazon", "404-1", "SKU-A", "90", commission="10", tcs="1.5"))]))
check("THE PAYMENT LANDS ON THE ROW ITS ORDER ALREADY HAS, and nothing is appended",
      _p1 is not None and len(_p1.update) == 1 and _p1.append == () and _p1.unmatched == ())
_after1 = after(HELD, _p1) if _p1 else HELD
_r = a_row(_after1, _name) or {}
check("the settlement and the charges are on it", _r.get("settlement") == "90" and _r.get("charge_commission") == "10"
      and _r.get("charge_tcs") == "1.5")
check("and the day of the file is in the payments marker, and in no other", _r.get("paymentsOn") == "2026-09-05"
      and _r.get("returnsOn") == "" and _r.get("claimsOn") == "")
check("AND NOTHING THE ORDERS FILE SAID WAS TOUCHED: quantity, price, status and the orders marker stand",
      _r.get("qty") == "2" and _r.get("gmv") == "199" and _r.get("status") == "Delivered" and _r.get("ordersOn") == "2026-08-02")
check("and the row's version is left to the ERP", _r.get("rev") == "")
check("and a charge the file did not state is still blank, never nought", _r.get("charge_penalty") == ""
      and _r.get("charge_tds") == "")
_p2 = answered(lambda: ledger.plan(_after1, [pays("az_settlements", "2026-09-05",
                                                  a_payment("amazon", "404-1", "SKU-A", "90", commission="10", tcs="1.5"))]))
check("THE SAME FILE READ AGAIN WRITES NOTHING", _p2 is not None and not _p2.changes_anything and _p2.unmatched == ())

_p3 = answered(lambda: ledger.plan(HELD, [pays("fk_payments", "2026-09-05",
                                               a_payment("flipkart", "OD99", "DJ 14", "5"))]))
check("A PAYMENT FOR AN ORDER THE LEDGER DOES NOT HOLD CREATES THE ORDER'S ROW, and is never dropped (D449)",
      _p3 is not None and len(_p3.append) == 1 and _p3.update == () and _p3.unmatched == ())
_r3 = a_row(after(HELD, _p3), sales.name_for("flipkart", "OD99", "DJ 14")) if _p3 else {}
check("AND THE ROW HAS THE MONEY AND THE DAY OF THE FILE, and nothing of the order's own columns",
      _r3 is not None and _r3.get("settlement") == "5" and _r3.get("paymentsOn") == "2026-09-05"
      and _r3.get("qty") == "" and _r3.get("ordersOn") == "" and _r3.get("whatHappened") == ""
      and (_r3.get("platform"), _r3.get("orderId"), _r3.get("sku")) == ("flipkart", "OD99", "DJ 14"))
check("and the plan's one line counts the lines left with no order to go on, nought here",
      _p3 is not None and "0 payment lines with no order to go on" in _p3.says())
_orders_later = answered(lambda: ledger.plan(after(HELD, _p3), [ledger.Reading(
    report="fk_orders", on="2026-09-06", knows=reading.WHAT_ORDERS_KNOWS, which="fk_orders-0906",
    sales=(an_order("flipkart", "OD99", "DJ 14", orders_on="2026-09-06"),))]))
_r3b = a_row(after(after(HELD, _p3), _orders_later), sales.name_for("flipkart", "OD99", "DJ 14")) if _orders_later else {}
check("WHEN THE ORDER'S OWN FILE ARRIVES IT FILLS THE SAME ROW, and the money stays",
      _orders_later is not None and len(_orders_later.append) == 0 and _r3b.get("qty") == "2" and _r3b.get("settlement") == "5")

_p4 = answered(lambda: ledger.plan(HELD, [pays("fk_payments", "2026-09-05",
                                               a_payment("flipkart", "OD1", "DJ 99", "5"))]))
check("A LINE THAT NAMES A SKU THE ORDER DOES NOT HAVE IS NOT PUT ON THE ORDER'S ONLY ROW: it CREATES its own order+SKU row (D449)",
      _p4 is not None and _p4.update == () and len(_p4.append) == 1 and _p4.unmatched == ())

_p5 = answered(lambda: ledger.plan(HELD, [pays("az_settlements", "2026-09-05",
                                               a_payment("amazon", "404-1", "", "-20", shipping="20"))]))
check("A CHARGE WITH NO SKU GOES ON ITS ORDER'S ROW WHEN THE ORDER HAS EXACTLY ONE, matched by the order id (D554, A90)",
      _p5 is not None and len(_p5.update) == 1 and _p5.unmatched == ()
      and (a_row(after(HELD, _p5), _name) or {}).get("charge_shipping") == "20"
      and (a_row(after(HELD, _p5), _name) or {}).get("settlement") == "-20")
_p5n = answered(lambda: ledger.plan(HELD, [pays("az_settlements", "2026-09-05",
                                                a_payment("amazon", "408-NOROW", "", "-28.91", otherServices="28.91"))]))
check("A CHARGE WITH NO SKU FOR AN ORDER THE LEDGER HAS NO ROW FOR IS SAID, never dropped and never put on another order (AU3 #6)",
      _p5n is not None and _p5n.update == () and _p5n.append == () and len(_p5n.unmatched) == 1
      and "no row for this order" in str(_p5n.unmatched[0]))
check("PAYMENTS NAMES NO STATUS BY HAND: it uses the shared names, so a rename can never silently stop matching (A90)",
      '"Delivered"' not in Path(tool.__file__).read_text(encoding="utf-8")
      and '"Came back"' not in Path(tool.__file__).read_text(encoding="utf-8")
      and tool.MEESHO_STATUS_MEANS == {"delivered": tool.DELIVERED, "return": tool.CAME_BACK, "rto": tool.CAME_BACK})


def _priced(sku, gmv):
    return sales.Sale(platform="amazon", order_id="404-7", sku=sku, on="2026-08-01", qty="1", gmv=gmv, status="Delivered",
                      orders_on="2026-08-02")


_TWO = sheet_with(_priced("SKU-X", "300"), _priced("SKU-Y", "100"))
_p5b = answered(lambda: ledger.plan(_TWO, [pays("az_settlements", "2026-09-05",
                                                a_payment("amazon", "404-7", "", "-28.91", otherServices="28.91"))]))
_after5b = after(_TWO, _p5b) if _p5b else _TWO
_rx = a_row(_after5b, sales.name_for("amazon", "404-7", "SKU-X")) or {}
_ry = a_row(_after5b, sales.name_for("amazon", "404-7", "SKU-Y")) or {}
check("A CHARGE WITH NO SKU FOR AN ORDER WITH SEVERAL ROWS IS SHARED BY EACH ROW'S SALE VALUE, none left off (D563, A90)",
      _p5b is not None and len(_p5b.update) == 2 and _p5b.unmatched == ()
      and _rx.get("charge_otherServices") == "21.68" and _ry.get("charge_otherServices") == "7.23")
check("AND THE SHARES ADD UP TO THE CHARGE EXACTLY, the odd paisa on the last row, and the settlement is shared the same way",
      Decimal(_rx.get("charge_otherServices", "0")) + Decimal(_ry.get("charge_otherServices", "0")) == Decimal("28.91")
      and Decimal(_rx.get("settlement", "0")) + Decimal(_ry.get("settlement", "0")) == Decimal("-28.91"))
_h5 = answered(lambda: sheet_with(_priced("SKU-X", ""), _priced("SKU-Y", "")))
_p5d = answered(lambda: ledger.plan(_h5, [pays("az_settlements", "2026-09-05",
                                               a_payment("amazon", "404-7", "", "-28.91", otherServices="28.91"))]))
check("A SHARE THAT CANNOT BE WORKED OUT (a row with no sale value) IS SAID, never guessed",
      _p5d is not None and _p5d.update == () and len(_p5d.unmatched) == 1 and "names no SKU" in str(_p5d.unmatched[0]))

# D574 (3): a no-SKU fee from a LATER file ADDS to the row's settlement, never replaces it (replacing loses money).
_paid_before = sales.Sale(platform="amazon", order_id="404-8", sku="SKU-P", on="2026-08-01", qty="1", gmv="500", status="Delivered",
                          orders_on="2026-08-02", settlement="450", charges={"commission": "50"}, payments_on="2026-09-01")
_HP = sheet_with(_paid_before)
_pn = sales.name_for("amazon", "404-8", "SKU-P")
_p5e = answered(lambda: ledger.plan(_HP, [pays("az_settlements", "2026-09-05",
                                               a_payment("amazon", "404-8", "", "-28.91", otherServices="28.91"))]))
_r5e = a_row(after(_HP, _p5e), _pn) if _p5e else {}
check("A LATER FILE'S NO-SKU FEE ADDS TO THE ROW'S SETTLEMENT AND CHARGES, never replaces them (D574 item 3, A90)",
      _r5e is not None and _r5e.get("settlement") == "421.09" and _r5e.get("charge_otherServices") == "28.91"
      and _r5e.get("charge_commission") == "50" and (_p5e is not None and _p5e.restated == ()))
_p5f = answered(lambda: ledger.plan(_HP, [pays("az_settlements", "2026-09-05",
                                               a_payment("amazon", "404-8", "SKU-P", "400", commission="60"))]))
_r5f = a_row(after(_HP, _p5f), _pn) if _p5f else {}
check("BUT A LATER FILE'S LINE THAT NAMES THE SKU STILL REPLACES, as before: it is the order's whole figure",
      _r5f is not None and _r5f.get("settlement") == "400" and _r5f.get("charge_commission") == "60")
# D575: adding a later no-SKU fee is SAFE TO RE-READ. Each fee carries its settlement id and line; a fee already on the row is never added twice.
_fee = replace(a_payment("amazon", "404-8", "", "-28.91", otherServices="28.91"), notes="fee:S1:5")
_fee_reading = pays("az_settlements", "2026-09-05", _fee)
_once = answered(lambda: ledger.plan(_HP, [_fee_reading]))
_sheet1 = after(_HP, _once) if _once else _HP
_twice = answered(lambda: ledger.plan(_sheet1, [_fee_reading]))
_sheet2 = after(_sheet1, _twice) if _twice else _sheet1
_again = answered(lambda: ledger.plan(_sheet2, [pays("az_settlements", "2026-09-06", _fee, which="az_settlements2026-09-06")]))
_sheet3 = after(_sheet2, _again) if _again else _sheet2
check("A FEE READ TWICE (a full re-read, even under another day's file) IS ADDED ONCE (D575, A90)",
      (a_row(_sheet1, _pn) or {}).get("settlement") == "421.09" and (a_row(_sheet2, _pn) or {}).get("settlement") == "421.09"
      and (a_row(_sheet3, _pn) or {}).get("settlement") == "421.09"
      and (a_row(_sheet3, _pn) or {}).get("charge_otherServices") == "28.91")
check("AND THE ROW'S NOTES KEEP THE FEE'S KEY, with whatever he typed there left in place",
      "fee:S1:5" in (a_row(_sheet1, _pn) or {}).get("notes", ""))
_other_fee = replace(a_payment("amazon", "404-8", "", "-1.09", otherServices="1.09"), notes="fee:S2:9")
_third = answered(lambda: ledger.plan(_sheet3, [pays("az_settlements", "2026-09-07", _other_fee, which="az_settlements2026-09-07")]))
check("A DIFFERENT FEE (another settlement or line) STILL ADDS",
      (a_row(after(_sheet3, _third), _pn) or {}).get("settlement") == "420" if _third else False)
_dr_bad = answered(lambda: read_as("az_settlements", "amazon_az_settlements_2026-09-30.csv", an_amazon_file(
    an_amazon_line("Order", "407-1", "SKU-A", "100", "Released", **{"fba fees": "x?"}))))
check("THE DATE RANGE READER SAYS AN UNREADABLE CHARGE, with its order and its own text (D575, Rule 29)",
      _dr_bad is not None and any("unreadable charge 407-1" in x and "'x?'" in x for x in _dr_bad[0].set_aside))
# D581 (2): a Date Range no-SKU fee is SAFE TO RE-READ too, keyed by the line's own fields so a re-download of the file reads the same.
_dr_fee_line = an_amazon_line("Shipping Services", "404-8", "", "-28.91", **{"date/time": "5 Sep 2026 10:11:12 am UTC", "other transaction fees": "-28.91"})
_dr_fee_file = lambda day: an_amazon_file(_dr_fee_line)
_dr_one = answered(lambda: read_as("az_settlements", "amazon_az_settlements_2026-09-05.csv", _dr_fee_file(1)))
_dr_two = answered(lambda: read_as("az_settlements", "amazon_az_settlements_2026-09-12.csv", _dr_fee_file(2)))
_dr_s1 = after(_HP, answered(lambda: ledger.plan(_HP, [_dr_one[0]])))
_dr_s2 = after(_dr_s1, answered(lambda: ledger.plan(_dr_s1, [_dr_one[0]])))
_dr_s3 = after(_dr_s2, answered(lambda: ledger.plan(_dr_s2, [_dr_two[0]])))
check("THE SAME DATE RANGE FILE READ TWICE, EVEN RE-DOWNLOADED UNDER ANOTHER DAY, ADDS ITS NO-SKU FEE ONCE (D581 item 2, D575)",
      (a_row(_dr_s1, _pn) or {}).get("settlement") == "421.09" and (a_row(_dr_s2, _pn) or {}).get("settlement") == "421.09"
      and (a_row(_dr_s3, _pn) or {}).get("settlement") == "421.09" and (a_row(_dr_s3, _pn) or {}).get("charge_otherServices", "") != "57.82")
_dr_other = an_amazon_line("Shipping Services", "404-8", "", "-1.09", **{"date/time": "6 Sep 2026 1:00:00 pm UTC", "other transaction fees": "-1.09"})
_dr_s4 = after(_dr_s3, answered(lambda: ledger.plan(_dr_s3, [read_as("az_settlements", "amazon_az_settlements_2026-09-13.csv",
                                                                     an_amazon_file(_dr_other))[0]])))
check("AND A DIFFERENT DATE RANGE LINE (another day or figure) STILL ADDS", (a_row(_dr_s4, _pn) or {}).get("settlement") == "420")
_dr_same_twice = read_as("az_settlements", "amazon_az_settlements_2026-09-14.csv", an_amazon_file(_dr_fee_line, _dr_fee_line))
check("TWO IDENTICAL LINES IN ONE FILE ARE TWO FEES, each with its own key",
      len({k for s in _dr_same_twice[0].sales for k in (s.notes or "").split()}) == 2)

# D581 (3): a SKU line that replaces the row's figure clears the fee keys, so a later re-read of the first fee file ADDS it back correctly.
_c_fee = replace(a_payment("amazon", "404-8", "", "-28.91", otherServices="28.91"), notes="fee:S1:5")
_c1 = after(_HP, answered(lambda: ledger.plan(_HP, [pays("az_settlements", "2026-09-05", _c_fee)])))
_c2 = after(_c1, answered(lambda: ledger.plan(_c1, [pays("az_settlements", "2026-09-07", a_payment("amazon", "404-8", "SKU-P", "400", commission="60"),
                                                          which="az_settlements2026-09-07")])))
check("A SKU LINE THAT REPLACES THE ROW'S FIGURE CLEARS THE REPLACED FEE KEYS FROM ITS NOTES (D581 item 3)",
      (a_row(_c2, _pn) or {}).get("settlement") == "400" and "fee:" not in (a_row(_c2, _pn) or {}).get("notes", ""))
_c3 = after(_c2, answered(lambda: ledger.plan(_c2, [pays("az_settlements", "2026-09-08", _c_fee, which="az_settlements2026-09-08")])))
check("AND A LATER RE-READ OF THE FIRST FEE FILE ADDS THE FEE BACK, once (D581 item 3)",
      (a_row(_c3, _pn) or {}).get("settlement") == "371.09" and "fee:S1:5" in (a_row(_c3, _pn) or {}).get("notes", ""))
_c_typed = sheet_with(replace(_paid_before, notes="call buyer fee:S1:5 keep"))
_c4 = after(_c_typed, answered(lambda: ledger.plan(_c_typed, [pays("az_settlements", "2026-09-07", a_payment("amazon", "404-8", "SKU-P", "400", commission="60"))])))
check("CLEARING THE FEE KEYS LEAVES WHAT HE TYPED IN THE NOTES", (a_row(_c4, _pn) or {}).get("notes") == "call buyer keep")
_c_word = sheet_with(replace(_paid_before, notes="fee:waived fee:200 fee:S1:5"))
_c5 = after(_c_word, answered(lambda: ledger.plan(_c_word, [pays("az_settlements", "2026-09-07", a_payment("amazon", "404-8", "SKU-P", "400", commission="60"))])))
_c_plan = answered(lambda: ledger.plan(_c1, [pays("az_settlements", "2026-09-07", a_payment("amazon", "404-8", "SKU-P", "400", commission="60"),
                                                   which="az_settlements2026-09-07")]))
check("THE CLEARED NOTES CELL IS SENT TO THE SHEET, not only changed in memory (D581 item 3)",
      _c_plan is not None and any(c == "notes" and v == "" for _, cs in _c_plan.cells for c, v in cs))
_c_two_fees = after(_c1, answered(lambda: ledger.plan(_c1, [pays("az_settlements", "2026-09-07", replace(a_payment("amazon", "404-8", "", "-1.09", otherServices="1.09"), notes="fee:S2:9"),
                                                                 which="az_settlements2026-09-07")])))
check("A SECOND FEE ADDED BESIDE THE FIRST KEEPS BOTH KEYS: adding is not replacing, so nothing is cleared",
      (a_row(_c_two_fees, _pn) or {}).get("notes") == "fee:S1:5 fee-base:450 fee:S2:9")
check("AND A WORD OF HIS OWN THAT BEGINS 'fee:' IS NOT A KEY AND STAYS", (a_row(_c5, _pn) or {}).get("notes") == "fee:waived fee:200")
# Proving (AP11): only a SKU line that changes the FIGURE is a replacement -- one that keeps the figure and changes a charge clears no fee key.
_c_charge = after(_c1, answered(lambda: ledger.plan(_c1, [pays("az_settlements", "2026-09-07", a_payment("amazon", "404-8", "SKU-P", "421.09", commission="70"),
                                                               which="az_settlements2026-09-07")])))
check("A SKU LINE THAT LEAVES THE FIGURE AS IT IS AND CHANGES A CHARGE CLEARS NO FEE KEY: the fee is still counted once",
      (a_row(_c_charge, _pn) or {}).get("settlement") == "421.09" and "fee:S1:5" in (a_row(_c_charge, _pn) or {}).get("notes", ""))

# D582: a SKU file downloaded AGAIN under a later day with the SAME figure is a re-download, not a replacement: it clears no fee key, and the fee is never lost.
_rd_sku = a_payment("amazon", "404-8", "SKU-P", "450", commission="50")
_rd1 = after(_HP, answered(lambda: ledger.plan(_HP, [pays("az_settlements", "2026-09-05", _c_fee)])))
_rd2 = after(_rd1, answered(lambda: ledger.plan(_rd1, [pays("az_settlements", "2026-09-07", _rd_sku, which="az_settlements2026-09-07")])))
_rd3 = after(_rd2, answered(lambda: ledger.plan(_rd2, [pays("az_settlements", "2026-09-08", _c_fee, which="az_settlements2026-09-08")])))
check("A SKU FILE RE-DOWNLOADED UNDER A LATER DAY WITH THE SAME FIGURE LEAVES THE EARLIER FEE COUNTED ONCE (D582, Rule 29)",
      (a_row(_rd1, _pn) or {}).get("settlement") == "421.09" and (a_row(_rd2, _pn) or {}).get("settlement") == "421.09"
      and (a_row(_rd2, _pn) or {}).get("charge_otherServices") == "28.91" and "fee:S1:5" in (a_row(_rd2, _pn) or {}).get("notes", ""))
check("AND RE-READING THE FEE FILE AFTER THAT ADDS NOTHING", (a_row(_rd3, _pn) or {}).get("settlement") == "421.09"
      and (a_row(_rd3, _pn) or {}).get("charge_otherServices") == "28.91")
_rd_new = after(_rd1, answered(lambda: ledger.plan(_rd1, [pays("az_settlements", "2026-09-07", a_payment("amazon", "404-8", "SKU-P", "400", commission="60"),
                                                                which="az_settlements2026-09-07")])))
check("BUT A SKU LINE THAT CHANGES THE FIGURE STILL REPLACES AND CLEARS THE FEE KEYS AND THE REMEMBERED FIGURE (D582)",
      (a_row(_rd_new, _pn) or {}).get("settlement") == "400" and (a_row(_rd_new, _pn) or {}).get("notes") == "")
_rd_fee2 = after(_rd1, answered(lambda: ledger.plan(_rd1, [pays("az_settlements", "2026-09-06", replace(a_payment("amazon", "404-8", "", "-1.09", otherServices="1.09"), notes="fee:S2:9"),
                                                                which="az_settlements2026-09-06")])))
_rd_fee2b = after(_rd_fee2, answered(lambda: ledger.plan(_rd_fee2, [pays("az_settlements", "2026-09-07", _rd_sku, which="az_settlements2026-09-07")])))
check("A SKU RE-DOWNLOAD AFTER TWO FEES LEAVES BOTH COUNTED (the first figure is the one remembered)",
      (a_row(_rd_fee2b, _pn) or {}).get("settlement") == "420")

# Proving (A90f): a fee whose own figure equals the remembered one still ADDS; a fee onto a row with no figure remembers nothing.
_rd_big = after(_rd1, answered(lambda: ledger.plan(_rd1, [pays("az_settlements", "2026-09-06", replace(a_payment("amazon", "404-8", "", "450", otherServices="-450"), notes="fee:S3:1"),
                                                              which="az_settlements2026-09-06")])))
check("A NEW FEE WHOSE FIGURE EQUALS THE REMEMBERED ONE IS STILL ADDED, it is not a SKU line (D582)", (a_row(_rd_big, _pn) or {}).get("settlement") == "871.09")
_blank_row = sheet_with(replace(_paid_before, settlement=""))
_rd_blank = after(_blank_row, answered(lambda: ledger.plan(_blank_row, [pays("az_settlements", "2026-09-05", _c_fee)])))
check("A FEE ONTO A ROW WITH NO FIGURE REMEMBERS NO FIGURE (nothing was added to)", "fee-base" not in (a_row(_rd_blank, _pn) or {}).get("notes", ""))

# Proving (A90d): every change a mutation could make to the fee code, each with a check that goes red for it.
_fee_two = replace(a_payment("amazon", "404-8", "", "-30", otherServices="30"), notes="fee:S1:5 fee:S1:6")
_held_noted = sheet_with(replace(_paid_before, notes="call buyer fee:S1:5"))
_part_reading = pays("az_settlements", "2026-09-05", _fee_two)
_fee_reading_one_statement = _part_reading.one_statement
_part = answered(lambda: ledger.plan(_held_noted, [_part_reading]))
check("A FILE WHOSE FEES ARE ONLY PARTLY ON THE ROW LEAVES THE ROW'S MONEY ALONE AND SAYS SO (D575)",
      _part is not None and len(_part.disagreements) == 1 and _part.disagreements[0].kept == "450"
      and _part.disagreements[0].column == "settlement"
      and _part.disagreements[0].kept_from == ledger.THE_SHEET_REMEMBERS and _part.disagreements[0].also_from == _fee_reading_one_statement
      and (a_row(after(_held_noted, _part), _pn) or {}).get("settlement") == "450")
_all_seen = answered(lambda: ledger.plan(_held_noted, [pays("az_settlements", "2026-09-05", replace(_fee_two, notes="fee:S1:5"))]))
check("AND A FILE WHOSE FEES ARE ALL ON THE ROW SAYS NOTHING ABOUT IT",
      _all_seen is not None and _all_seen.disagreements == ()
      and (a_row(after(_held_noted, _all_seen), _pn) or {}).get("settlement") == "450")
_first_fee = replace(a_payment("amazon", "404-8", "", "-28.91", otherServices="28.91"), notes="fee:S1:5")
_then_sku = a_payment("amazon", "404-8", "SKU-P", "400", commission="60")
_both = answered(lambda: ledger.plan(_HP, [pays("az_settlements", "2026-09-05", _first_fee, _then_sku)]))
check("A FILE THAT NAMES THE SKU AS WELL AS CARRYING A NO-SKU FEE REPLACES THE ROW'S FIGURE, never adds to it (D574 item 3)",
      _both is not None and (a_row(after(_HP, _both), _pn) or {}).get("settlement") == "371.09")
_typed = sheet_with(replace(_paid_before, notes="call buyer"))
_keep = answered(lambda: ledger.plan(_typed, [_fee_reading]))
check("THE FEE'S KEY GOES BESIDE WHATEVER HE TYPED IN THE ROW'S NOTES, which stays",
      _keep is not None and (a_row(after(_typed, _keep), _pn) or {}).get("notes") == "call buyer fee:S1:5 fee-base:450")
_zero_fee = replace(a_payment("amazon", "404-8", "", "0"), notes="fee:S3:1")
_zero = answered(lambda: ledger.plan(_HP, [pays("az_settlements", "2026-09-01", replace(_zero_fee, payments_on="2026-09-01"))]))
check("A FEE THAT CHANGES NO FIGURE STILL WRITES ITS KEY, so the row is updated and the notes cell is sent",
      _zero is not None and len(_zero.update) == 1 and (a_row(after(_HP, _zero), _pn) or {}).get("settlement") == "450"
      and "fee:S3:1" in (a_row(after(_HP, _zero), _pn) or {}).get("notes", "")
      and any(c == "notes" for _, cs in _zero.cells for c, _v in cs))
_shape = [list(r) for r in _HP]
_shape[1][_shape[0].index("settlement")] = "n/a"
_odd = answered(lambda: ledger.plan(_shape, [_fee_reading]))
check("A SETTLEMENT ON THE ROW THAT IS NOT A FIGURE IS LEFT TO THE ORDINARY RULE, not added to and not a crash",
      _odd is not None and (a_row(after(_shape, _odd), _pn) or {}).get("settlement") == "-28.91")
_two_paid = sheet_with(replace(_priced("SKU-X", "300"), settlement="250", payments_on="2026-09-01"),
                       replace(_priced("SKU-Y", "100"), settlement="100", payments_on="2026-09-01"))
_sh_add = answered(lambda: ledger.plan(_two_paid, [pays("az_settlements", "2026-09-05",
                                                        a_payment("amazon", "404-7", "", "-28.91", otherServices="28.91"))]))
_sx = a_row(after(_two_paid, _sh_add), sales.name_for("amazon", "404-7", "SKU-X")) if _sh_add else {}
_sy = a_row(after(_two_paid, _sh_add), sales.name_for("amazon", "404-7", "SKU-Y")) if _sh_add else {}
check("A SHARED FEE ADDS TO EACH ROW'S SETTLEMENT, never replaces it (D563 with D574 item 3)",
      _sx is not None and _sy is not None and _sx.get("settlement") == "228.32" and _sy.get("settlement") == "92.77")
_now_plain = {sales.name_for("amazon", "404-8", "SKU-P"): dict(zip(_HP[0], _HP[1]))}
_got = answered(lambda: ledger._put_each_on_its_row(pays("az_settlements", "2026-09-05", _first_fee), _now_plain, set()))
check("PLACING A LINE WORKS WITHOUT ASKING WHICH ROWS WERE REACHED ONLY BY A FEE", _got is not None and len(_got[0]) == 1)
_shared_one = ledger.SharedCharge(order_id="404-7", amount="-28.91", rows=("a",), from_report="r", on="2026-09-05")
try:
    _shared_one.amount = "1"
    _frozen = False
except Exception:  # noqa: BLE001
    _frozen = True
check("A SHARED CHARGE'S RECORD CANNOT BE CHANGED AFTER IT IS MADE", _frozen)
_fee_a = replace(a_payment("amazon", "404-8", "", "-28.91", otherServices="28.91"), notes="fee:S1:5")
_fee_b = replace(a_payment("amazon", "404-8", "", "-1.09", otherServices="1.09"), notes="fee:S1:6")
_two_fees = answered(lambda: ledger.plan(_HP, [pays("az_settlements", "2026-09-05", _fee_a, _fee_b)]))
_r_two = a_row(after(_HP, _two_fees), _pn) if _two_fees else {}
check("TWO NO-SKU FEES OF ONE FILE ON ONE ROW ARE ADDED TOGETHER AND BOTH KEYS ARE KEPT (D575)",
      _r_two is not None and _r_two.get("settlement") == "420" and _r_two.get("notes") == "fee:S1:5 fee:S1:6 fee-base:450")
_dr_blank = answered(lambda: read_as("az_settlements", "amazon_az_settlements_2026-09-30.csv", an_amazon_file(
    an_amazon_line("Order", "407-2", "SKU-A", "100", "Released", **{"fba fees": ""}))))
check("A BLANK CHARGE CELL IN THE DATE RANGE REPORT IS NOT SAID TO BE UNREADABLE (it is a blank)",
      _dr_blank is not None and not any("unreadable charge" in x for x in _dr_blank[0].set_aside))
_p7 = answered(lambda: ledger.plan(HELD, [pays("az_settlements", "2026-09-05",
                                               a_payment("amazon", "404-1", "SKU-A", "100", commission="10"),
                                               a_payment("amazon", "404-1", "SKU-A", "-20", shipping="20"))]))
_r7 = a_row(after(HELD, _p7), _name) if _p7 else {}
check("TWO LINES OF ONE FILE FOR ONE ROW ARE ADDED TOGETHER, not left to overwrite each other",
      _r7 is not None and _r7.get("settlement") == "80" and _r7.get("charge_commission") == "10"
      and _r7.get("charge_shipping") == "20")

# ------------------------------------------------------- rule 2: the newest file wins, and a blank never overwrites

_newer = answered(lambda: ledger.plan(HELD, [pays("az_settlements", "2026-09-10",
                                                  a_payment("amazon", "404-1", "SKU-A", "95", "2026-09-10"))]))
_older = answered(lambda: ledger.plan(after(HELD, _newer), [pays("az_settlements", "2026-09-05",
                                                                 a_payment("amazon", "404-1", "SKU-A", "90"))]))
check("A PAYMENTS FILE OLDER THAN THE ONE THAT LAST WROTE THE ROW DOES NOT UNDO IT, and says so",
      _older is not None and _older.update == () and len(_older.left_alone) == 1)
check("and an orders file dated later does not hold a payments file back (its own marker only)",
      answered(lambda: ledger.plan(sheet_with(an_order("amazon", "404-1", "SKU-A", orders_on="2026-12-01")),
                                   [pays("az_settlements", "2026-09-05", a_payment("amazon", "404-1", "SKU-A", "90"))])
               ).update != ())
_blank = answered(lambda: ledger.plan(after(HELD, _p1), [pays("az_settlements", "2026-09-20", sales.Sale(
    platform="amazon", order_id="404-1", sku="SKU-A", settlement=None, charges={"shipping": "3"}, payments_on="2026-09-20"))]))
_rb = a_row(after(after(HELD, _p1), _blank), _name) if _blank else {}
check("A LATER FILE THAT SAYS NO SETTLEMENT DOES NOT BLANK THE ONE THERE", _rb.get("settlement") == "90"
      and _rb.get("charge_shipping") == "3" and _rb.get("charge_commission") == "10")
_tie = answered(lambda: ledger.plan(after(HELD, _p1), [pays("az_settlements", "2026-09-05",
                                                            a_payment("amazon", "404-1", "SKU-A", "91"), which="another")]))
check("TWO FILES OF ONE DAY DISAGREEING ARE A TIE: kept and reported, as for any other report",
      _tie is not None and len(_tie.disagreements) >= 1 and (a_row(after(after(HELD, _p1), _tie), _name) or {}).get("settlement") == "90")
_cannot = ledger.Reading(report="me_payments", on="2026-09-05", knows=reading.WHAT_PAYMENTS_KNOW, only_existing=True,
                         sales=(sales.Sale(platform="amazon", order_id="404-1", sku="SKU-A", qty="9", gmv="1",
                                           settlement="1", payments_on="2026-09-05"),))
_rc = a_row(after(HELD, ledger.plan(HELD, [_cannot])), _name) or {}
check("RULE 1: A PAYMENTS FILE CANNOT WRITE WHAT WAS SOLD, however its sale was built", _rc.get("qty") == "2"
      and _rc.get("gmv") == "199" and _rc.get("settlement") == "1")
check("a payments reading with nothing in its payments marker is refused when it is built",
      refused_by(lambda: ledger.Reading(report="me_payments", on="2026-09-05", knows=reading.WHAT_PAYMENTS_KNOW,
                                        sales=(sales.Sale(platform="amazon", order_id="x", settlement="1"),))))

# ------------------------------------------------------- a newer file that changes a settlement is said

_first = answered(lambda: ledger.plan(HELD, [pays("az_settlements", "2026-09-05", a_payment("amazon", "404-1", "SKU-A", "90"))]))
_second = answered(lambda: ledger.plan(after(HELD, _first), [pays("fk_payments", "2026-09-12",
                                                                  a_payment("amazon", "404-1", "SKU-A", "-20", "2026-09-12"))]))
check("A NEWER FILE THAT PUTS ANOTHER SETTLEMENT OVER AN EARLIER ONE IS SAID, both figures and the file -- it may be only part of the order",
      _second is not None and len(_second.restated) == 1 and "90" in str(_second.restated[0])
      and "-20" in str(_second.restated[0]) and "1 settlements restated" in _second.says())
check("and the newest still wins, as D150 rule 2 says", (a_row(after(after(HELD, _first), _second), _name) or {}).get("settlement") == "-20")
check("and a first settlement, or the same figure again, is not a restatement",
      _first is not None and _first.restated == () and answered(lambda: ledger.plan(after(HELD, _first), [pays(
          "fk_payments", "2026-09-12", a_payment("amazon", "404-1", "SKU-A", "90", "2026-09-12"))])).restated == ())

# ------------------------------------------------------- payments are applied after orders, whatever day each is about

_order_how = next(o for o in reading.WHAT_CAN_BE_READ if o.report_id == "me_orders")
_pay_how = next(o for o in reading.WHAT_CAN_BE_READ if o.report_id == "fk_payments")
_ordered = reading._oldest_first(
    {"me_orders": [a_folder_file("o-1", "meesho_me_orders_2026-09-03.csv")],
     "fk_payments": [a_folder_file("p-1", "flipkart_fk_payments_2026-08-28.xlsx")]},
    (_order_how, _pay_how), ())
check("A PAYMENTS FILE DATED BEFORE AN ORDERS FILE IS STILL APPLIED AFTER IT, so a catch-up night does not settle orders it has not yet read",
      [one.which for _, one in _ordered] == ["o-1", "p-1"])
_two = reading._oldest_first(
    {"fk_payments": [a_folder_file("p-2", "flipkart_fk_payments_2026-09-02.xlsx"), a_folder_file("p-1", "flipkart_fk_payments_2026-08-28.xlsx")]},
    (_pay_how,), ())
check("and payments files among themselves are still oldest first", [one.which for _, one in _two] == ["p-1", "p-2"])

# ------------------------------------------------------- a payment to a row the sheet holds twice is not written

_twice = sheet_with(an_order("amazon", "404-1", "SKU-A"), an_order("amazon", "404-1", "SKU-A"))
_pt = answered(lambda: ledger.plan(_twice, [pays("az_settlements", "2026-09-05", a_payment("amazon", "404-1", "SKU-A", "9"))]))
check("A ROW THE SHEET HOLDS TWICE IS LEFT ALONE BY A PAYMENT TOO", _pt is not None and _pt.update == () and _pt.append == ())

# ================================================================ the whole night, through the real reader


class TheSheet:
    """The seller's ledger in memory, written the way the real door writes it."""

    def __init__(self, values):
        self.values = [list(r) for r in values]
        self.said = []

    def everything(self):
        return [list(r) for r in self.values]

    def carry_out(self, what):
        self.values = after(self.values, what)
        return {"added": len(what.append), "changed": len(what.update)}


def a_night(the_sheet, files, bodies, already=()):
    record = ledger_sheet.recording_into(the_sheet, the_sheet.said.append)
    return reading.read_what_is_new(
        already_read=already,
        what_is_in_the_folder=lambda report: list(files.get(report, ())),
        bring_it_back=lambda which: bodies[which],
        record_the_sales=record,
    )


_said5 = []
answered(lambda: ledger_sheet.recording_into(TheSheet([list(r) for r in _TWO]), _said5.append)([pays(
    "az_settlements", "2026-09-05", a_payment("amazon", "404-7", "", "-28.91", otherServices="28.91"))]))
check("EACH SHARED CHARGE IS LISTED IN THE NIGHT'S OWN WORDS: the order, the amount and how it was split (D563 as amended)",
      _p5b is not None and len(_p5b.shared) == 1
      and any(x.startswith("SALES LEDGER SHARED ORDER CHARGE") and "404-7" in x and "28.91" in x and "sale value" in x for x in _said5)
      and any("split may change when more items land" in x for x in _said5))

_the = TheSheet(sheet_with(
    an_order("amazon", "404-1", "SKU-A"), an_order("amazon", "404-5", "SKU-X"), an_order("amazon", "404-5", "SKU-Y"),
    an_order("flipkart", "OD1", "DJ 14"), an_order("flipkart", "OD2", "DJ 14"),
    an_order("meesho", "M1_1", "SKU-M"),
))
_files = {
    "az_settlements": [a_folder_file("as-1", "amazon_az_settlements_2026-09-30.csv")],
    "fk_payments": [a_folder_file("fp-1", "flipkart_fk_payments_2026-08-28.xlsx")],
    "me_payments": [a_folder_file("mp-1", "meesho_me_payments_2026-10-03.xlsx")],
}
_bodies = {"as-1": AMAZON_BODY, "fp-1": FLIPKART_BODY, "mp-1": MEESHO_BODY}
_n1 = answered(lambda: a_night(_the, _files, _bodies))
_mine = {n: a_row(_the.values, sales.name_for(*n)) or {} for n in [
    ("amazon", "404-1", "SKU-A"), ("flipkart", "OD1", "DJ 14"), ("flipkart", "OD2", "DJ 14"), ("meesho", "M1_1", "SKU-M")]}
check("THREE PLATFORMS' PAYMENT FILES, THROUGH THE REAL READER AND THE REAL LEDGER, FILL THE MATCHING ROWS",
      _n1 is not None and _n1.read_tonight and len(_n1.read_tonight) == 3
      and _mine[("amazon", "404-1", "SKU-A")].get("settlement") == "80.5"
      and _mine[("flipkart", "OD1", "DJ 14")].get("settlement") == "-300.5"
      and _mine[("flipkart", "OD2", "DJ 14")].get("charge_penalty") == "7"
      and _mine[("meesho", "M1_1", "SKU-M")].get("charge_fixedFee") == "4")
# **D449 (A87): A PAYMENT THAT ARRIVES BEFORE ITS ORDER CREATES THE ORDER'S ROW, so no payments file waits for orders any more.** (OD1/DJ 15 and
# M2_1 have no row: each gets one, with the money on it and nothing of the order's.)
check("every file is written down as read, so none is read again, and none is left waiting for its orders", _n1 is not None
      and set(_n1.files_read) == {"as-1", "fp-1", "mp-1"} and _n1.payments_waiting == 0 and not _n1.payment_files_waiting)
_created = {n: a_row(_the.values, sales.name_for(*n)) or {} for n in [("flipkart", "OD1", "DJ 15"), ("meesho", "M2_1", "SKU-N")]}
check("AND THE TWO PAYMENTS WITH NO ORDER LINE YET HAVE THEIR OWN ROWS, with money and no order columns",
      len(_the.values) == 12 and all(r.get("settlement") not in (None, "") and r.get("qty") == "" for r in _created.values()))
check("the lines set aside and the payment with no SKU to key a row by are said in the night's own words",
      any("PAYMENT WITH NO ORDER" in x and "404-6" in x for x in _the.said)
      and any("SET ASIDE" in x and "Transfer" in x for x in _the.said)
      and any("SET ASIDE" in x and "Deferred" in x for x in _the.said))
check("and the manifest has a line for each of the three files read", _n1 is not None and len(_n1.reads) == 3)
_before = [list(r) for r in _the.values]
_n2 = answered(lambda: a_night(_the, _files, _bodies, already=_n1.files_read if _n1 else ()))
check("A SECOND NIGHT OVER THE SAME FILES WRITES NOTHING", _n2 is not None and _n2.read_tonight == () and _the.values == _before)
_n3 = answered(lambda: a_night(_the, _files, _bodies))
check("AND READ AGAIN FROM SCRATCH, THE SAME FILES CHANGE NOTHING IN THE SHEET (the re-read is idempotent)",
      _n3 is not None and _the.values == _before)

# **THE CATCH-UP NIGHT, WHOLE:** the payments file is about an EARLIER day than the orders file that makes its row, and both are new.
_empty_sheet = TheSheet([list(sales.COLUMNS)])
_orders_text = ("Sub Order No,SKU,Quantity,Order Date,Reason for Credit Entry,Supplier Discounted Price (Incl GST and Commision)"
                + chr(10) + "M1_1,SKU-M,1,2026-09-30 10:00:00,SHIPPED,199" + chr(10)).encode("utf-8")
_catch_up = answered(lambda: a_night(
    _empty_sheet,
    {"me_orders": [a_folder_file("o-1", "meesho_me_orders_2026-10-05.csv")],
     "me_payments": [a_folder_file("mp-1", "meesho_me_payments_2026-10-03.xlsx")]},
    {"o-1": _orders_text, "mp-1": MEESHO_BODY}))
_caught = a_row(_empty_sheet.values, sales.name_for("meesho", "M1_1", "SKU-M")) or {}
check("A PAYMENTS FILE OLDER THAN THE ORDERS IT SETTLES FILLS THEIR ROW WHEN BOTH ARE NEW TOGETHER, and M2_1 (no order file) has its own row",
      _catch_up is not None and _caught.get("settlement") == "150" and _caught.get("charge_commission") == "20"
      and _caught.get("qty") == "1" and set(_catch_up.files_read) == {"o-1", "mp-1"} and _catch_up.payments_waiting == 0
      and a_row(_empty_sheet.values, sales.name_for("meesho", "M2_1", "SKU-N")) is not None)

# ================================================================ the guard that refuses to write

check("every report is read, or says why not -- and the three payments reports are now read",
      reading.why_a_report_has_no_decision() == ""
      and all(r in reading.what_this_can_read() for r in ("az_settlements", "fk_payments", "me_payments"))
      and not any(r in reading.WHAT_IS_FETCHED_AND_NOT_READ_YET for r in ("az_settlements", "fk_payments", "me_payments")))
check("with the real readers the night is not refused", ledger_sheet.why_it_must_not_write_yet() == "")
_the_real = tool.read_payments


def _fills_no_marker(rows, platform, data_date):
    return _no_marker(_the_real(rows, platform, data_date))


def _no_marker(paid):
    from dataclasses import replace
    return tool.WhatWasPaid(paid.platform, tuple(replace(s, payments_on=None) for s in paid.sales), paid.not_read, paid.set_aside)


def _says_one_fixed_day(rows, platform, data_date):
    from dataclasses import replace
    paid = _the_real(rows, platform, data_date)
    return tool.WhatWasPaid(paid.platform, tuple(replace(s, payments_on="2026-09-08") for s in paid.sales), paid.not_read, paid.set_aside)


tool.read_payments = _fills_no_marker
_refused_no_marker = ledger_sheet.why_it_must_not_write_yet()
tool.read_payments = _says_one_fixed_day
_refused_fixed = ledger_sheet.why_it_must_not_write_yet()
tool.read_payments = _the_real
check("A PAYMENTS READER THAT PUTS NO DAY IN ITS MARKER IS REFUSED, and the refusal names the payments reports",
      _refused_no_marker != "" and all(r in _refused_no_marker for r in ("az_settlements", "fk_payments", "me_payments")))
check("A PAYMENTS READER THAT CLAIMS EVERY FILE IS ONE FIXED DAY IS REFUSED TOO", _refused_fixed != "")
check("and with the real reader back, nothing is refused again", ledger_sheet.why_it_must_not_write_yet() == "")


# ================================================================ his real files, if they are here: SHAPE ONLY

def his(name):
    one = SAMPLES / name
    return one.read_bytes() if one.is_file() else None


_real_az = his("2026Sep1-2026Sep30CustomUnifiedTransaction.csv")
_real_fk = his("flipkart_payments_2026-08-28.xlsx")
_real_me = his("meesho_payments_2026-10-03.xlsx")
real_ran = 0
if _real_az is not None:
    got = answered(lambda: read_as("az_settlements", "amazon_az_settlements_2026-09-30.csv", _real_az))
    rd = got[0] if got else None
    # An independent sum, written differently: the csv module, no helper from this package.
    text = _real_az.decode("utf-8-sig").replace("\r\r\n", "\n").replace("\r\n", "\n")
    rows = list(csv.reader(io.StringIO(text)))
    at = next(i for i, r in enumerate(rows) if r and r[0].lower() == "date/time")
    head = rows[at]
    total = sum(Decimal(r[head.index("total")] or 0) for r in rows[at + 1:]
                if len(r) == len(head) and r[head.index("order id")].strip() and r[head.index("Transaction Status")] == "Released")
    check("HIS REAL AMAZON FILE: every released order line's money is on a sale, and the sum is the file's own, to the paisa",
          rd is not None and rd.sales and sum(Decimal(s.settlement) for s in rd.sales if s.settlement is not None) == total)
    check("HIS REAL AMAZON FILE: the payouts and service fees are set aside, and every sale names an order",
          rd is not None and any("Transfer" in x for x in rd.set_aside) and all(s.order_id for s in rd.sales))
    real_ran += 2
_real_v2 = his("amazon_az_settlements_2026-09-08.csv")
if _real_v2 is not None:
    got = answered(lambda: read_as("az_settlements", "amazon_az_settlements_2026-09-08.csv", _real_v2))
    rd = got[0] if got else None
    # An independent sum, written differently: the csv module, tab-separated, no helper from this package.
    vrows = list(csv.reader(io.StringIO(_real_v2.decode("utf-8-sig").replace("\r\n", "\n")), delimiter="\t", quoting=csv.QUOTE_NONE))
    vhead = vrows[0]
    vall = sum(Decimal(r[vhead.index("amount")] or 0) for r in vrows[1:] if len(r) == len(vhead))
    vsales = sum(Decimal(s.settlement) for s in rd.sales if s.settlement is not None) if rd else None
    vaside = sum(Decimal(r[vhead.index("amount")] or 0) for r in vrows[1:]
                 if len(r) == len(vhead) and not r[vhead.index("order-id")].strip())
    check("HIS REAL SETTLEMENT FILE: the money on the sales plus the lines with no order is the file's own total-amount, to the paisa",
          rd is not None and bool(rd.sales) and got[1] == 0
          and vsales + vaside == Decimal(vrows[1][vhead.index("total-amount")]) == vall)
    check("HIS REAL SETTLEMENT FILE: the advertising line is said, and every sale names an order",
          rd is not None and all(s.order_id for s in rd.sales) and any("Cost of Advertising" in x for x in rd.set_aside))
    real_ran += 2
if _real_fk is not None:
    got = answered(lambda: read_as("fk_payments", "flipkart_fk_payments_2026-08-28.xlsx", _real_fk))
    rd = got[0] if got else None
    check("HIS REAL FLIPKART FILE: every order line is a sale, none refused, and each carries a settlement",
          rd is not None and len(rd.sales) > 50 and got[1] == 0 and all(s.settlement is not None for s in rd.sales))
    real_ran += 1
if _real_me is not None:
    got = answered(lambda: read_as("me_payments", "meesho_me_payments_2026-10-03.xlsx", _real_me))
    rd = got[0] if got else None
    check("HIS REAL MEESHO FILE: every order line is a sale, none refused, and each carries a settlement",
          rd is not None and len(rd.sales) >= 10 and got[1] == 0 and all(s.settlement is not None for s in rd.sales))
    real_ran += 1

# ================================================================ the other sheets (job 15 c)

# **MEESHO: THE RETURN PREMIUM.** Two columns in the revenue block, the platform's sign turned over, the two added.
_prem = answered(lambda: read_as("me_payments", "meesho_me_payments_2026-10-03.xlsx", a_meesho_file(
    a_meesho_line("MP1", "SKU-P", "100", returnPremium="-30", returnPremiumOfReturn="-5"),
    a_meesho_line("MP2", "SKU-P", "100", returnPremium="0"),
    a_meesho_line("MP3", "SKU-P", "100"),
)))
_prem_sales = {s.order_id: s for s in (_prem[0].sales if _prem else ())}
check("MEESHO: the return premium is a charge, the two columns added, the platform's sign turned over",
      _prem is not None and _prem_sales["MP1"].charges.get("returnPremium") == "35")
check("and a real nought is written as a nought",
      _prem is not None and _prem_sales["MP2"].charges.get("returnPremium") == "0")
check("and a blank is left out, never written as nought",
      _prem is not None and "returnPremium" not in _prem_sales["MP3"].charges)
check("and a file that has lost a premium column is refused, naming it",
      refused_by(lambda: read_as("me_payments", "meesho_me_payments_2026-10-03.xlsx", a_meesho_file(
          a_meesho_line("MP1", "SKU-P", "100"), rename={"Return premium (incl GST) of Return": "Return premium (renamed)"}))))


def a_two_row_sheet(columns, *lines):
    return [["Payment Details"] + [""] * (len(columns) - 1), columns] + [list(l) for l in lines]


def with_more_sheets(body_sheets, extra):
    """A real workbook: the sheets of a made payments file plus these, by name."""
    return a_spreadsheet(body_sheets + extra)


FK_ORDERS_SHEET = ("Orders", [["Payment Details"] + [""] * (len(FLIPKART_HEADER) - 1), FLIPKART_HEADER,
                              ["", "", "", "sub-heading"] + [""] * (len(FLIPKART_HEADER) - 4),
                              a_flipkart_line("OD1", "DJ 14", "-300", commission="-40"),
                              a_flipkart_line("OD2", "DJ 15", "50")])
_REBATE_COLUMNS = ["NEFT ID", "Neft Type", " Payment Date", "Settlement Value (Rs.)", "SKU", "Order ID", "Order item ID",
                   "Order Date", "Rebate Processing Date"]
_FINES_COLUMNS = ["NEFT ID", "Payment Date", "Settlement Value(Rs.) ", "Transaction Name", "Transaction Details"]
_fk_more = answered(lambda: read_as("fk_payments", "flipkart_fk_payments_2026-08-28.xlsx", with_more_sheets(
    [("Report Help", [["How to read"]]), FK_ORDERS_SHEET],
    [("MP Fee Rebate", a_two_row_sheet(_REBATE_COLUMNS,
        ["N1", "NEFT", "2026-08-01", "12.5", "DJ 14", "OD1", "OI1", "2026-07-01", "2026-08-01"],
        ["N1", "NEFT", "2026-08-01", "3", "DJ 99", "OD404", "OI2", "2026-07-01", "2026-08-01"],
        ["N1", "NEFT", "2026-08-01", "4", "DJ 98", "", "OI3", "2026-07-01", "2026-08-01"])),
     ("Fines", a_two_row_sheet(_FINES_COLUMNS, ["N2", "2026-08-02", "-100", "Late", "x"], ["N2", "2026-08-02", "-50", "Late", "y"])),
     ("TDS", a_two_row_sheet(["NEFT ID", "Payment Date", "Settlement Value (Rs.)", "ID", "Claim Date"])),
     ("GST_Details", [["Transaction Summary"], ["Service Type", "Amount (Rs.)"], ["x", "9"]])],
)))
_fk_more_reading = _fk_more[0] if _fk_more else None
_fk_more_sales = {(s.order_id, s.sku): s for s in (_fk_more_reading.sales if _fk_more_reading else ())}
check("FLIPKART: a marketplace fee rebate is added to its order's settlement",
      _fk_more_reading is not None and _fk_more_sales[("OD1", "DJ 14")].settlement == "-287.5")
check("and taken off its other charges, as a fee given back is a negative charge",
      _fk_more_reading is not None and _fk_more_sales[("OD1", "DJ 14")].charges.get("otherServices") == "-12.5")
check("and the order's other charges are still there beside it",
      _fk_more_reading is not None and _fk_more_sales[("OD1", "DJ 14")].charges.get("commission") == "40")
check("a rebate for an order this file does not otherwise state is LEFT OUT AND SAID, so it cannot replace that order's money",
      _fk_more_reading is not None and ("OD404", "DJ 99") not in _fk_more_sales
      and any("does not otherwise state" in x for x in _fk_more_reading.set_aside))
check("a rebate line with no order id is said and makes no line",
      _fk_more_reading is not None and any("rebate line" in x and "no order id" in x for x in _fk_more_reading.set_aside)
      and len(_fk_more_sales) == 2)
check("a sheet that belongs to no sale is said by name and by how many lines carried a figure, never by amount",
      _fk_more_reading is not None and any(x == "2 line(s) in the 'Fines' sheet, which belong to no sale"
                                           for x in _fk_more_reading.set_aside)
      and not any("100" in x for x in _fk_more_reading.set_aside))
check("and a sheet with nothing in it is not mentioned", _fk_more_reading is not None
      and not any("TDS" in x for x in _fk_more_reading.set_aside))
check("and a sheet that is not money is not read at all", _fk_more_reading is not None
      and not any("GST_Details" in x for x in _fk_more_reading.set_aside))
check("the orders sheet's own figures are unchanged by the sheets beside it",
      _fk_more_reading is not None and _fk_more_sales[("OD2", "DJ 15")].settlement == "50")

_fk_no_extras = answered(lambda: read_as("fk_payments", "flipkart_fk_payments_2026-08-28.xlsx", a_spreadsheet([FK_ORDERS_SHEET])))
check("a workbook without the other sheets reads exactly as before, with nothing said",
      _fk_no_extras is not None and _fk_no_extras[0].set_aside == ())

_fk_bad_sheet = answered(lambda: read_as("fk_payments", "flipkart_fk_payments_2026-08-28.xlsx", a_spreadsheet(
    [FK_ORDERS_SHEET, ("Fines", [["only one row"]])])))
check("a sheet that will not read does not stop the orders' money, and is said",
      _fk_bad_sheet is not None and len(_fk_bad_sheet[0].sales) == 2
      and any("'Fines' sheet could not be read" in x for x in _fk_bad_sheet[0].set_aside))
check("a rebate sheet that will not read at all REFUSES THE FILE too, so the same fault is not sometimes said and sometimes refused",
      refused_by(lambda: read_as("fk_payments", "flipkart_fk_payments_2026-08-28.xlsx", a_spreadsheet(
          [FK_ORDERS_SHEET, ("MP Fee Rebate", [["only one row"]])]))))
check("a rebate sheet whose columns moved REFUSES THE FILE, so the file is read again once it is mended and no rebate is lost",
      refused_by(lambda: read_as("fk_payments", "flipkart_fk_payments_2026-08-28.xlsx", a_spreadsheet(
          [FK_ORDERS_SHEET, ("MP Fee Rebate", a_two_row_sheet(["NEFT ID", "Something else"], ["N1", "5"]))]))))

_fk_two_amounts = answered(lambda: read_as("fk_payments", "flipkart_fk_payments_2026-08-28.xlsx", a_spreadsheet(
    [FK_ORDERS_SHEET, ("Fines", a_two_row_sheet(["NEFT ID", "Settlement Value (Rs.)", "Settlement Value(Rs.)"], ["N", "1", "2"]))])))
check("a sheet with two columns that could state its money is said as uncountable, not counted from one of them",
      _fk_two_amounts is not None and any("'Fines' sheet has 2 columns" in x for x in _fk_two_amounts[0].set_aside))

_ME_ADS = ["Deduction Duration", "Deduction Date", "Campaign ID", "Ad Cost", "Credits / Waivers / Discounts",
           "Ad Cost incl. Credits/Waivers/Discounts", "GST", "Total Ads Cost"]
_me_more = answered(lambda: read_as("me_payments", "meesho_me_payments_2026-10-03.xlsx", a_spreadsheet([
    ("Disclaimer", [["Meesho"]]),
    ("Order Payments", [["Order Related Details"] + [""] * (len(MEESHO_HEADER) - 1), MEESHO_HEADER,
                        [""] * len(MEESHO_HEADER), a_meesho_line("MX1", "SKU-M", "100", commission="-10")]),
    ("Ads Cost", [["Ads Cost"], _ME_ADS, ["", "", "", "A", "B", "(A + B)"],
                  ["1-7 Aug", "2026-08-07", "C1", "10", "0", "10", "1.8", "11.8"],
                  ["8-14 Aug", "2026-08-14", "C2", "20", "0", "20", "3.6", "23.6"]]),
    ("Referral Payments", [["Referral Payments"], ["Reward Id", "Payment Date", "Store Name", "Reason", "Net Referral Amount",
                                                   "Taxes (GST/TDS)"], [], ["No data is available for these dates."]]),
    ("Compensation and Recovery", [["Platform Recovery & Compensation"], ["Date", "Program Name", "Reason", "Amount (inc GST) INR"],
                                   ["2026-08-03", "P", "R", "-40"]]),
])))
_me_more_reading = _me_more[0] if _me_more else None
check("MEESHO: the orders sheet is still read beside the other sheets", _me_more_reading is not None
      and len(_me_more_reading.sales) == 1 and _me_more_reading.sales[0].charges.get("commission") == "10")
check("the ads cost sheet is said by how many lines carried a figure; the formula row under the names is not one",
      _me_more_reading is not None and "2 line(s) in the 'Ads Cost' sheet, which belong to no sale" in _me_more_reading.set_aside)
check("the compensation and recovery sheet is said too", _me_more_reading is not None
      and "1 line(s) in the 'Compensation and Recovery' sheet, which belong to no sale" in _me_more_reading.set_aside)
check("and a sheet that says no data is available is not said at all",
      _me_more_reading is not None and not any("Referral" in x for x in _me_more_reading.set_aside))

# ================================================================ AMAZON'S SETTLEMENT FILE (job 18)

# **THE FILE THE RUN ACTUALLY FETCHES** (`GET_V2_SETTLEMENT_REPORT_DATA_FLAT_FILE_V2`): tab-separated, the header on line 1, one
# line per money line (order, SKU, amount-type, amount-description, amount). The 24 column names are the ones his real file of
# 2026-09-08 carries. Every figure below is made up.
V2_COLUMNS = ["settlement-id", "settlement-start-date", "settlement-end-date", "deposit-date", "total-amount", "currency",
              "transaction-type", "order-id", "merchant-order-id", "adjustment-id", "shipment-id", "marketplace-name",
              "amount-type", "amount-description", "amount", "fulfillment-id", "posted-date", "posted-date-time",
              "order-item-code", "merchant-order-item-id", "merchant-adjustment-item-id", "sku", "quantity-purchased",
              "promotion-id"]


def a_v2_line(kind, order, sku, amount_type, description, amount, sid="1"):
    cells = {"settlement-id": sid, "transaction-type": kind, "order-id": order, "amount-type": amount_type,
             "amount-description": description, "amount": amount, "sku": sku}
    return "\t".join(cells.get(c, "") for c in V2_COLUMNS)


def a_v2_file(*lines, total="0", columns=V2_COLUMNS, sid="1"):
    head = "\t".join(columns)
    summary = "\t".join({"settlement-id": sid, "total-amount": total, "currency": "INR"}.get(c, "") for c in columns)
    return ("\r\n".join([head, summary, *lines]) + "\r\n").encode("utf-8")


V2_NAME = "amazon_az_settlements_2026-09-08.csv"
_v2 = answered(lambda: read_as("az_settlements", V2_NAME, a_v2_file(
    a_v2_line("Order", "406-1", "SKU-A", "ItemPrice", "Principal", "100.00"),
    a_v2_line("Order", "406-1", "SKU-A", "ItemPrice", "Product Tax", "3.00"),
    a_v2_line("Order", "406-1", "SKU-A", "ItemTCS", "TCS-IGST", "-1.00"),
    a_v2_line("Order", "406-1", "SKU-A", "ItemTCS", "TCS-CGST", "-0.50"),
    a_v2_line("Order", "406-1", "SKU-A", "ItemTDS", "TDS", "-0.25"),
    a_v2_line("Order", "406-1", "SKU-A", "ItemFees", "Fixed closing fee", "-22.00"),
    a_v2_line("Order", "406-1", "SKU-A", "ItemFees", "Fixed closing fee IGST", "-3.96"),
    a_v2_line("Order", "406-1", "SKU-A", "ItemFees", "Commission", "-8.00"),
    a_v2_line("Order", "406-1", "SKU-A", "ItemFees", "FBA Pick and Pack Fee", "-2.00"),
    a_v2_line("other-transaction", "406-1", "", "other-transaction", "Amazon Easy Ship Charges", "-5.00"),
    a_v2_line("other-transaction", "406-1", "", "other-transaction", "MFNPostagePurchaseCompleteIGST", "-0.90"),
    a_v2_line("Order", "406-2", "SKU-B", "ItemPrice", "Principal", "50.00"),
    a_v2_line("Order", "406-2", "SKU-B", "ItemPrice", "Shipping", "10.00"),
    a_v2_line("Order", "406-2", "SKU-B", "Promotion", "Principal", "-5.00"),
    a_v2_line("Refund", "406-3", "SKU-C", "ItemPrice", "Principal", "-40.00"),
    a_v2_line("Refund", "406-3", "SKU-C", "ItemFees", "Refund commission", "4.00"),
    a_v2_line("Order", "406-4", "SKU-D", "ItemPrice", "Principal", "30.00"),
    a_v2_line("Order", "406-4", "SKU-E", "ItemPrice", "Principal", "20.00"),
    a_v2_line("other-transaction", "406-4", "", "other-transaction", "Amazon Easy Ship Charges", "-6.00"),
    a_v2_line("ServiceFee", "", "", "Cost of Advertising", "TransactionTotalAmount", "-5.90"),
    a_v2_line("Order", "406-5", "SKU-F", "SomethingNew", "A New Charge", "-1.00"),
    total="1",
)))
_v2_reading, _v2_refused = _v2 if _v2 else (None, None)
_v2_sales = {(s.order_id, s.sku): s for s in (_v2_reading.sales if _v2_reading else ())}
_v1 = _v2_sales.get(("406-1", "SKU-A"))


def _v2s(order, sku):
    return _v2_sales.get((order, sku))


check("AMAZON SETTLEMENT FILE: the file the run really fetches is read, and none of its lines is refused",
      _v2_reading is not None and len(_v2_sales) > 0 and _v2_refused == 0)
check("and what was paid for an order line is every amount on it added, its own order-level shipping lines included",
      _v1 is not None and _v1.settlement == "59.39")
check("and the fixed closing fee is a positive charge where money was taken",
      _v1 is not None and _v1.charges.get("fixedFee") == "22")
check("and the commission", _v1 is not None and _v1.charges.get("commission") == "8")
check("and the GST on a fee and on the postage is the GST on the platform's fees, added",
      _v1 is not None and _v1.charges.get("otherServicesTax") == "4.86")
check("and the postage line is shipping", _v1 is not None and _v1.charges.get("shipping") == "5")
check("and the TCS lines are one tax, added; the TDS line is TDS",
      _v1 is not None and _v1.charges.get("tcs") == "1.5" and _v1.charges.get("tds") == "0.25")
check("and a fulfilment fee is other services", _v1 is not None and _v1.charges.get("otherServices") == "2")
check("and the price, its shipping and a promotion are the sale, not a charge",
      _v2s("406-2", "SKU-B") is not None and _v2s("406-2", "SKU-B").settlement == "55"
      and _v2s("406-2", "SKU-B").charges == {})
check("and a refunded commission is a charge below nought",
      _v2s("406-3", "SKU-C") is not None and _v2s("406-3", "SKU-C").charges.get("commission") == "-4"
      and _v2s("406-3", "SKU-C").settlement == "-36")
check("and an order's postage with two SKUs in the file is left without a SKU, not guessed onto one",
      _v2s("406-4", "") is not None and _v2s("406-4", "").settlement == "-6")
check("and a kind of line the reader has no name for is a charge under other services, and is said",
      _v2s("406-5", "SKU-F") is not None and _v2s("406-5", "SKU-F").charges.get("otherServices") == "1"
      and any("SomethingNew" in x for x in _v2_reading.set_aside))
check("and the advertising line with no order is set aside, said, and on no sale",
      _v2_reading is not None and any("Cost of Advertising" in x for x in _v2_reading.set_aside)
      and all(s.order_id for s in _v2_reading.sales))
check("and its day is the file's own, out of its name", _v2_reading is not None and _v2_reading.on == "2026-09-08"
      and all(s.payments_on == "2026-09-08" for s in _v2_reading.sales))
_v2_bad = answered(lambda: read_as("az_settlements", V2_NAME, a_v2_file(
    a_v2_line("Order", "406-9", "SKU-Z", "ItemPrice", "Principal", "12abc"))))
check("and an amount that is not a figure is said with its order and its own text, not dropped as a blank (D574 item 5)",
      _v2_bad is not None and "unreadable charge 406-9: '12abc'" in _v2_bad[0].set_aside and not _v2_bad[0].sales)
_v2_bad2 = answered(lambda: read_as("az_settlements", V2_NAME, a_v2_file(
    a_v2_line("Order", "", "", "Other", "Fee", "x9"))))
_v2_bad3 = answered(lambda: read_as("az_settlements", V2_NAME, a_v2_file(
    a_v2_line("Order", "406-1", "SKU-A", "ItemPrice", "Principal", "100.00", sid="77"),
    a_v2_line("Order", "406-1", "", "ItemFees", "Cancellation", "x?", sid="77"))))
check("and an unreadable no-SKU fee adds nothing to its order's sale, not even its key",
      _v2_bad3 is not None and len(_v2_bad3[0].sales) == 1 and _v2_bad3[0].sales[0].settlement == "100"
      and _v2_bad3[0].sales[0].notes is None and any("unreadable charge 406-1: 'x?'" in x for x in _v2_bad3[0].set_aside))
check("and so is one with no order id at all",
      _v2_bad2 is not None and "unreadable charge (no order id): 'x9'" in _v2_bad2[0].set_aside)
_v2_keyed = answered(lambda: read_as("az_settlements", V2_NAME, a_v2_file(
    a_v2_line("Order", "406-1", "SKU-A", "ItemPrice", "Principal", "100.00", sid="77"),
    a_v2_line("Order", "406-1", "", "ItemFees", "Cancellation", "-28.91", sid="77"))))
check("THE SETTLEMENT READER KEYS A NO-SKU FEE BY ITS SETTLEMENT ID AND LINE",
      _v2_keyed is not None and any("fee:77:" in (s.notes or "") for s in _v2_keyed[0].sales))
_v2_two = answered(lambda: read_as("az_settlements", V2_NAME, a_v2_file(
    a_v2_line("Order", "406-1", "SKU-A", "ItemPrice", "Principal", "100.00", sid="77"),
    a_v2_line("Order", "406-1", "", "ItemFees", "Cancellation", "-28.91", sid="77"),
    a_v2_line("Order", "406-1", "", "ItemFees", "Cancellation", "-1.09", sid="77"))))
check("TWO NO-SKU FEES OF ONE ORDER KEEP BOTH THEIR KEYS, in order",
      _v2_two is not None and [s.notes for s in _v2_two[0].sales] == ["fee:77:3 fee:77:4"])
_v2_nokey = answered(lambda: read_as("az_settlements", V2_NAME, a_v2_file(
    a_v2_line("Order", "406-1", "SKU-A", "ItemPrice", "Principal", "100.00", sid="77"),
    a_v2_line("Order", "406-1", "SKU-A", "ItemPrice", "Tax", "5.00", sid="77"))))
check("and two lines of one row with no fee between them leave no notes at all",
      _v2_nokey is not None and len(_v2_nokey[0].sales) == 1 and _v2_nokey[0].sales[0].notes is None)
check("and a settlement file that has lost a column is refused, naming it",
      refused_by(lambda: read_as("az_settlements", V2_NAME, a_v2_file(
          a_v2_line("Order", "406-1", "SKU-A", "ItemPrice", "Principal", "1"),
          columns=[c for c in V2_COLUMNS if c != "amount-description"]))))
check("and the Date Range Transaction file is still read as before", _az_reading is not None and len(_az_sales) > 0)

# ---------------------------------------------------------------- SEVERAL SETTLEMENTS, ONE ORDER (job 18, Control's ruling)

# **SETTLEMENT FILES ARE SEPARATE PERIODS, NOT RE-DOWNLOADS.** A sale in one settlement and its refund in a later one are BOTH the
# order's money, so the order's net is their sum. The same settlement (one settlement-id) read twice is one statement, never two.
def a_folder_of(files):
    """(listing, bring_it_back) for a made folder of settlement files: {name: bytes}."""
    listing = [whats_new.InTheFolder(which="id-" + name, name=name, size=len(body)) for name, body in files.items()]
    return listing, (lambda which: files[which[3:]])


_sale_file = a_v2_file(a_v2_line("Order", "407-1", "SKU-A", "ItemPrice", "Principal", "100.00", sid="S1"),
                       a_v2_line("Order", "407-1", "SKU-A", "ItemFees", "Commission", "-10.00", sid="S1"),
                       a_v2_line("Order", "407-2", "SKU-B", "ItemPrice", "Principal", "40.00", sid="S1"), sid="S1")
_refund_file = a_v2_file(a_v2_line("Refund", "407-1", "SKU-A", "ItemPrice", "Principal", "-60.00", sid="S2"),
                         a_v2_line("Refund", "407-1", "SKU-A", "ItemFees", "Refund commission", "6.00", sid="S2"), sid="S2")
_folder = {"amazon_az_settlements_2026-09-08.csv": _sale_file, "amazon_az_settlements_2026-09-22.csv": _refund_file}


def the_settlements(files, which_is_new):
    listing, back = a_folder_of(files)
    how = next(o for o in reading.WHAT_CAN_BE_READ if o.report_id == "az_settlements")
    one = next(f for f in listing if f.name == which_is_new)
    return reading.a_settlements_reading(how, one, back(one.which), listing, back)


_sum = answered(lambda: the_settlements(_folder, "amazon_az_settlements_2026-09-22.csv"))
_sum_by = {(s.order_id, s.sku): s for s in (_sum[0].sales if _sum else ())}
check("SEVERAL SETTLEMENTS: a sale in one file and its refund in a later one are the order's net, added",
      _sum is not None and _sum_by[("407-1", "SKU-A")].settlement == "36"
      and _sum_by[("407-1", "SKU-A")].charges.get("commission") == "4")
check("and an order only the older settlement has is still stated, from that file",
      _sum is not None and _sum_by[("407-2", "SKU-B")].settlement == "40")
check("and the reading is dated by the newest settlement it holds",
      _sum is not None and _sum[0].on == "2026-09-22" and all(s.payments_on == "2026-09-22" for s in _sum[0].sales))
_late = answered(lambda: the_settlements(_folder, "amazon_az_settlements_2026-09-08.csv"))
check("and the sum is the same whichever file is the new one",
      _late is not None and {(s.order_id, s.sku): s.settlement for s in _late[0].sales}
      == {k: v.settlement for k, v in _sum_by.items()})
_twice = answered(lambda: the_settlements(
    {**_folder, "amazon_az_settlements_2026-09-23.csv": _refund_file}, "amazon_az_settlements_2026-09-23.csv"))
check("and two copies of ONE settlement count once, not twice",
      _twice is not None and {(s.order_id, s.sku): s.settlement for s in _twice[0].sales}[("407-1", "SKU-A")] == "36")
_edited = a_v2_file(a_v2_line("Refund", "407-1", "SKU-A", "ItemPrice", "Principal", "-50.00", sid="S2"), sid="S2")
_newest = answered(lambda: the_settlements(
    {**_folder, "amazon_az_settlements_2026-09-23.csv": _edited}, "amazon_az_settlements_2026-09-23.csv"))
check("and of two copies of one settlement the NEWEST is the one that stands",
      _newest is not None and {(s.order_id, s.sku): s.settlement for s in _newest[0].sales}[("407-1", "SKU-A")] == "40"
      and _newest[0].on == "2026-09-23")
check("and an older settlement file that cannot be read stops the night's figure, rather than leaving it out",
      refused_by(lambda: the_settlements({**_folder, "amazon_az_settlements_2026-09-01.csv": b'"a","b"' + bytes([13, 10]) + b'"1","2"'},
                                         "amazon_az_settlements_2026-09-22.csv")))
_old_shape = answered(lambda: the_settlements(
    {**_folder, "amazon_az_settlements_2026-09-30.csv": AMAZON_BODY}, "amazon_az_settlements_2026-09-30.csv"))
check("and a Date Range Transaction file in the same folder is read on its own, as before",
      _old_shape is not None and _old_shape[0].on == "2026-09-30"
      and ("404-1", "SKU-A") in {(s.order_id, s.sku) for s in _old_shape[0].sales}
      and ("407-1", "SKU-A") not in {(s.order_id, s.sku) for s in _old_shape[0].sales})

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

HIS_FILES_GROUP = 6
print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
WITHOUT = ran - real_ran
if WITHOUT != 95 + 22 + 17 + 8 + 2 + 3 + 5 + 3 + 5 + 14 + 9 + 4 + 2 + 1 + 1:  # one 1 is N018 (AU3 #6), the other AP11 proving, the 14 are A90d proving, the 9 A90e (D581), the 6 A90f (D582)
    print(f"FAIL  checks went missing -- {WITHOUT} ran without his files, 191 expected")
    sys.exit(1)
print(f"all {ran} checks passed" + ("" if real_ran == HIS_FILES_GROUP else f" ({HIS_FILES_GROUP - real_ran} of his real-file checks not run -- the files are elsewhere)"))
