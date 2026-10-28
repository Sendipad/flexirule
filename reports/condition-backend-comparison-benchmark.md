# FlexiRule — Five-Approach Condition Backend Comparison Benchmark Report

**Date:** 2026-10-28T23:15:02Z
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
| `simple_equality` | Tier 1 — Simple | 175.384 µs/op | 10.704 µs/op | UNSUPPORTED | UNSUPPORTED | 29.755 µs/op | 7.482 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 407.969 µs/op | 11.576 µs/op | UNSUPPORTED | UNSUPPORTED | 56.11 µs/op | 15.96 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 541.279 µs/op | 11.428 µs/op | UNSUPPORTED | UNSUPPORTED | 64.752 µs/op | 15.996 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1125.753 µs/op | 15.467 µs/op | UNSUPPORTED | UNSUPPORTED | 110.14 µs/op | 31.824 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 712.301 µs/op | 16.595 µs/op | UNSUPPORTED | UNSUPPORTED | 76.66 µs/op | 30.708 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 371.581 µs/op | 10.209 µs/op | UNSUPPORTED | UNSUPPORTED | 47.849 µs/op | 15.143 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 578.296 µs/op | 14.213 µs/op | UNSUPPORTED | UNSUPPORTED | 38.371 µs/op | 8.787 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 54.971 µs/op | 7.386 µs/op | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 299.846 µs/op | 10.077 µs/op | UNSUPPORTED | UNSUPPORTED | 20.336 µs/op | 4.056 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.1129 ms | 0.1342 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.2121 ms | 0.199 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.1067 ms | 0.0232 ms |
| `simple_equality` | Canonical Condition (Prepared Plan Diagnostic) | 0.1159 ms | 0.0203 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.4076 ms | 0.2055 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.598 ms | 0.5031 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.38 ms | 0.0493 ms |
| `typical_business_rule` | Canonical Condition (Prepared Plan Diagnostic) | 0.1737 ms | 0.0375 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.4823 ms | 0.2756 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.7232 ms | 0.7004 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.3429 ms | 0.0643 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Plan Diagnostic) | 0.2315 ms | 0.0476 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 0.7972 ms | 0.627 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.5467 ms | 1.3947 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.5637 ms | 0.0844 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Plan Diagnostic) | 0.4606 ms | 0.08 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.5656 ms | 0.3069 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.9071 ms | 0.8685 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.3901 ms | 0.0548 ms |
| `collection_predicate` | Canonical Condition (Prepared Plan Diagnostic) | 0.226 ms | 0.0448 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.4551 ms | 0.2142 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.6193 ms | 0.5073 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.2575 ms | 0.0364 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Plan Diagnostic) | 0.2015 ms | 0.0324 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.5006 ms | 0.2737 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.7454 ms | 0.7216 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.2318 ms | 0.0347 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Plan Diagnostic) | 0.1427 ms | 0.0294 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.1672 ms | 0.0489 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.1314 ms | 0.0817 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.2883 ms | 0.1491 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.5319 ms | 0.3592 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.1528 ms | 0.0216 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Plan Diagnostic) | 0.0644 ms | 0.0175 ms |

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