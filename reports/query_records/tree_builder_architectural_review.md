# Architectural Review: TreeBuilder & Query Filter Synchronization

**Branch**: `refactor/reusable-tree-builder-final-v2`
**Base Branch**: `refactor/query-records`
**Target Scope**: `TreeBuilder.vue`, `TreeBuilderNode.vue`, `QueryFilterTree.vue`, `FilterLeaf.vue`, `filter_tree_adapter.js`, `FetchRecordsConfig.vue`, `useRuleConfig.js`, `frappe_query_compat.py`

---

## Executive Summary

This architectural review evaluates the recent refactoring on `refactor/reusable-tree-builder-final-v2`. The goal of the refactor was to introduce a domain-agnostic, reusable `TreeBuilder` component and transition Query Records / Fetch Records filter state management from ad-hoc arrays to a canonical recursive tree AST (`{ type: "group", operator: "and", children: [...] }`).

### Key Findings & Verdict
1. **Target Contract Clarity**: The persisted contract (`config.filters`) is now cleanly established as a canonical tree AST. Backend lowering in `frappe_query_compat.py:_compile_filter_tree` converts this tree into Frappe Query Builder nested logic at query runtime.
2. **Duplicated Editing State & Watcher Loops**: `QueryFilterTree.vue` currently maintains a reactive `tree` state parallel to `TreeBuilder.root`. Edits trigger bidirectional watchers between `QueryFilterTree`, `TreeBuilder`, and `FetchRecordsConfig`, creating redundant cloning and potential synchronization edge cases.
3. **Legacy Adapter Residuals**: `filter_tree_adapter.js` still contains legacy array conversion logic (`serializeFilterTree`), which converts canonical trees to legacy flat/nested Frappe arrays (`[doctype, field, op, val]`). Since the persisted contract is now purely the canonical tree, frontend conversion to legacy arrays is obsolete and can be pruned once backend runtime tests strictly rely on canonical AST compilation.
4. **Condition Builder Alignment**: `TreeBuilder` abstracts tree structural operations (groups, leaves, drag-and-drop, keyboard shortcuts, logic operators) cleanly. However, `ConditionBuilder.vue` currently maintains its own independent recursive tree implementation (`ConditionGroupUI.vue`). `TreeBuilder` is structurally ready to become the shared lower-level primitive for both systems.

---

## Section A: Current Architecture & State Flow

### 1. Data & State Flow Diagram

```
                              Action Node Store Draft
                            (useGraphStore / useRuleConfig)
                                         │
                                 props.modelValue.filters
                                         │
                                         ▼
                            FetchRecordsConfig.vue
                       ├── filterTree (reactive ref)
                       └── localConfig.filters (canonical tree AST)
                                         │
                                 props.modelValue
                                         │
                                         ▼
                             QueryFilterTree.vue
                       └── tree (mirrored reactive ref)
                                         │
                                 props.modelValue
                                         │
                                         ▼
                              TreeBuilder.vue
                       └── root (reactive AST state)
                                         │
                           provided via treeBuilderActions
                                         │
                                         ▼
                            TreeBuilderNode.vue
                       └── renders group header OR #leaf slot
                                         │
                                    #leaf slot
                                         │
                                         ▼
                              FilterLeaf.vue
                     (Field / Operator / FlexValue controls)
```

### 2. Complete Trace Across Synchronization Boundaries

1. **Hydration Boundary (`FetchRecordsConfig.vue` & `QueryFilterTree.vue`)**:
   - `FetchRecordsConfig.vue` initializes `filterTree` by calling `deserializeFilterPayload(props.modelValue?.filters, { defaultDoctype })`.
   - `FetchRecordsConfig.vue` passes `filterTree` down to `QueryFilterTree.vue` via `:modelValue`.
   - `QueryFilterTree.vue` creates its own reactive `tree` ref from `normalizeTree(props.modelValue)` and passes it to `TreeBuilder.vue`.
   - `TreeBuilder.vue` initializes its internal reactive `root` state using `normalizeTree(props.modelValue)`.

2. **Editing Operations Boundary (`FilterLeaf.vue` -> `TreeBuilder.vue`)**:
   - When a user changes a field, operator, or value inside `FilterLeaf.vue`, `FilterLeaf` emits `@update:modelValue`.
   - `QueryFilterTree.vue` intercepts this emit in `updateLeaf(node, value)` and calls `treeBuilderRef.value.updateNode(node.id, updater)`.
   - `TreeBuilder.updateNode` directly mutates the target node in `TreeBuilder.root`.

3. **Structural Operations Boundary (`TreeBuilder.vue`)**:
   - Operations like `addLeaf`, `addGroup`, `removeNode`, `moveNode`, or toggling group operators (`and`/`or`) directly mutate `TreeBuilder.root`.
   - `TreeBuilder` has a deep watcher on `root`. When `root` changes, it emits `@update:modelValue` and `@change` with `cloneTree(root)`.

4. **Upward Propagation Boundary (`QueryFilterTree.vue` -> `FetchRecordsConfig.vue`)**:
   - `QueryFilterTree.vue` listens to `@update:modelValue` on `TreeBuilder`. Its `handleTreeUpdate` function updates its local `tree` ref and emits `@update:modelValue` to `FetchRecordsConfig.vue`.
   - `FetchRecordsConfig.vue` catches `@update:modelValue` in `updateFilterTree(value)`.
   - `updateFilterTree` updates `FetchRecordsConfig.filterTree`, converts the tree to canonical format via `toPersistedFilterTree(nextTree)`, assigns `localConfig.filters`, sets `filterDraftDirty = true`, and emits `@change` up to the Action Modal host.

5. **Validation & Persistence Boundary**:
   - At save/validation time, `FetchRecordsConfig.vue` calls `filterTreeRef.value.validate()`.
   - `QueryFilterTree.validate()` performs structural validation via `validateFilterTree()` and delegates leaf field/operator/value validation to `FilterLeaf.vue` instances via component refs.
   - Upon successful validation, `FetchRecordsConfig.commitFilters()` clones `localConfig.filters` into the node's persistent action configuration draft.

6. **Backend Execution Boundary (`frappe_query_compat.py`)**:
   - When Query Records executes on the backend, `execute_query()` receives `config.filters`.
   - If `filters` is a canonical tree (`type: "group"` or `type: "leaf"`), `_compile_filter_tree()` lowers the AST into Frappe Query Builder's nested condition list structure (e.g., `[["DocType", "field", "=", "val"], "and", ...]`).
   - `frappe.qb.get_query()` builds the native PyPika SQL query while preserving arbitrary AND/OR nesting.

---

## Section B: Synchronization Audit & Boundaries

### 1. State Owners Summary

| Component | State Owned | Role / Boundary |
| :--- | :--- | :--- |
| `TreeBuilder.vue` | `root` (reactive) | Authoritative editing state for tree hierarchy, group operators, and node order. |
| `QueryFilterTree.vue` | `tree` (reactive ref) | **Redundant Middleman**: Mirrors `TreeBuilder.root` and acts as a pass-through adapter. |
| `FetchRecordsConfig.vue` | `filterTree` & `localConfig.filters` | Bridge between local draft state and persistent action node configuration. |
| `FilterLeaf.vue` | `localRow` (reactive copy) | Local control state for a single leaf's field, operator, and value. |

### 2. Synchronization Issues & Vulnerabilities

1. **Mirrored Tree State in `QueryFilterTree.vue`**:
   `QueryFilterTree.vue` maintains `const tree = ref(normalizeTree(props.modelValue))` and a `watch(() => props.modelValue)` watcher, alongside a `handleTreeUpdate` handler. Because `TreeBuilder.vue` already owns `root` and normalizes incoming `modelValue`, `QueryFilterTree`'s `tree` ref is entirely redundant. Changes travel: `TreeBuilder` -> `QueryFilterTree` -> `FetchRecordsConfig` -> `QueryFilterTree` -> `TreeBuilder`, triggering multiple watcher turns and unnecessary `cloneTree()` allocations.

2. **Dual Representation Ambiguity in `filter_tree_adapter.js`**:
   The adapter currently provides two export functions for tree serialization:
   - `toPersistedFilterTree()`: Generates canonical AST (`{ type: "group", operator: "and", children: [...] }`).
   - `serializeFilterTree()`: Converts canonical AST to legacy flat/nested Frappe arrays (`[doctype, field, op, val]`).
   While `FetchRecordsConfig.vue` uses `toPersistedFilterTree()`, `QueryFilterTree.getPayload()` exposes `serializeFilterTree()`. This creates confusion about which function represents the ground truth.

3. **Dirty State Hydration Boundary Edge Case**:
   In `FetchRecordsConfig.vue`, `hydrateFilterTree` guards against overwriting active user edits using `if (filterDraftDirty.value) return;`. However, if the parent DocType changes in `FetchRecordsConfig.vue`, `hydrateFilterTree` is called with the new DocType. If `filterDraftDirty` is true, the tree does not reset leaf DocTypes until saved or discarded, which could leave stale DocTypes on leaves.

---

## Section C: Categorized Removal & Refactoring Candidates

The following list classifies code elements on `refactor/reusable-tree-builder-final-v2` into clear action categories based on empirical codebase verification.

### 1. Safe Removals (Immediate Cleanup)

| File | Code / Component / Function | Reason for Redundancy | Replacement / Alternative | Confidence Level |
| :--- | :--- | :--- | :--- | :--- |
| `QueryFilterTree.vue` | `const tree = ref(...)` and `watch(() => props.modelValue)` | `TreeBuilder.vue` already manages incoming props and internal reactive tree state. `QueryFilterTree` mirroring creates double reactivity cycles. | Pass `modelValue` directly to `TreeBuilder`. | **High (100%)** |
| `QueryFilterTree.vue` | `handleTreeUpdate` wrapper function | Re-clones and re-emits tree updates that `TreeBuilder` already emits cleanly. | Bind `TreeBuilder` events directly or forward emits (`@update:modelValue`). | **High (100%)** |
| `filter_tree_adapter.js` | `serializeFilterTree()` | Legacy array conversion (`[doctype, field, op, val]`). `config.filters` now strictly uses canonical tree AST. | Backend `_compile_filter_tree` handles runtime lowering. | **High (95%)** |
| `useGraphStore.js` | `clean_action_config()` legacy filter tuple flattening logic | Previously flattened filter arrays during canvas serialization. Now obsolete since filters are canonical ASTs. | Canonical AST serialization in `toPersistedFilterTree`. | **High (95%)** |

### 2. Likely Redundant Code Requiring Confirmation

| File | Code / Component / Function | Reason for Redundancy | Replacement / Alternative | Confidence Level |
| :--- | :--- | :--- | :--- | :--- |
| `FilterLeaf.vue` | Dual mode payload support (`modelValue` as Array vs Object) | Legacy filter leaves were wrapped in 1-element arrays (`[row]`). Canonical tree leaves pass plain objects. | Standardize `FilterLeaf` prop to expect a plain object payload. | **Medium-High (90%)** |
| `filter_tree_adapter.js` | `looksLikeLeafTuple()` and tuple conversion helpers | Exists to convert legacy 3-tuple / 4-tuple arrays to leaf objects. Necessary only if reading legacy rules. | Keep in `deserializeFilterPayload()` as backward-compatibility shim. | **Medium (85%)** |

### 3. Code That Must Remain (Core Infrastructure)

| File | Code / Component / Function | Role / Reason |
| :--- | :--- | :--- |
| `TreeBuilder.vue` | Core structural tree manager | Owns tree hierarchy, `addLeaf`, `addGroup`, `removeNode`, `moveNode`, keyboard shortcuts, and drag-and-drop. |
| `TreeBuilderNode.vue` | Recursive node wrapper | Renders group headers with logic toggles (`AND`/`OR`) and recurses for child nodes or leaf slots. |
| `FilterLeaf.vue` | Domain-specific filter row editor | Manages DocType, Field ComboBox, Operator selection, and FlexValue input controls for Fetch Records. |
| `toPersistedFilterTree()` | Canonical AST generator | Strips editor-only metadata (`id`) and produces clean persisted filter ASTs. |
| `frappe_query_compat.py` | `_compile_filter_tree()` | Backend AST compiler translating canonical trees into native Frappe QB filters. |

### 4. Architectural Improvements Deferred to Later Phase

| File | Feature / Component | Description / Deferred Objective |
| :--- | :--- | :--- |
| `ConditionBuilder.vue` | Condition Builder Migration | Refactor `ConditionBuilder` to replace `ConditionGroupUI.vue` with `TreeBuilder.vue` as its core tree primitive. |
| `TreeBuilder.vue` | Generic Collection / Sub-tree support | Extend `TreeBuilder` slot mechanism to support nested collection nodes (`where` clause sub-trees used in Condition Builder). |

---

## Section D: Comparison against Condition Builder

A core requirement of this architectural review is evaluating whether `TreeBuilder` duplicates capabilities already present in `ConditionBuilder`, and assessing its suitability as a shared lower-level primitive.

### 1. Comparative Architecture Matrix

| Feature / Aspect | Condition Builder (`ConditionBuilder.vue` / `ConditionGroupUI.vue`) | Query Filter Tree (`TreeBuilder.vue` / `QueryFilterTree.vue`) | Shared / Generalizable Status |
| :--- | :--- | :--- | :--- |
| **Tree AST Contract** | `{ op: "and", conditions: [...] }` | `{ type: "group", operator: "and", children: [...] }` | **Generalizable**: Canonical `type: "group"` / `type: "leaf"` model in `TreeBuilder` is cleaner and explicit. |
| **Node Types** | Condition Leaf, Group, Collection (`any`/`all` with `where` clause) | Leaf, Group | **TreeBuilder Extensible**: `TreeBuilder` can support custom node types via factory/slots. |
| **State Ownership** | `ConditionBuilder` owns `rootGroup` (reactive); `ConditionGroupUI` provides recursive rendering. | `TreeBuilder` owns `root` (reactive); `TreeBuilderNode` provides recursive rendering. | **Identical Pattern**: Both use top-level reactive root state with `provide/inject` action dispatchers. |
| **Drag & Drop** | Manual HTML5 drag handlers on `ConditionNode.vue` using `dragInfo`. | Built-in drag handlers on `TreeBuilderNode.vue` using `beginDrag`/`dropNode`. | **TreeBuilder Superior**: Handles descendant drop prevention and group drops cleanly. |
| **Keyboard Accessibility** | Basic focus management. | `Shift + Enter` shortcut to insert sibling leaf; automatic focus targeting on creation. | **TreeBuilder Superior**: Better keyboard UX out of the box. |
| **Domain Logic Coupling** | Embedded directly in `SimpleCondition.vue` and `ConditionGroupUI.vue` (Frappe operator API calls, alias context). | Decoupled: `TreeBuilder` is pure generic UI; domain concepts reside strictly in `FilterLeaf.vue` / `QueryFilterTree.vue`. | **TreeBuilder Architectural Target**: Clean domain decoupling. |

### 2. Evaluation Findings & Roadmap

1. **What `TreeBuilder` Abstracts Correctly**:
   - `TreeBuilder` successfully isolates group operator management (`AND`/`OR`), recursive rendering, node insertion/deletion, drag-and-drop reordering, and focus management from domain semantics.
   - It contains zero references to Frappe, DocTypes, or Query Builder.

2. **What `ConditionBuilder` Does Better (Gaps to Bridge)**:
   - `ConditionBuilder` supports Collection nodes (`addCollection`), which allow nested filtering over child table collections with contextual aliases (`alias: "row"`, `where: {...}`).
   - For `TreeBuilder` to fully replace `ConditionGroupUI` in the future, `TreeBuilder` should support configurable leaf/node types or custom node action slots.

3. **Condition Builder Migration Viability**:
   - `TreeBuilder` is well-architected for future adoption by `ConditionBuilder`. Migration will allow deleting `ConditionGroupUI.vue` and unifying tree-editing UI across FlexiRule.

---

## Section E: Recommended Target Architecture

### 1. Layered Separation of Concerns

```
┌────────────────────────────────────────────────────────────────────────┐
│                              TreeBuilder                               │
│  Generic, domain-agnostic tree editing primitive                      │
│  - State: root AST ({ type, operator, children })                     │
│  - Capabilities: Add/Remove/Move/Drag-Drop/Keyboard Shortcuts         │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         │                                                   │
         ▼                                                   ▼
┌───────────────────────────────┐           ┌───────────────────────────────┐
│       Condition Builder       │           │        QueryFilterTree        │
│  Condition Semantics          │           │  Filter Semantics             │
│  - SimpleCondition (L / Op / R)│           │  - FilterLeaf (DT / Fld / Op) │
│  - Collection sub-trees       │           │  - Frappe Metadata / Links    │
│  - FlexValue integration      │           │  - FlexValue integration      │
└──────────────┬────────────────┘           └──────────────┬────────────────┘
               │                                           │
               ▼                                           ▼
  { op, conditions: [...] }                      { type: "group", ... }
    (Condition Payload)                            (config.filters AST)
               │                                           │
               ▼                                           ▼
  Condition Evaluator Engine                     frappe_query_compat.py
   (Rule Execution Gate)                          (_compile_filter_tree)
```

### 2. Principles of Target Architecture
- **TreeBuilder**: Pure UI primitive. Does not import Frappe, DocTypes, or action handlers.
- **QueryFilterTree**: Lightweight domain wrapper around `TreeBuilder`. Passes `FilterLeaf` into `#leaf` slot. Does not duplicate reactive tree state.
- **FetchRecordsConfig**: Manages hydration and validation/commit boundaries for action configuration.
- **Backend Compiler**: Receives canonical tree ASTs and handles query engine translation.

---

## Section F: Proposed Implementation Phases

### Phase 1: Cleanup & Streamlining of `refactor/reusable-tree-builder-final-v2` (Current Focus)
1. **Remove Duplicate State in `QueryFilterTree.vue`**:
   - Eliminate local `tree` ref and `watch(() => props.modelValue)` in `QueryFilterTree.vue`.
   - Forward `modelValue` directly to `TreeBuilder.vue` and pass emits upward without re-cloning.
2. **Standardize Serialization & Prune Dead Legacy Code**:
   - Rely strictly on `toPersistedFilterTree()` for `config.filters`.
   - Deprecate/remove `serializeFilterTree()` and legacy tuple flattening methods in `useGraphStore.js` after verifying test coverage.
3. **Clean Up `FilterLeaf.vue` Model Binding**:
   - Simplify `FilterLeaf` to accept plain leaf objects directly rather than supporting legacy 1-element array wrappers.

### Phase 2: Condition Builder Migration (Deferred Future Phase)
1. **Extend `TreeBuilder` Node Types**:
   - Add support for custom node types (e.g., Collection nodes) and custom group action slots in `TreeBuilder.vue`.
2. **Refactor `ConditionBuilder.vue`**:
   - Replace `ConditionGroupUI.vue` with `TreeBuilder.vue` using `SimpleCondition.vue` in the `#leaf` slot.
3. **Delete Obsolete UI Code**:
   - Remove `ConditionGroupUI.vue` and redundant drag-and-drop handlers.

---

## Conclusion & Next Steps

Branch `refactor/reusable-tree-builder-final-v2` achieves its core objective: establishing a clean, canonical recursive tree AST for Query Records filters backed by an evidence-verified backend compiler (`_compile_filter_tree`).

By completing the Phase 1 cleanup steps outlined in Section F (eliminating mirrored state in `QueryFilterTree.vue` and pruning legacy array adapters), the tree builder architecture will be minimal, production-ready, and prepared for future adoption across FlexiRule.
