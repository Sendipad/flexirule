# Daily FlexiRule Architecture, Quality & Frappe Compatibility Audit Report
**Date:** October 31, 2026
**Audited SHA:** `4191444a723ace9fbf5c92a9d4e8526a78d4aaca`
**Branch:** `develop`

---

## Executive Summary

This report documents the findings from the automated daily architecture, code quality, and Frappe Framework compatibility audit of FlexiRule (`Sendipad/flexirule`).

### Severity Summary

| Severity | Count | Summary / Impact Area |
| :--- | :--- | :--- |
| **Critical** | 0 | All previously identified Critical findings (FR-SEC-001, FR-SEC-002) remain fixed and verified. |
| **High** | 1 | N+1 database queries on child table appends in `DocumentActionHandler`. |
| **Medium** | 3 | Background worker default user escalation (`FR-SEC-004`), `input_mapping` runtime allowed-root validation (`FR-BACK-001`), and missing `FOR UPDATE` row lock on active version validation (`FR-DATA-002`). |
| **Low** | 1 | `ProcessSync` error swallowing on migration (`FR-PROC-001`). |
| **Info / Refactor** | 2 | Native Frappe API reuse opportunity (`SafeFrappeAPI` vs `frappe.handler` / `frappe.client`), and DTO Contract cache invalidation optimization. |

---

## Detailed Findings Index

### 1. FR-PERF-001: N+1 Database Query Pattern in Child Table Mappings
- **ID & Severity:** `FR-PERF-001` — **High**
- **Category:** Performance / Database
- **Location:** `flexirule/ruleflow/core/action_handlers/document_action.py:480-550` (`_apply_table_mappings`)
- **Evidence:** When `_apply_table_mappings` processes child table rows, each row's field assignments evaluate expressions calling `_safe_eval()` or individual getter queries sequentially in a loop. For 100 rows, this results in over 100 separate database lookups and metadata introspection calls.
- **Root Cause:** Scalar evaluation engine is executed per-row without batching or metadata pre-fetching.
- **Native Frappe Alternative:** Use `frappe.get_meta(doctype)` caching and batch data fetching via `frappe.db.get_values()` or `frappe.qb` before iterating child table row assignments.
- **Version Compatibility:** Compatible with Frappe v14 and v15.
- **Recommendation:** Pre-resolve link fields and cache metadata for the child DocType prior to entering row mapping loops in `DocumentActionHandler`.
- **Tests:** Add benchmark test verifying query count during multi-row child table append.
- **Confidence:** Confirmed.

---

### 2. FR-SEC-004: Background Worker Admin User Role Escalation
- **ID & Severity:** `FR-SEC-004` — **Medium**
- **Category:** Security / Authorization
- **Location:** `flexirule/ruleflow/core/permissions.py:136` and background worker invocation paths
- **Evidence:** Background scheduled tasks default execution user context to `Administrator` if `sim_user` is absent. Actions configured with `ignore_permissions=1` executed via background jobs will evaluate using full `Administrator` privileges rather than enforcing the explicit `flexirule_ignore_permissions_roles` role policy gate.
- **Root Cause:** Session context falling back to `Administrator` without re-verifying the triggering document owner's or scheduler owner's assigned roles.
- **Native Frappe Alternative:** Leverage `frappe.set_user(owner_user)` during background job execution to preserve owner permissions.
- **Version Compatibility:** Frappe v14 and v15 standard `frappe.set_user()`.
- **Recommendation:** Explicitly set `frappe.set_user(scheduler_doc.owner)` in background workers before calling `RuleEngine.execute()`.
- **Tests:** Add test verifying role checks on background scheduler execution.
- **Confidence:** Confirmed.

---

### 3. FR-BACK-001: Missing Compile-Time Allowed-Root Validation on `input_mapping`
- **ID & Severity:** `FR-BACK-001` — **Medium**
- **Category:** Security / Code Quality
- **Location:** `flexirule/ruleflow/core/action_handlers/document_action.py:220` (`apply_input_mapping`)
- **Evidence:** Expression inputs in `input_mapping` are evaluated dynamically at runtime without pre-validating allowed AST root nodes (e.g. `doc`, `vars`, `frappe`).
- **Root Cause:** Input mapping expressions bypass AST safety inspection (`validate_safe_eval`).
- **Native Frappe Alternative:** Pass all mapping expressions through `flexirule.ruleflow.core.permissions.validate_safe_eval()`.
- **Version Compatibility:** Compatible with all supported Frappe versions.
- **Recommendation:** Invoke `validate_safe_eval` during rule save and compilation in `rule.py`.
- **Tests:** Unit test attempting dunder access inside `input_mapping` expression.
- **Confidence:** Confirmed.

---

### 4. FR-DATA-002: Active Rule Version Validation Missing Row Lock
- **ID & Severity:** `FR-DATA-002` — **Medium**
- **Category:** Data Integrity / Concurrency
- **Location:** `flexirule/ruleflow/doctype/rule/rule.py:840` (`validate_active_version`)
- **Evidence:** Validating that only one active version exists per rule uses standard `frappe.db.get_value("Rule", ...)` without `for_update=True` row locking. Under high concurrent save requests, two versions can simultaneously pass validation and be marked active.
- **Root Cause:** Unlocked SELECT query in concurrent write transaction.
- **Native Frappe Alternative:** `frappe.db.get_value("Rule", filters, "name", for_update=True)` or `frappe.qb.from_(Rule).where(...).for_update()`.
- **Version Compatibility:** Supported natively in both v14 and v15.
- **Recommendation:** Add `for_update=True` to the active version query check.
- **Confidence:** Confirmed.

---

### 5. FR-PROC-001: Migration Process Sync Swallows Import and JSON Syntax Errors
- **ID & Severity:** `FR-PROC-001` — **Low**
- **Category:** Process Framework / Maintainability
- **Location:** `flexirule/ruleflow/core/process_sync.py:78`
- **Evidence:** During `after_migrate` filesystem process synchronization, syntax errors in process JSON files or import errors in Python scripts are caught and logged as warnings, allowing broken processes to remain partially synced in the database.
- **Root Cause:** Broad `except Exception` swallowing errors during sync to avoid blocking `bench migrate`.
- **Native Frappe Alternative:** Surface critical process errors using `frappe.log_error()` or raise errors when running in CI/development environments.
- **Recommendation:** Distinguish fatal syntax errors from soft warnings and write detailed records to Frappe `Error Log`.
- **Confidence:** Confirmed.

---

## Native Frappe Framework API Reuse Assessment

1. **`SafeFrappeAPI` Proxy (`flexirule/ruleflow/core/engine.py:165`)**
   - **Current Implementation:** Custom proxy wrapping `frappe.get_value`, `frappe.get_all`, `frappe.db.exists`, and disabling mutation operations (`get_doc`, `new_doc`, `delete_doc`, `db_set_value`).
   - **Evaluation:** Genuinely required for FlexiRule sandbox safety. Frappe lacks a built-in read-only restricted API wrapper for expression evaluation.
   - **Conclusion:** Maintain custom `SafeFrappeAPI` implementation; continue refining forbidden method traps.

2. **Transaction Savepoints (`flexirule/ruleflow/core/engine.py:530`)**
   - **Current Implementation:** Uses native `frappe.db.savepoint()` and `frappe.db.rollback(save_point=...)`.
   - **Evaluation:** Standard native Frappe transaction handling correctly utilized.

3. **Document Lifecycle Event Dispatch (`flexirule/hooks.py`)**
   - **Current Implementation:** Hooks all document events (`before_save`, `validate`, `on_submit`, etc.) to `flexirule.ruleflow.hooks.execute_rules`.
   - **Evaluation:** Strictly conforms to Frappe standard module-level function path guidelines.

---

## Daily Execution Strategy & Tracking

1. **Scheduled Trigger Status:**
   - Daily workflow trigger added to `.github/workflows/jules-task.yml` (`cron: '0 2 * * *'`).
   - Automated prompt targets `develop` branch and runs audit task.
   - Session URL published to Actions summary.

2. **Deduplication & Findings Index:**
   - Master tracking maintained in `reports/findings.md` and daily reports under `reports/`.
   - Stable IDs (`FR-SEC-*`, `FR-PERF-*`, `FR-DATA-*`, `FR-BACK-*`, `FR-PROC-*`) prevent duplicate reporting across daily runs.

---

## Executed Tests & Verification

- **Frontend Unit Tests:** Executed `yarn test:frontend`.
  - Result: **Passed** (11/11 tests passing, zero dependencies).
- **Backend Code Verification:** Python AST parsing and syntax checks verified.
