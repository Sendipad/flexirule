# Implementation Plan: Generic TreeBuilder Readable View and Leaf Editing

## Status and intent

**Status:** Plan only. Do not implement this file's plan as part of the planning change itself.

**Goal:** Extend Generic TreeBuilder so a consumer can render each leaf as either a readable summary or its existing form, with double-click and an explicit accessible action to switch between them. Unify the behavior with GenericGrid through a reusable, headless inline-presentation contract, while keeping row/leaf-specific rendering and drag/drop behavior in their own components. Use Query Filter as the first concrete consumer so nested filters can read like ordinary language, while keeping the generic layer independent of Frappe, Query Records, Condition semantics, and value-resolver details.

This is a presentation and interaction enhancement. It must not change the canonical tree payload, validation contract, filter serialization, or rule execution behavior.

## 1. Verified current architecture

Relevant source files on the current develop branch:

- [TreeBuilder.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilder.vue) owns the root UI, exposes the generic read-only option, and currently forwards a leaf slot.
- [TreeBuilderNode.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilderNode.vue) recursively renders groups, collections, and leaves and forwards the existing leaf slot through nested nodes.
- [TreeBuilderLeaf.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilderLeaf.vue) currently renders one default leaf slot plus the generic remove action. It has no summary/editor switching behavior.
- [useTreeBuilder.js](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/useTreeBuilder.js) already keeps UI state outside the tree model and defines an editingNodeId ref plus setEditing(). These are not currently wired into the leaf presentation. Reuse this existing state rather than adding edit flags to persisted nodes.
- [TreeBuilder README](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/README.md) establishes the intended boundary: TreeBuilder owns hierarchy and mutations; the consumer owns leaf semantics.
- [GenericGrid.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/controls/GenericGrid.vue) already uses separate row-summary and row slots, double-click switching, and a row action event. It is a useful UX reference.
- [generic_grid_model.mjs](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/controls/generic_grid_model.mjs) centralizes the grid's summary toggle decision. However, GenericGrid currently uses a row property (default isEditing) for its edit state. **Do not copy that storage pattern into TreeBuilder:** an edit flag on a tree node risks leaking UI state into the canonical serialized rule configuration.
- [QueryFilterTree.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/QueryFilterTree.vue) is currently the first clear TreeBuilder consumer. It supplies FilterLeaf as the existing leaf slot and delegates model changes to TreeBuilder.
- [FilterLeaf.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/FilterLeaf.vue) owns field, operator, value/resolver editing, and validation. It already resolves field metadata and uses the existing control/value architecture; keep these responsibilities in the filter domain layer.
- [RuleFlow Settings](https://github.com/Sendipad/flexirule/blob/develop/flexirule/ruleflow/doctype/ruleflow_settings/ruleflow_settings.json) is a single site-wide DocType currently restricted to System Manager for writes. It is not the correct persistence store for a preference that each user can independently change.

## 2. User-visible behavior and terminology

Keep three concepts separate:

1. **Structural/read-only lock** (existing readOnly API): controls whether structural operations and domain editing are permitted. Do not redefine this prop to mean summary presentation.
2. **Presentation mode:** controls whether leaves initially show the form or a readable summary.
3. **Per-leaf edit state:** temporary UI state for the leaf currently opened in form mode.

Recommended public presentation values, resolved from the RuleFlow Settings default:

- **hybrid:** show the summary for existing, valid items; show the form for new or invalid items. When a valid existing item is explicitly edited, switch to its form until the user finishes.
- **summary:** show the summary for existing items, with explicit edit interaction when editing is allowed.
- **form:** show the form for every item. This preserves the existing always-form layout.

Use **Hybrid** as the new RuleFlow Settings default. To avoid a disruptive migration, verify and explicitly document how existing consumers are migrated from their current behavior; do not silently assume every current consumer already has a reliable validity/new-item signal.

When readOnly is true (including an active Ruleflow that cannot be edited), keep presentation and permission as separate concerns. Continue applying Hybrid/Summary/Form presentation rules: a valid existing item can still be shown as a readable summary, while a new or invalid item may be shown in its form-shaped view for inspection. But suppress edit transitions and mutation actions, and pass readOnly/disabled state to the consumer form. Never use presentation mode to grant permission to edit an active/read-only rule.

If a consumer selects summary but does not supply a summary slot, safely fall back to the existing form slot. Do not render a blank leaf or require every current consumer to migrate at once.

## 3. Recommended component contract

### Shared policy, component-specific rendering

Use one small, headless presentation policy shared by GenericGrid, TreeBuilder, and future components. Prefer pure decision helpers with a thin composable only if reactive state wiring is needed. The policy should receive normalized inputs such as `mode`, `isNew`, `isValid`, `editing`, and `readOnly`, and return the display decision and whether editing actions are allowed. It must not inspect arbitrary domain properties or implement its own validation.

Do not merge GenericGrid and TreeBuilder into one rendering component. Keep row selection, grid actions, recursive tree structure, drag/drop, item identity, and domain-specific summary content inside their existing component/consumer layers.

### TreeBuilder API

Add a `presentationMode` prop constrained to `hybrid | summary | form`. The generic component should receive the resolved mode from its owner; it must not fetch RuleFlow Settings itself. For Hybrid, accept consumer-supplied item status (for example a status resolver or explicit booleans in the slot context) so the component can reliably distinguish new/existing and valid/invalid leaves.

Preserve the existing `#leaf` slot as the form/editor renderer and add an optional `#leaf-summary` slot for readable content. Keep existing leaf slot names and slot props backward compatible. Both slots should receive a documented context including node, context, index, parent, effective presentation/edit state, readOnly, and explicit callbacks to request edit or return to summary.

Add an `editorLayout` prop with `replace | alongside`. For TreeBuilder, default to `replace`: the editor replaces the summary content for the active leaf. This keeps the tree compact and avoids presenting duplicate content. Keep the leaf/node wrapper, identity, drag handlers, and drop-target behavior stable while switching the inner content. If `alongside` is supported, it should be an explicit opt-in and must not be the default for TreeBuilder.

Use the existing `editingNodeId` / `setEditing()` state in `useTreeBuilder`. Do not add UI-only flags to serialized nodes. Keep at most one leaf in form-edit mode at a time unless a later use case explicitly requires multi-edit. Clear stale edit state if the active leaf is removed or the tree is replaced.

### GenericGrid adapter

Apply the same mode decision and toggle semantics to GenericGrid using stable row keys, but preserve its own row rendering and grid actions. Audit all current Grid consumers before changing how `isEditing` is read or written. Move UI-only edit state toward component-owned state keyed by stable identity, with a compatibility adapter if existing consumers currently depend on the row's `isEditing` property. Do not break bulk edit, row updates, clone/copy-paste, row replacement, or consumer action events.

GenericGrid may retain its current summary/editor layout by default for backward compatibility; it should support the same explicit `editorLayout` values so callers can opt into consistent replacement behavior. Do not add `editorLayout` to RuleFlow Settings in this task: the global setting should select Hybrid/Summary/Form, not component-specific layout mechanics.

### Interaction details

- Double-click the summary surface to open the editor when editing is permitted. Ignore double-clicks originating from interactive descendants such as links, buttons, inputs, and comboboxes.
- Provide a visible, keyboard-accessible Edit action; double-click must never be the only route into editing.
- Provide a clear Done/return-to-reading action when the editor is open and the configured mode supports summary presentation.
- In readOnly mode, preserve the configured display decision but suppress edit transitions and mutation actions. Pass readOnly/disabled state to the consumer form. An active Rule that is read-only must not be forced into a special summary-only or form-only view.
- For Hybrid, show summary only for existing valid items that are not currently being edited. Show the form for new or invalid items. In readOnly mode, a new/invalid item may still be rendered as a disabled form for inspection.
- Keep drag behavior on a stable wrapper or dedicated drag handle. Interactive controls inside the editor must not start a tree drag, and summary interactions must not accidentally initiate a drag.
- Do not automatically close the editor on blur. Preserve the existing update:modelValue path and make switching modes explicit.
- If a consumer selects summary but provides no summary slot, fall back safely to the existing form slot.
- Keep presentation state out of the canonical tree, Grid row domain data, serialized filters, and Rule Action config.
- Ensure the presentation prop reacts to parent changes and preserve focus/accessibility across transitions.

## 4. Query Filter as the first consumer

After the generic contract is in place, add a dedicated summary renderer for Query Filters, for example FilterLeafSummary.vue or a small pure formatter plus a renderer component. Do not put Query Filter knowledge into TreeBuilder.

The summary should communicate the filter in ordinary language, using available metadata and value information. Examples of the intended shape:

- **Status equals Open**
- **Posting Date is on or after 1 October**
- **Amount is between 100 and 500**
- **Customer is one of …**
- A variable/resolver value shown by a user-facing description rather than raw resolver JSON or an opaque configuration object.

These are illustrative examples; use the actual metadata, translations, and formatting available in the component's context.

Implementation guidance:

1. Reuse the field metadata and value display/formatting mechanisms already used by FlexiRule. Before adding a formatter, inspect whether the existing FlexValue/control architecture exposes a suitable display label or formatter; do not invent a parallel resolver-display schema.
2. Reuse field labels obtained by the current navigable-field/metadata code. Resolve dotted/navigated fields accurately and retain enough context for nested Link/Table fields.
3. Reuse the existing operator-label policy where possible. Preserve operator-specific wording such as date comparisons and special operators.
4. Handle Between as two displayed operands, and handle in / not in and multi-value forms without serializing implementation details.
5. For static values, display meaningful formatted values. For variable or resolver-driven values, display a concise human-readable token/description. Never evaluate a resolver only to paint the summary, and never expose private/runtime values just to create the display text.
6. For empty or malformed leaves, show a stable, translated incomplete/invalid state that lets the user open the form. Do not hide invalid configuration behind an empty label.
7. Render text through normal Vue interpolation; do not render user-configured summaries as raw HTML.
8. Keep summaries presentational. Leaf edits must continue to flow through FilterLeaf and TreeBuilder.replaceNode; summary formatting must not mutate or normalize the persisted payload.

Once summaries cover supported cases, configure QueryFilterTree to use the resolved RuleFlow Settings default (Hybrid by default), while retaining an explicit component override for integrations and tests. Hybrid validity/new-item status must come from the filter consumer's actual validation and identity state, not from a duplicate, weaker validation implementation in TreeBuilder.

## 5. Condition Builder compatibility

Design the generic contract so a future condition leaf can use the same pattern: a domain-specific condition summary slot and the existing condition form/editor slot. The generic core must not parse conditions or format expressions.

The current condition-builder implementation has its own domain model and UI; this task must not silently migrate or rewrite it. Treat moving the existing Condition Builder onto Generic TreeBuilder and adding condition-language summaries as a separate task, following an audit of its canonical model, short-circuit semantics, validation, and save/load contract. That keeps this UX work from inadvertently changing condition compilation or runtime behavior.

## 6. RuleFlow Settings and future per-user preference

Add a Select field to the existing single DocType **RuleFlow Settings** for the site-wide default row/leaf presentation mode. Recommended field name: `row_leaf_presentation_mode`. Options: `Hybrid\nSummary\nForm`. Default: `Hybrid`.

The owning Ruleflow UI should read the setting through the existing settings-loading path and pass the resolved mode into GenericGrid/TreeBuilder. The generic components must not import or fetch RuleFlow Settings directly. Unknown or missing values should safely fall back to Hybrid. An explicit component prop should override the site-wide setting for special consumers and tests.

This is an administrator-configured site-wide default, not a per-user preference: RuleFlow Settings is a Single DocType. A per-user override can be considered later as a separate layer if requested, using Frappe v15's native user-scoped settings mechanism after verifying the exact installed-version API. Do not implement localStorage or a second preference store for this initial setting.

Recommended precedence now: explicit component prop > RuleFlow Settings default > safe fallback Hybrid. If per-user overrides are added later, use explicit component prop > saved user preference > RuleFlow Settings default > safe fallback Hybrid.

The selected presentation mode never grants editing permission. Active/read-only state and backend lifecycle/permission checks remain authoritative; the mode only determines how data is presented.

## 7. Suggested implementation slices

### Slice A — Shared inline-presentation contract for Grid and TreeBuilder

- Define a shared headless inline-presentation contract (for example a composable plus pure decision helpers) for mode resolution, new/valid/editing/read-only decisions, and edit/view actions. Keep the DOM wrappers, grid row selection, tree nesting, and drag/drop local to each component.
- Add presentationMode (hybrid/summary/form) and the optional leaf-summary slot while preserving the current leaf slot.
- Wire the UI-only editingNodeId state through TreeBuilder, recursive TreeBuilderNode, and TreeBuilderLeaf; migrate GenericGrid to the same behavioral contract using stable row keys and component-owned edit state, avoiding row-model mutation for presentation state.
- Implement double-click, accessible Edit/Done actions, hard-read-only gating, missing-summary fallback, and edit-state cleanup.
- Document the API in the TreeBuilder README.
- Add pure tests for mode resolution and edit-state cleanup where the project's current unit-test structure supports them.

### Slice B — Query Filter summaries

- Audit existing FlexValue/control display helpers and field metadata APIs.
- Implement the Query Filter summary renderer and tests for field/operator/value combinations.
- Integrate both slots in QueryFilterTree without changing its model ownership, replaceNode update flow, validation, or serializer.
- Make summary mode the QueryFilterTree-level default only when supported summaries and a usable fallback are in place.

### Slice C — RuleFlow Settings default

- Add a Select field to the existing RuleFlow Settings DocType: Hybrid (default), Summary, Form.
- Wire the setting through the existing settings-loading pattern into GenericGrid and TreeBuilder consumers, without making generic components fetch settings directly.
- Test default/missing/invalid setting fallback and runtime changes if supported by the current settings flow.
- Keep per-user overrides explicitly out of this slice; they can be layered on later if required.

### Slice D — Condition summaries (future, separate scope)

- Audit the current Condition Builder's canonical model and rendering flow.
- Adopt the generic slot/interaction contract only after proving a lossless mapping and preserving validation, serialization, and short-circuit semantics.
- Add readable summaries for the supported condition operators and operands.

## 8. Test plan

### Generic TreeBuilder unit/component tests

- Default form mode renders the existing leaf slot without changing current consumer behavior.
- Summary mode renders leaf-summary by default and returns to the form for the correct node when double-clicked.
- Explicit Edit/Done actions work by keyboard and expose correct accessible labels.
- Double-click on an interactive descendant of the summary does not accidentally toggle editing.
- Summary mode with no summary slot falls back to the existing form.
- Hard readOnly blocks edit transitions and structural operations; current form-only read-only behavior stays compatible.
- Editing one node switches away from the previously edited node as documented.
- Removing the edited leaf or replacing the tree so the node no longer exists clears stale edit state.
- The mode and edit state do not appear in getTree(), emitted update:modelValue, serialized filters, or persisted Rule Action config.
- The summary slot is correctly passed through nested groups and collections.
- Changing presentationMode at runtime updates rendering without requiring a full page reload.

### Query Filter summary tests

Cover at least: missing field/operator/value, normal text/number values, date operators, Between, in / not in, special Is values, nested field paths, static arrays, and variable/resolver-driven values. Assert human-readable output and absence of raw config dumps.

### Regression checks

- Run existing TreeBuilder mutation/validation and drag-model tests.
- Run existing filter operator and serializer tests.
- Verify loading, editing, validating, and saving filters produces the same canonical persisted payload as before.
- Run the frontend build/lint and the targeted UI tests available in the configured Frappe v15 bench.
- If Cypress coverage is added, keep it in its own PR unless that is explicitly in scope; do not make a new Cypress setup a prerequisite for accepting the component/API change.

## 9. Acceptance criteria

1. GenericGrid and TreeBuilder use the same documented inline-presentation decisions and interaction contract, while retaining their component-specific rendering and interactions.
2. RuleFlow Settings exposes Hybrid, Summary, and Form with Hybrid as the default.
3. TreeBuilder supports Hybrid, Summary, and Form presentation modes, with a status resolver supplied by the consumer.
4. A summary leaf/row can switch to form by double-click and by an accessible explicit action, and can return to summary intentionally.
5. TreeBuilder owns generic presentation state; leaf/row consumers own domain summary text and form contents.
6. UI state remains outside the canonical serializable tree and row models.
7. readOnly retains its current permission/interaction meaning and is not overloaded as a display-mode flag. Active/read-only rules still use the configured presentation mode but cannot be edited.
8. The new summary slot works at arbitrary supported nesting depth, and summary rendering does not disable tree drag/drop or require dragging the summary content itself.
9. Hybrid shows summaries for existing valid items and form views for new or invalid items, based on authoritative consumer-supplied status.
10. Query Filter summaries improve readability without changing filter evaluation, values, validation, or serialization.
11. The generic TreeBuilder knows nothing about Frappe DocTypes, filter operators, conditions, or resolver internals.
12. RuleFlow Settings supplies the initial site-wide default; preference loading remains outside generic components. Any later per-user override is a separate explicit decision.
13. The Condition Builder is prepared to reuse the contract later, but its model/compiler/runtime path is not silently changed by this task.
14. Tests verify the observable contracts above and existing grid/tree/filter regressions remain green.

## 10. Source references

- FlexiRule TreeBuilder API and composition: [TreeBuilder.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilder.vue), [TreeBuilderNode.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilderNode.vue), [TreeBuilderLeaf.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilderLeaf.vue), [useTreeBuilder.js](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/useTreeBuilder.js), [TreeBuilder README](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/README.md).
- Grid interaction reference: [GenericGrid.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/controls/GenericGrid.vue) and [generic_grid_model.mjs](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/controls/generic_grid_model.mjs).
- First consumer: [QueryFilterTree.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/QueryFilterTree.vue), [FilterLeaf.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/FilterLeaf.vue), and [query_filter_serializer.js](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/query_filter_serializer.js).
- Current global settings: [RuleFlow Settings DocType](https://github.com/Sendipad/flexirule/blob/develop/flexirule/ruleflow/doctype/ruleflow_settings/ruleflow_settings.json).
- Framework user preferences: [Frappe v15 user_settings.js](https://github.com/frappe/frappe/blob/version-15/frappe/public/js/frappe/model/user_settings.js) and [Frappe v15 user_settings.py](https://github.com/frappe/frappe/blob/version-15/frappe/model/utils/user_settings.py).

## 11. Cross-component design checklist

The follow-up requirement is to unify GenericGrid and TreeBuilder behavior and establish **Hybrid** as the RuleFlow Settings default. This section is authoritative if an earlier paragraph still describes a form-only default or per-user settings as the first persistence layer.

### Shared behavior, not one universal renderer

Use one shared, headless decision/state layer for row and leaf presentation. It should resolve the requested mode, item status (new/existing and valid/invalid), current edit state, and read-only permission into a presentation decision. Keep row/leaf markup, row selection, recursive tree structure, drag/drop, action buttons, and domain-specific summaries in GenericGrid/TreeBuilder and their consumer slots. Do not force the Grid and Tree to share one DOM component.

A reasonable shared API is a composable plus pure helper functions (names to be finalized during implementation), with inputs like `mode`, `itemKey`, `isNew`, `isValid`, `readOnly`, and `editing`. Keep it framework-light and testable. The generic layer must not infer validity from a domain model or implement its own filter/condition validation.

### Should the editor replace the summary in TreeBuilder?

**Yes: in the normal summary/hybrid presentation, the active leaf editor should replace the summary content for that leaf, not sit beside it.** Showing both wastes space and makes the leaf appear duplicated. It also creates a much taller tree that is harder to scan.

The leaf wrapper and its drag/drop affordance must remain mounted/stable while the inner summary/editor content switches. Preserve drag/drop by keeping drag handlers/identity on the wrapper and preferably providing a dedicated drag handle, rather than relying on the summary text itself as the drag target. Interactive controls inside the summary must not accidentally trigger edit-on-double-click or initiate a drag. The Grid can retain its own layout where useful, but its visible mode decisions should follow the same contract.

### Hybrid decision table

| Item status                | Hybrid default                                                         | Edit permitted?                     |
| -------------------------- | ---------------------------------------------------------------------- | ----------------------------------- |
| New item/row/leaf          | Form                                                                   | Yes, unless read-only               |
| Existing and valid         | Summary                                                                | Yes, via explicit Edit/double-click |
| Existing but invalid       | Form, with validation state visible                                    | Yes, unless read-only               |
| Any status while read-only | Apply the configured display rule; suppress edit actions and mutations | No                                  |

For Hybrid, "new" and "valid" are supplied by the consumer using authoritative identity and validation state. Do not guess that a row is new solely because it lacks a generic `name` property, or duplicate a validator inside the presentation layer. For invalid items, make the error state discoverable in both summary and form, and ensure Hybrid selects the form so the user can repair the item.

### Read-only and active rules

Read-only is a capability/permission gate, not a presentation mode. An active rule that cannot be edited should still use the configured Hybrid/Summary/Form display policy. In Hybrid, valid existing items can remain concise summaries; new/invalid items can be shown in form-shaped, non-editable form for inspection. Do not force every row/leaf into a separate "readonly-only" visual mode, and do not let double-click or the Edit button bypass the read-only gate. Preserve the existing backend rule lifecycle and permission checks; this is only a UI presentation contract.

### RuleFlow Settings

Add a Select field in the existing RuleFlow Settings DocType, for example `row_leaf_presentation_mode`, with options:

- `Hybrid`
- `Summary`
- `Form`

Default: `Hybrid`.

This is a site-wide administrator default because RuleFlow Settings is a Single DocType and the user explicitly requested this location. Pass the resolved value down from the settings owner; GenericGrid and TreeBuilder must not fetch settings themselves. A future per-user override may be layered above the site-wide default, but is not part of the first implementation.

### Grid state migration and drag/drop safeguards

GenericGrid currently defaults to reading/writing an `isEditing` property on each row. That differs from TreeBuilder's component-owned `editingNodeId`. During unification, migrate presentation state toward stable-keyed component-owned state in GenericGrid so UI flags do not become part of the row's business data or get serialized/copied. Before changing this, audit every GenericGrid consumer and the bulk-edit actions to preserve public behavior. Add compatibility tests for row updates, cloning/copy-paste, bulk edit, row replacement, and stable row identity.

TreeBuilder must continue supporting drag/drop when summaries replace forms. Keep the draggable wrapper and node identity stable across mode transitions, avoid putting drag behavior on nested interactive summary elements, and test dragging while in Hybrid mode as well as after opening/closing an editor.

### Required tests for this update

- Shared mode-decision tests for all three modes crossed with new/existing, valid/invalid, and read-only states.
- Grid and Tree use identical decisions for equivalent item status.
- Hybrid default loads from RuleFlow Settings and safely falls back to Hybrid for missing/unrecognized values.
- Existing valid item shows summary; new/invalid item shows form; edit/done toggles only the intended item.
- Active/read-only rule still follows the display policy but cannot edit, remove, reorder, or mutate through row/leaf actions.
- Tree drag/drop works while summary content is displayed and after switching a leaf to its form.
- GenericGrid row UI state is not added to row payloads, clipboard serialization, or persisted rule/action data.
- Existing GenericGrid selection, bulk actions, keyboard interactions, and row-update tests remain green.
