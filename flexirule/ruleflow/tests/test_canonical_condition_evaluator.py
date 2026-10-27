# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import unittest
from decimal import Decimal

from flexirule.ruleflow.core.condition_evaluator import (
	ConditionEvaluationError,
	evaluate_canonical_condition,
)


class TestCanonicalConditionEvaluator(unittest.TestCase):
	def setUp(self):
		self.context = {
			"doc": {
				"status": "Open",
				"grand_total": 1500,
				"is_priority": True,
				"zero_val": 0,
				"false_val": False,
				"empty_str": "",
				"whitespace_str": "   ",
				"null_val": None,
				"customer_name": "Acme Corp",
				"items": [
					{"item_code": "A1", "qty": 10, "amount": 100},
					{"item_code": "B2", "qty": 2, "amount": 20},
				],
			},
			"vars": {"discount": 50},
		}

	def test_comparison_evaluation(self):
		# status == "Open" -> True
		cond_eq = {
			"type": "comparison",
			"operator": "eq",
			"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["status"]}},
			"right": {"mode": "static", "value_type": "string", "value": "Open"},
		}
		self.assertTrue(evaluate_canonical_condition(cond_eq, self.context))

		# grand_total > 1000 -> True
		cond_gt = {
			"type": "comparison",
			"operator": "gt",
			"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["grand_total"]}},
			"right": {"mode": "static", "value_type": "decimal", "value": "1000"},
		}
		self.assertTrue(evaluate_canonical_condition(cond_gt, self.context))

	def test_false_vs_zero_distinction(self):
		# false_val == 0 -> False in canonical evaluation
		cond_false_eq_zero = {
			"type": "comparison",
			"operator": "eq",
			"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["false_val"]}},
			"right": {"mode": "static", "value_type": "integer", "value": 0},
		}
		self.assertFalse(evaluate_canonical_condition(cond_false_eq_zero, self.context))

	def test_is_set_semantics(self):
		# is_set on status -> True
		cond_set = {
			"type": "comparison",
			"operator": "is_set",
			"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["status"]}},
		}
		self.assertTrue(evaluate_canonical_condition(cond_set, self.context))

		# is_set on empty_str -> False
		cond_set_empty = {
			"type": "comparison",
			"operator": "is_set",
			"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["empty_str"]}},
		}
		self.assertFalse(evaluate_canonical_condition(cond_set_empty, self.context))

		# is_set on whitespace_str -> True (whitespace is set)
		cond_set_ws = {
			"type": "comparison",
			"operator": "is_set",
			"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["whitespace_str"]}},
		}
		self.assertTrue(evaluate_canonical_condition(cond_set_ws, self.context))

		# is_set on zero_val -> True
		cond_set_zero = {
			"type": "comparison",
			"operator": "is_set",
			"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["zero_val"]}},
		}
		self.assertTrue(evaluate_canonical_condition(cond_set_zero, self.context))

	def test_missing_path_raises_error(self):
		# Comparison on missing path -> raises ConditionEvaluationError
		cond_missing = {
			"type": "comparison",
			"operator": "eq",
			"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["non_existent_field"]}},
			"right": {"mode": "static", "value_type": "string", "value": "val"},
		}
		with self.assertRaises(ConditionEvaluationError) as cm:
			evaluate_canonical_condition(cond_missing, self.context)
		self.assertEqual(cm.exception.code, "MISSING_PATH")

	def test_and_group_short_circuit(self):
		# First child evaluates False -> second child (which is invalid/broken) is NEVER evaluated!
		group_and = {
			"type": "group",
			"operator": "and",
			"children": [
				{
					"type": "comparison",
					"operator": "eq",
					"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["status"]}},
					"right": {"mode": "static", "value_type": "string", "value": "Closed"},
				},
				{
					"type": "comparison",
					"operator": "gt",
					"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["non_existent"]}},
					"right": {"mode": "static", "value_type": "integer", "value": 10},
				},
			],
		}
		# Should return False without raising exception on second child
		self.assertFalse(evaluate_canonical_condition(group_and, self.context))

	def test_or_group_short_circuit(self):
		# First child evaluates True -> second child (which is invalid/broken) is NEVER evaluated!
		group_or = {
			"type": "group",
			"operator": "or",
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
					"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["non_existent"]}},
					"right": {"mode": "static", "value_type": "integer", "value": 10},
				},
			],
		}
		# Should return True without raising exception on second child
		self.assertTrue(evaluate_canonical_condition(group_or, self.context))

	def test_collection_predicate(self):
		# any item has qty > 5 -> True (item A1 has qty 10)
		collection_any = {
			"type": "collection_predicate",
			"quantifier": "any",
			"source": {"mode": "variable", "path": {"scope": "doc", "segments": ["items"]}},
			"as": "line",
			"where": {
				"type": "comparison",
				"operator": "gt",
				"left": {"mode": "variable", "path": {"scope": "line", "segments": ["qty"]}},
				"right": {"mode": "static", "value_type": "integer", "value": 5},
			},
		}
		self.assertTrue(evaluate_canonical_condition(collection_any, self.context))

		# all items have qty > 5 -> False (item B2 has qty 2)
		collection_all = {
			"type": "collection_predicate",
			"quantifier": "all",
			"source": {"mode": "variable", "path": {"scope": "doc", "segments": ["items"]}},
			"as": "line",
			"where": {
				"type": "comparison",
				"operator": "gt",
				"left": {"mode": "variable", "path": {"scope": "line", "segments": ["qty"]}},
				"right": {"mode": "static", "value_type": "integer", "value": 5},
			},
		}
		self.assertFalse(evaluate_canonical_condition(collection_all, self.context))

	def test_resolver_denied_by_default(self):
		cond_resolver = {
			"type": "comparison",
			"operator": "eq",
			"left": {
				"mode": "resolver",
				"family": "custom",
				"operation": "lookup",
				"config": {},
			},
			"right": {"mode": "static", "value_type": "string", "value": "x"},
		}
		with self.assertRaises(ConditionEvaluationError) as cm:
			evaluate_canonical_condition(cond_resolver, self.context)
		self.assertEqual(cm.exception.code, "RESOLVER_DENIED")
