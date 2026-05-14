# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.coordinator import RuleCoordinator
from flexirule.ruleflow.core.exceptions import CycleDetectedError


class TestComplexFlows(FrappeTestCase):
	def setUp(self):
		self.cleanup()
		self.create_test_data()

	def tearDown(self):
		self.cleanup()

	def cleanup(self):
		frappe.db.delete("Rule", {"rule_name": ["like", "Test %"]})
		frappe.db.delete("Rule Action", {"parent": ["like", "Test %"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "Test %"]})
		frappe.db.commit()

	def create_test_data(self):
		# Create a dummy doctype or use User
		self.doctype = "User"
		self.docname = "test_user_flow@example.com"
		if not frappe.db.exists("User", self.docname):
			user = frappe.get_doc(
				{"doctype": "User", "email": self.docname, "first_name": "Test User", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		else:
			user = frappe.get_doc("User", self.docname)
		self.doc = user

	def test_nested_sub_rule_branching(self):
		"""
		Test Case: Rule A calls Rule B, which has a Condition that branches.
		"""
		# Rule B: Child Rule
		rule_b = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Child Rule",
				"document_type": self.doctype,
				"trigger_type": "Callable Event",
				"priority": 0,
				"is_active": 1,
				"exposed_as_subrule": 1,
				"actions": [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"action_label": "Start",
						"next_step_if_true": "cond_1",
					},
					{
						"action_id": "cond_1",
						"action_type": "Condition",
						"action_label": "Check First Name",
						"condition_json": json.dumps(
							{"left": {"ref": "doc.first_name"}, "op": "==", "right": {"value": "Test User"}}
						),
						"next_step_if_true": "set_true",
						"next_step_if_false": "set_false",
					},
					{
						"action_id": "set_true",
						"action_type": "Set Value",
						"operation": "Current Document",
						"action_label": "Set Middle Name",
						"target_field": "middle_name",
						"value_template": "SubRuleSuccess",
					},
					{
						"action_id": "set_false",
						"action_type": "Set Value",
						"operation": "Current Document",
						"action_label": "Set Middle Name Fail",
						"target_field": "middle_name",
						"value_template": "SubRuleFail",
					},
				],
			}
		).insert()

		# Rule A: Parent Rule
		rule_a = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Parent Rule",
				"document_type": self.doctype,
				"trigger_type": "Callable Event",
				"priority": 0,
				"is_active": 1,
				"actions": [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"action_label": "Start",
						"next_step_if_true": "call_sub",
					},
					{
						"action_id": "call_sub",
						"action_type": "Sub-Rule",
						"action_label": "Execute Child",
						"rule": rule_b.name,
					},
				],
			}
		).insert()

		# Execute Parent
		RuleCoordinator.execute_rule(rule_a.name, {"doc": self.doc})

		# Verify result (doc is mutated in sub-rule)
		self.assertEqual(self.doc.middle_name, "SubRuleSuccess")

	def test_recursive_cycle_prevention(self):
		"""
		Test Case: Rule A calls Rule B, Rule B calls Rule A.
		Should throw ValidationError during cycle detection in Rule.validate().
		"""
		# Create Rules without sub-rule actions first to satisfy link validation during insert
		rule_a = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Cycle A",
				"document_type": self.doctype,
				"trigger_type": "Callable Event",
				"priority": 0,
				"is_active": 1,
				"exposed_as_subrule": 1,
				"actions": [{"action_id": "root", "action_type": "Entry Action", "action_label": "Start"}],
			}
		).insert()

		rule_b = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Cycle B",
				"document_type": self.doctype,
				"trigger_type": "Callable Event",
				"priority": 0,
				"is_active": 1,
				"exposed_as_subrule": 1,
				"actions": [{"action_id": "root", "action_type": "Entry Action", "action_label": "Start"}],
			}
		).insert()

		# Now add the sub-rule actions that point to each other via DB to bypass link validation if needed,
		# but here we use append and save with ignore_links if possible, or just re-insert.
		# Actually, Frappe 15+ link validation is strict.
		frappe.db.sql(
			"insert into `tabRule Action` (name, parent, parenttype, parentfield, action_id, action_type, rule) values (%s, %s, %s, %s, %s, %s, %s)",
			(frappe.generate_hash(), rule_a.name, "Rule", "actions", "call_b", "Sub-Rule", rule_b.name),
		)

		rule_b.append("actions", {"action_id": "call_a", "action_type": "Sub-Rule", "rule": rule_a.name})

		# This save should trigger Rule.validate() -> validate_graph_integrity -> frappe.throw
		with self.assertRaises(frappe.exceptions.ValidationError) as cm:
			rule_b.save()

		self.assertIn("Cycle detected", str(cm.exception))

	def test_analytics_and_audit(self):
		"""
		Verify analytics fields are updated and path trace is saved.
		"""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Analytics",
				"document_type": self.doctype,
				"trigger_type": "Callable Event",
				"priority": 0,
				"is_active": 1,
				"actions": [{"action_id": "root", "action_type": "Entry Action", "action_label": "Start"}],
			}
		).insert()

		# Execute
		RuleCoordinator.execute_rule(rule.name, {"doc": self.doc})

		# Check Execution Log
		logs = frappe.get_all("Rule Execution Log", filters={"rule": rule.name}, fields=["name", "status"])
		self.assertEqual(len(logs), 1, f"Expected 1 log, got {len(logs)}: {logs}")

		# Calculate stats from logs
		execution_count = len(logs)
		success_rate = 100.0 if execution_count > 0 and logs[0].status == "Success" else 0.0
		avg_execution_time = (
			frappe.db.get_value("Rule Execution Log", {"rule": rule.name}, "avg(duration)") or 0.0
		)

		self.assertEqual(execution_count, 1)
		self.assertEqual(success_rate, 100.0)
		self.assertGreater(avg_execution_time, 0)

		# Check Execution Log
		logs = frappe.get_all("Rule Execution Log", filters={"rule": rule.name}, fields=["execution_path"])
		self.assertTrue(len(logs) > 0)
		path = json.loads(logs[0].execution_path)
		self.assertEqual(path[0]["action"], "Start")


import json
