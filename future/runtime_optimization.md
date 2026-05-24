# Future: Runtime Optimization

## 🚀 Scaling the Engine
As FlexiRule deployments grow to thousands of rules and millions of executions, performance becomes the primary architectural challenge.

---

## 🛠️ Current Optimization Primitives

### 1. Compiled Expression Caching
Visual conditions are compiled once and cached. The engine never "parses" the condition logic at execution time.

### 2. Watched Fields
The `RuleCoordinator` uses static analysis of compiled expressions to determine which document fields a rule actually cares about.
- **Impact**: Rules that check `status` are never even loaded when `description` is changed.

### 3. Request-Local Memoization
The `get_compiled_resolver` and `RuleCoordinator` registries use `frappe.local` to avoid redundant lookups within the same web request.

---

## 📈 Future Optimization Opportunities

### 1. Compiled Action Plans
Moving beyond node-by-node interpretation. The engine could pre-compile an entire Rule into a **Static Execution Plan** (similar to a SQL Query Plan), further reducing the overhead of graph traversal.

### 2. Resolver Caching
Adding a result-cache to resolvers for idempotent operations.
- E.g., `Sum(items)` only needs to be calculated once per document save, even if 10 different actions use that value.

### 3. Dependency Graph Optimization
Using graph analysis to find nodes that can be executed in **Parallel**.
- Currently, execution is sequential. In an async context, multiple independent branches could be dispatched to workers simultaneously.

### 4. Lazy Evaluation of `old_doc`
Fetching `old_doc` from the database is expensive. The engine could delay this until a rule actually tries to access an `old_doc.*` path.

---

## 🏛️ Scalability Implications
The move towards **Declarative Runtime v2** is a step toward massive scalability. By enforcing strict schemas and mutation intents, the engine can safely "offload" execution to background workers or even specialized "Edge" runtimes in the future.
