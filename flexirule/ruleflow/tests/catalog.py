import json

from flexirule.ruleflow.tests.builder import RuleBuilder


class ActionBlocks:
	@staticmethod
	def email_mandatory(builder, next_step=None):
		action_id = "check_email_mandatory"
		builder.add_action(
			action_id=action_id,
			action_type="Condition",
			action_label="Is Email Set?",
			condition_json=json.dumps(
				[{"left": {"ref": "doc.email_id"}, "op": "!=", "right": {"value": ""}}]
			),
			next_step_if_true=next_step,
			next_step_if_false="fail_email_mandatory",
		)
		builder.add_action(
			action_id="fail_email_mandatory",
			action_type="Raise Error",
			action_label="Raise Email Error",
			value_template="Email is mandatory.",
		)
		return action_id

	@staticmethod
	def normalize_email(builder, next_step=None):
		action_id = "normalize_email"
		builder.assignment(
			label="Normalize Email",
			action_id=action_id,
			assignments=[
				{
					"target": "doc.email_id",
					"operator": "set",
					"value": "{{ doc.email_id.lower().strip() if doc.email_id else '' }}",
				}
			],
			next_step=next_step,
		)
		return action_id

	@staticmethod
	def credit_limit_check(builder, next_step=None):
		action_id = "check_credit_limit"
		builder.add_action(
			action_id=action_id,
			action_type="Condition",
			action_label="Within Credit Limit?",
			condition_json=json.dumps(
				[{"left": {"ref": "doc.credit_limit"}, "op": "<=", "right": {"value": 10000}}]
			),
			next_step_if_true=next_step,
			next_step_if_false="fail_credit_limit",
		)
		builder.add_action(
			action_id="fail_credit_limit",
			action_type="Raise Error",
			action_label="Raise Credit Error",
			value_template="Credit limit exceeded (Max 10000).",
		)
		return action_id


class Workflows:
	@staticmethod
	def contact_validation(rule_name="Contact Validation", **kwargs):
		builder = RuleBuilder(rule_name).document_type("Test Contact").subrule()

		last_step = "success_stop"
		builder.stop("Success", action_id=last_step)

		if kwargs.get("normalize_email", True):
			last_step = ActionBlocks.normalize_email(builder, next_step=last_step)

		if kwargs.get("require_email", True):
			last_step = ActionBlocks.email_mandatory(builder, next_step=last_step)

		builder.entry_action(next_step=last_step)
		return builder.build()

	@staticmethod
	def customer_workflow(rule_name="Customer Flow", **kwargs):
		builder = RuleBuilder(rule_name).document_type("Test Customer")

		last_step = "customer_stop"
		builder.stop("Finished", action_id=last_step)

		if kwargs.get("check_credit", True):
			last_step = ActionBlocks.credit_limit_check(builder, next_step=last_step)

		if kwargs.get("sub_rule"):
			last_step = builder.sub_rule_call(
				"Call Sub-Rule", kwargs.get("sub_rule"), next_step=last_step
			)._actions[-1]["action_id"]

		builder.entry_action(next_step=last_step)
		return builder.build()
