# DocType Reference

FlexiRule uses a structured set of DocTypes to manage rule definitions, visual metadata, reusable logic, and execution audit trails.

## 1. Rule
The primary DocType that defines a visual automation flow. It serves as the container for both the business intent (Triggers) and the execution logic (Actions).

### Key Fields
- **Rule Name (`rule_name`)**: Unique identifier.
- **Trigger Type (`trigger_type`)**: `DocType Event`, `Scheduler Event`, or `Callable Event`.
- **Document Type (`document_type`)**: The target Frappe DocType this rule monitors.
- **Trigger Event (`trigger_event`)**: The specific hook (e.g., `Before Save`).
- **Priority (`priority`)**: Execution order (0-20).
- **Execution Mode (`execution_mode`)**: `Synchronous` or `Asynchronous`.
- **Exposed As Sub-Rule (`exposed_as_subrule`)**: Makes the rule visible to other rules.
- **Visual Data (`visual_data`)**: Stores canvas layout and node coordinates.

---

## 2. Rule Action (Child Table)
Represents a single node in the visual graph.

### Key Fields
- **Action ID (`action_id`)**: Unique ID within the graph.
- **Step Type (`action_type`)**: Category (e.g., `Condition`, `Process`, `Loop`).
- **Label (`action_label`)**: Display name on the canvas.
- **On Error (`on_error`)**: Failure policy (`Stop`, `Continue`, `Retry`, `Rollback`).
- **Mutation Mode (`mutation_mode`)**: How to apply results (e.g., `Set Doc Field`).
- **Next Step (`next_step_if_true`)**: Primary continuation path.
- **Else Step (`next_step_if_false`)**: Path for False/Error branches.

---

## 3. Process & Process Operation
A framework for extending FlexiRule with custom Python logic.
- **Process**: Groups functions into a named, file-backed module.
- **Process Operation**: Defines the metadata for each function, including **Config Schemas** for UI generation and **Side-Effect Intents** (`Writes To`).

---

## 4. Rule Execution Log
A persistent audit trail for every execution. It stores the `status`, `duration`, a detailed `execution_path` trace, and a `context_snapshot` of all variables at the end of the run.

---

## 5. Supporting DocTypes

### Rule Scheduler
Manages the execution of rules with the `Scheduler Event` trigger type. It allows for CRON-based automation.

### Rule Permission
A child table within the `Rule` DocType that enables role-based execution control.

### RuleFlow Settings
Global system configuration, including designer preferences (Sidebar vs Modal) and log retention policies.

### Data Review Task & Related Document
Part of the advanced data management suite, used for human-in-the-loop validation tasks triggered by rules.

### RuleFlow Excluded DocType
A blacklist of DocTypes that should never trigger rules (e.g., Log files, temporary tables) to prevent performance issues.
