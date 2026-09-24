# Security Analysis & Boundary Specification

## 1. Security Architecture Overview

Value Resolvers evaluate dynamic expressions, row predicates, field paths, and format strings against live Frappe document contexts.

Simplifying the user-facing taxonomy from 10 strategies to 8 families **does NOT alter or broaden the underlying executable attack surface**. The security boundary relies on three strict principles:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Security Boundary Layers                        │
├────────────────────────┬───────────────────────┬───────────────────────┤
│ 1. Non-Eval Execution  │ 2. SafeEval AST Guard │ 3. Jinja SSTI Shield  │
└────────────────────────┴───────────────────────┴───────────────────────┘
```

---

## 2. In-Depth Security Analysis by Layer

### 2.1 Non-Eval Execution Paradigm (Predicate & Collection Security)
In **Collections & Tables** (`CollectionResolver`), row predicate conditions (e.g. `row.qty > 100`) are evaluated strictly via `ConditionEvaluator`.
- **Zero String `eval()` or `exec()`**: Predicate expressions are NOT converted to executable Python string code.
- **Operator Whitelist**: Operations rely on explicit Python `operator` mapping (`operator.gt`, `operator.eq`, `operator.in_`).
- **Scope Restriction**: Variable references are restricted to `doc`, `row`, `old_doc`, and `vars`. Dunder attribute access (`__class__`, `__subclasses__`, `__globals__`) is explicitly rejected.

### 2.2 SafeEval AST Inspection & Sandbox Boundary
For numeric arithmetic (`number.calculate`) and date expressions (`date.calculate`), expressions compiled to Python code are validated using `SafeEvalVisitor` (`flexirule/ruleflow/core/permissions.py`).
- **AST Whitelist**: Only `ast.BinOp`, `ast.UnaryOp`, `ast.Name`, `ast.Constant`, `ast.Call`, and `ast.Attribute` nodes are permitted.
- **Blocked Constructs**: Import statements, function definitions, lambda expressions, generator expressions, and dunder attributes are blocked at compile time.

### 2.3 Jinja SSTI Prevention
In string formatting and templating (`text.format`), raw `frappe` framework objects and internal python modules are strictly excluded from the rendering context (`document_action.py:_template_context`).
- **Context Injection**: Only `doc`, `old_doc`, `vars`, and standard formatting helpers (`fmt_money`, `format_date`) are exposed to Jinja environments.

---

## 3. Dynamic Field Reference & Lookup Security

In **Lookup** (`lookup.field` / `lookup.record`):
- Document permissions (`frappe.has_permission`) are enforced prior to executing link lookups via `FieldResolver`.
- Dynamic DocType names are sanitized against standard Frappe metadata (`frappe.get_meta(doctype)`). SQL injection or illegal table access via unescaped DocType strings is impossible.
