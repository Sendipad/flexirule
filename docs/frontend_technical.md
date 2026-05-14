# Frontend Technical Documentation

The FlexiRule frontend is a sophisticated **Vue 3** application integrated into the Frappe Desk environment. It leverages **VueFlow** for graph orchestration and **Pinia** for modular state management.

## Tech Stack
- **Vue 3**: Composition API.
- **Pinia**: State management with 5 modular stores.
- **VueFlow**: A highly customizable library for building node-based editors.
- **Dagre**: Used for automated graph layout (Sugiyama algorithm).
- **Frappe UI**: Integrated with standard Frappe dialogs, controls, and API calls.

---

## State Management (Pinia Stores)

### `useRuleStore`
The "Brain" of the application. It manages the Rule document's lifecycle.
- **Fetch**: Loads the Rule DocType, fetches metadata, and coordinates the initialization of the `GraphStore`.
- **Save**: Serializes the graph back into the Rule Action child table, performs topological sorting, and validates the document before persisting.
- **Transitions**: Calls backend APIs to move rules between `Draft` and `Active` states.

### `useGraphStore`
Manages the visual elements of the rule.
- **Elements**: Holds the arrays of `nodes` and `edges`.
- **Sync**: Responsible for mapping Rule Action rows to VueFlow nodes and vice versa.
- **Operations**: Provides helpers for adding, deleting, and connecting nodes.
- **Context**: Implements the `getAvailableVariables` logic by traversing the graph upstream from a selected node.

### `useUIStore`
Handles the transient state of the user interface.
- **Selection**: Tracks the currently selected node ID.
- **Modals**: Controls the visibility of the configuration sidebar or modal.
- **Testing**: Stores the results of `test_rule` or `simulate_rule` for visualization on the canvas.

### `useMetaStore` & `useHistoryStore`
- **MetaStore**: Caches DocType information to reduce API calls during configuration.
- **HistoryStore**: Manages a stack of graph snapshots to enable Undo/Redo.

---

## Graph Normalization & Sync

One of the most complex parts of the frontend is syncing the **Graph (Nodes/Edges)** with the **Relational Data (Child Table Rows)**.

1.  **Loading**: `sync_actions_to_graph` reads the `actions` child table. It uses `next_step_if_true/false` to build the `edges` array.
2.  **Visual Layout**: After loading actions, `merge_visual_layout` applies coordinates from the `visual_data` JSON field.
3.  **Saving**: Before saving, the `RuleStore` performs a **Topological Sort** on the nodes to ensure they are stored in a logical execution order in the child table. It then translates the graph's edges back into `next_step` ID references.

---

## Dynamic Configuration Forms

FlexiRule does not have hardcoded forms for every action. Instead, it uses a schema-driven approach:

- **Schema**: The backend provides a JSON Schema for each action (via `get_node_config_schema`).
- **Control Factory**: The frontend iterates over this schema and uses a `ControlFactory` to mount the appropriate Vue component (e.g., `DataControl`, `LinkControl`, `FlexiGrid`).
- **Validation**: Forms are validated against the schema before the user can "Save" the node configuration.

---

## Testing Visualization

When a test run is performed, the backend returns a `path_trace`. The `UIStore` processes this trace to provide visual feedback:

- **Path Highlighting**: Edges involved in the execution are styled (e.g., animated or colored).
- **Node Badges**: Nodes are decorated with status icons (Checkmarks for success, Crosses for failure).
- **Execution Panel**: A sidebar displays a chronological list of steps with their durations and results.
