# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers.condition import ConditionHandler


class TestConditionHandler(FrappeTestCase):
	def test_invalid_source_payload_does_not_use_stale_compiled_expression(self):
		action = frappe._dict(
			{
				"action_label": "Invalid Condition",
				"config": "{invalid-json",
				"condition_json": None,
				"compiled_expression": "True",
				"next_step_if_true": "TRUE",
				"next_step_if_false": "FALSE",
			}
		)

		with self.assertRaises(frappe.ValidationError):
			ConditionHandler().execute(action, {}, engine=None)

	def test_malformed_canonical_config_does_not_fall_back_to_legacy_condition_json(self):
		action = frappe._dict(
			{
				"action_label": "Malformed Canonical Condition",
				"config": "{invalid-json",
				"condition_json": '[{"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Open"}}]',
				"compiled_expression": "True",
				"next_step_if_true": "TRUE",
				"next_step_if_false": "FALSE",
			}
		)

		with self.assertRaises(frappe.ValidationError):
			ConditionHandler().execute(action, {}, engine=None)

	def test_compiled_expression_is_only_used_when_source_payload_is_absent(self):
		action = frappe._dict(
			{
				"action_label": "Legacy Condition",
				"config": None,
				"condition_json": None,
				"compiled_expression": "legacy",
				"next_step_if_true": "TRUE",
				"next_step_if_false": "FALSE",
			}
		)

		class LegacyEngine:
			@staticmethod
			def _evaluate_python_condition(expression, context):
				return expression == "legacy"

		result, next_id = ConditionHandler().execute(action, {}, LegacyEngine())
		self.assertTrue(result)
		self.assertEqual(next_id, "TRUE")
