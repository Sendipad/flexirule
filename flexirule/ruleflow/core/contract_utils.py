# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Contract Utilities and Constants.

Contains shared constants, trigger type contracts, field override utilities,
and action type normalization logic.
"""

from __future__ import annotations

import json
from typing import Any

# Trigger Type Contract
# Defines which fields are required, optional, or hidden for each trigger_type.
TRIGGER_TYPE_CONTRACT = {
	"DocType Event": {
		"required_fields": ["document_type", "trigger_event"],
		"optional_fields": ["trigger_condition", "compiled_expression"],
		"hidden_fields": [],
	},
	"Scheduler Event": {
		"required_fields": [],
		"optional_fields": ["document_type"],
		"hidden_fields": ["trigger_event", "trigger_condition", "compiled_expression"],
	},
	"Callable Event": {
		"required_fields": [],
		"optional_fields": ["document_type", "trigger_condition", "compiled_expression"],
		"hidden_fields": ["trigger_event"],
	},
}

RETURN_TYPE_OPTIONS = [
	"Yes / No",
	"Single Record",
	"List of Values",
	"List of Records",
	"Full Document",
]

MUTATION_MODE_OPTIONS = [
	"Set Doc Field",
	"Update Doc Field",
	"Set Context Variable",
	"Update Context Variable",
	"Append to Context Variable",
	"Batch Database Set",
]

# Aliases used by frontend
RUNTIME_FIELD_ALIASES = {
	"Sub-Rule": {
		"sub_rule_name": "rule",
	},
}

RELEASE_DISABLED_ACTION_TYPES: set[str] = set()

# Schema version — bump whenever the DTO shape changes in a breaking way.
# Stored alongside contract_version_hash in sessionStorage so the frontend
# can detect incompatible cached payloads without deserializing them.
CONTRACT_SCHEMA_VERSION = "v4"

# Per-action-type human-readable descriptions.
# These are emitted in the DTO so the frontend never needs to hard-code them.
ACTION_TYPE_DESCRIPTIONS: dict[str, str] = {
	"Entry Action": "The starting point of your rule flow. Defines when the rule is triggered.",
	"Condition": (
		"Branch your flow based on a logical condition. "
		"If true, follow the 'True' path; otherwise, follow 'False'."
	),
	"Process": (
		"Execute a specific business process or operation. "
		"Operations can interact with the database, current document, or external systems."
	),
	"Loop": "Iterate over a list of items and execute actions for each item.",
	"Stop": "Terminates the rule execution as Success or Error.",
	"Switch": "Direct the flow to different paths based on the value of a specific field or expression.",
	"Wait": "Introduce a delay or wait for a specific event before proceeding.",
	"Sub-Rule": "Invoke another rule as a reusable component within this flow.",
	"Assignment": (
		"Declare one or more batch state mutations applied sequentially. "
		"Supports doc.* and vars.* targets with type-aware operators "
		"(set, clear, increment, decrement, toggle, append, merge)."
	),
	"Notify": (
		"Send a notification as a toast, realtime message, email, "
		"Notification Log entry, or provider dispatch."
	),
	"Raise Error": "Stop execution immediately with a configured error message.",
	"Query Records": (
		"Query records from a DocType. Supports Query List, Query Doc, "
		"Exist Record, and Query Report modes."
	),
	"Document Action": (
		"Create, update, or delete documents, including convenience modes "
		"for linked ToDos and timeline comments."
	),
}


def _parse_json_object(value: Any) -> dict[str, Any]:
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


def apply_field_overrides(base_fields: list, overrides: list) -> list:
	"""Apply field overrides to base field definitions.

	Field overrides can include:
	- Standard Frappe field properties (reqd, options, default, etc.)
	- Dynamic properties: hidden, mandatory_depends_on, read_only_depends_on
	- Custom properties: description, link_filters, etc.
	"""
	field_map = {f["fieldname"]: f for f in base_fields}

	for override in overrides:
		fieldname = override["fieldname"]
		if fieldname in field_map:
			existing = field_map[fieldname]
			merged = existing.copy()
			merged.update(override)
			field_map[fieldname] = merged
		else:
			field_map[fieldname] = override.copy()

	return list(field_map.values())


def get_trigger_type_contract(trigger_type: str) -> dict:
	"""Get contract for a trigger type."""
	return TRIGGER_TYPE_CONTRACT.get(
		trigger_type,
		{
			"required_fields": [],
			"optional_fields": [],
			"hidden_fields": [],
		},
	)


def normalize_action_type(action_type: str | None) -> str:
	"""Normalize machine/case variants to canonical action type keys."""
	if not action_type:
		return ""

	raw = str(action_type).strip()

	from flexirule.ruleflow.core.action_handlers import HandlerRegistry

	# Lazily get registered action types to avoid import cycle issues
	action_types = list(HandlerRegistry._handlers.keys())

	if raw in action_types:
		return raw

	normalized = " ".join(raw.replace("_", " ").replace("-", " ").lower().split())
	for canonical in action_types:
		if canonical.lower() == normalized:
			return canonical

	compact = normalized.replace(" ", "")
	for canonical in action_types:
		if canonical.lower().replace(" ", "") == compact:
			return canonical

	# Check the legacy mapping to be safe
	legacy_types = {
		"Entry Action",
		"Condition",
		"Process",
		"Loop",
		"Switch",
		"Stop",
		"Raise Error",
		"Wait",
		"Sub-Rule",
		"Assignment",
		"Notify",
		"Query Records",
		"Document Action",
	}
	if raw in legacy_types:
		return raw
	for canonical in legacy_types:
		if canonical.lower() == normalized:
			return canonical
		if canonical.lower().replace(" ", "") == compact:
			return canonical

	return raw


def is_release_disabled_action(action_type: str) -> bool:
	"""Check if an action type is intentionally disabled for the current release."""
	action_type = normalize_action_type(action_type)
	return action_type in RELEASE_DISABLED_ACTION_TYPES
