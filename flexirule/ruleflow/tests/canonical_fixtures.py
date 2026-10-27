# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Shared positive and negative canonical condition fixtures.
"""

POSITIVE_FIXTURES = [
	{
		"name": "simple_root_comparison_eq",
		"condition": {
			"type": "comparison",
			"operator": "eq",
			"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["status"]}},
			"right": {"mode": "static", "value_type": "string", "value": "Open"},
		},
		"context": {"doc": {"status": "Open"}},
		"expected": True,
	},
	{
		"name": "root_comparison_decimal_gt",
		"condition": {
			"type": "comparison",
			"operator": "gt",
			"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["grand_total"]}},
			"right": {"mode": "static", "value_type": "decimal", "value": "1000.00"},
		},
		"context": {"doc": {"grand_total": "1500.50"}},
		"expected": True,
	},
	{
		"name": "nested_group_and_or",
		"condition": {
			"type": "group",
			"operator": "and",
			"children": [
				{
					"type": "comparison",
					"operator": "eq",
					"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["status"]}},
					"right": {"mode": "static", "value_type": "string", "value": "Open"},
				},
				{
					"type": "group",
					"operator": "or",
					"children": [
						{
							"type": "comparison",
							"operator": "gt",
							"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["total"]}},
							"right": {"mode": "static", "value_type": "integer", "value": 100},
						},
						{
							"type": "comparison",
							"operator": "eq",
							"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["is_priority"]}},
							"right": {"mode": "static", "value_type": "boolean", "value": True},
						},
					],
				},
			],
		},
		"context": {"doc": {"status": "Open", "total": 50, "is_priority": True}},
		"expected": True,
	},
	{
		"name": "collection_predicate_any",
		"condition": {
			"type": "collection_predicate",
			"quantifier": "any",
			"source": {"mode": "variable", "path": {"scope": "doc", "segments": ["items"]}},
			"as": "line",
			"where": {
				"type": "comparison",
				"operator": "gt",
				"left": {"mode": "variable", "path": {"scope": "line", "segments": ["qty"]}},
				"right": {"mode": "static", "value_type": "integer", "value": 10},
			},
		},
		"context": {
			"doc": {
				"items": [
					{"item_code": "I1", "qty": 5},
					{"item_code": "I2", "qty": 12},
				]
			}
		},
		"expected": True,
	},
]

NEGATIVE_VALIDATION_FIXTURES = [
	{
		"name": "unknown_transient_id_key",
		"condition": {
			"type": "comparison",
			"operator": "eq",
			"id": "ui-node-999",
			"left": {"mode": "static", "value_type": "string", "value": "a"},
			"right": {"mode": "static", "value_type": "string", "value": "a"},
		},
		"expected_error_code": "UNKNOWN_KEY",
	},
	{
		"name": "one_child_group",
		"condition": {
			"type": "group",
			"operator": "and",
			"children": [
				{
					"type": "comparison",
					"operator": "is_set",
					"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["name"]}},
				}
			],
		},
		"expected_error_code": "ONE_CHILD_GROUP",
	},
	{
		"name": "unknown_operator_regex",
		"condition": {
			"type": "comparison",
			"operator": "regex",
			"left": {"mode": "static", "value_type": "string", "value": "abc"},
			"right": {"mode": "static", "value_type": "string", "value": "^a"},
		},
		"expected_error_code": "UNKNOWN_OPERATOR",
	},
	{
		"name": "invalid_arity_unary_with_right",
		"condition": {
			"type": "comparison",
			"operator": "is_set",
			"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["status"]}},
			"right": {"mode": "static", "value_type": "string", "value": "unexpected"},
		},
		"expected_error_code": "INVALID_ARITY",
	},
]
