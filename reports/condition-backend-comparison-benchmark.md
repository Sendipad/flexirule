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
| Benchmark Execution UTC | 2026-10-20T22:14:54Z |
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
| `tier1_simple_equality` | Tier 1 — Simple | 1 / 1 | 173.03 µs/op (core 160.694 µs/op) | 9.595 µs/op (core 2.254 µs/op) | **3.922 µs/op (core 2.137 µs/op)** | 5.8 µs/op (core 3.942 µs/op) | **44.12x** | **29.83x** | **1.48x** |
| `tier2_typical_business_rule` | Tier 2 — Typical Business Rule | 3 / 1 | 406.805 µs/op (core 391.308 µs/op) | 11.946 µs/op (core 4.539 µs/op) | **6.249 µs/op (core 4.446 µs/op)** | 10.235 µs/op (core 8.344 µs/op) | **65.1x** | **39.75x** | **1.64x** |
| `tier3_nested_and_or_groups` | Tier 3 — Nested Groups | 4 / 2 | 539.013 µs/op (core 522.833 µs/op) | 11.9 µs/op (core 4.431 µs/op) | **6.642 µs/op (core 4.816 µs/op)** | 11.083 µs/op (core 9.139 µs/op) | **81.15x** | **48.63x** | **1.67x** |
| `tier4_deep_nested_complex` | Tier 4 — Deep Nested Complex | 8 / 3 | 1124.092 µs/op (core 1105.424 µs/op) | 15.909 µs/op (core 8.451 µs/op) | **10.005 µs/op (core 8.148 µs/op)** | 17.542 µs/op (core 15.487 µs/op) | **112.35x** | **64.08x** | **1.75x** |
| `tier5_collection_child_records` | Tier 5 — Collection / Child Records | 3 / 2 | 707.112 µs/op (core 689.479 µs/op) | 16.4 µs/op (core 8.736 µs/op) | **10.429 µs/op (core 8.504 µs/op)** | 16.626 µs/op (core 14.606 µs/op) | **67.8x** | **42.53x** | **1.59x** |
| `edge_case_is_set_null_empty` | Edge Case — Null / Empty | 1 / 1 | 306.567 µs/op (core 291.698 µs/op) | 11.287 µs/op (core 3.807 µs/op) | **3.164 µs/op (core 1.398 µs/op)** | 4.757 µs/op (core 2.961 µs/op) | **96.89x** | **64.45x** | **1.5x** |
| `edge_case_link_tuple` | Edge Case — Link Tuple | 1 / 1 | 243.209 µs/op (core 229.584 µs/op) | 11.56 µs/op (core 4.121 µs/op) | **5.291 µs/op (core 3.548 µs/op)** | 7.203 µs/op (core 5.387 µs/op) | **45.97x** | **33.76x** | **1.36x** |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 2 / 1 | 373.397 µs/op (core 357.765 µs/op) | 10.662 µs/op (core 3.06 µs/op) | **4.972 µs/op (core 3.161 µs/op)** | 7.584 µs/op (core 5.73 µs/op) | **75.1x** | **49.23x** | **1.53x** |
| `edge_case_contains_not_contains` | Edge Case — Substring | 2 / 1 | 573.122 µs/op (core 557.062 µs/op) | 14.472 µs/op (core 7.065 µs/op) | **5.703 µs/op (core 3.889 µs/op)** | 8.899 µs/op (core 7.03 µs/op) | **100.49x** | **64.4x** | **1.56x** |
| `edge_case_collection_all_and_none` | Edge Case — Collection All/None | 1 / 2 | 465.841 µs/op (core 448.87 µs/op) | 14.036 µs/op (core 6.469 µs/op) | **7.159 µs/op (core 5.31 µs/op)** | 10.739 µs/op (core 8.773 µs/op) | **65.07x** | **43.38x** | **1.5x** |
| `edge_case_length_gt_eq` | Edge Case — Length | 1 / 1 | 212.726 µs/op (core 199.446 µs/op) | 9.782 µs/op (core 2.434 µs/op) | **4.025 µs/op (core 2.264 µs/op)** | 5.993 µs/op (core 4.157 µs/op) | **52.85x** | **35.5x** | **1.49x** |
| `edge_case_has_changed` | Edge Case — Field Change | 1 / 1 | INVALID | INVALID | **INVALID** | INVALID | N/A | N/A | N/A |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 1 / 1 | 301.281 µs/op (core 286.905 µs/op) | 10.298 µs/op (core 2.864 µs/op) | **3.15 µs/op (core 1.415 µs/op)** | 4.723 µs/op (core 2.947 µs/op) | **95.64x** | **63.79x** | **1.5x** |

---

## 4. Preparation Timings

Preparation time measured separately outside the execution loop:

| Fixture ID | Approach A Prep (ms) | Approach B Prep (ms) | Approach C Prep (ms) |
|---|---|---|---|
| `tier1_simple_equality` | 0.0954 ms | **0.0147 ms** | 0.0015 ms |
| `tier2_typical_business_rule` | 0.2101 ms | **0.0278 ms** | 0.0018 ms |
| `tier3_nested_and_or_groups` | 0.2717 ms | **0.0334 ms** | 0.0019 ms |
| `tier4_deep_nested_complex` | 0.6443 ms | **0.0521 ms** | 0.0018 ms |
| `tier5_collection_child_records` | 0.3353 ms | **0.0344 ms** | 0.0019 ms |
| `edge_case_is_set_null_empty` | 0.1486 ms | **0.0167 ms** | 0.0016 ms |
| `edge_case_link_tuple` | 0.1385 ms | **0.017 ms** | 0.0018 ms |
| `edge_case_membership_in_not_in` | 0.2053 ms | **0.0232 ms** | 0.0018 ms |
| `edge_case_contains_not_contains` | 0.3188 ms | **0.0217 ms** | 0.0018 ms |
| `edge_case_collection_all_and_none` | 0.2092 ms | **0.0228 ms** | 0.0017 ms |
| `edge_case_length_gt_eq` | 0.1131 ms | **0.0164 ms** | 0.0017 ms |
| `edge_case_has_changed` | 0.0448 ms | **0.0121 ms** | 0.0015 ms |
| `edge_case_none_vs_missing_field` | 0.1429 ms | **0.016 ms** | 0.0016 ms |

---

## 5. Amortized Total Cost Measurements

Estimates one preparation plus N evaluations. Preparation time is the median of repeated samples; execution time is the median total duration across repeated N-evaluation batches. Fixtures that fail semantic parity are excluded. Core-only timing diagnostics are also retained in raw JSON.

$$\text{Total Amortized Cost} = \text{Preparation Time} + (N \times \text{Execution Time})$$

| Fixture ID | N Evaluations | Approach A Total Cost (ms) | Approach B Total Cost (ms) | Approach A Cost/Eval (µs) | Approach B Cost/Eval (µs) |
|---|---|---|---|---|---|
| `tier1_simple_equality` | N = 1 | 0.2735 ms | **0.0223 ms** | 273.505 µs | **22.273 µs** |
| `tier1_simple_equality` | N = 10 | 1.8841 ms | **0.0584 ms** | 188.412 µs | **5.841 µs** |
| `tier1_simple_equality` | N = 100 | 17.2658 ms | **0.384 ms** | 172.658 µs | **3.84 µs** |
| `tier1_simple_equality` | N = 1000 | 172.3137 ms | **3.8294 ms** | 172.314 µs | **3.829 µs** |
| `tier2_typical_business_rule` | N = 1 | 0.6674 ms | **0.0434 ms** | 667.445 µs | **43.381 µs** |
| `tier2_typical_business_rule` | N = 10 | 4.3306 ms | **0.0987 ms** | 433.057 µs | **9.871 µs** |
| `tier2_typical_business_rule` | N = 100 | 40.955 ms | **0.6783 ms** | 409.55 µs | **6.783 µs** |
| `tier2_typical_business_rule` | N = 1000 | 407.2868 ms | **6.217 ms** | 407.287 µs | **6.217 µs** |
| `tier3_nested_and_or_groups` | N = 1 | 0.8334 ms | **0.0513 ms** | 833.41 µs | **51.294 µs** |
| `tier3_nested_and_or_groups` | N = 10 | 5.6664 ms | **0.1108 ms** | 566.64 µs | **11.077 µs** |
| `tier3_nested_and_or_groups` | N = 100 | 54.2464 ms | **0.7095 ms** | 542.464 µs | **7.095 µs** |
| `tier3_nested_and_or_groups` | N = 1000 | 537.1753 ms | **6.6875 ms** | 537.175 µs | **6.687 µs** |
| `tier4_deep_nested_complex` | N = 1 | 1.6709 ms | **0.0853 ms** | 1670.887 µs | **85.279 µs** |
| `tier4_deep_nested_complex` | N = 10 | 11.7305 ms | **0.1717 ms** | 1173.053 µs | **17.169 µs** |
| `tier4_deep_nested_complex` | N = 100 | 111.9808 ms | **1.1053 ms** | 1119.808 µs | **11.053 µs** |
| `tier4_deep_nested_complex` | N = 1000 | 1122.9612 ms | **10.0836 ms** | 1122.961 µs | **10.084 µs** |
| `tier5_collection_child_records` | N = 1 | 1.0879 ms | **0.0589 ms** | 1087.896 µs | **58.879 µs** |
| `tier5_collection_child_records` | N = 10 | 7.375 ms | **0.1947 ms** | 737.503 µs | **19.469 µs** |
| `tier5_collection_child_records` | N = 100 | 70.7979 ms | **1.0681 ms** | 707.979 µs | **10.681 µs** |
| `tier5_collection_child_records` | N = 1000 | 707.603 ms | **10.3623 ms** | 707.603 µs | **10.362 µs** |
| `edge_case_is_set_null_empty` | N = 1 | 0.4634 ms | **0.0219 ms** | 463.4 µs | **21.928 µs** |
| `edge_case_is_set_null_empty` | N = 10 | 3.1888 ms | **0.051 ms** | 318.884 µs | **5.099 µs** |
| `edge_case_is_set_null_empty` | N = 100 | 30.5529 ms | **0.3414 ms** | 305.529 µs | **3.414 µs** |
| `edge_case_is_set_null_empty` | N = 1000 | 306.0216 ms | **3.1365 ms** | 306.022 µs | **3.137 µs** |
| `edge_case_link_tuple` | N = 1 | 0.4188 ms | **0.0281 ms** | 418.781 µs | **28.088 µs** |
| `edge_case_link_tuple` | N = 10 | 2.6067 ms | **0.0766 ms** | 260.674 µs | **7.656 µs** |
| `edge_case_link_tuple` | N = 100 | 24.496 ms | **0.5672 ms** | 244.96 µs | **5.672 µs** |
| `edge_case_link_tuple` | N = 1000 | 242.9737 ms | **5.3944 ms** | 242.974 µs | **5.394 µs** |
| `edge_case_membership_in_not_in` | N = 1 | 0.6332 ms | **0.036 ms** | 633.157 µs | **36.007 µs** |
| `edge_case_membership_in_not_in` | N = 10 | 3.9438 ms | **0.0809 ms** | 394.381 µs | **8.094 µs** |
| `edge_case_membership_in_not_in` | N = 100 | 37.6445 ms | **0.4933 ms** | 376.445 µs | **4.933 µs** |
| `edge_case_membership_in_not_in` | N = 1000 | 500.1436 ms | **5.0049 ms** | 500.144 µs | **5.005 µs** |
| `edge_case_contains_not_contains` | N = 1 | 1.5949 ms | **0.0652 ms** | 1594.943 µs | **65.216 µs** |
| `edge_case_contains_not_contains` | N = 10 | 11.5125 ms | **0.1282 ms** | 1151.247 µs | **12.824 µs** |
| `edge_case_contains_not_contains` | N = 100 | 101.537 ms | **1.0229 ms** | 1015.37 µs | **10.229 µs** |
| `edge_case_contains_not_contains` | N = 1000 | 575.3814 ms | **5.6856 ms** | 575.381 µs | **5.686 µs** |
| `edge_case_collection_all_and_none` | N = 1 | 0.6725 ms | **0.04 ms** | 672.452 µs | **39.998 µs** |
| `edge_case_collection_all_and_none` | N = 10 | 4.8771 ms | **0.1049 ms** | 487.705 µs | **10.491 µs** |
| `edge_case_collection_all_and_none` | N = 100 | 46.5649 ms | **0.7694 ms** | 465.649 µs | **7.694 µs** |
| `edge_case_collection_all_and_none` | N = 1000 | 463.1721 ms | **7.1582 ms** | 463.172 µs | **7.158 µs** |
| `edge_case_length_gt_eq` | N = 1 | 0.3217 ms | **0.0255 ms** | 321.694 µs | **25.459 µs** |
| `edge_case_length_gt_eq` | N = 10 | 2.2848 ms | **0.0643 ms** | 228.477 µs | **6.435 µs** |
| `edge_case_length_gt_eq` | N = 100 | 21.12 ms | **0.4432 ms** | 211.2 µs | **4.432 µs** |
| `edge_case_length_gt_eq` | N = 1000 | 210.3294 ms | **4.0504 ms** | 210.329 µs | **4.05 µs** |
| `edge_case_has_changed` | N = 1 | ERR | **ERR** | ERR | **ERR** |
| `edge_case_has_changed` | N = 10 | ERR | **ERR** | ERR | **ERR** |
| `edge_case_has_changed` | N = 100 | ERR | **ERR** | ERR | **ERR** |
| `edge_case_has_changed` | N = 1000 | ERR | **ERR** | ERR | **ERR** |
| `edge_case_none_vs_missing_field` | N = 1 | 0.4544 ms | **0.0224 ms** | 454.369 µs | **22.428 µs** |
| `edge_case_none_vs_missing_field` | N = 10 | 3.266 ms | **0.0535 ms** | 326.597 µs | **5.353 µs** |
| `edge_case_none_vs_missing_field` | N = 100 | 30.4919 ms | **0.3109 ms** | 304.919 µs | **3.109 µs** |
| `edge_case_none_vs_missing_field` | N = 1000 | 305.5426 ms | **3.1904 ms** | 305.543 µs | **3.19 µs** |

---

## 6. Architectural Analysis & Diagnostic Note

1. **Approach A Experimental Code-Object Diagnostic:** Evaluating precompiled RestrictedPython code objects via `eval(code_obj)` eliminates string parsing and AST compilation overhead. However, it is labeled strictly as a **lower-level diagnostic**, NOT as the primary production `frappe.safe_eval` result, because standard Frappe APIs do not expose code object caching.
2. **Coverage Scope:** 12 of 13 fixtures passed semantic correctness tests. Fixtures that fail the gate are excluded from performance measurements. A finite fixture suite does not prove universal equivalence for all possible condition expressions; edge cases and untested operators still require verification.
3. **Production Isolation Confirmation:** **No production code, evaluators, controllers, persistence contracts, or DocTypes were modified.** All candidate evaluators and test harnesses reside isolated in `flexirule/ruleflow/tests/condition_benchmark/`.