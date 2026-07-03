# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


def normalize_action_type(action_type: str | None, action_types: list[str] | None = None) -> str:
	"""Normalize machine/case variants to canonical action type keys."""
	if not action_type:
		return ""

	raw = str(action_type).strip()

	if action_types is None:
		from flexirule.ruleflow.core.action_handlers import HandlerRegistry
		action_types = HandlerRegistry.action_types()

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

	return raw


def apply_field_overrides(base_fields: list, overrides: list) -> list:
	"""Apply field overrides to base field definitions."""
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


# Trigger Type Contract
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
