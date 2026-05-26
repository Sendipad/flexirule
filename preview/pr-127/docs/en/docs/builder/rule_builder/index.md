# Rule Builder<no value>

# Visual Rule Builder

The Rule Builder is a Vue 3-based visual workspace for designing business logic graphs. It provides a drag-and-drop canvas where you can orchestrate complex workflows.

## Key Concepts

### Nodes (Actions)

Each node in the graph represents a **Rule Action**.

- **Entry Action**: The starting point. Defines trigger criteria.
- **Functional Nodes**: Perform work (Process, Assignment, Query Records, Document Action, Notify).
- **Control Nodes**: Manage flow (Condition, Loop, Switch, Wait, Stop, Raise Error).

---

## No-Code & Error Prevention

A primary goal of the Rule Builder is to eliminate error-prone manual input by providing a strictly guided configuration experience.

### Temporal Context Visibility (Context-Awareness)

One of the core safety features of the builder is **Temporal Context Isolation**. At design-time, the builder ensures that an action can only access variables that are logically available at its point in the execution flow.

- **Upstream-Only Visibility**: The field picker _only_ displays variables created or updated by **upstream nodes** (nodes that execute before the current one).
- **Isolation from the Future**: A node cannot "see" or reference variables that are created or updated by actions that come after it in the graph.
- **Dynamic Schema Switching**: When a node points to a different record (e.g., in a `Query Records` action), the picker automatically switches to the schema of that reference DocType, while maintaining access to all valid upstream context.

### Reactive & Type-Aware Controls

The builder's input controls are highly reactive and understand the **FieldType** of the selected data.

- **Intelligent Filter Builder (`FilterGroup`)**: Used in Query and Condition nodes, it dynamically adapts operators based on field types and supports advanced **Timespan** tokens (e.g., "Last Week").
- **Magic Formula Builder (`ValueResolver`)**: Allows defining complex logic (Date math, Aggregations, String manipulation) via a guided UI that generates safe Jinja snippets.
- **Automatic Validation**: If a user selects a Date field (`posting_date`), the system ensures the comparison value is a date, preventing invalid configurations like `posting_date == "Yes"`.
- **Dynamic Operator Filtering**: Available operators (e.g., `Greater Than`, `Contains`) change based on the data type (numeric, string, or collection).

---

## Builder UI Features

### 1. The Canvas (VueFlow)

- **Auto-Layout**: Automatically organize nodes using the "Auto Layout" button.
- **Mini-map & Controls**: Navigate large graphs with ease.

### 2. Configuration Modes

- **Sidebar Mode**: Quick edits on the right panel.
- **Modal Mode**: Focused full-screen dialog.

---

## Testing & Debugging

### Live Test

Click **Test Rule** to execute the current logic against a real document.

- **Dry Run**: No database commits.
- **Visual Feedback**: Highlights the execution path and provides real-time status badges (✅/❌) on each node.

### Simulation

Step through rule logic without executing side-effects to verify condition paths and variable changes.
