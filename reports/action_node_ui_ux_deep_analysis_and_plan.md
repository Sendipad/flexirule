# FlexiRule Action Node UI/UX Improvement — Deep Source Analysis and Implementation Plan

## Executive Summary

FlexiRule uses a Vue 3 + VueFlow visual builder canvas for designing and executing business rules. In its current implementation, Rule Action nodes on the canvas exhibit inconsistent visual identity:
- Some Action nodes display only a user-entered custom label or operation name (e.g. `Query List`), hiding their underlying Action Type (`Query Records`).
- Unconfigured or partially configured nodes often lack an obvious, human-readable Action Type banner.
- Action Type identity, operation/variant, user description, and configuration status are not structured with a unified visual hierarchy across the canvas.

This report presents a deep source-code audit across the backend Python contract framework (`flexirule/ruleflow/core/`) and frontend Vue 3 canvas architecture (`flexirule/public/js/flexirule/rule_builder/`), and outlines an implementation plan to establish a canonical, stable Action Type identity for every Action node on the canvas.

---

## 1. Current Action Type Inventory

Every Action Type in FlexiRule is registered via an `ActionHandler` subclass in `flexirule/ruleflow/core/action_handlers/` and exposed to the frontend via the `ContractDTOBuilder` (`/api/flexirule.ruleflow.core.contracts.get_contract_dto`).

| Action Type | Internal ID / `action_type` | Current Canvas Label | Current Operation Label | Metadata Source | Identified UX / Technical Problems |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Query Records** | `Query Records` | `(action_label)` or `QUERY RECORDS` | `data.operation` (e.g. `Query List`, `Query Doc`, `Exist Record`) | `query_records.py` | Overwrites header label if `action_label` is custom; `Query List` appears as title without indicating `QUERY RECORDS`. |
| **Assignment** | `Assignment` | `(action_label)` or `ASSIGNMENT` | None | `assignment.py` | Shows generic `Set Context Variable` tag regardless of operation/target; lacks clean summary of assigned fields/values. |
| **Document Action** | `Document Action` | `(action_label)` or `DOCUMENT ACTION` | `data.operation` (e.g. `Create New`, `Update Existing`) | `document_action.py` | Operation is listed in subtitle, but header displays uppercase `DOCUMENT ACTION` without displaying `display_label` from contract. |
| **Process** | `Process` | `(action_label)` or `PROCESS` | `data.operation` (e.g. Process Name / Operation Name) | `process.py` | Dynamic Process operations lack a distinct operation badge; title falls back to raw operation string. |
| **Notify** | `Notify` | `(action_label)` or `NOTIFY` | `data.operation` (e.g. `Toast`, `Email`, `System`) | `simple_actions.py` | Subtitle shows `Toast` or `Email`, but message content / target recipient is hidden from canvas summary. |
| **Raise Error** | `Raise Error` | `(action_label)` or `RAISE ERROR` | None | `simple_actions.py` | Lacks concise summary of configured error message/code on the canvas card. |
| **Wait** | `Wait` | `(action_label)` or `WAIT` | None | `simple_actions.py` | Lacks summary of delay duration or resume condition on the canvas card. |
| **Sub-Rule** | `Sub-Rule` | `(action_label)` or `SUB-RULE` | None | `sub_rule.py` | Shows `sub_rule_name` in details, but sub-rule identity and return variable summary are unformatted. |
| **Stop** | `Stop` | `(action_label)` or `STOP` | `data.operation` (`Success` / `Error`) | `simple_actions.py` | Terminal node status and response message summary are not visually distinct. |
| **Condition** | `Condition` | Rendered via `ConditionNode.vue` | None | `condition.py` | Structural control flow node; uses dedicated canvas card. |
| **Loop** | `Loop` | Rendered via `LoopNode.vue` | None | `loop.py` | Structural control flow node; uses dedicated canvas card. |
| **Switch** | `Switch` | `(action_label)` or `SWITCH` | None | `switch.py` | Structural/Action hybrid; rendered via `ProcessNode.vue` when used as an action node. |
| **Entry Action** | `Entry Action` | Rendered via `StartNode.vue` | None | `simple_actions.py` | Flow entry trigger node; distinct canvas component (`StartNode.vue`). |

---

## 2. Current Canvas Node Rendering Architecture

### Node Dispatch in `App.vue`
In `App.vue`, VueFlow templates dispatch nodes based on their `type` property:
```vue
<template #node-process="nodeProps"><ProcessNode v-bind="nodeProps" /></template>
<template #node-set-value="nodeProps"><ProcessNode v-bind="nodeProps" /></template>
<template #node-notify="nodeProps"><ProcessNode v-bind="nodeProps" /></template>
<template #node-query="nodeProps"><ProcessNode v-bind="nodeProps" /></template>
<template #node-documentaction="nodeProps"><ProcessNode v-bind="nodeProps" /></template>
<template #node-assignment="nodeProps"><ProcessNode v-bind="nodeProps" /></template>
<template #node-sub-rule="nodeProps"><ProcessNode v-bind="nodeProps" /></template>
<template #node-raise-error="nodeProps"><ProcessNode v-bind="nodeProps" /></template>
<template #node-wait="nodeProps"><ProcessNode v-bind="nodeProps" /></template>
<template #node-switch="nodeProps"><ProcessNode v-bind="nodeProps" /></template>
```

All Rule Action nodes use `ProcessNode.vue` as their primary canvas rendering shell. Structural flow nodes (`StartNode.vue`, `ConditionNode.vue`, `LoopNode.vue`, `StopNode.vue`) have dedicated components.

### Current `ProcessNode.vue` Visual Structure
Currently, `ProcessNode.vue` computes `nodeMeta` as follows:
```js
const nodeMeta = computed(() => {
    const actionType = props.data?.action_type || "Process";
    const contract = getContract(actionType);
    const css = contract.css || {};
    return {
        color: css.color || "#0d6efd",
        icon: css.icon || "fa-cog",
        typeLabel: (actionType || "PROCESS").toUpperCase(),
    };
});
```
And renders:
1. **Header**: `<i :class="nodeMeta.icon"></i> <span class="type-text">{{ nodeMeta.typeLabel }}</span>`
2. **Body Title**: `<InlineEditor v-model:value="data.action_label" />`
3. **Body Subtitle**: `<div class="node-subtitle" v-if="data.operation">{{ data.operation }}</div>`
4. **Body Details**: `<div class="node-details">` checking individual raw properties (`data.reference_doctype`, `data.mutation_mode`, `data.target_field`, `data.variable_name`).
5. **Footer**: `<NodeStatusIndicator :status="status" :errors="errors" />`

### Key Problems with Current Implementation
1. **Ambiguous Action Identity when Custom Label is Set**: If a user renames an action to "Validate Invoice", `InlineEditor` edits `data.action_label`. The small upper header shows `QUERY RECORDS`, but the main title shows `Validate Invoice` and subtitle shows `Query List`. In unconfigured nodes, `action_label` is empty, leaving only `Query List` in subtitle, making the Action Type unclear.
2. **Lack of Standardized Display Labels**: `typeLabel` uses raw `actionType.toUpperCase()`. Human-readable display titles like `"Query Records"` or `"Document Action"` are not explicitly provided in `ActionContract`.
3. **Fragile Detail Summaries**: `ProcessNode.vue` contains hardcoded `v-if` checks for specific properties (`data.reference_doctype`, `data.target_field`), which fail to produce clean summaries for Assignment (e.g. `status = 'Approved'`), Raise Error, or Sub-Rule actions.

---

## 3. Canonical Source-of-Truth Recommendation

To eliminate duplicate metadata definitions and fit seamlessly within FlexiRule's release-candidate architecture:

1. **Extend `ActionContract` in `base_contract.py`**:
   Add explicit `display_label` to `ActionContract`.
   ```python
   class ActionContract:
       def __init__(
           self,
           action_type: str,
           *,
           display_label: str | None = None,
           icon: str | None = None,
           ...
       ):
           self.action_type = action_type
           self.display_label = display_label or action_type
   ```

2. **Propagate Display Metadata via Contract DTO (`contract_dto.py` and `contracts.js`)**:
   `ContractDTOBuilder` passes `display_label`, `icon`, and `description` to the frontend `contracts.js` registry and `useMetaStore`.

3. **Presentation-Only Summary Formatter Composable (`useActionSummary.js`)**:
   Create a dedicated lightweight composable (`flexirule/public/js/flexirule/rule_builder/composables/useActionSummary.js`) that safely inspects `data` (and optional `operation`) and formats a concise presentation summary for each Action Type:
   - **Query Records**: `DocType` + `return_variable` (e.g., `Journal Entry → vars.journal_doc`)
   - **Assignment**: Target assignment list or field target (e.g., `doc.status = Approved`)
   - **Document Action**: Operation mode + Reference DocType (e.g., `Create New: Sales Order`)
   - **Notify**: Message channel/type (e.g., `Toast: "Order Approved"`)
   - **Raise Error**: Error message (e.g., `"Invalid status"`)
   - **Sub-Rule**: Target rule name (e.g., `Rule: Calculate Tax`)
   - **Wait**: Delay expression / duration
   - **Process**: Process operation name + target

---

## 4. Target Canvas Visual Hierarchy

Every Rule Action node rendered via `ProcessNode.vue` will strictly adhere to the following visual hierarchy:

```
┌───────────────────────────────────────────┐
│ 🔍 QUERY RECORDS                         │  ← Header: Icon + Canonical Display Label
├───────────────────────────────────────────┤
│ Query List                                │  ← Subtitle: Operation / Variant (if present)
│ Find Open Journal Entries                 │  ← Title: Custom user label (if present)
│                                           │
│ 🗄️ Journal Entry                         │  ← Summary: Key configuration details
│ ➔ vars.entries                            │
├───────────────────────────────────────────┤
│ ● Configured                              │  ← Footer: Standardized Node Status Indicator
└───────────────────────────────────────────┘
```

### Invariant Rules
- **Action Type Identity (`QUERY RECORDS`, `ASSIGNMENT`, etc.) is invariant and ALWAYS visible.**
- **Operation/Variant** (`Query List`, `Query Doc`, `Create New`) is displayed beneath the Action Type identity when applicable.
- **Custom User Label** (`action_label`) provides context (e.g. `Find Open Journal Entries`) without replacing or hiding the Action Type identity.
- **Unconfigured Nodes** still clearly display Action Type and Operation, with a status indicator showing `● Not Configured`.

---

## 5. File-Level Implementation Plan

### Phase 1 — Metadata & Source of Truth
1. **`flexirule/ruleflow/core/action_handlers/base_contract.py`**
   - **Current Responsibility**: Defines `ActionContract` data class.
   - **Required Change**: Add `display_label` parameter (defaulting to `action_type`) to `ActionContract.__init__` and include it in `to_dict()`.
   - **Why**: Allows action handlers to declare explicit human-readable display titles.
   - **Risk**: None. Fully backward compatible.

2. **`flexirule/ruleflow/core/action_handlers/*.py`**
   - **Current Responsibility**: Subclasses of `ActionHandler` declaring contracts for Query Records, Assignment, Document Action, Process, Notify, Raise Error, Wait, Sub-Rule, etc.
   - **Required Change**: Pass `display_label` in `get_action_contract()` for each handler (e.g. `display_label="Query Records"`, `display_label="Assignment"`).
   - **Why**: Guarantees canonical display metadata comes directly from handler definitions.
   - **Risk**: None.

3. **`flexirule/public/js/flexirule/core/contracts.js`**
   - **Current Responsibility**: Frontend cache and helper functions (`getContract(actionType)`).
   - **Required Change**: Ensure `getContract()` surfaces `display_label` and `icon`.
   - **Why**: Provides reactive access to canonical Action Type metadata on the canvas.
   - **Risk**: None.

### Phase 2 — Presentation Summary Formatter
1. **`flexirule/public/js/flexirule/rule_builder/composables/useActionSummary.js`** *(New File)*
   - **Responsibility**: Provides a deterministic `getSummary(actionType, nodeData)` formatter that returns structured summary items (`{ label, icon, badge, detail }`) for canvas rendering without altering serialized rule JSON.
   - **Why**: Keeps presentation summary logic clean, modular, and testable without polluting `ProcessNode.vue`.
   - **Risk**: Low. Must handle missing/incomplete node configuration gracefully.

### Phase 3 — Standardized Canvas Action Shell (`ProcessNode.vue`)
1. **`flexirule/public/js/flexirule/rule_builder/components/nodes/ProcessNode.vue`**
   - **Current Responsibility**: Renders canvas cards for all Rule Action nodes.
   - **Required Change**: Update node header to display `nodeMeta.displayLabel` (`QUERY RECORDS`, `ASSIGNMENT`), display `data.operation` as operation subtitle, show custom `action_label` as user note/title, and render `useActionSummary` items in the details section. Ensure full light/dark theme and RTL CSS compatibility.
   - **Why**: Fulfills primary UX principle across all Action nodes.
   - **Risk**: Low. Visual presentation change only; no execution semantics or state structures modified.

### Phase 4 — Testing
1. **`flexirule/ruleflow/tests/test_process_contract_v2.py`** (and backend contract tests)
   - **Change**: Add assertions verifying `display_label` is populated in contract DTO output.
2. **Cypress UI Tests** (`cypress/e2e/canvas_action_nodes.cy.js` / existing UI specs)
   - **Change**: Add tests verifying canvas node header displays stable Action Type labels for both configured and unconfigured action nodes.

---

## 6. Compatibility & Risk Analysis

- **Rule Semantics**: Zero changes to rule engine execution, AST parsing, condition evaluation, or database mutations.
- **Rule Serialization**: Zero changes to persisted JSON schemas in `Rule Action` child doctype rows or `Rule` JSON exports.
- **Backward Compatibility**: Fully compatible with existing rules, cached DTOs, and custom third-party action handlers.

---

## 7. Recommended Implementation Sequence

1. **Step 1**: Update `base_contract.py` and action handlers to include `display_label`.
2. **Step 2**: Create `useActionSummary.js` composable for lightweight presentation summaries.
3. **Step 3**: Update `ProcessNode.vue` to implement the standardized visual hierarchy.
4. **Step 4**: Run backend and frontend test suites to verify metadata contracts and UI integrity.
5. **Step 5**: Run linter (`pre-commit run --all`) and finalize submission.
