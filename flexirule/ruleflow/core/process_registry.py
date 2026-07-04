# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Process Registry helpers.

Centralizes Process + Process Operation metadata access so API, builder DTOs,
and runtime policy resolution share one source of truth.
"""

from __future__ import annotations

from typing import Any, cast

import frappe

from flexirule.ruleflow.core.contracts import ACTION_TYPE_CONTRACT
from flexirule.ruleflow.core.process_contract_v2 import resolve_process_operation_contract_v2


def _existing_fields(doctype: str, candidates: list[str]) -> list[str]:
	"""Return fields that are present in both meta and DB schema."""
	meta = frappe.get_meta(doctype)
	return [
		fieldname
		for fieldname in candidates
		if fieldname == "name"
		or (
			(meta.has_field(fieldname) or fieldname in {"parent", "parenttype", "parentfield", "idx"})
			and frappe.db.has_column(doctype, fieldname)
		)
	]


def _get_process_fields() -> list[str]:
	return _existing_fields("Process", ["name", "process_name", "module", "is_standard", "status"])


def _get_process_operation_fields() -> list[str]:
	fields = _existing_fields(
		"Process Operation",
		[
			"parent",
			"func_name",
			"label",
			"description",
			"enabled",
			"visible_in_builder",
			"icon",
			"color",
			"writes_to",
			"is_terminal",
			"requires_doc",
			"can_stop_save",
			"allows_async",
			"transactional",
			"has_side_effect",
			"for_doctype",
			"doctype_filters",
			"reads_vars",
			"writes_vars",
			"config_schema",
			"output_schema",
			"action_overrides",
			"idx",
		],
	)
	if "parent" not in fields:
		fields = ["parent", *fields]
	return fields


def get_process_registry(
	include_disabled: bool = False,
	include_hidden: bool = True,
) -> list[dict[str, Any]]:
	"""Return Process docs with attached operations."""
	process_rows = frappe.get_all(
		"Process",
		fields=_get_process_fields(),
		order_by="modified desc",
		ignore_permissions=True,
	)
	process_map: dict[str, dict[str, Any]] = {row["name"]: {**row, "operations": []} for row in process_rows}

	if not process_map:
		return []

	operation_rows = frappe.get_all(
		"Process Operation",
		fields=_get_process_operation_fields(),
		filters={"parent": ["in", list(process_map.keys())]},
		order_by="parent asc, idx asc",
		ignore_permissions=True,
	)

	for row in operation_rows:
		if not include_disabled and row.get("enabled", 1) == 0:
			continue
		if not include_hidden and row.get("visible_in_builder", 1) == 0:
			continue
		parent = row.get("parent")
		if parent in process_map:
			process_map[parent]["operations"].append(row)

	return [p for p in process_map.values() if p["operations"]]


def get_process_operation_policies(
	process_registry: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
	"""Build per-process operation policy map."""
	process_registry = process_registry or get_process_registry(include_disabled=True, include_hidden=True)
	policies: dict[str, dict[str, dict[str, Any]]] = {}
	for process in process_registry:
		process_name = process.get("name")
		for operation in process.get("operations") or []:
			func_name = operation.get("func_name")
			if not process_name or not func_name:
				continue
			try:
				contract_v2 = resolve_process_operation_contract_v2(
					process_name,
					func_name,
					operation,
					strict=True,
				)
				policies.setdefault(process_name, {})[func_name] = contract_v2.get("policy") or {}
			except Exception as e:
				frappe.logger().warning(f"Failed to load policy for {process_name}.{func_name}: {e}")
	return policies


def get_process_operation_registry_v2(
	process_registry: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, dict[str, Any]]]:
	"""Return strict contract_v2 registry grouped by process/operation."""
	process_registry = process_registry or get_process_registry(include_disabled=True, include_hidden=True)
	registry: dict[str, dict[str, dict[str, Any]]] = {}
	for process in process_registry:
		process_name = process.get("name")
		for operation in process.get("operations") or []:
			func_name = operation.get("func_name")
			if not process_name or not func_name:
				continue
			try:
				contract_v2 = resolve_process_operation_contract_v2(
					process_name,
					func_name,
					operation,
					strict=True,
				)
				registry.setdefault(process_name, {})[func_name] = contract_v2
			except Exception as e:
				frappe.logger().warning(f"Failed to load contract for {process_name}.{func_name}: {e}")
	return registry


def build_operation_registry(
	process_registry: list[dict[str, Any]] | None = None,
	process_operation_policies: dict[str, dict[str, dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
	"""Build unified operation registry for all action types + process ops."""
	process_registry = process_registry or get_process_registry(include_disabled=False, include_hidden=False)
	process_operation_policies = process_operation_policies or get_process_operation_policies(
		process_registry
	)

	operation_registry: list[dict[str, Any]] = []
	seen_ops: set[tuple[str, str, str]] = set()

	def _append_operation(
		action_type: str,
		value: str,
		label: str | None = None,
		process_name: str | None = None,
		policy: dict[str, Any] | None = None,
	):
		if not value:
			return
		key = (action_type, process_name or "", value)
		if key in seen_ops:
			return
		seen_ops.add(key)
		operation_registry.append(
			{
				"action_type": action_type,
				"value": value,
				"label": label or value,
				"process_name": process_name,
				"policy": policy or {},
			}
		)

	for action_type, action_contract in cast(dict[str, dict[str, Any]], ACTION_TYPE_CONTRACT).items():
		for operation_name in action_contract.get("operation_options", []) or []:
			op_policy = (action_contract.get("operation_policies", {}) or {}).get(operation_name, {})
			_append_operation(
				action_type=action_type,
				value=operation_name,
				label=operation_name,
				process_name=None,
				policy=op_policy,
			)

	for process in process_registry:
		process_name = process.get("name")
		for operation in process.get("operations") or []:
			func_name = operation.get("func_name")
			if not process_name or not func_name:
				continue
			if operation.get("enabled", 1) == 0 or operation.get("visible_in_builder", 1) == 0:
				continue
			_append_operation(
				action_type="Process",
				value=func_name,
				label=operation.get("label") or func_name,
				process_name=process_name,
				policy=process_operation_policies.get(process_name, {}).get(func_name, {}),
			)

	return operation_registry


def find_process_operation(process_name: str, func_name: str) -> dict[str, Any] | None:
	"""Find one operation row by process + function name."""
	if not process_name or not func_name:
		return None
	rows = frappe.get_all(
		"Process Operation",
		fields=_get_process_operation_fields(),
		filters={"parent": process_name, "func_name": func_name},
		limit=1,
		ignore_permissions=True,
	)
	return rows[0] if rows else None
