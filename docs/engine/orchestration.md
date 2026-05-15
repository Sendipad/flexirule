# Orchestration Capabilities

FlexiRule is more than a simple automation engine; it is a **Visual Orchestration Layer** that allows for the coordination of complex business processes across multiple DocTypes and systems.

## Key Orchestration Patterns

### 1. Sequential & Parallel Logic
While the engine executes nodes sequentially, the graph structure allows for complex logical paths.
- **Conditional Branching**: Use the `Condition` node to create `If/Else` paths.
- **Switch Logic**: Dispatch execution to different paths based on a variable's value (e.g., routing a document based on its "Status").

### 2. Iterative Orchestration (`Loop`)
The `Loop` action allows you to orchestrate logic over collections of data.
- **Child Table Processing**: Iterate over items in a Sales Invoice to apply line-by-line calculations or validations.
- **Batch Processing**: Process results from a `Query Records` action in a loop.
- **Scoped Context**: Each iteration has its own `item` alias, ensuring clean data separation.

### 3. Modular Reusability (`Sub-Rule`)
Complex workflows can be decomposed into smaller, manageable sub-rules.
- **Callable Rules**: Define a rule once and mark it as `Exposed as Sub-Rule`.
- **Context Merging**: Sub-rules inherit context from the caller, allowing for seamless data transfer between the main orchestration and utility routines.
- **Separation of Concerns**: Keep your main flow high-level and offload detailed technical logic to sub-rules.

### 4. Lifecycle Orchestration (`Document Action`)
FlexiRule can orchestrate the entire lifecycle of records in Frappe.
- **Chained Transactions**: A single rule on `Sales Order` can automatically create a `Production Plan`, multiple `Work Orders`, and send a `Notification` to the warehouse manager.
- **Reference Updates**: Update related documents (e.g., updating a `Customer` record based on a `Payment Entry`) as part of a larger flow.

### 5. Error & Recovery Orchestration
Orchestration includes managing what happens when things go wrong.
- **Self-Healing Flows**: Use the `Retry` policy with exponential backoff for transient failures (e.g., external API calls).
- **Graceful Degradation**: Use the `Continue` policy to skip non-critical steps if they fail.
- **Atomic Rollbacks**: Use `savepoints` to ensure that if a specific step in a complex orchestration fails, only that step is reverted, maintaining the integrity of the overall process.

### 6. Synchronous vs. Asynchronous Execution
- **Sync**: For real-time validations and blocking logic.
- **Async**: For long-running orchestrations (e.g., generating 100+ documents) that should not block the user's browser. The engine automatically handles the offloading to background workers.

---

## Technical Implementation

Orchestration is achieved through the **Strategy Pattern** implemented in the `RuleEngine`. By decoupling the *execution logic* (Handlers) from the *traversal logic* (Engine), FlexiRule provides a robust and extensible framework for any business orchestration need.
