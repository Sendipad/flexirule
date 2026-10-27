# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Contract tests independent of a Bench site."""

import copy
import json
import unittest
from pathlib import Path
from typing import Any

from flexirule.ruleflow.core.condition_contract import (
	OPERATOR_REGISTRY,
	condition_contract_dto,
	validate_condition_node,
)
from flexirule.ruleflow.core.condition_errors import ConditionValidationError
from flexirule.ruleflow.core.condition_payload import detect_canonical_condition_payload
from flexirule.ruleflow.core.flexvalue_contract import validate_flex_value


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "canonical_condition_fixtures.json"


class TestCanonicalConditionContract(unittest.TestCase):
	fixtures: dict[str, Any]
	@classmethod
	def setUpClass(cls):
		cls.fixtures = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

	def test_shared_valid_root_variants(self):
		for name, node in self.fixtures["valid"].items():
			with self.subTest(name=name):
				validate_condition_node(node)

	def test_direct_root_comparison_is_valid(self):
		validate_condition_node(self.fixtures["valid"]["root_comparison"])

	def test_empty_and_single_child_groups_are_invalid(self):
		for name in ("empty_group", "unary_group"):
			with self.subTest(name=name), self.assertRaises(ConditionValidationError):
				validate_condition_node(self.fixtures["invalid"][name])

	def test_unknown_operator_node_and_keys_are_rejected(self):
		for name in ("unknown_operator", "unknown_node", "extra_key"):
			with self.subTest(name=name), self.assertRaises(ConditionValidationError):
				validate_condition_node(self.fixtures["invalid"][name])

	def test_canonical_payload_is_detected_without_unwrapping(self):
		node = self.fixtures["valid"]["root_comparison"]
		self.assertEqual(detect_canonical_condition_payload(node), (True, node))
		self.assertEqual(detect_canonical_condition_payload(json.dumps(node)), (True, node))

	def test_unknown_discriminated_node_never_falls_back_to_legacy(self):
		node = self.fixtures["invalid"]["unknown_node"]
		self.assertEqual(detect_canonical_condition_payload(node), (True, node))
		with self.assertRaises(ConditionValidationError):
			validate_condition_node(node)

	def test_envelope_is_rejected_not_guessed(self):
		with self.assertRaises(ConditionValidationError) as raised:
			detect_canonical_condition_payload({"schema":"old", "version":1, "root":self.fixtures["valid"]["root_comparison"]})
		self.assertEqual(raised.exception.code, "unsupported_condition_envelope")

	def test_payload_validation_does_not_mutate_input(self):
		node = copy.deepcopy(self.fixtures["valid"]["nested_and_or"])
		before = copy.deepcopy(node)
		validate_condition_node(node)
		self.assertEqual(node, before)

	def test_boolean_is_not_an_integer_literal(self):
		with self.assertRaises(ConditionValidationError):
			validate_flex_value({"mode":"static","value_type":"integer","value":True})

	def test_decimal_literal_must_be_finite_string(self):
		for value in (1.25, "NaN", "Infinity"):
			with self.subTest(value=value), self.assertRaises(ConditionValidationError):
				validate_flex_value({"mode":"static","value_type":"decimal","value":value})

	def test_unknown_resolver_defaults_to_denied(self):
		node = {
			"type":"comparison","operator":"eq",
			"left":{"mode":"resolver","family":"database","operation":"lookup","config":{}},
			"right":{"mode":"static","value_type":"string","value":"x"},
		}
		with self.assertRaises(ConditionValidationError) as raised:
			validate_condition_node(node)
		self.assertEqual(raised.exception.code, "resolver_not_allowed")

	def test_unhashable_discriminants_return_validation_errors(self):
		invalid_nodes: list[dict[str, Any]] = [
			{"type": "group", "operator": [], "children": []},
			{"type": "collection_predicate", "quantifier": [], "source": {}, "as": "row_item", "where": {}},
			{
				"type": "comparison",
				"operator": "eq",
				"left": {"mode": "static", "value_type": [], "value": "x"},
				"right": {"mode": "static", "value_type": "string", "value": "x"},
			},
		]
		for node in invalid_nodes:
			with self.subTest(node_type=node.get("type")), self.assertRaises(ConditionValidationError):
				validate_condition_node(node)

	def test_canonical_payload_size_is_bounded(self):
		from flexirule.ruleflow.core.flexvalue_contract import MAX_CONDITION_PAYLOAD_BYTES

		node = {
			"type": "comparison",
			"operator": "eq",
			"left": {"mode": "static", "value_type": "string", "value": "x" * MAX_CONDITION_PAYLOAD_BYTES},
			"right": {"mode": "static", "value_type": "string", "value": "x"},
		}
		with self.assertRaises(ConditionValidationError) as raised:
			validate_condition_node(node)
		self.assertEqual(raised.exception.code, "condition_payload_too_large")

	def test_nested_collection_alias_cannot_shadow_parent_alias(self):
		node = {
			"type": "collection_predicate",
			"quantifier": "any",
			"source": {"scope": "doc", "segments": ["items"]},
			"as": "row_item",
			"where": {
				"type": "collection_predicate",
				"quantifier": "any",
				"source": {"scope": "row_item", "segments": ["parts"]},
				"as": "row_item",
				"where": {
					"type": "comparison",
					"operator": "eq",
					"left": {"mode": "static", "value_type": "integer", "value": 1},
					"right": {"mode": "static", "value_type": "integer", "value": 1},
				},
			},
		}
		with self.assertRaises(ConditionValidationError) as raised:
			validate_condition_node(node)
		self.assertEqual(raised.exception.code, "invalid_collection_alias")

	def test_operator_contract_is_backend_owned_and_stable(self):
		dto = condition_contract_dto()
		self.assertEqual(dto["persisted_payload_version"], None)
		self.assertEqual(set(OPERATOR_REGISTRY), {item["id"] for item in dto["operators"]})
		self.assertNotIn("regex", OPERATOR_REGISTRY)
		self.assertNotIn("has_changed", OPERATOR_REGISTRY)
		self.assertNotIn("==", OPERATOR_REGISTRY)
		self.assertEqual(dto["limits"]["condition_depth"], 32)
		self.assertEqual(dto["limits"]["condition_nodes"], 1000)


if __name__ == "__main__":
	unittest.main()
