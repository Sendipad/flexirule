# Backend Resolver Architecture & Runtime Execution

## Overview

The backend Value Resolver system (`flexirule/ruleflow/core/value_resolver.py`) converts dynamic frontend JSON configurations or raw expressions into compiled, highly optimized `CompiledResolver` strategy objects.

To achieve maximum execution speed during rule evaluation, compiled resolvers are cached on `frappe.local` per action execution key.

---

## Backend Execution Pipeline

```
Rule Engine / Action Handler (e.g. AssignmentHandler, QueryRecordsHandler)
    ↓
get_compiled_resolver(action, key, value_payload)
    ↓
Check frappe.local.flexirule_compiled_resolvers Cache
    ↓ (Cache Miss)
ValueResolver.compile(value_payload)
    ↓
    ├── If payload is dict:
    │     ├── mode in ("static", "link") → StaticResolver
    │     ├── mode == "variable" → VariableResolver
    │     ├── mode == "expression" → ExpressionResolver(segments)
    │     └── mode in ("resolver", "formatter", "normalize", "format", "normalization") or "kind" in val:
    │           └── ValueResolver.compile_resolver_config(config)
    │                 ├── "date_formula" → DateFormulaResolver
    │                 ├── "math_formula" → MathFormulaResolver
    │                 ├── "date_diff" → DateDiffResolver
    │                 ├── "child_aggregation" → ChildAggregationResolver
    │                 ├── "string_formula" → StringFormulaResolver
    │                 ├── "normalization" → NormalizationResolver
    │                 ├── "format" → FormatResolver
    │                 ├── "fetch" → FetchResolver
    │                 └── "system_context" → SystemContextResolver
    └── If payload is str:
          ├── Contains "{{" or "{%" → JinjaResolver
          ├── Starts with "{" and ends with "}" → SafeEvalResolver
          └── Otherwise → StaticResolver
    ↓
Cache compiled strategy object in frappe.local
    ↓
resolver_instance.resolve(context) → Final Resolved Value
```

---

## Compiled Strategy Hierarchy

All resolver strategy classes inherit from `CompiledResolver`:

```python
class CompiledResolver:
    def resolve(self, context: dict) -> Any:
        raise NotImplementedError()
```

### Strategy Implementations

1. **`StaticResolver`**:
   - Holds static value. Returns `self.value`.
2. **`VariableResolver`**:
   - Calls `get_context_value(context, self.path)`.
   - Supports dot notation across `doc`, `vars`, `item`, `loop`, `row` scopes.
3. **`DateFormulaResolver`**:
   - Resolves base date (`today` or field via `get_context_value`).
   - Uses `frappe.utils.add_days` or `frappe.utils.add_to_date`.
4. **`MathFormulaResolver`**:
   - Coerces inputs using `frappe.utils.flt`.
   - Evaluates arithmetic (`+`, `-`, `*`, `/`).
   - Prevents zero-division errors (`val_b != 0.0 else 0.0`).
   - Applies `frappe.utils.flt(res, precision)`.
5. **`DateDiffResolver`**:
   - Resolves start and end dates.
   - Evaluates difference via `frappe.utils.date_diff` or `month_diff`.
6. **`ChildAggregationResolver`**:
   - Retrieves child array from context.
   - Computes `len(rows)` for `count`, or sums/averages row field values using `frappe.utils.flt`.
7. **`StringFormulaResolver`**:
   - Resolves string inputs `val_a` and `val_b`.
   - Executes `concat`, `uppercase`, `lowercase`, or `frappe.utils.fmt_money`.
8. **`NormalizationResolver`**:
   - Calls `execute_normalization_pipeline(value, pipeline, profile)` from `flexirule.ruleflow.utils.normalization`.
9. **`FormatResolver`**:
   - Applies `frappe.utils.format_date`, `frappe.utils.fmt_money`, or python string `.format()`.
10. **`FetchResolver`**:
    - Resolves link field value from context.
    - Executes single read `frappe.db.get_value(linked_doctype, link_value, fetch_field)`.
11. **`SystemContextResolver`**:
    - Returns `frappe.session.user` or checks `frappe.get_roles(frappe.session.user)`.
12. **`JinjaResolver`**:
    - Renders template via `frappe.render_template(self.template, template_context)` with SSTI-sanitized context.
13. **`SafeEvalResolver`**:
    - Evaluates expression string via `handler._safe_eval(self.expression, context)` using `SafeEvalVisitor` AST inspection.
14. **`ExpressionResolver`**:
    - Iterates over segments array, calls `.resolve(context)` on each segment, and concatenates non-null string results.

---

## Context Scope Resolution (`get_context_value`)

Variable lookups in `get_context_value(context, path)` resolve dot-notated paths in the following order:

1. **Explicit Scopes**:
   - `doc.field` → `context.get("doc")`
   - `vars.field` → `context.get("vars")`
   - `item.field` → `context.get("item")`
   - `loop.field` → `context.get("loop")`
   - `row.field` → `context.get("row")`
2. **Implicit Fallback** (if no scope prefix specified):
   - First checks if field exists in `context.get("doc")`.
   - Next checks if field exists in `context.get("vars")`.
   - Returns `None` if unfound.

---

## Caching Strategy (`get_compiled_resolver`)

To prevent re-compiling JSON schemas into strategy objects during loops or repetitive rule executions:

```python
def get_compiled_resolver(action, key: str, value_payload: Any) -> CompiledResolver:
    if not hasattr(frappe.local, "flexirule_compiled_resolvers"):
        frappe.local.flexirule_compiled_resolvers = {}

    cache_key = f"{getattr(action, 'name', 'action')}_{key}"
    if cache_key not in frappe.local.flexirule_compiled_resolvers:
        frappe.local.flexirule_compiled_resolvers[cache_key] = ValueResolver.compile(value_payload)

    return frappe.local.flexirule_compiled_resolvers[cache_key]
```

This request-local cache ensures O(1) compilation overhead per HTTP request or background job transaction.
