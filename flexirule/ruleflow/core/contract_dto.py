# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Contract DTO Builder.

Builds the frontend-safe contract DTO from the handler registry and contract utilities.
"""

from __future__ import annotations

import hashlib
import json

import frappe

from flexirule.ruleflow.core.action_handlers import HandlerRegistry
from flexirule.ruleflow.core.contract_utils import (
	MUTATION_MODE_OPTIONS,
	RELEASE_DISABLED_ACTION_TYPES,
	RETURN_TYPE_OPTIONS,
	RUNTIME_FIELD_ALIASES,
	TRIGGER_TYPE_CONTRACT,
)


class ContractDTOBuilder:
	"""Builds the frontend-safe contract DTO from the handler registry."""

	@staticmethod
	def build() -> dict:
		contracts = HandlerRegistry.get_all_contracts()
		operation_contracts = HandlerRegistry.get_all_operation_contracts()

		# Determine reference context types
		reference_context_types = {"Query Records", "Document Action", "Process", "Assignment"}
		# Determine return schema types
		return_schema_types = {"Process", "Query Records", "Document Action"}
		# Determine config modal types: those with configurable=True
		config_modal_types = {at for at, c in contracts.items() if c.get("configurable")}

		return {
			"action_type_contract": contracts,
			"operation_contract": operation_contracts,
			"trigger_type_contract": TRIGGER_TYPE_CONTRACT,
			"runtime_field_aliases": RUNTIME_FIELD_ALIASES,
			"release_disabled_action_types": sorted(list(RELEASE_DISABLED_ACTION_TYPES)),
			"return_type_options": RETURN_TYPE_OPTIONS,
			"mutation_mode_options": MUTATION_MODE_OPTIONS,
			"action_types_with_reference_context": sorted(list(reference_context_types)),
			"action_types_with_return_schema": sorted(list(return_schema_types)),
			"config_modal_types": sorted(list(config_modal_types)),
		}


def get_contract_dto() -> dict:
	"""Return canonical action/trigger contracts for frontend consumers."""
	from flexirule.ruleflow.core.process_registry import (
		build_operation_registry,
		get_process_operation_policies,
		get_process_operation_registry_v2,
		get_process_registry,
	)

	payload = ContractDTOBuilder.build()

	process_registry = get_process_registry(include_disabled=True, include_hidden=True)
	process_operation_policies = get_process_operation_policies(process_registry)
	process_operation_registry_v2 = get_process_operation_registry_v2(process_registry)
	operation_registry = build_operation_registry(process_registry, process_operation_policies)

	# Fetch full Action Type records for registry mapping
	action_types = frappe.get_all("Action Type", fields=["name", "category", "is_multi_mode", "description"])
	action_type_map = {
		at.name: {
			"category": at.category,
			"is_multi_mode": at.is_multi_mode,
			"description": at.description,
		}
		for at in action_types
	}

	payload.update(
		{
			"process_registry": process_registry,
			"operation_registry": operation_registry,
			"process_operation_registry_v2": process_operation_registry_v2,
			"action_type_map": action_type_map,
		}
	)

	payload["contract_version_hash"] = hashlib.sha256(
		json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
	).hexdigest()

	return payload
