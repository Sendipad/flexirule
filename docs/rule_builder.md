# Visual Rule Builder

The Rule Builder is a Vue 3-based visual workspace for designing business logic graphs. It provides a drag-and-drop canvas where you can orchestrate complex workflows.

## Key Concepts

### Nodes (Actions)
Each node in the graph represents a **Rule Action**.
- **Entry Action**: The starting point of every rule. It defines the trigger criteria (DocType, Event, Priority).
- **Functional Nodes**: Perform work (e.g., Process, Set Value, Query Records).
- **Control Nodes**: Manage flow (e.g., Condition, Loop, Switch).
- **Terminal Nodes**: End the execution (e.g., Stop, Raise Error).

### Edges (Connections)
Connections between nodes define the execution order.
- **Default Path**: Followed after a node completes successfully.
- **Conditional Paths**: Labeled `True` (Success) and `False` (Failure/Else) for branching logic.
- **Loop Paths**: `For Each` (body of the loop) and `After Last` (continuation after completion).

---

## Builder UI Features

### 1. The Canvas (VueFlow)
- **Drag-and-Drop**: Easily move nodes to organize your flow.
- **Auto-Layout**: Use the "Auto Layout" button to automatically organize nodes using a Sugiyama-style algorithm (Dagre).
- **Mini-map & Controls**: Zoom, pan, and fit-view for navigating large graphs.

### 2. Configuration Modes
Depending on your settings, nodes can be configured in two ways:
- **Sidebar Mode**: A panel opens on the right side for quick edits.
- **Modal Mode**: A centered dialog for a focused configuration experience.

### 3. Dynamic Form Rendering
FlexiRule uses **JSON Schemas** to generate configuration forms. This means that if you create a custom `Process`, the builder will automatically render the correct inputs (Link pickers, Checkboxes, etc.) based on your Python code.

---

## Designer Tools

### Context-Aware Variable Picker
When configuring an action (like `Set Value`), the builder provides an autocomplete list of all variables available at that point in the graph. This includes:
- All fields from the primary DocType.
- Output variables from all upstream nodes.
- Special variables like `vars.loop` (inside loops) or `vars.index`.

### Copy & Paste
You can select one or more nodes and copy them (`Ctrl+C`) to the clipboard. These can be pasted (`Ctrl+V`) into the same rule or a different one. FlexiRule remaps the internal connections and ensures action IDs are unique.

### Undo / Redo
The builder maintains a history of your changes. You can safely experiment and revert changes using standard shortcuts (`Ctrl+Z`, `Ctrl+Y`).

---

## Testing & Debugging

### Live Test
From the builder, you can click **Test Rule** to execute the current logic against a real document.
- **Dry Run**: Execute the rule without committing database changes.
- **Visual Feedback**: The builder highlights the path taken during the test directly on the canvas.
- **Execution Log Overlay**: View real-time status badges (✅/❌) on each node and inspect the final variable state.

### Simulation
Simulation allows you to step through the rule logic to see exactly how conditions would evaluate and how variables would change, without executing side-effect-heavy processes.
