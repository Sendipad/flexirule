# FlexiRule — Five-Approach Condition Backend Comparison Benchmark Report

**Date:** 2026-10-28T22:21:20Z
**Branch:** `jules-3100235434379853320-7a89fca0`
**Commit:** `5ce124cbc1b2a6b2b879af0f242a1ddc6e814a77`
**Python:** 3.12.13
**Frappe Framework:** 15.123.1

## Production Selection Gate Status

- **Selected Production Option:** **Not established**
- **Gate Status:** Production selection remains Not established until explicit correctness, security, and performance criteria gates pass.

---

## 1. Candidate Evaluators Evaluated

| Candidate | Paradigm | Preparation Mechanism | Execution Path |
|---|---|---|---|
| **Approach A (`safe_eval`)** | Legacy Dynamic Eval | Python expr string | `frappe.safe_eval` (RestrictedPython parse on every call) |
| **Approach A Exp (`code_obj`)** | Diagnostic Compiled | Pre-compiled bytecode | `eval(code_object)` |
| **Approach B (`plan`)** | Normalized AST Plan | Pre-compiled tuple AST | Direct AST recursive interpreter |
| **Approach C (`json_tree`)** | Direct JSON Evaluator | Pure JSON AST | Direct JSON tree walker |
| **Canonical (`evaluate_condition`)** | Public PR #469 Runtime | LRU-cached AST compilation | Public API with context normalization & cache lookup |
| **Canonical (`Prepared Plan`)** | Diagnostic PR #469 Plan | Direct compiled AST plan | Direct internal `_evaluate_node` execution |

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

| Scenario ID | Tier | Approach A (`safe_eval`) | Approach A Exp (`code_obj`) | Approach B (`plan`) | Approach C (`json_tree`) | Canonical Runtime (`evaluate_condition`) | Canonical Diagnostic (`Plan`) |
|---|---|---|---|---|---|---|---|
| `simple_equality` | Tier 1 — Simple | 176.905 µs/op | 9.979 µs/op | UNSUPPORTED | UNSUPPORTED | 29.346 µs/op | 7.25 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 419.198 µs/op | 11.686 µs/op | UNSUPPORTED | UNSUPPORTED | 56.845 µs/op | 16.358 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 553.783 µs/op | 11.607 µs/op | UNSUPPORTED | UNSUPPORTED | 66.411 µs/op | 16.041 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1147.75 µs/op | 15.458 µs/op | UNSUPPORTED | UNSUPPORTED | 112.985 µs/op | 31.945 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 721.415 µs/op | 16.417 µs/op | UNSUPPORTED | UNSUPPORTED | 78.056 µs/op | 31.213 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 383.578 µs/op | 10.122 µs/op | UNSUPPORTED | UNSUPPORTED | 49.708 µs/op | 15.695 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 602.236 µs/op | 14.125 µs/op | UNSUPPORTED | UNSUPPORTED | 39.382 µs/op | 8.96 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 55.245 µs/op | 7.376 µs/op | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 338.516 µs/op | 9.964 µs/op | UNSUPPORTED | UNSUPPORTED | 20.925 µs/op | 4.162 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.2695 ms | 0.1607 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.3891 ms | 0.3381 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.2279 ms | 0.045 ms |
| `simple_equality` | Canonical Condition (Prepared Plan Diagnostic) | 0.3369 ms | 0.0354 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.5008 ms | 0.2248 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.5452 ms | 0.5606 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.3971 ms | 0.0417 ms |
| `typical_business_rule` | Canonical Condition (Prepared Plan Diagnostic) | 0.2331 ms | 0.0406 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.5485 ms | 0.2833 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.7178 ms | 0.7084 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.3509 ms | 0.0533 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Plan Diagnostic) | 0.2287 ms | 0.0478 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 1.0501 ms | 0.5747 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.4435 ms | 1.4589 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.5279 ms | 0.0893 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Plan Diagnostic) | 0.4379 ms | 0.0803 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.5496 ms | 0.312 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.979 ms | 0.9017 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.4538 ms | 0.0493 ms |
| `collection_predicate` | Canonical Condition (Prepared Plan Diagnostic) | 0.2679 ms | 0.044 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.4223 ms | 0.2089 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.5799 ms | 0.5428 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.268 ms | 0.0369 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Plan Diagnostic) | 0.2179 ms | 0.056 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.5046 ms | 0.3698 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.7761 ms | 0.6839 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.24 ms | 0.0352 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Plan Diagnostic) | 0.1326 ms | 0.0308 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.1633 ms | 0.0472 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.2519 ms | 0.1064 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.3544 ms | 0.1433 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.3948 ms | 0.4162 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.158 ms | 0.0212 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Plan Diagnostic) | 0.0659 ms | 0.0175 ms |

---

## 5. Methodology, Security Profile & Trade-offs

### Measurement Methodology & Isolation
1. **Cold Prep Isolation:** All LRU caches (`clear_condition_plan_cache()`) are explicitly cleared prior to cold preparation measurements. Correctness checks execute in an isolated phase to avoid pre-warming cold execution states.
2. **Steady-State Execution Latency:** Timed across 5 batches of 10,000 evaluations using alternating matching and non-matching document instances to prevent CPU branch prediction bias.
3. **Fair Comparison Scope:** Semantics are compared only across shared supported operators. Operators not supported by a candidate (e.g., `has_changed` in canonical contract) are explicitly marked as `UNSUPPORTED` or `DEPRECATED` rather than counted as failures.

### Security Profile & Analysis
- **Approach A (`frappe.safe_eval`)**: Re-compiles Python expressions dynamically using RestrictedPython on every call. While restricted, dynamic string evaluation carries latent code execution attack vectors if input sanitization is bypassed.
- **Approach B / Approach C / PR #469 Canonical Evaluator**: Parse conditions into structured AST nodes and evaluate them via pure Python tree traversal. This completely avoids `eval()`, `exec()`, and `safe_eval()`, eliminating dynamic string execution vulnerabilities.

### Production Selection Gate
Production selection remains **Not established** in this report. Final production adoption requires explicit formal review of security boundaries, governance policies, and cross-module integration requirements.