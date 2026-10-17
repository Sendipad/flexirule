# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Condition Action Handler.

Evaluates a compiled Python condition expression and routes to
next_step_if_true or next_step_if_false based on the result.
"""

import frappe
from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry
from flexirule.ruleflow.core.action_handlers.base_contract import ActionContract, OperationContract
from flexirule.ruleflow.core.condition_payload import get_condition_payload


class ConditionHandler(ActionHandler):
	"""Handler for Condition action type."""

	action_type = "Condition"

	@classmethod
	def get_action_contract(cls):
		return ActionContract(
			action_type="Condition",
			display_label="Condition",
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
	def get_operation_contracts(cls) -> dict:
		return {
			"Condition": OperationContract(
				operation="Condition",
				action_overrides=[
					{"fieldname": "action_type", "default": "Condition"},
					{"fieldname": "config", "reqd": 1},
					{
						"fieldname": "next_step_if_false",
						"mandatory_depends_on": "eval:doc.parent.is_active===1",
					},
					{"fieldname": "description", "description": "Evaluates a condition to branch execution"},
				],
				validation={"frontend": "validate_condition"},
			)
		}

	def execute(self, action, context, engine):
		"""Evaluate the saved tree first; use compiled Python only for legacy records."""
		payload = get_condition_payload(action)
		compiled_expression = getattr(action, "compiled_expression", None)

		if payload is not None:
			from flexirule.ruleflow.core.evaluator import ConditionEvaluator

			result = ConditionEvaluator(payload, strict=True).evaluate(context=context)
		elif compiled_expression:
			# Legacy fallback for records without a readable saved condition payload.
			result = engine._evaluate_python_condition(compiled_expression, context)
		else:
			raw_config = action.get("config") if hasattr(action, "get") else getattr(action, "config", None)
			raw_legacy = (
				action.get("condition_json")
				if hasattr(action, "get")
				else getattr(action, "condition_json", None)
			)
			if raw_config not in (None, "") or raw_legacy not in (None, ""):
				frappe.throw(
					_(
						"Action '{0}' has invalid condition configuration. Please correct the condition tree and save the Rule."
					).format(getattr(action, "action_label", None) or getattr(action, "name", "")),
					frappe.ValidationError,
				)
			result = True

		next_id = action.next_step_if_true if result else action.next_step_if_false
		return result, next_id

	def validate(self, action, context):
		"""Validate that a configured condition is a readable tree."""
		errors = []
		raw_config = action.get("config") if hasattr(action, "get") else getattr(action, "config", None)
		raw_legacy = (
			action.get("condition_json")
			if hasattr(action, "get")
		else getattr(action, "condition_json", None)
		)
		if (raw_config not in (None, "") or raw_legacy not in (None, "")) and get_condition_payload(action) is None:
			errors.append(
				_("Condition '{0}' has invalid condition configuration.").format(
					getattr(action, "action_label", None) or getattr(action, "name", "")
				)
			)
		return errors


# Register the handler
HandlerRegistry.register(ConditionHandler())
