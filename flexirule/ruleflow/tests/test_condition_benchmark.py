# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json
import os
import tempfile
from typing import Any

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.condition_errors import ConditionEvaluationError, ConditionValidationError
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
from flexirule.ruleflow.tests.condition_benchmark.fixtures import (
	get_all_fixtures,
	get_canonical_fixtures,
)


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

		self.canonical_candidate = CanonicalConditionCandidate()
		self.canonical_prepared = CanonicalPreparedPlanCandidate()
		self.canonical_harness = ConditionComparisonHarness(
			[self.canonical_candidate, self.canonical_prepared]
		)

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

	def test_canonical_suite_agrees_on_all_canonical_fixtures(self):
		runner = BenchmarkRunner(
			iterations_per_batch=10, num_batches=1, warmup_iterations=1, use_canonical_suite=True
		)
		suite_results = runner.run_semantic_correctness_suite()

		failed_fixtures = [r for r in suite_results["results"] if not r["is_correct"]]
		failed_ids = [f["fixture_id"] for f in failed_fixtures]
		self.assertEqual(failed_ids, [], f"Canonical correctness failures: {failed_ids}")
		self.assertTrue(suite_results["all_correct"])

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
		self.assertFalse(check["matches_expected"])

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
		runner.legacy_candidates = [c1, c2]
		runner.candidates = [c1, c2]
		runner.harness = ConditionComparisonHarness([c1, c2])

		results = runner.run_primary_benchmarks()
		fix_metric = results["fixtures"][0]["candidate_metrics"]["C1"]
		self.assertFalse(fix_metric["is_valid_measurement"])
		self.assertIn("Warm-up", fix_metric["error"])

	def test_measurement_batch_failure_invalidates_batch(self):
		c1 = DummyCandidate(
			"C1", result=True, fail_after_eval_count=15
		)  # succeeds warmup (5), fails in batch 1
		c2 = DummyCandidate("C2", result=True)
		runner = BenchmarkRunner(iterations_per_batch=10, num_batches=2, warmup_iterations=5)
		runner.legacy_candidates = [c1, c2]
		runner.candidates = [c1, c2]
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

		failed = fixtures_by_id["edge_case_has_changed"]
		self.assertFalse(failed["correctness_gate_passed"])
		for count in ("1", "3"):
			for metric in failed["counts"][count].values():
				self.assertFalse(metric["is_valid"])
				self.assertIn("correctness gate failed", metric["error"])

	def test_amortized_benchmark_rejects_non_positive_execution_counts(self):
		runner = BenchmarkRunner(iterations_per_batch=1, num_batches=1, warmup_iterations=0)
		invalid_counts: list[list[Any]] = [[0], [-1], [1, 0], [True], [False], [1, True]]
		for counts in invalid_counts:
			with self.subTest(counts=counts):
				with self.assertRaises(ValueError):
					runner.run_amortized_benchmarks(execution_counts=counts)

	def test_benchmark_runner_full_suite_export(self):
		with tempfile.TemporaryDirectory() as tmp_dir:
			json_path = os.path.join(tmp_dir, "canonical_condition_benchmark_results.json")
			md_path = os.path.join(tmp_dir, "condition-backend-comparison-benchmark.md")

			runner = BenchmarkRunner(iterations_per_batch=10, num_batches=1, warmup_iterations=1)
			payload = runner.run_full_suite_and_export(json_path, md_path)

			self.assertEqual(payload["benchmark_protocol_version"], 2)
			self.assertIn("measurement_protocol", payload)
			self.assertIn("environment", payload)
			self.assertIn("legacy_suite", payload)
			self.assertIn("canonical_suite", payload)

			self.assertTrue(os.path.exists(json_path))
			self.assertTrue(os.path.exists(md_path))

			with open(md_path, encoding="utf-8") as f:
				md_content = f.read()

			self.assertIn(
				"# FlexiRule — Condition Backend Comprehensive Comparison Benchmark Report", md_content
			)
			self.assertIn("PR #469 Canonical Condition Backend Evaluation", md_content)

	def test_canonical_runner_export_produces_dedicated_json_and_markdown(self):
		with tempfile.TemporaryDirectory() as tmp_dir:
			json_path = os.path.join(tmp_dir, "canonical_condition_benchmark_results.json")
			md_path = os.path.join(tmp_dir, "condition-backend-comparison-benchmark.md")

			runner = BenchmarkRunner(
				iterations_per_batch=50, num_batches=2, warmup_iterations=1, use_canonical_suite=True
			)
			payload = runner.run_full_suite_and_export(json_path, md_path)

			self.assertTrue(os.path.exists(json_path))
			self.assertTrue(os.path.exists(md_path))

			self.assertIn("PR #469 Canonical Condition Backend", payload["benchmark_target"])

			with open(md_path, encoding="utf-8") as f:
				md_content = f.read()

			self.assertIn("PR #469 Canonical Condition Backend Evaluation", md_content)
			self.assertIn("Selected Production Option", md_content)

	# --- Explicit Short-Circuit Behavior Tests for All Benchmark Approaches ---

	def test_short_circuit_and_operator(self):
		and_payload = {
			"op": "and",
			"conditions": [
				{"left": {"ref": "doc.first_cond"}, "op": "==", "right": {"value": True}},
				{"left": {"ref": "doc.second_cond"}, "op": "==", "right": {"value": True}},
			],
		}

		for cand in self.candidates:
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

		for cand in self.candidates:
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

	def test_short_circuit_nested_groups(self):
		nested_payload = {
			"op": "and",
			"conditions": [
				{
					"op": "or",
					"conditions": [
						{"left": {"ref": "doc.cond_group1_a"}, "op": "==", "right": {"value": True}},
						{"left": {"ref": "doc.cond_group1_skipped"}, "op": "==", "right": {"value": True}},
					],
				},
				{
					"op": "and",
					"conditions": [
						{"left": {"ref": "doc.cond_group2_a"}, "op": "==", "right": {"value": True}},
						{"left": {"ref": "doc.cond_group2_skipped"}, "op": "==", "right": {"value": True}},
					],
				},
				{"left": {"ref": "doc.cond_outer_skipped"}, "op": "==", "right": {"value": True}},
			],
		}

		for cand in self.candidates:
			with self.subTest(candidate=cand.candidate_name):
				tracking_doc = TrackingDoc(
					{
						"cond_group1_a": True,
						"cond_group1_skipped": False,
						"cond_group2_a": False,
						"cond_group2_skipped": True,
						"cond_outer_skipped": True,
					}
				)
				prep = cand.prepare(nested_payload)
				res = cand.evaluate(prep, tracking_doc)

				self.assertIsNone(res.error)
				self.assertFalse(res.result)
				self.assertEqual(tracking_doc.access_counts.get("cond_group1_a", 0), 1)
				self.assertEqual(
					tracking_doc.access_counts.get("cond_group1_skipped", 0),
					0,
					f"Candidate '{cand.candidate_name}' evaluated cond_group1_skipped",
				)
				self.assertEqual(tracking_doc.access_counts.get("cond_group2_a", 0), 1)
				self.assertEqual(
					tracking_doc.access_counts.get("cond_group2_skipped", 0),
					0,
					f"Candidate '{cand.candidate_name}' evaluated cond_group2_skipped",
				)
				self.assertEqual(
					tracking_doc.access_counts.get("cond_outer_skipped", 0),
					0,
					f"Candidate '{cand.candidate_name}' evaluated cond_outer_skipped",
				)

	def test_short_circuit_collection_any(self):
		any_payload = {
			"collection": "doc.items",
			"op": "any",
			"alias": "item",
			"where": {
				"left": {"ref": "item.qty"},
				"op": ">",
				"right": {"value": 10},
			},
		}

		for cand in self.candidates:
			with self.subTest(candidate=cand.candidate_name):
				r1 = TrackingDoc({"item_code": "I1", "qty": 5})
				r2 = TrackingDoc({"item_code": "I2", "qty": 15})
				r3 = TrackingDoc({"item_code": "I3", "qty": 20})

				doc = frappe._dict({"items": [r1, r2, r3]})
				prep = cand.prepare(any_payload)
				res = cand.evaluate(prep, doc)

				self.assertIsNone(res.error)
				self.assertTrue(res.result)
				self.assertEqual(r1.access_counts.get("qty", 0), 1)
				self.assertEqual(r2.access_counts.get("qty", 0), 1)
				self.assertEqual(
					r3.access_counts.get("qty", 0),
					0,
					f"Candidate '{cand.candidate_name}' evaluated row 3 in collection 'any'",
				)

	def test_short_circuit_collection_all(self):
		all_payload = {
			"collection": "doc.items",
			"op": "all",
			"alias": "item",
			"where": {
				"left": {"ref": "item.qty"},
				"op": ">",
				"right": {"value": 10},
			},
		}

		for cand in self.candidates:
			with self.subTest(candidate=cand.candidate_name):
				r1 = TrackingDoc({"item_code": "I1", "qty": 15})
				r2 = TrackingDoc({"item_code": "I2", "qty": 5})
				r3 = TrackingDoc({"item_code": "I3", "qty": 20})

				doc = frappe._dict({"items": [r1, r2, r3]})
				prep = cand.prepare(all_payload)
				res = cand.evaluate(prep, doc)

				self.assertIsNone(res.error)
				self.assertFalse(res.result)
				self.assertEqual(r1.access_counts.get("qty", 0), 1)
				self.assertEqual(r2.access_counts.get("qty", 0), 1)
				self.assertEqual(
					r3.access_counts.get("qty", 0),
					0,
					f"Candidate '{cand.candidate_name}' evaluated row 3 in collection 'all'",
				)

	def test_short_circuit_collection_none(self):
		none_payload = {
			"collection": "doc.items",
			"op": "none",
			"alias": "item",
			"where": {
				"left": {"ref": "item.qty"},
				"op": ">",
				"right": {"value": 10},
			},
		}

		for cand in self.candidates:
			with self.subTest(candidate=cand.candidate_name):
				r1 = TrackingDoc({"item_code": "I1", "qty": 5})
				r2 = TrackingDoc({"item_code": "I2", "qty": 15})
				r3 = TrackingDoc({"item_code": "I3", "qty": 20})

				doc = frappe._dict({"items": [r1, r2, r3]})
				prep = cand.prepare(none_payload)
				res = cand.evaluate(prep, doc)

				self.assertIsNone(res.error)
				self.assertFalse(res.result)
				self.assertEqual(r1.access_counts.get("qty", 0), 1)
				self.assertEqual(r2.access_counts.get("qty", 0), 1)
				self.assertEqual(
					r3.access_counts.get("qty", 0),
					0,
					f"Candidate '{cand.candidate_name}' evaluated row 3 in collection 'none'",
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
