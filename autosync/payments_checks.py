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
    ["Sub Order No", "Supplier SKU", "Final Settlement Amount", "Fixed Fee (Incl. GST)", "Return premium (incl GST)"]
    + MEESHO_COLUMNS[3:]
)


def a_meesho_file(*rows, rename=None):
    cols = [(rename or {}).get(c, c) for c in MEESHO_HEADER]
    formulas = ["", "A", "(B + C)"] + [""] * (len(cols) - 3)
    return a_spreadsheet([
        ("Disclaimer", [["Meesho"]]),
        ("Order Payments", [["Order Related Details"] + [""] * (len(cols) - 1), cols, formulas] + [r for r in rows]),
        ("Ads Cost", [["Ads Cost"], ["Deduction Date"], ["No data is available for these dates."]]),
    ])


def a_meesho_line(order, sku, settlement, first_fixed_fee="", **charges):
    names = {
        "commission": "Meesho Commission (Incl. GST)", "shipping": "Shipping Charge (Incl. GST)",
        "returnShipping": "Return Shipping Charge (Incl. GST)", "tcs": "TCS", "tds": "TDS",
        "warehousing": "Warehousing fee (Incl. GST)",
    }
    cells = a_line(MEESHO_HEADER, **{
        "Sub Order No": order, "Supplier SKU": sku, "Final Settlement Amount": settlement,
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
    a_meesho_line("M1_1", "SKU-M", "150", commission="-20", shipping="-30", tcs="-1", tds="-0.5", fixedFee="-4",
                  first_fixed_fee="99"),
    a_meesho_line("M2_1", "SKU-N", "-60", returnShipping="-60"),
)
_me = answered(lambda: read_as("me_payments", "meesho_me_payments_2026-10-03.xlsx", MEESHO_BODY))
_me_reading = _me[0] if _me else None
_me_sales = {(s.order_id, s.sku): s for s in (_me_reading.sales if _me_reading else ())}
check("MEESHO: THE FORMULA ROW UNDER THE NAMES IS NOT AN ORDER", _me_reading is not None and len(_me_sales) == 2)
_m1 = _me_sales.get(("M1_1", "SKU-M"))
check("what was paid is the final settlement", _m1 is not None and _m1.settlement == "150")
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
check("A PAYMENTS REPORT MAY WRITE THE SETTLEMENT, THE CHARGES AND ITS OWN MARKER, AND NO ORDER COLUMN",
      set(reading.WHAT_PAYMENTS_KNOW) == {"settlement", "paymentsOn"} | set(sales.CHARGE_COLUMNS)
      and not set(reading.WHAT_PAYMENTS_KNOW) & set(reading.WHAT_ORDERS_KNOWS))
check("and every charge the ledger has is one a payments report may write",
      all(c in reading.WHAT_PAYMENTS_KNOW for c in sales.CHARGE_COLUMNS))


# ================================================================ the ledger: matching on the order id


def sheet_with(*rows):
    """A ledger as the sheet would hold it: the header and one row for each sale given."""
    return [list(sales.COLUMNS)] + [list(sales.the_row_for(r)) for r in rows]


def after(values, what):
    """The sheet as it stands once a plan has been carried out. Row numbers count the header as row 1."""
    out = [list(r) for r in values]
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
check("and the row's version moved on, because the row changed", _r.get("rev") == "1")
check("and a charge the file did not state is still blank, never nought", _r.get("charge_penalty") == ""
      and _r.get("charge_tds") == "")
_p2 = answered(lambda: ledger.plan(_after1, [pays("az_settlements", "2026-09-05",
                                                  a_payment("amazon", "404-1", "SKU-A", "90", commission="10", tcs="1.5"))]))
check("THE SAME FILE READ AGAIN WRITES NOTHING", _p2 is not None and not _p2.changes_anything and _p2.unmatched == ())

_p3 = answered(lambda: ledger.plan(HELD, [pays("fk_payments", "2026-09-05",
                                               a_payment("flipkart", "OD99", "DJ 14", "5"))]))
check("A PAYMENT FOR AN ORDER THE LEDGER DOES NOT HOLD IS NOT A ROW: nothing is appended",
      _p3 is not None and _p3.append == () and _p3.update == ())
check("AND IT IS SAID, by name, with its reason and the file it came from",
      _p3 is not None and len(_p3.unmatched) == 1 and "flipkart::OD99::DJ 14" in str(_p3.unmatched[0])
      and "no row for this order" in str(_p3.unmatched[0]) and "fk_payments" in str(_p3.unmatched[0]))
check("and the plan's one line counts it, even when the count is nought",
      _p3 is not None and "1 payment lines with no order to go on" in _p3.says()
      and "0 payment lines with no order to go on" in ledger.plan(HELD, []).says())

_p4 = answered(lambda: ledger.plan(HELD, [pays("fk_payments", "2026-09-05",
                                               a_payment("flipkart", "OD1", "DJ 99", "5"))]))
check("A LINE THAT NAMES A SKU THE ORDER DOES NOT HAVE IS NOT PUT ON THE ORDER'S ONLY ROW -- that would be another item's money",
      _p4 is not None and _p4.update == () and len(_p4.unmatched) == 1
      and "not under this SKU" in str(_p4.unmatched[0]))

_p5 = answered(lambda: ledger.plan(HELD, [pays("az_settlements", "2026-09-05",
                                               a_payment("amazon", "404-1", "", "-20", shipping="20"))]))
check("A LINE WITH NO SKU THAT REACHES THE LEDGER IS NEVER GUESSED ONTO 'THE ORDER'S ONLY ROW': it is said",
      _p5 is not None and _p5.update == () and len(_p5.unmatched) == 1 and "names no SKU" in str(_p5.unmatched[0]))
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
check("and each file is written down as read, so it is not read again", _n1 is not None
      and set(_n1.files_read) == {"as-1", "fp-1", "mp-1"})
check("AND NO ROW WAS ADDED: the ledger has the same number of rows it began with", len(_the.values) == 7)
check("the payment with no order is said in the night's own words, and so are the lines set aside",
      any("PAYMENT WITH NO ORDER" in x and "404-2" in x for x in _the.said)
      and any("SET ASIDE" in x and "Transfer" in x for x in _the.said)
      and any("SET ASIDE" in x and "Deferred" in x for x in _the.said))
check("and the manifest's line for each says it was read into the sales ledger",
      _n1 is not None and len(_n1.reads) == 3)
_before = [list(r) for r in _the.values]
_n2 = answered(lambda: a_night(_the, _files, _bodies, already=_n1.files_read if _n1 else ()))
check("A SECOND NIGHT OVER THE SAME FILES OPENS NOTHING AND WRITES NOTHING",
      _n2 is not None and _n2.read_tonight == () and _the.values == _before)
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
check("A PAYMENTS FILE OLDER THAN THE ORDERS IT SETTLES STILL FILLS THEIR ROW WHEN BOTH ARE NEW TOGETHER, and is then read for good",
      _catch_up is not None and _caught.get("settlement") == "150" and _caught.get("charge_commission") == "20"
      and set(_catch_up.files_read) == {"o-1", "mp-1"})

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

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

HIS_FILES_GROUP = 4
print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
WITHOUT = ran - real_ran
if WITHOUT != 95:
    print(f"FAIL  checks went missing -- {WITHOUT} ran without his files, 95 expected")
    sys.exit(1)
print(f"all {ran} checks passed" + ("" if real_ran == HIS_FILES_GROUP else f" ({HIS_FILES_GROUP - real_ran} of his real-file checks not run -- the files are elsewhere)"))
