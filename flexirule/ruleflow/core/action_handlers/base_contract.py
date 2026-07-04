# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Handler-Owned Contract Data Classes.

Provides ActionContract and OperationContract data classes that each
ActionHandler uses to declare its metadata contract.  Reusable field
override presets eliminate duplication across handlers.

Usage:
    from flexirule.ruleflow.core.action_handlers.base_contract import (
        ActionContract,
        OperationContract,
        reference_doctype_override,
        config_depends_on_doctype,
        aggregate_operation_overrides,
    )
"""

from __future__ import annotations

from typing import Any

# ── Data Classes ─────────────────────────────────────────────────


class ActionContract:
	"""Data class representing an action type's full contract.

	Produces the same dict shape as a legacy ACTION_TYPE_CONTRACT entry
	when serialized via ``to_dict()``.
	"""

	def __init__(
		self,
		action_type: str,
		*,
		required_fields: list[str] | None = None,
		has_next_true: bool = True,
		has_next_false: bool = False,
		terminal: bool = False,
		css: dict | None = None,
		node_type: str = "action",
		category: str = "Other",
		configurable: bool = True,
		config_component: str | None = None,
		field_labels: dict | None = None,
		operation_label: str | None = None,
		operation_options: list[str] | None = None,
		allowed_mutations: list[str] | None = None,
		allowed_return_types: list[str] | None = None,
		default_return_type: str | None = None,
		show_return_type: bool | None = None,
		require_return_type: bool = False,
		show_return_variable: bool | None = None,
		require_return_variable: bool = False,
		operation_policies: dict | None = None,
		mandatory_fields: dict | None = None,
		validation: dict | None = None,
		dynamic_fields: bool | None = None,
		field_overrides: list[dict] | None = None,
		# Runtime field aliases for frontend mapping
		runtime_field_aliases: dict | None = None,
		# Additional custom keys stored as extras
		**extras,
	):
		self.action_type = action_type
		self.required_fields = required_fields or []
		self.has_next_true = has_next_true
		self.has_next_false = has_next_false
		self.terminal = terminal
		self.css = css or {}
		self.node_type = node_type
		self.category = category
		self.configurable = configurable
		self.config_component = config_component
		self.field_labels = field_labels or {}
		self.operation_label = operation_label
		self.operation_options = operation_options
		self.allowed_mutations = allowed_mutations
		self.allowed_return_types = allowed_return_types
		self.default_return_type = default_return_type
		self.show_return_type = show_return_type
		self.require_return_type = require_return_type
		self.show_return_variable = show_return_variable
		self.require_return_variable = require_return_variable
		self.operation_policies = operation_policies
		self.mandatory_fields = mandatory_fields
		self.validation = validation
		self.dynamic_fields = dynamic_fields
		self.field_overrides = field_overrides or []
		self.runtime_field_aliases = runtime_field_aliases
		self.extras = extras

	def get_common_action_overrides(self) -> list[dict[str, Any]]:
		"""Return action-wide Rule Action field overrides inferred from contract flags."""
		overrides: list[dict[str, Any]] = []

		if self.terminal or not self.has_next_true:
			overrides.append({"fieldname": "next_step_if_true", "hidden": 1, "reqd": 0})
		if self.terminal or not self.has_next_false:
			overrides.append({"fieldname": "next_step_if_false", "hidden": 1, "reqd": 0})

		overrides.extend(dict(row) for row in self.field_overrides)
		return overrides

	def to_dict(self) -> dict[str, Any]:
		"""Serialize to the same dict format as legacy ACTION_TYPE_CONTRACT entries."""
		d: dict[str, Any] = {
			"required_fields": self.required_fields,
			"has_next_true": self.has_next_true,
			"has_next_false": self.has_next_false,
			"terminal": self.terminal,
			"css": self.css,
			"node_type": self.node_type,
			"category": self.category,
			"configurable": self.configurable,
		}

		if self.config_component:
			d["config_component"] = self.config_component
		if self.field_labels:
			d["field_labels"] = self.field_labels
		if self.operation_label is not None:
			d["operation_label"] = self.operation_label
		if self.operation_options is not None:
			d["operation_options"] = self.operation_options
		if self.allowed_mutations is not None:
			d["allowed_mutations"] = self.allowed_mutations
		if self.allowed_return_types is not None:
			d["allowed_return_types"] = self.allowed_return_types
		if self.default_return_type is not None:
			d["default_return_type"] = self.default_return_type
		if self.show_return_type is not None:
			d["show_return_type"] = self.show_return_type
		if self.require_return_type:
			d["require_return_type"] = self.require_return_type
		if self.show_return_variable is not None:
			d["show_return_variable"] = self.show_return_variable
		if self.require_return_variable:
			d["require_return_variable"] = self.require_return_variable
		if self.operation_policies is not None:
			d["operation_policies"] = self.operation_policies
		if self.mandatory_fields is not None:
			d["mandatory_fields"] = self.mandatory_fields
		if self.validation is not None:
			d["validation"] = self.validation
		if self.dynamic_fields is not None:
			d["dynamic_fields"] = self.dynamic_fields
		common_overrides = self.get_common_action_overrides()
		if common_overrides:
			d["field_overrides"] = common_overrides

		# Merge extras
		d.update(self.extras)
		return d


class OperationContract:
	"""Data class representing an operation's field overrides.

	Produces the same dict shape as a legacy OPERATION_CONTRACTS entry
	when serialized via ``to_dict()``.
	"""

	def __init__(
		self,
		operation: str,
		*,
		rule_overrides: list[dict] | None = None,
		action_overrides: list[dict] | None = None,
		validation: dict | None = None,
	):
		self.operation = operation
		self.rule_overrides = rule_overrides or []
		self.action_overrides = action_overrides or []
		self.validation = validation or {}

	def to_dict(self) -> dict[str, Any]:
		"""Serialize to the same dict format as legacy OPERATION_CONTRACTS entries."""
		return {
			"Rule": list(self.rule_overrides),
			"Rule Action": list(self.action_overrides),
			"Validation": dict(self.validation),
		}


# ── Reusable Field Override Presets ──────────────────────────────

# Standard DocType link filters used by Query Records, Document Action, etc.
STANDARD_DOCTYPE_LINK_FILTERS = '[["DocType","issingle","=",0],["DocType","istable","=",0]]'
# Relaxed filter allowing single doctypes (used by Query Doc)
SINGLE_ALLOWED_DOCTYPE_LINK_FILTERS = '[["DocType","istable","=",0]]'


def reference_doctype_override(*, reqd: int = 1, link_filters: str | None = None) -> dict:
	"""Standard reference_doctype field override.

	Used by Query Records, Document Action, etc. Provides consistent
	link filters to exclude single and child table DocTypes.
	"""
	return {
		"fieldname": "reference_doctype",
		"reqd": reqd,
		"link_filters": link_filters or STANDARD_DOCTYPE_LINK_FILTERS,
	}


def config_depends_on_doctype(*, reqd: int = 1, description: str | None = None) -> dict:
	"""Standard config field override that depends on reference_doctype selection."""
	override: dict[str, Any] = {
		"fieldname": "config",
		"depends_on": "eval:doc.reference_doctype",
		"reqd": reqd,
	}
	if description:
		override["description"] = description
	return override


def standard_trigger_overrides(
	*,
	trigger_events: list[str] | None = None,
	trigger_types: list[str] | None = None,
) -> list[dict]:
	"""Standard Rule-level trigger overrides for trigger_event and trigger_type."""
	overrides: list[dict] = []
	if trigger_events is not None:
		overrides.append({"fieldname": "trigger_event", "options": trigger_events})
	if trigger_types is not None:
		overrides.append({"fieldname": "trigger_type", "options": trigger_types})
	return overrides


# Common trigger type/event combos
STANDARD_TRIGGER_TYPES = ["DocType Event", "Callable Event"]
BROAD_TRIGGER_EVENTS = ["Before Save", "After Insert", "After Save", "Validate", "On Submit", "On Change"]
VALIDATE_TRIGGER_EVENTS = ["Validate", "Before Save", "On Change"]
AFTER_TRIGGER_EVENTS = ["After Save", "On Submit", "On Change"]
CREATE_TRIGGER_EVENTS = ["Before Insert", "Validate", "Before Save"]


def aggregate_operation_overrides(operation: str, description: str) -> OperationContract:
	"""Factory for Sum/Average/Min/Max which share identical structure.

	These aggregate operations differ only in operation name and description.
	All use the same trigger events, reference_doctype filters, config dependency,
	return type, and validation backend.
	"""
	return OperationContract(
		operation=operation,
		rule_overrides=standard_trigger_overrides(
			trigger_events=VALIDATE_TRIGGER_EVENTS,
			trigger_types=STANDARD_TRIGGER_TYPES,
		),
		action_overrides=[
			{"fieldname": "action_type", "default": "Query Records"},
			{"fieldname": "operation", "default": operation},
			reference_doctype_override(),
			config_depends_on_doctype(),
			{"fieldname": "return_type", "default": "List of Values", "read_only": 1},
			{"fieldname": "description", "description": description},
		],
		validation={"backend": "validate_aggregate_query"},
	)
