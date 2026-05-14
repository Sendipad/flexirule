# FlexiRule Architecture

FlexiRule is a visual rule orchestration engine built for Frappe v15+. It bridges the gap between no-code configuration and standard Python business logic by providing a graph-based execution layer.

## System Overview

FlexiRule follows a layered architecture that integrates deeply with the Frappe Framework:

1.  **Presentation Layer (Vue 3 + VueFlow)**: A modern, reactive visual builder for designing rules.
2.  **API Layer (`flexirule.ruleflow.api`)**: Standardized whitelisted endpoints for lifecycle management, execution, and metadata introspection.
3.  **Domain Layer (Core Engine)**: The heart of the system, responsible for rule compilation, validation, and deterministic execution.
4.  **Persistence Layer (DocTypes)**: Frappe DocTypes for storing rule definitions, process metadata, and execution logs.

---

## 1. Presentation Layer (Frontend)

The frontend is built using **Vue 3** and **VueFlow**, integrated into the Frappe Desk.

-   **State Management**: Uses **Pinia** with five specialized stores:
    -   `useRuleStore`: Manages the Rule document lifecycle (fetch, save, activation).
    -   `useGraphStore`: Handles nodes, edges, and graph-specific logic (topology, auto-layout).
    -   `useUIStore`: Manages selection, sidebar/modal states, and test visualization.
    -   `useMetaStore`: Caches DocType metadata and field information.
    -   `useHistoryStore`: Implements snapshot-based undo/redo functionality.
-   **Visual Builder**: Renders a graph where each node is a **Rule Action**.
-   **Dynamic UI**: Configuration forms for nodes are generated at runtime using **JSON Schemas** provided by the backend.

---

## 2. API Layer

The API layer provides a secure bridge between the frontend and backend. Key functionalities include:

-   **Introspection**: `get_contract_dto` and `get_node_config_schema` allow the frontend to understand available actions and their configuration requirements without hardcoding.
-   **Validation**: `validate_rule_document` provides real-time feedback on rule integrity.
-   **Execution**: `test_rule` and `simulate_rule` enable safe testing of rules with detailed path tracing.

---

## 3. Domain Layer (The Core Engine)

The core engine is responsible for the deterministic execution of rules.

### **RuleCoordinator**
The entry point for all rule executions. It handles:
-   **Event Dispatching**: Listens to Frappe `doc_events` and identifies applicable rules.
-   **Layered Caching**: Manages a high-performance runtime registry using request-local (frappe.local), Redis, and database fallbacks.
-   **Pruning**: Uses `watched_fields` to quickly skip rules that aren't affected by specific field changes.

### **RuleEngine**
The executor that traverses the graph. It features:
-   **Strategy Pattern**: Uses a `HandlerRegistry` to dispatch execution to specific `ActionHandlers` (Condition, Process, Set Value, etc.).
-   **Cycle Detection**: Prevents infinite loops via visit counting and iteration limits.
-   **Error Policy**: Implements configurable error handling (Continue, Retry with backoff, Rollback, Escalate).

### **ConditionCompiler**
Compiles visual JSON condition trees into optimized Python strings for ultra-fast evaluation via `frappe.safe_eval`.

### **ContextManager**
Manages the variable scope (`vars`) during execution, ensuring type safety and providing structured mutation modes for updating the document or context.

---

## 4. Persistence Layer (Data Model)

FlexiRule uses several Frappe DocTypes:

-   **Rule**: The primary document containing trigger settings and visual metadata.
-   **Rule Action**: A child table within Rule representing nodes in the graph.
-   **Process**: A file-backed module that groups reusable business logic (Operations).
-   **Rule Execution Log**: Stores detailed traces of every rule execution for auditing and debugging.
-   **RuleFlow Settings**: Global configuration for the engine and builder.

---

## Integration with Frappe

-   **Doc Events**: Rules are hooked into the standard Frappe lifecycle (`before_save`, `on_submit`, etc.) via `hooks.py`.
-   **Background Jobs**: Asynchronous rules are offloaded to Frappe's background workers using `frappe.enqueue`.
-   **Security**: Execution is sandboxed using `SafeFrappeAPI` to prevent unauthorized side effects in conditions and templates.
