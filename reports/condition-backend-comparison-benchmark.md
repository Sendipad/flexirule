# FlexiRule — Condition Backend Comparison Benchmark Report

> **SUPERSEDED HISTORICAL RESULTS — DO NOT USE THESE TIMINGS TO PICK A WINNER.** This report was generated with benchmark protocol v1. Its amortized measurements used one sample per execution count, omitted the semantic-correctness gate, and ran candidates in a fixed order. The runner now uses protocol v2: repeated preparation and execution samples, candidate-order rotation, alternating matching/non-matching inputs, and explicit correctness gates. The project's Frappe bench must run the updated benchmark to produce replacement numbers. The old tables below are preserved only as historical diagnostic evidence.


**Date:** 2026-10-20
**Repository:** [Sendipad/flexirule](https://github.com/Sendipad/flexirule)
**Branch:** `feat/condition-benchmark`
**Report Location:** `/app/reports/condition-backend-comparison-benchmark.md`
**Raw Results Data:** `reports/condition_benchmark_results.json`

---

## Executive Summary

This report documents the architectural investigation, empirical runtime probe, correctness test suite, and high-precision performance benchmarks comparing two architectural candidates for evaluating visual JSON rule conditions in FlexiRule:

- **Approach A — Precompiled Python Expression (`Approach A (frappe.safe_eval)`):** Evaluating a Python expression string generated from a condition tree using installed Frappe v15 restricted evaluation (`frappe.safe_eval`). Includes an isolated experimental diagnostic (`Approach A (Experimental Restricted Code Object)`) for evaluating precompiled RestrictedPython code objects.
- **Approach B — Prebuilt Normalized Execution Plan (`Approach B (Normalized Execution Plan)`):** Evaluating a typed, validated execution plan using a pure evaluator and comparator without Python compilation or AST parsing during execution.

### Summary Statistics and Findings

1. **`frappe.safe_eval` Overhead:** Installed Frappe v15 `frappe.safe_eval` performs `unicodedata.normalize()`, `ast.parse()`, AST node walking (`_validate_safe_eval_syntax`), and RestrictedPython AST transformation / compilation on **every single invocation**. It implements **no caching** of compiled bytecode objects.
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
| Benchmark Execution UTC | 2026-10-20T18:20:09Z |
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

**Methodology:** Preparation (compilation / plan building) was performed **outside** the timed loop. The timed loop measured prepared execution over 5 batches of 10,000 iterations each (10,000 iterations x 5 batches).

| Fixture ID | Tier | Leaf / Depth | Approach A (`safe_eval`) | Approach A Exp (`code_obj`) | Approach B (`plan`) | Approach C (`json_tree`) | Speedup B vs Primary A | Speedup C vs Primary A | Speedup B vs C |
|---|---|---|---|---|---|---|---|---|---|
| `tier1_simple_equality` | Tier 1 — Simple | 1 / 1 | 175.582 µs/op | 9.194 µs/op | **3.658 µs/op** | 5.61 µs/op | **48.0x** | **31.3x** | **1.53x** |
| `tier2_typical_business_rule` | Tier 2 — Typical Business Rule | 3 / 1 | 413.094 µs/op | 12.414 µs/op | **6.947 µs/op** | 11.585 µs/op | **59.46x** | **35.66x** | **1.67x** |
| `tier3_nested_and_or_groups` | Tier 3 — Nested Groups | 4 / 2 | 588.872 µs/op | 12.395 µs/op | **7.375 µs/op** | 12.96 µs/op | **79.85x** | **45.44x** | **1.76x** |
| `tier4_deep_nested_complex` | Tier 4 — Deep Nested Complex | 8 / 3 | 1194.186 µs/op | 18.549 µs/op | **12.348 µs/op** | 21.814 µs/op | **96.71x** | **54.74x** | **1.77x** |
| `tier5_collection_child_records` | Tier 5 — Collection / Child Records | 3 / 2 | 719.069 µs/op | 17.519 µs/op | **10.985 µs/op** | 18.398 µs/op | **65.46x** | **39.08x** | **1.67x** |
| `edge_case_is_set_null_empty` | Edge Case — Null / Empty | 1 / 1 | 305.123 µs/op | 10.785 µs/op | **2.854 µs/op** | 4.53 µs/op | **106.91x** | **67.36x** | **1.59x** |
| `edge_case_link_tuple` | Edge Case — Link Tuple | 1 / 1 | 246.964 µs/op | 11.337 µs/op | **5.123 µs/op** | 6.939 µs/op | **48.21x** | **35.59x** | **1.35x** |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 2 / 1 | 448.753 µs/op | 11.381 µs/op | **9.384 µs/op** | 9.907 µs/op | **47.82x** | **45.3x** | **1.06x** |
| `edge_case_contains_not_contains` | Edge Case — Substring | 2 / 1 | 877.982 µs/op | 14.205 µs/op | **5.554 µs/op** | 8.642 µs/op | **158.08x** | **101.59x** | **1.56x** |
| `edge_case_collection_all_and_none` | Edge Case — Collection All/None | 1 / 2 | 469.16 µs/op | 13.229 µs/op | **6.95 µs/op** | 10.621 µs/op | **67.51x** | **44.17x** | **1.53x** |
| `edge_case_length_gt_eq` | Edge Case — Length | 1 / 1 | 412.309 µs/op | 53.601 µs/op | **20.644 µs/op** | 12.464 µs/op | **19.97x** | **33.08x** | **0.6x** |
| `edge_case_has_changed` | Edge Case — Field Change | 1 / 1 | INVALID | INVALID | **INVALID** | INVALID | N/A | N/A | N/A |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 1 / 1 | 725.764 µs/op | 23.682 µs/op | **5.614 µs/op** | 4.734 µs/op | **129.28x** | **153.31x** | **0.84x** |

---

## 4. Preparation Timings

Preparation time measured separately outside the execution loop:

| Fixture ID | Approach A Prep (ms) | Approach B Prep (ms) | Approach C Prep (ms) |
|---|---|---|---|
| `tier1_simple_equality` | 0.1137 ms | **0.0161 ms** | 0.0016 ms |
| `tier2_typical_business_rule` | 0.2327 ms | **0.0305 ms** | 0.002 ms |
| `tier3_nested_and_or_groups` | 0.2989 ms | **0.036 ms** | 0.0017 ms |
| `tier4_deep_nested_complex` | 0.624 ms | **0.0587 ms** | 0.0021 ms |
| `tier5_collection_child_records` | 0.38 ms | **0.0395 ms** | 0.002 ms |
| `edge_case_is_set_null_empty` | 0.1893 ms | **0.0162 ms** | 0.0019 ms |
| `edge_case_link_tuple` | 0.1528 ms | **0.0168 ms** | 0.0018 ms |
| `edge_case_membership_in_not_in` | 0.2328 ms | **0.0253 ms** | 0.0018 ms |
| `edge_case_contains_not_contains` | 0.3051 ms | **0.0576 ms** | 0.0035 ms |
| `edge_case_collection_all_and_none` | 0.2058 ms | **0.0265 ms** | 0.0021 ms |
| `edge_case_length_gt_eq` | 0.119 ms | **0.0181 ms** | 0.0018 ms |
| `edge_case_has_changed` | 0.1072 ms | **0.0345 ms** | 0.0102 ms |
| `edge_case_none_vs_missing_field` | 0.3477 ms | **0.0264 ms** | 0.0022 ms |

---

## 5. Amortized Total Cost Measurements

Calculates total cost for 1 preparation followed by N evaluations:

$$\text{Total Amortized Cost} = \text{Preparation Time} + (N \times \text{Execution Time})$$

| Fixture ID | N Evaluations | Approach A Total Cost (ms) | Approach B Total Cost (ms) | Approach A Cost/Eval (µs) | Approach B Cost/Eval (µs) |
|---|---|---|---|---|---|
| `tier1_simple_equality` | N = 1 | 0.5177 ms | **0.0384 ms** | 517.715 µs | **38.418 µs** |
| `tier1_simple_equality` | N = 10 | 2.1921 ms | **0.0698 ms** | 219.21 µs | **6.982 µs** |
| `tier1_simple_equality` | N = 100 | 19.7558 ms | **0.4378 ms** | 197.558 µs | **4.378 µs** |
| `tier1_simple_equality` | N = 1000 | 186.6333 ms | **3.8342 ms** | 186.633 µs | **3.834 µs** |
| `tier2_typical_business_rule` | N = 1 | 0.9171 ms | **0.0627 ms** | 917.137 µs | **62.681 µs** |
| `tier2_typical_business_rule` | N = 10 | 4.6286 ms | **0.1265 ms** | 462.862 µs | **12.646 µs** |
| `tier2_typical_business_rule` | N = 100 | 47.2101 ms | **1.1192 ms** | 472.101 µs | **11.192 µs** |
| `tier2_typical_business_rule` | N = 1000 | 895.3394 ms | **20.0801 ms** | 895.339 µs | **20.08 µs** |
| `tier3_nested_and_or_groups` | N = 1 | 2.2569 ms | **0.1544 ms** | 2256.9 µs | **154.398 µs** |
| `tier3_nested_and_or_groups` | N = 10 | 16.2889 ms | **0.3754 ms** | 1628.893 µs | **37.536 µs** |
| `tier3_nested_and_or_groups` | N = 100 | 107.3218 ms | **1.2325 ms** | 1073.218 µs | **12.325 µs** |
| `tier3_nested_and_or_groups` | N = 1000 | 1185.0244 ms | **11.4815 ms** | 1185.024 µs | **11.482 µs** |
| `tier4_deep_nested_complex` | N = 1 | 2.1083 ms | **0.1001 ms** | 2108.305 µs | **100.067 µs** |
| `tier4_deep_nested_complex` | N = 10 | 12.9702 ms | **0.2618 ms** | 1297.023 µs | **26.175 µs** |
| `tier4_deep_nested_complex` | N = 100 | 122.4727 ms | **1.4586 ms** | 1224.727 µs | **14.586 µs** |
| `tier4_deep_nested_complex` | N = 1000 | 1205.5027 ms | **12.6833 ms** | 1205.503 µs | **12.683 µs** |
| `tier5_collection_child_records` | N = 1 | 1.4146 ms | **0.0796 ms** | 1414.608 µs | **79.633 µs** |
| `tier5_collection_child_records` | N = 10 | 8.1241 ms | **0.1938 ms** | 812.41 µs | **19.381 µs** |
| `tier5_collection_child_records` | N = 100 | 76.9841 ms | **1.1776 ms** | 769.841 µs | **11.776 µs** |
| `tier5_collection_child_records` | N = 1000 | 758.5752 ms | **12.2917 ms** | 758.575 µs | **12.292 µs** |
| `edge_case_is_set_null_empty` | N = 1 | 0.6757 ms | **0.0398 ms** | 675.707 µs | **39.788 µs** |
| `edge_case_is_set_null_empty` | N = 10 | 3.7833 ms | **0.0677 ms** | 378.334 µs | **6.768 µs** |
| `edge_case_is_set_null_empty` | N = 100 | 33.6427 ms | **0.3222 ms** | 336.427 µs | **3.222 µs** |
| `edge_case_is_set_null_empty` | N = 1000 | 338.1336 ms | **2.9759 ms** | 338.134 µs | **2.976 µs** |
| `edge_case_link_tuple` | N = 1 | 0.6426 ms | **0.0403 ms** | 642.567 µs | **40.331 µs** |
| `edge_case_link_tuple` | N = 10 | 3.1523 ms | **0.1281 ms** | 315.23 µs | **12.81 µs** |
| `edge_case_link_tuple` | N = 100 | 26.8434 ms | **0.5715 ms** | 268.434 µs | **5.715 µs** |
| `edge_case_link_tuple` | N = 1000 | 267.7024 ms | **5.084 ms** | 267.702 µs | **5.084 µs** |
| `edge_case_membership_in_not_in` | N = 1 | 0.9367 ms | **0.0519 ms** | 936.655 µs | **51.935 µs** |
| `edge_case_membership_in_not_in` | N = 10 | 6.3121 ms | **0.1042 ms** | 631.21 µs | **10.422 µs** |
| `edge_case_membership_in_not_in` | N = 100 | 41.4493 ms | **0.7553 ms** | 414.493 µs | **7.553 µs** |
| `edge_case_membership_in_not_in` | N = 1000 | 410.223 ms | **6.0929 ms** | 410.223 µs | **6.093 µs** |
| `edge_case_contains_not_contains` | N = 1 | 1.2245 ms | **0.0627 ms** | 1224.502 µs | **62.728 µs** |
| `edge_case_contains_not_contains` | N = 10 | 6.5727 ms | **0.1089 ms** | 657.275 µs | **10.887 µs** |
| `edge_case_contains_not_contains` | N = 100 | 61.4513 ms | **0.6307 ms** | 614.513 µs | **6.307 µs** |
| `edge_case_contains_not_contains` | N = 1000 | 624.9389 ms | **5.5422 ms** | 624.939 µs | **5.542 µs** |
| `edge_case_collection_all_and_none` | N = 1 | 1.0149 ms | **0.0623 ms** | 1014.864 µs | **62.263 µs** |
| `edge_case_collection_all_and_none` | N = 10 | 5.5708 ms | **0.2456 ms** | 557.081 µs | **24.564 µs** |
| `edge_case_collection_all_and_none` | N = 100 | 50.3013 ms | **0.88 ms** | 503.013 µs | **8.8 µs** |
| `edge_case_collection_all_and_none` | N = 1000 | 495.4954 ms | **7.2088 ms** | 495.495 µs | **7.209 µs** |
| `edge_case_length_gt_eq` | N = 1 | 0.6489 ms | **0.0471 ms** | 648.915 µs | **47.071 µs** |
| `edge_case_length_gt_eq` | N = 10 | 2.9466 ms | **0.0878 ms** | 294.655 µs | **8.779 µs** |
| `edge_case_length_gt_eq` | N = 100 | 23.4855 ms | **0.5339 ms** | 234.855 µs | **5.339 µs** |
| `edge_case_length_gt_eq` | N = 1000 | 227.6945 ms | **3.813 ms** | 227.694 µs | **3.813 µs** |
| `edge_case_has_changed` | N = 1 | 0.3815 ms | **0.0522 ms** | 381.477 µs | **52.229 µs** |
| `edge_case_has_changed` | N = 10 | 0.9853 ms | **0.0651 ms** | 98.53 µs | **6.51 µs** |
| `edge_case_has_changed` | N = 100 | 6.4432 ms | **0.3768 ms** | 64.432 µs | **3.768 µs** |
| `edge_case_has_changed` | N = 1000 | 61.344 ms | **3.6128 ms** | 61.344 µs | **3.613 µs** |
| `edge_case_none_vs_missing_field` | N = 1 | 0.6495 ms | **0.039 ms** | 649.496 µs | **39.008 µs** |
| `edge_case_none_vs_missing_field` | N = 10 | 3.6319 ms | **0.0639 ms** | 363.195 µs | **6.393 µs** |
| `edge_case_none_vs_missing_field` | N = 100 | 32.6529 ms | **0.3675 ms** | 326.529 µs | **3.675 µs** |
| `edge_case_none_vs_missing_field` | N = 1000 | 329.0458 ms | **2.8947 ms** | 329.046 µs | **2.895 µs** |

---

## 6. Architectural Analysis & Diagnostic Note

1. **Approach A Experimental Code-Object Diagnostic:** Evaluating precompiled RestrictedPython code objects via `eval(code_obj)` eliminates string parsing and AST compilation overhead. However, it is labeled strictly as a **lower-level diagnostic**, NOT as the primary production `frappe.safe_eval` result, because standard Frappe APIs do not expose code object caching.
2. **Coverage Scope:** The historical protocol-v1 run passed only 12 of 13 fixtures; `edge_case_has_changed` failed semantic parity. These historical timings are superseded and must not be used to select a performance winner. A finite fixture suite also cannot prove universal equivalence for all possible condition expressions.
3. **Production Isolation Confirmation:** **No production code, evaluators, controllers, persistence contracts, or DocTypes were modified.** All candidate evaluators and test harnesses reside isolated in `flexirule/ruleflow/tests/condition_benchmark/`.