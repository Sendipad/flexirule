# Frontend Jules Task — Canonical Condition Builder

**Task type:** Frontend implementation plan for FlexiRule.  
**Depends on:** [Shared contract and handoff](README.md).  
**Coordination:** Backend publishes the versioned condition-contract DTO and authoritative validation. This task can start against shared JSON fixtures, but final integration must be tested against the backend API and should stack on or target the backend implementation branch if the API is not yet merged.

## Objective

Update the visual Condition Builder so it loads, edits, validates and saves the canonical flexirule.condition v1 envelope without changing its meaning. The frontend owns interaction and ephemeral UI state only. It must not become a second source of truth for operators, resolver capabilities or execution semantics.

Do not edit Python/backend files, DocType JSON, runtime condition code or API contracts in this task. Use the DTO and fixtures in the shared contract; report required backend contract changes instead of inventing them.

## Source-first review: existing implementation

Inspect these current source paths before coding:

- **components/condition_builder/ConditionBuilder.vue:** owns a legacy root {op, conditions} and emits a deep clone of that editor tree.
- **ConditionNode.vue, ConditionGroupUI.vue, CollectionUI.vue and SimpleCondition.vue:** discriminate legacy nodes by fields such as left, conditions, collection and where; they use per-node logical joins and legacy row predicate shapes.
- **components/rule_config/types/ConditionStep.vue:** hydrates the old tree, adds ephemeral IDs, strips them on save, writes trigger condition on the Start node and writes Condition action data.config directly. It also clears condition_json.
- **rule_builder/utils/condition_payload.js:** permissively unwraps multiple legacy formats; it should become an explicit versioned boundary adapter, not silently classify malformed canonical JSON as an empty tree.
- **SimpleCondition.vue:** the left side is currently a FieldPicker, the right side is FlexValue, and operator choices include static DEFAULT_OPERATORS/DEFAULT_LABELS fallbacks.
- **FlexValueControl.vue, controls/value_resolver/strategies.js, controls/value_resolver/index.js, useValueResolver.js and resolver components:** controls support legacy/generated-expression output and manual mode. Do not globally remove those behaviors from unrelated Assignment/Query/Process consumers as part of this condition-only task.
- **api.py:get_operator_config():** current legacy endpoint publishes Fieldtype operator maps from ConditionCompiler. The backend task will publish the canonical condition-contract DTO.

Relevant test runner in the current package.json: yarn test:frontend / yarn test; existing Cypress command is yarn test:e2e:cypress and regressions live under cypress/. Verify current scripts/test conventions before choosing the final test command.

## Implementation scope

### Stage F0 — Contract fixtures and adapter boundaries

1. Read README.md and use its exact schema/version, node shapes and operator decisions. Create shared positive/negative fixtures where repository layout permits; if one fixture file cannot be consumed by both test runners, keep equivalent JSON fixtures generated from one documented source and assert equivalence.
2. Refactor rule_builder/utils/condition_payload.js into explicit functions with separate responsibilities:
   - strict recognition/validation of the canonical envelope for v1;
   - explicit legacy format detection and conversion for display only when conversion is deterministic;
   - serialization of an already-valid canonical envelope with UI-only IDs removed;
   - stable error records for unsupported versions, malformed canonical nodes and ambiguous legacy payloads.
3. Do not silently return a new empty {op:"and", conditions:[]} when a non-empty payload fails parsing. Preserve the original payload for diagnostics, render a blocking migration/error state and do not overwrite it on save.
4. Keep UI IDs for Vue keys only. They may exist in local component state but must never appear under root, node children, FlexValue configs or persisted JSON.

**Gate F0:** round-trip fixtures preserve canonical JSON; invalid or ambiguous input never becomes an empty passing-looking tree.

### Stage F1 — Build and edit canonical nodes

Refactor the builder components to operate on the new node discriminants:

- Group: { type: "group", operator: "and" | "or", children: [...] }
- Comparison: { type: "comparison", operator, left: FlexValue, right?: FlexValue }
- Collection predicate: { type: "collection_predicate", quantifier: "any" | "all" | "none", source: FlexValue (variable/path only in v1), as, where: ConditionNode }

Tasks:

1. ConditionBuilder.vue loads the envelope’s root into editor state, provides root-group controls and emits the envelope with schema/version on save. Keep root state distinct from its UI wrapper and do not persist a second legacy tree.
2. ConditionNode.vue dispatches on node.type, not key-presence heuristics such as left or conditions.
3. ConditionGroupUI.vue has one AND/OR switch per group and nested groups for mixed logic. Do not persist logical_operator on individual children. Preserve child ordering and drag/drop identity.
4. CollectionUI.vue builds the explicit collection predicate: source path, validated local alias and where subtree. any/all/none are quantifiers; do not use the legacy {op:"any", collection:"...", alias:"row"} as canonical JSON.
5. condition_validator.js validates canonical structure, node limits, required values and metadata-driven operator/operand constraints. It is UX validation only; server-side validation remains authoritative.
6. Incomplete interaction state can exist locally, but saving a present empty group or malformed canonical node must be blocked. Draft behavior for a wholly absent optional condition follows the owning Rule/Action contract; do not encode absence as an empty canonical group.

**Gate F1:** all node types round-trip; nested AND/OR is explicit; no sibling-join ambiguity remains in saved data.

### Stage F2 — Use FlexValue for both operands

1. Replace the left-only FieldPicker binding in SimpleCondition.vue with the shared FlexValue editor model. Both left and right are FlexValue nodes; the left control defaults to a variable/path picker but permits static or resolver choices only where the backend DTO allows them.
2. Integrate with FlexValueControl.vue and resolver strategy/config components using a condition-specific purpose/capability context. Do not force generated Python into value, persist a generated expression as executable truth or allow manual raw Python/Jinja in canonical condition mode.
3. Preserve static literal types: boolean false is not numeric zero; null is not missing; decimal precision is not lost to Number coercion; list/object values are not reinterpreted as Link tuples based on shape.
4. Use the left operand’s metadata to filter operators when it is a direct document field. For resolver/variable operands, use declared result type from the backend DTO. For unknown types show only the conservative operators the server explicitly permits; never promise an operator the API will reject.
5. Unary operators should hide/disable the right operand according to backend arity metadata; do not hard-code a second independent unary operator list.
6. Dynamic Link selection and context roots (old_doc, vars, caller, rule, doctype, local collection alias) must serialize into the exact canonical path.scope + path.segments shape. Do not serialize executable expressions or ambiguous dotted fallback strings.
7. Use backend-provided operator labels, allowed Fieldtypes, resolver operations/output types, permission/capability flags and limits. Remove legacy static operator fallback maps only after the versioned contract DTO is available; if the DTO fails to load, show an actionable error rather than silently showing stale/default operators.

**Gate F2:** both operands serialize as valid FlexValues; resolver mode emits structured family/operation/config; every enabled UI capability is allowed by backend metadata.

### Stage F3 — Hydration and persistence integration

Target ConditionStep.vue, condition_payload.js and identified Rule graph/config serializer consumers. Do not alter the backend contract.

1. Trigger condition: save the complete canonical envelope to the Start node’s existing trigger-condition property.
2. Condition action: save the same envelope directly to data.config (no additional {condition: ...} wrapper); keep old condition_json only as a legacy read fallback until backend migration/deprecation makes it safe to remove.
3. Save must strip all ephemeral IDs recursively—including nested collection where trees and any IDs in templates—without dropping real config fields.
4. Add a schema/version check before every load/edit/save boundary. Unsupported canonical versions are preserved and shown as unsupported; do not silently downgrade.
5. On deterministic legacy formats, display the converted canonical view and make conversion visible where behavior changed. On ambiguous legacy joins, like/not like, has_changed, raw Python/Jinja or mismatched Link tuples, block destructive save and explain the required repair. Do not “fix” it by resetting to an empty group.
6. Ensure draft/activation behavior matches the backend rules: empty configuration may remain an absent optional condition on a draft where the owning contract allows it, but never serialize an empty canonical group or bypass Condition-action activation validation.
7. Ensure importing/exporting/cloning/copy-pasting a Rule preserves the envelope and does not reintroduce legacy op/conditions data on the next save.

**Gate F3:** trigger and Condition-action save/reload works without changing semantics; no nested UI IDs remain in stored JSON.

### Stage F4 — API integration and frontend validation states

1. Call the backend’s versioned condition-contract API for operators, resolver capabilities, scopes and limits. Do not maintain a parallel frontend operator/family registry.
2. Preserve get_operator_config() only where unrelated/legacy UI still uses it. Do not change Query Records filter operators; they are a separate query contract.
3. Display backend validation diagnostics by AST path and map them to the corresponding node/operand where possible. Keep a top-level fallback that says which condition cannot be saved/activated.
4. Distinguish incomplete editor state from invalid persisted canonical JSON and from backend runtime/validation error. Do not show runtime evaluator failures as ordinary required-field validation.
5. Do not send manual Python/Jinja conditions to the canonical condition API. If a user opens a legacy raw expression, offer an explicit rewrite path or blocking “not supported in canonical conditions” notice.
6. Avoid N+1 per-node metadata API calls; fetch DTO once per editor session and invalidate/refetch on schema-version changes.

**Gate F4:** UI options match backend metadata and backend diagnostics are visible and actionable.

## Frontend test plan

Use the existing Node frontend test harness and Cypress. Add/extend focused tests under current tests/frontend conventions and update UI regressions to target actual visible behavior rather than implementation-only selectors.

Required cases:

- Canonical positive/negative fixtures: all node variants, FlexValue variants, unknown version/key/operator/scope/resolver, missing operands and malformed nested configs.
- Serialization: no UI id; stable schema/version; JSON round-trip; static false/zero/null/decimal/list/object preservation; aliases and nested groups stable.
- Logical semantics: nested AND/OR structure remains structural, no per-child logical joins, drag/drop and move preserve child order and group membership.
- FlexValue operands: variable/static/resolver left and right; supported output-type operator filtering; unary operand rendering; Dynamic Link target; context scopes; template/value tokens; no raw Python/Jinja canonical output.
- Legacy conversion: supported simple field comparisons convert deterministically; unsupported mixed joins, ambiguous operators, raw code and invalid JSON display blocking diagnostics and are not overwritten on save.
- Validation UX: empty group cannot be saved as canonical; draft absence and Condition-action activation requirements are not conflated; backend errors map to node/operand; missing API DTO gives a clear error, not static fallback.
- Flow integration: Entry/trigger condition and Condition action config save/reload; Rule clone/import/export/copy/paste; nested collection predicate round-trip.
- Cypress regressions: create nested groups, edit operands, save/reopen, assert serialized payload at API boundary and verify backend validation response. Do not mock away the contract/serialization layer in every end-to-end test.

Run and report actual results:

- yarn test:frontend (or verified project equivalent)
- relevant focused Node tests
- yarn lint or the actual ESLint command
- targeted Cypress spec(s), including existing builder regressions impacted by the changes
- production asset build only if this repository’s normal workflow includes it

Do not claim Cypress or build tests passed if not run. This is a docs/plan PR; implementation test results belong on the implementation PR.

## Acceptance criteria

- [ ] The builder writes only the v1 envelope and canonical node/FlexValue variants.
- [ ] Both comparison operands use FlexValue and preserve value types.
- [ ] Operator/resolver options come from the backend contract DTO.
- [ ] No condition is persisted as Python/Jinja or generated expression.
- [ ] UI IDs never persist; load/edit/save round-trips preserve schema and semantics.
- [ ] Legacy ambiguity is shown and cannot be silently overwritten.
- [ ] Frontend validation improves UX without replacing backend validation.
- [ ] Tests are run with exact commands/results; failures and unrun tests are stated honestly.

## Jules execution notes

Read this plan and the shared README, then inspect current source and test conventions at the task base. Keep the diff frontend-only. Trace each payload through ConditionStep.vue, the graph store, condition_payload.js and save/export/import before changing a component. If the backend API is not yet in the base branch, use the agreed DTO fixtures in unit tests and stack final integration on the backend implementation branch; do not invent a different DTO contract.
