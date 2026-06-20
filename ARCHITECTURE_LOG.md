# Architecture Log - FlexiRule

This log tracks the evolution of the FlexiRule architecture, capturing key decisions, shifts in paradigms, and the reasoning behind system-level changes.

## Current State: Hybrid V1/V2 Runtime

### What exists
FlexiRule currently operates with a hybrid execution model.
- **Rule Engine (V1 core)** handles DocType events, triggering graphs of `Rule Action` nodes.
- **Process System (V1)** uses file-backed Python modules for operation logic.
- **Declarative Runtime (V2)** is being introduced (seen in `process_runtime_v2.py`) to move toward schema-validated, declarative execution.

### How it works internally
1.  **Triggers:** `RuleCoordinator` listens to Frappe hooks (`before_save`, `validate`, etc.) and filters applicable rules using a compiled Redis-backed registry.
2.  **Execution:** `RuleEngine` traverses the action graph. It uses a `HandlerRegistry` to dispatch actions (Conditions, Processes, Assignments, etc.) to specific handlers.
3.  **Processes:** Currently, "Standard Processes" load Python functions dynamically. V2 processes use `OperationInvocation` and `ProcessOperationExecutor` with strict JSON schema validation.

### Why it exists
The system was designed to consolidate fragmented Frappe hooks into a single, visual orchestration layer to solve "hook-hell." The shift to V2 is to enforce better contracts, security, and predictability.

### Risks / technical debt
- **V1 Processes:** Rely on dynamic Python imports and lack strict input/output validation.
- **Python Exposure:** Over-reliance on `safe_eval` for conditions and assignments creates a security surface area that is hard to audit perfectly.
- **Cycle Detection:** Current `_event_reentry_guard` is limited to single-document recursion.

---

## Strategic Shift: The Move to V2 and DSL-First Logic

#### Decision: Rule Lifecycle Traceability
Detailed analysis of the lifecycle confirms that logging is intentionally decoupled from the main transaction via background enqueuing to ensure "forensic" integrity even on request failure. Eligibility is optimized through a Redis-backed registry and "watched fields" filtering to minimize hook overhead.

#### Decision: Action Handler Strategy
The engine uses a stateless Strategy pattern for action execution. Key handlers like `Sub-Rule` and `Loop` manage complex state (recursion depth, iteration indices) through the `meta` and `vars` overlays in the execution context.

#### Decision: Process V2 Standard
The declarative V2 contract (in `process_contract_v2.py`) is now the mandatory baseline for process operations. It enforces schema-validated inputs/outputs and strictly defined capabilities (e.g., `writes_to`, `transactional`). File-backed Python controllers from V1 are treated as legacy adapters.

#### Decision: Expression System Evolution (ValueResolver)
The system is transitioning from raw `safe_eval` calls to a structured `ValueResolver` (CompiledResolver) pattern. This allows complex data transformations (Math, Date, String) to be executed via optimized Python objects instead of arbitrary string evaluation, laying the groundwork for the cross-platform DSL.

#### Decision: Contract-Driven UI (VueFlow + Pinia)
The Visual Builder is built as a Vue 3 application integrated into Frappe. It is strictly "contract-driven": the backend (`api.get_contract_dto`) dictates the available node types, their config schemas, and validation rules. The frontend manages the visual topology (`useGraphStore`) and document lifecycle (`useRuleStore`), ensuring "What you see is what executes."

### Decision: V1 Deprecation
V1 processes are now officially considered legacy. All new development must target the V2 declarative runtime.

### Decision: DSL-First Expressions
The system is moving away from raw Python in user-defined logic toward a structured expression DSL. This DSL will be compilable to Python for backend execution and JS for frontend previews.

### Decision: Global Execution DAG
Cycle management is being re-envisioned as a global execution graph check per trigger chain, preventing "ping-pong" cycles between different documents.

### Decision: Replay-Capable Logging
Execution logs are being refined to ensure they contain enough semantic data (inputs, path decisions, mutation diffs) to reconstruct the logic flow of a transaction.
