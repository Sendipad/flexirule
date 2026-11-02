# Frappe Standard Doc Form (`Rule`) Consistency & Audit Report

**Date:** July 2026
**Target DocType:** `Rule` (Frappe Standard Doc Form & List View)
**Scope:** Client-side form handlers (`rule.js`), DocType Schema (`rule.json`), Server-side Document Class (`rule.py`), and List View Settings (`rule_list.js`).

---

## Executive Summary

An audit was conducted on the Frappe standard document form for the **`Rule`** DocType. The goal was to inspect the operational consistency, user experience (UX), state locking mechanisms, event handlers (such as the `is_active` field toggle), action buttons, child table controls, and backend status synchronization.

While the `Rule` form provides features such as dynamic field visibility based on trigger type contracts, lock-on-active governance, and custom actions for Visual Builder routing and debugging, several inconsistencies and edge-case issues were identified. This report outlines the findings, fix requirements, and a detailed step-by-step implementation plan.

---

## Audit Scope & Files Inspected

- **`flexirule/ruleflow/doctype/rule/rule.js`**: Standard form client script containing event triggers (`is_active`, `trigger_type`, `refresh`, `onload`, `before_insert`), child action handlers, and custom action buttons.
- **`flexirule/ruleflow/doctype/rule/rule.json`**: DocType metadata definition, field layouts, dependencies (`depends_on`, `mandatory_depends_on`), permissions, and naming rules.
- **`flexirule/ruleflow/doctype/rule/rule.py`**: Backend Document class handling validation (`validate_active_rule_lock`, `_sync_status`, `normalize_trigger_type_fields`, etc.), lifecycle events, and graph compilation.
- **`flexirule/ruleflow/doctype/rule/rule_list.js`**: List view settings, status indicators, custom action buttons ("Create with Builder"), and Visual Builder quick routes.

---

## Key Findings & Detailed Analysis

### Finding 1: `is_active` Toggle & Form Locking Lifecycle Inconsistencies

#### 1.1. Deactivation Dialog Cancellation State Desynchronization
- **Behavior:** When an active rule (`is_active == 1`) is unchecked by the user (`is_active` changed to `0`), `is_active(frm)` immediately forces `frm.set_value("is_active", 1)` and opens `show_deactivation_dialog(frm)`.
- **Issue:** If the user closes the dialog (via modal close icon, ESC key, or backdrop click) without selecting either "Edit Current Rule" or "Create Amendment & Edit", `frm.doc.is_active` remains set to `1`. However, `frm._was_active` is already tracking `1`. If the user subsequently edits other fields on the form and saves, server-side `validate_active_rule_lock()` in `rule.py` blocks saving with error: *"Cannot edit an Active Rule. Please set to 'Disabled' (Draft) before making changes."*
- **Fix Requirement:** The deactivation dialog must handle modal hide events (`d.on_hide`) to restore original state or prompt the user gracefully if the dialog is dismissed.

#### 1.2. Premature Form Locking on Activation before Save Validation
- **Behavior:** When a user checks `is_active` (`0` -> `1`) on an editable draft rule, `is_active(frm)` immediately invokes `apply_active_lock(frm)`, locking all form fields to read-only (`read_only = 1`) and disabling child action grid editing.
- **Issue:** If the rule fails server-side validation upon saving (e.g., missing required trigger event, invalid sub-rule target, missing start node, or variable dependency failure), the server throws an error and rejects the save. However, the client-side UI remains locked in read-only state, requiring a manual page refresh to regain edit access.
- **Fix Requirement:** Form locking should strictly reflect saved state (`frm.doc.is_active && !frm.is_dirty()`). On `is_active` change, field locking should be deferred or properly reverted if save fails or if the form is dirty.

---

### Finding 2: Primary Action Overrides and Custom Button UX

#### 2.1. Primary Action Button Overrides Standard Save Action
- **Behavior:** In `refresh(frm)`, `frm.page.set_primary_action(__("Visual Builder"), ...)` overrides the standard Frappe primary "Save" button for saved rules.
- **Issue:** When a user modifies fields on the standard form (making the form dirty), the primary action button remains "Visual Builder". Clicking "Visual Builder" triggers a route change to `/app/rule-builder/{rule_name}` without warning the user or saving unsaved form modifications, leading to silent data loss.
- **Fix Requirement:** Check `frm.is_dirty()` before primary action execution or restore the standard "Save" primary action when `frm.is_dirty()` is true.

#### 2.2. "Clear Cache" Action with Empty Document Type
- **Behavior:** In `refresh(frm)`, the "Clear Cache" action calls `clear_rule_cache(frm)` which invokes `flexirule.ruleflow.api.clear_cache` with `args: { doctype: frm.doc.document_type }`.
- **Issue:** For "Callable Event" or "Scheduler Event" rules, `frm.doc.document_type` is `null` / empty. The API call sends `{ doctype: null }`, which fails to clear the relevant runtime cache or causes unnecessary backend calls.
- **Fix Requirement:** Update `clear_rule_cache(frm)` to pass `rule_name: frm.doc.name` or fallback gracefully when `document_type` is not set.

#### 2.3. "Debug Rule" on Unsaved Form Data
- **Behavior:** "Debug Rule" opens a dialog to test the rule against a document.
- **Issue:** If the user has made unsaved edits on the form and clicks "Debug Rule", the server executes `test_rule` against the database version of the rule, ignoring the current unsaved form state. The user might expect unsaved changes to be tested.
- **Fix Requirement:** Display an alert or prompt to save unsaved form changes before launching the Debug Rule simulation.

---

### Finding 3: Child Table Grid ("Rule Action") Lock & Form Render Sync

#### 3.1. Read-Only State Sync in Child Grid Row Dialogs
- **Behavior:** `apply_active_lock(frm)` sets `grid.cannot_add_rows = is_active` and `grid.cannot_delete_rows = is_active`.
- **Issue:** When a row modal is opened in the child table (`form_render` event in `frappe.ui.form.on("Rule Action")`), individual fields inside the grid form row dialog do not explicitly re-evaluate their read-only state against `frm.doc.is_active`. If a row modal is rendered while active, certain controls or custom operation configuration buttons (`configure_operation`) remain clickable.
- **Fix Requirement:** Ensure `Rule Action`'s `form_render` and `refresh` triggers check `frm.doc.is_active` and disable interactive configuration controls (`configure_operation`) when active.

---

### Finding 4: Field Contract & Status Alignment

#### 4.1. Status Overwrite on Deactivation / Activation
- **Behavior:** `_sync_status()` in `rule.py` auto-sets `self.status = "Active"` when `is_active == 1` and `self.status = "Disabled"` / `"Draft"` when `is_active == 0`.
- **Issue:** If a rule was in `"Error"` or `"Invalid"` status due to execution failure or invalid schema, toggling `is_active` off and on overwrites the status back to `"Active"`, masking the error state until the next validation pass.
- **Fix Requirement:** Preserve `"Error"` or `"Invalid"` statuses when `is_active` is toggled if `last_error` or validation warnings persist.

---

## Remediation Requirements & Fix Overview

| Component | Issue Area | Required Fix |
| :--- | :--- | :--- |
| **`rule.js`** | `is_active` field trigger | Handle dialog dismiss/close in `show_deactivation_dialog` to reset `is_active` cleanly. Re-evaluate `apply_active_lock` after save. |
| **`rule.js`** | Primary Action | Warn on dirty form when clicking "Visual Builder" primary action button. |
| **`rule.js`** | "Clear Cache" button | Send `rule_name` or handle null `document_type` for Callable/Scheduler rules. |
| **`rule.js`** | "Debug Rule" button | Check `frm.is_dirty()` before opening debug modal and prompt to save. |
| **`rule.js`** | Child Grid `form_render` | Disable `configure_operation` button and row fields when `frm.doc.is_active` is 1. |
| **`rule.py`** | `_sync_status` | Ensure `"Error"` or `"Invalid"` statuses are preserved appropriately during activation updates if `last_error` is present. |

---

## Implementation Plan

### Phase 1: Client-Side Form Handler Enhancements (`rule.js`)
1. **Fix `show_deactivation_dialog` dismissal handling:**
   - Add `on_hide` handler to `frappe.ui.dialog` in `show_deactivation_dialog(frm)` to revert `frm.doc.is_active` to `1` and refresh fields if user cancels or closes dialog without choosing an action.
2. **Fix Primary Action & Unsaved Guard:**
   - In "Visual Builder" primary action callback, check if `frm.is_dirty()`. If dirty, show `frappe.confirm` asking user to save or discard changes before opening Visual Builder.
3. **Fix "Clear Cache" & "Debug Rule" Actions:**
   - Update `clear_rule_cache(frm)` to handle empty `document_type`.
   - Update `test_rule(frm)` to alert user if form has unsaved edits.
4. **Child Grid Row Modal Locking:**
   - Update `toggle_action_fields` or `form_render` in `Rule Action` to set `read_only` on `configure_operation` button if `frm.doc.is_active` is true.

### Phase 2: Server-Side Governance & Status Preservation (`rule.py`)
1. **Preserve Error/Invalid Statuses:**
   - Refine `_sync_status()` in `rule.py` so that setting `is_active = 1` checks if `self.last_error` exists before replacing `"Error"` or `"Invalid"` status.

### Phase 3: Verification & Test Execution
1. Verify report formatting and correctness.
2. Run automated test suite (`pytest flexirule/ruleflow/tests/test_rule.py`) to confirm zero regressions.
3. Complete pre-commit checks and submit.
