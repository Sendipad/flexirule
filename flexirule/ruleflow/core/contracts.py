# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Facade for FlexiRule Action Contracts.

Delegates to HandlerRegistry (strategy-owned contracts) and contract_utils.py/contract_dto.py.
Maintains absolute backward compatibility for all imports and function signatures.
"""

from __future__ import annotations

import json
from typing import Any

from flexirule.ruleflow.core.action_handlers import HandlerRegistry
from flexirule.ruleflow.core.contract_dto import get_contract_dto
from flexirule.ruleflow.core.contract_utils import (
	MUTATION_MODE_OPTIONS,
	RELEASE_DISABLED_ACTION_TYPES,
	RETURN_TYPE_OPTIONS,
	RUNTIME_FIELD_ALIASES,
	TRIGGER_TYPE_CONTRACT,
	apply_field_overrides,
	get_process_operation_overrides,
	get_trigger_type_contract,
	is_release_disabled_action,
	normalize_action_type,
)


def get_contract(action_type: str) -> dict:
	"""Get contract for an action type, with defaults for unknown types."""
	return HandlerRegistry.get_action_contract(action_type)


def is_terminal_action(action_type: str) -> bool:
	"""Check if action type terminates the flow."""
	return get_contract(action_type).get("terminal", False)


def get_required_fields(action_type: str) -> list:
	"""Get required fields for an action type."""
	return get_contract(action_type).get("required_fields", [])


def get_operation_contract(operation: str, process_operation: dict | None = None) -> dict:
	"""Get contract for a known operation."""
	return HandlerRegistry.get_operation_contract(operation, process_operation)


def get_operation_field_overrides(
	operation: str, doctype: str, process_operation: dict | None = None
) -> list:
	"""Get field overrides for a specific operation and doctype."""
	contract = get_operation_contract(operation, process_operation)
	overrides = list(contract.get(doctype, []))

	# Process operations can contribute generic field-level overrides through metadata.
	if doctype == "Rule Action" and isinstance(process_operation, dict):
		overrides_meta = get_process_operation_overrides(process_operation)
		for fieldname, field_config in (overrides_meta.get("fields") or {}).items():
			if not fieldname or not isinstance(field_config, dict):
				continue
			overrides.append({"fieldname": fieldname, **field_config})

	return overrides


def infer_process_operation_policy(process_operation: dict | None) -> dict:
	"""Infer runtime/UI policy from Process Operation metadata."""
	policy: dict = {}
	if not isinstance(process_operation, dict):
		return policy

	process_overrides = get_process_operation_overrides(process_operation)

	writes_to = (process_operation.get("writes_to") or "None").strip()
	if writes_to == "Document":
		policy["allowed_mutations"] = [
			"Set Doc Field",
			"Update Doc Field",
			"Set Context Variable",
			"Update Context Variable",
		]
	elif writes_to == "Database":
		policy["allowed_mutations"] = [
			"Set Context Variable",
			"Update Context Variable",
			"Batch Database Set",
		]
	elif writes_to == "Context":
		policy["allowed_mutations"] = [
			"Set Context Variable",
			"Update Context Variable",
			"Append to Context Variable",
		]
	else:
		policy["allowed_mutations"] = [
			"Set Context Variable",
			"Update Context Variable",
		]

	output_schema = process_operation.get("output_schema")
	allowed_return_types = []
	default_return_type = None
	field_labels = {}
	show_return_type = True
	require_return_type = False
	require_return_variable = False

	if output_schema:
		try:
			schema = json.loads(output_schema) if isinstance(output_schema, str) else output_schema
			if isinstance(schema, dict):
				schema_type = schema.get("type")
				if schema_type == "array":
					allowed_return_types = ["List of Records", "List of Values"]
					default_return_type = "List of Records"
					field_labels["return_type"] = "Collection Output Type"
					show_return_type = True
					require_return_type = False
				elif schema_type == "boolean":
					allowed_return_types = ["Yes / No"]
					default_return_type = "Yes / No"
					field_labels["return_type"] = "Boolean Output Type"
					show_return_type = False
					require_return_type = False
				elif schema_type == "object":
					allowed_return_types = ["Single Record", "Full Document"]
					default_return_type = "Single Record"
					field_labels["return_type"] = "Record Output Type"
					show_return_type = True
					require_return_type = False
				elif schema_type in ("string", "number", "integer"):
					allowed_return_types = ["List of Values"]
					default_return_type = "List of Values"
					field_labels["return_type"] = "Value Output Type"
					show_return_type = False
					require_return_type = False
		except Exception:
			pass

	if writes_to == "Context":
		require_return_variable = True

	writes_vars = process_operation.get("writes_vars")
	try:
		parsed_writes_vars = json.loads(writes_vars) if isinstance(writes_vars, str) else writes_vars
		if isinstance(parsed_writes_vars, list) and parsed_writes_vars:
			require_return_variable = True
	except Exception:
		pass

	if output_schema:
		require_return_variable = True

	if not allowed_return_types:
		allowed_return_types = [
			"Yes / No",
			"Single Record",
			"List of Values",
			"List of Records",
			"Full Document",
		]
		default_return_type = "Single Record"
		field_labels["return_type"] = "Result Type"
		show_return_type = True
		require_return_type = False

	policy["allowed_return_types"] = allowed_return_types
	policy["default_return_type"] = default_return_type
	policy["show_return_type"] = show_return_type
	policy["require_return_type"] = require_return_type
	policy["require_return_variable"] = require_return_variable
	if field_labels:
		policy["field_labels"] = field_labels

	override_policy = process_overrides.get("policy") or {}
	if isinstance(override_policy, dict):
		if isinstance(override_policy.get("field_labels"), dict):
			policy["field_labels"] = {
				**policy.get("field_labels", {}),
				**override_policy.get("field_labels", {}),
			}
		for key, value in override_policy.items():
			if key == "field_labels":
				continue
			policy[key] = value

	return policy


def get_effective_action_policy(
	action_type: str | None,
	operation: str | None = None,
	process_operation: dict | None = None,
) -> dict:
	"""Resolve action policy including operation-level overrides."""
	return HandlerRegistry.get_effective_policy(action_type, operation, process_operation)


# Module-level property getters using __getattr__ for 100% backward compatibility
def __getattr__(name: str) -> Any:
	if name == "ACTION_TYPE_CONTRACT":
		return HandlerRegistry.get_all_contracts()
	if name == "OPERATION_CONTRACTS":
		return HandlerRegistry.get_all_operation_contracts()
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
