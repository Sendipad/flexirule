# FlexiRule — Five-Approach Condition Backend Comparison Benchmark Report

**Date:** 2026-10-28T23:05:26Z
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
| `simple_equality` | Tier 1 — Simple | 167.659 µs/op | 9.32 µs/op | UNSUPPORTED | UNSUPPORTED | 27.493 µs/op | 7.5 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 406.612 µs/op | 11.591 µs/op | UNSUPPORTED | UNSUPPORTED | 55.397 µs/op | 15.811 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 548.519 µs/op | 11.503 µs/op | UNSUPPORTED | UNSUPPORTED | 64.551 µs/op | 16.117 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1133.354 µs/op | 15.428 µs/op | UNSUPPORTED | UNSUPPORTED | 109.057 µs/op | 31.587 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 703.714 µs/op | 16.07 µs/op | UNSUPPORTED | UNSUPPORTED | 75.68 µs/op | 30.078 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 371.267 µs/op | 10.077 µs/op | UNSUPPORTED | UNSUPPORTED | 48.465 µs/op | 15.022 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 575.408 µs/op | 14.031 µs/op | UNSUPPORTED | UNSUPPORTED | 38.344 µs/op | 8.866 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 54.413 µs/op | 7.283 µs/op | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 301.77 µs/op | 9.998 µs/op | UNSUPPORTED | UNSUPPORTED | 20.19 µs/op | 3.942 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.113 ms | 0.083 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.2135 ms | 0.2505 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.1109 ms | 0.0226 ms |
| `simple_equality` | Canonical Condition (Prepared Plan Diagnostic) | 0.0759 ms | 0.0193 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.3559 ms | 0.2652 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.5465 ms | 0.6115 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.3165 ms | 0.0433 ms |
| `typical_business_rule` | Canonical Condition (Prepared Plan Diagnostic) | 0.1767 ms | 0.0405 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.4978 ms | 0.2692 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.7994 ms | 0.7572 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.3496 ms | 0.0534 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Plan Diagnostic) | 0.2849 ms | 0.0541 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 0.8992 ms | 0.5902 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.4858 ms | 1.389 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.5864 ms | 0.0805 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Plan Diagnostic) | 0.3892 ms | 0.1156 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.4974 ms | 0.297 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.9102 ms | 0.8779 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.4327 ms | 0.0504 ms |
| `collection_predicate` | Canonical Condition (Prepared Plan Diagnostic) | 0.222 ms | 0.0443 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.3876 ms | 0.1999 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.5805 ms | 0.4628 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.2591 ms | 0.038 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Plan Diagnostic) | 0.1505 ms | 0.0324 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.4988 ms | 0.2743 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.7744 ms | 0.6829 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.2421 ms | 0.0371 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Plan Diagnostic) | 0.206 ms | 0.0378 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.2225 ms | 0.0951 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.1371 ms | 0.0835 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.2887 ms | 0.1362 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.4664 ms | 0.3588 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.1971 ms | 0.0286 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Plan Diagnostic) | 0.0736 ms | 0.018 ms |

---

## 5. Methodology, Security Profile & Trade-offs

### Measurement Methodology & Isolation
1. **Cold Prep Isolation:** All LRU caches (`clear_condition_plan_cache()`) are explicitly cleared prior to cold preparation measurements. If cache clearing fails, cold preparation is marked invalid rather than silently proceeding.
2. **Steady-State Execution Latency:** Timed across 5 batches of 10,000 evaluations using alternating matching and non-matching document instances to prevent CPU branch prediction bias.
3. **Fair Comparison Scope:** Semantics are compared only across shared supported operators. Operators not supported by a candidate (e.g., `has_changed` in canonical contract) are explicitly marked as `UNSUPPORTED` or `DEPRECATED` rather than counted as failures.

### Security Profile & Analysis
- **Approach A (`safe_eval`)**: Re-compiles Python expressions dynamically using RestrictedPython on every call. While restricted, dynamic string evaluation carries latent code execution attack vectors if input sanitization is bypassed.
- **Approach B / Approach C / PR #469 Canonical Evaluator**: Parse conditions into structured AST nodes and evaluate them via pure Python tree traversal. This completely avoids `eval()`, `exec()`, and `safe_eval()`, eliminating dynamic string execution vulnerabilities.

### Production Selection Gate
Production selection remains **Not established** in this report. Final production adoption requires explicit formal review of security boundaries, governance policies, and cross-module integration requirements.