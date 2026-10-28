# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import time
from typing import Any

import frappe

from flexirule.ruleflow.core.condition_errors import ConditionError
from flexirule.ruleflow.core.condition_evaluator import (
	_evaluate_node,
	compile_condition,
	evaluate_condition,
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


class CanonicalConditionCandidate(BaseConditionCandidate):
	"""Canonical Condition production runtime evaluator.

	Measures the actual public production runtime path (`evaluate_condition`),
	including LRU cache lookup, payload validation/compilation (or cache hit),
	and node evaluation overhead.
	"""

	candidate_name = "Canonical Condition (evaluate_condition)"

	def prepare(self, condition_payload: Any, metadata_context: dict | None = None) -> PreparedCondition:
		start_time = time.perf_counter()
		try:
			plan = compile_condition(condition_payload)
			prep_time = time.perf_counter() - start_time

			return PreparedCondition(
				candidate_name=self.candidate_name,
				prepared_object=condition_payload,  # Payload passed to evaluate_condition
				preparation_time_seconds=prep_time,
				metadata={"compiled_plan_type": plan[0] if plan else None},
			)
		except Exception as exc:
			prep_time = time.perf_counter() - start_time
			return PreparedCondition(
				candidate_name=self.candidate_name,
				prepared_object=condition_payload,
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

		payload = prepared_condition.prepared_object
		context = _build_canonical_context(document_context, execution_context)

		start_time = time.perf_counter()
		try:
			res = evaluate_condition(payload, context, doctype=None)
			exec_time = time.perf_counter() - start_time
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=bool(res),
				execution_time_seconds=exec_time,
			)
		except ConditionError as exc:
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


class CanonicalPreparedPlanCandidate(BaseConditionCandidate):
	"""Canonical Condition prepared plan execution diagnostic.

	Measures evaluating a pre-compiled, immutable execution plan directly via `_evaluate_node`,
	bypassing public API cache lookup and entrypoint checks. Labeled strictly as a diagnostic.
	"""

	candidate_name = "Canonical Condition (Prepared Plan Diagnostic)"

	def prepare(self, condition_payload: Any, metadata_context: dict | None = None) -> PreparedCondition:
		start_time = time.perf_counter()
		try:
			plan = compile_condition(condition_payload)
			prep_time = time.perf_counter() - start_time

			return PreparedCondition(
				candidate_name=self.candidate_name,
				prepared_object=plan,
				preparation_time_seconds=prep_time,
				metadata={"plan_kind": plan[0] if plan else None},
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

		plan = prepared_condition.prepared_object
		context = _build_canonical_context(document_context, execution_context)

		start_time = time.perf_counter()
		try:
			res = _evaluate_node(plan, context)
			exec_time = time.perf_counter() - start_time
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=bool(res),
				execution_time_seconds=exec_time,
			)
		except ConditionError as exc:
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
