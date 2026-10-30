# Data Integrity and Transactions — FlexiRule

## 1. Overview & Transaction Model

FlexiRule relies on Frappe's underlying database transaction management during document event rules executed within HTTP request cycles. Actions in FlexiRule mutate documents (`doc`), context variables (`vars`), and external database records.

Transaction mechanisms:
1. **Frappe Standard Doc Event Transaction**: All rule actions running inside synchronous hooks (`before_save`, `validate`, `on_update`) execute within the active HTTP request MariaDB transaction.
2. **Action-Level Error Policies**: `on_error` settings on actions:
   - `Stop`: Stops graph traversal and raises exception, triggering full transaction rollback.
   - `Continue`: Swallows error, logs warning, and proceeds to `next_step_if_true`.
   - `Retry`: Re-executes the action up to `retry_count` times with exponential backoff.
   - `Rollback`: Sets a MariaDB savepoint (`frappe.db.savepoint()`) before action execution and rolls back to savepoint on failure.
3. **Asynchronous Background Queue**: Actions marked `is_async=1` execute in separate background Redis/RQ jobs using dedicated database connections.

---

## 2. Detailed Findings

### Finding FR-DATA-001 (HIGH) — Savepoint Failure Fallback Swallowing
- **File**: `flexirule/ruleflow/core/engine.py`
- **Function/Class**: `RuleEngine._execute_graph`
- **Description**: Savepoint rollback failure allows partial database writes to remain committed.
- **Technical Analysis**: When an action with `on_error="Rollback"` fails, `engine.py` attempts `frappe.db.rollback(save_point=savepoint_name)`. If this savepoint rollback fails (e.g. because an underlying library call issued an implicit DDL commit or MariaDB savepoint limits were exceeded), the `except` block logs a warning and re-raises the original action exception. The caller catches the exception, but because the savepoint rollback failed, mutations performed before the error remain committed in the active transaction, leading to partial data corruption.
- **Impact**: Permanent data corruption / partial updates saved to the database.
- **Remediation**: In the `except` block of savepoint rollback, immediately issue a full `frappe.db.rollback()` to abort the entire transaction and prevent corrupt state.

---

### Finding FR-DATA-002 (MEDIUM) — Concurrent Active Rule Activation Race Condition
- **File**: `flexirule/ruleflow/doctype/rule/rule.py`
- **Function/Class**: `Rule.validate_single_active_version`
- **Description**: Concurrent requests can activate multiple versions of the same rule simultaneously.
- **Technical Analysis**: `validate_single_active_version` checks if another version is active using `frappe.get_all("Rule", filters={"base_rule_name": self.base_rule_name, "is_active": 1})`. This query does not lock rows with `FOR UPDATE`. If two users or API calls activate different versions of the same rule concurrently, both validation queries pass, resulting in two active versions for the same logical rule. Subsequent document events trigger duplicate rule executions.
- **Impact**: Duplicate execution of rules on document save events.
- **Remediation**: Use `for_update=True` in validation queries or add a database unique constraint on `(base_rule_name, is_active)` where `is_active=1`.

---

### Finding FR-DATA-003 (LOW) — Unindexed `execution_id` in Rule Execution Log
- **File**: `flexirule/ruleflow/doctype/rule_execution_log/rule_execution_log.json`
- **Description**: Missing database index on `execution_id` causes full table scans.
- **Technical Analysis**: `Rule Execution Log` queries logs by `execution_id` to correlate step traces and API responses. The `execution_id` column lacks a database index (`"search_index": 1`), causing slow full table scans as the execution log table grows in production.
- **Impact**: Slow query execution for audit log lookups.
- **Remediation**: Add `"search_index": 1` to `execution_id` in `rule_execution_log.json`.
