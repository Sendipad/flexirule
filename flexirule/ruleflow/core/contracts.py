# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Unified Backend/Frontend Contract for FlexiRule Action Types (Facade)

This module acts as a compatibility facade delegating to the decentralized
HandlerRegistry and contract utility modules.
"""

from __future__ import annotations

from typing import Any

from flexirule.ruleflow.core.action_handlers import HandlerRegistry
from flexirule.ruleflow.core.contract_dto import get_contract_dto
from flexirule.ruleflow.core.contract_utils import (
	MUTATION_MODE_OPTIONS,
	RETURN_TYPE_OPTIONS,
	TRIGGER_TYPE_CONTRACT,
	apply_field_overrides,
	get_trigger_type_contract,
	normalize_action_type,
)


# Injected into the module as properties via __getattr__
def __getattr__(name):
	if name == "ACTION_TYPE_CONTRACT":
		return HandlerRegistry.get_all_contracts()
	if name == "OPERATION_CONTRACTS":
		return HandlerRegistry.get_all_operation_contracts()
	if name == "ACTION_TYPES_WITH_REFERENCE_CONTEXT":
		return {"Query Records", "Document Action", "Process", "Assignment"}
	if name == "ACTION_TYPES_WITH_RETURN_SCHEMA":
		return {"Process", "Query Records", "Document Action"}
	if name == "CONFIG_MODAL_TYPES":
		return {
			"Process",
			"Condition",
			"Assignment",
			"Stop",
			"Raise Error",
			"Notify",
			"Wait",
			"Sub-Rule",
			"Query Records",
			"Document Action",
			"Loop",
		}
	if name == "RELEASE_DISABLED_ACTION_TYPES":
		return set()

	raise AttributeError(f"module {__name__} has no attribute {name}")


def get_operation_contract(operation: str, process_operation: dict | None = None) -> dict:
	"""Get contract for a known operation."""
	return HandlerRegistry.get_operation_contract(operation)


def get_operation_field_overrides(
	operation: str, doctype: str, process_operation: dict | None = None
) -> list:
	"""Get field overrides for a specific operation and doctype."""
	contract = get_operation_contract(operation, process_operation)
	overrides = list(contract.get(doctype, []))

	# Process operations can contribute generic field-level overrides through metadata.
	if doctype == "Rule Action" and isinstance(process_operation, dict):
		from flexirule.ruleflow.core.contracts import get_process_operation_overrides
		process_overrides = get_process_operation_overrides(process_operation)
		for fieldname, field_config in (process_overrides.get("fields") or {}).items():
			if not fieldname or not isinstance(field_config, dict):
				continue
			overrides.append({"fieldname": fieldname, **field_config})

	return overrides


def get_contract(action_type: str) -> dict:
	"""Get contract for an action type."""
	return HandlerRegistry.get_action_contract(action_type)


def is_terminal_action(action_type: str) -> bool:
	"""Check if action type terminates the flow"""
	return get_contract(action_type).get("terminal", False)


def get_required_fields(action_type: str) -> list:
	"""Get required fields for an action type"""
	return get_contract(action_type).get("required_fields", [])


def is_release_disabled_action(action_type: str) -> bool:
	"""Check if an action type is intentionally disabled."""
	return False


def get_effective_action_policy(
	action_type: str | None,
	operation: str | None = None,
	process_operation: dict | None = None,
) -> dict:
	"""Resolve action policy including operation-level overrides."""
	return HandlerRegistry.get_effective_policy(action_type, operation, process_operation)


def _parse_json_object(value: Any) -> dict[str, Any]:
	import json
	if isinstance(value, dict):
		return value
	if isinstance(value, str):
		try:
			parsed = json.loads(value)
			return parsed if isinstance(parsed, dict) else {}
		except Exception:
			return {}
	return {}


def get_process_operation_overrides(process_operation: dict | None = None) -> dict[str, Any]:
	"""Parse optional operation-level action overrides from Process metadata."""
	if not isinstance(process_operation, dict):
		return {}
	overrides = _parse_json_object(process_operation.get("action_overrides"))
	if not overrides:
		return {}

	policy = overrides.get("policy")
	fields = overrides.get("fields")
	return {
		"policy": policy if isinstance(policy, dict) else {},
		"fields": fields if isinstance(fields, dict) else {},
	}


def infer_process_operation_policy(process_operation: dict | None) -> dict:
	"""Infer runtime/UI policy from Process Operation metadata."""
	import json
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
