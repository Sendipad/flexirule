# GridBuilder — Complete Implementation Plan

**Status:** Plan only; no component implementation has started.  
**Repository:** Sendipad/flexirule  
**Implementation branch:** feat/grid-builder-generic-20261012  
**Base:** develop at 1c32acc451ff13950c3d5125a114cf3b59dfa01b  
**Design reference:** Accepted “GridBuilder – Sketchup” concept from this conversation.

## 1. Goal

Implement GridBuilder as a reusable Vue 3 composition primitive for ordered collections of rows. It should provide the structural and interaction features that many FlexiRule action-configuration screens need, while leaving the meaning and detailed rendering of each row to the consuming action type.

The core should own row-collection interactions and a stable contract: selection, immutable row operations, ordering, row actions, keyboard/focus coordination, clipboard envelopes, drag-and-drop boundaries, and accessible structure. Consumers own domain fields, validation, row contents, nested-collection semantics, and action-specific bulk operations.

GridBuilder should follow the compositional design demonstrated by Tree Builder: a thin Vue component, a composable for reactive UI state, pure helpers/commands for collection operations, optional row rendering through a slot or a supplied Vue component, and a documented contract with focused tests.

## 2. Repository findings and architectural constraints

Before implementation, the following repository facts are relevant:

- The new branch was created from develop. Keep that base unless explicitly directed otherwise.
- The generic Tree Builder currently exists on feat/fetch-records-mode under flexirule/public/js/flexirule/rule_builder/components/tree_builder/. Its key pattern is a controlled component, a composable, pure utility/command modules, a README, and focused tests. Use it as a design reference, not as a runtime dependency: its source is not currently present on this branch’s develop base.
- develop already includes controls/FlexiGrid.vue. That component is Frappe DocField/ControlFactory-oriented: it depends on df, engine, field normalization, dynamic options, and validation. GridBuilder must not become a second implementation of those responsibilities. It should be generic and compositional, with consumers free to use FlexiGrid or ControlFactory inside a row if appropriate.
- controls/InlineTableControl.vue is another domain/control-driven repeatable-table implementation. Do not couple GridBuilder to its schema.
- The existing useClipboard.js and utils/clipboard.js establish native clipboard plus fallback patterns, but the GridBuilder payload must have its own unique type and storage key. It must not use or overwrite the rule-flow node clipboard envelope.
- flexirule/public/css/design-tokens.css provides FlexiRule surface, border, text, accent, spacing, radius, focus, and theme tokens. flexi_table.css and FlexiGrid.vue provide visual references, but GridBuilder should use its own class namespace and avoid changing existing controls.
- package.json currently has a placeholder npm test script. Do not treat npm test as proof of coverage. Follow the repository’s actual lint, formatting, build, unit-test, and Frappe validation workflows.

## 3. Scope

### Required for the first complete implementation

1. Optional title/header region and optional custom column-header row.
2. Controlled rows using the standard Vue v-model / modelValue contract.
3. Custom row rendering via a named row slot or a supplied row component.
4. Optional select-all and per-row selection, including a correct indeterminate state.
5. Copy and paste selected rows, including between tabs of the same origin for the same declared row-data type.
6. Optional bulk-action toolbar/slot whose actions are supplied by the consumer.
7. Optional per-row move-up, move-down, remove, and explicit drag handle controls.
8. Drag-and-drop row reordering with validated same-grid drop targets.
9. Keyboard navigation across rows and cells/controls, quick row creation, and focus restoration after structural operations.
10. Optional nested GridBuilder instances for collection/scope data inside a parent row.
11. Responsive and theme-aware FlexiRule presentation, including empty, selected, active-focus, drag-over, disabled, read-only, and action states.
12. Accessible labels, keyboard-operable alternatives to drag actions, useful announcements, and predictable native input behavior.
13. Documentation, pure logic tests, component interaction tests, and a manual browser verification checklist.

### Provide extension points, but do not hard-code domain policy

The accepted sketch also illustrates sortable column headings, pagination, and domain-specific bulk actions. GridBuilder should provide header, column-header, toolbar, bulk-action, and footer slots plus useful row/count context so consumers can compose these features. Generic sorting and pagination should not mutate or reinterpret the canonical order in the first implementation: sorting and paging can conflict with manual reorder semantics and require explicit consumer/domain policies. They can be added later behind a separate, clearly defined contract if a real use case requires them.

### Explicit non-goals

- No action-type-specific field schema, resolver semantics, Frappe DocField validation, or business rules in the generic builder.
- No coupling to TreeBuilder internals, Pinia stores, VueFlow, or a particular action configuration.
- No persisted selection, focus, hover, drag, clipboard UI state, or generated internal row IDs in the consumer’s row payload.
- No bypass of browser clipboard permission/security rules.
- No custom global keyboard listener that intercepts unrelated inputs or browser-reserved shortcuts.
- No automatic deletion/confirmation or domain mutation rules beyond the explicit operation requested by the consumer.

## 4. Proposed file layout

Create a sibling directory:

    flexirule/public/js/flexirule/rule_builder/components/grid_builder/
      GridBuilder.vue
      GridBuilderRow.vue
      useGridBuilder.js
      grid_builder_types.js
      grid_builder_utils.js
      grid_builder_commands.js
      grid_builder_clipboard.js
      grid_builder.test.js
      README.md

Keep the first version small. GridBuilder.vue owns the public API and high-level structure. GridBuilderRow.vue provides the default structural row renderer and action/focus affordances; consumers may supply their own row component. useGridBuilder.js coordinates controlled-data synchronization, selection, focus, and UI operations. Pure helpers and commands remain independent of Vue wherever practical. Clipboard serialization/validation is isolated so it can be tested without mounting Vue.

Only introduce separate toolbar, header, or keyboard modules if implementation complexity warrants it; do not create one-file-per-trivial-helper. Keep style scoped to the component where practical, with the grid-builder class namespace. Do not modify FlexiGrid.vue, InlineTableControl.vue, TreeBuilder, or global design tokens just to make the new component work.

## 5. Public API proposal

Finalize naming in code review before implementation, but keep the public surface small and compositional.

### Core props

| Prop | Purpose |
| --- | --- |
| modelValue: Array | Canonical controlled row collection; default empty array. |
| getRowKey(row, index) | Optional row-key resolver. Prefer a stable consumer key; recognize common id/name/key fields as a convenience. |
| rowFactory() | Produces a fresh row for Add Row and quick-add operations. Never reuse one mutable object. |
| rowComponent | Optional Vue component used to render each row’s domain content. |
| readOnly | Disables mutation, selection actions that imply mutation, row add/remove/move, and paste. |
| showHeader | Toggles the optional top/header region. |
| showColumnHeader | Toggles a consumer-provided column-header slot if the chosen structure uses a distinct column-heading row. |
| selectable | Enables per-row selection. |
| showSelectAll | Enables the select-all control when selection is enabled. |
| showCopyPaste | Enables copy/paste UI controls. |
| clipboardType | Required stable identifier when copy/paste is enabled; only matching types may be pasted. |
| showBulkActions | Enables the bulk-action region when supplied by the consumer. |
| showMoveButtons | Enables move-up and move-down controls. |
| showRemoveButton | Enables per-row removal controls. |
| draggableRows | Enables pointer drag-and-drop ordering; default off. |
| allowAddRows | Enables Add Row and quick-add keyboard action. |
| keyboardNavigation | Enables grid-scoped keyboard/focus navigation; default on where row markup provides the required cell markers. |
| ariaLabel | Accessible name for the collection when no visible heading provides one. |

Optional refinements such as per-row capability callbacks (canSelectRow, canMoveRow, canRemoveRow), paste insertion policy, or configurable shortcut keys should be added only where they simplify real consumer use. Avoid exposing many overlapping booleans that can be represented more clearly through slots.

The builder should not silently invent a persisted field in a row just to track identity. Keys must be unique and stable while a row is selected, edited, reordered, or pasted. If a row does not expose a usable intrinsic key, maintain a private, non-serialized key sidecar; document getRowKey as the preferred production contract and warn in development when supplied rows have duplicate or unstable identities. Do not use array indices as persistent identity for selection or drag state.

### Slots

- header: optional title, description, and/or top toolbar content.
- column-header: consumer-provided column headings aligned with the custom row layout.
- row: default customization point receiving the row context. It takes precedence as the content renderer when provided alongside the default row component.
- empty: custom empty-state content.
- bulk-actions: receives selected rows/keys and selection helpers so the action menu remains consumer-owned.
- row-actions: optional custom row actions in addition to or instead of built-in move/remove actions, depending on final API.
- footer: pagination, counts, or other consumer-owned footer content.

A row slot should receive at least row, index, rowKey, selected, readOnly, updateRow, moveUp, moveDown, remove, and focus helpers where relevant. A supplied rowComponent receives the same documented row context as props and is required to follow the documented focusable-cell/data-attribute contract. Do not expose internal reactive Sets or mutate them from consumers; expose controlled helper methods and read-only selected values.

### Events

- update:modelValue — emit the next row array as the single source of truth for row collection mutations.
- change — summarize the operation, affected keys, and old/new indices for consumers that need to react to changes.
- selection-change — provide selected keys and selected row values.
- row-added, row-removed, rows-reordered, copy, paste, and bulk-action — add only where consumer behavior is materially different from the main model update; document payloads and avoid duplicate, contradictory event sources.

All updates must be deterministic. Add, remove, move, paste, and updateRow should produce a new array and emit one canonical update per completed operation. UI state remains internal and must not be serialized into modelValue.

## 6. State, identity, and command semantics

Use modelValue as the canonical row data. Derive displayed rows from props rather than maintaining an independently mutable localRows copy that can drift from the parent. The composable may hold transient state: selected key set, active row/cell, drag source/target, and pending focus restoration.

Required pure collection commands:

- resolve/validate unique row identities.
- create or normalize a fresh row from rowFactory.
- add before/after a target or append.
- remove one row and remove selected rows.
- move one row by delta and reorder one row at a target index.
- replace/update a row immutably, including nested-value updates initiated from a row slot.
- select all eligible rows, clear selection, and prune selection when rows disappear.
- insert validated clipboard rows at the defined insertion point.
- return safe operation metadata for change events and focus restoration.

Invariants:

1. Never mutate the consumer-provided array in place.
2. Never treat array index as persistent row identity.
3. A no-op, invalid, out-of-range, read-only, or disallowed operation must not emit a misleading successful update.
4. Selection is key-based and pruned when a selected row is removed externally.
5. Reordering preserves row objects and their domain data; it changes only their order.
6. Moving/deleting/pasting rows must restore focus to a predictable surviving row/control or to Add Row when appropriate.
7. Nested-grid selection and keyboard navigation must remain scoped to the nested builder and must not accidentally select, move, or delete rows in its parent.

## 7. Copy/paste contract

Create a dedicated clipboard envelope, independent of the existing rule-flow clipboard:

    {
      "type": "flexirule-grid-clipboard",
      "version": 1,
      "dataType": "consumer-defined-stable-type",
      "copiedAt": "ISO-8601 timestamp",
      "rows": []
    }

The exact shape and version should be centralized in grid_builder_clipboard.js and documented. Copy selected rows in their current visual order. Copy only serializable row data; exclude selected/focused flags, drag metadata, private builder keys, Vue proxies, component instances, functions, and other UI-only state.

Paste must validate the envelope, type, version, timestamp/expiry, rows array, and JSON-safe payload before changing the model. Enforce exact clipboardType match so a grid for one row type cannot accidentally accept another row type. Generate fresh consumer keys when the row type requires them; do not duplicate internal identifiers. Never blindly trust localStorage content.

Clipboard behavior:

1. Prefer the native system Clipboard API during a direct user gesture where it is available and permitted. This is the path that makes copy/paste available across tabs and can support other applications that preserve the JSON text.
2. Provide a separate GridBuilder namespaced same-origin localStorage fallback with a bounded expiry (proposed 30 minutes), so another tab of the same app can still paste when system clipboard read access is unavailable. Listen to storage changes only when needed and clean up listeners on unmount.
3. Keep existing graph/rule-flow clipboard keys and payload types untouched.
4. Always offer visible Copy/Paste actions when enabled; toolbar actions must work even if keyboard shortcuts are inapplicable.
5. Keyboard copy/paste must not hijack text-selection copy, normal editor paste, combobox interaction, or browser-reserved shortcuts. Only intercept when focus is in the grid’s own navigation context and the target is not an editable control with native clipboard behavior.
6. Show accessible success/error feedback without placing row contents in logs. If both system and fallback paths fail, report the failure rather than claiming the copy succeeded.

The localStorage fallback is same-origin only; cross-origin tabs, separate browser profiles, and unrelated devices require the native system clipboard or another explicit transport.

## 8. Keyboard and focus contract

Keyboard handling must be scoped to the active GridBuilder root. Do not register permanent window-level listeners per mounted grid and do not conflict with the existing global useKeyboardRegistry.

The exact interaction map should be encoded as tests and documented in the component README. Recommended defaults:

- Tab / Shift+Tab: preserve browser-native movement between focusable controls; never trap Tab.
- Arrow Up / Arrow Down: when focus is on a grid cell/control that opts into grid navigation, move to the corresponding control in the previous/next row where possible.
- Arrow Left / Arrow Right: move between grid cells only when the event is not being used to edit text, navigate a native input, control a select, or operate a combobox/listbox.
- Enter: preserve native activation/editing semantics. It may move into a cell or advance after editing only for controls explicitly participating in GridBuilder navigation; do not make Enter unexpectedly submit a parent form or activate a different row.
- Alt+Enter: proposed default quick-add shortcut when adding is enabled, focused inside the grid, and the target is not an editor that owns that shortcut. Allow the mapping to be configured if an actual consumer has a conflict.
- Escape: cancel an active drag or dismiss grid-owned transient UI without undoing committed row changes.
- Ctrl/Cmd+C and Ctrl/Cmd+V: row copy/paste only under the focus/selection rules in the clipboard contract; otherwise leave native behavior intact.
- Move up/down buttons remain available as an accessible non-drag alternative. Keyboard reordering can be exposed when a row action or dedicated documented shortcut is focused.

Custom row renderers must mark cell boundaries/focusable controls through a documented attribute/registration contract. A row may contain text inputs, Selects, ComboBoxes, buttons, and nested grids, so unconditional arrow interception is unacceptable. Focus restoration must run after Vue has updated the DOM, and tests must prove that focus lands in the intended row/cell.

## 9. Selection, bulk operations, drag-and-drop, and removal

### Selection

- Selection is optional; when enabled, each selectable row has a checkbox or equivalent accessible selection control.
- Select All affects only eligible rows. The master checkbox represents none/some/all with a correct indeterminate state and accessible mixed value.
- Selection survives reorder and ordinary row value edits because it is keyed by row identity.
- External removal prunes stale selected keys.
- Bulk action content is supplied through a slot, receiving a stable selected-row snapshot and clearSelection helper. The generic component must not invent domain operations such as activate, export, or update category.

### Row actions

- Move Up/Move Down appear only when configured, are disabled at boundaries, and announce the target position.
- Remove appears only when configured and writable. Confirmation is a consumer policy or an explicitly provided hook; do not pop an unpredictable confirmation for every consumer by default.
- Delete Selected should be a clearly configured bulk action or built-in generic remove-selected action; avoid silently duplicating both controls.
- All visible icon-only buttons need translated labels and title/help text; use __() for frontend strings.

### Drag-and-drop

- Use an explicit drag handle and keep editable cells/buttons independently interactive.
- Track source and target within a unique GridBuilder instance. A row can be dropped only into the same builder unless a future cross-grid move contract is explicitly added.
- Prevent nested builders from consuming or bubbling each other’s drag/drop operations.
- Drop indicators must visibly identify insertion position. Clear drag state on drop, cancel, invalid drop, and unmount.
- Reordering must work at the top, middle, bottom, empty-grid target (where supported), and after moving within the same collection without off-by-one errors.
- Provide move-up/down buttons or documented keyboard reordering as an accessible alternative to drag.

## 10. Nested grids and scopes

GridBuilder should not prescribe a collection schema. A row renderer can compose another GridBuilder over a child collection, so a parent row may contain an expandable list of variants, output mappings, query fields, or another scoped collection.

The parent row context must provide updateRow(index, nextRow) or an equivalent immutable helper. A nested component update should replace the affected parent row and emit a new outer modelValue array; it must not mutate row.children silently or bypass the parent’s controlled update. Example consumer flow:

    parent GridBuilder row slot
      render parent row cells
      render nested GridBuilder with row.children as its value
      on nested update, replace parent row with a new row object
      emit the new parent row array through the parent builder

Each nested instance has independent row keys, selection, focus state, drag state, and clipboard dataType. Nested events and keyboard operations stay within that instance unless the consumer explicitly coordinates them. Include a nested sample in the README and tests for parent/child edits, delete, reorder, selection isolation, and copy/paste type isolation.

## 11. Responsive, visual, and accessibility requirements

- Use scoped .grid-builder* classes and existing FlexiRule design tokens for surfaces, borders, text, spacing, radii, accent states, and focus. Support the application’s light and dark themes.
- Reuse consistent FlexiRule action-button and icon conventions; do not hard-code a standalone palette or introduce a CSS framework.
- At wide widths, keep header/row alignment consistent and allow consumer-defined cell layouts.
- At narrow widths, the shell must not force page-wide overflow. Provide a usable horizontal-scroll mode when a custom row needs aligned columns; permit consumers to switch row content to stacked/card layout through responsive slots/styles. GridBuilder cannot infer custom cell labels, so the row renderer must provide labels or accessible names for stacked cells.
- Preserve visible focus, selected-row highlighting, a clear drag insertion marker, disabled/read-only states, and a useful empty state.
- Add status/live-region announcements for selection changes, row add/remove/reorder, paste result, and operation errors without noisy announcements on every keystroke.
- Maintain sufficient contrast and non-color cues; respect reduced-motion preferences for transitions.
- Every interaction must be usable by keyboard; drag-and-drop is enhancement, never the only reorder mechanism.
- Keep title/header, column header, action toolbar, and footer optional so GridBuilder can fit compact action panels as well as full-width grid layouts.

## 12. Implementation phases

### Phase 0 — Contract and risk lock

- Re-read current develop versions of FlexiGrid.vue, InlineTableControl.vue, useClipboard.js, utils/clipboard.js, design-tokens.css, and any consumers likely to use the new primitive.
- Define props, slots, events, row identity requirements, clipboard envelope, and keyboard contract in README before implementation.
- Confirm whether any current component already supplies a suitable shared control for confirmation or announcements; reuse it only if it fits without coupling GridBuilder to a feature-specific store.

**Exit gate:** no ambiguous ownership between GridBuilder and the row renderer; clipboard cannot conflict with graph clipboard; identity and nested update semantics are documented.

### Phase 1 — Pure core and invariants

- Implement grid_builder_types.js constants for supported operation names and clipboard envelope version.
- Implement pure utilities for stable identity, eligible rows, operation targets, index normalization, safe payload validation, and clipboard serialization.
- Implement immutable commands for add, update, remove, remove-selected, move, reorder, select-all eligibility, and paste insertion.
- Add focused tests for duplicates/missing keys, invalid indices, read-only no-ops, no-op reorders, stable selection through reorder, and immutable updates.

**Exit gate:** pure commands are deterministic and do not require a browser, Vue mount, Frappe globals, or a Pinia store.

### Phase 2 — Controlled component and compositional rendering

- Implement GridBuilder.vue and default GridBuilderRow.vue.
- Wire modelValue / update:modelValue and stable per-instance row keys.
- Add optional header, column-header, row, empty, bulk-actions, row-actions, and footer slots as justified by the final API.
- Support a consumer-supplied rowComponent with a documented slot/prop contract.
- Implement immutable updateRow so custom rows and nested grids can update safely.
- Ensure readOnly blocks every mutation path, including keyboard, paste, toolbar, row actions, and drag/drop.

**Exit gate:** a minimal consumer can render plain rows and a custom component row without action-specific imports or domain schema.

### Phase 3 — Selection and row operations

- Add selection controls, select-all/indeterminate state, stable selected rows, pruning on external updates, move controls, remove control, and selected-row bulk slot.
- Add rowFactory handling and focus restoration after add/remove/move.
- Add drag handle/drop target state and same-grid reorder commands.

**Exit gate:** mouse and keyboard-accessible non-drag alternatives yield identical canonical row order and selection remains attached to the intended records.

### Phase 4 — Clipboard

- Add copy/paste toolbar actions and the typed/versioned clipboard envelope.
- Implement native clipboard path, safe parsing, same-origin storage fallback with expiry, stale/invalid payload rejection, wrong-type rejection, and fresh-key rules.
- Add nested-grid isolation and ensure that the existing rule-flow clipboard remains unchanged.
- Ensure error/permission paths are visible and do not report false success.

**Exit gate:** same-type rows paste correctly in another tab; different-type or malformed clipboard data changes nothing.

### Phase 5 — Keyboard, accessibility, and responsive polish

- Implement scoped keyboard navigation and cell registration/attribute contract.
- Preserve native input, textarea, select, combobox, text-selection, and form behavior.
- Add aria labels, mixed selection state, live announcements, focus styles, and reduced-motion support.
- Build narrow-width layout and verify both horizontal and stacked consumer-rendered rows.
- Translate all component-owned user-facing strings using __().

**Exit gate:** keyboard and assistive-technology checks pass for a default row, a form-control row, and a nested-grid row.

### Phase 6 — Consumer example, documentation, and hardening

- Write README usage snippets for a simple row slot, a rowComponent, nested collection, selection/bulk action, and cross-tab clipboardType configuration.
- Add a small isolated demonstration/test consumer or story only if the repository has an appropriate convention; do not add production action-specific configuration merely to demo the generic component.
- Run formatter, ESLint/pre-commit checks, focused unit tests, JavaScript/Vue build, and relevant Frappe app validation. Fix formatting mutations and rerun the checks so the final status reflects the committed version.
- Review event contract, performance for large row collections, lifecycle cleanup, import paths, and accidental CSS/global listener leaks.

**Exit gate:** plan requirements are met, focused tests pass, docs are complete, and CI/build checks for the touched paths pass.

## 13. Test matrix

### Pure utilities and commands

- Add row produces a fresh object and appends/inserts at the intended position.
- Update row and nested update produce new arrays without mutating old arrays.
- Remove one/many rows; no stale selected keys remain.
- Reorder top-to-bottom, bottom-to-top, adjacent and non-adjacent rows; invalid/self moves are no-ops.
- Selection survives reorder and edits; duplicate keys are detected.
- Empty rows and malformed clipboard payloads are handled safely.
- Clipboard dataType/version/expiry mismatch is rejected.
- Paste creates fresh identity where required and strips private UI metadata.
- Same-type copy/paste retains row order and serializable domain values.

### Component behavior

- Header, column header, footer, empty state, and action regions can each be hidden or provided independently.
- row slot and rowComponent paths both receive the same documented context.
- Select all and indeterminate state are correct for zero, some, all, and ineligible rows.
- Read-only disables every mutation and paste entry point.
- Add/remove/move/drag focus restoration targets a sensible surviving control.
- Nested grid emits an outer update and does not leak selection or drag state into its parent.
- Mount/unmount cycles leave no event listeners, storage listeners, drag state, or timers behind.

### Keyboard and accessibility

- Tab and Shift+Tab are never trapped.
- Arrow navigation works across marked controls/cells and rows.
- Text caret movement, native selects, combobox menus, and text editors retain native behavior.
- Enter does not unexpectedly submit a containing form or activate a destructive action.
- Quick-add only runs within the active builder and honors read-only/add permissions.
- Accessible labels exist for icon-only controls; master checkbox reports mixed state.
- Screen-reader/live status messages are informative but not emitted for every keystroke.

### Browser/integration checks

- Drag-and-drop over first/middle/last target works and highlights the actual insertion target.
- Nested drag does not reorder the parent.
- Clipboard works via the native path and local fallback; denied permissions do not produce false success.
- Two same-origin tabs can paste the same data type; another type is rejected.
- Light/dark themes and narrow/wide viewports render without clipped controls or page-level horizontal overflow.
- Build and lint check component imports and Vue template syntax.

Use the focused pure-test pattern alongside the Tree Builder tests as a reference, but explicitly verify the repository’s test runner. Since npm test is currently a placeholder, the plan should not claim that command runs the new tests until the package/test tooling is deliberately updated.

## 14. Acceptance criteria

The implementation is ready for review when all of the following are true:

- GridBuilder is a reusable sibling primitive under components/grid_builder and has no imports from action-specific configuration folders, Pinia stores, VueFlow, or TreeBuilder internals.
- Consumer row data remains canonical and controlled; UI state does not leak into modelValue.
- Consumers can choose a row slot or a row component and can nest another GridBuilder without bypassing outer model updates.
- All requested optional controls can be enabled independently without empty controls or awkward layout gaps.
- Selection, add/remove, movement, drag/drop, bulk slots, and clipboard share one consistent operation contract.
- Cross-tab paste is type-checked, versioned, bounded in its fallback lifetime, and isolated from the rule-flow clipboard.
- Keyboard use is scoped and respects native editing interactions; drag is not the only reorder method.
- Responsive styles use FlexiRule tokens and preserve the consumer’s ability to provide accessible cell labels.
- Tests cover pure commands, focus/keyboard interactions, clipboard validation, nested grids, and read-only behavior.
- README documents API, slot/component contracts, row identity, clipboardType, keyboard behavior, and nested-grid updates.
- Formatting, linting, focused tests, build, and any relevant Frappe validation have been run and their actual results recorded in the PR.

## 15. Main risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Unstable identity causes selection to jump rows | Require/document stable keys; use an internal non-serialized sidecar only as a fallback; test external updates and reorder. |
| Generic builder duplicates FlexiGrid or InlineTableControl | Keep domain schema and ControlFactory integration out of the core; expose slots/components instead. |
| Custom controls break arrow navigation | Require opt-in cell markers and preserve native editing/combobox behavior; cover with browser tests. |
| Nested grid events mutate parent data invisibly | Expose immutable updateRow helper and test the full child-to-parent emit path. |
| Clipboard accepts the wrong row kind or stale payload | Type/version/timestamp checks, safe JSON validation, strict clipboardType match, and bounded fallback expiry. |
| Storage fallback overwrites graph clipboard | Separate type and localStorage key; never modify the existing graph clipboard contract. |
| Drag targets or indices are off by one | Pure reorder commands, explicit insertion targets, and boundary-focused tests. |
| Styling relies on global selectors or light-theme colors | Scoped class namespace, design tokens, dark-theme checks, and focus/reduced-motion tests. |
| Keyboard listener collisions across multiple grids | Attach listeners to each grid root, clean them up, and ensure nested grids stop handling parent navigation. |
| Sorting/pagination conflict with canonical manual order | Expose extension slots now; defer generic sorting/paging state until consumer requirements define interaction with reordering. |

## 16. Recommended implementation order

Implement the contract and pure tests first; then controlled rendering; selection and row actions; drag/drop; clipboard; keyboard/focus; responsive/accessibility; finally documentation, consumer verification, and CI hardening. Do not build the complete feature set directly inside one large Vue file, and do not introduce a real action-type integration until the generic API has passed its isolated tests.

This document is the implementation plan only. The next implementation step is Phase 0 on feat/grid-builder-generic-20261012, followed by the pure core; no GridBuilder source implementation is included in this commit.
