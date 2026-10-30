# 🚀 ARCHITECTURE PROPOSAL: FlexiRule Switch Action Node & Dynamic Edge Routing

## Phase 1: The War Room Debate (Live Unfiltered Transcript)

**Date & Time:** Thursday, 14:00 UTC
**Location:** FlexiRule Core Architecture War Room (Closed-Door Session)
**Subject:** Switch Action Type Node & Dynamic Edge Routing Architecture for Vue Flow Canvas
**Panelists:**
- **"The Lead Engineer"**: Core Architecture, Pinia State, Vue Flow & Frappe Backend Contracts
- **"Devil’s Advocate"**: Bug-hunter, Edge Case Inquisitor & Canvas Stress Tester
- **"The Lazy End-User"**: Low-patience Workflow Builder & Visual Spaghetti Critic
- **"The UX/UI Canvas Specialist"**: Interactive Graph Visualization & Diagramming Architect
- **"The Maestro"**: Systems Orchestrator & Final Architectural Arbiter

---

### [TRANSCRIPT BEGINS]

**The Lead Engineer:** Let’s get straight to the whiteboard. In FlexiRule right now, every action node on the Vue Flow canvas follows a rigid topological pattern: a single `target` input handle at the top or left, and either a single output handle (`next_step_if_true`) or binary output handles like `ConditionNode` (`true` / `false`). But our engine has a `Switch` handler (`flexirule/ruleflow/core/action_handlers/switch.py`) that evaluates an expression like `doc.status` against arbitrary case dictionaries:
```json
{
  "expression": "doc.status",
  "cases": {
    "Draft": "action_id_draft",
    "Pending": "action_id_pending",
    "Approved": "action_id_approved"
  }
}
```
Currently, on the canvas, users configure this in a detached modal (`SwitchConfig.vue`). When branches are defined, the node doesn't reflect individual branches visually on the graph. We want to promote `Switch` to a first-class canvas node (`SwitchNode.vue`) with dynamic handles per branch, allowing direct interactive wire routing.

**Devil’s Advocate:** Stop right there. A naive implementation of dynamic handles on Vue Flow is a guaranteed disaster. Have you actually benchmarked what happens when you dynamically inject `<Handle />` elements into an existing node inside Vue Flow?
First: **Handle Coordinate Desynchronization and Phantom Edges**. When a user adds or reorders a branch row in the Vue template, Vue re-renders the DOM, changing the vertical offsets. But Vue Flow caches handle bounds in `nodeInternals`. If you don't invoke `updateNodeInternals(node.id)` at the exact right microtask lifecycle, Vue Flow draws edges to old coordinates or `NaN, NaN`, leaving broken ghost lines.
Second: **Handle ID Collision & Detachment**. In your naive backend contract, the case key is `"Draft"`. If a user is typing in a text field and changes `"Draft"` to `"Drafting"`, the handle ID changes from `"Draft"` to `"Drafting"`. Vue Flow detects that handle `"Draft"` disappeared, instantly severing the connected edge! The user just wanted to edit a label, and their canvas wiring vanished!
Third: **Edge Overlap & Collision Horror**. If a user routes four switch branches into the same downstream error handler or logging node, standard Bezier or SmoothStep edges render directly on top of one another. It looks like a single thick smudge.

**The Lazy End-User:** Preach! Listen to the Devil's Advocate! I’m the one who has to use this thing. In other rule builders, as soon as you have a switch node with 5 branches, the canvas turns into an illegible bowl of squid-ink spaghetti.
1. I can’t tell which wire corresponds to which case without hovering and squinting.
2. If I have 6 branches, the node becomes taller than my entire monitor, pushing all other nodes out of view.
3. Snapping is infuriating. When I drag a line from handle 3, it accidentally snaps to handle 2 because the handles are crammed 10 pixels apart.
4. And where on earth is the fallback? If my document status is `"Cancelled"`, and I didn't write a case for it, what happens? Does the rule silently swallow the doc or crash? If there isn’t a crystal-clear, distinct "Default Fallback" wire on the canvas, I’m not touching this.

**The UX/UI Canvas Specialist:** Take a breath, everyone. These are solvable interaction design challenges. Let's dissect the visual mechanics:
1. **Dynamic Stacked Branch Anatomy**: A Switch Node cannot just be a generic rectangle. It needs an explicit itemized table layout. Each branch is an individual row element with a minimum height of 36px (comfortably exceeding touch/click target guidelines). The handle isn't floating arbitrarily; it is pinned to the right edge of each specific branch row.
2. **Handle ID Decoupling**: Devil's Advocate hit the bullseye on label renaming. The canvas handle identifier MUST NEVER be the condition string. Each branch must have an immutable, unique internal identifier—say `branch_id: "br_x7k9"`. The edge connects to `sourceHandle: "br_x7k9"`. The condition expression and label can change a hundred times, and the edge remains firmly anchored.
3. **Collapsible Workspace Footprint**: To address the Lazy End-User's valid complaint about monstrous nodes: the Switch Node must have two display modes:
   - *Expanded Mode (Authoring)*: Displays the expression banner, full list of cases with inline value badges, fallback branch, and "+ Add Branch" button.
   - *Compact Mode (Overview)*: Folds into a 48px header showing `Switch: doc.status (4 branches)`. The individual handles collapse into a grouped visual port, or the node maintains clean anchor routing without blowing up canvas real estate.
4. **Collision-Free Orthogonal Routing**: Standard `default` edges won't cut it. We must create a dedicated `SwitchEdge.vue` renderer using `getSmoothStepPath` with **calculated dynamic channel offsets**. If 4 edges share the same target, each edge receives an incremental orthogonal offset: `offset = baseOffset + (branchIndex * 16px)`. They will run strictly in parallel corridors like printed circuit board (PCB) traces!

**The Lead Engineer:** That solves the visual layout and interaction, but let's dive into the execution contract and state synchronization. How does this map to Pinia (`useGraphStore.js`) and the Frappe DocType backend?
In our engine, execution is strictly deterministic:
- Switch node receives an incoming context.
- It evaluates `config.expression`.
- It matches the evaluated scalar against `config.cases`.
- If matched, it follows `cases[val]` (the target node ID).
- If no match, it **must** fall back to `next_step_if_true`, which represents the `default` fallback handle!

Now, look at the synchronization lifecycle in Pinia:
When a branch is added in `SwitchNode.vue`:
```typescript
function addBranch(label, value) {
  const branchId = `branch_${nanoid(6)}`;
  node.data.config.branches.push({ id: branchId, label, value });
  nextTick(() => {
    updateNodeInternals(node.id);
  });
}
```
And what happens when a user deletes a branch?
```typescript
function removeBranch(branchId) {
  // Prune branch from node config
  node.data.config.branches = node.data.config.branches.filter(b => b.id !== branchId);
  // Synchronize edges in store immediately to prevent orphan edges
  graphStore.edges = graphStore.edges.filter(
    e => !(e.source === node.id && e.sourceHandle === branchId)
  );
  nextTick(() => {
    updateNodeInternals(node.id);
  });
}
```
Notice how deleting a branch synchronously removes the associated edge before the next render tick. That prevents Vue Flow from ever querying a non-existent handle!

**Devil’s Advocate:** Good, but you missed two critical edge cases:
First: **Evaluation Type Coercion Traps**. In Python, `doc.status` might evaluate to an integer `1` (or a boolean `True`), while JSON keys are strictly strings (`"1"`). If a user specifies a case for numeric values or types, the backend does:
```python
next_id = cases.get(val) or cases.get(str(val)) or action.next_step_if_true
```
Our frontend schema validator must enforce valid literal types and prevent duplicate case keys! If the user enters `"Draft"` in branch 1 and `"Draft"` in branch 2, which branch does the engine execute? It's ambiguous!
Second: **Parallel vs. Sequential Semantics**. What if someone wants pattern matching or expression conditions per branch instead of a single scalar switch? For instance: `Case 1: amount > 1000`, `Case 2: amount <= 1000`? If we only support scalar equality, users will complain.

**The Lazy End-User:** Wait, don't overcomplicate it! If I want complex boolean logic, I use a `ConditionNode`. A `SwitchNode` should be for classic switching: evaluating a single property or expression against multiple values! Like an enum or state machine! But I DO want the canvas to warn me if I create two identical cases. Put an orange badge on duplicate branches!
And what about edge styles? When I test-run the rule, I want the active edge that fired to light up!

**The UX/UI Canvas Specialist:** Exactly. Visual hierarchy and state feedback:
1. **Interactive Edge States**:
   - **Inactive / Dormant**: Subtle cyan (`#06b6d4`, 2px stroke) with standard arrowhead.
   - **Active / Evaluated**: Glowing emerald pulse (`#10b981`, 3px stroke, animated SVG `stroke-dasharray` and drop-shadow filter) indicating runtime traversal.
   - **Default Fallback**: Distinct charcoal/slate dashed pattern (`#64748b`, stroke-dasharray `6,4`) with an inline pill label reading `⚡ Default`.
   - **Invalid / Orphan**: Red dashed stroke (`#ef4444`) if the branch target is missing or points to a non-existent node.
2. **Inline Edge Labels**: Every branch edge renders an interactive label positioned at `labelX, labelY` returned by `getSmoothStepPath`. The label shows the branch value (e.g. `[="Draft"]`), with a 1-click delete button on hover.

**The Lead Engineer:** And on the backend serialization contract:
We maintain backward compatibility with `flexirule/ruleflow/core/action_handlers/switch.py`.
When `serializeRule()` is called:
```typescript
function serializeSwitchNode(node, edges) {
  const cases = {};
  let defaultTarget = null;

  edges.filter(e => e.source === node.id).forEach(edge => {
    if (edge.sourceHandle === 'default') {
      defaultTarget = edge.target;
    } else {
      const branch = node.data.config.branches.find(b => b.id === edge.sourceHandle);
      if (branch && branch.value !== undefined) {
        cases[String(branch.value)] = edge.target;
      }
    }
  });

  return {
    action_type: 'Switch',
    name: node.id,
    next_step_if_true: defaultTarget,
    config: {
      expression: node.data.config.expression,
      cases: cases
    }
  };
}
```
This guarantees 100% adherence to FlexiRule's existing rule execution engine and test suites!

**The Maestro:** Excellent. The debate has rigorously addressed:
1. Dynamic handle DOM synchronization without coordinate lag (`updateNodeInternals` debounced in RAF).
2. Immutable handle IDs (`branch_id`) to prevent wire breakage during label editing.
3. Dedicated `SwitchEdge.vue` with parallel channel offset algorithm to eradicate edge spaghetti.
4. Distinct visual styles for Active, Fallback, and Invalid edge states.
5. Strict schema validation (duplicate key detection, type coercion, and backward-compatible serialization).

I will now compile the definitive architectural specification and implementation proposal.

---

### [TRANSCRIPT ENDS]

---

## Phase 2: The Maestro’s Decision & Proposal Document

# 🚀 ARCHITECTURE PROPOSAL: FlexiRule Switch Action Node & Dynamic Edge Routing

## 1. Executive Summary & Design Philosophy
The **FlexiRule Switch Action Node** elevates multi-branch conditional routing from hidden property modals directly onto the visual Vue Flow canvas. Traditional rule builders often degrade into visually chaotic "edge spaghetti" when multi-branching nodes are introduced.

This architecture proposal delivers a clean, scalable, and reactive multi-branch routing system founded on four foundational pillars:
1. **Immutable Handle Identification**: Handles are decoupled from user-editable condition strings by assigning unique, stable UUIDs (`branch_id`), guaranteeing zero edge detachment during branch editing.
2. **Spatial Row-Handle Synchronization**: Handles are embedded directly within branch list items in `SwitchNode.vue` and synchronized with Vue Flow’s coordinate system via microtask-debounced `updateNodeInternals`.
3. **Parallel Orthogonal Edge Routing**: Custom SVG `SwitchEdge.vue` components use dynamic channel offsets (`getSmoothStepPath` with stepped corridors) to eliminate edge collision and overlap.
4. **Canonical Engine Contract Compliance**: The visual branch representation serializes cleanly into FlexiRule’s existing `SwitchHandler` backend specification (`expression`, `cases`, and fallback `next_step_if_true`).

---

## 2. Switch Node UI/UX Specification (`SwitchNode.vue`)

### 2.1 Node Anatomy & Visual Layout
The Switch Node is designed as a structured card utilizing Tailwind CSS classes, organized into four distinct visual zones:

```
+-------------------------------------------------------------+
| 🔀 SWITCH: Document Router                   [ ⤢ ] [ ✕ ]   |  Zone 1: Header & Controls
| Expr: doc.workflow_state                                    |
+-------------------------------------------------------------+
| ┌─────────────────────────────────────────────────────────┐ |
| │ 1. "Draft"                      [ -> Create_Task ]  (o) │ |  Zone 2: Dynamic Branch Rows
| ├─────────────────────────────────────────────────────────┤ |        with Pinned Source Handles
| │ 2. "Under Review"               [ -> Assign_Lead ]  (o) │ |
| ├─────────────────────────────────────────────────────────┤ |
| │ 3. "Approved"                   [ -> Emit_Event  ]  (o) │ |
| └─────────────────────────────────────────────────────────┘ |
+-------------------------------------------------------------+
| ⚡ Default Fallback                [ -> Log_Audit   ]  (o) │  Zone 3: Default Fallback Branch
+-------------------------------------------------------------+
| ➕ Add Case Branch                                          |  Zone 4: Action Trigger
+-------------------------------------------------------------+
```

1. **Header Zone**:
   - Icon: Cyan router icon (`fa fa-random`).
   - Title: Action display name with inline editable label.
   - Expression pill badge: Displays current context path (e.g. `doc.status`).
   - Action controls: Toggle Collapse/Expand (`[⤢]`), Configuration settings dialog (`[⚙]`), Delete node (`[✕]`).
2. **Dynamic Branch Rows (Case Branches)**:
   - Ordered list of registered branch cases.
   - Each row features an index counter, value editor, target preview badge, and delete row action.
   - Integrated Vue Flow `<Handle type="source" />` pinned to the right edge with interactive hover states.
3. **Default Fallback Branch**:
   - Fixed baseline branch representing the execution engine's fallback route (`next_step_if_true`).
   - Rendered with muted slate border and distinct amber/gray fallback badge.
   - Dedicated fallback source handle (`id="default"`).
4. **Action Trigger Zone**:
   - Dashed button allowing instant inline addition of new case branches without opening full configuration dialogs.

### 2.2 Micro-Interactions & Handle Pinning
- **Handle Snapping & Sizing**: Handles are styled with a base diameter of 12px, expanding to 18px on hover with an active glow ring (`ring-4 ring-cyan-500/30`).
- **Snapping Magnetism**: Configured with a 20px snap radius (`connectionRadius: 20`) to eliminate user friction when routing edges.
- **Collapsible Mode**:
  - In collapsed state, the node contracts to 44px height: `Switch: doc.status (3 branches)`.
  - Individual branch handles fold gracefully into a singular grouped output port, maintaining graph readability on high-density diagrams.

---

## 3. Vue Flow Edge Connection Architecture & Routing

### 3.1 Custom Orthogonal Routing (`SwitchEdge.vue`)
To eliminate the visual collision of multiple wires connecting to the same downstream target, `SwitchEdge.vue` implements computed channel offsets using Vue Flow’s `getSmoothStepPath`:

```vue
<!-- SwitchEdge.vue -->
<template>
  <g class="vue-flow__edge-switch">
    <path
      :id="id"
      :class="['vue-flow__edge-path', edgeClasses]"
      :d="edgePath"
      :marker-end="markerEnd"
      :style="edgeStyles"
    />
    <EdgeLabelRenderer v-if="data?.label">
      <div
        :style="{
          position: 'absolute',
          transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
          pointerEvents: 'all'
        }"
        class="nodrag nopan switch-edge-badge"
      >
        <span :class="badgeClasses">{{ data.label }}</span>
      </div>
    </EdgeLabelRenderer>
  </g>
</template>

<script setup>
import { computed } from 'vue';
import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath, Position } from '@vue-flow/core';

const props = defineProps({
  id: { type: String, required: true },
  sourceX: { type: Number, required: true },
  sourceY: { type: Number, required: true },
  targetX: { type: Number, required: true },
  targetY: { type: Number, required: true },
  sourcePosition: { type: String, default: Position.Right },
  targetPosition: { type: String, default: Position.Left },
  data: { type: Object, default: () => ({}) },
  markerEnd: { type: String }
});

// Dynamic Corridor Channel Offset Algorithm
const edgePathData = computed(() => {
  const branchIndex = props.data?.branchIndex || 0;
  const totalBranches = props.data?.totalBranches || 1;

  // Calculate dynamic orthogonal separation (14px corridor per branch)
  const channelSpread = (branchIndex - (totalBranches - 1) / 2) * 14;
  const dynamicOffset = Math.max(24, 20 + Math.abs(channelSpread));

  return getSmoothStepPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    sourcePosition: props.sourcePosition,
    targetX: props.targetX,
    targetY: props.targetY,
    targetPosition: props.targetPosition,
    borderRadius: 8,
    offset: dynamicOffset
  });
});

const edgePath = computed(() => edgePathData.value[0]);
const labelX = computed(() => edgePathData.value[1]);
const labelY = computed(() => edgePathData.value[2]);

const isFallback = computed(() => props.data?.isFallback || false);
const isActive = computed(() => props.data?.isActive || false);

const edgeClasses = computed(() => ({
  'stroke-cyan-500': !isFallback.value && !isActive.value,
  'stroke-emerald-400 stroke-[3px] filter drop-shadow': isActive.value,
  'stroke-slate-400 stroke-dashed': isFallback.value
}));

const edgeStyles = computed(() => ({
  strokeDasharray: isFallback.value ? '6,4' : undefined,
  animation: isActive.value ? 'switch-edge-flow 1s linear infinite' : undefined
}));
</script>
```

### 3.2 Visual State Matrix

| State | Primary Color | Stroke Width | Stroke Pattern | Label / Marker Style | Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Normal Branch** | Cyan-500 (`#06b6d4`) | 2px | Solid | Cyan text pill, cyan arrowhead | Standard conditional branch connection |
| **Active / Fired** | Emerald-400 (`#34d399`)| 3px | Animated Pulse | Emerald glow, pulse animation | Execution test-run telemetry visualization |
| **Default Fallback** | Slate-400 (`#94a3b8`) | 2px | Dashed `6,4` | Slate pill with ⚡ icon | Unmatched fallthrough route (`next_step_if_true`) |
| **Warning / Loop** | Amber-500 (`#f59e0b`) | 2px | Dotted `4,4` | Amber warning badge | Potential circular loop warning |
| **Invalid / Empty** | Rose-500 (`#f4395e`) | 2px | Solid | Rose badge `[Missing Target]` | Unconnected branch handle |

---

## 4. Technical Implementation Blueprint

### 4.1 Vue 3 Component Implementation (`SwitchNode.vue`)

```vue
<!-- flexirule/public/js/flexirule/rule_builder/components/nodes/SwitchNode.vue -->
<template>
  <div
    class="flexirule-switch-node bg-slate-900 border-2 rounded-xl text-slate-100 shadow-2xl transition-all duration-200 select-none"
    :class="[
      isSelected ? 'border-cyan-400 ring-2 ring-cyan-500/20' : 'border-slate-700 hover:border-slate-500',
      isCollapsed ? 'w-64' : 'w-80'
    ]"
  >
    <!-- Node Header -->
    <div class="flex items-center justify-between px-3 py-2.5 bg-slate-800/90 rounded-t-xl border-b border-slate-700/80">
      <div class="flex items-center space-x-2 truncate">
        <span class="w-6 h-6 rounded-lg bg-cyan-500/20 text-cyan-400 flex items-center justify-center text-xs">
          <i class="fa fa-random"></i>
        </span>
        <span class="font-semibold text-xs tracking-wide truncate text-slate-200">
          {{ data.action_label || 'Switch' }}
        </span>
      </div>
      <div class="flex items-center space-x-1 nodrag">
        <button
          @click="toggleCollapse"
          class="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-700 transition-colors"
          :title="isCollapsed ? 'Expand Node' : 'Collapse Node'"
        >
          <i :class="isCollapsed ? 'fa fa-expand' : 'fa fa-compress'" class="text-[10px]"></i>
        </button>
      </div>
    </div>

    <!-- Expression Evaluation Subheader -->
    <div class="px-3 py-1.5 bg-slate-950/60 border-b border-slate-800 text-[11px] font-mono flex items-center justify-between">
      <span class="text-slate-400">Expr:</span>
      <span class="text-cyan-300 font-medium truncate max-w-[180px]" :title="expression">
        {{ expression || '<not set>' }}
      </span>
    </div>

    <!-- Branch Items (Expanded State) -->
    <div v-if="!isCollapsed" class="p-2 space-y-1.5">
      <!-- Case Branch Rows -->
      <div
        v-for="(branch, idx) in branches"
        :key="branch.id"
        class="group relative flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-slate-800/60 hover:bg-slate-800 border border-slate-700/50 hover:border-slate-600 transition-all text-xs"
      >
        <div class="flex items-center space-x-2 truncate pr-4">
          <span class="text-slate-500 font-mono text-[10px]">{{ idx + 1 }}.</span>
          <input
            type="text"
            v-model="branch.value"
            @input="onBranchChange"
            placeholder="case value"
            class="nodrag bg-transparent border-none text-slate-200 focus:text-white text-xs p-0 focus:ring-0 font-mono w-28 truncate"
          />
        </div>

        <button
          @click="deleteBranch(branch.id)"
          class="nodrag opacity-0 group-hover:opacity-100 text-slate-500 hover:text-rose-400 transition-opacity p-0.5"
          title="Delete Branch"
        >
          <i class="fa fa-times text-[10px]"></i>
        </button>

        <!-- Pinned Dynamic Handle for Case Branch -->
        <Handle
          type="source"
          :id="branch.id"
          :position="Position.Right"
          class="!w-3 !h-3 !-right-1.5 !bg-cyan-500 hover:!bg-cyan-300 !border-2 !border-slate-900 transition-transform hover:scale-125"
        />
      </div>

      <!-- Default Fallback Branch -->
      <div class="relative flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-slate-950/40 border border-dashed border-slate-700/80 text-xs text-slate-400">
        <span class="flex items-center space-x-1.5 text-[11px]">
          <i class="fa fa-bolt text-amber-400/80"></i>
          <span>Default Fallback</span>
        </span>
        <Handle
          type="source"
          id="default"
          :position="Position.Right"
          class="!w-3 !h-3 !-right-1.5 !bg-slate-400 hover:!bg-slate-200 !border-2 !border-slate-900 transition-transform hover:scale-125"
        />
      </div>

      <!-- Add Branch Action Trigger -->
      <button
        @click="addNewBranch"
        class="nodrag w-full py-1 mt-1 border border-dashed border-cyan-500/40 hover:border-cyan-400 rounded-lg text-cyan-400 text-[11px] font-medium hover:bg-cyan-950/20 transition-all flex items-center justify-center space-x-1"
      >
        <i class="fa fa-plus text-[9px]"></i>
        <span>Add Case</span>
      </button>
    </div>

    <!-- Collapsed Badge Display -->
    <div v-else class="px-3 py-2 text-center text-xs text-slate-400 flex items-center justify-between">
      <span>{{ branches.length }} Cases + Default</span>
      <Handle
        type="source"
        id="default"
        :position="Position.Right"
        class="!w-3 !h-3 !-right-1.5 !bg-cyan-500 !border-2 !border-slate-900"
      />
    </div>

    <!-- Input Handle (Incoming Target) -->
    <Handle
      type="target"
      id="input"
      :position="Position.Left"
      class="!w-3 !h-3 !-left-1.5 !bg-slate-400 hover:!bg-white !border-2 !border-slate-900"
    />
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue';
import { Handle, Position, useVueFlow } from '@vue-flow/core';
import { useStore } from '../../stores';

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, required: true },
  selected: { type: Boolean, default: false }
});

const store = useStore();
const { updateNodeInternals } = useVueFlow();

const isCollapsed = ref(false);
const isSelected = computed(() => props.selected);

const expression = computed(() => props.data?.config?.expression || '');
const branches = computed(() => {
  if (!props.data.config) props.data.config = {};
  if (!props.data.config.branches) props.data.config.branches = [];
  return props.data.config.branches;
});

function scheduleNodeInternalsUpdate() {
  nextTick(() => {
    requestAnimationFrame(() => {
      updateNodeInternals(props.id);
    });
  });
}

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value;
  scheduleNodeInternalsUpdate();
}

function addNewBranch() {
  const branchId = `br_${Date.now().toString(36)}_${Math.random().toString(36).substring(2, 5)}`;
  branches.value.push({
    id: branchId,
    value: `Case ${branches.value.length + 1}`
  });
  scheduleNodeInternalsUpdate();
  store.mark_dirty();
}

function deleteBranch(branchId) {
  const idx = branches.value.findIndex(b => b.id === branchId);
  if (idx !== -1) {
    branches.value.splice(idx, 1);
    // Automatically prune connected edge in graph store
    store.edges = (store.edges || []).filter(
      e => !(e.source === props.id && e.sourceHandle === branchId)
    );
    scheduleNodeInternalsUpdate();
    store.mark_dirty();
  }
}

function onBranchChange() {
  store.mark_dirty();
}
</script>
```

---

### 4.2 Pinia State & Rule Schema Mapping

#### 1. Store Graph Edge Synchronization
When branches are modified or connected on canvas, Pinia maintains consistency:

```javascript
// Inside Pinia Graph Action / Composable
export function syncSwitchNodeEdges(store, nodeId, branches, fallbackTarget) {
  const existingEdges = store.edges.filter(e => e.source === nodeId);
  const retainedEdges = [];

  // Reconcile branch edges
  branches.forEach((branch, index) => {
    const existing = existingEdges.find(e => e.sourceHandle === branch.id);
    if (existing) {
      existing.data = {
        ...existing.data,
        label: branch.value,
        branchIndex: index,
        totalBranches: branches.length,
        isFallback: false
      };
      retainedEdges.push(existing);
    }
  });

  // Reconcile fallback edge
  const existingFallback = existingEdges.find(e => e.sourceHandle === 'default');
  if (existingFallback) {
    existingFallback.data = {
      ...existingFallback.data,
      label: 'Default',
      branchIndex: branches.length,
      totalBranches: branches.length + 1,
      isFallback: true
    };
    retainedEdges.push(existingFallback);
  }

  // Preserve unrelated edges and update store
  store.edges = [
    ...store.edges.filter(e => e.source !== nodeId),
    ...retainedEdges
  ];
}
```

#### 2. Backend Serialization (`serializeRule`)
Converts the visual branch node and edge connections into canonical Frappe rule action dictionaries:

```javascript
// Serialization to Canonical Frappe DocType Rule Schema
export function serializeSwitchAction(node, edges) {
  const config = node.data?.config || {};
  const branches = config.branches || [];
  const casesMap = {};
  let nextStepIfTrue = null;

  // Scan outgoing edges from this Switch node
  const outgoing = edges.filter(e => e.source === node.id);

  outgoing.forEach(edge => {
    if (edge.sourceHandle === 'default') {
      nextStepIfTrue = edge.target;
    } else {
      const matchBranch = branches.find(b => b.id === edge.sourceHandle);
      if (matchBranch && matchBranch.value !== undefined) {
        casesMap[String(matchBranch.value)] = edge.target;
      }
    }
  });

  return {
    action_type: 'Switch',
    name: node.id,
    action_label: node.data?.action_label || 'Switch',
    next_step_if_true: nextStepIfTrue,
    next_step_if_false: null,
    config: {
      expression: config.expression || '',
      cases: casesMap
    }
  };
}
```

---

## 5. Performance & Canvas Optimization Matrix

1. **RAF-Debounced `updateNodeInternals`**:
   - Calling `updateNodeInternals` on every microtask causes layout recalculation loops. Wrapping handle updates in `requestAnimationFrame` ensures DOM layout updates coincide cleanly with browser render frames.
2. **Channel-Offset Corridors**:
   - Instead of complex multi-pass collision detection, deterministic stepped corridors ($14\text{px} \times (\text{index} - \text{median})$) execute in $O(1)$ time per edge.
3. **Graph Boundary Isolation**:
   - Deleting a branch row mutates the store in an isolated batch, eliminating ghost edges and orphaned coordinate lookups without requiring a canvas-wide graph rebuild.

---
