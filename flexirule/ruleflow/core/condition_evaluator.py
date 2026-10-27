"""
Direct Typed AST Evaluator for Canonical Conditions

Traverses and evaluates canonical condition JSON objects directly.
Does NOT generate Python source and does NOT use eval/exec/safe_eval.
"""

from decimal import Decimal, InvalidOperation
from typing import Any

import frappe
from flexirule.ruleflow.core.condition_contract import (
	CanonicalOperatorRegistry,
	validate_condition_payload,
)
from flexirule.ruleflow.core.flexvalue_contract import (
	MAX_COLLECTION_ROWS,
	FlexValueResolverRegistry,
	validate_flex_value,
)


class PrivateMissingSentinel:
	"""Private sentinel representing a missing property/path during evaluation."""

	pass


MISSING = PrivateMissingSentinel()


class ConditionEvaluationError(RuntimeError):
	"""Raised when evaluation fails due to missing values, type mismatches, or limit breaches."""

	def __init__(self, message: str, code: str = "EVALUATION_ERROR", path: str = "$"):
		super().__init__(f"[{code}] {path}: {message}" if path else f"[{code}] {message}")
		self.message = message
		self.code = code
		self.path = path


class CanonicalConditionEvaluator:
	"""Evaluates canonical condition AST directly against evaluation context."""

	def __init__(
		self, context: dict[str, Any] | None = None, allowed_scopes: set | None = None
	):
		self.context = context or {}
		self.allowed_scopes = allowed_scopes

	def evaluate(self, node: dict) -> bool:
		"""
		Validates and evaluates a canonical condition node.
		Returns True or False. Raises ConditionValidationError or ConditionEvaluationError on failure.
		"""
		validate_condition_payload(node, allowed_scopes=self.allowed_scopes)
		return self._evaluate_node(node, "$")

	def _evaluate_node(self, node: dict, path: str) -> bool:
		node_type = node["type"]

		if node_type == "group":
			return self._evaluate_group(node, path)
		elif node_type == "comparison":
			return self._evaluate_comparison(node, path)
		elif node_type == "collection_predicate":
			return self._evaluate_collection_predicate(node, path)
		else:
			raise ConditionEvaluationError(
				f"Unsupported node type '{node_type}'", "INVALID_NODE_TYPE", path
			)

	def _evaluate_group(self, node: dict, path: str) -> bool:
		group_op = node["operator"]
		children = node["children"]

		if group_op == "and":
			for idx, child in enumerate(children):
				res = self._evaluate_node(child, f"{path}.children[{idx}]")
				if not res:
					# Short-circuit: stop evaluating rest of AND children
					return False
			return True

		elif group_op == "or":
			for idx, child in enumerate(children):
				res = self._evaluate_node(child, f"{path}.children[{idx}]")
				if res:
					# Short-circuit: stop evaluating rest of OR children
					return True
			return False

		raise ConditionEvaluationError(
			f"Invalid group operator '{group_op}'", "INVALID_GROUP_OP", path
		)

	def _evaluate_comparison(self, node: dict, path: str) -> bool:
		op_id = node["operator"]
		op_meta = CanonicalOperatorRegistry.get(op_id)
		if not op_meta:
			raise ConditionEvaluationError(
				f"Unknown operator '{op_id}'", "UNKNOWN_OPERATOR", path
			)

		is_meta = op_meta.get("is_metadata_operator", False)

		# Resolve left operand
		left_val = self._resolve_flex_value(node["left"], f"{path}.left")

		# Handle explicit metadata operators separately
		if is_meta:
			return self._evaluate_metadata_operator(op_id, left_val, node, path)

		# Unary operators
		if op_meta["arity"] == 1:
			return self._evaluate_unary_operator(op_id, left_val, path)

		# Binary operators
		right_val = self._resolve_flex_value(node["right"], f"{path}.right")
		return self._evaluate_binary_operator(op_id, left_val, right_val, path)

	def _evaluate_metadata_operator(
		self, op_id: str, left_val: Any, node: dict, path: str
	) -> bool:
		if left_val is MISSING or left_val is None:
			raise ConditionEvaluationError(
				"Metadata operator require a valid DocType name",
				"MISSING_OPERAND",
				f"{path}.left",
			)

		if not isinstance(left_val, str) or not left_val:
			raise ConditionEvaluationError(
				"Metadata operator left operand must be a non-empty string",
				"INVALID_TYPE",
				f"{path}.left",
			)

		doctype = left_val

		if op_id == "is_submittable":
			try:
				meta = frappe.get_meta(doctype)
				return bool(meta.is_submittable)
			except Exception as e:
				raise ConditionEvaluationError(
					f"DocType '{doctype}' metadata lookup failed: {e!s}",
					"METADATA_ERROR",
					f"{path}.left",
				)

		elif op_id == "has_field":
			right_val = self._resolve_flex_value(node["right"], f"{path}.right")
			if (
				right_val is MISSING
				or right_val is None
				or not isinstance(right_val, str)
				or not right_val
			):
				raise ConditionEvaluationError(
					"has_field right operand must be a non-empty fieldname string",
					"INVALID_TYPE",
					f"{path}.right",
				)

			fieldname = right_val
			try:
				meta = frappe.get_meta(doctype)
				return meta.has_field(fieldname)
			except Exception as e:
				raise ConditionEvaluationError(
					f"DocType '{doctype}' field lookup failed: {e!s}",
					"METADATA_ERROR",
					f"{path}.right",
				)

		raise ConditionEvaluationError(
			f"Unhandled metadata operator '{op_id}'", "UNKNOWN_OPERATOR", path
		)

	def _evaluate_unary_operator(self, op_id: str, val: Any, path: str) -> bool:
		if op_id == "is_set":
			if val is MISSING or val is None:
				return False
			if isinstance(val, str) and len(val) == 0:
				return False
			return True

		elif op_id == "is_not_set":
			return not self._evaluate_unary_operator("is_set", val, path)

		elif op_id == "is_null":
			if val is MISSING:
				raise ConditionEvaluationError(
					"Cannot check is_null on a missing variable", "MISSING_PATH", path
				)
			return val is None

		elif op_id == "is_not_null":
			if val is MISSING:
				raise ConditionEvaluationError(
					"Cannot check is_not_null on a missing variable", "MISSING_PATH", path
				)
			return val is not None

		elif op_id == "is_empty":
			if val is MISSING or val is None:
				return True
			if isinstance(val, str | list | dict | set | tuple):
				return len(val) == 0
			return False

		elif op_id == "is_not_empty":
			return not self._evaluate_unary_operator("is_empty", val, path)

		raise ConditionEvaluationError(
			f"Unhandled unary operator '{op_id}'", "UNKNOWN_OPERATOR", path
		)

	def _evaluate_binary_operator(
		self, op_id: str, left: Any, right: Any, path: str
	) -> bool:
		# Unexpected MISSING operands raise evaluation errors unless unary checks handled them
		if left is MISSING or right is MISSING:
			raise ConditionEvaluationError(
				"Cannot perform binary comparison on missing operand", "MISSING_OPERAND", path
			)

		# Handle length operators
		if op_id.startswith("length_"):
			if not isinstance(left, str | list | dict | tuple | set) and left is not None:
				raise ConditionEvaluationError(
					"Length operator requires iterable/string left operand",
					"INVALID_TYPE",
					f"{path}.left",
				)

			l_len = len(left) if left is not None else 0
			try:
				r_num = int(right)
			except (ValueError, TypeError):
				raise ConditionEvaluationError(
					"Length operator right operand must be an integer",
					"INVALID_TYPE",
					f"{path}.right",
				)

			sub_op = op_id.replace("length_", "")
			if sub_op == "eq":
				return l_len == r_num
			elif sub_op == "gt":
				return l_len > r_num
			elif sub_op == "gte":
				return l_len >= r_num
			elif sub_op == "lt":
				return l_len < r_num
			elif sub_op == "lte":
				return l_len <= r_num

		if op_id == "eq":
			return self._safe_equals(left, right)
		elif op_id == "ne":
			return not self._safe_equals(left, right)

		if op_id in ("gt", "gte", "lt", "lte"):
			left_num, right_num = self._coerce_numeric_comparison(left, right, path)
			if op_id == "gt":
				return left_num > right_num
			elif op_id == "gte":
				return left_num >= right_num
			elif op_id == "lt":
				return left_num < right_num
			elif op_id == "lte":
				return left_num <= right_num

		if op_id == "in":
			if not isinstance(right, list | set | tuple | dict | str):
				raise ConditionEvaluationError(
					"'in' operator right operand must be a collection/string",
					"INVALID_TYPE",
					f"{path}.right",
				)
			return left in right

		if op_id == "not_in":
			return not self._evaluate_binary_operator("in", left, right, path)

		if op_id == "contains":
			if not isinstance(left, list | set | tuple | dict | str):
				raise ConditionEvaluationError(
					"'contains' operator left operand must be a collection/string",
					"INVALID_TYPE",
					f"{path}.left",
				)
			return right in left

		if op_id == "not_contains":
			return not self._evaluate_binary_operator("contains", left, right, path)

		if op_id in ("starts_with", "ends_with"):
			if not isinstance(left, str) or not isinstance(right, str):
				raise ConditionEvaluationError(
					"String prefix/suffix matching requires string operands",
					"INVALID_TYPE",
					path,
				)
			return left.startswith(right) if op_id == "starts_with" else left.endswith(right)

		raise ConditionEvaluationError(
			f"Unhandled binary operator '{op_id}'", "UNKNOWN_OPERATOR", path
		)

	def _safe_equals(self, left: Any, right: Any) -> bool:
		# Strict typed equality: False and 0 are distinct!
		if isinstance(left, bool) or isinstance(right, bool):
			if type(left) is not type(right):
				return False
			return left == right

		# Decimal / Numeric comparison
		if isinstance(left, int | float | Decimal) and isinstance(
			right, int | float | Decimal
		):
			return Decimal(str(left)) == Decimal(str(right))

		return left == right

	def _coerce_numeric_comparison(
		self, left: Any, right: Any, path: str
	) -> tuple[Decimal, Decimal]:
		if isinstance(left, bool) or isinstance(right, bool):
			raise ConditionEvaluationError(
				"Boolean values cannot be used in numeric inequality comparisons",
				"TYPE_MISMATCH",
				path,
			)

		try:
			l_dec = Decimal(str(left))
			r_dec = Decimal(str(right))
			return l_dec, r_dec
		except (InvalidOperation, ValueError, TypeError):
			raise ConditionEvaluationError(
				"Inequality comparisons require numeric operands", "TYPE_MISMATCH", path
			)

	def _evaluate_collection_predicate(self, node: dict, path: str) -> bool:
		source_rows = self._resolve_flex_value(node["source"], f"{path}.source")
		if source_rows is MISSING or source_rows is None:
			source_rows = []

		if not isinstance(source_rows, list):
			raise ConditionEvaluationError(
				"Collection predicate source must resolve to a list",
				"INVALID_COLLECTION_SOURCE",
				f"{path}.source",
			)

		if len(source_rows) > MAX_COLLECTION_ROWS:
			raise ConditionEvaluationError(
				f"Collection rows ({len(source_rows)}) exceed max limit of {MAX_COLLECTION_ROWS}",
				"LIMIT_EXCEEDED",
				f"{path}.source",
			)

		quantifier = node["quantifier"]
		alias = node["as"]
		where_node = node["where"]

		match_count = 0
		total_rows = len(source_rows)

		base_scopes = self.allowed_scopes or {"doc", "vars", "system", "env"}
		scoped_allowed_scopes = set(base_scopes) | {alias}

		for _idx, row in enumerate(source_rows):
			# Create sub-evaluator with scoped item alias context
			scoped_ctx = dict(self.context)
			scoped_ctx[alias] = row
			sub_evaluator = CanonicalConditionEvaluator(
				scoped_ctx, allowed_scopes=scoped_allowed_scopes
			)

			row_result = sub_evaluator._evaluate_node(where_node, f"{path}.where")

			if row_result:
				match_count += 1
				if quantifier == "any":
					return True  # Short-circuit on first match

		if quantifier == "any":
			return False
		elif quantifier == "all":
			return match_count == total_rows
		elif quantifier == "none":
			return match_count == 0

		raise ConditionEvaluationError(
			f"Invalid quantifier '{quantifier}'", "INVALID_QUANTIFIER", path
		)

	def _resolve_flex_value(self, flex_value: dict, path: str) -> Any:
		validate_flex_value(flex_value, path, allowed_scopes=self.allowed_scopes)
		mode = flex_value["mode"]

		if mode == "static":
			val_type = flex_value["value_type"]
			val = flex_value["value"]
			if val_type == "decimal":
				return Decimal(str(val))
			return val

		elif mode == "variable":
			path_obj = flex_value["path"]
			scope = path_obj["scope"]
			segments = path_obj["segments"]

			curr = self.context.get(scope, MISSING)
			if curr is MISSING:
				return MISSING

			for seg in segments:
				if curr is MISSING or curr is None:
					return MISSING
				if isinstance(curr, dict):
					curr = curr.get(seg, MISSING)
				elif hasattr(curr, seg):
					curr = getattr(curr, seg, MISSING)
				else:
					return MISSING
			return curr

		elif mode == "resolver":
			family = flex_value["family"]
			operation = flex_value["operation"]

			# Check if allowed as condition operand
			if not FlexValueResolverRegistry.is_allowed_as_condition_operand(
				family, operation
			):
				raise ConditionEvaluationError(
					f"Resolver operation '{family}.{operation}' is not allowed as a condition operand",
					"RESOLVER_DISALLOWED",
					path,
				)

			raise ConditionEvaluationError(
				f"Resolver execution for '{family}.{operation}' is disabled in core evaluator",
				"RESOLVER_UNSUPPORTED",
				path,
			)

		elif mode == "template":
			segments = flex_value["segments"]
			parts = []
			for idx, seg in enumerate(segments):
				if isinstance(seg, str):
					parts.append(seg)
				elif isinstance(seg, dict):
					res = self._resolve_flex_value(seg, f"{path}.segments[{idx}]")
					parts.append("" if res in (MISSING, None) else str(res))
			return "".join(parts)

		raise ConditionEvaluationError(
			f"Invalid FlexValue mode '{mode}'", "INVALID_FLEXVALUE_MODE", path
		)
