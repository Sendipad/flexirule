# <no value>
# Architecture: Action Runtime

## 🚂 The Execution Pipeline
The `RuleEngine` is the heart of FlexiRule. It doesn't just run code; it manages a **Stateful Execution Pipeline**.

### 1. Compilation
Before execution, the `ConditionCompiler` transforms visual logic into optimized Python. This ensures that the runtime doesn't waste cycles parsing JSON in the middle of a document save.

### 2. Initialization
The `RuleCoordinator` acts as the dispatcher. It finds all active rules for a specific DocType event and prepares the `ExecutionContext`.

### 3. Graph Traversal
The engine performs a "Walk" on the action graph:
- It starts at the **Entry Action** (or deduces the root).
- For each node, it looks up the appropriate `ActionHandler` from the `HandlerRegistry`.
- It executes the handler, captures the result, and determines the **Next Action ID**.

---

## 🏗️ Action DocType Architecture
- **Rule (Parent)**: Contains metadata, trigger settings, and the overall graph configuration.
- **Rule Action (Child)**: Represents a single node. It stores:
    - `action_type`: Determines the handler.
    - `config`: A JSON blob containing node-specific settings.
    - `next_step_if_true` / `next_step_if_false`: The edges of the graph.

---

## 🔌 Plugin Architecture & Extensibility
The use of the **Strategy Pattern** via `HandlerRegistry` is a masterstroke of flexibility.
```python
# To add a new action type:
class MyCustomHandler(ActionHandler):
    action_type = "My Action"
    def execute(self, action, context, engine):
        # logic...
        return result, next_id

HandlerRegistry.register(MyCustomHandler())
```
This means new platform capabilities (like "Call OpenAI" or "Generate PDF") can be added as plugins without touching the core engine.

---

## 🛡️ Resilience & Error Handling
FlexiRule implements several enterprise-grade execution patterns:
- **Savepoints**: The engine creates `frappe.db.savepoint` before complex actions. If they fail, it can rollback to that specific point without failing the whole transaction.
- **Retry with Backoff**: Configurable retry logic for transient failures (e.g., external API timeouts).
- **Cycle Detection**: A visit-counting mechanism prevents infinite loops, a common danger in graph-based systems.

---

## 📈 Runtime Dispatch & Performance
- **Watched Fields**: The engine extracts field dependencies from the compiled expressions. If a document update doesn't touch those fields, the rule execution is skipped early.
- **Layered Caching**: Rule metadata is cached in `frappe.local` -> `Redis` -> `Database`. This ensures that even with hundreds of rules, the overhead on every document save is minimal.
