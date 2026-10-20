"""A stand-in Firestore for the checks of everything that writes records (A87, D482: one stand-in, not one per check file).

It answers `batchGet` and `runQuery` from the records it was given, by collection, and keeps what was committed, so a check can ask what a sink read, what it
wrote and in how many calls. Records are plain dicts; they are held and returned in Firestore's own shapes (`firestore.a_deep` / `plain_deep`).

This is support for the checks, not a check: it has none of its own, and nothing outside the `*_checks.py` files imports it.
"""

from typing import Dict, Iterable, Optional

import firestore


class Reply:
    """What the transport answers: a status, a body, `records()` (a list answer) and `ok`."""

    def __init__(self, status: int = 200, body=None):
        self.status, self._body, self.text = status, body if body is not None else {}, str(body or "")

    ok = property(lambda self: 200 <= self.status < 300)

    def json(self):
        return self._body

    def records(self):
        return self._body if isinstance(self._body, list) else None


class FakeFirestore:
    """`collections` is `{collection: {record name: plain record}}`. `fail_on` makes every write answer with that status."""

    def __init__(self, collections: Optional[Dict[str, Dict[str, dict]]] = None, fail_on: Optional[int] = None,
                 refuse: Iterable[str] = (), odd_query: bool = False):
        self.collections = {name: dict(held) for name, held in (collections or {}).items()}
        self.fail_on = fail_on
        # Record names whose commit is refused (403), as Firestore refuses one write and takes the next; `odd_query` answers a query with a map, not a list.
        self.refuse = set(refuse)
        self.odd_query = odd_query
        self.posts = []

    def post(self, url, params=None, headers=None, json=None, data=None):
        self.posts.append({"url": url, "json": json})
        if url.endswith(":batchGet"):
            found = []
            for name in json["documents"]:
                collection, record_name = name.split("/documents/", 1)[1].rsplit("/", 1)
                got = self.collections.get(collection, {}).get(record_name)
                found.append({"found": {"name": name, "fields": firestore.a_deep(got)["mapValue"]["fields"]}} if got else {"missing": name})
            return Reply(200, found)
        if url.endswith(":runQuery"):
            if self.odd_query:
                return Reply(200, {"error": "not a list"})
            query = json["structuredQuery"]
            collection = query["from"][0]["collectionId"]
            out = []
            for name, record in sorted(self.collections.get(collection, {}).items()):
                if query.get("where") and not _matches(query["where"], record):
                    continue
                out.append({"document": {"name": f"projects/p/databases/(default)/documents/{collection}/{name}",
                                         "fields": firestore.a_deep(record)["mapValue"]["fields"]}})
            # **AS FIRESTORE ANSWERS A QUERY THAT FINDS NOTHING:** one entry with a read time and no document.
            return Reply(200, out or [{"readTime": "2026-10-21T00:00:00Z"}])
        if url.endswith(":commit") and any(w["update"]["name"].rsplit("/", 1)[-1] in self.refuse for w in json["writes"]):
            return Reply(403, {"error": {"status": "PERMISSION_DENIED"}})
        return Reply(self.fail_on or 200, {})

    def commits(self) -> int:
        """How many commit calls were sent."""
        return len([p for p in self.posts if p["url"].endswith(":commit")])

    def asked(self) -> list:
        """The kinds of call sent, in order (`batchGet`, `runQuery`, `commit`)."""
        return [p["url"].rsplit(":", 1)[-1] for p in self.posts]

    def written_where(self) -> Dict[str, str]:
        """Every record committed, by name, with the collection it was written into."""
        return {
            write["update"]["name"].rsplit("/", 1)[-1]: write["update"]["name"].split("/documents/", 1)[1].rsplit("/", 1)[0]
            for post in self.posts if post["url"].endswith(":commit") for write in post["json"]["writes"]
        }

    def written(self) -> Dict[str, dict]:
        """Every record committed, by name, as plain data (a later write of a name replaces an earlier one)."""
        out: Dict[str, dict] = {}
        for post in self.posts:
            if post["url"].endswith(":commit"):
                for write in post["json"]["writes"]:
                    out[write["update"]["name"].rsplit("/", 1)[-1]] = firestore.plain_deep({"mapValue": {"fields": write["update"]["fields"]}})
        return out


_OPS = {
    "EQUAL": lambda a, b: a == b, "LESS_THAN": lambda a, b: a < b, "LESS_THAN_OR_EQUAL": lambda a, b: a <= b,
    "GREATER_THAN": lambda a, b: a > b, "GREATER_THAN_OR_EQUAL": lambda a, b: a >= b,
}


def _matches(where: dict, record: dict) -> bool:
    """A query's filter asked of one plain record, as Firestore asks it: a record without the field never matches; AND and OR as named."""
    if "compositeFilter" in where:
        both = [_matches(one, record) for one in where["compositeFilter"]["filters"]]
        return all(both) if where["compositeFilter"]["op"] == "AND" else any(both)
    asked = where["fieldFilter"]
    field = asked["field"]["fieldPath"]
    return field in record and _OPS[asked["op"]](str(record[field]), asked["value"]["stringValue"])
