"""Collecting an uploaded list through the account-service interface.

`AccountPageLoader` is the only supported way to read an upload. The service
has produced several broken paging shapes (see `sources.py`), so collection
here is defensive: it keeps paging while pages yield rows it has not already
seen, and stops with a stated reason when they stop.

One shape is deliberately *not* detectable at this layer. A read that stops
early and reports `truncated=False` is indistinguishable from a genuine end
without an independent expected row count. `ReadResult.complete` records only
what the service claimed; verifying that claim is the caller's job.
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
    complete: bool
    reason: str
    pages_requested: int
    pages_with_new_rows: int

    @property
    def barren_pages(self) -> int:
        """Pages the service served that carried nothing we had not seen."""
        return self.pages_requested - self.pages_with_new_rows


def _fingerprint(rows: list[dict[str, Any]]) -> str:
    """Identify a page by its content, not by the cursor that produced it.

    Deliberately not keyed on row ids: an upload is not guaranteed to give
    every row a unique one, and a replayed page is a property of the page.
    """
    return json.dumps(rows, sort_keys=True, default=str)


def collect_rows(
    loader: AccountPageLoader,
    *,
    page_size: int = 25,
) -> ReadResult:
    """Page through `loader` until it ends, stalls, or runs out of rope."""
    rows: list[dict[str, Any]] = []
    seen_pages: set[str] = set()
    cursor: str | None = None
    requested = 0
    no_progress = 0

    while True:
        page = loader.load_page(cursor=cursor, page_size=page_size)
        requested += 1

        fingerprint = _fingerprint(page.rows)
        if fingerprint in seen_pages:
            no_progress += 1
        else:
            seen_pages.add(fingerprint)
            rows.extend(page.rows)
            no_progress = 0

        if not page.truncated:
            return ReadResult(
                rows=rows,
                complete=True,
                reason="service reported the end of the list",
                pages_requested=requested,
                pages_with_new_rows=len(seen_pages),
            )

        if page.next_cursor is None:
            return ReadResult(
                rows=rows,
                complete=False,
                reason="service reported more rows but supplied no cursor",
                pages_requested=requested,
                pages_with_new_rows=len(seen_pages),
            )

        if no_progress >= NO_PROGRESS_LIMIT:
            return ReadResult(
                rows=rows,
                complete=False,
                reason=(
                    f"cursor stopped advancing at {page.next_cursor!r} "
                    f"after {no_progress} pages with no new rows"
                ),
                pages_requested=requested,
                pages_with_new_rows=len(seen_pages),
            )

        if requested >= PAGE_REQUEST_LIMIT:
            return ReadResult(
                rows=rows,
                complete=False,
                reason=f"gave up after {PAGE_REQUEST_LIMIT} page requests",
                pages_requested=requested,
                pages_with_new_rows=len(seen_pages),
            )

        cursor = page.next_cursor
