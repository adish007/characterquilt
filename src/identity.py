"""What counts as one company, and which rows make that hard to answer.

The policy, stated so a check can enforce it:

1. A row's company identity is its ``company_id`` as text, stripped. Rows
   sharing that value are one company.
2. A row whose ``company_id`` is missing, null, or blank after stripping has
   *no* identity. It is never merged with any other row: its *occurrence* in
   the upload — not its uploaded ``id``, which no upload guarantees to be
   unique — is what makes it one company on its own, flagged unidentified.
3. Nothing else merges or splits rows. Name and domain are evidence. They are
   reported as conflicts and never used to decide identity.

Rule 2 is the load-bearing one. Treating absent identity as a shared value is
what lets `str(None)` fold unrelated companies into a single bucket, and the
same fault reappears as `""` on a differently shaped upload. Rule 3 is what
keeps a subsidiary that shares its parent's domain from being deleted.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

IDENTITY_FIELD = "company_id"

# Fields a row may carry that would silently displace the request's own
# selections. Presence is a fact about the row; whether it conflicts depends
# on what the request asked for.
OVERRIDE_FIELDS = ("saved_brand_kit_id", "saved_template_id")


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def row_label(row: dict[str, Any], index: int) -> str:
    """A stable handle for a row, for reporting and for keying unidentified rows."""
    return _text(row.get("id")) or f"row-at-index-{index}"


def unique_row_labels(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    """Per-row labels that are unique across the whole upload.

    ``row_label`` trusts the uploaded ``id``, but nothing guarantees an upload
    gives distinct ids. Two rows sharing one id would otherwise be
    indistinguishable in a deliverable, and — for unidentified rows, whose key
    is built from the label — would merge into a single company in violation of
    rule 2. Labels seen exactly once are left alone so the common upload reads
    naturally; a repeated label gets ``#0``, ``#1``, ... on every occurrence in
    order, so no row silently borrows another's provenance.
    """
    bases = [row_label(row, index) for index, row in enumerate(rows)]
    counts: dict[str, int] = {}
    for base in bases:
        counts[base] = counts.get(base, 0) + 1
    seen: dict[str, int] = {}
    labels: list[str] = []
    for base in bases:
        if counts[base] == 1:
            labels.append(base)
            continue
        occurrence = seen.get(base, 0)
        seen[base] = occurrence + 1
        labels.append(f"{base}#{occurrence}")
    return tuple(labels)


def identity_of(
    row: dict[str, Any], index: int, label: str | None = None
) -> tuple[str, bool]:
    """Return ``(key, identified)`` for one row under the policy above.

    ``label`` lets a caller that already resolved upload-wide unique labels
    pass one in; without it the row's own label is used, which is only safe
    when uploaded ids are known to be distinct.
    """
    company_id = _text(row.get(IDENTITY_FIELD))
    if company_id:
        return company_id, True
    return f"unidentified:{label or row_label(row, index)}", False


def domain_of(row: dict[str, Any]) -> str:
    return _text(row.get("domain")).lower()


@dataclass(frozen=True)
class Company:
    """One logical company and every uploaded row that resolved to it."""

    key: str
    identified: bool
    rows: tuple[dict[str, Any], ...]
    row_labels: tuple[str, ...]

    @property
    def names(self) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for row in self.rows:
            seen.setdefault(_text(row.get("company_name")), None)
        return tuple(seen)

    @property
    def domains(self) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for row in self.rows:
            seen.setdefault(domain_of(row), None)
        return tuple(seen)


@dataclass(frozen=True)
class Inventory:
    """Every logical company on an upload, plus the rows that contest it."""

    rows: tuple[dict[str, Any], ...]
    companies: tuple[Company, ...]

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def company_count(self) -> int:
        return len(self.companies)

    @property
    def unidentified(self) -> tuple[Company, ...]:
        return tuple(c for c in self.companies if not c.identified)

    @property
    def identified(self) -> tuple[Company, ...]:
        return tuple(c for c in self.companies if c.identified)

    @property
    def duplicated(self) -> tuple[Company, ...]:
        """Companies the upload names more than once."""
        return tuple(c for c in self.companies if len(c.rows) > 1)

    @property
    def extra_rows(self) -> int:
        """Rows beyond the first for every company named more than once."""
        return sum(len(c.rows) - 1 for c in self.duplicated)

    @property
    def id_spans_domains(self) -> tuple[Company, ...]:
        """One identity, several domains. Possibly two customers, possibly a typo."""
        return tuple(
            c for c in self.identified if len({d for d in c.domains if d}) > 1
        )

    @property
    def domain_spans_ids(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        """One domain, several identities. Merging these would delete companies."""
        by_domain: dict[str, list[str]] = {}
        for company in self.identified:
            for domain in company.domains:
                if domain:
                    by_domain.setdefault(domain, []).append(company.key)
        return tuple(
            (domain, tuple(sorted(set(keys))))
            for domain, keys in sorted(by_domain.items())
            if len(set(keys)) > 1
        )

    def override_rows(
        self,
        *,
        brand_kit_id: str | None = None,
        template_id: str | None = None,
    ) -> tuple[tuple[str, dict[str, Any], tuple[str, ...]], ...]:
        """Rows carrying saved selections that would displace the request's.

        With the request's selections supplied, only rows that actually differ
        from what was asked for are returned.
        """
        wanted = {
            "saved_brand_kit_id": brand_kit_id,
            "saved_template_id": template_id,
        }
        found: list[tuple[str, dict[str, Any], tuple[str, ...]]] = []
        labels = unique_row_labels(list(self.rows))
        for index, row in enumerate(self.rows):
            conflicts = tuple(
                field
                for field in OVERRIDE_FIELDS
                if field in row
                and (wanted[field] is None or _text(row[field]) != wanted[field])
            )
            if conflicts:
                found.append((labels[index], row, conflicts))
        return tuple(found)

    def contested_row_labels(
        self,
        *,
        brand_kit_id: str | None = None,
        template_id: str | None = None,
    ) -> tuple[str, ...]:
        """Every row a human would have to look at to trust the count."""
        labels: set[str] = set()
        for company in self.unidentified + self.duplicated + self.id_spans_domains:
            labels.update(company.row_labels)
        conflicted = {key for _, keys in self.domain_spans_ids for key in keys}
        for company in self.identified:
            if company.key in conflicted:
                labels.update(company.row_labels)
        for label, _, _ in self.override_rows(
            brand_kit_id=brand_kit_id, template_id=template_id
        ):
            labels.add(label)
        return tuple(sorted(labels))


def build_inventory(rows: list[dict[str, Any]]) -> Inventory:
    """Group uploaded rows into logical companies under the stated policy."""
    grouped: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    identified: dict[str, bool] = {}

    labels = unique_row_labels(rows)
    for index, row in enumerate(rows):
        label = labels[index]
        key, is_identified = identity_of(row, index, label)
        grouped.setdefault(key, []).append((label, row))
        identified[key] = is_identified

    companies = tuple(
        Company(
            key=key,
            identified=identified[key],
            rows=tuple(row for _, row in entries),
            row_labels=tuple(label for label, _ in entries),
        )
        for key, entries in grouped.items()
    )
    return Inventory(rows=tuple(rows), companies=companies)
