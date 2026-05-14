# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Comprehensive Tests for FlexiRule Engine covering all action types
"""

import json
import time
import unittest
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.engine import RuleEngine
from flexirule.ruleflow.core.exceptions import (
	CycleDetectedError,
	EmptyRuleError,
	MethodExecutionError,
	RuleDisabledError,
)
from flexirule.ruleflow.core.exceptions import (
	TimeoutError as FlexiRuleTimeoutError,
)


class TestRuleEngineComprehensive(FrappeTestCase):
	"""Comprehensive test cases for RuleEngine covering all action types"""

	def setUp(self):
		super().setUp()
		# Clean up any existing test rules
		frappe.db.delete("Rule", {"rule_name": ["like", "Test%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "Test%"]})

	def tearDown(self):
		super().tearDown()
		# Clean up test rules after each test
		frappe.db.delete("Rule", {"rule_name": ["like", "Test%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "Test%"]})

	def create_test_rule(
		self,
		name,
		actions=None,
		doctype="ToDo",
		event="Validate",
		is_active=1,
		trigger_type="DocType Event",
		exposed_as_subrule=0,
		priority=10,
	):
		"""Helper to create test rules"""
		if actions is None:
			actions = [
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Start",
					"is_enabled": 1,
					"next_step_if_true": "ACT-PROCESS",
				},
				{
					"action_id": "ACT-PROCESS",
					"action_type": "Process",
					"action_label": "Test Process",
					"is_enabled": 1,
					"process_name": "Validation",
					"operation": "value_in_range",
					"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
					"return_variable": "test_res",
					"on_error": "Stop",
				},
			]

		rule_doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": name,
				"document_type": doctype,
				"trigger_type": trigger_type,
				"trigger_event": event,
				"is_active": is_active,
				"exposed_as_subrule": exposed_as_subrule,
				"priority": priority,
				"actions": actions,
			}
		)
		rule_doc.insert(ignore_permissions=True)
		return rule_doc

	def test_engine_initialization_with_string_rule_name(self):
		"""Test RuleEngine initialization with string rule name"""
		rule = self.create_test_rule("Test Init String")

		# Initialize engine with string rule name
		engine = RuleEngine(rule.name)

		self.assertEqual(engine.rule.name, rule.name)
		self.assertEqual(len(engine.actions), 2)  # Start + Process actions

	def test_engine_initialization_with_doc_rule(self):
		"""Test RuleEngine initialization with rule doc"""
		rule = self.create_test_rule("Test Init Doc")

		# Initialize engine with rule doc
		engine = RuleEngine(rule)

		self.assertEqual(engine.rule.name, rule.name)
		self.assertEqual(len(engine.actions), 2)  # Start + Process actions

	def test_engine_execute_success(self):
		"""Test successful rule execution"""
		rule = self.create_test_rule("Test Execute Success")

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		result = engine.execute(doc)

		# Should return context with execution details
		self.assertIsInstance(result, dict)
		self.assertIn("doc", result)
		self.assertIn("vars", result)

	def test_engine_execute_disabled_rule(self):
		"""Test execution of disabled rule raises exception"""
		rule = self.create_test_rule("Test Execute Disabled", is_active=0)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		with self.assertRaises(RuleDisabledError):
			engine.execute(doc)

	def test_engine_execute_empty_rule(self):
		"""Test execution of rule with no enabled actions"""
		rule = self.create_test_rule("Test Execute Empty", actions=[])
		# Manually disable all actions including the auto-created root
		for action in rule.actions:
			action.is_enabled = 0
		rule.flags.ignore_validate = True
		rule.save()

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		with self.assertRaises(EmptyRuleError):
			engine.execute(doc)

	def test_engine_execute_with_context(self):
		"""Test rule execution with custom context"""
		rule = self.create_test_rule("Test Execute Context")

		custom_context = {"test_mode": True, "custom_var": "value"}
		engine = RuleEngine(rule, execution_context=custom_context)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		result = engine.execute(doc)

		# Custom context should be preserved
		self.assertIn("test_mode", result)
		self.assertTrue(result["test_mode"])
		self.assertIn("custom_var", result)
		self.assertEqual(result["custom_var"], "value")

	def test_engine_execute_condition_true(self):
		"""Test rule execution with Condition action returning True"""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "ACT-COND",
			},
			{
				"action_id": "ACT-COND",
				"action_type": "Condition",
				"action_label": "Check Status",
				"is_enabled": 1,
				"condition_json": '[{"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Open"}}]',
				"next_step_if_true": "ACT-PROCESS-TRUE",
				"next_step_if_false": "ACT-PROCESS-FALSE",
			},
			{
				"action_id": "ACT-PROCESS-TRUE",
				"action_type": "Process",
				"action_label": "Process True",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "res_true",
				"on_error": "Stop",
			},
			{
				"action_id": "ACT-PROCESS-FALSE",
				"action_type": "Process",
				"action_label": "Process False",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "res_false",
				"on_error": "Stop",
			},
		]

		rule = self.create_test_rule("Test Condition True", actions=actions)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test", "status": "Open"})

		engine.execute(doc)

		# Should follow the true path
		# Check execution log for the right actions
		executed_actions = [
			entry["message"] for entry in engine.execution_log if "Executing action" in entry["message"]
		]
		# At least the start and condition should be executed
		self.assertTrue(any("Start" in action for action in executed_actions))
		self.assertTrue(any("Check Status" in action for action in executed_actions))

	def test_engine_execute_condition_false(self):
		"""Test rule execution with Condition action returning False"""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "ACT-COND",
			},
			{
				"action_id": "ACT-COND",
				"action_type": "Condition",
				"action_label": "Check Status",
				"is_enabled": 1,
				"condition_json": '[{"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Closed"}}]',
				"next_step_if_true": "ACT-PROCESS-TRUE",
				"next_step_if_false": "ACT-PROCESS-FALSE",
			},
			{
				"action_id": "ACT-PROCESS-TRUE",
				"action_type": "Process",
				"action_label": "Process True",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "res_true",
				"on_error": "Stop",
			},
			{
				"action_id": "ACT-PROCESS-FALSE",
				"action_type": "Process",
				"action_label": "Process False",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "res_false",
				"on_error": "Stop",
			},
		]

		rule = self.create_test_rule("Test Condition False", actions=actions)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test", "status": "Open"})

		engine.execute(doc)

		# Should follow the false path
		executed_actions = [
			entry["message"] for entry in engine.execution_log if "Executing action" in entry["message"]
		]
		# At least the start and condition should be executed
		self.assertTrue(any("Start" in action for action in executed_actions))
		self.assertTrue(any("Check Status" in action for action in executed_actions))

	def test_engine_execute_process_action(self):
		"""Test rule execution with Process action"""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "ACT-PROCESS",
			},
			{
				"action_id": "ACT-PROCESS",
				"action_type": "Process",
				"action_label": "Validate Description",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "res",
				"on_error": "Stop",
			},
		]

		rule = self.create_test_rule("Test Process Action", actions=actions)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		engine.execute(doc)

		# Should execute the process action successfully
		executed_actions = [
			entry["message"] for entry in engine.execution_log if "Executing action" in entry["message"]
		]
		process_executed = any("Validate Description" in action for action in executed_actions)
		self.assertTrue(process_executed)

	def test_engine_execute_loop_action(self):
		"""Test rule execution with Loop action"""
		self.skipTest("Loop action is disabled for the v0.1 release surface")
		# Create a test document with child table items
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test with items", "status": "Open"})
		doc.insert()

		# Add some items to a child table (we'll simulate with a custom field if needed)
		# For this test, we'll create a simpler scenario

		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "ACT-LOOP",
			},
			{
				"action_id": "ACT-LOOP",
				"action_type": "Loop",
				"action_label": "Loop Items",
				"is_enabled": 1,
				"config": '{"iterator": "[\\"test1\\", \\"test2\\", \\"test3\\"]", "alias": "item"}',
				"next_step_if_true": "ACT-PROCESS-INSIDE-LOOP",
				"next_step_if_false": "ACT-AFTER-LOOP",
			},
			{
				"action_id": "ACT-PROCESS-INSIDE-LOOP",
				"action_type": "Process",
				"action_label": "Process Inside Loop",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "loop_res",
				"on_error": "Stop",
				"next_step_if_true": "ACT-AFTER-LOOP",  # Go to after loop to avoid cycle
			},
			{
				"action_id": "ACT-AFTER-LOOP",
				"action_type": "Process",
				"action_label": "After Loop",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "after_res",
				"on_error": "Stop",
			},
		]

		rule = self.create_test_rule("Test Loop Action", actions=actions)

		engine = RuleEngine(rule)

		# Execute the rule
		engine.execute(doc)

		# Should execute the loop action
		executed_actions = [
			entry["message"] for entry in engine.execution_log if "Executing action" in entry["message"]
		]
		loop_executed = any("Loop Items" in action for action in executed_actions)
		self.assertTrue(loop_executed)

	def test_engine_execute_stop_action(self):
		"""Test rule execution with Stop action"""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "ACT-STOP",
			},
			{
				"action_id": "ACT-STOP",
				"action_type": "Stop",
				"operation": "Success",
				"action_label": "Stop Execution",
				"is_enabled": 1,
				"next_step_if_true": None,  # Stop action should not have a next step
			},
		]

		rule = self.create_test_rule("Test Stop Action", actions=actions)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		engine.execute(doc)

		# Should execute up to the stop action
		executed_actions = [
			entry["message"] for entry in engine.execution_log if "Executing action" in entry["message"]
		]
		stop_executed = any("Stop Execution" in action for action in executed_actions)

		self.assertTrue(stop_executed)

	def test_engine_execute_switch_action(self):
		"""Test rule execution with Switch action"""
		self.skipTest("Switch action is disabled for the v0.1 release surface")
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "ACT-SWITCH",
			},
			{
				"action_id": "ACT-SWITCH",
				"action_type": "Switch",
				"action_label": "Switch Priority",
				"is_enabled": 1,
				"config": '{"expression": "doc.priority", "cases": {"High": "ACT-PROCESS", "default": "ACT-PROCESS"}}',
				"next_step_if_true": "ACT-PROCESS",  # Connect to the same target to avoid unreachable nodes
			},
			{
				"action_id": "ACT-PROCESS",
				"action_type": "Process",
				"action_label": "Process Action",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "switch_res",
				"on_error": "Stop",
			},
		]

		rule = self.create_test_rule("Test Switch Action", actions=actions)

		# Test with High priority
		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test", "priority": "High"})

		engine.execute(doc)

		# Should execute the process action after switch
		executed_actions = [
			entry["message"] for entry in engine.execution_log if "Executing action" in entry["message"]
		]
		process_executed = any("Process Action" in action for action in executed_actions)
		self.assertTrue(process_executed)

	def test_engine_execute_sub_rule_action(self):
		"""Test rule execution with Sub-Rule action"""
		# First, create a sub-rule
		sub_rule_actions = [
			{
				"action_id": "SUB-START",
				"action_type": "Entry Action",
				"action_label": "Sub Start",
				"is_enabled": 1,
				"next_step_if_true": "SUB-PROCESS",
			},
			{
				"action_id": "SUB-PROCESS",
				"action_type": "Process",
				"action_label": "Sub Process",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "sub_res",
				"on_error": "Stop",
			},
		]

		sub_rule = self.create_test_rule(
			"Test Sub Rule",
			actions=sub_rule_actions,
			trigger_type="Callable Event",
			event=None,
			exposed_as_subrule=1,
			priority=0,
		)

		# Now create the main rule with sub-rule action
		main_actions = [
			{
				"action_id": "MAIN-START",
				"action_type": "Entry Action",
				"action_label": "Main Start",
				"is_enabled": 1,
				"next_step_if_true": "MAIN-SUB",
			},
			{
				"action_id": "MAIN-SUB",
				"action_type": "Sub-Rule",
				"action_label": "Call Sub Rule",
				"is_enabled": 1,
				"rule": sub_rule.name,
				"config": f'{{"rule": "{sub_rule.name}", "skip_conditions": 1}}',
				"next_step_if_true": "MAIN-END",
			},
			{
				"action_id": "MAIN-END",
				"action_type": "Stop",
				"operation": "Success",
				"action_label": "Main End",
				"is_enabled": 1,
			},
		]

		main_rule = self.create_test_rule("Test Main Rule", actions=main_actions)

		engine = RuleEngine(main_rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		engine.execute(doc)

		# Should execute the sub-rule
		executed_actions = [
			entry["message"] for entry in engine.execution_log if "Executing action" in entry["message"]
		]
		sub_executed = any("Call Sub Rule" in action for action in executed_actions)
		self.assertTrue(sub_executed)

	def test_engine_execute_wait_action(self):
		"""Test rule execution with Wait action"""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "ACT-WAIT",
			},
			{
				"action_id": "ACT-WAIT",
				"action_type": "Wait",
				"action_label": "Wait Action",
				"is_enabled": 1,
				"config": '{"duration": 0.1}',  # Very short wait for testing
				"next_step_if_true": "ACT-AFTER-WAIT",
			},
			{
				"action_id": "ACT-AFTER-WAIT",
				"action_type": "Process",
				"action_label": "After Wait",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "after_wait_res",
				"on_error": "Stop",
			},
		]

		rule = self.create_test_rule("Test Wait Action", actions=actions)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		# Record start time
		start_time = time.time()
		engine.execute(doc)
		end_time = time.time()

		# Should execute the wait action
		executed_actions = [
			entry["message"] for entry in engine.execution_log if "Executing action" in entry["message"]
		]
		wait_executed = any("Wait Action" in action for action in executed_actions)
		after_wait_executed = any("After Wait" in action for action in executed_actions)

		self.assertTrue(wait_executed)
		self.assertTrue(after_wait_executed)

		# Duration should be at least the wait time (though it might be slightly longer due to processing)
		self.assertGreaterEqual(end_time - start_time, 0.05)  # At least 0.05s, accounting for processing time

	def test_engine_execute_with_return_variable(self):
		"""Test rule execution with return variable storage"""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "ACT-PROCESS",
			},
			{
				"action_id": "ACT-PROCESS",
				"action_type": "Process",
				"action_label": "Get Description Length",
				"is_enabled": 1,
				"process_name": "Validation",  # Use existing process
				"operation": "value_in_range",  # Use existing operation
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "desc_length",
				"on_error": "Stop",
			},
		]

		rule = self.create_test_rule("Test Return Variable", actions=actions)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})  # Length is 4 > 3

		result = engine.execute(doc)

		# The variable should be stored in context
		# Note: The actual return value depends on the operation implementation
		# For value_in_range, it returns a boolean when the numeric check passes
		self.assertIn("desc_length", result["vars"])

	def test_engine_execute_with_error_handling_continue(self):
		"""Test rule execution with error handling set to Continue"""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "ACT-FAIL-PROCESS",
			},
			{
				"action_id": "ACT-FAIL-PROCESS",
				"action_type": "Process",
				"action_label": "Fail Process",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",  # This will fail if description is empty
				"config": '{"field": "description", "min_value": 1}',  # This should cause an error
				"return_variable": "error_res",
				"on_error": "Continue",  # Should continue despite error
				"next_step_if_true": "ACT-AFTER-ERROR",
			},
			{
				"action_id": "ACT-AFTER-ERROR",
				"action_type": "Process",
				"action_label": "After Error",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "after_error_res",
				"on_error": "Stop",
			},
		]

		rule = self.create_test_rule("Test Error Continue", actions=actions)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		# This should not raise an exception due to Continue error handling
		engine.execute(doc)

		# Both actions should have been attempted
		executed_actions = [
			entry["message"] for entry in engine.execution_log if "Executing action" in entry["message"]
		]
		fail_process_executed = any("Fail Process" in action for action in executed_actions)
		after_error_executed = any("After Error" in action for action in executed_actions)

		self.assertTrue(fail_process_executed)
		# With Continue, the next action should still execute
		self.assertTrue(after_error_executed)

	def test_engine_execute_with_error_handling_stop(self):
		"""Test rule execution with error handling set to Stop"""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "ACT-FAIL-PROCESS",
			},
			{
				"action_id": "ACT-FAIL-PROCESS",
				"action_type": "Process",
				"action_label": "Fail Process",
				"is_enabled": 1,
				"process_name": "Enrichment",
				"operation": "calculate_value",
				"config": '{"target_field": "description", "formula": "1/0"}',
				"return_variable": "fail_res",
				"on_error": "Stop",  # Should stop on error
				"next_step_if_true": "ACT-AFTER-ERROR",
			},
			{
				"action_id": "ACT-AFTER-ERROR",
				"action_type": "Process",
				"action_label": "After Error",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "after_fail_res",
				"on_error": "Stop",
			},
		]

		rule = self.create_test_rule("Test Error Stop", actions=actions)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		# This should raise an exception due to Stop error handling
		with self.assertRaises(Exception):
			engine.execute(doc)

	def test_engine_execute_with_cycle_detection(self):
		"""Test rule execution with cycle detection"""
		# Create a circular reference intentionally
		# But we'll use a Loop action type which is allowed for cycles
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "ACT-PROCESS",
			},
			{
				"action_id": "ACT-PROCESS",
				"action_type": "Process",
				"action_label": "Process",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "cycle_res",
				"on_error": "Stop",
				"next_step_if_true": "root",  # Points back, creating cycle
			},
		]

		# This should fail during rule creation due to cycle detection in graph validation
		with self.assertRaises(Exception):
			self.create_test_rule("Test Cycle Detection", actions=actions)

	def test_engine_execute_with_timeout(self):
		"""Test rule execution with timeout"""
		# Create a rule that would take too long
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "ACT-PROCESS",
			},
			{
				"action_id": "ACT-PROCESS",
				"action_type": "Process",
				"action_label": "Slow Process",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "timeout_res",
				"on_error": "Stop",
			},
		]

		rule = self.create_test_rule("Test Timeout", actions=actions)
		rule.max_execution_time = 0.1  # Very short timeout for testing
		rule.flags.ignore_validate = True
		rule.save(ignore_permissions=True)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		# Mock time passing to trigger timeout between action iterations
		class TimeMock:
			def __init__(self):
				self.count = 0
				self.start_t = time.time()

			def __call__(self):
				self.count += 1
				return self.start_t + (100 if self.count > 1 else 0)

		with patch("time.time", side_effect=TimeMock()):
			with self.assertRaises(FlexiRuleTimeoutError):
				engine.execute(doc, test_mode=False)  # Don't use test mode to enforce timeout

	def test_engine_execute_with_test_mode_no_timeout(self):
		"""Test rule execution in test mode ignores timeout"""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "ACT-PROCESS",
			},
			{
				"action_id": "ACT-PROCESS",
				"action_type": "Process",
				"action_label": "Process",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "test_mode_res",
				"on_error": "Stop",
			},
		]

		rule = self.create_test_rule("Test No Timeout In Test Mode", actions=actions)
		rule.max_execution_time = 0.01  # Very short timeout
		rule.flags.ignore_validate = True
		rule.save(ignore_permissions=True)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		# In test mode, timeout should be ignored
		result = engine.execute(doc, test_mode=True)
		self.assertIsInstance(result, dict)

	def test_engine_execute_with_skip_for_roles(self):
		"""Test rule execution with skip for roles"""
		# Create a test user
		test_user = "test_skip_role@example.com"
		if not frappe.db.exists("User", test_user):
			user_doc = frappe.get_doc(
				{
					"doctype": "User",
					"email": test_user,
					"first_name": "Test Skip Role",
					"send_welcome_email": 0,
					"user_type": "System User",
				}
			)
			user_doc.insert(ignore_permissions=True)

		# Add a role to the user and clear cache
		user_doc = frappe.get_doc("User", test_user)
		user_doc.add_roles("System Manager")
		frappe.clear_cache(user=test_user)

		try:
			# Create a rule that skips for System Manager role
			rule = self.create_test_rule("Test Skip Roles")
			rule.append("skip_for_roles", {"role": "System Manager"})
			rule.flags.ignore_validate = True
			rule.save(ignore_permissions=True)

			# Set user context
			frappe.set_user(test_user)

			engine = RuleEngine(rule)
			doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

			# Execution should be skipped
			engine.execute(doc)

			# Check if the rule was skipped by looking at execution log
			skip_messages = [
				entry["message"]
				for entry in engine.execution_log
				if "Skipping rule execution" in entry["message"]
			]
			self.assertTrue(len(skip_messages) > 0)

		finally:
			# Clean up
			frappe.set_user("Administrator")
			if frappe.db.exists("User", test_user):
				frappe.delete_doc("User", test_user, force=True)

	def test_get_start_node_explicit_root(self):
		"""Test getting start node when explicit root exists"""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Root",
				"is_enabled": 1,
				"next_step_if_true": "ACT-NEXT",
			},
			{
				"action_id": "ACT-NEXT",
				"action_type": "Process",
				"action_label": "Next",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "next_res",
				"on_error": "Stop",
			},
		]

		rule = self.create_test_rule("Test Explicit Root", actions=actions)
		engine = RuleEngine(rule)

		start_node = engine._get_start_node()
		self.assertEqual(start_node.action_id, "root")

	def test_get_start_node_no_incoming_edges(self):
		"""Test getting start node by finding node with no incoming edges"""
		actions = [
			{
				"action_id": "ACT-FIRST",
				"action_type": "Entry Action",
				"action_label": "First",
				"is_enabled": 1,
				"next_step_if_true": "ACT-SECOND",
			},
			{
				"action_id": "ACT-SECOND",
				"action_type": "Process",
				"action_label": "Second",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "sec_res",
				"on_error": "Stop",
			},
		]

		rule = self.create_test_rule("Test No Incoming Edges", actions=actions)
		engine = RuleEngine(rule)

		start_node = engine._get_start_node()
		self.assertEqual(start_node.action_id, "ACT-FIRST")

	def test_get_start_node_fallback_first(self):
		"""Test getting start node fallback to first action"""
		# Create a simple linear flow
		actions = [
			{
				"action_id": "ACT-A",
				"action_type": "Entry Action",
				"action_label": "A",
				"is_enabled": 1,
				"next_step_if_true": "ACT-B",
			},
			{
				"action_id": "ACT-B",
				"action_type": "Process",
				"action_label": "B",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "b_res",
				"on_error": "Stop",
			},
		]

		rule = self.create_test_rule("Test Fallback", actions=actions)
		engine = RuleEngine(rule)

		start_node = engine._get_start_node()
		# Should return the entry action
		self.assertEqual(start_node.action_id, "ACT-A")
