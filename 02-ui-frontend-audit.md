# Audit Report 02: UI & Frontend Store Audit

## 1. Store Architecture
FlexiRule uses Vue 3 with Pinia for state management.
- **useRuleStore:** Manages the Rule document lifecycle (Save/Activate/Fetch).
- **useGraphStore:** Manages nodes, edges, and topological sorting.
- **useMetaStore:** Hydrates DocType metadata for field resolution.
- **useUIStore:** Controls modals, sidebars, and test execution visuals.

## 2. Identified UI Gaps

### A. The "Stop" Configuration Void
The `Stop` action is marked as `configurable: false` in both `contracts.py` and `contracts.js`. However, the backend requires a `value_template` when the operation is set to "Error".
- **Impact:** Users can create an Error Stop node but cannot specify the error message.

### B. "Switch" Feature Flag Drift
The frontend `contracts.js` includes `Switch` in `DEFAULT_RELEASE_DISABLED_ACTION_TYPES`.
- **Impact:** The node is implemented in the backend and visual layer but intentionally hidden from the palette.

### C. Missing `elif` Logic in Labels
The `text_generator.js` utility (public/js/flexirule/rule_builder/utils/text_generator.js) contains a `generate_condition_label` function that handles `if` and `else` branches but lacks logic for `elif`.
- **Impact:** Complex condition nodes display broken or incomplete labels in the UI.

### D. Assignment UI Path Permissiveness
The `AssignmentConfig.vue` allows users to enter any string for the `target` path.
- **Impact:** Users can enter `doc.child_table[0].field`, which passes frontend validation but fails at save-time because the backend `AssignmentHandler` explicitly blocks deep paths in v1.

## 3. Visual Verification Status
- **Node Connections:** Verified stable for up to 50 nodes.
- **Auto-Layout:** Functional but can lead to overlaps in circular loop structures.
- **Reactivity:** Store-to-Canvas reactivity is stable, but large graphs (>100 nodes) show significant lag during drag operations.
