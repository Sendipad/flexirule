# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Typed, short-circuiting evaluator for canonical direct-node conditions.

Canonical conditions are never converted to Python source and never pass through
eval, exec, or frappe.safe_eval. The bounded cached plan contains only immutable
structure and static values; runtime context and results are never cached.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from typing import Any, NoReturn

from flexirule.ruleflow.core.condition_contract import (
	CONDITION_SEMANTICS_VERSION,
	UNARY_OPERATORS,
	validate_condition_node,
)
from flexirule.ruleflow.core.condition_errors import ConditionEvaluationError, ConditionValidationError
from flexirule.ruleflow.core.flexvalue_contract import (
	CONDITION_LIMITS,
	CONDITION_RESOLVER_REGISTRY,
	MAX_CONDITION_PAYLOAD_BYTES,
	MAX_TEMPLATE_OUTPUT_CHARS,
	MISSING,
	format_template_value,
	parse_static_value,
	resolve_variable,
	resolver_registry_fingerprint,
)

EVALUATOR_CACHE_VERSION = 1
MAX_CACHEABLE_CONDITION_BYTES = 65536


class _EvaluationContext(dict):
	"""Dict-compatible user context with private, non-enumerable evaluation state."""

	__slots__ = ("collection_row_budget",)

	def __init__(self, source=None, budget=None):
		super().__init__(source or {})
		self.collection_row_budget = (
			budget if budget is not None else {"collection_row_visits": 0}
		)


def _child_context(context: dict | _EvaluationContext) -> _EvaluationContext:
	return _EvaluationContext(context, context.collection_row_budget)


def _freeze_json(value: Any) -> Any:
	if isinstance(value, dict):
		return ("__object__", tuple((key, _freeze_json(child)) for key, child in sorted(value.items())))
	if isinstance(value, list):
		return ("__list__", tuple(_freeze_json(child) for child in value))
	return value


def _thaw_json(value: Any) -> Any:
	if isinstance(value, tuple) and len(value) == 2 and value[0] == "__object__":
		return {key: _thaw_json(child) for key, child in value[1]}
	if isinstance(value, tuple) and len(value) == 2 and value[0] == "__list__":
		return [_thaw_json(child) for child in value[1]]
	return value


def _as_node(node: Any) -> dict:
	if isinstance(node, str):
		if len(node.encode("utf-8")) > MAX_CONDITION_PAYLOAD_BYTES:
			raise ConditionValidationError(
				"condition_payload_too_large", "$", "Condition payload exceeds the configured byte limit"
			)
		try:
			node = json.loads(node)
		except Exception as exc:
			raise ConditionValidationError("invalid_json", "$", "Condition JSON is malformed") from exc
	if not isinstance(node, dict):
		raise ConditionValidationError(
			"invalid_condition_node", "$", "Canonical condition must be a direct node"
		)
	return node


def compile_condition(node: Any, *, doctype: str | None = None) -> tuple:
	"""Validate and compile a canonical node into a reusable immutable execution plan."""
	condition_node = _as_node(node)
	try:
		payload_json = json.dumps(
			condition_node,
			ensure_ascii=False,
			sort_keys=True,
			separators=(",", ":"),
			allow_nan=False,
		)
	except (TypeError, ValueError, RecursionError) as exc:
		raise ConditionValidationError(
			"invalid_json_value", "$", "Condition payload is not valid JSON"
		) from exc
	payload_bytes = payload_json.encode("utf-8")
	if len(payload_bytes) > MAX_CONDITION_PAYLOAD_BYTES:
		raise ConditionValidationError(
			"condition_payload_too_large", "$", "Condition payload exceeds the configured byte limit"
		)
	payload_digest = hashlib.sha256(payload_bytes).hexdigest()
	registry_fingerprint = resolver_registry_fingerprint()
	cache_key = (
		payload_digest,
		payload_json,
		CONDITION_SEMANTICS_VERSION,
		EVALUATOR_CACHE_VERSION,
		registry_fingerprint,
		doctype or "",
	)
	# Do not retain unusually large source strings in the process-local LRU.
	# These still get full validation and plan compilation, just without caching.
	if len(payload_bytes) > MAX_CACHEABLE_CONDITION_BYTES:
		return _compile_cached.__wrapped__(*cache_key)
	return _compile_cached(*cache_key)


@lru_cache(maxsize=512)
def _compile_cached(
	payload_digest: str,
	payload_json: str,
	semantics_version: int,
	cache_version: int,
	registry_fingerprint: str,
	doctype: str,
) -> tuple:
	# payload_digest is part of the cache identity by design. Keep payload_json too
	# so a collision can never cause one condition to execute as another.
	if (
		not payload_digest
		or semantics_version != CONDITION_SEMANTICS_VERSION
		or cache_version != EVALUATOR_CACHE_VERSION
		or registry_fingerprint != resolver_registry_fingerprint()
		or hashlib.sha256(payload_json.encode("utf-8")).hexdigest() != payload_digest
	):
		raise ConditionValidationError(
			"condition_semantics_version", "$", "Unsupported condition semantics version"
		)
	try:
		node = json.loads(payload_json)
	except Exception as exc:
		raise ConditionValidationError("invalid_json", "$", "Condition JSON is malformed") from exc
	validate_condition_node(node, doctype=doctype or None)
	return _compile_node(node, "$")


def clear_condition_plan_cache() -> None:
	"""Clear only derived plans; saved JSON remains the source of truth."""
	_compile_cached.cache_clear()


def condition_plan_cache_info():
	"""Expose cache metrics for targeted tests/diagnostics without exposing plan content."""
	return _compile_cached.cache_info()


def _compile_node(node: dict, path: str) -> tuple:
	node_type = node["type"]
	if node_type == "group":
		return (
			"group",
			node["operator"],
			tuple(
				_compile_node(child, f"{path}.children[{index}]")
				for index, child in enumerate(node["children"])
			),
			path,
		)
	if node_type == "comparison":
		operator_id = node["operator"]
		left = _compile_value(node["left"], f"{path}.left")
		right = _compile_value(node["right"], f"{path}.right") if operator_id not in UNARY_OPERATORS else None
		return ("comparison", operator_id, left, right, path)
	if node_type == "collection_predicate":
		source = node["source"]
		return (
			"collection_predicate",
			node["quantifier"],
			source["scope"],
			tuple(source["segments"]),
			node["as"],
			_compile_node(node["where"], f"{path}.where"),
			path,
		)
	raise ConditionValidationError(
		"unknown_condition_node_type", f"{path}.type", "Unknown canonical node type"
	)


def _compile_value(value: dict, path: str) -> tuple:
	mode = value["mode"]
	if mode == "static":
		value_type = value["value_type"]
		static_value = parse_static_value(value_type, value["value"])
		if value_type in {"list", "object"}:
			static_value = _freeze_json(static_value)
		return ("static", value_type, static_value, path)
	if mode == "variable":
		path_value = value["path"]
		return ("variable", path_value["scope"], tuple(path_value["segments"]), path)
	if mode == "resolver":
		return (
			"resolver",
			value["family"],
			value["operation"],
			_freeze_json(value["config"]),
			path,
		)
	if mode == "template":
		segments = []
		for index, segment in enumerate(value["segments"]):
			segment_path = f"{path}.segments[{index}]"
			if segment["type"] == "text":
				segments.append(("text", segment["value"], segment_path))
			else:
				segments.append(
					("value", _compile_value(segment["value"], f"{segment_path}.value"), segment_path)
				)
		return ("template", tuple(segments), path)
	raise ConditionValidationError(
		"unknown_flex_value_mode", f"{path}.mode", "Unknown canonical FlexValue mode"
	)


def evaluate_condition(
	node: Any,
	context: dict | None = None,
	*,
	doctype: str | None = None,
	_evaluation_budget: dict[str, int] | None = None,
) -> bool:
	"""Evaluate one canonical node. Validation/runtime errors remain typed exceptions."""
	ctx = _EvaluationContext(
		context or {},
		_evaluation_budget if isinstance(_evaluation_budget, dict) else None,
	)
	effective_doctype = doctype or ctx.get("doctype")
	if not effective_doctype:
		doc = ctx.get("doc")
		effective_doctype = doc.get("doctype") if isinstance(doc, dict) else getattr(doc, "doctype", None)
	plan = compile_condition(node, doctype=effective_doctype)
	try:
		return bool(_evaluate_node(plan, ctx))
	except (ConditionValidationError, ConditionEvaluationError):
		raise
	except Exception as exc:
		raise ConditionEvaluationError(
			"runtime_error",
			plan[-1] if plan and isinstance(plan[-1], str) else "$",
			"Canonical condition evaluation failed",
		) from exc


def consume_collection_row_visit(budget: dict[str, int], path: str) -> None:
	"""Consume one unit from a shared budget, including when a resolver calls us repeatedly."""
	budget["collection_row_visits"] = budget.get("collection_row_visits", 0) + 1
	if budget["collection_row_visits"] > CONDITION_LIMITS["collection_row_visits"]:
		raise ConditionEvaluationError(
			"collection_evaluation_budget_exceeded",
			path,
			"Condition exceeded the configured total collection row-visit budget",
		)


def _consume_collection_row_budget(context: dict | _EvaluationContext, path: str) -> None:
	consume_collection_row_visit(context.collection_row_budget, path)


def _evaluate_node(plan: tuple, context: dict | _EvaluationContext) -> bool:
	kind = plan[0]
	if kind == "group":
		operator_id, children, path = plan[1], plan[2], plan[3]
		if operator_id == "and":
			for child in children:
				if not _evaluate_node(child, context):
					return False
			return True
		for child in children:
			if _evaluate_node(child, context):
				return True
		return False

	if kind == "comparison":
		_, operator_id, left_plan, right_plan, path = plan
		left = _evaluate_value(left_plan, context)
		if operator_id == "is_set":
			return left is not MISSING and left is not None and left != ""
		if operator_id == "is_not_set":
			return left is MISSING or left is None or left == ""
		if left is MISSING:
			raise ConditionEvaluationError("missing_operand", left_plan[-1], "Left operand path is missing")
		if operator_id == "is_null":
			return left is None
		if operator_id == "is_not_null":
			return left is not None
		if operator_id == "is_empty":
			return _is_empty(left, left_plan[-1])
		if operator_id == "is_not_empty":
			return not _is_empty(left, left_plan[-1])
		if operator_id == "is_submittable":
			return _is_submittable(left, left_plan[-1])
		if right_plan is None:
			raise ConditionEvaluationError(
				"invalid_operator_arity", path, "Operator requires a right operand"
			)
		right = _evaluate_value(right_plan, context)
		if right is MISSING:
			raise ConditionEvaluationError("missing_operand", right_plan[-1], "Right operand path is missing")
		if operator_id == "has_field":
			return _compare_metadata(operator_id, left, right, path)
		return _compare(operator_id, left, right, path)

	if kind == "collection_predicate":
		_, quantifier, source_scope, source_segments, alias, where_plan, path = plan
		rows = resolve_variable(source_scope, source_segments, context, f"{path}.source")
		if rows is MISSING:
			raise ConditionEvaluationError("missing_collection", f"{path}.source", "Collection source path is missing")
		if not isinstance(rows, list | tuple):
			raise ConditionEvaluationError(
				"invalid_collection", f"{path}.source", "Collection source must resolve to a list"
			)
		if len(rows) > CONDITION_LIMITS["collection_rows"]:
			raise ConditionEvaluationError(
				"collection_limit_exceeded",
				f"{path}.source",
				"Collection source exceeds the configured row limit",
			)
		if quantifier == "any":
			for row in rows:
				_consume_collection_row_budget(context, f"{path}.source")
				row_context = _child_context(context)
				row_context["row"] = row
				row_context[alias] = row
				if _evaluate_node(where_plan, row_context):
					return True
			return False
		if quantifier == "all":
			for row in rows:
				_consume_collection_row_budget(context, f"{path}.source")
				row_context = _child_context(context)
				row_context["row"] = row
				row_context[alias] = row
				if not _evaluate_node(where_plan, row_context):
					return False
			return True
		for row in rows:
			_consume_collection_row_budget(context, f"{path}.source")
			row_context = _child_context(context)
			row_context["row"] = row
			row_context[alias] = row
			if _evaluate_node(where_plan, row_context):
				return False
		return True

	raise ConditionEvaluationError("invalid_execution_plan", "$", "Unknown compiled condition node")


def _evaluate_value(plan: tuple, context: dict) -> Any:
	kind = plan[0]
	if kind == "static":
		value_type, value, path = plan[1], plan[2], plan[3]
		if value_type in {"list", "object"}:
			return _thaw_json(value)
		return value
	if kind == "variable":
		_, scope, segments, path = plan
		value = resolve_variable(scope, segments, context, path)
		if value is MISSING:
			return MISSING
		return _coerce_field_value(value, _fieldtype_for_context(scope, segments, context), path)
	if kind == "template":
		segments, path = plan[1], plan[2]
		parts = []
		output_length = 0
		for segment_kind, item, segment_path in segments:
			if segment_kind == "text":
				part = item
			else:
				resolved = _evaluate_value(item, context)
				if resolved is MISSING:
					raise ConditionEvaluationError(
						"missing_template_value", segment_path, "Template value path is missing"
					)
				part = format_template_value(resolved, segment_path)
			output_length += len(part)
			if output_length > MAX_TEMPLATE_OUTPUT_CHARS:
				raise ConditionEvaluationError(
					"template_output_too_large",
					path,
					"Resolved template exceeds the configured output limit",
				)
			parts.append(part)
		return "".join(parts)
	if kind == "resolver":
		_, family, operation, frozen_config, path = plan
		entry = CONDITION_RESOLVER_REGISTRY.get((family, operation))
		if not entry or not entry.get("condition_operand_allowed"):
			raise ConditionEvaluationError(
				"resolver_not_allowed", path, "Resolver operation is no longer approved"
			)
		try:
			resolved = entry["resolve"](_thaw_json(frozen_config), context)
			actual_type = _runtime_value_type(resolved, path)
			if actual_type != entry["output_type"]:
				raise ConditionEvaluationError(
					"resolver_output_type_mismatch",
					path,
					"Resolver output does not match its declared output type",
				)
			return resolved
		except ConditionEvaluationError:
			raise
		except Exception as exc:
			raise ConditionEvaluationError(
				"resolver_failed", path, "Condition resolver operation failed"
			) from exc
	raise ConditionEvaluationError("invalid_flexvalue_plan", "$", "Unknown compiled FlexValue")


def _fieldtype_for_context(scope: str, segments: tuple[str, ...], context: dict) -> str | None:
	if not segments or scope not in {"doc", "old_doc", "row"} and scope not in context:
		return None
	from flexirule.ruleflow.core.condition_contract import resolve_fieldtype_for_path

	root = context.get(scope)
	doctype = getattr(root, "doctype", None)
	if scope in {"doc", "old_doc"}:
		doctype = doctype or context.get("doctype")
	try:
		return resolve_fieldtype_for_path(scope, segments, doctype)
	except ConditionValidationError as exc:
		raise ConditionEvaluationError(exc.code, exc.path, exc.message) from exc


def _coerce_field_value(value: Any, fieldtype: str | None, path: str) -> Any:
	"""Convert Frappe's documented storage representations at the typed boundary."""
	if value is None or fieldtype is None:
		return value
	try:
		if fieldtype == "Check":
			if value in (0, 1, "0", "1", False, True):
				return bool(int(value))
			raise ValueError
		if fieldtype == "Int":
			if isinstance(value, bool):
				raise ValueError
			return int(value)
		if fieldtype in {"Float", "Currency", "Percent"}:
			if isinstance(value, bool):
				raise ValueError
			number = Decimal(str(value))
			if not number.is_finite():
				raise ValueError
			return number
		if fieldtype == "Date":
			if isinstance(value, date) and not isinstance(value, datetime):
				return value
			return date.fromisoformat(str(value))
		if fieldtype == "Datetime":
			if isinstance(value, datetime):
				return value
			return datetime.fromisoformat(str(value).replace(" ", "T", 1))
		if fieldtype == "Time":
			if isinstance(value, time):
				return value
			return time.fromisoformat(str(value))
	except (ValueError, TypeError, InvalidOperation) as exc:
		raise ConditionEvaluationError(
			"invalid_field_value", path, "Field value cannot be converted to its declared type"
		) from exc
	return value


def _is_numeric(value: Any) -> bool:
	return type(value) in (int, float) or isinstance(value, Decimal)


def _decimal(value: Any, path: str) -> Decimal:
	if isinstance(value, bool):
		raise ConditionEvaluationError("invalid_numeric_type", path, "Boolean values are not numbers")
	try:
		result = Decimal(str(value))
	except (InvalidOperation, ValueError) as exc:
		raise ConditionEvaluationError("invalid_numeric_type", path, "Value is not a valid number") from exc
	if not result.is_finite():
		raise ConditionEvaluationError("invalid_numeric_type", path, "Numeric values must be finite")
	return result


def _strict_equal(left: Any, right: Any, path: str) -> bool:
	if left is None or right is None:
		return left is right
	if isinstance(left, bool) or isinstance(right, bool):
		return isinstance(left, bool) and isinstance(right, bool) and left is right
	if _is_numeric(left) and _is_numeric(right):
		return _decimal(left, path) == _decimal(right, path)
	if type(left) is not type(right):
		return False
	if isinstance(left, list):
		return len(left) == len(right) and all(
			_strict_equal(a, b, path) for a, b in zip(left, right, strict=False)
		)
	if isinstance(left, dict):
		return left.keys() == right.keys() and all(_strict_equal(left[key], right[key], path) for key in left)
	return left == right


def _ordered_compare(operator_id: str, left: Any, right: Any, path: str) -> bool:
	if _is_numeric(left) and _is_numeric(right):
		left, right = _decimal(left, path), _decimal(right, path)
	elif type(left) is not type(right) or type(left) not in (date, datetime, time):
		raise ConditionEvaluationError(
			"operand_type_mismatch", path, "Ordered comparisons require matching numeric or date/time types"
		)
	try:
		if operator_id == "gt":
			return left > right
		if operator_id == "gte":
			return left >= right
		if operator_id == "lt":
			return left < right
		return left <= right
	except TypeError as exc:
		raise ConditionEvaluationError(
			"datetime_timezone_mismatch", path, "Datetime operands must use compatible timezone awareness"
		) from exc


def _runtime_value_type(value: Any, path: str) -> str:
	if value is None:
		return "null"
	if isinstance(value, bool):
		return "boolean"
	if isinstance(value, int) and not isinstance(value, bool):
		return "integer"
	if isinstance(value, Decimal):
		if not value.is_finite():
			raise ConditionEvaluationError(
				"non_finite_runtime_number", path, "Runtime numeric values must be finite"
			)
		return "decimal"
	if isinstance(value, float):
		if not math.isfinite(value):
			raise ConditionEvaluationError(
				"non_finite_runtime_number", path, "Runtime numeric values must be finite"
			)
		return "decimal"
	if isinstance(value, str):
		return "string"
	if isinstance(value, datetime):
		return "datetime"
	if isinstance(value, date):
		return "date"
	if isinstance(value, time):
		return "time"
	if isinstance(value, list):
		return "list"
	if isinstance(value, dict):
		return "object"
	raise ConditionEvaluationError(
		"unsupported_operand_type", path, "Operand type is not supported by canonical conditions"
	)


def _assert_runtime_equality_types(left: Any, right: Any, path: str) -> None:
	left_type = _runtime_value_type(left, path)
	right_type = _runtime_value_type(right, path)
	if left_type == "null" or right_type == "null":
		return
	if left_type in {"integer", "decimal"} and right_type in {"integer", "decimal"}:
		return
	if left_type != right_type:
		raise ConditionEvaluationError(
			"operand_type_mismatch", path, "Equality operands have incompatible runtime types"
		)


def _compare(operator_id: str, left: Any, right: Any, path: str) -> bool:
	if operator_id in {"eq", "ne"}:
		_assert_runtime_equality_types(left, right, path)
		equal = _strict_equal(left, right, path)
		return equal if operator_id == "eq" else not equal
	if operator_id in {"gt", "gte", "lt", "lte"}:
		return _ordered_compare(operator_id, left, right, path)
	if operator_id in {"in", "not_in"}:
		if not isinstance(right, list | tuple):
			raise ConditionEvaluationError("invalid_membership_rhs", path, "Membership requires a list")
		found = any(_strict_equal(left, candidate, path) for candidate in right)
		return found if operator_id == "in" else not found
	if operator_id in {"contains", "not_contains", "starts_with", "ends_with"}:
		if not isinstance(left, str) or not isinstance(right, str):
			raise ConditionEvaluationError(
				"operand_type_mismatch", path, "Text operators require string operands"
			)
		if operator_id == "contains":
			return right in left
		if operator_id == "not_contains":
			return right not in left
		if operator_id == "starts_with":
			return left.startswith(right)
		return left.endswith(right)
	if operator_id.startswith("length_"):
		if not isinstance(left, str | list | dict):
			raise ConditionEvaluationError("operand_type_mismatch", path, "Length operator requires a sized value")
		if not (isinstance(right, int) and not isinstance(right, bool)):
			raise ConditionEvaluationError("operand_type_mismatch", path, "Length comparison requires an integer")
		length = len(left)
		if operator_id == "length_eq":
			return length == right
		if operator_id == "length_gt":
			return length > right
		if operator_id == "length_gte":
			return length >= right
		if operator_id == "length_lt":
			return length < right
		return length <= right
	raise ConditionEvaluationError("unknown_operator", path, "Operator is not available to the canonical evaluator")


def _is_empty(value: Any, path: str) -> bool:
	if isinstance(value, str | list | dict):
		return len(value) == 0
	raise ConditionEvaluationError("operand_type_mismatch", path, "Emptiness operator requires string, list or object")


def _get_meta(doctype: Any, path: str):
	if not isinstance(doctype, str) or not doctype:
		raise ConditionEvaluationError("invalid_metadata_operand", path, "A DocType name is required")
	try:
		import frappe

		return frappe.get_meta(doctype)
	except Exception as exc:
		raise ConditionEvaluationError(
			"metadata_lookup_failed", path, "DocType metadata lookup failed"
		) from exc


def _is_submittable(doctype: Any, path: str) -> bool:
	meta = _get_meta(doctype, path)
	return bool(getattr(meta, "is_submittable", 0))


def _compare_metadata(operator_id: str, left: Any, right: Any, path: str) -> bool:
	if operator_id == "is_submittable":
		return _is_submittable(left, path)
	if operator_id == "has_field":
		if not isinstance(right, str) or not right:
			raise ConditionEvaluationError("invalid_metadata_operand", path, "A field name is required")
		return bool(_get_meta(left, path).has_field(right))
	return False
