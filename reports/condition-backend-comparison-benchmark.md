# FlexiRule — Condition Backend Comparison Benchmark Report

**Date:** 2026-10-20
**Repository:** [Sendipad/flexirule](https://github.com/Sendipad/flexirule)
**Branch:** `feat/condition-benchmark`
**Report Location:** `/home/jules/frappe-bench/apps/flexirule/reports/condition-backend-comparison-benchmark.md`
**Benchmark Protocol:** v2
**Measurement Protocol:** repeated medians, rotating order, alternating matching/non-matching documents, correctness gate
**Raw Results Data:** `reports/condition_benchmark_results.json`

---

## Executive Summary

This report documents the architectural investigation, empirical runtime probe, correctness test suite, and high-precision performance benchmarks comparing two architectural candidates for evaluating visual JSON rule conditions in FlexiRule:

- **Approach A — Generated Python Expression (`frappe.safe_eval`; restricted compilation on every evaluation) (`Approach A (frappe.safe_eval)`):** Evaluating a Python expression string generated from a condition tree using installed Frappe v15 restricted evaluation (`frappe.safe_eval`). Includes an isolated experimental diagnostic (`Approach A (Experimental Restricted Code Object)`) for evaluating precompiled RestrictedPython code objects.
- **Approach B — Prebuilt Normalized Execution Plan (`Approach B (Normalized Execution Plan)`):** Evaluating a typed, validated execution plan using a pure evaluator and comparator without Python compilation or AST parsing during execution.

### Summary Statistics and Findings

1. **`frappe.safe_eval` Overhead:** Installed Frappe v15 `frappe.safe_eval` performs `unicodedata.normalize()`, `ast.parse()`, AST node walking (`_validate_safe_eval_syntax`), and RestrictedPython AST transformation / compilation on **every single invocation**. It implements **no caching** of compiled bytecode objects.
2. **`has_changed` Operator Contract Divergence:** In `ConditionCompiler`, the `has_changed` operator is deprecated and returns `True` for backward compatibility, while candidate evaluators evaluate dynamic field changes against `_doc_before_save`. Under the semantic correctness gate, `edge_case_has_changed` exhibits contract divergence and is excluded from timing measurements.
2. **Semantic Correctness Gate Status:** **FAILED (Disagreements Detected)**. Total Fixtures Tested: 13, Agreed: 12.
3. **Evaluations Completed:** **2,400,000** total error-free evaluations were completed during this benchmark run.

---

## 1. Environment and Reproducibility

| Key | Value |
|---|---|
| Python Version | 3.12.13 |
| Platform | Linux-6.8.0-x86_64-with-glibc2.39 |
| Frappe Framework | 15.123.1 |
| FlexiRule Version | 1.0.0-beta.3 |
| Benchmark Execution UTC | 2026-10-20T23:18:35Z |
| Benchmark Command | `PYTHONPATH=. /home/jules/frappe-bench/env/bin/python -m flexirule.ruleflow.tests.condition_benchmark.benchmark_runner` |

---

## 2. Correctness Test Suite Results

The correctness gate evaluates every candidate against matching and non-matching document contexts and verifies that all candidates agree with each other AND match the fixture's explicit expected results.

| Fixture ID | Complexity Tier | Status | Matching Check | Non-Matching Check | Errors |
|---|---|---|---|---|---|
| `tier1_simple_equality` | Tier 1 — Simple | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `tier2_typical_business_rule` | Tier 2 — Typical Business Rule | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `tier3_nested_and_or_groups` | Tier 3 — Nested Groups | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `tier4_deep_nested_complex` | Tier 4 — Deep Nested Complex | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `tier5_collection_child_records` | Tier 5 — Collection / Child Records | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `edge_case_is_set_null_empty` | Edge Case — Null / Empty | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `edge_case_link_tuple` | Edge Case — Link Tuple | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `edge_case_membership_in_not_in` | Edge Case — Membership | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `edge_case_contains_not_contains` | Edge Case — Substring | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `edge_case_collection_all_and_none` | Edge Case — Collection All/None | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `edge_case_length_gt_eq` | Edge Case — Length | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `edge_case_has_changed` | Edge Case — Field Change | **FAILED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |

---

## 3. Primary Prepared-Execution Benchmark Results

**Methodology:** Preparation time is the median of repeated samples and is excluded from primary execution timing. Each of 5 batches contains 10,000 evaluations. Matching and non-matching documents alternate, candidate order rotates across batches, and the timer covers the entire candidate.evaluate() call. Each table cell shows full-call latency, followed by the candidate-reported inner evaluator timer in parentheses.

| Fixture ID | Tier | Leaf / Depth | Approach A (`safe_eval`) | Approach A Exp (`code_obj`) | Approach B (`plan`) | Approach C (`json_tree`) | Speedup B vs Primary A | Speedup C vs Primary A | Speedup B vs C |
|---|---|---|---|---|---|---|---|---|---|
| `tier1_simple_equality` | Tier 1 — Simple | 1 / 1 | 185.557 µs/op (core 172.423 µs/op) | 10.046 µs/op (core 2.412 µs/op) | **4.048 µs/op (core 2.206 µs/op)** | 6.239 µs/op (core 4.249 µs/op) | **45.84x** | **29.74x** | **1.54x** |
| `tier2_typical_business_rule` | Tier 2 — Typical Business Rule | 3 / 1 | 410.963 µs/op (core 395.46 µs/op) | 11.844 µs/op (core 4.577 µs/op) | **6.16 µs/op (core 4.393 µs/op)** | 10.381 µs/op (core 8.413 µs/op) | **66.71x** | **39.59x** | **1.69x** |
| `tier3_nested_and_or_groups` | Tier 3 — Nested Groups | 4 / 2 | 552.817 µs/op (core 536.029 µs/op) | 11.92 µs/op (core 4.612 µs/op) | **6.567 µs/op (core 4.73 µs/op)** | 11.264 µs/op (core 9.321 µs/op) | **84.18x** | **49.08x** | **1.72x** |
| `tier4_deep_nested_complex` | Tier 4 — Deep Nested Complex | 8 / 3 | 1142.074 µs/op (core 1122.834 µs/op) | 15.818 µs/op (core 8.516 µs/op) | **10.028 µs/op (core 8.151 µs/op)** | 17.605 µs/op (core 15.442 µs/op) | **113.89x** | **64.87x** | **1.76x** |
| `tier5_collection_child_records` | Tier 5 — Collection / Child Records | 3 / 2 | 713.981 µs/op (core 695.799 µs/op) | 16.619 µs/op (core 8.948 µs/op) | **10.4 µs/op (core 8.494 µs/op)** | 16.903 µs/op (core 14.79 µs/op) | **68.65x** | **42.24x** | **1.63x** |
| `edge_case_is_set_null_empty` | Edge Case — Null / Empty | 1 / 1 | 308.871 µs/op (core 293.962 µs/op) | 11.238 µs/op (core 3.793 µs/op) | **3.145 µs/op (core 1.391 µs/op)** | 4.864 µs/op (core 3.013 µs/op) | **98.21x** | **63.5x** | **1.55x** |
| `edge_case_link_tuple` | Edge Case — Link Tuple | 1 / 1 | 242.573 µs/op (core 229.112 µs/op) | 11.629 µs/op (core 4.292 µs/op) | **5.334 µs/op (core 3.599 µs/op)** | 7.4 µs/op (core 5.542 µs/op) | **45.48x** | **32.78x** | **1.39x** |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 2 / 1 | 374.272 µs/op (core 358.785 µs/op) | 10.517 µs/op (core 3.101 µs/op) | **4.927 µs/op (core 3.145 µs/op)** | 7.704 µs/op (core 5.779 µs/op) | **75.96x** | **48.58x** | **1.56x** |
| `edge_case_contains_not_contains` | Edge Case — Substring | 2 / 1 | 577.245 µs/op (core 560.558 µs/op) | 14.857 µs/op (core 7.177 µs/op) | **5.815 µs/op (core 3.986 µs/op)** | 9.12 µs/op (core 7.154 µs/op) | **99.27x** | **63.29x** | **1.57x** |
| `edge_case_collection_all_and_none` | Edge Case — Collection All/None | 1 / 2 | 466.7 µs/op (core 450.021 µs/op) | 14.088 µs/op (core 6.637 µs/op) | **7.298 µs/op (core 5.423 µs/op)** | 10.925 µs/op (core 8.892 µs/op) | **63.95x** | **42.72x** | **1.5x** |
| `edge_case_length_gt_eq` | Edge Case — Length | 1 / 1 | 211.977 µs/op (core 198.949 µs/op) | 9.857 µs/op (core 2.581 µs/op) | **4.093 µs/op (core 2.315 µs/op)** | 6.048 µs/op (core 4.159 µs/op) | **51.79x** | **35.05x** | **1.48x** |
| `edge_case_has_changed` | Edge Case — Field Change | 1 / 1 | INVALID | INVALID | **INVALID** | INVALID | N/A | N/A | N/A |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 1 / 1 | 302.455 µs/op (core 288.191 µs/op) | 10.188 µs/op (core 2.962 µs/op) | **3.193 µs/op (core 1.445 µs/op)** | 4.834 µs/op (core 2.989 µs/op) | **94.72x** | **62.57x** | **1.51x** |

---

## 4. Preparation Timings

Preparation time measured separately outside the execution loop:

| Fixture ID | Approach A Prep (ms) | Approach B Prep (ms) | Approach C Prep (ms) |
|---|---|---|---|
| `tier1_simple_equality` | 0.0903 ms | **0.0152 ms** | 0.0016 ms |
| `tier2_typical_business_rule` | 0.2132 ms | **0.0287 ms** | 0.0018 ms |
| `tier3_nested_and_or_groups` | 0.2759 ms | **0.0335 ms** | 0.0017 ms |
| `tier4_deep_nested_complex` | 0.651 ms | **0.0528 ms** | 0.0019 ms |
| `tier5_collection_child_records` | 0.3302 ms | **0.0344 ms** | 0.0019 ms |
| `edge_case_is_set_null_empty` | 0.143 ms | **0.0155 ms** | 0.0016 ms |
| `edge_case_link_tuple` | 0.1335 ms | **0.0162 ms** | 0.0016 ms |
| `edge_case_membership_in_not_in` | 0.2048 ms | **0.0231 ms** | 0.0018 ms |
| `edge_case_contains_not_contains` | 0.2794 ms | **0.0232 ms** | 0.0018 ms |
| `edge_case_collection_all_and_none` | 0.2003 ms | **0.022 ms** | 0.0018 ms |
| `edge_case_length_gt_eq` | 0.1195 ms | **0.0173 ms** | 0.0017 ms |
| `edge_case_has_changed` | 0.0443 ms | **0.0118 ms** | 0.0015 ms |
| `edge_case_none_vs_missing_field` | 0.1508 ms | **0.016 ms** | 0.0017 ms |

---

## 5. Amortized Total Cost Measurements

Estimates one preparation plus N evaluations. Preparation time is the median of repeated samples; execution time is the median total duration across repeated N-evaluation batches. Fixtures that fail semantic parity are excluded. Core-only timing diagnostics are also retained in raw JSON.

$$\text{Total Amortized Cost} = \text{Preparation Time} + (N \times \text{Execution Time})$$

| Fixture ID | N Evaluations | Approach A Total Cost (ms) | Approach B Total Cost (ms) | Approach A Cost/Eval (µs) | Approach B Cost/Eval (µs) |
|---|---|---|---|---|---|
| `tier1_simple_equality` | N = 1 | 0.2865 ms | **0.0234 ms** | 286.459 µs | **23.433 µs** |
| `tier1_simple_equality` | N = 10 | 1.926 ms | **0.0603 ms** | 192.597 µs | **6.029 µs** |
| `tier1_simple_equality` | N = 100 | 17.5888 ms | **0.4327 ms** | 175.888 µs | **4.327 µs** |
| `tier1_simple_equality` | N = 1000 | 179.3593 ms | **4.0142 ms** | 179.359 µs | **4.014 µs** |
| `tier2_typical_business_rule` | N = 1 | 0.6438 ms | **0.0409 ms** | 643.821 µs | **40.944 µs** |
| `tier2_typical_business_rule` | N = 10 | 4.3186 ms | **0.0986 ms** | 431.857 µs | **9.86 µs** |
| `tier2_typical_business_rule` | N = 100 | 40.9663 ms | **0.6707 ms** | 409.663 µs | **6.707 µs** |
| `tier2_typical_business_rule` | N = 1000 | 408.3324 ms | **6.1788 ms** | 408.332 µs | **6.179 µs** |
| `tier3_nested_and_or_groups` | N = 1 | 0.8295 ms | **0.0482 ms** | 829.489 µs | **48.202 µs** |
| `tier3_nested_and_or_groups` | N = 10 | 5.63 ms | **0.1078 ms** | 562.996 µs | **10.78 µs** |
| `tier3_nested_and_or_groups` | N = 100 | 53.8284 ms | **0.6941 ms** | 538.284 µs | **6.941 µs** |
| `tier3_nested_and_or_groups` | N = 1000 | 539.6153 ms | **6.6092 ms** | 539.615 µs | **6.609 µs** |
| `tier4_deep_nested_complex` | N = 1 | 1.6793 ms | **0.0785 ms** | 1679.271 µs | **78.524 µs** |
| `tier4_deep_nested_complex` | N = 10 | 11.5811 ms | **0.1665 ms** | 1158.109 µs | **16.645 µs** |
| `tier4_deep_nested_complex` | N = 100 | 112.4252 ms | **1.1156 ms** | 1124.252 µs | **11.156 µs** |
| `tier4_deep_nested_complex` | N = 1000 | 1113.8012 ms | **10.1346 ms** | 1113.801 µs | **10.135 µs** |
| `tier5_collection_child_records` | N = 1 | 1.0403 ms | **0.0598 ms** | 1040.328 µs | **59.822 µs** |
| `tier5_collection_child_records` | N = 10 | 7.273 ms | **0.1515 ms** | 727.296 µs | **15.154 µs** |
| `tier5_collection_child_records` | N = 100 | 70.2426 ms | **1.111 ms** | 702.426 µs | **11.11 µs** |
| `tier5_collection_child_records` | N = 1000 | 699.8814 ms | **10.3194 ms** | 699.881 µs | **10.319 µs** |
| `edge_case_is_set_null_empty` | N = 1 | 0.4635 ms | **0.0224 ms** | 463.458 µs | **22.433 µs** |
| `edge_case_is_set_null_empty` | N = 10 | 3.1878 ms | **0.0518 ms** | 318.78 µs | **5.177 µs** |
| `edge_case_is_set_null_empty` | N = 100 | 30.2993 ms | **0.3089 ms** | 302.993 µs | **3.089 µs** |
| `edge_case_is_set_null_empty` | N = 1000 | 301.97 ms | **3.1444 ms** | 301.97 µs | **3.144 µs** |
| `edge_case_link_tuple` | N = 1 | 0.3778 ms | **0.0272 ms** | 377.759 µs | **27.232 µs** |
| `edge_case_link_tuple` | N = 10 | 2.5951 ms | **0.0755 ms** | 259.514 µs | **7.547 µs** |
| `edge_case_link_tuple` | N = 100 | 24.3099 ms | **0.5251 ms** | 243.099 µs | **5.251 µs** |
| `edge_case_link_tuple` | N = 1000 | 240.3026 ms | **5.3657 ms** | 240.303 µs | **5.366 µs** |
| `edge_case_membership_in_not_in` | N = 1 | 0.58 ms | **0.0352 ms** | 579.963 µs | **35.233 µs** |
| `edge_case_membership_in_not_in` | N = 10 | 4.1541 ms | **0.0839 ms** | 415.412 µs | **8.391 µs** |
| `edge_case_membership_in_not_in` | N = 100 | 37.3243 ms | **0.5232 ms** | 373.243 µs | **5.232 µs** |
| `edge_case_membership_in_not_in` | N = 1000 | 370.7482 ms | **4.9609 ms** | 370.748 µs | **4.961 µs** |
| `edge_case_contains_not_contains` | N = 1 | 0.8563 ms | **0.0366 ms** | 856.329 µs | **36.585 µs** |
| `edge_case_contains_not_contains` | N = 10 | 5.9701 ms | **0.0874 ms** | 597.01 µs | **8.741 µs** |
| `edge_case_contains_not_contains` | N = 100 | 57.1953 ms | **0.6158 ms** | 571.953 µs | **6.158 µs** |
| `edge_case_contains_not_contains` | N = 1000 | 570.3152 ms | **5.8061 ms** | 570.315 µs | **5.806 µs** |
| `edge_case_collection_all_and_none` | N = 1 | 0.6564 ms | **0.0394 ms** | 656.432 µs | **39.389 µs** |
| `edge_case_collection_all_and_none` | N = 10 | 4.8042 ms | **0.115 ms** | 480.425 µs | **11.504 µs** |
| `edge_case_collection_all_and_none` | N = 100 | 46.1172 ms | **0.7625 ms** | 461.172 µs | **7.625 µs** |
| `edge_case_collection_all_and_none` | N = 1000 | 456.7154 ms | **7.1806 ms** | 456.715 µs | **7.181 µs** |
| `edge_case_length_gt_eq` | N = 1 | 0.3323 ms | **0.0248 ms** | 332.292 µs | **24.77 µs** |
| `edge_case_length_gt_eq` | N = 10 | 2.2475 ms | **0.064 ms** | 224.755 µs | **6.395 µs** |
| `edge_case_length_gt_eq` | N = 100 | 20.8504 ms | **0.3967 ms** | 208.504 µs | **3.967 µs** |
| `edge_case_length_gt_eq` | N = 1000 | 208.6412 ms | **4.0432 ms** | 208.641 µs | **4.043 µs** |
| `edge_case_has_changed` | N = 1 | ERR | **ERR** | ERR | **ERR** |
| `edge_case_has_changed` | N = 10 | ERR | **ERR** | ERR | **ERR** |
| `edge_case_has_changed` | N = 100 | ERR | **ERR** | ERR | **ERR** |
| `edge_case_has_changed` | N = 1000 | ERR | **ERR** | ERR | **ERR** |
| `edge_case_none_vs_missing_field` | N = 1 | 0.4521 ms | **0.0227 ms** | 452.088 µs | **22.661 µs** |
| `edge_case_none_vs_missing_field` | N = 10 | 3.2167 ms | **0.0526 ms** | 321.666 µs | **5.262 µs** |
| `edge_case_none_vs_missing_field` | N = 100 | 30.3657 ms | **0.3508 ms** | 303.657 µs | **3.508 µs** |
| `edge_case_none_vs_missing_field` | N = 1000 | 303.6367 ms | **3.2035 ms** | 303.637 µs | **3.203 µs** |

---

## 6. Architectural Analysis & Diagnostic Note

1. **Approach A Experimental Code-Object Diagnostic:** Evaluating precompiled RestrictedPython code objects via `eval(code_obj)` eliminates string parsing and AST compilation overhead. However, it is labeled strictly as a **lower-level diagnostic**, NOT as the primary production `frappe.safe_eval` result, because standard Frappe APIs do not expose code object caching.
2. **Coverage Scope:** 12 of 13 fixtures passed semantic correctness tests. Fixtures that fail the gate are excluded from performance measurements. A finite fixture suite does not prove universal equivalence for all possible condition expressions; edge cases and untested operators still require verification.
3. **Production Isolation Confirmation:** **No production code, evaluators, controllers, persistence contracts, or DocTypes were modified.** All candidate evaluators and test harnesses reside isolated in `flexirule/ruleflow/tests/condition_benchmark/`.