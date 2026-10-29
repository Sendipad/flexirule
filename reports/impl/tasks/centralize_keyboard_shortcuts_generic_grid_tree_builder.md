# Implementation Plan: Centralize and Unify Keyboard Shortcuts Across Generic Grid and Tree Builder

## Status and Intent

**Status:** Proposed Formal Implementation Plan.

**Goal:** Centralize and unify keyboard shortcut handling across `GenericGrid` and `TreeBuilder` using a single authoritative shortcut matching and dispatch mechanism built on `useKeyboardRegistry.js`. Standardize the `Ctrl+Shift+E` view-transition shortcut (toggling between readable summary and edit mode) across both components, introduce active node tracking in `TreeBuilder` for keyboard interaction, and preserve component-specific shortcut extensions, focus semantics, backward compatibility, and accessibility.

---

## 1. Current Architecture and Findings

### Source Analysis

1. **`GenericGrid.vue`** (`flexirule/public/js/flexirule/rule_builder/controls/GenericGrid.vue`):
   - Handles keyboard shortcuts locally in an inline `handleKeydown(event)` method attached to the root grid container via `@keydown`.
   - Uses `matchesShortcut(event, shortcut)` from `generic_grid_model.mjs` to match key combinations against props (`props.editShortcut` defaulting to `"Ctrl+Shift+E"`, `props.primaryActionShortcut` defaulting to `"Shift+Enter"`).
   - Handles `Ctrl+C` and `Ctrl+V` for clipboard row copy/paste when focus is not inside interactive input controls.
   - Handles row navigation (`ArrowUp`, `ArrowDown`, `Home`, `End`, `PageUp`, `PageDown`, `Space`) on focused rows.
   - Handles `Shift+Enter` for triggering primary actions and `props.actionOptions[].shortcut` for secondary actions.

2. **`TreeBuilder`** (`TreeBuilder.vue`, `TreeBuilderNode.vue`, `TreeBuilderLeaf.vue`, `useTreeBuilder.js`):
   - Currently has **no keyboard shortcut event listeners or handlers**.
   - Leaf edit state is managed via `editingNodeId` in `useTreeBuilder.js` (using `setEditing()` and `finishEditing()`), but mode transitions are triggered solely via double-click on the summary surface or clicking mouse buttons.
   - Lacks an explicit keyboard focus or active node selection concept for non-editing leaves.

3. **`useKeyboardRegistry.js`** (`flexirule/public/js/flexirule/rule_builder/composables/useKeyboardRegistry.js`):
   - Provides a module-level singleton registry with context stack (`pushContext`, `popContext`), priority sorting, reserved browser key blocking, and a global `window` keydown listener.
   - Currently requires registering discrete boolean modifier flags (`ctrl: true`, `meta: true`, `shift: true`, `alt: true`) and exact single-character `key` strings, rather than parsing string formats like `"Ctrl+Shift+E"`.
   - Bypasses input controls by checking `isInput` unless `bestMatch` has `ctrl` or `meta`.
   - Used in `App.vue` for global shortcuts (Save `Ctrl+S`, Test `Alt+D`, Undo/Redo, Shortcuts Help `?`), but not currently consumed by `GenericGrid` or `TreeBuilder`.

4. **`generic_grid_model.mjs`** (`flexirule/public/js/flexirule/rule_builder/controls/generic_grid_model.mjs`):
   - Contains `matchesShortcut(event, shortcut)` which parses key strings like `"Ctrl+Shift+E"`, `"Shift+Enter"`, `"Alt+Shift+A"`, normalizing modifiers (`ctrl`, `control`, `cmd`, `meta`, `command`, `alt`, `shift`) and checking against `event.key`, `event.ctrlKey`, `event.metaKey`, `event.shiftKey`, and `event.altKey`.

### Duplication, Inconsistencies, and Defects

- **Duplicated & Inconsistent Key Matching:** `useKeyboardRegistry.js` and `generic_grid_model.mjs` parse key events differently. `useKeyboardRegistry` relies on manual object options (`{ key: 'e', ctrl: true, shift: true }`), while `generic_grid_model.mjs` parses strings (`"Ctrl+Shift+E"`).
- **Missing Shortcuts in Tree Builder:** `TreeBuilder` lacks shortcut support entirely, creating an inconsistent editing experience compared to `GenericGrid`.
- **Input Control Bypass Discrepancies:** `GenericGrid` manually checks `isInputTarget(target)` in its `handleKeydown` method, while `useKeyboardRegistry` uses `isInput`.

---

## 2. Proposed Centralized Architecture

### Centralized Keyboard Shortcut Registry & Key Matcher

We will enhance `useKeyboardRegistry.js` and `generic_grid_model.mjs` to form a single, cohesive shortcut mechanism:

1. **Unified Key Matcher (`generic_grid_model.mjs` / `useKeyboardRegistry.js`):**
   - Consolidate string-based shortcut normalization (`"Ctrl+Shift+E"`, `"Shift+Enter"`, `"Ctrl+S"`) into `matchesShortcut` / `parseShortcutString` as the authoritative helper used across both registry registration and direct event evaluation.
   - Support string inputs (`shortcut: "Ctrl+Shift+E"`) directly in `registerShortcutOptions` within `useKeyboardRegistry.js`.

2. **Input Skipping Policy (`allowInInputs` / `isGlobalInputShortcut`):**
   - Application shortcuts with modifier keys (e.g., `Ctrl+Shift+E`, `Ctrl+S`) must remain triggerable when focus is inside interactive controls (`<input>`, `<textarea>`, `<select>`, `.fxr-control`, etc.) if explicitly allowed or safe.
   - Ordinary typing and navigation keys (e.g. single letters, `Space`) are skipped when typing in inputs to prevent accidental interception.

3. **Scoped Context & Lifecycle Management:**
   - Components (`GenericGrid` and `TreeBuilder`) register their shortcuts into component-level contexts (or handle container keydown with central matching) during `onMounted` / `onUnmounted`.
   - Event listeners are automatically unregistered when components unmount, preventing memory leaks or duplicate handlers.

4. **Separation of Concerns:**
   - Central Registry: Key combination parsing, modifier checking, event matching, priority ordering, `preventDefault()` and `stopPropagation()`.
   - Components: Specific business logic (`toggleEditView`, `addLeaf`, `pasteRows`, etc.).

---

## 3. Common and Component-Specific Shortcuts

### Inventory & Classification

| Shortcut Identifier | Default Key Combination | Scope / Category | Description |
| :--- | :--- | :--- | :--- |
| **`editShortcut`** | `Ctrl+Shift+E` | **Shared** | Toggle row/leaf between read-only/summary view and edit view. Works inside inputs for active item. |
| **`primaryActionShortcut`** | `Shift+Enter` | **Generic Grid** / **Tree Builder Extension** | Invoke primary action (e.g. Add Row or Add Leaf). |
| **`copy`** | `Ctrl+C` | **Generic Grid** | Copy selected rows (when focus is outside inputs). |
| **`paste`** | `Ctrl+V` | **Generic Grid** | Paste copied rows (when focus is outside inputs). |
| **`gridNavigation`** | `ArrowUp`, `ArrowDown`, `Home`, `End`, `PageUp`, `PageDown`, `Space` | **Generic Grid** | Focus navigation and range selection across rows. |
| **`treeNavigation`** | `ArrowUp`, `ArrowDown`, `Home`, `End` | **Tree Builder** | Focus navigation across active tree nodes. |
| **`deleteNode`** | `Delete` / `Backspace` | **Tree Builder Extension** | Delete focused node (when focus is outside inputs). |
| **`customGridAction`** | `action.shortcut` | **Consumer Configurable** | Trigger secondary or pinned action from `actionOptions`. |

---

## 4. Read-Only and Edit View Transition (`Ctrl+Shift+E`)

1. **Canonical Definition:**
   - Default shortcut: `Ctrl+Shift+E` (configurable via `editShortcut` prop in both `GenericGrid.vue` and `TreeBuilder.vue`).
2. **Behavior in `GenericGrid`:**
   - Preserved exactly as existing: toggles selected or active row(s) between summary/readable mode and editor mode using `getBulkEditAction()`.
3. **Behavior in `TreeBuilder`:**
   - `TreeBuilder` tracks `focusedNodeId` or active leaf selection when clicked or navigated via keyboard.
   - Pressing `Ctrl+Shift+E` while a leaf is active or while focus is inside an input control within that leaf calls `setEditing(nodeId)` if in summary mode, or `finishEditing(nodeId)` if in edit mode.
   - Unsaved changes / validation: In `Hybrid` mode, `finishEditing()` validates the leaf using `isLeafValid`. If invalid, editing mode is safely retained to prevent data loss.
   - If `readOnly` is `true`, view transitions or mutation shortcuts are safely suppressed.

---

## 5. Backward Compatibility and Accessibility

- **Props & Public API:**
  - `GenericGrid.vue`: `editShortcut` (default `"Ctrl+Shift+E"`), `primaryActionShortcut` (default `"Shift+Enter"`).
  - `TreeBuilder.vue`: Add `editShortcut` prop (default `"Ctrl+Shift+E"`).
- **Model Utilities:**
  - `matchesShortcut(event, shortcut)` in `generic_grid_model.mjs` remains fully backward-compatible for existing unit tests and callers.
- **Accessibility:**
  - Preserve `aria-keyshortcuts` attributes on toolbar buttons and row/leaf action elements.
  - Apply `preventDefault()` and `stopPropagation()` only on matched application commands, preserving standard browser and assistive technology navigation.

---

## 6. Testing Strategy

1. **Key Matcher & Registry Unit Tests:**
   - Test `matchesShortcut` for case-insensitivity, modifier matching (`Ctrl`, `Meta`, `Shift`, `Alt`), and invalid inputs in `generic_grid_model.test.mjs`.
   - Test string-based registration and `allowInInputs` behavior in `useKeyboardRegistry.js`.
2. **Generic Grid Keyboard Interaction Tests:**
   - Verify `Ctrl+Shift+E` toggles editing mode for selected/active rows.
   - Verify `Shift+Enter` triggers primary action.
   - Verify input control typing bypasses non-modifier shortcuts.
3. **Tree Builder Keyboard Interaction Tests:**
   - Verify `editShortcut` (`Ctrl+Shift+E`) toggles leaf editing state.
   - Verify unmounting `TreeBuilder` cleans up event listeners without side effects.
4. **Regression Testing:**
   - Execute full test suite via `npm test`.
   - Run `pre-commit run --all-files` before submission.

---

## 7. Implementation Sequence and Acceptance Criteria

### Implementation Sequence

1. **Centralize & Unify Key Matching in `useKeyboardRegistry.js` & `generic_grid_model.mjs`**:
   - Update `useKeyboardRegistry.js` to support string shortcut registration (`shortcut: "Ctrl+Shift+E"`) and integrate with `matchesShortcut`.
2. **Refactor `GenericGrid.vue` Shortcut Handling**:
   - Standardize `GenericGrid.vue` keydown handling to use the unified matcher/registry.
3. **Enhance `TreeBuilder` with Active Node Focus & `Ctrl+Shift+E` View Transition**:
   - Add `editShortcut` prop to `TreeBuilder.vue`.
   - Wire keyboard focus and `Ctrl+Shift+E` toggle in `useTreeBuilder.js` / `TreeBuilderLeaf.vue`.
4. **Add Unit & Component Tests**:
   - Write tests in `generic_grid_model.test.mjs` and `tree_builder.test.mjs`.
5. **Run Verification & Pre-Commit Checks**:
   - Run `npm test` and `pre-commit run --all-files`.

### Acceptance Criteria

1. **Single Matcher & Registry Core:** Key parsing and matching logic has one authoritative implementation shared across components.
2. **Generic Grid & Tree Builder Integration:** Both components share the centralized shortcut mechanism.
3. **Unified View Transition:** `Ctrl+Shift+E` toggles between readable summary and edit mode in both `GenericGrid` and `TreeBuilder`.
4. **Input Control Safety:** Modifier shortcuts (`Ctrl+Shift+E`) work inside inputs; ordinary typing keys are not intercepted.
5. **Clean Lifecycle Cleanup:** Event listeners are correctly removed on component unmount.
6. **Full Test & Lint Pass:** All tests pass, linting passes, and pre-commit checks run clean.
