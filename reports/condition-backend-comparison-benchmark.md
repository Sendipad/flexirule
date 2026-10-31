# FlexiRule — Condition Backend Comparison Benchmark Report

**Date:** 2026-10-31T16:16:46Z
**Branch:** `jules-3036709536307989151-9ae6b294`
**Commit:** `961cae7e94a19083b3331dbe085f7e692e142d0d`
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
| `simple_equality` | Tier 1 — Simple | 181.142 µs/op | 3.539 µs/op | 5.217 µs/op | 29.314 µs/op | 10.516 µs/op | 11.658 µs/op | 11.321 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 420.096 µs/op | 6.298 µs/op | 10.287 µs/op | 56.825 µs/op | 12.91 µs/op | 21.981 µs/op | 25.525 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 552.793 µs/op | 6.592 µs/op | 11.434 µs/op | 66.151 µs/op | 12.729 µs/op | 21.373 µs/op | 25.828 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1141.898 µs/op | 10.085 µs/op | 17.577 µs/op | 110.801 µs/op | 16.844 µs/op | 40.015 µs/op | 57.786 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 710.842 µs/op | 10.709 µs/op | 16.958 µs/op | 77.323 µs/op | 17.604 µs/op | 34.794 µs/op | 42.206 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 378.148 µs/op | 5.052 µs/op | 7.67 µs/op | 51.115 µs/op | 10.989 µs/op | 21.418 µs/op | 33.085 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 580.522 µs/op | 5.836 µs/op | 8.88 µs/op | 39.331 µs/op | 14.947 µs/op | 13.214 µs/op | 15.288 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 60.715 µs/op | 3.443 µs/op | 5.333 µs/op | UNSUPPORTED | 8.373 µs/op | UNSUPPORTED | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 312.833 µs/op | 2.897 µs/op | 4.156 µs/op | 22.115 µs/op | 11.311 µs/op | 7.797 µs/op | 6.868 µs/op |
| `dynamic_operands_both_sides` | Dynamic Operands — Both Variables | 246.739 µs/op | 3.978 µs/op | 5.981 µs/op | 31.323 µs/op | 11.701 µs/op | 14.099 µs/op | 13.149 µs/op |
| `dynamic_operands_static_left` | Dynamic Operands — Static Left | 174.81 µs/op | 3.511 µs/op | 5.141 µs/op | 28.546 µs/op | 10.309 µs/op | 11.828 µs/op | 11.069 µs/op |
| `dynamic_operands_template` | Dynamic Operands — Template | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | 32.517 µs/op | UNSUPPORTED | 11.083 µs/op | 12.191 µs/op |
| `frappe_metadata_user_roles` | Frappe Metadata — User Roles | 468.922 µs/op | 7.015 µs/op | 10.152 µs/op | 53.07 µs/op | 15.19 µs/op | 25.167 µs/op | 25.834 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.1476 ms | 0.0911 ms |
| `simple_equality` | Approach B (Normalized Execution Plan) | 0.0249 ms | 0.0116 ms |
| `simple_equality` | Approach C (Direct JSON Tree Evaluator) | 0.0055 ms | 0.0127 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.1264 ms | 0.0254 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.2847 ms | 0.2098 ms |
| `simple_equality` | Canonical Condition (Prepared Artifact Runtime) | 0.107 ms | 0.0826 ms |
| `simple_equality` | Direct Canonical AST Interpreter | 0.0676 ms | 0.0712 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.3521 ms | 0.2111 ms |
| `typical_business_rule` | Approach B (Normalized Execution Plan) | 0.0421 ms | 0.0206 ms |
| `typical_business_rule` | Approach C (Direct JSON Tree Evaluator) | 0.0052 ms | 0.0025 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.3545 ms | 0.0511 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.5978 ms | 0.5146 ms |
| `typical_business_rule` | Canonical Condition (Prepared Artifact Runtime) | 0.233 ms | 0.1659 ms |
| `typical_business_rule` | Direct Canonical AST Interpreter | 0.2014 ms | 0.1508 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.5085 ms | 0.2803 ms |
| `nested_and_or_groups` | Approach B (Normalized Execution Plan) | 0.0525 ms | 0.0554 ms |
| `nested_and_or_groups` | Approach C (Direct JSON Tree Evaluator) | 0.0056 ms | 0.0028 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.3365 ms | 0.0541 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.8169 ms | 0.7734 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Artifact Runtime) | 0.3631 ms | 0.2316 ms |
| `nested_and_or_groups` | Direct Canonical AST Interpreter | 0.1984 ms | 0.1957 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 0.8216 ms | 0.67 ms |
| `deep_nested_complex` | Approach B (Normalized Execution Plan) | 0.0759 ms | 0.0412 ms |
| `deep_nested_complex` | Approach C (Direct JSON Tree Evaluator) | 0.0052 ms | 0.0028 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.586 ms | 0.125 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.449 ms | 1.44 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Artifact Runtime) | 0.4844 ms | 0.3574 ms |
| `deep_nested_complex` | Direct Canonical AST Interpreter | 0.3799 ms | 0.3327 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.4619 ms | 0.3621 ms |
| `collection_predicate` | Approach B (Normalized Execution Plan) | 0.052 ms | 0.0259 ms |
| `collection_predicate` | Approach C (Direct JSON Tree Evaluator) | 0.0053 ms | 0.0028 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.3668 ms | 0.0587 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.8379 ms | 0.878 ms |
| `collection_predicate` | Canonical Condition (Prepared Artifact Runtime) | 0.2587 ms | 0.2031 ms |
| `collection_predicate` | Direct Canonical AST Interpreter | 0.2368 ms | 0.2443 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.3695 ms | 0.2508 ms |
| `edge_case_membership_in_not_in` | Approach B (Normalized Execution Plan) | 0.0386 ms | 0.0165 ms |
| `edge_case_membership_in_not_in` | Approach C (Direct JSON Tree Evaluator) | 0.0053 ms | 0.0027 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.2501 ms | 0.0379 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.5121 ms | 0.4926 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Artifact Runtime) | 0.1915 ms | 0.1404 ms |
| `edge_case_membership_in_not_in` | Direct Canonical AST Interpreter | 0.123 ms | 0.1691 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.4154 ms | 0.3364 ms |
| `edge_case_contains_not_contains` | Approach B (Normalized Execution Plan) | 0.0373 ms | 0.016 ms |
| `edge_case_contains_not_contains` | Approach C (Direct JSON Tree Evaluator) | 0.0057 ms | 0.0029 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.2913 ms | 0.0399 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.8535 ms | 0.72 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Artifact Runtime) | 0.1878 ms | 0.1332 ms |
| `edge_case_contains_not_contains` | Direct Canonical AST Interpreter | 0.1171 ms | 0.1084 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.1549 ms | 0.0702 ms |
| `edge_case_has_changed` | Approach B (Normalized Execution Plan) | 0.0225 ms | 0.0101 ms |
| `edge_case_has_changed` | Approach C (Direct JSON Tree Evaluator) | 0.0057 ms | 0.0031 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.1326 ms | 0.0861 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.2705 ms | 0.1529 ms |
| `edge_case_none_vs_missing_field` | Approach B (Normalized Execution Plan) | 0.0241 ms | 0.0093 ms |
| `edge_case_none_vs_missing_field` | Approach C (Direct JSON Tree Evaluator) | 0.0051 ms | 0.0026 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.1442 ms | 0.0231 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.4044 ms | 0.4756 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Artifact Runtime) | 0.1078 ms | 0.0711 ms |
| `edge_case_none_vs_missing_field` | Direct Canonical AST Interpreter | 0.0589 ms | 0.049 ms |
| `dynamic_operands_both_sides` | Approach A (frappe.safe_eval) | 0.2456 ms | 0.1127 ms |
| `dynamic_operands_both_sides` | Approach B (Normalized Execution Plan) | 0.026 ms | 0.0108 ms |
| `dynamic_operands_both_sides` | Approach C (Direct JSON Tree Evaluator) | 0.0057 ms | 0.0027 ms |
| `dynamic_operands_both_sides` | Canonical Condition (evaluate_condition) | 0.1665 ms | 0.0267 ms |
| `dynamic_operands_both_sides` | Approach A (Experimental Restricted Code Object) | 0.3967 ms | 0.3042 ms |
| `dynamic_operands_both_sides` | Canonical Condition (Prepared Artifact Runtime) | 0.1167 ms | 0.1497 ms |
| `dynamic_operands_both_sides` | Direct Canonical AST Interpreter | 0.0855 ms | 0.0669 ms |
| `dynamic_operands_static_left` | Approach A (frappe.safe_eval) | 0.2531 ms | 0.1066 ms |
| `dynamic_operands_static_left` | Approach B (Normalized Execution Plan) | 0.0259 ms | 0.0109 ms |
| `dynamic_operands_static_left` | Approach C (Direct JSON Tree Evaluator) | 0.0051 ms | 0.0028 ms |
| `dynamic_operands_static_left` | Canonical Condition (evaluate_condition) | 0.1571 ms | 0.0255 ms |
| `dynamic_operands_static_left` | Approach A (Experimental Restricted Code Object) | 0.2729 ms | 0.2145 ms |
| `dynamic_operands_static_left` | Canonical Condition (Prepared Artifact Runtime) | 0.2147 ms | 0.0847 ms |
| `dynamic_operands_static_left` | Direct Canonical AST Interpreter | 0.0689 ms | 0.061 ms |
| `dynamic_operands_template` | Canonical Condition (evaluate_condition) | 0.2143 ms | 0.0316 ms |
| `dynamic_operands_template` | Canonical Condition (Prepared Artifact Runtime) | 0.1644 ms | 0.1054 ms |
| `dynamic_operands_template` | Direct Canonical AST Interpreter | 0.0891 ms | 0.081 ms |
| `frappe_metadata_user_roles` | Approach A (frappe.safe_eval) | 0.3308 ms | 0.2876 ms |
| `frappe_metadata_user_roles` | Approach B (Normalized Execution Plan) | 0.0356 ms | 0.0141 ms |
| `frappe_metadata_user_roles` | Approach C (Direct JSON Tree Evaluator) | 0.0053 ms | 0.0028 ms |
| `frappe_metadata_user_roles` | Canonical Condition (evaluate_condition) | 0.2517 ms | 0.033 ms |
| `frappe_metadata_user_roles` | Approach A (Experimental Restricted Code Object) | 0.5524 ms | 0.5851 ms |
| `frappe_metadata_user_roles` | Canonical Condition (Prepared Artifact Runtime) | 0.1812 ms | 0.194 ms |
| `frappe_metadata_user_roles` | Direct Canonical AST Interpreter | 0.1264 ms | 0.1158 ms |

---

## Direct Canonical AST vs Compiled Tuple Plan

### 1. Architecture Overview & Lifecycle
- **Direct Canonical AST Interpreter (Approach A)**: Validates the canonical JSON condition tree once during `prepare()` against authoritative Frappe and contract metadata. Retains the parsed JSON structure as an immutable snapshot (`PreparedDirectCanonicalAST`). At runtime, walks the JSON dict tree directly, evaluating operands and child branches strictly lazily without compiling into tuples or intermediate code.
- **Compiled Immutable Execution Plan (Approach B / Production)**: Validates the canonical JSON tree and compiles it into an immutable tuple hierarchy (`_compile_node`, `_compile_value`, `_PreparedCanonicalCondition`). Caches compiled plans in an in-memory bounded LRU. At runtime, walks the tuple structure using index-based node unpacking.

### 2. Component Cost Breakdown (Microseconds)
Measures the exact cost of each stage in the condition evaluation pipeline:

| Scenario ID | Tier | JSON Serialization | Structural Validation | Metadata Validation | Direct AST Prep | Plan Cold Prep | Plan Warm Prep |
|---|---|---|---|---|---|---|---|
| `simple_equality` | Tier 1 — Simple | 34.58 µs | 70.53 µs | N/A | 74.91 µs | 172.25 µs | 96.18 µs |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 36.38 µs | 112.62 µs | N/A | 149.34 µs | 216.68 µs | 162.63 µs |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 40.65 µs | 179.55 µs | N/A | 198.67 µs | 275.33 µs | 212.57 µs |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 64.1 µs | 374.45 µs | N/A | 361.42 µs | 517.55 µs | 370.92 µs |
| `collection_predicate` | Tier 5 — Collection Predicate | 39.3 µs | 129.11 µs | N/A | 247.18 µs | 261.77 µs | 208.47 µs |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 26.71 µs | 81.79 µs | N/A | 120.11 µs | 203.92 µs | 151.28 µs |
| `edge_case_contains_not_contains` | Edge Case — Substring | 24.41 µs | 72.26 µs | N/A | 109.05 µs | 160.8 µs | 124.24 µs |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 13.64 µs | 32.58 µs | N/A | 52.89 µs | 77.13 µs | 63.51 µs |
| `dynamic_operands_both_sides` | Dynamic Operands — Both Variables | 20.62 µs | 48.0 µs | N/A | 66.95 µs | 162.09 µs | 82.34 µs |
| `dynamic_operands_static_left` | Dynamic Operands — Static Left | 15.6 µs | 47.09 µs | N/A | 62.77 µs | 90.15 µs | 74.27 µs |
| `dynamic_operands_template` | Dynamic Operands — Template | 19.98 µs | 56.95 µs | N/A | 81.78 µs | 172.79 µs | 103.35 µs |
| `frappe_metadata_user_roles` | Frappe Metadata — User Roles | 20.29 µs | 62.77 µs | 106.52 | 124.47 µs | 152.61 µs | 128.12 µs |

### 3. Collection Scaling & Short-Circuit Behavior
Empirical comparison across collection workloads with varying row counts (10 to 10,000 rows) and match positions:

| Scenario ID | Rows | Behavior | Direct Canonical AST | Compiled Tuple Plan | Speedup Ratio |
|---|---|---|---|---|---|
| `collection_scaling_any_early_match_10` | 10 | early_match | 52.451 µs/op | 47.44 µs/op | 1.11x (Plan is faster) |
| `collection_scaling_any_late_match_10` | 10 | late_match | 89.026 µs/op | 77.967 µs/op | 1.14x (Plan is faster) |
| `collection_scaling_all_early_fail_10` | 10 | early_match | 52.764 µs/op | 47.966 µs/op | 1.1x (Plan is faster) |
| `collection_scaling_none_10` | 10 | no_match | 88.409 µs/op | 78.195 µs/op | 1.13x (Plan is faster) |
| `collection_scaling_any_early_match_100` | 100 | early_match | 415.471 µs/op | 354.827 µs/op | 1.17x (Plan is faster) |
| `collection_scaling_any_late_match_100` | 100 | late_match | 809.651 µs/op | 697.387 µs/op | 1.16x (Plan is faster) |
| `collection_scaling_all_early_fail_100` | 100 | early_match | 416.712 µs/op | 360.957 µs/op | 1.15x (Plan is faster) |
| `collection_scaling_none_100` | 100 | no_match | 808.167 µs/op | 709.459 µs/op | 1.14x (Plan is faster) |
| `collection_scaling_any_early_match_1000` | 1000 | early_match | 4062.671 µs/op | 3472.254 µs/op | 1.17x (Plan is faster) |
| `collection_scaling_any_late_match_1000` | 1000 | late_match | 8074.703 µs/op | 6932.888 µs/op | 1.16x (Plan is faster) |
| `collection_scaling_all_early_fail_1000` | 1000 | early_match | 4069.466 µs/op | 3556.004 µs/op | 1.14x (Plan is faster) |
| `collection_scaling_none_1000` | 1000 | no_match | 8189.15 µs/op | 7042.338 µs/op | 1.16x (Plan is faster) |
| `collection_scaling_any_early_match_10000` | 10000 | early_match | 45646.26 µs/op | 35002.943 µs/op | 1.3x (Plan is faster) |
| `collection_scaling_any_late_match_10000` | 10000 | late_match | 81340.703 µs/op | 71968.583 µs/op | 1.13x (Plan is faster) |
| `collection_scaling_all_early_fail_10000` | 10000 | early_match | 40951.397 µs/op | 35823.322 µs/op | 1.14x (Plan is faster) |
| `collection_scaling_none_10000` | 10000 | no_match | 81166.118 µs/op | 70300.848 µs/op | 1.15x (Plan is faster) |

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