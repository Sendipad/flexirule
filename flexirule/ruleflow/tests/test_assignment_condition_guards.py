# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Strict Canonical-Only Assignment guard compilation and execution tests."""

import json
import unittest
from types import SimpleNamespace

from flexirule.ruleflow.core.action_handlers.assignment import AssignmentHandler
from flexirule.ruleflow.core.condition_errors import ConditionValidationError
from flexirule.ruleflow.core.engine import RuleEngine


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

	def test_legacy_expression_fields_are_rejected(self):
		config = json.dumps([{"target": "doc.status", "when_expression": "doc.status == 'Open'"}])
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "unsupported_assignment_guard")

	def test_legacy_dict_guard_is_rejected(self):
		config = json.dumps(
			[
				{
					"target": "doc.status",
					"when_condition": {"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Open"}},
				}
			]
		)
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "unsupported_assignment_guard")

	def test_unknown_legacy_guard_shape_is_rejected(self):
		config = '[{"target":"doc.status","when_condition":{"unexpected":"shape"}}]'
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "unsupported_assignment_guard")

	def test_empty_legacy_group_is_rejected(self):
		config = '[{"target":"doc.status","when_condition":{"op":"and","conditions":[]}}]'
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "unsupported_assignment_guard")

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

	def test_json_encoded_legacy_guard_is_rejected(self):
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
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "unsupported_assignment_guard")

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

	def test_runtime_assignment_execution_does_not_mutate_doc_when_later_row_has_invalid_guard(self):
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

		self.assertEqual(raised.exception.code, "unsupported_assignment_guard")
		self.assertEqual(doc["status"], "Open")
		self.assertEqual(doc["remarks"], "Initial")

	def test_supplied_when_condition_canonical_is_rejected(self):
		config = '[{"target":"doc.status","when_condition_canonical":{"unexpected":"shape"}}]'
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "unsupported_assignment_guard")

	def test_runtime_assignment_execution_does_not_mutate_doc_when_later_row_supplies_when_condition_canonical(
		self,
	):
		config = [
			{"target": "doc.status", "value": "Closed"},
			{"target": "doc.remarks", "when_condition_canonical": {"unexpected": "shape"}},
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

		self.assertEqual(raised.exception.code, "unsupported_assignment_guard")
		self.assertEqual(doc["status"], "Open")
		self.assertEqual(doc["remarks"], "Initial")

	def test_runtime_assignment_execution_preflight_blocks_mutation_on_later_invalid_doctype_field(self):
		# Row 1 would mutate doc.status to 'Closed', but Row 2 has a guard with an invalid field on ToDo
		invalid_field_guard = {
			"type": "comparison",
			"operator": "eq",
			"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["non_existent_todo_field"]}},
			"right": {"mode": "static", "value_type": "string", "value": "test"},
		}
		config = [
			{"target": "doc.status", "value": "Closed"},
			{"target": "doc.description", "value": "New Description", "when_condition": invalid_field_guard},
		]
		action = SimpleNamespace(
			is_enabled=True,
			name="act-preflight-1",
			action_id="act-preflight-1",
			action_type="Assignment",
			action_label="Assignment Preflight Test",
			config=config,
		)
		rule = SimpleNamespace(
			name="test-rule-preflight",
			actions=[action],
			document_type="ToDo",
		)
		engine = RuleEngine(rule)
		doc = {"doctype": "ToDo", "status": "Open", "description": "Original Description"}
		context = {"doc": doc}
		handler = AssignmentHandler()

		with self.assertRaises(ConditionValidationError) as raised:
			handler.execute(action, context, engine)

		self.assertEqual(raised.exception.code, "unknown_field")
		# Crucial check: row 1 must NOT have mutated doc.status before row 2 failed preflight!
		self.assertEqual(doc["status"], "Open")
		self.assertEqual(doc["description"], "Original Description")

	def test_runtime_assignment_execution_preflight_blocks_mutation_with_cached_action_plan(self):
		from unittest.mock import patch

		from flexirule.ruleflow.core.action_plan_cache import clear_rule_action_plan_cache

		clear_rule_action_plan_cache()
		invalid_operator_guard = {
			"type": "comparison",
			"operator": "gt",
			"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["description"]}},
			"right": {"mode": "static", "value_type": "string", "value": "test"},
		}
		config = [
			{"target": "doc.status", "value": "Closed"},
			{
				"target": "doc.description",
				"value": "New Description",
				"when_condition": invalid_operator_guard,
			},
		]
		action = SimpleNamespace(
			is_enabled=True,
			name="act-preflight-cached",
			action_id="act-preflight-cached",
			action_type="Assignment",
			action_label="Assignment Preflight Cached Test",
			config=config,
		)
		rule = SimpleNamespace(
			name="test-rule-preflight-cached",
			actions=[action],
			document_type="ToDo",
		)
		engine = RuleEngine(rule)
		doc = {"doctype": "ToDo", "status": "Open", "description": "Original Description"}
		context = {"doc": doc}
		handler = AssignmentHandler()

		# Even if get_action_plan returns a plan without DocType pre-validation, runtime preflight catches it
		fake_plan = {
			"rows": [
				{"target": "doc.status", "operator": "set", "value": "Closed"},
				{
					"target": "doc.description",
					"operator": "set",
					"value": "New Description",
					"when_condition_canonical": invalid_operator_guard,
				},
			]
		}
		with patch(
			"flexirule.ruleflow.core.action_handlers.assignment.get_action_plan", return_value=fake_plan
		):
			with self.assertRaises(ConditionValidationError) as raised:
				handler.execute(action, context, engine)

		self.assertEqual(raised.exception.code, "operand_type_mismatch")
		self.assertEqual(doc["status"], "Open")
		self.assertEqual(doc["description"], "Original Description")


if __name__ == "__main__":
	unittest.main()
