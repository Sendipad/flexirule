import json

import frappe
from frappe.tests.utils import FrappeTestCase


class TestRuleCycles(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Rule")
		frappe.db.delete("Rule Action")
		frappe.db.delete("Rule Execution Log")

	def create_rule(self, name, actions=None, trigger_condition=None):
		if actions is None:
			actions = [{"action_id": "root", "action_type": "Entry Action", "action_label": "Start"}]

		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": name,
				"document_type": "Note",
				"trigger_type": "Callable Event",
				"is_active": 0,
				"exposed_as_subrule": 1,
				"priority": "0",
				"trigger_condition": trigger_condition,
				"actions": actions,
			}
		)
		rule.insert()
		return rule

	def test_direct_cycle(self):
		# A calls A
		rule = self.create_rule("Rule A")
		rule.set("actions", [])
		rule.append(
			"actions",
			{
				"action_id": "act_a_call_a",
				"action_type": "Sub-Rule",
				"action_label": "Call A",
				"rule": rule.name,
				"config": json.dumps({"rule": rule.name}),
			},
		)
		with self.assertRaises(frappe.ValidationError) as cm:
			rule.save()
		self.assertIn("cannot reference its own Rule as Sub-Rule", str(cm.exception))

	def test_indirect_cycle(self):
		# A calls B, B calls A
		rule_a = self.create_rule("Rule A")
		rule_b = self.create_rule("Rule B")
		frappe.db.set_value("Rule", rule_b.name, "is_active", 1, update_modified=False)

		# A calls B
		rule_a.set("actions", [])
		rule_a.append(
			"actions",
			{
				"action_id": "act_a_call_b",
				"action_type": "Sub-Rule",
				"action_label": "Call B",
				"rule": rule_b.name,
				"config": json.dumps({"rule": rule_b.name}),
			},
		)
		rule_a.save()
		frappe.db.set_value("Rule", rule_a.name, "is_active", 1, update_modified=False)

		# B calls A -> Cycle
		rule_b.set("actions", [])
		rule_b.append(
			"actions",
			{
				"action_id": "act_b_call_a",
				"action_type": "Sub-Rule",
				"action_label": "Call A",
				"rule": rule_a.name,
				"config": json.dumps({"rule": rule_a.name}),
			},
		)
		with self.assertRaises(frappe.ValidationError) as cm:
			rule_b.save()
		self.assertIn("Cycle detected in sub-rule graph", str(cm.exception))

	def test_loop_cycle_prevention(self):
		# A -> B -> C -> A
		rule_a = self.create_rule("Rule A")
		rule_b = self.create_rule("Rule B")
		rule_c = self.create_rule("Rule C")
		frappe.db.set_value("Rule", rule_b.name, "is_active", 1, update_modified=False)
		frappe.db.set_value("Rule", rule_c.name, "is_active", 1, update_modified=False)

		rule_a.set("actions", [])
		rule_a.append(
			"actions",
			{
				"action_id": "act_a_next",
				"action_label": "Next",
				"action_type": "Sub-Rule",
				"rule": rule_b.name,
				"config": json.dumps({"rule": rule_b.name}),
			},
		)
		rule_a.save()
		frappe.db.set_value("Rule", rule_a.name, "is_active", 1, update_modified=False)

		rule_b.set("actions", [])
		rule_b.append(
			"actions",
			{
				"action_id": "act_b_next",
				"action_label": "Next",
				"action_type": "Sub-Rule",
				"rule": rule_c.name,
				"config": json.dumps({"rule": rule_c.name}),
			},
		)
		rule_b.save()

		rule_c.set("actions", [])
		rule_c.append(
			"actions",
			{
				"action_id": "act_c_next",
				"action_label": "Next",
				"action_type": "Sub-Rule",
				"rule": rule_a.name,
				"config": json.dumps({"rule": rule_a.name}),
			},
		)
		with self.assertRaises(frappe.ValidationError) as cm:
			rule_c.save()
		self.assertIn("Cycle detected in sub-rule graph", str(cm.exception))

	"""
    def test_sub_rule_bypass_condition(self):
        # Helper to clear logs before each execution
        def clear_rule_logs():
            frappe.db.sql("DELETE FROM `tabRule Execution Log`")
            # frappe.db.commit() removed for test isolation

        # Create notes for testing
        note1 = frappe.get_doc({"doctype": "Note", "title": "Test Note 1"}).insert()
        note2 = frappe.get_doc({"doctype": "Note", "title": "Test Note 2"}).insert()

        # Create Sub Rule that should normally not match
        sub_rule = self.create_rule("Sub Rule", trigger_condition="doc.title == 'Impossible'")
        sub_rule.set("actions", [])
        sub_rule.append("actions", {
            "action_id": "act_stop",
            "action_type": "Stop",
            "action_label": "Log Stop"
        })
        sub_rule.is_active = 1
        sub_rule.save()

        # Clear cache to ensure fresh execution
        from flexirule.ruleflow.core.coordinator import RuleCoordinator
        RuleCoordinator.clear_cache()
        frappe.cache().delete_keys("Rule")

        # --- Test Strict Main Rule (skip_conditions=0) ---
        main_rule_strict = self.create_rule("Main Strict")
        main_rule_strict.set("actions", [])
        main_rule_strict.append("actions", {
            "action_id": "act_strict",
            "action_label": "Strict Call",
            "action_type": "Sub-Rule",
            "rule": sub_rule.name,
            "config": json.dumps({
                "rule": sub_rule.name,
                "skip_conditions": 0  # IMPORTANT: put inside config
            })
        })
        main_rule_strict.is_active = 1
        main_rule_strict.save()

        clear_rule_logs()
        from flexirule.ruleflow.core.engine import RuleEngine
        engine = RuleEngine(main_rule_strict.name)
        engine.execute(note1)

        logs = frappe.get_all("Rule Execution Log", filters={"rule": sub_rule.name})
        self.assertEqual(len(logs), 0, "Sub Rule should NOT execute when skip_conditions=0")

        # --- Test Loose Main Rule (skip_conditions=1) ---
        main_rule_loose = self.create_rule("Main Loose")
        main_rule_loose.set("actions", [])
        main_rule_loose.append("actions", {
            "action_id": "act_loose",
            "action_label": "Loose Call",
            "action_type": "Sub-Rule",
            "rule": sub_rule.name,
            "config": json.dumps({
                "rule": sub_rule.name,
                "skip_conditions": 1  # IMPORTANT: put inside config
            })
        })
        main_rule_loose.is_active = 1
        main_rule_loose.save()

        clear_rule_logs()
        engine = RuleEngine(main_rule_loose.name)
        engine.execute(note2)

        logs = frappe.get_all("Rule Execution Log", filters={"rule": sub_rule.name})
        self.assertGreater(len(logs), 0, "Sub Rule SHOULD execute when skip_conditions=1")
    """
