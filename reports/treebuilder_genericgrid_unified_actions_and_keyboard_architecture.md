# TreeBuilder & GenericGrid — Unified Actions, Keyboard Shortcuts, and Contextual Options Menu Architecture

**Target Document:** `reports/treebuilder_genericgrid_unified_actions_and_keyboard_architecture.md`
**Repository:** `/Sendipad/flexirule`
**Branch:** `feat/canonical-condition-backend-3777722595536260068`
**Status:** Approved Architecture and Implementation Plan
**Scope:** Architectural Analysis, Design Specification, and Implementation Roadmap (No application code changes in this phase)

---

## Executive Summary

`TreeBuilder` (hierarchical condition and filter tree structures) and `GenericGrid` (tabular/list models for outputs and records) are FlexiRule's two core visual structural components. Both components have evolved independently, leading to divergent interaction patterns:

1. **Delete Button Proliferation:** Both `TreeBuilderLeaf` (`flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilderLeaf.vue`) and `GenericGrid` (`flexirule/public/js/flexirule/rule_builder/controls/GenericGrid.vue`) render dedicated delete icon buttons on every single row/leaf, introducing visual noise, accidental deletions, and UI inconsistency.
2. **Scattered Action & Shortcut Logic:** `GenericGrid.vue` implements custom inline keyboard listeners for `Ctrl+Shift+E`, `Shift+Enter`, `ArrowUp/Down`, `Space`, `Ctrl+C`, and `Ctrl+V` inside its own container `@keydown`, while `TreeBuilder` relies on individual DOM listeners, drag-and-drop, and parent modal listeners.
3. **Flat, Non-Hierarchical Keyboard Registry:** `useKeyboardRegistry.js` (`flexirule/public/js/flexirule/rule_builder/composables/useKeyboardRegistry.js`) maintains a flat `Set` of active context strings (`activeContexts.value.add(context)`). In nested modal flows (`RuleConfigModal` → `FetchRecordsConfig` → `OutputFieldsEditor` or `QueryFilterTree`), there is no scoped stacking mechanism to direct keyboard events exclusively to the active component without risk of collision or accidental triggers.
4. **Action Divergence:** Actions such as "Toggle Edit/Summary", "Copy", "Duplicate", "Insert", and "Remove" are implemented redundantly across templates, buttons, and keyboard handlers.

This document presents a unified, extensible **Command / Action Architecture** that:
- Centralizes action metadata (ID, label, icon, shortcut hint, visibility, disabled state, execution handler, confirmation policy) into an authoritative, reusable layer.
- Introduces an accessible, responsive **Contextual Options Menu (`RowActionsMenu.vue`)** triggered via an ellipsis (`⋮`) button, replacing individual row/leaf delete buttons while keeping high-frequency view/edit toggles and reorder handles inline.
- Upgrades `useKeyboardRegistry.js` with **hierarchical scoped context stacks**, strict editor/input safety boundaries, and context-priority dispatching.
- Establishes a zero-regression, 5-phase migration strategy with concrete acceptance criteria and testing harnesses.

---

## 1. Current Implementation Architecture and Interaction Flow

### 1.1 GenericGrid Component Architecture

- **Primary Component:** `flexirule/public/js/flexirule/rule_builder/controls/GenericGrid.vue` (Lines 1–1105)
- **Helper Models:** `flexirule/public/js/flexirule/rule_builder/controls/generic_grid_model.mjs`, `inline_presentation_policy.mjs`
- **Active Consumers:**
  - `OutputFieldsEditor.vue` (`flexirule/public/js/flexirule/rule_builder/components/rule_config/types/query_records/OutputFieldsEditor.vue`)
  - `FetchRecordsConfig.vue` (`flexirule/public/js/flexirule/rule_builder/components/rule_config/types/query_records/FetchRecordsConfig.vue`)

#### Current Interaction Flow:
1. **Row Toolbar Actions:** Lines 61–152 of `GenericGrid.vue` render an inline action cluster inside each row's index column:
   - Edit / Readable mode toggle button (`fa-pencil` / `fa-check`)
   - Up / Down reorder buttons (`fa-chevron-up` / `fa-chevron-down`)
   - Remove row button (`fa-trash` with class `.is-danger`)
2. **Keyboard Handling:** Bound directly to the grid root `<div>` via `@keydown="handleKeydown"` (Lines 18, 590–716):
   - `Ctrl/Cmd + C`: Copies selected rows via `copySelectedRows()`
   - `Ctrl/Cmd + V`: Pastes rows via `pasteRows()`
   - `Ctrl+Shift+E`: Toggles edit/summary mode for selected or active entries
   - `Shift+Enter`: Invokes pinned primary action (e.g. `add-field`)
   - Secondary shortcuts: Scans `resolvedActionOptions` for custom shortcuts (e.g., `Alt+Shift+F`, `Alt+Shift+G`, `Alt+Shift+L`)
   - Navigation: `ArrowUp`, `ArrowDown`, `Home`, `End`, `PageUp`, `PageDown`
   - Selection: `Space` on row index button toggles row selection
3. **Double Click:** Double-clicking summary toggles editing mode (`toggleSummaryRow`, Line 427).
4. **Drag Selection:** Pointer drag across row numbers selects row ranges (`beginDragSelection`, `extendDragSelection`, Lines 344–387).

### 1.2 TreeBuilder Component Architecture

- **Hierarchy:**
  - `TreeBuilder.vue` (`flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilder.vue` Lines 1–183) — Root container, operator selector, add leaf/group buttons, drag-drop drop target.
  - `TreeBuilderNode.vue` (`TreeBuilderNode.vue` Lines 1–352) — Recursive dispatcher for `group`, `collection`, and `leaf` nodes.
  - `TreeBuilderGroup.vue` (`TreeBuilderGroup.vue` Lines 1–125) — Logical AND/OR container with inline `add-leaf`, `add-group`, `add-collection`, and `remove` buttons.
  - `TreeBuilderCollection.vue` (`TreeBuilderCollection.vue` Lines 1–85) — Scope container for child tables/collections with inline `add-leaf`, `add-group`, `add-collection`, and `remove` buttons.
  - `TreeBuilderLeaf.vue` (`TreeBuilderLeaf.vue` Lines 1–228) — Terminal condition/filter leaf rendering summary or editor with inline `edit`, `finish`, and `remove` buttons.
  - `useTreeBuilder.js` (`useTreeBuilder.js` Lines 1–285) — Reactive state, immutability wrapper (`mutate`), selection, focus, editing ID, expansion, and drag state.
- **Active Consumers:**
  - `CanonicalConditionBuilder.vue` (`flexirule/public/js/flexirule/rule_builder/components/condition_builder/CanonicalConditionBuilder.vue`)
  - `QueryFilterTree.vue` (`flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/QueryFilterTree.vue`)

#### Current Interaction Flow:
1. **Leaf Action Buttons:** Lines 33–50 and 87–104 of `TreeBuilderLeaf.vue` render inline buttons:
   - Edit toggle (`fa-pencil` or `fa-check`)
   - Remove leaf (`fa-trash` with class `.tree-leaf__remove`)
2. **Container Actions:** `TreeBuilderGroup.vue` (Lines 18–44) and `TreeBuilderCollection.vue` (Lines 14–39) render inline add and delete buttons:
   - Add condition (`fa-plus`)
   - Add group (`fa-folder-open-o`)
   - Add collection (`fa-sitemap`)
   - Remove container (`fa-times` with class `.fxr-btn--danger`)
3. **Keyboard Handling:** Currently, `TreeBuilder` does not implement component-level keyboard shortcuts for node navigation, leaf selection, deletion, or duplication. Users must rely entirely on mouse clicks and HTML5 drag-and-drop.
4. **Safeguard Interception:** `TreeBuilder.vue` exposes `:beforeRemove="confirmNodeRemoval"`. When invoked in `CanonicalConditionBuilder.vue` (Lines 159–185), it verifies whether deleting the node would leave 0 conditions in an entry action, prompting `frappe.confirm` to prevent accidental unconditioned rule activation.

### 1.3 Interaction Flow Comparison Matrix

| Interaction | `GenericGrid` Current Flow | `TreeBuilder` Current Flow | Genuinely Shared Semantics | Divergent / Domain-Specific Semantics |
|---|---|---|---|---|
| **Toggle View/Edit** | Inline button (`fa-pencil`/`fa-check`), double-click summary, or `Ctrl+Shift+E`. State tracked via `row[editStateKey]`. | Inline button (`fa-pencil`/`fa-check`), double-click summary. State tracked via `editingNodeId` in `useTreeBuilder`. | **Yes:** Pure UI mode switch between summary slot and active editor slot. Guarded by `canToggle` and `isValid`. | In `GenericGrid`, rows are plain objects. In `TreeBuilder`, editing ID is centralized in composable context (`setEditing(node.id)`). |
| **Select / Focus** | Index button click / Spacebar / pointer drag selects row keys in `Set`. Focus on grid root. | `selectNode(id)` and `focusNode(id)` exist in `useTreeBuilder.js`, but lack UI selection indicators or keyboard shortcuts. | **Yes:** Active target resolution for subsequent command execution. | `GenericGrid` supports multi-selection range drag; `TreeBuilder` targets a single node/subtree in hierarchical depth. |
| **Delete / Remove** | Inline trash button per row (`requestRowAction('remove', entry)`). Emits `row-action` to parent. | Inline trash button on leaves and containers (`$emit('remove')`). Passes through `beforeRemove` hook. | **Yes:** Resolves item, executes safety guard, requests confirmation if dangerous, deletes, restores focus. | `TreeBuilder` has recursive subtree deletion and entry action rules (`isSoleCondition`); `GenericGrid` has flat index splicing and bulk delete. |
| **Insert** | Primary button in footer, dropdown menu with pin options, or `Shift+Enter`. Inserts after active row. | Plus buttons on group/collection headers or root toolbar (`api.addLeaf(parentId)`). Always appends to end of children. | **Conceptual:** Create new item and immediately set it into editing mode. | In `GenericGrid`, position is linear index (`afterIndex`). In `TreeBuilder`, position is parent container ID + sibling index (`position`). |
| **Copy** | Footer button or `Ctrl+C` serializes selected rows to JSON with format `flexirule-generic-grid`. | No copy mechanism implemented. | **Yes:** Serialize payload, write to internal/OS clipboard, provide feedback. | `GenericGrid` copies flat list of row objects; `TreeBuilder` copies hierarchical AST subtree without parent link pointers. |
| **Duplicate** | Not implemented (users must copy and paste manually). | Not implemented. | **Yes:** In-place deep clone adjacent to original with freshly generated IDs; no OS clipboard mutation. | `GenericGrid` appends clone at `index + 1`; `TreeBuilder` inserts clone at identical parent container with new unique node ID (`createNodeId`). |

---

## 2. Source Inventory: Files, Components, Composables, and Functions

### 2.1 File Inventory

```
flexirule/public/js/flexirule/rule_builder/
├── composables/
│   ├── useKeyboardRegistry.js                   <-- Authoritative global keyboard shortcut engine
│   ├── useFloatingDropdown.js                   <-- Viewport-aware floating popover positioning
│   ├── useFocusTrap.js                          <-- Modal/dialog focus trapping
│   └── useClipboard.js                          <-- Canvas-level clipboard management
├── controls/
│   ├── GenericGrid.vue                          <-- Data & layout grid with toolbar and row controls
│   ├── generic_grid_model.mjs                   <-- Pure functions for search, pagination, shortcuts
│   └── inline_presentation_policy.mjs           <-- Shared presentation policy (hybrid/summary/form)
├── components/
│   ├── tree_builder/
│   │   ├── TreeBuilder.vue                      <-- Root TreeBuilder component
│   │   ├── TreeBuilderNode.vue                  <-- Recursive node dispatcher
│   │   ├── TreeBuilderGroup.vue                 <-- Logical group container
│   │   ├── TreeBuilderCollection.vue            <-- Collection scope container
│   │   ├── TreeBuilderLeaf.vue                  <-- Terminal condition/filter leaf
│   │   ├── useTreeBuilder.js                    <-- Reactive state and tree manipulation API
│   │   ├── tree_builder_commands.mjs            <-- Pure tree mutations (addLeaf, removeNode, etc.)
│   │   ├── tree_builder_utils.mjs               <-- Tree search, path finding, cloning, normalization
│   │   └── tree_builder_validation.mjs          <-- Structural validation
│   ├── condition_builder/
│   │   ├── CanonicalConditionBuilder.vue        <-- Consumer: rule condition editor
│   │   └── CanonicalConditionLeaf.vue           <-- Consumer: condition leaf editor
│   ├── rule_config/
│   │   ├── RuleConfigModal.vue                  <-- Host modal managing contexts and global shortcuts
│   │   ├── query_filters/
│   │   │   ├── QueryFilterTree.vue              <-- Consumer: TreeBuilder query filter tree
│   │   │   └── FilterLeaf.vue                   <-- Consumer: filter leaf editor
│   │   └── types/query_records/
│   │       ├── FetchRecordsConfig.vue           <-- Host: QueryFilterTree + OutputFieldsEditor
│   │       └── OutputFieldsEditor.vue           <-- Consumer: GenericGrid output fields editor
│   ├── App.vue                                  <-- Top-level app shell (canvas context)
│   ├── CommandPalette.vue                       <-- Command palette shortcut consumer
│   └── ShortcutsHelp.vue                        <-- Keyboard shortcuts cheat sheet
```

### 2.2 Key Functions and Hooks Trace

1. **`useKeyboardRegistry.js`:**
   - `registerShortcut(options)`: Registers key combination with modifiers, context, priority, callback.
   - `pushContext(context)`: Adds context string to global active context set.
   - `popContext(context)`: Removes context string from active context set.
   - `handleKeydown(e)`: Global `window.addEventListener("keydown")` listener with basic `isInput` filter.
2. **`useTreeBuilder.js`:**
   - `addLeaf(parentId, payload)`: Inserts leaf, records transient new node, sets `editingNodeId`.
   - `addGroup(parentId, operator)`: Inserts logical container.
   - `addCollection(parentId)`: Inserts collection container.
   - `removeNode(id)`: Removes node, cleans up selection/focus/editing IDs.
   - `moveNode(id, targetId, position)`: Reorders or moves node across parents.
   - `setEditing(id)` / `finishEditing(id)`: Manages edit vs. summary state.
   - `selectNode(id)` / `focusNode(id)`: Manages active node pointers.
3. **`generic_grid_model.mjs` & `GenericGrid.vue`:**
   - `matchesShortcut(event, shortcut)`: Parses string shortcut into key and modifier matches.
   - `requestRowAction(action, entry)`: Emits row action event (`edit`, `view`, `move-up`, `move-down`, `remove`).
   - `copySelectedRows()`: Serializes selected rows to `GRID_CLIPBOARD_FORMAT`.
   - `pasteRows()`: Deserializes rows, invokes `cloneRow`, splices into `sourceList`.
   - `getBulkEditAction(rows, editStateKey)`: Determines whether to switch selection to edit or view.

---

## 3. Existing Keyboard Shortcut Inventory and Conflict Analysis

### 3.1 Comprehensive Shortcut Audit

| Key Binding | Modifier | Location / Component | Registered Context | Priority | Action Description | Browser / Conflict Risk |
|---|---|---|---|---|---|---|
| `s` | `Ctrl` / `Cmd` | `App.vue` (Line 502) | `global` | 0 | Save Rule changes | Safe (Standard app save) |
| `s` | `Ctrl` / `Cmd` | `RuleConfigModal.vue` (Line 995) | `modal` | 11 | Save Action Modal | Safe (Overrides global when modal active) |
| `z` | `Ctrl` / `Cmd` | `App.vue` (Line 508) | `canvas` | 0 | Undo canvas change | Intercepts browser undo if canvas active |
| `y` | `Ctrl` / `Cmd` | `App.vue` (Line 517) | `canvas` | 0 | Redo canvas change | Safe (Windows Redo) |
| `z` | `Ctrl+Shift` | `App.vue` (Line 526) | `canvas` | 0 | Redo canvas change | Safe (Mac Redo) |
| `c` | `Ctrl` / `Cmd` | `App.vue` (Line 536) | `canvas` | 0 | Copy nodes (if no text selected) | Checks `window.getSelection().toString()` |
| `c` | `Ctrl` / `Cmd` | `GenericGrid.vue` (Line 598) | Component listener | Local | Copy selected grid rows | Intercepted in grid root if not input target |
| `v` | `Ctrl` / `Cmd` | `App.vue` (Line 547) | `canvas` | 0 | Paste nodes on canvas | Safe |
| `v` | `Ctrl` / `Cmd` | `GenericGrid.vue` (Line 605) | Component listener | Local | Paste grid rows | Intercepted in grid root if not input target |
| `?` | `Shift` | `App.vue` (Line 554) | `global` | 0 | Toggle Shortcuts Help dialog | Safe |
| `1` | `Alt` | `App.vue` (Line 560) | `global` | 0 | Focus Sidebar | Safe |
| `1` | `Alt` | `RuleConfigModal.vue` (Line 1064) | `modal` | 10 | Focus first config input | Conflict with `App.vue` if both active |
| `2` | `Alt` | `RuleConfigModal.vue` (Line 1073) | `modal` | 10 | Toggle Raw / Workspace View | Safe |
| `k` | `Ctrl` / `Cmd` | `App.vue` (Line 568) | `global` | 0 | Command Palette | Safe |
| `d` | `Ctrl` / `Cmd` | **Browser Default** | None | — | **Bookmark Page (Chrome/Firefox/Safari)** | **CRITICAL: NEVER USE Ctrl+D for Duplicate** |
| `d` | `Alt` | `App.vue` (Line 574) | `global` | 0 | Open Rule Debug Dialog | Safe |
| `l` | `Alt` | `App.vue` (Line 580) | `global` | 0 | Auto Layout Graph | Safe |
| `a` | `Alt+Shift` | `App.vue` (Line 586) | `global` | 0 | Toggle Active / Draft rule | Safe |
| `Escape` | None | `RuleConfigModal.vue` (Line 982) | `modal` | 10 | Close modal / Discard | Checks `.modal` dialogs |
| `Escape` | None | `ShortcutsHelp.vue` (Line 119) | `global` | 30 | Close Shortcuts Help | High priority |
| `Escape` | None | `CommandPalette.vue` (Line 198) | `command_palette`| 20 | Close Command Palette | High priority |
| `Escape` | None | `ValueResolverControl.vue` (Line 262) | `resolver_control`| 20 | Close Resolver popover | High priority |
| `ArrowUp` / `Down` | `Ctrl` / `Cmd` | `RuleConfigModal.vue` (Lines 1004, 1034)| `modal` | 10 | Prev / Next Action Node | Safe in modal |
| `ArrowLeft`/`Right`| `Ctrl` / `Cmd` | `RuleConfigModal.vue` (Lines 1019, 1049)| `modal` | 10 | Prev / Next Action Node | Safe in modal |
| `Ctrl+Shift+E` | `Ctrl+Shift` | `GenericGrid.vue` (Line 615) | Component listener | Local | Toggle Edit/Readable row mode | Safe (Avoids Chrome Alt+E menu collision) |
| `Shift+Enter` | `Shift` | `GenericGrid.vue` (Line 646) | Component listener | Local | Add row (Pinned primary action) | Safe; bypasses textareas and inputs |
| `Alt+Shift+F` | `Alt+Shift` | `OutputFieldsEditor.vue` (Line 282) | Grid action | Local | Add field | Safe |
| `Alt+Shift+G` | `Alt+Shift` | `OutputFieldsEditor.vue` (Line 287) | Grid action | Local | Add aggregate function | Safe |
| `Alt+Shift+L` | `Alt+Shift` | `OutputFieldsEditor.vue` (Line 293) | Grid action | Local | Add literal value | Safe |
| `Alt+Shift+C` | `Alt+Shift` | `OutputFieldsEditor.vue` (Line 300) | Grid action | Local | Add child table selection | Safe |

### 3.2 Conflict Analysis & Identified Risks

1. **Browser Collision with `Ctrl+D`:** Browsers globally bind `Ctrl+D` (Windows/Linux) and `Cmd+D` (macOS) to bookmarking the current webpage. Overriding this creates high user frustration and inconsistent browser behavior. We strictly reject `Ctrl+D` and adopt `Alt+Shift+ArrowDown` for Duplicate.
2. **`Delete` / `Backspace` Key Danger:** In text fields, `Delete` removes characters forwards, and `Backspace` removes characters backwards. If a global listener captures `Delete`, typing inside a condition's value input or an output field name will trigger row deletion. The keyboard system must enforce an impenetrable input protection boundary.
3. **Double Interception in Nested Components:**
   In `RuleConfigModal`, the context is set to `"modal"`. When `OutputFieldsEditor` or `QueryFilterTree` is rendered inside `RuleConfigModal`, a flat context check allows shortcuts from both the modal and the inner grid to collide. For example, pressing `Delete` or arrow keys must be scoped strictly to the focused sub-component.
4. **Clipboard Clashing:**
   If text inside an input field is highlighted, pressing `Ctrl+C` must copy that text to the OS clipboard and **never** trigger grid row copy or canvas node copy. `window.getSelection().toString()` must be checked, and `isInput` checks must take precedence.

---

## 4. Duplication and Architectural Weaknesses

1. **Delete Button Duplication & Visual Pollution:**
   - `TreeBuilderLeaf.vue`: Lines 42–49 and 96–103 render two separate `<button class="tree-leaf__action tree-leaf__remove">` blocks (one for summary mode, one for editor mode).
   - `TreeBuilderGroup.vue`: Lines 38–43 render `<button class="fxr-btn fxr-btn--icon fxr-btn--danger">`.
   - `TreeBuilderCollection.vue`: Lines 33–38 render identical remove buttons.
   - `GenericGrid.vue`: Lines 141–150 render `<button class="fxr-grid-icon-button is-danger">`.
   - This duplication means four separate components independently render destructive buttons without shared safety or confirmation hooks.
2. **Ad-hoc Shortcut Implementations:**
   - `GenericGrid.vue` contains ~130 lines of bespoke keydown logic in `handleKeydown()` (checking `matchesShortcut`, manually navigating rows, toggling editing). None of this uses `useKeyboardRegistry.js`.
   - `TreeBuilder.vue` has zero keyboard shortcuts; users cannot select, navigate, duplicate, or delete nodes using the keyboard.
3. **Flat, Non-Scoped Context in `useKeyboardRegistry.js`:**
   - Active contexts are stored in a flat set: `const activeContexts = ref(new Set(["global"]))`.
   - Any component calling `pushContext("foo")` activates `"foo"`. If both `modal` and `canvas` are active, both sets of shortcuts fire.
   - There is no hierarchical concept of "innermost active context takes precedence", nor is there an automatic stack-based deactivation when focus shifts.
4. **Incomplete Command Abstraction:**
   - In `GenericGrid`, actions are defined as ad-hoc strings (`"edit"`, `"view"`, `"move-up"`, `"move-down"`, `"remove"`, `"add-field"`).
   - In `TreeBuilder`, actions are tied directly to hardcoded template buttons calling `api.addLeaf()`, `api.addGroup()`, `api.removeNode()`.
   - Neither system provides an authoritative command definition describing the action's human label, icon, shortcut, enablement, visibility, and execution handler.

---

## 5. Proposed Centralized Command / Action Architecture

To achieve clean separation of concerns and avoid an oversized, unmaintainable composable, the system is structured into **three distinct, connected architectural layers**:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Centralized Command Registry (Domain-Agnostic Engine)    │
│    - Defines command schema, metadata, and contracts       │
│    - Exports standard definitions & factory functions      │
└──────────────────────────────┬──────────────────────────────┘
                               │
       ┌───────────────────────┴───────────────────────┐
       ▼                                               ▼
┌──────────────────────────────────┐ ┌──────────────────────────────────┐
│ 2a. useTreeBuilderActions        │ │ 2b. useGenericGridActions        │
│     - Resolves TreeBuilder nodes │ │     - Resolves Grid rows         │
│     - In-place subtree duplicate │ │     - Adjacent row duplicate     │
│     - Subtree removal & guards   │ │     - Bulk selection & clipboard │
│     - Leaf edit/view toggle      │ │     - Row edit/view toggle       │
└──────────────────┬───────────────┘ └──────────────────┬───────────────┘
                   │                                    │
                   └──────────────────┬─────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Presentation & Execution Surfaces                        │
│    - RowActionsMenu.vue (Contextual Ellipsis Menu)          │
│    - Inline Quick Actions (Edit toggle, reorder chevrons)   │
│    - useKeyboardRegistry.js (Hierarchical Scoped Shortcuts) │
└─────────────────────────────────────────────────────────────┘
```

### 5.1 Layer 1: Core Command Schema (`command_action_types.mjs`)

A command is a plain, immutable descriptor object:

```typescript
interface CommandDefinition<TContext = any> {
  id: string;                      // Unique command ID (e.g., "row.toggle-edit")
  label: string | (() => string);  // Localized human label
  icon?: string;                   // FontAwesome icon class (e.g., "fa fa-pencil")
  shortcut?: string;               // Display hint & key binding (e.g., "Ctrl+Shift+E")
  ariaKeyShortcuts?: string;       // ARIA shortcut hint
  group?: 'edit' | 'navigate' | 'clipboard' | 'destructive';

  // Dynamic visibility and enablement rules
  isVisible: (ctx: TContext) => boolean;
  isEnabled: (ctx: TContext) => boolean;

  // Execution pipeline
  execute: (ctx: TContext) => Promise<boolean | void> | boolean | void;

  // Guard and safety policies
  guard?: (ctx: TContext) => Promise<boolean> | boolean;
  requiresConfirmation?: (ctx: TContext) => boolean;
  confirmationMessage?: (ctx: TContext) => string;
}
```

### 5.2 Layer 2: Domain Action Composables

#### 5.2.1 `useTreeBuilderActions.js`
Adapts the generic command registry for `TreeBuilder`:
- **Context:** `{ treeApi, node, parent, index, isRoot, readOnly }`
- **Commands:**
  1. `tree.toggle-edit`: Invokes `treeApi.setEditing(node.id)` or `treeApi.finishEditing(node.id)`. Visible only for leaves with a summary slot.
  2. `tree.select`: Invokes `treeApi.selectNode(node.id)`.
  3. `tree.insert-leaf`: Invokes `treeApi.addLeaf(parent.id, null, index + 1)`.
  4. `tree.insert-child`: For containers (groups/collections), adds child leaf inside.
  5. `tree.duplicate`: Clones the node via `cloneTree(node)`, regenerates IDs for all subnodes via `regenerateNodeIds(clone)`, and inserts as sibling at `index + 1`.
  6. `tree.copy`: Serializes subtree to `TREE_CLIPBOARD_FORMAT`, writes to clipboard, emits feedback.
  7. `tree.remove`: Calls `confirmNodeRemoval` / `beforeRemove` guard. If approved, executes `treeApi.removeNode(node.id)` and restores focus to adjacent sibling.

#### 5.2.2 `useGenericGridActions.js`
Adapts the generic command registry for `GenericGrid`:
- **Context:** `{ gridApi, row, index, key, selectedRows, readOnly }`
- **Commands:**
  1. `grid.toggle-edit`: Invokes `requestRowAction(isEditing ? 'view' : 'edit', entry)`.
  2. `grid.select`: Toggles selection of `row.key` in `selectedKeys`.
  3. `grid.insert-row`: Invokes `requestPrimaryAction(index)`.
  4. `grid.duplicate`: Clones `row` using `props.cloneRow(row, index + 1)`, assigns new unique `id`, and splices into `sourceRows` at `index + 1`. Does not modify OS clipboard.
  5. `grid.copy`: Invokes `copySelectedRows()` with `GRID_CLIPBOARD_FORMAT`.
  6. `grid.remove`: Invokes `requestRowAction('remove', entry)`. If bulk selected, prompts bulk delete confirmation.

---

## 6. Proposed Centralized Keyboard Shortcut Architecture

### 6.1 Hierarchical Scoped Context Engine (`useKeyboardRegistry.js`)

Instead of a flat `Set(["global", "modal", "canvas"])`, `useKeyboardRegistry.js` is upgraded with an active **context stack and scope hierarchy**:

```javascript
// Internal state in useKeyboardRegistry.js
const contextStack = ref(["global"]);
const activeContexts = computed(() => new Set(contextStack.value));
```

#### Context Hierarchy & Scope Lifecycle:
1. **Root:** Always contains `["global"]`.
2. **Modal Push:** When `RuleConfigModal` mounts, it calls `pushContext("modal")` → Stack: `["global", "modal"]`.
3. **Component Focus:** When focus enters `GenericGrid` (or `TreeBuilder`), the component pushes its unique context ID: `pushContext("grid:" + instanceId)` → Stack: `["global", "modal", "grid:1"]`.
4. **Scope Resolution:** During keydown, matching shortcuts are filtered such that the **innermost (top-of-stack)** context takes absolute priority. If the top context handles the key, propagation stops. If not handled, it bubbles down to `"modal"`, then `"global"`.
5. **Component Blur / Unmount:** When focus leaves the component container (checked via `event.relatedTarget`), it pops its context: `popContext("grid:" + instanceId)`.

### 6.2 Strict Input & Editor Protection Boundary

To ensure shortcuts never corrupt user typing in text fields, Monaco, or Tiptap:

```javascript
export function isInputOrEditorTarget(target) {
    if (!target || !(target instanceof Element)) return false;

    // 1. Native HTML input controls
    const tagName = target.tagName;
    if (["INPUT", "TEXTAREA", "SELECT"].includes(tagName)) return true;

    // 2. Rich text & code editors
    if (target.isContentEditable) return true;
    if (target.closest(".monaco-editor, .CodeMirror, .ace_editor, .ProseMirror, [contenteditable='true']")) return true;

    // 3. Frappe custom controls and dropdown popovers
    if (target.closest(".combobox-input-group, .flex-value-control-input, [role='combobox'], [role='textbox']")) return true;

    return false;
}
```

#### Safe Dispatch Policy:
- When `isInputOrEditorTarget(e.target)` is `true`:
  - **Single character keys** (e.g. `Space`, `Delete`, `Backspace`, `a-z`) are **strictly ignored** by grid/tree shortcuts, allowing native cursor and text modification.
  - **Navigation keys** (`ArrowUp`, `ArrowDown`, `Home`, `End`) are **strictly ignored**, allowing native text caret movement within inputs.
  - **Allowed exceptions:** Explicit global accelerator combinations with `Ctrl/Cmd` or `Alt` that specify `allowInInputs: true` (e.g. `Ctrl+S` to save, `Ctrl+Shift+E` to toggle row mode).

### 6.3 Authoritative Keyboard Shortcut Mappings

| Action | Proposed Shortcut | TreeBuilder Context | GenericGrid Context | Context Rule & Precondition |
|---|---|---|---|---|
| **Toggle Edit / Summary** | `Ctrl+Shift+E` | Active leaf is focused/selected and has summary slot | Active row is focused/selected | Allowed in input if child of active row/leaf |
| **Insert Row / Leaf** | `Shift+Enter` | Active container or leaf focused; inserts sibling leaf | Active row focused; inserts row below | Blocked inside native `<textarea>` or multi-line editors |
| **Select Item** | `Space` | Active leaf or node index focused | Active row index button focused | Blocked when typing in input controls |
| **Delete / Remove** | `Delete` | Active node selected/focused | Active row(s) selected/focused | **Strictly blocked** if `isInputOrEditorTarget` is true |
| **Copy** | `Ctrl+C` | Active node selected | Active row(s) selected | **Strictly ignored** if `window.getSelection().toString()` is non-empty |
| **Duplicate** | `Alt+Shift+ArrowDown` | Active node selected/focused | Active row selected/focused | Clones adjacent item in-place; no clipboard mutation |
| **Open More Options (⋮)**| `Shift+F10` or `ContextMenu` | Active node ellipsis button | Active row ellipsis button | Opens `RowActionsMenu` floating dropdown |
| **Move Focus Up/Down** | `ArrowUp` / `ArrowDown` | Navigates between tree nodes | Navigates between grid rows | Blocked when input has focus |

---

## 7. Contextual Options Menu (⋮) Design and Component Specification

### 7.1 Architecture of `RowActionsMenu.vue`

Instead of ad-hoc dropdown implementations, we introduce a unified, headless-accessible component:
`flexirule/public/js/flexirule/rule_builder/components/common/RowActionsMenu.vue`

```
┌─────────────────────────────────────────────────────────────┐
│ [Row / Leaf Toolbar]                                        │
│  [1]   Summary or Content               [✎] [↑] [↓]  [ ⋮ ]  │
└─────────────────────────────────────────────────────────┼───┘
                                                          │ (click / Shift+F10)
                                                          ▼
                                            ┌─────────────────────────┐
                                            │ Edit Row   Ctrl+Shift+E │
                                            │ Select            Space │
                                            │ ─────────────────────── │
                                            │ Insert Below   Shift+↵  │
                                            │ Duplicate   Alt+Shift+↓ │
                                            │ Copy             Ctrl+C │
                                            │ ─────────────────────── │
                                            │ Remove           Delete │ (Red text)
                                            └─────────────────────────┘
```

### 7.2 Contextual Visibility Rules

Actions displayed in the menu are dynamically evaluated using each command's `isVisible(context)` and `isEnabled(context)`:

1. **For `TreeBuilderLeaf`:**
   - **Edit / Summary:** Visible only when `hasSummarySlot` is true and presentation mode allows toggling.
   - **Select:** Always visible; sets `selectedNodeId`.
   - **Insert Leaf:** Inserts sibling leaf below.
   - **Duplicate:** Clones leaf in-place with new ephemeral ID.
   - **Copy:** Copies leaf subtree to clipboard.
   - **Remove:** Always visible unless `readOnly`. Displays shortcut hint `Delete`.
2. **For `TreeBuilderGroup` and `TreeBuilderCollection`:**
   - **Add Child Condition:** Adds leaf inside container.
   - **Add Child Group:** Adds nested group inside (if `allowGroups` is true and `maxDepth` not reached).
   - **Add Collection:** Adds child collection (if `allowCollections` is true).
   - **Duplicate:** Clones entire group/collection hierarchy with deep ID regeneration.
   - **Remove:** Removes container; prompts confirmation if containing multiple conditions.
3. **For `GenericGrid` Rows:**
   - **Edit / View:** Toggles readable summary vs. field editor.
   - **Select:** Toggles row selection checkbox.
   - **Insert Row:** Inserts new row below the current row.
   - **Duplicate:** Clones current row at `index + 1`.
   - **Copy:** Copies row (or all selected rows) to clipboard.
   - **Remove:** Deletes row. If multiple rows selected, labels action "Delete Selected (N)".

### 7.3 Accessibility and Focus Restoration

`RowActionsMenu.vue` leverages `useFloatingDropdown.js` (`flexirule/public/js/flexirule/rule_builder/composables/useFloatingDropdown.js`) to provide robust accessibility:
- **ARIA Attributes:**
  - Ellipsis button: `aria-haspopup="menu"`, `:aria-expanded="String(isOpen)"`, `:aria-label="__('More options for row {0}', [index + 1])"`.
  - Dropdown container: `role="menu"`, `tabindex="-1"`, `@keydown="handleMenuKeydown"`.
  - Action items: `role="menuitem"`, `:aria-keyshortcuts="item.shortcut"`, `:disabled="!item.isEnabled"`.
- **Keyboard Navigation within Menu:**
  - `ArrowDown` / `ArrowUp`: Cycles focus through menu items with wraparound.
  - `Home` / `End`: Jumps to first / last active menu item.
  - `Enter` / `Space`: Executes command and closes menu.
  - `Escape`: Closes menu and immediately returns focus to the trigger ellipsis button.
- **Focus Restoration:**
  - When an action is invoked from the menu, the trigger button or newly active row/leaf is programmatically focused via `nextTick()`, preventing focus loss to `<body>`.

### 7.4 Mobile and Responsive Touch Behavior

- **Touch Target Size:** The ellipsis button maintains a minimum hit area of 36×36px on mobile viewports (`max-width: 768px`).
- **Menu Positioning:** Uses `useFloatingDropdown.js` automatic flipping: if the row is near the bottom of the viewport, the menu opens upwards (`openUp = true`).
- **Responsive Stacking:** On viewports `< 600px`, the ellipsis menu stays pinned to the top-right of the row card, while long field names and summaries wrap cleanly beneath.

---

## 8. TreeBuilder vs. GenericGrid: Shared and Specialized Responsibilities

| Dimension | Shared Interactions (Centralized in Command Registry) | Specialized `TreeBuilder` Responsibility | Specialized `GenericGrid` Responsibility |
|---|---|---|---|
| **Data Hierarchy** | Action registry interfaces; unified menu UX; shortcut listeners; clipboard format envelope. | **Hierarchical Tree AST:** Operates on recursive parent-child nodes (`children: []`), tree depth, scope resolution, and operators (`and`/`or`). | **Tabular / List:** Operates on flat array `sourceRows`, pagination (`currentPage`, `pageSize`), column widths, and bulk selection. |
| **Editing Lifecycle** | `inline_presentation_policy.mjs`: `hybrid`, `summary`, and `form` modes; validation gating for summary return. | Centralized editing node ID in `useTreeBuilder.js` (`editingNodeId`, `transientNewNodes`). Single active leaf editor at a time. | Per-row editing state flag (`row[editStateKey] = true/false`). Supports multiple simultaneously editing rows. |
| **Insertion** | Commands create new item, activate editor mode, and reveal in viewport. | Inserts into container (`parent.id`) at sibling index or inside child list. Generates typed AST node (`createLeaf`, `createCollection`). | Inserts into linear array at `afterIndex`. Evaluates default primary action preference (e.g. `add-field`, `add-function`). |
| **Duplication** | Clones data in-place without OS clipboard mutation; regenerates IDs. | Deep subtree cloning with recursive ID replacement (`regenerateNodeIds`). Preserves operator and condition configuration. | Flat row cloning via `props.cloneRow()`. Resolves column keys, clears `isEditing`, generates `pasted-...` ID. |
| **Deletion & Safety** | Pipeline: Target resolution → Permission check → Guard hook → Confirmation → Delete → Focus restore. | **AST Protection:** Structural validation via `beforeRemove`. Checks `isSoleCondition` on Entry Actions to block unintended rule triggers. | **Bulk Protection:** Bulk delete confirmation dialog when `selectedRows.length > 1`. Clears active keys from `selectedKeys`. |
| **Clipboard** | JSON clipboard serialization; browser clipboard + local fallback; toast notifications. | Formats payload as `{ format: "flexirule-condition-tree", version: 1, node: AST }`. | Formats payload as `{ format: "flexirule-generic-grid", version: 1, rows: [] }`. |

---

## 9. Deletion Safety Pipeline and Safeguard Migration

### 9.1 Unified Deletion Pipeline Execution Flow

All deletion invocations—whether triggered by the ellipsis menu, inline trash button (during transition), bulk delete button, or the `Delete` keyboard shortcut—must traverse the exact same execution pipeline:

```
[User triggers Delete via Menu / Keyboard / Button]
                         │
                         ▼
             [1. Resolve Target Item]
             (Active node ID or selected grid rows)
                         │
                         ▼
             [2. Check Read-Only & Permissions]
             (If read-only, abort silently)
                         │
                         ▼
             [3. Execute Consumer Safety Guards]
             (e.g., TreeBuilder props.beforeRemove(nodeId, root))
                         │
               ┌─────────┴─────────┐
          (Allowed)             (Blocked) ──► Abort operation
               │
               ▼
   [4. Evaluate Confirmation Policy]
   - Is it the sole condition in Entry Node? ──► Show warning confirm dialog
   - Is it a container with multiple children? ──► Show group deletion confirm
   - Is it a bulk grid deletion (N > 1)? ──► Show bulk deletion confirm
   - Is it a routine single leaf/row deletion? ──► Proceed directly (frictionless)
               │
         (User Confirms)
               │
               ▼
         [5. Execute Mutation]
         (treeApi.removeNode(id) or rows.splice(index, 1))
                         │
                         ▼
       [6. Post-Deletion Focus & Selection Recovery]
       - Focus adjacent sibling (previous if exists, else next)
       - If container now empty, focus parent container
       - Update selection sets and emit change events
```

### 9.2 Preserving Critical Invariants (`CanonicalConditionBuilder`)

In `CanonicalConditionBuilder.vue` (Lines 159–185), removing the sole condition in an entry action turns a filtered rule into an unconditional trigger. This protection is preserved verbatim:

```javascript
// Centralized guard function used by tree.remove command
export function checkConditionRemovalSafety(nodeId, root, isEntryNode) {
    const remaining = countRemainingLeaves(root, nodeId);
    if (remaining === 0 && isEntryNode) {
        return {
            requiresConfirm: true,
            message: __(
                "WARNING: Removing the only Entry Condition will remove all trigger filtering, " +
                "causing the rule to run unconditionally for all documents! Are you sure you want to delete it?"
            ),
        };
    }
    return { requiresConfirm: false };
}
```

By embedding this in the command's `guard` and `requiresConfirmation` hooks, **the `Delete` keyboard shortcut can never bypass the entry condition safety check.**

---

## 10. Migration Strategy for Existing Row/Leaf Delete Buttons

To ensure zero downtime, uninterrupted developer workflow, and zero regressions for existing consumers, we implement a backward-compatible migration plan:

### 10.1 Phase-by-Phase Deprecation of Inline Delete Buttons

1. **Step 1: Introduction of `RowActionsMenu.vue`**
   - Create `RowActionsMenu.vue` and integrate into `TreeBuilderLeaf.vue` and `GenericGrid.vue`.
   - The ellipsis menu provides Edit, Duplicate, Copy, and Delete.
2. **Step 2: Configuration Flag for Graceful Transition**
   - Introduce prop `:showEllipsisMenu="{ type: Boolean, default: true }"` and `:showInlineDelete="{ type: Boolean, default: false }"`.
   - In `TreeBuilderLeaf.vue`:
     - Keep inline edit toggle button (`fa-pencil` / `fa-check`).
     - Remove inline delete button (`fa-trash`), directing deletion exclusively to the ellipsis menu and the `Delete` shortcut.
   - In `GenericGrid.vue`:
     - Keep inline edit toggle button and up/down reorder chevrons.
     - Replace `<button class="fxr-grid-icon-button is-danger">` with `<RowActionsMenu>`.
3. **Step 3: Consumer Validation**
   - Verify `CanonicalConditionBuilder.vue`, `QueryFilterTree.vue`, `OutputFieldsEditor.vue`, and `FetchRecordsConfig.vue`.
   - Confirm that all existing tests in `flexirule/ruleflow/tests/` and frontend test suites pass without regression.

---

## 11. Prioritized Implementation Phases and Suggested PR Breakdown

We recommend breaking the implementation into **five small, independently reviewable PRs**:

```
┌────────────────────────────────────────────────────────────────────────┐
│ PR 1: Core Action Types & Upgraded Keyboard Registry Scope Engine     │
│       - command_action_types.mjs                                       │
│       - useKeyboardRegistry.js (hierarchical stack + input boundaries) │
│       - Unit tests for shortcut matching and context stacking          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PR 2: RowActionsMenu.vue Component & Styling                           │
│       - RowActionsMenu.vue (floating dropdown + ARIA menu pattern)     │
│       - Shortcuts badge styling and focus restoration                  │
│       - Responsive / touch hit targets                                 │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PR 3: GenericGrid Integration & Actions Unification                    │
│       - useGenericGridActions.js composable                            │
│       - Ellipsis menu integration into GenericGrid row toolbar         │
│       - Duplicate row implementation via cloneRow                      │
│       - Centralized Delete pipeline with bulk delete protection        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PR 4: TreeBuilder Integration & Actions Unification                    │
│       - useTreeBuilderActions.js composable                            │
│       - Ellipsis menu integration into TreeBuilderLeaf and Containers   │
│       - In-place subtree duplication with ID regeneration              │
│       - Condition safety guard integration (Entry action safeguard)    │
│       - Removal of individual leaf delete buttons                      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PR 5: End-to-End Consumer Verification & Documentation                 │
│       - Update ShortcutsHelp.vue cheat sheet                           │
│       - Verify CanonicalConditionBuilder & OutputFieldsEditor          │
│       - Playwright / Cypress UI interaction test suite                 │
└────────────────────────────────────────────────────────────────────────┘
```

### Detailed PR Descriptions:

- **PR 1: Core Action Infrastructure & Hierarchical Keyboard Registry**
  - Files touched:
    - `flexirule/public/js/flexirule/rule_builder/composables/command_action_types.mjs` (New)
    - `flexirule/public/js/flexirule/rule_builder/composables/useKeyboardRegistry.js` (Refactor)
    - `flexirule/ruleflow/tests/test_keyboard_registry.test.js` (New standalone Node unit test)
  - Deliverable: Context stacking, strict `isInputOrEditorTarget` boundary, shortcut registration and execution tests.

- **PR 2: Reusable Contextual Ellipsis Menu (`RowActionsMenu.vue`)**
  - Files touched:
    - `flexirule/public/js/flexirule/rule_builder/components/common/RowActionsMenu.vue` (New)
  - Deliverable: WAI-ARIA compliant menu, floating positioning with `useFloatingDropdown.js`, keyboard traversal (`ArrowUp/Down`, `Escape`, `Enter`), shortcut hints badge rendering.

- **PR 3: GenericGrid Unified Actions & Keyboard Shortcuts**
  - Files touched:
    - `flexirule/public/js/flexirule/rule_builder/controls/useGenericGridActions.js` (New)
    - `flexirule/public/js/flexirule/rule_builder/controls/GenericGrid.vue` (Modified)
    - `flexirule/public/js/flexirule/rule_builder/controls/generic_grid_model.mjs` (Modified)
  - Deliverable: Row toolbar ellipsis menu replaces delete button; row duplication support; contextual shortcuts (`Ctrl+Shift+E`, `Shift+Enter`, `Alt+Shift+ArrowDown`, `Delete`).

- **PR 4: TreeBuilder Unified Actions & Safeguarded Deletion**
  - Files touched:
    - `flexirule/public/js/flexirule/rule_builder/components/tree_builder/useTreeBuilderActions.js` (New)
    - `flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilderLeaf.vue` (Modified)
    - `flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilderGroup.vue` (Modified)
    - `flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilderCollection.vue` (Modified)
    - `flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilderNode.vue` (Modified)
  - Deliverable: Leaf and container ellipsis menu; in-place duplicate action; deletion pipeline enforcing `beforeRemove` and `confirmNodeRemoval`.

- **PR 5: Consumer Integration, Shortcuts Help, and Verification**
  - Files touched:
    - `flexirule/public/js/flexirule/rule_builder/components/ShortcutsHelp.vue` (Updated)
    - `flexirule/public/js/flexirule/rule_builder/components/condition_builder/CanonicalConditionBuilder.vue` (Verified)
    - `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/query_records/OutputFieldsEditor.vue` (Verified)
  - Deliverable: Updated shortcuts cheat sheet, end-to-end regression tests.

---

## 12. Testing Strategy, Edge Cases, and Acceptance Criteria

### 12.1 Testing Strategy

1. **Unit Tests (Node Native Runner):**
   - Execute via `node --test $(find flexirule -name "*.test.js")`.
   - Test suite `useKeyboardRegistry.test.js`:
     - Test context push/pop stacking order.
     - Test that child context shadows parent context shortcuts for identical keys.
     - Test that input targets (`<input>`, `<textarea>`, Monaco, Tiptap) block single-key and navigation shortcuts.
     - Test that `Ctrl+Shift+E` fires even when focus is inside a row control.
   - Test suite `useTreeBuilderActions.test.js` & `useGenericGridActions.test.js`:
     - Test duplication produces detached deep clone with newly generated IDs.
     - Test deletion invokes guard before removing node.
     - Test clipboard serialization matches `GRID_CLIPBOARD_FORMAT` and `TREE_CLIPBOARD_FORMAT`.
2. **Component Integration Tests:**
   - Verify mounting of `GenericGrid` with `OutputFieldsEditor` rows:
     - Click ellipsis menu → Verify items render with correct shortcut badges.
     - Press `Alt+Shift+ArrowDown` on row → Verify row is duplicated at `index + 1`.
     - Press `Delete` on selected row → Verify row is deleted.
     - Type in output field name input and press `Delete` → Verify text character is deleted, **not the row**.
3. **E2E / Cypress Scenarios:**
   - Test entry condition safety in `CanonicalConditionBuilder`:
     - With a single condition, press `Delete` or select "Remove" from menu.
     - Confirm modal alert appears warning of unconditional rule execution.
     - Reject confirmation → Condition remains intact.

### 12.2 Critical Edge Cases Matrix

| Edge Case Scenario | Potential Failure Mode | Architectural Prevention Mechanism |
|---|---|---|
| **User typing inside a condition value input presses `Delete`** | The condition leaf gets deleted instead of the character. | `isInputOrEditorTarget` check immediately returns early, preventing the shortcut from triggering. |
| **User highlights text inside a string input and presses `Ctrl+C`** | The entire grid row is copied, overwriting the user's OS clipboard text. | Check `window.getSelection().toString().length > 0`; if true, abort command and let native copy proceed. |
| **User presses `Alt+Shift+ArrowDown` with no row selected** | Crash due to undefined row pointer or duplicate inserted at end. | `isEnabled(ctx)` checks that `activeRowIndex` or `selectedNodeId` is valid before dispatching. |
| **Duplicating a complex collection with nested conditions** | Child conditions share identical ephemeral IDs, corrupting AST on save. | `regenerateNodeIds(clone)` recursively visits every child node and assigns fresh IDs via `createNodeId()`. |
| **Rapid double-click on menu action** | Duplicate actions dispatched twice (e.g., two rows created). | Debounced command execution guard with in-flight lock flag. |
| **Row deletion when menu is open** | Memory leak or focus lost to document root. | Menu automatically closes before executing deletion; focus is shifted to adjacent sibling row. |
| **Screen reader accessibility** | Ellipsis button unlabelled; popup unannounced. | Explicit `aria-label`, `aria-haspopup="menu"`, and `role="menu"` compliant with WAI-ARIA standards. |

### 12.3 Acceptance Criteria

1. **Menu Consistency:**
   - Individual delete buttons on every row and leaf are completely removed and replaced by the contextual ellipsis (`⋮`) menu button.
   - Inline edit/readable toggle button and reorder controls remain easily accessible inline.
   - Ellipsis menu renders clean, accessible items with shortcut badges on the right.
2. **Unified Implementation:**
   - Clicking an action in the ellipsis menu and pressing its assigned keyboard shortcut invokes the exact same underlying command function.
   - Zero duplicated business logic across buttons, menus, and keyboard handlers.
3. **Ergonomic Keyboard Shortcuts:**
   - `Ctrl+Shift+E`: Toggles edit/summary mode.
   - `Shift+Enter`: Inserts row/leaf.
   - `Space`: Selects focused item.
   - `Delete`: Removes selected item (strictly protected against input interference).
   - `Alt+Shift+ArrowDown`: Duplicates item in-place without clipboard pollution.
   - `Ctrl+C`: Copies selected item(s).
   - `Shift+F10` / `ContextMenu`: Opens contextual menu.
4. **Safety & Safeguards:**
   - Structural safeguards (`isSoleCondition` in `CanonicalConditionBuilder`) cannot be bypassed by keyboard shortcuts or menu actions.
   - Bulk delete prompts explicit confirmation.
5. **No Regression:**
   - All existing tests pass.
   - Application code remains unchanged during this architecture phase.
