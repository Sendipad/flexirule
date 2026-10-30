# FlexiRule — Condition Backend Comparison Benchmark Report

**Date:** 2026-10-30T17:39:07Z
**Branch:** `jules-153869591853811413-f75be7de`
**Commit:** `468ad3f477e21081c65ef28c0ef596ea762bffaf`
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
| `simple_equality` | Tier 1 — Simple | 177.068 µs/op | 3.498 µs/op | 5.254 µs/op | 28.684 µs/op | 9.537 µs/op | 10.751 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 412.526 µs/op | 6.141 µs/op | 10.487 µs/op | 58.412 µs/op | 12.454 µs/op | 20.694 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 549.97 µs/op | 6.439 µs/op | 11.155 µs/op | 66.497 µs/op | 11.788 µs/op | 20.104 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1146.664 µs/op | 9.73 µs/op | 17.176 µs/op | 117.538 µs/op | 15.673 µs/op | 37.569 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 717.834 µs/op | 10.516 µs/op | 16.805 µs/op | 77.013 µs/op | 17.235 µs/op | 33.392 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 374.437 µs/op | 4.943 µs/op | 7.618 µs/op | 50.429 µs/op | 11.276 µs/op | 19.551 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 588.184 µs/op | 5.604 µs/op | 9.101 µs/op | 39.425 µs/op | 14.243 µs/op | 11.884 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 54.635 µs/op | 3.39 µs/op | 5.951 µs/op | UNSUPPORTED | 7.494 µs/op | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 304.608 µs/op | 2.821 µs/op | 4.06 µs/op | 21.316 µs/op | 10.382 µs/op | 7.096 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.1228 ms | 0.0844 ms |
| `simple_equality` | Approach B (Normalized Execution Plan) | 0.019 ms | 0.0105 ms |
| `simple_equality` | Approach C (Direct JSON Tree Evaluator) | 0.0036 ms | 0.0024 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.1129 ms | 0.0239 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.203 ms | 0.2536 ms |
| `simple_equality` | Canonical Condition (Prepared Artifact Runtime) | 0.0985 ms | 0.0769 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.392 ms | 0.2112 ms |
| `typical_business_rule` | Approach B (Normalized Execution Plan) | 0.0429 ms | 0.0203 ms |
| `typical_business_rule` | Approach C (Direct JSON Tree Evaluator) | 0.0045 ms | 0.0025 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.3348 ms | 0.0528 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.6626 ms | 0.5357 ms |
| `typical_business_rule` | Canonical Condition (Prepared Artifact Runtime) | 0.2211 ms | 0.1898 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.4237 ms | 0.4036 ms |
| `nested_and_or_groups` | Approach B (Normalized Execution Plan) | 0.0487 ms | 0.0255 ms |
| `nested_and_or_groups` | Approach C (Direct JSON Tree Evaluator) | 0.0045 ms | 0.0028 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.4516 ms | 0.0616 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.8568 ms | 0.802 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Artifact Runtime) | 0.275 ms | 0.2082 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 0.854 ms | 0.5575 ms |
| `deep_nested_complex` | Approach B (Normalized Execution Plan) | 0.0736 ms | 0.0415 ms |
| `deep_nested_complex` | Approach C (Direct JSON Tree Evaluator) | 0.0052 ms | 0.0028 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.5572 ms | 0.085 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.4074 ms | 1.4345 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Artifact Runtime) | 0.4504 ms | 0.4077 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.5221 ms | 0.3114 ms |
| `collection_predicate` | Approach B (Normalized Execution Plan) | 0.0675 ms | 0.027 ms |
| `collection_predicate` | Approach C (Direct JSON Tree Evaluator) | 0.0053 ms | 0.0026 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.3268 ms | 0.0488 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.9761 ms | 0.8619 ms |
| `collection_predicate` | Canonical Condition (Prepared Artifact Runtime) | 0.3166 ms | 0.2095 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.3948 ms | 0.2022 ms |
| `edge_case_membership_in_not_in` | Approach B (Normalized Execution Plan) | 0.1066 ms | 0.0185 ms |
| `edge_case_membership_in_not_in` | Approach C (Direct JSON Tree Evaluator) | 0.0045 ms | 0.0027 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.2813 ms | 0.0379 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.511 ms | 0.5129 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Artifact Runtime) | 0.2423 ms | 0.1523 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.4638 ms | 0.2676 ms |
| `edge_case_contains_not_contains` | Approach B (Normalized Execution Plan) | 0.037 ms | 0.0158 ms |
| `edge_case_contains_not_contains` | Approach C (Direct JSON Tree Evaluator) | 0.0045 ms | 0.0025 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.2774 ms | 0.0379 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.7298 ms | 0.7411 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Artifact Runtime) | 0.1694 ms | 0.1259 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.2018 ms | 0.0697 ms |
| `edge_case_has_changed` | Approach B (Normalized Execution Plan) | 0.0251 ms | 0.0093 ms |
| `edge_case_has_changed` | Approach C (Direct JSON Tree Evaluator) | 0.0054 ms | 0.0025 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.121 ms | 0.0796 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.2963 ms | 0.1485 ms |
| `edge_case_none_vs_missing_field` | Approach B (Normalized Execution Plan) | 0.0267 ms | 0.0107 ms |
| `edge_case_none_vs_missing_field` | Approach C (Direct JSON Tree Evaluator) | 0.0108 ms | 0.0039 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.2092 ms | 0.0315 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.493 ms | 0.3898 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Artifact Runtime) | 0.1139 ms | 0.0763 ms |

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