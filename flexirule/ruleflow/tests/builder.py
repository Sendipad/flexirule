import json

import frappe

from flexirule.ruleflow.core.coordinator import RuleCoordinator


class RuleBuilder:
	def __init__(self, rule_name):
		self.rule_name = rule_name
		self._document_type = "ToDo"
		self._trigger_type = "DocType Event"
		self._trigger_event = "Validate"
		self._is_active = 1
		self._actions = []
		self._exposed_as_subrule = 0
		self._priority = "10"
		self._max_execution_time = 30
		self._trigger_condition = None

	def document_type(self, doctype):
		self._document_type = doctype
		return self

	def trigger(
		self, trigger_type: str, event: str | None = None, condition: str | None = None
	) -> "RuleBuilder":
		self._trigger_type = trigger_type
		if event is not None:
			self._trigger_event = event
		if condition is not None:
			self._trigger_condition = condition
		return self

	def active(self, is_active=1):
		self._is_active = is_active
		return self

	def subrule(self, exposed=1):
		self._exposed_as_subrule = exposed
		self._trigger_type = "Callable Event"
		self._trigger_event = None  # type: ignore[assignment]
		return self

	def add_action(self, **kwargs):
		action = {
			"action_id": kwargs.get("action_id") or f"action_{len(self._actions) + 1}",
			"action_type": kwargs.get("action_type"),
			"action_label": kwargs.get("action_label") or kwargs.get("action_id"),
			"is_enabled": 1,
			"next_step_if_true": kwargs.get("next_step_if_true"),
			"next_step_if_false": kwargs.get("next_step_if_false"),
			"config": kwargs.get("config", "{}"),
			"operation": kwargs.get("operation"),
			"process_name": kwargs.get("process_name"),
			"return_variable": kwargs.get("return_variable"),
			"return_type": kwargs.get("return_type"),
			"mutation_mode": kwargs.get("mutation_mode"),
			"condition_json": kwargs.get("condition_json"),
			"value_template": kwargs.get("value_template"),
			"reference_doctype": kwargs.get("reference_doctype"),
			"rule": kwargs.get("rule"),
		}
		self._actions.append(action)
		return self

	def entry_action(self, label="Start", next_step=None):
		return self.add_action(
			action_id="root", action_type="Entry Action", action_label=label, next_step_if_true=next_step
		)

	def stop(self, label="Stop", operation="Success", action_id=None):
		return self.add_action(
			action_id=action_id, action_type="Stop", action_label=label, operation=operation
		)

	def condition(self, label, condition_expr, next_true=None, next_false=None, action_id=None):
		# Very basic conversion if it's a string, otherwise assume it's JSON
		if isinstance(condition_expr, str):
			# This is a simplification. Real engine uses condition_json or compiled_expression.
			# For builder, we might want to support both.
			pass

		return self.add_action(
			action_id=action_id,
			action_type="Condition",
			action_label=label,
			condition_json=condition_expr if not isinstance(condition_expr, str) else None,
			# If we want to support raw python strings, we might need another field or handle it in engine
			next_step_if_true=next_true,
			next_step_if_false=next_false,
		)

	def assignment(self, label, assignments, next_step=None, action_id=None):
		return self.add_action(
			action_id=action_id,
			action_type="Assignment",
			action_label=label,
			config=json.dumps(assignments) if isinstance(assignments, list) else assignments,
			next_step_if_true=next_step,
		)

	def sub_rule_call(self, label, target_rule, next_step=None, action_id=None):
		return self.add_action(
			action_id=action_id,
			action_type="Sub-Rule",
			action_label=label,
			rule=target_rule,
			next_step_if_true=next_step,
		)

	def build(self, do_not_save=False):
		from flexirule.ruleflow.tests.test_doctypes import setup_test_doctypes

		setup_test_doctypes()

		if frappe.db.exists("Rule", self.rule_name):
			frappe.delete_doc("Rule", self.rule_name, force=1)

		rule_dict = {
			"doctype": "Rule",
			"rule_name": self.rule_name,
			"document_type": self._document_type,
			"trigger_type": self._trigger_type,
			"trigger_event": self._trigger_event,
			"is_active": self._is_active,
			"exposed_as_subrule": self._exposed_as_subrule,
			"priority": self._priority,
			"max_execution_time": self._max_execution_time,
			"trigger_condition": self._trigger_condition,
			"actions": self._actions,
		}
		rule = frappe.get_doc(rule_dict)
		if not do_not_save:
			rule.insert(ignore_permissions=True)
			RuleCoordinator.clear_cache()
		return rule

	def add_block(self, block_func, **kwargs):
		"""Allows adding a pre-defined set of actions."""
		block_func(self, **kwargs)
		return self
