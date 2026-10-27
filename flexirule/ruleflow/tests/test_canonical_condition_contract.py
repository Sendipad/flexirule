# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import unittest

from flexirule.ruleflow.core.condition_contract import (
	ConditionContractError,
	validate_condition_node,
)


class TestCanonicalConditionContract(unittest.TestCase):
	def test_valid_root_comparison(self):
		valid_comparison = {
			"type": "comparison",
			"operator": "eq",
			"left": {
				"mode": "variable",
				"path": {"scope": "doc", "segments": ["status"]},
			},
			"right": {
				"mode": "static",
				"value_type": "string",
				"value": "Open",
			},
		}
		validate_condition_node(valid_comparison)

	def test_valid_unary_comparison(self):
		valid_unary = {
			"type": "comparison",
			"operator": "is_set",
			"left": {
				"mode": "variable",
				"path": {"scope": "doc", "segments": ["customer"]},
			},
		}
		validate_condition_node(valid_unary)

	def test_valid_group_node(self):
		valid_group = {
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
					"type": "comparison",
					"operator": "gt",
					"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["total"]}},
					"right": {"mode": "static", "value_type": "decimal", "value": "100"},
				},
			],
		}
		validate_condition_node(valid_group)

	def test_valid_collection_predicate(self):
		valid_collection = {
			"type": "collection_predicate",
			"quantifier": "any",
			"source": {
				"mode": "variable",
				"path": {"scope": "doc", "segments": ["items"]},
			},
			"as": "item",
			"where": {
				"type": "comparison",
				"operator": "gt",
				"left": {"mode": "variable", "path": {"scope": "item", "segments": ["qty"]}},
				"right": {"mode": "static", "value_type": "integer", "value": 5},
			},
		}
		validate_condition_node(valid_collection)

	def test_invalid_one_child_group(self):
		one_child_group = {
			"type": "group",
			"operator": "and",
			"children": [
				{
					"type": "comparison",
					"operator": "is_set",
					"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["name"]}},
				}
			],
		}
		with self.assertRaises(ConditionContractError) as cm:
			validate_condition_node(one_child_group)
		self.assertEqual(cm.exception.code, "ONE_CHILD_GROUP")

	def test_invalid_empty_group(self):
		empty_group = {
			"type": "group",
			"operator": "and",
			"children": [],
		}
		with self.assertRaises(ConditionContractError) as cm:
			validate_condition_node(empty_group)
		self.assertEqual(cm.exception.code, "EMPTY_GROUP")

	def test_invalid_unknown_key_rejection(self):
		comparison_with_id = {
			"type": "comparison",
			"operator": "eq",
			"id": "ui-node-123",
			"left": {"mode": "static", "value_type": "string", "value": "a"},
			"right": {"mode": "static", "value_type": "string", "value": "b"},
		}
		with self.assertRaises(ConditionContractError) as cm:
			validate_condition_node(comparison_with_id)
		self.assertEqual(cm.exception.code, "UNKNOWN_KEY")

	def test_invalid_unknown_operator(self):
		unknown_op = {
			"type": "comparison",
			"operator": "regex",
			"left": {"mode": "static", "value_type": "string", "value": "abc"},
			"right": {"mode": "static", "value_type": "string", "value": "^a"},
		}
		with self.assertRaises(ConditionContractError) as cm:
			validate_condition_node(unknown_op)
		self.assertEqual(cm.exception.code, "UNKNOWN_OPERATOR")

	def test_invalid_arity_unary_with_right(self):
		unary_with_right = {
			"type": "comparison",
			"operator": "is_set",
			"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["name"]}},
			"right": {"mode": "static", "value_type": "string", "value": "extra"},
		}
		with self.assertRaises(ConditionContractError) as cm:
			validate_condition_node(unary_with_right)
		self.assertEqual(cm.exception.code, "INVALID_ARITY")
