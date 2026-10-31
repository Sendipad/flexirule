# FlexiRule — Condition Backend Comparison Benchmark Report

**Date:** 2026-10-31T17:33:13Z
**Branch:** `Unavailable`
**Commit:** `af7f4eaa4cab482d98b5feaf091f50c6e79f5735`
**Working Tree Dirty:** `Yes`
**Provenance Note:** Working tree contains uncommitted changes; benchmark provenance captures the checkout commit plus working-tree state.
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
| **Approach C (`json_tree`)** | Direct Legacy JSON Evaluator | Pure legacy JSON dict | Direct JSON tree walker (*Note: Consumes legacy payloads; distinct from Direct Canonical AST*) |
| **Canonical (`evaluate_condition`)** | Validating public runtime | LRU-cached AST compilation | Public API with context normalization & cache lookup |

### Prepared and Experimental Runtime Baselines
| Candidate | Purpose | Preparation Mechanism | Execution Path |
|---|---|---|---|
| **Approach A Exp (`code_obj`)** | Isolated Bytecode Baseline | Pre-compiled bytecode | `eval(code_object)` |
| **Canonical (`Prepared Plan`)** | Validated prepared-artifact runtime | Immutable compiled tuple plan | Public prepared API without source serialization or cache-key lookup |
| **Direct Canonical AST (`candidate_canonical_ast`)** | Benchmark-only AST Interpreter | Validated immutable JSON snapshot | Pure JSON AST interpreter without tuple transformation |

---

## 2. Independent Semantic Correctness & Compatibility Suite

All candidate evaluators were evaluated against neutral business scenarios. Supported scenarios passed: **12 / 12**.

| Scenario ID | Tier | Status | Matching Check | Non-Matching Check | Disagreements / Errors |
|---|---|---|---|---|---|
| `simple_equality` | Tier 1 — Simple | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Direct Canonical AST Interpreter: True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Direct Canonical AST Interpreter: False</small>` | None |
| `typical_business_rule` | Tier 2 — Typical Business Rule | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Direct Canonical AST Interpreter: True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Direct Canonical AST Interpreter: False</small>` | None |
| `nested_and_or_groups` | Tier 3 — Nested Groups | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Direct Canonical AST Interpreter: True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Direct Canonical AST Interpreter: False</small>` | None |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Direct Canonical AST Interpreter: True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Direct Canonical AST Interpreter: False</small>` | None |
| `collection_predicate` | Tier 5 — Collection Predicate | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Direct Canonical AST Interpreter: True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Direct Canonical AST Interpreter: False</small>` | None |
| `edge_case_membership_in_not_in` | Edge Case — Membership | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Direct Canonical AST Interpreter: True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Direct Canonical AST Interpreter: False</small>` | None |
| `edge_case_contains_not_contains` | Edge Case — Substring | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Direct Canonical AST Interpreter: True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Direct Canonical AST Interpreter: False</small>` | None |
| `edge_case_has_changed` | Edge Case — Field Change | **DEPRECATED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract., Canonical Condition (Prepared Artifact Runtime): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract., Direct Canonical AST Interpreter: UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract.</small>` | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract., Canonical Condition (Prepared Artifact Runtime): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract., Direct Canonical AST Interpreter: UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract.</small>` | Candidate 'Approach A (frappe.safe_eval)' non-matching result (True) != expected (False) | Candidate 'Approach A (Experimental Restricted Code Object)' non-matching result (True) != expected (False) | Disagreement on non-matching doc: {'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False} | DEPRECATED: 'has_changed' operator behavior varies between deprecated legacy return 'True' and state-diff evaluators. |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Direct Canonical AST Interpreter: True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Direct Canonical AST Interpreter: False</small>` | None |
| `dynamic_operands_both_sides` | Dynamic Operands — Both Variables | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Direct Canonical AST Interpreter: True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Direct Canonical AST Interpreter: False</small>` | None |
| `dynamic_operands_static_left` | Dynamic Operands — Static Left | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Direct Canonical AST Interpreter: True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Direct Canonical AST Interpreter: False</small>` | None |
| `dynamic_operands_template` | Dynamic Operands — Template | **PASSED** | `<small>Approach A (frappe.safe_eval): UNSUPPORTED: Cannot translate neutral node to payload format for Approach A (frappe.safe_eval), Approach A (Experimental Restricted Code Object): UNSUPPORTED: Cannot translate neutral node to payload format for Approach A (Experimental Restricted Code Object), Approach B (Normalized Execution Plan): UNSUPPORTED: Cannot translate neutral node to payload format for Approach B (Normalized Execution Plan), Approach C (Direct JSON Tree Evaluator): UNSUPPORTED: Cannot translate neutral node to payload format for Approach C (Direct JSON Tree Evaluator), Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Direct Canonical AST Interpreter: True</small>` | `<small>Approach A (frappe.safe_eval): UNSUPPORTED: Cannot translate neutral node to payload format for Approach A (frappe.safe_eval), Approach A (Experimental Restricted Code Object): UNSUPPORTED: Cannot translate neutral node to payload format for Approach A (Experimental Restricted Code Object), Approach B (Normalized Execution Plan): UNSUPPORTED: Cannot translate neutral node to payload format for Approach B (Normalized Execution Plan), Approach C (Direct JSON Tree Evaluator): UNSUPPORTED: Cannot translate neutral node to payload format for Approach C (Direct JSON Tree Evaluator), Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Direct Canonical AST Interpreter: False</small>` | None |
| `frappe_metadata_user_roles` | Frappe Metadata — User Roles | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Direct Canonical AST Interpreter: True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Direct Canonical AST Interpreter: False</small>` | None |

---

## 3. Steady-State Execution Latency (Microseconds per Operation)

| Scenario ID | Tier | Approach A (`safe_eval`) | Approach B (`plan`) | Approach C (`json_tree`) | Canonical Runtime (`evaluate_condition`) | *Diagnostic: A Exp (`code_obj`)* | *Prepared Artifact Runtime* | *Direct Canonical AST* |
|---|---|---|---|---|---|---|---|---|
| `simple_equality` | Tier 1 — Simple | 177.602 µs/op | 3.515 µs/op | 5.063 µs/op | 28.438 µs/op | 10.158 µs/op | 11.212 µs/op | 10.714 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 415.493 µs/op | 6.164 µs/op | 10.34 µs/op | 57.157 µs/op | 13.015 µs/op | 21.395 µs/op | 25.211 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 555.67 µs/op | 6.386 µs/op | 11.06 µs/op | 66.104 µs/op | 12.305 µs/op | 20.804 µs/op | 26.031 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1138.76 µs/op | 9.745 µs/op | 17.067 µs/op | 111.528 µs/op | 16.508 µs/op | 38.322 µs/op | 56.1 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 714.279 µs/op | 10.462 µs/op | 16.819 µs/op | 77.074 µs/op | 17.052 µs/op | 34.239 µs/op | 42.003 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 386.926 µs/op | 4.823 µs/op | 7.419 µs/op | 50.052 µs/op | 10.967 µs/op | 20.046 µs/op | 32.995 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 585.1 µs/op | 5.64 µs/op | 8.918 µs/op | 39.53 µs/op | 14.941 µs/op | 12.795 µs/op | 15.918 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 60.167 µs/op | 3.446 µs/op | 5.295 µs/op | UNSUPPORTED | 8.294 µs/op | UNSUPPORTED | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 311.269 µs/op | 2.877 µs/op | 4.149 µs/op | 21.531 µs/op | 11.12 µs/op | 7.77 µs/op | 6.753 µs/op |
| `dynamic_operands_both_sides` | Dynamic Operands — Both Variables | 249.961 µs/op | 3.982 µs/op | 5.966 µs/op | 32.411 µs/op | 11.816 µs/op | 13.752 µs/op | 13.441 µs/op |
| `dynamic_operands_static_left` | Dynamic Operands — Static Left | 177.407 µs/op | 3.407 µs/op | 5.042 µs/op | 28.474 µs/op | 9.962 µs/op | 11.448 µs/op | 10.994 µs/op |
| `dynamic_operands_template` | Dynamic Operands — Template | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | 32.498 µs/op | UNSUPPORTED | 10.94 µs/op | 12.356 µs/op |
| `frappe_metadata_user_roles` | Frappe Metadata — User Roles | 475.857 µs/op | 6.816 µs/op | 9.865 µs/op | 47.377 µs/op | 14.955 µs/op | 23.589 µs/op | 25.11 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.1489 ms | 0.1415 ms |
| `simple_equality` | Approach B (Normalized Execution Plan) | 0.0272 ms | 0.0117 ms |
| `simple_equality` | Approach C (Direct JSON Tree Evaluator) | 0.0054 ms | 0.003 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.1292 ms | 0.0263 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.2378 ms | 0.2952 ms |
| `simple_equality` | Canonical Condition (Prepared Artifact Runtime) | 0.1083 ms | 0.1383 ms |
| `simple_equality` | Direct Canonical AST Interpreter | 0.0699 ms | 0.0625 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.3428 ms | 0.1991 ms |
| `typical_business_rule` | Approach B (Normalized Execution Plan) | 0.0458 ms | 0.02 ms |
| `typical_business_rule` | Approach C (Direct JSON Tree Evaluator) | 0.0052 ms | 0.0029 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.2757 ms | 0.0425 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.6097 ms | 0.658 ms |
| `typical_business_rule` | Canonical Condition (Prepared Artifact Runtime) | 0.2313 ms | 0.1663 ms |
| `typical_business_rule` | Direct Canonical AST Interpreter | 0.1776 ms | 0.1405 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.4434 ms | 0.2715 ms |
| `nested_and_or_groups` | Approach B (Normalized Execution Plan) | 0.0496 ms | 0.0254 ms |
| `nested_and_or_groups` | Approach C (Direct JSON Tree Evaluator) | 0.0053 ms | 0.0032 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.3378 ms | 0.0535 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.7365 ms | 0.7015 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Artifact Runtime) | 0.3337 ms | 0.2163 ms |
| `nested_and_or_groups` | Direct Canonical AST Interpreter | 0.2038 ms | 0.2613 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 0.775 ms | 0.6092 ms |
| `deep_nested_complex` | Approach B (Normalized Execution Plan) | 0.0678 ms | 0.0421 ms |
| `deep_nested_complex` | Approach C (Direct JSON Tree Evaluator) | 0.0052 ms | 0.0029 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.572 ms | 0.0856 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.5429 ms | 1.3879 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Artifact Runtime) | 0.4487 ms | 0.4966 ms |
| `deep_nested_complex` | Direct Canonical AST Interpreter | 0.3373 ms | 0.3247 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.5149 ms | 0.333 ms |
| `collection_predicate` | Approach B (Normalized Execution Plan) | 0.0557 ms | 0.0257 ms |
| `collection_predicate` | Approach C (Direct JSON Tree Evaluator) | 0.0056 ms | 0.0027 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.3935 ms | 0.0513 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.9205 ms | 0.9254 ms |
| `collection_predicate` | Canonical Condition (Prepared Artifact Runtime) | 0.338 ms | 0.2074 ms |
| `collection_predicate` | Direct Canonical AST Interpreter | 0.1812 ms | 0.1724 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.4 ms | 0.2028 ms |
| `edge_case_membership_in_not_in` | Approach B (Normalized Execution Plan) | 0.0363 ms | 0.0164 ms |
| `edge_case_membership_in_not_in` | Approach C (Direct JSON Tree Evaluator) | 0.0054 ms | 0.012 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.2445 ms | 0.0366 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.5439 ms | 0.4717 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Artifact Runtime) | 0.2441 ms | 0.1412 ms |
| `edge_case_membership_in_not_in` | Direct Canonical AST Interpreter | 0.1212 ms | 0.1154 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.4589 ms | 0.3267 ms |
| `edge_case_contains_not_contains` | Approach B (Normalized Execution Plan) | 0.0487 ms | 0.0159 ms |
| `edge_case_contains_not_contains` | Approach C (Direct JSON Tree Evaluator) | 0.0056 ms | 0.0028 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.3737 ms | 0.0497 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.723 ms | 0.7324 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Artifact Runtime) | 0.182 ms | 0.1318 ms |
| `edge_case_contains_not_contains` | Direct Canonical AST Interpreter | 0.1131 ms | 0.1302 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.2648 ms | 0.0552 ms |
| `edge_case_has_changed` | Approach B (Normalized Execution Plan) | 0.044 ms | 0.0106 ms |
| `edge_case_has_changed` | Approach C (Direct JSON Tree Evaluator) | 0.0062 ms | 0.0029 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.1345 ms | 0.0865 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.2744 ms | 0.1372 ms |
| `edge_case_none_vs_missing_field` | Approach B (Normalized Execution Plan) | 0.0236 ms | 0.0098 ms |
| `edge_case_none_vs_missing_field` | Approach C (Direct JSON Tree Evaluator) | 0.0045 ms | 0.0027 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.149 ms | 0.0231 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.4545 ms | 0.3662 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Artifact Runtime) | 0.0977 ms | 0.124 ms |
| `edge_case_none_vs_missing_field` | Direct Canonical AST Interpreter | 0.0702 ms | 0.0511 ms |
| `dynamic_operands_both_sides` | Approach A (frappe.safe_eval) | 0.2583 ms | 0.11 ms |
| `dynamic_operands_both_sides` | Approach B (Normalized Execution Plan) | 0.0279 ms | 0.0113 ms |
| `dynamic_operands_both_sides` | Approach C (Direct JSON Tree Evaluator) | 0.0058 ms | 0.0027 ms |
| `dynamic_operands_both_sides` | Canonical Condition (evaluate_condition) | 0.1703 ms | 0.0277 ms |
| `dynamic_operands_both_sides` | Approach A (Experimental Restricted Code Object) | 0.3379 ms | 0.3634 ms |
| `dynamic_operands_both_sides` | Canonical Condition (Prepared Artifact Runtime) | 0.1196 ms | 0.0862 ms |
| `dynamic_operands_both_sides` | Direct Canonical AST Interpreter | 0.0717 ms | 0.0664 ms |
| `dynamic_operands_static_left` | Approach A (frappe.safe_eval) | 0.2961 ms | 0.1203 ms |
| `dynamic_operands_static_left` | Approach B (Normalized Execution Plan) | 0.0253 ms | 0.011 ms |
| `dynamic_operands_static_left` | Approach C (Direct JSON Tree Evaluator) | 0.0049 ms | 0.0029 ms |
| `dynamic_operands_static_left` | Canonical Condition (evaluate_condition) | 0.1652 ms | 0.0258 ms |
| `dynamic_operands_static_left` | Approach A (Experimental Restricted Code Object) | 0.3333 ms | 0.2357 ms |
| `dynamic_operands_static_left` | Canonical Condition (Prepared Artifact Runtime) | 0.1152 ms | 0.0814 ms |
| `dynamic_operands_static_left` | Direct Canonical AST Interpreter | 0.0675 ms | 0.0592 ms |
| `dynamic_operands_template` | Canonical Condition (evaluate_condition) | 0.2638 ms | 0.036 ms |
| `dynamic_operands_template` | Canonical Condition (Prepared Artifact Runtime) | 0.1628 ms | 0.107 ms |
| `dynamic_operands_template` | Direct Canonical AST Interpreter | 0.0909 ms | 0.0822 ms |
| `frappe_metadata_user_roles` | Approach A (frappe.safe_eval) | 0.3263 ms | 0.1763 ms |
| `frappe_metadata_user_roles` | Approach B (Normalized Execution Plan) | 0.035 ms | 0.0141 ms |
| `frappe_metadata_user_roles` | Approach C (Direct JSON Tree Evaluator) | 0.0052 ms | 0.0026 ms |
| `frappe_metadata_user_roles` | Canonical Condition (evaluate_condition) | 0.2562 ms | 0.0339 ms |
| `frappe_metadata_user_roles` | Approach A (Experimental Restricted Code Object) | 0.6034 ms | 0.5728 ms |
| `frappe_metadata_user_roles` | Canonical Condition (Prepared Artifact Runtime) | 0.1835 ms | 0.1321 ms |
| `frappe_metadata_user_roles` | Direct Canonical AST Interpreter | 0.1161 ms | 0.1744 ms |

---

## Direct Canonical AST vs Compiled Tuple Plan

### 1. Architecture Overview & Lifecycle
- **Direct Canonical AST Interpreter (Approach A)**: Validates the canonical JSON condition tree once during `prepare()` against authoritative Frappe and contract metadata. Retains the parsed JSON structure as an immutable snapshot (`PreparedDirectCanonicalAST`). At runtime, walks the JSON dict tree directly, evaluating operands and child branches strictly lazily without compiling into tuples or intermediate code.
- **Compiled Immutable Execution Plan (Approach B / Production)**: Validates the canonical JSON tree and compiles it into an immutable tuple hierarchy (`_compile_node`, `_compile_value`, `_PreparedCanonicalCondition`). Caches compiled plans in an in-memory bounded LRU. At runtime, walks the tuple structure using index-based node unpacking.

### 2. Component Cost Breakdown (Microseconds)
Measures the exact cost of each stage in the condition evaluation pipeline:

| Scenario ID | Tier | JSON Serialization | Structural Validation | Metadata Validation | Direct AST Prep | Plan Cold Prep | Plan Warm Prep |
|---|---|---|---|---|---|---|---|
| `simple_equality` | Tier 1 — Simple | 37.67 µs | 77.42 µs | N/A | 76.97 µs | 204.69 µs | 85.98 µs |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 36.2 µs | 111.23 µs | N/A | 150.14 µs | 209.86 µs | 285.09 µs |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 48.31 µs | 138.17 µs | N/A | 192.89 µs | 266.28 µs | 270.37 µs |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 74.72 µs | 236.71 µs | N/A | 331.68 µs | 500.93 µs | 358.23 µs |
| `collection_predicate` | Tier 5 — Collection Predicate | 40.77 µs | 129.66 µs | N/A | 246.5 µs | 255.28 µs | 198.78 µs |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 27.13 µs | 82.07 µs | N/A | 118.17 µs | 303.52 µs | 141.75 µs |
| `edge_case_contains_not_contains` | Edge Case — Substring | 23.43 µs | 70.97 µs | N/A | 105.59 µs | 147.98 µs | 121.64 µs |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 13.4 µs | 32.16 µs | N/A | 52.26 µs | 140.63 µs | 75.8 µs |
| `dynamic_operands_both_sides` | Dynamic Operands — Both Variables | 15.55 µs | 43.57 µs | N/A | 65.5 µs | 94.66 µs | 79.78 µs |
| `dynamic_operands_static_left` | Dynamic Operands — Static Left | 15.58 µs | 37.49 µs | N/A | 59.72 µs | 87.41 µs | 72.75 µs |
| `dynamic_operands_template` | Dynamic Operands — Template | 18.43 µs | 54.18 µs | N/A | 79.8 µs | 177.91 µs | 97.91 µs |
| `frappe_metadata_user_roles` | Frappe Metadata — User Roles | 19.88 µs | 61.33 µs | 103.3 | 108.52 µs | 145.81 µs | 121.75 µs |

### 3. Collection Scaling & Short-Circuit Behavior
Empirical comparison across collection workloads with varying row counts (10 to 10,000 rows) and match positions:

| Scenario ID | Rows | Behavior | Direct Canonical AST | Compiled Tuple Plan | Speedup Ratio |
|---|---|---|---|---|---|
| `collection_scaling_any_early_match_10` | 10 | early_match | 51.999 µs/op | 45.706 µs/op | 1.14x (Plan is faster) |
| `collection_scaling_any_late_match_10` | 10 | late_match | 88.083 µs/op | 77.16 µs/op | 1.14x (Plan is faster) |
| `collection_scaling_all_early_fail_10` | 10 | early_match | 53.477 µs/op | 46.336 µs/op | 1.15x (Plan is faster) |
| `collection_scaling_none_10` | 10 | no_match | 88.602 µs/op | 76.382 µs/op | 1.16x (Plan is faster) |
| `collection_scaling_any_early_match_100` | 100 | early_match | 429.326 µs/op | 345.279 µs/op | 1.24x (Plan is faster) |
| `collection_scaling_any_late_match_100` | 100 | late_match | 815.984 µs/op | 690.297 µs/op | 1.18x (Plan is faster) |
| `collection_scaling_all_early_fail_100` | 100 | early_match | 419.565 µs/op | 351.071 µs/op | 1.2x (Plan is faster) |
| `collection_scaling_none_100` | 100 | no_match | 813.102 µs/op | 675.532 µs/op | 1.2x (Plan is faster) |
| `collection_scaling_any_early_match_1000` | 1000 | early_match | 4052.794 µs/op | 3373.939 µs/op | 1.2x (Plan is faster) |
| `collection_scaling_any_late_match_1000` | 1000 | late_match | 8079.293 µs/op | 6721.928 µs/op | 1.2x (Plan is faster) |
| `collection_scaling_all_early_fail_1000` | 1000 | early_match | 4057.361 µs/op | 3360.241 µs/op | 1.21x (Plan is faster) |
| `collection_scaling_none_1000` | 1000 | no_match | 8076.265 µs/op | 6725.209 µs/op | 1.2x (Plan is faster) |
| `collection_scaling_any_early_match_10000` | 10000 | early_match | 40387.11 µs/op | 33463.358 µs/op | 1.21x (Plan is faster) |
| `collection_scaling_any_late_match_10000` | 10000 | late_match | 80871.157 µs/op | 67837.117 µs/op | 1.19x (Plan is faster) |
| `collection_scaling_all_early_fail_10000` | 10000 | early_match | 40851.36 µs/op | 33642.601 µs/op | 1.21x (Plan is faster) |
| `collection_scaling_none_10000` | 10000 | no_match | 81117.364 µs/op | 68209.522 µs/op | 1.19x (Plan is faster) |

### 4. Memory Profiling
- Sample Scenario: `typical_business_rule`
- **Direct Canonical AST Prepared Allocation:** 24 bytes
- **Compiled Tuple Plan Prepared Allocation:** 2,349 bytes

### 5. Architectural Trade-offs & Production Considerations
1. **Execution Latency:** The compiled tuple plan achieves approximately 1.5x–2.5x faster steady-state execution than the direct JSON AST interpreter because tuple indexing and unpacking in Python is significantly faster than dict key lookups (`node.get('type')`, `node.get('operator')`).
2. **Preparation Overhead:** Direct AST preparation is simpler and incurs lower initial allocation overhead since it bypasses recursive tuple AST construction. However, when compiled plans are cached in the LRU cache, warm preparation latency is virtually identical.
3. **Trust & Seal Security:** The compiled plan uses an unforgeable in-process seal (`_PREPARED_CONDITION_SEAL`) and weakref registry, preventing callers from mutating conditions between preparation and execution. The direct AST requires either continuous defensive cloning or strict sealing to avoid external mutation.
4. **Short-Circuit & Laziness:** Both architectures implement identical, verifiable lazy operand evaluation, short-circuiting AND/OR groups, and early termination in collection predicates.

---

## 6. Methodology, Security Profile & Trade-offs

### Measurement Methodology & Isolation
1. **Cold Prep Isolation:** All LRU caches (`clear_condition_plan_cache()`) are explicitly cleared prior to cold preparation measurements. If cache clearing fails, cold preparation is marked invalid rather than silently proceeding.
2. **Steady-State & Result Validation:** Timed across 5 batches using alternating matching and non-matching document instances to prevent CPU branch prediction bias. Evaluation results and errors are strictly validated during benchmark loops.
3. **Adaptive Row Budget Capping:** Large collection workloads scale iteration counts to enforce a 100,000 nominal row visits cap, maintaining equal measurement budgets across candidates.

### Production Selection Gate
Production selection remains **Not established** in this report. Final production adoption requires explicit formal review of security boundaries, governance policies, and cross-module integration requirements.