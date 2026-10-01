# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

import frappe
from frappe.utils import now_datetime

from flexirule.ruleflow.core.contracts import normalize_action_type
from flexirule.ruleflow.core.coordinator import RuleCoordinator
from flexirule.ruleflow.core.process_contract_v2 import resolve_process_operation_contract_v2

ARTIFACT_VERSION = 1


def compile_rule(rule_doc) -> dict[str, Any]:
	"""Build a deterministic compiled artifact for a normalized Rule document."""
	artifact: dict[str, Any] = {
		"artifact_version": ARTIFACT_VERSION,
		"rule": rule_doc.name,
		"rule_version": rule_doc.version or 1,
		"trigger": _compile_trigger(rule_doc),
		"actions": [_compile_action(action) for action in (rule_doc.actions or [])],
	}
	artifact["hash"] = hash_artifact(artifact)
	artifact["compiled_at"] = str(now_datetime())
	return artifact


def hash_artifact(artifact: Mapping[str, Any]) -> str:
	"""Return a stable hash for an artifact, excluding transient compile fields."""
	payload = {key: value for key, value in dict(artifact).items() if key not in {"hash", "compiled_at"}}
	encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
	return hashlib.sha256(encoded).hexdigest()


def serialize_artifact(artifact: Mapping[str, Any]) -> str:
	return json.dumps(artifact, sort_keys=True, default=str, indent=2)


def parse_artifact(value: str | Mapping[str, Any] | None) -> dict[str, Any] | None:
	if not value:
		return None
	if isinstance(value, Mapping):
		return dict(value)
	try:
		parsed = json.loads(value)
	except Exception:
		return None
	return parsed if isinstance(parsed, dict) else None


def _compile_trigger(rule_doc) -> dict[str, Any]:
	return {
		"trigger_type": rule_doc.trigger_type,
		"document_type": rule_doc.document_type,
		"trigger_event": rule_doc.trigger_event,
		"compiled_expression": rule_doc.compiled_expression,
		"has_trigger_condition": bool(rule_doc.trigger_condition),
		"watched_fields": _parse_field_list(rule_doc.get("watched_fields")),
		"compiled_dependencies": RuleCoordinator._extract_watched_fields(rule_doc.compiled_expression),
	}


def _compile_action(action) -> dict[str, Any]:
	action_type = normalize_action_type(action.action_type)
	config = _parse_json_value(action.get("config"))
	compiled: dict[str, Any] = {
		"action_id": action.action_id,
		"action_label": action.action_label,
		"action_type": action_type,
		"is_enabled": int(action.is_enabled or 0),
		"operation": action.operation,
		"process_name": action.process_name,
		"reference_doctype": action.reference_doctype,
		"reference_docname": action.reference_docname,
		"mutation_mode": action.mutation_mode,
		"return_variable": action.return_variable,
		"return_type": action.return_type,
		"next_step_if_true": action.next_step_if_true,
		"next_step_if_false": action.next_step_if_false,
	}

	if action_type == "Condition":
		compiled["condition"] = {"compiled_expression": action.compiled_expression}

	if action_type == "Assignment":
		compiled["assignment_plan"] = config if isinstance(config, list) else []

	if action_type == "Notify":
		compiled["template_spec"] = {
			"value_template": action.value_template,
			"config": config if isinstance(config, dict) else {},
		}

	if action_type == "Document Action":
		compiled["document_mapper_plan"] = config if isinstance(config, dict) else {}

	if action_type == "Query Records":
		if action.operation == "Query Doc":
			from flexirule.ruleflow.core.action_handlers.query_records import reconcile_query_doc_action

			reconcile_query_doc_action(action)
			config = _parse_json_value(action.get("config"))
			compiled["reference_doctype"] = action.reference_doctype
			compiled["reference_docname"] = action.reference_docname
		compiled["query_config"] = config if isinstance(config, dict) else {}

	if action_type == "Process" and action.process_name and action.operation:
		compiled["process_contract"] = _compile_process_contract(action)

	return compiled


def _compile_process_contract(action) -> dict[str, Any]:
	try:
		process = frappe.get_cached_doc("Process", action.process_name)
		process_operation = process.get_operation(action.operation)
		contract = resolve_process_operation_contract_v2(
			action.process_name,
			action.operation,
			process_operation,
			strict=True,
		)
		return {
			"process_name": action.process_name,
			"operation": action.operation,
			"policy": contract.get("policy") or {},
			"config_schema": contract.get("config_schema") or {},
			"result_schema": contract.get("result_schema") or {},
		}
	except Exception as exc:
		return {
			"process_name": action.process_name,
			"operation": action.operation,
			"error": str(exc),
		}


def _parse_json_value(value):
	if value in (None, ""):
		return None
	if isinstance(value, str):
		try:
			return json.loads(value)
		except Exception:
			return value
	return value


def _parse_field_list(value) -> list[str]:
	if not value:
		return []
	if isinstance(value, str):
		return [field.strip() for field in value.split(",") if field.strip()]
	if isinstance(value, list | tuple | set):
		return [str(field).strip() for field in value if str(field).strip()]
	return []


COMPILED_ARTIFACT_CACHE_PREFIX = "flexirule_compiled_artifact_v1"


def cache_compiled_artifact(rule_doc) -> dict[str, Any]:
	"""Compile and cache the rule artifact in Redis, returning the compiled artifact."""
	artifact = compile_rule(rule_doc)
	key = f"{COMPILED_ARTIFACT_CACHE_PREFIX}:{rule_doc.name}"
	try:
		frappe.cache.set_value(key, artifact, expires_in_sec=24 * 60 * 60)
	except Exception:
		pass
	return artifact


def get_compiled_artifact(rule_name: str) -> dict[str, Any] | None:
	"""Retrieve the compiled artifact from Redis. Recompile and cache on miss."""
	key = f"{COMPILED_ARTIFACT_CACHE_PREFIX}:{rule_name}"
	try:
		cached = frappe.cache.get_value(key)
		if cached and isinstance(cached, dict):
			return cached
	except Exception:
		pass

	# Recompile on miss
	try:
		rule_doc = frappe.get_doc("Rule", rule_name)
		return cache_compiled_artifact(rule_doc)
	except Exception:
		return None


def clear_compiled_artifact_cache(rule_name: str | None = None) -> None:
	"""Clear compiled artifact cache from Redis."""
	try:
		if rule_name:
			key = f"{COMPILED_ARTIFACT_CACHE_PREFIX}:{rule_name}"
			frappe.cache.delete_value(key)
		else:
			pattern = f"{COMPILED_ARTIFACT_CACHE_PREFIX}:*"
			frappe.cache.delete_keys(pattern)
			if hasattr(frappe.cache, "make_key"):
				frappe.cache.delete_keys(frappe.cache.make_key(pattern))
	except Exception:
		pass
