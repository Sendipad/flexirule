# Rule DocType Form Consistency Audit Report

## 1. Executive Summary

This audit evaluates the standard Frappe DocType form implementation for **Rule** in FlexiRule (`flexirule/ruleflow/doctype/rule/rule.js`, `rule.json`, `rule.py`, `rule_list.js`, and `rule_action.json`). The objective of this evaluation is to inspect form UX consistency, state management, field reactivity, button availability, child grid field toggling, and specifically the behavior when the `is_active` field is clicked or modified.

Overall, the Rule form has well-structured lifecycle logic and custom UI contracts. However, critical UI/UX inconsistencies and edge-case state glitches exist that impair user experience, cause form state sync bugs, and create discrepancies between frontend form UI and backend state validations.

---

## 2. Form Architecture Overview

The Rule DocType form manages rule metadata, trigger definitions, sub-rule public interfaces, settings, permissions, and the child table of actions (`Rule Action`).

- **Frontend JS Controller (`rule.js`)**: Manages `onload`, `refresh`, `is_active`, `trigger_type`, child table events (`form_render`, `refresh`, `action_type`, `process_name`, `configure_operation`), and custom toolbar buttons.
- **Backend Python Document (`rule.py`)**: Enforces server-side validations (`validate`), status compatibility (`_sync_status`), version lineage, graph integrity, subrule contracts, and permissions.
- **DocType Schema (`rule.json`)**: Configures standard form layout, field types, `depends_on`, `mandatory_depends_on`, `read_only`, and standard state indicators.
- **List View Controller (`rule_list.js`)**: Displays list indicators and quick toggles.

---

## 3. Comprehensive Inspection & Findings

### Finding 1: `is_active` Checkbox Handler & Form Locking Inconsistencies

#### Description & Root Cause
When a user clicks `is_active` on an active rule (`is_active = 1`), `rule.js` intercepts the event in the `is_active(frm)` handler:
```javascript
is_active(frm) {
    if (frm.doc.is_active === 0 && frm._was_active) {
        frm.set_value("is_active", 1);
        show_deactivation_dialog(frm);
        return;
    }

    apply_active_lock(frm);
    frm.refresh_fields();
    frm._was_active = frm.doc.is_active;
}
```

1. **Unsaved / Dirtied State Glitch**:
   - Toggling `is_active` from `1` to `0` immediately reverts the value back to `1` using `frm.set_value("is_active", 1)` and opens `show_deactivation_dialog`.
   - If the user closes or cancels the deactivation dialog (by clicking `X` or clicking outside), `is_active` remains `1`, but the form is marked dirty (`frm.is_dirty() === true`).
   - If the user saves or navigates away, Frappe prompts to save or attempts to save a dirtied form where no actual change was committed by the user.

2. **Inconsistent Lock Application (`apply_active_lock`)**:
   - `apply_active_lock(frm)` sets `read_only` on all fields except `is_active`.
   - However, `apply_active_lock(frm)` disables child table rows using DOM classes:
     ```javascript
     f.grid.wrapper.find(".grid-row, .grid-add-row").toggleClass("disabled", is_active);
     ```
   - DOM manipulation on `f.grid.wrapper` can be overwritten whenever Frappe re-renders the grid or when a user clicks expand/collapse on child rows.
   - Standard Frappe property `frm.set_df_property("actions", "read_only", is_active ? 1 : 0)` or setting grid properties cleanly via Frappe API is preferable to direct jQuery DOM toggles.

3. **Inconsistent Status Synchronisation on Unlocking**:
   - In `show_deactivation_dialog`, clicking "Edit Current Rule" sets `frm._was_active = 0` and calls `frm.set_value("is_active", 0)`.
   - On the client side, setting `is_active = 0` does not automatically update `frm.doc.status` in the UI from "Active" to "Draft" / "Disabled", causing a visually mismatched state (`status` reads "Active" while `is_active` checkbox reads unchecked) until the record is saved and reloaded from the server.

---

### Finding 2: Custom Action Buttons & Action Bar Consistency

#### Description & Root Cause
The `refresh(frm)` hook configures page actions as follows:
```javascript
frm.page.clear_primary_action();
frm.page.set_primary_action(__("Visual Builder"), () => {
    frappe.set_route("rule-builder", frm.doc.name);
});

frm.page.clear_custom_actions();
frm.add_custom_button(__("Amend Rule"), () => amend_rule(frm), __("Actions"));
frm.add_custom_button(__("Debug Rule"), () => test_rule(frm), __("Actions"));
frm.add_custom_button(__("Clear Cache"), () => clear_rule_cache(frm), __("Actions"));
```

1. **Button Visibility on New / Unsaved Documents**:
   - The line `if (frm.is_new()) return;` skips custom buttons on new documents.
   - However, if a user edits an existing saved document and dirties the form (`frm.is_dirty()`), clicking **Visual Builder** navigates away to `#rule-builder/<name>` without warning the user that un-saved form changes will be lost.
   - Similarly, clicking **Amend Rule** or **Debug Rule** while the form is dirty operates on the persisted database record rather than current form modifications, leading to confusion if form edits are unsaved.

2. **Amend Rule Availability**:
   - "Amend Rule" button is visible in the "Actions" dropdown regardless of whether the rule is `Active`, `Draft`, or `Disabled`.
   - On backend, `amend_rule` creates a new version from any rule, but amending a `Draft` rule creates redundant draft versions. "Amend Rule" should primarily be prominent/available when a rule is `Active` or archived/historical.

3. **Debug Rule Modal Context**:
   - "Debug Rule" opens a simulation dialog. However, if `document_type` on the form was changed but not saved, the dialog uses `frm.doc.document_type` which might not match what is in the database, causing server execution errors during `flexirule.ruleflow.api.test_rule`.

---

### Finding 3: Trigger Type Field Dependencies (`apply_trigger_type_contract`)

#### Description & Root Cause
Trigger type handling switches visibility and required flags on `document_type`, `trigger_event`, `trigger_condition`, and `compiled_expression`.
```javascript
function apply_trigger_type_contract(frm, options = {}) { ... }
```

1. **Field Reset Consistency**:
   - Changing `trigger_type` from `DocType Event` to `Callable Event` clears `document_type` and `trigger_event` when `clear_hidden_values: true` is passed.
   - However, `watched_fields` (Small Text) is NOT managed by `apply_trigger_type_contract`. When `trigger_type` is changed to `Callable Event`, `watched_fields` remains hidden by `depends_on` in `rule.json`, but its underlying form value is NOT cleared, leaving orphaned data in `doc.watched_fields`.

2. **`input_schema` and `output_schema` Section Visibility**:
   - In `rule.json`, `section_break_subrule_interface` depends on `eval:doc.trigger_type==="Callable Event" && doc.exposed_as_subrule`.
   - When `exposed_as_subrule` is toggled off, `input_schema` and `output_schema` are hidden, but values remain in `frm.doc.input_schema`. If the rule is saved, those contracts persist in the backend database.

---

### Finding 4: Child Table (`Rule Action`) Grid Field Reactivity

#### Description & Root Cause
Child table formatting uses `toggle_action_fields(frm, cdt, cdn)` and `update_operation_options(frm, cdt, cdn)` triggered on `form_render` and `refresh` of `Rule Action`.

1. **Grid Row Redrawn Glitch during Lock/Unlock**:
   - When `is_active` toggles, `apply_active_lock(frm)` disables child row buttons via DOM manipulation.
   - If a user opens a child row form in a modal or expands a grid row, Frappe re-renders the row HTML, destroying the jQuery `.disabled` class and allowing users to edit inline fields of an Active rule.

2. **Missing `get_query` Refresh for Sub-Rules**:
   - In `onload`, `rule_field.get_query` filters subrules (`trigger_type = 'Callable Event'`, `is_active = 1`, `exposed_as_subrule = 1`).
   - If the user creates a subrule in another tab and activates it, returning to the current rule form and opening the `Sub-Rule` action dropdown shows stale options because `get_query` is set only once in `onload` and never refreshed.

---

### Finding 5: Client-Server Status Synchronization (`_sync_status`)

#### Description & Root Cause
In `rule.py`:
```python
def _sync_status(self):
    active_flag = self.get("is_active")
    status = self.get("status")

    if active_flag:
        if status not in ("Error", "Invalid", "Active"):
            self.status = "Active"
    else:
        if status == "Active":
            self.status = "Disabled"
        elif status not in ("Error", "Invalid", "Disabled", "Archived"):
            self.status = "Draft"
```
- In `rule.js`, when a user checks `is_active`, `frm.doc.status` is not updated on the client prior to save.
- When `is_active` is toggled in client side JS, `frm.set_value("status", ...)` should be called in lock/unlock handlers to ensure immediate visual alignment in the status badge at top right of the form.

---

## 4. What Must Be Fixed

To achieve standard, robust, and consistent behavior across the Rule DocType form, the following fixes are required:

1. **`is_active` Checkbox Handler & Lock Mechanics**:
   - Fix `is_active(frm)` so that closing/canceling `show_deactivation_dialog` restores `frm.doc.is_active = 1` AND resets `frm.dirty()` state if no other fields were changed.
   - Synchronize `status` field immediately on client-side (`frm.set_value("status", "Active")` or `"Disabled"` / `"Draft"`).
   - Replace jQuery direct DOM disabling in `apply_active_lock` with standard Frappe grid read-only property enforcement (`frm.set_df_property("actions", "read_only", is_active ? 1 : 0)` and grid row read-only flags).

2. **Action Buttons Safety Guards**:
   - In `Visual Builder` primary button handler, add a dirty check (`frm.is_dirty()` check) prompting the user to save changes before opening the visual builder.
   - In `Debug Rule` and `Amend Rule`, add dirty checks prompting save prior to simulation/amendment.
   - Restrict "Amend Rule" custom button to active or submitted/historical rules where amendment is applicable.

3. **Trigger Type & Sub-Rule Contract Cleansing**:
   - Update `apply_trigger_type_contract` to include `watched_fields` in managed fields and clear its value when changing away from `DocType Event`.
   - When `exposed_as_subrule` is unchecked, clear `input_schema` and `output_schema` if hidden.

4. **Child Table Grid Lock & Refresh Integrity**:
   - Ensure `Rule Action` child grid properly inherits form read-only state during grid row expansion/modal rendering.
   - Provide a dynamic `get_query` for subrules that re-evaluates or refreshes options on form refresh.

---

## 5. Remediation & Implementation Plan

### Step 1: Frontend Script Refactoring (`flexirule/ruleflow/doctype/rule/rule.js`)
1. Refactor `is_active(frm)` and `show_deactivation_dialog(frm)`:
   - Handle dialog dismissal cleanly without leaving orphaned dirty state.
   - Sync `status` field on client-side when `is_active` changes.
2. Refactor `apply_active_lock(frm)`:
   - Use `frm.set_df_property("actions", "read_only", is_active ? 1 : 0)` alongside grid property settings.
3. Enhance Action Buttons in `refresh(frm)`:
   - Wrap `Visual Builder` route change with `frm.dirty()` check.
   - Add prompt or auto-save check before `Debug Rule` and `Amend Rule`.
4. Update `apply_trigger_type_contract(frm)`:
   - Add `watched_fields` to managed fields list and handle clearing.

### Step 2: Backend DocType Validation Sync (`flexirule/ruleflow/doctype/rule/rule.py`)
1. Verify `_sync_status` handles all transition states cleanly on save.
2. Ensure subrule schema fields are cleaned up when `exposed_as_subrule` is false.

### Step 3: Verification & Automated Testing
1. Run backend tests:
   ```bash
   bench --site test_site run-tests --module flexirule.ruleflow.tests.test_rule
   ```
2. Run frontend unit / cypress integration tests if applicable:
   ```bash
   yarn test:frontend
   ```

---

*Report prepared as part of the Flexirule DocType Consistency Audit.*
