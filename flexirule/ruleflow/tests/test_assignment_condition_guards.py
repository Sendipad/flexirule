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


if __name__ == "__main__":
	unittest.main()
