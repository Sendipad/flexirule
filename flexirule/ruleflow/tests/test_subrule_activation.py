import frappe

from flexirule.ruleflow.tests.builder import RuleBuilder
from flexirule.ruleflow.tests.test_case import FlexiRuleTestCase


class TestSubRuleActivation(FlexiRuleTestCase):
	def test_subrule_activation_sequence(self):
		# 1. Create Inactive Sub-Rule
		sub_rule = (
			RuleBuilder("Inactive Sub Rule")
			.document_type("Test Contact")
			.subrule()
			.active(0)
			.entry_action(next_step="stop_node")
			.stop(action_id="stop_node")
			.build()
		)

		self.assertEqual(sub_rule.is_active, 0)

		# 2. Create Inactive Parent Rule referencing Inactive Sub-Rule
		# This should now succeed
		parent_builder = (
			RuleBuilder("Inactive Parent Rule")
			.document_type("Test Contact")
			.active(0)
			.entry_action(next_step="call_sub")
			.sub_rule_call("Call Sub", sub_rule.name, action_id="call_sub", next_step="stop_1")
			.stop(action_id="stop_1")
		)

		parent_rule = parent_builder.build()
		self.assertEqual(parent_rule.is_active, 0)

		# 3. Attempt to Activate Parent Rule while Sub-Rule is Inactive
		# This should fail
		parent_rule.is_active = 1
		with self.assertRaises(frappe.ValidationError) as cm:
			parent_rule.save()

		self.assertIn("must target an active rule", str(cm.exception))

		# 4. Activate Sub-Rule
		sub_rule.reload()
		sub_rule.is_active = 1
		sub_rule.save()
		self.assertEqual(sub_rule.is_active, 1)

		# 5. Activate Parent Rule
		# This should now succeed
		parent_rule.reload()
		parent_rule.is_active = 1
		parent_rule.save()
		self.assertEqual(parent_rule.is_active, 1)
