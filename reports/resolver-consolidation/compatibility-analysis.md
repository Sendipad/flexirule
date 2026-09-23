# Compatibility Analysis

## Executive Summary
FlexiRule rules stored in production databases contain legacy resolver `kind` configurations (`date_formula`, `date_diff`, `math_formula`, `string_formula`, `normalization`, `format`, `fetch`, `system_context`, `child_aggregation`). Deleting these identifiers would break execution of saved rules.

This analysis details how backward compatibility is guaranteed at runtime via transparent payload coercion and compiler aliasing.

---

## Legacy Config Mapping Matrix

| Legacy `kind` String | Legacy Configuration Fields | Canonical Target Family (`kind`) | Canonical Target Operation | Payload Coercion Rules |
| :--- | :--- | :--- | :--- | :--- |
| `date_formula` | `{ base_type, base_field, offset_value, offset_unit, offset_sign }` | `date` | `offset_sign == '-' ? 'subtract' : 'add'` | Maps `offset_value`, `offset_unit`, `base_field` into `DateResolver` |
| `date_diff` | `{ diff_start_type, diff_start_field, diff_end_type, diff_end_field, diff_unit }` | `date` | `diff` | Maps `diff_start_field`, `diff_end_field`, `diff_unit` into `DateResolver` |
| `math_formula` | `{ field_a, math_op, field_b_type, field_b, constant_b, precision }` | `math` | `math_op` (`+`, `-`, `*`, `/`) | Direct compilation into `MathResolver` |
| `string_formula` | `{ str_op, str_a_type, str_a, str_b_type, str_b }` | `text` | `str_op` (`concat`, `uppercase`→`upper`, `lowercase`→`lower`, `fmt_money`) | Maps `str_a` as `field_a`, `str_b` as `field_b` into `TextResolver` |
| `normalization` | `{ norm_field, norm_profile, norm_pipeline, norm_op }` | `text` | `norm_op` (`trim`, `slug`, `snake`, `title`, `upper`, `lower`) | Maps `norm_field` as `field_a` into `TextResolver` |
| `format` | `{ fmt_op, fmt_field, fmt_config }` | `text` | `fmt_op` (`format_date`, `fmt_money`, `format`→`pattern`) | Maps `fmt_field` as `field_a`, `fmt_config` into `TextResolver` |
| `child_aggregation` | `{ agg_table, agg_field, agg_op }` | `aggregate` | `agg_op` (`sum`, `avg`, `min`, `max`, `count`) | Direct compilation into `AggregateResolver` |
| `fetch` | `{ link_field, fetch_field, linked_doctype }` | `lookup` | `get` | Direct compilation into `LookupResolver` |
| `system_context` | `{ sys_token, sys_role }` | `value_source` | `system_context` | Direct compilation into `ValueSourceResolver` |

---

## Guaranteed Behavioral Invariants
1. **Zero Database Migrations Required**: Saved rule JSON payloads in the database remain intact.
2. **Deterministic Output**: Executing a legacy `date_formula` payload via the consolidated `DateResolver` produces the exact same string/date result as the pre-refactor implementation.
3. **Frontend Deserialization**: When an existing rule containing `kind: "date_formula"` is opened in the visual Rule Builder, the frontend normalizes it to `kind: "date"` so the new UI component displays the state accurately without data loss.
