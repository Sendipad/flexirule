# Fetch Records Filter Tree & FilterLeaf — Investigation Report

**Repository:** `Sendipad/flexirule`  
**Inspected branch:** `feat/fetch-records-mode`  
**Implementation branch:** `refactor/fetch-records-filter-operators-20261009`  
**Status:** Source investigation in progress; findings below are grounded in inspected source. No implementation changes are included in this report commit.

## 1. Scope and source trace

Inspected:
- `flexirule/ruleflow/core/action_handlers/query_records.py` — canonical Fetch Records tree validation, filter normalization, field validation, and query execution.
- `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/query_records/FetchRecordsConfig.vue` — Fetch Records UI entry point; passes `localConfig.filters` into `QueryFilterTree`.
- `flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/QueryFilterTree.vue` — adapts the persisted filter tree to the generic `TreeBuilder`, supplies a `FilterLeaf`, and emits serialized state.
- `flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/FilterLeaf.vue` — field/operator/value row; uses existing field-navigation and value-control infrastructure.
- `flexirule/public/js/flexirule/rule_builder/components/rule_config/FilterGroup.vue` — older flat-filter implementation with a separate operator list and compatibility logic; useful as a source of existing conventions, but not an authoritative contract for the new Fetch Records tree.
- `flexirule/public/js/flexirule/rule_builder/controls/FlexValueControl.vue` — generic static/dynamic value editor and resolver-entry UI.
- `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/index.js`, `useValueResolver.js`, and `strategies.js` — resolver strategy registration and resolver configuration lifecycle.
- `reports/query-records/frappe-qb-v15-capability-audit.md` — documented Frappe Query Builder capability checks, including nested-set operators.

The UI lifecycle is: `FetchRecordsConfig` owns the action config and passes `filters` to `QueryFilterTree`; the tree adapter owns tree serialization; the leaf edits a single field/operator/value; `FlexValueControl` owns value editing and resolver entry; backend `QueryRecords` validates the canonical tree, normalizes supported filter forms, validates field references, and delegates query execution to the Frappe query compatibility layer.

## 2. Backend operator inventory

The canonical filter-tree allowlist in `query_records.py` (`_FETCH_RECORDS_OPERATORS`) currently contains:

| Canonical value | Initial semantic category | Value-shape consideration |
|---|---|---|
| `=` | equality | scalar / explicit null as supported by query path |
| `!=` | inequality | scalar |
| `<>` | inequality alias | scalar |
| `>` | greater-than | scalar |
| `>=` | greater-than-or-equal | scalar |
| `<` | less-than | scalar |
| `<=` | less-than-or-equal | scalar |
| `like` | text/pattern match | scalar pattern |
| `not like` | negative pattern match | scalar pattern |
| `in` | membership | list-like value |
| `not in` | negative membership | list-like value |
| `between` | inclusive range semantics depend on backend | two-bound value |
| `not between` | negative range | two-bound value |
| `is` | null/special-value comparison | operator-specific scalar or null |
| `is set` | presence check | no ordinary value should be needed if execution path implements it as a unary operator |
| `is not set` | absence check | no ordinary value should be needed if execution path implements it as a unary operator |
| `timespan` | relative-time comparison | structured/date-relative value |
| `starts with` | text prefix match | scalar text |
| `ends with` | text suffix match | scalar text |
| `descendants of` | nested-set hierarchy | selected node name; requires a Tree DocType context |
| `ancestors of` | nested-set hierarchy | selected node name; requires a Tree DocType context |

This is the validator's accepted canonical set, not proof that every entry has correct end-to-end execution semantics. Each operator must be traced through the normalization/compiler path and covered by backend tests before the frontend exposes it.

The capability audit also documents `not descendants of` and `not ancestors of` in Frappe Query Builder nested-set behavior. Those values are **not** present in the canonical Fetch Records validator allowlist above. Do not expose them in Fetch Records unless the product contract and backend validator/compiler are deliberately aligned. Likewise, the legacy `FilterGroup.vue` contains `descendants of (inclusive)`, but that legacy label is not in the canonical Fetch Records allowlist.

## 3. Current frontend mismatch and risks

1. `FilterGroup.vue` has its own hardcoded operator labels, type exclusions, extra text operators, and nested-set logic. It is not a safe source of truth for the canonical Fetch Records tree.
2. The old component's operators use title-cased values such as `Between` and `Timespan`, while the new backend canonical allowlist uses lowercase `between` and `timespan`. Reusing the old operator strings without a deliberate adapter can produce invalid serialized values.
3. Legacy operator filtering includes a separate `FRAPPE_INVALID_CONDITION_MAP`, special cases for Check, and `frappe.boot.nested_set_doctypes`. These rules need to be reconciled with actual Fetch Records backend execution rather than copied blindly.
4. The backend validator requires a canonical tree and an explicit `value` key (with `null` representing an explicit NULL). UI-only blank leaves must not serialize as executable filters.
5. The current canonical operator allowlist and Frappe Query Builder's nested-set operator set are not identical. Contract parity tests should guard the intended supported set and prevent accidental expansion.
6. `FetchRecordsConfig.vue` passes the parent DocType to `QueryFilterTree`; the leaf must preserve the correct field/target DocType context when a selected field is a Link or a navigated linked field.
7. Tree DocType semantics must be derived from the Link field's target DocType metadata (and/or authoritative Frappe nested-set metadata), not from the Link field being mistaken for a Table field. Tree hierarchy operators apply to a Tree DocType context, not every Link.

## 4. Responsibilities and proposed reusable abstraction

Use a focused, declarative operator registry plus a composable (proposed `useFilterOperators`) rather than moving query semantics into the generic Tree Builder.

- **Operator registry/contract:** canonical lowercase values, translated labels, value shape, unary/value-required flag, and broad semantic category. Must be parity-tested against backend allowlist.
- **Compatibility policy:** maps resolved field metadata and target DocType metadata to the supported subset; treats missing metadata explicitly and safely; only offers nested-set operators when the actual target DocType is a Tree DocType and the backend accepts that operator.
- **`FilterLeaf`:** owns leaf interaction and renders field/operator/value controls. It asks the composable for valid operators; it should not own a second operator registry.
- **`QueryFilterTree`:** owns canonical tree adaptation/serialization and delegates structural editing to `TreeBuilder`.
- **`TreeBuilder`:** remains structural; no backend-specific operator or resolver logic.
- **`FlexValueControl`:** remains the value editor and resolver entry point. Resolver selection/default policy should be reusable and separate from leaf rendering.

The composable should accept reactive field metadata/context, return computed canonical operator options, and expose deterministic default-operator selection. It must not make metadata requests itself if the field-navigation/metadata composables already own that responsibility.

## 5. Value Resolver findings and design constraints

The current resolver UI registers strategies in `controls/value_resolver/index.js` and stores strategy metadata/default state through the strategy registry in `controls/value_resolver/strategies.js`. `useValueResolver.js` owns local resolver state and emits updates. `FlexValueControl.vue` is the user-facing entry point for `/` resolver selection.

Resolver defaults should be selected using both the actual field type and the operator's expected input semantics:
- date/datetime + scalar comparison is not automatically equivalent to a relative-time comparison;
- membership operators need a list-compatible result/value shape;
- range operators need a two-bound shape;
- unary operators such as presence checks should not create an unnecessary value resolver;
- text matching needs a text-compatible result, and numeric comparisons need a numeric-compatible result.

The persisted resolver contract for this work is `{ family, operation, config }`. The implementation must use the registered resolver strategies' canonical default-state/config factories and operation metadata. It must not add `config.kind` or deprecated payload keys. When a field/operator changes, retain a resolver configuration only if it remains valid for the new context; otherwise mark/reset it deliberately without silently rewriting valid user-authored settings.

## 6. Tree DocType and metadata behavior

- Resolve the field's true fieldtype separately from its control component type.
- For a Link field, `field.options` identifies the target DocType; use target metadata to determine whether the target is a Tree DocType.
- Keep Select-field choices, Link target DocType metadata, operator dropdown options, and tree hierarchy choices separate. They are different data channels.
- Reuse the existing metadata and navigable-field facilities; avoid duplicate fetches and stale option state.
- When target metadata is missing or delayed, avoid showing tree-only operators until the metadata can establish the target is a Tree DocType.
- On field/target changes, invalidate stale dependent choices and ensure operator/value state is consistent.

## 7. Test plan

1. Backend contract test: canonical operator registry matches `_FETCH_RECORDS_OPERATORS` and labels are not used as serialized values.
2. Backend execution tests: every allowlisted operator has a verified execution/value-shape test, including `is`, unary presence checks, `timespan`, and nested-set operators.
3. Frontend composable tests: compatibility by actual fieldtype, missing metadata, dynamic metadata updates, Link target metadata, and Tree vs non-Tree target.
4. Leaf tests: blank editable leaf, canonical operator serialization, invalid operator replacement after field change, value-required/unary controls, list/range value shape, and incomplete-leaf exclusion from executable serialization.
5. Resolver tests: slash selection, family/operation/config defaults, operator-sensitive selection, preservation of valid user settings, and invalidation when the field/operator changes.
6. Build/lint and backend tests using existing repository tooling; report checks as unavailable if the execution environment cannot run them.

## 8. Implementation sequence

1. Finish tracing operator normalization and execution for each allowlisted value.
2. Confirm current filter leaf's value-control context and the resolver selection callback.
3. Add a single canonical frontend operator metadata/compatibility abstraction and focused tests.
4. Wire `FilterLeaf` to the abstraction and correct value shapes/unary operators.
5. Add resolver default-selection policy at the resolver integration boundary, using existing strategy defaults.
6. Add contract parity/integration tests; run focused tests, lint, and build.
7. Record actual results and limitations in a verification report.

## 9. Evidence and limitations

Source evidence was inspected on `feat/fetch-records-mode`; implementation branch was created from that ref. The report intentionally distinguishes the backend validator allowlist from the broader capabilities documented by the Frappe Query Builder audit and from the legacy flat-filter UI. The exact execution semantics and value coercion of each allowlisted operator still require completion of the backend handler trace and focused tests before implementation is considered verified.
