# Frontend Jules Task — Canonical Condition Builder

**Task type:** Frontend implementation plan for FlexiRule.  
**Depends on:** [Shared contract and handoff](README.md).  
**Coordination:** Backend publishes the versioned condition-contract DTO and authoritative validation. This task can start against shared JSON fixtures, but final integration must be tested against the backend API and should stack on or target the backend implementation branch if the API is not yet merged.

## Objective

Update the visual Condition Builder so it loads, edits, validates and saves a direct canonical condition node without changing its meaning. The persisted node has no schema/version/root envelope. The frontend owns interaction and ephemeral UI state only. It must not become a second source of truth for operators, resolver capabilities or execution semantics.

Do not edit Python/backend files, DocType JSON, runtime condition code or API contracts in this task. Use the DTO and fixtures in the shared contract; report required backend contract changes instead of inventing them.

## Related reports and prototypes to inspect first

Read the full [canonical condition + FlexValue implementation plan](../canonical-condition-flexvalue-implementation-plan.md) before coding. Inspect [PR #416](https://github.com/Sendipad/flexirule/pull/416) for its ConditionBuilder/SimpleCondition prototype and tests, but compare its implementation with the frozen shared contract; it is a draft, not an approved final schema. The [PR #433 benchmark report](../condition-backend-comparison-benchmark.md) is background only: correctness gate failed 12/13 agreement due to `has_changed`, and timing source SHA was not captured. Do not derive UI behavior or operator availability from benchmark candidate implementations; the backend DTO is authoritative; its API version does not become a field in the saved condition node.

## Source-first review: existing implementation

Inspect these current source paths before coding:

- **components/condition_builder/ConditionBuilder.vue:** owns a legacy root {op, conditions} and emits a deep clone of that editor tree.
- **Existing TreeBuilder implementation:** must be the structural editor for the canonical condition builder; inspect its README and actual API first. The current condition-specific components (`ConditionNode.vue`, `ConditionGroupUI.vue`, `CollectionUI.vue`) are legacy UI paths to migrate away from as recursive structure owners, not templates for a new parallel tree. Reuse the leaf/collection slots and domain controls where suitable.
- **components/rule_config/types/ConditionStep.vue:** hydrates the old tree, adds ephemeral IDs, strips them on save, writes trigger condition on the Start node and writes Condition action data.config directly. It also clears condition_json.
- **rule_builder/utils/condition_payload.js:** permissively unwraps multiple legacy formats; it should become an explicit legacy boundary adapter, not silently classify malformed canonical JSON as an empty tree.
- **SimpleCondition.vue:** the left side is currently a FieldPicker, the right side is FlexValue, and operator choices include static DEFAULT_OPERATORS/DEFAULT_LABELS fallbacks.
- **FlexValueControl.vue, controls/value_resolver/strategies.js, controls/value_resolver/index.js, useValueResolver.js and resolver components:** controls support legacy/generated-expression output and manual mode. Do not globally remove those behaviors from unrelated Assignment/Query/Process consumers as part of this condition-only task.
- **api.py:get_operator_config():** current legacy endpoint publishes Fieldtype operator maps from ConditionCompiler. The backend task will publish the canonical condition-contract DTO.

Relevant test runner in the current package.json: yarn test:frontend / yarn test; existing Cypress command is yarn test:e2e:cypress and regressions live under cypress/. Verify current scripts/test conventions before choosing the final test command.

## Implementation scope

### Mandatory architecture constraint — reuse the existing Generic TreeBuilder

The frontend implementation **must reuse the already-developed Generic TreeBuilder** at `flexirule/public/js/flexirule/rule_builder/components/tree_builder/`. Do not create a separate recursive ConditionNode/ConditionGroupUI/CollectionUI tree, a second drag/drop implementation, or duplicate generic add/remove/move/group logic.

Inspect and reuse the current public contract and existing source before coding:

- `TreeBuilder.vue` and `TreeBuilderNode.vue` for the generic hierarchy and rendering.
- `TreeBuilderGroup.vue`, `TreeBuilderScope.vue`, and `TreeBuilderLeaf.vue` for group, scope and leaf presentation.
- `useTreeBuilder.js`, `tree_builder_commands.js`, `tree_builder_validation.js`, and `tree_builder_utils.js` for controlled state, operations, validation hooks and structural helpers.
- `components/tree_builder/README.md` for the generic model and slot contract.

TreeBuilder owns hierarchy and interactions, **not condition-language semantics**. The condition feature supplies the leaf editor/summary and collection-slot content, validates conditions against the backend DTO, and keeps the canonical condition node as the sole persisted source of truth. Keep presentation state and TreeBuilder IDs out of persisted condition JSON.

The generic editor model is intentionally different from the saved condition AST. Use one thin, explicit `condition_tree_adapter.js` (or extend an existing suitable adapter) to map between them; this is a boundary adapter, not a second tree implementation:

- Canonical `group` maps to a TreeBuilder group; preserve its `and`/`or` operator and child order.
- Canonical `comparison` maps to a generic TreeBuilder `leaf`. Keep the full canonical comparison payload under a domain-owned property such as `conditionNode`, because TreeBuilder uses `type: "leaf"` as its structural discriminant.
- Canonical `collection_predicate` maps to TreeBuilder's generic collection `scope` node, preserving the canonical source, quantifier, alias and `where` subtree as domain payload. Use the existing inherited scope/context mechanism; do not mistake a scope for a logical group.
- TreeBuilder's UI root is a group. For a canonical root comparison or collection predicate, use a **synthetic UI-only root group** containing that one node; unwrap this wrapper on serialization. If a user adds a second root child, the root becomes a real canonical group. If a group ends with one child, collapse it before serialization; an empty group is invalid and blocks save.
- For a collection predicate, preserve its `where` root as one child under the TreeBuilder scope, even when `where` is a group. Do not flatten its logic or store a one-child logical group.

The adapter must be tested for canonical → TreeBuilder model → canonical round-trips, nested AND/OR groups, nested collection scopes, root comparisons, transient IDs, and malformed/ambiguous legacy conditions. Do not persist the TreeBuilder model directly and do not build a second condition tree component hierarchy.

### Stage F0 — Contract fixtures and adapter boundaries

1. Read README.md and use its exact direct-node shapes, semantic operator IDs and validation decisions. Create shared positive/negative fixtures where repository layout permits; if one fixture file cannot be consumed by both test runners, keep equivalent JSON fixtures generated from one documented source and assert equivalence.
2. Refactor rule_builder/utils/condition_payload.js into explicit functions with separate responsibilities:
   - strict recognition/validation of a direct canonical root node and its recursive child/operand shapes;
   - explicit legacy format detection and conversion for display only when conversion is deterministic;
   - serialization of an already-valid direct canonical condition node with UI-only IDs removed;
   - stable error records for unknown node/operator IDs, malformed canonical nodes and ambiguous legacy payloads.
3. Do not silently return a new empty {op:"and", conditions:[]} when a non-empty payload fails parsing. Preserve the original payload for diagnostics, render a blocking migration/error state and do not overwrite it on save.
4. Keep UI IDs for Vue keys only. They may exist in local component state but must never appear under root, node children, FlexValue configs or persisted JSON.

**Gate F0:** round-trip fixtures preserve canonical JSON; invalid or ambiguous input never becomes an empty passing-looking tree.

### Stage F1 — Adopt Generic TreeBuilder and map canonical nodes

Do not implement new recursive structure components. Integrate the existing `TreeBuilder.vue` with the condition domain through `condition_tree_adapter.js` and domain slots.

1. Use TreeBuilder's controlled `v-model`, group operators, leaf/collection factories, structural validation hooks, max-depth and drag/drop operations. Reuse its existing `useTreeBuilder` state/commands and inline presentation API. Do not duplicate these mechanics in ConditionBuilder.
2. Provide a condition-specific leaf slot (reusing/refactoring `SimpleCondition.vue` as a leaf editor) and, if readable presentation is enabled, a `#leaf-summary` slot. Provide collection-slot content for the condition-specific source, quantifier and alias; leave recursion and descendant rendering to TreeBuilder.
3. Map the canonical node variants through the adapter:
   - Group: canonical `{type: "group", operator: "and" | "or", children: [...]}` ↔ TreeBuilder group.
   - Comparison: canonical `{type: "comparison", operator, left: FlexValue, right?: FlexValue}` ↔ TreeBuilder leaf with the complete canonical node stored as domain payload.
   - Collection predicate: canonical `{type: "collection_predicate", quantifier, source, as, where}` ↔ TreeBuilder collection `scope` plus domain payload. Preserve `where` as a subtree boundary and use inherited scope context; any/all/none remain quantifiers, not group operators.
4. TreeBuilder's root is always a UI group. When the saved root is a comparison or collection predicate, represent it temporarily as the only child of a synthetic root group, then unwrap on serialization. A root with two or more direct children serializes as a canonical group. Collapse one-child group wrappers before save; an empty group is invalid and blocks save.
5. Never persist TreeBuilder IDs, generic `leaf`/`scope` discriminants or presentation/edit state. Persist only the direct canonical condition node. Do not mutate or replace the saved AST with the TreeBuilder model.
6. Do not serialize per-child `logical_operator`. Each canonical group owns one AND/OR operator; mixed logic is represented by nested groups. Preserve child order.
7. Keep canonical validation in `condition_validator.js` or the existing domain validator adapter; use TreeBuilder's structural hooks for basic hierarchy checks and the backend as authoritative for operator, operand, field metadata, scopes and resolver capabilities.
8. A wholly absent optional condition remains different from an empty editor tree. Incomplete local edit state can exist; saving a present empty group or malformed canonical node must be blocked.

**Gate F1:** the existing TreeBuilder owns all generic tree interactions; the condition adapter/slots round-trip every node variant; nested AND/OR and collection scope are preserved; no duplicate recursive tree UI or drag/drop implementation is introduced.

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

1. Trigger condition: save the direct canonical root node as JSON in the Start node’s existing trigger-condition property.
2. Condition action: save the same direct root node in data.config (no additional {condition: ...}, {root: ...}, schema or version wrapper); keep old condition_json only as a legacy read fallback until backend migration/deprecation makes it safe to remove.
3. Save must strip all ephemeral IDs recursively—including nested collection where trees and any IDs in templates—without dropping real config fields.
4. Validate the canonical node type and exact allowed shape at every load/edit/save boundary. A canonical node with an unknown type is preserved and shown as unsupported; do not retry it as legacy data or silently downgrade it.
5. On deterministic legacy formats, display the converted canonical view and make conversion visible where behavior changed. On ambiguous legacy joins, like/not like, has_changed, raw Python/Jinja or mismatched Link tuples, block destructive save and explain the required repair. Do not “fix” it by resetting to an empty group.
6. Ensure draft/activation behavior matches the backend rules: empty configuration may remain an absent optional condition on a draft where the owning contract allows it, but never serialize an empty canonical group or bypass Condition-action activation validation.
7. Ensure importing/exporting/cloning/copy-pasting a Rule preserves the direct canonical condition node and does not reintroduce legacy op/conditions data on the next save.

**Gate F3:** trigger and Condition-action save/reload works without changing semantics; no nested UI IDs remain in stored JSON.

### Stage F4 — API integration and frontend validation states

1. Call the backend’s versioned condition-contract API for operators, resolver capabilities, scopes and limits. Do not maintain a parallel frontend operator/family registry.
2. Preserve get_operator_config() only where unrelated/legacy UI still uses it. Do not change Query Records filter operators; they are a separate query contract.
3. Display backend validation diagnostics by AST path and map them to the corresponding node/operand where possible. Keep a top-level fallback that says which condition cannot be saved/activated.
4. Distinguish incomplete editor state from invalid persisted canonical JSON and from backend runtime/validation error. Do not show runtime evaluator failures as ordinary required-field validation.
5. Do not send manual Python/Jinja conditions to the canonical condition API. If a user opens a legacy raw expression, offer an explicit rewrite path or blocking “not supported in canonical conditions” notice.
6. Avoid N+1 per-node metadata API calls; fetch DTO once per editor session and invalidate/refetch when the contract DTO/registry version changes.

**Gate F4:** UI options match backend metadata and backend diagnostics are visible and actionable.

## Frontend test plan

Use the existing Node frontend test harness and Cypress. Add/extend focused tests under current tests/frontend conventions and update UI regressions to target actual visible behavior rather than implementation-only selectors.

Required cases:

- Canonical positive/negative fixtures: root comparison, root group, root collection predicate, root group mixing comparisons and nested groups, all node/FlexValue variants, unknown node type/key/operator/scope/resolver, missing operands, malformed nested configs, empty groups, unary groups and no-predicate trees.
- TreeBuilder adapter tests: canonical node ↔ generic tree round-trips; synthetic root unwrap/wrap; node IDs never persisted; scope/collection alias context; move/reorder/add/remove preserves direct canonical payload; group operators remain attached to groups; nested collection where boundaries do not flatten.
- Serialization: no UI id or wrapper; direct node JSON round-trip; static false/zero/null/decimal/list/object preservation; stable semantic operator IDs; aliases and nested groups stable.
- Logical semantics: nested AND/OR structure remains structural, no per-child logical joins, drag/drop and move preserve child order and group membership.
- FlexValue operands: variable/static/resolver left and right; supported output-type operator filtering; unary operand rendering; Dynamic Link target; context scopes; template/value tokens; no raw Python/Jinja canonical output.
- Legacy conversion: supported simple field comparisons convert deterministically; unsupported mixed joins, ambiguous operators, raw code and invalid JSON display blocking diagnostics and are not overwritten on save.
- Validation UX: empty or one-child groups cannot be saved as canonical; draft absence and Condition-action activation requirements are not conflated; backend errors map to node/operand; missing API DTO gives a clear error, not static fallback.
- Flow integration: Entry/trigger condition and Condition action config save/reload; Rule clone/import/export/copy/paste; nested collection predicate round-trip.
- Cypress regressions: through the existing TreeBuilder UI, create nested groups, edit condition leaves, configure a collection scope, save/reopen, assert the direct canonical serialized payload at the API boundary and verify backend validation response. Assert generic TreeBuilder remains responsible for drag/drop and structural actions; do not mock away the adapter/serialization layer in every end-to-end test.

Run and report actual results:

- yarn test:frontend (or verified project equivalent)
- relevant focused Node tests
- yarn lint or the actual ESLint command
- targeted Cypress spec(s), including existing builder regressions impacted by the changes
- production asset build only if this repository’s normal workflow includes it

Do not claim Cypress or build tests passed if not run. This is a docs/plan PR; implementation test results belong on the implementation PR.

## Acceptance criteria

- [ ] The builder reuses Generic TreeBuilder for recursive hierarchy, group/scope/leaf rendering, drag/drop and generic mutations; no parallel condition-tree component hierarchy is introduced.
- [ ] The condition-specific adapter maps between TreeBuilder's editor model and direct canonical condition nodes; TreeBuilder IDs, structural discriminants and UI state never persist.
- [ ] The builder writes only direct canonical condition nodes and canonical FlexValue variants; no persisted schema/version/root envelope.
- [ ] Both comparison operands use FlexValue and preserve value types.
- [ ] Operator/resolver options come from the backend contract DTO.
- [ ] No condition is persisted as Python/Jinja or generated expression.
- [ ] UI IDs never persist; load/edit/save round-trips preserve node shape and semantics.
- [ ] Legacy ambiguity is shown and cannot be silently overwritten.
- [ ] Frontend validation improves UX without replacing backend validation.
- [ ] Tests are run with exact commands/results; failures and unrun tests are stated honestly.

## Jules execution notes

Read this plan and the shared README, then inspect current source and test conventions at the task base. Inspect the current Generic TreeBuilder implementation and its README first; reuse its public API and slots. Do not create a replacement condition-specific tree. Keep the diff frontend-only. Trace each payload through ConditionStep.vue, the graph store, condition_payload.js and save/export/import before changing a component. If the backend API is not yet in the base branch, use the agreed DTO fixtures in unit tests and stack final integration on the backend implementation branch; do not invent a different DTO contract.
