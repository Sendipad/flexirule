# FlexiRule Operation-Level Verification Matrix

## Section A — Executive Summary

- **Audit Date**: 2026-11-01
- **Repository**: [https://github.com/Sendipad/flexirule](https://github.com/Sendipad/flexirule)
- **Audited Commit SHA**: `504840d3bf3ec012a2c0ed5c7859bc7a7fd1b3c2`
- **Audit Target (as recorded by the audit)**: `develop` (the associated PR currently targets `feat/canonical-condition-backend`).
- **Review Scope Note (2026-11-02)**: The audited SHA is `504840d3bf3ec012a2c0ed5c7859bc7a7fd1b3c2`. The PR base (`8f1b1884a235940d2ef5da625490a9668c27e896`) is 39 commits ahead of that SHA. The final reviewed PR head is seven commits ahead of the audited SHA; all six commits added after the original report commit are report-only corrections and do not refresh the source audit. The report is therefore a historical snapshot, not a complete re-audit of the current PR base. Operation totals and test results below must remain scoped to the audited SHA until re-run against the intended release candidate.
- **Audit Scope**: Comprehensive source code audit and empirical verification of every supported FlexiRule RuleFlow Action Type and individual operation, covering frontend registration, configuration UI components, backend contracts, schema validation, runtime handlers, authorization boundaries, error and transaction handling, and test coverage.
- **Discovered Action Types**: 13
- **Discovered Individual Operations**: 43 (31 core Action Type operations across 13 Action Types + 12 Process operations across 4 Process modules)
- **Status Breakdown**:
  - **PASS**: 37 operations
  - **PARTIAL**: 6 operations (`Loop`, `Switch`, `Wait`, `Notify.System`, `Notify.Email`, `Notify.Provider`)
  - **FAIL**: 0 operations
  - **UNVERIFIED**: 0 operations
  - **DISABLED**: 0 operations
  - **EXPERIMENTAL**: 0 operations
- **Confirmed P0 Findings**: 0
- **Confirmed P1 Findings**: 2 (`REL-001`: Loop/Switch release-gate drift, tracked in [issue #360](https://github.com/Sendipad/flexirule/issues/360); `SWT-001`: Switch canvas/runtime routing and graph-validation mismatch)
- **P2 Findings Requiring Release Treatment**: 2 (`WIT-001`: Wait blocks the executing worker thread via `time.sleep()`, `NOT-001`: Realtime / provider notifications may escape the database transaction; Email is queued by default in Frappe v15).
- **RC1 Recommendation**: **NOT READY** until `REL-001` and `SWT-001` are resolved, or both `Loop` and `Switch` are kept server-side gated for RC1.

---

## Section B — Authoritative Catalog

Discovered strictly from source inspection of `flexirule/ruleflow/core/action_handlers/`, `flexirule/ruleflow/core/contract_utils.py`, `flexirule/ruleflow/core/contract_dto.py`, and `flexirule/ruleflow/process/`.

| Action Type | Operation / Mode | UI Component | Backend Contract | Validation Mode | Runtime Handler | Test Status | Assigned Agent |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Entry Action** | Entry Action | `StartNodeProperties.vue` | `ActionContract` | Backend / Full | `EntryActionHandler` | PASS | Agent 1 |
| **Condition** | Condition | `ConditionStep.vue` | `OperationContract` | Backend & Evaluator | `ConditionHandler` | PASS | Agent 1 |
| **Switch** | Switch | `SwitchConfig.vue` / `SwitchNodeConfig.vue` | `ActionContract` | Frontend & Graph | `SwitchHandler` | PARTIAL | Agent 1 |
| **Loop** | Loop | `LoopConfig.vue` / `LoopNodeConfig.vue` | `ActionContract` | Backend (`_validate_flow_constraints`) | `LoopHandler` | PASS | Agent 1 |
| **Stop** | Success | Canvas / Modal | `OperationContract` | Backend | `StopHandler` | PASS | Agent 1 |
| **Stop** | Error | Canvas / Modal | `OperationContract` | Backend | `StopHandler` | PASS | Agent 1 |
| **Raise Error** | Raise Error | `RaiseErrorConfig.vue` | `OperationContract` | Backend | `RaiseErrorHandler` | PASS | Agent 1 |
| **Wait** | Wait | `WaitConfig.vue` / `WaitNodeConfig.vue` | `OperationContract` | Backend | `WaitHandler` | PASS | Agent 6 |
| **Assignment** | Assignment (7 operators) | `AssignmentConfig.vue` | `OperationContract` | Backend & Resolver | `AssignmentHandler` | PASS | Agent 2 |
| **Sub-Rule** | Sub-Rule | `SubRuleConfig.vue` / `SubRuleNodeConfig.vue` | `OperationContract` | Backend (`validate_sub_rule_contract`) | `SubRuleHandler` | PASS | Agent 6 |
| **Document Action** | Create New | `DocumentActionConfig.vue` | `OperationContract` | Backend | `DocumentActionHandler._create_new` | PASS | Agent 4 |
| **Document Action** | Update Existing | `DocumentActionConfig.vue` | `OperationContract` | Backend | `DocumentActionHandler._update_existing` | PASS | Agent 4 |
| **Document Action** | Delete Record | `DocumentActionConfig.vue` | `OperationContract` | Backend | `DocumentActionHandler._delete_record` | PASS | Agent 4 |
| **Document Action** | Create ToDo | `DocumentActionConfig.vue` | `OperationContract` | Backend | `DocumentActionHandler._create_todo` | PASS | Agent 4 |
| **Document Action** | Add Comment | `DocumentActionConfig.vue` | `OperationContract` | Backend | `DocumentActionHandler._add_comment` | PASS | Agent 4 |
| **Query Records** | Fetch Records | `QueryRecordsConfig.vue` | `OperationContract` | Backend (`validate_fetch_records`) | `QueryRecordsHandler._fetch_records` | PASS | Agent 3 |
| **Query Records** | Query List | `QueryRecordsConfig.vue` | `OperationContract` | Backend | `QueryRecordsHandler._query_list` | PASS | Agent 3 |
| **Query Records** | Query Doc | `QueryRecordsConfig.vue` | `OperationContract` | Backend (`validate_graph_integrity`) | `QueryRecordsHandler._query_doc` | PASS | Agent 3 |
| **Query Records** | Exist Record | `QueryRecordsConfig.vue` | `OperationContract` | Backend | `QueryRecordsHandler._exist_record` | PASS | Agent 3 |
| **Query Records** | Query Report | `QueryRecordsConfig.vue` | `OperationContract` | Backend | `QueryRecordsHandler._query_report` | PASS | Agent 3 |
| **Query Records** | Count | `QueryRecordsConfig.vue` | `OperationContract` | Backend | `QueryRecordsHandler._count_records` | PASS | Agent 3 |
| **Query Records** | Sum | `QueryRecordsConfig.vue` | `OperationContract` | Backend | `QueryRecordsHandler._aggregate` | PASS | Agent 3 |
| **Query Records** | Average | `QueryRecordsConfig.vue` | `OperationContract` | Backend | `QueryRecordsHandler._aggregate` | PASS | Agent 3 |
| **Query Records** | Min | `QueryRecordsConfig.vue` | `OperationContract` | Backend | `QueryRecordsHandler._aggregate` | PASS | Agent 3 |
| **Query Records** | Max | `QueryRecordsConfig.vue` | `OperationContract` | Backend | `QueryRecordsHandler._aggregate` | PASS | Agent 3 |
| **Query Records** | Group By | `QueryRecordsConfig.vue` | `OperationContract` | Backend | `QueryRecordsHandler._group_by` | PASS | Agent 3 |
| **Notify** | Toast | `NotifyConfig.vue` | `OperationContract` | Backend | `NotifyHandler` | PASS | Agent 6 |
| **Notify** | System | `NotifyConfig.vue` | `OperationContract` | Backend | `NotifyHandler` | PASS | Agent 6 |
| **Notify** | Email | `NotifyConfig.vue` | `OperationContract` | Backend | `NotifyHandler` | PASS | Agent 6 |
| **Notify** | System Notification | `NotifyConfig.vue` | `OperationContract` | Backend | `NotifyHandler` | PASS | Agent 6 |
| **Notify** | Provider | `NotifyConfig.vue` | `OperationContract` | Backend | `NotifyHandler` | PASS | Agent 6 |
| **Process (Validation)** | `value_in_range` | `ProcessConfig.vue` | Process Contract V2 | JSON Schema | `validation.value_in_range` | PASS | Agent 5 |
| **Process (Validation)** | `conditional_required` | `ProcessConfig.vue` | Process Contract V2 | JSON Schema | `validation.conditional_required` | PASS | Agent 5 |
| **Process (Validation)** | `child_table_rows` | `ProcessConfig.vue` | Process Contract V2 | JSON Schema | `validation.child_table_rows` | PASS | Agent 5 |
| **Process (Validation)** | `composite_uniqueness` | `ProcessConfig.vue` | Process Contract V2 | JSON Schema | `validation.composite_uniqueness` | PASS | Agent 5 |
| **Process (Validation)** | `role_check` | `ProcessConfig.vue` | Process Contract V2 | JSON Schema | `validation.role_check` | PASS | Agent 5 |
| **Process (Validation)** | `on_field_change` | `ProcessConfig.vue` | Process Contract V2 | JSON Schema | `validation.on_field_change` | PASS | Agent 5 |
| **Process (Dedupe)** | `find_duplicates_in_child_table` | `ProcessConfig.vue` | Process Contract V2 | JSON Schema | `deduplication.find_duplicates_in_child_table` | PASS | Agent 5 |
| **Process (Dedupe)** | `find_matching_records` | `ProcessConfig.vue` | Process Contract V2 | JSON Schema | `deduplication.find_matching_records` | PASS | Agent 5 |
| **Process (Batch)** | `execute_for_documents` | `ProcessConfig.vue` | Process Contract V2 | JSON Schema | `batch.execute_for_documents` | PASS | Agent 5 |
| **Process (Enrichment)** | `calculate_value` | `ProcessConfig.vue` | Process Contract V2 | JSON Schema | `enrichment.calculate_value` | PASS | Agent 5 |
| **Process (Enrichment)** | `linked_doc_autocomplete` | `ProcessConfig.vue` | Process Contract V2 | JSON Schema | `enrichment.linked_doc_autocomplete` | PASS | Agent 5 |
| **Process (Enrichment)** | `copy_from_template` | `ProcessConfig.vue` | Process Contract V2 | JSON Schema | `enrichment.copy_from_template` | PASS | Agent 5 |

*Note on Legacy & Deprecated Operations*:
- `Query Records / Query API`: Explicitly rejected during validation (`validation_service.py:345`: `Action '{0}' uses removed mode Query API`). Fully removed from current catalog.
- **Release-gate drift (`REL-001`, tracked by [issue #360](https://github.com/Sendipad/flexirule/issues/360))**: `contract_utils.RELEASE_DISABLED_ACTION_TYPES` is empty and the backend contract DTO passes that empty set to `contracts.js`; however, `utils/variable_validator.js:23,312-319` independently hardcodes `Loop` and `Switch` as disabled. The frontend rejects these actions while backend validation/runtime helpers do not. This is a client-only gate, not server enforcement. Do not claim Loop and Switch are formally disabled or release-ready until the backend canonical set, DTO, frontend validation and runtime agree.

---

## Section C — Operation-Level Verification Matrix

| Action Type | Operation | UI/Contract | Runtime | Validation | Security | Error / Transaction | Tests | Overall Status | Finding IDs |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Entry Action** | Entry Action | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Condition** | Condition | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Switch** | Switch | PARTIAL | UNVERIFIED | PARTIAL | PASS | PASS | UNVERIFIED | **PARTIAL** | `REL-001`, `SWT-001` |
| **Loop** | Loop | PARTIAL | PASS | PARTIAL | PASS | PASS | PASS | **PARTIAL** | `REL-001` |
| **Stop** | Success | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Stop** | Error | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Raise Error** | Raise Error | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Wait** | Wait | PASS | PASS | PASS | PASS | PARTIAL | PASS | **PARTIAL** | `WIT-001` |
| **Assignment** | Assignment | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Sub-Rule** | Sub-Rule | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Document Action** | Create New | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Document Action** | Update Existing | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Document Action** | Delete Record | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Document Action** | Create ToDo | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Document Action** | Add Comment | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Query Records** | Fetch Records | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Query Records** | Query List | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Query Records** | Query Doc | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Query Records** | Exist Record | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Query Records** | Query Report | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Query Records** | Count | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Query Records** | Sum | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Query Records** | Average | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Query Records** | Min | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Query Records** | Max | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Query Records** | Group By | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Notify** | Toast | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Notify** | System | PASS | PASS | PASS | PASS | PARTIAL | PASS | **PARTIAL** | `NOT-001` |
| **Notify** | Email | PASS | PASS | PASS | PASS | PARTIAL | PASS | **PARTIAL** | `NOT-001` |
| **Notify** | System Notification | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Notify** | Provider | PASS | PASS | PASS | PASS | PARTIAL | PASS | **PARTIAL** | `NOT-001` |
| **Process** | `value_in_range` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process** | `conditional_required`| PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process** | `child_table_rows` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process** | `composite_uniqueness`| PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process** | `role_check` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process** | `on_field_change` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process** | `find_duplicates_in_child_table` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process** | `find_matching_records` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process** | `execute_for_documents` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process** | `calculate_value` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process** | `linked_doc_autocomplete`| PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process** | `copy_from_template` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |

---

## Section D — Operation Details

### D.1 Control Flow: Entry, Condition, Switch, Loop, Stop, Raise Error

#### Entry Action
- **Contract**: Top-level start node (`action_type="Entry Action"` or `action_id="root"`). Requires exactly 1 start node for active rules. `terminal=False`, `has_next_true=True`, `has_next_false=False`.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/simple_actions.py` (`EntryActionHandler.execute`), returns `(None, action.next_step_if_true)`.
- **Validation**: Enforced by `validation_service.py` (`len(entry_nodes) == 1` for active rules) and `graph_validator.py`.
- **Security**: Bound to parent Rule permissions; does not alter docstate.
- **Failure Behavior**: Pass-through; failures abort execution.
- **Tests**: Verified across `test_engine.py`, `test_engine_comprehensive.py`, `test_real_rules.py`. Status: **PASS**.

#### Condition
- **Contract**: Evaluates canonical AST condition JSON or compiled python condition. `has_next_true=True`, `has_next_false=True`. Required fields: `config`.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/condition.py` (`ConditionHandler.execute`), routes to `evaluate_condition` / `evaluate_prepared_condition` in `condition_evaluator.py`.
- **Validation**: Validates canonical condition node structure; raises `ConditionValidationError` if malformed or non-boolean.
- **Security**: Evaluated inside pure sandbox (`SafeFrappeAPI`, whitelist operators, no dunder/import access).
- **Failure Behavior**: On exception, logs error and either raises or respects rule error policy.
- **Tests**: Tested in `test_canonical_condition_evaluator.py` (34 tests), `test_condition_contract.py`, `test_engine_comprehensive.py`. Status: **PASS**.

#### Switch
- **Contract**: Multi-branch router. The current `ActionContract` declares `has_next_true=False`, `has_next_false=True`, but runtime only routes configured case matches and falls back through `next_step_if_true`; it never follows a generic false path. The contract should describe the default fallback as the normal output (`has_next_true=True`, `has_next_false=False`), while case-specific branches remain explicit dynamic outputs.
- **Execution Path**: `SwitchHandler.execute` evaluates the expression through `engine._evaluate_python_value(...)`, routes a match through `config.cases[val]` / `config.cases[str(val)]`, and uses `action.next_step_if_true` as the fallback when there is no matching case (or when the expression/config is absent). A `cases["default"]` entry is not a special fallback; it is only a case for the literal evaluated value `"default"`.
- **Canvas Integration Defect**: `App.vue` maps `node-switch` to `ProcessNode`, and `ProcessNode` renders only a source `Handle` with id `default`. However, `SwitchConfig.syncEdges` creates case edges with `sourceHandle` equal to each case value. No matching case handles are rendered by the current node component, so the saved case-edge model and the canvas handle model are inconsistent. The existing `reports/proposal/switch-node-edge-implementation-proposal.md` specifies a dedicated Switch node, dynamic branch handles, immutable branch IDs, and a distinct default fallback handle; current code uses the mutable case value as the handle ID.
- **Validation Defect**: `graph_validator.get_neighbors` sees ordinary next-step fields but does not read `config.cases`. It can therefore miss actual case edges for reachability, cycle detection, and reference validation. On the current PR base, `_loop_body_returns_to_loop` has a Switch-specific case-target traversal, but the global `_validate_flow_constraints` outgoing graph and `graph_validator.validate_graph_integrity` still do not model all Switch routes (`SWT-001`).
- **Security**: The handler delegates expression evaluation to `RuleEngine._evaluate_python_value` (which delegates to the engine's `eval_value` helper); `SwitchHandler` does not call `frappe.safe_eval` directly.
- **Failure Behavior**: Expression evaluation failures are logged and re-raised. An unmatched value follows `next_step_if_true`; there is no separate implicit `cases["default"]` semantic.
- **Tests**: `test_engine_comprehensive.py:test_engine_execute_switch_action` is explicitly skipped with `self.skipTest("Switch action is disabled for the v0.1 release surface")`. The Switch fixture in `test_advanced_rule_flows.py` is included for action-type catalog coverage with empty `cases`; that test does not execute Switch routing. The cited tests also do not cover rendered case handles. Runtime routing, graph validation, and the visual case-edge contract are therefore **UNVERIFIED by the cited tests**. Status: **PARTIAL**.
#### Loop
- **Contract**: Iterates over collection. `has_next_true=True` (body path), `has_next_false=True` (after last / complete path). Requires `config` and `return_variable` (item alias).
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/loop.py` (`LoopHandler.execute`). Maintains iteration state in `context["vars"]["_loops"][action_id]`. Exposes current item under alias and metadata under `context["vars"]["loop"]` (`index`, `first`, `last`, `length`).
- **Validation**: Strict graph validation in `validation_service.py` (`_loop_body_returns_to_loop`) verifies that body path cycles back to the Loop node and After-Last path leads downstream without loop-shadowing.
- **Security**: Memory iteration bounded by max node visit limits in `RuleEngine` (`max_visits_per_node=1000`).
- **Failure Behavior**: Errors in loop body abort or follow action error policy. Loop state cleaned up on completion.
- **Tests**: `test_loop_flow_constraints.py`, `test_engine_comprehensive.py:test_engine_execute_loop_action`. Status: **PASS**.

- **Release Gate (`REL-001`)**: The frontend `utils/variable_validator.js` hardcodes `Loop` and `Switch` as release-disabled, but backend `contract_utils.RELEASE_DISABLED_ACTION_TYPES` is empty; the contract DTO sends that empty list to `contracts.js`. Therefore frontend validation rejects Loop and Switch while the backend canonical helper used by validation/runtime does not. This is an existing P1 RC1 gate inconsistency tracked in [issue #360](https://github.com/Sendipad/flexirule/issues/360). Keep Loop gated server-side until the backend set, DTO, frontend and runtime share one authoritative release policy.

#### Stop
- **Contract**: Terminal action. `terminal=True`, `has_next_true=False`, `has_next_false=False`. Modes: `Success` and `Error`.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/simple_actions.py` (`StopHandler.execute`). Mode `Success` terminates flow with `(None, None)`. Mode `Error` renders `value_template` with Jinja and calls `frappe.throw()`.
- **Validation**: Enforced terminal (must not have outgoing edges). `Error` requires non-empty message template.
- **Security**: Jinja rendering uses `SafeFrappeAPI` context.
- **Failure Behavior**: Stops engine loop immediately.
- **Tests**: `test_engine_comprehensive.py:test_engine_execute_stop_action`. Status: **PASS**.

#### Raise Error
- **Contract**: Terminal error action. `terminal=True`, `has_next_true=False`, `has_next_false=False`. Required field: `value_template`.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/simple_actions.py` (`RaiseErrorHandler.execute`). Renders message with `SafeFrappeAPI`, appends Rule provenance link, throws `frappe.ValidationError` or `frappe.PermissionError`.
- **Validation**: Enforces terminal node constraints; requires `value_template`.
- **Security**: Jinja rendering protected against SSTI; read-only context.
- **Failure Behavior**: Halts transaction and rolls back uncommitted changes.
- **Tests**: `test_real_rules.py:test_raise_error_stops_execution`, `test_advanced_rule_flows.py`. Status: **PASS**.

---

### D.2 Data Mutation: Assignment

#### Assignment & Operators
- **Contract**: Sequential batch state mutation. Required field: `config` (JSON array of assignment rows). Supports target paths starting with `doc.` or `vars.`.
- **Supported Operators**:
  1. `set`: Sets target to evaluated operand. Idempotent.
  2. `clear`: Resets target to empty/default type (`None`, `""`, `[]`, `{}`). Idempotent.
  3. `increment`: Adds numeric operand to numeric field. Supported: `Int`, `Float`, `Currency`, `Percent`.
  4. `decrement`: Subtracts numeric operand from numeric field. Supported: `Int`, `Float`, `Currency`, `Percent`.
  5. `append`: Appends operand to target list (`Table`, `Table MultiSelect`). Non-idempotent.
  6. `merge`: Merges dictionary operand into target dictionary (`JSON`, `Code`, `Text`). Non-idempotent.
  7. `toggle`: Inverts boolean/check field (`0` <-> `1`). Non-idempotent.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/assignment.py` (`AssignmentHandler.execute`):
  - **Phase A (Preflight)**: Validates target paths against DocType metadata and checks `AFTER_EVENT_MUTATION_BLOCKLIST`. Resolves operator instances from `AssignmentOperatorRegistry`. Compiles canonical condition guards (`when_condition`).
  - **Phase B (Staged Execution)**: Applies mutations sequentially to deep copies of `doc` and `vars`. Any error discards staged changes cleanly without touching live state.
  - **Phase C (Atomic Commit)**: Applies staged mutations to real document and context.
- **Validation**: `validation_service._validate_assignment_inline` and `rule.py:_validate_assignment`. Forbids system prefixes (`meta.`, `frappe.`, `rule.`). Enforces `allow_on_submit` if rule triggers after submit.
- **Security**: Direct field mutations respect Frappe DocType schema constraints; deep dotted paths rejected in v1 (`len(parts) == 2` enforced for `doc`).
- **Failure Behavior**: Staged rollback prevents partial memory corruption on resolver errors.
- **Tests**: `test_assignment_condition_guards.py` (21 tests), `test_assignment_resolver.py`, `test_compiled_controls.py`. Status: **PASS**.

---

### D.3 Data Retrieval: Query Records

#### Fetch Records
- **Contract**: Query builder engine. Requires `reference_doctype`, `operation="Fetch Records"`. Supports canonical boolean filter tree, ordering, pagination, field aliases, and computed literal columns.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/query_records.py` (`_fetch_records`), delegates to `flexirule/ruleflow/utils/frappe_query_compat.py` (`execute_query` using `frappe.qb.get_query`).
- **Validation**: `validate_fetch_records` validates canonical filter tree, ensures fields exist on DocType, rejects child-table aggregations without PyPika joins, and verifies literal column definitions.
- **Security**: In Frappe v15, Query Builder does not natively apply user permissions. FlexiRule explicitly enforces fail-closed permission checks: requires explicit `ignore_permissions=1` with non-empty `permission_audit_reason`, or raises `ValidationError`.
- **Failure Behavior**: Fails closed on invalid fields or permissions; returns empty list if limit is 0.
- **Tests**: `test_fetch_records.py` (27 tests), `test_fetch_records_filter_tree_integration.py`, `test_fetch_records_tree_operators.py`. Status: **PASS**.

#### Query List
- **Contract**: Standard Frappe query. Requires `reference_doctype`. Returns `List of Records`.
- **Execution Path**: `QueryRecordsHandler._query_list`, calls `frappe.get_list()`.
- **Validation**: Validates target DocType and standard filters.
- **Security**: Automatically enforces standard Frappe user permissions and user permissions rules.
- **Failure Behavior**: Native Frappe permission error or DB syntax error handling.
- **Tests**: `test_query_records_filters.py`, `test_query_records_field_navigation.py`. Status: **PASS**.

#### Query Doc
- **Contract**: Fetches single record. Returns `Single Record` or `Full Document`. Supports static name, dynamic `docname_expression`, or `get_latest` strategy.
- **Execution Path**: `QueryRecordsHandler._query_doc`, calls `frappe.get_doc()` or `frappe.get_single_value()`.
- **Validation**: Enforces that Single DocTypes are persistence-backed (`graph_validator.py` blocks virtual singles).
- **Security**: Enforces read permission on referenced DocType unless bypass authorized.
- **Failure Behavior**: Throws `DoesNotExistError` if required record missing and fallback not set.
- **Tests**: `test_query_records_refactor.py` (17 tests). Status: **PASS**.

#### Exist Record
- **Contract**: Verifies record existence. Returns boolean (`Yes / No`).
- **Execution Path**: `QueryRecordsHandler._exist_record`, calls `frappe.get_list(reference_doctype, filters=..., limit=1)` with user permissions.
- **Validation**: Requires `reference_doctype`.
- **Security**: Permission-aware read.
- **Failure Behavior**: Returns `False` on empty match.
- **Tests**: Covered under `test_query_records_filters.py`. Status: **PASS**.

#### Query Report
- **Contract**: Executes standard Frappe Report. Returns `List of Records`. Requires `report_name` in config.
- **Execution Path**: `QueryRecordsHandler._query_report`, calls `frappe.desk.query_report.run(report_name, filters=...)`.
- **Validation**: Validates that report exists and resolves filter dictionaries.
- **Security**: Explicitly checks `frappe.has_permission(reference_doctype, "report")`.
- **Failure Behavior**: Invalid report throws `ValidationError`.
- **Tests**: `test_query_report_serialization.py` (2 tests). Status: **PASS**.

#### Aggregations (Count, Sum, Average, Min, Max, Group By)
- **Contract**: Metric and aggregation queries. Count/Sum/Avg/Min/Max return `List of Values` (numeric result); Group By returns `List of Records`.
- **Execution Path**: `QueryRecordsHandler._count_records`, `_aggregate`, `_group_by`. All execute through `frappe.get_list()` with native SQL aggregation functions (`count(name)`, `sum(field)`, `avg(field)`, `min(field)`, `max(field)`).
- **Validation**: Validates aggregation field against DocType metadata.
- **Security**: Enforces Frappe document permissions through `frappe.get_list`.
- **Failure Behavior**: Returns `0` or `None` on empty matches.
- **Tests**: `test_query_records_field_navigation.py`, `test_query_records_filters.py`. Status: **PASS**.

---

### D.4 Document Mutation: Document Action

#### Create New
- **Contract**: Creates and inserts a new document. Supports field mapping, static values, table mappings, and same-field copy.
- **Execution Path**: `DocumentActionHandler._create_new`. Assembles document dictionary, instantiates `frappe.get_doc(doc_data)`, and calls `new_doc.insert(ignore_permissions=...)`. Supports `is_async=True` via `frappe.enqueue`.
- **Validation**: Validates mandatory fields and target DocType.
- **Security**: Enforces `create` permissions on target DocType unless `ignore_permissions` is enabled with audit reason.
- **Failure Behavior**: Standard Frappe document validation hooks (`validate`, `before_insert`) execute; errors abort transaction.
- **Tests**: `test_compiled_controls.py`, `test_real_rules.py:test_rule_04_document_actions_and_context`. Status: **PASS**.

#### Update Existing
- **Contract**: Modifies an existing document. Resolves target document name from `action.reference_docname`, `config.docname_expression`, or `config.docname`.
- **Execution Path**: `DocumentActionHandler._update_existing`. Loads document with `frappe.get_doc(reference_doctype, docname)`, applies field mappings, and calls `doc.save(ignore_permissions=...)`.
- **Validation**: Requires non-empty document identifier.
- **Security**: Enforces `write` permission on target document.
- **Failure Behavior**: Executes document validation and triggers update hooks; errors abort transaction.
- **Tests**: `test_real_rules.py:test_rule_08_bulk_status_update`, `test_rule_09_cross_doc_query_and_update`. Status: **PASS**.

#### Delete Record
- **Contract**: Permanently removes a document. Returns `{"deleted": True, "doctype": ..., "name": ...}`.
- **Execution Path**: `DocumentActionHandler._delete_record`. Checks `frappe.has_permission(reference_doctype, "delete", docname)`, then calls `frappe.delete_doc(reference_doctype, docname, ignore_permissions=...)`.
- **Validation**: Requires valid target document name.
- **Security**: Enforces `delete` permissions.
- **Failure Behavior**: Deletion hooks execute; DB foreign key constraints enforced.
- **Tests**: Unit tested and validated in handler suite. Status: **PASS**.

#### Create ToDo & Add Comment
- **Contract**: Convenience modes for Frappe ToDo assignments and timeline comments.
- **Execution Path**: `DocumentActionHandler._create_todo` and `_add_comment`.
  - `Create ToDo` instantiates a `ToDo` doc linked to `context["doc"]` (`reference_type`, `reference_name`).
  - `Add Comment` calls `context["doc"].add_comment("Comment", text)` or inserts `Comment` record.
- **Validation**: Enforces required config keys: `assigned_to` and `description` for ToDo; `comment_text` for Comment.
- **Security**: Respects comment/ToDo permissions or audited bypass.
- **Failure Behavior**: Database rollback removes inserted ToDo/Comment if subsequent transactional actions fail.
- **Tests**: `test_real_rules.py:test_rule_04_document_actions_and_context`, `test_advanced_rule_flows.py`. Status: **PASS**.

---

### D.5 Process Operations: Process Contract V2

All Process operations are registered under declarative Process Contract V2 (`flexirule/ruleflow/core/process_contract_v2.py`) and executed through `ProcessRuntimeV2` (`flexirule/ruleflow/core/process_runtime_v2.py`).

- **Architecture**:
  - `config_schema`: Strict JSON Schema validating configuration properties.
  - `result_schema`: Strict JSON Schema validating returned data.
  - `capabilities`: Defines `requires_doc`, `writes_to`, `allows_async`, `transactional`, `can_stop_save`, `has_side_effect`.
  - `OperationAdapterRegistry`: Registers adapters for `validate`, `transform`, `lookup`, `dedupe`, `batch`.
- **Audited Operations (12 total)**:
  1. `Validation.value_in_range`: Validates numeric field bounds. Returns `{"is_valid": bool, "errors": list}`. Status: **PASS**.
  2. `Validation.conditional_required`: Enforces conditional field requirements. Status: **PASS**.
  3. `Validation.child_table_rows`: Validates child-table row constraints. Status: **PASS**.
  4. `Validation.composite_uniqueness`: Enforces uniqueness across parent and child-table fields. Status: **PASS**.
  5. `Validation.role_check`: Evaluates user roles (`has_any`, `has_all`, `not_has_any`). Status: **PASS**.
  6. `Validation.on_field_change`: Detects document field mutations against `old_doc`. Status: **PASS**.
  7. `Deduplication.find_matching_records`: Weighted field scoring for duplicate candidate detection. Status: **PASS**.
  8. `Deduplication.find_duplicates_in_child_table`: Detects duplicate child records across parent documents. Status: **PASS**.
  9. `Batch.execute_for_documents`: Batched execution of a rule across document lists with progress emission. Status: **PASS**.
  10. `Enrichment.calculate_value`: Evaluates mathematical and string formulas in safe sandbox. Status: **PASS**.
  11. `Enrichment.linked_doc_autocomplete`: Automatically maps fields from linked document records. Status: **PASS**.
  12. `Enrichment.copy_from_template`: Copies field lists from template documents. Status: **PASS**.
- **Tests**: `test_process_contract_v2.py`, `test_process_runtime_v2.py`, `test_process_sync.py`, and process-specific suites in `flexirule/ruleflow/process/*/tests/`.

---

### D.6 Orchestration: Sub-Rule, Wait, Notify

#### Sub-Rule
- **Contract**: Reusable rule invocation. Requires `rule` (target callable Rule name).
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/sub_rule.py` (`SubRuleHandler.execute`):
  - Resolves target Rule via `RuleCoordinator.get_runtime_registry()` and `resolve_rule_reference()`.
  - Verifies target is `Callable Event`, `is_active`, and `exposed_as_subrule`.
  - Cross-rule cycle detection checks `execution_stack` using logical base names to block recursive deadlocks.
  - Enforces depth limits (`MAX_SUB_RULE_DEPTH = 5`).
  - Context isolation: Executes with `SubRuleContextVars(context["vars"])` copy-on-write wrapper. Sub-rule cannot corrupt parent context unless mapped to `return_variable`.
- **Validation**: `validation_service.py` (`validate_sub_rule_contract`) validates that required target inputs are mapped.
- **Security**: Caller must have permission to execute target rule; audited permission bypass supported.
- **Failure Behavior**: Exceptions in Sub-Rule propagate to parent rule and trigger parent error policy.
- **Tests**: `test_sub_rule_contract.py` (5 tests), `test_real_rules.py:test_subrule_isolation_with_return_variable`, `test_advanced_rule_flows.py`. Status: **PASS**.

#### Wait
- **Contract**: Pauses rule execution. Config contains `duration` (seconds); falls back to `action.timeout`.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/simple_actions.py` (`WaitHandler.execute`). Calls `time.sleep(duration)`.
- **Limitation (Finding `WIT-001`)**: `time.sleep()` is synchronous and blocks the executing worker thread. While acceptable for short delays in background jobs or test simulations, long waits block Gunicorn web workers during synchronous DocType events. Non-blocking durable scheduling (e.g. background job re-enqueue) is deferred to future releases.
- **Validation**: Duration parsed and coerced to float.
- **Security**: No database mutations.
- **Failure Behavior**: Sleep interruption logs error and halts.
- **Tests**: `test_engine_comprehensive.py:test_engine_execute_wait_action`. Status: **PASS**.

#### Notify
- **Contract**: Multi-channel notifications. Requires `value_template` and `operation`. Modes:
  1. `Toast`: Browser alert (`frappe.msgprint(..., alert=True)`).
  2. `System`: Realtime websocket publish (`frappe.publish_realtime`).
  3. `Email`: Calls `frappe.sendmail`; requires `recipients` and `subject`.
  4. `System Notification`: Creates a persistent `Notification Log` document for the target user.
  5. `Provider`: Calls a hook-registered provider (`flexirule_notification_providers`) synchronously; requires `provider` and `recipient`.
- **Execution Path**: `NotifyHandler.execute` does not set `delayed=False` or `now=True`, so Frappe v15 `frappe.sendmail` uses its default `delayed=True`. For the ordinary queue path, `QueueBuilder.process` inserts an `Email Queue` document. For `queue_separately` or more than 100 recipients, Frappe v15's `QueueBuilder.process` calls `frappe.enqueue(self.send_emails, ...)` without `enqueue_after_commit=True`; `frappe.enqueue` defaults that option to `False`, and the worker later creates queue rows and commits before sending. That bulk path can race the originating transaction. `frappe.publish_realtime` also defaults to `after_commit=False`, which the handler does not override. Provider hooks are invoked synchronously.
- **Validation**: Enforces required config keys per mode in `validation_service.py` and `NotifyHandler.validate()`.
- **Security**: Jinja templates are rendered using the handler's restricted template context. Provider behavior depends on the installed hook implementation.
- **Transaction Behavior (Finding `NOT-001`)**: It is inaccurate to describe all Email as immediate SMTP dispatch, but it is also unsafe to claim all queued Email is rollback-safe: the standard single-queue path inserts an Email Queue row in the current transaction, while the bulk / separately queued path can enqueue a worker before commit. Realtime publication is pre-commit by default; Provider hooks may perform non-transactional side effects. `System Notification` itself is a database record.
- **Tests**: Unit tests in `test_compiled_controls.py` and integration tests in `test_advanced_rule_flows.py` do not prove rollback behavior for each notification mode or recipient-count path. Status: **PARTIAL**.
---

## Section E — Cross-Operation Integration Matrix

| Scenario # | Scenario Description | Action Chain | Expected Result | Actual Result | Test Evidence | Findings |
| :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| **1** | Sequential State Mutation & Stop | Entry → Assignment → Condition → Stop | Assignment sets doc/vars; Condition checks mutated state; flow terminates at Stop node. | Verified: Staged atomic commit applies updates before Condition evaluation. | `test_real_rules.py:test_rule_03_before_save_validation` | None |
| **2** | Boolean Branch Routing | Entry → Condition → True / False Branches | True branch executes on match; False branch executes on non-match. | Verified: Evaluates canonical condition AST and branches correctly. | `test_engine_comprehensive.py:test_engine_execute_condition_true` | None |
| **3** | Collection Iteration & Accumulation | Entry → Loop → Assignment → Next Iteration | Loops over items; updates index metadata; exits via false path after last item. | Verified: `_loops` context accurately tracks index, length, and terminates. | `test_engine_comprehensive.py:test_engine_execute_loop_action` | None |
| **4** | Query Retrieval to Condition | Query Records → Context Variable → Condition | Query Records populates `vars.records`; Condition tests count or field values. | Verified: Context variables are immediately available to downstream condition guards. | `test_real_rules.py:test_rule_09_cross_doc_query_and_update` | None |
| **5** | Data Pipeline: Calculation to Record Creation | Assignment → Document Action (Create New) | Assignment computes values in context; Document Action creates target record with mapped fields. | Verified: Field mappings resolve variables and insert target document. | `test_real_rules.py:test_rule_04_document_actions_and_context` | None |
| **6** | Business Logic Process to Context | Process (Validation/Dedupe) → Result Variable → Assignment | Process executes operation; writes boolean/record to `return_variable`; Assignment updates doc status. | Verified: Output schema and return type validated before context write. | `test_real_rules.py:test_rule_02_phone_validation_subrule` | None |
| **7** | Isolated Sub-Rule Execution | Parent Rule → Sub-Rule → Return Variable | Sub-rule executes with isolated vars; returns results to parent without contaminating parent context. | Verified: `SubRuleContextVars` enforces copy-on-write namespace isolation. | `test_real_rules.py:test_subrule_isolation_with_return_variable` | None |
| **8** | Configured Error Policy Handling | Action Failure → On Error (Continue / Retry / Rollback) | Error in non-critical action either continues, retries with backoff, or halts execution. | Verified: `on_error="Continue"` proceeds to `next_step_if_true`; `"Retry"` performs exponential backoff. | `test_real_rules.py:test_rule_05_error_handling_continue` | None |
| **9** | Document Action Savepoint Rollback | Document Action Failure → Transaction Rollback | Failure during document mutation triggers savepoint rollback, preventing partial DB commits. | Verified: Engine creates action savepoint and rolls back MariaDB state on error. | `test_engine.py:test_engine_process_execution` | None |
| **10** | Notification side effect followed by downstream failure | Notify (System realtime / Provider / Email) → Subsequent Failure | Rule transaction rolls back. | `System` realtime publishes with `after_commit=False`; Provider runs synchronously. Frappe v15 Email is normally queued, but for `queue_separately` or more than 100 recipients its QueueBuilder enqueues a worker without `enqueue_after_commit=True`; that worker can commit its own Email Queue rows and send before the originating transaction outcome is known. | Source trace of `NotifyHandler`, Frappe v15 `sendmail`, `QueueBuilder.process`, `frappe.enqueue`, and `publish_realtime`; no per-mode rollback test cited. | `NOT-001` |

---

## Section F — RC1 Release Blockers

| Finding ID | Affected Operation | Severity | Evidence & Location | Business / Technical Impact | Recommended Correction | Required Test to Close | RC1 Disposition |
| :--- | :--- | :---: | :--- | :--- | :--- | :--- | :---: |
| **REL-001** | Loop and Switch release availability | **P1** | `contract_utils.py:64` leaves `RELEASE_DISABLED_ACTION_TYPES` empty; `is_release_disabled_action()` checks that set and the contract DTO serializes it. `utils/variable_validator.js:23,312-319` independently hardcodes `Loop` and `Switch`; `contracts.js:109-111` consumes the empty DTO list. Existing project tracking: [issue #360](https://github.com/Sendipad/flexirule/issues/360). | Frontend validation blocks Loop/Switch, but backend validation/runtime do not reject them through the canonical release gate. A request that bypasses client validation can still submit or execute them; Switch additionally has the structural defects in `SWT-001`. | Keep Loop and Switch in the backend canonical release-disabled set for RC1; derive DTO and frontend state from that one source; remove the independent hardcoded frontend set; reject both at backend activation and runtime boundaries. | Backend tests for `validate_rule_definition` and runtime rejection; DTO serialization test; frontend tests proving the client consumes the same backend gate; regression tests for bypassed/direct requests. | **Keep both gated until the complete behavior is deliberately released** |
| **SWT-001** | `Switch` Action | **P1** | `switch.py:27-28` declares `has_next_true=False`, `has_next_false=True`, while `switch.py:72` falls back to `next_step_if_true`. `App.vue:83-85` maps `node-switch` to `ProcessNode`; `ProcessNode.vue:146-152` renders only the `default` source handle, while `SwitchConfig.vue:82-89` emits case edges with `sourceHandle` equal to the case value. `graph_validator.py:20-27` omits `config.cases`; reference validation at `graph_validator.py:56-60` also omits case targets. The PR-base `_validate_flow_constraints` global adjacency is still next-step-only; only `_loop_body_returns_to_loop` has a Switch-specific case traversal. | The canvas has no matching output handle for its configured case edges. Active rules can have valid case targets omitted from reachability, and case-edge cycles or missing targets can escape validation. The generic false pointer is not a runtime route. | Align the contract to `has_next_true=True`, `has_next_false=False`; implement a dedicated Switch node with dynamic case handles and a distinct default handle, using stable branch IDs (with compatibility for existing `config.cases` data). Centralize routing adjacency so case targets plus the `next_step_if_true` fallback are used for missing-reference checks, cycle detection, global reachability, and loop-return analysis. | Add frontend tests for rendered case/default handles and edge serialization; backend integration tests for multiple case targets, fallback, missing target rejection, case-edge cycle detection, and exclusion of the unused false pointer. | **Must be resolved or Switch gated before RC1** |

---

## Section G — Accepted Limitations and Deferrals

| Limitation ID | Affected Operation | Current Behavior | Why Acceptable for RC1 | User Impact & Workaround | Documentation Requirement | Follow-up Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **WIT-001** | `Wait` Action | Uses synchronous `time.sleep(duration)` in `simple_actions.py:153-155`. | This is a known synchronous delay, not a non-blocking wait. Short bounded delays may be tolerable, but the current implementation consumes the executing worker thread. | A long wait blocks a Gunicorn request worker in synchronous DocType events or consumes background-worker capacity when run in a job. Moving the same `sleep` into a background job does not make it non-blocking. | State clearly that Wait blocks the current worker; do not recommend long delays or imply that scheduler jobs avoid worker occupancy. | A future durable wait must persist/resume rule execution state through delayed scheduling rather than sleep inside a worker. |
| **NOT-001** | `Notify` (System realtime / Provider / bulk Email path) | `System` calls `frappe.publish_realtime` with default `after_commit=False`; Provider invokes its hook synchronously. Frappe v15 Email defaults to `delayed=True`; the ordinary path inserts an Email Queue row, while `queue_separately` / more than 100 recipients calls `frappe.enqueue` without `enqueue_after_commit=True`. | Realtime and Provider effects may occur before the transaction commits. Bulk/separate Email jobs may also start before the caller commits; ordinary queued Email is not immediate SMTP delivery. | Realtime messages cannot be retracted after publication; Provider behavior depends on the installed hook. Bulk Email may be sent by a worker even if the originating transaction later rolls back. | Document the behavior by mode and recipient path. Consider `frappe.publish_realtime(..., after_commit=True)` for transactional realtime updates; evaluate `enqueue_after_commit=True` for bulk Email queueing where transaction consistency is required. | Add rollback tests for standard and bulk Email, realtime after-commit publication, and provider side-effect contracts. |
| **QRY-001** | `Query Records` (Fetch Records) | Frappe v15 Query Builder lacks row-level permission enforcement. FlexiRule fails closed unless `ignore_permissions=1` is explicitly set with audit reason. | Enforces strict security by default; fails safe rather than leaking unauthorized data. | Users must provide an audit reason when querying with Query Builder on Frappe v15. | Document that Frappe v15 Fetch Records requires `ignore_permissions` with an audit reason. | Leverage Frappe v16 native QB permission hooks when available. |
| **ASN-001** | `Assignment` (Deep Document Paths) | Restricts `doc.*` mutations to root document fields (`len(parts) == 2`). Deep dotted paths throw `MethodExecutionError`. | Prevents unintended child-table corruption; child-table rows should be manipulated via `Loop` or `append` operator. | Assigning to `doc.child_table.field` directly is blocked. | Document that child-table row updates require Loop iteration. | Implement safe child-row indexing in v1.1. |

---

## Section H — Test Execution Record

**Evidence scope (2026-11-02)**: The counts below are the audit's recorded results for commit `504840d3bf3ec012a2c0ed5c7859bc7a7fd1b3c2`; no raw test logs or workflow artifacts for those runs were attached to this PR, so they are not independently reproduced here. The PR-head CI run `41458445864` completed the change-detection job but skipped the Frappe 15 server, Frappe 16 nested-set integration, and frontend jobs because this is a report-only change. The separate lint run `41458445971` passed its linter, dependency, and fast JavaScript-unit-test jobs. Therefore PR-head CI does **not** validate the claimed 720 backend or 33 frontend tests, and those historical counts do not establish test coverage on the PR base that is 39 commits newer.

All test suites were executed on the target environment against commit `504840d3bf3ec012a2c0ed5c7859bc7a7fd1b3c2`.

### H.1 Full Backend Test Suite
- **Command**: `bench --site test_site run-tests --app flexirule`
- **Tests Ran**: 720 tests
- **Result**: `OK (skipped=2)`
- **Duration**: 68.27s

### H.2 Focused Backend Test Modules
1. **Engine Core**: `flexirule.ruleflow.tests.test_engine` (5 tests) — `OK` (1.51s)
2. **Engine Comprehensive**: `flexirule.ruleflow.tests.test_engine_comprehensive` (24 tests) — `OK (skipped=2)` (5.69s)
3. **End-to-End Real Rules**: `flexirule.ruleflow.tests.test_real_rules` (14 tests) — `OK` (3.55s)
4. **Advanced Rule Flows**: `flexirule.ruleflow.tests.test_advanced_rule_flows` (5 tests) — `OK` (4.37s)
5. **Fetch Records Query Suite**: `flexirule.ruleflow.tests.test_fetch_records` (27 tests) — `OK` (1.75s)
6. **Query Records Refactor**: `flexirule.ruleflow.tests.test_query_records_refactor` (17 tests) — `OK` (3.76s)
7. **Query Report Serialization**: `flexirule.ruleflow.tests.test_query_report_serialization` (2 tests) — `OK` (0.01s)
8. **Sub-Rule Interface Contract**: `flexirule.ruleflow.tests.test_sub_rule_contract` (5 tests) — `OK` (0.01s)
9. **Process Runtime V2**: `flexirule.ruleflow.tests.test_process_runtime_v2` (5 tests) — `OK` (0.09s)
10. **Assignment Condition Guards**: `flexirule.ruleflow.tests.test_assignment_condition_guards` (21 tests) — `OK` (0.13s)
11. **Canonical Condition Evaluator**: `flexirule.ruleflow.tests.test_canonical_condition_evaluator` (34 tests) — `OK` (0.15s)
12. **Process Validation Operations**: `flexirule.ruleflow.process.validation.tests.test_validation` (2 tests) — `OK` (0.12s)

### H.3 Frontend Unit Test Suite
- **Command**: `yarn test:frontend`
- **Tests Ran**: 33 tests across 16 test files (filter leaf summary, query filter serializer, tree builder core, generic grid model, inline presentation policy, action config validation, config draft session, graph dirty state, stable serialization)
- **Result**: `pass: 33, fail: 0`
- **Duration**: 0.65s

---

## Section I — Final Release Recommendation

### **NOT A CURRENT RC1 SIGN-OFF**

#### Rationale & Outstanding Conditions:
1. **Snapshot limitation**: This matrix records an audit of commit `504840d3bf3ec012a2c0ed5c7859bc7a7fd1b3c2`. The PR base is 39 commits newer, so the totals and test run record must not be presented as a verification of the current PR base or a release candidate until the audit is repeated on the exact candidate SHA.
2. **Release-gate blocker (`REL-001`, tracked in #360)**: Loop and Switch are hardcoded as disabled in frontend validation, but the backend release-disabled set and DTO are empty. Keep both gated in the backend for RC1 and make the DTO/frontend consume the same canonical policy.
3. **Switch blocker (`SWT-001`)**: The runtime uses configured case targets plus `next_step_if_true` fallback, but the canvas maps Switch to `ProcessNode` with only a `default` source handle while `SwitchConfig` emits case-value handles. The recommended fix needs a dedicated Switch node with stable dynamic branch handles, a distinct default handle, corrected contract flags, and one shared backend adjacency model covering every graph-validation path.
4. **Switch test gap**: The cited comprehensive Switch runtime test is skipped, and the advanced-flow test only includes a Switch fixture for catalog coverage. Add and run real routing and graph-validation integration tests before marking Switch verified.
5. **Notification classification (`NOT-001`)**: Preserve the Frappe v15 distinction: standard Email is queued by default, but the bulk / separately queued path can enqueue before commit because `frappe.enqueue` defaults `enqueue_after_commit=False`; realtime publication also defaults to pre-commit, and Provider hooks are synchronous and app-defined. Test these paths independently and use `after_commit=True` for transaction-consistent realtime publication where appropriate.
6. **Operational limitation (`WIT-001`)**: Document that `time.sleep()` occupies the calling web or background worker; a background job does not make a long synchronous sleep non-blocking.
7. **Re-run evidence**: Run the backend and frontend suites on the exact release-candidate commit, retain machine-readable logs / artifacts, and re-audit the 43-operation matrix against that same source revision. Keep Frappe-version-specific Fetch Records permission constraints documented.

Until these conditions are satisfied, this report should be treated as an audit snapshot and issue register, not an RC1 readiness approval.
