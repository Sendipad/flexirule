# Action Zone: FlexiRule Research Initiative (A → Z)

Welcome to the **Master Internal Knowledge Base** for FlexiRule. This workspace contains a complete deep-dive analysis of the FlexiRule architecture, discovered through reverse-engineering the codebase.

## 🗺️ Architecture Map

FlexiRule is not just an app; it is a **metadata-driven automation framework** built on top of Frappe. It provides a graph-based execution engine that orchestrates reusable logic units (Processes) via declarative rules.

### Core Subsystems

-   **[Ruleflow Core Runtime](architecture/action_runtime.md)**: The engine that compiles and executes action graphs.
-   **[Resolver Engine](resolver/resolver_engine.md)**: A sophisticated value-resolution pipeline for dynamic context-aware data access.
-   **[Schema-Driven UI](ui/schema_driven_ui.md)**: A frontend engine that generates configuration UIs from backend metadata.
-   **[Process vs Rule](architecture/system_philosophy.md)**: The foundational distinction between file-backed logic (Processes) and DB-defined orchestration (Rules).

---

## 🏗️ A → Z Capability Matrix

This matrix provides a "framework capability encyclopedia" for FlexiRule.

### A — Action Abstraction
The system uses a **Strategy Pattern** for action execution. Every action (Assignment, Condition, Process, etc.) is handled by a dedicated `ActionHandler`, enabling infinite extensibility via the `HandlerRegistry`.

### B — Binding System
Contextual variable binding allows actions to share state. The `ContextManager` facilitates "doc.*" and "vars.*" path resolution and mutation.

### C — Compiled Expressions
To ensure performance and security, visual conditions are compiled into optimized Python expressions using the `ConditionCompiler` and executed via `frappe.safe_eval`.

### D — Declarative Runtime v2
A strict contract system that enforces schemas and capabilities between the Rule engine and Processes, ensuring predictable behavior and low-code safety.

### E — Execution Lifecycle
A robust pipeline with built-in:
-   **Cycle Detection**: Prevents infinite loops in the action graph.
-   **Timeout Protection**: Ensures rules don't hang the system.
-   **Error Policies**: Retries (with backoff), Rollbacks (via savepoints), and Escalation.

### F — FlexiGrid
A powerful, recursive, and schema-aware grid component that enables complex collection editing and nested configuration structures.

### G — Graph Orchestration
Rules are represented as directed graphs where nodes are actions and edges are transitions (True/False/Switch cases).

### H — Handler Strategy
The `HandlerRegistry` allows third-party apps to register new action types, making the platform naturally "plugin-oriented."

### I — Intermediate State
Execution "memory" flows through the system via the `vars` scope, allowing subsequent nodes to access outputs from previous operations.

### J — Jinja Integration
Seamless integration with Jinja2 for advanced string templating and logic within the resolver pipeline.

### K — Knowledge Injection
Context injection allows rules to be aware of the triggering document, user roles, session data, and global settings.

### L — Low-Code Foundations
By abstracting complex logic into Processes and providing a visual builder, FlexiRule enables non-developers to configure enterprise automation safely.

### M — Mutation Intents
Processes can return "mutation intents" instead of direct side effects, allowing the engine to manage state changes predictably and with rollback support.

### N — Normalization Pipeline
Built-in resolvers for data cleansing (trim, slug, title, etc.) reduce the need for custom Python code.

### O — Operation Registry
A centralized registry that maps Processes and their Operations to the Rule builder, complete with config/output schemas.

### P — Polymorphic Dispatch
The `ControlFactory` and `FlexValueControl` dynamically dispatch UI components based on the field metadata, enabling a rich multi-modal input experience.

### Q — Query Abstraction
Built-in `Query Records` handlers generalize database lookups into configurable nodes with filter resolution.

### R — Resolver Composition
The `ExpressionResolver` allows composing multiple resolution patterns (Variable + Formula + Static) into a single transformation chain.

### S — Savepoint Transactions
The engine uses database savepoints to allow granular rollbacks of specific actions without failing the entire request.

### T — Type Conversion
Automatic type coercion and validation (via JSON Schema) ensure data integrity across the execution pipeline.

### U — UI Schema Generation
Backend metadata is dynamically translated into frontend control configurations, minimizing code duplication.

### V — Versioned Lineage
Rule versioning and amendment workflows enable safe evolution of automation logic with history tracking.

### W — Watched Fields
Optimized dispatching uses "watched fields" detection to skip rules that are not affected by a specific document change.

### X — eXecution Tracing
Detailed execution logs capture the full path, variable states, and timing for every run, providing unmatched observability.

### Y — Yielding Control (Async)
Background execution support (via `frappe.enqueue`) allows long-running or non-blocking rules to run asynchronously.

### Z — Zero-Touch Evolution
The architecture is designed to evolve into a full visual flow builder with minimal core changes, thanks to its generic graph-based foundation.

---

## 📂 Deep-Dive Documentation

### Architecture
- [System Philosophy](architecture/system_philosophy.md)
- [Action Runtime](architecture/action_runtime.md)
- [Execution Context](architecture/execution_context.md)

### Resolver Engine
- [Resolver Architecture](resolver/resolver_engine.md)
- [Resolver Patterns](resolver/resolver_patterns.md)

### UI Engine
- [Schema-Driven UI](ui/schema_driven_ui.md)
- [FlexiGrid Architecture](ui/flexigrid_architecture.md)
- [Action Config Panels](ui/action_config_panels.md)

### Action System
- [Action Types Catalog](actions/action_types_catalog.md)
- [Action Orchestration Patterns](actions/action_patterns.md)

### Platform Evolution
- [Low-Code Platform Potential](future/low_code_platform_potential.md)
- [Runtime Optimization](future/runtime_optimization.md)
