# Frontend-Backend Contract Analysis

## Data Contract Mapping Table

The following table maps how resolver configurations travel from the Vue UI to stored representations in MariaDB and backend Python execution:

| Resolver Kind | Frontend Generated Config | Stored JSON Representation | Backend Expected Config | Contract Compatibility | Discrepancies / Mismatches |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `date_formula` | `{ kind: "date_formula", base_type, base_field, offset_sign, offset_value, offset_unit }` | `{ "mode": "resolver", "value": "{frappe.utils.add_days(...)}", "config": {...} }` | `DateFormulaResolver(base_type, base_field, offset_value, offset_unit, offset_sign)` | **Compatible** | Frontend defaults `base_type` based on target field; backend defaults `base_type` to `"today"`. |
| `math_formula` | `{ kind: "math_formula", field_a, math_op, field_b_type, field_b, constant_b, precision }` | `{ "mode": "resolver", "value": "{frappe.utils.flt(...)}", "config": {...} }` | `MathFormulaResolver(field_a, math_op, field_b_type, field_b, constant_b, precision)` | **Compatible** | Frontend defaults `precision` to `2`; backend defaults to `2` but allows `None`. |
| `date_diff` | `{ kind: "date_diff", diff_start_type, diff_start_field, diff_end_type, diff_end_field, diff_unit }` | `{ "mode": "resolver", "value": "{frappe.utils.date_diff(...)}", "config": {...} }` | `DateDiffResolver(diff_start_type, diff_start_field, diff_end_type, diff_end_field, diff_unit)` | **Compatible** | Frontend default `diff_end_type` is `"doc_field"`; backend default is `"doc_field"`. |
| `child_aggregation` | `{ kind: "child_aggregation", agg_table, agg_field, agg_op }` | `{ "mode": "resolver", "value": "{sum(...)}", "config": {...} }` | `ChildAggregationResolver(agg_table, agg_field, agg_op)` | **Compatible** | `agg_field` is unused by backend when `agg_op == "count"`, but required by frontend validation for other ops. |
| `string_formula` | `{ kind: "string_formula", str_op, str_a_type, str_a, str_b_type, str_b }` | `{ "mode": "resolver", "value": "{str(...) + ...}", "config": {...} }` | `StringFormulaResolver(str_op, str_a_type, str_a, str_b_type, str_b)` | **Compatible** | Frontend defaults `str_b_type` to `"constant"`; backend defaults to `"constant"`. |
| `normalization` | `{ kind: "normalization", norm_field, norm_profile, norm_pipeline }` | `{ "mode": "resolver", "value": "{flexirule.utils...}", "config": {...} }` | `NormalizationResolver(norm_field, norm_profile, norm_pipeline, norm_op)` | **Compatible** | Frontend generates pipeline/profile; backend supports legacy `norm_op` mapping fallback (`trim`, `slug`, `snake`, `title`, `upper`, `lower`). |
| `format` | `{ kind: "format", fmt_op, fmt_field, fmt_config }` | `{ "mode": "resolver", "value": "{frappe.utils.format_date(...)}", "config": {...} }` | `FormatResolver(fmt_op, fmt_field, fmt_config)` | **Compatible** | `fmt_config` holds date format string or currency field name depending on `fmt_op`. |
| `fetch` | `{ kind: "fetch", link_field, fetch_field, linked_doctype, link_source_type }` | `{ "mode": "resolver", "value": "{frappe.db.get_value(...)}", "config": {...} }` | `FetchResolver(link_field, fetch_field, linked_doctype)` | **Compatible** | Frontend generates extra `link_source_type` property which backend safely ignores. |
| `system_context` | `{ kind: "system_context", sys_token, sys_role }` | `{ "mode": "resolver", "value": "{frappe.session.user}", "config": {...} }` | `SystemContextResolver(sys_token, sys_role)` | **Compatible** | Match. |

---

## Analysis of Legacy Modes & Coercion Flow

### Frontend Coercion (`coerceStructuredValue`)
In `FlexValueControl.vue`, incoming values are passed through `coerceStructuredValue()`:

```javascript
function coerceStructuredValue(val) {
    if (val && typeof val === "object" && val.mode) {
        if (["formula", "format", "normalize", "normalization"].includes(val.mode)) {
            const config = { ...(val.config || {}) };
            if (!config.kind) {
                if (val.mode === "formula") config.kind = "math_formula";
                if (val.mode === "format") config.kind = "format";
                if (val.mode === "normalize" || val.mode === "normalization") {
                    config.kind = "normalization";
                }
            }
            return {
                mode: "resolver",
                value: val.value || val.expression || val.resolver || compileToCode(config) || "",
                config,
            };
        }
        // ...
    }
}
```

### Backend Coercion (`ValueResolver.compile`)
In `flexirule/ruleflow/core/value_resolver.py`, `ValueResolver.compile()` also handles legacy modes:

```python
if mode in ("resolver", "formatter", "normalize", "format", "normalization") or "kind" in val:
    config = val.get("config") or val
    if isinstance(config, dict) and "kind" in config:
        return ValueResolver.compile_resolver_config(config)
```

---

## Identified Contract Issues & Mismatches

### 1. Missing `config` in Manual Mode Strips Visual Editing
When a user switches to **Manual Mode** in `FlexValueControl.vue`, `tokenDraftAttrs.value.config` is set to `null`. On save, the stored payload becomes `{ mode: "resolver", value: "doc.amount * 2" }` without a `config` key.
- **Backend Behavior**: `ValueResolver.compile()` falls back to `SafeEvalResolver` on the `value` string. The backend evaluates it correctly.
- **Frontend Behavior**: Opening the token editor again defaults to Manual Mode because `config` is missing. The user cannot switch back to Visual Builder unless they re-configure the token from scratch.

### 2. Double Expression Wrapping in Mixed Expression Mode
In `serialize()` inside `FlexValueControl.vue`, when multiple tokens or mixed text/token content exist, `serialize()` produces `mode: "expression"`:
```json
{
  "mode": "expression",
  "value": [
    { "type": "text", "value": "Date: " },
    { "type": "variableToken", "attrs": { "path": "doc.creation", "expression": "{doc.creation}" } }
  ]
}
```
In `serialize()`, `variableToken` expression is manually wrapped with `{}` (`expr = \`{${expr}}\``). However, `resolverToken` expressions already include `{}` from `compileToCode()`. If `item.attrs.expression` is used on a variable, it gets wrapped once, but if passed through legacy serializers, double braces (e.g. `{{doc.creation}}`) can cause Jinja parsing ambiguity instead of Python evaluation.

### 3. Extra Unused Frontend Fields
Frontend strategy for `fetch` generates `link_source_type: "doc_field"`. The backend constructor `FetchResolver` only accepts `link_field`, `fetch_field`, and `linked_doctype`. The backend safely ignores `link_source_type`, but it creates minor payload bloat.
