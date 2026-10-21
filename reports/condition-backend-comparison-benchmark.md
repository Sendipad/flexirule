# FlexiRule — Condition Backend Comparison Benchmark Report

**Date:** 2026-10-21
**Repository:** [Sendipad/flexirule](https://github.com/Sendipad/flexirule)
**Branch:** `feat/condition-benchmark-sendipad-only-88653f9d`
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
| Benchmark Execution UTC | 2026-10-21T00:17:45Z |
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
| `tier1_simple_equality` | Tier 1 — Simple | 1 / 1 | 193.87 µs/op (core 179.374 µs/op) | 9.842 µs/op (core 2.28 µs/op) | **3.876 µs/op (core 2.068 µs/op)** | 5.953 µs/op (core 4.057 µs/op) | **50.02x** | **32.57x** | **1.54x** |
| `tier2_typical_business_rule` | Tier 2 — Typical Business Rule | 3 / 1 | 436.425 µs/op (core 419.49 µs/op) | 12.524 µs/op (core 4.775 µs/op) | **6.455 µs/op (core 4.549 µs/op)** | 10.699 µs/op (core 8.672 µs/op) | **67.61x** | **40.79x** | **1.66x** |
| `tier3_nested_and_or_groups` | Tier 3 — Nested Groups | 4 / 2 | 581.002 µs/op (core 563.097 µs/op) | 12.524 µs/op (core 4.645 µs/op) | **6.858 µs/op (core 4.925 µs/op)** | 11.65 µs/op (core 9.591 µs/op) | **84.72x** | **49.87x** | **1.7x** |
| `tier4_deep_nested_complex` | Tier 4 — Deep Nested Complex | 8 / 3 | 1173.186 µs/op (core 1153.292 µs/op) | 16.463 µs/op (core 8.589 µs/op) | **10.266 µs/op (core 8.331 µs/op)** | 18.457 µs/op (core 16.341 µs/op) | **114.28x** | **63.56x** | **1.8x** |
| `tier5_collection_child_records` | Tier 5 — Collection / Child Records | 3 / 2 | 721.313 µs/op (core 702.983 µs/op) | 16.757 µs/op (core 8.881 µs/op) | **10.377 µs/op (core 8.367 µs/op)** | 16.889 µs/op (core 14.789 µs/op) | **69.51x** | **42.71x** | **1.63x** |
| `edge_case_is_set_null_empty` | Edge Case — Null / Empty | 1 / 1 | 313.258 µs/op (core 298.237 µs/op) | 11.32 µs/op (core 3.819 µs/op) | **3.145 µs/op (core 1.365 µs/op)** | 4.855 µs/op (core 3.006 µs/op) | **99.61x** | **64.52x** | **1.54x** |
| `edge_case_link_tuple` | Edge Case — Link Tuple | 1 / 1 | 249.293 µs/op (core 235.211 µs/op) | 11.545 µs/op (core 4.134 µs/op) | **5.318 µs/op (core 3.561 µs/op)** | 7.382 µs/op (core 5.545 µs/op) | **46.88x** | **33.77x** | **1.39x** |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 2 / 1 | 386.045 µs/op (core 370.086 µs/op) | 10.51 µs/op (core 3.045 µs/op) | **5.049 µs/op (core 3.235 µs/op)** | 7.835 µs/op (core 5.96 µs/op) | **76.46x** | **49.27x** | **1.55x** |
| `edge_case_contains_not_contains` | Edge Case — Substring | 2 / 1 | 597.576 µs/op (core 580.279 µs/op) | 15.228 µs/op (core 7.338 µs/op) | **5.999 µs/op (core 4.072 µs/op)** | 9.104 µs/op (core 7.219 µs/op) | **99.61x** | **65.64x** | **1.52x** |
| `edge_case_collection_all_and_none` | Edge Case — Collection All/None | 1 / 2 | 484.882 µs/op (core 467.336 µs/op) | 14.663 µs/op (core 6.708 µs/op) | **7.428 µs/op (core 5.461 µs/op)** | 11.342 µs/op (core 9.348 µs/op) | **65.28x** | **42.75x** | **1.53x** |
| `edge_case_length_gt_eq` | Edge Case — Length | 1 / 1 | 218.195 µs/op (core 204.568 µs/op) | 9.765 µs/op (core 2.394 µs/op) | **4.105 µs/op (core 2.318 µs/op)** | 6.186 µs/op (core 4.322 µs/op) | **53.15x** | **35.27x** | **1.51x** |
| `edge_case_has_changed` | Edge Case — Field Change | 1 / 1 | INVALID | INVALID | **INVALID** | INVALID | N/A | N/A | N/A |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 1 / 1 | 313.136 µs/op (core 298.28 µs/op) | 10.534 µs/op (core 3.004 µs/op) | **3.238 µs/op (core 1.444 µs/op)** | 4.828 µs/op (core 2.992 µs/op) | **96.71x** | **64.86x** | **1.49x** |

---

## 4. Preparation Timings

Preparation time measured separately outside the execution loop:

| Fixture ID | Approach A Prep (ms) | Approach B Prep (ms) | Approach C Prep (ms) |
|---|---|---|---|
| `tier1_simple_equality` | 0.0972 ms | **0.0149 ms** | 0.0016 ms |
| `tier2_typical_business_rule` | 0.2043 ms | **0.0283 ms** | 0.0019 ms |
| `tier3_nested_and_or_groups` | 0.2771 ms | **0.0367 ms** | 0.0019 ms |
| `tier4_deep_nested_complex` | 0.5888 ms | **0.0551 ms** | 0.002 ms |
| `tier5_collection_child_records` | 0.3411 ms | **0.0383 ms** | 0.002 ms |
| `edge_case_is_set_null_empty` | 0.1419 ms | **0.0166 ms** | 0.0016 ms |
| `edge_case_link_tuple` | 0.141 ms | **0.0192 ms** | 0.0018 ms |
| `edge_case_membership_in_not_in` | 0.2019 ms | **0.0237 ms** | 0.0018 ms |
| `edge_case_contains_not_contains` | 0.2874 ms | **0.0246 ms** | 0.002 ms |
| `edge_case_collection_all_and_none` | 0.2163 ms | **0.0241 ms** | 0.0018 ms |
| `edge_case_length_gt_eq` | 0.1249 ms | **0.016 ms** | 0.0017 ms |
| `edge_case_has_changed` | 0.0493 ms | **0.0124 ms** | 0.0015 ms |
| `edge_case_none_vs_missing_field` | 0.1574 ms | **0.0156 ms** | 0.0017 ms |

---

## 5. Amortized Total Cost Measurements

Estimates one preparation plus N evaluations. Preparation time is the median of repeated samples; execution time is the median total duration across repeated N-evaluation batches. Fixtures that fail semantic parity are excluded. Core-only timing diagnostics are also retained in raw JSON.

$$\text{Total Amortized Cost} = \text{Preparation Time} + (N \times \text{Execution Time})$$

| Fixture ID | N Evaluations | Approach A Total Cost (ms) | Approach B Total Cost (ms) | Approach A Cost/Eval (µs) | Approach B Cost/Eval (µs) |
|---|---|---|---|---|---|
| `tier1_simple_equality` | N = 1 | 0.2854 ms | **0.0235 ms** | 285.386 µs | **23.483 µs** |
| `tier1_simple_equality` | N = 10 | 1.9338 ms | **0.0597 ms** | 193.382 µs | **5.971 µs** |
| `tier1_simple_equality` | N = 100 | 18.1551 ms | **0.3975 ms** | 181.551 µs | **3.975 µs** |
| `tier1_simple_equality` | N = 1000 | 181.2917 ms | **3.8938 ms** | 181.292 µs | **3.894 µs** |
| `tier2_typical_business_rule` | N = 1 | 0.6697 ms | **0.0435 ms** | 669.71 µs | **43.497 µs** |
| `tier2_typical_business_rule` | N = 10 | 4.6457 ms | **0.1078 ms** | 464.571 µs | **10.784 µs** |
| `tier2_typical_business_rule` | N = 100 | 42.6828 ms | **0.6573 ms** | 426.828 µs | **6.573 µs** |
| `tier2_typical_business_rule` | N = 1000 | 418.1572 ms | **6.2703 ms** | 418.157 µs | **6.27 µs** |
| `tier3_nested_and_or_groups` | N = 1 | 0.8246 ms | **0.0497 ms** | 824.578 µs | **49.704 µs** |
| `tier3_nested_and_or_groups` | N = 10 | 5.6941 ms | **0.1126 ms** | 569.413 µs | **11.263 µs** |
| `tier3_nested_and_or_groups` | N = 100 | 55.529 ms | **0.723 ms** | 555.29 µs | **7.23 µs** |
| `tier3_nested_and_or_groups` | N = 1000 | 556.5916 ms | **6.7674 ms** | 556.592 µs | **6.767 µs** |
| `tier4_deep_nested_complex` | N = 1 | 1.7814 ms | **0.0818 ms** | 1781.354 µs | **81.812 µs** |
| `tier4_deep_nested_complex` | N = 10 | 12.1532 ms | **0.1819 ms** | 1215.325 µs | **18.187 µs** |
| `tier4_deep_nested_complex` | N = 100 | 114.9029 ms | **1.0528 ms** | 1149.029 µs | **10.528 µs** |
| `tier4_deep_nested_complex` | N = 1000 | 1145.4331 ms | **10.1542 ms** | 1145.433 µs | **10.154 µs** |
| `tier5_collection_child_records` | N = 1 | 1.0702 ms | **0.0608 ms** | 1070.192 µs | **60.833 µs** |
| `tier5_collection_child_records` | N = 10 | 7.4023 ms | **0.155 ms** | 740.234 µs | **15.503 µs** |
| `tier5_collection_child_records` | N = 100 | 72.0116 ms | **1.0835 ms** | 720.116 µs | **10.835 µs** |
| `tier5_collection_child_records` | N = 1000 | 720.8359 ms | **10.488 ms** | 720.836 µs | **10.488 µs** |
| `edge_case_is_set_null_empty` | N = 1 | 0.4619 ms | **0.023 ms** | 461.863 µs | **22.964 µs** |
| `edge_case_is_set_null_empty` | N = 10 | 3.2084 ms | **0.0819 ms** | 320.842 µs | **8.191 µs** |
| `edge_case_is_set_null_empty` | N = 100 | 30.8084 ms | **0.3571 ms** | 308.084 µs | **3.571 µs** |
| `edge_case_is_set_null_empty` | N = 1000 | 315.0482 ms | **3.2288 ms** | 315.048 µs | **3.229 µs** |
| `edge_case_link_tuple` | N = 1 | 0.4117 ms | **0.0287 ms** | 411.653 µs | **28.665 µs** |
| `edge_case_link_tuple` | N = 10 | 2.5667 ms | **0.0769 ms** | 256.665 µs | **7.694 µs** |
| `edge_case_link_tuple` | N = 100 | 24.6879 ms | **0.5689 ms** | 246.879 µs | **5.689 µs** |
| `edge_case_link_tuple` | N = 1000 | 248.195 ms | **5.5065 ms** | 248.195 µs | **5.506 µs** |
| `edge_case_membership_in_not_in` | N = 1 | 0.6019 ms | **0.0355 ms** | 601.858 µs | **35.474 µs** |
| `edge_case_membership_in_not_in` | N = 10 | 3.9315 ms | **0.0829 ms** | 393.146 µs | **8.285 µs** |
| `edge_case_membership_in_not_in` | N = 100 | 37.1825 ms | **0.5387 ms** | 371.825 µs | **5.387 µs** |
| `edge_case_membership_in_not_in` | N = 1000 | 378.7377 ms | **4.9983 ms** | 378.738 µs | **4.998 µs** |
| `edge_case_contains_not_contains` | N = 1 | 0.8626 ms | **0.0388 ms** | 862.619 µs | **38.835 µs** |
| `edge_case_contains_not_contains` | N = 10 | 6.0519 ms | **0.0934 ms** | 605.186 µs | **9.337 µs** |
| `edge_case_contains_not_contains` | N = 100 | 57.5045 ms | **0.6183 ms** | 575.045 µs | **6.183 µs** |
| `edge_case_contains_not_contains` | N = 1000 | 582.0521 ms | **5.8213 ms** | 582.052 µs | **5.821 µs** |
| `edge_case_collection_all_and_none` | N = 1 | 0.675 ms | **0.0388 ms** | 675.008 µs | **38.75 µs** |
| `edge_case_collection_all_and_none` | N = 10 | 4.8317 ms | **0.1082 ms** | 483.166 µs | **10.82 µs** |
| `edge_case_collection_all_and_none` | N = 100 | 46.6221 ms | **0.7675 ms** | 466.221 µs | **7.675 µs** |
| `edge_case_collection_all_and_none` | N = 1000 | 471.3839 ms | **7.2112 ms** | 471.384 µs | **7.211 µs** |
| `edge_case_length_gt_eq` | N = 1 | 0.3341 ms | **0.0251 ms** | 334.053 µs | **25.068 µs** |
| `edge_case_length_gt_eq` | N = 10 | 2.2683 ms | **0.0662 ms** | 226.831 µs | **6.619 µs** |
| `edge_case_length_gt_eq` | N = 100 | 22.0837 ms | **0.4065 ms** | 220.837 µs | **4.065 µs** |
| `edge_case_length_gt_eq` | N = 1000 | 217.9331 ms | **4.0506 ms** | 217.933 µs | **4.051 µs** |
| `edge_case_has_changed` | N = 1 | ERR | **ERR** | ERR | **ERR** |
| `edge_case_has_changed` | N = 10 | ERR | **ERR** | ERR | **ERR** |
| `edge_case_has_changed` | N = 100 | ERR | **ERR** | ERR | **ERR** |
| `edge_case_has_changed` | N = 1000 | ERR | **ERR** | ERR | **ERR** |
| `edge_case_none_vs_missing_field` | N = 1 | 0.4788 ms | **0.0227 ms** | 478.767 µs | **22.664 µs** |
| `edge_case_none_vs_missing_field` | N = 10 | 3.2794 ms | **0.0539 ms** | 327.943 µs | **5.389 µs** |
| `edge_case_none_vs_missing_field` | N = 100 | 31.4668 ms | **0.3289 ms** | 314.668 µs | **3.289 µs** |
| `edge_case_none_vs_missing_field` | N = 1000 | 311.7222 ms | **3.2155 ms** | 311.722 µs | **3.216 µs** |

---

## 6. Architectural Analysis & Diagnostic Note

1. **Approach A Experimental Code-Object Diagnostic:** Evaluating precompiled RestrictedPython code objects via `eval(code_obj)` eliminates string parsing and AST compilation overhead. However, it is labeled strictly as a **lower-level diagnostic**, NOT as the primary production `frappe.safe_eval` result, because standard Frappe APIs do not expose code object caching.
2. **Coverage Scope:** 12 of 13 fixtures passed semantic correctness tests. Fixtures that fail the gate are excluded from performance measurements. A finite fixture suite does not prove universal equivalence for all possible condition expressions; edge cases and untested operators still require verification.
3. **Production Isolation Confirmation:** **No production code, evaluators, controllers, persistence contracts, or DocTypes were modified.** All candidate evaluators and test harnesses reside isolated in `flexirule/ruleflow/tests/condition_benchmark/`.