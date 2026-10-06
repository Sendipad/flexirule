# Query Records Filter Tree — Production Implementation Plan & Realized Architecture

**Repository:** `Sendipad/flexirule`  
**Source branch:** `refactor/query-records`
**Report path:** `reports/query-records/filter-tree-adapter-implementation-plan.md`  
**Scope:** Reusable Tree Builder architecture, standalone `FilterLeaf.vue` single-row filter editor with independent field navigation context, and explicit domain boundary via `filter_tree_adapter.js`.

---

## 1. Executive Summary & Realized Architecture

The implementation establishes a clean, reusable **Tree Builder** architecture for Fetch Records and query filter trees while keeping legacy components (`FilterGroup.vue`) completely independent.

```
                    Fetch Records / Query Filter Tree
                                   │
                                   ▼
                        Domain / Adapter Layer
                        (filter_tree_adapter.js)
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                serialize      deserialize    validation
                    │              │              │
                    └──────────────┼──────────────┘
                                   │
                                   ▼
                         Reusable Tree Builder
                          (TreeBuilder.vue)
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                 Groups          Leaves       Interaction
             (TreeBuilderNode)  (slot)    (Shift+Enter, Drag)
                                   │
                                   ▼
                              FilterLeaf
                       ├── Field (ComboBoxControl)
                       ├── Navigation (useNavigableFields)
                       ├── Operator
                       ├── Value (FlexValueControl)
                       └── Leaf Validation
```

---

## 2. Core Architectural Principles & Boundaries

1. **TreeBuilder is strictly domain-agnostic:**
   - Operates on generic structural tree nodes (`{ id, type: 'leaf' | 'group', operator, children }`).
   - Owns structural operations: add leaf, add group, remove node, move node, reorder siblings, structural drag-and-drop, focus management, active node selection, and keyboard shortcuts (`Shift + Enter` to insert a sibling leaf next to the active node).
   - Configurable capabilities via props (`canAddLeaf`, `canAddGroup`, `canDelete`, `canMove`, `canDrag`, `canDrop`, `canChangeLogicalOperator`).
   - Does NOT know about Fetch Records, filter comparison operators, FlexValue, DocTypes, or backend query syntax.

2. **Standalone FilterLeaf.vue Single-Row Filter Editor:**
   - Single-row filter editor owned by the Fetch Records domain.
   - Operates on a single filter payload `{ doctype, field, operator, value }`.
   - Owns its own dedicated, independent `useNavigableFields()` composable instance to prevent shared or indexed navigation state bugs across multiple leaves.
   - Houses `ComboBoxControl` for field selection with Link/child table navigation support, operator selection dropdown, and `FlexValueControl` for value/resolver configuration.

3. **Blank Filter Leaf Handling:**
   - A newly added blank leaf (`field: ""`, `operator: "="`, `value: { mode: "static", value: "" }`) immediately renders its controls (Field picker, Operator dropdown, Value control) in the UI tree.
   - Blank leaves remain visible during editing as a valid UI editing state.
   - Blank/incomplete leaves are rejected during validation (`validateFilterTree` and leaf-level `validate()`) to prevent executing unconfigured queries.

4. **Filter Tree Adapter Boundary (`filter_tree_adapter.js`):**
   - Pure domain boundary between the UI tree model and the backend Fetch Records filter payload.
   - Handles `deserializeFilterPayload`, `serializeFilterTree`, `normalizeFilterTree`, and `validateFilterTree`.
   - Converts backend filter arrays (`[doctype, field, operator, value]` and nested logical groups `[leaf1, "or", leaf2]`) into UI tree structures and vice versa.
   - Preserves FlexValue structures (static, variable, resolver/expression modes) intact.

5. **Legacy Independence:**
   - `FilterGroup.vue` remains completely untouched and independent for legacy flat filter consumers.
   - No dependencies exist between `TreeBuilder.vue` or `FilterLeaf.vue` and `FilterGroup.vue`.

---

## 3. Realized Ownership Matrix

| Responsibility | Component / Module |
|---|---|
| Interactive generic tree & keyboard/drag interaction | `TreeBuilder.vue` & `TreeBuilderNode.vue` |
| Generic tree utility functions | `tree_builder_utils.js` |
| Single-row filter editor | `FilterLeaf.vue` |
| Independent leaf field navigation | `FilterLeaf.vue` → `useNavigableFields.js` |
| Filter Tree ↔ Backend serialization boundary | `filter_tree_adapter.js` |
| Query Filter Tree UI integration | `QueryFilterTree.vue` |
| Action configuration container | `FetchRecordsConfig.vue` |
| Query execution & Frappe API compatibility | Backend `query_records.py` & `frappe_query_compat.py` |

---

## 4. Verification & Testing

- Unit tests in `filter_tree_adapter.test.js` verify single leaf serialization/deserialization, nested AND/OR precedence, mixed operator sequence left-associativity, FlexValue object preservation, blank/incomplete leaf validation, and UI property stripping.
- Asset compilation via `bench build --app flexirule` executed cleanly.
- Code formatting and linter checks verified across all modified tree builder and filter leaf files.
