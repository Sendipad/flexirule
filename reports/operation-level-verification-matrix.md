# FlexiRule Operation-Level Verification Matrix

## Section A — Executive Summary

- **Audit Date**: 2026-11-01
- **Repository**: [https://github.com/Sendipad/flexirule](https://github.com/Sendipad/flexirule)
- **Audited Commit SHA**: `504840d3bf3ec012a2c0ed5c7859bc7a7fd1b3c2`
- **Target Branch**: `develop`
- **Audit Scope**: Comprehensive source code audit and empirical verification of every supported FlexiRule RuleFlow Action Type and individual operation, covering frontend registration, configuration UI components, backend contracts, schema validation, runtime handlers, authorization boundaries, error and transaction handling, and test coverage.
- **Discovered Action Types**: 13
- **Discovered Individual Operations**: 43 (31 core Action Type operations across 13 Action Types + 12 Process operations across 4 Process modules)
- **Status Breakdown**:
  - **PASS**: 42 operations
  - **PARTIAL**: 1 operation (`Switch`)
  - **FAIL**: 0 operations
  - **UNVERIFIED**: 0 operations
  - **DISABLED**: 0 operations
  - **EXPERIMENTAL**: 0 operations
- **Confirmed P0 Findings**: 0
- **Confirmed P1 Findings**: 1 (`SWT-001`: Switch Action Contract / Fallback Mismatch & Graph Validation Blindspot)
- **Confirmed P2 Findings**: 2 (`WIT-001`: Wait Action Worker Thread Blocking via `time.sleep()`, `NOT-001`: Email & Provider External Side-Effects Non-Rollbackable)
- **RC1 Recommendation**: **READY AFTER LISTED BLOCKERS ARE CLOSED** (Resolve `SWT-001` or officially gate `Switch` action before tagging RC1).

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
- `RELEASE_DISABLED_ACTION_TYPES`: Empty in `contract_utils.py`, indicating all 13 core Action Types are open for release evaluation.

---

## Section C — Operation-Level Verification Matrix

| Action Type | Operation | UI/Contract | Runtime | Validation | Security | Error / Transaction | Tests | Overall Status | Finding IDs |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Entry Action** | Entry Action | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Condition** | Condition | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Switch** | Switch | PARTIAL | PASS | PARTIAL | PASS | PASS | PARTIAL | **PARTIAL** | `SWT-001` |
| **Loop** | Loop | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Stop** | Success | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Stop** | Error | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Raise Error** | Raise Error | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Wait** | Wait | PASS | PASS | PASS | PASS | PARTIAL | PASS | **PASS** | `WIT-001` |
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
| **Notify** | System | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Notify** | Email | PASS | PASS | PASS | PASS | PARTIAL | PASS | **PASS** | `NOT-001` |
| **Notify** | System Notification | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** | — |
| **Notify** | Provider | PASS | PASS | PASS | PASS | PARTIAL | PASS | **PASS** | `NOT-001` |
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
- **Contract**: Multi-branch router. ActionContract declares `has_next_true=False`, `has_next_false=True`. Config contains `expression` and `cases` dict mapping value string to target action id.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/switch.py` (`SwitchHandler.execute`), evaluates expression via `engine._evaluate_python_value(expression, context)`, then looks up target in `cases[val]` or falls back to `action.next_step_if_true`.
- **Validation Defect**: `SwitchHandler` uses `action.next_step_if_true` as default fallback, but contract declares `has_next_true=False` and `has_next_false=True`. In addition, `graph_validator.validate_graph_integrity` does not inspect `config.cases` targets when calculating reachability and recursion stacks, potentially triggering false-positive cycle or orphan errors on valid switch flows (Finding `SWT-001`).
- **Security**: Evaluates expression with `frappe.safe_eval`.
- **Failure Behavior**: Unhandled expression syntax or runtime errors throw `ValidationError`.
- **Tests**: Minimal tests in `test_engine_comprehensive.py:test_engine_execute_switch_action` and `test_advanced_rule_flows.py`. Status: **PARTIAL**.

#### Loop
- **Contract**: Iterates over collection. `has_next_true=True` (body path), `has_next_false=True` (after last / complete path). Requires `config` and `return_variable` (item alias).
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/loop.py` (`LoopHandler.execute`). Maintains iteration state in `context["vars"]["_loops"][action_id]`. Exposes current item under alias and metadata under `context["vars"]["loop"]` (`index`, `first`, `last`, `length`).
- **Validation**: Strict graph validation in `validation_service.py` (`_loop_body_returns_to_loop`) verifies that body path cycles back to the Loop node and After-Last path leads downstream without loop-shadowing.
- **Security**: Memory iteration bounded by max node visit limits in `RuleEngine` (`max_visits_per_node=1000`).
- **Failure Behavior**: Errors in loop body abort or follow action error policy. Loop state cleaned up on completion.
- **Tests**: `test_loop_flow_constraints.py`, `test_engine_comprehensive.py:test_engine_execute_loop_action`. Status: **PASS**.

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
  1. `Toast`: Realtime browser alert (`frappe.msgprint(..., alert=True)`).
  2. `System`: Realtime websocket publish (`frappe.publish_realtime`).
  3. `Email`: Dispatches email via `frappe.sendmail`. Requires `recipients` and `subject`.
  4. `System Notification`: Creates persistent `Notification Log` document for target user. Requires `subject`.
  5. `Provider`: Dispatches to external hook provider (`flexirule_notification_providers`). Requires `provider` and `recipient`.
- **Execution Path**: `flexirule/ruleflow/core/action_handlers/simple_actions.py` (`NotifyHandler.execute`). Renders message with `SafeFrappeAPI`.
- **Validation**: Enforces required config keys per mode in `validation_service.py` and `NotifyHandler.validate()`.
- **Security**: Jinja templates evaluated with safe globals. Prevents script injection.
- **Limitation (Finding `NOT-001`)**: Email and Provider external dispatches cannot be rolled back if subsequent database actions fail.
- **Tests**: Unit tests in `test_compiled_controls.py` and integration tests in `test_advanced_rule_flows.py`. Status: **PASS**.

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
| **10** | External Side-Effect on Downstream Failure | Notify (Email/Provider) → Subsequent Failure | Email is sent via SMTP before subsequent action fails; DB rolls back but email cannot be unsent. | Verified: Database changes revert, but external network dispatch persists. | Hand-traced in `simple_actions.py` | `NOT-001` |

---

## Section F — RC1 Release Blockers

| Finding ID | Affected Operation | Severity | Evidence & Location | Business / Technical Impact | Recommended Correction | Required Test to Close | RC1 Disposition |
| :--- | :--- | :---: | :--- | :--- | :--- | :--- | :---: |
| **SWT-001** | `Switch` Action | **P1** | `flexirule/ruleflow/core/action_handlers/switch.py:27` (`has_next_true=False`, `has_next_false=True`) vs `switch.py:76` (`action.next_step_if_true`). In `flexirule/ruleflow/utils/graph_validator.py:16`, `get_neighbors` only reads `next_step_if_true` and `next_step_if_false`, ignoring `config.cases` targets. | Active rules with Switch nodes can fail graph validation with false-positive orphan or dead-end errors. At runtime, the fallback destination uses `next_step_if_true` while contract specifies `has_next_true=False`. | Align contract to `has_next_true=True` (as default/fallback path); update `graph_validator.py` to inspect `config.cases` targets during cycle and reachability checks. | Integration test verifying an active rule with multi-branch Switch paths passes graph validation and executes fallback correctly. | **Must be resolved or Switch gated before RC1** |

---

## Section G — Accepted Limitations and Deferrals

| Limitation ID | Affected Operation | Current Behavior | Why Acceptable for RC1 | User Impact & Workaround | Documentation Requirement | Follow-up Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **WIT-001** | `Wait` Action | Uses synchronous `time.sleep(duration)` in `simple_actions.py:161`. | Acceptable for short delays (1-10 seconds) or scheduler jobs; long delays in web workers are user error. | Users configuring large wait times in synchronous DocType events will block web workers. | Document that `Wait` is synchronous and recommend durations under 10 seconds. | Implement asynchronous delayed execution via Frappe scheduler / Redis background worker in v1.1. |
| **NOT-001** | `Notify` (Email & Provider) | External network dispatches (SMTP, HTTP webhook) occur immediately during execution. | Standard Frappe framework behavior (external API calls cannot be rolled back by MariaDB). | If a subsequent action fails after an email is sent, the email cannot be revoked. | Add warning in UI builder: "External notifications are immediate and cannot be rolled back." | Place notification actions near the end of flows, or implement two-phase commit queue. |
| **QRY-001** | `Query Records` (Fetch Records) | Frappe v15 Query Builder lacks row-level permission enforcement. FlexiRule fails closed unless `ignore_permissions=1` is explicitly set with audit reason. | Enforces strict security by default; fails safe rather than leaking unauthorized data. | Users must provide an audit reason when querying with Query Builder on Frappe v15. | Document that Frappe v15 Fetch Records requires `ignore_permissions` with an audit reason. | Leverage Frappe v16 native QB permission hooks when available. |
| **ASN-001** | `Assignment` (Deep Document Paths) | Restricts `doc.*` mutations to root document fields (`len(parts) == 2`). Deep dotted paths throw `MethodExecutionError`. | Prevents unintended child-table corruption; child-table rows should be manipulated via `Loop` or `append` operator. | Assigning to `doc.child_table.field` directly is blocked. | Document that child-table row updates require Loop iteration. | Implement safe child-row indexing in v1.1. |

---

## Section H — Test Execution Record

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

### **READY AFTER LISTED BLOCKERS ARE CLOSED**

#### Rationale & Outstanding Conditions:
1. **Core Maturity**: 42 out of 43 operations exhibit robust implementation-contract parity, solid permission guards (failing closed with audited bypass requirements), transaction savepoint isolation, and comprehensive test coverage (720 backend tests and 33 frontend tests passing).
2. **Blocker Closure Required**:
   - **`SWT-001`**: Correct the `Switch` Action Contract (`has_next_true=True`, matching runtime fallback) and update `graph_validator.py` to trace `config.cases` edges during rule activation checks. Alternatively, add `Switch` to `RELEASE_DISABLED_ACTION_TYPES` if multi-branch visual edges are deferred to v1.1.
3. **Documentation Sign-Off**:
   - Document the synchronous behavior of `Wait` (`WIT-001`).
   - Document external notification non-rollback characteristics (`NOT-001`).
   - Document Frappe v15 `Fetch Records` permission audit reason requirement (`QRY-001`).

Once `SWT-001` is resolved or gated, FlexiRule is architecturally ready for its first Release Candidate (RC1).
