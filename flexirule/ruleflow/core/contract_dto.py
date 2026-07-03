# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

from flexirule.ruleflow.core.contract_utils import (
	MUTATION_MODE_OPTIONS,
	RETURN_TYPE_OPTIONS,
	TRIGGER_TYPE_CONTRACT,
)


class ContractDTOBuilder:
	"""Builds the frontend-safe contract DTO from the handler registry."""

	@staticmethod
	def build() -> dict:
		from flexirule.ruleflow.core.action_handlers import HandlerRegistry

		return {
			"action_type_contract": HandlerRegistry.get_all_contracts(),
			"operation_contract": HandlerRegistry.get_all_operation_contracts(),
			"trigger_type_contract": TRIGGER_TYPE_CONTRACT,
			"runtime_field_aliases": {
				"Sub-Rule": {
					"sub_rule_name": "rule",
				},
			},
			"release_disabled_action_types": [],  # Can be extended if needed
			"return_type_options": RETURN_TYPE_OPTIONS,
			"mutation_mode_options": MUTATION_MODE_OPTIONS,
			"action_types_with_reference_context": _infer_reference_context_types(),
			"action_types_with_return_schema": _infer_return_schema_types(),
			"config_modal_types": _infer_config_modal_types(),
		}


def _infer_reference_context_types():
	"""Infer which action types use reference_doctype from their contracts."""
	from flexirule.ruleflow.core.action_handlers import HandlerRegistry

	result = set()
	for action_type, contract in HandlerRegistry.get_all_contracts().items():
		if "reference_doctype" in contract.get("required_fields", []):
			result.add(action_type)

	# Manually add those that might not have it in required_fields but use it
	# Based on legacy contracts.py: ACTION_TYPES_WITH_REFERENCE_CONTEXT = {"Query Records", "Document Action", "Process", "Assignment"}
	# Process and Assignment don't always have it in required_fields
	result.update({"Process", "Assignment"})
	return sorted(result)


def _infer_return_schema_types():
	"""Infer which action types have return schema."""
	# Based on legacy contracts.py: ACTION_TYPES_WITH_RETURN_SCHEMA = {"Process", "Query Records", "Document Action"}
	return sorted({"Process", "Query Records", "Document Action"})


def _infer_config_modal_types():
	"""Infer which action types have config modals from their contracts."""
	from flexirule.ruleflow.core.action_handlers import HandlerRegistry

	return sorted(at for at, c in HandlerRegistry.get_all_contracts().items() if c.get("configurable"))


def get_contract_dto() -> dict:
	"""API-facing function for contract DTO."""
	return ContractDTOBuilder.build()
