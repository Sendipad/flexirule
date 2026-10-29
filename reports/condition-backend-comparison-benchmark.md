# FlexiRule — Five-Approach Condition Backend Comparison Benchmark Report

**Date:** 2026-10-29T00:32:48Z
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
| `simple_equality` | Tier 1 — Simple | 172.644 µs/op | 3.571 µs/op | 5.279 µs/op | 27.687 µs/op | 9.809 µs/op | 7.359 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 413.814 µs/op | 6.203 µs/op | 10.36 µs/op | 56.348 µs/op | 11.891 µs/op | 16.202 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 548.154 µs/op | 6.618 µs/op | 11.396 µs/op | 101.711 µs/op | 11.843 µs/op | 16.13 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1134.295 µs/op | 10.045 µs/op | 17.496 µs/op | 110.108 µs/op | 15.884 µs/op | 31.821 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 708.712 µs/op | 10.656 µs/op | 17.255 µs/op | 76.846 µs/op | 16.646 µs/op | 30.073 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 377.538 µs/op | 5.008 µs/op | 7.705 µs/op | 48.819 µs/op | 10.742 µs/op | 15.212 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 585.018 µs/op | 5.771 µs/op | 8.925 µs/op | 38.981 µs/op | 14.653 µs/op | 9.287 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 55.239 µs/op | 3.44 µs/op | 5.334 µs/op | UNSUPPORTED | 7.608 µs/op | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 302.026 µs/op | 2.844 µs/op | 4.208 µs/op | 20.688 µs/op | 10.511 µs/op | 4.288 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.1908 ms | 0.108 ms |
| `simple_equality` | Approach B (Normalized Execution Plan) | 0.0188 ms | 0.0163 ms |
| `simple_equality` | Approach C (Direct JSON Tree Evaluator) | 0.0039 ms | 0.0025 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.1171 ms | 0.0226 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.312 ms | 0.237 ms |
| `simple_equality` | Canonical Condition (Prepared Plan Diagnostic) | 0.1251 ms | 0.0254 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.3857 ms | 0.2954 ms |
| `typical_business_rule` | Approach B (Normalized Execution Plan) | 0.0436 ms | 0.0203 ms |
| `typical_business_rule` | Approach C (Direct JSON Tree Evaluator) | 0.005 ms | 0.0025 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.3442 ms | 0.0459 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.6068 ms | 0.5782 ms |
| `typical_business_rule` | Canonical Condition (Prepared Plan Diagnostic) | 0.2668 ms | 0.0426 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.4462 ms | 0.2602 ms |
| `nested_and_or_groups` | Approach B (Normalized Execution Plan) | 0.054 ms | 0.0254 ms |
| `nested_and_or_groups` | Approach C (Direct JSON Tree Evaluator) | 0.0046 ms | 0.0026 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.3301 ms | 0.0522 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.7387 ms | 0.7192 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Plan Diagnostic) | 0.3221 ms | 0.0965 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 0.8113 ms | 0.7037 ms |
| `deep_nested_complex` | Approach B (Normalized Execution Plan) | 0.069 ms | 0.0433 ms |
| `deep_nested_complex` | Approach C (Direct JSON Tree Evaluator) | 0.0049 ms | 0.0026 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.5693 ms | 0.124 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.4758 ms | 1.4147 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Plan Diagnostic) | 0.4555 ms | 0.0742 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.5228 ms | 0.3062 ms |
| `collection_predicate` | Approach B (Normalized Execution Plan) | 0.0602 ms | 0.0368 ms |
| `collection_predicate` | Approach C (Direct JSON Tree Evaluator) | 0.006 ms | 0.0508 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.416 ms | 0.0558 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.9687 ms | 0.9823 ms |
| `collection_predicate` | Canonical Condition (Prepared Plan Diagnostic) | 0.216 ms | 0.0438 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.4143 ms | 0.2591 ms |
| `edge_case_membership_in_not_in` | Approach B (Normalized Execution Plan) | 0.0382 ms | 0.0175 ms |
| `edge_case_membership_in_not_in` | Approach C (Direct JSON Tree Evaluator) | 0.0049 ms | 0.0026 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.259 ms | 0.038 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.5207 ms | 0.5392 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Plan Diagnostic) | 0.1483 ms | 0.0771 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.4689 ms | 0.2874 ms |
| `edge_case_contains_not_contains` | Approach B (Normalized Execution Plan) | 0.0416 ms | 0.0161 ms |
| `edge_case_contains_not_contains` | Approach C (Direct JSON Tree Evaluator) | 0.0052 ms | 0.0026 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.2757 ms | 0.0352 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.7398 ms | 0.8154 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Plan Diagnostic) | 0.1357 ms | 0.0298 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.1846 ms | 0.049 ms |
| `edge_case_has_changed` | Approach B (Normalized Execution Plan) | 0.0224 ms | 0.0094 ms |
| `edge_case_has_changed` | Approach C (Direct JSON Tree Evaluator) | 0.0054 ms | 0.0028 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.2213 ms | 0.0892 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.2798 ms | 0.1408 ms |
| `edge_case_none_vs_missing_field` | Approach B (Normalized Execution Plan) | 0.0261 ms | 0.0099 ms |
| `edge_case_none_vs_missing_field` | Approach C (Direct JSON Tree Evaluator) | 0.0051 ms | 0.0029 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.1542 ms | 0.022 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.3976 ms | 0.4257 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Plan Diagnostic) | 0.0675 ms | 0.0172 ms |

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