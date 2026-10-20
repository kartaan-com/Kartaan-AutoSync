"""What every record-writing reader shares (A87; his standing order D458 / D482: built once in the shared layer, never a copy per report).

Claims, product performance, listing quality and the shop's own figures each turn a platform file into records for the seller's database. The parts that are
the same for all of them live here and nowhere else:

* `the_digest` -- the fingerprint of what a record SAYS (never of the day it was read), so the same file read twice writes nothing;
* `require_columns` -- a file lacking a column it cannot be read without stops, in words naming the columns it has;
* `a_figure` -- a figure from text: a blank or `NA` is nothing (never nought), anything else that is not a finite figure in range is refused (`ValueError`);
* `a_safe_name` -- a platform-supplied word that is to name a record: empty, a slash, a dot name or a very long one is refused.

Nothing here opens a file, a clock or a connection.
"""

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional, Sequence, Tuple

import table

# What the fingerprint never covers: the day a record was read and the fingerprint itself.
NOT_IN_THE_DIGEST = ("fileDay", "digest")
# Firestore refuses a record name past 1500 bytes; a platform word is held to less so the name round it fits.
MOST_NAME_BYTES = 1000


@dataclass(frozen=True)
class RecordKind:
    """What one kind of record in the seller's database may hold, said once: `firestore.a_record_write` checks every record against it.

    `fields` are the only fields it may hold (absent ones are absent). `required_days` must be there and be days; `days` are checked when there;
    `months` are `yyyy-mm`. `what` names the record in the words of a refusal.
    """

    collection: str
    fields: Tuple[str, ...]
    what: str
    required_days: Tuple[str, ...] = ()
    days: Tuple[str, ...] = ()
    months: Tuple[str, ...] = ()


def the_digest(record: Dict[str, object], leave_out: Sequence[str] = ()) -> str:
    """A fingerprint of what a record says. `leave_out` names any further fields it must not cover (a history that grows with every change)."""
    said = {k: v for k, v in sorted(record.items()) if k not in NOT_IN_THE_DIGEST and k not in leave_out}
    return hashlib.sha1(json.dumps(said, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]


def require_columns(rows: table.Table, wanted: Sequence[str], what: str) -> None:
    """Refuse a file that lacks a column it cannot be read without, in words naming the columns it does have."""
    missing = [c for c in wanted if c not in rows.columns]
    if missing:
        raise table.CannotRead(
            f"This does not look like {what}. It has no " + ", ".join(repr(c) for c in missing)
            + ". It has: " + ", ".join(repr(c) for c in rows.columns if c) + ". Nothing was read."
        )


def a_figure(said: str, most: Optional[float] = None, whole: bool = False, negative: bool = False) -> Optional[Decimal]:
    """A figure out of a cell. A blank or `NA` is nothing; a figure that is not finite, is negative (unless `negative`), is past `most`, or (with `whole`) has a fraction is refused."""
    text = (said or "").replace("₹", "").replace("%", "").replace(",", "").strip()
    if not text or text.upper() == "NA":
        return None
    try:
        value = Decimal(text)
        if not value.is_finite() or (value < 0 and not negative) or (most is not None and value > Decimal(str(most))):
            raise ValueError(f"{said!r} is not a figure" + (f" from 0 to {most:g}" if most is not None else ""))
        if whole and value != value.to_integral_value():
            raise ValueError(f"{said!r} is not a whole count")
    except (InvalidOperation, ArithmeticError):
        raise ValueError(f"{said!r} is not a figure") from None
    return value


def a_safe_name(word: str) -> bool:
    """May this platform-supplied word name a record? Not empty, no slash, not a dot name, not very long."""
    return bool(word) and "/" not in word and word not in (".", "..") and len(word.encode("utf-8")) <= MOST_NAME_BYTES
