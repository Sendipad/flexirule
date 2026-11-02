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

	def test_run_main_prepares_frappe_log_directories_and_destroys_site(self):
		from unittest.mock import Mock, patch

		from flexirule.ruleflow.tests.condition_benchmark import benchmark_runner

		with tempfile.TemporaryDirectory() as temp_dir:
			bench_root = os.path.join(temp_dir, "bench")
			working_directory = os.path.join(temp_dir, "checkout")
			os.makedirs(working_directory)
			bench_log_dir = os.path.join(temp_dir, "logs")
			site_log_dir = os.path.join(working_directory, "benchmark.test", "logs")
			runner = Mock()
			runner.run_full_suite_and_export.side_effect = RuntimeError("benchmark failed")

			def assert_log_directories_exist():
				self.assertTrue(os.path.isdir(bench_log_dir))
				self.assertTrue(os.path.isdir(site_log_dir))

			with (
				patch.dict(
					os.environ,
					{
						"FRAPPE_BENCH_PATH": bench_root,
						"FRAPPE_SITE_NAME": "benchmark.test",
						"CONDITION_BENCHMARK_JSON_PATH": "/tmp/benchmark.json",
						"CONDITION_BENCHMARK_MARKDOWN_PATH": "/tmp/benchmark.md",
					},
				),
				patch.object(benchmark_runner.os, "getcwd", return_value=working_directory),
				patch.object(benchmark_runner.frappe, "local", Mock(site="benchmark.test")),
				patch.object(benchmark_runner.frappe, "init") as init,
				patch.object(
					benchmark_runner.frappe, "connect", side_effect=assert_log_directories_exist
				) as connect,
				patch.object(benchmark_runner.frappe, "destroy") as destroy,
				patch.object(benchmark_runner, "BenchmarkRunner", return_value=runner),
			):
				with self.assertRaisesRegex(RuntimeError, "benchmark failed"):
					benchmark_runner.run_main()

			init.assert_called_once_with(
				site="benchmark.test", sites_path=os.path.join(bench_root, "sites")
			)
			connect.assert_called_once_with()
			destroy.assert_called_once_with()
			runner.run_full_suite_and_export.assert_called_once_with(
				"/tmp/benchmark.json", "/tmp/benchmark.md"
			)

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

	def test_canonical_comparison_invalidates_failed_cache_isolation(self):
		from unittest.mock import patch

		from flexirule.ruleflow.tests.condition_benchmark import benchmark_runner

		runner = BenchmarkRunner(iterations_per_batch=1, num_batches=1, warmup_iterations=0)
		workload = {
			"payload": {
				"type": "comparison",
				"operator": "eq",
				"left": {
					"mode": "variable",
					"path": {"scope": "doc", "segments": ["status"]},
				},
				"right": {"mode": "static", "value_type": "string", "value": "Open"},
			},
			"doc": {"status": "Open"},
			"expected": True,
			"description": "Cache-isolation regression workload",
		}
		with (
			patch.object(
				benchmark_runner, "get_canonical_scaling_workloads", return_value={"cache_test": workload}
			),
			patch.object(benchmark_runner, "_clear_cache_safely", return_value=False),
		):
			result = runner.run_canonical_ast_vs_plan_comparison()

		measurement = result["workloads"]["cache_test"]
		self.assertFalse(measurement["is_valid_measurement"])
		self.assertFalse(measurement["cache_isolation_verified"])
		self.assertIn("cache isolation", measurement["reason"])

	def test_canonical_comparison_rotates_candidate_order_and_records_distributions(self):
		from unittest.mock import patch

		from flexirule.ruleflow.tests.condition_benchmark import benchmark_runner

		runner = BenchmarkRunner(iterations_per_batch=1, num_batches=2, warmup_iterations=1)
		workload = {
			"payload": {
				"type": "comparison",
				"operator": "eq",
				"left": {
					"mode": "variable",
					"path": {"scope": "doc", "segments": ["status"]},
				},
				"right": {"mode": "static", "value_type": "string", "value": "Open"},
			},
			"doc": {"status": "Open"},
			"expected": True,
			"description": "Paired-order regression workload",
		}
		with (
			patch.object(
				benchmark_runner, "get_canonical_scaling_workloads", return_value={"paired_test": workload}
			),
			patch.object(benchmark_runner, "_clear_cache_safely", return_value=True),
		):
			result = runner.run_canonical_ast_vs_plan_comparison()

		measurement = result["workloads"]["paired_test"]
		self.assertTrue(measurement["is_valid_measurement"], measurement.get("reason"))
		self.assertEqual(
			measurement["paired_samples"][0]["candidate_order"],
			["compiled_plan", "direct_ast"],
		)
		self.assertEqual(
			measurement["paired_samples"][1]["candidate_order"],
			["direct_ast", "compiled_plan"],
		)
		self.assertIn("p95", measurement["evaluation_distributions"]["compiled_plan_us"])
		self.assertEqual(len(measurement["evaluation_distributions"]["direct_ast_us"]["samples"]), 2)

	def test_canonical_comparison_rejects_incorrect_timed_evaluation(self):
		from unittest.mock import patch

		from flexirule.ruleflow.tests.condition_benchmark import benchmark_runner

		runner = BenchmarkRunner(iterations_per_batch=2, num_batches=1, warmup_iterations=1)
		workload = {
			"payload": {
				"type": "comparison",
				"operator": "eq",
				"left": {
					"mode": "variable",
					"path": {"scope": "doc", "segments": ["status"]},
				},
				"right": {"mode": "static", "value_type": "string", "value": "Open"},
			},
			"doc": {"status": "Open"},
			"expected": True,
			"description": "Timed-result validation regression workload",
		}
		original_evaluate = runner.cand_canon_ast.evaluate
		evaluation_calls = {"count": 0}

		def incorrect_after_warmup(prepared, document, execution_context=None):
			evaluation_calls["count"] += 1
			result = original_evaluate(prepared, document, execution_context)
			if evaluation_calls["count"] > 1:
				return result.__class__(
					candidate_name=result.candidate_name,
					result=False,
					execution_time_seconds=result.execution_time_seconds,
					error=None,
				)
			return result

		with (
			patch.object(runner.cand_canon_ast, "evaluate", side_effect=incorrect_after_warmup),
			patch.object(
				benchmark_runner, "get_canonical_scaling_workloads", return_value={"timed_test": workload}
			),
			patch.object(benchmark_runner, "_clear_cache_safely", return_value=True),
		):
			result = runner.run_canonical_ast_vs_plan_comparison()

		measurement = result["workloads"]["timed_test"]
		self.assertFalse(measurement["is_valid_measurement"])
		self.assertIn("Incorrect result", measurement["reason"])

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

			self.assertEqual(payload["benchmark_protocol_version"], 5)
			self.assertEqual(payload["production_selection_status"], "Not established")
			self.assertIn("correctness_suite", payload)
			self.assertIn("steady_state_benchmark", payload)
			self.assertIn("amortized_benchmark", payload)

			self.assertTrue(os.path.exists(json_path))
			self.assertTrue(os.path.exists(md_path))

			with open(md_path, encoding="utf-8") as f:
				md_content = f.read()

			self.assertIn("FlexiRule — Condition Backend Comparison Benchmark Report", md_content)
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

	# --- Tests for Direct Canonical AST Candidate & Parity with Compiled Plan ---

	def test_canonical_ast_candidate_parity_with_compiled_plan(self):
		"""Verify identical evaluation results across supported neutral scenarios."""
		from flexirule.ruleflow.tests.condition_benchmark.candidate_canonical_ast import CanonicalASTCandidate

		ast_candidate = CanonicalASTCandidate()
		scenarios = get_neutral_scenarios()

		for sc in scenarios:
			canonical_p = node_to_canonical_payload(sc.root)
			if canonical_p is None:
				continue

			with self.subTest(scenario=sc.scenario_id):
				prep_compiled = self.canonical_prepared.prepare(canonical_p)
				prep_ast = ast_candidate.prepare(canonical_p)

				self.assertEqual(bool(prep_compiled.error), bool(prep_ast.error))
				if prep_compiled.error:
					continue

				res_compiled_m = self.canonical_prepared.evaluate(prep_compiled, sc.matching_doc)
				res_ast_m = ast_candidate.evaluate(prep_ast, sc.matching_doc)
				self.assertEqual(res_compiled_m.result, res_ast_m.result)
				self.assertEqual(bool(res_compiled_m.error), bool(res_ast_m.error))

				res_compiled_nm = self.canonical_prepared.evaluate(prep_compiled, sc.non_matching_doc)
				res_ast_nm = ast_candidate.evaluate(prep_ast, sc.non_matching_doc)
				self.assertEqual(res_compiled_nm.result, res_ast_nm.result)
				self.assertEqual(bool(res_compiled_nm.error), bool(res_ast_nm.error))

	def test_lazy_operand_evaluation_and_or_short_circuit(self):
		"""Verify lazy evaluation: later operands/children are not evaluated once decisive."""
		from flexirule.ruleflow.tests.condition_benchmark.candidate_canonical_ast import CanonicalASTCandidate

		ast_cand = CanonicalASTCandidate()

		and_payload = {
			"type": "group",
			"operator": "and",
			"children": [
				{
					"type": "comparison",
					"operator": "eq",
					"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["first_cond"]}},
					"right": {"mode": "static", "value_type": "boolean", "value": True},
				},
				{
					"type": "comparison",
					"operator": "eq",
					"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["second_cond"]}},
					"right": {"mode": "static", "value_type": "boolean", "value": True},
				},
			],
		}

		for cand in [self.canonical_prepared, ast_cand]:
			with self.subTest(candidate=cand.candidate_name, test="and_short_circuit"):
				tracking_doc = TrackingDoc({"first_cond": False, "second_cond": True})
				prep = cand.prepare(and_payload)
				res = cand.evaluate(prep, tracking_doc)
				self.assertIsNone(res.error)
				self.assertFalse(res.result)
				self.assertEqual(tracking_doc.access_counts.get("first_cond", 0), 1)
				self.assertEqual(tracking_doc.access_counts.get("second_cond", 0), 0)

		or_payload = {
			"type": "group",
			"operator": "or",
			"children": [
				{
					"type": "comparison",
					"operator": "eq",
					"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["first_cond"]}},
					"right": {"mode": "static", "value_type": "boolean", "value": True},
				},
				{
					"type": "comparison",
					"operator": "eq",
					"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["second_cond"]}},
					"right": {"mode": "static", "value_type": "boolean", "value": True},
				},
			],
		}

		for cand in [self.canonical_prepared, ast_cand]:
			with self.subTest(candidate=cand.candidate_name, test="or_short_circuit"):
				tracking_doc = TrackingDoc({"first_cond": True, "second_cond": False})
				prep = cand.prepare(or_payload)
				res = cand.evaluate(prep, tracking_doc)
				self.assertIsNone(res.error)
				self.assertTrue(res.result)
				self.assertEqual(tracking_doc.access_counts.get("first_cond", 0), 1)
				self.assertEqual(tracking_doc.access_counts.get("second_cond", 0), 0)

	def test_lazy_resolver_invocation_in_unreachable_branch(self):
		"""Verify resolvers in unreachable short-circuited branches are never invoked."""
		import flexirule.ruleflow.core.flexvalue_contract as fvc
		from flexirule.ruleflow.tests.condition_benchmark.candidate_canonical_ast import CanonicalASTCandidate

		resolver_invocations = 0

		def counting_resolver(config, context):
			nonlocal resolver_invocations
			resolver_invocations += 1
			return config.get("value", 0)

		def noop_validator(config, path, allowed_scopes, resolver_depth, flexvalue_depth):
			pass

		fvc.register_condition_resolver(
			family="bench_lazy",
			operation="get_number",
			label="Bench Lazy Resolver",
			output_type="integer",
			config_schema={"type": "object", "properties": {"value": {"type": "integer"}}},
			permission_policy="no_data_access",
			validate_config=noop_validator,
			resolve=counting_resolver,
			condition_operand_allowed=True,
			required_capability="condition_operand",
		)

		payload = {
			"type": "group",
			"operator": "and",
			"children": [
				{
					"type": "comparison",
					"operator": "eq",
					"left": {"mode": "variable", "path": {"scope": "doc", "segments": ["active"]}},
					"right": {"mode": "static", "value_type": "boolean", "value": True},
				},
				{
					"type": "comparison",
					"operator": "gt",
					"left": {
						"mode": "resolver",
						"family": "bench_lazy",
						"operation": "get_number",
						"config": {"value": 50},
					},
					"right": {"mode": "static", "value_type": "integer", "value": 10},
				},
			],
		}

		ast_cand = CanonicalASTCandidate()
		try:
			for cand in [self.canonical_prepared, ast_cand]:
				with self.subTest(candidate=cand.candidate_name):
					prep = cand.prepare(payload)
					resolver_invocations = 0
					res1 = cand.evaluate(prep, {"doc": {"active": False}})
					self.assertFalse(res1.result)
					self.assertEqual(
						resolver_invocations,
						0,
						f"Resolver was invoked in {cand.candidate_name} on short-circuit!",
					)

					resolver_invocations = 0
					res2 = cand.evaluate(prep, {"doc": {"active": True}})
					self.assertTrue(res2.result)
					self.assertEqual(
						resolver_invocations,
						1,
						f"Resolver was not invoked exactly once in {cand.candidate_name}!",
					)
		finally:
			fvc.CONDITION_RESOLVER_REGISTRY.pop(("bench_lazy", "get_number"), None)
			fvc._RESOLVER_REGISTRY_FINGERPRINT_CACHE = None

	def test_lazy_collection_quantifier_short_circuit(self):
		"""Verify collection predicates stop iterating as soon as the quantifier is decisive."""
		from flexirule.ruleflow.tests.condition_benchmark.candidate_canonical_ast import CanonicalASTCandidate

		ast_cand = CanonicalASTCandidate()

		any_payload = {
			"type": "collection_predicate",
			"quantifier": "any",
			"source": {"scope": "doc", "segments": ["items"]},
			"as": "it",
			"where": {
				"type": "comparison",
				"operator": "eq",
				"left": {"mode": "variable", "path": {"scope": "it", "segments": ["active"]}},
				"right": {"mode": "static", "value_type": "boolean", "value": True},
			},
		}

		rows = [
			TrackingDoc({"active": False}),
			TrackingDoc({"active": True}),
			TrackingDoc({"active": False}),
			TrackingDoc({"active": False}),
			TrackingDoc({"active": False}),
		]

		for cand in [self.canonical_prepared, ast_cand]:
			with self.subTest(candidate=cand.candidate_name):
				for r in rows:
					r.access_counts.clear()
				prep = cand.prepare(any_payload)
				res = cand.evaluate(prep, {"doc": {"items": rows}})
				self.assertTrue(res.result)
				self.assertEqual(rows[0].access_counts.get("active", 0), 1)
				self.assertEqual(rows[1].access_counts.get("active", 0), 1)
				self.assertEqual(rows[2].access_counts.get("active", 0), 0)
				self.assertEqual(rows[3].access_counts.get("active", 0), 0)
				self.assertEqual(rows[4].access_counts.get("active", 0), 0)

	def test_frappe_metadata_user_roles_scenario(self):
		"""Verify authoritative User -> Has Role metadata resolution in both candidates."""
		from flexirule.ruleflow.tests.condition_benchmark.candidate_canonical_ast import CanonicalASTCandidate

		ast_cand = CanonicalASTCandidate()

		payload = {
			"type": "collection_predicate",
			"quantifier": "any",
			"source": {"scope": "doc", "segments": ["roles"]},
			"as": "role_item",
			"where": {
				"type": "comparison",
				"operator": "eq",
				"left": {"mode": "variable", "path": {"scope": "role_item", "segments": ["role"]}},
				"right": {"mode": "static", "value_type": "string", "value": "System Manager"},
			},
		}

		meta_ctx = {"doctype": "User"}
		prep_compiled = self.canonical_prepared.prepare(payload, metadata_context=meta_ctx)
		prep_ast = ast_cand.prepare(payload, metadata_context=meta_ctx)

		self.assertIsNone(prep_compiled.error)
		self.assertIsNone(prep_ast.error)

		doc_matching = {
			"doctype": "User",
			"roles": [
				{"doctype": "Has Role", "role": "Blogger"},
				{"doctype": "Has Role", "role": "System Manager"},
			],
		}
		doc_non_matching = {
			"doctype": "User",
			"roles": [
				{"doctype": "Has Role", "role": "Blogger"},
				{"doctype": "Has Role", "role": "Guest"},
			],
		}

		res_c_m = self.canonical_prepared.evaluate(prep_compiled, doc_matching)
		res_ast_m = ast_cand.evaluate(prep_ast, doc_matching)
		self.assertTrue(res_c_m.result)
		self.assertTrue(res_ast_m.result)

		res_c_nm = self.canonical_prepared.evaluate(prep_compiled, doc_non_matching)
		res_ast_nm = ast_cand.evaluate(prep_ast, doc_non_matching)
		self.assertFalse(res_c_nm.result)
		self.assertFalse(res_ast_nm.result)


class TrackingDoc(frappe._dict):
	"""Helper dictionary context that tracks field access counts for short-circuit assertions."""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.access_counts: dict[str, int] = {}

	def get(self, key, default=None):
		if key not in ("doctype", "_doc_before_save"):
			self.access_counts[key] = self.access_counts.get(key, 0) + 1
		return super().get(key, default)
