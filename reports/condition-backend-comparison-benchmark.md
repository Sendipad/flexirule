# FlexiRule — Condition Backend Comparison Benchmark Report

**Date:** 2026-10-30T19:26:38Z
**Branch:** `jules-153869591853811413-f75be7de`
**Commit:** `723a874310d34d8ef18fda9a472f16d4d93c024f`
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
| `simple_equality` | Tier 1 — Simple | 172.131 µs/op | 3.573 µs/op | 5.305 µs/op | 29.271 µs/op | 9.35 µs/op | 11.037 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 414.476 µs/op | 6.245 µs/op | 10.454 µs/op | 57.57 µs/op | 11.981 µs/op | 20.682 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 542.404 µs/op | 6.868 µs/op | 11.639 µs/op | 69.99 µs/op | 12.138 µs/op | 20.743 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1164.6 µs/op | 10.198 µs/op | 17.484 µs/op | 115.025 µs/op | 16.114 µs/op | 39.522 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 746.948 µs/op | 10.897 µs/op | 17.436 µs/op | 81.967 µs/op | 16.928 µs/op | 34.015 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 374.604 µs/op | 4.958 µs/op | 7.669 µs/op | 50.124 µs/op | 10.585 µs/op | 19.515 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 580.274 µs/op | 5.814 µs/op | 9.115 µs/op | 40.115 µs/op | 14.477 µs/op | 12.377 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 55.779 µs/op | 3.533 µs/op | 5.361 µs/op | UNSUPPORTED | 7.407 µs/op | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 300.857 µs/op | 2.838 µs/op | 4.156 µs/op | 21.771 µs/op | 10.325 µs/op | 7.112 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.1576 ms | 0.0845 ms |
| `simple_equality` | Approach B (Normalized Execution Plan) | 0.0176 ms | 0.0105 ms |
| `simple_equality` | Approach C (Direct JSON Tree Evaluator) | 0.004 ms | 0.0028 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.138 ms | 0.0241 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.2083 ms | 0.1973 ms |
| `simple_equality` | Canonical Condition (Prepared Artifact Runtime) | 0.124 ms | 0.1482 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.3448 ms | 0.1986 ms |
| `typical_business_rule` | Approach B (Normalized Execution Plan) | 0.0493 ms | 0.0207 ms |
| `typical_business_rule` | Approach C (Direct JSON Tree Evaluator) | 0.0051 ms | 0.0026 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.2896 ms | 0.0432 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.6584 ms | 0.7913 ms |
| `typical_business_rule` | Canonical Condition (Prepared Artifact Runtime) | 0.4311 ms | 0.2068 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.5075 ms | 0.3354 ms |
| `nested_and_or_groups` | Approach B (Normalized Execution Plan) | 0.049 ms | 0.0258 ms |
| `nested_and_or_groups` | Approach C (Direct JSON Tree Evaluator) | 0.0046 ms | 0.0033 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.3417 ms | 0.0535 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.6987 ms | 0.7016 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Artifact Runtime) | 0.3285 ms | 0.2148 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 0.7781 ms | 0.5685 ms |
| `deep_nested_complex` | Approach B (Normalized Execution Plan) | 0.0683 ms | 0.0487 ms |
| `deep_nested_complex` | Approach C (Direct JSON Tree Evaluator) | 0.005 ms | 0.0024 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.5694 ms | 0.085 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.4111 ms | 1.4492 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Artifact Runtime) | 0.4551 ms | 0.4372 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.5426 ms | 0.3227 ms |
| `collection_predicate` | Approach B (Normalized Execution Plan) | 0.0617 ms | 0.0267 ms |
| `collection_predicate` | Approach C (Direct JSON Tree Evaluator) | 0.0056 ms | 0.0024 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.3295 ms | 0.052 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.9757 ms | 0.8981 ms |
| `collection_predicate` | Canonical Condition (Prepared Artifact Runtime) | 0.3404 ms | 0.2095 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.3973 ms | 0.2028 ms |
| `edge_case_membership_in_not_in` | Approach B (Normalized Execution Plan) | 0.039 ms | 0.0164 ms |
| `edge_case_membership_in_not_in` | Approach C (Direct JSON Tree Evaluator) | 0.0044 ms | 0.0025 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.2857 ms | 0.0374 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.6178 ms | 0.473 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Artifact Runtime) | 0.257 ms | 0.1405 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.4325 ms | 0.3181 ms |
| `edge_case_contains_not_contains` | Approach B (Normalized Execution Plan) | 0.0393 ms | 0.0156 ms |
| `edge_case_contains_not_contains` | Approach C (Direct JSON Tree Evaluator) | 0.0054 ms | 0.0026 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.2908 ms | 0.0421 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.7006 ms | 0.779 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Artifact Runtime) | 0.1757 ms | 0.1279 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.1676 ms | 0.0479 ms |
| `edge_case_has_changed` | Approach B (Normalized Execution Plan) | 0.0265 ms | 0.0089 ms |
| `edge_case_has_changed` | Approach C (Direct JSON Tree Evaluator) | 0.0056 ms | 0.0027 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.133 ms | 0.0837 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.2771 ms | 0.1476 ms |
| `edge_case_none_vs_missing_field` | Approach B (Normalized Execution Plan) | 0.0367 ms | 0.0102 ms |
| `edge_case_none_vs_missing_field` | Approach C (Direct JSON Tree Evaluator) | 0.0057 ms | 0.0027 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.1556 ms | 0.0598 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.4456 ms | 0.4189 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Artifact Runtime) | 0.1174 ms | 0.0737 ms |

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