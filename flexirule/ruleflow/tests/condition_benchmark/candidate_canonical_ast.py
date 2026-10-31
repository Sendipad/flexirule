# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Direct Canonical JSON AST Interpreter Benchmark Candidate.

Benchmark-only candidate evaluating validated canonical JSON direct-node condition
trees directly at runtime. It preserves the JSON AST structure (as a validated, immutable
snapshot) and never compiles the condition into a tuple plan, byte-code, or Python source.
Operands and branches are resolved strictly lazily at execution time.
"""

from __future__ import annotations

import copy
import json
import time
from typing import Any

import frappe

from flexirule.ruleflow.core.condition_contract import (
	UNARY_OPERATORS,
	validate_condition_node,
)
from flexirule.ruleflow.core.condition_errors import (
	ConditionEvaluationError,
	ConditionValidationError,
)
from flexirule.ruleflow.core.condition_evaluator import (
	_as_node,
	_child_context,
	_coerce_field_value,
	_compare,
	_compare_metadata,
	_consume_collection_row_budget,
	_context_doctype,
	_EvaluationContext,
	_fieldtype_for_context,
	_is_empty,
	_is_submittable,
)
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
from flexirule.ruleflow.tests.condition_benchmark.comparison_api import (
	BaseConditionCandidate,
	EvaluationResult,
	PreparedCondition,
)


def _build_canonical_context(document_context: Any, execution_context: dict | None = None) -> dict:
	"""Construct context dictionary for canonical condition evaluation."""
	if isinstance(document_context, dict) and "doc" in document_context:
		context = dict(document_context)
	else:
		context = {"doc": document_context or frappe._dict()}

	if execution_context:
		for k, v in execution_context.items():
			context[k] = v

	return context


class PreparedDirectCanonicalAST:
	"""Validated snapshot holding the raw canonical JSON AST and metadata context."""

	__slots__ = (
		"ast",
		"doctype",
		"resolver_fingerprint",
		"scope_doctypes",
	)

	def __init__(
		self,
		ast: dict,
		doctype: str | None = None,
		scope_doctypes: dict[str, str | None] | None = None,
		resolver_fingerprint: str | None = None,
	):
		self.ast = ast
		self.doctype = doctype
		self.scope_doctypes = scope_doctypes
		self.resolver_fingerprint = resolver_fingerprint or resolver_registry_fingerprint()


class DirectCanonicalASTCandidate(BaseConditionCandidate):
	"""Approach A: Direct Canonical JSON AST Interpreter (Benchmark-Only).

	Consumes canonical direct-node JSON, validates it once against authoritative Frappe
	and contract metadata during preparation, and evaluates the resulting AST directly
	without compiling it into an intermediate tuple plan.
	"""

	candidate_name = "Direct Canonical AST Interpreter"

	def prepare(
		self,
		condition_payload: Any,
		metadata_context: dict | None = None,
	) -> PreparedCondition:
		start_time = time.perf_counter()
		doctype = metadata_context.get("doctype") if metadata_context else None
		scope_doctypes = metadata_context.get("scope_doctypes") if metadata_context else None

		try:
			# 1. Normalize and check size limit (same as production pipeline)
			node = _as_node(condition_payload)
			payload_json = json.dumps(
				node,
				ensure_ascii=False,
				sort_keys=True,
				separators=(",", ":"),
				allow_nan=False,
			)
			if len(payload_json.encode("utf-8")) > MAX_CONDITION_PAYLOAD_BYTES:
				raise ConditionValidationError(
					"condition_payload_too_large",
					"$",
					"Condition payload exceeds the configured byte limit",
				)

			# 2. Immutable validated snapshot (deep copy / json clone)
			validated_node = json.loads(payload_json)

			# 3. Canonical validation against authoritative contract & DocType metadata
			validate_condition_node(
				validated_node,
				doctype=doctype,
				scope_doctypes=scope_doctypes,
			)

			prep_artifact = PreparedDirectCanonicalAST(
				ast=validated_node,
				doctype=doctype,
				scope_doctypes=scope_doctypes,
			)

			prep_time = time.perf_counter() - start_time
			return PreparedCondition(
				candidate_name=self.candidate_name,
				prepared_object=prep_artifact,
				preparation_time_seconds=prep_time,
				metadata={"ast_type": validated_node.get("type")},
			)
		except Exception as exc:
			prep_time = time.perf_counter() - start_time
			return PreparedCondition(
				candidate_name=self.candidate_name,
				prepared_object=None,
				preparation_time_seconds=prep_time,
				error=str(exc),
			)

	def evaluate(
		self,
		prepared_condition: PreparedCondition,
		document_context: Any,
		execution_context: dict | None = None,
	) -> EvaluationResult:
		if prepared_condition.error or prepared_condition.prepared_object is None:
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=None,
				execution_time_seconds=0.0,
				error=prepared_condition.error or "Missing prepared condition",
			)

		prep: PreparedDirectCanonicalAST = prepared_condition.prepared_object
		raw_context = _build_canonical_context(document_context, execution_context)
		context_doctype = _context_doctype(raw_context)

		effective_doctype = prep.doctype or context_doctype
		if prep.doctype is not None and effective_doctype and prep.doctype != effective_doctype:
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=None,
				execution_time_seconds=0.0,
				error="condition_doctype_mismatch at $: Prepared condition belongs to a different DocType",
			)

		# Wrap into typed EvaluationContext with collection budget tracking
		ctx = _EvaluationContext(raw_context)
		if effective_doctype:
			ctx["doctype"] = effective_doctype

		start_time = time.perf_counter()
		try:
			res = self._evaluate_node(prep.ast, ctx, path="$")
			exec_time = time.perf_counter() - start_time
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=bool(res),
				execution_time_seconds=exec_time,
			)
		except (ConditionValidationError, ConditionEvaluationError) as exc:
			exec_time = time.perf_counter() - start_time
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=None,
				execution_time_seconds=exec_time,
				error=f"{exc.code} at {exc.path}: {exc.message}",
			)
		except Exception as exc:
			exec_time = time.perf_counter() - start_time
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=None,
				execution_time_seconds=exec_time,
				error=f"runtime_error at $: {exc!s}",
			)

	def _evaluate_node(
		self,
		node: dict[str, Any],
		context: dict | _EvaluationContext,
		path: str = "$",
	) -> bool:
		node_type = node.get("type")

		# 1. Group Node: Strict short-circuit evaluation
		if node_type == "group":
			op = node.get("operator")
			children = node.get("children", [])
			if op == "and":
				for index, child in enumerate(children):
					child_path = f"{path}.children[{index}]"
					if not self._evaluate_node(child, context, child_path):
						return False
				return True
			elif op == "or":
				for index, child in enumerate(children):
					child_path = f"{path}.children[{index}]"
					if self._evaluate_node(child, context, child_path):
						return True
				return False
			raise ConditionEvaluationError("unknown_group_operator", f"{path}.operator", f"Unknown group operator {op}")

		# 2. Comparison Node: Strict lazy evaluation of left and right operands
		if node_type == "comparison":
			op = node.get("operator")
			left_val_node = node.get("left")
			left_path = f"{path}.left"

			left = self._evaluate_flex_value(left_val_node, context, left_path)

			if op == "is_set":
				return left is not MISSING and left is not None and left != ""
			if op == "is_not_set":
				return left is MISSING or left is None or left == ""

			if left is MISSING:
				raise ConditionEvaluationError("missing_operand", left_path, "Left operand path is missing")

			if op == "is_null":
				return left is None
			if op == "is_not_null":
				return left is not None
			if op == "is_empty":
				return _is_empty(left, left_path)
			if op == "is_not_empty":
				return not _is_empty(left, left_path)
			if op == "is_submittable":
				return _is_submittable(left, left_path)

			# Arity 2 operators: lazy evaluation of right operand
			if op in UNARY_OPERATORS:
				raise ConditionEvaluationError("invalid_operator_arity", path, f"Operator {op} does not accept a right operand")

			right_val_node = node.get("right")
			right_path = f"{path}.right"
			if right_val_node is None:
				raise ConditionEvaluationError("invalid_operator_arity", path, "Operator requires a right operand")

			right = self._evaluate_flex_value(right_val_node, context, right_path)
			if right is MISSING:
				raise ConditionEvaluationError("missing_operand", right_path, "Right operand path is missing")

			if op == "has_field":
				return _compare_metadata(op, left, right, path)
			return _compare(op, left, right, path)

		# 3. Collection Predicate: Bounded, short-circuiting iteration
		if node_type == "collection_predicate":
			quantifier = node.get("quantifier")
			source = node.get("source", {})
			source_scope = source.get("scope")
			source_segments = tuple(source.get("segments") or ())
			alias = node.get("as", "row")
			where_node = node.get("where", {})
			source_path = f"{path}.source"

			rows = resolve_variable(source_scope, source_segments, context, source_path)
			if rows is MISSING:
				raise ConditionEvaluationError("missing_collection", source_path, "Collection source path is missing")
			if not isinstance(rows, list | tuple):
				raise ConditionEvaluationError("invalid_collection", source_path, "Collection source must resolve to a list")
			if len(rows) > CONDITION_LIMITS["collection_rows"]:
				raise ConditionEvaluationError(
					"collection_limit_exceeded",
					source_path,
					"Collection source exceeds the configured row limit",
				)

			where_path = f"{path}.where"
			if quantifier == "any":
				for row in rows:
					_consume_collection_row_budget(context, source_path)
					row_context = _child_context(context)
					row_context["row"] = row
					row_context[alias] = row
					if self._evaluate_node(where_node, row_context, where_path):
						return True
				return False
			elif quantifier == "all":
				for row in rows:
					_consume_collection_row_budget(context, source_path)
					row_context = _child_context(context)
					row_context["row"] = row
					row_context[alias] = row
					if not self._evaluate_node(where_node, row_context, where_path):
						return False
				return True
			elif quantifier == "none":
				for row in rows:
					_consume_collection_row_budget(context, source_path)
					row_context = _child_context(context)
					row_context["row"] = row
					row_context[alias] = row
					if self._evaluate_node(where_node, row_context, where_path):
						return False
				return True
			raise ConditionEvaluationError("unknown_collection_quantifier", f"{path}.quantifier", f"Unknown quantifier {quantifier}")

		raise ConditionEvaluationError("invalid_condition_node", path, f"Unknown condition node type: {node_type}")

	def _evaluate_flex_value(
		self,
		val_node: dict[str, Any],
		context: dict | _EvaluationContext,
		path: str,
	) -> Any:
		if not isinstance(val_node, dict):
			raise ConditionEvaluationError("invalid_flex_value", path, "FlexValue must be an object")

		mode = val_node.get("mode")

		if mode == "static":
			value_type = val_node.get("value_type", "")
			raw_val = val_node.get("value")
			parsed = parse_static_value(value_type, raw_val)
			if value_type in {"list", "object"}:
				return copy.deepcopy(parsed)
			return parsed

		if mode == "variable":
			path_dict = val_node.get("path") or {}
			scope = path_dict.get("scope", "")
			segments = tuple(path_dict.get("segments") or ())
			value = resolve_variable(scope, segments, context, path)
			if value is MISSING:
				return MISSING
			fieldtype = _fieldtype_for_context(scope, segments, context)
			return _coerce_field_value(value, fieldtype, path)

		if mode == "template":
			segments = val_node.get("segments", [])
			parts = []
			output_length = 0
			for index, seg in enumerate(segments):
				seg_path = f"{path}.segments[{index}]"
				seg_type = seg.get("type")
				if seg_type == "text":
					part = str(seg.get("value", ""))
				else:
					nested_val = self._evaluate_flex_value(seg.get("value", {}), context, f"{seg_path}.value")
					if nested_val is MISSING:
						raise ConditionEvaluationError(
							"missing_template_value",
							seg_path,
							"Template value path is missing",
						)
					part = format_template_value(nested_val, seg_path)
				output_length += len(part)
				if output_length > MAX_TEMPLATE_OUTPUT_CHARS:
					raise ConditionEvaluationError(
						"template_output_too_large",
						path,
						"Resolved template exceeds the configured output limit",
					)
				parts.append(part)
			return "".join(parts)

		if mode == "resolver":
			family = val_node.get("family", "")
			operation = val_node.get("operation", "")
			config = val_node.get("config", {})
			entry = CONDITION_RESOLVER_REGISTRY.get((family, operation))
			if not entry or not entry.get("condition_operand_allowed"):
				raise ConditionEvaluationError(
					"resolver_not_allowed", path, "Resolver operation is no longer approved"
				)
			try:
				from flexirule.ruleflow.core.condition_evaluator import _runtime_value_type

				resolved = entry["resolve"](copy.deepcopy(config), context)
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

		raise ConditionEvaluationError("unknown_flex_value_mode", f"{path}.mode", f"Unknown FlexValue mode: {mode}")
