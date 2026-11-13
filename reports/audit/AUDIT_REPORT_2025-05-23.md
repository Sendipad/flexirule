# FlexiRule Comprehensive Architecture, Code Quality & Frappe Compatibility Audit Report

**Audit Date:** 2025-05-23
**Target Branch:** `develop`
**Auditor:** Senior Frappe Architect & Software Quality Audit System (Jules)
**Status:** Initial Audit Completed

---

## Executive Summary

A comprehensive deep audit of the **FlexiRule** codebase was conducted covering Python backend modules, action handlers, Vue/JS frontend components, RuleFlow execution engine, contract schemas, permission layers, and native Frappe v15/v16 API compatibility.

FlexiRule exhibits a strong architectural foundation built around contracts as the single source of truth (`TRIGGER_TYPE_CONTRACT`, `contract_utils.py`, `FlexValueControl`). However, several key opportunities for improvement were identified regarding cache invalidation race conditions, native Frappe Query Builder utilization, document event hook overhead, and report-level permission contracts.

---

## Findings Summary Table

| Finding ID | Title | Category | Severity | File / Location | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **AUDIT-001** | Process Contract Invalidation Cache Key Mismatch | Concurrency / Cache | **High** | `flexirule/ruleflow/hooks.py:126` | Open |
| **AUDIT-002** | Query Records Aggregate Expressions Bypassing Query Builder | Frappe API / Query | **Medium** | `flexirule/ruleflow/core/action_handlers/query_records.py:840` | Open |
| **AUDIT-003** | `Query Report` Mode Ignores `ignore_permissions` Contract Silent Behavior | Permissions / Contract | **Medium** | `flexirule/ruleflow/core/action_handlers/query_records.py:1290` | Open |
| **AUDIT-004** | Broad Doc Events Triggering Overhead on Non-Rule DocTypes | Performance / Hooks | **Medium** | `flexirule/hooks.py:14` | Open |
| **AUDIT-005** | Workflow Concurrency Key Missing Run ID Differentiation | CI/CD Automation | **Low** | `.github/workflows/jules-task.yml:30` | Resolved (in this PR) |

---

## Detailed Audit Findings

### AUDIT-001: Process Contract Invalidation Cache Key Mismatch
- **ID & Severity:** AUDIT-001 | **Severity:** High
- **Category:** Race Condition / Cache Invalidation
- **Location:** `flexirule/ruleflow/hooks.py`, lines 126–135
- **Evidence:**
  ```python
  def clear_rule_cache(doc=None, method=None, *args, **kwargs):
      if RuleCoordinator.should_rebuild_registry_for_rule_change(doc, method):
          clear_rule_action_plan_cache(rule_name=doc.name)
          clear_compiled_artifact_cache(rule_name=doc.name)
          RuleCoordinator.clear_cache(doctype=doc.get("document_type"))
  ```
- **Root Cause:** When a `Rule` is updated or deleted, `RuleCoordinator.clear_cache` invalidates the `document_type` cache in Redis. However, compiled process contracts and action plan caches used by `process_runtime_v2.py` store cache keys formatted with `rule_name` instead of `document_type`. As a result, updating a Rule invalidates the Rule level cache but leaves stale compiled process runtime contracts in worker process memory when workers execute queued rules.
- **Impact:** Workers may execute outdated rule decision logic after a Rule doc has been edited in Desk until the worker process restarts or Redis cache TTL expires.
- **Recommended Remediation:** Ensure `clear_rule_cache` explicitly triggers `clear_compiled_artifact_cache` for both `rule_name` and `document_type` key aliases, and broadcasts a process cache invalidation signal.
- **Relevant Tests:** `flexirule/ruleflow/tests/test_rule_cache_invalidation.py`
- **Verification Status:** Unverified / Open

---

### AUDIT-002: Query Records Aggregate Expressions Bypassing Native Query Builder
- **ID & Severity:** AUDIT-002 | **Severity:** Medium
- **Category:** Frappe API Compatibility / SQL Injection Risk
- **Location:** `flexirule/ruleflow/core/action_handlers/query_records.py`, lines 840–865
- **Evidence:**
  ```python
  rows = frappe.get_list(
      reference_doctype,
      filters=filters,
      or_filters=or_filters,
      fields=[f"{agg_fn}({agg_field_expr}) as result"],
      ignore_permissions=ignore_permissions,
      limit_page_length=0,
  )
  ```
- **Root Cause:** In aggregate mode (`Sum`, `Average`, `Min`, `Max`), `QueryRecordsHandler` constructs formatted field strings using backticks (`f"`tab{field_dt}`.`{field_name}`"`). Frappe v15/v16 `frappe.qb` provides native aggregate methods (`frappe.qb.functions.Sum`, `Avg`, `Min`, `Max`). Passing formatted strings to `frappe.get_list` relies on raw SQL string interpolation inside Frappe's field parser rather than Query Builder AST expressions.
- **Impact:** Increases risk of SQL formatting incompatibilities on non-MySQL dialects (e.g. PostgreSQL in custom Frappe setups) and bypasses PyPika/QueryBuilder AST type checks.
- **Recommended Remediation:** Refactor `_aggregate` and `_group_by` in `QueryRecordsHandler` to execute queries via `frappe.qb` (using `flexirule.ruleflow.utils.frappe_query_compat`), aligning with the `Fetch Records` design.
- **Relevant Tests:** `flexirule/ruleflow/tests/test_query_records_aggregates.py`
- **Verification Status:** Unverified / Open

---

### AUDIT-003: `Query Report` Mode Silently Ignores `ignore_permissions` Parameter
- **ID & Severity:** AUDIT-003 | **Severity:** Medium
- **Category:** Permission Contract / Error Handling
- **Location:** `flexirule/ruleflow/core/action_handlers/query_records.py`, lines 1290–1310
- **Evidence:**
  ```python
  def _query_report(self, reference_doctype, config, context, action, ignore_permissions):
      # Note: ignore_permissions is a no-op for Query Report mode.
      # Frappe's query_report.run() enforces report-level permissions
      # internally and does not accept an ignore_permissions parameter.
  ```
- **Root Cause:** When `Query Records` is configured with operation `Query Report` and `ignore_permissions` is enabled on the rule step, `QueryRecordsHandler` silently discards `ignore_permissions` because `frappe.desk.query_report.run()` does not support permission overrides.
- **Impact:** System Manager authors setting `ignore_permissions` on a Query Report rule step will experience unexpected `PermissionError` exceptions during background background execution for non-System Manager trigger users without clear warning during validation.
- **Recommended Remediation:** Add a validation check in `QueryRecordsHandler.get_operation_contracts()` or `validate_query_report()` to alert rule authors when `ignore_permissions` is set on `Query Report` mode, or handle `PermissionError` explicitly with a informative exception message.
- **Relevant Tests:** `flexirule/ruleflow/tests/test_query_report_permissions.py`
- **Verification Status:** Unverified / Open

---

### AUDIT-004: Broad Doc Events Triggering Overhead on Non-Rule DocTypes
- **ID & Severity:** AUDIT-004 | **Severity:** Medium
- **Category:** Performance / Hook Optimization
- **Location:** `flexirule/hooks.py`, lines 14–34
- **Evidence:**
  ```python
  doc_events = {
      "*": {
          "before_naming": "flexirule.ruleflow.hooks.execute_rules",
          "before_insert": "flexirule.ruleflow.hooks.execute_rules",
          "before_save": "flexirule.ruleflow.hooks.execute_rules",
          "validate": "flexirule.ruleflow.hooks.execute_rules",
          ...
      }
  }
  ```
- **Root Cause:** `flexirule` listens to 16 document lifecycle events on wildcard `"*"` DocTypes. While `execute_rules_from_event` uses `RuleCoordinator.has_active_rules` for fast-exit negative caching, every single document insert, update, or save across the entire ERPNext site incurs Frappe hook dispatch overhead and `get_excluded_doctypes()` set checks.
- **Impact:** High-volume transaction processing (e.g. bulk stock ledger entries, GL entries, or API imports) incurs slight CPU overhead per record save.
- **Recommended Remediation:** Maintain a dynamic list of active rule DocTypes in Redis/Frappe cache and check `doc.doctype in active_doctypes` before calling full hook resolution.
- **Relevant Tests:** `flexirule/ruleflow/tests/test_hook_performance.py`
- **Verification Status:** Unverified / Open

---

### AUDIT-005: Workflow Trigger Compatibility & Scheduled Execution Safety
- **ID & Severity:** AUDIT-005 | **Severity:** Low
- **Category:** CI/CD Automation / Workflow Governance
- **Location:** `.github/workflows/jules-task.yml`
- **Evidence:** Daily cron trigger (`0 2 * * *`) added, default prompt configured for `schedule` events targeting `develop`, and Python request preparation updated to handle empty human inputs.
- **Impact:** Resolved. Automated daily audits can now run headlessly without human input, outputting findings into `reports/audit/`.
- **Recommended Remediation:** N/A (Verified & Resolved in this PR).
- **Verification Status:** Verified / Resolved

---

## Methodological Summary & Next Steps

1. **Daily Execution:** Scheduled runs will inspect newly committed code changes against this report.
2. **Remediation Strategy:** Critical and High findings (e.g. AUDIT-001) should be addressed in focused, isolated PRs with dedicated regression tests.
3. **Continuous Tracking:** Resolved findings will be updated in subsequent daily reports without creating duplicate records.
