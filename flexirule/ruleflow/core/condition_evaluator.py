# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

import frappe

from flexirule.ruleflow.core.condition_contract import (
	CanonicalOperatorRegistry,
	validate_condition_node,
)
from flexirule.ruleflow.core.exceptions import RuleEngineError
from flexirule.ruleflow.core.flexvalue_contract import (
	MAX_COLLECTION_ROWS,
	MAX_CONDITION_DEPTH,
	MAX_CONDITION_NODES,
	validate_flexvalue,
)

# Private sentinel for missing paths
MISSING = object()


class ConditionEvaluationError(RuleEngineError):
	"""Raised when a condition evaluation encounters a runtime failure."""

	def __init__(self, message: str, code: str = "EVALUATION_ERROR", path: str = "$"):
		super().__init__(message)
		self.message = message
		self.code = code
		self.path = path

	def to_dict(self) -> dict[str, Any]:
		return {
			"error": self.message,
			"code": self.code,
			"path": self.path,
		}


def evaluate_canonical_condition(
	condition: dict[str, Any],
	context: dict[str, Any] | None = None,
) -> bool:
	"""
	Evaluate a canonical condition node directly against an execution context.

	Strictly enforces validation, limits, left-to-right short-circuit AND/OR,
	missing-value sentinel semantics, and scoped collection quantifiers.
	"""
	if context is None:
		context = {}

	# Ensure strictly valid canonical payload before evaluating
	validate_condition_node(condition)

	return _eval_node(condition, context=context, depth=0)


def _eval_node(node: dict[str, Any], context: dict[str, Any], depth: int) -> bool:
	if depth > MAX_CONDITION_DEPTH:
		raise ConditionEvaluationError(
			f"Maximum condition depth ({MAX_CONDITION_DEPTH}) exceeded during evaluation",
			code="LIMIT_EXCEEDED",
		)

	n_type = node.get("type")
	if n_type == "comparison":
		return _eval_comparison(node, context)
	elif n_type == "group":
		return _eval_group(node, context, depth=depth)
	elif n_type == "collection_predicate":
		return _eval_collection_predicate(node, context, depth=depth)
	else:
		raise ConditionEvaluationError(
			f"Unknown condition node type '{n_type}' during evaluation",
			code="INVALID_NODE_TYPE",
		)


def resolve_canonical_flexvalue(
	fv: dict[str, Any],
	context: dict[str, Any],
	path: str = "$",
) -> Any:
	"""
	Resolve a FlexValue operand against execution context.

	Returns value or MISSING sentinel for missing path segments.
	"""
	mode = fv.get("mode")
	if mode == "static":
		v_type = fv["value_type"]
		val = fv["value"]
		if v_type == "decimal" and val is not None:
			return Decimal(str(val))
		return val

	elif mode == "variable":
		p_data = fv["path"]
		scope = p_data["scope"]
		segments = p_data["segments"]

		# Scope lookup
		scope_obj = _get_scope_target(scope, context)
		if scope_obj is MISSING or scope_obj is None:
			return MISSING

		curr: Any = scope_obj
		for seg in segments:
			curr = _get_property_or_item(curr, seg)
			if curr is MISSING:
				return MISSING
		return curr

	elif mode == "resolver":
		family = fv.get("family")
		operation = fv.get("operation")
		raise ConditionEvaluationError(
			f"Resolver operation '{family}.{operation}' is not allowed as a condition operand",
			code="RESOLVER_DENIED",
			path=path,
		)

	elif mode == "template":
		segments = fv.get("segments", [])
		parts = []
		for seg in segments:
			if seg.get("type") == "text":
				parts.append(seg.get("text", ""))
			elif seg.get("type") == "value":
				resolved = resolve_canonical_flexvalue(seg["value"], context, path=path)
				if resolved is MISSING or resolved is None:
					parts.append("")
				else:
					parts.append(str(resolved))
		return "".join(parts)

	raise ConditionEvaluationError(f"Unknown FlexValue mode '{mode}'", code="INVALID_MODE", path=path)


def _get_scope_target(scope: str, context: dict[str, Any]) -> Any:
	if scope in context:
		return context[scope]

	# Frappe Document object compatibility if 'doc' is passed directly
	if scope == "doc" and "doc" in context:
		return context["doc"]

	return MISSING


def _get_property_or_item(obj: Any, key: str) -> Any:
	if obj is None or obj is MISSING:
		return MISSING

	if isinstance(obj, dict):
		return obj.get(key, MISSING)

	if hasattr(obj, "get") and callable(obj.get):
		res = obj.get(key)
		if res is not None:
			return res

	if hasattr(obj, key):
		val = getattr(obj, key)
		if not callable(val):
			return val

	return MISSING


def _eval_comparison(node: dict[str, Any], context: dict[str, Any]) -> bool:
	op_id = node["operator"]
	left_fv = node["left"]
	right_fv = node.get("right")

	left_val = resolve_canonical_flexvalue(left_fv, context, path="left")

	# Unary Presence & Nullness
	if op_id == "is_set":
		if left_val is MISSING or left_val is None or left_val == "":
			return False
		return True

	if op_id == "is_not_set":
		if left_val is MISSING or left_val is None or left_val == "":
			return True
		return False

	if op_id == "is_null":
		if left_val is MISSING:
			raise ConditionEvaluationError(
				"Cannot test 'is_null' on missing runtime path",
				code="MISSING_PATH",
			)
		return left_val is None

	if op_id == "is_not_null":
		if left_val is MISSING:
			raise ConditionEvaluationError(
				"Cannot test 'is_not_null' on missing runtime path",
				code="MISSING_PATH",
			)
		return left_val is not None

	if op_id == "is_empty":
		if left_val is MISSING:
			raise ConditionEvaluationError(
				"Cannot test 'is_empty' on missing runtime path",
				code="MISSING_PATH",
			)
		if left_val is None:
			raise ConditionEvaluationError(
				"Cannot test 'is_empty' on null value",
				code="NULL_VALUE",
			)
		if isinstance(left_val, (str, list, dict, tuple, set)):
			return len(left_val) == 0
		raise ConditionEvaluationError(
			f"Value of type {type(left_val).__name__} does not support emptiness test",
			code="TYPE_MISMATCH",
		)

	if op_id == "is_not_empty":
		return not _eval_comparison(
			{"operator": "is_empty", "left": left_fv}, context
		)

	if op_id == "has_field":
		doc = _get_scope_target("doc", context)
		if doc is MISSING or doc is None:
			return False
		fieldname = left_val if isinstance(left_val, str) else str(left_val)
		if isinstance(doc, dict):
			return fieldname in doc
		return hasattr(doc, fieldname)

	if op_id == "is_submittable":
		doc = _get_scope_target("doc", context)
		if doc is MISSING or doc is None:
			return False
		if hasattr(doc, "docstatus") or getattr(doc, "is_submittable", None):
			return bool(getattr(doc, "is_submittable", lambda: False)())
		return False

	# Binary operators require right_val
	right_val = resolve_canonical_flexvalue(right_fv, context, path="right")  # type: ignore

	if left_val is MISSING or right_val is MISSING:
		raise ConditionEvaluationError(
			f"Comparison '{op_id}' encountered missing runtime value",
			code="MISSING_PATH",
		)

	if op_id == "eq":
		return _are_equal(left_val, right_val)

	if op_id == "ne":
		return not _are_equal(left_val, right_val)

	if op_id in {"gt", "gte", "lt", "lte"}:
		return _compare_order(left_val, right_val, op_id)

	if op_id == "in":
		if not isinstance(right_val, (list, tuple, set, dict, str)):
			raise ConditionEvaluationError(
				f"Right operand for 'in' must be iterable, got {type(right_val).__name__}",
				code="TYPE_MISMATCH",
			)
		return left_val in right_val

	if op_id == "not_in":
		if not isinstance(right_val, (list, tuple, set, dict, str)):
			raise ConditionEvaluationError(
				f"Right operand for 'not_in' must be iterable, got {type(right_val).__name__}",
				code="TYPE_MISMATCH",
			)
		return left_val not in right_val

	if op_id in {"contains", "not_contains", "starts_with", "ends_with"}:
		if not isinstance(left_val, str) or not isinstance(right_val, str):
			raise ConditionEvaluationError(
				f"Text matching operator '{op_id}' requires string operands",
				code="TYPE_MISMATCH",
			)
		if op_id == "contains":
			return right_val in left_val
		if op_id == "not_contains":
			return right_val not in left_val
		if op_id == "starts_with":
			return left_val.startswith(right_val)
		if op_id == "ends_with":
			return left_val.endswith(right_val)

	if op_id.startswith("length_"):
		if not isinstance(left_val, (str, list, dict, tuple, set)):
			raise ConditionEvaluationError(
				f"Length operator '{op_id}' requires sized LHS",
				code="TYPE_MISMATCH",
			)
		try:
			rhs_num = int(right_val)
		except (ValueError, TypeError):
			raise ConditionEvaluationError(
				f"Length operator '{op_id}' requires integer RHS",
				code="TYPE_MISMATCH",
			)
		length = len(left_val)
		if op_id == "length_eq":
			return length == rhs_num
		if op_id == "length_gt":
			return length > rhs_num
		if op_id == "length_gte":
			return length >= rhs_num
		if op_id == "length_lt":
			return length < rhs_num
		if op_id == "length_lte":
			return length <= rhs_num

	raise ConditionEvaluationError(f"Unsupported operator '{op_id}'", code="UNKNOWN_OPERATOR")


def _are_equal(left: Any, right: Any) -> bool:
	# Strict type distinction for boolean vs zero
	if type(left) is bool or type(right) is bool:
		if type(left) is not type(right):
			return False
		return left is right

	# Decimal & numeric handling
	if isinstance(left, Decimal) or isinstance(right, Decimal):
		try:
			return Decimal(str(left)) == Decimal(str(right))
		except (InvalidOperation, TypeError, ValueError):
			return False

	return left == right


def _compare_order(left: Any, right: Any, op: str) -> bool:
	if isinstance(left, Decimal) or isinstance(right, Decimal):
		try:
			l_dec = Decimal(str(left))
			r_dec = Decimal(str(right))
			if op == "gt":
				return l_dec > r_dec
			if op == "gte":
				return l_dec >= r_dec
			if op == "lt":
				return l_dec < r_dec
			if op == "lte":
				return l_dec <= r_dec
		except (InvalidOperation, TypeError, ValueError):
			raise ConditionEvaluationError("Numeric comparison error for Decimal", code="TYPE_MISMATCH")

	try:
		if op == "gt":
			return left > right
		if op == "gte":
			return left >= right
		if op == "lt":
			return left < right
		if op == "lte":
			return left <= right
	except TypeError as e:
		raise ConditionEvaluationError(
			f"Cannot compare {type(left).__name__} and {type(right).__name__}",
			code="TYPE_MISMATCH",
		) from e

	return False


def _eval_group(node: dict[str, Any], context: dict[str, Any], depth: int) -> bool:
	op = node["operator"]
	children = node["children"]

	if op == "and":
		for child in children:
			res = _eval_node(child, context, depth=depth + 1)
			if not res:
				return False  # Short-circuit AND
		return True

	elif op == "or":
		for child in children:
			res = _eval_node(child, context, depth=depth + 1)
			if res:
				return True  # Short-circuit OR
		return False

	raise ConditionEvaluationError(f"Unknown group operator '{op}'", code="INVALID_GROUP_OPERATOR")


def _eval_collection_predicate(
	node: dict[str, Any],
	context: dict[str, Any],
	depth: int,
) -> bool:
	quantifier = node["quantifier"]
	source_fv = node["source"]
	alias = node["as"]
	where_node = node["where"]

	collection = resolve_canonical_flexvalue(source_fv, context, path="source")
	if collection is MISSING or collection is None:
		raise ConditionEvaluationError("Collection source is missing or null", code="MISSING_COLLECTION")

	if not isinstance(collection, (list, tuple)):
		raise ConditionEvaluationError(
			f"Collection source must be a list or tuple, got {type(collection).__name__}",
			code="TYPE_MISMATCH",
		)

	if len(collection) > MAX_COLLECTION_ROWS:
		raise ConditionEvaluationError(
			f"Collection row count ({len(collection)}) exceeds maximum limit of {MAX_COLLECTION_ROWS}",
			code="COLLECTION_ROW_LIMIT_EXCEEDED",
		)

	for item in collection:
		row_context = dict(context)
		row_context[alias] = item
		# Also bind 'row' and 'item' if not conflicting
		row_context["row"] = item
		row_context["item"] = item

		res = _eval_node(where_node, row_context, depth=depth + 1)

		if quantifier == "any" and res:
			return True  # Short-circuit ANY
		elif quantifier == "all" and not res:
			return False  # Short-circuit ALL
		elif quantifier == "none" and res:
			return False  # Short-circuit NONE

	if quantifier == "any":
		return False
	elif quantifier == "all":
		return True
	elif quantifier == "none":
		return True

	raise ConditionEvaluationError(f"Unknown quantifier '{quantifier}'", code="INVALID_QUANTIFIER")
