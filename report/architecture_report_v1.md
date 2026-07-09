# FlexiRule Architecture Report & Migration Plan (v1.0)

## Phase 1: Analysis of Current Implementation

### 1. Application Initialization & Mounting
- **Page Entry**: The `rule-builder` Frappe Page (`rule_builder.js`) acts as the entry point. It uses `frappe.ui.make_app_page` to initialize the chrome and then dynamically requires `rule_builder.bundle.js`.
- **Controller**: The `frappe.ui.RuleBuilder` class in the bundle is the "Controller". It:
    - Receives the `page` object and `wrapper`.
    - Initializes Pinia and mounts the Vue 3 app (`App.vue`).
    - Holds references to `ruleStore` and `uiStore`.
- **Vue Mounting**: The app is mounted to `.layout-main-section`.

### 2. Page API & Toolbar Implementation
- **Access**: The `RuleBuilder` class accesses the Page API via `this.page`.
- **Toolbar Buttons**: Primary (Save) and secondary (Reset, Draft/Active toggle, Debug) buttons are created in `setup_page()`.
- **State Coupling**:
    - The controller uses manual Vue `watch` calls on `ruleStore.is_dirty` and `ruleStore.rule_doc.is_active`.
    - It also uses Pinia `$subscribe` and `$onAction` to trigger UI updates like `update_status_button` and `update_test_ui`.
- **DOM Manipulation**: The status indicators (Active/Draft/Sub-Rule) are currently injected into the title area using jQuery DOM manipulation (`this.page.$title_area.find(...)`).

### 3. Event & Data Flow
1. **User Action**: User clicks a button in a Vue component.
2. **Store Action**: Component calls a Pinia store action (e.g., `graphStore.addNode`).
3. **State Change**: Store updates state, triggering `is_dirty` computed property.
4. **Controller Watcher**: `RuleBuilder` class detects change via `watch`.
5. **Page Update**: Controller calls `page.set_indicator` or `page.set_primary_action`.

---

## Phase 2: Frappe Best Practices (Source of Truth)

### 1. Form Builder / Workflow Builder Patterns
- **Standardization**: Frappe uses a JS class (e.g., `WorkflowBuilder`) as a wrapper for the Vue app.
- **Reactivity**:
    - They use `watchEffect` inside the controller to keep the Frappe Page synchronized with the store.
    - **Dirty State**: `watchEffect(() => { if (store.dirty) frm.dirty(); })`.
- **Toolbar**:
    - Primary actions are set once or updated reactively.
    - They avoid complex manual DOM manipulation for titles, preferring standard `page.set_title` and `page.set_indicator`.

### 2. Key Findings
- **Single Source of Truth**: The Pinia store is the source of truth for the *application state*, while the Controller is the source of truth for the *integration*.
- **No Direct API in Vue**: Vue components are "dumb" regarding the Frappe Page; they only know about the store.

---

## Phase 3: Architecture Comparison

| Feature | Current FlexiRule | Frappe Standard (v15) | Recommendation |
| :--- | :--- | :--- | :--- |
| **Toolbar Sync** | Fragmented `watch` + `$subscribe` | Centralized `watchEffect` | **Adopt `watchEffect`** |
| **Status Display** | Manual jQuery DOM injection | `page.set_indicator` | **Use Standard Indicators** |
| **Primary Action** | Fixed label ("Save Rule") | Dynamic based on context | **Make Dynamic** |
| **Breadcrumbs** | Handled in Pinia Store | Handled in Controller | **Move to Controller** |

---

## Phase 4: Migration Design

### 1. Reactive Integration Strategy
The `RuleBuilder` controller will implement a single `watch_changes()` method using Vue's `watchEffect`. This effect will track:
- `ruleStore.is_dirty`
- `ruleStore.is_active`
- `uiStore.has_test_path`
- `ruleStore.rule_doc.rule_name`

When any of these change, the controller will call a `refresh_page()` method that updates the title, indicators, and toolbar in one pass.

### 2. State Ownership
- **Pinia**: Owns the "Dirty" flag, the "Active" status, and the "Has Results" state.
- **Controller**: Owns the mapping of that state to Frappe Page API calls.

---

## Phase 5: Implementation Plan

### 1. Files to Modify
- `flexirule/public/js/flexirule/rule_builder/rule_builder.js`:
    - Remove fragmented watchers.
    - Implement `watch_changes()` and `refresh_toolbar()`.
    - Clean up `setup_page()`.
- `flexirule/public/js/flexirule/rule_builder/stores/useRuleStore.js`:
    - Remove `setup_breadcrumbs` and any other Page API calls.

### 2. New Update Flow
1. **Change** happens in Store.
2. **`watchEffect`** in `RuleBuilder` is triggered automatically.
3. **`refresh_toolbar()`** clears and re-adds actions based on current store state.
4. **`set_indicator()`** updates the status (Draft/Active) and dirty state.

### 3. Risks & Testing
- **Risk**: Frequent toolbar clearing might cause a slight flicker.
    - *Mitigation*: Only clear/re-add if the relevant state actually changed, or rely on Frappe's efficient DOM handling.
- **Testing**:
    - Verify "Save" button appears/disappears correctly.
    - Verify "Activate" button replaces "Save" when not dirty.
    - Verify "Edit" (Unlock) button appears when Active.
