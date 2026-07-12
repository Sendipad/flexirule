# Deep UI/UX Audit & Implementation Plan – Query Report Configuration UI
**Author:** Senior Frappe Framework Architect & Enterprise Product Designer
**Target Component:** `QueryRecordsConfig.vue` (Query Report Mode) & Integrated Reusable Controls
**Status:** Ready for Implementation

---

## 1. Executive Summary

The **Query Report Configuration UI** within FlexiRule's Rule Builder is a high-impact interface that allows users to execute standard and custom Frappe Reports, map rule-level execution contexts to report filters, and capture tabular results for downstream flow operations (e.g., loops, conditional routing, and document creation).

This audit provides a holistic, evidence-based review of the existing frontend codebase—specifically targeting `QueryRecordsConfig.vue`, `FilterGroup.vue`, `ActionSettings.vue`, and their underlying data synchronisation schemas. While the current implementation successfully supports dynamic filter fetching, it suffers from several critical issues:
* **Severe Security Liability:** Insecure usage of `frappe.dom.eval` to execute untrusted report client scripts in the builder sandbox.
* **UX/UI Inconsistencies:** Custom hand-rolled filter styling and toggles that deviate from standard Query List (`FilterGroup`) styling, native Frappe form guidelines, and the standardized value resolver paradigm.
* **Technical Debt:** Fragile `setTimeout` race conditions, redundant state-management synchronisation loops, and incomplete validation systems.

This document proposes a comprehensive, low-risk, phased roadmap to elevate the Query Report UI into a modern, secure, and enterprise-grade interface. By unifying Query Report filters with the existing `FlexValueControl` and implementing robust security sandbox wrappers, we align the component with Frappe UI/UX best practices and ensure absolute production readiness.

---

## 2. Current UI Audit

We evaluated the current implementation of Query Report mode inside `QueryRecordsConfig.vue` against Frappe UX standards, visual design principles, security profiles, and code quality.

### Strengths
* **Deferred Schema Mapping:** Real-time generation of the resolved output schema via backend dry-run (`flexirule.ruleflow.api.test_action_query`), storing columns on `resolved_output_schema` for use in subsequent actions.
* **On-Demand Loading:** Lazy loading of filters via the `load_report_filters` watcher when a report is selected in the Setup panel.
* **Unified API Facade:** Uses the standard `useActionConfig` composable to interface with Rule Builder state, keeping synchronisation logical and centralized.

### Weaknesses & UX Issues

#### A. Security Vulnerabilities (Critical Severity)
In `QueryRecordsConfig.vue` (lines 752–768), report-specific client scripts are executed using `frappe.dom.eval`:
```javascript
if (res.message?.script) {
    try {
        frappe.dom.eval(res.message.script);
        await new Promise((resolve) => setTimeout(resolve, 100));
        const settings = frappe.query_reports[report_name] || {};
        ...
```
* **Vulnerability:** Any user with permission to edit or create a Report can inject arbitrary JavaScript into the report's client script. When an administrative user opens a Rule Action referencing this report, the script executes automatically in their browser session. This represents a severe Cross-Site Scripting (XSS) and privilege escalation vector.
* **Fragile Execution:** Relying on `setTimeout(resolve, 100)` to wait for side effects from an evaluated script is highly non-deterministic and leads to race conditions on slower networks or busy rendering loops.

#### B. Information Architecture & Spatial Disorientation
* **The "Setup" vs. "Configuration" Split:** The report selection control (`reference_docname` link field) resides in the Setup/Action Settings panel (left), while the report filters live in the Configuration panel (right).
* **Empty State Disconnect:** When no report is selected, `QueryRecordsConfig.vue` displays a generic dashed empty state: `"Select a report to load its filters."` It lacks a call-to-action or indicator pointing the user toward the left-side Setup panel, leaving novice users disoriented.
* **Unlabeled/Unstructured Report Filter Table:** Unlike standard database queries which use structured headers, the report filter row uses a raw flex list without column headers.

#### C. Non-Standard Filter Control Paradigm
* Query List, Query Doc, and Exist Record use the consolidated `FilterGroup.vue` and `FlexValueControl.vue` components. This allows users to input literal values (`mode: 'static'`), pick rule context variables (`mode: 'variable'`), or write complex formulas (`mode: 'resolver'`).
* In contrast, Query Report implements a separate, custom hand-rolled toggling UI:
  - An `abc` vs. `{ }` toggle button triggers state switching between "Value" (raw input via `ControlFactory`) and "Expression" (variable input via `ComboBoxControl` wrapped in custom curly braces `{ }`).
  - This introduces parallel, redundant state tracking (`report_filter_values` and `report_filter_types`) that must be constantly synchronized with the node configuration.
  - This custom paradigm completely bypasses date math resolvers, string formatters, and other rich resolver types, preventing users from running reports with criteria like `posting_date = Today - 30 days`.

#### D. Visual Layout, Spacing, and Responsive Failures
* **Table Gutters:** The layout class `.report-filter-row` utilizes a strict grid template `grid-template-columns: 1fr 2fr` which causes layout breakage on narrow configuration panels or mobile views.
* **Checkbox Alignment:** Checkbox inputs do not align cleanly with standard labels, violating Frappe Desk guidelines which require checkboxes to be on the left with `flex-shrink: 0` and labels right beside them.
* **Styling Bloat:** Heavy usage of scoped CSS overrides (e.g., `:deep(.form-control)`) that make theme modifications difficult and increase styling maintenance costs.

---

## 3. Priority Matrix

To execute the refactoring in a structured and safe manner, we have categorized the identified opportunities based on impact and complexity.

| Category | Issue / Feature | Impact | Complexity | Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| **Critical** | **Arbitrary JS Execution** (`frappe.dom.eval` XSS vulnerability) | High | Medium | Replace with safe metadata parsing from DB/JSON schema without evaluating untrusted scripts. |
| **High** | **Unified Filter Value Paradigm** (Adopting `FlexValueControl`) | High | Medium | Migrate report filter rows to use the unified `FlexValueControl` to enable date formulas and variables. |
| **High** | **Visual Hierarchy & Labels** (Filter headers and toggle clarification) | High | Low | Add column headers (Filter Name, Context Mode, Input Value) and clean up the visual layout. |
| **Medium** | **Layout & Spacing Alignment** (Frappe Desk Checkbox standards) | Medium | Low | Refactor form layout margins and adjust checkboxes to align with native Frappe Desk styles. |
| **Medium** | **Contextual Empty/Loading States** | Medium | Low | Upgrade the empty state with a visual arrow or helpful button guiding users to the Setup panel. |
| **Medium** | **Incomplete Action Validation** | Medium | Medium | Integrate report-level filter requirements check within the node's `validate()` promise cycle. |
| **Low** | **Redundant Script Timeouts** | Low | Low | Remove `setTimeout(..., 100)` and replace with direct metadata/JSON-based configuration loading. |

---

## 4. Proposed Information Architecture

The proposed Information Architecture (IA) reframes the Query Report setup to match the rest of the database configuration screens, maintaining absolute consistency across the builder:

```
+---------------------------------------------------------------------------------+
|                               RULE BUILDER MAIN PAGE                            |
+---------------------------------------------------------------------------------+
|   LEFT PANEL (Setup / Action Settings)     |   RIGHT PANEL (Configuration)       |
|                                            |                                    |
|   1. Action Type: [ Query Records ]        |   +----------------------------+   |
|   2. Query Mode:  [ Query Report  ]        |   |    QUERY REPORT SETTINGS   |   |
|   3. Report Name: [ Gross Profit  ] <----+ |   +----------------------------+   |
|                                  | |       |   | Report Name: Gross Profit  |   |
|                                  | |       |   | (Click to configure name)  |   |
|                                  | |       |   +----------------------------+   |
|                                  | |       |   |      REPORT FILTERS        |   |
|                                  | |       |   |                            |   |
|                                  | |       |   | [X] Customer: { customer } |   |
|                                  | |       |   | [X] Date range: [Between]  |   |
|                                  | |       |   |     - From: { today - 7d } |   |
|                                  | |       |   |     - To:   { today }      |   |
|                                  | |       |   +----------------------------+   |
|                                  | +------ |   | [ Refresh Schema & Debug ] |   |
|                                            |   +----------------------------+   |
+---------------------------------------------------------------------------------+
```

### Key Changes
1. **Secondary Breadcrumb / Title Display:** Display the active report name inside the Configuration Panel header as a read-only metadata badge, letting users know exactly what report they are editing without having to constantly inspect the Setup Panel.
2. **Standardized Row Structure:** Every report filter row is treated like a standard query constraint, providing complete familiarity to users transitioning from "Query List" configurations.

---

## 5. UI/UX Improvement Recommendations

### A. Contextual Empty States
Instead of a simple static string, replace the empty state with an instructional container:
```html
<div v-if="!report_name" class="empty-mode-state text-center p-5 border-dashed rounded">
    <i class="fa fa-folder-open fa-3x text-muted mb-3 opacity-30"></i>
    <h5 class="text-strong">{{ __("No Report Selected") }}</h5>
    <p class="text-muted small">
        {{ __("Please select a target report in the Setup panel on the left to configure execution filters.") }}
    </p>
</div>
```

### B. Header Alignment and Labeling
Introduce a clear column header for Report Filters:
```html
<div class="report-filter-header-row mb-2">
    <div class="col-lbl-name">{{ __("Filter Parameter") }}</div>
    <div class="col-lbl-value">{{ __("Value Mapping / Resolver") }}</div>
</div>
```

### C. Standardized Checkbox Styling & Alignment
Align with Frappe Desk styling principles:
* Checkbox inputs should float left with `align-items: start`.
* Prevent checkbox label compression using CSS `flex-shrink: 0` on the check icon/input.
* Descriptions must reside beneath the main input in standard muted help-text formatting (`.help-box` or `.text-muted.small`).

---

## 6. Component-Level Refactoring Plan

### Target Component: `QueryRecordsConfig.vue`

#### Step 1: Secure Metadata Acquisition
Remove the risky client-side script evaluation. In Frappe, all report filters can be safely extracted from standard Report records or Report JSON configurations without executing dynamic JS scripts in the Rule Builder.
```javascript
// REFACTOR: Safe filter extraction from the backend
async function load_report_filters(report_name) {
    if (!report_name) return;
    loading.value = true;
    try {
        // Fetch structural configuration directly via safe Frappe DB calls
        const report_doc = await frappe.db.get_doc("Report", report_name);

        let filters = [];
        if (report_doc.json) {
            const data = JSON.parse(report_doc.json);
            filters = data.filters || [];
        } else if (report_doc.filters) {
            filters = report_doc.filters;
        }

        // Apply fallback standard filter extraction from report script metadata
        if (!filters.length) {
            const res = await frappe.call("flexirule.ruleflow.api.get_safe_report_filters", {
                report_name: report_name
            });
            filters = res.message || [];
        }

        report_filters.value = filters.filter(f => !f.fieldtype?.includes("Break"));

        // Populate standard values
        initialize_report_filter_values();
    } catch (e) {
        console.error("Error loading report filters securely:", e);
    } finally {
        loading.value = false;
    }
}
```

#### Step 2: Unify Filter Value Controls
Replace the custom `report_filter_types` state and separate inputs with `FlexValueControl`. This instantly enables expressions, system contexts, and math/date formula resolvers for all reports.
```html
<!-- REFACTOR: Unified FlexValueControl integration in QueryRecordsConfig -->
<div class="report-filter-table">
    <div v-for="df in visible_filters" :key="df.fieldname" class="report-filter-row">
        <div class="filter-meta">
            <label class="filter-label text-strong">{{ df.label || df.fieldname }}</label>
            <span v-if="df.reqd" class="text-danger ml-1">*</span>
            <div v-if="df.description" class="filter-desc text-muted help-box">{{ df.description }}</div>
        </div>
        <div class="filter-value-control-container">
            <FlexValueControl
                :ref="setControlRef"
                :modelValue="config.filters[df.fieldname] || { mode: 'static', value: '' }"
                :context="{
                    df: { ...df, reqd: df.reqd },
                    referenceDoctype: df.options || reference_doctype,
                }"
                :variableOptions="variable_options"
                :readOnly="readOnly"
                :showValidation="showValidation"
                @update:modelValue="(val) => update_report_filter_value(df.fieldname, val)"
            />
        </div>
    </div>
</div>
```

#### Step 3: Align Synchronisation Lifecycle
Refactor the watch/sync loop to write filter settings directly into `config.filters` as a structured dict (similar to standard Query List filters, but mapped as `{ fieldname: structured_value }`). This ensures that the backend execution engine can cleanly unpack and compile report filters.

---

## 7. Architecture & Reusability Recommendations

To prevent code duplication, enhance testability, and keep the application lightweight, we recommend the following structural adjustments:

### 1. Extract Filter Normalisation and Logic
Move the filter-fetching and schema-resolution logic out of the UI view completely and into a unified composable, e.g., `useReportConfig.js`. This allows other query action types (such as future automated reporting nodes or alert dispatchers) to reuse the secure report-loading logic.

### 2. Extend `FlexValueControl` Config Schema
Ensure that when a report filter has specialized selection criteria (such as predefined static options from a Report doctype), `FlexValueControl` seamlessly treats it as a standard native Frappe `Select` field, rendering options as standard dropdown values.

### 3. Native Report Permission Check Hook
Add a specialized validation rule in `permissions.py` (backend) to verify that if `ignore_permissions` is checked, the user is notified that Frappe Report permissions are strictly governed at the Report execution level and cannot be bypassed. This clarifies expectations right inside the UI.

---

## 8. Phased Implementation Roadmap

To maintain absolute stability and minimize regression risk, we propose a three-stage phased rollout:

### Phase 1: Security Patching & Schema Reliability (Low Risk, High Priority)
* **Goal:** Eliminate `frappe.dom.eval` and the asynchronous `setTimeout` block.
* **Tasks:**
  * Implement safe DB/JSON report-metadata loading on the frontend.
  * Implement backend validation checks to sanitize report references.
  * Ensure dry-run schema execution (`test_action_query`) fails gracefully if report configurations are incomplete.

### Phase 2: Interface Polish & IA Realignment (Medium Risk, High Priority)
* **Goal:** Modernize the layout, visual spacing, and contextual guide controls.
* **Tasks:**
  * Clean up the configuration view with structured column headers.
  * Align custom checkboxes with standard native Frappe Desk styles.
  * Add the contextual empty state guiding users to the left-side Setup panel.
  * Add clean loading animation overlays.

### Phase 3: Filter Convergence (Medium Risk, Medium Priority)
* **Goal:** Completely replace the custom `{ }` / `abc` toggle with `FlexValueControl`.
* **Tasks:**
  * Map report filters to structured `FlexValueControl` schemas.
  * Update the backend compilation flow to parse and resolve the standard structured configuration dict format.
  * Write automated Cypress/Cypress E2E tests to verify report filter criteria resolution.

---

## 9. Risks & Testing Strategy

### Key Risks
1. **Report Script Overrides:** Some custom report scripts historically manipulated default filter values inside their UI rendering files. Bypassing client JS evaluations might omit these client-side mutations in rare scenarios.
   * *Mitigation:* Ensure the backend-based fallback (`get_safe_report_filters`) parses standard Python report filters as the definitive source of truth.
2. **Backward Compatibility:** Older rule configurations stored report filters as flat literal dictionary mappings.
   * *Mitigation:* Implement a robust translation fallback in `useGraphStore.js` (`normalizeProcessConfigLegacyShape` or similar) to automatically wrap flat literal filters into `{ mode: 'static', value: val }` upon editor loading.

### Testing Strategy

#### A. Backend Unit Tests
Add a Python unit test in `test_query_records_refactor.py` verifying that report filters are securely loaded and compiled:
```python
def test_secure_report_filter_extraction(self):
    from flexirule.ruleflow.api import get_safe_report_filters
    # Mock / Fetch target report filter definitions safely
    filters = get_safe_report_filters("Gross Profit")
    self.assertTrue(len(filters) > 0)
    self.assertNotIn("Break", [f.get("fieldtype") for f in filters])
```

#### B. Cypress End-to-End Tests
Add a Cypress spec verifying the Query Report UI workflow:
```javascript
describe('Query Report UI Workflow', () => {
    it('shows safe report loading and contextual empty states', () => {
        cy.login();
        cy.visit('/desk#flexirule/rule-builder/test_rule');
        // Click Query Records Node -> Query Report Mode
        cy.get('.node-action[data-type="Query Records"]').click();
        cy.get('[data-fieldname="operation"]').click().type('Query Report{enter}');
        // Verify empty state warning
        cy.contains('No Report Selected').should('be.visible');
        // Select a report and verify filter loading
        cy.get('[data-fieldname="reference_docname"]').type('Gross Profit{enter}');
        cy.get('.report-filter-row').should('have.length.at.least', 1);
    });
});
```

---

## 10. Production Readiness Assessment

The current Query Report UI is **not production-ready** due to the critical security risk associated with `frappe.dom.eval`.

Once the refactoring plan detailed in this document is executed:
* **Security Rating:** Will increase from **Critical Risk** to **A+ Secure** (zero client script evaluations).
* **Maintainability Rating:** Will increase from **Medium** to **High** (all filtering logic unified on `FlexValueControl.vue` and standard `FilterGroup` patterns).
* **User Satisfaction Rating:** Will increase significantly by unlocking rich date formulas and system context resolvers for automated enterprise reporting.

Executing this plan is highly recommended to complete the v1.0 milestone prep for the FlexiRule Rule Builder platform.
