# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Authoritative schema and operator metadata for canonical conditions."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, NoReturn

from flexirule.ruleflow.core.condition_errors import ConditionValidationError
from flexirule.ruleflow.core.flexvalue_contract import (
	BASE_SCOPES,
	CONDITION_LIMITS,
	MAX_CONDITION_DEPTH,
	MAX_CONDITION_NODES,
	MAX_CONDITION_PAYLOAD_BYTES,
	MAX_PATH_SEGMENTS,
	MAX_TEMPLATE_SEGMENTS,
	VALUE_TYPES,
	validate_flex_value,
)

CONDITION_SEMANTICS_VERSION = 1

ALL_FIELD_TYPES = None
TEXT_FIELD_TYPES = (
	"Data",
	"Small Text",
	"Text",
	"Text Editor",
	"Code",
	"Select",
	"Link",
	"Dynamic Link",
)
NUMERIC_FIELD_TYPES = ("Int", "Float", "Currency", "Percent")
ORDERED_FIELD_TYPES = (*NUMERIC_FIELD_TYPES, "Date", "Datetime", "Time")
EMPTY_FIELD_TYPES = (
	"Data",
	"Small Text",
	"Text",
	"Text Editor",
	"Code",
	"Select",
	"Table",
	"Table MultiSelect",
	"JSON",
)
RESERVED_ALIASES = BASE_SCOPES | {"and", "or", "any", "all", "none"}


@dataclass(frozen=True)
class OperatorSpec:
	operator_id: str
	label: str
	arity: int
	left_types: tuple[str, ...]
	right_types: tuple[str, ...] = ()
	fieldtypes: tuple[str, ...] | None = None
	legacy_aliases: tuple[str, ...] = ()
	description: str = ""


def _spec(
	operator_id: str,
	label: str,
	arity: int,
	left_types: tuple[str, ...],
	right_types: tuple[str, ...] = (),
	fieldtypes: tuple[str, ...] | None = None,
	legacy_aliases: tuple[str, ...] = (),
	description: str = "",
) -> OperatorSpec:
	return OperatorSpec(
		operator_id, label, arity, left_types, right_types, fieldtypes, legacy_aliases, description
	)


SCALAR_TYPES = ("string", "integer", "decimal", "boolean", "null", "date", "datetime", "time")
MEMBERSHIP_TYPES = ("string", "integer", "decimal", "boolean", "null")
COMPARABLE_TYPES = (*SCALAR_TYPES, "list", "object")
NUMERIC_TYPES = ("integer", "decimal")
SIZED_TYPES = ("string", "list", "object")

# This is the only live canonical operator registry. Legacy aliases are migration-only.
OPERATOR_REGISTRY: dict[str, OperatorSpec] = {
	"eq": _spec("eq", "Equals", 2, COMPARABLE_TYPES, COMPARABLE_TYPES, legacy_aliases=("==",)),
	"ne": _spec("ne", "Does not equal", 2, COMPARABLE_TYPES, COMPARABLE_TYPES, legacy_aliases=("!=",)),
	"gt": _spec(
		"gt",
		"Greater than",
		2,
		(*NUMERIC_TYPES, "date", "datetime", "time"),
		(*NUMERIC_TYPES, "date", "datetime", "time"),
		ORDERED_FIELD_TYPES,
		(">",),
	),
	"gte": _spec(
		"gte",
		"Greater than or equal",
		2,
		(*NUMERIC_TYPES, "date", "datetime", "time"),
		(*NUMERIC_TYPES, "date", "datetime", "time"),
		ORDERED_FIELD_TYPES,
		(">=",),
	),
	"lt": _spec(
		"lt",
		"Less than",
		2,
		(*NUMERIC_TYPES, "date", "datetime", "time"),
		(*NUMERIC_TYPES, "date", "datetime", "time"),
		ORDERED_FIELD_TYPES,
		("<",),
	),
	"lte": _spec(
		"lte",
		"Less than or equal",
		2,
		(*NUMERIC_TYPES, "date", "datetime", "time"),
		(*NUMERIC_TYPES, "date", "datetime", "time"),
		ORDERED_FIELD_TYPES,
		("<=",),
	),
	"in": _spec("in", "Is in", 2, MEMBERSHIP_TYPES, ("list",), legacy_aliases=("in",)),
	"not_in": _spec("not_in", "Is not in", 2, MEMBERSHIP_TYPES, ("list",), legacy_aliases=("not in",)),
	"contains": _spec("contains", "Contains text", 2, ("string",), ("string",), TEXT_FIELD_TYPES),
	"not_contains": _spec(
		"not_contains", "Does not contain text", 2, ("string",), ("string",), TEXT_FIELD_TYPES
	),
	"starts_with": _spec("starts_with", "Starts with", 2, ("string",), ("string",), TEXT_FIELD_TYPES),
	"ends_with": _spec("ends_with", "Ends with", 2, ("string",), ("string",), TEXT_FIELD_TYPES),
	"is_set": _spec("is_set", "Is set", 1, COMPARABLE_TYPES, fieldtypes=ALL_FIELD_TYPES),
	"is_not_set": _spec("is_not_set", "Is not set", 1, COMPARABLE_TYPES, fieldtypes=ALL_FIELD_TYPES),
	"is_null": _spec("is_null", "Is null", 1, COMPARABLE_TYPES, fieldtypes=ALL_FIELD_TYPES),
	"is_not_null": _spec("is_not_null", "Is not null", 1, COMPARABLE_TYPES, fieldtypes=ALL_FIELD_TYPES),
	"is_empty": _spec("is_empty", "Is empty", 1, SIZED_TYPES, fieldtypes=EMPTY_FIELD_TYPES),
	"is_not_empty": _spec("is_not_empty", "Is not empty", 1, SIZED_TYPES, fieldtypes=EMPTY_FIELD_TYPES),
	"length_eq": _spec("length_eq", "Length equals", 2, SIZED_TYPES, ("integer",), EMPTY_FIELD_TYPES),
	"length_gt": _spec("length_gt", "Length greater than", 2, SIZED_TYPES, ("integer",), EMPTY_FIELD_TYPES),
	"length_gte": _spec("length_gte", "Length at least", 2, SIZED_TYPES, ("integer",), EMPTY_FIELD_TYPES),
	"length_lt": _spec("length_lt", "Length less than", 2, SIZED_TYPES, ("integer",), EMPTY_FIELD_TYPES),
	"length_lte": _spec("length_lte", "Length at most", 2, SIZED_TYPES, ("integer",), EMPTY_FIELD_TYPES),
	"is_submittable": _spec("is_submittable", "DocType is submittable", 1, ("string",)),
	"has_field": _spec("has_field", "DocType has field", 2, ("string",), ("string",)),
}

UNARY_OPERATORS = frozenset(key for key, spec in OPERATOR_REGISTRY.items() if spec.arity == 1)
MISSING = object()


def operator_contract_dto() -> list[dict[str, Any]]:
	"""Return stable public metadata without exposing implementation callables."""
	result = []
	for operator_id, spec in sorted(OPERATOR_REGISTRY.items()):
		result.append(
			{
				"id": operator_id,
				"label": spec.label,
				"arity": spec.arity,
				"accepted_left_types": list(spec.left_types),
				"accepted_right_types": list(spec.right_types),
				"fieldtypes": list(spec.fieldtypes) if spec.fieldtypes is not None else None,
				"legacy_aliases": list(spec.legacy_aliases),
				"description": spec.description,
			}
		)
	return result


def _fail(code: str, path: str, message: str) -> NoReturn:
	raise ConditionValidationError(code, path, message)


def _exact_keys(value: Mapping, required: set[str], path: str) -> None:
	if any(not isinstance(key, str) for key in value):
		_fail("invalid_key_type", path, "Condition object keys must be strings")
	missing = required - set(value)
	unknown = set(value) - required
	if missing:
		_fail("missing_key", path, f"Missing required key(s): {', '.join(sorted(missing))}")
	if unknown:
		_fail("unknown_key", path, f"Unknown key(s): {', '.join(sorted(unknown))}")


def _known_type_compatible(actual: str | None, accepted: tuple[str, ...]) -> bool:
	return actual is None or actual in accepted


def _validate_membership_items(left_type: str | None, right_value: Any, path: str) -> None:
	if left_type is None or left_type == "null":
		return
	if not isinstance(right_value, Mapping):
		return
	if right_value.get("mode") != "static" or right_value.get("value_type") != "list":
		return
	items = right_value.get("value")
	if not isinstance(items, list):
		return
	accepted = {
		"string": {"string", "null"},
		"integer": {"integer", "decimal", "null"},
		"decimal": {"integer", "decimal", "null"},
		"boolean": {"boolean", "null"},
	}.get(left_type)
	if accepted is None:
		return
	for index, item in enumerate(items):
		if _json_runtime_type(item) not in accepted:
			_fail(
				"operand_type_mismatch",
				f"{path}.right.value[{index}]",
				"Membership list item type is incompatible with the left operand",
			)


def _types_compatible(left_type: str | None, right_type: str | None, operator_id: str, path: str) -> None:
	if left_type is None or right_type is None:
		return
	if operator_id in {"eq", "ne"}:
		if left_type == "null" or right_type == "null":
			return
		if left_type == right_type or {left_type, right_type} <= {"integer", "decimal"}:
			return
		_fail("operand_type_mismatch", path, "Equality operands have incompatible declared types")
	if operator_id in {"gt", "gte", "lt", "lte"}:
		if left_type in NUMERIC_TYPES and right_type in NUMERIC_TYPES:
			return
		if left_type == right_type and left_type in {"date", "datetime", "time"}:
			return
		_fail("operand_type_mismatch", path, "Ordered comparison operands have incompatible types")
	if operator_id in {"in", "not_in"}:
		if right_type != "list" or left_type not in SCALAR_TYPES:
			_fail(
				"operand_type_mismatch",
				path,
				"Membership requires a scalar left operand and list right operand",
			)
		return
	spec = OPERATOR_REGISTRY[operator_id]
	if left_type not in spec.left_types:
		_fail("operand_type_mismatch", f"{path}.left", "Left operand type is not supported by this operator")
	if spec.arity == 2 and right_type not in spec.right_types:
		_fail(
			"operand_type_mismatch", f"{path}.right", "Right operand type is not supported by this operator"
		)


def _meta_for(doctype: str, path: str):
	try:
		import frappe

		return frappe.get_meta(doctype)
	except Exception:
		_fail("unknown_doctype", path, "Could not resolve DocType metadata for this path")


def resolve_fieldtype_for_path(scope: str, segments: tuple[str, ...], doctype: str | None) -> str | None:
	"""Resolve Fieldtype metadata for a variable path when a concrete DocType is known.

	Returns None for scopes whose metadata is not statically available. A provided
	DocType with an invalid known document path fails closed at validation time.
	"""
	if not doctype or scope not in {"doc", "old_doc", "row"} and scope in BASE_SCOPES:
		return None
	current_doctype = doctype
	fieldtype = None
	for index, segment in enumerate(segments):
		if segment == "name" and index == len(segments) - 1:
			return "Data"
		meta = _meta_for(current_doctype, f"$.{scope}.segments[{index}]")
		field = meta.get_field(segment)
		if not field:
			_fail(
				"unknown_field",
				f"$.{scope}.segments[{index}]",
				"Field does not exist on the declared DocType",
			)
		fieldtype = field.fieldtype
		if index < len(segments) - 1:
			if fieldtype in {"Table", "Table MultiSelect", "Link", "Dynamic Link"}:
				_fail(
					"unsupported_field_traversal",
					f"$.{scope}.segments[{index}]",
					"Canonical paths do not implicitly traverse collections or fetch linked documents",
				)
			_fail(
				"invalid_field_path",
				f"$.{scope}.segments[{index}]",
				"Field path continues through a scalar value",
			)
	return fieldtype


FIELD_TYPE_VALUE_TYPES = {
	"Data": ("string",),
	"Small Text": ("string",),
	"Text": ("string",),
	"Text Editor": ("string",),
	"Code": ("string",),
	"Select": ("string",),
	"Link": ("string",),
	"Dynamic Link": ("string",),
	"Int": ("integer",),
	"Float": ("integer", "decimal"),
	"Currency": ("integer", "decimal"),
	"Percent": ("integer", "decimal"),
	"Check": ("boolean",),
	"Date": ("date",),
	"Datetime": ("datetime",),
	"Time": ("time",),
	"Table": ("list",),
	"Table MultiSelect": ("list",),
	"JSON": ("string", "list", "object"),
}


def _json_runtime_type(value: Any) -> str:
	if value is None:
		return "null"
	if isinstance(value, bool):
		return "boolean"
	if isinstance(value, int) and not isinstance(value, bool):
		return "integer"
	if isinstance(value, float):
		return "decimal"
	if isinstance(value, str):
		return "string"
	if isinstance(value, list):
		return "list"
	if isinstance(value, dict):
		return "object"
	return "unsupported"


def _known_fieldtype_check(
	operator_id: str,
	left: Any,
	fieldtype: str | None,
	path: str,
	right_value: Any = None,
	right_type: str | None = None,
) -> None:
	spec = OPERATOR_REGISTRY[operator_id]
	if fieldtype and spec.fieldtypes is not None and fieldtype not in spec.fieldtypes:
		_fail(
			"fieldtype_not_supported",
			f"{path}.left",
			"Operator is not supported for the left operand's Fieldtype",
		)
	if fieldtype == "Check" and operator_id in {
		"gt",
		"gte",
		"lt",
		"lte",
		"length_eq",
		"length_gt",
		"length_gte",
		"length_lt",
		"length_lte",
		"contains",
		"not_contains",
		"starts_with",
		"ends_with",
	}:
		_fail("fieldtype_not_supported", f"{path}.left", "Boolean fields do not support this operator")

	if not fieldtype:
		return

	if operator_id in {"in", "not_in"}:
		expected_types = FIELD_TYPE_VALUE_TYPES.get(fieldtype)
		if (
			isinstance(right_value, Mapping)
			and right_value.get("mode") == "static"
			and right_value.get("value_type") == "list"
		):
			items = right_value.get("value", [])
			if expected_types and any(
				_json_runtime_type(item) not in (*expected_types, "null") for item in items
			):
				message = (
					"Link membership lists must contain record-name strings; link tuples are not inferred"
					if fieldtype in {"Link", "Dynamic Link"}
					else "Membership list item types are incompatible with the left field's Fieldtype"
				)
				_fail("operand_type_mismatch", f"{path}.right", message)
		return

	if right_type in (None, "null"):
		return
	expected_types = FIELD_TYPE_VALUE_TYPES.get(fieldtype)
	if expected_types and right_type not in expected_types:
		_fail(
			"operand_type_mismatch",
			f"{path}.right",
			"Right operand type is incompatible with the left field's declared Fieldtype",
		)


def validate_condition_node(node: Any, *, doctype: str | None = None) -> None:
	"""Strictly validate a canonical direct-node condition; never repair or mutate it."""
	try:
		encoded = json.dumps(
			node, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
		).encode("utf-8")
	except (TypeError, ValueError, RecursionError) as exc:
		raise ConditionValidationError(
			"invalid_json_value", "$", "Condition payload must be a finite, acyclic JSON value"
		) from exc
	if len(encoded) > MAX_CONDITION_PAYLOAD_BYTES:
		_fail("condition_payload_too_large", "$", "Condition payload exceeds the configured byte limit")
	counter = {"nodes": 0}
	scope_doctypes: dict[str, str | None] = {"doc": doctype, "old_doc": doctype}
	_validate_node(
		node,
		path="$",
		depth=1,
		counter=counter,
		allowed_scopes=set(BASE_SCOPES),
		scope_doctypes=scope_doctypes,
	)


def _validate_node(
	node: Any,
	*,
	path: str,
	depth: int,
	counter: dict[str, int],
	allowed_scopes: set[str],
	scope_doctypes: dict[str, str | None],
) -> None:
	if depth > MAX_CONDITION_DEPTH:
		_fail("condition_depth_exceeded", path, "Condition tree exceeds the maximum nesting depth")
	counter["nodes"] += 1
	if counter["nodes"] > MAX_CONDITION_NODES:
		_fail("condition_node_limit_exceeded", path, "Condition tree exceeds the maximum node count")
	if not isinstance(node, Mapping):
		_fail("invalid_condition_node", path, "Condition node must be an object")
	node_type = node.get("type")

	if node_type == "group":
		_exact_keys(node, {"type", "operator", "children"}, path)
		operator_id = node.get("operator")
		if not isinstance(operator_id, str) or operator_id not in {"and", "or"}:
			_fail("unknown_group_operator", f"{path}.operator", "Group operator must be 'and' or 'or'")
		children = node.get("children")
		if not isinstance(children, list) or len(children) < 2:
			_fail(
				"invalid_group_children",
				f"{path}.children",
				"A persisted group must have at least two children",
			)
		for index, child in enumerate(children):
			_validate_node(
				child,
				path=f"{path}.children[{index}]",
				depth=depth + 1,
				counter=counter,
				allowed_scopes=allowed_scopes,
				scope_doctypes=scope_doctypes,
			)
		return

	if node_type == "comparison":
		operator_id = node.get("operator")
		spec = OPERATOR_REGISTRY.get(operator_id) if isinstance(operator_id, str) else None
		if spec is None:
			_fail("unknown_operator", f"{path}.operator", "Unknown canonical condition operator")
		if not isinstance(operator_id, str):
			_fail("unknown_operator", f"{path}.operator", "Unknown canonical condition operator")
		required = {"type", "operator", "left"}
		if spec.arity == 2:
			required.add("right")
		_exact_keys(node, required, path)
		left_type = validate_flex_value(
			node.get("left"),
			path=f"{path}.left",
			allowed_scopes=allowed_scopes,
		)
		right_type = None
		if spec.arity == 2:
			right_type = validate_flex_value(
				node.get("right"),
				path=f"{path}.right",
				allowed_scopes=allowed_scopes,
			)
		if not _known_type_compatible(left_type, spec.left_types):
			_fail(
				"operand_type_mismatch", f"{path}.left", "Left operand type is not supported by this operator"
			)
		if spec.arity == 2 and not _known_type_compatible(right_type, spec.right_types):
			_fail(
				"operand_type_mismatch",
				f"{path}.right",
				"Right operand type is not supported by this operator",
			)
		if spec.arity == 2:
			_types_compatible(left_type, right_type, operator_id, path)
			if operator_id in {"in", "not_in"}:
				_validate_membership_items(left_type, node.get("right"), path)
		left_value = node.get("left")
		if isinstance(left_value, Mapping) and left_value.get("mode") == "variable":
			path_value = left_value.get("path") or {}
			scope = path_value.get("scope")
			if not isinstance(scope, str):
				_fail("invalid_variable_scope", f"{path}.left.path.scope", "Variable scope must be a string")
			segments = tuple(path_value.get("segments") or ())
			fieldtype = resolve_fieldtype_for_path(scope, segments, scope_doctypes.get(scope))
			_known_fieldtype_check(operator_id, left_value, fieldtype, path, node.get("right"), right_type)
		if operator_id in {"is_submittable", "has_field"}:
			# Metadata checks accept explicit DocType names only; no arbitrary objects.
			for operand, operand_path in ((node.get("left"), f"{path}.left"),):
				if isinstance(operand, Mapping) and operand.get("mode") == "static":
					if operand.get("value_type") != "string":
						_fail(
							"invalid_metadata_operand",
							operand_path,
							"Metadata predicates require a DocType string",
						)
			if spec.arity == 2:
				right = node.get("right")
				if (
					isinstance(right, Mapping)
					and right.get("mode") == "static"
					and right.get("value_type") != "string"
				):
					_fail(
						"invalid_metadata_operand",
						f"{path}.right",
						"Metadata predicates require a field name string",
					)
		return

	if node_type == "collection_predicate":
		_exact_keys(node, {"type", "quantifier", "source", "as", "where"}, path)
		quantifier = node.get("quantifier")
		if not isinstance(quantifier, str) or quantifier not in {"any", "all", "none"}:
			_fail(
				"unknown_collection_quantifier", f"{path}.quantifier", "Quantifier must be any, all, or none"
			)
		source = node.get("source")
		source_scope, source_segments = _validate_source_path(source, f"{path}.source", allowed_scopes)
		alias = node.get("as")
		if (
			not isinstance(alias, str)
			or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", alias)
			or "__" in alias
			or alias in RESERVED_ALIASES
			or alias in allowed_scopes
		):
			_fail(
				"invalid_collection_alias",
				f"{path}.as",
				"Collection alias must be a safe, non-reserved identifier",
			)
		child_doctype = None
		parent_doctype = scope_doctypes.get(source_scope)
		if parent_doctype:
			try:
				meta = _meta_for(parent_doctype, f"{path}.source")
				current_meta = meta
				field = None
				for segment in source_segments:
					field = current_meta.get_field(segment)
					if not field:
						_fail(
							"unknown_field",
							f"{path}.source",
							"Collection source field does not exist on the declared DocType",
						)
					if segment != source_segments[-1]:
						if field.fieldtype in {"Table", "Table MultiSelect", "Link", "Dynamic Link"}:
							_fail(
								"unsupported_field_traversal",
								f"{path}.source",
								"Collection source paths cannot implicitly traverse collections or linked documents",
							)
						_fail(
							"invalid_collection_source",
							f"{path}.source",
							"Collection source path continues through a scalar field",
						)
				if field and field.fieldtype in {"Table", "Table MultiSelect"}:
					child_doctype = field.options
				elif field and field.fieldtype not in {"Table", "Table MultiSelect"}:
					_fail(
						"collection_source_not_table",
						f"{path}.source",
						"Collection source must reference a table/list field",
					)
			except ConditionValidationError:
				raise
		nested_scopes = set(allowed_scopes)
		nested_scopes.add(alias)
		nested_doctypes = dict(scope_doctypes)
		nested_doctypes[alias] = child_doctype
		nested_doctypes["row"] = child_doctype
		_validate_node(
			node.get("where"),
			path=f"{path}.where",
			depth=depth + 1,
			counter=counter,
			allowed_scopes=nested_scopes,
			scope_doctypes=nested_doctypes,
		)
		return

	if "type" in node:
		_fail("unknown_condition_node_type", f"{path}.type", "Unknown canonical condition node type")
	_fail(
		"missing_condition_node_type", f"{path}.type", "Canonical condition node requires a type discriminant"
	)


def _validate_source_path(source: Any, path: str, allowed_scopes: set[str]) -> tuple[str, tuple[str, ...]]:
	if not isinstance(source, Mapping):
		_fail("invalid_collection_source", path, "Collection source must be a path object")
	_exact_keys(source, {"scope", "segments"}, path)
	scope = source.get("scope")
	segments = source.get("segments")
	if not isinstance(scope, str) or scope not in allowed_scopes or scope == "doctype":
		_fail("unknown_scope", f"{path}.scope", "Collection source scope is not available")
	if not isinstance(segments, list) or not segments or len(segments) > CONDITION_LIMITS["path_segments"]:
		_fail(
			"invalid_collection_source",
			f"{path}.segments",
			"Collection source must have bounded, non-empty path segments",
		)
	for index, segment in enumerate(segments):
		if not isinstance(segment, str) or not re.fullmatch(r"[A-Za-z0-9_]+", segment) or "__" in segment:
			_fail("invalid_path_segment", f"{path}.segments[{index}]", "Unsafe or empty source path segment")
	return scope, tuple(segments)


def condition_contract_dto() -> dict[str, Any]:
	"""Build the authenticated API contract from the live backend registries."""
	from flexirule.ruleflow.core.flexvalue_contract import resolver_contract_dto

	return {
		"api_version": "1",
		"persisted_payload_version": None,
		"node_types": {
			"group": {
				"required_keys": ["type", "operator", "children"],
				"operators": ["and", "or"],
				"minimum_children": 2,
			},
			"comparison": {"required_keys": ["type", "operator", "left"], "right_key_by_arity": True},
			"collection_predicate": {
				"required_keys": ["type", "quantifier", "source", "as", "where"],
				"quantifiers": ["any", "all", "none"],
			},
		},
		"flexvalue_modes": {
			"static": sorted(VALUE_TYPES),
			"variable": {"scopes": sorted(BASE_SCOPES), "path_segment_limit": MAX_PATH_SEGMENTS},
			"resolver": resolver_contract_dto(),
			"template": {"segments": ["text", "value"], "maximum_segments": MAX_TEMPLATE_SEGMENTS},
		},
		"operators": operator_contract_dto(),
		"limits": dict(CONDITION_LIMITS),
		"semantics_version": CONDITION_SEMANTICS_VERSION,
	}
