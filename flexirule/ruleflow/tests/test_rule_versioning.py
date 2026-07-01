"""
Tests for Logical Rule Versioning, Safe Editing, and Sub-Rule Lifecycle.

Covers:
- Version amendment flow (base_rule_name, previous_version lineage)
- Version promotion via transition_rule (auto-deactivation of old version)
- Deactivation safety (blocks deactivation when active parents reference the sub-rule)
- Deletion safety (blocks deletion when active parents reference the sub-rule)
- Cycle detection with versioned names (logical base name normalization)
- Sub-rule target resolution via logical base name
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.tests.builder import RuleBuilder


class TestRuleVersioning(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Rule")
		frappe.db.delete("Rule Action")
		frappe.db.delete("Rule Execution Log")
		frappe.db.delete("Rule Scheduler")

	# ── helpers ──────────────────────────────────────────────

	def _create_callable_sub_rule(self, name, active=0):
		"""Create a minimal Callable Event sub-rule."""
		return (
			RuleBuilder(name)
			.document_type("Test Contact")
			.subrule()
			.active(active)
			.entry_action(next_step="stop_node")
			.stop(action_id="stop_node")
			.build()
		)

	def _create_parent_rule(self, name, sub_rule_target, active=0):
		"""Create a parent rule that calls a sub-rule by its logical name."""
		return (
			RuleBuilder(name)
			.document_type("Test Contact")
			.active(active)
			.entry_action(next_step="call_sub")
			.sub_rule_call("Call Sub", sub_rule_target, action_id="call_sub", next_step="stop_1")
			.stop(action_id="stop_1")
			.build()
		)

	# ── Amendment / version fields ───────────────────────────

	def test_base_rule_name_populated_on_insert(self):
		"""New rules should auto-populate base_rule_name from rule_name."""
		rule = self._create_callable_sub_rule("MY_CREDIT_CHECK")
		rule.reload()
		self.assertEqual(rule.base_rule_name, "MY_CREDIT_CHECK")

	def test_base_rule_name_strips_version_suffix(self):
		"""If rule_name already ends with _v<N>, base_rule_name strips it."""
		rule = (
			RuleBuilder("FOO_v3")
			.document_type("Test Contact")
			.subrule()
			.active(0)
			.entry_action(next_step="stop_node")
			.stop(action_id="stop_node")
			.build()
		)
		rule.reload()
		self.assertEqual(rule.base_rule_name, "FOO")

	def test_amend_rule_sets_version_lineage(self):
		"""amend_rule should set previous_version and base_rule_name on the new draft."""
		from flexirule.ruleflow.core.rule_service import amend_rule

		original = self._create_callable_sub_rule("AMEND_TEST")
		original.reload()

		new_name = amend_rule(original.name)
		new_doc = frappe.get_doc("Rule", new_name)

		self.assertEqual(new_doc.previous_version, original.name)
		self.assertEqual(new_doc.base_rule_name, "AMEND_TEST")
		self.assertEqual(new_doc.version, 2)
		self.assertIn("_v2", new_doc.rule_name)
		self.assertEqual(new_doc.is_active, 0)

	def test_amend_creates_correct_chain(self):
		"""Multiple amendments should build a linear version chain."""
		from flexirule.ruleflow.core.rule_service import amend_rule

		v1 = self._create_callable_sub_rule("CHAIN_TEST", active=1)
		v1.reload()

		v2_name = amend_rule(v1.name)
		v2 = frappe.get_doc("Rule", v2_name)
		self.assertEqual(v2.previous_version, v1.name)
		self.assertEqual(v2.version, 2)

		# Activate v2 so it can itself be amended
		v2.is_active = 1
		v2.save(ignore_permissions=True)

		v3_name = amend_rule(v2.name)
		v3 = frappe.get_doc("Rule", v3_name)
		self.assertEqual(v3.previous_version, v2.name)
		self.assertEqual(v3.version, 3)
		self.assertEqual(v3.base_rule_name, "CHAIN_TEST")

	# ── Version promotion via transition_rule ─────────────────

	def test_transition_rule_deactivates_previous_version(self):
		"""Activating v2 should auto-deactivate v1 of the same logical rule."""
		from flexirule.ruleflow.core.rule_service import amend_rule

		v1 = self._create_callable_sub_rule("PROMO_TEST", active=1)
		v1.reload()
		self.assertEqual(v1.is_active, 1)

		v2_name = amend_rule(v1.name)
		v2 = frappe.get_doc("Rule", v2_name)
		v2.is_active = 1
		v2.save(ignore_permissions=True)

		# v1 should now be deactivated (by the activation flow in transition_rule,
		# but since we're using .save() here directly, let's check via the API)
		from flexirule.ruleflow.api import transition_rule

		# Reset both to test via API
		frappe.db.set_value("Rule", v1.name, {"is_active": 1, "status": "Active"}, update_modified=False)
		frappe.db.set_value("Rule", v2.name, {"is_active": 0, "status": "Draft"}, update_modified=False)
		frappe.db.commit()

		transition_rule(v2.name, "Active")

		v1.reload()
		self.assertEqual(v1.is_active, 0, "v1 should be auto-deactivated after v2 promotion")
		self.assertEqual(v1.status, "Disabled")

	# ── Deactivation safety ───────────────────────────────────

	def test_deactivation_blocked_when_active_parents_exist(self):
		"""Cannot deactivate a sub-rule that active parents depend on."""
		sub_rule = self._create_callable_sub_rule("DEACT_SUB", active=1)
		sub_rule.reload()

		parent = self._create_parent_rule("DEACT_PARENT", sub_rule.base_rule_name, active=1)
		parent.reload()

		# Now try to deactivate the sub-rule
		sub_rule.reload()
		sub_rule.is_active = 0
		sub_rule.flags.run_deactivation_safety_in_test = True

		with self.assertRaises(frappe.ValidationError) as cm:
			sub_rule.save()

		self.assertIn("Cannot deactivate", str(cm.exception))
		self.assertIn("DEACT_PARENT", str(cm.exception))

	def test_deactivation_allowed_when_no_active_parents(self):
		"""Can deactivate a sub-rule when no active parent references it."""
		sub_rule = self._create_callable_sub_rule("DEACT_SAFE", active=1)
		sub_rule.reload()

		# Create an inactive parent that references it
		self._create_parent_rule("DEACT_INACT_PARENT", sub_rule.base_rule_name, active=0)

		sub_rule.reload()
		sub_rule.is_active = 0
		sub_rule.flags.run_deactivation_safety_in_test = True
		# Should not raise
		sub_rule.save()
		self.assertEqual(sub_rule.is_active, 0)

	def test_deactivation_allowed_when_other_version_active(self):
		"""Can deactivate v1 if v2 is active for the same logical rule."""
		from flexirule.ruleflow.core.rule_service import amend_rule

		v1 = self._create_callable_sub_rule("DEACT_VER", active=1)
		v1.reload()

		# Create parent that references the logical name
		self._create_parent_rule("DEACT_VER_PARENT", v1.base_rule_name, active=1)

		# Create and activate v2
		v2_name = amend_rule(v1.name)
		v2 = frappe.get_doc("Rule", v2_name)
		v2.is_active = 1
		v2.save(ignore_permissions=True)

		# Now deactivating v1 should be allowed because v2 covers the logical name
		v1.reload()
		v1.is_active = 0
		v1.flags.run_deactivation_safety_in_test = True
		v1.save()  # Should not raise
		self.assertEqual(v1.is_active, 0)

	# ── Deletion safety ───────────────────────────────────────

	def test_deletion_blocked_when_active_parents_exist(self):
		"""Cannot delete a sub-rule version when active parents reference its logical name."""
		sub_rule = self._create_callable_sub_rule("DEL_SUB", active=1)
		sub_rule.reload()

		parent = self._create_parent_rule("DEL_PARENT", sub_rule.base_rule_name, active=1)
		parent.reload()

		# Now deactivate sub-rule (bypass safety for setup) then try delete
		frappe.db.set_value("Rule", sub_rule.name, "is_active", 0, update_modified=False)

		# Delete should still be blocked because this is the only version and parent is active
		with self.assertRaises(frappe.ValidationError) as cm:
			frappe.delete_doc("Rule", sub_rule.name, force=True)

		self.assertIn("Cannot delete", str(cm.exception))

	def test_deletion_allowed_when_other_version_active(self):
		"""Can delete v1 if v2 is active for the same logical rule."""
		from flexirule.ruleflow.core.rule_service import amend_rule

		v1 = self._create_callable_sub_rule("DEL_VER", active=1)
		v1.reload()

		self._create_parent_rule("DEL_VER_PARENT", v1.base_rule_name, active=1)

		v2_name = amend_rule(v1.name)
		v2 = frappe.get_doc("Rule", v2_name)
		v2.is_active = 1
		v2.save(ignore_permissions=True)

		# Deactivate v1 first (bypass safety)
		frappe.db.set_value("Rule", v1.name, "is_active", 0, update_modified=False)

		# Should be able to delete v1 because v2 covers the logical name
		frappe.delete_doc("Rule", v1.name, force=True)
		self.assertFalse(frappe.db.exists("Rule", v1.name))

	# ── Cycle detection with versioned names ──────────────────

	def test_cycle_detection_across_versions(self):
		"""Cycle detection should work with logical base names, not versioned names."""
		# Create A and B as inactive first, then configure, then activate
		rule_a = self._create_callable_sub_rule("CYC_A", active=0)
		rule_b = self._create_callable_sub_rule("CYC_B", active=0)

		# Activate B so A can reference it
		rule_b.is_active = 1
		rule_b.save()

		# A calls B (A is inactive, so editable)
		rule_a.set("actions", [])
		rule_a.append(
			"actions",
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"next_step_if_true": "call_b",
			},
		)
		rule_a.append(
			"actions",
			{
				"action_id": "call_b",
				"action_type": "Sub-Rule",
				"action_label": "Call B",
				"rule": rule_b.base_rule_name,
				"next_step_if_true": "stop_1",
			},
		)
		rule_a.append(
			"actions",
			{
				"action_id": "stop_1",
				"action_type": "Stop",
				"action_label": "Stop",
			},
		)
		rule_a.save()

		# Activate A via db so we bypass the lock for the next step
		frappe.db.set_value("Rule", rule_a.name, "is_active", 1, update_modified=False)

		# B calls A → should detect cycle (B is active but we use db bypass)
		frappe.db.set_value("Rule", rule_b.name, "is_active", 0, update_modified=False)
		rule_b.reload()
		rule_b.set("actions", [])
		rule_b.append(
			"actions",
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"next_step_if_true": "call_a",
			},
		)
		rule_b.append(
			"actions",
			{
				"action_id": "call_a",
				"action_type": "Sub-Rule",
				"action_label": "Call A",
				"rule": rule_a.base_rule_name,
				"next_step_if_true": "stop_1",
			},
		)
		rule_b.append(
			"actions",
			{
				"action_id": "stop_1",
				"action_type": "Stop",
				"action_label": "Stop",
			},
		)

		with self.assertRaises(frappe.ValidationError) as cm:
			rule_b.save()

		self.assertIn("Cycle detected", str(cm.exception))

	# ── Sub-rule target resolution via logical name ───────────

	def test_sub_rule_target_resolves_by_base_name(self):
		"""Parent rules referencing a logical base name should resolve the active version."""
		sub_rule = self._create_callable_sub_rule("RESOLVE_SUB", active=1)
		sub_rule.reload()

		# Parent references the logical base name, not the versioned name
		parent = self._create_parent_rule("RESOLVE_PARENT", sub_rule.base_rule_name, active=1)
		parent.reload()

		# Verify the parent saved successfully (sub-rule was resolved)
		self.assertEqual(parent.is_active, 1)

		# Verify the action references the logical name
		sub_action = next(a for a in parent.actions if a.action_type == "Sub-Rule")
		self.assertEqual(sub_action.rule, sub_rule.base_rule_name)
