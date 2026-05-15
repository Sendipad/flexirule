# Execution Engine

The FlexiRule Execution Engine is a deterministic graph executor designed for reliability, observability, and safety.

## Execution Lifecycle

### 1. Triggering
Execution starts when the `RuleCoordinator` receives an event.

### 2. Eligibility & Pruning
Before running the graph, the coordinator performs several checks: Active Status, Event Match, Watched Fields, and Trigger Conditions.

### 3. Graph Traversal (`RuleEngine`)
The `RuleEngine` traverses the graph node by node.

---

## Incremental Context & Isolation

The engine maintains a strict **Temporal Context Isolation** policy during execution. This mirrors the design-time safeguards in the Rule Builder.

### Incremental Context Building
At runtime, the execution context (`vars`, `doc` state) is built **incrementally**.
- **Step-by-Step Availability**: An action can only read variables or document states that have been set by preceding actions in the current execution path.
- **Future Isolation**: An action has no visibility into variables, document updates, or mutations that occur in steps following it. This prevents "future-leaking" where a node might incorrectly rely on data that hasn't been generated yet.
- **State Consistency**: By ensuring that an action only sees the "world" as it exists at its specific timestamp in the flow, FlexiRule guarantees predictable and repeatable logic.

---

## Handler Strategy Pattern

The engine uses a pluggable handler system. Built-in handlers include:

| Handler | Responsibility |
| :--- | :--- |
| **Condition** | Evaluates a Python expression and branches (True/False). |
| **Process** | Executes a Python function. Returns data or mutation intents. |
| **Set Value** | Updates a field or variable using a Jinja template. |
| **Query Records** | Performs database lookups (List, Doc, Count, etc.). |
| **Document Action** | CRUD operations on DocTypes. |
| **Notify** | Sends notifications (Toasts, Emails, etc.). |
| **Sub-Rule** | Executes another rule as a subroutine. |
| **Loop** | Iterates over a collection. |
| **Stop** | Terminates execution successfully or with an error. |

---

## Safety & Reliability

### Cycle Detection
- **Visit Count**: Each node can be visited a maximum of 100 times.
- **Total Iterations**: A single rule execution is limited to 1000 steps.

### Error Handling (`on_error`)
Each action can define how to handle failures: Stop, Continue, Retry (with backoff), Rollback (savepoint), or Escalate.

### Sandboxing
Rule conditions and templates are evaluated using `SafeFrappeAPI`, preventing write operations during evaluation.

---

## Observability

### Execution Tracing
Every step taken by the engine is recorded in a `path_trace`, including status, inputs, and outputs.

### Rule Execution Log
After execution, the trace and a snapshot of the `vars` are persisted in the **Rule Execution Log** DocType.
