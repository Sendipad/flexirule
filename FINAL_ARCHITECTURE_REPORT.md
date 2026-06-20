# Final Architectural Analysis: FlexiRule

This report provides a comprehensive architectural overview of the FlexiRule system, acting as the definitive mental model for a production-grade No-Code Rule Orchestration Engine.

## 1. Rule Lifecycle (Trigger → Execution → Logging)

### What exists
A multi-stage pipeline that transitions from standard Frappe database hooks to a deterministic, graph-based execution context.

### How it works internally
1.  **Trigger:** `hooks.py` listens to all DocType events and routes them to `RuleCoordinator`.
2.  **Eligibility:** `RuleCoordinator` uses a layered filtering strategy:
    -   **Registry:** Fast lookup in a Redis-backed compiled registry.
    -   **Watched Fields:** Change-based filtering (diffing `doc` vs `old_doc`) for `Before Save` events.
    -   **Compiled Conditions:** Evaluating `compiled_expression` (Python) using `safe_eval`.
3.  **Execution:** `RuleEngine` traverses the action graph, dispatching to `ActionHandler` instances via a strategy registry.
4.  **Logging:** `RuleEngine` enqueues `persist_execution_log` to background workers. These workers use separate database connections and explicit commits to ensure log persistence even if the main transaction rolls back.

### Why it exists
To centralize and visualize business logic that is traditionally hidden in fragmented Python hooks, providing full traceability and deterministic outcomes.

### Risks / technical debt
-   **Hook Overhead:** Listening to `*` for all events can add latency if the negative cache (registry) isn't highly optimized.
-   **Log Bloat:** High-frequency rules can generate massive amounts of log data, requiring aggressive cleanup tasks.

### Suggested improvement
-   Implement event-specific hook registration in `hooks.py` dynamically if possible, or further optimize the `RuleCoordinator` entry point to exit in micro-seconds for non-rule DocTypes.

---

## 2. Execution Engine Internals

### What exists
A stateless, graph-traversal engine (`RuleEngine`) that manages execution context and drives action handlers.

### How it works internally
-   **Graph Traversal:** Uses topological sorting for order and `node_visits` tracking for infinite loop protection.
-   **Context Isolation:** `Sub-Rule` handlers use `SubRuleVarsOverlay` (copy-on-write) to prevent child rules from unintentionally polluting parent state.
-   **Error Handling:** Supports "Continue," "Retry" (with exponential backoff), "Rollback" (to savepoint), and "Escalate" strategies.

### Why it exists
To provide a robust, programmable runtime that guarantees the "What you see is what executes" promise while protecting the system from common runtime failures (loops, state pollution).

### Risks / technical debt
-   **Recursion Depth:** `MAX_SUB_RULE_DEPTH` is currently hardcoded (2), which might be too restrictive for complex enterprise workflows.
-   **Cross-Doc Cycles:** Currently relies on local guards; doesn't yet have a global lineage tracker for "Doc A -> Doc B -> Doc A" cycles.

### Suggested improvement
-   Introduce a `GlobalExecutionContext` that tracks event lineage across document boundaries to prevent ping-pong cycles.

---

## 3. Frontend Builder Architecture

### What exists
A Vue 3 + VueFlow application integrated into the Frappe Desk, driven by a strict backend contract.

### How it works internally
-   **Contract DTO:** The frontend hydrates its registry (nodes, ops, schemas) from `api.get_contract_dto`.
-   **Pinia Stores:** `useGraphStore` manages visual topology; `useRuleStore` manages document lifecycle.
-   **Serialization:** The visual graph is topologically sorted on save and persisted as flat `Rule Action` rows + `visual_data` JSON.

### Why it exists
To provide a low-friction, high-fidelity environment for logic design that maps 1:1 to the backend execution model.

---

## 4. Process System (V2 Contract Runtime)

### What exists
A schema-first, declarative runtime for business logic operations, transitioning away from file-backed Python modules.

### How it works internally
-   **Contract V2:** Every operation defines `config_schema`, `result_schema`, and `capabilities`.
-   **Executor:** `ProcessOperationExecutor` validates inputs before calling the adapter and validates outputs after.
-   **Mutation Intents:** Operations return intent objects rather than performing direct database writes, allowing the engine to control the side-effect lifecycle.

### Why it exists
To enforce strict boundaries, improve security, and enable cross-platform execution (Python/JS) of process logic.

### Risks / technical debt
-   **Migration Path:** V1 processes are still present and lack the safety of V2.

### Suggested improvement
-   Provide a migration tool/decorator that allows V1 modules to "upgrade" to V2 by simply providing a schema and capability map.

---

## 5. Performance + Caching Model

### What exists
A multi-layered caching strategy designed for high-frequency rule execution.

### How it works internally
1.  **Request Local:** Memoization of registry lookups and changed field sets.
2.  **Redis:** The `RuleCoordinator` registry and `CompiledResolver` objects are cached across requests.
3.  **Database:** The definitive source of truth, used only for cache rebuilds.

### Why it exists
Execution of visual rules must not significantly degrade standard ERPNext transaction times.

---

## 6. Expression System & Security

### What exists
A hybrid model featuring `ValueResolver` (Compiled Resolvers) and `safe_eval` with restricted proxies.

### How it works internally
-   **ValueResolver:** Compiles Math, Date, and String formulas into optimized Python objects.
-   **Proxies:** `SafeFrappeAPI` and `ReadOnlyDocument` prevent unauthorized mutations during condition and assignment evaluation.

### Why it exists
To move toward a unified DSL (Domain Specific Language) that is secure by default and doesn't require "Python skills" or "Security clearance" to write.

### Suggested improvement
-   Complete the transition to a full DSL parser that eliminates the need for `safe_eval` entirely for user-defined expressions.
