# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import frappe

from flexirule.ruleflow.tests.condition_benchmark.adapters import (
	NeutralNode,
	NeutralScenario,
	node_to_canonical_payload,
	node_to_legacy_payload,
)


@dataclass
class BenchmarkFixture:
	"""Represents a benchmark test fixture case."""

	fixture_id: str
	tier: str
	description: str
	condition_payload: Any
	matching_doc: Any
	non_matching_doc: Any
	expected_matching_result: bool = True
	expected_non_matching_result: bool = False
	leaf_count: int = 1
	nesting_depth: int = 1


def get_neutral_scenarios() -> list[NeutralScenario]:
	"""Return standard neutral business scenarios covering representative rule categories."""
	scenarios = []

	# 1. Simple Equality
	scenarios.append(
		NeutralScenario(
			scenario_id="simple_equality",
			tier="Tier 1 — Simple",
			description="Single leaf comparison for status equality",
			root=NeutralNode(
				kind="comparison",
				operator="eq",
				left_scope="doc",
				left_segments=["status"],
				right_value_type="string",
				right_value="Open",
			),
			matching_doc=frappe._dict({"status": "Open"}),
			non_matching_doc=frappe._dict({"status": "Closed"}),
			leaf_count=1,
			nesting_depth=1,
		)
	)

	# 2. Typical Business Rule
	scenarios.append(
		NeutralScenario(
			scenario_id="typical_business_rule",
			tier="Tier 2 — Typical Business Rule",
			description="Three leaf conditions joined by AND",
			root=NeutralNode(
				kind="group",
				operator="and",
				children=[
					NeutralNode(
						kind="comparison",
						operator="eq",
						left_scope="doc",
						left_segments=["status"],
						right_value_type="string",
						right_value="Submitted",
					),
					NeutralNode(
						kind="comparison",
						operator="gt",
						left_scope="doc",
						left_segments=["grand_total"],
						right_value_type="decimal",
						right_value="1000",
					),
					NeutralNode(
						kind="comparison",
						operator="eq",
						left_scope="doc",
						left_segments=["customer_group"],
						right_value_type="string",
						right_value="Commercial",
					),
				],
			),
			matching_doc=frappe._dict(
				{
					"status": "Submitted",
					"grand_total": 1500,
					"customer_group": "Commercial",
				}
			),
			non_matching_doc=frappe._dict(
				{
					"status": "Submitted",
					"grand_total": 800,
					"customer_group": "Commercial",
				}
			),
			leaf_count=3,
			nesting_depth=1,
		)
	)

	# 3. Nested AND/OR Groups
	scenarios.append(
		NeutralScenario(
			scenario_id="nested_and_or_groups",
			tier="Tier 3 — Nested Groups",
			description="Nested AND/OR groups for status and total/priority",
			root=NeutralNode(
				kind="group",
				operator="and",
				children=[
					NeutralNode(
						kind="group",
						operator="or",
						children=[
							NeutralNode(
								kind="comparison",
								operator="eq",
								left_scope="doc",
								left_segments=["status"],
								right_value_type="string",
								right_value="Draft",
							),
							NeutralNode(
								kind="comparison",
								operator="eq",
								left_scope="doc",
								left_segments=["status"],
								right_value_type="string",
								right_value="Submitted",
							),
						],
					),
					NeutralNode(
						kind="group",
						operator="or",
						children=[
							NeutralNode(
								kind="comparison",
								operator="gte",
								left_scope="doc",
								left_segments=["grand_total"],
								right_value_type="decimal",
								right_value="5000",
							),
							NeutralNode(
								kind="comparison",
								operator="eq",
								left_scope="doc",
								left_segments=["priority"],
								right_value_type="boolean",
								right_value=True,
							),
						],
					),
				],
			),
			matching_doc=frappe._dict(
				{
					"status": "Submitted",
					"grand_total": 6000,
					"priority": False,
				}
			),
			non_matching_doc=frappe._dict(
				{
					"status": "Cancelled",
					"grand_total": 6000,
					"priority": True,
				}
			),
			leaf_count=4,
			nesting_depth=2,
		)
	)

	# 4. Deep Nested Complex Rule
	scenarios.append(
		NeutralScenario(
			scenario_id="deep_nested_complex",
			tier="Tier 4 — Deep Nested Complex",
			description="8 leaf conditions across 3 nested levels",
			root=NeutralNode(
				kind="group",
				operator="and",
				children=[
					NeutralNode(
						kind="comparison",
						operator="eq",
						left_scope="doc",
						left_segments=["docstatus"],
						right_value_type="integer",
						right_value=1,
					),
					NeutralNode(
						kind="group",
						operator="or",
						children=[
							NeutralNode(
								kind="comparison",
								operator="in",
								left_scope="doc",
								left_segments=["territory"],
								right_value_type="list",
								right_value=["North", "East", "West"],
							),
							NeutralNode(
								kind="comparison",
								operator="eq",
								left_scope="doc",
								left_segments=["is_prime_customer"],
								right_value_type="boolean",
								right_value=True,
							),
						],
					),
					NeutralNode(
						kind="group",
						operator="and",
						children=[
							NeutralNode(
								kind="comparison",
								operator="gt",
								left_scope="doc",
								left_segments=["net_amount"],
								right_value_type="decimal",
								right_value="500",
							),
							NeutralNode(
								kind="comparison",
								operator="lte",
								left_scope="doc",
								left_segments=["discount_percentage"],
								right_value_type="decimal",
								right_value="15",
							),
							NeutralNode(
								kind="group",
								operator="or",
								children=[
									NeutralNode(
										kind="comparison",
										operator="eq",
										left_scope="doc",
										left_segments=["workflow_state"],
										right_value_type="string",
										right_value="Approved",
									),
									NeutralNode(
										kind="comparison",
										operator="eq",
										left_scope="doc",
										left_segments=["auto_approved"],
										right_value_type="boolean",
										right_value=True,
									),
								],
							),
						],
					),
					NeutralNode(
						kind="comparison",
						operator="is_set",
						left_scope="doc",
						left_segments=["notes"],
					),
				],
			),
			matching_doc=frappe._dict(
				{
					"docstatus": 1,
					"territory": "North",
					"is_prime_customer": False,
					"net_amount": 750,
					"discount_percentage": 10,
					"workflow_state": "Approved",
					"auto_approved": False,
					"notes": "Verified rule context",
				}
			),
			non_matching_doc=frappe._dict(
				{
					"docstatus": 1,
					"territory": "South",
					"is_prime_customer": False,
					"net_amount": 750,
					"discount_percentage": 10,
					"workflow_state": "Approved",
					"auto_approved": False,
					"notes": "Verified rule context",
				}
			),
			leaf_count=8,
			nesting_depth=3,
		)
	)

	# 5. Collection Predicate (any)
	scenarios.append(
		NeutralScenario(
			scenario_id="collection_predicate",
			tier="Tier 5 — Collection Predicate",
			description="Collection condition checking items child table with 'any' quantifier",
			root=NeutralNode(
				kind="group",
				operator="and",
				children=[
					NeutralNode(
						kind="comparison",
						operator="eq",
						left_scope="doc",
						left_segments=["status"],
						right_value_type="string",
						right_value="Submitted",
					),
					NeutralNode(
						kind="collection_predicate",
						quantifier="any",
						source_scope="doc",
						source_segments=["items"],
						alias="item_row",
						where=NeutralNode(
							kind="group",
							operator="and",
							children=[
								NeutralNode(
									kind="comparison",
									operator="gt",
									left_scope="item_row",
									left_segments=["qty"],
									right_value_type="integer",
									right_value=10,
								),
								NeutralNode(
									kind="comparison",
									operator="gte",
									left_scope="item_row",
									left_segments=["rate"],
									right_value_type="decimal",
									right_value="100",
								),
							],
						),
					),
				],
			),
			matching_doc=frappe._dict(
				{
					"status": "Submitted",
					"items": [
						frappe._dict({"item_code": "ITEM-1", "qty": 5, "rate": 50}),
						frappe._dict({"item_code": "ITEM-2", "qty": 15, "rate": 120}),
					],
				}
			),
			non_matching_doc=frappe._dict(
				{
					"status": "Submitted",
					"items": [
						frappe._dict({"item_code": "ITEM-1", "qty": 5, "rate": 50}),
						frappe._dict({"item_code": "ITEM-2", "qty": 8, "rate": 120}),
					],
				}
			),
			leaf_count=3,
			nesting_depth=2,
		)
	)

	# 6. Edge Case: Membership
	scenarios.append(
		NeutralScenario(
			scenario_id="edge_case_membership_in_not_in",
			tier="Edge Case — Membership",
			description="Membership in and not_in operators",
			root=NeutralNode(
				kind="group",
				operator="and",
				children=[
					NeutralNode(
						kind="comparison",
						operator="in",
						left_scope="doc",
						left_segments=["status"],
						right_value_type="list",
						right_value=["Open", "Pending", "Draft"],
					),
					NeutralNode(
						kind="comparison",
						operator="not_in",
						left_scope="doc",
						left_segments=["priority"],
						right_value_type="list",
						right_value=["Low", "Trivial"],
					),
				],
			),
			matching_doc=frappe._dict({"status": "Pending", "priority": "High"}),
			non_matching_doc=frappe._dict({"status": "Closed", "priority": "High"}),
			leaf_count=2,
			nesting_depth=1,
		)
	)

	# 7. Edge Case: Text & Length
	scenarios.append(
		NeutralScenario(
			scenario_id="edge_case_contains_not_contains",
			tier="Edge Case — Substring",
			description="Contains substring and not_contains operators",
			root=NeutralNode(
				kind="group",
				operator="and",
				children=[
					NeutralNode(
						kind="comparison",
						operator="contains",
						left_scope="doc",
						left_segments=["subject"],
						right_value_type="string",
						right_value="URGENT",
					),
					NeutralNode(
						kind="comparison",
						operator="not_contains",
						left_scope="doc",
						left_segments=["subject"],
						right_value_type="string",
						right_value="SPAM",
					),
				],
			),
			matching_doc=frappe._dict({"subject": "URGENT: Server issue"}),
			non_matching_doc=frappe._dict({"subject": "URGENT: SPAM detected"}),
			leaf_count=2,
			nesting_depth=1,
		)
	)

	# 8. Edge Case: Field Change
	scenarios.append(
		NeutralScenario(
			scenario_id="edge_case_has_changed",
			tier="Edge Case — Field Change",
			description="Checking has_changed operator comparing doc and old_doc",
			root=NeutralNode(
				kind="comparison",
				operator="has_changed",
				left_scope="doc",
				left_segments=["status"],
			),
			matching_doc=frappe._dict(
				{"status": "Submitted", "_doc_before_save": frappe._dict({"status": "Draft"})}
			),
			non_matching_doc=frappe._dict(
				{"status": "Submitted", "_doc_before_save": frappe._dict({"status": "Submitted"})}
			),
			leaf_count=1,
			nesting_depth=1,
		)
	)

	# 9. Edge Case: Missing vs Set
	scenarios.append(
		NeutralScenario(
			scenario_id="edge_case_none_vs_missing_field",
			tier="Edge Case — Missing Field",
			description="Checking is_not_set on missing field versus set field",
			root=NeutralNode(
				kind="comparison",
				operator="is_not_set",
				left_scope="doc",
				left_segments=["missing_field"],
			),
			matching_doc=frappe._dict({}),
			non_matching_doc=frappe._dict({"missing_field": "Present"}),
			leaf_count=1,
			nesting_depth=1,
		)
	)

	return scenarios


def get_all_fixtures() -> list[BenchmarkFixture]:
	"""Return legacy benchmark fixtures derived from shared neutral scenarios."""
	fixtures = []
	for sc in get_neutral_scenarios():
		legacy_payload = node_to_legacy_payload(sc.root)
		fixtures.append(
			BenchmarkFixture(
				fixture_id=sc.scenario_id,
				tier=sc.tier,
				description=sc.description,
				condition_payload=legacy_payload,
				matching_doc=sc.matching_doc,
				non_matching_doc=sc.non_matching_doc,
				expected_matching_result=sc.expected_matching_result,
				expected_non_matching_result=sc.expected_non_matching_result,
				leaf_count=sc.leaf_count,
				nesting_depth=sc.nesting_depth,
			)
		)
	return fixtures


def get_canonical_fixtures() -> list[BenchmarkFixture]:
	"""Return PR #469 canonical benchmark fixtures derived from shared neutral scenarios."""
	fixtures = []
	for sc in get_neutral_scenarios():
		# Exclude has_changed from canonical fixtures since has_changed is not in canonical operator contract
		if sc.scenario_id == "edge_case_has_changed":
			continue
		canonical_payload = node_to_canonical_payload(sc.root)
		fixtures.append(
			BenchmarkFixture(
				fixture_id=f"canonical_{sc.scenario_id}",
				tier=f"Canonical {sc.tier}",
				description=sc.description,
				condition_payload=canonical_payload,
				matching_doc=sc.matching_doc,
				non_matching_doc=sc.non_matching_doc,
				expected_matching_result=sc.expected_matching_result,
				expected_non_matching_result=sc.expected_non_matching_result,
				leaf_count=sc.leaf_count,
				nesting_depth=sc.nesting_depth,
			)
		)
	return fixtures
