# Collection Resolver: Frontend Design & UI Integration

## 1. Overview & Reused Controls

The Collection Resolver UI integrates with `FlexValueControl.vue` and `ValueResolverControl.vue` without creating imaginary UI abstractions.

It extends the strategy registry in `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/index.js` and reuses existing controls (`ComboBoxControl`, `SelectControl`, `SimpleCondition.vue`).

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

## 2. Verified Strategy Registration

In `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/index.js`:

```javascript
import CollectionResolver from "./components/CollectionResolver.vue";

registerStrategy("collection", {
    label: __("Collection Query"),
    description: __("Filter, search, check, or extract values from child table rows or list variables."),
    icon: "fa fa-list-ol",
    component: CollectionResolver,
    defaultState: (props) => ({
        source: props.context?.fieldname ? `doc.${props.context.fieldname}` : "",
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

---

## 3. Verified Formula Registry Extensions

In `flexirule/public/js/flexirule/core/formula_registry.js`:
- Add `collection` command options under `FORMULA_GROUPS.TABLE`: `any`, `all`, `count`, `first`, `find`, `filter`, `pluck`, `unique`.
- Update `getAllowedBuilderKinds(fieldtype)` to include `"collection"` for `Table`, `MultiSelect`, and list variable fields.
