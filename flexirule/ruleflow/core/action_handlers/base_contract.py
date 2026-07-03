# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any


class ActionContract:
	"""Data class representing an action type's full contract."""

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
		require_return_type: bool | None = None,
		show_return_variable: bool | None = None,
		require_return_variable: bool | None = None,
		operation_policies: dict | None = None,
		mandatory_fields: dict | None = None,
		validation: dict | None = None,
		dynamic_fields: bool = False,
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
		self.field_labels = field_labels
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
		self.extras = extras

	def to_dict(self) -> dict[str, Any]:
		"""Serialize to the same dict format as legacy ACTION_TYPE_CONTRACT entries."""
		res = {
			"required_fields": self.required_fields,
			"has_next_true": self.has_next_true,
			"has_next_false": self.has_next_false,
			"terminal": self.terminal,
			"css": self.css,
			"node_type": self.node_type,
			"category": self.category,
			"configurable": self.configurable,
			"require_return_type": self.require_return_type if self.require_return_type is not None else False,
		}

		if self.config_component:
			res["config_component"] = self.config_component

		if self.field_labels is not None:
			res["field_labels"] = self.field_labels
		if self.operation_label:
			res["operation_label"] = self.operation_label
		if self.operation_options:
			res["operation_options"] = self.operation_options
		if self.allowed_mutations is not None:
			res["allowed_mutations"] = self.allowed_mutations
		if self.allowed_return_types is not None:
			res["allowed_return_types"] = self.allowed_return_types
		if self.default_return_type is not None:
			res["default_return_type"] = self.default_return_type
		if self.show_return_type is not None:
			res["show_return_type"] = self.show_return_type

		if self.show_return_variable is not None:
			res["show_return_variable"] = self.show_return_variable
		if self.require_return_variable is not None:
			res["require_return_variable"] = self.require_return_variable
		if self.operation_policies:
			res["operation_policies"] = self.operation_policies
		if self.mandatory_fields:
			res["mandatory_fields"] = self.mandatory_fields
		if self.validation:
			res["validation"] = self.validation
		if self.dynamic_fields:
			res["dynamic_fields"] = self.dynamic_fields

		res.update(self.extras)
		return res


class OperationContract:
	"""Data class representing an operation's field overrides."""

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
			"Rule": self.rule_overrides,
			"Rule Action": self.action_overrides,
			"Validation": self.validation,
		}


# ── Reusable field override presets ──────────────────────────────

STANDARD_DOCTYPE_LINK_FILTERS = "[['DocType','issingle','=',0],['DocType','istable','=',0]]"
SINGLE_ALLOWED_DOCTYPE_LINK_FILTERS = "[['DocType','istable','=',0]]"


def reference_doctype_override(*, reqd=1, link_filters=None):
	"""Standard reference_doctype override used by Query Records, Document Action, etc."""
	return {
		"fieldname": "reference_doctype",
		"reqd": reqd,
		"link_filters": link_filters or STANDARD_DOCTYPE_LINK_FILTERS,
	}


def config_depends_on_doctype(*, reqd=1, description=None):
	"""Standard config override that depends on reference_doctype selection."""
	override = {
		"fieldname": "config",
		"depends_on": "eval:doc.reference_doctype",
		"reqd": reqd,
	}
	if description:
		override["description"] = description
	return override


def aggregate_operation_overrides(operation: str, description: str):
	"""Factory for Sum/Average/Min/Max which share identical structure."""
	return OperationContract(
		operation=operation,
		rule_overrides=[
			{"fieldname": "trigger_event", "options": ["Validate", "Before Save", "On Change"]},
			{"fieldname": "trigger_type", "options": ["DocType Event", "Callable Event"]},
		],
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
