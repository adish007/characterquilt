from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from identity import Company, Inventory, build_inventory

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

    A landing page needs exactly one address, so this cannot decline to choose.
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
    # Deferred: paging imports the loader protocol from this module.
    from paging import collect_rows

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
) -> tuple[bool, str]:
    """Interim check, carried over the plan's new shape. Rewritten in D.

    Still weak in the way the customer disputes: it only inspects what the plan
    already contains, and so cannot notice a company that never arrived.
    """
    by_company: dict[str, set[str]] = {}
    for item in plan.get("deliverables", []):
        by_company.setdefault(str(item["company_key"]), set()).add(
            str(item["asset_type"])
        )

    for key, asset_types in sorted(by_company.items()):
        if asset_types != set(REQUIRED_ASSET_TYPES):
            return False, f"company {key} has the wrong asset set"

    if plan.get("verified_complete") == "false":
        return False, plan.get("completion_reason", "the read did not complete")
    return True, f"all {len(by_company)} companies have the requested asset types"
