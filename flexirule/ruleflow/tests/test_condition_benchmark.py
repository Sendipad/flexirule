# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import os
import tempfile
from typing import Any

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.tests.condition_benchmark.adapters import (
	NeutralNode,
	node_to_canonical_payload,
	node_to_legacy_payload,
)
from flexirule.ruleflow.tests.condition_benchmark.benchmark_runner import (
	BenchmarkRunner,
	UnifiedScenarioEvaluator,
	_get_git_metadata,
)
from flexirule.ruleflow.tests.condition_benchmark.candidate_approach_a import (
	ApproachACandidate,
	ApproachAExperimentalCodeObjectCandidate,
)
from flexirule.ruleflow.tests.condition_benchmark.candidate_approach_b import (
	ApproachBCandidate,
	ExecutionPlanBuilder,
)
from flexirule.ruleflow.tests.condition_benchmark.candidate_approach_c import ApproachCCandidate
from flexirule.ruleflow.tests.condition_benchmark.candidate_canonical import (
	CanonicalConditionCandidate,
	CanonicalPreparedPlanCandidate,
)
from flexirule.ruleflow.tests.condition_benchmark.comparison_api import (
	BaseConditionCandidate,
	ConditionComparisonHarness,
	EvaluationResult,
	PreparedCondition,
)
from flexirule.ruleflow.tests.condition_benchmark.fixtures import get_neutral_scenarios


class DummyCandidate(BaseConditionCandidate):
	def __init__(
		self,
		name: str,
		result: bool | None = None,
		prep_error: str | None = None,
		eval_error: str | None = None,
	):
		self.candidate_name = name
		self.forced_result = result
		self.prep_error = prep_error
		self.eval_error = eval_error

	def prepare(self, condition_payload, metadata_context=None) -> PreparedCondition:
		if self.prep_error:
			raise ValueError(self.prep_error)
		return PreparedCondition(
			candidate_name=self.candidate_name, prepared_object="dummy", preparation_time_seconds=0.001
		)

	def evaluate(self, prepared_condition, document_context, execution_context=None) -> EvaluationResult:
		if self.eval_error:
			raise RuntimeError(self.eval_error)

		res = self.forced_result
		if res is None:
			res = getattr(document_context, "status", "Open") == "Open"

		return EvaluationResult(
			candidate_name=self.candidate_name,
			result=res,
			execution_time_seconds=0.001,
			error=None,
		)


class TestConditionBenchmark(FrappeTestCase):
	"""Unit tests for FlexiRule condition benchmark comparison API, adapters, five candidates, and runner."""

	def setUp(self):
		super().setUp()
		frappe.flags.in_validate_safe_eval = False
		self.candidate_a = ApproachACandidate()
		self.candidate_a_exp = ApproachAExperimentalCodeObjectCandidate()
		self.candidate_b = ApproachBCandidate()
		self.candidate_c = ApproachCCandidate()
		self.canonical_candidate = CanonicalConditionCandidate()
		self.canonical_prepared = CanonicalPreparedPlanCandidate()

		self.candidates = [
			self.candidate_a,
			self.candidate_a_exp,
			self.candidate_b,
			self.candidate_c,
			self.canonical_candidate,
			self.canonical_prepared,
		]
		self.harness = ConditionComparisonHarness(self.candidates)
		self.builder = ExecutionPlanBuilder()

	def test_adapter_neutral_node_translations(self):
		node = NeutralNode(
			kind="comparison",
			operator="eq",
			left_scope="doc",
			left_segments=["status"],
			right_value_type="string",
			right_value="Open",
		)
		legacy_p = node_to_legacy_payload(node)
		canonical_p = node_to_canonical_payload(node)

		self.assertEqual(legacy_p, {"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Open"}})
		self.assertEqual(
			canonical_p,
			{
				"type": "comparison",
				"operator": "eq",
				"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["status"]}},
				"right": {"mode": "static", "value_type": "string", "value": "Open"},
			},
		)

	def test_five_candidate_preparation_and_evaluation_on_neutral_scenarios(self):
		scenarios = get_neutral_scenarios()
		simple_sc = scenarios[0]

		evaluator = UnifiedScenarioEvaluator(self.candidates)
		check = evaluator.check_semantic_correctness(simple_sc)

		self.assertTrue(check["is_correct"])
		self.assertEqual(check["supported_candidate_count"], 6)
		self.assertEqual(len(check["errors"]), 0)

	def test_unsupported_and_deprecated_cases_isolation(self):
		scenarios = get_neutral_scenarios()
		has_changed_sc = next(sc for sc in scenarios if sc.scenario_id == "edge_case_has_changed")

		evaluator = UnifiedScenarioEvaluator(self.candidates)
		check = evaluator.check_semantic_correctness(has_changed_sc)

		self.assertTrue(check["is_deprecated_case"])
		# Canonical candidates should report UNSUPPORTED reason, not fail
		self.assertIn("UNSUPPORTED", check["candidate_statuses"]["Canonical Condition (evaluate_condition)"])
		self.assertIn(
			"UNSUPPORTED",
			check["candidate_statuses"]["Canonical Condition (Prepared Artifact Runtime)"],
		)

	def test_git_metadata_capture(self):
		git_meta = _get_git_metadata()
		branch, commit = git_meta["branch"], git_meta["commit"]
		self.assertIsInstance(branch, str)
		self.assertIsInstance(commit, str)
		self.assertNotEqual(branch, "")
		self.assertNotEqual(commit, "")

	def test_cold_vs_warm_cache_isolation(self):
		runner = BenchmarkRunner(iterations_per_batch=10, num_batches=1, warmup_iterations=1)
		sc = runner.scenarios[0]
		prep_metrics = runner.measure_preparation_times(sc)

		for _c_name, metric in prep_metrics.items():
			if metric.get("is_supported"):
				self.assertIn("cold_preparation_time_ms", metric)
				self.assertIn("warm_preparation_time_ms", metric)
				self.assertGreaterEqual(metric["cold_preparation_time_ms"], 0.0)
				self.assertGreaterEqual(metric["warm_preparation_time_ms"], 0.0)

	def test_amortized_benchmark_rejects_non_positive_execution_counts(self):
		runner = BenchmarkRunner(iterations_per_batch=1, num_batches=1, warmup_iterations=0)
		invalid_counts: list[list[Any]] = [[0], [-1], [1, 0], [True], [False], [1, True]]
		for counts in invalid_counts:
			with self.subTest(counts=counts):
				with self.assertRaises(ValueError):
					runner.run_amortized_benchmarks(execution_counts=counts)

	def test_full_suite_export_produces_valid_json_and_markdown(self):
		with tempfile.TemporaryDirectory() as tmp_dir:
			json_path = os.path.join(tmp_dir, "canonical_condition_benchmark_results.json")
			md_path = os.path.join(tmp_dir, "condition-backend-comparison-benchmark.md")

			runner = BenchmarkRunner(iterations_per_batch=10, num_batches=1, warmup_iterations=1)
			payload = runner.run_full_suite_and_export(json_path, md_path)

			self.assertEqual(payload["benchmark_protocol_version"], 3)
			self.assertEqual(payload["production_selection_status"], "Not established")
			self.assertIn("correctness_suite", payload)
			self.assertIn("steady_state_benchmark", payload)
			self.assertIn("amortized_benchmark", payload)

			self.assertTrue(os.path.exists(json_path))
			self.assertTrue(os.path.exists(md_path))

			with open(md_path, encoding="utf-8") as f:
				md_content = f.read()

			self.assertIn(
				# FlexiRule — Condition Backend Comparison Benchmark Report, md_content
			)
			self.assertIn("Not established", md_content)

	# --- Explicit Short-Circuit Behavior Tests for All Benchmark Approaches ---

	def test_short_circuit_and_operator(self):
		and_payload = {
			"op": "and",
			"conditions": [
				{"left": {"ref": "doc.first_cond"}, "op": "==", "right": {"value": True}},
				{"left": {"ref": "doc.second_cond"}, "op": "==", "right": {"value": True}},
			],
		}

		for cand in [self.candidate_a, self.candidate_a_exp, self.candidate_b, self.candidate_c]:
			with self.subTest(candidate=cand.candidate_name):
				tracking_doc = TrackingDoc({"first_cond": False, "second_cond": True})
				prep = cand.prepare(and_payload)
				res = cand.evaluate(prep, tracking_doc)

				self.assertIsNone(res.error)
				self.assertFalse(res.result)
				self.assertEqual(tracking_doc.access_counts.get("first_cond", 0), 1)
				self.assertEqual(
					tracking_doc.access_counts.get("second_cond", 0),
					0,
					f"Candidate '{cand.candidate_name}' evaluated second_cond despite AND short-circuit",
				)

	def test_short_circuit_or_operator(self):
		or_payload = {
			"op": "or",
			"conditions": [
				{"left": {"ref": "doc.first_cond"}, "op": "==", "right": {"value": True}},
				{"left": {"ref": "doc.second_cond"}, "op": "==", "right": {"value": True}},
			],
		}

		for cand in [self.candidate_a, self.candidate_a_exp, self.candidate_b, self.candidate_c]:
			with self.subTest(candidate=cand.candidate_name):
				tracking_doc = TrackingDoc({"first_cond": True, "second_cond": False})
				prep = cand.prepare(or_payload)
				res = cand.evaluate(prep, tracking_doc)

				self.assertIsNone(res.error)
				self.assertTrue(res.result)
				self.assertEqual(tracking_doc.access_counts.get("first_cond", 0), 1)
				self.assertEqual(
					tracking_doc.access_counts.get("second_cond", 0),
					0,
					f"Candidate '{cand.candidate_name}' evaluated second_cond despite OR short-circuit",
				)

	def test_canonical_candidate_typed_validation_error_handling(self):
		invalid_payload = {
			"type": "comparison",
			"operator": "invalid_op",
			"left": {"mode": "static", "value_type": "string", "value": "x"},
			"right": {"mode": "static", "value_type": "string", "value": "x"},
		}
		prep = self.canonical_candidate.prepare(invalid_payload)
		res = self.canonical_candidate.evaluate(prep, {})
		self.assertIsNotNone(res.error)
		self.assertIn("unknown_operator", res.error)

	def test_canonical_candidate_typed_evaluation_error_handling(self):
		payload = {
			"type": "comparison",
			"operator": "gt",
			"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["amount"]}},
			"right": {"mode": "static", "value_type": "decimal", "value": "100"},
		}
		doc = {"amount": "not_a_number"}
		prep = self.canonical_candidate.prepare(payload)
		res = self.canonical_candidate.evaluate(prep, doc)
		self.assertIsNotNone(res.error)
		self.assertIn("operand_type_mismatch", res.error)


class TrackingDoc(frappe._dict):
	"""Helper dictionary context that tracks field access counts for short-circuit assertions."""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.access_counts: dict[str, int] = {}

	def get(self, key, default=None):
		if key not in ("doctype", "_doc_before_save"):
			self.access_counts[key] = self.access_counts.get(key, 0) + 1
		return super().get(key, default)
