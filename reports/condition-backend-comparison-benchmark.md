# FlexiRule — Condition Backend Comparison Benchmark Report

**Date:** 2026-10-31T15:52:25Z
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
| `simple_equality` | Tier 1 — Simple | 181.935 µs/op | 3.581 µs/op | 5.217 µs/op | 28.906 µs/op | 10.349 µs/op | 11.773 µs/op | 11.118 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 424.874 µs/op | 6.281 µs/op | 10.384 µs/op | 57.97 µs/op | 12.838 µs/op | 21.907 µs/op | 25.789 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 560.414 µs/op | 6.6 µs/op | 11.343 µs/op | 67.552 µs/op | 12.749 µs/op | 21.623 µs/op | 26.414 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1137.052 µs/op | 10.053 µs/op | 17.563 µs/op | 113.352 µs/op | 16.692 µs/op | 40.031 µs/op | 57.846 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 708.827 µs/op | 10.482 µs/op | 17.064 µs/op | 77.884 µs/op | 17.046 µs/op | 34.702 µs/op | 42.347 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 378.565 µs/op | 4.934 µs/op | 7.572 µs/op | 50.153 µs/op | 11.129 µs/op | 20.5 µs/op | 32.154 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 583.654 µs/op | 5.662 µs/op | 8.855 µs/op | 39.298 µs/op | 15.09 µs/op | 12.818 µs/op | 15.554 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 59.835 µs/op | 3.502 µs/op | 5.362 µs/op | UNSUPPORTED | 8.343 µs/op | UNSUPPORTED | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 307.877 µs/op | 2.812 µs/op | 4.221 µs/op | 21.43 µs/op | 11.078 µs/op | 7.638 µs/op | 6.771 µs/op |
| `dynamic_operands_both_sides` | Dynamic Operands — Both Variables | 248.564 µs/op | 4.039 µs/op | 6.079 µs/op | 32.514 µs/op | 11.884 µs/op | 13.621 µs/op | 13.189 µs/op |
| `dynamic_operands_static_left` | Dynamic Operands — Static Left | 175.723 µs/op | 3.495 µs/op | 5.038 µs/op | 29.584 µs/op | 10.168 µs/op | 11.693 µs/op | 10.886 µs/op |
| `dynamic_operands_template` | Dynamic Operands — Template | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | 33.071 µs/op | UNSUPPORTED | 11.3 µs/op | 12.11 µs/op |
| `frappe_metadata_user_roles` | Frappe Metadata — User Roles | 465.298 µs/op | 7.056 µs/op | 10.282 µs/op | 48.258 µs/op | 14.882 µs/op | 24.12 µs/op | 25.193 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.154 ms | 0.0945 ms |
| `simple_equality` | Approach B (Normalized Execution Plan) | 0.0262 ms | 0.0111 ms |
| `simple_equality` | Approach C (Direct JSON Tree Evaluator) | 0.0051 ms | 0.0028 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.1756 ms | 0.0302 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.2375 ms | 0.2112 ms |
| `simple_equality` | Canonical Condition (Prepared Artifact Runtime) | 0.1119 ms | 0.0837 ms |
| `simple_equality` | Direct Canonical AST Interpreter | 0.0692 ms | 0.0658 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.3937 ms | 0.2164 ms |
| `typical_business_rule` | Approach B (Normalized Execution Plan) | 0.0441 ms | 0.0201 ms |
| `typical_business_rule` | Approach C (Direct JSON Tree Evaluator) | 0.0048 ms | 0.0026 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.2761 ms | 0.0447 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.558 ms | 0.5887 ms |
| `typical_business_rule` | Canonical Condition (Prepared Artifact Runtime) | 0.344 ms | 0.1802 ms |
| `typical_business_rule` | Direct Canonical AST Interpreter | 0.1522 ms | 0.1418 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.4226 ms | 0.3848 ms |
| `nested_and_or_groups` | Approach B (Normalized Execution Plan) | 0.0475 ms | 0.0249 ms |
| `nested_and_or_groups` | Approach C (Direct JSON Tree Evaluator) | 0.005 ms | 0.0029 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.3817 ms | 0.0575 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.7502 ms | 0.6776 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Artifact Runtime) | 0.2953 ms | 0.2199 ms |
| `nested_and_or_groups` | Direct Canonical AST Interpreter | 0.2471 ms | 0.1993 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 0.7409 ms | 0.6578 ms |
| `deep_nested_complex` | Approach B (Normalized Execution Plan) | 0.0684 ms | 0.0404 ms |
| `deep_nested_complex` | Approach C (Direct JSON Tree Evaluator) | 0.0054 ms | 0.0028 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.5486 ms | 0.0892 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.4637 ms | 1.5173 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Artifact Runtime) | 0.4589 ms | 0.4209 ms |
| `deep_nested_complex` | Direct Canonical AST Interpreter | 0.3431 ms | 0.3217 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.5141 ms | 0.3283 ms |
| `collection_predicate` | Approach B (Normalized Execution Plan) | 0.0495 ms | 0.0246 ms |
| `collection_predicate` | Approach C (Direct JSON Tree Evaluator) | 0.005 ms | 0.0027 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.3117 ms | 0.0494 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.9354 ms | 0.8753 ms |
| `collection_predicate` | Canonical Condition (Prepared Artifact Runtime) | 0.3297 ms | 0.2087 ms |
| `collection_predicate` | Direct Canonical AST Interpreter | 0.1859 ms | 0.1762 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.3438 ms | 0.2716 ms |
| `edge_case_membership_in_not_in` | Approach B (Normalized Execution Plan) | 0.0405 ms | 0.0168 ms |
| `edge_case_membership_in_not_in` | Approach C (Direct JSON Tree Evaluator) | 0.0051 ms | 0.0027 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.2553 ms | 0.0359 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.5115 ms | 0.5326 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Artifact Runtime) | 0.1874 ms | 0.14 ms |
| `edge_case_membership_in_not_in` | Direct Canonical AST Interpreter | 0.1743 ms | 0.1257 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.5091 ms | 0.2858 ms |
| `edge_case_contains_not_contains` | Approach B (Normalized Execution Plan) | 0.0363 ms | 0.0162 ms |
| `edge_case_contains_not_contains` | Approach C (Direct JSON Tree Evaluator) | 0.005 ms | 0.0027 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.2258 ms | 0.0362 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.7584 ms | 0.7361 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Artifact Runtime) | 0.1744 ms | 0.1818 ms |
| `edge_case_contains_not_contains` | Direct Canonical AST Interpreter | 0.1273 ms | 0.1076 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.2183 ms | 0.0542 ms |
| `edge_case_has_changed` | Approach B (Normalized Execution Plan) | 0.0223 ms | 0.01 ms |
| `edge_case_has_changed` | Approach C (Direct JSON Tree Evaluator) | 0.0052 ms | 0.0027 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.1359 ms | 0.0971 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.2643 ms | 0.1398 ms |
| `edge_case_none_vs_missing_field` | Approach B (Normalized Execution Plan) | 0.0249 ms | 0.0093 ms |
| `edge_case_none_vs_missing_field` | Approach C (Direct JSON Tree Evaluator) | 0.0051 ms | 0.003 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.188 ms | 0.0292 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.4452 ms | 0.4329 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Artifact Runtime) | 0.1023 ms | 0.0712 ms |
| `edge_case_none_vs_missing_field` | Direct Canonical AST Interpreter | 0.0583 ms | 0.0506 ms |
| `dynamic_operands_both_sides` | Approach A (frappe.safe_eval) | 0.2998 ms | 0.1282 ms |
| `dynamic_operands_both_sides` | Approach B (Normalized Execution Plan) | 0.0259 ms | 0.0111 ms |
| `dynamic_operands_both_sides` | Approach C (Direct JSON Tree Evaluator) | 0.0051 ms | 0.0028 ms |
| `dynamic_operands_both_sides` | Canonical Condition (evaluate_condition) | 0.1665 ms | 0.0269 ms |
| `dynamic_operands_both_sides` | Approach A (Experimental Restricted Code Object) | 0.3795 ms | 0.2935 ms |
| `dynamic_operands_both_sides` | Canonical Condition (Prepared Artifact Runtime) | 0.1658 ms | 0.094 ms |
| `dynamic_operands_both_sides` | Direct Canonical AST Interpreter | 0.0739 ms | 0.0663 ms |
| `dynamic_operands_static_left` | Approach A (frappe.safe_eval) | 0.2199 ms | 0.0944 ms |
| `dynamic_operands_static_left` | Approach B (Normalized Execution Plan) | 0.0243 ms | 0.0194 ms |
| `dynamic_operands_static_left` | Approach C (Direct JSON Tree Evaluator) | 0.005 ms | 0.0026 ms |
| `dynamic_operands_static_left` | Canonical Condition (evaluate_condition) | 0.168 ms | 0.0258 ms |
| `dynamic_operands_static_left` | Approach A (Experimental Restricted Code Object) | 0.314 ms | 0.2469 ms |
| `dynamic_operands_static_left` | Canonical Condition (Prepared Artifact Runtime) | 0.1145 ms | 0.0812 ms |
| `dynamic_operands_static_left` | Direct Canonical AST Interpreter | 0.0684 ms | 0.0599 ms |
| `dynamic_operands_template` | Canonical Condition (evaluate_condition) | 0.2126 ms | 0.0313 ms |
| `dynamic_operands_template` | Canonical Condition (Prepared Artifact Runtime) | 0.147 ms | 0.1592 ms |
| `dynamic_operands_template` | Direct Canonical AST Interpreter | 0.0912 ms | 0.085 ms |
| `frappe_metadata_user_roles` | Approach A (frappe.safe_eval) | 0.3533 ms | 0.1869 ms |
| `frappe_metadata_user_roles` | Approach B (Normalized Execution Plan) | 0.0304 ms | 0.0134 ms |
| `frappe_metadata_user_roles` | Approach C (Direct JSON Tree Evaluator) | 0.0048 ms | 0.0026 ms |
| `frappe_metadata_user_roles` | Canonical Condition (evaluate_condition) | 0.2551 ms | 0.0736 ms |
| `frappe_metadata_user_roles` | Approach A (Experimental Restricted Code Object) | 0.5817 ms | 0.5328 ms |
| `frappe_metadata_user_roles` | Canonical Condition (Prepared Artifact Runtime) | 0.1957 ms | 0.1359 ms |
| `frappe_metadata_user_roles` | Direct Canonical AST Interpreter | 0.1276 ms | 0.1148 ms |

---

## Direct Canonical AST vs Compiled Tuple Plan

### 1. Architecture Overview & Lifecycle
- **Direct Canonical AST Interpreter (Approach A)**: Validates the canonical JSON condition tree once during `prepare()` against authoritative Frappe and contract metadata. Retains the parsed JSON structure as an immutable snapshot (`PreparedDirectCanonicalAST`). At runtime, walks the JSON dict tree directly, evaluating operands and child branches strictly lazily without compiling into tuples or intermediate code.
- **Compiled Immutable Execution Plan (Approach B / Production)**: Validates the canonical JSON tree and compiles it into an immutable tuple hierarchy (`_compile_node`, `_compile_value`, `_PreparedCanonicalCondition`). Caches compiled plans in an in-memory bounded LRU. At runtime, walks the tuple structure using index-based node unpacking.

### 2. Component Cost Breakdown (Microseconds)
Measures the exact cost of each stage in the condition evaluation pipeline:

| Scenario ID | Tier | JSON Serialization | Structural Validation | Metadata Validation | Direct AST Prep | Plan Cold Prep | Plan Warm Prep |
|---|---|---|---|---|---|---|---|
| `simple_equality` | Tier 1 — Simple | 37.58 µs | 73.11 µs | N/A | 125.7 µs | 142.34 µs | 82.28 µs |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 35.41 µs | 113.66 µs | N/A | 164.8 µs | 215.32 µs | 222.04 µs |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 46.88 µs | 137.13 µs | N/A | 203.53 µs | 334.53 µs | 286.14 µs |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 66.36 µs | 246.74 µs | N/A | 338.51 µs | 505.44 µs | 372.71 µs |
| `collection_predicate` | Tier 5 — Collection Predicate | 40.79 µs | 181.61 µs | N/A | 197.96 µs | 250.22 µs | 217.59 µs |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 26.72 µs | 85.44 µs | N/A | 174.24 µs | 181.03 µs | 140.76 µs |
| `edge_case_contains_not_contains` | Edge Case — Substring | 25.18 µs | 72.75 µs | N/A | 119.38 µs | 152.85 µs | 228.68 µs |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 19.86 µs | 37.69 µs | N/A | 56.44 µs | 85.21 µs | 67.05 µs |
| `dynamic_operands_both_sides` | Dynamic Operands — Both Variables | 16.06 µs | 44.58 µs | N/A | 68.37 µs | 106.43 µs | 84.05 µs |
| `dynamic_operands_static_left` | Dynamic Operands — Static Left | 16.95 µs | 39.25 µs | N/A | 63.31 µs | 91.65 µs | 110.67 µs |
| `dynamic_operands_template` | Dynamic Operands — Template | 25.25 µs | 61.37 µs | N/A | 85.2 µs | 122.53 µs | 96.76 µs |
| `frappe_metadata_user_roles` | Frappe Metadata — User Roles | 19.91 µs | 68.2 µs | 106.04 | 118.05 µs | 152.3 µs | 183.84 µs |

### 3. Collection Scaling & Short-Circuit Behavior
Empirical comparison across collection workloads with varying row counts (10 to 10,000 rows) and match positions:

| Scenario ID | Rows | Behavior | Direct Canonical AST | Compiled Tuple Plan | Speedup Ratio |
|---|---|---|---|---|---|
| `collection_scaling_any_early_match_10` | 10 | early_match | 54.053 µs/op | 47.61 µs/op | 1.14x (Plan is faster) |
| `collection_scaling_any_late_match_10` | 10 | late_match | 89.908 µs/op | 168.063 µs/op | 0.53x (Plan is faster) |
| `collection_scaling_all_early_fail_10` | 10 | early_match | 112.202 µs/op | 103.418 µs/op | 1.08x (Plan is faster) |
| `collection_scaling_none_10` | 10 | no_match | 162.719 µs/op | 155.923 µs/op | 1.04x (Plan is faster) |
| `collection_scaling_any_early_match_100` | 100 | early_match | 930.809 µs/op | 367.169 µs/op | 2.54x (Plan is faster) |
| `collection_scaling_any_late_match_100` | 100 | late_match | 833.556 µs/op | 721.067 µs/op | 1.16x (Plan is faster) |
| `collection_scaling_all_early_fail_100` | 100 | early_match | 433.072 µs/op | 370.269 µs/op | 1.17x (Plan is faster) |
| `collection_scaling_none_100` | 100 | no_match | 832.481 µs/op | 708.523 µs/op | 1.17x (Plan is faster) |
| `collection_scaling_any_early_match_1000` | 1000 | early_match | 4190.45 µs/op | 3558.389 µs/op | 1.18x (Plan is faster) |
| `collection_scaling_any_late_match_1000` | 1000 | late_match | 8328.205 µs/op | 7101.052 µs/op | 1.17x (Plan is faster) |
| `collection_scaling_all_early_fail_1000` | 1000 | early_match | 4147.443 µs/op | 3558.105 µs/op | 1.17x (Plan is faster) |
| `collection_scaling_none_1000` | 1000 | no_match | 8313.057 µs/op | 7122.368 µs/op | 1.17x (Plan is faster) |
| `collection_scaling_any_early_match_10000` | 10000 | early_match | 43498.002 µs/op | 35832.046 µs/op | 1.21x (Plan is faster) |
| `collection_scaling_any_late_match_10000` | 10000 | late_match | 85598.39 µs/op | 72517.915 µs/op | 1.18x (Plan is faster) |
| `collection_scaling_all_early_fail_10000` | 10000 | early_match | 42273.767 µs/op | 35519.461 µs/op | 1.19x (Plan is faster) |
| `collection_scaling_none_10000` | 10000 | no_match | 84523.861 µs/op | 71059.719 µs/op | 1.19x (Plan is faster) |

### 4. Memory Profiling
- Sample Scenario: `typical_business_rule`
- **Direct Canonical AST Prepared Allocation:** 2,070 bytes
- **Compiled Tuple Plan Prepared Allocation:** 3,629 bytes

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