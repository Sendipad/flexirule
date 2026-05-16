import json
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.coordinator import RuleCoordinator


class TestExecutionAPI(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")

	def test_pure_execute_rule(self):
		"""Test RuleCoordinator.execute_rule directly"""
		# Create a rule
		rule_name = "Test Pure Execute"
		if frappe.db.exists("Rule", rule_name):
			frappe.delete_doc("Rule", rule_name)

		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": rule_name,
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"actions": [
					{
						"action_id": "set_desc",
						"action_type": "Assignment",
						"config": '[{"target": "doc.description", "operator": "set", "value_template": "Set by API"}]',
						"action_label": "Set Description",
						"is_enabled": 1,
					}
				],
			}
		).insert()

		todo = frappe.get_doc({"doctype": "ToDo", "description": "Original"})

		# Execute without dry run
		context = {"doc": todo}
		RuleCoordinator.execute_rule(rule.name, context, dry_run=False)

		self.assertEqual(todo.description, "Set by API")
		log = frappe.get_all(
			"Rule Execution Log",
			filters={"rule": rule.name},
			fields=["rule_version", "trigger_source"],
			order_by="creation desc",
			limit=1,
		)[0]
		self.assertEqual(log.rule_version, rule.version)
		self.assertIn("Doc Event: ToDo/", log.trigger_source)

	def test_dry_run_execute_rule(self):
		"""Test RuleCoordinator.execute_rule with dry_run=True"""
		rule_name = "Test Dry Run"
		if frappe.db.exists("Rule", rule_name):
			frappe.delete_doc("Rule", rule_name)

		# We need a document that exists in DB to verify rollback of DB changes
		todo = frappe.get_doc({"doctype": "ToDo", "description": "Original"}).insert()
		todo_name = todo.name

		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": rule_name,
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"actions": [
					{
						"action_id": "set_desc",
						"action_type": "Assignment",
						"config": '[{"target": "doc.description", "operator": "set", "value_template": "Should not persist"}]',
						"action_label": "Set Description",
						"is_enabled": 1,
					}
				],
			}
		).insert()

		# Execute with dry run
		# We'll use a native action that changes the document and verify it does not persist in DB
		context = {"doc": todo}
		RuleCoordinator.execute_rule(rule.name, context, dry_run=True)

		# In-memory object might still be changed (since it's not deep-copied),
		# but DB should NOT have the change.

		frappe.clear_cache(doctype="ToDo")
		todo_from_db = frappe.get_doc("ToDo", todo_name)
		self.assertEqual(todo_from_db.description, "Original")

	def test_execute_rule_api_serialization(self):
		"""Test flexirule.ruleflow.api.execute_rule for JSON serialization safety"""
		from flexirule.ruleflow.api import execute_rule

		rule_name = "Test Serialization"
		if frappe.db.exists("Rule", rule_name):
			frappe.delete_doc("Rule", rule_name)

		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": rule_name,
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"actions": [
					{
						"action_id": "set_desc",
						"action_type": "Assignment",
						"config": '[{"target": "doc.description", "operator": "set", "value_template": "API Test"}]',
						"action_label": "Set Description",
						"is_enabled": 1,
					}
				],
			}
		).insert()

		todo = frappe.get_doc({"doctype": "ToDo", "description": "Original"}).insert()

		# Call the whitelisted API directly
		response = execute_rule(
			rule.name,
			context={"doc": {"doctype": "ToDo", "name": todo.name}},
			dry_run=True,
		)

		self.assertTrue(response.get("success"))
		context = response.get("context")

		# Verify non-serializable objects are removed
		self.assertNotIn("frappe", context)
		self.assertNotIn("doc", context)
		self.assertNotIn("old_doc", context)

		# Verify it can be dumped to JSON
		try:
			json.dumps(response)
		except TypeError as e:
			self.fail(f"API response is not JSON serializable: {e}")
