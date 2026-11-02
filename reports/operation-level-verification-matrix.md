# FlexiRule Operation-Level Verification Matrix

## Section A — Executive Summary

- **Audit Date**: 2026-11-01 (Updated 2026-11-02 to align with RC1 tracking issues #358, #359, #360, #361, #368)
- **Repository**: `https://github.com/Sendipad/flexirule`
- **Target Branch**: `develop`
- **Audited Commit SHA**: `1f7bdb71fdd9328a2de40088869c42c1d9274dcb`
- **Audit Scope**: End-to-end multi-agent static and dynamic verification of all visual RuleFlow Action Types, individual operation options, process adapters, assignment operators, validation boundaries, permissions, transactions, and test coverage.
- **Action Types Discovered**: 13 Action Types (`Entry Action`, `Condition`, `Assignment`, `Query Records`, `Document Action`, `Process`, `Loop`, `Switch`, `Stop`, `Wait`, `Raise Error`, `Notify`, `Sub-Rule`).
- **Discovered Operations / Variants Assessed**: 49 total discrete operations across all action types (including 11 Query Records, 5 Document Action, 12 Process Operations across 4 Processes, 5 Notify modes, 2 Stop modes, 7 Assignment operators, Condition, Entry Action, Loop, Switch, Wait, Raise Error, and Sub-Rule).
- **Operation Assessment Counts**:
  - **PASS**: 39 operations
  - **PARTIAL**: 5 operations
  - **FAIL**: 0 operations
  - **UNVERIFIED**: 3 operations
  - **DISABLED**: 2 operations (`Switch`, `Loop` on builder UI gate)
  - **EXPERIMENTAL**: 0 operations
- **Confirmed P0/P1 Findings**:
  - **PRC-368 (Severity P0 — Release Blocker, Tracked in Issue #368)**: Process filesystem sync in `flexirule/ruleflow/core/process_sync.py` relies on a timestamp-only change detector (`_should_sync_existing_process()`) which can skip content updates when timestamps are stale, and needs deterministic change-aware reconciliation for RC1.
  - **TXN-001 (Severity P1 — High Priority, Tracked in Issue #359)**: Missing Savepoint Initialization in General `_execute_graph()` Action Execution Causes Uncoordinated Full Transaction Rollback on `on_error == "Rollback"`.
  - **REL-001 (Severity P1 — High Priority, Tracked in Issue #360)**: Release Gating Asymmetry Between Frontend Hardcoded Denylist (`variable_validator.js`) and Backend DTO / Server Enforcement (`contract_utils.py`, `validation_service.py`, `engine.py`).
- **Accepted Limitations / P2 Items**:
  - **QRY-001 (Severity P2 — Medium / Accepted v15 Limitation, Tracked in Issue #361)**: Frappe Query Builder Record-Level Permission Enforcement Asymmetry on Frappe v15 / v16 (`can_ignore_permissions` Fail-Closed Behavior).
- **RC1 Recommendation**: **READY AFTER LISTED BLOCKERS ARE CLOSED**. FlexiRule possesses robust, modern architecture across its core actions, declarative Process V2 contract, and unified ValueResolver. However, before declaring RC1, the Process synchronization change detector (PRC-368 / #368) must be made deterministic, the savepoint lifecycle in `engine.py` (TXN-001 / #359) must be normalized, and the release-gating contract between frontend and backend DTOs/validators (REL-001 / #360) must be unified.

---

## Section B — Authoritative Catalog

The following authoritative inventory was discovered directly from repository source code (`flexirule/ruleflow/core/action_handlers/`, `flexirule/ruleflow/core/contract_utils.py`, `flexirule/ruleflow/core/contract_dto.py`, and `flexirule/public/js/flexirule/core/contracts.js`).

| Action Type | Operation / Variant | Category | UI Status | Backend Contract Status | Validation Status | Runtime Handler | Test Coverage Status | Assigned Investigator |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Entry Action** | Entry Action | Control Flow | Available | Active | Pass | `EntryActionHandler` | PASS | Agent 1 |
| **Condition** | Condition | Control Flow | Available | Active | Pass | `ConditionHandler` | PASS | Agent 1 |
| **Switch** | Switch | Control Flow | Gated / Hidden | Registered | Partial | `SwitchHandler` | DISABLED | Agent 1 |
| **Loop** | Loop | Control Flow | Gated / Hidden | Registered | Pass | `LoopHandler` | DISABLED | Agent 1 |
| **Stop** | Success | Control Flow | Available | Active | Pass | `StopHandler` | PASS | Agent 1 |
| **Stop** | Error | Control Flow | Available | Active | Pass | `StopHandler` | PASS | Agent 1 |
| **Raise Error** | Raise Error | Control Flow | Available | Active | Pass | `RaiseErrorHandler` | PASS | Agent 1 |
| **Wait** | Wait | Control Flow | Available | Active | Pass | `WaitHandler` | PARTIAL | Agent 6 |
| **Sub-Rule** | Sub-Rule | Control Flow | Available | Active | Pass | `SubRuleHandler` | PASS | Agent 6 |
| **Assignment** | `set` | Data Actions | Available | Active | Pass | `AssignmentHandler` | PASS | Agent 2 |
| **Assignment** | `clear` | Data Actions | Available | Active | Pass | `AssignmentHandler` | PASS | Agent 2 |
| **Assignment** | `increment` | Data Actions | Available | Active | Pass | `AssignmentHandler` | PASS | Agent 2 |
| **Assignment** | `decrement` | Data Actions | Available | Active | Pass | `AssignmentHandler` | PASS | Agent 2 |
| **Assignment** | `append` | Data Actions | Available | Active | Pass | `AssignmentHandler` | PASS | Agent 2 |
| **Assignment** | `merge` | Data Actions | Available | Active | Pass | `AssignmentHandler` | PASS | Agent 2 |
| **Assignment** | `toggle` | Data Actions | Available | Active | Pass | `AssignmentHandler` | PASS | Agent 2 |
| **Query Records** | Fetch Records | Data Actions | Available | Active | Pass | `QueryRecordsHandler` | PASS | Agent 3 |
| **Query Records** | Query List | Data Actions | Available | Active | Pass | `QueryRecordsHandler` | PASS | Agent 3 |
| **Query Records** | Query Doc | Data Actions | Available | Active | Pass | `QueryRecordsHandler` | PASS | Agent 3 |
| **Query Records** | Exist Record | Data Actions | Available | Active | Pass | `QueryRecordsHandler` | PASS | Agent 3 |
| **Query Records** | Query Report | Data Actions | Available | Active | Pass | `QueryRecordsHandler` | PASS | Agent 3 |
| **Query Records** | Count | Data Actions | Available | Active | Pass | `QueryRecordsHandler` | PASS | Agent 3 |
| **Query Records** | Sum | Data Actions | Available | Active | Pass | `QueryRecordsHandler` | PASS | Agent 3 |
| **Query Records** | Average | Data Actions | Available | Active | Pass | `QueryRecordsHandler` | PASS | Agent 3 |
| **Query Records** | Min | Data Actions | Available | Active | Pass | `QueryRecordsHandler` | PASS | Agent 3 |
| **Query Records** | Max | Data Actions | Available | Active | Pass | `QueryRecordsHandler` | PASS | Agent 3 |
| **Query Records** | Group By | Data Actions | Available | Active | Pass | `QueryRecordsHandler` | PASS | Agent 3 |
| **Document Action** | Create New | Data Actions | Available | Active | Pass | `DocumentActionHandler` | PASS | Agent 4 |
| **Document Action** | Update Existing | Data Actions | Available | Active | Pass | `DocumentActionHandler` | PASS | Agent 4 |
| **Document Action** | Delete Record | Data Actions | Available | Active | Pass | `DocumentActionHandler` | PASS | Agent 4 |
| **Document Action** | Create ToDo | Data Actions | Available | Active | Pass | `DocumentActionHandler` | PASS | Agent 4 |
| **Document Action** | Add Comment | Data Actions | Available | Active | Pass | `DocumentActionHandler` | PASS | Agent 4 |
| **Notify** | Toast | Communication | Available | Active | Pass | `NotifyHandler` | PASS | Agent 6 |
| **Notify** | System | Communication | Available | Active | Pass | `NotifyHandler` | PASS | Agent 6 |
| **Notify** | Email | Communication | Available | Active | Pass | `NotifyHandler` | PASS | Agent 6 |
| **Notify** | System Notification | Communication | Available | Active | Pass | `NotifyHandler` | PASS | Agent 6 |
| **Notify** | Provider | Communication | Available | Active | Pass | `NotifyHandler` | PARTIAL | Agent 6 |
| **Process (Validation)** | `value_in_range` | Processes | Available | Active (V2) | Pass | `ProcessHandler` | PASS | Agent 5 |
| **Process (Validation)** | `conditional_required` | Processes | Available | Active (V2) | Pass | `ProcessHandler` | PASS | Agent 5 |
| **Process (Validation)** | `child_table_rows` | Processes | Available | Active (V2) | Pass | `ProcessHandler` | PASS | Agent 5 |
| **Process (Validation)** | `composite_uniqueness` | Processes | Available | Active (V2) | Pass | `ProcessHandler` | PASS | Agent 5 |
| **Process (Validation)** | `role_check` | Processes | Available | Active (V2) | Pass | `ProcessHandler` | PASS | Agent 5 |
| **Process (Validation)** | `on_field_change` | Processes | Available | Active (V2) | Pass | `ProcessHandler` | PASS | Agent 5 |
| **Process (Dedupe)** | `find_duplicates_in_child_table` | Processes | Available | Active (V2) | Pass | `ProcessHandler` | PARTIAL | Agent 5 |
| **Process (Dedupe)** | `find_matching_records` | Processes | Available | Active (V2) | Pass | `ProcessHandler` | PARTIAL | Agent 5 |
| **Process (Enrichment)** | `calculate_value` | Processes | Available | Active (V2) | Pass | `ProcessHandler` | PARTIAL | Agent 5 |
| **Process (Enrichment)** | `linked_doc_autocomplete` | Processes | Available | Active (V2) | Pass | `ProcessHandler` | UNVERIFIED | Agent 5 |
| **Process (Enrichment)** | `copy_from_template` | Processes | Available | Active (V2) | Pass | `ProcessHandler` | UNVERIFIED | Agent 5 |
| **Process (Batch)** | `execute_for_documents` | Processes | Available | Active (V2) | Pass | `ProcessHandler` | UNVERIFIED | Agent 5 |

---

## Section C — Operation-Level Verification Matrix

*Scoring Rule*: Overall Status reflects end-to-end release readiness. An operation is marked `PASS` when its core runtime implementation, contracts, validation, security boundaries, and adequate tests are verified. When test coverage does not exercise advanced branch options or complex fuzzy heuristics, the Tests dimension is marked `PARTIAL`, resulting in an overall status of `PARTIAL`. For `Document Action`, runtime execution and document validation pass, while the ambient transaction rollback behavior under `on_error == 'Rollback'` is affected by TXN-001.

| Action Type | Operation | UI / Contract | Runtime | Validation | Security | Error / Txn Behavior | Tests | Overall Status | Finding IDs |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Entry Action** | Start Node | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Condition** | Evaluate Python Expression | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Switch** | Dynamic Case Routing | PARTIAL | PARTIAL | PARTIAL | PASS | PARTIAL | UNVERIFIED | **DISABLED** | REL-001 |
| **Loop** | Iterate Collection | PARTIAL | PASS | PASS | PASS | PARTIAL | PARTIAL | **DISABLED** | REL-001 |
| **Stop** | Success | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Stop** | Error | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Raise Error** | Raise Error | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Wait** | Sleep / Delay | PASS | PASS | PASS | PASS | PARTIAL | UNVERIFIED | **PARTIAL** | WAI-001 |
| **Sub-Rule** | Sub-Rule Call | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Assignment** | `set` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Assignment** | `clear` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Assignment** | `increment` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Assignment** | `decrement` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Assignment** | `append` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Assignment** | `merge` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Assignment** | `toggle` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Query Records** | Fetch Records | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | QRY-001 |
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
| **Document Action** | Create New | PASS | PASS | PASS | PASS | PARTIAL | PASS | **PASS** | TXN-001 |
| **Document Action** | Update Existing | PASS | PASS | PASS | PASS | PARTIAL | PASS | **PASS** | TXN-001 |
| **Document Action** | Delete Record | PASS | PASS | PASS | PASS | PARTIAL | PASS | **PASS** | TXN-001 |
| **Document Action** | Create ToDo | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Document Action** | Add Comment | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Notify** | Toast | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Notify** | System | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Notify** | Email | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Notify** | System Notification | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Notify** | Provider | PARTIAL | PARTIAL | PASS | PASS | PASS | UNVERIFIED | **PARTIAL** | NTF-001 |
| **Process (Validation)** | `value_in_range` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process (Validation)** | `conditional_required` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process (Validation)** | `child_table_rows` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process (Validation)** | `composite_uniqueness` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process (Validation)** | `role_check` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process (Validation)** | `on_field_change` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Process (Dedupe)** | `find_duplicates_in_child_table` | PASS | PASS | PASS | PASS | PASS | PARTIAL | **PARTIAL** | — |
| **Process (Dedupe)** | `find_matching_records` | PASS | PASS | PASS | PASS | PASS | PARTIAL | **PARTIAL** | — |
| **Process (Enrichment)** | `calculate_value` | PASS | PASS | PASS | PASS | PASS | PARTIAL | **PARTIAL** | — |
| **Process (Enrichment)** | `linked_doc_autocomplete` | PARTIAL | PARTIAL | PASS | PASS | PASS | UNVERIFIED | **UNVERIFIED** | PRC-001 |
| **Process (Enrichment)** | `copy_from_template` | PARTIAL | PARTIAL | PASS | PASS | PASS | UNVERIFIED | **UNVERIFIED** | PRC-001 |
| **Process (Batch)** | `execute_for_documents` | PARTIAL | PARTIAL | PASS | PASS | PASS | UNVERIFIED | **UNVERIFIED** | PRC-002 |

---

## Section D — Operation Details

### D.1 Entry Action
- **Contract**: Starting node of rule graph. No inputs required; consumes no variables; returns `None`; directs traversal to `action.next_step_if_true`.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/simple_actions.py` (`EntryActionHandler.execute`), invoked by `RuleEngine._execute_graph()` via `HandlerRegistry`.
- **Validation**: Automatically verified as initial node; no configuration payload required.
- **Security**: No database mutations, permission checks or side effects.
- **Failure Behavior**: Deterministic traversal; no failure mode.
- **Tests**: `flexirule/ruleflow/tests/test_advanced_rule_flows.py` (`test_suite_fixtures_cover_all_current_action_types`).
- **Status & Rationale**: **PASS**. Implementation is minimal, verified, and safe.
- **Open Gaps**: None.

### D.2 Condition
- **Contract**: Evaluates a compiled Python boolean condition against execution context (`doc`, `vars`, `old_doc`, `frappe`). Traverses `next_step_if_true` on truthy, `next_step_if_false` on falsy.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/condition.py` (`ConditionHandler.execute`), delegating to `engine._evaluate_python_condition()`.
- **Validation**: Frontend `validate_condition`; backend requires `compiled_expression` when condition config is present (enforced during `Rule.validate()`).
- **Security**: Evaluated inside `frappe.safe_eval` with safe locals (`doc`, `old_doc`, `vars`, `add_days`, `nowdate`, `getdate`, `SafeFrappeAPI`).
- **Failure Behavior**: Syntax or runtime errors in expression raise `ValidationError` and halt traversal.
- **Tests**: `flexirule/ruleflow/tests/test_evaluator.py`, `flexirule/ruleflow/tests/test_action_return_schema_contract.py`.
- **Status & Rationale**: **PASS**. Condition compilation and safe runtime evaluation are fully tested and functional.
- **Open Gaps**: None.

### D.3 Switch
- **Contract**: Multi-way branching based on evaluated expression (`config.expression`). Evaluates value, compares against `config.cases` dict mapping case values to target `action_id`. Falls back to `next_step_if_true`.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/switch.py` (`SwitchHandler.execute`).
- **Validation**: Incomplete backend validation schema. Vue component `SwitchConfig.vue` manages cases and edges, but the action is disabled in builder UI denylist.
- **Security**: Expression evaluated with `engine._evaluate_python_value` (`frappe.safe_eval`).
- **Failure Behavior**: Falls back to `next_step_if_true` if unconfigured or unmatched.
- **Tests**: `flexirule/ruleflow/tests/test_engine_comprehensive.py` (`test_engine_execute_switch_action` marked skipped: `"Switch action is disabled for the v0.1 release surface"`).
- **Status & Rationale**: **DISABLED**. Gated in frontend `variable_validator.js`. As documented in Finding REL-001, backend contract DTO and server-side checks need to be synchronized so it remains strictly disabled until multi-handle visual graph routing is formalized.
- **Open Gaps**: Edge serialization and UI routing for arbitrary case branches.

### D.4 Loop
- **Contract**: Iterates over a collection resolved from `config.iterator`. Advances iteration state stored in `context['vars']['_loops'][action_id]`. Sets current item in `vars[action.return_variable]` and loop metadata in `vars['loop']`. Returns `(True, next_step_if_true)` while items remain; returns `(False, next_step_if_false)` when exhausted.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/loop.py` (`LoopHandler.execute`).
- **Validation**: Validated in `flexirule/ruleflow/core/validation_service.py` (`_validate_flow_constraints`) ensuring body path returns to the loop head and separate false path exists.
- **Security**: Resolves iterator using `frappe.safe_eval`. Enforces engine cycle protection (`max_visits_per_node = 1000`).
- **Failure Behavior**: Non-iterable inputs log a warning and exit cleanly through false path.
- **Tests**: `flexirule/ruleflow/tests/test_loop_flow_constraints.py` (9 tests passed), `test_engine_comprehensive.py` (skipped in comprehensive suite due to release gate).
- **Status & Rationale**: **DISABLED**. Handlers and graph constraint validations are fully implemented, but Loop is gated off in `variable_validator.js`.
- **Open Gaps**: UI integration for visual loop grouping and clean cycle detection boundaries.

### D.5 Stop (Success & Error Modes)
- **Contract**:
  - `Success`: Terminates rule execution immediately without raising exceptions. Returns `(None, None)`.
  - `Error`: Renders Jinja `value_template` with context and raises `frappe.throw(message)` to abort transaction.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/simple_actions.py` (`StopHandler.execute`).
- **Validation**: `Error` mode requires `value_template`.
- **Security**: Template rendered using `SafeFrappeAPI` in context; prevents arbitrary write operations.
- **Failure Behavior**: Terminal node; stops graph execution loop in `RuleEngine`.
- **Tests**: `flexirule/ruleflow/tests/test_advanced_rule_flows.py`, `flexirule/ruleflow/tests/test_action_return_schema_contract.py`.
- **Status & Rationale**: **PASS**. Behavior is well-isolated, tested, and reliable.
- **Open Gaps**: None.

### D.6 Raise Error
- **Contract**: Aborts rule execution immediately by throwing `frappe.ValidationError`. Supports configurable error code, title, and Jinja `value_template`.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/simple_actions.py` (`RaiseErrorHandler.execute`).
- **Validation**: Backend operation contract enforces mandatory `value_template`.
- **Security**: Template rendered via `SafeFrappeAPI`.
- **Failure Behavior**: Throws exception immediately; triggers Frappe transaction rollback unless trapped by parent coordinator.
- **Tests**: `flexirule/ruleflow/tests/test_advanced_rule_flows.py` (`test_callable_raise_error_rule_fails_and_persists_log`).
- **Status & Rationale**: **PASS**. Fully operational and verified.
- **Open Gaps**: None.

### D.7 Wait
- **Contract**: Pauses execution synchronously using `time.sleep(duration)` where duration is derived from `config.duration` or `action.timeout`.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/simple_actions.py` (`WaitHandler.execute`).
- **Validation**: Configurable in `WaitConfig.vue`; duration parsed as numeric seconds.
- **Security**: Safe synchronous delay.
- **Failure Behavior**: Synchronous blocking.
- **Tests**: Not covered by automated backend tests in suite.
- **Status & Rationale**: **PARTIAL**. Operates via Python `time.sleep()`, which holds the Frappe worker thread synchronously. For RC1, this blocking behavior is an accepted limitation (documented in Section G / Finding WAI-001) until durable Redis/scheduler-based waiting is designed.
- **Open Gaps**: No durable background delay mechanism.

### D.8 Sub-Rule
- **Contract**: Executes another active `Callable Event` Rule as an isolated subroutine. Passes input mapping to child `vars`; executes via nested `RuleEngine`; returns output mapping or namespaced result to parent `vars`. Enforces `MAX_SUB_RULE_DEPTH = 10` and cross-rule cycle detection.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/sub_rule.py` (`SubRuleHandler.execute`).
- **Validation**: Enforces target rule must be active, exposed as subrule, and callable.
- **Security**: Uses `SubRuleVarsOverlay` for memory isolation; checks permission bypass flags with `can_ignore_permissions`.
- **Failure Behavior**: Exceptions in child rule propagate to parent unless handled.
- **Tests**: `flexirule/ruleflow/tests/test_sub_rule_contract.py` (5 tests passed), `test_advanced_rule_flows.py` (`test_contact_insert_runs_multi_rule_chain_with_nested_subrules`).
- **Status & Rationale**: **PASS**. Sub-rule recursion, cycle prevention, and context scoping are thoroughly verified.
- **Open Gaps**: None.

### D.9 Assignment (7 Operators: Set, Clear, Increment, Decrement, Append, Merge, Toggle)
- **Contract**: Sequential batch state mutations on target paths starting with `doc.` or `vars.`. Supported operators:
  - `set`: Replaces target value with evaluated operand.
  - `clear`: Resets target to type-appropriate empty value (`[]`, `{}`, `""`, `None`).
  - `increment`: Adds numeric operand to current value.
  - `decrement`: Subtracts numeric operand from current value.
  - `append`: Appends item to list (allocating new list to ensure change detection).
  - `merge`: Deep-merges dictionary operand into target dict.
  - `toggle`: Inverts boolean / checkbox values.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/assignment.py` (`AssignmentHandler.execute`), `flexirule/ruleflow/core/operators.py` (`AssignmentOperatorRegistry`).
- **Validation**: Restricts target paths (`_validate_target_path` blocks `meta.`, `frappe.`, `rule.`, `caller.`). Blocks `doc.*` mutations during after-save events (`AFTER_EVENT_MUTATION_BLOCKLIST`).
- **Security**: Operands resolved through compiled `ValueResolver` with strict type bounds.
- **Failure Behavior**: Target validation errors raise `MethodExecutionError`.
- **Tests**: `flexirule/ruleflow/tests/test_assignment_resolver.py` (12 tests passed), `test_advanced_rule_flows.py`.
- **Status & Rationale**: **PASS**. All 7 operators and row-level `when_expression` guards function with high fidelity.
- **Open Gaps**: None.

### D.10 Query Records (11 Operations)
- **Shared Architecture**: `flexirule/ruleflow/core/action_handlers/query_records.py` (`QueryRecordsHandler`). Dispatches via `mode_handlers` dictionary based on `action.operation`. Supports permission checking via `can_ignore_permissions(action, context)`.
- **D.10.1 Fetch Records**:
  - *Contract*: Queries records using Frappe Query Builder (`frappe.qb.get_query`). Supports canonical filter trees, literal columns, nested set hierarchies, sorting, pagination.
  - *Execution Path*: `QueryRecordsHandler._fetch_records` -> `frappe_query_compat.execute_query`.
  - *Security & Permissions*: On Frappe v15, Query Builder lacks native record permission enforcement; system enforces fail-closed behavior unless `ignore_permissions` is audited (`can_ignore_permissions`).
  - *Status*: **PASS** (with documented Frappe v15 permission behavior QRY-001).
- **D.10.2 Query List**:
  - *Contract*: Uses `frappe.get_list` to return a list of dictionaries with standard Frappe permission checks and child joins.
  - *Status*: **PASS**.
- **D.10.3 Query Doc**:
  - *Contract*: Fetches single document via `frappe.get_doc` or `frappe.get_cached_doc` (supports Single DocTypes and Latest Doc strategies). Enforces `doc.check_permission("read")`.
  - *Status*: **PASS**.
- **D.10.4 Exist Record**:
  - *Contract*: Returns boolean existence check via `frappe.get_list` with `limit_page_length=1`.
  - *Status*: **PASS**.
- **D.10.5 Query Report**:
  - *Contract*: Executes Frappe script or query reports via `frappe.desk.query_report.run()`. Normalizes filter parameters for SQL binding.
  - *Status*: **PASS**.
- **D.10.6-D.10.10 Aggregations (Count, Sum, Average, Min, Max)**:
  - *Contract*: Executes SQL aggregations (`count`, `sum`, `avg`, `min`, `max`) over target fields with full permission awareness via `frappe.get_list`.
  - *Status*: **PASS**.
- **D.10.11 Group By**:
  - *Contract*: Executes group-by aggregations and returns rows of `{group_field, value}` tuples via `frappe.get_list`.
  - *Status*: **PASS**.

### D.11 Document Action (5 Operations)
- **Shared Architecture**: `flexirule/ruleflow/core/action_handlers/document_action.py` (`DocumentActionHandler`).
- **D.11.1 Create New**:
  - *Contract*: Creates and inserts a new document (`frappe.get_doc(doc_data).insert()`). Supports scalar field mappings, child table mappings (`_apply_table_mappings`), and async queueing.
  - *Status*: **PASS**.
- **D.11.2 Update Existing**:
  - *Contract*: Loads existing doc (`frappe.get_doc(reference_doctype, docname)`), checks `doc.check_permission("write")`, applies scalar and table mappings, and saves.
  - *Status*: **PASS**.
- **D.11.3 Delete Record**:
  - *Contract*: Deletes target document via `frappe.delete_doc` after checking `frappe.has_permission(reference_doctype, "delete")`.
  - *Status*: **PASS**.
- **D.11.4 Create ToDo**:
  - *Contract*: Creates a linked `ToDo` document for context doc with rendered `assigned_to`, `description`, and `priority`.
  - *Status*: **PASS**.
- **D.11.5 Add Comment**:
  - *Contract*: Creates a `Comment` document on the current context document timeline.
  - *Status*: **PASS**.

### D.12 Process (12 Operations across 4 Standard Processes)
- **Architecture**: Declarative Process Contract V2 (`flexirule/ruleflow/core/process_runtime_v2.py`, `ProcessOperationExecutor`). Enforces JSON Schema validation for config and result schemas, capability checks (`requires_doc`, `allows_async`, `writes_to`), and mutation intents.
- **D.12.1-D.12.6 Validation Process (`validate` adapter)**:
  - Operations: `value_in_range`, `conditional_required`, `child_table_rows`, `composite_uniqueness`, `role_check`, `on_field_change`.
  - Tested: All 6 operations verified against declarative schemas and return policies.
  - Status: **PASS**.
- **D.12.7-D.12.8 Deduplication Process (`dedupe` adapter)**:
  - Operations: `find_duplicates_in_child_table`, `find_matching_records`.
  - Status: **PARTIAL** (Core matching logic works; complex fuzzy thresholds and edge cases require additional integration test suites).
- **D.12.9-D.12.11 Enrichment Process (`lookup` adapter)**:
  - Operations: `calculate_value` (**PARTIAL**), `linked_doc_autocomplete` (**UNVERIFIED** / PRC-001), `copy_from_template` (**UNVERIFIED** / PRC-001).
- **D.12.12 Batch Process (`batch` adapter)**:
  - Operation: `execute_for_documents` (**UNVERIFIED** / PRC-002). Requires background worker queue verification.

### D.13 Notify (5 Operations)
- **Shared Architecture**: `flexirule/ruleflow/core/action_handlers/simple_actions.py` (`NotifyHandler`).
- **Toast**: `frappe.msgprint(message, alert=True)`. Status: **PASS**.
- **System**: `frappe.publish_realtime("msgprint", ...)`. Status: **PASS**.
- **Email**: `frappe.sendmail(...)` with recipients, subject, and optional PDF attachment. Status: **PASS**.
- **System Notification**: Creates `Notification Log` document row. Status: **PASS**.
- **Provider**: Hook-based dispatch (`flexirule_notification_providers`). Status: **PARTIAL** (hook registration mechanism exists; third-party provider adapters unverified, documented under NTF-001).

---

## Section E — Cross-Operation Integration Matrix

| Scenario | Description & Setup | Expected Behavior | Actual Verification Status | Relevant Test Files | Defects / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Entry → Assignment → Condition → Stop** | Flow starts at Entry, mutates `vars.status = "Approved"`, evaluates `vars.status == "Approved"` as True, reaches Stop (Success). | Execution succeeds cleanly; context carries updated variable. | **PASS** | `test_engine_complex_flows.py`, `test_advanced_rule_flows.py` | None. |
| **2. Entry → Condition → True/False Branches** | Condition branches on `doc.docstatus == 1`. True branch triggers Process; False branch triggers Notification. | Clean branching without traversing unselected branch. | **PASS** | `test_condition_benchmark.py`, `test_evaluator.py` | None. |
| **3. Entry → Loop → Assignment → Next Iteration** | Iterates over items list, mutates running total `vars.total += item.amount`, exits via false branch when done. | All items processed sequentially; loop state cleaned up on exit. | **PARTIAL** | `test_loop_flow_constraints.py` | Graph path validation passes; action node gated on UI. |
| **4. Query Records → Context Variable → Condition** | `Fetch Records` or `Count` queries open Orders, sets `vars.order_count`, followed by Condition `vars.order_count > 0`. | Result smoothly populated into `vars` and accessible to Condition. | **PASS** | `test_fetch_records.py`, `test_query_records_canonical_filters.py` | None. |
| **5. Assignment → Document Action** | `Assignment` computes field values into `vars.target_data`, `Document Action (Create New)` uses them in `field_mappings`. | New document created with correctly resolved dynamic values. | **PASS** | `test_advanced_rule_flows.py` (`test_contact_insert_...`) | None. |
| **6. Process → Result Variable → Subsequent Action** | `Process (Validation.value_in_range)` returns boolean result, stored in `vars.is_valid`, followed by Condition checking result. | Result schema enforced; result correctly passed downstream. | **PASS** | `test_process_contract_v2.py`, `test_process_runtime_v2.py` | None. |
| **7. Parent Rule → Sub-Rule → Return to Parent** | Parent rule calls Sub-Rule; Sub-Rule executes in isolated overlay; mutations exported back to parent namespace. | No variable leak; execution stack tracks recursion depth; cycle detection active. | **PASS** | `test_sub_rule_contract.py`, `test_advanced_rule_flows.py` | None. |
| **8. Action Failure → Configured Error Policy** | Action throws exception with `on_error == "Continue"` vs `on_error == "Stop"`. | "Continue" logs warning and advances to `next_step_if_true`; "Stop" halts execution. | **PASS** | `test_engine.py`, `test_advanced_rule_flows.py` | None. |
| **9. Document Action Failure → Transaction / Rollback** | Action fails with `on_error == "Rollback"`. | Database state rolled back to pre-action savepoint. | **PARTIAL** (Defect Found) | `test_engine.py` | **TXN-001**: Savepoint not created before general action execution. |
| **10. Notify / External Side Effect → Subsequent Failure** | Email notification sent, followed by terminal `Raise Error`. | Email sent (cannot be undone by DB rollback); exception aborts DB changes. | **PASS** (Documented) | `test_advanced_rule_flows.py` (`test_callable_raise_error_...`) | External side effects cannot be reversed by database rollback (Section G limitation). |

---

## Section F — RC1 Release Blockers

### Finding PRC-368 (Tracked in Issue #368)
- **Affected Operation**: Process Filesystem Synchronization (`bench migrate` / `after_migrate`)
- **Severity**: P0 (Release Blocker — Tracked in Issue #368)
- **Source Location**: `flexirule/ruleflow/core/process_sync.py` (specifically `_should_sync_existing_process` lines 30–45, and `sync_processes` lines 50–90)
- **Evidence**:
  In `process_sync.py`, stale operation pruning and standard Process deletion exist (`_prune_missing_standard_processes`). However, the existing process update gate relies strictly on comparing timestamps via `_should_sync_existing_process()`:
  ```python
  def _should_sync_existing_process(doc, source_modified) -> bool:
      if not source_modified:
          return True
      return get_datetime(source_modified) > get_datetime(doc.modified)
  ```
  If a file-backed Process definition is modified without updating its embedded `modified` timestamp (or if git checkout leaves the file mtime older than the database record), `bench migrate` skips importing the modified operations and schema overrides. Furthermore, missing test coverage for non-standard process isolation and idempotent multi-app sync prevents verifying change-aware reconciliation.
- **User / Business Impact**: Updates to standard Process operations in new releases or app updates may not synchronize to the database during migration.
- **Recommended Correction**: Adopt Frappe-aligned sync principles: compute a deterministic definition hash (or migration hash) over the Process and its child operations. Only skip sync when the hash matches. Ensure custom Processes remain strictly protected from pruning.
- **Test Required**: Add migration sync tests verifying that content modifications with identical timestamps still trigger an update, and that running sync twice produces zero DB writes.
- **RC1 Disposition**: **Must be resolved before RC1 (P0 Prerequisite)**.

---

### Finding TXN-001 (Tracked in Issue #359)
- **Affected Operation**: RuleEngine graph traversal / all actions configuring `on_error == "Rollback"`
- **Severity**: P1 (High Priority — Tracked in Issue #359)
- **Source Location**: `flexirule/ruleflow/core/engine.py` (lines 530–565, 650–670)
- **Evidence**:
  In `RuleEngine._execute_graph()`, line 653:
  ```python
  elif current.on_error == "Rollback":
      savepoint_name = f"flexirule_action_{current.action_id or current.name}"
      self._log("ERROR", _("Error in action {0}, rolling back to savepoint: {1}").format(current.action_label, str(e)))
      try:
          frappe.db.rollback(save_point=savepoint_name)
      except Exception as rollback_err:
          frappe.db.rollback()
  ```
  However, unlike `_call_process_with_retry` (which explicitly creates `frappe.db.savepoint(savepoint_name)` before calling the process), the general execution loop in `_execute_graph()` does **not** invoke `frappe.db.savepoint(savepoint_name)` prior to executing `handler.execute()`. When an exception occurs and rollback is requested, the savepoint does not exist in MariaDB/PostgreSQL, causing an inner `DatabaseError` which triggers the fallback `frappe.db.rollback()`. This unexpectedly rolls back the entire database transaction instead of just the failed action.
- **User / Business Impact**: Rules using `on_error: Rollback` cannot perform fine-grained step rollbacks; they inadvertently abort all earlier database operations in the transaction.
- **Recommended Correction**: In `_execute_graph()`, before executing `handler.execute()`, check if `getattr(current, "on_error", None) == "Rollback"`. If so, create `frappe.db.savepoint(savepoint_name)` inside a try-finally block and release it (`frappe.db.release_savepoint(savepoint_name)`) on successful completion.
- **Test Required**: Add a regression test executing an action with `on_error: "Rollback"` that fails, asserting that prior database writes survive while writes made by the failed action are reverted.
- **RC1 Disposition**: **Must be resolved before RC1**.

---

### Finding REL-001 (Tracked in Issue #360)
- **Affected Operation**: `Loop`, `Switch` Action Types
- **Severity**: P1 (High Priority — Tracked in Issue #360)
- **Source Location**:
  - Backend Contract Utility: `flexirule/ruleflow/core/contract_utils.py` (line 64: `RELEASE_DISABLED_ACTION_TYPES: set[str] = set()`)
  - Server-Side Validation: `flexirule/ruleflow/core/validation_service.py` (lines 37, 98, 211: calls `is_release_disabled_action(action_type)`)
  - Runtime Engine Enforcement: `flexirule/ruleflow/core/engine.py` (lines 31, 423: calls `is_release_disabled_action(a.action_type)`)
  - Contract DTO Serialization: `flexirule/ruleflow/core/contract_dto.py` (line 64: `"release_disabled_action_types": sorted(list(RELEASE_DISABLED_ACTION_TYPES))`)
  - Frontend Fallback & DTO Consumption: `flexirule/public/js/flexirule/utils/variable_validator.js` (line 23), `flexirule/public/js/flexirule/core/contracts.js` (lines 53, 110, 1193)
- **Evidence**:
  `variable_validator.js` defines a client-side hardcoded set:
  ```javascript
  const RELEASE_DISABLED_ACTION_TYPES = new Set(["Loop", "Switch"]);
  ```
  However, backend `contract_utils.py` defines:
  ```python
  RELEASE_DISABLED_ACTION_TYPES: set[str] = set()
  ```
  Because the backend set is empty, `is_release_disabled_action()` returns `False` on the server. When `validation_service.py` validates a rule at save time or activation time, and when `engine.py` validates disabled action nodes before running, neither rejects `Loop` or `Switch`. Furthermore, when `contracts.js` hydrates from backend DTO (`RELEASE_DISABLED_ACTION_TYPES = new Set(dto.release_disabled_action_types)`), it overwrites the frontend set with an empty set. This creates an architectural divergence where the server fails to gate off incomplete or unrouted actions.
- **User / Business Impact**: Inconsistent UI availability and validation behavior between cached sessions, direct API invocations, and desk navigation.
- **Recommended Correction**: Synchronize `RELEASE_DISABLED_ACTION_TYPES` in `contract_utils.py` to include `{"Loop", "Switch"}` as the single canonical source of truth for the RC1 release surface.
- **Test Required**: Backend test ensuring `get_contract_dto()["release_disabled_action_types"]` returns `['Loop', 'Switch']` and server validation rejects them.
- **RC1 Disposition**: **Must be resolved before RC1**.

---

## Section G — Accepted Limitations and Deferrals

1. **Frappe v15 Query Builder Permission Fail-Closed Behavior (QRY-001 / Tracked in Issue #361)**:
   - *Severity*: P2 (Accepted Frappe v15 Limitation)
   - *Source Location*: `flexirule/ruleflow/utils/frappe_query_compat.py` (lines 200–225)
   - *Current Behavior*: Frappe v15's `frappe.database.query.Engine.get_query()` does not support the `ignore_permissions` argument, whereas Frappe v16 natively exposes it. FlexiRule detects this capability: on v16 it passes the permission flag natively; on v15 it intentionally fails closed unless the audited bypass (`can_ignore_permissions`) is configured.
   - *RC1 Disposition*: This is an intentional security design choice, not a defect. It must not be bypassed by falling back to `frappe.get_list`, because Query Builder and `get_list` differ in aggregation, joins, and filter syntax. Documented for RC1; users desiring permission-enforced queries on v15 use `Query List`.

2. **Synchronous Sleep in Wait Action (WAI-001)**:
   - *Severity*: P3 (Accepted Limitation)
   - *Current Behavior*: `WaitHandler.execute()` uses Python `time.sleep()`, which synchronously blocks the gunicorn/bench worker.
   - *RC1 Justification*: Acceptable for micro-delays (< 5s) in synchronous hooks. Long delays should be documented as discouraged.
   - *Recommendation for Post-RC1*: Implement a durable async pause/resume mechanism using Frappe scheduler and background jobs.

3. **External Side Effects Persistence on Rollback (SE-001)**:
   - *Severity*: P3 (Accepted Limitation)
   - *Current Behavior*: Actions that produce external side effects (e.g. sending real emails via `Notify`, calling external webhook providers) cannot be rolled back if a subsequent action in the rule fails.
   - *RC1 Justification*: Standard across distributed automation platforms.

4. **Third-Party Notification Providers (NTF-001)**:
   - *Severity*: P3 (Accepted Limitation / Unverified Provider Adapters)
   - *Current Behavior*: `NotifyHandler` supports a `Provider` mode dispatched via Frappe hook `flexirule_notification_providers`. Core hook dispatch logic is present, but third-party external provider packages are external integrations unverified in core.
   - *RC1 Disposition*: Defer third-party provider certifications to post-RC1.

5. **Unverified Advanced Process Operations (PRC-001, PRC-002)**:
   - *Severity*: P3 (Accepted Limitation / Deferred to Full Test Harness)
   - *Current Behavior*: Enrichment operations `linked_doc_autocomplete` and `copy_from_template` (PRC-001) and Batch operation `execute_for_documents` (PRC-002) have valid V2 declarative contracts but lack end-to-end integration test fixtures in the core test suite.
   - *RC1 Disposition*: Handlers and schemas are registered; complete end-to-end integration tests deferred to post-RC1 test hardening.

---

## Section H — Test Execution Record

Targeted test suites were executed in the local Frappe Bench development environment (`/home/jules/frappe-bench` with `test_site` and Node.js v20) to verify source behavior without altering any code.

### 1. Frontend Unit Tests (`yarn test:frontend`)
- **Command**: `node --experimental-default-type=module --test --test-reporter=spec $(find tests/frontend -name '*.test.mjs' -o -name '*.test.js')`
- **Exit Code**: `0`
- **Result**: **PASS** (34 passed, 0 failed, duration: 747ms)
- **Scope Covered**:
  - Filter leaf summary, operators, serializer, and canonical query filter persistence.
  - Output field metadata, model, schema, and schema refresh.
  - Tree builder core and drag models.
  - CheckControl and GenericGrid models.
  - Inline presentation policy, action config validation, draft session, and save lifecycle.
  - Graph dirty state, layout merge, stable serialization, and workspace guard.

### 2. Backend Automated Test Suites (`bench run-tests`)
Executed across 13 test modules covering action handlers, query engine, process runtime, sub-rules, and versioning:
1. `flexirule.ruleflow.tests.test_action_return_schema_contract`: 26 tests (0.142s — OK)
2. `flexirule.ruleflow.tests.test_process_contract_v2`: 4 tests (0.331s — OK)
3. `flexirule.ruleflow.tests.test_sub_rule_contract`: 5 tests (0.006s — OK)
4. `flexirule.ruleflow.tests.test_fetch_records`: 29 tests (2.086s — OK)
5. `flexirule.ruleflow.tests.test_query_records_canonical_filters`: 1 test (0.035s — OK)
6. `flexirule.ruleflow.tests.test_query_records_refactor`: 17 tests (3.590s — OK)
7. `flexirule.ruleflow.tests.test_assignment_resolver`: 12 tests (0.120s — OK)
8. `flexirule.ruleflow.tests.test_permissions`: 10 tests (4.916s — OK)
9. `flexirule.ruleflow.tests.test_advanced_rule_flows`: 5 tests (3.869s — OK)
10. `flexirule.ruleflow.tests.test_engine_complex_flows`: 3 tests (2.328s — OK)
11. `flexirule.ruleflow.tests.test_loop_flow_constraints`: 9 tests (0.417s — OK)
12. `flexirule.ruleflow.tests.test_process_sync`: 17 tests (1.929s — OK)
13. `flexirule.ruleflow.tests.test_rule_versioning`: 17 tests (3.222s — OK)

- **Total Backend Tests Executed & Passed**: Exactly 155 tests across 13 test modules; 0 failures; 0 errors.

### 3. Static Code Quality & Linter Checks
- **Command**: `/home/jules/.local/bin/ruff check flexirule/`
- **Exit Code**: `0` (All checks passed!)

---

## Section I — Final Release Recommendation

**Recommendation**: **READY AFTER LISTED BLOCKERS ARE CLOSED**

### Outstanding Conditions for RC1:
1. **Resolve PRC-368 (P0 Blocker, Issue #368)**: Make Process filesystem synchronization deterministic and change-aware during `bench migrate`, replacing timestamp-only checks with content/hash reconciliation and testing standard process pruning.
2. **Resolve TXN-001 (P1 Blocker, Issue #359)**: Implement proper savepoint wrapping in `flexirule/ruleflow/core/engine.py` around action execution when `on_error == "Rollback"`, avoiding unhandled database exceptions and uncoordinated full rollbacks.
3. **Resolve REL-001 (P1 Blocker, Issue #360)**: Synchronize `RELEASE_DISABLED_ACTION_TYPES` in `flexirule/ruleflow/core/contract_utils.py` to match the frontend gating list (`["Loop", "Switch"]`), ensuring contract DTO hydration and server-side validators (`validation_service.py`, `engine.py`) strictly enforce release gating.
4. **Documentation Alignment (Issue #361)**: Maintain documentation for QRY-001 (Frappe v15 Query Builder fail-closed behavior) and WAI-001 (synchronous execution of Wait action).

Once these targeted corrections are in place, the FlexiRule core automation engine is architecturally sound and ready for Release Candidate 1.
