"""Checks for reading the return and ad files into the seller's own database (A78).

**EVERY ROW IN HERE IS MADE UP.** The column names are the ones his real files carry (read from `D:\\Kartaan-Samples\\autosync-returns-ads-2026-10-12`
on 2026-10-12); no value of his, and no customer detail, is written here.

Run: python autosync/returns_ads_checks.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ads  # noqa: E402
import firestore  # noqa: E402
import firestore_door  # noqa: E402
import reading  # noqa: E402
import records  # noqa: E402
import reports  # noqa: E402
import returns  # noqa: E402
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


def refused(work, kind=Exception):
    try:
        work()
    except kind:
        return True
    return False


def csv(*lines, sep=","):
    return ("\n".join(lines) + "\n").encode("utf-8")


FK_RET_HEAD = '"Order ID","Return ID","Tracking ID","SKU","Quantity","Return Requested Date","Completed Date","Completion Status","Return Type","Return Reason","Return Sub-reason"'
ME_RET_HEAD = '"S No","SKU","Qty","Suborder Number","Return Created Date","Type of Return","Delivered Date","AWB Number","Return Reason","Detailed Return Reason"'
AZ_RET_HEAD = "Amazon RMA ID\tOrder ID\tReturn request date\tReturn request status\tTracking ID\tMerchant SKU\tReturn quantity\tReturn Reason\tReturn type\tReturn delivery date"


def fk(*rows, head=FK_RET_HEAD):
    return table.read(csv(head, *rows))


def me(*rows, head=ME_RET_HEAD):
    return table.read(csv("", '"Meesho Supplier Panel"', '"Supplier ID","1"', "", head, *rows), header_row=5)


def az(*rows, head=AZ_RET_HEAD):
    return table.read(("\n".join([head, *rows]) + "\n").encode("utf-8"))


# ------------------------------------------------------------------ days

check("a day is read in the three ways the platforms write it",
      returns.a_day("11 October, 2026") == "2026-10-11" and returns.a_day("09-Oct-2026") == "2026-10-09"
      and returns.a_day("2026-10-11 12:52:00") == "2026-10-11")
check("a day written the other way round, an impossible day, or nothing is nothing -- never guessed",
      returns.a_day("26.08.2026") is None and returns.a_day("31 February, 2026") is None and returns.a_day("") is None
      and returns.a_day("5 Smarch, 2026") is None)

# ------------------------------------------------------------------ Flipkart returns

f = answered(lambda: returns.read_returns("fk_returns", fk(
    '"OD1","111","TRK1","DJ-1","2","2 October, 2026","11 October, 2026","Closed","courier_return","ORC_validated with customer","ORC_validated with customer"',
    '"OD2","222","","""SKU:DJ-2""","1","5 October, 2026","","Open","customer_return","MISSING_ITEM","MISSING_PRODUCT"',
), "2026-10-11"))
one = (f.records.get("flipkart__111") or {}) if f else {}
two = (f.records.get("flipkart__222") or {}) if f else {}
check("a Flipkart return is named platform, two underscores, its Return ID", f is not None and set(f.records) == {"flipkart__111", "flipkart__222"})
check("the platform's own words are kept exactly -- type, reason, sub-reason, status",
      one.get("returnType") == "courier_return" and one.get("reason") == "ORC_validated with customer"
      and two.get("reason") == "MISSING_ITEM" and two.get("subReason") == "MISSING_PRODUCT" and two.get("status") == "Open")
check("the order, the SKU, the tracking id and the quantity are carried; the quantity is a whole number",
      one.get("orderId") == "OD1" and one.get("sku") == "DJ-1" and one.get("trackingId") == "TRK1" and one.get("qty") == 2
      and isinstance(one.get("qty"), int))
check("the sale it belongs to is named exactly as the ledger names a sale", one.get("saleKey") == "flipkart::OD1::DJ-1")
check("Flipkart's wrapped SKU is unwrapped as the orders reader does", two.get("sku") == "DJ-2" and two.get("saleKey") == "flipkart::OD2::DJ-2")
check("the days are year-month-day", one.get("startedOn") == "2026-10-02" and one.get("closedOn") == "2026-10-11")
check("a blank is absent, never nought or an empty word: no tracking id, no close day",
      "trackingId" not in two and "closedOn" not in two)
check("the file's day is kept", one.get("fileDay") == "2026-10-11")
check("a record carries only the fields of a returned line", all(set(r) <= set(returns.RETURN_FIELDS) for r in f.records.values()))

same = answered(lambda: returns.read_returns("fk_returns", fk(
    '"OD1","111","TRK1","DJ-1","2","2 October, 2026","11 October, 2026","Closed","courier_return","R","S"'), "2026-10-12"))
check("the fingerprint ignores the day the file was read, so the same return in tomorrow's file is the same",
      same is not None and same.records["flipkart__111"]["digest"] != "" and same.records["flipkart__111"]["fileDay"] == "2026-10-12"
      and same.records["flipkart__111"]["digest"] == records.the_digest({**one, "reason": "R", "subReason": "S"}))
changed = answered(lambda: returns.read_returns("fk_returns", fk(
    '"OD1","111","TRK1","DJ-1","2","2 October, 2026","11 October, 2026","Closed","courier_return","OTHER","S"'), "2026-10-11"))
check("a changed reason is a different fingerprint", changed is not None and changed.records["flipkart__111"]["digest"] != one.get("digest"))

check("a file missing a column it needs stops, naming the columns it has",
      refused(lambda: returns.read_returns("fk_returns", fk('"OD1","111"', head='"Order ID","Return ID"'), "2026-10-11"), table.CannotRead))
check("a column the file has twice stops it too",
      refused(lambda: returns.read_returns("fk_returns", fk(
          '"OD1","111","a","b","c","d","e","f","g","h","i","j"', head=FK_RET_HEAD + ',"Return Reason"'), "2026-10-11"), table.CannotRead))
bad = answered(lambda: returns.read_returns("fk_returns", fk(
    '"OD1","111","T","S","1","2 October, 2026","26.08.2026","Closed","c","R","S"',
    '"OD3","333","T","S","1","2 October, 2026","11 October, 2026","Closed","c","R","S"',
    '"","444","T","S","1","2 October, 2026","11 October, 2026","Closed","c","R","S"',
    '"OD5","a/b","T","S","1","2 October, 2026","11 October, 2026","Closed","c","R","S"',
    '"OD6","666","T","S","1.5","2 October, 2026","11 October, 2026","Closed","c","R","S"'), "2026-10-11"))
check("a row with a date that is not one, no order, a slash in its name or a fractional quantity is refused by name and the rest are read",
      bad is not None and set(bad.records) == {"flipkart__333"} and len(bad.not_read) == 4 and bad.rows_in_file == 5)
twice = answered(lambda: returns.read_returns("fk_returns", fk(
    '"OD1","111","T","S","1","2 October, 2026","11 October, 2026","Closed","c","FIRST","S"',
    '"OD1","111","T","S","1","2 October, 2026","11 October, 2026","Closed","c","SECOND","S"'), "2026-10-11"))
check("a return named twice in one file is one record, the first row standing", twice is not None and len(twice.records) == 1
      and twice.records["flipkart__111"]["reason"] == "FIRST")

# ------------------------------------------------------------------ Meesho returns

m = answered(lambda: returns.read_returns("me_returns", me(
    '"1","SKU-M","1","100_1","2026-10-05","Customer Return","2026-10-11","R-AWB-1","Reason words as Meesho writes them","Product was broken or torn"',
    '"2","DJ-2","1","101_1","2026-09-26","Courier Return (RTO)","","","NA","NA"'), "2026-10-11"))
mine = (m.records.get("meesho__100_1") or {}) if m else {}
check("a Meesho return is named by its Suborder Number, and the order is the same number the ledger calls Sub Order No",
      m is not None and set(m.records) == {"meesho__100_1", "meesho__101_1"} and mine.get("orderId") == "100_1"
      and mine.get("saleKey") == "meesho::100_1::SKU-M")
check("Meesho's own words are kept: its Return Reason is the reason and its Detailed Return Reason the sub-reason",
      mine.get("reason") == "Reason words as Meesho writes them" and mine.get("subReason") == "Product was broken or torn"
      and mine.get("returnType") == "Customer Return")
check("the AWB is the tracking id, and an unfinished return has no close day", mine.get("trackingId") == "R-AWB-1"
      and "closedOn" not in m.records["meesho__101_1"] and "trackingId" not in m.records["meesho__101_1"])
check("Meesho's 'NA' is its own word and is kept, not turned into nothing", m.records["meesho__101_1"].get("reason") == "NA")

# ------------------------------------------------------------------ Amazon returns

a = answered(lambda: returns.read_returns("az_returns", az(
    "RMA1\t407-1\t09-Oct-2026\tApproved\tTRK-A\tSKU-Q\t1\tAMZ-REASON-ONE\tC-Returns\t",
    "RMA2\t407-2\t09-Oct-2026\tApproved\t\t\t1\tNOT_AS_DESCRIBED\tC-Returns\t11-Oct-2026"), "2026-10-09"))
ar = (a.records.get("amazon__RMA1") or {}) if a else {}
check("an Amazon return is named by its own Amazon RMA ID, so two returns of one order and SKU are two records",
      a is not None and set(a.records) == {"amazon__RMA1", "amazon__RMA2"})
check("Amazon's own reason code and status are kept as written", ar.get("reason") == "AMZ-REASON-ONE" and ar.get("status") == "Approved"
      and ar.get("returnType") == "C-Returns" and ar.get("trackingId") == "TRK-A")
check("the request day and delivery day are read from Amazon's day-month-name way", ar.get("startedOn") == "2026-10-09"
      and a.records["amazon__RMA2"].get("closedOn") == "2026-10-11" and "closedOn" not in ar)
check("the sale is the ledger's", ar.get("saleKey") == "amazon::407-1::SKU-Q")
check("a return with no SKU has no sku field, not an empty one", "sku" not in a.records["amazon__RMA2"] and a.records["amazon__RMA2"]["saleKey"] == "amazon::407-2::")

# ------------------------------------------------------------------ Flipkart / Meesho ads

DAILY_HEAD = "Campaign ID,Campaign Name,Date,Ad Spend,Views,Clicks,Total converted units,Total Revenue (Rs.),ROI"
PLACE_HEAD = "Campaign ID,Campaign Name,AdGroup Name,Placement Type,Views,Clicks,Click Through Rate in %,Average CPC,Conversion Rate,Ad Spend,Direct Units Sold,Indirect Units Sold,Direct Revenue,Indirect Revenue,ROI"
OVER_HEAD = "Campaign ID,AdGroup Name,Listing ID,Product Name,Sku Id,AdGroup CPC,Views,Clicks,Click Through Rate in %,Total converted units,Ad Spend,Total Revenue (Rs.),Direct Units Sold,Direct Revenue,Indirect Units Sold,Indirect Revenue,ROI"
SEARCH_HEAD = "AdGroup ID,AdGroup Name,Campaign ID,Campaign Name,Query,Views,Clicks,Average CPC,Click Through Rate in %, Direct Units Sold,Indirect Units Sold,Direct Conversion Rate in %,Indirect Conversion Rate in %,Direct Revenue,Indirect Revenue,ROI,SUM(cost)"
ORDERS_HEAD = "Campaign ID,AdGroup Name,Listing ID,Product Name,Advertised FSN ID,Date,order_id,AdGroup CPC,Expected ROI,Purchased FSN ID,Total Revenue (Rs.),Direct Units Sold,Indirect Units Sold"
SUMMARY_HEAD = '"Date","Campaign ID","Campaign Name","Ad Spend","Revenue","ROI","Ad Spend Per Order","Views","Clicks","Orders","Conversion %","Avg Order Value"'
TITLES = ("Start Time, 2026-10-11 00:00:00", "End Time, 2026-10-11 23:59:59")


def flipkart_file(head, *rows):
    return table.read(csv(*TITLES, head, *rows), header_row=3)


d = answered(lambda: ads.read_ads("fk_ads_daily", flipkart_file(
    DAILY_HEAD,
    "C1,Campaign one,2026-10-11,474.41,20751,477,2,614.0000,1.29",
    "C2,Campaign two,2026-10-11,12.72,483,12,,0.0000,0.0"), "2026-10-11", "2026-10-11"))
rec = (d.records.get("flipkart__2026-10-11") or {}) if d else {}
camps = rec.get("campaigns", {})
check("Flipkart's daily ads are one record per platform per day, holding each campaign",
      d is not None and set(d.records) == {"flipkart__2026-10-11"} and set(camps) == {"C1", "C2"} and d.kind == "days")
check("a campaign's figures are the platform's own: spend, views, clicks, units, revenue, and the name",
      camps.get("C1") == {"campaignName": "Campaign one", "spend": 474.41, "views": 20751, "clicks": 477, "units": 2, "revenue": 614.0})
check("a blank is absent, not nought: the campaign with no units says no units", "units" not in camps.get("C2", {}) and camps["C2"]["clicks"] == 12)

dd = answered(lambda: ads.read_ads("fk_ads_daily", flipkart_file(
    DAILY_HEAD, "C1,N,2026-10-10,1,1,1,1,1,1", "C1,N,2026-10-11,2,1,1,1,1,1", "C1,N,2026-10-11,3,1,1,1,1,1"), "2026-10-11", "2026-10-11"))
check("a file with several days in it makes a record for each, and a campaign named twice on a day is added",
      dd is not None and set(dd.records) == {"flipkart__2026-10-10", "flipkart__2026-10-11"}
      and dd.records["flipkart__2026-10-11"]["campaigns"]["C1"]["spend"] == 5.0)

s = answered(lambda: ads.read_ads("me_ads_summary", table.read(csv(
    SUMMARY_HEAD, '"2026-10-11","M1","Meesho one","108.86000000000001","181","1.66","109.04","32661","582","1","0.17","181"')), "2026-10-11", None))
mc = ((s.records.get("meesho__2026-10-11") or {}).get("campaigns") or {}).get("M1", {}) if s else {}
check("Meesho's daily ads come from its summary, money to two places", mc.get("spend") == 108.86 and mc.get("units") == 1 and mc.get("revenue") == 181.0
      and mc.get("views") == 32661)

pl = answered(lambda: ads.read_ads("fk_ads_placements", flipkart_file(
    PLACE_HEAD,
    "C1,Campaign one,Artificial Jewellery,Product Page,17694,398,2.2,1.0,0.005,398.0000,2,1,614.0000,100.0000,1.54",
    "C1,Campaign one,Artificial Jewellery,Home Page,579,24,4.1,1.0,0.0,24.0,0,0,0,0,0"), "2026-10-11", "2026-10-11"))
prow = (pl.records.get("flipkart__2026-10-11__placements") or {}) if pl else {}
check("placements are one detail record for the day, holding every row, with how many rows the file had and how many are kept",
      pl is not None and set(pl.records) == {"flipkart__2026-10-11__placements"} and len(prow.get("rows", [])) == 2
      and prow.get("rowsInFile") == 2 and prow.get("rowsKept") == 2 and prow.get("kind") == "placements")
check("a placement row keeps the platform's own placement name and the direct and indirect figures apart",
      prow["rows"][0]["placementType"] == "Product Page" and prow["rows"][0]["unitsDirect"] == 2 and prow["rows"][0]["unitsIndirect"] == 1
      and prow["rows"][0]["revenueDirect"] == 614.0 and prow["rows"][0]["revenueIndirect"] == 100.0 and prow["rows"][0]["spend"] == 398.0)

ov = answered(lambda: ads.read_ads("fk_ads_overall", flipkart_file(
    OVER_HEAD, "C1,AG,LST1,Product,LM-20 (1),1.01,48,0,0,0,0.00,0,0,0,0,0,0", "C2,AG,LST2,Product,LM-21 (1),1.01,5,1,0,0,2.00,0,0,0,0,0,0"),
    "2026-10-11", "2026-10-11"))
check("overall is a file per campaign, so its record is about one campaign",
      ov is not None and set(ov.records) == {"flipkart__2026-10-11__overall__C1", "flipkart__2026-10-11__overall__C2"}
      and ov.records["flipkart__2026-10-11__overall__C1"]["rows"][0]["skuId"] == "LM-20 (1)"
      and ov.records["flipkart__2026-10-11__overall__C1"]["campaignId"] == "C1")

se = answered(lambda: ads.read_ads("fk_ads_search", flipkart_file(
    SEARCH_HEAD, "AG1,AG,C1,Campaign one,bahubali jhumka,7,0,0,0,0,0,0,0,0,0,0,0.63"), "2026-10-11", "2026-10-11"))
check("a search term's cost is read from SUM(cost), whatever spaces the platform left in the other headings",
      se is not None and se.records["flipkart__2026-10-11__search"]["rows"][0]["spend"] == 0.63
      and se.records["flipkart__2026-10-11__search"]["rows"][0]["query"] == "bahubali jhumka")

orr = answered(lambda: ads.read_ads("fk_ads_orders", flipkart_file(
    ORDERS_HEAD, "C1,AG,LST1,Product,FSN1,2026-10-11,OD9,0.88,,FSN2,294.0000,1,0",
    "C1,AG,LST1,Product,FSN1,2026-10-10,OD8,0.88,,FSN1,100.0000,0,1"), "2026-10-11", "2026-10-11"))
check("an ad order's day is the row's own, so a file with two days makes two records, and an FSN is kept as an FSN",
      orr is not None and set(orr.records) == {"flipkart__2026-10-11__orders", "flipkart__2026-10-10__orders"}
      and orr.records["flipkart__2026-10-11__orders"]["rows"][0]["purchasedFsn"] == "FSN2"
      and orr.records["flipkart__2026-10-11__orders"]["rows"][0]["orderId"] == "OD9")

long_money = answered(lambda: ads.read_ads("fk_ads_placements", flipkart_file(
    PLACE_HEAD, "C1,N,AG,Product Page,1,1,1,1,1,10.456,0,0,0,0,0"), "2026-10-11", "2026-10-11"))
check("money in a breakdown is kept to the paisa too", long_money is not None
      and long_money.records["flipkart__2026-10-11__placements"]["rows"][0]["spend"] == 10.46)

nodate = answered(lambda: ads.read_ads("fk_ads_placements", flipkart_file(
    PLACE_HEAD, "C1,N,AG,Product Page,1,1,1,1,1,1,0,0,0,0,0"), "2026-10-11", None))
check("a file with no day on its first line is dated by its name", nodate is not None and "flipkart__2026-10-11__placements" in nodate.records)
header_wins = answered(lambda: ads.read_ads("fk_ads_placements", flipkart_file(
    PLACE_HEAD, "C1,N,AG,Product Page,1,1,1,1,1,1,0,0,0,0,0"), "2026-10-12", "2026-10-11"))
check("and the day on its first line wins over the name", header_wins is not None and "flipkart__2026-10-11__placements" in header_wins.records)

check("an ads file missing a column it needs stops, naming the columns it has",
      refused(lambda: ads.read_ads("fk_ads_daily", flipkart_file("Campaign ID,Date", "C1,2026-10-11"), "2026-10-11", None), table.CannotRead))
badrows = answered(lambda: ads.read_ads("fk_ads_daily", flipkart_file(
    DAILY_HEAD, ",N,2026-10-11,1,1,1,1,1,1", "C1,N,11/10/2026,1,1,1,1,1,1", "C1,N,2026-10-11,abc,1,1,1,1,1", "C1,N,2026-10-11,1,-5,1,1,1,1",
    "C9,N,2026-10-11,9,1,1,1,1,1"), "2026-10-11", None))
check("a row with no campaign, a day that is not one, a spend that is not a figure or a negative count is refused by name and the rest are read",
      badrows is not None and set(badrows.records["flipkart__2026-10-11"]["campaigns"]) == {"C9"} and len(badrows.not_read) == 4)

big = [{"campaignId": "C", "query": f"q{i}" * 20, "spend": float(i), "views": i} for i in range(200)]
kept = ads.held_to_size(big, most=4000)
check("a breakdown too big for a record keeps the rows that spent most and says how many were cut: never an arbitrary cut",
      0 < len(kept) < 200 and kept[0]["spend"] == 199.0 and all(k["spend"] >= 199 - len(kept) for k in kept) and ads.held_to_size(big[:3]) == big[:3])
wide = answered(lambda: ads.read_ads("fk_ads_search", flipkart_file(
    SEARCH_HEAD, *[f"AG1,AG,C1,N,term{i} " + "x" * 30000 + f",1,0,0,0,0,0,0,0,0,0,0,{i}.5" for i in range(40)]), "2026-10-11", "2026-10-11"))
big_record = (wide.records.get("flipkart__2026-10-11__search") or {}) if wide else {}
check("a record that would pass Firestore's limit is held under it, and says what it left out",
      wide is not None and big_record.get("rowsInFile") == 40 and 0 < big_record.get("rowsKept") < 40
      and ads._size(big_record["rows"]) <= ads.MOST_BYTES)

# ------------------------------------------------------------------ writers

ret_write = answered(lambda: firestore.a_return_write("p", one))
fields = (ret_write or {}).get("update", {}).get("fields", {})
check("a returned line is written whole, to platform_returns, under platform and Return ID",
      ret_write is not None and ret_write["update"]["name"].endswith("/platform_returns/flipkart__111") and "updateMask" not in ret_write)
check("its whole numbers go as whole numbers and its words as words", fields.get("qty") == {"integerValue": "2"} and fields.get("reason") == {"stringValue": "ORC_validated with customer"})
check("a field outside the returned line's own is refused, so a platform's new column cannot reach the database",
      refused(lambda: firestore.a_return_write("p", {**one, "customerName": "x"}), firestore.Refused))
check("a day that is not a day is refused", refused(lambda: firestore.a_return_write("p", {**one, "closedOn": "11 Oct"}), firestore.Refused))

days_write = answered(lambda: firestore.a_ads_days_write("p", "flipkart", "2026-10-11", camps, "dig", "2026-10-11", "2026-10-12"))
check("a day's ad figures are written with a mask naming only the campaigns' fields, so what the charge file says is never undone",
      days_write is not None and days_write["update"]["name"].endswith("/platform_ads_days/flipkart__2026-10-11")
      and "campaigns" in days_write["updateMask"]["fieldPaths"] and "charged" not in days_write["updateMask"]["fieldPaths"])
check("a campaign's money goes as money and its counts as counts",
      days_write["update"]["fields"]["campaigns"]["mapValue"]["fields"]["C1"]["mapValue"]["fields"]["views"] == {"integerValue": "20751"}
      and days_write["update"]["fields"]["campaigns"]["mapValue"]["fields"]["C1"]["mapValue"]["fields"]["spend"] == {"doubleValue": 474.41})
det_write = answered(lambda: firestore.a_ads_detail_write("p", "flipkart__2026-10-11__placements", "flipkart", prow, "2026-10-11", "2026-10-12"))
check("a breakdown is written whole, rows as a list of maps",
      det_write is not None and det_write["update"]["name"].endswith("/platform_ads_detail/flipkart__2026-10-11__placements")
      and len(det_write["update"]["fields"]["rows"]["arrayValue"]["values"]) == 2)
check("the new collections are the only ones added to what the run may write",
      set(firestore.WHAT_IT_MAY_WRITE) - {"sync_log", "sync_board", "sync_runs", "listing_views", "listings_seen", "sync_check", "sync_ledger", "returns_sheet", "platform_claims", "platform_performance", "platform_ads_month", "platform_quality", "platform_shop_days"} ==
      {"platform_returns", "platform_ads_days", "platform_ads_detail"})
check("a collection the run may not write is still refused", refused(lambda: firestore.where_a_document_lives("p", "orders", "x"), firestore.Refused))


# ------------------------------------------------------------------ the sinks

class Reply:
    def __init__(self, status=200, body=None):
        self.status, self._body, self.text = status, body if body is not None else {}, str(body or "")

    ok = property(lambda self: 200 <= self.status < 300)

    def json(self):
        return self._body

    def records(self):
        return self._body if isinstance(self._body, list) else None


class Transport:
    """A stand-in database: `held` is {document name: (digest field, digest, day field, day)}."""

    def __init__(self, held=None, fail_on=None):
        self.posts, self.held, self.fail_on = [], held or {}, fail_on

    def post(self, url, params=None, headers=None, json=None, data=None):
        self.posts.append({"url": url, "json": json})
        if url.endswith(":batchGet"):
            found = []
            for name in json["documents"]:
                got = self.held.get(name.rsplit("/", 1)[-1])
                found.append({"found": {"name": name, "fields": {
                    got[0]: {"stringValue": got[1]}, got[2]: {"stringValue": got[3]}}}} if got else {"missing": name})
            return Reply(200, found)
        return Reply(self.fail_on or 200, {})


class NotAList(Transport):
    def post(self, url, params=None, headers=None, json=None, data=None):
        return Reply(200, {"not": "a list"})


there = Transport()
put = answered(lambda: firestore_door.a_returns_sink(there, "p", "2026-10-12")("fk_returns", "2026-10-11", f.records))
check("new returns are asked about first, then written, in one call", [p["url"].rsplit(":", 1)[-1] for p in there.posts] == ["batchGet", "commit"])
check("and the sink says how many records it wrote", put == 2 and len(there.posts[1]["json"]["writes"]) == 2)

held_same = Transport(held={k: ("digest", v["digest"], "fileDay", "2026-10-11") for k, v in f.records.items()})
zero = answered(lambda: firestore_door.a_returns_sink(held_same, "p", "2026-10-12")("fk_returns", "2026-10-11", f.records))
check("a second run on the same file writes nothing at all", zero == 0 and all(not p["url"].endswith(":commit") for p in held_same.posts))
held_old = Transport(held={k: ("digest", "stale", "fileDay", "2026-10-01") for k, v in f.records.items()})
check("a record whose words changed in a newer file is written again",
      answered(lambda: firestore_door.a_returns_sink(held_old, "p", "2026-10-12")("fk_returns", "2026-10-11", f.records)) == 2)
held_newer = Transport(held={k: ("digest", "different", "fileDay", "2026-10-20") for k, v in f.records.items()})
check("but never over a newer file's record: a late upload cannot undo a later one",
      answered(lambda: firestore_door.a_returns_sink(held_newer, "p", "2026-10-12")("fk_returns", "2026-10-11", f.records)) == 0)
check("a database that says no stops the sink", refused(lambda: firestore_door.a_returns_sink(Transport(fail_on=403), "p", "2026-10-12")(
    "fk_returns", "2026-10-11", f.records), firestore_door.TheirDatabaseSaidNo))
check("an answer that is not a list of records is not 'nothing held'", refused(lambda: firestore_door.a_returns_sink(NotAList(), "p", "2026-10-12")(
    "fk_returns", "2026-10-11", f.records), firestore_door.TheirDatabaseSaidNo))

adstransport = Transport()
put = answered(lambda: firestore_door.an_ads_sink(adstransport, "p", "2026-10-12")("fk_ads_daily", "flipkart", "days", "2026-10-11", d.records))
check("a day's ads are written to platform_ads_days, one record, with a mask",
      put == 1 and adstransport.posts[1]["json"]["writes"][0]["update"]["name"].endswith("/platform_ads_days/flipkart__2026-10-11")
      and "updateMask" in adstransport.posts[1]["json"]["writes"][0])
held_days = Transport(held={"flipkart__2026-10-11": ("campaignsDigest", d.records["flipkart__2026-10-11"]["digest"], "campaignsFileDay", "2026-10-11")})
check("the same day's ads read again write nothing",
      answered(lambda: firestore_door.an_ads_sink(held_days, "p", "2026-10-12")("fk_ads_daily", "flipkart", "days", "2026-10-11", d.records)) == 0)
detail_t = Transport()
check("a breakdown is written to platform_ads_detail, one record per record",
      answered(lambda: firestore_door.an_ads_sink(detail_t, "p", "2026-10-12")("fk_ads_overall", "flipkart", "overall", "2026-10-11", ov.records)) == 2
      and detail_t.posts[1]["json"]["writes"][0]["update"]["name"].endswith("/platform_ads_detail/flipkart__2026-10-11__overall__C1"))
held_detail = Transport(held={k: ("digest", v["digest"], "fileDay", "2026-10-11") for k, v in ov.records.items()})
check("the same breakdown read again writes nothing",
      answered(lambda: firestore_door.an_ads_sink(held_detail, "p", "2026-10-12")("fk_ads_overall", "flipkart", "overall", "2026-10-11", ov.records)) == 0)


# ------------------------------------------------------------------ the night

def a_file(which, name, size=100):
    return whats_new.InTheFolder(which=which, name=name, size=size)


class Night:
    def __init__(self, files, bodies, give=True, throws=None):
        self.files, self.bodies, self.returned, self.advertised, self.throws = files, bodies, [], [], throws
        self.give = give

    def returns_sink(self, report_id, day, records):
        if self.throws:
            raise self.throws
        self.returned.append((report_id, day, records))
        return len(records)

    def ads_sink(self, report_id, platform, kind, day, records):
        if self.throws:
            raise self.throws
        self.advertised.append((report_id, platform, kind, day, records))
        return len(records)

    def go(self, already=()):
        return answered(lambda: reading.read_what_is_new(
            already_read=already,
            what_is_in_the_folder=lambda r: list(self.files.get(r, ())),
            bring_it_back=lambda w: self.bodies[w],
            record_the_sales=lambda readings: None,
            record_returns=self.returns_sink if self.give else None,
            record_ads=self.ads_sink if self.give else None,
        ))


FILES = {
    "fk_returns": [a_file("r1", "flipkart_fk_returns_2026-10-11.csv")],
    "me_returns": [a_file("r2", "meesho_me_returns_2026-10-11.csv")],
    "az_returns": [a_file("r3", "amazon_az_returns_2026-10-09.csv")],
    "fk_ads_daily": [a_file("a1", "flipkart_fk_ads_daily_2026-10-11.csv")],
    "me_ads_summary": [a_file("a2", "meesho_me_ads_summary_2026-10-11.csv")],
}
BODIES = {
    "r1": csv(FK_RET_HEAD, '"OD1","111","TRK1","DJ-1","2","2 October, 2026","11 October, 2026","Closed","courier_return","R","S"'),
    "r2": csv("", '"Meesho Supplier Panel"', '"Supplier ID","1"', "", "", "", ME_RET_HEAD,
              '"1","DJ-1","1","100_1","2026-10-05","Customer Return","2026-10-11","R-AWB-1","R","D"'),
    "r3": ("\n".join([AZ_RET_HEAD, "RMA1\t407-1\t09-Oct-2026\tApproved\tTRK-A\tJJ\t1\tAMZ\tC-Returns\t"]) + "\n").encode("utf-8"),
    "a1": csv(*TITLES, DAILY_HEAD, "C1,N,2026-10-11,474.41,20751,477,2,614.0000,1.29"),
    "a2": csv(SUMMARY_HEAD, '"2026-10-11","M1","N","108.86","181","1.66","109.04","32661","582","1","0.17","181"'),
}
night = Night(FILES, BODIES)
was = night.go()
check("a night reads the three returns files and the two ads files into records",
      was is not None and len(was.read_tonight) == 5 and len(night.returned) == 3 and len(night.advertised) == 2)
check("the Meesho returns file is found by its first column name, past a title block of any length",
      any(r[0] == "me_returns" and "meesho__100_1" in r[2] for r in night.returned))
check("the day given to a sink is the day in the file's name", all(r[1] in ("2026-10-11", "2026-10-09") for r in night.returned)
      and all(a[3] == "2026-10-11" for a in night.advertised))
check("the records written are counted and said", was is not None and was.returns_written == 3 and was.ads_written == 2
      and "3 returned line(s)" in was.says() and "2 ad record(s)" in was.says())
check("the standing record says what each file held and what was read",
      was is not None and {r.into for r in was.reads} == {"returned lines", "ad records"} and all(r.rows_read == r.rows_in_file for r in was.reads))
check("all five files are written down as read", was is not None and set(was.files_read) == {"r1", "r2", "r3", "a1", "a2"})
again = Night(FILES, BODIES).go(already=("r1", "r2", "r3", "a1", "a2"))
check("a file already read is not read again", again is not None and again.read_tonight == () and again.already_read == 5)

nowhere = Night(FILES, BODIES, give=False)
was = nowhere.go()
check("with nowhere to write them the files are not opened and not marked read, and the night says so",
      was is not None and was.read_tonight == () and was.returns_waiting == 3 and was.ads_waiting == 2 and "left unread" in was.says())

broken = Night(FILES, BODIES, throws=RuntimeError("the database would not take it")).go()
check("a sink that throws leaves the files unread and says why, by name",
      broken is not None and broken.read_tonight == () and len(broken.could_not_read) == 5 and "would not take it" in broken.could_not_read[0])
refusing = Night(FILES, BODIES, throws=firestore_door.TheirDatabaseSaidNo("403")).go()
check("a database that says no is OUR defect, named as the database's, and the files stay unread",
      refusing is not None and refusing.is_a_defect and len(refusing.the_database_refused) == 5 and refusing.read_tonight == ())

hopeless = Night({"fk_returns": [a_file("h", "flipkart_fk_returns_2026-10-11.csv")]},
                 {"h": csv(FK_RET_HEAD, '"OD1","111","T","S","1","2 October, 2026","26.08.2026","C","c","R","S"')}).go()
check("a file in which no row could be read is NOT marked read, since it would never be opened again",
      hopeless is not None and hopeless.read_tonight == () and "no row of" in hopeless.could_not_read[0])
nameless = Night({"fk_returns": [a_file("n", "returns.csv")]}, {"n": BODIES["r1"]}).go()
check("a file with no day in its name is refused, since which of two files is newer decides a record",
      nameless is not None and nameless.read_tonight == () and "no day in its name" in nameless.could_not_read[0])
moved = Night({"fk_returns": [a_file("m", "flipkart_fk_returns_2026-10-11.csv")]}, {"m": csv('"Order ID","Return ID"', '"OD1","1"')}).go()
check("a file whose columns have moved stops, in words, and is left to be read again",
      moved is not None and moved.read_tonight == () and "no column called" in moved.could_not_read[0].lower())

# ------------------------------------------------------------------ the rule that ties reports to readers

readers = {o.report_id for o in reading.WHAT_RETURNS_CAN_BE_READ + reading.WHAT_ADS_CAN_BE_READ}
check("the returns and ads readers are the ten reports named",
      readers == {"fk_returns", "me_returns", "az_returns", "fk_ads_daily", "fk_ads_placements", "fk_ads_overall", "fk_ads_search",
                  "fk_ads_orders", "me_ads_summary", "me_ads"})
check("each is a report that exists and none is also said to be unread",
      all(r in reports.BY_ID for r in readers) and not (readers & set(reading.WHAT_IS_FETCHED_AND_NOT_READ_YET)))
check("and they write no ledger column", all(o.knows == () for o in reading.WHAT_RETURNS_CAN_BE_READ + reading.WHAT_ADS_CAN_BE_READ))
check("Flipkart keyword ads are not read, are not fetched, and say why in words",
      "fk_ads_kw" in reading.WHAT_IS_FETCHED_AND_NOT_READ_YET and "discontinued" in reading.WHAT_IS_FETCHED_AND_NOT_READ_YET["fk_ads_kw"]
      and reports.BY_ID["fk_ads_kw"].needs_a_person is True)
# ---- me_ads (A87): read from his real file meesho_me_ads_2026-10-14.csv (Date, Campaign ID, Campaign Name, Status, Start Date, Ad Spend, ...)
_ME_ADS_HEAD = '"Date","Campaign ID","Campaign Name","Status","Start Date","Ad Spend","Revenue","Orders","Views","Clicks","ROI","Conversion %","Avg Order Value","Ad Spend Per Order"'
_life = answered(lambda: ads.read_ads("me_ads", table.read(csv(
    _ME_ADS_HEAD, '"2026-10-14","24960469","1244938 - 8/7/2026","LIVE","2026-08-07","5649.58","57154","234","1848493","52783","10.12","0.44","244.25","24.14"')),
    "2026-10-14", None))
_life_row = (((_life.records if _life else {}).get("meesho__2026-10-14__lifetime") or {}).get("rows") or [{}])[0]
check("MEESHO'S CAMPAIGNS-SO-FAR FILE IS READ INTO A RECORD OF ITS OWN KIND, never one of the day-by-day records its campaign id shares",
      _life is not None and set(_life.records) == {"meesho__2026-10-14__lifetime"} and _life_row.get("spend") == 5649.58
      and _life_row.get("revenue") == 57154.0 and _life_row.get("units") == 234 and _life_row.get("views") == 1848493
      and _life_row.get("status") == "LIVE" and _life_row.get("startDate") == "2026-08-07" and _life_row.get("campaignId") == "24960469")
check("the campaigns-so-far file's clicks are read too (R20 proving)", _life_row.get("clicks") == 52783)
check("and its campaign name (R20 proving)", _life_row.get("campaignName") == "1244938 - 8/7/2026")
_ME_ROW = '"2026-10-14","24960469","1244938 - 8/7/2026","LIVE","2026-08-07","5649.58","57154","234","1848493","52783","10.12","0.44","244.25","24.14"'
check("a campaigns-so-far file without its Ad Spend or Campaign ID column is refused, never read without them (R20 proving)",
      all(refused(lambda h=h: ads.read_ads("me_ads", table.read(csv(_ME_ADS_HEAD.replace(h, '"Other"'), _ME_ROW)), "2026-10-14", None))
          for h in ('"Ad Spend"', '"Campaign ID"')))
_me_night = Night({"me_ads": [a_file("ma", "meesho_me_ads_2026-10-14.csv")]}, {"ma": csv(_ME_ADS_HEAD, _ME_ROW)})
_me_night_said = _me_night.go()
check("and the night reads it with its names on the FIRST line (R20 proving)",
      _me_night_said is not None and _me_night_said.read_tonight == ("ma",) and len(_me_night.advertised) == 1)
_life_more = answered(lambda: ads.read_ads("me_ads", table.read(csv(
    _ME_ADS_HEAD, '"2026-10-14","24960469","1244938 - 8/7/2026","LIVE","2026-08-07","5700.00","57154","234","1848493","52783","10.12","0.44","244.25","24.14"')),
    "2026-10-14", None))
_life_rec = (_life.records if _life else {}).get("meesho__2026-10-14__lifetime") or {}
_more_rec = (_life_more.records if _life_more else {}).get("meesho__2026-10-14__lifetime") or {}
check("an ads record's fingerprint is of everything it holds, its rows included, so a changed figure is written again (R20 proving)",
      _life_rec.get("digest") == records.the_digest({k: v for k, v in _life_rec.items() if k != "digest"})
      and _life_rec.get("digest") != _more_rec.get("digest"))
check("the rule that ties every report to a reader or a reason still holds", reading.why_a_report_has_no_decision() == "")

# ------------------------------------------------------------------ found by the independent review (A78)

two_rma = answered(lambda: returns.read_returns("az_returns", az(
    "RMA1\t111-1\t09-Oct-2026\tApproved\t\tSKU A\t1\tR1\tC-Returns\t", "RMA2\t111-1\t09-Oct-2026\tApproved\t\tSKU A\t1\tR2\tC-Returns\t"), "2026-10-09"))
check("two Amazon returns of one order and SKU are two records, each with its own reason (the key is Amazon's RMA id)",
      two_rma is not None and {r["reason"] for r in two_rma.records.values()} == {"R1", "R2"})
dup = answered(lambda: returns.read_returns("fk_returns", fk(
    '"OD1","111","T","S","1","2 October, 2026","11 October, 2026","Closed","c","R1","S"',
    '"OD1","111","T","S","1","2 October, 2026","11 October, 2026","Closed","c","R2","S"',
    '"OD1","111","T","S","1","2 October, 2026","11 October, 2026","Closed","c","R1","S"'), "2026-10-11"))
check("a return named twice with different words is SAID, not silently the first; named twice with the same words is just one",
      dup is not None and dup.records["flipkart__111"]["reason"] == "R1" and len(dup.not_read) == 1 and "different words" in dup.not_read[0])
check("a reserved name for a record is refused", answered(lambda: len(returns.read_returns("fk_returns", fk(
    '"OD1","__x__","T","S","1","2 October, 2026","11 October, 2026","Closed","c","R","S"'), "2026-10-11").not_read)) == 1)
check("a negative quantity is refused by name", answered(lambda: len(returns.read_returns("fk_returns", fk(
    '"OD1","111","T","S","-1","2 October, 2026","11 October, 2026","Closed","c","R","S"'), "2026-10-11").not_read)) == 1)
check("'11 Sept, 2026' is read, as some platforms abbreviate September so", returns.a_day("11 Sept, 2026") == "2026-09-11")

slash = answered(lambda: ads.read_ads("fk_ads_overall", flipkart_file(
    OVER_HEAD, "A/B,AG,LST1,Product,LM-20 (1),1.01,48,0,0,0,0.00,0,0,0,0,0,0", "C2,AG,LST2,Product,LM-21 (1),1.01,5,1,0,0,2.00,0,0,0,0,0,0"),
    "2026-10-11", "2026-10-11"))
check("a campaign id with a slash is refused by name in a breakdown too, so it cannot make a record name that the writer refuses every night",
      slash is not None and set(slash.records) == {"flipkart__2026-10-11__overall__C2"} and len(slash.not_read) == 1)
check("a file for a range of days has no one day to be filed under and is refused",
      refused(lambda: ads.refuse_a_range(csv("Start Time, 2026-10-04 00:00:00", "End Time, 2026-10-11 23:59:59", "x")), table.CannotRead)
      and not refused(lambda: ads.refuse_a_range(csv(*TITLES, "x"))) and not refused(lambda: ads.refuse_a_range(csv("Date,x", "1,2"))))

check("the ads-days write's mask is exactly the campaigns' own fields and nothing else",
      days_write["updateMask"]["fieldPaths"] == sorted(["platform", "day", "updatedOn", "campaigns", "campaignsDigest", "campaignsFileDay"]))
held_samefile = Transport(held={k: ("digest", "different", "fileDay", "2026-10-11") for k in f.records})
check("a same-day file whose words changed is written again (a re-fetched report for the day)",
      answered(lambda: firestore_door.a_returns_sink(held_samefile, "p", "2026-10-12")("fk_returns", "2026-10-11", f.records)) == 2)
many = {f"flipkart__{n}": {**one, "returnKey": str(n), "digest": f"d{n}"} for n in range(150)}
chunked = Transport()
answered(lambda: firestore_door.a_returns_sink(chunked, "p", "2026-10-12")("fk_returns", "2026-10-11", many))
check("more than a hundred records are asked about in more than one call, and every one is written",
      [p["url"].rsplit(":", 1)[-1] for p in chunked.posts].count("batchGet") == 2
      and sum(len(p["json"]["writes"]) for p in chunked.posts if p["url"].endswith(":commit")) == 150)
held_all = Transport(held={k: ("digest", v["digest"], "fileDay", "2026-10-11") for k, v in many.items()})
check("and records past the first hundred that are already held are recognised as held, so a catch-up night rewrites none of them",
      answered(lambda: firestore_door.a_returns_sink(held_all, "p", "2026-10-12")("fk_returns", "2026-10-11", many)) == 0)
check("an answer that is not a list stops the sink with that said in words",
      answered(lambda: firestore_door.a_returns_sink(NotAList(), "p", "2026-10-12")("fk_returns", "2026-10-11", f.records)) is None
      and any("not a list" in t for t in THREW) and not THREW.clear())
check("a held record's rows are kept under the limit exactly: the kept rows measure no more than the limit given",
      ads._size(ads.held_to_size(big, most=4000)) <= 4000)

part_night = Night({"fk_returns": [a_file("p", "flipkart_fk_returns_2026-10-11.csv")]}, {"p": csv(
    FK_RET_HEAD, '"OD1","111","T","S","1","2 October, 2026","11 October, 2026","Closed","c","R","S"',
    '"OD2","222","T","S","1","2 October, 2026","26.08.2026","Closed","c","R","S"')}).go()
check("a file with some rows refused is read, and says how many rows and which was the first",
      part_night is not None and part_night.read_tonight == ("p",) and part_night.rows_refused == 1
      and "1 row(s) not read" in part_night.could_not_read[0])

# ------------------------------------------------------------------ a sub-order returned twice (A87, AU2)

_ret1 = '"1","SKU-M","1","334_1","2026-10-08","Customer Return","2026-10-10","AWB1","FIRST","d1"'
_ret2 = '"2","SKU-M","1","334_1","2026-10-11","Customer Return","2026-10-19","AWB2","SECOND","d2"'
back_twice = answered(lambda: returns.read_returns("me_returns", me(_ret1, _ret2), "2026-10-18"))
back_twice_reversed = answered(lambda: returns.read_returns("me_returns", me(_ret2, _ret1), "2026-10-18"))
check("A MEESHO SUB-ORDER RETURNED TWICE KEEPS BOTH RETURNS, the earlier under the name it always had and the later named by its day",
      back_twice is not None and set(back_twice.records) == {"meesho__334_1", "meesho__334_1~2026-10-11"}
      and back_twice.records["meesho__334_1"]["reason"] == "FIRST"
      and back_twice.records["meesho__334_1~2026-10-11"]["reason"] == "SECOND"
      and back_twice.records["meesho__334_1~2026-10-11"]["returnKey"] == "334_1" and back_twice.not_read == ())
check("and the file's row order makes no difference to which return is which",
      back_twice_reversed is not None and back_twice_reversed.records == back_twice.records)
check("the same two returns written out twice are still two returns",
      (lambda x: x is not None and len(x.records) == 2 and x.not_read == ())(
          answered(lambda: returns.read_returns("me_returns", me(_ret1, _ret2, _ret1, _ret2), "2026-10-18"))))
_same_day = answered(lambda: returns.read_returns("me_returns", me(
    _ret1, '"2","SKU-M","1","334_1","2026-10-08","Customer Return","2026-10-10","AWB1","OTHER WORDS","d1"'), "2026-10-18"))
check("a Meesho return listed twice for the SAME request day with different words is said, not made into a second return",
      _same_day is not None and set(_same_day.records) == {"meesho__334_1"} and len(_same_day.not_read) == 1)
_third = answered(lambda: returns.read_returns("me_returns", me(
    _ret1, _ret2, '"3","SKU-M","1","334_1","2026-10-11","Customer Return","2026-10-19","AWB3","THIRD","d3"'), "2026-10-18"))
check("a THIRD return of one sub-order on the later return's day, in other words, is said and does not replace the second (R20 proving)",
      _third is not None and set(_third.records) == {"meesho__334_1", "meesho__334_1~2026-10-11"}
      and _third.records["meesho__334_1~2026-10-11"]["reason"] == "SECOND" and len(_third.not_read) == 1)
_by_day = []
for _words in ("A", "B", "C", "D", "E", "F", "G", "H"):
    _pair = answered(lambda w=_words: returns.read_returns("me_returns", me(
        f'"1","SKU-M","1","334_1","2026-10-08","Customer Return","2026-10-10","AWB1","{w}","d1"', _ret2), "2026-10-18"))
    _by_day.append(_pair is not None and _pair.records.get("meesho__334_1", {}).get("reason") == _words)
check("whichever words the two returns carry, the EARLIER request day keeps the plain name (R20 proving)", all(_by_day))
_fk_twice = answered(lambda: returns.read_returns("fk_returns", fk(
    '"OD1","111","T","S","1","2 October, 2026","11 October, 2026","Closed","c","FIRST","S"',
    '"OD1","111","T","S","1","5 October, 2026","11 October, 2026","Closed","c","SECOND","S"'), "2026-10-11"))
check("only a MEESHO sub-order is one return per request day: a Flipkart return id named twice on two days is said, not split (R20 proving)",
      _fk_twice is not None and set(_fk_twice.records) == {"flipkart__111"} and len(_fk_twice.not_read) == 1)
# ------------------------------------------------------------------ a return in the ledger (D447, D449, A87)

import ledger  # noqa: E402
import sales  # noqa: E402

_done = '"1","SKU-M","1","555_1","2026-10-08","Customer Return","2026-10-10","AWB1","R","d"'
_open = '"2","SKU-M","1","556_1","2026-10-08","Customer Return","","AWB2","R","d"'
_said = answered(lambda: returns.read_returns("me_returns", me(_done, _open), "2026-10-18"))
_in_ledger = answered(lambda: reading.a_returns_in_the_ledger(_said, "2026-10-18", "file-1", "me_returns"))
_made = answered(lambda: ledger.plan([list(sales.COLUMNS)], [_in_ledger]))
_cols = list(sales.COLUMNS)
_rows = {r[_cols.index("id")]: dict(zip(_cols, r)) for r in (_made.append if _made else ())}
check("A RETURN ARRIVING BEFORE ITS ORDER CREATES THE ORDER'S ROW with platform, order, SKU and the return's day (D449)",
      _made is not None and set(_rows) == {"meesho::555_1::SKU-M", "meesho::556_1::SKU-M"}
      and _rows["meesho::555_1::SKU-M"]["platform"] == "meesho" and _rows["meesho::555_1::SKU-M"]["returnsOn"] == "2026-10-18")
check("A FINISHED RETURN SAYS THE ORDER CAME BACK; one still open says nothing about it",
      _rows["meesho::555_1::SKU-M"]["whatHappened"] == "Came back" and _rows["meesho::556_1::SKU-M"]["whatHappened"] == "")
_fk_open = answered(lambda: returns.read_returns("fk_returns", fk(
    '"OD1","111","T","S","1","2 October, 2026","11 October, 2026","Open","c","R","S"',
    '"OD2","222","T","S","1","2 October, 2026","11 October, 2026","Closed","c","R","S"'), "2026-10-11"))
_fk_led = answered(lambda: reading.a_returns_in_the_ledger(_fk_open, "2026-10-11", "f", "fk_returns"))
check("A FLIPKART RETURN STILL OPEN IS NOT 'CAME BACK' even though Flipkart fills its completed day; a Closed one is",
      _fk_led is not None and {s.order_id: s.what_happened for s in _fk_led.sales} == {"OD1": None, "OD2": "Came back"})
check("and a return line with no SKU makes no row (it has none to be keyed by)",
      reading.a_returns_in_the_ledger(answered(lambda: returns.read_returns("me_returns", me(
          '"1","","1","557_1","2026-10-08","Customer Return","2026-10-10","AWB1","R","d"'), "2026-10-18")), "2026-10-18", "f", "me_returns") is None)

check("a Flipkart Return ID named twice is still one return (its Return ID is the return's own), only Meesho's key is the order's",
      twice is not None and len(twice.records) == 1)

_into_the_ledger = []
_night_with_ledger = answered(lambda: reading.read_what_is_new(
    already_read=(),
    what_is_in_the_folder=lambda r: [a_file("m1", "meesho_me_returns_2026-10-18.csv")] if r == "me_returns" else [],
    bring_it_back=lambda w: csv("", '"Meesho Supplier Panel"', '"Supplier ID","1"', "", ME_RET_HEAD, _done),
    record_the_sales=lambda readings: _into_the_ledger.extend(readings),
    record_returns=lambda report_id, day, records: len(records),
    record_ads=lambda *a: 0,
))
check("THE NIGHT HANDS A FINISHED RETURN TO THE LEDGER as well as to the returns record",
      _night_with_ledger is not None and _night_with_ledger.read_tonight == ("m1",) and len(_into_the_ledger) == 1
      and _into_the_ledger[0].sales[0].order_id == "555_1")

check("and that reading names the returns report and the file, and may make a row an order has not made yet (R20 proving)",
      len(_into_the_ledger) == 1 and _into_the_ledger[0].report == "me_returns" and _into_the_ledger[0].which == "m1"
      and _into_the_ledger[0].only_existing is False)
_fk_spaced = answered(lambda: returns.read_returns("fk_returns", fk(
    '"OD3","333","T","S","1","2 October, 2026","11 October, 2026"," Closed ","c","R","S"'), "2026-10-11"))
check("a Flipkart status written ' Closed ' still says the order came back (R20 proving)",
      (lambda r: r is not None and [s.what_happened for s in r.sales] == ["Came back"])(
          answered(lambda: reading.a_returns_in_the_ledger(_fk_spaced, "2026-10-11", "f", "fk_returns"))))


def _ledger_says_no(readings):
    raise ledger.LedgerRefused("the sheet's columns have moved")


_two_returns = {"m1": [a_file("m1", "meesho_me_returns_2026-10-18.csv"), a_file("m2", "meesho_me_returns_2026-10-19.csv")]}
_refused_night = answered(lambda: reading.read_what_is_new(
    already_read=(), what_is_in_the_folder=lambda r: _two_returns["m1"] if r == "me_returns" else [],
    bring_it_back=lambda w: csv("", '"Meesho Supplier Panel"', '"Supplier ID","1"', "", ME_RET_HEAD, _done),
    record_the_sales=_ledger_says_no, record_returns=lambda report_id, day, records: len(records), record_ads=lambda *a: 0))
check("A LEDGER THAT REFUSES A RETURNS FILE IS SAID AS THE LEDGER'S REFUSAL, the file left unread, and the next file still tried (R20 proving)",
      _refused_night is not None and _refused_night.read_tonight == () and len(_refused_night.the_ledger_refused) == 2
      and "columns have moved" in _refused_night.the_ledger_refused[0])

check(f"nothing above ended by throwing rather than by answering -- {THREW}", not THREW)

EXPECTED = 107 + 3 + 2 + 3 + 3
if ran != EXPECTED:
    print(f"FAIL  checks went missing -- {ran} ran, {EXPECTED} expected")
    failures.append("count")

print(f"\n{len(failures)} FAILED ({ran} checks)" if failures else f"\nall {ran} checks passed")
sys.exit(1 if failures else 0)
