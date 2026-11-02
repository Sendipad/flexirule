# FlexiRule — Condition Backend Comparison Benchmark Report

**Date:** 2026-11-02T18:16:40Z
**Branch:** `jules-841098406004505918-e91cef3b`
**Commit:** `8f1b1884a235940d2ef5da625490a9668c27e896`
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
| `simple_numeric` | 0 | 226.2 / 91.9 | 106.7 / 77.6 | 10.578 | 10.587 | 10.464 | 10.590 | 0.99x | PASS |
| `dynamic_operands_var_vs_var` | 0 | 257.8 / 96.1 | 85.8 / 129.3 | 12.114 | 12.219 | 11.626 | 11.774 | 0.96x | PASS |
| `complex_nested_tree` | 0 | 550.4 / 236.9 | 235.2 / 206.8 | 26.971 | 27.112 | 41.239 | 41.328 | 1.53x | PASS |
| `collection_any_10_early` | 10 | 271.1 / 120.4 | 111.7 / 98.5 | 14.206 | 14.212 | 14.537 | 14.542 | 1.02x | PASS |
| `collection_any_10_late` | 10 | 282.9 / 163.0 | 120.0 / 97.9 | 73.600 | 73.776 | 82.168 | 83.277 | 1.12x | PASS |
| `collection_any_10_none` | 10 | 262.6 / 169.5 | 110.0 / 97.5 | 73.737 | 73.993 | 81.889 | 83.040 | 1.11x | PASS |
| `collection_any_100_early` | 100 | 288.8 / 118.9 | 108.0 / 97.5 | 13.974 | 14.152 | 14.311 | 14.448 | 1.02x | PASS |
| `collection_any_100_late` | 100 | 242.1 / 167.2 | 107.3 / 97.4 | 670.930 | 672.343 | 769.780 | 774.716 | 1.15x | PASS |
| `collection_any_100_none` | 100 | 283.7 / 119.5 | 148.2 / 110.3 | 670.516 | 672.384 | 766.083 | 766.651 | 1.14x | PASS |
| `collection_any_1000_early` | 1000 | 279.7 / 117.0 | 108.4 / 107.5 | 13.763 | 15.873 | 15.236 | 15.468 | 1.11x | PASS |
| `collection_any_1000_late` | 1000 | 220.8 / 114.9 | 105.3 / 96.4 | 6722.030 | 6741.520 | 7657.695 | 7688.620 | 1.14x | PASS |
| `collection_any_1000_none` | 1000 | 351.5 / 135.8 | 109.2 / 99.2 | 6720.876 | 6725.849 | 7704.026 | 7719.188 | 1.15x | PASS |
| `collection_any_10000_early` | 10000 | 264.1 / 118.2 | 176.9 / 105.9 | 13.699 | 14.169 | 13.813 | 13.993 | 1.01x | PASS |
| `collection_any_10000_late` | 10000 | 159.1 / 120.8 | 102.8 / 141.1 | 67710.385 | 67713.367 | 77376.102 | 77379.236 | 1.14x | PASS |
| `collection_any_10000_none` | 10000 | 290.1 / 117.5 | 109.4 / 153.1 | 67629.386 | 67648.205 | 77226.003 | 77235.586 | 1.14x | PASS |
| `collection_all_100_early_break` | 100 | 282.1 / 139.6 | 123.0 / 98.2 | 14.688 | 15.455 | 14.385 | 15.066 | 0.98x | PASS |
| `dynamic_operands_static_left` | 0 | 226.4 / 90.1 | 119.3 / 91.2 | 10.345 | 10.391 | 9.982 | 10.128 | 0.96x | PASS |
| `template_operand` | 0 | 270.1 / 115.8 | 150.0 / 104.5 | 11.775 | 11.801 | 13.265 | 13.339 | 1.13x | PASS |

### 5. Amortized Cost (Preparation + N Evaluations)

| Execution Count | Compiled Plan (Cold μs) | AST Interpreter (Cold μs) | Compiled Plan (Warm μs) | AST Interpreter (Warm μs) | Faster (Cold) | Faster (Warm) |
|---|---|---|---|---|---|---|
| **N=1** | 577.33 | 276.48 | 263.86 | 247.99 | AST | AST |
| **N=10** | 82.01 | 64.76 | 50.66 | 61.91 | AST | Compiled Plan |
| **N=100** | 32.47 | 43.59 | 29.34 | 43.31 | Compiled Plan | Compiled Plan |
| **N=1000** | 27.52 | 41.47 | 27.21 | 41.45 | Compiled Plan | Compiled Plan |

### 6. Realistic Frappe Metadata Verification
- **Metadata Scenario:** `User -> Has Role (parent field roles, child field role)`
- **Compiled Plan Preparation:** `785.49 μs` | **Evaluation Median:** `1.058 μs`
- **Direct AST Preparation:** `638.89 μs` | **Evaluation Median:** `1.115 μs`

### 7. Memory, Cache, and Maintenance Trade-offs
- **Direct Canonical AST:** Simpler architectural model without secondary AST compiler or tuple layout dependencies. Saves compilation step entirely. Cold preparation is noticeably faster. Runtime evaluation is slightly slower due to dictionary key lookups vs tuple index access.
- **Compiled Tuple Plan:** Has lower steady-state per-evaluation latency once prepared, as tuple index indexing is faster than dict key lookups in Python. However, it requires maintaining `_compile_node` and `_compile_value` compilers and plan synchronization.

- **Memory sample:** `complex_nested_tree`
- **Compiled Plan retained / peak allocation:** `4009 / 10303 bytes`
- **Direct AST retained / peak allocation:** `3000 / 8977 bytes`
- **Interpretation:** Single-run tracemalloc diagnostic; allocation figures are approximate and not production memory guarantees.

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
| `simple_equality` | Tier 1 — Simple | 176.968 µs/op | 3.594 µs/op | 5.171 µs/op | 28.959 µs/op | 10.057 µs/op | 11.617 µs/op |
| `typical_business_rule` | Tier 2 — Typical Business Rule | 420.207 µs/op | 6.248 µs/op | 10.418 µs/op | 57.139 µs/op | 12.664 µs/op | 21.293 µs/op |
| `nested_and_or_groups` | Tier 3 — Nested Groups | 573.495 µs/op | 6.63 µs/op | 11.408 µs/op | 67.487 µs/op | 12.792 µs/op | 21.733 µs/op |
| `deep_nested_complex` | Tier 4 — Deep Nested Complex | 1156.315 µs/op | 10.093 µs/op | 17.658 µs/op | 115.336 µs/op | 16.6 µs/op | 39.412 µs/op |
| `collection_predicate` | Tier 5 — Collection Predicate | 727.929 µs/op | 10.678 µs/op | 16.902 µs/op | 79.622 µs/op | 17.301 µs/op | 35.655 µs/op |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 384.53 µs/op | 5.146 µs/op | 7.723 µs/op | 50.852 µs/op | 11.308 µs/op | 20.378 µs/op |
| `edge_case_contains_not_contains` | Edge Case — Substring | 604.46 µs/op | 5.844 µs/op | 9.122 µs/op | 40.888 µs/op | 15.17 µs/op | 13.493 µs/op |
| `edge_case_has_changed` | Edge Case — Field Change | 62.048 µs/op | 3.495 µs/op | 5.393 µs/op | UNSUPPORTED | 8.276 µs/op | UNSUPPORTED |
| `edge_case_none_vs_missing_field` | Edge Case — Missing Field | 323.745 µs/op | 2.889 µs/op | 4.168 µs/op | 21.987 µs/op | 11.035 µs/op | 7.949 µs/op |

---

## 4. Cold vs Warm Preparation Latency (Milliseconds)

| Scenario ID | Candidate | Cold Preparation (ms) | Warm Preparation (ms) |
|---|---|---|---|
| `simple_equality` | Approach A (frappe.safe_eval) | 0.1258 ms | 0.0874 ms |
| `simple_equality` | Approach B (Normalized Execution Plan) | 0.0176 ms | 0.0102 ms |
| `simple_equality` | Approach C (Direct JSON Tree Evaluator) | 0.0036 ms | 0.0024 ms |
| `simple_equality` | Canonical Condition (evaluate_condition) | 0.1815 ms | 0.0297 ms |
| `simple_equality` | Approach A (Experimental Restricted Code Object) | 0.2165 ms | 0.2178 ms |
| `simple_equality` | Canonical Condition (Prepared Artifact Runtime) | 0.11 ms | 0.0836 ms |
| `typical_business_rule` | Approach A (frappe.safe_eval) | 0.4307 ms | 0.2275 ms |
| `typical_business_rule` | Approach B (Normalized Execution Plan) | 0.0418 ms | 0.02 ms |
| `typical_business_rule` | Approach C (Direct JSON Tree Evaluator) | 0.005 ms | 0.0024 ms |
| `typical_business_rule` | Canonical Condition (evaluate_condition) | 0.2734 ms | 0.0442 ms |
| `typical_business_rule` | Approach A (Experimental Restricted Code Object) | 0.5417 ms | 0.5907 ms |
| `typical_business_rule` | Canonical Condition (Prepared Artifact Runtime) | 0.2931 ms | 0.1716 ms |
| `nested_and_or_groups` | Approach A (frappe.safe_eval) | 0.4671 ms | 0.2712 ms |
| `nested_and_or_groups` | Approach B (Normalized Execution Plan) | 0.0868 ms | 0.0278 ms |
| `nested_and_or_groups` | Approach C (Direct JSON Tree Evaluator) | 0.005 ms | 0.0024 ms |
| `nested_and_or_groups` | Canonical Condition (evaluate_condition) | 0.3311 ms | 0.1374 ms |
| `nested_and_or_groups` | Approach A (Experimental Restricted Code Object) | 0.7357 ms | 0.661 ms |
| `nested_and_or_groups` | Canonical Condition (Prepared Artifact Runtime) | 0.3147 ms | 0.2742 ms |
| `deep_nested_complex` | Approach A (frappe.safe_eval) | 0.7899 ms | 0.6619 ms |
| `deep_nested_complex` | Approach B (Normalized Execution Plan) | 0.0674 ms | 0.0407 ms |
| `deep_nested_complex` | Approach C (Direct JSON Tree Evaluator) | 0.0054 ms | 0.0026 ms |
| `deep_nested_complex` | Canonical Condition (evaluate_condition) | 0.5874 ms | 0.0986 ms |
| `deep_nested_complex` | Approach A (Experimental Restricted Code Object) | 1.4404 ms | 1.5864 ms |
| `deep_nested_complex` | Canonical Condition (Prepared Artifact Runtime) | 0.4585 ms | 0.4599 ms |
| `collection_predicate` | Approach A (frappe.safe_eval) | 0.4673 ms | 0.3072 ms |
| `collection_predicate` | Approach B (Normalized Execution Plan) | 0.0572 ms | 0.0255 ms |
| `collection_predicate` | Approach C (Direct JSON Tree Evaluator) | 0.0052 ms | 0.003 ms |
| `collection_predicate` | Canonical Condition (evaluate_condition) | 0.3981 ms | 0.0591 ms |
| `collection_predicate` | Approach A (Experimental Restricted Code Object) | 0.9116 ms | 0.9898 ms |
| `collection_predicate` | Canonical Condition (Prepared Artifact Runtime) | 0.2764 ms | 0.2138 ms |
| `edge_case_membership_in_not_in` | Approach A (frappe.safe_eval) | 0.3533 ms | 0.2574 ms |
| `edge_case_membership_in_not_in` | Approach B (Normalized Execution Plan) | 0.039 ms | 0.0167 ms |
| `edge_case_membership_in_not_in` | Approach C (Direct JSON Tree Evaluator) | 0.0049 ms | 0.0026 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (evaluate_condition) | 0.2432 ms | 0.0377 ms |
| `edge_case_membership_in_not_in` | Approach A (Experimental Restricted Code Object) | 0.512 ms | 0.5148 ms |
| `edge_case_membership_in_not_in` | Canonical Condition (Prepared Artifact Runtime) | 0.1982 ms | 0.1448 ms |
| `edge_case_contains_not_contains` | Approach A (frappe.safe_eval) | 0.3971 ms | 0.3182 ms |
| `edge_case_contains_not_contains` | Approach B (Normalized Execution Plan) | 0.0349 ms | 0.0151 ms |
| `edge_case_contains_not_contains` | Approach C (Direct JSON Tree Evaluator) | 0.0051 ms | 0.0029 ms |
| `edge_case_contains_not_contains` | Canonical Condition (evaluate_condition) | 0.2351 ms | 0.0369 ms |
| `edge_case_contains_not_contains` | Approach A (Experimental Restricted Code Object) | 0.7142 ms | 0.7344 ms |
| `edge_case_contains_not_contains` | Canonical Condition (Prepared Artifact Runtime) | 0.2173 ms | 0.1426 ms |
| `edge_case_has_changed` | Approach A (frappe.safe_eval) | 0.2204 ms | 0.0597 ms |
| `edge_case_has_changed` | Approach B (Normalized Execution Plan) | 0.023 ms | 0.0138 ms |
| `edge_case_has_changed` | Approach C (Direct JSON Tree Evaluator) | 0.0049 ms | 0.0028 ms |
| `edge_case_has_changed` | Approach A (Experimental Restricted Code Object) | 0.1302 ms | 0.09 ms |
| `edge_case_none_vs_missing_field` | Approach A (frappe.safe_eval) | 0.2628 ms | 0.1427 ms |
| `edge_case_none_vs_missing_field` | Approach B (Normalized Execution Plan) | 0.0228 ms | 0.0099 ms |
| `edge_case_none_vs_missing_field` | Approach C (Direct JSON Tree Evaluator) | 0.0048 ms | 0.0027 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (evaluate_condition) | 0.1482 ms | 0.0731 ms |
| `edge_case_none_vs_missing_field` | Approach A (Experimental Restricted Code Object) | 0.4833 ms | 0.3615 ms |
| `edge_case_none_vs_missing_field` | Canonical Condition (Prepared Artifact Runtime) | 0.1203 ms | 0.0739 ms |

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