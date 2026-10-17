# Phase 2 Implementation Roadmap

## 1. Overview & Sequencing

This document provides the ordered, step-by-step implementation roadmap for executing the Value Resolver consolidation in Phase 2.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Phase 2 Implementation Progression                   │
├────────────────────────────────────────────────────────────────────────┤
│ Step 1: Explicit Legacy Adapters & Canonical Dispatch (value_resolver) │
│ Step 2: Frontend Family & Operation Registries (families.js, etc.)     │
│ Step 3: Frontend Family Vue Components (TextResolver.vue, etc.)         │
│ Step 4: FlexValueControl.vue & Control Integration                     │
│ Step 5: Test Suite Updates & Regression Execution (392 Test Methods)   │
│ Step 6: Documentation & Fixture Migration                              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Execution Steps

### Step 1: Explicit Legacy Adapters & Backend Normalizer
- **Target File**: `flexirule/ruleflow/core/value_resolver.py`
- **Actions**:
  1. Implement explicit field-level adapter functions for `date_formula`, `normalization`, `format`, `string_formula`, `child_aggregation`, and `fetch`.
  2. Implement `normalize_resolver_payload(payload)` with strict `UnrecognizedResolverPayloadError` on unmapped payloads.
  3. Implement canonical family dispatch in `ValueResolver.compile_resolver_config()`.
  4. Map `number` + `format_money` to `FormatResolver`.
- **Verification**: Run `bench --site test_site run-tests --module flexirule.ruleflow.tests.test_value_resolver_core`.

---

### Step 2: Frontend Registries & Registrations
- **Target Files**:
  - `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/families.js`
  - `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/operations.js`
  - `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/index.js`
- **Actions**:
  1. Create `families.js` registering the core families (Date, Text, Number, Collection, Lookup, System).
  2. Create `operations.js` mapping all verified existing operations to their respective families.
  3. Refactor `index.js` to expose family-level strategy lookup functions.
- **Verification**: Verify frontend build with `yarn build`.

---

### Step 3: Frontend Family Vue Components
- **Target Directory**: `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/`
- **Actions**:
  1. Build `TextResolver.vue` (consolidates `StringFormulaResolver` and `NormalizationResolver`).
  2. Build `NumberResolver.vue` (includes arithmetic, rounding, and `format_money`).
  3. Build `DateResolver.vue` (consolidates date calculation, diff, and date formatting).
  4. Build `LookupResolver.vue` and `SystemResolver.vue`.
  5. Refactor `CollectionResolver.vue` to support both predicate filtering and child aggregation operations.
- **Verification**: Inspect components in Vue DevTools and run Cypress UI tests.

---

### Step 4: `FlexValueControl.vue` & Control Integration
- **Target Files**:
  - `flexirule/public/js/flexirule/rule_builder/controls/ValueResolverControl.vue`
  - `flexirule/public/js/flexirule/rule_builder/controls/FlexValueControl.vue`
  - `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/useValueResolver.js`
- **Actions**:
  1. Update `useValueResolver.js` to handle canonical payload state hydration and operation switching.
  2. Update `ValueResolverControl.vue` template to render family selector and dynamic family component.
- **Verification**: Verify visual node configuration in Rule Builder canvas.

---

### Step 5: Test Suite Updates & Regression Execution
- **Target Directory**: `flexirule/ruleflow/tests/`
- **Actions**:
  1. Add `TestCanonicalResolverContract` class to `test_value_resolver_core.py`.
  2. Add runtime tests for canonical families in `test_value_resolvers_complex.py`.
  3. Execute full backend test suite (392 methods across 42 test files).
- **Verification**: Run `bench --site test_site run-tests --app flexirule`.

---

### Step 6: Documentation & Fixture Migration
- **Target Files**: `flexirule/docs/` and `flexirule/fixture/`
- **Actions**:
  1. Execute bulk fixture update script.
  2. Update markdown documentation in `docs/`.
- **Verification**: Confirm `git status` clean and pre-commit linters pass.
