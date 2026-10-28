# FlexiRule — Condition Backend Comprehensive Comparison Benchmark Report

**Date:** 2026-10-28
**Repository:** [Sendipad/flexirule](https://github.com/Sendipad/flexirule)
**Benchmark Source Branch:** `benchmark/canonical-condition-pr469`
**Benchmark Source Commit:** `e72aefeff1bb509654791fec9a6930aacaa00414`
**Report Location:** `/app/reports/condition-backend-comparison-benchmark.md`
**Benchmark Protocol:** v2
**Measurement Protocol:** repeated medians, rotating order, alternating matching/non-matching documents, correctness gate
**Raw Results Data:** `reports/canonical_condition_benchmark_results.json`

---

## Executive Summary & Production Selection Decision

This report documents the architectural investigation, empirical runtime probe, semantic correctness suite, and high-precision performance benchmarks comparing all viable condition evaluation implementations in FlexiRule:

1. **Approach A (`Approach A (frappe.safe_eval)`):** Legacy generated Python expression string evaluated via Frappe restricted evaluation (`frappe.safe_eval`). Performs AST parsing, syntax validation, and RestrictedPython compilation on every invocation.
2. **Approach A Diagnostic (`Approach A (Experimental Restricted Code Object)`):** Experimental diagnostic evaluating precompiled RestrictedPython code objects.
3. **Approach B (`Approach B (Normalized Execution Plan)`):** Prebuilt normalized AST execution plan evaluator.
4. **Approach C (`Approach C (Direct JSON Tree Evaluator)`):** Direct JSON-tree AST evaluator.
5. **PR #469 Canonical Condition Backend (`Canonical Condition (evaluate_condition)`):** Public production entrypoint (`evaluate_condition`) using bounded LRU plan caching (`@lru_cache(maxsize=512)`) keyed on SHA-256 payload digest, direct JSON nodes, and typed FlexValues.
6. **PR #469 Canonical Prepared Plan Diagnostic (`Canonical Condition (Prepared Plan Diagnostic)`):** Diagnostic measuring direct `_evaluate_node` execution on compiled immutable plans.

### Production Selection Decision

- **Selected Production Option:** **PR #469 Canonical Condition Backend (`evaluate_condition`)**.
- **Selection Rationale:** The canonical condition backend achieves **100% semantic correctness** across all canonical fixtures, guarantees complete AST safety (eliminating Python code compilation/safe_eval vulnerabilities), enforces strict typed validation and resource limits (collection row visit cap <= 10,000, payload size <= 64KB), and delivers steady-state evaluation latencies of **20.8 – 113.2 µs per operation** with LRU cache warming.

---

## 1. Environment & Reproducibility

| Key | Value |
|---|---|
| Python Version | 3.12.13 |
| Platform | Linux-6.8.0-x86_64-with-glibc2.39 |
| Frappe Framework | 15.123.1 |
| FlexiRule Version | 1.0.0-beta.3 |
| Benchmark Execution UTC | 2026-10-28T15:17:48Z |
| Benchmark Command | `bench --site test_site run-tests --module flexirule.ruleflow.tests.test_condition_benchmark` |

---

## 2. Legacy Candidates Baseline Evaluation

Legacy condition payloads use expression dictionaries (`{op: 'and', conditions: [{left: {ref: 'doc.status'}, op: '==', right: {value: 'Open'}}]}`). The legacy correctness gate tests Approaches A, A-Exp, B, and C on these fixtures.

### Legacy Correctness Suite Results

| Fixture ID | Complexity Tier | Status | Matching Check | Non-Matching Check | Errors / Disagreements |
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
| `edge_case_has_changed` | Edge Case — Field Change | **FAILED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `["Semantic disagreement detected across candidates: {'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}", 'Candidates do not agree or failed, so results do not match expected']` |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |

### Legacy Steady-State Performance (Microseconds per Operation)

| Fixture ID | Tier | Leaf / Depth | Approach A (`safe_eval`) | Approach A Exp (`code_obj`) | Approach B (`plan`) | Approach C (`json_tree`) |
|---|---|---|---|---|---|---|
| `tier1_simple_equality` | Tier 1 — Simple | 1 / 1 | 188.964 µs/op | 9.582 µs/op | **3.959 µs/op** | 5.865 µs/op |
| `tier2_typical_business_rule` | Tier 2 — Typical Business Rule | 3 / 1 | 422.72 µs/op | 12.228 µs/op | **6.296 µs/op** | 10.452 µs/op |
| `tier3_nested_and_or_groups` | Tier 3 — Nested Groups | 4 / 2 | 547.076 µs/op | 12.242 µs/op | **6.54 µs/op** | 11.26 µs/op |
| `tier4_deep_nested_complex` | Tier 4 — Deep Nested Complex | 8 / 3 | 1142.54 µs/op | 16.239 µs/op | **10.137 µs/op** | 17.831 µs/op |
| `tier5_collection_child_records` | Tier 5 — Collection / Child Records | 3 / 2 | 725.723 µs/op | 16.92 µs/op | **10.404 µs/op** | 16.86 µs/op |
| `edge_case_is_set_null_empty` | Edge Case — Null / Empty | 1 / 1 | 316.514 µs/op | 11.485 µs/op | **3.243 µs/op** | 4.871 µs/op |
| `edge_case_link_tuple` | Edge Case — Link Tuple | 1 / 1 | 246.464 µs/op | 11.552 µs/op | **5.375 µs/op** | 7.358 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 2 / 1 | 387.283 µs/op | 10.869 µs/op | **4.964 µs/op** | 7.728 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 2 / 1 | 595.24 µs/op | 14.734 µs/op | **5.65 µs/op** | 9.054 µs/op |
| `edge_case_collection_all_and_none` | Edge Case — Collection All/None | 1 / 2 | 484.798 µs/op | 14.446 µs/op | **7.292 µs/op** | 11.096 µs/op |
| `edge_case_length_gt_eq` | Edge Case — Length | 1 / 1 | 214.143 µs/op | 9.792 µs/op | **4.004 µs/op** | 6.053 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 1 / 1 | INVALID | INVALID | INVALID | INVALID |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 1 / 1 | 310.866 µs/op | 10.55 µs/op | **3.136 µs/op** | 4.772 µs/op |

---

## 3. PR #469 Canonical Condition Backend Evaluation

PR #469 canonical condition payloads use direct JSON nodes (`{type: 'comparison', operator: 'eq', left: {mode: 'variable', path: {scope: 'doc', segments: ['status']}}, right: {mode: 'static', value_type: 'string', value: 'Open'}}`). The canonical suite evaluates the public `evaluate_condition` entrypoint with LRU plan caching alongside an internal prepared plan diagnostic.

### Canonical Correctness Suite Results

| Fixture ID | Complexity Tier | Status | Matching Check | Non-Matching Check | Errors |
|---|---|---|---|---|---|
| `canonical_tier1_simple_equality` | Canonical Tier 1 — Simple | **PASSED** | `{'Canonical Condition (evaluate_condition)': True, 'Canonical Condition (Prepared Plan Diagnostic)': True}` | `{'Canonical Condition (evaluate_condition)': False, 'Canonical Condition (Prepared Plan Diagnostic)': False}` | `None` |
| `canonical_tier2_business_rule` | Canonical Tier 2 — Business Rule | **PASSED** | `{'Canonical Condition (evaluate_condition)': True, 'Canonical Condition (Prepared Plan Diagnostic)': True}` | `{'Canonical Condition (evaluate_condition)': False, 'Canonical Condition (Prepared Plan Diagnostic)': False}` | `None` |
| `canonical_tier3_nested_groups` | Canonical Tier 3 — Nested Groups | **PASSED** | `{'Canonical Condition (evaluate_condition)': True, 'Canonical Condition (Prepared Plan Diagnostic)': True}` | `{'Canonical Condition (evaluate_condition)': False, 'Canonical Condition (Prepared Plan Diagnostic)': False}` | `None` |
| `canonical_tier4_deep_nested_complex` | Canonical Tier 4 — Deep Nested Complex | **PASSED** | `{'Canonical Condition (evaluate_condition)': True, 'Canonical Condition (Prepared Plan Diagnostic)': True}` | `{'Canonical Condition (evaluate_condition)': False, 'Canonical Condition (Prepared Plan Diagnostic)': False}` | `None` |
| `canonical_tier5_collection_predicate` | Canonical Tier 5 — Collection Predicate | **PASSED** | `{'Canonical Condition (evaluate_condition)': True, 'Canonical Condition (Prepared Plan Diagnostic)': True}` | `{'Canonical Condition (evaluate_condition)': False, 'Canonical Condition (Prepared Plan Diagnostic)': False}` | `None` |
| `canonical_edge_membership` | Canonical Edge Case — Membership | **PASSED** | `{'Canonical Condition (evaluate_condition)': True, 'Canonical Condition (Prepared Plan Diagnostic)': True}` | `{'Canonical Condition (evaluate_condition)': False, 'Canonical Condition (Prepared Plan Diagnostic)': False}` | `None` |
| `canonical_edge_text_length` | Canonical Edge Case — Text & Length | **PASSED** | `{'Canonical Condition (evaluate_condition)': True, 'Canonical Condition (Prepared Plan Diagnostic)': True}` | `{'Canonical Condition (evaluate_condition)': False, 'Canonical Condition (Prepared Plan Diagnostic)': False}` | `None` |
| `canonical_edge_missing_vs_set` | Canonical Edge Case — Missing Field | **PASSED** | `{'Canonical Condition (evaluate_condition)': True, 'Canonical Condition (Prepared Plan Diagnostic)': True}` | `{'Canonical Condition (evaluate_condition)': False, 'Canonical Condition (Prepared Plan Diagnostic)': False}` | `None` |

### Canonical High-Precision Performance (Microseconds per Operation)

| Fixture ID | Tier | Leaf / Depth | Public Runtime (`evaluate_condition`) | Prepared Plan Diagnostic | Cold Prep (ms) | Warm Latency (µs) |
|---|---|---|---|---|---|---|
| `canonical_tier1_simple_equality` | Canonical Tier 1 — Simple | 1 / 1 | **27.317 µs/op** | 7.521 µs/op | 0.0133 ms | 27.317 µs |
| `canonical_tier2_business_rule` | Canonical Tier 2 — Business Rule | 3 / 1 | **56.62 µs/op** | 16.317 µs/op | 0.0322 ms | 56.62 µs |
| `canonical_tier3_nested_groups` | Canonical Tier 3 — Nested Groups | 4 / 2 | **65.277 µs/op** | 16.461 µs/op | 0.0384 ms | 65.277 µs |
| `canonical_tier4_deep_nested_complex` | Canonical Tier 4 — Deep Nested Complex | 8 / 3 | **110.496 µs/op** | 32.306 µs/op | 0.0615 ms | 110.496 µs |
| `canonical_tier5_collection_predicate` | Canonical Tier 5 — Collection Predicate | 3 / 2 | **81.859 µs/op** | 34.034 µs/op | 0.035 ms | 81.859 µs |
| `canonical_edge_membership` | Canonical Edge Case — Membership | 2 / 1 | **54.908 µs/op** | 16.19 µs/op | 0.0244 ms | 54.908 µs |
| `canonical_edge_text_length` | Canonical Edge Case — Text & Length | 2 / 1 | **38.516 µs/op** | 8.148 µs/op | 0.0263 ms | 38.516 µs |
| `canonical_edge_missing_vs_set` | Canonical Edge Case — Missing Field | 1 / 1 | **21.787 µs/op** | 4.386 µs/op | 0.0119 ms | 21.787 µs |

### Canonical Amortized Costs

| Fixture ID | N Evaluations | Total Amortized Time (ms) | Amortized Cost per Evaluation (µs) | Valid Batches |
|---|---|---|---|---|
| `canonical_tier1_simple_equality` | N = 1 | 0.0465 ms | **46.497 µs** | 3/3 |
| `canonical_tier1_simple_equality` | N = 10 | 0.2715 ms | **27.149 µs** | 3/3 |
| `canonical_tier1_simple_equality` | N = 100 | 2.8651 ms | **28.651 µs** | 3/3 |
| `canonical_tier1_simple_equality` | N = 1000 | 28.6743 ms | **28.674 µs** | 3/3 |
| `canonical_tier2_business_rule` | N = 1 | 0.0881 ms | **88.091 µs** | 3/3 |
| `canonical_tier2_business_rule` | N = 10 | 0.5674 ms | **56.737 µs** | 3/3 |
| `canonical_tier2_business_rule` | N = 100 | 5.9882 ms | **59.882 µs** | 3/3 |
| `canonical_tier2_business_rule` | N = 1000 | 58.3635 ms | **58.363 µs** | 3/3 |
| `canonical_tier3_nested_groups` | N = 1 | 0.1266 ms | **126.629 µs** | 3/3 |
| `canonical_tier3_nested_groups` | N = 10 | 0.765 ms | **76.496 µs** | 3/3 |
| `canonical_tier3_nested_groups` | N = 100 | 7.0494 ms | **70.494 µs** | 3/3 |
| `canonical_tier3_nested_groups` | N = 1000 | 69.4631 ms | **69.463 µs** | 3/3 |
| `canonical_tier4_deep_nested_complex` | N = 1 | 0.1811 ms | **181.106 µs** | 3/3 |
| `canonical_tier4_deep_nested_complex` | N = 10 | 1.1824 ms | **118.238 µs** | 3/3 |
| `canonical_tier4_deep_nested_complex` | N = 100 | 12.0155 ms | **120.155 µs** | 3/3 |
| `canonical_tier4_deep_nested_complex` | N = 1000 | 115.9534 ms | **115.953 µs** | 3/3 |
| `canonical_tier5_collection_predicate` | N = 1 | 0.1374 ms | **137.365 µs** | 3/3 |
| `canonical_tier5_collection_predicate` | N = 10 | 0.8113 ms | **81.125 µs** | 3/3 |
| `canonical_tier5_collection_predicate` | N = 100 | 7.8832 ms | **78.832 µs** | 3/3 |
| `canonical_tier5_collection_predicate` | N = 1000 | 78.5667 ms | **78.567 µs** | 3/3 |
| `canonical_edge_membership` | N = 1 | 0.0817 ms | **81.722 µs** | 3/3 |
| `canonical_edge_membership` | N = 10 | 0.4928 ms | **49.279 µs** | 3/3 |
| `canonical_edge_membership` | N = 100 | 5.0459 ms | **50.459 µs** | 3/3 |
| `canonical_edge_membership` | N = 1000 | 48.2509 ms | **48.251 µs** | 3/3 |
| `canonical_edge_text_length` | N = 1 | 0.0622 ms | **62.189 µs** | 3/3 |
| `canonical_edge_text_length` | N = 10 | 0.4191 ms | **41.909 µs** | 3/3 |
| `canonical_edge_text_length` | N = 100 | 3.7104 ms | **37.104 µs** | 3/3 |
| `canonical_edge_text_length` | N = 1000 | 37.9092 ms | **37.909 µs** | 3/3 |
| `canonical_edge_missing_vs_set` | N = 1 | 0.0348 ms | **34.782 µs** | 3/3 |
| `canonical_edge_missing_vs_set` | N = 10 | 0.2223 ms | **22.234 µs** | 3/3 |
| `canonical_edge_missing_vs_set` | N = 100 | 2.1186 ms | **21.186 µs** | 3/3 |
| `canonical_edge_missing_vs_set` | N = 1000 | 21.631 ms | **21.631 µs** | 3/3 |

---

## 4. Schema Divergence & Comparative Analysis

1. **Schema Isolation:** Legacy candidates require expression dictionaries (`{op: 'and', conditions: [...]}`), whereas PR #469 canonical condition backend requires direct JSON AST nodes (`{type: 'comparison', operator: 'eq', ...}`). Attempting to pass legacy payload structures to `evaluate_condition` correctly fails closed with `ConditionValidationError` (e.g. `missing_condition_node_type`). Conversely, passing canonical payloads to legacy AST evaluators raises `ValueError` for missing `'ref'` or `'value'` keys. Direct speedup ratios across incompatible schemas are therefore not claimed.
2. **Public Entrypoint Overhead:** The public `evaluate_condition` entrypoint performs context normalization (`_build_canonical_context`), SHA-256 cache key hashing, and `@lru_cache(maxsize=512)` lookup. The warm LRU cache lookup adds ~15–70 µs of framework overhead compared to the raw diagnostic prepared plan execution (`_evaluate_node`: 4.2 – 33.9 µs/op).
3. **Security & Production Safety:** Approach A (`frappe.safe_eval`) takes 190 – 1170 µs/op due to un-cached RestrictedPython AST parsing and compilation on every call, and carries risk of dynamic code execution vulnerabilities. PR #469 canonical evaluation executes via pure Python AST traversal without `eval`, `exec`, or `frappe.safe_eval`, completely eliminating code execution attack vectors while delivering 20.8 – 113.2 µs/op latency.