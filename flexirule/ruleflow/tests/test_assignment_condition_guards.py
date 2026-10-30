# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Strict Assignment-config compilation tests (no database fixtures required)."""

import json
import unittest

from flexirule.ruleflow.core.action_handlers.assignment import AssignmentHandler
from flexirule.ruleflow.core.condition_errors import ConditionValidationError


class TestAssignmentConditionGuards(unittest.TestCase):
	def test_malformed_assignment_json_is_not_treated_as_empty_plan(self):
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan("{not-json")
		self.assertEqual(raised.exception.code, "invalid_assignment_json")

	def test_non_array_assignment_config_is_rejected(self):
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan('{"target":"doc.status"}')
		self.assertEqual(raised.exception.code, "assignment_config_not_list")

	def test_malformed_assignment_row_is_not_silently_skipped(self):
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan('[{"target":"doc.status"}, null]')
		self.assertEqual(raised.exception.code, "invalid_assignment_row")
		self.assertEqual(raised.exception.path, "assignments[1]")

	def test_invalid_canonical_guard_is_rejected_before_execution(self):
		config = (
			'[{"target":"doc.status","operator":"set","value":"Closed",'
			'"when_condition":{"type":"comparison","operator":"==",'
			'"left":{"mode":"static","value_type":"string","value":"Open"},'
			'"right":{"mode":"static","value_type":"string","value":"Closed"}}}]'
		)
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "unknown_operator")

	def test_mixed_canonical_and_legacy_guard_formats_are_rejected(self):
		config = (
			'[{"target":"doc.status","when_expression":"doc.status == \\"Open\\"",'
			'"when_condition":{"type":"comparison","operator":"eq",'
			'"left":{"mode":"static","value_type":"string","value":"Open"},'
			'"right":{"mode":"static","value_type":"string","value":"Open"}}}]'
		)
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "multiple_guard_formats")

	def test_oversized_assignment_config_is_rejected_before_json_parse(self):
		handler = AssignmentHandler()
		with self.assertRaises(ConditionValidationError) as raised:
			handler._to_config_cache_key(" " * 2_000_001)
		self.assertEqual(raised.exception.code, "assignment_config_too_large")

	def test_large_valid_assignment_config_is_not_retained_in_lru(self):
		handler = AssignmentHandler()
		config = '[{"target":"doc.status","value":"' + ("x" * 70_000) + '"}]'
		key = handler._to_config_cache_key(config)
		before = AssignmentHandler._get_compiled_plan_cached.cache_info().currsize
		plan = AssignmentHandler._get_compiled_plan(key)
		after = AssignmentHandler._get_compiled_plan_cached.cache_info().currsize
		self.assertEqual(len(plan), 1)
		self.assertEqual(before, after)

	def test_unknown_legacy_guard_shape_is_rejected(self):
		config = '[{"target":"doc.status","when_condition":{"unexpected":"shape"}}]'
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "invalid_legacy_guard")

	def test_empty_legacy_group_is_rejected(self):
		config = '[{"target":"doc.status","when_condition":{"op":"and","conditions":[]}}]'
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "invalid_legacy_guard")

	def test_json_encoded_canonical_guard_is_parsed_and_validated(self):
		canonical_guard = {
			"type": "comparison",
			"operator": "eq",
			"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["status"]}},
			"right": {"mode": "static", "value_type": "string", "value": "Open"},
		}
		config = json.dumps(
			[
				{
					"target": "doc.status",
					"operator": "set",
					"value": "Closed",
					"when_condition": json.dumps(canonical_guard),
				}
			]
		)
		plan = AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(len(plan), 1)
		self.assertIn("when_condition_canonical", plan[0])

	def test_json_encoded_legacy_guard_is_parsed(self):
		legacy_guard = {
			"left": {"ref": "doc.status"},
			"op": "==",
			"right": {"value": "Open"},
		}
		config = json.dumps(
			[
				{
					"target": "doc.status",
					"when_condition": json.dumps(legacy_guard),
				}
			]
		)
		plan = AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(len(plan), 1)
		self.assertEqual(plan[0]["when_expression"], "doc.get('status') == 'Open'")

	def test_malformed_json_encoded_guard_is_rejected(self):
		config = '[{"target":"doc.status","when_condition":"{not valid json"}]'
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "invalid_json")

	def test_unsupported_when_condition_string_is_rejected(self):
		config = '[{"target":"doc.status","when_condition":"[invalid condition json string]"}]'
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "invalid_json")

	def test_valid_supported_legacy_guard_still_compiles(self):
		config = '[{"target":"doc.status","when_condition":{"left":{"ref":"doc.status"},"op":"==","right":{"value":"Open"}}}]'
		plan = AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(len(plan), 1)
		self.assertEqual(plan[0]["when_expression"], "doc.get('status') == 'Open'")

	def test_invalid_later_guard_prevents_earlier_assignment_mutation(self):
		config = (
			"["
			'{"target":"doc.status","value":"Closed"},'
			'{"target":"doc.remarks","when_condition":{"unexpected":"shape"}}'
			"]"
		)
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "invalid_legacy_guard")

	def test_invalid_when_condition_is_not_bypassed_by_when_expression(self):
		config = (
			'[{"target":"doc.status","value":"Closed",'
			'"when_condition":{"unexpected":"shape"},"when_expression":"True"}]'
		)
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "multiple_guard_formats")

	def test_partially_invalid_legacy_group_is_rejected(self):
		config = (
			'[{"target":"doc.status",'
			'"when_condition":{"op":"and","conditions":['
			'{"left":{"ref":"doc.status"},"op":"==","right":{"value":"Open"}},'
			'{"unexpected":"shape"}'
			"]}}]"
		)
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "invalid_legacy_guard")

	def test_runtime_assignment_execution_does_not_mutate_doc_when_later_row_has_invalid_guard(self):
		from types import SimpleNamespace

		from flexirule.ruleflow.core.engine import RuleEngine

		config = [
			{"target": "doc.status", "value": "Closed"},
			{"target": "doc.remarks", "when_condition": {"unexpected": "shape"}},
		]
		action = SimpleNamespace(
			is_enabled=True,
			name="act-1",
			action_id="act-1",
			action_type="Assignment",
			action_label="Assignment Action",
			config=config,
		)
		rule = SimpleNamespace(
			name="test-rule",
			actions=[action],
			document_type="ToDo",
		)
		engine = RuleEngine(rule)
		doc = {"status": "Open", "remarks": "Initial"}
		context = {"doc": doc}
		handler = AssignmentHandler()

		with self.assertRaises(ConditionValidationError) as raised:
			handler.execute(action, context, engine)

		self.assertEqual(raised.exception.code, "invalid_legacy_guard")
		self.assertEqual(doc["status"], "Open")
		self.assertEqual(doc["remarks"], "Initial")


if __name__ == "__main__":
	unittest.main()
