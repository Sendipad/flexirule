# DocType Reference

FlexiRule uses several DocTypes to manage rule definitions, reusable logic, and execution history.

## Rule
The central DocType that defines "When" and "What" happens.
- **Trigger Settings**: `document_type`, `trigger_event`, `trigger_type`, `priority`.
- **Condition**: `trigger_condition` (Visual) and `compiled_expression` (Python).
- **Execution Settings**: `execution_mode` (Sync/Async), `max_execution_time`.
- **Visual Data**: A JSON blob containing the coordinates and layout of the graph.
- **Actions**: A child table containing the configuration for each node in the graph.

## Rule Action (Child Table)
Represents a single node in the Rule's graph.
- **Identity**: `action_id`, `action_label`, `action_type`.
- **Operation**: `process_name`, `operation` (for Process actions).
- **Configuration**: `config` (JSON), `target_field`, `value_template`.
- **Flow**: `next_step_if_true`, `next_step_if_false`.
- **Policy**: `on_error`, `retry_count`, `mutation_mode`.

## Process
A container for reusable business logic. Processes are typically "File-Backed," meaning their logic is stored in `.py` and `.js` files in your app.
- **Module**: The Frappe module/app where the code resides.
- **Is Standard**: If enabled, Frappe generates boilerplate code for you.
- **Operations**: A child table defining the individual functions available in this Process.

## Process Operation (Child Table)
Defines a single executable function within a Process.
- **Metadata**: `func_name`, `label`, `description`, `icon`, `color`.
- **Contracts**: `writes_to`, `requires_doc`, `transactional`, `is_terminal`.
- **Schemas**: `config_schema` (inputs) and `output_schema` (results).

## Rule Execution Log
A persistent audit trail of rule executions.
- **Reference**: Links to the `Rule` and the document processed.
- **Metrics**: `status` (Success/Failed), `duration`, `executed_by`.
- **Trace**: `execution_path` (the exact sequence of nodes) and `error_trace`.
- **Snapshot**: `context_snapshot` stores the final state of all variables.

## RuleFlow Settings
Global configuration for the FlexiRule engine.
- **Designer Prefs**: `action_config_mode` (Sidebar vs Modal), `layout_direction`.
- **Engine Prefs**: `default_timeout`, `log_retention_days`.

## Rule Permission
A child table within `Rule` that allows for fine-grained execution control based on Frappe Roles.
