# Frontend Audit — FlexiRule

## 1. Overview & Audit Scope

The frontend audit evaluated the Vue 3 application located under `flexirule/public/js/flexirule/`:
- **Stores**: `useRuleStore.js`, `useGraphStore.js`, `useUIStore.js`, `useMetaStore.js`, `useHistoryStore.js`.
- **Canvas & Nodes**: `App.vue`, `Sidebar.vue`, `CommandPalette.vue`, custom VueFlow node components (`StartNodeProperties.vue`, `ActionZone.vue`, `AddNodeEdge.vue`).
- **Configuration Controls**: `ValueResolverControl.vue`, `TextGeneratorControl.vue`, `ResourceMapperControl.vue`, `ComboBoxControl.vue`, `DataControl.vue`.
- **Composables & Utilities**: `useRuleGraph.js`, `useCanvasLayout.js`, `useNodeStatus.js`, `serialization.js`, `condition_payload.js`.

---

## 2. Detailed Findings

### Finding FR-FE-001 (MEDIUM) — Canvas Auto-Layout Pollutes Draft "Is Dirty" Tracking
- **Files**: `flexirule/public/js/flexirule/rule_builder/stores/useRuleStore.js`, `flexirule/public/js/flexirule/rule_builder/composables/useCanvasLayout.js`
- **Description**: Canvas auto-layout execution causes false dirty state flags on document load.
- **Technical Analysis**: When opening a Rule in the Rule Builder, `useRuleStore.fetch()` builds the VueFlow graph and immediately captures `initial_state = JSON.stringify(graphStore.getStateSnapshot())`. However, VueFlow node rendering and Dagre layout calculation (`layoutGraph()`) adjust node `(x, y)` position coordinates asynchronously across animation frames. Because `checkDirty()` compares the live graph snapshot against `initial_state`, the position changes cause `is_dirty` to become `true`.
- **Impact**: Users are falsely warned about "Unsaved Changes" when closing or navigating away from a Rule without having edited any configuration.
- **Remediation**: Call `sync_initial_state_positions()` or `clear_dirty()` inside `nextTick()` after layout calculations settle.

---

### Finding FR-FE-002 (MEDIUM) — Double Stringification of `condition_json` on Rule Save
- **File**: `flexirule/public/js/flexirule/rule_builder/stores/useRuleStore.js`
- **Function/Class**: `save_changes`
- **Description**: Condition payloads stored in Code controls can be double-stringified during serialization.
- **Technical Analysis**: In `useRuleStore.js:save_changes()`, `condition_json` is serialized using:
  ```javascript
  condition_json: action_type === "Condition" ? serializeField(finalConfig) : null
  ```
  If `finalConfig` is already a JSON string (for instance, when configured directly in a raw JSON editor), `serializeField()` applies `JSON.stringify()` again, producing escaped JSON strings like `"\"{\\\"conditions\\\":...}\""`. Upon saving, backend compilation in `compiler.py` throws a JSON parsing error.
- **Impact**: Rules with condition actions edited via raw code editors fail to compile and save.
- **Remediation**: Normalize `finalConfig` using `getConditionPayload()` before calling `serializeField()`.

---

### Finding FR-FE-003 (LOW) — Duplicate Action ID Collision on Node Duplication
- **File**: `flexirule/public/js/flexirule/rule_builder/stores/useGraphStore.js`
- **Function/Class**: `duplicateNode`
- **Description**: Duplicating a node reuses the existing `action_id`.
- **Technical Analysis**: When a user duplicates a node on the canvas, `duplicateNode()` generates a new VueFlow node ID (e.g., `node_999`), but deep-clones the node `data` object including `data.action_id`. As a result, two distinct canvas nodes share the same `action_id` (e.g. `act_01`). During topological sorting and backend serialization in `save_changes()`, both nodes map to the same `action_id`, corrupting target references for `next_step_if_true`.
- **Impact**: Corrupted graph execution flow when duplicating configured actions.
- **Remediation**: Re-generate a unique `action_id` (e.g. `act_` + timestamp) inside `duplicateNode()`.

---

### Finding FR-FE-004 (INFO) — Missing Type Annotations in Composable Contracts
- **File**: `flexirule/public/js/flexirule/rule_builder/composables/useRuleConfig.js`
- **Description**: Action config composables rely on plain JavaScript dictionaries without type enforcement or JSDoc contract declarations.
- **Impact**: Maintainability concern during frontend component additions.
- **Remediation**: Add JSDoc `@typedef` definitions matching backend `ContractDTO` fields.
