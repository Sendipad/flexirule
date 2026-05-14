# Frontend Technical Documentation

The FlexiRule frontend is a sophisticated **Vue 3** application integrated into the Frappe Desk environment. It leverages **VueFlow** for graph orchestration and **Pinia** for modular state management.

## Tech Stack
- **Vue 3**: Composition API.
- **Pinia**: State management with 5 modular stores.
- **VueFlow**: Library for building node-based editors.
- **Dagre**: Automated graph layout algorithm.

---

## State Management (Pinia Stores)

### `useRuleStore` & `useGraphStore`
These stores manage the Rule lifecycle and visual graph elements.

#### **Variable Resolution Algorithm**
The `useGraphStore` implements the `getAvailableVariables` method, which is the heart of the builder's temporal isolation:
1.  **Graph Traversal**: It performs a backward traversal of the graph starting from the currently selected node.
2.  **Upstream Collection**: It identifies all reachable **upstream nodes** (ancestors in the execution path).
3.  **Variable Extraction**: It collects all output variables, return values, and document mutations defined in those upstream nodes.
4.  **Schema Projection**: If an upstream node is a Process or Query, it projects the expected output schema into the variable list.
5.  **Scope Filtering**: It ensures that variables from parallel branches or downstream nodes are strictly excluded.

### `useUIStore`
Handles selection, modal states, and stores execution traces.

---

## Intelligent & Reactive Controls

The Rule Builder ensures data integrity through the `SchemaRenderer` and `ControlFactory` components.

### Dynamic Control Factory
The `ControlFactory` dynamically mounts Vue components based on metadata. It ensures type-matched inputs, preventing errors like comparing a date to a boolean.

### Reactivity & Awareness
Controls are cross-reactive. Updating a `reference_doctype` instantly refreshes dependent field pickers (`target_field`) by re-evaluating the configuration schema.

---

## Graph Normalization & Sync

1.  **Loading**: `sync_actions_to_graph` builds the VueFlow representation from the child table.
2.  **Visual Layout**: `merge_visual_layout` applies coordinates.
3.  **Saving**: `RuleStore` performs a **Topological Sort** to ensure actions are persisted in execution order.

---

## Testing Visualization

When a test run is performed, the `UIStore` processes the `path_trace` to highlight edges, decorate nodes with badges, and display a step-by-step execution log.
