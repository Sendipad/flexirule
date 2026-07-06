import json

import frappe
from frappe.tests.utils import FrappeTestCase


class TestTriggerConditionMigration(FrappeTestCase):
	def setUp(self):
		self.rule_name = "Migration Test Rule"
		if frappe.db.exists("Rule", self.rule_name):
			frappe.delete_doc("Rule", self.rule_name)

		# Create a rule with legacy trigger_condition
		self.condition = {
			"op": "and",
			"conditions": [{"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Open"}}],
		}

		self.rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": self.rule_name,
				"document_type": "User",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"trigger_condition": json.dumps(self.condition),
				"actions": [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"action_label": "Start",
						"next_step_if_true": "stop_node",
					},
					{
						"action_id": "stop_node",
						"action_type": "Stop",
						"action_label": "Stop",
						"operation": "Success",
					},
				],
			}
		)
		self.rule.insert(ignore_permissions=True)
		# Clear config of entry action to simulate Case A
		entry_action = self.rule.get_entry_action()
		frappe.db.set_value("Rule Action", entry_action.name, "config", None)

	def test_migration_case_a_clean_move(self):
		from flexirule.patches.v1_0.migrate_trigger_condition_to_entry_action import execute

		execute()

		# Reload
		self.rule.reload()
		entry_action = self.rule.get_entry_action()

		# Verify migrated
		self.assertEqual(json.loads(entry_action.config), self.condition)
		# Verify legacy field is NOT cleared
		self.assertEqual(json.loads(self.rule.trigger_condition), self.condition)
		# Verify compiled_expression is updated
		self.assertTrue(self.rule.compiled_expression)

	def test_migration_idempotency(self):
		from flexirule.patches.v1_0.migrate_trigger_condition_to_entry_action import execute

		# Run once
		execute()
		self.rule.reload()
		first_config = self.rule.get_entry_action().config

		# Run again
		execute()
		self.rule.reload()
		second_config = self.rule.get_entry_action().config

		self.assertEqual(first_config, second_config)

	def test_migration_case_b_ambiguity(self):
		# Set different config in Entry Action
		other_condition = {
			"op": "and",
			"conditions": [{"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Closed"}}],
		}
		entry_action = self.rule.get_entry_action()
		frappe.db.set_value("Rule Action", entry_action.name, "config", json.dumps(other_condition))

		# Mock log_error to verify it was called since Error Log is proving tricky in test transaction
		import flexirule.patches.v1_0.migrate_trigger_condition_to_entry_action as patch_mod
		from flexirule.patches.v1_0.migrate_trigger_condition_to_entry_action import execute

		original_log = patch_mod.frappe.log_error
		log_called = [False]

		def mock_log(msg, title):
			log_called[0] = True

		patch_mod.frappe.log_error = mock_log
		try:
			execute()
		finally:
			patch_mod.frappe.log_error = original_log

		self.assertTrue(log_called[0])

		# Verify NOT migrated
		self.rule.reload()
		entry_action = self.rule.get_entry_action()
		self.assertEqual(json.loads(entry_action.config), other_condition)
