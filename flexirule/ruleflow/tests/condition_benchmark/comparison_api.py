# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PreparedCondition:
	"""Encapsulates a condition prepared by a candidate evaluator."""

	candidate_name: str
	prepared_object: Any
	preparation_time_seconds: float
	metadata: dict = field(default_factory=dict)
	error: str | None = None


@dataclass
class EvaluationResult:
	"""Result of executing a prepared condition against document context."""

	candidate_name: str
	result: bool | None
	execution_time_seconds: float
	error: str | None = None


class BaseConditionCandidate(ABC):
	"""Base interface for condition evaluator candidates."""

	candidate_name: str

	@abstractmethod
	def prepare(self, condition_payload: Any, metadata_context: dict | None = None) -> PreparedCondition:
		"""Prepare a condition payload for execution.

		Measures preparation time separately from execution time.
		"""
		pass

	@abstractmethod
	def evaluate(
		self,
		prepared_condition: PreparedCondition,
		document_context: Any,
		execution_context: dict | None = None,
	) -> EvaluationResult:
		"""Evaluate an already-prepared condition against document/execution context."""
		pass


class ConditionComparisonHarness:
	"""Internal test harness for comparing condition candidates."""

	def __init__(self, candidates: list[BaseConditionCandidate]):
		self.candidates = {c.candidate_name: c for c in candidates}

	def prepare_all(
		self, condition_payload: Any, metadata_context: dict | None = None
	) -> dict[str, PreparedCondition]:
		"""Prepare the condition using all registered candidates."""
		prepared = {}
		for name, candidate in self.candidates.items():
			start_time = time.perf_counter()
			try:
				prepared[name] = candidate.prepare(condition_payload, metadata_context)
			except Exception as exc:
				elapsed = time.perf_counter() - start_time
				prepared[name] = PreparedCondition(
					candidate_name=name,
					prepared_object=None,
					preparation_time_seconds=elapsed,
					error=f"Preparation failed: {exc!s}",
				)
		return prepared

	def evaluate_all(
		self,
		prepared_conditions: dict[str, PreparedCondition],
		document_context: Any,
		execution_context: dict | None = None,
	) -> dict[str, EvaluationResult]:
		"""Evaluate all prepared conditions against document context."""
		results = {}
		for name, candidate in self.candidates.items():
			prep = prepared_conditions.get(name)
			if prep is None:
				results[name] = EvaluationResult(
					candidate_name=name,
					result=None,
					execution_time_seconds=0.0,
					error="Missing prepared condition",
				)
				continue
			if prep.error:
				results[name] = EvaluationResult(
					candidate_name=name,
					result=None,
					execution_time_seconds=0.0,
					error=prep.error,
				)
				continue

			start_time = time.perf_counter()
			try:
				results[name] = candidate.evaluate(prep, document_context, execution_context)
			except Exception as exc:
				elapsed = time.perf_counter() - start_time
				results[name] = EvaluationResult(
					candidate_name=name,
					result=None,
					execution_time_seconds=elapsed,
					error=f"Evaluation failed: {exc!s}",
				)
		return results

	def check_semantic_agreement(
		self,
		condition_payload: Any,
		document_context: Any,
		expected_result: bool | None = None,
		metadata_context: dict | None = None,
		execution_context: dict | None = None,
	) -> dict:
		"""Compare results across candidates and verify correctness against expected results.

		A evaluation check is correct ONLY when:
		- Every registered candidate prepared and evaluated successfully (no errors, no missing results).
		- Non-empty candidate results set.
		- All candidates returned the exact same result.
		- The agreed result equals expected_result (if expected_result is provided).
		"""
		prepared = self.prepare_all(condition_payload, metadata_context)
		eval_results = self.evaluate_all(prepared, document_context, execution_context)

		errors = {}
		for name, prep in prepared.items():
			if prep.error:
				errors[name] = prep.error

		for name, res in eval_results.items():
			if res.error is not None:
				errors[name] = res.error
			elif res.result is None:
				errors[name] = "Evaluation produced None result"

		candidate_outputs = {
			name: res.result
			for name, res in eval_results.items()
			if res.error is None and res.result is not None
		}

		all_registered_succeeded = (
			len(self.candidates) > 0 and len(candidate_outputs) == len(self.candidates) and len(errors) == 0
		)

		unique_results = set(candidate_outputs.values())
		agrees = all_registered_succeeded and len(unique_results) == 1

		disagreements = []
		matches_expected = True

		if not all_registered_succeeded:
			if len(candidate_outputs) == 0:
				disagreements.append("No candidate produced a valid evaluation result")
			elif len(errors) > 0:
				disagreements.append(f"Evaluation or preparation errors encountered: {errors}")

		if len(unique_results) > 1:
			disagreements.append(f"Semantic disagreement detected across candidates: {candidate_outputs}")

		if expected_result is not None:
			if not agrees:
				matches_expected = False
				disagreements.append("Candidates do not agree or failed, so results do not match expected")
			else:
				actual_res = next(iter(unique_results))
				if actual_res != expected_result:
					matches_expected = False
					disagreements.append(
						f"Candidate agreed result ({actual_res}) does not match expected result ({expected_result})"
					)

		is_correct = agrees and matches_expected and len(errors) == 0

		return {
			"is_correct": is_correct,
			"agrees": agrees,
			"matches_expected": matches_expected,
			"all_registered_succeeded": all_registered_succeeded,
			"candidate_results": candidate_outputs,
			"disagreements": disagreements,
			"errors": errors,
			"prepared": prepared,
			"evaluations": eval_results,
		}
