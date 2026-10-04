# Task Specification: Navigable Field Browsing Rollout Across FlexiRule

## Status & Overview
- **Feature Name**: Navigable Field & Hierarchy Browsing
- **Foundation Status**: Completed in Query Records (`ComboBoxControl.vue` + `useNavigableFields.js`)
- **Scope**: Roll out generic navigable browsing across all field-selection controls in FlexiRule.

---

## 1. Established Foundation Architecture

The field browsing foundation is built on a clean separation of concerns:

### Generic Control Layer (`ComboBoxControl.vue`)
- **Props**:
  - `navigable`: `{ type: Boolean, default: false }`
  - `navStack`: `{ type: Array, default: () => [] }`
- **Events**:
  - `@navigate`: Emits `(option)` when user clicks navigation arrow `→` or presses `ArrowRight`.
  - `@back`: Emits `(stackIndex)` when user clicks back button/breadcrumb or presses `ArrowLeft`/`Backspace`.
- **UI & UX Capabilities**:
  - Popover breadcrumb header displaying the navigation stack (`[Parent] / [Child]`).
  - Navigation affordance button (`→`) on navigable option rows.
  - Parent path selection matching: parent relationship options (e.g. `accounts`) display selected checkmarks and active hover states when a nested child field (`accounts.exchange_rate`) is selected.
  - Auto-navigation and auto-scroll (`scrollToActive()`) on dropdown open to highlight selected values directly.
  - Full RTL language support for chevron and back button icons.
  - Full label translation via `__(...)`.

### Metadata & Option Adapter Layer (`useNavigableFields.js`)
- Transforms Frappe DocType metadata into generic ComboBox options.
- Differentiates Link fields (`navType: "link"`) and Child Table fields (`navType: "table"`).
- Automatically resolves nested dotted field path labels (e.g., `accounts.exchange_rate` -> `Accounts: Exchange Rate (accounts.exchange_rate)`).
- Manages navigation stack state (`navStack`) and asynchronous metadata pre-fetching via `useMetaStore`.

---

## 2. Future Rollout Roadmap

The goal of this future task is to enable `:navigable="true"` and `useNavigableFields` across all remaining field selectors in FlexiRule.

### Phase 1: Action Configuration Components
1. **Assignment Action (`AssignmentConfig.vue`)**:
   - Target field selection.
   - Source value field selector for parent and child table references.
2. **Document Action (`DocumentActionConfig.vue`)**:
   - Dynamic field mapping when creating or updating document records (e.g., ToDo, Comment, Sales Invoice).
3. **Sub-Rule Mapping (`SubRuleConfig.vue`)**:
   - Sub-rule input parameter binding to parent rule fields and child table rows.

### Phase 2: Controls & Value Resolvers
1. **Lookup Resolver (`LookupResolver.vue`)**:
   - Field selection when fetching records from static or dynamic Link DocTypes.
2. **Collection Resolver (`CollectionResolver.vue`)**:
   - Field selection for collection operations (`pluck`, `filter`, `sum`, `avg`, `first`, `unique`).
3. **Resource Mapper Control (`ResourceMapperControl.vue`)**:
   - Source and target field mapping tables.
4. **Formula & Text Resolvers**:
   - `MathFormulaResolver.vue` and `TextTransformResolver.vue` field pickers.

---

## 3. Implementation Guidelines for Future Rollout

When enabling navigation on a new control:
1. Initialize `const nav = useNavigableFields(doctype, modelValue);` in the component.
2. Bind `ComboBoxControl`:
   ```html
   <ComboBoxControl
       :df="{ fieldtype: 'FieldPicker' }"
       :options="nav.currentFields.value"
       :modelValue="modelValue"
       :navigable="true"
       :navStack="nav.navStack.value"
       @navigate="nav.handleNavigate"
       @back="nav.handleBack"
       @update:modelValue="(val) => { emit('update:modelValue', val); nav.resetStack(); }"
   />
   ```
3. Ensure no backend configuration contracts are modified unless explicitly required.
