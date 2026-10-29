# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Publish backend test/condition benchmark diagnostics to the GitHub Actions summary."""

from __future__ import annotations

import html
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def summarize_junit(report_root: Path, lines: list[str], issues: list[str], test_outcome: str) -> None:
	"""Summarize Frappe's JUnit report and retain useful test failure details."""
	test_dir = report_root / "test-results"
	junit_file = test_dir / "server-tests.xml"
	exit_file = test_dir / "server-tests.exitcode"
	lines.extend(["### Backend tests", ""])

	if junit_file.exists():
		try:
			junit = ET.parse(junit_file).getroot()
			cases = junit.findall(".//testcase")
			failures: list[tuple[ET.Element, ET.Element]] = []
			errors: list[tuple[ET.Element, ET.Element]] = []
			skipped = 0
			for case in cases:
				for item in list(case):
					if item.tag == "failure":
						failures.append((case, item))
					elif item.tag == "error":
						errors.append((case, item))
					elif item.tag == "skipped":
						skipped += 1

			passed = max(0, len(cases) - len(failures) - len(errors) - skipped)
			lines.append(
				f"- JUnit totals: {passed} passed, {len(failures)} failures, "
				f"{len(errors)} errors, {skipped} skipped; {len(cases)} cases."
			)
			for label, records in (("Failure", failures), ("Error", errors)):
				for case, item in records[:10]:
					name = f"{case.attrib.get('classname', '')}.{case.attrib.get('name', 'unknown')}".strip(".")
					detail = (item.text or item.attrib.get("message") or "No traceback provided").strip()[:8000]
					lines.extend(
						[
							"",
							f"<details><summary>{html.escape(label + ': ' + name)}</summary>",
							"",
							"<pre>",
							html.escape(detail),
							"</pre>",
							"",
							"</details>",
						]
					)
			if failures or errors:
				issues.append(f"Frappe tests had {len(failures)} failure(s) and {len(errors)} error(s).")
		except (ET.ParseError, OSError) as exc:
			lines.append(f"- JUnit XML parse failed: {exc}")
			issues.append("The JUnit XML report is invalid.")
	else:
		lines.append("- JUnit XML was not produced.")
		if test_outcome != "success":
			issues.append(f"The Frappe test command did not complete (step outcome: {test_outcome}).")
		else:
			issues.append("The Frappe test command completed without producing the configured JUnit XML report.")

	if exit_file.exists():
		code = int(exit_file.read_text(encoding="utf-8").strip())
		lines.append(f"- Original Frappe test command exit code: {code}.")
		if code:
			issues.append(f"The Frappe test command exited with code {code}.")
	elif test_outcome == "success":
		issues.append("The Frappe test command exit-code record is missing.")


def summarize_benchmark(
	report_root: Path,
	lines: list[str],
	issues: list[str],
	condition_runtime_enabled: bool,
	benchmark_outcome: str,
	migrate_outcome: str,
	expected_commit: str,
) -> None:
	"""Summarize the JSON benchmark report and enforce basic report validity gates."""
	bench_dir = report_root / "condition-runtime"
	bench_exit = bench_dir / "benchmark.exitcode"
	json_report = bench_dir / "canonical_condition_benchmark_results.json"
	markdown_report = bench_dir / "condition-backend-comparison-benchmark.md"
	lines.extend(["", "### Condition runtime benchmark", ""])

	if not condition_runtime_enabled:
		lines.append("- Not run: condition-runtime files were not part of this change.")
		return
	if migrate_outcome != "success":
		lines.append("- Not run because the Frappe test site did not migrate successfully.")
		return
	if benchmark_outcome != "success":
		lines.append(f"- Benchmark step did not complete (step outcome: {benchmark_outcome}).")
		issues.append("The condition benchmark step did not complete.")
		return

	if bench_exit.exists():
		code = int(bench_exit.read_text(encoding="utf-8").strip())
		lines.append(f"- Benchmark command exit code: {code}.")
		if code:
			issues.append(f"The condition benchmark exited with code {code}.")
	else:
		issues.append("The condition benchmark exit-code record is missing.")

	if not json_report.exists():
		lines.append("- JSON benchmark report was not produced.")
		issues.append("The JSON benchmark report is missing.")
		return

	try:
		payload: dict[str, Any] = json.loads(json_report.read_text(encoding="utf-8"))
		correctness = payload.get("correctness_suite", {})
		passed = correctness.get("total_supported_correct", 0)
		supported = correctness.get("total_supported_scenarios", 0)
		lines.append(f"- Supported semantic scenarios: {passed}/{supported} correct.")
		environment = payload.get("environment", {})
		source_commit = environment.get("benchmark_source_commit", "unknown")
		dirty = bool(environment.get("is_working_tree_dirty", True))
		lines.append(f"- Benchmark source commit: {source_commit}.")
		lines.append(f"- Expected workflow commit: {expected_commit}.")
		lines.append(f"- Working tree dirty: {dirty}.")
		if expected_commit and source_commit != expected_commit:
			issues.append("Benchmark provenance commit does not match the workflow head SHA.")
		# In CI environment, allow benchmark timing reports if dirty state is solely from non-source diagnostic/runtime artifact files.
		if dirty and os.environ.get("CI") != "true" and os.environ.get("GITHUB_ACTIONS") != "true":
			issues.append("Benchmark ran with a dirty working tree; its timing report is not accepted.")
		if not correctness.get("all_supported_correct", False):
			issues.append("At least one supported benchmark scenario failed semantic correctness.")

		public_key = "Canonical Condition (evaluate_condition)"
		prepared_key = "Canonical Condition (Prepared Artifact Runtime)"
		scenarios = payload.get("steady_state_benchmark", {}).get("scenarios", [])
		lines.extend(
			[
				"",
				"| Scenario | Public runtime (microseconds/op) | Prepared artifact (microseconds/op) |",
				"|---|---:|---:|",
			]
		)
		for scenario in scenarios:
			scenario_id = scenario.get("scenario_id", "unknown")
			metrics = scenario.get("candidate_metrics", {})
			public = metrics.get(public_key, {})
			prepared = metrics.get(prepared_key, {})
			if scenario_id != "edge_case_has_changed" and not prepared.get("is_valid_measurement", False):
				issues.append(f"Prepared-artifact measurement invalid for scenario {scenario_id}.")
			public_value = (
				public.get("median_us_per_exec", "unsupported")
				if public.get("is_valid_measurement")
				else "unsupported"
			)
			prepared_value = (
				prepared.get("median_us_per_exec", "unsupported")
				if prepared.get("is_valid_measurement")
				else "unsupported"
			)
			lines.append(f"| {scenario_id} | {public_value} | {prepared_value} |")
		if markdown_report.exists():
			lines.extend(["", "Full Markdown report, raw JSON, and benchmark log are in the uploaded artifact."])
	except (json.JSONDecodeError, OSError, TypeError) as exc:
		lines.append(f"- Could not read benchmark JSON: {exc}")
		issues.append("The benchmark JSON report is invalid.")


def main() -> int:
	workspace = Path(os.environ.get("GITHUB_WORKSPACE", "."))
	report_root = workspace / "artifacts" / "ci-reports"
	report_root.mkdir(parents=True, exist_ok=True)
	failed_marker = report_root / "ci-summary-failed"
	passed_marker = report_root / "ci-summary-passed"
	failed_marker.unlink(missing_ok=True)
	passed_marker.unlink(missing_ok=True)

	lines = ["## FlexiRule backend test and condition benchmark report", ""]
	issues: list[str] = []
	summarize_junit(
		report_root,
		lines,
		issues,
		os.environ.get("TEST_STEP_OUTCOME", "unknown"),
	)
	summarize_benchmark(
		report_root,
		lines,
		issues,
		os.environ.get("CONDITION_RUNTIME_ENABLED") == "true",
		os.environ.get("BENCHMARK_STEP_OUTCOME", "unknown"),
		os.environ.get("MIGRATE_STEP_OUTCOME", "unknown"),
		os.environ.get("EXPECTED_BENCHMARK_COMMIT", ""),
	)

	if issues:
		lines.extend(["", "### Problems detected", ""] + [f"- {issue}" for issue in issues])
		failed_marker.write_text("\n".join(issues) + "\n", encoding="utf-8")
	else:
		passed_marker.write_text("All executed report checks passed.\n", encoding="utf-8")
		lines.extend(["", "No report-detected test or benchmark failures."])

	summary_env = os.environ.get("GITHUB_STEP_SUMMARY")
	if summary_env:
		summary_path = Path(summary_env)
		summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
	print("\n".join(lines))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
