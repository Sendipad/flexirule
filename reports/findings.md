# Consolidated Audit Findings — FlexiRule

## Master Findings Summary

| Finding ID | Severity | Area | File / Location | Finding Summary | Status | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **FR-SEC-001** | **CRITICAL** | Security | `flexirule/ruleflow/core/permissions.py:186` | AST validation stub in `validate_safe_eval` allows Python sandbox escape via dunder attributes | **Fixed** | High |
| **FR-SEC-002** | **CRITICAL** | Security | `flexirule/ruleflow/core/action_handlers/document_action.py:642` | Unsanitized Jinja template rendering (`_render_scalar`) permits Server-Side Template Injection (SSTI) | **Fixed** | High |
| **FR-SEC-003** | **HIGH** | Security | `flexirule/ruleflow/core/engine.py:165` | `SafeFrappeAPI.format_value` accepts unvalidated `df` dict, bypassing read-only restrictions | **Fixed** | High |
| **FR-SEC-004** | **HIGH** | Security | `flexirule/ruleflow/core/permissions.py:136` | Background worker execution defaults to Administrator session user, bypassing `ignore_permissions` role gate | Documented | High |
| **FR-DATA-001** | **HIGH** | Data Integrity | `flexirule/ruleflow/core/engine.py:530` | Savepoint rollback failure swallows database error and leaves partial mutations committed | **Fixed** | High |
| **FR-ENGINE-001** | **HIGH** | Rule Engine | `flexirule/ruleflow/core/action_plan_cache.py:53` | Wildcard Redis key pattern deletion fails in Redis clusters, leaving stale action plans active | **Fixed** | High |
| **FR-ENGINE-002** | **HIGH** | Rule Engine | `flexirule/ruleflow/core/action_handlers/sub_rule.py:85` | Sub-rule execution does not propagate depth counter, leading to unenforced recursion limits and stack overflow | **Fixed** | High |
| **FR-BACK-001** | **MEDIUM** | Backend | `flexirule/ruleflow/core/action_handlers/document_action.py:220` | `input_mapping` expressions are evaluated at runtime without compile-time allowed-root validation | Documented | High |
| **FR-FE-001** | **MEDIUM** | Frontend | `flexirule/public/js/flexirule/rule_builder/stores/useRuleStore.js:145` | VueFlow canvas auto-layout execution causes false "is dirty" state on initial document load | **Fixed** | High |
| **FR-FE-002** | **MEDIUM** | Frontend | `flexirule/public/js/flexirule/rule_builder/stores/useRuleStore.js:320` | Double stringification of `condition_json` during save corrupts raw JSON condition payloads | Documented | High |
| **FR-FE-003** | **MEDIUM** | Frontend | `flexirule/public/js/flexirule/rule_builder/stores/useGraphStore.js:412` | Duplicating a node reuses the existing `action_id`, causing collision and graph target errors | **Fixed** | High |
| **FR-PROC-001** | **MEDIUM** | Process Framework | `flexirule/ruleflow/core/process_sync.py:78` | Filesystem process sync swallows import and JSON syntax errors during migration | Documented | High |
| **FR-DATA-002** | **MEDIUM** | Data Integrity | `flexirule/ruleflow/doctype/rule/rule.py:840` | Active version validation lacks row locking (`FOR UPDATE`), permitting concurrent active versions | Documented | High |
| **FR-PERF-001** | **HIGH** | Performance | `flexirule/ruleflow/core/action_handlers/document_action.py:480` | N+1 database query pattern during child table row appends in `DocumentActionHandler` | Documented | High |
| **FR-DATA-003** | **LOW** | Data Integrity | `flexirule/ruleflow/doctype/rule_execution_log/rule_execution_log.json` | Missing database index on `execution_id` causes full table scans during log lookups | **Fixed** | High |
| **FR-DOC-001** | **INFO** | Documentation | `flexirule/ruleflow/README.md` | Discrepancy between documented sub-rule recursion enforcement and actual runtime behavior | **Fixed** | High |

---

## Detailed Finding Entries & Remediation Summaries

### FR-SEC-001: AST Validation Stub in `validate_safe_eval` (CRITICAL)
- **Status**: **Fixed**
- **File**: `flexirule/ruleflow/core/permissions.py`
- **Remediation**: Replaced syntax-only `compile()` with `ast.parse()` and `SafeEvalVisitor(ast.NodeVisitor)` to inspect AST trees and throw `ValidationError` upon encountering attribute or identifier names starting with `__` or import statements. Verified by `test_FR_SEC_001_ast_validation_stub_sandbox_escape`.

---

### FR-SEC-002: Server-Side Template Injection in Document Actions (CRITICAL)
- **Status**: **Fixed**
- **File**: `flexirule/ruleflow/core/action_handlers/document_action.py`
- **Remediation**: Removed global `frappe` module injection from `_template_context()` in `DocumentActionHandler`. Jinja template rendering contexts now only receive `doc` and `vars`. Verified by `test_FR_SEC_002_ssti_in_document_action_rendering`.

---

### FR-SEC-003: SafeFrappeAPI Format Value Bypass (HIGH)
- **Status**: **Fixed**
- **File**: `flexirule/ruleflow/core/engine.py`
- **Remediation**: Added parameter validation in `SafeFrappeAPI.format_value` to raise `PermissionError` if `df` is passed as a raw dictionary override. Verified by `test_FR_SEC_003_safe_frappe_api_format_value_dict_override`.

---

### FR-DATA-001: Savepoint Rollback Failure Swallowing (HIGH)
- **Status**: **Fixed**
- **File**: `flexirule/ruleflow/core/engine.py`
- **Remediation**: Added `frappe.db.rollback()` fallback inside `_execute_graph()` when savepoint rollback raises an exception, ensuring full transaction rollback to protect database integrity.

---

### FR-ENGINE-001: Wildcard Redis Pattern Key Deletion Defect (HIGH)
- **Status**: **Fixed**
- **File**: `flexirule/ruleflow/core/action_plan_cache.py`
- **Remediation**: Updated `clear_rule_action_plan_cache()` to call `frappe.cache.delete_value(pattern)` and `delete_keys(pattern)` directly.

---

### FR-ENGINE-002: Sub-Rule Recursion Depth Counter Loss (HIGH)
- **Status**: **Fixed**
- **File**: `flexirule/ruleflow/core/action_handlers/sub_rule.py`
- **Remediation**: Updated `SubRuleHandler.execute()` to pass `_sub_rule_depth = context.get("_sub_rule_depth", 0) + 1` into child execution context and throw `CycleDetectedError` when depth exceeds `MAX_SUB_RULE_DEPTH = 2`. Verified by `test_FR_ENGINE_002_sub_rule_recursion_depth_propagated`.
