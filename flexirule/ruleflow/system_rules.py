"""Version-controlled built-in System Rule definitions.

These declarative rules implement governance conventions that are intentionally
separate from Python's hard safety invariants. They are registered inactive so
operators explicitly choose when to enable each policy.
"""

from __future__ import annotations

import json
from typing import Any


def _condition_group(*conditions: dict[str, Any]) -> str:
	"""Serialize canonical Rule trigger conditions."""
	return json.dumps({"op": "and", "conditions": list(conditions)}, separators=(",", ":"))


def _install_guard() -> dict[str, Any]:
	"""Only evaluate governance policies outside the installation lifecycle."""
	return {
		"left": {"ref": "vars.is_install"},
		"op": "!=",
		"right": {"value": True},
	}


def _assign_error_then_stop(action_id: str, message: str) -> list[dict[str, Any]]:
	"""Build Entry Action -> Assignment -> Stop(Error), gated by trigger_condition."""
	assignment_id = "assign_error"
	assignment_config = json.dumps(
		[
			{
				"target": "vars.rejection_message",
				"operator": "set",
				"value": {"mode": "static", "value": message},
			}
		],
		separators=(",", ":"),
	)
	return [
		{
			"action_id": "root",
			"action_type": "Entry Action",
			"action_label": "Start",
			"is_enabled": 1,
			"next_step_if_true": assignment_id,
		},
		{
			"action_id": assignment_id,
			"action_type": "Assignment",
			"action_label": "Set rejection message",
			"is_enabled": 1,
			"config": assignment_config,
			"next_step_if_true": action_id,
		},
		{
			"action_id": action_id,
			"action_type": "Stop",
			"action_label": "Reject",
			"is_enabled": 1,
			"operation": "Error",
			"value_template": "{{ vars.rejection_message }}",
		},
	]


def _stop_with_error(action_id: str, message: str) -> list[dict[str, Any]]:
	"""Build the minimal Entry Action -> Stop(Error) graph."""
	return [
		{
			"action_id": "root",
			"action_type": "Entry Action",
			"action_label": "Start",
			"is_enabled": 1,
			"next_step_if_true": action_id,
		},
		{
			"action_id": action_id,
			"action_type": "Stop",
			"action_label": "Reject",
			"is_enabled": 1,
			"operation": "Error",
			"value_template": message,
		},
	]


def get_system_rule_definitions() -> list[dict[str, Any]]:
	"""Return the initial governance and naming policies for Rule documents."""
	naming_condition = _condition_group(
		_install_guard(),
		{
			"op": "or",
			"conditions": [
				{
					"left": {"ref": "doc.rule_name"},
					"op": "is_not_set",
				},
				{
					"left": {"ref": "doc.rule_name"},
					"op": "starts_with",
					"right": {"value": "new"},
				},
			],
		},
	)
	governance_condition = _condition_group(
		_install_guard(),
		{
			"left": {"ref": "doc.description"},
			"op": "is_not_set",
		},
	)

	return [
		{
			"rule_name": "RULE_NAMING_REJECT_EMPTY_OR_PLACEHOLDER",
			"description": "Reject Rule names that are empty or use the placeholder prefix 'new'.",
			"module": "Ruleflow",
			"document_type": "Rule",
			"trigger_type": "DocType Event",
			"trigger_event": "Before Naming",
			"trigger_condition": naming_condition,
			"priority": "20",
			"actions": _assign_error_then_stop(
				"reject",
				"Rule Name must be set to a meaningful value and must not start with the placeholder prefix 'new'.",
			),
		},
		{
			"rule_name": "RULE_GOVERNANCE_REQUIRE_DESCRIPTION",
			"description": "Require a purpose description when creating a new Rule.",
			"module": "Ruleflow",
			"document_type": "Rule",
			"trigger_type": "DocType Event",
			"trigger_event": "Before Insert",
			"trigger_condition": governance_condition,
			"priority": "20",
			"actions": _stop_with_error(
				"reject",
				"Add a short description explaining the purpose of this Rule before saving it.",
			),
		},
	]
