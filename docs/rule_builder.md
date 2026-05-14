# Visual Rule Builder

The Rule Builder is a Vue 3-based visual workspace for designing business logic graphs. It provides a drag-and-drop canvas where you can orchestrate complex workflows.

## Key Concepts

### Nodes (Actions)
Each node in the graph represents a **Rule Action**.
- **Entry Action**: The starting point. Defines trigger criteria.
- **Functional Nodes**: Perform work (Process, Set Value, Query Records).
- **Control Nodes**: Manage flow (Condition, Loop, Switch).

### Edges (Connections)
Connections define execution order, including branching (`True`/`False`) and iteration (`For Each`).

---

## No-Code & Error Prevention

A primary goal of the Rule Builder is to eliminate error-prone manual input by providing a strictly guided configuration experience.

### Context-Aware Field Pickers
Instead of typing field names, users select them from intelligent pickers. These pickers are **Context-Aware**, meaning they only show fields relevant to the current state:
- **Primary DocFields**: Fields from the Rule's target DocType.
- **Upstream Variables**: Results and outputs from previous nodes in the current path.
- **Reference DocTypes**: When a node points to a different record (e.g., in a `Query Records` action), the picker automatically switches to the schema of that reference DocType.

### Reactive & Type-Aware Controls
The builder's input controls are highly reactive. They understand the **FieldType** of the selected data and adapt accordingly:
- **Automatic Validation**: If a user selects a Date field (`posting_date`), the system automatically ensures the comparison value is a date, preventing invalid configurations like `posting_date == "Yes"`.
- **Dynamic Operator Filtering**: The list of available operators (e.g., `Greater Than`, `Contains`) changes based on whether the selected field is numeric, a string, or a collection.
- **Inter-Field Reactivity**: Changing one field (like selecting a different DocType) instantly updates the configuration options for all dependent fields in that node's setup.

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
