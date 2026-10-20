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
2. **`has_changed` Operator Alignment:** In `ConditionCompiler`, the `has_changed` operator is deprecated and returns `True` for backward compatibility, while candidate evaluators implement dynamic diff comparison against `_doc_before_save`. Under the correctness gate, `edge_case_has_changed` fails parity and is excluded from timing measurements.
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
| Benchmark Execution UTC | 2026-10-20T22:56:13Z |
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
| `tier1_simple_equality` | Tier 1 — Simple | 1 / 1 | 176.924 µs/op (core 164.133 µs/op) | 9.647 µs/op (core 2.302 µs/op) | **3.802 µs/op (core 2.065 µs/op)** | 5.814 µs/op (core 3.981 µs/op) | **46.53x** | **30.43x** | **1.53x** |
| `tier2_typical_business_rule` | Tier 2 — Typical Business Rule | 3 / 1 | 411.382 µs/op (core 395.655 µs/op) | 12.103 µs/op (core 4.57 µs/op) | **6.275 µs/op (core 4.468 µs/op)** | 10.184 µs/op (core 8.252 µs/op) | **65.56x** | **40.39x** | **1.62x** |
| `tier3_nested_and_or_groups` | Tier 3 — Nested Groups | 4 / 2 | 541.058 µs/op (core 524.841 µs/op) | 12.094 µs/op (core 4.544 µs/op) | **6.558 µs/op (core 4.78 µs/op)** | 11.238 µs/op (core 9.296 µs/op) | **82.5x** | **48.15x** | **1.71x** |
| `tier4_deep_nested_complex` | Tier 4 — Deep Nested Complex | 8 / 3 | 1127.632 µs/op (core 1108.819 µs/op) | 15.972 µs/op (core 8.385 µs/op) | **10.11 µs/op (core 8.226 µs/op)** | 17.47 µs/op (core 15.377 µs/op) | **111.54x** | **64.55x** | **1.73x** |
| `tier5_collection_child_records` | Tier 5 — Collection / Child Records | 3 / 2 | 703.523 µs/op (core 685.727 µs/op) | 16.65 µs/op (core 8.871 µs/op) | **10.485 µs/op (core 8.539 µs/op)** | 16.662 µs/op (core 14.611 µs/op) | **67.1x** | **42.22x** | **1.59x** |
| `edge_case_is_set_null_empty` | Edge Case — Null / Empty | 1 / 1 | 307.711 µs/op (core 293.129 µs/op) | 11.206 µs/op (core 3.819 µs/op) | **3.122 µs/op (core 1.36 µs/op)** | 4.895 µs/op (core 3.04 µs/op) | **98.56x** | **62.86x** | **1.57x** |
| `edge_case_link_tuple` | Edge Case — Link Tuple | 1 / 1 | 242.681 µs/op (core 229.193 µs/op) | 11.513 µs/op (core 4.135 µs/op) | **5.294 µs/op (core 3.552 µs/op)** | 7.265 µs/op (core 5.409 µs/op) | **45.84x** | **33.4x** | **1.37x** |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 2 / 1 | 371.176 µs/op (core 355.76 µs/op) | 10.617 µs/op (core 3.098 µs/op) | **5.013 µs/op (core 3.235 µs/op)** | 7.61 µs/op (core 5.703 µs/op) | **74.04x** | **48.77x** | **1.52x** |
| `edge_case_contains_not_contains` | Edge Case — Substring | 2 / 1 | 578.181 µs/op (core 561.387 µs/op) | 14.669 µs/op (core 7.125 µs/op) | **5.76 µs/op (core 3.91 µs/op)** | 8.858 µs/op (core 6.915 µs/op) | **100.38x** | **65.27x** | **1.54x** |
| `edge_case_collection_all_and_none` | Edge Case — Collection All/None | 1 / 2 | 469.711 µs/op (core 452.434 µs/op) | 14.391 µs/op (core 6.653 µs/op) | **7.239 µs/op (core 5.347 µs/op)** | 10.858 µs/op (core 8.875 µs/op) | **64.89x** | **43.26x** | **1.5x** |
| `edge_case_length_gt_eq` | Edge Case — Length | 1 / 1 | 215.705 µs/op (core 202.14 µs/op) | 9.935 µs/op (core 2.486 µs/op) | **4.029 µs/op (core 2.298 µs/op)** | 5.972 µs/op (core 4.147 µs/op) | **53.54x** | **36.12x** | **1.48x** |
| `edge_case_has_changed` | Edge Case — Field Change | 1 / 1 | INVALID | INVALID | **INVALID** | INVALID | N/A | N/A | N/A |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 1 / 1 | 307.881 µs/op (core 292.99 µs/op) | 10.659 µs/op (core 3.005 µs/op) | **3.126 µs/op (core 1.411 µs/op)** | 4.825 µs/op (core 2.999 µs/op) | **98.49x** | **63.81x** | **1.54x** |

---

## 4. Preparation Timings

Preparation time measured separately outside the execution loop:

| Fixture ID | Approach A Prep (ms) | Approach B Prep (ms) | Approach C Prep (ms) |
|---|---|---|---|
| `tier1_simple_equality` | 0.0928 ms | **0.0163 ms** | 0.0016 ms |
| `tier2_typical_business_rule` | 0.2197 ms | **0.0279 ms** | 0.002 ms |
| `tier3_nested_and_or_groups` | 0.2742 ms | **0.0348 ms** | 0.0019 ms |
| `tier4_deep_nested_complex` | 0.6079 ms | **0.0528 ms** | 0.0019 ms |
| `tier5_collection_child_records` | 0.3302 ms | **0.0342 ms** | 0.002 ms |
| `edge_case_is_set_null_empty` | 0.1452 ms | **0.0152 ms** | 0.0018 ms |
| `edge_case_link_tuple` | 0.1375 ms | **0.0172 ms** | 0.0017 ms |
| `edge_case_membership_in_not_in` | 0.2037 ms | **0.0231 ms** | 0.0018 ms |
| `edge_case_contains_not_contains` | 0.3179 ms | **0.0223 ms** | 0.0018 ms |
| `edge_case_collection_all_and_none` | 0.1971 ms | **0.0226 ms** | 0.0019 ms |
| `edge_case_length_gt_eq` | 0.1181 ms | **0.0168 ms** | 0.0017 ms |
| `edge_case_has_changed` | 0.0435 ms | **0.0118 ms** | 0.0014 ms |
| `edge_case_none_vs_missing_field` | 0.1461 ms | **0.0158 ms** | 0.0017 ms |

---

## 5. Amortized Total Cost Measurements

Estimates one preparation plus N evaluations. Preparation time is the median of repeated samples; execution time is the median total duration across repeated N-evaluation batches. Fixtures that fail semantic parity are excluded. Core-only timing diagnostics are also retained in raw JSON.

$$\text{Total Amortized Cost} = \text{Preparation Time} + (N \times \text{Execution Time})$$

| Fixture ID | N Evaluations | Approach A Total Cost (ms) | Approach B Total Cost (ms) | Approach A Cost/Eval (µs) | Approach B Cost/Eval (µs) |
|---|---|---|---|---|---|
| `tier1_simple_equality` | N = 1 | 0.2787 ms | **0.0226 ms** | 278.698 µs | **22.634 µs** |
| `tier1_simple_equality` | N = 10 | 1.9361 ms | **0.0597 ms** | 193.606 µs | **5.967 µs** |
| `tier1_simple_equality` | N = 100 | 17.6631 ms | **0.4357 ms** | 176.631 µs | **4.357 µs** |
| `tier1_simple_equality` | N = 1000 | 176.0337 ms | **3.7687 ms** | 176.034 µs | **3.769 µs** |
| `tier2_typical_business_rule` | N = 1 | 0.6261 ms | **0.0411 ms** | 626.105 µs | **41.062 µs** |
| `tier2_typical_business_rule` | N = 10 | 4.316 ms | **0.0995 ms** | 431.604 µs | **9.952 µs** |
| `tier2_typical_business_rule` | N = 100 | 40.9152 ms | **0.6764 ms** | 409.152 µs | **6.764 µs** |
| `tier2_typical_business_rule` | N = 1000 | 416.3634 ms | **6.3262 ms** | 416.363 µs | **6.326 µs** |
| `tier3_nested_and_or_groups` | N = 1 | 0.8801 ms | **0.0564 ms** | 880.073 µs | **56.418 µs** |
| `tier3_nested_and_or_groups` | N = 10 | 5.7991 ms | **0.1149 ms** | 579.915 µs | **11.495 µs** |
| `tier3_nested_and_or_groups` | N = 100 | 54.3759 ms | **0.7374 ms** | 543.759 µs | **7.374 µs** |
| `tier3_nested_and_or_groups` | N = 1000 | 537.3958 ms | **6.6905 ms** | 537.396 µs | **6.691 µs** |
| `tier4_deep_nested_complex` | N = 1 | 1.7171 ms | **0.0813 ms** | 1717.116 µs | **81.33 µs** |
| `tier4_deep_nested_complex` | N = 10 | 11.7519 ms | **0.173 ms** | 1175.194 µs | **17.304 µs** |
| `tier4_deep_nested_complex` | N = 100 | 113.0873 ms | **1.0749 ms** | 1130.873 µs | **10.749 µs** |
| `tier4_deep_nested_complex` | N = 1000 | 1141.9197 ms | **10.2642 ms** | 1141.92 µs | **10.264 µs** |
| `tier5_collection_child_records` | N = 1 | 1.0766 ms | **0.0609 ms** | 1076.606 µs | **60.907 µs** |
| `tier5_collection_child_records` | N = 10 | 7.4916 ms | **0.1567 ms** | 749.158 µs | **15.673 µs** |
| `tier5_collection_child_records` | N = 100 | 71.186 ms | **1.1059 ms** | 711.86 µs | **11.059 µs** |
| `tier5_collection_child_records` | N = 1000 | 705.1352 ms | **10.5284 ms** | 705.135 µs | **10.528 µs** |
| `edge_case_is_set_null_empty` | N = 1 | 0.447 ms | **0.0245 ms** | 446.975 µs | **24.517 µs** |
| `edge_case_is_set_null_empty` | N = 10 | 3.3377 ms | **0.0564 ms** | 333.766 µs | **5.641 µs** |
| `edge_case_is_set_null_empty` | N = 100 | 30.8987 ms | **0.3591 ms** | 308.987 µs | **3.591 µs** |
| `edge_case_is_set_null_empty` | N = 1000 | 309.1895 ms | **3.1698 ms** | 309.189 µs | **3.17 µs** |
| `edge_case_link_tuple` | N = 1 | 0.3909 ms | **0.0278 ms** | 390.852 µs | **27.775 µs** |
| `edge_case_link_tuple` | N = 10 | 2.7641 ms | **0.077 ms** | 276.407 µs | **7.701 µs** |
| `edge_case_link_tuple` | N = 100 | 24.9199 ms | **0.5254 ms** | 249.199 µs | **5.254 µs** |
| `edge_case_link_tuple` | N = 1000 | 244.8524 ms | **5.3412 ms** | 244.852 µs | **5.341 µs** |
| `edge_case_membership_in_not_in` | N = 1 | 0.6144 ms | **0.037 ms** | 614.443 µs | **37.025 µs** |
| `edge_case_membership_in_not_in` | N = 10 | 3.8805 ms | **0.0812 ms** | 388.046 µs | **8.117 µs** |
| `edge_case_membership_in_not_in` | N = 100 | 37.2994 ms | **0.5298 ms** | 372.994 µs | **5.298 µs** |
| `edge_case_membership_in_not_in` | N = 1000 | 376.3991 ms | **5.064 ms** | 376.399 µs | **5.064 µs** |
| `edge_case_contains_not_contains` | N = 1 | 0.9207 ms | **0.0363 ms** | 920.661 µs | **36.305 µs** |
| `edge_case_contains_not_contains` | N = 10 | 6.1219 ms | **0.089 ms** | 612.192 µs | **8.901 µs** |
| `edge_case_contains_not_contains` | N = 100 | 58.2944 ms | **0.6179 ms** | 582.944 µs | **6.179 µs** |
| `edge_case_contains_not_contains` | N = 1000 | 578.533 ms | **5.8431 ms** | 578.533 µs | **5.843 µs** |
| `edge_case_collection_all_and_none` | N = 1 | 0.681 ms | **0.0389 ms** | 681.03 µs | **38.916 µs** |
| `edge_case_collection_all_and_none` | N = 10 | 4.8397 ms | **0.1031 ms** | 483.967 µs | **10.307 µs** |
| `edge_case_collection_all_and_none` | N = 100 | 46.271 ms | **0.7106 ms** | 462.71 µs | **7.106 µs** |
| `edge_case_collection_all_and_none` | N = 1000 | 463.3247 ms | **7.2578 ms** | 463.325 µs | **7.258 µs** |
| `edge_case_length_gt_eq` | N = 1 | 0.3387 ms | **0.0246 ms** | 338.727 µs | **24.563 µs** |
| `edge_case_length_gt_eq` | N = 10 | 2.2888 ms | **0.0622 ms** | 228.876 µs | **6.218 µs** |
| `edge_case_length_gt_eq` | N = 100 | 21.1473 ms | **0.4388 ms** | 211.473 µs | **4.388 µs** |
| `edge_case_length_gt_eq` | N = 1000 | 216.3843 ms | **4.0483 ms** | 216.384 µs | **4.048 µs** |
| `edge_case_has_changed` | N = 1 | ERR | **ERR** | ERR | **ERR** |
| `edge_case_has_changed` | N = 10 | ERR | **ERR** | ERR | **ERR** |
| `edge_case_has_changed` | N = 100 | ERR | **ERR** | ERR | **ERR** |
| `edge_case_has_changed` | N = 1000 | ERR | **ERR** | ERR | **ERR** |
| `edge_case_none_vs_missing_field` | N = 1 | 0.4778 ms | **0.0248 ms** | 477.815 µs | **24.804 µs** |
| `edge_case_none_vs_missing_field` | N = 10 | 3.1949 ms | **0.0543 ms** | 319.488 µs | **5.428 µs** |
| `edge_case_none_vs_missing_field` | N = 100 | 30.4927 ms | **0.3499 ms** | 304.927 µs | **3.499 µs** |
| `edge_case_none_vs_missing_field` | N = 1000 | 304.2315 ms | **3.1754 ms** | 304.232 µs | **3.175 µs** |

---

## 6. Architectural Analysis & Diagnostic Note

1. **Approach A Experimental Code-Object Diagnostic:** Evaluating precompiled RestrictedPython code objects via `eval(code_obj)` eliminates string parsing and AST compilation overhead. However, it is labeled strictly as a **lower-level diagnostic**, NOT as the primary production `frappe.safe_eval` result, because standard Frappe APIs do not expose code object caching.
2. **Coverage Scope:** 12 of 13 fixtures passed semantic correctness tests. Fixtures that fail the gate are excluded from performance measurements. A finite fixture suite does not prove universal equivalence for all possible condition expressions; edge cases and untested operators still require verification.
3. **Production Isolation Confirmation:** **No production code, evaluators, controllers, persistence contracts, or DocTypes were modified.** All candidate evaluators and test harnesses reside isolated in `flexirule/ruleflow/tests/condition_benchmark/`.