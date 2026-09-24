# Current Resolver Inventory & Analysis

## 1. Overview

This document provides a comprehensive inventory of all 10 development-era Value Resolver implementations currently present in FlexiRule as of commit `b3c3e43172cf2f65d31725173f2b49bc57308d2f`.

Each resolver strategy was inspected across:
- Frontend Vue components (`flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/`)
- Frontend strategy registry (`flexirule/public/js/flexirule/rule_builder/controls/value_resolver/index.js`)
- Backend class implementations (`flexirule/ruleflow/core/value_resolver.py`)
- Test suites (`flexirule/ruleflow/tests/`)

---

## 2. Exhaustive Strategy Inventory & Classification

All capabilities in this inventory are classified according to the Phase 1 audit standards:
- **`EXISTING`**: Functionality demonstrably present in current source code.
- **`CONSOLIDATED`**: Existing capability exposed under a unified user-facing family.
- **`RENAMED`**: Existing capability with terminology updated for clarity.
- **`NEW`**: Capability not currently implemented in source code.
- **`REMOVED`**: Existing capability intentionally removed due to redundancy.
- **`DEFERRED`**: Candidate capability postponed to post-v1.0 releases.

---

### 1. `date_formula`
- **Frontend Component**: `DateFormulaResolver.vue`
- **Backend Class**: `DateFormulaResolver(CompiledResolver)`
- **Classification**: `CONSOLIDATED`
- **Current Parameters**: `base_type` (`"field"` / `"today"`), `base_field`, `offset_value`, `offset_unit` (`"days"`, `"weeks"`, `"months"`, `"years"`), `offset_sign` (`"+"` / `"-"`).
- **Target Family & Operation**: `date` → `calculate`

---

### 2. `math_formula`
- **Frontend Component**: `MathFormulaResolver.vue`
- **Backend Class**: `MathFormulaResolver(CompiledResolver)`
- **Classification**: `CONSOLIDATED`
- **Current Parameters**: `field_a`, `math_op` (`"+"`, `"-"`, `*`, `/`), `field_b_type`, `field_b`, `constant_b`, `precision`.
- **Target Family & Operation**: `number` → `calculate`

---

### 3. `date_diff`
- **Frontend Component**: `DateDiffResolver.vue`
- **Backend Class**: `DateDiffResolver(CompiledResolver)`
- **Classification**: `CONSOLIDATED`
- **Current Parameters**: `diff_start_type`, `diff_start_field`, `diff_end_type`, `diff_end_field`, `diff_unit` (`"days"`, `"months"`, `"years"`).
- **Target Family & Operation**: `date` → `diff`

---

### 4. `child_aggregation`
- **Frontend Component**: `AggregationResolver.vue`
- **Backend Class**: `ChildAggregationResolver(CompiledResolver)`
- **Classification**: `CONSOLIDATED`
- **Current Parameters**: `agg_table`, `agg_field`, `agg_op` (`"sum"`, `"avg"`, `"count"`).
- **Target Family & Operation**: `collection` → `sum` / `average` / `count`
- **Audit Note**: `min` and `max` operations do not exist in `ChildAggregationResolver` implementation and are classified as `DEFERRED`.

---

### 5. `string_formula`
- **Frontend Component**: `StringFormulaResolver.vue`
- **Backend Class**: `StringFormulaResolver(CompiledResolver)`
- **Classification**: `CONSOLIDATED` / `REMOVED`
- **Current Operations**:
  - `concat`: `CONSOLIDATED` → `text` → `combine`
  - `uppercase` / `lowercase`: `CONSOLIDATED` → `text` → `case`
  - `fmt_money`: `REMOVED` from string formula (reassigned exclusively to `number` → `format_money`).

---

### 6. `normalization`
- **Frontend Component**: `NormalizationResolver.vue`
- **Backend Class**: `NormalizationResolver(CompiledResolver)`
- **Classification**: `CONSOLIDATED`
- **Current Parameters**: `norm_field`, `norm_pipeline` (`["trim", "slug", "snake", "title", "upper", "lower", "normalize"]`).
- **Target Family & Operation**: `text` → `normalize`

---

### 7. `format`
- **Frontend Component**: `FormatResolver.vue`
- **Backend Class**: `FormatResolver(CompiledResolver)`
- **Classification**: `CONSOLIDATED`
- **Current Operations**:
  - `format_date`: `CONSOLIDATED` → `date` → `format`
  - `fmt_money`: `CONSOLIDATED` → `number` → `format_money`
  - `format_number`: `CONSOLIDATED` → `number` → `format`

---

### 8. `fetch`
- **Frontend Component**: `FetchResolver.vue`
- **Backend Class**: `FetchResolver(CompiledResolver)`
- **Classification**: `RENAMED`
- **Current Parameters**: `link_field`, `fetch_field`, `linked_doctype`.
- **Target Family & Operation**: `lookup` → `field`

---

### 9. `system_context`
- **Frontend Component**: `SystemContextResolver.vue`
- **Backend Class**: `SystemContextResolver(CompiledResolver)`
- **Classification**: `RENAMED`
- **Current Parameters**: `sys_token` (`"user"`, `"role_check"`, `"today"`, `"now"`), `sys_role`.
- **Target Family & Operation**: `system` → `user` / `role_check` / `context`

---

### 10. `collection`
- **Frontend Component**: `CollectionResolver.vue`
- **Backend Class**: `CollectionResolver(CompiledResolver)`
- **Classification**: `CONSOLIDATED`
- **Current Operations**: `count`, `any`, `all`, `first` (and alias `find`), `filter`, `pluck`, `unique`.
- **Target Family & Operation**: `collection` → `count` / `any` / `all` / `first` / `filter` / `pluck` / `unique`

---

## 3. Inventory Classification Summary

| Current Strategy (`kind`) | Implemented Operations in Source | Target Family | Target Operation | Classification |
| :--- | :--- | :--- | :--- | :--- |
| `date_formula` | Base + Offset (days, weeks, months, years) | `date` | `calculate` | `CONSOLIDATED` |
| `date_diff` | Diff (days, months, years) | `date` | `diff` | `CONSOLIDATED` |
| `math_formula` | Add, Subtract, Multiply, Divide | `number` | `calculate` | `CONSOLIDATED` |
| `string_formula` | Concat, Uppercase, Lowercase, Fmt Money | `text` / `number` | `combine`, `case`, `format_money` | `CONSOLIDATED` |
| `normalization` | Pipeline (trim, slug, snake, title, upper, lower) | `text` | `normalize` | `CONSOLIDATED` |
| `format` | Format Date, Fmt Money, Format Number | `date` / `number` / `text` | `format`, `format_money` | `CONSOLIDATED` |
| `child_aggregation` | Sum, Avg, Count | `collection` | `sum`, `average`, `count` | `CONSOLIDATED` |
| `collection` | Count, Any, All, First, Find, Filter, Pluck, Unique | `collection` | `count`, `any`, `all`, `first`, `filter`, `pluck`, `unique` | `CONSOLIDATED` |
| `fetch` | Fetch Linked Field | `lookup` | `field` | `RENAMED` |
| `system_context` | Session User, Role Check | `system` | `user`, `role_check` | `RENAMED` |
| *Candidate* | Percentage calculation | `number` | `percentage` | `DEFERRED` |
| *Candidate* | Record lookup by key/value | `lookup` | `record` | `DEFERRED` |
| *Candidate* | Type Casting (To Number, To Text, To Date) | `conversion` | `to_text`, `to_number` | `DEFERRED` |
| *Candidate* | Conditional If/Else, Coalesce | `conditional` | `if_else`, `coalesce` | `DEFERRED` |
