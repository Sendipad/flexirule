# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.tests.condition_benchmark.benchmark_runner import BenchmarkRunner
from flexirule.ruleflow.tests.condition_benchmark.candidate_approach_a import (
	ApproachACandidate,
	ApproachAExperimentalCodeObjectCandidate,
)
from flexirule.ruleflow.tests.condition_benchmark.candidate_approach_b import (
	ApproachBCandidate,
	ExecutionPlanBuilder,
)
from flexirule.ruleflow.tests.condition_benchmark.candidate_approach_c import ApproachCCandidate
from flexirule.ruleflow.tests.condition_benchmark.comparison_api import (
	BaseConditionCandidate,
	ConditionComparisonHarness,
	EvaluationResult,
	PreparedCondition,
)
from flexirule.ruleflow.tests.condition_benchmark.fixtures import get_all_fixtures


class DummyCandidate(BaseConditionCandidate):
	def __init__(
		self,
		name: str,
		result: bool | None = None,
		prep_error: str | None = None,
		eval_error: str | None = None,
		fail_after_eval_count: int | None = None,
	):
		self.candidate_name = name
		self.forced_result = result
		self.prep_error = prep_error
		self.eval_error = eval_error
		self.fail_after_eval_count = fail_after_eval_count
		self.eval_count = 0

	def prepare(self, condition_payload, metadata_context=None) -> PreparedCondition:
		if self.prep_error:
			raise ValueError(self.prep_error)
		return PreparedCondition(
			candidate_name=self.candidate_name, prepared_object="dummy", preparation_time_seconds=0.001
		)

	def evaluate(self, prepared_condition, document_context, execution_context=None) -> EvaluationResult:
		self.eval_count += 1
		if self.fail_after_eval_count is not None and self.eval_count > self.fail_after_eval_count:
			raise RuntimeError("Injected evaluation failure after threshold")
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
	"""Unit tests for FlexiRule condition benchmark comparison API and candidates."""

	def setUp(self):
		super().setUp()
		self.candidate_a = ApproachACandidate()
		self.candidate_a_exp = ApproachAExperimentalCodeObjectCandidate()
		self.candidate_b = ApproachBCandidate()
		self.candidate_c = ApproachCCandidate()
		self.candidates = [self.candidate_a, self.candidate_a_exp, self.candidate_b, self.candidate_c]
		self.harness = ConditionComparisonHarness(self.candidates)
		self.builder = ExecutionPlanBuilder()

	def test_candidates_prepare_and_evaluate_simple_fixture(self):
		fixtures = get_all_fixtures()
		simple_fixture = fixtures[0]

		prepared = self.harness.prepare_all(simple_fixture.condition_payload)
		self.assertEqual(len(prepared), 4)

		# Evaluate matching doc
		match_results = self.harness.evaluate_all(prepared, simple_fixture.matching_doc)
		for name, res in match_results.items():
			self.assertIsNone(res.error, f"Candidate {name} failed with error: {res.error}")
			self.assertTrue(res.result, f"Candidate {name} expected True for matching doc")

		# Evaluate non-matching doc
		non_match_results = self.harness.evaluate_all(prepared, simple_fixture.non_matching_doc)
		for name, res in non_match_results.items():
			self.assertIsNone(res.error, f"Candidate {name} failed with error: {res.error}")
			self.assertFalse(res.result, f"Candidate {name} expected False for non-matching doc")

	def test_semantic_correctness_suite_agreement(self):
		runner = BenchmarkRunner(iterations_per_batch=10, num_batches=1, warmup_iterations=1)
		suite_results = runner.run_semantic_correctness_suite()

		# Identify passed and failed fixture checks
		failed_fixtures = [r for r in suite_results["results"] if not r["is_correct"]]
		failed_ids = [f["fixture_id"] for f in failed_fixtures]

		# edge_case_has_changed fails parity between ConditionCompiler (deprecated operator returning True) and candidates
		self.assertEqual(
			failed_ids, ["edge_case_has_changed"], f"Unexpected correctness failures: {failed_ids}"
		)

	def test_correctness_gate_normal_success(self):
		c1 = DummyCandidate("C1", result=True)
		c2 = DummyCandidate("C2", result=True)
		harness = ConditionComparisonHarness([c1, c2])
		check = harness.check_semantic_agreement({}, {}, expected_result=True)
		self.assertTrue(check["is_correct"])
		self.assertTrue(check["agrees"])
		self.assertTrue(check["matches_expected"])

	def test_correctness_gate_preparation_failure(self):
		c1 = DummyCandidate("C1", result=True)
		c2 = DummyCandidate("C2", prep_error="Prep failed")
		harness = ConditionComparisonHarness([c1, c2])
		check = harness.check_semantic_agreement({}, {}, expected_result=True)
		self.assertFalse(check["is_correct"])
		self.assertIn("C2", check["errors"])

	def test_correctness_gate_evaluation_failure(self):
		c1 = DummyCandidate("C1", result=True)
		c2 = DummyCandidate("C2", eval_error="Eval crashed")
		harness = ConditionComparisonHarness([c1, c2])
		check = harness.check_semantic_agreement({}, {}, expected_result=True)
		self.assertFalse(check["is_correct"])
		self.assertIn("C2", check["errors"])

	def test_correctness_gate_semantic_disagreement(self):
		c1 = DummyCandidate("C1", result=True)
		c2 = DummyCandidate("C2", result=False)
		harness = ConditionComparisonHarness([c1, c2])
		check = harness.check_semantic_agreement({}, {}, expected_result=True)
		self.assertFalse(check["is_correct"])
		self.assertFalse(check["agrees"])

	def test_correctness_gate_agreed_incorrect_result(self):
		c1 = DummyCandidate("C1", result=False)
		c2 = DummyCandidate("C2", result=False)
		harness = ConditionComparisonHarness([c1, c2])
		check = harness.check_semantic_agreement({}, {}, expected_result=True)
		self.assertFalse(check["is_correct"])
		self.assertTrue(check["agrees"])
		self.assertFalse(check["matches_expected"])

	def test_correctness_gate_all_candidates_failing(self):
		c1 = DummyCandidate("C1", eval_error="Err1")
		c2 = DummyCandidate("C2", eval_error="Err2")
		harness = ConditionComparisonHarness([c1, c2])
		check = harness.check_semantic_agreement({}, {}, expected_result=True)
		self.assertFalse(check["is_correct"])
		self.assertEqual(len(check["candidate_results"]), 0)

	def test_measurement_warmup_failure_invalidates_candidate(self):
		# Correctness check uses 2 evals. Set fail_after_eval_count=2 so correctness passes but warmup (eval 3) fails.
		c1 = DummyCandidate("C1", fail_after_eval_count=2)
		c2 = DummyCandidate("C2")
		runner = BenchmarkRunner(iterations_per_batch=10, num_batches=2, warmup_iterations=5)
		runner.candidates = [c1, c2]
		runner.candidate_a = c1
		runner.candidate_b = c2
		runner.harness = ConditionComparisonHarness([c1, c2])

		results = runner.run_primary_benchmarks()
		fix_metric = results["fixtures"][0]["candidate_metrics"]["C1"]
		self.assertFalse(fix_metric["is_valid_measurement"])
		self.assertIn("Warm-up", fix_metric["error"])
		self.assertIsNone(results["fixtures"][0]["speedup_ratio_b_vs_primary_a"])

	def test_measurement_batch_failure_invalidates_batch(self):
		c1 = DummyCandidate(
			"C1", result=True, fail_after_eval_count=15
		)  # succeeds warmup (5), fails in batch 1
		c2 = DummyCandidate("C2", result=True)
		runner = BenchmarkRunner(iterations_per_batch=10, num_batches=2, warmup_iterations=5)
		runner.candidates = [c1, c2]
		runner.candidate_a = c1
		runner.candidate_b = c2
		runner.harness = ConditionComparisonHarness([c1, c2])

		results = runner.run_primary_benchmarks()
		fix_metric = results["fixtures"][0]["candidate_metrics"]["C1"]
		self.assertFalse(fix_metric["is_valid_measurement"])
		self.assertIn("failed", fix_metric["error"])

	def test_plan_validation_unsupported_logical_operator(self):
		payload = {"op": "invalid_logic", "conditions": []}
		with self.assertRaises(ValueError) as cm:
			self.builder.build_plan(payload)
		self.assertIn("Unsupported logical operator", str(cm.exception))

	def test_plan_validation_unsupported_comparison_operator(self):
		payload = {
			"op": "and",
			"conditions": [
				{"left": {"ref": "doc.status"}, "op": "invalid_comparison_op", "right": {"value": "X"}}
			],
		}
		with self.assertRaises(ValueError) as cm:
			self.builder.build_plan(payload)
		self.assertIn("Unsupported condition comparison operator", str(cm.exception))

	def test_plan_validation_invalid_operand_scope(self):
		payload = {
			"op": "and",
			"conditions": [
				{"left": {"ref": "forbidden_scope.status"}, "op": "==", "right": {"value": "Open"}}
			],
		}
		with self.assertRaises(ValueError) as cm:
			self.builder.build_plan(payload)
		self.assertIn("Invalid operand scope", str(cm.exception))

	def test_plan_validation_malformed_collection_node(self):
		payload = {"collection": "", "op": "any", "where": {"op": "and", "conditions": []}}
		with self.assertRaises(ValueError) as cm:
			self.builder.build_plan(payload)
		self.assertIn("Collection condition requires a non-empty 'collection'", str(cm.exception))

		payload_no_where = {"collection": "doc.items", "op": "any"}
		with self.assertRaises(ValueError) as cm:
			self.builder.build_plan(payload_no_where)
		self.assertIn("Collection condition requires a valid dict 'where'", str(cm.exception))

	def test_plan_validation_invalid_child_node_in_conditions_list(self):
		payload = {"op": "and", "conditions": ["not_a_dict_node"]}
		with self.assertRaises(ValueError) as cm:
			self.builder.build_plan(payload)
		self.assertIn("Invalid child condition node at index 0", str(cm.exception))

	def test_plan_empty_group_semantics(self):
		and_plan = self.builder.build_plan({"op": "and", "conditions": []})
		self.assertIsNotNone(and_plan.root_node)
		assert and_plan.root_node is not None
		self.assertTrue(and_plan.root_node.evaluate(frappe._dict()))

		or_plan = self.builder.build_plan({"op": "or", "conditions": []})
		self.assertIsNotNone(or_plan.root_node)
		assert or_plan.root_node is not None
		self.assertFalse(or_plan.root_node.evaluate(frappe._dict()))

	def test_experimental_code_object_candidate_compiles_code_object(self):
		import types

		payload = {
			"op": "and",
			"conditions": [{"left": {"ref": "doc.status"}, "op": "==", "right": {"value": "Open"}}],
		}
		prep = self.candidate_a_exp.prepare(payload)
		self.assertIsInstance(prep.prepared_object, types.CodeType)

		doc = frappe._dict({"status": "Open"})
		res = self.candidate_a_exp.evaluate(prep, doc)
		self.assertIsNone(res.error)
		self.assertTrue(res.result)

	def test_experimental_code_object_candidate_security_policy(self):
		# Verify that RestrictedPython blocks forbidden dunder access during compilation
		from frappe.utils.safe_exec import FrappeTransformer
		from RestrictedPython import compile_restricted

		forbidden_expr = "doc.__class__.__base__"
		with self.assertRaises(SyntaxError):
			compile_restricted(forbidden_expr, filename="<safe_eval>", policy=FrappeTransformer, mode="eval")

	def test_amortized_benchmark_repeats_samples_and_gates_correctness(self):
		runner = BenchmarkRunner(
			iterations_per_batch=4,
			num_batches=2,
			warmup_iterations=1,
		)
		results = runner.run_amortized_benchmarks(execution_counts=[1, 3])
		fixtures_by_id = {item["fixture_id"]: item for item in results["amortized"]}

		simple = fixtures_by_id["tier1_simple_equality"]
		self.assertTrue(simple["correctness_gate_passed"])
		for count in ("1", "3"):
			metric = simple["counts"][count]["Approach B (Normalized Execution Plan)"]
			self.assertTrue(metric["is_valid"])
			self.assertEqual(metric["valid_batches"], 2)
			self.assertEqual(len(metric["sample_execution_times_ms"]), 2)
			self.assertIn("median_exec_us_per_eval", metric)
			self.assertIn("median_core_exec_us_per_eval", metric)

		# The known has_changed parity failure must never emit timing values.
		failed = fixtures_by_id["edge_case_has_changed"]
		self.assertFalse(failed["correctness_gate_passed"])
		for count in ("1", "3"):
			for metric in failed["counts"][count].values():
				self.assertFalse(metric["is_valid"])
				self.assertIn("correctness gate failed", metric["error"])

	def test_amortized_benchmark_rejects_non_positive_execution_counts(self):
		runner = BenchmarkRunner(iterations_per_batch=1, num_batches=1, warmup_iterations=0)
		for counts in ([0], [-1], [1, 0]):
			with self.subTest(counts=counts):
				with self.assertRaises(ValueError):
					runner.run_amortized_benchmarks(execution_counts=counts)

	def test_benchmark_runner_full_suite_export(self):
		import os
		import tempfile

		with tempfile.TemporaryDirectory() as tmp_dir:
			json_path = os.path.join(tmp_dir, "benchmark_results.json")
			md_path = os.path.join(tmp_dir, "condition-backend-comparison-benchmark.md")

			runner = BenchmarkRunner(iterations_per_batch=10, num_batches=1, warmup_iterations=1)
			payload = runner.run_full_suite_and_export(json_path)

			self.assertEqual(payload["benchmark_protocol_version"], 2)
			self.assertIn("measurement_protocol", payload)
			self.assertIn("environment", payload)
			self.assertIn("correctness_suite", payload)
			self.assertIn("primary_benchmark", payload)
			self.assertIn("amortized_benchmark", payload)
			primary_fixture = next(
				item
				for item in payload["primary_benchmark"]["fixtures"]
				if item["fixture_id"] == "tier1_simple_equality"
			)
			self.assertTrue(primary_fixture["correctness_gate_passed"])
			plan_metric = primary_fixture["candidate_metrics"]["Approach B (Normalized Execution Plan)"]
			self.assertIn("median_core_us_per_exec", plan_metric)

			self.assertTrue(os.path.exists(json_path))
			self.assertTrue(os.path.exists(md_path))

			with open(md_path, encoding="utf-8") as f:
				md_content = f.read()

			self.assertIn("# FlexiRule — Condition Backend Comparison Benchmark Report", md_content)
			self.assertIn("Tier 1 — Simple", md_content)

	def test_report_evaluations_count_and_has_changed_contract(self):
		import json
		import os
		import tempfile

		with tempfile.TemporaryDirectory() as tmp_dir:
			json_path = os.path.join(tmp_dir, "benchmark_results.json")
			md_path = os.path.join(tmp_dir, "condition-backend-comparison-benchmark.md")

			runner = BenchmarkRunner(iterations_per_batch=100, num_batches=2, warmup_iterations=1)
			payload = runner.run_full_suite_and_export(json_path, md_path)

			# Verify total error-free evaluation count calculation
			calculated_evals = 0
			for fix in payload["primary_benchmark"]["fixtures"]:
				for metric in fix["candidate_metrics"].values():
					calculated_evals += metric.get("successful_evaluations", 0)

			with open(md_path, encoding="utf-8") as f:
				md_content = f.read()

			formatted_count_str = f"**{calculated_evals:,}**"
			self.assertIn(formatted_count_str, md_content)
			self.assertIn("has_changed", md_content)
			self.assertIn("ConditionCompiler", md_content)
