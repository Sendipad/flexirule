import frappe

from flexirule.ruleflow.tests.builder import RuleBuilder
from flexirule.ruleflow.tests.factories import make_test_contact
from flexirule.ruleflow.tests.test_case import FlexiRuleTestCase


class TestRuleRefactored(FlexiRuleTestCase):
	def test_active_rule_requires_next_step(self):
		# Using RuleBuilder to verify validation logic
		builder = (
			RuleBuilder("Test Missing False Path")
			.document_type("Test Contact")
			.entry_action(next_step="condition_1")
			.condition(
				"Check",
				'[{"left":{"ref":"doc.first_name"},"op":"!=","right":{"value":""}}]',
				next_true="stop_1",
			)
			.stop("Stop", action_id="stop_1")
		)

		with self.assertRaises(frappe.ValidationError):
			builder.build()

	def test_notify_email_validation(self):
		builder = (
			RuleBuilder("Test Notify Validation")
			.document_type("Test Contact")
			.entry_action(next_step="notify_1")
			.add_action(
				action_id="notify_1",
				action_type="Notify",
				action_label="Notify Email",
				operation="Email",
				value_template="Hello {{ doc.first_name }}",
				config="{}",
			)
		)

		with self.assertRaises(frappe.ValidationError):
			builder.build()

	def test_sub_rule_visibility_validation(self):
		# Target not exposed as subrule
		target_rule = (
			RuleBuilder("Hidden Target")
			.document_type("Test Contact")
			.subrule(exposed=0)
			.entry_action()
			.build()
		)

		parent_builder = (
			RuleBuilder("Parent Rule")
			.document_type("Test Contact")
			.entry_action(next_step="call_sub")
			.sub_rule_call("Call Target", target_rule.name, action_id="call_sub")
		)

		with self.assertRaises(frappe.ValidationError):
			parent_builder.build()
