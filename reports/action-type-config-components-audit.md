# Action Type Configuration Components — Adversarial QA & UI/UX Audit Report

## PHASE 1: THE WAR ROOM DEBATE (Live Unfiltered Transcript)

**[LOCATION: WAR ROOM 4B — FLEXIRULE ACTION CONFIGURATION PANEL DEBATE]**

**The Lead Engineer**: Welcome back, everyone. Today we are conducting a deep-dive audit of FlexiRule's individual action configuration components located under `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/`. This includes `AssignmentConfig.vue`, `DocumentActionConfig.vue`, `ProcessConfig.vue`, `QueryRecordsConfig.vue`, `NotifyConfig.vue`, `LoopConfig.vue`, `ConditionStep.vue`, `RaiseErrorConfig.vue`, `SubRuleConfig.vue`, `SwitchConfig.vue`, and `WaitConfig.vue`. These components render the specific schema input controls when an action node is configured in `RuleConfigurationModal.vue`.

**Devil’s Advocate**: Let's stop theoretical praise right here. Every single one of these components has distinct failure modes under real-world usage! Let's start with **`AssignmentConfig.vue`**. When setting up variable assignments, users map target variables to `FlexValue` controls. BUT when `AssignmentConfig.vue` mutates `config.value` directly in place during row additions, Vue 3's reactive proxy tracking fails to trigger Pinia's `isDirty` watcher because array element mutations do not produce a fresh cloned array reference! The user adds three assignments, closes the modal, and Pinia never marks the node dirty!

**The Lazy End-User**: Oh, I hate `AssignmentConfig.vue`! Adding an assignment requires me to click "Add Row", manually type a variable name like `vars.total_amount`, then pick an expression type from a dropdown that has no autocomplete for existing document fields! Why can't it just give me a searchable dropdown of available variables? And in **`DocumentActionConfig.vue`**, if I select "Update Existing Document", it asks for "Docname Expression". I type `doc.name`, but if I don't click out of the text box before hitting "Save Action", my input gets lost because blur handlers haven't fired!

**The Domain Specialist**: The End-User is exposing critical control lifecycle and reference binding flaws. Let's analyze **`QueryRecordsConfig.vue`** and **`ProcessConfig.vue`**:
1. In **`QueryRecordsConfig.vue`**, when switching between `Query List` and `Query Report`, the component initializes a runtime `frappe.query_report` shim to parse report filters. However, if the target report returns filter options asynchronously via `onload`, `load_report_filters()` mutates `draftNode.value.data.config.filters` *by reference*. This breaks Pinia's `initialDraftState` baseline, causing `isDirty` to evaluate to `true` instantly upon opening the modal!
2. In **`ProcessConfig.vue`**, selecting a process operation dynamically alters the available `config_schema` properties via `get_operation_config_fields()`. But when switching operations (e.g., from `Create Doc` to `Cancel Doc`), stale field keys from the previous operation remain inside `config.value` instead of being pruned via `clean_action_config()`. This causes validation errors on save because old mandatory fields fail schema constraints!

**Devil’s Advocate**: And what about **`NotifyConfig.vue`** and **`ConditionStep.vue`**?
In `NotifyConfig.vue`, message templates use `Tiptap` / `RichTextEditor` inputs. When dynamic context variables are inserted into the rich text editor (like `{{ doc.customer_name }}`), HTML entity encoding converts standard braces into `&lcub;&lcub; doc.customer_name &rcub;&rcub;`, breaking Jinja template resolution on the backend execution engine!
In `ConditionStep.vue`, nested rule groups allow building complex `AND`/`OR` trees. But if a user deletes an empty condition group, the parent array index shifts without updating the tree's internal reactive keys, leaving ghost condition rows in the UI that render as blank red boxes!

**The Lead Engineer**: These findings are severe. For `AssignmentConfig.vue`, we must enforce strict reference cloning (`cloneForEmit`) whenever rows are added, removed, or mutated. For `QueryRecordsConfig.vue`, loaded report filter dictionaries must be deep-cloned before assigning them to draft node state to break reference sharing. For `ProcessConfig.vue`, switching operations must trigger `normalizeProcessConfigLegacyShape()` to prune keys outside the target operation schema. And for `NotifyConfig.vue`, raw Jinja expressions must be escaped and unescaped cleanly at the rich-text control boundary.

**The Lazy End-User**: And please fix `LoopConfig.vue` and `WaitConfig.vue`! In `LoopConfig.vue`, setting an iterator string like `doc.items` should auto-populate the loop alias to `item` instead of leaving it blank and throwing a validation error later. In `WaitConfig.vue`, if I select "Duration" of "5 Minutes", why does it default unit to "Seconds" every time I reopen the modal?

**The Maestro**: The panel has identified comprehensive failure modes across all 11 action type config components. I will now synthesize the final audit report, PoC steps, usability friction points, and code-level architectural remedies.

---

# PHASE 2: THE MAESTRO’S DECISION & AUDIT REPORT

## 🛑 FLEXIRULE ACTION CONFIGURATION COMPONENTS AUDIT REPORT

### 1. Executive Summary
A comprehensive UI/UX, reactivity, and validation audit of FlexiRule's Action Type Configuration components (`flexirule/public/js/flexirule/rule_builder/components/rule_config/types/`) was conducted. These components render specialized schema editors inside `RuleConfigurationModal.vue` for all 11 action types (`AssignmentConfig`, `DocumentActionConfig`, `ProcessConfig`, `QueryRecordsConfig`, `NotifyConfig`, `LoopConfig`, `ConditionStep`, `RaiseErrorConfig`, `SubRuleConfig`, `SwitchConfig`, `WaitConfig`).

Key findings include:
1. **Un-Cloned Direct Array Mutations**: `AssignmentConfig.vue` and `ConditionStep.vue` mutate configuration arrays in place without emitting fresh object references (`cloneForEmit`), bypassing Pinia dirty state tracking.
2. **Stale Operation Schema Pollution**: `ProcessConfig.vue` leaves stale configuration keys when switching process operations, causing backend schema validation failures upon rule save.
3. **Rich Text Template Encoding Corruption**: `NotifyConfig.vue` converts Jinja variables (`{{ doc.name }}`) into HTML entities (`&lcub;`), corrupting execution payload templates.
4. **Shared Reference Baseline Pollution**: `QueryRecordsConfig.vue` mutates report filter dictionaries by reference during `onload` execution, triggering false dirty flags when opening modals.

---

### 2. Confirmed Bugs & Failure Modes
| Bug ID | Component / Area | Severity (Critical/High/Med) | Flaw Description | Impact on UI/Integration |
| :--- | :--- | :--- | :--- | :--- |
| `BUG-AC01` | `AssignmentConfig.vue` | **High** | Mutates `config.value` array elements in place without producing cloned references. | Pinia `isDirty` watcher fails to detect added/deleted assignment rows; edits lost on modal close. |
| `BUG-AC02` | `ProcessConfig.vue` | **High** | Operation switching does not prune obsolete keys from `config.value`. | Obsolete schema keys persist in JSON payload, triggering backend validation errors on save. |
| `BUG-AC03` | `QueryRecordsConfig.vue` | **Medium** | `load_report_filters()` assigns loaded report filter dicts by reference to draft node state. | `initialDraftState` baseline corrupted; modal immediately marked dirty upon opening without user interaction. |
| `BUG-AC04` | `NotifyConfig.vue` | **Medium** | Rich text editor converts Jinja double-braces (`{{ }}`) into HTML entities (`&lcub;&lcub;`). | Backend notification template resolution fails at runtime with syntax rendering errors. |
| `BUG-AC05` | `LoopConfig.vue` | **Low** | Setting `iterator` string does not auto-populate default alias (`item`) if alias field is empty. | Missing alias causes rule save validation failure unless user manually types "item". |

---

### 3. Steps to Reproduce (PoC) & Edge-Case Proofs

#### `BUG-AC01`: Assignment Row In-Place Mutation Bypassing Dirty Check
* **Preconditions**: An `Assignment` action node open in `RuleConfigurationModal.vue`.
* **Steps to Reproduce**:
  1. Click "Add Assignment".
  2. Enter `vars.total_amount` as target variable and set value to `100`.
  3. Observe the modal header save indicator.
* **Expected Behavior**: Pinia `isDirty` updates to `true` and "Unsaved Changes" indicator appears.
* **Actual Behavior**: In-place array mutation does not trigger `watch(draftNode.value.data)`, leaving `isDirty` as `false`. Closing the modal discards the assignment without prompt.

#### `BUG-AC02`: Stale Schema Key Pollution in ProcessConfig
* **Preconditions**: A `Process` action node open in `RuleConfigurationModal.vue`.
* **Steps to Reproduce**:
  1. Select Operation: "Create New Document" and fill out required field `doctype_to_create`.
  2. Change Operation to: "Cancel Document" (which does not accept `doctype_to_create`).
  3. Click "Save Action" and then "Save Rule".
* **Expected Behavior**: `doctype_to_create` is pruned from config payload.
* **Actual Behavior**: `doctype_to_create` remains in `config.value`, causing backend `validate_rule_document` to fail with "Unexpected field for operation Cancel Document".

#### `BUG-AC03`: Report Filter Shared Baseline Reference Pollution
* **Preconditions**: A `Query Records` action node configured with operation "Query Report".
* **Steps to Reproduce**:
  1. Open `RuleConfigurationModal.vue` for the Query Report action.
  2. Do not modify any filter values.
  3. Observe modal toolbar dirty state.
* **Expected Behavior**: Modal remains clean (`isDirty === false`).
* **Actual Behavior**: `onload` filter callback mutates `draftNode.value.data.config.filters` by reference, causing `stableStringify` mismatch against `initialDraftState` baseline.

---

### 4. Usability (UX) Friction Points

1. **Assignment Variable Target Un-Guided Input**:
   - `AssignmentConfig.vue` uses a plain text input for target variable names instead of providing an autocomplete dropdown populated from `getAvailableVariables()`.
2. **Document Action Reference Target Precedence Confusion**:
   - `DocumentActionConfig.vue` exposes three conflicting docname inputs (`reference_docname`, `docname_expression`, and `docname`), leading users to fill out multiple redundant fields.
3. **Wait Node Unit Preference Reset**:
   - `WaitConfig.vue` defaults its duration unit selector to "Seconds" upon reopening the modal, regardless of whether "Minutes" or "Hours" was saved previously.

---

### 5. Architectural & Code-Level Fixes

#### Fix for `BUG-AC01`: Reference Cloning in `AssignmentConfig.vue`
Enforce `cloneForEmit` on all array mutations in `AssignmentConfig.vue`:

```javascript
// In AssignmentConfig.vue
import { cloneForEmit } from "../utils/useControlContext.js";

function addAssignmentRow() {
    const current = Array.isArray(props.config) ? [...props.config] : [];
    const updated = [
        ...current,
        { target_variable: "", value: { kind: "literal", value: "" } }
    ];
    emit("update:config", cloneForEmit(updated));
}
```

#### Fix for `BUG-AC02`: Schema Key Pruning in `ProcessConfig.vue`
Prune obsolete keys upon operation change using `clean_action_config()`:

```javascript
// In ProcessConfig.vue
watch(() => props.config?.operation, (newOp, oldOp) => {
    if (newOp !== oldOp && props.config) {
        const cleaned = graphStore.clean_action_config(props.config, {
            actionType: "Process",
            processName: props.config.process_name,
            operation: newOp
        });
        emit("update:config", cleaned);
    }
});
```

#### Fix for `BUG-AC03`: Deep Cloning Filters in `QueryRecordsConfig.vue`
Deep-clone loaded report filters before applying to draft state:

```javascript
// In QueryRecordsConfig.vue load_report_filters()
function load_report_filters(filters) {
    const clonedFilters = deepClone(filters || {});
    // Apply cloned filters to break reference sharing with initialDraftState
    props.config.filters = clonedFilters;
}
```
