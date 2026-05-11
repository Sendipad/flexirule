# Condition System Deep Dive

## Two-Phase Condition Architecture
1. **Design-time:** `condition_json` (visual AST)
    - Tree structure: `{logical_operator, conditions: [{left, op, right}], ...}`
    - Built by `ConditionBuilder.vue` → `ConditionNode.vue`
    - Stored as JSON in Rule Action `condition_json` field

2. **Runtime:** `compiled_expression` (Python string)
    - Generated on save via `ConditionCompiler.compile_node(condition_json)`
    - Example: `(doc.status == "Open" and doc.amount > 1000) or ("Manager" in frappe.get_roles())`
    - Evaluated with `frappe.safe_eval(compiled_expression, eval_locals)`

## ConditionCompiler Module (`flexirule.ruleflow.core.compiler`)
- Key functions:
  - `compile_node(node)` → Python string
  - `_compile_condition(cond)` → single condition
  - `_compile_path(expr)` → dot/bracket path resolver
  - `_quote(value)` → Python literal quoting
- Operator mapping: `==, !=, >, <, >=, <=, in, not in, like, not like, contains`
- Type-aware quoting (strings, dates, numbers, booleans, None)
- `PathTransformer` — rewrites `doc.field` / `doc.get("field")` / `resolve(doc, "path")` to safe FieldResolver calls

## FieldResolver (`flexirule.ruleflow.utils.field_resolver`)
- `resolve(obj, path)` — unified field resolution
- Supports: dot notation (`doc.items[0].qty`), bracket notation, function calls
- Cached attribute lookup for performance

## Expression Evaluation
- `eval_condition_bool(expr, locals, default=False)` — boolean coercion
- `eval_value(expr, locals, default=None)` — raw value extraction
- Implemented in `runtime_eval.py` using `frappe.safe_eval` with restricted globals

## Performance
- `compiled_expression` parsed once per rule load, cached in runtime registry
- Direct eval of pure Python string (no JSON traversal at runtime)
- Watched fields extraction via regex for change-based filtering

## Validation
- AST root validation — only allowed context roots (`doc`, `old_doc`, `vars`, `frappe`, `item`, `loop`, `caller`, `rule`, `doctype`, `resolve`, `check_link_match`, utility functions)
- Undefined name detection at compile time
- SafeFrappeAPI prevents writes in conditions

