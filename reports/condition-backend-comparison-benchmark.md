# FlexiRule — Five-Approach Condition Backend Comparison Benchmark Report

**Date:** 2026-10-29T00:23:40Z
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
| `simple_equality` | Tier 1 — Simple | 172.612 µs/op | 3.491 µs/op | 5.125 µs/op | 27.719 µs/op | 9.398 µs/op | 7.433 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 413.096 µs/op | 6.326 µs/op | 10.55 µs/op | 57.037 µs/op | 11.919 µs/op | 16.869 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 542.121 µs/op | 6.578 µs/op | 11.626 µs/op | 65.357 µs/op | 11.932 µs/op | 16.565 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1130.409 µs/op | 10.05 µs/op | 17.844 µs/op | 111.139 µs/op | 15.856 µs/op | 32.585 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 719.296 µs/op | 10.715 µs/op | 17.193 µs/op | 77.923 µs/op | 16.573 µs/op | 30.608 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 376.572 µs/op | 5.121 µs/op | 7.659 µs/op | 49.049 µs/op | 10.371 µs/op | 15.634 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 581.805 µs/op | 5.743 µs/op | 9.026 µs/op | 39.173 µs/op | 14.475 µs/op | 9.208 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 55.795 µs/op | 3.451 µs/op | 5.326 µs/op | UNSUPPORTED | 7.555 µs/op | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 302.94 µs/op | 2.892 µs/op | 4.215 µs/op | 20.89 µs/op | 10.355 µs/op | 4.363 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.1237 ms | 0.0849 ms |
| `simple_equality` | Approach B (Normalized Execution Plan) | 0.0172 ms | 0.0101 ms |
| `simple_equality` | Approach C (Direct JSON Tree Evaluator) | 0.0039 ms | 0.0024 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.1104 ms | 0.023 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.2615 ms | 0.2 ms |
| `simple_equality` | Canonical Condition (Prepared Plan Diagnostic) | 0.0765 ms | 0.0194 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.357 ms | 0.3252 ms |
| `typical_business_rule` | Approach B (Normalized Execution Plan) | 0.0445 ms | 0.02 ms |
| `typical_business_rule` | Approach C (Direct JSON Tree Evaluator) | 0.0052 ms | 0.0028 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.2829 ms | 0.0435 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.538 ms | 0.5839 ms |
| `typical_business_rule` | Canonical Condition (Prepared Plan Diagnostic) | 0.2268 ms | 0.0439 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.4265 ms | 0.2572 ms |
| `nested_and_or_groups` | Approach B (Normalized Execution Plan) | 0.0471 ms | 0.025 ms |
| `nested_and_or_groups` | Approach C (Direct JSON Tree Evaluator) | 0.0053 ms | 0.0026 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.3395 ms | 0.0526 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.7228 ms | 0.6884 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Plan Diagnostic) | 0.2821 ms | 0.0534 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 0.7958 ms | 0.6214 ms |
| `deep_nested_complex` | Approach B (Normalized Execution Plan) | 0.0763 ms | 0.0394 ms |
| `deep_nested_complex` | Approach C (Direct JSON Tree Evaluator) | 0.0062 ms | 0.0026 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.5473 ms | 0.0808 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.4624 ms | 1.3598 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Plan Diagnostic) | 0.4506 ms | 0.0773 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.4826 ms | 0.348 ms |
| `collection_predicate` | Approach B (Normalized Execution Plan) | 0.0561 ms | 0.025 ms |
| `collection_predicate` | Approach C (Direct JSON Tree Evaluator) | 0.0056 ms | 0.0024 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.3968 ms | 0.0502 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.8738 ms | 0.879 ms |
| `collection_predicate` | Canonical Condition (Prepared Plan Diagnostic) | 0.2343 ms | 0.0498 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.3761 ms | 0.2061 ms |
| `edge_case_membership_in_not_in` | Approach B (Normalized Execution Plan) | 0.0363 ms | 0.0163 ms |
| `edge_case_membership_in_not_in` | Approach C (Direct JSON Tree Evaluator) | 0.0053 ms | 0.0029 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.373 ms | 0.0463 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.5679 ms | 0.4805 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Plan Diagnostic) | 0.1539 ms | 0.0311 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.4968 ms | 0.2724 ms |
| `edge_case_contains_not_contains` | Approach B (Normalized Execution Plan) | 0.0853 ms | 0.0211 ms |
| `edge_case_contains_not_contains` | Approach C (Direct JSON Tree Evaluator) | 0.0053 ms | 0.0026 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.2297 ms | 0.0353 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.7476 ms | 0.797 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Plan Diagnostic) | 0.1308 ms | 0.0369 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.1663 ms | 0.0488 ms |
| `edge_case_has_changed` | Approach B (Normalized Execution Plan) | 0.0214 ms | 0.0096 ms |
| `edge_case_has_changed` | Approach C (Direct JSON Tree Evaluator) | 0.0051 ms | 0.0024 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.1168 ms | 0.0814 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.2739 ms | 0.1844 ms |
| `edge_case_none_vs_missing_field` | Approach B (Normalized Execution Plan) | 0.0617 ms | 0.015 ms |
| `edge_case_none_vs_missing_field` | Approach C (Direct JSON Tree Evaluator) | 0.0053 ms | 0.0029 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.1479 ms | 0.0217 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.397 ms | 0.4438 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Plan Diagnostic) | 0.0673 ms | 0.0178 ms |

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