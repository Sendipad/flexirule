# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestRuleAction(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")

	def test_validate_action_id_required(self):
		"""Verify that action_id is required for Rule Action"""
		rule_action = frappe.get_doc(
			{
				"doctype": "Rule Action",
				"action_label": "Test Action",
				"action_type": "Process",
				"is_enabled": 1,
			}
		)
		with self.assertRaises(frappe.MandatoryError):
			rule_action.insert()

	def test_validate_action_type_options(self):
		"""Verify that action_type must be from the allowed options"""
		rule_action = frappe.get_doc(
			{
				"doctype": "Rule Action",
				"action_id": "test_1",
				"action_label": "Test Action",
				"action_type": "Invalid Type",
				"is_enabled": 1,
			}
		)
		# Frappe Select fields throw ValidationError if value is not in options
		with self.assertRaises(frappe.ValidationError):
			rule_action.insert()

	def test_assignment_config_validation(self):
		"""Verify that Assignment actions require config"""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Assignment Validation",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,  # Must be active for strict validation in 'full' mode
				"actions": [
					{
						"action_id": "assign_1",
						"action_type": "Assignment",
						"action_label": "Missing Config",
						"is_enabled": 1,
						# "config" is missing
					}
				],
			}
		)
		# Rule.validate() calls validate_with_service which uses mode='full' for active rules
		with self.assertRaisesRegex(frappe.ValidationError, "requires field 'config'"):
			rule.validate()

	def test_condition_missing_compiled_expression_fails_activation(self):
		"""Verify that Condition actions must have compiled_expression if rule is active"""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Condition Activation",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"actions": [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"action_label": "Start",
						"is_enabled": 1,
						"next_step_if_true": "cond_1",
					},
					{
						"action_id": "cond_1",
						"action_type": "Condition",
						"action_label": "Condition Missing Compiled",
						"is_enabled": 1,
						"config": '{"op": "and", "conditions": []}',
						# compiled_expression is missing
						"next_step_if_true": "node_end",
						"next_step_if_false": "node_end",
					},
					{
						"action_id": "node_end",
						"action_type": "Stop",
						"action_label": "End",
						"operation": "Success",
						"is_enabled": 1,
					},
				],
			}
		)
		with self.assertRaisesRegex(frappe.ValidationError, "is a Condition but no condition is defined"):
			rule.validate()
