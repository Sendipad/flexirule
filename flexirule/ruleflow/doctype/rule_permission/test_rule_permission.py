# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.engine import RuleEngine


class TestRulePermission(FrappeTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.rule_name = "Test Permission Rule"
		if frappe.db.exists("Rule", self.rule_name):
			frappe.delete_doc("Rule", self.rule_name)

		self.rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": self.rule_name,
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
						"next_step_if_true": "node_end",
					},
					{
						"action_id": "node_end",
						"action_type": "Stop",
						"action_label": "End",
						"operation": "Success",
						"is_enabled": 1,
					},
				],
				"permissions": [
					{"role": "System Manager", "can_execute": 1},
					{"role": "Guest", "can_execute": 0},
				],
			}
		)
		self.rule.flags.ignore_permissions = True
		self.rule.insert()

	def test_permission_bypass_for_system_manager(self):
		"""Verify System Manager can execute rules even if not explicitly listed"""
		frappe.set_user("Administrator")
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		engine = RuleEngine(self.rule)
		# Should not throw PermissionError
		engine.execute(doc)

	def test_permission_enforcement_for_regular_user(self):
		"""Verify that a user without listed role cannot execute the rule"""
		# Create a temporary user with a specific role
		user_email = "test_perm@example.com"
		if not frappe.db.exists("User", user_email):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user_email,
					"first_name": "Test Perm",
					"roles": [{"role": "Blogger"}],
				}
			).insert(ignore_permissions=True)

		frappe.set_user(user_email)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		engine = RuleEngine(self.rule)

		with self.assertRaises(frappe.PermissionError):
			engine.execute(doc)

	def test_explicit_denial(self):
		"""Verify that explicitly listed role with can_execute=0 is blocked"""
		frappe.set_user("Guest")
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		engine = RuleEngine(self.rule)

		with self.assertRaises(frappe.PermissionError):
			engine.execute(doc)
