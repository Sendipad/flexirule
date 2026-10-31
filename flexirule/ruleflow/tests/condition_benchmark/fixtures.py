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
	metadata_context: dict | None = None
	collection_row_count: int = 0
	short_circuit_behavior: str = "none"


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
			collection_row_count=2,
			short_circuit_behavior="late_match",
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

	# --- Additional Canonical Focused Scenarios ---

	# 10. Dynamic Operands: Variable on Left, Variable on Right
	scenarios.append(
		NeutralScenario(
			scenario_id="dynamic_operands_both_sides",
			tier="Dynamic Operands — Both Variables",
			description="Comparison comparing customer balance with credit limit",
			root=NeutralNode(
				kind="comparison",
				operator="gt",
				left_scope="doc",
				left_segments=["current_balance"],
				right_mode="variable",
				right_scope="doc",
				right_segments=["credit_limit"],
			),
			matching_doc=frappe._dict({"current_balance": 5000, "credit_limit": 4000}),
			non_matching_doc=frappe._dict({"current_balance": 3000, "credit_limit": 4000}),
			leaf_count=1,
			nesting_depth=1,
		)
	)

	# 11. Dynamic Operands: Static on Left, Variable on Right
	scenarios.append(
		NeutralScenario(
			scenario_id="dynamic_operands_static_left",
			tier="Dynamic Operands — Static Left",
			description="Comparison comparing static threshold with dynamic document score",
			root=NeutralNode(
				kind="comparison",
				operator="lt",
				left_mode="static",
				left_value_type="integer",
				left_value=50,
				right_mode="variable",
				right_scope="doc",
				right_segments=["score"],
			),
			matching_doc=frappe._dict({"score": 85}),
			non_matching_doc=frappe._dict({"score": 30}),
			leaf_count=1,
			nesting_depth=1,
		)
	)

	# 12. Dynamic Operands: Template Operand
	scenarios.append(
		NeutralScenario(
			scenario_id="dynamic_operands_template",
			tier="Dynamic Operands — Template",
			description="Comparison matching dynamic template string against static prefix",
			root=NeutralNode(
				kind="comparison",
				operator="starts_with",
				left_raw_payload={
					"mode": "template",
					"segments": [
						{"type": "text", "value": "REQ-"},
						{
							"type": "value",
							"value": {
								"mode": "variable",
								"path": {"scope": "doc", "segments": ["category"]},
							},
						},
					],
				},
				right_mode="static",
				right_value_type="string",
				right_value="REQ-URGENT",
			),
			matching_doc=frappe._dict({"category": "URGENT_MAINTENANCE"}),
			non_matching_doc=frappe._dict({"category": "ROUTINE"}),
			leaf_count=1,
			nesting_depth=1,
		)
	)

	# 13. Realistic Frappe Metadata: User and Has Role
	scenarios.append(
		NeutralScenario(
			scenario_id="frappe_metadata_user_roles",
			tier="Frappe Metadata — User Roles",
			description="Authoritative User DocType metadata check with Has Role child table",
			root=NeutralNode(
				kind="collection_predicate",
				quantifier="any",
				source_scope="doc",
				source_segments=["roles"],
				alias="r",
				where=NeutralNode(
					kind="comparison",
					operator="eq",
					left_scope="r",
					left_segments=["role"],
					right_value_type="string",
					right_value="System Manager",
				),
			),
			matching_doc=frappe._dict(
				{
					"doctype": "User",
					"name": "test_user@example.com",
					"roles": [
						frappe._dict({"role": "Employee"}),
						frappe._dict({"role": "System Manager"}),
					],
				}
			),
			non_matching_doc=frappe._dict(
				{
					"doctype": "User",
					"name": "guest@example.com",
					"roles": [
						frappe._dict({"role": "Guest"}),
						frappe._dict({"role": "Blogger"}),
					],
				}
			),
			leaf_count=1,
			nesting_depth=1,
			metadata_context={"doctype": "User"},
			collection_row_count=2,
			short_circuit_behavior="late_match",
		)
	)

	return scenarios


def get_collection_scaling_scenarios() -> list[NeutralScenario]:
	"""Return collection scaling workloads with 10, 100, 1000, and 10000 rows.

	Includes early_match, late_match, and no_match scenarios.
	"""
	scenarios = []

	sizes = [10, 100, 1000, 10000]

	for size in sizes:
		# 1. Quantifier 'any' - Early Match (row 0 matches)
		early_match_rows = [frappe._dict({"id": i, "val": 100 if i == 0 else 10}) for i in range(size)]
		no_match_rows = [frappe._dict({"id": i, "val": 10}) for i in range(size)]

		scenarios.append(
			NeutralScenario(
				scenario_id=f"collection_scaling_any_early_match_{size}",
				tier=f"Collection Scaling — any ({size} rows)",
				description=f"Collection any check with early match at row 0 across {size} rows",
				root=NeutralNode(
					kind="collection_predicate",
					quantifier="any",
					source_scope="doc",
					source_segments=["items"],
					alias="it",
					where=NeutralNode(
						kind="comparison",
						operator="gt",
						left_scope="it",
						left_segments=["val"],
						right_value_type="integer",
						right_value=50,
					),
				),
				matching_doc=frappe._dict({"items": early_match_rows}),
				non_matching_doc=frappe._dict({"items": no_match_rows}),
				leaf_count=1,
				nesting_depth=1,
				collection_row_count=size,
				short_circuit_behavior="early_match",
			)
		)

		# 2. Quantifier 'any' - Late Match (last row matches)
		late_match_rows = [frappe._dict({"id": i, "val": 100 if i == size - 1 else 10}) for i in range(size)]
		scenarios.append(
			NeutralScenario(
				scenario_id=f"collection_scaling_any_late_match_{size}",
				tier=f"Collection Scaling — any ({size} rows)",
				description=f"Collection any check with late match at row {size - 1} across {size} rows",
				root=NeutralNode(
					kind="collection_predicate",
					quantifier="any",
					source_scope="doc",
					source_segments=["items"],
					alias="it",
					where=NeutralNode(
						kind="comparison",
						operator="gt",
						left_scope="it",
						left_segments=["val"],
						right_value_type="integer",
						right_value=50,
					),
				),
				matching_doc=frappe._dict({"items": late_match_rows}),
				non_matching_doc=frappe._dict({"items": no_match_rows}),
				leaf_count=1,
				nesting_depth=1,
				collection_row_count=size,
				short_circuit_behavior="late_match",
			)
		)

		# 3. Quantifier 'all' - Early Short-Circuit (row 0 fails)
		all_matching_rows = [frappe._dict({"id": i, "val": 100}) for i in range(size)]
		all_early_fail_rows = [frappe._dict({"id": i, "val": 10 if i == 0 else 100}) for i in range(size)]
		scenarios.append(
			NeutralScenario(
				scenario_id=f"collection_scaling_all_early_fail_{size}",
				tier=f"Collection Scaling — all ({size} rows)",
				description=f"Collection all check with early failure at row 0 across {size} rows",
				root=NeutralNode(
					kind="collection_predicate",
					quantifier="all",
					source_scope="doc",
					source_segments=["items"],
					alias="it",
					where=NeutralNode(
						kind="comparison",
						operator="gt",
						left_scope="it",
						left_segments=["val"],
						right_value_type="integer",
						right_value=50,
					),
				),
				matching_doc=frappe._dict({"items": all_matching_rows}),
				non_matching_doc=frappe._dict({"items": all_early_fail_rows}),
				leaf_count=1,
				nesting_depth=1,
				collection_row_count=size,
				short_circuit_behavior="early_match",
			)
		)

		# 4. Quantifier 'none' - Full Scan No Match
		none_matching_rows = [frappe._dict({"id": i, "val": 10}) for i in range(size)]
		none_late_fail_rows = [frappe._dict({"id": i, "val": 100 if i == size - 1 else 10}) for i in range(size)]
		scenarios.append(
			NeutralScenario(
				scenario_id=f"collection_scaling_none_{size}",
				tier=f"Collection Scaling — none ({size} rows)",
				description=f"Collection none check requiring scan of {size} rows",
				root=NeutralNode(
					kind="collection_predicate",
					quantifier="none",
					source_scope="doc",
					source_segments=["items"],
					alias="it",
					where=NeutralNode(
						kind="comparison",
						operator="gt",
						left_scope="it",
						left_segments=["val"],
						right_value_type="integer",
						right_value=50,
					),
				),
				matching_doc=frappe._dict({"items": none_matching_rows}),
				non_matching_doc=frappe._dict({"items": none_late_fail_rows}),
				leaf_count=1,
				nesting_depth=1,
				collection_row_count=size,
				short_circuit_behavior="no_match",
			)
		)

	return scenarios


def get_all_fixtures() -> list[BenchmarkFixture]:
	"""Return legacy benchmark fixtures derived from shared neutral scenarios."""
	fixtures = []
	for sc in get_neutral_scenarios():
		legacy_payload = node_to_legacy_payload(sc.root)
		if legacy_payload is None:
			continue
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
