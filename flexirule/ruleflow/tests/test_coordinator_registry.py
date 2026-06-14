# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.coordinator import RuleCoordinator


class TestCoordinatorRegistry(FrappeTestCase):
	def setUp(self):
		super().setUp()
		RuleCoordinator.clear_cache()

	def test_registry_rebuild_on_rule_change(self):
		"""Verify that registry is rebuilt when an active DocType Event rule is changed"""
		rule_name = "Registry Test Rule"
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
				"priority": 10,
				"actions": [
					{"action_id": "root", "action_type": "Entry Action", "action_label": "Start", "is_enabled": 1}
				],
			}
		).insert(ignore_permissions=True)

		# Registry should now contain this rule
		registry = RuleCoordinator.get_runtime_registry()
		self.assertIn(rule_name, registry["rules"])
		self.assertIn(rule_name, registry["doctype_event_map"]["ToDo"]["Validate"])

		# Change priority and verify it's updated (rebuild triggered)
		rule.priority = "20"
		rule.save()

		registry = RuleCoordinator.get_runtime_registry()
		self.assertEqual(registry["rules"][rule_name]["priority"], 20)

	def test_watched_fields_filtering(self):
		"""Verify that rules are skipped if none of the watched fields changed"""
		rule_name = "Watched Fields Rule"
		if frappe.db.exists("Rule", rule_name):
			frappe.delete_doc("Rule", rule_name)

		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": rule_name,
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"is_active": 1,
				"watched_fields": "description,status",
				"actions": [
					{"action_id": "root", "action_type": "Entry Action", "action_label": "Start", "is_enabled": 1}
				],
			}
		).insert(ignore_permissions=True)

		RuleCoordinator.clear_cache()

		# Create a doc
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Original", "status": "Open"}).insert()

		# 1. Change an unwatched field (priority)
		doc.priority = "High"
		# Mock old_doc since before_save normally handles this
		doc._doc_before_save = frappe.get_doc("ToDo", doc.name)

		rule_spec = RuleCoordinator.get_runtime_registry()["rules"][rule_name]
		passes = RuleCoordinator._passes_watched_field_filter(rule_spec, doc, "Before Save")
		self.assertFalse(passes, "Should skip rule when unwatched field changes")

		# 2. Change a watched field (status)
		doc.status = "Closed"
		passes = RuleCoordinator._passes_watched_field_filter(rule_spec, doc, "Before Save")
		self.assertTrue(passes, "Should execute rule when watched field changes")

	def test_reentry_guard(self):
		"""Verify that the same doc/event does not trigger recursive rule execution"""
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Recursive", "name": "REC-001"})

		with RuleCoordinator._event_reentry_guard(doc, "Validate") as first_call:
			self.assertTrue(first_call)
			with RuleCoordinator._event_reentry_guard(doc, "Validate") as second_call:
				self.assertFalse(second_call, "Re-entry guard should block recursive call for same doc/event")

		# After exiting guard, it should be available again
		with RuleCoordinator._event_reentry_guard(doc, "Validate") as third_call:
			self.assertTrue(third_call)
