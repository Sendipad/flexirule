# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import hashlib
import json
from typing import Any

import frappe

from flexirule.ruleflow.core.contracts import normalize_action_type

CACHE_VERSION = 1
CACHE_KEY_PREFIX = "flexirule_action_plan_v1"
LOCAL_CACHE_KEY = "flexirule_action_plan_cache"


def get_rule_action_plan(rule_doc) -> dict[str, Any]:
	"""Get compiled per-action execution plan for a rule using local + Redis cache."""
	rule_hash = get_rule_version_hash(rule_doc)
	plan_key = _plan_key(rule_doc.name, rule_hash)

	local_cache = _get_local_cache()
	if plan_key in local_cache:
		return local_cache[plan_key]

	plan = None
	try:
		cached = frappe.cache.get_value(plan_key)
		if _is_valid_plan(cached):
			plan = cached
	except Exception:
		plan = None

	if plan is None:
		plan = _compile_rule_action_plan(rule_doc, rule_hash)
		try:
			frappe.cache.set_value(plan_key, plan, expires_in_sec=24 * 60 * 60)
		except Exception:
			pass

	local_cache[plan_key] = plan
	return plan


def get_action_plan(rule_doc, action) -> dict[str, Any]:
	"""Resolve compiled action plan for a specific action row."""
	plan = get_rule_action_plan(rule_doc)
	actions = plan.get("actions", {})
	action_key = _action_key(action)
	return actions.get(action_key, {})


def clear_rule_action_plan_cache(rule_name: str | None = None) -> None:
	"""Clear request-local compiled action plan cache. Optionally clear one rule family in Redis."""
	if hasattr(frappe.local, LOCAL_CACHE_KEY):
		delattr(frappe.local, LOCAL_CACHE_KEY)

	if not rule_name:
		return

	try:
		pattern = f"{CACHE_KEY_PREFIX}:{rule_name}:*"
		frappe.cache.delete_keys(pattern)
		if hasattr(frappe.cache, "make_key"):
			frappe.cache.delete_keys(frappe.cache.make_key(pattern))
	except Exception:
		pass


def get_rule_version_hash(rule_doc) -> str:
	"""Compute deterministic hash for the execution-relevant rule payload."""
	actions = []
	for row in getattr(rule_doc, "actions", []) or []:
		actions.append(
			{
				"name": getattr(row, "name", None),
				"action_id": getattr(row, "action_id", None),
				"action_type": normalize_action_type(getattr(row, "action_type", None)),
				"operation": getattr(row, "operation", None),
				"config": getattr(row, "config", None),
				"value_template": getattr(row, "value_template", None),
				"reference_doctype": getattr(row, "reference_doctype", None),
				"reference_docname": getattr(row, "reference_docname", None),
				"is_async": getattr(row, "is_async", None),
			}
		)

	payload = {
		"name": getattr(rule_doc, "name", None),
		"version": getattr(rule_doc, "version", None),
		"modified": str(getattr(rule_doc, "modified", None) or ""),
		"actions": actions,
	}
	raw = json.dumps(payload, sort_keys=True, default=str)
	return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _compile_rule_action_plan(rule_doc, rule_hash: str) -> dict[str, Any]:
	actions: dict[str, dict[str, Any]] = {}

	for action in getattr(rule_doc, "actions", []) or []:
		action_type = normalize_action_type(getattr(action, "action_type", None))
		compiled: dict[str, Any] = {}

		if action_type == "Assignment":
			compiled = _compile_assignment_action(action)
		elif action_type == "Notify":
			compiled = _compile_notify_action(action)
		elif action_type == "Document Action":
			compiled = _compile_document_action(action)

		if compiled:
			actions[_action_key(action)] = compiled

	return {
		"cache_version": CACHE_VERSION,
		"rule_name": getattr(rule_doc, "name", None),
		"rule_hash": rule_hash,
		"actions": actions,
	}


def _compile_assignment_action(action) -> dict[str, Any]:
	from flexirule.ruleflow.core.action_handlers.assignment import AssignmentHandler

	config_key = getattr(action, "config", "[]") or "[]"
	compiled_plan_getter = getattr(AssignmentHandler, "_get_compiled_plan", None)
	if callable(compiled_plan_getter):
		compiled_rows = compiled_plan_getter(str(config_key))
	else:
		# Safe fallback for mixed-version/runtime import edge-cases.
		try:
			rows = json.loads(str(config_key) or "[]")
		except Exception:
			rows = []
		if not isinstance(rows, list):
			rows = []
		compiled_rows = tuple(row for row in rows if isinstance(row, dict))
	return {"action_type": "Assignment", "rows": list(compiled_rows)}


def _compile_notify_action(action) -> dict[str, Any]:
	from flexirule.ruleflow.core.action_handlers.simple_actions import NotifyHandler

	handler = NotifyHandler()
	config = _parse_json(getattr(action, "config", None), fallback={})
	mode = handler._normalize_mode(getattr(action, "operation", NotifyHandler.MODE_TOAST))

	return {
		"action_type": "Notify",
		"mode": mode,
		"message_spec": _compile_template_spec(getattr(action, "value_template", "") or ""),
		"subject_spec": _compile_template_spec(config.get("subject")),
		"recipients_spec": _compile_value_spec(config.get("recipients")),
		"for_user_spec": _compile_value_spec(config.get("for_user")),
		"recipient_spec": _compile_value_spec(config.get("recipient")),
		"provider": config.get("provider"),
		"attach_doc": bool(config.get("attach_doc")),
	}


def _compile_document_action(action) -> dict[str, Any]:
	from flexirule.ruleflow.core.action_handlers.create_doc import DocumentActionHandler

	handler = DocumentActionHandler()
	config = handler._parse_config(getattr(action, "config", None))
	input_mapping = config.get("input_mapping")

	return {
		"action_type": "Document Action",
		"mode": getattr(action, "operation", None),
		"reference_doctype": getattr(action, "reference_doctype", None),
		"reference_docname": getattr(action, "reference_docname", None),
		"is_async": bool(getattr(action, "is_async", 0)),
		"config": config,
		"input_mapping": input_mapping,
		"has_input_mapping": bool(input_mapping),
		"docname_spec": _compile_expression_spec(config.get("docname_expression")),
	}


def _compile_template_spec(value: Any) -> dict[str, Any]:
	if value is None:
		return {"source": "none", "value": ""}
	if not isinstance(value, str):
		return {"source": "literal", "value": value}
	text = value or ""
	if "{{" in text or "{%" in text:
		return {"source": "jinja", "value": text}
	return {"source": "literal", "value": text}


def _compile_value_spec(value: Any) -> dict[str, Any]:
	if isinstance(value, list):
		return {"source": "list", "items": [_compile_value_spec(v) for v in value]}
	if isinstance(value, str):
		if "{{" in value or "{%" in value:
			return {"source": "jinja", "value": value}
		return {"source": "literal", "value": value}
	return {"source": "literal", "value": value}


def _compile_expression_spec(expr: Any) -> dict[str, Any]:
	if isinstance(expr, str) and expr.strip():
		return {"source": "expression", "value": expr.strip()}
	return {"source": "none", "value": None}


def _parse_json(value: Any, fallback: Any):
	if not value:
		return fallback
	if isinstance(value, dict):
		return value
	try:
		return json.loads(value)
	except Exception:
		return fallback


def _action_key(action) -> str:
	return str(getattr(action, "name", None) or getattr(action, "action_id", None) or "")


def _plan_key(rule_name: str, rule_hash: str) -> str:
	return f"{CACHE_KEY_PREFIX}:{rule_name}:{rule_hash}"


def _get_local_cache() -> dict[str, Any]:
	cache = getattr(frappe.local, LOCAL_CACHE_KEY, None)
	if isinstance(cache, dict):
		return cache
	cache = {}
	setattr(frappe.local, LOCAL_CACHE_KEY, cache)
	return cache


def _is_valid_plan(data: Any) -> bool:
	return (
		isinstance(data, dict)
		and data.get("cache_version") == CACHE_VERSION
		and isinstance(data.get("actions"), dict)
	)
