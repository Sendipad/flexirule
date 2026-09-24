# Executive Summary: Value Resolver Architecture

## 1. Context & Consistency Audit Summary

FlexiRule is an enterprise rule engine built on the Frappe framework. Value Resolvers are the foundational mechanism used by FlexiRule actions (such as Assignments, Condition Evaluations, and Sub-rule Arguments) to compute dynamic values from document fields, expressions, formulas, context variables, and external lookups.

Following a thorough **Phase 1 Consistency Audit**, all proposed architectural components were verified against the actual repository source code (`flexirule/ruleflow/core/value_resolver.py`, `permissions.py`, `evaluator.py`, and `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/`).

---

## 2. Verified Architectural Decisions

1. **Focus on Consolidating Existing Capabilities**:
   Consolidation focuses strictly on existing capabilities (`EXISTING`, `CONSOLIDATED`, `RENAMED`). Unimplemented candidate operations (such as `conversion`, `conditional`, `percentage`, `min`/`max` column aggregation, and `lookup.record`) are classified as `DEFERRED` for post-v1.0 releases to avoid inventing untested functionality during pre-release consolidation.

2. **Explicit Field-Level Legacy Adapters**:
   Legacy payloads (`{ "kind": "..." }`) are mapped to canonical `{ "family": "...", "operation": "...", "config": { ... } }` contracts via explicit field-level adapters, ensuring legacy schemas are NOT wrapped inside the canonical config object. Unmapped or unknown legacy operations raise an explicit `UnrecognizedResolverPayloadError`.

3. **Duplication Elimination (`fmt_money`)**:
   Currency formatting (`fmt_money`) is removed from `StringFormulaResolver` and `FormatResolver` and assigned exclusively to **Number** → `format_money`.

4. **Unified Collection & Table Mental Model**:
   Both child table column aggregation (`ChildAggregationResolver`) and predicate filtering (`CollectionResolver`) are presented under a single user-facing component: **Collections & Tables** (`CollectionResolver.vue`). The backend compiler automatically dispatches to `ChildAggregationResolver` when un-filtered column math is requested, or `CollectionResolver` when predicate conditions are present.

5. **Security & Performance Verification**:
   - `CollectionResolver` enforces `MAX_COLLECTION_ROWS = 10000` and uses non-eval `ConditionEvaluator` predicate execution.
   - Expression evaluation is guarded by `SafeEvalVisitor` AST inspection (`permissions.py`).
   - Repository test suite metrics are verified at **42 test files** containing **392 test methods**.

---

## 3. The Consolidated First-Release Value Taxonomy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FlexiRule Consolidated Value Families                    │
├───────────────┬───────────────┬───────────────┬─────────────────────────────┤
│ 1. Date & Time│ 2. Text       │ 3. Number     │ 4. Collections & Tables     │
├───────────────┼───────────────┼───────────────┼─────────────────────────────┤
│ 5. Lookup     │ 6. System     │ (Conversion)* │ (Conditional)*              │
└───────────────┴───────────────┴───────────────┴─────────────────────────────┘
  * Note: Conversion and Conditional families are DEFERRED to post-v1.0.
```

### Core Family Summary

1. **Date & Time** (`date`): `calculate` (add/subtract offset), `diff` (difference in days/months/years), `format` (format date string).
2. **Text** (`text`): `combine` (concatenation), `case` (upper/lower/title), `normalize` (multi-step pipeline), `format` (string interpolation).
3. **Number** (`number`): `calculate` (add/subtract/multiply/divide), `round` (precision rounding), `format_money` (currency formatting).
4. **Collections & Tables** (`collection`): `count`, `any`, `all`, `first` (`find`), `filter`, `pluck`, `unique`, `sum`, `average`.
5. **Lookup** (`lookup`): `field` (fetch field from linked document).
6. **System & Context** (`system`): `user` (session user), `role_check` (user role check), `context` (today/now).
