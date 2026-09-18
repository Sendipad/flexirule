# Process Framework Audit — FlexiRule

## 1. Process Architecture Overview

FlexiRule features a modular **Process Framework** designed to allow custom domain logic (enrichment, validation, deduplication, batch processing) to be registered as modular plugin adapters:
1. **Process DocType**: Metadata record defining process names, modules, and file paths.
2. **Process Operation Child DocType**: Defines individual process methods (`func_name`), required parameters, UI labels, icons, and behavior contracts (`requires_doc`, `writes_to`, `transactional`, `has_side_effect`, `allows_async`).
3. **Filesystem Package Structure**: Python backend code located under `flexirule/ruleflow/process/<process_name>/`.
   - `<process_name>.py`: Python execution dispatcher.
   - `<process_name>.json`: Operations metadata schema.
   - `<process_name>.js`: Frontend builder adapter.
4. **Process Sync**: `process_sync.py` automatically scans filesystem processes during `after_migrate` or `bench migrate` and syncs them into the database.

---

## 2. Detailed Process Plugin Audits

The application contains 4 core built-in Process packages under `flexirule/ruleflow/process/`:
1. `validation` (Field and document cross-validation)
2. `enrichment` (Data fetching, calculated fields, external API enrichment)
3. `deduplication` (Duplicate record checking and matching)
4. `batch` (Bulk table processing)

---

## 3. Detailed Findings

### Finding FR-PROC-001 (MEDIUM) — Silent Failure in Process Filesystem Sync
- **File**: `flexirule/ruleflow/core/process_sync.py`
- **Function/Class**: `sync_process_from_folder`
- **Description**: Filesystem sync swallows import and JSON syntax errors.
- **Technical Analysis**: When `sync_process_from_folder` reads `<process_name>.json` or imports `<process_name>.py`, syntax or schema errors are caught with a generic `except Exception as e:` and logged as warnings. Migration continues without throwing an error, leaving partial or missing Process DocType records in the database. When a rule executes an action targeting the un-synced process, execution fails at runtime with `Process not found`.
- **Impact**: Unnoticed migration failures leading to runtime rule execution crashes.
- **Remediation**: Raise explicit `ProcessSyncError` during `after_migrate` if a built-in process fails to sync.

---

### Finding FR-PROC-002 (MEDIUM) — Contract Discrepancy in `ProcessOperation` Async Execution
- **File**: `flexirule/ruleflow/core/process_runtime_v2.py`
- **Function/Class**: `execute_process_operation_v2`
- **Description**: Asynchronous execution flag in `Process Operation` child table is ignored by `ProcessHandler`.
- **Technical Analysis**: `Process Operation` defines `allows_async` (Check) and `is_async` on `Rule Action`. However, `ProcessHandler.execute()` executes process operations synchronously regardless of `allows_async` settings, bypassing background queue dispatching.
- **Impact**: Long-running process operations execute synchronously in HTTP request threads, causing HTTP gateway timeouts.
- **Remediation**: In `ProcessHandler.execute`, check `action.is_async` and `operation.allows_async` and dispatch via `frappe.enqueue()` when enabled.

---

### Finding FR-PROC-003 (LOW) — Missing Output Schema Validation in Process Adapter
- **File**: `flexirule/ruleflow/core/engine.py`
- **Function/Class**: `RuleEngine._validate_output_against_schema`
- **Description**: Schema validation for process operations only checks top-level keys.
- **Technical Analysis**: `_validate_output_against_schema` performs shallow key existence checks against `output_schema` JSON. Nested schema structures (such as arrays of child objects or typed properties) are ignored, providing false confidence that process operation output conforms to expected schema formats.
- **Impact**: Uncaught data structure mismatches when process outputs feed downstream actions.
- **Remediation**: Integrate `jsonschema.validate` for deep schema validation against `output_schema`.
