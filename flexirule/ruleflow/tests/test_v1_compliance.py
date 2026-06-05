import json
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.coordinator import RuleCoordinator
from flexirule.ruleflow.core.engine import RuleEngine
from flexirule.ruleflow.utils.graph_validator import validate_graph_integrity


class TestV1Compliance(FrappeTestCase):
	def setUp(self):
		super().setUp()

	def test_eligibility_mode_strict(self):
		"""
		V1 Contract: Mode check (Sync/Async)
		"""
		# Create a dummy rule doc
		rule = frappe.new_doc("Rule")
		rule.is_active = 1
		rule.trigger_event = "Before Save"
		rule.document_type = "ToDo"
		# Only memory, don't save

		# Test Signature
		val = RuleCoordinator.check_eligibility(rule, frappe.new_doc("ToDo"), "Before Save")
		# Expect tuple
		self.assertIsInstance(val, tuple)
		is_eligible, reason = val

		self.assertTrue(is_eligible)

		# Test Mismatch Event
		is_eligible, reason = RuleCoordinator.check_eligibility(rule, frappe.new_doc("ToDo"), "After Save")
		self.assertFalse(is_eligible)
		self.assertIn("Event mismatch", reason)

		# Test Trigger Condition requires pre-compilation
		# Now if trigger_condition exists without compiled_expression, it's an error
		rule.trigger_condition = json.dumps(
			[
				{
					"left": {"type": "field", "value": "status"},
					"operator": "==",
					"right": "Open",
				}
			]
		)
		rule.compiled_expression = None  # No compiled version

		doc = frappe.new_doc("ToDo")
		doc.status = "Closed"
		is_eligible, reason = RuleCoordinator.check_eligibility(rule, doc, "Before Save")
		self.assertFalse(is_eligible)
		# New behavior: Returns error about missing compiled filters
		self.assertIn("compiled_expression", reason)

		# Test with properly compiled compiled_expression
		rule.compiled_expression = "resolve(doc, 'status') == 'Open'"
		is_eligible, reason = RuleCoordinator.check_eligibility(rule, doc, "Before Save")
		self.assertFalse(is_eligible)  # status is Closed, filter fails

		doc.status = "Open"
		is_eligible, reason = RuleCoordinator.check_eligibility(rule, doc, "Before Save")
		self.assertTrue(is_eligible)

	def test_graph_cycle_detection(self):
		"""
		V1 Contract: Acyclic Graph
		"""
		rule = frappe.new_doc("Rule")
		rule.append(
			"actions",
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Step A",
				"next_step_if_true": "B",
			},
		)
		rule.append(
			"actions",
			{
				"action_id": "B",
				"action_type": "Process",
				"action_label": "Step B",
				"next_step_if_true": "root",  # Cycle
			},
		)

		with self.assertRaises(frappe.ValidationError) as cm:
			validate_graph_integrity(rule)
		self.assertIn("Cycle detected", str(cm.exception))

	def test_orphan_detection(self):
		"""
		V1 Contract: Connected Graph (No orphans)
		"""
		rule = frappe.new_doc("Rule")
		rule.is_active = 1  # Enable orphan detection for active rules
		rule.append(
			"actions",
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Step A",
			},
		)
		# Valid so far. Now let's add C which is disconnected.
		rule.append(
			"actions",
			{"action_id": "C", "action_type": "Process", "action_label": "Step C"},
		)

		with self.assertRaises(frappe.ValidationError) as cm:
			validate_graph_integrity(rule)
		self.assertIn("Unreachable", str(cm.exception))
