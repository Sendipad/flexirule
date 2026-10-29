# Implementation Plan: Centralized Keyboard Shortcuts Across GenericGrid and TreeBuilder

## 1. Current Architecture and Findings

### File Locations & Implementation Audit
- **Keyboard Registry**: `flexirule/public/js/flexirule/rule_builder/composables/useKeyboardRegistry.js`
  - Provides basic registration (`registerShortcut`), context pushing/popping (`pushContext`, `popContext`), and global keydown dispatch (`handleKeydown`).
- **GenericGrid**: `flexirule/public/js/flexirule/rule_builder/controls/GenericGrid.vue` and `generic_grid_model.mjs`
  - Features local inline keydown handler (`handleKeydown`) for ArrowUp/Down, Home/End, Space, Shift+Enter (Primary action), Ctrl+Shift+E (Edit/View toggle), Ctrl+C, Ctrl+V, and custom secondary action shortcuts.
  - Parsing and matching relies on `matchesShortcut(event, shortcutString)` in `generic_grid_model.mjs`.
- **TreeBuilder**: `flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilder.vue`, `TreeBuilderLeaf.vue`, and `useTreeBuilder.js`
  - Lacks dedicated keyboard shortcut registration or keyboard event listeners for edit mode toggling or tree navigation.
  - Double-click on summary triggers `startEditing()`, but `Ctrl+Shift+E` and arrow navigation are missing/unhandled.
- **Presentation Policy**: `flexirule/public/js/flexirule/rule_builder/controls/inline_presentation_policy.mjs`
  - Shared policy determining when rows/leaves are in `summary` vs `editor` presentation mode.

### Gaps & Inconsistencies
1. Keyboard handling in `GenericGrid` is hardcoded directly inside its `<template @keydown="handleKeydown">` rather than utilizing or sharing composables with `TreeBuilder`.
2. `TreeBuilder` does not support keyboard shortcuts for row/leaf editing (`Ctrl+Shift+E`) or keyboard navigation.
3. Matching string representations (e.g. `"Ctrl+Shift+E"`, `"Shift+Enter"`) is implemented in `generic_grid_model.mjs` independently of `useKeyboardRegistry.js`.

---

2. Proposed Centralized Architecture

### Central Composables & Models
- **`useKeyboardShortcuts.js` (or enhancing `useKeyboardRegistry.js`)**:
  - Centralize shortcut string parsing (`parseShortcutString`) and matching logic (`matchesShortcut`).
  - Provide a reusable composable/helper `useListKeyboardNavigation` or unified shortcut handling for structured collections (`GenericGrid` and `TreeBuilder`).
  - Ensure lifecycle cleanup on unmount.

### Extension & Conflict Resolution
- Component instances register context (`grid`, `tree_builder`) or handle local keydown events with unified helper utilities.
- Input control guard:
  - Modified shortcuts (`Ctrl+Shift+E`, `Shift+Enter`) execute even when focus is inside interactive input elements within a grid row or tree leaf.
  - Unmodified navigation (`ArrowUp`/`ArrowDown`, `Home`/`End`, `Space`) is suppressed when focus is inside editable controls (`<input>`, `<textarea>`, `<select>`, `[contenteditable="true"]`).

---

3. Inventory of Shortcuts

| Identifier | Key Combo | Category | Target Component(s) | Description |
|---|---|---|---|---|
| `toggle-edit` | `Ctrl+Shift+E` | Shared | GenericGrid, TreeBuilder | Toggles row/leaf between summary and edit view |
| `nav-up` | `ArrowUp` | Shared | GenericGrid, TreeBuilder | Moves focus/selection to previous item |
| `nav-down` | `ArrowDown` | Shared | GenericGrid, TreeBuilder | Moves focus/selection to next item |
| `nav-home` | `Home` | Shared | GenericGrid, TreeBuilder | Moves focus/selection to first item |
| `nav-end` | `End` | Shared | GenericGrid, TreeBuilder | Moves focus/selection to last item |
| `select-item` | `Space` | Shared | GenericGrid, TreeBuilder | Toggles item selection |
| `primary-action` | `Shift+Enter` | Component-Specific | GenericGrid | Executes primary grid action (e.g. Add Row) |
| `copy-rows` | `Ctrl+C` / `Cmd+C` | Component-Specific | GenericGrid | Copies selected rows |
| `paste-rows` | `Ctrl+V` / `Cmd+V` | Component-Specific | GenericGrid | Pastes copied rows |

---

4. Read-Only and Edit View Transition Integration

- Standard default: `Ctrl+Shift+E`.
- `GenericGrid`: Supports prop `editShortcut` (default `"Ctrl+Shift+E"`).
- `TreeBuilder`: Accepts `editShortcut` prop (default `"Ctrl+Shift+E"`).
- Uses `getInlinePresentation` from `inline_presentation_policy.mjs` to evaluate whether toggling is allowed (`canToggle`).
- Focus management: Preserves active leaf/row focus when toggled.

---

5. Backward Compatibility and Accessibility

- All existing props (`editShortcut`, `primaryActionShortcut`) remain functional with zero breaking changes.
- `aria-keyshortcuts` attributes updated dynamically on relevant controls.
- Proper use of `preventDefault()` and `stopPropagation()` to avoid browser accelerator collisions.

---

6. Testing Strategy

- **Unit & Integration Tests**:
  - `tests/frontend/flexirule/rule_builder/controls/generic_grid_model.test.mjs`: Verify shortcut string parsing/matching.
  - `tests/frontend/flexirule/rule_builder/components/tree_builder/tree_builder.test.mjs`: Test leaf editing keyboard shortcuts (`Ctrl+Shift+E`) and navigation.
  - New test file `tests/frontend/flexirule/rule_builder/composables/keyboard_shortcuts.test.mjs` for centralized shortcut utilities.

---

7. Implementation Sequence and Acceptance Criteria

1. **Step 1**: Centralize shortcut parsing & matching utilities in frontend codebase.
2. **Step 2**: Integrate `TreeBuilder` with keyboard shortcut handling (leaf edit toggle and navigation).
3. **Step 3**: Refactor `GenericGrid` to use shared shortcut utilities while maintaining backward compatibility.
4. **Step 4**: Add test coverage for both components and run `npm test`.
5. **Step 5**: Perform pre-commit checks and submit changes.
