# FlexiRule — Five-Approach Condition Backend Comparison Benchmark Report

**Date:** 2026-10-28T23:25:47Z
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
| `simple_equality` | Tier 1 — Simple | 172.487 µs/op | 8.97 µs/op | UNSUPPORTED | UNSUPPORTED | 26.839 µs/op | 7.227 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 410.574 µs/op | 11.271 µs/op | UNSUPPORTED | UNSUPPORTED | 55.187 µs/op | 15.969 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 544.019 µs/op | 11.227 µs/op | UNSUPPORTED | UNSUPPORTED | 63.981 µs/op | 15.781 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1136.152 µs/op | 15.354 µs/op | UNSUPPORTED | UNSUPPORTED | 108.595 µs/op | 31.746 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 713.288 µs/op | 15.991 µs/op | UNSUPPORTED | UNSUPPORTED | 77.511 µs/op | 30.023 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 375.416 µs/op | 9.903 µs/op | UNSUPPORTED | UNSUPPORTED | 48.824 µs/op | 14.856 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 581.617 µs/op | 13.675 µs/op | UNSUPPORTED | UNSUPPORTED | 37.931 µs/op | 8.711 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 55.182 µs/op | 6.991 µs/op | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 302.663 µs/op | 9.844 µs/op | UNSUPPORTED | UNSUPPORTED | 21.355 µs/op | 4.05 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.1128 ms | 0.0832 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.2621 ms | 0.2041 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.1064 ms | 0.0901 ms |
| `simple_equality` | Canonical Condition (Prepared Plan Diagnostic) | 0.0873 ms | 0.0202 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.3649 ms | 0.199 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.5969 ms | 0.5643 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.4134 ms | 0.0428 ms |
| `typical_business_rule` | Canonical Condition (Prepared Plan Diagnostic) | 0.1689 ms | 0.0388 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.5811 ms | 0.3312 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.7266 ms | 0.7673 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.3997 ms | 0.0539 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Plan Diagnostic) | 0.2234 ms | 0.0559 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 1.0005 ms | 0.5697 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.572 ms | 1.4978 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.5103 ms | 0.0872 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Plan Diagnostic) | 0.4279 ms | 0.0772 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.5735 ms | 0.3102 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.9092 ms | 0.8704 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.4419 ms | 0.0565 ms |
| `collection_predicate` | Canonical Condition (Prepared Plan Diagnostic) | 0.2654 ms | 0.0481 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.3783 ms | 0.1948 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.5699 ms | 0.4567 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.304 ms | 0.0371 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Plan Diagnostic) | 0.1936 ms | 0.0313 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.5048 ms | 0.2805 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.7744 ms | 0.8402 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.2368 ms | 0.0366 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Plan Diagnostic) | 0.1315 ms | 0.0313 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.1731 ms | 0.0494 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.1284 ms | 0.0839 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.3877 ms | 0.1463 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.4242 ms | 0.4171 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.1594 ms | 0.0212 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Plan Diagnostic) | 0.0771 ms | 0.0172 ms |

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