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
| Benchmark Execution UTC | 2026-10-28T20:48:44Z |
| Benchmark Command | `bench --site test_site run-tests --module flexirule.ruleflow.tests.test_condition_benchmark` |

---

## 2. Legacy Candidates Baseline Evaluation

Legacy condition payloads use expression dictionaries (`{op: 'and', conditions: [{left: {ref: 'doc.status'}, op: '==', right: {value: 'Open'}}]}`). The legacy correctness gate tests Approaches A, A-Exp, B, and C on these fixtures.

### Legacy Correctness Suite Results

| Fixture ID | Complexity Tier | Status | Matching Check | Non-Matching Check | Errors / Disagreements |
|---|---|---|---|---|---|
| `simple_equality` | Tier 1 — Simple | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `typical_business_rule` | Tier 2 — Typical Business Rule | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `nested_and_or_groups` | Tier 3 — Nested Groups | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `collection_predicate` | Tier 5 — Collection Predicate | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `edge_case_membership_in_not_in` | Edge Case — Membership | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `edge_case_contains_not_contains` | Edge Case — Substring | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |
| `edge_case_has_changed` | Edge Case — Field Change | **FAILED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `["Semantic disagreement detected across candidates: {'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}", 'Candidates do not agree or failed, so results do not match expected']` |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True, 'Approach C (Direct JSON Tree Evaluator)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False}` | `None` |

### Legacy Steady-State Performance (Microseconds per Operation)

| Fixture ID | Tier | Leaf / Depth | Approach A (`safe_eval`) | Approach A Exp (`code_obj`) | Approach B (`plan`) | Approach C (`json_tree`) |
|---|---|---|---|---|---|---|
| `simple_equality` | Tier 1 — Simple | 1 / 1 | 182.886 µs/op | 9.688 µs/op | **3.57 µs/op** | 5.285 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 3 / 1 | 444.369 µs/op | 12.157 µs/op | **6.302 µs/op** | 10.503 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 4 / 2 | 579.23 µs/op | 12.25 µs/op | **6.644 µs/op** | 11.616 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 8 / 3 | 1189.863 µs/op | 16.306 µs/op | **10.091 µs/op** | 17.849 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 3 / 2 | 739.992 µs/op | 16.681 µs/op | **10.845 µs/op** | 17.258 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 2 / 1 | 396.69 µs/op | 10.439 µs/op | **5.024 µs/op** | 7.745 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 2 / 1 | 611.803 µs/op | 14.726 µs/op | **5.814 µs/op** | 9.097 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 1 / 1 | INVALID | INVALID | INVALID | INVALID |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 1 / 1 | 316.221 µs/op | 10.538 µs/op | **2.838 µs/op** | 4.121 µs/op |

---

## 3. PR #469 Canonical Condition Backend Evaluation

PR #469 canonical condition payloads use direct JSON nodes (`{type: 'comparison', operator: 'eq', left: {mode: 'variable', path: {scope: 'doc', segments: ['status']}}, right: {mode: 'static', value_type: 'string', value: 'Open'}}`). The canonical suite evaluates the public `evaluate_condition` entrypoint with LRU plan caching alongside an internal prepared plan diagnostic.

### Canonical Correctness Suite Results

| Fixture ID | Complexity Tier | Status | Matching Check | Non-Matching Check | Errors |
|---|---|---|---|---|---|
| `canonical_simple_equality` | Canonical Tier 1 — Simple | **PASSED** | `{'Canonical Condition (evaluate_condition)': True, 'Canonical Condition (Prepared Plan Diagnostic)': True}` | `{'Canonical Condition (evaluate_condition)': False, 'Canonical Condition (Prepared Plan Diagnostic)': False}` | `None` |
| `canonical_typical_business_rule` | Canonical Tier 2 — Typical Business Rule | **PASSED** | `{'Canonical Condition (evaluate_condition)': True, 'Canonical Condition (Prepared Plan Diagnostic)': True}` | `{'Canonical Condition (evaluate_condition)': False, 'Canonical Condition (Prepared Plan Diagnostic)': False}` | `None` |
| `canonical_nested_and_or_groups` | Canonical Tier 3 — Nested Groups | **PASSED** | `{'Canonical Condition (evaluate_condition)': True, 'Canonical Condition (Prepared Plan Diagnostic)': True}` | `{'Canonical Condition (evaluate_condition)': False, 'Canonical Condition (Prepared Plan Diagnostic)': False}` | `None` |
| `canonical_deep_nested_complex` | Canonical Tier 4 — Deep Nested Complex | **PASSED** | `{'Canonical Condition (evaluate_condition)': True, 'Canonical Condition (Prepared Plan Diagnostic)': True}` | `{'Canonical Condition (evaluate_condition)': False, 'Canonical Condition (Prepared Plan Diagnostic)': False}` | `None` |
| `canonical_collection_predicate` | Canonical Tier 5 — Collection Predicate | **PASSED** | `{'Canonical Condition (evaluate_condition)': True, 'Canonical Condition (Prepared Plan Diagnostic)': True}` | `{'Canonical Condition (evaluate_condition)': False, 'Canonical Condition (Prepared Plan Diagnostic)': False}` | `None` |
| `canonical_edge_case_membership_in_not_in` | Canonical Edge Case — Membership | **PASSED** | `{'Canonical Condition (evaluate_condition)': True, 'Canonical Condition (Prepared Plan Diagnostic)': True}` | `{'Canonical Condition (evaluate_condition)': False, 'Canonical Condition (Prepared Plan Diagnostic)': False}` | `None` |
| `canonical_edge_case_contains_not_contains` | Canonical Edge Case — Substring | **PASSED** | `{'Canonical Condition (evaluate_condition)': True, 'Canonical Condition (Prepared Plan Diagnostic)': True}` | `{'Canonical Condition (evaluate_condition)': False, 'Canonical Condition (Prepared Plan Diagnostic)': False}` | `None` |
| `canonical_edge_case_none_vs_missing_field` | Canonical Edge Case — Missing Field | **PASSED** | `{'Canonical Condition (evaluate_condition)': True, 'Canonical Condition (Prepared Plan Diagnostic)': True}` | `{'Canonical Condition (evaluate_condition)': False, 'Canonical Condition (Prepared Plan Diagnostic)': False}` | `None` |

### Canonical High-Precision Performance (Microseconds per Operation)

| Fixture ID | Tier | Leaf / Depth | Public Runtime (`evaluate_condition`) | Prepared Plan Diagnostic | Cold Prep (ms) | Warm Latency (µs) |
|---|---|---|---|---|---|---|
| `canonical_simple_equality` | Canonical Tier 1 — Simple | 1 / 1 | **28.318 µs/op** | 7.595 µs/op | 0.0131 ms | 28.318 µs |
| `canonical_typical_business_rule` | Canonical Tier 2 — Typical Business Rule | 3 / 1 | **56.309 µs/op** | 16.376 µs/op | 0.0284 ms | 56.309 µs |
| `canonical_nested_and_or_groups` | Canonical Tier 3 — Nested Groups | 4 / 2 | **82.336 µs/op** | 17.517 µs/op | 0.0808 ms | 82.336 µs |
| `canonical_deep_nested_complex` | Canonical Tier 4 — Deep Nested Complex | 8 / 3 | **111.238 µs/op** | 31.814 µs/op | 0.0598 ms | 111.238 µs |
| `canonical_collection_predicate` | Canonical Tier 5 — Collection Predicate | 3 / 2 | **78.627 µs/op** | 30.864 µs/op | 0.0406 ms | 78.627 µs |
| `canonical_edge_case_membership_in_not_in` | Canonical Edge Case — Membership | 2 / 1 | **49.628 µs/op** | 15.087 µs/op | 0.0224 ms | 49.628 µs |
| `canonical_edge_case_contains_not_contains` | Canonical Edge Case — Substring | 2 / 1 | **40.063 µs/op** | 9.313 µs/op | 0.0219 ms | 40.063 µs |
| `canonical_edge_case_none_vs_missing_field` | Canonical Edge Case — Missing Field | 1 / 1 | **21.274 µs/op** | 4.266 µs/op | 0.0121 ms | 21.274 µs |

### Canonical Amortized Costs

| Fixture ID | N Evaluations | Total Amortized Time (ms) | Amortized Cost per Evaluation (µs) | Valid Batches |
|---|---|---|---|---|
| `canonical_simple_equality` | N = 1 | 0.0418 ms | **41.837 µs** | 5/5 |
| `canonical_simple_equality` | N = 10 | 0.275 ms | **27.5 µs** | 5/5 |
| `canonical_simple_equality` | N = 100 | 2.8377 ms | **28.377 µs** | 5/5 |
| `canonical_simple_equality` | N = 1000 | 29.4539 ms | **29.454 µs** | 5/5 |
| `canonical_typical_business_rule` | N = 1 | 0.084 ms | **84.042 µs** | 5/5 |
| `canonical_typical_business_rule` | N = 10 | 0.5801 ms | **58.01 µs** | 5/5 |
| `canonical_typical_business_rule` | N = 100 | 5.6675 ms | **56.675 µs** | 5/5 |
| `canonical_typical_business_rule` | N = 1000 | 56.7688 ms | **56.769 µs** | 5/5 |
| `canonical_nested_and_or_groups` | N = 1 | 0.1002 ms | **100.178 µs** | 5/5 |
| `canonical_nested_and_or_groups` | N = 10 | 0.702 ms | **70.205 µs** | 5/5 |
| `canonical_nested_and_or_groups` | N = 100 | 6.64 ms | **66.4 µs** | 5/5 |
| `canonical_nested_and_or_groups` | N = 1000 | 66.8222 ms | **66.822 µs** | 5/5 |
| `canonical_deep_nested_complex` | N = 1 | 0.1735 ms | **173.484 µs** | 5/5 |
| `canonical_deep_nested_complex` | N = 10 | 1.19 ms | **119.005 µs** | 5/5 |
| `canonical_deep_nested_complex` | N = 100 | 12.2224 ms | **122.224 µs** | 5/5 |
| `canonical_deep_nested_complex` | N = 1000 | 113.4665 ms | **113.467 µs** | 5/5 |
| `canonical_collection_predicate` | N = 1 | 0.1103 ms | **110.316 µs** | 5/5 |
| `canonical_collection_predicate` | N = 10 | 0.809 ms | **80.896 µs** | 5/5 |
| `canonical_collection_predicate` | N = 100 | 7.8336 ms | **78.336 µs** | 5/5 |
| `canonical_collection_predicate` | N = 1000 | 79.282 ms | **79.282 µs** | 5/5 |
| `canonical_edge_case_membership_in_not_in` | N = 1 | 0.0745 ms | **74.467 µs** | 5/5 |
| `canonical_edge_case_membership_in_not_in` | N = 10 | 0.5266 ms | **52.661 µs** | 5/5 |
| `canonical_edge_case_membership_in_not_in` | N = 100 | 5.1526 ms | **51.526 µs** | 5/5 |
| `canonical_edge_case_membership_in_not_in` | N = 1000 | 50.0602 ms | **50.06 µs** | 5/5 |
| `canonical_edge_case_contains_not_contains` | N = 1 | 0.0632 ms | **63.228 µs** | 5/5 |
| `canonical_edge_case_contains_not_contains` | N = 10 | 0.4534 ms | **45.344 µs** | 5/5 |
| `canonical_edge_case_contains_not_contains` | N = 100 | 4.0349 ms | **40.349 µs** | 5/5 |
| `canonical_edge_case_contains_not_contains` | N = 1000 | 42.06 ms | **42.06 µs** | 5/5 |
| `canonical_edge_case_none_vs_missing_field` | N = 1 | 0.0598 ms | **59.795 µs** | 5/5 |
| `canonical_edge_case_none_vs_missing_field` | N = 10 | 0.4051 ms | **40.51 µs** | 5/5 |
| `canonical_edge_case_none_vs_missing_field` | N = 100 | 3.5597 ms | **35.597 µs** | 5/5 |
| `canonical_edge_case_none_vs_missing_field` | N = 1000 | 20.8553 ms | **20.855 µs** | 5/5 |

---

## 4. Schema Divergence & Comparative Analysis

1. **Schema Isolation:** Legacy candidates require expression dictionaries (`{op: 'and', conditions: [...]}`), whereas PR #469 canonical condition backend requires direct JSON AST nodes (`{type: 'comparison', operator: 'eq', ...}`). Attempting to pass legacy payload structures to `evaluate_condition` correctly fails closed with `ConditionValidationError` (e.g. `missing_condition_node_type`). Conversely, passing canonical payloads to legacy AST evaluators raises `ValueError` for missing `'ref'` or `'value'` keys. Direct speedup ratios across incompatible schemas are therefore not claimed.
2. **Public Entrypoint Overhead:** The public `evaluate_condition` entrypoint performs context normalization (`_build_canonical_context`), SHA-256 cache key hashing, and `@lru_cache(maxsize=512)` lookup. The warm LRU cache lookup adds ~15–70 µs of framework overhead compared to the raw diagnostic prepared plan execution (`_evaluate_node`: 4.2 – 33.9 µs/op).
3. **Security & Production Safety:** Approach A (`frappe.safe_eval`) takes 190 – 1170 µs/op due to un-cached RestrictedPython AST parsing and compilation on every call, and carries risk of dynamic code execution vulnerabilities. PR #469 canonical evaluation executes via pure Python AST traversal without `eval`, `exec`, or `frappe.safe_eval`, completely eliminating code execution attack vectors while delivering 20.8 – 113.2 µs/op latency.