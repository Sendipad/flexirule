# Collection Resolver: Frontend Design & UI Integration

## 1. Overview
The Collection Resolver UI integrates smoothly with standard FlexiRule controls: `FlexValueControl.vue` and `ValueResolverControl.vue`.

```
                  ┌────────────────────────────────────────┐
                  │          FlexValueControl.vue          │
                  └───────────────────┬────────────────────┘
                                      │
                         ValueResolverControl.vue
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
            ComboBoxControl (Kind)       CollectionResolver.vue
                                                   │
                                      ┌────────────┴────────────┐
                                      ▼                         ▼
                          Source & Operation Selects   Condition / Target Field
```

---

## 2. Component Specifications

### 2.1 Strategy Registration (`flexirule/public/js/flexirule/rule_builder/controls/value_resolver/index.js`)
```javascript
import CollectionResolver from "./components/CollectionResolver.vue";

registerStrategy("collection", {
    label: __("Collection Query"),
    description: __("Filter, search, check, or extract values from child table rows or list variables."),
    icon: "fa fa-list-ol",
    component: CollectionResolver,
    defaultState: (props) => ({
        source: props.context?.fieldname || "",
        operation: "any",
        target_field: "",
        condition: null,
    }),
    compileToCode: (item) => {
        const src = item.source || "doc.items";
        const op = (item.operation || "any").toUpperCase();
        if (["PLUCK", "UNIQUE"].includes(op)) {
            return `{${op}(${src}, "${item.target_field || ""}")}`;
        }
        return `{${op}(${src})}`;
    },
    compileToLabel: (item) => {
        const op = (item.operation || "any").toUpperCase();
        const src = item.source || "?";
        if (["PLUCK", "UNIQUE"].includes(op)) {
            return `${op}(${src}.${item.target_field || "?"})`;
        }
        return `${op}(${src})`;
    },
    validate: (item) => {
        const errors = [];
        if (!item.source) errors.push(__("Source collection is required"));
        if (["pluck", "unique"].includes(item.operation) && !item.target_field) {
            errors.push(__("Target field is required for this operation"));
        }
        return { isValid: errors.length === 0, errors };
    }
});
```

### 2.2 Control Component Architecture (`CollectionResolver.vue`)
The component layout will present:
1. **Source Collection Dropdown** (`ComboBoxControl` populated with child table fields from `metaStore` and `vars`).
2. **Operation Selector** (`SelectControl` with operations: `Count`, `Any`, `All`, `First`, `Last`, `Find`, `Filter`, `Pluck`, `Unique`).
3. **Target Field Selector** (rendered when `operation` is `pluck` or `unique`).
4. **Row Condition Builder** (rendered when operation accepts a condition; embeds `SimpleCondition.vue` or filter row with `row.` field suggestions).

---

## 3. Slash Commands & Formula Registry
In `flexirule/public/js/flexirule/core/formula_registry.js`:
- Add `collection` command under `FORMULA_GROUPS.TABLE`:
```javascript
{ id: "any", label: "any", description: "Check if any row matches condition" },
{ id: "all", label: "all", description: "Check if all rows match condition" },
{ id: "find", label: "find", description: "Find first row matching condition" },
{ id: "filter", label: "filter", description: "Filter collection rows by condition" },
{ id: "pluck", label: "pluck", description: "Extract list of field values from rows" },
{ id: "unique", label: "unique", description: "Extract distinct list of field values" }
```
- Update `getAllowedBuilderKinds(fieldtype)` to include `"collection"` for `Table`, `MultiSelect`, and list variable fields.
