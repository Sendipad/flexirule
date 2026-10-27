# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Runtime tests for canonical condition semantics and isolation."""

import json
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from typing import Any

from flexirule.ruleflow.core.condition_errors import ConditionEvaluationError, ConditionValidationError
from flexirule.ruleflow.core.condition_evaluator import (
	clear_condition_plan_cache,
	condition_plan_cache_info,
	compile_condition,
	evaluate_condition,
	_evaluate_node,
)
from flexirule.ruleflow.core.value_resolver import CollectionResolver


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "canonical_condition_fixtures.json"


def variable(scope, *segments):
	return {"mode":"variable","path":{"scope":scope,"segments":list(segments)}}


def static(value_type, value):
	return {"mode":"static","value_type":value_type,"value":value}


def compare(operator_id, left, right=None):
	node = {"type":"comparison","operator":operator_id,"left":left}
	if operator_id not in {
		"is_set","is_not_set","is_null","is_not_null","is_empty","is_not_empty","is_submittable"
	}:
		node["right"] = right
	return node


class TestCanonicalConditionEvaluator(unittest.TestCase):
	fixtures: dict[str, Any]
	@classmethod
	def setUpClass(cls):
		cls.fixtures = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

	def setUp(self):
		clear_condition_plan_cache()

	def test_root_comparison_and_nested_groups(self):
		node = self.fixtures["valid"]["root_comparison"]
		self.assertTrue(evaluate_condition(node, {"doc":{"status":"Open"}}))
		self.assertFalse(evaluate_condition(node, {"doc":{"status":"Closed"}}))
		nested = self.fixtures["valid"]["nested_and_or"]
		self.assertTrue(evaluate_condition(nested, {"doc":{"status":"Open","total":500,"priority":True}}))
		self.assertFalse(evaluate_condition(nested, {"doc":{"status":"Closed","total":500,"priority":True}}))

	def test_missing_is_distinct_from_null_and_falsy_values(self):
		missing = variable("doc", "not_present")
		self.assertFalse(evaluate_condition(compare("is_set", missing), {"doc":{}}))
		self.assertTrue(evaluate_condition(compare("is_not_set", missing), {"doc":{}}))
		self.assertFalse(evaluate_condition(compare("is_set", missing), {"doc":{"not_present":None}}))
		self.assertTrue(evaluate_condition(compare("is_set", variable("doc","flag")), {"doc":{"flag":False}}))
		self.assertTrue(evaluate_condition(compare("is_set", variable("doc","count")), {"doc":{"count":0}}))
		self.assertTrue(evaluate_condition(compare("is_set", variable("doc","text")), {"doc":{"text":" "}}))
		with self.assertRaises(ConditionEvaluationError) as raised:
			evaluate_condition(compare("is_null", missing), {"doc":{}})
		self.assertEqual(raised.exception.code, "missing_operand")
		self.assertTrue(evaluate_condition(compare("is_null", variable("doc","value")), {"doc":{"value":None}}))

	def test_boolean_is_not_equal_to_numeric_zero(self):
		self.assertFalse(evaluate_condition(
			compare("eq", variable("doc","count"), static("boolean", False)),
			{"doc":{"count":0}},
		))
		self.assertFalse(evaluate_condition(
			compare("eq", variable("doc","flag"), static("integer", 0)),
			{"doc":{"flag":False}},
		))

	def test_decimal_comparison_is_precision_safe(self):
		node = compare("gt", static("decimal","9007199254740992.2"), static("decimal","9007199254740992.1"))
		self.assertTrue(evaluate_condition(node))
		self.assertEqual(Decimal("0.1") + Decimal("0.2"), Decimal("0.3"))

	def test_text_and_length_operators_are_literal_and_case_sensitive(self):
		self.assertTrue(evaluate_condition(compare("contains", static("string","aBc"), static("string","B"))))
		self.assertFalse(evaluate_condition(compare("contains", static("string","aBc"), static("string","b"))))
		self.assertTrue(evaluate_condition(compare("starts_with", static("string","FlexiRule"), static("string","Flexi"))))
		self.assertTrue(evaluate_condition(compare("ends_with", static("string","FlexiRule"), static("string","Rule"))))
		self.assertTrue(evaluate_condition(compare("length_eq", static("string","abcd"), static("integer",4))))
		self.assertTrue(evaluate_condition(compare("is_empty", static("list",[]))))

	def test_operator_matrix_uses_canonical_operator_ids(self):
		self.assertTrue(evaluate_condition(compare("ne", static("integer", 1), static("integer", 2))))
		self.assertTrue(evaluate_condition(compare("gte", static("integer", 2), static("integer", 2))))
		self.assertTrue(evaluate_condition(compare("lte", static("integer", 2), static("integer", 2))))
		self.assertTrue(evaluate_condition(compare("in", static("string", "Open"), static("list", ["Open", "Closed"]))))
		self.assertTrue(evaluate_condition(compare("not_in", static("string", "Open"), static("list", ["Closed"]))))
		self.assertTrue(evaluate_condition(compare("not_contains", static("string", "FlexiRule"), static("string", "other"))))
		self.assertTrue(evaluate_condition(compare("length_gt", static("string", "abcd"), static("integer", 3))))
		self.assertTrue(evaluate_condition(compare("length_gte", static("string", "abcd"), static("integer", 4))))
		self.assertTrue(evaluate_condition(compare("length_lt", static("string", "abcd"), static("integer", 5))))
		self.assertTrue(evaluate_condition(compare("length_lte", static("string", "abcd"), static("integer", 4))))
		self.assertTrue(evaluate_condition(compare("is_not_null", static("string", "x"))))
		self.assertTrue(evaluate_condition(compare("is_not_empty", static("string", "x"))))

	def test_metadata_operators_use_frappe_metadata(self):
		class FakeMeta:
			is_submittable = 1

			@staticmethod
			def has_field(fieldname):
				return fieldname == "status"

		with patch("frappe.get_meta", return_value=FakeMeta()):
			self.assertTrue(evaluate_condition(compare("is_submittable", static("string", "ToDo"))))
			self.assertTrue(evaluate_condition(
				compare("has_field", static("string", "ToDo"), static("string", "status"))
			))
			self.assertFalse(evaluate_condition(
				compare("has_field", static("string", "ToDo"), static("string", "missing"))
			))

	def test_compiled_static_plan_is_immutable_after_input_mutation(self):
		node = compare(
			"eq",
			static("list", [1, {"x": 2}]),
			static("list", [1, {"x": 2}]),
		)
		plan = compile_condition(node)
		self.assertTrue(_evaluate_node(plan, {}))
		node["left"]["value"][1]["x"] = 99
		self.assertTrue(_evaluate_node(plan, {}))

	def test_true_short_circuit_and_prevents_later_resolution(self):
		node = {
			"type":"group","operator":"and","children":[
				compare("eq", static("integer",1), static("integer",2)),
				compare("eq", variable("doc","missing"), static("integer",2)),
			],
		}
		self.assertFalse(evaluate_condition(node, {"doc":{}}))

	def test_false_short_circuit_or_prevents_later_resolution(self):
		node = {
			"type":"group","operator":"or","children":[
				compare("eq", static("integer",1), static("integer",1)),
				compare("eq", variable("doc","missing"), static("integer",2)),
			],
		}
		self.assertTrue(evaluate_condition(node, {"doc":{}}))

	def test_collection_quantifiers_keep_row_alias_context(self):
		base = self.fixtures["valid"]["root_collection_any"]
		context = {"doc":{"items":[{"amount":1},{"amount":3}]}}
		self.assertTrue(evaluate_condition(base, context))
		all_rows = {**base, "quantifier":"all"}
		self.assertFalse(evaluate_condition(all_rows, context))
		no_rows = {**base, "quantifier":"none"}
		self.assertFalse(evaluate_condition(no_rows, context))
		none_empty = {**base, "quantifier":"none"}
		self.assertTrue(evaluate_condition(none_empty, {"doc":{"items":[]}}))
		all_empty = {**base, "quantifier":"all"}
		self.assertTrue(evaluate_condition(all_empty, {"doc":{"items":[]}}))

	def test_collection_resolver_applies_canonical_predicate_for_count_any_all(self):
		predicate = compare(
			"gt",
			variable("row", "amount"),
			static("integer", 2),
		)
		context = {"doc": {"items": [{"amount": 1}, {"amount": 3}]}}

		count = CollectionResolver("doc.items", operation="count", condition=predicate)
		any_match = CollectionResolver("doc.items", operation="any", condition=predicate)
		all_match = CollectionResolver("doc.items", operation="all", condition=predicate)

		self.assertEqual(count.resolve(context), 1)
		self.assertTrue(any_match.resolve(context))
		self.assertFalse(all_match.resolve(context))

	def test_nested_collection_predicates_share_total_row_visit_budget(self):
		inner = {
			"type": "collection_predicate",
			"quantifier": "all",
			"source": {"scope": "item_row", "segments": ["parts"]},
			"as": "part_row",
			"where": compare(
				"eq",
				variable("part_row", "enabled"),
				static("boolean", True),
			),
		}
		node = {
			"type": "collection_predicate",
			"quantifier": "all",
			"source": {"scope": "doc", "segments": ["items"]},
			"as": "item_row",
			"where": inner,
		}
		context = {
			"doc": {
				"items": [
					{"parts": [{"enabled": True} for _ in range(100)]}
					for _ in range(100)
				]
			}
		}
		with self.assertRaises(ConditionEvaluationError) as raised:
			evaluate_condition(node, context)
		self.assertEqual(raised.exception.code, "collection_evaluation_budget_exceeded")

	def test_collection_row_limit_fails_without_truncation(self):
		base = self.fixtures["valid"]["root_collection_any"]
		with self.assertRaises(ConditionEvaluationError) as raised:
			evaluate_condition(base, {"doc":{"items":[{"amount":3}] * 10001}})
		self.assertEqual(raised.exception.code, "collection_limit_exceeded")

	def test_collection_exact_limit_is_allowed(self):
		base = self.fixtures["valid"]["root_collection_any"]
		self.assertTrue(evaluate_condition(base, {"doc":{"items":[{"amount":3}] * 10000}}))

	def test_cache_never_caches_context_or_result(self):
		node = compare("eq", variable("doc","value"), static("integer",5))
		self.assertTrue(evaluate_condition(node, {"doc":{"value":5}}))
		before = condition_plan_cache_info().hits
		self.assertFalse(evaluate_condition(node, {"doc":{"value":4}}))
		self.assertGreaterEqual(condition_plan_cache_info().hits, before + 1)

	def test_cached_plan_does_not_change_payload_or_context(self):
		node = compare("eq", static("list",[1, {"x":2}]), static("list",[1, {"x":2}]))
		self.assertTrue(evaluate_condition(node))
		# A mutation of the input after compilation cannot mutate the cached plan.
		node["left"]["value"][1]["x"] = 99
		self.assertTrue(evaluate_condition(compare("eq", static("list",[1, {"x":2}]), static("list",[1, {"x":2}]))))

	def test_malformed_condition_is_not_a_boolean_result(self):
		with self.assertRaises(ConditionValidationError):
			evaluate_condition({"type":"group","operator":"and","children":[]})
		with self.assertRaises(ConditionValidationError):
			evaluate_condition({"type":"comparison","operator":"==","left":static("integer",1),"right":static("integer",1)})


if __name__ == "__main__":
	unittest.main()
