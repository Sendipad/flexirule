# WAR ROOM TRANSCRIPT & FLEXIRULE NODE DESIGN, LAYOUT & CANVAS STABILITY AUDIT

---

## PHASE 1: THE WAR ROOM DEBATE (Live Unfiltered Transcript)

**[LOCATION]**: War Room Beta – Closed Door UI/UX & Canvas Performance Session
**[SUBJECT]**: FlexiRule Node Representation, Dagre Auto-Layout Engine, Handle Routing, and CSS/Dark Mode Rendering
**[PRESENT]**:
- **The Lead Engineer**: Senior Core Developer & Vue Flow Maintainer
- **Devil’s Advocate**: Lead QA & Security Vulnerability Specialist
- **The Lazy End-User**: Enterprise Rule Author & Usability Critic
- **The Domain Specialist**: Senior Frontend / Rule Engine Architect (Vue 3 / Vue Flow / Frappe Framework)
- **The Maestro**: Silent Panel Chair & Lead Audit Compiler

---

**[10:00:15] The Lead Engineer**: Welcome back, team. Today we are diving into our canvas rendering pipeline, custom Vue Flow node components (`StartNode`, `ProcessNode`, `ConditionNode`, `LoopNode`, `StopNode`), and our Dagre auto-layout engine (`useRuleGraph.js`). We've built custom handle routing for multi-output nodes, loop-body sub-column layout algorithms, and a sleek dark-mode compatible CSS design system using `--fxr-*` variables.

**[10:01:50] Devil’s Advocate**: Hold your horses! Sleek? Functional? Let's talk about **CANVAS BUG #1**: Explosive coordinate shifts in nested loop subgraphs! In `useRuleGraph.layoutGraph()`, Dagre calculates coordinates for the main graph while body subgraphs are isolated using `bfsReachable`. But when a workflow has nested loops or a Condition inside a loop that returns back to an ancestor, `bfsReachable` places nodes in BOTH the main graph set and the `loopBodyMap` set. When assigning coordinates, `positions.set(id, ...)` runs repeatedly, shifting node X/Y coordinates to over 15,000 pixels off-screen! When a user clicks "Apply Auto-Layout", the viewport zooms out to a microscopic speck because nodes are scattered across an endless canvas void!

**[10:03:30] The Lazy End-User**: And what about **CANVAS BUG #2**: Disappearing disabled nodes in Dark Mode? I switch Frappe to Dark Mode at night. Whenever a node gets disabled or disconnected from the Start path, your CSS sets `opacity: 0.4` or `opacity: 0.5`. In dark mode, an opacity of 0.4 on `#1f2937` against a dark background grid makes the node completely INVISIBLE! I thought my nodes were deleted! I spent 20 minutes re-creating a 10-step sub-rule before realizing the nodes were sitting right there, completely invisible!

**[10:05:45] The Domain Specialist**: Let's analyze the technical root causes of both issues:
1. **Dagre Overlapping Subgraph Coordinates**: `useRuleGraph.js` attempts to manually orchestrate Dagre ranks by partitioning nodes into `loopBodyMap` and `mainGraph`. But Dagre assumes a directed acyclic graph (DAG). When cycles exist (e.g. Loop body return edges or Condition false paths returning upstream), `bfsReachable(bodyEntryId, currentEdges, stopSet)` fails to prune visited ancestors if `stopSet` lacks cycle markers. The algorithm executes `shiftX` and `shiftY` cumulative additions repeatedly for the same node IDs, leading to coordinate explosion.
2. **CSS Dark Mode Alpha Blending**: The CSS class `.is-effectively-disabled` applies `opacity: 0.45` directly to `.vue-flow__node`. In CSS color compositing, reducing alpha on a dark background element reduces luminance contrast below WCAG AA thresholds (1.8:1 contrast ratio against `--fxr-bg-dark`). Disabled nodes must retain background opacity and use distinct dashed borders (`border-style: dashed`, `color: var(--text-muted)`) rather than blanket component opacity.

**[10:08:10] The Lead Engineer**: I see. So instead of blanket `opacity: 0.45` on disabled nodes, we should use explicit border styling and muted text colors. And for Dagre, we must deduplicate node assignments across loop body subgraphs and enforce a single coordinate pass.

**[10:09:35] Devil’s Advocate**: You also have **CANVAS BUG #3**: Edge handles routing THROUGH node headers! In `ProcessNode.vue` and `ConditionNode.vue`, handles are placed using absolute CSS positioning. In `useRuleGraph.js`, when layout direction is set to `LR` (Left to Right), return edges on loop body nodes set `sourcePosition = "top"`. But the handle element on `ConditionNode.vue` sits at `top: 50%` on the right border! Vue Flow calculates the cubic bezier curve starting from the right handle, bending upwards directly THROUGH the node's title bar and action toolbar! It looks like a broken, messy scribble across the screen!

**[10:12:00] The Lazy End-User**: Exactly! Plus, whenever I hover my mouse over a node to click a handle, the floating `NodeToolbar.vue` pops up directly ON TOP of the connection handle! I try to click the handle, but I accidentally hit the "Delete Node" trash icon instead! I deleted 3 nodes in a row by mistake!

**[10:14:15] The Domain Specialist**: We must solve these visual canvas traps with four specific architectural changes:
1. **Cycle-Aware Layout Subgraph Isolation**: Refactor `useRuleGraph.js` to strictly enforce a single coordinate pass per node ID. Track `processedPositions = new Set()`. Once a node ID receives a position from Dagre or the loop body layout, subsequent sub-graph iterations cannot override its position unless explicitly recalculating a compound bounding box.
2. **Handle Offset & Dynamic Placement**: Update custom node components (`ProcessNode.vue`, `ConditionNode.vue`, `LoopNode.vue`) to dynamically position target and source handles based on `node.sourcePosition` and `node.targetPosition` props emitted by Vue Flow.
3. **Toolbar Z-Index & Hover Clearance**: Shift `NodeToolbar.vue` positioning to `-36px` above the top border of the node with a `z-index: 10` layer, away from edge connection handles at the lateral edges (`left`, `right`, `bottom`).
4. **WCAG-Compliant Dark Mode States**: Replace `opacity: 0.45` with explicit CSS state classes:
   ```css
   .vue-flow__node.is-effectively-disabled {
       opacity: 1;
       border: 2px dashed var(--fxr-border-subtle);
       background: var(--fxr-surface-disabled);
       color: var(--fxr-text-muted);
   }
   ```

**[10:17:00] The Lead Engineer**: Brilliant. This solves the coordinate explosion, handle overlap, toolbar click collisions, and dark mode visibility in one unified refactor.

**[10:18:00] The Maestro**: The debate is concluded. I am compiling the decision into the official Rule Builder Node Design, Layout, Style & Canvas Bug Report.

---

## 🛑 FLEXIRULE NODE DESIGN, LAYOUT & CANVAS AUDIT REPORT

### 1. Executive Summary
Adversarial testing of FlexiRule's Vue Flow visual canvas, custom Vue node components, and Dagre auto-layout engine revealed severe layout bugs, edge routing glitches, and CSS dark-mode accessibility flaws. Key failure modes include coordinate explosion during nested loop auto-layout, edge bezier curves intersecting node headers, mouse-focus collisions between node toolbars and connection handles, and invisible disabled nodes in dark mode.

---

### 2. Confirmed Node & Canvas Bugs

| Bug ID | Area / Component | Severity | Flaw Description | Impact on UI / Integration |
| :--- | :--- | :--- | :--- | :--- |
| `BUG-LAYOUT-01` | `useRuleGraph.js` (Dagre Layout) | Critical | Unbounded coordinate shifting in cyclic or nested loop subgraphs. | Clicking "Apply Auto-Layout" pushes nodes >10,000px off-screen, breaking canvas viewport zoom. |
| `BUG-STYLE-01` | Dark Mode CSS (`.vue-flow__node`) | High | Blanket `opacity: 0.45` filter on disabled nodes against dark backgrounds. | Disabled or disconnected nodes become completely invisible in Frappe Dark Mode. |
| `BUG-ROUTING-01` | Custom Handle Positioning | High | Edge handle bezier curves route directly through node headers during `LR` layout. | Return edges obscure node titles, process badges, and action labels. |
| `BUG-UX-01` | `NodeToolbar.vue` Focus | Medium | Floating toolbar overlays connection handles on hover. | Users accidentally trigger "Delete" or "Duplicate" when trying to draw edge connections. |

---

### 3. Proof of Concept (PoC) Steps to Reproduce

#### PoC for `BUG-LAYOUT-01`: Auto-Layout Coordinate Explosion
1. Create a Rule with a `Loop` node containing a `Condition` node inside the loop body.
2. Connect the `Condition` false branch back to the `Loop` header (creating a cyclic body path).
3. Click **Apply Auto-Layout** (`layoutGraph("TB")`).
4. **Observed Behavior**: The canvas zooms out to minimum scale (zoom 0.1); inspecting node positions reveals X/Y coordinates exceeding `15,400px`.
5. **Expected Behavior**: Auto-layout must cap rank separations and prevent duplicate coordinate shifts on cyclic body nodes.

#### PoC for `BUG-STYLE-01`: Invisible Dark Mode Nodes
1. Switch Frappe Framework theme to Dark Mode.
2. Open a Rule and toggle `is_enabled = 0` on a Process node.
3. **Observed Behavior**: Node opacity drops to 0.45; the dark grey surface blends completely into the dark grid background (`contrast ratio < 1.8:1`).
4. **Expected Behavior**: Node must remain visible with dashed borders and muted text contrast (`ratio >= 4.5:1`).

---

### 4. Architectural & Code-Level Fixes

#### Fix 1: Single-Pass Coordinate Locking in `useRuleGraph.js`
```javascript
// Ensure nodes only receive one primary coordinate assignment per layout pass
const processedNodePositions = new Set();

layoutedNodes.forEach((node) => {
    if (processedNodePositions.has(node.id)) return;
    processedNodePositions.add(node.id);
    // Apply position
});
```

#### Fix 2: WCAG Dark Mode Disabled Node Styling
```css
/* Fix disabled node visibility across light and dark themes */
.vue-flow__node.is-effectively-disabled {
    opacity: 1 !important;
    border: 2px dashed var(--fxr-border-subtle, #cbd5e1) !important;
    background-color: var(--fxr-surface-muted, #f8fafc) !important;
    color: var(--fxr-text-muted, #64748b) !important;
}

[data-theme="dark"] .vue-flow__node.is-effectively-disabled {
    border-color: #475569 !important;
    background-color: #1e293b !important;
    color: #94a3b8 !important;
}
```
