# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Comprehensive Unit Test Suite for FlexiRule Rule Engine
"""

import json
import unittest
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.doctype.process.process import Process


def create_test_rule(name, doctype="ToDo", event="Validate", actions=None):
	"""Helper to create test rules"""
	if frappe.db.exists("Rule", name):
		return frappe.get_doc("Rule", name)

	rule = frappe.get_doc(
		{
			"doctype": "Rule",
			"rule_name": name,
			"document_type": doctype,
			"trigger_type": "DocType Event",
			"trigger_event": event,
			"is_active": 1,
			"priority": "0" if event == "Manual" else "10",
			"max_execution_time": 30,
		}
	)

	if actions:
		for action in actions:
			rule.append("actions", action)

	rule.insert(ignore_permissions=True)
	return rule


class TestRuleEngine(FrappeTestCase):
	"""Test RuleEngine class"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

	def test_engine_initialization(self):
		"""Test engine initializes correctly"""
		from flexirule.ruleflow.core.engine import RuleEngine

		rule = create_test_rule("Test Engine Init")
		engine = RuleEngine(rule)

		self.assertEqual(engine.rule.name, "Test Engine Init")
		self.assertIsInstance(engine.execution_log, list)

	def test_engine_validates_disabled_rule(self):
		"""Test engine rejects disabled rules"""
		from flexirule.ruleflow.core.engine import RuleEngine
		from flexirule.ruleflow.core.exceptions import RuleDisabledError

		rule = create_test_rule("Test Disabled Rule")
		rule.is_active = 0
		rule.save()

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		with self.assertRaises(RuleDisabledError):
			engine.execute(doc)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()


class TestNewTriggerEvents(FrappeTestCase):
	"""Test the newly added trigger events"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

	def test_before_naming_trigger(self):
		"""Test 'Before Naming' trigger event"""
		from flexirule.ruleflow.core.coordinator import RuleCoordinator

		RuleCoordinator.clear_cache()

		# Create a rule that sets description 'Set by Naming' on Before Naming
		rule_name = "Test Before Naming"
		create_test_rule(
			rule_name,
			doctype="ToDo",
			event="Before Naming",
			actions=[
				{
					"action_id": "set_desc_naming",
					"action_type": "Assignment",
					"config": '[{"target": "doc.description", "operator": "set", "value_template": "Set by Naming"}]',
					"action_label": "Set Description",
					"is_enabled": 1,
				}
			],
		)

		# Creating a doc triggers before_naming
		todo = frappe.get_doc({"doctype": "ToDo", "description": "Original"})
		todo.insert()

		self.assertEqual(todo.description, "Set by Naming")

	def test_on_change_trigger(self):
		"""Test 'On Change' trigger event"""
		from flexirule.ruleflow.core.coordinator import RuleCoordinator

		RuleCoordinator.clear_cache()

		todo = frappe.get_doc({"doctype": "ToDo", "description": "Original"}).insert()

		# On Change runs after the document is saved, so it should use
		# non-mutating actions such as notifications rather than Set Value.
		rule_name = "Test On Change"
		create_test_rule(
			rule_name,
			doctype="ToDo",
			event="On Change",
			actions=[
				{
					"action_id": "notify_change",
					"action_type": "Notify",
					"action_label": "Notify Change",
					"operation": "System Notification",
					"value_template": "Changed {{ doc.name }}",
					"config": '{"subject":"On Change {{ doc.name }}","for_user":"Administrator"}',
					"is_enabled": 1,
				}
			],
		)

		todo.description = "Something Else"
		todo.save()

		notification_name = frappe.db.get_value(
			"Notification Log",
			{
				"for_user": "Administrator",
				"subject": f"On Change {todo.name}",
			},
			"name",
			order_by="creation desc",
		)
		self.assertTrue(notification_name)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()


if __name__ == "__main__":
	unittest.main()
