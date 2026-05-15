# Frontend Technical Deep Dive

The FlexiRule frontend is a Vue 3 application that synchronizes complex graph logic with Frappe's relational data model.

## State Synchronization

The builder manages three distinct layers of state:
1.  **Frappe Model**: The `Rule` and `Rule Action` documents in `frappe.model`.
2.  **Pinia Stores**: The reactive application state (`nodes`, `edges`, `is_dirty`).
3.  **VueFlow State**: The internal DOM representation of the canvas.

### The topological Sort for Persistence
Because Frappe child tables are linear (indexed), but Rule logic is a graph, we must ensure that actions are stored in a logical sequence. Before saving, `useRuleStore` calls a topological sort algorithm:
- **Algorithm**: Breadth-First Search (BFS) starting from the `Entry Action`.
- **Purpose**: Ensures that when the Rule Engine loads the rule sequentially from the database, nodes that depend on upstream results are generally loaded after their dependencies, facilitating faster registry hydration.

---

## Intelligent & Reactive Controls

### Schema Renderer & Control Factory
The `SchemaRenderer` component takes a backend JSON schema and iterates through its properties. For each property, it uses the `ControlFactory` to mount a Vue component:
- **Reactivity**: Every control emits a `change` event that triggers a re-validation of the entire node's schema.
- **Awareness**: Controls like `FieldPicker` use the `getAvailableVariables` algorithm to traverse the graph and provide real-time suggestions.

### Variable Resolution Algorithm
Implemented in `useGraphStore.getAvailableVariables`, this is the heart of the builder's context-awareness:
1.  **Backwards Traversal**: Starting from node $N$, find all nodes reachable by following incoming edges.
2.  **Ancestry Collection**: Identify the set of all ancestor nodes.
3.  **Variable Aggregation**: For each ancestor, inspect its `return_variable` and `return_type`.
4.  **Schema Projection**: If an ancestor is a `Process` with a known `output_schema`, project those fields as selectable child properties (e.g., `vars.my_result.status`).

---

## Performance & Optimization

- **Snapshot-based History**: Undo/Redo is implemented by taking full snapshots of the `nodes` and `edges` arrays. To optimize memory, consecutive identical states are deduplicated.
- **Metadata Caching**: `useMetaStore` maintains a request-level cache of DocType schemas to prevent redundant `get_doctype_fields` API calls while the user is designing.
