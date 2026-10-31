# FlexiRule — Condition Backend Comparison Benchmark Report

**Date:** 2026-10-31T17:03:00Z
**Branch:** `feat/benchmark-canonical-ast-vs-plan`
**Commit:** `3a9cd50b8d5ff047a0269693d0152d6646b4bcec`
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
| `simple_numeric` | 0 | 266.8 / 92.3 | 92.7 / 77.7 | 11.303 | 11.399 | 11.269 | 11.272 | 1.00x | PASS |
| `dynamic_operands_var_vs_var` | 0 | 249.7 / 145.6 | 151.6 / 78.2 | 12.762 | 12.942 | 12.588 | 12.931 | 0.99x | PASS |
| `complex_nested_tree` | 0 | 480.8 / 231.3 | 289.1 / 218.4 | 27.078 | 27.143 | 40.798 | 41.518 | 1.51x | PASS |
| `collection_any_10_early` | 10 | 288.3 / 118.6 | 110.9 / 98.0 | 14.788 | 14.804 | 14.757 | 14.998 | 1.00x | PASS |
| `collection_any_10_late` | 10 | 271.5 / 113.4 | 106.0 / 95.2 | 83.492 | 84.954 | 96.949 | 102.302 | 1.16x | PASS |
| `collection_any_10_none` | 10 | 334.8 / 180.5 | 118.5 / 98.1 | 73.981 | 88.451 | 87.415 | 144.927 | 1.18x | PASS |
| `collection_any_100_early` | 100 | 344.4 / 134.5 | 109.2 / 96.8 | 14.650 | 15.066 | 14.827 | 14.861 | 1.01x | PASS |
| `collection_any_100_late` | 100 | 331.0 / 131.2 | 187.7 / 107.3 | 671.167 | 675.479 | 770.838 | 789.524 | 1.15x | PASS |
| `collection_any_100_none` | 100 | 338.0 / 128.5 | 106.3 / 96.9 | 668.408 | 671.606 | 772.169 | 777.247 | 1.16x | PASS |
| `collection_any_1000_early` | 1000 | 342.3 / 124.2 | 109.1 / 95.7 | 14.789 | 14.882 | 14.828 | 15.026 | 1.00x | PASS |
| `collection_any_1000_late` | 1000 | 240.7 / 147.5 | 118.4 / 97.5 | 6569.435 | 6572.349 | 7733.568 | 7740.817 | 1.18x | PASS |
| `collection_any_1000_none` | 1000 | 343.9 / 130.6 | 108.3 / 97.7 | 6601.606 | 6604.098 | 7700.163 | 7741.559 | 1.17x | PASS |
| `collection_any_10000_early` | 10000 | 298.1 / 115.8 | 161.3 / 108.8 | 14.874 | 17.247 | 14.920 | 15.370 | 1.00x | PASS |
| `collection_any_10000_late` | 10000 | 222.4 / 112.2 | 104.0 / 95.6 | 66339.734 | 66493.471 | 77733.255 | 78257.388 | 1.17x | PASS |
| `collection_any_10000_none` | 10000 | 313.0 / 225.3 | 124.5 / 117.7 | 65853.980 | 66754.809 | 76891.899 | 77047.380 | 1.17x | PASS |
| `collection_all_100_early_break` | 100 | 336.1 / 117.8 | 107.3 / 104.6 | 14.901 | 14.943 | 14.913 | 14.914 | 1.00x | PASS |

### 5. Amortized Cost (Preparation + N Evaluations)

| Execution Count | Compiled Plan (Cold μs) | AST Interpreter (Cold μs) | Compiled Plan (Warm μs) | AST Interpreter (Warm μs) | Faster (Cold) | Faster (Warm) |
|---|---|---|---|---|---|---|
| **N=1** | 507.87 | 329.95 | 258.43 | 259.24 | AST | Compiled Plan |
| **N=10** | 75.16 | 69.71 | 50.21 | 62.64 | AST | Compiled Plan |
| **N=100** | 31.89 | 43.69 | 29.39 | 42.98 | Compiled Plan | Compiled Plan |
| **N=1000** | 27.56 | 41.09 | 27.31 | 41.02 | Compiled Plan | Compiled Plan |

### 6. Realistic Frappe Metadata Verification
- **Metadata Scenario:** `User -> Has Role (parent field roles, child field role)`
- **Compiled Plan Preparation:** `1077.14 μs` | **Evaluation Median:** `1.056 μs`
- **Direct AST Preparation:** `617.99 μs` | **Evaluation Median:** `1.074 μs`

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
| `simple_equality` | Tier 1 — Simple | 175.61 µs/op | 3.589 µs/op | 5.247 µs/op | 28.678 µs/op | 11.423 µs/op | 12.05 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 430.508 µs/op | 6.826 µs/op | 11.034 µs/op | 60.153 µs/op | 13.791 µs/op | 24.078 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 557.326 µs/op | 6.541 µs/op | 11.296 µs/op | 66.4 µs/op | 12.587 µs/op | 21.767 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1153.665 µs/op | 10.119 µs/op | 17.31 µs/op | 114.152 µs/op | 16.716 µs/op | 40.379 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 733.458 µs/op | 10.626 µs/op | 16.809 µs/op | 80.276 µs/op | 17.596 µs/op | 36.098 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 391.76 µs/op | 4.934 µs/op | 7.734 µs/op | 50.066 µs/op | 11.126 µs/op | 20.998 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 595.512 µs/op | 5.726 µs/op | 9.266 µs/op | 39.907 µs/op | 15.036 µs/op | 13.459 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 59.774 µs/op | 3.854 µs/op | 5.816 µs/op | UNSUPPORTED | 9.089 µs/op | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 312.996 µs/op | 2.875 µs/op | 4.108 µs/op | 21.656 µs/op | 11.238 µs/op | 8.005 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.1682 ms | 0.0906 ms |
| `simple_equality` | Approach B (Normalized Execution Plan) | 0.0277 ms | 0.0106 ms |
| `simple_equality` | Approach C (Direct JSON Tree Evaluator) | 0.0037 ms | 0.0024 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.1131 ms | 0.024 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.2157 ms | 0.2792 ms |
| `simple_equality` | Canonical Condition (Prepared Artifact Runtime) | 0.1491 ms | 0.0878 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.4395 ms | 0.2153 ms |
| `typical_business_rule` | Approach B (Normalized Execution Plan) | 0.0415 ms | 0.0202 ms |
| `typical_business_rule` | Approach C (Direct JSON Tree Evaluator) | 0.0052 ms | 0.0025 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.2938 ms | 0.0987 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.5885 ms | 0.526 ms |
| `typical_business_rule` | Canonical Condition (Prepared Artifact Runtime) | 0.2458 ms | 0.1791 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.5204 ms | 0.3394 ms |
| `nested_and_or_groups` | Approach B (Normalized Execution Plan) | 0.0484 ms | 0.0244 ms |
| `nested_and_or_groups` | Approach C (Direct JSON Tree Evaluator) | 0.0049 ms | 0.0027 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.3973 ms | 0.0584 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.7037 ms | 0.723 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Artifact Runtime) | 0.2832 ms | 0.2395 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 0.8035 ms | 0.5861 ms |
| `deep_nested_complex` | Approach B (Normalized Execution Plan) | 0.0747 ms | 0.0454 ms |
| `deep_nested_complex` | Approach C (Direct JSON Tree Evaluator) | 0.0055 ms | 0.0025 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.5378 ms | 0.0816 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.5375 ms | 1.388 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Artifact Runtime) | 0.5072 ms | 0.42 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.5489 ms | 0.3174 ms |
| `collection_predicate` | Approach B (Normalized Execution Plan) | 0.0571 ms | 0.0254 ms |
| `collection_predicate` | Approach C (Direct JSON Tree Evaluator) | 0.0048 ms | 0.0024 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.3338 ms | 0.0493 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.9704 ms | 0.914 ms |
| `collection_predicate` | Canonical Condition (Prepared Artifact Runtime) | 0.3239 ms | 0.2091 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.4199 ms | 0.2798 ms |
| `edge_case_membership_in_not_in` | Approach B (Normalized Execution Plan) | 0.0366 ms | 0.0162 ms |
| `edge_case_membership_in_not_in` | Approach C (Direct JSON Tree Evaluator) | 0.0058 ms | 0.0024 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.3075 ms | 0.0419 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.6038 ms | 0.4734 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Artifact Runtime) | 0.2071 ms | 0.144 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.5296 ms | 0.3423 ms |
| `edge_case_contains_not_contains` | Approach B (Normalized Execution Plan) | 0.0385 ms | 0.0155 ms |
| `edge_case_contains_not_contains` | Approach C (Direct JSON Tree Evaluator) | 0.0053 ms | 0.0027 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.2774 ms | 0.0387 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.7244 ms | 0.8175 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Artifact Runtime) | 0.1868 ms | 0.1298 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.2094 ms | 0.0595 ms |
| `edge_case_has_changed` | Approach B (Normalized Execution Plan) | 0.0235 ms | 0.0097 ms |
| `edge_case_has_changed` | Approach C (Direct JSON Tree Evaluator) | 0.0052 ms | 0.0028 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.1318 ms | 0.0884 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.3111 ms | 0.1483 ms |
| `edge_case_none_vs_missing_field` | Approach B (Normalized Execution Plan) | 0.0919 ms | 0.0163 ms |
| `edge_case_none_vs_missing_field` | Approach C (Direct JSON Tree Evaluator) | 0.0058 ms | 0.0031 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.1658 ms | 0.0666 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.4809 ms | 0.3814 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Artifact Runtime) | 0.1186 ms | 0.0741 ms |

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