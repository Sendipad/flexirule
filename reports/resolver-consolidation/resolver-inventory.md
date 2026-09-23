# Resolver Inventory

## Overview
This document outlines every resolver concept found in the FlexiRule repository across frontend controls, backend compilation engine, execution handlers, and tests prior to consolidation.

---

## Detailed Resolver Matrix

| Resolver Kind | Purpose | Input Schema | Output Type | Frontend Strategy Component | Backend Class | Runtime Execution Mechanism | Duplicate / Overlap Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `date_formula` | Date arithmetic (add/subtract offsets from base date or today) | `{ base_type, base_field, offset_value, offset_unit, offset_sign }` | Date string (`YYYY-MM-DD`) | `DateFormulaResolver.vue` | `DateFormulaResolver` | `frappe.utils.add_days` / `add_to_date` | Overlaps with `date_diff` → Merged into `date` |
| `date_diff` | Calculate difference between two dates in days/months/years | `{ diff_start_type, diff_start_field, diff_end_type, diff_end_field, diff_unit }` | Number | `DateDiffResolver.vue` | `DateDiffResolver` | `frappe.utils.date_diff` / `month_diff` | Overlaps with `date_formula` → Merged into `date` |
| `math_formula` | Binary numeric operation between field/constant | `{ field_a, math_op, field_b_type, field_b, constant_b, precision }` | Number (Float/Int) | `MathFormulaResolver.vue` | `MathFormulaResolver` | Python arithmetic operators (`+`, `-`, `*`, `/`) | Re-architected into canonical `math` |
| `string_formula` | String concatenation, upper/lower casing, money formatting | `{ str_op, str_a_type, str_a, str_b_type, str_b }` | String | `StringFormulaResolver.vue` | `StringFormulaResolver` | Python string methods / `frappe.utils.fmt_money` | Overlaps with `normalization` and `format` → Merged into `text` |
| `normalization` | Clean and normalize text using pipeline profiles (slug, snake, etc) | `{ norm_field, norm_profile, norm_pipeline, norm_op }` | String | `NormalizationResolver.vue` | `NormalizationResolver` | `flexirule.ruleflow.utils.normalization` | Overlaps with `string_formula` and `format` → Merged into `text` |
| `format` | String formatting, date formatting, money formatting | `{ fmt_op, fmt_field, fmt_config }` | String | `FormatResolver.vue` | `FormatResolver` | `frappe.utils.format_date` / `str.format()` | Overlaps with `string_formula` → Merged into `text` |
| `child_aggregation` | Aggregates child table columns (`sum`, `avg`, `count`) | `{ agg_table, agg_field, agg_op }` | Number | `AggregationResolver.vue` | `ChildAggregationResolver` | In-memory iteration over child rows | Overlaps with `collection` → Refactored into `aggregate` |
| `collection` | Evaluates conditions over child arrays (`any`, `all`, `first`, `filter`, `pluck`, `unique`, `count`) | `{ source, operation, condition, target_field }` | Any (List, Dict, Bool, Int) | `CollectionResolver.vue` | `CollectionResolver` | In-memory `ConditionEvaluator` on array | Retained as canonical `collection` |
| `fetch` | Database lookup of field value from linked document | `{ link_field, fetch_field, linked_doctype }` | Any | `FetchResolver.vue` | `FetchResolver` | `frappe.db.get_value` | Renamed / generalized to canonical `lookup` |
| `system_context` | Session user name or role check | `{ sys_token, sys_role }` | String / Boolean | `SystemContextResolver.vue` | `SystemContextResolver` | `frappe.session.user` / `frappe.get_roles` | Merged into `value_source` |
| `VariableResolver` | Path lookup in context (`doc.name`, `vars.total`) | Path string | Any | Text token / @-mention | `VariableResolver` | `get_context_value()` | Exposed as `field` / `variable` operation in `value_source` |
| `StaticResolver` | Literal primitive value (string, int, bool, dict) | Value | Any | Direct text input | `StaticResolver` | Returns literal value | Exposed as `static` operation in `value_source` |
| `SafeEvalResolver` | Fallback execution of python expressions | Expression string | Any | Expression token | `SafeEvalResolver` | `ActionHandler._safe_eval()` | Internal execution strategy (Hidden from primary UI) |
| `JinjaResolver` | Fallback rendering of Jinja templates | Template string | String | Template token | `JinjaResolver` | `frappe.render_template()` | Internal execution strategy (Hidden from primary UI) |
| `ExpressionResolver` | Composite segments of text, variables, and tokens | List of compiled resolvers | String | Rich text editor | `ExpressionResolver` | Join resolved segments | Internal container strategy |
