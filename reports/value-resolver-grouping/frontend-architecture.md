# Frontend Architecture & Control Specifications

## 1. Vue Component Structure

The frontend Value Resolver architecture is restructured into **8 cohesive family components** located under `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/`:

```
flexirule/public/js/flexirule/rule_builder/controls/value_resolver/
├── index.js                     # Strategy and Family Registries
├── families.js                  # 8 Family Definitions & Metadata
├── operations.js                # Operation Definitions Registry
├── useValueResolver.js          # Main Composable for Resolver Controls
├── ValueResolverControl.vue     # Top-Level Resolver Wrapper
└── components/
    ├── DateResolver.vue         # Family 1: Date & Time Operations
    ├── TextResolver.vue         # Family 2: Text Operations
    ├── NumberResolver.vue       # Family 3: Numeric & Currency Operations
    ├── CollectionResolver.vue   # Family 4: Collection & Child Table Operations
    ├── LookupResolver.vue       # Family 5: Link Field & Record Lookups
    ├── SystemResolver.vue       # Family 6: System Context Operations
    ├── ConversionResolver.vue   # Family 7: Type Conversion Operations
    └── ConditionalResolver.vue  # Family 8: Inline Branching Operations
```

---

## 2. Operation Registry Design (`operations.js`)

Each family component is driven by a declarative operation registry. The registry defines available operations, UI labels, configuration fields, validation logic, and code compilation strategy.

```javascript
// Example Operation Registry for Text Family
export const TEXT_OPERATIONS = {
  combine: {
    label: "Combine Text",
    description: "Concatenate multiple text fields or literal strings",
    fields: [
      { name: "delimiter", type: "string", default: "" },
      { name: "items", type: "array", default: [] }
    ],
    compileToCode: (config) => `"".join([${config.items.join(", ")}])`,
    validate: (config) => ({ isValid: config.items.length > 0 })
  },
  normalize: {
    label: "Clean & Normalize",
    description: "Apply pipeline transformations (trim, slugify, remove accents)",
    fields: [
      { name: "source_field", type: "field", required: true },
      { name: "pipeline", type: "multiselect", options: ["trim", "slug", "snake", "lower", "upper"] }
    ],
    compileToCode: (config) => `execute_normalization_pipeline(${config.source_field}, ${JSON.stringify(config.pipeline)})`,
    validate: (config) => ({ isValid: !!config.source_field })
  }
};
```

---

## 3. `FlexValueControl.vue` Integration & State Lifecycle

`FlexValueControl.vue` serves as the primary value input control throughout the Rule Builder canvas (used in Assignment nodes, Condition nodes, and Sub-rule parameters).

```
                      ┌────────────────────────────────────────┐
                      │          FlexValueControl.vue          │
                      └───────────────────┬────────────────────┘
                                          │
                            ValueResolverControl.vue
                                          │
                       ┌──────────────────┴──────────────────┐
                       ▼                                     ▼
            Family Selector Dropdown             Family Component Loader
          (Date, Text, Number, etc.)               (e.g., TextResolver)
                                                             │
                                                  ┌──────────┴──────────┐
                                                  ▼                     ▼
                                          Operation Dropdown    Operation Config UI
```

### State Management & Switching Lifecycle

1. **Initialization**:
   When `ValueResolverControl.vue` receives a `modelValue`, `useValueResolver` inspects whether it is in canonical format (`family + operation + config`) or legacy format (`kind`). It hydrates local reactive state accordingly.

2. **Family Switching**:
   When a user switches the family dropdown (e.g. from **Text** to **Number**):
   - Local state is reset to the default state of the target family's default operation.
   - The reactive `isValid` status is re-evaluated.
   - The parent control is notified via `update:modelValue`.

3. **Operation Switching**:
   When a user changes the operation within a family component (e.g. from `combine` to `normalize` in `TextResolver.vue`):
   - Common fields (like `source_field`) are preserved where applicable.
   - Operation-specific default parameters are initialized.
   - Reactive validation is executed immediately.
