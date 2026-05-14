# Execution Engine

The FlexiRule Execution Engine is a deterministic graph executor designed for reliability, observability, and safety.

## Execution Lifecycle

### 1. Triggering
Execution starts when the `RuleCoordinator` receives an event.
- **DocType Events**: Hooked into Frappe's document lifecycle (e.g., `before_save`).
- **Scheduler Events**: Triggered by CRON-based background jobs.
- **Callable Events**: Triggered manually or by other rules (Sub-Rules).

### 2. Eligibility & Pruning
Before running the graph, the coordinator performs several checks:
- **Active Status**: Only active rules are executed (unless in test mode).
- **Event Match**: Ensures the rule is configured for the current event.
- **Watched Fields**: If a rule defines `watched_fields`, it only runs if those fields have changed.
- **Trigger Conditions**: The `compiled_expression` (pre-compiled Python) is evaluated. If it returns `False`, execution stops here.

### 3. Graph Traversal (`RuleEngine`)
If eligible, the `RuleEngine` takes over:
- **Entry Point**: Starts at the **Entry Action** (or the node with no incoming edges).
- **Iteration**: Moves from node to node based on connection logic.
- **Handlers**: Every node type has a corresponding `ActionHandler`. The engine calls `handler.execute(action, context, engine)`.
- **Result & Next Step**: The handler returns a result and the ID of the next node to execute.

### 4. Context & Variables
The `ContextManager` maintains an execution context:
- `doc`: The document being processed.
- `vars`: A key-value store for intermediate data.
- `meta`: Metadata about the current execution (user, timestamp, etc.).

Handlers can read from and write to `vars`. Results can also be mapped back to the `doc` or `vars` using **Mutation Modes**.

---

## Handler Strategy Pattern

The engine uses a pluggable handler system. Built-in handlers include:

| Handler | Responsibility |
| :--- | :--- |
| **Condition** | Evaluates a Python expression and branches (True/False). |
| **Process** | Executes a Python function defined in a `Process` DocType. |
| **Set Value** | Updates a field or variable using a Jinja template. |
| **Query Records** | Performs database lookups (List, Doc, Count, Sum, etc.). |
| **Document Action** | Creates, Updates, or Deletes records; Adds ToDos/Comments. |
| **Notify** | Sends notifications (Toasts, Emails, System Alerts). |
| **Sub-Rule** | Executes another rule as a subroutine. |
| **Loop** | Iterates over a collection, executing a body path for each item. |
| **Stop** | Terminates execution successfully or raises a user-defined error. |

---

## Safety & Reliability

### Cycle Detection
To prevent infinite loops, the engine tracks:
- **Visit Count**: Each node can be visited a maximum of 100 times.
- **Total Iterations**: A single rule execution is limited to 1000 steps.

### Error Handling (`on_error`)
Each action can define how to handle failures:
- **Stop** (Default): Aborts execution and logs the error.
- **Continue**: Logs a warning and proceeds to the next step.
- **Retry**: Re-executes the action with exponential backoff (up to `retry_count`).
- **Rollback**: Rolls back to a database savepoint created before the action.
- **Escalate**: Passes the error up to the caller (useful for Sub-Rules).

### Sandboxing
Rule conditions and templates are evaluated using `SafeFrappeAPI`, a restricted proxy that prevents write operations (like `frappe.db.commit()`) during evaluation.

### Timeout Protection
Rules have a `max_execution_time`. If exceeded, the engine raises a `TimeoutError` to prevent long-running processes from hanging the worker.

---

## Observability

### Execution Tracing
Every step taken by the engine is recorded in a `path_trace`. This includes:
- Action name and type.
- Timestamp and duration.
- Success/Error status.
- Input/Output data (for Processes).

### Rule Execution Log
After execution, the trace and a snapshot of the `vars` are persisted in the **Rule Execution Log** DocType. This allows developers to "replay" or debug rules with the exact data that was present at runtime.
