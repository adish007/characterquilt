from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from identity import Company, Inventory, build_inventory
from paging import collect_rows

REQUIRED_ASSET_TYPES = (
    "landing_page",
    "linkedin_ad_1",
    "linkedin_ad_2",
    "linkedin_ad_3",
)


@dataclass(frozen=True)
class ToolPage:
    rows: list[dict[str, Any]]
    next_cursor: str | None
    truncated: bool


class AccountPageLoader(Protocol):
    def load_page(
        self,
        *,
        cursor: str | None = None,
        page_size: int = 25,
    ) -> ToolPage: ...


class TargetAccountTool:
    """Deterministic stand-in for the paginated uploaded-account service."""

    def __init__(self, accounts: list[dict[str, Any]]) -> None:
        self._accounts = [dict(account) for account in accounts]

    def load_page(
        self,
        *,
        cursor: str | None = None,
        page_size: int = 25,
    ) -> ToolPage:
        start = int(cursor or "0")
        rows = self._accounts[start : start + page_size]
        next_index = start + len(rows)
        next_cursor = (
            str(next_index) if next_index < len(self._accounts) else None
        )
        return ToolPage(
            rows=rows,
            next_cursor=next_cursor,
            truncated=next_cursor is not None,
        )


def _domain_owners(inventory: Inventory) -> dict[str, set[str]]:
    """Which company ids claim each domain."""
    owners: dict[str, set[str]] = {}
    for company in inventory.identified:
        for domain in company.domains:
            if domain:
                owners.setdefault(domain, set()).add(company.key)
    return owners


def choose_domain(
    company: Company, owners: dict[str, set[str]]
) -> tuple[str, str]:
    """Pick the one domain that personalizes a company. Returns (domain, note).

    A landing page needs exactly one address. If none exists, the caller must
    stop campaign construction rather than represent an empty address as a
    deliverable.
    A shared domain is *less preferred*, never disqualified: three EMEA
    subsidiaries and their parents hold nothing else, and refusing it would
    delete a company over a data-quality problem.

    Order is service order, so the tiebreak is stable across page sizes. It is
    only reached once a shared domain -- the case where the wrong pick ships
    another company's website -- has already been ruled out.
    """
    domains = [d for d in company.domains if d]
    if not domains:
        return "", "no domain on file"
    sole = [d for d in domains if len(owners.get(d, ())) <= 1]
    if len(sole) == 1:
        return sole[0], ""
    if sole:
        return sole[0], f"several sole-owned domains ({', '.join(sole)}); used the first"
    shared_with = sorted(owners.get(domains[0], set()) - {company.key})
    return domains[0], f"only domain is shared with {', '.join(shared_with)}"


def _make_deliverables(
    inventory: Inventory,
    *,
    brand_kit_id: str,
    template_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """One of each required asset per *company* -- never per row."""
    owners = _domain_owners(inventory)
    deliverables: list[dict[str, Any]] = []
    notes: list[dict[str, str]] = []

    for company in inventory.companies:
        domain, note = choose_domain(company, owners)
        if note:
            notes.append(
                {"company": company.key, "domain_used": domain, "note": note}
            )
        for asset_type in REQUIRED_ASSET_TYPES:
            deliverables.append(
                {
                    "company_key": company.key,
                    "company_name": company.names[0] if company.names else "",
                    "identified": company.identified,
                    "domain": domain,
                    "asset_type": asset_type,
                    # The request wins. A row's saved selections are recorded
                    # as exceptions and never applied: a disclosed override is
                    # still creative in the brand the customer did not pick.
                    "brand_kit_id": brand_kit_id,
                    "template_id": template_id,
                    # Every row that resolved to this company, so a deliverable
                    # stays traceable when several rows named the same company.
                    "source_row_ids": list(company.row_labels),
                }
            )
    return deliverables, notes


def build_campaign_plan(
    tool: AccountPageLoader,
    *,
    brand_kit_id: str,
    template_id: str,
    page_size: int = 25,
    expected_row_count: int | None = None,
) -> dict[str, Any]:
    """Read the upload, group it into companies, and build one set per company.

    Grouping happens after the whole read, so the answer cannot depend on page
    size -- the defect that made the same upload report 214, 214 and 211.
    """
    read = collect_rows(
        tool, page_size=page_size, expected_row_count=expected_row_count
    )
    inventory = build_inventory(read.rows)
    deliverables, domain_notes = _make_deliverables(
        inventory, brand_kit_id=brand_kit_id, template_id=template_id
    )
    exceptions = [
        {
            "source_row_id": label,
            "fields": list(fields),
            "ignored": {field: row.get(field) for field in fields},
        }
        for label, row, fields in inventory.override_rows(
            brand_kit_id=brand_kit_id, template_id=template_id
        )
    ]

    return {
        "companies": [company.key for company in inventory.companies],
        "source_row_ids": [
            label for company in inventory.companies for label in company.row_labels
        ],
        "deliverables": deliverables,
        "exceptions": exceptions,
        "domain_notes": domain_notes,
        "brand_kit_id": brand_kit_id,
        "template_id": template_id,
        "rows_read": len(read.rows),
        "service_claimed_complete": read.service_claimed_complete,
        "verified_complete": read.verified_complete,
        "completion_reason": read.reason,
    }


def evaluate_campaign_coverage(
    plan: dict[str, Any],
    accounts: list[dict[str, Any]],
    *,
    brand_kit_id: str,
    template_id: str,
    page_sizes: tuple[int, ...] = (10, 25, 100),
) -> tuple[bool, str]:
    """Reconcile a plan against the upload it claims to cover.

    The check it replaces asked only whether rows *already in the plan* had
    four assets each, so a plan holding a single row passed, and it finished by
    echoing the plan's own `complete` flag. That is why a run that shipped six
    duplicates and dropped six companies was reported as passing.

    Nothing self-reported is trusted here. The expected companies are re-derived
    from the upload through the loader interface, and the requested brand kit
    and template come from the caller, not from the plan.
    """
    read = collect_rows(
        TargetAccountTool(accounts), expected_row_count=len(accounts)
    )
    inventory = build_inventory(read.rows)
    expected = {company.key for company in inventory.companies}
    rows_of = {c.key: list(c.row_labels) for c in inventory.companies}
    owners = _domain_owners(inventory)
    domains_of: dict[str, str] = {}
    for company in inventory.companies:
        domain, _ = choose_domain(company, owners)
        if not domain:
            return False, f"company {company.key} has no usable domain"
        domains_of[company.key] = domain
    deliverables = plan.get("deliverables", [])

    shipped: dict[str, list[str]] = {}
    for item in deliverables:
        shipped.setdefault(str(item["company_key"]), []).append(
            str(item["asset_type"])
        )

    # 1 coverage, 3 no orphans
    missing = expected - shipped.keys()
    if missing:
        return False, f"{len(missing)} companies never campaigned, e.g. {min(missing)}"
    orphans = shipped.keys() - expected
    if orphans:
        return False, f"{len(orphans)} deliverables name no uploaded company, e.g. {min(orphans)}"

    # 2 exactly one of each asset type, 4 no duplicates
    for key, asset_types in sorted(shipped.items()):
        if len(asset_types) != len(set(asset_types)):
            return False, f"company {key} has duplicate deliverables"
        if set(asset_types) != set(REQUIRED_ASSET_TYPES):
            return False, f"company {key} has the wrong asset set"

    # 5 attribution, 6 traceability
    traced: set[str] = set()
    for item in deliverables:
        key = str(item["company_key"])
        cited = item.get("source_row_ids")
        if not isinstance(cited, list) or cited != rows_of[key]:
            return False, f"deliverable for {item['company_key']} cites the wrong rows"
        if item.get("domain") != domains_of[key]:
            return False, f"deliverable for {item['company_key']} uses the wrong domain"
        traced.update(cited)
    untraced = {label for rows in rows_of.values() for label in rows} - traced
    if untraced:
        return False, f"{len(untraced)} uploaded rows reach no deliverable, e.g. {min(untraced)}"

    # 7 request conformity -- unconditional. A reported override is still an
    # override; the exceptions block records what was suppressed, it excuses
    # nothing.
    off_brand = [
        item
        for item in deliverables
        if item.get("brand_kit_id") != brand_kit_id
        or item.get("template_id") != template_id
    ]
    if off_brand:
        return False, f"{len(off_brand)} deliverables do not use the requested brand kit or template"

    # 8 the exceptions block names exactly the suppressed rows
    declared = {str(e["source_row_id"]) for e in plan.get("exceptions", [])}
    suppressed = {
        label
        for label, _, _ in inventory.override_rows(
            brand_kit_id=brand_kit_id, template_id=template_id
        )
    }
    if declared != suppressed:
        return False, (
            f"exceptions block lists {len(declared)} rows, "
            f"{len(suppressed)} were actually suppressed"
        )

    # 9 determinism
    for page_size in page_sizes:
        other = build_campaign_plan(
            TargetAccountTool(accounts),
            brand_kit_id=brand_kit_id,
            template_id=template_id,
            page_size=page_size,
            expected_row_count=len(accounts),
        )
        if len(other["companies"]) != len(expected):
            return False, (
                f"page size {page_size} gives {len(other['companies'])} companies, "
                f"not {len(expected)}"
            )

    # 10 honesty -- our own read, never the plan's claim
    if read.verified_complete != "true":
        return False, f"the upload could not be read completely: {read.reason}"

    return True, (
        f"{len(expected)} companies from {len(read.rows)} rows, "
        f"{len(deliverables)} deliverables, {len(declared)} exceptions, "
        f"read verified against declared size {len(accounts)}"
    )
