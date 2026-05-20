---
title: "Execution Engine"
weight: 10
---

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

- **Delay Formula**: `wait_time = 2 ** current_attempt` seconds.
- **Example**: Attempt 1 (2s), Attempt 2 (4s), Attempt 3 (8s).
- **Safety**: Retries are automatically disabled if the context flag `_in_sync_hook` is set, preventing unsafe sleeps in synchronous DocType events.

### Savepoint / Rollback Management

For actions with the `transactional` flag or `on_error: "Rollback"`, the engine uses database savepoints to ensure atomic consistency at the node level:

1.  **Creation**: `frappe.db.savepoint(savepoint_name)` is called before the action handler.
    - **Process naming**: `process_{process_name}_{operation}_{attempt}`
    - **Action naming**: `flexirule_action_{action_id}`
2.  **Execution**: The action handler is executed within a try-except block.
3.  **Rollback**: If an error occurs and rollback is required, `frappe.db.rollback(save_point=...)` is called, reverting only the changes made by that specific action, not the entire transaction.
4.  **Cleanup**: Savepoints are released upon successful completion of the action (only for Process actions).

### Reentrancy Guards

To prevent infinite recursive loops, the `RuleCoordinator` implements a global reentrancy guard:

- **Mechanism**: A request-local registry tracks active executions.
- **Key Format**: `{doctype}:{name}:{event_name}`.
- **Action**: If a key is already present in the local stack, the execution request is denied to prevent stack overflow and cascading updates.

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

| Handler             | Responsibility               | Implementation File |
| :------------------ | :--------------------------- | :------------------ |
| **Condition**       | Python expression branching. | `condition.py`      |
| **Process**         | External logic execution.    | `process.py`        |
| **Assignment**      | Batch state mutation.        | `assignment.py`     |
| **Query Records**   | Database lookups.            | `query_records.py`  |
| **Document Action** | CRUD operations.             | `create_doc.py`     |
| **Notify**          | User communications.         | `simple_actions.py` |
| **Sub-Rule**        | Nested rule execution.       | `sub_rule.py`       |
| **Loop**            | Collection iteration.        | `loop.py`           |
| **Switch**          | Multi-path branching.        | `switch.py`         |

---

## Safety & Reliability

### Cycle Detection

- **Visit Count**: Each node can be visited a maximum of 100 times.
- **Total Iterations**: A single rule execution is limited to 1000 steps.

### Sandboxing

Rule conditions and templates are evaluated using `SafeFrappeAPI`, preventing write operations during evaluation.
