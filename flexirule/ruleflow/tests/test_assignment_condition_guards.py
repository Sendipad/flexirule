# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Strict Assignment-config compilation tests (no database fixtures required)."""

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
		self.assertEqual(raised.exception.code, "unknown_legacy_guard_shape")

	def test_empty_legacy_group_is_rejected(self):
		config = '[{"target":"doc.status","when_condition":{"op":"and","conditions":[]}}]'
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "empty_legacy_group")

	def test_json_encoded_canonical_guard_is_parsed_and_validated(self):
		config = (
			'[{"target":"doc.status","when_condition":"{\\"type\\":\\"comparison\\",'
			'\\"operator\\":\\"eq\\",\\"left\\":{\\"mode\\":\\"static\\",\\"value_type\\":\\"string\\",'
			'\\"value\\":\\"Open\\"},\\"right\\":{\\"mode\\":\\"static\\",\\"value_type\\":\\"string\\",'
			'\\"value\\":\\"Open\\"}}"}]'
		)
		plan = AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(len(plan), 1)
		self.assertEqual(plan[0]["when_condition_canonical"]["operator"], "eq")

	def test_json_encoded_legacy_guard_is_parsed(self):
		config = (
			'[{"target":"doc.status","when_condition":"{\\"left\\":{\\"ref\\":\\"doc.status\\"},'
			'\\"op\\":\\"==\\",\\"right\\":{\\"value\\":\\"Open\\"}}"}]'
		)
		plan = AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(len(plan), 1)
		self.assertEqual(plan[0]["when_expression"], "doc.get('status') == 'Open'")

	def test_malformed_json_encoded_guard_is_rejected(self):
		config = '[{"target":"doc.status","when_condition":"{not-json"}]'
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "invalid_json")

	def test_unsupported_when_condition_string_is_rejected(self):
		config = '[{"target":"doc.status","when_condition":"if True: import os; os.system(\\"ls\\")"}]'
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "invalid_when_expression")

	def test_valid_supported_legacy_guard_still_compiles(self):
		config = (
			'[{"target":"doc.status","when_condition":[{"left":{"ref":"doc.status"},'
			'"op":"==","right":{"value":"Open"}}]}]'
		)
		plan = AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(len(plan), 1)
		self.assertEqual(plan[0]["when_expression"], "(doc.get('status') == 'Open')")

	def test_invalid_guard_never_mutates_assignment_target(self):
		# Preflight compilation fails before execution starts
		config = (
			'[{"target":"doc.status","operator":"set","value":"Closed",'
			'"when_condition":{"type":"comparison","operator":"invalid_op",'
			'"left":{"mode":"static","value_type":"string","value":"Open"},'
			'"right":{"mode":"static","value_type":"string","value":"Closed"}}}]'
		)
		handler = AssignmentHandler()
		with self.assertRaises(ConditionValidationError):
			handler._to_config_cache_key(config)
			AssignmentHandler._get_compiled_plan(config)

	def test_invalid_later_guard_prevents_earlier_assignment_mutation(self):
		# Row 1 is valid, Row 2 has an invalid guard. Whole plan must fail preflight compilation.
		config = (
			"["
			'{"target":"doc.status","operator":"set","value":"Pending"},'
			'{"target":"doc.priority","operator":"set","value":"High",'
			'"when_condition":{"type":"comparison","operator":"bad_operator",'
			'"left":{"mode":"static","value_type":"string","value":"Open"}}}'
			"]"
		)
		with self.assertRaises(ConditionValidationError) as raised:
			AssignmentHandler._get_compiled_plan(config)
		self.assertEqual(raised.exception.code, "unknown_operator")


if __name__ == "__main__":
	unittest.main()
