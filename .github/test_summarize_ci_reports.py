# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Regression tests for CI report generation, including passing and failing Frappe test cases."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from summarize_ci_reports import main


class TestCIReportSummarizer(unittest.TestCase):
	def test_passing_junit_case_marks_ci_passed(self):
		with tempfile.TemporaryDirectory() as temp_dir:
			workspace = Path(temp_dir)
			report_root = workspace / "artifacts" / "ci-reports"
			test_results = report_root / "test-results"
			test_results.mkdir(parents=True)
			(test_results / "server-tests.xml").write_text(
				'<?xml version="1.0" encoding="UTF-8"?>'
				'<testsuites><testsuite tests="2" failures="0" errors="0">'
				'<testcase classname="test_sample" name="test_one"/>'
				'<testcase classname="test_sample" name="test_two"/>'
				'</testsuite></testsuites>',
				encoding="utf-8",
			)
			(test_results / "server-tests.exitcode").write_text("0\n", encoding="utf-8")
			summary_path = workspace / "github-step-summary.md"
			environment = {
				"GITHUB_WORKSPACE": str(workspace),
				"GITHUB_STEP_SUMMARY": str(summary_path),
				"TEST_STEP_OUTCOME": "success",
				"CONDITION_RUNTIME_ENABLED": "false",
				"BENCHMARK_STEP_OUTCOME": "skipped",
				"MIGRATE_STEP_OUTCOME": "success",
				"EXPECTED_BENCHMARK_COMMIT": "",
			}

			with patch.dict(os.environ, environment, clear=False):
				self.assertEqual(main(), 0)

			passed_marker = report_root / "ci-summary-passed"
			self.assertTrue(passed_marker.exists())
			summary = summary_path.read_text(encoding="utf-8")
			self.assertIn("JUnit totals: 2 passed, 0 failures, 0 errors, 0 skipped; 2 cases.", summary)

	def test_failing_junit_case_is_reported_and_marks_ci_failed(self):
		with tempfile.TemporaryDirectory() as temp_dir:
			workspace = Path(temp_dir)
			report_root = workspace / "artifacts" / "ci-reports"
			test_results = report_root / "test-results"
			test_results.mkdir(parents=True)
			(test_results / "server-tests.xml").write_text(
				'<?xml version="1.0" encoding="UTF-8"?>'
				'<testsuites><testsuite tests="1" failures="1" errors="0">'
				'<testcase classname="test_sample" name="test_expected_failure">'
				'<failure message="expected failure">AssertionError: sample traceback</failure>'
				'</testcase></testsuite></testsuites>',
				encoding="utf-8",
			)
			(test_results / "server-tests.exitcode").write_text("1\n", encoding="utf-8")
			summary_path = workspace / "github-step-summary.md"
			environment = {
				"GITHUB_WORKSPACE": str(workspace),
				"GITHUB_STEP_SUMMARY": str(summary_path),
				"TEST_STEP_OUTCOME": "success",
				"CONDITION_RUNTIME_ENABLED": "false",
				"BENCHMARK_STEP_OUTCOME": "skipped",
				"MIGRATE_STEP_OUTCOME": "success",
				"EXPECTED_BENCHMARK_COMMIT": "",
			}

			with patch.dict(os.environ, environment, clear=False):
				self.assertEqual(main(), 0)

			failure_marker = report_root / "ci-summary-failed"
			self.assertTrue(failure_marker.exists())
			self.assertIn("Frappe tests had 1 failure(s)", failure_marker.read_text(encoding="utf-8"))
			summary = summary_path.read_text(encoding="utf-8")
			self.assertIn("test_sample.test_expected_failure", summary)
			self.assertIn("AssertionError: sample traceback", summary)
			self.assertIn("Original Frappe test command exit code: 1", summary)

	def test_missing_junit_report_is_not_treated_as_pass(self):
		with tempfile.TemporaryDirectory() as temp_dir:
			workspace = Path(temp_dir)
			report_root = workspace / "artifacts" / "ci-reports"
			(report_root / "test-results").mkdir(parents=True)
			summary_path = workspace / "github-step-summary.md"
			environment = {
				"GITHUB_WORKSPACE": str(workspace),
				"GITHUB_STEP_SUMMARY": str(summary_path),
				"TEST_STEP_OUTCOME": "success",
				"CONDITION_RUNTIME_ENABLED": "false",
				"BENCHMARK_STEP_OUTCOME": "skipped",
				"MIGRATE_STEP_OUTCOME": "success",
				"EXPECTED_BENCHMARK_COMMIT": "",
			}

			with patch.dict(os.environ, environment, clear=False):
				self.assertEqual(main(), 0)

			self.assertTrue((report_root / "ci-summary-failed").exists())
			self.assertIn(
				"without producing the configured JUnit XML report",
				summary_path.read_text(encoding="utf-8"),
			)

	def test_invalid_condition_metadata_measurement_fails_ci_report(self):
		with tempfile.TemporaryDirectory() as temp_dir:
			workspace = Path(temp_dir)
			report_root = workspace / "artifacts" / "ci-reports"
			test_results = report_root / "test-results"
			bench_dir = report_root / "condition-runtime"
			test_results.mkdir(parents=True)
			bench_dir.mkdir(parents=True)
			(test_results / "server-tests.xml").write_text(
				'<?xml version="1.0" encoding="UTF-8"?>'
				'<testsuites><testsuite tests="1" failures="0" errors="0">'
				'<testcase classname="test_sample" name="test_one"/>'
				'</testsuite></testsuites>',
				encoding="utf-8",
			)
			(test_results / "server-tests.exitcode").write_text("0\n", encoding="utf-8")
			(bench_dir / "benchmark.exitcode").write_text("0\n", encoding="utf-8")
			(bench_dir / "condition-backend-comparison-benchmark.md").write_text(
				"# Benchmark report\n", encoding="utf-8"
			)
			payload = {
				"correctness_suite": {
					"all_supported_correct": True,
					"total_supported_correct": 1,
					"total_supported_scenarios": 1,
				},
				"environment": {
					"benchmark_source_commit": "merge-commit",
					"benchmark_pr_head_commit": "pull-request-head",
					"is_working_tree_dirty": True,
					"working_tree_changes": ["flexirule/public/dist/generated.js"],
				},
				"canonical_ast_vs_plan_comparison": {
					"workloads": {
						"simple": {"is_valid_measurement": True, "is_correct": True},
					},
					"metadata_scenario": {
						"is_valid_measurement": False,
						"reason": "Frappe metadata cache is not bound",
					},
				},
				"steady_state_benchmark": {"scenarios": []},
			}
			(bench_dir / "canonical_condition_benchmark_results.json").write_text(
				json.dumps(payload), encoding="utf-8"
			)
			summary_path = workspace / "github-step-summary.md"
			environment = {
				"GITHUB_WORKSPACE": str(workspace),
				"GITHUB_STEP_SUMMARY": str(summary_path),
				"TEST_STEP_OUTCOME": "success",
				"CONDITION_RUNTIME_ENABLED": "true",
				"BENCHMARK_STEP_OUTCOME": "success",
				"MIGRATE_STEP_OUTCOME": "success",
				"EXPECTED_BENCHMARK_COMMIT": "merge-commit",
				"CONDITION_BENCHMARK_PR_HEAD_SHA": "pull-request-head",
			}

			with patch.dict(os.environ, environment, clear=False):
				self.assertEqual(main(), 0)

			failure_marker = report_root / "ci-summary-failed"
			self.assertTrue(failure_marker.exists())
			failure_text = failure_marker.read_text(encoding="utf-8")
			self.assertIn("Frappe metadata scenario invalid", failure_text)
			summary = summary_path.read_text(encoding="utf-8")
			self.assertIn("flexirule/public/dist/generated.js", summary)
			self.assertIn("PR head commit: pull-request-head", summary)


if __name__ == "__main__":
	unittest.main()
