# Frontend Jules Task — Canonical Condition Builder

**Task type:** Frontend implementation plan for FlexiRule.  
**Depends on:** [Shared contract and handoff](README.md).  
**Baseline:** Primary specification PR #460 (`reports/condition-evaluation/README.md`).

## Objective

Update the visual Condition Builder so it loads, edits, validates, and saves the canonical `flexirule.condition` v1 envelope without changing its meaning. The frontend owns interaction and ephemeral UI state only. It MUST NOT become a second source of truth for operators, resolver capabilities, or execution semantics.

Keep this task frontend-only. Use the shared static JSON fixture contract (`flexirule/ruleflow/fixtures/condition_contract_fixtures.json`) so frontend unit tests run against the same fixtures as the backend.

## Scope Boundaries & Principles

1. **Zero Runtime Modifications in Task 0:** Task 0 freezes contracts and creates static JSON fixtures only. Implementation steps below apply to subsequent frontend execution tasks.
2. **Server-Driven Metadata:** Operator options, labels, supported operand types, and resolver capabilities MUST be fetched from the backend API/contract DTO rather than hardcoded in Vue components.
3. **Ephemeral UI IDs:** Ephemeral UI node IDs (used for Vue key rendering) MUST be stripped prior to JSON AST serialization and persistence.
4. **Preserve Malformed / Unsupported Payloads:** When loading a malformed canonical payload or unsupported schema version, the frontend MUST NOT silently reset it to an empty passing-looking group (`{ op: "and", conditions: [] }`). It MUST display a blocking diagnostic and preserve the original payload to prevent accidental data loss on save.

---

## Detailed Implementation Stages for Subsequent Frontend Task

### Stage F0 — Shared Fixtures and Adapter Boundaries

1. Consume `flexirule/ruleflow/fixtures/condition_contract_fixtures.json` in frontend unit tests (`npm test`).
2. Refactor `rule_builder/utils/condition_payload.js` into explicit functions:
   - `validateCanonicalEnvelope(payload)`: Strict v1 schema/version check.
   - `convertLegacyPayload(payload)`: Deterministic legacy format adapter.
   - `serializeCanonicalEnvelope(astNode)`: Strips ephemeral UI IDs before persistence.
   - `getPayloadDiagnostics(payload)`: Generates actionable diagnostics for invalid/ambiguous payloads.

### Stage F1 — Build and Edit Canonical Nodes

1. Refactor `ConditionBuilder.vue`, `ConditionGroupUI.vue`, `SimpleCondition.vue`, and `CollectionUI.vue` to edit canonical node discriminants:
   - `type: "group"` (`operator: "and" | "or"`, `children: [...]`)
   - `type: "comparison"` (`operator: "<canonical_id>"`, `left`, `right`)
   - `type: "collection_predicate"` (`quantifier: "any" | "all" | "none"`, `source`, `as`, `where`)
2. Integrate `FlexValueControl.vue` for left and right operands, supporting static values, variable paths, resolvers, and templates.

### Stage F2 — Typed Document Reference and Operator UX

1. Render typed document reference controls (`value_type: "document_reference"`) with DocType picker and document selector.
2. Fetch available business operators and labels dynamically from the backend contract API.

### Stage F3 — Integration and Round-Trip Verification

1. Verify round-trip load, edit, and save cycles against shared contract fixtures without semantic loss.
