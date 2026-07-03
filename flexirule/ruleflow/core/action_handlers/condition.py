# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Condition Action Handler.

Evaluates a compiled Python condition expression and routes to
next_step_if_true or next_step_if_false based on the result.
"""

from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry
from flexirule.ruleflow.core.action_handlers.base_contract import (
	ActionContract,
	OperationContract,
)
from flexirule.ruleflow.core.condition_payload import get_condition_payload


class ConditionHandler(ActionHandler):
	"""Handler for Condition action type."""

	action_type = "Condition"

	@classmethod
	def get_action_contract(cls):
		return ActionContract(
			action_type="Condition",
			required_fields=["config"],
			has_next_true=True,
			has_next_false=True,
			terminal=False,
			css={"icon": "fa fa-code-fork", "color": "#3b82f6"},
			validation={"frontend": "validate_condition"},
			field_labels={
				"compiled_expression": "Compiled Expression (Python)",
				"config": "Condition Builder Config",
			},
			node_type="condition",
			category="Control Flow",
			configurable=True,
			config_component="ConditionStep",
		)

	@classmethod
	def get_operation_contracts(cls):
		return {
			"Condition": OperationContract(
				operation="Condition",
				action_overrides=[
					{"fieldname": "action_type", "default": "Condition"},
					{"fieldname": "config", "reqd": 1},
					{"fieldname": "next_step_if_false", "mandatory_depends_on": "eval:doc.parent.is_active===1"},
					{"fieldname": "description", "description": "Evaluates a condition to branch execution"},
				],
				validation={"frontend": "validate_condition"},
			)
		}

	def execute(self, action, context, engine):
		"""
		Execute condition evaluation.

		The compiled_expression should already be compiled from config
		during Rule.validate(). If compiled_expression is missing but
		condition payload exists, the rule was not properly saved.

		Returns:
		    Tuple of (boolean_result, next_action_id)
		"""
		compiled_expression = getattr(action, "compiled_expression", None)
		if not compiled_expression:
			if get_condition_payload(action) is not None:
				raise ValueError(
					_(
						"Action '{0}' has condition config but no compiled_expression. "
						"Please re-save the Rule to compile conditions."
					).format(action.action_label)
				)
			# Empty condition passes
			result = True
		else:
			result = engine._evaluate_python_condition(compiled_expression, context)

		next_id = action.next_step_if_true if result else action.next_step_if_false
		return result, next_id

	def validate(self, action, context):
		"""Validate condition action configuration."""
		errors = []
		if get_condition_payload(action) is not None and not getattr(action, "compiled_expression", None):
			errors.append(
				_("Condition '{0}' needs to be compiled. Re-save the rule.").format(action.action_label)
			)
		return errors


# Register the handler
HandlerRegistry.register(ConditionHandler())
