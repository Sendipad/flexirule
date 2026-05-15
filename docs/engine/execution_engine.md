# Execution Engine Deep Dive

The FlexiRule Execution Engine is a deterministic graph executor designed for reliability, observability, and safety.

## Execution Lifecycle

### 1. Triggering
Execution starts when the `RuleCoordinator` receives an event.

### 2. Eligibility & Pruning
Before running the graph, the coordinator performs several checks: Active Status, Event Match, Watched Fields, and Trigger Conditions.

---

## Transaction & Error Management

The engine provides enterprise-grade reliability features for handling failures and maintaining data integrity.

### Exponential Backoff Math
When an action is configured with `on_error: "Retry"`, the engine uses an exponential backoff strategy:
- **Delay Formula**: `wait_time = 2 ^ current_attempt` seconds.
- **Example**: Attempt 1 (2s), Attempt 2 (4s), Attempt 3 (8s).
- **Safety**: Retries are automatically disabled inside synchronous hooks to prevent blocking the web worker.

### Savepoint / Rollback Management
For actions with the `transactional` flag or `on_error: "Rollback"`, the engine uses database savepoints:
1.  **Creation**: `frappe.db.savepoint(savepoint_name)` is called before the action handler.
2.  **Execution**: The handler runs.
3.  **Rollback**: If an error occurs and rollback is required, `frappe.db.rollback(save_point=...)` is called, reverting only the changes made by that specific action, not the entire transaction.
4.  **Release**: On success, the savepoint is released.

### Reentrancy Guards
To prevent infinite recursive loops (e.g., a rule on `Sales Invoice` updating itself and triggering the same rule), the `RuleCoordinator` implements an **Event Reentry Guard**:
- **Mechanism**: A request-local stack tracks `(doctype, name, event)`.
- **Action**: If a triple is already in the stack, the execution is silently skipped.

---

## Incremental Context & Isolation

The engine maintains a strict **Temporal Context Isolation** policy.

### Incremental Context Building
At runtime, the execution context (`vars`, `doc` state) is built **incrementally**.
- **Step-by-Step Availability**: An action can only read variables or document states that have been set by preceding actions in the current execution path.
- **Future Isolation**: An action has no visibility into variables, document updates, or mutations that occur in steps following it.

---

## Handler Strategy Pattern

The engine uses a pluggable handler system.

| Handler | Responsibility | Implementation File |
| :--- | :--- | :--- |
| **Condition** | Python expression branching. | `condition.py` |
| **Process** | External logic execution. | `process.py` |
| **Set Value** | Jinja-based assignment. | `simple_actions.py` |
| **Query Records** | Database lookups. | `query_records.py` |
| **Document Action** | CRUD operations. | `create_doc.py` |
| **Notify** | User communications. | `simple_actions.py` |
| **Sub-Rule** | Nested rule execution. | `sub_rule.py` |
| **Loop** | Collection iteration. | `loop.py` |

---

## Safety & Reliability

### Cycle Detection
- **Visit Count**: Each node can be visited a maximum of 100 times.
- **Total Iterations**: A single rule execution is limited to 1000 steps.

### Sandboxing
Rule conditions and templates are evaluated using `SafeFrappeAPI`, preventing write operations during evaluation.
