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
These stores manage the Rule lifecycle and visual graph elements. They coordinate the mapping of Rule Action child tables to visual nodes and maintain the topological order required for saving.

### `useUIStore`
Handles selection, modal states, and stores execution traces for visualization.

---

## Intelligent & Reactive Controls

The Rule Builder ensures data integrity through a combination of the `SchemaRenderer` and `ControlFactory` components.

### Dynamic Control Factory
The `ControlFactory` dynamically mounts Vue components based on the metadata provided by the backend. It ensures that every input is "aware" of its context:
- **Type-Matching**: Controls like `DataControl` or `LinkControl` are instantiated with knowledge of the expected Frappe FieldType.
- **Value Constraints**: If a backend schema specifies a field as `Date`, the `ControlFactory` ensures only date-compatible inputs are available, preventing type-mismatch errors in rule logic.

### Reactivity & Awareness
Controls are designed to be cross-reactive. When a field like `reference_doctype` is updated in a node:
1.  A reactive event is triggered.
2.  The `SchemaRenderer` re-evaluates the configuration schema.
3.  Dependent field pickers (like `target_field`) instantly refresh their options based on the new DocType's metadata.

This "awareness" is what prevents invalid logic, such as comparing a date field to a boolean value, by strictly limiting available options and operators at the UI level.

---

## Graph Normalization & Sync

1.  **Loading**: `sync_actions_to_graph` reads the `actions` child table and builds the VueFlow representation.
2.  **Visual Layout**: `merge_visual_layout` applies stored coordinates.
3.  **Saving**: `RuleStore` performs a **Topological Sort** to ensure actions are persisted in execution order.

---

## Testing Visualization

When a test run is performed, the `UIStore` processes the `path_trace`:
- **Path Highlighting**: Styles edges involved in the execution.
- **Node Badges**: Decorates nodes with status icons based on the execution result.
- **Execution Panel**: Provides a chronological list of steps and durations.
