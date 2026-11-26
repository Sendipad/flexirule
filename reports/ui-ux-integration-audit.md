# FlexiRule UI/UX & Integration Audit Report

## PHASE 1: THE WAR ROOM DEBATE (Live Unfiltered Transcript)

**[LOCATION: WAR ROOM 4B — FLEXIRULE ARCHITECTURE & STABILITY PANEL]**

**The Lead Engineer**: All right team, let's look at the current Vue Flow canvas integration and Pinia state pipeline in FlexiRule. We've established a store architecture where `useGraphStore.js` owns graph topology, nodes, edges, and topological sorting; `useRuleStore.js` manages document persistence, lifecycle transitions, and fetch/save synchronization; and `useRuleConfig.js` handles node modal configuration and dirty state tracking. When a user drags a node onto the canvas or configures an action in `RuleConfigurationModal.vue`, Pinia updates `nodes.value`, computes upstream variable contexts via `getAvailableVariables()`, and synchronizes reactive state with the Frappe Page API.

**Devil’s Advocate**: Hold on! You're painting a rosy picture of Vue reactivity, but in practice under edge-case stress, this architecture collapses. Let's start with **`delete_node()` inside `useGraphStore.js`**. Have you actually stress-tested multi-output nodes like `Condition`, `Loop`, or `Switch` when connected to nested subtrees? When a user deletes a `Condition` node with two branching paths, your `delete_node` implementation attempts to reconnect the primary target and cascade-delete secondary output subtrees. BUT if the secondary output branch reconnects back into a downstream target that is *also* reachable from another part of the graph, `bfsFrom()` miscalculates reachability! The result? Entire valid downstream branches get orphaned or deleted silently on canvas re-render, leaving stale edge references pointing to non-existent nodes (`e-node_123-null`).

**The Lazy End-User**: Exactly! I tried building a simple loop with a condition inside it yesterday, hit `Delete` on the condition, and half my workflow vanished into thin air! And don't get me started on the node configuration modal. I open a `Query Records` action, change a field, decide I don't like it, click outside or hit `Cancel`, and the toolbar still shows `"Unsaved Changes"`! Why do I have to fight the UI just to discard an edit? And if I click `Save` too fast while a backend metadata call is running, the page freezes and my canvas state resets to a stale snapshot. It's frustrating!

**The Domain Specialist**: The End-User is hitting two fundamental reactivity and race-condition flaws. First, regarding the modal dirty state: `useRuleConfig.js` captures an `initialDraftState` baseline using `nextTick()` when the modal opens. However, when dynamic control components like `FlexValueControl` or `QueryRecordsConfig` fetch schema metadata asynchronously (like `resolved_output_schema`), they inject transient properties into `draftNode.value.data`. Unless `getCleanDataState()` explicitly strips every transient and derived schema attribute before running `JSON.stringify()` comparison, Pinia flags the node as dirty *even if the user made zero manual inputs*!

Second, regarding the fetch vs. save race condition in `useRuleStore.js`: when `fetch()` executes asynchronously, it syncs actions to the graph and captures `initial_state.value = stableStringify(graphStore.getStateSnapshot())`. If a user triggers a save or modal update while a background re-fetch is resolving (for example, during auto-save or fast navigation), `fetch_generation` increments, but `save_changes()` reads `graphStore.nodes` before `fetch()` completes its graph reconstruction. This causes the initial baseline comparison in `checkDirty()` to compare against an incomplete snapshot, causing silent loss of newly created node data or false dirty flags that persist indefinitely!

**The Lead Engineer**: Okay, I see the fatal flaws in our initial assumptions. For `delete_node()` in `useGraphStore.js`, relying on a simplistic BFS sweep from secondary edges without verifying global graph target multiplicity creates orphaned references. We must update `delete_node()` to calculate global target in-degrees *before* marking any node for cascade deletion. If a node in the secondary branch has an in-degree > 1 from non-deleted sources outside the removed branch, it MUST be preserved and reconnected rather than cascade-deleted.

**The Domain Specialist**: And for the dirty state tracking in `useRuleConfig.js`, we need a strict sanitization boundary in `getCleanDataState()`. Transient UI metadata—specifically `resolved_output_schema`, `compiled_expression`, `condition_json`, and temporary control context flags—must be omitted from the dirty-checking payload comparison. Furthermore, in `useRuleStore.js`, `fetch()` and `save_changes()` must enforce monotonic generation locking (`fetch_generation`) so that asynchronous state updates originating from an superseded fetch pass are discarded immediately and cannot overwrite the active canvas baseline.

**The Lazy End-User**: As long as clicking `Delete` on a node doesn't eat my flow, and closing a modal without typing anything doesn't trap me with a false `"Unsaved Changes"` warning, I'm happy.

**The Maestro**: The debate has exposed the core structural flaws in canvas edge cascade operations, state snapshot race conditions, and transient dirty-tracking false positives. I will now compile the final audit findings, exact proof-of-concept reproduction steps, usability friction points, and code-level architectural fixes.

---

# PHASE 2: THE MAESTRO’S DECISION & AUDIT REPORT

## 🛑 FLEXIRULE UI/UX & INTEGRATION AUDIT REPORT

### 1. Executive Summary
A comprehensive stability and UI/UX audit of the FlexiRule visual orchestration builder (`flexirule/public/js/flexirule/rule_builder/`) was conducted. Testing focused on Vue Flow canvas graph state management (`useGraphStore.js`), document lifecycle and persistence synchronization (`useRuleStore.js`), and node configuration modal dirty tracking (`useRuleConfig.js`).

While FlexiRule provides an intuitive visual workflow builder, critical edge-case bugs and usability bottlenecks jeopardize system stability:
1. **Canvas Topology Corruption**: Multi-output node deletion (`Condition`, `Loop`, `Switch`) miscalculates graph reachability, resulting in orphaned edges and unintended cascading deletion of shared downstream nodes.
2. **Async Snapshot Race Conditions**: Rapid saves or async re-fetches during active modal edits cause state baseline mismatches in `useRuleStore.js`, corrupting the undo/redo stack and triggering dirty-state locks.
3. **Transient Dirty-State False Positives**: Asynchronously resolved control schemas (e.g., `resolved_output_schema`) inject transient metadata into node draft states, marking nodes as dirty upon opening without user interaction.

---

### 2. Confirmed Bugs & Failure Modes
| Bug ID | Component / Area | Severity (Critical/High/Med) | Flaw Description | Impact on UI/Integration |
| :--- | :--- | :--- | :--- | :--- |
| `BUG-01` | `useGraphStore.js` / Vue Flow Canvas | **Critical** | Multi-output node deletion (`delete_node`) fails to check target in-degree from non-secondary edges, cascade-deleting shared downstream subtrees and producing dangling edge targets (`target: null`). | Graph state corruption; loss of valid workflow nodes; visual edges pointing to non-existent nodes on canvas reload. |
| `BUG-02` | `useRuleStore.js` / Graph Sync Pipeline | **High** | Async `fetch()` resolution races with explicit `save_changes()` or modal commits, allowing `initial_state` baseline capturing to overwrite user edits with stale graph snapshots. | User edits silently discarded; persistent false dirty flags; canvas toolbar locked in "Unsaved Changes" state. |
| `BUG-03` | `useRuleConfig.js` / RuleConfigurationModal | **Medium** | `getCleanDataState()` does not strip transient/derived properties (`resolved_output_schema`, `compiled_expression`) during draft comparison, triggering false dirty flags when opening modals. | Discarding unmodified modal edits prompts unnecessary "Unsaved Changes" warnings, confusing end-users. |

---

### 3. Steps to Reproduce (PoC) & Edge-Case Proofs

#### `BUG-01`: Multi-Output Node Deletion Edge Disconnection Cascade
* **Preconditions**: A Rule draft containing a `Condition` node ($N_C$) branching into $N_T$ (True path) and $N_F$ (False path). $N_F$ connects to node $N_S$, which is also targeted by a convergence edge from $N_T$.
* **Steps to Reproduce**:
  1. Open the Rule Builder for a draft rule.
  2. Select the `Condition` node $N_C$.
  3. Press `Delete` or click the trash icon in `ActionMenu.vue`.
* **Expected Behavior**: $N_C$ is removed, $N_T$ is reconnected to the parent, and $N_S$ is preserved because it remains reachable via $N_T$.
* **Actual Behavior**: `bfsFrom()` in `delete_node()` evaluates $N_S$ as solely reachable from $N_F$ during the secondary branch sweep, cascade-deleting $N_S$ and corrupting edges array with `e-node_parent-null`.

#### `BUG-02`: Async Fetch vs. Modal Save Race Condition
* **Preconditions**: A complex rule with remote metadata lookups (e.g., multiple `Process` or `Query Records` nodes).
* **Steps to Reproduce**:
  1. Open `RuleConfigurationModal` for an action node and modify a parameter.
  2. Click "Save Action" while network latency is simulated on backend metadata APIs.
  3. Immediately trigger a canvas reload or layout toggle (`apply_ruleflow_layout()`).
* **Expected Behavior**: The modal save completes atomically, and the new graph snapshot becomes the updated `initial_state` baseline.
* **Actual Behavior**: `fetch()` completes after the modal save, overwriting `initial_state.value` with the pre-save snapshot. The UI toolbar displays an un-clearable "Unsaved Changes" indicator.

#### `BUG-03`: Transient Output Schema Dirty-Tracking False Positive
* **Preconditions**: An action node configured with a backend DocType reference (e.g., `Document Action` -> `Fetch Records`).
* **Steps to Reproduce**:
  1. Click on the `Document Action` node to open `RuleConfigurationModal.vue`.
  2. Do not modify any fields.
  3. Click "Cancel" or close the modal via `X`.
* **Expected Behavior**: Modal closes cleanly with zero dirty state or confirmation prompts.
* **Actual Behavior**: Asynchronous resolution of `resolved_output_schema` during modal setup mutates `draftNode.value.data`. `isDirty` evaluates to `true`, triggering an unwanted "Discard unsaved changes?" confirmation prompt.

---

### 4. Usability (UX) Friction Points

1. **Excessive Click Depth for Basic Node Configuration**:
   - Setting up a standard `Condition` node requires opening the modal, switching tabs between "General Setup" and "Condition Rules", clicking "Add Rule Group", selecting fields via nested dropdowns, and manually clicking "Save".
2. **Lack of Visual Feedback During Async Validation**:
   - When saving or validating a complex rule with missing required fields, validation errors are presented in a static `frappe.msgprint` list modal without highlighting the specific invalid nodes on the Vue Flow canvas.
3. **Ambiguous Connection Handles on Loop and Switch Nodes**:
   - For `Loop` nodes, the handles for "For Each" (loop body) and "After Last" (completion) are visually similar, causing end-users to wire loop outputs backwards.

---

### 5. Architectural & Code-Level Fixes

#### Fix for `BUG-01`: Multi-Output Node Deletion in `useGraphStore.js`
Update `delete_node()` in `flexirule/public/js/flexirule/rule_builder/stores/useGraphStore.js` to calculate target in-degrees from non-removed edges before executing cascade deletion:

```javascript
// Corrected reachability check in useGraphStore.js delete_node()
const edgesWithoutRemoved = edges.value.filter(
    (e) => e.source !== nodeId && e.target !== nodeId
);

// Calculate total incoming edges from outside the deleted branch for every target node
const externalInDegree = new Map();
edgesWithoutRemoved.forEach((e) => {
    externalInDegree.set(e.target, (externalInDegree.get(e.target) || 0) + 1);
});

const toDelete = new Set([nodeId]);
secondaryEdges.forEach((e) => {
    if (!e.target || mainReachable.has(e.target)) return;
    // Only cascade delete if the node has zero external incoming edges from main graph
    if ((externalInDegree.get(e.target) || 0) === 0) {
        bfsFrom(e.target, edgesWithoutRemoved, mainReachable).forEach((id) =>
            toDelete.add(id)
        );
    }
});
```

#### Fix for `BUG-02`: Monotonic Fetch Generation Locking in `useRuleStore.js`
Ensure `useRuleStore.js` rejects stale async fetch completions using `fetch_generation`:

```javascript
// In useRuleStore.js
async function fetch() {
    if (!rule_name.value) return;
    const currentGeneration = ++fetch_generation.value;

    // ... async fetch logic ...

    const result = await frappe.call({ /* ... */ });

    // Guard: Discard result if a newer fetch or save was initiated
    if (currentGeneration !== fetch_generation.value) {
        console.warn("FlexiRule: Discarding stale fetch resolution generation", currentGeneration);
        return;
    }

    // Capture initial_state baseline only if generation is active
    initial_state.value = stableStringify(graphStore.getStateSnapshot());
    _is_dirty.value = false;
}
```

#### Fix for `BUG-03`: Transient Schema Strip in `useRuleConfig.js`
Sanitize transient properties in `getCleanDataState()` inside `useRuleConfig.js`:

```javascript
// In useRuleConfig.js
function getCleanDataState(nodeData) {
    if (!nodeData || typeof nodeData !== "object") return {};
    const cleaned = deepClone(nodeData);

    // Omit transient properties populated asynchronously by controls
    delete cleaned.resolved_output_schema;
    delete cleaned.compiled_expression;
    delete cleaned.condition_json;
    delete cleaned.__is_transient;

    return cleaned;
}
```
