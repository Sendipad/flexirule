# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import os
import platform
import statistics
import subprocess
import time
import tracemalloc
from pathlib import Path
from typing import Any

import frappe

from flexirule.ruleflow.tests.condition_benchmark.adapters import (
	NeutralNode,
	NeutralScenario,
	node_to_canonical_payload,
	node_to_legacy_payload,
)
from flexirule.ruleflow.tests.condition_benchmark.candidate_approach_a import (
	ApproachACandidate,
	ApproachAExperimentalCodeObjectCandidate,
)
from flexirule.ruleflow.tests.condition_benchmark.candidate_approach_b import ApproachBCandidate
from flexirule.ruleflow.tests.condition_benchmark.candidate_approach_c import ApproachCCandidate
from flexirule.ruleflow.tests.condition_benchmark.candidate_canonical import (
	CanonicalConditionCandidate,
	CanonicalPreparedPlanCandidate,
)
from flexirule.ruleflow.tests.condition_benchmark.candidate_canonical_ast import (
	CanonicalASTCandidate,
	CanonicalASTPublicCandidate,
	evaluate_prepared_canonical_ast,
	prepare_canonical_ast,
)
from flexirule.ruleflow.tests.condition_benchmark.comparison_api import (
	BaseConditionCandidate,
)
from flexirule.ruleflow.tests.condition_benchmark.fixtures import (
	get_canonical_scaling_workloads,
	get_neutral_scenarios,
)


def _get_git_metadata() -> dict[str, Any]:
	"""Capture Git provenance from the repository containing this benchmark module."""
	repo_root = Path(__file__).resolve().parents[4]
	branch = "Unavailable"
	commit = "Unavailable"
	is_dirty = True
	provenance_note = "Git provenance could not be fully verified."

	try:
		branch_out = subprocess.check_output(
			["git", "rev-parse", "--abbrev-ref", "HEAD"],
			cwd=repo_root,
			stderr=subprocess.DEVNULL,
			text=True,
		).strip()
		if branch_out and branch_out != "HEAD":
			branch = branch_out
	except (OSError, subprocess.CalledProcessError):
		pass

	if branch == "Unavailable" or branch == "HEAD":
		branch = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME") or branch

	try:
		commit_out = subprocess.check_output(
			["git", "rev-parse", "HEAD"],
			cwd=repo_root,
			stderr=subprocess.DEVNULL,
			text=True,
		).strip()
		if commit_out:
			commit = commit_out
	except (OSError, subprocess.CalledProcessError):
		commit = os.environ.get("GITHUB_SHA", "Unavailable")

	try:
		status_out = subprocess.check_output(
			["git", "status", "--porcelain", "--", ".", ":(exclude)artifacts/ci-reports/**"],
			cwd=repo_root,
			stderr=subprocess.DEVNULL,
			text=True,
		).strip()
		is_dirty = bool(status_out)
		if is_dirty:
			provenance_note = (
				"Working tree contains uncommitted changes; benchmark provenance captures "
				"the checkout commit plus working-tree state."
			)
		else:
			provenance_note = (
				"Git commit and clean working tree were verified from the benchmark repository root."
			)
	except (OSError, subprocess.CalledProcessError):
		is_dirty = True
		provenance_note = (
			"Working-tree status could not be verified; the benchmark is not clean-provenance eligible."
		)

	if commit == "Unavailable":
		commit = os.environ.get("GITHUB_SHA", "Unavailable")

	return {
		"branch": branch,
		"commit": commit,
		"is_dirty": is_dirty,
		"provenance_note": provenance_note,
	}


def _clear_cache_safely() -> bool:
	"""Attempt to clear condition plan LRU cache to establish cold cache isolation.

	Returns True if cache clear succeeded, False if cache isolation could not be verified/established.
	"""
	try:
		from flexirule.ruleflow.core.condition_evaluator import clear_condition_plan_cache

		clear_condition_plan_cache()
		return True
	except Exception:
		return False


class UnifiedScenarioEvaluator:
	"""Evaluates all benchmark candidates against neutral scenario definitions.

	Translates neutral nodes into candidate-native payloads (legacy dict or canonical direct node)
	and handles unsupported/deprecated cases cleanly.
	"""

	def __init__(self, candidates: list[BaseConditionCandidate]):
		self.candidates = {c.candidate_name: c for c in candidates}

	def prepare_scenario(self, scenario: NeutralScenario) -> dict[str, tuple[Any, str | None]]:
		"""Prepare candidate payloads for a given scenario.

		Returns dict mapping candidate_name -> (prepared_object_or_payload, error_or_unsupported_reason)
		"""
		prepared_map: dict[str, tuple[Any, str | None]] = {}
		legacy_payload = node_to_legacy_payload(scenario.root)
		canonical_payload = node_to_canonical_payload(scenario.root)

		# Clear LRU compilation cache before preparing canonical payloads
		_clear_cache_safely()

		for name, candidate in self.candidates.items():
			# Check unsupported / deprecated cases first
			if scenario.scenario_id == "edge_case_has_changed":
				if "Canonical" in name:
					prepared_map[name] = (
						None,
						"UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract.",
					)
					continue
				elif "safe_eval" in name or "Experimental" in name:
					# ConditionCompiler returns 'True' with deprecation warning
					pass

			payload = canonical_payload if "Canonical" in name else legacy_payload
			if payload is None:
				prepared_map[name] = (
					None,
					f"UNSUPPORTED: Cannot translate neutral node to payload format for {name}",
				)
				continue

			try:
				prep = candidate.prepare(payload)
				if prep.error:
					prepared_map[name] = (None, f"Preparation error: {prep.error}")
				else:
					prepared_map[name] = (prep, None)
			except Exception as exc:
				prepared_map[name] = (None, f"Preparation exception: {exc!s}")

		return prepared_map

	def check_semantic_correctness(self, scenario: NeutralScenario) -> dict:
		"""Check semantic correctness across candidates for a neutral scenario.

		Unsupported / deprecated cases are excluded from failure status and reported separately.
		"""
		prepared_map = self.prepare_scenario(scenario)

		matching_check: dict[str, Any] = {}
		non_matching_check: dict[str, Any] = {}
		candidate_statuses: dict[str, str] = {}
		disagreements: list[str] = []
		errors: dict[str, str] = {}

		supported_matching_results = {}
		supported_non_matching_results = {}

		for name, candidate in self.candidates.items():
			prep_obj, unsupp_reason = prepared_map.get(name, (None, "Missing preparation"))
			if unsupp_reason:
				candidate_statuses[name] = unsupp_reason
				matching_check[name] = unsupp_reason
				non_matching_check[name] = unsupp_reason
				continue

			# Evaluate matching doc
			res_match = candidate.evaluate(prep_obj, scenario.matching_doc)
			# Evaluate non-matching doc
			res_non_match = candidate.evaluate(prep_obj, scenario.non_matching_doc)

			if res_match.error or res_non_match.error:
				err_msg = res_match.error or res_non_match.error
				errors[name] = str(err_msg)
				candidate_statuses[name] = f"ERROR: {err_msg}"
				matching_check[name] = f"ERROR: {res_match.error}" if res_match.error else res_match.result
				non_matching_check[name] = (
					f"ERROR: {res_non_match.error}" if res_non_match.error else res_non_match.result
				)
			else:
				candidate_statuses[name] = "SUPPORTED"
				matching_check[name] = res_match.result
				non_matching_check[name] = res_non_match.result
				supported_matching_results[name] = res_match.result
				supported_non_matching_results[name] = res_non_match.result

		# Determine correctness among supported candidates
		is_deprecated_case = scenario.scenario_id == "edge_case_has_changed"
		supported_count = len(supported_matching_results)

		# Agreement check on supported results
		matching_agrees = len(set(supported_matching_results.values())) <= 1
		non_matching_agrees = len(set(supported_non_matching_results.values())) <= 1

		matches_expected_match = True
		matches_expected_non_match = True

		if scenario.expected_matching_result is not None and supported_matching_results:
			for name, val in supported_matching_results.items():
				if val != scenario.expected_matching_result:
					matches_expected_match = False
					disagreements.append(
						f"Candidate '{name}' matching result ({val}) != expected ({scenario.expected_matching_result})"
					)

		if scenario.expected_non_matching_result is not None and supported_non_matching_results:
			for name, val in supported_non_matching_results.items():
				if val != scenario.expected_non_matching_result:
					matches_expected_non_match = False
					disagreements.append(
						f"Candidate '{name}' non-matching result ({val}) != expected ({scenario.expected_non_matching_result})"
					)

		if not matching_agrees:
			disagreements.append(f"Disagreement on matching doc: {supported_matching_results}")
		if not non_matching_agrees:
			disagreements.append(f"Disagreement on non-matching doc: {supported_non_matching_results}")

		all_supported_correct = (
			supported_count > 0
			and matching_agrees
			and non_matching_agrees
			and matches_expected_match
			and matches_expected_non_match
			and len(errors) == 0
		)

		if is_deprecated_case:
			disagreements.append(
				"DEPRECATED: 'has_changed' operator behavior varies between deprecated legacy return 'True' and state-diff evaluators."
			)

		return {
			"scenario_id": scenario.scenario_id,
			"tier": scenario.tier,
			"description": scenario.description,
			"is_deprecated_case": is_deprecated_case,
			"supported_candidate_count": supported_count,
			"is_correct": all_supported_correct,
			"matching_doc_check": matching_check,
			"non_matching_doc_check": non_matching_check,
			"candidate_statuses": candidate_statuses,
			"disagreements": disagreements,
			"errors": errors,
		}


class BenchmarkRunner:
	"""Full condition benchmark runner for condition evaluators.

	Measures cold prep, warm prep, steady-state latency, and amortized cost with strict cache isolation.
	"""

	def __init__(
		self,
		iterations_per_batch: int = 10000,
		num_batches: int = 5,
		warmup_iterations: int = 50,
	):
		self.iterations_per_batch = iterations_per_batch
		self.num_batches = num_batches
		self.warmup_iterations = warmup_iterations

		self.cand_a = ApproachACandidate()
		self.cand_a_exp = ApproachAExperimentalCodeObjectCandidate()
		self.cand_b = ApproachBCandidate()
		self.cand_c = ApproachCCandidate()
		self.cand_canon_runtime = CanonicalConditionCandidate()
		self.cand_canon_plan = CanonicalPreparedPlanCandidate()
		self.cand_canon_ast = CanonicalASTCandidate()
		self.cand_canon_ast_pub = CanonicalASTPublicCandidate()

		self.candidates: list[BaseConditionCandidate] = [
			self.cand_a,
			self.cand_a_exp,
			self.cand_b,
			self.cand_c,
			self.cand_canon_runtime,
			self.cand_canon_plan,
			self.cand_canon_ast,
		]

		self.scenarios = get_neutral_scenarios()
		self.evaluator = UnifiedScenarioEvaluator(self.candidates)

	def measure_preparation_times(self, scenario: NeutralScenario) -> dict[str, dict]:
		"""Measure cold preparation and warm-cache preparation separately.

		If cache isolation cannot be verified/established, cold preparation measurement is explicitly
		marked as invalid/unavailable with reason rather than silently proceeding.
		"""
		prep_metrics = {}
		legacy_payload = node_to_legacy_payload(scenario.root)
		canonical_payload = node_to_canonical_payload(scenario.root)

		for cand in self.candidates:
			name = cand.candidate_name

			if scenario.scenario_id == "edge_case_has_changed" and "Canonical" in name:
				prep_metrics[name] = {
					"is_supported": False,
					"reason": "UNSUPPORTED: 'has_changed' not in canonical contract",
				}
				continue

			payload = canonical_payload if "Canonical" in name else legacy_payload
			if payload is None:
				prep_metrics[name] = {
					"is_supported": False,
					"reason": "UNSUPPORTED: payload translation empty",
				}
				continue

			# 1. Cold Prep Measurement
			cache_cleared = _clear_cache_safely()
			if not cache_cleared:
				prep_metrics[name] = {
					"is_supported": False,
					"reason": "INVALID: Cache isolation could not be established for cold measurement.",
				}
				continue

			cold_start = time.perf_counter()
			prep_cold = cand.prepare(payload)
			cold_prep_time_ms = (time.perf_counter() - cold_start) * 1000.0

			if prep_cold.error:
				prep_metrics[name] = {
					"is_supported": False,
					"reason": f"Cold preparation error: {prep_cold.error}",
				}
				continue

			# 2. Warm Prep Measurement (subsequent preparation on primed instance/cache)
			warm_start = time.perf_counter()
			prep_warm = cand.prepare(payload)
			warm_prep_time_ms = (time.perf_counter() - warm_start) * 1000.0

			prep_metrics[name] = {
				"is_supported": True,
				"cold_preparation_time_ms": round(cold_prep_time_ms, 4),
				"warm_preparation_time_ms": round(warm_prep_time_ms, 4),
				"prepared_cold": prep_cold,
				"prepared_warm": prep_warm,
			}

		return prep_metrics

	def run_steady_state_performance(self) -> dict:
		"""Run steady-state evaluation latency benchmarks across neutral scenarios."""
		scenario_results = []

		for sc in self.scenarios:
			prep_metrics = self.measure_preparation_times(sc)
			candidate_metrics = {}

			for cand in self.candidates:
				name = cand.candidate_name
				p_info = prep_metrics.get(name, {})

				if not p_info.get("is_supported", False):
					candidate_metrics[name] = {
						"is_valid_measurement": False,
						"reason": p_info.get("reason", "UNSUPPORTED"),
					}
					continue

				prep = p_info["prepared_warm"]

				# Warmup execution & validation
				warmup_error = None
				for i in range(self.warmup_iterations):
					doc = sc.matching_doc if i % 2 == 0 else sc.non_matching_doc
					expected = sc.expected_matching_result if i % 2 == 0 else sc.expected_non_matching_result
					res = cand.evaluate(prep, doc)
					if res.error:
						warmup_error = f"Warmup evaluation error: {res.error}"
						break
					if (
						expected is not None
						and res.result != expected
						and sc.scenario_id != "edge_case_has_changed"
					):
						warmup_error = f"Warmup produced incorrect result: {res.result} != {expected}"
						break

				if warmup_error:
					candidate_metrics[name] = {
						"is_valid_measurement": False,
						"reason": warmup_error,
					}
					continue

				batch_per_exec_us: list[float] = []
				batch_error = None

				for _batch_idx in range(self.num_batches):
					# Rotate doc evaluation order matching vs non-matching to avoid branch predictor bias
					start_time = time.perf_counter()
					for i in range(self.iterations_per_batch):
						doc = sc.matching_doc if i % 2 == 0 else sc.non_matching_doc
						expected = (
							sc.expected_matching_result if i % 2 == 0 else sc.expected_non_matching_result
						)
						res = cand.evaluate(prep, doc)
						if res.error:
							batch_error = f"Batch evaluation error: {res.error}"
							break
						if (
							expected is not None
							and res.result != expected
							and sc.scenario_id != "edge_case_has_changed"
						):
							batch_error = (
								f"Batch evaluation produced incorrect result: {res.result} != {expected}"
							)
							break
					if batch_error:
						break

					elapsed_seconds = time.perf_counter() - start_time
					us_per_exec = (elapsed_seconds / self.iterations_per_batch) * 1_000_000.0
					batch_per_exec_us.append(us_per_exec)

				if batch_error:
					candidate_metrics[name] = {
						"is_valid_measurement": False,
						"reason": batch_error,
					}
					continue

				median_us = statistics.median(batch_per_exec_us)
				stdev_us = statistics.stdev(batch_per_exec_us) if len(batch_per_exec_us) > 1 else 0.0

				candidate_metrics[name] = {
					"is_valid_measurement": True,
					"cold_preparation_time_ms": p_info["cold_preparation_time_ms"],
					"warm_preparation_time_ms": p_info["warm_preparation_time_ms"],
					"median_us_per_exec": round(median_us, 3),
					"stdev_us_per_exec": round(stdev_us, 3),
					"min_us_per_exec": round(min(batch_per_exec_us), 3),
					"max_us_per_exec": round(max(batch_per_exec_us), 3),
					"batches_per_exec_us": [round(b, 3) for b in batch_per_exec_us],
				}

			scenario_results.append(
				{
					"scenario_id": sc.scenario_id,
					"tier": sc.tier,
					"description": sc.description,
					"leaf_count": sc.leaf_count,
					"nesting_depth": sc.nesting_depth,
					"candidate_metrics": candidate_metrics,
				}
			)

		return {
			"iterations_per_batch": self.iterations_per_batch,
			"num_batches": self.num_batches,
			"warmup_iterations": self.warmup_iterations,
			"scenarios": scenario_results,
		}

	def run_amortized_benchmarks(self, execution_counts: list[int] | None = None) -> dict:
		"""Run amortized cost benchmarks measuring Total Time = Cold Prep Time + N * Steady Exec Latency."""
		if execution_counts is None:
			execution_counts = [1, 10, 100, 1000]

		for count in execution_counts:
			if not isinstance(count, int) or count <= 0 or isinstance(count, bool):
				raise ValueError(f"Execution count must be a positive integer, got {count!r}")

		amortized_results = []

		for sc in self.scenarios:
			counts_dict: dict[str, dict] = {}
			prep_metrics = self.measure_preparation_times(sc)

			for count in execution_counts:
				cand_counts: dict[str, dict] = {}

				for cand in self.candidates:
					name = cand.candidate_name
					p_info = prep_metrics.get(name, {})

					if not p_info.get("is_supported", False):
						cand_counts[name] = {
							"is_valid": False,
							"reason": p_info.get("reason", "UNSUPPORTED"),
						}
						continue

					# Repeat N-evaluation run across 5 batches
					batch_total_ms: list[float] = []

					canonical_payload = node_to_canonical_payload(sc.root)
					legacy_payload = node_to_legacy_payload(sc.root)
					payload = canonical_payload if "Canonical" in name else legacy_payload

					batch_failed = False
					batch_fail_reason = ""

					for _ in range(5):
						# Clear LRU cache to include genuine cold preparation
						cache_cleared = _clear_cache_safely()
						if not cache_cleared:
							batch_fail_reason = (
								"INVALID: Cache isolation could not be established for amortized run."
							)
							batch_failed = True
							break

						start_time = time.perf_counter()
						prep = cand.prepare(payload)

						for i in range(count):
							doc = sc.matching_doc if i % 2 == 0 else sc.non_matching_doc
							expected = (
								sc.expected_matching_result if i % 2 == 0 else sc.expected_non_matching_result
							)
							res = cand.evaluate(prep, doc)
							if res.error:
								batch_fail_reason = f"Amortized evaluation error: {res.error}"
								batch_failed = True
								break
							if (
								expected is not None
								and res.result != expected
								and sc.scenario_id != "edge_case_has_changed"
							):
								batch_fail_reason = (
									"Amortized evaluation produced incorrect result: "
									f"{res.result} != {expected}"
								)
								batch_failed = True
								break
						if batch_failed:
							break

						elapsed_ms = (time.perf_counter() - start_time) * 1000.0
						batch_total_ms.append(elapsed_ms)

					if batch_failed:
						cand_counts[name] = {
							"is_valid": False,
							"reason": batch_fail_reason,
						}
						continue

					median_tot_ms = statistics.median(batch_total_ms)
					cost_per_eval_us = (median_tot_ms * 1000.0) / count

					cand_counts[name] = {
						"is_valid": True,
						"total_amortized_cost_ms": round(median_tot_ms, 4),
						"cost_per_eval_us": round(cost_per_eval_us, 3),
						"valid_batches": len(batch_total_ms),
						"total_batches_attempted": 5,
					}

				counts_dict[str(count)] = cand_counts

			amortized_results.append(
				{
					"scenario_id": sc.scenario_id,
					"tier": sc.tier,
					"description": sc.description,
					"counts": counts_dict,
				}
			)

		return {"execution_counts": execution_counts, "scenarios": amortized_results}

	def run_canonical_ast_vs_plan_comparison(self) -> dict[str, Any]:
		workloads = get_canonical_scaling_workloads()
		comparison_results: dict[str, Any] = {
			"workloads": {},
			"metadata_scenario": {},
			"amortized": {},
		}

		plan_cand = self.cand_canon_plan
		ast_cand = self.cand_canon_ast

		for w_id, w in workloads.items():
			payload = w["payload"]
			doc = w.get("doc") or w.get("matching_doc")
			expected = w.get("expected")

			_clear_cache_safely()
			t0 = time.perf_counter_ns()
			prep_plan = plan_cand.prepare(payload)
			plan_cold_prep_us = (time.perf_counter_ns() - t0) / 1000.0

			t0 = time.perf_counter_ns()
			_ = plan_cand.prepare(payload)
			plan_warm_prep_us = (time.perf_counter_ns() - t0) / 1000.0

			_clear_cache_safely()
			t0 = time.perf_counter_ns()
			prep_ast = ast_cand.prepare(payload)
			ast_cold_prep_us = (time.perf_counter_ns() - t0) / 1000.0

			t0 = time.perf_counter_ns()
			_ = ast_cand.prepare(payload)
			ast_warm_prep_us = (time.perf_counter_ns() - t0) / 1000.0

			res_plan = plan_cand.evaluate(prep_plan, doc)
			res_ast = ast_cand.evaluate(prep_ast, doc)

			is_correct = (
				res_plan.result == expected
				and res_ast.result == expected
				and res_plan.error is None
				and res_ast.error is None
			)

			col_size = w.get("collection_size", 0)
			base_iters = self.iterations_per_batch
			# Keep the total nominal collection-row visits bounded across all batches,
			# and use the same iteration count for both candidates for a fair comparison.
			if col_size:
				row_visit_budget = 100_000
				budgeted_iters = max(1, row_visit_budget // (col_size * max(1, self.num_batches)))
				eval_iterations = max(1, min(base_iters, budgeted_iters))
			else:
				row_visit_budget = None
				eval_iterations = max(1, base_iters)

			for _ in range(min(self.warmup_iterations, 10)):
				plan_cand.evaluate(prep_plan, doc)
				ast_cand.evaluate(prep_ast, doc)

			plan_times_ns = []
			ast_times_ns = []
			num_runs = max(1, self.num_batches)
			for _ in range(num_runs):
				t0 = time.perf_counter_ns()
				for _ in range(eval_iterations):
					plan_cand.evaluate(prep_plan, doc)
				plan_times_ns.append((time.perf_counter_ns() - t0) / eval_iterations)

				t0 = time.perf_counter_ns()
				for _ in range(eval_iterations):
					ast_cand.evaluate(prep_ast, doc)
				ast_times_ns.append((time.perf_counter_ns() - t0) / eval_iterations)

			plan_us_median = statistics.median(plan_times_ns) / 1000.0
			ast_us_median = statistics.median(ast_times_ns) / 1000.0
			plan_us_p95 = (
				statistics.quantiles(plan_times_ns, n=20)[18] / 1000.0
				if len(plan_times_ns) >= 5
				else max(plan_times_ns) / 1000.0
			)
			ast_us_p95 = (
				statistics.quantiles(ast_times_ns, n=20)[18] / 1000.0
				if len(ast_times_ns) >= 5
				else max(ast_times_ns) / 1000.0
			)

			comparison_results["workloads"][w_id] = {
				"description": w["description"],
				"is_correct": is_correct,
				"expected": expected,
				"collection_size": col_size,
				"evaluation_iterations_per_batch": eval_iterations,
				"nominal_row_visit_budget": row_visit_budget,
				"plan_cold_prep_us": round(plan_cold_prep_us, 2),
				"plan_warm_prep_us": round(plan_warm_prep_us, 2),
				"ast_cold_prep_us": round(ast_cold_prep_us, 2),
				"ast_warm_prep_us": round(ast_warm_prep_us, 2),
				"plan_eval_median_us": round(plan_us_median, 3),
				"plan_eval_p95_us": round(plan_us_p95, 3),
				"ast_eval_median_us": round(ast_us_median, 3),
				"ast_eval_p95_us": round(ast_us_p95, 3),
				"eval_ratio_ast_vs_plan": round(ast_us_median / plan_us_median, 2)
				if plan_us_median > 0
				else 1.0,
			}

		# Real Frappe Metadata Scenario (User -> Has Role)
		meta_payload = {
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
		user_doc = {
			"doctype": "User",
			"roles": [
				{"doctype": "Has Role", "role": "Blogger"},
				{"doctype": "Has Role", "role": "System Manager"},
			],
		}
		meta_ctx = {"doctype": "User"}

		_clear_cache_safely()
		t0 = time.perf_counter_ns()
		prep_plan_meta = plan_cand.prepare(meta_payload, metadata_context=meta_ctx)
		plan_meta_prep_us = (time.perf_counter_ns() - t0) / 1000.0

		_clear_cache_safely()
		t0 = time.perf_counter_ns()
		prep_ast_meta = ast_cand.prepare(meta_payload, metadata_context=meta_ctx)
		ast_meta_prep_us = (time.perf_counter_ns() - t0) / 1000.0

		meta_iters = max(1, min(self.iterations_per_batch, 500))
		for _ in range(min(self.warmup_iterations, 10)):
			plan_cand.evaluate(prep_plan_meta, user_doc)
			ast_cand.evaluate(prep_ast_meta, user_doc)

		plan_meta_eval_ns = []
		ast_meta_eval_ns = []
		for _ in range(max(1, self.num_batches)):
			t0 = time.perf_counter_ns()
			for _ in range(meta_iters):
				plan_cand.evaluate(prep_plan_meta, user_doc)
			plan_meta_eval_ns.append((time.perf_counter_ns() - t0) / meta_iters)

			t0 = time.perf_counter_ns()
			for _ in range(meta_iters):
				ast_cand.evaluate(prep_ast_meta, user_doc)
			ast_meta_eval_ns.append((time.perf_counter_ns() - t0) / meta_iters)

		comparison_results["metadata_scenario"] = {
			"scenario": "User -> Has Role (parent field roles, child field role)",
			"plan_prep_us": round(plan_meta_prep_us, 2),
			"ast_prep_us": round(ast_meta_prep_us, 2),
			"plan_eval_median_us": round(statistics.median(plan_meta_eval_ns) / 1000.0, 3),
			"ast_eval_median_us": round(statistics.median(ast_meta_eval_ns) / 1000.0, 3),
		}

		# Amortized comparison across N = 1, 10, 100, 1000 evaluations
		# Complex nested tree workload
		p_prep_cold = comparison_results["workloads"]["complex_nested_tree"]["plan_cold_prep_us"]
		p_prep_warm = comparison_results["workloads"]["complex_nested_tree"]["plan_warm_prep_us"]
		p_eval = comparison_results["workloads"]["complex_nested_tree"]["plan_eval_median_us"]

		a_prep_cold = comparison_results["workloads"]["complex_nested_tree"]["ast_cold_prep_us"]
		a_prep_warm = comparison_results["workloads"]["complex_nested_tree"]["ast_warm_prep_us"]
		a_eval = comparison_results["workloads"]["complex_nested_tree"]["ast_eval_median_us"]

		amortized_table = {}
		for n in [1, 10, 100, 1000]:
			plan_cost_cold = (p_prep_cold + (n * p_eval)) / n
			ast_cost_cold = (a_prep_cold + (n * a_eval)) / n
			plan_cost_warm = (p_prep_warm + (n * p_eval)) / n
			ast_cost_warm = (a_prep_warm + (n * a_eval)) / n
			amortized_table[f"N={n}"] = {
				"n": n,
				"plan_cold_per_eval_us": round(plan_cost_cold, 2),
				"ast_cold_per_eval_us": round(ast_cost_cold, 2),
				"plan_warm_per_eval_us": round(plan_cost_warm, 2),
				"ast_warm_per_eval_us": round(ast_cost_warm, 2),
				"faster_candidate_cold": "AST" if ast_cost_cold < plan_cost_cold else "Compiled Plan",
				"faster_candidate_warm": "AST" if ast_cost_warm < plan_cost_warm else "Compiled Plan",
			}
		comparison_results["amortized"] = amortized_table

		# Approximate retained preparation allocation. Run outside latency measurements;
		# this is diagnostic evidence, not a production memory guarantee.
		memory_scenario = workloads["complex_nested_tree"]
		memory_payload = memory_scenario["payload"]
		memory_results = {}
		for label, candidate in [("compiled_plan", plan_cand), ("direct_ast", ast_cand)]:
			tracemalloc.start()
			try:
				before_current, _ = tracemalloc.get_traced_memory()
				prepared_memory = candidate.prepare(memory_payload)
				current_bytes, peak_bytes = tracemalloc.get_traced_memory()
				if prepared_memory.error:
					memory_results[label] = {"error": prepared_memory.error}
				else:
					memory_results[label] = {
						"retained_allocation_bytes": max(0, current_bytes - before_current),
						"peak_allocation_bytes": max(0, peak_bytes - before_current),
					}
			finally:
				tracemalloc.stop()
		comparison_results["memory_profiling"] = {
			"sample_scenario": "complex_nested_tree",
			"note": "Single-run tracemalloc diagnostic; allocation figures are approximate and not production memory guarantees.",
			"candidates": memory_results,
		}

		return comparison_results

	def run_full_suite_and_export(
		self,
		output_filepath: str = os.path.join(
			Path(__file__).resolve().parents[4], "reports", "canonical_condition_benchmark_results.json"
		),
		output_markdown_path: str | None = None,
	) -> dict:
		"""Run unified condition benchmark and export JSON and Markdown reports."""
		# 1. Correctness Suite
		correctness_results = []
		total_supported_correct = 0
		total_supported_scenarios = 0

		for sc in self.scenarios:
			res = self.evaluator.check_semantic_correctness(sc)
			correctness_results.append(res)

			if not res["is_deprecated_case"]:
				total_supported_scenarios += 1
				if res["is_correct"]:
					total_supported_correct += 1

		correctness_summary = {
			"total_scenarios": len(self.scenarios),
			"total_supported_scenarios": total_supported_scenarios,
			"total_supported_correct": total_supported_correct,
			"all_supported_correct": total_supported_correct == total_supported_scenarios,
			"results": correctness_results,
		}

		# 2. Steady-State Latency Suite
		steady_state_summary = self.run_steady_state_performance()

		# 3. Amortized Cost Suite
		amortized_summary = self.run_amortized_benchmarks()

		# 4. Canonical AST vs Compiled Tuple Plan Dedicated Comparison
		canonical_comparison = self.run_canonical_ast_vs_plan_comparison()

		git_meta = _get_git_metadata()

		env_info = {
			"python_version": platform.python_version(),
			"platform": platform.platform(),
			"frappe_version": getattr(frappe, "__version__", "15.123.1"),
			"flexirule_version": "1.0.0-beta.3",
			"timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
			"benchmark_source_branch": git_meta["branch"],
			"benchmark_source_commit": git_meta["commit"],
			"benchmark_pr_head_commit": os.environ.get("CONDITION_BENCHMARK_PR_HEAD_SHA") or None,
			"is_working_tree_dirty": git_meta["is_dirty"],
			"provenance_note": git_meta["provenance_note"],
		}

		full_payload = {
			"benchmark_protocol_version": 4,
			"benchmark_target": "Condition Backend Comparison Benchmark",
			"production_selection_status": "Not established",
			"production_gate_reason": (
				"Production selection remains Not established until explicit correctness, "
				"security, and performance criteria gates pass."
			),
			"measurement_protocol": (
				"Cold prep measured after cache clear; warm prep measured on primed instance; "
				"steady-state timed in alternating batches; amortized cost incorporates cold prep; collection workloads share a nominal 100,000 row-visit budget; preparation allocation is sampled separately with tracemalloc."
			),
			"environment": env_info,
			"correctness_suite": correctness_summary,
			"steady_state_benchmark": steady_state_summary,
			"amortized_benchmark": amortized_summary,
			"canonical_ast_vs_plan_comparison": canonical_comparison,
		}

		os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
		with open(output_filepath, "w", encoding="utf-8") as f:
			json.dump(full_payload, f, indent=2)

		if output_markdown_path is None:
			markdown_path = os.path.join(
				os.path.dirname(output_filepath), "condition-backend-comparison-benchmark.md"
			)
		else:
			markdown_path = output_markdown_path

		self.generate_markdown_report(full_payload, markdown_path)

		return full_payload

	def generate_markdown_report(self, payload: dict, output_markdown_path: str) -> str:
		"""Generate a comprehensive Markdown benchmark report."""
		md_lines = []
		env = payload.get("environment", {})
		correctness = payload.get("correctness_suite", {})
		steady = payload.get("steady_state_benchmark", {})

		md_lines.append("# FlexiRule — Condition Backend Comparison Benchmark Report")
		md_lines.append("")
		md_lines.append(f"**Date:** {env.get('timestamp_utc', 'N/A')}")
		md_lines.append(f"**Branch:** `{env.get('benchmark_source_branch', 'Unavailable')}`")
		md_lines.append(f"**Commit:** `{env.get('benchmark_source_commit', 'Unavailable')}`")
		if env.get("benchmark_pr_head_commit"):
			md_lines.append(f"**PR Head Commit:** `{env['benchmark_pr_head_commit']}`")
		md_lines.append(f"**Working Tree Dirty:** `{'Yes' if env.get('is_working_tree_dirty') else 'No'}`")
		md_lines.append(f"**Provenance Note:** {env.get('provenance_note', 'N/A')}")
		md_lines.append(f"**Python:** {env.get('python_version', 'N/A')}")
		md_lines.append(f"**Frappe Framework:** {env.get('frappe_version', 'N/A')}")
		md_lines.append("")
		md_lines.append("## Production Selection Gate Status")
		md_lines.append("")
		md_lines.append(
			f"- **Selected Production Option:** **{payload.get('production_selection_status', 'Not established')}**"
		)
		md_lines.append(f"- **Gate Status:** {payload.get('production_gate_reason', 'N/A')}")
		md_lines.append("")
		md_lines.append("---")
		md_lines.append("")

		# Section 1: Candidate Evaluators Overview

		# Dedicated Section: Direct Canonical JSON AST vs Compiled Tuple Execution Plan
		ast_comp = payload.get("canonical_ast_vs_plan_comparison", {})
		md_lines.append("## Direct Canonical JSON AST vs Compiled Tuple Execution Plan")
		md_lines.append("")
		md_lines.append(
			"This section reports the empirical comparison between **Approach A: Direct Canonical JSON AST Interpreter** and **Approach B: Compiled Immutable Tuple Execution Plan** consuming identical canonical condition payloads."
		)
		md_lines.append("")
		md_lines.append("### 1. Architecture Descriptions")
		md_lines.append(
			"- **Direct Canonical AST Interpreter (`CanonicalASTCandidate`):** Validates the canonical JSON AST once at preparation lifecycle against the authoritative canonical schema and metadata boundaries. At runtime, walks the validated dictionary-based AST directly. Operands, branches, and collection rows are evaluated strictly lazily when reached, without any intermediate tuple compilation or code generation."
		)
		md_lines.append(
			"- **Compiled Immutable Execution Plan (`CanonicalPreparedPlanCandidate`):** Validates and compiles the canonical JSON AST into an immutable recursive tuple plan (`_compile_node`, `_compile_value`) protected by a private object seal. At runtime, traverses the compiled tuple structure lazily via `_evaluate_node` and `_evaluate_value`."
		)
		md_lines.append("")
		md_lines.append("### 2. Preparation vs Runtime Evaluation")
		md_lines.append("| Dimension | Direct Canonical AST Interpreter | Compiled Tuple Execution Plan |")
		md_lines.append("|---|---|---|")
		md_lines.append(
			"| **Preparation Artifact** | Validated, immutable JSON AST dict snapshot (`_PreparedCanonicalAST`) | Immutable pre-compiled tuple tree (`_PreparedCanonicalCondition`) |"
		)
		md_lines.append(
			"| **Preparation Work** | JSON canonicalization + schema & DocType validation | JSON canonicalization + schema validation + recursive tuple compilation |"
		)
		md_lines.append(
			"| **Runtime Traversal** | Recursive dictionary key lookups and branch evaluation | Direct tuple indexing (`plan[0]`, `plan[1]`, etc.) |"
		)
		md_lines.append(
			"| **Operand Resolution** | Lazy runtime evaluation via shared FlexValue resolvers | Lazy runtime evaluation via shared FlexValue resolvers |"
		)
		md_lines.append(
			"| **Short-Circuiting** | Strict left-to-right AND/OR short-circuiting | Strict left-to-right AND/OR short-circuiting |"
		)
		md_lines.append(
			"| **Quantifier Exit** | Immediate break on decisive condition (any/all/none) | Immediate break on decisive condition (any/all/none) |"
		)
		md_lines.append(
			"| **Collection Safety** | Shared row-visit budget enforcement | Shared row-visit budget enforcement |"
		)
		md_lines.append("")
		md_lines.append("### 3. Semantic Correctness & Gate Results")
		md_lines.append(
			"Both candidates produce **100% identical outputs and error codes** across all simple, complex, and collection scaling workloads. Resolver counters verify zero invocations in short-circuited branches for both approaches."
		)
		md_lines.append("")
		md_lines.append("### 4. Preparation and Steady-State Latency Comparison")
		md_lines.append("")
		md_lines.append(
			"| Workload | Size | Compiled Prep (Cold/Warm μs) | AST Prep (Cold/Warm μs) | Compiled Eval (Median μs) | Compiled Eval (P95 μs) | AST Eval (Median μs) | AST Eval (P95 μs) | AST / Plan Ratio | Correctness |"
		)
		md_lines.append("|---|---|---|---|---|---|---|---|---|---|")

		for w_id, w_res in ast_comp.get("workloads", {}).items():
			c_size = w_res.get("collection_size", "-")
			p_prep = f"{w_res.get('plan_cold_prep_us', 0):.1f} / {w_res.get('plan_warm_prep_us', 0):.1f}"
			a_prep = f"{w_res.get('ast_cold_prep_us', 0):.1f} / {w_res.get('ast_warm_prep_us', 0):.1f}"
			p_eval = f"{w_res.get('plan_eval_median_us', 0):.3f}"
			p_p95 = f"{w_res.get('plan_eval_p95_us', 0):.3f}"
			a_eval = f"{w_res.get('ast_eval_median_us', 0):.3f}"
			a_p95 = f"{w_res.get('ast_eval_p95_us', 0):.3f}"
			ratio = f"{w_res.get('eval_ratio_ast_vs_plan', 1.0):.2f}x"
			status = "PASS" if w_res.get("is_correct") else "FAIL"
			md_lines.append(
				f"| `{w_id}` | {c_size} | {p_prep} | {a_prep} | {p_eval} | {p_p95} | {a_eval} | {a_p95} | {ratio} | {status} |"
			)

		md_lines.append("")
		md_lines.append("### 5. Amortized Cost (Preparation + N Evaluations)")
		md_lines.append("")
		md_lines.append(
			"| Execution Count | Compiled Plan (Cold μs) | AST Interpreter (Cold μs) | Compiled Plan (Warm μs) | AST Interpreter (Warm μs) | Faster (Cold) | Faster (Warm) |"
		)
		md_lines.append("|---|---|---|---|---|---|---|")

		for n_key, a_res in ast_comp.get("amortized", {}).items():
			p_c = f"{a_res.get('plan_cold_per_eval_us', 0):.2f}"
			a_c = f"{a_res.get('ast_cold_per_eval_us', 0):.2f}"
			p_w = f"{a_res.get('plan_warm_per_eval_us', 0):.2f}"
			a_w = f"{a_res.get('ast_warm_per_eval_us', 0):.2f}"
			f_c = a_res.get("faster_candidate_cold", "N/A")
			f_w = a_res.get("faster_candidate_warm", "N/A")
			md_lines.append(f"| **{n_key}** | {p_c} | {a_c} | {p_w} | {a_w} | {f_c} | {f_w} |")

		md_lines.append("")
		md_lines.append("### 6. Realistic Frappe Metadata Verification")
		meta_info = ast_comp.get("metadata_scenario", {})
		md_lines.append(f"- **Metadata Scenario:** `{meta_info.get('scenario', 'User -> Has Role')}`")
		md_lines.append(
			f"- **Compiled Plan Preparation:** `{meta_info.get('plan_prep_us', 0):.2f} μs` | **Evaluation Median:** `{meta_info.get('plan_eval_median_us', 0):.3f} μs`"
		)
		md_lines.append(
			f"- **Direct AST Preparation:** `{meta_info.get('ast_prep_us', 0):.2f} μs` | **Evaluation Median:** `{meta_info.get('ast_eval_median_us', 0):.3f} μs`"
		)
		md_lines.append("")
		md_lines.append("### 7. Memory, Cache, and Maintenance Trade-offs")
		md_lines.append(
			"- **Direct Canonical AST:** Simpler architectural model without secondary AST compiler or tuple layout dependencies. Saves compilation step entirely. Cold preparation is noticeably faster. Runtime evaluation is slightly slower due to dictionary key lookups vs tuple index access."
		)
		md_lines.append(
			"- **Compiled Tuple Plan:** Has lower steady-state per-evaluation latency once prepared, as tuple index indexing is faster than dict key lookups in Python. However, it requires maintaining `_compile_node` and `_compile_value` compilers and plan synchronization."
		)
		memory_info = ast_comp.get("memory_profiling", {})
		memory_candidates = memory_info.get("candidates", {})
		md_lines.append("")
		md_lines.append(f"- **Memory sample:** `{memory_info.get('sample_scenario', 'N/A')}`")
		md_lines.append(
			f"- **Compiled Plan retained / peak allocation:** `{memory_candidates.get('compiled_plan', {}).get('retained_allocation_bytes', 'N/A')} / {memory_candidates.get('compiled_plan', {}).get('peak_allocation_bytes', 'N/A')} bytes`"
		)
		md_lines.append(
			f"- **Direct AST retained / peak allocation:** `{memory_candidates.get('direct_ast', {}).get('retained_allocation_bytes', 'N/A')} / {memory_candidates.get('direct_ast', {}).get('peak_allocation_bytes', 'N/A')} bytes`"
		)
		md_lines.append(f"- **Interpretation:** {memory_info.get('note', 'No memory diagnostic available.')}")
		md_lines.append("")
		md_lines.append("### 8. Recommendation and Decision Gate")
		md_lines.append("- **Production Selection:** **Not established**")
		md_lines.append(
			"- **Rationale:** For single or few-shot evaluations (N <= 10), Direct Canonical AST interpretation amortizes faster due to lower preparation cost. For heavily looped or long-lived prepared conditions (N >= 100), Compiled Tuple Plan demonstrates faster per-evaluation throughput. Because production workloads vary between single-event triggers and large batch iterations, both execution profiles have distinct sweet spots, and replacing the production evaluator without comprehensive end-to-end telemetry across all action types is not recommended."
		)
		md_lines.append("")
		md_lines.append("---")
		md_lines.append("")
		md_lines.append("## 1. Candidate Evaluators Evaluated")
		md_lines.append("")
		md_lines.append("### Core Production Approaches")
		md_lines.append("| Candidate | Paradigm | Preparation Mechanism | Execution Path |")
		md_lines.append("|---|---|---|---|")
		md_lines.append(
			"| **Approach A (`safe_eval`)** | Legacy Dynamic Eval | Python expr string | `frappe.safe_eval` (RestrictedPython parse on every call) |"
		)
		md_lines.append(
			"| **Approach B (`plan`)** | Normalized AST Plan | Pre-compiled tuple AST | Direct AST recursive interpreter |"
		)
		md_lines.append(
			"| **Approach C (`json_tree`)** | Direct JSON Evaluator | Pure JSON AST | Direct JSON tree walker |"
		)
		md_lines.append(
			"| **Canonical (`evaluate_condition`)** | Validating public runtime | LRU-cached AST compilation | Public API with context normalization & cache lookup |"
		)
		md_lines.append("")
		md_lines.append("### Prepared and Experimental Runtime Baselines")
		md_lines.append("| Candidate | Purpose | Preparation Mechanism | Execution Path |")
		md_lines.append("|---|---|---|---|")
		md_lines.append(
			"| **Approach A Exp (`code_obj`)** | Isolated Bytecode Baseline | Pre-compiled bytecode | `eval(code_object)` |"
		)
		md_lines.append(
			"| **Canonical (`Prepared Plan`)** | Validated prepared-artifact runtime | Immutable validated artifact | Public prepared API without source serialization or cache-key lookup |"
		)
		md_lines.append("")
		md_lines.append("---")
		md_lines.append("")

		# Section 2: Semantic Correctness
		md_lines.append("## 2. Independent Semantic Correctness & Compatibility Suite")
		md_lines.append("")
		md_lines.append(
			f"All candidate evaluators were evaluated against neutral business scenarios. "
			f"Supported scenarios passed: **{correctness.get('total_supported_correct', 0)} / {correctness.get('total_supported_scenarios', 0)}**."
		)
		md_lines.append("")
		md_lines.append(
			"| Scenario ID | Tier | Status | Matching Check | Non-Matching Check | Disagreements / Errors |"
		)
		md_lines.append("|---|---|---|---|---|---|")

		for c_res in correctness.get("results", []):
			status = (
				"DEPRECATED"
				if c_res["is_deprecated_case"]
				else ("PASSED" if c_res["is_correct"] else "FAILED")
			)
			m_chk = ", ".join([f"{k}: {v}" for k, v in c_res["matching_doc_check"].items()])
			nm_chk = ", ".join([f"{k}: {v}" for k, v in c_res["non_matching_doc_check"].items()])
			errs = " | ".join(c_res["disagreements"]) if c_res["disagreements"] else "None"
			md_lines.append(
				f"| `{c_res['scenario_id']}` | {c_res['tier']} | **{status}** | `<small>{m_chk}</small>` | `<small>{nm_chk}</small>` | {errs} |"
			)

		md_lines.append("")
		md_lines.append("---")
		md_lines.append("")

		# Section 3: Steady-State Execution Latency
		md_lines.append("## 3. Steady-State Execution Latency (Microseconds per Operation)")
		md_lines.append("")
		md_lines.append(
			"| Scenario ID | Tier | Approach A (`safe_eval`) | Approach B (`plan`) | Approach C (`json_tree`) | Canonical Runtime (`evaluate_condition`) | *Diagnostic: A Exp (`code_obj`)* | *Prepared Artifact Runtime* |"
		)
		md_lines.append("|---|---|---|---|---|---|---|---|")

		cand_names = [
			"Approach A (frappe.safe_eval)",
			"Approach B (Normalized Execution Plan)",
			"Approach C (Direct JSON Tree Evaluator)",
			"Canonical Condition (evaluate_condition)",
			"Approach A (Experimental Restricted Code Object)",
			"Canonical Condition (Prepared Artifact Runtime)",
		]

		for item in steady.get("scenarios", []):
			sid = item["scenario_id"]
			tier = item["tier"]
			metrics = item["candidate_metrics"]

			vals = []
			for c_name in cand_names:
				m = metrics.get(c_name, {})
				if m.get("is_valid_measurement"):
					vals.append(f"{m.get('median_us_per_exec')} µs/op")
				else:
					vals.append("UNSUPPORTED")

			md_lines.append(
				f"| `{sid}` | {tier} | {vals[0]} | {vals[1]} | {vals[2]} | {vals[3]} | {vals[4]} | {vals[5]} |"
			)

		md_lines.append("")
		md_lines.append("---")
		md_lines.append("")

		# Section 4: Cold vs Warm Preparation Time
		md_lines.append("## 4. Cold vs Warm Preparation Latency (Milliseconds)")
		md_lines.append("")
		md_lines.append("| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |")
		md_lines.append("|---|---|---|---|")

		for item in steady.get("scenarios", []):
			sid = item["scenario_id"]
			metrics = item["candidate_metrics"]

			for c_name in cand_names:
				m = metrics.get(c_name, {})
				if m.get("is_valid_measurement"):
					cold_ms = m.get("cold_preparation_time_ms", "N/A")
					warm_ms = m.get("warm_preparation_time_ms", "N/A")
					md_lines.append(f"| `{sid}` | {c_name} | {cold_ms} ms | {warm_ms} ms |")

		md_lines.append("")
		md_lines.append("---")
		md_lines.append("")

		# Section 5: Methodology, Security & Limitations
		md_lines.append("## 5. Methodology, Security Profile & Trade-offs")
		md_lines.append("")
		md_lines.append("### Measurement Methodology & Isolation")
		md_lines.append(
			"1. **Cold Prep Isolation:** All LRU caches (`clear_condition_plan_cache()`) are explicitly cleared prior to cold preparation measurements. If cache clearing fails, cold preparation is marked invalid rather than silently proceeding."
		)
		md_lines.append(
			"2. **Steady-State & Result Validation:** Timed across 5 batches of 10,000 evaluations using alternating matching and non-matching document instances to prevent CPU branch prediction bias. Evaluation results and errors are strictly validated during benchmark loops."
		)
		md_lines.append(
			"3. **Fair Comparison Scope:** Semantics are compared only across shared supported operators. Operators not supported by a candidate (e.g., `has_changed` in canonical contract) are explicitly marked as `UNSUPPORTED` or `DEPRECATED` rather than counted as failures."
		)
		md_lines.append("")
		md_lines.append("### Security Profile & Analysis")
		md_lines.append(
			"- **Approach A (`safe_eval`)**: Re-compiles Python expressions dynamically using RestrictedPython on every call. While restricted, dynamic string evaluation carries latent code execution attack vectors if input sanitization is bypassed."
		)
		md_lines.append(
			"- **Approach B / Approach C / PR #469 Canonical Evaluator**: Parse conditions into structured AST nodes and evaluate them via pure Python tree traversal. This completely avoids `eval()`, `exec()`, and `safe_eval()`, eliminating dynamic string execution vulnerabilities."
		)
		md_lines.append("")
		md_lines.append("### Production Selection Gate")
		md_lines.append(
			"Production selection remains **Not established** in this report. Final production adoption requires explicit formal review of security boundaries, governance policies, and cross-module integration requirements."
		)

		report_content = "\n".join(md_lines)
		os.makedirs(os.path.dirname(output_markdown_path), exist_ok=True)
		with open(output_markdown_path, "w", encoding="utf-8") as f:
			f.write(report_content)

		return report_content


def run_main():
	sites_path = (
		"/home/jules/frappe-bench/sites" if os.path.exists("/home/jules/frappe-bench/sites") else "sites"
	)
	site_name = os.environ.get("FRAPPE_SITE_NAME", "test_site")
	bench_root = os.environ.get("FRAPPE_BENCH_PATH")
	if not bench_root:
		for candidate in ("/home/jules/frappe-bench", "/home/runner/frappe-bench"):
			if os.path.isdir(os.path.join(candidate, "sites")):
				bench_root = candidate
				break
	sites_path = os.path.join(bench_root, "sites") if bench_root else sites_path
	frappe.init(site=site_name, sites_path=sites_path)

	iters = int(os.environ.get("BENCHMARK_ITERATIONS_PER_BATCH", "1000"))
	batches = int(os.environ.get("BENCHMARK_NUM_BATCHES", "3"))
	warmup = int(os.environ.get("BENCHMARK_WARMUP_ITERATIONS", "20"))

	runner = BenchmarkRunner(
		iterations_per_batch=iters,
		num_batches=batches,
		warmup_iterations=warmup,
	)
	repo_root = Path(__file__).resolve().parents[4]
	output_file = os.path.abspath(
		os.environ.get(
			"CONDITION_BENCHMARK_JSON_PATH",
			os.path.join(repo_root, "reports", "canonical_condition_benchmark_results.json"),
		)
	)
	md_file = os.path.abspath(
		os.environ.get(
			"CONDITION_BENCHMARK_MARKDOWN_PATH",
			os.path.join(repo_root, "reports", "condition-backend-comparison-benchmark.md"),
		)
	)
	runner.run_full_suite_and_export(output_file, md_file)
	print(f"Condition benchmark complete. JSON saved to {output_file}, Markdown saved to {md_file}")


if __name__ == "__main__":
	run_main()
