# Value Resolver Remediation Plan

This plan outlines the prioritized technical roadmap to address findings identified during the Value Resolver audit before release.

---

## Phase 1: Critical & Security Fixes (Immediate)

### Target Issues: `VR-AUDIT-001`

#### Action Items:
1. **Implement Backend Enforcement of `resolverLevel`**:
   - Update `ValueResolver.compile(val, context=None, level=None)` in `flexirule/ruleflow/core/value_resolver.py`.
   - Add level verification against `RESOLVER_LEVEL_KIND_MAP`:
     ```python
     ALLOWED_LEVEL_MAP = {
         "basic": {"system_context", "string_formula", "normalization", "format"},
         "standard": {"date_formula", "date_diff", "system_context", "string_formula", "normalization", "format"},
         "advanced": {"date_formula", "date_diff", "math_formula", "child_aggregation", "system_context", "string_formula", "normalization", "format"},
         "full": None
     }
     ```
   - Raise `frappe.ValidationError` if `config["kind"]` is disallowed for the active site/rule level.
2. **Add Unit Test for Backend Security Enforcement**:
   - Add test case in `flexirule/ruleflow/tests/test_permissions.py` verifying that unauthorized resolver kinds are rejected on backend execution.

---

## Phase 2: Contract & Data Integrity Alignment (Sprint 1)

### Target Issues: `VR-AUDIT-002`, `VR-AUDIT-003`, `VR-AUDIT-004`, `VR-AUDIT-006`

#### Action Items:
1. **Preserve `config` in Manual Mode**:
   - Refactor `FlexValueControl.vue` save handler to retain `config` or attach `{ mode: "manual", raw_expression: "..." }` when manual overrides are applied.
2. **Harmonize Strategy Parameter Defaults**:
   - Audit parameter defaults in `value_resolver/index.js` strategies and `value_resolver.py` constructors:
     - Align `DateFormulaResolver` `base_type` default to `"doc_field"` if `base_field` is specified, else `"today"`.
     - Align `MathFormulaResolver` `precision` default to `2`.
3. **Clean Up Unused Strategy Fields**:
   - Remove `link_source_type` from `fetch` strategy default state in `value_resolver/index.js`.
4. **Consolidate Legacy Mode Coercion**:
   - Centralize mode normalization into `ValueResolver.normalize_payload()` in Python and `coerceStructuredValue()` in Vue.

---

## Phase 3: Testing & Documentation Hardening (Sprint 2)

### Target Issues: `VR-AUDIT-005`

#### Action Items:
1. **Add End-to-End Cypress UI Tests**:
   - Add test suite in `cypress/integration/rule_builder.js` testing `/` slash command menu, token insertion, modal editing, and visual vs manual mode switching.
2. **Update User & Developer Documentation**:
   - Update `docs/` with explicit JSON Schema specifications for all 9 canonical resolver `config` types.
   - Publish step-by-step authoring guide for `FlexValueControl`.
