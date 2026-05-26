# Doctypes<no value>

# DocType Reference

FlexiRule uses a structured set of DocTypes to manage rule definitions, visual metadata, reusable logic, and execution audit trails. This document provides a exhaustive breakdown of all fields for every DocType in the system.

---

## 1. Rule

The primary container for an automation flow. It defines _when_ a logic starts and _what_ it aims to achieve.

| Field                 | Type   | Label                    | Description                                                                     |
| :-------------------- | :----- | :----------------------- | :------------------------------------------------------------------------------ |
| `rule_name`           | Data   | Rule Name                | Unique identifier and primary name of the rule.                                 |
| `is_active`           | Check  | Is Active                | If disabled, the `RuleCoordinator` will skip this rule entirely.                |
| `exposed_as_subrule`  | Check  | Exposed As Sub-Rule      | If enabled, this rule appears in the `Sub-Rule` action picker for other rules.  |
| `priority`            | Select | Priority                 | Execution order (0-20). Higher values run first.                                |
| `version`             | Int    | Version                  | Auto-incremented version number for historical tracking.                        |
| `status`              | Select | Status                   | Lifecycle state: `Draft`, `Active`, `Disabled`, `Invalid`, `Error`, `Archived`. |
| `trigger_type`        | Select | Trigger Type             | `DocType Event`, `Scheduler Event`, or `Callable Event`.                        |
| `document_type`       | Link   | Document Type            | The target DocType this rule monitors.                                          |
| `trigger_event`       | Select | Trigger Event            | The specific Frappe hook (e.g., `Before Save`, `Validate`).                     |
| `trigger_condition`   | Code   | Trigger Condition (JSON) | Visual AST representation of the entry filters.                                 |
| `compiled_expression` | Code   | Trigger Filters (Python) | Optimized Python string compiled from the trigger condition.                    |
| `execution_mode`      | Select | Execution Mode           | `Synchronous` or `Asynchronous`.                                                |
| `max_execution_time`  | Int    | Max Execution Time       | Timeout in seconds to prevent runaway logic.                                    |
| `debug_mode`          | Check  | Debug Mode               | Enables verbose logging.                                                        |
| `module`              | Link   | Module                   | The Frappe module this rule belongs to (for export).                            |
| `skip_for_roles`      | Table  | Skip for Roles           | Rule will NOT execute for users with these roles.                               |
| `description`         | Text   | Description              | Brief explanation of what this rule does.                                       |
| `permissions`         | Table  | Permissions              | Define role-based permissions for this rule.                                    |
| `actions`             | Table  | Actions                  | Child table containing the sequence of steps (`Rule Action`).                   |
| `visual_data`         | Code   | Visual Data              | Stores the X/Y coordinates and UI metadata for the visual graph.                |
| `last_error`          | Text   | Last Error               | Stores the last error traceback if the rule failed.                             |

---

## 2. Rule Action (Child Table)

Represents a single executable node within a Rule's graph.

| Field                     | Type         | Label                        | Description                                                  |
| :------------------------ | :----------- | :--------------------------- | :----------------------------------------------------------- |
| `action_id`               | Data         | Action ID                    | Unique ID for the node. Used for graph edges.                |
| `action_label`            | Data         | Label                        | User-defined label displayed on the node.                    |
| `action_type`             | Select       | Step Type                    | Category: `Condition`, `Process`, `Loop`, `Assignment`, etc. |
| `process_name`            | Link         | Process                      | Link to a `Process` DocType.                                 |
| `rule`                    | Link         | Rule                         | Link to a sub-rule (for `Sub-Rule` type).                    |
| `operation`               | Autocomplete | Mode                         | Operation mode for this action.                              |
| `is_enabled`              | Check        | Enabled                      | Whether this specific step is active.                        |
| `on_error`                | Select       | On Error                     | Policy: `Stop`, `Continue`, `Retry`, `Rollback`, `Escalate`. |
| `is_async`                | Check        | Async                        | Execute in background queue.                                 |
| `retry_count`             | Int          | Retry Count                  | Number of retries on failure (exponential backoff).          |
| `timeout`                 | Int          | Timeout (seconds)            | Maximum execution time for this specific node.               |
| `skip_permissions`        | Check        | Ignore Permissions           | Skip permission checks (requires audit reason).              |
| `permission_audit_reason` | Small Text   | Permission Audit Reason      | Why permission checks are bypassed.                          |
| `skip_conditions`         | Check        | Skip Trigger Check           | For sub-rules, skip their entry conditions.                  |
| `input_source`            | Select       | Input Source                 | `Context Doc`, `Context Variable`, or `Both`.                |
| `reference_doctype`       | Link         | Reference DocType            | Target DocType for query or document creation.               |
| `reference_docname`       | Dynamic Link | Reference Document           | Specific document reference.                                 |
| `condition_json`          | Code         | Condition (JSON)             | Condition expression for `Condition` type.                   |
| `compiled_expression`     | Code         | Compiled Expression (Python) | Python version of the condition.                             |
| `target_field`            | Data         | Target Field                 | Field to update (e.g., `doc.status`).                        |
| `value_template`          | Code         | Action Template              | Jinja template for values or notifications.                  |
| `config`                  | Code         | Configuration (JSON)         | Parameters for the action.                                   |
| `mutation_mode`           | Select       | Result Handling              | How to apply results (e.g., `Set Doc Field`).                |
| `return_variable`         | Data         | Save Result As               | Name to save this step's result under.                       |
| `return_type`             | Select       | Result Type                  | Expected data structure.                                     |
| `resolved_output_schema`  | Code         | Result Fields                | JSON schema for return keys.                                 |
| `next_step_if_true`       | Autocomplete | Next Step                    | Node ID to execute on success.                               |
| `next_step_if_false`      | Data         | Else Step                    | Node ID to execute on failure (Conditions).                  |
| `description`             | Text         | Description                  | Documentation for this action.                               |

---

## 3. Process

Defines a file-backed logic module that can be extended via custom Python code.

| Field                 | Type   | Label                     | Description                                         |
| :-------------------- | :----- | :------------------------ | :-------------------------------------------------- |
| `process_name`        | Data   | Process Name              | Unique identifier.                                  |
| `is_standard`         | Select | Is Standard               | If `Yes`, code is synced to the app's directory.    |
| `module`              | Link   | Module                    | The Frappe module/app for controllers.              |
| `default_ref_doctype` | Link   | Default Reference DocType | Used to filter operations in the UI.                |
| `description`         | Data   | Description               | Summary of the process purpose.                     |
| `operations`          | Table  | Operations                | Functions within the process (`Process Operation`). |

---

## 4. Process Operation (Child Table)

Metadata for an individual function within a Process.

| Field                | Type       | Label              | Description                                                    |
| :------------------- | :--------- | :----------------- | :------------------------------------------------------------- |
| `func_name`          | Data       | Function Name      | The actual Python method name.                                 |
| `label`              | Data       | Display Label      | Friendly name for the builder.                                 |
| `enabled`            | Check      | Enabled            | Whether the function can be used.                              |
| `visible_in_builder` | Check      | Visible in Builder | Visibility in the action selector.                             |
| `description`        | Small Text | Description        | Tooltip shown in the builder.                                  |
| `writes_to`          | Select     | Writes To          | Side-effect intent: `None`, `Context`, `Document`, `Database`. |
| `requires_doc`       | Check      | Requires Document  | Needs `context['doc']` to be present.                          |
| `can_stop_save`      | Check      | Can Stop Save      | May throw ValidationError to abort database save.              |
| `is_terminal`        | Check      | Terminal           | No next action allowed after this node.                        |
| `allows_async`       | Check      | Allows Async       | Safe for background execution.                                 |
| `transactional`      | Check      | Transactional      | Wrap execution in database savepoint.                          |
| `has_side_effect`    | Check      | Has Side Effects   | Mark if destructive or external effects exist.                 |
| `for_doctype`        | Link       | For DocType        | Restrict to specific DocType.                                  |
| `doctype_filters`    | Code       | DocType Filters    | Frappe-style filters for availability.                         |
| `reads_vars`         | Code       | Reads Variables    | Expected input variables (DocField style).                     |
| `writes_vars`        | Code       | Writes Variables   | Output variables produced (DocField style).                    |
| `config_schema`      | Code       | Config Schema      | JSON Schema for node inputs.                                   |
| `output_schema`      | Code       | Output Schema      | JSON Schema for return value.                                  |
| `action_overrides`   | Code       | Action Overrides   | Optional override contract JSON.                               |
| `icon`               | Data       | Icon               | CSS class for node icon.                                       |
| `color`              | Data       | Color              | Hex code for node color.                                       |

---

## 5. Rule Execution Log

Audit trail for every rule execution.

| Field               | Type         | Label              | Description                             |
| :------------------ | :----------- | :----------------- | :-------------------------------------- |
| `rule`              | Link         | Rule               | Reference to the Rule DocType.          |
| `execution_id`      | Data         | Execution ID       | Unique ID for the specific run.         |
| `rule_version`      | Int          | Rule Version       | Version of the rule at execution time.  |
| `status`            | Select       | Status             | `Success`, `Failed`, or `Stopped`.      |
| `duration`          | Float        | Duration (s)       | Execution time in seconds.              |
| `trigger_source`    | Data         | Trigger Source     | Context (e.g., `Doc: INV-001`).         |
| `reference_doctype` | Link         | Reference DocType  | The DocType being processed.            |
| `reference_docname` | Dynamic Link | Reference Document | The specific record name.               |
| `executed_by`       | Link         | Executed By        | The user who triggered the rule.        |
| `scheduler`         | Link         | Scheduler          | Link to `Rule Scheduler` if applicable. |
| `batch_id`          | Data         | Batch ID           | ID for batch process grouping.          |
| `batch_index`       | Int          | Batch Index        | Position within the batch.              |
| `batch_total`       | Int          | Batch Total        | Total items in the batch.               |
| `message`           | Small Text   | Message            | Summary result or error message.        |
| `execution_path`    | Code         | Execution Path     | JSON trace of nodes and results.        |
| `context_snapshot`  | Code         | Context Snapshot   | JSON dump of variables (`vars`).        |
| `error_trace`       | Code         | Error Trace        | Python traceback on failure.            |

---

## 6. Rule Scheduler

Manages time-based execution of rules.

| Field            | Type     | Label          | Description                                     |
| :--------------- | :------- | :------------- | :---------------------------------------------- |
| `rule`           | Link     | Rule           | The Rule to execute.                            |
| `stopped`        | Check    | Stopped        | Disable the schedule.                           |
| `frequency`      | Select   | Frequency      | `Hourly`, `Daily`, `Weekly`, `Monthly`, `Cron`. |
| `cron_format`    | Data     | Cron Format    | Standard Crontab syntax.                        |
| `filter_doctype` | Link     | Filter DocType | DocType to query for batch processing.          |
| `filter_json`    | Code     | Filter (JSON)  | Frappe filter for finding records.              |
| `batch_size`     | Int      | Batch Size     | Documents per execution batch.                  |
| `on_error`       | Select   | On Error       | `Skip` (continue batch) or `Stop`.              |
| `last_execution` | Datetime | Last Execution | Timestamp of previous run.                      |
| `next_execution` | Datetime | Next Execution | Calculated upcoming run time.                   |
| `last_error`     | Text     | Last Error     | Error from the most recent run.                 |

---

## 7. RuleFlow Settings

Global application configuration.

| Field                         | Type   | Label                        | Description                           |
| :---------------------------- | :----- | :--------------------------- | :------------------------------------ |
| `enable_debug_logging`        | Check  | Enable Debug Logging         | System-wide verbose logs.             |
| `log_retention_days`          | Int    | Log Retention (Days)         | Retention period for execution logs.  |
| `max_execution_time_default`  | Int    | Default Max Execution Time   | System-wide rule timeout.             |
| `allow_async_actions`         | Check  | Allow Async Actions          | Globally enable background steps.     |
| `excluded_doctypes`           | Table  | Excluded DocTypes            | Blacklist of high-frequency DocTypes. |
| `action_config_mode`          | Select | Action Configuration Mode    | `Sidebar` or `Dialog`.                |
| `open_config_on`              | Select | Open Configuration On        | `Click` or `Double Click`.            |
| `theme`                       | Select | Canvas Theme                 | `System`, `Light`, `Dark`.            |
| `layout_direction`            | Select | Auto-Layout Direction        | `Left to Right` or `Top to Bottom`.   |
| `sidebar_position`            | Select | Sidebar Position             | `Left` or `Right`.                    |
| `enable_edge_insertion`       | Check  | Enable Edge Insertion        | Show "+" button on connections.       |
| `require_approval_for_active` | Check  | Require Approval to Activate | Enable activation workflow.           |
| `allow_editing_active`        | Check  | Allow Editing Active Rules   | Toggle warning for active rules.      |

---

## 8. Other Supporting DocTypes

### Rule Permission (Child Table)

- `role` (Link): Frappe Role allowed to execute the rule.
- `can_execute` (Check): Permission flag.

### Data Review Task

- `task_type` (Select): `Duplicate Review`, `Data Quality`, etc.
- `status` (Select): `Open`, `In Progress`, `Resolved`, `Rejected`.
- `priority` (Select): `Low` to `Critical`.
- `source_doctype` / `source_document`: The record being reviewed.
- `similarity_score` (Percent): Match score for duplicate detection.
- `context_json` (Code): Snapshot of context when task was created.
- `related_documents` (Table): List of `Data Review Related Document`.

### RuleFlow Excluded DocType (Child Table)

- `document_type` (Link): The DocType to blacklist from rule evaluation.
