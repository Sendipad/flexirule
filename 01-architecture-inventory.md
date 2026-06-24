# Audit Report 01: Architecture & Action Inventory

## 1. Action Handler Mapping (Backend)
The FlexiRule engine uses a Strategy pattern via `HandlerRegistry`. All handlers reside in `flexirule/ruleflow/core/action_handlers/`.

| Action Type | Handler File | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Entry Action** | `simple_actions.py` | Active | Root node of all flows. |
| **Condition** | `condition.py` | Active | Boolean branching via `frappe.safe_eval`. |
| **Process** | `process.py` | Active | Dynamic operation execution via Process DocType. |
| **Loop** | `loop.py` | Active | Iterator support for lists/queries. |
| **Stop** | `simple_actions.py` | **Partial** | Supports Success/Error. UI configuration is missing. |
| **Switch** | `switch.py` | **Inactive** | Handler exists but Action Type is disabled in UI. |
| **Wait** | `simple_actions.py` | Active | Pause execution (Async only). |
| **Sub-Rule** | `sub_rule.py` | Active | Recursion depth capped at 2. |
| **Assignment** | `assignment.py` | Active | Supports `doc.*` and `vars.*`. No deep paths. |
| **Notify** | `simple_actions.py` | Active | Supports Toast, Email, Provider. |
| **Raise Error** | `simple_actions.py` | Active | Direct exception raising. |
| **Query Records** | `query_records.py` | Active | 10 query modes (Count, Sum, etc). |
| **Document Action** | `create_doc.py` | Active | CRUD + ToDo/Comment convenience. |

## 2. Global Runtime Constraints
- **Total Iteration Limit:** 1000 nodes (Prevents runaway loops).
- **Sub-Rule Depth:** 2 levels (Hardcoded in `engine.py`).
- **Concurrent Rules:** Max 21 active rules per DocType (Limited by Frappe Priority field 0-20).
- **Concurrency:** `on_error: Retry` is prohibited in synchronous hooks (Validate/Before Save).

## 3. Database Consistency
- **Transactional Rollback:** Verified. Rules running in `Before Save` or `Validate` trigger a standard DB rollback on `Stop (Error)` or unhandled exceptions.
- **Savepoints:** `Document Action` uses savepoints for individual node rollbacks if `on_error: Rollback` is selected.
