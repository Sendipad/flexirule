# Component-Operation Mapping & Verification Matrix

## 1. Verified Component & Operation Matrix

Every operation in this matrix has been verified against the current repository source (`flexirule/ruleflow/core/value_resolver.py` and `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/`).

| Existing Strategy (`kind`) | Existing Operation / Params | Target Family | Target Operation | Existing Source Location | Classification | Decision for Release v1.0 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `date_formula` | Base + Offset (days, weeks, months, years) | `date` | `calculate` | `value_resolver.py:DateFormulaResolver` | `CONSOLIDATED` | Included in `DateResolver.vue`. |
| `date_diff` | Diff (days, months, years) | `date` | `diff` | `value_resolver.py:DateDiffResolver` | `CONSOLIDATED` | Included in `DateResolver.vue`. |
| `format` | `format_date` | `date` | `format` | `value_resolver.py:FormatResolver` | `CONSOLIDATED` | Included in `DateResolver.vue`. |
| `string_formula` | `concat` | `text` | `combine` | `value_resolver.py:StringFormulaResolver` | `CONSOLIDATED` | Included in `TextResolver.vue`. |
| `string_formula` | `uppercase`, `lowercase` | `text` | `case` | `value_resolver.py:StringFormulaResolver` | `CONSOLIDATED` | Included in `TextResolver.vue`. |
| `normalization` | `norm_pipeline` (trim, slug, snake, etc.) | `text` | `normalize` | `value_resolver.py:NormalizationResolver` | `CONSOLIDATED` | Included in `TextResolver.vue`. |
| `format` | Jinja / String interpolation | `text` | `format` | `value_resolver.py:FormatResolver` | `CONSOLIDATED` | Included in `TextResolver.vue`. |
| `math_formula` | `+`, `-`, `*`, `/` | `number` | `calculate` | `value_resolver.py:MathFormulaResolver` | `CONSOLIDATED` | Included in `NumberResolver.vue`. |
| `math_formula` | `precision` (rounding) | `number` | `round` | `value_resolver.py:MathFormulaResolver` | `CONSOLIDATED` | Included in `NumberResolver.vue`. |
| `string_formula` / `format` | `fmt_money` | `number` | `format_money` | `value_resolver.py:FormatResolver` / `StringFormulaResolver` | `CONSOLIDATED` / `REMOVED` | Reassigned exclusively to `NumberResolver.vue`. Removed from Text/Format. |
| `child_aggregation` | `sum`, `avg`, `count` | `collection` | `sum`, `average`, `count` | `value_resolver.py:ChildAggregationResolver` | `CONSOLIDATED` | Exposed under `CollectionResolver.vue`. Backend dispatches to direct child table math. |
| `collection` | `count` (with condition) | `collection` | `count` | `value_resolver.py:CollectionResolver` | `CONSOLIDATED` | Exposed under `CollectionResolver.vue`. Backend supports filtered counting. |
| `collection` | `any`, `all`, `first` (`find`), `filter`, `pluck`, `unique` | `collection` | `any`, `all`, `first`, `filter`, `pluck`, `unique` | `value_resolver.py:CollectionResolver` | `CONSOLIDATED` | Memory-safe predicate collection engine in `CollectionResolver.vue`. |
| `fetch` | `link_field`, `fetch_field`, `linked_doctype` | `lookup` | `field` | `value_resolver.py:FetchResolver` | `RENAMED` | Renamed from "Fetch From Link" to "Lookup" (`LookupResolver.vue`). |
| `system_context` | `sys_token` (`user`, `role_check`, `today`, `now`) | `system` | `user`, `role_check`, `context` | `value_resolver.py:SystemContextResolver` | `RENAMED` | Renamed to "System & Context" (`SystemResolver.vue`). |
| *Candidate* | `min`, `max` column aggregation | `collection` | `min`, `max` | N/A (Not in current backend) | `DEFERRED` | Excluded from v1.0. Deferred to post-release. |
| *Candidate* | Percentage calculation | `number` | `percentage` | N/A | `DEFERRED` | Excluded from v1.0 consolidation. |
| *Candidate* | Record lookup by key/value | `lookup` | `record` | N/A | `DEFERRED` | Excluded from v1.0. `lookup.field` suffices. |
| *Candidate* | Type Conversion (To Text, To Number, etc.) | `conversion` | `to_text`, `to_number` | N/A | `DEFERRED` | Excluded from v1.0. Explicit type casting deferred. |
| *Candidate* | Conditional If/Else, Coalesce | `conditional` | `if_else`, `coalesce` | N/A | `DEFERRED` | Excluded from v1.0. Branching handled by rule processes. |

---

## 2. Reconciliation Notes

### 2.1 `child_aggregation` `min` / `max` Reconciliation
The current backend class `ChildAggregationResolver` in `value_resolver.py` explicitly supports only `count`, `sum`, and `avg`:
```python
if self.agg_op == "count": return len(rows)
if self.agg_op == "sum": return sum(values)
if self.agg_op == "avg": return sum(values) / len(values) if values else 0.0
```
Therefore, `min` and `max` operations are classified as `DEFERRED` for v1.0 to ensure Phase 1 consolidates existing code rather than inventing unimplemented features.

### 2.2 Date Difference Semantics Reconciliation
`DateDiffResolver` in `value_resolver.py` accepts `diff_unit` parameter with values `"days"`, `"months"`, or `"years"`.
In the canonical contract, date difference is represented as a single canonical operation `date.diff` with `unit` property in `config`.

### 2.3 Collection Count Semantics Reconciliation
- **Child Table Column Count** (`ChildAggregationResolver`): Computes total row count `len(rows)` for child tables (`agg_table`).
- **Predicate Filtered Count** (`CollectionResolver`): Computes count of rows matching a predicate condition (`op == "count"`).
Both semantics share the user-facing operation label **Count** inside `CollectionResolver.vue`. The backend compiler inspects whether `condition` is present: if `condition` is empty and source is a simple child table path, it dispatches to `ChildAggregationResolver`; if `condition` is present, it dispatches to `CollectionResolver`.
