"""Step 1: derive how many logical companies an upload represents.

Prints the count and, more usefully, every row that makes the count arguable.
Nothing here is specific to a fixture: the classes are computed from the data,
so a different upload produces a different list, or an empty one.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import sources
from identity import build_inventory, domain_of
from paging import collect_rows
from repair_lab import TargetAccountTool, build_campaign_plan

LOADERS = {cls.__name__: cls for cls in (TargetAccountTool,) + sources.ALL_SOURCES}

COMPARISON_PAGE_SIZES = (10, 25, 100)


def _name(row: dict) -> str:
    return str(row.get("company_name", ""))


def _report(inventory, read, request, *, list_path, loader_name, page_size):
    brand_kit_id = request["brand_kit"]["id"]
    template_id = request["template"]["id"]

    print(f"list                 : {list_path}")
    print(f"loader               : {loader_name}  (page_size={page_size})")
    print(
        f"rows read            : {len(read.rows)}"
        f"  ({read.pages_requested} page requests,"
        f" {read.barren_pages} carrying nothing new)"
    )
    print(f"read complete        : {read.complete} — {read.reason}")
    if read.complete:
        print(
            "                       caveat: a read that stops early and reports "
            "success\n                       cannot be told from a real end at this layer."
        )

    print()
    print(f"logical companies    : {inventory.company_count}")
    print(f"  by company_id      : {len(inventory.identified)}")
    print(f"  unidentified       : {len(inventory.unidentified)}  (each its own company)")

    contested = inventory.contested_row_labels(
        brand_kit_id=brand_kit_id, template_id=template_id
    )
    print(f"contested rows       : {len(contested)} of {len(read.rows)}")

    print()
    unidentified = inventory.unidentified
    print(f"[A] no usable company_id — never merged ({len(unidentified)} rows)")
    for company in unidentified:
        row = company.rows[0]
        print(f"    {company.row_labels[0]:<12} {_name(row):<26} {domain_of(row)}")

    print()
    duplicated = inventory.duplicated
    print(
        f"[B] one company_id named by several rows"
        f" ({len(duplicated)} groups, {inventory.extra_rows} extra rows)"
    )
    for company in sorted(duplicated, key=lambda c: c.key):
        if not company.identified:
            continue
        labels = ", ".join(company.row_labels)
        print(f"    {company.key:<32} {len(company.rows)} rows  {labels}")
        print(f"        {' | '.join(company.names)}")

    print()
    spans = inventory.id_spans_domains
    print(f"[C] one company_id, several domains ({len(spans)}) — one customer or two?")
    for company in spans:
        print(f"    {company.key:<32} {', '.join(d for d in company.domains if d)}")

    print()
    collisions = inventory.domain_spans_ids
    print(
        f"[D] one domain, several company_ids ({len(collisions)})"
        " — merging these would delete companies"
    )
    for domain, keys in collisions:
        print(f"    {domain:<32} {', '.join(keys)}")

    print()
    overrides = inventory.override_rows(
        brand_kit_id=brand_kit_id, template_id=template_id
    )
    print(f"[E] rows overriding the request's own selections ({len(overrides)})")
    for label, row, fields in overrides:
        detail = ", ".join(f"{f}={row[f]}" for f in fields)
        print(f"    {label:<12} {_name(row):<26} {detail}")


def _page_size_sensitivity(accounts, request, expected):
    print()
    print("what the shipped builder reports for the same upload:")
    for size in COMPARISON_PAGE_SIZES:
        plan = build_campaign_plan(
            TargetAccountTool(accounts),
            brand_kit_id=request["brand_kit"]["id"],
            template_id=request["template"]["id"],
            page_size=size,
        )
        rows = len(plan["source_row_ids"])
        print(
            f"    page_size={size:<5} {rows} rows campaigned,"
            f" complete={plan['complete']}   (off by {rows - expected:+d})"
        )
    print(f"    the count above is invariant: {expected} companies at any page size")


def _as_json(inventory, read, request):
    brand_kit_id = request["brand_kit"]["id"]
    template_id = request["template"]["id"]
    return {
        "rows_read": len(read.rows),
        "read_complete": read.complete,
        "read_reason": read.reason,
        "logical_companies": inventory.company_count,
        "identified": len(inventory.identified),
        "unidentified": [c.row_labels[0] for c in inventory.unidentified],
        "duplicate_groups": {
            c.key: list(c.row_labels) for c in inventory.duplicated if c.identified
        },
        "id_spans_domains": {
            c.key: [d for d in c.domains if d] for c in inventory.id_spans_domains
        },
        "domain_spans_ids": {d: list(k) for d, k in inventory.domain_spans_ids},
        "request_overrides": [
            label
            for label, _, _ in inventory.override_rows(
                brand_kit_id=brand_kit_id, template_id=template_id
            )
        ],
        "contested_rows": list(
            inventory.contested_row_labels(
                brand_kit_id=brand_kit_id, template_id=template_id
            )
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", default="fixtures/target_accounts.json")
    parser.add_argument("--loader", default="TargetAccountTool", choices=sorted(LOADERS))
    parser.add_argument("--page-size", type=int, default=25)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    accounts = json.loads(Path(args.list).read_text())
    request = json.loads(Path("fixtures/request.json").read_text())

    read = collect_rows(LOADERS[args.loader](accounts), page_size=args.page_size)
    inventory = build_inventory(read.rows)

    if args.json:
        print(json.dumps(_as_json(inventory, read, request), indent=2))
        return

    _report(
        inventory,
        read,
        request,
        list_path=args.list,
        loader_name=args.loader,
        page_size=args.page_size,
    )
    if args.loader == "TargetAccountTool":
        _page_size_sensitivity(accounts, request, inventory.company_count)


if __name__ == "__main__":
    main()
