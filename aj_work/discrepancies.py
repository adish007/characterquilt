"""Sweep an uploaded list for everything that looks off, not just what breaks the count.

`audit.py` answers one question: how many companies is this. This script is the
wider net — provenance, hygiene, and data conflicts that a reviewer would want
to see even when they do not change the number.

Every class is computed from the data. Nothing here names a fixture value, so a
clean upload prints a clean report.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

from identity import IDENTITY_FIELD, build_inventory, domain_of
from paging import collect_rows
from repair_lab import TargetAccountTool

CORPORATE_SUFFIX = re.compile(r"\b(inc|incorporated|ltd|limited|llc|corp|corporation|plc|gmbh)\b", re.I)
TRAILING_NUMBER = re.compile(r"(\d+)$")


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def _id_blocks(rows) -> list[tuple[int, int, int]]:
    """Contiguous runs in the trailing number of each row id.

    A separate run usually means a separate import batch, which is worth
    knowing when the rows in it misbehave together.
    """
    numbers = sorted(
        int(match.group(1))
        for row in rows
        if (match := TRAILING_NUMBER.search(_text(row.get("id"))))
    )
    if not numbers:
        return []
    blocks, start, previous = [], numbers[0], numbers[0]
    for number in numbers[1:]:
        if number != previous + 1:
            blocks.append((start, previous, previous - start + 1))
            start = number
        previous = number
    blocks.append((start, previous, previous - start + 1))
    return blocks


def _inserted_rows(rows) -> list[str]:
    """Rows that sit out of ascending id order relative to the row after them.

    A row numbered above its successor was written into a sequence that was
    already ordered, which points at a later edit rather than the original
    upload.
    """
    numbers = []
    for row in rows:
        match = TRAILING_NUMBER.search(_text(row.get("id")))
        numbers.append(int(match.group(1)) if match else None)
    return [
        _text(rows[i].get("id"))
        for i in range(len(rows) - 1)
        if numbers[i] is not None
        and numbers[i + 1] is not None
        and numbers[i] > numbers[i + 1]
    ]


def scan(rows) -> dict[str, list]:
    """Return every discrepancy class, each as a list of human-readable lines."""
    inventory = build_inventory(rows)
    out: dict[str, list] = {}

    out["blank identity"] = [
        f"{c.row_labels[0]:<12} {_text(c.rows[0].get('company_name')):<26}"
        f" {domain_of(c.rows[0])}  ({IDENTITY_FIELD}="
        f"{c.rows[0].get(IDENTITY_FIELD)!r})"
        for c in inventory.unidentified
    ]

    out["repeated identity"] = [
        f"{c.key:<32} {len(c.rows)} rows  {', '.join(c.row_labels)}"
        f"   {' | '.join(c.names)}"
        for c in sorted(inventory.duplicated, key=lambda c: c.key)
        if c.identified
    ]

    out["one identity, several domains"] = [
        f"{c.key:<32} {', '.join(d for d in c.domains if d)}"
        f"   rows {', '.join(c.row_labels)}"
        for c in inventory.id_spans_domains
    ]

    out["one domain, several identities"] = [
        f"{domain:<32} {', '.join(keys)}"
        for domain, keys in inventory.domain_spans_ids
    ]

    out["row overrides the request"] = [
        f"{label:<12} {_text(row.get('company_name')):<26}"
        f" {', '.join(f'{f}={row[f]}' for f in fields)}"
        for label, row, fields in inventory.override_rows()
    ]

    identical: dict[str, list[str]] = collections.defaultdict(list)
    for row in rows:
        key = json.dumps(
            {k: v for k, v in sorted(row.items()) if k != "id"}, default=str
        )
        identical[key].append(_text(row.get("id")))
    out["rows identical except id"] = [
        f"{', '.join(ids)}   {_text(json.loads(key).get('company_name'))}"
        for key, ids in identical.items()
        if len(ids) > 1
    ]

    conflicts = []
    for company in inventory.duplicated:
        for field in sorted({k for row in company.rows for k in row} - {"id"}):
            values = {_text(row.get(field)) for row in company.rows}
            if len(values) > 1 and field != "company_name":
                conflicts.append(
                    f"{company.key:<32} {field}: {sorted(values)}"
                    f"   rows {', '.join(company.row_labels)}"
                )
    out["conflicting fields within one identity"] = conflicts

    out["name differs only by case or suffix"] = [
        f"{c.key:<32} {' | '.join(c.names)}"
        for c in inventory.duplicated
        if c.identified
        and len({CORPORATE_SUFFIX.sub("", n).strip().lower() for n in c.names}) == 1
        and len(c.names) > 1
    ]

    blocks = _id_blocks(rows)
    out["row id blocks (import batches)"] = [
        f"{low}-{high}  ({count} rows)" for low, high, count in blocks
    ] if len(blocks) > 1 else []

    inserted = _inserted_rows(rows)
    out["rows written out of id order"] = (
        [f"{len(inserted)} rows: {', '.join(inserted)}"] if inserted else []
    )

    key_sets = collections.Counter(frozenset(row) for row in rows)
    out["rows carry different fields"] = (
        [
            f"{count}x  {sorted(shape)}"
            for shape, count in key_sets.most_common()
        ]
        if len(key_sets) > 1
        else []
    )

    orders = collections.Counter(
        tuple(row.keys()) for row in rows if frozenset(row) in key_sets
    )
    same_set_orders = collections.Counter()
    for order, count in orders.items():
        same_set_orders[(frozenset(order), order)] = count
    varied = [
        (order, count)
        for (shape, order), count in same_set_orders.items()
        if sum(c for (s, _), c in same_set_orders.items() if s == shape) != count
    ]
    out["same fields, different key order"] = (
        [f"{count}x  {list(order)}" for order, count in varied] if varied else []
    )

    segments = {_text(row.get("segment")) for row in rows if row.get("segment")}
    spaced = sorted(s for s in segments if " " in s)
    scored = sorted(s for s in segments if "_" in s)
    out["mixed segment taxonomy"] = (
        [f"space-separated {spaced} alongside underscore {scored}"]
        if spaced and scored
        else []
    )

    hygiene = []
    for row in rows:
        for field, value in row.items():
            if isinstance(value, str):
                if value != value.strip():
                    hygiene.append(f"{row.get('id')} {field} has padding: {value!r}")
                if field == "domain" and value != value.lower():
                    hygiene.append(f"{row.get('id')} domain not lowercase: {value!r}")
    upper = [
        _text(row.get("id"))
        for row in rows
        if _text(row.get("company_name")).isupper()
    ]
    if upper:
        hygiene.append(f"ALL-CAPS company_name on {len(upper)} rows: {', '.join(upper)}")
    out["value hygiene"] = hygiene

    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", default="fixtures/target_accounts.json")
    parser.add_argument("--page-size", type=int, default=25)
    args = parser.parse_args()

    accounts = json.loads(Path(args.list).read_text())
    read = collect_rows(TargetAccountTool(accounts), page_size=args.page_size)
    inventory = build_inventory(read.rows)
    findings = scan(read.rows)

    print(f"list                : {args.list}")
    print(f"rows read           : {len(read.rows)}  (complete={read.complete})")
    print(f"logical companies   : {inventory.company_count}")
    total = sum(len(v) for v in findings.values())
    print(f"discrepancy classes : {sum(1 for v in findings.values() if v)} "
          f"populated, {total} findings")

    for title, lines in findings.items():
        if not lines:
            continue
        print()
        print(f"-- {title} ({len(lines)}) --")
        for line in lines:
            print(f"   {line}")

    clean = [t for t, v in findings.items() if not v]
    if clean:
        print()
        print(f"-- nothing found ({len(clean)}) --")
        for title in clean:
            print(f"   {title}")


if __name__ == "__main__":
    main()
