# 🔀 WAR ROOM DEBATE & COMPREHENSIVE ARCHITECTURAL SPECIFICATION: FlexiRule Canvas Switch Action Node & Edge Routing

---

# PHASE 1: THE WAR ROOM DEBATE (Exhaustive Technical Transcript)

**Location**: FlexiRule Core Engineering War Room
**Subject**: Architectural Redesign & Edge Routing Protocol for the VueFlow Switch Action Node
**Participants**:
- **The Lead Engineer**: Core Vue 3 / Composition API & Canvas Architecture Lead.
- **Devil’s Advocate**: Senior Systems Critic (Memory, State Integrity, & Performance Auditor).
- **The Lazy End-User**: Product Experience & Developer Ergonomics Lead.
- **The Canvas & UX Specialist**: Canvas Spatial Interaction & SVG Routing Designer.
- **The Maestro**: Principal Systems Architect.

---

### ROUND 1: Dilemma 1 — Dynamic Handle Re-Indexing vs. Edge Connection Integrity

**The Lead Engineer**: Team, our legacy Switch node on the Vue Flow canvas is fundamentally flawed. Right now, when a Switch action evaluated `doc.status`, it used a rigid `source` handle and attempted to encode branching inside stringified JSON. We are upgrading `SwitchNode.vue` to render dynamic, multi-port source handles on the right edge of the node: one handle per case (`source-case-0`, `source-case-1`, etc.) and one default fallback handle (`source-default`). In Vue 3, we simply map over `node.data.config.cases` in `<template>` using v-for, placing `<Handle type="source" :id="\`source-case-\${index}\`"` />` dynamically.

**Devil’s Advocate**: Hold your enthusiasm. That naive dynamic template mapping is a total landmine. Let's trace what happens when an end-user has 5 cases (`Draft`, `Pending`, `Approved`, `Rejected`, `Cancelled`), each connected to distinct downstream nodes. The user deletes the middle case, `Approved` (at index 2). Your reactive array shrinks from length 5 to 4. Vue re-renders the loop. What used to be index 3 (`Rejected`) now receives handle ID `source-case-2`. What happens to Vue Flow's internal edge registry? The edge that was originally wired to `source-case-2` (which pointed to the `Approved` branch handler) is now instantly connected to the handle at index 2 (`Rejected`). The edge for `source-case-4` becomes completely orphaned because `source-case-4` no longer exists in the DOM! You've just silently corrupted the graph topology and miswired customer business logic without raising a single error.

**The Lazy End-User**: Whoa, wait! As a user, if I delete a case in the UI, I expect two things: either the connected edges pointing out of that specific deleted case get cleanly purged, or I get prompted. I definitely DON'T want the remaining lower branches to secretly adopt the wrong connections! Also, if I drag-to-reorder cases using a handle grip because I want `Approved` evaluated before `Pending`, I don't want the visual edges on the canvas to jump around or cross over like spaghetti!

**The Canvas & UX Specialist**: Precisely. Handles on a spatial node are physical anchor points. If you re-index handles purely based on array array index (`0, 1, 2...`), edge target targets are bound to index positions rather than semantic case identities. We need stable handle IDs based on immutable UUIDs or unique case identifiers (e.g. `handle-case-${case.id}`), NOT ephemeral array indices. But wait—how does the backend rule engine execute cases? The backend `SwitchHandler` expects a dictionary or ordered map of case expressions to target `action_id`s.

**The Lead Engineer**: Exactly! The backend `SwitchHandler.py` evaluates `cases = config.get("cases", {})`, where keys are stringified case values (or condition expressions) and values are target `action_id`s. On the canvas, however, edges in `useGraphStore` explicitly represent the connections (`edge.source = node.id`, `edge.sourceHandle = handleId`, `edge.target = targetActionId`). If handle IDs are immutable UUIDs (e.g., `source-case-uuid-1234`), then moving or reordering a case in `config.cases` array keeps the edge tethered to `source-case-uuid-1234`!

**Devil’s Advocate**: Okay, but what happens when a case is deleted entirely? If handle `source-case-uuid-1234` is unmounted from the DOM, Vue Flow's internal reactivity doesn't automatically purge the orphaned edge from Pinia's `edges` array unless we explicitly handle node handle updates. Furthermore, calling `updateNodeInternals(node.id)` is asynchronous! If you mutate the Pinia store, unmount the handle DOM node, and fail to invoke `updateNodeInternals(node.id)` on the next DOM tick (`nextTick()`), Vue Flow’s SVG edge render engine will still attempt to calculate path vectors from a nonexistent handle DOM node, throwing `TypeError: Cannot read properties of undefined (reading 'x')` during canvas panning or zoom!

**The Maestro**: The consensus for Dilemma 1 is clear. We must establish the **Stable Case ID Protocol**:
1. Every switch case object inside `node.data.config.cases` must carry an immutable `id` (e.g., `case_a1b2c3d4`). Handle IDs on the Vue Flow canvas shall strictly use `source-case-${case.id}`.
2. The default handle shall always be `source-default`.
3. Edge reconnection and deletion must be transactional: When `removeCase(caseId)` is invoked in `useSwitchNode`, the composable must first query Pinia `useGraphStore`, remove all edges where `edge.sourceHandle === 'source-case-' + caseId`, splice the case from `node.data.config.cases`, and immediately invoke `nextTick(() => updateNodeInternals(nodeId))`.
4. When reordering cases, the handle IDs remain attached to their respective case IDs, maintaining zero graph connection corruption while visually re-ordering the port handles vertically.

---

### ROUND 2: Dilemma 2 — SVG Edge Tangling, Multi-Branch Fan-Out & Collision Avoidance

**The Canvas & UX Specialist**: Let's address spatial clutter. A Switch node can easily have 6 to 10 output ports. If all source handles are clustered on the right edge of a standard 200px tall node, the handles overlap visually, and the bezier edge curves fan out into an unreadable mess, crisscrossing each other as they head toward downstream action nodes.

**The Lead Engineer**: We can fix the handle spacing by dynamically calculating the node's height based on the number of active cases. Each case row in `SwitchNode.vue` will have a fixed height (e.g., 44px), and the source handle for that case will be vertically centered relative to its row. As cases are added or removed, the node container grows or shrinks naturally.

**Devil’s Advocate**: Dynamic node resizing creates a massive DOM reflow issue on large canvas graphs! If a node changes height from 180px to 520px as 8 cases are added, it will overlap adjacent nodes sitting directly below it on the canvas. If Vue Flow's node position is static (`node.position = { x, y }`), the growing Switch node will swallow or collide with downstream nodes. Furthermore, standard `SmoothStep` or `Bezier` edge curves starting from handles separated by only 44px vertically will intersect if the target nodes are placed horizontally or diagonally across the canvas. SVG edge paths will overlap directly on top of each other, obscuring case labels!

**The Lazy End-User**: I don't want to manually drag 10 downstream nodes every time I add a case to a Switch statement! The canvas should either auto-layout downstream branches or visually distinguish which edge belongs to which case with inline labels right on the edge line!

**The Canvas & UX Specialist**: We need a dedicated edge component: `CustomSwitchEdge.vue`. Standard VueFlow edges just render an SVG `<path>`. `CustomSwitchEdge.vue` will compute an adjusted orthogonal cubic bezier path with dynamic source offset controls. Additionally, `CustomSwitchEdge.vue` will mount an interactive inline label pill directly at `edge.path.centerX` using `<foreignObject>`. The label pill will display the case evaluation expression (e.g., `== 'Approved'` or `> 10000`), color-coded to match the case handle port!

**The Lead Engineer**: To prevent edge overlap when multiple edges emerge from the same vertical node boundaries, `CustomSwitchEdge.vue` can read custom data properties from `edge.data.caseIndex` and `edge.data.totalCases`. We can adjust the initial control point offset ($dx$) of the Bezier curve dynamically:
$$\text{ControlPoint}_1.x = \text{source.x} + \text{baseOffset} + (\text{caseIndex} \times \text{offsetStep})$$
This forces each outgoing edge to curve out at a slightly different horizontal curvature distance before bending toward its target node, completely eliminating path overlap within the first 100 pixels of the node!

**Devil’s Advocate**: Watch out for reactivity loops! If `CustomSwitchEdge.vue` reaches into Pinia to calculate `caseIndex` on every animation frame, or if `SwitchNode.vue` triggers layout updates that modify node positions, which triggers `updateNodeInternals()`, which triggers edge re-renders, you will create an infinite reactivity loop. Vue Flow stores edges inside reactive arrays. If edge path calculations mutate edge objects or trigger Pinia updates during render, Vue 3 will crash with "Maximum recursive updates exceeded".

**The Maestro**: Resolution for Dilemma 2:
1. **Dynamic Node Height & Layout Contract**: `SwitchNode.vue` will auto-calculate explicit vertical handle offsets using Tailwind row heights ($44\text{px}$ per case slot). Node height changes will trigger an explicit non-recursive `updateNodeInternals(nodeId)` call via Vue Flow composables inside a `watch()` observing `cases.length` with `flush: 'post'`.
2. **Orthogonal Fan-Out Routing**: `CustomSwitchEdge.vue` will implement custom Bezier curvature with calculated horizontal control point offsets based on `sourceHandle` position index, ensuring outgoing curves never collide.
3. **Inline SVG Edge Badges**: `CustomSwitchEdge.vue` will utilize native SVG `<foreignObject>` wrappers with Tailwind CSS badges to display readable condition triggers along the edge path without modifying graph state during render cycles.

---

### ROUND 3: Dilemma 3 — Memory Leaks, Pinia vs. Vue Flow State Synchronization & Reactivity Traps

**Devil’s Advocate**: Now for the worst part: State sync and memory management. Vue Flow maintains its own internal reactive graph state (`useVueFlow()`), while FlexiRule maintains the canonical workflow state in Pinia (`useGraphStore.js`). In `useGraphStore.js`, nodes and edges are stored in `ref([])`.
When a node is updated in the UI (e.g. adding a case in `SwitchNode.vue`), developers often do deep cloning or mutate `node.data.config.cases`.
If Vue Flow wraps DOM elements or node instances in Vue `reactive()` proxies, and Pinia holds raw or deep-cloned references, we get object identity mismatches.
Even worse: when a Switch Node is deleted from the canvas, if custom event listeners (for drag-and-drop reordering, keyboard shortcuts, or input change handlers) attached inside `SwitchNode.vue` are not cleanly destroyed, or if Vue Flow retains handle references in its internal DOM observers, unmounting the node leaves dangling references in memory. After editing a complex rule for 30 minutes, canvas panning becomes laggy due to uncollected detached DOM trees!

**The Lead Engineer**: We can resolve object identity issues by ensuring that `useGraphStore` acts as the single source of truth. When `SwitchNode.vue` modifies cases, it dispatches atomic mutations through a dedicated composable, `useSwitchNode(nodeId)`. `useSwitchNode` operates directly on `useGraphStore().nodes`. We use Vue 3's `toRaw()` when serializing state for Pinia history/undo snapshots, and wrap complex non-reactive Vue Flow internal instances with `markRaw()`.

**The Lazy End-User**: And what about validation? What if I leave a case condition empty or forget to attach an edge to a case output handle? I want instant visual feedback on the node—like a glowing red border around the invalid handle or case input box—so I don't deploy broken rules to production!

**The Canvas & UX Specialist**: We will build a multi-layered validation state directly into `SwitchNode.vue` and `CustomSwitchEdge.vue`:
1. **Case Expression Validation**: If a case has an empty condition or duplicate case key, the specific case row renders a subtle Rose-500 warning badge and tooltip.
2. **Orphan Port Detection**: If a case source handle or default handle is unconnected, the handle port glows with a pulsing Amber-400 indicator ring.
3. **Active Execution Visualizer**: During rule debugging/dry-run execution, the edge that was evaluated as `true` turns into an animated Emerald-500 pulsating path!

**The Maestro**: Excellent. The debate is settled. Let us summarize the final architecture before moving to the complete implementation blueprint:
1. **Architecture**: Immutable Case IDs, Pinia-driven single source of truth with atomic `useSwitchNode` mutations, asynchronous `updateNodeInternals` synchronization.
2. **Routing**: `CustomSwitchEdge` with dynamic horizontal Bezier control-point offsets and SVG `foreignObject` expression badges.
3. **UX & Design**: Ergonomic drag handles, case insertion/deletion, clear fallback pathing, and state-aware Tailwind CSS design tokens.

---

# PHASE 2: THE MAESTRO’S COMPREHENSIVE IMPLEMENTATION SPECIFICATION

```markdown
# 🔀 COMPREHENSIVE ARCHITECTURAL SPECIFICATION: FlexiRule Canvas Switch Action Node & Edge Routing

- **Target Component**: FlexiRule Canvas (`SwitchNode.vue`, `CustomSwitchEdge.vue`, Vue Flow, Vue 3, Pinia)
- **File Path**: `reports/proposal/rule-builder-switch-node-proposal.md`
- **Status**: Production-Ready Engineering Specification

---

## 1. Executive Summary & Design Paradigm

Conditional multi-branching is a foundational control flow construct in decision automation engines. Legacy node architectures suffer from rigid two-port branching (True/False binary trees), leading to visual clutter ("Condition cascades") when modeling multi-state logic (e.g., status codes, risk levels, region routing).

FlexiRule introduces the **Switch Action Node Matrix**, a multi-port, dynamic evaluation node for Vue Flow canvas graphs. This specification defines:
- A dynamic, reactive dynamic handle lifecycle that maintains edge connections during case insertion, deletion, and reordering.
- Non-overlapping SVG edge fan-out routing algorithms with inline expression labeling.
- Strict state isolation between Pinia canvas graph state and Vue Flow canvas instances.
- Zero-leak memory management protocols and reactive DOM updating.

```
+-----------------------------------------------------------------------+
|  🔀 SWITCH: Document Status Evaluation                                |
|  Expression: {{ doc.status }}                                         |
+-----------------------------------------------------------------------+
|  [::] Case 1: "Draft"        -----> (O) source-case-c_1101 --------+  |
|  [::] Case 2: "Pending"      -----> (O) source-case-c_1102 -----+  | |
|  [::] Case 3: "Approved"     -----> (O) source-case-c_1103 ----+ |  | |
|  [*]  Default / Fallback     -----> (O) source-default -------- | |  | |
+----------------------------------------------------------------+ | |  | |
                                                                 | | |  | |
             +---------------------------------------------------+ | |  | |
             | Custom Bezier Fan-Out Paths                         | |  | |
             v                                                     v v  v v
   [ Edge: == "Draft" ]                                    [ Target Nodes ]
```

---

## 2. Deep Node Architecture & Dynamic Handle Lifecycle Management

### 2.1 Anatomy of `SwitchNode.vue`
The Switch Node is composed of four functional zones:
1. **Header Zone**: Action icon, editable node label, status indicator, and quick-action menu (disable, duplicate, delete).
2. **Expression Evaluator Bar**: The Python/Jinja2 expression input field (e.g., `doc.status` or `vars.score`) with context auto-complete integration.
3. **Sortable Case List Zone**: Reorderable list of case branches, each containing:
   - Drag grip handle for reordering.
   - Case value/condition input field.
   - Distinct source handle port (`source-case-${case.id}`).
   - Delete case action button.
4. **Default Fallback Port Zone**: Dedicated fallback path handle (`source-default`) executed when no case matches.

### 2.2 Reactive Handle Re-Indexing & Immutable Case ID Algorithm
To prevent edge connection corruption during case array mutations:
- **Case Object Schema**: Each case in `node.data.config.cases` is represented as an object:
  ```json
  {
    "id": "c_a1b2c3d4",
    "value": "Draft",
    "label": "Draft Status"
  }
  ```
- **Handle ID Isolation**: Source handles render using the immutable case ID (`source-case-c_a1b2c3d4`).
- **Transactional Mutation Pipeline**:
  1. **Add Case**: Appends a new case object with a generated UUID. Inserts the case into `node.data.config.cases`.
  2. **Remove Case**: Queries `useGraphStore.edges`, purges edges matching `sourceHandle === source-case-${caseId}`, splices the case from `config.cases`, and triggers `updateNodeInternals(nodeId)`.
  3. **Reorder Cases**: Reorders the array in `node.data.config.cases`. Handle IDs remain tied to their respective case IDs, so edges do not detach or scramble.

### 2.3 VueFlow Integration & DOM Internals Synchronization
Adding or removing cases dynamically changes the height of `SwitchNode.vue`. Vue Flow requires explicit node dimension updates to recalculate handle coordinates for SVG edge paths.
```ts
// Flushes internal DOM node bounds to Vue Flow instance
watch(
  () => nodeData.value.config.cases.length,
  async () => {
    await nextTick();
    updateNodeInternals(props.id);
  },
  { flush: 'post' }
);
```

---

## 3. VueFlow Edge Layout, Routing & Collision Prevention

### 3.1 Edge Path Strategy & Curve Offsets
To prevent SVG edge path overlap when fanning out multiple outgoing branches from a single vertical node boundary, `CustomSwitchEdge.vue` dynamically calculates control point offsets based on the handle index position.

For a source handle at index $i$ out of $N$ total source handles:
$$x_{\text{offset}} = x_{\text{base}} + (i \times \Delta x)$$
Where $x_{\text{base}} = 40\text{px}$ and $\Delta x = 12\text{px}$.

```
Source Node (Switch)
+-------------------+
| Case 0 (i=0) (O)=======================> [Offset = 40px] ----+
| Case 1 (i=1) (O)===============================> [Offset = 52px] --+
| Case 2 (i=2) (O)=======================================> [Offset = 64px]
+-------------------+
```

### 3.2 Inline Edge Badges (`<foreignObject>`)
Each switch edge renders an interactive condition pill centered on the edge path:
- Renders via native SVG `<foreignObject>`.
- Displays the case value preview (e.g., `== "Draft"` or `Default`).
- Includes a hover tooltip showing full expression evaluations.

---

## 4. Visual Design System & Tailwind CSS Token Specification

### 4.1 Visual State Matrix

| State | Canvas Border | Header Background | Handle Color | Edge Style |
| :--- | :--- | :--- | :--- | :--- |
| **Default** | `border-slate-700` | `bg-slate-800/90` | `bg-cyan-500` | `stroke-slate-500` (2px solid) |
| **Hover** | `border-cyan-500/50` | `bg-slate-800` | `bg-cyan-400` | `stroke-cyan-400` (2px solid) |
| **Selected** | `border-cyan-400 ring-2 ring-cyan-400/20` | `bg-slate-800` | `bg-cyan-400` | `stroke-cyan-400` (2.5px solid) |
| **Active Execution** | `border-emerald-400 ring-2 ring-emerald-400/30` | `bg-emerald-950/40` | `bg-emerald-400` | `stroke-emerald-400` (3px animated dash) |
| **Validation Error** | `border-rose-500 ring-2 ring-rose-500/20` | `bg-rose-950/30` | `bg-rose-500` | `stroke-rose-500` (2px dashed) |

### 4.2 Port & Handle Color Tokens
- **Case Handles**: `bg-cyan-500 border-2 border-slate-900 hover:scale-125`
- **Default Fallback Handle**: `bg-amber-500 border-2 border-slate-900 hover:scale-125`
- **Target Inflow Handle**: `bg-indigo-500 border-2 border-slate-900`

---

## 5. Production-Ready Code Implementation Blueprint

### 5.1 `SwitchNode.vue` (Complete Implementation)

```vue
<template>
	<div
		class="flexirule-switch-node group relative min-w-[280px] rounded-xl border bg-slate-900/95 shadow-xl transition-all duration-200"
		:class="[
			isSelected
				? 'border-cyan-400 ring-2 ring-cyan-400/20 shadow-cyan-500/10'
				: isExecutionActive
				? 'border-emerald-400 ring-2 ring-emerald-400/30 shadow-emerald-500/20'
				: hasValidationError
				? 'border-rose-500 ring-2 ring-rose-500/20'
				: 'border-slate-700/80 hover:border-slate-500',
			isEffectivelyDisabled ? 'opacity-60 grayscale-[0.3]' : '',
		]"
	>
		<!-- Input Target Handle -->
		<Handle
			id="target"
			type="target"
			:position="Position.Left"
			class="!h-3.5 !w-3.5 !-left-2 !bg-indigo-500 !border-2 !border-slate-900 transition-transform hover:scale-125"
		/>

		<!-- Node Header -->
		<div
			class="flex items-center justify-between border-b border-slate-800 px-3.5 py-2.5 rounded-t-xl bg-slate-800/50"
		>
			<div class="flex items-center gap-2 overflow-hidden">
				<div
					class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
				>
					<i class="fa fa-random text-xs"></i>
				</div>
				<div class="flex flex-col truncate">
					<span class="text-xs font-semibold text-slate-200 truncate">
						{{ nodeData.action_label || 'Switch' }}
					</span>
					<span class="text-[10px] font-medium text-slate-400 uppercase tracking-wider">
						Control Flow
					</span>
				</div>
			</div>

			<!-- Status & Actions -->
			<div class="flex items-center gap-1.5 shrink-0">
				<NodeStatusIndicator :is-enabled="nodeData.is_enabled" :node-id="id" />
				<button
					type="button"
					class="h-6 w-6 rounded flex items-center justify-center text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 transition-colors"
					@click.stop="toggleMenu"
				>
					<i class="fa fa-ellipsis-v text-xs"></i>
				</button>
			</div>
		</div>

		<!-- Expression Evaluator Bar -->
		<div class="p-3 border-b border-slate-800/80 bg-slate-950/40">
			<label class="block text-[10px] font-medium text-slate-400 mb-1 uppercase tracking-wider">
				Switch Expression
			</label>
			<div class="relative">
				<input
					v-model="expressionValue"
					type="text"
					placeholder="e.g. doc.status or vars.score"
					class="w-full rounded-md border border-slate-700/80 bg-slate-900 px-2.5 py-1.5 text-xs text-slate-200 placeholder-slate-500 font-mono focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
					@change="handleExpressionChange"
				/>
				<span
					v-if="!expressionValue"
					class="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-rose-500 animate-pulse"
					title="Expression required"
				></span>
			</div>
		</div>

		<!-- Case Outlets Container -->
		<div class="p-2 space-y-2">
			<div class="flex items-center justify-between px-1.5 text-[10px] font-medium text-slate-400 uppercase">
				<span>Cases ({{ casesList.length }})</span>
				<button
					type="button"
					class="text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1 transition-colors"
					@click="handleAddCase"
				>
					<i class="fa fa-plus text-[9px]"></i> Add Case
				</button>
			</div>

			<!-- Cases List -->
			<div class="space-y-1.5">
				<div
					v-for="(caseItem, index) in casesList"
					:key="caseItem.id"
					class="group/case relative flex items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-800/40 p-2 hover:border-slate-700 transition-colors"
				>
					<!-- Drag Handle -->
					<span class="cursor-grab text-slate-600 hover:text-slate-400 active:cursor-grabbing text-xs px-0.5">
						<i class="fa fa-bars"></i>
					</span>

					<!-- Case Key/Value Input -->
					<div class="flex-1 min-w-0">
						<input
							v-model="caseItem.value"
							type="text"
							placeholder="Case match value..."
							class="w-full rounded bg-slate-900/90 border border-slate-700/60 px-2 py-1 text-xs font-mono text-cyan-300 placeholder-slate-600 focus:border-cyan-500 focus:outline-none"
							@change="handleCaseMutated"
						/>
					</div>

					<!-- Delete Case Button -->
					<button
						type="button"
						class="text-slate-500 hover:text-rose-400 p-1 transition-colors opacity-0 group-hover/case:opacity-100"
						title="Remove Case"
						@click="handleRemoveCase(caseItem.id)"
					>
						<i class="fa fa-trash text-xs"></i>
					</button>

					<!-- Dynamic Source Handle for Case -->
					<Handle
						:id="`source-case-${caseItem.id}`"
						type="source"
						:position="Position.Right"
						class="!h-3 !w-3 !-right-1.5 !bg-cyan-500 !border-2 !border-slate-900 transition-transform hover:scale-125"
						:style="{ top: `${calculateCaseHandleTop(index)}px` }"
					/>
				</div>
			</div>

			<!-- Default / Fallback Branch -->
			<div class="relative flex items-center justify-between rounded-lg border border-amber-500/20 bg-amber-500/5 p-2 mt-3">
				<div class="flex items-center gap-2">
					<i class="fa fa-level-down-alt text-amber-400 text-xs rotate-90"></i>
					<span class="text-xs font-medium text-amber-200">Default / Fallback</span>
				</div>
				<span class="text-[10px] text-amber-400/70 font-mono">Otherwise</span>

				<!-- Default Source Handle -->
				<Handle
					id="source-default"
					type="source"
					:position="Position.Right"
					class="!h-3 !w-3 !-right-1.5 !bg-amber-500 !border-2 !border-slate-900 transition-transform hover:scale-125"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, watch } from 'vue';
import { Handle, Position, useVueFlow } from '@vueflow/core';
import { useGraphStore } from '../stores/useGraphStore.js';
import { useSwitchNode } from '../composables/useSwitchNode.ts';
import NodeStatusIndicator from './NodeStatusIndicator.vue';

const props = defineProps({
	id: { type: String, required: true },
	data: { type: Object, required: true },
	selected: { type: Boolean, default: false }
});

const graphStore = useGraphStore();
const { updateNodeInternals } = useVueFlow();
const {
	nodeData,
	expressionValue,
	casesList,
	addCase,
	removeCase,
	updateExpression,
	validateNode
} = useSwitchNode(props.id);

const isSelected = computed(() => props.selected);
const isEffectivelyDisabled = computed(() =>
	graphStore.effectiveDisabledIds.has(props.id)
);
const isExecutionActive = computed(() => props.data?.is_executing || false);
const hasValidationError = computed(() => !validateNode().isValid);

// Vertical offset computation for handle alignment
function calculateCaseHandleTop(index) {
	// Offset header + expression bar + case padding
	const BASE_OFFSET = 124;
	const ROW_HEIGHT = 42;
	return BASE_OFFSET + index * ROW_HEIGHT;
}

function handleExpressionChange() {
	updateExpression(expressionValue.value);
}

function handleAddCase() {
	addCase();
}

function handleRemoveCase(caseId) {
	removeCase(caseId);
}

function handleCaseMutated() {
	graphStore.touch_node(props.id);
}

function toggleMenu() {
	// Trigger node context menu
}

// Ensure Vue Flow updates edge targets on handle DOM modifications
watch(
	() => casesList.value.length,
	async () => {
		await nextTick();
		updateNodeInternals(props.id);
	},
	{ flush: 'post' }
);
</script>
```

---

### 5.2 `useSwitchNode.ts` (Composable Specification)

```ts
import { computed } from 'vue';
import { useGraphStore } from '../stores/useGraphStore.js';
import { generateShortId } from '../utils/schema_utils.js';

export interface SwitchCase {
	id: string;
	value: string;
	label?: string;
}

export interface SwitchConfig {
	expression: string;
	cases: SwitchCase[];
}

export interface ValidationResult {
	isValid: boolean;
	errors: string[];
}

export function useSwitchNode(nodeId: string) {
	const graphStore = useGraphStore();

	const node = computed(() =>
		graphStore.nodes.find((n) => n.id === nodeId)
	);

	const nodeData = computed(() => node.value?.data || {});

	// Ensure config structure integrity
	const config = computed<SwitchConfig>(() => {
		const rawConfig = nodeData.value.config || {};
		const expression = rawConfig.expression || '';
		let cases: SwitchCase[] = [];

		if (Array.isArray(rawConfig.cases)) {
			cases = rawConfig.cases;
		} else if (rawConfig.cases && typeof rawConfig.cases === 'object') {
			// Migrate legacy dictionary shape {"Draft": "act_1"} to structured array
			cases = Object.entries(rawConfig.cases).map(([val]) => ({
				id: `c_${generateShortId()}`,
				value: val,
				label: val
			}));
		}

		return { expression, cases };
	});

	const expressionValue = computed({
		get: () => config.value.expression,
		set: (val: string) => updateExpression(val)
	});

	const casesList = computed(() => config.value.cases);

	function updateExpression(expr: string) {
		if (!node.value) return;
		node.value.data.config = {
			...node.value.data.config,
			expression: expr
		};
		graphStore.touch_node(nodeId);
	}

	function addCase(initialValue: string = '') {
		if (!node.value) return;
		const newCase: SwitchCase = {
			id: `c_${generateShortId()}`,
			value: initialValue || `Case ${casesList.value.length + 1}`
		};

		const updatedCases = [...casesList.value, newCase];
		node.value.data.config = {
			...node.value.data.config,
			cases: updatedCases
		};
		graphStore.touch_node(nodeId);
	}

	function removeCase(caseId: string) {
		if (!node.value) return;

		// 1. Transactionally remove connected graph edges for this specific handle
		const targetHandleId = `source-case-${caseId}`;
		graphStore.edges = graphStore.edges.filter(
			(edge) => !(edge.source === nodeId && edge.sourceHandle === targetHandleId)
		);

		// 2. Remove case object
		const updatedCases = casesList.value.filter((c) => c.id !== caseId);
		node.value.data.config = {
			...node.value.data.config,
			cases: updatedCases
		};

		graphStore.touch_node(nodeId);
	}

	function reorderCases(newCases: SwitchCase[]) {
		if (!node.value) return;
		node.value.data.config = {
			...node.value.data.config,
			cases: newCases
		};
		graphStore.touch_node(nodeId);
	}

	function validateNode(): ValidationResult {
		const errors: string[] = [];

		if (!config.value.expression.trim()) {
			errors.push('Switch expression is missing.');
		}

		if (casesList.value.length === 0) {
			errors.push('At least one case path must be configured.');
		}

		const values = casesList.value.map((c) => c.value.trim());
		const hasDuplicates = new Set(values).size !== values.length;
		if (hasDuplicates) {
			errors.push('Duplicate case match values detected.');
		}

		return {
			isValid: errors.length === 0,
			errors
		};
	}

	return {
		nodeData,
		config,
		expressionValue,
		casesList,
		addCase,
		removeCase,
		reorderCases,
		updateExpression,
		validateNode
	};
}
```

---

### 5.3 `CustomSwitchEdge.vue` (Complete Implementation)

```vue
<template>
	<g class="flexirule-switch-edge group">
		<!-- Main Edge SVG Path -->
		<path
			:id="id"
			:d="edgePath"
			class="vue-flow__edge-path transition-all duration-200 fill-none"
			:class="[
				selected ? '!stroke-cyan-400 !stroke-[2.5px]' : '',
				data?.isExecuting ? '!stroke-emerald-400 !stroke-[3px] animate-pulse' : '',
				data?.isDefault ? 'stroke-amber-500/80' : 'stroke-slate-500 hover:stroke-slate-300'
			]"
			:style="style"
			:marker-end="markerEnd"
		/>

		<!-- Invisible Interaction Hit-Zone -->
		<path
			:d="edgePath"
			class="fill-none stroke-transparent stroke-[16px] cursor-pointer"
			@click="onEdgeClick"
		/>

		<!-- ForeignObject Inline Condition Badge -->
		<foreignObject
			:x="labelX - 45"
			:y="labelY - 12"
			width="90"
			height="24"
			class="overflow-visible pointer-events-auto"
		>
			<div
				class="flex items-center justify-center h-6 px-2 rounded-full border shadow-md backdrop-blur-md text-[10px] font-mono font-medium transition-transform hover:scale-105 select-none"
				:class="[
					data?.isDefault
						? 'border-amber-500/40 bg-amber-950/80 text-amber-300'
						: 'border-slate-700 bg-slate-900/90 text-cyan-300'
				]"
			>
				<span class="truncate max-w-[75px]">
					{{ edgeBadgeText }}
				</span>
			</div>
		</foreignObject>
	</g>
</template>

<script setup>
import { computed } from 'vue';
import { getBezierPath } from '@vueflow/core';

const props = defineProps({
	id: { type: String, required: true },
	sourceX: { type: Number, required: true },
	sourceY: { type: Number, required: true },
	targetX: { type: Number, required: true },
	targetY: { type: Number, required: true },
	sourcePosition: { type: String, required: true },
	targetPosition: { type: String, required: true },
	data: { type: Object, default: () => ({}) },
	selected: { type: Boolean, default: false },
	style: { type: Object, default: () => ({}) },
	markerEnd: { type: String, default: '' }
});

const emit = defineEmits(['edge-click']);

// Dynamic Orthogonal Fan-Out Control Offset Computation
const edgePathData = computed(() => {
	const caseIndex = props.data?.caseIndex || 0;
	const BASE_CURVE_OFFSET = 40;
	const OFFSET_STEP = 12;

	// Calculate horizontal curvature offset based on source handle position
	const curvatureOffset = BASE_CURVE_OFFSET + caseIndex * OFFSET_STEP;

	const [path, labelX, labelY] = getBezierPath({
		sourceX: props.sourceX,
		sourceY: props.sourceY,
		sourcePosition: props.sourcePosition,
		targetX: props.targetX,
		targetY: props.targetY,
		targetPosition: props.targetPosition,
		curvature: curvatureOffset / 100
	});

	return { path, labelX, labelY };
});

const edgePath = computed(() => edgePathData.value.path);
const labelX = computed(() => edgePathData.value.labelX);
const labelY = computed(() => edgePathData.value.labelY);

const edgeBadgeText = computed(() => {
	if (props.data?.isDefault) return 'Otherwise';
	return props.data?.conditionExpression
		? `== ${props.data.conditionExpression}`
		: 'Case';
});

function onEdgeClick(event) {
	emit('edge-click', { id: props.id, event });
}
</script>
```

---

## 6. Graph Compilation & Engine Execution Synchronization

The frontend canvas graph must serialize cleanly into the backend `SwitchHandler` contract (`flexirule/ruleflow/core/action_handlers/switch.py`).

### 6.1 Action Record Serialization Standard
During graph compilation before rule saving, `useGraphStore.clean_graph_data()` transforms the Switch node and its dynamic edges into the JSON payload expected by the backend engine:

```json
{
  "action_id": "act_switch_1",
  "action_type": "Switch",
  "action_label": "Route by Document Status",
  "config": {
    "expression": "doc.status",
    "cases": {
      "Draft": "act_process_draft",
      "Pending": "act_notify_manager",
      "Approved": "act_execute_payment"
    }
  },
  "next_step_if_true": "act_log_fallback",
  "next_step_if_false": null
}
```

- **Case Map Resolution**: `config.cases` is compiled by pairing each case item's `value` with the target `action_id` of the edge originating from `source-case-${case.id}`.
- **Default Branch Resolution**: `next_step_if_true` receives the target `action_id` connected to `source-default`.

---

## 7. Quality Assurance & Verification Criteria

1. **Handle ID Stability Test**:
   - Create 4 cases (`A`, `B`, `C`, `D`) and connect edges to distinct target nodes.
   - Delete case `B`.
   - Verify that case `C` and `D` retain their original edge targets without cross-wiring or handle mutation errors.
2. **Dynamic Height & Re-alignment Test**:
   - Rapidly add 10 cases to a Switch node.
   - Verify that `updateNodeInternals` flushes handle positions asynchronously and edge lines stay anchored to their handle centers.
3. **Engine Dry-Run Test**:
   - Execute a test document with `doc.status = "Pending"`.
   - Confirm backend `SwitchHandler` evaluates `doc.status`, matches `"Pending"`, and routes execution to `act_notify_manager`.
```
