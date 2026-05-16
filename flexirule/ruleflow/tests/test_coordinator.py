# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Tests for FlexiRule Rule Coordinator
"""

import json
import unittest
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.coordinator import RuleCoordinator
from flexirule.ruleflow.core.engine import RuleEngine


class TestRuleCoordinator(FrappeTestCase):
	"""Test cases for RuleCoordinator"""

	def setUp(self):
		super().setUp()
		# Clean up any existing test rules
		frappe.db.delete("Rule", {"rule_name": ["like", "Test%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "Test%"]})
		RuleCoordinator.clear_cache()

	def tearDown(self):
		super().tearDown()
		# Clean up test rules after each test
		frappe.db.delete("Rule", {"rule_name": ["like", "Test%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "Test%"]})
		RuleCoordinator.clear_cache()

	def create_test_rule(
		self,
		name,
		doctype="ToDo",
		event="Validate",
		is_active=1,
		trigger_condition=None,
		actions=None,
	):
		"""Helper to create test rules"""
		meta = frappe.get_meta(doctype)
		target_field = "description"
		for candidate in ("description", "subject", "title", "method", "error"):
			if meta.get_field(candidate):
				target_field = candidate
				break

		rule_doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": name,
				"document_type": doctype,
				"trigger_type": "DocType Event",
				"trigger_event": event,
				"is_active": is_active,
				"priority": 10,
				"trigger_condition": (json.dumps(trigger_condition) if trigger_condition else None),
				"actions": actions
				or [
					{
						"action_id": "ACT-TEST",
						"action_type": "Assignment",
						"action_label": "Set Description",
						"is_enabled": 1,
						"config": json.dumps(
							[
								{
									"target": f"doc.{target_field}",
									"operator": "set",
									"value_template": "Set by Coordinator",
								}
							]
						),
						"next_step_if_true": "ACT-STOP",
					},
					{
						"action_id": "ACT-STOP",
						"action_type": "Stop",
						"action_label": "Stop",
						"is_enabled": 1,
						"operation": "Success",
					},
				],
			}
		)
		rule_doc.insert(ignore_permissions=True)

		if trigger_condition:
			rule_doc.compile_conditions()
			frappe.db.set_value("Rule", rule_doc.name, "compiled_expression", rule_doc.compiled_expression)

		return rule_doc

	def test_has_active_rules_positive(self):
		"""Test that has_active_rules returns True for active rules"""
		self.create_test_rule("Test Active Rule", event="Validate")

		has_rules = RuleCoordinator.has_active_rules("ToDo", "Validate")
		self.assertTrue(has_rules)

	def test_has_active_rules_negative(self):
		"""Test that has_active_rules returns False for inactive rules"""
		self.create_test_rule("Test Inactive Rule", is_active=0)

		has_rules = RuleCoordinator.has_active_rules("ToDo", "Validate")
		self.assertFalse(has_rules)

	def test_has_active_rules_different_event(self):
		"""Test that has_active_rules returns False for different event"""
		self.create_test_rule("Test Different Event", event="Before Save")

		has_rules = RuleCoordinator.has_active_rules("ToDo", "Validate")
		self.assertFalse(has_rules)

	def test_doctype_runtime_cache_hydrates_all_events_on_first_lookup(self):
		"""Runtime memoization should cache all events per doctype in one load."""
		self.create_test_rule("Test Cache Validate", event="Validate")
		self.create_test_rule("Test Cache Before Save", event="Before Save")

		validate_rules = RuleCoordinator._get_event_runtime("ToDo", "Validate")
		self.assertTrue(validate_rules)

		local_cache = getattr(frappe.local, RuleCoordinator.LOCAL_RUNTIME_KEY, {})
		self.assertIn("ToDo", local_cache)
		self.assertIn("Validate", local_cache["ToDo"])
		self.assertIn("Before Save", local_cache["ToDo"])

	def test_get_applicable_rules(self):
		"""Test getting applicable rules"""
		rule = self.create_test_rule("Test Get Rules", event="Validate")

		rules = RuleCoordinator.get_applicable_rules("ToDo", "Validate")
		self.assertEqual(len(rules), 1)
		self.assertEqual(rules[0].name, rule.name)

	def test_get_applicable_rules_multiple(self):
		"""Test getting multiple applicable rules"""
		rule1 = self.create_test_rule("Test Get Rules 1", event="Validate")
		rule2 = self.create_test_rule("Test Get Rules 2", event="Validate")

		rules = RuleCoordinator.get_applicable_rules("ToDo", "Validate")
		self.assertEqual(len(rules), 2)
		rule_names = [r.name for r in rules]
		self.assertIn(rule1.name, rule_names)
		self.assertIn(rule2.name, rule_names)

	def test_get_applicable_rules_inactive(self):
		"""Test that inactive rules are not returned"""
		self.create_test_rule("Test Inactive Rules", event="Validate", is_active=0)

		rules = RuleCoordinator.get_applicable_rules("ToDo", "Validate")
		self.assertEqual(len(rules), 0)

	def test_check_eligibility_active_rule(self):
		"""Test eligibility check for active rule"""
		rule = self.create_test_rule("Test Eligibility Active")

		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		is_eligible, _reason = RuleCoordinator.check_eligibility(rule, doc, "Validate")
		self.assertTrue(is_eligible)

	def test_check_eligibility_inactive_rule(self):
		"""Test eligibility check for inactive rule"""
		rule = self.create_test_rule("Test Eligibility Inactive", is_active=0)

		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		is_eligible, reason = RuleCoordinator.check_eligibility(rule, doc, "Validate")
		self.assertFalse(is_eligible)
		self.assertIn("not active", reason.lower())

	def test_check_eligibility_wrong_event(self):
		"""Test eligibility check for wrong event"""
		rule = self.create_test_rule("Test Wrong Event", event="Before Save")

		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		is_eligible, reason = RuleCoordinator.check_eligibility(rule, doc, "Validate")
		self.assertFalse(is_eligible)
		self.assertIn("event mismatch", reason.lower())

	def test_check_eligibility_skip_event_check(self):
		"""Test eligibility check with skip_event_check"""
		rule = self.create_test_rule("Test Skip Event", event="Before Save")

		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		is_eligible, _reason = RuleCoordinator.check_eligibility(rule, doc, "Validate", skip_event_check=True)
		self.assertTrue(is_eligible)

	def test_check_eligibility_trigger_condition_true(self):
		"""Test eligibility check with trigger condition that evaluates to True"""
		trigger_condition = [{"left": {"ref": "doc.description"}, "op": "!=", "right": {"value": ""}}]
		rule = self.create_test_rule("Test Cond True", trigger_condition=trigger_condition)

		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		is_eligible, _reason = RuleCoordinator.check_eligibility(rule, doc, "Validate")
		self.assertTrue(is_eligible)

	def test_check_eligibility_trigger_condition_false(self):
		"""Test eligibility check with trigger condition that evaluates to False"""
		trigger_condition = [
			{
				"left": {"ref": "doc.description"},
				"op": "==",
				"right": {"value": "Wrong"},
			}
		]
		rule = self.create_test_rule("Test Cond False", trigger_condition=trigger_condition)

		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		is_eligible, _reason = RuleCoordinator.check_eligibility(rule, doc, "Validate")
		# The condition should fail, so it should be False
		self.assertFalse(is_eligible)
		# The reason might vary, so we'll just check that it's not eligible

	def test_check_eligibility_trigger_condition_context_helpers(self):
		"""Test eligibility check with context helper operators."""
		trigger_condition = [
			{"left": {"ref": "doctype"}, "op": "==", "right": {"value": "ToDo"}},
			{
				"left": {"ref": "rule.document_type"},
				"op": "has_field",
				"right": {"value": "description"},
			},
		]
		rule = self.create_test_rule("Test Cond Context Helpers", trigger_condition=trigger_condition)

		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		is_eligible, _reason = RuleCoordinator.check_eligibility(rule, doc, "Validate")
		self.assertTrue(is_eligible)

	def test_execute_rules_no_applicable(self):
		"""Test execute_rules when no rules are applicable"""
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		RuleCoordinator.execute_rules(doc, "Validate")  # Should not raise an exception

	def test_execute_rules_with_eligible_rule(self):
		"""Test execute_rules with eligible rule"""
		self.create_test_rule("Test Execute Eligible")

		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		RuleCoordinator.execute_rules(doc, "Validate")  # Should execute without error

	def test_execute_rules_failure_logs_once(self):
		"""A failed rule execution should create only one execution log row."""
		rule = self.create_test_rule(
			"Test Execute Fail Once",
			actions=[
				{
					"action_id": "ACT-ERROR",
					"action_type": "Stop",
					"operation": "Error",
					"action_label": "Fail Explicitly",
					"is_enabled": 1,
					"value_template": "Coordinator failure for {{ doc.doctype }}",
				}
			],
		)

		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		with self.assertRaises(frappe.ValidationError):
			RuleCoordinator.execute_rules(doc, "Validate")

		logs = frappe.get_all(
			"Rule Execution Log",
			filters={"rule": rule.name},
			fields=["name", "status"],
		)
		self.assertEqual(len(logs), 1)
		self.assertEqual(logs[0].status, "Failed")

	def test_execute_rules_re_raises_non_validation_errors_for_blocking_events(self):
		rule = self.create_test_rule("Test Blocking Event Error")
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		with mock.patch.object(
			RuleCoordinator,
			"execute_single_rule",
			side_effect=RuntimeError("boom"),
		):
			with self.assertRaises(RuntimeError):
				RuleCoordinator.execute_rules_from_event(doc, rule.trigger_event)

	def test_execute_rules_with_ineligible_rule(self):
		"""Test execute_rules with ineligible rule"""
		trigger_condition = [
			{
				"left": {"ref": "doc.description"},
				"op": "==",
				"right": {"value": "Wrong"},
			}
		]
		self.create_test_rule("Test Execute Ineligible", trigger_condition=trigger_condition)

		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		RuleCoordinator.execute_rules(doc, "Validate")  # Should not execute the rule

	def test_execute_single_rule_sync(self):
		"""Test execute_single_rule in synchronous mode"""
		rule = self.create_test_rule("Test Execute Sync")
		rule.execution_mode = "Synchronous"
		rule.flags.ignore_validate = True
		rule.save(ignore_permissions=True)

		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		RuleCoordinator.execute_single_rule(doc, rule)  # Should execute without error

	def test_execute_single_rule_async(self):
		"""Test execute_single_rule in asynchronous mode"""
		rule = self.create_test_rule("Test Execute Async")
		rule.execution_mode = "Asynchronous"
		rule.flags.ignore_validate = True
		rule.save(ignore_permissions=True)

		# Create a saved document for async execution
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		doc.insert(ignore_permissions=True)

		# This should enqueue the rule for background execution
		RuleCoordinator.execute_single_rule(doc, rule)

	def test_clear_cache(self):
		"""Test clearing rule cache"""
		# Create a rule to test cache clearing
		self.create_test_rule("Test Clear Cache")

		# Access the cache to populate it
		RuleCoordinator.has_active_rules("ToDo", "Validate")

		# Clear cache for specific doctype
		RuleCoordinator.clear_cache("ToDo")

		# The function should not raise an exception
		has_rules = RuleCoordinator.has_active_rules("ToDo", "Validate")
		self.assertTrue(has_rules)

	def test_clear_cache_all(self):
		"""Test clearing all rule cache"""
		# Create a rule to test cache clearing
		self.create_test_rule("Test Clear Cache All")

		# Access the cache to populate it
		RuleCoordinator.has_active_rules("ToDo", "Validate")

		# Clear all cache
		RuleCoordinator.clear_cache()

		# The function should not raise an exception
		has_rules = RuleCoordinator.has_active_rules("ToDo", "Validate")
		self.assertTrue(has_rules)

	def test_execute_rules_import_flag(self):
		"""Test execute_rules respects import flag"""
		self.create_test_rule("Test Import Flag")

		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		# Set import flag
		frappe.flags.in_import = True
		try:
			# This should not execute rules
			RuleCoordinator.execute_rules(doc, "Validate")
		finally:
			frappe.flags.in_import = False

	def test_execute_rules_migrate_flag(self):
		"""Test execute_rules respects migrate flag"""
		self.create_test_rule("Test Migrate Flag")

		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		# Set migrate flag
		frappe.flags.in_migrate = True
		try:
			# This should not execute rules
			RuleCoordinator.execute_rules(doc, "Validate")
		finally:
			frappe.flags.in_migrate = False

	def test_execute_rules_excluded_doctype(self):
		"""Test execute_rules skips excluded doctypes"""
		self.create_test_rule("Test Excluded", doctype="Error Log")

		doc = frappe.get_doc({"doctype": "Error Log", "message": "Test"})
		# This should not execute rules as Error Log is in excluded list
		RuleCoordinator.execute_rules(doc, "Validate")

	def test_execute_rules_debug_mode(self):
		"""Test execute_rules with debug mode"""
		rule = self.create_test_rule("Test Debug Mode")
		rule.debug_mode = 1
		rule.flags.ignore_validate = True
		rule.save(ignore_permissions=True)

		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		# This should execute rules in debug mode
		RuleCoordinator.execute_rules(doc, "Validate")
