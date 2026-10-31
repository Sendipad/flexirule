# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Direct Canonical JSON AST Interpreter Benchmark Candidate.

Evaluates canonical condition JSON trees directly at runtime without compiling
them into an intermediate tuple plan or generating Python bytecode/source.

Validates the canonical condition JSON once at preparation time and retains the
validated, immutable JSON AST structure. Operands and branch children are evaluated
lazily at runtime strictly when reached.
"""

from __future__ import annotations

import copy
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

import frappe

from flexirule.ruleflow.core.condition_contract import (
	CONDITION_SEMANTICS_VERSION,
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
	_runtime_value_type,
)
from flexirule.ruleflow.core.flexvalue_contract import (
	CONDITION_LIMITS,
	CONDITION_RESOLVER_REGISTRY,
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

_DIRECT_AST_SEAL = object()


@dataclass(frozen=True)
class _PreparedCanonicalAST:
	"""Opaque, validated canonical AST artifact for direct interpretation."""

	ast: dict[str, Any]
	doctype: str | None
	scope_doctypes: tuple[tuple[str, str | None], ...] | None
	condition_digest: str
	semantics_version: int
	resolver_fingerprint: str
	_seal: object


def prepare_canonical_ast(
	node: Any,
	*,
	doctype: str | None = None,
	scope_doctypes: dict[str, str | None] | None = None,
) -> _PreparedCanonicalAST:
	"""Validate once and snapshot the canonical AST for repeated direct interpretation.

	Does not compile into a tuple plan. Validates the structural JSON AST and metadata
	freshness, matching the lifecycle boundaries of prepare_condition.
	"""
	raw_node = _as_node(node)
	try:
		payload_json = json.dumps(raw_node, sort_keys=True, separators=(",", ":"))
	except (TypeError, ValueError) as exc:
		raise ConditionValidationError("invalid_json", "$", "Condition payload is not JSON-serializable") from exc

	payload_bytes = payload_json.encode("utf-8")
	if len(payload_bytes) > CONDITION_LIMITS["payload_bytes"]:
		raise ConditionValidationError("payload_too_large", "$", "Condition payload exceeds the configured byte limit")

	payload_digest = hashlib.sha256(payload_bytes).hexdigest()
	registry_fingerprint = resolver_registry_fingerprint()

	try:
		validated_node = json.loads(payload_json)
	except Exception as exc:
		raise ConditionValidationError("invalid_json", "$", "Condition JSON is malformed") from exc

	validate_condition_node(validated_node, doctype=doctype, scope_doctypes=scope_doctypes)

	scope_doctypes_frozen = (
		tuple(sorted((k, v) for k, v in scope_doctypes.items())) if scope_doctypes else None
	)

	return _PreparedCanonicalAST(
		ast=validated_node,
		doctype=doctype or None,
		scope_doctypes=scope_doctypes_frozen,
		condition_digest=payload_digest,
		semantics_version=CONDITION_SEMANTICS_VERSION,
		resolver_fingerprint=registry_fingerprint,
		_seal=_DIRECT_AST_SEAL,
	)


def evaluate_prepared_canonical_ast(
	prepared: Any,
	context: dict | None = None,
	*,
	doctype: str | None = None,
	_evaluation_budget: dict[str, int] | None = None,
) -> bool:
	"""Directly interpret a validated canonical AST without compiling into a tuple plan."""
	if (
		not isinstance(prepared, _PreparedCanonicalAST)
		or prepared._seal is not _DIRECT_AST_SEAL
	):
		raise ConditionValidationError(
			"untrusted_prepared_condition",
			"$",
			"Prepared AST conditions must be created by prepare_canonical_ast",
		)
	if prepared.semantics_version != CONDITION_SEMANTICS_VERSION:
		raise ConditionValidationError(
			"condition_semantics_version", "$", "Prepared condition uses an unsupported semantics version"
		)
	if prepared.resolver_fingerprint != resolver_registry_fingerprint():
		raise ConditionValidationError(
			"condition_resolver_registry_changed",
			"$",
			"Resolver registry changed after this condition was prepared",
		)

	context_doctype = _context_doctype(context)
	if doctype and context_doctype and doctype != context_doctype:
		raise ConditionValidationError(
			"condition_doctype_mismatch", "$", "Explicit DocType disagrees with the execution context"
		)
	effective_doctype = doctype or context_doctype
	if prepared.doctype is None:
		if effective_doctype:
			raise ConditionValidationError(
				"condition_doctype_unvalidated",
				"$",
				"Prepare this condition with the execution DocType before evaluating it",
			)
	elif effective_doctype and prepared.doctype != effective_doctype:
		raise ConditionValidationError(
			"condition_doctype_mismatch", "$", "Prepared condition belongs to a different DocType"
		)
	else:
		effective_doctype = prepared.doctype

	if prepared.scope_doctypes:
		for scope, s_doctype in prepared.scope_doctypes:
			if s_doctype and isinstance(context, dict):
				ctx_root = context.get(scope)
				ctx_doctype = getattr(ctx_root, "doctype", None) or (
					ctx_root.get("doctype") if isinstance(ctx_root, dict) else None
				)
				if ctx_doctype and ctx_doctype != s_doctype:
					raise ConditionValidationError(
						"condition_doctype_mismatch",
						"$",
						f"Prepared condition scope '{scope}' belongs to a different DocType ('{s_doctype}' vs '{ctx_doctype}')",
					)

	ctx = _EvaluationContext(
		context or {},
		_evaluation_budget if isinstance(_evaluation_budget, dict) else None,
	)
	if effective_doctype:
		ctx["doctype"] = effective_doctype

	try:
		return bool(_evaluate_ast_node(prepared.ast, ctx, "$"))
	except (ConditionValidationError, ConditionEvaluationError):
		raise
	except Exception as exc:
		raise ConditionEvaluationError(
			"runtime_error",
			"$",
			"Canonical AST condition evaluation failed",
		) from exc


def evaluate_canonical_ast(
	node: Any,
	context: dict | None = None,
	*,
	doctype: str | None = None,
	scope_doctypes: dict[str, str | None] | None = None,
	_evaluation_budget: dict[str, int] | None = None,
) -> bool:
	"""Public one-shot API: validate AST and interpret directly."""
	effective_doctype = _context_doctype(context, doctype)
	prepared = prepare_canonical_ast(node, doctype=effective_doctype, scope_doctypes=scope_doctypes)
	return evaluate_prepared_canonical_ast(
		prepared,
		context,
		doctype=effective_doctype,
		_evaluation_budget=_evaluation_budget,
	)


def _evaluate_ast_node(node: dict[str, Any], context: dict | _EvaluationContext, path: str) -> bool:
	"""Directly interpret one canonical condition node (group, comparison, collection_predicate)."""
	node_type = node.get("type")
	if node_type == "group":
		operator_id = node["operator"]
		children = node.get("children", [])
		if operator_id == "and":
			for index, child in enumerate(children):
				child_path = f"{path}.children[{index}]"
				if not _evaluate_ast_node(child, context, child_path):
					return False
			return True
		# or
		for index, child in enumerate(children):
			child_path = f"{path}.children[{index}]"
			if _evaluate_ast_node(child, context, child_path):
				return True
		return False

	if node_type == "comparison":
		operator_id = node["operator"]
		left_val_def = node["left"]
		left_path = f"{path}.left"
		left = _evaluate_ast_value(left_val_def, context, left_path)

		if operator_id == "is_set":
			return left is not MISSING and left is not None and left != ""
		if operator_id == "is_not_set":
			return left is MISSING or left is None or left == ""
		if left is MISSING:
			raise ConditionEvaluationError("missing_operand", left_path, "Left operand path is missing")
		if operator_id == "is_null":
			return left is None
		if operator_id == "is_not_null":
			return left is not None
		if operator_id == "is_empty":
			return _is_empty(left, left_path)
		if operator_id == "is_not_empty":
			return not _is_empty(left, left_path)
		if operator_id == "is_submittable":
			return _is_submittable(left, left_path)

		if operator_id in UNARY_OPERATORS or "right" not in node:
			raise ConditionEvaluationError(
				"invalid_operator_arity", path, "Operator requires a right operand"
			)

		right_val_def = node["right"]
		right_path = f"{path}.right"
		right = _evaluate_ast_value(right_val_def, context, right_path)
		if right is MISSING:
			raise ConditionEvaluationError("missing_operand", right_path, "Right operand path is missing")
		if operator_id == "has_field":
			return _compare_metadata(operator_id, left, right, path)
		return _compare(operator_id, left, right, path)

	if node_type == "collection_predicate":
		quantifier = node["quantifier"]
		source = node["source"]
		source_scope = source["scope"]
		source_segments = tuple(source["segments"])
		alias = node.get("as", "item_row")
		where_node = node["where"]
		source_path = f"{path}.source"

		rows = resolve_variable(source_scope, source_segments, context, source_path)
		if rows is MISSING:
			raise ConditionEvaluationError(
				"missing_collection", source_path, "Collection source path is missing"
			)
		if not isinstance(rows, list | tuple):
			raise ConditionEvaluationError(
				"invalid_collection", source_path, "Collection source must resolve to a list"
			)
		if len(rows) > CONDITION_LIMITS["collection_rows"]:
			raise ConditionEvaluationError(
				"collection_limit_exceeded",
				source_path,
				"Collection source exceeds the configured row limit",
			)

		if quantifier == "any":
			for row in rows:
				_consume_collection_row_budget(context, source_path)
				row_context = _child_context(context)
				row_context["row"] = row
				row_context[alias] = row
				if _evaluate_ast_node(where_node, row_context, f"{path}.where"):
					return True
			return False

		if quantifier == "all":
			for row in rows:
				_consume_collection_row_budget(context, source_path)
				row_context = _child_context(context)
				row_context["row"] = row
				row_context[alias] = row
				if not _evaluate_ast_node(where_node, row_context, f"{path}.where"):
					return False
			return True

		# none
		for row in rows:
			_consume_collection_row_budget(context, source_path)
			row_context = _child_context(context)
			row_context["row"] = row
			row_context[alias] = row
			if _evaluate_ast_node(where_node, row_context, f"{path}.where"):
				return False
		return True

	raise ConditionEvaluationError("invalid_execution_plan", "$", f"Unknown canonical condition node type: {node_type}")


def _evaluate_ast_value(val_def: dict[str, Any], context: dict, path: str) -> Any:
	"""Directly evaluate a FlexValue definition without compilation."""
	mode = val_def.get("mode")
	if mode == "static":
		value_type = val_def["value_type"]
		raw_val = val_def["value"]
		parsed = parse_static_value(value_type, raw_val)
		if value_type in {"list", "object"}:
			return copy.deepcopy(parsed)
		return parsed

	if mode == "variable":
		path_def = val_def["path"]
		scope = path_def["scope"]
		segments = tuple(path_def["segments"])
		value = resolve_variable(scope, segments, context, path)
		if value is MISSING:
			return MISSING
		return _coerce_field_value(value, _fieldtype_for_context(scope, segments, context), path)

	if mode == "template":
		segments = val_def.get("segments", [])
		parts = []
		output_length = 0
		for index, segment in enumerate(segments):
			segment_path = f"{path}.segments[{index}]"
			segment_type = segment.get("type")
			if segment_type == "text":
				part = segment.get("value", "")
			else:
				resolved = _evaluate_ast_value(segment["value"], context, f"{segment_path}.value")
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

	if mode == "resolver":
		family = val_def["family"]
		operation = val_def["operation"]
		config = val_def.get("config", {})
		entry = CONDITION_RESOLVER_REGISTRY.get((family, operation))
		if not entry or not entry.get("condition_operand_allowed"):
			raise ConditionEvaluationError(
				"resolver_not_allowed", path, "Resolver operation is no longer approved"
			)
		try:
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

	raise ConditionEvaluationError("invalid_flexvalue_plan", path, f"Unknown canonical FlexValue mode: {mode}")


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


class CanonicalASTCandidate(BaseConditionCandidate):
	"""Benchmark Candidate: Direct Canonical JSON AST Interpreter (steady-state).

	Validates and retains the canonical JSON AST representation once during preparation.
	Evaluates by walking the AST dictionary directly at runtime, lazily resolving operands.
	"""

	candidate_name = "Canonical Condition (Direct JSON AST Runtime)"

	def prepare(self, condition_payload: Any, metadata_context: dict | None = None) -> PreparedCondition:
		start_time = time.perf_counter()
		doctype = metadata_context.get("doctype") if metadata_context else None
		scope_doctypes = metadata_context.get("scope_doctypes") if metadata_context else None
		try:
			prepared = prepare_canonical_ast(condition_payload, doctype=doctype, scope_doctypes=scope_doctypes)
			prep_time = time.perf_counter() - start_time
			return PreparedCondition(
				candidate_name=self.candidate_name,
				prepared_object=prepared,
				preparation_time_seconds=prep_time,
				metadata={"prepared_artifact_type": type(prepared).__name__},
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
		if prepared_condition.error:
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=None,
				execution_time_seconds=0.0,
				error=prepared_condition.error,
			)

		prepared = prepared_condition.prepared_object
		context = _build_canonical_context(document_context, execution_context)

		start_time = time.perf_counter()
		try:
			res = evaluate_prepared_canonical_ast(prepared, context)
			exec_time = time.perf_counter() - start_time
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=bool(res),
				execution_time_seconds=exec_time,
			)
		except ConditionEvaluationError as exc:
			exec_time = time.perf_counter() - start_time
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=None,
				execution_time_seconds=exec_time,
				error=f"{exc.code} at {exc.path}: {exc.message}",
			)
		except ConditionValidationError as exc:
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
				error=str(exc),
			)


class CanonicalASTPublicCandidate(BaseConditionCandidate):
	"""Benchmark Candidate: Direct Canonical JSON AST (one-shot public path).

	Validates and interprets in a single step (evaluate_canonical_ast) without reuse.
	"""

	candidate_name = "Canonical Condition (evaluate_canonical_ast)"

	def prepare(self, condition_payload: Any, metadata_context: dict | None = None) -> PreparedCondition:
		start_time = time.perf_counter()
		prep_time = time.perf_counter() - start_time
		return PreparedCondition(
			candidate_name=self.candidate_name,
			prepared_object=condition_payload,
			preparation_time_seconds=prep_time,
			metadata={"mode": "unprepared_payload"},
		)

	def evaluate(
		self,
		prepared_condition: PreparedCondition,
		document_context: Any,
		execution_context: dict | None = None,
	) -> EvaluationResult:
		payload = prepared_condition.prepared_object
		context = _build_canonical_context(document_context, execution_context)

		start_time = time.perf_counter()
		try:
			res = evaluate_canonical_ast(payload, context)
			exec_time = time.perf_counter() - start_time
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=bool(res),
				execution_time_seconds=exec_time,
			)
		except ConditionEvaluationError as exc:
			exec_time = time.perf_counter() - start_time
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=None,
				execution_time_seconds=exec_time,
				error=f"{exc.code} at {exc.path}: {exc.message}",
			)
		except ConditionValidationError as exc:
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
				error=str(exc),
			)
