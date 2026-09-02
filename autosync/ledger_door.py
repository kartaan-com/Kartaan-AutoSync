"""Writing the seller's sales ledger. The doing half of `ledger.py`.

**THE TRANSPORT IS HANDED IN**, exactly as it is for Drive, Amazon and Firestore,
so every line here is checked with no account, no sheet and no internet. Nothing
in this file opens a connection.

**EVERY CALL BELOW IS THE ONE KARTAAN ALREADY MAKES.** They are not worked out
here: they are read off the ERP's own `src/shared/data/sheet-store.js`, which has
been reviewed and whose faults have already been found and fixed. **One fact,
one shape, both halves** -- writing a second, different way of talking to Google
is the duplication D119 exists to prevent.

| What | The call |
|---|---|
| is this our sheet | `GET /v4/spreadsheets/{id}` with `fields=sheets.properties.title` |
| the whole ledger | `GET /v4/spreadsheets/{id}/values/{tab}!A:AB` |
| add rows | `POST .../values/{tab}!A:AB:append`, `valueInputOption=RAW`, `insertDataOption=INSERT_ROWS` |
| change rows | `POST .../values:batchUpdate`, `valueInputOption=RAW` |

**IT NEEDS NO PERMISSION THE SELLER HAS NOT ALREADY GIVEN (D137).** Google's own
scope list marks `drive.file` as accepted by the Sheets API, Non-sensitive, and
Recommended; both scopes named for spreadsheets are Sensitive and neither is
asked for. **What that makes load-bearing: KARTAAN MUST HAVE CREATED THE SHEET.**
A spreadsheet the seller made by hand is not a file this app created, so
`drive.file` cannot reach it at all -- which is why a sheet that does not answer
is refused in words rather than retried.

---

**THREE THINGS THIS REFUSES TO DO:**

- **It never removes a row.** A sale that did not happen is a sale in a state
  that says so. A row taken out of a sheet moves every row under it, and every
  remembered row number becomes wrong -- including the ones in the plan it is
  holding.
- **It never writes to row 1.** That row is the column names, and a sale written
  over them makes every later read of the sheet refuse.
- **It never writes a plan it did not build the numbers for.** The row numbers in
  a plan describe the sheet as it was READ; if anything was appended in between,
  they are stale. The append is done LAST for exactly this reason -- appending
  first would move nothing, but reading and planning again would.
"""

from typing import Callable, Dict, List, Optional, Sequence, Tuple

from ledger import LedgerRefused, Plan
from sales import COLUMNS, THE_TAB, the_whole_tab

# Where the Sheets API is. Written once so nothing can invent a near-miss.
API = "https://sheets.googleapis.com"

# What is asked for when the sheet is checked. **Only the tab names** -- asking
# for the whole spreadsheet would pull every cell back to answer one question.
JUST_THE_TAB_NAMES = "sheets.properties.title"


def _quote(text: str) -> str:
    """A range as it goes in a path. `orders!A:AB` -> `orders%21A%3AAB`."""
    out = []
    for ch in text:
        if ch.isalnum() or ch in "-._~":
            out.append(ch)
        else:
            out.append("".join(f"%{b:02X}" for b in ch.encode("utf-8")))
    return "".join(out)


def why_that_sheet_will_not_do(about) -> Optional[str]:
    """Why this is not the seller's sales ledger, or nothing at all.

    **THE SAME QUESTION THE ERP ASKS, and it is asked because of a live fault:**
    a stored sheet id once pointed at an unrelated empty spreadsheet, and every
    write failed with *"Unable to parse range"* -- a message about syntax, for a
    problem about identity.

    **AND THE ERP'S OWN VERSION OF THIS EXISTED, WAS CHECKED, AND WAS CALLED BY
    NOTHING** until an independent reviewer found it. It is called here, and a
    check proves it is called.
    """
    if not isinstance(about, dict):
        return (
            "Google said nothing about that spreadsheet, so nothing has been "
            "written to it."
        )
    tabs = []
    for one in about.get("sheets") or []:
        if isinstance(one, dict):
            tabs.append(str((one.get("properties") or {}).get("title") or "").strip())
    if THE_TAB not in tabs:
        return (
            f'That spreadsheet has no "{THE_TAB}" tab in it '
            f"(it has {', '.join(t for t in tabs if t) or 'none'}), so it is not "
            "this business's sales ledger and nothing has been written to it."
        )
    return None


class LedgerDoor:
    """The seller's sales ledger, as something a run can read and write.

    `ask` is handed in and is the only thing that touches Google. It is called
    as `ask(method, path, query=..., body=...)` and answers what Google said.
    """

    def __init__(self, ask: Callable, sheet_id: str):
        if not callable(ask):
            raise LedgerRefused("The sales ledger needs a way of asking Google.")
        if not str(sheet_id or "").strip():
            raise LedgerRefused(
                "The sales ledger needs the id of the seller's own sheet. "
                "Kartaan creates that sheet at set-up (D137); a pasted id is "
                "refused, because a file this app did not create cannot be "
                "reached with the permission the seller has given."
            )
        self._ask = ask
        self._sheet_id = str(sheet_id).strip()
        self._checked = False

    # ------------------------------------------------------------- reading

    def make_sure_it_is_ours(self) -> None:
        """Asked ONCE, before a single cell is read or written.

        It costs a request, and the answer cannot change without somebody editing
        the sheet -- at which point the column check catches it anyway.
        """
        if self._checked:
            return
        about = self._ask(
            "GET",
            f"/v4/spreadsheets/{self._sheet_id}",
            query={"fields": JUST_THE_TAB_NAMES},
        )
        wrong = why_that_sheet_will_not_do(about)
        if wrong:
            raise LedgerRefused(wrong)
        self._checked = True

    def everything(self) -> List[List[str]]:
        """The whole ledger, in ONE call, whatever it holds.

        **THAT IS THE WHOLE REASON SALES ARE IN A SHEET (D126)**: thirty thousand
        of them come back in one request, where thirty thousand documents would
        be thirty thousand reads.
        """
        self.make_sure_it_is_ours()
        said = self._ask(
            "GET",
            f"/v4/spreadsheets/{self._sheet_id}/values/{_quote(the_whole_tab())}",
        )
        values = (said or {}).get("values") if isinstance(said, dict) else None
        return [list(r) for r in (values or [])]

    # ------------------------------------------------------------- writing

    def write_the_header(self) -> None:
        """Put the column names on row 1 of an empty sheet.

        **ONLY EVER ON AN EMPTY SHEET.** Written over a sheet that already holds
        sales, this would replace the first sale with the column names.
        """
        self._ask(
            "POST",
            f"/v4/spreadsheets/{self._sheet_id}/values/{_quote(the_whole_tab())}:append",
            query={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
            body={"values": [list(COLUMNS)]},
        )

    def carry_out(self, plan: Plan) -> Dict[str, int]:
        """Do what the plan says: change rows first, add rows last.

        **THE ORDER IS THE POINT.** A plan's row numbers describe the sheet as it
        was read. Appending first adds rows at the bottom, which moves nothing --
        but any later re-read would renumber, and a plan is not re-read. Changing
        first and appending last keeps every number in the plan true at the
        moment it is used.

        **NOTHING IS SENT WHEN THERE IS NOTHING TO SEND.** A run on a quiet day
        makes no write call at all, rather than a call that changes nothing.
        """
        if not isinstance(plan, Plan):
            raise LedgerRefused(
                f"The ledger is written from a plan, and this is a "
                f"{type(plan).__name__}."
            )
        self.make_sure_it_is_ours()

        for row, _ in plan.update:
            if row <= 1:
                raise LedgerRefused(
                    f"Something asked to write a sale over row {row}. Row 1 is the "
                    "column names, and writing a sale there makes every later "
                    "read of the sheet refuse."
                )
        for cells in plan.append:
            if len(cells) != len(COLUMNS):
                raise LedgerRefused(
                    f"A row to be added has {len(cells)} cells where the ledger "
                    f"has {len(COLUMNS)} columns, so it would be written into the "
                    "wrong columns."
                )

        changed = 0
        if plan.update:
            # **ONE CALL FOR EVERY CHANGED ROW, not one call each.** A settlement
            # landing for three hundred sales is one request, not three hundred.
            self._ask(
                "POST",
                f"/v4/spreadsheets/{self._sheet_id}/values:batchUpdate",
                body={
                    "valueInputOption": "RAW",
                    "data": [
                        {"range": _a_row_range(row), "values": [list(cells)]}
                        for row, cells in plan.update
                    ],
                },
            )
            changed = len(plan.update)

        added = 0
        if plan.append:
            self._ask(
                "POST",
                f"/v4/spreadsheets/{self._sheet_id}/values/"
                f"{_quote(the_whole_tab())}:append",
                query={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
                body={"values": [list(cells) for cells in plan.append]},
            )
            added = len(plan.append)

        return {"added": added, "changed": changed}


def _a_row_range(row: int) -> str:
    """One row of the ledger, as a range. Worked out, never typed."""
    from sales import the_range_for

    return the_range_for(row)
