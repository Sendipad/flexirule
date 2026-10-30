# FlexiRule — Condition Backend Comparison Benchmark Report

**Date:** 2026-10-30T21:42:00Z
**Branch:** `jules-153869591853811413-f75be7de`
**Commit:** `3e02b156986718effc338ae68f3ed724e83e4d78`
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
| `simple_equality` | Tier 1 — Simple | 171.071 µs/op | 3.587 µs/op | 5.524 µs/op | 34.347 µs/op | 9.432 µs/op | 13.009 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 418.645 µs/op | 6.294 µs/op | 10.464 µs/op | 57.798 µs/op | 12.11 µs/op | 20.744 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 539.821 µs/op | 6.594 µs/op | 11.296 µs/op | 66.498 µs/op | 11.791 µs/op | 20.662 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1142.041 µs/op | 10.327 µs/op | 17.787 µs/op | 118.914 µs/op | 16.059 µs/op | 44.065 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 730.75 µs/op | 10.584 µs/op | 17.119 µs/op | 78.685 µs/op | 16.814 µs/op | 33.958 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 392.032 µs/op | 10.234 µs/op | 15.825 µs/op | 50.592 µs/op | 10.483 µs/op | 19.278 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 573.711 µs/op | 5.722 µs/op | 8.928 µs/op | 38.818 µs/op | 14.306 µs/op | 12.072 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 55.06 µs/op | 3.565 µs/op | 5.42 µs/op | UNSUPPORTED | 7.383 µs/op | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 297.762 µs/op | 2.912 µs/op | 4.033 µs/op | 21.074 µs/op | 10.301 µs/op | 7.144 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.1119 ms | 0.1383 ms |
| `simple_equality` | Approach B (Normalized Execution Plan) | 0.0171 ms | 0.0105 ms |
| `simple_equality` | Approach C (Direct JSON Tree Evaluator) | 0.0035 ms | 0.0024 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.1247 ms | 0.0261 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.2225 ms | 0.199 ms |
| `simple_equality` | Canonical Condition (Prepared Artifact Runtime) | 0.1011 ms | 0.0794 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.417 ms | 0.2526 ms |
| `typical_business_rule` | Approach B (Normalized Execution Plan) | 0.0881 ms | 0.0306 ms |
| `typical_business_rule` | Approach C (Direct JSON Tree Evaluator) | 0.0051 ms | 0.0027 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.3132 ms | 0.0531 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.7303 ms | 0.5819 ms |
| `typical_business_rule` | Canonical Condition (Prepared Artifact Runtime) | 0.2511 ms | 0.1936 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.4879 ms | 0.2814 ms |
| `nested_and_or_groups` | Approach B (Normalized Execution Plan) | 0.1 ms | 0.0342 ms |
| `nested_and_or_groups` | Approach C (Direct JSON Tree Evaluator) | 0.0055 ms | 0.0026 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.343 ms | 0.0551 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.7428 ms | 0.6491 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Artifact Runtime) | 0.2754 ms | 0.2588 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 0.7952 ms | 0.5631 ms |
| `deep_nested_complex` | Approach B (Normalized Execution Plan) | 0.0658 ms | 0.0411 ms |
| `deep_nested_complex` | Approach C (Direct JSON Tree Evaluator) | 0.005 ms | 0.0028 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.5552 ms | 0.087 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.5084 ms | 1.3727 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Artifact Runtime) | 0.4989 ms | 0.4326 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.5906 ms | 0.3295 ms |
| `collection_predicate` | Approach B (Normalized Execution Plan) | 0.0611 ms | 0.0262 ms |
| `collection_predicate` | Approach C (Direct JSON Tree Evaluator) | 0.0055 ms | 0.0027 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.4051 ms | 0.0648 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.9136 ms | 0.8656 ms |
| `collection_predicate` | Canonical Condition (Prepared Artifact Runtime) | 0.2924 ms | 0.2156 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.333 ms | 0.2002 ms |
| `edge_case_membership_in_not_in` | Approach B (Normalized Execution Plan) | 0.0364 ms | 0.061 ms |
| `edge_case_membership_in_not_in` | Approach C (Direct JSON Tree Evaluator) | 0.0066 ms | 0.0025 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.2741 ms | 0.0382 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.5532 ms | 0.4615 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Artifact Runtime) | 0.2608 ms | 0.1609 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.4126 ms | 0.265 ms |
| `edge_case_contains_not_contains` | Approach B (Normalized Execution Plan) | 0.0392 ms | 0.0161 ms |
| `edge_case_contains_not_contains` | Approach C (Direct JSON Tree Evaluator) | 0.0048 ms | 0.0026 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.2284 ms | 0.0359 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.7682 ms | 0.8069 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Artifact Runtime) | 0.1719 ms | 0.2024 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.1661 ms | 0.0479 ms |
| `edge_case_has_changed` | Approach B (Normalized Execution Plan) | 0.0221 ms | 0.0085 ms |
| `edge_case_has_changed` | Approach C (Direct JSON Tree Evaluator) | 0.005 ms | 0.0025 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.1175 ms | 0.0807 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.3142 ms | 0.1426 ms |
| `edge_case_none_vs_missing_field` | Approach B (Normalized Execution Plan) | 0.0266 ms | 0.0098 ms |
| `edge_case_none_vs_missing_field` | Approach C (Direct JSON Tree Evaluator) | 0.0051 ms | 0.0026 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.1523 ms | 0.0225 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.4562 ms | 0.4151 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Artifact Runtime) | 0.098 ms | 0.0674 ms |

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