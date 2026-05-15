# DocType Reference

FlexiRule uses a structured set of DocTypes to manage rule definitions, visual metadata, reusable logic, and execution audit trails. This document provides a detailed breakdown of the fields and their roles within the system.

---

## 1. Rule
The primary container for an automation flow. It defines *when* a logic starts and *what* it aims to achieve.

| Field | Type | Description |
| :--- | :--- | :--- |
| `rule_name` | Data | Unique identifier and primary name of the rule. |
| `is_active` | Check | If disabled, the `RuleCoordinator` will skip this rule entirely. |
| `status` | Select | Lifecycle state: `Draft`, `Active`, `Disabled`, `Invalid`, `Error`, `Archived`. |
| `trigger_type` | Select | `DocType Event` (hooks), `Scheduler Event` (CRON), or `Callable Event` (Sub-Rule). |
| `document_type` | Link | The target DocType this rule monitors (required for DocType Events). |
| `trigger_event` | Select | The specific Frappe hook (e.g., `Before Save`, `Validate`, `On Change`). |
| `priority` | Select | Execution order (0-20). Rules with higher priority run first for the same event. |
| `version` | Int | Auto-incremented version number for historical tracking. |
| `execution_mode` | Select | `Synchronous` (runs in current thread) or `Asynchronous` (offloaded to background). |
| `max_execution_time`| Int | Timeout in seconds to prevent runaway logic or infinite loops. |
| `debug_mode` | Check | Enables verbose logging in the console and execution logs. |
| `trigger_condition` | Code (JSON)| Visual AST representation of the entry filters. |
| `compiled_expression`| Code (Python)| Optimized Python string compiled from the trigger condition. |
| `exposed_as_subrule`| Check | If enabled, this rule appears in the `Sub-Rule` action picker for other rules. |
| `skip_for_roles` | Table | List of roles that, if held by the current user, will cause the rule to be skipped. |
| `actions` | Table | Child table containing the sequence of steps (`Rule Action`). |
| `visual_data` | Code (JSON)| Stores the X/Y coordinates and UI metadata for the visual graph. |
| `last_error` | Text | Stores the last error traceback if the rule failed during its most recent run. |

---

## 2. Rule Action (Child Table)
Represents a single executable node within a Rule's graph.

| Field | Type | Description |
| :--- | :--- | :--- |
| `action_id` | Data | Unique ID for the node (e.g., `root`, `act_1`). Used for graph edges. |
| `action_label` | Data | User-defined label displayed on the node in the builder. |
| `action_type` | Select | Category: `Condition`, `Process`, `Loop`, `Set Value`, `Notify`, `Query Records`, etc. |
| `operation` | Autocomplete | The specific mode for the action (e.g., `Query List`, `Create ToDo`). |
| `config` | Code (JSON)| Parameters for the action (filters, inputs, template segments). |
| `value_template` | Code (Jinja)| Used by `Set Value` and `Notify` to generate dynamic content. |
| `target_field` | Data | Dot-path (e.g., `doc.status`) for the field being updated by the action. |
| `process_name` | Link | Link to a `Process` DocType (used only when `action_type` is `Process`). |
| `mutation_mode` | Select | Logic for applying results: `Set Doc Field`, `Set Context Variable`, etc. |
| `return_variable` | Data | Name for the variable in the context (`vars`) where the result will be saved. |
| `return_type` | Select | Expected data structure: `Single Record`, `List of Records`, `Yes / No`, etc. |
| `on_error` | Select | Error policy: `Stop`, `Continue`, `Retry` (Backoff), `Rollback` (Savepoint). |
| `retry_count` | Int | Number of times to re-attempt the action on failure. |
| `timeout` | Int | Per-node timeout for long-running processes. |
| `next_step_if_true` | Data | The `action_id` of the node to execute on success or "True" result. |
| `next_step_if_false`| Data | The `action_id` of the node to execute on "False" result (Conditions only). |
| `is_async` | Check | If enabled, this specific node is executed in a background queue. |

---

## 3. Process
Defines a file-backed logic module that can be extended via custom Python code.

| Field | Type | Description |
| :--- | :--- | :--- |
| `process_name` | Data | Unique name of the logic group (e.g., `Standard Validation`). |
| `is_standard` | Select | If `Yes`, Frappe syncs the `.py` and `.js` controllers to the app's folder. |
| `module` | Link | The Frappe module/app where the code controllers reside. |
| `default_ref_doctype`| Link | Suggested DocType for this process (used to filter operations in the UI). |
| `operations` | Table | Child table defining functions within the process (`Process Operation`). |

---

## 4. Process Operation (Child Table)
Metadata for an individual Python function within a Process adapter.

| Field | Type | Description |
| :--- | :--- | :--- |
| `func_name` | Data | The actual Python method name in the controller class. |
| `label` | Data | Friendly name shown in the action picker. |
| `writes_to` | Select | Side-effect intent: `None` (Pure), `Context`, `Document`, `Database`. |
| `requires_doc` | Check | If enabled, the function will fail if no document is in context. |
| `transactional` | Check | Wraps the function call in a database savepoint for atomic rollback. |
| `is_terminal` | Check | If enabled, no further actions can be connected after this node. |
| `allows_async` | Check | Flag indicating the logic is safe for background execution. |
| `config_schema` | Code (JSON)| JSON Schema used to auto-generate the builder's configuration form. |
| `output_schema` | Code (JSON)| JSON Schema describing the returned data for autocomplete support. |
| `icon` / `color` | Data | Visual styling for the node on the builder canvas. |

---

## 5. Supporting Data DocTypes

### Rule Execution Log
Captures the full lifecycle of a rule run, including the `execution_id`, `status`, `duration`, `trigger_source`, and a full `execution_path` trace. It also stores a `context_snapshot` for debugging.

### Rule Scheduler
Handles rules with the `Scheduler Event` trigger. It contains settings for frequency (CRON) and the specific Rule to invoke.

### RuleFlow Settings
Global configuration for the entire app. It includes preferences for the designer UI (Sidebar vs Modal config mode) and log retention settings.

### RuleFlow Excluded DocType
A performance optimization list. DocTypes added here (like `Error Log` or `Version`) will never trigger rules, preventing recursive overhead on high-frequency system tables.
