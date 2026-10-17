# Configuration Schema Consistency Analysis

## Executive Summary

This report compares configuration schemas across all Value Resolvers in FlexiRule to evaluate structural consistency, property naming conventions, field reference formats, and opportunities for schema unification.

---

## 1. Cross-Resolver Configuration Schema Comparison

| Resolver Kind | Configuration Shape Structure | Primary Source Field | Operation Field | Condition / Filter Syntax | Consistency Rating |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `date_formula` | Flat JSON | `base_field` | N/A (Offset sign/unit) | N/A | Moderate |
| `math_formula` | Flat JSON | `field_a`, `field_b` | `math_op` (`+`, `-`, `*`, `/`) | N/A | Moderate |
| `date_diff` | Flat JSON | `diff_start_field`, `diff_end_field` | `diff_unit` (`days`, `months`, `years`) | N/A | Moderate |
| `child_aggregation` | Flat JSON | `agg_table`, `agg_field` | `agg_op` (`sum`, `avg`, `count`) | N/A | High |
| `string_formula` | Flat JSON | `str_a`, `str_b` | `str_op` (`concat`, `uppercase`, `lowercase`, `fmt_money`) | N/A | Moderate |
| `normalization` | Flat JSON | `norm_field` | `norm_profile` / `norm_pipeline` | N/A | High |
| `format` | Flat JSON | `fmt_field` | `fmt_op` (`format_date`, `fmt_money`, `format`) | `fmt_config` (format string/currency) | Low |
| `fetch` | Flat JSON | `link_field` | N/A (Lookup target `fetch_field`) | N/A | High |
| `system_context` | Flat JSON | N/A | `sys_token` (`user`, `role_check`) | `sys_role` | Moderate |
| `collection` | Nested Operation Schema | `source` (`doc.items`) | `operation` (`count`, `any`, `all`, `first`, `filter`, `pluck`, `unique`) | `condition` (Standard FlexiRule condition tree) | **Canonical Model** |

---

## 2. Inconsistencies & Property Naming Divergence

### 2.1. Operational Verb Property Names
Existing scalar resolvers prefix their operation property with a 3-letter abbreviation of the resolver kind:
- `math_formula` uses `math_op`
- `child_aggregation` uses `agg_op`
- `string_formula` uses `str_op`
- `normalization` uses `norm_op` (legacy)
- `format` uses `fmt_op`
- `system_context` uses `sys_token`

In contrast, **`collection`** uses the standard, clean property name:
- `operation` (`"operation": "pluck"`)

### 2.2. Source Field Naming
- `date_formula` uses `base_field`
- `normalization` uses `norm_field`
- `format` uses `fmt_field`
- `child_aggregation` uses `agg_table`
- `collection` uses `source` (`"source": "doc.items"`)

### 2.3. Condition & Filter Structure
- `collection` uses the standard FlexiRule condition array structure (`ConditionEvaluator` JSON payload).
- `child_aggregation` has **NO condition support**, preventing filtered aggregations (e.g., sum of items where rate > 100).

---

## 3. Unified Configuration Schema Model Proposal

A consistent, forward-compatible configuration schema across all resolvers should follow the pattern established by `CollectionResolver`:

```json
{
  "kind": "family_or_kind",
  "operation": "canonical_operation_verb",
  "source": "field_or_path",
  "config": {
    "target_field": "optional_field",
    "precision": 2,
    "unit": "days",
    "condition": [...]
  }
}
```

This model standardizes `operation`, `source`, and optional nested `config` properties across all resolver types.
