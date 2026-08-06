# Runtime Specification - FlexiRule Execution Engine

This document defines the formal execution semantics, contract requirements, and runtime invariants of the FlexiRule engine.

## 1. Execution Lifecycle

### Trigger Phase
Rules are triggered by three primary sources:
1.  **DocType Events:** Handled via `flexirule/ruleflow/hooks.py`. It maps Frappe methods (e.g., `on_update`) to standard events (e.g., `After Save`).
2.  **Scheduler Events:** Managed by `flexirule/ruleflow/scheduler.py`, executing rules via background jobs.
3.  **Callable Events:** Rules with `trigger_type='Callable Event'`, invoked by other rules or API.

### Eligibility Phase
The `RuleCoordinator` (in `coordinator.py`) performs layered filtering:
-   **Negative Caching:** `has_active_rules` quickly exits if the (DocType, Event) pair has no active rules in the Redis registry.
-   **Registry Lookup:** Specs for active rules are retrieved.
-   **Watched Fields:** For `FIELD_FILTER_EVENTS`, rules are skipped if none of their `watched_fields` intersect with `_get_changed_fields(doc)`.
-   **Re-entry Guard:** `_event_reentry_guard` prevents recursive loops for the same (Doc, Event) within a request.
-   **Condition Evaluation:** `check_eligibility` evaluates the `compiled_expression` using `frappe.safe_eval`.

### Execution Phase (The Graph)
The `RuleEngine` (in `engine.py`) drives the action graph:
-   **Start Node Deduction:** Finds the "Entry Action" or deduces the root by identifying nodes with no incoming edges.
-   **Stateful Traversal:** `_execute_graph` tracks `node_visits` for loop safety and manages the `path_trace`.
-   **Handler Registry:** Execution is delegated to `ActionHandler` implementations via `HandlerRegistry`. Built-in handlers include:
    -   **Sub-Rule:** Uses `SubRuleVarsOverlay` for copy-on-write context isolation.
    -   **Loop:** Manages iteration state in `vars._loops`.
    -   **Assignment:** Performs batch mutations using `AssignmentOperatorRegistry`.
    -   **Process:** Dispatches to V2 declarative runtime.
-   **Context Management:** `vars` are transient and scoped to the execution.

### Logging Phase (Forensic Integrity)
Logging is designed to survive transaction rollbacks:
-   **Enqueued Persistence:** `_save_execution_log` enqueues `persist_execution_log` to a background worker.
-   **Separate Transaction:** The background worker uses a separate DB connection and performs an explicit `frappe.db.commit()`.
-   **Trace Data:** Logs include `execution_path` (JSON), `context_snapshot` (JSON), and `error_trace` for semantic replay.

## 2. Declarative Runtime (V2) Contract

The V2 runtime (in `process_runtime_v2.py` and `process_contract_v2.py`) enforces strict boundaries on Process operations. It is versioned (currently `PROCESS_CONTRACT_V2_VERSION = 2`).

### Configuration Schema
Every operation must define a JSON Schema for its input parameters. The `ProcessOperationExecutor` performs validation using a customized `jsonschema` validator that handles Frappe-specific types (e.g., 0/1 for booleans).

### Result Schema
Operations must return data conforming to a declared output schema (`result_schema`). The executor validates the `OperationResult.data` against this schema post-execution.

### Mutation Intents
Operations return `OperationResult` which can include a list of `MutationIntent` objects.
-   **Mutation Modes:** Supported modes include `Set Doc Field`, `Update Context Variable`, etc.
-   **Validation:** Mutations are validated against the operation's `policy.allowed_mutations`.
-   **Safety:** The `ProcessOperationExecutor` blocks `writes_to` (Document/Database) capabilities during "After" events (e.g., `After Save`) for synchronous rules to prevent side-effect loops.

### Capabilities & Policies
Operations declare their capabilities:
-   `requires_doc`: Boolean, requires a document in context.
-   `writes_to`: `None`, `Context`, `Document`, or `Database`.
-   `transactional`: Wraps execution in a database savepoint.
-   `allows_async`: Whether the operation can be offloaded to a background job.

## 3. Expression System & Security Model

The system utilizes a multi-layered expression evaluation model to balance flexibility and security.

### Layer 1: Compiled Resolvers (`ValueResolver`)
The preferred method for dynamic values. It converts structured configurations (Math, Date formulas, Aggregations) into a graph of `CompiledResolver` objects.
-   **Security:** High. Logic is hardcoded in resolver classes, avoiding arbitrary execution.
-   **Performance:** High. Request-local memoization and avoidance of string parsing at runtime.

### Layer 2: `safe_eval` with Restricted Proxies
For more complex logic, `frappe.safe_eval` is used with significant security constraints:
-   **SafeFrappeAPI:** A restricted proxy for `frappe` that blocks all write operations (`db_set_value`, `delete_doc`, `commit`, etc.).
-   **ReadOnlyDocument:** A proxy that prevents mutation of document fields in "Pure" evaluation contexts.
-   **Scoped Globals:** Python 3 generator/comprehension scoping is handled by promoting `safe_locals` to globals, ensuring helper functions like `check_link_match` are available.

### Layer 3: Security Boundaries
-   **Mutation Paths:** All mutations must be explicitly routed through `Assignment` nodes or `MutationIntent` results from V2 Processes.
-   **Protected Paths:** System paths like `meta.*`, `frappe.*`, and `rule.*` are protected from mutation in `AssignmentHandler`.
-   **Pure Evaluators:** `evaluator.py` and `runtime_eval.py` provide side-effect-free evaluation of conditions.

## 4. Frontend-Backend Contract (Builder)

The Visual Builder and Rule Engine are unified by a shared contract.

### Contract DTO (`get_contract_dto`)
The backend provides a comprehensive Data Transfer Object to the frontend:
-   **Action Type Contract:** Defines icons, colors, terminal status, and required fields for each action type.
-   **Operation Contract:** Provides field-level overrides and validation scripts for specific operations.
-   **Trigger Type Contract:** Manages visibility of Rule fields (e.g., Cron vs DocType Event).

### Builder Topology (`useGraphStore`)
The frontend manages the graph as a collection of nodes and edges:
-   **Synchronization:** `sync_actions_to_graph` maps the flat `Rule Action` child table to the visual graph.
-   **Serialization:** On save, the graph is topologically sorted to ensure a deterministic execution order in the backend database.
-   **Visual Persistence:** Node positions and edge metadata are stored in the `visual_data` JSON field on the `Rule` DocType.

### Validation Pipeline
Validation is performed at multiple layers:
1.  **Frontend (Contract):** Immediate feedback based on `ACTION_TYPE_CONTRACT`.
2.  **API (`validate_rule_document`):** Pre-save validation of the entire rule payload in "draft" or "full" mode.
3.  **Backend (`Rule.validate`):** Compilation of conditions and structural integrity checks.

## 5. Transactional Integrity
-   **Atomic Execution:** Rules triggered by synchronous Frappe hooks run within the same database transaction.
-   **Savepoints:** The engine uses database savepoints (`flexirule_action_{id}`) for action-level error handling (Rollback mode), allowing local recovery without necessarily aborting the entire request.
-   **Fail-Fast:** By default, unhandled exceptions in a Rule will propagate and abort the outer Frappe transaction to preserve data consistency.

## 4. Cycle and Recursion Control
-   **Local Guard:** `_event_reentry_guard` (in `coordinator.py`) uses a request-local set to prevent a single document from re-triggering the same event within the same request.
-   **Iteration Limit:** The `RuleEngine` enforces a hard limit on total steps (currently 1000) and visits per node (currently 100) via `node_visits` tracking in `_execute_graph`.
-   **Cross-Rule Stack:** The `Sub-Rule` handler maintains an `execution_stack` in the `meta` context to detect cycles across different rules.
-   **Future:** Transitioning to a global execution lineage tracker to detect complex cross-document "ping-pong" cycles.
