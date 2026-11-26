# Architectural Findings Report

## Executive Summary

This report documents all architectural issues, functional redundancies, configuration inconsistencies, and design limitations identified during the repository-wide audit of FlexiRule Value Resolvers.

Every finding follows the standardized `VR-GROUP-XXX` format.

---

### VR-GROUP-001 — Functional Redundancy Between `child_aggregation` and `collection`

- **Severity**: High
- **Area**: Architecture / Backend / Frontend
- **Evidence**:
  - Backend: `ChildAggregationResolver` vs `CollectionResolver` in `flexirule/ruleflow/core/value_resolver.py`
  - Frontend: `AggregationResolver.vue` vs `CollectionResolver.vue` in `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/`
- **Problem**:
  `child_aggregation` computes `count`, `sum`, and `avg` over child table rows without filtering capabilities. `CollectionResolver` performs `count`, `any`, `all`, `first`, `find`, `filter`, `pluck`, and `unique` over child table rows and list variables, supporting full row-level conditions (`ConditionEvaluator`). `child_aggregation.count` is 100% duplicated by `collection.count`.
- **Impact**:
  Increases maintenance overhead, confuses users with redundant UI choices, and limits aggregations because `child_aggregation` cannot filter rows before summing or averaging.
- **Scenario**:
  A rule builder wants to sum the total amount of item rows where `rate > 100`. Using `child_aggregation`, this is impossible because it lacks condition support. Using `collection`, the user can `pluck` item rates where `rate > 100`, but cannot sum them directly in a single operation step.
- **Recommendation**:
  Consolidate `child_aggregation` into `CollectionResolver` by adding numeric aggregation operations (`sum`, `avg`, `min`, `max`) to `CollectionResolver`, and deprecating `child_aggregation` via an in-memory compatibility alias.

---

### VR-GROUP-002 — Currency Formatting (`fmt_money`) Defined Independently in Two Resolvers

- **Severity**: Medium
- **Area**: Architecture / Frontend / Backend
- **Evidence**:
  - `StringFormulaResolver`: supports `str_op == "fmt_money"` in `flexirule/ruleflow/core/value_resolver.py:183`
  - `FormatResolver`: supports `fmt_op == "fmt_money"` in `flexirule/ruleflow/core/value_resolver.py:228`
- **Problem**:
  The currency formatting utility (`frappe.utils.fmt_money`) is duplicated across two distinct value resolver kinds (`string_formula` and `format`), each using different configuration key names (`str_a`/`str_b` vs `fmt_field`/`fmt_config`).
- **Impact**:
  Inconsistent user experience depending on whether currency formatting is invoked via String Manipulation or Format resolver, leading to redundant code paths.
- **Scenario**:
  A rule configured using `string_formula.fmt_money` expects currency symbol as `str_b`, whereas `format.fmt_money` expects currency symbol or field path in `fmt_config`.
- **Recommendation**:
  Standardize currency formatting under the `Transform.Format` family and deprecate `fmt_money` inside `StringFormulaResolver`.

---

### VR-GROUP-003 — Duplicate Standalone Child Aggregation Function in `field_resolver.py`

- **Severity**: Medium
- **Area**: Backend Architecture / Utilities
- **Evidence**:
  - `FieldResolver.aggregate_child_table()` in `flexirule/ruleflow/utils/field_resolver.py:125-155`
- **Problem**:
  The utility module `field_resolver.py` contains a standalone implementation of `aggregate_child_table` performing `sum`, `avg`, `min`, `max`, and `count` over document child tables, bypassing `ValueResolver`.
- **Impact**:
  Creates parallel, un-cached evaluation logic outside the canonical `ValueResolver` compiled strategy pattern.
- **Scenario**:
  Fixes or optimizations made to `ValueResolver` caching or evaluation guards will not benefit callers using `FieldResolver.aggregate_child_table()`.
- **Recommendation**:
  Refactor `FieldResolver.aggregate_child_table()` to delegate execution directly to `ValueResolver.compile()`.

---

### VR-GROUP-004 — Inconsistent Configuration Key Naming Across Resolvers

- **Severity**: Low
- **Area**: Contract / Configuration
- **Evidence**:
  - `date_formula`: `base_field`, `offset_sign`, `offset_value`, `offset_unit`
  - `math_formula`: `field_a`, `math_op`, `field_b`, `constant_b`
  - `normalization`: `norm_field`, `norm_profile`, `norm_pipeline`
  - `collection`: `source`, `operation`, `condition`, `target_field`
- **Problem**:
  Every resolver kind invents custom prefixes (`norm_`, `str_`, `agg_`, `fmt_`, `diff_`) for operational verbs and source fields rather than following a unified schema.
- **Impact**:
  Prevents building generic, reusable schema validation routines across resolver configurations.
- **Scenario**:
  Building a frontend generic resolver configurator requires custom field-mapping switches for all 10 resolver kinds.
- **Recommendation**:
  Adopt the standardized schema structure (`source`, `operation`, `config`) introduced by `CollectionResolver`.

---

### VR-GROUP-005 — Flat Strategy Selector Menu in `ValueResolverControl.vue`

- **Severity**: Low
- **Area**: UX / Frontend
- **Evidence**:
  - `ValueResolverControl.vue` strategy rendering logic in `flexirule/public/js/flexirule/rule_builder/controls/ValueResolverControl.vue`
- **Problem**:
  The UI displays 10 unorganized strategy buttons in a single flat flex wrap layout without category groupings or visual hierarchy.
- **Impact**:
  Increases visual clutter and cognitive overhead for rule authors selecting value resolvers.
- **Scenario**:
  A non-technical user seeking to calculate a date difference must visually scan through 10 disparate choices including `normalization`, `child_aggregation`, and `system_context`.
- **Recommendation**:
  Organize strategy buttons into 4 accordion/tabbed families: `Transform & Calculation`, `Collection & Table`, `Data Retrieval`, and `System & Session`.
