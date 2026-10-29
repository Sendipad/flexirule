# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import os
import platform
import statistics
import subprocess
import time
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
from flexirule.ruleflow.tests.condition_benchmark.comparison_api import (
	BaseConditionCandidate,
)
from flexirule.ruleflow.tests.condition_benchmark.fixtures import get_neutral_scenarios


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
			["git", "status", "--porcelain"],
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
			provenance_note = "Git commit and clean working tree were verified from the benchmark repository root."
	except (OSError, subprocess.CalledProcessError):
		is_dirty = True
		provenance_note = "Working-tree status could not be verified; the benchmark is not clean-provenance eligible."

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

		self.candidates: list[BaseConditionCandidate] = [
			self.cand_a,
			self.cand_a_exp,
			self.cand_b,
			self.cand_c,
			self.cand_canon_runtime,
			self.cand_canon_plan,
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

	def run_full_suite_and_export(
		self,
		output_filepath: str = "reports/canonical_condition_benchmark_results.json",
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

		git_meta = _get_git_metadata()

		env_info = {
			"python_version": platform.python_version(),
			"platform": platform.platform(),
			"frappe_version": getattr(frappe, "__version__", "15.123.1"),
			"flexirule_version": "1.0.0-beta.3",
			"timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
			"benchmark_source_branch": git_meta["branch"],
			"benchmark_source_commit": git_meta["commit"],
			"is_working_tree_dirty": git_meta["is_dirty"],
			"provenance_note": git_meta["provenance_note"],
		}

		full_payload = {
			"benchmark_protocol_version": 3,
			"benchmark_target": "Condition Backend Comparison Benchmark",
			"production_selection_status": "Not established",
			"production_gate_reason": (
				"Production selection remains Not established until explicit correctness, "
				"security, and performance criteria gates pass."
			),
			"measurement_protocol": (
				"Cold prep measured after cache clear; warm prep measured on primed instance; "
				"steady-state timed in 5 batches of alternating docs; amortized cost incorporates cold prep."
			),
			"environment": env_info,
			"correctness_suite": correctness_summary,
			"steady_state_benchmark": steady_state_summary,
			"amortized_benchmark": amortized_summary,
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
	runner = BenchmarkRunner(iterations_per_batch=10000, num_batches=5)
	output_file = os.path.abspath(
		os.environ.get(
			"CONDITION_BENCHMARK_JSON_PATH",
			"reports/canonical_condition_benchmark_results.json",
		)
	)
	md_file = os.path.abspath(
		os.environ.get(
			"CONDITION_BENCHMARK_MARKDOWN_PATH",
			"reports/condition-backend-comparison-benchmark.md",
		)
	)
	runner.run_full_suite_and_export(output_file, md_file)
	print(f"Condition benchmark complete. JSON saved to {output_file}, Markdown saved to {md_file}")


if __name__ == "__main__":
	run_main()
