"""Collecting an uploaded list through the account-service interface.

`AccountPageLoader` is the only supported way to read an upload. The service
has produced several broken paging shapes (see `sources.py`), so collection
here is defensive: it keeps paging until the service ends the list, stalls, or
runs out of rope, and it always states why it stopped.

Two signals that look alike are kept apart on purpose, because conflating them
loses rows:

* *Stalling* is about the cursor. Consecutive pages that carry nothing new mean
  the service is no longer advancing, so the read must end. That says nothing
  about whether the rows already collected were real.
* *Replaying* is about a page. A page whose content we have seen before is only
  a **suspected** replay. The protocol cannot decide it: an upload may
  legitimately contain two identical pages, and dropping the second one silently
  deletes real rows.

So no row is ever discarded during the read. Both readings are kept — every row
served, and the rows left after removing repeated pages — and the declared row
count of the upload (`expected_row_count`) picks between them. Without one, the
result reports `verified_complete="unknown"` rather than guessing.

Whether a read that stops early while reporting `truncated=False` is a genuine
end is likewise undecidable at this layer; that claim is recorded separately in
`service_claimed_complete`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from repair_lab import AccountPageLoader

# Stop of last resort. A cursor that neither advances nor repeats a page we
# have already ingested would otherwise page forever.
PAGE_REQUEST_LIMIT = 10_000

# How many consecutive pages may yield nothing new before we call it stalled.
# Must be >= 2: a service that replays each page once (ReplayingLoader) is
# recoverable and produces exactly one barren page between useful ones.
NO_PROGRESS_LIMIT = 2


@dataclass(frozen=True)
class ReadResult:
    """Rows collected from one upload, and how much of it we can vouch for."""

    rows: list[dict[str, Any]]
    """The working answer: the reading of the upload we would act on."""

    service_claimed_complete: bool
    """Whether the read ended because the service reported `truncated=False`."""

    verified_complete: str
    """`"true"` / `"false"` / `"unknown"` — checked against a declared size."""

    reason: str
    pages_requested: int

    rows_served: int
    """Every row the service handed over, duplicates included."""

    rows_deduped: int
    """Rows left after removing pages whose content had already been served."""

    # Compatibility only: `aj_work/audit.py` and `aj_work/discrepancies.py`
    # read `read.complete`, which predates the claimed/verified split.
    pages_with_new_rows: int = 0

    @property
    def complete(self) -> bool:
        """Alias of `service_claimed_complete`, kept for existing callers.

        `aj_work/audit.py` and `aj_work/discrepancies.py` read `read.complete`.
        It is the service's *claim*, never a verified fact — use
        `verified_complete` for that.
        """
        return self.service_claimed_complete

    @property
    def barren_pages(self) -> int:
        """Pages the service served that carried nothing we had not seen.

        Compatibility only, for `aj_work/audit.py`.
        """
        return self.pages_requested - self.pages_with_new_rows


def _fingerprint(rows: list[dict[str, Any]]) -> str:
    """Identify a page by its content, not by the cursor that produced it.

    Deliberately not keyed on row ids: an upload is not guaranteed to give
    every row a unique one, and a replayed page is a property of the page.
    """
    return json.dumps(rows, sort_keys=True, default=str)


def _resolve(
    served: list[dict[str, Any]],
    fresh: list[dict[str, Any]],
    expected_row_count: int | None,
) -> tuple[list[dict[str, Any]], str, str]:
    """Choose between the two readings of the upload, and say how sure we are.

    Returns `(rows, verified_complete, note)` where `note` is appended to the
    reason. Repeated pages are only a *suspected* replay, so this is the one
    place allowed to prefer one reading over the other — and only ever because
    a declared size says so.
    """
    if expected_row_count is None:
        note = ""
        if len(served) != len(fresh):
            note = (
                f"; {len(served)} rows served, {len(fresh)} after removing "
                "repeated pages — cannot tell which is right without a "
                "declared size"
            )
        return served, "unknown", note

    expected = expected_row_count
    if len(fresh) == expected:
        return fresh, "true", f"; matches declared size {expected}"
    if len(served) == expected:
        return (
            served,
            "true",
            f"; repeated pages were legitimate, matches declared size {expected}",
        )
    return (
        fresh,
        "false",
        f"; expected {expected} rows, collected {len(fresh)}",
    )


def collect_rows(
    loader: AccountPageLoader,
    *,
    page_size: int = 25,
    expected_row_count: int | None = None,
) -> ReadResult:
    """Page through `loader` until it ends, stalls, or runs out of rope.

    Pass `expected_row_count` (the upload's declared size) to get a verified
    answer; without it the read still returns every row it was served.
    """
    served: list[dict[str, Any]] = []
    fresh: list[dict[str, Any]] = []
    seen_pages: set[str] = set()
    cursor: str | None = None
    requested = 0
    barren = 0
    claimed = False

    while True:
        page = loader.load_page(cursor=cursor, page_size=page_size)
        requested += 1

        # Never discard rows here: a repeated page may be a real part of the
        # upload, and only the declared size can tell.
        served.extend(page.rows)

        fingerprint = _fingerprint(page.rows)
        if fingerprint in seen_pages:
            barren += 1
        else:
            seen_pages.add(fingerprint)
            fresh.extend(page.rows)
            barren = 0

        if not page.truncated:
            claimed = True
            reason = "service reported the end of the list"
            break

        if page.next_cursor is None:
            reason = "service reported more rows but supplied no cursor"
            break

        if barren >= NO_PROGRESS_LIMIT:
            reason = (
                f"cursor stopped advancing at {page.next_cursor!r} "
                f"after {barren} pages with no new rows"
            )
            break

        if requested >= PAGE_REQUEST_LIMIT:
            reason = f"gave up after {PAGE_REQUEST_LIMIT} page requests"
            break

        cursor = page.next_cursor

    rows, verified, note = _resolve(served, fresh, expected_row_count)
    return ReadResult(
        rows=rows,
        service_claimed_complete=claimed,
        verified_complete=verified,
        reason=reason + note,
        pages_requested=requested,
        rows_served=len(served),
        rows_deduped=len(fresh),
        pages_with_new_rows=len(seen_pages),
    )
