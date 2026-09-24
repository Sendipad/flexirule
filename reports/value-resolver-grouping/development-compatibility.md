# Development Compatibility & Pre-Release Migration Strategy

## 1. Pre-Release Compatibility Stance

FlexiRule is currently under active development and has **not yet had its first public installable release**.

Therefore:
- **Clean Architecture First**: Clean taxonomy, cohesive component boundaries, and explicit canonical contracts take precedence over preserving development-era abstractions.
- **Zero Public Breaking Change Risk**: No external customer databases or public production sites exist that require long-term legacy API deprecation cycles.
- **Development Data Integrity**: Existing test rules, JSON fixtures, and automated test suites in the development environment must continue to work seamlessly during the v1.0 migration.

---

## 2. Impact Assessment on Existing Development Artifacts

An audit of the codebase revealed the following dependencies on development-era resolver structures:

| Artifact Type | Location | Current Dependency | Impact of Canonical Transition |
| :--- | :--- | :--- | :--- |
| **Python Test Suites** | `flexirule/ruleflow/tests/test_*.py` | ~120 test cases use `{ "kind": "..." }` payloads | Handled automatically by backend load-time normalizer. |
| **JSON Fixtures** | `flexirule/fixture/` & tests | `format`, `fetch`, `normalization` references | Handled automatically by normalizer; fixtures updated in Phase 2. |
| **Frontend Stores** | `useGraphStore.js`, `useValueResolver.js` | Direct checks on `source.kind` | Replaced by `family` and `operation` checks in Phase 2. |
| **Formula Registry** | `formula_registry.js` | Hardcoded strategy array | Updated to reflect 8 canonical families. |

---

## 3. Migration Mechanism: Load/Save Normalization Layer

To ensure development tests pass without requiring a monolithic rewrite of all existing test files, FlexiRule implements a dual-mode normalization layer.

```
                    ┌────────────────────────────────────────┐
                    │       Persisted Config / Payload       │
                    └───────────────────┬────────────────────┘
                                        │
                         ValueResolver.compile_resolver_config()
                                        │
                      Is payload canonical (family/operation)?
                                   │        │
                          Yes ┌────┘        └────┐ No (Legacy kind)
                              ▼                  ▼
                    Direct Execution     Execute Normalization Layer
                                                 │
                                                 ▼
                                        Canonical Representation
```

### Read Normalization (Load Time)
When loading a rule node or compiling an expression, `ValueResolver.compile_resolver_config()` checks for legacy `kind` structures. If detected, it maps `kind` + sub-properties into `family` + `operation` + `config` before passing it to the execution strategy.

### Write Normalization (Save Time)
When saving a rule in the Visual Rule Builder, the frontend `ValueResolverControl.vue` ALWAYS emits canonical `{ "family": "...", "operation": "...", "config": { ... } }` JSON objects.

---

## 4. Migration Execution Plan for Existing Fixtures & Tests

1. **Phase 2 Step 1**: Deploy backend normalization function `normalize_resolver_payload()`.
2. **Phase 2 Step 2**: Update core tests (`test_value_resolver_core.py`, `test_value_resolvers_complex.py`) to verify both canonical and legacy payloads.
3. **Phase 2 Step 3**: Run bulk migration script over fixture JSON files to update them to canonical contract format.
4. **Phase 2 Step 4**: Verify all 47 Python test suites pass 100%.
