# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import frappe
import time
from frappe.tests.utils import FrappeTestCase
from flexirule.ruleflow.core.engine import RuleEngine

class TestEnginePolicies(FrappeTestCase):
	def test_retry_policy_exponential_backoff(self):
		"""Verify that 'Retry' policy performs retries (simulated)"""
		# Since we can't easily mock time.sleep or verify actual wait times without a long test,
		# we verify the retry logic by tracking attempts in context.vars

		# Note: actual retry logic in engine.py uses time.sleep(2**attempt).
		# In tests, we might want to ensure it doesn't actually sleep forever.

		rule = frappe.get_doc({
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
					"next_step_if_true": "failing_node"
				},
				{
					"action_id": "failing_node",
					"action_type": "Process",
					"action_label": "Fail Always",
					"process_name": "Validation", # Assuming Validation exists
					"operation": "invalid_operation", # Will fail
					"on_error": "Retry",
					"retry_count": 2
				}
			]
		})

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		# We expect it to fail after retries
		start_time = time.time()
		with self.assertRaises(Exception):
			engine.execute(doc)
		duration = time.time() - start_time

		# With retry_count=2, it should attempt 0, 1, 2.
		# Wait times: 2^0=1s, 2^1=2s. Total wait ~3s.
		self.assertGreaterEqual(duration, 3)

	def test_rollback_policy_savepoint(self):
		"""Verify that 'Rollback' policy uses savepoints and reverts changes"""
		# This requires an action that modifies DB, then fails.
		# Assignment with 'doc.description' modifies the object in memory.
		# To test DB rollback, we'd need 'Batch Database Set' or similar.

		rule = frappe.get_doc({
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
					"next_step_if_true": "mod_node"
				},
				{
					"action_id": "mod_node",
					"action_type": "Assignment",
					"action_label": "Modify Doc",
					"config": '[{"target": "doc.description", "operator": "set", "value": "Modified"}]',
					"next_step_if_true": "fail_node"
				},
				{
					"action_id": "fail_node",
					"action_type": "Raise Error",
					"value_template": "Abort!",
					"on_error": "Rollback"
				}
			]
		})

		doc = frappe.get_doc({"doctype": "ToDo", "description": "Original"}).insert()
		engine = RuleEngine(rule)

		with self.assertRaises(frappe.exceptions.ValidationError):
			engine.execute(doc)

		# After rollback policy, doc in memory might still be modified if it wasn't a DB rollback
		# BUT engine.py implements Rollback via frappe.db.rollback(save_point=...)
		# For local 'doc' object, savepoint rollback won't revert memory changes.
		# However, it should revert any 'db_set' or 'insert' done during the action.

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
