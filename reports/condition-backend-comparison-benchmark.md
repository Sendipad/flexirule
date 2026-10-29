# FlexiRule — Five-Approach Condition Backend Comparison Benchmark Report

**Date:** 2026-10-29T00:42:19Z
**Branch:** `jules-3100235434379853320-7a89fca0`
**Commit:** `5ce124cbc1b2a6b2b879af0f242a1ddc6e814a77`
**Working Tree Dirty:** `Yes`
**Provenance Note:** Working tree contains uncommitted changes; benchmark provenance captures HEAD commit plus uncommitted working tree state.
**Python:** 3.12.13
**Frappe Framework:** 15.123.1

## Production Selection Gate Status

- **Selected Production Option:** **Not established**
- **Gate Status:** Production selection remains Not established until explicit correctness, security, and performance criteria gates pass.

---

## 1. Candidate Evaluators Evaluated

### Core Production Approaches
| Candidate | Paradigm | Preparation Mechanism | Execution Path |
|---|---|---|---|
| **Approach A (`safe_eval`)** | Legacy Dynamic Eval | Python expr string | `frappe.safe_eval` (RestrictedPython parse on every call) |
| **Approach B (`plan`)** | Normalized AST Plan | Pre-compiled tuple AST | Direct AST recursive interpreter |
| **Approach C (`json_tree`)** | Direct JSON Evaluator | Pure JSON AST | Direct JSON tree walker |
| **Canonical (`evaluate_condition`)** | Public PR #469 Runtime | LRU-cached AST compilation | Public API with context normalization & cache lookup |

### Internal Diagnostic Baselines
| Candidate | Purpose | Preparation Mechanism | Execution Path |
|---|---|---|---|
| **Approach A Exp (`code_obj`)** | Isolated Bytecode Baseline | Pre-compiled bytecode | `eval(code_object)` |
| **Canonical (`Prepared Plan`)** | Isolated Plan Diagnostic | Direct compiled AST plan | Direct internal `_evaluate_node` execution |

---

## 2. Independent Semantic Correctness & Compatibility Suite

All five approaches were evaluated against neutral business scenarios. Supported scenarios passed: **8 / 8**.

| Scenario ID | Tier | Status | Matching Check | Non-Matching Check | Disagreements / Errors |
|---|---|---|---|---|---|
| `simple_equality` | Tier 1 — Simple | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Plan Diagnostic): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Plan Diagnostic): False</small>` | None |
| `typical_business_rule` | Tier 2 — Typical Business Rule | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Plan Diagnostic): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Plan Diagnostic): False</small>` | None |
| `nested_and_or_groups` | Tier 3 — Nested Groups | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Plan Diagnostic): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Plan Diagnostic): False</small>` | None |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Plan Diagnostic): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Plan Diagnostic): False</small>` | None |
| `collection_predicate` | Tier 5 — Collection Predicate | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Plan Diagnostic): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Plan Diagnostic): False</small>` | None |
| `edge_case_membership_in_not_in` | Edge Case — Membership | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Plan Diagnostic): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Plan Diagnostic): False</small>` | None |
| `edge_case_contains_not_contains` | Edge Case — Substring | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Plan Diagnostic): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Plan Diagnostic): False</small>` | None |
| `edge_case_has_changed` | Edge Case — Field Change | **DEPRECATED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract., Canonical Condition (Prepared Plan Diagnostic): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract.</small>` | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract., Canonical Condition (Prepared Plan Diagnostic): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract.</small>` | Candidate 'Approach A (frappe.safe_eval)' non-matching result (True) != expected (False) | Candidate 'Approach A (Experimental Restricted Code Object)' non-matching result (True) != expected (False) | Disagreement on non-matching doc: {'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False} | DEPRECATED: 'has_changed' operator behavior varies between deprecated legacy return 'True' and state-diff evaluators. |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Plan Diagnostic): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Plan Diagnostic): False</small>` | None |

---

## 3. Steady-State Execution Latency (Microseconds per Operation)

| Scenario ID | Tier | Approach A (`safe_eval`) | Approach B (`plan`) | Approach C (`json_tree`) | Canonical Runtime (`evaluate_condition`) | *Diagnostic: A Exp (`code_obj`)* | *Diagnostic: Canonical Plan* |
|---|---|---|---|---|---|---|---|
| `simple_equality` | Tier 1 — Simple | 169.728 µs/op | 3.622 µs/op | 5.294 µs/op | 27.921 µs/op | 9.629 µs/op | 7.745 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 417.2 µs/op | 6.378 µs/op | 10.789 µs/op | 56.099 µs/op | 12.005 µs/op | 16.239 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 551.935 µs/op | 6.856 µs/op | 11.481 µs/op | 64.46 µs/op | 12.164 µs/op | 16.068 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1140.134 µs/op | 10.345 µs/op | 17.877 µs/op | 112.255 µs/op | 15.996 µs/op | 32.106 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 713.995 µs/op | 10.795 µs/op | 16.959 µs/op | 77.009 µs/op | 16.633 µs/op | 30.301 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 377.611 µs/op | 5.119 µs/op | 7.701 µs/op | 49.32 µs/op | 10.361 µs/op | 15.344 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 582.351 µs/op | 6.222 µs/op | 9.329 µs/op | 39.719 µs/op | 14.904 µs/op | 9.427 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 94.935 µs/op | 5.574 µs/op | 9.27 µs/op | UNSUPPORTED | 11.633 µs/op | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 307.956 µs/op | 3.004 µs/op | 4.32 µs/op | 20.958 µs/op | 10.605 µs/op | 4.34 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.1149 ms | 0.1352 ms |
| `simple_equality` | Approach B (Normalized Execution Plan) | 0.0174 ms | 0.0105 ms |
| `simple_equality` | Approach C (Direct JSON Tree Evaluator) | 0.0042 ms | 0.0026 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.1111 ms | 0.0233 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.2119 ms | 0.2015 ms |
| `simple_equality` | Canonical Condition (Prepared Plan Diagnostic) | 0.0935 ms | 0.0207 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.4679 ms | 0.2128 ms |
| `typical_business_rule` | Approach B (Normalized Execution Plan) | 0.041 ms | 0.0204 ms |
| `typical_business_rule` | Approach C (Direct JSON Tree Evaluator) | 0.0053 ms | 0.0027 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.3215 ms | 0.0424 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.6466 ms | 0.5077 ms |
| `typical_business_rule` | Canonical Condition (Prepared Plan Diagnostic) | 0.1717 ms | 0.0944 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.4286 ms | 0.3231 ms |
| `nested_and_or_groups` | Approach B (Normalized Execution Plan) | 0.0475 ms | 0.0246 ms |
| `nested_and_or_groups` | Approach C (Direct JSON Tree Evaluator) | 0.0138 ms | 0.0025 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.3808 ms | 0.0564 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.6843 ms | 0.7828 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Plan Diagnostic) | 0.2307 ms | 0.0474 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 0.8592 ms | 0.6791 ms |
| `deep_nested_complex` | Approach B (Normalized Execution Plan) | 0.0661 ms | 0.0388 ms |
| `deep_nested_complex` | Approach C (Direct JSON Tree Evaluator) | 0.0056 ms | 0.0029 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.6935 ms | 0.0939 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.557 ms | 1.388 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Plan Diagnostic) | 0.3944 ms | 0.0756 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.5327 ms | 0.3251 ms |
| `collection_predicate` | Approach B (Normalized Execution Plan) | 0.1228 ms | 0.0273 ms |
| `collection_predicate` | Approach C (Direct JSON Tree Evaluator) | 0.0059 ms | 0.0483 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.3564 ms | 0.0895 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.9819 ms | 0.8951 ms |
| `collection_predicate` | Canonical Condition (Prepared Plan Diagnostic) | 0.2327 ms | 0.0445 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.3593 ms | 0.2586 ms |
| `edge_case_membership_in_not_in` | Approach B (Normalized Execution Plan) | 0.0372 ms | 0.0168 ms |
| `edge_case_membership_in_not_in` | Approach C (Direct JSON Tree Evaluator) | 0.0053 ms | 0.0027 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.2525 ms | 0.0363 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.5387 ms | 0.5204 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Plan Diagnostic) | 0.1582 ms | 0.0318 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.4919 ms | 0.2908 ms |
| `edge_case_contains_not_contains` | Approach B (Normalized Execution Plan) | 0.0383 ms | 0.0157 ms |
| `edge_case_contains_not_contains` | Approach C (Direct JSON Tree Evaluator) | 0.0051 ms | 0.0028 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.2223 ms | 0.0352 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.8337 ms | 0.7287 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Plan Diagnostic) | 0.1385 ms | 0.0305 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.1756 ms | 0.0487 ms |
| `edge_case_has_changed` | Approach B (Normalized Execution Plan) | 0.061 ms | 0.0192 ms |
| `edge_case_has_changed` | Approach C (Direct JSON Tree Evaluator) | 0.0093 ms | 0.0042 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.2109 ms | 0.089 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.6078 ms | 0.2798 ms |
| `edge_case_none_vs_missing_field` | Approach B (Normalized Execution Plan) | 0.0413 ms | 0.0188 ms |
| `edge_case_none_vs_missing_field` | Approach C (Direct JSON Tree Evaluator) | 0.013 ms | 0.0041 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.2644 ms | 0.0503 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.9533 ms | 0.7996 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Plan Diagnostic) | 0.1913 ms | 0.0315 ms |

---

## 5. Methodology, Security Profile & Trade-offs

### Measurement Methodology & Isolation
1. **Cold Prep Isolation:** All LRU caches (`clear_condition_plan_cache()`) are explicitly cleared prior to cold preparation measurements. If cache clearing fails, cold preparation is marked invalid rather than silently proceeding.
2. **Steady-State & Result Validation:** Timed across 5 batches of 10,000 evaluations using alternating matching and non-matching document instances to prevent CPU branch prediction bias. Evaluation results and errors are strictly validated during benchmark loops.
3. **Fair Comparison Scope:** Semantics are compared only across shared supported operators. Operators not supported by a candidate (e.g., `has_changed` in canonical contract) are explicitly marked as `UNSUPPORTED` or `DEPRECATED` rather than counted as failures.

### Security Profile & Analysis
- **Approach A (`safe_eval`)**: Re-compiles Python expressions dynamically using RestrictedPython on every call. While restricted, dynamic string evaluation carries latent code execution attack vectors if input sanitization is bypassed.
- **Approach B / Approach C / PR #469 Canonical Evaluator**: Parse conditions into structured AST nodes and evaluate them via pure Python tree traversal. This completely avoids `eval()`, `exec()`, and `safe_eval()`, eliminating dynamic string execution vulnerabilities.

### Production Selection Gate
Production selection remains **Not established** in this report. Final production adoption requires explicit formal review of security boundaries, governance policies, and cross-module integration requirements.