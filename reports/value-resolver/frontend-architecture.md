# Frontend Resolver Architecture

## Pipeline Overview

The frontend Value Resolver system provides a rich, inline Tiptap editor experience embedded within `FlexValueControl.vue`, allowing users to seamlessly transition between static inputs, variable references (`@`), and advanced formula resolvers (`/`).

The component chain flows as follows:

```
FlexValueControl.vue (Entry point with Static / Dynamic mode toggle)
    ↓
Tiptap Editor (`@` for variables, `/` for command palette)
    ↓
formula_registry.js (Filters commands and formulas by fieldtype)
    ↓
Slash Command Selection (e.g. `/` → Math Formula)
    ↓
resolverToken Insertion into ProseMirror Document
    ↓
ResolverTokenView.vue NodeView
    ↓
ValueResolverControl.vue (Popover or Inline builder)
    ↓
useValueResolver.js Composable + Strategy Registration (index.js / strategies.js)
    ↓
compileToCode() & compileToLabel()
    ↓
Token attributes updated in Tiptap: { config, label, expression }
    ↓
serialize() → coerceStructuredValue()
    ↓
Emitted modelValue payload: { mode: "resolver", value: "...", config: {...} }
```

---

## Detailed Component Responsibilities

### 1. `FlexValueControl.vue`
- **Responsibility**: Main user-facing control. Dynamically switches between Static mode (`ControlFactory`, `MultiSelectList`) and Dynamic mode (Tiptap editor). Controls the modal editor overlay.
- **Input Props**:
  - `modelValue`: Plain value, variable string, or structured object `{ mode, value, config }`.
  - `context`: Structured field metadata (`df`), reference DocType, operator, callbacks.
  - `variableOptions`: Available variable list for `@` autocomplete.
  - `readOnly` / `read_only`: Disables editing.
- **Static Mode Support**:
  - Supported for all fieldtypes EXCEPT pure text editors (`Code`, `Text Editor`, `JSON`).
  - If field operator is `in`, `not in`, or field is a multi-select link type, renders `MultiSelectList`.
  - Otherwise renders `ControlFactory` for standard inputs.
- **Keydown Interception**:
  - `onStaticKeydown`: Pressing `@` or `/` in static mode automatically flips `isDynamicMode` to `true` and inserts the key into the Tiptap editor.

---

### 2. Slash Command & Variable Triggers (`formula_registry.js`)
- **Trigger `@`**:
  - Invokes `VariableTrigger` extension configured with `PluginKey`.
  - Calls `availableVariableOptions` computed property.
  - Filters `doc.*`, `vars.*`, and scope variables.
  - Command callback inserts a `variableToken` node into the editor:
    ```json
    { "type": "variableToken", "attrs": { "path": "doc.status", "label": "Status" } }
    ```
- **Trigger `/`**:
  - Invokes `CommandTrigger` extension.
  - Executes `getCommandsForFieldtype(fieldType)` and `getFormulasForFieldtype(fieldType)`.
  - Maps commands and formula definitions into menu items.
  - Command callback checks `allowedBuilderKinds` and inserts a `resolverToken` node:
    ```json
    { "type": "resolverToken", "attrs": { "config": { "kind": "math_formula" } } }
    ```

---

### 3. `ValueResolverControl.vue` & `useValueResolver.js`
- **Responsibility**: Provides the category dropdown (`ComboBoxControl`) and dynamically mounts the Vue strategy configuration component (e.g., `MathFormulaResolver.vue`).
- **View Modes**:
  - `popover` (default): Floating token trigger that opens popover dropdown via `useFloatingDropdown`.
  - `inline`: Used inside the Token Editor Modal.
- **Composable State Management**:
  - `useValueResolver` maintains `localState`, `activeKind`, `isValid`, and `errors`.
  - Reactively re-calculates code and label whenever `localState` or `activeKind` mutates:
    ```javascript
    const config = { ...newState, kind: newKind };
    const label = strategy.compileToLabel(config);
    const expression = strategy.compileToCode(config);
    ```

---

### 4. Token Editor Modal & Visual vs Manual Modes

When a user clicks an existing `resolverToken` in the editor or clicks the JSON/Code preview button, `openTokenEditor()` opens a modal:

```
+-------------------------------------------------------------------+
|  Configure Formula / Resolver                                  X  |
+-------------------------------------------------------------------+
|  Edit Mode: [ (o) Visual  |  ( ) Manual ]                        |
|                                                                   |
|  [ Visual Builder Component: ValueResolverControl ]               |
|  - Formula Type: [ Math Formula v ]                              |
|  - Field A: [ doc.amount ]                                       |
|  - Operator: [ * ]                                               |
|  - Constant B: [ 100 ]                                           |
|                                                                   |
|  Preview: {frappe.utils.flt(doc.amount * 100, 2)}                 |
+-------------------------------------------------------------------+
|                                            [ Cancel ]  [ Save ]   |
+-------------------------------------------------------------------+
```

- **Visual Mode**:
  - Binds to `ValueResolverControl.vue` in `inline` mode.
  - Validates `config` against strategy rules. Disables "Save" if `isValid` is `false`.
- **Manual Mode**:
  - Exposes raw `expression` textarea (e.g. `frappe.utils.add_days(doc.posting_date, 7)`).
  - Displays variable pills for quick insertion.
  - Nulls `config` on save (`tokenDraftAttrs.value.config = null`), forcing backend to evaluate via `SafeEvalResolver`.

---

### 5. Level Restriction Filtering (`resolverLevel`)

Level filtering is managed via `RESOLVER_LEVEL_KIND_MAP` in `FlexValueControl.vue`:

```javascript
const RESOLVER_LEVEL_KIND_MAP = {
    basic: ["system_context", "string_formula", "normalization", "format"],
    standard: ["date_formula", "date_diff", "system_context", "string_formula", "normalization", "format"],
    advanced: ["date_formula", "date_diff", "math_formula", "child_aggregation", "system_context", "string_formula", "normalization", "format"],
    full: null // Allows all
};
```

The computed property `allowedBuilderKinds` intersects fieldtype allowed kinds with `RESOLVER_LEVEL_KIND_MAP[configuredResolverLevel]`.
*(Note: As identified in `VR-AUDIT-001`, this restriction is enforced purely in the Vue frontend).*
