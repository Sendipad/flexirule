# <no value>
# Architecture: Graph Orchestration

## 🕸️ The Logic Topology

FlexiRule represents automation as a **Directed Graph**. This is not just a UI choice; it is the fundamental way the engine reasons about execution.

### Node Types

1.  **Entry Nodes**: The starting points of the graph.
2.  **Action Nodes**: Where work happens (Assignment, Process).
3.  **Branching Nodes**: Where the path splits (Condition, Switch).
4.  **Terminal Nodes**: Where execution stops (Stop, Raise Error).

---

## 🧭 Traversal Logic

The engine uses a **Linear Walk with Jump** strategy:

- Execution starts at the root.
- After an action finishes, the engine looks at the node's `next_step` pointers.
- It "jumps" to the next node and repeats.

### Cycle Detection & Loop Safety

To prevent infinite loops (e.g., Node A -> Node B -> Node A), the engine implements **Visit Counting**.

- Every node maintains a count of how many times it has been visited in a single execution.
- If a node is visited more than the `max_visits_per_node` threshold (default: 100), the engine aborts with a `CycleDetectedError`.

---

## 🎨 Visual-Runtime Sync

A unique feature of FlexiRule is the **Bidirectional Sync** between the visual graph and the database representation.

- **`visual_data`**: A JSON blob (typically for VueFlow or ReactFlow) that stores node positions and UI metadata.
- **`actions`**: A Frappe child table that stores the execution logic.
- The `graph_service.py` ensures that the logical edges in the child table match the visual edges in the diagram.

---

## 🚀 The Power of Graph Thinking

By decoupling logic into a graph, FlexiRule enables:

- **Non-Linear Workflows**: Jumping back to a previous state for retries or corrections.
- **Parallel Branches (Future)**: The graph topology already supports multiple outgoing edges that could be executed in parallel.
- **Visual Debugging**: The `path_trace` can be overlaid on the graph to show exactly where an execution failed or took a wrong turn.
