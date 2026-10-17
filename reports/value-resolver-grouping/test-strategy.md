# Comprehensive Test Strategy & Verification Metrics

## 1. Verified Repository Test Metrics

Following an automated repository audit:
- **Exact Test Files Count**: **42 Python test files** under `flexirule/ruleflow/tests/`.
- **Exact Test Methods Count**: **392 test methods** (`def test_*`).

---

## 2. Five-Tier Test Matrix for Phase 2

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Five-Tier Test Matrix                         │
├────────────────────────────────────────────────────────────────────────┤
│ Tier 1: Frontend Component & Control Tests (Cypress UI)                │
│ Tier 2: Canonical Contract & Adapter Tests (Python Unit)               │
│ Tier 3: Compiler AST & Expression Generation Tests (Python Unit)       │
│ Tier 4: Runtime Resolution & Security Sandbox Tests (Bench Integration)│
│ Tier 5: Full Regression Suite Run (392 Methods across 42 Test Files)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Test Tier Specifications

### Tier 1: Frontend Component & Control Tests
- **Target File**: `cypress/e2e/value_resolver.cy.js`
- **Cases**:
  - Test family dropdown selection (`date`, `text`, `number`, `collection`, `lookup`, `system`).
  - Test `TextResolver.vue` concatenation, casing, and normalization pipeline UI.
  - Test `NumberResolver.vue` arithmetic and currency formatting (`format_money`) UI.
  - Confirm control emits canonical payload `{ "family": "...", "operation": "...", "config": { ... } }`.

### Tier 2: Canonical Contract & Adapter Tests
- **Target File**: `flexirule/ruleflow/tests/test_value_resolver_core.py`
- **Test Class**: `TestCanonicalResolverContract`
- **Cases**:
  - `test_canonical_payload_structure`: Validate canonical JSON serialization and deserialization.
  - `test_legacy_adapters`: Verify explicit field-level adapter mappings for `date_formula`, `normalization`, `format`, `string_formula`, `child_aggregation`, and `fetch`.
  - `test_unrecognized_payload_rejection`: Confirm unmapped legacy payloads raise `UnrecognizedResolverPayloadError`.

### Tier 3: Compiler AST & Expression Generation Tests
- **Target File**: `flexirule/ruleflow/tests/test_compiler.py`
- **Cases**:
  - Verify AST expression generation for `text.normalize`, `number.format_money`, `date.calculate`, and `date.diff`.

### Tier 4: Runtime Resolution & Security Sandbox Tests
- **Target File**: `flexirule/ruleflow/tests/test_value_resolvers_complex.py`
- **Cases**:
  - Execute `combine`, `case`, `normalize` against document context.
  - Execute `calculate`, `round`, and `format_money` against test documents.
  - Execute `count`, `any`, `all`, `filter`, `pluck`, `unique` with 10,000 row limit check.
  - Verify AST sandbox blocks dunder attribute access (`__class__`).

### Tier 5: Repository Regression Suite Run
- **Command**: `bench --site test_site run-tests --app flexirule`
- **Gate**: All 392 test methods across 42 test files must pass with zero regression.
