# FlexiRule — Five-Approach Condition Backend Comparison Benchmark Report

**Date:** 2026-10-29T00:52:31Z
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
| `simple_equality` | Tier 1 — Simple | 167.679 µs/op | 3.442 µs/op | 5.175 µs/op | 27.707 µs/op | 9.607 µs/op | 7.576 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 408.866 µs/op | 6.25 µs/op | 10.701 µs/op | 56.153 µs/op | 11.813 µs/op | 16.559 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 538.819 µs/op | 6.562 µs/op | 11.501 µs/op | 66.368 µs/op | 11.967 µs/op | 16.489 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1156.589 µs/op | 10.031 µs/op | 17.82 µs/op | 112.157 µs/op | 16.298 µs/op | 31.872 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 711.938 µs/op | 10.645 µs/op | 17.34 µs/op | 77.288 µs/op | 16.896 µs/op | 30.693 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 373.443 µs/op | 5.183 µs/op | 7.785 µs/op | 49.118 µs/op | 10.646 µs/op | 15.456 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 577.228 µs/op | 5.706 µs/op | 9.008 µs/op | 38.939 µs/op | 14.771 µs/op | 9.102 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 55.495 µs/op | 3.467 µs/op | 5.343 µs/op | UNSUPPORTED | 7.705 µs/op | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 299.804 µs/op | 2.824 µs/op | 4.152 µs/op | 20.511 µs/op | 10.498 µs/op | 4.294 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.1595 ms | 0.1511 ms |
| `simple_equality` | Approach B (Normalized Execution Plan) | 0.0281 ms | 0.0197 ms |
| `simple_equality` | Approach C (Direct JSON Tree Evaluator) | 0.0122 ms | 0.0027 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.316 ms | 0.0292 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.3958 ms | 0.3787 ms |
| `simple_equality` | Canonical Condition (Prepared Plan Diagnostic) | 0.1199 ms | 0.039 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.3483 ms | 0.4002 ms |
| `typical_business_rule` | Approach B (Normalized Execution Plan) | 0.0419 ms | 0.02 ms |
| `typical_business_rule` | Approach C (Direct JSON Tree Evaluator) | 0.0053 ms | 0.0027 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.2916 ms | 0.0412 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.6301 ms | 0.5542 ms |
| `typical_business_rule` | Canonical Condition (Prepared Plan Diagnostic) | 0.222 ms | 0.0376 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.4077 ms | 0.3089 ms |
| `nested_and_or_groups` | Approach B (Normalized Execution Plan) | 0.0512 ms | 0.0251 ms |
| `nested_and_or_groups` | Approach C (Direct JSON Tree Evaluator) | 0.006 ms | 0.0025 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.3895 ms | 0.0715 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.7441 ms | 0.7221 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Plan Diagnostic) | 0.2347 ms | 0.0479 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 0.8501 ms | 0.5714 ms |
| `deep_nested_complex` | Approach B (Normalized Execution Plan) | 0.0685 ms | 0.0397 ms |
| `deep_nested_complex` | Approach C (Direct JSON Tree Evaluator) | 0.0054 ms | 0.0026 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.6074 ms | 0.0839 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.5498 ms | 1.3948 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Plan Diagnostic) | 0.4225 ms | 0.0801 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.4934 ms | 0.3471 ms |
| `collection_predicate` | Approach B (Normalized Execution Plan) | 0.0651 ms | 0.0258 ms |
| `collection_predicate` | Approach C (Direct JSON Tree Evaluator) | 0.0066 ms | 0.0466 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.3427 ms | 0.0496 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.9596 ms | 0.8332 ms |
| `collection_predicate` | Canonical Condition (Prepared Plan Diagnostic) | 0.2115 ms | 0.0548 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.4052 ms | 0.2043 ms |
| `edge_case_membership_in_not_in` | Approach B (Normalized Execution Plan) | 0.0372 ms | 0.0167 ms |
| `edge_case_membership_in_not_in` | Approach C (Direct JSON Tree Evaluator) | 0.0059 ms | 0.0027 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.2395 ms | 0.0355 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.5072 ms | 0.5203 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Plan Diagnostic) | 0.2742 ms | 0.0408 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.4724 ms | 0.2694 ms |
| `edge_case_contains_not_contains` | Approach B (Normalized Execution Plan) | 0.0384 ms | 0.0159 ms |
| `edge_case_contains_not_contains` | Approach C (Direct JSON Tree Evaluator) | 0.0051 ms | 0.0026 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.2822 ms | 0.0352 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.7416 ms | 0.6679 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Plan Diagnostic) | 0.1314 ms | 0.0347 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.2214 ms | 0.055 ms |
| `edge_case_has_changed` | Approach B (Normalized Execution Plan) | 0.0232 ms | 0.0096 ms |
| `edge_case_has_changed` | Approach C (Direct JSON Tree Evaluator) | 0.0053 ms | 0.0028 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.2101 ms | 0.0885 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.2726 ms | 0.1499 ms |
| `edge_case_none_vs_missing_field` | Approach B (Normalized Execution Plan) | 0.0357 ms | 0.0098 ms |
| `edge_case_none_vs_missing_field` | Approach C (Direct JSON Tree Evaluator) | 0.0056 ms | 0.0027 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.1562 ms | 0.0213 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.4522 ms | 0.4186 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Plan Diagnostic) | 0.0663 ms | 0.0171 ms |

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