# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Process Action Handler.

Executes a Process operation with configuration, input/output mapping,
and retry logic.
"""

import frappe
from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry
from flexirule.ruleflow.core.action_handlers.base_contract import (
	ActionContract,
	OperationContract,
)
from flexirule.ruleflow.core.exceptions import MethodExecutionError
from flexirule.ruleflow.core.process_runtime_v2 import ProcessOperationExecutor
from flexirule.ruleflow.utils.mapping import apply_input_mapping


class ProcessHandler(ActionHandler):
	"""Handler for Process action type."""

	action_type = "Process"
	executor = ProcessOperationExecutor()

	@classmethod
	def get_action_contract(cls):
		return ActionContract(
			action_type="Process",
			required_fields=["process_name", "operation"],
			has_next_true=True,
			has_next_false=False,
			terminal=False,
			css={"icon": "fa fa-cog", "color": "#8b5cf6"},
			dynamic_fields=True,
			field_labels={
				"operation": "Process Operation",
				"mutation_mode": "Result Handling",
				"return_type": "Result Type",
			},
			allowed_mutations=[
				"Set Context Variable",
				"Update Context Variable",
				"Append to Context Variable",
				"Set Doc Field",
				"Update Doc Field",
				"Batch Database Set",
			],
			allowed_return_types=[
				"Yes / No",
				"Single Record",
				"List of Values",
				"List of Records",
				"Full Document",
			],
			show_return_type=True,
			node_type="process",
			category="Processes",
			configurable=True,
			config_component="ProcessConfig",
		)

	@classmethod
	def get_runtime_policy(cls, operation=None, process_operation=None) -> dict:
		"""Resolve runtime policy for Process including metadata-driven inference."""
		from flexirule.ruleflow.core.contracts import infer_process_operation_policy

		# Base policy from contract
		policy = super().get_runtime_policy(operation, process_operation)

		# Complex resolution for Process V2
		if operation and process_operation:
			from flexirule.ruleflow.core.process_contract_v2 import (
				resolve_process_operation_contract_v2,
			)

			process_name = (
				process_operation.get("parent") if isinstance(process_operation, dict) else None
			)
			if process_name:
				contract_v2 = resolve_process_operation_contract_v2(
					process_name,
					operation,
					process_operation,
					strict=True,
				)
				op_policy = contract_v2.get("policy") or {}
				for key, value in op_policy.items():
					if value is not None:
						if key in ("allowed_mutations", "allowed_return_types"):
							policy[key] = list(value)
						elif key == "field_labels":
							policy["field_labels"].update(value)
						else:
							policy[key] = value
		elif process_operation:
			dynamic_policy = infer_process_operation_policy(process_operation)
			for key, value in dynamic_policy.items():
				if value is not None:
					if key in ("allowed_mutations", "allowed_return_types"):
						policy[key] = list(value)
					elif key == "field_labels":
						policy["field_labels"].update(value)
					else:
						policy[key] = value

		return policy

	def execute(self, action, context, engine):
		"""
		Execute a Process operation.

		Process actions are the primary way to execute business logic.
		They support:
		- Input mapping (context vars -> config)
		- Output mapping (result -> context vars)
		- Retry logic with exponential backoff
		- Timeout protection
		- Savepoint transactions

		Returns:
		    Tuple of (operation_result, next_action_id)
		"""
		process_name = getattr(action, "process_name", None)

		if not process_name:
			engine._log(
				"WARNING",
				_("Process action {0} has no process_name set").format(action.action_label),
			)
			return None, getattr(action, "next_step_if_true", None)

		# Parse configuration
		config = engine._get_action_config(action)

		# Apply Input Mapping (Context -> Config)
		action_config = frappe.parse_json(getattr(action, "config", "{}") or "{}")
		if action_config.get("input_mapping"):
			config = apply_input_mapping(context, action_config.get("input_mapping"), config)

		# Execute through centralized declarative runtime v2 path
		# (adapter registry + strict config/result schemas + policy gate).
		result = self.executor.execute(action, context, config)

		return result, getattr(action, "next_step_if_true", None)

	def validate(self, action, context):
		"""Validate process action configuration."""
		errors = []
		if not getattr(action, "process_name", None):
			errors.append(_("Process action '{0}' requires a process_name").format(action.action_label))
		return errors


# Register the handler
HandlerRegistry.register(ProcessHandler())
