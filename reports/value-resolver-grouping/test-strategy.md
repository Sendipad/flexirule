# Comprehensive Test Strategy & Verification Plan

## 1. Test Architecture Overview

The verification strategy for FlexiRule's canonical Value Resolver system spans five distinct testing tiers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Five-Tier Test Matrix                         │
├────────────────────────────────────────────────────────────────────────┤
│ Tier 1: Frontend Component & Control Tests (Cypress / Vitest)          │
│ Tier 2: Canonical Contract & Normalization Tests (Python Unit)         │
│ Tier 3: Compiler AST & Code Generation Tests (Python Unit)             │
│ Tier 4: Runtime Execution & Security Sandbox Tests (Bench Integration)  │
│ Tier 5: Development Data Migration Regression Suite (Bench Full Suite) │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tier Specifications & Test Cases

### Tier 1: Frontend Component & Control Tests
- **Location**: `cypress/e2e/value_resolver.cy.js`
- **Scope**:
  - Verify switching family dropdowns updates available operations and loads correct Vue component.
  - Test `TextResolver.vue` concatenation, case changes, and normalization pipeline configuration.
  - Test `NumberResolver.vue` currency formatting (`format_money`) and arithmetic input.
  - Confirm `update:modelValue` emits canonical `{ "family": "...", "operation": "...", "config": { ... } }` payload.

### Tier 2: Canonical Contract & Normalization Tests
- **Location**: `flexirule/ruleflow/tests/test_value_resolver_core.py`
- **Test Class**: `TestCanonicalResolverContract`
- **Cases**:
  - `test_canonical_payload_structure`: Validate canonical JSON serialization and deserialization.
  - `test_legacy_payload_auto_normalization`: Confirm legacy `{ "kind": "normalization" }` and `{ "kind": "format", "fmt_op": "fmt_money" }` payloads convert to canonical `family` + `operation` contracts.

### Tier 3: Compiler AST & Code Generation Tests
- **Location**: `flexirule/ruleflow/tests/test_compiler.py`
- **Test Class**: `TestResolverCompiler`
- **Cases**:
  - `test_text_normalize_ast`: Verify `execute_normalization_pipeline` expression compilation.
  - `test_number_format_money_ast`: Verify `frappe.utils.fmt_money` expression compilation.
  - `test_date_calculate_ast`: Verify `frappe.utils.add_to_date` expression compilation.

### Tier 4: Runtime Execution & Security Sandbox Tests
- **Location**: `flexirule/ruleflow/tests/test_value_resolvers_complex.py`
- **Test Class**: `TestValueResolversRuntime`
- **Cases**:
  - `test_text_operations_execution`: Execute `combine`, `case`, `normalize` against document context.
  - `test_number_operations_execution`: Execute arithmetic, rounding, and `format_money` against test documents.
  - `test_collection_operations_execution`: Execute `count`, `any`, `all`, `filter`, `pluck`, `unique` with 10,000 row bounds verification.
  - `test_sandbox_dunder_blocking`: Confirm attempts to access `__class__` or execute `import` in expressions raise `PermissionError`.

### Tier 5: Development Data Migration Regression Suite
- **Command**: `bench --site test_site run-tests --app flexirule`
- **Verification**: Ensure all 47 existing test files pass without regression.
