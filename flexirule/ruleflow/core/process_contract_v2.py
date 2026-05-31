# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

import frappe
from frappe import _

PROCESS_CONTRACT_V2_VERSION = 2
SUPPORTED_PROCESS_ADAPTER_KEYS = ("validate", "transform", "lookup", "dedupe", "batch")

DEFAULT_ALLOWED_RETURN_TYPES = [
	"Yes / No",
	"Single Record",
	"List of Values",
	"List of Records",
	"Full Document",
]

DEFAULT_ALLOWED_MUTATIONS_BY_WRITE_TARGET = {
	"None": ["Set Context Variable", "Update Context Variable"],
	"Context": ["Set Context Variable", "Update Context Variable", "Append to Context Variable"],
	"Document": ["Set Doc Field", "Update Doc Field", "Set Context Variable", "Update Context Variable"],
	"Database": ["Set Context Variable", "Update Context Variable", "Batch Database Set"],
}


@dataclass
class ExecutionContext:
	doc: Any = None
	vars: dict[str, Any] = field(default_factory=dict)
	event_name: str | None = None
	is_async: bool = False
	dry_run: bool = False
	raw_context: dict[str, Any] = field(default_factory=dict)

	@classmethod
	def from_runtime_context(cls, context: dict[str, Any] | None) -> ExecutionContext:
		context = context or {}
		return cls(
			doc=context.get("doc"),
			vars=context.get("vars") or {},
			event_name=context.get("event_name"),
			is_async=bool(context.get("is_async")),
			dry_run=bool(context.get("dry_run")),
			raw_context=context,
		)


@dataclass
class MutationIntent:
	mutation_mode: str
	target: str
	value: Any = None


@dataclass
class OperationResult:
	status: Literal["success", "failed", "skipped"] = "success"
	data: Any = None
	mutations: list[MutationIntent] = field(default_factory=list)
	errors: list[str] = field(default_factory=list)
	warnings: list[str] = field(default_factory=list)
	metrics: dict[str, Any] = field(default_factory=dict)

	def as_dict(self) -> dict[str, Any]:
		return {
			"status": self.status,
			"data": self.data,
			"mutations": [
				{
					"mutation_mode": mutation.mutation_mode,
					"target": mutation.target,
					"value": mutation.value,
				}
				for mutation in self.mutations
			],
			"errors": list(self.errors),
			"warnings": list(self.warnings),
			"metrics": dict(self.metrics),
		}


@dataclass
class OperationInvocation:
	operation_key: str
	adapter_key: str
	process_name: str
	operation_name: str
	config: dict[str, Any]
	process_operation: dict[str, Any]
	config_schema: dict[str, Any]
	result_schema: dict[str, Any]
	capabilities: dict[str, Any]
	policy: dict[str, Any]
	return_type: str | None = None
	return_variable: str | None = None
	action_id: str | None = None
	context: ExecutionContext = field(default_factory=ExecutionContext)


def parse_json_object(value: Any) -> dict[str, Any]:
	if isinstance(value, dict):
		return value
	if isinstance(value, str) and value.strip():
		try:
			parsed = json.loads(value)
			return parsed if isinstance(parsed, dict) else {}
		except Exception:
			return {}
	return {}


def _parse_json_schema(value: Any, label: str) -> dict[str, Any]:
	if isinstance(value, dict):
		return value
	if isinstance(value, str) and value.strip():
		try:
			parsed = json.loads(value)
		except Exception as exc:
			raise frappe.ValidationError(_("{0} must be valid JSON: {1}").format(label, str(exc)))
		if isinstance(parsed, dict):
			return parsed
	raise frappe.ValidationError(_("{0} must be a JSON object schema").format(label))


def _normalize_capabilities(
	process_operation: dict[str, Any], capabilities: dict[str, Any]
) -> dict[str, Any]:
	normalized = {
		"requires_doc": bool(process_operation.get("requires_doc")),
		"writes_to": process_operation.get("writes_to") or "None",
		"allows_async": bool(process_operation.get("allows_async")),
		"transactional": bool(process_operation.get("transactional")),
		"can_stop_save": bool(process_operation.get("can_stop_save")),
		"has_side_effect": bool(process_operation.get("has_side_effect")),
	}
	for key in (
		"requires_doc",
		"writes_to",
		"allows_async",
		"transactional",
		"can_stop_save",
		"has_side_effect",
	):
		if key in capabilities:
			normalized[key] = capabilities[key]
	return normalized


def _normalize_policy(
	policy: dict[str, Any],
	capabilities: dict[str, Any],
	process_operation: dict[str, Any],
) -> dict[str, Any]:
	writes_to = str(capabilities.get("writes_to") or process_operation.get("writes_to") or "None")
	allowed_mutations = policy.get("allowed_mutations")
	if not isinstance(allowed_mutations, list) or not allowed_mutations:
		allowed_mutations = DEFAULT_ALLOWED_MUTATIONS_BY_WRITE_TARGET.get(
			writes_to, DEFAULT_ALLOWED_MUTATIONS_BY_WRITE_TARGET["None"]
		)
	allowed_mutations_list: list[Any] = list(allowed_mutations)

	allowed_return_types = policy.get("allowed_return_types")
	if not isinstance(allowed_return_types, list) or not allowed_return_types:
		allowed_return_types = list(DEFAULT_ALLOWED_RETURN_TYPES)
	allowed_return_types_list: list[Any] = list(allowed_return_types)

	allowed_mutation_targets_raw = policy.get("allowed_mutation_targets")
	allowed_mutation_targets_list: list[Any]
	if isinstance(allowed_mutation_targets_raw, list):
		allowed_mutation_targets_list = list(allowed_mutation_targets_raw)
	else:
		allowed_mutation_targets_list = []
	if not allowed_mutation_targets_list:
		allowed_mutation_targets_list = list(allowed_mutations_list)

	normalized = {
		"allowed_mutations": allowed_mutations_list,
		"allowed_return_types": allowed_return_types_list,
		"default_return_type": policy.get("default_return_type"),
		"require_return_variable": bool(policy.get("require_return_variable")),
		"require_return_type": bool(policy.get("require_return_type")),
		"allowed_mutation_targets": allowed_mutation_targets_list,
	}

	return normalized


def resolve_process_operation_contract_v2(
	process_name: str,
	operation_name: str,
	process_operation: dict[str, Any],
	*,
	strict: bool = True,
) -> dict[str, Any]:
	"""Resolve one Process Operation into canonical declarative contract v2."""
	if not isinstance(process_operation, dict):
		raise frappe.ValidationError(
			_("Invalid Process Operation metadata for {0}.{1}").format(process_name, operation_name)
		)

	overrides = parse_json_object(process_operation.get("action_overrides"))
	contract_v2 = overrides.get("contract_v2")
	if not isinstance(contract_v2, dict):
		if strict:
			raise frappe.ValidationError(
				_(
					"Process operation '{0}.{1}' must define action_overrides.contract_v2 "
					"with adapter_key, capabilities, policy, config_schema, and result_schema"
				).format(process_name, operation_name)
			)
		contract_v2 = {}

	adapter_key = contract_v2.get("adapter_key")
	if not adapter_key or not isinstance(adapter_key, str):
		raise frappe.ValidationError(
			_("Process operation '{0}.{1}' must provide a valid string adapter_key").format(
				process_name, operation_name
			)
		)
	if adapter_key not in SUPPORTED_PROCESS_ADAPTER_KEYS:
		raise frappe.ValidationError(
			_("Process operation '{0}.{1}' uses unsupported adapter_key '{2}'").format(
				process_name, operation_name, adapter_key
			)
		)

	config_schema = contract_v2.get("config_schema", process_operation.get("config_schema"))
	result_schema = contract_v2.get("result_schema", process_operation.get("output_schema"))
	config_schema = _parse_json_schema(
		config_schema, _("Config schema for {0}.{1}").format(process_name, operation_name)
	)
	result_schema = _parse_json_schema(
		result_schema, _("Result schema for {0}.{1}").format(process_name, operation_name)
	)

	capabilities = contract_v2.get("capabilities")
	if capabilities is None:
		capabilities = {}
	if not isinstance(capabilities, dict):
		raise frappe.ValidationError(
			_("Process operation '{0}.{1}' contract_v2.capabilities must be an object").format(
				process_name, operation_name
			)
		)

	policy = contract_v2.get("policy")
	if policy is None:
		policy = {}
	if not isinstance(policy, dict):
		raise frappe.ValidationError(
			_("Process operation '{0}.{1}' contract_v2.policy must be an object").format(
				process_name, operation_name
			)
		)

	capabilities = _normalize_capabilities(process_operation, capabilities)
	policy = _normalize_policy(policy, capabilities, process_operation)

	return {
		"version": PROCESS_CONTRACT_V2_VERSION,
		"operation_key": f"{process_name}.{operation_name}",
		"adapter_key": adapter_key,
		"config_schema": config_schema,
		"result_schema": result_schema,
		"capabilities": capabilities,
		"policy": policy,
	}
