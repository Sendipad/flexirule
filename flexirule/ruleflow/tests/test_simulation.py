# Copyright (c) 2026, FlexiRule and Contributors
# See license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.coordinator import RuleCoordinator


class TestSimulation(FrappeTestCase):
	def setUp(self):
		super().setUp()

		# Establish a known global state
		frappe.set_user("Administrator")

		# Use unique suffixes for every run to avoid LinkExistsError and collisions
		self.suffix = frappe.generate_hash(length=8)
		self.test_role = f"Role {self.suffix}"
		self.test_user_email = f"user_{self.suffix}@example.com"
		self.rule_name = f"Rule {self.suffix}"

		# 1. Ensure test role exists
		if not frappe.db.exists("Role", self.test_role):
			frappe.get_doc({"doctype": "Role", "role_name": self.test_role}).insert(ignore_permissions=True)

		# 2. Ensure test user exists with the role
		if not frappe.db.exists("User", self.test_user_email):
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": self.test_user_email,
					"first_name": "Simulation",
					"last_name": "Test User",
					"send_welcome_email": 0,
				}
			)
			user.insert(ignore_permissions=True)
			user.add_roles(self.test_role)
			user.reload()

		# 3. Create a mock rule that captures session context into variables
		# Use { expression } to ensure raw object evaluation (e.g. Roles list)
		self.rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": self.rule_name,
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Manual Test",  # Avoid firing on standard inserts
				"execution_mode": "Synchronous",
				"is_active": 1,
				"actions": [
					{
						"action_id": "root",
						"action_label": "Start",
						"action_type": "Entry Action",
						"next_step_if_true": "capture",
					},
					{
						"action_id": "capture",
						"action_label": "Capture Context",
						"action_type": "Assignment",
						"config": json.dumps(
							[
								{
									"target": "vars.actual_user",
									"operator": "set",
									"value": "{frappe.session.user}",
								},
								{
									"target": "vars.actual_roles",
									"operator": "set",
									"value": "{frappe.get_roles()}",
								},
							]
						),
					},
				],
			}
		).insert(ignore_permissions=True)

		# 4. Create a ToDo for testing
		self.todo = frappe.get_doc(
			{"doctype": "ToDo", "description": f"Simulation Task {self.suffix}"}
		).insert(ignore_permissions=True)

		# Clear caches to ensure isolation
		RuleCoordinator.clear_cache()

	def test_valid_sim_user_override(self):
		"""Verify the rule engine switches context to an active target user."""
		context = {"sim_user": self.test_user_email, "doc": self.todo, "skip_log_enqueue": True}
		result = RuleCoordinator.execute_rule(self.rule.name, context=context)
		self.assertEqual(result["vars"]["actual_user"], self.test_user_email)

	def test_valid_sim_role_override(self):
		"""Verify a specific role is successfully injected into the user context."""
		context = {"sim_role": self.test_role, "doc": self.todo, "skip_log_enqueue": True}
		result = RuleCoordinator.execute_rule(self.rule.name, context=context)
		# SafeFrappeAPI for sim_role returns [sim_role]
		actual_roles = result["vars"]["actual_roles"]
		self.assertIn(self.test_role, actual_roles)

	def test_null_simulation_parameters(self):
		"""Verify that passing None defaults safely back to frappe.session.user."""
		original_user = frappe.session.user
		context = {"sim_user": None, "sim_role": "", "doc": self.todo, "skip_log_enqueue": True}
		result = RuleCoordinator.execute_rule(self.rule.name, context=context)
		self.assertEqual(result["vars"]["actual_user"], original_user)

	def test_non_existent_sim_user(self):
		"""Verify behavior with non-existent user ID."""
		invalid_user = "ghost_user_999@example.com"
		context = {"sim_user": invalid_user, "doc": self.todo, "skip_log_enqueue": True}
		result = RuleCoordinator.execute_rule(self.rule.name, context=context)
		# Engine implementation returns string passthrough in SafeFrappeAPI
		self.assertEqual(result["vars"]["actual_user"], invalid_user)

	def test_non_existent_sim_role(self):
		"""Verify behavior when a fake role string is simulated."""
		invalid_role = "Non Existent Super Role"
		context = {"sim_role": invalid_role, "doc": self.todo, "skip_log_enqueue": True}
		result = RuleCoordinator.execute_rule(self.rule.name, context=context)
		self.assertEqual(result["vars"]["actual_roles"], [invalid_role])

	def test_sim_role_restriction(self):
		"""Verify the engine isolates execution *only* to that single role context."""
		context = {
			"sim_user": "Administrator",
			"sim_role": "Guest",
			"doc": self.todo,
			"skip_log_enqueue": True,
		}
		result = RuleCoordinator.execute_rule(self.rule.name, context=context)
		self.assertEqual(result["vars"]["actual_roles"], ["Guest"])

	def test_simulation_global_isolation(self):
		"""Verify that simulation context does not leak into the global frappe.session."""
		original_user = frappe.session.user
		original_roles = frappe.get_roles()

		context = {
			"sim_user": self.test_user_email,
			"sim_role": self.test_role,
			"doc": self.todo,
			"skip_log_enqueue": True,
		}
		RuleCoordinator.execute_rule(self.rule.name, context=context)

		# Verify global state is untouched after execution
		self.assertEqual(frappe.session.user, original_user)
		self.assertEqual(frappe.get_roles(), original_roles)

	def test_simulation_context_does_not_affect_subsequent_execution(self):
		"""Verify simulation context does not affect subsequent rule evaluations."""
		original_user = frappe.session.user

		# 1. Run with simulation
		context = {"sim_user": self.test_user_email, "doc": self.todo, "skip_log_enqueue": True}
		RuleCoordinator.execute_rule(self.rule.name, context=context)

		# 2. Run without simulation
		context_normal = {"doc": self.todo, "skip_log_enqueue": True}
		result = RuleCoordinator.execute_rule(self.rule.name, context=context_normal)

		# Should revert to session user
		self.assertEqual(result["vars"]["actual_user"], original_user)

	def test_session_restoration_on_exception(self):
		"""Verify session restoration even when an engine exception occurs."""
		original_user = frappe.session.user
		original_roles = frappe.get_roles()

		# Create a unique rule that explicitly throws an error using Raise Error action
		crash_rule_name = f"Crash Rule {self.suffix}"
		crash_rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": crash_rule_name,
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Manual Test",
				"execution_mode": "Synchronous",
				"is_active": 1,
				"actions": [
					{
						"action_id": "root",
						"action_label": "Start",
						"action_type": "Entry Action",
						"next_step_if_true": "fail",
					},
					{
						"action_id": "fail",
						"action_label": "Intentional Failure",
						"action_type": "Raise Error",
						"value_template": "Intentional Crash",
					},
				],
			}
		).insert(ignore_permissions=True)

		context = {"sim_user": self.test_user_email, "doc": self.todo, "skip_log_enqueue": True}

		try:
			with self.assertRaises(Exception):
				RuleCoordinator.execute_rule(crash_rule.name, context=context)
		finally:
			# Verify global state remains intact
			self.assertEqual(frappe.session.user, original_user)
			self.assertEqual(frappe.get_roles(), original_roles)
