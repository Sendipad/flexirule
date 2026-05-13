# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Integration tests for FlexiRule API endpoints
"""

import json
import unittest

import frappe
from frappe.exceptions import PermissionError

from flexirule.ruleflow.core.coordinator import RuleCoordinator


class TestBoltonAPI(unittest.TestCase):
	"""Test API endpoints"""

	def setUp(self):
		"""Setup test data"""
		frappe.set_user("Administrator")

		# Create test rule using new Process architecture
		if not frappe.db.exists("Rule", "Test API Rule"):
			self.rule = frappe.get_doc(
				{
					"doctype": "Rule",
					"rule_name": "Test API Rule",
					"document_type": "ToDo",
					"trigger_type": "DocType Event",
					"trigger_event": "Validate",
					"is_active": 1,
					"actions": [
						{
							"action_type": "Set Value",
							"operation": "Current Document",
							"action_label": "Set Priority",
							"action_id": "action_1",
							"target_field": "priority",
							"value_template": "Medium",
							"is_entry_action": 1,
							"next_step_if_true": "action_stop",
						},
						{
							"action_type": "Stop",
							"operation": "Success",
							"action_label": "Stop",
							"action_id": "action_stop",
						},
					],
				}
			)
			self.rule.insert(ignore_permissions=True)
		else:
			self.rule = frappe.get_doc("Rule", "Test API Rule")

	def tearDown(self):
		"""Cleanup"""
		frappe.db.rollback()
		# Clean up cache to prevent DoNotExistError in other tests
		RuleCoordinator.clear_cache("ToDo")

	def test_get_doctype_fields(self):
		"""Test getting DocType fields"""
		from flexirule.ruleflow.api import get_doctype_fields

		result = get_doctype_fields("ToDo")

		self.assertIsInstance(result, dict)
		self.assertIn("parent_fields", result)

	def test_get_doctype_fields_with_filters(self):
		"""Test getting DocType fields with filters"""
		from flexirule.ruleflow.api import get_doctype_fields

		filters = json.dumps({"fieldtypes": ["Data", "Select"]})
		result = get_doctype_fields("ToDo", filters)

		self.assertIsInstance(result, dict)

	def test_test_rule(self):
		"""Test rule testing API"""
		from flexirule.ruleflow.api import test_rule

		# Create a test TODO
		todo = frappe.get_doc({"doctype": "ToDo", "description": "Test for API"})
		todo.insert(ignore_permissions=True)

		result = test_rule(self.rule.name, "ToDo", todo.name)

		self.assertIn("success", result)

	def test_test_rule_allows_inactive_draft_pre_activation(self):
		"""Rule testing should work before activation."""
		from flexirule.ruleflow.api import test_rule

		self.rule.is_active = 0
		self.rule.save(ignore_permissions=True)
		RuleCoordinator.clear_cache("ToDo")

		todo = frappe.get_doc({"doctype": "ToDo", "description": "Inactive test"})
		todo.insert(ignore_permissions=True)

		result = test_rule(self.rule.name, "ToDo", todo.name, dry_run=True, skip_log_enqueue=True)
		self.assertTrue(result.get("success"))

	def test_clear_cache(self):
		"""Test cache clearing API"""
		from flexirule.ruleflow.api import clear_cache

		result = clear_cache("ToDo")

		self.assertTrue(result.get("success"))

	def test_get_process_operations_returns_normalized_dto(self):
		"""Process operations API should return normalized records."""
		from flexirule.ruleflow.api import get_process_operations

		result = get_process_operations("Enrichment")

		self.assertIsInstance(result, list)
		if result:
			row = result[0]
			self.assertIn("value", row)
			self.assertIn("func_name", row)
			self.assertIn("label", row)
			self.assertIn("adapter_key", row)
			self.assertIn("capabilities", row)
			self.assertIn("policy", row)

	def test_transition_rule_uses_v15_cache_clear_signature(self):
		"""Lifecycle transition should not call frappe.clear_cache with unsupported kwargs."""
		from flexirule.ruleflow.api import transition_rule

		result = transition_rule(self.rule.name, "Draft")

		self.assertEqual(result.get("status"), "Draft")
		self.assertEqual(result.get("is_active"), 0)
		refreshed = frappe.get_doc("Rule", self.rule.name)
		self.assertEqual(refreshed.status, "Draft")
		self.assertEqual(refreshed.is_active, 0)


class TestAPIPermissions(unittest.TestCase):
	"""Test API permission enforcement"""

	def setUp(self):
		"""Setup"""
		frappe.set_user("Administrator")

	def tearDown(self):
		"""Cleanup"""
		frappe.set_user("Administrator")
		frappe.db.rollback()

	def test_api_requires_builder_access(self):
		"""Sensitive metadata APIs should require builder/admin access."""
		from flexirule.ruleflow.api import get_doctype_fields

		frappe.set_user("Guest")
		with self.assertRaises(PermissionError):
			get_doctype_fields("ToDo")


def run_tests():
	"""Helper function to run all API tests"""
	suite = unittest.TestSuite()
	suite.addTest(unittest.makeSuite(TestBoltonAPI))
	suite.addTest(unittest.makeSuite(TestAPIPermissions))
	runner = unittest.TextTestRunner()
	runner.run(suite)


if __name__ == "__main__":
	unittest.main()
