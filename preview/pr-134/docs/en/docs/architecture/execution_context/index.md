# <no value>
# Architecture: Execution Context

## 🧠 The Shared Memory

The `ExecutionContext` is the "Brain" of a rule execution. It travels through every node, carrying state and providing environmental awareness.

### Context Scopes

1. **`doc`**: The primary document triggering the rule.
2. **`old_doc`**: The state of the document before the current transaction (crucial for "Before Save" change detection).
3. **`vars`**: The execution memory. This is where intermediate results (e.g., from a "Query Records" or "Process") are stored.
4. **`meta`**: Metadata about the execution (rule name, version, user, timestamp).
5. **`frappe`**: A `SafeFrappeAPI` proxy that allows read-only DB access but blocks mutations (ensuring safety in conditions).

---

## 🔄 State Propagation Pattern

When an action executes, it can:

- **Read** from any scope.
- **Write** to `vars`.
- **Mutate** `doc` (if in a "Before" event and permitted).

### Example: The "Chaining" Pattern

1. **Node A (Query)**: Finds a related "Project". Saves it to `vars.project`.
2. **Node B (Assignment)**: Sets `doc.project_manager = vars.project.manager`.
3. **Node C (Condition)**: If `vars.project.status == 'Delayed'`, it triggers a notification.

This pattern demonstrates how the context enables **composite logic** that spans multiple documents and data sources.

---

## 🛡️ Transactional Awareness

The context is aware of whether it is running in a **Synchronous Hook** or an **Asynchronous Job**.

- In a Sync Hook, it enforces stricter safety (e.g., blocking `time.sleep` during retries).
- It manages database savepoints to ensure that even if part of the graph fails, the `doc` remains in a valid state according to the user's "On Error" policy.

---

## 🧬 Future Evolution: Graph Memory

The current architecture could naturally evolve to support **State Persistence**.

- By saving the `ExecutionContext` (the `vars` snapshot) to a database, FlexiRule could support **Long-Running Workflows** that "wait" for an external event (e.g., an approval) and then resume exactly where they left off.
- The foundations for this are already present in the serializable nature of the `vars` dictionary.
