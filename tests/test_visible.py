"""Property tests for the campaign planner.

Nothing here asserts a fixture's company count. The fixtures are used as two
independent uploads of unknown shape; every assertion states a property that
must hold for *any* upload (invariance, conservation, arity, uniqueness,
honesty). Behaviour that needs a specific shape is tested on a small synthetic
upload built in the test itself.
"""
from __future__ import annotations

import copy
import json
import signal
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

import sources
from identity import build_inventory
from paging import collect_rows
from repair_lab import (
    REQUIRED_ASSET_TYPES,
    TargetAccountTool,
    ToolPage,
    build_campaign_plan,
    evaluate_campaign_coverage,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
REQUEST = json.loads((FIXTURES / "request.json").read_text())
BRAND_KIT = REQUEST["brand_kit"]["id"]
TEMPLATE = REQUEST["template"]["id"]

UPLOADS = {
    name: json.loads((FIXTURES / name).read_text())
    for name in ("target_accounts.json", "second_list.json")
}
LARGEST_UPLOAD = max(UPLOADS, key=lambda name: len(UPLOADS[name]))

# Page sizes chosen to straddle every fixture: below, between and above.
PAGE_SIZES = (1, 7, 10, 25, 100, 1000)


def plan_for(
    accounts: list[dict[str, Any]],
    *,
    page_size: int = 25,
    declared: bool = True,
) -> dict[str, Any]:
    """The plan the product would ship for this upload."""
    return build_campaign_plan(
        TargetAccountTool(accounts),
        brand_kit_id=BRAND_KIT,
        template_id=TEMPLATE,
        page_size=page_size,
        expected_row_count=len(accounts) if declared else None,
    )


def evaluate(
    plan: dict[str, Any], accounts: list[dict[str, Any]]
) -> tuple[bool, str]:
    return evaluate_campaign_coverage(
        plan, accounts, brand_kit_id=BRAND_KIT, template_id=TEMPLATE
    )


def deliverables_by_company(plan: dict[str, Any]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for item in plan["deliverables"]:
        grouped.setdefault(item["company_key"], []).append(item)
    return grouped


@contextmanager
def time_limit(seconds: int) -> Iterator[None]:
    """Fail rather than hang: a paging bug that loops forever is a bug."""

    def raise_timeout(signum, frame):  # pragma: no cover - only on failure
        raise AssertionError(f"read did not terminate within {seconds}s")

    previous = signal.signal(signal.SIGALRM, raise_timeout)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


class FilteringLoader:
    """Drops rows matching a predicate, then pages the remainder perfectly.

    A test double for the failure the paging protocol cannot see: rows are lost
    before paging begins, so every page, cursor and completion flag it emits is
    internally consistent.
    """

    def __init__(
        self,
        accounts: list[dict[str, Any]],
        predicate: Callable[[dict[str, Any]], bool],
    ) -> None:
        self.kept = [dict(a) for a in accounts if not predicate(a)]
        self._inner = TargetAccountTool(self.kept)

    def load_page(
        self, *, cursor: str | None = None, page_size: int = 25
    ) -> ToolPage:
        return self._inner.load_page(cursor=cursor, page_size=page_size)


def has_no_identity(row: dict[str, Any]) -> bool:
    return not str(row.get("company_id") or "").strip()


class GroupingInvariantTests(unittest.TestCase):
    """Properties of company grouping that must hold for any upload."""

    def test_company_count_is_invariant_across_page_sizes(self) -> None:
        """How the service chunks an upload must not change the answer.

        This is the defect that made one upload report 214, 214 and 211.
        """
        for name, accounts in UPLOADS.items():
            baseline = len(plan_for(accounts)["companies"])
            for page_size in PAGE_SIZES:
                with self.subTest(upload=name, page_size=page_size):
                    plan = plan_for(accounts, page_size=page_size)
                    self.assertEqual(len(plan["companies"]), baseline)
                    self.assertEqual(plan["rows_read"], len(accounts))

    def test_blank_identity_never_merges_rows(self) -> None:
        """Rows with no company_id stay separate, whatever the blank looks like.

        Treating absent identity as a shared value folds unrelated companies
        into one bucket and deletes real customers.
        """
        for sentinel in (None, "", "   "):
            with self.subTest(sentinel=repr(sentinel)):
                upload = [
                    {
                        "id": f"row-{n}",
                        "company_id": sentinel,
                        "company_name": f"Company {n}",
                        "domain": f"company-{n}.test",
                    }
                    for n in range(3)
                ]
                inventory = build_inventory(upload)
                self.assertEqual(inventory.company_count, len(upload))
                self.assertEqual(len(inventory.unidentified), len(upload))

    def test_shared_domain_never_merges_companies(self) -> None:
        """Two identities on one domain stay two companies.

        Merging on domain deletes subsidiaries that share a parent's website.
        """
        upload = [
            {"id": "row-a", "company_id": "identity-a",
             "company_name": "Parent", "domain": "shared.test"},
            {"id": "row-b", "company_id": "identity-b",
             "company_name": "Subsidiary", "domain": "shared.test"},
        ]
        inventory = build_inventory(upload)
        self.assertEqual(inventory.company_count, len(upload))
        self.assertEqual(
            {c.key for c in inventory.companies}, {"identity-a", "identity-b"}
        )

    def test_every_uploaded_row_lands_in_exactly_one_company(self) -> None:
        """Conservation: grouping neither loses nor duplicates a row."""
        for name, accounts in UPLOADS.items():
            with self.subTest(upload=name):
                companies = build_inventory(accounts).companies
                labels = [label for c in companies for label in c.row_labels]
                self.assertEqual(len(labels), len(accounts))
                self.assertEqual(len(set(labels)), len(accounts))

    def test_every_company_gets_exactly_one_of_each_asset(self) -> None:
        """Arity: assets are produced per company, never per row.

        Per-row production is what shipped duplicate creative for companies the
        upload named twice.
        """
        for name, accounts in UPLOADS.items():
            with self.subTest(upload=name):
                plan = plan_for(accounts)
                grouped = deliverables_by_company(plan)
                self.assertEqual(sorted(grouped), sorted(plan["companies"]))
                for key, items in grouped.items():
                    types = sorted(item["asset_type"] for item in items)
                    self.assertEqual(
                        types, sorted(REQUIRED_ASSET_TYPES), f"company {key}"
                    )


class PagingTests(unittest.TestCase):
    """The read must terminate, and must not overstate what it collected."""

    def test_broken_paging_shapes_terminate_and_report_honestly(self) -> None:
        """A verified-complete claim must match what was actually collected.

        Each shape is a paging bug seen in production; the ones that cannot
        deliver the whole upload must say so rather than claim completeness.
        """
        for name, accounts in UPLOADS.items():
            for loader_cls in sources.ALL_SOURCES:
                for page_size in (10, 25, 100):
                    with self.subTest(
                        upload=name,
                        loader=loader_cls.__name__,
                        page_size=page_size,
                    ):
                        with time_limit(30):
                            read = collect_rows(
                                loader_cls(accounts),
                                page_size=page_size,
                                expected_row_count=len(accounts),
                            )
                        self.assertIn(read.verified_complete, ("true", "false"))
                        # A matching row count is necessary but not sufficient:
                        # a cycling service can visit every row and still never
                        # report that the upload ended.
                        if read.verified_complete == "true":
                            self.assertTrue(read.service_claimed_complete)
                            self.assertEqual(read.rows, accounts)
                        if not read.service_claimed_complete:
                            self.assertEqual(read.verified_complete, "false")
                        self.assertTrue(read.reason.strip())
                        if read.verified_complete == "false":
                            self.assertIn(str(len(accounts)), read.reason)
                            self.assertIn(
                                str(len(read.rows)),
                                read.reason,
                                "the reason must say how much was collected",
                            )

    def test_two_legitimate_identical_pages_lose_no_rows(self) -> None:
        """An upload may honestly contain two identical pages.

        Discarding a repeated page as a suspected replay silently deletes real
        rows, so the served reading must survive with and without a declared
        size.
        """
        half = [
            {
                "id": f"row-{n}",
                "company_id": f"identity-{n}",
                "company_name": f"Company {n}",
                "domain": f"company-{n}.test",
            }
            for n in range(3)
        ]
        upload = copy.deepcopy(half) + copy.deepcopy(half)

        undeclared = collect_rows(TargetAccountTool(upload), page_size=len(half))
        self.assertEqual(len(undeclared.rows), len(upload))
        self.assertEqual(undeclared.verified_complete, "unknown")

        declared = collect_rows(
            TargetAccountTool(upload),
            page_size=len(half),
            expected_row_count=len(upload),
        )
        self.assertEqual(len(declared.rows), len(upload))
        self.assertEqual(declared.verified_complete, "true")

        # And the repeated rows stay distinguishable downstream.
        inventory = build_inventory(declared.rows)
        self.assertEqual(
            len({label for c in inventory.companies for label in c.row_labels}),
            len(upload),
        )

    def test_three_identical_pages_followed_by_more_data_lose_no_rows(self) -> None:
        """Repeated content is not a stall while the cursor keeps advancing."""
        same = {
            "id": "same-id",
            "company_id": "same-company",
            "company_name": "Same Company",
            "domain": "same.test",
        }
        last = {
            "id": "last-id",
            "company_id": "last-company",
            "company_name": "Last Company",
            "domain": "last.test",
        }
        upload = [copy.deepcopy(same) for _ in range(3)] + [last]
        read = collect_rows(
            TargetAccountTool(upload),
            page_size=1,
            expected_row_count=len(upload),
        )
        self.assertTrue(read.service_claimed_complete)
        self.assertEqual(read.verified_complete, "true")
        self.assertEqual(read.rows, upload)

    def test_a_short_read_reconciles_as_incomplete(self) -> None:
        """A service that stops early while claiming success must be caught.

        Only the declared size can expose it: the read itself looks clean.
        """
        accounts = UPLOADS[LARGEST_UPLOAD]
        read = collect_rows(
            sources.SilentlyShortLoader(accounts),
            expected_row_count=len(accounts),
        )
        self.assertTrue(read.service_claimed_complete)
        self.assertEqual(read.verified_complete, "false")
        self.assertLess(len(read.rows), len(accounts))

    def test_a_filtered_read_is_only_detectable_via_the_declared_size(self) -> None:
        """Rows lost before paging are invisible to the protocol.

        This records the limit of the read: without the upload's declared size
        a filtered read is indistinguishable from a correct one, so supplying
        the declared size is not optional.
        """
        for name, accounts in UPLOADS.items():
            with self.subTest(upload=name):
                dropped = FilteringLoader(accounts, has_no_identity).kept
                self.assertLess(
                    len(dropped), len(accounts), "predicate dropped nothing"
                )

                honest = collect_rows(TargetAccountTool(accounts))
                blind = collect_rows(FilteringLoader(accounts, has_no_identity))
                self.assertTrue(blind.service_claimed_complete)
                self.assertEqual(
                    (
                        blind.service_claimed_complete,
                        blind.verified_complete,
                        blind.reason,
                    ),
                    (
                        honest.service_claimed_complete,
                        honest.verified_complete,
                        honest.reason,
                    ),
                    "a filtered read must look exactly like a correct one",
                )

                checked = collect_rows(
                    FilteringLoader(accounts, has_no_identity),
                    expected_row_count=len(accounts),
                )
                self.assertTrue(checked.service_claimed_complete)
                self.assertEqual(checked.verified_complete, "false")


class DomainSelectionTests(unittest.TestCase):
    """A landing page needs one address, and it must be the company's own."""

    def test_a_sole_owned_domain_beats_a_shared_one(self) -> None:
        """A company with a domain of its own must not ship somebody else's."""
        upload = [
            {"id": "r1", "company_id": "identity-a", "company_name": "A",
             "domain": "shared.test"},
            {"id": "r2", "company_id": "identity-a", "company_name": "A",
             "domain": "own.test"},
            {"id": "r3", "company_id": "identity-b", "company_name": "B",
             "domain": "shared.test"},
        ]
        grouped = deliverables_by_company(plan_for(upload))
        self.assertEqual(
            {item["domain"] for item in grouped["identity-a"]}, {"own.test"}
        )

    def test_two_sole_owned_domains_ship_and_are_noted(self) -> None:
        """An ambiguous company is still campaigned, disclosed, and stable.

        Dropping it deletes a customer over a data-quality problem; picking a
        different domain per page size makes the run unreproducible.
        """
        upload = [
            {"id": "r1", "company_id": "identity-a", "company_name": "A",
             "domain": "first.test"},
            {"id": "r2", "company_id": "identity-a", "company_name": "A",
             "domain": "second.test"},
        ]
        chosen = set()
        for page_size in PAGE_SIZES:
            with self.subTest(page_size=page_size):
                plan = plan_for(upload, page_size=page_size)
                items = deliverables_by_company(plan)["identity-a"]
                self.assertEqual(len(items), len(REQUIRED_ASSET_TYPES))
                self.assertIn(
                    "identity-a",
                    [note["company"] for note in plan["domain_notes"]],
                )
                chosen.update(item["domain"] for item in items)
        self.assertEqual(
            len(chosen), 1, f"domain drifted across page sizes: {chosen}"
        )

    def test_a_company_whose_only_domain_is_shared_still_ships(self) -> None:
        """A shared domain is less preferred, never disqualifying."""
        upload = [
            {"id": "r1", "company_id": "identity-a", "company_name": "A",
             "domain": "shared.test"},
            {"id": "r2", "company_id": "identity-b", "company_name": "B",
             "domain": "shared.test"},
        ]
        grouped = deliverables_by_company(plan_for(upload))
        for key in ("identity-a", "identity-b"):
            with self.subTest(company=key):
                self.assertEqual(len(grouped[key]), len(REQUIRED_ASSET_TYPES))
                self.assertEqual(
                    {item["domain"] for item in grouped[key]}, {"shared.test"}
                )

    def test_no_deliverable_ever_ships_without_a_domain(self) -> None:
        """A landing page with no address is not a deliverable.

        An earlier draft of the domain policy declined to choose and shipped
        deliverables with an empty domain.
        """
        for name, accounts in UPLOADS.items():
            with self.subTest(upload=name):
                blank = [
                    item
                    for item in plan_for(accounts)["deliverables"]
                    if not item["domain"]
                ]
                self.assertEqual(blank, [])

    def test_a_company_with_no_domain_still_ships_and_is_noted(self) -> None:
        """No company is blocked; a missing address is reported, not fatal.

        One unusable row must not cost the customer the rest of the campaign,
        so the company is campaigned and named in `domain_notes` for a human.
        """
        upload = [
            {
                "id": "r1",
                "company_id": "identity-a",
                "company_name": "A",
                "domain": "",
            }
        ]
        plan = plan_for(upload)
        self.assertEqual(len(plan["deliverables"]), len(REQUIRED_ASSET_TYPES))
        self.assertEqual(
            [note["company"] for note in plan["domain_notes"]], ["identity-a"]
        )


class CoverageEvaluatorTests(unittest.TestCase):
    """The evaluator must reject a plan for the reasons a customer would."""

    def good(self, name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        accounts = UPLOADS[name]
        return copy.deepcopy(plan_for(accounts)), accounts

    def assertRejected(
        self, plan: dict[str, Any], accounts: list[dict[str, Any]]
    ) -> None:
        passed, detail = evaluate(plan, accounts)
        self.assertFalse(passed, f"damaged plan was accepted: {detail}")
        self.assertTrue(detail.strip(), "rejection gave no reason")

    def test_the_shipped_plan_passes(self) -> None:
        """The baseline must pass, or the suite proves nothing by rejecting."""
        for name, accounts in UPLOADS.items():
            with self.subTest(upload=name):
                passed, detail = evaluate(plan_for(accounts), accounts)
                self.assertTrue(passed, detail)

    def test_a_dropped_company_is_rejected(self) -> None:
        """A company in the upload with no creative is the original failure."""
        for name in UPLOADS:
            with self.subTest(upload=name):
                plan, accounts = self.good(name)
                dropped = plan["companies"].pop()
                plan["deliverables"] = [
                    d for d in plan["deliverables"] if d["company_key"] != dropped
                ]
                self.assertRejected(plan, accounts)

    def test_doubled_deliverables_are_rejected(self) -> None:
        """Two landing pages for one company is wasted spend, not coverage."""
        for name in UPLOADS:
            with self.subTest(upload=name):
                plan, accounts = self.good(name)
                target = plan["companies"][0]
                plan["deliverables"] += [
                    copy.deepcopy(d)
                    for d in plan["deliverables"]
                    if d["company_key"] == target
                ]
                self.assertRejected(plan, accounts)

    def test_an_orphan_deliverable_is_rejected(self) -> None:
        """Creative for a company nobody uploaded means the run lost its place."""
        for name in UPLOADS:
            with self.subTest(upload=name):
                plan, accounts = self.good(name)
                orphan = copy.deepcopy(plan["deliverables"][0])
                orphan["company_key"] = "identity-never-uploaded"
                plan["deliverables"].append(orphan)
                self.assertRejected(plan, accounts)

    def test_wrong_attribution_is_rejected(self) -> None:
        """A deliverable that cites the wrong rows cannot be audited."""
        for name in UPLOADS:
            with self.subTest(upload=name):
                plan, accounts = self.good(name)
                plan["deliverables"][0]["source_row_ids"] = ["row-never-uploaded"]
                self.assertRejected(plan, accounts)

    def test_duplicate_provenance_is_rejected(self) -> None:
        """A row citation must match exactly, including multiplicity."""
        plan, accounts = self.good(LARGEST_UPLOAD)
        item = next(
            d for d in plan["deliverables"] if len(d["source_row_ids"]) > 1
        )
        item["source_row_ids"].append(item["source_row_ids"][0])
        self.assertRejected(plan, accounts)

    def test_wrong_or_empty_personalisation_domain_is_rejected(self) -> None:
        """Correct rows cannot excuse a wrong or missing destination."""
        for name in UPLOADS:
            for invalid_domain in ("wrong.test", ""):
                with self.subTest(upload=name, domain=invalid_domain):
                    plan, accounts = self.good(name)
                    for item in plan["deliverables"]:
                        item["domain"] = invalid_domain
                    self.assertRejected(plan, accounts)

    def test_an_unauthorised_brand_kit_is_rejected(self) -> None:
        """Creative in a brand the customer did not select is off-brand."""
        for name in UPLOADS:
            with self.subTest(upload=name):
                plan, accounts = self.good(name)
                plan["deliverables"][0]["brand_kit_id"] = "brand-kit-not-requested"
                self.assertRejected(plan, accounts)

    def test_an_emptied_exceptions_block_is_rejected(self) -> None:
        """Suppressing a row's saved selections without recording it hides the change."""
        upload = [
            {"id": "r1", "company_id": "identity-a", "company_name": "A",
             "domain": "a.test",
             "saved_brand_kit_id": "brand-kit-somebody-else"},
            {"id": "r2", "company_id": "identity-b", "company_name": "B",
             "domain": "b.test"},
        ]
        plan = plan_for(upload)
        self.assertTrue(plan["exceptions"], "this upload has no overrides to hide")
        passed, detail = evaluate(plan, upload)
        self.assertTrue(passed, detail)

        damaged = copy.deepcopy(plan)
        damaged["exceptions"] = []
        self.assertRejected(damaged, upload)

    def test_rows_sharing_an_uploaded_id_stay_distinguishable(self) -> None:
        """Uploads do not guarantee unique ids; two blank-identity rows are two companies."""
        upload = [
            {"id": "same-id", "company_id": None, "company_name": "A",
             "domain": "a.test"},
            {"id": "same-id", "company_id": "", "company_name": "B",
             "domain": "b.test"},
            {"id": "same-id#0", "company_id": " ", "company_name": "C",
             "domain": "c.test"},
        ]
        companies = build_inventory(upload).companies
        self.assertEqual(len(companies), len(upload))
        labels = [label for c in companies for label in c.row_labels]
        self.assertEqual(len(set(labels)), len(upload))
        passed, detail = evaluate(plan_for(upload), upload)
        self.assertTrue(passed, detail)

    def test_a_self_reported_success_does_not_excuse_a_gap(self) -> None:
        """The evaluator must re-derive the truth, never read the plan's own claim.

        The check this replaces echoed the plan's completion flag, which is how
        a run that dropped companies was reported as passing.
        """
        for name in UPLOADS:
            with self.subTest(upload=name):
                plan, accounts = self.good(name)
                dropped = plan["companies"].pop()
                plan["deliverables"] = [
                    d for d in plan["deliverables"] if d["company_key"] != dropped
                ]
                plan["verified_complete"] = "true"
                plan["service_claimed_complete"] = True
                plan["completion_reason"] = "all companies covered, read verified"
                self.assertRejected(plan, accounts)


if __name__ == "__main__":
    unittest.main()
