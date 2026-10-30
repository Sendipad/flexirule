# FlexiRule — Condition Backend Comparison Benchmark Report

**Date:** 2026-10-30T22:10:49Z
**Branch:** `jules-153869591853811413-f75be7de`
**Commit:** `f3d812b4d4a6cc43cf07a2de3e3852ef7d73a7a0`
**Working Tree Dirty:** `No`
**Provenance Note:** Git commit and clean working tree were verified from the benchmark repository root.
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
| **Canonical (`evaluate_condition`)** | Validating public runtime | LRU-cached AST compilation | Public API with context normalization & cache lookup |

### Prepared and Experimental Runtime Baselines
| Candidate | Purpose | Preparation Mechanism | Execution Path |
|---|---|---|---|
| **Approach A Exp (`code_obj`)** | Isolated Bytecode Baseline | Pre-compiled bytecode | `eval(code_object)` |
| **Canonical (`Prepared Plan`)** | Validated prepared-artifact runtime | Immutable validated artifact | Public prepared API without source serialization or cache-key lookup |

---

## 2. Independent Semantic Correctness & Compatibility Suite

All candidate evaluators were evaluated against neutral business scenarios. Supported scenarios passed: **8 / 8**.

| Scenario ID | Tier | Status | Matching Check | Non-Matching Check | Disagreements / Errors |
|---|---|---|---|---|---|
| `simple_equality` | Tier 1 — Simple | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False</small>` | None |
| `typical_business_rule` | Tier 2 — Typical Business Rule | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False</small>` | None |
| `nested_and_or_groups` | Tier 3 — Nested Groups | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False</small>` | None |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False</small>` | None |
| `collection_predicate` | Tier 5 — Collection Predicate | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False</small>` | None |
| `edge_case_membership_in_not_in` | Edge Case — Membership | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False</small>` | None |
| `edge_case_contains_not_contains` | Edge Case — Substring | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False</small>` | None |
| `edge_case_has_changed` | Edge Case — Field Change | **DEPRECATED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract., Canonical Condition (Prepared Artifact Runtime): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract.</small>` | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract., Canonical Condition (Prepared Artifact Runtime): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract.</small>` | Candidate 'Approach A (frappe.safe_eval)' non-matching result (True) != expected (False) | Candidate 'Approach A (Experimental Restricted Code Object)' non-matching result (True) != expected (False) | Disagreement on non-matching doc: {'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False} | DEPRECATED: 'has_changed' operator behavior varies between deprecated legacy return 'True' and state-diff evaluators. |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False</small>` | None |

---

## 3. Steady-State Execution Latency (Microseconds per Operation)

| Scenario ID | Tier | Approach A (`safe_eval`) | Approach B (`plan`) | Approach C (`json_tree`) | Canonical Runtime (`evaluate_condition`) | *Diagnostic: A Exp (`code_obj`)* | *Prepared Artifact Runtime* |
|---|---|---|---|---|---|---|---|
| `simple_equality` | Tier 1 — Simple | 169.606 µs/op | 3.562 µs/op | 5.395 µs/op | 30.179 µs/op | 9.65 µs/op | 10.859 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 407.698 µs/op | 6.3 µs/op | 10.454 µs/op | 57.541 µs/op | 12.069 µs/op | 20.517 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 538.117 µs/op | 6.517 µs/op | 11.418 µs/op | 66.534 µs/op | 12.041 µs/op | 20.532 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1124.021 µs/op | 10.045 µs/op | 17.678 µs/op | 110.299 µs/op | 15.882 µs/op | 37.126 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 711.983 µs/op | 10.624 µs/op | 17.1 µs/op | 77.791 µs/op | 16.823 µs/op | 33.533 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 375.368 µs/op | 4.802 µs/op | 7.66 µs/op | 52.06 µs/op | 10.409 µs/op | 18.821 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 576.983 µs/op | 5.797 µs/op | 8.949 µs/op | 40.425 µs/op | 14.692 µs/op | 12.329 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 55.568 µs/op | 3.488 µs/op | 5.415 µs/op | UNSUPPORTED | 7.699 µs/op | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 301.459 µs/op | 2.87 µs/op | 4.262 µs/op | 21.469 µs/op | 10.593 µs/op | 7.301 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.1177 ms | 0.0844 ms |
| `simple_equality` | Approach B (Normalized Execution Plan) | 0.0188 ms | 0.0109 ms |
| `simple_equality` | Approach C (Direct JSON Tree Evaluator) | 0.0039 ms | 0.0025 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.1157 ms | 0.0243 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.2674 ms | 0.2118 ms |
| `simple_equality` | Canonical Condition (Prepared Artifact Runtime) | 0.1063 ms | 0.078 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.3218 ms | 0.1947 ms |
| `typical_business_rule` | Approach B (Normalized Execution Plan) | 0.0449 ms | 0.0205 ms |
| `typical_business_rule` | Approach C (Direct JSON Tree Evaluator) | 0.0046 ms | 0.0027 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.2752 ms | 0.0433 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.655 ms | 0.5709 ms |
| `typical_business_rule` | Canonical Condition (Prepared Artifact Runtime) | 0.2096 ms | 0.1643 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.4733 ms | 0.2749 ms |
| `nested_and_or_groups` | Approach B (Normalized Execution Plan) | 0.0596 ms | 0.026 ms |
| `nested_and_or_groups` | Approach C (Direct JSON Tree Evaluator) | 0.0047 ms | 0.0027 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.3425 ms | 0.0551 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.7944 ms | 0.7221 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Artifact Runtime) | 0.2912 ms | 0.3674 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 0.7913 ms | 0.5472 ms |
| `deep_nested_complex` | Approach B (Normalized Execution Plan) | 0.0722 ms | 0.0932 ms |
| `deep_nested_complex` | Approach C (Direct JSON Tree Evaluator) | 0.0071 ms | 0.0027 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.5132 ms | 0.0805 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.4499 ms | 1.5153 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Artifact Runtime) | 0.5017 ms | 0.3695 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.4554 ms | 0.2976 ms |
| `collection_predicate` | Approach B (Normalized Execution Plan) | 0.0678 ms | 0.028 ms |
| `collection_predicate` | Approach C (Direct JSON Tree Evaluator) | 0.0056 ms | 0.0027 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.3253 ms | 0.0512 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.8959 ms | 1.3583 ms |
| `collection_predicate` | Canonical Condition (Prepared Artifact Runtime) | 0.2689 ms | 0.2893 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.3543 ms | 0.2635 ms |
| `edge_case_membership_in_not_in` | Approach B (Normalized Execution Plan) | 0.0418 ms | 0.0161 ms |
| `edge_case_membership_in_not_in` | Approach C (Direct JSON Tree Evaluator) | 0.0054 ms | 0.0026 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.2705 ms | 0.0371 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.5793 ms | 0.5256 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Artifact Runtime) | 0.1889 ms | 0.1992 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.4117 ms | 0.3354 ms |
| `edge_case_contains_not_contains` | Approach B (Normalized Execution Plan) | 0.0387 ms | 0.016 ms |
| `edge_case_contains_not_contains` | Approach C (Direct JSON Tree Evaluator) | 0.005 ms | 0.0024 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.2819 ms | 0.0404 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.7574 ms | 0.6918 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Artifact Runtime) | 0.1738 ms | 0.1277 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.1561 ms | 0.0455 ms |
| `edge_case_has_changed` | Approach B (Normalized Execution Plan) | 0.0232 ms | 0.0089 ms |
| `edge_case_has_changed` | Approach C (Direct JSON Tree Evaluator) | 0.0048 ms | 0.003 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.1163 ms | 0.0783 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.3078 ms | 0.2045 ms |
| `edge_case_none_vs_missing_field` | Approach B (Normalized Execution Plan) | 0.027 ms | 0.01 ms |
| `edge_case_none_vs_missing_field` | Approach C (Direct JSON Tree Evaluator) | 0.0052 ms | 0.0029 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.147 ms | 0.0218 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.3976 ms | 0.4126 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Artifact Runtime) | 0.0954 ms | 0.0676 ms |

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