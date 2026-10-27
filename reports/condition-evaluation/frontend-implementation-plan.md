# Frontend Jules Task — Canonical Condition Builder

**Task type:** Frontend implementation plan for FlexiRule.  
**Depends on:** [Shared contract and handoff](README.md).  
**Baseline:** Primary specification PR #460 (`reports/condition-evaluation/README.md`).

---

## Objective

Update the visual Condition Builder so it loads, edits, validates, and saves the canonical `flexirule.condition` v1 envelope without changing its meaning. The frontend owns interaction and ephemeral UI state only. It MUST NOT become a second source of truth for operators, resolver capabilities, or execution semantics.

Keep this task frontend-only. Use the shared static JSON fixture contract (`flexirule/ruleflow/fixtures/condition_contract_fixtures.json`) so frontend unit tests run against the same fixtures as the backend.

---

## Scope Boundaries & Principles

1. **Zero Runtime Modifications in Task 0:** Task 0 freezes contracts and creates static JSON fixtures only. Implementation steps below apply to subsequent frontend execution tasks.
2. **Server-Driven Metadata:** Operator options, labels, supported operand types, and resolver capabilities MUST be fetched from the backend API/contract DTO rather than hardcoded in Vue components.
3. **Ephemeral UI IDs:** Ephemeral UI node IDs (used for Vue key rendering) MUST be stripped prior to JSON AST serialization and persistence.
4. **Preserve Malformed / Unsupported Payloads:** When loading a malformed canonical payload or unsupported schema version, the frontend MUST NOT silently reset it to an empty passing-looking group (`{ op: "and", conditions: [] }`). It MUST display a blocking diagnostic and preserve the original payload to prevent accidental data loss on save.

---

## Detailed Implementation Stages for Subsequent Frontend Tasks

### Stage F0 — Shared Fixtures and Adapter Boundaries
1. Consume `flexirule/ruleflow/fixtures/condition_contract_fixtures.json` in Node unit tests (`yarn test`).
2. Refactor `rule_builder/utils/condition_payload.js` into explicit functions:
   - `validateCanonicalEnvelope(payload)`: Strict v1 schema/version check.
   - `convertLegacyPayload(payload)`: Deterministic legacy format adapter.
   - `serializeCanonicalEnvelope(astNode)`: Strips ephemeral UI IDs before persistence.
   - `getPayloadDiagnostics(payload)`: Generates actionable diagnostics for invalid/ambiguous payloads.
3. Verify that parsing malformed or ambiguous payloads returns error diagnostics and preserves original payloads without silent reset.

**Gate F0:** Unit tests pass against shared contract fixtures; serialization cleanly strips ephemeral UI keys without mutating real AST properties.

---

### Stage F1 — Build and Edit Canonical Nodes
1. Refactor `ConditionBuilder.vue`, `ConditionGroupUI.vue`, `SimpleCondition.vue`, and `CollectionUI.vue` to edit canonical node discriminants:
   - `type: "group"` (`operator: "and" | "or"`, `children: [...]`)
   - `type: "comparison"` (`operator: "<canonical_id>"`, `left`, `right`)
   - `type: "collection_predicate"` (`quantifier: "any" | "all" | "none"`, `source`, `as`, `where`)
2. Ensure group nodes render explicit nested AND/OR structures rather than per-child logical join properties.
3. Implement `CollectionUI.vue` for collection predicates with source variable path, row alias input, and nested `where` condition subtree.

**Gate F1:** Builder loads and edits all 3 canonical node types; nested AND/OR groups render correctly; collection predicates save valid `where` ASTs.

---

### Stage F2 — Dynamic Server-Driven Metadata & FlexValue Controls
1. Fetch available business operators, labels, scopes, and resolver capabilities dynamically from the backend contract DTO API (`flexirule.ruleflow.api.get_condition_contract_dto`).
2. Integrate `FlexValueControl.vue` for both left and right operands.
3. Render typed document reference controls (`value_type: "document_reference"`) with DocType picker and document selector.
4. Enforce arity rules in UI: unary operators (`is_set`, `is_not_set`, `is_empty`, `is_not_empty`, `is_submittable`) automatically hide/disable the right operand control.

**Gate F2:** Operator dropdowns and resolver strategy choices are populated dynamically from DTO API; unary operators hide right operand; typed document references render correctly.

---

### Stage F3 — Hydration, Persistence, and Import/Export Integration
1. Update Start node trigger condition hydration and Condition action config persistence in `ConditionStep.vue`.
2. Ensure saving strips all ephemeral UI IDs recursively.
3. Ensure exporting, importing, cloning, and copy-pasting Rules preserves the `flexirule.condition` envelope without adding legacy `op/conditions` wrappers.
4. Render blocking diagnostic messages when ambiguous legacy conditions or unsupported schema versions are encountered.

**Gate F3:** Start node trigger conditions and Condition actions save valid canonical AST envelopes; cloning/importing rules round-trips cleanly without data loss.

---

### Stage F4 — End-to-End Verification & Cypress Regressions
1. Run Node frontend unit tests (`yarn test`).
2. Run targeted Cypress UI tests verifying visual builder creation, operand editing, group nesting, and persistence.
3. Confirm that backend validation error diagnostics map directly to corresponding UI AST nodes.

**Gate F4:** All frontend unit tests (`yarn test`) and Cypress builder specs pass cleanly; UI validation matches backend DTO error responses.
