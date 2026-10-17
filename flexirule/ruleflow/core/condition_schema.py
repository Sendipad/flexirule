# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Strict validation and normalization for the declarative condition tree.

This module validates the saved condition contract before the legacy
expression compiler sees it. It does not compile Python or evaluate conditions;
expression/formula values remain a separate feature boundary.
"""

from __future__ import annotations

import keyword
import re
from collections.abc import Mapping
from typing import Any

from flexirule.ruleflow.core.condition_operators import (
	BINARY_OPERATOR_TOKENS as _BINARY_OPERATORS,
)
from flexirule.ruleflow.core.condition_operators import (
	COLLECTION_OPERATION_TOKENS as _COLLECTION_OPERATORS,
)
from flexirule.ruleflow.core.condition_operators import (
	GROUP_OPERATOR_TOKENS as _GROUP_OPERATORS,
)
from flexirule.ruleflow.core.condition_operators import (
	SUPPORTED_OPERATOR_TOKENS as _SUPPORTED_OPERATORS,
)
from flexirule.ruleflow.core.condition_operators import (
	UNARY_OPERATOR_TOKENS as _UNARY_OPERATORS,
)
from flexirule.ruleflow.core.condition_operators import (
	UNSUPPORTED_OPERATOR_DIAGNOSTICS as _UNSUPPORTED_OPERATORS,
)
from flexirule.ruleflow.core.condition_operators import (
	normalize_operator,
)

_BASE_SCOPES = frozenset({"doc", "old_doc", "row", "vars", "item", "loop", "caller", "rule", "doctype", "ctx"})
_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

# The editor adds descriptive metadata to tree nodes. These fields are never
# interpreted by the runtime and may be retained while the condition is edited.
_NODE_METADATA_KEYS = frozenset(
	{
		"id",
		"uid",
		"uuid",
		"type",
		"name",
		"label",
		"description",
		"fieldtype",
		"fieldname",
		"field_name",
		"field_label",
		"field_options",
		"options",
		"metadata",
	}
)
_HELPER_NAMES = frozenset(
	{
		"any",
		"all",
		"min",
		"max",
		"sum",
		"len",
		"str",
		"int",
		"float",
		"frappe",
		"resolve",
		"is_empty_value",
		"is_submittable",
		"has_field",
		"check_link_match",
		"length_of",
	}
)


def validate_condition_tree(tree: Any, scopes: set[str] | frozenset[str] | None = None) -> dict:
	"""Validate and normalize one non-empty tree into the compiler's shape.

	Root lists are the supported legacy representation and are normalized to
	an AND group. Empty/missing configuration is handled by the caller; an
	empty group inside a configured tree is invalid.
	"""
	allowed_scopes = set(scopes or _BASE_SCOPES)
	if isinstance(tree, list):
		if not tree:
			raise ValueError("Condition tree is empty; omit the condition instead of saving an empty group")
		tree = {"op": "and", "conditions": tree}

	if not isinstance(tree, Mapping):
		raise ValueError("Condition must be a condition object or a root list")

	normalized = _normalize_node(tree, "$", allowed_scopes)
	if not isinstance(normalized, dict):
		raise ValueError("Condition root must be an object")
	return normalized


def _normalize_node(node: Any, path: str, scopes: set[str]) -> dict:
	if not isinstance(node, Mapping):
		raise ValueError(f"{path}: condition node must be an object")

	has_group = "conditions" in node
	has_collection = "collection" in node or "where" in node
	has_leaf = "left" in node
	if sum((has_group, has_collection, has_leaf)) != 1:
		raise ValueError(f"{path}: expected exactly one node shape: group, collection, or condition")

	if has_group:
		allowed = {"op", "logical_operator", "conditions"} | _NODE_METADATA_KEYS
		_check_keys(node, allowed, path)
		children = node.get("conditions")
		if not isinstance(children, list):
			raise ValueError(f"{path}.conditions: must be a list")
		if not children:
			raise ValueError(f"{path}.conditions: groups must contain at least one child")
		raw_op = node.get("op", node.get("logical_operator", "and"))
		group_op = _logical_operator(raw_op, f"{path}.op")
		result = dict(node)
		result["op"] = group_op
		result["conditions"] = [
			_normalize_node(child, f"{path}.conditions[{index}]", scopes)
			for index, child in enumerate(children)
		]
		if "logical_operator" in result:
			result["logical_operator"] = _logical_operator(
				result["logical_operator"], f"{path}.logical_operator"
			)
		return result

	if has_collection:
		allowed = {"op", "collection", "alias", "where", "logical_operator"} | _NODE_METADATA_KEYS
		_check_keys(node, allowed, path)
		if "collection" not in node or "where" not in node:
			raise ValueError(f"{path}: collection nodes require both 'collection' and 'where'")

		collection = node.get("collection")
		_validate_reference(collection, scopes, f"{path}.collection", require_field=True)

		raw_op = node.get("op", "any")
		if not isinstance(raw_op, str) or raw_op.strip().lower() not in _COLLECTION_OPERATORS:
			raise ValueError(
				f"{path}.op: unsupported collection operation {raw_op!r}; expected any, all, or none"
			)
		alias = node.get("alias", "row")
		_validate_alias(alias, f"{path}.alias")
		nested_scopes = set(scopes)
		nested_scopes.add(alias)
		result = dict(node)
		result["op"] = raw_op.strip().lower()
		result["collection"] = collection
		result["alias"] = alias
		result["where"] = _normalize_node(node.get("where"), f"{path}.where", nested_scopes)
		if "logical_operator" in result:
			result["logical_operator"] = _logical_operator(
				result["logical_operator"], f"{path}.logical_operator"
			)
		return result

	allowed = {"left", "op", "operator", "right", "logical_operator"} | _NODE_METADATA_KEYS
	_check_keys(node, allowed, path)

	if "op" in node and "operator" in node and node.get("op") != node.get("operator"):
		raise ValueError(f"{path}: 'op' and legacy 'operator' disagree")

	raw_op = node.get("op", node.get("operator", "=="))
	if not isinstance(raw_op, str) or not raw_op.strip():
		raise ValueError(f"{path}.op: operator must be a non-empty string")
	op = normalize_operator(raw_op)

	if op in _UNSUPPORTED_OPERATORS:
		raise ValueError(f"{path}.op: operator {raw_op!r} {_UNSUPPORTED_OPERATORS[op]}")
	if op not in _SUPPORTED_OPERATORS:
		raise ValueError(f"{path}.op: unknown or unsupported condition operator {raw_op!r}")

	_validate_operand(node.get("left"), scopes, f"{path}.left")
	needs_right = op in _BINARY_OPERATORS or op == "has_field"
	if needs_right and "right" not in node:
		raise ValueError(f"{path}.right: operator {op!r} requires a right operand")
	if "right" in node:
		_validate_operand(node.get("right"), scopes, f"{path}.right")

	result = dict(node)
	result["op"] = op
	result.pop("operator", None)
	# Unary comparisons do not consume a right operand. Drop any editor-retained
	# value from the canonical plan so evaluation cannot accidentally depend on it.
	if op in _UNARY_OPERATORS:
		result.pop("right", None)
	if "logical_operator" in result:
		result["logical_operator"] = _logical_operator(result["logical_operator"], f"{path}.logical_operator")
	return result


def _validate_operand(operand: Any, scopes: set[str], path: str) -> None:
	if not isinstance(operand, Mapping):
		raise ValueError(f"{path}: operand must be an object with exactly one of 'ref' or 'value'")

	keys = set(operand)
	if len(keys & {"ref", "value"}) != 1 or keys - {"ref", "value"}:
		raise ValueError(f"{path}: operand must contain exactly one supported key: 'ref' or 'value'")

	if "ref" in operand:
		_validate_reference(operand["ref"], scopes, f"{path}.ref")
		return

	_validate_value_payload(operand["value"], scopes, f"{path}.value")


def _validate_value_payload(value: Any, scopes: set[str], path: str) -> None:
	if not isinstance(value, Mapping) or "mode" not in value:
		return

	mode = value.get("mode")
	if not isinstance(mode, str) or not mode.strip():
		raise ValueError(f"{path}.mode: value mode must be a non-empty string")
	mode = mode.strip().lower()
	supported_modes = {
		"static",
		"link",
		"dynamic_link",
		"variable",
		"resolver",
		"formula",
		"format",
		"formatter",
		"normalize",
		"normalization",
		"expression",
	}
	if mode not in supported_modes:
		raise ValueError(f"{path}.mode: unsupported structured value mode {mode!r}")

	if mode == "variable":
		reference = value.get("path") or value.get("value")
		_validate_reference(reference, scopes, f"{path}.path")
		return

	if mode == "expression":
		segments = value.get("value")
		if segments is None:
			return
		if not isinstance(segments, list):
			raise ValueError(f"{path}.value: mixed expression must be a list of segments")
		for index, segment in enumerate(segments):
			segment_path = f"{path}.value[{index}]"
			if not isinstance(segment, Mapping):
				raise ValueError(f"{segment_path}: expression segment must be an object")
			segment_type = segment.get("type")
			if segment_type == "variableToken":
				attrs = segment.get("attrs") or {}
				if not isinstance(attrs, Mapping):
					raise ValueError(f"{segment_path}.attrs: must be an object")
				_validate_reference(attrs.get("path"), scopes, f"{segment_path}.attrs.path")
			elif segment_type not in {
				"text",
				"resolverToken",
				"formulaToken",
				"normalizeToken",
				"formatToken",
				"jsonToken",
			}:
				raise ValueError(f"{segment_path}.type: unsupported expression segment {segment_type!r}")


def _validate_reference(reference: Any, scopes: set[str], path: str, *, require_field: bool = False) -> None:
	if not isinstance(reference, str) or not reference.strip():
		raise ValueError(f"{path}: reference must be a non-empty string")

	parts = reference.strip().split(".")
	if require_field and len(parts) < 2:
		raise ValueError(f"{path}: collection reference must include a scope and field path")
	if parts[0] not in scopes:
		raise ValueError(f"{path}: unknown reference scope {parts[0]!r}")
	for part in parts:
		if not _IDENTIFIER.fullmatch(part) or part.startswith("__"):
			raise ValueError(f"{path}: invalid reference path {reference!r}")


def _validate_alias(alias: Any, path: str) -> None:
	if not isinstance(alias, str) or not _IDENTIFIER.fullmatch(alias) or alias.startswith("__"):
		raise ValueError(f"{path}: alias must be a safe identifier")
	if keyword.iskeyword(alias) or alias in _HELPER_NAMES:
		raise ValueError(f"{path}: alias {alias!r} is reserved")
	if alias in {"doc", "old_doc", "vars", "caller", "rule", "doctype", "ctx", "frappe"}:
		raise ValueError(f"{path}: alias {alias!r} would shadow a reserved condition scope")


def _logical_operator(value: Any, path: str) -> str:
	if not isinstance(value, str) or value.strip().lower() not in _GROUP_OPERATORS:
		raise ValueError(f"{path}: expected logical operator 'and' or 'or'")
	return value.strip().lower()


def _check_keys(node: Mapping, allowed: set[str], path: str) -> None:
	unknown = sorted(set(node) - allowed)
	if unknown:
		raise ValueError(
			f"{path}: unexpected condition node key(s): {', '.join(str(key) for key in unknown)}"
		)
