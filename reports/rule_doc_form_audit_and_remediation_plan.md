# Rule Doc Form (Standard Frappe Form) Audit & Remediation Plan

## Executive Overview & Audit Scope

This document presents a comprehensive audit of the **FlexiRule Standard Frappe Doc Form** (`Rule` DocType in `flexirule/ruleflow/doctype/rule/rule.js`, `rule.json`, and `rule.py`).

While FlexiRule provides a custom Vue 3 Visual Builder canvas (`rule-builder`), the standard Frappe DocForm remains a critical interface for administrators to inspect rule metadata, manage lifecycle activation states (`is_active`), configure triggers, view execution stats, and debug rules.

Our deep inspection identified several UI/UX inconsistencies, race conditions, field lock issues, and button action mismatches in the standard `Rule` form controller (`rule.js`). This report details each finding, its root cause, impact, required fixes, and an execution plan for remediation.

---

## Detailed Findings & Root Cause Analysis

### 1. `is_active` Checkbox Interaction & Premature Form Locking (FR-FORM-001)
- **Symptom**:
  When a user toggles the `Is Active` (`is_active`) checkbox on a **new or draft** rule before saving, `apply_active_lock(frm)` immediately marks all form fields as `read_only = 1` and locks the `actions` child table grid (`cannot_add_rows = true`, `cannot_delete_rows = true`).
- **Root Cause**:
  In `rule.js`, the `is_active(frm)` event handler invokes `apply_active_lock(frm)` unconditionally whenever `frm.doc.is_active` evaluates to `1`, regardless of whether the document is new (`frm.is_new()`), unsaved, or dirty (`frm.is_dirty()`).
- **Impact**:
  Users creating a new rule or editing a draft rule who check `is_active` before clicking "Save" find all fields instantly locked in read-only mode. If validation fails or if they need to adjust any field before saving, they are blocked until they uncheck `is_active`.
- **Deactivation Dialog Logic**:
  Conversely, when unchecking `is_active` on an active rule, `is_active(frm)` correctly triggers `show_deactivation_dialog(frm)`. However, if the user cancels or closes the dialog without selecting "Edit Current Rule" or "Create Amendment & Edit", `frm.set_value("is_active", 1)` has already executed, keeping the lock intact. While this safeguards active rules, the locking state must only be enforced for **saved active documents**.

---

### 2. Primary Page Action ("Visual Builder") vs. Standard Form "Save" Button (FR-FORM-002)
- **Symptom**:
  When opening an existing Rule in standard Frappe Form view, the top-right primary action button is replaced with **"Visual Builder"**.
- **Root Cause**:
  In `rule.js` `refresh(frm)`:
  ```javascript
  frm.page.clear_primary_action();
  frm.page.set_primary_action(__("Visual Builder"), () => {
      frappe.set_route("rule-builder", frm.doc.name);
  });
  ```
- **Impact**:
  1. **Loss of Primary Save Button**: In standard Frappe form behavior, users expect the primary header button to save modified field values. Overriding primary action with `Visual Builder` leaves users without a visible primary "Save" button when editing standard form fields (e.g. Description, Priority, Watched Fields, Execution Mode, or child table actions).
  2. **Data Loss Risk**: If a user edits fields on the standard DocForm and clicks "Visual Builder", Frappe immediately routes to `rule-builder` without warning the user about unsaved dirty form changes or giving them an option to save first.

---

### 3. Custom Actions Scope & Contract Mismatches (FR-FORM-003)
In `rule.js`, custom header buttons are registered under the **Actions** dropdown:
```javascript
frm.add_custom_button(__("Amend Rule"), () => amend_rule(frm), __("Actions"));
frm.add_custom_button(__("Debug Rule"), () => test_rule(frm), __("Actions"));
frm.add_custom_button(__("Clear Cache"), () => clear_rule_cache(frm), __("Actions"));
```

- **Issue 3a: "Amend Rule" shown on Draft Rules**:
  - *Finding*: "Amend Rule" creates a new version copy (`_V2`, `_V3`). Amending a rule that is **already in Draft status** creates redundant draft copies of a draft.
  - *Fix*: "Amend Rule" should only be shown when the rule is **Active** (`frm.doc.is_active === 1`).
- **Issue 3b: "Debug Rule" Dialog Mandatory DocType for Non-DocType Triggers**:
  - *Finding*: The `test_rule(frm)` dialog defines `doctype` as a required Link field (`reqd: 1`), defaulting to `frm.doc.document_type`.
  - *Impact*: For rules with `trigger_type` set to `Callable Event` or `Scheduler Event`, `frm.doc.document_type` is `null`. The debug dialog opens with a blank `Document Type` field marked mandatory (`reqd: 1`), blocking execution with validation errors unless the user manually selects an arbitrary DocType.
  - *Fix*: Make `doctype` and `docname` in `test_rule` dialog dynamically required only when `trigger_type === "DocType Event"` or when `frm.doc.document_type` is specified.
- **Issue 3c: Missing Lifecycle Transition Buttons**:
  - *Finding*: The backend API (`flexirule.ruleflow.api.transition_rule`) supports status transitions (Activate, Disable, Unlock for Editing, Archive). The standard DocForm relied exclusively on toggling the `is_active` checkbox. Adding explicit action buttons improves usability and alignment with standard Frappe document lifecycle workflows.

---

### 4. Dashboard Headline Alert Race Condition (FR-FORM-004)
- **Symptom**:
  The orange warning banner *"This rule is active and locked. Deactivate it to edit."* disappears shortly after loading an active rule form.
- **Root Cause**:
  In `refresh(frm)`:
  1. `apply_active_lock(frm)` executes and sets `frm.dashboard.set_headline_alert(__("This rule is active and locked. Deactivate it to edit."), "orange")`.
  2. Concurrently, `update_dashboard_indicators(frm)` triggers an asynchronous API call `get_rule_stats`.
  3. When `get_rule_stats` callback resolves, `update_dashboard_indicators` calls `frm.dashboard.clear_headline()`, wiping out the orange headline banner set by `apply_active_lock`.
- **Fix**:
  Modify `update_dashboard_indicators(frm)` so it clears/updates only indicator pills (`frm.dashboard.indicator_area`) and does not invoke `frm.dashboard.clear_headline()` when the document is active and locked.

---

### 5. Action Table Grid Row Field Contract & Query Filter Synchronization (FR-FORM-005)
- **Symptom**:
  When editing rows in the `actions` child table (`Rule Action`), switching `action_type` or changing trigger options does not always clear obsolete config fields or re-query target callable rules.
- **Root Cause**:
  `toggle_action_fields` correctly queries `flexirule.contracts.getContract(type)`, but when field visibility is toggled off, `toggle_grid_row_field_display` hides elements without resetting invalid data for non-Process types (e.g. `Query Records`, `Sub-Rule`).
- **Fix**:
  Ensure field values for action-specific parameters are reset or validated when `action_type` changes, and ensure target `Sub-Rule` filters in grid queries account for activeCallable status dynamically.

---

## Remediation & Implementation Plan

### Phase 1: Standardize `is_active` Lock Behavior & Dashboard Headlines
1. Refine `apply_active_lock(frm)` in `flexirule/ruleflow/doctype/rule/rule.js`:
   - Enforce full read-only lock on form fields and actions grid **only if** `frm.doc.is_active === 1` AND document is saved (`!frm.is_new()`).
   - Allow toggling `is_active` on new/draft documents without prematurely locking form fields before save.
2. Fix headline race condition in `update_dashboard_indicators(frm)`:
   - Preserve headline alerts set by `apply_active_lock`. Clear only indicator pills (`frm.dashboard.indicator_area`) inside `update_dashboard_indicators`.

### Phase 2: Standardize Primary Action Button & Navigation
1. In `refresh(frm)`:
   - For existing saved docs (`!frm.is_new()`), add **"Visual Builder"** as a custom header button (e.g., `frm.add_custom_button(__("Visual Builder"), ..., null)` or secondary action) rather than overriding the primary "Save" button when the form is dirty.
   - When "Visual Builder" is clicked, check `if (frm.is_dirty())`: prompt the user to save changes or automatically save before navigating (`frappe.set_route("rule-builder", frm.doc.name)`).

### Phase 3: Custom Actions & Debug Dialog Cleanup
1. **"Amend Rule"**:
   - Only render `frm.add_custom_button(__("Amend Rule"), ...)` under `Actions` when `frm.doc.is_active === 1` (Active rules).
2. **"Debug Rule"**:
   - In `test_rule(frm)`:
     - If `frm.doc.trigger_type !== "DocType Event"`, make `doctype` and `docname` optional or default to relevant context.
     - Add conditional `reqd` based on `frm.doc.document_type`.
3. **"Clear Cache"**:
   - Provide feedback indicating whether DocType-specific or global rule cache was cleared.

### Phase 4: Verification & Automated Tests
1. Run frontend unit tests (`yarn test`) to verify rule dirty-state lifecycle and utility functions.
2. Run Frappe Python unit tests (`cd /home/jules/frappe-bench && bench --site test_site run-tests --app flexirule --module flexirule.ruleflow.tests.test_rule`).

---

## Summary Matrix of Form Findings & Action Items

| Issue ID | Component | Summary Finding | Corrective Action | Status |
| :--- | :--- | :--- | :--- | :--- |
| **FR-FORM-001** | `rule.js` (`is_active`) | Toggling `is_active=1` locks unsaved draft forms immediately | Restrict active lock to saved docs (`!frm.is_new()`) | Planned |
| **FR-FORM-002** | `rule.js` (`refresh`) | "Visual Builder" replaces standard "Save" primary button | Keep "Save" primary action when dirty; prompt/save on Visual Builder click | Planned |
| **FR-FORM-003a**| `rule.js` (`amend_rule`)| "Amend Rule" button displayed on Draft rules | Show "Amend Rule" only when `frm.doc.is_active === 1` | Planned |
| **FR-FORM-003b**| `rule.js` (`test_rule`) | Debug Rule requires `doctype` for Callable/Scheduler events | Make `doctype` / `docname` required only for DocType Event rules | Planned |
| **FR-FORM-004** | `rule.js` (`dashboard`) | `update_dashboard_indicators` wipes out active lock headline | Preserve headline alert in `update_dashboard_indicators` | Planned |
| **FR-FORM-005** | `rule.js` (`actions`)   | Grid fields contract toggling leaves stale data on type change | Clear inactive fields on `action_type` change | Planned |

---
