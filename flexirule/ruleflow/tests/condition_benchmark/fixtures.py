# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import frappe


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


def get_all_fixtures() -> list[BenchmarkFixture]:
	"""Return standard benchmark fixture corpus across all complexity tiers."""
	fixtures = []

	# --- Tier 1: Simple Condition ---
	tier1 = BenchmarkFixture(
		fixture_id="tier1_simple_equality",
		tier="Tier 1 — Simple",
		description="Single leaf comparison for status equality",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.status"},
					"op": "==",
					"right": {"value": "Open"},
				}
			],
		},
		matching_doc=frappe._dict({"status": "Open", "doctype": "ToDo"}),
		non_matching_doc=frappe._dict({"status": "Closed", "doctype": "ToDo"}),
		leaf_count=1,
		nesting_depth=1,
	)
	fixtures.append(tier1)

	# --- Tier 2: Typical Business Rule ---
	tier2 = BenchmarkFixture(
		fixture_id="tier2_typical_business_rule",
		tier="Tier 2 — Typical Business Rule",
		description="Three leaf conditions joined by AND",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.status"},
					"op": "==",
					"right": {"value": "Submitted"},
				},
				{
					"left": {"ref": "doc.grand_total"},
					"op": ">",
					"right": {"value": 1000},
				},
				{
					"left": {"ref": "doc.customer_group"},
					"op": "==",
					"right": {"value": "Commercial"},
				},
			],
		},
		matching_doc=frappe._dict(
			{
				"status": "Submitted",
				"grand_total": 1500,
				"customer_group": "Commercial",
				"doctype": "Sales Order",
			}
		),
		non_matching_doc=frappe._dict(
			{
				"status": "Submitted",
				"grand_total": 800,
				"customer_group": "Commercial",
				"doctype": "Sales Order",
			}
		),
		leaf_count=3,
		nesting_depth=1,
	)
	fixtures.append(tier2)

	# --- Tier 3: Nested AND/OR Groups ---
	tier3 = BenchmarkFixture(
		fixture_id="tier3_nested_and_or_groups",
		tier="Tier 3 — Nested Groups",
		description="Nested AND/OR groups for status and total/priority",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"op": "or",
					"conditions": [
						{
							"left": {"ref": "doc.status"},
							"op": "==",
							"right": {"value": "Draft"},
						},
						{
							"left": {"ref": "doc.status"},
							"op": "==",
							"right": {"value": "Submitted"},
						},
					],
				},
				{
					"op": "or",
					"conditions": [
						{
							"left": {"ref": "doc.grand_total"},
							"op": ">=",
							"right": {"value": 5000},
						},
						{
							"left": {"ref": "doc.priority"},
							"op": "==",
							"right": {"value": "High"},
						},
					],
				},
			],
		},
		matching_doc=frappe._dict(
			{
				"status": "Submitted",
				"grand_total": 6000,
				"priority": "Medium",
				"doctype": "Sales Order",
			}
		),
		non_matching_doc=frappe._dict(
			{
				"status": "Cancelled",
				"grand_total": 6000,
				"priority": "High",
				"doctype": "Sales Order",
			}
		),
		leaf_count=4,
		nesting_depth=2,
	)
	fixtures.append(tier3)

	# --- Tier 4: Deep Nested Complex Rule ---
	tier4 = BenchmarkFixture(
		fixture_id="tier4_deep_nested_complex",
		tier="Tier 4 — Deep Nested Complex",
		description="10 leaf conditions across 3 nested levels with mixed operators",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.docstatus"},
					"op": "==",
					"right": {"value": 1},
				},
				{
					"op": "or",
					"conditions": [
						{
							"left": {"ref": "doc.territory"},
							"op": "in",
							"right": {"value": ["North", "East", "West"]},
						},
						{
							"left": {"ref": "doc.is_prime_customer"},
							"op": "==",
							"right": {"value": 1},
						},
					],
				},
				{
					"op": "and",
					"conditions": [
						{
							"left": {"ref": "doc.net_amount"},
							"op": ">",
							"right": {"value": 500},
						},
						{
							"left": {"ref": "doc.discount_percentage"},
							"op": "<=",
							"right": {"value": 15},
						},
						{
							"op": "or",
							"conditions": [
								{
									"left": {"ref": "doc.workflow_state"},
									"op": "==",
									"right": {"value": "Approved"},
								},
								{
									"left": {"ref": "doc.auto_approved"},
									"op": "==",
									"right": {"value": 1},
								},
							],
						},
					],
				},
				{
					"left": {"ref": "doc.notes"},
					"op": "is_set",
				},
			],
		},
		matching_doc=frappe._dict(
			{
				"docstatus": 1,
				"territory": "North",
				"is_prime_customer": 0,
				"net_amount": 750,
				"discount_percentage": 10,
				"workflow_state": "Approved",
				"auto_approved": 0,
				"notes": "Verified rule context",
				"doctype": "Sales Invoice",
			}
		),
		non_matching_doc=frappe._dict(
			{
				"docstatus": 1,
				"territory": "South",
				"is_prime_customer": 0,
				"net_amount": 750,
				"discount_percentage": 10,
				"workflow_state": "Approved",
				"auto_approved": 0,
				"notes": "Verified rule context",
				"doctype": "Sales Invoice",
			}
		),
		leaf_count=8,
		nesting_depth=3,
	)
	fixtures.append(tier4)

	# --- Tier 5: Collection Child Records ---
	tier5 = BenchmarkFixture(
		fixture_id="tier5_collection_child_records",
		tier="Tier 5 — Collection / Child Records",
		description="Collection condition checking items child table with 'any' logic",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.status"},
					"op": "==",
					"right": {"value": "Submitted"},
				},
				{
					"collection": "doc.items",
					"op": "any",
					"alias": "item",
					"where": {
						"op": "and",
						"conditions": [
							{
								"left": {"ref": "item.qty"},
								"op": ">",
								"right": {"value": 10},
							},
							{
								"left": {"ref": "item.rate"},
								"op": ">=",
								"right": {"value": 100},
							},
						],
					},
				},
			],
		},
		matching_doc=frappe._dict(
			{
				"status": "Submitted",
				"items": [
					frappe._dict({"item_code": "ITEM-1", "qty": 5, "rate": 50}),
					frappe._dict({"item_code": "ITEM-2", "qty": 15, "rate": 120}),
				],
				"doctype": "Sales Order",
			}
		),
		non_matching_doc=frappe._dict(
			{
				"status": "Submitted",
				"items": [
					frappe._dict({"item_code": "ITEM-1", "qty": 5, "rate": 50}),
					frappe._dict({"item_code": "ITEM-2", "qty": 8, "rate": 120}),
				],
				"doctype": "Sales Order",
			}
		),
		leaf_count=3,
		nesting_depth=2,
	)
	fixtures.append(tier5)

	# --- Edge Case 1: Null vs Empty String ---
	edge1 = BenchmarkFixture(
		fixture_id="edge_case_is_set_null_empty",
		tier="Edge Case — Null / Empty",
		description="Checking is_set with null vs empty string vs non-empty string",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.remarks"},
					"op": "is_set",
				}
			],
		},
		matching_doc=frappe._dict({"remarks": "Some notes"}),
		non_matching_doc=frappe._dict({"remarks": ""}),
		leaf_count=1,
		nesting_depth=1,
	)
	fixtures.append(edge1)

	# --- Edge Case 2: Link Tuple ---
	edge2 = BenchmarkFixture(
		fixture_id="edge_case_link_tuple",
		tier="Edge Case — Link Tuple",
		description="Link tuple comparison for Customer link field",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.customer"},
					"op": "==",
					"right": {"value": ["Customer", "CUST-00001"]},
				}
			],
		},
		matching_doc=frappe._dict({"customer": "CUST-00001"}),
		non_matching_doc=frappe._dict({"customer": "CUST-00002"}),
		leaf_count=1,
		nesting_depth=1,
	)
	fixtures.append(edge2)

	# --- Edge Case 3: Membership ('in' / 'not_in') ---
	edge3 = BenchmarkFixture(
		fixture_id="edge_case_membership_in_not_in",
		tier="Edge Case — Membership",
		description="Checking 'in' and 'not_in' with list operand",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.status"},
					"op": "in",
					"right": {"value": ["Open", "Pending", "Draft"]},
				},
				{
					"left": {"ref": "doc.priority"},
					"op": "not in",
					"right": {"value": ["Low", "Trivial"]},
				},
			],
		},
		matching_doc=frappe._dict({"status": "Pending", "priority": "High"}),
		non_matching_doc=frappe._dict({"status": "Closed", "priority": "High"}),
		leaf_count=2,
		nesting_depth=1,
	)
	fixtures.append(edge3)

	# --- Edge Case 4: Substring Contains ---
	edge4 = BenchmarkFixture(
		fixture_id="edge_case_contains_not_contains",
		tier="Edge Case — Substring",
		description="Checking 'contains' and 'not_contains' on string fields",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.subject"},
					"op": "contains",
					"right": {"value": "URGENT"},
				},
				{
					"left": {"ref": "doc.subject"},
					"op": "not_contains",
					"right": {"value": "SPAM"},
				},
			],
		},
		matching_doc=frappe._dict({"subject": "URGENT: Server issue"}),
		non_matching_doc=frappe._dict({"subject": "URGENT: SPAM detected"}),
		leaf_count=2,
		nesting_depth=1,
	)
	fixtures.append(edge4)

	# --- Edge Case 5: Collection All / None ---
	edge5 = BenchmarkFixture(
		fixture_id="edge_case_collection_all_and_none",
		tier="Edge Case — Collection All/None",
		description="Collection condition verifying 'all' items are verified",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"collection": "doc.items",
					"op": "all",
					"alias": "item",
					"where": {
						"left": {"ref": "item.is_verified"},
						"op": "==",
						"right": {"value": 1},
					},
				}
			],
		},
		matching_doc=frappe._dict(
			{
				"items": [
					frappe._dict({"item_code": "I1", "is_verified": 1}),
					frappe._dict({"item_code": "I2", "is_verified": 1}),
				]
			}
		),
		non_matching_doc=frappe._dict(
			{
				"items": [
					frappe._dict({"item_code": "I1", "is_verified": 1}),
					frappe._dict({"item_code": "I2", "is_verified": 0}),
				]
			}
		),
		leaf_count=1,
		nesting_depth=2,
	)
	fixtures.append(edge5)

	# --- Edge Case 6: Length Operators ---
	edge6 = BenchmarkFixture(
		fixture_id="edge_case_length_gt_eq",
		tier="Edge Case — Length",
		description="Checking length_gt and length_eq on text fields",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.title"},
					"op": "length_gt",
					"right": {"value": 5},
				}
			],
		},
		matching_doc=frappe._dict({"title": "Detailed Title"}),
		non_matching_doc=frappe._dict({"title": "Tiny"}),
		leaf_count=1,
		nesting_depth=1,
	)
	fixtures.append(edge6)

	# --- Edge Case 7: has_changed Operator ---
	edge7 = BenchmarkFixture(
		fixture_id="edge_case_has_changed",
		tier="Edge Case — Field Change",
		description="Checking has_changed operator comparing doc and old_doc",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.status"},
					"op": "has_changed",
				}
			],
		},
		matching_doc=frappe._dict(
			{"status": "Submitted", "_doc_before_save": frappe._dict({"status": "Draft"})}
		),
		non_matching_doc=frappe._dict(
			{"status": "Submitted", "_doc_before_save": frappe._dict({"status": "Submitted"})}
		),
		leaf_count=1,
		nesting_depth=1,
	)
	fixtures.append(edge7)

	# --- Edge Case 8: None vs Missing Field ---
	edge8 = BenchmarkFixture(
		fixture_id="edge_case_none_vs_missing_field",
		tier="Edge Case — Missing Field",
		description="Checking is_not_set on missing field versus set field",
		condition_payload={
			"op": "and",
			"conditions": [
				{
					"left": {"ref": "doc.missing_field"},
					"op": "is_not_set",
				}
			],
		},
		matching_doc=frappe._dict({}),
		non_matching_doc=frappe._dict({"missing_field": "Present"}),
		leaf_count=1,
		nesting_depth=1,
	)
	fixtures.append(edge8)

	return fixtures


def get_canonical_fixtures() -> list[BenchmarkFixture]:
	"""Return PR #469 direct-node canonical benchmark fixtures using canonical operator IDs and typed FlexValues."""
	fixtures = []

	# 1. Tier 1: Canonical Simple Equality
	fixtures.append(
		BenchmarkFixture(
			fixture_id="canonical_tier1_simple_equality",
			tier="Canonical Tier 1 — Simple",
			description="Canonical direct comparison node for status equality",
			condition_payload={
				"type": "comparison",
				"operator": "eq",
				"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["status"]}},
				"right": {"mode": "static", "value_type": "string", "value": "Open"},
			},
			matching_doc=frappe._dict({"status": "Open"}),
			non_matching_doc=frappe._dict({"status": "Closed"}),
			leaf_count=1,
			nesting_depth=1,
		)
	)

	# 2. Tier 2: Canonical Business Rule
	fixtures.append(
		BenchmarkFixture(
			fixture_id="canonical_tier2_business_rule",
			tier="Canonical Tier 2 — Business Rule",
			description="Canonical group node joining three comparison nodes",
			condition_payload={
				"type": "group",
				"operator": "and",
				"children": [
					{
						"type": "comparison",
						"operator": "eq",
						"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["status"]}},
						"right": {"mode": "static", "value_type": "string", "value": "Submitted"},
					},
					{
						"type": "comparison",
						"operator": "gt",
						"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["grand_total"]}},
						"right": {"mode": "static", "value_type": "decimal", "value": "1000"},
					},
					{
						"type": "comparison",
						"operator": "eq",
						"left": {
							"mode": "variable",
							"path": {"scope": "doc", "segments": ["customer_group"]},
						},
						"right": {"mode": "static", "value_type": "string", "value": "Commercial"},
					},
				],
			},
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

	# 3. Tier 3: Canonical Nested Groups
	fixtures.append(
		BenchmarkFixture(
			fixture_id="canonical_tier3_nested_groups",
			tier="Canonical Tier 3 — Nested Groups",
			description="Canonical nested AND/OR groups for status and total/priority",
			condition_payload={
				"type": "group",
				"operator": "and",
				"children": [
					{
						"type": "group",
						"operator": "or",
						"children": [
							{
								"type": "comparison",
								"operator": "eq",
								"left": {
									"mode": "variable",
									"path": {"scope": "doc", "segments": ["status"]},
								},
								"right": {"mode": "static", "value_type": "string", "value": "Draft"},
							},
							{
								"type": "comparison",
								"operator": "eq",
								"left": {
									"mode": "variable",
									"path": {"scope": "doc", "segments": ["status"]},
								},
								"right": {"mode": "static", "value_type": "string", "value": "Submitted"},
							},
						],
					},
					{
						"type": "group",
						"operator": "or",
						"children": [
							{
								"type": "comparison",
								"operator": "gte",
								"left": {
									"mode": "variable",
									"path": {"scope": "doc", "segments": ["grand_total"]},
								},
								"right": {"mode": "static", "value_type": "decimal", "value": "5000"},
							},
							{
								"type": "comparison",
								"operator": "eq",
								"left": {
									"mode": "variable",
									"path": {"scope": "doc", "segments": ["priority"]},
								},
								"right": {"mode": "static", "value_type": "boolean", "value": True},
							},
						],
					},
				],
			},
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

	# 4. Tier 4: Canonical Deep Nested Complex
	fixtures.append(
		BenchmarkFixture(
			fixture_id="canonical_tier4_deep_nested_complex",
			tier="Canonical Tier 4 — Deep Nested Complex",
			description="Canonical 8 leaf conditions across 3 nested levels",
			condition_payload={
				"type": "group",
				"operator": "and",
				"children": [
					{
						"type": "comparison",
						"operator": "eq",
						"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["docstatus"]}},
						"right": {"mode": "static", "value_type": "integer", "value": 1},
					},
					{
						"type": "group",
						"operator": "or",
						"children": [
							{
								"type": "comparison",
								"operator": "in",
								"left": {
									"mode": "variable",
									"path": {"scope": "doc", "segments": ["territory"]},
								},
								"right": {
									"mode": "static",
									"value_type": "list",
									"value": ["North", "East", "West"],
								},
							},
							{
								"type": "comparison",
								"operator": "eq",
								"left": {
									"mode": "variable",
									"path": {"scope": "doc", "segments": ["is_prime_customer"]},
								},
								"right": {"mode": "static", "value_type": "boolean", "value": True},
							},
						],
					},
					{
						"type": "group",
						"operator": "and",
						"children": [
							{
								"type": "comparison",
								"operator": "gt",
								"left": {
									"mode": "variable",
									"path": {"scope": "doc", "segments": ["net_amount"]},
								},
								"right": {"mode": "static", "value_type": "decimal", "value": "500"},
							},
							{
								"type": "comparison",
								"operator": "lte",
								"left": {
									"mode": "variable",
									"path": {"scope": "doc", "segments": ["discount_percentage"]},
								},
								"right": {"mode": "static", "value_type": "decimal", "value": "15"},
							},
							{
								"type": "group",
								"operator": "or",
								"children": [
									{
										"type": "comparison",
										"operator": "eq",
										"left": {
											"mode": "variable",
											"path": {"scope": "doc", "segments": ["workflow_state"]},
										},
										"right": {
											"mode": "static",
											"value_type": "string",
											"value": "Approved",
										},
									},
									{
										"type": "comparison",
										"operator": "eq",
										"left": {
											"mode": "variable",
											"path": {"scope": "doc", "segments": ["auto_approved"]},
										},
										"right": {"mode": "static", "value_type": "boolean", "value": True},
									},
								],
							},
						],
					},
					{
						"type": "comparison",
						"operator": "is_set",
						"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["notes"]}},
					},
				],
			},
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

	# 5. Tier 5: Canonical Collection Predicate
	fixtures.append(
		BenchmarkFixture(
			fixture_id="canonical_tier5_collection_predicate",
			tier="Canonical Tier 5 — Collection Predicate",
			description="Canonical collection_predicate with 'any' quantifier",
			condition_payload={
				"type": "group",
				"operator": "and",
				"children": [
					{
						"type": "comparison",
						"operator": "eq",
						"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["status"]}},
						"right": {"mode": "static", "value_type": "string", "value": "Submitted"},
					},
					{
						"type": "collection_predicate",
						"quantifier": "any",
						"source": {"scope": "doc", "segments": ["items"]},
						"as": "item_row",
						"where": {
							"type": "group",
							"operator": "and",
							"children": [
								{
									"type": "comparison",
									"operator": "gt",
									"left": {
										"mode": "variable",
										"path": {"scope": "item_row", "segments": ["qty"]},
									},
									"right": {"mode": "static", "value_type": "integer", "value": 10},
								},
								{
									"type": "comparison",
									"operator": "gte",
									"left": {
										"mode": "variable",
										"path": {"scope": "item_row", "segments": ["rate"]},
									},
									"right": {"mode": "static", "value_type": "decimal", "value": "100"},
								},
							],
						},
					},
				],
			},
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

	# 6. Canonical Edge Case: Membership (in / not_in)
	fixtures.append(
		BenchmarkFixture(
			fixture_id="canonical_edge_membership",
			tier="Canonical Edge Case — Membership",
			description="Canonical in and not_in operators with static list values",
			condition_payload={
				"type": "group",
				"operator": "and",
				"children": [
					{
						"type": "comparison",
						"operator": "in",
						"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["status"]}},
						"right": {
							"mode": "static",
							"value_type": "list",
							"value": ["Open", "Pending", "Draft"],
						},
					},
					{
						"type": "comparison",
						"operator": "not_in",
						"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["priority"]}},
						"right": {
							"mode": "static",
							"value_type": "list",
							"value": ["Low", "Trivial"],
						},
					},
				],
			},
			matching_doc=frappe._dict({"status": "Pending", "priority": "High"}),
			non_matching_doc=frappe._dict({"status": "Closed", "priority": "High"}),
			leaf_count=2,
			nesting_depth=1,
		)
	)

	# 7. Canonical Edge Case: Text & Length
	fixtures.append(
		BenchmarkFixture(
			fixture_id="canonical_edge_text_length",
			tier="Canonical Edge Case — Text & Length",
			description="Canonical contains and length_gt operators",
			condition_payload={
				"type": "group",
				"operator": "and",
				"children": [
					{
						"type": "comparison",
						"operator": "contains",
						"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["subject"]}},
						"right": {"mode": "static", "value_type": "string", "value": "URGENT"},
					},
					{
						"type": "comparison",
						"operator": "length_gt",
						"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["subject"]}},
						"right": {"mode": "static", "value_type": "integer", "value": 5},
					},
				],
			},
			matching_doc=frappe._dict({"subject": "URGENT: Server issue"}),
			non_matching_doc=frappe._dict({"subject": "Normal note"}),
			leaf_count=2,
			nesting_depth=1,
		)
	)

	# 8. Canonical Edge Case: Missing vs Set
	fixtures.append(
		BenchmarkFixture(
			fixture_id="canonical_edge_missing_vs_set",
			tier="Canonical Edge Case — Missing Field",
			description="Canonical is_not_set on missing field versus set field",
			condition_payload={
				"type": "comparison",
				"operator": "is_not_set",
				"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["missing_field"]}},
			},
			matching_doc=frappe._dict({}),
			non_matching_doc=frappe._dict({"missing_field": "Present"}),
			leaf_count=1,
			nesting_depth=1,
		)
	)

	return fixtures
