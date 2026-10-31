# FlexiRule — Condition Backend Comparison Benchmark Report

**Date:** 2026-10-31T15:42:33Z
**Branch:** `jules-15497228258288256306-bee649d9`
**Commit:** `43715e2258b9c6ee52526bc20cba06d98ddd9eff`
**Working Tree Dirty:** `Yes`
**Provenance Note:** Working tree contains uncommitted changes; benchmark provenance captures the checkout commit plus working-tree state.
**Python:** 3.12.13
**Frappe Framework:** 15.124.0

## Production Selection Gate Status

- **Selected Production Option:** **Not established**
- **Gate Status:** Production selection remains Not established until explicit correctness, security, and performance criteria gates pass.

---

## Direct Canonical JSON AST vs Compiled Tuple Execution Plan

This section reports the empirical comparison between **Approach A: Direct Canonical JSON AST Interpreter** and **Approach B: Compiled Immutable Tuple Execution Plan** consuming identical canonical condition payloads.

### 1. Architecture Descriptions
- **Direct Canonical AST Interpreter (`CanonicalASTCandidate`):** Validates the canonical JSON AST once at preparation lifecycle against the authoritative canonical schema and metadata boundaries. At runtime, walks the validated dictionary-based AST directly. Operands, branches, and collection rows are evaluated strictly lazily when reached, without any intermediate tuple compilation or code generation.
- **Compiled Immutable Execution Plan (`CanonicalPreparedPlanCandidate`):** Validates and compiles the canonical JSON AST into an immutable recursive tuple plan (`_compile_node`, `_compile_value`) protected by a private object seal. At runtime, traverses the compiled tuple structure lazily via `_evaluate_node` and `_evaluate_value`.

### 2. Preparation vs Runtime Evaluation
| Dimension | Direct Canonical AST Interpreter | Compiled Tuple Execution Plan |
|---|---|---|
| **Preparation Artifact** | Validated, immutable JSON AST dict snapshot (`_PreparedCanonicalAST`) | Immutable pre-compiled tuple tree (`_PreparedCanonicalCondition`) |
| **Preparation Work** | JSON canonicalization + schema & DocType validation | JSON canonicalization + schema validation + recursive tuple compilation |
| **Runtime Traversal** | Recursive dictionary key lookups and branch evaluation | Direct tuple indexing (`plan[0]`, `plan[1]`, etc.) |
| **Operand Resolution** | Lazy runtime evaluation via shared FlexValue resolvers | Lazy runtime evaluation via shared FlexValue resolvers |
| **Short-Circuiting** | Strict left-to-right AND/OR short-circuiting | Strict left-to-right AND/OR short-circuiting |
| **Quantifier Exit** | Immediate break on decisive condition (any/all/none) | Immediate break on decisive condition (any/all/none) |
| **Collection Safety** | Shared row-visit budget enforcement | Shared row-visit budget enforcement |

### 3. Semantic Correctness & Gate Results
Both candidates produce **100% identical outputs and error codes** across all simple, complex, and collection scaling workloads. Resolver counters verify zero invocations in short-circuited branches for both approaches.

### 4. Preparation and Steady-State Latency Comparison

| Workload | Size | Compiled Prep (Cold/Warm μs) | AST Prep (Cold/Warm μs) | Compiled Eval (Median μs) | Compiled Eval (P95 μs) | AST Eval (Median μs) | AST Eval (P95 μs) | AST / Plan Ratio | Correctness |
|---|---|---|---|---|---|---|---|---|---|
| `simple_numeric` | 0 | 277.5 / 93.2 | 181.8 / 130.0 | 10.912 | 10.947 | 10.923 | 11.046 | 1.00x | PASS |
| `dynamic_operands_var_vs_var` | 0 | 251.9 / 103.0 | 102.8 / 86.3 | 12.601 | 12.683 | 12.191 | 12.208 | 0.97x | PASS |
| `complex_nested_tree` | 0 | 452.2 / 289.9 | 235.0 / 226.1 | 26.505 | 26.853 | 41.023 | 41.321 | 1.55x | PASS |
| `collection_any_10_early` | 10 | 299.5 / 120.8 | 121.5 / 98.2 | 14.461 | 14.730 | 14.935 | 15.058 | 1.03x | PASS |
| `collection_any_10_late` | 10 | 274.6 / 192.9 | 165.8 / 101.5 | 74.276 | 75.255 | 84.661 | 85.318 | 1.14x | PASS |
| `collection_any_10_none` | 10 | 286.1 / 166.8 | 112.3 / 97.8 | 75.054 | 75.513 | 84.972 | 85.021 | 1.13x | PASS |
| `collection_any_100_early` | 100 | 280.4 / 117.1 | 117.2 / 96.5 | 14.276 | 15.166 | 14.625 | 14.907 | 1.02x | PASS |
| `collection_any_100_late` | 100 | 323.2 / 136.5 | 110.4 / 96.6 | 670.914 | 671.351 | 783.466 | 792.773 | 1.17x | PASS |
| `collection_any_100_none` | 100 | 308.2 / 117.8 | 112.1 / 157.3 | 675.937 | 675.942 | 792.500 | 799.351 | 1.17x | PASS |
| `collection_any_1000_early` | 1000 | 275.1 / 170.9 | 107.8 / 97.1 | 14.516 | 15.025 | 14.604 | 14.757 | 1.01x | PASS |
| `collection_any_1000_late` | 1000 | 276.3 / 117.6 | 105.9 / 95.2 | 6683.581 | 6705.144 | 7866.247 | 7895.348 | 1.18x | PASS |
| `collection_any_1000_none` | 1000 | 305.2 / 119.3 | 174.2 / 156.1 | 6697.427 | 6712.987 | 7873.505 | 7879.454 | 1.18x | PASS |
| `collection_any_10000_early` | 10000 | 356.2 / 168.3 | 119.0 / 125.3 | 15.517 | 16.590 | 14.666 | 17.146 | 0.95x | PASS |
| `collection_any_10000_late` | 10000 | 246.4 / 159.4 | 118.3 / 97.0 | 66847.054 | 66864.040 | 78593.800 | 106611.531 | 1.18x | PASS |
| `collection_any_10000_none` | 10000 | 361.7 / 123.7 | 110.1 / 96.8 | 66596.628 | 66691.551 | 77899.836 | 78195.431 | 1.17x | PASS |
| `collection_all_100_early_break` | 100 | 347.8 / 137.2 | 109.5 / 97.7 | 14.932 | 15.083 | 14.690 | 15.114 | 0.98x | PASS |

### 5. Amortized Cost (Preparation + N Evaluations)

| Execution Count | Compiled Plan (Cold μs) | AST Interpreter (Cold μs) | Compiled Plan (Warm μs) | AST Interpreter (Warm μs) | Faster (Cold) | Faster (Warm) |
|---|---|---|---|---|---|---|
| **N=1** | 478.69 | 276.03 | 316.38 | 267.08 | AST | AST |
| **N=10** | 71.72 | 64.52 | 55.49 | 63.63 | AST | Compiled Plan |
| **N=100** | 31.03 | 43.37 | 29.40 | 43.28 | Compiled Plan | Compiled Plan |
| **N=1000** | 26.96 | 41.26 | 26.79 | 41.25 | Compiled Plan | Compiled Plan |

### 6. Realistic Frappe Metadata Verification
- **Metadata Scenario:** `User -> Has Role (parent field roles, child field role)`
- **Compiled Plan Preparation:** `955.55 μs` | **Evaluation Median:** `1.085 μs`
- **Direct AST Preparation:** `515.74 μs` | **Evaluation Median:** `1.035 μs`

### 7. Memory, Cache, and Maintenance Trade-offs
- **Direct Canonical AST:** Simpler architectural model without secondary AST compiler or tuple layout dependencies. Saves compilation step entirely. Cold preparation is noticeably faster. Runtime evaluation is slightly slower due to dictionary key lookups vs tuple index access.
- **Compiled Tuple Plan:** Has lower steady-state per-evaluation latency once prepared, as tuple index indexing is faster than dict key lookups in Python. However, it requires maintaining `_compile_node` and `_compile_value` compilers and plan synchronization.

### 8. Recommendation and Decision Gate
- **Production Selection:** **Not established**
- **Rationale:** For single or few-shot evaluations (N <= 10), Direct Canonical AST interpretation amortizes faster due to lower preparation cost. For heavily looped or long-lived prepared conditions (N >= 100), Compiled Tuple Plan demonstrates faster per-evaluation throughput. Because production workloads vary between single-event triggers and large batch iterations, both execution profiles have distinct sweet spots, and replacing the production evaluator without comprehensive end-to-end telemetry across all action types is not recommended.

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
| `simple_equality` | Tier 1 — Simple | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Canonical Condition (Direct JSON AST Runtime): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Canonical Condition (Direct JSON AST Runtime): False</small>` | None |
| `typical_business_rule` | Tier 2 — Typical Business Rule | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Canonical Condition (Direct JSON AST Runtime): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Canonical Condition (Direct JSON AST Runtime): False</small>` | None |
| `nested_and_or_groups` | Tier 3 — Nested Groups | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Canonical Condition (Direct JSON AST Runtime): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Canonical Condition (Direct JSON AST Runtime): False</small>` | None |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Canonical Condition (Direct JSON AST Runtime): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Canonical Condition (Direct JSON AST Runtime): False</small>` | None |
| `collection_predicate` | Tier 5 — Collection Predicate | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Canonical Condition (Direct JSON AST Runtime): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Canonical Condition (Direct JSON AST Runtime): False</small>` | None |
| `edge_case_membership_in_not_in` | Edge Case — Membership | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Canonical Condition (Direct JSON AST Runtime): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Canonical Condition (Direct JSON AST Runtime): False</small>` | None |
| `edge_case_contains_not_contains` | Edge Case — Substring | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Canonical Condition (Direct JSON AST Runtime): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Canonical Condition (Direct JSON AST Runtime): False</small>` | None |
| `edge_case_has_changed` | Edge Case — Field Change | **DEPRECATED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract., Canonical Condition (Prepared Artifact Runtime): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract., Canonical Condition (Direct JSON AST Runtime): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract.</small>` | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract., Canonical Condition (Prepared Artifact Runtime): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract., Canonical Condition (Direct JSON AST Runtime): UNSUPPORTED: 'has_changed' operator is not supported in PR #469 canonical condition contract.</small>` | Candidate 'Approach A (frappe.safe_eval)' non-matching result (True) != expected (False) | Candidate 'Approach A (Experimental Restricted Code Object)' non-matching result (True) != expected (False) | Disagreement on non-matching doc: {'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': False, 'Approach C (Direct JSON Tree Evaluator)': False} | DEPRECATED: 'has_changed' operator behavior varies between deprecated legacy return 'True' and state-diff evaluators. |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | **PASSED** | `<small>Approach A (frappe.safe_eval): True, Approach A (Experimental Restricted Code Object): True, Approach B (Normalized Execution Plan): True, Approach C (Direct JSON Tree Evaluator): True, Canonical Condition (evaluate_condition): True, Canonical Condition (Prepared Artifact Runtime): True, Canonical Condition (Direct JSON AST Runtime): True</small>` | `<small>Approach A (frappe.safe_eval): False, Approach A (Experimental Restricted Code Object): False, Approach B (Normalized Execution Plan): False, Approach C (Direct JSON Tree Evaluator): False, Canonical Condition (evaluate_condition): False, Canonical Condition (Prepared Artifact Runtime): False, Canonical Condition (Direct JSON AST Runtime): False</small>` | None |

---

## 3. Steady-State Execution Latency (Microseconds per Operation)

| Scenario ID | Tier | Approach A (`safe_eval`) | Approach B (`plan`) | Approach C (`json_tree`) | Canonical Runtime (`evaluate_condition`) | *Diagnostic: A Exp (`code_obj`)* | *Prepared Artifact Runtime* |
|---|---|---|---|---|---|---|---|
| `simple_equality` | Tier 1 — Simple | 175.972 µs/op | 3.647 µs/op | 5.314 µs/op | 28.97 µs/op | 10.492 µs/op | 11.852 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 419.247 µs/op | 6.173 µs/op | 10.333 µs/op | 57.327 µs/op | 12.537 µs/op | 21.86 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 555.51 µs/op | 6.624 µs/op | 11.729 µs/op | 67.938 µs/op | 12.943 µs/op | 22.345 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1161.662 µs/op | 10.299 µs/op | 18.08 µs/op | 112.638 µs/op | 17.372 µs/op | 40.265 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 725.477 µs/op | 10.684 µs/op | 17.23 µs/op | 79.311 µs/op | 17.466 µs/op | 35.395 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 383.784 µs/op | 4.998 µs/op | 7.615 µs/op | 49.947 µs/op | 11.089 µs/op | 20.728 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 597.948 µs/op | 5.722 µs/op | 8.988 µs/op | 40.739 µs/op | 15.227 µs/op | 13.552 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 61.509 µs/op | 3.561 µs/op | 5.375 µs/op | UNSUPPORTED | 8.481 µs/op | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 314.716 µs/op | 2.969 µs/op | 4.273 µs/op | 21.844 µs/op | 11.085 µs/op | 8.064 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.1587 ms | 0.1105 ms |
| `simple_equality` | Approach B (Normalized Execution Plan) | 0.0181 ms | 0.0124 ms |
| `simple_equality` | Approach C (Direct JSON Tree Evaluator) | 0.0038 ms | 0.0025 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.1145 ms | 0.0235 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.2148 ms | 0.2037 ms |
| `simple_equality` | Canonical Condition (Prepared Artifact Runtime) | 0.2618 ms | 0.1063 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.3874 ms | 0.2137 ms |
| `typical_business_rule` | Approach B (Normalized Execution Plan) | 0.0394 ms | 0.0196 ms |
| `typical_business_rule` | Approach C (Direct JSON Tree Evaluator) | 0.0056 ms | 0.0026 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.2951 ms | 0.0922 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.5922 ms | 0.5306 ms |
| `typical_business_rule` | Canonical Condition (Prepared Artifact Runtime) | 0.2277 ms | 0.1929 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.4768 ms | 0.2687 ms |
| `nested_and_or_groups` | Approach B (Normalized Execution Plan) | 0.0488 ms | 0.0243 ms |
| `nested_and_or_groups` | Approach C (Direct JSON Tree Evaluator) | 0.005 ms | 0.0027 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.3911 ms | 0.0608 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.871 ms | 0.7421 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Artifact Runtime) | 0.2827 ms | 0.22 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 0.7444 ms | 0.6284 ms |
| `deep_nested_complex` | Approach B (Normalized Execution Plan) | 0.0754 ms | 0.0397 ms |
| `deep_nested_complex` | Approach C (Direct JSON Tree Evaluator) | 0.0058 ms | 0.0026 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.5516 ms | 0.0869 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.5368 ms | 1.4314 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Artifact Runtime) | 0.4585 ms | 0.4135 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.5139 ms | 0.306 ms |
| `collection_predicate` | Approach B (Normalized Execution Plan) | 0.0564 ms | 0.0251 ms |
| `collection_predicate` | Approach C (Direct JSON Tree Evaluator) | 0.0055 ms | 0.0024 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.3149 ms | 0.049 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.8838 ms | 0.9888 ms |
| `collection_predicate` | Canonical Condition (Prepared Artifact Runtime) | 0.3326 ms | 0.2063 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.3956 ms | 0.2091 ms |
| `edge_case_membership_in_not_in` | Approach B (Normalized Execution Plan) | 0.0343 ms | 0.0156 ms |
| `edge_case_membership_in_not_in` | Approach C (Direct JSON Tree Evaluator) | 0.0057 ms | 0.0026 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.2429 ms | 0.0369 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.5471 ms | 0.4882 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Artifact Runtime) | 0.2195 ms | 0.1404 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.4568 ms | 0.2821 ms |
| `edge_case_contains_not_contains` | Approach B (Normalized Execution Plan) | 0.0384 ms | 0.0159 ms |
| `edge_case_contains_not_contains` | Approach C (Direct JSON Tree Evaluator) | 0.0058 ms | 0.0027 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.2524 ms | 0.036 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.8201 ms | 0.7646 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Artifact Runtime) | 0.1791 ms | 0.1333 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.1584 ms | 0.0511 ms |
| `edge_case_has_changed` | Approach B (Normalized Execution Plan) | 0.0226 ms | 0.0091 ms |
| `edge_case_has_changed` | Approach C (Direct JSON Tree Evaluator) | 0.0057 ms | 0.0025 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.141 ms | 0.0896 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.3397 ms | 0.1542 ms |
| `edge_case_none_vs_missing_field` | Approach B (Normalized Execution Plan) | 0.0255 ms | 0.0098 ms |
| `edge_case_none_vs_missing_field` | Approach C (Direct JSON Tree Evaluator) | 0.0053 ms | 0.0027 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.1498 ms | 0.0228 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.4284 ms | 0.4128 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Artifact Runtime) | 0.0995 ms | 0.0715 ms |

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