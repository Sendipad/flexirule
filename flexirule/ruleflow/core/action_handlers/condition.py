# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Condition Action Handler.

Evaluates a compiled Python condition expression and routes to
next_step_if_true or next_step_if_false based on the result.
"""

from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry
from flexirule.ruleflow.core.action_handlers.base_contract import ActionContract, OperationContract
from flexirule.ruleflow.core.condition_contract import validate_condition_node
from flexirule.ruleflow.core.condition_errors import ConditionError, ConditionValidationError
from flexirule.ruleflow.core.condition_evaluator import evaluate_condition, evaluate_prepared_condition
from flexirule.ruleflow.core.condition_payload import (
	detect_canonical_condition_payload,
	get_condition_payload,
)


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
		"""Evaluate prepared canonical JSON or route legacy expressions through the adapter."""
		condition_getter = getattr(engine, "_get_condition_payload_and_prepared", None)
		if callable(condition_getter):
			payload, is_canonical, canonical_node, prepared = condition_getter(action)
		else:
			payload = get_condition_payload(action)
			is_canonical, canonical_node = detect_canonical_condition_payload(payload)
			prepared = None

		if is_canonical:
			doctype = getattr(getattr(engine, "rule", None), "document_type", None)
			if prepared is not None:
				result = evaluate_prepared_condition(prepared, context, doctype=doctype)
			else:
				result = evaluate_condition(canonical_node, context, doctype=doctype)
		else:
			compiled_expression = getattr(action, "compiled_expression", None)
			if not compiled_expression:
				if payload is not None:
					raise ConditionValidationError(
						"legacy_condition_not_compiled",
						"$",
						"Legacy condition config has no compiled expression; re-save or repair the Rule",
					)
				raise ConditionValidationError(
					"condition_required",
					"$",
					"Condition actions require a valid condition before execution",
				)
			result = engine._evaluate_python_condition(compiled_expression, context)

		next_id = action.next_step_if_true if result else action.next_step_if_false
		return result, next_id

	def validate(self, action, context):
		"""Validate without treating canonical JSON as a compiled Python expression."""
		errors: list[str] = []
		mode = context.get("mode") if isinstance(context, dict) else None
		rule = context.get("rule") if isinstance(context, dict) else None
		is_active = False
		if rule:
			is_active = bool(
				getattr(rule, "is_active", None)
				or (rule.get("is_active") if isinstance(rule, dict) else False)
			)

		try:
			payload = get_condition_payload(action)
			if payload in (None, ""):
				# Drafts intentionally tolerate incomplete setup, but activation / full mode must reject
				if mode == "full" or is_active:
					errors.append(
						_("Condition '{0}' requires a condition before activation.").format(
							getattr(action, "action_label", None)
							or getattr(action, "action_id", None)
							or _("Condition")
						)
					)
				return errors
			is_canonical, canonical_node = detect_canonical_condition_payload(payload)
			if is_canonical:
				if canonical_node is None:
					errors.append(
						_("Condition '{0}' has a malformed canonical condition payload.").format(
							getattr(action, "action_label", None)
							or getattr(action, "action_id", None)
							or _("Condition")
						)
					)
					return errors
				doctype = getattr(rule, "document_type", None) or (
					rule.get("document_type") if isinstance(rule, dict) else None
				)
				validate_condition_node(canonical_node, doctype=doctype)
				return errors
			if not getattr(action, "compiled_expression", None):
				errors.append(
					_("Condition '{0}' needs a compiled legacy expression or a valid canonical node.").format(
						getattr(action, "action_label", None)
						or getattr(action, "action_id", None)
						or _("Condition")
					)
				)
		except ConditionError as exc:
			errors.append(
				_("Condition '{0}' is invalid [{1} at {2}]: {3}").format(
					getattr(action, "action_label", None)
					or getattr(action, "action_id", None)
					or _("Condition"),
					exc.code,
					exc.path,
					exc.message,
				)
			)
		return errors


# Register the handler
HandlerRegistry.register(ConditionHandler())
