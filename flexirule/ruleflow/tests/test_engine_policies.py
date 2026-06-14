# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import time
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.engine import RuleEngine


class TestEnginePolicies(FrappeTestCase):
	def test_retry_policy_exponential_backoff(self):
		"""Verify that 'Retry' policy performs retries (simulated)"""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Retry Policy Rule",
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
						"next_step_if_true": "failing_node",
					},
					{
						"action_id": "failing_node",
						"action_type": "Process",
						"action_label": "Fail Always",
						"process_name": "Validation",  # Assuming Validation exists
						"operation": "invalid_operation",  # Will fail
						"on_error": "Retry",
						"retry_count": 2,
						"is_enabled": 1,
					},
				],
			}
		)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		# Mock time.sleep to avoid waiting in tests
		with patch("time.sleep") as mocked_sleep:
			with self.assertRaises(Exception):
				engine.execute(doc)

			# With retry_count=2, it should attempt initial (0), then retry 1 and 2.
			# Total 2 sleep calls: 2^0=1s and 2^1=2s.
			self.assertEqual(mocked_sleep.call_count, 2)
			mocked_sleep.assert_any_call(1)
			mocked_sleep.assert_any_call(2)

	def test_rollback_policy_savepoint(self):
		"""Verify that 'Rollback' policy uses savepoints and reverts changes"""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Rollback Policy Rule",
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
						"next_step_if_true": "mod_node",
					},
					{
						"action_id": "mod_node",
						"action_type": "Assignment",
						"action_label": "Modify Doc",
						"is_enabled": 1,
						"config": '[{"target": "doc.description", "operator": "set", "value": "Modified"}]',
						"next_step_if_true": "fail_node",
					},
					{
						"action_id": "fail_node",
						"action_type": "Raise Error",
						"action_label": "Fail",
						"is_enabled": 1,
						"value_template": "Abort!",
						"on_error": "Rollback",
					},
				],
			}
		)

		doc = frappe.get_doc({"doctype": "ToDo", "description": "Original"}).insert()
		engine = RuleEngine(rule)

		# The engine should raise the exception after rolling back
		with self.assertRaises(frappe.ValidationError):
			engine.execute(doc)

	def test_safe_frappe_api_restrictions(self):
		"""Verify SafeFrappeAPI blocks write operations"""
		from flexirule.ruleflow.core.engine import SafeFrappeAPI

		safe = SafeFrappeAPI()

		with self.assertRaisesRegex(PermissionError, "not allowed"):
			safe.db.set_value("ToDo", "some-name", "description", "hacked")

		with self.assertRaisesRegex(PermissionError, "not allowed"):
			safe.db.sql("DELETE FROM `tabToDo`")

		with self.assertRaisesRegex(PermissionError, "not allowed"):
			safe.new_doc("ToDo")
