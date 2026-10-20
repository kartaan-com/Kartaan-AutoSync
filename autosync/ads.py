"""Reading a platform's ad reports into an ads record per day, and the detail behind it (plan jobs 35, 78).

**TWO KINDS OF RECORD, written by `firestore_door`:**

| Kind | Id | From | Holds |
|---|---|---|---|
| lifetime | `<platform>__<day>__lifetime` | `me_ads` (Meesho) | `rows`: each campaign's takings since it began, as read that day |
| days | `<platform>__<day>` | `fk_ads_daily` (Flipkart), `me_ads_summary` (Meesho) | `campaigns`: campaign id -> name, spend, views, clicks, units, revenue |
| detail | `<platform>__<day>__<kind>` (`overall`: `..__overall__<campaignId>`, a file per campaign) | `fk_ads_placements`, `fk_ads_overall`, `fk_ads_search`, `fk_ads_orders` | `rows`: the file's rows, in the ERP's words |

**THE COLUMNS ARE FROM HIS REAL FILES (2026-10-11, `D:\\Kartaan-Samples\\autosync-returns-ads-2026-10-12`).** The Flipkart files open with
`Start Time, <day>` and `End Time, ...` lines and the column names are on line 3; **only `fk_ads_daily` and `fk_ads_orders` carry a
`Date` per row**, so the others are about the day on their first line (else the day in their name, the same refusal `views.py` makes).

**A BLANK IS NOTHING, NEVER NOUGHT:** a cell the file left empty leaves the field out. **A COLUMN THE FILE LACKS STOPS THE FILE**,
naming the columns it has, and a name it has twice stops it too. **A ROW WITH NO CAMPAIGN, OR A DAY OR FIGURE THAT IS NOT ONE, IS
REFUSED BY NAME** and the rest are read. A figure that is money keeps two places (`108.86000000000001` is `108.86`).

**NO RECORD IS EVER SILENTLY SHORTENED.** A detail record is held to `MOST_BYTES`; past that the rows that spent most are kept and the
record says how many were in the file (`rowsInFile`) and how many it holds (`rowsKept`).

Nothing here opens a file, a clock or a connection.
"""

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable, Dict, List, Optional, Tuple

import orders
import returns
import table
import views

# Firestore's record limit is 1 MiB; this leaves room for the fields around the rows.
MOST_BYTES = 700 * 1024

COUNTS = frozenset({"views", "clicks", "units", "unitsDirect", "unitsIndirect"})
TEXT = frozenset({
    "campaignId", "campaignName", "placementType", "skuId", "listingId", "productName", "query", "orderId", "advertisedFsn",
    "purchasedFsn",
})


@dataclass(frozen=True)
class Way:
    """One ad report: where it goes, how its columns are named, and which of them it cannot be read without."""

    platform: str
    kind: str
    # field -> the column name (lower-cased, stripped) or several whose cells are added together
    columns: Dict[str, Tuple[str, ...]]
    needed: Tuple[str, ...]
    header_row: int
    day_column: Optional[str] = None


WAYS: Dict[str, Way] = {
    "fk_ads_daily": Way(
        "flipkart", "days",
        {
            "campaignId": ("campaign id",), "campaignName": ("campaign name",), "spend": ("ad spend",), "views": ("views",),
            "clicks": ("clicks",), "units": ("total converted units",), "revenue": ("total revenue (rs.)",),
        },
        needed=("campaignId", "spend"), header_row=3, day_column="date",
    ),
    "me_ads_summary": Way(
        "meesho", "days",
        {
            "campaignId": ("campaign id",), "campaignName": ("campaign name",), "spend": ("ad spend",), "views": ("views",),
            "clicks": ("clicks",), "units": ("orders",), "revenue": ("revenue",),
        },
        needed=("campaignId", "spend"), header_row=1, day_column="date",
    ),
    # **A CAMPAIGN'S TAKINGS SINCE IT BEGAN, stamped with the day it was read (A87; his real file meesho_me_ads_2026-10-14.csv).** Its campaign
    # id is the one `me_ads_summary` reads day by day, so it is a record of its own kind (`lifetime`) and never one of the day-by-day `days`
    # records, which its lifetime figures would overwrite.
    "me_ads": Way(
        "meesho", "lifetime",
        {
            "campaignId": ("campaign id",), "campaignName": ("campaign name",), "status": ("status",), "startDate": ("start date",),
            "spend": ("ad spend",), "revenue": ("revenue",), "units": ("orders",), "views": ("views",), "clicks": ("clicks",),
        },
        needed=("campaignId", "spend"), header_row=1, day_column="date",
    ),
    "fk_ads_placements": Way(
        "flipkart", "placements",
        {
            "campaignId": ("campaign id",), "campaignName": ("campaign name",), "placementType": ("placement type",),
            "views": ("views",), "clicks": ("clicks",), "spend": ("ad spend",), "unitsDirect": ("direct units sold",),
            "unitsIndirect": ("indirect units sold",), "revenueDirect": ("direct revenue",), "revenueIndirect": ("indirect revenue",),
        },
        needed=("campaignId", "placementType"), header_row=3,
    ),
    "fk_ads_overall": Way(
        "flipkart", "overall",
        {
            "campaignId": ("campaign id",), "skuId": ("sku id",), "listingId": ("listing id",), "productName": ("product name",),
            "cpc": ("adgroup cpc",), "views": ("views",), "clicks": ("clicks",), "spend": ("ad spend",),
            "unitsDirect": ("direct units sold",), "unitsIndirect": ("indirect units sold",),
            "revenueDirect": ("direct revenue",), "revenueIndirect": ("indirect revenue",),
        },
        needed=("campaignId", "skuId"), header_row=3,
    ),
    "fk_ads_search": Way(
        "flipkart", "search",
        {
            "campaignId": ("campaign id",), "campaignName": ("campaign name",), "query": ("query",), "views": ("views",),
            "clicks": ("clicks",), "spend": ("sum(cost)",), "unitsDirect": ("direct units sold",),
            "unitsIndirect": ("indirect units sold",), "revenueDirect": ("direct revenue",), "revenueIndirect": ("indirect revenue",),
        },
        needed=("campaignId", "query"), header_row=3,
    ),
    "fk_ads_orders": Way(
        "flipkart", "orders",
        {
            "campaignId": ("campaign id",), "orderId": ("order_id",), "advertisedFsn": ("advertised fsn id",),
            "purchasedFsn": ("purchased fsn id",), "listingId": ("listing id",), "productName": ("product name",),
            "revenue": ("total revenue (rs.)",), "unitsDirect": ("direct units sold",), "unitsIndirect": ("indirect units sold",),
        },
        needed=("campaignId", "orderId"), header_row=3, day_column="date",
    ),
}


# **ONE MONTH OF ADS, BUILT FROM THE PER-DAY RECORDS (D463, A87).** Nothing is summed: every day stays a day, so any period inside the month can still be
# answered. `days` is each day's campaigns as `platform_ads_days` holds them; the other five are each day's rows as `platform_ads_detail` holds them.
MONTH_FIELDS = ("platform", "month", "updatedOn", "days", "search", "placements", "overall", "orders", "lifetime", "trimmed")
MONTH_KINDS = ("search", "placements", "overall", "orders", "lifetime")
# Firestore's record limit is 1 MiB, counted the way Firestore counts (see `firestore_size`); a month that would not fit is refused in words, never shortened.
MOST_MONTH_BYTES = 1000 * 1000


def firestore_size(held) -> int:
    """About what Firestore counts for a value: text its UTF-8 bytes + 1, a number 8, a name its bytes + 1, plus 32 for a record. Never less than the truth."""
    if isinstance(held, dict):
        return 32 + sum(len(str(k).encode("utf-8")) + 1 + firestore_size(v) for k, v in held.items())
    if isinstance(held, (list, tuple)):
        return sum(firestore_size(v) for v in held)
    if isinstance(held, str):
        return len(held.encode("utf-8")) + 1
    return 8 if isinstance(held, (int, float)) and not isinstance(held, bool) else 1


def build_month(platform: str, month: str, days: Dict[str, Dict], details: List[Dict], updated_on: str) -> Dict[str, object]:
    """The month's record. `days` is `{day: record}` of `platform_ads_days`; `details` is every `platform_ads_detail` record of the month (any platform).

    Another platform's records are left out. A day with nothing of a kind is left out of that kind.
    """
    out: Dict[str, object] = {"platform": platform, "month": month, "updatedOn": updated_on, "days": {}, **{kind: {} for kind in MONTH_KINDS}}
    trimmed: Dict[str, List[Dict]] = {}
    for day, record in sorted(days.items()):
        campaigns = record.get("campaigns")
        if str(record.get("platform", platform)) == platform and isinstance(campaigns, dict) and campaigns:
            out["days"][day[8:10]] = campaigns
    for record in sorted(details, key=lambda one: (str(one.get("day", "")), str(one.get("campaignId", "")))):
        kind, day = str(record.get("kind", "")), str(record.get("day", ""))
        if str(record.get("platform", "")) != platform or kind not in MONTH_KINDS or not day.startswith(month):
            continue
        out[kind].setdefault(day[8:10], []).extend(record.get("rows") or [])
        # **A DAY THAT WAS HELD TO SIZE WHEN IT WAS WRITTEN SAYS SO IN THE MONTH TOO (D463 review):** the month must not look more complete than its days.
        if record.get("rowsKept") is not None and record.get("rowsInFile") is not None and record["rowsKept"] < record["rowsInFile"]:
            trimmed.setdefault(day[8:10], []).append({
                "kind": kind, "rowsInFile": record["rowsInFile"], "rowsKept": record["rowsKept"],
                **({"campaignId": record["campaignId"]} if record.get("campaignId") else {}),
            })
    if trimmed:
        out["trimmed"] = trimmed
    size = firestore_size(out)
    if size > MOST_MONTH_BYTES:
        raise table.CannotRead(
            f"The {platform} ads for {month} would make a summary of {size} bytes, past the {MOST_MONTH_BYTES} one record may hold, "
            "so it was not written; the Ads tab goes on reading that month's days one by one."
        )
    return out


def way_for(report_id: str) -> Way:
    found = WAYS.get(report_id)
    if found is None:
        raise table.CannotRead(f"Nothing here knows how to read {report_id!r} into ads.")
    return found


@dataclass(frozen=True)
class WhatAdsSaid:
    """One file's ad records, by record name, and every row it would not take."""

    report: str
    platform: str
    kind: str
    # record name -> {"campaigns": {...}} for days, {"rows": [...], "rowsInFile", "rowsKept", "day", "kind", "campaignId"?} for detail
    records: Dict[str, Dict[str, object]]
    not_read: Tuple[str, ...] = ()
    rows_in_file: int = 0


def _the_columns(columns: Tuple[str, ...], wanted: Tuple[str, ...], field: str, needed: bool) -> List[str]:
    out = []
    for name in wanted:
        found = [c for c in columns if c.strip().lower() == name]
        if len(found) == 1:
            out.append(found[0])
        elif not found:
            if needed:
                raise table.CannotRead(
                    f"There is no column called {name!r} (for {field}) in this file. It has: "
                    + ", ".join(repr(c) for c in columns) + "."
                )
        else:
            raise table.CannotRead(f"{len(found)} columns are called {name!r} (for {field}), so which is meant cannot be decided.")
    return out


def _a_figure(said: str, field: str):
    text = (said or "").strip().replace(",", "")
    if not text:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"{said!r} is not a figure") from None
    if not value.is_finite():
        raise ValueError(f"{said!r} is not a figure")
    if field in COUNTS:
        if value < 0 or value != value.to_integral_value():
            raise ValueError(f"{said!r} is not a whole number")
        return int(value)
    return float(round(value, 2))


def _size(rows: List[Dict]) -> int:
    return len(json.dumps(rows, separators=(",", ":")).encode("utf-8"))


def held_to_size(rows: List[Dict], most: int = MOST_BYTES) -> List[Dict]:
    """The rows if they fit, else the biggest-spending ones that do. **Never an arbitrary cut:** the order of what stays is spend, then views."""
    if _size(rows) <= most:
        return rows
    ranked = sorted(rows, key=lambda r: (-(r.get("spend") or r.get("revenue") or 0), -(r.get("views") or 0)))
    kept: List[Dict] = []
    used = 2
    for one in ranked:
        cost = _size([one]) + 1
        if used + cost > most:
            break
        kept.append(one)
        used += cost
    return kept


def the_digest(content: Dict) -> str:
    return hashlib.sha1(json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]


def read_ads(report_id: str, rows: table.Table, file_day: str, header_day: Optional[str]) -> WhatAdsSaid:
    """One file's rows turned into ad records.

    `file_day` is the day in the file's name; `header_day` is the day on its first line (`Start Time, ...`), which wins when there is one.
    """
    way = way_for(report_id)
    columns = tuple(rows.columns)
    where = {f: _the_columns(columns, names, f, f in way.needed) for f, names in way.columns.items()}
    day_column = _the_columns(columns, (way.day_column,), "the day", True)[0] if way.day_column else None
    own_day = header_day or file_day

    parsed: List[Tuple[str, Dict[str, object]]] = []
    not_read: List[str] = []
    count = 0
    for row in rows:
        count += 1
        said: Dict[str, object] = {}
        try:
            for field, cols in where.items():
                if field in COUNTS or field in ("spend", "cpc", "revenue", "revenueDirect", "revenueIndirect"):
                    parts = [_a_figure(row[c], field) for c in cols]
                    stated = [p for p in parts if p is not None]
                    if stated:
                        said[field] = sum(stated)
                else:
                    text = row[cols[0]].strip() if cols else ""
                    if text:
                        said[field] = text
        except ValueError as wrong:
            not_read.append(f"line {row.line}: {wrong}")
            continue
        if not said.get("campaignId"):
            not_read.append(f"line {row.line}: no campaign named, so the figures on it belong to nothing")
            continue
        if "/" in str(said["campaignId"]):
            not_read.append(f"line {row.line}: {said['campaignId']!r} cannot be the name of a campaign in a record (a slash)")
            continue
        if day_column:
            day = returns.a_day(row[day_column])
            if day is None:
                not_read.append(f"line {row.line}: {row[day_column]!r} is not a day this can read")
                continue
        else:
            day = own_day
        parsed.append((day, said))

    records: Dict[str, Dict[str, object]] = {}
    if way.kind == "days":
        by_day: Dict[str, Dict[str, Dict[str, object]]] = {}
        for day, said in parsed:
            one = dict(said)
            campaign = str(one.pop("campaignId"))
            # A campaign named twice on a day is its figures added.
            held = by_day.setdefault(day, {}).setdefault(campaign, {})
            for field, value in one.items():
                if field in ("campaignName",):
                    held.setdefault(field, value)
                else:
                    held[field] = held.get(field, 0) + value
        for day, campaigns in by_day.items():
            for campaign in campaigns.values():
                for field, value in list(campaign.items()):
                    if isinstance(value, float):
                        campaign[field] = round(value, 2)
            records[f"{way.platform}__{day}"] = {"campaigns": campaigns, "day": day}
    else:
        grouped: Dict[Tuple[str, str], List[Dict]] = {}
        for day, said in parsed:
            # `overall` is a file per campaign, so its record is about one campaign; the rest are one record per day.
            part = str(said["campaignId"]) if way.kind == "overall" else ""
            grouped.setdefault((day, part), []).append(said)
        for (day, part), group in grouped.items():
            name = f"{way.platform}__{day}__{way.kind}" + (f"__{part}" if part else "")
            kept = held_to_size(group)
            records[name] = {
                "rows": kept, "rowsInFile": len(group), "rowsKept": len(kept), "day": day, "kind": way.kind,
                **({"campaignId": part} if part else {}),
            }
    for record in records.values():
        record["digest"] = the_digest({k: v for k, v in record.items() if k != "digest"})
    return WhatAdsSaid(report_id, way.platform, way.kind, records, tuple(not_read), count)


def refuse_a_range(body: bytes) -> None:
    """A Flipkart ads file whose `End Time` is on another day than its `Start Time` holds a range, and is filed under no one day: refused."""
    lines = table.one_line_endings(table.as_text(body)).split(chr(10), 2)
    if len(lines) < 2:
        return
    start, end = (orders.the_day_in(x.split(",", 1)[1].strip().strip('"')) if "," in x else None for x in lines[:2])
    if lines[0].split(",", 1)[0].strip().lower() == "start time" and lines[1].split(",", 1)[0].strip().lower() == "end time" and end and start != end:
        raise table.CannotRead(f"this file runs from {start} to {end}, which is more than one day, so there is no one day to file it under.")


def day_in_header(body: bytes) -> Optional[str]:
    """The day on the first line of a Flipkart ads file, or nothing (shared with `views`)."""
    return views.day_in_ads_header(body)
