# Phase 2 Implementation Roadmap

## 1. Overview & Sequencing

This document provides the ordered, step-by-step implementation roadmap for executing the Value Resolver consolidation in Phase 2.

Each step specifies target files, required modifications, and verification gates.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Phase 2 Implementation Progression                   │
├────────────────────────────────────────────────────────────────────────┤
│ Step 1: Backend Normalizer & Canonical Dispatch (value_resolver.py)    │
│ Step 2: Frontend Family & Operation Registries (families.js, etc.)    │
│ Step 3: Frontend Family Vue Components (TextResolver.vue, etc.)        │
│ Step 4: FlexValueControl.vue & Control Integration                     │
│ Step 5: Test Suite Updates & Regression Run                           │
│ Step 6: Documentation & Fixture Migration                              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Execution Steps

### Step 1: Backend Normalizer & Canonical Dispatch Layer
- **Target File**: `flexirule/ruleflow/core/value_resolver.py`
- **Actions**:
  1. Implement `normalize_resolver_payload(payload)` to convert legacy `{ "kind": "..." }` dicts into canonical `{ "family": "...", "operation": "...", "config": { ... } }`.
  2. Implement `_compile_canonical_family()` in `ValueResolver.compile_resolver_config()`.
  3. Map `number` + `format_money` to `FormatResolver`.
- **Verification**: Run `bench --site test_site run-tests --module flexirule.ruleflow.tests.test_value_resolver_core`.

---

### Step 2: Frontend Registries & Registrations
- **Target Files**:
  - `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/families.js`
  - `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/operations.js`
  - `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/index.js`
- **Actions**:
  1. Create `families.js` registering the 8 core families (Date, Text, Number, Collection, Lookup, System, Conversion, Conditional).
  2. Create `operations.js` mapping all operations to their respective families.
  3. Refactor `index.js` to expose family-level strategy lookup functions.
- **Verification**: Verify frontend build with `yarn build`.

---

### Step 3: Frontend Family Vue Components
- **Target Directory**: `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/`
- **Actions**:
  1. Build `TextResolver.vue` (consolidates `StringFormulaResolver` and `NormalizationResolver`).
  2. Build `NumberResolver.vue` (includes arithmetic, rounding, and `format_money`).
  3. Build `DateResolver.vue` (consolidates date calculation, diff, and date formatting).
  4. Build `LookupResolver.vue`, `SystemResolver.vue`, `ConversionResolver.vue`, `ConditionalResolver.vue`.
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
  2. Add runtime tests for new canonical families in `test_value_resolvers_complex.py`.
  3. Execute full backend test suite.
- **Verification**: Run `bench --site test_site run-tests --app flexirule`.

---

### Step 6: Documentation & Fixture Migration
- **Target Files**: `flexirule/docs/` and `flexirule/fixture/`
- **Actions**:
  1. Execute bulk fixture update script.
  2. Update markdown documentation in `docs/`.
- **Verification**: Confirm `git status` clean and pre-commit linters pass.
