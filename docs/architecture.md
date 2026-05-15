# FlexiRule Architecture

FlexiRule is a visual rule orchestration engine built for Frappe v15+. It bridges the gap between no-code configuration and standard Python business logic by providing a graph-based execution layer.

## System Overview

FlexiRule follows a layered architecture that integrates deeply with the Frappe Framework:

1.  **Presentation Layer (Vue 3 + VueFlow)**: A modern, reactive visual builder for designing rules. See [Rule Builder Guide](builder/rule_builder.md).
2.  **API Layer (`flexirule.ruleflow.api`)**: Standardized whitelisted endpoints for lifecycle management, execution, and metadata introspection. See [API Reference](reference/api.md).
3.  **Domain Layer (Core Engine)**: The heart of the system, responsible for rule compilation, validation, and deterministic execution. See [Execution Engine](engine/execution_engine.md) and [Condition System](engine/condition_system.md).
4.  **Persistence Layer (DocTypes)**: Frappe DocTypes for storing rule definitions, process metadata, and execution logs. See [DocType Reference](reference/doctypes.md).

---

## 1. Presentation Layer (Frontend)

The frontend is built using **Vue 3** and **VueFlow**, integrated into the Frappe Desk. It manages complex graph states and ensures design-time safety through context-aware validation.

---

## 2. API Layer

The API layer provides a secure bridge between the frontend and backend. Key functionalities include introspection, validation, and execution testing.

---

## 3. Domain Layer (The Core Engine)

The core engine is responsible for the deterministic execution of rules.

### **RuleCoordinator**
The entry point for all rule executions. It handles event dispatching, layered caching, and pruning via `watched_fields`. See [Trigger System](engine/trigger_system.md).

### **RuleEngine**
The executor that traverses the graph using a Strategy Pattern. It manages the orchestration flow and error recovery. See [Orchestration Capabilities](engine/orchestration.md).

### **ConditionCompiler**
Compiles visual JSON condition trees into optimized Python strings for ultra-fast evaluation. See [Condition System Technical Details](engine/condition_system.md).

### **ContextManager**
Manages variable scope (`vars`) and provides structured mutation modes.

---

## 4. Persistence Layer (Data Model)

FlexiRule uses several Frappe DocTypes to maintain rules, processes, and audit trails. See [DocType Reference](reference/doctypes.md) for a full breakdown of fields and usages.

---

## Integration with Frappe

-   **Doc Events**: Rules are hooked into the standard Frappe lifecycle via `hooks.py`.
-   **Background Jobs**: Asynchronous rules are offloaded using `frappe.enqueue`.
-   **Security**: Execution is sandboxed using `SafeFrappeAPI`.
