# WAR ROOM TRANSCRIPT & ARCHITECTURE PROPOSAL

---

## PHASE 1: THE WAR ROOM DEBATE (Live Unfiltered Transcript)

**Location**: FlexiRule Engineering War Room
**Topic**: Vue Flow Switch Action Node (Multi-Branch Decision/Router) & Dynamic Edge Routing Architecture
**Participants**:
- **The Lead Engineer** (`@lead-eng`): Core Vue Flow state architect, Pinia store lead, and Frappe rule engine developer.
- **Devil’s Advocate** (`@bug-hunter`): Systems QA lead, performance critic, and edge-case antagonist.
- **The Lazy End-User** (`@lazy-user`): Visual workflow designer who despises modal hopping and visual canvas spaghetti.
- **The UX/UI Canvas Specialist** (`@ux-architect`): Interactive flow designer specializing in node ergonomics, Tailwind/CSS variables, and edge diagramming.
- **The Maestro** (`@maestro`): Panel moderator and synthesis architect.

---

### [00:01] ROUND 1: THE NAIVE MULTI-HANDLE PARADIGM & IMMEDIATE BACKLASH

**@lead-eng**: Alright team, we need to bring first-class multi-branch routing to the FlexiRule Vue Flow canvas. Right now, `ConditionNode.vue` only handles binary `YES / NO` branches (`true` / `false` handles). For `Switch` actions, users currently have to configure target node IDs inside `SwitchNodeConfig.vue` via text inputs. That completely breaks the visual drag-and-connect paradigm of Vue Flow. My initial proposal is simple: we create a `SwitchNode.vue` component that reads `data.config.cases` and dynamically renders a stack of Vue Flow `<Handle type="source">` elements along the right edge of a standard 160px card, plus one `<Handle>` for the default fallback at the bottom.

**@lazy-user**: Hold on. Stop right there. A stack of tiny dots along the side of a tiny 160px card? Have you tried clicking a 10px target when there are 8 cases jammed into a 120px height? You expect me to squint, hover over dot #5, drag an edge, and pray I didn't snap to case #4 or #6? And then when all 8 edges shoot out from the right side, they’ll overlap each other into a giant blue wire hairball! I’m out. If I wanted to read spaghetti wire art, I'd go back to writing raw Python `if-elif-else` blocks.

**@bug-hunter**: The end-user is right, but the problem is ten times worse under the hood. Let's talk about Vue Flow handle position caching and re-render cycles. If `@lead-eng` renders dynamic handles using `:id="val"` where `val` is the case value (e.g., `'Active'`, `'Pending'`, `'Closed'`), what happens when a user renames `'Pending'` to `'In Review'`?
1. Vue Flow loses the handle DOM reference.
2. The connected edge's `sourceHandle` becomes an orphan (`'Pending'` handle no longer exists).
3. Vue Flow either crashes on layout calculation or teleports the edge to `(0, 0)` on the canvas.
4. Even worse, if you reorder cases in the list, Vue Flow doesn't recalculate handle bounds automatically unless you trigger `updateNodeInternals(nodeId)`. Without `updateNodeInternals()`, edges remain anchored to stale pixel coordinates!

**@ux-architect**: Exactly. We cannot treat handles as floating invisible points. In diagramming ergonomics, **a handle must be visually bonded to a clear semantic row**. Each branch in a Switch node is a decision path: a condition expression or case value, an output label, and a distinct port.
Look at how modern graph engines handle multi-branch nodes:
1. **Dynamic Node Heights**: The node card height must expand vertically per branch row so every handle gets at least `32px` of vertical target clearance.
2. **Inline Branch Rows**: Each branch needs its own visual row inside the card containing:
   - A color badge / case value label (e.g., `"val == 'High'"`).
   - An interactive output port indicator on the right edge.
   - A dedicated `<Handle>` positioned precisely at the row's vertical center.
3. **Explicit Default Branch**: The Fallback/Default path cannot be an afterthought at the bottom edge. It must be a distinct, visually highlighted row (e.g., dashed border, slate-tinted badge) anchored at the bottom of the case list.

---

### [08:15] ROUND 2: DYNAMIC EDGE ROUTING, OVERLAP COLLISIONS & PATH CALCULATIONS

**@bug-hunter**: Okay, suppose we build dynamic branch rows with expanding node heights. Now let's address the elephant on the canvas: **Edge Overlap Collisions**. If 5 branches from Node A connect to 3 different downstream nodes (or worse, 3 branches connect to the SAME downstream error handler node), standard Vue Flow edge renderers break down:
- **`BezierEdge`**: Curved paths originating from parallel handles stacked vertically will overlap and mask each other. You won't be able to tell which branch goes where without clicking every single edge.
- **`SmoothStepEdge`**: Orthogonal right-angle paths will share the exact same grid coordinate vectors `(x, y)` when turning towards the same target node, causing complete edge line blending!
- **Circular & Loop Traps**: What if a switch branch routes back to an upstream node or to the switch node itself? Standard step routing creates hidden overlapping loops that look like a single vertical line.

**@lead-eng**: That's a valid graph layout problem. But Vue Flow allows custom edge components! Instead of built-in `Bezier` or default `SmoothStep`, we can implement a custom `SwitchBranchEdge.vue` renderer.
Here is how we can solve path overlapping mathematically:
1. Every edge generated by a Switch node carries metadata: `branchIndex` and `totalBranches` in `edge.data`.
2. Inside `SwitchBranchEdge.vue`, we wrap Vue Flow's `getSmoothStepPath` or `getBezierPath` utility functions.
3. We inject a dynamic `offset` and `borderRadius` based on `branchIndex`. For example, `offset = 20 + (branchIndex * 12)`.
4. This forces orthogonal edges exiting from the same node to route along staggered parallel tracks, eliminating visual line overlap!

```javascript
// Example path calculation inside SwitchBranchEdge.vue
const path = computed(() => {
  const branchOffset = (props.data?.branchIndex || 0) * 14;
  return getSmoothStepPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    sourcePosition: props.sourcePosition,
    targetX: props.targetX,
    targetY: props.targetY,
    targetPosition: props.targetPosition,
    borderRadius: 16,
    offset: 25 + branchOffset, // Dynamic offset prevents path collisions
  });
});
```

**@lazy-user**: Now we're talking! Staggered tracks sound great, but how do I know which line belongs to which branch when I'm looking at a complex rule canvas? I don't want to hover over 10 grey lines to trace a route.
I need:
1. **Color Accents per Branch**: The output handle, the branch row badge, and the connecting edge MUST share the same distinct accent color (e.g., Amber for Case 1, Emerald for Case 2, Indigo for Case 3, Muted Slate for Default).
2. **Interactive Edge Hover & Focus**: When I hover over a branch row on the node, the corresponding edge should light up, expand stroke width from `2px` to `4px`, and show a directional glow or animated pulse!
3. **Mid-Edge Branch Badges**: Put a tiny readable label right in the middle of the edge path showing the case value (e.g., `=="VIP"` or `DEFAULT`), so I can scan the workflow at a glance.

**@ux-architect**: `@lazy-user`'s feedback highlights key graph readability principles. Let's formalize the visual edge states:
- **Default Inactive State**: `2px` stroke, subtle theme-aware stroke color (`var(--fxr-border-strong)`), `11px` pill label with backdrop blur.
- **Active / Evaluated Path State** (during test simulation / execution mode): `3px` solid stroke with pulsating stroke-dasharray animation and drop-shadow glow matching the execution status.
- **Default Fallback Edge**: `2px` stroke with `stroke-dasharray: 6, 4` (dashed pattern) to clearly signify a catch-all fallback path.
- **Hover / Selected State**: `3px` high-contrast accent stroke with a `z-index` boost (`z-index: 1000`) so the hovered edge pops above all other intersecting canvas elements.

---

### [18:40] ROUND 3: BACKEND SCHEMA SYNC, DYNAMIC HANDLES & PINIA STATE INTEGRATION

**@bug-hunter**: Visuals are fine, but let's expose the architectural state sync flaw. How does this visual layout map back to the Frappe backend JSON schema?
In FlexiRule, a `Switch` action in `ruleDoc.actions` is serialized into canonical JSON:
```json
{
  "action_id": "switch_102",
  "action_type": "Switch",
  "action_label": "Route Order Priority",
  "config": {
    "expression": "doc.order_type",
    "cases": {
      "Express": "node_shipping_fast",
      "Standard": "node_shipping_ground",
      "Bulk": "node_manual_review"
    },
    "default_next_step": "node_default_process"
  }
}
```
Look at that schema! Notice the problem?
1. In `useGraphStore.js`, standard edges connect `source` to `target` using `sourceHandle`.
2. For standard single-output actions, `next_step_if_true` holds the target. For `Condition`, `next_step_if_true` is `YES` and `next_step_if_false` is `NO`.
3. For `Switch`, target nodes are stored inside the `config.cases` dictionary (`cases[val] = target_id`) AND `config.default_next_step`!
4. If a user connects an edge from a Switch branch handle on the Vue Flow canvas, how does `useGraphStore.js` catch that event and update `config.cases` without corrupting `getStateSnapshot()` or breaking dirty state tracking?

**@lead-eng**: That is the core store integration problem. Here is how we bridge Pinia (`useGraphStore.js`) and the canonical Rule JSON:

1. **Persistent Handle ID Contract**:
   Every branch row inside `SwitchNode.vue` generates a deterministic handle ID:
   - Case Branch Handle: `handle-case-${branch.id}` (where `branch.id` is a unique immutable UUID generated on branch creation, e.g., `branch_a1b2`).
   - Default Fallback Handle: `handle-default`.

2. **Handle-to-Case Dictionary Normalization**:
   In `node.data.config`, we maintain:
   ```javascript
   config: {
     expression: "doc.order_type",
     branches: [
       { id: "b_1", value: "Express", target_id: "node_fast" },
       { id: "b_2", value: "Standard", target_id: "node_ground" }
     ],
     cases: {
       "Express": "node_fast",
       "Standard": "node_ground"
     },
     default_next_step: "node_default"
   }
   ```
   When saving or serializing, `useGraphStore.clean_action_config()` automatically compiles the `branches` array into the flat `cases` dictionary required by the backend Python execution engine (`SwitchActionHandler`).

3. **Graph Store Connection Listener (`onConnect` / `reconnect_node_edge`)**:
   When an edge connection event is emitted from Vue Flow:
   ```javascript
   function handleSwitchEdgeConnect(connection) {
     const { source, sourceHandle, target } = connection;
     if (sourceHandle === "handle-default") {
       node.data.config.default_next_step = target;
     } else if (sourceHandle.startsWith("handle-case-")) {
       const branchId = sourceHandle.replace("handle-case-", "");
       const branch = node.data.config.branches.find(b => b.id === branchId);
       if (branch) {
         branch.target_id = target;
         node.data.config.cases[branch.value] = target;
       }
     }
     useGraphStore().touch_node(source);
     useGraphStore().mark_dirty();
   }
   ```

**@bug-hunter**: What about deletion cascades?
If a user deletes a downstream target node from the canvas:
1. `useGraphStore.delete_node(targetId)` fires.
2. `delete_node` must inspect all upstream `Switch` nodes, find any `branches` or `default_next_step` referencing `targetId`, and reset them to `null`!
3. If this cleanup is missed, the Switch node will retain dead node references in its `config.cases`, causing backend execution failures during rule run time!

**@lead-eng**: Spot on. We will augment `useGraphStore.delete_node()` to include explicit Switch branch target cleansing:
```javascript
// Upstream Switch target purging inside delete_node()
nodes.value.forEach(n => {
  if (n.data?.action_type === "Switch" && n.data?.config) {
    const cfg = n.data.config;
    if (cfg.default_next_step === nodeId) {
      cfg.default_next_step = null;
    }
    if (Array.isArray(cfg.branches)) {
      cfg.branches.forEach(b => {
        if (b.target_id === nodeId) b.target_id = null;
      });
    }
    if (cfg.cases) {
      Object.keys(cfg.cases).forEach(k => {
        if (cfg.cases[k] === nodeId) delete cfg.cases[k];
      });
    }
  }
});
```

---

### [26:10] ROUND 4: CANVAS ERGONOMICS, COMPACT VS. EXPANDED MODES & PERFORMANCE

**@lazy-user**: Okay, I love the dynamic branch rows and auto-cleansing. But what happens when my Switch node has 12 cases?
A node with 12 branch rows plus header and default fallback will be 450 pixels tall! It will block half my canvas and force me to scroll forever.
Can we have a **Compact vs. Expanded View Mode**?
- **Compact View**: Displays just the node header, expression summary badge (e.g. `doc.category`), and total branch count pill (e.g. `4 Cases + Default`). Handles are collapsed or stacked neatly along the right edge with a hover menu.
- **Expanded View**: Full interactive card with inline branch rows, quick inline case editing, drag handles, and explicit handle ports.
- A single quick toggle button on the node toolbar to switch between Compact and Expanded!

**@ux-architect**: Excellent proposal. That directly addresses canvas visual density.
Let's define the two states for `SwitchNode.vue`:
1. **Expanded Mode (Default during editing)**:
   - Width: `220px`.
   - Card structure: Header, Expression Preview input, Branch List (`v-for="branch in branches"`), Fallback Branch row, Add Branch button (`+ Add Case`).
   - Every branch row has an inline output handle port positioned on the right edge (`right: -12px`).
2. **Compact Summary Mode**:
   - Width: `180px`.
   - Card structure: Compact header with accent bar, expression badge (`doc.order_type`), condensed branch indicators.
   - Outputs collapse into a single master right-port handle stack with tooltip breakdown on hover.

**@bug-hunter**: What about DOM re-rendering performance when dragging nodes or panning the canvas?
If every Switch node has 10 branch rows, 10 handles, 10 reactive badges, and Vue Flow is constantly updating node positions on mouse move:
- If we put heavy computed properties or un-memoized inline functions inside `SwitchNode.vue`, canvas drag FPS will drop from 60fps to 15fps!
- We MUST use Vue 3 `<script setup>` with `shallowRef` or strict memoization for handle bounds, and call `useVueFlow().updateNodeInternals(id)` ONLY when branch count or layout mode actually changes!

**@lead-eng**: Agreed. We will ensure:
1. `updateNodeInternals(props.id)` is debounced and triggered strictly on `branches.length` or `isExpanded` mutation via `watch(..., nextTick)`.
2. Structural node updates reuse key tracking (`:key="branch.id"`).
3. Custom edge rendering uses requestAnimationFrame-friendly SVG path generation.

---

### [34:00] ROUND 5: THE MAESTRO’S SYNTHESIS

**@maestro**: The debate has reached clear convergence. We have successfully solved the technical, architectural, performance, and UI/UX challenges of the multi-branch Switch Node on the Vue Flow canvas.

Here are the key agreed architectural decisions:
1. **Node UI/UX (`SwitchNode.vue`)**:
   - Dynamic vertically expanding card (`220px` base width) with distinct branch rows.
   - Dedicated row handle pinning (`handle-case-${branch.id}`) ensuring 1:1 visual bonding between branch value and output edge.
   - Prominent Default Fallback branch row (`handle-default`) with slate dashed styling.
   - Compact vs. Expanded presentation mode toggle for high-density diagramming.
2. **Edge Architecture (`SwitchBranchEdge.vue`)**:
   - Custom SVG edge component utilizing `getSmoothStepPath` with branch-index offset calculations to eliminate line overlap collisions.
   - Dynamic edge visual states: Active glowing pulse (simulation), Dashed slate (fallback), High-contrast accent (hover/focus).
   - Interactive mid-path edge label pills.
3. **Pinia & Schema Integration (`useGraphStore.js`)**:
   - Dual-representation mapping: normalized `branches` array (`{ id, value, target_id }`) synchronized with canonical `config.cases` dictionary.
   - Automated upstream deletion cascading inside `delete_node()`.
   - Reactive handle re-indexing via `updateNodeInternals()` on structural branch changes.

I will now compile these decision points into the official, production-ready **Switch Node & Dynamic Edge Routing Implementation Proposal**.

---

# 🚀 ARCHITECTURE PROPOSAL: FlexiRule Switch Action Node & Dynamic Edge Routing

## 1. Executive Summary & Design Philosophy
The **Switch Action Type Node** provides multi-branch conditional routing within the FlexiRule decision automation canvas. Unlike standard binary decision nodes (`ConditionNode.vue` with `YES / NO` paths), a Switch node evaluates a Python expression (e.g., `doc.category` or `doc.priority`) and routes rule execution dynamically down $N$ discrete case paths plus a mandatory Default Fallback path.

### Core Vision & Design Philosophy:
- **Zero-Friction Ergonomics**: Workflow authors can add, edit, reorder, and visually connect switch cases directly on the Vue Flow canvas without constant modal switching.
- **Anti-Spaghetti Edge Routing**: Prevents edge overlapping and line blending using custom orthogonal step-path offset algorithms (`SwitchBranchEdge.vue`).
- **Deterministic Handle Keying**: Maintains strict 1:1 state binding between visual handle ports, Pinia graph edges, and Frappe backend JSON action payloads (`config.cases` and `config.default_next_step`).
- **Visual Hierarchy & Scalability**: Supports dual presentation modes (**Expanded Card** vs. **Compact Summary**) to ensure clean canvas rendering even when handling 10+ decision branches.

---

## 2. Switch Node UI/UX Specification (`SwitchNode.vue`)

### 2.1 Node Anatomy
The `SwitchNode.vue` component renders a custom Vue Flow node with a base width of `220px` in Expanded Mode and `180px` in Compact Mode.

```
+-------------------------------------------------------+
|  [🔀 SWITCH]  Route Order Priority          [⚙️][👁️][🗑️] |  <-- Node Header & Toolbar
+-------------------------------------------------------+
| Expression: {{ doc.order_type }}                      |  <-- Expression Summary
+-------------------------------------------------------+
| BRANCHES                                              |
|  [●] Case 1: "Express"                     (o)------|  <-- Source Handle (handle-case-b1)
|  [●] Case 2: "Standard"                    (o)------|  <-- Source Handle (handle-case-b2)
|  [●] Case 3: "Bulk"                        (o)------|  <-- Source Handle (handle-case-b3)
|  [➕ Add Case Branch]                                 |  <-- Inline Trigger
+-------------------------------------------------------+
| FALLBACK                                              |
|  [⮞] Default / Fallback                    (o)------|  <-- Source Handle (handle-default)
+-------------------------------------------------------+
| [✓ Configured]                                        |  <-- Node Status Footer
+-------------------------------------------------------+
```

1. **Node Header & Accent Bar**:
   - Accent Color: `#8b5cf6` (Purple / Router Accent).
   - Icon: `fa-code-fork` or `fa-random`.
   - Title: Inline editable label (`InlineEditor.vue`) bound to `data.action_label`.
   - Action Toolbar (`NodeToolbar.vue`): Quick buttons for Configure Modal, Mode Toggle (Compact/Expanded), and Delete.
2. **Expression Summary Bar**:
   - Compact Python code badge showing the switch target expression (e.g., `doc.order_category`).
3. **Dynamic Branch Case List (`.switch-branch-list`)**:
   - Renders individual case rows for each entry in `data.config.branches`.
   - Each row features an inline handle port (`<Handle type="source" ... />`), case value pill, and quick inline removal trigger.
4. **Default Fallback Branch Row (`.switch-fallback-row`)**:
   - Pinned at the bottom of the case container.
   - Distinct dashed border and muted slate badge (`var(--fxr-surface-muted)`).
   - Holds the catch-all target handle (`handle-default`).
5. **Add Branch Trigger (`.add-branch-btn`)**:
   - Inline trigger allowing single-click addition of a new switch branch directly on the canvas.

### 2.2 Dynamic Handle Management
To prevent Vue Flow handle key collisions and edge orphan states during branch reordering or deletion:

| Handle Name | Handle Type | Handle ID Format | Position | Accent Style |
| :--- | :--- | :--- | :--- | :--- |
| **Input Target** | `target` | `target` | Left (`Position.Left`) | `#8b5cf6` (Solid Border) |
| **Case Branch** | `source` | `handle-case-${branch.id}` | Right (`Position.Right`) | Palette Accents (Amber, Emerald, Cyan) |
| **Default Fallback** | `source` | `handle-default` | Right (`Position.Right`) | `#64748b` (Dashed Slate) |

- **Deterministic ID Binding**: `branch.id` uses immutable UUIDs (e.g. `b_8f1a`) generated on creation, completely decoupling handle identities from volatile user-typed case strings.
- **Dynamic Handle Re-indexing**: When a branch is added, reordered, or deleted, `SwitchNode.vue` invokes `useVueFlow().updateNodeInternals(props.id)` within `nextTick()` to force Vue Flow to recalculate port coordinates.

### 2.3 Visual Micro-Interactions & States
- **Hover/Highlight Synchronization**: Hovering over a branch row lights up the corresponding source handle and highlights its connected canvas edge with an elevated `z-index`.
- **Validation Error Badges**: If a branch value is empty, duplicate, or missing a connected target node, an inline error indicator (`fa-exclamation-triangle`) is displayed beside the row.
- **Compact vs. Expanded Toggle**:
  - **Expanded Mode**: Displays full inline rows with handles and controls.
  - **Compact Mode**: Condenses height to `80px`, displaying the expression badge and branch count pill (`3 Cases + Fallback`), while collapsing handles to a right-aligned vertical stack with hover tooltips.

---

## 3. Vue Flow Edge Connection Architecture & Routing

### 3.1 Edge Layout Strategy (`SwitchBranchEdge.vue`)
Standard orthogonal (`SmoothStepEdge`) or curved (`BezierEdge`) paths collapse into overlapping lines when multiple handles exit vertically from the same node side. FlexiRule addresses this with a custom SVG edge component: `SwitchBranchEdge.vue`.

```
Switch Node
+--------------------+
| Case 1 (b1) -------+====== offset: 20px ======\
| Case 2 (b2) -------+======== offset: 34px ======\------> Downstream Target A
| Case 3 (b3) -------+========== offset: 48px =====\-----> Downstream Target B
| Default (def) -----+============ offset: 62px ====\----> Downstream Target C
+--------------------+
```

- **Staggered Orthogonal Path Offsets**:
  `SwitchBranchEdge.vue` computes path vectors using Vue Flow's `getSmoothStepPath()`, supplying a dynamic `offset` proportional to the branch index:
  $$\text{Path Offset} = \text{Base Offset } (20\text{px}) + (\text{Branch Index} \times 14\text{px})$$
  This guarantees that parallel edges exiting from adjacent handles run along distinct horizontal and vertical lanes.

### 3.2 Edge Visual Styling Matrix

```css
/* Custom Edge CSS Rules */
.fxr-switch-edge {
  stroke-width: 2px;
  transition: stroke 0.2s, stroke-width 0.2s, filter 0.2s;
}

.fxr-switch-edge.is-case {
  stroke: var(--fxr-edge-case, #8b5cf6);
}

.fxr-switch-edge.is-default {
  stroke: var(--fxr-edge-default, #64748b);
  stroke-dasharray: 6, 4;
}

.fxr-switch-edge.is-hovered,
.fxr-switch-edge.is-selected {
  stroke-width: 4px !important;
  filter: drop-shadow(0 0 6px rgba(139, 92, 246, 0.5));
  z-index: 1000 !important;
}

.fxr-switch-edge.is-evaluated-active {
  stroke: #10b981 !important;
  stroke-width: 3px !important;
  stroke-dasharray: 8, 4;
  animation: fxr-edge-flow 1s linear infinite;
}

@keyframes fxr-edge-flow {
  from { stroke-dashoffset: 24; }
  to { stroke-dashoffset: 0; }
}
```

1. **Active / Evaluated Path State** (Execution Simulation Mode):
   - Solid Emerald stroke (`#10b981`) with animated stroke-dashoffset directional flow.
   - Accompanied by execution step order badges.
2. **Default / Fallback Edge**:
   - Distinct dashed stroke (`stroke-dasharray: 6, 4`) in muted slate (`#64748b`).
3. **Disabled / Invalid Edge**:
   - Muted semi-transparent gray with inline error badge if target node is missing or disabled.

### 3.3 Edge Labeling & Handles
- **Mid-Path Branch Pills**: Rendered using `<EdgeLabelRenderer>` at `[labelX, labelY]`.
- Displays the case value in a compact, backdrop-blurred pill (e.g. `== "Express"` or `DEFAULT`).
- Clicking an edge label highlights the source branch row inside `SwitchNode.vue`.

---

## 4. Technical Implementation Blueprint

### 4.1 Vue 3 Component Structure (`SwitchNode.vue`)

```vue
<script setup>
import { computed, ref, watch, nextTick } from "vue";
import { Handle, Position, useVueFlow } from "@vue-flow/core";
import { useGraphStore, useRuleStore } from "../../stores";
import NodeToolbar from "./NodeToolbar.vue";
import InlineEditor from "./InlineEditor.vue";
import NodeStatusIndicator from "./NodeStatusIndicator.vue";

const props = defineProps(["id", "data", "selected"]);
const graphStore = useGraphStore();
const ruleStore = useRuleStore();
const { updateNodeInternals } = useVueFlow();

const isExpanded = ref(true);

// Normalise branches array from data.config
const branches = computed(() => {
	const config = graphStore.clean_action_config(props.data?.config, { actionType: "Switch" });
	return config.branches || [];
});

// Re-index handles whenever branch structure changes
watch(
	() => branches.value.length,
	async () => {
		await nextTick();
		updateNodeInternals(props.id);
	}
);

function addBranch() {
	const currentConfig = { ...(props.data?.config || {}) };
	const newBranches = [...(currentConfig.branches || [])];
	const newId = `b_${Date.now().toString(36)}`;
	newBranches.push({ id: newId, value: `Case ${newBranches.length + 1}`, target_id: null });

	currentConfig.branches = newBranches;
	props.data.config = currentConfig;
	graphStore.touch_node(props.id);
	graphStore.mark_dirty();
}

function removeBranch(branchId) {
	const currentConfig = { ...(props.data?.config || {}) };
	currentConfig.branches = (currentConfig.branches || []).filter((b) => b.id !== branchId);

	// Clean corresponding edge
	graphStore.edges = graphStore.edges.filter(
		(e) => !(e.source === props.id && e.sourceHandle === `handle-case-${branchId}`)
	);

	props.data.config = currentConfig;
	graphStore.touch_node(props.id);
	graphStore.mark_dirty();
}
</script>

<template>
	<div
		class="switch-node-card"
		:class="{ selected: selected, 'is-compact': !isExpanded }"
	>
		<Handle type="target" :position="Position.Left" id="target" class="handle-target" />

		<NodeToolbar
			:node-id="id"
			:selected="selected"
			@configure="graphStore.open_config(id)"
			@delete="graphStore.delete_node(id)"
		>
			<button class="btn-xs" @click="isExpanded = !isExpanded" :title="__('Toggle View')">
				<i :class="['fa', isExpanded ? 'fa-compress' : 'fa-expand']"></i>
			</button>
		</NodeToolbar>

		<div class="node-header">
			<i class="fa fa-code-fork icon-switch"></i>
			<InlineEditor v-model:value="data.action_label" tag="span" class="node-title" />
		</div>

		<!-- Expanded Mode -->
		<div v-if="isExpanded" class="node-body">
			<div class="expr-preview">
				<span class="expr-label">{{ __("Switch On:") }}</span>
				<code>{{ data.config?.expression || 'doc.status' }}</code>
			</div>

			<div class="branch-section">
				<div
					v-for="(branch, idx) in branches"
					:key="branch.id"
					class="branch-row"
				>
					<span class="branch-pill">Case {{ idx + 1 }}: {{ branch.value }}</span>
					<button class="btn-remove-branch" @click.stop="removeBranch(branch.id)">
						<i class="fa fa-times"></i>
					</button>
					<Handle
						type="source"
						:position="Position.Right"
						:id="`handle-case-${branch.id}`"
						class="handle-branch"
					/>
				</div>

				<button class="btn-add-branch" @click="addBranch">
					<i class="fa fa-plus"></i> {{ __("Add Case Branch") }}
				</button>
			</div>

			<!-- Fallback Row -->
			<div class="fallback-row">
				<span class="fallback-pill">{{ __("Default / Fallback") }}</span>
				<Handle
					type="source"
					:position="Position.Right"
					id="handle-default"
					class="handle-fallback"
				/>
			</div>
		</div>

		<!-- Compact Summary Mode -->
		<div v-else class="node-body-compact">
			<span class="compact-badge">{{ branches.length }} Cases + Default</span>
		</div>
	</div>
</template>
```

### 4.2 Pinia State & Rule Schema Mapping (`useGraphStore.js`)

When serializing graph data to save to the Frappe backend, `useGraphStore.clean_action_config()` normalizes the switch configuration structure:

```javascript
// Graph Store Normalization for Switch Actions inside clean_action_config()
if (actionType === "Switch") {
  const branches = clean.branches || [];
  const casesDict = {};

  branches.forEach(b => {
    if (b.value && b.target_id) {
      casesDict[b.value] = b.target_id;
    }
  });

  return {
    expression: clean.expression || "",
    branches: branches,
    cases: casesDict, // Flat dictionary required by backend SwitchActionHandler
    default_next_step: clean.default_next_step || null
  };
}
```

#### Automated Deletion Cascade in `delete_node(nodeId)`:
When any node is deleted from the graph, `useGraphStore.delete_node()` strips all stale target references in upstream Switch nodes:
```javascript
// Upstream Switch target purging inside delete_node()
nodes.value.forEach(n => {
  if (n.data?.action_type === "Switch" && n.data?.config) {
    const cfg = n.data.config;
    if (cfg.default_next_step === nodeId) {
      cfg.default_next_step = null;
    }
    if (Array.isArray(cfg.branches)) {
      cfg.branches.forEach(b => {
        if (b.target_id === nodeId) b.target_id = null;
      });
    }
    if (cfg.cases) {
      Object.keys(cfg.cases).forEach(k => {
        if (cfg.cases[k] === nodeId) delete cfg.cases[k];
      });
    }
  }
});
```

### 4.3 Performance & Canvas Optimization
1. **Debounced Handle Re-indexing**:
   Calls to `updateNodeInternals()` are batched using `nextTick()` to prevent multiple DOM reflows when bulk operations occur.
2. **Memoized Edge Path Renderers**:
   `SwitchBranchEdge.vue` uses Vue `computed()` properties for SVG path generation, ensuring edge paths are recalculated strictly when handle coordinates or canvas viewport transform changes.
3. **Passive Drag Event Overhead**:
   Handle elements utilize CSS `pointer-events: all` strictly on port targets, preventing canvas panning drag listeners from tripping on hidden handle hitboxes.

---

## 5. Verification & Rollout Plan

| Step | Objective | Target File(s) | Verification Strategy |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Implement `SwitchNode.vue` component with dynamic branch rows & handles. | `components/nodes/SwitchNode.vue` | Inspect DOM rendering & handle generation in Vue DevTools. |
| **Phase 2** | Create `SwitchBranchEdge.vue` custom edge component with offset paths. | `components/edges/SwitchBranchEdge.vue` | Verify no line overlap with 5+ connected branch edges. |
| **Phase 3** | Update Pinia `useGraphStore.js` sync, edge connection listeners, and delete cascades. | `stores/useGraphStore.js` | Test adding/deleting cases & target nodes; check rule JSON. |
| **Phase 4** | Register Switch node & edge types in Vue Flow canvas setup. | `App.vue` / `Canvas.vue` | Validate end-to-end drag, connect, save, and simulation workflows. |

---
*End of Architecture Proposal.*
