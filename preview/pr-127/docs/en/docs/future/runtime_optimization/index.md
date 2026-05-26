# <no value>
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
The current engine uses an **Interpreter Pattern**, traversing the action graph node-by-node at runtime. While flexible, this involves repeated metadata lookups, registry checks, and graph-walking overhead.

#### The "SQL Query Plan" Analogy
Just as a database compiles a SQL string into an optimized physical execution plan before running it, FlexiRule can compile a Rule (DAG) into a **Static Action Plan**.

#### Key Compilation Strategies:
- **Linearization**: Identifying the "Hot Path" (the most frequent execution sequence) and flattening it into a list of pre-bound function calls.
- **Pre-Binding**: Instead of looking up `HandlerRegistry.get(action_type)` for every node, the plan would store direct references to the handler instances.
- **Path Pruning**: Static analysis of conditions can identify branches that are unreachable under certain context states (e.g., specific event names), removing them from the plan entirely.
- **Inlining**: For very simple graphs, sub-rules or common processes could be "inlined" into the parent plan, eliminating the overhead of nested engine invocations.

#### Performance Impact:
- **Reduced Dispatch Latency**: Eliminating the "graph walk" overhead for every step.
- **Lower Memory Pressure**: A pre-compiled plan is a lean execution object compared to a collection of Frappe Documents and JSON configs.
- **Optimized Cold Starts**: Once a plan is compiled and stored in Redis, the engine can go from "Trigger" to "Action 1" in microseconds.

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
