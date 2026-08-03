from __future__ import annotations

import argparse
import json
from pathlib import Path

from identity import build_inventory
from paging import collect_rows
from repair_lab import (
    TargetAccountTool,
    build_campaign_plan,
    evaluate_campaign_coverage,
)

PAGE_SIZES = (10, 25, 100)


def _plan(accounts: list[dict], request: dict, page_size: int = 25) -> dict:
    return build_campaign_plan(
        TargetAccountTool(accounts),
        brand_kit_id=request["brand_kit"]["id"],
        template_id=request["template"]["id"],
        page_size=page_size,
        # The upload declares its own size. Without it a short or filtered read
        # is indistinguishable from a correct one.
        expected_row_count=len(accounts),
    )


def _page_size_table(accounts: list[dict], request: dict) -> None:
    runs = {size: _plan(accounts, request, size) for size in PAGE_SIZES}
    rows = {
        "companies": lambda p: len(p["companies"]),
        "deliverables": lambda p: len(p["deliverables"]),
        "uploaded rows read": lambda p: p["rows_read"],
        "service claimed complete": lambda p: p["service_claimed_complete"],
        "verified complete": lambda p: p["verified_complete"],
    }
    header = "".join(f"{f'page_size={s}':>16}" for s in PAGE_SIZES)
    print(f"{'':30}{header}")
    for label, read in rows.items():
        cells = "".join(f"{str(read(runs[s])):>16}" for s in PAGE_SIZES)
        print(f"{label:30}{cells}")

    answers = {len(runs[s]['companies']) for s in PAGE_SIZES}
    verdict = (
        f"invariant at {answers.pop()} companies"
        if len(answers) == 1
        else f"DEPENDS ON PAGE SIZE: {sorted(answers)}"
    )
    print(f"\n{'the count is':30}{verdict}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", default="fixtures/target_accounts.json")
    args = parser.parse_args()

    accounts = json.loads(Path(args.list).read_text())
    request = json.loads(Path("fixtures/request.json").read_text())
    brand_kit_id = request["brand_kit"]["id"]
    template_id = request["template"]["id"]

    print(f"list                          : {args.list}")
    print(f"uploaded rows                 : {len(accounts)}")
    print(f"brand kit selected on request : {brand_kit_id}")
    print(f"template selected on request  : {template_id}")
    print()

    _page_size_table(accounts, request)

    plan = _plan(accounts, request)
    print()
    print(f"read                          : {plan['completion_reason']}")

    kits: dict[str, int] = {}
    for item in plan["deliverables"]:
        kits[item["brand_kit_id"]] = kits.get(item["brand_kit_id"], 0) + 1
    print()
    print("deliverables by brand kit:")
    for kit, count in sorted(kits.items()):
        print(f"  {kit:34} {count:>6}")

    # A row may ask for a different kit; the request wins and the row is
    # recorded here instead. An empty block is a result, not a gap.
    print()
    print(f"rows whose saved selections the request overrode: {len(plan['exceptions'])}")
    for item in plan["exceptions"]:
        ignored = ", ".join(f"{k}={v}" for k, v in item["ignored"].items())
        print(f"  {item['source_row_id']:12} {ignored}")

    print()
    print(f"companies whose domain needed a choice: {len(plan['domain_notes'])}")
    for note in plan["domain_notes"]:
        print(f"  {note['company']:34} {note['domain_used']:30} {note['note']}")

    print()
    print("contested records — what a human must look at:")
    # Through the loader interface, like everything else that reads the upload.
    inventory = build_inventory(
        collect_rows(
            TargetAccountTool(accounts), expected_row_count=len(accounts)
        ).rows
    )
    summary = inventory.contested_summary(
        brand_kit_id=brand_kit_id, template_id=template_id
    )
    for label, value in summary.items():
        print(f"  {label:44} {value:>5}")
    for key, field, values in inventory.attribute_conflicts():
        print(f"    conflict  {key:32} {field}: {', '.join(values)}")

    passed, detail = evaluate_campaign_coverage(
        plan,
        accounts,
        brand_kit_id=brand_kit_id,
        template_id=template_id,
    )
    print()
    print(f"check returned                : {passed}")
    print(f"check said                    : {detail}")


if __name__ == "__main__":
    main()
