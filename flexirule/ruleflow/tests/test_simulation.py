# Copyright (c) 2026, FlexiRule and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from flexirule.ruleflow.core.engine import RuleEngine
from flexirule.ruleflow.core.coordinator import RuleCoordinator

class TestSimulation(FrappeTestCase):
	def setUp(self):
		self.cleanup_entities()

		# Create a test role
		self.test_role = "FlexiRule Test Role"
		if not frappe.db.exists("Role", self.test_role):
			frappe.get_doc({
				"doctype": "Role",
				"role_name": self.test_role
			}).insert(ignore_permissions=True)

		# Create a test user
		self.test_user_email = "test_sim_user@example.com"
		if not frappe.db.exists("User", self.test_user_email):
			user = frappe.get_doc({
				"doctype": "User",
				"email": self.test_user_email,
				"first_name": "Sim User",
				"send_welcome_email": 0
			})
			user.insert(ignore_permissions=True)
			user.add_roles(self.test_role)

		# Create a mock rule
		self.rule_name = "Test Simulation Rule"
		self.rule = frappe.get_doc({
			"doctype": "Rule",
			"rule_name": self.rule_name,
			"document_type": "ToDo",
			"trigger_type": "DocType Event",
			"trigger_event": "Before Save",
			"is_active": 1,
			"actions": [
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"next_step_if_true": "assign_1"
				},
				{
					"action_id": "assign_1",
					"action_label": "Record Context",
					"action_type": "Assignment",
					"config": [
						{
							"target": "vars.actual_user",
							"operator": "set",
							"value": {"mode": "formula", "expression": "frappe.session.user"}
						},
						{
							"target": "vars.actual_roles",
							"operator": "set",
							"value": {"mode": "formula", "expression": "frappe.get_roles()"}
						}
					]
				}
			]
		}).insert(ignore_permissions=True)

		# Create a ToDo for testing
		self.todo = frappe.get_doc({
			"doctype": "ToDo",
			"description": "Simulation Test ToDo"
		}).insert(ignore_permissions=True)

	def tearDown(self):
		self.cleanup_entities()
		frappe.db.rollback()

	def cleanup_entities(self):
		# Cleanup ToDos
		frappe.db.delete("ToDo", {"description": "Simulation Test ToDo"})
		# Cleanup Rule
		frappe.db.delete("Rule", {"rule_name": "Test Simulation Rule"})
		# Cleanup User
		frappe.db.delete("User", {"email": "test_sim_user@example.com"})
		# Cleanup Role
		frappe.db.delete("Role", {"role_name": "FlexiRule Test Role"})

	def test_valid_sim_user_override(self):
		"""Verify the rule engine switches context to an active target user."""
		context = {
			"sim_user": self.test_user_email,
			"doc": self.todo
		}
		result = RuleCoordinator.execute_rule(self.rule.name, context=context)
		self.assertEqual(result["vars"]["actual_user"], self.test_user_email)

	def test_valid_sim_role_override(self):
		"""Verify a specific role is successfully injected into the user context."""
		context = {
			"sim_role": self.test_role,
			"doc": self.todo
		}
		result = RuleCoordinator.execute_rule(self.rule.name, context=context)
		# SafeFrappeAPI for sim_role returns [sim_role]
		self.assertIn(self.test_role, result["vars"]["actual_roles"])

	def test_null_simulation_parameters(self):
		"""Verify that passing None defaults safely back to frappe.session.user."""
		original_user = frappe.session.user
		context = {
			"sim_user": None,
			"sim_role": "",
			"doc": self.todo
		}
		result = RuleCoordinator.execute_rule(self.rule.name, context=context)
		self.assertEqual(result["vars"]["actual_user"], original_user)

	def test_non_existent_sim_user(self):
		"""Verify behavior with non-existent user (current implementation behavior)."""
		# Audit revealed SafeFrappeAPI just takes the string.
		# If user doesn't exist, frappe.get_roles(non_existent) usually returns ["Guest"] or throws if not handled.
		# We document what actually happens.
		invalid_user = "ghost_user_999@example.com"
		context = {
			"sim_user": invalid_user,
			"doc": self.todo
		}
		result = RuleCoordinator.execute_rule(self.rule.name, context=context)
		self.assertEqual(result["vars"]["actual_user"], invalid_user)

	def test_non_existent_sim_role(self):
		"""Verify behavior when a fake role string is simulated."""
		invalid_role = "Non Existent Super Role"
		context = {
			"sim_role": invalid_role,
			"doc": self.todo
		}
		result = RuleCoordinator.execute_rule(self.rule.name, context=context)
		self.assertIn(invalid_role, result["vars"]["actual_roles"])
		self.assertEqual(len(result["vars"]["actual_roles"]), 1)

	def test_sim_role_restriction(self):
		"""Verify the engine isolates execution *only* to that single role context."""
		# Even if Administrator has many roles, sim_role should restrict to only that one.
		context = {
			"sim_user": "Administrator",
			"sim_role": "Guest",
			"doc": self.todo
		}
		result = RuleCoordinator.execute_rule(self.rule.name, context=context)
		self.assertEqual(result["vars"]["actual_roles"], ["Guest"])

	def test_simulation_context_isolation(self):
		"""Verify that simulation context does not leak into the real session."""
		original_user = frappe.session.user
		original_roles = frappe.get_roles()

		context = {
			"sim_user": self.test_user_email,
			"sim_role": self.test_role,
			"doc": self.todo
		}
		RuleCoordinator.execute_rule(self.rule.name, context=context)

		# Verify global state is untouched
		self.assertEqual(frappe.session.user, original_user)
		self.assertEqual(frappe.get_roles(), original_roles)

	def test_session_restoration_on_exception(self):
		"""Verify session restoration (isolation) even when an exception occurs."""
		original_user = frappe.session.user

		# Create a rule that crashes
		crash_rule = frappe.get_doc({
			"doctype": "Rule",
			"rule_name": "Crash Rule",
			"document_type": "ToDo",
			"trigger_type": "DocType Event",
			"trigger_event": "Before Save",
			"is_active": 1,
			"actions": [
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"next_step_if_true": "stop_err"
				},
				{
					"action_id": "stop_err",
					"action_type": "Stop",
					"operation": "Error",
					"value_template": "Intentional Crash"
				}
			]
		}).insert(ignore_permissions=True)

		context = {
			"sim_user": self.test_user_email,
			"doc": self.todo
		}

		try:
			from flexirule.ruleflow.core.exceptions import MethodExecutionError
			# In RuleEngine, a Stop Error raises MethodExecutionError or ValidationError depending on context
			# But coordinator.execute_rule calls engine.execute which raises.
			with self.assertRaises(Exception):
				RuleCoordinator.execute_rule(crash_rule.name, context=context)
		finally:
			# Verify global state is still intact
			self.assertEqual(frappe.session.user, original_user)
			frappe.db.delete("Rule", {"rule_name": "Crash Rule"})
